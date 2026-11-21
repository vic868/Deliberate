---
title: "第 07 章｜Pydantic 请求参数与响应模型"
chapter: "07"
source: "第 07 章｜Pydantic 请求参数与响应模型.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - pydantic
  - schema
---

# 第 07 章｜Pydantic 请求参数与响应模型

> [!abstract] 本章重点
>
> - ==ChatRequest / ChatResponse 拆成多个小模型== — ChatMessage、TokenUsage、SourceDocument 各管一块，别堆成一个大字典。
> - ==用泛型做统一响应结构== — code / message / data 外壳固定，data 里装什么都行。
> - ==Path + Query + Body 可以同时用== — 一个接口里三种来源的参数各写各的。
> - ==Schema 是企业项目和 Demo 的分水岭== — 数据结构定清楚，后面 RAG、会话管理才好接。
>
> [!note] 大白话
>
> - **TokenUsage**：记一次调用花了多少输入/输出 token，用来算成本和排查。
> - **SourceDocument**：RAG 回答里引用的原文出处。
>
> [!info] 导航与来源
> - 原始讲义：[[第 07 章｜Pydantic 请求参数与响应模型|打开原始讲义]]
> - [[第 06 章｜FastAPI 快速入门|上一章｜第 06 章]]
> - [[第 08 章｜FastAPI Router 与项目工程化|下一章｜第 08 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#Pydantic 请求参数与响应模型]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#五、02｜先回顾上一章的 ChatRequest]]
- [[#六、03｜创建新的 Chat Schema]]
- [[#七、04｜定义 ChatMessage]]
- [[#八、05｜定义 TokenUsage]]
- [[#九、06｜定义 SourceDocument 引用来源]]
- [[#十、07｜定义 ChatRequest]]
- [[#十一、08｜定义 ChatResponse]]
- [[#十二、09｜完整代码：app/schemas/chat.py]]
- [[#十三、10｜升级 ChatService]]

---
适合人群：已经完成 FastAPI 快速入门，准备系统设计 AI Chat / RAG / Agent 接口结构的学员。

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们已经完成了 FastAPI 快速入门。

我们跑通了：

```http
GET /
GET /api/v1/health
POST /api/v1/chat
```

也完成了基础项目分层：

```text
main.py
 ↓
api/v1/chat.py
 ↓
schemas/chat.py
 ↓
services/chat_service.py
```

但是上一章的 `ChatRequest` 和 `ChatResponse` 还比较简单：

```python
class ChatRequest(BaseModel):
    message: str
    model: str
    temperature: float
    stream: bool
```

真实 AI 项目不会这么简单。

比如一个企业级 AI Chat 接口，可能需要支持：

```text
多轮 messages
模型名称
temperature
stream
session_id
user_id
metadata
工具开关
知识库开关
引用来源
token 用量
trace_id
```

如果不把请求模型和响应模型设计好，后面项目会越来越乱。

所以这一章我们专门讲：

## Pydantic 请求参数与响应模型
这一章的核心目标是：

**把普通 Demo 接口，升级成企业级 AI 接口的数据结构。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. FastAPI 中 Path / Query / Body 分别是什么
2. Pydantic 请求体模型如何设计
3. 响应模型 response_model 如何设计
4. 多轮对话 messages 如何建模
5. Enum 如何约束消息角色
6. Field 如何定义描述、默认值、校验规则
7. 嵌套模型如何设计
8. 列表模型如何设计
9. 统一响应结构如何设计
10. 错误响应模型如何设计
11. TokenUsage 响应模型如何设计
12. SourceDocument 引用来源模型如何设计
13. metadata 扩展字段如何设计
14. 前端 camelCase 和后端 snake_case 如何适配
15. 如何让 Swagger 文档更清晰
16. 如何避免返回敏感字段
17. 如何为 AI Chat / RAG / Agent 提前设计通用 Schema
```

---

## 三、本章最终项目结构
本章结束之后，项目结构会变成：

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
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       └── rag.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── response.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   └── rag.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── chat_service.py
│       ├── conversation_service.py
│       └── rag_service.py
│
├── tests/
│   ├── test_chat_api.py
│   └── test_schema.py
│
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

这一章我们重点升级：

```text
schemas/chat.py
schemas/response.py
api/v1/chat.py
services/chat_service.py
```

同时会新增：

```text
conversation.py
rag.py
```

为后面 RAG 和多轮对话提前铺路。

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 07 章。

上一章我们已经完成了 FastAPI 快速入门，跑通了第一个 Chat 接口。

但是上一章的接口还是一个 Demo 级别的接口。

比如请求体只有：

```json
{
  "message": "什么是 AI Agent？",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

这种结构适合入门。

但是如果我们要做真实 AI Chat，尤其是企业级 AI Agent 平台，就不能只传一个 message。

为什么？

因为真实大模型对话通常是多轮消息结构：

```json
[
  {
    "role": "system",
    "content": "你是一个专业 AI 助手"
  },
  {
    "role": "user",
    "content": "什么是 AI Agent？"
  },
  {
    "role": "assistant",
    "content": "AI Agent 是..."
  },
  {
    "role": "user",
    "content": "它和 RAG 有什么区别？"
  }
]
```

==所以这一章我们要把 `ChatRequest` 升级成真正接近企业项目的结构。==

同时，响应也不能只返回：

```json
{
  "answer": "..."
}
```

我们还需要返回：

```text
模型名称
会话 ID
token 用量
引用来源
trace_id
是否命中知识库
耗时
```

这就是这一章要解决的问题：

**如何用 Pydantic 设计一个可维护、可扩展、适合 AI 项目的请求和响应模型。**

---

## 五、02｜先回顾上一章的 ChatRequest

> [!success] 复盘要点
> 复盘时重点看这一节。

上一章的：

```text
app/schemas/chat.py
```

大概是这样：

```python
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=False, description="是否流式输出")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
```

---

### 【重点内容】
这个版本有几个问题。

第一个问题：

```text
只支持单轮 message
```

也就是说，它只能处理一个问题。

第二个问题：

```text
没有消息角色 role
```

大模型消息通常有：

```text
system
user
assistant
tool
```

第三个问题：

```text
响应太简单
```

真实项目里，前端不仅需要 answer，还需要：

```text
会话 ID
消息 ID
token 用量
来源引用
trace_id
```

第四个问题：

```text
没有扩展字段
```

后面接 RAG、Agent、Tool Calling 的时候会很难扩展。

==所以这一章我们来系统升级它。==

---

## 六、03｜创建新的 Chat Schema
### 【操作】
打开：

```text
app/schemas/chat.py
```

先清空原来的简单版本，准备重写。

---

### 【第一步：定义消息角色 Enum】
写入：

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

---

### 【重点内容】
我们先定义消息角色。

大模型对话里面，消息不是一堆普通字符串。

每条消息都有角色。

常见角色有：

```text
system
user
assistant
tool
```

其中：

```text
system
= 系统提示词，用来定义 AI 的身份和规则

user
= 用户输入

assistant
= AI 回复

tool
= 工具调用结果
```

这里我们使用 Python 的 Enum：

```python
class MessageRole(str, Enum):
```

为什么继承 `str`？

因为后面序列化成 JSON 的时候，我们希望它最终是字符串。

比如：

```json
{
  "role": "user"
}
```

而不是一个奇怪的 Python 对象。

---

## 七、04｜定义 ChatMessage
继续写：

```python
class ChatMessage(BaseModel):
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")
```

---

### 【重点内容】
现在我们定义一条聊天消息。

它有两个字段：

```text
role
content
```

role 表示消息角色。

content 表示消息内容。

比如一条用户消息：

```json
{
  "role": "user",
  "content": "什么是 AI Agent？"
}
```

对应到 Pydantic：

```python
ChatMessage(
    role=MessageRole.USER,
    content="什么是 AI Agent？"
)
```

这里我们给 content 设置了：

```python
min_length=1
```

表示消息内容不能为空。

因为空消息没有意义，也会浪费接口请求。

---

## 八、05｜定义 TokenUsage
继续写：

```python
class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0, description="输入 token 数")
    completion_tokens: int = Field(default=0, ge=0, description="输出 token 数")
    total_tokens: int = Field(default=0, ge=0, description="总 token 数")
```

---

### 【重点内容】
真实 AI 项目里，响应通常要返回 token 用量。

为什么？

因为 token 直接关系到：

```text
成本
限额
计费
性能分析
用户配额
```

所以我们定义一个：

```python
TokenUsage
```

它包括：

```text
prompt_tokens
completion_tokens
total_tokens
```

后面真正接入大模型 API 时，不同模型厂商都会返回类似 usage 的字段。

现在我们先把响应结构设计好。

---

## 九、06｜定义 SourceDocument 引用来源
继续写：

```python
class SourceDocument(BaseModel):
    document_id: str = Field(..., description="文档 ID")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="命中的文档片段")
    score: float = Field(default=0.0, ge=0, le=1, description="相关性分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="文档元数据")
```

---

### 【重点内容】
如果后面我们做 RAG，AI 回答不能只返回答案。

企业知识库问答通常要返回：

```text
答案
+
引用来源
```

比如用户问：

```text
公司的年假制度是什么？
```

AI 回答以后，要告诉用户：

```text
这个答案来自《员工手册》第 5 章
```

所以我们提前定义：

```python
SourceDocument
```

它包括：

```text
document_id
title
content
score
metadata
```

现在 Chat 接口可以先不用 sources。

但是提前设计好，后面接 RAG 会非常自然。

---

## 十、07｜定义 ChatRequest
继续写：

```python
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
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value
```

---

### 【重点内容】
现在这个 `ChatRequest` 就比上一章完整很多了。

我们从单个：

```python
message: str
```

升级成：

```python
messages: list[ChatMessage]
```

也就是支持多轮对话。

比如：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业 AI 助手"
    },
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

这里还有几个字段。

```python
session_id
```

用于表示会话。

```python
user_id
```

用于表示用户。

```python
metadata
```

用于放扩展信息。

比如：

```json
{
  "source": "web",
  "client": "admin-console"
}
```

最后：

```python
model_config = ConfigDict(extra="forbid")
```

表示不允许前端乱传未知字段。

这在企业接口里很重要。

---

## 十一、08｜定义 ChatResponse
继续写：

```python
class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
    session_id: str | None = Field(default=None, description="会话 ID")
    message_id: str | None = Field(default=None, description="消息 ID")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    sources: list[SourceDocument] = Field(default_factory=list, description="引用来源")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
```

---

### 【重点内容】
现在我们定义响应模型。

它不只是返回：

```python
answer
```

还包括：

```text
model
session_id
message_id
usage
sources
trace_id
```

这些字段后面都很有价值。

比如：

```text
session_id
= 前端继续追问时要带上

message_id
= 用于消息反馈、点赞、点踩

usage
= 用于统计 token 成本

sources
= RAG 引用来源

trace_id
= 排查问题、日志追踪
```

==你看，这就是企业项目和 Demo 的区别。==

Demo 只需要返回答案。

企业项目要考虑：

```text
会话
成本
来源
追踪
可维护性
```

---

## 十二、09｜完整代码：app/schemas/chat.py
最终完整代码如下：

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0, description="输入 token 数")
    completion_tokens: int = Field(default=0, ge=0, description="输出 token 数")
    total_tokens: int = Field(default=0, ge=0, description="总 token 数")


class SourceDocument(BaseModel):
    document_id: str = Field(..., description="文档 ID")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="命中的文档片段")
    score: float = Field(default=0.0, ge=0, le=1, description="相关性分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="文档元数据")


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
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
    session_id: str | None = Field(default=None, description="会话 ID")
    message_id: str | None = Field(default=None, description="消息 ID")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    sources: list[SourceDocument] = Field(default_factory=list, description="引用来源")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
```

---

## 十三、10｜升级 ChatService
打开：

```text
app/services/chat_service.py
```

修改代码：

```python
import asyncio
import uuid

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
        model=request.model,
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
现在我们升级了 ChatService。

这里重点看几个函数。

第一个：

```python
get_latest_user_message()
```

它的作用是从 messages 里找到最后一条用户消息。

为什么？

因为多轮对话里可能有很多消息：

```text
system
user
assistant
user
```

我们通常要拿最后一条 user 消息作为当前问题。

第二个：

```python
count_mock_tokens_from_messages()
```

这里我们只是模拟 token 统计。

真实项目里会使用模型厂商返回的 usage，或者用 tokenizer 计算。

第三个：

```python
build_mock_sources()
```

这里我们模拟 RAG 来源。

如果用户问题里包含：

```text
RAG
知识库
```

我们就返回一个模拟引用来源。

这样前端可以提前适配 sources 结构。

---

## 十四、11｜测试新的 Chat 接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

打开：

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
      "role": "system",
      "content": "你是一个专业的 AI 助手"
    },
    {
      "role": "user",
      "content": "什么是 RAG？"
    }
  ],
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false,
  "session_id": null,
  "user_id": "u_10001",
  "metadata": {
    "source": "swagger"
  }
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "RAG 是检索增强生成，用于让大模型结合企业私有知识库进行回答。",
    "model": "deepseek-chat",
    "session_id": "s_xxxxxxxx",
    "message_id": "m_xxxxxxxx",
    "usage": {
      "prompt_tokens": 25,
      "completion_tokens": 31,
      "total_tokens": 56
    },
    "sources": [
      {
        "document_id": "doc_001",
        "title": "企业知识库说明文档",
        "content": "RAG 是 Retrieval Augmented Generation，用于结合外部知识增强大模型回答。",
        "score": 0.89,
        "metadata": {
          "source": "mock",
          "page": 1
        }
      }
    ],
    "trace_id": "trace_xxxxxxxx"
  }
}
```

---

### 【重点内容】
现在大家看一下，这个接口已经很接近真实 AI Chat 接口了。

它不是简单返回一个 answer。

它返回：

```text
answer
model
session_id
message_id
usage
sources
trace_id
```

后面前端可以基于这些字段做很多事情。

比如：

```text
session_id
= 继续追问

message_id
= 点赞点踩

usage
= 显示 token 消耗

sources
= 展示引用来源

trace_id
= 报错时给后端排查
```

==这就是响应模型设计的价值。==

---

## 十五、12｜升级统一响应结构：使用泛型
上一章我们写的：

```python
class ApiResponse(BaseModel):
    code: int
    message: str
    data: Any
```

虽然简单，但是有一个问题：

```text
data 没有类型提示
```

现在我们升级成泛型响应。

打开：

```text
app/schemas/response.py
```

修改：

```python
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="响应数据")


class ErrorResponse(BaseModel):
    code: int = Field(default=500, description="错误码")
    message: str = Field(..., description="错误信息")
    detail: str | None = Field(default=None, description="错误详情")
```

---

### 【重点内容】
这里我们把：

```python
data: Any
```

升级成：

```python
data: T | None
```

这就是泛型。

如果你学过 TypeScript，可以类比：

```typescript
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
```

Python 里面是：

```python
T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: T | None
```

这样我们后面就可以写：

```python
ApiResponse[ChatResponse]
```

表示：

```text
这是一个统一响应结构
里面的 data 是 ChatResponse 类型
```

这样 IDE 和 Swagger 文档都更清晰。

---

## 十六、13｜让 Chat 接口使用泛型响应
修改：

```text
app/api/v1/chat.py
```

代码：

```python
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import ApiResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(request: ChatRequest) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(request)

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

### 【重点内容】
现在我们把接口响应模型升级成：

```python
response_model=ApiResponse[ChatResponse]
```

这表示接口返回的是统一响应结构。

其中：

```python
data
```

的类型是：

```python
ChatResponse
```

这样 Swagger 文档会更加清晰。

而且代码可读性也更强。

你看到接口定义就知道：

```text
这个接口返回 ApiResponse
data 里面是 ChatResponse
```

这比 `data: Any` 更适合企业项目。

---

## 十七、14｜Path + Query + Body 混合使用
真实项目里，一个接口可能同时有：

```text
Path 参数
Query 参数
Body 请求体
```

例如：

```http
POST /api/v1/conversations/{conversation_id}/chat?debug=true
```

Path 里有：

```text
conversation_id
```

Query 里有：

```text
debug
```

Body 里有：

```text
messages
model
temperature
```

---

### 【创建接口】
修改：

```text
app/api/v1/chat.py
```

增加：

```python
from fastapi import Path, Query
```

新增接口：

```python
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
```

---

### 【测试请求】
访问：

```http
POST /api/v1/conversations/c_10001/chat?debug=true
```

请求体：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "什么是 LangGraph？"
    }
  ],
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

---

### 【重点内容】
这里我们演示了 FastAPI 非常重要的能力：

```text
Path
+
Query
+
Body
```

混合使用。

```python
conversation_id: str = Path(...)
```

从路径里来。

```python
debug: bool = Query(...)
```

从 URL query 里来。

```python
request: ChatRequest
```

从请求体 JSON 里来。

FastAPI 会根据参数声明自动判断每个参数从哪里取。

这个能力后面会大量用到。

比如：

```http
POST /knowledge-bases/{kb_id}/query?top_k=5
POST /agents/{agent_id}/run?stream=true
GET /conversations/{conversation_id}/messages?page=1
```

---

## 十八、15｜新增 Conversation Schema
现在我们提前设计会话相关模型。

创建：

```text
app/schemas/conversation.py
```

写入：

```python
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ConversationCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="会话标题")


class ConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="会话状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class ConversationMessagesResponse(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    messages: list[ChatMessage] = Field(default_factory=list, description="消息列表")
```

---

### 【重点内容】
==AI Chat 一定会涉及会话管理。==

用户不是只问一个问题。

用户会：

```text
创建会话
连续追问
查看历史
删除会话
切换会话
```

所以我们提前定义：

```python
ConversationCreateRequest
ConversationResponse
ConversationMessagesResponse
```

注意这里：

```python
created_at: datetime = Field(default_factory=datetime.now)
```

表示默认使用当前时间。

这个写法比直接写一个固定时间更合适。

后面真正接数据库时，这些字段会对应数据库表。

---

## 十九、16｜新增 ConversationService
创建：

```text
app/services/conversation_service.py
```

写入：

```python
import uuid

from app.schemas.chat import ChatMessage, MessageRole
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationMessagesResponse,
    ConversationResponse,
)


async def create_conversation(
    request: ConversationCreateRequest,
) -> ConversationResponse:
    return ConversationResponse(
        conversation_id=f"c_{uuid.uuid4().hex[:8]}",
        title=request.title,
    )


async def get_conversation_messages(
    conversation_id: str,
) -> ConversationMessagesResponse:
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            ChatMessage(
                role=MessageRole.USER,
                content="什么是 AI Agent？"
            ),
            ChatMessage(
                role=MessageRole.ASSISTANT,
                content="AI Agent 是能够调用工具完成任务的智能体。"
            )
        ]
    )
```

---

### 【重点内容】
这里我们先用模拟数据。

真实项目里，这里应该查询数据库。

但是现在我们先把接口结构、请求模型、响应模型跑通。

==课程开发时建议大家养成这种习惯：==

```text
先设计 Schema
 ↓
再写 Service 假数据
 ↓
接口跑通
 ↓
最后替换真实数据库
```

这样开发速度很快，也方便调试。

---

## 二十、17｜新增 Conversation Router
创建：

```text
app/api/v1/conversations.py
```

写入：

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

修改：

```text
app/main.py
```

增加：

```python
from app.api.v1.conversations import router as conversations_router
```

注册：

```python
app.include_router(conversations_router, prefix="/api/v1", tags=["Conversations"])
```

---

### 【重点内容】
现在我们新增了会话接口。

第一个：

```http
POST /api/v1/conversations
```

创建会话。

第二个：

```http
GET /api/v1/conversations/{conversation_id}/messages
```

获取某个会话的消息列表。

你会发现，我们现在已经开始从一个简单 Chat 接口，慢慢扩展成完整 AI Chat 系统了。

==这就是企业项目的演进过程。==

---

## 二十一、18｜新增 RAG Schema
这一章虽然不是正式讲 RAG，但我们先把 RAG 请求响应模型设计出来。

创建：

```text
app/schemas/rag.py
```

写入：

```python
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chat import SourceDocument, TokenUsage


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    top_k: int = Field(default=5, ge=1, le=20, description="召回文档数量")
    rerank: bool = Field(default=True, description="是否开启重排")
    metadata_filter: dict[str, Any] = Field(default_factory=dict, description="元数据过滤条件")


class RAGQueryResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    knowledge_base_id: str = Field(..., description="知识库 ID")
    sources: list[SourceDocument] = Field(default_factory=list, description="引用来源")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
```

---

### 【重点内容】
虽然 RAG 是后面的阶段才正式讲。

但是这里我们先提前看一下 RAG 接口应该怎么设计。

一个 RAG 查询接口通常需要：

```text
question
knowledge_base_id
top_k
rerank
metadata_filter
```

其中：

```text
question
= 用户问题

knowledge_base_id
= 查哪个知识库

top_k
= 召回多少条文档

rerank
= 是否开启重排

metadata_filter
= 元数据过滤
```

响应里面通常包括：

```text
answer
sources
usage
trace_id
```

大家看，Pydantic 模型不是只用于 Chat。

它同样用于 RAG。

---

## 二十二、19｜新增 RAG Service
创建：

```text
app/services/rag_service.py
```

写入：

```python
import uuid

from app.schemas.chat import SourceDocument, TokenUsage
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse


async def query_rag(request: RAGQueryRequest) -> RAGQueryResponse:
    source = SourceDocument(
        document_id="doc_001",
        title="AI Agent 课程资料",
        content="RAG 是检索增强生成，用于让大模型结合外部知识回答问题。",
        score=0.92,
        metadata={
            "knowledge_base_id": request.knowledge_base_id,
            "page": 1,
        },
    )

    answer = f"根据知识库 {request.knowledge_base_id} 的内容，RAG 是检索增强生成。"

    return RAGQueryResponse(
        answer=answer,
        knowledge_base_id=request.knowledge_base_id,
        sources=[source],
        usage=TokenUsage(
            prompt_tokens=len(request.question),
            completion_tokens=len(answer),
            total_tokens=len(request.question) + len(answer),
        ),
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
    )
```

---

## 二十三、20｜新增 RAG Router
创建：

```text
app/api/v1/rag.py
```

写入：

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

修改：

```text
app/main.py
```

增加：

```python
from app.api.v1.rag import router as rag_router
```

注册：

```python
app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])
```

---

### 【重点内容】
现在我们增加了：

```http
POST /api/v1/rag/query
```

这个接口。

虽然现在还是模拟数据，但是接口结构已经具备真实 RAG 的雏形。

请求：

```json
{
  "question": "什么是 RAG？",
  "knowledge_base_id": "kb_001",
  "top_k": 5,
  "rerank": true,
  "metadata_filter": {}
}
```

响应：

```json
{
  "answer": "...",
  "sources": [],
  "usage": {},
  "trace_id": "..."
}
```

后面真正接入向量数据库、Embedding、Rerank 的时候，只需要替换 service 逻辑。

Schema 可以继续复用。

---

## 二十四、21｜main.py 完整注册
最终：

```text
app/main.py
```

代码：

```python
from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.rag import router as rag_router

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(conversations_router, prefix="/api/v1", tags=["Conversations"])
app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])


@app.get("/")
async def root():
    return {
        "message": "AI Agent Course API"
    }
```

---

## 二十五、22｜测试所有接口
启动：

```bash
uv run uvicorn app.main:app --reload
```

打开：

```http
http://127.0.0.1:8000/docs
```

你应该能看到：

```text
Health
Chat
Conversations
RAG
```

四个分组。

---

### 测试 1：创建会话
```http
POST /api/v1/conversations
```

请求：

```json
{
  "title": "AI Agent 学习咨询"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_xxxxxxxx",
    "title": "AI Agent 学习咨询",
    "status": "active",
    "created_at": "2026-xx-xxTxx:xx:xx",
    "updated_at": "2026-xx-xxTxx:xx:xx"
  }
}
```

---

### 测试 2：获取会话消息
```http
GET /api/v1/conversations/c_10001/messages
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_10001",
    "messages": [
      {
        "role": "user",
        "content": "什么是 AI Agent？"
      },
      {
        "role": "assistant",
        "content": "AI Agent 是能够调用工具完成任务的智能体。"
      }
    ]
  }
}
```

---

### 测试 3：Chat 多轮对话
```http
POST /api/v1/chat
```

请求：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业 AI 助手"
    },
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ],
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false,
  "session_id": "c_10001",
  "user_id": "u_10001",
  "metadata": {
    "source": "course-demo"
  }
}
```

---

### 测试 4：RAG 查询
```http
POST /api/v1/rag/query
```

请求：

```json
{
  "question": "什么是 RAG？",
  "knowledge_base_id": "kb_001",
  "top_k": 5,
  "rerank": true,
  "metadata_filter": {}
}
```

---

## 二十六、23｜前端 camelCase 和后端 snake_case 的问题
### 【重点内容】
现在我们讲一个真实前后端联调很常见的问题。

前端通常喜欢 camelCase：

```json
{
  "sessionId": "c_10001",
  "userId": "u_10001"
}
```

但是 Python 后端喜欢 snake_case：

```python
session_id
user_id
```

那到底接口用哪种？

有两种方案。

第一种：

```text
前后端统一使用 snake_case
```

这样最简单。

第二种：

```text
前端使用 camelCase
后端内部使用 snake_case
通过 Pydantic alias 适配
```

企业项目里两种都能看到。

如果前端团队强依赖 camelCase，我们可以用 alias。

---

## 二十七、24｜使用 alias 适配 sessionId
创建：

```text
app/schemas/chat_alias_demo.py
```

写入：

```python
from pydantic import BaseModel, ConfigDict, Field


class ChatAliasRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str | None = Field(default=None, alias="sessionId")
    user_id: str | None = Field(default=None, alias="userId")
    message: str


request1 = ChatAliasRequest(
    sessionId="c_10001",
    userId="u_10001",
    message="你好"
)

request2 = ChatAliasRequest(
    session_id="c_10002",
    user_id="u_10002",
    message="你好"
)

print(request1.model_dump())
print(request1.model_dump(by_alias=True))
print(request2.model_dump())
```

运行：

```bash
python app/schemas/chat_alias_demo.py
```

输出：

```text
{'session_id': 'c_10001', 'user_id': 'u_10001', 'message': '你好'}
{'sessionId': 'c_10001', 'userId': 'u_10001', 'message': '你好'}
{'session_id': 'c_10002', 'user_id': 'u_10002', 'message': '你好'}
```

---

### 【重点内容】
这里：

```python
Field(alias="sessionId")
```

表示前端可以传：

```json
{
  "sessionId": "c_10001"
}
```

Python 里面仍然用：

```python
request.session_id
```

而：

```python
model_config = ConfigDict(populate_by_name=True)
```

表示：

```text
sessionId 可以传
session_id 也可以传
```

最后：

```python
model_dump(by_alias=True)
```

可以把响应重新序列化成 camelCase。

这个在前后端协作时非常有用。

---

## 二十八、25｜响应模型过滤敏感字段
### 【创建示例】
创建：

```text
app/schemas/user_response_demo.py
```

写入：

```python
from pydantic import BaseModel


class UserInDB(BaseModel):
    user_id: str
    username: str
    email: str
    password_hash: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str


user = UserInDB(
    user_id="u_10001",
    username="dawei",
    email="dawei@example.com",
    password_hash="hashed_password_xxx"
)

response = UserResponse(
    user_id=user.user_id,
    username=user.username,
    email=user.email
)

print(response.model_dump())
```

运行：

```bash
python app/schemas/user_response_demo.py
```

输出：

```text
{'user_id': 'u_10001', 'username': 'dawei', 'email': 'dawei@example.com'}
```

---

### 【重点内容】
响应模型非常重要的一个作用是：

**不要把敏感字段返回给前端。**

比如数据库里的用户对象可能有：

```text
password_hash
api_key
secret_key
```

这些字段一定不能返回。

==所以企业项目里经常会区分：==

```text
UserInDB
= 数据库模型

UserResponse
= 返回给前端的模型
```

后面我们做用户系统、API Key、LLM Provider 配置时，这个原则非常重要。

---

## 二十九、26｜错误响应模型设计
打开：

```text
app/schemas/response.py
```

我们已经有：

```python
class ErrorResponse(BaseModel):
    code: int = Field(default=500, description="错误码")
    message: str = Field(..., description="错误信息")
    detail: str | None = Field(default=None, description="错误详情")
```

现在创建一个示例接口。

修改：

```text
app/api/v1/health.py
```

增加：

```python
from fastapi import HTTPException


@router.get("/error-demo")
async def error_demo():
    raise HTTPException(
        status_code=400,
        detail="这是一个错误示例"
    )
```

访问：

```http
GET /api/v1/error-demo
```

返回：

```json
{
  "detail": "这是一个错误示例"
}
```

---

### 【重点内容】
现在 FastAPI 默认错误格式是：

```json
{
  "detail": "..."
}
```

这没问题。

但是企业项目里，我们通常希望错误也统一成：

```json
{
  "code": 400,
  "message": "Bad Request",
  "detail": "具体错误"
}
```

这个我们会在后面的异常处理章节专门讲。

这一章先把 ErrorResponse 模型定义出来。

后面我们会通过全局异常处理器统一错误格式。

---

## 三十、27｜Body 参数：单独声明请求体字段
==有时候接口不一定需要一个完整 Pydantic 模型，也可以用 `Body` 声明单个 Body 字段。==

修改：

```text
app/api/v1/chat.py
```

导入：

```python
from fastapi import APIRouter, Body, Path, Query
```

新增接口：

```python
@router.post("/chat/title")
async def generate_chat_title(
    message: str = Body(..., embed=True, min_length=1, description="用户第一条消息"),
):
    return {
        "title": message[:20]
    }
```

请求：

```json
{
  "message": "帮我介绍一下 AI Agent 的核心能力"
}
```

返回：

```json
{
  "title": "帮我介绍一下 AI Agent "
}
```

---

### 【重点内容】
这里我们使用了：

```python
Body
```

它表示这个参数来自请求体。

```python
embed=True
```

表示请求体是：

```json
{
  "message": "..."
}
```

而不是直接传一个 JSON 字符串。

==不过企业项目里，如果请求体稍微复杂一点，还是推荐定义 Pydantic 模型。==

比如：

```python
class GenerateTitleRequest(BaseModel):
    message: str
```

这样更清晰，也更方便扩展。

---

## 三十一、28｜新增 GenerateTitleRequest
为了更规范，我们把刚才的 Body 改成模型。

打开：

```text
app/schemas/chat.py
```

追加：

```python
class GenerateTitleRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="用户第一条消息")


class GenerateTitleResponse(BaseModel):
    title: str = Field(..., description="生成的会话标题")
```

修改：

```text
app/api/v1/chat.py
```

导入：

```python
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    GenerateTitleRequest,
    GenerateTitleResponse,
)
```

新增接口：

```python
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

### 【重点内容】
大家看，虽然 Body 可以直接声明单个字段。

但是我更推荐使用：

```python
GenerateTitleRequest
GenerateTitleResponse
```

为什么？

因为这样接口结构更清晰。

以后要增加：

```text
model
language
max_length
```

这些字段时，只需要扩展 Pydantic 模型。

不用改一堆函数参数。

==所以企业项目里面，复杂接口尽量使用 Request Model 和 Response Model。==

---

## 三十二、29｜完整代码：app/api/v1/chat.py
最终这一章的 `chat.py` 可以整理成：

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

## 三十三、30｜现在的接口清单
打开：

```http
http://127.0.0.1:8000/docs
```

现在我们应该看到：

```text
Health
  GET /api/v1/health
  GET /api/v1/error-demo

Chat
  POST /api/v1/chat
  POST /api/v1/conversations/{conversation_id}/chat
  POST /api/v1/chat/title

Conversations
  POST /api/v1/conversations
  GET /api/v1/conversations/{conversation_id}/messages

RAG
  POST /api/v1/rag/query
```

---

### 【重点内容】
大家看，现在我们的接口已经不再是一个简单 Demo 了。

它已经开始有了真实 AI 应用的结构：

```text
Chat
Conversations
RAG
```

每个接口都有自己的：

```text
Request Model
Response Model
统一响应结构
Swagger 文档
参数校验
```

==这就是我们这一章的核心成果。==

---

## 三十四、31｜使用 tests/test_schema.py 测试 Schema
创建：

```text
tests/test_schema.py
```

写入：

```python
from app.schemas.chat import ChatMessage, ChatRequest, MessageRole


request = ChatRequest(
    messages=[
        ChatMessage(
            role=MessageRole.SYSTEM,
            content="你是一个专业 AI 助手"
        ),
        ChatMessage(
            role=MessageRole.USER,
            content="什么是 AI Agent？"
        )
    ],
    model="deepseek-chat",
    temperature=0.7,
    stream=False,
)

print(request.model_dump())
```

运行：

```bash
python tests/test_schema.py
```

---

### 【重点内容】
这里我们不通过 FastAPI，直接测试 Pydantic Schema。

这个习惯很好。

因为有时候接口报错，可能不是路由问题，而是 Schema 校验问题。

我们可以单独运行：

```text
tests/test_schema.py
```

看模型能不能正常创建。

后面复杂项目里，Schema 单独测试非常有价值。

---

## 三十五、32｜使用 requests 测试 Chat 接口
修改：

```text
tests/test_chat_api.py
```

写入：

```python
import requests


url = "http://127.0.0.1:8000/api/v1/chat"

payload = {
    "messages": [
        {
            "role": "system",
            "content": "你是一个专业 AI 助手"
        },
        {
            "role": "user",
            "content": "什么是 AI Agent？"
        }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": False,
    "session_id": "c_10001",
    "user_id": "u_10001",
    "metadata": {
        "client": "python-requests"
    }
}

response = requests.post(url, json=payload)

print(response.status_code)
print(response.json())
```

运行前确保服务启动：

```bash
uv run uvicorn app.main:app --reload
```

另开一个终端执行：

```bash
python tests/test_chat_api.py
```

---

## 三十六、33｜常见错误一：messages 为空

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误请求：

```json
{
  "messages": [],
  "model": "deepseek-chat"
}
```

会报校验错误。

因为我们定义了：

```python
messages: list[ChatMessage] = Field(..., min_length=1)
```

---

### 【重点内容】
AI Chat 至少要有一条消息。

==所以 messages 不能为空。==

如果为空，Pydantic 会直接拦截。

这比业务代码里再判断更好。

---

## 三十七、34｜常见错误二：role 写错
错误请求：

```json
{
  "messages": [
    {
      "role": "human",
      "content": "你好"
    }
  ],
  "model": "deepseek-chat"
}
```

会报错。

因为我们只允许：

```text
system
user
assistant
tool
```

---

### 【重点内容】
这里体现了 Enum 的价值。

如果不用 Enum，前端传：

```text
human
```

后端可能会继续往下走，最后调用模型时报错。

现在我们在请求入口就拦截掉。

这就是请求模型的价值：

**错误越早发现，系统越稳定。**

---

## 三十八、35｜常见错误三：多传未知字段

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误请求：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "你好"
    }
  ],
  "model": "deepseek-chat",
  "unknown": "xxx"
}
```

会报错。

因为：

```python
model_config = ConfigDict(extra="forbid")
```

---

### 【重点内容】
有时候前端多传一个字段，后端默认忽略，看起来没问题。

但是在严格系统里，未知字段可能代表：

```text
前端字段拼错
接口文档不一致
版本不匹配
潜在安全风险
```

==所以在核心接口里，我建议使用：==

```python
extra="forbid"
```

这样接口更严谨。

---

## 三十九、36｜常见错误四：response_model 和实际返回不一致

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误示例：

```python
@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(request: ChatRequest):
    return {
        "answer": "你好"
    }
```

问题：

```text
response_model 要求 ApiResponse[ChatResponse]
但是实际只返回 answer
```

正确：

```python
return ApiResponse[ChatResponse](
    data=ChatResponse(
        answer="你好",
        model=request.model
    )
)
```

---

### 【重点内容】
response_model 不是摆设。

你写了什么响应模型，就尽量按这个结构返回。

否则 Swagger 文档和实际返回对不上，前端会很痛苦。

---

## 四十、37｜常见错误五：把数据库模型直接返回给前端

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误习惯：

```python
return user_db
```

风险：

```text
可能返回 password_hash
可能返回内部字段
可能返回不该暴露的配置
```

正确做法：

```python
return UserResponse(
    user_id=user_db.user_id,
    username=user_db.username,
    email=user_db.email
)
```

---

## 四十一、38｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| `ChatMessage` | 多轮对话消息 |
| `MessageRole` | system / user / assistant / tool |
| `ChatRequest` | AI Chat 请求体 |
| `ChatResponse` | AI Chat 响应体 |
| `TokenUsage` | token 成本统计 |
| `SourceDocument` | RAG 引用来源 |
| `ApiResponse[T]` | 统一响应格式 |
| `ErrorResponse` | 错误响应格式 |
| `ConversationResponse` | 会话管理 |
| `RAGQueryRequest` | 知识库问答请求 |
| `RAGQueryResponse` | 知识库问答响应 |
| `Path` | 会话 ID、知识库 ID、Agent ID |
| `Query` | debug、top_k、分页参数 |
| `Body` | 请求体字段 |
| `Field` | 参数说明和校验规则 |
| `Enum` | 固定角色、状态、类型 |
| `default_factory` | 默认空列表、默认时间、默认对象 |
| `alias` | 前端 camelCase 适配 |
| `response_model` | 生成文档、控制响应结构 |


---

## 四十二、39｜本章完整复习
这一章我们完成了：

```text
1. 升级 ChatMessage
2. 升级 ChatRequest
3. 升级 ChatResponse
4. 增加 TokenUsage
5. 增加 SourceDocument
6. 增加泛型 ApiResponse[T]
7. 设计 ErrorResponse
8. 混合使用 Path / Query / Body
9. 新增 Conversation Schema
10. 新增 RAG Schema
11. 新增 Conversation Router
12. 新增 RAG Router
13. 解决 camelCase / snake_case 问题
14. 演示响应模型过滤敏感字段
15. 测试 Schema 和 API
```

现在我们的项目已经从：

```text
简单 /chat Demo
```

升级成了：

```text
Chat
Conversations
RAG
统一响应
Schema 分层
Service 分层
```

==这就是企业级 AI 应用后端的雏形。==

---

## 四十三、40｜课后任务一：给 ChatResponse 增加 latency_ms
要求：

```text
1. 在 ChatResponse 中增加 latency_ms
2. 类型为 int
3. 默认值为 0
4. description 写“接口耗时，单位毫秒”
5. 在 chat_service.py 中模拟返回 500
```

参考答案：

```python
class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
    session_id: str | None = Field(default=None, description="会话 ID")
    message_id: str | None = Field(default=None, description="消息 ID")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token 用量")
    sources: list[SourceDocument] = Field(default_factory=list, description="引用来源")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
    latency_ms: int = Field(default=0, ge=0, description="接口耗时，单位毫秒")
```

---

## 四十四、41｜课后任务二：新增 ModelListResponse
要求：

```text
1. 创建 ModelInfo
2. 字段包括 name、provider、support_stream
3. 创建 ModelListResponse
4. 返回 models: list[ModelInfo]
5. 新增 GET /api/v1/models
```

参考答案：

```python
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="模型厂商")
    support_stream: bool = Field(default=True, description="是否支持流式输出")


class ModelListResponse(BaseModel):
    models: list[ModelInfo] = Field(default_factory=list, description="模型列表")
```

---

## 四十五、42｜课后任务三：新增 AgentRunRequest
要求：

```text
1. 创建 app/schemas/agent.py
2. 定义 AgentRunRequest
3. 字段包括 question、agent_id、stream、metadata
4. question 最小长度 1
5. metadata 默认空 dict
```

参考答案：

```python
from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    agent_id: str = Field(..., description="Agent ID")
    stream: bool = Field(default=True, description="是否流式输出")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
```

---

## 四十六、43｜课后任务四：新增 AgentRunResponse
要求：

```text
1. 定义 AgentStep
2. 定义 AgentRunResponse
3. 字段包括 answer、steps、trace_id
```

参考答案：

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStepType(str, Enum):
    THINK = "think"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL = "final"


class AgentStep(BaseModel):
    step_type: AgentStepType = Field(..., description="步骤类型")
    content: str = Field(..., description="步骤内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class AgentRunResponse(BaseModel):
    answer: str = Field(..., description="最终回答")
    steps: list[AgentStep] = Field(default_factory=list, description="执行步骤")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")
```

---

## 四十七、44｜课后任务五：用 Swagger 测试所有错误请求
测试以下错误：

```text
1. messages 为空
2. role 写成 human
3. temperature 写成 3
4. model 写成 unknown-model
5. 多传 unknown 字段
6. RAG top_k 写成 100
7. Conversation title 为空
```

要求：

```text
观察每个错误的 detail
理解 loc 字段表示错误位置
理解 msg 字段表示错误原因
```

---

## 四十八、45｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 07 章我们就讲完了。

这一章非常关键。

因为从这一章开始，我们已经不是在写简单接口了。

我们开始真正设计企业级 AI 应用的数据结构。

大家一定要记住：

```text
Request Model
不是随便接收参数

Response Model
不是随便返回 JSON
```

它们代表的是：

```text
前后端接口协议
业务数据结构
参数校验规则
Swagger 文档来源
系统扩展能力
```

这一章我们把 Chat 接口从：

```json
{
  "message": "什么是 AI Agent？"
}
```

升级成：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业 AI 助手"
    },
    {
      "role": "user",
      "content": "什么是 AI Agent？"
    }
  ],
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false,
  "session_id": "c_10001",
  "user_id": "u_10001",
  "metadata": {}
}
```

响应也从：

```json
{
  "answer": "..."
}
```

升级成：

```json
{
  "answer": "...",
  "model": "deepseek-chat",
  "session_id": "c_10001",
  "message_id": "m_10001",
  "usage": {},
  "sources": [],
  "trace_id": "trace_xxx"
}
```

==这就是企业级 AI Chat 接口应该具备的基础结构。==

后面我们接入真正的大模型、RAG、Agent、Tool Calling 时，这些 Schema 都可以继续复用和扩展。

所以大家一定要重视 Schema 设计。

很多项目后面难维护，不是因为模型调用难，而是因为一开始接口结构没有设计好。

---

> [!success] 一句话带走
> ==先把数据契约定死，业务代码才不会越写越乱。==

> [!quote] 关于本文档
> 由原始讲义 `第 07 章｜Pydantic 请求参数与响应模型.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
