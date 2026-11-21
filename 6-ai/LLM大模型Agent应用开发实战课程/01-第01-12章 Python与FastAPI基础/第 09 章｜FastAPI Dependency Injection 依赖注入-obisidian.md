---
title: "第 09 章｜FastAPI Dependency Injection 依赖注入"
chapter: "09"
source: "第 09 章｜FastAPI Dependency Injection 依赖注入.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - 依赖注入
---

# 第 09 章｜FastAPI Dependency Injection 依赖注入

> [!abstract] 本章重点
>
> - ==Depends 的本质是「调用前先跑一个函数」== — 框架把返回值塞给参数，公共逻辑就抽出来了。
> - ==settings 抽成依赖，随时可替换== — 测试时换成假配置很方便。
> - ==从 Header 读当前用户== — 鉴权逻辑写一次，多个接口复用。
> - ==API Key 校验放 Router 级别== — 整组接口统一保护，不用每个函数都写一遍。
> - ==yield 依赖可以做收尾清理== — 请求前建连接、请求后关连接。
>
> [!note] 大白话
>
> - **依赖注入**：你要的东西不用自己造，框架在调用前递给你。
> - **Header**：请求头里带的附加信息，常用来放 token 或 API Key。
>
> [!info] 导航与来源
> - 原始讲义：[[第 09 章｜FastAPI Dependency Injection 依赖注入|打开原始讲义]]
> - [[第 08 章｜FastAPI Router 与项目工程化|上一章｜第 08 章]]
> - [[第 10 章｜Middleware、异常处理与日志|下一章｜第 10 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#Dependency Injection 依赖注入]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#Dependency Injection 依赖注入]]
- [[#五、02｜为什么需要依赖注入]]
- [[#六、03｜依赖注入解决什么问题]]
- [[#七、04｜和 Spring Boot / NestJS 对比]]
- [[#八、05｜创建 dependencies 目录]]
- [[#九、06｜第一个 Depends 示例]]
- [[#十、07｜Depends 的本质]]
- [[#十一、08｜把 settings 抽成依赖]]
- [[#十二、09｜定义 User Schema]]

---
---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们完成了 FastAPI 项目工程化。

当前项目已经拆成了：

```text
app/
├── api/
├── core/
├── schemas/
├── services/
├── repositories/
├── models/
└── dependencies/
```

并且我们已经有了比较清晰的调用链路：

```text
main.py
 ↓
api/v1/api.py
 ↓
api/v1/chat.py
 ↓
services/chat_service.py
 ↓
repositories/
```

但是现在还有一个问题没有解决。

比如后面我们很多接口都需要：

```text
当前用户
API Key
数据库 Session
Redis Client
LLM Provider
权限校验
租户信息
Trace ID
```

如果每个接口都手动写一遍，就会变成这样：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    api_key = request.headers.get("x-api-key")
    user = get_user_by_api_key(api_key)
    db = create_db_session()
    llm = create_llm_provider()
    result = await chat_service.chat(request, user, db, llm)
    return result
```

这样写的问题是：

```text
重复代码多
接口越来越臃肿
不好测试
不好替换依赖
不好做统一鉴权
不好做资源释放
```

==所以这一章我们要学习 FastAPI 非常核心的能力：==

## Dependency Injection 依赖注入
也就是：

```text
Depends
```

这一章的核心目标是：

**把当前用户、API Key、配置、模拟数据库、LLM Provider 这些公共能力，从接口代码里抽出来，通过 Depends 自动注入。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. 什么是依赖注入
2. 为什么 FastAPI 项目需要 Depends
3. Depends 的基本写法
4. 依赖函数如何返回值
5. 依赖函数如何接收 Query / Header 参数
6. 依赖函数如何抛出 HTTPException
7. 如何定义当前用户依赖
8. 如何定义 API Key 校验依赖
9. 如何定义配置 Settings 依赖
10. 如何定义模拟数据库 Session 依赖
11. 如何定义 LLM Provider 依赖
12. 如何在 Router 级别添加依赖
13. 如何在单个接口中添加依赖
14. 如何使用子依赖 Sub-dependencies
15. Depends 缓存机制怎么理解
16. 如何使用 yield 管理资源释放
17. 如何把依赖注入应用到 AI Chat / RAG / Agent 接口中
18. 如何避免依赖函数写乱
```

---

## 三、本章最终项目结构
本章结束后，项目会升级成：

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
│   │       └── rag.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── constants.py
│   │
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── llm.py
│   │   └── settings.py
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
│   └── test_project_structure.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

这一章新增重点目录：

```text
app/dependencies/
```

里面会放：

```text
auth.py       当前用户、API Key 校验
database.py   数据库 Session 依赖
llm.py        LLM Provider 依赖
settings.py   配置依赖
```

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 09 章。

这一章我们讲 FastAPI 非常重要的能力：

## Dependency Injection 依赖注入
也就是：

```python
Depends
```

如果你是 Java Spring Boot 开发者，应该对依赖注入不陌生。

Spring 里面我们经常写：

```java
@Autowired
private UserService userService;
```

或者构造器注入。

如果你是 NestJS 开发者，也会看到：

```typescript
constructor(private readonly userService: UserService) {}
```

FastAPI 里面没有 Spring 那套庞大的 IoC 容器，但是它提供了一个非常轻量、非常好用的依赖注入系统：

```python
Depends
```

比如：

```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    pass
```

这段代码的意思是：

这个接口除了需要 ChatRequest，还依赖当前用户 current_user。  
FastAPI 会自动执行 get_current_user，并把结果传给 current_user。

这就是依赖注入。

我们这一章不会只讲概念。

我们会把依赖注入放到当前 AI 项目里，做几个真实场景：

```text
当前用户依赖
API Key 校验
Settings 配置依赖
模拟数据库 Session
LLM Provider 依赖
Router 级别鉴权
Agent 上下文依赖
```

==这些都是后面企业级 AI 后端一定会用到的能力。==

---

## 五、02｜为什么需要依赖注入
### 【反面代码】
如果没有依赖注入，接口可能会这样写：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    api_key = "从 Header 里手动读取"
    current_user = "根据 API Key 查询用户"
    db = "手动创建数据库连接"
    llm = "手动创建 LLM Provider"

    result = await chat_with_ai(
        request=request,
        current_user=current_user,
        db=db,
        llm=llm,
    )

    return result
```

---

### 【重点内容】
这段代码的问题是：

```text
接口层逻辑太重
很多接口都会重复写鉴权
每个接口都要手动创建资源
不好统一处理异常
不好测试
不好替换实现
```

比如我们后面会有很多接口：

```http
POST /chat
POST /rag/query
POST /agent/run
POST /tool/call
POST /mcp/call
```

这些接口可能都需要：

```text
当前用户
API Key 校验
数据库连接
LLM Provider
```

如果每个接口都写一遍，很快就乱了。

所以我们希望这样写：

```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    pass
```

这样接口看起来非常清楚：

```text
这个接口需要 request
这个接口需要 current_user
这个接口需要 llm_provider
```

至于 current_user 和 llm_provider 怎么创建，由依赖函数负责。

---

## 六、03｜依赖注入解决什么问题
### 【实操】
```text
没有 Depends：

Router 里面手动创建所有东西
    ↓
代码重复
逻辑混乱
不好测试

使用 Depends：

公共能力抽成依赖函数
    ↓
Router 只声明自己需要什么
    ↓
FastAPI 自动执行并注入
```

---

### 【重点内容】
大家先记住一句话：

**依赖注入的核心不是“高级”，而是“解耦”。**

什么叫解耦？

就是接口不关心某个东西怎么来的。

接口只声明：

```text
我需要当前用户
我需要数据库 Session
我需要 LLM Provider
```

然后 FastAPI 负责把这些东西准备好。

这对于 AI 项目非常重要。

比如后面我们要支持多模型：

```text
DeepSeek
Qwen
OpenAI
Claude
本地 Ollama
```

接口不应该关心具体创建哪个 Provider。

接口只写：

```python
llm_provider = Depends(get_llm_provider)
```

至于具体返回哪个模型供应商，由依赖函数根据配置或请求参数决定。

---

## 七、04｜和 Spring Boot / NestJS 对比
### 【实操】
| 场景 | Spring Boot | NestJS | FastAPI |
| --- | --- | --- | --- |
| 依赖注入核心 | Spring IoC | Nest DI Container | `Depends` |
| 注入 Service | `@Autowired`<br/> / 构造器注入 | constructor 注入 | 函数参数 `Depends` |
| 当前用户 | ArgumentResolver / SecurityContext | Guard / Decorator | `Depends(get_current_user)` |
| 权限校验 | Filter / Interceptor / Security | Guard | Router / Path Dependency |
| 数据库 Session | Repository / Transaction | Provider / Repository | `Depends(get_db)` |
| 配置 | `@Value`<br/> / ConfigurationProperties | ConfigService | `Depends(get_app_settings)` |
| 资源释放 | Spring 生命周期管理 | Provider 生命周期 | `yield`<br/> dependency |
| 接口鉴权 | Spring Security | Guard | `Depends(verify_api_key)` |


---

### 【重点内容】
如果你熟悉 Spring Boot，可以这样理解：

```text
FastAPI Depends
≈
Spring 里某种轻量级依赖注入 + 参数解析器
```

如果你熟悉 NestJS，可以这样理解：

```text
FastAPI Depends
≈
NestJS Provider + Guard + Decorator 的一部分能力
```

但是 FastAPI 的写法更函数式。

比如：

```python
async def get_current_user():
    return user
```

然后接口里：

```python
current_user = Depends(get_current_user)
```

你不需要写很多类和注解。

这也是 Python + FastAPI 写 AI 后端非常爽的地方：

```text
足够工程化
但又不臃肿
```

---

## 八、05｜创建 dependencies 目录
### 【实操】
进入项目根目录：

```bash
cd ai-agent-course
```

创建目录：

```bash
mkdir -p app/dependencies
```

Windows PowerShell：

```powershell
mkdir app\dependencies
```

创建文件：

```bash
touch app/dependencies/__init__.py
touch app/dependencies/settings.py
touch app/dependencies/auth.py
touch app/dependencies/database.py
touch app/dependencies/llm.py
```

Windows PowerShell：

```powershell
New-Item app\dependencies\__init__.py
New-Item app\dependencies\settings.py
New-Item app\dependencies\auth.py
New-Item app\dependencies\database.py
New-Item app\dependencies\llm.py
```

---

### 【重点内容】
我们先创建：

```text
app/dependencies
```

这个目录。

后面所有 FastAPI 依赖函数都放在这里。

比如：

```text
settings.py
= 配置依赖

auth.py
= 当前用户、API Key、权限校验

database.py
= 数据库 Session 依赖

llm.py
= LLM Provider 依赖
```

这样依赖逻辑不会散落在 Router 文件里。

---

## 九、06｜第一个 Depends 示例
先在：

```text
app/api/v1/health.py
```

里写一个最简单的依赖。

修改代码：

```python
from fastapi import APIRouter, Depends

from app.core.config import settings

router = APIRouter()


async def get_request_source() -> str:
    return "fastapi-dependency"


@router.get("/health")
async def health(
    source: str = Depends(get_request_source),
):
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "version": settings.app_version,
        "source": source,
    }
```

启动：

```bash
uv run uvicorn app.main:app --reload
```

访问：

```http
GET /api/v1/health
```

返回：

```json
{
  "status": "ok",
  "service": "AI Agent Course API",
  "env": "development",
  "version": "0.1.0",
  "source": "fastapi-dependency"
}
```

---

### 【重点内容】
这是最简单的 Depends。

我们先定义一个依赖函数：

```python
async def get_request_source() -> str:
    return "fastapi-dependency"
```

然后在接口参数里写：

```python
source: str = Depends(get_request_source)
```

意思是：

FastAPI 在执行 health 接口之前，先执行 get_request_source。  
然后把返回值赋给 source。

所以最终接口返回：

```json
"source": "fastapi-dependency"
```

==这就是 Depends 最基本的工作方式。==

---

## 十、07｜Depends 的本质

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```bash
请求进入
 ↓
FastAPI 发现接口依赖 get_request_source
 ↓
执行 get_request_source()
 ↓
拿到返回值
 ↓
传给 source 参数
 ↓
执行接口函数 health()
```

---

### 【重点内容】
Depends 的本质其实很简单。

不是魔法。

就是 FastAPI 帮你做了几件事：

```text
1. 分析接口函数参数
2. 发现某个参数使用 Depends
3. 执行 Depends 里面的依赖函数
4. 把依赖函数返回值传给接口参数
5. 再执行真正的接口逻辑
```

所以我们可以把很多公共逻辑抽成依赖函数。

比如：

```text
读取 Header
校验 API Key
获取当前用户
创建数据库 Session
创建 LLM Provider
```

---

## 十一、08｜把 settings 抽成依赖
打开：

```text
app/dependencies/settings.py
```

写入：

```python
from app.core.config import Settings, get_settings


async def get_app_settings() -> Settings:
    return get_settings()
```

修改：

```text
app/api/v1/health.py
```

代码：

```python
from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.dependencies.settings import get_app_settings

router = APIRouter()


@router.get("/health")
async def health(
    settings: Settings = Depends(get_app_settings),
):
    return {
        "status": "ok",
        "service": settings.app_name,
        "env": settings.app_env,
        "version": settings.app_version,
    }
```

---

### 【重点内容】
现在我们把 settings 也改成 Depends 注入。

之前我们在 Router 里直接导入：

```python
from app.core.config import settings
```

这种写法也可以。

但是如果你希望在测试时替换配置，或者希望依赖更加统一，可以写成：

```python
settings: Settings = Depends(get_app_settings)
```

这样接口就只声明：

```text
我需要 settings
```

至于 settings 怎么创建，由：

```python
get_app_settings()
```

负责。

---

## 十二、09｜定义 User Schema
创建：

```text
app/schemas/user.py
```

写入：

```python
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class CurrentUser(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")
    is_active: bool = Field(default=True, description="是否启用")
```

---

### 【重点内容】
接下来我们要做当前用户依赖。

先定义一个：

```python
CurrentUser
```

它代表当前请求的用户。

字段包括：

```text
user_id
username
role
is_active
```

后面真实项目里，当前用户可能来自：

```text
JWT Token
API Key
Session
OAuth2
企业微信登录
飞书登录
```

这一章我们先用 Header 模拟。

==重点是先掌握 Depends 的使用方式。==

---

## 十三、10｜从 Header 读取当前用户
打开：

```text
app/dependencies/auth.py
```

写入：

```python
from fastapi import Header, HTTPException, status

from app.schemas.user import CurrentUser, UserRole


async def get_current_user(
    x_user_id: str | None = Header(default=None),
    x_username: str | None = Header(default=None),
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

    return CurrentUser(
        user_id=x_user_id,
        username=x_username,
        role=UserRole.USER,
        is_active=True,
    )
```

---

### 【重点内容】
这里我们写了一个当前用户依赖：

```python
get_current_user()
```

它从请求头里读取：

```text
x-user-id
x-username
```

大家注意代码里写的是：

```python
x_user_id
x_username
```

但是 FastAPI 会自动把下划线转换成 Header 里的中划线。

也就是说：

```python
x_user_id
```

对应请求头：

```text
x-user-id
```

如果没有传，就抛出：

```python
HTTPException
```

状态码是：

```text
401
```

表示未认证。

---

## 十四、11｜在 Chat 接口中注入当前用户
修改：

```text
app/api/v1/chat.py
```

导入：

```python
from fastapi import APIRouter, Depends, Path, Query

from app.dependencies.auth import get_current_user
from app.schemas.user import CurrentUser
```

修改 Chat 接口：

```python
@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(request)

    result.trace_id = f"{result.trace_id}_user_{current_user.user_id}"

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

### 【重点内容】
现在我们的 Chat 接口多了一个参数：

```python
current_user: CurrentUser = Depends(get_current_user)
```

这表示：

==访问这个接口之前，必须先执行 get_current_user。==  
get_current_user 会从 Header 里读取用户信息。  
如果没有用户信息，就直接返回 401。  
如果有，就把 CurrentUser 注入进来。

接口里我们可以直接使用：

```python
current_user.user_id
current_user.username
```

这就是依赖注入的典型使用方式。

---

## 十五、12｜测试当前用户依赖
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

访问 Swagger：

```http
http://127.0.0.1:8000/docs
```

测试：

```http
POST /api/v1/chat
```

请求体：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ],
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

请求头需要加：

```text
x-user-id: u_10001
x-username: dawei
```

curl 测试：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
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

如果不传 Header，会返回：

```json
{
  "detail": "缺少请求头 x-user-id"
}
```

---

### 【重点内容】
现在这个接口已经有了最基础的认证效果。

没有传用户 Header，就不能访问。

传了 Header，FastAPI 会自动注入当前用户。

虽然现在我们只是模拟。

但是后面换成 JWT 或 API Key，接口层的写法变化不大。

==这就是 Depends 的价值：==

**认证逻辑可以替换，接口业务代码尽量不变。**

---

## 十六、13｜API Key 校验依赖
在 AI 项目里，经常会有 API Key。

比如企业内部调用你的 AI 平台接口，可能需要传：

```text
x-api-key
```

我们先在 `.env` 增加配置：

```text
APP_API_KEY=dev-api-key-123
```

`.env.example` 也增加：

```text
APP_API_KEY=dev-api-key-123
```

---

### 修改 `app/core/config.py`
增加字段：

```python
app_api_key: str = Field(default="dev-api-key-123")
```

完整相关片段：

```python
class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Course API")
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_v1_prefix: str = Field(default="/api/v1")
    debug: bool = Field(default=True)

    app_api_key: str = Field(default="dev-api-key-123")

    default_model: str = Field(default="deepseek-chat")
    supported_models: str = Field(default="deepseek-chat,qwen-plus,gpt-4o-mini")
```

---

## 十七、14｜编写 verify_api_key
修改：

```text
app/dependencies/auth.py
```

增加：

```python
from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.schemas.user import CurrentUser, UserRole


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少请求头 x-api-key",
        )

    if x_api_key != settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key 不正确",
        )

    return x_api_key
```

---

### 【重点内容】
这里我们新增了一个 API Key 校验依赖：

```python
verify_api_key()
```

它从 Header 里读取：

```text
x-api-key
```

如果没传，返回 401。

如果传了但不正确，返回 403。

这里简单区分一下：

```text
401
= 没有认证信息

403
= 有认证信息，但是没有权限或不正确
```

后面企业项目里，API Key 通常不会写死在 `.env`。

而是存数据库，支持：

```text
用户级 API Key
组织级 API Key
过期时间
额度限制
权限范围
```

这一章先做基础版。

---

## 十八、15｜Router 级别依赖
有些接口全部都需要 API Key。

比如：

```text
Chat
RAG
Agent
Tool
```

我们不想每个接口都写：

```python
api_key: str = Depends(verify_api_key)
```

可以在 Router 级别加依赖。

修改：

```text
app/api/v1/api.py
```

导入：

```python
from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_api_key
```

然后注册时：

```python
api_router.include_router(
    chat_router,
    tags=[ApiTag.CHAT],
    dependencies=[Depends(verify_api_key)],
)

api_router.include_router(
    rag_router,
    tags=[ApiTag.RAG],
    dependencies=[Depends(verify_api_key)],
)
```

完整示例：

```python
from fastapi import APIRouter, Depends

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.models import router as models_router
from app.api.v1.rag import router as rag_router
from app.core.constants import ApiTag
from app.dependencies.auth import verify_api_key


api_router = APIRouter()

api_router.include_router(health_router, tags=[ApiTag.HEALTH])
api_router.include_router(models_router, tags=[ApiTag.MODELS])

api_router.include_router(
    chat_router,
    tags=[ApiTag.CHAT],
    dependencies=[Depends(verify_api_key)],
)

api_router.include_router(
    conversations_router,
    tags=[ApiTag.CONVERSATIONS],
    dependencies=[Depends(verify_api_key)],
)

api_router.include_router(
    rag_router,
    tags=[ApiTag.RAG],
    dependencies=[Depends(verify_api_key)],
)
```

---

### 【重点内容】
这里我们使用了 Router 级别依赖。

什么意思？

==就是 Chat Router 下面所有接口都必须先通过：==

```python
verify_api_key
```

比如：

```http
POST /api/v1/chat
POST /api/v1/chat/title
POST /api/v1/conversations/{conversation_id}/chat
```

都会先校验 API Key。

这样就不用在每个接口函数里都写一遍。

注意：

```python
dependencies=[Depends(verify_api_key)]
```

这种写法只执行依赖，不把返回值注入到函数参数里。

如果你需要使用返回值，就要写在函数参数里：

```python
api_key: str = Depends(verify_api_key)
```

---

## 十九、16｜测试 Router 级别 API Key
测试 Chat 接口时，现在必须加：

```text
x-api-key: dev-api-key-123
```

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
        "content": "什么是 RAG？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

如果不传 API Key：

```json
{
  "detail": "缺少请求头 x-api-key"
}
```

如果传错：

```json
{
  "detail": "API Key 不正确"
}
```

---

### 【重点内容】
现在 Chat、Conversations、RAG 这些接口都受 API Key 保护。

但是 Health 和 Models 我们暂时没有加。

为什么？

因为：

```text
health
= 通常用于健康检查，可以公开

models
= 有些系统可以公开，有些系统需要保护
```

实际企业项目里是否保护，要看业务需求。

这一章我们先演示不同 Router 可以有不同依赖。

---

## 二十、17｜依赖返回值 vs 只校验不返回
### 【重点内容】
这里大家要区分两种 Depends 用法。

第一种，依赖结果要在接口里使用：

```python
@router.post("/chat")
async def chat(
    current_user: CurrentUser = Depends(get_current_user),
):
    print(current_user.user_id)
```

这种写在函数参数里。

第二种，只想校验，不需要使用返回值：

```python
api_router.include_router(
    chat_router,
    dependencies=[Depends(verify_api_key)],
)
```

这种写在 Router 级别。

它会执行依赖。

依赖失败就直接返回错误。

依赖成功就继续执行接口。

但是接口函数拿不到它的返回值。

---

## 二十一、18｜子依赖 Sub-dependencies
有时候一个依赖还依赖另一个依赖。

比如当前用户依赖可以先校验 API Key。

修改：

```text
app/dependencies/auth.py
```

让 `get_current_user` 依赖 `verify_api_key`：

```python
from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings
from app.schemas.user import CurrentUser, UserRole


async def verify_api_key(
    x_api_key: str | None = Header(default=None),
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少请求头 x-api-key",
        )

    if x_api_key != settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key 不正确",
        )

    return x_api_key


async def get_current_user(
    api_key: str = Depends(verify_api_key),
    x_user_id: str | None = Header(default=None),
    x_username: str | None = Header(default=None),
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

    return CurrentUser(
        user_id=x_user_id,
        username=x_username,
        role=UserRole.USER,
        is_active=True,
    )
```

---

### 【重点内容】
现在：

```python
get_current_user
```

里面也写了：

```python
api_key: str = Depends(verify_api_key)
```

这表示：

==要获取当前用户之前，必须先校验 API Key。==

这就是子依赖。

依赖之间可以形成链路：

```text
get_current_user
    ↓
verify_api_key
    ↓
读取 Header
```

后面真实项目里经常会这样：

```text
get_current_user
    ↓
verify_token
    ↓
decode_jwt
    ↓
query_user_from_db
```

或者：

```text
get_current_tenant
    ↓
get_current_user
    ↓
verify_api_key
```

---

## 二十二、19｜Depends 的缓存机制
### 【重点内容】
如果同一个请求里，多个地方都依赖同一个函数，FastAPI 默认会缓存依赖结果。

比如：

```text
verify_api_key 被 Router 级别依赖调用
get_current_user 里面又依赖 verify_api_key
```

默认情况下，同一个请求里不会无意义重复执行多次。

这对数据库连接、用户查询、权限解析很重要。

大多数时候，我们不用管它。

但是如果某个依赖你希望每次都重新执行，可以设置：

```python
Depends(get_xxx, use_cache=False)
```

课程里一般不需要这样做。

先记住默认缓存即可。

---

## 二十三、20｜模拟数据库 Session 依赖
后面我们会接 PostgreSQL。

这一章先用一个假的 DB Session 模拟。

打开：

```text
app/dependencies/database.py
```

写入：

```python
from collections.abc import AsyncGenerator


class MockDBSession:
    async def execute(self, sql: str) -> str:
        return f"执行 SQL：{sql}"

    async def close(self):
        print("关闭 MockDBSession")


async def get_db_session() -> AsyncGenerator[MockDBSession, None]:
    db = MockDBSession()

    try:
        yield db
    finally:
        await db.close()
```

---

### 【重点内容】
这里我们写了一个数据库依赖：

```python
get_db_session()
```

它使用了：

```python
yield
```

这种写法非常重要。

它表示：

```text
请求开始时创建资源
 ↓
yield 把资源交给接口使用
 ↓
请求结束后执行 finally 释放资源
```

这非常适合数据库连接。

真实项目里会类似：

```python
async with async_session() as session:
    yield session
```

这一章我们先用 MockDBSession 模拟。

---

## 二十四、21｜在 Conversation 接口中使用 DB Session
修改：

```text
app/api/v1/conversations.py
```

导入：

```python
from fastapi import APIRouter, Depends, Path

from app.dependencies.database import MockDBSession, get_db_session
```

修改创建会话接口：

```python
@router.post("/conversations", response_model=ApiResponse[ConversationResponse])
async def create_new_conversation(
    request: ConversationCreateRequest,
    db: MockDBSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    sql_result = await db.execute("INSERT INTO conversations ...")
    print(sql_result)

    result = await create_conversation(request)

    return ApiResponse[ConversationResponse](
        data=result
    )
```

---

### 【重点内容】
现在创建会话接口里多了：

```python
db: MockDBSession = Depends(get_db_session)
```

FastAPI 会在请求进来时执行：

```python
get_db_session()
```

拿到 db，然后注入进来。

接口执行完后，会进入 finally：

```python
await db.close()
```

==这就是资源型依赖最常见的使用方式。==

后面我们接 SQLAlchemy 时，基本就是这个模式。

---

## 二十五、22｜为什么 DB Session 要用 yield
### 【重点内容】
数据库连接这种资源，不能只创建不关闭。

错误方式：

```python
async def get_db():
    db = create_session()
    return db
```

如果你只 return，不做关闭，连接可能一直占用。

推荐方式：

```python
async def get_db():
    db = create_session()
    try:
        yield db
    finally:
        await db.close()
```

这表示：

```text
请求前创建
请求中使用
请求后释放
```

后面 Redis Client、HTTP Client、MCP Client，也可以用类似思想管理。

---

## 二十六、23｜LLM Provider 依赖
现在我们模拟一个 LLM Provider。

打开：

```text
app/dependencies/llm.py
```

写入：

```python
from app.core.config import settings


class MockLLMProvider:
    def __init__(self, model: str):
        self.model = model

    async def chat(self, message: str) -> str:
        return f"[{self.model}] 模拟回答：{message}"


async def get_llm_provider() -> MockLLMProvider:
    return MockLLMProvider(model=settings.default_model)
```

---

### 【重点内容】
这里我们定义了一个：

```python
MockLLMProvider
```

它现在只是模拟大模型。

里面有一个：

```python
chat()
```

方法。

后面我们会把它替换成真正的：

```text
OpenAIProvider
DeepSeekProvider
QwenProvider
OllamaProvider
```

但是接口层不用关心具体实现。

接口只需要：

```python
llm_provider: MockLLMProvider = Depends(get_llm_provider)
```

==这就是依赖注入对 AI 项目的价值。==

---

## 二十七、24｜新增一个依赖注入演示接口
修改：

```text
app/api/v1/chat.py
```

导入：

```python
from app.dependencies.llm import MockLLMProvider, get_llm_provider
```

新增接口：

```python
@router.post("/chat/di-demo", response_model=ApiResponse[ChatResponse])
async def chat_di_demo(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: MockLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[ChatResponse]:
    latest_message = request.messages[-1].content

    answer = await llm_provider.chat(
        message=f"用户 {current_user.username} 问：{latest_message}"
    )

    result = ChatResponse(
        answer=answer,
        model=llm_provider.model,
        session_id=request.session_id,
    )

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

### 【重点内容】
这个接口演示了多个依赖同时注入：

```python
current_user: CurrentUser = Depends(get_current_user)
llm_provider: MockLLMProvider = Depends(get_llm_provider)
```

也就是说，这个接口需要：

```text
当前用户
LLM Provider
```

FastAPI 会先准备好它们，再执行接口逻辑。

接口里我们直接使用：

```python
current_user.username
llm_provider.chat()
```

==这就是后面真实 AI Chat 接口的雏形。==

---

## 二十八、25｜测试 LLM Provider 依赖
curl 测试：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat/di-demo" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是依赖注入？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

返回类似：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "[deepseek-chat] 模拟回答：用户 dawei 问：什么是依赖注入？",
    "model": "deepseek-chat",
    "session_id": null,
    "message_id": null,
    "usage": {
      "prompt_tokens": 0,
      "completion_tokens": 0,
      "total_tokens": 0
    },
    "sources": [],
    "trace_id": null
  }
}
```

---

### 【重点内容】
现在我们已经看到依赖注入的价值了。

接口本身没有写：

```text
如何解析用户
如何校验 API Key
如何创建 LLM Provider
```

这些都由 Depends 处理。

接口只关注自己的业务逻辑：

```text
拿到当前用户
拿到 LLM Provider
生成回答
返回响应
```

==这就是干净的接口层代码。==

---

## 二十九、26｜权限依赖：只允许管理员访问
有些接口只有管理员可以访问，比如：

```text
查看系统配置
查看所有用户
查看成本统计
管理模型
```

在：

```text
app/dependencies/auth.py
```

增加：

```python
async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return current_user
```

---

### 【重点内容】
这里我们写了一个管理员权限依赖：

```python
require_admin()
```

它本身又依赖：

```python
get_current_user()
```

也就是说：

```text
先获取当前用户
再判断用户是不是 admin
```

如果不是 admin，就返回 403。

这就是依赖组合。

后面我们可以继续扩展：

```text
require_login
require_admin
require_workspace_member
require_agent_owner
require_api_key_scope
```

---

## 三十、27｜让 Header 模拟管理员
修改 `get_current_user`：

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

    return CurrentUser(
        user_id=x_user_id,
        username=x_username,
        role=role,
        is_active=True,
    )
```

---

### 【重点内容】
为了演示管理员权限，我们增加一个 Header：

```text
x-user-role
```

如果传：

```text
x-user-role: admin
```

就认为当前用户是管理员。

当然真实项目里不能这么做。

真实项目里角色应该来自：

```text
数据库
JWT Claims
权限系统
组织成员关系
```

这一章只是为了演示依赖注入和权限控制。

---

## 三十一、28｜保护 Models 接口：管理员才能访问
修改：

```text
app/api/v1/models.py
```

导入：

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import require_admin
from app.schemas.user import CurrentUser
```

修改接口：

```python
@router.get("/models", response_model=ApiResponse[ModelListResponse])
async def list_models(
    admin_user: CurrentUser = Depends(require_admin),
) -> ApiResponse[ModelListResponse]:
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
```

---

### 【重点内容】
现在：

```http
GET /api/v1/models
```

需要管理员权限。

接口里写：

```python
admin_user: CurrentUser = Depends(require_admin)
```

这表示：

```text
必须先通过 require_admin
```

如果用户不是 admin，就不能访问模型列表。

后面管理后台接口、系统配置接口、成本统计接口，都可以这样做。

---

## 三十二、29｜测试管理员权限
普通用户访问：

```bash
curl "http://127.0.0.1:8000/api/v1/models" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

返回：

```json
{
  "detail": "需要管理员权限"
}
```

管理员访问：

```bash
curl "http://127.0.0.1:8000/api/v1/models" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_admin" \
  -H "x-username: admin" \
  -H "x-user-role: admin"
```

返回模型列表。

---

### 【重点内容】
==这就是最基础的权限依赖。==

它的好处是，权限逻辑不写在接口里。

接口只声明：

```python
Depends(require_admin)
```

至于怎么判断管理员，由依赖函数负责。

后面我们可以继续升级成：

```text
RBAC
组织权限
Workspace 权限
Agent 权限
Knowledge Base 权限
```

但基本思想不变。

---

## 三十三、30｜依赖类：Class as Dependency
有时候依赖不一定是函数，也可以是类。

创建：

```text
app/dependencies/pagination.py
```

写入：

```python
from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="页码"),
        page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
```

---

### 【重点内容】
==FastAPI 的依赖不一定非得是函数。==

只要是 callable，就可以作为依赖。

类也可以。

这里我们定义了：

```python
PaginationParams
```

它封装分页参数：

```text
page
page_size
offset
```

后面列表接口会经常用到分页。

---

## 三十四、31｜在 Conversations 中使用分页依赖
修改：

```text
app/api/v1/conversations.py
```

导入：

```python
from app.dependencies.pagination import PaginationParams
```

新增接口：

```python
@router.get("/conversations", response_model=ApiResponse[dict])
async def list_conversations(
    pagination: PaginationParams = Depends(PaginationParams),
) -> ApiResponse[dict]:
    return ApiResponse[dict](
        data={
            "page": pagination.page,
            "page_size": pagination.page_size,
            "offset": pagination.offset,
            "items": [],
        }
    )
```

测试：

```http
GET /api/v1/conversations?page=2&page_size=20
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "page": 2,
    "page_size": 20,
    "offset": 20,
    "items": []
  }
}
```

---

### 【重点内容】
这里我们把分页参数封装成依赖类。

接口里只需要写：

```python
pagination: PaginationParams = Depends(PaginationParams)
```

就可以拿到：

```python
pagination.page
pagination.page_size
pagination.offset
```

以后所有列表接口都可以复用这个分页依赖。

比如：

```http
GET /conversations
GET /knowledge-bases
GET /agents
GET /tools
GET /logs
```

这就是依赖复用的价值。

---

## 三十五、32｜AI Agent 上下文依赖
后面 Agent 接口会经常需要一个上下文对象，比如：

```text
当前用户
Trace ID
模型名称
是否开启 Debug
```

先创建：

```text
app/dependencies/agent_context.py
```

写入：

```python
import uuid

from fastapi import Depends, Query

from app.dependencies.auth import get_current_user
from app.schemas.user import CurrentUser


class AgentContext:
    def __init__(
        self,
        current_user: CurrentUser,
        trace_id: str,
        debug: bool,
    ):
        self.current_user = current_user
        self.trace_id = trace_id
        self.debug = debug


async def get_agent_context(
    current_user: CurrentUser = Depends(get_current_user),
    debug: bool = Query(default=False, description="是否开启调试模式"),
) -> AgentContext:
    return AgentContext(
        current_user=current_user,
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        debug=debug,
    )
```

---

### 【重点内容】
这里我们提前设计了一个：

```python
AgentContext
```

它表示 Agent 执行上下文。

里面包括：

```text
当前用户
trace_id
debug
```

后面真正做 Agent 时，Context 会越来越重要。

它可能还包括：

```text
workspace_id
tenant_id
model
tools
memory
permissions
```

这一章先让大家理解：

**依赖注入不仅可以注入简单值，也可以注入上下文对象。**

---

## 三十六、33｜新增 Agent Router 使用上下文依赖
如果上一章课后任务已经创建了：

```text
app/api/v1/agents.py
```

可以直接修改。

如果没有，先创建：

```text
app/api/v1/agents.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.agent_context import AgentContext, get_agent_context
from app.schemas.response import ApiResponse

router = APIRouter()


class AgentRunRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    agent_id: str = Field(default="agent_chat", description="Agent ID")


class AgentRunResponse(BaseModel):
    answer: str = Field(..., description="Agent 回答")
    trace_id: str = Field(..., description="链路追踪 ID")
    debug: bool = Field(default=False, description="是否调试模式")


@router.post("/agents/run", response_model=ApiResponse[AgentRunResponse])
async def run_agent(
    request: AgentRunRequest,
    context: AgentContext = Depends(get_agent_context),
) -> ApiResponse[AgentRunResponse]:
    answer = (
        f"用户 {context.current_user.username} 调用了 {request.agent_id}，"
        f"问题是：{request.question}"
    )

    return ApiResponse[AgentRunResponse](
        data=AgentRunResponse(
            answer=answer,
            trace_id=context.trace_id,
            debug=context.debug,
        )
    )
```

---

### 注册 Agent Router
修改：

```text
app/core/constants.py
```

确认：

```python
AGENTS = "Agents"
```

修改：

```text
app/api/v1/api.py
```

增加：

```python
from app.api.v1.agents import router as agents_router
```

注册：

```python
api_router.include_router(
    agents_router,
    tags=[ApiTag.AGENTS],
    dependencies=[Depends(verify_api_key)],
)
```

---

### 【重点内容】
现在我们新增了一个 Agent 运行接口：

```http
POST /api/v1/agents/run
```

它依赖：

```python
AgentContext = Depends(get_agent_context)
```

而 `get_agent_context` 又依赖：

```python
get_current_user
```

这就形成了依赖链：

```text
run_agent
  ↓
get_agent_context
  ↓
get_current_user
  ↓
verify_api_key
```

==这就是复杂 AI 项目里非常常见的依赖结构。==

---

## 三十七、34｜测试 Agent Context
curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/agents/run?debug=true" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "帮我查询订单状态",
    "agent_id": "agent_order"
  }'
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "用户 dawei 调用了 agent_order，问题是：帮我查询订单状态",
    "trace_id": "trace_xxxxxxxx",
    "debug": true
  }
}
```

---

### 【重点内容】
这个接口展示了 Depends 的组合能力。

请求里只传了：

```text
question
agent_id
debug
headers
```

但是接口里拿到了完整的：

```text
AgentContext
```

这就是依赖注入的价值。

后面我们做真实 Agent 时，接口层就可以保持很干净。

---

## 三十八、35｜当前完整依赖关系图
### 【实操】
```http
POST /api/v1/agents/run
    ↓
run_agent()
    ↓
Depends(get_agent_context)
    ↓
Depends(get_current_user)
    ↓
Depends(verify_api_key)
    ↓
读取 Header x-api-key / x-user-id / x-username
```

再看 Chat：

```http
POST /api/v1/chat/di-demo
    ↓
chat_di_demo()
    ↓
Depends(get_current_user)
    ↓
Depends(verify_api_key)
    ↓
Depends(get_llm_provider)
    ↓
MockLLMProvider
```

数据库：

```http
POST /api/v1/conversations
    ↓
create_new_conversation()
    ↓
Depends(get_db_session)
    ↓
yield MockDBSession
    ↓
finally close()
```

---

## 三十九、36｜依赖函数应该放哪里
### 【重点内容】
依赖函数不要乱放。

推荐放在：

```text
app/dependencies/
```

按照职责拆分：

```text
auth.py
= 登录用户、API Key、权限校验

database.py
= 数据库连接

llm.py
= LLM Provider

settings.py
= 配置

pagination.py
= 分页参数

agent_context.py
= Agent 上下文
```

不要所有 Depends 都写到 router 文件里。

Router 应该保持简单。

---

## 四十、37｜常见错误一：Depends 忘记导入

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
current_user: CurrentUser = Depends(get_current_user)
```

但是没有导入：

```python
from fastapi import Depends
```

会报：

```text
NameError: name 'Depends' is not defined
```

解决：

```python
from fastapi import Depends
```

---

## 四十一、38｜常见错误二：把 Depends 写成函数调用
错误：

```python
current_user: CurrentUser = Depends(get_current_user())
```

正确：

```python
current_user: CurrentUser = Depends(get_current_user)
```

---

### 【重点内容】
这里非常容易写错。

Depends 里面传的是函数对象：

```python
get_current_user
```

不是调用结果：

```python
get_current_user()
```

也就是说不要加括号。

FastAPI 会在请求进来时帮你调用它。

---

## 四十二、39｜常见错误三：依赖函数里返回 coroutine

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
async def get_data():
    return some_async_func()
```

如果 `some_async_func()` 是异步函数，这里少了 await。

正确：

```python
async def get_data():
    return await some_async_func()
```

---

### 【重点内容】
依赖函数本身也可以是 async。

如果里面调用其他 async 函数，也要 await。

否则你返回的可能是 coroutine object。

这和第 05 章异步编程里的坑是一样的。

---

## 四十三、40｜常见错误四：Router 级依赖拿不到返回值
错误理解：

```python
api_router.include_router(
    chat_router,
    dependencies=[Depends(verify_api_key)],
)
```

以为接口里可以直接使用 api_key。

其实不行。

Router 级 dependencies 只执行依赖，不注入返回值。

==如果你要拿到返回值，必须写：==

```python
async def chat(
    api_key: str = Depends(verify_api_key),
):
    pass
```

---

## 四十四、41｜常见错误五：把权限逻辑写死在接口里

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不推荐：

```python
@router.get("/models")
async def list_models(current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403)
```

推荐：

```python
@router.get("/models")
async def list_models(
    admin_user: CurrentUser = Depends(require_admin),
):
    pass
```

---

### 【重点内容】
权限逻辑尽量抽成依赖。

这样多个接口可以复用。

比如：

```text
require_admin
require_login
require_workspace_owner
require_agent_permission
```

这些都应该是独立依赖，而不是到处复制 if 判断。

---

## 四十五、42｜常见错误六：依赖之间循环引用

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
auth.py 依赖 agent_context.py
agent_context.py 又依赖 auth.py
```

这样容易产生循环导入。

正确依赖方向：

```text
agent_context.py
    ↓
auth.py

auth.py
不要反过来导入 agent_context.py
```

原则：

```text
更具体的上下文依赖，可以依赖更基础的 auth 依赖
基础 auth 依赖不要依赖业务上下文
```

---

## 四十六、43｜本章知识点和 AI 开发场景对应表
| Depends 知识点 | AI 开发场景 |
| --- | --- |
| `Depends(get_current_user)` | 当前用户认证 |
| `Depends(verify_api_key)` | API Key 鉴权 |
| Router 级依赖 | 保护 Chat / RAG / Agent 模块 |
| 子依赖 | 当前用户依赖 API Key / Token |
| `yield`<br/> dependency | 数据库 Session、Redis Client、HTTP Client |
| `Depends(get_llm_provider)` | 注入 DeepSeek / Qwen / OpenAI Provider |
| `Depends(get_agent_context)` | 注入 Agent 执行上下文 |
| Class 依赖 | 分页、过滤、搜索参数 |
| `require_admin` | 管理后台、模型管理、成本统计 |
| Header 依赖 | 读取 API Key、用户 ID、租户 ID |
| Query 依赖 | debug、page、page_size、top_k |
| 缓存机制 | 同一请求复用用户、DB Session、配置 |
| 依赖拆分目录 | 避免 Router 变臃肿 |


---

## 四十七、44｜本章完整复习
这一章我们完成了：

```text
1. 理解什么是依赖注入
2. 理解 Depends 解决什么问题
3. 创建 dependencies 目录
4. 编写 settings 依赖
5. 编写当前用户依赖
6. 从 Header 读取 x-user-id / x-username
7. 编写 API Key 校验依赖
8. 在 Router 级别添加依赖
9. 理解依赖返回值和只执行依赖的区别
10. 理解子依赖 Sub-dependencies
11. 理解 Depends 缓存机制
12. 编写 MockDBSession
13. 使用 yield 释放资源
14. 编写 MockLLMProvider 依赖
15. 在 Chat 接口注入 current_user 和 llm_provider
16. 编写 require_admin 权限依赖
17. 保护 Models 接口
18. 使用 Class as Dependency 封装分页参数
19. 编写 AgentContext 依赖
20. 新增 Agent Router 演示上下文注入
```

现在我们的项目调用链路进一步升级成：

```text
Router
 ↓
Dependency
 ↓
Service
 ↓
Repository
```

这已经非常接近真实企业级 FastAPI 后端结构。

---

## 四十八、45｜课后任务一：新增 Workspace 依赖
要求：

```text
1. 创建 app/dependencies/workspace.py
2. 从 Header 读取 x-workspace-id
3. 如果没有传，返回 400
4. 返回 workspace_id 字符串
```

参考答案：

```python
from fastapi import Header, HTTPException, status


async def get_workspace_id(
    x_workspace_id: str | None = Header(default=None),
) -> str:
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少请求头 x-workspace-id",
        )

    return x_workspace_id
```

---

## 四十九、46｜课后任务二：在 RAG 接口注入 workspace_id
要求：

```text
1. 修改 app/api/v1/rag.py
2. 注入 workspace_id
3. 在返回结果 trace_id 或 metadata 中体现 workspace_id
```

参考写法：

```python
from fastapi import APIRouter, Depends

from app.dependencies.workspace import get_workspace_id


@router.post("/rag/query", response_model=ApiResponse[RAGQueryResponse])
async def rag_query(
    request: RAGQueryRequest,
    workspace_id: str = Depends(get_workspace_id),
) -> ApiResponse[RAGQueryResponse]:
    result = await query_rag(request)
    result.trace_id = f"{result.trace_id}_workspace_{workspace_id}"

    return ApiResponse[RAGQueryResponse](
        data=result
    )
```

---

## 五十、47｜课后任务三：新增 require_active_user
要求：

```text
1. 创建 require_active_user
2. 依赖 get_current_user
3. 如果 is_active=False，返回 403
4. 否则返回 CurrentUser
```

参考答案：

```python
async def require_active_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return current_user
```

---

## 五十一、48｜课后任务四：新增 CostContext 依赖
要求：

```text
1. 创建 app/dependencies/cost.py
2. 定义 CostContext
3. 包括 user_id、model、max_tokens
4. 依赖 get_current_user
5. 从 Query 读取 max_tokens，默认 1024，最大 8192
```

参考答案：

```python
from fastapi import Depends, Query

from app.schemas.user import CurrentUser
from app.dependencies.auth import get_current_user


class CostContext:
    def __init__(self, user_id: str, max_tokens: int):
        self.user_id = user_id
        self.max_tokens = max_tokens


async def get_cost_context(
    current_user: CurrentUser = Depends(get_current_user),
    max_tokens: int = Query(default=1024, ge=1, le=8192),
) -> CostContext:
    return CostContext(
        user_id=current_user.user_id,
        max_tokens=max_tokens,
    )
```

---

## 五十二、49｜课后任务五：画出 Depends 调用链
画出：

```http
POST /api/v1/agents/run
```

的完整依赖链：

```text
run_agent
 ↓
get_agent_context
 ↓
get_current_user
 ↓
verify_api_key
 ↓
读取 Header
```

再画出：

```http
POST /api/v1/conversations
```

的依赖链：

```text
create_new_conversation
 ↓
get_db_session
 ↓
yield MockDBSession
 ↓
finally close()
```

---

## 五十三、50｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 09 章我们就讲完了。

这一章我们系统学习了 FastAPI 的依赖注入：

```text
Depends
```

==大家一定要记住，Depends 不是为了让代码看起来高级。==

它解决的是企业项目里非常实际的问题：

```text
公共逻辑复用
接口代码简洁
鉴权统一
资源统一管理
依赖可以替换
方便测试
```

在 AI 项目里，Depends 非常重要。

因为后面我们会有很多公共上下文：

```text
当前用户
API Key
Workspace
数据库 Session
Redis Client
LLM Provider
Agent Context
权限信息
Trace ID
Cost Context
```

这些都不适合在每个接口里手动创建。

正确方式是：

```python
current_user: CurrentUser = Depends(get_current_user)
db = Depends(get_db_session)
llm_provider = Depends(get_llm_provider)
context = Depends(get_agent_context)
```

这样 Router 会非常干净。

现在我们的项目调用链路已经升级成：

```text
FastAPI Router
 ↓
Dependency
 ↓
Service
 ↓
Repository
```

==这就是企业级 FastAPI 后端的基本结构。==

下一章我们继续往企业级方向走：

## 第 10 章｜Middleware、异常处理与日志
为什么要讲它？

因为当前项目还有几个问题：

```text
错误响应格式不统一
接口日志不统一
请求耗时没有记录
trace_id 没有贯穿全链路
异常没有集中处理
```

下一章我们会统一解决这些问题。

---

> [!success] 一句话带走
> ==把横切逻辑交给 Depends，接口函数就只剩业务。==

> [!quote] 关于本文档
> 由原始讲义 `第 09 章｜FastAPI Dependency Injection 依赖注入.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
