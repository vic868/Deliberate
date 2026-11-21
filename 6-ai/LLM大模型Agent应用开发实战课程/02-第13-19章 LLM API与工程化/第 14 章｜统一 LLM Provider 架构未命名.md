---

# 一、本章定位
上一章我们讲了：

```plain
第 13 章｜大模型 API 原理
```

重点理解了：

```plain
API Key
Base URL
Endpoint
model
messages
role
temperature
max_tokens
stream
SSE
usage
timeout
retry
```

我们也写了几个脚本：

```plain
scripts/llm_openai_responses_demo.py
scripts/llm_openai_compatible_chat_demo.py
scripts/llm_qwen_compatible_demo.py
scripts/llm_stream_demo.py
scripts/token_usage_demo.py
```

这些脚本证明我们可以直接请求大模型 API。

但是现在有一个新问题：

**如果业务代码里到处直接调用模型 API，项目会很快失控。**

比如 ChatService 里直接写：

```python
url = "https://api.deepseek.com/chat/completions"
headers = {
    "Authorization": f"Bearer {settings.deepseek_api_key}"
}
```

RAGService 里又直接写：

```python
url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
```

AgentService 里又写 OpenAI 的接口。

这样后面会很难维护。

所以这一章我们要做一件非常关键的工程化封装：

# 统一 LLM Provider 架构
也就是把不同模型厂商统一抽象成：

```plain
BaseLLMProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
LLMProviderFactory
```

业务层以后不再直接关心模型厂商。

业务层只写：

```python
response = await llm_provider.chat(request)
```

具体是 DeepSeek、Qwen 还是 OpenAI，由 Provider 内部处理。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 为什么不能在业务代码里直接调用模型 API
2. Provider 架构解决什么问题
3. BaseLLMProvider 抽象类怎么设计
4. LLMRequest / LLMResponse 怎么设计
5. LLMMessage / LLMUsage 怎么复用
6. 非流式 chat 接口怎么统一
7. 流式 stream_chat 接口怎么统一
8. OpenAI-compatible Provider 怎么封装
9. DeepSeekProvider 怎么实现
10. QwenProvider 怎么实现
11. OpenAIProvider 怎么处理 Responses API 差异
12. ProviderFactory 怎么根据 provider / model 创建实例
13. 如何统一解析 choices.message.content
14. 如何统一解析 usage
15. 如何统一处理 HTTP 错误
16. 如何统一处理 timeout
17. 如何把 Provider 接入 Depends
18. 如何把 ChatService 从模拟回答改成真实 LLM 调用
19. 如何在 Redis 缓存和 PostgreSQL 消息持久化之间集成 LLMProvider
20. 如何为后面的 Streaming / Tool Calling / LangChain 做准备
```

---

# 三、本章最终项目结构
本章结束后，项目结构会升级成：

```plain
ai-agent-course/
├── app/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── base.py
│   │   ├── errors.py
│   │   ├── http_client.py
│   │   ├── factory.py
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── openai_compatible.py
│   │       ├── deepseek.py
│   │       ├── qwen.py
│   │       └── openai.py
│   │
│   ├── dependencies/
│   │   ├── llm.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   └── ...
│   │
│   └── ...
│
├── scripts/
│   ├── test_llm_factory.py
│   ├── test_llm_deepseek_provider.py
│   ├── test_llm_qwen_provider.py
│   └── test_llm_stream_provider.py
│
├── .env
└── .env.example
```

本章重点新增：

```plain
app/llm/base.py
app/llm/errors.py
app/llm/http_client.py
app/llm/factory.py
app/llm/providers/
app/dependencies/llm.py
```

---

# 四、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 14 章。

这一章我们开始做大模型调用层的工程化封装。

上一章我们已经知道，大模型 API 本质上就是：

```plain
HTTP 请求
+
JSON 请求体
+
JSON 响应体
```

但是实际项目里，不能在业务代码里到处写 HTTP 请求。

比如 ChatService 直接调 DeepSeek。

RAGService 直接调 Qwen。

AgentService 直接调 OpenAI。

这样会带来很多问题。

第一，模型切换困难。

第二，错误处理重复。

第三，usage 解析重复。

第四，stream 解析重复。

第五，API Key 和 base_url 到处散落。

第六，后面接 LangChain / LangGraph 时不好复用。

所以我们要封装一个统一 LLM Provider 架构。

这也是企业级 AI 后端非常核心的一层。

从这一章开始，我们的项目会从：

```plain
脚本里调用大模型
```

升级成：

```plain
业务服务正式通过统一 LLM Provider 调用大模型
```

---

# 五、02｜为什么不能在业务代码里直接调模型
## 【反面代码】
```python
async def chat_with_ai(request: ChatRequest):
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": request.messages[-1].content,
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=payload)

    data = response.json()

    return data["choices"][0]["message"]["content"]
```

---

## 【重点内容】
这段代码看起来能跑。

但是它有很多问题。

第一个问题：

```plain
DeepSeek 写死了
```

如果后面要换成 Qwen，就要改 ChatService。

第二个问题：

```plain
响应解析写死了
```

不同模型厂商的响应结构可能有差异。

第三个问题：

```plain
错误处理写死了
```

超时、限流、API Key 错误，每个地方都要处理一遍。

第四个问题：

```plain
usage 解析写死了
```

有些模型非流式返回 usage，有些流式最后一个 chunk 才返回 usage。

第五个问题：

```plain
无法统一做日志、重试、降级、fallback
```

所以正确做法是：

```plain
业务层
不要直接关心模型厂商

业务层
只依赖统一 Provider 接口
```

---

# 六、03｜Provider 架构是什么
## 【实操】
```plain
ChatService
    ↓
BaseLLMProvider
    ↓
DeepSeekProvider / QwenProvider / OpenAIProvider
    ↓
不同模型服务商 API
```

---

## 【重点内容】
Provider 架构的核心思想是：

**把不同模型厂商的差异封装起来，对业务层暴露统一接口。**

比如业务层只写：

```python
llm_response = await llm_provider.chat(llm_request)
```

业务层不关心：

```plain
base_url 是什么
api_key 从哪来
endpoint 是 /responses 还是 /chat/completions
usage 字段叫什么
stream chunk 怎么解析
错误码怎么处理
```

这些都由具体 Provider 负责。

这样我们的业务层就很干净。

后面要新增 Kimi、Claude、Ollama，也不需要重写 ChatService。

只需要新增对应 Provider。

---

# 七、04｜Provider 架构和前端适配器模式对比
## 【重点内容】
如果你是前端开发，可以把 Provider 理解成适配器模式。

比如你做过支付：

```plain
支付宝支付
微信支付
Stripe 支付
PayPal 支付
```

业务层不应该直接写支付宝 SDK。

而是抽象成：

```typescript
interface PaymentProvider {
  pay(order): Promise<PayResult>
}
```

然后分别实现：

```plain
AlipayProvider
WechatPayProvider
StripeProvider
```

现在大模型也是一样。

我们抽象：

```python
BaseLLMProvider
```

然后实现：

```plain
DeepSeekProvider
QwenProvider
OpenAIProvider
```

业务层只依赖抽象，不依赖具体厂商。

这就是架构设计里的解耦。

---

# 八、05｜本章 Provider 设计图
## 【实操】
```plain
app/llm/
├── schemas.py
│   ├── LLMMessage
│   ├── LLMRequest
│   ├── LLMResponse
│   └── LLMUsage
│
├── base.py
│   └── BaseLLMProvider
│
├── providers/
│   ├── openai_compatible.py
│   │   └── OpenAICompatibleProvider
│   ├── deepseek.py
│   │   └── DeepSeekProvider
│   ├── qwen.py
│   │   └── QwenProvider
│   └── openai.py
│       └── OpenAIProvider
│
└── factory.py
    └── LLMProviderFactory
```

---

## 【重点内容】
这一章我们会按这个结构来写。

`schemas.py` 定义统一请求和响应。

`base.py` 定义抽象基类。

`openai_compatible.py` 封装兼容 Chat Completions 的通用逻辑。

因为 DeepSeek 和 Qwen 都可以走 OpenAI-compatible Chat Completions 风格。

DeepSeek 官方文档给出的基础 base_url 是 `https://api.deepseek.com`，并提供 Chat Completions 调用方式；QwenCloud 文档也说明 OpenAI-compatible API 可以通过替换 `base_url`、`api_key`、`model` 来使用 Qwen 模型。

`deepseek.py` 和 `qwen.py` 只负责填自己的配置。

`openai.py` 额外演示 OpenAI Responses API 适配，因为 OpenAI 当前官方 Quickstart 使用 Responses API 的 `input` 和 `output_text` 风格。

`factory.py` 负责根据配置创建具体 Provider。

---

# 九、06｜创建目录和文件
## 【屏幕操作】
执行：

```bash
mkdir -p app/llm/providers

touch app/llm/__init__.py
touch app/llm/schemas.py
touch app/llm/base.py
touch app/llm/errors.py
touch app/llm/http_client.py
touch app/llm/factory.py

touch app/llm/providers/__init__.py
touch app/llm/providers/openai_compatible.py
touch app/llm/providers/deepseek.py
touch app/llm/providers/qwen.py
touch app/llm/providers/openai.py
```

Windows PowerShell：

```powershell
mkdir app\llm\providers

New-Item app\llm\__init__.py
New-Item app\llm\schemas.py
New-Item app\llm\base.py
New-Item app\llm\errors.py
New-Item app\llm\http_client.py
New-Item app\llm\factory.py

New-Item app\llm\providers\__init__.py
New-Item app\llm\providers\openai_compatible.py
New-Item app\llm\providers\deepseek.py
New-Item app\llm\providers\qwen.py
New-Item app\llm\providers\openai.py
```

---

## 【重点内容】
我们先把目录建出来。

注意：

```plain
providers
```

这个目录专门放不同厂商的实现。

以后新增模型厂商，也放这里。

比如：

```plain
kimi.py
claude.py
ollama.py
doubao.py
```

---

# 十、07｜升级 app/llm/schemas.py
打开：

```plain
app/llm/schemas.py
```

写入：

```python
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMProviderName(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"


class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    role: LLMRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class LLMRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: list[LLMMessage] = Field(..., min_length=1, description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大输出 token")
    stream: bool = Field(default=False, description="是否流式输出")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class LLMUsage(BaseModel):
    prompt_tokens: int = Field(default=0, ge=0, description="输入 token")
    completion_tokens: int = Field(default=0, ge=0, description="输出 token")
    total_tokens: int = Field(default=0, ge=0, description="总 token")


class LLMResponse(BaseModel):
    provider: LLMProviderName = Field(..., description="模型供应商")
    model: str = Field(..., description="模型名称")
    content: str = Field(..., description="模型输出内容")
    usage: LLMUsage = Field(default_factory=LLMUsage, description="Token 用量")
    raw_response: dict[str, Any] = Field(default_factory=dict, description="原始响应")


class LLMStreamChunk(BaseModel):
    provider: LLMProviderName = Field(..., description="模型供应商")
    model: str = Field(..., description="模型名称")
    content: str = Field(default="", description="当前增量内容")
    finish_reason: str | None = Field(default=None, description="结束原因")
    usage: LLMUsage | None = Field(default=None, description="Token 用量")
    raw_chunk: dict[str, Any] = Field(default_factory=dict, description="原始 chunk")
```

---

## 【重点内容】
这里我们统一定义 LLM 调用的数据结构。

重点是这几个类：

```plain
LLMRequest
LLMResponse
LLMStreamChunk
LLMUsage
```

`LLMRequest` 是我们后端内部调用模型的请求。

`LLMResponse` 是非流式调用的统一响应。

`LLMStreamChunk` 是流式调用时每一段 chunk 的统一格式。

这样无论底层是 DeepSeek、Qwen 还是 OpenAI，业务层看到的都是统一结构。

---

# 十一、08｜定义 LLM 错误
打开：

```plain
app/llm/errors.py
```

写入：

```python
class LLMProviderError(Exception):
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int | None = None,
        raw_error: str | None = None,
    ):
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.raw_error = raw_error

        super().__init__(message)


class LLMProviderConfigError(LLMProviderError):
    pass


class LLMProviderTimeoutError(LLMProviderError):
    pass


class LLMProviderResponseParseError(LLMProviderError):
    pass
```

---

## 【重点内容】
这里我们定义 LLM 层自己的异常。

为什么不直接抛 HTTPException？

因为 LLM Provider 是底层模块。

它不应该直接知道 FastAPI 的 HTTPException。

Provider 只抛自己的异常。

然后 Service 层或者统一异常转换层，把它转换成：

```python
AppException
```

这样层次更清楚。

错误分层是：

```plain
Provider 内部
抛 LLMProviderError

Service 层
捕获后转 AppException

Exception Handler
统一返回 ErrorResponse
```

---

# 十二、09｜定义 BaseLLMProvider
打开：

```plain
app/llm/base.py
```

写入：

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.llm.schemas import LLMRequest, LLMResponse, LLMStreamChunk


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

---

## 【重点内容】
这是 Provider 架构的核心抽象。

所有模型 Provider 都要实现两个方法：

```python
chat()
```

用于非流式调用。

```python
stream_chat()
```

用于流式调用。

业务层以后只依赖：

```python
BaseLLMProvider
```

而不是依赖具体的 DeepSeekProvider 或 QwenProvider。

这就是面向抽象编程。

---

# 十三、10｜封装 http_client.py
打开：

```plain
app/llm/http_client.py
```

写入：

```python
import httpx


def create_llm_http_client(timeout_seconds: float = 60) -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        connect=10,
        read=timeout_seconds,
        write=10,
        pool=10,
    )

    return httpx.AsyncClient(timeout=timeout)
```

---

## 【重点内容】
这里我们单独封装 HTTP Client 创建逻辑。

为什么？

因为大模型请求一般比普通接口慢。

尤其是：

```plain
长文本生成
RAG 总结
Agent 多步骤推理
Deep Research
```

所以 timeout 要合理设置。

后面如果要加代理、连接池、重试，也可以在这里统一改。

httpx 官方文档说明 timeout 可以拆成 connect、read、write、pool 多个阶段，这比只写一个数字更清晰。

---

# 十四、11｜封装 OpenAICompatibleProvider
打开：

```plain
app/llm/providers/openai_compatible.py
```

写入：

```python
import json
from collections.abc import AsyncGenerator

import httpx

from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import (
    LLMProviderConfigError,
    LLMProviderError,
    LLMProviderResponseParseError,
    LLMProviderTimeoutError,
)
from app.llm.http_client import create_llm_http_client
from app.llm.schemas import (
    LLMProviderName,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
)


logger = get_logger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_name: LLMProviderName

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_seconds: float = 60,
    ):
        if not api_key:
            raise LLMProviderConfigError(
                message="LLM API Key 未配置",
                provider=self.provider_name.value,
            )

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds

    async def chat(self, request: LLMRequest) -> LLMResponse:
        payload = self._build_payload(request=request, stream=False)
        url = f"{self.base_url}/chat/completions"

        logger.info(
            f"llm_chat_start provider={self.provider_name.value} "
            f"model={payload['model']} message_count={len(request.messages)}"
        )

        try:
            async with create_llm_http_client(self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                )

                response.raise_for_status()

        except httpx.TimeoutException as exc:
            logger.exception(
                f"llm_chat_timeout provider={self.provider_name.value}"
            )
            raise LLMProviderTimeoutError(
                message="大模型调用超时",
                provider=self.provider_name.value,
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.exception(
                f"llm_chat_http_error provider={self.provider_name.value} "
                f"status_code={exc.response.status_code}"
            )
            raise LLMProviderError(
                message="大模型 HTTP 调用失败",
                provider=self.provider_name.value,
                status_code=exc.response.status_code,
                raw_error=exc.response.text,
            ) from exc

        except httpx.RequestError as exc:
            logger.exception(
                f"llm_chat_request_error provider={self.provider_name.value}"
            )
            raise LLMProviderError(
                message="大模型网络请求失败",
                provider=self.provider_name.value,
                raw_error=repr(exc),
            ) from exc

        data = response.json()

        try:
            llm_response = self._parse_chat_response(data)
        except Exception as exc:
            logger.exception(
                f"llm_chat_parse_error provider={self.provider_name.value}"
            )
            raise LLMProviderResponseParseError(
                message="大模型响应解析失败",
                provider=self.provider_name.value,
                raw_error=json.dumps(data, ensure_ascii=False),
            ) from exc

        logger.info(
            f"llm_chat_success provider={self.provider_name.value} "
            f"model={llm_response.model} total_tokens={llm_response.usage.total_tokens}"
        )

        return llm_response

    async def stream_chat(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        payload = self._build_payload(request=request, stream=True)
        url = f"{self.base_url}/chat/completions"

        logger.info(
            f"llm_stream_start provider={self.provider_name.value} "
            f"model={payload['model']} message_count={len(request.messages)}"
        )

        try:
            async with create_llm_http_client(self.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=self._headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        if not line.startswith("data:"):
                            continue

                        data = line.removeprefix("data:").strip()

                        if data == "[DONE]":
                            break

                        chunk_data = json.loads(data)
                        chunk = self._parse_stream_chunk(chunk_data)

                        yield chunk

        except httpx.TimeoutException as exc:
            logger.exception(
                f"llm_stream_timeout provider={self.provider_name.value}"
            )
            raise LLMProviderTimeoutError(
                message="大模型流式调用超时",
                provider=self.provider_name.value,
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.exception(
                f"llm_stream_http_error provider={self.provider_name.value} "
                f"status_code={exc.response.status_code}"
            )
            raise LLMProviderError(
                message="大模型流式 HTTP 调用失败",
                provider=self.provider_name.value,
                status_code=exc.response.status_code,
                raw_error=exc.response.text,
            ) from exc

        except httpx.RequestError as exc:
            logger.exception(
                f"llm_stream_request_error provider={self.provider_name.value}"
            )
            raise LLMProviderError(
                message="大模型流式网络请求失败",
                provider=self.provider_name.value,
                raw_error=repr(exc),
            ) from exc

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        request: LLMRequest,
        stream: bool,
    ) -> dict:
        payload = {
            "model": request.model or self.default_model,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
            ],
            "temperature": request.temperature,
            "stream": stream,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        return payload

    def _parse_chat_response(self, data: dict) -> LLMResponse:
        choice = data["choices"][0]
        message = choice["message"]

        usage_data = data.get("usage") or {}

        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            provider=self.provider_name,
            model=data.get("model", self.default_model),
            content=message.get("content", ""),
            usage=usage,
            raw_response=data,
        )

    def _parse_stream_chunk(self, data: dict) -> LLMStreamChunk:
        choice = data["choices"][0]
        delta = choice.get("delta") or {}
        usage_data = data.get("usage")

        usage = None

        if usage_data:
            usage = LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        return LLMStreamChunk(
            provider=self.provider_name,
            model=data.get("model", self.default_model),
            content=delta.get("content") or "",
            finish_reason=choice.get("finish_reason"),
            usage=usage,
            raw_chunk=data,
        )
```

---

## 【重点内容】
这个文件是本章最核心的代码。

它封装了 OpenAI-compatible Chat Completions 的通用逻辑。

为什么叫 OpenAI-compatible？

因为很多模型厂商都兼容类似接口。

请求都是：

```plain
POST /chat/completions
```

请求体都有：

```plain
model
messages
temperature
stream
```

响应里通常都有：

```plain
choices
message
content
usage
```

DeepSeek 的 Chat Completion 文档就展示了这种结构，并说明流式模式会通过 SSE 返回 `data:` chunk，最后用 `data: [DONE]` 结束。

所以我们把这些通用逻辑放到：

```python
OpenAICompatibleProvider
```

后面 DeepSeekProvider 和 QwenProvider 继承它就行。

---

# 十五、12｜实现 DeepSeekProvider
打开：

```plain
app/llm/providers/deepseek.py
```

写入：

```python
from app.core.config import settings
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.llm.schemas import LLMProviderName


class DeepSeekProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.DEEPSEEK

    def __init__(self):
        super().__init__(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            default_model="deepseek-chat",
            timeout_seconds=60,
        )
```

---

## 【重点内容】
DeepSeekProvider 非常简单。

因为通用调用逻辑已经在父类里了。

DeepSeekProvider 只需要提供：

```plain
provider_name
api_key
base_url
default_model
```

这就是继承和复用的价值。

后面如果 DeepSeek 有特殊逻辑，比如 reasoning_content、前缀补全、beta 接口，我们可以在 DeepSeekProvider 里单独扩展。

---

# 十六、13｜实现 QwenProvider
打开：

```plain
app/llm/providers/qwen.py
```

写入：

```python
from app.core.config import settings
from app.llm.providers.openai_compatible import OpenAICompatibleProvider
from app.llm.schemas import LLMProviderName, LLMRequest


class QwenProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.QWEN

    def __init__(self):
        super().__init__(
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
            default_model="qwen-plus",
            timeout_seconds=60,
        )

    def _build_payload(
        self,
        request: LLMRequest,
        stream: bool,
    ) -> dict:
        payload = super()._build_payload(request=request, stream=stream)

        if stream:
            payload["stream_options"] = {
                "include_usage": True
            }

        return payload
```

---

## 【重点内容】
QwenProvider 也继承 OpenAICompatibleProvider。

但是它重写了：

```python
_build_payload()
```

为什么？

因为 Qwen 流式输出时，如果想在最后一个 chunk 里拿到 usage，可以设置：

```python
stream_options = {
    "include_usage": True
}
```

QwenCloud 文档也提到，OpenAI Chat Completions 流式调用可以通过 `stream_options={"include_usage": True}` 在最后一个 chunk 中返回 usage。

这就是 Provider 的意义。

业务层不用关心这个细节。

QwenProvider 自己处理。

---

# 十七、14｜实现 OpenAIProvider
打开：

```plain
app/llm/providers/openai.py
```

写入：

```python
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import (
    LLMProviderConfigError,
    LLMProviderError,
    LLMProviderResponseParseError,
    LLMProviderTimeoutError,
)
from app.llm.http_client import create_llm_http_client
from app.llm.schemas import (
    LLMProviderName,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
)


logger = get_logger(__name__)


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        if not settings.openai_api_key:
            raise LLMProviderConfigError(
                message="OpenAI API Key 未配置",
                provider=LLMProviderName.OPENAI.value,
            )

        self.provider_name = LLMProviderName.OPENAI
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.default_model = "gpt-4.1-mini"
        self.timeout_seconds = 60

    async def chat(self, request: LLMRequest) -> LLMResponse:
        url = f"{self.base_url}/responses"

        payload = {
            "model": request.model or self.default_model,
            "input": self._messages_to_input(request),
        }

        logger.info(
            f"llm_chat_start provider=openai model={payload['model']} "
            f"message_count={len(request.messages)}"
        )

        try:
            async with create_llm_http_client(self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()

        except httpx.TimeoutException as exc:
            logger.exception("llm_chat_timeout provider=openai")
            raise LLMProviderTimeoutError(
                message="OpenAI 调用超时",
                provider=self.provider_name.value,
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.exception(
                f"llm_chat_http_error provider=openai status_code={exc.response.status_code}"
            )
            raise LLMProviderError(
                message="OpenAI HTTP 调用失败",
                provider=self.provider_name.value,
                status_code=exc.response.status_code,
                raw_error=exc.response.text,
            ) from exc

        except httpx.RequestError as exc:
            logger.exception("llm_chat_request_error provider=openai")
            raise LLMProviderError(
                message="OpenAI 网络请求失败",
                provider=self.provider_name.value,
                raw_error=repr(exc),
            ) from exc

        data = response.json()

        try:
            return self._parse_response(data)
        except Exception as exc:
            logger.exception("llm_chat_parse_error provider=openai")
            raise LLMProviderResponseParseError(
                message="OpenAI 响应解析失败",
                provider=self.provider_name.value,
                raw_error=str(data),
            ) from exc

    async def stream_chat(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        raise NotImplementedError(
            "OpenAI Responses API streaming 会在后续 Streaming 章节单独完善"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _messages_to_input(self, request: LLMRequest) -> str:
        lines = []

        for message in request.messages:
            lines.append(f"{message.role.value}: {message.content}")

        return "\n".join(lines)

    def _parse_response(self, data: dict) -> LLMResponse:
        content = data.get("output_text", "")

        usage_data = data.get("usage") or {}

        usage = LLMUsage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            provider=self.provider_name,
            model=data.get("model", self.default_model),
            content=content,
            usage=usage,
            raw_response=data,
        )
```

---

## 【重点内容】
OpenAIProvider 和 DeepSeekProvider、QwenProvider 不完全一样。

因为 OpenAI 当前 Quickstart 更推荐 Responses API。

Responses API 的请求里常见的是：

```plain
input
```

返回文本可以通过：

```plain
output_text
```

读取。

所以这里我们单独适配。

这一章里，OpenAIProvider 先实现非流式。

流式部分后面第 16 章专门讲。

这里大家先理解一个点：

**Provider 的价值就是把不同 API 风格统一成 LLMResponse。**

---

# 十八、15｜整理 providers/**init**.py
打开：

```plain
app/llm/providers/__init__.py
```

写入：

```python
from app.llm.providers.deepseek import DeepSeekProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.qwen import QwenProvider


__all__ = [
    "DeepSeekProvider",
    "OpenAIProvider",
    "QwenProvider",
]
```

---

# 十九、16｜实现 LLMProviderFactory
打开：

```plain
app/llm/factory.py
```

写入：

```python
from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.providers import DeepSeekProvider, OpenAIProvider, QwenProvider
from app.llm.schemas import LLMProviderName


class LLMProviderFactory:
    @staticmethod
    def create(provider: LLMProviderName | str | None = None) -> BaseLLMProvider:
        provider_name = provider or infer_provider_from_model(settings.default_model)

        if isinstance(provider_name, str):
            provider_name = LLMProviderName(provider_name)

        if provider_name == LLMProviderName.DEEPSEEK:
            return DeepSeekProvider()

        if provider_name == LLMProviderName.QWEN:
            return QwenProvider()

        if provider_name == LLMProviderName.OPENAI:
            return OpenAIProvider()

        raise ValueError(f"不支持的 LLM Provider：{provider_name}")


def infer_provider_from_model(model: str) -> LLMProviderName:
    if model.startswith("deepseek"):
        return LLMProviderName.DEEPSEEK

    if model.startswith("qwen"):
        return LLMProviderName.QWEN

    if model.startswith("gpt"):
        return LLMProviderName.OPENAI

    return LLMProviderName.DEEPSEEK
```

---

## 【重点内容】
Factory 的作用是创建 Provider。

业务层不用写：

```python
if provider == "deepseek":
    provider = DeepSeekProvider()
elif provider == "qwen":
    provider = QwenProvider()
```

而是直接：

```python
provider = LLMProviderFactory.create()
```

后面我们可以继续扩展 Factory。

比如根据：

```plain
请求参数
用户配置
workspace 配置
模型名称
数据库模型配置
```

来决定使用哪个 Provider。

这一章先用默认模型推断。

---

# 二十、17｜更新 app/llm/**init**.py
打开：

```plain
app/llm/__init__.py
```

写入：

```python
from app.llm.base import BaseLLMProvider
from app.llm.factory import LLMProviderFactory
from app.llm.schemas import (
    LLMMessage,
    LLMProviderName,
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMStreamChunk,
    LLMUsage,
)


__all__ = [
    "BaseLLMProvider",
    "LLMProviderFactory",
    "LLMMessage",
    "LLMProviderName",
    "LLMRequest",
    "LLMResponse",
    "LLMRole",
    "LLMStreamChunk",
    "LLMUsage",
]
```

---

# 二十一、18｜配置 .env
打开：

```plain
.env
```

确认配置：

```plain
DEFAULT_MODEL=deepseek-chat
SUPPORTED_MODELS=deepseek-chat,qwen-plus,gpt-4o-mini

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 【重点内容】
这里注意。

如果你想默认用 DeepSeek：

```plain
DEFAULT_MODEL=deepseek-chat
```

就需要配置：

```plain
DEEPSEEK_API_KEY=xxx
```

如果想默认用 Qwen：

```plain
DEFAULT_MODEL=qwen-plus
```

就需要配置：

```plain
DASHSCOPE_API_KEY=xxx
```

如果想默认用 OpenAI：

```plain
DEFAULT_MODEL=gpt-4.1-mini
```

就需要配置：

```plain
OPENAI_API_KEY=xxx
```

不要把真实 key 提交到 Git。

---

# 二十二、19｜创建测试脚本：test_llm_factory.py
创建：

```plain
scripts/test_llm_factory.py
```

写入：

```python
from app.llm.factory import LLMProviderFactory, infer_provider_from_model


models = [
    "deepseek-chat",
    "qwen-plus",
    "gpt-4.1-mini",
    "unknown-model",
]

for model in models:
    provider = infer_provider_from_model(model)
    print(model, "=>", provider)
```

运行：

```bash
python scripts/test_llm_factory.py
```

预期输出：

```plain
deepseek-chat => LLMProviderName.DEEPSEEK
qwen-plus => LLMProviderName.QWEN
gpt-4.1-mini => LLMProviderName.OPENAI
unknown-model => LLMProviderName.DEEPSEEK
```

---

## 【重点内容】
这个脚本先不真正调用模型。

只是测试 provider 推断逻辑。

根据模型名判断供应商。

这只是第一版策略。

真实项目里更推荐把模型配置放数据库。

比如：

```plain
model_name
provider
base_url
enabled
support_stream
input_price
output_price
```

后面平台化阶段会继续升级。

---

# 二十三、20｜创建测试脚本：DeepSeekProvider
创建：

```plain
scripts/test_llm_deepseek_provider.py
```

写入：

```python
import asyncio

from app.llm.providers.deepseek import DeepSeekProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole


async def main():
    provider = DeepSeekProvider()

    request = LLMRequest(
        model="deepseek-chat",
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="你是一个专业的 AI Agent 课程助教。",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content="请用一句话解释什么是 LLM Provider。",
            ),
        ],
        temperature=0.7,
        stream=False,
    )

    response = await provider.chat(request)

    print("provider:", response.provider)
    print("model:", response.model)
    print("content:", response.content)
    print("usage:", response.usage.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_llm_deepseek_provider.py

python -m app.scripts.test_llm_deepseek_provider
```

---

## 【重点内容】
这个脚本测试 DeepSeekProvider。

现在调用逻辑已经不再散落在脚本里。

而是封装到：

```python
DeepSeekProvider
```

我们只需要构造：

```python
LLMRequest
```

然后调用：

```python
provider.chat(request)
```

返回统一的：

```python
LLMResponse
```

这就是架构封装的价值。

---

# 二十四、21｜创建测试脚本：QwenProvider
创建：

```plain
scripts/test_llm_qwen_provider.py
```

写入：

```python
import asyncio

from app.llm.providers.qwen import QwenProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole


async def main():
    provider = QwenProvider()

    request = LLMRequest(
        model="qwen-plus",
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="你是一个专业的 AI Agent 课程助教。",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content="请用一句话解释什么是统一 LLM Provider 架构。",
            ),
        ],
        temperature=0.7,
        stream=False,
    )

    response = await provider.chat(request)

    print("provider:", response.provider)
    print("model:", response.model)
    print("content:", response.content)
    print("usage:", response.usage.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_llm_qwen_provider.py
```

---

# 二十五、22｜创建测试脚本：流式 Provider
创建：

```plain
scripts/test_llm_stream_provider.py
```

写入：

```python
import asyncio

from app.llm.providers.deepseek import DeepSeekProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole


async def main():
    provider = DeepSeekProvider()

    request = LLMRequest(
        model="deepseek-chat",
        messages=[
            LLMMessage(
                role=LLMRole.USER,
                content="请用三句话解释为什么要封装 LLM Provider。",
            ),
        ],
        temperature=0.7,
        stream=True,
    )

    full_content = ""

    async for chunk in provider.stream_chat(request):
        if chunk.content:
            full_content += chunk.content
            print(chunk.content, end="", flush=True)

        if chunk.usage:
            print("\nusage:", chunk.usage.model_dump())

    print("\n\nfull_content:")
    print(full_content)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_llm_stream_provider.py
```

---

## 【重点内容】
这个脚本测试统一流式接口：

```python
provider.stream_chat(request)
```

它返回的是：

```python
AsyncGenerator[LLMStreamChunk, None]
```

也就是说，业务层可以：

```python
async for chunk in provider.stream_chat(request):
    yield chunk.content
```

后面第 16 章做 FastAPI StreamingResponse 时，会直接复用这个接口。

---

# 二十六、23｜创建 LLM 依赖
打开：

```plain
app/dependencies/llm.py
```

替换为：

```python
from app.llm.base import BaseLLMProvider
from app.llm.factory import LLMProviderFactory


async def get_llm_provider() -> BaseLLMProvider:
    return LLMProviderFactory.create()
```

---

## 【重点内容】
第 09 章我们写过 MockLLMProvider。

现在我们把它替换成真正的 LLM Provider。

以后接口里注入：

```python
llm_provider: BaseLLMProvider = Depends(get_llm_provider)
```

拿到的就是真实模型 Provider。

---

# 二十七、24｜ChatRequest 转 LLMRequest
现在我们要把业务层的 ChatRequest 转成 LLMRequest。

打开：

```plain
app/services/chat_service.py
```

增加导入：

```python
from app.llm.base import BaseLLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole
```

新增转换函数：

```python
def build_llm_request_from_chat_request(request: ChatRequest) -> LLMRequest:
    return LLMRequest(
        model=request.model,
        messages=[
            LLMMessage(
                role=LLMRole(message.role.value),
                content=message.content,
            )
            for message in request.messages
        ],
        temperature=request.temperature,
        stream=request.stream,
    )
```

---

## 【重点内容】
这里大家要注意分层。

`ChatRequest` 是前端请求我们后端的模型。

`LLMRequest` 是我们后端请求大模型的模型。

这两个结构很像，但不是同一层。

所以我们写一个转换函数：

```python
build_llm_request_from_chat_request
```

这样以后如果 ChatRequest 里多了业务字段，比如：

```plain
session_id
user_id
metadata
```

不会污染 LLMRequest。

---

# 二十八、25｜改造 ChatService 调用真实 Provider
打开：

```plain
app/services/chat_service.py
```

把函数签名改成：

```python
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
    llm_provider: BaseLLMProvider | None = None,
) -> ChatResponse:
```

将原来模拟回答的逻辑，替换为真实 Provider 调用。

完整示例：

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
from app.redis.cache import cache_chat_response, get_cached_chat_response
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRole,
    SourceDocument,
    TokenUsage,
)


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
        f"chat_start model={model} message_count={len(request.messages)}"
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

    if redis:
        await cache_chat_response(
            redis=redis,
            question=latest_user_message,
            answer=answer,
        )

    if db and request.session_id:
        await conversation_repository.add_message(
            db=db,
            conversation_id=request.session_id,
            role=MessageRole.USER.value,
            content=latest_user_message,
            model=model,
            prompt_tokens=usage.prompt_tokens,
        )

        await conversation_repository.add_message(
            db=db,
            conversation_id=request.session_id,
            role=MessageRole.ASSISTANT.value,
            content=answer,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    logger.info(
        f"chat_success model={model} answer_length={len(answer)} "
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
    )


def build_llm_request_from_chat_request(request: ChatRequest) -> LLMRequest:
    return LLMRequest(
        model=request.model,
        messages=[
            LLMMessage(
                role=LLMRole(message.role.value),
                content=message.content,
            )
            for message in request.messages
        ],
        temperature=request.temperature,
        stream=request.stream,
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
现在 ChatService 发生了关键变化。

以前它是模拟回答。

现在它调用：

```python
llm_provider.chat(llm_request)
```

真实请求大模型。

同时保留了之前的工程能力：

```plain
Redis 响应缓存
PostgreSQL 消息保存
usage 保存
日志
异常转换
```

这就是项目演进的价值。

我们不是推倒重来。

而是在前面搭好的工程骨架上，把模拟逻辑替换成真实 LLM 调用。

---

# 二十九、26｜改造 Chat Router 注入 LLM Provider
打开：

```plain
app/api/v1/chat.py
```

导入：

```python
from app.llm.base import BaseLLMProvider
from app.dependencies.llm import get_llm_provider
```

修改 Chat 接口：

```python
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
```

---

## 【重点内容】
现在 Chat Router 通过 Depends 注入：

```python
llm_provider: BaseLLMProvider = Depends(get_llm_provider)
```

这就是第 09 章 Depends 的再次应用。

现在 Chat 接口依赖：

```plain
current_user
db
redis
llm_provider
```

但是接口本身依然很干净。

它只是把这些依赖传给 Service。

---

# 三十、27｜测试真实 Chat 接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的 AI Agent 课程助教。"
      },
      {
        "role": "user",
        "content": "请用一句话解释什么是统一 LLM Provider 架构。"
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
    "answer": "统一 LLM Provider 架构是把不同大模型厂商的调用方式封装成统一接口，让业务层无需关心底层差异。",
    "model": "deepseek-chat",
    "session_id": "s_xxxxxxxx",
    "message_id": "m_xxxxxxxx",
    "usage": {
      "prompt_tokens": 40,
      "completion_tokens": 30,
      "total_tokens": 70
    },
    "sources": [],
    "trace_id": "trace_xxx_user_u_10001"
  },
  "trace_id": null
}
```

---

## 【重点内容】
现在这个接口已经不是模拟回答了。

它真正经过：

```plain
Chat Router
 ↓
ChatService
 ↓
LLMProvider
 ↓
DeepSeek API
```

拿到模型返回。

这一步非常关键。

到这里，我们的项目正式完成了真实大模型调用。

---

# 三十一、28｜测试缓存效果
第一次请求会调用真实模型。

第二次请求相同问题，会命中 Redis：

```plain
chat_response_cache_hit
```

Redis Insight 里可以看到：

```plain
chat:response:xxxxxxxxxxxxxxxx
```

---

## 【重点内容】
第 12 章我们已经做了 LLM 响应缓存。

现在接入真实 LLM 后，缓存价值就更明显了。

第一次请求消耗模型 token。

第二次同样问题，直接从 Redis 返回。

这能降低：

```plain
模型成本
接口耗时
服务商限流风险
```

但是记住，不是所有问题都适合缓存。

强上下文、强实时、带用户隐私的问题，要谨慎缓存。

---

# 三十二、29｜Provider 错误如何流转
## 【实操】
```plain
DeepSeek API 错误
    ↓
OpenAICompatibleProvider
    ↓
raise LLMProviderError
    ↓
ChatService 捕获
    ↓
raise AppException
    ↓
Exception Handler
    ↓
统一 ErrorResponse
```

---

## 【重点内容】
现在错误链路也清楚了。

比如 API Key 错误。

Provider 里捕获 HTTPStatusError。

然后抛：

```python
LLMProviderError
```

ChatService 捕获后转成：

```python
AppException
```

最后统一异常处理器返回：

```json
{
  "code": 50002,
  "message": "大模型 HTTP 调用失败",
  "data": {
    "provider": "deepseek",
    "status_code": 401
  },
  "trace_id": "trace_xxx"
}
```

这样业务接口不会直接崩。

前端也能收到统一错误结构。

---

# 三十三、30｜为什么不直接把 raw_error 返回给前端
## 【重点内容】
Provider 里有：

```python
raw_error
```

里面可能包含服务商返回的详细错误。

但是我们没有直接返回给前端。

为什么？

因为里面可能包含：

```plain
模型服务商内部字段
请求 ID
账号信息
敏感错误信息
调试细节
```

所以我们只返回：

```plain
provider
status_code
```

详细错误写日志。

这符合第 10 章讲过的原则：

**对用户友好，对日志详细。**

---

# 三十四、31｜Provider 和 Factory 的演进方向
## 【重点内容】
这一章的 ProviderFactory 还是第一版。

现在它主要根据：

```plain
settings.default_model
```

推断 provider。

后面可以继续升级。

比如：

```plain
从请求参数 model 推断 provider
从数据库 models 表读取 provider
从 workspace 配置读取默认模型
从用户配置读取模型
从 Agent 配置读取模型
```

真实平台里，模型配置最好不要写死在代码里。

而是放到数据库：

```plain
llm_models
├── id
├── provider
├── model_name
├── base_url
├── enabled
├── support_stream
├── input_price
├── output_price
└── config
```

后面平台化阶段会继续扩展。

---

# 三十五、32｜统一 Provider 的好处总结
## 【实操】
| 没有 Provider | 有 Provider |
| --- | --- |
| 业务代码直接写厂商 URL | 业务代码只调用统一接口 |
| DeepSeek / Qwen / OpenAI 逻辑混在 Service | 每个厂商独立 Provider |
| usage 解析重复 | usage 统一解析 |
| 错误处理重复 | Provider 统一抛错 |
| stream 解析重复 | stream_chat 统一接口 |
| 模型切换困难 | Factory 统一创建 |
| 后续接 LangChain 不好复用 | Provider 可作为底层 LLM 调用层 |


---

## 【重点内容】
Provider 架构最大的价值是解耦。

业务代码不再和某个模型厂商绑定。

比如我们现在 ChatService 可以用 DeepSeek。

明天换 Qwen。

后天换 OpenAI。

ChatService 不需要大改。

只要 Provider 返回统一的：

```python
LLMResponse
```

业务层就能继续工作。

---

# 三十六、33｜常见错误一：API Key 未配置
错误：

```plain
LLM API Key 未配置
```

原因：

```plain
DEEPSEEK_API_KEY=
```

为空。

解决：

```plain
DEEPSEEK_API_KEY=你的真实 Key
```

重启服务：

```bash
uv run uvicorn app.main:app --reload
```

---

# 三十七、34｜常见错误二：Provider 推断错误
比如：

```plain
DEFAULT_MODEL=qwen-plus
```

但是没有配置：

```plain
DASHSCOPE_API_KEY
```

就会报 Qwen API Key 未配置。

解决：

```plain
1. 检查 DEFAULT_MODEL
2. 检查对应 API Key
3. 检查 factory.py 的 infer_provider_from_model
```

---

# 三十八、35｜常见错误三：base_url 多了路径
错误配置：

```plain
DEEPSEEK_BASE_URL=https://api.deepseek.com/chat/completions
```

Provider 里又拼：

```python
f"{base_url}/chat/completions"
```

最终变成：

```plain
https://api.deepseek.com/chat/completions/chat/completions
```

正确：

```plain
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

---

# 三十九、36｜常见错误四：流式 chunk 解析失败
不同厂商的流式 chunk 可能略有差异。

不要假设每个 chunk 都有：

```plain
delta.content
```

正确写法：

```python
delta = choice.get("delta") or {}
content = delta.get("content") or ""
```

并且 usage 可能为空：

```python
usage_data = data.get("usage")
```

要做空值判断。

---

# 四十、37｜常见错误五：OpenAI Responses API 和 Chat Completions 混用
OpenAI Responses API 常见 endpoint 是：

```plain
/responses
```

Chat Completions 常见 endpoint 是：

```plain
/chat/completions
```

它们请求和响应结构不一样。

不要把：

```python
choices[0].message.content
```

直接用在 Responses API 上。

Responses API 的 Quickstart 示例使用 `output_text` 获取输出文本。

---

# 四十一、38｜常见错误六：把 Provider 写成一个超级类
不推荐：

```python
class LLMProvider:
    if provider == "deepseek":
        ...
    elif provider == "qwen":
        ...
    elif provider == "openai":
        ...
```

这个类会越来越大。

推荐拆分：

```plain
BaseLLMProvider
OpenAICompatibleProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
Factory
```

这样每个类职责更清楚。

---

# 四十二、39｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| BaseLLMProvider | 统一大模型调用接口 |
| DeepSeekProvider | 接入 DeepSeek Chat |
| QwenProvider | 接入 Qwen / DashScope compatible API |
| OpenAIProvider | 接入 OpenAI Responses API |
| OpenAICompatibleProvider | 复用 Chat Completions 兼容逻辑 |
| LLMRequest | 后端内部模型请求结构 |
| LLMResponse | 后端内部模型响应结构 |
| LLMStreamChunk | 流式输出统一 chunk |
| LLMUsage | 统一 token 用量 |
| ProviderFactory | 根据模型或配置创建 Provider |
| LLMProviderError | 模型调用错误封装 |
| ChatService 接入 Provider | 从模拟回答切换成真实模型调用 |
| Redis Cache + LLMProvider | 降低模型成本 |
| PostgreSQL + usage | 保存消息和 token 消耗 |
| Depends(get_llm_provider) | 注入模型调用能力 |
| Factory 推断 provider | 支持多模型切换 |


---

# 四十三、40｜本章完整复习
这一章我们完成了：

```plain
1. 理解为什么不能在业务代码里直接调模型 API
2. 理解 Provider 架构的价值
3. 创建 app/llm/providers 目录
4. 定义 LLMProviderName
5. 定义 LLMRequest / LLMResponse / LLMStreamChunk
6. 定义 LLMUsage
7. 定义 LLMProviderError
8. 定义 BaseLLMProvider 抽象类
9. 封装 create_llm_http_client
10. 实现 OpenAICompatibleProvider
11. 实现 DeepSeekProvider
12. 实现 QwenProvider
13. 实现 OpenAIProvider
14. 实现 LLMProviderFactory
15. 创建 LLM 依赖 get_llm_provider
16. 编写 DeepSeekProvider 测试脚本
17. 编写 QwenProvider 测试脚本
18. 编写流式 Provider 测试脚本
19. 改造 ChatService 调用真实 LLM Provider
20. 改造 Chat Router 注入 LLM Provider
21. 保留 Redis 响应缓存
22. 保留 PostgreSQL 消息保存
23. 保留 usage 统计
24. 保留统一异常处理
```

现在我们的项目已经从：

```plain
脚本里调用大模型
```

升级成：

```plain
FastAPI 业务正式接入统一 LLM Provider 架构
```

这是 AI 后端工程化非常关键的一步。

---

# 四十四、41｜课后任务一：新增 KimiProvider
要求：

```plain
1. 在 LLMProviderName 中新增 KIMI
2. 创建 app/llm/providers/kimi.py
3. 如果 Kimi 支持 OpenAI-compatible，则继承 OpenAICompatibleProvider
4. 在 factory.py 中注册
5. 写 scripts/test_llm_kimi_provider.py
```

参考结构：

```python
class KimiProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.KIMI

    def __init__(self):
        super().__init__(
            api_key=settings.kimi_api_key,
            base_url=settings.kimi_base_url,
            default_model="kimi-k2",
            timeout_seconds=60,
        )
```

---

# 四十五、42｜课后任务二：根据 model 参数选择 Provider
当前 `get_llm_provider()` 使用默认模型。

要求升级成：

```plain
1. ChatService 根据 request.model 创建 Provider
2. 使用 infer_provider_from_model(request.model)
3. 支持 deepseek-chat / qwen-plus / gpt-xxx
```

参考：

```python
provider_name = infer_provider_from_model(request.model)
llm_provider = LLMProviderFactory.create(provider_name)
```

思考：

```plain
这个逻辑应该放在 Dependency、Service，还是 Factory？
```

---

# 四十六、43｜课后任务三：增加 LLM timeout 配置
要求：

```plain
1. 在 Settings 增加 LLM_TIMEOUT_SECONDS
2. 默认 60
3. Provider 从 settings 读取
4. 测试 timeout 配置是否生效
```

参考：

```python
llm_timeout_seconds: int = Field(default=60)
```

---

# 四十七、44｜课后任务四：统一 Provider 错误码
要求在：

```plain
app/core/exceptions.py
```

增加：

```plain
LLM_API_KEY_MISSING = 50010
LLM_MODEL_NOT_FOUND = 50011
LLM_RATE_LIMITED = 50012
LLM_TIMEOUT = 50013
LLM_RESPONSE_PARSE_FAILED = 50014
LLM_PROVIDER_ERROR = 50015
```

然后在 ChatService 中根据异常类型返回不同 code。

---

# 四十八、45｜课后任务五：画出 Provider 调用链路
画出：

```plain
POST /api/v1/chat
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
ChatService
 ↓
LLMProviderFactory
 ↓
DeepSeekProvider / QwenProvider / OpenAIProvider
 ↓
模型 API
 ↓
LLMResponse
 ↓
保存 messages + usage
 ↓
返回 ChatResponse
```

---

# 四十九、46｜本章总结
## 【重点内容】
好了，到这里，第 14 章我们就讲完了。

这一章非常关键。

因为我们完成了从：

```plain
会调用大模型 API
```

到：

```plain
能工程化封装大模型调用层
```

的升级。

大家一定要记住，真实 AI 项目不能在业务代码里直接到处写模型 API。

一定要抽象统一 Provider。

这一章我们封装了：

```plain
BaseLLMProvider
OpenAICompatibleProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
LLMProviderFactory
```

并且统一了：

```plain
LLMRequest
LLMResponse
LLMStreamChunk
LLMUsage
LLMProviderError
```

现在业务层只需要：

```python
llm_response = await llm_provider.chat(llm_request)
```

不需要关心底层是 DeepSeek、Qwen 还是 OpenAI。

到这里，我们的项目已经具备了真实 AI 后端的核心调用能力。
