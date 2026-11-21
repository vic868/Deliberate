---
title: "第 10 章｜Middleware、异常处理与日志"
chapter: "10"
source: "第 10 章｜Middleware、异常处理与日志.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - middleware
  - 日志
---

# 第 10 章｜Middleware、异常处理与日志

> [!abstract] 本章重点
>
> - ==Middleware 包在请求生命周期最外层== — 进业务前后都能插手，适合放 request_id 和耗时统计。
> - ==统一错误格式== — 不管哪里出错，前端都收到同一种结构，好处理。
> - ==业务错误码和系统异常分开== — 给用户看的提示，和给开发排查的堆栈，是两回事。
> - ==exception_handlers 集中兜底== — HTTPException、参数校验错误、业务异常各注册一个处理器。
> - ==日志要带 request_id== — 一次请求的所有日志才能串起来查。
>
> [!note] 大白话
>
> - **Middleware**：请求进来和响应出去都要经过的一层「安检门」。
> - **request_id**：给每次请求发个号码牌，日志靠它对账。
>
> [!info] 导航与来源
> - 原始讲义：[[第 10 章｜Middleware、异常处理与日志|打开原始讲义]]
> - [[第 09 章｜FastAPI Dependency Injection 依赖注入|上一章｜第 09 章]]
> - [[第 11 章｜PostgreSQL + SQLAlchemy 数据库开发|下一章｜第 11 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章]]
- [[#五、02｜先看当前项目的问题]]
- [[#六、03｜我们希望的统一错误格式]]
- [[#七、04｜请求生命周期：Middleware 在哪里执行]]
- [[#八、05｜创建 request_context.py]]
- [[#九、06｜创建 logging.py]]
- [[#十、07｜创建 middleware.py]]
- [[#十一、08｜修改 main.py 注册 Middleware 和日志]]
- [[#十二、09｜测试 Middleware]]
- [[#十三、10｜升级统一响应模型]]
- [[#十四、11｜创建 exceptions.py]]

---
---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面几章我们已经完成了 FastAPI 后端的基础骨架：

```text
第 06 章｜FastAPI 快速入门
第 07 章｜Pydantic 请求参数与响应模型
第 08 章｜FastAPI Router 与项目工程化
第 09 章｜FastAPI Dependency Injection 依赖注入
```

现在我们的项目已经有了：

```text
Router
 ↓
Dependency
 ↓
Service
 ↓
Repository
```

也已经有了：

```text
Chat 接口
RAG 接口
Conversations 接口
Models 接口
Agents 接口
API Key 校验
当前用户依赖
LLM Provider 依赖
Mock DB Session
```

==但是现在还有几个企业项目必须解决的问题：==

```text
1. 错误响应格式不统一
2. 接口日志不统一
3. 请求耗时没有统一统计
4. trace_id 没有贯穿全链路
5. 业务异常和系统异常没有区分
6. ValidationError 返回格式不适合前端统一处理
7. 后面 LLM / RAG / Agent 出错不好排查
```

所以这一章我们要引入三个核心能力：

```text
Middleware
异常处理
日志系统
```

这一章的目标不是简单会写：

```python
@app.middleware("http")
```

而是要把项目升级成：

**有统一请求链路、有统一 trace_id、有统一异常格式、有统一日志输出的企业级 AI 后端。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. Middleware 是什么
2. 请求进入 FastAPI 后的完整生命周期
3. 如何编写 HTTP Middleware
4. 如何生成 trace_id
5. 如何把 trace_id 放到 request.state
6. 如何把 trace_id 返回给前端
7. 如何统计接口耗时
8. 如何记录请求日志
9. 如何设计统一错误响应
10. 如何定义业务异常 AppException
11. 如何定义错误码 ErrorCode
12. 如何处理 HTTPException
13. 如何处理 RequestValidationError
14. 如何处理业务异常
15. 如何处理未知系统异常
16. 如何把异常和 trace_id 关联起来
17. 如何设计 logging.py
18. 如何让 Service 抛出业务异常
19. 如何测试错误请求
20. 如何为后续 LLM / RAG / Agent 调试打基础
```

---

## 三、本章最终项目结构
本章结束后，项目结构会升级成：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       ├── models.py
│   │       ├── agents.py
│   │       └── rag.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── request_context.py
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   ├── exception_handlers.py
│   │   └── middleware.py
│   │
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── llm.py
│   │   ├── settings.py
│   │   ├── pagination.py
│   │   └── agent_context.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   ├── rag.py
│   │   └── user.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py
│   │   ├── conversation_service.py
│   │   └── rag_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── conversation_repository.py
│   │   └── knowledge_repository.py
│   │
│   └── models/
│       └── __init__.py
│
├── tests/
│   ├── test_chat_api.py
│   ├── test_dependency_api.py
│   ├── test_exception_api.py
│   └── test_project_structure.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

本章重点新增：

```text
app/core/request_context.py
app/core/logging.py
app/core/exceptions.py
app/core/exception_handlers.py
app/core/middleware.py
tests/test_exception_api.py
```

---

## 四、01｜本章
### 【重点内容】
大家好，欢迎来到第 10 章。

这一章我们讲三个企业级 FastAPI 项目非常重要的能力：

```text
Middleware
异常处理
日志
```

如果你只是写一个 Demo，其实可以不讲这些。

比如接口直接返回：

```json
{
  "detail": "xxx"
}
```

或者直接在控制台 print 一下：

```python
print("调用大模型失败")
```

也能跑。

但是企业项目不行。

尤其是 AI 应用，问题会比传统后端更多。

比如：

```text
LLM 超时
模型返回格式不对
RAG 检索为空
向量数据库异常
工具调用失败
Agent 执行中断
用户输入参数错误
Token 超限
API Key 无效
权限不足
```

如果没有统一异常和日志，你后面排查问题会非常痛苦。

==所以这一章我们要做几件事。==

第一：

```text
每个请求生成 trace_id
```

第二：

```text
记录请求方法、路径、耗时、状态码
```

第三：

```text
所有错误返回统一结构
```

第四：

```text
业务异常、参数异常、系统异常分开处理
```

第五：

```text
让日志里也带上 trace_id
```

这样后面用户反馈：

```text
刚才那个 AI 回答接口报错了
```

我们就可以让用户把 trace_id 发给我们。

然后后端通过 trace_id 查日志，快速定位问题。

这就是企业级 AI 后端必须具备的能力。

---

## 五、02｜先看当前项目的问题
### 【当前默认错误】
如果现在调用 Chat 接口不传 API Key：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是 AI Agent？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

默认返回可能是：

```json
{
  "detail": "缺少请求头 x-api-key"
}
```

如果参数校验失败，比如 `messages` 为空：

```json
{
  "messages": [],
  "model": "deepseek-chat"
}
```

默认返回可能是：

```json
{
  "detail": [
    {
      "type": "too_short",
      "loc": ["body", "messages"],
      "msg": "List should have at least 1 item after validation, not 0",
      "input": [],
      "ctx": {
        "field_type": "List",
        "min_length": 1,
        "actual_length": 0
      }
    }
  ]
}
```

---

### 【重点内容】
FastAPI 默认错误响应其实已经挺好了。

但是对企业前端来说，它有几个问题。

第一：

```text
成功响应和错误响应格式不统一
```

成功时我们返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

但是错误时返回：

```json
{
  "detail": "xxx"
}
```

前端就要写两套处理逻辑。

第二：

```text
没有 trace_id
```

错误发生后，前端无法把某次请求和后端日志关联起来。

第三：

```text
业务错误和系统错误没有区分
```

比如：

```text
模型不存在
权限不足
参数错误
服务内部异常
```

这些最好有不同错误码。

==所以这一章我们要统一错误响应格式。==

---

## 六、03｜我们希望的统一错误格式
我们希望所有错误都返回：

```json
{
  "code": 40001,
  "message": "缺少请求头 x-api-key",
  "data": null,
  "trace_id": "trace_xxxxxxxx"
}
```

参数错误返回：

```json
{
  "code": 42200,
  "message": "请求参数校验失败",
  "data": {
    "errors": [
      {
        "field": "body.messages",
        "message": "List should have at least 1 item after validation, not 0"
      }
    ]
  },
  "trace_id": "trace_xxxxxxxx"
}
```

系统错误返回：

```json
{
  "code": 50000,
  "message": "服务器内部错误",
  "data": null,
  "trace_id": "trace_xxxxxxxx"
}
```

---

### 【重点内容】
这就是我们这一章要实现的目标。

成功响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误响应：

```json
{
  "code": 40001,
  "message": "xxx",
  "data": null,
  "trace_id": "trace_xxx"
}
```

这样前端可以统一判断：

```text
code === 0
表示成功

code !== 0
表示失败
```

同时所有响应都带：

```text
trace_id
```

方便排查。

---

## 七、04｜请求生命周期：Middleware 在哪里执行
### 【实操】
```text
HTTP Request
    ↓
Middleware 请求前逻辑
    ↓
Dependency
    ↓
Router
    ↓
Service
    ↓
Repository / LLM / RAG / Agent
    ↓
Response
    ↓
Middleware 响应后逻辑
    ↓
HTTP Response
```

---

### 【重点内容】
Middleware 可以理解成请求的“外层包装”。

请求进入之后，不会直接到 Router。

它会先经过 Middleware。

Middleware 可以做：

```text
生成 trace_id
记录请求开始时间
打印请求日志
统一处理响应 Header
统计接口耗时
```

然后 Middleware 会调用：

```python
call_next(request)
```

把请求交给后面的 Router、Dependency、Service。

等接口处理完返回 response 后，Middleware 又可以继续做：

```text
记录状态码
记录耗时
把 trace_id 写入响应头
```

==所以 Middleware 非常适合做全局能力。==

---

## 八、05｜创建 request_context.py
我们希望日志里能随时拿到当前请求的 trace_id。

创建：

```text
app/core/request_context.py
```

写入：

```python
from contextvars import ContextVar


trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


def set_trace_id(trace_id: str):
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    return trace_id_var.get()


def set_user_id(user_id: str):
    user_id_var.set(user_id)


def get_user_id() -> str:
    return user_id_var.get()
```

---

### 【重点内容】
这里我们使用了 Python 的：

```python
ContextVar
```

它可以保存当前请求上下文里的变量。

为什么不用普通全局变量？

因为 FastAPI 是并发服务。

同一时间可能有很多请求。

如果用普通全局变量：

```python
trace_id = "xxx"
```

多个请求之间可能互相覆盖。

而 `ContextVar` 可以让每个请求有自己的上下文。

所以我们用它保存：

```text
trace_id
user_id
```

后面日志系统就可以从这里读取当前请求的 trace_id。

---

## 九、06｜创建 logging.py
创建：

```text
app/core/logging.py
```

写入：

```python
import logging
import sys

from app.core.request_context import get_trace_id, get_user_id


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.user_id = get_user_id()
        return True


def setup_logging():
    logger = logging.getLogger()

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | "
            "trace_id=%(trace_id)s | user_id=%(user_id)s | "
            "%(name)s:%(lineno)d | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```

---

### 【重点内容】
现在我们定义日志系统。

这里有几个重点。

第一：

```python
RequestContextFilter
```

它会给每条日志自动加上：

```text
trace_id
user_id
```

第二：

```python
setup_logging()
```

用于初始化日志格式。

第三：

```python
get_logger(__name__)
```

后面每个模块都可以通过它拿到 logger。

比如：

```python
logger = get_logger(__name__)
logger.info("开始调用大模型")
```

日志会自动带上 trace_id。

这对 AI 项目排查问题非常有用。

---

## 十、07｜创建 middleware.py
创建：

```text
app/core/middleware.py
```

写入：

```python
import time
import uuid

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.logging import get_logger
from app.core.request_context import set_trace_id, set_user_id


logger = get_logger(__name__)


def register_middleware(app: FastAPI):
    @app.middleware("http")
    async def trace_and_log_middleware(request: Request, call_next):
        start_time = time.perf_counter()

        trace_id = request.headers.get("x-trace-id") or f"trace_{uuid.uuid4().hex[:12]}"
        user_id = request.headers.get("x-user-id") or "-"

        set_trace_id(trace_id)
        set_user_id(user_id)

        logger.info(
            f"request_start method={request.method} path={request.url.path}"
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            cost_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f"request_exception method={request.method} "
                f"path={request.url.path} cost_ms={cost_ms:.2f}"
            )
            raise

        cost_ms = (time.perf_counter() - start_time) * 1000

        response.headers["x-trace-id"] = trace_id
        response.headers["x-process-time-ms"] = f"{cost_ms:.2f}"

        logger.info(
            f"request_end method={request.method} "
            f"path={request.url.path} status_code={response.status_code} "
            f"cost_ms={cost_ms:.2f}"
        )

        return response
```

---

### 【重点内容】
==这个 Middleware 是这一章的核心之一。==

它做了几件事。

第一，生成 trace_id：

```python
trace_id = request.headers.get("x-trace-id") or f"trace_{uuid.uuid4().hex[:12]}"
```

如果前端传了 `x-trace-id`，我们就使用前端传的。

如果没传，后端自动生成。

第二，把 trace_id 放到上下文：

```python
set_trace_id(trace_id)
```

第三，记录请求开始日志：

```python
request_start
```

第四，执行真正的接口：

```python
response = await call_next(request)
```

第五，统计耗时：

```python
cost_ms = (time.perf_counter() - start_time) * 1000
```

第六，把 trace_id 和耗时写到响应头：

```python
response.headers["x-trace-id"] = trace_id
response.headers["x-process-time-ms"] = f"{cost_ms:.2f}"
```

第七，记录请求结束日志。

这样每个请求都会自动有：

```text
trace_id
耗时
开始日志
结束日志
```

---

## 十一、08｜修改 main.py 注册 Middleware 和日志
打开：

```text
app/main.py
```

修改为：

```python
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import register_middleware


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        description="Python + FastAPI + LLM + Agent 开发实战",
        version=settings.app_version,
        debug=settings.debug,
    )

    register_middleware(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root():
        return {
            "message": settings.app_name,
            "env": settings.app_env,
            "version": settings.app_version,
        }

    return app


app = create_app()
```

---

### 【重点内容】
现在我们在 `create_app()` 里做两件事。

第一：

```python
setup_logging()
```

初始化日志系统。

第二：

```python
register_middleware(app)
```

注册 Middleware。

这样应用启动后，每个请求都会经过我们的中间件。

注意顺序：

```python
setup_logging()
app = FastAPI()
register_middleware(app)
app.include_router(...)
```

这是一种比较清晰的应用初始化流程。

---

## 十二、09｜测试 Middleware
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

访问：

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

响应头中应该看到：

```text
x-trace-id: trace_xxxxxxxxxxxx
x-process-time-ms: 1.23
```

终端日志类似：

```text
2026-08-24 10:30:00 | INFO | trace_id=trace_xxx | user_id=- | app.core.middleware:24 | request_start method=GET path=/api/v1/health
2026-08-24 10:30:00 | INFO | trace_id=trace_xxx | user_id=- | app.core.middleware:48 | request_end method=GET path=/api/v1/health status_code=200 cost_ms=2.35
```

---

### 【重点内容】
现在我们测试一下。

使用：

```bash
curl -i
```

可以看到响应头。

我们重点看两个响应头：

```text
x-trace-id
x-process-time-ms
```

这说明 Middleware 生效了。

再看终端日志，每条日志里都带了：

```text
trace_id
user_id
```

==这就是统一日志链路的基础。==

---

## 十三、10｜升级统一响应模型
打开：

```text
app/schemas/response.py
```

修改成：

```python
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")


class ErrorDetail(BaseModel):
    field: str | None = Field(default=None, description="错误字段")
    message: str = Field(..., description="错误信息")


class ErrorResponse(BaseModel):
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误信息")
    data: dict | list | None = Field(default=None, description="错误详情")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
```

---

### 【重点内容】
现在我们给统一响应增加一个：

```python
trace_id
```

成功响应也可以带 trace_id。

错误响应也带 trace_id。

这样前端不管成功还是失败，都可以拿到 trace_id。

==不过这一章里，我们重点先让错误响应带 trace_id。==

后面如果想让所有成功响应体也带 trace_id，可以在每个接口返回时设置，或者后面做统一响应包装。

目前我们先不强行自动包装成功响应，避免引入过多复杂度。

---

## 十四、11｜创建 exceptions.py
创建：

```text
app/core/exceptions.py
```

写入：

```python
from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 0

    BAD_REQUEST = 40000
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    VALIDATION_ERROR = 42200

    MODEL_NOT_SUPPORTED = 50001
    LLM_CALL_FAILED = 50002
    RAG_QUERY_FAILED = 50003
    TOOL_CALL_FAILED = 50004
    AGENT_RUN_FAILED = 50005

    INTERNAL_ERROR = 50000


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: int = ErrorCode.BAD_REQUEST,
        status_code: int = 400,
        data: dict | list | None = None,
    ):
        self.message = message
        self.code = int(code)
        self.status_code = status_code
        self.data = data

        super().__init__(message)
```

---

### 【重点内容】
现在我们定义自己的业务异常：

```python
AppException
```

它有几个字段：

```text
message
code
status_code
data
```

`message` 是错误提示。

`code` 是业务错误码。

`status_code` 是 HTTP 状态码。

`data` 是额外错误详情。

比如后面模型不支持，我们可以抛：

```python
raise AppException(
    message="不支持的模型",
    code=ErrorCode.MODEL_NOT_SUPPORTED,
    status_code=400,
)
```

这样错误就会被统一处理。

---

## 十五、12｜为什么要有业务错误码
### 【重点内容】
很多新手会问：

HTTP 状态码不是已经有 400、401、403、500 了吗？为什么还要业务 code？

因为 HTTP 状态码粒度比较粗。

比如都是 400，但是原因可能不同：

```text
参数错误
模型不支持
知识库不存在
工具参数错误
```

==所以企业项目通常会设计业务错误码。==

比如：

```text
40000
= 普通请求错误

40100
= 未登录或认证失败

40300
= 无权限

42200
= 参数校验失败

50001
= 模型不支持

50002
= LLM 调用失败

50003
= RAG 查询失败

50004
= Tool 调用失败

50005
= Agent 执行失败
```

这样前端、后端、测试、运维都能更清楚地定位问题。

---

## 十六、13｜创建 exception_handlers.py
创建：

```text
app/core/exception_handlers.py
```

写入：

```python
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.core.request_context import get_trace_id
from app.schemas.response import ErrorResponse


logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            f"app_exception path={request.url.path} "
            f"code={exc.code} message={exc.message}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                data=exc.data,
                trace_id=get_trace_id(),
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            f"http_exception path={request.url.path} "
            f"status_code={exc.status_code} detail={exc.detail}"
        )

        code = map_http_status_to_error_code(exc.status_code)

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=code,
                message=str(exc.detail),
                data=None,
                trace_id=get_trace_id(),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        errors = []

        for error in exc.errors():
            loc = ".".join(str(item) for item in error.get("loc", []))
            msg = error.get("msg", "参数错误")

            errors.append(
                {
                    "field": loc,
                    "message": msg,
                }
            )

        logger.warning(
            f"validation_exception path={request.url.path} errors={errors}"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                code=int(ErrorCode.VALIDATION_ERROR),
                message="请求参数校验失败",
                data={
                    "errors": errors
                },
                trace_id=get_trace_id(),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            f"unhandled_exception path={request.url.path} error={repr(exc)}"
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                code=int(ErrorCode.INTERNAL_ERROR),
                message="服务器内部错误",
                data=None,
                trace_id=get_trace_id(),
            ).model_dump(),
        )


def map_http_status_to_error_code(status_code: int) -> int:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return int(ErrorCode.UNAUTHORIZED)

    if status_code == status.HTTP_403_FORBIDDEN:
        return int(ErrorCode.FORBIDDEN)

    if status_code == status.HTTP_404_NOT_FOUND:
        return int(ErrorCode.NOT_FOUND)

    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return int(ErrorCode.VALIDATION_ERROR)

    if 400 <= status_code < 500:
        return int(ErrorCode.BAD_REQUEST)

    return int(ErrorCode.INTERNAL_ERROR)
```

---

### 【重点内容】
==这个文件是这一章的核心。==

我们统一注册了四类异常处理器。

第一类：

```python
AppException
```

这是我们自己定义的业务异常。

第二类：

```python
HTTPException
```

这是 FastAPI 常用异常，比如 401、403、404。

第三类：

```python
RequestValidationError
```

这是请求参数校验失败，比如字段缺失、类型错误、长度不符合规则。

第四类：

```python
Exception
```

这是兜底异常，捕获所有未处理的系统错误。

这样我们就能把所有错误统一返回成：

```json
{
  "code": 50000,
  "message": "服务器内部错误",
  "data": null,
  "trace_id": "trace_xxx"
}
```

---

## 十七、14｜修改 main.py 注册异常处理器
打开：

```text
app/main.py
```

修改为：

```python
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import register_middleware


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        description="Python + FastAPI + LLM + Agent 开发实战",
        version=settings.app_version,
        debug=settings.debug,
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root():
        return {
            "message": settings.app_name,
            "env": settings.app_env,
            "version": settings.app_version,
        }

    return app


app = create_app()
```

---

### 【重点内容】
现在我们在应用启动时注册异常处理器：

```python
register_exception_handlers(app)
```

注意现在 `create_app()` 的职责越来越清楚：

```text
setup_logging
 ↓
创建 FastAPI app
 ↓
注册 middleware
 ↓
注册 exception handlers
 ↓
注册 router
```

==这就是企业级应用初始化流程。==

---

## 十八、15｜测试 HTTPException 统一格式
现在我们测试 API Key 错误。

curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是 AI Agent？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

返回应该变成：

```json
{
  "code": 40100,
  "message": "缺少请求头 x-api-key",
  "data": null,
  "trace_id": "trace_xxxxxxxxxxxx"
}
```

---

### 【重点内容】
现在大家看，错误格式已经不再是默认的：

```json
{
  "detail": "xxx"
}
```

而是我们统一的：

```json
{
  "code": 40100,
  "message": "缺少请求头 x-api-key",
  "data": null,
  "trace_id": "trace_xxx"
}
```

这说明我们的 HTTPException 处理器生效了。

---

## 十九、16｜测试参数校验错误
请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [],
    "model": "deepseek-chat",
    "temperature": 3,
    "stream": false
  }'
```

返回类似：

```json
{
  "code": 42200,
  "message": "请求参数校验失败",
  "data": {
    "errors": [
      {
        "field": "body.messages",
        "message": "List should have at least 1 item after validation, not 0"
      },
      {
        "field": "body.temperature",
        "message": "Input should be less than or equal to 2"
      }
    ]
  },
  "trace_id": "trace_xxxxxxxxxxxx"
}
```

---

### 【重点内容】
现在参数错误也被统一处理了。

这里我们重点看：

```json
"field": "body.messages"
```

表示错误字段位置。

```json
"message": "..."
```

表示错误原因。

这样前端可以根据字段名做表单提示。

比如：

```text
temperature 输入错误
messages 不能为空
```

后面如果做管理后台、Agent 创建表单、知识库配置表单，这种错误格式会非常有用。

---

## 二十、17｜让 Service 抛业务异常
现在我们把 ChatRequest 的模型校验保留，同时在 Service 里模拟一个业务异常。

打开：

```text
app/services/chat_service.py
```

增加导入：

```python
from app.core.exceptions import AppException, ErrorCode
```

在 `chat_with_ai` 里面添加：

```python
if "触发业务异常" in latest_user_message:
    raise AppException(
        message="这是一个模拟业务异常",
        code=ErrorCode.LLM_CALL_FAILED,
        status_code=500,
        data={
            "reason": "mock llm failed"
        },
    )
```

完整片段：

```python
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    latest_user_message = get_latest_user_message(request)
    model = request.model or settings.default_model

    if "触发业务异常" in latest_user_message:
        raise AppException(
            message="这是一个模拟业务异常",
            code=ErrorCode.LLM_CALL_FAILED,
            status_code=500,
            data={
                "reason": "mock llm failed"
            },
        )

    if "AI Agent" in latest_user_message:
        answer = "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。"
    elif "RAG" in latest_user_message:
        answer = "RAG 是检索增强生成，用于让大模型结合企业私有知识库进行回答。"
    elif "LangGraph" in latest_user_message:
        answer = "LangGraph 适合开发有状态、有分支、有流程控制的复杂 Agent。"
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{latest_user_message}」。"
```

---

### 【重点内容】
现在我们让 Service 抛出业务异常。

比如用户问题里包含：

```text
触发业务异常
```

我们就抛：

```python
AppException
```

这模拟后面真实场景：

```text
LLM 调用失败
RAG 查询失败
Tool 调用失败
Agent 执行失败
```

为什么要在 Service 里抛？

因为这些是业务执行过程中的错误，不是请求参数格式错误。

参数格式错误交给 Pydantic。

业务错误交给 Service。

然后统一由异常处理器返回。

---

## 二十一、18｜测试业务异常
curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "触发业务异常"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

返回：

```json
{
  "code": 50002,
  "message": "这是一个模拟业务异常",
  "data": {
    "reason": "mock llm failed"
  },
  "trace_id": "trace_xxxxxxxxxxxx"
}
```

---

### 【重点内容】
现在业务异常也变成了统一结构。

错误码：

```text
50002
```

表示：

```text
LLM_CALL_FAILED
```

前端看到这个 code，就知道是模型调用相关异常。

同时返回了：

```text
trace_id
```

排查时可以用它查日志。

---

## 二十二、19｜新增系统异常测试接口
修改：

```text
app/api/v1/health.py
```

增加：

```python
@router.get("/system-error-demo")
async def system_error_demo():
    result = 1 / 0
    return {
        "result": result
    }
```

测试：

```bash
curl http://127.0.0.1:8000/api/v1/system-error-demo
```

返回：

```json
{
  "code": 50000,
  "message": "服务器内部错误",
  "data": null,
  "trace_id": "trace_xxxxxxxxxxxx"
}
```

---

### 【重点内容】
这里我们故意写：

```python
1 / 0
```

触发系统异常。

这种错误不是业务异常，也不是参数异常，而是代码内部错误。

比如真实项目里可能是：

```text
空指针
数据库连接异常
代码 Bug
第三方 SDK 未捕获异常
```

这类错误不要直接把详细堆栈返回给前端。

前端只需要知道：

```text
服务器内部错误
```

详细堆栈要写到后端日志里。

---

## 二十三、20｜为什么系统异常不要暴露细节
### 【重点内容】
系统异常里可能包含敏感信息。

比如：

```text
数据库地址
SQL 语句
API Key
文件路径
内部类名
第三方服务地址
```

如果直接返回给前端，会有安全风险。

所以我们统一返回：

```json
{
  "message": "服务器内部错误"
}
```

但是日志里要记录完整异常：

```python
logger.exception(...)
```

这样用户看不到敏感信息，后端又能排查。

==这就是生产级错误处理的基本原则：==

**对用户友好，对日志详细。**

---

## 二十四、21｜在日志里观察 trace_id
当你触发系统异常后，终端会看到类似日志：

```text
2026-08-24 10:40:00 | ERROR | trace_id=trace_xxx | user_id=- | app.core.exception_handlers:80 | unhandled_exception path=/api/v1/system-error-demo error=ZeroDivisionError('division by zero')
Traceback (most recent call last):
  ...
ZeroDivisionError: division by zero
```

---

### 【重点内容】
大家看这里。

日志里有：

```text
trace_id=trace_xxx
```

前端拿到的错误响应里也有：

```json
"trace_id": "trace_xxx"
```

这样就能关联起来。

以后用户反馈问题时，不要只问：

```text
你刚才点了什么？
```

而是让前端把：

```text
trace_id
```

带给后端。

后端直接搜日志，就能定位这次请求。

这就是 trace_id 的价值。

---

## 二十五、22｜让 CurrentUser 依赖写入 user_id 上下文
现在我们的 Middleware 会从 Header 里读取 `x-user-id`。

但是更规范的方式是，在用户依赖解析成功后，把 user_id 写入上下文。

修改：

```text
app/dependencies/auth.py
```

增加导入：

```python
from app.core.request_context import set_user_id
```

在 `get_current_user` 返回前添加：

```python
set_user_id(x_user_id)
```

完整片段：

```python
async def get_current_user(
    api_key: str = Depends(verify_api_key),
    x_user_id: str | None = Header(default=None),
    x_username: str | None = Header(default=None),
    x_user_role: str = Header(default="user"),
) -> CurrentUser:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少请求头 x-user-id",
        )

    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少请求头 x-username",
        )

    role = UserRole.ADMIN if x_user_role == "admin" else UserRole.USER

    set_user_id(x_user_id)

    return CurrentUser(
        user_id=x_user_id,
        username=x_username,
        role=role,
        is_active=True,
    )
```

---

### 【重点内容】
现在当用户认证通过后，我们把：

```text
user_id
```

写到请求上下文里。

这样后续 Service 或日志打印时，就能自动带上 user_id。

比如：

```python
logger.info("开始调用大模型")
```

输出日志里就会带：

```text
user_id=u_10001
```

这对排查用户级问题非常有帮助。

---

## 二十六、23｜在 ChatService 中记录日志
打开：

```text
app/services/chat_service.py
```

增加导入：

```python
from app.core.logging import get_logger
```

定义 logger：

```python
logger = get_logger(__name__)
```

在 `chat_with_ai` 中增加日志：

```python
logger.info(
    f"chat_start model={model} message_count={len(request.messages)}"
)
```

在返回前增加：

```python
logger.info(
    f"chat_success model={model} answer_length={len(answer)}"
)
```

完整关键片段：

```python
logger = get_logger(__name__)


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    latest_user_message = get_latest_user_message(request)
    model = request.model or settings.default_model

    logger.info(
        f"chat_start model={model} message_count={len(request.messages)}"
    )

    if "触发业务异常" in latest_user_message:
        logger.warning("chat_mock_business_exception")
        raise AppException(
            message="这是一个模拟业务异常",
            code=ErrorCode.LLM_CALL_FAILED,
            status_code=500,
            data={
                "reason": "mock llm failed"
            },
        )

    if "AI Agent" in latest_user_message:
        answer = "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。"
    elif "RAG" in latest_user_message:
        answer = "RAG 是检索增强生成，用于让大模型结合企业私有知识库进行回答。"
    elif "LangGraph" in latest_user_message:
        answer = "LangGraph 适合开发有状态、有分支、有流程控制的复杂 Agent。"
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{latest_user_message}」。"

    logger.info(
        f"chat_success model={model} answer_length={len(answer)}"
    )
```

---

### 【重点内容】
现在 ChatService 里也开始写日志了。

注意不要用：

```python
print()
```

而是用：

```python
logger.info()
logger.warning()
logger.error()
logger.exception()
```

这样日志会有统一格式。

并且自动带：

```text
trace_id
user_id
模块名
行号
```

后面真正调用 LLM 时，我们会记录：

```text
模型名称
请求 token
响应 token
耗时
是否成功
错误原因
```

这些都应该进入日志。

---

## 二十七、24｜日志不要打印敏感信息
### 【重点内容】
这里特别强调一个点。

日志不是越详细越好。

不要打印敏感信息。

比如不要打印：

```text
完整 API Key
完整 Authorization Token
用户密码
身份证
手机号
银行卡
企业私密文档全文
大模型完整 Prompt
```

尤其是 AI 项目，Prompt 里可能包含企业内部知识。

日志里可以记录：

```text
message_count
answer_length
model
token 数
耗时
trace_id
```

但不要无脑把用户问题、完整 Prompt、完整文档内容都打进日志。

如果确实要记录，也要做脱敏和权限控制。

---

## 二十八、25｜新增 exception 测试脚本
创建：

```text
tests/test_exception_api.py
```

写入：

```python
import requests


BASE_URL = "http://127.0.0.1:8000"


def print_response(response):
    print("status_code:", response.status_code)
    print("headers x-trace-id:", response.headers.get("x-trace-id"))
    print("json:", response.json())


def test_missing_api_key():
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "什么是 AI Agent？"
                }
            ],
            "model": "deepseek-chat",
            "temperature": 0.7,
            "stream": False
        }
    )

    print_response(response)


def test_validation_error():
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        headers={
            "x-api-key": "dev-api-key-123",
            "x-user-id": "u_10001",
            "x-username": "dawei",
        },
        json={
            "messages": [],
            "model": "deepseek-chat",
            "temperature": 3,
            "stream": False
        }
    )

    print_response(response)


def test_business_error():
    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        headers={
            "x-api-key": "dev-api-key-123",
            "x-user-id": "u_10001",
            "x-username": "dawei",
        },
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "触发业务异常"
                }
            ],
            "model": "deepseek-chat",
            "temperature": 0.7,
            "stream": False
        }
    )

    print_response(response)


def test_system_error():
    response = requests.get(
        f"{BASE_URL}/api/v1/system-error-demo"
    )

    print_response(response)


if __name__ == "__main__":
    print("====== missing api key ======")
    test_missing_api_key()

    print("====== validation error ======")
    test_validation_error()

    print("====== business error ======")
    test_business_error()

    print("====== system error ======")
    test_system_error()
```

运行前启动服务：

```bash
uv run uvicorn app.main:app --reload
```

另开终端运行：

```bash
python tests/test_exception_api.py
```

---

### 【重点内容】
这个测试脚本会分别测试四类错误：

```text
缺少 API Key
参数校验错误
业务异常
系统异常
```

这样大家可以清楚看到每种错误的返回格式。

后面每新增一种异常，都可以加到这个测试脚本里。

---

## 二十九、26｜错误分类总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【实操】
| 错误类型 | 来源 | 示例 | 处理方式 |
| --- | --- | --- | --- |
| HTTPException | 依赖 / Router | API Key 缺失、权限不足 | http_exception_handler |
| RequestValidationError | Pydantic | 参数缺失、类型错误 | validation_exception_handler |
| AppException | Service 业务逻辑 | LLM 失败、RAG 失败 | app_exception_handler |
| Exception | 未知系统异常 | 代码 Bug、除零错误 | unhandled_exception_handler |


---

### 【重点内容】
==大家一定要把这几类错误分清楚。==

第一类：

```text
HTTPException
```

一般来自依赖、权限、简单接口错误。

第二类：

```text
RequestValidationError
```

来自请求参数校验。

第三类：

```text
AppException
```

来自我们自己的业务逻辑。

第四类：

```text
Exception
```

兜底处理未知系统异常。

企业项目里，不要所有错误都用 Exception。

该业务异常就抛 AppException。

该权限错误就抛 HTTPException。

参数错误交给 Pydantic。

未知错误交给兜底处理。

---

## 三十、27｜AI 项目中的典型异常设计
### 【实操】
```text
LLM_CALL_FAILED
= 大模型调用失败

RAG_QUERY_FAILED
= 知识库查询失败

TOOL_CALL_FAILED
= 工具调用失败

AGENT_RUN_FAILED
= Agent 执行失败

MODEL_NOT_SUPPORTED
= 不支持的模型

VALIDATION_ERROR
= 请求参数错误

UNAUTHORIZED
= 未认证

FORBIDDEN
= 无权限
```

---

### 【重点内容】
AI 项目的异常设计要围绕真实场景。

比如后面调用 LLM，可能出现：

```text
API Key 无效
模型不存在
请求超时
Token 超限
服务商限流
返回格式不是 JSON
```

RAG 可能出现：

```text
知识库不存在
文档为空
向量库查询失败
rerank 失败
没有命中文档
```

Agent 可能出现：

```text
工具不存在
工具参数错误
工具执行失败
步骤超时
超过最大迭代次数
```

这些都应该逐步设计成明确错误码。

这一章我们先把基础机制搭好。

后面接 LLM / RAG / Agent 时继续扩展。

---

## 三十一、28｜在 RAGService 中使用 AppException
打开：

```text
app/services/rag_service.py
```

增加导入：

```python
from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
```

定义 logger：

```python
logger = get_logger(__name__)
```

修改：

```python
async def query_rag(request: RAGQueryRequest) -> RAGQueryResponse:
    logger.info(
        f"rag_query_start knowledge_base_id={request.knowledge_base_id} top_k={request.top_k}"
    )

    if request.knowledge_base_id == "kb_error":
        raise AppException(
            message="知识库查询失败",
            code=ErrorCode.RAG_QUERY_FAILED,
            status_code=500,
            data={
                "knowledge_base_id": request.knowledge_base_id
            },
        )

    sources = await knowledge_repository.search_documents(
        question=request.question,
        knowledge_base_id=request.knowledge_base_id,
        top_k=request.top_k,
        metadata_filter=request.metadata_filter,
    )

    answer = f"根据知识库 {request.knowledge_base_id} 的内容，RAG 是检索增强生成。"

    logger.info(
        f"rag_query_success knowledge_base_id={request.knowledge_base_id} source_count={len(sources)}"
    )

    return RAGQueryResponse(
        answer=answer,
        knowledge_base_id=request.knowledge_base_id,
        sources=sources,
        usage=TokenUsage(
            prompt_tokens=len(request.question),
            completion_tokens=len(answer),
            total_tokens=len(request.question) + len(answer),
        ),
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
    )
```

---

### 【重点内容】
现在 RAGService 也使用 AppException。

如果知识库 ID 是：

```text
kb_error
```

我们模拟查询失败。

真实项目里，这里可能是：

```text
向量数据库异常
知识库不存在
embedding 服务失败
```

这样 RAG 异常也会走统一异常处理。

---

## 三十二、29｜测试 RAG 业务异常
curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "什么是 RAG？",
    "knowledge_base_id": "kb_error",
    "top_k": 5,
    "rerank": true,
    "metadata_filter": {}
  }'
```

返回：

```json
{
  "code": 50003,
  "message": "知识库查询失败",
  "data": {
    "knowledge_base_id": "kb_error"
  },
  "trace_id": "trace_xxxxxxxxxxxx"
}
```

---

## 三十三、30｜Middleware 和异常处理的执行关系
### 【实操】
```text
Request
  ↓
Middleware request_start
  ↓
Router / Dependency / Service
  ↓
如果抛异常
  ↓
Exception Handler 生成错误响应
  ↓
Middleware request_end
  ↓
Response
```

---

### 【重点内容】
这里大家要理解 Middleware 和异常处理器的关系。

请求进来先经过 Middleware。

然后进入 Router。

如果 Router、Dependency、Service 里面抛异常，FastAPI 会交给对应的 Exception Handler。

Exception Handler 会生成一个错误响应。

然后这个响应还会回到 Middleware。

==所以 Middleware 仍然可以给错误响应加：==

```text
x-trace-id
x-process-time-ms
```

这就是为什么错误响应头里也有 trace_id。

---

## 三十四、31｜状态码和业务 code 的关系
### 【实操】
| HTTP 状态码 | 业务 code | 场景 |
| --- | --- | --- |
| 200 | 0 | 成功 |
| 400 | 40000 | 请求错误 |
| 401 | 40100 | 未认证 |
| 403 | 40300 | 无权限 |
| 404 | 40400 | 资源不存在 |
| 422 | 42200 | 参数校验失败 |
| 500 | 50000+ | 服务内部错误 / AI 调用失败 |


---

### 【重点内容】
这里再强调一下。

HTTP 状态码和业务 code 是两层东西。

HTTP 状态码给浏览器、网关、负载均衡、运维系统看。

业务 code 给前端业务逻辑看。

比如：

```text
HTTP 401
表示未认证

业务 code 40100
表示我们系统里的未认证错误
```

再比如：

```text
HTTP 500
表示服务器错误

业务 code 50002
表示 LLM 调用失败
```

这样可读性更强。

---

## 三十五、32｜不要吞掉异常
### 【重点内容】
有些同学喜欢这样写：

```python
try:
    result = await call_llm()
except Exception:
    return "调用失败"
```

这样不好。

因为你把错误吞掉了。

日志没有记录，错误码没有返回，trace_id 没有关联。

推荐：

```python
try:
    result = await call_llm()
except TimeoutError as e:
    logger.exception("llm_timeout")
    raise AppException(
        message="大模型调用超时",
        code=ErrorCode.LLM_CALL_FAILED,
        status_code=500,
    ) from e
```

这样既记录了日志，又返回了统一错误格式。

---

## 三十六、33｜更新 README
打开：

```text
README.md
```

追加：

```markdown
## 日志与异常处理

本项目统一使用：

```
Middleware
+
Exception Handler
+
Logger
+
trace_id
```text

每个请求都会自动生成：

```
x-trace-id
x-process-time-ms
```text

错误响应格式：

```
{
  "code": 50000,
  "message": "服务器内部错误",
  "data": null,
  "trace_id": "trace_xxx"
}
```text

常见错误码：

```
40000 请求错误
40100 未认证
40300 无权限
40400 资源不存在
42200 参数校验失败
50001 模型不支持
50002 LLM 调用失败
50003 RAG 查询失败
50004 Tool 调用失败
50005 Agent 执行失败
50000 服务器内部错误
```text

```
---

## 三十七、34｜当前完整请求链路

### 【实操】

```text id="ye5h2t"
HTTP Request
    ↓
trace_and_log_middleware
    ↓
生成 trace_id
    ↓
记录 request_start
    ↓
verify_api_key
    ↓
get_current_user
    ↓
Router
    ↓
Service
    ↓
Repository / LLM / RAG
    ↓
如果成功：ApiResponse
    ↓
如果失败：Exception Handler -> ErrorResponse
    ↓
Middleware 添加响应头
    ↓
记录 request_end
    ↓
HTTP Response
```

---

### 【重点内容】
现在我们的 FastAPI 项目链路已经非常清楚。

每个请求都会经过：

```text
Middleware
Dependency
Router
Service
Repository
```

如果中间出错，会进入：

```text
Exception Handler
```

最后统一返回。

==这就是企业级后端的基础链路。==

后面我们接入：

```text
LLM
RAG
Agent
MCP
Multi-Agent
```

都在这个链路里继续扩展。

---

## 三十八、35｜常见错误一：异常处理器没有注册

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误现象：

```json
错误响应还是 {"detail": "..."}
```

原因可能是：

```text
register_exception_handlers(app) 没有调用
```

检查 `main.py`：

```python
register_exception_handlers(app)
```

必须写在 `create_app()` 里。

---

## 三十九、36｜常见错误二：Middleware 没有注册
错误现象：

```text
响应头没有 x-trace-id
日志没有 request_start / request_end
```

检查：

```python
register_middleware(app)
```

是否调用。

---

## 四十、37｜常见错误三：logger 里没有 trace_id

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误现象：

```text
trace_id=-
```

可能原因：

```text
1. setup_logging 没有执行
2. RequestContextFilter 没有加到 handler
3. Middleware 没有执行 set_trace_id
4. 在应用启动阶段打印的日志本来就没有请求上下文
```

启动阶段日志没有 trace_id 是正常的。

请求处理中应该有 trace_id。

---

## 四十一、38｜常见错误四：异常返回里不能序列化
如果 `data` 里面放了不能 JSON 序列化的对象，比如：

```python
data={"error": Exception("xxx")}
```

可能会报序列化错误。

建议：

```text
data 里只放 str / int / float / bool / dict / list / None
```

不要直接放异常对象、数据库连接、复杂类实例。

---

## 四十二、39｜常见错误五：日志打印敏感数据

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不推荐：

```python
logger.info(f"api_key={api_key}")
logger.info(f"prompt={full_prompt}")
logger.info(f"document={document_content}")
```

推荐：

```python
logger.info(f"api_key_prefix={api_key[:6]}***")
logger.info(f"prompt_length={len(full_prompt)}")
logger.info(f"document_length={len(document_content)}")
```

---

## 四十三、40｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| Middleware | 全局请求处理、日志、trace_id、耗时统计 |
| trace_id | 排查 LLM / RAG / Agent 调用问题 |
| request.state / ContextVar | 请求上下文传递 |
| logging.Filter | 日志自动带 trace_id / user_id |
| AppException | 业务异常统一封装 |
| ErrorCode | AI 系统错误码设计 |
| HTTPException Handler | API Key、权限、资源错误统一格式 |
| RequestValidationError Handler | 请求参数错误统一格式 |
| Exception Handler | 未知系统异常兜底 |
| logger.info | 记录正常业务流程 |
| logger.warning | 记录可预期业务异常 |
| logger.exception | 记录系统异常堆栈 |
| x-process-time-ms | 接口耗时分析 |
| x-trace-id | 前后端协同排查问题 |
| LLM_CALL_FAILED | 大模型调用失败 |
| RAG_QUERY_FAILED | 知识库查询失败 |
| TOOL_CALL_FAILED | 工具调用失败 |
| AGENT_RUN_FAILED | Agent 执行失败 |


---

## 四十四、41｜本章完整复习
这一章我们完成了：

```text
1. 理解 Middleware 的作用
2. 理解请求生命周期
3. 创建 request_context.py
4. 使用 ContextVar 保存 trace_id 和 user_id
5. 创建 logging.py
6. 统一日志格式
7. 日志自动注入 trace_id / user_id
8. 创建 middleware.py
9. 每个请求生成 trace_id
10. 统计接口耗时
11. 响应头返回 x-trace-id
12. 响应头返回 x-process-time-ms
13. 创建 ErrorCode
14. 创建 AppException
15. 创建 exception_handlers.py
16. 统一处理 AppException
17. 统一处理 HTTPException
18. 统一处理 RequestValidationError
19. 统一处理未知 Exception
20. ChatService 抛业务异常
21. RAGService 抛业务异常
22. 新增系统异常测试接口
23. 新增 tests/test_exception_api.py
24. 更新 README
```

现在我们的项目已经具备：

```text
统一日志
统一 trace_id
统一异常格式
统一错误码
接口耗时统计
业务异常处理
系统异常兜底
```

这一步完成以后，项目就更像一个真正的企业级 AI 后端了。

---

## 四十五、42｜课后任务一：新增 ToolCallFailed 异常测试
要求：

```text
1. 在 ErrorCode 中已经有 TOOL_CALL_FAILED
2. 新增一个接口 POST /api/v1/tools/mock-call
3. 当 tool_name = "error_tool" 时抛 AppException
4. code 使用 TOOL_CALL_FAILED
5. 测试统一错误响应
```

参考代码：

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.exceptions import AppException, ErrorCode
from app.schemas.response import ApiResponse

router = APIRouter()


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="工具名称")


@router.post("/tools/mock-call", response_model=ApiResponse[dict])
async def mock_call_tool(request: ToolCallRequest) -> ApiResponse[dict]:
    if request.tool_name == "error_tool":
        raise AppException(
            message="工具调用失败",
            code=ErrorCode.TOOL_CALL_FAILED,
            status_code=500,
            data={
                "tool_name": request.tool_name
            },
        )

    return ApiResponse[dict](
        data={
            "tool_name": request.tool_name,
            "result": "ok"
        }
    )
```

---

## 四十六、43｜课后任务二：把 trace_id 加入成功响应
要求：

```text
1. 在 chat.py 的返回 ApiResponse 时增加 trace_id
2. 使用 get_trace_id()
3. 测试成功响应体也带 trace_id
```

参考代码：

```python
from app.core.request_context import get_trace_id


return ApiResponse[ChatResponse](
    data=result,
    trace_id=get_trace_id(),
)
```

---

## 四十七、44｜课后任务三：新增 logger 到 Agent 接口
要求：

```text
1. 在 agents.py 中引入 get_logger
2. run_agent 开始时打印 agent_run_start
3. 成功时打印 agent_run_success
4. 日志中自动带 trace_id 和 user_id
```

参考代码：

```python
from app.core.logging import get_logger

logger = get_logger(__name__)


logger.info(
    f"agent_run_start agent_id={request.agent_id}"
)

logger.info(
    f"agent_run_success agent_id={request.agent_id}"
)
```

---

## 四十八、45｜课后任务四：新增自定义 NotFound 异常
要求：

```text
1. 在 ErrorCode 中增加 CONVERSATION_NOT_FOUND = 40401
2. 在 conversation_service.py 中模拟 conversation_id = c_not_found
3. 抛出 AppException
4. status_code = 404
5. 测试统一错误响应
```

参考代码：

```python
raise AppException(
    message="会话不存在",
    code=40401,
    status_code=404,
    data={
        "conversation_id": conversation_id
    },
)
```

---

## 四十九、46｜课后任务五：画出异常处理链路图
要求画出：

```http
POST /api/v1/chat
```

当 Service 抛出 AppException 时的完整链路：

```text
Request
 ↓
Middleware request_start
 ↓
Dependency
 ↓
Router
 ↓
ChatService
 ↓
raise AppException
 ↓
app_exception_handler
 ↓
ErrorResponse
 ↓
Middleware 添加 Header
 ↓
Response
```

---

## 五十、47｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 10 章我们就讲完了。

这一章非常关键。

因为从这一章开始，我们的 FastAPI 项目已经不只是“能跑接口”。

它开始具备企业级后端的基础能力。

我们完成了：

```text
Middleware
统一日志
trace_id
接口耗时
统一异常
统一错误码
业务异常
参数异常
系统异常兜底
```

==大家一定要记住，AI 应用比普通后端更需要这些能力。==

因为 AI 应用的问题更多、更复杂：

```text
模型调用失败
模型超时
RAG 检索失败
Tool 调用失败
Agent 执行失败
输出格式不稳定
第三方服务不可控
```

如果没有 trace_id、日志、异常处理，后面排查问题会非常痛苦。

现在我们已经有了一个清晰的请求链路：

```text
HTTP Request
 ↓
Middleware
 ↓
Dependency
 ↓
Router
 ↓
Service
 ↓
Repository / LLM / RAG / Agent
 ↓
Exception Handler
 ↓
Middleware
 ↓
HTTP Response
```

这就是企业级 AI 后端的基础骨架。

下一章我们会继续进入：



---

> [!success] 一句话带走
> ==出错能不能快速定位，取决于日志和错误格式有没有提前设计。==

> [!quote] 关于本文档
> 由原始讲义 `第 10 章｜Middleware、异常处理与日志.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
