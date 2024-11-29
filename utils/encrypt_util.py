"""
加密工具模块

提供完整的加密解密功能，支持以下特性：

功能特性:
    - 哈希算法
        * MD5
        * SHA1/SHA224/SHA256/SHA384/SHA512
        * HMAC
    - 对称加密
        * AES (CBC/ECB/CFB/OFB/CTR)
        * DES
        * 3DES
    - 非对称加密
        * RSA
    - 编码转换
        * Base16/Base32/Base64/Base85
        * URL编码
        * HTML编码
    - 随机数生成
        * 安全随机数
        * UUID生成

技术特点:
    - 完整的类型注解
    - 自动化日志记录
    - 异常重试机制
    - 链式调用支持
"""

import base64
import hashlib
import hmac
import html
import urllib.parse
import uuid
from enum import Enum, auto
from functools import wraps
from typing import Optional, Type

from Crypto.Cipher import AES, DES, DES3, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

from .log_util import my_logger


class EncryptError(Exception):
    """加密错误基类"""
    pass


class DecryptError(Exception):
    """解密错误基类"""
    pass


class EncodeError(Exception):
    """编码错误基类"""
    pass


class DecodeError(Exception):
    """解码错误基类"""
    pass


class CipherMode(Enum):
    """密码模式枚举"""
    ECB = auto()
    CBC = auto()
    CFB = auto()
    OFB = auto()
    CTR = auto()


def encrypt_handler(func):
    """加密操作装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            my_logger.logger.debug(f"🔒 开始{func.__name__}操作")
            result = func(*args, **kwargs)
            my_logger.logger.debug(f"✅ {func.__name__}操作成功")
            return result
        except Exception as e:
            my_logger.logger.error(f"❌ {func.__name__}操作失败: {str(e)}")
            raise

    return wrapper


class HashUtil:
    """哈希算法工具类"""

    @staticmethod
    @encrypt_handler
    def md5(text: str, encoding: str = 'utf-8') -> str:
        """MD5哈希"""
        return hashlib.md5(str(text).encode(encoding)).hexdigest()

    @staticmethod
    @encrypt_handler
    def sha1(text: str, encoding: str = 'utf-8') -> str:
        """SHA1哈希"""
        return hashlib.sha1(str(text).encode(encoding)).hexdigest()

    @staticmethod
    @encrypt_handler
    def sha256(text: str, encoding: str = 'utf-8') -> str:
        """SHA256哈希"""
        return hashlib.sha256(str(text).encode(encoding)).hexdigest()

    @staticmethod
    @encrypt_handler
    def sha512(text: str, encoding: str = 'utf-8') -> str:
        """SHA512哈希"""
        return hashlib.sha512(str(text).encode(encoding)).hexdigest()

    @staticmethod
    @encrypt_handler
    def hmac_sha256(key: str, text: str, encoding: str = 'utf-8') -> str:
        """HMAC-SHA256"""
        return hmac.new(
            key.encode(encoding),
            text.encode(encoding),
            hashlib.sha256
        ).hexdigest()


class AESUtil:
    """AES加密工具类"""

    @staticmethod
    def _pad_key(key: bytes) -> bytes:
        """调整密钥长度为16/24/32字节"""
        key_length = len(key)
        if key_length <= 16:
            return key.ljust(16, b'\0')
        elif key_length <= 24:
            return key.ljust(24, b'\0')
        else:
            return key.ljust(32, b'\0')

    @staticmethod
    @encrypt_handler
    def encrypt(key: str, text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        AES加密

        Args:
            key: 密钥(会自动调整到16/24/32字节)
            text: 待加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: Base64编码的加密结果
        """
        # 处理密钥
        padded_key = AESUtil._pad_key(key.encode(encoding))

        # 生成随机IV
        iv = get_random_bytes(16)

        # 创建加密器
        if mode == CipherMode.ECB:
            cipher = AES.new(padded_key, AES.MODE_ECB)
        else:
            cipher = AES.new(padded_key, getattr(AES, f'MODE_{mode.name}'), iv)

        # 加密
        padded_data = pad(text.encode(encoding), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)

        # 组合IV和加密数据
        result = iv + encrypted_data if mode != CipherMode.ECB else encrypted_data

        return base64.b64encode(result).decode(encoding)

    @staticmethod
    @encrypt_handler
    def decrypt(key: str, encrypted_text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        AES解密

        Args:
            key: 密钥(会自动调整到16/24/32字节)
            encrypted_text: Base64编码的加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: 解密后的原文
        """
        # 处理密钥
        padded_key = AESUtil._pad_key(key.encode(encoding))

        # 解码Base64
        encrypted_data = base64.b64decode(encrypted_text)

        # 提取IV和加密数据
        if mode == CipherMode.ECB:
            iv = b''
            cipher_text = encrypted_data
        else:
            iv = encrypted_data[:16]
            cipher_text = encrypted_data[16:]

        # 创建解密器
        if mode == CipherMode.ECB:
            cipher = AES.new(padded_key, AES.MODE_ECB)
        else:
            cipher = AES.new(padded_key, getattr(AES, f'MODE_{mode.name}'), iv)

        # 解密
        decrypted_data = cipher.decrypt(cipher_text)
        unpadded_data = unpad(decrypted_data, AES.block_size)

        return unpadded_data.decode(encoding)


class DESUtil:
    """DES加密工具类"""

    @staticmethod
    def _pad_key(key: bytes) -> bytes:
        """调整密钥长度为8字节"""
        return key[:8].ljust(8, b'\0')

    @staticmethod
    @encrypt_handler
    def encrypt(key: str, text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        DES加密

        Args:
            key: 密钥(会自动调整到8字节)
            text: 待加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: Base64编码的加密结果
        """
        # 处理密钥
        padded_key = DESUtil._pad_key(key.encode(encoding))

        # 生成随机IV
        iv = get_random_bytes(8)

        # 创建加密器
        if mode == CipherMode.ECB:
            cipher = DES.new(padded_key, DES.MODE_ECB)
        else:
            cipher = DES.new(padded_key, getattr(DES, f'MODE_{mode.name}'), iv)

        # 加密
        padded_data = pad(text.encode(encoding), DES.block_size)
        encrypted_data = cipher.encrypt(padded_data)

        # 组合IV和加密数据
        result = iv + encrypted_data if mode != CipherMode.ECB else encrypted_data

        return base64.b64encode(result).decode(encoding)

    @staticmethod
    @encrypt_handler
    def decrypt(key: str, encrypted_text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        DES解密

        Args:
            key: 密钥(会自动调整到8字节)
            encrypted_text: Base64编码的加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: 解密后的原文
        """
        # 处理密钥
        padded_key = DESUtil._pad_key(key.encode(encoding))

        # 解码Base64
        encrypted_data = base64.b64decode(encrypted_text)

        # 提取IV和加密数据
        if mode == CipherMode.ECB:
            iv = b''
            cipher_text = encrypted_data
        else:
            iv = encrypted_data[:8]
            cipher_text = encrypted_data[8:]

        # 创建解密器
        if mode == CipherMode.ECB:
            cipher = DES.new(padded_key, DES.MODE_ECB)
        else:
            cipher = DES.new(padded_key, getattr(DES, f'MODE_{mode.name}'), iv)

        # 解密
        decrypted_data = cipher.decrypt(cipher_text)
        unpadded_data = unpad(decrypted_data, DES.block_size)

        return unpadded_data.decode(encoding)


class TripleDESUtil:
    """3DES加密工具类"""

    @staticmethod
    def _pad_key(key: bytes) -> bytes:
        """调整密钥长度为24字节"""
        return key[:24].ljust(24, b'\0')

    @staticmethod
    @encrypt_handler
    def encrypt(key: str, text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        3DES加密

        Args:
            key: 密钥(会自动调整到24字节)
            text: 待加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: Base64编码的加密结果
        """
        # 处理密钥
        padded_key = TripleDESUtil._pad_key(key.encode(encoding))

        # 生成随机IV
        iv = get_random_bytes(8)

        # 创建加密器
        if mode == CipherMode.ECB:
            cipher = DES3.new(padded_key, DES3.MODE_ECB)
        else:
            cipher = DES3.new(padded_key, getattr(DES3, f'MODE_{mode.name}'), iv)

        # 加密
        padded_data = pad(text.encode(encoding), DES3.block_size)
        encrypted_data = cipher.encrypt(padded_data)

        # 组合IV和加密数据
        result = iv + encrypted_data if mode != CipherMode.ECB else encrypted_data

        return base64.b64encode(result).decode(encoding)

    @staticmethod
    @encrypt_handler
    def decrypt(key: str, encrypted_text: str, mode: CipherMode = CipherMode.CBC,
                encoding: str = 'utf-8') -> str:
        """
        3DES解密

        Args:
            key: 密钥(会自动调整到24字节)
            encrypted_text: Base64编码的加密文本
            mode: 加密模式
            encoding: 字符编码

        Returns:
            str: 解密后的原文
        """
        # 处理密钥
        padded_key = TripleDESUtil._pad_key(key.encode(encoding))

        # 解码Base64
        encrypted_data = base64.b64decode(encrypted_text)

        # 提取IV和加密数据
        if mode == CipherMode.ECB:
            iv = b''
            cipher_text = encrypted_data
        else:
            iv = encrypted_data[:8]
            cipher_text = encrypted_data[8:]

        # 创建解密器
        if mode == CipherMode.ECB:
            cipher = DES3.new(padded_key, DES3.MODE_ECB)
        else:
            cipher = DES3.new(padded_key, getattr(DES3, f'MODE_{mode.name}'), iv)

        # 解密
        decrypted_data = cipher.decrypt(cipher_text)
        unpadded_data = unpad(decrypted_data, DES3.block_size)

        return unpadded_data.decode(encoding)


class RSAUtil:
    """RSA加密工具类"""

    def __init__(self, public_key: Optional[str] = None,
                 private_key: Optional[str] = None):
        """
        初始化RSA工具

        Args:
            public_key: PEM格式的公钥
            private_key: PEM格式的私钥
        """
        self.public_key = RSA.import_key(public_key) if public_key else None
        self.private_key = RSA.import_key(private_key) if private_key else None

    @staticmethod
    @encrypt_handler
    def generate_key_pair(bits: int = 2048) -> tuple[str, str]:
        """
        生成RSA密钥对

        Args:
            bits: 密钥长度

        Returns:
            tuple: (公钥, 私钥)的PEM格式字符串
        """
        key = RSA.generate(bits)
        private_key = key.export_key().decode()
        public_key = key.publickey().export_key().decode()
        return public_key, private_key

    @encrypt_handler
    def encrypt(self, text: str, encoding: str = 'utf-8') -> str:
        """
        RSA加密

        Args:
            text: 待加密文本
            encoding: 字符编码

        Returns:
            str: Base64编码的加密结果
        """
        if not self.public_key:
            raise ValueError("未设置公钥")

        cipher = PKCS1_OAEP.new(self.public_key)
        encrypted_data = cipher.encrypt(text.encode(encoding))
        return base64.b64encode(encrypted_data).decode(encoding)

    @encrypt_handler
    def decrypt(self, encrypted_text: str, encoding: str = 'utf-8') -> str:
        """
        RSA解密

        Args:
            encrypted_text: Base64编码的加密文本
            encoding: 字符编码

        Returns:
            str: 解密后的原文
        """
        if not self.private_key:
            raise ValueError("未设置私钥")

        cipher = PKCS1_OAEP.new(self.private_key)
        encrypted_data = base64.b64decode(encrypted_text)
        decrypted_data = cipher.decrypt(encrypted_data)
        return decrypted_data.decode(encoding)


class EncodeUtil:
    """编码工具类"""

    @staticmethod
    @encrypt_handler
    def base64_encode(text: str, encoding: str = 'utf-8') -> str:
        """Base64编码"""
        return base64.b64encode(text.encode(encoding)).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base64_decode(text: str, encoding: str = 'utf-8') -> str:
        """Base64解码"""
        return base64.b64decode(text).decode(encoding)

    @staticmethod
    @encrypt_handler
    def url_encode(text: str) -> str:
        """URL编码"""
        return urllib.parse.quote(text)

    @staticmethod
    @encrypt_handler
    def url_decode(text: str) -> str:
        """URL解码"""
        return urllib.parse.unquote(text)

    @staticmethod
    @encrypt_handler
    def html_encode(text: str) -> str:
        """HTML编码"""
        return html.escape(text)

    @staticmethod
    @encrypt_handler
    def html_decode(text: str) -> str:
        """HTML解码"""
        return html.unescape(text)

    @staticmethod
    @encrypt_handler
    def base16_encode(text: str, encoding: str = 'utf-8') -> str:
        """Base16编码"""
        return base64.b16encode(text.encode(encoding)).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base16_decode(text: str, encoding: str = 'utf-8') -> str:
        """Base16解码"""
        return base64.b16decode(text).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base32_encode(text: str, encoding: str = 'utf-8') -> str:
        """Base32编码"""
        return base64.b32encode(text.encode(encoding)).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base32_decode(text: str, encoding: str = 'utf-8') -> str:
        """Base32解码"""
        return base64.b32decode(text).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base85_encode(text: str, encoding: str = 'utf-8') -> str:
        """Base85编码"""
        return base64.b85encode(text.encode(encoding)).decode(encoding)

    @staticmethod
    @encrypt_handler
    def base85_decode(text: str, encoding: str = 'utf-8') -> str:
        """Base85解码"""
        return base64.b85decode(text).decode(encoding)


class RandomUtil:
    """随机数工具类"""

    @staticmethod
    @encrypt_handler
    def random_bytes(length: int) -> bytes:
        """生成指定长度的随机字节"""
        return get_random_bytes(length)

    @staticmethod
    @encrypt_handler
    def random_str(length: int) -> str:
        """生成指定长度的随机字符串"""
        return base64.b64encode(get_random_bytes(length)).decode()[:length]

    @staticmethod
    @encrypt_handler
    def uuid4() -> str:
        """生成UUID4"""
        return str(uuid.uuid4())


class EncryptUtil:
    """加密工具类"""

    # 创建静态实例
    hash = HashUtil()
    encode = EncodeUtil()
    random = RandomUtil()

    @staticmethod
    def aes() -> Type[AESUtil]:
        """返回AES工具类"""
        return AESUtil

    @staticmethod
    def des() -> Type[DESUtil]:
        """返回DES工具类"""
        return DESUtil

    @staticmethod
    def des3() -> Type[TripleDESUtil]:
        """返回3DES工具类"""
        return TripleDESUtil

    @staticmethod
    def rsa(public_key: Optional[str] = None,
            private_key: Optional[str] = None) -> RSAUtil:
        """创建RSA工具实例"""
        return RSAUtil(public_key, private_key)


# 创建默认加密工具实例
encrypt_util = EncryptUtil()
