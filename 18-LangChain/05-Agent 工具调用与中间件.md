---
title: Agent 工具调用与中间件（V1.0 主战场）
tags: [langchain, agent, create-agent, tool-calling, middleware, sql, python]
created: 2026-11-08
related:
  - "[[00-LangChain V1.0 学习总览]]"
  - "[[01-V1.0 重构与整体体系]]"
  - "[[02-Model I-O 模型提示词与输出解析]]"
source: "LangChainV1.0讲义.pdf P15–P16、P45–P64"
---

# Agent 工具调用与中间件（V1.0 主战场）

> [!abstract] 一句话
> 只聊天的大模型用途有限；让它**像人一样使用工具**才真正打开场景（MCP、Agent2Agent 底层都绕不开工具调用）。核心分工是：**模型只负责"决定要调哪个工具、传什么参数"，执行工具的是我们的应用**。V1.0 用 `create_agent` 把这个往返循环内置了。

```mermaid
flowchart LR
    U["用户问题"] --> A["create_agent"]
    A --> M["模型：判断是否需要工具"]
    M -->|需要| TC["tool_call 内容块"]
    TC --> EXEC["应用执行工具"]
    EXEC -->|ToolMessage| M
    M -->|不需要| ANS["最终答案<br/>messages[-1].content"]
    MW["Middleware<br/>before/after_model 钩子"] -.拦截.-> M
```

---

## 一、工具 Tools 的五要素

工具是「代理、链或 LLM 用来与世界互动的接口」，包含：

| 要素 | 说明 |
|---|---|
| 名称 | 模型据此选择工具 |
| 描述 | **docstring 就是给模型看的说明书**，写得含糊会选错工具 |
| 输入的 JSON Schema | 由函数类型标注自动生成 |
| 要调用的函数 | 实际执行逻辑 |
| 结果是否直接返回用户 | 默认交回模型继续推理 |

`Toolkits` 是为特定目标打包好的一组工具（如 `SQLDatabaseToolkit`）。

### 1.1 定义与绑定

```python
from datetime import datetime
from langchain.tools import tool

@tool
def get_current_time(input: str = "") -> str:
    """获取当前时间"""
    return f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}。"

@tool
def open_browser(url: str) -> str:
    """打开浏览器访问指定网址"""
    import webbrowser
    webbrowser.open(url)
    return f"已打开浏览器访问 {url}"

tools = [get_current_time, open_browser]

# 绑定到大模型（不带 Agent，只观察模型"发起请求"这一步）
client_with_tools = client.bind_tools(tools)
resp = client_with_tools.invoke([HumanMessage(content="现在几点了？")])
print(resp.tool_calls)        # [{'name': 'get_current_time', 'args': {...}, ...}]
```

> [!important] 讲义特意强调的那句
> 「大模型判断出需要工具，但**工具的使用不是大模型负责的，而应该是我们的应用负责的**」。所以 `bind_tools` 之后你只拿到一个调用请求；要得到最终结果，往往需要"模型 → 工具结果 → 模型"多次交互。`create_agent` 就是把这个循环自动化。

内置工具（如 `TavilySearchResults`）与自定义工具在使用上**并无本质差别**，都是 `bind_tools([...])` / 交给 Agent。

---

## 二、`create_agent` 完整用法

```python
import os
from langchain.agents import create_agent
from langchain.messages import SystemMessage
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

llm = ChatOpenAI(
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    model_name="qwen-max",
)

@tool
def get_current_time(input: str = "") -> str:
    """获取当前时间"""
    return f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# 短期记忆：Checkpointer 实现线程级持久化
memory = InMemorySaver()

agent = create_agent(
    model=llm,
    tools=[get_current_time],
    system_prompt="你是人工智能助手。需要帮助用户解决各种问题。",
    checkpointer=memory,       # 内置消息历史管理
)

# v1.0 输入是标准 messages 列表；thread_id 区分用户 / 会话
response = agent.invoke(
    {"messages": [{"role": "user", "content": "现在几点了？"}]},
    config={"configurable": {"thread_id": "user_1"}},
)

# 输出是含完整执行状态的 dict，最终答案取最后一条消息
answer = response["messages"][-1].content
```

### 2.1 v0.3 vs v1.0

| | v0.3 | v1.0 |
|---|---|---|
| 创建 | `initialize_agent(tools, llm, agent=AgentType.OPENAI_FUNCTIONS, ...)` | `create_agent(model, tools, system_prompt, checkpointer, middleware)` |
| 循环 | `AgentExecutor` 驱动 | LangGraph 运行时内置 Tool Calling 循环 |
| 记忆 | `ConversationBufferMemory` | `checkpointer` + `thread_id` |
| 错误 | `handle_parsing_errors=True` 手工配 | 参数填错自动捕获并反馈给模型自我修正重试 |
| 输入 / 输出 | `{"input": "..."}` / `output` | `{"messages": [...]}` / `{"messages": [...]}`，含中间步骤 |

> [!tip] 取答案的固定写法
> `result["messages"][-1].content`。讲义里还演示了从消息历史里筛 `AIMessage.tool_calls` 来提取实际执行过的 SQL，用于审计和调试。

---

## 三、实战：用工具查 MySQL 数据库

### 3.1 连接数据库

```python
import pymysql
pymysql.install_as_MySQLdb()      # PyMySQL 适配（需 pip install mysqlclient / SQLAlchemy）

from langchain_community.utilities import SQLDatabase

MYSQL_URI = "mysql+mysqldb://root:root123456@127.0.0.1:3306/world?charset=utf8mb4"
db = SQLDatabase.from_uri(MYSQL_URI)
print(db.get_usable_table_names())
print(db.run("select * from country limit 1"))
```

### 3.2 自定义工具绑定（观察 tool_calls）

```python
@tool
def get_table_names():
    """获取数据库中的所有表名"""
    return db.get_table_names()

client_with_tools = client.bind_tools([get_table_names])
resp = client_with_tools.invoke([HumanMessage(content="请从国家表中查询出China的所有数据")])
print(resp.tool_calls)
```

### 3.3 v0.3 版：手工 LCEL 拼出 SQL 链（讲义用来讲清数据流动）

要回答这个问题，需要 5 步：① 查表名与字段 → ② 结果回给模型 → ③ 生成 SQL → ④ 执行 SQL → ⑤ 结果回给模型生成答案。

```python
import re
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_classic.chains.sql_database.query import create_sql_query_chain
from langchain_community.tools import QuerySQLDatabaseTool

# 模型生成的是 ```sql ... ``` 包裹的文本，先清洗才能执行
class SQLCleaner(StrOutputParser):
    def parse(self, text: str) -> str:
        match = re.search(r"```sql(.*?)```", text, re.DOTALL)
        sql = match.group(1).strip() if match else text.strip()
        return re.sub(r"^SQLQuery:", "", sql).strip()

sql_make_chain = create_sql_query_chain(client, db) | SQLCleaner()

answer_prompt = PromptTemplate.from_template(
    """给定以下用户问题、可能的SQL语句和SQL执行后的结果，回答用户问题
Question: {question}
SQL Query: {query}
SQL Result: {result}
回答:"""
)
execute_sql_tools = QuerySQLDatabaseTool(db=db)

# 关键：assign 一步步攒齐 question / query / result 三个字段
chain = (
    RunnablePassthrough.assign(query=sql_make_chain)
    .assign(result=itemgetter("query") | execute_sql_tools)
    | answer_prompt | client | StrOutputParser()
)
print(chain.invoke({"question": "请从国家表中查询出China的相关数据"}))
```

> [!important] 执行顺序（讲义专门讲的一句）
> `result=itemgetter('query') | execute_sql_tools` 实际是 **`result = (itemgetter('query') | execute_sql_tools)`**：先取 `query` 字段 → 交给执行工具 → 结果赋给 `result`。不是先赋值再执行。

### 3.4 v1.0 版：一个 `create_agent` 搞定

```python
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.messages import AIMessage

toolkit = SQLDatabaseToolkit(db=db, llm=client)
tools = toolkit.get_tools()

system_prompt = """你是一个精通MySQL数据库的AI助手。你的任务是查询数据库并回答用户问题。
【极其重要的规则】
1. 绝对不要猜测表名。你必须先使用工具查看数据库里到底有哪些表。
2. 绝对不要猜测字段名。确定表名后，必须使用工具查看表的 Schema（结构）。
3. 只有在确认了表名和字段名之后，才能编写 SQL 语句。
4. 如果 SQL 执行报错，仔细查看错误信息，修正后重试。
注意：
- 永远不要执行 DROP, DELETE, INSERT, UPDATE 等修改数据的操作。
- 只输出最终的自然语言回答，不要暴露内部的 SQL 逻辑，除非用户要求。
"""

agent = create_agent(model=client, tools=tools, system_prompt=system_prompt)

result = agent.invoke({"messages": [("user", "请从国家表中查询出China的相关数据")]})

# 从消息历史里审计实际执行的 SQL
for msg in result["messages"]:
    if isinstance(msg, AIMessage) and msg.tool_calls:
        for call in msg.tool_calls:
            if call["name"] == "sql_db_query":
                print("最终使用的 SQL:", call["args"].get("query"))

print("最终回答:", result["messages"][-1].content)
```

> [!tip] 这段对比是本课最值钱的部分
> v0.3 要手工用 `RunnablePassthrough.assign` 编排 5 步、自己写 `SQLCleaner`、自己接执行工具；v1.0 用 `create_agent` + `SQLDatabaseToolkit` 把**工具选择、执行、错误重试、消息历史**全部内置，人只需要写清楚 system_prompt 里的约束。这就是「工程化升级」的具体含义。

---

## 四、中间件 Middleware（V1.0 最大亮点）

> 定义：一种流程控制机制，在智能体执行过程中**拦截、修改或增强请求与响应**，无需改核心 Agent 或工具代码。每个步骤之前与之后都暴露钩子。

> [!note] 讲义定位
> 「中间件通常搭配 Agent 来用，本阶段简单了解即可」。钩子示意：`before_model` / `after_model` / 工具调用前后。

### 4.1 内置中间件

| 中间件 | 作用 |
|---|---|
| `PIIMiddleware` | 发送至模型前屏蔽 / 遮掩敏感信息 |
| `SummarizationMiddleware` | 对话历史过长时自动压缩 |
| `HumanInTheLoopMiddleware` | 工具执行前暂停，等待人工审批 / 编辑 / 拒绝 |
| `ModelCallLimitMiddleware` | 限制模型调用次数，防无限循环与成本失控 |
| `ToolCallLimitMiddleware` | 限制工具调用次数（全局或按工具） |

官方文档：https://docs.langchain.com/oss/python/langchain/middleware/built-in

### 4.2 PIIMiddleware 示例

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware
from langchain.tools import tool

@tool
def read_user_data(user_id: str) -> str:
    """读取用户数据的工具"""
    return f"用户 {user_id} 的数据：姓名张三，邮箱 zhangsan@example.com，手机号 13800138000"

agent = create_agent(
    model=client,
    tools=[read_user_data],
    middleware=[
        PIIMiddleware("email", strategy="redact",
                      apply_to_input=True, apply_to_output=True),
        PIIMiddleware("ip",  # 借用自定义正则匹配手机号
                      detector=r"(?:13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}",
                      strategy="redact",
                      apply_to_input=True, apply_to_output=True),
        PIIMiddleware("credit_card",  # 借用匹配身份证号
                      detector=r"\d{17}[\dXx]",
                      strategy="redact",
                      apply_to_input=True, apply_to_output=True),
    ],
    system_prompt="你是一个安全的数据处理助手，严格保护用户隐私",
)

result = agent.invoke({"messages": [{"role": "user", "content": "请读取用户001的数据"}]})
print(result["messages"][-1].content)
```

### 4.3 自定义中间件

两种写法：**基于装饰器**（单钩子，快速简便）、**基于类**（多钩子，功能更强）。

```python
import re
from typing import Any, Dict
from langchain.agents.middleware import AgentMiddleware

class FixedSensitiveDataMiddleware(AgentMiddleware):
    """讲义示例：before_model 里对邮箱 / 手机号脱敏"""

    def __init__(self, patterns: list = None):
        super().__init__()
        self.patterns = patterns or [
            (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]"),
            (r"(\+86)?1[3-9]\d{9}", "[PHONE]"),
        ]

    def _desensitize_text(self, text: str) -> str:
        for pattern, replacement in self.patterns:
            text = re.sub(pattern, replacement, text)
        return text

    def before_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        for message in state.get("messages", []):
            if hasattr(message, "content") and isinstance(message.content, str):
                message.content = self._desensitize_text(message.content)
        return state

    def after_model(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return state      # 后处理钩子，按需实现

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt="你是一个专业的助手",
    checkpointer=InMemorySaver(),
    middleware=[FixedSensitiveDataMiddleware()],
)
```

> [!warning] 讲义里的自定义中间件代码标注了"仅演示如何创建，本阶段无需掌握"
> 实际落库前要核对当前版本 `AgentMiddleware` 的钩子签名（讲义里专门有一段"修复的脱敏中间件 - 使用正确的参数签名"，说明 API 曾变过）。先用内置中间件，再考虑自定义。

---

## 五、踩坑清单

| 坑 | 处理 |
|---|---|
| 模型不选工具 / 选错工具 | docstring 写清楚工具用途；确认模型支持 function calling；用 `content_blocks` 看 `tool_call` 块 |
| `bind_tools` 后拿不到答案 | 那是正常的——只拿到了调用请求，需要应用执行或改用 `create_agent` |
| `agent.invoke()` 后取不到文本 | v1.0 返回 dict，取 `result["messages"][-1].content` |
| 多用户串会话 | 必须传 `config={"configurable": {"thread_id": ...}}`，并确保 checkpointer 已配置 |
| Agent 执行了 UPDATE/DELETE | 在 system_prompt 里明令禁止 + 用 `HumanInTheLoopMiddleware` 加人工审批 |
| Agent 死循环 / 费用失控 | `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` |
| 生成的 SQL 带 ```sql 围栏 | v0.3 手写链需要 `SQLCleaner`；v1.0 Agent 内置循环已处理 |

> [!note] 与 [[03-链与 LCEL]] 的关系
> LCEL 是「人定义好每一步」的确定性编排；Agent 是「模型决定走哪几步」的动态编排。V1.0 把主推方向从前者切到了后者，但 RAG 的检索、数据准备这些固定步骤仍大量使用 `Runnable` 组合。
