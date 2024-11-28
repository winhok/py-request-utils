"""
断言工具模块

提供完整的断言管理功能，支持以下特性：

功能特性:
    - 断言结果管理
        * 自动记录断言结果
        * 支持批量验证
    - 丰富的断言方法
        * 相等性断言
        * 包含关系断言
        * 类型检查断言
    - 自定义错误消息

技术特点:
    - 完整的类型注解
    - 装饰器模式支持
    - 链式调用支持
    - 自动化日志记录
"""
import json
import operator
from functools import wraps
from typing import (
    Any, Optional, List, Dict, Union, Protocol, Callable, Literal,
    TypeVar, Generic, cast, runtime_checkable
)

import jmespath
import pytest
from deepdiff import DeepDiff
from jsonschema import validate, ValidationError

from .log_util import my_logger


@runtime_checkable
class SupportsRichComparison(Protocol):
    """支持富比较操作的协议"""

    def __lt__(self, other: Any) -> bool: ...

    def __le__(self, other: Any) -> bool: ...

    def __gt__(self, other: Any) -> bool: ...

    def __ge__(self, other: Any) -> bool: ...

    def __eq__(self, other: object) -> bool: ...

    def __ne__(self, other: object) -> bool: ...


T = TypeVar('T')
V = TypeVar('V')

JsonScalarType = Union[str, int, float, bool, None]
JsonType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
"""
JSON 数据类型

支持的数据类型:
    - Dict[str, Any]: JSON 对象
    - List[Any]: JSON 数组
    - str: 字符串
    - int: 整数
    - float: 浮点数
    - bool: 布尔值
    - None: 空值
"""

PathType = str
"""
JSON 路径类型

使用 JMESPath 语法的路径表达式字符串。

语法特性:
    - 点号访问: "data.id"
    - 数组索引: "items[0]"
    - 过滤表达式: "users[?age > 18]"
    - 投影: "users[*].name"
"""

ErrorMessageType = str
"""
错误消息类型

用于断言失败时的错误消息字符串。

格式规范:
    - 清晰描述错误原因
    - 包含期望值和实际值
    - 可选包含上下文信息
"""

CompareOperatorType = Literal['>', '<', '==', '>=', '<=', '!=']
"""
比较运算符类型

支持的比较运算符:
    - '>': 大于
    - '<': 小于
    - '==': 等于
    - '>=': 大于等于
    - '<=': 小于等于
    - '!=': 不等于
"""

HandlerType = Callable[[str], None]
"""
处理器函数类型

用于处理断言结果的回调函数类型。

参数:
    message (str): 要处理的消息

功能类型:
    - handle_error: 错误处理器
    - handle_success: 成功处理器
    - handle_warning: 警告处理器
    - handle_info: 信息处理器
"""

MatcherType = Callable[[Any], bool]
"""
匹配器函数类型

用于自定义匹配逻辑的函数类型。

参数:
    value (Any): 要匹配的值
返回:
    bool: True 表示匹配成功，False 表示匹配失败
"""

JsonSchemaType = Dict[str, Any]
"""
JSON Schema 类型

用于定义 JSON 数据结构的 schema 对象。

格式要求:
    - 符合 JSON Schema 规范
    - 包含类型定义
    - 可包含验证规则
"""


class ExpectAssertionError(AssertionError):
    """
    Expect断言错误类

    提供自定义的断言错误类型，用于区分普通断言错误和Expect断言错误。
    支持错误信息的格式化和传递。

    Attributes:
        args: 错误参数元组

    Note:
        - 继承自Python内置的AssertionError
        - 用于在断言失败时提供更详细的错误信息
        - 支持与pytest的异常处理机制集成
    """
    pass


class ResponseProtocol(Protocol):
    """
    响应对象协议类

    定义HTTP响应对象必须实现的接口规范，用于类型检查和接口约束。

    Methods:
        json(): 返回响应的JSON数据
        text(): 返回响应的文本内容
        status_code (int): HTTP响应状态码

    Note:
        - 继承自typing.Protocol
        - 用于静态类型检查
        - 定义了响应对象的最小接口要求
        - 不需要显式继承，只需实现相应方法即可
    """

    @property
    def status_code(self) -> int:
        """
        获取响应状态码

        Returns:
            int: HTTP响应状态码
        """
        ...

    def json(self) -> Dict[str, Any]:
        """
        获取响应的JSON数据

        Returns:
            Dict[str, Any]: 解析后的JSON数据

        Raises:
            JSONDecodeError: 当响应内容不是有效的JSON格式时
        """
        ...

    def text(self) -> str:
        """
        获取响应的原始文本内容

        Returns:
            str: 响应的文本内容
        """
        ...


class AssertInfo:
    """
    断言信息管理类

    管断言过程中的警告和错误信息，提供统一的信息收集和管理功能。

    Attributes:
        warning (List[str]): 警告信息列表
        error (List[str]): 错误信息列表

    Methods:
        clear(): 清空所有信息
        has_errors(): 检查是否存在错误
        add_expect_error(): 添加断言错误信息

    Note:
        - 使用类属性存储信息，便于全局访问
        - 支持多个断言的信息收集
        - 区分警告和错误两种级别
        - 提供清理机制避免信息累积
    """

    warning: List[str] = []
    error: List[str] = []

    @classmethod
    def clear(cls) -> None:
        """
        清空所有警告和错误信息

        Returns:
            None

        Note:
            - 在每次断言开始前调用
            - 避免不同测试用例间的信息混淆
        """
        cls.warning = []
        cls.error = []

    @classmethod
    def has_errors(cls) -> bool:
        """
        检查是否存在错误信息

        Returns:
            bool: True 表示存在错误，False 表示没有错误
        """
        return len(cls.error) > 0

    @classmethod
    def add_expect_error(cls, message: str) -> None:
        """
        添加断言错误信息

        Args:
            message (str): 错误信息内容

        Returns:
            None

        Note:
            - 自动添加 "Expect Assertion Error: " 前缀
            - 错误信息会被追加到错误列表中
        """
        cls.error.append(f"Expect Assertion Error: {message}")


def handle_result(func):
    """
    统一的断言结果处理装饰器

    提供完整的断言结果处理机制，支持以下特性：

    功能特性:
        - 统一的错误处理
            * 断言错误
            * 类型错误
            * 值错误
            * 通用异常
        - 成功和警告处理
        - 日志记录
        - 异常转换
        - 上下文信息保留
        - 调用链跟踪

    :param func: 要装饰的断言方法
    :type func: Callable

    :return: 装饰后的方法
    :rtype: Callable

    :raises ExpectAssertionError: 当断言失败时
    :raises TypeError: 当发生类型错误时
    :raises ValueError: 当发生值错误时
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 注入处理方法
        def handle_error(message: str, exc_info: bool = True):
            """
            错误处理

            Args:
                message: 错误消息
                exc_info: 是否包含异常堆栈信息
            """
            my_logger.logger.error(
                f"❌ {message}",
                exc_info=exc_info
            )
            raise ExpectAssertionError(message)

        def handle_success(message: str):
            """
            成功处理

            Args:
                message: 成功消息
            """
            my_logger.logger.success(f"✅ {message}")

        def handle_warning(message: str):
            """
            警告处理

            Args:
                message: 警告消息
            """
            my_logger.logger.warning(f"💡 {message}")

        def handle_info(message: str):
            """
            信息处理

            Args:
                message: 日志消息
            """
            my_logger.logger.info(f"ℹ️ {message}")

        # 注入处理方法到实例
        self.handle_error = handle_error
        self.handle_success = handle_success
        self.handle_warning = handle_warning
        self.handle_info = handle_info

        try:
            # 记录断言开始
            func_name = func.__name__
            if not func_name.startswith('_'):  # 跳过私有方法的日志
                my_logger.logger.debug(f"🔍 开始断言: {func_name}")

            # 执行断言
            result = func(self, *args, **kwargs)

            # 记录断言完成
            if not func_name.startswith('_'):
                my_logger.logger.debug(f"✨ 断言完成: {func_name}")

            return result

        except ExpectAssertionError:
            # 直接抛出已处理的断言错误
            raise

        except AssertionError as e:
            # 转换普通断言错误
            handle_error(str(e))
            return None

        except TypeError as e:
            # 处理类型错误
            handle_error(f"类型错误: {str(e)}", exc_info=True)
            return None

        except ValueError as e:
            # 处理值错误
            handle_error(f"值错误: {str(e)}", exc_info=True)
            return None

        except KeyError as e:
            # 处理键错误
            handle_error(f"键错误: {str(e)}", exc_info=True)
            return None

        except IndexError as e:
            # 处理索引错误
            handle_error(f"索引错误: {str(e)}", exc_info=True)
            return None

        except Exception as e:
            # 处理其他未预期的错误
            error_type = type(e).__name__
            handle_error(
                f"断言过程发生异常 [{error_type}]: {str(e)}",
                exc_info=True
            )
            return None

    return wrapper


# 定义泛型类型变量


class ExpectAssertion(Generic[T]):
    """断言基类"""

    # 声明处理方法的类型
    handle_error: Callable[[str], None]
    handle_success: Callable[[str], None]
    handle_warning: Callable[[str], None]
    handle_info: Callable[[str], None]

    def __init__(self, response: ResponseProtocol) -> None:
        """初始化断言基类"""
        self.response = response
        self.json_data = self._parse_json()
        AssertInfo.clear()
        self.status = StatusAssertion(self)
        self.json = JsonAssertion(self)

    def _parse_json(self) -> Dict[str, Any]:
        """解析响应JSON数据"""
        try:
            data = self.response.json()
            my_logger.logger.debug(f"📤 响应数据: {data}")
            return data
        except json.JSONDecodeError as e:
            text = self.response.text()
            preview = text[:200] + "..." if len(text) > 200 else text
            raise AssertionError(f"无效的JSON响应: {e}\n响应内容: {preview}")

    @handle_result
    def _check_type(self, value: Any, expected_type: type) -> None:
        """
        统一的类型检查

        检查值的类型是否符合预期类型。

        :param value: 要检查的值
        :type value: Any
        :param expected_type: 期望的类型
        :type expected_type: type

        :raises ExpectAssertionError: 当类型不匹配时

        注意:
            - 使用 isinstance 进行类型检查
            - 支持内置类型和自定义类型
        """
        if not isinstance(value, expected_type):
            self.handle_error(
                f"类型不匹配: 期望 {expected_type.__name__}, "
                f"实际 {type(value).__name__}"
            )

    @handle_result
    def _compare_values(self, actual: Any, expected: Any, operator_str: str) -> None:
        """
        统一的值比较

        使用 operator 库进行值比较，支持以下运算符：
            - '>' : 大于
            - '<' : 小于
            - '==' : 等于
            - '>=' : 大于等于
            - '<=' : 小于等于
            - '!=' : 不等于

        :param actual: 实际值
        :type actual: Any
        :param expected: 期望值
        :type expected: Any
        :param operator_str: 比较运算符
        :type operator_str: str

        :raises ValueError: 当使用不支持的运算符时
        :raises TypeError: 当比较类型不支持比较操作时
        """
        operators = {
            '>': operator.gt,
            '<': operator.lt,
            '==': operator.eq,
            '>=': operator.ge,
            '<=': operator.le,
            '!=': operator.ne
        }

        if operator_str not in operators:
            raise ValueError(f"不支持的运算符: {operator_str}")

        compare_func = operators[operator_str]
        if not compare_func(actual, expected):
            self.handle_error(f"比较失败: {actual} {operator_str} {expected}")

    @handle_result
    def _check_path(self, path: str, data: dict) -> Any:
        """
        统一的路径检查

        使用 JMESPath 检查 JSON 路径并获取对应的值。

        :param path: JSON 路径表达式
        :type path: str
        :param data: 要检查的数据
        :type data: dict

        :return: 路径对应的值
        :rtype: Any

        :raises ExpectAssertionError: 当路径不存在时

        注意:
            - 支持 JMESPath 的所有表达式语法
            - 当路径不存在时返回值为 None
        """
        value = jmespath.search(path, data)
        if value is None:
            self.handle_error(f"JSON 路径不存在: {path}")
        return value

    @handle_result
    def _check_length(self, value: Any, expected_length: int, error_prefix: str = "") -> None:
        """
        统一的长度检查

        检查可计算长度的对象的长度是否符合预期。

        :param value: 要检查的值
        :type value: Any
        :param expected_length: 期望的长度
        :type expected_length: int
        :param error_prefix: 错误消息前缀
        :type error_prefix: str

        :raises ExpectAssertionError: 当长度不匹配或对象不支持长度计算时

        注意:
            - 支持所有实现了 __len__ 方法的对象
            - 检查 None 值和不支持长度计算的对象
        """
        if value is None:
            self.handle_error(f"{error_prefix}值为 None，无法计算长度")

        if not hasattr(value, '__len__'):
            self.handle_error(
                f"{error_prefix}值类型 {type(value)} 不支持长度计算"
            )

        actual_length = len(value)
        if actual_length != expected_length:
            self.handle_error(
                f"{error_prefix}长度不匹配: 期望 {expected_length}, 实际 {actual_length}"
            )

    @handle_result
    def _check_empty(self, value: Any, should_be_empty: bool = True) -> None:
        """
        统一的空值检查

        检查值是否为空或非空。

        :param value: 要检查的值
        :type value: Any
        :param should_be_empty: True 表示应该为空，False 表示不应该为空
        :type should_be_empty: bool

        :raises ExpectAssertionError: 当空值状态不符合预期时

        注意:
            - 支持列表、字典、字符串等可判断空值的对象
            - None 值被视为空值
        """
        if should_be_empty and value:
            self.handle_error(f"值不为空: {value}")
        elif not should_be_empty and not value:
            self.handle_error("值为空")

    @handle_result
    def _check_contains(self, container: Any, item: Any, path: Optional[str] = None) -> None:
        """
        统一的包含关系检查

        检查容器对象是否包含指定的项。

        :param container: 容器对象
        :type container: Any
        :param item: 要检查的项
        :type item: Any
        :param path: JSON 路径（可选）
        :type path: Optional[str]

        :raises ExpectAssertionError: 当未找到指定项时

        功能特性:
            - 支持的容器类型：
                * 列表 (list)
                * 元组 (tuple)
                * 集合 (set)
                * 字典 (dict)
            - 字典支持：
                * 键值对匹配
                * 子集检查
        """
        if isinstance(container, (list, tuple, set)):
            if item not in container:
                error_message = f"未找到预期内容: {item}"
                if path:
                    error_message = f"路径 {path} {error_message}"
                self.handle_error(error_message)
        elif isinstance(container, dict):
            if isinstance(item, dict):
                for key, value in item.items():
                    if key not in container or container[key] != value:
                        error_message = f"未找到键值对 {key}: {value}"
                        if path:
                            error_message = f"路径 {path} {error_message}"
                        self.handle_error(error_message)
            else:
                self.handle_error(f"不支持的值类型进行包含判断: {type(item)}")
        else:
            self.handle_error(f"不支持的容器类型进行包含判断: {type(container)}")

    @handle_result
    def _handle_diff_results(self, diff: DeepDiff) -> None:
        """
        处理 DeepDiff 比较结果

        解析并处理深度比较的结果，生成详细的差异报告。

        :param diff: DeepDiff 比较结果对象
        :type diff: DeepDiff

        :raises ExpectAssertionError: 当发生差异时

        功能特性:
            - 差异类型处理：
                * 字典项移除
                * 字典项添加
                * 值变更
                * 类型变更
                * 列表项变更
            - 信息收集：
                * 错误信息
                * 警告信息
            - 详细的差异描述

        注意:
            - 使用 AssertInfo 收集差异信息
            - 区分警告和错误级别的差异
        """
        if diff.get('dictionary_item_removed'):
            for item in diff['dictionary_item_removed']:
                key = item.split("root['")[-1].split("']")[0]
                AssertInfo.error.append(f"响应数据缺少键: {key}")

        if diff.get('dictionary_item_added'):
            for item in diff['dictionary_item_added']:
                key = item.split("root['")[-1].split("']")[0]
                AssertInfo.warning.append(f"断言数据未包含: {key}")

        if diff.get('values_changed'):
            for path, change in diff['values_changed'].items():
                AssertInfo.error.append(
                    f"值不相等: {change.old_value} != {change.new_value}"
                )

        if diff.get('type_changes'):
            for path, change in diff['type_changes'].items():
                AssertInfo.error.append(
                    f"类型不匹配 {path}: 期望 {type(change.old_value).__name__}, "
                    f"实际 {type(change.new_value).__name__}"
                )

        if diff.get('iterable_item_removed') or diff.get('iterable_item_added'):
            AssertInfo.error.append("列表长度或内容与预期不匹配")

        if AssertInfo.warning:
            self.handle_warning("\n".join(AssertInfo.warning))

        if AssertInfo.error:
            error_message = "\n".join(AssertInfo.error)
            self.handle_error(f"JSON 比较失败:\n{error_message}")

    @handle_result
    def skip_test(self, reason: str) -> None:
        """
        跳过测试

        标记测试为跳过状态，并记录原因。

        :param reason: 跳过原因
        :type reason: str

        注意:
            - 使用 pytest.skip 实现
            - 会记录警告日志
        """
        self.handle_warning(f"跳过测试: {reason}")
        pytest.skip(reason)

    def fail_test(self, message: str) -> None:
        """
        使测试失败

        主动使测试失败，并提供失败原因。

        :param message: 失败消息
        :type message: str

        :raises pytest.fail: 始终抛出

        注意:
            - 使用 pytest.fail 实现
            - 会记录错误日志
        """
        self.handle_error(f"测试失败: {message}")
        pytest.fail(message)

    @handle_result
    def _deep_compare(self,
                      actual: Any,
                      expected: Any,
                      exclude: Optional[List[str]] = None,
                      ignore_string_case: bool = False,
                      error_prefix: str = "") -> None:
        """
        深度比较两个值

        使用 DeepDiff 进行深度比较，支持复杂数据结构的对比。

        功能特性:
            - 支持嵌套结构比较
            - 可排除指定路径
            - 可忽略字符串大小写
            - 详细的差异报告

        :param actual: 实际值
        :type actual: Any
        :param expected: 期望值
        :type expected: Any
        :param exclude: 要排除的路径列表
        :type exclude: Optional[List[str]]
        :param ignore_string_case: 是否忽略字符串大小写
        :type ignore_string_case: bool
        :param error_prefix: 错误消息前缀
        :type error_prefix: str

        :raises ExpectAssertionError: 当比较发现差异时

        注意:
            - exclude 参数使用点号分隔的路径格式
            - 比较结果会通过日志详细记录
        """
        my_logger.logger.info(f"👀 进行深度比较")

        diff = DeepDiff(
            expected,
            actual,
            exclude_paths=exclude or [],
            ignore_order=True,
            ignore_string_case=ignore_string_case,
            report_repetition=True,
            verbose_level=2
        )

        if not diff:
            self.handle_success(f"{error_prefix}数据完全匹配")
        else:
            self._handle_diff_results(diff)

    @handle_result
    def to_equal(self, expected: Any, deep_compare: bool = False) -> 'ExpectAssertion':
        """
        通用的相等性断言
        支持简单比较和深度比较两种模式

        Args:
            expected: 期望值
            deep_compare: 是否使用深度比较

        Returns:
            ExpectAssertion: 支持链式调用
        """
        actual = self._get_current_value()

        if deep_compare:
            diff = DeepDiff(expected, actual, ignore_order=True)
            if diff:
                self._handle_diff_results(diff)
        else:
            self._compare_values(actual, expected, "==")

        return self

    def _get_current_value(self) -> T:
        """
        获取当前要断言的值

        此方法是一个抽象方法，子类必须实现以提供具体的值获取逻辑。

        :return: 当前要断言的值
        :rtype: T

        :raises NotImplementedError: 当子类未实现此方法时

        注意:
            - StatusAssertion 返回状态码
            - JsonAssertion 返回当前 JSON 路径的值或完整 JSON 数据
        """
        raise NotImplementedError("子类必须实现此方法")

    @handle_result
    def to_be_in_range(self, start: T, end: T) -> 'ExpectAssertion[T]':
        """
        通用的范围断言

        Args:
            start: 范围起始值(包含)
            end: 范围结束值(不包含)

        Returns:
            ExpectAssertion: 支持链式调用
        """
        value = self._get_current_value()
        if not start <= value < end:  # type: ignore
            self.handle_error(f"值不在范围 [{start}, {end}) 内: {value}")
        return self

    @handle_result
    def to_match(self, matcher: Callable[[Any], bool],
                 error_message: str) -> 'ExpectAssertion':
        """
        通用的匹配断言

        Args:
            matcher: 匹配函数
            error_message: 匹配失败时的错误消息

        Returns:
            ExpectAssertion: 支持链式调用
        """
        value = self._get_current_value()
        if not matcher(value):
            self.handle_error(error_message)
        return self


class StatusAssertion(ExpectAssertion[int]):
    """
    状态码断言器

    提供完整的 HTTP 状态码断言功能，支持以下特性：

    功能特性:
        - 具体状态码断言
            * 200 OK
            * 201 Created
            * 202 Accepted
            * 204 No Content
            * 400 Bad Request
            * 401 Unauthorized
            * 403 Forbidden
            * 404 Not Found
            * 500 Server Error
        - 状态码范围断言
            * 2xx 成功状态码
            * 3xx 重定向状态码
            * 4xx 客户端错误状态码
            * 5xx 服务器错误状态码
        - 自定义状态码断言
            * 支持任意状态码比较
            * 支持状态码范围检查

    技术特点:
        - 继承自 ExpectAssertion 基类
        - 完整的类型注解
        - 统一的错误处理
        - 详细的日志记录
        - 链式调用支持

    属性:
        :ivar parent: 父断言对象
        :type parent: ExpectAssertion
        :ivar handle_error: 错误处理函数
        :type handle_error: Callable[[str], None]
        :ivar handle_success: 成功处理函数
        :type handle_success: Callable[[str], None]
        :ivar handle_warning: 警告处理函数
        :type handle_warning: Callable[[str], None]
        :ivar handle_info: 信息处理函数
        :type handle_info: Callable[[str], None]

    注意事项:
        - 状态码必须是有效的 HTTP 状态码
        - 范围断言使用半开区间 [start, end)
        - 所有断言方法都支持链式调用
        - 断言失败会抛出 ExpectAssertionError
    """

    # 声明处理方法的类型
    handle_error: Callable[[str], None]
    handle_success: Callable[[str], None]
    handle_warning: Callable[[str], None]
    handle_info: Callable[[str], None]

    def __init__(self, parent: ExpectAssertion):
        super().__init__(parent.response)
        self.parent = parent

    def _get_current_value(self) -> int:
        """获取当前状态码"""
        return self.parent.response.status_code

    def to_be_status(self, code: int) -> ExpectAssertion:
        """断言指定状态码"""
        self.handle_info(f"👀 断言状态码为 {code}")
        return self.to_equal(code)

    def to_be_in_range(self, start: int, end: int) -> ExpectAssertion:
        """断言状态码在指定范围内"""
        self.handle_info(f"👀 断言状态码在 {start}-{end} 范围内")
        return super().to_be_in_range(start, end)

    def to_be_success(self) -> ExpectAssertion:
        return self.to_be_in_range(200, 300)

    def to_be_client_error(self) -> ExpectAssertion:
        return self.to_be_in_range(400, 500)

    def to_be_server_error(self) -> ExpectAssertion:
        return self.to_be_in_range(500, 600)


class JsonAssertion(ExpectAssertion[JsonType]):
    """
    JSON 断言器

    提供完整的 JSON 断言功能，支持以下特性：

    功能特性:
        - JSON 路径断言
            * 支持 JMESPath 表达式
            * 支持链式调用
        - 类型断言
            * 列表类型
            * 字典类型
        - 内容断言
            * 长度验证
            * 包含关系
            * Schema 验证

    属性:
        :ivar parent: 父断言对象
        :type parent: ExpectAssertion
        :ivar _current_path: 当前选择的 JSON 路径
        :type _current_path: Optional[str]
        :ivar _current_value: 当前路径对应的值
        :type _current_value: Any
    """

    # 声明处理方法的类型
    handle_error: Callable[[str], None]
    handle_success: Callable[[str], None]
    handle_warning: Callable[[str], None]
    handle_info: Callable[[str], None]

    def __init__(self, parent: ExpectAssertion):
        # 调用父类的 __init__
        super().__init__(parent.response)
        self.parent = parent
        self._current_path: Optional[str] = None
        self._current_value: Any = None

    def _get_current_value(self) -> JsonType:
        """获取当前 JSON 值"""
        return (self._current_value if self._current_path
                else self.parent.json_data)

    @handle_result
    def at(self, path: str) -> 'JsonAssertion':
        """
        选择 JSON 路径

        Args:
            path: JMESPath 路径表达式

        Returns:
            JsonAssertion: 支持链式调用
        """
        self.handle_info(f"👀 选择 JSON 路径: {path}")
        self._current_path: Optional[str] = path
        self._current_value = self.parent._check_path(
            path, self.parent.json_data)
        return self

    @handle_result
    def to_be_list(self) -> 'JsonAssertion':
        """
        断言当前值为列表类型
        """
        value = self._get_current_value()
        self.handle_info(f"👀 断言值为列表类型: {value}")
        self.parent._check_type(value, list)
        self.handle_success("值类型为列表")
        return self

    @handle_result
    def to_be_dict(self) -> 'JsonAssertion':
        """
        断言当前值为字典类型
        """
        value = self._get_current_value()
        self.handle_info(f"👀 断言值为字典类型: {value}")
        self.parent._check_type(value, dict)
        self.handle_success("值类型为字典")
        return self

    @handle_result
    def to_have_length(self, expected_length: int) -> 'JsonAssertion':
        """
        断言当前值的长度

        Args:
            expected_length: 期望的长度
        """
        value = self._get_current_value()
        self.handle_info(f"👀 断言长度为 {expected_length}")
        self.parent._check_length(value, expected_length)
        self.handle_success(f"长度为 {expected_length}")
        return self

    @handle_result
    def to_contain(self, expected_data: Any) -> 'JsonAssertion':
        """
        断言当前值包含指定内容

        Args:
            expected_data: 期望包含的数据
        """
        value = self._get_current_value()
        self.handle_info(f"👀 断言包含: {expected_data}")
        self.parent._check_contains(value, expected_data, self._current_path)
        self.handle_success("包含预期数据")
        return self

    @handle_result
    def to_match_schema(self, schema: dict) -> 'JsonAssertion':
        """
        断言符合 JSON Schema

        Args:
            schema: JSON Schema 定义
        """
        value = self._get_current_value()
        self.handle_info("👀 验证 JSON Schema")
        try:
            validate(instance=value, schema=schema)
            self.handle_success("JSON Schema 验证成功")
        except ValidationError as e:
            self.handle_error(f"Schema 验证失败: {str(e)}")
        return self

    @handle_result
    def to_be_empty(self) -> 'JsonAssertion':
        """
        断言当前值为空
        """
        value = self._get_current_value()
        self.handle_info("👀 断言值为空")
        self.parent._check_empty(value, True)
        return self

    @handle_result
    def to_not_be_empty(self) -> 'JsonAssertion':
        """
        断言当前值不为空
        """
        value = self._get_current_value()
        self.handle_info("👀 断言值不为空")
        self.parent._check_empty(value, False)
        return self

    @handle_result
    def to_have_keys(self, *keys: str) -> 'JsonAssertion':
        """
        断言当前字典包含指定的键
        """
        value = self._get_current_value()
        self.handle_info(f"👀 断言包含键: {keys}")
        self.parent._check_type(value, dict)

        # 类型断言，告诉类型检查器这是一个字典
        value_dict = cast(Dict[str, Any], value)

        for key in keys:
            if key not in value_dict:
                self.handle_error(f"字典中不存在键: {key}")
        self.handle_success(f"包含所有期望的键: {keys}")
        return self

    @handle_result
    def to_match_pattern(self, pattern: str) -> 'JsonAssertion':
        """
        断言当前字符串值匹配正则表达式
        """
        import re
        value = self._get_current_value()
        self.handle_info(f"👀 断言匹配模式: {pattern}")
        self.parent._check_type(value, str)

        # 类型断言，告诉类型检查器这是一个字符串
        value_str = cast(str, value)

        if not re.match(pattern, value_str):
            self.handle_error(f"值不匹配模式: {pattern}")
        self.handle_success("值匹配指定模式")
        return self


# 便捷函数
def expect(response: Any) -> ExpectAssertion:
    """
    创建 expect 风格的断言对象

    提供流畅的断言接口，支持链式调用和丰富的断言功能。

    功能特性:
        - 状态码断言
            * HTTP 状态码验证
            * 状态码范围检查
            * 常用状态码快捷方法
        - JSON 数据断言
            * 路径值验证
            * 类型检查
            * 长度验证
            * 包含关系检查
            * Schema 验证
            * 正则匹配
        - 链式调用
            * 支持多个断言连续调用
            * 清晰的方法调用链
            * 优雅的代码风格
        - 自动日志记录
            * 详细的断言过程
            * 清晰的错误信息
            * 成功和警告提示

    :param response: 响应对象，必须实现 ResponseProtocol 接口
    :type response: Any

    :return: expect 风格的断言对象
    :rtype: ExpectAssertion

    :raises AssertionError: 当响应对象不符合要求时
    :raises JSONDecodeError: 当响应不包含有效的 JSON 数据时

    注意事项:
        - 响应对象必须实现 ResponseProtocol 接口
            * status_code 属性
            * json() 方法
            * text() 方法
        - JSON 数据必须是有效的 JSON 格式
        - 路径表达式使用 JMESPath 语法
        - 所有断言方法支持链式调用
        - 断言失败会抛出 ExpectAssertionError
        - 会自动记录详细的断言日志
    """
    return ExpectAssertion(response)
