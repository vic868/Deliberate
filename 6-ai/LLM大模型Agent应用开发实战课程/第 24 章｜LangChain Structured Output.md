---

# 一、本章定位
前面我们已经完成了：

```plain
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
```

第 23 章我们把 Prompt 工程化接入了：

```plain
ChatPromptTemplate
MessagesPlaceholder
partial variables
PromptRegistry
PromptService
Prompt | Model
```

这一章继续讲 LangChain 里的第三个核心能力：

# Structured Output 结构化输出
第 17 章我们已经手写过一套结构化输出能力：

```plain
IntentClassificationOutput
RAGStructuredAnswerOutput
AgentPlanOutput
parse_structured_output
extract_json_text
response_format
repair retry
StructuredOutputService
```

这一章要解决的问题是：

**如何用 LangChain 的 OutputParser 和 with_structured_output，把模型输出稳定转换成后端可校验、可入库、可驱动业务流程的数据结构。**

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. LangChain Structured Output 是什么
2. OutputParser 是什么
3. StrOutputParser 怎么用
4. JsonOutputParser 怎么用
5. PydanticOutputParser 怎么用
6. parser.get_format_instructions() 有什么用
7. Prompt | Model | Parser 怎么组成结构化输出链
8. PydanticOutputParser 和第 17 章手写 parser 的区别
9. with_structured_output 是什么
10. with_structured_output 和 PydanticOutputParser 的区别
11. 哪些场景适合 Parser 方案
12. 哪些场景适合 with_structured_output 方案
13. 如何做意图识别结构化输出
14. 如何做 RAG 结构化回答
15. 如何做 Agent Plan 结构化输出
16. 如何处理模型输出解析失败
17. 如何做结构化输出修复重试
18. 如何保留我们自己的 StructuredOutputService
19. 如何把 LangChain Structured Output 接入第 19 章项目
20. 如何为后面的 Tool Calling / Agent / RAG 打基础
```

---

# 三、本章版本口径
本课程 LangChain 阶段统一使用：

```plain
Python：3.12+
Pydantic：v2
LangChain：1.3.x
langchain-core：1.5.x
langchain-openai：1.5.x
LangGraph：1.2.x
```

安装：

```bash
uv add "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6" \
       "langgraph>=1.2,<1.3"
```

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langchain_structured_outputs/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── retry.py
│   │   ├── demo_str_output_parser.py
│   │   ├── demo_json_output_parser.py
│   │   ├── demo_pydantic_output_parser.py
│   │   ├── demo_with_structured_output.py
│   │   ├── demo_intent_classification.py
│   │   ├── demo_rag_structured_answer.py
│   │   ├── demo_agent_plan.py
│   │   └── demo_project_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langchain_structured_outputs.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc24_str_parser.py
│   ├── test_lc24_json_parser.py
│   ├── test_lc24_pydantic_parser.py
│   ├── test_lc24_with_structured_output.py
│   ├── test_lc24_intent.py
│   ├── test_lc24_rag_answer.py
│   └── test_lc24_agent_plan.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 24 章。

这一章我们讲 LangChain Structured Output。

第 17 章我们已经讲过结构化输出。

当时我们说过一句话：

AI 应用不能只让模型输出一段自然语言，很多时候后端需要的是稳定的数据结构。

比如用户问：

```plain
我的订单怎么还没发货？
```

模型如果只回答：

```plain
用户应该是想查询订单。
```

人能看懂，但是程序不好处理。

程序更希望拿到：

```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true,
  "reply_strategy": "ask_order_id"
}
```

这就是结构化输出。

第 17 章我们用原生方式写了：

```plain
Pydantic Schema
JSON 解析
Markdown JSON 提取
字段校验
失败重试
修复 Prompt
```

这一章我们看看 LangChain 如何帮我们做这件事。

---

# 六、02｜LangChain Structured Output 的两条路线
## 【实操】
```plain
路线一：OutputParser 方案

Prompt
 ↓
Model
 ↓
OutputParser
 ↓
Pydantic 对象 / JSON / str
```

```plain
路线二：with_structured_output 方案

Model.with_structured_output(PydanticSchema)
 ↓
直接返回结构化对象
```

---

## 【重点内容】
LangChain 里做结构化输出，常见有两条路线。

第一条是 OutputParser。

也就是：

```python
chain = prompt | model | parser
```

这个方案比较通用。

你可以控制 Prompt，控制格式说明，控制解析器。

第二条是：

```python
model.with_structured_output(Schema)
```

这个方案更直接。

它会把模型包装成结构化输出模型。

调用后直接返回指定结构。

但是要注意，不是所有模型和所有 OpenAI-compatible 服务商都对结构化输出支持完全一致。

所以课程里两个方案都讲。

真实项目里，一般会这样选：

```plain
需要强兼容：
优先用 PydanticOutputParser

模型原生支持结构化输出：
可以用 with_structured_output
```

LangChain 官方结构化输出文档说明，结构化输出可以让 Agent 或模型返回类型化、机器可读的数据，而不是普通文本；模型文档也说明 LangChain 支持多种 schema 类型和多种结构化输出约束方式。

---

# 七、03｜第 17 章原生结构化输出回顾
第 17 章我们写过：

```python
class IntentClassificationOutput(BaseModel):
    intent: Literal[
        "query_order",
        "refund",
        "logistics",
        "product_question",
        "human_service",
        "other",
    ]
    confidence: float
    need_order_id: bool
    reply_strategy: Literal[
        "answer_directly",
        "ask_order_id",
        "call_tool",
        "transfer_human",
        "reject",
    ]
    reason: str
```

并通过：

```python
parse_structured_output(raw_text, IntentClassificationOutput)
```

把模型输出解析成对象。

---

## 【重点内容】
原生结构化输出的核心流程是：

```plain
写 Pydantic Schema
 ↓
Prompt 里要求模型输出 JSON
 ↓
模型返回字符串
 ↓
提取 JSON
 ↓
Pydantic 校验
 ↓
校验成功进入业务逻辑
```

LangChain 的 OutputParser 方案，本质上也是这个流程。

只是它把：

```plain
格式说明生成
输出解析
Runnable 组合
```

封装好了。

---

# 八、04｜OutputParser 是什么
## 【实操】
```plain
OutputParser
=
把模型输出转换成程序需要的数据类型

AIMessage / str
 ↓
Parser
 ↓
str / dict / Pydantic object / list
```

常用 Parser：

```plain
StrOutputParser
JsonOutputParser
PydanticOutputParser
```

---

## 【重点内容】
OutputParser 就是输出解析器。

它解决的是：

模型输出不是最终业务对象，需要解析。

比如 ChatModel 默认返回：

```plain
AIMessage
```

但是业务可能只需要字符串。

那就用：

```plain
StrOutputParser
```

如果业务需要 JSON dict，就用：

```plain
JsonOutputParser
```

如果业务需要 Pydantic 对象，就用：

```plain
PydanticOutputParser
```

LangChain Core 的 output parser 参考文档列出了 `StrOutputParser`、`JsonOutputParser`、`PydanticOutputParser` 等解析器，并说明 OutputParser 类用于把 LLM 调用输出解析成结构化数据。

---

# 九、05｜创建 langchain_structured_outputs 目录
执行：

```bash
mkdir -p app/langchain_structured_outputs

touch app/langchain_structured_outputs/__init__.py
touch app/langchain_structured_outputs/schemas.py
touch app/langchain_structured_outputs/service.py
touch app/langchain_structured_outputs/retry.py
touch app/langchain_structured_outputs/demo_str_output_parser.py
touch app/langchain_structured_outputs/demo_json_output_parser.py
touch app/langchain_structured_outputs/demo_pydantic_output_parser.py
touch app/langchain_structured_outputs/demo_with_structured_output.py
touch app/langchain_structured_outputs/demo_intent_classification.py
touch app/langchain_structured_outputs/demo_rag_structured_answer.py
touch app/langchain_structured_outputs/demo_agent_plan.py
touch app/langchain_structured_outputs/demo_project_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_structured_outputs

New-Item app\langchain_structured_outputs\__init__.py
New-Item app\langchain_structured_outputs\schemas.py
New-Item app\langchain_structured_outputs\service.py
New-Item app\langchain_structured_outputs\retry.py
New-Item app\langchain_structured_outputs\demo_str_output_parser.py
New-Item app\langchain_structured_outputs\demo_json_output_parser.py
New-Item app\langchain_structured_outputs\demo_pydantic_output_parser.py
New-Item app\langchain_structured_outputs\demo_with_structured_output.py
New-Item app\langchain_structured_outputs\demo_intent_classification.py
New-Item app\langchain_structured_outputs\demo_rag_structured_answer.py
New-Item app\langchain_structured_outputs\demo_agent_plan.py
New-Item app\langchain_structured_outputs\demo_project_adapter.py
```

---

# 十、06｜定义结构化输出 Schema
打开：

```plain
app/langchain_structured_outputs/schemas.py
```

写入：

```python
from typing import Literal

from pydantic import BaseModel, Field


class IntentClassificationResult(BaseModel):
    intent: Literal[
        "query_order",
        "refund",
        "logistics",
        "product_question",
        "human_service",
        "other",
    ] = Field(..., description="用户意图")

    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="置信度，0 到 1 之间",
    )

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


class RAGAnswerResult(BaseModel):
    answer: str = Field(..., description="最终回答")

    is_answered: bool = Field(
        ...,
        description="是否基于知识库回答了问题",
    )

    citations: list[str] = Field(
        default_factory=list,
        description="引用的 document_id 列表",
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
        "ask_user",
        "human_confirm",
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


class AgentPlanResult(BaseModel):
    goal: str = Field(..., description="用户目标")

    need_tools: bool = Field(
        ...,
        description="是否需要调用工具",
    )

    need_human_confirm: bool = Field(
        default=False,
        description="是否需要人工确认",
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


class ResumeReviewResult(BaseModel):
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="简历评分",
    )

    problems: list[str] = Field(
        default_factory=list,
        description="简历存在的问题",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="优化建议",
    )

    rewritten_summary: str = Field(
        ...,
        description="改写后的项目摘要",
    )
```

---

## 【重点内容】
这里我们定义四类结构化输出。

第一类：

```plain
IntentClassificationResult
```

用于电商客服意图识别。

第二类：

```plain
RAGAnswerResult
```

用于企业知识库问答。

第三类：

```plain
AgentPlanResult
```

用于 Agent 任务规划。

第四类：

```plain
ResumeReviewResult
```

用于简历分析。

这些 Schema 和第 17 章类似，只是这次会用于 LangChain OutputParser 和 with_structured_output。

---

# 十一、07｜示例一：StrOutputParser
打开：

```plain
app/langchain_structured_outputs/demo_str_output_parser.py
```

写入：

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory


def main():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业 AI Agent 课程助教。",
        ),
        (
            "human",
            "请用三句话解释：{topic}",
        ),
    ])

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
    )

    parser = StrOutputParser()

    chain = prompt | model | parser

    result = chain.invoke({
        "topic": "StrOutputParser 的作用",
    })

    print("result type:", type(result))
    print("result:")
    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_str_parser.py
```

写入：

```python
from app.langchain_structured_outputs.demo_str_output_parser import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc24_str_parser.py
```

---

## 【重点内容】
StrOutputParser 是最简单的 Parser。

它把 ChatModel 返回的 AIMessage 转成字符串。

也就是说：

```plain
AIMessage
 ↓
StrOutputParser
 ↓
str
```

如果你的业务只需要最终文本，用它就够了。

比如普通 Chat 的最终回答就可以用 StrOutputParser。

---

# 十二、08｜示例二：JsonOutputParser
打开：

```plain
app/langchain_structured_outputs/demo_json_output_parser.py
```

写入：

```python
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory


def main():
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个电商客服意图识别器。\n"
                "你必须只输出 JSON，不要输出 Markdown，不要解释。\n"
                "{format_instructions}"
            ),
        ),
        (
            "human",
            "用户问题：{user_question}",
        ),
    ]).partial(
        format_instructions=parser.get_format_instructions()
    )

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    chain = prompt | model | parser

    result = chain.invoke({
        "user_question": "我的订单怎么还没发货？",
    })

    print("result type:", type(result))
    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_json_parser.py
```

写入：

```python
from app.langchain_structured_outputs.demo_json_output_parser import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
JsonOutputParser 会把模型输出解析成 Python dict。

它比 StrOutputParser 更进一步。

但是 JsonOutputParser 只保证解析成 JSON 对象。

它不一定能帮你做完整业务字段校验。

比如它能解析出：

```json
{
  "intent": "订单查询",
  "confidence": "很高"
}
```

这依然是 JSON。

但业务上不一定合法。

所以业务强结构更推荐：

```plain
PydanticOutputParser
```

---

# 十三、09｜JsonOutputParser 适合什么场景
适合：

```plain
1. 临时 JSON 输出
2. 字段结构不强
3. 探索性原型
4. 不需要严格枚举值
5. 后续自己再处理 dict
```

不适合：

```plain
1. 意图识别
2. 工具参数
3. Agent Plan
4. RAG 引用
5. 需要强校验的业务流程
```

---

## 【重点内容】
JsonOutputParser 适合轻量场景。

但是如果模型输出要驱动业务逻辑，比如：

```plain
是否调用工具
是否转人工
是否退款
是否执行 Agent 步骤
```

就应该用 PydanticOutputParser 或 with_structured_output。

因为这些场景需要强校验。

---

# 十四、10｜示例三：PydanticOutputParser
打开：

```plain
app/langchain_structured_outputs/demo_pydantic_output_parser.py
```

写入：

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import IntentClassificationResult


def main():
    parser = PydanticOutputParser(
        pydantic_object=IntentClassificationResult,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个电商客服意图识别器。\n"
                "你必须根据格式要求输出结构化结果。\n"
                "不要输出 Markdown，不要输出解释。\n"
                "{format_instructions}"
            ),
        ),
        (
            "human",
            "用户问题：{user_question}",
        ),
    ]).partial(
        format_instructions=parser.get_format_instructions()
    )

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    chain = prompt | model | parser

    result = chain.invoke({
        "user_question": "我的订单怎么还没发货？",
    })

    print("result type:", type(result))
    print(result.model_dump())


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_pydantic_parser.py
```

写入：

```python
from app.langchain_structured_outputs.demo_pydantic_output_parser import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc24_pydantic_parser.py
```

---

## 【重点内容】
PydanticOutputParser 是这一章最重要的 Parser。

它做两件事。

第一，生成格式说明：

```python
parser.get_format_instructions()
```

第二，把模型输出解析成 Pydantic 对象：

```plain
模型输出
 ↓
PydanticOutputParser
 ↓
IntentClassificationResult
```

LangChain 参考文档说明，`PydanticOutputParser` 可以解析 LLM 输出为 Pydantic 对象，并提供 `get_format_instructions()` 返回 JSON 输出的格式说明。

---

# 十五、11｜PydanticOutputParser 和第 17 章手写 parser 对比
| 对比项 | 第 17 章手写 parser | LangChain PydanticOutputParser |
| --- | --- | --- |
| JSON 提取 | 自己写 `extract_json_text` | Parser 内部处理一部分 |
| 格式说明 | 自己写 Prompt 示例 | `get_format_instructions()` |
| Pydantic 校验 | `model_validate_json()` | Parser 调用 Pydantic |
| LCEL 组合 | 自己编排 | `prompt |
| 异常类型 | 自定义异常 | OutputParserException 等 |
| 可控性 | 高 | 更标准、更省代码 |
| 兼容性 | 完全自己控制 | 依赖 LangChain 行为 |


---

## 【重点内容】
PydanticOutputParser 不是魔法。

它本质上还是：

```plain
让模型按格式输出
再用 Pydantic 校验
```

只不过 LangChain 帮我们封装了格式说明和解析流程。

真实项目里，我建议保留我们自己的 StructuredOutputService。

只是底层解析能力可以替换为 PydanticOutputParser。

这样业务层仍然稳定。

---

# 十六、12｜为什么还需要 Prompt 约束
有了 Parser，也不能省 Prompt。

错误想法：

```plain
反正 parser 会校验，Prompt 随便写
```

正确做法：

```plain
Prompt 明确要求结构化输出
Parser 负责解析和校验
失败后做重试或兜底
```

---

## 【重点内容】
结构化输出是三层配合。

第一层：

```plain
Prompt 约束
```

告诉模型要输出什么。

第二层：

```plain
模型结构化能力
```

比如 JSON mode 或 provider 原生 structured output。

第三层：

```plain
Pydantic 校验
```

后端兜底。

这三层不能只靠一层。

---

# 十七、13｜示例四：with_structured_output
打开：

```plain
app/langchain_structured_outputs/demo_with_structured_output.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import IntentClassificationResult


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    structured_model = model.with_structured_output(
        IntentClassificationResult
    )

    result = structured_model.invoke([
        SystemMessage(
            content=(
                "你是一个电商客服意图识别器。\n"
                "请根据用户问题输出结构化分类结果。"
            )
        ),
        HumanMessage(
            content="我的订单怎么还没发货？"
        ),
    ])

    print("result type:", type(result))
    print(result.model_dump())


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_with_structured_output.py
```

写入：

```python
from app.langchain_structured_outputs.demo_with_structured_output import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
with_structured_output 的写法更直接：

```python
structured_model = model.with_structured_output(IntentClassificationResult)
```

然后：

```python
result = structured_model.invoke(messages)
```

返回结果就是 Pydantic 对象。

`ChatOpenAI.with_structured_output()` 参考文档把它描述为把模型包装成返回匹配给定 schema 的输出；schema 可以是 Pydantic 类、TypedDict、JSON Schema 或 OpenAI function schema 等形式，具体支持取决于模型和方法。

---

# 十八、14｜with_structured_output 的注意事项
## 【重点内容】
with_structured_output 很好用，但要注意几个点。

第一，不同模型支持情况不一样。

OpenAI 官方模型支持的结构化能力，和其他 OpenAI-compatible 服务不一定完全一致。

第二，有些 provider 对 JSON Schema、tool calling、json_object 的支持细节不同。

第三，课程中我们用 DeepSeek / Qwen / OpenAI 都可能通过 ChatOpenAI 接入，但不代表所有结构化输出方法都完全等价。

所以真实项目里建议：

```plain
优先写一个统一 Service
先尝试 with_structured_output
失败时 fallback 到 PydanticOutputParser
```

这样兼容性更好。

---

# 十九、15｜Parser 方案 vs with_structured_output 方案
| 对比项 | Parser 方案 | with_structured_output |
| --- | --- | --- |
| 组合方式 | `prompt | model |
| Prompt 控制 | 强 | 中等 |
| 格式说明 | parser 生成 | provider / model 处理 |
| 模型支持依赖 | 相对低 | 相对高 |
| 兼容 OpenAI-compatible | 通常更稳 | 取决于服务商 |
| 返回对象 | Parser 解析后返回 | 模型 wrapper 直接返回 |
| 适合场景 | 兼容性优先、可控性优先 | 模型原生支持、快速开发 |
| 失败修复 | 自己更容易控制 | 需要外层兜底 |


---

## 【重点内容】
我建议学员这样理解：

```plain
PydanticOutputParser
更像通用方案

with_structured_output
更像模型能力优先方案
```

课程中两种都要掌握。

项目里可以同时支持。

---

# 二十、16｜实现意图识别结构化输出
打开：

```plain
app/langchain_structured_outputs/demo_intent_classification.py
```

写入：

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import IntentClassificationResult


def build_intent_chain():
    parser = PydanticOutputParser(
        pydantic_object=IntentClassificationResult,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个电商客服意图识别器。\n"
                "\n"
                "你需要识别用户问题属于哪一类意图。\n"
                "不要输出 Markdown，不要输出解释性文字。\n"
                "\n"
                "{format_instructions}"
            ),
        ),
        (
            "human",
            "用户问题：{user_question}",
        ),
    ]).partial(
        format_instructions=parser.get_format_instructions()
    )

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    return prompt | model | parser


def main():
    chain = build_intent_chain()

    questions = [
        "我的订单怎么还没发货？",
        "我想退款，怎么操作？",
        "这个商品有黑色吗？",
        "我要找人工客服。",
        "你好，今天天气不错。",
    ]

    for question in questions:
        result = chain.invoke({
            "user_question": question,
        })

        print("question:", question)
        print(result.model_dump())
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_intent.py
```

写入：

```python
from app.langchain_structured_outputs.demo_intent_classification import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个意图识别就是电商客服项目最常用的结构化输出。

它可以帮助系统判断：

```plain
用户是查订单
还是退款
还是问商品
还是要转人工
```

然后后端根据结构化结果决定下一步。

比如：

```python
if result.intent == "query_order" and result.need_order_id:
    return "请提供订单号"
```

这就是结构化输出驱动业务流程。

---

# 二十一、17｜实现 RAG 结构化回答
打开：

```plain
app/langchain_structured_outputs/demo_rag_structured_answer.py
```

写入：

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import RAGAnswerResult


def build_rag_answer_chain():
    parser = PydanticOutputParser(
        pydantic_object=RAGAnswerResult,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个企业知识库问答助手。\n"
                "\n"
                "回答规则：\n"
                "1. 只能基于提供的知识库片段回答。\n"
                "2. 如果知识库片段没有答案，is_answered 必须为 false。\n"
                "3. citations 只能包含知识库片段中出现的 document_id。\n"
                "4. 不要编造引用。\n"
                "5. 不要输出 Markdown，不要输出额外解释。\n"
                "\n"
                "{format_instructions}\n"
                "\n"
                "知识库片段：\n"
                "{retrieved_context}"
            ),
        ),
        (
            "human",
            "用户问题：{user_question}",
        ),
    ]).partial(
        format_instructions=parser.get_format_instructions()
    )

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    return prompt | model | parser


def main():
    chain = build_rag_answer_chain()

    result = chain.invoke({
        "user_question": "员工年假有几天？",
        "retrieved_context": (
            "[doc_001] 员工入职满一年后，每年享有 5 天带薪年假。\n"
            "[doc_002] 年假申请需要提前 3 个工作日提交。"
        ),
    })

    print(result.model_dump())


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_rag_answer.py
```

写入：

```python
from app.langchain_structured_outputs.demo_rag_structured_answer import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
RAG 结构化回答比普通文本回答更适合企业知识库。

因为它不仅有：

```plain
answer
```

还有：

```plain
is_answered
citations
missing_info
confidence
```

这样前端可以展示引用来源。

后端也可以判断：

```plain
这次回答有没有基于知识库
有没有引用文档
置信度是否太低
```

这对企业级 RAG 很重要。

---

# 二十二、18｜实现 Agent Plan 结构化输出
打开：

```plain
app/langchain_structured_outputs/demo_agent_plan.py
```

写入：

```python
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import AgentPlanResult


def build_agent_plan_chain():
    parser = PydanticOutputParser(
        pydantic_object=AgentPlanResult,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个 AI Agent 任务规划器。\n"
                "\n"
                "你需要根据用户目标、可用工具和约束条件，规划执行步骤。\n"
                "\n"
                "规则：\n"
                "1. 只能使用 available_tools 中列出的工具。\n"
                "2. 不要编造不存在的工具。\n"
                "3. 如果需要高风险操作，need_human_confirm 必须为 true。\n"
                "4. 如果信息不足，要规划 ask_user 步骤。\n"
                "5. 不要输出 Markdown，不要输出额外解释。\n"
                "\n"
                "{format_instructions}\n"
                "\n"
                "可用工具：\n"
                "{available_tools}\n"
                "\n"
                "约束条件：\n"
                "{constraints}"
            ),
        ),
        (
            "human",
            "用户目标：{user_goal}",
        ),
    ]).partial(
        format_instructions=parser.get_format_instructions()
    )

    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    return prompt | model | parser


def main():
    chain = build_agent_plan_chain()

    result = chain.invoke({
        "user_goal": "帮用户查询订单 10001 的物流状态，并生成客服回复。",
        "available_tools": (
            "query_order(order_id: string)：根据订单号查询订单和物流状态。\n"
            "transfer_human(reason: string)：转人工客服。"
        ),
        "constraints": "不能编造物流信息；只能调用已提供的工具。",
    })

    print(result.model_dump())


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc24_agent_plan.py
```

写入：

```python
from app.langchain_structured_outputs.demo_agent_plan import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
Agent Plan 是后面 LangGraph 的基础。

模型不能只说：

```plain
我会先查订单，再回复用户。
```

它要输出结构化步骤。

比如：

```json
{
  "need_tools": true,
  "steps": [
    {
      "step_id": 1,
      "action_type": "tool_call",
      "tool_name": "query_order",
      "arguments": {
        "order_id": "10001"
      }
    }
  ]
}
```

这样程序才能执行。

这就是 Agent 从“会聊天”变成“可执行”的关键。

---

# 二十三、19｜结构化输出失败会发生什么
模型可能输出：

```plain
好的，下面是结果：
{
  "intent": "query_order"
}
```

或者：

```json
{
  "intent": "订单查询",
  "confidence": "很高"
}
```

或者输出半截 JSON：

```json
{
  "intent": "query_order",
  "confidence":
```

这些都会导致解析失败。

LangChain 的 Pydantic parser 相关文档提到，解析失败会抛出可以捕获并用于修复处理的 `OutputParserException`。

---

## 【重点内容】
结构化输出不是 100% 稳定。

即使你用了 Parser，也可能失败。

所以真实项目一定要有：

```plain
解析失败日志
重试
修复 Prompt
兜底响应
告警
```

不能因为用了 LangChain，就假设模型永远输出正确。

---

# 二十四、20｜实现结构化输出修复重试
打开：

```plain
app/langchain_structured_outputs/retry.py
```

写入：

```python
from pydantic import BaseModel

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.langchain_models.model_factory import LangChainModelFactory


async def parse_with_repair(
    raw_text: str,
    schema: type[BaseModel],
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
):
    parser = PydanticOutputParser(
        pydantic_object=schema,
    )

    try:
        return parser.parse(raw_text)

    except Exception as first_error:
        repair_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    "你是一个 JSON 修复器。\n"
                    "你的任务是把用户提供的内容修复为符合目标 Schema 的合法 JSON。\n"
                    "只能输出 JSON，不要输出 Markdown，不要输出解释。\n"
                    "\n"
                    "{format_instructions}"
                ),
            ),
            (
                "human",
                (
                    "原始输出：\n"
                    "{raw_text}\n"
                    "\n"
                    "解析错误：\n"
                    "{error_message}\n"
                    "\n"
                    "请修复。"
                ),
            ),
        ]).partial(
            format_instructions=parser.get_format_instructions()
        )

        model = LangChainModelFactory.create(
            provider=provider,
            model=model_name,
            temperature=0,
        )

        repair_chain = repair_prompt | model | parser

        return await repair_chain.ainvoke({
            "raw_text": raw_text,
            "error_message": repr(first_error),
        })
```

---

## 【重点内容】
这个函数做了一个修复重试。

第一步：

```plain
先用 parser.parse(raw_text)
```

如果成功，直接返回。

如果失败，就把：

```plain
原始输出
解析错误
格式说明
```

发给模型，让它修复成合法 JSON。

注意这里最多修复一次。

真实项目不要无限重试。

因为重试也有成本和延迟。

---

# 二十五、21｜创建 LangChainStructuredOutputService
打开：

```plain
app/langchain_structured_outputs/service.py
```

写入：

```python
from pydantic import BaseModel

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_structured_outputs.schemas import (
    AgentPlanResult,
    IntentClassificationResult,
    RAGAnswerResult,
)
from app.langchain_structured_outputs.retry import parse_with_repair


logger = get_logger(__name__)


class LangChainStructuredOutputService:
    async def classify_intent(
        self,
        user_question: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> IntentClassificationResult:
        return await self._run_pydantic_chain(
            schema=IntentClassificationResult,
            provider=provider,
            model_name=model_name,
            task_name="intent_classification",
            system_prompt=(
                "你是一个电商客服意图识别器。\n"
                "你需要识别用户问题属于哪一类意图。\n"
                "不要输出 Markdown，不要输出解释性文字。"
            ),
            human_template="用户问题：{user_question}",
            variables={
                "user_question": user_question,
            },
        )

    async def generate_rag_answer(
        self,
        user_question: str,
        retrieved_context: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> RAGAnswerResult:
        return await self._run_pydantic_chain(
            schema=RAGAnswerResult,
            provider=provider,
            model_name=model_name,
            task_name="rag_structured_answer",
            system_prompt=(
                "你是一个企业知识库问答助手。\n"
                "只能基于提供的知识库片段回答。\n"
                "如果知识库没有答案，is_answered 必须为 false。\n"
                "citations 只能包含知识库片段中出现的 document_id。\n"
                "不要编造引用。\n"
                "\n"
                "知识库片段：\n"
                "{retrieved_context}"
            ),
            human_template="用户问题：{user_question}",
            variables={
                "user_question": user_question,
                "retrieved_context": retrieved_context,
            },
        )

    async def plan_agent_task(
        self,
        user_goal: str,
        available_tools: str,
        constraints: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> AgentPlanResult:
        return await self._run_pydantic_chain(
            schema=AgentPlanResult,
            provider=provider,
            model_name=model_name,
            task_name="agent_plan",
            system_prompt=(
                "你是一个 AI Agent 任务规划器。\n"
                "只能使用 available_tools 中列出的工具。\n"
                "不要编造不存在的工具。\n"
                "如果信息不足，要规划 ask_user 步骤。\n"
                "如果需要高风险操作，need_human_confirm 必须为 true。\n"
                "\n"
                "可用工具：\n"
                "{available_tools}\n"
                "\n"
                "约束条件：\n"
                "{constraints}"
            ),
            human_template="用户目标：{user_goal}",
            variables={
                "user_goal": user_goal,
                "available_tools": available_tools,
                "constraints": constraints,
            },
        )

    async def _run_pydantic_chain(
        self,
        schema: type[BaseModel],
        provider: str,
        model_name: str,
        task_name: str,
        system_prompt: str,
        human_template: str,
        variables: dict,
    ):
        parser = PydanticOutputParser(
            pydantic_object=schema,
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                (
                    system_prompt
                    + "\n\n"
                    + "你必须严格按照下面格式输出。\n"
                    + "不要输出 Markdown，不要输出额外解释。\n"
                    + "{format_instructions}"
                ),
            ),
            (
                "human",
                human_template,
            ),
        ]).partial(
            format_instructions=parser.get_format_instructions()
        )

        model = LangChainModelFactory.create(
            provider=provider,
            model=model_name,
            temperature=0,
        )

        chain = prompt | model | parser

        logger.info(
            f"langchain_structured_output_start task={task_name} "
            f"schema={schema.__name__} model={model_name}"
        )

        try:
            result = await chain.ainvoke(variables)

        except Exception as exc:
            logger.warning(
                f"langchain_structured_output_parse_failed "
                f"task={task_name} error={repr(exc)}"
            )

            raise AppException(
                message="LangChain 结构化输出解析失败",
                code=ErrorCode.STRUCTURED_OUTPUT_PARSE_FAILED,
                status_code=500,
                data={
                    "task": task_name,
                    "schema": schema.__name__,
                    "error": repr(exc),
                },
            ) from exc

        logger.info(
            f"langchain_structured_output_success task={task_name} "
            f"schema={schema.__name__}"
        )

        return result

    async def parse_or_repair(
        self,
        raw_text: str,
        schema: type[BaseModel],
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ):
        return await parse_with_repair(
            raw_text=raw_text,
            schema=schema,
            provider=provider,
            model_name=model_name,
        )


langchain_structured_output_service = LangChainStructuredOutputService()
```

---

## 【重点内容】
这个 Service 是本章核心。

它保留了第 17 章的服务化思路。

但底层换成了 LangChain：

```plain
ChatPromptTemplate
PydanticOutputParser
Prompt | Model | Parser
```

业务层调用：

```python
classify_intent(...)
generate_rag_answer(...)
plan_agent_task(...)
```

拿到的仍然是 Pydantic 对象。

这就是迁移的关键：

上层业务不变，底层实现逐步替换成 LangChain。

---

# 二十六、22｜为什么 Service 里还要自己封装
## 【重点内容】
有同学可能会问：

既然 LangChain 可以直接 prompt | model | parser，为什么还要 Service？

原因很简单。

真实项目里，业务不应该到处写 chain。

如果到处写：

```python
chain = prompt | model | parser
```

会导致：

```plain
Prompt 分散
Schema 分散
日志分散
错误处理分散
重试逻辑分散
模型选择分散
```

所以我们保留：

```plain
LangChainStructuredOutputService
```

把结构化输出统一管理起来。

LangChain 负责底层编排。

Service 负责业务入口和工程治理。

---

# 二十七、23｜创建结构化输出 API
创建：

```plain
app/api/v1/langchain_structured_outputs.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.langchain_structured_outputs.schemas import (
    AgentPlanResult,
    IntentClassificationResult,
    RAGAnswerResult,
)
from app.langchain_structured_outputs.service import (
    langchain_structured_output_service,
)


router = APIRouter()


class LCIntentRequest(BaseModel):
    question: str = Field(..., min_length=1)
    provider: str = Field(default="deepseek")
    model: str = Field(default="deepseek-chat")


class LCRAGAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1)
    retrieved_context: str = Field(..., min_length=1)
    provider: str = Field(default="deepseek")
    model: str = Field(default="deepseek-chat")


class LCAgentPlanRequest(BaseModel):
    goal: str = Field(..., min_length=1)
    available_tools: str = Field(..., min_length=1)
    constraints: str = Field(default="无")
    provider: str = Field(default="deepseek")
    model: str = Field(default="deepseek-chat")


@router.post(
    "/langchain/structured/intent",
    response_model=ApiResponse[IntentClassificationResult],
)
async def classify_intent(
    request: LCIntentRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[IntentClassificationResult]:
    result = await langchain_structured_output_service.classify_intent(
        user_question=request.question,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[IntentClassificationResult](
        data=result
    )


@router.post(
    "/langchain/structured/rag-answer",
    response_model=ApiResponse[RAGAnswerResult],
)
async def rag_answer(
    request: LCRAGAnswerRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[RAGAnswerResult]:
    result = await langchain_structured_output_service.generate_rag_answer(
        user_question=request.question,
        retrieved_context=request.retrieved_context,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[RAGAnswerResult](
        data=result
    )


@router.post(
    "/langchain/structured/agent-plan",
    response_model=ApiResponse[AgentPlanResult],
)
async def agent_plan(
    request: LCAgentPlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[AgentPlanResult]:
    result = await langchain_structured_output_service.plan_agent_task(
        user_goal=request.goal,
        available_tools=request.available_tools,
        constraints=request.constraints,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[AgentPlanResult](
        data=result
    )
```

---

# 二十八、24｜注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langchain_structured_outputs import (
    router as langchain_structured_outputs_router,
)
```

注册：

```python
api_router.include_router(
    langchain_structured_outputs_router,
    tags=["LangChain Structured Outputs"],
)
```

---

# 二十九、25｜测试意图识别接口
启动项目：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/structured/intent" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "我的订单怎么还没发货？",
    "provider": "deepseek",
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
    "reason": "用户询问订单发货状态，但没有提供订单号，需要先引导用户提供订单号。"
  },
  "trace_id": null
}
```

---

# 三十、26｜测试 RAG 结构化回答接口
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/structured/rag-answer" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "员工年假有几天？",
    "retrieved_context": "[doc_001] 员工入职满一年后，每年享有 5 天带薪年假。",
    "provider": "deepseek",
    "model": "deepseek-chat"
  }'
```

预期：

```json
{
  "data": {
    "answer": "员工入职满一年后，每年享有 5 天带薪年假。",
    "is_answered": true,
    "citations": ["doc_001"],
    "missing_info": null,
    "confidence": 0.9
  }
}
```

---

# 三十一、27｜测试 Agent Plan 接口
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/structured/agent-plan" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "goal": "帮用户查询订单 10001 的物流状态，并生成客服回复。",
    "available_tools": "query_order(order_id: string)：根据订单号查询订单和物流状态。transfer_human(reason: string)：转人工客服。",
    "constraints": "不能编造物流信息；只能调用已提供的工具。",
    "provider": "deepseek",
    "model": "deepseek-chat"
  }'
```

预期：

```json
{
  "data": {
    "goal": "帮用户查询订单 10001 的物流状态，并生成客服回复。",
    "need_tools": true,
    "need_human_confirm": false,
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
      }
    ],
    "final_response_style": "customer_service"
  }
}
```

---

# 三十二、28｜项目一如何接入 LangChain Structured Output
第 19 章项目里，我们可以这样用：

```plain
ChatService
 ↓
先调用 classify_intent
 ↓
根据 intent 决定是否走 Tool Calling
 ↓
否则走普通 Chat
```

示例：

```python
intent_result = await langchain_structured_output_service.classify_intent(
    user_question=latest_user_message,
    provider="deepseek",
    model_name=model,
)

if intent_result.intent == "query_order" and intent_result.need_order_id:
    return ChatResponse(
        answer="请提供您的订单号，我帮您查询订单状态。",
        model=model,
        session_id=request.session_id,
        metadata={
            "intent": intent_result.model_dump(),
        },
    )

if intent_result.reply_strategy == "transfer_human":
    return ChatResponse(
        answer="这个问题建议为您转接人工客服处理。",
        model=model,
        session_id=request.session_id,
        metadata={
            "intent": intent_result.model_dump(),
        },
    )
```

---

## 【重点内容】
这个接入思路非常实用。

结构化输出不是为了展示 JSON。

它是为了驱动业务决策。

比如：

```plain
用户缺订单号
直接追问订单号

用户要人工
直接转人工

用户是普通咨询
继续走大模型回答

用户是订单查询并提供了订单号
走 Tool Calling
```

这就是 AI Chat 项目升级成客服 Agent 的关键。

---

# 三十三、29｜结构化输出和 Tool Calling 的关系
## 【重点内容】
结构化输出和 Tool Calling 很像，但不要混淆。

结构化输出解决：

```plain
模型输出一个结构化判断结果
```

比如：

```json
{
  "intent": "query_order",
  "need_order_id": true
}
```

Tool Calling 解决：

```plain
模型选择一个工具，并生成工具参数
```

比如：

```json
{
  "tool_name": "query_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

真实项目里，两者可以组合：

```plain
先结构化识别意图
再决定是否启用工具
```

这样比所有请求都直接暴露 tools 更安全。

---

# 三十四、30｜结构化输出和 RAG 的关系
RAG 结构化输出推荐包含：

```plain
answer
is_answered
citations
missing_info
confidence
```

---

## 【重点内容】
RAG 不建议只返回一段答案。

企业知识库更需要知道：

```plain
回答是否来自知识库
引用了哪些文档
是否缺少信息
置信度如何
```

所以后面第 39 章开始讲 RAG 时，会继续使用这一章的 RAGAnswerResult。

---

# 三十五、31｜结构化输出和 Agent Plan 的关系
Agent Plan 推荐包含：

```plain
goal
need_tools
need_human_confirm
steps
final_response_style
```

---

## 【重点内容】
Agent Plan 是 LangGraph 的前置基础。

LangGraph 会把流程拆成：

```plain
State
Node
Edge
Conditional Routing
```

而结构化 Agent Plan 可以告诉系统：

```plain
下一步该思考
该调用工具
该追问用户
还是需要人工确认
```

所以 Structured Output 是 Agent 可控性的基础。

---

# 三十六、32｜为什么结构化输出不建议盲目流式
## 【重点内容】
结构化输出一般不建议盲目流式。

因为 JSON 没完整生成之前，没法稳定解析。

比如流式输出到一半：

```json
{
  "intent": "query_order",
```

这时候不是合法 JSON。

所以结构化输出更适合非流式。

如果做 Agent 流式，可以这样：

```plain
每个事件是完整 JSON
```

比如：

```plain
event: step
data: {"step_id": 1, "status": "running"}
```

而不是把一个大 JSON 拆成半截半截发。

---

# 三十七、33｜常见错误一：以为 Parser 可以保证模型一定正确
错误理解：

```plain
用了 PydanticOutputParser，模型就一定会输出合法 JSON
```

正确理解：

```plain
Parser 负责解析和校验
但模型仍然可能输出不合法内容
```

---

## 【重点内容】
Parser 不是控制模型的绝对开关。

它只是：

```plain
告诉模型格式要求
并在后端校验输出
```

如果模型不遵守，还是会解析失败。

所以要有重试和兜底。

---

# 三十八、34｜常见错误二：忘记插入 format_instructions
错误：

```python
parser = PydanticOutputParser(pydantic_object=IntentClassificationResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是意图识别器。"),
    ("human", "{user_question}"),
])
```

正确：

```python
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "你是意图识别器。\n{format_instructions}",
    ),
    ("human", "{user_question}"),
]).partial(
    format_instructions=parser.get_format_instructions()
)
```

---

# 三十九、35｜常见错误三：Schema 字段太复杂
字段太多会导致模型更容易出错。

不推荐一开始就定义：

```plain
20 个字段
5 层嵌套
大量自由文本
复杂 list
多层 dict
```

推荐先定义最小可用结构：

```plain
intent
confidence
reason
```

跑稳定后再扩展。

---

# 四十、36｜常见错误四：枚举值没有限制
不推荐：

```python
intent: str
```

推荐：

```python
intent: Literal[
    "query_order",
    "refund",
    "logistics",
    "other",
]
```

---

## 【重点内容】
业务字段要稳定。

如果 intent 是普通字符串，模型可能输出：

```plain
订单查询
queryOrder
order_query
查订单
```

程序就不好判断。

所以用 Literal 限定枚举值。

---

# 四十一、37｜常见错误五：把结构化输出直接执行
模型输出：

```json
{
  "action_type": "tool_call",
  "tool_name": "refund_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

不能直接执行退款。

必须检查：

```plain
用户权限
订单归属
订单状态
金额限制
风控规则
是否需要人工确认
```

---

# 四十二、38｜常见错误六：with_structured_output 不兼容就直接放弃
## 【重点内容】
有时候 with_structured_output 在某些模型或 OpenAI-compatible 服务上不好用。

不要直接放弃结构化输出。

可以 fallback 到：

```plain
PydanticOutputParser
```

也就是：

```plain
优先 provider 原生结构化能力
不行就 Prompt + Parser
```

这才是企业项目比较稳的方案。

---

# 四十三、39｜常见错误七：结构化输出日志记录太多隐私
不建议完整记录：

```plain
用户问题原文
订单号
手机号
地址
企业知识库片段
完整模型输出
```

建议记录：

```plain
task_name
schema_name
success
error_type
trace_id
model
latency
```

敏感内容做截断或脱敏。

---

# 四十四、40｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| `StrOutputParser` | 普通 Chat 文本输出 |
| `JsonOutputParser` | 第 17 章 JSON 输出 |
| `PydanticOutputParser` | 第 17 章 Pydantic 校验 |
| `get_format_instructions()` | 第 17 章 JSON 格式 Prompt |
| `with_structured_output` | 第 17 章 response_format / JSON Schema |
| `Prompt | Model |
| `IntentClassificationResult` | 电商客服意图识别 |
| `RAGAnswerResult` | 企业知识库回答 |
| `AgentPlanResult` | Agent 规划 |
| `parse_with_repair` | 第 17 章修复重试 |
| `LangChainStructuredOutputService` | 第 17 章 StructuredOutputService |
| 结构化输出决策 | 第 19 章 AI Chat 项目升级 |
| Agent Plan | 后续 LangGraph State / Routing |


---

# 四十五、41｜本章完整复习
这一章我们完成了：

```plain
1. 理解 LangChain Structured Output 的定位
2. 回顾第 17 章原生结构化输出
3. 理解 OutputParser 是什么
4. 理解 StrOutputParser
5. 理解 JsonOutputParser
6. 理解 PydanticOutputParser
7. 理解 get_format_instructions
8. 理解 Prompt | Model | Parser
9. 理解 with_structured_output
10. 对比 Parser 方案和 with_structured_output 方案
11. 创建 langchain_structured_outputs 目录
12. 定义 IntentClassificationResult
13. 定义 RAGAnswerResult
14. 定义 AgentPlanResult
15. 定义 ResumeReviewResult
16. 编写 StrOutputParser 示例
17. 编写 JsonOutputParser 示例
18. 编写 PydanticOutputParser 示例
19. 编写 with_structured_output 示例
20. 编写意图识别结构化输出
21. 编写 RAG 结构化回答
22. 编写 Agent Plan 结构化输出
23. 实现 parse_with_repair
24. 实现 LangChainStructuredOutputService
25. 创建结构化输出 API
26. 测试意图识别接口
27. 测试 RAG 结构化回答接口
28. 测试 Agent Plan 接口
29. 理解结构化输出和 Tool Calling 的关系
30. 理解结构化输出和 RAG 的关系
31. 理解结构化输出和 Agent Plan 的关系
32. 总结结构化输出常见错误
```

---

# 四十六、42｜课后任务一：跑通 StrOutputParser
要求：

```plain
1. 运行 scripts/test_lc24_str_parser.py
2. 打印 result type
3. 确认结果是 str
4. 对比不加 parser 时返回的 AIMessage
```

---

# 四十七、43｜课后任务二：跑通 PydanticOutputParser
要求：

```plain
1. 运行 scripts/test_lc24_pydantic_parser.py
2. 输入“我的订单怎么还没发货？”
3. 输出 IntentClassificationResult
4. 打印 result.model_dump()
```

---

# 四十八、44｜课后任务三：用 with_structured_output 实现意图识别
要求：

```plain
1. 使用 model.with_structured_output(IntentClassificationResult)
2. 输入用户问题
3. 打印返回对象
4. 如果当前模型不支持，记录报错，并改用 PydanticOutputParser
```

---

# 四十九、45｜课后任务四：新增内容审核结构化输出
要求定义：

```python
class ContentModerationResult(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    categories: list[str]
    action: Literal["pass", "review", "reject"]
    reason: str
```

并完成：

```plain
1. Prompt
2. Parser
3. Chain
4. 测试脚本
```

---

# 五十、46｜课后任务五：结构化输出接入 ChatService
要求：

```plain
1. ChatService 收到 ecommerce_customer_service 请求
2. 先调用 classify_intent
3. 如果 need_order_id=True，直接追问订单号
4. 如果 reply_strategy=transfer_human，返回转人工话术
5. 如果 reply_strategy=call_tool，进入 Tool Calling
6. metadata 里返回 intent 结构化结果
```

---

# 五十一、47｜课后任务六：实现结构化输出 fallback 策略
要求：

```plain
1. 优先尝试 with_structured_output
2. 如果抛异常，fallback 到 PydanticOutputParser
3. 如果 Parser 也失败，进入 repair
4. 如果 repair 仍失败，返回 AppException
```

伪代码：

```python
try:
    return await run_with_structured_output(...)
except Exception:
    try:
        return await run_with_parser(...)
    except Exception:
        return await parse_with_repair(...)
```

---

# 五十二、48｜课后任务七：画出 LangChain Structured Output 链路
画出：

```plain
POST /api/v1/langchain/structured/intent
```

完整链路：

```plain
HTTP Request
 ↓
Router
 ↓
LangChainStructuredOutputService
 ↓
PydanticOutputParser
 ↓
parser.get_format_instructions()
 ↓
ChatPromptTemplate.partial()
 ↓
Prompt | Model | Parser
 ↓
ChatModel.ainvoke()
 ↓
AIMessage
 ↓
Parser 校验
 ↓
IntentClassificationResult
 ↓
ApiResponse
```

---

# 五十三、49｜本章总结 
## 【重点内容】
好了，到这里，第 24 章我们就讲完了。

这一章我们把第 17 章手写的结构化输出，迁移到了 LangChain 体系里。

大家一定要记住，LangChain Structured Output 主要有两条路线：

```plain
第一条：
Prompt | Model | Parser

第二条：
model.with_structured_output(Schema)
```

Parser 方案更通用、更可控。

with_structured_output 更简洁，但更依赖模型和 provider 的支持。

真实企业项目里，不要只押一种方案。

推荐设计成：

```plain
with_structured_output
+
PydanticOutputParser
+
repair retry
+
AppException 兜底
```

这一章我们实现了：

```plain
StrOutputParser
JsonOutputParser
PydanticOutputParser
with_structured_output
IntentClassificationResult
RAGAnswerResult
AgentPlanResult
parse_with_repair
LangChainStructuredOutputService
结构化输出 API
```

到这里，我们的 LangChain 阶段已经完成了：

```plain
Model
Message
Prompt
Structured Output
```

下一步就是 Tool。

---


