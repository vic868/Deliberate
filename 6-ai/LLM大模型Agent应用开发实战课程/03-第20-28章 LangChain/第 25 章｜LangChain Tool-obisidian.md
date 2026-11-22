---
title: "第 25 章｜LangChain Tool"
chapter: "25"
source: "第 25 章｜LangChain Tool.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langchain
  - tool
  - bind_tools
---

# 第 25 章｜LangChain Tool

> [!abstract] 本章重点
>
> - ==@tool 装饰器最快== — 一个函数加一行就变成带 Schema 的工具。
> - ==StructuredTool 适合更精细的控制== — 参数 Schema、描述、异步实现都能显式指定。
> - ==bind_tools 只是把工具告诉模型== — 真正决定调用循环的是 Agent。
> - ==工具描述写清楚，模型才选得对== — description 是给模型看的说明书。
> - ==Registry / Executor 依然值得保留== — 和企业项目的权限、日志、审计挂钩。

> [!note] 大白话
>
> - **bind_tools**：把工具清单挂在模型上，让模型知道有哪些工具可点。

> [!info] 导航与来源
> - 原始讲义：[[第 25 章｜LangChain Tool|打开原始讲义]]
> - [[第 24 章｜LangChain Structured Output|上一章｜第 24 章]]
> - [[第 26 章｜LangChain Agent|下一章｜第 26 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜先回顾第 18 章 Tool Calling]]
- [[#七、03｜LangChain Tool 是什么]]
- [[#八、04｜LangChain Tool 和 Function Calling 的关系]]
- [[#九、05｜bind_tools 和 Agent 的区别]]
- [[#十、06｜创建 langchain_tools 目录]]
- [[#十一、07｜定义工具参数 Schema]]
- [[#十二、08｜定义电商业务函数]]
- [[#十三、09｜方式一：@tool 装饰器]]
- [[#十四、10｜方式二：StructuredTool]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面我们已经完成了：

```text
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
```

第 24 章我们把第 17 章的结构化输出迁移到了 LangChain：

```text
StrOutputParser
JsonOutputParser
PydanticOutputParser
with_structured_output
LangChainStructuredOutputService
```

这一章继续迁移第 18 章：

```text
Function Calling 与 Tool Calling
```

第 18 章我们手写过：

```text
ToolDefinition
ToolRegistry
ToolExecutor
query_order
query_logistics
transfer_human
ToolCallingService
tools schema
tool_calls parser
tool result message
```

这一章要解决的问题是：

**如何用 LangChain 的 Tool 体系，把 Python 函数、Pydantic 参数、模型 tool_calls、工具执行、ToolMessage 回传模型，形成完整工具调用闭环。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. LangChain Tool 是什么
2. LangChain Tool 和第 18 章 ToolDefinition 的关系
3. @tool 装饰器怎么用
4. StructuredTool 怎么用
5. args_schema 怎么定义
6. 工具 name / description 为什么重要
7. model.bind_tools 是什么
8. bind_tools 和 Agent 的区别
9. AIMessage.tool_calls 长什么样
10. ToolMessage 的作用
11. tool_call_id 为什么必须保留
12. 如何手动执行 tool_calls
13. 如何把工具结果回传给模型
14. 如何实现 LangChain Tool Calling 闭环
15. query_order 如何改造成 LangChain Tool
16. query_logistics 如何改造成 LangChain Tool
17. transfer_human 如何改造成 LangChain Tool
18. 为什么还要保留自己的 ToolRegistry / ToolExecutor
19. 如何做工具权限、脱敏、人工确认
20. 如何把 LangChain Tool 接入第 19 章项目
21. 如何为第 26 章 LangChain Agent 打基础
```

---

## 三、本章版本口径
本课程 LangChain 阶段统一使用：

```text
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

本章主要用到：

```python
from langchain_core.tools import tool, StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
```

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langchain_tools/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── ecommerce_functions.py
│   │   ├── tools.py
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── service.py
│   │   ├── demo_tool_decorator.py
│   │   ├── demo_structured_tool.py
│   │   ├── demo_bind_tools.py
│   │   ├── demo_tool_calling_loop.py
│   │   └── demo_project_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langchain_tools.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc25_tool_decorator.py
│   ├── test_lc25_structured_tool.py
│   ├── test_lc25_bind_tools.py
│   ├── test_lc25_tool_executor.py
│   ├── test_lc25_tool_calling_loop.py
│   └── test_lc25_tool_service.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 25 章。

这一章我们讲 LangChain Tool。

第 18 章我们已经讲过 Tool Calling 的完整原理。

当时我们强调过一句话：

模型不会真的执行工具，模型只是生成工具调用请求，真正执行工具的是后端。

这个原则在 LangChain 里依然成立。

LangChain 可以帮我们更方便地定义工具、绑定工具、读取模型返回的 tool_calls。

但是：

```text
权限校验
参数校验
工具执行
结果脱敏
高风险确认
日志记录
```

这些仍然要后端负责。

==所以这一章我们不是简单学一个：==

```python
@tool
def query_order(...):
    ...
```

而是要把 LangChain Tool 放进我们前面已经搭好的企业项目架构里。

也就是：

```text
LangChain Tool
+
我们的 ToolRegistry
+
我们的 ToolExecutor
+
我们的 ToolCallingService
+
FastAPI 项目一
```

这样才是能落地的写法。

---

## 六、02｜先回顾第 18 章 Tool Calling

> [!success] 复盘要点
> 复盘时重点看这一节。

第 18 章完整链路是：

```text
用户问题
 ↓
后端发送 messages + tools 给模型
 ↓
模型判断需要调用 query_order
 ↓
模型返回 tool_calls
 ↓
后端解析 tool_calls
 ↓
后端校验 arguments
 ↓
后端执行 query_order
 ↓
工具返回真实结果
 ↓
后端把 tool result 追加到 messages
 ↓
再次调用模型
 ↓
模型生成最终回复
```

---

### 【重点内容】
==这一章的 LangChain Tool，本质上还是这条链路。==

只不过有几处会被 LangChain 简化。

第一个简化：

```text
工具定义
```

第 18 章我们手写 ToolDefinition。

这一章可以用：

```text
@tool
StructuredTool
```

第二个简化：

```text
tools schema 生成
```

第 18 章我们手写 `to_openai_tool()`。

这一章 LangChain 可以根据工具函数和 args_schema 生成工具描述。

第三个简化：

```text
tool_calls 读取
```

第 18 章我们自己解析 response raw json。

这一章可以从：

```python
AIMessage.tool_calls
```

直接读取。

但是工具真正执行和安全控制，仍然要我们自己负责。

---

## 七、03｜LangChain Tool 是什么
### 【实操】
```text
LangChain Tool
=
模型可以调用的外部能力

可以是：
Python 函数
异步函数
API 调用
数据库查询
RAG 检索
MCP 工具
业务服务
```

---

### 【重点内容】
LangChain Tool 可以理解成：

**包装给模型看的后端能力。**

比如：

```text
query_order
query_logistics
transfer_human
search_knowledge_base
query_database
send_email
```

这些都可以变成 Tool。

LangChain 的工具文档说明，工具可以由普通 Python 函数或协程定义，也可以通过 `@tool` 装饰器定制工具名、描述、参数 schema 等信息。

但注意，不是把所有函数都暴露给模型。

只有经过后端允许、描述清晰、参数可控的能力，才应该变成 Tool。

---

## 八、04｜LangChain Tool 和 Function Calling 的关系
### 【实操】
```text
Function Calling / Tool Calling：
模型 API 层面的能力

LangChain Tool：
框架层对工具的封装
```

---

### 【重点内容】
Function Calling / Tool Calling 是模型 API 层面的能力。

比如模型服务商支持：

```text
tools
tool_choice
tool_calls
tool_call_id
```

LangChain Tool 是框架层的封装。

它帮我们把 Python 函数、Pydantic 参数、工具描述包装成模型能理解的工具 schema。

然后通过：

```python
model.bind_tools([query_order])
```

绑定给模型。

`bind_tools()` 的参考文档显示，它接收 dict、Pydantic 类型、Python callable 或 BaseTool 序列，并返回一个绑定工具后的 Runnable ChatModel；`ChatOpenAI.bind_tools()` 还支持 `tool_choice` 参数，用来控制模型调用哪个工具或是否必须调用工具。

---

## 九、05｜bind_tools 和 Agent 的区别
### 【实操】
| 能力 | bind_tools | Agent |
| --- | --- | --- |
| 绑定工具给模型 | 支持 | 支持 |
| 模型返回 tool_calls | 支持 | 支持 |
| 自动执行工具 | 不自动 | 通常自动 |
| 多轮工具循环 | 手动写 | Agent 负责 |
| 状态管理 | 手动写 | Agent / LangGraph 负责 |
| 适合章节 | 本章 | 第 26 章 |


---

### 【重点内容】
这一点非常重要。

很多同学以为：

```text
model.bind_tools([tool])
```

以后，模型就会自动执行工具。

不是。

bind_tools 只是把工具 schema 绑定给模型。

它让模型知道：

```text
我有哪些工具可以选择
每个工具需要什么参数
```

模型返回的是：

```python
AIMessage.tool_calls
```

后端还要自己执行工具，再把结果作为 ToolMessage 回传给模型。

到了第 26 章 LangChain Agent，Agent 才会帮我们封装更多工具执行循环。

LangChain 的模型文档也说明，`ToolMessage` 会包含匹配原始工具调用的 `tool_call_id`，帮助模型把工具结果和请求对应起来。

---

## 十、06｜创建 langchain_tools 目录
执行：

```bash
mkdir -p app/langchain_tools

touch app/langchain_tools/__init__.py
touch app/langchain_tools/schemas.py
touch app/langchain_tools/ecommerce_functions.py
touch app/langchain_tools/tools.py
touch app/langchain_tools/registry.py
touch app/langchain_tools/executor.py
touch app/langchain_tools/service.py
touch app/langchain_tools/demo_tool_decorator.py
touch app/langchain_tools/demo_structured_tool.py
touch app/langchain_tools/demo_bind_tools.py
touch app/langchain_tools/demo_tool_calling_loop.py
touch app/langchain_tools/demo_project_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_tools

New-Item app\langchain_tools\__init__.py
New-Item app\langchain_tools\schemas.py
New-Item app\langchain_tools\ecommerce_functions.py
New-Item app\langchain_tools\tools.py
New-Item app\langchain_tools\registry.py
New-Item app\langchain_tools\executor.py
New-Item app\langchain_tools\service.py
New-Item app\langchain_tools\demo_tool_decorator.py
New-Item app\langchain_tools\demo_structured_tool.py
New-Item app\langchain_tools\demo_bind_tools.py
New-Item app\langchain_tools\demo_tool_calling_loop.py
New-Item app\langchain_tools\demo_project_adapter.py
```

---

## 十一、07｜定义工具参数 Schema
打开：

```text
app/langchain_tools/schemas.py
```

写入：

```python
from typing import Literal

from pydantic import BaseModel, Field


class QueryOrderArgs(BaseModel):
    order_id: str = Field(
        ...,
        min_length=1,
        description="订单号，例如 10001",
    )


class QueryOrderResult(BaseModel):
    order_id: str = Field(..., description="订单号")

    status: Literal[
        "pending",
        "paid",
        "shipped",
        "delivered",
        "cancelled",
        "refunding",
        "refunded",
        "not_found",
    ] = Field(..., description="订单状态")

    status_text: str = Field(..., description="订单状态中文说明")

    tracking_company: str | None = Field(
        default=None,
        description="物流公司",
    )

    tracking_no: str | None = Field(
        default=None,
        description="物流单号",
    )

    latest_event: str | None = Field(
        default=None,
        description="最新物流节点",
    )


class QueryLogisticsArgs(BaseModel):
    tracking_no: str = Field(
        ...,
        min_length=1,
        description="物流单号，例如 SF10001",
    )


class QueryLogisticsResult(BaseModel):
    tracking_no: str = Field(..., description="物流单号")

    tracking_company: str = Field(..., description="物流公司")

    latest_event: str = Field(..., description="最新物流节点")

    status: Literal[
        "in_transit",
        "delivered",
        "exception",
        "not_found",
    ] = Field(..., description="物流状态")


class TransferHumanArgs(BaseModel):
    reason: str = Field(
        ...,
        min_length=1,
        description="转人工原因",
    )


class TransferHumanResult(BaseModel):
    ticket_id: str = Field(..., description="人工客服工单 ID")

    status: Literal["created"] = Field(
        default="created",
        description="工单状态",
    )

    message: str = Field(..., description="提示信息")
```

---

### 【重点内容】
这里我们继续沿用第 18 章的参数和结果 Schema。

为什么要继续用 Pydantic？

因为 LangChain Tool 也需要清晰的参数 schema。

==模型调用工具时，参数必须是可校验的。==

比如 query_order 工具只需要：

```text
order_id
```

不要给模型一个万能的：

```python
data: dict
```

参数越明确，模型越容易调用正确。

---

## 十二、08｜定义电商业务函数
打开：

```text
app/langchain_tools/ecommerce_functions.py
```

写入：

```python
import uuid

from app.langchain_tools.schemas import (
    QueryLogisticsResult,
    QueryOrderResult,
    TransferHumanResult,
)


MOCK_ORDERS = {
    "10001": {
        "order_id": "10001",
        "status": "shipped",
        "status_text": "已发货",
        "tracking_company": "顺丰",
        "tracking_no": "SF10001",
        "latest_event": "包裹已到达成都高新区中转站。",
    },
    "10002": {
        "order_id": "10002",
        "status": "paid",
        "status_text": "已付款，待发货",
        "tracking_company": None,
        "tracking_no": None,
        "latest_event": None,
    },
    "10003": {
        "order_id": "10003",
        "status": "delivered",
        "status_text": "已签收",
        "tracking_company": "圆通",
        "tracking_no": "YT10003",
        "latest_event": "用户本人已签收。",
    },
}


MOCK_LOGISTICS = {
    "SF10001": {
        "tracking_no": "SF10001",
        "tracking_company": "顺丰",
        "latest_event": "包裹已到达成都高新区中转站。",
        "status": "in_transit",
    },
    "YT10003": {
        "tracking_no": "YT10003",
        "tracking_company": "圆通",
        "latest_event": "用户本人已签收。",
        "status": "delivered",
    },
}


async def query_order(order_id: str) -> QueryOrderResult:
    order = MOCK_ORDERS.get(order_id)

    if not order:
        return QueryOrderResult(
            order_id=order_id,
            status="not_found",
            status_text="未查询到订单",
            tracking_company=None,
            tracking_no=None,
            latest_event=None,
        )

    return QueryOrderResult(**order)


async def query_logistics(tracking_no: str) -> QueryLogisticsResult:
    logistics = MOCK_LOGISTICS.get(tracking_no)

    if not logistics:
        return QueryLogisticsResult(
            tracking_no=tracking_no,
            tracking_company="未知",
            latest_event="未查询到物流信息",
            status="not_found",
        )

    return QueryLogisticsResult(**logistics)


async def transfer_human(reason: str) -> TransferHumanResult:
    ticket_id = f"ticket_{uuid.uuid4().hex[:8]}"

    return TransferHumanResult(
        ticket_id=ticket_id,
        status="created",
        message=f"已为您创建人工客服工单，原因：{reason}",
    )
```

---

### 【重点内容】
这一层是纯业务函数。

它不依赖 LangChain。

这点很重要。

==我不建议大家把业务函数直接写死成 LangChain Tool。==

推荐拆成两层：

```text
业务函数：
query_order

LangChain Tool 包装：
query_order_tool
```

这样以后不用 LangChain 时，业务函数仍然能复用。

---

## 十三、09｜方式一：@tool 装饰器
打开：

```text
app/langchain_tools/tools.py
```

写入：

```python
import json

from langchain_core.tools import StructuredTool, tool

from app.langchain_tools.ecommerce_functions import (
    query_logistics,
    query_order,
    transfer_human,
)
from app.langchain_tools.schemas import (
    QueryLogisticsArgs,
    QueryOrderArgs,
    TransferHumanArgs,
)


@tool
async def query_order_simple(order_id: str) -> str:
    """根据订单号查询订单状态和物流信息。当用户询问订单状态、发货状态、物流状态时使用。"""
    result = await query_order(order_id=order_id)

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )


@tool
async def query_logistics_simple(tracking_no: str) -> str:
    """根据物流单号查询物流轨迹。当用户已经提供物流单号，并询问包裹运输状态时使用。"""
    result = await query_logistics(tracking_no=tracking_no)

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )


@tool
async def transfer_human_simple(reason: str) -> str:
    """当用户明确要求人工客服，或者问题超出 AI 能力范围时创建人工客服工单。"""
    result = await transfer_human(reason=reason)

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )
```

---

### 【重点内容】
这是最简单的 LangChain Tool 写法。

用：

```python
@tool
```

包装一个函数。

函数名就是工具名。

docstring 就是工具描述。

参数会根据函数签名生成 schema。

LangChain 工具文档也说明，`@tool` 装饰器可以从函数创建工具，并支持定制工具名称、描述和参数 schema。

但是简单写法有一个问题：

```text
参数 schema 不够可控
```

==所以企业项目里更推荐 StructuredTool + args_schema。==

---

## 十四、10｜方式二：StructuredTool
继续在：

```text
app/langchain_tools/tools.py
```

追加：

```python
query_order_tool = StructuredTool.from_function(
    coroutine=query_order,
    name="query_order",
    description=(
        "根据订单号查询订单状态和物流信息。"
        "当用户询问订单状态、发货状态、物流状态时使用。"
        "如果用户没有提供订单号，不要调用该工具，应先追问订单号。"
    ),
    args_schema=QueryOrderArgs,
)


query_logistics_tool = StructuredTool.from_function(
    coroutine=query_logistics,
    name="query_logistics",
    description=(
        "根据物流单号查询物流轨迹。"
        "当用户已经提供物流单号，并询问包裹运输状态时使用。"
    ),
    args_schema=QueryLogisticsArgs,
)


transfer_human_tool = StructuredTool.from_function(
    coroutine=transfer_human,
    name="transfer_human",
    description=(
        "当用户明确要求人工客服，或者问题超出 AI 能力范围时创建人工客服工单。"
        "该工具只创建工单，不处理退款、赔付、删除、支付等高风险操作。"
    ),
    args_schema=TransferHumanArgs,
)


ECOMMERCE_LANGCHAIN_TOOLS = [
    query_order_tool,
    query_logistics_tool,
    transfer_human_tool,
]
```

---

### 【重点内容】
StructuredTool 更适合企业项目。

因为它可以明确指定：

```text
name
description
args_schema
coroutine
```

也就是：

```python
StructuredTool.from_function(
    coroutine=query_order,
    name="query_order",
    description="...",
    args_schema=QueryOrderArgs,
)
```

这样工具的参数结构更稳定。

`StructuredTool` 参考文档也提供了结构化工具类，并包含工具调用 schema、运行、异步运行、stream events 等能力。

---

## 十五、11｜测试 @tool 装饰器
打开：

```text
app/langchain_tools/demo_tool_decorator.py
```

写入：

```python
import asyncio

from app.langchain_tools.tools import query_order_simple


async def main():
    print("tool name:")
    print(query_order_simple.name)

    print("=" * 80)
    print("tool description:")
    print(query_order_simple.description)

    print("=" * 80)
    print("tool args:")
    print(query_order_simple.args)

    print("=" * 80)
    print("tool result:")
    result = await query_order_simple.ainvoke({
        "order_id": "10001",
    })
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```text
scripts/test_lc25_tool_decorator.py
```

写入：

```python
import asyncio

from app.langchain_tools.demo_tool_decorator import main


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc25_tool_decorator.py
```

---

### 【重点内容】
这个脚本用于观察 Tool 对象。

重点看：

```text
name
description
args
```

==模型能不能正确调用工具，description 非常关键。==

工具描述不要写成：

```text
查询
```

要写清楚：

```text
什么时候用
需要什么参数
不能做什么
```

---

## 十六、12｜测试 StructuredTool
打开：

```text
app/langchain_tools/demo_structured_tool.py
```

写入：

```python
import asyncio

from app.langchain_tools.tools import (
    query_logistics_tool,
    query_order_tool,
    transfer_human_tool,
)


async def main():
    tools = [
        query_order_tool,
        query_logistics_tool,
        transfer_human_tool,
    ]

    for tool_item in tools:
        print("tool name:", tool_item.name)
        print("description:", tool_item.description)
        print("args:", tool_item.args)
        print("=" * 80)

    result = await query_order_tool.ainvoke({
        "order_id": "10001",
    })

    print("query_order result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```text
scripts/test_lc25_structured_tool.py
```

写入：

```python
import asyncio

from app.langchain_tools.demo_structured_tool import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 【重点内容】
StructuredTool 的输出结构更清楚。

它基于 Pydantic args_schema 生成参数说明。

如果模型要调用 query_order，就应该生成：

```json
{
  "order_id": "10001"
}
```

这比让模型猜参数更稳定。

---

## 十七、13｜创建 LangChainToolRegistry
打开：

```text
app/langchain_tools/registry.py
```

写入：

```python
from langchain_core.tools import BaseTool

from app.langchain_tools.tools import ECOMMERCE_LANGCHAIN_TOOLS


class LangChainToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"工具不存在：{name}")

        return self._tools[name]

    def list(self) -> list[BaseTool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def get_many(
        self,
        names: list[str] | None = None,
    ) -> list[BaseTool]:
        if not names:
            return self.list()

        return [
            self.get(name)
            for name in names
        ]


langchain_tool_registry = LangChainToolRegistry()


for item in ECOMMERCE_LANGCHAIN_TOOLS:
    langchain_tool_registry.register(item)
```

---

### 【重点内容】
虽然 LangChain 可以直接传 tools list。

但我们仍然保留 ToolRegistry。

为什么？

因为真实项目里，你需要按场景管理工具。

比如：

```text
电商客服场景：
query_order / query_logistics / transfer_human

RAG 场景：
search_knowledge_base

数据分析场景：
query_database / generate_chart

管理员场景：
update_config / disable_user
```

不是所有请求都暴露所有工具。

Registry 可以统一管理。

---

## 十八、14｜创建 LangChainToolExecutor
打开：

```text
app/langchain_tools/executor.py
```

写入：

```python
from typing import Any

from langchain_core.messages import ToolMessage

from app.core.logging import get_logger
from app.langchain_tools.registry import langchain_tool_registry


logger = get_logger(__name__)


class LangChainToolExecutionError(Exception):
    def __init__(
        self,
        message: str,
        tool_name: str,
        detail: str | None = None,
    ):
        self.message = message
        self.tool_name = tool_name
        self.detail = detail
        super().__init__(message)


class LangChainToolExecutor:
    async def execute_tool_call(
        self,
        tool_call: dict[str, Any],
    ) -> ToolMessage:
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args") or {}
        tool_call_id = tool_call.get("id")

        if not tool_name:
            raise LangChainToolExecutionError(
                message="tool_call 缺少工具名称",
                tool_name="unknown",
                detail=str(tool_call),
            )

        if not tool_call_id:
            raise LangChainToolExecutionError(
                message="tool_call 缺少 id",
                tool_name=tool_name,
                detail=str(tool_call),
            )

        try:
            tool = langchain_tool_registry.get(tool_name)

        except KeyError as exc:
            raise LangChainToolExecutionError(
                message="工具不存在",
                tool_name=tool_name,
                detail=str(exc),
            ) from exc

        logger.info(
            f"langchain_tool_execute_start tool_name={tool_name} "
            f"tool_call_id={tool_call_id}"
        )

        try:
            result = await tool.ainvoke(tool_args)

        except Exception as exc:
            logger.exception(
                f"langchain_tool_execute_failed tool_name={tool_name}"
            )

            result = {
                "success": False,
                "error": "工具执行失败",
                "detail": repr(exc),
            }

        else:
            result = {
                "success": True,
                "data": result,
            }

        logger.info(
            f"langchain_tool_execute_success tool_name={tool_name} "
            f"tool_call_id={tool_call_id}"
        )

        return ToolMessage(
            content=str(result),
            tool_call_id=tool_call_id,
            name=tool_name,
        )

    async def execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolMessage]:
        messages = []

        for tool_call in tool_calls:
            message = await self.execute_tool_call(tool_call)
            messages.append(message)

        return messages


langchain_tool_executor = LangChainToolExecutor()
```

---

### 【重点内容】
这里我们创建 LangChainToolExecutor。

它做的事和第 18 章 ToolExecutor 类似。

输入是：

```python
AIMessage.tool_calls
```

也就是模型返回的工具调用请求。

输出是：

```python
ToolMessage
```

也就是工具结果消息。

==注意 ToolMessage 里一定要带：==

```text
tool_call_id
```

这样模型才能知道工具结果对应哪一次调用。

---

## 十九、15｜测试 ToolExecutor
创建：

```text
scripts/test_lc25_tool_executor.py
```

写入：

```python
import asyncio

from app.langchain_tools.executor import langchain_tool_executor


async def main():
    tool_call = {
        "name": "query_order",
        "args": {
            "order_id": "10001",
        },
        "id": "call_query_order_001",
        "type": "tool_call",
    }

    tool_message = await langchain_tool_executor.execute_tool_call(
        tool_call
    )

    print("tool message type:", tool_message.type)
    print("tool message content:", tool_message.content)
    print("tool_call_id:", tool_message.tool_call_id)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc25_tool_executor.py
```

---

### 【重点内容】
这个脚本不调用模型。

它只测试：

```text
tool_call
 ↓
ToolExecutor
 ↓
ToolMessage
```

这个闭环是否正常。

==项目里排查问题时，一定要分层测试。==

不要一上来就调用模型。

先确认工具本身能不能执行。

---

## 二十、16｜bind_tools 示例
打开：

```text
app/langchain_tools/demo_bind_tools.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_tools.registry import langchain_tool_registry


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    tools = langchain_tool_registry.get_many([
        "query_order",
        "query_logistics",
        "transfer_human",
    ])

    model_with_tools = model.bind_tools(tools)

    response = model_with_tools.invoke([
        SystemMessage(
            content=(
                "你是一个跨境电商客服助手。\n"
                "当用户询问订单状态时，优先调用工具查询真实信息。\n"
                "不要编造订单状态。"
            )
        ),
        HumanMessage(
            content="帮我查一下订单 10001 到哪了？"
        ),
    ])

    print("content:")
    print(response.content)
    print("=" * 80)

    print("tool_calls:")
    print(response.tool_calls)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            print("tool name:", tool_call["name"])
            print("tool args:", tool_call["args"])
            print("tool id:", tool_call["id"])


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc25_bind_tools.py
```

写入：

```python
from app.langchain_tools.demo_bind_tools import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc25_bind_tools.py
```

---

### 【重点内容】
这个脚本演示 bind_tools。

核心代码是：

```python
model_with_tools = model.bind_tools(tools)
```

然后正常调用：

```python
response = model_with_tools.invoke(messages)
```

如果模型认为需要调用工具，结果会出现在：

```python
response.tool_calls
```

LangChain 的 ChatOpenAI 文档也展示了 `bind_tools` 后，返回的 AIMessage 里会包含 `tool_calls`，其中有工具名称、参数、调用 ID 和类型。

---

## 二十一、17｜AIMessage.tool_calls 长什么样
典型结构：

```python
[
    {
        "name": "query_order",
        "args": {
            "order_id": "10001",
        },
        "id": "call_xxx",
        "type": "tool_call",
    }
]
```

---

### 【重点内容】
这个结构对应第 18 章的 LLMToolCall。

==区别是，LangChain 已经帮你标准化成：==

```text
name
args
id
type
```

所以我们不用再从 raw response 里解析：

```text
function.name
function.arguments
```

直接读取：

```python
response.tool_calls
```

就可以。

LangChain 早期 tool calling 公告也说明，不同模型服务商的工具调用响应格式不完全一样，LangChain 会把工具调用结果标准化到 `AIMessage.tool_calls`。

---

## 二十二、18｜工具调用闭环示例
打开：

```text
app/langchain_tools/demo_tool_calling_loop.py
```

写入：

```python
import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_tools.executor import langchain_tool_executor
from app.langchain_tools.registry import langchain_tool_registry


async def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    tools = langchain_tool_registry.get_many([
        "query_order",
        "query_logistics",
        "transfer_human",
    ])

    model_with_tools = model.bind_tools(tools)

    messages = [
        SystemMessage(
            content=(
                "你是一个跨境电商客服助手。\n"
                "当用户询问订单、物流、发货状态时，必须优先调用工具查询真实信息。\n"
                "工具返回结果后，请用礼貌、简洁的中文回复用户。\n"
                "不要编造订单状态、物流公司或物流单号。"
            )
        ),
        HumanMessage(
            content="帮我查一下订单 10001 到哪了？"
        ),
    ]

    first_response = await model_with_tools.ainvoke(messages)

    print("first_response content:")
    print(first_response.content)
    print("=" * 80)

    print("tool_calls:")
    print(first_response.tool_calls)
    print("=" * 80)

    if not first_response.tool_calls:
        print("模型没有请求工具，直接回答：")
        print(first_response.content)
        return

    tool_messages = await langchain_tool_executor.execute_tool_calls(
        first_response.tool_calls
    )

    messages.append(first_response)
    messages.extend(tool_messages)

    final_response = await model.ainvoke(messages)

    print("final answer:")
    print(final_response.content)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```text
scripts/test_lc25_tool_calling_loop.py
```

写入：

```python
import asyncio

from app.langchain_tools.demo_tool_calling_loop import main


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc25_tool_calling_loop.py
```

---

### 【重点内容】
==这个脚本是本章最重要的示例。==

它完整实现了 Tool Calling 闭环。

第一步：

```text
model.bind_tools(tools)
```

第二步：

```text
模型返回 AIMessage.tool_calls
```

第三步：

```text
后端执行工具
```

第四步：

```text
生成 ToolMessage
```

第五步：

```text
把 first_response 和 ToolMessage 追加回 messages
```

第六步：

```text
再次调用模型生成最终回答
```

这就是 Tool Calling 的标准闭环。

---

## 二十三、19｜为什么要 append first_response
工具调用后，messages 顺序应该是：

```text
SystemMessage
HumanMessage
AIMessage(tool_calls=[...])
ToolMessage(tool_call_id=...)
AIMessage(final answer)
```

---

### 【重点内容】
很多同学会犯一个错误。

模型第一次返回 tool_calls 后，直接 append ToolMessage。

少了：

```text
AIMessage(tool_calls)
```

==正确流程必须把第一次模型返回的 AIMessage 也放进 messages。==

因为 ToolMessage 是回应这个 AIMessage 里的 tool_call。

如果缺了 AIMessage，模型可能不知道 ToolMessage 是从哪来的。

这个点和第 18 章讲的一样。

---

## 二十四、20｜创建 LangChainToolCallingService
打开：

```text
app/langchain_tools/service.py
```

写入：

```python
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_tools.executor import (
    LangChainToolExecutionError,
    langchain_tool_executor,
)
from app.langchain_tools.registry import langchain_tool_registry


logger = get_logger(__name__)


class LangChainToolCallingService:
    async def run_ecommerce_customer_service(
        self,
        user_question: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> dict:
        model = LangChainModelFactory.create(
            provider=provider,
            model=model_name,
            temperature=0,
        )

        tools = langchain_tool_registry.get_many([
            "query_order",
            "query_logistics",
            "transfer_human",
        ])

        model_with_tools = model.bind_tools(tools)

        messages = [
            SystemMessage(
                content=(
                    "你是一个跨境电商客服助手。\n"
                    "当用户询问订单、物流、发货状态时，优先调用工具查询真实信息。\n"
                    "不要编造订单状态、物流公司或物流单号。\n"
                    "如果用户没有提供订单号，应先追问订单号，不要调用 query_order。\n"
                    "工具返回结果后，请用礼貌、简洁的中文回复用户。"
                )
            ),
            HumanMessage(content=user_question),
        ]

        logger.info(
            f"langchain_tool_calling_start model={model_name}"
        )

        try:
            first_response = await model_with_tools.ainvoke(messages)

        except Exception as exc:
            logger.exception("langchain_tool_model_first_call_failed")

            raise AppException(
                message="LangChain 工具调用前模型请求失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "error": repr(exc),
                    "provider": provider,
                    "model": model_name,
                },
            ) from exc

        if not first_response.tool_calls:
            return {
                "answer": first_response.content,
                "tool_calls": [],
                "tool_messages": [],
                "metadata": {
                    "used_tools": False,
                },
            }

        try:
            tool_messages = await langchain_tool_executor.execute_tool_calls(
                first_response.tool_calls
            )

        except LangChainToolExecutionError as exc:
            logger.exception(
                f"langchain_tool_execute_error tool={exc.tool_name}"
            )

            raise AppException(
                message=exc.message,
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                data={
                    "tool_name": exc.tool_name,
                    "detail": exc.detail,
                },
            ) from exc

        messages.append(first_response)
        messages.extend(tool_messages)

        try:
            final_response = await model.ainvoke(messages)

        except Exception as exc:
            logger.exception("langchain_tool_model_final_call_failed")

            raise AppException(
                message="LangChain 工具调用后模型总结失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "error": repr(exc),
                    "provider": provider,
                    "model": model_name,
                },
            ) from exc

        logger.info(
            f"langchain_tool_calling_success model={model_name} "
            f"tool_count={len(first_response.tool_calls)}"
        )

        return {
            "answer": final_response.content,
            "tool_calls": first_response.tool_calls,
            "tool_messages": [
                {
                    "tool_call_id": message.tool_call_id,
                    "name": message.name,
                    "content": message.content,
                }
                for message in tool_messages
            ],
            "metadata": {
                "used_tools": True,
                "provider": provider,
                "model": model_name,
            },
        }


langchain_tool_calling_service = LangChainToolCallingService()
```

---

### 【重点内容】
这个 Service 对应第 18 章的 ToolCallingService。

但底层换成了 LangChain：

```text
model.bind_tools
AIMessage.tool_calls
ToolMessage
```

业务调用入口仍然是：

```python
run_ecommerce_customer_service(...)
```

返回：

```text
answer
tool_calls
tool_messages
metadata
```

==这就是第 19 章项目后面接入 LangChain Tool 的基础。==

---

## 二十五、21｜创建测试脚本
创建：

```text
scripts/test_lc25_tool_service.py
```

写入：

```python
import asyncio
import json

from app.langchain_tools.service import langchain_tool_calling_service


async def main():
    result = await langchain_tool_calling_service.run_ecommerce_customer_service(
        user_question="帮我查一下订单 10001 到哪了？",
        provider="deepseek",
        model_name="deepseek-chat",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc25_tool_service.py
```

---

## 二十六、22｜创建 LangChain Tool API
创建：

```text
app/api/v1/langchain_tools.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langchain_tools.registry import langchain_tool_registry
from app.langchain_tools.service import langchain_tool_calling_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class LangChainToolChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    provider: str = Field(default="deepseek", description="模型供应商")
    model: str = Field(default="deepseek-chat", description="模型名称")


@router.get(
    "/langchain/tools",
    response_model=ApiResponse[list[dict]],
)
async def list_langchain_tools(
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[dict]]:
    tools = langchain_tool_registry.list()

    return ApiResponse[list[dict]](
        data=[
            {
                "name": item.name,
                "description": item.description,
                "args": item.args,
            }
            for item in tools
        ]
    )


@router.post(
    "/langchain/tools/chat",
    response_model=ApiResponse[dict],
)
async def langchain_tool_chat(
    request: LangChainToolChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = await langchain_tool_calling_service.run_ecommerce_customer_service(
        user_question=request.question,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[dict](
        data=result
    )
```

---

## 二十七、23｜注册 Router
打开：

```text
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langchain_tools import router as langchain_tools_router
```

注册：

```python
api_router.include_router(
    langchain_tools_router,
    tags=["LangChain Tools"],
)
```

---

## 二十八、24｜测试工具列表接口
启动：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl "http://127.0.0.1:8000/api/v1/langchain/tools" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

预期：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "name": "query_order",
      "description": "根据订单号查询订单状态和物流信息...",
      "args": {
        "order_id": {
          "title": "Order Id",
          "description": "订单号，例如 10001",
          "type": "string"
        }
      }
    }
  ]
}
```

---

## 二十九、25｜测试工具调用接口
请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/tools/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "帮我查一下订单 10001 到哪了？",
    "provider": "deepseek",
    "model": "deepseek-chat"
  }'
```

预期：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "您好，您的订单 10001 已发货，物流公司是顺丰，物流单号是 SF10001，最新物流节点为：包裹已到达成都高新区中转站。",
    "tool_calls": [
      {
        "name": "query_order",
        "args": {
          "order_id": "10001"
        },
        "id": "call_xxx",
        "type": "tool_call"
      }
    ],
    "metadata": {
      "used_tools": true
    }
  }
}
```

---

## 三十、26｜项目一如何接入 LangChain Tool
第 19 章项目里可以这样接：

```text
ChatService
 ↓
判断 prompt_scenario=ecommerce_customer_service
 ↓
调用 LangChainToolCallingService
 ↓
返回 ChatResponse
```

示例：

```python
from app.langchain_tools.service import langchain_tool_calling_service


if request.prompt_scenario == "ecommerce_customer_service":
    tool_result = await langchain_tool_calling_service.run_ecommerce_customer_service(
        user_question=latest_user_message,
        provider="deepseek",
        model_name=model,
    )

    return ChatResponse(
        answer=tool_result["answer"],
        model=model,
        session_id=request.session_id,
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=TokenUsage(),
        sources=[],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "tool_calls": tool_result["tool_calls"],
            "tool_messages": tool_result["tool_messages"],
            "langchain_tool": True,
        },
    )
```

---

### 【重点内容】
这里我们只是替换 Tool Calling 分支。

原来的普通 Chat、Streaming、Redis、PostgreSQL 都不用动。

这就是逐步迁移。

第 19 章项目现在可以有两种工具调用实现：

```text
原生 ToolCallingService
LangChainToolCallingService
```

可以通过配置决定用哪个。

---

## 三十一、27｜为什么还要保留自己的 ToolExecutor
### 【重点内容】
用了 LangChain Tool，不代表可以删除自己的 ToolExecutor。

==原因是企业项目一定要做工具治理。==

比如：

```text
当前用户是否能查这个订单？
这个订单是不是属于当前用户？
工具结果是否需要脱敏？
这个工具是否需要人工确认？
工具调用是否要记录日志？
工具失败后是否要重试？
工具是否命中限流？
```

LangChain Tool 解决的是：

```text
工具描述
参数 schema
模型绑定
工具调用格式
```

业务治理还是我们自己负责。

所以推荐架构是：

```text
LangChain Tool
负责对接模型

我们的 ToolExecutor
负责权限、安全、日志、执行
```

---

## 三十二、28｜工具权限设计
可以给工具增加元数据：

```python
TOOL_SECURITY_CONFIG = {
    "query_order": {
        "risk_level": "low",
        "required_roles": ["user"],
        "require_confirm": False,
    },
    "transfer_human": {
        "risk_level": "low",
        "required_roles": ["user"],
        "require_confirm": False,
    },
    "refund_order": {
        "risk_level": "high",
        "required_roles": ["user"],
        "require_confirm": True,
    },
}
```

---

### 【重点内容】
后面企业级平台阶段，我们会把这些配置放到数据库。

本章先让大家有这个意识。

工具不是定义出来就能随便调。

每个工具都应该有：

```text
风险等级
权限要求
是否需要确认
是否可自动执行
是否记录审计日志
```

特别是写操作工具，更要谨慎。

---

## 三十三、29｜工具结果脱敏
示例：

```python
def mask_phone(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:]
```

==工具结果里不建议给模型完整看到：==

```text
手机号
地址
身份证号
邮箱
支付信息
内部备注
```

---

### 【重点内容】
模型只需要完成任务所需的最小信息。

比如用户问订单状态。

模型需要：

```text
订单状态
物流公司
物流单号
最新物流节点
```

不需要：

```text
用户手机号
完整地址
身份证号
支付流水号
```

所以 ToolExecutor 可以在返回 ToolMessage 之前做脱敏。

---

## 三十四、30｜高风险工具不能自动执行
高风险工具包括：

```text
退款
扣款
删除数据
发送短信
发送邮件
修改订单
提交审批
调用外部付费接口
```

这些工具必须：

```text
人工确认
权限校验
二次验证
审计日志
```

---

### 【重点内容】
这一章我们只做查询类工具。

不要一上来就让模型自动退款。

如果后面要做：

```text
refund_order
```

正确流程应该是：

```text
模型提出退款建议
后端检查权限
展示确认页面
用户确认
后端执行退款
记录审计日志
```

不是模型一句话就执行。

---

## 三十五、31｜工具 description 怎么写
不推荐：

```text
查询订单
```

推荐：

```text
根据订单号查询订单状态和物流信息。
当用户询问订单状态、发货状态、物流状态时使用。
如果用户没有提供订单号，不要调用该工具，应先追问订单号。
```

---

### 【重点内容】
Tool description 是给模型看的。

它决定模型什么时候用这个工具。

所以工具描述要写清楚：

```text
这个工具做什么
什么时候用
需要什么输入
什么时候不能用
```

==这就是工具版 Prompt Engineering。==

---

## 三十六、32｜工具参数怎么设计
不推荐：

```python
class QueryOrderArgs(BaseModel):
    data: dict
```

推荐：

```python
class QueryOrderArgs(BaseModel):
    order_id: str = Field(..., description="订单号，例如 10001")
```

---

### 【重点内容】
工具参数越明确，模型越容易生成正确参数。

不要给模型太自由的 dict。

尤其是工具参数要执行真实业务逻辑时，必须明确字段和类型。

Pydantic args_schema 就是工具调用安全的第一层。

---

## 三十七、33｜工具返回值怎么设计
工具返回给模型可以是字符串。

比如：

```python
return "订单 10001 已发货，物流公司顺丰。"
```

也可以是 JSON 字符串：

```python
return json.dumps(result.model_dump(), ensure_ascii=False)
```

---

### 【重点内容】
如果工具结果只是给模型读，字符串就可以。

如果你还要后端做日志、展示、分析，建议返回结构化结果。

本章用的是 Pydantic Result，再转 JSON 字符串。

这样更利于调试和扩展。

LangChain 工具文档也说明，当工具需要给模型提供普通文本读取时，可以返回字符串。

---

## 三十八、34｜bind_tools 的 tool_choice
一些模型支持控制工具选择：

```python
model_with_tools = model.bind_tools(
    tools,
    tool_choice="auto",
)
```

或者强制某个工具：

```python
model_with_tools = model.bind_tools(
    tools,
    tool_choice="query_order",
)
```

---

### 【重点内容】
tool_choice 用来控制模型是否调用工具。

但是不同模型和 provider 支持细节可能不同。

OpenAI-compatible 服务里，一般有：

```text
auto
none
required
指定工具
```

LangChain 的 ChatOpenAI `bind_tools` 参考文档也列出了 `tool_choice` 参数，含义是指定要求模型调用哪个工具。

真实项目里，最常用还是：

```text
auto
```

让模型自己判断是否需要工具。

==如果你确定某个场景必须调工具，再考虑强制。==

---

## 三十九、35｜多工具调用
模型可能一次返回多个 tool_calls：

```python
[
    {
        "name": "query_order",
        "args": {"order_id": "10001"},
        "id": "call_001",
        "type": "tool_call",
    },
    {
        "name": "query_logistics",
        "args": {"tracking_no": "SF10001"},
        "id": "call_002",
        "type": "tool_call",
    },
]
```

所以执行时要：

```python
for tool_call in response.tool_calls:
    ...
```

---

### 【重点内容】
不要只处理第一个 tool_call。

虽然很多时候只有一个工具调用，但模型可能一次请求多个工具。

所以 ToolExecutor 要支持列表。

我们前面的：

```python
execute_tool_calls
```

就是为这个准备的。

---

## 四十、36｜并行工具调用要不要做
### 【重点内容】
本章先串行执行工具。

也就是：

```text
一个 tool_call 执行完
再执行下一个
```

后面可以优化成并行：

```python
await asyncio.gather(...)
```

但并行执行要考虑：

```text
工具之间是否有依赖
是否有顺序要求
是否会抢同一资源
是否有事务一致性
是否有风控风险
```

==所以课程里先串行，安全清晰。==

---

## 四十一、37｜Tool 和 Structured Output 的关系
### 【重点内容】
Structured Output 和 Tool Calling 都会让模型输出结构化内容。

但用途不同。

Structured Output 输出的是：

```text
判断结果
```

比如：

```json
{
  "intent": "query_order",
  "need_order_id": true
}
```

Tool Calling 输出的是：

```text
可执行动作
```

比如：

```json
{
  "name": "query_order",
  "args": {
    "order_id": "10001"
  }
}
```

所以企业项目里经常先用 Structured Output 判断意图，再决定是否启用 tools。

---

## 四十二、38｜Tool 和 Agent 的关系
### 【重点内容】
Tool 是 Agent 的行动能力。

没有 Tool，Agent 只能回答。

有 Tool，Agent 才能：

```text
查订单
查知识库
查数据库
调用接口
创建工单
执行任务
```

但本章还不是 Agent。

本章是手动 Tool Calling Loop。

第 26 章会进入 LangChain Agent。

Agent 会把：

```text
模型判断
工具调用
工具执行
继续推理
最终回答
```

封装成更完整的循环。

---

## 四十三、39｜常见错误一：以为 bind_tools 会自动执行工具

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误理解：

```text
model.bind_tools([query_order]) 后，模型会自动查订单
```

正确理解：

```text
bind_tools 只让模型知道有哪些工具
模型返回 tool_calls
后端还要执行工具
```

---

## 四十四、40｜常见错误二：没有把 AIMessage 加回 messages
错误：

```python
messages.extend(tool_messages)
final_response = await model.ainvoke(messages)
```

正确：

```python
messages.append(first_response)
messages.extend(tool_messages)
final_response = await model.ainvoke(messages)
```

---

### 【重点内容】
ToolMessage 是对第一次 AIMessage tool_calls 的回应。

==所以 first_response 必须放回 messages。==

否则消息链路不完整。

---

## 四十五、41｜常见错误三：ToolMessage 缺 tool_call_id

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
ToolMessage(content="订单已发货")
```

正确：

```python
ToolMessage(
    content="订单已发货",
    tool_call_id=tool_call["id"],
)
```

---

## 四十六、42｜常见错误四：工具 description 太短
错误：

```text
查订单
```

正确：

```text
根据订单号查询订单状态和物流信息。
当用户询问订单状态、发货状态、物流状态时使用。
如果用户没有提供订单号，不要调用该工具。
```

---

## 四十七、43｜常见错误五：工具参数没有 schema
错误：

```python
@tool
def query_order(data: dict):
    ...
```

正确：

```python
class QueryOrderArgs(BaseModel):
    order_id: str = Field(..., description="订单号")
```

---

## 四十八、44｜常见错误六：高风险工具自动执行

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
模型调用 refund_order，后端直接退款
```

正确：

```text
进入人工确认
校验权限
校验订单
记录审计
用户二次确认后再执行
```

---

## 四十九、45｜常见错误七：把全部工具都暴露给所有场景
错误：

```text
每次 Chat 都绑定所有 tools
```

正确：

```text
按场景绑定工具
```

比如：

```text
电商客服：
query_order / query_logistics / transfer_human

RAG：
search_knowledge_base

数据分析：
query_database / generate_chart
```

---

## 五十、46｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| `@tool` | 第 18 章 ToolDefinition 简化版 |
| `StructuredTool` | 第 18 章 args_schema / result_schema |
| `args_schema` | Pydantic 工具参数校验 |
| `bind_tools` | 第 18 章 request.tools |
| `AIMessage.tool_calls` | 第 18 章 LLMToolCall |
| `ToolMessage` | 第 18 章 role=tool |
| `tool_call_id` | 工具调用结果关联 ID |
| `LangChainToolRegistry` | 第 18 章 ToolRegistry |
| `LangChainToolExecutor` | 第 18 章 ToolExecutor |
| `LangChainToolCallingService` | 第 18 章 ToolCallingService |
| 工具权限 | 第 09 章认证 / 第 18 章工具安全 |
| 工具日志 | 第 10 章日志与 trace_id |
| 工具结果脱敏 | 第 18 章工具安全 |
| Tool + Agent | 第 26 章 LangChain Agent |


---

## 五十一、47｜本章完整复习
这一章我们完成了：

```text
1. 理解 LangChain Tool 的定位
2. 回顾第 18 章 Tool Calling
3. 理解 Tool 和 Function Calling 的关系
4. 理解 bind_tools 和 Agent 的区别
5. 创建 langchain_tools 目录
6. 定义 QueryOrderArgs / QueryOrderResult
7. 定义 QueryLogisticsArgs / QueryLogisticsResult
8. 定义 TransferHumanArgs / TransferHumanResult
9. 创建电商业务函数
10. 使用 @tool 定义简单工具
11. 使用 StructuredTool 定义企业级工具
12. 测试 @tool 装饰器
13. 测试 StructuredTool
14. 创建 LangChainToolRegistry
15. 创建 LangChainToolExecutor
16. 把 tool_call 转成 ToolMessage
17. 测试 ToolExecutor
18. 使用 model.bind_tools
19. 读取 AIMessage.tool_calls
20. 实现手动工具调用闭环
21. 理解为什么要 append first_response
22. 创建 LangChainToolCallingService
23. 创建测试脚本
24. 创建 LangChain Tool API
25. 测试工具列表接口
26. 测试工具调用接口
27. 理解项目一如何接入 LangChain Tool
28. 理解为什么还要保留自己的 ToolExecutor
29. 理解工具权限、脱敏、高风险确认
30. 理解 Tool 和 Structured Output 的关系
31. 理解 Tool 和 Agent 的关系
32. 总结 LangChain Tool 常见错误
```

---

## 五十二、48｜课后任务一：跑通 @tool 示例
要求：

```text
1. 运行 scripts/test_lc25_tool_decorator.py
2. 打印 tool name
3. 打印 tool description
4. 打印 tool args
5. 调用 query_order_simple.ainvoke
```

---

## 五十三、49｜课后任务二：跑通 StructuredTool 示例
要求：

```json
1. 运行 scripts/test_lc25_structured_tool.py
2. 查看 query_order_tool.args
3. 确认 args_schema 生效
4. 调用 query_order_tool.ainvoke({"order_id": "10001"})
```

---

## 五十四、50｜课后任务三：跑通 bind_tools
要求：

```text
1. 运行 scripts/test_lc25_bind_tools.py
2. 输入“帮我查一下订单 10001 到哪了？”
3. 打印 response.tool_calls
4. 找到 tool name / args / id
```

---

## 五十五、51｜课后任务四：跑通工具调用闭环
要求：

```text
1. 运行 scripts/test_lc25_tool_calling_loop.py
2. 第一次调用模型拿到 tool_calls
3. 执行工具得到 ToolMessage
4. 把 first_response 和 ToolMessage 追加到 messages
5. 第二次调用模型得到最终回答
```

---

## 五十六、52｜课后任务五：新增 search_knowledge_base 工具
要求：

```typescript
1. 定义 SearchKnowledgeBaseArgs
2. 实现 search_knowledge_base(query: str)
3. 用 StructuredTool.from_function 包装
4. 注册到 LangChainToolRegistry
5. 测试用户问“公司年假有几天？”时模型是否调用该工具
```

---

## 五十七、53｜课后任务六：给工具增加安全配置
要求：

```text
1. 定义 TOOL_SECURITY_CONFIG
2. query_order risk_level=low
3. transfer_human risk_level=low
4. refund_order risk_level=high require_confirm=True
5. ToolExecutor 执行前检查 require_confirm
```

---

## 五十八、54｜课后任务七：项目一接入 LangChain Tool
要求：

```text
1. ChatService 判断 prompt_scenario=ecommerce_customer_service
2. 调用 LangChainToolCallingService
3. 返回 ChatResponse
4. metadata 中带上 tool_calls / tool_messages
5. 查询订单 10001 完整跑通
```

---

## 五十九、55｜课后任务八：画出 LangChain Tool 调用链路
画出：

```http
POST /api/v1/langchain/tools/chat
```

完整链路：

```text
HTTP Request
 ↓
LangChain Tool Router
 ↓
LangChainToolCallingService
 ↓
LangChainToolRegistry
 ↓
ChatModel.bind_tools(tools)
 ↓
model.ainvoke(messages)
 ↓
AIMessage.tool_calls
 ↓
LangChainToolExecutor
 ↓
StructuredTool.ainvoke(args)
 ↓
ToolMessage(tool_call_id)
 ↓
messages.append(AIMessage)
 ↓
messages.extend(ToolMessage)
 ↓
model.ainvoke(messages)
 ↓
final AIMessage.content
 ↓
ApiResponse
```

---

## 六十、56｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 25 章我们就讲完了。

这一章我们把第 18 章的 Function Calling 与 Tool Calling，迁移到了 LangChain Tool 体系里。

大家一定要记住：

```text
@tool 和 StructuredTool
负责定义工具

bind_tools
负责把工具绑定给模型

AIMessage.tool_calls
负责承载模型请求调用的工具

ToolMessage
负责把工具执行结果回传给模型

ToolExecutor
负责真正执行工具和做安全控制
```

尤其要记住一句话：

bind_tools 不等于自动执行工具。

模型只会返回 tool_calls。

后端必须执行工具、校验参数、检查权限、脱敏结果、记录日志，然后把 ToolMessage 回传给模型。

这一章结束后，我们已经完成了 LangChain 阶段的五个核心能力：

```text
Model
Message
Prompt
Structured Output
Tool
```

下一章就可以进入：

```text
LangChain Agent
```

也就是把模型、工具、循环执行组合起来。

---

---

> [!success] 一句话带走
> ==LangChain Tool 是把第 18 章手写工具标准化，不是换了个概念。==

> [!quote] 关于本文档
> 由原始讲义 `第 25 章｜LangChain Tool.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
