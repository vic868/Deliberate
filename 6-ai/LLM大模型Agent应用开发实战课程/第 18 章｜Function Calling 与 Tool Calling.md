---

# 一、本章定位
前面我们已经完成了：

```plain
第 13 章｜大模型 API 原理
第 14 章｜统一 LLM Provider 架构
第 15 章｜Prompt Engineering 工程化实战
第 16 章｜Streaming 流式输出
第 17 章｜Structured Output 结构化输出
```

到目前为止，我们的模型已经可以：

```plain
调用真实大模型
使用统一 LLM Provider
使用工程化 Prompt
流式输出
输出结构化 JSON
用 Pydantic 校验结果
```

但是模型还缺一个非常关键的能力：

**调用工具。**

比如用户问：

```plain
我的订单 10001 到哪了？
```

模型不能直接编：

```plain
您的订单已发货，物流单号是 SF123456。
```

因为它不知道真实订单状态。

正确流程应该是：

```plain
用户提问
 ↓
模型判断需要查订单
 ↓
模型生成工具调用参数
 ↓
后端执行 query_order 工具
 ↓
工具返回真实订单数据
 ↓
模型基于真实数据生成客服回复
```

这就是 Function Calling / Tool Calling。

本章就是让我们的 AI Chat 从：

```plain
只能回答
```

升级成：

```plain
能调用业务工具完成任务
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Function Calling 是什么
2. Tool Calling 是什么
3. Function Calling 和 Tool Calling 的区别
4. 为什么 Agent 离不开工具调用
5. 大模型工具调用完整链路
6. tools 参数怎么设计
7. tool_choice 是什么
8. auto / none / required 分别是什么意思
9. 如何定义工具 JSON Schema
10. 如何用 Pydantic 定义工具参数
11. 如何把 Pydantic Schema 转成 tool schema
12. 如何解析模型返回的 tool_calls
13. 如何执行本地 Python 工具函数
14. 如何校验工具参数
15. 如何把工具执行结果回传给模型
16. 如何生成最终自然语言回复
17. 如何设计 ToolRegistry
18. 如何设计 ToolExecutor
19. 如何实现电商订单查询 Tool
20. 如何实现物流查询 Tool
21. 如何处理工具不存在、参数错误、执行失败
22. 如何避免模型越权调用工具
23. Tool Calling 和 Structured Output 的关系
24. Tool Calling 和 Agent 的关系
```

---

# 三、本章最终项目结构
本章结束后，项目会新增和修改：

```plain
ai-agent-course/
├── app/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── executor.py
│   │   ├── schemas.py
│   │   ├── ecommerce.py
│   │   └── examples.py
│   │
│   ├── llm/
│   │   ├── schemas.py
│   │   ├── providers/
│   │   │   ├── openai_compatible.py
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── services/
│   │   ├── tool_calling_service.py
│   │   ├── chat_service.py
│   │   └── ...
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── tool_calling.py
│   │       ├── chat.py
│   │       └── api.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_tool_schema.py
│   ├── test_tool_registry.py
│   ├── test_tool_executor.py
│   ├── test_tool_calling_service.py
│   └── test_order_tool_calling_api.py
│
└── README.md
```

本章重点新增：

```plain
app/tools/
app/services/tool_calling_service.py
app/api/v1/tool_calling.py
```

---

# 四、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 18 章。

这一章我们讲 Function Calling 与 Tool Calling。

前面第 17 章，我们已经让模型可以输出结构化 JSON。

比如：

```json
{
  "intent": "query_order",
  "confidence": 0.92,
  "need_order_id": true
}
```

这个能力很有用。

但是它还只是“模型告诉我们它想干什么”。

现在我们要进一步：

```plain
让模型选择工具
让模型生成工具参数
让后端执行真实工具
让模型基于工具结果回答
```

比如用户说：

```plain
帮我查一下订单 10001 到哪了？
```

模型应该输出工具调用：

```json
{
  "tool_name": "query_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

后端执行：

```python
query_order(order_id="10001")
```

拿到结果：

```json
{
  "status": "shipped",
  "tracking_no": "SF10001"
}
```

然后再把结果交给模型，让模型生成最终客服回复。

这就是 Tool Calling。

从这一章开始，我们的 AI 应用就不只是聊天了。

它开始能连接业务系统。

---

# 五、02｜Function Calling 是什么
## 【实操】
```plain
Function Calling
=
模型根据用户问题
判断是否需要调用函数
并生成函数名和参数
```

---

## 【示例】
用户问题：

```plain
订单 10001 到哪了？
```

模型输出：

```json
{
  "name": "query_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

---

## 【重点内容】
Function Calling 可以理解成：

**模型不直接回答，而是先告诉后端：我需要调用哪个函数，以及参数是什么。**

注意，模型自己不会真的执行 Python 函数。

模型只是生成：

```plain
函数名
参数
```

真正执行函数的是我们的后端。

这点非常重要。

很多新手会误解为：

```plain
模型直接连接数据库
模型直接调用接口
模型直接执行代码
```

不是。

模型只是提出工具调用请求。

后端负责校验和执行。

---

# 六、03｜Tool Calling 是什么
## 【重点内容】
现在很多文档更常用：

```plain
Tool Calling
```

而不是 Function Calling。

为什么？

因为工具不一定只是函数。

它可能是：

```plain
Python 函数
HTTP API
数据库查询
搜索引擎
MCP Server
文件读取器
浏览器操作
代码解释器
向量检索器
```

所以 Tool Calling 比 Function Calling 更宽泛。

在 API 里常见结构是：

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "query_order",
        "description": "根据订单号查询订单状态",
        "parameters": {}
      }
    }
  ]
}
```

也就是说：

```plain
Function 是 Tool 的一种形式
```

本章先从 function 类型的 tool 开始。

这也是最常用、最容易理解的方式。

---

# 七、04｜Function Calling 和 Structured Output 的区别
## 【实操】
| 对比项 | Structured Output | Tool Calling |
| --- | --- | --- |
| 目标 | 让模型输出结构化结果 | 让模型选择并调用工具 |
| 输出内容 | JSON 结果 | tool_name + arguments |
| 是否执行外部逻辑 | 不执行 | 后端执行工具 |
| 适合场景 | 意图识别、分类、抽取、规划 | 查订单、查天气、查数据库、调用 API |
| 后续步骤 | 程序读取结果 | 执行工具，再把结果交回模型 |
| Agent 关系 | Agent 的理解能力 | Agent 的行动能力 |


---

## 【重点内容】
Structured Output 和 Tool Calling 很像。

它们都让模型输出结构化数据。

但区别很明显。

Structured Output 输出的是一个结果。

比如：

```json
{
  "intent": "query_order"
}
```

Tool Calling 输出的是一个动作请求。

比如：

```json
{
  "tool_name": "query_order",
  "arguments": {
    "order_id": "10001"
  }
}
```

然后后端要执行这个工具。

所以可以这样理解：

```plain
Structured Output
让模型“说清楚”

Tool Calling
让模型“会行动”
```

后面 Agent 就是建立在 Tool Calling 之上的。

---

# 八、05｜一次 Tool Calling 的完整链路
## 【实操】
```plain
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
 ↓
返回给用户
```

---

## 【重点内容】
Tool Calling 通常不是一次模型调用就结束。

它至少包含两次模型交互。

第一次：

```plain
让模型判断要不要调用工具
```

如果模型返回 tool_calls，后端执行工具。

然后第二次：

```plain
把工具结果交回模型，让模型生成最终自然语言回答
```

这就是完整闭环。

OpenAI Chat Completions 文档里 `finish_reason` 可能出现 `tool_calls`，表示模型调用了工具；DeepSeek 的 Tool Calls 示例也展示了把 `role="tool"`、`tool_call_id` 和工具结果追加回 messages 的流程。

---

# 九、06｜tools 参数长什么样
## 【典型结构】
```json
[
  {
    "type": "function",
    "function": {
      "name": "query_order",
      "description": "根据订单号查询订单状态和物流信息",
      "parameters": {
        "type": "object",
        "properties": {
          "order_id": {
            "type": "string",
            "description": "订单号"
          }
        },
        "required": ["order_id"],
        "additionalProperties": false
      }
    }
  }
]
```

---

## 【重点内容】
tools 是给模型看的工具说明书。

它告诉模型：

```plain
有哪些工具
每个工具叫什么
工具能做什么
需要什么参数
参数类型是什么
哪些参数必填
```

模型不会凭空知道你后端有哪些函数。

你必须把工具 schema 传给模型。

这样模型才知道：

```plain
查订单要调用 query_order
参数是 order_id
```

---

# 十、07｜tool_choice 是什么
## 【实操】
| tool_choice | 含义 |
| --- | --- |
| `none` | 不调用工具，只生成普通回答 |
| `auto` | 模型自己决定是否调用工具 |
| `required` | 必须调用一个或多个工具 |
| 指定工具 | 强制调用某个工具 |


---

## 【重点内容】
tool_choice 用来控制模型是否调用工具。

常见值有：

```plain
none
auto
required
```

`none` 表示不调用工具。

`auto` 表示模型自己判断。

`required` 表示必须调用工具。

OpenAI Chat Completions 文档也说明，`none` 表示模型不会调用工具，`auto` 表示模型可以选择回答或调用工具，`required` 表示模型必须调用一个或多个工具。

实际项目里，最常用的是：

```plain
auto
```

因为我们希望模型根据问题自己判断。

比如用户问：

```plain
你好
```

不需要调用工具。

用户问：

```plain
订单 10001 到哪了？
```

就应该调用工具。

---

# 十一、08｜工具调用安全原则
## 【重点内容】
Tool Calling 很强，但也很危险。

因为它会连接真实业务系统。

所以一定要记住：

**模型只能提出工具调用建议，后端必须负责校验和执行。**

后端必须检查：

```plain
工具是否存在
当前用户是否有权限调用
参数是否符合 Schema
资源是否属于当前用户
工具是否允许在当前场景使用
是否需要人工确认
工具是否超时
工具结果是否需要脱敏
```

千万不能让模型输出什么，后端就执行什么。

比如模型输出：

```json
{
  "tool_name": "refund_order",
  "arguments": {
    "order_id": "10001",
    "amount": 9999
  }
}
```

后端必须做权限和业务规则判断。

这一章先实现查询类工具。

不做退款、删除、支付这类高风险工具。

---

# 十二、09｜创建 tools 目录
## 【屏幕操作】
执行：

```bash
mkdir -p app/tools

touch app/tools/__init__.py
touch app/tools/base.py
touch app/tools/registry.py
touch app/tools/executor.py
touch app/tools/schemas.py
touch app/tools/ecommerce.py
touch app/tools/examples.py
```

Windows PowerShell：

```powershell
mkdir app\tools

New-Item app\tools\__init__.py
New-Item app\tools\base.py
New-Item app\tools\registry.py
New-Item app\tools\executor.py
New-Item app\tools\schemas.py
New-Item app\tools\ecommerce.py
New-Item app\tools\examples.py
```

---

## 【重点内容】
现在我们创建：

```plain
app/tools
```

这个目录专门管理工具。

不要把工具函数散落在 Service 里。

我们会分成：

```plain
base.py
= 工具基础模型

schemas.py
= 工具参数和结果 Schema

ecommerce.py
= 电商业务工具

registry.py
= 工具注册表

executor.py
= 工具执行器
```

这样后面新增 RAG Tool、MCP Tool、Agent Tool 都有位置放。

---

# 十三、10｜定义工具参数和结果 Schema
打开：

```plain
app/tools/schemas.py
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
        description="物流单号",
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
    status: Literal["created"] = Field(default="created")
    message: str = Field(..., description="提示信息")
```

---

## 【重点内容】
这里我们先定义三个工具的参数和结果。

第一个：

```plain
query_order
```

根据订单号查询订单状态。

第二个：

```plain
query_logistics
```

根据物流单号查询物流状态。

第三个：

```plain
transfer_human
```

创建转人工工单。

每个工具都有 Args 和 Result。

这是很重要的规范。

不要工具参数随便传 dict。

一定要用 Pydantic 校验。

---

# 十四、11｜定义 Tool 基础模型
打开：

```plain
app/tools/base.py
```

写入：

```python
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


ToolCallable = Callable[..., Awaitable[BaseModel] | BaseModel]


class ToolDefinition(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    args_schema: type[BaseModel] = Field(..., description="参数 Schema")
    result_schema: type[BaseModel] = Field(..., description="结果 Schema")
    func: ToolCallable = Field(..., description="工具函数")
    enabled: bool = Field(default=True, description="是否启用")
    require_confirm: bool = Field(default=False, description="是否需要人工确认")

    class Config:
        arbitrary_types_allowed = True

    def to_openai_tool(self) -> dict:
        schema = self.args_schema.model_json_schema()

        schema.setdefault("additionalProperties", False)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

    async def execute(self, arguments: dict[str, Any]) -> BaseModel:
        validated_args = self.args_schema.model_validate(arguments)

        if inspect.iscoroutinefunction(self.func):
            return await self.func(**validated_args.model_dump())

        result = self.func(**validated_args.model_dump())

        if inspect.isawaitable(result):
            return await result

        return result
```

---

## 【重点内容】
ToolDefinition 是我们自己定义的工具对象。

它包含：

```plain
name
description
args_schema
result_schema
func
enabled
require_confirm
```

最重要的是两个方法。

第一个：

```python
to_openai_tool()
```

把我们的工具定义转换成模型 API 需要的 tools 格式。

第二个：

```python
execute()
```

执行工具。

执行前先用：

```python
args_schema.model_validate(arguments)
```

校验模型生成的参数。

这一步非常关键。

模型生成的 arguments 不能直接相信。

---

# 十五、12｜实现电商工具函数
打开：

```plain
app/tools/ecommerce.py
```

写入：

```python
import uuid

from app.tools.schemas import (
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
        message=f"已为您创建人工客服工单，原因：{reason}",
    )
```

---

## 【重点内容】
这里我们先用 mock 数据模拟电商工具。

真实项目里，这些工具会调用：

```plain
订单系统
物流系统
售后系统
客服工单系统
```

本章重点不是接真实业务系统。

而是讲清楚 Tool Calling 的架构。

所以先用 mock。

后面大家可以把 mock 换成真实数据库查询或 HTTP API。

---

# 十六、13｜实现 ToolRegistry
打开：

```plain
app/tools/registry.py
```

写入：

```python
from app.tools.base import ToolDefinition
from app.tools.ecommerce import (
    query_logistics,
    query_order,
    transfer_human,
)
from app.tools.schemas import (
    QueryLogisticsArgs,
    QueryLogisticsResult,
    QueryOrderArgs,
    QueryOrderResult,
    TransferHumanArgs,
    TransferHumanResult,
)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        if name not in self._tools:
            raise KeyError(f"工具不存在：{name}")

        tool = self._tools[name]

        if not tool.enabled:
            raise KeyError(f"工具已禁用：{name}")

        return tool

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        return [
            tool.to_openai_tool()
            for tool in self._tools.values()
            if tool.enabled
        ]


tool_registry = ToolRegistry()

tool_registry.register(
    ToolDefinition(
        name="query_order",
        description="根据订单号查询订单状态和物流信息。当用户询问订单状态、发货状态、物流状态时使用。",
        args_schema=QueryOrderArgs,
        result_schema=QueryOrderResult,
        func=query_order,
    )
)

tool_registry.register(
    ToolDefinition(
        name="query_logistics",
        description="根据物流单号查询物流轨迹。当用户已经提供物流单号，并询问包裹运输状态时使用。",
        args_schema=QueryLogisticsArgs,
        result_schema=QueryLogisticsResult,
        func=query_logistics,
    )
)

tool_registry.register(
    ToolDefinition(
        name="transfer_human",
        description="当用户明确要求人工客服，或者问题超出 AI 能力范围时创建人工客服工单。",
        args_schema=TransferHumanArgs,
        result_schema=TransferHumanResult,
        func=transfer_human,
    )
)
```

---

## 【重点内容】
ToolRegistry 的作用是统一管理所有工具。

以后业务层不要直接 import 某个工具函数。

而是通过：

```python
tool_registry.get("query_order")
```

拿到工具。

并且可以通过：

```python
tool_registry.to_openai_tools()
```

把所有启用的工具转换成模型 API 的 tools 参数。

这就是工具注册表。

后面接 MCP 的时候，也可以把 MCP Tools 注册进来。

---

# 十七、14｜测试工具 Schema
创建：

```plain
scripts/test_tool_schema.py
```

写入：

```python
import json

from app.tools.registry import tool_registry


def main():
    tools = tool_registry.to_openai_tools()

    print(json.dumps(tools, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_tool_schema.py
```

你应该看到类似：

```json
[
  {
    "type": "function",
    "function": {
      "name": "query_order",
      "description": "根据订单号查询订单状态和物流信息...",
      "parameters": {
        "properties": {
          "order_id": {
            "description": "订单号，例如 10001",
            "minLength": 1,
            "title": "Order Id",
            "type": "string"
          }
        },
        "required": ["order_id"],
        "title": "QueryOrderArgs",
        "type": "object",
        "additionalProperties": false
      }
    }
  }
]
```

---

## 【重点内容】
这个脚本先测试 tools 参数生成。

大家一定要看生成结果。

因为模型能不能正确调用工具，很大程度取决于：

```plain
工具名称是否清晰
工具描述是否准确
参数 Schema 是否明确
```

Tool Schema 写得越清楚，模型越容易正确调用。

---

# 十八、15｜实现 ToolExecutor
打开：

```plain
app/tools/executor.py
```

写入：

```python
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.tools.registry import tool_registry


logger = get_logger(__name__)


class ToolExecutionError(Exception):
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


class ToolExecutor:
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> BaseModel:
        logger.info(
            f"tool_execute_start tool_name={tool_name}"
        )

        try:
            tool = tool_registry.get(tool_name)

        except KeyError as exc:
            raise ToolExecutionError(
                message="工具不存在或未启用",
                tool_name=tool_name,
                detail=str(exc),
            ) from exc

        if tool.require_confirm:
            raise ToolExecutionError(
                message="该工具需要人工确认，不能自动执行",
                tool_name=tool_name,
            )

        try:
            result = await tool.execute(arguments)

        except ValidationError as exc:
            raise ToolExecutionError(
                message="工具参数校验失败",
                tool_name=tool_name,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            logger.exception(
                f"tool_execute_failed tool_name={tool_name}"
            )
            raise ToolExecutionError(
                message="工具执行失败",
                tool_name=tool_name,
                detail=repr(exc),
            ) from exc

        logger.info(
            f"tool_execute_success tool_name={tool_name}"
        )

        return result


tool_executor = ToolExecutor()
```

---

## 【重点内容】
ToolExecutor 是工具执行入口。

它会做几件事：

```plain
1. 根据 tool_name 查工具
2. 判断工具是否启用
3. 判断是否需要人工确认
4. 用 Pydantic 校验参数
5. 执行工具函数
6. 返回工具结果
7. 统一处理工具异常
```

以后 Agent 调工具，也会走这个执行器。

不要让模型直接执行函数。

必须经过 ToolExecutor。

---

# 十九、16｜测试 ToolExecutor
创建：

```plain
scripts/test_tool_executor.py
```

写入：

```python
import asyncio


from app.tools.executor import tool_executor


async def main():
    result = await tool_executor.execute(
        tool_name="query_order",
        arguments={
            "order_id": "10001",
        },
    )

    print(result.model_dump())

    result = await tool_executor.execute(
        tool_name="query_logistics",
        arguments={
            "tracking_no": "SF10001",
        },
    )

    print(result.model_dump())


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_tool_executor.py
```

预期输出：

```json
{
  "order_id": "10001",
  "status": "shipped",
  "status_text": "已发货",
  "tracking_company": "顺丰",
  "tracking_no": "SF10001",
  "latest_event": "包裹已到达成都高新区中转站。"
}
```

---

## 【重点内容】
这个脚本不调用模型。

只测试工具执行器。

这一步很重要。

Tool Calling 出问题时，要先判断：

```plain
是模型没生成正确 tool_call
还是工具本身执行失败
```

所以工具本身一定要先单独测试。

---

# 二十、17｜升级 LLM Schema 支持 Tool Calling
打开：

```plain
app/llm/schemas.py
```

在原有代码基础上增加下面几个结构。

```python
from typing import Any, Literal
```

新增：

```python
class LLMToolCall(BaseModel):
    id: str = Field(..., description="Tool Call ID")
    name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="工具参数",
    )
    raw_arguments: str = Field(
        default="{}",
        description="模型返回的原始参数字符串",
    )


class LLMToolResultMessage(BaseModel):
    tool_call_id: str = Field(..., description="Tool Call ID")
    name: str = Field(..., description="工具名称")
    content: str = Field(..., description="工具执行结果 JSON 字符串")
```

修改 `LLMMessage`：

```python
class LLMMessage(BaseModel):
    role: LLMRole = Field(..., description="消息角色")
    content: str = Field(default="", description="消息内容")
    tool_call_id: str | None = Field(
        default=None,
        description="tool message 对应的 tool_call_id",
    )
```

修改 `LLMRequest`，增加：

```python
tools: list[dict] | None = Field(
    default=None,
    description="可用工具列表",
)
tool_choice: str | dict | None = Field(
    default=None,
    description="工具调用策略：none / auto / required / 指定工具",
)
```

修改 `LLMResponse`，增加：

```python
tool_calls: list[LLMToolCall] = Field(
    default_factory=list,
    description="模型请求调用的工具",
)
finish_reason: str | None = Field(
    default=None,
    description="结束原因",
)
```

最终关键结构类似：

```python
class LLMRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: list[LLMMessage] = Field(..., min_length=1, description="消息列表")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    max_tokens: int | None = Field(default=None, ge=1, description="最大输出 token")
    stream: bool = Field(default=False, description="是否流式输出")
    response_format: dict | None = Field(default=None, description="模型结构化输出格式约束")
    tools: list[dict] | None = Field(default=None, description="可用工具列表")
    tool_choice: str | dict | None = Field(default=None, description="工具调用策略")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展信息")


class LLMResponse(BaseModel):
    provider: LLMProviderName = Field(..., description="模型供应商")
    model: str = Field(..., description="模型名称")
    content: str = Field(default="", description="模型输出内容")
    usage: LLMUsage = Field(default_factory=LLMUsage, description="Token 用量")
    tool_calls: list[LLMToolCall] = Field(default_factory=list, description="模型请求调用的工具")
    finish_reason: str | None = Field(default=None, description="结束原因")
    raw_response: dict[str, Any] = Field(default_factory=dict, description="原始响应")
```

---

## 【重点内容】
现在 LLMRequest 支持：

```plain
tools
tool_choice
```

LLMResponse 支持：

```plain
tool_calls
finish_reason
```

这样 Provider 才能把工具调用信息传回业务层。

以前模型只返回 content。

现在模型可能不返回 content，而是返回 tool_calls。

所以 content 要允许为空。

这就是 Tool Calling 和普通 Chat 最大的不同。

---

# 二十一、18｜升级 OpenAICompatibleProvider 支持 tools
打开：

```plain
app/llm/providers/openai_compatible.py
```

修改 `_build_payload`，增加：

```python
if request.tools:
    payload["tools"] = request.tools

if request.tool_choice is not None:
    payload["tool_choice"] = request.tool_choice
```

完整片段：

```python
def _build_payload(
    self,
    request: LLMRequest,
    stream: bool,
) -> dict:
    payload = {
        "model": request.model or self.default_model,
        "messages": [
            self._build_message_payload(message)
            for message in request.messages
        ],
        "temperature": request.temperature,
        "stream": stream,
    }

    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens

    if request.response_format is not None:
        payload["response_format"] = request.response_format

    if request.tools:
        payload["tools"] = request.tools

    if request.tool_choice is not None:
        payload["tool_choice"] = request.tool_choice

    return payload


def _build_message_payload(self, message: LLMMessage) -> dict:
    payload = {
        "role": message.role.value,
        "content": message.content,
    }

    if message.role == LLMRole.TOOL and message.tool_call_id:
        payload["tool_call_id"] = message.tool_call_id

    return payload
```

---

## 【重点内容】
这里我们把 tools 和 tool_choice 传给模型。

另外新增了：

```python
_build_message_payload()
```

为什么？

因为普通 message 只有：

```plain
role
content
```

但是 tool 结果 message 还需要：

```plain
tool_call_id
```

DeepSeek Tool Calls 示例里也展示了把工具结果作为 `role="tool"` 的消息追加，并带上 `tool_call_id`。

所以 message payload 要单独处理。

---

# 二十二、19｜升级 Provider 解析 tool_calls
继续修改：

```plain
app/llm/providers/openai_compatible.py
```

增加导入：

```python
from app.llm.schemas import LLMMessage, LLMRole, LLMToolCall
```

修改 `_parse_chat_response`：

```python
def _parse_chat_response(self, data: dict) -> LLMResponse:
    choice = data["choices"][0]
    message = choice["message"]

    usage_data = data.get("usage") or {}

    usage = LLMUsage(
        prompt_tokens=usage_data.get("prompt_tokens", 0),
        completion_tokens=usage_data.get("completion_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0),
    )

    tool_calls = self._parse_tool_calls(message)

    return LLMResponse(
        provider=self.provider_name,
        model=data.get("model", self.default_model),
        content=message.get("content") or "",
        usage=usage,
        tool_calls=tool_calls,
        finish_reason=choice.get("finish_reason"),
        raw_response=data,
    )


def _parse_tool_calls(self, message: dict) -> list[LLMToolCall]:
    raw_tool_calls = message.get("tool_calls") or []
    parsed_tool_calls: list[LLMToolCall] = []

    for item in raw_tool_calls:
        function = item.get("function") or {}
        raw_arguments = function.get("arguments") or "{}"

        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}

        parsed_tool_calls.append(
            LLMToolCall(
                id=item.get("id", ""),
                name=function.get("name", ""),
                arguments=arguments,
                raw_arguments=raw_arguments,
            )
        )

    return parsed_tool_calls
```

---

## 【重点内容】
这里我们解析模型返回的 tool_calls。

典型结构是：

```json
{
  "tool_calls": [
    {
      "id": "call_xxx",
      "type": "function",
      "function": {
        "name": "query_order",
        "arguments": "{\"order_id\":\"10001\"}"
      }
    }
  ]
}
```

注意 arguments 很多时候是 JSON 字符串。

所以要：

```python
json.loads(raw_arguments)
```

解析成 dict。

如果解析失败，也不要直接崩，要记录 raw_arguments，后面可以抛参数错误。

---

# 二十三、20｜实现 ToolCallingService
创建：

```plain
app/services/tool_calling_service.py
```

写入完整代码：

```python
import json

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider
from app.llm.errors import LLMProviderError
from app.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMRole,
)
from app.tools.executor import ToolExecutionError, tool_executor
from app.tools.registry import tool_registry


logger = get_logger(__name__)


class ToolCallingService:
    async def run_with_tools(
        self,
        user_question: str,
        model: str,
        llm_provider: BaseLLMProvider,
    ) -> dict:
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=(
                    "你是一个跨境电商客服助手。\n"
                    "当用户询问订单、物流、发货状态时，优先调用工具查询真实信息。\n"
                    "不要编造订单状态、物流单号或退款进度。\n"
                    "工具返回结果后，请用礼貌、简洁的中文回复用户。"
                ),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=user_question,
            ),
        ]

        first_request = LLMRequest(
            model=model,
            messages=messages,
            temperature=0.1,
            stream=False,
            tools=tool_registry.to_openai_tools(),
            tool_choice="auto",
        )

        try:
            first_response = await llm_provider.chat(first_request)

        except LLMProviderError as exc:
            raise AppException(
                message="工具调用前模型请求失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "provider": exc.provider,
                    "status_code": exc.status_code,
                },
            ) from exc

        if not first_response.tool_calls:
            return {
                "answer": first_response.content,
                "tool_calls": [],
                "tool_results": [],
                "usage": first_response.usage.model_dump(),
            }

        tool_results = []

        for tool_call in first_response.tool_calls:
            try:
                result = await tool_executor.execute(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                )

            except ToolExecutionError as exc:
                logger.warning(
                    f"tool_call_failed tool_name={exc.tool_name} detail={exc.detail}"
                )

                result_content = {
                    "success": False,
                    "error": exc.message,
                    "detail": exc.detail,
                }

            else:
                result_content = {
                    "success": True,
                    "data": result.model_dump(),
                }

            tool_results.append(
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result_content,
                }
            )

            messages.append(
                LLMMessage(
                    role=LLMRole.ASSISTANT,
                    content="",
                )
            )

            messages.append(
                LLMMessage(
                    role=LLMRole.TOOL,
                    tool_call_id=tool_call.id,
                    content=json.dumps(
                        result_content,
                        ensure_ascii=False,
                    ),
                )
            )

        second_request = LLMRequest(
            model=model,
            messages=messages,
            temperature=0.3,
            stream=False,
        )

        try:
            final_response: LLMResponse = await llm_provider.chat(second_request)

        except LLMProviderError as exc:
            raise AppException(
                message="工具调用后模型总结失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "provider": exc.provider,
                    "status_code": exc.status_code,
                },
            ) from exc

        return {
            "answer": final_response.content,
            "tool_calls": [
                tool_call.model_dump()
                for tool_call in first_response.tool_calls
            ],
            "tool_results": tool_results,
            "usage": {
                "first": first_response.usage.model_dump(),
                "final": final_response.usage.model_dump(),
            },
        }


tool_calling_service = ToolCallingService()
```

---

## 【重点内容】
这个 Service 是本章核心。

它完整实现了 Tool Calling 两阶段流程。

第一阶段：

```plain
把 messages + tools 发给模型
让模型判断是否需要调用工具
```

如果模型没有返回 tool_calls，说明它选择直接回答。

如果返回 tool_calls，后端执行工具。

第二阶段：

```plain
把工具结果追加回 messages
再次调用模型
生成最终自然语言回复
```

这里有一个地方要注意。

我们追加了：

```python
LLMMessage(role=LLMRole.TOOL, tool_call_id=tool_call.id, content=...)
```

这是告诉模型：

这个工具调用的执行结果是这些内容。

---

# 二十四、21｜关于 assistant tool_calls message 的说明
## 【重点内容】
严格来说，OpenAI-compatible 的完整 messages 流程里，第一次模型返回的 assistant message 里会包含 tool_calls。

然后我们应该把这个 assistant message 也追加回 messages。

本章为了降低代码复杂度，先用简化版：

```plain
assistant 空消息
+
tool 结果消息
```

在一些兼容 API 上可以跑通。

更严谨的工程版本应该在 LLMMessage 里支持：

```plain
tool_calls
```

然后把第一次 assistant tool_calls 原样放回 messages。

课后任务会让大家补全这个严谨版本。

---

# 二十五、22｜测试 ToolCallingService
创建：

```plain
scripts/test_tool_calling_service.py
```

写入：

```python
import asyncio
import json

from app.llm.factory import LLMProviderFactory
from app.services.tool_calling_service import tool_calling_service


async def main():
    provider = LLMProviderFactory.create("deepseek")

    result = await tool_calling_service.run_with_tools(
        user_question="帮我查一下订单 10001 到哪了？",
        model="deepseek-chat",
        llm_provider=provider,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_tool_calling_service.py
```

预期结果类似：

```json
{
  "answer": "您好，您的订单 10001 已发货，物流公司是顺丰，物流单号是 SF10001，最新物流节点为：包裹已到达成都高新区中转站。",
  "tool_calls": [
    {
      "id": "call_xxx",
      "name": "query_order",
      "arguments": {
        "order_id": "10001"
      },
      "raw_arguments": "{\"order_id\":\"10001\"}"
    }
  ],
  "tool_results": [
    {
      "tool_call_id": "call_xxx",
      "tool_name": "query_order",
      "arguments": {
        "order_id": "10001"
      },
      "result": {
        "success": true,
        "data": {
          "order_id": "10001",
          "status": "shipped",
          "status_text": "已发货",
          "tracking_company": "顺丰",
          "tracking_no": "SF10001",
          "latest_event": "包裹已到达成都高新区中转站。"
        }
      }
    }
  ]
}
```

---

## 【重点内容】
这个脚本是真正的 Tool Calling 测试。

它会让模型根据用户问题判断要调用哪个工具。

如果模型正确，它应该调用：

```plain
query_order
```

参数是：

```json
{
  "order_id": "10001"
}
```

然后后端执行工具，最后模型生成客服回复。

这就是 AI Agent 的雏形。

---

# 二十六、23｜创建 Tool Calling API
创建：

```plain
app/api/v1/tool_calling.py
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
from app.services.tool_calling_service import tool_calling_service
from app.tools.registry import tool_registry


router = APIRouter()


class ToolCallingRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")


@router.get("/tools", response_model=ApiResponse[list[dict]])
async def list_tools(
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[dict]]:
    tools = tool_registry.list()

    return ApiResponse[list[dict]](
        data=[
            {
                "name": tool.name,
                "description": tool.description,
                "enabled": tool.enabled,
                "require_confirm": tool.require_confirm,
                "args_schema": tool.args_schema.model_json_schema(),
                "result_schema": tool.result_schema.model_json_schema(),
            }
            for tool in tools
        ]
    )


@router.post("/tools/run", response_model=ApiResponse[dict])
async def run_tool_calling(
    request: ToolCallingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    llm_provider: BaseLLMProvider = Depends(get_llm_provider),
) -> ApiResponse[dict]:
    result = await tool_calling_service.run_with_tools(
        user_question=request.question,
        model=request.model,
        llm_provider=llm_provider,
    )

    return ApiResponse[dict](
        data=result
    )
```

---

## 【重点内容】
现在我们新增两个接口。

第一个：

```plain
GET /tools
```

查看当前系统有哪些工具。

第二个：

```plain
POST /tools/run
```

让模型根据用户问题自动决定是否调用工具。

这两个接口先用于演示和调试。

后面我们会把 Tool Calling 接入 ChatService 和 AgentService。

---

# 二十七、24｜注册 Tool Calling Router
打开：

```plain
app/api/v1/api.py
```

增加导入：

```python
from app.api.v1.tool_calling import router as tool_calling_router
```

增加注册：

```python
api_router.include_router(
    tool_calling_router,
    tags=["Tool Calling"],
)
```

---

# 二十八、25｜测试工具列表接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl "http://127.0.0.1:8000/api/v1/tools" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "name": "query_order",
      "description": "根据订单号查询订单状态和物流信息...",
      "enabled": true,
      "require_confirm": false
    }
  ]
}
```

---

# 二十九、26｜测试 Tool Calling 接口
请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tools/run" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "帮我查一下订单 10001 到哪了？",
    "model": "deepseek-chat"
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "您好，您的订单 10001 已发货，物流公司是顺丰，物流单号是 SF10001，最新物流节点为：包裹已到达成都高新区中转站。",
    "tool_calls": [
      {
        "name": "query_order",
        "arguments": {
          "order_id": "10001"
        }
      }
    ],
    "tool_results": [
      {
        "tool_name": "query_order",
        "result": {
          "success": true,
          "data": {
            "status_text": "已发货",
            "tracking_company": "顺丰"
          }
        }
      }
    ]
  },
  "trace_id": null
}
```

---

## 【重点内容】
现在这个接口已经具备 Tool Calling 能力。

用户问订单状态。

模型不再瞎答。

而是先调用 query_order 工具。

然后基于工具返回的真实结果回复。

这就是 AI 客服 Agent 的核心能力。

---

# 三十、27｜把 Tool Calling 接入 ChatService 的思路
## 【重点内容】
现在我们先做了独立接口：

```plain
/tools/run
```

用于理解和调试。

下一步可以接入：

```plain
/chat
```

流程是：

```plain
用户请求 /chat
 ↓
先做意图识别
 ↓
如果是订单 / 物流类问题
 ↓
走 tool_calling_service.run_with_tools
 ↓
否则走普通 llm_provider.chat
```

也可以更简单：

```plain
所有 Chat 都带 tools
让模型自己决定要不要调用
```

但真实项目里，我更建议分场景控制。

比如普通聊天不一定要带工具。

电商客服场景才带订单工具。

这样更安全、成本也更低。

---

# 三十一、28｜ChatService 集成示例
在：

```plain
app/services/chat_service.py
```

可以加一个分支：

```python
from app.services.tool_calling_service import tool_calling_service


if request.prompt_scenario == "ecommerce_customer_service":
    tool_result = await tool_calling_service.run_with_tools(
        user_question=latest_user_message,
        model=model,
        llm_provider=llm_provider,
    )

    answer = tool_result["answer"]

    return ChatResponse(
        answer=answer,
        model=model,
        session_id=request.session_id or f"s_{uuid.uuid4().hex[:8]}",
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=TokenUsage(),
        sources=[],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
    )
```

---

## 【重点内容】
这只是一个接入示例。

实际项目里要更细。

比如：

```plain
先判断意图
再决定是否启用 tools
再决定哪些工具对当前用户可见
再执行 Tool Calling
```

这一章先让大家理解主流程。

后面 LangChain / LangGraph 阶段，我们会把 Tool Calling 进一步升级成 Agent 执行图。

---

# 三十二、29｜工具权限设计
## 【重点内容】
真实项目里，工具不是所有用户都能调用。

比如：

```plain
query_order
普通用户只能查自己的订单

refund_order
可能需要人工确认

delete_document
只有管理员能执行

send_email
需要用户授权
```

所以 ToolDefinition 后面可以增加：

```plain
required_roles
allowed_scenarios
risk_level
require_confirm
```

比如：

```python
required_roles: list[str] = ["admin"]
risk_level: Literal["low", "medium", "high"] = "low"
```

本章我们先实现基础版本。

但是大家要有权限意识。

Tool Calling 的安全边界一定在后端，不在模型。

---

# 三十三、30｜工具结果脱敏
## 【重点内容】
工具返回结果不一定都能原样交给模型。

比如订单系统返回：

```json
{
  "phone": "13812345678",
  "address": "成都市高新区某小区 1 栋 1001",
  "id_card": "..."
}
```

这些不能直接传给模型。

应该脱敏：

```json
{
  "phone": "138****5678",
  "address": "成都市高新区***",
  "id_card": null
}
```

所以真实项目里，Tool Result 需要做：

```plain
字段过滤
敏感信息脱敏
最小必要数据返回
```

模型只应该看到完成任务需要的信息。

---

# 三十四、31｜工具调用日志设计
## 【重点内容】
Tool Calling 一定要记录日志。

建议记录：

```plain
trace_id
user_id
tool_name
arguments 摘要
success / failed
error_message
latency_ms
model
tool_call_id
```

不要记录：

```plain
完整敏感参数
完整隐私数据
API Key
身份证号
手机号明文
地址明文
```

后面可以设计表：

```plain
tool_call_logs
├── id
├── trace_id
├── user_id
├── tool_name
├── arguments
├── result_summary
├── success
├── error_message
├── latency_ms
├── created_at
```

这一章先通过 logger 打日志。

后面平台化阶段再入库。

---

# 三十五、32｜Tool Calling 和 Agent 的关系
## 【重点内容】
Tool Calling 是 Agent 的基础。

没有工具调用，Agent 只能聊天。

有了工具调用，Agent 才能：

```plain
查数据
查订单
查知识库
调用 API
写文件
发通知
执行任务
```

但是 Tool Calling 还不是完整 Agent。

完整 Agent 还需要：

```plain
任务规划
状态管理
多步骤循环
工具选择
错误恢复
记忆
人类确认
执行终止条件
```

后面 LangGraph 阶段，我们会把 Tool Calling 放进图里，形成真正的 Agent workflow。

这一章先把工具调用这个基础能力做扎实。

---

# 三十六、33｜Tool Calling 和 RAG 的关系
## 【重点内容】
RAG 其实也可以看作一种工具调用。

比如：

```plain
search_knowledge_base(query)
```

模型遇到知识库问题时，可以调用这个工具检索文档。

然后基于检索结果回答。

未来我们可以定义：

```plain
search_documents
retrieve_chunks
rerank_documents
```

这些都可以作为 tools。

所以 Tool Calling 不只是电商客服。

它也是 RAG Agent 的基础。

---

# 三十七、34｜多工具调用
## 【重点内容】
有些模型一次可能返回多个 tool_calls。

比如：

```plain
先 query_order
再 query_logistics
```

DeepSeek 的 API 升级新闻提到 Function Calling 支持一次调用返回多个函数调用，数量上限以官方文档说明为准；OpenAI-compatible 的 tool_calls 结构本身也支持列表形式。

所以我们的代码里写的是：

```python
for tool_call in first_response.tool_calls:
```

而不是只处理第一个。

这就是为多工具调用预留扩展。

---

# 三十八、35｜Tool Calling 常见错误一：工具描述太模糊
不推荐：

```plain
查询信息
```

推荐：

```plain
根据订单号查询订单状态和物流信息。
当用户询问订单状态、发货状态、物流状态时使用。
```

---

## 【重点内容】
工具描述非常影响模型选择。

如果描述太模糊，模型不知道什么时候用。

所以描述要写清楚：

```plain
这个工具做什么
什么时候用
需要什么输入
不能做什么
```

Tool Schema 也是一种 Prompt。

---

# 三十九、36｜Tool Calling 常见错误二：参数 Schema 太宽
不推荐：

```json
{
  "type": "object",
  "properties": {
    "data": {
      "type": "object"
    }
  }
}
```

推荐：

```json
{
  "type": "object",
  "properties": {
    "order_id": {
      "type": "string",
      "description": "订单号"
    }
  },
  "required": ["order_id"]
}
```

---

## 【重点内容】
参数越明确，模型越容易生成正确参数。

不要给一个万能 data。

工具参数应该尽量小、明确、稳定。

---

# 四十、37｜Tool Calling 常见错误三：模型参数不校验直接执行
错误：

```python
await query_order(**tool_call.arguments)
```

正确：

```python
validated_args = QueryOrderArgs.model_validate(tool_call.arguments)
await query_order(**validated_args.model_dump())
```

---

## 【重点内容】
模型生成的参数一定要校验。

因为它可能：

```plain
少字段
多字段
字段类型错
枚举值错
把说明文字塞进参数
```

Pydantic 是后端的最后一道防线。

---

# 四十一、38｜Tool Calling 常见错误四：工具结果没回传给模型
错误流程：

```plain
模型返回 tool_calls
后端执行工具
直接把工具结果返回用户
```

这不是完整 Tool Calling。

完整流程应该是：

```plain
工具结果
再交回模型
让模型生成自然语言回复
```

因为工具结果是结构化数据，用户不一定看得懂。

模型负责把它转成友好的回答。

---

# 四十二、39｜Tool Calling 常见错误五：高风险工具自动执行
高风险工具包括：

```plain
退款
扣款
删除数据
发送邮件
发短信
修改订单
提交审批
外部系统写操作
```

这些工具不应该默认自动执行。

应该设置：

```plain
require_confirm=True
```

或者走人工确认。

---

# 四十三、40｜Tool Calling 常见错误六：所有场景都暴露所有工具
不推荐：

```plain
每次 Chat 都传全部 tools
```

推荐：

```plain
按场景暴露工具
```

比如：

```plain
电商客服场景：query_order / query_logistics / transfer_human

RAG 场景：search_knowledge_base

数据分析场景：query_database / generate_chart
```

工具越多，模型选择越容易混乱，token 成本也越高。

---

# 四十四、41｜Tool Calling 常见错误七：把工具返回的错误原样给用户
工具错误：

```plain
DatabaseTimeoutError: connection pool exhausted
```

不要直接给用户。

应该让模型或后端转换成友好话术：

```plain
抱歉，当前订单系统查询较慢，请稍后再试，或联系人工客服。
```

技术细节写日志即可。

---

# 四十五、42｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| Function Calling | 模型生成函数名和参数 |
| Tool Calling | 模型调用业务工具 |
| tools | 把可用工具告诉模型 |
| tool_choice | 控制是否调用工具 |
| tool_calls | 模型返回的工具调用请求 |
| ToolDefinition | 后端工具定义 |
| ToolRegistry | 工具注册和管理 |
| ToolExecutor | 工具校验和执行 |
| args_schema | 工具参数校验 |
| result_schema | 工具结果结构 |
| query_order | 电商订单查询 |
| query_logistics | 物流查询 |
| transfer_human | 转人工 |
| role=tool | 把工具结果回传模型 |
| tool_call_id | 关联工具调用和工具结果 |
| require_confirm | 高风险工具人工确认 |
| 工具脱敏 | 避免隐私泄露 |
| 多工具调用 | 支持复杂任务 |
| Agent 基础 | Agent 的行动能力 |


---

# 四十六、43｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Function Calling 是什么
2. 理解 Tool Calling 是什么
3. 理解 Function Calling 和 Structured Output 的区别
4. 理解 Tool Calling 完整链路
5. 理解 tools 参数结构
6. 理解 tool_choice
7. 理解工具调用安全原则
8. 创建 app/tools 目录
9. 定义 QueryOrderArgs / QueryOrderResult
10. 定义 QueryLogisticsArgs / QueryLogisticsResult
11. 定义 TransferHumanArgs / TransferHumanResult
12. 定义 ToolDefinition
13. 实现 to_openai_tool
14. 实现电商 mock 工具
15. 实现 ToolRegistry
16. 生成 OpenAI-compatible tools schema
17. 实现 ToolExecutor
18. 升级 LLM Schema 支持 tools / tool_choice / tool_calls
19. 升级 OpenAICompatibleProvider 传递 tools
20. 升级 OpenAICompatibleProvider 解析 tool_calls
21. 实现 ToolCallingService
22. 完成两阶段模型调用
23. 新增 Tool Calling API
24. 测试工具列表接口
25. 测试 /tools/run 自动工具调用
26. 理解 Tool Calling 和 ChatService 集成思路
27. 理解工具权限、脱敏、日志、安全
28. 理解 Tool Calling 和 Agent 的关系
```

现在我们的项目已经从：

```plain
模型只能回答
```

升级成：

```plain
模型可以选择工具，并由后端执行工具完成任务
```

这就是 Agent 能力的第一步。

---

# 四十七、44｜课后任务一：补全严谨版 assistant tool_calls message
要求：

```plain
1. 在 LLMMessage 中增加 tool_calls 字段
2. Provider 解析第一次 assistant message 时保留原始 tool_calls
3. 第二次调用模型时，把 assistant tool_calls message 原样追加回 messages
4. 再追加 role=tool 的工具结果
```

目标格式：

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [
    {
      "id": "call_xxx",
      "type": "function",
      "function": {
        "name": "query_order",
        "arguments": "{\"order_id\":\"10001\"}"
      }
    }
  ]
}
```

---

# 四十八、45｜课后任务二：增加工具权限控制
要求：

```plain
1. ToolDefinition 增加 required_roles
2. ToolExecutor.execute 增加 current_user 参数
3. 执行前判断用户角色
4. 无权限抛 ToolExecutionError
```

参考：

```python
required_roles: list[str] = Field(default_factory=list)
```

---

# 四十九、46｜课后任务三：新增 search_knowledge_base 工具
要求：

```plain
1. 定义 SearchKnowledgeBaseArgs
2. 定义 SearchKnowledgeBaseResult
3. 实现 search_knowledge_base mock 函数
4. 注册工具
5. 测试用户问“公司年假有几天？”时是否调用知识库搜索工具
```

---

# 五十、47｜课后任务四：新增工具调用日志表设计
要求设计表：

```plain
tool_call_logs
├── id
├── trace_id
├── user_id
├── tool_name
├── arguments
├── result_summary
├── success
├── error_message
├── latency_ms
├── created_at
```

并思考：

```plain
arguments 是否要脱敏？
result 是否完整保存？
失败是否要告警？
```

---

# 五十一、48｜课后任务五：让 ChatService 自动走工具调用
要求：

```plain
1. ChatRequest 中 prompt_scenario=ecommerce_customer_service 时启用 tools
2. 用户问订单或物流问题时走 ToolCallingService
3. 普通问题继续走普通 LLM Chat
4. 工具调用结果保存到 messages 表
5. tool_calls 信息暂时写入日志
```

---

# 五十二、49｜课后任务六：画出 Tool Calling 完整链路
画出：

```plain
POST /api/v1/tools/run
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
ToolCalling Router
 ↓
ToolCallingService
 ↓
Prompt + messages + tools
 ↓
LLMProvider.chat()
 ↓
模型返回 tool_calls
 ↓
解析 tool_name / arguments
 ↓
ToolExecutor
 ↓
ToolRegistry
 ↓
Pydantic 校验 arguments
 ↓
执行 query_order
 ↓
获得工具结果
 ↓
追加 role=tool message
 ↓
再次 LLMProvider.chat()
 ↓
生成最终客服回复
 ↓
ApiResponse
```

---

# 五十三、50｜本章总结
## 【重点内容】
好了，到这里，第 18 章我们就讲完了。

这一章非常关键。

因为我们完成了从：

```plain
模型输出内容
```

到：

```plain
模型调用工具
```

的升级。

大家一定要记住：

模型不是直接执行工具。

模型只是生成：

```plain
tool_name
arguments
```

后端必须做：

```plain
工具校验
权限校验
参数校验
工具执行
结果脱敏
错误处理
日志记录
```

这一章我们实现了：

```plain
ToolDefinition
ToolRegistry
ToolExecutor
query_order
query_logistics
transfer_human
LLMRequest tools / tool_choice
LLMResponse tool_calls
Provider 解析 tool_calls
ToolCallingService
/tools/run 接口
```

现在我们的系统已经具备了 Agent 的核心行动能力。

---
