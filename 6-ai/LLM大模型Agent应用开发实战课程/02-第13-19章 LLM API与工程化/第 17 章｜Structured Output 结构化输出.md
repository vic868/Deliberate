---

# 一、本章定位
前面我们已经完成了：

```plain
第 13 章｜大模型 API 原理
第 14 章｜统一 LLM Provider 架构
第 15 章｜Prompt Engineering 工程化实战
第 16 章｜Streaming 流式输出
```

现在项目已经具备：

```plain
统一 LLM Provider
Prompt 模板化管理
普通 Chat 调用
流式 Chat 调用
Redis 缓存
PostgreSQL 消息保存
统一异常处理
```

但是目前模型主要还是输出一段自然语言。

比如：

```plain
用户想查询订单。
```

这对人来说能看懂。

但是对程序来说不好处理。

程序更希望拿到：

```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true
}
```

这就是结构化输出。

本章要解决的问题是：

**如何让大模型输出后端能稳定解析、校验、保存和驱动业务逻辑的数据结构。**

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 什么是 Structured Output
2. 为什么自然语言不适合程序处理
3. JSON Mode 和 JSON Schema 的区别
4. Prompt 约束 JSON 输出怎么写
5. Pydantic 如何校验模型输出
6. model_validate_json 怎么用
7. 如何定义结构化输出 Schema
8. 如何做意图识别结构化输出
9. 如何做 RAG 答案结构化输出
10. 如何做 Agent Plan 结构化输出
11. 如何把 response_format 传给 LLM Provider
12. 如何解析 LLMResponse.content
13. 如何处理模型输出 Markdown 代码块
14. 如何处理 JSON 解析失败
15. 如何做结构化输出失败重试
16. 如何做输出修复 Prompt
17. 如何把结构化结果接入 FastAPI 接口
18. 如何记录结构化输出日志
19. 如何避免直接相信模型输出
20. Structured Output 和 Function Calling 的关系
```

---

# 三、本章最终项目结构
本章结束后，项目会新增和修改：

```plain
ai-agent-course/
├── app/
│   ├── structured_outputs/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── parser.py
│   │   ├── response_format.py
│   │   ├── retry.py
│   │   └── examples.py
│   │
│   ├── prompts/
│   │   ├── structured.py
│   │   └── ...
│   │
│   ├── services/
│   │   ├── structured_output_service.py
│   │   ├── chat_service.py
│   │   └── ...
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── structured_outputs.py
│   │       ├── api.py
│   │       └── ...
│   │
│   ├── llm/
│   │   ├── schemas.py
│   │   ├── providers/
│   │   │   ├── openai_compatible.py
│   │   │   └── ...
│   │   └── ...
│   │
│   └── ...
│
├── scripts/
│   ├── test_structured_output_parse.py
│   ├── test_intent_classification.py
│   ├── test_rag_structured_output.py
│   └── test_agent_plan_structured_output.py
│
└── README.md
```

本章重点新增：

```plain
app/structured_outputs/
app/prompts/structured.py
app/services/structured_output_service.py
app/api/v1/structured_outputs.py
```

---

# 四、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 17 章。

这一章我们讲 Structured Output，结构化输出。

前面我们已经能让模型回答问题了。

比如用户问：

```plain
我的订单怎么还没发货？
```

模型可能回答：

```plain
用户想查询订单物流，但是缺少订单号，需要引导用户提供订单号。
```

这个回答人能看懂。

但是程序不好处理。

如果我们要让后端系统自动判断下一步动作，比如：

```plain
是否查询订单
是否调用物流工具
是否转人工
是否提醒用户补充订单号
```

自然语言就不够稳定。

我们更希望模型输出：

```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true,
  "reply_strategy": "ask_order_id"
}
```

这样程序可以直接读取字段。

这就是结构化输出的价值。

这一章我们要把模型输出从：

```plain
一段自然语言
```

升级成：

```plain
后端可解析、可校验、可入库、可驱动业务流程的数据结构
```

---

# 五、02｜自然语言输出的问题
## 【实操】
自然语言输出：

```plain
用户可能想查订单，需要订单号。
```

程序想要的是：

```json
{
  "intent": "query_order",
  "need_order_id": true
}
```

---

## 【重点内容】
自然语言适合给人看。

但是不适合程序直接处理。

比如模型输出：

```plain
这个用户大概率是想查询订单。
```

或者：

```plain
看起来像是订单相关问题。
```

或者：

```plain
用户应该是想问物流。
```

这些表达都差不多。

但程序很难稳定判断。

程序不能靠：

```python
if "大概率" in answer:
```

这种方式处理。

所以只要模型输出要进入业务流程，就应该尽量结构化。

---

# 六、03｜Structured Output 是什么
## 【实操】
```plain
Structured Output
=
让模型按照固定结构输出数据
```

常见形式：

```plain
JSON
JSON Schema
Pydantic Model
TypedDict
Function Arguments
Tool Arguments
```

---

## 【重点内容】
Structured Output 就是让模型输出固定结构。

最常见是 JSON。

比如意图识别：

```json
{
  "intent": "refund",
  "confidence": 0.88
}
```

RAG 问答：

```json
{
  "answer": "根据员工手册，年假为 5 天。",
  "citations": ["doc_001"],
  "is_answered": true
}
```

Agent 规划：

```json
{
  "goal": "查询订单物流",
  "steps": [
    {
      "name": "查询订单",
      "tool": "query_order",
      "reason": "需要根据订单号查询物流状态"
    }
  ]
}
```

这些结果可以直接被后端解析和使用。

---

# 七、04｜Structured Output 的典型使用场景
## 【实操】
| 场景 | 结构化输出 |
| --- | --- |
| 意图识别 | intent、confidence |
| 参数抽取 | order_id、phone、email |
| RAG 问答 | answer、citations、is_answered |
| Agent 规划 | steps、tool、arguments |
| 内容审核 | risk_level、reason、action |
| 简历分析 | problems、suggestions、rewritten_text |
| 客服分流 | category、priority、need_human |
| SQL 生成前置分析 | tables、fields、filters |


---

## 【重点内容】
结构化输出不是只用于 JSON 演示。

它在 AI 应用里非常常见。

比如电商客服：

```plain
用户到底是查订单、退款，还是问商品？
```

需要结构化意图识别。

RAG 问答：

```plain
答案是什么，引用了哪些文档，是否真的回答了？
```

需要结构化结果。

Agent：

```plain
下一步调用哪个工具，参数是什么？
```

这也需要结构化。

所以这一章是后面 Function Calling、Tool Calling、Agent 的基础。

---

# 八、05｜JSON Mode 和 JSON Schema 的区别
## 【实操】
| 能力 | JSON Mode | JSON Schema / Structured Outputs |
| --- | --- | --- |
| 目标 | 输出合法 JSON | 输出符合指定结构的 JSON |
| 约束强度 | 中等 | 更强 |
| 能否约束字段 | 弱 | 强 |
| 能否约束枚举 | 依赖模型遵守 Prompt | 可通过 schema 表达 |
| 是否还需要后端校验 | 必须 | 仍然必须 |
| 适合 | 简单 JSON 输出 | 业务强结构输出 |


---

## 【重点内容】
这里大家要分清楚两个概念。

第一个是 JSON Mode。

它主要解决：

```plain
输出必须是合法 JSON
```

比如 DeepSeek 的 JSON Output 文档里说明，可以设置：

```json
{
  "response_format": {
    "type": "json_object"
  }
}
```

让模型输出合法 JSON 字符串。

第二个是 JSON Schema。

它不仅要求是 JSON，还要求字段结构符合 schema。

比如 OpenAI Chat Completions 文档里提到：

```json
{
  "type": "json_schema",
  "json_schema": {}
}
```

用于 Structured Outputs，让模型匹配你提供的 JSON Schema。

但是不管哪种方式，后端都不能直接相信模型输出。

最终还要用 Pydantic 校验。

---

# 九、06｜为什么后端还要 Pydantic 校验
## 【重点内容】
很多同学会问：

既然模型支持 JSON Schema 了，为什么还要 Pydantic？

原因很简单。

第一，不同模型对结构化输出支持程度不一样。

第二，有些厂商只保证合法 JSON，不保证业务字段完全正确。

第三，模型可能因为安全拒答、上下文异常、长度截断，输出非预期内容。

第四，后端业务不能把关键逻辑完全交给模型。

所以正确链路是：

```plain
Prompt 约束
 ↓
response_format 约束
 ↓
模型输出 JSON
 ↓
Pydantic 校验
 ↓
校验成功才进入业务逻辑
```

Pydantic v2 的 `model_validate_json()` 可以直接校验 JSON 字符串并转换成模型对象。

---

# 十、07｜创建 structured_outputs 目录
## 【屏幕操作】
执行：

```bash
mkdir -p app/structured_outputs

touch app/structured_outputs/__init__.py
touch app/structured_outputs/schemas.py
touch app/structured_outputs/parser.py
touch app/structured_outputs/response_format.py
touch app/structured_outputs/retry.py
touch app/structured_outputs/examples.py
```

Windows PowerShell：

```powershell
mkdir app\structured_outputs

New-Item app\structured_outputs\__init__.py
New-Item app\structured_outputs\schemas.py
New-Item app\structured_outputs\parser.py
New-Item app\structured_outputs\response_format.py
New-Item app\structured_outputs\retry.py
New-Item app\structured_outputs\examples.py
```

---

## 【重点内容】
现在我们创建一个新目录：

```plain
app/structured_outputs
```

专门管理结构化输出。

不要把这些代码全部塞进 ChatService。

这里会放：

```plain
schemas.py
= 结构化输出 Pydantic 模型

parser.py
= JSON 解析和校验

response_format.py
= 给 LLM Provider 的 response_format

retry.py
= 失败重试和修复

examples.py
= 测试样例
```

这样结构清晰。

---

# 十一、08｜定义结构化输出 Schema
打开：

```plain
app/structured_outputs/schemas.py
```

写入：

```python
from typing import Literal

from pydantic import BaseModel, Field


class IntentClassificationOutput(BaseModel):
    intent: Literal[
        "query_order",
        "refund",
        "logistics",
        "product_question",
        "human_service",
        "other",
    ] = Field(..., description="用户意图")

    confidence: float = Field(..., ge=0, le=1, description="置信度")

    need_order_id: bool = Field(
        default=False,
        description="是否需要用户提供订单号",
    )

    reply_strategy: Literal[
        "answer_directly",
        "ask_order_id",
        "call_tool",
        "transfer_human",
        "reject",
    ] = Field(..., description="回复策略")

    reason: str = Field(..., description="判断原因")


class RAGStructuredAnswerOutput(BaseModel):
    answer: str = Field(..., description="最终回答")

    is_answered: bool = Field(
        ...,
        description="是否根据知识库回答了问题",
    )

    citations: list[str] = Field(
        default_factory=list,
        description="引用文档 ID 列表",
    )

    missing_info: str | None = Field(
        default=None,
        description="如果无法回答，缺少什么信息",
    )

    confidence: float = Field(
        default=0,
        ge=0,
        le=1,
        description="回答置信度",
    )


class AgentPlanStep(BaseModel):
    step_id: int = Field(..., ge=1, description="步骤序号")

    name: str = Field(..., description="步骤名称")

    action_type: Literal[
        "think",
        "tool_call",
        "respond",
    ] = Field(..., description="动作类型")

    tool_name: str | None = Field(
        default=None,
        description="需要调用的工具名称",
    )

    arguments: dict = Field(
        default_factory=dict,
        description="工具参数",
    )

    reason: str = Field(..., description="为什么需要这一步")


class AgentPlanOutput(BaseModel):
    goal: str = Field(..., description="用户目标")

    need_tools: bool = Field(
        ...,
        description="是否需要调用工具",
    )

    steps: list[AgentPlanStep] = Field(
        ...,
        min_length=1,
        description="执行步骤",
    )

    final_response_style: Literal[
        "short",
        "detailed",
        "customer_service",
    ] = Field(
        default="short",
        description="最终回复风格",
    )


class ResumeOptimizationOutput(BaseModel):
    problems: list[str] = Field(
        default_factory=list,
        description="简历存在的问题",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="优化建议",
    )

    rewritten_text: str = Field(
        ...,
        description="改写后的简历内容",
    )
```

---

## 【重点内容】
这里我们先定义四类结构化输出。

第一类：

```plain
IntentClassificationOutput
```

用于用户意图识别。

第二类：

```plain
RAGStructuredAnswerOutput
```

用于 RAG 问答结果。

第三类：

```plain
AgentPlanOutput
```

用于 Agent 任务规划。

第四类：

```plain
ResumeOptimizationOutput
```

用于简历优化输出。

大家看这些 Schema 都是业务结构。

不是随便定义的。

结构化输出必须服务业务流程。

---

# 十二、09｜为什么字段要用 Literal
## 【重点内容】
大家看这里：

```python
intent: Literal[
    "query_order",
    "refund",
    "logistics",
    "product_question",
    "human_service",
    "other",
]
```

为什么不用普通字符串？

因为普通字符串太宽泛。

模型可能输出：

```plain
查询订单
order_query
queryOrder
订单查询
```

这些对人来说都差不多。

但对程序来说是不同值。

所以我们用 Literal 限定枚举值。

这样 Pydantic 会强校验。

如果模型输出：

```json
{
  "intent": "订单查询"
}
```

就会校验失败。

这正是我们想要的。

程序系统里，字段值必须稳定。

---

# 十三、10｜创建 JSON 解析器
打开：

```plain
app/structured_outputs/parser.py
```

写入：

```python
import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)


class StructuredOutputParseError(Exception):
    def __init__(
        self,
        message: str,
        raw_text: str,
        detail: str | None = None,
    ):
        self.message = message
        self.raw_text = raw_text
        self.detail = detail

        super().__init__(message)


def extract_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            text,
            re.DOTALL,
        )

        if match:
            return match.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    return text


def parse_structured_output(
    raw_text: str,
    schema: type[T],
) -> T:
    json_text = extract_json_text(raw_text)

    try:
        return schema.model_validate_json(json_text)

    except ValidationError as exc:
        raise StructuredOutputParseError(
            message="结构化输出字段校验失败",
            raw_text=raw_text,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise StructuredOutputParseError(
            message="结构化输出不是合法 JSON",
            raw_text=raw_text,
            detail=str(exc),
        ) from exc


def safe_json_loads(raw_text: str) -> dict:
    json_text = extract_json_text(raw_text)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise StructuredOutputParseError(
            message="JSON 解析失败",
            raw_text=raw_text,
            detail=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise StructuredOutputParseError(
            message="结构化输出必须是 JSON object",
            raw_text=raw_text,
            detail=f"实际类型：{type(data)}",
        )

    return data
```

---

## 【重点内容】
这个解析器非常实用。

模型有时候会输出：

```plain
```json
{
  "intent": "query_order"
}
```

```plain
也就是带 Markdown 代码块。

如果我们直接：

```python id="prpj6h"
model_validate_json(raw_text)
```

可能会失败。

所以先用：

```python
extract_json_text()
```

把 JSON 提取出来。

然后再：

```python
schema.model_validate_json(json_text)
```

校验。

这样能处理很多常见情况。

---

# 十四、11｜测试 JSON 解析器
创建：

```plain
scripts/test_structured_output_parse.py
```

写入：

```python
from app.structured_outputs.parser import parse_structured_output
from app.structured_outputs.schemas import IntentClassificationOutput


def main():
    raw_text = """
```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true,
  "reply_strategy": "ask_order_id",
  "reason": "用户在询问订单状态，但是没有提供订单号。"
}
```

"""

```plain
result = parse_structured_output(
    raw_text=raw_text,
    schema=IntentClassificationOutput,
)

print(result.model_dump())
```

if **name** == "**main**":  
main()

```plain
运行：

```bash id="tpu0k6"
python scripts/test_structured_output_parse.py
```

预期输出：

```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true,
  "reply_strategy": "ask_order_id",
  "reason": "用户在询问订单状态，但是没有提供订单号。"
}
```

---

## 【重点内容】
这个脚本测试两件事。

第一，能从 Markdown 代码块里提取 JSON。

第二，能用 Pydantic 校验字段。

如果模型输出少字段、字段类型错误、枚举值错误，都会失败。

这就是结构化输出的基础防线。

---

# 十五、12｜创建 response_format 工具
打开：

```plain
app/structured_outputs/response_format.py
```

写入：

```python
from pydantic import BaseModel


def build_json_object_response_format() -> dict:
    return {
        "type": "json_object",
    }


def build_json_schema_response_format(
    schema: type[BaseModel],
    name: str,
    strict: bool = True,
) -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "strict": strict,
            "schema": schema.model_json_schema(),
        },
    }
```

---

## 【重点内容】
这里我们封装两种 response_format。

第一种：

```python
json_object
```

适合支持 JSON Mode 的模型。

第二种：

```python
json_schema
```

适合支持 JSON Schema Structured Outputs 的模型。

这两种能力在不同模型服务商上支持情况不完全一样。

所以我们的 Provider 只负责透传。

具体使用哪种，由业务和模型能力决定。

---

# 十六、13｜升级 LLMRequest 支持 response_format
打开：

```plain
app/llm/schemas.py
```

找到：

```python
class LLMRequest(BaseModel):
```

增加字段：

```python
response_format: dict | None = Field(
    default=None,
    description="模型结构化输出格式约束",
)
```

完整片段：

```python
class LLMRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: list[LLMMessage] = Field(..., min_length=1, description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大输出 token")
    stream: bool = Field(default=False, description="是否流式输出")
    response_format: dict | None = Field(
        default=None,
        description="模型结构化输出格式约束",
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")
```

---

## 【重点内容】
现在 LLMRequest 支持：

```python
response_format
```

这样业务层可以告诉 Provider：

```plain
我希望这次输出 JSON
```

或者：

```plain
我希望这次输出符合某个 JSON Schema
```

Provider 不需要知道业务是什么。

它只负责把 response_format 传给模型服务商。

---

# 十七、14｜升级 OpenAICompatibleProvider 透传 response_format
打开：

```plain
app/llm/providers/openai_compatible.py
```

找到：

```python
def _build_payload(
    self,
    request: LLMRequest,
    stream: bool,
) -> dict:
```

修改成：

```python
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

    if request.response_format is not None:
        payload["response_format"] = request.response_format

    return payload
```

---

## 【重点内容】
这里我们只做一件事：

```python
payload["response_format"] = request.response_format
```

这样 DeepSeekProvider、QwenProvider 这类继承 OpenAICompatibleProvider 的 Provider，都可以支持 response_format。

注意，这只是透传。

如果某个模型不支持对应格式，模型服务商会报错。

所以真实项目里还要在模型配置里标记：

```plain
support_json_object
support_json_schema
support_structured_output
```

这一章先打通基础能力。

---

# 十八、15｜创建结构化 Prompt
创建：

```plain
app/prompts/structured.py
```

写入：

```python
from app.prompts.base import (
    PromptMessageTemplate,
    PromptRole,
    PromptScenario,
    PromptTemplate,
)


INTENT_CLASSIFICATION_STRUCTURED_PROMPT_V1 = PromptTemplate(
    prompt_id="intent_classification_structured",
    name="客服意图识别结构化输出 Prompt",
    scenario=PromptScenario.ECOMMERCE_CUSTOMER_SERVICE,
    version="v1",
    description="识别用户客服意图，并输出严格 JSON。",
    required_variables=[
        "user_question",
    ],
    messages=[
        PromptMessageTemplate(
            role=PromptRole.SYSTEM,
            template=(
                "你是一个电商客服意图识别器。\n"
                "你必须只输出 JSON，不要输出 Markdown，不要输出解释，不要输出代码块。\n"
                "\n"
                "字段说明：\n"
                "- intent：用户意图，只能是 query_order、refund、logistics、product_question、human_service、other 之一。\n"
                "- confidence：置信度，0 到 1 之间的小数。\n"
                "- need_order_id：是否需要用户提供订单号。\n"
                "- reply_strategy：回复策略，只能是 answer_directly、ask_order_id、call_tool、transfer_human、reject 之一。\n"
                "- reason：简短说明判断原因。\n"
                "\n"
                "输出 JSON 示例：\n"
                "{{\n"
                "  \"intent\": \"query_order\",\n"
                "  \"confidence\": 0.92,\n"
                "  \"need_order_id\": true,\n"
                "  \"reply_strategy\": \"ask_order_id\",\n"
                "  \"reason\": \"用户想查询订单，但没有提供订单号。\"\n"
                "}}"
            ),
        ),
        PromptMessageTemplate(
            role=PromptRole.USER,
            template="用户问题：{user_question}",
        ),
    ],
)


RAG_STRUCTURED_ANSWER_PROMPT_V1 = PromptTemplate(
    prompt_id="rag_structured_answer",
    name="RAG 结构化回答 Prompt",
    scenario=PromptScenario.RAG_QA,
    version="v1",
    description="基于知识库片段生成结构化 RAG 回答。",
    required_variables=[
        "user_question",
        "retrieved_context",
    ],
    messages=[
        PromptMessageTemplate(
            role=PromptRole.SYSTEM,
            template=(
                "你是一个企业知识库问答助手。\n"
                "你必须只输出 JSON，不要输出 Markdown，不要输出解释，不要输出代码块。\n"
                "\n"
                "回答规则：\n"
                "1. 只能基于提供的知识库片段回答。\n"
                "2. 如果知识库片段中没有答案，is_answered 必须为 false。\n"
                "3. citations 必须只包含知识库片段中出现的文档 ID。\n"
                "4. 不要编造引用来源。\n"
                "\n"
                "输出 JSON 格式：\n"
                "{{\n"
                "  \"answer\": \"回答内容\",\n"
                "  \"is_answered\": true,\n"
                "  \"citations\": [\"doc_001\"],\n"
                "  \"missing_info\": null,\n"
                "  \"confidence\": 0.9\n"
                "}}"
            ),
        ),
        PromptMessageTemplate(
            role=PromptRole.USER,
            template=(
                "用户问题：\n"
                "{user_question}\n"
                "\n"
                "知识库片段：\n"
                "{retrieved_context}"
            ),
        ),
    ],
)


AGENT_PLAN_STRUCTURED_PROMPT_V1 = PromptTemplate(
    prompt_id="agent_plan_structured",
    name="Agent 规划结构化输出 Prompt",
    scenario=PromptScenario.AGENT_PLANNER,
    version="v1",
    description="将用户目标拆解成结构化 Agent 执行计划。",
    required_variables=[
        "user_goal",
        "available_tools",
        "constraints",
    ],
    messages=[
        PromptMessageTemplate(
            role=PromptRole.SYSTEM,
            template=(
                "你是一个 AI Agent 任务规划器。\n"
                "你必须只输出 JSON，不要输出 Markdown，不要输出解释，不要输出代码块。\n"
                "\n"
                "规划规则：\n"
                "1. 只能使用 available_tools 中列出的工具。\n"
                "2. 如果不需要工具，need_tools 为 false。\n"
                "3. 如果需要工具，action_type 使用 tool_call。\n"
                "4. 如果工具不足以完成任务，要在 reason 里说明。\n"
                "\n"
                "输出 JSON 格式：\n"
                "{{\n"
                "  \"goal\": \"用户目标\",\n"
                "  \"need_tools\": true,\n"
                "  \"steps\": [\n"
                "    {{\n"
                "      \"step_id\": 1,\n"
                "      \"name\": \"查询订单\",\n"
                "      \"action_type\": \"tool_call\",\n"
                "      \"tool_name\": \"query_order\",\n"
                "      \"arguments\": {{\"order_id\": \"10001\"}},\n"
                "      \"reason\": \"需要通过订单号查询物流状态。\"\n"
                "    }}\n"
                "  ],\n"
                "  \"final_response_style\": \"customer_service\"\n"
                "}}"
            ),
        ),
        PromptMessageTemplate(
            role=PromptRole.USER,
            template=(
                "用户目标：\n"
                "{user_goal}\n"
                "\n"
                "可用工具：\n"
                "{available_tools}\n"
                "\n"
                "约束条件：\n"
                "{constraints}"
            ),
        ),
    ],
)
```

---

## 【重点内容】
这里我们新增了三个结构化 Prompt。

第一个是意图识别。

第二个是 RAG 结构化回答。

第三个是 Agent Plan。

注意每个 Prompt 都明确写了：

```plain
只输出 JSON
不要 Markdown
不要解释
不要代码块
```

这是为了减少模型输出：

```plain
好的，下面是 JSON：
```json
...
```

```plain
这种情况。

虽然我们 parser 能处理代码块，但 Prompt 里还是要尽量要求它不要输出。

---

# 十九、16｜注册结构化 Prompt

打开：

```text id="zce8pi"
app/prompts/registry.py
```

增加导入：

```python
from app.prompts.structured import (
    AGENT_PLAN_STRUCTURED_PROMPT_V1,
    INTENT_CLASSIFICATION_STRUCTURED_PROMPT_V1,
    RAG_STRUCTURED_ANSWER_PROMPT_V1,
)
```

增加注册：

```python
prompt_registry.register(INTENT_CLASSIFICATION_STRUCTURED_PROMPT_V1)
prompt_registry.register(RAG_STRUCTURED_ANSWER_PROMPT_V1)
prompt_registry.register(AGENT_PLAN_STRUCTURED_PROMPT_V1)
```

---

## 【重点内容】
现在这些结构化 Prompt 已经进入 PromptRegistry。

后面可以通过：

```python
prompt_service.render_by_prompt_id(
    prompt_id="intent_classification_structured",
    variables={...}
)
```

统一渲染。

这就是第 15 章 Prompt 工程化的价值。

---

# 二十、17｜创建 StructuredOutputService
创建：

```plain
app/services/structured_output_service.py
```

写入：

```python
from pydantic import BaseModel

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import LLMRequest
from app.prompts.base import PromptScenario
from app.services.prompt_service import prompt_service
from app.structured_outputs.parser import (
    StructuredOutputParseError,
    parse_structured_output,
)
from app.structured_outputs.response_format import (
    build_json_object_response_format,
)
from app.structured_outputs.schemas import (
    AgentPlanOutput,
    IntentClassificationOutput,
    RAGStructuredAnswerOutput,
)


logger = get_logger(__name__)


class StructuredOutputService:
    async def classify_intent(
        self,
        user_question: str,
        model: str,
        llm_provider: BaseLLMProvider,
    ) -> IntentClassificationOutput:
        messages = prompt_service.render_by_prompt_id(
            prompt_id="intent_classification_structured",
            variables={
                "user_question": user_question,
            },
        )

        request = LLMRequest(
            model=model,
            messages=messages,
            temperature=0.1,
            stream=False,
            response_format=build_json_object_response_format(),
        )

        return await self._call_and_parse(
            request=request,
            llm_provider=llm_provider,
            schema=IntentClassificationOutput,
            task_name="intent_classification",
        )

    async def generate_rag_answer(
        self,
        user_question: str,
        retrieved_context: str,
        model: str,
        llm_provider: BaseLLMProvider,
    ) -> RAGStructuredAnswerOutput:
        messages = prompt_service.render_by_prompt_id(
            prompt_id="rag_structured_answer",
            variables={
                "user_question": user_question,
                "retrieved_context": retrieved_context,
            },
        )

        request = LLMRequest(
            model=model,
            messages=messages,
            temperature=0.1,
            stream=False,
            response_format=build_json_object_response_format(),
        )

        return await self._call_and_parse(
            request=request,
            llm_provider=llm_provider,
            schema=RAGStructuredAnswerOutput,
            task_name="rag_structured_answer",
        )

    async def plan_agent_task(
        self,
        user_goal: str,
        available_tools: str,
        constraints: str,
        model: str,
        llm_provider: BaseLLMProvider,
    ) -> AgentPlanOutput:
        messages = prompt_service.render_by_prompt_id(
            prompt_id="agent_plan_structured",
            variables={
                "user_goal": user_goal,
                "available_tools": available_tools,
                "constraints": constraints,
            },
        )

        request = LLMRequest(
            model=model,
            messages=messages,
            temperature=0.1,
            stream=False,
            response_format=build_json_object_response_format(),
        )

        return await self._call_and_parse(
            request=request,
            llm_provider=llm_provider,
            schema=AgentPlanOutput,
            task_name="agent_plan",
        )

    async def _call_and_parse(
        self,
        request: LLMRequest,
        llm_provider: BaseLLMProvider,
        schema: type[BaseModel],
        task_name: str,
    ):
        logger.info(
            f"structured_output_start task={task_name} "
            f"model={request.model} schema={schema.__name__}"
        )

        try:
            response = await llm_provider.chat(request)

        except LLMProviderError as exc:
            logger.exception(
                f"structured_output_llm_error task={task_name} "
                f"provider={exc.provider} status_code={exc.status_code}"
            )

            raise AppException(
                message="结构化输出模型调用失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "task": task_name,
                    "provider": exc.provider,
                    "status_code": exc.status_code,
                },
            ) from exc

        try:
            result = parse_structured_output(
                raw_text=response.content,
                schema=schema,
            )

        except StructuredOutputParseError as exc:
            logger.warning(
                f"structured_output_parse_failed task={task_name} "
                f"detail={exc.detail}"
            )

            raise AppException(
                message="模型结构化输出解析失败",
                code=ErrorCode.LLM_RESPONSE_PARSE_FAILED,
                status_code=500,
                data={
                    "task": task_name,
                    "detail": exc.detail,
                },
            ) from exc

        logger.info(
            f"structured_output_success task={task_name} "
            f"schema={schema.__name__}"
        )

        return result


structured_output_service = StructuredOutputService()
```

---

## 【重点内容】
这个 Service 是本章核心。

它做了三件事。

第一，渲染结构化 Prompt。

第二，调用 LLM Provider。

第三，用 Pydantic 解析模型输出。

比如意图识别：

```python
classify_intent()
```

返回的不是字符串，而是：

```python
IntentClassificationOutput
```

也就是说，业务代码可以直接写：

```python
if result.intent == "query_order":
    ...
```

这就是结构化输出的价值。

---

# 二十一、18｜补充 ErrorCode
打开：

```plain
app/core/exceptions.py
```

在 `ErrorCode` 中补充：

```python
LLM_API_KEY_MISSING = 50010
LLM_MODEL_NOT_FOUND = 50011
LLM_RATE_LIMITED = 50012
LLM_TIMEOUT = 50013
LLM_RESPONSE_PARSE_FAILED = 50014
LLM_PROVIDER_ERROR = 50015
STRUCTURED_OUTPUT_PARSE_FAILED = 50016
```

完整片段示例：

```python
class ErrorCode(IntEnum):
    SUCCESS = 0

    BAD_REQUEST = 40000
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    VALIDATION_ERROR = 42200
    RATE_LIMITED = 42900

    MODEL_NOT_SUPPORTED = 50001
    LLM_CALL_FAILED = 50002
    RAG_QUERY_FAILED = 50003
    TOOL_CALL_FAILED = 50004
    AGENT_RUN_FAILED = 50005

    LLM_API_KEY_MISSING = 50010
    LLM_MODEL_NOT_FOUND = 50011
    LLM_RATE_LIMITED = 50012
    LLM_TIMEOUT = 50013
    LLM_RESPONSE_PARSE_FAILED = 50014
    LLM_PROVIDER_ERROR = 50015
    STRUCTURED_OUTPUT_PARSE_FAILED = 50016

    INTERNAL_ERROR = 50000
```

---

## 【重点内容】
结构化输出失败不应该简单返回系统错误。

它是 AI 应用里的高频错误。

比如：

```plain
模型没有输出 JSON
字段缺失
枚举值错误
数字越界
输出被截断
输出了 Markdown
```

这些都应该有明确错误码。

这样前端、后端、日志系统才能定位问题。

---

# 二十二、19｜创建结构化输出 API
创建：

```plain
app/api/v1/structured_outputs.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.dependencies.llm import get_llm_provider
from app.llm.base import BaseLLMProvider
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.services.structured_output_service import structured_output_service
from app.structured_outputs.schemas import (
    AgentPlanOutput,
    IntentClassificationOutput,
    RAGStructuredAnswerOutput,
)


router = APIRouter()


class IntentClassificationRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")


class RAGStructuredRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    retrieved_context: str = Field(..., description="检索到的知识库上下文")
    model: str = Field(default="deepseek-chat", description="模型名称")


class AgentPlanRequest(BaseModel):
    goal: str = Field(..., min_length=1, description="用户目标")
    available_tools: str = Field(..., description="可用工具列表")
    constraints: str = Field(default="无", description="约束条件")
    model: str = Field(default="deepseek-chat", description="模型名称")


@router.post(
    "/structured/intent",
    response_model=ApiResponse[IntentClassificationOutput],
)
async def classify_intent(
    request: IntentClassificationRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[IntentClassificationOutput]:
    result = await structured_output_service.classify_intent(
        user_question=request.question,
        model=request.model,
        llm_provider=llm_provider,
    )

    return ApiResponse[IntentClassificationOutput](
        data=result
    )


@router.post(
    "/structured/rag-answer",
    response_model=ApiResponse[RAGStructuredAnswerOutput],
)
async def generate_rag_structured_answer(
    request: RAGStructuredRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[RAGStructuredAnswerOutput]:
    result = await structured_output_service.generate_rag_answer(
        user_question=request.question,
        retrieved_context=request.retrieved_context,
        model=request.model,
        llm_provider=llm_provider,
    )

    return ApiResponse[RAGStructuredAnswerOutput](
        data=result
    )


@router.post(
    "/structured/agent-plan",
    response_model=ApiResponse[AgentPlanOutput],
)
async def plan_agent(
    request: AgentPlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[AgentPlanOutput]:
    result = await structured_output_service.plan_agent_task(
        user_goal=request.goal,
        available_tools=request.available_tools,
        constraints=request.constraints,
        model=request.model,
        llm_provider=llm_provider,
    )

    return ApiResponse[AgentPlanOutput](
        data=result
    )
```

---

## 【重点内容】
现在我们新增三个接口。

第一个：

```plain
/structured/intent
```

用于意图识别。

第二个：

```plain
/structured/rag-answer
```

用于 RAG 结构化回答。

第三个：

```plain
/structured/agent-plan
```

用于 Agent 规划。

这些接口返回的 data 都是 Pydantic 模型。

不是普通字符串。

这就是结构化输出真正接入业务接口。

---

# 二十三、20｜注册结构化输出 Router
打开：

```plain
app/api/v1/api.py
```

增加导入：

```python
from app.api.v1.structured_outputs import router as structured_outputs_router
```

增加注册：

```python
api_router.include_router(
    structured_outputs_router,
    tags=["Structured Outputs"],
)
```

---

# 二十四、21｜测试意图识别接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/structured/intent" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "我的订单怎么还没发货？",
    "model": "deepseek-chat"
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "intent": "query_order",
    "confidence": 0.92,
    "need_order_id": true,
    "reply_strategy": "ask_order_id",
    "reason": "用户在询问订单发货状态，需要订单号才能查询。"
  },
  "trace_id": null
}
```

---

## 【重点内容】
现在后端拿到的不是一句话。

而是结构化对象。

这样我们后面可以写业务逻辑：

```python
if result.intent == "query_order" and result.need_order_id:
    return "请提供订单号"
```

这就是结构化输出驱动业务流程。

---

# 二十五、22｜测试 RAG 结构化回答接口
请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/structured/rag-answer" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "员工年假有几天？",
    "retrieved_context": "[doc_001] 员工入职满一年后，每年享有 5 天带薪年假。",
    "model": "deepseek-chat"
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "员工入职满一年后，每年享有 5 天带薪年假。",
    "is_answered": true,
    "citations": ["doc_001"],
    "missing_info": null,
    "confidence": 0.9
  },
  "trace_id": null
}
```

---

## 【重点内容】
RAG 结构化回答有几个关键字段。

```python
answer
```

给前端展示。

```python
is_answered
```

判断知识库是否真的回答了问题。

```python
citations
```

引用了哪些文档。

```python
missing_info
```

如果回答不了，缺什么信息。

这比一段纯文本更容易做产品功能。

---

# 二十六、23｜测试 Agent Plan 接口
请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/structured/agent-plan" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "goal": "帮用户查询订单 10001 的物流状态，并给出客服回复。",
    "available_tools": "query_order(order_id: string)：根据订单号查询订单和物流状态。",
    "constraints": "不能编造物流信息；只能调用已提供的工具。",
    "model": "deepseek-chat"
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "goal": "帮用户查询订单 10001 的物流状态，并给出客服回复。",
    "need_tools": true,
    "steps": [
      {
        "step_id": 1,
        "name": "查询订单物流",
        "action_type": "tool_call",
        "tool_name": "query_order",
        "arguments": {
          "order_id": "10001"
        },
        "reason": "需要通过订单号查询真实物流状态。"
      },
      {
        "step_id": 2,
        "name": "生成客服回复",
        "action_type": "respond",
        "tool_name": null,
        "arguments": {},
        "reason": "根据工具结果给用户生成自然语言回复。"
      }
    ],
    "final_response_style": "customer_service"
  },
  "trace_id": null
}
```

---

## 【重点内容】
Agent Plan 是后面 Agent 的基础。

模型不能只说：

```plain
我会先查询订单，再回复用户。
```

它要输出结构化步骤。

这样程序才能知道：

```plain
第一步要调用 query_order
参数是 order_id=10001
第二步再生成客服回复
```

这就是 Agent 能执行的基础。

---

# 二十七、24｜创建测试脚本：意图识别
创建：

```plain
scripts/test_intent_classification.py
```

写入：

```python
import asyncio

from app.llm.factory import LLMProviderFactory
from app.services.structured_output_service import structured_output_service


async def main():
    provider = LLMProviderFactory.create("deepseek")

    questions = [
        "我的订单怎么还没发货？",
        "我想退款，怎么操作？",
        "这款衣服有黑色吗？",
        "我要找人工客服。",
    ]

    for question in questions:
        result = await structured_output_service.classify_intent(
            user_question=question,
            model="deepseek-chat",
            llm_provider=provider,
        )

        print("question:", question)
        print(result.model_dump())
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_intent_classification.py
```

---

## 【重点内容】
这个脚本可以批量测试意图识别。

结构化输出必须多测几类 case。

不要只测一个正常问题。

至少要覆盖：

```plain
查订单
退款
物流
商品咨询
转人工
其他问题
```

这样才能知道 Prompt 和 Schema 是否稳定。

---

# 二十八、25｜创建测试脚本：RAG 结构化输出
创建：

```plain
scripts/test_rag_structured_output.py
```

写入：

```python
import asyncio

from app.llm.factory import LLMProviderFactory
from app.services.structured_output_service import structured_output_service


async def main():
    provider = LLMProviderFactory.create("deepseek")

    result = await structured_output_service.generate_rag_answer(
        user_question="公司年假有几天？",
        retrieved_context="[doc_001] 员工入职满一年后，每年享有 5 天带薪年假。",
        model="deepseek-chat",
        llm_provider=provider,
    )

    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 二十九、26｜创建测试脚本：Agent Plan
创建：

```plain
scripts/test_agent_plan_structured_output.py
```

写入：

```python
import asyncio

from app.llm.factory import LLMProviderFactory
from app.services.structured_output_service import structured_output_service


async def main():
    provider = LLMProviderFactory.create("deepseek")

    result = await structured_output_service.plan_agent_task(
        user_goal="帮用户查询订单 10001 的物流状态，并生成客服回复。",
        available_tools="query_order(order_id: string)：根据订单号查询订单和物流状态。",
        constraints="不能编造物流信息；只能调用已提供的工具。",
        model="deepseek-chat",
        llm_provider=provider,
    )

    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 三十、27｜结构化输出失败重试思路
## 【重点内容】
结构化输出不是 100% 成功。

可能失败原因包括：

```plain
模型输出了 Markdown
模型少字段
模型枚举值错了
模型输出被截断
模型解释了一堆文字
模型拒答
模型返回空内容
```

所以我们需要失败重试。

最简单策略：

```plain
第一次正常请求
 ↓
解析失败
 ↓
把错误原因和原始输出发回模型
 ↓
要求模型修复成合法 JSON
 ↓
再次解析
```

这叫输出修复。

---

# 三十一、28｜实现结构化输出修复 Prompt
打开：

```plain
app/structured_outputs/retry.py
```

写入：

```python
from pydantic import BaseModel

from app.llm.base import BaseLLMProvider
from app.llm.schemas import LLMMessage, LLMRequest, LLMRole
from app.structured_outputs.parser import (
    StructuredOutputParseError,
    parse_structured_output,
)
from app.structured_outputs.response_format import (
    build_json_object_response_format,
)


async def parse_or_repair_structured_output(
    raw_text: str,
    schema: type[BaseModel],
    model: str,
    llm_provider: BaseLLMProvider,
):
    try:
        return parse_structured_output(
            raw_text=raw_text,
            schema=schema,
        )
    except StructuredOutputParseError as first_error:
        repair_messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "你是一个 JSON 修复器。\n"
                    "你的任务是把输入内容修复为符合目标结构的合法 JSON。\n"
                    "只能输出 JSON，不要输出 Markdown，不要输出解释。"
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=(
                    "目标 JSON Schema：\n"
                    f"{schema.model_json_schema()}\n"
                    "\n"
                    "上一次输出：\n"
                    f"{raw_text}\n"
                    "\n"
                    "解析错误：\n"
                    f"{first_error.detail}\n"
                    "\n"
                    "请修复为合法 JSON。"
                ),
            ),
        ]

        repair_request = LLMRequest(
            model=model,
            messages=repair_messages,
            temperature=0,
            stream=False,
            response_format=build_json_object_response_format(),
        )

        repair_response = await llm_provider.chat(repair_request)

        return parse_structured_output(
            raw_text=repair_response.content,
            schema=schema,
        )
```

---

## 【重点内容】
这个方法先尝试本地解析。

如果解析成功，直接返回。

如果失败，就让模型修复。

注意修复 Prompt 里包含：

```plain
目标 JSON Schema
上一次输出
解析错误
```

这样模型更容易修好。

但要注意，修复不是万能的。

如果业务很关键，修复失败就应该返回错误，不要硬往下走。

---

# 三十二、29｜在 Service 中使用修复重试
修改：

```plain
app/services/structured_output_service.py
```

导入：

```python
from app.structured_outputs.retry import parse_or_repair_structured_output
```

把：

```python
result = parse_structured_output(
    raw_text=response.content,
    schema=schema,
)
```

替换为：

```python
result = await parse_or_repair_structured_output(
    raw_text=response.content,
    schema=schema,
    model=request.model,
    llm_provider=llm_provider,
)
```

---

## 【重点内容】
现在结构化输出多了一层容错。

如果第一次输出不合法，会尝试修复一次。

真实项目里，不建议无限重试。

一般最多：

```plain
1～2 次
```

因为重试也会消耗 token 和时间。

后面可以把重试次数放到配置里。

---

# 三十三、30｜结构化输出和 Streaming 的关系
## 【重点内容】
结构化输出一般不建议流式返回。

原因是：

```plain
JSON 没生成完整前，无法稳定解析
```

比如模型流式输出：

```plain
{
  "intent":
```

这时候不是完整 JSON。

程序不能解析。

所以结构化输出更适合非流式。

如果必须流式，可以把它分成两类事件。

比如 Agent 流式：

```plain
step 事件是结构化 JSON
message 事件是自然语言文本
```

但每个结构化事件本身最好是完整 JSON。

本章先用非流式完成结构化输出。

---

# 三十四、31｜结构化输出和 Function Calling 的关系
## 【重点内容】
Structured Output 和 Function Calling 很像，但定位不一样。

Structured Output 主要解决：

```plain
让模型输出一个符合结构的数据结果
```

Function Calling 主要解决：

```plain
让模型选择是否调用某个函数，并生成函数参数
```

比如意图识别，用 Structured Output 就够了。

比如查询订单，如果模型要决定调用：

```plain
query_order(order_id)
```

那就更适合 Function Calling 或 Tool Calling。

不过底层思想是一样的：

```plain
自然语言
转成
程序能处理的结构化数据
```

下一章第 18 章会正式讲 Function Calling 与 Tool Calling。

---

# 三十五、32｜结构化输出不要直接执行
## 【重点内容】
这里特别强调一个安全点。

模型输出了结构化数据，不代表可以直接执行。

比如模型输出：

```json
{
  "action_type": "tool_call",
  "tool_name": "refund_order",
  "arguments": {
    "order_id": "10001",
    "amount": 999
  }
}
```

后端不能直接退款。

必须做：

```plain
工具是否存在
用户是否有权限
参数是否合法
订单是否属于该用户
金额是否允许
是否需要人工确认
```

模型只能建议。

真正执行由后端系统控制。

这点在 Agent 场景非常重要。

---

# 三十六、33｜结构化输出日志设计
## 【重点内容】
结构化输出日志建议记录：

```plain
task_name
schema_name
model
success / failed
parse_error
token usage
trace_id
```

不建议记录完整 raw output。

因为 raw output 里可能有用户隐私、订单信息、企业知识库内容。

推荐日志：

```python
logger.info(
    f"structured_output_success task={task_name} "
    f"schema={schema.__name__}"
)
```

失败时可以记录：

```python
logger.warning(
    f"structured_output_parse_failed task={task_name} "
    f"detail={exc.detail}"
)
```

如果要记录原始内容，建议只在开发环境开启，并且做截断。

---

# 三十七、34｜结构化输出和数据库入库
## 【重点内容】
结构化输出通常应该入库。

比如：

```plain
用户意图识别结果
RAG 引用信息
Agent Plan
工具参数
审核结果
```

后面可以建表：

```plain
llm_structured_outputs
├── id
├── task_name
├── schema_name
├── model
├── raw_output
├── parsed_output
├── success
├── error_message
├── trace_id
├── created_at
```

这一章先不强行建表。

后面平台化阶段再统一设计 LLM 调用日志和结构化输出日志表。

---

# 三十八、35｜结构化输出和前端展示
## 【重点内容】
结构化输出不一定直接展示给用户。

比如意图识别结果：

```json
{
  "intent": "query_order",
  "need_order_id": true
}
```

用户不需要看到这段 JSON。

前端可以根据它展示：

```plain
请输入您的订单号
```

或者后端直接继续生成客服回复。

RAG 结构化输出则可以一部分展示：

```plain
answer
citations
```

Agent Plan 可以展示给用户，也可以只给系统内部使用。

所以要区分：

```plain
结构化输出给程序用
自然语言回答给用户看
```

---

# 三十九、36｜结构化输出常见错误一：只靠 Prompt，不做校验
错误做法：

```python
data = json.loads(llm_response.content)
intent = data["intent"]
```

问题：

```plain
字段可能不存在
类型可能错误
枚举值可能乱写
confidence 可能是字符串
```

正确：

```python
result = IntentClassificationOutput.model_validate_json(json_text)
```

---

# 四十、37｜结构化输出常见错误二：把 JSON 写在普通字符串里没有转义
Prompt 模板里写：

```plain
{
  "intent": "query_order"
}
```

在 Python `.format()` 模板里会报错。

正确写法：

```plain
{{
  "intent": "query_order"
}}
```

因为单大括号会被当成模板变量。

---

# 四十一、38｜结构化输出常见错误三：枚举值中英文混乱
Schema 要求：

```plain
query_order
```

模型输出：

```plain
查询订单
```

Pydantic 会校验失败。

解决：

```plain
1. Prompt 里明确只能输出英文枚举值
2. Few-shot 示例里使用正确枚举值
3. Pydantic 兜底校验
4. 必要时做修复重试
```

---

# 四十二、39｜结构化输出常见错误四：JSON 被 Markdown 包住
模型输出：

```plain
```json
{
  "intent": "query_order"
}
```

```plain
解决：

```python id="had70x"
extract_json_text(raw_text)
```

先把 JSON 提取出来。

同时 Prompt 里明确：

```plain
不要输出 Markdown，不要输出代码块。
```

---

# 四十三、40｜结构化输出常见错误五：输出被截断
如果 max_tokens 太小，模型可能输出半截 JSON：

```json
{
  "intent": "query_order",
  "confidence":
```

解决：

```plain
1. 适当增大 max_tokens
2. 输出结构不要太复杂
3. 减少无关字段
4. 对长结构分步骤生成
```

---

# 四十四、41｜结构化输出常见错误六：字段设计太复杂
不推荐一上来设计：

```json
{
  "intent": "...",
  "sub_intent": "...",
  "emotion": "...",
  "risk": "...",
  "entities": [...],
  "actions": [...],
  "rules": [...],
  "explanation": "..."
}
```

字段太多会让模型更容易出错。

推荐先从最小可用结构开始：

```json
{
  "intent": "query_order",
  "confidence": 0.9
}
```

跑稳定后再扩展。

---

# 四十五、42｜结构化输出常见错误七：把业务决策完全交给模型
模型可以判断：

```plain
用户可能要退款
```

但是能不能退款，需要后端系统判断：

```plain
订单状态
付款时间
商品类型
用户权限
售后规则
风控策略
```

所以结构化输出只能作为输入。

最终决策必须由业务系统确认。

---

# 四十六、43｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| JSON Mode | 让模型输出合法 JSON |
| JSON Schema | 让模型尽量符合指定结构 |
| Pydantic 校验 | 后端强校验模型输出 |
| `model_validate_json()` | JSON 字符串转业务对象 |
| Literal 枚举 | 限制模型输出固定值 |
| IntentClassificationOutput | 客服意图识别 |
| RAGStructuredAnswerOutput | RAG 答案和引用 |
| AgentPlanOutput | Agent 步骤规划 |
| response_format | 模型结构化输出约束 |
| extract_json_text | 处理 Markdown 代码块 |
| StructuredOutputParseError | 结构化解析异常 |
| 修复重试 | 解析失败后让模型修复 |
| 非流式调用 | 更适合完整 JSON 解析 |
| Function Calling | 后续工具调用基础 |
| 日志和 trace_id | 排查结构化输出失败 |


---

# 四十七、44｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Structured Output 是什么
2. 理解自然语言输出的问题
3. 理解 JSON Mode 和 JSON Schema 区别
4. 理解为什么还需要 Pydantic 校验
5. 创建 app/structured_outputs 目录
6. 定义 IntentClassificationOutput
7. 定义 RAGStructuredAnswerOutput
8. 定义 AgentPlanOutput
9. 定义 ResumeOptimizationOutput
10. 实现 extract_json_text
11. 实现 parse_structured_output
12. 实现 safe_json_loads
13. 创建 response_format 工具
14. 升级 LLMRequest 支持 response_format
15. 升级 OpenAICompatibleProvider 透传 response_format
16. 创建结构化 Prompt
17. 注册结构化 Prompt
18. 创建 StructuredOutputService
19. 新增结构化输出错误码
20. 新增结构化输出 API
21. 测试意图识别接口
22. 测试 RAG 结构化回答接口
23. 测试 Agent Plan 接口
24. 编写结构化输出测试脚本
25. 实现解析失败修复重试
26. 理解结构化输出和 Streaming 的关系
27. 理解结构化输出和 Function Calling 的关系
28. 总结结构化输出常见错误
```

现在我们的项目已经从：

```plain
模型输出自然语言
```

升级成：

```plain
模型输出可被程序解析和校验的结构化数据
```

---

# 四十八、45｜课后任务一：新增订单信息抽取结构化输出
要求：

```plain
1. 定义 OrderInfoExtractOutput
2. 字段包含 order_id、phone_last4、has_required_info、missing_fields
3. 编写 Prompt
4. 注册 Prompt
5. 写 Service 方法
6. 写 API：POST /structured/order-info
```

参考 Schema：

```python
class OrderInfoExtractOutput(BaseModel):
    order_id: str | None = Field(default=None, description="订单号")
    phone_last4: str | None = Field(default=None, description="手机号后四位")
    has_required_info: bool = Field(..., description="是否具备查询订单所需信息")
    missing_fields: list[str] = Field(default_factory=list, description="缺少字段")
```

---

# 四十九、46｜课后任务二：新增内容审核结构化输出
要求：

```plain
1. 定义 ContentModerationOutput
2. 字段包含 risk_level、categories、action、reason
3. risk_level 限定 low / medium / high
4. action 限定 pass / review / reject
5. 写测试脚本
```

---

# 五十、47｜课后任务三：支持 json_schema response_format
要求：

```plain
1. 在 StructuredOutputService 中增加 use_json_schema 参数
2. 如果 use_json_schema=True，使用 build_json_schema_response_format
3. 测试支持 JSON Schema 的模型
4. 不支持时回退 json_object
```

参考：

```python
response_format = build_json_schema_response_format(
    schema=IntentClassificationOutput,
    name="intent_classification",
)
```

---

# 五十一、48｜课后任务四：结构化输出失败重试次数配置
要求：

```plain
1. Settings 增加 STRUCTURED_OUTPUT_MAX_RETRIES
2. 默认 1
3. retry.py 支持循环重试
4. 超过次数后抛 AppException
```

---

# 五十二、49｜课后任务五：结构化输出和 ChatService 集成
要求：

```plain
1. 在 ChatService 回答前先调用 classify_intent
2. 如果 intent=query_order 且 need_order_id=True
3. 直接返回“请提供订单号”
4. 如果 intent=human_service，返回转人工话术
5. 其他情况继续调用普通 LLM Chat
```

思考：

```plain
哪些意图应该直接走规则？
哪些意图应该继续调用大模型？
哪些意图应该调用工具？
```

---

# 五十三、50｜课后任务六：画出结构化输出完整链路
画出：

```plain
POST /api/v1/structured/intent
```

完整链路：

```plain
HTTP Request
 ↓
Middleware trace_id
 ↓
verify_api_key
 ↓
get_current_user
 ↓
get_llm_provider
 ↓
StructuredOutputs Router
 ↓
StructuredOutputService
 ↓
PromptService
 ↓
PromptRegistry
 ↓
render_prompt
 ↓
LLMRequest(response_format=json_object)
 ↓
LLMProvider.chat()
 ↓
模型输出 JSON
 ↓
extract_json_text
 ↓
Pydantic model_validate_json
 ↓
IntentClassificationOutput
 ↓
ApiResponse
```

---

# 五十四、51｜本章总结
## 【重点内容】
好了，到这里，第 17 章我们就讲完了。

这一章我们完成了一个非常关键的升级：

```plain
从模型自然语言输出
升级到
结构化输出
```

大家一定要记住，AI 应用不是只把模型回答展示给用户。

很多时候，模型输出要进入程序系统。

比如：

```plain
识别用户意图
抽取订单号
判断是否需要调用工具
生成 Agent Plan
生成 RAG 引用
生成审核结果
```

这些都不能只靠自然语言。

必须结构化。

这一章我们实现了：

```plain
结构化输出 Schema
JSON 解析器
Pydantic 校验
response_format
结构化 Prompt
StructuredOutputService
意图识别接口
RAG 结构化回答接口
Agent Plan 接口
解析失败修复重试
```

现在我们的项目已经具备了后端可以真正消费模型输出的能力。


