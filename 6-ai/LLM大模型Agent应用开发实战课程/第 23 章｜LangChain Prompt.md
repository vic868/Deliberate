---

# 一、本章定位
前面我们已经完成了：

```plain
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
```

上一章我们重点讲了：

```plain
SystemMessage
HumanMessage
AIMessage
ToolMessage
ChatOpenAI
invoke
ainvoke
stream
astream
MessageAdapter
LangChainLLMProvider
```

这一章继续讲 LangChain 里的第二个核心模块：

# Prompt
也就是：

```plain
LangChain PromptTemplate
LangChain ChatPromptTemplate
MessagesPlaceholder
Prompt | Model
Prompt | Model | Parser
```

第 15 章我们已经手写了一套 Prompt 工程化：

```plain
PromptTemplate
PromptMessageTemplate
PromptRegistry
PromptService
PromptScenario
PromptVersion
```

这一章要解决的问题是：

**如何把我们自己写的 Prompt 工程化能力，和 LangChain 的 PromptTemplate 体系打通。**

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. PromptTemplate 和 ChatPromptTemplate 的区别
2. 为什么 Chat 场景优先用 ChatPromptTemplate
3. ChatPromptTemplate.from_messages 怎么用
4. system / human / ai / placeholder 分别怎么写
5. Prompt 输入变量如何校验
6. invoke 后返回的 PromptValue 是什么
7. PromptValue.messages 是什么
8. MessagesPlaceholder 如何接入历史上下文
9. MessagesPlaceholder optional=True 怎么用
10. MessagesPlaceholder n_messages 怎么用
11. partial variables 怎么用
12. Prompt metadata / tags 有什么用
13. 如何写通用聊天 Prompt
14. 如何写电商客服 Prompt
15. 如何写 RAG Prompt
16. 如何写 Agent Planner Prompt
17. 如何保留我们自己的 PromptRegistry
18. 如何把 ChatPromptTemplate 接入 PromptService
19. 如何组成 prompt | model
20. 如何组成 prompt | model | parser
21. 如何在第 19 章项目中逐步替换 PromptService
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
│   ├── langchain_prompts/
│   │   ├── __init__.py
│   │   ├── templates.py
│   │   ├── registry.py
│   │   ├── service.py
│   │   ├── demo_prompt_basic.py
│   │   ├── demo_chat_prompt_template.py
│   │   ├── demo_messages_placeholder.py
│   │   ├── demo_partial_variables.py
│   │   ├── demo_prompt_chain.py
│   │   ├── demo_prompt_parser_chain.py
│   │   └── demo_project_prompt_adapter.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc23_prompt_basic.py
│   ├── test_lc23_chat_prompt.py
│   ├── test_lc23_history_prompt.py
│   ├── test_lc23_partial_prompt.py
│   ├── test_lc23_prompt_chain.py
│   └── test_lc23_prompt_service.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 23 章。

这一章我们讲 LangChain Prompt。

第 15 章我们已经讲过 Prompt Engineering 工程化实战。

当时我们自己写了：

```plain
PromptTemplate
PromptRegistry
PromptService
PromptScenario
PromptVersion
```

这些东西的核心目的是什么？

就是不要在业务代码里到处写字符串。

比如不要在 ChatService 里直接写：

```python
system_prompt = "你是一个专业客服助手..."
```

而是把 Prompt 当成一个可管理、可版本化、可复用的工程资产。

LangChain 也提供了 PromptTemplate 体系。

它能帮我们做：

```plain
模板变量替换
Chat messages 生成
历史消息占位
Prompt 和 Model 组合
Prompt 和 Parser 组合
Prompt tracing metadata
```

所以这一章不是重新学 Prompt Engineering。

而是把我们第 15 章的 Prompt 工程化能力，迁移到 LangChain 的写法里。

---

# 六、02｜先回顾第 15 章我们手写的 PromptService
第 15 章我们大概写过类似结构：

```python
class PromptTemplate(BaseModel):
    prompt_id: str
    name: str
    scenario: PromptScenario
    version: str
    description: str
    required_variables: list[str]
    messages: list[PromptMessageTemplate]


class PromptService:
    def render_by_prompt_id(
        self,
        prompt_id: str,
        variables: dict,
    ) -> list[LLMMessage]:
        ...
```

业务里使用：

```python
messages = prompt_service.render_by_scenario(
    scenario=PromptScenario.ECOMMERCE_CUSTOMER_SERVICE,
    version="v1",
    variables={
        "user_question": latest_user_message,
        "business_rules": "不能编造订单状态。",
        "order_info": "用户提供了订单号 10001。",
    },
)
```

---

## 【重点内容】
这套设计本身没问题。

它解决了几个问题：

```plain
Prompt 不散落
Prompt 可复用
Prompt 可按场景管理
Prompt 可按版本管理
变量缺失可以提前报错
```

但是它也有一个问题：

我们自己维护了很多模板渲染、消息转换、变量处理逻辑。

现在进入 LangChain 阶段，我们可以把底层渲染能力交给：

```plain
ChatPromptTemplate
```

但是上层的：

```plain
PromptRegistry
PromptService
PromptScenario
PromptVersion
```

仍然可以保留。

这就是比较稳的改造方式。

---

# 七、03｜PromptTemplate 和 ChatPromptTemplate 的区别
## 【屏幕展示】
| 类型 | 输出 | 适合场景 |
| --- | --- | --- |
| `PromptTemplate` | 普通字符串 | 补全文本、单段 Prompt |
| `ChatPromptTemplate` | Chat messages | Chat Model、Agent、Tool Calling、RAG |
| `MessagesPlaceholder` | 插入消息列表 | 历史上下文、多轮对话、Agent 中间步骤 |


---

## 【重点内容】
LangChain 里有两类常用 Prompt。

第一类是：

```plain
PromptTemplate
```

它主要输出普通字符串。

第二类是：

```plain
ChatPromptTemplate
```

它输出的是 messages。

我们这门课主要做 Chat、RAG、Agent，所以优先使用：

```plain
ChatPromptTemplate
```

因为现代大模型 Chat API 的输入本来就是 messages。

也就是：

```plain
system
user / human
assistant / ai
tool
```

LangChain `ChatPromptTemplate.from_messages()` 可以从多种 message 格式创建聊天提示词模板，最终渲染成聊天模型可用的 PromptValue / messages。

---

# 八、04｜最小 ChatPromptTemplate 示例
打开：

```plain
app/langchain_prompts/demo_chat_prompt_template.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate


def main():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业的 AI Agent 课程助教。",
        ),
        (
            "human",
            "请用三句话解释：{topic}",
        ),
    ])

    prompt_value = prompt.invoke({
        "topic": "LangChain Prompt",
    })

    print("prompt_value type:", type(prompt_value))
    print("messages:")

    for message in prompt_value.messages:
        print(message.type, ":", message.content)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc23_chat_prompt.py
```

写入：

```python
from app.langchain_prompts.demo_chat_prompt_template import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc23_chat_prompt.py
```

---

## 【重点内容】
这个例子是最小 ChatPromptTemplate。

它有两个 message：

```plain
system
human
```

里面的：

```plain
{topic}
```

就是变量。

调用：

```python
prompt.invoke({"topic": "LangChain Prompt"})
```

以后，LangChain 会把变量填进去，生成 messages。

注意，这一步还没有调用模型。

Prompt 只是负责生成 messages。

---

# 九、05｜PromptValue 是什么
`ChatPromptTemplate.invoke()` 返回的不是 list，也不是字符串，而是：

```plain
ChatPromptValue
```

它里面有：

```python
prompt_value.messages
```

也可以转成字符串：

```python
prompt_value.to_string()
```

---

## 【重点内容】
很多同学第一次会困惑：

```python
prompt.invoke(...)
```

返回的到底是什么？

它返回的是 PromptValue。

对 ChatPromptTemplate 来说，通常是 ChatPromptValue。

它里面最重要的是：

```python
prompt_value.messages
```

这些 messages 才会传给 ChatModel。

所以流程是：

```plain
ChatPromptTemplate
 ↓
PromptValue
 ↓
messages
 ↓
ChatModel
```

---

# 十、06｜Prompt 输入变量
打开：

```plain
app/langchain_prompts/demo_prompt_basic.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate


def main():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业的 {role_name}。"),
        ("human", "请回答用户问题：{user_question}"),
    ])

    print("input_variables:", prompt.input_variables)
    print("optional_variables:", prompt.optional_variables)
    print("partial_variables:", prompt.partial_variables)

    prompt_value = prompt.invoke({
        "role_name": "AI Agent 课程助教",
        "user_question": "为什么 Prompt 需要工程化管理？",
    })

    for message in prompt_value.messages:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc23_prompt_basic.py
```

写入：

```python
from app.langchain_prompts.demo_prompt_basic import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
Prompt 里出现的变量，LangChain 会自动识别成：

```python
input_variables
```

比如这里有：

```plain
role_name
user_question
```

如果 invoke 的时候少传变量，就会报错。

这比手写字符串替换更安全。

LangChain 的 PromptTemplate / ChatPromptTemplate 参考文档中也列出了 `input_variables`、`optional_variables`、`partial_variables`、`metadata`、`tags` 等属性。

---

# 十一、07｜变量缺失会发生什么
错误示例：

```python
prompt.invoke({
    "user_question": "为什么需要 LangChain？",
})
```

少传了：

```plain
role_name
```

会报类似错误：

```plain
KeyError / missing variables
```

---

## 【重点内容】
变量缺失是 Prompt 工程里很常见的问题。

比如模板里写了：

```plain
{business_rules}
```

但是业务层忘记传。

如果是手写字符串，可能到了运行时才发现。

LangChain 会根据 input_variables 做校验。

这能提前发现问题。

---

# 十二、08｜MessagesPlaceholder：接入历史消息
## 【屏幕展示】
```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业 AI 助手。"),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])
```

---

## 【重点内容】
MessagesPlaceholder 是 ChatPromptTemplate 里非常重要的能力。

它解决的是：

```plain
历史消息怎么插入 Prompt
```

比如多轮对话里，Prompt 不是只有当前问题。

还要有历史上下文：

```plain
用户上一轮问了什么
AI 上一轮回答了什么
用户当前又问了什么
```

`MessagesPlaceholder` 就是给历史消息留一个位置。

LangChain 参考文档说明，`MessagesPlaceholder` 假设传入变量本身已经是 message 列表；它也可以设置 `optional=True`，没有历史时返回空列表，还可以用 `n_messages` 限制保留的消息数量。

---

# 十三、09｜MessagesPlaceholder 示例
打开：

```plain
app/langchain_prompts/demo_messages_placeholder.py
```

写入：

```python
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def main():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个专业 AI Agent 课程助教。",
        ),
        MessagesPlaceholder(
            variable_name="history",
            optional=True,
        ),
        (
            "human",
            "{user_question}",
        ),
    ])

    history = [
        HumanMessage(content="什么是 AI Agent？"),
        AIMessage(content="AI Agent 是可以理解目标、规划步骤并调用工具的智能体。"),
    ]

    prompt_value = prompt.invoke({
        "history": history,
        "user_question": "那 LangChain 和 AI Agent 有什么关系？",
    })

    for message in prompt_value.messages:
        print(message.type, ":", message.content)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc23_history_prompt.py
```

写入：

```python
from app.langchain_prompts.demo_messages_placeholder import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子里，Prompt 顺序是：

```plain
SystemMessage
历史 HumanMessage
历史 AIMessage
当前 HumanMessage
```

这就是多轮对话的基本结构。

注意：

```python
optional=True
```

表示 history 可以不传。

如果没有历史消息，也不会报错。

这对新会话很有用。

---

# 十四、10｜限制历史消息数量：n_messages
示例：

```python
MessagesPlaceholder(
    variable_name="history",
    optional=True,
    n_messages=6,
)
```

---

## 【重点内容】
历史消息不能无限塞进 Prompt。

因为上下文有 token 限制，也有成本。

所以可以用：

```plain
n_messages
```

限制最多插入几条历史消息。

比如只保留最近 6 条：

```plain
Human
AI
Human
AI
Human
AI
```

这和第 19 章课后任务里的“查询最近 10 条历史消息”是一致的。

区别是：

```plain
数据库负责查历史
MessagesPlaceholder 负责把历史插入 Prompt
```

---

# 十五、11｜partial variables：固定部分变量
## 示例
```python
prompt = prompt.partial(
    role_name="AI Agent 课程助教",
)
```

调用时只需要传：

```python
prompt.invoke({
    "user_question": "为什么需要 LangChain？"
})
```

---

## 【重点内容】
partial variables 用于提前固定一部分变量。

比如这个 Prompt 每次都要传：

```plain
role_name
```

但它其实一直是：

```plain
AI Agent 课程助教
```

那就可以用 partial 固定住。

这样业务层只传真正变化的变量。

LangChain 的 `partial()` 方法和 `partial_variables` 属性就是用于这类部分填充场景；官方参考文档也展示了模板中部分变量先被填充，剩余变量后续再传入的用法。

---

# 十六、12｜partial variables 示例
打开：

```plain
app/langchain_prompts/demo_partial_variables.py
```

写入：

```python
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate


def main():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个专业的 {role_name}。\n"
                "当前日期：{current_date}\n"
                "回答要求：{answer_style}"
            ),
        ),
        (
            "human",
            "{user_question}",
        ),
    ])

    prompt = prompt.partial(
        role_name="AI Agent 课程助教",
        current_date=datetime.now().strftime("%Y-%m-%d"),
        answer_style="口语化、结构清晰、不要编造。",
    )

    print("input_variables:", prompt.input_variables)
    print("partial_variables:", prompt.partial_variables)

    prompt_value = prompt.invoke({
        "user_question": "为什么 Prompt 需要版本管理？",
    })

    for message in prompt_value.messages:
        print(message.type, ":", message.content)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc23_partial_prompt.py
```

写入：

```python
from app.langchain_prompts.demo_partial_variables import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
大家看，partial 以后，Prompt 的 input_variables 会减少。

因为：

```plain
role_name
current_date
answer_style
```

已经被固定了。

业务层只需要传：

```plain
user_question
```

这对企业 Prompt 很实用。

比如系统角色、输出风格、当前产品名称、业务规则版本，都可以 partial。

---

# 十七、13｜Prompt metadata 和 tags
示例：

```python
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "你是一个专业 AI 助手。"),
        ("human", "{question}"),
    ],
    metadata={
        "prompt_id": "general_chat",
        "version": "v1",
    },
    tags=[
        "general_chat",
        "v1",
    ],
)
```

---

## 【重点内容】
metadata 和 tags 主要用于 tracing 和调试。

比如后面接 LangSmith 或自建 callback 时，可以知道：

```plain
这次调用用了哪个 prompt_id
用了哪个 version
属于哪个 scenario
```

这和我们第 15 章讲的 Prompt 版本管理是一致的。

Prompt 不是一段匿名字符串。

Prompt 应该有：

```plain
id
name
scenario
version
metadata
```

---

# 十八、14｜创建 LangChain Prompt 模板
现在创建：

```plain
app/langchain_prompts/templates.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


GENERAL_CHAT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个专业、耐心、表达清晰的 AI 助手。\n"
                "\n"
                "回答要求：\n"
                "1. 使用中文回答。\n"
                "2. 先给结论，再解释原因。\n"
                "3. 不要编造事实。\n"
                "4. 如果不确定，要明确说明不确定。\n"
                "5. 面向学习者时，尽量用口语化方式解释。"
            ),
        ),
        MessagesPlaceholder(
            variable_name="history",
            optional=True,
            n_messages=10,
        ),
        (
            "human",
            "{user_question}",
        ),
    ],
    metadata={
        "prompt_id": "general_chat",
        "version": "v1",
        "scenario": "general_chat",
    },
    tags=[
        "general_chat",
        "v1",
    ],
)


ECOMMERCE_CUSTOMER_SERVICE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个跨境电商平台的智能客服助手。\n"
                "\n"
                "核心规则：\n"
                "1. 用户询问订单、物流、发货、退款时，不要编造状态。\n"
                "2. 如果需要真实订单信息，应该通过工具查询。\n"
                "3. 如果用户没有提供订单号，要先引导用户提供订单号。\n"
                "4. 如果问题超出客服范围，要建议转人工。\n"
                "5. 回复要礼貌、简洁、可执行。\n"
                "\n"
                "业务规则：\n"
                "{business_rules}\n"
                "\n"
                "已知订单信息：\n"
                "{order_info}"
            ),
        ),
        MessagesPlaceholder(
            variable_name="history",
            optional=True,
            n_messages=10,
        ),
        (
            "human",
            "{user_question}",
        ),
    ],
    metadata={
        "prompt_id": "ecommerce_customer_service",
        "version": "v1",
        "scenario": "ecommerce_customer_service",
    },
    tags=[
        "ecommerce_customer_service",
        "v1",
    ],
)


RAG_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个企业知识库问答助手。\n"
                "\n"
                "回答规则：\n"
                "1. 只能基于提供的知识库片段回答。\n"
                "2. 如果知识库没有相关内容，直接说明无法从知识库中确认。\n"
                "3. 不要编造政策、数字、流程。\n"
                "4. 回答要带上引用来源 document_id。\n"
                "5. 如果多个片段互相冲突，要指出冲突，不要强行合并。\n"
                "\n"
                "知识库片段：\n"
                "{retrieved_context}"
            ),
        ),
        MessagesPlaceholder(
            variable_name="history",
            optional=True,
            n_messages=6,
        ),
        (
            "human",
            "{user_question}",
        ),
    ],
    metadata={
        "prompt_id": "rag_qa",
        "version": "v1",
        "scenario": "rag_qa",
    },
    tags=[
        "rag_qa",
        "v1",
    ],
)


AGENT_PLANNER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "你是一个 AI Agent 任务规划器。\n"
                "\n"
                "你的任务：\n"
                "根据用户目标、可用工具和约束条件，规划下一步应该怎么做。\n"
                "\n"
                "规划要求：\n"
                "1. 不要编造工具。\n"
                "2. 只能使用 available_tools 中列出的工具。\n"
                "3. 如果信息不足，要先追问用户。\n"
                "4. 如果工具不足以完成任务，要明确说明。\n"
                "5. 高风险动作不能自动执行，必须请求确认。\n"
                "\n"
                "可用工具：\n"
                "{available_tools}\n"
                "\n"
                "约束条件：\n"
                "{constraints}"
            ),
        ),
        MessagesPlaceholder(
            variable_name="history",
            optional=True,
            n_messages=8,
        ),
        (
            "human",
            "用户目标：{user_goal}",
        ),
    ],
    metadata={
        "prompt_id": "agent_planner",
        "version": "v1",
        "scenario": "agent_planner",
    },
    tags=[
        "agent_planner",
        "v1",
    ],
)
```

---

## 【重点内容】
这里我们先定义四个 Prompt：

```plain
GENERAL_CHAT_PROMPT
ECOMMERCE_CUSTOMER_SERVICE_PROMPT
RAG_QA_PROMPT
AGENT_PLANNER_PROMPT
```

它们分别对应：

```plain
通用聊天
电商客服
RAG 问答
Agent 规划
```

每个 Prompt 都有：

```plain
system
history placeholder
human
metadata
tags
```

这就是 LangChain 版本的 Prompt 工程化。

---

# 十九、15｜为什么保留 PromptRegistry
## 【重点内容】
有同学可能会问：

既然用了 ChatPromptTemplate，还要 PromptRegistry 吗？

我的建议是：

```plain
要保留。
```

原因是 ChatPromptTemplate 解决的是模板渲染问题。

但是 PromptRegistry 解决的是 Prompt 管理问题。

比如：

```plain
根据 prompt_id 找 Prompt
根据 scenario 找 Prompt
管理 version
列出所有 Prompt
控制 Prompt 是否启用
记录 Prompt metadata
```

这些不是 ChatPromptTemplate 单独负责的。

所以我们的架构是：

```plain
ChatPromptTemplate
负责渲染

PromptRegistry
负责管理

PromptService
负责业务调用入口
```

---

# 二十、16｜创建 LangChain PromptRegistry
创建：

```plain
app/langchain_prompts/registry.py
```

写入：

```python
from pydantic import BaseModel, ConfigDict, Field
from langchain_core.prompts import ChatPromptTemplate

from app.prompts.base import PromptScenario
from app.langchain_prompts.templates import (
    AGENT_PLANNER_PROMPT,
    ECOMMERCE_CUSTOMER_SERVICE_PROMPT,
    GENERAL_CHAT_PROMPT,
    RAG_QA_PROMPT,
)


class LangChainPromptDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    prompt_id: str = Field(..., description="Prompt ID")
    name: str = Field(..., description="Prompt 名称")
    scenario: PromptScenario = Field(..., description="Prompt 场景")
    version: str = Field(default="v1", description="Prompt 版本")
    description: str = Field(default="", description="Prompt 描述")
    prompt: ChatPromptTemplate = Field(..., description="LangChain ChatPromptTemplate")
    enabled: bool = Field(default=True, description="是否启用")


class LangChainPromptRegistry:
    def __init__(self):
        self._prompts: dict[str, LangChainPromptDefinition] = {}

    def register(self, definition: LangChainPromptDefinition):
        key = self._build_key(
            prompt_id=definition.prompt_id,
            version=definition.version,
        )

        self._prompts[key] = definition

    def get_by_prompt_id(
        self,
        prompt_id: str,
        version: str = "v1",
    ) -> LangChainPromptDefinition:
        key = self._build_key(
            prompt_id=prompt_id,
            version=version,
        )

        if key not in self._prompts:
            raise KeyError(f"Prompt 不存在：{prompt_id}@{version}")

        definition = self._prompts[key]

        if not definition.enabled:
            raise KeyError(f"Prompt 已禁用：{prompt_id}@{version}")

        return definition

    def get_by_scenario(
        self,
        scenario: PromptScenario,
        version: str = "v1",
    ) -> LangChainPromptDefinition:
        for definition in self._prompts.values():
            if definition.scenario == scenario and definition.version == version and definition.enabled:
                return definition

        raise KeyError(f"未找到场景 Prompt：{scenario}@{version}")

    def list(self) -> list[LangChainPromptDefinition]:
        return list(self._prompts.values())

    def _build_key(
        self,
        prompt_id: str,
        version: str,
    ) -> str:
        return f"{prompt_id}:{version}"


langchain_prompt_registry = LangChainPromptRegistry()


langchain_prompt_registry.register(
    LangChainPromptDefinition(
        prompt_id="general_chat",
        name="通用聊天 Prompt",
        scenario=PromptScenario.GENERAL_CHAT,
        version="v1",
        description="用于普通 AI Chat 问答。",
        prompt=GENERAL_CHAT_PROMPT,
    )
)

langchain_prompt_registry.register(
    LangChainPromptDefinition(
        prompt_id="ecommerce_customer_service",
        name="电商客服 Prompt",
        scenario=PromptScenario.ECOMMERCE_CUSTOMER_SERVICE,
        version="v1",
        description="用于跨境电商客服场景。",
        prompt=ECOMMERCE_CUSTOMER_SERVICE_PROMPT,
    )
)

langchain_prompt_registry.register(
    LangChainPromptDefinition(
        prompt_id="rag_qa",
        name="RAG 问答 Prompt",
        scenario=PromptScenario.RAG_QA,
        version="v1",
        description="用于企业知识库问答。",
        prompt=RAG_QA_PROMPT,
    )
)

langchain_prompt_registry.register(
    LangChainPromptDefinition(
        prompt_id="agent_planner",
        name="Agent 规划 Prompt",
        scenario=PromptScenario.AGENT_PLANNER,
        version="v1",
        description="用于 Agent 任务规划。",
        prompt=AGENT_PLANNER_PROMPT,
    )
)
```

---

## 【重点内容】
这个 Registry 和第 15 章的思路一致。

区别是，原来我们注册的是自己定义的 PromptTemplate。

现在注册的是：

```plain
ChatPromptTemplate
```

这样就实现了：

```plain
业务 Prompt 管理
+
LangChain Prompt 渲染
```

两者结合。

---

# 二十一、17｜创建 LangChainPromptService
创建：

```plain
app/langchain_prompts/service.py
```

写入：

```python
from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import ChatPromptValue

from app.langchain_prompts.registry import (
    LangChainPromptDefinition,
    langchain_prompt_registry,
)
from app.prompts.base import PromptScenario


class LangChainPromptService:
    def get_by_prompt_id(
        self,
        prompt_id: str,
        version: str = "v1",
    ) -> LangChainPromptDefinition:
        return langchain_prompt_registry.get_by_prompt_id(
            prompt_id=prompt_id,
            version=version,
        )

    def get_by_scenario(
        self,
        scenario: PromptScenario,
        version: str = "v1",
    ) -> LangChainPromptDefinition:
        return langchain_prompt_registry.get_by_scenario(
            scenario=scenario,
            version=version,
        )

    def render_by_prompt_id(
        self,
        prompt_id: str,
        variables: dict,
        version: str = "v1",
    ) -> ChatPromptValue:
        definition = self.get_by_prompt_id(
            prompt_id=prompt_id,
            version=version,
        )

        return definition.prompt.invoke(variables)

    def render_messages_by_prompt_id(
        self,
        prompt_id: str,
        variables: dict,
        version: str = "v1",
    ) -> list[BaseMessage]:
        prompt_value = self.render_by_prompt_id(
            prompt_id=prompt_id,
            variables=variables,
            version=version,
        )

        return prompt_value.messages

    def render_by_scenario(
        self,
        scenario: PromptScenario,
        variables: dict,
        version: str = "v1",
    ) -> ChatPromptValue:
        definition = self.get_by_scenario(
            scenario=scenario,
            version=version,
        )

        return definition.prompt.invoke(variables)

    def render_messages_by_scenario(
        self,
        scenario: PromptScenario,
        variables: dict,
        version: str = "v1",
    ) -> list[BaseMessage]:
        prompt_value = self.render_by_scenario(
            scenario=scenario,
            variables=variables,
            version=version,
        )

        return prompt_value.messages

    def list_prompts(self) -> list[dict]:
        return [
            {
                "prompt_id": definition.prompt_id,
                "name": definition.name,
                "scenario": definition.scenario.value,
                "version": definition.version,
                "description": definition.description,
                "enabled": definition.enabled,
                "input_variables": definition.prompt.input_variables,
                "optional_variables": definition.prompt.optional_variables,
                "metadata": definition.prompt.metadata,
                "tags": definition.prompt.tags,
            }
            for definition in langchain_prompt_registry.list()
        ]


langchain_prompt_service = LangChainPromptService()
```

---

## 【重点内容】
LangChainPromptService 是业务层调用入口。

它提供两类方法。

第一类返回：

```plain
ChatPromptValue
```

第二类直接返回：

```plain
messages
```

比如：

```python
render_messages_by_scenario(...)
```

后面接模型时，就可以直接：

```python
messages = langchain_prompt_service.render_messages_by_scenario(...)
response = await model.ainvoke(messages)
```

这就和 LangChain Model 连接上了。

---

# 二十二、18｜测试 LangChainPromptService
创建：

```plain
scripts/test_lc23_prompt_service.py
```

写入：

```python
from app.langchain_prompts.service import langchain_prompt_service
from app.prompts.base import PromptScenario


def main():
    print("prompt list:")
    for item in langchain_prompt_service.list_prompts():
        print(item)

    print("=" * 80)

    messages = langchain_prompt_service.render_messages_by_scenario(
        scenario=PromptScenario.ECOMMERCE_CUSTOMER_SERVICE,
        version="v1",
        variables={
            "history": [],
            "user_question": "帮我查一下订单 10001 到哪了？",
            "business_rules": "不能编造物流信息；没有订单号时必须追问。",
            "order_info": "用户提供了订单号 10001。",
        },
    )

    for message in messages:
        print(message.type, ":", message.content)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个脚本验证两件事。

第一，Registry 能不能列出 Prompt。

第二，电商客服 Prompt 能不能正常渲染成 LangChain messages。

如果这一步通了，后面就可以接 ChatModel。

---

# 二十三、19｜Prompt | Model：组成最小 Chain
打开：

```plain
app/langchain_prompts/demo_prompt_chain.py
```

写入：

```python
from langchain_core.output_parsers import StrOutputParser

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_prompts.templates import GENERAL_CHAT_PROMPT


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7,
    )

    parser = StrOutputParser()

    chain = GENERAL_CHAT_PROMPT | model | parser

    result = chain.invoke({
        "history": [],
        "user_question": "请用三句话解释 LangChain Prompt 的作用。",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc23_prompt_chain.py
```

写入：

```python
from app.langchain_prompts.demo_prompt_chain import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这里出现了经典写法：

```python
chain = GENERAL_CHAT_PROMPT | model | parser
```

执行流程是：

```plain
GENERAL_CHAT_PROMPT
把变量渲染成 messages

model
调用大模型

parser
把 AIMessage 转成字符串
```

这就是 LangChain Prompt 和 Model 的组合能力。

---

# 二十四、20｜Prompt | Model | Parser：结构化输出
打开：

```plain
app/langchain_prompts/demo_prompt_parser_chain.py
```

写入：

```python
from typing import Literal

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.langchain_models.model_factory import LangChainModelFactory


class IntentResult(BaseModel):
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
        description="置信度",
    )

    reason: str = Field(..., description="判断原因")


def main():
    parser = PydanticOutputParser(
        pydantic_object=IntentResult,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个电商客服意图识别器。\n"
                "你必须根据格式要求输出。\n"
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

    print(result.model_dump())


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子对应第 17 章结构化输出。

我们用：

```python
PydanticOutputParser
```

生成格式要求。

再用：

```python
partial(format_instructions=...)
```

把格式说明固定到 Prompt 里。

最后：

```python
prompt | model | parser
```

得到 Pydantic 对象。

这就是 LangChain 写结构化输出的典型方式。

---

# 二十五、21｜项目一 Prompt 改造适配器
现在写一个项目适配示例。

打开：

```plain
app/langchain_prompts/demo_project_prompt_adapter.py
```

写入：

```python
from langchain_core.messages import BaseMessage

from app.langchain_prompts.service import langchain_prompt_service
from app.prompts.base import PromptScenario
from app.schemas.chat import ChatRequest, MessageRole


def build_history_from_chat_request(
    request: ChatRequest,
) -> list[BaseMessage]:
    history = []

    for message in request.messages[:-1]:
        if message.role == MessageRole.USER:
            history.append(("human", message.content))

        elif message.role == MessageRole.ASSISTANT:
            history.append(("ai", message.content))

    return history


def build_langchain_messages_from_chat_request(
    request: ChatRequest,
) -> list[BaseMessage]:
    latest_user_question = ""

    for message in reversed(request.messages):
        if message.role == MessageRole.USER:
            latest_user_question = message.content
            break

    scenario = PromptScenario(request.prompt_scenario or PromptScenario.GENERAL_CHAT.value)

    variables = {
        "history": build_history_from_chat_request(request),
        "user_question": latest_user_question,
    }

    if scenario == PromptScenario.ECOMMERCE_CUSTOMER_SERVICE:
        variables["business_rules"] = request.metadata.get(
            "business_rules",
            "暂无额外业务规则。",
        )
        variables["order_info"] = request.metadata.get(
            "order_info",
            "用户未提供订单信息。",
        )

    if scenario == PromptScenario.RAG_QA:
        variables["retrieved_context"] = request.metadata.get(
            "retrieved_context",
            "暂无检索上下文。",
        )

    if scenario == PromptScenario.AGENT_PLANNER:
        variables["user_goal"] = latest_user_question
        variables["available_tools"] = request.metadata.get(
            "available_tools",
            "暂无可用工具。",
        )
        variables["constraints"] = request.metadata.get(
            "constraints",
            "无。",
        )

    return langchain_prompt_service.render_messages_by_scenario(
        scenario=scenario,
        version=request.prompt_version or "v1",
        variables=variables,
    )
```

---

## 【重点内容】
这个适配器展示了如何把第 19 章的 ChatRequest 转成 LangChain messages。

它做了几件事：

```plain
1. 从 request.messages 里提取历史消息
2. 找到最新用户问题
3. 根据 prompt_scenario 选择 Prompt
4. 根据场景补充变量
5. 调用 LangChainPromptService 渲染 messages
```

这就是把项目一接入 LangChain Prompt 的关键。

---

# 二十六、22｜项目一 ChatService 怎么改
当前第 19 章里，我们大概有：

```python
llm_request = build_llm_request_from_chat_request(request)
```

未来可以改成：

```python
from app.langchain_prompts.demo_project_prompt_adapter import (
    build_langchain_messages_from_chat_request,
)

messages = build_langchain_messages_from_chat_request(request)

response = await model.ainvoke(messages)
```

但更推荐保持 Provider 抽象：

```plain
ChatService
 ↓
LangChainPromptService 渲染 messages
 ↓
LangChainLLMProvider 调用模型
```

---

## 【重点内容】
这一章先不要全量改第 19 章项目。

我们只是先把 Prompt 的 LangChain 版本写出来。

后面逐步替换：

```plain
先替换 Prompt 渲染
再替换 Model 调用
再替换 Parser
再替换 Tool
```

这样更稳。

---

# 二十七、23｜为什么不要把 Prompt 写死在 Chain 里
不推荐：

```python
chain = ChatPromptTemplate.from_messages([
    ("system", "你是客服助手..."),
    ("human", "{question}"),
]) | model
```

如果到处这样写，问题是：

```plain
Prompt 分散
Prompt 无法统一版本管理
Prompt 难以灰度
Prompt 难以复用
Prompt 难以统计
```

推荐：

```plain
templates.py
定义 Prompt

registry.py
注册 Prompt

service.py
渲染 Prompt

业务层
按 scenario 调用
```

---

## 【重点内容】
LangChain 让 Prompt 变得很好写。

但也容易导致大家随手写 Prompt。

真实项目不要这样。

Prompt 是资产。

应该统一管理。

所以我们保留 PromptRegistry。

LangChain 只负责底层模板渲染和组合。

---

# 二十八、24｜Prompt 版本管理怎么做
可以注册多个版本：

```python
langchain_prompt_registry.register(
    LangChainPromptDefinition(
        prompt_id="general_chat",
        name="通用聊天 Prompt",
        scenario=PromptScenario.GENERAL_CHAT,
        version="v2",
        description="更适合教学场景的通用聊天 Prompt。",
        prompt=GENERAL_CHAT_PROMPT_V2,
    )
)
```

调用时：

```python
langchain_prompt_service.render_messages_by_scenario(
    scenario=PromptScenario.GENERAL_CHAT,
    version="v2",
    variables={...},
)
```

---

## 【重点内容】
Prompt 版本管理非常重要。

比如 v1 回复太啰嗦。

你想上线 v2。

不要直接改 v1。

否则之前的效果无法复现。

正确做法是：

```plain
新增 v2
灰度测试
对比效果
确认稳定后切默认版本
```

后面企业级 AI 平台阶段，会把 Prompt 版本放到数据库里管理。

---

# 二十九、25｜Prompt 和历史上下文的关系
历史消息一般来自：

```plain
PostgreSQL
Redis 最近消息缓存
前端传入 messages
```

Prompt 只负责：

```plain
把 history 插入到合适位置
```

不要让 Prompt 自己去查数据库。

---

## 【重点内容】
这点一定要讲清楚。

MessagesPlaceholder 不负责查历史。

它只负责占位。

历史消息从哪里来？

由业务系统决定。

比如：

```plain
ConversationService 从 PostgreSQL 查
Redis 缓存最近 10 条
ChatService 组装 history
PromptService 渲染 messages
```

职责要分清楚。

---

# 三十、26｜Prompt 和 RAG 的关系
RAG Prompt 一般结构：

```plain
System:
  你是企业知识库助手
  只能基于上下文回答
  不要编造

Context:
  {retrieved_context}

History:
  {history}

Human:
  {user_question}
```

---

## 【重点内容】
RAG Prompt 的核心是：

```plain
把检索到的文档片段放进 Prompt
```

但是要强调规则：

```plain
只能基于知识库回答
没有答案要说不知道
不要编造引用
引用 document_id
```

这些规则应该放在 system 里。

文档片段作为变量传入。

后面 RAG 阶段会继续深入。

---

# 三十一、27｜Prompt 和 Agent 的关系
Agent Prompt 一般包含：

```plain
角色
目标
可用工具
工具使用规则
约束条件
历史消息
用户目标
```

示例变量：

```plain
available_tools
constraints
history
user_goal
```

---

## 【重点内容】
Agent Prompt 比普通 Chat Prompt 更复杂。

因为它不只是回答问题。

它要指导模型：

```plain
什么时候调用工具
哪些工具能用
工具参数怎么填
什么情况不能执行
什么时候追问用户
什么时候结束
```

这就是后面 Agent 和 LangGraph 的基础。

这一章先把 Agent Planner Prompt 定义好。

---

# 三十二、28｜Prompt 安全边界
## 【重点内容】
Prompt 不是安全系统。

比如你在 system 里写：

```plain
不要泄露用户隐私
不要执行高风险操作
```

这很有必要。

但不能只靠它。

真实系统还要有：

```plain
权限校验
参数校验
工具白名单
敏感信息脱敏
人工确认
日志审计
```

Prompt 是第一层约束。

后端规则才是最后防线。

---

# 三十三、29｜Prompt 常见错误一：大括号没有转义
如果 Prompt 里要展示 JSON 示例：

错误：

```python
"""
{
  "intent": "query_order"
}
"""
```

在模板里可能被当成变量。

正确：

```python
"""
{{
  "intent": "query_order"
}}
"""
```

---

## 【重点内容】
这是最常见错误。

因为 LangChain Prompt 默认使用 Python 风格的 `{variable}` 格式。

如果你要在 Prompt 里展示 JSON，就要把大括号写成双大括号。

LangSmith 的 prompt template 格式文档也说明，f-string 模板使用 Python 风格的 `{variable}` 做变量替换。

---

# 三十四、30｜Prompt 常见错误二：history 类型传错
错误：

```python
prompt.invoke({
    "history": "用户上一轮问了什么...",
    "user_question": "继续解释",
})
```

正确：

```python
prompt.invoke({
    "history": [
        ("human", "什么是 AI Agent？"),
        ("ai", "AI Agent 是..."),
    ],
    "user_question": "继续解释",
})
```

或者：

```python
from langchain_core.messages import HumanMessage, AIMessage

history = [
    HumanMessage(content="什么是 AI Agent？"),
    AIMessage(content="AI Agent 是..."),
]
```

---

## 【重点内容】
MessagesPlaceholder 要的是消息列表。

不是字符串。

如果传字符串，会报错或者渲染异常。

所以 history 一定要是：

```plain
list[BaseMessage]
```

或者 LangChain 支持的 tuple message 格式。

---

# 三十五、31｜Prompt 常见错误三：把所有上下文塞进 system
错误：

```plain
system 里塞角色、历史、知识库、用户问题、工具结果
```

问题：

```plain
结构混乱
不利于多轮对话
不利于 ToolMessage
不利于模型理解消息角色
```

推荐：

```plain
System：规则
History：历史
Context：知识库变量
Human：当前问题
ToolMessage：工具结果
```

---

# 三十六、32｜Prompt 常见错误四：Prompt 太长
问题：

```plain
成本高
上下文挤占
模型抓不住重点
延迟增加
```

解决：

```plain
1. 精简 system 规则
2. 用 MessagesPlaceholder 限制历史数量
3. RAG 只放最相关片段
4. 长业务规则拆成配置或检索
5. 定期评估 Prompt 效果
```

---

# 三十七、33｜Prompt 常见错误五：没有版本管理
错误：

```plain
直接改线上 Prompt
```

正确：

```plain
新增 v2
灰度测试
记录效果
再切默认版本
```

---

# 三十八、34｜Prompt 常见错误六：Prompt 和业务规则混在一起
比如退款规则：

```plain
签收后 7 天内可退
生鲜不支持无理由退货
大额退款需要人工审核
```

这些不应该只写在 Prompt 里。

应该在业务系统里也有规则校验。

Prompt 只是告诉模型如何回复。

真正能不能退款，由后端规则判断。

---

# 三十九、35｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| `ChatPromptTemplate` | 第 15 章 PromptTemplate |
| `from_messages` | 第 13 章 messages 结构 |
| `SystemMessage`<br/> 模板 | 第 15 章 system prompt |
| `HumanMessage`<br/> 模板 | 用户当前问题 |
| `MessagesPlaceholder` | 第 19 章历史消息上下文 |
| `partial` | 固定公共变量 |
| `metadata / tags` | Prompt 版本管理和 tracing |
| `PromptRegistry` | 第 15 章 PromptRegistry |
| `PromptService` | 第 15 章 PromptService |
| `Prompt | Model` |
| `Prompt | Model |
| RAG Prompt | 后续企业知识库 |
| Agent Prompt | 后续 LangChain Agent / LangGraph |


---

# 四十、36｜本章完整复习
这一章我们完成了：

```plain
1. 理解 LangChain Prompt 的定位
2. 回顾第 15 章手写 PromptService
3. 理解 PromptTemplate 和 ChatPromptTemplate 区别
4. 理解为什么 Chat 场景优先用 ChatPromptTemplate
5. 编写最小 ChatPromptTemplate 示例
6. 理解 ChatPromptValue / PromptValue
7. 理解 input_variables
8. 理解变量缺失报错
9. 理解 MessagesPlaceholder
10. 使用 MessagesPlaceholder 接入历史消息
11. 使用 optional=True
12. 使用 n_messages 限制历史数量
13. 理解 partial variables
14. 编写 partial 示例
15. 理解 metadata 和 tags
16. 创建通用聊天 Prompt
17. 创建电商客服 Prompt
18. 创建 RAG Prompt
19. 创建 Agent Planner Prompt
20. 保留 PromptRegistry
21. 创建 LangChainPromptRegistry
22. 创建 LangChainPromptService
23. 测试 LangChainPromptService
24. 编写 prompt | model | parser 示例
25. 编写 PydanticOutputParser 结构化 Prompt 示例
26. 编写项目一 Prompt Adapter
27. 理解项目一如何逐步迁移 LangChain Prompt
28. 总结 Prompt 与历史上下文、RAG、Agent 的关系
29. 总结 Prompt 常见错误
```

---

# 四十一、37｜课后任务一：跑通 ChatPromptTemplate 示例
要求：

```plain
1. 运行 scripts/test_lc23_chat_prompt.py
2. 打印 prompt_value 类型
3. 打印 messages
4. 说明 system / human 分别是什么
```

---

# 四十二、38｜课后任务二：给通用聊天 Prompt 增加 history
要求：

```plain
1. 使用 MessagesPlaceholder("history", optional=True)
2. 构造两条历史消息
3. 传入当前 user_question
4. 打印最终 messages 顺序
```

---

# 四十三、39｜课后任务三：给电商客服 Prompt 新增 v2
要求：

```plain
1. 新建 ECOMMERCE_CUSTOMER_SERVICE_PROMPT_V2
2. 增加“不要承诺具体到达时间”规则
3. 注册到 Registry
4. version 设置为 v2
5. 使用 version="v2" 渲染
```

---

# 四十四、40｜课后任务四：把第 19 章 ChatRequest 转成 LangChain messages
要求：

```plain
1. 使用 demo_project_prompt_adapter.py
2. 从 request.messages 提取历史消息
3. 找到最新 user_question
4. 根据 prompt_scenario 选择 Prompt
5. 渲染出 LangChain messages
```

---

# 四十五、41｜课后任务五：实现 Prompt | Model | Parser
要求：

```plain
1. 定义 IntentResult Pydantic 模型
2. 用 PydanticOutputParser 生成 format_instructions
3. 用 partial 固定 format_instructions
4. 组成 chain = prompt | model | parser
5. 输入“我的订单怎么还没发货？”
6. 输出 intent / confidence / reason
```

---

# 四十六、42｜课后任务六：画出 LangChain Prompt 调用链路
画出：

```plain
POST /api/v1/chat
```

接入 LangChain Prompt 后的链路：

```plain
ChatRequest
 ↓
ChatService
 ↓
提取 latest_user_question
 ↓
查询历史 messages
 ↓
LangChainPromptService
 ↓
LangChainPromptRegistry
 ↓
ChatPromptTemplate
 ↓
MessagesPlaceholder 插入 history
 ↓
PromptValue.messages
 ↓
LangChainLLMProvider
 ↓
ChatModel.ainvoke()
```

---

# 四十七、43｜本章总结 
## 【重点内容】
好了，到这里，第 23 章我们就讲完了。

这一章我们把第 15 章手写的 Prompt 工程化能力，迁移到了 LangChain Prompt 体系里。

大家一定要记住：

```plain
ChatPromptTemplate
负责把变量渲染成 messages

MessagesPlaceholder
负责插入历史消息

partial
负责固定公共变量

metadata / tags
负责 tracing 和版本标识

PromptRegistry
负责 Prompt 管理

PromptService
负责业务调用入口
```

所以我们不是简单地在代码里写：

```python
prompt = ChatPromptTemplate.from_messages(...)
```

然后到处复制。

我们仍然保留企业项目里需要的：

```plain
Prompt ID
Prompt Scenario
Prompt Version
Prompt Registry
Prompt Service
```

LangChain 负责底层渲染和组合。

业务系统负责管理和治理。

这就是比较合理的工程化方式。


