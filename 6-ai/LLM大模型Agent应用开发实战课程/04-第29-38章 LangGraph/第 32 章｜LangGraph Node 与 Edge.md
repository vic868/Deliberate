---

# 一、本章定位
前面两章我们已经进入 LangGraph 阶段：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
```

第 31 章我们重点讲了 State。

也就是：

```plain
Graph 执行过程中的共享上下文。
```

这一章继续讲两个核心概念：

# Node 与 Edge
一句话理解：

```plain
Node：每一个处理步骤。
Edge：步骤之间怎么流转。
```

如果 State 是 Agent 的上下文，那么 Node 就是处理动作，Edge 就是流程路线。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Node 到底是什么
2. Node 的同步写法
3. Node 的异步写法
4. Node 如何读取 State
5. Node 如何返回 State 更新
6. Node 如何读取 RunnableConfig
7. Node 如何调用 LLM
8. Node 如何调用 Tool
9. Node 如何调用 RAG
10. Node 如何处理异常
11. Node 如何追加 logs / errors
12. Edge 到底是什么
13. START / END 怎么用
14. 普通 Edge 怎么写
15. 条件 Edge 怎么写
16. 条件路由函数怎么设计
17. 循环 Edge 怎么写
18. 如何避免无限循环
19. Command 和 Edge 的区别
20. Node 与 Edge 的设计原则
21. 电商客服 Agent 如何拆 Node
22. 订单查询 Node 如何写
23. 售后规则检索 Node 如何写
24. 最终回答生成 Node 如何写
25. 面试中如何讲 Node 与 Edge
```

---

# 三、本章版本口径
本课程 LangGraph 阶段统一使用：

```plain
Python：3.12+
Pydantic：v2
LangChain：1.x
LangGraph：1.x
```

安装：

```bash
uv add "langgraph>=1.2,<1.3" \
       "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6"
```

本章主要用到：

```python
from typing import Annotated, Literal, TypedDict
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
```

LangGraph 的 `add_node` 用来把函数或 Runnable 注册为图节点，`add_edge` 用来添加静态边，`add_conditional_edges` 用来添加条件边；如果条件路由函数没有明确的类型提示或 path map，图可视化时可能会假设它能跳到任意节点，所以课程里会强制写清楚 `Literal[...]` 和 path map。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langgraph_node_edge/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── mock_services.py
│   │   ├── demo_01_simple_node_edge.py
│   │   ├── demo_02_sequence_edges.py
│   │   ├── demo_03_conditional_edges.py
│   │   ├── demo_04_async_node.py
│   │   ├── demo_05_node_with_config.py
│   │   ├── demo_06_llm_node.py
│   │   ├── demo_07_tool_node.py
│   │   ├── demo_08_rag_node.py
│   │   ├── demo_09_error_node.py
│   │   ├── demo_10_loop_edge.py
│   │   ├── demo_11_command_node.py
│   │   └── demo_12_ecommerce_node_edge_graph.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg32_01_simple_node_edge.py
│   ├── test_lg32_02_sequence_edges.py
│   ├── test_lg32_03_conditional_edges.py
│   ├── test_lg32_04_async_node.py
│   ├── test_lg32_05_node_with_config.py
│   ├── test_lg32_06_llm_node.py
│   ├── test_lg32_07_tool_node.py
│   ├── test_lg32_08_rag_node.py
│   ├── test_lg32_09_error_node.py
│   ├── test_lg32_10_loop_edge.py
│   ├── test_lg32_11_command_node.py
│   └── test_lg32_12_ecommerce_node_edge_graph.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 32 章。

这一章我们专门讲 LangGraph 里的 Node 和 Edge。

上一章我们讲 State。

State 是图里的共享上下文。

但是光有 State 不够。

你还需要有人处理 State。

这个处理动作就是 Node。

比如电商客服 Agent 里：

```plain
识别意图
提取订单号
查询订单
查询售后规则
判断是否人工确认
生成最终回答
```

这些都可以拆成 Node。

然后 Node 之间怎么走？

这就是 Edge。

比如：

```plain
先识别意图
再提取订单号
再查询订单
如果是退款，再查售后规则
如果只是查订单，直接生成订单回答
```

这些流程关系就是 Edge。

这一章的核心目标就是：

让大家知道，一个复杂 Agent 到底应该怎么拆节点、怎么连边。

---

# 六、02｜Node 一句话解释
## 【实操】
```plain
Node
=
Graph 里的一个处理步骤
=
一个读取 State、返回 State 更新的函数
```

典型写法：

```python
def classify_intent_node(state: AgentState) -> dict:
    return {
        "intent": "refund"
    }
```

---

## 【重点内容】
Node 本质上就是一个函数。

它接收 State。

然后返回一个 dict。

这个 dict 代表要更新到 State 里的字段。

注意，不是让你返回完整 State。

而是返回当前节点负责更新的那部分字段。

比如意图识别节点只负责更新：

```plain
intent
logs
```

订单查询节点只负责更新：

```plain
order_info
tool_calls
logs
```

这样每个节点职责清晰。

---

# 七、03｜Edge 一句话解释
## 【实操】
```plain
Edge
=
Node 之间的连线
=
执行顺序和路由规则
```

普通边：

```python
graph.add_edge("extract_order_id", "query_order")
```

条件边：

```python
graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "general": "general_answer",
        "refund": "refund_flow",
    },
)
```

---

## 【重点内容】
Edge 就是流程怎么走。

普通边适合固定流程。

比如：

```plain
extract_order_id
 ↓
query_order
```

条件边适合动态流程。

比如：

```plain
intent=general -> general_answer
intent=refund -> refund_flow
intent=query_order -> query_order
```

真实 Agent 里，条件边非常常见。

因为业务流程经常要根据 State 决定下一步。

---

# 八、04｜创建目录
执行：

```bash
mkdir -p app/langgraph_node_edge

touch app/langgraph_node_edge/__init__.py
touch app/langgraph_node_edge/schemas.py
touch app/langgraph_node_edge/mock_services.py
touch app/langgraph_node_edge/demo_01_simple_node_edge.py
touch app/langgraph_node_edge/demo_02_sequence_edges.py
touch app/langgraph_node_edge/demo_03_conditional_edges.py
touch app/langgraph_node_edge/demo_04_async_node.py
touch app/langgraph_node_edge/demo_05_node_with_config.py
touch app/langgraph_node_edge/demo_06_llm_node.py
touch app/langgraph_node_edge/demo_07_tool_node.py
touch app/langgraph_node_edge/demo_08_rag_node.py
touch app/langgraph_node_edge/demo_09_error_node.py
touch app/langgraph_node_edge/demo_10_loop_edge.py
touch app/langgraph_node_edge/demo_11_command_node.py
touch app/langgraph_node_edge/demo_12_ecommerce_node_edge_graph.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_node_edge

New-Item app\langgraph_node_edge\__init__.py
New-Item app\langgraph_node_edge\schemas.py
New-Item app\langgraph_node_edge\mock_services.py
New-Item app\langgraph_node_edge\demo_01_simple_node_edge.py
New-Item app\langgraph_node_edge\demo_02_sequence_edges.py
New-Item app\langgraph_node_edge\demo_03_conditional_edges.py
New-Item app\langgraph_node_edge\demo_04_async_node.py
New-Item app\langgraph_node_edge\demo_05_node_with_config.py
New-Item app\langgraph_node_edge\demo_06_llm_node.py
New-Item app\langgraph_node_edge\demo_07_tool_node.py
New-Item app\langgraph_node_edge\demo_08_rag_node.py
New-Item app\langgraph_node_edge\demo_09_error_node.py
New-Item app\langgraph_node_edge\demo_10_loop_edge.py
New-Item app\langgraph_node_edge\demo_11_command_node.py
New-Item app\langgraph_node_edge\demo_12_ecommerce_node_edge_graph.py
```

---

# 九、05｜准备公共 State Schema
打开：

```plain
app/langgraph_node_edge/schemas.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict


class OrderInfo(TypedDict, total=False):
    order_id: str
    status: str
    status_text: str
    tracking_company: str | None
    tracking_no: str | None
    latest_event: str | None


class SourceInfo(TypedDict, total=False):
    document_id: str
    chunk_id: str
    source: str
    content_preview: str
    score: float


class ToolCallInfo(TypedDict, total=False):
    name: str
    args: dict
    id: str
    success: bool
    result_preview: str


class EcommerceNodeEdgeState(TypedDict):
    user_question: str

    intent: Literal[
        "general",
        "query_order",
        "logistics",
        "refund",
        "human_service",
        "unknown",
    ]

    order_id: str | None
    order_info: OrderInfo | None

    policy_query: str | None
    policy_answer: str | None
    sources: Annotated[list[SourceInfo], operator.add]

    need_human_confirm: bool
    risk_level: Literal["low", "medium", "high"]
    pending_action: str | None

    tool_calls: Annotated[list[ToolCallInfo], operator.add]
    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

    final_answer: str
    retry_count: int
    is_finished: bool
```

---

## 【重点内容】
这里我们定义了本章公共 State。

它不是最终项目版，但已经很接近企业 Agent 了。

里面有几类字段：

```plain
用户问题
意图
订单信息
售后规则
人工确认
工具调用
日志
错误
最终回答
重试次数
```

注意：

```python
sources
tool_calls
logs
errors
```

这些字段用了 reducer。

因为它们通常需要多个节点追加。

---

# 十、06｜准备 Mock Service
为了让本章示例先跑通，我们准备一个 mock 服务文件。

打开：

```plain
app/langgraph_node_edge/mock_services.py
```

写入：

```python
import asyncio


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
}


async def mock_query_order(order_id: str | None) -> dict:
    await asyncio.sleep(0.05)

    if not order_id:
        return {
            "order_id": "",
            "status": "missing_order_id",
            "status_text": "缺少订单号",
            "tracking_company": None,
            "tracking_no": None,
            "latest_event": None,
        }

    return MOCK_ORDERS.get(
        order_id,
        {
            "order_id": order_id,
            "status": "not_found",
            "status_text": "未查询到订单",
            "tracking_company": None,
            "tracking_no": None,
            "latest_event": None,
        },
    )


async def mock_retrieve_policy(
    order_status: str | None,
) -> dict:
    await asyncio.sleep(0.05)

    if order_status == "paid":
        return {
            "policy_query": "订单未发货退款规则",
            "policy_answer": "订单未发货时，用户可以申请取消订单并退款。",
            "sources": [
                {
                    "document_id": "ecommerce_after_sales",
                    "chunk_id": "ecommerce_after_sales_chunk_0",
                    "source": "data/knowledge_base/ecommerce_after_sales.md",
                    "content_preview": "订单未发货时，用户可以申请取消订单并退款。",
                    "score": 0.92,
                }
            ],
        }

    if order_status == "shipped":
        return {
            "policy_query": "订单已发货退货退款规则",
            "policy_answer": "订单已发货后，需要用户收到商品后再发起退货退款申请。",
            "sources": [
                {
                    "document_id": "ecommerce_after_sales",
                    "chunk_id": "ecommerce_after_sales_chunk_1",
                    "source": "data/knowledge_base/ecommerce_after_sales.md",
                    "content_preview": "订单已发货后，需要用户收到商品后再发起退货退款申请。",
                    "score": 0.89,
                }
            ],
        }

    return {
        "policy_query": "退款规则",
        "policy_answer": "当前订单状态无法确认退款规则，建议转人工客服。",
        "sources": [],
    }


def create_initial_state(
    user_question: str,
) -> dict:
    return {
        "user_question": user_question,

        "intent": "unknown",

        "order_id": None,
        "order_info": None,

        "policy_query": None,
        "policy_answer": None,
        "sources": [],

        "need_human_confirm": False,
        "risk_level": "low",
        "pending_action": None,

        "tool_calls": [],
        "logs": [],
        "errors": [],

        "final_answer": "",
        "retry_count": 0,
        "is_finished": False,
    }
```

---

## 【重点内容】
这个 mock_services 先模拟三个东西：

```plain
1. 订单查询
2. 售后规则查询
3. State 初始化
```

后面第 38 章项目二里，我们会把这些 mock 替换成真实能力：

```plain
真实 query_order Tool
真实 RAG Service
真实 ChatModel
真实日志和异常处理
```

这一章先把 Node 和 Edge 的设计讲清楚。

---

# 十一、07｜示例一：最小 Node + Edge
打开：

```plain
app/langgraph_node_edge/demo_01_simple_node_edge.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SimpleState(TypedDict):
    user_question: str
    final_answer: str


def answer_node(state: SimpleState) -> dict:
    return {
        "final_answer": f"你问的是：{state['user_question']}"
    }


def build_graph():
    graph = StateGraph(SimpleState)

    graph.add_node("answer", answer_node)

    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "Node 和 Edge 是什么？",
        "final_answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_01_simple_node_edge.py
```

写入：

```python
from app.langgraph_node_edge.demo_01_simple_node_edge import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg32_01_simple_node_edge.py
```

---

## 【重点内容】
这是最小 Node + Edge。

这里只有一个节点：

```plain
answer_node
```

两条边：

```plain
START -> answer
answer -> END
```

这就是最小图。

后面再复杂，都是这个基础扩展出来的。

---

# 十二、08｜示例二：顺序 Edge
打开：

```plain
app/langgraph_node_edge/demo_02_sequence_edges.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SequenceState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    final_answer: str


def classify_intent_node(state: SequenceState) -> dict:
    question = state["user_question"]

    if "订单" in question:
        intent = "query_order"
    else:
        intent = "general"

    return {
        "intent": intent
    }


def extract_order_id_node(state: SequenceState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        return {"order_id": "10001"}

    return {"order_id": None}


def answer_node(state: SequenceState) -> dict:
    return {
        "final_answer": (
            f"意图：{state['intent']}，"
            f"订单号：{state['order_id']}"
        )
    }


def build_graph():
    graph = StateGraph(SequenceState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "extract_order_id")
    graph.add_edge("extract_order_id", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "帮我查一下订单 10001。",
        "intent": "unknown",
        "order_id": None,
        "final_answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_02_sequence_edges.py
```

写入：

```python
from app.langgraph_node_edge.demo_02_sequence_edges import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个图是固定顺序。

流程是：

```plain
classify_intent
 ↓
extract_order_id
 ↓
answer
```

不管用户问什么，都会按这个顺序走。

这种适合固定流程。

比如文档索引流程：

```plain
解析文件
切 chunk
生成 embedding
写向量库
```

---

# 十三、09｜示例三：条件 Edge
打开：

```plain
app/langgraph_node_edge/demo_03_conditional_edges.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RouteState(TypedDict):
    user_question: str
    intent: str
    final_answer: str


def classify_intent_node(state: RouteState) -> dict:
    question = state["user_question"]

    if "退款" in question:
        intent = "refund"
    elif "订单" in question:
        intent = "query_order"
    else:
        intent = "general"

    return {
        "intent": intent
    }


def route_by_intent(
    state: RouteState,
) -> Literal["general", "query_order", "refund"]:
    return state["intent"]  # type: ignore[return-value]


def general_answer_node(state: RouteState) -> dict:
    return {
        "final_answer": "这是普通问题，走普通 Chat。"
    }


def query_order_node(state: RouteState) -> dict:
    return {
        "final_answer": "这是订单查询问题，下一步应该调用订单工具。"
    }


def refund_node(state: RouteState) -> dict:
    return {
        "final_answer": "这是退款问题，下一步应该查订单状态和退款规则。"
    }


def build_graph():
    graph = StateGraph(RouteState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("refund", refund_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "general_answer",
            "query_order": "query_order",
            "refund": "refund",
        },
    )

    graph.add_edge("general_answer", END)
    graph.add_edge("query_order", END)
    graph.add_edge("refund", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "帮我查一下订单 10001。",
        "我的订单还没发货，可以退款吗？",
    ]

    for question in questions:
        result = app.invoke({
            "user_question": question,
            "intent": "unknown",
            "final_answer": "",
        })

        print("question:", question)
        print("intent:", result["intent"])
        print("final_answer:", result["final_answer"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_03_conditional_edges.py
```

写入：

```python
from app.langgraph_node_edge.demo_03_conditional_edges import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子是条件边。

核心是：

```python
graph.add_conditional_edges(...)
```

它会在 classify_intent 执行后，根据 route_by_intent 的返回值决定下一步。

注意 route 函数最好写返回类型：

```python
Literal["general", "query_order", "refund"]
```

这样代码更清晰，可视化也更准确。

---

# 十四、10｜Node 的设计原则
## 原则一：一个 Node 只做一件事
不推荐：

```plain
一个节点里：
识别意图
提取订单号
查订单
查知识库
生成回答
```

推荐：

```plain
classify_intent_node
extract_order_id_node
query_order_node
retrieve_policy_node
generate_answer_node
```

---

## 原则二：Node 返回局部更新
不推荐：

```python
state["intent"] = "refund"
return state
```

推荐：

```python
return {
    "intent": "refund"
}
```

---

## 原则三：Node 要可单独测试
每个 Node 最好能单独输入 State，单独看输出。

这样排查问题非常方便。

---

## 原则四：Node 里不要写太深的分支
复杂路由交给 Edge。

Node 负责做事。

Edge 负责决定下一步。

---

# 十五、11｜示例四：异步 Node
打开：

```plain
app/langgraph_node_edge/demo_04_async_node.py
```

写入：

```python
import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AsyncNodeState(TypedDict):
    user_question: str
    order_id: str | None
    order_status: str
    final_answer: str


async def extract_order_id_node(state: AsyncNodeState) -> dict:
    await asyncio.sleep(0.05)

    if "10001" in state["user_question"]:
        return {"order_id": "10001"}

    return {"order_id": None}


async def query_order_node(state: AsyncNodeState) -> dict:
    await asyncio.sleep(0.05)

    if state["order_id"] == "10001":
        return {"order_status": "已发货"}

    return {"order_status": "未查询到订单"}


async def answer_node(state: AsyncNodeState) -> dict:
    await asyncio.sleep(0.05)

    return {
        "final_answer": f"订单状态：{state['order_status']}"
    }


def build_graph():
    graph = StateGraph(AsyncNodeState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")
    graph.add_edge("query_order", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


async def main():
    app = build_graph()

    result = await app.ainvoke({
        "user_question": "帮我查一下订单 10001。",
        "order_id": None,
        "order_status": "",
        "final_answer": "",
    })

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_04_async_node.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_04_async_node import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
真实项目里，大部分 Node 都可能是异步的。

比如：

```plain
调用 LLM
查数据库
查 Redis
调用 HTTP API
执行 RAG
```

这些都应该写成 async node。

FastAPI 项目里也更推荐用：

```python
await graph.ainvoke(...)
```

这样不会阻塞服务。

---

# 十六、12｜示例五：Node 读取 Config
打开：

```plain
app/langgraph_node_edge/demo_05_node_with_config.py
```

写入：

```python
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph


class ConfigNodeState(TypedDict):
    user_question: str
    order_id: str | None
    final_answer: str


def extract_order_id_node(state: ConfigNodeState) -> dict:
    if "10001" in state["user_question"]:
        return {"order_id": "10001"}

    return {"order_id": None}


def query_order_node(
    state: ConfigNodeState,
    config: RunnableConfig,
) -> dict:
    configurable = config.get("configurable", {})

    user_id = configurable.get("user_id", "unknown")
    trace_id = configurable.get("trace_id", "unknown")

    return {
        "final_answer": (
            f"trace_id={trace_id}，"
            f"用户 {user_id} 查询订单 {state['order_id']}。"
            "真实项目这里要做订单归属校验。"
        )
    }


def build_graph():
    graph = StateGraph(ConfigNodeState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)

    graph.add_edge(START, "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")
    graph.add_edge("query_order", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        {
            "user_question": "帮我查一下订单 10001。",
            "order_id": None,
            "final_answer": "",
        },
        config={
            "configurable": {
                "thread_id": "thread_lg32_config_001",
                "user_id": "u_10001",
                "trace_id": "trace_lg32_abc",
            }
        },
    )

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_05_node_with_config.py
```

写入：

```python
from app.langgraph_node_edge.demo_05_node_with_config import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
Node 可以读取 RunnableConfig。

这在企业项目里非常常用。

比如：

```plain
user_id
tenant_id
trace_id
conversation_id
permissions
```

这些运行上下文不一定放 State。

可以放 config。

节点需要时读取即可。

LangGraph 运行时文档也说明，可以通过在节点函数中增加 `config: RunnableConfig` 参数来访问运行配置。

---

# 十七、13｜示例六：LLM Node
这个示例需要你已经完成第 22 章的：

```plain
app.langchain_models.model_factory.LangChainModelFactory
```

打开：

```plain
app/langgraph_node_edge/demo_06_llm_node.py
```

写入：

```python
import asyncio
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.langchain_models.model_factory import LangChainModelFactory


class LLMNodeState(TypedDict):
    user_question: str
    draft_answer: str
    final_answer: str


async def draft_answer_node(state: LLMNodeState) -> dict:
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.3,
    )

    response = await model.ainvoke([
        SystemMessage(
            content=(
                "你是一个 AI Agent 课程助教。"
                "回答要简洁、口语化。"
            )
        ),
        HumanMessage(
            content=state["user_question"]
        ),
    ])

    return {
        "draft_answer": str(response.content)
    }


async def polish_answer_node(state: LLMNodeState) -> dict:
    return {
        "final_answer": (
            "【最终回答】\n"
            + state["draft_answer"].strip()
        )
    }


def build_graph():
    graph = StateGraph(LLMNodeState)

    graph.add_node("draft_answer", draft_answer_node)
    graph.add_node("polish_answer", polish_answer_node)

    graph.add_edge(START, "draft_answer")
    graph.add_edge("draft_answer", "polish_answer")
    graph.add_edge("polish_answer", END)

    return graph.compile()


async def main():
    app = build_graph()

    result = await app.ainvoke({
        "user_question": "为什么复杂 Agent 需要 LangGraph？",
        "draft_answer": "",
        "final_answer": "",
    })

    print(result["final_answer"])


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_06_llm_node.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_06_llm_node import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个例子展示 LLM Node。

核心就是：

```plain
Node 内部调用 ChatModel
```

Node 不一定都是规则函数。

它可以调用：

```plain
LLM
Prompt
Parser
Tool
RAG
数据库
HTTP API
```

LangGraph 的价值是把这些能力组织成图。

---

# 十八、14｜示例七：Tool Node
打开：

```plain
app/langgraph_node_edge/demo_07_tool_node.py
```

写入：

```python
import asyncio

from langgraph.graph import END, START, StateGraph

from app.langgraph_node_edge.mock_services import (
    create_initial_state,
    mock_query_order,
)
from app.langgraph_node_edge.schemas import EcommerceNodeEdgeState


def extract_order_id_node(state: EcommerceNodeEdgeState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：订单号为 {order_id}"],
    }


async def query_order_tool_node(
    state: EcommerceNodeEdgeState,
) -> dict:
    order_info = await mock_query_order(
        order_id=state["order_id"]
    )

    return {
        "order_info": order_info,
        "tool_calls": [
            {
                "name": "query_order",
                "args": {
                    "order_id": state["order_id"],
                },
                "id": "tool_call_query_order_001",
                "success": True,
                "result_preview": order_info["status_text"],
            }
        ],
        "logs": [
            f"query_order_tool_node：{order_info['status_text']}"
        ],
    }


def answer_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    return {
        "final_answer": f"您的订单状态是：{order_info['status_text']}。",
        "is_finished": True,
        "logs": ["answer_node：订单回答生成完成"],
    }


def build_graph():
    graph = StateGraph(EcommerceNodeEdgeState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_tool_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")
    graph.add_edge("query_order", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


async def main():
    app = build_graph()

    result = await app.ainvoke(
        create_initial_state("帮我查一下订单 10001。")
    )

    print("final_answer:", result["final_answer"])
    print("tool_calls:", result["tool_calls"])
    print("logs:", result["logs"])


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_07_tool_node.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_07_tool_node import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个例子就是 Tool Node。

注意这个节点不负责判断要不要查订单。

它只负责：

```plain
拿到 order_id
调用订单工具
写入 order_info
追加 tool_calls
追加 logs
```

这就是一个好 Node 的设计。

职责单一。

输入输出清晰。

---

# 十九、15｜示例八：RAG Node
打开：

```plain
app/langgraph_node_edge/demo_08_rag_node.py
```

写入：

```python
import asyncio

from langgraph.graph import END, START, StateGraph

from app.langgraph_node_edge.mock_services import (
    create_initial_state,
    mock_query_order,
    mock_retrieve_policy,
)
from app.langgraph_node_edge.schemas import EcommerceNodeEdgeState


def extract_order_id_node(state: EcommerceNodeEdgeState) -> dict:
    if "10002" in state["user_question"]:
        return {
            "order_id": "10002",
            "logs": ["extract_order_id：订单号为 10002"],
        }

    return {
        "order_id": None,
        "logs": ["extract_order_id：未提取到订单号"],
    }


async def query_order_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = await mock_query_order(state["order_id"])

    return {
        "order_info": order_info,
        "logs": [f"query_order：{order_info['status_text']}"],
    }


async def retrieve_policy_rag_node(
    state: EcommerceNodeEdgeState,
) -> dict:
    order_info = state["order_info"]

    policy_result = await mock_retrieve_policy(
        order_status=order_info.get("status"),
    )

    return {
        "policy_query": policy_result["policy_query"],
        "policy_answer": policy_result["policy_answer"],
        "sources": policy_result["sources"],
        "logs": ["retrieve_policy_rag_node：完成售后规则检索"],
    }


def answer_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    return {
        "final_answer": (
            f"您的订单状态是：{order_info['status_text']}。"
            f"{state['policy_answer']}"
        ),
        "is_finished": True,
        "logs": ["answer_node：最终回答完成"],
    }


def build_graph():
    graph = StateGraph(EcommerceNodeEdgeState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("retrieve_policy", retrieve_policy_rag_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")
    graph.add_edge("query_order", "retrieve_policy")
    graph.add_edge("retrieve_policy", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


async def main():
    app = build_graph()

    result = await app.ainvoke(
        create_initial_state("我的订单 10002 还没发货，可以退款吗？")
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("sources:")
    for source in result["sources"]:
        print(source)

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_08_rag_node.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_08_rag_node import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个例子就是 RAG Node。

它不关心订单怎么查。

它只根据订单状态检索售后规则。

真实项目里，这个节点会调用第 27 章的：

```plain
langchain_rag_service.ask
```

或者更底层的 Retriever。

节点职责还是很清楚：

```plain
输入 order_info
输出 policy_answer 和 sources
```

---

# 二十、16｜示例九：异常处理 Node
打开：

```plain
app/langgraph_node_edge/demo_09_error_node.py
```

写入：

```python
import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_node_edge.mock_services import create_initial_state
from app.langgraph_node_edge.schemas import EcommerceNodeEdgeState


async def risky_tool_node(state: EcommerceNodeEdgeState) -> dict:
    try:
        if "异常" in state["user_question"]:
            raise RuntimeError("模拟工具调用失败")

        return {
            "logs": ["risky_tool_node：工具调用成功"],
            "final_answer": "工具调用成功，正常返回结果。",
            "is_finished": True,
        }

    except Exception as exc:
        return {
            "errors": [repr(exc)],
            "logs": ["risky_tool_node：工具调用失败"],
        }


def route_after_risky_tool(
    state: EcommerceNodeEdgeState,
) -> Literal["error_handler", "end"]:
    if state["errors"]:
        return "error_handler"

    return "end"


def error_handler_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "当前服务暂时异常，请稍后再试，或联系人工客服。",
        "is_finished": True,
        "logs": ["error_handler_node：已生成兜底回答"],
    }


def build_graph():
    graph = StateGraph(EcommerceNodeEdgeState)

    graph.add_node("risky_tool", risky_tool_node)
    graph.add_node("error_handler", error_handler_node)

    graph.add_edge(START, "risky_tool")

    graph.add_conditional_edges(
        "risky_tool",
        route_after_risky_tool,
        {
            "error_handler": "error_handler",
            "end": END,
        },
    )

    graph.add_edge("error_handler", END)

    return graph.compile()


async def main():
    app = build_graph()

    for question in ["正常问题", "这个问题会触发异常"]:
        result = await app.ainvoke(
            create_initial_state(question)
        )

        print("question:", question)
        print("final_answer:", result["final_answer"])
        print("errors:", result["errors"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_09_error_node.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_09_error_node import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个示例展示异常处理。

真实项目里，Node 可能失败：

```plain
LLM 调用失败
数据库失败
工具超时
RAG 检索失败
参数校验失败
```

推荐做法是：

```plain
Node 捕获异常
写入 errors
通过条件边进入 error_handler
生成用户可理解的兜底回答
```

不要把 Python 错误直接返回给用户。

---

# 二十一、17｜示例十：循环 Edge
打开：

```plain
app/langgraph_node_edge/demo_10_loop_edge.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class LoopState(TypedDict):
    user_question: str
    draft: str
    review_result: str
    retry_count: int
    final_answer: str


def generate_draft_node(state: LoopState) -> dict:
    retry_count = state["retry_count"]

    if retry_count == 0:
        draft = "这是一个很粗糙的回答。"
    else:
        draft = "这是一个更完整、更清晰的回答。"

    return {
        "draft": draft
    }


def review_node(state: LoopState) -> dict:
    if "粗糙" in state["draft"] and state["retry_count"] < 1:
        return {
            "review_result": "need_refine",
            "retry_count": state["retry_count"] + 1,
        }

    return {
        "review_result": "pass"
    }


def route_after_review(
    state: LoopState,
) -> Literal["refine", "finish"]:
    if state["review_result"] == "need_refine":
        return "refine"

    return "finish"


def finish_node(state: LoopState) -> dict:
    return {
        "final_answer": state["draft"]
    }


def build_graph():
    graph = StateGraph(LoopState)

    graph.add_node("generate_draft", generate_draft_node)
    graph.add_node("review", review_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "generate_draft")
    graph.add_edge("generate_draft", "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "refine": "generate_draft",
            "finish": "finish",
        },
    )

    graph.add_edge("finish", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        {
            "user_question": "解释一下 LangGraph Node 与 Edge。",
            "draft": "",
            "review_result": "",
            "retry_count": 0,
            "final_answer": "",
        },
        config={
            "recursion_limit": 10
        },
    )

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_10_loop_edge.py
```

写入：

```python
from app.langgraph_node_edge.demo_10_loop_edge import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示循环边。

流程是：

```plain
generate_draft
 ↓
review
 ↓
如果不通过，回到 generate_draft
如果通过，finish
```

循环要非常小心。

一定要有退出条件。

这里我们用：

```plain
retry_count
```

控制最多改一次。

同时也可以通过：

```python
config={"recursion_limit": 10}
```

限制图最大递归步数。

LangGraph 文档里也强调，图循环通常需要条件边路由到 `END` 作为退出条件，并可以通过 `recursion_limit` 避免无限循环。

---

# 二十二、18｜示例十一：Command Node
打开：

```plain
app/langgraph_node_edge/demo_11_command_node.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class CommandRouteState(TypedDict):
    user_question: str
    intent: str
    final_answer: str


def router_node(
    state: CommandRouteState,
) -> Command[Literal["general_node", "refund_node"]]:
    question = state["user_question"]

    if "退款" in question:
        return Command(
            update={
                "intent": "refund"
            },
            goto="refund_node",
        )

    return Command(
        update={
            "intent": "general"
        },
        goto="general_node",
    )


def general_node(state: CommandRouteState) -> dict:
    return {
        "final_answer": "这是普通问题。"
    }


def refund_node(state: CommandRouteState) -> dict:
    return {
        "final_answer": "这是退款问题，需要进入订单和售后规则流程。"
    }


def build_graph():
    graph = StateGraph(CommandRouteState)

    graph.add_node("router", router_node)
    graph.add_node("general_node", general_node)
    graph.add_node("refund_node", refund_node)

    graph.add_edge(START, "router")
    graph.add_edge("general_node", END)
    graph.add_edge("refund_node", END)

    return graph.compile()


def main():
    app = build_graph()

    for question in ["你好", "我的订单可以退款吗？"]:
        result = app.invoke({
            "user_question": question,
            "intent": "unknown",
            "final_answer": "",
        })

        print("question:", question)
        print(result)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg32_11_command_node.py
```

写入：

```python
from app.langgraph_node_edge.demo_11_command_node import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
Command 可以让 Node 同时做两件事：

```plain
更新 State
指定下一步 goto
```

但是要注意，不要在同一个节点上又返回 Command，又给它加普通静态边。

否则可能会出现两个后续节点都执行的情况。

官方 Graph API 文档明确提醒，如果节点返回 `Command(goto=...)`，同时又配置了普通 `add_edge`，两个目标都可能运行，因此每个节点应该选择一种路由方式。

---

# 二十三、19｜Edge 的设计原则
## 原则一：固定流程用普通 Edge
```python
graph.add_edge("parse_file", "split_text")
graph.add_edge("split_text", "embed_chunks")
graph.add_edge("embed_chunks", "save_vector")
```

---

## 原则二：动态流程用 Conditional Edge
```python
graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "general": "general_answer",
        "refund": "refund_flow",
    },
)
```

---

## 原则三：同一个节点不要混用静态边和动态路由
不推荐：

```python
graph.add_edge("router", "node_a")
graph.add_conditional_edges("router", route_func, ...)
```

---

## 原则四：循环一定要有退出条件
```plain
retry_count
max_steps
is_finished
tool_calls_count
```

---

## 原则五：路由函数只负责路由
不推荐在路由函数里调用模型、工具、数据库。

路由函数应该尽量简单。

---

# 二十四、20｜电商客服 Agent 应该怎么拆 Node
电商客服 Agent 可以拆成：

```plain
1. classify_intent_node
2. extract_order_id_node
3. route_by_intent
4. ask_order_id_node
5. query_order_node
6. route_after_query_order
7. retrieve_policy_node
8. assess_risk_node
9. human_confirm_node
10. generate_answer_node
11. error_handler_node
```

---

## 【重点内容】
大家看这个拆法。

每个节点都非常明确。

比如：

```plain
classify_intent_node 只识别意图
extract_order_id_node 只提取订单号
query_order_node 只查订单
retrieve_policy_node 只查知识库规则
assess_risk_node 只判断风险
generate_answer_node 只生成最终回答
```

这样后面任何一个环节出问题，都能单独排查。

---

# 二十五、21｜综合示例：电商客服 Node + Edge Graph
打开：

```plain
app/langgraph_node_edge/demo_12_ecommerce_node_edge_graph.py
```

写入：

```python
import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_node_edge.mock_services import (
    create_initial_state,
    mock_query_order,
    mock_retrieve_policy,
)
from app.langgraph_node_edge.schemas import EcommerceNodeEdgeState


def classify_intent_node(state: EcommerceNodeEdgeState) -> dict:
    question = state["user_question"]

    if "人工" in question:
        intent = "human_service"
    elif "退款" in question or "退货" in question:
        intent = "refund"
    elif "物流" in question:
        intent = "logistics"
    elif "订单" in question:
        intent = "query_order"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：{intent}"],
    }


def route_by_intent(
    state: EcommerceNodeEdgeState,
) -> Literal["general", "human", "need_order"]:
    if state["intent"] == "general":
        return "general"

    if state["intent"] == "human_service":
        return "human"

    return "need_order"


def general_answer_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "这是一个普通问题，可以走普通 ChatModel 生成回答。",
        "is_finished": True,
        "logs": ["general_answer：普通回答完成"],
    }


def transfer_human_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "我已经为您转接人工客服，请稍等。",
        "is_finished": True,
        "tool_calls": [
            {
                "name": "transfer_human",
                "args": {
                    "reason": state["user_question"],
                },
                "id": "tool_call_transfer_human_001",
                "success": True,
                "result_preview": "已创建人工客服工单",
            }
        ],
        "logs": ["transfer_human：已创建人工客服工单"],
    }


def extract_order_id_node(state: EcommerceNodeEdgeState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：{order_id}"],
    }


def route_after_extract_order_id(
    state: EcommerceNodeEdgeState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "请您提供订单号，我才能继续查询订单状态。",
        "is_finished": True,
        "logs": ["ask_order_id：缺少订单号"],
    }


async def query_order_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = await mock_query_order(
        order_id=state["order_id"]
    )

    return {
        "order_info": order_info,
        "tool_calls": [
            {
                "name": "query_order",
                "args": {
                    "order_id": state["order_id"],
                },
                "id": "tool_call_query_order_001",
                "success": True,
                "result_preview": order_info["status_text"],
            }
        ],
        "logs": [f"query_order：{order_info['status_text']}"],
    }


def route_after_query_order(
    state: EcommerceNodeEdgeState,
) -> Literal["retrieve_policy", "generate_order_answer", "error_handler"]:
    order_info = state["order_info"]

    if not order_info:
        return "error_handler"

    if order_info["status"] == "not_found":
        return "generate_order_answer"

    if state["intent"] == "refund":
        return "retrieve_policy"

    return "generate_order_answer"


async def retrieve_policy_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    policy_result = await mock_retrieve_policy(
        order_status=order_info.get("status"),
    )

    return {
        "policy_query": policy_result["policy_query"],
        "policy_answer": policy_result["policy_answer"],
        "sources": policy_result["sources"],
        "logs": ["retrieve_policy：完成规则检索"],
    }


def assess_risk_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    if state["intent"] == "refund" and order_info["status"] == "shipped":
        return {
            "risk_level": "medium",
            "need_human_confirm": False,
            "pending_action": None,
            "logs": ["assess_risk：已发货退款，建议用户收货后申请退货退款"],
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,
        "logs": ["assess_risk：低风险"],
    }


def route_after_assess_risk(
    state: EcommerceNodeEdgeState,
) -> Literal["human_confirm", "generate_refund_answer"]:
    if state["need_human_confirm"]:
        return "human_confirm"

    return "generate_refund_answer"


def human_confirm_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "该操作需要人工确认，我已经为您提交人工处理。",
        "is_finished": True,
        "logs": ["human_confirm：进入人工确认"],
    }


def generate_order_answer_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    if order_info["status"] == "not_found":
        answer = "没有查询到该订单，请您检查订单号是否正确。"
    else:
        answer = f"您的订单当前状态是：{order_info['status_text']}。"

        if order_info.get("tracking_no"):
            answer += (
                f"物流公司：{order_info['tracking_company']}，"
                f"物流单号：{order_info['tracking_no']}，"
                f"最新节点：{order_info['latest_event']}"
            )

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["generate_order_answer：订单回答完成"],
    }


def generate_refund_answer_node(state: EcommerceNodeEdgeState) -> dict:
    order_info = state["order_info"]

    answer = (
        f"您的订单当前状态是：{order_info['status_text']}。"
        f"{state['policy_answer']}"
    )

    if state["sources"]:
        answer += " 回答依据来自售后规则知识库。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["generate_refund_answer：退款回答完成"],
    }


def error_handler_node(state: EcommerceNodeEdgeState) -> dict:
    return {
        "final_answer": "当前处理失败，请稍后再试，或联系人工客服。",
        "is_finished": True,
        "errors": ["order_info 为空"],
        "logs": ["error_handler：兜底处理"],
    }


def build_graph():
    graph = StateGraph(EcommerceNodeEdgeState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("transfer_human", transfer_human_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("human_confirm", human_confirm_node)
    graph.add_node("generate_order_answer", generate_order_answer_node)
    graph.add_node("generate_refund_answer", generate_refund_answer_node)
    graph.add_node("error_handler", error_handler_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "general_answer",
            "human": "transfer_human",
            "need_order": "extract_order_id",
        },
    )

    graph.add_conditional_edges(
        "extract_order_id",
        route_after_extract_order_id,
        {
            "ask_order_id": "ask_order_id",
            "query_order": "query_order",
        },
    )

    graph.add_conditional_edges(
        "query_order",
        route_after_query_order,
        {
            "retrieve_policy": "retrieve_policy",
            "generate_order_answer": "generate_order_answer",
            "error_handler": "error_handler",
        },
    )

    graph.add_edge("retrieve_policy", "assess_risk")

    graph.add_conditional_edges(
        "assess_risk",
        route_after_assess_risk,
        {
            "human_confirm": "human_confirm",
            "generate_refund_answer": "generate_refund_answer",
        },
    )

    graph.add_edge("general_answer", END)
    graph.add_edge("transfer_human", END)
    graph.add_edge("ask_order_id", END)
    graph.add_edge("generate_order_answer", END)
    graph.add_edge("generate_refund_answer", END)
    graph.add_edge("human_confirm", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


async def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "帮我查一下订单 10001。",
        "我的订单 10002 还没发货，可以退款吗？",
        "我要退款，但是忘记订单号了。",
        "我要找人工客服。",
    ]

    for question in questions:
        print("question:", question)
        print("=" * 80)

        result = await app.ainvoke(
            create_initial_state(question),
            config={
                "recursion_limit": 20
            },
        )

        print("final_answer:")
        print(result["final_answer"])

        print("\nlogs:")
        for log in result["logs"]:
            print("-", log)

        print("\ntool_calls:")
        for tool_call in result["tool_calls"]:
            print("-", tool_call)

        print("\nsources:")
        for source in result["sources"]:
            print("-", source)

        print("=" * 120)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg32_12_ecommerce_node_edge_graph.py
```

写入：

```python
import asyncio

from app.langgraph_node_edge.demo_12_ecommerce_node_edge_graph import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这是本章最重要的综合示例。

它已经非常接近后面第 38 章项目二。

它包含：

```plain
普通问题
转人工
缺少订单号
订单查询
退款规则检索
风险评估
最终回答
错误兜底
```

你会发现，复杂业务不再是一个大函数。

而是拆成多个 Node。

每个 Node 只负责一个步骤。

流程用 Edge 明确连起来。

这就是 LangGraph 的价值。

---

# 二十六、22｜如何观察 Node 执行过程
可以用 stream：

```python
async for chunk in app.astream(
    create_initial_state("我的订单 10002 还没发货，可以退款吗？"),
    stream_mode="updates",
):
    print(chunk)
```

`stream_mode="updates"` 适合观察每个节点的输出更新；`stream_mode="values"` 适合观察每一步之后的完整 State。LangGraph Streaming 文档也说明，Graph 可以通过不同 stream mode 暴露节点更新、完整状态、LLM token、自定义事件等执行过程。

---

## 【重点内容】
做 LangGraph 调试，一定要学会 stream。

不要只看最终回答。

你要看：

```plain
哪个节点执行了
节点返回了什么
State 怎么变化
条件边怎么路由
有没有进入错误节点
```

这些都能通过 stream 观察。

---

# 二十七、23｜Node 调试建议
调试 Node 时建议看：

```plain
1. 输入 State 是否完整
2. Node 返回字段是否正确
3. 返回字段是否存在于 State schema 中
4. list 字段是否配置 reducer
5. 异常是否被捕获
6. logs 是否记录关键步骤
7. 下一个 Edge 是否符合预期
```

---

# 二十八、24｜Edge 调试建议
调试 Edge 时建议看：

```plain
1. 条件路由函数返回值是什么
2. 返回值是否在 path_map 中
3. 是否遗漏 END
4. 是否存在循环退出条件
5. 是否从同一个节点同时配置静态边和条件边
6. Command 和 add_edge 是否混用
7. 可视化图是否符合预期
```

---

# 二十九、25｜Node 与 Edge 和项目一的关系
第 19 章项目一里很多逻辑原来写在 ChatService 里。

引入 LangGraph 后，可以拆成：

```plain
ChatService
 ↓
GraphService
 ↓
classify_intent_node
extract_order_id_node
query_order_node
retrieve_policy_node
generate_answer_node
```

Router 不关心图内部。

ChatService 不关心每个节点细节。

GraphService 负责执行图。

Node 负责具体步骤。

---

# 三十、26｜Node 与 Edge 和项目二的关系
第 38 章项目二会做：

```plain
LangGraph 电商客服 Agent
```

它的基础就是本章这个综合图。

后面会逐步替换：

```plain
mock_query_order
 -> 真实 ToolExecutor / query_order_tool

mock_retrieve_policy
 -> 真实 RAG Retriever / RAGService

规则意图识别
 -> Structured Output 意图识别

模板回答
 -> ChatModel 生成最终回答

普通日志
 -> trace_id + PostgreSQL / observability
```

---

# 三十一、27｜常见错误一：Node 职责太大
错误：

```plain
一个 node 里做完整客服流程。
```

正确：

```plain
一个 node 只做一个明确步骤。
```

---

# 三十二、28｜常见错误二：Node 直接修改 State
错误：

```python
def node(state):
    state["intent"] = "refund"
    return state
```

正确：

```python
def node(state):
    return {
        "intent": "refund"
    }
```

---

# 三十三、29｜常见错误三：条件路由函数里做复杂业务
错误：

```plain
route 函数里调用 LLM、调用工具、查数据库。
```

正确：

```plain
Node 做业务动作。
route 函数只读 State，返回下一步。
```

---

# 三十四、30｜常见错误四：路由返回值和 path_map 不一致
错误：

```python
def route(state):
    return "refund_flow"

graph.add_conditional_edges(
    "router",
    route,
    {
        "refund": "refund_node"
    }
)
```

问题：

```plain
route 返回 refund_flow，但 path_map 里没有。
```

---

# 三十五、31｜常见错误五：循环没有退出条件
错误：

```plain
review -> generate -> review 无限循环
```

正确：

```plain
使用 retry_count / is_finished / recursion_limit 控制退出。
```

---

# 三十六、32｜常见错误六：从同一个节点混用普通 Edge 和 Conditional Edge
不推荐：

```python
graph.add_edge("classify_intent", "node_a")
graph.add_conditional_edges("classify_intent", route_func, ...)
```

这样流程容易变得难以理解。

推荐：

```plain
固定流程用 add_edge。
动态流程用 add_conditional_edges。
一个节点选择一种主要路由方式。
```

---

# 三十七、33｜常见错误七：Command 和普通 Edge 混用
错误：

```python
def router_node(state):
    return Command(goto="refund_node")

graph.add_edge("router_node", "general_node")
```

问题：

```plain
可能 refund_node 和 general_node 都运行。
```

正确：

```plain
使用 Command 的节点，不再额外配置普通后续边。
```

---

# 三十八、34｜常见错误八：Node 没有 logs
不推荐：

```plain
节点执行了，但 State 里看不到任何过程。
```

推荐：

```python
return {
    "logs": ["query_order：订单状态为已发货"]
}
```

---

# 三十九、35｜面试回答：Node 和 Edge 怎么理解
## 回答话术一：基础版
```plain
LangGraph 里的 Node 可以理解成图里的一个处理步骤，本质上是一个 Python 函数。它读取当前 State，然后返回部分状态更新。

Edge 是节点之间的连接，决定图的执行顺序。固定流程用 add_edge，动态流程用 add_conditional_edges。

比如电商客服 Agent 里，我会把流程拆成 classify_intent、extract_order_id、query_order、retrieve_policy、generate_answer 这些节点，然后用 Edge 控制它们的执行顺序和条件分支。
```

---

## 回答话术二：项目版
```plain
在电商客服项目里，我不会把整个 Agent 流程写成一个大函数。

我会拆成多个 Node：

classify_intent_node 负责识别用户意图；
extract_order_id_node 负责提取订单号；
query_order_node 负责调用订单工具；
retrieve_policy_node 负责调用 RAG 检索售后规则；
assess_risk_node 负责判断是否需要人工确认；
generate_answer_node 负责生成最终回复。

Edge 负责控制流程，比如缺订单号就走 ask_order_id，退款问题就走 retrieve_policy，只查订单就直接 generate_order_answer。
```

---

## 回答话术三：工程版
```plain
工程上，Node 和 Edge 的价值是把复杂 Agent 流程显式化。

Node 单一职责，方便单测、日志、异常处理和复用。

Edge 显式表达执行顺序和条件分支，避免大量 if/else 散落在业务代码里。

再配合 State、Reducer、Checkpoint 和 Streaming，就可以做到流程可控、状态可恢复、执行过程可观察。
```

---

# 四十、36｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Node | 第 30 章核心概念 |
| Edge | 第 30 章核心概念 |
| State | 第 31 章 State 设计 |
| 同步 Node | 普通业务处理 |
| 异步 Node | FastAPI / LLM / Tool |
| LLM Node | 第 22 章 Model |
| Tool Node | 第 25 章 Tool |
| RAG Node | 第 27 章 RAG |
| Conditional Edge | 第 30 章条件路由 |
| Loop Edge | Agent 反思 / 工具循环 |
| Command | 第 30 章 Command |
| Error Node | 第 10 章异常处理 |
| logs / errors | 第 10 章日志体系 |
| Ecommerce Graph | 第 38 章项目二基础 |


---

# 四十一、37｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Node 是图里的处理步骤
2. 理解 Edge 是节点之间的执行流
3. 创建 langgraph_node_edge 目录
4. 定义 EcommerceNodeEdgeState
5. 准备 mock query_order 和 mock RAG service
6. 写出最小 Node + Edge
7. 写出顺序 Edge
8. 写出条件 Edge
9. 理解 Node 设计原则
10. 写出异步 Node
11. 写出读取 RunnableConfig 的 Node
12. 写出 LLM Node
13. 写出 Tool Node
14. 写出 RAG Node
15. 写出异常处理 Node
16. 写出循环 Edge
17. 写出 Command Node
18. 理解 Edge 设计原则
19. 拆分电商客服 Agent Node
20. 完成电商客服 Node + Edge 综合图
21. 理解如何观察 Node 执行过程
22. 理解 Node 调试方法
23. 理解 Edge 调试方法
24. 理解 Node 与 Edge 和项目一的关系
25. 理解 Node 与 Edge 和项目二的关系
26. 总结常见错误
27. 准备面试回答话术
```

---

# 四十二、38｜课后任务一：跑通最小 Node + Edge
要求：

```plain
1. 运行 scripts/test_lg32_01_simple_node_edge.py
2. 找到 answer_node
3. 找到 START -> answer -> END
4. 说明 Node 返回的 dict 如何更新 State
```

---

# 四十三、39｜课后任务二：跑通顺序 Edge
要求：

```plain
1. 运行 scripts/test_lg32_02_sequence_edges.py
2. 查看 classify_intent、extract_order_id、answer 的执行顺序
3. 说明普通 add_edge 适合什么场景
```

---

# 四十四、40｜课后任务三：跑通条件 Edge
要求：

```plain
1. 运行 scripts/test_lg32_03_conditional_edges.py
2. 输入普通问题、订单问题、退款问题
3. 观察路由到不同节点
4. 说明 route_by_intent 的作用
```

---

# 四十五、41｜课后任务四：跑通异步 Node
要求：

```plain
1. 运行 scripts/test_lg32_04_async_node.py
2. 查看 async node 写法
3. 说明为什么真实项目里 Node 经常写成 async
```

---

# 四十六、42｜课后任务五：跑通 Tool Node
要求：

```plain
1. 运行 scripts/test_lg32_07_tool_node.py
2. 查看 query_order_tool_node 输入什么
3. 查看它输出 order_info、tool_calls、logs
4. 思考如何替换成第 25 章真实 LangChain Tool
```

---

# 四十七、43｜课后任务六：跑通 RAG Node
要求：

```plain
1. 运行 scripts/test_lg32_08_rag_node.py
2. 查看 retrieve_policy_rag_node 输入什么
3. 查看它输出 policy_answer 和 sources
4. 思考如何替换成第 27 章真实 RAGService
```

---

# 四十八、44｜课后任务七：跑通 Error Node
要求：

```plain
1. 运行 scripts/test_lg32_09_error_node.py
2. 输入触发异常的问题
3. 查看 errors 是否被写入 State
4. 查看是否进入 error_handler_node
```

---

# 四十九、45｜课后任务八：跑通 Loop Edge
要求：

```plain
1. 运行 scripts/test_lg32_10_loop_edge.py
2. 查看 generate_draft 和 review 的循环
3. 修改 retry_count 条件
4. 观察如何避免无限循环
```

---

# 五十、46｜课后任务九：跑通 Command Node
要求：

```plain
1. 运行 scripts/test_lg32_11_command_node.py
2. 查看 router_node 如何同时 update 和 goto
3. 说明 Command 和 conditional edge 的区别
4. 不要给 router_node 再添加普通后续 Edge
```

---

# 五十一、47｜课后任务十：跑通电商客服综合图
要求：

```plain
1. 运行 scripts/test_lg32_12_ecommerce_node_edge_graph.py
2. 输入“我的订单 10002 还没发货，可以退款吗？”
3. 查看经过哪些 logs
4. 查看是否调用 query_order
5. 查看是否检索售后规则 sources
6. 画出这条请求的执行路径
```

---

# 五十二、48｜课后任务十一：扩展物流分支
要求新增：

```plain
query_logistics_node
generate_logistics_answer_node
```

当 intent=logistics 时：

```plain
extract_order_id
 ↓
query_order
 ↓
如果有 tracking_no
 ↓
query_logistics
 ↓
generate_logistics_answer
```

---

# 五十三、49｜课后任务十二：扩展人工确认分支
要求：

```plain
1. 在 assess_risk_node 中设置 need_human_confirm=True
2. route_after_assess_risk 路由到 human_confirm
3. human_confirm_node 返回待确认提示
4. 暂时不用 interrupt，第 35 章再实现真正暂停恢复
```

---

# 五十四、50｜本章总结
## 【重点内容】
好了，到这里，第 32 章我们就讲完了。

这一章我们专门讲了 LangGraph 的 Node 和 Edge。

大家一定要记住：

```plain
Node 是处理步骤。
Edge 是执行路线。
State 是它们之间共享的上下文。
```

Node 的核心写法是：

```python
def some_node(state):
    return {
        "field": "new value"
    }
```

Edge 的核心写法是：

```python
graph.add_edge("node_a", "node_b")
```

动态分支用：

```python
graph.add_conditional_edges(...)
```

这一章我们还讲了不同类型的 Node：

```plain
同步 Node
异步 Node
读取 config 的 Node
LLM Node
Tool Node
RAG Node
异常处理 Node
Command Node
```

也讲了不同类型的 Edge：

```plain
普通顺序 Edge
条件 Edge
循环 Edge
Command 路由
```

最后，我们完成了一个电商客服 Agent 的 Node + Edge 综合图。

它已经具备：

```plain
意图识别
订单号提取
订单查询
售后规则检索
风险评估
转人工
错误兜底
最终回答
```

这就是第 38 章项目二的基础。

---
