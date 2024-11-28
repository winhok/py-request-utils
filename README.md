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

### 4. 测试工具（开发中）

- [ ] 测试报告生成器
- [ ] 数据驱动支持
- [ ] 环境配置管理
- [ ] 数据库操作工具
- [ ] 缓存管理
- [ ] 随机数生成器

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

## 项目结构

```
project/
├── utils/
│   ├── __init__.py
│   ├── log_util.py      # 日志工具
│   └── request_util.py  # HTTP请求工具
│   └── assert_util.py   # 断言工具
├── tests/
│   └── __init__.py
├── pyproject.toml
└── README.md
```

## 开发路线图

- [x] 日志系统
  - [x] 基础日志功能
  - [x] 装饰器支持
  - [x] 文件轮转
- [x] HTTP 请求模块
  - [x] 基础请求方法
  - [x] 会话管理
  - [x] 重试机制
  - [x] curl 命令生成
- [x] 断言工具
  - [x] 断言结果管理
  - [x] 丰富的断言方法
  - [x] 自定义错误消息
  - [x] 支持 JSON 数据断言
- [ ] 测试报告生成
- [ ] 数据驱动功能
- [ ] 配置管理系统
- [ ] 数据库工具
- [ ] 缓存系统
- [ ] 随机数工具

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
