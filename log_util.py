import sys
import time
import os
from typing import Any, Callable, TypeVar, cast, Optional
from loguru import logger
from functools import wraps

# 定义泛型类型变量
F = TypeVar('F', bound=Callable[..., Any])


class LogConfig:
    """日志配置类"""
    LOG_PATH: Optional[str] = None
    DEFAULT_LEVEL: str = "DEBUG"
    CONSOLE_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {thread.name} | {message}"
    FILE_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {thread.name} | {message}"
    ROTATION: str = "5 MB"
    RETENTION: str = "1 week"


class LoggerManager:
    """日志管理类"""

    def __init__(self, level: str = LogConfig.DEFAULT_LEVEL, colorlog: bool = True) -> None:
        """
        初始化日志管理器
        :param level: 日志级别
        :param colorlog: 是否启用彩色日志
        """
        self.logger = logger
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
        """创建日志和报告目录"""
        # 获取项目根目录路径
        current_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))))

        # 设置日志目录为 src/zrlog_test/log
        self.log_dir = os.path.join(current_dir, "src", "zrlog_test", "log")
        # 设置报告目录
        self.report_dir = os.path.join(current_dir, "report")

        # 创建目录
        for dir_path in [self.log_dir, self.report_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # 创建日志文件路径
        self.log_file = os.path.join(
            self.log_dir, f"{time.strftime('%Y%m%d-%H%M%S')}.log")

    def _clear_log_file(self) -> None:
        """清空日志文件"""
        if os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate(0)

    def configure_logging(self,
                          console_format: str = None,
                          file_format: str = None,
                          level: str = None,
                          rotation: str = LogConfig.ROTATION,
                          retention: str = LogConfig.RETENTION) -> None:
        """
        配置日志设置
        :param console_format: 控制台日志格式
        :param file_format: 文件日志格式
        :param level: 日志级别
        :param rotation: 日志文件切割大小
        :param retention: 日志保留时间
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

    def runtime_logger(self, func: F) -> F:
        """函数运行时日志装饰器"""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 获取更详细的函数信息
            module_name = func.__module__
            func_name = func.__name__

            self.logger.info(f"开始执行: {module_name}.{func_name}")
            start_time = time.time()
            result: Optional[Any] = None

            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = (end_time - start_time) * 1000  # 转换为毫秒
                self.logger.success(
                    f"执行成功: {module_name}.{func_name} | 耗时: {execution_time:.2f}ms")
            except Exception as e:
                self.logger.error(
                    f"执行失败: {module_name}.{func_name} | 错误: {str(e)}")
                raise e

            return result
        return cast(F, wrapper)

    def runtime_logger_class(self, cls: Any) -> Any:
        """类方法运行时日志装饰器"""
        for attr_name in dir(cls):
            if attr_name.startswith('test_') and callable(getattr(cls, attr_name)):
                setattr(cls, attr_name, self.runtime_logger(
                    getattr(cls, attr_name)))
        return cls

    def set_level(self, level: str) -> None:
        """动态设置日志级别"""
        self._level = level
        self.configure_logging(level=level)


# 创建默认日志管理器实例
my_logger = LoggerManager()
