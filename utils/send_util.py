"""
发送工具模块

提供基础的消息发送功能,支持以下特性:

功能特性:
    - 钉钉机器人
        * 文本消息
        * 文件消息
    - 企业微信机器人
        * 文本消息
        * 文件消息
    - 邮件
        * 文本邮件
        * 附件邮件

技术特点:
    - 完整的类型注解
    - 自动化日志记录
    - 异常重试机制
"""
import smtplib
import time
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

import requests

from .log_util import my_logger
from .encrypt_util import encrypt_util

class MessageConfig:
    """消息配置类"""
    
    # 钉钉配置
    DINGTALK_TOKEN = ""  # 访问令牌
    DINGTALK_SECRET = ""  # 加签密钥
    
    # 企业微信配置
    WECHAT_KEY = ""  # 机器人Key
    
    # 邮件配置
    SMTP_HOST = "smtp.example.com"
    SMTP_PORT = 465
    SMTP_USER = "your-email@example.com"
    SMTP_PASSWORD = "your-password"
    FROM_NAME = "Sender Name"
    FROM_ADDR = "sender@example.com"
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1

class MessageSender:
    """消息发送基类"""
    
    def __init__(self):
        """初始化消息发送器"""
        my_logger.logger.info("🔄 初始化消息发送器")
        self.dingtalk = DingTalkBot(
            MessageConfig.DINGTALK_TOKEN,
            MessageConfig.DINGTALK_SECRET
        )
        self.wechat = WeChatBot(MessageConfig.WECHAT_KEY)
        self.email = EmailSender(
            MessageConfig.SMTP_HOST,
            MessageConfig.SMTP_PORT,
            MessageConfig.SMTP_USER,
            MessageConfig.SMTP_PASSWORD
        )
        my_logger.logger.info("✅ 消息发送器初始化完成")

class DingTalkBot:
    """钉钉机器人类"""
    
    def __init__(self, access_token: str, secret: Optional[str] = None):
        """初始化钉钉机器人"""
        self.access_token = access_token
        self.secret = secret
        self.api_url = "https://oapi.dingtalk.com/robot/send"
        self.upload_url = "https://oapi.dingtalk.com/robot/upload_media"
        
    def _get_sign(self) -> Tuple[str, str]:
        """生成签名"""
        timestamp = str(round(time.time() * 1000))
        if self.secret:
            string_to_sign = f'{timestamp}\n{self.secret}'
            sign = encrypt_util.hash.hmac_sha256(self.secret, string_to_sign)
            sign = encrypt_util.encode.url_encode(
                encrypt_util.encode.base64_encode(bytes.fromhex(sign))
            )
            return timestamp, sign
        return timestamp, ""
    
    def _send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息"""
        timestamp, sign = self._get_sign()
        
        params = {
            "access_token": self.access_token
        }
        
        if self.secret:
            params.update({
                "timestamp": timestamp,
                "sign": sign
            })
            
        for _ in range(MessageConfig.MAX_RETRIES):
            try:
                response = requests.post(
                    self.api_url,
                    params=params,
                    json=data,
                    timeout=5
                )
                return response.json()
            except Exception as e:
                my_logger.logger.error(f"❌ 钉钉发送异常: {str(e)}")
                time.sleep(MessageConfig.RETRY_DELAY)
                
        return {"errcode": -1, "errmsg": "发送失败"}
    
    def send_text(self, content: str) -> Dict[str, Any]:
        """发送文本消息"""
        data = {
            "msgtype": "text",
            "text": {"content": content}
        }
        return self._send(data)
    
    def send_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """发送文件消息"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        # 上传文件
        files = {
            'media': (file_path.name, open(file_path, 'rb'), 'application/octet-stream')
        }
        params = {"access_token": self.access_token, "type": "file"}
        response = requests.post(self.upload_url, params=params, files=files)
        result = response.json()
        
        if result.get("errcode") != 0:
            raise Exception(f"文件上传失败: {result.get('errmsg')}")
            
        # 发送文件消息
        data = {
            "msgtype": "file",
            "file": {"media_id": result["media_id"]}
        }
        return self._send(data)

class WeChatBot:
    """企业微信机器人类"""
    
    def __init__(self, key: str):
        """初始化企业微信机器人"""
        self.key = key
        self.webhook = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
        self.upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
        
    def _send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息"""
        for _ in range(MessageConfig.MAX_RETRIES):
            try:
                response = requests.post(
                    self.webhook,
                    json=data,
                    timeout=5
                )
                return response.json()
            except Exception as e:
                my_logger.logger.error(f"❌ 企业微信发送异常: {str(e)}")
                time.sleep(MessageConfig.RETRY_DELAY)
                
        return {"errcode": -1, "errmsg": "发送失败"}
    
    def send_text(self, content: str) -> Dict[str, Any]:
        """发送文本消息"""
        data = {
            "msgtype": "text",
            "text": {"content": content}
        }
        return self._send(data)
    
    def send_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """发送文件消息"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        # 上传文件
        files = {
            'media': (file_path.name, open(file_path, 'rb'), 'application/octet-stream')
        }
        response = requests.post(self.upload_url, files=files)
        result = response.json()
        
        if result.get("errcode") != 0:
            raise Exception(f"文件上传失败: {result.get('errmsg')}")
            
        # 发送文件消息
        data = {
            "msgtype": "file",
            "file": {"media_id": result["media_id"]}
        }
        return self._send(data)

class EmailSender:
    """邮件发送类"""
    
    def __init__(self, host: str, port: int, user: str, password: str, use_ssl: bool = True):
        """初始化邮件发送器"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        
    def _create_smtp(self) -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
        """创建SMTP连接"""
        if self.use_ssl:
            return smtplib.SMTP_SSL(self.host, self.port)
        return smtplib.SMTP(self.host, self.port)
    
    def send_mail(self, to_addrs: Union[str, List[str]], subject: str,
                 content: str, content_type: str = 'plain',
                 attachments: Optional[List[Union[str, Path]]] = None) -> bool:
        """发送邮件"""
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
            
        msg = MIMEMultipart()
        msg['From'] = f"{MessageConfig.FROM_NAME} <{MessageConfig.FROM_ADDR}>"
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = Header(subject, 'utf-8')
        
        msg.attach(MIMEText(content, content_type, 'utf-8'))
        
        if attachments:
            for attachment in attachments:
                attachment_path = Path(attachment)
                if not attachment_path.exists():
                    my_logger.logger.warning(f"⚠️ 附件不存在: {attachment_path}")
                    continue
                    
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read())
                    part.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=attachment_path.name
                    )
                    msg.attach(part)
        
        for _ in range(MessageConfig.MAX_RETRIES):
            try:
                with self._create_smtp() as smtp:
                    smtp.login(self.user, self.password)
                    smtp.send_message(msg)
                return True
            except Exception as e:
                my_logger.logger.error(f"❌ 邮件发送异常: {str(e)}")
                time.sleep(MessageConfig.RETRY_DELAY)
                
        return False

# 创建默认发送器实例
message_sender = MessageSender() 