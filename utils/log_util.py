"""
日志工具模块

提供完整的日志管理功能，支持以下特性：

功能特性:
    - 控制台和文件双重输出
    - 彩色日志支持
    - 自动日志文件管理
        * 自动创建日志目录
        * 日志文件自动切割
        * 日志文件自动清理
    - 运行时日志装饰器
        * 函数执行时间统计
        * 异常自动捕获和记录
    
技术特点:
    - 基于 loguru 实现
    - 支持动态配置
    - 完整的类型注解
    - 装饰器模式支持

使用示例:
    >>> # 基本使用
    >>> from utils.log_util import my_logger
    >>> my_logger.logger.info("这是一条信息")
    
    >>> # 装饰器使用
    >>> @my_logger.runtime_logger
    ... def some_function():
    ...     pass
"""

import os
import sys
import time
from functools import wraps
from types import FunctionType
from typing import Callable, TypeVar, Optional, ParamSpec, Type
from typing import cast

from loguru import logger, Logger

# 定义泛型类型变量
P = ParamSpec('P')  # 用于参数规范
R = TypeVar('R')  # 用于返回值类型
T = TypeVar('T')  # 用于类类型


class LogConfig:
    """日志配置类

    集中管理日志相关的配置参数

    Attributes:
        LOG_PATH: 日志文件路径
        DEFAULT_LEVEL: 默认日志级别
        CONSOLE_FORMAT: 控制台日志格式
        FILE_FORMAT: 文件日志格式
        ROTATION: 日志文件切割大小
        RETENTION: 日志保留时间
    """
    LOG_PATH: Optional[str] = None
    DEFAULT_LEVEL: str = "DEBUG"
    CONSOLE_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {thread.name} | {message}"
    FILE_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {thread.name} | {message}"
    ROTATION: str = "5 MB"
    RETENTION: str = "1 week"


class LoggerManager:
    """日志管理类

    提供完整的日志管理功能，包括日志配置、输出和装饰器支持

    Attributes:
        logger: loguru 日志器实例
        log_dir: 日志目录路径
        report_dir: 报告目录路径
        log_file: 日志文件路径
        _colorlog: 是否启用彩色日志
        _console_format: 控制台日志格式
        _file_format: 文件日志格式
        _level: 日志级别

    Methods:
        configure_logging(): 配置日志设置
        runtime_logger(): 函数运行时日志装饰器
        runtime_logger_class(): 类方法运行时日志装饰器
        set_level(): 动态设置日志级别
    """

    def __init__(self, level: str = LogConfig.DEFAULT_LEVEL, colorlog: bool = True) -> None:
        """初始化日志管理器

        Args:
            level: 日志级别，默认使用 LogConfig.DEFAULT_LEVEL
            colorlog: 是否启用彩色日志，默认为 True

        Example:
            >>> logger_manager = LoggerManager(level="DEBUG", colorlog=True)
        """
        self.logger: Logger = logger
        logger.remove()

        # 自动创建日志目录
        self._create_log_dirs()

        # 清空已存在的日志文件
        self._clear_log_file()

        # 设置默认配置
        self._colorlog = colorlog
        self._console_format = LogConfig.CONSOLE_FORMAT
        self._file_format = LogConfig.FILE_FORMAT
        self._level = level

        # 配置日志
        self.configure_logging()

    def _create_log_dirs(self) -> None:
        """
        创建日志和报告目录

        自动创建必要的目录结构，包括:
            - 日志目录: ./log
            - 报告目录: ./report

        Note:
            目录将创建在项目根目录下
        """
        # 获取项目根目录路径
        current_dir = os.path.dirname(os.path.dirname(__file__))

        # 设置日志目录为 ./log
        self.log_dir: str = os.path.join(current_dir, "log")
        # 设置报告目录为 ./report
        self.report_dir: str = os.path.join(current_dir, "report")

        # 创建目录
        for dir_path in [self.log_dir, self.report_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # 创建日志文件路径
        self.log_file: str = os.path.join(
            self.log_dir, f"{time.strftime('%Y%m%d-%H%M%S')}.log")

    def _clear_log_file(self) -> None:
        """
        清空日志文件

        如果日志文件已存在，则清空其内容
        """
        if os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate(0)

    def configure_logging(self,
                          console_format: str = "",
                          file_format: str = "",
                          level: str = "",
                          rotation: str = LogConfig.ROTATION,
                          retention: str = LogConfig.RETENTION) -> None:
        """
        配置日志设置

        Args:
            console_format: 控制台日志格式，为空时使用默认格式
            file_format: 文件日志格式，为空时使用默认格式
            level: 日志级别，为空时使用默认级别
            rotation: 日志文件切割大小，默认为 LogConfig.ROTATION
            retention: 日志保留时间，默认为 LogConfig.RETENTION

        Note:
            - 同时配置控制台和文件两个输出处理器
            - 支持日志文件的自动切割和清理

        Example:
            >>> logger_manager.configure_logging(
            ...     level="DEBUG",
            ...     rotation="10 MB",
            ...     retention="1 week"
            ... )
        """
        self.logger.remove()  # 清除所有处理器

        # 使用传入的参数或默认值
        console_format = console_format or self._console_format
        file_format = file_format or self._file_format
        level = level or self._level

        # 添加控制台处理器
        self.logger.add(
            sys.stderr,
            format=console_format,
            level=level,
            colorize=self._colorlog,
            backtrace=True,
            diagnose=True
        )

        # 添加文件处理器
        self.logger.add(
            self.log_file,
            format=file_format,
            level=level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )

    def runtime_logger(self, func: Callable[P, R]) -> Callable[P, R]:
        """
        函数运行时日志装饰器

        为函数添加运行时日志，记录:
            - 函数开始执行
            - 执行耗时
            - 执行结果
            - 异常信息(如果发生)

        Args:
            func: 要装饰的函数

        Returns:
            装饰后的函数

        Raises:
            Exception: 保持原函数抛出的异常，但会记录到日志中

        Example:
            >>> @my_logger.runtime_logger
            ... def some_function():
            ...     pass
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            actual_func = cast(FunctionType, func)
            # 获取更详细的函数信息
            module_name = actual_func.__module__
            func_name = actual_func.__name__

            self.logger.info(f"开始执行: {module_name}.{func_name}")
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000
                self.logger.success(
                    f"执行成功: {module_name}.{func_name} | 耗时: {execution_time:.2f}ms")
                return result
            except Exception as e:
                self.logger.error(
                    f"执行失败: {module_name}.{func_name} | 错误: {str(e)}")
                raise e

        return wrapper

    def runtime_logger_class(self, cls: Type[T]) -> Type[T]:
        """
        类方法运行时日志装饰器

        为类的测试方法添加运行时日志

        Args:
            cls: 要装饰的类

        Returns:
            装饰后的类

        Note:
            - 只装饰以 test_ 开头的方法
            - 使用 runtime_logger 装饰每个测试方法

        Example:
            >>> @my_logger.runtime_logger_class
            ... class TestClass:
            ...     def test_method(self):
            ...         pass
        """
        for attr_name in dir(cls):
            if attr_name.startswith('test_') and callable(getattr(cls, attr_name)):
                setattr(cls, attr_name, self.runtime_logger(
                    getattr(cls, attr_name)))
        return cls

    def set_level(self, level: str) -> None:
        """
        动态设置日志级别

        Args:
            level: 新的日志级别

        Note:
            会重新配置所有日志处理器

        Example:
            >>> my_logger.set_level("DEBUG")
        """
        self._level = level
        self.configure_logging(level=level)


# 创建默认日志管理器实例
my_logger = LoggerManager()
