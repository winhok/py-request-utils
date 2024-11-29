"""
随机数据生成工具模块

提供完整的随机测试数据生成功能，支持以下特性：

功能特性:
    - 基础数据生成
        * 数字类型
        * 字符串类型
        * 日期时间类型
        * 布尔类型
    - 复合数据生成
        * 列表生成
        * 字典生成
        * 嵌套结构生成
    - 业务数据生成
        * 个人信息
        * 地址信息
        * 公司信息
        * 网络信息
    - 属性测试
        * 基于假设的测试
        * 自定义策略
        * 边界值测试

技术特点:
    - 基于 Faker 和 Hypothesis 实现
    - 完整的类型注解
    - 装饰器模式支持
    - 链式调用支持
    - 自动化日志记录
"""

import random
from datetime import datetime, timedelta
from typing import Any, List, Dict, Union, Optional, TypeVar

from faker import Faker
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from .log_util import my_logger

# 类型变量定义
T = TypeVar('T')
Number = Union[int, float]
DateType = Union[datetime, str]


class RandomGenerator:
    """
    随机数据生成器基类
    
    提供基础的随机数据生成功能和通用方法
    """

    def __init__(self, locale: str = 'zh_CN', seed: Optional[int] = None):
        """
        初始化随机数据生成器
        
        Args:
            locale: 语言地区设置
            seed: 随机种子
        """
        my_logger.logger.info(f"🎲 初始化随机数据生成器 | 语言: {locale}")
        self.faker = Faker(locale)
        if seed is not None:
            my_logger.logger.info(f"🎯 设置随机种子: {seed}")
            Faker.seed(seed)
            random.seed(seed)
        self._current_value: Any = None

    def seed(self, seed: int) -> None:
        """设置随机种子"""
        my_logger.logger.info(f"🎯 更新随机种子: {seed}")
        self.faker.seed(seed)
        random.seed(seed)

    def reset(self) -> None:
        """重置生成器状态"""
        my_logger.logger.debug("🔄 重置生成器状态")
        self._current_value = None


class NumericGenerator(RandomGenerator):
    """数值类型随机数据生成器"""

    @my_logger.runtime_logger
    def integer(self, min_value: int = 0, max_value: int = 100) -> int:
        """生成随机整数"""
        my_logger.logger.debug(f"🎲 生成随机整数 | 范围: [{min_value}, {max_value}]")
        self._current_value = self.faker.random_int(min_value, max_value)
        my_logger.logger.debug(f"✨ 生成结果: {self._current_value}")
        return self._current_value

    @my_logger.runtime_logger
    def float_number(self, min_value: float = 0.0, max_value: float = 100.0,
                     precision: int = 2) -> float:
        """生成随机浮点数"""
        my_logger.logger.debug(
            f"🎲 生成随机浮点数 | 范围: [{min_value}, {max_value}] | 精度: {precision}"
        )
        self._current_value = round(
            self.faker.random.uniform(min_value, max_value),
            precision
        )
        my_logger.logger.debug(f"✨ 生成结果: {self._current_value}")
        return self._current_value

    @my_logger.runtime_logger
    def percentage(self) -> float:
        """生成随机百分比(0-100)"""
        my_logger.logger.debug("🎲 生成随机百分比")
        result = self.float_number(0, 100, 2)
        my_logger.logger.debug(f"✨ 生成结果: {result}%")
        return result

    @my_logger.runtime_logger
    def amount(self, min_value: float = 0.0, max_value: float = 10000.0) -> float:
        """生成随机金额"""
        my_logger.logger.debug(f"🎲 生成随机金额 | 范围: [{min_value}, {max_value}]")
        result = self.float_number(min_value, max_value, 2)
        my_logger.logger.debug(f"✨ 生成结果: ¥{result}")
        return result


class StringGenerator(RandomGenerator):
    """字符串类型随机数据生成器"""

    @my_logger.runtime_logger
    def string(self, min_length: int = 1, max_length: int = 10) -> str:
        """生成随机字符串"""
        my_logger.logger.debug(f"🎲 生成随机字符串 | 长度范围: [{min_length}, {max_length}]")
        self._current_value = self.faker.pystr(min_length, max_length)
        my_logger.logger.debug(f"✨ 生成结果: {self._current_value}")
        return self._current_value

    @my_logger.runtime_logger
    def word(self) -> str:
        """生成随机单词"""
        my_logger.logger.debug("🎲 生成随机单词")
        result = self.faker.word()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def sentence(self, nb_words: int = 6) -> str:
        """生成随机句子"""
        my_logger.logger.debug(f"🎲 生成随机句子 | 单词数: {nb_words}")
        result = self.faker.sentence(nb_words)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def paragraph(self, nb_sentences: int = 3) -> str:
        """生成随机段落"""
        my_logger.logger.debug(f"🎲 生成随机段落 | 句子数: {nb_sentences}")
        result = self.faker.paragraph(nb_sentences)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def text(self, max_nb_chars: int = 200) -> str:
        """生成随机文本"""
        my_logger.logger.debug(f"🎲 生成随机文本 | 最大字符数: {max_nb_chars}")
        result = self.faker.text(max_nb_chars)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class DateTimeGenerator(RandomGenerator):
    """日期时间类型随机数���生成器"""

    @my_logger.runtime_logger
    def date(self, start_date: DateType = '-30y', end_date: DateType = 'now') -> str:
        """生成随机日期"""
        my_logger.logger.debug(f"🎲 生成随机日期 | 范围: [{start_date}, {end_date}]")
        self._current_value = self.faker.date_between(start_date, end_date)
        result = self._current_value.strftime('%Y-%m-%d')
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def time(self) -> str:
        """生成随机时间"""
        my_logger.logger.debug("🎲 生成随机时间")
        result = self.faker.time()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def datetime(self, start_date: DateType = '-30y', end_date: DateType = 'now') -> str:
        """生成随机日期时间"""
        my_logger.logger.debug(f"🎲 生成随机日期时间 | 范围: [{start_date}, {end_date}]")
        dt = self.faker.date_time_between(start_date, end_date)
        result = dt.strftime('%Y-%m-%d %H:%M:%S')
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def future_date(self, days: int = 30) -> str:
        """生���未来日期"""
        my_logger.logger.debug(f"🎲 生成未来日期 | 天数范围: [0, {days}]")
        end_date = datetime.now() + timedelta(days=days)
        result = self.date('now', end_date)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def past_date(self, days: int = 30) -> str:
        """生成过去日期"""
        my_logger.logger.debug(f"🎲 生成过去日期 | 天数范围: [-{days}, 0]")
        start_date = datetime.now() - timedelta(days=days)
        result = self.date(start_date, 'now')
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class PersonGenerator(RandomGenerator):
    """个人信息随机数据生成器"""

    @my_logger.runtime_logger
    def name(self) -> str:
        """生成随机姓名"""
        my_logger.logger.debug("🎲 生成随机姓名")
        result = self.faker.name()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def first_name(self) -> str:
        """生成随机名"""
        my_logger.logger.debug("🎲 生成随机名")
        result = self.faker.first_name()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def last_name(self) -> str:
        """生成随机姓"""
        my_logger.logger.debug("🎲 生成随机姓")
        result = self.faker.last_name()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def age(self, min_age: int = 0, max_age: int = 100) -> int:
        """生成随机年龄"""
        my_logger.logger.debug(f"🎲 生成随机年龄 | 范围: [{min_age}, {max_age}]")
        result = self.faker.random_int(min_age, max_age)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def phone_number(self) -> str:
        """生成随机手机号"""
        my_logger.logger.debug("🎲 生成随机手机号")
        result = self.faker.phone_number()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def email(self, domain: Optional[str] = None) -> str:
        """生成随机邮箱"""
        my_logger.logger.debug(f"🎲 生成随机邮箱 | 域名: {domain or '随机'}")
        result = self.faker.email() if domain is None else self.faker.email(domain=domain)
        my_logger.logger.debug(f"✨ 生成��果: {result}")
        return result

    @my_logger.runtime_logger
    def id_card(self) -> str:
        """生成随机身份证号"""
        my_logger.logger.debug("🎲 生成随机身份证号")
        result = self.faker.ssn()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class AddressGenerator(RandomGenerator):
    """地址信息随机数据生成器"""

    @my_logger.runtime_logger
    def country(self) -> str:
        """生成随机国家"""
        my_logger.logger.debug("🎲 生成随机国家")
        result = self.faker.country()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def province(self) -> str:
        """生成随机省份"""
        my_logger.logger.debug("🎲 生成随机省份")
        result = self.faker.province()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def city(self) -> str:
        """生成随机城市"""
        my_logger.logger.debug("🎲 生成随机城市")
        result = self.faker.city()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def street_address(self) -> str:
        """生成随机街道地址"""
        my_logger.logger.debug("🎲 生成随机街道地址")
        result = self.faker.street_address()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def postcode(self) -> str:
        """生成随机邮编"""
        my_logger.logger.debug("🎲 生成随机邮编")
        result = self.faker.postcode()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def latitude(self) -> float:
        """生成随机纬度"""
        my_logger.logger.debug("🎲 生成随机纬度")
        result = float(self.faker.latitude())
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def longitude(self) -> float:
        """生成随机经度"""
        my_logger.logger.debug("🎲 生成随机经度")
        result = float(self.faker.longitude())
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class InternetGenerator(RandomGenerator):
    """网络信息随机数据生成器"""

    @my_logger.runtime_logger
    def url(self) -> str:
        """生成随机URL"""
        my_logger.logger.debug("🎲 生成随机URL")
        result = self.faker.url()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def domain_name(self) -> str:
        """生成随机域名"""
        my_logger.logger.debug("🎲 生成随机域名")
        result = self.faker.domain_name()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def ipv4(self) -> str:
        """生成随机IPv4地址"""
        my_logger.logger.debug("🎲 生成随机IPv4地址")
        result = self.faker.ipv4()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def ipv6(self) -> str:
        """生成随机IPv6地址"""
        my_logger.logger.debug("🎲 生成随机IPv6地址")
        result = self.faker.ipv6()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def mac_address(self) -> str:
        """生成随机MAC地址"""
        my_logger.logger.debug("🎲 生成随机MAC地址")
        result = self.faker.mac_address()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def user_name(self) -> str:
        """生成随机用户名"""
        my_logger.logger.debug("🎲 生成随机用户名")
        result = self.faker.user_name()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def password(self, length: int = 10) -> str:
        """生成随机密码"""
        my_logger.logger.debug(f"🎲 生成随机密码 | 长度: {length}")
        result = self.faker.password(length=length)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class CompanyGenerator(RandomGenerator):
    """公司信息随机数据生成器"""

    @my_logger.runtime_logger
    def company_name(self) -> str:
        """生成随机公司名"""
        my_logger.logger.debug("🎲 生成随机公司名")
        result = self.faker.company()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def company_suffix(self) -> str:
        """生成随机公司后缀"""
        my_logger.logger.debug("🎲 生成随机公司后缀")
        result = self.faker.company_suffix()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def job(self) -> str:
        """生成随机职位"""
        my_logger.logger.debug("🎲 生成随机职位")
        result = self.faker.job()
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result

    @my_logger.runtime_logger
    def department(self) -> str:
        """生成随机部门"""
        my_logger.logger.debug("🎲 生成随机部门")
        departments = ['研发部', '市场部', '销售部', '人力资源部', '财务部', '运营部']
        result = random.choice(departments)
        my_logger.logger.debug(f"✨ 生成结果: {result}")
        return result


class HypothesisGenerator:
    """Hypothesis策略生成器"""

    @staticmethod
    def integers(min_value: Optional[int] = None,
                 max_value: Optional[int] = None) -> SearchStrategy[int]:
        """生成整数策略"""
        my_logger.logger.debug(f"🎲 创建整数策略 | 范围: [{min_value or '-∞'}, {max_value or '∞'}]")
        return st.integers(min_value=min_value, max_value=max_value)

    @staticmethod
    def floats(min_value: Optional[float] = None,
               max_value: Optional[float] = None,
               allow_infinity: bool = False,
               allow_nan: bool = False) -> SearchStrategy[float]:
        """生成浮点数策略"""
        my_logger.logger.debug(
            f"🎲 创建浮点数策略 | 范围: [{min_value or '-∞'}, {max_value or '∞'}] | "
            f"允许无穷: {allow_infinity} | 允许NaN: {allow_nan}"
        )
        return st.floats(
            min_value=min_value,
            max_value=max_value,
            allow_infinity=allow_infinity,
            allow_nan=allow_nan
        )

    @staticmethod
    def text(alphabet: Optional[str] = None,
             min_size: int = 0,
             max_size: Optional[int] = None) -> SearchStrategy[str]:
        """生成文本策略"""
        my_logger.logger.debug(
            f"🎲 创建文本策略 | 字母表: {alphabet or '默认'} | "
            f"长度范围: [{min_size}, {max_size or '∞'}]"
        )
        return st.text(alphabet=alphabet, min_size=min_size, max_size=max_size)

    @staticmethod
    def lists(elements: SearchStrategy[T],
              min_size: int = 0,
              max_size: Optional[int] = None) -> SearchStrategy[List[T]]:
        """生成列表策略"""
        my_logger.logger.debug(
            f"🎲 创建列表策略 | 长度范围: [{min_size}, {max_size or '∞'}]"
        )
        return st.lists(elements, min_size=min_size, max_size=max_size)

    @staticmethod
    def dictionaries(keys: SearchStrategy[T],
                     values: SearchStrategy[Any],
                     min_size: int = 0,
                     max_size: Optional[int] = None) -> SearchStrategy[Dict[T, Any]]:
        """生成字典策略"""
        my_logger.logger.debug(
            f"🎲 创建字典策略 | 大小范围: [{min_size}, {max_size or '∞'}]"
        )
        return st.dictionaries(
            keys=keys,
            values=values,
            min_size=min_size,
            max_size=max_size
        )

    @staticmethod
    def datetimes(min_value: Optional[datetime] = None,
                  max_value: Optional[datetime] = None) -> SearchStrategy[datetime]:
        """生成日期时间策略"""
        my_logger.logger.debug(
            f"🎲 创建日期时间策略 | 范围: [{min_value or '最小'}, {max_value or '最大'}]"
        )
        return st.datetimes(min_value=min_value, max_value=max_value)


class RandomData:
    """
    随机数据生成器主类
    
    整合所有类型的数据生成器，提供统一的访问接口
    """

    def __init__(self, locale: str = 'zh_CN', seed: Optional[int] = None):
        """
        初始化随机数据生成器
        
        Args:
            locale: 语言地区设置
            seed: 随机种子
        """
        my_logger.logger.info(f"🎲 初始化随机数据生成器")
        my_logger.logger.info(f"📍 语言设置: {locale}")
        if seed is not None:
            my_logger.logger.info(f"🎯 随机种子: {seed}")

        self.numeric = NumericGenerator(locale, seed)
        self.string = StringGenerator(locale, seed)
        self.datetime = DateTimeGenerator(locale, seed)
        self.person = PersonGenerator(locale, seed)
        self.address = AddressGenerator(locale, seed)
        self.internet = InternetGenerator(locale, seed)
        self.company = CompanyGenerator(locale, seed)
        self.hypothesis = HypothesisGenerator()

        my_logger.logger.info("✅ 随机数据生成器初始化完成")

    def seed(self, seed: int) -> None:
        """设置随机种子"""
        my_logger.logger.info(f"🎯 设置全局随机种子: {seed}")
        generators = [
            self.numeric, self.string, self.datetime,
            self.person, self.address, self.internet,
            self.company
        ]
        for generator in generators:
            generator.seed(seed)
        my_logger.logger.info("✅ 随机种子设置完成")

    def reset(self) -> None:
        """重置所有生成器状态"""
        my_logger.logger.info("🔄 重置所有生成器状态")
        generators = [
            self.numeric, self.string, self.datetime,
            self.person, self.address, self.internet,
            self.company
        ]
        for generator in generators:
            generator.reset()
        my_logger.logger.info("✅ 重置完成")


# 创建默认实例
random_data = RandomData()
