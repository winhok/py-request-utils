# Python 自动化测试工具集

## 简介

这是一个基于 Python 的自动化测试工具集，专注于提供简单易用的接口测试解决方案。本项目旨在降低自动化测试的学习门槛，让测试人员能够快速上手并专注于测试用例的编写。

目前为该入行的新手想写写项目练手，该工具集都是参考前辈们的书籍或视频整理而来，如果侵权请联系我删除谢谢。

## 环境要求

- Python 3.10 或更高版本
- Poetry 包管理工具(推荐)
- pip 包管理工具(可选)

## 核心功能

### 1. 日志系统 ✅

- [x] 支持控制台彩色输出和文件记录
- [x] 自动创建日志目录和时间戳文件
- [x] 提供装饰器用于记录函数执行情况
- [x] 支持动态调整日志级别
- [x] 日志文件自动轮转和保留策略
- [x] 支持类方法和函数的运行时日志记录

### 2. HTTP 请求工具 ✅

- [x] 支持所有标准 HTTP 方法（GET, POST, PUT, DELETE, PATCH 等）
- [x] 自动会话管理和重试机制
- [x] 请求响应详细日志记录
- [x] 支持生成 curl 命令
- [x] Unicode 文本自动处理
- [x] 灵活的请求配置选项

### 3. 断言工具 ✅

- [x] 断言结果管理
  - [x] 自动记录断言结果
  - [x] 支持批量验证
- [x] 丰富的断言方法
  - [x] 相等性断言
  - [x] 包含关系断言
  - [x] 类型检查断言
- [x] 自定义错误消息
- [x] 支持 JSON 数据断言
  - [x] 路径值验证
  - [x] Schema 验证
  - [x] 正则匹配

### 4. 缓存工具 ✅

- [x] 多种缓存实现
  - [x] Redis 缓存
  - [x] LRU 内存缓存
  - [x] 磁盘缓存
  - [x] JSON文件缓存
- [x] 缓存装饰器
  - [x] 函数结果缓存
  - [x] 类方法结果缓存
  - [x] 依赖函数缓存
- [x] 缓存策略
  - [x] 过期时间控制
  - [x] 最大容量控制
  - [x] 自动清理机制

### 5. 加密解密工具 ✅

- [x] 对称加密
  - [x] AES 加密
  - [x] DES 加密
- [x] 非对称加密
  - [x] RSA 加密
- [x] Hash 算法
  - [x] MD5
  - [x] SHA256
- [x] Base64 编码解码

### 6. 随机测试数据生成 ✅

- [x] 基础数据生成
  - [x] 数字类型
  - [x] 字符串类型
  - [x] 日期时间类型
  - [x] 布尔类型
- [x] 业务数据生成
  - [x] 个人信息
  - [x] 地址信息
  - [x] 公司信息
  - [x] 网络信息

### 7. 测试报告工具 ✅

- [x] 报告生成
  - [x] 离线HTML报告
  - [x] 资源文件内联
  - [x] 报告打包
- [x] 报告发送
  - [x] 钉钉机器人
  - [x] 企业微信机器人
  - [x] 邮件发送
- [x] 报告管理
  - [x] 自动清理历史报告
  - [x] 报告统计信息
  - [x] 报告模板定制



## 快速开始

### 安装

```bash
# 使用 Poetry 安装依赖
poetry install
```

```bash
# 使用 pip 安装依赖
pip install -r requirements.txt
```

### 日志使用示例

```python
from utils.log_util import my_logger

# 使用默认配置
logger = my_logger.logger

# 自定义日志级别
my_logger.set_level("INFO")

# 使用装饰器
@my_logger.runtime_logger
def your_function():
    # 你的代码
    pass

@my_logger.runtime_logger_class
class YourTestClass:
    def test_something(self):
        # 测试代码
        pass
```

### HTTP 请求示例

```python
from utils.request_util import HttpClient
创建客户端实例
client = HttpClient(base_url="https://api.example.com")
发送 GET 请求
response = client.get("/users")
发送 POST 请求
response = client.post("/users", json_data={"name": "test"})
获取响应状态码
status = client.status_code
生成 curl 命令
curl_command = client.curl()
```

### 断言工具使用示例

```python
from utils.assert_util import expect

# 基本断言
response = client.get("/api/users/1")
expect(response).status_code.to_equal(200)

# JSON 数据断言
expect(response).json.at("user.name").to_equal("张三")
expect(response).json.at("user.age").to_be_greater_than(18)

# Schema 验证
user_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    },
    "required": ["name", "age"]
}
expect(response).json.to_match_schema(user_schema)

# 正则匹配
expect(response).json.at("user.email").to_match(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# 链式调用
expect(response)\
    .status_code.to_equal(200)\
    .json.at("user.name").to_equal("张三")\
    .json.at("user.age").to_be_greater_than(18)
```


#### 随机数据生成使用示例

```python
from utils.random_util import PersonGenerator, AddressGenerator

# 创建生成器实例
person = PersonGenerator()
address = AddressGenerator()

# 生成个人信息
name = person.name()
phone = person.phone_number()
email = person.email()

# 生成地址信息
province = address.province()
city = address.city()
street = address.street_address()
```

#### 报告生成和发送使用示例

```python
from utils.report_util import ReportManager

# 创建报告管理器
report_manager = ReportManager()

# 生成报告
report_path = report_manager.generate_offline_report()

# 发送报告
report_manager.send_report(
    report_path=report_path,
    title="测试报告",
    to_dingtalk=True,
    to_wechat=True,
    to_email="test@example.com"
)
```

#### 缓存使用示例

```python
from utils.cache_util import RedisCache, LRUCache

# 创建缓存实例
redis_cache = RedisCache()
memory_cache = LRUCache()

# 使用缓存装饰器
@redis_cache.cache(ttl=3600)
def get_user_info(user_id):
    # 获取用户信息的逻辑
    pass
```


## 项目结构

```
project/
├── utils/
│   ├── __init__.py
│   ├── log_util.py      # 日志工具
│   ├── request_util.py  # HTTP请求工具
│   ├── assert_util.py   # 断言工具
│   ├── cache_util.py    # 缓存工具
│   ├── encrypt_util.py  # 加密解密工具
│   ├── random_util.py   # 随机数据工具
│   ├── send_util.py     # 消息发送工具
│   └── report_util.py   # 报告工具
├── tests/
│   └── __init__.py
├── pyproject.toml
└── README.md
```

## 开发路线图

- [x] 日志系统
- [x] HTTP 请求模块
- [x] 断言工具
- [x] 缓存系统
- [x] 加密解密工具
- [x] 随机数据生成
- [x] 消息发送工具
- [x] 测试报告工具
- [ ] 数据驱动功能
- [ ] 配置管理系统
- [ ] 数据库工具



## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。在提交代码前，请确保：

1. 代码符合 PEP 8 规范
2. 添加了适当的单元测试
3. 更新了相关文档

## 许可证

MIT License

## 联系方式

- 邮箱：2063685743@qq.com
- GitHub：[[项目地址](https://github.com/winhok/py-request-utils)]
