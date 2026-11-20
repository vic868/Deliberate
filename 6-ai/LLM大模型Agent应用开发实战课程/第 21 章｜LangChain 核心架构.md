---

# 一、本章定位
上一章我们讲了：

```plain
第 20 章｜为什么需要 LangChain
```

重点解决了一个问题：

为什么我们已经会原生大模型开发了，还要学习 LangChain？

因为前面我们手写过：

```plain
LLMProvider
PromptService
StructuredOutputService
ToolRegistry
ToolExecutor
ChatService
ToolCallingService
```

这些能力在真实 AI 项目里会反复出现。

LangChain 就是把这些重复能力抽象成了一套框架。

这一章我们不急着写 RAG，不急着写 Agent。

我们先系统拆解 LangChain 的核心架构。

也就是搞清楚：

```plain
langchain
langchain-core
langchain-openai
langchain-community
LangGraph
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
```

这些东西到底分别负责什么。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. LangChain 1.x 生态包如何拆分
2. langchain-core 是什么
3. langchain 是什么
4. langchain-openai 是什么
5. langchain-community 是什么
6. LangGraph 和 LangChain 是什么关系
7. Message 在 LangChain 里的作用
8. ChatModel 在 LangChain 里的作用
9. PromptTemplate 在 LangChain 里的作用
10. OutputParser 在 LangChain 里的作用
11. Runnable 是什么
12. LCEL 是什么
13. Tool 在 LangChain 里的作用
14. Agent 和 Tool 的关系
15. Retriever 和 RAG 的关系
16. Callback / tracing 的作用
17. LangChain 和我们前 19 章原生代码如何对应
18. 如何在项目一里逐步引入 LangChain
```

---

# 三、本章版本口径
本课程从第 21 章开始，统一采用：

```plain
Python：3.12+
Pydantic：v2
FastAPI：当前项目版本
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

如果还要用社区集成：

```bash
uv add "langchain-community>=0.4,<0.5"
```

---

## 【重点内容】
这里先把版本定下来。

LangChain 和 LangGraph 迭代非常快。

如果我们课程里直接写：

```bash
uv add langchain langgraph
```

短期没问题。

但过几个月，学员安装到新的小版本或新的大版本，API 可能发生变化。

所以课程里采用一个比较稳的策略：

```plain
文档里锁定主版本和次版本范围
代码包里用 uv.lock 锁定实际版本
```

也就是：

```plain
课程讲解：
LangChain 1.3.x / LangGraph 1.2.x

代码运行：
以 uv.lock 为准
```

LangChain 官方安装文档要求 Python 3.10+；本课程继续使用 Python 3.12。LangChain 官方版本说明也采用语义化版本号，格式是 `MAJOR.MINOR.PATCH`，所以课程里固定主版本和次版本，更适合教学复现。

---

# 四、本章最终项目结构
本章不重构第 19 章项目。

只新增架构学习示例目录：

```markdown
ai-agent-course/
├── app/
│   ├── langchain_arch/
│   │   ├── __init__.py
│   │   ├── 01_package_check.py
│   │   ├── 02_messages_demo.py
│   │   ├── 03_chat_model_demo.py
│   │   ├── 04_prompt_template_demo.py
│   │   ├── 05_runnable_demo.py
│   │   ├── 06_output_parser_demo.py
│   │   ├── 07_tool_demo.py
│   │   ├── 08_chain_arch_demo.py
│   │   └── 09_native_mapping_demo.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_langchain_packages.py
│   ├── test_langchain_messages.py
│   ├── test_langchain_runnable.py
│   └── test_langchain_arch_mapping.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 21 章。

这一章我们正式拆解 LangChain 的核心架构。

上一章我们已经知道 LangChain 为什么出现。

它不是大模型。

它不是 Agent 本身。

它是一个 LLM 应用开发框架。

这一章我们要解决的是：

LangChain 内部到底有哪些核心模块？这些模块分别对应我们前面手写过的哪些代码？

这章非常重要。

因为很多同学学 LangChain 最大的问题是：

```plain
API 会复制
但是架构不清楚
```

比如看到：

```python
prompt | model | parser
```

不知道这个 `|` 到底在干什么。

看到：

```python
ChatPromptTemplate
```

不知道它和前面 messages 是什么关系。

看到：

```python
Runnable
```

不知道为什么 Prompt、Model、Parser 都能串起来。

看到：

```python
@tool
```

不知道它和第 18 章 Tool Calling 的 tools schema 有什么关系。

所以这一章我们先把架构讲清楚。

代码可以慢慢写。

但架构必须先稳。

---

# 六、02｜LangChain 1.x 生态包拆分
## 【实操】
```plain
LangChain 1.x 生态

langchain-core
  ↓
核心抽象：Message / Prompt / Runnable / OutputParser / Tool

langchain
  ↓
主入口：Agent、常用高级能力

langchain-openai
  ↓
OpenAI / OpenAI-compatible 模型集成

langchain-community
  ↓
社区集成：第三方工具、向量库、文档加载器等

langgraph
  ↓
复杂 Agent 状态图、持久化、多步骤、人类介入
```

---

## 【重点内容】
LangChain 1.x 之后，生态是拆包的。

这点一定要讲清楚。

以前很多老教程会这样写：

```python
from langchain.chat_models import ChatOpenAI
```

新版本不建议这么写了。

现在更推荐：

```python
from langchain_openai import ChatOpenAI
```

因为模型集成被拆到单独的 provider 包里。

官方 API Reference 里也能看到，`langchain-core` 是 LangChain 生态的核心接口和抽象，`langchain` 是主入口包，而 provider 集成会拆到类似 `langchain-openai` 这样的包里；集成总览也说明，很多 provider 都有自己的 `langchain-<provider>` 包，用来实现 ChatModel、Embedding、VectorStore 等标准接口。

所以本课程后续统一用新版本写法：

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
```

---

# 七、03｜为什么要拆成这么多包
## 【重点内容】
很多同学第一次看会觉得：

```plain
怎么这么多包？
langchain
langchain-core
langchain-openai
langchain-community
langgraph
```

其实这是工程演进的结果。

如果所有东西都塞进一个 `langchain` 包，会有几个问题。

第一，依赖太重。

你可能只是想调用 OpenAI，但是包里带了一堆向量库、文档加载器、第三方工具。

第二，版本冲突。

不同 provider、不同社区集成依赖不同库，很容易互相影响。

第三，核心抽象不清晰。

核心接口和具体集成混在一起，框架会越来越重。

所以现在拆成：

```plain
核心抽象归 core
模型集成归 provider 包
社区生态归 community
复杂 Agent 编排归 LangGraph
```

这种架构更清楚。

---

# 八、04｜LangChain 核心架构总图
## 【实操】
```plain
                ┌─────────────────────┐
                │       Agent         │
                │  决策 / 工具调用 / 循环│
                └──────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    Model     │   │     Tool     │   │  Retriever   │
│  模型调用     │   │  外部能力     │   │  知识检索      │
└──────┬───────┘   └──────────────┘   └──────────────┘
       │
       ▼
┌──────────────┐
│   Message    │
│ system/human │
│ ai/tool      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Prompt    │
│  模板 / 变量   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Parser     │
│ 输出解析 / 校验 │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Runnable   │
│ 统一可执行接口 │
└──────────────┘
```

---

## 【重点内容】
这张图就是 LangChain 的核心架构。

不要把它看复杂。

我们从底往上看。

第一层是 Message。

它对应大模型 API 里的：

```plain
system
human / user
ai / assistant
tool
```

第二层是 Prompt。

它负责把模板和变量渲染成 messages。

第三层是 Model。

它负责调用大模型。

第四层是 Parser。

它负责把模型输出解析成字符串、JSON、Pydantic 对象。

第五层是 Tool。

它负责连接外部能力。

第六层是 Retriever。

它负责从知识库检索文档。

第七层是 Agent。

它负责根据目标决定下一步做什么。

而 Runnable 是贯穿这些组件的统一接口。

---

# 九、05｜核心模块一：Message
## 【实操】
```plain
LangChain Message

SystemMessage
HumanMessage
AIMessage
ToolMessage
```

---

## 原生写法
```python
messages = [
    {
        "role": "system",
        "content": "你是一个专业 AI 助手。"
    },
    {
        "role": "user",
        "content": "什么是 LangChain？"
    }
]
```

---

## LangChain 写法
```python
from langchain_core.messages import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="你是一个专业 AI 助手。"),
    HumanMessage(content="什么是 LangChain？"),
]
```

---

## 【重点内容】
Message 是 LangChain 里最底层的概念之一。

它本质上就是对大模型 messages 的封装。

我们第 13 章讲过：

```plain
system 负责定义角色和边界
user 负责用户输入
assistant 负责模型回答
tool 负责工具结果
```

在 LangChain 里对应：

```plain
SystemMessage
HumanMessage
AIMessage
ToolMessage
```

所以大家一定要记住：

```plain
LangChain Message
不是新概念

它就是 Chat API messages 的对象化封装
```

---

# 十、06｜核心模块二：ChatModel
## 【实操】
```plain
ChatModel
=
统一模型调用接口

invoke()
stream()
batch()
ainvoke()
astream()
```

---

## 示例
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="deepseek-chat",
    api_key="你的 Key",
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

response = model.invoke("请用一句话解释 LangChain。")

print(response.content)
```

---

## 【重点内容】
ChatModel 对应我们第 14 章写的：

```plain
BaseLLMProvider
DeepSeekProvider
QwenProvider
OpenAIProvider
```

它负责调用模型。

我们之前自己封装：

```python
llm_provider.chat(request)
```

LangChain 里是：

```python
model.invoke(input)
```

如果是流式：

```python
model.stream(input)
```

如果是异步：

```python
await model.ainvoke(input)
```

这就是统一模型调用接口。

---

# 十一、07｜核心模块三：PromptTemplate
## 【实操】
```plain
PromptTemplate
=
模板
+
变量
+
Message 结构
```

---

## 示例
```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的 {role_name}。"),
    ("human", "请回答：{question}"),
])

result = prompt.invoke({
    "role_name": "AI Agent 课程助教",
    "question": "为什么需要 LangChain？",
})

print(result.messages)
```

---

## 【重点内容】
PromptTemplate 对应我们第 15 章写的：

```plain
PromptTemplate
PromptMessageTemplate
PromptService
render_prompt
```

它解决的是 Prompt 模板化问题。

也就是：

```plain
把变量填进模板
生成 messages
```

LangChain 的 ChatPromptTemplate 更贴近 Chat API。

它输出的不是普通字符串，而是 messages。

这点很重要。

因为现代大模型 Chat API 的核心输入就是 messages。

---

# 十二、08｜核心模块四：OutputParser
## 【实操】
```plain
OutputParser
=
把模型输出
解析成程序可用的数据
```

常见类型：

```plain
StrOutputParser
JsonOutputParser
PydanticOutputParser
```

---

## 示例
```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()

chain = prompt | model | parser

result = chain.invoke({
    "question": "什么是 LangChain？"
})

print(result)
```

---

## 【重点内容】
OutputParser 对应我们第 17 章写的：

```plain
parse_structured_output
extract_json_text
Pydantic 校验
```

模型默认返回的是 AIMessage。

但是业务里经常希望拿到：

```plain
字符串
JSON
Pydantic 对象
列表
分类结果
```

OutputParser 就负责这件事。

比如：

```plain
StrOutputParser
```

把 AIMessage 转成字符串。

后面结构化输出章节，我们会用 PydanticOutputParser 或模型自身的 structured output 能力。

---

# 十三、09｜核心模块五：Runnable
## 【实操】
```plain
Runnable
=
LangChain 统一可执行协议

invoke()
ainvoke()
batch()
stream()
astream()
```

---

## 【重点内容】
Runnable 是 LangChain 里非常核心的抽象。

你可以把它理解成：

所有可运行组件的统一接口。

比如这些都可以是 Runnable：

```plain
PromptTemplate
ChatModel
OutputParser
RunnableLambda
Retriever
Chain
```

因为它们都可以被调用。

比如：

```python
prompt.invoke(...)
model.invoke(...)
parser.invoke(...)
chain.invoke(...)
```

LangChain 的 Runnable 文档展示了可通过 `|` 把多个 Runnable 组合成序列，并支持 `invoke`、`ainvoke`、`batch`、`astream` 等调用方式。

所以 Runnable 是理解 LangChain 架构的关键。

后面你看到任何组件，都可以先问一句：

```plain
它是不是 Runnable？
它输入什么？
它输出什么？
它能不能和别的 Runnable 串起来？
```

---

# 十四、10｜核心模块六：LCEL
## 【实操】
```python
chain = prompt | model | parser
```

```plain
LCEL
=
LangChain Expression Language
=
用表达式组合 Runnable
```

---

## 【重点内容】
LCEL 是 LangChain 的组合语法。

最典型的写法就是：

```python
chain = prompt | model | parser
```

它表达的是：

```plain
prompt 先执行
 ↓
输出传给 model
 ↓
model 输出传给 parser
```

这个写法非常简洁。

但是它不是魔法。

本质上还是：

```python
messages = prompt.invoke(input)
ai_message = model.invoke(messages)
result = parser.invoke(ai_message)
```

只不过 LangChain 用 `|` 帮你组合起来。

---

# 十五、11｜核心模块七：Tool
## 【实操】
```python
from langchain_core.tools import tool


@tool
def query_order(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。"""
    return "订单已发货"
```

---

## 【重点内容】
Tool 对应我们第 18 章写的：

```plain
ToolDefinition
ToolRegistry
ToolExecutor
```

LangChain 里可以用 `@tool` 把一个 Python 函数包装成工具。

官方工具文档说明，工具可以由普通 Python 函数或协程定义，也可以通过 `@tool` 装饰器定制名称、描述、参数 schema 等。

但是要注意：

```plain
LangChain Tool
不等于企业级工具权限系统
```

比如：

```plain
谁能调用这个工具？
工具结果要不要脱敏？
高风险工具要不要确认？
工具调用日志怎么记录？
```

这些仍然要业务系统自己做。

---

# 十六、12｜核心模块八：Agent
## 【实操】
```plain
Agent
=
模型
+
工具
+
决策循环
```

Agent 能做：

```plain
理解用户目标
判断是否需要工具
选择工具
生成参数
执行工具
观察工具结果
继续推理
最终回答
```

---

## 【重点内容】
Agent 是很多人最容易误解的概念。

Agent 不是某个固定函数。

它是一种流程。

简单理解：

```plain
普通 Chat：
用户问，模型答。

Tool Calling：
模型调用一次工具，再回答。

Agent：
模型可以根据目标，多轮思考、多次调用工具，直到完成任务。
```

LangChain 1.x 的 Agent 能力已经和 LangGraph 关系很紧。

官方文档也说明，LangChain 的 Agent 构建在 LangGraph 之上，从而获得持久化、流式、人类介入等能力。

所以后面我们会先学 LangChain Agent，再进一步学 LangGraph 的底层图编排。

---

# 十七、13｜核心模块九：Retriever
## 【实操】
```plain
Retriever
=
根据 query
返回相关 Document
```

RAG 链路：

```plain
用户问题
 ↓
Retriever 检索文档
 ↓
Prompt 拼接文档
 ↓
Model 生成答案
 ↓
Parser 解析结果
```

---

## 【重点内容】
Retriever 是 RAG 的核心组件。

它做的事很简单：

```plain
输入 query
返回相关文档
```

比如用户问：

```plain
公司年假有几天？
```

Retriever 去向量库或搜索系统里找相关文档片段。

然后把这些文档交给 Prompt。

模型基于文档回答。

这就是 RAG。

LangChain 里的 `Retriever` 抽象返回的是 Document 对象；官方 API Reference 也把 retriever 描述为根据文本 query 返回 Document 对象的组件。

---

# 十八、14｜核心模块十：Callback / Tracing
## 【实操】
```plain
Callback / Tracing
=
观察 LLM 应用运行过程

记录：
Prompt
Model
Tokens
Latency
Tool Calls
Errors
Chain Steps
```

---

## 【重点内容】
AI 应用非常需要可观测性。

因为它不是普通 CRUD。

一次请求里可能发生：

```plain
Prompt 渲染
模型调用
结构化解析
工具调用
再次模型调用
Retriever 检索
Agent 多步骤循环
```

如果没有日志和 tracing，很难排查问题。

LangChain 提供 Callback 机制，配合 LangSmith 可以做调用链观测。

不过本课程不会把企业日志完全交给 LangSmith。

我们会继续保留自己第 10 章写的：

```plain
trace_id
logger
middleware
AppException
```

然后在 LangChain 层补充 callback / tracing。

---

# 十九、15｜LangGraph 在架构中的位置
## 【实操】
```plain
LangChain
  ↓
组件组合：Model / Prompt / Parser / Tool / Agent

LangGraph
  ↓
状态图：State / Node / Edge / Checkpoint / Human-in-the-loop
```

---

## 【重点内容】
LangGraph 是后面非常重要的部分。

现在先理解它的位置。

LangChain 更像组件和高级 Agent 框架。

LangGraph 更像状态机和工作流引擎。

它适合处理：

```plain
多步骤 Agent
可中断执行
人类审批
状态持久化
多 Agent 协作
复杂条件分支
```

LangGraph 官方概览把它描述为用于构建有状态、多 actor 的 LLM 图应用的框架；LangGraph API Reference 也列出了 checkpoint、store、prebuilt agents、supervisor、swarm 等模块。

所以我们的课程顺序是：

```plain
先 LangChain
再 LangGraph
```

先掌握组件，再掌握状态图。

---

# 二十、16｜LangChain 和前 19 章原生架构映射
## 【实操】
| 前 19 章原生模块 | LangChain / LangGraph 对应 |
| --- | --- |
| `LLMMessage` | `SystemMessage`<br/> / `HumanMessage`<br/> / `AIMessage`<br/> / `ToolMessage` |
| `BaseLLMProvider` | `ChatModel` |
| `PromptTemplate` | `ChatPromptTemplate` |
| `PromptService` | Prompt Registry 可自建，渲染可用 `ChatPromptTemplate` |
| `StructuredOutputService` | `OutputParser`<br/> / structured output |
| `ToolDefinition` | `@tool`<br/> / `StructuredTool` |
| `ToolRegistry` | tools list / 自建 registry |
| `ToolExecutor` | Agent tool execution / 自建 executor |
| `ChatService` | Chain / Runnable 编排 |
| `ToolCallingService` | Agent |
| `RAGService` | Retriever + RAG Chain |
| `stream_chat_with_ai` | `stream`<br/> / `astream` |
| `trace_id + logger` | Callback / Tracing / LangSmith / 自建日志 |
| PostgreSQL | 业务持久化，LangChain 不替代 |
| Redis | 缓存、限流、状态，LangChain 不替代 |
| FastAPI Router | 接口层，LangChain 不替代 |


---

## 【重点内容】
这张表是本章最关键的部分。

你学 LangChain，不要把它看成完全陌生的新框架。

它和我们前 19 章有清晰对应关系。

我们之前的：

```plain
LLMProvider
```

对应 LangChain 的：

```plain
ChatModel
```

我们之前的：

```plain
PromptService
```

对应 LangChain 的：

```plain
ChatPromptTemplate
```

我们之前的：

```plain
ToolCallingService
```

对应 LangChain 的：

```plain
Agent
```

但注意：

```plain
数据库、缓存、权限、API、日志
不会因为用了 LangChain 就消失
```

这些仍然由我们的 FastAPI 工程架构负责。

---

# 二十一、17｜创建 langchain_arch 目录
执行：

```bash
mkdir -p app/langchain_arch

touch app/langchain_arch/__init__.py
touch app/langchain_arch/01_package_check.py
touch app/langchain_arch/02_messages_demo.py
touch app/langchain_arch/03_chat_model_demo.py
touch app/langchain_arch/04_prompt_template_demo.py
touch app/langchain_arch/05_runnable_demo.py
touch app/langchain_arch/06_output_parser_demo.py
touch app/langchain_arch/07_tool_demo.py
touch app/langchain_arch/08_chain_arch_demo.py
touch app/langchain_arch/09_native_mapping_demo.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_arch

New-Item app\langchain_arch\__init__.py
New-Item app\langchain_arch\01_package_check.py
New-Item app\langchain_arch\02_messages_demo.py
New-Item app\langchain_arch\03_chat_model_demo.py
New-Item app\langchain_arch\04_prompt_template_demo.py
New-Item app\langchain_arch\05_runnable_demo.py
New-Item app\langchain_arch\06_output_parser_demo.py
New-Item app\langchain_arch\07_tool_demo.py
New-Item app\langchain_arch\08_chain_arch_demo.py
New-Item app\langchain_arch\09_native_mapping_demo.py
```

---

# 二十二、18｜示例一：检查安装包版本
打开：

```plain
app/langchain_arch/01_package_check.py
```

写入：

```python
from importlib.metadata import version


PACKAGES = [
    "langchain",
    "langchain-core",
    "langchain-openai",
    "langgraph",
]


def main():
    for package in PACKAGES:
        try:
            print(package, "=>", version(package))
        except Exception as exc:
            print(package, "=> 未安装", repr(exc))


if __name__ == "__main__":
    main()
```

运行：

```bash
python app/langchain_arch/01_package_check.py
```

---

## 【重点内容】
这个脚本很实用。

后面学员报错时，第一件事不是看代码。

先看版本。

执行：

```bash
python app/langchain_arch/01_package_check.py
```

确认当前安装的是不是课程要求的版本范围。

很多 LangChain 问题，本质上都是版本不一致。

---

# 二十三、19｜示例二：Message 架构
打开：

```plain
app/langchain_arch/02_messages_demo.py
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
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请解释 LangChain Message 的作用。"),
        AIMessage(content="Message 是对大模型对话消息的对象化封装。"),
        ToolMessage(
            content='{"order_id":"10001","status":"已发货"}',
            tool_call_id="call_query_order_001",
        ),
    ]

    for message in messages:
        print("type:", message.type)
        print("content:", message.content)
        print("dict:", message.model_dump())
        print("=" * 80)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个示例让大家直观看到 LangChain 的 Message 对象。

注意：

```plain
SystemMessage.type = system
HumanMessage.type = human
AIMessage.type = ai
ToolMessage.type = tool
```

它和原生 API 的 role 不是一模一样的字符串，但含义是对应的。

后面调用模型时，LangChain 会帮你转换成模型服务商需要的格式。

---

# 二十四、20｜示例三：ChatModel 架构
打开：

```plain
app/langchain_arch/03_chat_model_demo.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_chat_model() -> ChatOpenAI:
    if not settings.deepseek_api_key:
        raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")

    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


def main():
    model = create_chat_model()

    messages = [
        SystemMessage(content="你是一个专业 AI Agent 课程助教。"),
        HumanMessage(content="请用一句话解释 LangChain ChatModel。"),
    ]

    response = model.invoke(messages)

    print("response type:", type(response))
    print("response message type:", response.type)
    print("content:")
    print(response.content)
    print("metadata:")
    print(response.response_metadata)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
ChatModel 是模型调用对象。

这里我们用：

```python
ChatOpenAI
```

来连接 DeepSeek。

因为 DeepSeek 支持 OpenAI-compatible 风格接口，所以我们可以配置：

```python
base_url=settings.deepseek_base_url
model="deepseek-chat"
```

这和第 14 章我们写 DeepSeekProvider 的思路是一样的。

只是现在 LangChain 帮我们封装了一层。

---

# 二十五、21｜示例四：PromptTemplate 架构
打开：

```plain
app/langchain_arch/04_prompt_template_demo.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate


def main():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "你是一个专业的 {role_name}。\n"
                "回答要求：\n"
                "1. 使用中文。\n"
                "2. 结构清晰。\n"
                "3. 不要编造。"
            ),
        ),
        (
            "human",
            "用户问题：{question}",
        ),
    ])

    prompt_value = prompt.invoke({
        "role_name": "AI Agent 课程助教",
        "question": "LangChain PromptTemplate 解决什么问题？",
    })

    print("prompt value type:", type(prompt_value))
    print("messages:")

    for message in prompt_value.messages:
        print(message.type, ":", message.content)
        print("-" * 60)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子展示 PromptTemplate 的职责：

```plain
输入变量
输出 messages
```

它并不会调用模型。

它只负责 Prompt 渲染。

所以它对应第 15 章的 PromptService。

大家要养成一个习惯：

```plain
Prompt 是 Prompt
Model 是 Model
Parser 是 Parser
```

每个组件职责要分清楚。

---

# 二十六、22｜示例五：Runnable 架构
打开：

```plain
app/langchain_arch/05_runnable_demo.py
```

写入：

```python
from langchain_core.runnables import RunnableLambda


def add_one(x: int) -> int:
    return x + 1


def multiply_two(x: int) -> int:
    return x * 2


def main():
    add_one_runnable = RunnableLambda(add_one)
    multiply_two_runnable = RunnableLambda(multiply_two)

    chain = add_one_runnable | multiply_two_runnable

    result = chain.invoke(10)

    print("result:", result)


if __name__ == "__main__":
    main()
```

运行：

```bash
python app/langchain_arch/05_runnable_demo.py
```

输出：

```plain
result: 22
```

---

## 【重点内容】
这个例子先不涉及大模型。

我们只理解 Runnable。

`10` 先进入：

```python
add_one
```

变成 `11`。

再进入：

```python
multiply_two
```

变成 `22`。

所以：

```python
chain = add_one_runnable | multiply_two_runnable
```

本质就是顺序组合。

后面：

```python
prompt | model | parser
```

也是同样道理。

---

# 二十七、23｜示例六：OutputParser 架构
打开：

```plain
app/langchain_arch/06_output_parser_demo.py
```

写入：

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_model():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


def main():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业 AI Agent 课程助教。"),
        ("human", "请用一句话解释：{topic}"),
    ])

    model = create_model()
    parser = StrOutputParser()

    chain = prompt | model | parser

    result = chain.invoke({
        "topic": "LangChain OutputParser",
    })

    print("result type:", type(result))
    print("result:", result)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这里我们第一次完整串起来：

```python
prompt | model | parser
```

执行流程是：

```plain
prompt：
把 topic 渲染成 messages

model：
把 messages 发给大模型

parser：
把 AIMessage 转成字符串
```

最后 result 是普通字符串。

这就是 LangChain 最基本的 Chain。

---

# 二十八、24｜示例七：Tool 架构
打开：

```plain
app/langchain_arch/07_tool_demo.py
```

写入：

```python
from langchain_core.tools import tool


@tool
def query_order(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。"""
    if order_id == "10001":
        return "订单 10001 已发货，物流公司顺丰，物流单号 SF10001。"

    if order_id == "10002":
        return "订单 10002 已付款，当前待发货。"

    return f"未查询到订单 {order_id}。"


def main():
    print("tool name:", query_order.name)
    print("tool description:", query_order.description)
    print("tool args:", query_order.args)

    result = query_order.invoke({
        "order_id": "10001",
    })

    print("result:", result)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子展示 LangChain Tool 的基本结构。

`@tool` 会把普通函数包装成工具。

工具有：

```plain
name
description
args
invoke
```

这和我们第 18 章手写 ToolDefinition 的结构非常像。

但是在企业项目里，不建议完全放弃我们自己的 ToolExecutor。

因为我们还需要：

```plain
权限判断
日志记录
结果脱敏
高风险确认
```

LangChain Tool 负责工具描述和调用抽象。

业务安全仍然要自己控制。

---

# 二十九、25｜示例八：Chain 架构总览
打开：

```plain
app/langchain_arch/08_chain_arch_demo.py
```

写入：

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_model():
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


def add_prefix(text: str) -> str:
    return f"【LangChain 架构解释】\n{text}"


def main():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个专业 AI Agent 课程助教。"),
        ("human", "请用三句话解释：{topic}"),
    ])

    model = create_model()
    parser = StrOutputParser()
    prefix = RunnableLambda(add_prefix)

    chain = prompt | model | parser | prefix

    result = chain.invoke({
        "topic": "Runnable 为什么是 LangChain 的核心",
    })

    print(result)


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子在：

```python
prompt | model | parser
```

后面又接了一个：

```python
RunnableLambda
```

这说明 LCEL 可以把模型组件和普通 Python 函数组合起来。

这很重要。

因为真实项目里，LLM 流程中经常有业务处理步骤。

比如：

```plain
输入清洗
输出脱敏
结果格式转换
日志记录
字段提取
```

这些都可以封装成 Runnable。

---

# 三十、26｜示例九：和原生架构做映射
打开：

```plain
app/langchain_arch/09_native_mapping_demo.py
```

写入：

```python
NATIVE_TO_LANGCHAIN_MAPPING = {
    "LLMMessage": "SystemMessage / HumanMessage / AIMessage / ToolMessage",
    "BaseLLMProvider": "ChatModel",
    "PromptService": "ChatPromptTemplate",
    "StructuredOutputService": "OutputParser",
    "ToolDefinition": "Tool / StructuredTool",
    "ToolRegistry": "tools list / 自建 Registry",
    "ToolExecutor": "Agent 工具执行 + 自建权限控制",
    "ChatService": "Chain / Runnable 编排",
    "ToolCallingService": "Agent",
    "RAGService": "Retriever + RAG Chain",
}


def main():
    for native, langchain in NATIVE_TO_LANGCHAIN_MAPPING.items():
        print(f"{native:<30} -> {langchain}")


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个脚本不调用模型。

它就是一个架构映射表。

课程里可以让学员反复看。

因为后面学习 LangChain 时，脑子里一定要有这张表。

这样就不会乱。

---

# 三十一、27｜创建测试脚本：版本检查
创建：

```plain
scripts/test_langchain_packages.py
```

写入：

```python
from app.langchain_arch.01_package_check import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_langchain_packages.py
```

---

# 三十二、28｜创建测试脚本：Message 检查
创建：

```plain
scripts/test_langchain_messages.py
```

写入：

```python
from app.langchain_arch.02_messages_demo import main


if __name__ == "__main__":
    main()
```

---

# 三十三、29｜创建测试脚本：Runnable 检查
创建：

```plain
scripts/test_langchain_runnable.py
```

写入：

```python
from app.langchain_arch.05_runnable_demo import main


if __name__ == "__main__":
    main()
```

---

# 三十四、30｜创建测试脚本：架构映射检查
创建：

```plain
scripts/test_langchain_arch_mapping.py
```

写入：

```python
from app.langchain_arch.09_native_mapping_demo import main


if __name__ == "__main__":
    main()
```

---

# 三十五、31｜项目一后续如何引入 LangChain
## 【建议路线】
```plain
第一步：
保留 FastAPI / PostgreSQL / Redis / Auth / Middleware 不变

第二步：
用 ChatPromptTemplate 替换部分 PromptService 渲染逻辑

第三步：
用 ChatOpenAI 替换部分 LLMProvider 调用

第四步：
用 StrOutputParser / PydanticOutputParser 替换结构化解析

第五步：
用 LangChain Tool 改造 query_order

第六步：
用 create_agent 或 LangGraph 改造 ToolCallingService
```

---

## 【重点内容】
我不建议大家一下子把第 19 章项目重构成 LangChain。

正确方式是逐步替换。

先替换最容易的：

```plain
Prompt
Model
Parser
```

再替换：

```plain
Tool
Agent
Retriever
```

同时保留我们自己的：

```plain
FastAPI 架构
数据库
Redis
权限
日志
异常处理
```

这才是企业项目比较稳的做法。

---

# 三十六、32｜架构原则一：LangChain 负责 LLM 编排，不负责业务系统
## 【重点内容】
这个原则一定要记住。

LangChain 适合负责：

```plain
Prompt
Model
Parser
Tool
Retriever
Agent
Chain
```

但不应该替代：

```plain
用户系统
权限系统
订单系统
数据库设计
缓存策略
限流策略
审计日志
支付退款
后台管理
```

所以我们的项目架构仍然是：

```plain
FastAPI 负责应用架构
LangChain 负责 LLM 编排层
LangGraph 负责复杂 Agent 状态流转
```

---

# 三十七、33｜架构原则二：不要把业务逻辑全塞进 Chain
## 错误写法
```plain
一个超级 chain 里处理所有业务：
鉴权
查库
缓存
Prompt
模型
工具
日志
响应
```

问题：

```plain
难排查
难测试
难复用
难做权限
难做异常处理
```

---

## 推荐写法
```plain
Router
  ↓
Service
  ↓
LangChain Chain
  ↓
Model / Tool / Parser
```

---

## 【重点内容】
Chain 是用来组合 LLM 相关组件的。

不要把所有业务系统逻辑都塞进去。

比如鉴权应该在 Dependency。

数据库操作应该在 Repository。

缓存策略应该在 Service。

LangChain Chain 只负责：

```plain
Prompt → Model → Parser
```

或者：

```plain
Retriever → Prompt → Model → Parser
```

这样边界更清楚。

---

# 三十八、34｜架构原则三：LangChain Tool 不等于可直接执行业务动作
## 【重点内容】
LangChain Tool 很方便。

但是工具调用涉及安全。

尤其是这些操作：

```plain
退款
删数据
发邮件
发短信
修改订单
创建工单
调用外部付费接口
```

不能因为模型选择了工具，后端就直接执行。

我们的做法应该是：

```plain
LangChain 负责让模型选择工具
业务系统负责权限、参数、确认、执行、日志
```

所以即使用 LangChain Tool，也可以外面包一层我们自己的 ToolExecutor。

---

# 三十九、35｜架构原则四：LangGraph 处理复杂状态，不要强行用普通 Chain
## 【重点内容】
普通 Chain 适合线性流程：

```plain
Prompt → Model → Parser
```

但是 Agent 经常不是线性的。

比如：

```plain
先判断意图
如果需要工具，调用工具
如果工具失败，重试
如果高风险，等待人工确认
如果信息不足，追问用户
如果完成，生成回答
```

这种流程更适合 LangGraph。

LangGraph 提供 StateGraph、节点、边、条件路由、checkpoint 等能力。

后面我们进入 LangGraph 阶段会详细讲。

这一章先知道边界：

```plain
线性 LLM 编排：LangChain Chain
复杂状态流转：LangGraph
```

---

# 四十、36｜LangChain 核心架构总结图
## 【实操】
```plain
用户请求
  ↓
FastAPI Router
  ↓
Service
  ↓
LangChain Runnable / Chain
  ├── PromptTemplate
  ├── ChatModel
  ├── OutputParser
  ├── Tool
  └── Retriever
  ↓
业务结果
  ↓
Repository / Redis / Response
```

如果是复杂 Agent：

```plain
用户目标
  ↓
LangGraph StateGraph
  ├── Node: LLM
  ├── Node: Tool
  ├── Node: Human Review
  ├── Edge: 条件路由
  └── Checkpoint: 状态保存
  ↓
最终结果
```

---

# 四十一、37｜常见错误一：老版本导入路径
错误：

```python
from langchain.chat_models import ChatOpenAI
```

新版本推荐：

```python
from langchain_openai import ChatOpenAI
```

---

## 【重点内容】
很多报错来自老教程。

如果你看到：

```plain
langchain.chat_models
langchain.llms
langchain.agents.initialize_agent
```

要警惕。

这些很多是旧版本教程里的写法。

本课程统一使用 LangChain 1.x 新体系。

LangChain v1 迁移文档也说明，`langchain` 包命名空间在 v1 中被明显收缩，重点聚焦 Agent 相关的核心构建块，旧功能迁移到了 `langchain-classic`。

---

# 四十二、38｜常见错误二：装了 langchain 但没装 langchain-openai
错误：

```plain
ModuleNotFoundError: No module named 'langchain_openai'
```

原因：

```plain
langchain-openai 是独立集成包
```

解决：

```bash
uv add "langchain-openai>=1.5,<1.6"
```

---

# 四十三、39｜常见错误三：把 HumanMessage 当成 user 字符串
错误理解：

```plain
HumanMessage 是新的角色
```

正确理解：

```plain
HumanMessage 对应 Chat API 里的 user
AIMessage 对应 assistant
SystemMessage 对应 system
ToolMessage 对应 tool
```

---

# 四十四、40｜常见错误四：不知道 chain 的输入输出
比如：

```python
chain = prompt | model | parser
```

一定要知道：

```plain
prompt 输入：dict
prompt 输出：PromptValue / messages

model 输入：messages
model 输出：AIMessage

parser 输入：AIMessage
parser 输出：str / dict / Pydantic 对象
```

如果输入输出不匹配，chain 就会报错。

---

# 四十五、41｜常见错误五：把 LangChain 当成业务系统
错误：

```plain
所有用户权限、缓存、数据库、业务规则都交给 LangChain
```

正确：

```plain
LangChain 负责 LLM 编排
业务系统仍然由 FastAPI + Service + Repository 负责
```

---

# 四十六、42｜常见错误六：版本不固定
错误：

```bash
uv add langchain langgraph
```

过几个月可能安装到新版本，代码不兼容。

推荐：

```bash
uv add "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6" \
       "langgraph>=1.2,<1.3"
```

然后提交：

```plain
uv.lock
```

---

# 四十七、43｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Message | 第 13 章 messages / role |
| ChatModel | 第 14 章 LLM Provider |
| PromptTemplate | 第 15 章 Prompt Engineering |
| Streaming | 第 16 章 stream_chat |
| OutputParser | 第 17 章 Structured Output |
| Tool | 第 18 章 Tool Calling |
| Chain / Runnable | 第 19 章 ChatService 编排 |
| Agent | 第 18 章 ToolCallingService 的升级版 |
| Retriever | 后续 RAG 阶段 |
| Callback / Tracing | 第 10 章日志与 trace_id |
| LangGraph | 后续复杂 Agent 状态图 |


---

# 四十八、44｜本章完整复习
这一章我们完成了：

```plain
1. 明确 LangChain 阶段的版本口径
2. 理解 LangChain 1.x 生态包拆分
3. 理解 langchain-core 的定位
4. 理解 langchain 的定位
5. 理解 langchain-openai 的定位
6. 理解 langchain-community 的定位
7. 理解 LangGraph 的定位
8. 理解 Message 架构
9. 理解 ChatModel 架构
10. 理解 PromptTemplate 架构
11. 理解 OutputParser 架构
12. 理解 Runnable 架构
13. 理解 LCEL 管道组合
14. 理解 Tool 架构
15. 理解 Agent 架构
16. 理解 Retriever 架构
17. 理解 Callback / Tracing 的作用
18. 理解 LangChain 和前 19 章原生代码映射
19. 创建 langchain_arch 示例目录
20. 编写版本检查脚本
21. 编写 Message 示例
22. 编写 ChatModel 示例
23. 编写 PromptTemplate 示例
24. 编写 Runnable 示例
25. 编写 OutputParser 示例
26. 编写 Tool 示例
27. 编写 Chain 架构示例
28. 编写原生映射示例
29. 总结项目一如何逐步引入 LangChain
30. 总结 LangChain 架构边界和常见错误
```

---

# 四十九、45｜课后任务一：检查本地 LangChain 版本
要求：

```plain
1. 安装课程指定版本范围
2. 运行 app/langchain_arch/01_package_check.py
3. 截图记录 langchain / langchain-core / langchain-openai / langgraph 版本
```

---

# 五十、46｜课后任务二：把第 15 章通用 Prompt 改成 ChatPromptTemplate
要求：

```plain
1. 使用 ChatPromptTemplate.from_messages
2. system 使用 GENERAL_CHAT_PROMPT_V1 的规则
3. human 使用 {user_question}
4. invoke 后打印 messages
```

---

# 五十一、47｜课后任务三：手写一个 Runnable 链
要求：

```plain
1. 定义 clean_question 函数
2. 定义 add_context 函数
3. 用 RunnableLambda 包装
4. 使用 clean_question | add_context 组合
5. 输入一个带空格的问题，输出清洗后的结果
```

---

# 五十二、48｜课后任务四：画 LangChain 核心架构图
要求必须包含：

```plain
Message
PromptTemplate
ChatModel
OutputParser
Runnable
Tool
Agent
Retriever
Callback
LangGraph
```

并标注：

```plain
哪些属于 langchain-core
哪些属于 langchain-openai
哪些属于 langchain
哪些属于 langgraph
```

---

# 五十三、49｜课后任务五：分析第 19 章项目一怎么接入 LangChain
要求回答：

```plain
1. ChatService 哪些逻辑可以用 Chain 替代？
2. PromptService 哪些逻辑可以用 ChatPromptTemplate 替代？
3. StructuredOutputService 哪些逻辑可以用 OutputParser 替代？
4. ToolCallingService 哪些逻辑可以用 Agent 替代？
5. 哪些逻辑不应该交给 LangChain？
```

---

# 五十四、50｜本章总结 
## 【重点内容】
好了，到这里，第 21 章我们就讲完了。

这一章我们没有急着做 RAG，也没有急着做 Agent。

我们先把 LangChain 的核心架构拆开讲了一遍。

大家一定要记住，LangChain 的核心不是某一个 API。

它的核心是一套抽象：

```plain
Message
PromptTemplate
ChatModel
OutputParser
Runnable
Tool
Retriever
Agent
Callback
```

其中 Runnable 是非常关键的统一执行协议。

LCEL 的：

```python
prompt | model | parser
```

本质上就是把多个 Runnable 串起来。

同时我们也明确了 LangChain 和我们前面项目的关系：

```plain
FastAPI 仍然负责应用架构
PostgreSQL 仍然负责数据持久化
Redis 仍然负责缓存和限流
LangChain 负责 LLM 编排
LangGraph 负责复杂 Agent 状态流转
```

这样后面我们进入 Model、Prompt、Structured Output、Tool、Agent、RAG 时，整个思路就不会乱。

---
