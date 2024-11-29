"""
缓存工具模块

提供完整的缓存管理功能，支持以下特性：

功能特性:
    - 多种缓存实现
        * Redis 缓存
        * LRU 内存缓存
        * 磁盘缓存
        * JSON文件缓存
    - 缓存装饰器
        * 函数结果缓存
        * 类方法结果缓存
        * 依赖函数缓存
    - 缓存策略
        * 过期时间控制
        * 最大容量控制
        * 自动清理机制
    - 序列化支持
        * JSON 序列化
        * Pickle 序列化
    - 缓存统计
        * 命中率统计
        * 使用量统计

技术特点:
    - 装饰器模式
    - 策略模式
    - 工厂模式
    - 完整的类型注解
    - 自动化日志记录
"""

import functools
import json
import os
import pickle
import shutil
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import (Any, Callable, Dict, Optional, Text,
                    TypeVar, Union, cast, Protocol)

import redis

from .log_util import my_logger

# 类型变量定义
T = TypeVar('T')  # 用于泛型方法返回值
CacheKey = Union[str, int]  # 缓存键类型
CacheValue = Any  # 缓存值类型

# 磁盘缓存的默认路径
DISK_CACHE_PATH = os.path.join(tempfile.gettempdir(), ".diskcache")
JSON_CACHE_PATH = os.path.join(tempfile.gettempdir(), "cache_data.json")

T_co = TypeVar("T_co", covariant=True)


class SupportsWrite(Protocol[T_co]):
    def write(self, __s: T_co) -> Any: ...


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0  # 命中次数
    misses: int = 0  # 未命中次数
    size: int = 0  # 当前缓存大小

    @property
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheBase(ABC):
    """缓存基类，定义缓存接口"""

    def __init__(self):
        self.stats = CacheStats()

    @abstractmethod
    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: CacheKey, value: CacheValue, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        pass

    @abstractmethod
    def delete(self, key: CacheKey) -> None:
        """删除缓存值"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        return self.stats


class LRUCache(CacheBase):
    """LRU缓存实现"""

    def __init__(self, capacity: int = 128):
        """
        初始化LRU缓存

        Args:
            capacity: 缓存最大容量
        """
        super().__init__()
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.ttl_map: Dict[CacheKey, float] = {}
        self.lock = Lock()

    def _check_ttl(self, key: CacheKey) -> bool:
        """检查键是否过期"""
        if key in self.ttl_map:
            if time.time() > self.ttl_map[key]:
                self.delete(key)
                return False
        return True

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            Optional[CacheValue]: 缓存值，不存在则返回None
        """
        with self.lock:
            if key in self.cache and self._check_ttl(key):
                self.stats.hits += 1
                self.cache.move_to_end(key)
                my_logger.logger.debug(f"🎯 LRU缓存命中: {key}")
                return self.cache[key]
            self.stats.misses += 1
            my_logger.logger.debug(f"❌ LRU缓存未命中: {key}")
            return None

    def set(self, key: CacheKey, value: CacheValue, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)
        """
        with self.lock:
            if key in self.cache:
                my_logger.logger.debug(f"📝 更新LRU缓存: {key}")
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.capacity:
                    removed_key, _ = self.cache.popitem(last=False)
                    my_logger.logger.debug(
                        f"♻️ LRU缓存已满，移除最久未使用项: {removed_key}")
                my_logger.logger.debug(f"📝 写入LRU缓存: {key}")
            self.cache[key] = value
            if ttl is not None:
                self.ttl_map[key] = time.time() + ttl
                my_logger.logger.debug(f"⏱️ 设置过期时间: {key}, TTL={ttl}秒")
            self.stats.size = len(self.cache)

    def delete(self, key: CacheKey) -> None:
        """
        删除缓存值

        Args:
            key: 缓存键
        """
        with self.lock:
            self.cache.pop(key, None)
            self.ttl_map.pop(key, None)
            self.stats.size = len(self.cache)
            my_logger.logger.debug(f"🗑️ 删除LRU缓存: {key}")

    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.ttl_map.clear()
            self.stats.size = 0
            my_logger.logger.info("🧹 清空LRU缓存")


class RedisCache(CacheBase):
    """Redis缓存实现"""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 prefix: str = 'cache:'):
        """
        初始化Redis缓存

        Args:
            host: Redis主机地址
            port: Redis端口
            db: 数据库编号
            password: 密码
            prefix: 键前缀
        """
        super().__init__()
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        self.prefix = prefix
        my_logger.logger.info(f"📦 初始化Redis缓存: {host}:{port}/{db}")

    def _make_key(self, key: CacheKey) -> str:
        """生成带前缀的键"""
        return f"{self.prefix}{key}"

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            Optional[CacheValue]: 缓存值，不存在则返回None
        """
        full_key = self._make_key(key)
        value = self.client.get(full_key)
        if value is not None:
            self.stats.hits += 1
            my_logger.logger.debug(f"🎯 Redis缓存命中: {full_key}")
            try:
                if isinstance(value, (str, bytes, bytearray)):
                    return pickle.loads(value.encode('latin1') if isinstance(value, str) else value)
                else:
                    my_logger.logger.warning(f"⚠️ Redis返回了意外的值类型: {type(value)}")
                    return None
            except (pickle.PickleError, ValueError, TypeError) as error:
                my_logger.logger.debug(f"📄 Redis值使用JSON解析: {full_key}, Pickle解析失败: {error}")
                try:
                    if isinstance(value, (str, bytes, bytearray)):
                        return json.loads(value)
                    else:
                        my_logger.logger.warning(f"⚠️ Redis返回了意外的值类型: {type(value)}")
                        return None
                except (json.JSONDecodeError, ValueError, TypeError) as error:
                    my_logger.logger.error(f"❌ 解析Redis值失败: {full_key}, 错误: {error}")
                    return None
        self.stats.misses += 1
        my_logger.logger.debug(f"❌ Redis缓存未命中: {full_key}")
        return None

    def set(self, key: CacheKey, value: CacheValue, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)
        """
        full_key = self._make_key(key)
        try:
            value_str = pickle.dumps(value)
            my_logger.logger.debug(f"📝 Redis使用Pickle序列化: {full_key}")
        except (pickle.PickleError, TypeError, AttributeError) as error:
            my_logger.logger.debug(f"⚠️ Pickle序列化失败，尝试JSON序列化: {full_key}, 错误: {error}")
            try:
                value_str = json.dumps(value)
                my_logger.logger.debug(f"📝 Redis使用JSON序列化: {full_key}")
            except (TypeError, ValueError) as error:
                my_logger.logger.error(f"❌ 序列化失败: {full_key}, 错误: {error}")
                raise

        if ttl is not None:
            my_logger.logger.debug(f"⏱️ Redis设置过期时间: {full_key}, TTL={ttl}秒")
            self.client.setex(full_key, ttl, value_str)
        else:
            my_logger.logger.debug(f"📝 写入Redis缓存: {full_key}")
            self.client.set(full_key, value_str)
        self.stats.size = self.client.dbsize()

    def delete(self, key: CacheKey) -> None:
        """
        删除缓存值

        Args:
            key: 缓存键
        """
        full_key = self._make_key(key)
        self.client.delete(full_key)
        self.stats.size = self.client.dbsize()
        my_logger.logger.debug(f"🗑️ 删除Redis缓存: {full_key}")

    def clear(self) -> None:
        """清空缓存"""
        pattern = f"{self.prefix}*"
        keys = list(self.client.keys(pattern))
        if keys:
            self.client.delete(*keys)
        self.stats.size = 0
        my_logger.logger.info(f"🧹 清空Redis缓存: {pattern}")


class DiskCache(CacheBase):
    """磁盘缓存实现"""

    _NAMESPACE = uuid.UUID("c875fb30-a8a8-402d-a796-225a6b065cad")

    def __init__(self, cache_path: Optional[str] = None):
        """
        初始化磁盘缓存

        Args:
            cache_path: 缓存目录路径，默认使用系统临时目录
        """
        super().__init__()
        if cache_path:
            self.cache_path = os.path.abspath(cache_path)
        else:
            self.cache_path = DISK_CACHE_PATH

        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
            my_logger.logger.info(f"📁 创建磁盘缓存目录: {self.cache_path}")

    def _get_cache_file(self, key: CacheKey) -> str:
        """生成缓存文件路径"""
        key_str = str(key)
        params_uuid = uuid.uuid5(self._NAMESPACE, key_str)
        return os.path.join(self.cache_path, f"{key_str}-{params_uuid}.cache")

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """从磁盘读取缓存值"""
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, 'rb') as f:
                self.stats.hits += 1
                my_logger.logger.debug(f"🎯 磁盘缓存命中: {cache_file}")
                return pickle.load(f)
        except (FileNotFoundError, pickle.PickleError) as e:
            self.stats.misses += 1
            my_logger.logger.debug(f"❌ 磁盘缓存未命中: {cache_file}, 原因: {str(e)}")
            return None

    def set(self, key: CacheKey, value: CacheValue, ttl: Optional[int] = None) -> None:
        """将值写入磁盘缓存"""
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(value, cast(SupportsWrite[bytes], f))
                my_logger.logger.debug(f"📝 写入磁盘缓存: {cache_file}")
            self.stats.size = len(os.listdir(self.cache_path))
        except (OSError, pickle.PickleError) as e:
            my_logger.logger.error(f"❌ 写入磁盘缓存失败: {cache_file}, 错误: {e}")

    def delete(self, key: CacheKey) -> None:
        """删除缓存文件"""
        cache_file = self._get_cache_file(key)
        try:
            os.remove(cache_file)
            self.stats.size = len(os.listdir(self.cache_path))
            my_logger.logger.debug(f"🗑️ 删除磁盘缓存: {cache_file}")
        except FileNotFoundError:
            pass

    def clear(self) -> None:
        """清空缓存目录"""
        if os.path.exists(self.cache_path):
            shutil.rmtree(self.cache_path)
            os.makedirs(self.cache_path)
            my_logger.logger.info(f"🧹 清空磁盘缓存目录: {self.cache_path}")
        self.stats.size = 0


class JsonDiskCache(CacheBase):
    """JSON文件缓存实现"""

    def __init__(self, file_path: Optional[str] = None):
        """
        初始化JSON文件缓存

        Args:
            file_path: JSON文件路径，默认使用系统临时目录
        """
        super().__init__()
        self.file_path = file_path or JSON_CACHE_PATH
        self.lock = Lock()

        # 确保缓存文件存在
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, cast(SupportsWrite[str], f))
            my_logger.logger.info(f"📄 创建JSON缓存文件: {self.file_path}")

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """从JSON文件读取缓存值"""
        with self.lock:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if str(key) in data:
                        self.stats.hits += 1
                        my_logger.logger.debug(f"🎯 JSON缓存命中: {key}")
                        return data[str(key)]
                    self.stats.misses += 1
                    my_logger.logger.debug(f"❌ JSON缓存未命中: {key}")
                    return None
            except (json.JSONDecodeError, FileNotFoundError) as error:
                my_logger.logger.error(
                    f"❌ 读取JSON缓存失败: {self.file_path}, 错误: {error}")
                return None

    def set(self, key: CacheKey, value: CacheValue, ttl: Optional[int] = None) -> None:
        """将值写入JSON文件缓存"""
        with self.lock:
            try:
                with open(self.file_path, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data[str(key)] = value
                    f.seek(0)
                    f.truncate()
                    json.dump(data, cast(SupportsWrite[str], f))
                    self.stats.size = len(data)
                    my_logger.logger.debug(f"📝 写入JSON缓存: {key}")
            except (json.JSONDecodeError, FileNotFoundError) as error:
                my_logger.logger.warning(f"⚠️ JSON缓存文件不存在或损坏，创建新文件: {error}")
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump({str(key): value}, cast(SupportsWrite[str], f))
                    self.stats.size = 1

    def delete(self, key: CacheKey) -> None:
        """从JSON文件删除缓存值"""
        with self.lock:
            try:
                with open(self.file_path, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    if str(key) in data:
                        del data[str(key)]
                        f.seek(0)
                        f.truncate()
                        json.dump(data, cast(SupportsWrite[str], f))
                        self.stats.size = len(data)
                        my_logger.logger.debug(f"🗑️ 删除JSON缓存: {key}")
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def clear(self) -> None:
        """清空JSON文件缓存"""
        with self.lock:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, cast(SupportsWrite[str], f))
            self.stats.size = 0
            my_logger.logger.info(f"🧹 清空JSON缓存文件: {self.file_path}")


class CacheFactory:
    """缓存工厂类"""

    @staticmethod
    def create(cache_type: str = 'lru', **kwargs: Any) -> CacheBase:
        """
        创建缓存实例

        Args:
            cache_type: 缓存类型 ('lru'、'redis'、'disk'、'json')
            **kwargs: 缓存配置参数

        Returns:
            CacheBase: 缓存实例
        """
        if cache_type == 'lru':
            return LRUCache(**kwargs)
        elif cache_type == 'redis':
            return RedisCache(**kwargs)
        elif cache_type == 'disk':
            return DiskCache(**kwargs)
        elif cache_type == 'json':
            return JsonDiskCache(**kwargs)
        else:
            raise ValueError(f"Unsupported cache type: {cache_type}")


def cache(cache_instance: Optional[CacheBase] = None,
          ttl: Optional[int] = None,
          key_prefix: str = "",
          key_generator: Optional[Callable[..., str]] = None) -> Callable:
    """
    缓存装饰器

    Args:
        cache_instance: 缓存实例，默认使用LRU缓存
        ttl: 缓存过期时间(秒)
        key_prefix: 缓存键前缀
        key_generator: 自定义缓存键生成函数

    Returns:
        Callable: 装饰器函数

    Example:
        >>> # 使用默认LRU缓存
        >>> @cache(ttl=300)
        ... def get_user(user_id: int) -> dict:
        ...     return {"id": user_id, "name": "test"}

        >>> # 使用Redis缓存
        >>> redis_cache = RedisCache(host='localhost', port=6379)
        >>> @cache(cache_instance=redis_cache, ttl=300)
        ... def get_user(user_id: int) -> dict:
        ...     return {"id": user_id, "name": "test"}
    """
    if cache_instance is None:
        cache_instance = LRUCache()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 生成缓存键
            if key_generator is not None:
                cache_key = key_generator(*args, **kwargs)
            else:
                # 默认使用函数名和参数生成键
                params = [str(arg) for arg in args]
                params.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}{func.__name__}:{':'.join(params)}"

            # 尝试从缓存获取
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                my_logger.logger.debug(f"🎯 缓存命中: {cache_key}")
                return cast(T, cached_value)

            # 执行函数并缓存结果
            my_logger.logger.debug(f"❌ 缓存未命中: {cache_key}")
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl)
            my_logger.logger.debug(f"💾 已缓存结果: {cache_key}")
            return result

        # 添加缓存管理方法
        wrapper.clear_cache = cache_instance.clear  # type: ignore
        wrapper.get_stats = cache_instance.get_stats  # type: ignore

        return wrapper

    return decorator


def dependent_cache(func_obj: Callable, key_name: Text = None, cache_instance: Optional[CacheBase] = None,
                    ttl: Optional[int] = None, *out_args, **out_kwargs) -> Callable:
    """
    依赖函数缓存装饰器

    Args:
        func_obj: 依赖的函数对象
        key_name: 缓存键名，默认使用依赖函数名
        cache_instance: 缓存实例，默认使用LRU缓存
        ttl: 缓存过期时间(秒)
        out_args: 依赖函数的位置参数
        out_kwargs: 依赖函数的关键字参数

    Returns:
        Callable: 装饰器函数

    Example:
        >>> def get_token():
        ...     return "token123"
        ...
        >>> @dependent_cache(get_token, ttl=300)
        ... def api_request():
        ...     pass
    """
    if cache_instance is None:
        cache_instance = LRUCache()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            func_name = func.__name__
            depend_func_name = func_obj.__name__

            # 使用指定的键名或函数名作为缓存键
            cache_key = key_name or depend_func_name

            # 检查缓存中是否存在依赖函数的结果
            cached_value = cache_instance.get(cache_key)
            if cached_value is None:
                my_logger.logger.info(
                    f"🔗 <{func_name}> 依赖 <{depend_func_name}>, 执行依赖函数")
                # 执行依赖函数并缓存结果
                result = func_obj(*out_args, **out_kwargs)
                cache_instance.set(cache_key, result, ttl)
            else:
                my_logger.logger.info(
                    f"🔗 <{depend_func_name}> 已执行, 从缓存获取结果: {cache_key}")

            # 执行主函数
            return func(*args, **kwargs)

        # 添加缓存管理方法
        wrapper.clear_cache = cache_instance.clear  # type: ignore
        wrapper.get_stats = cache_instance.get_stats  # type: ignore

        return wrapper

    return decorator


# 创建默认缓存实例
default_cache = LRUCache()
default_disk_cache = DiskCache()
default_json_cache = JsonDiskCache()
