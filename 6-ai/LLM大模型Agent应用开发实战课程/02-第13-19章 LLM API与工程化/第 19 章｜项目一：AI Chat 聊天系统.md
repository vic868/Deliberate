---

# 一、本章定位
前面我们已经完成了很多基础能力：

```plain
第 06 章｜FastAPI 快速入门
第 07 章｜Pydantic 请求参数与响应模型
第 08 章｜FastAPI Router 与项目工程化
第 09 章｜FastAPI Dependency Injection 依赖注入
第 10 章｜Middleware、异常处理与日志
第 11 章｜PostgreSQL + SQLAlchemy 数据库开发
补充小节｜Alembic 数据库迁移入门
第 12 章｜Redis 在 AI 应用中的使用
第 13 章｜大模型 API 原理
第 14 章｜统一 LLM Provider 架构
第 15 章｜Prompt Engineering 工程化实战
第 16 章｜Streaming 流式输出
第 17 章｜Structured Output 结构化输出
第 18 章｜Function Calling 与 Tool Calling
```

这些章节分别解决了不同问题。

但是学员学到这里，最需要的是：

**把这些能力串起来，做成一个完整可运行项目。**

所以第 19 章就是项目整合章。

我们要完成第一个正式项目：

# 项目一：AI Chat 聊天系统
这个项目不是简单写一个：

```plain
POST /chat
```

而是要做成一个具备企业 AI 应用雏形的聊天系统。

它要支持：

```plain
1. 创建会话
2. 查询会话列表
3. 查询会话消息
4. 普通非流式 Chat
5. Streaming 流式 Chat
6. Prompt 场景选择
7. Redis 响应缓存
8. PostgreSQL 消息持久化
9. Token Usage 记录
10. 电商客服 Tool Calling
11. 统一错误处理
12. 前端 HTML Demo 联调
```

这一章结束后，学员就能拿到一个可以演示的 AI Chat 后端项目。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 如何把前面零散能力整合成一个项目
2. 如何设计 AI Chat 项目整体链路
3. 如何设计会话 Conversation
4. 如何设计消息 Message
5. 如何设计普通 Chat 接口
6. 如何设计 Streaming Chat 接口
7. 如何处理 session_id / conversation_id
8. 如何保存用户消息和 AI 回复
9. 如何保存 token usage
10. 如何读取历史消息作为上下文
11. 如何使用 Redis 做响应缓存
12. 如何使用 PromptScenario 控制不同场景
13. 如何在电商客服场景接入 Tool Calling
14. 如何让普通 Chat 和 Stream Chat 复用同一套能力
15. 如何写完整 curl 联调命令
16. 如何写前端 HTML Demo
17. 如何排查项目整合阶段常见问题
18. 如何给项目做最终复盘
```

---

# 三、本章最终效果
本章结束后，可以完成下面几条链路。

---

## 链路一：创建会话
```plain
POST /api/v1/conversations
```

返回：

```json
{
  "conversation_id": "c_xxxxxxxx",
  "title": "AI Agent 学习咨询",
  "status": "active"
}
```

---

## 链路二：普通 Chat
```plain
POST /api/v1/chat
```

支持：

```plain
非流式返回
真实 LLM Provider
Prompt 工程化
Redis 缓存
PostgreSQL 保存消息
Token Usage 保存
```

---

## 链路三：Streaming Chat
```plain
POST /api/v1/chat/stream
```

支持：

```plain
start 事件
message 事件
done 事件
error 事件
前端打字机效果
```

---

## 链路四：电商客服 Tool Calling
```plain
POST /api/v1/chat
prompt_scenario=ecommerce_customer_service
```

用户问：

```plain
帮我查一下订单 10001 到哪了？
```

系统自动：

```plain
识别电商客服场景
 ↓
启用 tools
 ↓
模型选择 query_order
 ↓
后端执行工具
 ↓
模型基于工具结果回复
```

---

# 四、本章最终项目结构
本章结束后的核心结构：

```plain
ai-agent-course/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       ├── models.py
│   │       ├── prompts.py
│   │       ├── structured_outputs.py
│   │       └── tool_calling.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   ├── exception_handlers.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   └── request_context.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── dependencies/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── llm.py
│   │   └── rate_limit.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── repositories/
│   │   └── conversation_repository.py
│   │
│   ├── schemas/
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   ├── response.py
│   │   └── user.py
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── chat_stream_service.py
│   │   ├── conversation_service.py
│   │   ├── prompt_service.py
│   │   ├── structured_output_service.py
│   │   └── tool_calling_service.py
│   │
│   ├── redis/
│   │   ├── cache.py
│   │   ├── client.py
│   │   ├── keys.py
│   │   └── rate_limit.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   ├── schemas.py
│   │   ├── factory.py
│   │   └── providers/
│   │
│   ├── prompts/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── renderer.py
│   │   ├── templates.py
│   │   ├── ecommerce.py
│   │   ├── rag.py
│   │   ├── agent.py
│   │   └── structured.py
│   │
│   ├── structured_outputs/
│   │   ├── parser.py
│   │   ├── response_format.py
│   │   └── schemas.py
│   │
│   ├── tools/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── schemas.py
│   │   └── ecommerce.py
│   │
│   └── utils/
│       └── sse.py
│
├── scripts/
│   ├── create_tables.py
│   ├── test_db.py
│   ├── test_redis.py
│   ├── test_ai_chat_flow.py
│   └── test_chat_stream.py
│
├── frontend-demo/
│   └── ai-chat-demo.html
│
├── docker-compose.yml
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 19 章。

这一章我们进入第一个完整项目：

# AI Chat 聊天系统
前面我们已经讲了很多基础能力。

如果这些能力单独看，可能有点分散。

比如：

```plain
FastAPI 是接口层
PostgreSQL 是持久化
Redis 是缓存
LLM Provider 是模型调用
Prompt 是控制模型输出
Streaming 是打字机效果
Structured Output 是结构化结果
Tool Calling 是工具调用
```

但是一个真正的 AI 应用，一定是把这些能力组合起来。

所以这一章我们不再单独讲概念。

我们要把它们组装成一个项目。

到这一章结束时，我们要有一个可以演示的 AI Chat 系统。

它可以创建会话，可以发送消息，可以流式输出，可以保存历史记录，还可以在电商客服场景调用订单查询工具。

这就是我们的第一个项目闭环。

---

# 六、02｜项目一整体架构图
## 【实操】
```plain
前端页面
  ↓
FastAPI Router
  ↓
ChatService / ChatStreamService
  ↓
PromptService
  ↓
Redis Cache
  ↓
LLMProvider
  ↓
DeepSeek / Qwen / OpenAI
  ↓
ToolCallingService（可选）
  ↓
ToolExecutor
  ↓
业务工具 query_order
  ↓
PostgreSQL 保存消息
```

---

## 【重点内容】
项目一的主链路就是这张图。

用户从前端发起请求。

FastAPI Router 接收请求。

Service 层处理业务逻辑。

PromptService 负责组装 Prompt。

Redis 负责缓存。

LLMProvider 负责调用大模型。

如果是电商客服问题，还会走 ToolCallingService。

工具执行完以后，模型再生成最终回复。

最后 PostgreSQL 保存消息记录。

这就是一个 AI Chat 系统的完整后端链路。

---

# 七、03｜本项目接口清单
## 【实操】
| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/health/redis` | GET | Redis 健康检查 |
| `/api/v1/conversations` | POST | 创建会话 |
| `/api/v1/conversations` | GET | 查询会话列表 |
| `/api/v1/conversations/{conversation_id}` | GET | 查询会话详情 |
| `/api/v1/conversations/{conversation_id}/messages` | GET | 查询会话消息 |
| `/api/v1/chat` | POST | 普通非流式 Chat |
| `/api/v1/chat/stream` | POST | 流式 Chat |
| `/api/v1/models` | GET | 查询支持模型 |
| `/api/v1/prompts` | GET | 查询 Prompt 列表 |
| `/api/v1/tools` | GET | 查询工具列表 |
| `/api/v1/tools/run` | POST | 独立测试 Tool Calling |


---

## 【重点内容】
这个项目要有一组完整接口，而不是只有一个 Chat。

为什么？

因为真实 AI Chat 产品至少需要：

```plain
会话管理
消息管理
模型调用
流式输出
历史记录
工具调用
```

所以这一章我们会把核心接口都串起来。

---

# 八、04｜确认环境配置
## `.env`
```plain
APP_NAME=AI Agent Course API
APP_ENV=development
APP_VERSION=0.1.0
API_V1_PREFIX=/api/v1
DEBUG=true

APP_API_KEY=dev-api-key-123

DEFAULT_MODEL=deepseek-chat
SUPPORTED_MODELS=deepseek-chat,qwen-plus,gpt-4o-mini

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course

REDIS_URL=redis://:redis123@localhost:6379/0
REDIS_DEFAULT_TTL_SECONDS=300
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_REQUESTS=20

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

DEEPSEEK_API_KEY=你的 DeepSeek Key
DEEPSEEK_BASE_URL=https://api.deepseek.com

DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 【重点内容】
开始项目前，先确认 `.env`。

这一章默认用：

```plain
deepseek-chat
```

作为模型。

所以需要配置：

```plain
DEEPSEEK_API_KEY
```

如果你想用 Qwen，就把：

```plain
DEFAULT_MODEL=qwen-plus
```

并配置：

```plain
DASHSCOPE_API_KEY
```

不要把真实 key 提交到 GitHub。

---

# 九、05｜确认 Docker Compose
## `docker-compose.yml`
```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: ai_agent_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_agent_course
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: ai_agent_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass redis123
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

启动：

```bash
docker compose up -d
```

检查：

```bash
docker ps
```

---

## 【重点内容】
项目一需要两个基础服务：

```plain
PostgreSQL
Redis
```

PostgreSQL 保存会话和消息。

Redis 做缓存和限流。

如果这两个没启动，项目一定跑不完整。

所以先执行：

```bash
docker compose up -d
```

确认容器正常。

---

# 十、06｜确认数据库模型
这一章继续使用第 11 章的三张核心表：

```plain
users
conversations
messages
```

为了项目一演示，我们重点使用：

```plain
conversations
messages
```

---

## `app/models/conversation.py`
```python
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
```

---

## `app/models/message.py`
```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
```

---

## 【重点内容】
项目一先不要设计太多表。

先抓住 AI Chat 的核心：

```plain
Conversation
Message
```

Conversation 表示一个会话。

Message 表示会话里的每条消息。

messages 表里除了 role 和 content，还要记录：

```plain
model
prompt_tokens
completion_tokens
total_tokens
```

这样后面可以做用量统计和成本分析。

---

# 十一、07｜确认 Conversation Schema
打开：

```plain
app/schemas/conversation.py
```

写入或确认：

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
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="会话标题",
    )


class ConversationResponse(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE,
        description="会话状态",
    )
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse] = Field(
        default_factory=list,
        description="会话列表",
    )


class ConversationMessagesResponse(BaseModel):
    conversation_id: str = Field(..., description="会话 ID")
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="消息列表",
    )
```

---

## 【重点内容】
这里把会话相关响应结构统一起来。

前端需要的不是数据库模型。

前端需要的是：

```plain
conversation_id
title
status
created_at
updated_at
messages
```

所以我们用 Pydantic 单独定义 response model。

不要把 SQLAlchemy ORM 对象直接返回给前端。

---

# 十二、08｜确认 Chat Schema
打开：

```plain
app/schemas/chat.py
```

项目一建议最终保持下面这个结构：

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
        description="对话消息列表",
    )
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="模型温度")
    stream: bool = Field(default=False, description="是否流式输出")

    session_id: str | None = Field(default=None, description="会话 ID")
    user_id: str | None = Field(default=None, description="用户 ID")

    prompt_scenario: str | None = Field(
        default=None,
        description="Prompt 场景，如 general_chat / ecommerce_customer_service / rag_qa",
    )
    prompt_version: str | None = Field(
        default="v1",
        description="Prompt 版本",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展元数据",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        supported_models = [
            "deepseek-chat",
            "qwen-plus",
            "gpt-4o-mini",
            "gpt-4.1-mini",
        ]

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
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")
```

---

## 【重点内容】
ChatRequest 现在比最初复杂了一点。

因为它要支持项目一的完整能力。

重点字段有：

```plain
messages
model
temperature
stream
session_id
prompt_scenario
prompt_version
metadata
```

其中：

```plain
prompt_scenario
```

用于控制场景。

比如普通聊天还是电商客服。

```plain
metadata
```

用于传额外业务数据。

比如订单信息、业务规则、知识库片段。

---

# 十三、09｜实现 ConversationRepository
打开：

```plain
app/repositories/conversation_repository.py
```

写入项目一完整版本：

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class ConversationRepository:
    async def create_conversation(
        self,
        db: AsyncSession,
        title: str,
        user_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            id=f"c_{uuid.uuid4().hex[:8]}",
            title=title,
            user_id=user_id,
            status="active",
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.status == "active")
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )

        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)

        result = await db.execute(stmt)

        return list(result.scalars().all())

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.status == "active",
        )

        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        model: str | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> Message:
        message = Message(
            id=f"m_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        return message

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        limit: int = 50,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)

        return list(result.scalars().all())

    async def archive_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> bool:
        conversation = await self.get_conversation(
            db=db,
            conversation_id=conversation_id,
        )

        if not conversation:
            return False

        conversation.status = "archived"

        await db.commit()

        return True


conversation_repository = ConversationRepository()
```

---

## 【重点内容】
Repository 负责数据库操作。

这里我们提供几个基础方法：

```plain
create_conversation
list_conversations
get_conversation
add_message
get_messages
archive_conversation
```

注意，业务逻辑不要写在 Repository 里。

Repository 只处理数据库。

比如要不要调用模型、要不要查缓存，这些放到 Service。

这就是分层。

---

# 十四、10｜实现 ConversationService
打开：

```plain
app/services/conversation_service.py
```

写入：

```python
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ErrorCode
from app.redis.cache import (
    cache_recent_messages,
    get_cached_recent_messages,
)
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import ChatMessage, MessageRole
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    ConversationStatus,
)


class ConversationService:
    async def create_conversation(
        self,
        db: AsyncSession,
        request: ConversationCreateRequest,
        user_id: str | None = None,
    ) -> ConversationResponse:
        conversation = await conversation_repository.create_conversation(
            db=db,
            title=request.title,
            user_id=user_id,
        )

        return self._to_response(conversation)

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        limit: int = 20,
    ) -> ConversationListResponse:
        conversations = await conversation_repository.list_conversations(
            db=db,
            user_id=user_id,
            limit=limit,
        )

        return ConversationListResponse(
            conversations=[
                self._to_response(conversation)
                for conversation in conversations
            ]
        )

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> ConversationResponse:
        conversation = await conversation_repository.get_conversation(
            db=db,
            conversation_id=conversation_id,
        )

        if not conversation:
            raise AppException(
                message="会话不存在",
                code=ErrorCode.NOT_FOUND,
                status_code=404,
            )

        return self._to_response(conversation)

    async def get_conversation_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        redis: Redis | None = None,
    ) -> ConversationMessagesResponse:
        if redis:
            cached_messages = await get_cached_recent_messages(
                redis=redis,
                conversation_id=conversation_id,
            )

            if cached_messages is not None:
                return ConversationMessagesResponse(
                    conversation_id=conversation_id,
                    messages=cached_messages,
                )

        messages = await conversation_repository.get_messages(
            db=db,
            conversation_id=conversation_id,
        )

        chat_messages = [
            ChatMessage(
                role=MessageRole(message.role),
                content=message.content,
            )
            for message in messages
        ]

        if redis:
            await cache_recent_messages(
                redis=redis,
                conversation_id=conversation_id,
                messages=chat_messages[-10:],
            )

        return ConversationMessagesResponse(
            conversation_id=conversation_id,
            messages=chat_messages,
        )

    def _to_response(self, conversation) -> ConversationResponse:
        return ConversationResponse(
            conversation_id=conversation.id,
            title=conversation.title,
            status=ConversationStatus(conversation.status),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )


conversation_service = ConversationService()
```

---

## 【重点内容】
ConversationService 负责会话业务。

比如：

```plain
创建会话
查询会话
查询消息
缓存最近消息
```

这里查询消息时，我们用到了 Redis。

流程是：

```plain
先查 Redis
命中直接返回
未命中查 PostgreSQL
查完写 Redis
```

这就是第 12 章讲的缓存模式。

---

# 十五、11｜实现 Conversations Router
打开：

```plain
app/api/v1/conversations.py
```

写入：

```python
from fastapi import APIRouter, Depends, Path, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db_session
from app.dependencies.redis import get_redis_client
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationResponse,
)
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.services.conversation_service import conversation_service


router = APIRouter()


@router.post(
    "/conversations",
    response_model=ApiResponse[ConversationResponse],
)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    result = await conversation_service.create_conversation(
        db=db,
        request=request,
        user_id=current_user.user_id,
    )

    return ApiResponse[ConversationResponse](
        data=result
    )


@router.get(
    "/conversations",
    response_model=ApiResponse[ConversationListResponse],
)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationListResponse]:
    result = await conversation_service.list_conversations(
        db=db,
        user_id=current_user.user_id,
        limit=limit,
    )

    return ApiResponse[ConversationListResponse](
        data=result
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[ConversationResponse],
)
async def get_conversation(
    conversation_id: str = Path(..., description="会话 ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationResponse]:
    result = await conversation_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
    )

    return ApiResponse[ConversationResponse](
        data=result
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[ConversationMessagesResponse],
)
async def get_conversation_messages(
    conversation_id: str = Path(..., description="会话 ID"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> ApiResponse[ConversationMessagesResponse]:
    result = await conversation_service.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        redis=redis,
    )

    return ApiResponse[ConversationMessagesResponse](
        data=result
    )
```

---

## 【重点内容】
这里完成会话接口。

注意每个接口都注入了：

```python
current_user: CurrentUser = Depends(get_current_user)
```

因为真实系统里，会话一定属于某个用户。

这一章先用 header 模拟用户。

后面权限系统章节会再升级。

---

# 十六、12｜项目一 ChatService 整合版
打开：

```plain
app/services/chat_service.py
```

这一章推荐整理成下面这个版本：

```python
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import LLMProviderError
from app.llm.factory import LLMProviderFactory
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole
from app.prompts.base import PromptScenario
from app.redis.cache import cache_chat_response, get_cached_chat_response
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRole,
    SourceDocument,
    TokenUsage,
)
from app.services.prompt_service import prompt_service
from app.services.tool_calling_service import tool_calling_service


logger = get_logger(__name__)


async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
    llm_provider: BaseLLMProvider | None = None,
) -> ChatResponse:
    latest_user_message = get_latest_user_message(request)
    model = request.model or settings.default_model

    logger.info(
        f"chat_start model={model} "
        f"session_id={request.session_id} "
        f"scenario={request.prompt_scenario}"
    )

    if should_use_tool_calling(request):
        return await chat_with_tools(
            request=request,
            latest_user_message=latest_user_message,
            model=model,
            llm_provider=llm_provider,
        )

    if redis:
        cached_answer = await get_cached_chat_response(
            redis=redis,
            question=latest_user_message,
        )

        if cached_answer:
            logger.info("chat_response_cache_hit")

            return ChatResponse(
                answer=cached_answer,
                model=model,
                session_id=request.session_id,
                message_id=f"m_{uuid.uuid4().hex[:8]}",
                usage=TokenUsage(),
                sources=[],
                trace_id=f"trace_{uuid.uuid4().hex[:8]}",
                metadata={
                    "cache_hit": True,
                },
            )

    llm_provider = llm_provider or LLMProviderFactory.create()

    llm_request = build_llm_request_from_chat_request(request)

    try:
        llm_response = await llm_provider.chat(llm_request)

    except LLMProviderError as exc:
        logger.exception(
            f"chat_llm_provider_error provider={exc.provider} "
            f"status_code={exc.status_code}"
        )

        raise AppException(
            message=exc.message,
            code=ErrorCode.LLM_CALL_FAILED,
            status_code=500,
            data={
                "provider": exc.provider,
                "status_code": exc.status_code,
            },
        ) from exc

    answer = llm_response.content

    usage = TokenUsage(
        prompt_tokens=llm_response.usage.prompt_tokens,
        completion_tokens=llm_response.usage.completion_tokens,
        total_tokens=llm_response.usage.total_tokens,
    )

    if redis and answer:
        await cache_chat_response(
            redis=redis,
            question=latest_user_message,
            answer=answer,
        )

    if db and request.session_id:
        await save_chat_messages(
            db=db,
            conversation_id=request.session_id,
            user_message=latest_user_message,
            assistant_message=answer,
            model=model,
            usage=usage,
        )

    logger.info(
        f"chat_success model={model} "
        f"answer_length={len(answer)} "
        f"total_tokens={usage.total_tokens}"
    )

    return ChatResponse(
        answer=answer,
        model=model,
        session_id=request.session_id or f"s_{uuid.uuid4().hex[:8]}",
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=usage,
        sources=build_mock_sources(latest_user_message),
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "cache_hit": False,
        },
    )


def should_use_tool_calling(request: ChatRequest) -> bool:
    return request.prompt_scenario == PromptScenario.ECOMMERCE_CUSTOMER_SERVICE.value


async def chat_with_tools(
    request: ChatRequest,
    latest_user_message: str,
    model: str,
    llm_provider: BaseLLMProvider | None,
) -> ChatResponse:
    llm_provider = llm_provider or LLMProviderFactory.create()

    tool_result = await tool_calling_service.run_with_tools(
        user_question=latest_user_message,
        model=model,
        llm_provider=llm_provider,
    )

    return ChatResponse(
        answer=tool_result["answer"],
        model=model,
        session_id=request.session_id or f"s_{uuid.uuid4().hex[:8]}",
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=TokenUsage(),
        sources=[],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "tool_calls": tool_result.get("tool_calls", []),
            "tool_results": tool_result.get("tool_results", []),
        },
    )


async def save_chat_messages(
    db: AsyncSession,
    conversation_id: str,
    user_message: str,
    assistant_message: str,
    model: str,
    usage: TokenUsage,
):
    await conversation_repository.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.USER.value,
        content=user_message,
        model=model,
        prompt_tokens=usage.prompt_tokens,
    )

    await conversation_repository.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT.value,
        content=assistant_message,
        model=model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )


def build_llm_request_from_chat_request(request: ChatRequest) -> LLMRequest:
    return LLMRequest(
        model=request.model,
        messages=build_prompt_messages_for_chat(request),
        temperature=request.temperature,
        stream=request.stream,
    )


def build_prompt_messages_for_chat(request: ChatRequest) -> list[LLMMessage]:
    has_system_message = any(
        message.role == MessageRole.SYSTEM
        for message in request.messages
    )

    if has_system_message:
        return [
            LLMMessage(
                role=LLMRole(message.role.value),
                content=message.content,
            )
            for message in request.messages
        ]

    latest_user_message = get_latest_user_message(request)

    if request.prompt_scenario == PromptScenario.ECOMMERCE_CUSTOMER_SERVICE.value:
        return prompt_service.render_by_scenario(
            scenario=PromptScenario.ECOMMERCE_CUSTOMER_SERVICE,
            version=request.prompt_version or "v1",
            variables={
                "user_question": latest_user_message,
                "business_rules": request.metadata.get(
                    "business_rules",
                    "暂无额外业务规则。",
                ),
                "order_info": request.metadata.get(
                    "order_info",
                    "用户未提供订单信息。",
                ),
            },
        )

    return prompt_service.render_by_scenario(
        scenario=PromptScenario.GENERAL_CHAT,
        version=request.prompt_version or "v1",
        variables={
            "user_question": latest_user_message,
        },
    )


def get_latest_user_message(request: ChatRequest) -> str:
    for message in reversed(request.messages):
        if message.role == MessageRole.USER:
            return message.content

    return request.messages[-1].content


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

## 【重点内容】
这个 ChatService 是项目一的核心整合。

它做了几件事。

第一，拿到最新用户消息。

第二，如果是电商客服场景，走 Tool Calling。

第三，如果不是工具场景，先查 Redis 缓存。

第四，未命中缓存时调用 LLM Provider。

第五，把回答写入 Redis。

第六，把用户消息和 AI 回复写入 PostgreSQL。

第七，返回统一 ChatResponse。

这就是项目整合能力。

---

# 十七、13｜为什么 Tool Calling 暂时不写入 messages
## 【重点内容】
在上面的项目一版本里，Tool Calling 分支暂时没有把消息写入 PostgreSQL。

这是为了保持本章主线清晰。

真实项目应该把 Tool Calling 的用户消息、AI 回复、工具调用记录都保存起来。

比如：

```plain
messages 表保存用户和 assistant 回复
tool_call_logs 表保存工具调用明细
```

本章先让普通 Chat 完整入库。

Tool Calling 入库作为课后任务。

这样项目不会一下子太复杂。

---

# 十八、14｜Chat Router 最终版
打开：

```plain
app/api/v1/chat.py
```

整理成：

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db_session
from app.dependencies.llm import get_llm_provider
from app.dependencies.rate_limit import chat_rate_limit
from app.dependencies.redis import get_redis_client
from app.llm.base import BaseLLMProvider
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.services.chat_service import chat_with_ai
from app.services.chat_stream_service import stream_chat_with_ai


router = APIRouter()


@router.post(
    "/chat",
    response_model=ApiResponse[ChatResponse],
    dependencies=[Depends(chat_rate_limit)],
)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[ChatResponse]:
    request.user_id = current_user.user_id

    result = await chat_with_ai(
        request=request,
        db=db,
        redis=redis,
        llm_provider=llm_provider,
    )

    result.trace_id = f"{result.trace_id}_user_{current_user.user_id}"

    return ApiResponse[ChatResponse](
        data=result
    )


@router.post(
    "/chat/stream",
    dependencies=[Depends(chat_rate_limit)],
)
async def chat_stream(
    request_body: ChatRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
):
    request_body.user_id = current_user.user_id
    request_body.stream = True

    async def event_generator():
        async for event in stream_chat_with_ai(
            request=request_body,
            llm_provider=llm_provider,
            db=db,
            redis=redis,
        ):
            if await request.is_disconnected():
                break

            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

## 【重点内容】
Chat Router 现在有两个核心接口：

```plain
/chat
/chat/stream
```

普通 Chat 返回 ApiResponse。

流式 Chat 返回 StreamingResponse。

这两个接口都复用：

```plain
current_user
db
redis
llm_provider
chat_rate_limit
```

这就是我们第 09 章 Depends 的价值。

接口本身很干净。

复杂业务都放在 Service 里。

---

# 十九、15｜确认 ChatStreamService
打开：

```plain
app/services/chat_stream_service.py
```

项目一版可以保持第 16 章版本，但建议补上 Redis 缓存：

```python
import uuid
from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ErrorCode
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import LLMRequest
from app.redis.cache import cache_chat_response, get_cached_chat_response
from app.schemas.chat import ChatRequest, MessageRole, TokenUsage
from app.services.chat_service import (
    build_llm_request_from_chat_request,
    get_latest_user_message,
    save_chat_messages,
)
from app.utils.sse import format_done_event, format_error_event, format_sse


logger = get_logger(__name__)


async def stream_chat_with_ai(
    request: ChatRequest,
    llm_provider: BaseLLMProvider,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
) -> AsyncGenerator[str, None]:
    latest_user_message = get_latest_user_message(request)

    llm_request: LLMRequest = build_llm_request_from_chat_request(request)
    llm_request.stream = True

    message_id = f"m_{uuid.uuid4().hex[:8]}"
    full_answer = ""
    final_usage = TokenUsage()

    logger.info(
        f"chat_stream_start model={llm_request.model} "
        f"session_id={request.session_id}"
    )

    if redis:
        cached_answer = await get_cached_chat_response(
            redis=redis,
            question=latest_user_message,
        )

        if cached_answer:
            yield format_sse(
                event="start",
                data={
                    "message_id": message_id,
                    "model": llm_request.model,
                    "session_id": request.session_id,
                    "cache_hit": True,
                },
            )

            for part in split_text(cached_answer, size=8):
                yield format_sse(
                    event="message",
                    data={
                        "content": part,
                        "message_id": message_id,
                        "cache_hit": True,
                    },
                )

            yield format_done_event(
                {
                    "message_id": message_id,
                    "finish_reason": "cache_hit",
                    "usage": final_usage.model_dump(),
                }
            )

            return

    yield format_sse(
        event="start",
        data={
            "message_id": message_id,
            "model": llm_request.model,
            "session_id": request.session_id,
            "cache_hit": False,
        },
    )

    try:
        async for chunk in llm_provider.stream_chat(llm_request):
            if chunk.content:
                full_answer += chunk.content

                yield format_sse(
                    event="message",
                    data={
                        "content": chunk.content,
                        "message_id": message_id,
                    },
                )

            if chunk.usage:
                final_usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                )

        if redis and full_answer:
            await cache_chat_response(
                redis=redis,
                question=latest_user_message,
                answer=full_answer,
            )

        if db and request.session_id:
            await save_chat_messages(
                db=db,
                conversation_id=request.session_id,
                user_message=latest_user_message,
                assistant_message=full_answer,
                model=llm_request.model,
                usage=final_usage,
            )

        logger.info(
            f"chat_stream_success model={llm_request.model} "
            f"answer_length={len(full_answer)} "
            f"total_tokens={final_usage.total_tokens}"
        )

        yield format_done_event(
            {
                "message_id": message_id,
                "finish_reason": "stop",
                "usage": final_usage.model_dump(),
            }
        )

    except LLMProviderError as exc:
        logger.exception(
            f"chat_stream_llm_error provider={exc.provider} "
            f"status_code={exc.status_code}"
        )

        yield format_error_event(
            message=exc.message,
            code=int(ErrorCode.LLM_CALL_FAILED),
            detail={
                "provider": exc.provider,
                "status_code": exc.status_code,
            },
        )

    except Exception as exc:
        logger.exception(
            f"chat_stream_unhandled_error error={repr(exc)}"
        )

        yield format_error_event(
            message="流式输出失败",
            code=int(ErrorCode.INTERNAL_ERROR),
        )


def split_text(text: str, size: int = 8) -> list[str]:
    return [
        text[index:index + size]
        for index in range(0, len(text), size)
    ]
```

---

## 【重点内容】
项目一里，流式接口也支持 Redis 缓存了。

如果缓存命中，我们不再调用模型。

而是把缓存答案切成小片段，模拟流式返回。

这样用户仍然看到打字机效果，同时不消耗模型 token。

如果缓存未命中，就调用真实模型流式接口。

最后把完整回答保存到 Redis 和 PostgreSQL。

---

# 二十、16｜Models Router
如果前面还没有整理，可以新建：

```plain
app/api/v1/models.py
```

写入：

```python
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.response import ApiResponse


router = APIRouter()


@router.get("/models", response_model=ApiResponse[list[dict]])
async def list_models() -> ApiResponse[list[dict]]:
    models = []

    for model_name in settings.supported_models.split(","):
        model_name = model_name.strip()

        if not model_name:
            continue

        if model_name.startswith("deepseek"):
            provider = "deepseek"
        elif model_name.startswith("qwen"):
            provider = "qwen"
        elif model_name.startswith("gpt"):
            provider = "openai"
        else:
            provider = "unknown"

        models.append(
            {
                "model": model_name,
                "provider": provider,
                "support_stream": True,
                "support_tools": provider in ["deepseek", "qwen", "openai"],
            }
        )

    return ApiResponse[list[dict]](
        data=models
    )
```

---

## 【重点内容】
模型列表接口给前端用。

前端可以通过：

```plain
/models
```

拿到当前支持的模型。

项目一先从 settings 里读。

真实平台阶段可以放到数据库表：

```plain
llm_models
```

支持后台开关模型、配置价格和权限。

---

# 二十一、17｜注册所有 Router
打开：

```plain
app/api/v1/api.py
```

确认类似：

```python
from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.models import router as models_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.structured_outputs import router as structured_outputs_router
from app.api.v1.tool_calling import router as tool_calling_router


api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(conversations_router, tags=["Conversations"])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(models_router, tags=["Models"])
api_router.include_router(prompts_router, tags=["Prompts"])
api_router.include_router(structured_outputs_router, tags=["Structured Outputs"])
api_router.include_router(tool_calling_router, tags=["Tool Calling"])
```

---

## 【重点内容】
这一章要确认所有 Router 都注册进来了。

很多同学写了接口，但访问 404。

原因通常是：

```plain
写了 router
但没有 include_router
```

所以这里统一检查：

```plain
chat
conversations
models
prompts
tools
structured_outputs
health
```

都注册到 api_router。

---

# 二十二、18｜启动项目
执行：

```bash
uv run uvicorn app.main:app --reload
```

访问：

```plain
http://127.0.0.1:8000/docs
```

确认能看到：

```plain
Health
Conversations
Chat
Models
Prompts
Structured Outputs
Tool Calling
```

---

## 【重点内容】
现在启动项目。

先打开 Swagger 看接口分组。

如果接口分组不完整，先别急着调试业务。

先检查：

```plain
router 文件有没有导入
api.py 有没有 include_router
main.py 有没有 include api_router
prefix 是否是 /api/v1
```

项目整合阶段，很多问题都是路由注册问题。

---

# 二十三、19｜联调第一步：健康检查
```bash
curl "http://127.0.0.1:8000/api/v1/health"
```

预期：

```json
{
  "status": "ok",
  "service": "AI Agent Course API"
}
```

Redis：

```bash
curl "http://127.0.0.1:8000/api/v1/health/redis"
```

预期：

```json
{
  "status": "ok",
  "redis": true
}
```

---

## 【重点内容】
联调一定要按顺序来。

第一步不是直接调 Chat。

第一步先调健康检查。

确认后端能启动。

确认 Redis 能连。

如果这一步不通过，后面的 Chat 一定会出问题。

---

# 二十四、20｜联调第二步：创建会话
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversations" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "title": "AI Agent 学习咨询"
  }'
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_xxxxxxxx",
    "title": "AI Agent 学习咨询",
    "status": "active",
    "created_at": "2026-08-24T10:00:00",
    "updated_at": "2026-08-24T10:00:00"
  },
  "trace_id": null
}
```

记住：

```plain
conversation_id
```

后面 Chat 要用。

---

## 【重点内容】
创建会话后，拿到 conversation_id。

这个 ID 后面作为：

```plain
session_id
```

传给 ChatRequest。

这样消息才能保存到对应会话里。

课程里为了简单，我们让：

```plain
session_id = conversation_id
```

真实项目里也可以统一叫 conversation_id。

---

# 二十五、21｜联调第三步：普通 Chat
把上一步拿到的 `conversation_id` 替换到 `session_id`。

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "session_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "请用三句话解释什么是 AI Agent。"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false,
    "prompt_scenario": "general_chat"
  }'
```

预期：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "AI Agent 是...",
    "model": "deepseek-chat",
    "session_id": "c_xxxxxxxx",
    "message_id": "m_xxxxxxxx",
    "usage": {
      "prompt_tokens": 100,
      "completion_tokens": 80,
      "total_tokens": 180
    },
    "sources": [],
    "trace_id": "trace_xxx_user_u_10001",
    "metadata": {
      "cache_hit": false
    }
  }
}
```

---

## 【重点内容】
现在普通 Chat 已经走完整链路：

```plain
Router
 ↓
ChatService
 ↓
PromptService
 ↓
Redis Cache
 ↓
LLMProvider
 ↓
模型 API
 ↓
PostgreSQL 保存消息
 ↓
返回 ChatResponse
```

这就是项目一的主链路。

---

# 二十六、22｜联调第四步：查询会话消息
```bash
curl "http://127.0.0.1:8000/api/v1/conversations/c_xxxxxxxx/messages" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

预期：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "请用三句话解释什么是 AI Agent。"
      },
      {
        "role": "assistant",
        "content": "AI Agent 是..."
      }
    ]
  }
}
```

---

## 【重点内容】
这一步验证 PostgreSQL 入库是否成功。

如果 Chat 返回成功，但这里查不到消息，要检查：

```plain
ChatRequest 是否传 session_id
conversation_id 是否存在
save_chat_messages 是否执行
db session 是否提交
messages 表是否有数据
```

---

# 二十七、23｜联调第五步：测试 Redis 缓存
再次发送同样问题：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "session_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "请用三句话解释什么是 AI Agent。"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false,
    "prompt_scenario": "general_chat"
  }'
```

如果命中缓存，返回：

```json
{
  "metadata": {
    "cache_hit": true
  }
}
```

---

## 【重点内容】
第二次同样问题，应该命中 Redis。

日志里可以看到：

```plain
chat_response_cache_hit
```

Redis Insight 里可以看到：

```plain
chat:response:xxxxxxxxxxxxxxxx
```

这说明第 12 章的 Redis 缓存已经和项目一整合成功。

---

# 二十八、24｜联调第六步：Streaming Chat
```bash
curl -N -X POST "http://127.0.0.1:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "session_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "请用三句话解释为什么 AI Chat 需要流式输出。"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": true,
    "prompt_scenario": "general_chat"
  }'
```

预期输出：

```plain
event: start
data: {"message_id": "m_xxxxxxxx", "model": "deepseek-chat", "session_id": "c_xxxxxxxx", "cache_hit": false}

event: message
data: {"content": "AI", "message_id": "m_xxxxxxxx"}

event: message
data: {"content": " Chat", "message_id": "m_xxxxxxxx"}

event: done
data: {"message_id": "m_xxxxxxxx", "finish_reason": "stop", "usage": {...}}
```

---

## 【重点内容】
这里要注意 curl 的 `-N`。

如果不加，curl 可能会缓冲输出。

你就看不到实时效果。

看到一段一段的 `event: message`，说明 Streaming 接口正常。

---

# 二十九、25｜联调第七步：电商客服 Tool Calling
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "session_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "帮我查一下订单 10001 到哪了？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.3,
    "stream": false,
    "prompt_scenario": "ecommerce_customer_service",
    "metadata": {
      "business_rules": "不能编造物流信息；没有订单号时必须先引导用户提供订单号。",
      "order_info": "用户提供了订单号 10001。"
    }
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "您好，您的订单 10001 已发货，物流公司是顺丰，物流单号是 SF10001，最新物流节点为：包裹已到达成都高新区中转站。",
    "metadata": {
      "tool_calls": [
        {
          "name": "query_order",
          "arguments": {
            "order_id": "10001"
          }
        }
      ],
      "tool_results": [
        {
          "tool_name": "query_order",
          "result": {
            "success": true
          }
        }
      ]
    }
  }
}
```

---

## 【重点内容】
这一步是项目一的亮点。

因为它不是普通聊天。

而是：

```plain
模型判断需要查订单
 ↓
模型生成 query_order 工具调用
 ↓
后端执行工具
 ↓
模型根据真实订单结果回复
```

这就是电商客服 Agent 的雏形。

面试或者项目展示时，这个点非常重要。

---

# 三十、26｜创建完整联调脚本
创建：

```plain
scripts/test_ai_chat_flow.py
```

写入：

```python
import asyncio
import json

import httpx


BASE_URL = "http://127.0.0.1:8000/api/v1"

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "dev-api-key-123",
    "x-user-id": "u_10001",
    "x-username": "dawei",
}


async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        conversation_id = await create_conversation(client)

        await chat_once(
            client=client,
            conversation_id=conversation_id,
            question="请用三句话解释什么是 AI Agent。",
        )

        await chat_once(
            client=client,
            conversation_id=conversation_id,
            question="请用三句话解释什么是 AI Agent。",
        )

        await chat_with_tools(
            client=client,
            conversation_id=conversation_id,
        )

        await get_messages(
            client=client,
            conversation_id=conversation_id,
        )


async def create_conversation(client: httpx.AsyncClient) -> str:
    response = await client.post(
        f"{BASE_URL}/conversations",
        headers=HEADERS,
        json={
            "title": "项目一完整联调"
        },
    )

    data = response.json()
    print("create_conversation:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    return data["data"]["conversation_id"]


async def chat_once(
    client: httpx.AsyncClient,
    conversation_id: str,
    question: str,
):
    response = await client.post(
        f"{BASE_URL}/chat",
        headers=HEADERS,
        json={
            "session_id": conversation_id,
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ],
            "model": "deepseek-chat",
            "temperature": 0.7,
            "stream": False,
            "prompt_scenario": "general_chat",
        },
    )

    data = response.json()
    print("chat:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def chat_with_tools(
    client: httpx.AsyncClient,
    conversation_id: str,
):
    response = await client.post(
        f"{BASE_URL}/chat",
        headers=HEADERS,
        json={
            "session_id": conversation_id,
            "messages": [
                {
                    "role": "user",
                    "content": "帮我查一下订单 10001 到哪了？",
                }
            ],
            "model": "deepseek-chat",
            "temperature": 0.3,
            "stream": False,
            "prompt_scenario": "ecommerce_customer_service",
            "metadata": {
                "business_rules": "不能编造物流信息；没有订单号时必须先引导用户提供订单号。",
                "order_info": "用户提供了订单号 10001。",
            },
        },
    )

    data = response.json()
    print("chat_with_tools:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def get_messages(
    client: httpx.AsyncClient,
    conversation_id: str,
):
    response = await client.get(
        f"{BASE_URL}/conversations/{conversation_id}/messages",
        headers=HEADERS,
    )

    data = response.json()
    print("messages:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_ai_chat_flow.py
```

---

## 【重点内容】
这个脚本用于项目一完整联调。

它会按顺序执行：

```plain
创建会话
普通 Chat
再次 Chat 测缓存
电商客服 Tool Calling
查询消息历史
```

项目整合阶段，一定要有这种完整链路测试脚本。

不要只靠 Swagger 点接口。

---

# 三十一、27｜前端 Demo：AI Chat 页面
创建：

```plain
frontend-demo/ai-chat-demo.html
```

写入：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>AI Chat Demo</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 24px;
      max-width: 960px;
      margin: 0 auto;
      background: #f7f7f7;
    }

    h1 {
      margin-bottom: 12px;
    }

    .toolbar {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    input,
    select,
    textarea {
      padding: 8px;
      box-sizing: border-box;
    }

    textarea {
      width: 100%;
      height: 90px;
      margin-top: 12px;
    }

    button {
      padding: 8px 14px;
      cursor: pointer;
    }

    #chat {
      background: #fff;
      border: 1px solid #ddd;
      min-height: 360px;
      padding: 16px;
      margin-top: 16px;
      white-space: pre-wrap;
    }

    .message {
      margin-bottom: 16px;
      padding: 12px;
      border-radius: 8px;
    }

    .user {
      background: #e8f0ff;
    }

    .assistant {
      background: #f1f1f1;
    }

    .meta {
      color: #666;
      font-size: 12px;
      margin-top: 4px;
    }
  </style>
</head>
<body>
  <h1>AI Chat Demo</h1>

  <div class="toolbar">
    <input id="conversationTitle" value="前端 AI Agent 学习咨询" />
    <button onclick="createConversation()">创建会话</button>

    <select id="model">
      <option value="deepseek-chat">deepseek-chat</option>
      <option value="qwen-plus">qwen-plus</option>
    </select>

    <select id="scenario">
      <option value="general_chat">通用聊天</option>
      <option value="ecommerce_customer_service">电商客服</option>
    </select>

    <button onclick="sendNormal()">普通发送</button>
    <button onclick="sendStream()">流式发送</button>
  </div>

  <div>
    <strong>当前会话：</strong>
    <span id="conversationId">未创建</span>
  </div>

  <textarea id="question">请用三句话解释什么是 AI Agent。</textarea>

  <div id="chat"></div>

  <script>
    const BASE_URL = 'http://127.0.0.1:8000/api/v1';

    const headers = {
      'Content-Type': 'application/json',
      'x-api-key': 'dev-api-key-123',
      'x-user-id': 'u_10001',
      'x-username': 'dawei'
    };

    let conversationId = '';

    async function createConversation() {
      const title = document.getElementById('conversationTitle').value;

      const response = await fetch(`${BASE_URL}/conversations`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ title })
      });

      const data = await response.json();

      conversationId = data.data.conversation_id;
      document.getElementById('conversationId').textContent = conversationId;

      appendMessage('assistant', `会话已创建：${conversationId}`);
    }

    async function sendNormal() {
      ensureConversation();

      const question = document.getElementById('question').value;
      const model = document.getElementById('model').value;
      const scenario = document.getElementById('scenario').value;

      appendMessage('user', question);

      const response = await fetch(`${BASE_URL}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(buildPayload(question, model, scenario, false))
      });

      const data = await response.json();

      if (data.code !== 0) {
        appendMessage('assistant', `请求失败：${data.message}`);
        return;
      }

      appendMessage(
        'assistant',
        data.data.answer,
        JSON.stringify(data.data.metadata || {}, null, 2)
      );
    }

    async function sendStream() {
      ensureConversation();

      const question = document.getElementById('question').value;
      const model = document.getElementById('model').value;
      const scenario = document.getElementById('scenario').value;

      appendMessage('user', question);

      const assistantEl = appendMessage('assistant', '');

      const response = await fetch(`${BASE_URL}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(buildPayload(question, model, scenario, true))
      });

      if (!response.ok) {
        assistantEl.textContent = `请求失败：${response.status}`;
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const rawEvent of events) {
          handleSSEEvent(rawEvent, assistantEl);
        }
      }
    }

    function buildPayload(question, model, scenario, stream) {
      const metadata = {};

      if (scenario === 'ecommerce_customer_service') {
        metadata.business_rules = '不能编造物流信息；没有订单号时必须先引导用户提供订单号。';
        metadata.order_info = '如果用户提供订单号，则可以查询订单。';
      }

      return {
        session_id: conversationId,
        messages: [
          {
            role: 'user',
            content: question
          }
        ],
        model,
        temperature: scenario === 'ecommerce_customer_service' ? 0.3 : 0.7,
        stream,
        prompt_scenario: scenario,
        prompt_version: 'v1',
        metadata
      };
    }

    function handleSSEEvent(rawEvent, assistantEl) {
      const lines = rawEvent.split('\n');

      let eventName = 'message';
      let dataText = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventName = line.replace('event:', '').trim();
        }

        if (line.startsWith('data:')) {
          dataText += line.replace('data:', '').trim();
        }
      }

      if (!dataText) {
        return;
      }

      const data = JSON.parse(dataText);

      if (eventName === 'message') {
        assistantEl.textContent += data.content || '';
      }

      if (eventName === 'done') {
        console.log('done:', data);
      }

      if (eventName === 'error') {
        assistantEl.textContent += `\n\n[错误] ${data.message}`;
      }
    }

    function appendMessage(role, content, meta) {
      const chat = document.getElementById('chat');

      const el = document.createElement('div');
      el.className = `message ${role}`;
      el.textContent = `${role === 'user' ? '用户' : 'AI'}：\n${content}`;

      if (meta) {
        const metaEl = document.createElement('div');
        metaEl.className = 'meta';
        metaEl.textContent = meta;
        el.appendChild(metaEl);
      }

      chat.appendChild(el);

      return el;
    }

    function ensureConversation() {
      if (!conversationId) {
        throw new Error('请先创建会话');
      }
    }
  </script>
</body>
</html>
```

---

## 【重点内容】
这个前端 Demo 很简单，但能演示完整能力。

它支持：

```plain
创建会话
普通发送
流式发送
模型选择
场景选择
电商客服工具调用
```

这对课程演示非常有帮助。

学员不只是看到接口返回 JSON。

还能看到一个简单聊天页面。

---

# 三十二、28｜前端 Demo 运行方式
进入项目根目录：

```bash
cd ai-agent-course
```

启动一个静态服务器：

```bash
python -m http.server 5173
```

访问：

```plain
http://127.0.0.1:5173/frontend-demo/ai-chat-demo.html
```

如果遇到跨域问题，确认 FastAPI 已经配置 CORS。

---

## 【重点内容】
不要直接双击 HTML 文件。

推荐用：

```bash
python -m http.server 5173
```

这样浏览器 origin 是：

```plain
http://127.0.0.1:5173
```

后端 CORS 配置更清晰。

---

# 三十三、29｜项目一演示脚本
## 【课堂演示顺序】
```plain
1. 启动 PostgreSQL / Redis
2. 启动 FastAPI
3. 打开 Swagger
4. 调 health
5. 调 health/redis
6. 创建会话
7. 普通 Chat
8. 查询会话消息
9. 再次普通 Chat，看 Redis 缓存
10. 流式 Chat，看打字机效果
11. 电商客服场景，问订单 10001
12. 查看 metadata.tool_calls
13. 打开前端 Demo
14. 完成前端联调
```

---

## 【重点内容】
项目演示一定要有节奏。

不要一上来就打开代码讲细节。

先让学员看到最终效果。

然后再回头解释链路。

这样更容易理解：

```plain
为什么要有 PostgreSQL
为什么要有 Redis
为什么要有 Provider
为什么要有 Prompt
为什么要有 Tool Calling
```

---

# 三十四、30｜项目一技术亮点总结
## 【实操】
```plain
项目一：AI Chat 聊天系统

技术亮点：
1. FastAPI 分层架构
2. Pydantic 请求响应模型
3. PostgreSQL 会话消息持久化
4. SQLAlchemy AsyncSession
5. Redis 缓存和限流
6. 统一 LLM Provider
7. Prompt 工程化
8. Streaming SSE 流式输出
9. Tool Calling 电商客服工具调用
10. 统一异常处理和日志
```

---

## 【重点内容】
这个项目不是一个简单 Demo。

它已经具备了真实 AI 应用的很多核心点。

你可以在简历或面试里这样描述：

我做过一个基于 FastAPI 的 AI Chat 系统，底层接入统一 LLM Provider，支持 DeepSeek / Qwen / OpenAI 等模型切换；系统支持普通问答和 SSE 流式输出，使用 PostgreSQL 持久化会话和消息，使用 Redis 做响应缓存、限流和最近消息缓存；同时在电商客服场景中接入 Tool Calling，实现订单查询工具调用，避免模型编造订单状态。

这个说法就比：

```plain
我做了一个 AI 聊天机器人
```

高级很多。

---

# 三十五、31｜面试讲法一：整体架构怎么讲
## 【回答话术】
如果面试官问：

你这个 AI Chat 项目整体架构怎么设计的？

可以这样回答：

```plain
我这个项目采用 FastAPI 做后端接口层，整体分成 Router、Service、Repository、Provider、Tool 几层。

Router 负责接收请求和依赖注入，比如当前用户、数据库会话、Redis Client、LLM Provider。

Service 负责业务编排，比如普通 Chat、流式 Chat、会话管理、Tool Calling。

Repository 负责 PostgreSQL 数据库操作，主要存会话和消息。

LLM Provider 负责屏蔽不同模型厂商差异，比如 DeepSeek、Qwen、OpenAI，业务层只依赖统一的 LLMRequest 和 LLMResponse。

Redis 用来做响应缓存、限流和最近消息缓存。

另外，我还做了 Prompt 工程化，把通用聊天、电商客服、RAG、Agent 的 Prompt 做成模板和版本管理。

在电商客服场景里，我接入了 Tool Calling，让模型判断是否需要调用 query_order 工具，后端执行工具后再让模型基于真实数据回复用户。
```

---

# 三十六、32｜面试讲法二：为什么要设计 LLM Provider
## 【回答话术】
```plain
我没有把模型调用直接写死在 ChatService 里，而是抽了一层 LLM Provider。

原因是不同模型厂商的 base_url、鉴权方式、响应结构、usage 字段、tool_calls 解析都有差异。

如果直接写在业务代码里，后面切模型会很痛苦。

所以我定义了 BaseLLMProvider，统一 chat 和 stream_chat 两个方法。

DeepSeekProvider、QwenProvider、OpenAIProvider 分别适配不同厂商。

业务层只关心 LLMRequest 和 LLMResponse。

这样后续新增 Kimi、Claude 或本地 Ollama，也只需要新增 Provider，不需要大改 ChatService。
```

---

# 三十七、33｜面试讲法三：Redis 在项目里怎么用
## 【回答话术】
```plain
Redis 在这个 AI Chat 项目里主要用了三类场景。

第一是响应缓存。对于一些重复问题，比如“什么是 AI Agent”，第一次调用模型后把回答缓存到 Redis，第二次相同问题直接返回，降低模型成本和接口耗时。

第二是限流。因为大模型接口有成本，所以我用 Redis 的 INCR + EXPIRE 做了固定窗口限流，比如每个用户一分钟最多请求 20 次 Chat 接口。

第三是最近消息缓存。会话消息长期存在 PostgreSQL，但最近几轮上下文可以放 Redis，减少频繁查库。

这些数据都有 TTL，因为 Redis 主要保存高频、短生命周期的数据。
```

---

# 三十八、34｜面试讲法四：Streaming 怎么实现
## 【回答话术】
```plain
流式输出我用的是 SSE。

后端基于 FastAPI 的 StreamingResponse 实现，Service 层是一个 async generator。

模型侧调用 LLMProvider.stream_chat，拿到每个 chunk 后，后端把它包装成 SSE 事件，比如 start、message、done、error，然后 yield 给前端。

前端使用 fetch + ReadableStream 接收 POST 流式响应，解析 event 和 data，再把 message 事件里的 content 追加到页面上。

流结束后，后端会把所有 chunk 拼成完整回答，然后一次性保存到 PostgreSQL，避免每个 chunk 都写数据库。
```

FastAPI 官方文档说明 `StreamingResponse` 会把生成器产生的 chunk 原样返回，而不会转换成普通 JSON；这正好适合本章用 SSE 事件向前端持续推送模型输出。

---

# 三十九、35｜面试讲法五：Tool Calling 怎么实现
## 【回答话术】
```plain
Tool Calling 我是按两阶段实现的。

第一阶段，把用户问题、系统 Prompt 和 tools schema 一起发给模型，让模型判断是否需要调用工具。如果用户问订单状态，模型会返回 tool_calls，比如 query_order 和 order_id 参数。

第二阶段，后端解析 tool_calls，通过 ToolExecutor 校验参数并执行真实工具函数。工具返回结果后，我把 tool result 追加回 messages，再次调用模型，让模型基于工具结果生成最终客服回复。

这里我强调一点，模型不会直接执行工具。模型只是生成工具名和参数，真正执行、权限校验、参数校验、错误处理都在后端。
```

OpenAI Chat Completions 支持 `tools` 与 `tool_choice`，`tool_choice` 可以控制模型不调用工具、自动选择工具或必须调用工具；本项目里的电商客服场景就是把订单查询工具通过 tools schema 暴露给模型，再由后端执行真实工具。

---

# 四十、36｜项目一常见错误一：Chat 成功但消息没入库
## 现象
```plain
POST /chat 返回成功
但 GET /conversations/{id}/messages 查不到消息
```

## 排查
```plain
1. ChatRequest 是否传了 session_id
2. session_id 是否是真实 conversation_id
3. db 是否注入成功
4. save_chat_messages 是否执行
5. messages 表是否已经创建
6. 数据库连接是否指向正确 DB
```

---

# 四十一、37｜项目一常见错误二：接口 404
## 现象
```plain
访问 /api/v1/chat 返回 404
```

## 排查
```plain
1. chat.py 里是否定义 router
2. api.py 是否 include_router(chat_router)
3. main.py 是否 include_router(api_router, prefix=settings.api_v1_prefix)
4. .env 里的 API_V1_PREFIX 是否是 /api/v1
```

---

# 四十二、38｜项目一常见错误三：Redis 连接失败
## 现象
```plain
ConnectionError: Error connecting to localhost:6379
```

## 排查
```bash
docker ps
docker logs ai_agent_redis
```

检查 `.env`：

```plain
REDIS_URL=redis://:redis123@localhost:6379/0
```

---

# 四十三、39｜项目一常见错误四：流式接口没有实时输出
## 现象
```plain
后端在生成
但是前端等到最后才显示
```

## 排查
```plain
1. curl 是否加了 -N
2. StreamingResponse media_type 是否是 text/event-stream
3. SSE 是否有 \n\n
4. Nginx 是否开启了 buffering
5. 是否被 GZip 中间件缓冲
6. 前端是否正确解析 ReadableStream
```

---

# 四十四、40｜项目一常见错误五：Tool Calling 没调用工具
## 现象
```plain
用户问订单，但模型直接回答，没有返回 tool_calls
```

## 排查
```plain
1. prompt_scenario 是否传 ecommerce_customer_service
2. ToolCallingService 是否被调用
3. tools 是否传给模型
4. tool_choice 是否是 auto 或 required
5. 工具 description 是否足够清楚
6. 用户问题里是否包含订单号
7. 模型是否支持 Tool Calling
```

---

# 四十五、41｜项目一常见错误六：API Key 错误
## 现象
```plain
401 Unauthorized
```

## 排查
```plain
1. DEEPSEEK_API_KEY 是否配置
2. DEFAULT_MODEL 是否是 deepseek-chat
3. DEEPSEEK_BASE_URL 是否是 https://api.deepseek.com
4. key 是否有额度
5. 服务重启后配置是否生效
```

---

# 四十六、42｜项目一常见错误七：AsyncSession 被复用
## 【重点内容】
数据库会话不要做成全局变量。

不要这样：

```python
global_session = AsyncSessionLocal()
```

正确方式是通过 Depends 每个请求获取一个 session：

```python
db: AsyncSession = Depends(get_db_session)
```

SQLAlchemy 文档明确提醒，`AsyncSession` 是可变、有状态对象，不能在多个并发任务中共享同一个实例。

---

# 四十七、43｜项目一完整复习
这一章我们完成了：

```plain
1. 明确项目一目标：AI Chat 聊天系统
2. 梳理项目一整体架构
3. 梳理项目一接口清单
4. 确认 .env 配置
5. 确认 Docker Compose
6. 确认 Conversation / Message 模型
7. 确认 Conversation Schema
8. 确认 Chat Schema
9. 实现 ConversationRepository
10. 实现 ConversationService
11. 实现 Conversations Router
12. 整合 ChatService
13. 整合 PromptService
14. 整合 Redis 响应缓存
15. 整合 LLMProvider
16. 整合 PostgreSQL 消息保存
17. 整合 ToolCallingService
18. 整合 Chat Router
19. 整合 Streaming Chat
20. 整合 Models Router
21. 注册所有 Router
22. 完成健康检查联调
23. 完成创建会话联调
24. 完成普通 Chat 联调
25. 完成消息历史查询联调
26. 完成 Redis 缓存联调
27. 完成 Streaming Chat 联调
28. 完成电商客服 Tool Calling 联调
29. 编写完整联调脚本
30. 编写前端 HTML Demo
31. 总结项目一面试讲法
32. 总结项目一常见错误
```

---

# 四十八、44｜项目一可以写到简历里的描述
## 【简历项目描述】
```plain
项目名称：企业级 AI Chat 聊天系统

项目描述：
基于 FastAPI + PostgreSQL + Redis + 大模型 API 构建企业级 AI Chat 聊天系统，支持会话管理、消息持久化、普通问答、SSE 流式输出、Prompt 场景化管理、Redis 响应缓存、用户级限流，以及电商客服场景下的 Tool Calling 工具调用能力。系统通过统一 LLM Provider 屏蔽 DeepSeek、Qwen、OpenAI 等模型差异，业务层只依赖统一的 LLMRequest / LLMResponse。

技术栈：
FastAPI、Pydantic、SQLAlchemy AsyncSession、PostgreSQL、Redis、SSE、LLM Provider、Prompt Engineering、Tool Calling、Docker Compose。

核心职责：
1. 设计 Router / Service / Repository / Provider 分层架构，提升代码可维护性。
2. 设计 Conversation / Message 数据模型，实现会话和消息持久化。
3. 封装统一 LLM Provider，支持多模型切换。
4. 实现 Prompt 模板化和场景化，支持通用聊天与电商客服。
5. 实现 SSE Streaming 流式输出，提升 AI Chat 交互体验。
6. 使用 Redis 实现响应缓存、最近消息缓存和接口限流。
7. 在电商客服场景接入 Tool Calling，实现订单查询工具调用，避免模型编造订单状态。
8. 记录 token usage，为后续成本统计和模型调用分析打基础。
```

---

# 四十九、45｜项目一技术难点怎么讲
## 难点一：模型调用层解耦
```plain
难点：
不同模型厂商接口格式、base_url、鉴权方式、响应结构、usage 字段、stream chunk 格式不一致。

解决：
抽象 BaseLLMProvider，统一 chat 和 stream_chat 接口。DeepSeek、Qwen、OpenAI 分别实现 Provider，业务层只依赖统一 LLMRequest / LLMResponse。
```

---

## 难点二：流式输出和消息保存
```plain
难点：
流式输出时模型是一段一段返回，不能每个 chunk 都写数据库，否则写入次数多、消息结构混乱。

解决：
后端使用 async generator 接收 chunk 并通过 SSE 返回前端，同时在内存中拼接 full_answer。流结束后一次性保存完整 assistant message。
```

---

## 难点三：缓存和成本控制
```plain
难点：
大模型调用有成本，相同问题重复请求会造成浪费。

解决：
使用 Redis 缓存 LLM 响应，通过问题 hash 生成缓存 key，并设置 TTL。普通 Chat 和 Streaming Chat 都支持缓存命中。
```

---

## 难点四：Tool Calling 安全
```plain
难点：
模型生成的工具调用参数不可信，不能直接执行。

解决：
后端实现 ToolRegistry 和 ToolExecutor，工具参数必须经过 Pydantic Schema 校验，工具是否存在、是否启用、是否需要确认都由后端控制。
```

---

# 五十、46｜课后任务一：Tool Calling 消息入库
要求：

```plain
1. 电商客服 Tool Calling 分支也保存 user message
2. 保存最终 assistant message
3. metadata 里的 tool_calls 暂时不用入库
4. 后面单独设计 tool_call_logs 表
```

---

# 五十一、47｜课后任务二：会话标题自动生成
要求：

```plain
1. 用户第一次发送消息时，如果 conversation.title 为空或默认值
2. 调用 LLM 生成 10～20 字标题
3. 保存到 conversations.title
4. 增加接口测试
```

参考 Prompt：

```plain
请根据用户第一条消息生成一个简短会话标题，不超过 20 个字，只输出标题。
```

---

# 五十二、48｜课后任务三：历史上下文接入 Chat
当前 ChatRequest 只使用本次传入 messages。

要求升级：

```plain
1. 如果传了 session_id
2. 从 PostgreSQL 查询最近 10 条历史消息
3. 拼接到 LLMRequest messages 中
4. 再追加当前用户问题
5. 注意不要重复保存历史消息
```

---

# 五十三、49｜课后任务四：增加会话归档接口
要求：

```plain
1. 新增 DELETE /conversations/{conversation_id}
2. 不物理删除数据
3. status 改成 archived
4. 列表接口不返回 archived 会话
```

---

# 五十四、50｜课后任务五：前端增加会话列表
要求：

```plain
1. 页面左侧展示会话列表
2. 点击会话加载历史消息
3. 新建会话后刷新列表
4. 普通 Chat 和流式 Chat 都写入当前会话
```

---

# 五十五、51｜课后任务六：画出项目一完整架构图
画出：

```plain
AI Chat 项目完整链路
```

必须包含：

```plain
Frontend
FastAPI Router
Dependency
ChatService
PromptService
Redis
LLMProvider
ToolCallingService
ToolExecutor
PostgreSQL
StreamingResponse
```

参考链路：

```plain
用户发送消息
 ↓
前端请求 /api/v1/chat
 ↓
Middleware 生成 trace_id
 ↓
认证 / 限流
 ↓
Chat Router
 ↓
ChatService
 ↓
PromptService 渲染 Prompt
 ↓
Redis 查询缓存
 ↓
LLMProvider 调用模型
 ↓
可选 ToolCallingService
 ↓
PostgreSQL 保存消息
 ↓
返回 ChatResponse
```

---

# 五十六、52｜本章总结
## 【重点内容】
好了，到这里，第 19 章我们就讲完了。

这一章是第一阶段非常重要的项目整合章。

前面我们讲的 FastAPI、PostgreSQL、Redis、LLM Provider、Prompt、Streaming、Structured Output、Tool Calling，在这一章全部组合到了一个项目里。

我们最终完成了：

```plain
AI Chat 聊天系统
```

它支持：

```plain
会话创建
会话列表
消息历史
普通 Chat
Streaming Chat
Prompt 场景
Redis 缓存
PostgreSQL 持久化
Token Usage
电商客服 Tool Calling
前端 Demo 联调
```

到这里，大家已经不是只会写一个简单 AI 接口了。

而是已经具备了一个企业级 AI Chat 后端项目的基本架构能力。

这个项目后面还可以继续扩展成：

```plain
企业知识库
客服 Agent
RAG 问答
Agent 平台
多智能体协作系统
```

所以项目一是整个课程里非常关键的第一个里程碑。

---
