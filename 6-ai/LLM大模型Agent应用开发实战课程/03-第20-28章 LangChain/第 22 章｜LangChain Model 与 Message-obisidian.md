---
title: "第 22 章｜LangChain Model 与 Message"
chapter: "22"
source: "第 22 章｜LangChain Model 与 Message.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langchain
  - message
  - chatmodel
---

# 第 22 章｜LangChain Model 与 Message

> [!abstract] 本章重点
>
> - ==四类 Message 对应四种角色== — System 定规则、Human 提问、AI 回答、Tool 回传工具结果。
> - ==ToolMessage 把工具结果接回对话== — 没有它，模型不知道上一轮工具跑了什么。
> - ==ModelFactory 统一创建模型== — 和原生阶段的 Provider Factory 是同一个思路。
> - ==invoke 同步、ainvoke 异步、stream 流式== — 同一套接口，按场景选。
> - ==content_blocks 承载多模态内容== — 不只是纯文本，还能带结构化内容块。

> [!note] 大白话
>
> - **invoke**：LangChain 里「跑一次」的统一动词。

> [!info] 导航与来源
> - 原始讲义：[[第 22 章｜LangChain Model 与 Message|打开原始讲义]]
> - [[第 21 章｜LangChain 核心架构|上一章｜第 21 章]]
> - [[第 23 章｜LangChain Prompt|下一章｜第 23 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#LangChain Model 与 Message]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜先回顾原生大模型 messages]]
- [[#七、03｜LangChain Message 类型]]
- [[#八、04｜创建 langchain_models 目录]]
- [[#九、05｜示例一：Message 基础用法]]
- [[#十、06｜SystemMessage：系统规则]]
- [[#十一、07｜HumanMessage：用户输入]]
- [[#十二、08｜AIMessage：模型输出]]
- [[#十三、09｜ToolMessage：工具结果]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们讲了：

```text
第 21 章｜LangChain 核心架构
```

重点拆解了：

```text
Message
ChatModel
PromptTemplate
OutputParser
Runnable
LCEL
Tool
Agent
Retriever
Callback
LangGraph
```

==这一章开始，我们进入第一个核心模块：==

## LangChain Model 与 Message
为什么先讲 Model 和 Message？

因为所有 LLM 应用最底层都是：

```text
messages 输入
model 调用
message 输出
```

不管你后面做：

```text
Prompt
Structured Output
Tool Calling
RAG
Agent
Multi-Agent
```

底层都绕不开：

```text
Message
+
ChatModel
```

前面第 13、14 章我们已经手写过一套：

```text
LLMMessage
LLMRequest
LLMResponse
BaseLLMProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
```

这一章就是把这些原生概念，映射到 LangChain 里。

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. LangChain Message 是什么
2. SystemMessage / HumanMessage / AIMessage / ToolMessage 分别对应什么
3. HumanMessage 和 user role 的关系
4. AIMessage 和 assistant role 的关系
5. ToolMessage 和 tool_call_id 的关系
6. ChatModel 是什么
7. ChatOpenAI 如何接入 OpenAI-compatible 模型
8. 如何用 ChatOpenAI 接 DeepSeek
9. 如何用 ChatOpenAI 接 Qwen
10. 如何用 ChatOpenAI 接 OpenAI
11. invoke 和 ainvoke 怎么用
12. stream 和 astream 怎么用
13. batch 和 abatch 怎么用
14. response_metadata 怎么看
15. usage_metadata 怎么看
16. AIMessage.tool_calls 怎么看
17. 如何把我们自己的 LLMMessage 转成 LangChain Message
18. 如何把 LangChain AIMessage 转成我们自己的 LLMResponse
19. 如何封装 LangChainLLMProvider
20. 如何让第 19 章项目逐步支持 LangChain Model
```

---

## 三、本章版本口径
本课程 LangChain 阶段统一使用当前最新稳定 1.x 体系：

```text
Python：3.12+
Pydantic：v2
LangChain：1.3.x
langchain-core：1.5.x
langchain-openai：1.5.x
LangGraph：1.2.x
```

安装建议：

```bash
uv add "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6" \
       "langgraph>=1.2,<1.3"
```

目前 PyPI 上 `langchain` 1.3.15、`langchain-core` 1.5.3、`langchain-openai` 1.5.1 都属于 2026 年发布的 1.x 稳定版本线；课程用版本范围约束，代码包用 `uv.lock` 固定实际安装版本，方便后续复现。

---

## 四、本章最终项目结构
本章新增一个目录：

```text
ai-agent-course/
├── app/
│   ├── langchain_models/
│   │   ├── __init__.py
│   │   ├── message_adapter.py
│   │   ├── model_factory.py
│   │   ├── langchain_provider.py
│   │   ├── demo_messages_basic.py
│   │   ├── demo_chat_model_invoke.py
│   │   ├── demo_chat_model_async.py
│   │   ├── demo_chat_model_stream.py
│   │   ├── demo_chat_model_batch.py
│   │   ├── demo_message_metadata.py
│   │   └── demo_tool_calls_message.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc22_messages.py
│   ├── test_lc22_model_invoke.py
│   ├── test_lc22_model_stream.py
│   ├── test_lc22_message_adapter.py
│   └── test_lc22_langchain_provider.py
│
└── README.md
```

注意：这一章文件名不用 `01_xxx.py` 这种数字开头的模块名。  
因为 Python 里 `from app.xxx.01_demo import main` 这种导入是非法语法。  
==所以后续示例统一使用 `demo_xxx.py` 这种命名。==

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 22 章。

这一章我们讲 LangChain Model 与 Message。

上一章我们从宏观上讲了 LangChain 核心架构。

这一章我们开始深入第一组核心能力：

```text
Message
+
ChatModel
```

为什么先讲它？

因为所有大模型应用最底层都是这两个东西。

你看普通聊天：

```text
用户输入
 ↓
组装 messages
 ↓
调用 model
 ↓
拿到 AIMessage
```

你看 Tool Calling：

```text
用户输入
 ↓
messages + tools
 ↓
model 返回 AIMessage.tool_calls
 ↓
后端执行工具
 ↓
ToolMessage 回传工具结果
 ↓
model 生成最终回答
```

你看 RAG：

```text
用户问题
 ↓
检索文档
 ↓
文档拼进 messages
 ↓
model 生成答案
```

==所以 Message 和 Model 是后续所有 LangChain 能力的基础。==

这一章讲透，后面 Prompt、Tool、Agent、RAG 都会顺很多。

---

## 六、02｜先回顾原生大模型 messages

> [!success] 复盘要点
> 复盘时重点看这一节。

前面我们自己定义过：

```python
class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str
    tool_call_id: str | None = None
```

调用模型时，我们会组装：

```python
messages = [
    LLMMessage(
        role=LLMRole.SYSTEM,
        content="你是一个专业 AI Agent 课程助教。",
    ),
    LLMMessage(
        role=LLMRole.USER,
        content="什么是 LangChain？",
    ),
]
```

---

### 【重点内容】
这是我们前面第 13、14 章自己定义的消息结构。

它本质上对应 OpenAI-compatible Chat API 里的 messages。

也就是：

```json
[
  {
    "role": "system",
    "content": "你是一个专业 AI Agent 课程助教。"
  },
  {
    "role": "user",
    "content": "什么是 LangChain？"
  }
]
```

LangChain 的 Message 并没有改变这个底层逻辑。

它只是把这些 dict 变成了 Python 对象。

---

## 七、03｜LangChain Message 类型
LangChain 里常用 Message 类型有：

```text
SystemMessage
HumanMessage
AIMessage
ToolMessage
```

官方消息文档也说明，消息是模型输入和输出的基本单位，并且 LangChain 支持直接使用 OpenAI chat completions 格式的消息，也支持自己的 message object 表达。

---

### 对应关系
| OpenAI-compatible role | LangChain Message | 说明 |
| --- | --- | --- |
| `system` | `SystemMessage` | 系统身份、规则、边界 |
| `user` | `HumanMessage` | 用户输入 |
| `assistant` | `AIMessage` | 模型回复 |
| `tool` | `ToolMessage` | 工具执行结果 |


---

### 【重点内容】
这里有一个容易混淆的点。

LangChain 里叫：

```text
HumanMessage
```

不是 UserMessage。

但它对应的就是 API 里的：

```text
user
```

LangChain 里叫：

```text
AIMessage
```

对应 API 里的：

```text
assistant
```

所以大家记住：

```text
HumanMessage = user
AIMessage = assistant
```

不要被名字绕晕。

---

## 八、04｜创建 langchain_models 目录
执行：

```bash
mkdir -p app/langchain_models

touch app/langchain_models/__init__.py
touch app/langchain_models/message_adapter.py
touch app/langchain_models/model_factory.py
touch app/langchain_models/langchain_provider.py
touch app/langchain_models/demo_messages_basic.py
touch app/langchain_models/demo_chat_model_invoke.py
touch app/langchain_models/demo_chat_model_async.py
touch app/langchain_models/demo_chat_model_stream.py
touch app/langchain_models/demo_chat_model_batch.py
touch app/langchain_models/demo_message_metadata.py
touch app/langchain_models/demo_tool_calls_message.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_models

New-Item app\langchain_models\__init__.py
New-Item app\langchain_models\message_adapter.py
New-Item app\langchain_models\model_factory.py
New-Item app\langchain_models\langchain_provider.py
New-Item app\langchain_models\demo_messages_basic.py
New-Item app\langchain_models\demo_chat_model_invoke.py
New-Item app\langchain_models\demo_chat_model_async.py
New-Item app\langchain_models\demo_chat_model_stream.py
New-Item app\langchain_models\demo_chat_model_batch.py
New-Item app\langchain_models\demo_message_metadata.py
New-Item app\langchain_models\demo_tool_calls_message.py
```

---

### 【重点内容】
这一章我们单独创建：

```text
app/langchain_models
```

专门放 Model 和 Message 相关示例。

它不会影响第 19 章项目一的正常运行。

我们先通过小脚本掌握 LangChain 的基础调用方式。

再逐步封装到项目里。

---

## 九、05｜示例一：Message 基础用法
打开：

```text
app/langchain_models/demo_messages_basic.py
```

写入：

```python
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


def main():
    messages = [
        SystemMessage(
            content="你是一个专业 AI Agent 课程助教。",
        ),
        HumanMessage(
            content="请解释 LangChain Message 的作用。",
        ),
        AIMessage(
            content="LangChain Message 是对大模型对话消息的对象化封装。",
        ),
        ToolMessage(
            content='{"order_id":"10001","status":"已发货"}',
            tool_call_id="call_query_order_001",
        ),
    ]

    for message in messages:
        print("class:", message.__class__.__name__)
        print("type:", message.type)
        print("content:", message.content)
        print("model_dump:")
        print(message.model_dump())
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc22_messages.py
```

写入：

```python
from app.langchain_models.demo_messages_basic import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc22_messages.py
```

---

### 【重点内容】
这个示例先不调用模型。

只看 Message 对象本身。

每个 Message 都有：

```text
type
content
model_dump()
```

`type` 是 LangChain 内部消息类型。

比如：

```text
system
human
ai
tool
```

`content` 是消息内容。

`model_dump()` 可以看到完整结构。

学 LangChain，不要只看最终答案。

要多打印中间对象。

这样后面排错会更轻松。

---

## 十、06｜SystemMessage：系统规则
### 示例
```python
from langchain_core.messages import SystemMessage

message = SystemMessage(
    content=(
        "你是一个跨境电商客服助手。\n"
        "不能编造订单状态。\n"
        "如果缺少订单号，要引导用户提供订单号。"
    )
)
```

---

### 【重点内容】
SystemMessage 对应我们前面讲的 system prompt。

它主要放：

```text
角色
规则
边界
输出要求
安全约束
```

比如电商客服场景：

```text
你是客服助手
不能编造物流信息
缺少订单号要追问
超出范围转人工
```

这些都应该放 SystemMessage。

不要把所有规则都塞到用户问题里。

---

## 十一、07｜HumanMessage：用户输入
### 示例
```python
from langchain_core.messages import HumanMessage

message = HumanMessage(
    content="我的订单 10001 到哪了？"
)
```

---

### 【重点内容】
HumanMessage 对应用户输入。

在 OpenAI-compatible API 里，它最终会变成：

```json
{
  "role": "user",
  "content": "我的订单 10001 到哪了？"
}
```

所以：

```text
HumanMessage = user message
```

后面如果你看到 human，不要以为它是新的角色。

它就是用户消息。

---

## 十二、08｜AIMessage：模型输出
### 示例
```python
from langchain_core.messages import AIMessage

message = AIMessage(
    content="LangChain 是一个 LLM 应用开发框架。"
)

print(message.content)
print(message.response_metadata)
print(message.usage_metadata)
print(message.tool_calls)
```

---

### 【重点内容】
AIMessage 对应模型回答。

它比普通字符串更丰富。

除了：

```text
content
```

还可能有：

```text
response_metadata
usage_metadata
tool_calls
id
```

这点非常重要。

很多同学只知道：

```python
response.content
```

但是真实项目里，你还需要看：

```text
模型名称
finish_reason
token usage
tool_calls
```

这些信息通常都在 metadata 里。

---

## 十三、09｜ToolMessage：工具结果
### 示例
```python
from langchain_core.messages import ToolMessage

message = ToolMessage(
    content='{"order_id":"10001","status":"已发货"}',
    tool_call_id="call_query_order_001",
)
```

---

### 【重点内容】
ToolMessage 是工具调用闭环里非常重要的一类消息。

它用来告诉模型：

你刚才请求调用的工具，执行结果是这个。

这里一定要有：

```text
tool_call_id
```

因为模型可能一次调用多个工具。

比如：

```text
call_001 -> query_order
call_002 -> query_logistics
```

ToolMessage 通过 tool_call_id 告诉模型：

```text
这个工具结果对应哪个 tool_call
```

LangChain 模型文档也提到，每个 ToolMessage 都包含与原始工具调用匹配的 `tool_call_id`，帮助模型把工具结果和请求关联起来。

---

## 十四、10｜Message content 和 content_blocks
### 【重点内容】
LangChain v1 里 Message 除了 `content`，还引入了更标准化的：

```text
content_blocks
```

官方消息文档说明，content blocks 是 v1 新引入的消息属性，用来跨 provider 标准化内容格式，同时保持对既有 `content` 属性的兼容；它不是替代 content，而是提供标准化访问方式。

简单理解：

```text
content：
最常用，普通文本直接用它

content_blocks：
多模态、reasoning、tool、复杂内容时更标准
```

这一阶段我们先主要使用：

```python
message.content
```

后面多模态和 Agent 流式事件，再逐步接触 content_blocks。

---

## 十五、11｜创建 ModelFactory
打开：

```text
app/langchain_models/model_factory.py
```

写入：

```python
from langchain_openai import ChatOpenAI

from app.core.config import settings


class LangChainModelFactory:
    @staticmethod
    def create(
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        streaming: bool = False,
    ) -> ChatOpenAI:
        provider = provider or settings.default_llm_provider
        model = model or settings.default_model

        if provider == "deepseek":
            return LangChainModelFactory.create_deepseek(
                model=model,
                temperature=temperature,
                streaming=streaming,
            )

        if provider == "qwen":
            return LangChainModelFactory.create_qwen(
                model=model,
                temperature=temperature,
                streaming=streaming,
            )

        if provider == "openai":
            return LangChainModelFactory.create_openai(
                model=model,
                temperature=temperature,
                streaming=streaming,
            )

        raise ValueError(f"不支持的 LangChain 模型供应商：{provider}")

    @staticmethod
    def create_deepseek(
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        streaming: bool = False,
    ) -> ChatOpenAI:
        if not settings.deepseek_api_key:
            raise RuntimeError("请先配置 DEEPSEEK_API_KEY")

        return ChatOpenAI(
            model=model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=temperature,
            streaming=streaming,
        )

    @staticmethod
    def create_qwen(
        model: str = "qwen-plus",
        temperature: float = 0.7,
        streaming: bool = False,
    ) -> ChatOpenAI:
        if not settings.dashscope_api_key:
            raise RuntimeError("请先配置 DASHSCOPE_API_KEY")

        return ChatOpenAI(
            model=model,
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
            temperature=temperature,
            streaming=streaming,
        )

    @staticmethod
    def create_openai(
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        streaming: bool = False,
    ) -> ChatOpenAI:
        if not settings.openai_api_key:
            raise RuntimeError("请先配置 OPENAI_API_KEY")

        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=temperature,
            streaming=streaming,
        )
```

---

### 【重点内容】
这里我们先封装一个 LangChainModelFactory。

它的作用和第 14 章的 LLMProviderFactory 很像。

只不过现在返回的是：

```python
ChatOpenAI
```

为什么 DeepSeek 和 Qwen 也用 ChatOpenAI？

因为它们提供 OpenAI-compatible 接口。

也就是说，只要支持类似 OpenAI Chat Completions 的请求格式，我们就可以通过：

```python
base_url
api_key
model
```

来接入。

LangChain 的 ChatOpenAI 集成文档说明，`ChatOpenAI` 是 `langchain-openai` 包里的聊天模型集成入口，并支持工具绑定和工具调用输出等能力。

---

## 十六、12｜Settings 补充字段
如果前面 `app/core/config.py` 还没有这些字段，需要补充：

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Course API")
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_v1_prefix: str = Field(default="/api/v1")
    debug: bool = Field(default=True)

    app_api_key: str = Field(default="dev-api-key-123")

    default_llm_provider: str = Field(default="deepseek")
    default_model: str = Field(default="deepseek-chat")
    supported_models: str = Field(default="deepseek-chat,qwen-plus,gpt-4o-mini")

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")

    dashscope_api_key: str = Field(default="")
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
```

---

### `.env.example`
```http
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_MODEL=deepseek-chat

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

DASHSCOPE_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

### 【重点内容】
这里有一个细节：

```text
DashScope 的环境变量一般叫 DASHSCOPE_API_KEY
```

但是我们的 provider 名叫 qwen。

==所以配置里可以这样对应：==

```text
provider=qwen
api_key=settings.dashscope_api_key
base_url=settings.qwen_base_url
```

这样命名更贴近业务理解。

---

## 十七、13｜示例二：同步 invoke 调用模型
打开：

```text
app/langchain_models/demo_chat_model_invoke.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
    )

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用三句话解释 LangChain ChatModel。"),
    ]

    response = model.invoke(messages)

    print("response class:", response.__class__.__name__)
    print("message type:", response.type)
    print("content:")
    print(response.content)
    print("response_metadata:")
    print(response.response_metadata)
    print("usage_metadata:")
    print(response.usage_metadata)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc22_model_invoke.py
```

写入：

```python
from app.langchain_models.demo_chat_model_invoke import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc22_model_invoke.py
```

---

### 【重点内容】
这是最基础的 ChatModel 调用。

核心是：

```python
response = model.invoke(messages)
```

返回值是：

```text
AIMessage
```

所以拿文本要用：

```python
response.content
```

不要以为返回的是普通字符串。

这点和我们前面自定义的：

```python
LLMResponse.content
```

不一样。

LangChain 返回的是 Message 对象。

---

## 十八、14｜invoke 可以直接传字符串吗
可以。

```python
response = model.invoke("请解释 LangChain。")
```

==但课程里建议优先使用 messages：==

```python
messages = [
    SystemMessage(content="你是一个专业 AI 助手。"),
    HumanMessage(content="请解释 LangChain。"),
]

response = model.invoke(messages)
```

---

### 【重点内容】
LangChain 允许你直接传字符串。

它会帮你转成用户消息。

但是在真实项目里，我建议大家显式写 messages。

因为你需要控制：

```text
system 规则
history 历史消息
tool message
assistant message
```

如果只传字符串，很适合 demo。

但不适合复杂业务。

所以课程代码统一用 messages。

---

## 十九、15｜示例三：异步 ainvoke 调用
打开：

```text
app/langchain_models/demo_chat_model_async.py
```

写入：

```python
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory


async def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
    )

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用三句话解释 LangChain 的 ainvoke。"),
    ]

    response = await model.ainvoke(messages)

    print("content:")
    print(response.content)
    print("usage_metadata:")
    print(response.usage_metadata)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python app/langchain_models/demo_chat_model_async.py
```

---

### 【重点内容】
FastAPI 项目里，我们大部分 Service 都是 async。

所以更常用的是：

```python
await model.ainvoke(messages)
```

不要在 async 函数里调用同步：

```python
model.invoke(messages)
```

虽然有些情况下也能跑，但会影响并发性能。

我们的项目后面接入 LangChain Provider 时，会使用 `ainvoke`。

---

## 二十、16｜示例四：stream 流式输出
打开：

```text
app/langchain_models/demo_chat_model_stream.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
        streaming=True,
    )

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用三句话解释 LangChain 的 stream。"),
    ]

    full_text = ""

    for chunk in model.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_text += chunk.content

    print()
    print("=" * 80)
    print("full_text:")
    print(full_text)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc22_model_stream.py
```

写入：

```python
from app.langchain_models.demo_chat_model_stream import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc22_model_stream.py
```

---

### 【重点内容】
LangChain 的同步流式调用是：

```python
model.stream(messages)
```

它会返回一个个 chunk。

每个 chunk 通常是：

```text
AIMessageChunk
```

我们可以通过：

```python
chunk.content
```

拿到增量文本。

这和第 16 章我们自己写的：

```python
LLMProvider.stream_chat()
```

非常像。

---

## 二十一、17｜示例五：astream 异步流式输出
在 FastAPI 项目里，更常用：

```python
async for chunk in model.astream(messages):
    ...
```

示例：

```python
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory


async def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
        streaming=True,
    )

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用三句话解释 LangChain 的 astream。"),
    ]

    async for chunk in model.astream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)

    print()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 【重点内容】
`astream` 是后面接 FastAPI StreamingResponse 的关键。

第 16 章我们写过：

```python
async for chunk in llm_provider.stream_chat(llm_request):
```

如果换成 LangChain，就是：

```python
async for chunk in model.astream(messages):
```

==所以未来我们可以把底层 Provider 替换成 LangChain ChatModel。==

但上层 StreamingResponse 的逻辑不用大改。

---

## 二十二、18｜示例六：batch 批量调用
打开：

```text
app/langchain_models/demo_chat_model_batch.py
```

写入：

```python
from app.langchain_models.model_factory import LangChainModelFactory


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.3,
    )

    questions = [
        "什么是 LangChain？",
        "什么是 LangGraph？",
        "什么是 RAG？",
    ]

    responses = model.batch(questions)

    for question, response in zip(questions, responses):
        print("question:", question)
        print("answer:", response.content)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
`batch` 用于批量执行。

比如你有多个问题需要并发调用模型：

```python
responses = model.batch(questions)
```

这比自己写循环更简洁。

不过真实项目里要注意：

```text
模型并发限制
API 限流
成本控制
错误重试
```

不要一口气 batch 几千个请求。

---

## 二十三、19｜response_metadata 和 usage_metadata
打开：

```text
app/langchain_models/demo_message_metadata.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.3,
    )

    response = model.invoke([
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用一句话解释 response_metadata。"),
    ])

    print("content:")
    print(response.content)
    print("=" * 80)

    print("response_metadata:")
    print(response.response_metadata)
    print("=" * 80)

    print("usage_metadata:")
    print(response.usage_metadata)
    print("=" * 80)

    print("id:")
    print(response.id)


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这里重点看两个字段：

```text
response_metadata
usage_metadata
```

`response_metadata` 里通常会有：

```text
model_name
finish_reason
system_fingerprint
```

不同 provider 可能不完全一样。

`usage_metadata` 里通常会有 token 用量，比如：

```text
input_tokens
output_tokens
total_tokens
```

这和我们前面 `LLMUsage` 的：

```text
prompt_tokens
completion_tokens
total_tokens
```

==是同一类信息，只是字段名不一定完全一致。==

LangChain 的模型文档说明，chat model 返回的是 AIMessage，其中包含响应元数据以及工具调用等信息；模型还支持 tool calling、structured output、streaming 等能力。

---

## 二十四、20｜LangChain usage 和我们 TokenUsage 的映射
我们前面定义的是：

```python
class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
```

LangChain 里常见：

```python
response.usage_metadata
```

可能结构类似：

```python
{
    "input_tokens": 100,
    "output_tokens": 80,
    "total_tokens": 180,
}
```

映射关系：

| 我们自己的字段 | LangChain 常见字段 |
| --- | --- |
| `prompt_tokens` | `input_tokens` |
| `completion_tokens` | `output_tokens` |
| `total_tokens` | `total_tokens` |


---

### 【重点内容】
这一步后面很重要。

如果我们要让第 19 章项目支持 LangChain Provider，就要把 LangChain 的 usage_metadata 转成我们自己的 TokenUsage。

这样数据库 messages 表就不用改。

我们的业务层仍然使用：

```python
TokenUsage
```

底层到底是原生 Provider 还是 LangChain Provider，业务层不关心。

---

## 二十五、21｜AIMessage.tool_calls
Tool Calling 场景里，模型可能返回：

```python
response.tool_calls
```

示例结构可能是：

```python
[
    {
        "name": "query_order",
        "args": {
            "order_id": "10001"
        },
        "id": "call_xxx",
        "type": "tool_call"
    }
]
```

---

### 【重点内容】
这一点对应第 18 章。

我们前面自己解析过：

```python
LLMToolCall
```

在 LangChain 里，AIMessage 里已经有：

```python
tool_calls
```

模型如果决定调用工具，就会把工具调用请求放到这里。

LangChain 模型文档说明，工具调用可以通过 `bind_tools` 把工具提供给模型，模型随后可以根据需要选择调用；“function calling”和“tool calling”在文档语境中也可以互换使用。

---

## 二十六、22｜示例七：绑定工具并查看 tool_calls
打开：

```text
app/langchain_models/demo_tool_calls_message.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.langchain_models.model_factory import LangChainModelFactory


@tool
def query_order(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。"""
    if order_id == "10001":
        return "订单 10001 已发货，物流公司顺丰，物流单号 SF10001。"

    return f"未查询到订单 {order_id}。"


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    model_with_tools = model.bind_tools([query_order])

    messages = [
        SystemMessage(
            content=(
                "你是一个电商客服助手。\n"
                "当用户询问订单状态时，优先调用工具查询真实信息。"
            )
        ),
        HumanMessage(content="帮我查一下订单 10001 到哪了？"),
    ]

    response = model_with_tools.invoke(messages)

    print("content:")
    print(response.content)
    print("=" * 80)

    print("tool_calls:")
    print(response.tool_calls)
    print("=" * 80)

    if response.tool_calls:
        first_tool_call = response.tool_calls[0]
        print("tool name:", first_tool_call["name"])
        print("tool args:", first_tool_call["args"])
        print("tool id:", first_tool_call["id"])


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子非常关键。

它展示了 LangChain 里的工具绑定。

核心代码是：

```python
model_with_tools = model.bind_tools([query_order])
```

这相当于第 18 章我们手写的：

```python
tools=tool_registry.to_openai_tools()
```

==区别是，LangChain 会根据 `@tool` 函数生成 tool schema。==

模型如果决定调用工具，结果会出现在：

```python
response.tool_calls
```

注意，模型只是返回 tool_calls。

工具真正执行还要我们后端来做。

---

## 二十七、23｜工具调用闭环里的消息顺序
Tool Calling 完整 messages 顺序通常是：

```text
SystemMessage
HumanMessage
AIMessage(tool_calls=[...])
ToolMessage(tool_call_id=...)
AIMessage(final answer)
```

对应原生 API：

```text
system
user
assistant with tool_calls
tool
assistant
```

---

### 【重点内容】
第 18 章我们说过，严谨的 Tool Calling 流程里，模型第一次返回的 assistant tool_calls message 要保留下来。

然后再追加 ToolMessage。

也就是：

```text
AIMessage(tool_calls)
+
ToolMessage(tool_call_id)
```

这两个要成对出现。

否则模型不知道工具结果对应哪个工具请求。

后面第 25 章 LangChain Tool 会完整实现这个闭环。

这一章先让大家看懂 AIMessage.tool_calls 和 ToolMessage.tool_call_id。

---

## 二十八、24｜创建 MessageAdapter
现在我们把前面自己的 LLMMessage 和 LangChain Message 打通。

打开：

```text
app/langchain_models/message_adapter.py
```

写入：

```python
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.llm.schemas import (
    LLMMessage,
    LLMResponse,
    LLMRole,
    LLMToolCall,
    LLMUsage,
)
from app.llm.schemas import LLMProviderName


def to_langchain_message(message: LLMMessage) -> BaseMessage:
    if message.role == LLMRole.SYSTEM:
        return SystemMessage(content=message.content)

    if message.role == LLMRole.USER:
        return HumanMessage(content=message.content)

    if message.role == LLMRole.ASSISTANT:
        return AIMessage(content=message.content)

    if message.role == LLMRole.TOOL:
        if not message.tool_call_id:
            raise ValueError("ToolMessage 必须提供 tool_call_id")

        return ToolMessage(
            content=message.content,
            tool_call_id=message.tool_call_id,
        )

    raise ValueError(f"不支持的消息角色：{message.role}")


def to_langchain_messages(messages: list[LLMMessage]) -> list[BaseMessage]:
    return [
        to_langchain_message(message)
        for message in messages
    ]


def to_llm_usage(ai_message: AIMessage) -> LLMUsage:
    usage = ai_message.usage_metadata or {}

    return LLMUsage(
        prompt_tokens=usage.get("input_tokens", 0),
        completion_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
    )


def to_llm_tool_calls(ai_message: AIMessage) -> list[LLMToolCall]:
    tool_calls: list[LLMToolCall] = []

    for item in ai_message.tool_calls or []:
        tool_calls.append(
            LLMToolCall(
                id=item.get("id", ""),
                name=item.get("name", ""),
                arguments=item.get("args", {}),
                raw_arguments="",
            )
        )

    return tool_calls


def to_llm_response(
    ai_message: AIMessage,
    provider: LLMProviderName,
    model: str,
) -> LLMResponse:
    return LLMResponse(
        provider=provider,
        model=model,
        content=str(ai_message.content or ""),
        usage=to_llm_usage(ai_message),
        tool_calls=to_llm_tool_calls(ai_message),
        finish_reason=(ai_message.response_metadata or {}).get("finish_reason"),
        raw_response={
            "id": ai_message.id,
            "response_metadata": ai_message.response_metadata,
            "usage_metadata": ai_message.usage_metadata,
            "tool_calls": ai_message.tool_calls,
        },
    )
```

---

### 【重点内容】
这个 Adapter 非常重要。

它让我们自己的项目和 LangChain 之间打通。

输入侧：

```text
LLMMessage
转成
LangChain BaseMessage
```

输出侧：

```text
AIMessage
转成
我们自己的 LLMResponse
```

这样上层 ChatService 不需要关心底层是不是 LangChain。

这就是适配器模式。

---

## 二十九、25｜测试 MessageAdapter
创建：

```text
scripts/test_lc22_message_adapter.py
```

写入：

```python
from app.langchain_models.message_adapter import to_langchain_messages
from app.llm.schemas import LLMMessage, LLMRole


def main():
    messages = [
        LLMMessage(
            role=LLMRole.SYSTEM,
            content="你是一个专业 AI Agent 课程助教。",
        ),
        LLMMessage(
            role=LLMRole.USER,
            content="请解释 MessageAdapter 的作用。",
        ),
    ]

    langchain_messages = to_langchain_messages(messages)

    for message in langchain_messages:
        print(message.__class__.__name__)
        print(message.type)
        print(message.content)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc22_message_adapter.py
```

---

### 【重点内容】
这个脚本验证我们自己的 LLMMessage 能不能转成 LangChain Message。

如果这一步通了，后面就可以做 LangChainProvider。

也就是让我们原来的 LLMProvider 架构支持 LangChain 模型。

---

## 三十、26｜封装 LangChainLLMProvider
打开：

```text
app/langchain_models/langchain_provider.py
```

写入：

```python
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessageChunk

from app.langchain_models.message_adapter import (
    to_langchain_messages,
    to_llm_response,
)
from app.langchain_models.model_factory import LangChainModelFactory
from app.llm.base import BaseLLMProvider
from app.llm.schemas import (
    LLMProviderName,
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
)


class LangChainLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
    ):
        self.provider = provider
        self.model = model

    @property
    def provider_name(self) -> LLMProviderName:
        if self.provider == "deepseek":
            return LLMProviderName.DEEPSEEK

        if self.provider == "qwen":
            return LLMProviderName.QWEN

        if self.provider == "openai":
            return LLMProviderName.OPENAI

        return LLMProviderName.MOCK

    async def chat(self, request: LLMRequest) -> LLMResponse:
        model = LangChainModelFactory.create(
            provider=self.provider,
            model=request.model or self.model,
            temperature=request.temperature,
            streaming=False,
        )

        messages = to_langchain_messages(request.messages)

        if request.tools:
            model = model.bind_tools(request.tools)

        ai_message = await model.ainvoke(messages)

        return to_llm_response(
            ai_message=ai_message,
            provider=self.provider_name,
            model=request.model or self.model,
        )

    async def stream_chat(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        model = LangChainModelFactory.create(
            provider=self.provider,
            model=request.model or self.model,
            temperature=request.temperature,
            streaming=True,
        )

        messages = to_langchain_messages(request.messages)

        async for chunk in model.astream(messages):
            yield self._to_stream_chunk(
                chunk=chunk,
                model=request.model or self.model,
            )

    def _to_stream_chunk(
        self,
        chunk: AIMessageChunk,
        model: str,
    ) -> LLMStreamChunk:
        return LLMStreamChunk(
            provider=self.provider_name,
            model=model,
            content=str(chunk.content or ""),
            usage=LLMUsage(),
            finish_reason=None,
            raw_chunk={
                "id": chunk.id,
                "content": chunk.content,
                "response_metadata": chunk.response_metadata,
            },
        )
```

---

### 【重点内容】
这个文件非常关键。

我们并不是把第 19 章项目推倒重来。

而是新增一个：

```python
LangChainLLMProvider
```

它仍然实现我们自己的：

```python
BaseLLMProvider
```

==所以 ChatService 还是调用：==

```python
llm_provider.chat(request)
```

但是底层可以换成 LangChain。

这就是平滑迁移。

对业务层来说：

```text
原生 Provider
LangChain Provider
都一样
```

这才是好的架构。

---

## 三十一、27｜测试 LangChainLLMProvider
创建：

```text
scripts/test_lc22_langchain_provider.py
```

写入：

```python
import asyncio

from app.langchain_models.langchain_provider import LangChainLLMProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole


async def main():
    provider = LangChainLLMProvider(
        provider="deepseek",
        model="deepseek-chat",
    )

    request = LLMRequest(
        model="deepseek-chat",
        messages=[
            LLMMessage(
                role=LLMRole.SYSTEM,
                content="你是一个专业 AI Agent 课程助教。",
            ),
            LLMMessage(
                role=LLMRole.USER,
                content="请用三句话解释 LangChainLLMProvider 的作用。",
            ),
        ],
        temperature=0.7,
        stream=False,
    )

    response = await provider.chat(request)

    print("content:")
    print(response.content)
    print("=" * 80)
    print("usage:")
    print(response.usage.model_dump())
    print("=" * 80)
    print("raw_response:")
    print(response.raw_response)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc22_langchain_provider.py
```

---

### 【重点内容】
这个脚本验证 LangChain Provider 能不能兼容我们自己的 Provider 架构。

如果它能返回：

```text
LLMResponse
```

那就说明第 19 章项目后面可以平滑切换。

==这就是为什么我们前面先做 Provider 抽象。==

如果当时直接在 ChatService 里写死 httpx，现在要接 LangChain 就会很麻烦。

---

## 三十二、28｜把 LangChain Provider 接入依赖注入
打开：

```text
app/dependencies/llm.py
```

可以增加：

```python
from app.core.config import settings
from app.langchain_models.langchain_provider import LangChainLLMProvider
from app.llm.base import BaseLLMProvider
from app.llm.factory import LLMProviderFactory


async def get_llm_provider() -> BaseLLMProvider:
    if settings.default_llm_provider.startswith("langchain_"):
        provider = settings.default_llm_provider.replace("langchain_", "")

        return LangChainLLMProvider(
            provider=provider,
            model=settings.default_model,
        )

    return LLMProviderFactory.create(
        provider=settings.default_llm_provider,
    )
```

`.env` 里可以配置：

```text
DEFAULT_LLM_PROVIDER=langchain_deepseek
DEFAULT_MODEL=deepseek-chat
```

---

### 【重点内容】
这样我们就能通过配置控制底层模型调用方式。

如果：

```text
DEFAULT_LLM_PROVIDER=deepseek
```

就走第 14 章原生 DeepSeekProvider。

如果：

```text
DEFAULT_LLM_PROVIDER=langchain_deepseek
```

就走这一章的 LangChainLLMProvider。

上层接口不用变。

这就是可插拔架构。

---

## 三十三、29｜LangChain Model 和第 19 章项目的关系
第 19 章项目当前链路：

```text
ChatService
 ↓
BaseLLMProvider
 ↓
DeepSeekProvider / QwenProvider / OpenAIProvider
 ↓
模型 API
```

接入 LangChain 后：

```text
ChatService
 ↓
BaseLLMProvider
 ↓
LangChainLLMProvider
 ↓
ChatOpenAI
 ↓
DeepSeek / Qwen / OpenAI
```

---

### 【重点内容】
大家看，ChatService 不需要知道 LangChain。

它还是依赖：

```python
BaseLLMProvider
```

只是 BaseLLMProvider 有了一个新的实现：

```python
LangChainLLMProvider
```

这就是面向接口编程。

以后你要接：

```text
LangChain
原生 HTTP
本地 Ollama
Mock Provider
```

都可以做成 BaseLLMProvider 的实现。

---

## 三十四、30｜为什么不直接在 ChatService 里用 ChatOpenAI
错误做法：

```python
async def chat_with_ai(request):
    model = ChatOpenAI(...)
    response = await model.ainvoke(...)
```

问题：

```text
业务层和 LangChain 强耦合
不好切换原生 Provider
不好做 Mock 测试
不好统一 usage
不好统一 tool_calls
不好统一错误处理
```

推荐：

```text
ChatService
 ↓
BaseLLMProvider
 ↓
LangChainLLMProvider
 ↓
ChatOpenAI
```

---

### 【重点内容】
这是企业项目里很重要的架构原则。

框架可以用，但不要让业务层强依赖框架细节。

业务层应该依赖我们自己的接口。

LangChain 是底层实现之一。

这样后续哪怕 LangChain API 又变化，也主要影响 LangChainLLMProvider，不会影响整个项目。

---

## 三十五、31｜ChatModel 的错误处理思路
LangChain Model 调用也会抛异常。

比如：

```text
API Key 错误
Base URL 错误
模型不存在
网络超时
模型服务商限流
工具 schema 不支持
```

==所以 LangChainLLMProvider 里后面要补统一异常处理。==

示例：

```python
try:
    ai_message = await model.ainvoke(messages)
except Exception as exc:
    raise LLMProviderError(
        message="LangChain 模型调用失败",
        provider=self.provider,
        status_code=None,
        raw_error=repr(exc),
    ) from exc
```

---

### 【重点内容】
这一章代码为了突出主线，异常处理写得比较轻。

真实项目里要和第 14 章原生 Provider 一样，把异常统一转换成：

```python
LLMProviderError
```

这样 ChatService 就不用关心底层是 LangChain 报错，还是 httpx 报错。

统一都变成：

```text
LLM_CALL_FAILED
```

---

## 三十六、32｜ChatModel 的 Streaming 和 FastAPI 的关系
前面第 16 章我们写：

```python
async for chunk in llm_provider.stream_chat(llm_request):
    yield format_sse(...)
```

LangChain 接入后：

```python
async for chunk in model.astream(messages):
    yield LLMStreamChunk(...)
```

所以 FastAPI 层不需要变化。

---

### 【重点内容】
==这就是我们前面架构设计的好处。==

第 16 章的 StreamingResponse 不需要关心底层模型怎么流式返回。

它只关心：

```text
stream_chat 返回 LLMStreamChunk
```

只要 LangChainLLMProvider 也实现 `stream_chat`，整个流式接口就可以复用。

---

## 三十七、33｜Message 历史上下文怎么组织
真实 Chat 场景里，messages 不只是当前问题。

通常是：

```text
SystemMessage
HumanMessage 历史 1
AIMessage 历史 1
HumanMessage 历史 2
AIMessage 历史 2
HumanMessage 当前问题
```

示例：

```python
messages = [
    SystemMessage(content="你是一个专业 AI 助手。"),
    HumanMessage(content="什么是 AI Agent？"),
    AIMessage(content="AI Agent 是可以自主规划和调用工具的智能体。"),
    HumanMessage(content="那 LangChain 和它有什么关系？"),
]
```

---

### 【重点内容】
后面我们会把第 19 章的历史消息接入 LangChain。

思路很简单：

```text
从 PostgreSQL 查最近 10 条消息
 ↓
转成 HumanMessage / AIMessage
 ↓
加上 SystemMessage
 ↓
追加当前 HumanMessage
 ↓
调用 ChatModel
```

注意上下文不能无限带。

因为 token 有限制，也有成本。

后面 Memory 和 LangGraph checkpoint 会继续讲。

---

## 三十八、34｜Message 转换历史消息时的注意事项

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

数据库里的 role 是：

```text
user
assistant
system
tool
```

LangChain 需要：

```text
HumanMessage
AIMessage
SystemMessage
ToolMessage
```

转换规则：

```python
if role == "user":
    return HumanMessage(content=content)

if role == "assistant":
    return AIMessage(content=content)

if role == "system":
    return SystemMessage(content=content)

if role == "tool":
    return ToolMessage(content=content, tool_call_id=tool_call_id)
```

---

### 【重点内容】
数据库不要直接存 LangChain 对象。

数据库存稳定的业务字段：

```text
role
content
tool_call_id
created_at
```

运行时再转换成 LangChain Message。

这样更通用。

以后你不用 LangChain 了，数据仍然可用。

---

## 三十九、35｜Message 和多模态的关系
这一章先讲文本。

但 LangChain Message 也可以承载更复杂内容。

比如：

```text
文本
图片
音频
文件
reasoning
tool call
```

LangChain v1 的 content_blocks 就是为了更标准地处理这些跨 provider 内容格式。

---

### 【重点内容】
现在我们的课程主要是文本 Agent。

后面如果做多模态模型，比如图片理解、视频理解，就不能只看 content 字符串。

那时候需要看：

```text
content_blocks
```

这一章先知道它的存在。

真正用到多模态时再展开。

---

## 四十、36｜本章常见错误一：把 response 当字符串

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
response = model.invoke(messages)
print(response)
```

然后以为 response 就是回答文本。

正确：

```python
response = model.invoke(messages)
print(response.content)
```

---

### 【重点内容】
LangChain ChatModel 返回的是 AIMessage。

真正的文本在：

```text
response.content
```

==所以不要直接把 response 当字符串用。==

---

## 四十一、37｜常见错误二：HumanMessage 和 user 混淆
错误理解：

```text
HumanMessage 是 LangChain 自己定义的新角色
```

正确理解：

```text
HumanMessage 对应 OpenAI-compatible API 的 user role
```

---

## 四十二、38｜常见错误三：ToolMessage 缺 tool_call_id

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
ToolMessage(content="工具结果")
```

正确：

```python
ToolMessage(
    content="工具结果",
    tool_call_id="call_xxx",
)
```

---

### 【重点内容】
ToolMessage 必须知道它对应哪个工具调用。

否则多工具场景会乱。

这和第 18 章讲的 tool_call_id 是同一个概念。

---

## 四十三、39｜常见错误四：在 async 代码里用 invoke
不推荐：

```python
async def chat():
    response = model.invoke(messages)
```

推荐：

```python
async def chat():
    response = await model.ainvoke(messages)
```

---

### 【重点内容】
FastAPI 的 Service 是异步函数时，尽量用：

```python
ainvoke
astream
abatch
```

不要用同步 invoke 阻塞事件循环。

---

## 四十四、40｜常见错误五：直接在业务层依赖 ChatOpenAI

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不推荐：

```python
ChatService 直接 new ChatOpenAI
```

推荐：

```text
ChatService 依赖 BaseLLMProvider
LangChainLLMProvider 内部使用 ChatOpenAI
```

---

### 【重点内容】
这样做的好处是：

```text
业务层稳定
底层可替换
测试容易 Mock
版本变化影响范围小
```

---

## 四十五、41｜常见错误六：忽略 metadata
很多同学只看：

```python
response.content
```

但真实项目还要看：

```python
response.response_metadata
response.usage_metadata
response.tool_calls
```

---

### 【重点内容】
metadata 里经常有调试和计费需要的信息。

比如：

```text
finish_reason
token usage
model name
tool calls
```

这些后面做成本统计、错误排查、工具调用都很重要。

---

## 四十六、42｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| `SystemMessage` | 第 15 章 System Prompt |
| `HumanMessage` | 第 13 章 user role |
| `AIMessage` | 第 13 章 assistant role |
| `ToolMessage` | 第 18 章 tool result |
| `ChatOpenAI` | 第 14 章 OpenAI-compatible Provider |
| `invoke` | `LLMProvider.chat()` |
| `ainvoke` | async 版 `chat()` |
| `stream` | 第 16 章流式输出 |
| `astream` | FastAPI StreamingResponse 对接 |
| `usage_metadata` | `TokenUsage` |
| `tool_calls` | `LLMToolCall` |
| `MessageAdapter` | 原生架构和 LangChain 之间的桥 |
| `LangChainLLMProvider` | `BaseLLMProvider`<br/> 新实现 |


---

## 四十七、43｜本章完整复习
这一章我们完成了：

```text
1. 理解 LangChain Message 的定位
2. 理解 SystemMessage
3. 理解 HumanMessage
4. 理解 AIMessage
5. 理解 ToolMessage
6. 理解 content 和 content_blocks
7. 创建 langchain_models 目录
8. 编写 Message 基础示例
9. 编写 LangChainModelFactory
10. 支持 DeepSeek / Qwen / OpenAI
11. 使用 ChatOpenAI 接 OpenAI-compatible 模型
12. 使用 invoke 同步调用模型
13. 使用 ainvoke 异步调用模型
14. 使用 stream 同步流式输出
15. 使用 astream 异步流式输出
16. 使用 batch 批量调用
17. 查看 response_metadata
18. 查看 usage_metadata
19. 理解 AIMessage.tool_calls
20. 使用 bind_tools 绑定工具
21. 理解 ToolMessage 和 tool_call_id
22. 实现 MessageAdapter
23. 把 LLMMessage 转成 LangChain Message
24. 把 AIMessage 转成 LLMResponse
25. 实现 LangChainLLMProvider
26. 测试 LangChainLLMProvider
27. 设计通过 DEFAULT_LLM_PROVIDER 切换 LangChain Provider
28. 总结项目一如何接入 LangChain Model
29. 总结 Model 与 Message 常见错误
```

---

## 四十八、44｜课后任务一：跑通 Message 示例
要求：

```text
1. 运行 scripts/test_lc22_messages.py
2. 打印 SystemMessage / HumanMessage / AIMessage / ToolMessage
3. 对比 message.type 和原生 role
4. 写出它们的对应关系
```

---

## 四十九、45｜课后任务二：跑通 ChatModel invoke
要求：

```text
1. 配置 DEEPSEEK_API_KEY
2. 运行 scripts/test_lc22_model_invoke.py
3. 打印 response.content
4. 打印 response_metadata
5. 打印 usage_metadata
```

---

## 五十、46｜课后任务三：实现 Qwen Model 调用
要求：

```text
1. 配置 DASHSCOPE_API_KEY
2. 使用 provider=qwen
3. model=qwen-plus
4. 调用 model.invoke(messages)
5. 打印回答
```

参考：

```python
model = LangChainModelFactory.create(
    provider="qwen",
    model="qwen-plus",
    temperature=0.7,
)
```

---

## 五十一、47｜课后任务四：实现 astream 流式脚本
要求：

```text
1. 使用 model.astream(messages)
2. async for 读取 chunk
3. 实时打印 chunk.content
4. 拼接 full_text
5. 最后打印 full_text 长度
```

---

## 五十二、48｜课后任务五：补全 LangChainLLMProvider 异常处理
要求：

```text
1. 捕获 LangChain 模型调用异常
2. 转换成 LLMProviderError
3. ChatService 不直接感知 LangChain 异常
4. 保持和原生 Provider 一致的错误处理方式
```

---

## 五十三、49｜课后任务六：让项目一通过配置切换 LangChain Provider
要求：

```text
1. 修改 app/dependencies/llm.py
2. 支持 DEFAULT_LLM_PROVIDER=langchain_deepseek
3. 启动第 19 章项目一
4. 调用 /api/v1/chat
5. 确认底层走 LangChainLLMProvider
```

---

## 五十四、50｜课后任务七：画出 Model 与 Message 调用链路
画出：

```http
POST /api/v1/chat
```

接入 LangChain Provider 后的完整链路：

```text
HTTP Request
 ↓
Chat Router
 ↓
ChatService
 ↓
BaseLLMProvider
 ↓
LangChainLLMProvider
 ↓
MessageAdapter
 ↓
LLMMessage -> LangChain Message
 ↓
ChatOpenAI.ainvoke()
 ↓
AIMessage
 ↓
MessageAdapter
 ↓
AIMessage -> LLMResponse
 ↓
ChatResponse
```

---

## 五十五、51｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 22 章我们就讲完了。

==这一章我们重点讲了 LangChain 的两个最底层核心：==

```text
Message
+
ChatModel
```

大家一定要记住：

```text
SystemMessage 对应 system
HumanMessage 对应 user
AIMessage 对应 assistant
ToolMessage 对应 tool
```

ChatModel 则对应我们前面自己写的：

```text
BaseLLMProvider
```

LangChain 里调用模型主要有：

```text
invoke
ainvoke
stream
astream
batch
```

真实 FastAPI 项目里，优先使用：

```text
ainvoke
astream
```

这一章我们还做了一件很重要的事：

```text
实现 LangChainLLMProvider
```

也就是把 LangChain ChatModel 接到我们自己的 BaseLLMProvider 架构下面。

这样第 19 章项目不需要推倒重来。

只要通过配置：

```text
DEFAULT_LLM_PROVIDER=langchain_deepseek
```

就可以逐步切换到底层 LangChain 模型调用。

==这就是企业项目里比较稳的升级方式：==

```text
业务架构不动
底层实现可替换
```

---

# 
---

> [!success] 一句话带走
> ==把 messages 的角色体系吃透，后面 Prompt、Agent、Memory 都是它的排列组合。==

> [!quote] 关于本文档
> 由原始讲义 `第 22 章｜LangChain Model 与 Message.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
