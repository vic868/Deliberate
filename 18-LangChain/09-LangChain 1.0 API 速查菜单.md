---
title: LangChain 1.0 API 速查菜单
tags: [langchain, langchain-1.0, api, 速查, cheatsheet, python, 索引]
created: 2026-11-11
version: LangChain 1.0
source: "L2阶段 / 04-day01 + 05-day02 + 06-day03 讲义PDF 与四份课件中的 V1.0 写法"
related:
  - "[[00-LangChain V1.0 学习总览]]"
  - "[[01-V1.0 重构与整体体系]]"
---

# LangChain 1.0 API 速查菜单

> [!tldr] 这一篇是干什么的
> **只收 LangChain 1.0 当前可用的 API**，按功能分组，每个都给「作用 + import 路径 + 最小写法」。不收 v0.3 旧 API、不收 `langchain-classic`、不收 Pydantic / FastAPI 的版本差异。
> 需要看「哪些废弃了、替代是什么」→ [[00-LangChain V1.0 学习总览]] §5.1；需要看原理和完整实战 → 按下面的菜单进 `01`–`08`。

> [!warning] 版本基线
> Python **3.10+**（课程 3.11）。包分工：`langchain_core.*` = 抽象与接口，`langchain.*` = Agent 高层 API，`langchain_community.*` = 具体集成，`langchain_openai` / `langchain_chroma` / `langchain_text_splitters` = 合作伙伴包，`langgraph.*` = 状态持久化。**看到 `from langchain.chains / prompts / llms import ...` 就是旧代码，本篇不收。**

```mermaid
flowchart TB
    subgraph BASE["接入层"]
        A1["ChatOpenAI / init_chat_model"]
        A2["DashScopeEmbeddings"]
        A3["SystemMessage / HumanMessage / AIMessage / ToolMessage"]
    end
    subgraph IO["Model I/O"]
        B1["PromptTemplate 家族"]
        B2["OutputParser 家族"]
        B3["content_blocks"]
    end
    subgraph CORE["组合层 · LCEL"]
        C1["Runnable: invoke / stream / batch"]
        C2["RunnableLambda / Parallel / Passthrough"]
    end
    subgraph DATA["数据层 · RAG"]
        D1["Loader → Splitter → Embeddings"]
        D2["VectorStore → as_retriever"]
    end
    subgraph AGENT["智能体层 · V1.0 主战场"]
        E1["@tool / bind_tools"]
        E2["create_agent"]
        E3["checkpointer + thread_id"]
        E4["Middleware"]
    end
    subgraph SERVE["服务层"]
        F1["add_routes / RemoteRunnable"]
    end
    BASE --> IO --> CORE --> AGENT --> SERVE
    DATA --> CORE
```

---

## 〇、菜单（点标题直达）

| # | 模块 | 解决什么 | 主要 API |
|---|---|---|---|
| 一 | [[#一、环境与模型接入\|环境与模型接入]] | 怎么把模型接进来 | `ChatOpenAI`、`init_chat_model`、`DashScopeEmbeddings`、四类 Message |
| 二 | [[#二、Model I/O\|Model I/O]] | 提示词怎么模板化、输出怎么解析 | `PromptTemplate` 家族、`OutputParser` 家族、`content_blocks` |
| 三 | [[#三、LCEL 与 Runnable\|LCEL 与 Runnable]] | 组件怎么组合成链 | `invoke / stream / batch`、`\|`、`RunnableLambda / Parallel / Passthrough`、`bind / with_types` |
| 四 | [[#四、RAG 数据连接\|RAG 数据连接]] | 文档怎么变成可检索上下文 | Loader、`RecursiveCharacterTextSplitter`、`Chroma / FAISS`、`as_retriever`、`EnsembleRetriever` |
| 五 | [[#五、Agent 与工具\|Agent 与工具]] | 让模型自己决定调用几次工具 | `@tool`、`bind_tools`、`create_agent`、`InMemorySaver`、`response_format` |
| 六 | [[#六、Middleware\|Middleware]] | 在模型/工具调用前后插逻辑 | 5 个内置中间件、6 个钩子、`AgentMiddleware` |
| 七 | [[#七、服务化\|服务化]] | 把链变成 HTTP 接口 | `add_routes`、`RemoteRunnable`、`with_types` |
| 八 | [[#八、一页速查卡\|一页速查卡]] | 「我要做 X → 用哪个 API」 | 全篇压缩成一张表 |
| 九 | [[#九、落地前核对清单\|落地前核对清单]] | import 与签名怎么验 | 4 条核对项 |

> [!tip] 怎么用这篇
> 写代码时从 **§八 速查卡** 找到那一行，再点回对应章节看完整代码片段；复习时按 §〇 菜单从上往下走一遍。所有代码沿用讲义约定 `client = get_lc_model_client()`，等价于 §一.2 的 `ChatOpenAI` 实例。

---

## 一、环境与模型接入

### 1.1 包与依赖

| 包 | 提供什么 | 典型 import |
|---|---|---|
| `langchain` | V1.0 Agent 高层 API | `langchain.agents`、`langchain.tools`、`langchain.messages` |
| `langchain-core` | 抽象与接口（`Runnable`、Prompt、Parser） | `langchain_core.*` |
| `langchain-community` | 第三方集成（加载器、向量库、工具包） | `langchain_community.*` |
| `langchain-openai` | OpenAI 兼容协议的 Chat Model | `langchain_openai.ChatOpenAI` |
| `langchain-chroma` / `langchain-text-splitters` | 向量库 / 切分器 | 见 §四 |
| `langgraph` | 图运行时与状态持久化 | `langgraph.checkpoint.memory.InMemorySaver` |
| `langserve` | 部署成 REST API | `langserve.add_routes` |

```bash
pip install langchain langchain-core langchain-community langchain-openai \
            langchain-chroma langchain-text-splitters langgraph langserve
```

### 1.2 对话模型：OpenAI 兼容端点（本课程默认）

```python
import os
from langchain_openai import ChatOpenAI

client = ChatOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen-max-latest",
    temperature=0,
)
result = client.invoke([("system", "请翻译成中文"), ("human", "hello")])
```

阿里百炼、DeepSeek、腾讯混元等**只要兼容 OpenAI 协议**都用这个类，换 `base_url` + `model` 即可。讲义把它封装成 `models.py::get_lc_model_client()`。

| 情况 | 用哪个 |
|---|---|
| OpenAI 兼容 API | `ChatOpenAI` + `base_url` |
| 不兼容 OpenAI 协议 | `init_chat_model`（`langchain.chat_models`） |
| 厂商专属类 | `langchain_community.chat_models.ChatTongyi` 等 |

> [!note] 讲义未给完整代码的两个入口
> `init_chat_model` 与 `ChatTongyi` 在讲义里只出现在选型表中，没给可运行示例；上面按用途列出，具体参数签名以当前装的版本为准。日常开发用 §1.2 的 `ChatOpenAI` 即可覆盖绝大多数场景。

### 1.3 嵌入模型（与对话模型不是同一个客户端）

```python
import os
from langchain_community.embeddings import DashScopeEmbeddings

embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)
```

> [!important] 别混
> `client` 是对话模型，`embeddings` 是嵌入模型，两者用途、模型名、计费都不同；RAG 里两个都要用到。

### 1.4 消息类型

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

msgs = [
    SystemMessage(content="你是助手"),
    HumanMessage(content="你好"),
]
```

| 类型 | 含义 |
|---|---|
| `SystemMessage` | 行为准则 / 角色 / 约束 |
| `HumanMessage` | 用户输入 |
| `AIMessage` | 模型回复，含 `tool_calls`、`content_blocks` |
| `ToolMessage` | 工具执行结果 |

---

## 二、Model I/O

### 2.1 提示词模板家族

| API | 作用 | import |
|---|---|---|
| `PromptTemplate` | 字符串模板 | `langchain_core.prompts` |
| `ChatPromptTemplate` | 多角色消息模板（V1.0 主用） | `langchain_core.prompts` |
| `SystemMessagePromptTemplate` / `HumanMessagePromptTemplate` / `AIMessagePromptTemplate` | 显式角色模板 | `langchain_core.prompts` |
| `FewShotPromptTemplate` / `FewShotChatMessagePromptTemplate` | 少样本示例 | `langchain_core.prompts.few_shot` |
| `MessagesPlaceholder` | 在模板里留历史消息的槽位 | `langchain_core.prompts` |
| `.partial()` | 先固定部分变量，其余运行时再填 | — |

```python
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate

prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template("请将以下内容翻译成 {language}"),
    ("human", "{text}"),          # 元组简写，等价 HumanMessagePromptTemplate
])

prompt.format(**{"language": "意大利文", "text": "朋友啊再见！"})           # → str
prompt.format_messages(**{"language": "意大利文", "text": "朋友啊再见！"})   # → 消息列表
prompt.format_prompt(**{"language": "意大利文", "text": "朋友啊再见！"})     # → PromptValue
```

> [!warning] 三种取值别用错
> `format()` 得到纯字符串、**角色语义会丢失**；多轮对话 / 工具调用必须用 `format_messages()` 或 `format_prompt()`，否则 system 指令被当成普通文本。LCEL 链里框架自动走 `format_prompt`，不用手动调。

```python
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts.few_shot import FewShotPromptTemplate

p = PromptTemplate.from_template("回答：{question}")
half = p.partial(date="2026-11-11")          # 先固定 date
```

### 2.2 输出解析器家族

| 解析器 | 输出 | import |
|---|---|---|
| `StrOutputParser` | 纯字符串（去掉 `AIMessage` 外壳，最常用） | `langchain_core.output_parsers` |
| `JsonOutputParser` | JSON / `dict` | 同上 |
| `CommaSeparatedListOutputParser` | `list` | 同上 |
| `DatetimeOutputParser` | `datetime` | 同上 |
| `XMLOutputParser` | XML 结构 | 同上 |

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

chain = ChatPromptTemplate.from_template("翻译成{language}：{text}") | client | StrOutputParser()
print(chain.invoke({"language": "意大利文", "text": "朋友啊再见！"}))
```

**带格式约束的解析器**必须把格式指令注入提示词：

```python
from langchain_core.output_parsers import DatetimeOutputParser
from langchain_core.prompts import PromptTemplate

parser = DatetimeOutputParser()
prompt = PromptTemplate.from_template(
    "回答：{question}\n{format_instructions}",
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
chain = prompt | client | parser
```

### 2.3 `content_blocks`：V1.0 标准输出

跨厂商统一为 `text / reasoning / tool_call / citation` 内容块，切换模型不用改解析代码。

```python
ai_msg = client.invoke("你是谁")
for block in ai_msg.content_blocks:
    if block["type"] == "reasoning":
        print("推理:", block["reasoning"])
    elif block["type"] == "text":
        print("回答:", block["text"])
    elif block["type"] == "tool_call":
        print("请求调用:", block["name"], block["args"])
```

### 2.4 `bind_tools`：只要调用请求，不执行

```python
from langchain.tools import tool
from langchain.messages import HumanMessage

@tool
def get_weather(location: str) -> str:
    """获取指定地点天气"""       # docstring 就是给模型看的工具说明
    return f"{location} 晴 25 度"

model_with_tools = client.bind_tools([get_weather])
ai_msg = model_with_tools.invoke([HumanMessage(content="北京天气怎么样？")])
print(ai_msg.tool_calls)          # 只拿到调用请求，执行由应用负责
```

> [!tip] 分工
> **模型只发起工具调用请求，执行与结果回灌由应用负责**。要自动完成「模型 → 工具 → 模型」多轮往返，用 §五 的 `create_agent`。

---

## 三、LCEL 与 Runnable

> LCEL 在 V1.0 **没有废弃**，它是组件组合的通用协议，`create_agent` 也建立在这套抽象上。废弃的只是预制 Chain 类。

### 3.1 Runnable 统一接口

| 方法 | 作用 |
|---|---|
| `.invoke(x)` / `.ainvoke(x)` | 单次同步 / 异步调用 |
| `.stream(x)` / `.astream(x)` | 流式输出 |
| `.batch([x1, x2])` / `.abatch(...)` | 批量调用 |
| `.bind(k=1)` | 固定额外参数 |
| `.with_types(input_type=..., output_type=...)` | 声明输入输出 schema |

### 3.2 管道与顺序链

```python
from langchain_core.runnables import RunnableSequence

chain = prompt | client | StrOutputParser()          # 常用
chain2 = RunnableSequence(prompt, client, StrOutputParser())   # 等价显式写法
```

数据流 `dict → PromptValue → AIMessage → str`，每一步的输出类型必须匹配下一步的输入类型。

### 3.3 RunnableLambda / `@chain`

```python
from operator import itemgetter
from langchain_core.runnables import RunnableLambda, chain

def length(text):
    return len(text)

@chain                                    # 装饰器也能把函数变成 Runnable
def wrapped(_dict):
    return _dict["a"] * 2

c = {"a": itemgetter("foo") | RunnableLambda(length)} | prompt
```

### 3.4 RunnableParallel：字典字面量自动并行

```python
from langchain_core.runnables import RunnableParallel, RunnableLambda

add_one = RunnableLambda(lambda x: x + 1)
chain = add_one | RunnableParallel(mul_two=RunnableLambda(lambda x: x * 2),
                                   mul_three=RunnableLambda(lambda x: x * 3))
print(chain.invoke(1))     # {'mul_two': 4, 'mul_three': 6}
```

> [!warning] LCEL 里的 `{...}` 不是普通 dict
> 它会自动转成 `RunnableParallel`，**每个值必须是 Runnable 或可调用对象**；直接塞一个未执行的 Runnable 对象当 `context` 不会生效。

### 3.5 RunnablePassthrough / `assign()`

```python
from langchain_core.runnables import RunnablePassthrough

r = RunnableParallel(
    passed=RunnablePassthrough(),                 # 原样透传
    modified=RunnableLambda(lambda x: x["num"] + 1),
)
r2 = RunnablePassthrough().assign(              # 透传的同时追加字段
    query=RunnableLambda(lambda x: x["question"] + " 精简"),
)
```

### 3.6 调试 API

```python
import langchain
langchain.debug = True                    # 打印每个组件的输入 / 输出

print(chain.input_schema.model_json_schema())
print(chain.output_schema.model_json_schema())
print(chain.get_prompts())                # 链里所有提示模板
chain.get_graph().print_ascii()           # 结构图，需 pip install grandalf
```

---

## 四、RAG 数据连接

### 4.1 全链路

```mermaid
flowchart LR
    L["Loader.load()"] --> D["Document"] --> S["TextSplitter"] --> E["Embeddings"] --> V["VectorStore"] --> R["as_retriever()"] --> C["LCEL 链"]
```

### 4.2 文档加载器（统一接口 `load()` → `Document`）

| 数据源 | 加载器 |
|---|---|
| TXT | `TextLoader` |
| PDF | `PyPDFLoader` |
| CSV | `CSVLoader` |
| JSON | `JSONLoader` |
| HTML | `UnstructuredHTMLLoader` |
| Markdown | `UnStructuredMarkdownLoader` |
| 整个目录 | `DirectoryLoader` |
| 网页 | `WebBaseLoader` |

```python
import bs4
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document

loader = WebBaseLoader(
    web_path=["https://example.com/article"],
    bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("main-left left", "title"))),
)
docs = loader.load()          # → list[Document]，含 page_content 与 metadata
```

> `doc/docx/xlsx` 需 `UnstructuredWordDocumentLoader` / `UnstructuredExcelLoader` 一类（多依赖 `unstructured`），或先转 PDF/MD 再走统一链路。

### 4.3 切分器

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
documents = splitter.split_documents(docs)
```

### 4.4 向量库与检索器

```python
from langchain_chroma import Chroma

vector_store = Chroma.from_documents(documents=documents, embedding=embeddings)
print(vector_store.similarity_search("狸花猫"))
print(vector_store.similarity_search_with_score("狸花猫"))   # Chroma 默认 L2，分数越小越相似

retriever = vector_store.as_retriever()      # 检索器 = 向量库的统一包装器
```

| 创建方式 | 写法 | 擅长 |
|---|---|---|
| FAISS 语义检索 | `FAISS.from_texts(texts, embeddings).as_retriever()` | 语义相近、改写过的问法 |
| Chroma 语义检索 | `Chroma.from_documents(docs, embeddings).as_retriever()` | 同上，Document 列表建库 |
| BM25 关键词检索 | `BM25Retriever.from_texts(texts)` | 精确术语、型号、编号、人名 |
| 混合检索 | `EnsembleRetriever(retrievers=[r1, r2], weights=[0.7, 0.3])` | 两者互补 |

> 依赖：`BM25Retriever` 需 `rank_bm25`，`FAISS` 需 `faiss-cpu`；`weights` 需结合各检索器得分量级调，默认等权不等于最优。切换向量库时统一用 `as_retriever()`，查询代码不改。

### 4.5 最小 RAG 链（V1.0 推荐写法）

```python
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

docs_find = RunnableLambda(vector_store.similarity_search).bind(k=1)
prompt = ChatPromptTemplate.from_messages([
    ("human", "仅用上下文回答：{question}\n上下文：{context}"),
])
chain = (
    {"question": RunnablePassthrough(), "context": docs_find} | prompt | client
)
resp = chain.invoke("请介绍一下猫")
print(resp.content)
```

> [!tip] 为什么必须有 `RunnablePassthrough()`
> 定义链时还不知道用户要问什么，靠它把问题**动态透传**进来，与 `context` 并行组成提示词入参。这是 `{"...": ...}` 变 `RunnableParallel` 的典型用法。

---

## 五、Agent 与工具

### 5.1 `@tool` 与 Toolkit

```python
from langchain.tools import tool

@tool
def get_current_time(input: str = "") -> str:
    """获取当前时间"""            # docstring 决定模型选不选它
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

`Toolkit` 是为特定目标打包好的一组工具：

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

db = SQLDatabase.from_uri("mysql+mysqldb://user:pwd@127.0.0.1:3306/world?charset=utf8mb4")
print(db.get_usable_table_names())
tools = SQLDatabaseToolkit(db=db, llm=client).get_tools()
```

### 5.2 `create_agent`：V1.0 唯一入口

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model=client,
    tools=[get_current_time],
    system_prompt="你是人工智能助手。",
    checkpointer=InMemorySaver(),       # 内置消息历史管理
)

response = agent.invoke(
    {"messages": [{"role": "user", "content": "现在几点了？"}]},
    config={"configurable": {"thread_id": "user_1"}},
)
answer = response["messages"][-1].content
```

| 参数 | 作用 |
|---|---|
| `model` | 对话模型实例或模型名字符串 |
| `tools` | `@tool` 函数或 Toolkit 产出的工具列表 |
| `system_prompt` | 行为约束；复杂场景把规则写清楚比调模型更有效 |
| `checkpointer` | 状态持久化；传了它才能用 `thread_id` 做多轮记忆 |
| `middleware` | 流程拦截，见 §六 |
| `response_format` | 结构化输出，见 5.4 |

**输入输出约定**：输入 `{"messages": [...]}`，输出是含完整执行状态的 dict，最终答案取 `result["messages"][-1].content`；`thread_id` 区分用户 / 会话。可选错误重试、工具结果回灌、消息历史全部由内置循环接管。

### 5.3 审计工具调用

```python
from langchain.messages import AIMessage

for msg in response["messages"]:
    if isinstance(msg, AIMessage) and msg.tool_calls:
        for call in msg.tool_calls:
            print(call["name"], call["args"])
```

### 5.4 `response_format`：结构化输出进主循环

```python
from pydantic import BaseModel, Field

class Answer(BaseModel):
    summary: str = Field(description="结论")
    score: int = Field(ge=1, le=5, description="置信分")

agent = create_agent(model=client, tools=[], response_format=Answer)
result = agent.invoke({"messages": [{"role": "user", "content": "总结这段话"}]})
print(result["structured_response"])     # 校验后的 Pydantic 对象
```

> [!note] 出处说明
> 讲义只给了机制描述（「传 Pydantic 类 → 捕获校验 → 放在状态的 `structured_response` 键」），未给完整代码；上面按该机制补成可对照的写法，**落地前核对当前装的版本**。好处是结构化输出进主循环，不再额外多一次 LLM 调用。

---

## 六、Middleware

### 6.1 内置中间件（挂在 `create_agent(middleware=[...])`）

| 中间件 | 作用 |
|---|---|
| `PIIMiddleware` | 发送给模型前屏蔽 / 遮掩敏感信息 |
| `SummarizationMiddleware` | 对话历史过长时自动压缩（**按会话次数上限**触发，不是 token 数） |
| `HumanInTheLoopMiddleware` | 敏感工具执行前暂停，等待人工批准 / 编辑 / 拒绝 |
| `ModelCallLimitMiddleware` | 限制模型调用次数，防死循环与成本失控 |
| `ToolCallLimitMiddleware` | 限制工具调用次数，可全局或按工具 |

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model=client,
    tools=[read_user_data],
    middleware=[
        PIIMiddleware("email", strategy="redact",
                      apply_to_input=True, apply_to_output=True),
        PIIMiddleware("ip",
                      detector=r"(?:13[0-9]|14[01456879]|15[0-35-9])\d{8}",
                      strategy="redact",
                      apply_to_input=True, apply_to_output=True),
    ],
    system_prompt="你是一个安全的数据处理助手",
)
```

### 6.2 六个钩子

| 钩子 | 类型 | 触发时机 |
|---|---|---|
| `wrap_model_call` | 环绕 | 每次模型调用外层包装 |
| `wrap_tool_call` | 环绕 | 每次工具调用外层包装 |
| `before_model` | 前后型 | 模型调用前 |
| `after_model` | 前后型 | 模型调用后 |
| `before_agent` | 前后型 | **整次 invoke 一次** |
| `after_agent` | 前后型 | **整次 invoke 一次** |

> [!warning] 选错钩子会差好几倍
> `before_agent` / `after_agent` 每次 `invoke` 只触发一次；其余四个处在 Agent 循环里，**一次会话可能触发多次**。写限流、计费、审计时别放错。

### 6.3 自定义中间件（基于类，可挂多个钩子）

```python
from typing import Any, Dict
from langchain.agents.middleware import AgentMiddleware

class MaskMiddleware(AgentMiddleware):
    def before_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        for message in state.get("messages", []):
            if hasattr(message, "content") and isinstance(message.content, str):
                message.content = message.content.replace("@", "[AT]")
        return state

    def after_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return state

agent = create_agent(model=client, tools=tools,
                     checkpointer=InMemorySaver(),
                     middleware=[MaskMiddleware()])
```

> 课程还提到**基于装饰器**的单钩子写法（对应 `wrap_model_call` 等），但未给完整代码；优先用内置中间件，自定义前先核对 `AgentMiddleware` 的钩子签名——讲义里专门有过一段「修复的脱敏中间件：使用正确的参数签名」，说明这个 API 曾变过。

---

## 七、服务化

### 7.1 `add_routes`

```python
from fastapi import FastAPI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langserve import add_routes

chain = ChatPromptTemplate.from_messages([
    ("system", "请将以下内容翻译成 {language}"),
    ("human", "{text}"),
]) | client | StrOutputParser()

app = FastAPI(title="翻译服务")
add_routes(app, chain, path="/tslServer")     # 全部部署代码就这一行
```

| 自动端点 | 作用 |
|---|---|
| `POST /{path}/invoke` | 完整调用 |
| `POST /{path}/stream` | 流式返回 |
| `POST /{path}/batch` | 批量 |
| `/{path}/input_schema`、`/output_schema` | schema |
| `/{path}/playground` | 在线调试页 |
| `GET /docs`、`/redoc` | 交互式文档 |

### 7.2 自定义输入输出类型

```python
from pydantic import BaseModel
from typing import Optional, List

class CustomInput(BaseModel):
    query: str
    context: Optional[str] = None

class CustomOutput(BaseModel):
    answer: str
    sources: List[str]

typed_chain = chain.with_types(input_type=CustomInput, output_type=CustomOutput)
add_routes(app, typed_chain, path="/custom-qa")
```

### 7.3 客户端调用

```python
from langserve import RemoteRunnable

client_remote = RemoteRunnable("http://localhost:8000/tslServer")
print(client_remote.invoke({"language": "意大利文", "text": "为了部落！"}))
# RemoteRunnable 实现了 Runnable 接口，也能 .batch() / .stream()
```

```bash
curl -X POST 'http://localhost:8000/tslServer/invoke' \
  -H 'Content-Type: application/json' \
  -d '{"input": {"language": "意大利文", "text": "为了部落！"}}'
```

> [!important] 请求体别猜
> 单输入链与多变量字典链推导出的 Request schema 不同，`{"question": ...}` 与 `{"input": {...}}` 都可能是对的。**打开 `/docs` 看该端点生成的 schema 照着填**，这是联调时 422 的主要来源。

---

## 八、一页速查卡

| 我要做什么 | 用哪个 API | 最小写法 |
|---|---|---|
| 接一个 OpenAI 兼容模型 | `ChatOpenAI` | `ChatOpenAI(api_key=..., base_url=..., model=...)` |
| 接非兼容模型 | `init_chat_model` | `init_chat_model(model="...")`（签名按装的版本核对） |
| 做文本向量 | `DashScopeEmbeddings` | `DashScopeEmbeddings(model="text-embedding-v3", ...)` |
| 写多角色提示词 | `ChatPromptTemplate` | `ChatPromptTemplate.from_messages([("system", ...), ("human", "{text}")])` |
| 留历史消息槽位 | `MessagesPlaceholder` | `MessagesPlaceholder(variable_name="history")` |
| 先固定部分变量 | `.partial()` | `prompt.partial(date="2026-11-11")` |
| 去掉 `AIMessage` 外壳 | `StrOutputParser` | `chain = prompt \| client \| StrOutputParser()` |
| 要 JSON / datetime 等结构 | `JsonOutputParser` 等 | `partial_variables={"format_instructions": parser.get_format_instructions()}` |
| 统一读各厂商输出 | `content_blocks` | `for block in ai_msg.content_blocks: ...` |
| 把函数变成工具 | `@tool` | `@tool` + 带 docstring 的函数 |
| 只要工具调用请求 | `.bind_tools()` | `client.bind_tools([my_tool])` |
| 把组件串成链 | `\|` | `prompt \| client \| parser` |
| 自定义函数入链 | `RunnableLambda` / `@chain` | `RunnableLambda(func)` |
| 并行准备多个字段 | `RunnableParallel` / 字典字面量 | `{"question": ..., "context": ...}` |
| 透传原始输入 | `RunnablePassthrough` | `RunnablePassthrough()` / `.assign(k=v)` |
| 固定额外参数 | `.bind()` | `RunnableLambda(fn).bind(k=1)` |
| 读网页 / PDF / CSV | Loader `.load()` | `WebBaseLoader(web_path=[...]).load()` |
| 切分文档 | `RecursiveCharacterTextSplitter` | `splitter.split_documents(docs)` |
| 建向量库 | `Chroma.from_documents` | `Chroma.from_documents(documents=docs, embedding=embeddings)` |
| 换向量库不改查询代码 | `.as_retriever()` | `vector_store.as_retriever()` |
| 关键词 + 语义混合检索 | `EnsembleRetriever` | `EnsembleRetriever(retrievers=[r1, r2], weights=[0.7, 0.3])` |
| 创建 Agent | `create_agent` | `create_agent(model=client, tools=tools, system_prompt=...)` |
| 多轮记忆 | `checkpointer` + `thread_id` | `checkpointer=InMemorySaver()` + `config={"configurable": {"thread_id": "u1"}}` |
| 取 Agent 最终答案 | — | `result["messages"][-1].content` |
| 结构化输出 | `response_format` | `create_agent(..., response_format=YourModel)` |
| 打包一组工具 | `SQLDatabaseToolkit` | `SQLDatabaseToolkit(db=db, llm=client).get_tools()` |
| 脱敏 / 限流 / 人工审批 | 内置中间件 | `create_agent(..., middleware=[PIIMiddleware(...)])` |
| 自定义拦截逻辑 | `AgentMiddleware` | 实现 `before_model` / `after_model` 等钩子 |
| 部署成 HTTP | `add_routes` | `add_routes(app, chain, path="/qa")` |
| 声明接口输入输出类型 | `.with_types()` | `chain.with_types(input_type=..., output_type=...)` |
| 从客户端调服务 | `RemoteRunnable` | `RemoteRunnable(url).invoke({...})` |
| 看链结构 / 排错 | `get_graph` / `langchain.debug` | `chain.get_graph().print_ascii()`；`langchain.debug = True` |

---

## 九、落地前核对清单

1. **import 路径按装的版本验**：V1.0 里 `Runnable` / Prompt / Parser 在 `langchain_core.*`，Agent / Tool / Message 在 `langchain.*`，第三方集成在 `langchain_community.*`；合作伙伴包（Chroma、TextSplitters）有独立包名。
2. **请求体打开 `/docs` 看 schema**，不要照抄任何示例的固定格式。
3. **`response_format` 与自定义中间件钩子签名**讲义只给机制 / 演示代码，且钩子签名曾变动，落地前核对当前版本文档。
4. **包版本基线**：Python 3.10+（课程 3.11）；`BM25Retriever` 需 `rank_bm25`、`FAISS` 需 `faiss-cpu`、`get_graph().print_ascii()` 需 `grandalf`。

> [!note] 与系列笔记的关系
> 本篇是**纯 API 查用层**，只收 V1.0 当前写法；原理、完整实战、课件增量与勘误分别在 [[01-V1.0 重构与整体体系]]～[[08-Day03 课堂复盘 RAG 实战与工具中间件]]。旧 API 与替代对照在 [[00-LangChain V1.0 学习总览]] §5.1。
