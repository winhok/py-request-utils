"""
HTTP请求工具模块

提供完整的HTTP请求管理功能，支持以下特性：

功能特性:
    - HTTP请求封装
        * GET, POST, PUT, DELETE等方法支持
        * 会话管理
        * 自动重试机制
    - 请求/响应日志记录
        * 详细的请求参数记录
        * 响应状态和内容记录
        * 执行时间统计
    - curl命令生成
    - Unicode文本处理
    - 响应结果管理

技术特点:
    - 基于requests库实现
    - 完整的类型注解
    - 装饰器模式支持
    - 链式调用支持
    - 自动化日志记录

使用示例:
    >>> # 基本使用
    >>> from utils.request_util import HttpRequest
    >>> client = HttpRequest(base_url="http://api.example.com")
    >>> response = client.get("/users")
    
    >>> # 会话模式
    >>> with Session(base_url="http://api.example.com") as session:
    ...     response = session.post("/login", json={"username": "test"})
"""

import json
import re
import time
from functools import wraps
from shlex import quote
from types import ModuleType
from typing import Union, Any, Callable, Optional, List, Dict, TypeVar

import requests
from requests import Response, Session as RequestsSession
from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest
from urllib3.util.retry import Retry

from .log_util import my_logger

# 定义支持的图片文件扩展名列表
IMG: List[str] = ["jpg", "jpeg", "gif", "bmp", "webp"]

T = TypeVar('T')  # 用于泛型类型注解


@my_logger.runtime_logger
def to_curl(req: PreparedRequest, compressed: bool = False, verify: bool = True) -> str:
    """
    将HTTP请求对象转换为可执行的curl命令字符串

    Args:
        req: HTTP请求对象
        compressed: 是否在curl命令中添加压缩选项
        verify: 是否在curl命令中验证SSL证书

    Returns:
        str: 格式化后的curl命令字符串

    Example:
        >>> request = client.get("/api/users").request
        >>> curl_command = to_curl(request)
        >>> print(curl_command)
    """
    my_logger.logger.info("🔄 开始生成 curl 命令")
    my_logger.logger.debug(f"📝 请求方法: {req.method}")
    my_logger.logger.debug(f"🔗 请求URL: {req.url}")

    parts = [
        ('curl', None),
        ('-X', req.method),
    ]

    for key, value in sorted(req.headers.items()):
        parts += [('-H', f'{key}: {value}')]

    if req.body:
        body = req.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        parts += [('-d', body)]

    if compressed:
        parts += [('--compressed', None)]

    if not verify:
        parts += [('--insecure', None)]

    parts += [(None, req.url)]

    flat_parts = []
    for key, value in parts:
        if key:
            flat_parts.append(quote(key))
        if value:
            flat_parts.append(quote(value))

    result = ' '.join(flat_parts)
    my_logger.logger.info("✅ curl 命令生成完成")
    my_logger.logger.debug(f"📋 生成的命令:\n{result}")
    return result


class ResponseResult:
    """
    HTTP响应结果管理类

    用于存储和管理最近一次HTTP请求的响应信息，提供了响应对象的存取功能。

    Attributes:
        _response: 存储最近一次HTTP响应对象
        _request: 存储最近一次HTTP请求对象

    Methods:
        set_response(): 设置响应对象
        get_response(): 获取响应对象
        get_request(): 获取请求对象

    Example:
        >>> response = client.get("/api/users")
        >>> ResponseResult.set_response(response)
        >>> last_response = ResponseResult.get_response()
    """
    _response: Optional[Response] = None
    _request: Optional[requests.PreparedRequest] = None

    @classmethod
    def set_response(cls, response: Response) -> None:
        """
        设置响应对象

        Args:
            response: HTTP响应对象

        Example:
            >>> ResponseResult.set_response(response)
        """
        cls._response = response
        cls._request = response.request

    @classmethod
    def get_response(cls) -> Optional[Response]:
        """
        获取最近的响应对象

        Returns:
            Optional[Response]: 最近的响应对象，如果没有则返回 None

        Example:
            >>> response = ResponseResult.get_response()
        """
        return cls._response

    @classmethod
    def get_request(cls) -> Optional[requests.PreparedRequest]:
        """获取请求对象"""
        return cls._request


@my_logger.runtime_logger
def formatting(msg: Any) -> str:
    """
    将数据格式化为易读的字符串形式

    Args:
        msg: 需要格式化的数据，支持字典或其他类型

    Returns:
        str: 格式化后的字符串，字典类型会格式化为JSON字符串

    Example:
        >>> data = {"name": "test", "value": 123}
        >>> print(formatting(data))
        {
            "name": "test",
            "value": 123
        }
    """
    my_logger.logger.debug(f"📝 正在格式化数据，类型: {type(msg)}")
    result = json.dumps(msg, indent=2, ensure_ascii=False) if isinstance(
        msg, dict) else str(msg)
    my_logger.logger.debug("✅ 数据格式化完成")
    return result


@my_logger.runtime_logger
def handle_unicode_text(text: str) -> str:
    """
    处理字符串中的Unicode转义序列

    Args:
        text: 包含Unicode转义序列的字符串

    Returns:
        str: 转换后的Unicode字符串

    Example:
        >>> text = "\\u4f60\\u597d"
        >>> result = handle_unicode_text(text)
        >>> print(result)  # 输出: 你好
    """
    my_logger.logger.debug("🔄 开始处理 Unicode 文本")
    my_logger.logger.debug(f"📥 输入文本: {text[:100]}...")  # 只记录前100个字符

    result = text
    if re.search(r"\\u[0-9a-fA-F]{4}", text):
        my_logger.logger.debug("🔍 检测到 Unicode 转义序列，进行转换")
        result = text.encode().decode('unicode_escape')

    my_logger.logger.debug("✅ Unicode 文本处理完成")
    return result


def request(func: Callable[..., Response]) -> Callable[..., Response]:
    """
    HTTP请求装饰器

    为HTTP请求方法添加以下增强功能：
        - 自动记录请求和响应的详细日志
        - 保存响应结果到ResponseResult类中
        - 统一的异常处理和响应解析
        - 自动处理超时和SSL验证设置

    Args:
        func: 被装饰的HTTP请求方法

    Returns:
        Callable: 增强后的请求方法

    Raises:
        Exception: 原始请求可能抛出的任何异常

    Example:
        >>> @request
        ... def get(url: str) -> Response:
        ...     return requests.get(url)
    """

    @my_logger.runtime_logger
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Response:
        # 请求开始分隔符
        my_logger.logger.info('=' * 50)
        my_logger.logger.info('🚀 开始发送请求')
        my_logger.logger.info('-' * 50)

        # 获取请求信息
        func_name: str = func.__name__
        my_logger.logger.info('📤 请求详情:')

        try:
            url: str = list(args)[1]
        except IndexError:
            url: str = kwargs.get("url", "")

        # 请求信息日志
        my_logger.logger.info(f"📍 接口: {url}")
        my_logger.logger.info(f"📝 方法: {func_name.upper()}")

        # 记录请求参数
        params_map = {
            'auth': '🔐 认证信息',
            'headers': '📋 请求头',
            'cookies': '🍪 Cookies',
            'params': '❓ 查询参数',
            'data': '📦 表单数据',
            'json': '📄 JSON数据',
            'files': '📎 文件'
        }

        for param, desc in params_map.items():
            if kwargs.get(param):
                my_logger.logger.debug(f"{desc}:\n{formatting(kwargs[param])}")

        # 设置默认超时和SSL验证选项
        kwargs.setdefault('timeout', 10)
        kwargs.setdefault('verify', False)

        # 执行请求
        start_time = time.time()
        r: Response = func(*args, **kwargs)
        duration = time.time() - start_time

        # 响应分隔符
        my_logger.logger.info('-' * 50)
        my_logger.logger.info('📨 响应详情:')

        # 状态码图标映射
        status_icons = {
            2: '✅',  # 2xx
            3: '↪️',  # 3xx
            4: '⚠️',  # 4xx
            5: '❌'  # 5xx
        }
        status_icon = status_icons.get(r.status_code // 100, '❓')

        my_logger.logger.info(
            f"{status_icon} 状态码: {r.status_code} ({r.reason})")
        my_logger.logger.info(f"⏱️ 耗时: {duration:.3f}秒")

        # 处理响应内容
        try:
            resp: Dict = r.json()
            my_logger.logger.debug("📋 响应类型: JSON")
            my_logger.logger.debug(f"📝 响应内容:\n{formatting(resp)}")
        except json.JSONDecodeError:
            if url.split(".")[-1].lower() in IMG:
                my_logger.logger.debug("🖼️ 响应类型: 图片")
                my_logger.logger.debug(f"📦 响应大小: {len(r.content)} bytes")
            else:
                r.encoding = "utf-8"
                text = handle_unicode_text(r.text)
                my_logger.logger.debug("📄 响应类型: 文本")
                my_logger.logger.debug(f"📝 响应内容:\n{text}")

        # 处理cookies
        if r.cookies:
            cookies_dict = requests.utils.dict_from_cookiejar(r.cookies)
            my_logger.logger.debug(f"🍪 Cookies:\n{formatting(cookies_dict)}")

        # 请求结束分隔符
        my_logger.logger.info('-' * 50)
        my_logger.logger.info('✨ 请求完成')
        my_logger.logger.info('=' * 50)

        return r

    return wrapper


@my_logger.runtime_logger_class
class Session(RequestsSession):
    """
    HTTP会话管理类

    扩展requests.Session类，提供额外的功能：
        - 支持基础URL配置
        - 统一的超时和SSL验证设置
        - 自动重试机制
        - 所有请求方法的装饰器增强

    Args:
        base_url: 基础URL，所有相对路径都将基于此URL
        timeout: 请求超时时间（秒）
        verify: 是否验证SSL证书
        max_retries: 请求失败时的最大重试次数
        retry_delay: 重试间隔时间（秒）

    Example:
        >>> session = Session(base_url="http://api.example.com")
        >>> response = session.get("/users")
    """

    @my_logger.runtime_logger
    def __init__(self, base_url: Optional[str] = None,
                 timeout: int = 10,
                 verify: bool = False,
                 max_retries: int = 0,
                 retry_delay: int = 3):
        """
        初始化会话对象

        Args:
            base_url: 基础URL
            timeout: 超时时间(秒)
            verify: 是否验证SSL证书
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)

        Example:
            >>> session = Session(base_url="http://api.example.com", timeout=30)
        """
        super().__init__()
        my_logger.logger.info("🔄 初始化 Session")
        my_logger.logger.info(f"📍 基础URL: {base_url}")
        my_logger.logger.info(f"⏱️ 超时设置: {timeout}秒")
        my_logger.logger.info(f"🔐 SSL验证: {'启用' if verify else '禁用'}")
        my_logger.logger.info(f"🔄 最大重试次数: {max_retries}")
        my_logger.logger.info(f"⏲️ 重试延迟: {retry_delay}秒")

        self.base_url = base_url
        self.timeout = timeout
        self.verify = verify
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # 设置重试策略
        if max_retries > 0:
            retry = Retry(
                total=max_retries,
                backoff_factor=retry_delay,
                status_forcelist=[500, 502, 503, 504]
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.mount('http://', adapter)
            self.mount('https://', adapter)

    @my_logger.runtime_logger
    def _build_url(self, url: str) -> str:
        """
        根据基础URL构建完整的请求URL

        Args:
            url: 相对URL或绝对URL

        Returns:
            str: 拼接后的完整URL（如果是绝对URL，则直接返回）

        Example:
            >>> url = session._build_url("/users")
            >>> print(url)  # http://api.example.com/users
        """
        my_logger.logger.debug(f"🔄 构建完整URL")
        my_logger.logger.debug(f"📥 输入URL: {url}")
        result = url
        if self.base_url and not url.startswith(('http://', 'https://')):
            result = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        my_logger.logger.debug(f"📤 完整URL: {result}")
        return result

    @request
    def get(self, url: str, **kwargs: Any) -> Response:
        """
        发送GET请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.get("/users")
        """
        url = self._build_url(url)
        return super().get(url, **kwargs)

    @request
    def post(self, url: str, data: Optional[Union[Dict[str, Any], str]] = None,
             json_data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Response:
        """
        发送POST请求

        Args:
            url: 请求URL
            data: 请求数据
            json_data: JSON格式的请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.post("/login", json={"username": "test"})
        """
        url = self._build_url(url)
        return super().post(url, data=data, json=json_data, **kwargs)

    @request
    def put(self, url: str, data: Optional[Union[Dict, str]] = None,
            **kwargs: Any) -> Response:
        """
        发送PUT请求

        Args:
            url: 请求URL
            data: 请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.put("/users", json={"name": "test"})
        """
        url = self._build_url(url)
        return super().put(url, data=data, **kwargs)

    @request
    def delete(self, url: str, **kwargs: Any) -> Response:
        """
        发送DELETE请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.delete("/users")
        """
        url = self._build_url(url)
        return super().delete(url, **kwargs)

    @request
    def patch(self, url: str, data: Optional[Union[Dict, str]] = None,
              **kwargs: Any) -> Response:
        """
        发送PATCH请求

        Args:
            url: 请求URL
            data: 请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.patch("/users", json={"name": "test"})
        """
        url = self._build_url(url)
        return super().patch(url, data=data, **kwargs)

    @request
    def head(self, url: str, **kwargs: Any) -> Response:
        """
        发送HEAD请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.head("/users")
        """
        url = self._build_url(url)
        return super().head(url, **kwargs)

    @request
    def options(self, url: str, **kwargs: Any) -> Response:
        """
        发送OPTIONS请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = session.options("/users")
        """
        url = self._build_url(url)
        return super().options(url, **kwargs)


@my_logger.runtime_logger_class
class HttpRequest:
    """
    HTTP请求客户端类

    提供统一的HTTP请求接口，支持：
        - 会话管理
        - 基础URL配置
        - 代理设置
        - 请求/响应日志记录
        - curl命令生成

    Args:
        base_url: 基础URL，所有相对路径都将基于此URL
        use_session: 是否使用会话保持
        proxies: 代理服务器配置字典

    Methods:
        get(): 发送GET请求
        post(): 发送POST请求
        put(): 发送PUT请求
        delete(): 发送DELETE请求
        patch(): 发送PATCH请求
        head(): 发送HEAD请求
        options(): 发送OPTIONS请求

    Properties:
        response: 获取最近的响应对象
        status_code: 获取最近的响应状态码

    Example:
        >>> client = HttpRequest(base_url="http://api.example.com")
        >>> response = client.get("/users")
        >>> print(client.status_code)
    """

    client: Union[Session, ModuleType]  # 用于表示 Session 实例或 requests 模块

    @my_logger.runtime_logger
    def __init__(self, base_url: Optional[str] = None, use_session: bool = False,
                 proxies: Optional[Dict[str, str]] = None):
        my_logger.logger.info("🔄 初始化 HttpRequest")
        my_logger.logger.info(f"📍 基础URL: {base_url}")
        my_logger.logger.info(f"📌 会话模式: {'启用' if use_session else '禁用'}")
        if proxies:
            my_logger.logger.info(f"🔒 代理设置:\n{formatting(proxies)}")

        self.base_url: Optional[str] = base_url
        if use_session:
            self.client = Session(base_url=base_url)
            if proxies:
                self.client.proxies.update(proxies)
        else:
            self.client = requests

    @my_logger.runtime_logger
    def _build_url(self, url: str) -> str:
        """
        构建完整的请求URL

        Args:
            url: 相对或绝对URL

        Returns:
            str: 完整的URL

        Example:
            >>> url = client._build_url("/users")
            >>> print(url)  # http://api.example.com/users
        """
        my_logger.logger.debug("🔄 构建完整URL")
        my_logger.logger.debug(f"📥 输入URL: {url}")
        result = url
        if self.base_url and not url.startswith(('http://', 'https://')):
            result = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        my_logger.logger.debug(f"📤 完整URL: {result}")
        return result

    @request
    def get(self, url: str, **kwargs: Any) -> Response:
        """
        发送GET请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.get("/users")
        """
        url = self._build_url(url)
        return self.client.get(url, **kwargs)

    @request
    def post(self, url: str, data: Optional[Union[Dict, str]] = None,
             json_data: Optional[Dict] = None, **kwargs: Any) -> Response:
        """
        发送POST请求

        Args:
            url: 请求URL
            data: 请求数据
            json_data: JSON格式的请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.post("/login", json={"username": "test"})
        """
        url = self._build_url(url)
        return self.client.post(url, data=data, json=json_data, **kwargs)

    @request
    def put(self, url: str, data: Optional[Union[Dict, str]] = None,
            **kwargs: Any) -> Response:
        """
        发送PUT请求

        Args:
            url: 请求URL
            data: 请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.put("/users", json={"name": "test"})
        """
        url = self._build_url(url)
        return self.client.put(url, data=data, **kwargs)

    @request
    def delete(self, url: str, **kwargs: Any) -> Response:
        """
        发送DELETE请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.delete("/users")
        """
        url = self._build_url(url)
        return self.client.delete(url, **kwargs)

    @request
    def patch(self, url: str, data: Optional[Union[Dict, str]] = None,
              **kwargs: Any) -> Response:
        """
        发送PATCH请求

        Args:
            url: 请求URL
            data: 请求数据
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.patch("/users", json={"name": "test"})
        """
        url = self._build_url(url)
        return self.client.patch(url, data=data, **kwargs)

    @request
    def head(self, url: str, **kwargs: Any) -> Response:
        """
        发送HEAD请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.head("/users")
        """
        url = self._build_url(url)
        return self.client.head(url, **kwargs)

    @request
    def options(self, url: str, **kwargs: Any) -> Response:
        """
        发送OPTIONS请求

        Args:
            url: 请求URL
            **kwargs: 其他请求参数

        Returns:
            Response: 请求响应对象

        Example:
            >>> response = client.options("/users")
        """
        url = self._build_url(url)
        return self.client.options(url, **kwargs)

    @property
    @my_logger.runtime_logger
    def response(self) -> Optional[Response]:
        """
        获取最近的响应对象

        Returns:
            Optional[Response]: 最近的响应对象，如果没有则返回 None

        Example:
            >>> response = client.response
        """
        response = ResponseResult.get_response()
        my_logger.logger.debug(f"📤 获取响应对象: {'成功' if response else '无响应'}")
        return response

    @property
    @my_logger.runtime_logger
    def status_code(self) -> Union[int, None]:
        """
        获取最近的响应状态码

        Returns:
            Union[int, None]: 最近响应的状态码，如果没有响应则返回 None

        Example:
            >>> status = client.status_code
        """
        response = self.response
        status = response.status_code if response else None
        my_logger.logger.debug(f"📤 获取状态码: {status}")
        return status

    @staticmethod
    @my_logger.runtime_logger
    def curl(req: Optional[PreparedRequest] = None, compressed: bool = False, verify: bool = True) -> str:
        """
        获取请求的curl命令

        Args:
            req: 请求对象，默认使用最近的请求
            compressed: 是否添加压缩参数
            verify: 是否验证SSL证书

        Returns:
            str: curl命令字符串

        Raises:
            ValueError: 如果没有可用的请求对象

        Example:
            >>> curl_cmd = client.curl()
            >>> print(curl_cmd)
        """
        my_logger.logger.info("🔄 生成 curl 命令")
        if req is None:
            req = ResponseResult.get_request()
            my_logger.logger.debug("📝 使用最近的请求对象")

        if req is None:
            raise ValueError("No request object available")

        result = to_curl(req, compressed, verify)
        my_logger.logger.debug("✅ curl 命令生成完成")
        return result
