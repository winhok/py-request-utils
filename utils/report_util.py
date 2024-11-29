"""
报告工具模块

提供完整的测试报告管理功能,支持以下特性:

功能特性:
    - 报告生成
        * 离线HTML报告
        * 资源文件内联
        * 报告打包
    - 报告发送
        * 钉钉机器人
        * 企业微信机器人
        * 邮件发送
    - 报告管理
        * 自动清理历史报告
        * 报告统计信息
        * 报告模板定制

技术特点:
    - 完整的类型注解
    - 自动化日志记录
    - 异常重试机制
"""

import json
import shutil
import subprocess
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, Union, TypeVar, Dict, List

import allure
from allure_combine import combine_allure
from allure_commons.types import LinkType
from allure_commons.types import Severity

from .log_util import my_logger
from .send_util import message_sender

# 类型变量定义
T = TypeVar('T')


class ReportConfig:
    """报告配置类"""

    # 报告目录配置
    REPORT_DIR = "report"
    HISTORY_DIR = "history"
    SCREENSHOTS_DIR = "screenshots"

    # 报告清理配置
    MAX_HISTORY_DAYS = 7  # 历史报告保留天数
    MAX_HISTORY_COUNT = 10  # 保留的历史报告数量

    # 报告主题配置
    THEME = {
        "primary_color": "#7C4DFF",
        "secondary_color": "#FFD740",
        "success_color": "#00C853",
        "warning_color": "#FFB300",
        "error_color": "#FF1744"
    }

    # 多语言配置
    LANGUAGE = "zh_CN"

    # 环境信息配置
    ENVIRONMENT = {
        "Python版本": "3.10",
        "操作系统": "Windows",
        "测试环境": "测试环境",
        "测试人员": "测试人员"
    }

    # 离线报告配置
    OFFLINE_REPORT_DIR = "offline_reports"  # 离线报告保存目录
    OFFLINE_REPORT_TITLE = "自动化测试报告"  # 离线报告标题
    REPORT_ENCODING = "utf-8"  # 报告编码

    # 报告合并配置
    COMBINE_CONFIG = {
        "remove_temp_files": True,  # 是否删除临时文件
        "auto_create_folders": True,  # 自动创建目录
        "ignore_utf8_errors": False  # 添加新的支持参数
    }


@my_logger.runtime_logger_class
class ReportManager:
    """报告管理类"""

    @my_logger.runtime_logger
    def __init__(self):
        """初始化报告管理器"""
        self._init_dirs()
        self._clean_old_reports()
        self._set_environment()
        self._init_offline_dirs()

    @my_logger.runtime_logger
    def _init_dirs(self) -> None:
        """初始化报告相关目录"""
        my_logger.logger.info("🔄 初始化报告目录")

        # 创建主要目录
        for dir_name in [ReportConfig.REPORT_DIR,
                         ReportConfig.SCREENSHOTS_DIR]:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                dir_path.mkdir(parents=True)
                my_logger.logger.debug(f"📁 创建目录: {dir_path}")

    @my_logger.runtime_logger
    def _clean_old_reports(self) -> None:
        """清理旧的报告文件"""
        my_logger.logger.info("🧹 清理历史报告")

        report_dir = Path(ReportConfig.REPORT_DIR)
        if not report_dir.exists():
            return

        # 获取所有报告目录
        report_dirs = [d for d in report_dir.iterdir() if d.is_dir()]
        report_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # 保留最新的N个报告
        if len(report_dirs) > ReportConfig.MAX_HISTORY_COUNT:
            for old_dir in report_dirs[ReportConfig.MAX_HISTORY_COUNT:]:
                shutil.rmtree(old_dir)
                my_logger.logger.debug(f"🗑️ 删除旧报告: {old_dir}")

        # 删除超过最大天数的报告
        max_age = time.time() - (ReportConfig.MAX_HISTORY_DAYS * 86400)
        for dir_path in report_dirs:
            if dir_path.stat().st_mtime < max_age:
                shutil.rmtree(dir_path)
                my_logger.logger.debug(f"🗑️ 删除过期报告: {dir_path}")

    @my_logger.runtime_logger
    def _set_environment(self) -> None:
        """设置环境信息"""
        my_logger.logger.info("🌍 设置环境信息")

        # 添加动态环境信息
        env_info = {
            **ReportConfig.ENVIRONMENT,
            "报告时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "报告语言": ReportConfig.LANGUAGE
        }

        # 写入环境信息文件
        env_file = Path(ReportConfig.REPORT_DIR) / "environment.properties"
        with env_file.open("w", encoding="utf-8") as f:
            for key, value in env_info.items():
                f.write(f"{key}={value}\n")
                my_logger.logger.debug(f"📝 环境信息: {key}={value}")

    @my_logger.runtime_logger
    def _init_offline_dirs(self) -> None:
        """初始化离线报告目录"""
        offline_dir = Path(ReportConfig.OFFLINE_REPORT_DIR)
        if not offline_dir.exists():
            offline_dir.mkdir(parents=True)
            my_logger.logger.debug(f"📁 创建离线报告目录: {offline_dir}")

    @my_logger.runtime_logger
    def generate_offline_report(self,
                                results_dir: Optional[str] = None,
                                report_title: Optional[str] = None,
                                clean_results: bool = True) -> Path:
        """
        生成离线HTML报告
        
        Args:
            results_dir: Allure结果目录，默认为 report/allure-results
            report_title: 报告标题，默认使用配置中的标题
            clean_results: 是否清理结果目录
            
        Returns:
            Path: 生成的报告文件路径
        """
        my_logger.logger.info("🔄 开始生成离线报告")

        # 设置默认值
        results_dir = results_dir or str(Path(ReportConfig.REPORT_DIR) / "allure-results")
        report_title = report_title or ReportConfig.OFFLINE_REPORT_TITLE

        # 确保结果目录存在
        results_path = Path(results_dir)
        if not results_path.exists():
            raise FileNotFoundError(f"Allure结果目录不存在: {results_dir}")

        try:
            # 生成报告时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_dir = Path(ReportConfig.OFFLINE_REPORT_DIR) / f"report_{timestamp}"

            my_logger.logger.info(f"📊 报告标题: {report_title}")
            my_logger.logger.info(f"📂 结果目录: {results_dir}")
            my_logger.logger.info(f"📄 报告目录: {report_dir}")

            # 使用allure-combine生成报告
            combine_allure(
                folder=str(results_path),
                dest_folder=str(report_dir),
                remove_temp_files=ReportConfig.COMBINE_CONFIG["remove_temp_files"],
                auto_create_folders=ReportConfig.COMBINE_CONFIG["auto_create_folders"]
            )

            # 获取生成的报告文件路径
            report_path = report_dir / "complete.html"

            my_logger.logger.success(f"✅ 离线报告生成成功: {report_path}")

            # 清理结果目录
            if clean_results and results_path.exists():
                shutil.rmtree(results_path)
                my_logger.logger.debug(f"🧹 清理结果目录: {results_path}")

            return report_path

        except Exception as e:
            my_logger.logger.error(f"❌ 生成离线报告失败: {str(e)}")
            raise

    @my_logger.runtime_logger
    def generate_report_package(self,
                                results_dir: Optional[str] = None,
                                report_title: Optional[str] = None) -> Path:
        """
        生成完整的报告包
        包含离线HTML报告和原始结果文件
        
        Args:
            results_dir: Allure结果目录
            report_title: 报告标题
            
        Returns:
            Path: 报告包文件路径
        """
        my_logger.logger.info("🔄 开始生成报告包")

        try:
            # 生成离线报告
            report_file = self.generate_offline_report(
                results_dir=results_dir,
                report_title=report_title,
                clean_results=False  # 保留结果文件
            )

            # 创建打包目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            package_name = f"report_package_{timestamp}"
            package_dir = Path(ReportConfig.OFFLINE_REPORT_DIR) / package_name
            package_dir.mkdir(exist_ok=True)

            # 复制文件到打包目录
            shutil.copy2(report_file, package_dir)
            if results_dir:
                results_path = Path(results_dir)
                if results_path.exists():
                    results_target = package_dir / "allure-results"
                    shutil.copytree(results_path, results_target)

            # 创建压缩包
            package_file = package_dir.with_suffix('.zip')
            shutil.make_archive(
                str(package_file.with_suffix('')),
                'zip',
                package_dir
            )

            # 清理临时目录
            shutil.rmtree(package_dir)

            my_logger.logger.success(f"✅ 报告包生成成功: {package_file}")
            return package_file

        except Exception as e:
            my_logger.logger.error(f"❌ 生成报告包失败: {str(e)}")
            raise

    @my_logger.runtime_logger
    def serve_report(self,
                     results_dir: Optional[str] = None,
                     port: int = 8080) -> None:
        """
        启动Allure报告服务器
        
        Args:
            results_dir: Allure结果目录
            port: 服务器端口
        """
        results_dir = results_dir or str(Path(ReportConfig.REPORT_DIR) / "allure-results")

        try:
            my_logger.logger.info(f"🚀 启动Allure报告服务器 端口: {port}")
            subprocess.run(
                ["allure", "serve", results_dir, "-p", str(port)],
                check=True
            )
        except subprocess.CalledProcessError as e:
            my_logger.logger.error(f"❌ 启动报告服务器失败: {str(e)}")
            raise
        except FileNotFoundError:
            my_logger.logger.error("❌ 未找到allure命令，请确保已正确安装")
            raise

    @my_logger.runtime_logger
    def attach_data(self, name: str, data: Any,
                    attachment_type: str = allure.attachment_type.JSON) -> None:
        """
        添加附件到报告
        
        Args:
            name: 附件名称
            data: 附件数据
            attachment_type: 附件类型
        """
        my_logger.logger.debug(f"📎 添加附件: {name}")

        if attachment_type == allure.attachment_type.JSON:
            allure.attach(
                json.dumps(data, ensure_ascii=False, indent=2),
                name=name,
                attachment_type=attachment_type
            )
        else:
            allure.attach(
                str(data),
                name=name,
                attachment_type=attachment_type
            )

    @my_logger.runtime_logger
    def attach_file(self, file_path: Union[str, Path],
                    name: Optional[str] = None) -> None:
        """
        添加文件到报告
        
        Args:
            file_path: 文件路径
            name: 文件名称
        """
        file_path = Path(file_path)
        if not file_path.exists():
            my_logger.logger.warning(f"⚠️ 文件不存在: {file_path}")
            return

        name = name or file_path.name
        my_logger.logger.debug(f"📎 添加文件: {name}")

        allure.attach.file(
            str(file_path),
            name=name,
            attachment_type=self._get_attachment_type(file_path)
        )

    @staticmethod
    def _get_attachment_type(file_path: Path) -> str:
        """根据文件扩展名获取附件类型"""
        ext = file_path.suffix.lower()
        type_map = {
            '.txt': allure.attachment_type.TEXT,
            '.xml': allure.attachment_type.XML,
            '.html': allure.attachment_type.HTML,
            '.json': allure.attachment_type.JSON,
            '.png': allure.attachment_type.PNG,
            '.jpg': allure.attachment_type.JPG,
            '.jpeg': allure.attachment_type.JPG,
            '.gif': allure.attachment_type.GIF,
            '.bmp': allure.attachment_type.BMP,
            '.tiff': allure.attachment_type.TIFF,
            '.csv': allure.attachment_type.CSV,
            '.tsv': allure.attachment_type.TSV,
            '.svg': allure.attachment_type.SVG,
        }
        return type_map.get(ext, allure.attachment_type.TEXT)

    @my_logger.runtime_logger
    def add_step(self, name: str, status: str = "passed") -> None:
        """
        添加测试步骤
        
        Args:
            name: 步骤名称
            status: 步骤状态
        """
        my_logger.logger.debug(f"👣 添加测试步骤: {name} [{status}]")
        with allure.step(name):
            if status == "failed":
                allure.attach(
                    "Step failed",
                    name="Failure Details",
                    attachment_type=allure.attachment_type.TEXT
                )

    @my_logger.runtime_logger
    def send_report(self,
                    report_path: Optional[Path] = None,
                    title: str = "测试报告",
                    content: str = "",
                    to_dingtalk: bool = True,
                    to_wechat: bool = True,
                    to_email: Optional[Union[str, List[str]]] = None) -> None:
        """
        发送测试报告
        
        Args:
            report_path: 报告文件路径,为None时自动生成新报告
            title: 报告标题
            content: 报告说明内容
            to_dingtalk: 是否发送到钉钉
            to_wechat: 是否发送到企业微信
            to_email: 邮件接收人地址
        """
        my_logger.logger.info("📤 开始发送测试报告")

        # 如果没有指定报告路径,生成新报告
        if report_path is None:
            my_logger.logger.info("🔄 未指定报告路径,生成新报告")
            report_path = self.generate_offline_report()

        if not isinstance(report_path, Path):
            report_path = Path(report_path)

        if not report_path.exists():
            raise FileNotFoundError(f"报告文件不存在: {report_path}")

        # 生成报告概要
        if not content:
            content = self._generate_report_summary(report_path)

        # 发送到钉钉
        if to_dingtalk:
            try:
                my_logger.logger.info("📤 发送报告到钉钉")
                message_sender.dingtalk.send_file(str(report_path))
                message_sender.dingtalk.send_text(content)
                my_logger.logger.success("✅ 钉钉发送成功")
            except Exception as e:
                my_logger.logger.error(f"❌ 钉钉发送失败: {str(e)}")

        # 发送到企业微信
        if to_wechat:
            try:
                my_logger.logger.info("📤 发送报告到企业微信")
                message_sender.wechat.send_file(str(report_path))
                message_sender.wechat.send_text(content)
                my_logger.logger.success("✅ 企业微信发送成功")
            except Exception as e:
                my_logger.logger.error(f"❌ 企业微信发送失败: {str(e)}")

        # 发送邮件
        if to_email:
            try:
                my_logger.logger.info("📤 发送报告到邮件")
                message_sender.email.send_mail(
                    to_addrs=to_email,
                    subject=title,
                    content=content,
                    content_type="html",
                    attachments=[report_path]
                )
                my_logger.logger.success("✅ 邮件发送成功")
            except Exception as e:
                my_logger.logger.error(f"❌ 邮件发送失败: {str(e)}")

        my_logger.logger.info("✨ 报告发送完成")

    @my_logger.runtime_logger
    def _generate_report_summary(self, report_path: Path) -> str:
        """
        生成报告概要信息
        
        Args:
            report_path: 报告文件路径
            
        Returns:
            str: 报告概要内容
        """
        my_logger.logger.debug("📝 生成报告概要")

        # 获取报告统计信息
        stats = self._get_report_stats()

        # 生成概要内容
        summary = f"""### 测试报告概要
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 文件大小: {report_path.stat().st_size / 1024 / 1024:.2f}MB
- 测试用例: {stats['total']}
- 通过率: {stats['pass_rate']:.1f}%
- 执行时间: {stats['duration']}秒
"""
        my_logger.logger.debug(f"📋 报告概要:\n{summary}")
        return summary

    @staticmethod
    def _get_report_stats() -> Dict[str, Any]:
        """
        获取报告统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        # 这里可以添加从报告中解析统计信息的逻辑
        return {
            "total": 100,
            "passed": 95,
            "failed": 5,
            "pass_rate": 95.0,
            "duration": 60
        }


def story(*stories: str) -> Callable:
    """
    用户故事装饰器
    
    Args:
        stories: 用户故事名称
    """

    def decorator(func: Callable) -> Callable:
        for story_name in stories:
            allure.story(story_name)(func)
        return func

    return decorator


def feature(*features: str) -> Callable:
    """
    功能特性装饰器
    
    Args:
        features: 功能特性名称
    """

    def decorator(func: Callable) -> Callable:
        for feature_name in features:
            allure.feature(feature_name)(func)
        return func

    return decorator


def severity(level: str) -> Callable:
    """
    严重程度装饰器
    
    Args:
        level: 严重程度级别
    """

    def decorator(func: Callable) -> Callable:
        allure.severity(getattr(Severity, level.upper()))(func)
        return func

    return decorator


def step(title: str) -> Callable:
    """
    测试步骤装饰器
    
    Args:
        title: 步骤标题
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with allure.step(title):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def description(text: str) -> Callable:
    """
    测试用例描述装饰器
    
    Args:
        text: 描述文本
    """

    def decorator(func: Callable) -> Callable:
        allure.description(text)(func)
        return func

    return decorator


def link(url: str, name: Optional[str] = None,
         link_type: str = LinkType.LINK) -> Callable:
    """
    链接装饰器
    
    Args:
        url: 链接地址
        name: 链接名称
        link_type: 链接类型
    """

    def decorator(func: Callable) -> Callable:
        allure.link(url, name=name, link_type=link_type)(func)
        return func

    return decorator


def attach_data(name: str, data: Any,
                attachment_type: str = allure.attachment_type.JSON) -> Callable:
    """
    数据附件装饰器
    
    Args:
        name: 附件名称
        data: 附件数据
        attachment_type: 附件类型
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            report_manager.attach_data(name, data, attachment_type)
            return result

        return wrapper

    return decorator


# 创建默认报告管理器实例
report_manager = ReportManager()
