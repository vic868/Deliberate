---

# 一、本章定位
前面我们已经完成了两层非常重要的能力：

```plain
第 14 章｜统一 LLM Provider 架构
第 15 章｜Prompt Engineering 工程化实战
```

现在项目已经具备：

```plain
BaseLLMProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
LLMProviderFactory
PromptTemplate
PromptRegistry
PromptService
ChatService 接入真实 LLM Provider
```

但是目前 Chat 接口还是非流式的。

也就是说，用户发起请求以后，需要等待模型完整生成完，后端才一次性返回：

```json
{
  "answer": "完整回答内容..."
}
```

这种方式能跑，但是体验不好。

因为如果模型回答很长，用户要等好几秒，页面没有任何反馈。

真实 AI Chat 产品一般都是：

```plain
模型边生成
前端边展示
```

也就是我们常说的：

```plain
打字机效果
```

这一章我们就要实现这个能力：

# Streaming 流式输出
本章目标：

**把 **`**/api/v1/chat**`** 的一次性返回，升级出一个 **`**/api/v1/chat/stream**`** 流式接口，让前端像 ChatGPT 一样边收边展示模型输出。**

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Streaming 是什么
2. 非流式和流式有什么区别
3. SSE 是什么
4. FastAPI StreamingResponse 怎么用
5. LLMProvider.stream_chat() 怎么接入业务
6. 如何设计 /chat/stream 接口
7. 后端如何 yield SSE 数据
8. 前端如何接收流式数据
9. POST 请求为什么不能直接用 EventSource
10. fetch 如何接收 SSE 流
11. 如何边输出边拼接完整回答
12. 如何在流结束后保存完整 AI 回复
13. 如何保存用户消息和 AI 回复
14. 如何处理流式 usage
15. 如何处理流式错误
16. 如何处理用户中途断开连接
17. 如何设计 done / error / message 事件
18. 如何处理 Redis 缓存和流式输出的关系
19. 如何在 Swagger 之外测试流式接口
20. Streaming 在 AI Chat / RAG / Agent 中的使用场景
```

---

# 三、本章最终项目结构
本章结束后，项目会新增和修改：

```plain
ai-agent-course/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py
│   │       └── ...
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── chat_stream_service.py
│   │   └── ...
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── sse.py
│   │
│   ├── llm/
│   │   ├── base.py
│   │   ├── schemas.py
│   │   └── providers/
│   │       ├── openai_compatible.py
│   │       ├── deepseek.py
│   │       └── qwen.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_chat_stream.py
│   └── test_sse_format.py
│
└── frontend-demo/
    └── stream-demo.html
```

本章重点新增：

```plain
app/utils/sse.py
app/services/chat_stream_service.py
scripts/test_chat_stream.py
frontend-demo/stream-demo.html
```

---

# 四、01｜本章开场
## 【重要内容】
大家好，欢迎来到第 16 章。

这一章我们讲 Streaming 流式输出。

前面我们已经能调用真实大模型了。

但是现在我们的接口是这样的：

```plain
用户提问
 ↓
后端调用模型
 ↓
等待模型完整生成
 ↓
一次性返回完整回答
```

如果回答很短，这没问题。

但如果回答比较长，比如：

```plain
生成一份 1000 字报告
总结一篇文档
执行一个 RAG 问答
让 Agent 分步骤分析问题
```

用户就要等很久。

页面上一直没反应。

体验会很差。

所以真实 AI 产品一般都是流式输出。

也就是：

```plain
模型生成一点
后端返回一点
前端展示一点
```

用户能立刻看到内容开始出来。

这就是 ChatGPT 那种打字机效果。

这一章我们会把这个能力接到我们的 FastAPI 项目里。

---

# 五、02｜非流式 vs 流式
## 【实操】
### 非流式
```plain
请求开始
  ↓
模型生成完整回答
  ↓
后端一次性返回
  ↓
前端一次性展示
```

### 流式
```plain
请求开始
  ↓
模型生成 chunk 1 → 后端返回 → 前端展示
模型生成 chunk 2 → 后端返回 → 前端展示
模型生成 chunk 3 → 后端返回 → 前端展示
  ↓
最终完成
```

---

## 【重要内容】
非流式就是一次性返回。

优点是代码简单。

缺点是用户等待时间长。

流式输出的优点是体验好。

用户不用等完整答案生成完，就能看到模型开始回答。

这对 AI Chat 产品非常重要。

尤其是大模型回答通常不是毫秒级返回。

它可能需要：

```plain
1 秒
3 秒
10 秒
甚至更久
```

如果没有流式输出，用户会感觉系统卡住了。

所以这一章我们必须把它补上。

---

# 六、03｜SSE 是什么
## 【实操】
```plain
SSE = Server-Sent Events

服务端持续向客户端发送事件
客户端持续接收
适合大模型流式输出
```

---

## 【SSE 数据格式】
```plain
event: message
data: {"content": "AI"}

event: message
data: {"content": " Agent"}

event: done
data: {"finish_reason": "stop"}
```

或者最简单：

```plain
data: {"content": "AI"}

data: {"content": " Agent"}

data: [DONE]
```

---

## 【重要内容】
SSE 是 Server-Sent Events。

简单理解：

**服务端通过一个 HTTP 连接，不断向客户端推送文本事件。**

大模型流式输出经常用 SSE。

比如 DeepSeek 文档里就说明，`stream=true` 时会以 SSE 形式发送消息增量，并以 `data: [DONE]` 结束。

FastAPI 侧，我们会使用：

```python
StreamingResponse
```

返回这些流式数据。

FastAPI 官方文档说明，`StreamingResponse` 会把生成器产生的 chunk 原样发给客户端，不会再尝试把它转换成 JSON。

---

# 七、04｜为什么选择 SSE，而不是 WebSocket
## 【实操】
| 对比项 | SSE | WebSocket |
| --- | --- | --- |
| 通信方向 | 服务端 → 客户端 | 双向 |
| 协议复杂度 | 简单 | 较复杂 |
| 适合场景 | 模型流式输出、通知 | 实时协作、双向聊天、游戏 |
| 前端接收 | EventSource / fetch stream | WebSocket API |
| HTTP 兼容性 | 好 | 需要升级协议 |
| 本章选择 | 使用 SSE | 后续可扩展 |


---

## 【重要内容】
很多同学会问，为什么不用 WebSocket？

因为 AI Chat 的流式回答，本质上大部分是：

```plain
客户端发一个问题
服务端持续返回回答
```

这是服务端向客户端持续推送。

SSE 就很适合。

WebSocket 更适合真正双向实时通信，比如：

```plain
多人协作
实时游戏
实时音视频信令
双向消息不断交互
```

本章先用 SSE。

它简单、够用、好调试。

后面如果做更复杂的实时 Agent 控制台，再考虑 WebSocket。

---

# 八、05｜流式接口的整体链路
## 【实操】
```plain
POST /api/v1/chat/stream
    ↓
Chat Router
    ↓
chat_stream_service.stream_chat_with_ai()
    ↓
PromptService 渲染 Prompt
    ↓
LLMProvider.stream_chat()
    ↓
DeepSeek / Qwen 流式 API
    ↓
chunk by chunk
    ↓
StreamingResponse
    ↓
前端 fetch 逐段接收
```

---

## 【重要内容】
这一章的主链路是这样的。

前端请求：

```plain
/api/v1/chat/stream
```

后端进入 Chat Router。

Router 调用：

```python
stream_chat_with_ai()
```

这个方法会调用：

```python
llm_provider.stream_chat()
```

然后模型返回一个一个 chunk。

后端把每个 chunk 包装成 SSE 格式，然后：

```python
yield
```

给 FastAPI 的 StreamingResponse。

前端收到一点，展示一点。

这就是完整链路。

---

# 九、06｜先确认 Provider 已经支持 stream_chat
第 14 章我们已经在：

```plain
app/llm/base.py
```

定义了：

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def stream_chat(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        pass
```

并且在：

```plain
app/llm/providers/openai_compatible.py
```

实现了：

```python
async def stream_chat(
    self,
    request: LLMRequest,
) -> AsyncGenerator[LLMStreamChunk, None]:
    ...
```

---

## 【重要内容】
这一章不是从零开始。

我们第 14 章已经在 Provider 层做好了流式接口。

现在要做的是：

```plain
把 Provider 的 stream_chat
接到 FastAPI StreamingResponse
```

这体现了前面架构设计的价值。

如果第 14 章没有封装 Provider，这一章就会到处写模型厂商的流式解析代码。

现在我们只需要复用统一接口。

---

# 十、07｜创建 utils/sse.py
## 【屏幕操作】
执行：

```bash
mkdir -p app/utils
touch app/utils/__init__.py
touch app/utils/sse.py
```

Windows PowerShell：

```powershell
mkdir app\utils
New-Item app\utils\__init__.py
New-Item app\utils\sse.py
```

打开：

```plain
app/utils/sse.py
```

写入：

```python
import json
from typing import Any


def format_sse(
    data: Any,
    event: str | None = None,
    event_id: str | None = None,
    retry: int | None = None,
) -> str:
    lines = []

    if event_id is not None:
        lines.append(f"id: {event_id}")

    if event is not None:
        lines.append(f"event: {event}")

    if retry is not None:
        lines.append(f"retry: {retry}")

    if isinstance(data, str):
        payload = data
    else:
        payload = json.dumps(data, ensure_ascii=False)

    for line in payload.splitlines():
        lines.append(f"data: {line}")

    return "\n".join(lines) + "\n\n"


def format_done_event(data: dict | None = None) -> str:
    return format_sse(
        event="done",
        data=data or {
            "finish_reason": "stop"
        },
    )


def format_error_event(
    message: str,
    code: int = 50000,
    detail: dict | None = None,
) -> str:
    return format_sse(
        event="error",
        data={
            "code": code,
            "message": message,
            "detail": detail or {},
        },
    )
```

---

## 【重要内容】
这里我们封装 SSE 格式化函数。

SSE 的格式不是随便拼字符串。

常见格式是：

```plain
event: message
data: {...}
```

注意最后有两个换行。

也就是：

```plain
\n\n
```

如果少了这个，前端可能收不到完整事件。

我们封装：

```python
format_sse()
```

后面所有流式输出都走它。

这样不会到处手写 SSE 格式。

---

# 十一、08｜测试 SSE 格式化
创建：

```plain
scripts/test_sse_format.py
```

写入：

```python
from app.utils.sse import format_done_event, format_error_event, format_sse


def main():
    print("message event:")
    print(
        format_sse(
            event="message",
            data={
                "content": "AI Agent"
            },
        )
    )

    print("done event:")
    print(format_done_event())

    print("error event:")
    print(
        format_error_event(
            message="模型调用失败",
            code=50002,
        )
    )


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_sse_format.py
```

输出类似：

```plain
event: message
data: {"content": "AI Agent"}

event: done
data: {"finish_reason": "stop"}

event: error
data: {"code": 50002, "message": "模型调用失败", "detail": {}}
```

---

## 【重要内容】
这个脚本先验证 SSE 格式。

不要一开始就接大模型。

先把最基础的格式跑通。

后面出现前端收不到流的问题时，可以先检查：

```plain
是不是 SSE 格式不对
是不是少了两个换行
是不是 media_type 不对
```

---

# 十二、09｜创建 chat_stream_service.py
创建：

```plain
app/services/chat_stream_service.py
```

写入完整代码：

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
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import ChatRequest, MessageRole, TokenUsage
from app.services.chat_service import (
    build_llm_request_from_chat_request,
    get_latest_user_message,
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
        f"message_count={len(llm_request.messages)}"
    )

    yield format_sse(
        event="start",
        data={
            "message_id": message_id,
            "model": llm_request.model,
            "session_id": request.session_id,
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

        if db and request.session_id:
            await save_stream_messages(
                db=db,
                session_id=request.session_id,
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


async def save_stream_messages(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    assistant_message: str,
    model: str,
    usage: TokenUsage,
):
    await conversation_repository.add_message(
        db=db,
        conversation_id=session_id,
        role=MessageRole.USER.value,
        content=user_message,
        model=model,
        prompt_tokens=usage.prompt_tokens,
    )

    await conversation_repository.add_message(
        db=db,
        conversation_id=session_id,
        role=MessageRole.ASSISTANT.value,
        content=assistant_message,
        model=model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        total_tokens=usage.total_tokens,
    )
```

---

## 【重要内容】
这个文件是本章核心。

我们定义了：

```python
stream_chat_with_ai()
```

它是一个 async generator。

里面不是 return，而是不断：

```python
yield
```

每次模型返回一个 chunk，我们就 yield 一个 SSE 事件。

比如：

```python
yield format_sse(event="message", data={"content": chunk.content})
```

前端就能马上收到。

同时我们还做了几件事：

```plain
1. start 事件：告诉前端开始生成
2. message 事件：返回每段内容
3. done 事件：告诉前端结束
4. error 事件：告诉前端错误
5. full_answer：拼接完整回答
6. final_usage：保存 token 用量
7. save_stream_messages：流结束后保存消息
```

这就是流式输出的核心逻辑。

---

# 十三、10｜为什么流结束后再保存 AI 回复
## 【重要内容】
流式输出时，模型不是一次性返回完整内容。

所以我们需要边输出边拼接：

```python
full_answer += chunk.content
```

只有等模型完整输出结束后，才能把完整回答保存到数据库。

如果每个 chunk 都写数据库，会有问题：

```plain
写入次数太多
数据库压力大
一条 AI 回复会被拆成很多条
后续历史消息不好查询
```

所以推荐：

```plain
流式过程中只推给前端
后端内存里拼接完整回答
流结束后一次性保存完整 assistant message
```

这就是本章的设计。

---

# 十四、11｜流式 usage 怎么处理
## 【重要内容】
流式 usage 是一个坑。

非流式时，usage 通常在完整 response 里。

但是流式时，不同厂商处理不一样。

有些模型最后一个 chunk 会带 usage。

有些模型流式 chunk 里 usage 一直是 null。

Qwen 文档里就提到，流式模式可以通过 `stream_options={"include_usage": True}` 让最后一个 chunk 返回 usage。

所以我们的代码里这样处理：

```python
if chunk.usage:
    final_usage = TokenUsage(...)
```

也就是说：

```plain
有 usage 就记录
没有 usage 就默认 0
```

后面如果要更准确，可以做 token 本地估算，或者在模型 Provider 层补齐。

这一章先把流式链路跑通。

---

# 十五、12｜改造 Chat Router：新增 /chat/stream
打开：

```plain
app/api/v1/chat.py
```

增加导入：

```python
from fastapi import Request
from fastapi.responses import StreamingResponse

from app.services.chat_stream_service import stream_chat_with_ai
```

新增接口：

```python
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

## 【重要内容】
现在我们新增了：

```plain
/api/v1/chat/stream
```

这个接口返回的不是：

```python
ApiResponse
```

而是：

```python
StreamingResponse
```

注意这里不要写：

```python
response_model=ApiResponse[...]
```

因为流式响应不是普通 JSON。

它的 media type 是：

```plain
text/event-stream
```

这告诉浏览器：

这是一个 SSE 流。

另外我们设置了几个 header：

```plain
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

其中 `X-Accel-Buffering: no` 常用于避免某些反向代理缓冲响应，方便流式内容尽快到达前端。

---

# 十六、13｜为什么要判断 request.is_disconnected()
## 【重要内容】
流式接口可能会遇到一种情况：

```plain
用户关闭页面
用户取消请求
网络断开
```

这时候后端没必要继续生成。

所以我们在 event_generator 里判断：

```python
if await request.is_disconnected():
    break
```

Starlette 的 Request 支持在长轮询或流式响应这类场景中判断客户端是否断开连接。

这样可以减少不必要的模型调用和服务器压力。

---

# 十七、14｜完整 chat.py 关键片段
最终 `app/api/v1/chat.py` 里的关键结构应该类似：

```python
from fastapi import APIRouter, Depends, Path, Query, Request
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

# 十八、15｜测试流式接口：curl
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

使用 curl 测试：

```bash
curl -N -X POST "http://127.0.0.1:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "请用三句话解释什么是 Streaming 流式输出。"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": true
  }'
```

注意这里使用：

```bash
-N
```

表示关闭 curl 的输出缓冲。

如果不加，可能看不到实时输出效果。

---

## 【预期输出】
```plain
event: start
data: {"message_id": "m_xxxxxxxx", "model": "deepseek-chat", "session_id": null}

event: message
data: {"content": "Streaming", "message_id": "m_xxxxxxxx"}

event: message
data: {"content": " 流式输出", "message_id": "m_xxxxxxxx"}

event: message
data: {"content": " 是指...", "message_id": "m_xxxxxxxx"}

event: done
data: {"message_id": "m_xxxxxxxx", "finish_reason": "stop", "usage": {...}}
```

---

## 【重要内容】
测试流式接口，不建议只用 Swagger。

Swagger 对 SSE 体验不友好。

最简单是用：

```bash
curl -N
```

如果你看到一段一段的 `event: message` 输出，说明后端流式接口已经生效了。

---

# 十九、16｜创建 Python 流式测试脚本
创建：

```plain
scripts/test_chat_stream.py
```

写入：

```python
import asyncio

import httpx


async def main():
    url = "http://127.0.0.1:8000/api/v1/chat/stream"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": "dev-api-key-123",
        "x-user-id": "u_10001",
        "x-username": "dawei",
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": "请用三句话解释为什么 AI Chat 需要流式输出。",
            }
        ],
        "model": "deepseek-chat",
        "temperature": 0.7,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
        ) as response:
            print("status_code:", response.status_code)

            async for line in response.aiter_lines():
                if line:
                    print(line)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_chat_stream.py
```

---

## 【重要内容】
这个脚本用 httpx 模拟前端接收流。

核心是：

```python
async with client.stream(...)
```

然后：

```python
async for line in response.aiter_lines():
```

逐行读取 SSE。

这和我们第 13 章读取大模型流式 API 的方式非常像。

只不过现在读取的是我们自己的 FastAPI 流式接口。

---

# 二十、17｜前端为什么不能直接用 EventSource 发 POST
## 【重要内容】
浏览器原生的 EventSource 很方便。

但是它主要用于 GET 请求。

比如：

```javascript
const es = new EventSource('/api/v1/chat/stream')
```

但是我们的 Chat 接口需要 POST。

因为要传：

```plain
messages
model
temperature
metadata
```

这些放 GET query 里不合适。

所以前端更推荐用：

```javascript
fetch
+
ReadableStream
```

来接收 POST 流式响应。

也就是说：

```plain
GET SSE：可以用 EventSource

POST SSE：推荐用 fetch 读取 stream
```

---

# 二十一、18｜前端 fetch 接收流式输出
创建：

```plain
frontend-demo/stream-demo.html
```

如果没有目录：

```bash
mkdir -p frontend-demo
touch frontend-demo/stream-demo.html
```

写入：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>AI Chat Stream Demo</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      padding: 24px;
      max-width: 800px;
      margin: 0 auto;
    }

    textarea {
      width: 100%;
      height: 100px;
      padding: 12px;
      box-sizing: border-box;
    }

    button {
      margin-top: 12px;
      padding: 8px 16px;
      cursor: pointer;
    }

    #answer {
      margin-top: 24px;
      padding: 16px;
      border: 1px solid #ddd;
      min-height: 120px;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <h1>AI Chat Stream Demo</h1>

  <textarea id="question">请用三句话解释什么是 Streaming 流式输出。</textarea>
  <br />
  <button onclick="sendMessage()">发送</button>

  <div id="answer"></div>

  <script>
    async function sendMessage() {
      const question = document.getElementById('question').value;
      const answerEl = document.getElementById('answer');

      answerEl.textContent = '';

      const response = await fetch('http://127.0.0.1:8000/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': 'dev-api-key-123',
          'x-user-id': 'u_10001',
          'x-username': 'dawei'
        },
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content: question
            }
          ],
          model: 'deepseek-chat',
          temperature: 0.7,
          stream: true
        })
      });

      if (!response.ok) {
        answerEl.textContent = '请求失败：' + response.status;
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
          handleSSEEvent(rawEvent, answerEl);
        }
      }
    }

    function handleSSEEvent(rawEvent, answerEl) {
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
        answerEl.textContent += data.content || '';
      }

      if (eventName === 'done') {
        console.log('done:', data);
      }

      if (eventName === 'error') {
        answerEl.textContent += '\n\n[错误] ' + data.message;
      }
    }
  </script>
</body>
</html>
```

---

## 【重要内容】
这个前端 Demo 很简单。

重点是：

```javascript
const reader = response.body.getReader();
```

然后不断：

```javascript
await reader.read()
```

读取服务端推来的数据。

由于 SSE 事件之间用：

```plain
\n\n
```

分隔，所以我们用：

```javascript
buffer.split('\n\n')
```

拆事件。

然后解析：

```plain
event:
data:
```

最后把 `message` 事件里的 content 追加到页面上。

这就是前端打字机效果的最小实现。

---

# 二十二、19｜CORS 注意事项
如果前端直接打开 HTML 文件请求 FastAPI，可能会遇到 CORS 问题。

如果之前还没配置 CORS，可以在：

```plain
app/main.py
```

里增加：

```python
from fastapi.middleware.cors import CORSMiddleware
```

在创建 app 后增加：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 【重要内容】
开发阶段，前端和后端经常不是同一个地址。

比如：

```plain
前端：http://localhost:5173
后端：http://127.0.0.1:8000
```

这时候浏览器会有跨域限制。

所以要配置 CORS。

如果你直接双击打开 HTML 文件，origin 可能是：

```plain
null
```

所以开发 Demo 里也加了 `"null"`。

生产环境不要这么放开。

生产环境应该只允许自己的前端域名。

---

# 二十三、20｜流式输出和 Redis 缓存的关系
## 【重要内容】
第 12 章我们做过 LLM 响应缓存。

非流式接口可以这样：

```plain
先查 Redis
命中直接返回完整 answer
未命中调用模型
调用完成后写缓存
```

流式接口要稍微注意。

如果缓存命中，可以有两种处理方式。

第一种：

```plain
直接把完整缓存答案一次性返回成一个 message 事件
```

简单，但是没有打字机效果。

第二种：

```plain
把缓存答案切成小片段，模拟流式返回
```

体验更接近真实流式。

本章先不强行把缓存接进 stream。

因为我们重点是打通真实模型流式链路。

课后任务会让大家补上缓存命中流式返回。

---

# 二十四、21｜给流式接口增加缓存命中逻辑
如果希望流式接口也支持 Redis 缓存，可以在：

```plain
app/services/chat_stream_service.py
```

增加导入：

```python
from app.redis.cache import cache_chat_response, get_cached_chat_response
```

在调用模型前增加：

```python
if redis:
    cached_answer = await get_cached_chat_response(
        redis=redis,
        question=latest_user_message,
    )

    if cached_answer:
        logger.info("chat_stream_cache_hit")

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
```

再增加一个工具函数：

```python
def split_text(text: str, size: int = 8) -> list[str]:
    return [
        text[index:index + size]
        for index in range(0, len(text), size)
    ]
```

模型成功生成后，在 done 前写缓存：

```python
if redis and full_answer:
    await cache_chat_response(
        redis=redis,
        question=latest_user_message,
        answer=full_answer,
    )
```

---

## 【重要内容】
这个逻辑可以让流式接口也支持缓存。

如果 Redis 命中，我们不再调用模型。

而是把缓存答案切成小段，模拟流式返回。

这样既节省成本，又保留打字机体验。

真实项目里可以根据业务决定是否这么做。

---

# 二十五、22｜流式接口错误处理策略
## 【重要内容】
普通接口出错，可以直接返回：

```json
{
  "code": 50002,
  "message": "大模型调用失败"
}
```

但是流式接口不一样。

因为响应可能已经开始了。

一旦 StreamingResponse 已经开始发送，HTTP 状态码通常已经是 200。

中途出错时，不能再改成 500。

所以我们通过 SSE 发送 error 事件：

```plain
event: error
data: {"code": 50002, "message": "大模型调用失败"}
```

前端收到 error 事件后，在页面上提示用户。

这就是流式接口常见的错误处理方式。

---

# 二十六、23｜前端处理 error 事件
在前端 Demo 里已经有：

```javascript
if (eventName === 'error') {
  answerEl.textContent += '\n\n[错误] ' + data.message;
}
```

你可以根据需要改成：

```javascript
if (eventName === 'error') {
  showToast(data.message);
  stopLoading();
}
```

---

## 【重要内容】
前端一定要处理 error 事件。

不要只处理 message。

否则后端流式过程中出错，用户页面会卡住。

推荐前端维护几个状态：

```plain
loading
streaming
done
error
```

收到 start：进入 streaming。

收到 message：追加内容。

收到 done：结束 loading。

收到 error：结束 loading，并显示错误。

---

# 二十七、24｜流式输出和数据库保存的边界
## 【重要内容】
这里有一个真实项目一定会遇到的问题：

用户中途关闭页面，后端还要不要保存 AI 回复？

有几种策略。

第一种：

```plain
只保存完整生成成功的回答
```

简单干净。

第二种：

```plain
保存部分回答，并标记 interrupted
```

更完整，但表结构要支持状态。

第三种：

```plain
不保存 assistant 回答，只保存用户消息
```

适合对话历史必须完整但不想保存半截回复的系统。

本章我们采用第一种：

```plain
正常流结束后，保存完整 user + assistant
```

中断场景先不保存半截回复。

后面 Agent Run 和 Message 状态设计时再继续升级。

---

# 二十八、25｜流式消息表设计升级思路
后面可以给 `messages` 表增加：

```plain
status
```

比如：

```plain
generating
completed
failed
interrupted
```

也可以增加：

```plain
finish_reason
error_message
```

未来迁移示例：

```python
status: Mapped[str] = mapped_column(
    String(50),
    nullable=False,
    default="completed",
)

finish_reason: Mapped[str | None] = mapped_column(
    String(50),
    nullable=True,
)

error_message: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
)
```

---

## 【重要内容】
这部分先作为架构思考。

本章不强行改数据库。

因为我们已经有 Alembic 补充小节，后面可以自己加 migration。

真实 AI Chat 系统里，消息状态很有用。

比如：

```plain
生成中
生成完成
生成失败
用户取消
```

这些状态可以帮助前端恢复会话，也可以帮助排查问题。

---

# 二十九、26｜流式接口和 Prompt 的关系
## 【重要内容】
流式输出不改变 Prompt 逻辑。

也就是说，非流式和流式都应该复用：

```python
build_llm_request_from_chat_request()
```

这个函数里面已经接入了：

```plain
PromptService
PromptRegistry
PromptScenario
PromptVersion
```

所以无论是：

```plain
/chat
```

还是：

```plain
/chat/stream
```

都应该走同一套 Prompt 构建逻辑。

不要流式接口自己再写一套 Prompt。

否则两个接口回答风格会不一致。

---

# 三十、27｜流式接口和限流的关系
## 【重要内容】
流式接口一定要加限流。

因为一次流式请求可能比普通请求更耗资源。

它会占用：

```plain
HTTP 连接
模型请求
服务端协程
前端连接
```

所以我们继续复用第 12 章的：

```python
chat_rate_limit
```

在路由上写：

```python
dependencies=[Depends(chat_rate_limit)]
```

这样普通 Chat 和 Stream Chat 都会被限流保护。

---

# 三十一、28｜流式接口和 Nginx 代理注意事项
## 【重要内容】
如果后面你部署到 Nginx 后面，流式输出可能会遇到一个问题：

```plain
后端明明 yield 了
但是前端还是等到全部完成才收到
```

这通常是代理缓冲导致的。

可以考虑在 Nginx 配置里关闭 buffering：

```nginx
location /api/ {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
}
```

后端响应头里我们也加了：

```plain
X-Accel-Buffering: no
```

这有助于提示 Nginx 不要缓冲响应。

部署章节会再详细讲。

---

# 三十二、29｜流式接口和 GZip 注意事项
## 【重要内容】
流式 SSE 不建议被压缩中间件缓冲。

有些 GZip 中间件会为了压缩而缓存响应内容。

这样会影响流式实时性。

Starlette 文档里也提到 GZipMiddleware 默认会排除 `text/event-stream` 这类内容类型，避免流式 SSE 被压缩缓冲影响。

所以如果项目里加了 GZip，要注意：

```plain
不要压缩 text/event-stream
```

否则前端可能不能实时收到 chunk。

---

# 三十三、30｜Swagger 为什么不适合测试流式接口
## 【重要内容】
Swagger 非常适合测试普通 JSON 接口。

但是它不适合体验 SSE 流式输出。

因为它通常会等响应结束再展示，或者展示效果不直观。

测试流式接口，推荐：

```plain
curl -N
Python httpx stream
前端 fetch demo
Postman / Apifox 支持流式的版本
```

课程演示建议用：

```plain
curl -N
+
前端 HTML demo
```

这样学员最容易看懂。

---

# 三十四、31｜流式事件格式设计
## 【推荐事件】
| event | 说明 | data |
| --- | --- | --- |
| `start` | 开始生成 | message_id、model、session_id |
| `message` | 模型增量内容 | content |
| `done` | 生成结束 | finish_reason、usage |
| `error` | 生成失败 | code、message、detail |


---

## 【重要内容】
不要只返回纯文本。

比如：

```plain
AI Agent 是...
```

这样简单，但扩展性差。

推荐用结构化事件：

```plain
event: message
data: {"content": "AI Agent 是"}
```

这样后面可以扩展：

```plain
reasoning
tool_call
source
usage
done
error
```

这对 RAG 和 Agent 很重要。

---

# 三十五、32｜为后续 RAG 流式输出预留 source 事件
后面 RAG 流式接口可以这样设计：

```plain
event: source
data: {"document_id": "doc_001", "title": "企业手册", "score": 0.89}

event: message
data: {"content": "根据企业手册..."}

event: done
data: {"usage": {...}}
```

---

## 【重要内容】
RAG 流式输出不仅要输出回答。

还可能要先输出引用来源。

比如前端可以先展示：

```plain
已检索到 3 篇文档
```

然后再展示模型回答。

所以事件设计要有扩展性。

本章只实现 Chat 的 start/message/done/error。

后面 RAG 阶段继续扩展 source 事件。

---

# 三十六、33｜为后续 Agent 流式输出预留 step 事件
Agent 流式输出可能是：

```plain
event: step
data: {"step": "planning", "status": "running"}

event: tool_call
data: {"tool_name": "query_order", "arguments": {...}}

event: tool_result
data: {"tool_name": "query_order", "result": {...}}

event: message
data: {"content": "您的订单已经发货..."}

event: done
data: {"status": "completed"}
```

---

## 【重要内容】
Agent 的流式输出更复杂。

它不只是模型文本。

它还包括：

```plain
规划步骤
工具调用
工具结果
中间状态
最终回答
```

所以本章设计 SSE 的时候，要提前考虑扩展。

不要写死成只有 content。

---

# 三十七、34｜把流式输出封装成统一响应协议
## 【实操】
```plain
SSE Event Protocol

start:
  message_id
  session_id
  model

message:
  content

source:
  document_id
  title
  score

step:
  name
  status

tool_call:
  tool_name
  arguments

tool_result:
  tool_name
  result

done:
  finish_reason
  usage

error:
  code
  message
```

---

## 【重要内容】
这个协议后面会贯穿 Chat、RAG、Agent。

现在我们先实现四个：

```plain
start
message
done
error
```

后面继续加：

```plain
source
step
tool_call
tool_result
```

这样整个课程的流式协议是可演进的。

---

# 三十八、35｜常见错误一：少了两个换行
错误：

```python
yield "data: hello\n"
```

正确：

```python
yield "data: hello\n\n"
```

---

## 【重要内容】
SSE 每个事件结束必须有空行。

也就是两个换行。

如果少了，前端可能一直等，不触发事件解析。

所以我们才封装：

```python
format_sse()
```

避免到处手写格式。

---

# 三十九、36｜常见错误二：media_type 写错
错误：

```python
StreamingResponse(generator())
```

没有指定：

```plain
text/event-stream
```

正确：

```python
StreamingResponse(
    generator(),
    media_type="text/event-stream",
)
```

---

# 四十、37｜常见错误三：Swagger 看不到实时效果
原因：

```plain
Swagger 不适合体验 SSE
```

解决：

```plain
curl -N
前端 fetch demo
Python httpx stream
```

---

# 四十一、38｜常见错误四：代理缓冲
现象：

```plain
后端日志显示一直在 yield
前端却等到最后才收到
```

可能原因：

```plain
Nginx / 网关 / 浏览器 / 客户端工具缓冲
```

解决方向：

```plain
curl 使用 -N
响应头加 X-Accel-Buffering: no
Nginx proxy_buffering off
避免压缩 text/event-stream
```

---

# 四十二、39｜常见错误五：流式中途异常前端没提示
错误做法：

```python
except Exception:
    logger.exception("error")
```

但没有 yield error 事件。

正确：

```python
except Exception:
    yield format_error_event(
        message="流式输出失败",
        code=50000,
    )
```

---

# 四十三、40｜常见错误六：每个 chunk 都写数据库
不推荐：

```plain
chunk1 写数据库
chunk2 写数据库
chunk3 写数据库
```

推荐：

```plain
内存拼接 full_answer
流结束后一次性写入完整 assistant message
```

---

# 四十四、41｜常见错误七：忘记处理用户断开
如果用户关闭页面，后端还继续跑模型，会浪费资源。

推荐在 Router 的 event_generator 中判断：

```python
if await request.is_disconnected():
    break
```

---

# 四十五、42｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| Streaming | AI Chat 打字机效果 |
| SSE | 服务端持续推送模型增量 |
| StreamingResponse | FastAPI 流式响应 |
| `text/event-stream` | SSE 响应类型 |
| `yield` | 后端逐段输出 |
| `LLMProvider.stream_chat()` | 统一模型流式调用 |
| `LLMStreamChunk` | 模型 chunk 统一结构 |
| `format_sse()` | 统一 SSE 事件格式 |
| `start`<br/> 事件 | 前端进入生成状态 |
| `message`<br/> 事件 | 前端追加模型内容 |
| `done`<br/> 事件 | 前端结束 loading |
| `error`<br/> 事件 | 前端展示错误 |
| `full_answer`<br/> 拼接 | 保存完整 AI 回复 |
| `request.is_disconnected()` | 处理用户断开 |
| `curl -N` | 流式接口测试 |
| fetch reader | 前端 POST 流式接收 |
| `X-Accel-Buffering` | 部署时减少代理缓冲 |
| RAG source 事件 | 流式返回引用来源 |
| Agent step 事件 | 流式展示 Agent 执行过程 |


---

# 四十六、43｜本章完整复习
这一章我们完成了：

```plain
1. 理解非流式和流式区别
2. 理解 SSE 是什么
3. 理解为什么本章选择 SSE
4. 理解 FastAPI StreamingResponse
5. 创建 app/utils/sse.py
6. 封装 format_sse
7. 封装 done / error 事件
8. 创建 scripts/test_sse_format.py
9. 创建 chat_stream_service.py
10. 调用 LLMProvider.stream_chat()
11. 边接收 chunk 边 yield SSE
12. 拼接 full_answer
13. 处理流式 usage
14. 流结束后保存完整 user / assistant 消息
15. 新增 /api/v1/chat/stream 接口
16. 使用 StreamingResponse 返回 text/event-stream
17. 使用 curl -N 测试流式输出
18. 使用 Python httpx 测试流式输出
19. 编写前端 fetch stream demo
20. 理解 EventSource 和 POST 的关系
21. 理解流式错误处理
22. 理解用户断开处理
23. 理解代理缓冲和 GZip 注意事项
24. 为 RAG / Agent 流式事件预留扩展
```

现在我们的 AI Chat 已经从：

```plain
一次性返回完整回答
```

升级成：

```plain
边生成边返回
```

这一步非常关键。

因为这就是现代 AI Chat 产品的基础体验。

---

# 四十七、44｜课后任务一：给流式接口增加 Redis 缓存命中
要求：

```plain
1. 在 stream_chat_with_ai 中先查 Redis 缓存
2. 如果命中，把缓存答案切成小段
3. 用 message 事件逐段返回
4. done 事件里标记 finish_reason=cache_hit
5. 如果未命中，正常调用模型
6. 模型生成完成后写入 Redis
```

参考：

```python
for part in split_text(cached_answer, size=8):
    yield format_sse(
        event="message",
        data={
            "content": part,
            "cache_hit": True,
        },
    )
```

---

# 四十八、45｜课后任务二：增加 thinking 事件
要求：

```plain
1. 在流式开始时先发送 thinking 事件
2. 内容为：正在理解你的问题...
3. 前端收到 thinking 后展示灰色提示
4. message 事件开始后隐藏 thinking
```

示例：

```python
yield format_sse(
    event="thinking",
    data={
        "content": "正在理解你的问题..."
    },
)
```

---

# 四十九、46｜课后任务三：前端增加停止生成按钮
要求：

```plain
1. 使用 AbortController
2. 点击停止按钮后 abort 请求
3. 前端状态变成 stopped
4. 后端通过 request.is_disconnected 停止输出
```

前端参考：

```javascript
const controller = new AbortController();

fetch(url, {
  method: 'POST',
  signal: controller.signal,
  ...
});

function stopGenerate() {
  controller.abort();
}
```

---

# 五十、47｜课后任务四：把流式消息状态写入数据库
要求：

```plain
1. 给 messages 表增加 status 字段
2. 支持 completed / failed / interrupted
3. 使用 Alembic 生成迁移
4. 正常结束保存 completed
5. 异常时保存 failed
```

---

# 五十一、48｜课后任务五：设计 RAG 流式事件
要求设计下面事件：

```plain
source
message
done
error
```

source 事件示例：

```plain
event: source
data: {"document_id": "doc_001", "title": "员工手册", "score": 0.92}
```

并画出 RAG 流式链路：

```plain
用户问题
 ↓
检索知识库
 ↓
先返回 source 事件
 ↓
调用 LLMProvider.stream_chat
 ↓
返回 message 事件
 ↓
done
```

---

# 五十二、49｜课后任务六：画出 Chat Streaming 完整链路
画出：

```plain
POST /api/v1/chat/stream
```

完整链路：

```plain
HTTP Request
 ↓
Middleware trace_id
 ↓
verify_api_key
 ↓
chat_rate_limit
 ↓
get_current_user
 ↓
get_db_session
 ↓
get_redis_client
 ↓
get_llm_provider
 ↓
Chat Router
 ↓
StreamingResponse
 ↓
event_generator
 ↓
ChatStreamService
 ↓
PromptService
 ↓
LLMProvider.stream_chat()
 ↓
模型 SSE chunk
 ↓
format_sse(message)
 ↓
前端 fetch reader
 ↓
页面逐字展示
 ↓
done
 ↓
保存完整消息
```

---

# 五十三、50｜本章总结
## 【重要内容】
好了，到这里，第 16 章我们就讲完了。

这一章我们完成了 AI Chat 产品体验里非常关键的一步：

```plain
Streaming 流式输出
```

前面我们的接口是：

```plain
等模型完整生成
再一次性返回
```

现在升级成：

```plain
模型生成一点
后端返回一点
前端展示一点
```

这就是打字机效果。

这一章我们实现了：

```plain
SSE 格式封装
StreamingResponse
/chat/stream 接口
LLMProvider.stream_chat 接入
前端 fetch stream 接收
流式错误事件
done 事件
用户断开处理
流结束后保存完整回答
```

现在我们的项目已经具备真实 AI Chat 产品的核心体验。
