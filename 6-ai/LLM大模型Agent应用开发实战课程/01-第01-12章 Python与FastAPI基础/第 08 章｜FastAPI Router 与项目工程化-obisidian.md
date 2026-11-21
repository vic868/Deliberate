---
title: "第 08 章｜FastAPI Router 与项目工程化"
chapter: "08"
source: "第 08 章｜FastAPI Router 与项目工程化.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - 工程化
  - 分层
---

# 第 08 章｜FastAPI Router 与项目工程化

> [!abstract] 本章重点
>
> - ==不能把所有代码写进 main.py== — 文件一大就没人看得懂，也没法分工和测试。
> - ==core / api / services / repositories / schemas 分层== — 配置、路由、业务、数据访问、数据结构各归各位。
> - ==.env + pydantic-settings 管配置== — 密钥和地址不写死在代码里。
> - ==api.py 做路由聚合== — 所有 v1 路由先汇总到一个 router，再挂到 app。
> - ==Repository 隔离数据访问== — Service 不直接写 SQL，换存储时只改一层。
>
> [!note] 大白话
>
> - **分层**：把不同职责的代码放不同文件夹，改一处不牵连全身。
> - **环境变量**：把配置放在程序外面，换台机器不用改代码。
>
> [!info] 导航与来源
> - 原始讲义：[[第 08 章｜FastAPI Router 与项目工程化|打开原始讲义]]
> - [[第 07 章｜Pydantic 请求参数与响应模型|上一章｜第 07 章]]
> - [[第 09 章｜FastAPI Dependency Injection 依赖注入|下一章｜第 09 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#五、02｜为什么不能所有代码写在 main.py]]
- [[#六、03｜FastAPI 项目分层思想]]
- [[#七、04｜和 Spring Boot / NestJS 分层对比]]
- [[#八、05｜创建 core 目录]]
- [[#九、06｜创建 .env 配置]]
- [[#十、07｜安装 pydantic-settings]]
- [[#十一、08｜编写 core/config.py]]
- [[#十二、09｜测试配置读取]]
- [[#十三、10｜创建 core/constants.py]]
- [[#十四、11｜升级 main.py：使用 settings]]

---
---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面两章我们已经完成了 FastAPI 的基础能力：

```text
第 06 章｜FastAPI 快速入门
第 07 章｜Pydantic 请求参数与响应模型
```

目前我们已经有了：

```http
GET /api/v1/health
POST /api/v1/chat
POST /api/v1/conversations
GET /api/v1/conversations/{conversation_id}/messages
POST /api/v1/rag/query
```

但是现在项目还处于早期阶段。

如果继续往下写，我们马上会遇到一个问题：

**代码越来越多，main.py 越来越乱，模块边界越来越不清楚。**

比如后面我们还要继续加：

```text
LLM Provider
Prompt 管理
Streaming 流式输出
RAG
Knowledge Base
Agent
Tool Calling
MCP
Multi-Agent
用户系统
权限系统
日志
异常处理
数据库
Redis
```

如果这些东西全部堆在一个文件或者几个文件里，项目很快就会失控。

==所以这一章的核心目标是：==

**把 FastAPI 项目从“能跑的 Demo”，升级成“结构清晰、可维护、可扩展的 AI 后端工程”。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. 为什么不能把所有接口都写在 main.py
2. APIRouter 是什么
3. 如何按业务模块拆分 Router
4. 如何统一注册 v1 API
5. 如何设计 app/api/v1/api.py 聚合路由
6. 如何简化 main.py
7. 如何设计 core 配置模块
8. 如何使用 .env 管理配置
9. 如何使用 pydantic-settings 读取环境变量
10. 如何设计 services 业务层
11. 如何设计 repositories 数据访问层
12. 如何设计 schemas 请求响应模型层
13. 如何设计 models 数据库模型层
14. Controller / Service / Repository 分层思想
15. 如何设计 AI 项目目录结构
16. 如何让 Chat / RAG / Agent 模块边界更清晰
17. 如何避免循环导入
18. 如何为后续 LLM、RAG、Agent、MCP 扩展打基础
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
│   │       └── rag.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── constants.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   └── rag.py
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
│   ├── models/
│   │   └── __init__.py
│   │
│   └── dependencies/
│       └── __init__.py
│
├── tests/
│   ├── test_chat_api.py
│   ├── test_schema.py
│   └── test_project_structure.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

==这一章最核心的变化是新增：==

```text
app/api/v1/api.py
app/core/config.py
app/core/constants.py
app/repositories/
```

并且把：

```text
main.py
```

改成真正的应用入口，而不是业务代码堆积地。

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 08 章。

这一章我们要讲 FastAPI Router 与项目工程化。

前面我们已经能写接口了。

比如：

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

也能写：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    return await chat_with_ai(request)
```

但是企业项目和 Demo 最大的区别，不只是功能多。

更重要的是：

**代码组织方式不一样。**

Demo 可以所有东西都写在一个文件里。

但是企业项目一定要分层。

比如：

```toml
api
= 接口层

schemas
= 请求响应模型

services
= 业务逻辑

repositories
= 数据访问

models
= 数据库模型

core
= 核心配置、日志、异常、常量

dependencies
= FastAPI 依赖注入
```

这样后面项目变大以后，才不会乱。

==所以这一章我们要做一件事：==

**把当前 FastAPI Demo，重构成一个可以继续承载 LLM、RAG、Agent、MCP 的工程结构。**

---

## 五、02｜为什么不能所有代码写在 main.py
### 【重点内容】
我们先看一个反面例子。

很多刚学 FastAPI 的同学，一开始会这样写：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat():
    pass


@app.post("/rag/query")
async def rag_query():
    pass


@app.post("/agent/run")
async def agent_run():
    pass
```

一开始看起来没问题。

但是后面接口越来越多：

```text
health
chat
conversation
rag
knowledge
agent
tool
mcp
user
auth
admin
billing
```

最后 main.py 会变成：

```text
1000 行
2000 行
3000 行
```

这时候就会出现：

```text
不好找代码
不好拆模块
不好测试
不好协作
容易冲突
容易循环导入
```

==所以企业项目一定要拆分。==

main.py 只做一件事：

**创建 FastAPI 应用，注册路由，启动项目。**

业务代码不要堆在 main.py 里。

---

## 六、03｜FastAPI 项目分层思想
### 【实操】
```text
HTTP Request
    ↓
API Router
    ↓
Schema 校验
    ↓
Service 业务逻辑
    ↓
Repository 数据访问
    ↓
Database / Redis / VectorDB / LLM / Tool
```

---

### 【重点内容】
我们先建立一个分层认知。

FastAPI 项目可以按职责分成几层。

第一层：

```text
api
```

也就是接口层。

它负责：

```text
接收请求
读取参数
调用 service
返回响应
```

第二层：

```text
schemas
```

它负责：

```text
请求体模型
响应体模型
参数校验
Swagger 文档结构
```

第三层：

```text
services
```

它负责：

```text
业务逻辑
调用 LLM
调用 RAG
调用 Agent
组合多个 Repository
```

第四层：

```text
repositories
```

它负责：

```text
数据库查询
Redis 查询
向量库查询
数据持久化
```

第五层：

```text
core
```

它负责：

```text
配置
常量
日志
异常
安全设置
```

==所以后面我们写 AI 项目时，不要让某一层职责过重。==

尤其不要把所有逻辑都写在 Router 里面。

---

## 七、04｜和 Spring Boot / NestJS 分层对比
### 【实操】
| **分层职责** | **Spring Boot** | **NestJS** | **FastAPI** |
| --- | --- | --- | --- |
| 接口层 | Controller | Controller | API Router |
| 请求响应对象 | DTO / VO | DTO | Pydantic Schema |
| 业务层 | Service | Service | Service |
| 数据访问层 | Repository / Mapper | Repository | Repository |
| 数据库模型 | Entity | Entity | Model |
| 配置 | application.yml | ConfigModule | core/config.py |
| 依赖注入 | Spring IoC | Nest DI | Depends |
| 全局异常 | ControllerAdvice | Exception Filter | Exception Handler |
| 中间件 | Filter / Interceptor | Middleware / Guard | Middleware / Dependency |


---

### 【重点内容】
如果你有 Java Spring Boot 经验，可以这样理解：

```text
Spring Boot Controller
≈
FastAPI Router

Spring Boot DTO / VO
≈
Pydantic Schema

Spring Boot Service
≈
Python Service

Spring Boot Repository / Mapper
≈
Python Repository

application.yml
≈
.env + core/config.py
```

如果你有 NestJS 经验，也类似：

```text
NestJS Controller
≈
FastAPI Router

NestJS DTO
≈
Pydantic Schema

NestJS Service
≈
Python Service

NestJS Module
≈
FastAPI 项目目录 + router 聚合
```

==所以工程化这件事，本质不是某个框架独有的。==

而是所有企业项目都需要解决的问题：

**代码按职责拆分，模块边界清晰，项目才能长期维护。**

---

## 八、05｜创建 core 目录
### 【实操】
进入项目根目录：

```bash
cd ai-agent-course
```

创建目录：

```bash
mkdir -p app/core
```

Windows PowerShell：

```powershell
mkdir app\core
```

创建文件：

```bash
touch app/core/__init__.py
touch app/core/config.py
touch app/core/constants.py
```

Windows PowerShell：

```powershell
New-Item app\core\__init__.py
New-Item app\core\config.py
New-Item app\core\constants.py
```

---

### 【重点内容】
我们先创建：

```text
app/core
```

这个目录。

core 目录放什么？

==一般放项目的核心基础设施代码，比如：==

```text
配置
常量
日志
异常
安全
中间件
应用初始化
```

这一章我们先放两个文件：

```text
config.py
constants.py
```

后面章节会继续往里面加：

```text
logging.py
exceptions.py
security.py
middleware.py
```

---

## 九、06｜创建 .env 配置
打开项目根目录下的：

```text
.env
```

写入：

```text
APP_NAME=AI Agent Course API
APP_ENV=development
APP_VERSION=0.1.0
API_V1_PREFIX=/api/v1
DEBUG=true

DEFAULT_MODEL=deepseek-chat
SUPPORTED_MODELS=deepseek-chat,qwen-plus,gpt-4o-mini
```

创建：

```text
.env.example
```

写入：

```text
APP_NAME=AI Agent Course API
APP_ENV=development
APP_VERSION=0.1.0
API_V1_PREFIX=/api/v1
DEBUG=true

DEFAULT_MODEL=deepseek-chat
SUPPORTED_MODELS=deepseek-chat,qwen-plus,gpt-4o-mini
```

---

### 【重点内容】
==企业项目里，不建议把配置直接写死在代码里。==

比如：

```python
app = FastAPI(
    title="AI Agent Course API",
    version="0.1.0"
)
```

这在 Demo 里没问题。

但是企业项目里，不同环境配置不一样。

比如：

```text
开发环境
测试环境
预生产环境
生产环境
```

它们可能有不同的：

```text
APP_NAME
DEBUG
数据库地址
Redis 地址
模型配置
API Key
```

所以我们要用：

```text
.env
```

管理配置。

注意：

```text
.env
```

不要提交到 Git。

应该提交：

```text
.env.example
```

给其他开发者参考。

---

## 十、07｜安装 pydantic-settings
### 【实操】
执行：

```bash
uv add pydantic-settings
```

如果使用 pip：

```bash
pip install pydantic-settings
```

---

### 【重点内容】
Pydantic v2 之后，配置管理通常使用：

```text
pydantic-settings
```

它可以帮我们从环境变量和 `.env` 文件里读取配置。

这样我们就可以写：

```python
settings.app_name
settings.app_env
settings.api_v1_prefix
```

而不是在代码里到处写字符串。

---

## 十一、08｜编写 core/config.py
打开：

```text
app/core/config.py
```

写入：

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Course API")
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_v1_prefix: str = Field(default="/api/v1")
    debug: bool = Field(default=True)

    default_model: str = Field(default="deepseek-chat")
    supported_models: str = Field(default="deepseek-chat,qwen-plus,gpt-4o-mini")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def supported_model_list(self) -> list[str]:
        return [
            model.strip()
            for model in self.supported_models.split(",")
            if model.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

### 【重点内容】
这里我们定义了一个：

```python
Settings
```

它继承：

```python
BaseSettings
```

这表示它是一个配置类。

比如：

```python
app_name: str
app_env: str
app_version: str
api_v1_prefix: str
```

这些字段会优先从环境变量或者 `.env` 里面读取。

如果读取不到，就使用默认值。

这里：

```python
model_config = SettingsConfigDict(
    env_file=".env"
)
```

表示从项目根目录下的 `.env` 文件读取配置。

这里还有一个：

```python
@lru_cache
def get_settings()
```

它的作用是缓存 settings 对象。

因为配置不需要每次都重新读取。

最后：

```python
settings = get_settings()
```

后面项目中就可以直接导入使用：

```python
from app.core.config import settings
```

---

## 十二、09｜测试配置读取
创建：

```text
tests/test_project_structure.py
```

写入：

```python
from app.core.config import settings


print(settings.app_name)
print(settings.app_env)
print(settings.app_version)
print(settings.api_v1_prefix)
print(settings.default_model)
print(settings.supported_model_list)
```

运行：

```bash
python tests/test_project_structure.py
```

预期输出类似：

```text
AI Agent Course API
development
0.1.0
/api/v1
deepseek-chat
['deepseek-chat', 'qwen-plus', 'gpt-4o-mini']
```

---

### 【重点内容】
现在我们测试一下配置是否读取成功。

如果能看到：

```text
APP_NAME
APP_ENV
APP_VERSION
API_V1_PREFIX
SUPPORTED_MODELS
```

这些配置，说明 `.env` 和 `Settings` 已经打通。

后面我们不会再把模型列表写死在业务代码里。

而是从：

```python
settings.supported_model_list
```

读取。

这就是工程化的第一步。

---

## 十三、10｜创建 core/constants.py
打开：

```text
app/core/constants.py
```

写入：

```python
from enum import Enum


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ApiTag:
    HEALTH = "Health"
    CHAT = "Chat"
    CONVERSATIONS = "Conversations"
    RAG = "RAG"
    MODELS = "Models"
```

---

### 【重点内容】
constants.py 用来放项目常量。

比如：

```python
AppEnv
```

表示环境类型。

```python
ApiTag
```

表示 Swagger 分组名称。

为什么要抽常量？

因为如果你在项目里到处写字符串：

```python
tags=["Chat"]
tags=["Conversations"]
tags=["RAG"]
```

后面如果想改名字，就要全局搜索。

抽成常量后：

```python
tags=[ApiTag.CHAT]
```

更统一，也更好维护。

---

## 十四、11｜升级 main.py：使用 settings
打开：

```text
app/main.py
```

修改成：

```python
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="Python + FastAPI + LLM + Agent 开发实战",
    version=settings.app_version,
    debug=settings.debug,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {
        "message": settings.app_name,
        "env": settings.app_env,
        "version": settings.app_version,
    }
```

---

### 【重点内容】
这里我们先提前把 main.py 改成理想形态。

大家会看到：

```python
from app.api.v1.api import api_router
```

现在我们不再在 main.py 里面一个一个注册：

```python
chat_router
rag_router
health_router
```

而是统一注册：

```python
api_router
```

然后：

```python
prefix=settings.api_v1_prefix
```

从配置里读取：

```text
/api/v1
```

这样 main.py 就变得非常干净。

它只负责：

```text
创建 app
注册 api_router
定义根路由
```

==这就是我们想要的工程结构。==

---

## 十五、12｜创建 app/api/v1/api.py 聚合路由
创建：

```text
app/api/v1/api.py
```

写入：

```python
from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.rag import router as rag_router
from app.core.constants import ApiTag


api_router = APIRouter()

api_router.include_router(health_router, tags=[ApiTag.HEALTH])
api_router.include_router(chat_router, tags=[ApiTag.CHAT])
api_router.include_router(conversations_router, tags=[ApiTag.CONVERSATIONS])
api_router.include_router(rag_router, tags=[ApiTag.RAG])
```

---

### 【重点内容】
这个文件非常关键。

它的作用是：

**统一聚合 v1 版本下所有 router。**

以前我们在 main.py 里写：

```python
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])
```

现在我们把这些 v1 路由统一放到：

```text
app/api/v1/api.py
```

里面。

main.py 只需要注册一次：

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

这样后面新增模块时，只改 api.py，不用动 main.py。

比如后面新增：

```text
models.py
agents.py
tools.py
mcp.py
```

只需要在 api.py 里面 include_router。

---

## 十六、13｜为什么要有 api.py 聚合层
### 【重点内容】
很多项目一开始没有这个聚合层。

它们会在 main.py 里直接注册所有路由。

比如：

```python
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(tool_router)
app.include_router(user_router)
app.include_router(auth_router)
```

这会导致 main.py 越来越乱。

而我们现在设计成：

```text
main.py
  ↓
api/v1/api.py
  ↓
chat.py
rag.py
conversations.py
health.py
```

好处是：

```text
main.py 更干净
v1 路由集中管理
方便以后新增 v2
模块边界更清楚
```

以后如果要新增 v2：

```text
app/api/v2/api.py
```

main.py 可以同时注册：

```python
app.include_router(v1_api_router, prefix="/api/v1")
app.include_router(v2_api_router, prefix="/api/v2")
```

==这就是 API 版本管理的基础。==

---

## 十七、14｜检查现有 Router 文件
现在确认这些文件已经存在：

```text
app/api/v1/health.py
app/api/v1/chat.py
app/api/v1/conversations.py
app/api/v1/rag.py
```

如果没有，按下面代码补齐。

---

### app/api/v1/health.py
```python
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "version": settings.app_version,
    }


@router.get("/error-demo")
async def error_demo():
    return {
        "message": "error demo will be implemented in exception chapter"
    }
```

---

### app/api/v1/chat.py
```python
from fastapi import APIRouter, Path, Query

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    GenerateTitleRequest,
    GenerateTitleResponse,
)
from app.schemas.response import ApiResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(request: ChatRequest) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(request)

    return ApiResponse[ChatResponse](
        data=result
    )


@router.post("/conversations/{conversation_id}/chat", response_model=ApiResponse[ChatResponse])
async def chat_in_conversation(
    request: ChatRequest,
    conversation_id: str = Path(..., description="会话 ID"),
    debug: bool = Query(default=False, description="是否开启调试模式"),
) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(request)

    if debug:
        result.trace_id = result.trace_id or "debug_trace"

    result.session_id = conversation_id

    return ApiResponse[ChatResponse](
        data=result
    )


@router.post("/chat/title", response_model=ApiResponse[GenerateTitleResponse])
async def generate_chat_title(
    request: GenerateTitleRequest,
) -> ApiResponse[GenerateTitleResponse]:
    title = request.message[:20]

    return ApiResponse[GenerateTitleResponse](
        data=GenerateTitleResponse(title=title)
    )
```

---

### app/api/v1/conversations.py
```python
from fastapi import APIRouter, Path

from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationMessagesResponse,
    ConversationResponse,
)
from app.schemas.response import ApiResponse
from app.services.conversation_service import (
    create_conversation,
    get_conversation_messages,
)

router = APIRouter()


@router.post("/conversations", response_model=ApiResponse[ConversationResponse])
async def create_new_conversation(
    request: ConversationCreateRequest,
) -> ApiResponse[ConversationResponse]:
    result = await create_conversation(request)

    return ApiResponse[ConversationResponse](
        data=result
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[ConversationMessagesResponse],
)
async def get_messages(
    conversation_id: str = Path(..., description="会话 ID"),
) -> ApiResponse[ConversationMessagesResponse]:
    result = await get_conversation_messages(conversation_id)

    return ApiResponse[ConversationMessagesResponse](
        data=result
    )
```

---

### app/api/v1/rag.py
```python
from fastapi import APIRouter

from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.schemas.response import ApiResponse
from app.services.rag_service import query_rag

router = APIRouter()


@router.post("/rag/query", response_model=ApiResponse[RAGQueryResponse])
async def rag_query(
    request: RAGQueryRequest,
) -> ApiResponse[RAGQueryResponse]:
    result = await query_rag(request)

    return ApiResponse[RAGQueryResponse](
        data=result
    )
```

---

### 【重点内容】
这里我们把每个业务模块的 Router 都单独放到自己的文件里。

比如：

```text
health.py
= 健康检查

chat.py
= AI 对话

conversations.py
= 会话管理

rag.py
= 知识库问答
```

这样每个文件职责都很清楚。

后面如果要找 Chat 接口，就去：

```text
app/api/v1/chat.py
```

如果要找 RAG 接口，就去：

```text
app/api/v1/rag.py
```

这比所有接口写在 main.py 里清楚很多。

---

## 十八、15｜启动并测试路由是否正常
启动：

```bash
uv run uvicorn app.main:app --reload
```

浏览器打开：

```http
http://127.0.0.1:8000/docs
```

应该看到分组：

```text
Health
Chat
Conversations
RAG
```

测试健康检查：

```http
GET /api/v1/health
```

返回：

```json
{
  "status": "ok",
  "service": "AI Agent Course API",
  "env": "development",
  "version": "0.1.0"
}
```

测试根路径：

```http
GET /
```

返回：

```json
{
  "message": "AI Agent Course API",
  "env": "development",
  "version": "0.1.0"
}
```

---

### 【重点内容】
现在我们启动项目。

如果一切正常，说明：

```text
main.py
 ↓
api/v1/api.py
 ↓
各业务 router
```

已经打通。

从浏览器访问：

```text
/docs
```

能看到所有接口分组，就说明 Router 注册成功。

==这一章最关键的第一步已经完成了。==

---

## 十九、16｜创建 repositories 目录
### 【实操】
创建目录：

```bash
mkdir -p app/repositories
```

Windows PowerShell：

```powershell
mkdir app\repositories
```

创建文件：

```bash
touch app/repositories/__init__.py
touch app/repositories/conversation_repository.py
touch app/repositories/knowledge_repository.py
```

Windows PowerShell：

```powershell
New-Item app\repositories\__init__.py
New-Item app\repositories\conversation_repository.py
New-Item app\repositories\knowledge_repository.py
```

---

### 【重点内容】
接下来我们创建：

```text
repositories
```

目录。

Repository 是数据访问层。

它负责：

```text
查询数据库
写入数据库
查询 Redis
查询向量数据库
封装数据存储细节
```

现在我们还没有真正接 PostgreSQL、Redis、pgvector。

==所以这一章先用内存假数据模拟。==

但是目录和分层先搭好。

后面接数据库时，只需要替换 repository 里的实现。

---

## 二十、17｜编写 ConversationRepository
打开：

```text
app/repositories/conversation_repository.py
```

写入：

```python
from app.schemas.chat import ChatMessage, MessageRole
from app.schemas.conversation import ConversationCreateRequest


class ConversationRepository:
    def __init__(self):
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, list[ChatMessage]] = {}

    async def create(self, conversation_id: str, request: ConversationCreateRequest) -> dict:
        conversation = {
            "conversation_id": conversation_id,
            "title": request.title,
        }

        self._conversations[conversation_id] = conversation
        self._messages[conversation_id] = []

        return conversation

    async def get_messages(self, conversation_id: str) -> list[ChatMessage]:
        if conversation_id not in self._messages:
            return [
                ChatMessage(
                    role=MessageRole.USER,
                    content="什么是 AI Agent？"
                ),
                ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="AI Agent 是能够调用工具完成任务的智能体。"
                )
            ]

        return self._messages[conversation_id]


conversation_repository = ConversationRepository()
```

---

### 【重点内容】
这里我们写了一个：

```python
ConversationRepository
```

它现在只是用内存字典模拟数据库。

比如：

```python
self._conversations
self._messages
```

真实项目里，这里会替换成：

```text
PostgreSQL
MySQL
MongoDB
Redis
```

但是 service 层不需要关心底层到底怎么存。

Service 只需要调用：

```python
conversation_repository.create()
conversation_repository.get_messages()
```

==这就是 Repository 的价值：==

**把数据访问细节和业务逻辑隔离开。**

---

## 二十一、18｜改造 ConversationService 使用 Repository
打开：

```text
app/services/conversation_service.py
```

修改：

```python
import uuid

from app.repositories.conversation_repository import conversation_repository
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationMessagesResponse,
    ConversationResponse,
)


async def create_conversation(
    request: ConversationCreateRequest,
) -> ConversationResponse:
    conversation_id = f"c_{uuid.uuid4().hex[:8]}"

    conversation = await conversation_repository.create(
        conversation_id=conversation_id,
        request=request,
    )

    return ConversationResponse(
        conversation_id=conversation["conversation_id"],
        title=conversation["title"],
    )


async def get_conversation_messages(
    conversation_id: str,
) -> ConversationMessagesResponse:
    messages = await conversation_repository.get_messages(conversation_id)

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )
```

---

### 【重点内容】
现在 ConversationService 不再自己构造所有数据。

它开始调用：

```python
conversation_repository
```

这就形成了：

```text
Router
 ↓
Service
 ↓
Repository
```

的结构。

Router 负责接收请求。

Service 负责编排业务逻辑。

Repository 负责数据访问。

后面接真实数据库时，Router 和 Service 可以尽量少改，只改 Repository。

这就是分层的好处。

---

## 二十二、19｜编写 KnowledgeRepository
打开：

```text
app/repositories/knowledge_repository.py
```

写入：

```python
from typing import Any

from app.schemas.chat import SourceDocument


class KnowledgeRepository:
    async def search_documents(
        self,
        question: str,
        knowledge_base_id: str,
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SourceDocument]:
        return [
            SourceDocument(
                document_id="doc_001",
                title="AI Agent 课程资料",
                content="RAG 是检索增强生成，用于让大模型结合外部知识回答问题。",
                score=0.92,
                metadata={
                    "knowledge_base_id": knowledge_base_id,
                    "page": 1,
                    "filter": metadata_filter or {},
                },
            )
        ][:top_k]


knowledge_repository = KnowledgeRepository()
```

---

### 【重点内容】
现在我们给 RAG 模块也加一个 Repository。

它叫：

```python
KnowledgeRepository
```

负责搜索知识库文档。

现在我们用假数据。

后面真正做 RAG 的时候，这里会替换成：

```text
pgvector
Milvus
Qdrant
Elasticsearch
向量数据库
```

但是上层服务：

```python
rag_service
```

可以继续调用：

```python
knowledge_repository.search_documents()
```

这就是工程设计的意义。

---

## 二十三、20｜改造 RAGService 使用 Repository
打开：

```text
app/services/rag_service.py
```

修改：

```python
import uuid

from app.repositories.knowledge_repository import knowledge_repository
from app.schemas.chat import TokenUsage
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse


async def query_rag(request: RAGQueryRequest) -> RAGQueryResponse:
    sources = await knowledge_repository.search_documents(
        question=request.question,
        knowledge_base_id=request.knowledge_base_id,
        top_k=request.top_k,
        metadata_filter=request.metadata_filter,
    )

    answer = f"根据知识库 {request.knowledge_base_id} 的内容，RAG 是检索增强生成。"

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
现在 RAGService 也不直接构造文档了。

它通过：

```python
knowledge_repository.search_documents()
```

获取检索结果。

后面我们真正接入向量数据库时，RAGService 的主体流程可以保持不变。

只需要改 KnowledgeRepository 的内部实现。

这就是好的分层设计：

```text
改底层实现
不影响上层接口
```

---

## 二十四、21｜ChatService 使用 settings
打开：

```text
app/services/chat_service.py
```

修改 model 校验逻辑相关代码。

如果之前 ChatRequest 里已经校验 model，可以先在 Service 里使用默认模型。

完整代码示例：

```python
import asyncio
import uuid

from app.core.config import settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRole,
    SourceDocument,
    TokenUsage,
)


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    latest_user_message = get_latest_user_message(request)
    model = request.model or settings.default_model

    if "AI Agent" in latest_user_message:
        answer = "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。"
    elif "RAG" in latest_user_message:
        answer = "RAG 是检索增强生成，用于让大模型结合企业私有知识库进行回答。"
    elif "LangGraph" in latest_user_message:
        answer = "LangGraph 适合开发有状态、有分支、有流程控制的复杂 Agent。"
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{latest_user_message}」。"

    usage = TokenUsage(
        prompt_tokens=count_mock_tokens_from_messages(request),
        completion_tokens=len(answer),
        total_tokens=count_mock_tokens_from_messages(request) + len(answer),
    )

    sources = build_mock_sources(latest_user_message)

    return ChatResponse(
        answer=answer,
        model=model,
        session_id=request.session_id or f"s_{uuid.uuid4().hex[:8]}",
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=usage,
        sources=sources,
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
    )


def get_latest_user_message(request: ChatRequest) -> str:
    for message in reversed(request.messages):
        if message.role == MessageRole.USER:
            return message.content

    return request.messages[-1].content


def count_mock_tokens_from_messages(request: ChatRequest) -> int:
    return sum(len(message.content) for message in request.messages)


def build_mock_sources(question: str) -> list[SourceDocument]:
    if "RAG" not in question and "知识库" not in question:
        return []

    return [
        SourceDocument(
            document_id="doc_001",
            title="企业知识库说明文档",
            content="RAG 是 Retrieval Augmented Generation，用于结合外部知识增强大模型回答。",
            score=0.89,
            metadata={
                "source": "mock",
                "page": 1,
            },
        )
    ]
```

---

### 【重点内容】
这里我们在 ChatService 里面使用了：

```python
settings.default_model
```

这表示默认模型从配置里来。

后面如果我们想把默认模型从：

```text
deepseek-chat
```

改成：

```text
qwen-plus
```

不用改代码。

只需要改：

```text
.env
```

这就是配置管理的价值。

---

## 二十五、22｜把 ChatRequest 的模型校验改成使用 settings
打开：

```text
app/schemas/chat.py
```

找到：

```python
@field_validator("model")
```

修改为：

```python
from app.core.config import settings
```

然后：

```python
@field_validator("model")
@classmethod
def validate_model(cls, value: str) -> str:
    if value not in settings.supported_model_list:
        raise ValueError(f"不支持的模型：{value}")

    return value
```

完整片段：

```python
from app.core.config import settings


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(
        ...,
        min_length=1,
        description="对话消息列表"
    )
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="模型温度")
    stream: bool = Field(default=False, description="是否流式输出")
    session_id: str | None = Field(default=None, description="会话 ID")
    user_id: str | None = Field(default=None, description="用户 ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if value not in settings.supported_model_list:
            raise ValueError(f"不支持的模型：{value}")

        return value
```

---

### 【重点内容】
之前我们把支持的模型写死在代码里：

```python
supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]
```

现在我们改成从配置读取：

```python
settings.supported_model_list
```

这就更工程化了。

后面企业项目里，模型列表可能来自：

```text
配置文件
数据库
管理后台
租户配置
模型供应商配置
```

这一章我们先用 `.env` 管理。

后面再升级成数据库管理。

---

## 二十六、23｜新增 Models Router
现在我们新增一个模型列表接口。

创建：

```text
app/api/v1/models.py
```

写入：

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.response import ApiResponse

router = APIRouter()


class ModelInfo(BaseModel):
    name: str = Field(..., description="模型名称")
    provider: str = Field(default="mock", description="模型厂商")
    support_stream: bool = Field(default=True, description="是否支持流式输出")


class ModelListResponse(BaseModel):
    models: list[ModelInfo] = Field(default_factory=list, description="模型列表")


@router.get("/models", response_model=ApiResponse[ModelListResponse])
async def list_models() -> ApiResponse[ModelListResponse]:
    models = [
        ModelInfo(
            name=model,
            provider=get_provider_name(model),
            support_stream=True,
        )
        for model in settings.supported_model_list
    ]

    return ApiResponse[ModelListResponse](
        data=ModelListResponse(models=models)
    )


def get_provider_name(model: str) -> str:
    if model.startswith("deepseek"):
        return "deepseek"

    if model.startswith("qwen"):
        return "qwen"

    if model.startswith("gpt"):
        return "openai"

    return "unknown"
```

---

### 【重点内容】
这里我们新增了一个：

```http
GET /api/v1/models
```

接口。

它返回当前系统支持哪些模型。

这个接口后面很有用。

前端可以通过它渲染模型下拉框。

比如：

```text
deepseek-chat
qwen-plus
gpt-4o-mini
```

而不是前端写死模型列表。

这也是工程化思维：

**后端提供配置能力，前端动态渲染。**

---

## 二十七、24｜注册 Models Router
修改：

```text
app/core/constants.py
```

确认有：

```python
class ApiTag:
    HEALTH = "Health"
    CHAT = "Chat"
    CONVERSATIONS = "Conversations"
    RAG = "RAG"
    MODELS = "Models"
```

修改：

```text
app/api/v1/api.py
```

增加导入：

```python
from app.api.v1.models import router as models_router
```

注册：

```python
api_router.include_router(models_router, tags=[ApiTag.MODELS])
```

完整代码：

```python
from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.models import router as models_router
from app.api.v1.rag import router as rag_router
from app.core.constants import ApiTag


api_router = APIRouter()

api_router.include_router(health_router, tags=[ApiTag.HEALTH])
api_router.include_router(chat_router, tags=[ApiTag.CHAT])
api_router.include_router(conversations_router, tags=[ApiTag.CONVERSATIONS])
api_router.include_router(rag_router, tags=[ApiTag.RAG])
api_router.include_router(models_router, tags=[ApiTag.MODELS])
```

---

### 【重点内容】
现在新增 Models Router 以后，我们只改了：

```text
app/api/v1/api.py
```

没有改 main.py。

这就是聚合路由的好处。

以后新增：

```text
agents.py
tools.py
mcp.py
knowledge.py
```

也是一样。

只要在 api.py 注册即可。

main.py 保持稳定。

---

## 二十八、25｜再次测试接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

访问 Swagger：

```http
http://127.0.0.1:8000/docs
```

应该看到新分组：

```text
Models
```

测试：

```http
GET /api/v1/models
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "models": [
      {
        "name": "deepseek-chat",
        "provider": "deepseek",
        "support_stream": true
      },
      {
        "name": "qwen-plus",
        "provider": "qwen",
        "support_stream": true
      },
      {
        "name": "gpt-4o-mini",
        "provider": "openai",
        "support_stream": true
      }
    ]
  }
}
```

---

## 二十九、26｜现在的请求链路
### 【实操】
```http
GET /api/v1/models
    ↓
main.py
    ↓
api/v1/api.py
    ↓
api/v1/models.py
    ↓
settings.supported_model_list
    ↓
ApiResponse[ModelListResponse]
```

---

### 【重点内容】
现在我们看一下请求链路。

用户访问：

```http
GET /api/v1/models
```

请求先进入：

```text
main.py
```

因为 main.py 注册了：

```python
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

然后进入：

```text
api/v1/api.py
```

再进入：

```text
api/v1/models.py
```

最后读取：

```python
settings.supported_model_list
```

返回统一响应。

==这就是一个完整的工程化链路。==

---

## 三十、27｜项目目录职责说明
### 【实操】
```text
app/
├── api/              接口层
├── core/             核心配置
├── schemas/          请求响应模型
├── services/         业务逻辑
├── repositories/     数据访问
├── models/           数据库模型
└── dependencies/     依赖注入
```

---

### 【重点内容】
现在我们统一解释一下目录职责。

```text
api
```

只放接口。

比如：

```text
chat.py
rag.py
models.py
```

```text
schemas
```

只放 Pydantic 模型。

比如：

```text
ChatRequest
ChatResponse
RAGQueryRequest
ApiResponse
```

```text
services
```

只放业务逻辑。

比如：

```text
chat_with_ai
query_rag
create_conversation
```

```text
repositories
```

只放数据访问逻辑。

比如：

```text
查询会话
查询知识库
保存消息
搜索向量库
```

```text
core
```

放基础设施。

比如：

```text
配置
日志
异常
常量
安全
```

```text
models
```

后面放数据库 ORM 模型。

```text
dependencies
```

后面放 FastAPI 依赖注入，比如当前用户、数据库会话、权限校验。

每个目录都只做自己的事情。

这就是工程化。

---

## 三十一、28｜为什么 schemas 不等于 models
### 【重点内容】
很多同学会混淆两个概念：

```text
schemas
models
```

在我们这个项目里：

```text
schemas
= Pydantic 请求响应模型

models
= 数据库 ORM 模型
```

比如：

```python
class ChatRequest(BaseModel):
    pass
```

它是 schema。

它表示接口请求体。

后面我们接数据库时，可能会写：

```python
class Conversation(Base):
    pass
```

它是 model。

它表示数据库表。

不要把所有东西都叫 model。

否则项目后面会乱。

所以我们约定：

```text
请求响应
放 schemas

数据库表
放 models
```

---

## 三十二、29｜为什么 Service 不直接写 SQL
### 【重点内容】
有些同学会问：

老师，为什么 Service 不能直接查数据库？

当然可以。

小项目里直接写也没问题。

但是企业项目里，建议：

```text
Service
负责业务编排

Repository
负责数据访问
```

比如 ChatService 以后可能要做很多事情：

```text
读取会话
保存用户消息
调用 LLM
保存 AI 回复
统计 token
写日志
返回响应
```

如果里面再直接写 SQL，很快会变得很复杂。

==所以我们把数据访问放到 Repository。==

这样结构更清晰。

---

## 三十三、30｜AI 项目中的典型分层链路
### 【实操】
```http
POST /api/v1/chat
    ↓
chat.py
    ↓
ChatRequest
    ↓
chat_service.py
    ↓
conversation_repository.py
    ↓
llm_provider.py
    ↓
ChatResponse
    ↓
ApiResponse[ChatResponse]
```

---

### 【重点内容】
后面真实 Chat 接口大概会是这样。

第一步，接口层接收请求：

```text
chat.py
```

第二步，Pydantic 校验请求：

```text
ChatRequest
```

第三步，进入业务逻辑：

```text
chat_service.py
```

第四步，读取历史消息：

```text
conversation_repository.py
```

第五步，调用模型：

```text
llm_provider.py
```

第六步，生成响应：

```text
ChatResponse
```

第七步，统一返回：

```text
ApiResponse[ChatResponse]
```

==这就是企业级 AI Chat 的基本链路。==

---

## 三十四、31｜避免循环导入
### 【重点内容】
项目一拆分，就容易遇到一个问题：

```text
循环导入
```

比如：

```text
chat_service.py
导入 chat.py

chat.py
又导入 chat_service.py
```

这样就会报错。

我们要遵守一个方向：

```text
api
  ↓
services
  ↓
repositories
  ↓
models
```

上层可以依赖下层。

下层不要反过来依赖上层。

比如：

```text
chat.py 可以导入 chat_service.py

chat_service.py 不要导入 chat.py
```

同理：

```text
service 可以导入 repository

repository 不要导入 service
```

这就是模块依赖方向。

---

## 三十五、32｜推荐的导入方向
### 【实操】
```text
允许：

api -> schemas
api -> services
services -> schemas
services -> repositories
repositories -> schemas
repositories -> models
core -> 独立基础能力

避免：

services -> api
repositories -> services
schemas -> api
core -> services
```

---

### 【重点内容】
大家可以先记住这张图。

允许的方向：

```text
api 调 service
service 调 repository
repository 调 model
```

不要反过来。

如果你发现某个底层模块需要导入上层模块，通常说明你的设计有问题。

比如：

```text
repository 需要导入 router
```

这肯定不合理。

---

## 三十六、33｜创建应用工厂 create_app
现在我们进一步优化 main.py。

打开：

```text
app/main.py
```

修改成：

```python
from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Python + FastAPI + LLM + Agent 开发实战",
        version=settings.app_version,
        debug=settings.debug,
    )

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
这里我们使用了一个常见写法：

```python
def create_app() -> FastAPI:
```

它叫应用工厂。

也就是用一个函数创建 app。

这样有什么好处？

第一：

```text
main.py 更清晰
```

第二：

```text
测试时可以单独创建 app
```

第三：

```text
以后可以根据不同配置创建不同 app
```

比如测试环境可以创建：

```python
create_app()
```

然后用 FastAPI TestClient 测试接口。

现在我们先把结构搭好。

---

## 三十七、34｜确认 uvicorn 启动方式不变
虽然 main.py 改成了 create_app，但是最后仍然有：

```python
app = create_app()
```

所以启动命令不变：

```bash
uv run uvicorn app.main:app --reload
```

---

### 【重点内容】
大家注意。

虽然我们把 app 创建逻辑放到了：

```python
create_app()
```

但是文件底部还有：

```python
app = create_app()
```

==所以 uvicorn 还是能找到：==

```text
app.main:app
```

因此启动命令不变。

如果没有这行：

```python
app = create_app()
```

uvicorn 就找不到 app 对象。

---

## 三十八、35｜用 curl 测试所有核心接口

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

启动服务后测试：

```bash
curl http://127.0.0.1:8000/
```

测试 health：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

测试 models：

```bash
curl http://127.0.0.1:8000/api/v1/models
```

测试 chat：

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

测试 RAG：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "什么是 RAG？",
    "knowledge_base_id": "kb_001",
    "top_k": 5,
    "rerank": true,
    "metadata_filter": {}
  }'
```

---

## 三十九、36｜新增 README 项目结构说明
打开：

```text
README.md
```

追加：

```markdown
## 项目结构

```
app/
├── api/              FastAPI 接口层
==├── core/             核心配置、常量、日志、异常==
├── schemas/          Pydantic 请求与响应模型
├── services/         业务逻辑层
├── repositories/     数据访问层
├── models/           数据库 ORM 模型
└── dependencies/     FastAPI 依赖注入
```text

## 启动项目
```
uv run uvicorn app.main:app --reload
```text

## API 文档
```
http://127.0.0.1:8000/docs
```text

## 当前接口
```
GET  /api/v1/health
GET  /api/v1/models
POST /api/v1/chat
POST /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}/messages
POST /api/v1/rag/query
```text

```
---

### 【重点内容】

README 不要只写项目名称。

企业项目 README 至少要告诉别人：

```text
项目怎么启动
目录结构是什么
当前有哪些接口
配置文件怎么写
```

后面你的学员把这个项目写到简历里，README 也会体现工程习惯。

---

## 四十、37｜当前完整项目结构复盘
现在项目结构应该类似：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       ├── models.py
│   │       └── rag.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── constants.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   └── rag.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chat_service.py
│   │   ├── conversation_service.py
│   │   └── rag_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── conversation_repository.py
│   │   └── knowledge_repository.py
│   ├── models/
│   │   └── __init__.py
│   └── dependencies/
│       └── __init__.py
├── tests/
│   ├── test_chat_api.py
│   ├── test_schema.py
│   └── test_project_structure.py
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## 四十一、38｜常见错误一：忘记创建 **init**.py

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
ModuleNotFoundError
```

或者：

```text
No module named app.api.v1.xxx
```

解决：

确认这些目录下有：

```text
__init__.py
```

例如：

```text
app/__init__.py
app/api/__init__.py
app/api/v1/__init__.py
app/core/__init__.py
app/schemas/__init__.py
app/services/__init__.py
app/repositories/__init__.py
```

---

### 【重点内容】
Python 项目里，`__init__.py` 很重要。

它表示这个目录是一个 Python 包。

虽然新版本 Python 对命名空间包支持更灵活，但在课程项目里，我建议大家显式创建 `__init__.py`。

这样更清楚，也更不容易出路径问题。

---

## 四十二、39｜常见错误二：从错误目录启动项目

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```bash
uv run uvicorn app.main:app --reload
```

但是当前目录不是：

```text
ai-agent-course
```

就可能报：

```text
ModuleNotFoundError: No module named 'app'
```

解决：

```bash
pwd
```

确认当前目录。

然后：

```bash
cd ai-agent-course
uv run uvicorn app.main:app --reload
```

---

## 四十三、40｜常见错误三：api.py 循环导入
错误做法：

```python
# chat.py
from app.api.v1.api import api_router
```

然后：

```python
# api.py
from app.api.v1.chat import router as chat_router
```

这就循环了。

正确做法：

```text
chat.py 只定义自己的 router

api.py 负责导入 chat_router 并注册

chat.py 不要反过来导入 api.py
```

---

## 四十四、41｜常见错误四：配置没有生效

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

如果 `.env` 改了，但是运行结果没变。

检查：

```text
1. .env 是否在项目根目录
2. 字段名是否写对
3. 是否重启服务
4. SettingsConfigDict(env_file=".env") 是否配置
5. 是否存在系统环境变量覆盖
```

建议改完 `.env` 后重启：

```bash
Control + C
uv run uvicorn app.main:app --reload
```

---

## 四十五、42｜常见错误五：Repository 单例存储只适合 Demo
这一章我们写了：

```python
conversation_repository = ConversationRepository()
```

并且内部用：

```python
self._conversations
```

保存数据。

这只是为了演示分层。

注意：

```text
服务重启后数据会丢
多进程下数据不共享
不适合生产环境
```

后面接 PostgreSQL 后，这里会替换成真实数据库。

---

## 四十六、43｜本章知识点和 AI 开发场景对应表
| 工程化知识点 | AI 开发场景 |
| --- | --- |
| `APIRouter` | 拆分 Chat / RAG / Agent / Tool / MCP 接口 |
| `api/v1/api.py` | 统一注册 v1 API |
| `settings` | 管理模型、环境、API 前缀、调试开关 |
| `.env` | 管理本地配置和敏感变量 |
| `core/` | 配置、日志、异常、安全、常量 |
| `schemas/` | ChatRequest、RAGQueryRequest、AgentRunRequest |
| `services/` | LLM 调用、RAG 编排、Agent 执行 |
| `repositories/` | 数据库、Redis、向量库访问 |
| `models/` | SQLAlchemy ORM 模型 |
| `dependencies/` | 当前用户、数据库会话、权限校验 |
| `create_app()` | 应用工厂，方便测试和扩展 |
| `ApiTag` | Swagger 分组统一管理 |
| `API_V1_PREFIX` | API 版本管理 |
| Repository 分层 | 后续替换 PostgreSQL / pgvector 更方便 |
| 避免循环导入 | 大型项目保持模块依赖清晰 |


---

## 四十七、44｜本章完整复习
这一章我们完成了：

```text
1. 理解为什么 main.py 不能堆业务代码
2. 设计 FastAPI 企业级目录结构
3. 创建 core/config.py
4. 使用 .env 管理配置
5. 使用 pydantic-settings 读取配置
6. 创建 core/constants.py
7. 创建 api/v1/api.py 聚合路由
8. 简化 main.py
9. 新增 Models Router
10. 创建 repositories 目录
11. 创建 ConversationRepository
12. 创建 KnowledgeRepository
13. 改造 ConversationService
14. 改造 RAGService
15. ChatService 使用 settings
16. 梳理 api / schemas / services / repositories / core 职责
17. 讲清楚 schemas 和 models 的区别
18. 讲清楚 Service 和 Repository 的边界
19. 学会避免循环导入
20. 完成当前项目结构升级
```

现在我们的项目已经从：

```text
能跑接口的 FastAPI Demo
```

升级成：

```text
结构清晰的 AI 后端工程骨架
```

这一步非常重要。

因为后面我们要继续加：

```text
Dependency Injection
Middleware
异常处理
日志系统
数据库
Redis
LLM Provider
RAG
Agent
MCP
```

如果没有这一章的工程化结构，后面代码会越来越乱。

---

## 四十八、45｜课后任务一：新增 Agent Router
要求：

```text
1. 创建 app/api/v1/agents.py
2. 创建 GET /agents
3. 返回模拟 Agent 列表
4. 在 api/v1/api.py 中注册
5. Swagger 中显示 Agents 分组
```

参考答案：

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.response import ApiResponse

router = APIRouter()


class AgentInfo(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称")
    description: str = Field(..., description="Agent 描述")


class AgentListResponse(BaseModel):
    agents: list[AgentInfo] = Field(default_factory=list, description="Agent 列表")


@router.get("/agents", response_model=ApiResponse[AgentListResponse])
async def list_agents() -> ApiResponse[AgentListResponse]:
    return ApiResponse[AgentListResponse](
        data=AgentListResponse(
            agents=[
                AgentInfo(
                    agent_id="agent_chat",
                    name="通用聊天助手",
                    description="用于普通 AI Chat 场景",
                ),
                AgentInfo(
                    agent_id="agent_rag",
                    name="知识库问答助手",
                    description="用于企业知识库问答场景",
                ),
            ]
        )
    )
```

---

## 四十九、46｜课后任务二：把 Agents 加入 ApiTag
修改：

```text
app/core/constants.py
```

增加：

```python
class ApiTag:
    HEALTH = "Health"
    CHAT = "Chat"
    CONVERSATIONS = "Conversations"
    RAG = "RAG"
    MODELS = "Models"
    AGENTS = "Agents"
```

修改：

```text
app/api/v1/api.py
```

增加：

```python
from app.api.v1.agents import router as agents_router

api_router.include_router(agents_router, tags=[ApiTag.AGENTS])
```

---

## 五十、47｜课后任务三：新增 AgentService
要求：

```text
1. 创建 app/services/agent_service.py
2. 把 Agent 列表逻辑从 router 移到 service
3. router 只负责调用 service
```

参考答案：

```python
from app.api.v1.agents import AgentInfo, AgentListResponse


async def list_agent_service() -> AgentListResponse:
    return AgentListResponse(
        agents=[
            AgentInfo(
                agent_id="agent_chat",
                name="通用聊天助手",
                description="用于普通 AI Chat 场景",
            ),
            AgentInfo(
                agent_id="agent_rag",
                name="知识库问答助手",
                description="用于企业知识库问答场景",
            ),
        ]
    )
```

提示：

```text
更推荐把 AgentInfo / AgentListResponse 放到 app/schemas/agent.py
不要长期放在 router 文件里。
```

---

## 五十一、48｜课后任务四：新增 app/schemas/agent.py
要求：

```text
1. 创建 app/schemas/agent.py
2. 定义 AgentInfo
3. 定义 AgentListResponse
4. 修改 agents.py 和 agent_service.py 的导入路径
```

参考答案：

```python
from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent 名称")
    description: str = Field(..., description="Agent 描述")


class AgentListResponse(BaseModel):
    agents: list[AgentInfo] = Field(default_factory=list, description="Agent 列表")
```

---

## 五十二、49｜课后任务五：画出当前项目调用链路
要求画出：

```http
GET /api/v1/agents
```

从请求到响应的完整链路：

```text
main.py
 ↓
api/v1/api.py
 ↓
api/v1/agents.py
 ↓
services/agent_service.py
 ↓
schemas/agent.py
 ↓
ApiResponse[AgentListResponse]
```

这个任务是为了训练大家的工程结构意识。

---

## 五十三、50｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【最终重点内容】
好了，到这里，第 08 章我们就讲完了。

这一章我们没有讲太多新的业务功能。

但是这一章非常重要。

因为我们做了一件企业项目必须做的事情：

**项目工程化。**

前面我们的项目只是能跑。

现在我们的项目开始变得清晰。

我们把目录拆成了：

```text
api
core
schemas
services
repositories
models
dependencies
```

每一层都有自己的职责。

```text
api
负责接口

schemas
负责请求响应模型

services
负责业务逻辑

repositories
负责数据访问

core
负责配置和基础设施
```

同时我们也把路由注册升级成：

```text
main.py
 ↓
api/v1/api.py
 ↓
各业务 router
```

这样以后新增：

```text
LLM
RAG
Agent
Tool
MCP
User
Auth
```

都不会让 main.py 越来越乱。

我们还引入了：

```text
.env
pydantic-settings
settings
constants
repositories
create_app
```

这些都是企业级 FastAPI 项目中非常常见的工程能力。

大家一定要记住：

**项目能跑只是第一步，项目结构清晰才是长期可维护的基础。**

下一章我们会继续往企业级方向走



---

> [!success] 一句话带走
> ==工程化不是文件变多，而是每个文件只有一个改它的理由。==

> [!quote] 关于本文档
> 由原始讲义 `第 08 章｜FastAPI Router 与项目工程化.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
