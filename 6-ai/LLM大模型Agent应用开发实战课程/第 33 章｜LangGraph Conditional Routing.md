---

# 一、本章定位
前面我们已经完成了 LangGraph 阶段的基础：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
```

第 32 章我们已经知道：

```plain
Node：处理步骤
Edge：节点之间的执行路线
```

这一章专门深入：

# Conditional Routing
也就是：

```plain
条件路由
```

一句话理解：

**根据当前 State 的内容，决定下一步去哪个节点。**

比如电商客服 Agent：

```plain
用户问普通问题
  -> 走普通回答

用户问订单状态
  -> 走订单查询

用户问退款规则
  -> 先查订单，再查售后规则

用户没提供订单号
  -> 追问订单号

订单查询失败
  -> 进入错误兜底

退款金额过高
  -> 进入人工确认
```

这些都是条件路由。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Conditional Routing 是什么
2. 为什么复杂 Agent 必须有条件路由
3. add_conditional_edges 怎么用
4. 路由函数怎么写
5. Literal 返回类型怎么写
6. path_map 怎么设计
7. 如何路由到 END
8. 如何根据 intent 路由
9. 如何根据订单号是否存在路由
10. 如何根据工具结果路由
11. 如何根据 RAG 是否命中路由
12. 如何根据风险等级路由
13. 如何触发 Human Confirm
14. 如何设计 error_handler 路由
15. 如何做循环重试路由
16. 如何避免无限循环
17. Command 和 conditional edge 的区别
18. 路由函数为什么不要做业务动作
19. 电商客服 Agent 完整路由怎么设计
20. 面试中如何讲 Conditional Routing
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
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
```

LangGraph 的 Graph API 文档也提到，如果流程需要运行时根据 State 变化决定分支，可以用 `add_conditional_edges`；如果想在同一个函数里同时更新 State 并跳转，可以用 `Command`。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langgraph_routing/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── mock_services.py
│   │   ├── demo_01_basic_conditional_routing.py
│   │   ├── demo_02_route_by_intent.py
│   │   ├── demo_03_route_missing_order_id.py
│   │   ├── demo_04_route_tool_result.py
│   │   ├── demo_05_route_rag_result.py
│   │   ├── demo_06_route_risk_human_confirm.py
│   │   ├── demo_07_route_to_end.py
│   │   ├── demo_08_loop_retry_routing.py
│   │   ├── demo_09_command_vs_conditional.py
│   │   └── demo_10_ecommerce_full_routing_graph.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg33_01_basic_conditional_routing.py
│   ├── test_lg33_02_route_by_intent.py
│   ├── test_lg33_03_route_missing_order_id.py
│   ├── test_lg33_04_route_tool_result.py
│   ├── test_lg33_05_route_rag_result.py
│   ├── test_lg33_06_route_risk_human_confirm.py
│   ├── test_lg33_07_route_to_end.py
│   ├── test_lg33_08_loop_retry_routing.py
│   ├── test_lg33_09_command_vs_conditional.py
│   └── test_lg33_10_ecommerce_full_routing_graph.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 33 章。

这一章我们专门讲 LangGraph 条件路由。

前面我们已经知道，一个图由 State、Node、Edge 组成。

但是实际业务流程很少是一条直线。

比如用户问：

```plain
我的订单 10002 还没发货，可以退款吗？
```

这个请求可能要走：

```plain
识别意图
 ↓
提取订单号
 ↓
查询订单
 ↓
判断订单状态
 ↓
检索退款规则
 ↓
判断风险等级
 ↓
生成回答
```

但如果用户没有提供订单号，就不能查订单。

应该走：

```plain
追问订单号
```

如果订单查询失败，就应该走：

```plain
错误兜底
```

如果退款金额很大，就应该走：

```plain
人工确认
```

这些分支都不是固定的。

它们要根据 State 里的字段动态判断。

这就是 Conditional Routing。

---

# 六、02｜Conditional Routing 一句话解释
## 【实操】
```plain
Conditional Routing
=
根据 State 决定下一步走哪个节点
```

示例：

```plain
intent=general
  -> general_answer

intent=query_order
  -> extract_order_id

intent=refund
  -> extract_order_id + query_order + retrieve_policy

order_id=None
  -> ask_order_id

need_human_confirm=True
  -> human_confirm
```

---

## 【重点内容】
大家可以这样理解：

Node 是干活的。

Routing function 是判断下一步怎么走的。

Edge 是把判断结果映射到具体节点的。

比如：

```python
def route_by_intent(state):
    if state["intent"] == "refund":
        return "refund"
    return "general"
```

这个函数不查数据库，不调用模型，不修改 State。

它只看 State，然后返回一个路由 key。

---

# 七、03｜add_conditional_edges 基本语法
## 【实操】
```python
graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "general": "general_answer",
        "order": "query_order",
        "refund": "refund_flow",
    },
)
```

解释：

```plain
classify_intent：
前置节点

route_by_intent：
路由函数

path_map：
路由 key 到节点名的映射
```

---

## 【重点内容】
`add_conditional_edges` 的三个关键参数。

第一个是从哪个节点开始判断。

第二个是判断函数。

第三个是路由映射。

也就是说：

```plain
classify_intent 节点执行完
 ↓
调用 route_by_intent(state)
 ↓
得到 general / order / refund
 ↓
根据 path_map 找到下一个节点
```

这就是条件路由的基本执行逻辑。

---

# 八、04｜为什么要写 Literal 返回类型
推荐写法：

```python
def route_by_intent(
    state: AgentState,
) -> Literal["general", "order", "refund"]:
    ...
```

原因：

```plain
1. 类型更清晰
2. 编辑器能提示
3. 图可视化更准确
4. 避免返回未知路由 key
```

LangGraph 官方参考文档说明，如果没有类型提示或 `path_map`，图可视化可能会假设条件边能连接到图里的任意节点。

---

## 【重点内容】
这个细节非常重要。

很多同学刚开始写：

```python
def route_by_intent(state):
    return state["intent"]
```

代码能跑，但图可视化可能会很乱。

而且后续维护的人不知道这个函数到底可能返回什么。

所以课程里统一要求：

```plain
路由函数必须写 Literal 返回类型。
条件边必须写 path_map。
```

这样最稳。

---

# 九、05｜创建目录
执行：

```bash
mkdir -p app/langgraph_routing

touch app/langgraph_routing/__init__.py
touch app/langgraph_routing/schemas.py
touch app/langgraph_routing/mock_services.py
touch app/langgraph_routing/demo_01_basic_conditional_routing.py
touch app/langgraph_routing/demo_02_route_by_intent.py
touch app/langgraph_routing/demo_03_route_missing_order_id.py
touch app/langgraph_routing/demo_04_route_tool_result.py
touch app/langgraph_routing/demo_05_route_rag_result.py
touch app/langgraph_routing/demo_06_route_risk_human_confirm.py
touch app/langgraph_routing/demo_07_route_to_end.py
touch app/langgraph_routing/demo_08_loop_retry_routing.py
touch app/langgraph_routing/demo_09_command_vs_conditional.py
touch app/langgraph_routing/demo_10_ecommerce_full_routing_graph.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_routing

New-Item app\langgraph_routing\__init__.py
New-Item app\langgraph_routing\schemas.py
New-Item app\langgraph_routing\mock_services.py
New-Item app\langgraph_routing\demo_01_basic_conditional_routing.py
New-Item app\langgraph_routing\demo_02_route_by_intent.py
New-Item app\langgraph_routing\demo_03_route_missing_order_id.py
New-Item app\langgraph_routing\demo_04_route_tool_result.py
New-Item app\langgraph_routing\demo_05_route_rag_result.py
New-Item app\langgraph_routing\demo_06_route_risk_human_confirm.py
New-Item app\langgraph_routing\demo_07_route_to_end.py
New-Item app\langgraph_routing\demo_08_loop_retry_routing.py
New-Item app\langgraph_routing\demo_09_command_vs_conditional.py
New-Item app\langgraph_routing\demo_10_ecommerce_full_routing_graph.py
```

---

# 十、06｜准备公共 State
打开：

```plain
app/langgraph_routing/schemas.py
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


class RoutingToolCall(TypedDict, total=False):
    name: str
    args: dict
    success: bool
    result_preview: str


class RoutingState(TypedDict):
    user_question: str

    intent: Literal[
        "general",
        "query_order",
        "logistics",
        "refund",
        "after_sales",
        "human_service",
        "unknown",
    ]

    order_id: str | None
    order_info: OrderInfo | None

    need_policy: bool
    policy_query: str | None
    policy_answer: str | None
    sources: Annotated[list[SourceInfo], operator.add]

    tool_success: bool
    tool_calls: Annotated[list[RoutingToolCall], operator.add]

    rag_hit: bool
    need_human_confirm: bool
    risk_level: Literal["low", "medium", "high"]
    pending_action: str | None

    retry_count: int
    max_retry: int

    final_answer: str
    is_finished: bool

    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
```

---

## 【重点内容】
这个 State 是本章所有示例的基础。

它有几类字段。

第一类是用户输入和意图：

```plain
user_question
intent
```

第二类是订单相关：

```plain
order_id
order_info
```

第三类是 RAG 相关：

```plain
need_policy
policy_query
policy_answer
sources
rag_hit
```

第四类是工具和错误：

```plain
tool_success
tool_calls
errors
```

第五类是人工确认：

```plain
need_human_confirm
risk_level
pending_action
```

第六类是循环控制：

```plain
retry_count
max_retry
```

这些字段都会参与路由判断。

---

# 十一、07｜准备 Mock Service
打开：

```plain
app/langgraph_routing/mock_services.py
```

写入：

```python
import asyncio

from app.langgraph_routing.schemas import RoutingState


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


async def mock_query_order(order_id: str | None) -> dict:
    await asyncio.sleep(0.05)

    if not order_id:
        return {
            "success": False,
            "error": "missing_order_id",
            "data": None,
        }

    order = MOCK_ORDERS.get(order_id)

    if not order:
        return {
            "success": False,
            "error": "order_not_found",
            "data": {
                "order_id": order_id,
                "status": "not_found",
                "status_text": "未查询到订单",
            },
        }

    return {
        "success": True,
        "error": None,
        "data": order,
    }


async def mock_search_policy(query: str | None) -> dict:
    await asyncio.sleep(0.05)

    if not query:
        return {
            "hit": False,
            "answer": "根据当前知识库无法确认。",
            "sources": [],
        }

    if "未发货" in query or "待发货" in query:
        return {
            "hit": True,
            "answer": "订单未发货时，用户可以申请取消订单并退款。",
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

    if "已发货" in query or "已签收" in query:
        return {
            "hit": True,
            "answer": "订单已发货后，需要用户收到商品后再发起退货退款申请。",
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
        "hit": False,
        "answer": "根据当前知识库无法确认。",
        "sources": [],
    }


def create_initial_state(
    user_question: str,
) -> RoutingState:
    return {
        "user_question": user_question,

        "intent": "unknown",

        "order_id": None,
        "order_info": None,

        "need_policy": False,
        "policy_query": None,
        "policy_answer": None,
        "sources": [],

        "tool_success": True,
        "tool_calls": [],

        "rag_hit": False,
        "need_human_confirm": False,
        "risk_level": "low",
        "pending_action": None,

        "retry_count": 0,
        "max_retry": 2,

        "final_answer": "",
        "is_finished": False,

        "logs": [],
        "errors": [],
    }
```

---

# 十二、08｜示例一：最小条件路由
打开：

```plain
app/langgraph_routing/demo_01_basic_conditional_routing.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class BasicRouteState(TypedDict):
    user_question: str
    answer_type: str
    final_answer: str


def classify_node(state: BasicRouteState) -> dict:
    if "代码" in state["user_question"]:
        return {"answer_type": "code"}

    return {"answer_type": "text"}


def route_answer_type(
    state: BasicRouteState,
) -> Literal["text", "code"]:
    return state["answer_type"]  # type: ignore[return-value]


def text_answer_node(state: BasicRouteState) -> dict:
    return {
        "final_answer": "这是文字解释回答。"
    }


def code_answer_node(state: BasicRouteState) -> dict:
    return {
        "final_answer": "这是代码示例回答。"
    }


def build_graph():
    graph = StateGraph(BasicRouteState)

    graph.add_node("classify", classify_node)
    graph.add_node("text_answer", text_answer_node)
    graph.add_node("code_answer", code_answer_node)

    graph.add_edge(START, "classify")

    graph.add_conditional_edges(
        "classify",
        route_answer_type,
        {
            "text": "text_answer",
            "code": "code_answer",
        },
    )

    graph.add_edge("text_answer", END)
    graph.add_edge("code_answer", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "解释一下 LangGraph。",
        "给我一段 LangGraph 代码。",
    ]

    for question in questions:
        result = app.invoke({
            "user_question": question,
            "answer_type": "",
            "final_answer": "",
        })

        print("question:", question)
        print("answer_type:", result["answer_type"])
        print("final_answer:", result["final_answer"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_01_basic_conditional_routing.py
```

写入：

```python
from app.langgraph_routing.demo_01_basic_conditional_routing import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg33_01_basic_conditional_routing.py
```

---

## 【重点内容】
这是最小条件路由。

先由 classify 节点写入：

```plain
answer_type
```

然后 route_answer_type 根据 answer_type 决定走：

```plain
text_answer
```

还是：

```plain
code_answer
```

这就是条件路由最小闭环。

---

# 十三、09｜示例二：根据 intent 路由
打开：

```plain
app/langgraph_routing/demo_02_route_by_intent.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import create_initial_state
from app.langgraph_routing.schemas import RoutingState


def classify_intent_node(state: RoutingState) -> dict:
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
        "logs": [f"classify_intent：识别到 intent={intent}"],
    }


def route_by_intent(
    state: RoutingState,
) -> Literal["general", "human", "need_order"]:
    intent = state["intent"]

    if intent == "general":
        return "general"

    if intent == "human_service":
        return "human"

    return "need_order"


def general_answer_node(state: RoutingState) -> dict:
    return {
        "final_answer": "这是普通问题，可以走普通 Chat。",
        "is_finished": True,
        "logs": ["general_answer：完成普通回答"],
    }


def transfer_human_node(state: RoutingState) -> dict:
    return {
        "final_answer": "我已经为您转接人工客服，请稍等。",
        "is_finished": True,
        "logs": ["transfer_human：完成转人工"],
    }


def need_order_node(state: RoutingState) -> dict:
    return {
        "final_answer": "这个问题需要订单号，后续会进入订单号提取流程。",
        "logs": ["need_order：进入订单相关流程"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("transfer_human", transfer_human_node)
    graph.add_node("need_order", need_order_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "general_answer",
            "human": "transfer_human",
            "need_order": "need_order",
        },
    )

    graph.add_edge("general_answer", END)
    graph.add_edge("transfer_human", END)
    graph.add_edge("need_order", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "我要找人工客服。",
        "帮我查一下订单 10001。",
        "我的订单还没发货，可以退款吗？",
    ]

    for question in questions:
        result = app.invoke(create_initial_state(question))

        print("question:", question)
        print("intent:", result["intent"])
        print("final_answer:", result["final_answer"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_02_route_by_intent.py
```

写入：

```python
from app.langgraph_routing.demo_02_route_by_intent import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这里我们根据 intent 做第一层路由。

注意我的设计：

```plain
general
  -> general_answer

human_service
  -> transfer_human

其他订单相关 intent
  -> need_order
```

也就是说，退款、物流、订单查询，都先进入订单相关流程。

这就是业务路由设计。

---

# 十四、10｜示例三：缺少订单号路由
打开：

```plain
app/langgraph_routing/demo_03_route_missing_order_id.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import create_initial_state
from app.langgraph_routing.schemas import RoutingState


def extract_order_id_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


def route_after_extract_order_id(
    state: RoutingState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: RoutingState) -> dict:
    return {
        "final_answer": "请您提供订单号，我才能继续查询。",
        "is_finished": True,
        "logs": ["ask_order_id：缺少订单号，追问用户"],
    }


def query_order_entry_node(state: RoutingState) -> dict:
    return {
        "final_answer": f"已提取订单号 {state['order_id']}，下一步可以查询订单。",
        "logs": ["query_order_entry：进入订单查询流程"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order_entry", query_order_entry_node)

    graph.add_edge(START, "extract_order_id")

    graph.add_conditional_edges(
        "extract_order_id",
        route_after_extract_order_id,
        {
            "ask_order_id": "ask_order_id",
            "query_order": "query_order_entry",
        },
    )

    graph.add_edge("ask_order_id", END)
    graph.add_edge("query_order_entry", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "帮我查一下订单 10001。",
        "帮我查一下订单。",
    ]

    for question in questions:
        result = app.invoke(create_initial_state(question))

        print("question:", question)
        print("order_id:", result["order_id"])
        print("final_answer:", result["final_answer"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_03_route_missing_order_id.py
```

写入：

```python
from app.langgraph_routing.demo_03_route_missing_order_id import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子非常实用。

很多业务流程不是缺参数也继续跑。

比如查订单必须有订单号。

所以路由逻辑应该是：

```plain
order_id is None
  -> ask_order_id

order_id 存在
  -> query_order
```

这比让模型自己猜订单号安全得多。

---

# 十五、11｜示例四：根据工具结果路由
打开：

```plain
app/langgraph_routing/demo_04_route_tool_result.py
```

写入：

```python
import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import (
    create_initial_state,
    mock_query_order,
)
from app.langgraph_routing.schemas import RoutingState


def extract_order_id_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "99999" in question:
        order_id = "99999"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


async def query_order_node(state: RoutingState) -> dict:
    result = await mock_query_order(state["order_id"])

    if not result["success"]:
        return {
            "tool_success": False,
            "order_info": result.get("data"),
            "errors": [result["error"]],
            "tool_calls": [
                {
                    "name": "query_order",
                    "args": {"order_id": state["order_id"]},
                    "success": False,
                    "result_preview": result["error"],
                }
            ],
            "logs": [f"query_order：失败 {result['error']}"],
        }

    return {
        "tool_success": True,
        "order_info": result["data"],
        "tool_calls": [
            {
                "name": "query_order",
                "args": {"order_id": state["order_id"]},
                "success": True,
                "result_preview": result["data"]["status_text"],
            }
        ],
        "logs": [f"query_order：成功 {result['data']['status_text']}"],
    }


def route_after_query_order(
    state: RoutingState,
) -> Literal["success", "not_found", "error"]:
    if state["tool_success"]:
        return "success"

    if state["errors"] and "order_not_found" in state["errors"]:
        return "not_found"

    return "error"


def order_success_node(state: RoutingState) -> dict:
    return {
        "final_answer": f"您的订单状态是：{state['order_info']['status_text']}。",
        "is_finished": True,
        "logs": ["order_success：订单查询成功"],
    }


def order_not_found_node(state: RoutingState) -> dict:
    return {
        "final_answer": "没有查询到该订单，请检查订单号是否正确。",
        "is_finished": True,
        "logs": ["order_not_found：订单不存在"],
    }


def error_handler_node(state: RoutingState) -> dict:
    return {
        "final_answer": "订单查询服务暂时异常，请稍后再试。",
        "is_finished": True,
        "logs": ["error_handler：工具失败兜底"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("order_success", order_success_node)
    graph.add_node("order_not_found", order_not_found_node)
    graph.add_node("error_handler", error_handler_node)

    graph.add_edge(START, "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")

    graph.add_conditional_edges(
        "query_order",
        route_after_query_order,
        {
            "success": "order_success",
            "not_found": "order_not_found",
            "error": "error_handler",
        },
    )

    graph.add_edge("order_success", END)
    graph.add_edge("order_not_found", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


async def main():
    app = build_graph()

    for question in ["帮我查一下订单 10001。", "帮我查一下订单 99999。"]:
        result = await app.ainvoke(create_initial_state(question))

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
scripts/test_lg33_04_route_tool_result.py
```

写入：

```python
import asyncio

from app.langgraph_routing.demo_04_route_tool_result import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个例子是根据工具结果路由。

订单工具可能有三种结果：

```plain
成功
订单不存在
系统异常
```

这三种结果应该走不同节点。

不要全部丢给一个最终回答节点。

这样错误处理更清晰。

---

# 十六、12｜示例五：根据 RAG 是否命中路由
打开：

```plain
app/langgraph_routing/demo_05_route_rag_result.py
```

写入：

```python
import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import (
    create_initial_state,
    mock_search_policy,
)
from app.langgraph_routing.schemas import RoutingState


def build_policy_query_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "年假" in question:
        query = "员工年假制度"
    elif "退款" in question:
        query = "订单未发货退款规则"
    else:
        query = question

    return {
        "policy_query": query,
        "logs": [f"build_policy_query：query={query}"],
    }


async def retrieve_policy_node(state: RoutingState) -> dict:
    result = await mock_search_policy(state["policy_query"])

    return {
        "rag_hit": result["hit"],
        "policy_answer": result["answer"],
        "sources": result["sources"],
        "logs": [f"retrieve_policy：rag_hit={result['hit']}"],
    }


def route_after_rag(
    state: RoutingState,
) -> Literal["answer_with_sources", "fallback"]:
    if state["rag_hit"] and state["sources"]:
        return "answer_with_sources"

    return "fallback"


def answer_with_sources_node(state: RoutingState) -> dict:
    return {
        "final_answer": (
            f"{state['policy_answer']} 回答依据来自知识库。"
        ),
        "is_finished": True,
        "logs": ["answer_with_sources：基于知识库回答"],
    }


def fallback_node(state: RoutingState) -> dict:
    return {
        "final_answer": "根据当前知识库无法确认，建议联系人工客服。",
        "is_finished": True,
        "logs": ["fallback：知识库未命中，进入兜底"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("build_policy_query", build_policy_query_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("answer_with_sources", answer_with_sources_node)
    graph.add_node("fallback", fallback_node)

    graph.add_edge(START, "build_policy_query")
    graph.add_edge("build_policy_query", "retrieve_policy")

    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_rag,
        {
            "answer_with_sources": "answer_with_sources",
            "fallback": "fallback",
        },
    )

    graph.add_edge("answer_with_sources", END)
    graph.add_edge("fallback", END)

    return graph.compile()


async def main():
    app = build_graph()

    questions = [
        "订单未发货可以退款吗？",
        "公司下午茶制度是什么？",
    ]

    for question in questions:
        result = await app.ainvoke(create_initial_state(question))

        print("question:", question)
        print("rag_hit:", result["rag_hit"])
        print("final_answer:", result["final_answer"])
        print("sources:", result["sources"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg33_05_route_rag_result.py
```

写入：

```python
import asyncio

from app.langgraph_routing.demo_05_route_rag_result import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
RAG 未命中时，不要让模型硬编。

应该走 fallback。

路由条件可以是：

```plain
rag_hit=True 且 sources 不为空
  -> answer_with_sources

否则
  -> fallback
```

这样能明显降低知识库问答编造风险。

---

# 十七、13｜示例六：风险评估触发人工确认
打开：

```plain
app/langgraph_routing/demo_06_route_risk_human_confirm.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import create_initial_state
from app.langgraph_routing.schemas import RoutingState


def assess_risk_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "大额" in question or "1000" in question:
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "pending_action": "refund_order",
            "logs": ["assess_risk：高风险，需要人工确认"],
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,
        "logs": ["assess_risk：低风险，可自动处理"],
    }


def route_after_risk(
    state: RoutingState,
) -> Literal["human_confirm", "auto_answer"]:
    if state["need_human_confirm"]:
        return "human_confirm"

    return "auto_answer"


def human_confirm_node(state: RoutingState) -> dict:
    return {
        "final_answer": "该操作风险较高，需要人工客服确认后继续处理。",
        "is_finished": True,
        "logs": ["human_confirm：等待人工确认"],
    }


def auto_answer_node(state: RoutingState) -> dict:
    return {
        "final_answer": "该请求风险较低，可以继续自动处理。",
        "is_finished": True,
        "logs": ["auto_answer：自动处理"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("human_confirm", human_confirm_node)
    graph.add_node("auto_answer", auto_answer_node)

    graph.add_edge(START, "assess_risk")

    graph.add_conditional_edges(
        "assess_risk",
        route_after_risk,
        {
            "human_confirm": "human_confirm",
            "auto_answer": "auto_answer",
        },
    )

    graph.add_edge("human_confirm", END)
    graph.add_edge("auto_answer", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "我要退款。",
        "我要申请大额退款 1000 元。",
    ]

    for question in questions:
        result = app.invoke(create_initial_state(question))

        print("question:", question)
        print("risk_level:", result["risk_level"])
        print("need_human_confirm:", result["need_human_confirm"])
        print("final_answer:", result["final_answer"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_06_route_risk_human_confirm.py
```

写入：

```python
from app.langgraph_routing.demo_06_route_risk_human_confirm import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个示例是 Human-in-the-loop 的前置设计。

现在我们还没有真正 interrupt。

但已经通过 State 和条件路由实现了：

```plain
need_human_confirm=True
  -> human_confirm
```

第 35 章会在这个节点真正实现暂停、等待人工确认、恢复执行。

---

# 十八、14｜示例七：路由到 END
有时候某个条件下不需要继续执行任何节点，可以直接结束。

打开：

```plain
app/langgraph_routing/demo_07_route_to_end.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import create_initial_state
from app.langgraph_routing.schemas import RoutingState


def check_finished_node(state: RoutingState) -> dict:
    if "不用处理" in state["user_question"]:
        return {
            "final_answer": "好的，本次不做处理。",
            "is_finished": True,
            "logs": ["check_finished：用户表示不用处理"],
        }

    return {
        "is_finished": False,
        "logs": ["check_finished：需要继续处理"],
    }


def route_after_check_finished(
    state: RoutingState,
) -> Literal["continue", "end"]:
    if state["is_finished"]:
        return "end"

    return "continue"


def continue_node(state: RoutingState) -> dict:
    return {
        "final_answer": "继续进入后续处理流程。",
        "is_finished": True,
        "logs": ["continue_node：继续处理完成"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("check_finished", check_finished_node)
    graph.add_node("continue_node", continue_node)

    graph.add_edge(START, "check_finished")

    graph.add_conditional_edges(
        "check_finished",
        route_after_check_finished,
        {
            "continue": "continue_node",
            "end": END,
        },
    )

    graph.add_edge("continue_node", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "不用处理了。",
        "帮我继续处理订单。",
    ]

    for question in questions:
        result = app.invoke(create_initial_state(question))

        print("question:", question)
        print("final_answer:", result["final_answer"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_07_route_to_end.py
```

写入：

```python
from app.langgraph_routing.demo_07_route_to_end import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
路由到 END 很常见。

比如：

```plain
已经完成
无需继续
用户取消
超过最大重试次数
命中兜底
```

都可以直接结束。

课程里建议不要直接在路由函数里返回 `END` 常量。

更清晰的写法是返回：

```plain
"end"
```

然后在 path_map 里映射到：

```python
"end": END
```

可读性更好。

---

# 十九、15｜示例八：循环重试路由
打开：

```plain
app/langgraph_routing/demo_08_loop_retry_routing.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import create_initial_state
from app.langgraph_routing.schemas import RoutingState


def call_unstable_tool_node(state: RoutingState) -> dict:
    retry_count = state["retry_count"]

    if retry_count < 2:
        return {
            "tool_success": False,
            "retry_count": retry_count + 1,
            "errors": [f"第 {retry_count + 1} 次工具调用失败"],
            "logs": [f"call_unstable_tool：失败 retry_count={retry_count + 1}"],
        }

    return {
        "tool_success": True,
        "logs": ["call_unstable_tool：工具调用成功"],
    }


def route_after_unstable_tool(
    state: RoutingState,
) -> Literal["retry", "success", "fallback"]:
    if state["tool_success"]:
        return "success"

    if state["retry_count"] < state["max_retry"]:
        return "retry"

    return "fallback"


def success_node(state: RoutingState) -> dict:
    return {
        "final_answer": "工具调用成功，已完成处理。",
        "is_finished": True,
        "logs": ["success：处理完成"],
    }


def fallback_node(state: RoutingState) -> dict:
    return {
        "final_answer": "工具多次调用失败，请稍后再试或联系人工客服。",
        "is_finished": True,
        "logs": ["fallback：超过最大重试次数"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("call_unstable_tool", call_unstable_tool_node)
    graph.add_node("success", success_node)
    graph.add_node("fallback", fallback_node)

    graph.add_edge(START, "call_unstable_tool")

    graph.add_conditional_edges(
        "call_unstable_tool",
        route_after_unstable_tool,
        {
            "retry": "call_unstable_tool",
            "success": "success",
            "fallback": "fallback",
        },
    )

    graph.add_edge("success", END)
    graph.add_edge("fallback", END)

    return graph.compile()


def main():
    app = build_graph()

    state = create_initial_state("测试不稳定工具。")
    state["max_retry"] = 3

    result = app.invoke(
        state,
        config={
            "recursion_limit": 10
        },
    )

    print("final_answer:", result["final_answer"])
    print("retry_count:", result["retry_count"])
    print("errors:")
    for error in result["errors"]:
        print("-", error)

    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg33_08_loop_retry_routing.py
```

写入：

```python
from app.langgraph_routing.demo_08_loop_retry_routing import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这是循环重试路由。

工具失败后不是直接结束。

而是：

```plain
失败
 ↓
判断 retry_count 是否小于 max_retry
 ↓
如果可以重试，回到工具节点
 ↓
如果超过次数，进入 fallback
```

循环一定要有退出条件。

LangGraph 文档中也说明，图循环通常要通过条件边路由到结束节点，并且可以通过 `recursion_limit` 限制最大执行步数，避免无限循环。

---

# 二十、16｜示例九：Command vs Conditional Edge
打开：

```plain
app/langgraph_routing/demo_09_command_vs_conditional.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class CommandDemoState(TypedDict):
    user_question: str
    intent: str
    final_answer: str


def command_router_node(
    state: CommandDemoState,
) -> Command[Literal["general_node", "refund_node"]]:
    question = state["user_question"]

    if "退款" in question:
        return Command(
            update={"intent": "refund"},
            goto="refund_node",
        )

    return Command(
        update={"intent": "general"},
        goto="general_node",
    )


def general_node(state: CommandDemoState) -> dict:
    return {
        "final_answer": "Command 路由到了普通回答节点。"
    }


def refund_node(state: CommandDemoState) -> dict:
    return {
        "final_answer": "Command 路由到了退款节点。"
    }


def build_graph():
    graph = StateGraph(CommandDemoState)

    graph.add_node("router", command_router_node)
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
            "intent": "",
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
scripts/test_lg33_09_command_vs_conditional.py
```

写入：

```python
from app.langgraph_routing.demo_09_command_vs_conditional import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
Command 和 conditional edge 都能做路由。

区别是：

```plain
conditional edge：
节点更新 State，路由函数决定下一步。

Command：
一个节点同时更新 State 并指定下一步。
```

什么时候用 conditional edge？

```plain
路由逻辑独立、清晰、需要复用时。
```

什么时候用 Command？

```plain
节点天然知道下一步，并且需要同时更新状态时。
```

但是企业项目里，我建议初学阶段优先使用 conditional edge。

因为流程更清晰。

---

# 二十一、17｜路由函数设计原则
## 原则一：路由函数只读 State，不做业务动作
不推荐：

```python
def route(state):
    result = call_llm()
    return result
```

推荐：

```python
def route(state):
    if state["intent"] == "refund":
        return "refund"
    return "general"
```

---

## 原则二：返回值必须稳定
不要返回不可控字符串。

推荐用：

```python
Literal["general", "refund", "error"]
```

---

## 原则三：路由 key 和 path_map 要一致
```python
{
    "general": "general_answer",
    "refund": "refund_flow",
    "error": "error_handler",
}
```

route 就只能返回这三个 key。

---

## 原则四：复杂判断拆成前置 Node
如果路由逻辑太复杂，先写一个 Node 计算字段：

```plain
assess_risk_node 写入 risk_level
route_after_risk 只判断 risk_level
```

---

# 二十二、18｜综合示例：电商客服完整条件路由
打开：

```plain
app/langgraph_routing/demo_10_ecommerce_full_routing_graph.py
```

写入：

```python
import asyncio
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_routing.mock_services import (
    create_initial_state,
    mock_query_order,
    mock_search_policy,
)
from app.langgraph_routing.schemas import RoutingState


def classify_intent_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "人工" in question:
        intent = "human_service"
    elif "退款" in question or "退货" in question:
        intent = "refund"
    elif "售后" in question:
        intent = "after_sales"
    elif "物流" in question:
        intent = "logistics"
    elif "订单" in question:
        intent = "query_order"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：intent={intent}"],
    }


def route_by_intent(
    state: RoutingState,
) -> Literal["general", "human", "policy_only", "need_order"]:
    intent = state["intent"]

    if intent == "general":
        return "general"

    if intent == "human_service":
        return "human"

    if intent == "after_sales":
        return "policy_only"

    return "need_order"


def general_answer_node(state: RoutingState) -> dict:
    return {
        "final_answer": "这是普通问题，可以走普通 ChatModel。",
        "is_finished": True,
        "logs": ["general_answer：普通回答完成"],
    }


def transfer_human_node(state: RoutingState) -> dict:
    return {
        "final_answer": "我已经为您转接人工客服，请稍等。",
        "is_finished": True,
        "tool_calls": [
            {
                "name": "transfer_human",
                "args": {"reason": state["user_question"]},
                "success": True,
                "result_preview": "已创建人工客服工单",
            }
        ],
        "logs": ["transfer_human：已转人工"],
    }


def build_policy_query_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if state["intent"] == "after_sales":
        query = question
    elif state["order_info"] and state["order_info"].get("status") == "paid":
        query = "订单未发货退款规则"
    elif state["order_info"] and state["order_info"].get("status") in ["shipped", "delivered"]:
        query = "订单已发货退货退款规则"
    else:
        query = "售后规则"

    return {
        "policy_query": query,
        "logs": [f"build_policy_query：policy_query={query}"],
    }


async def retrieve_policy_node(state: RoutingState) -> dict:
    result = await mock_search_policy(state["policy_query"])

    return {
        "rag_hit": result["hit"],
        "policy_answer": result["answer"],
        "sources": result["sources"],
        "logs": [f"retrieve_policy：rag_hit={result['hit']}"],
    }


def route_after_policy_only(
    state: RoutingState,
) -> Literal["answer_policy", "policy_fallback"]:
    if state["rag_hit"] and state["sources"]:
        return "answer_policy"

    return "policy_fallback"


def answer_policy_node(state: RoutingState) -> dict:
    return {
        "final_answer": f"{state['policy_answer']} 回答依据来自知识库。",
        "is_finished": True,
        "logs": ["answer_policy：知识库回答完成"],
    }


def policy_fallback_node(state: RoutingState) -> dict:
    return {
        "final_answer": "根据当前知识库无法确认，建议联系人工客服。",
        "is_finished": True,
        "logs": ["policy_fallback：知识库未命中"],
    }


def extract_order_id_node(state: RoutingState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    elif "10003" in question:
        order_id = "10003"
    elif "99999" in question:
        order_id = "99999"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


def route_after_extract_order_id(
    state: RoutingState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: RoutingState) -> dict:
    return {
        "final_answer": "请您提供订单号，我才能继续查询订单状态。",
        "is_finished": True,
        "logs": ["ask_order_id：缺少订单号"],
    }


async def query_order_node(state: RoutingState) -> dict:
    result = await mock_query_order(state["order_id"])

    if not result["success"]:
        return {
            "tool_success": False,
            "order_info": result.get("data"),
            "errors": [result["error"]],
            "tool_calls": [
                {
                    "name": "query_order",
                    "args": {"order_id": state["order_id"]},
                    "success": False,
                    "result_preview": result["error"],
                }
            ],
            "logs": [f"query_order：失败 {result['error']}"],
        }

    return {
        "tool_success": True,
        "order_info": result["data"],
        "tool_calls": [
            {
                "name": "query_order",
                "args": {"order_id": state["order_id"]},
                "success": True,
                "result_preview": result["data"]["status_text"],
            }
        ],
        "logs": [f"query_order：成功 {result['data']['status_text']}"],
    }


def route_after_query_order(
    state: RoutingState,
) -> Literal["order_not_found", "error", "need_policy", "answer_order"]:
    if not state["tool_success"]:
        if state["errors"] and "order_not_found" in state["errors"]:
            return "order_not_found"

        return "error"

    if state["intent"] == "refund":
        return "need_policy"

    return "answer_order"


def order_not_found_node(state: RoutingState) -> dict:
    return {
        "final_answer": "没有查询到该订单，请检查订单号是否正确。",
        "is_finished": True,
        "logs": ["order_not_found：订单不存在"],
    }


def answer_order_node(state: RoutingState) -> dict:
    order_info = state["order_info"]

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
        "logs": ["answer_order：订单回答完成"],
    }


def route_after_refund_policy(
    state: RoutingState,
) -> Literal["assess_risk", "policy_fallback"]:
    if state["rag_hit"] and state["sources"]:
        return "assess_risk"

    return "policy_fallback"


def assess_risk_node(state: RoutingState) -> dict:
    order_info = state["order_info"]

    if order_info and order_info.get("status") == "delivered":
        return {
            "risk_level": "medium",
            "need_human_confirm": False,
            "pending_action": None,
            "logs": ["assess_risk：已签收订单，建议按退货退款流程处理"],
        }

    if "大额" in state["user_question"]:
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "pending_action": "refund_order",
            "logs": ["assess_risk：大额退款，需要人工确认"],
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,
        "logs": ["assess_risk：低风险"],
    }


def route_after_risk(
    state: RoutingState,
) -> Literal["human_confirm", "answer_refund"]:
    if state["need_human_confirm"]:
        return "human_confirm"

    return "answer_refund"


def human_confirm_node(state: RoutingState) -> dict:
    return {
        "final_answer": "该退款请求需要人工客服确认，我已经为您提交处理。",
        "is_finished": True,
        "logs": ["human_confirm：进入人工确认"],
    }


def answer_refund_node(state: RoutingState) -> dict:
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
        "logs": ["answer_refund：退款回答完成"],
    }


def error_handler_node(state: RoutingState) -> dict:
    return {
        "final_answer": "当前服务暂时异常，请稍后再试，或联系人工客服。",
        "is_finished": True,
        "logs": ["error_handler：错误兜底"],
    }


def build_graph():
    graph = StateGraph(RoutingState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("transfer_human", transfer_human_node)

    graph.add_node("build_policy_query", build_policy_query_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("answer_policy", answer_policy_node)
    graph.add_node("policy_fallback", policy_fallback_node)

    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("order_not_found", order_not_found_node)
    graph.add_node("answer_order", answer_order_node)

    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("human_confirm", human_confirm_node)
    graph.add_node("answer_refund", answer_refund_node)
    graph.add_node("error_handler", error_handler_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "general_answer",
            "human": "transfer_human",
            "policy_only": "build_policy_query",
            "need_order": "extract_order_id",
        },
    )

    graph.add_edge("build_policy_query", "retrieve_policy")

    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_policy_only,
        {
            "answer_policy": "answer_policy",
            "policy_fallback": "policy_fallback",
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
            "order_not_found": "order_not_found",
            "error": "error_handler",
            "need_policy": "build_policy_query",
            "answer_order": "answer_order",
        },
    )

    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_refund_policy,
        {
            "assess_risk": "assess_risk",
            "policy_fallback": "policy_fallback",
        },
    )

    graph.add_conditional_edges(
        "assess_risk",
        route_after_risk,
        {
            "human_confirm": "human_confirm",
            "answer_refund": "answer_refund",
        },
    )

    graph.add_edge("general_answer", END)
    graph.add_edge("transfer_human", END)
    graph.add_edge("answer_policy", END)
    graph.add_edge("policy_fallback", END)
    graph.add_edge("ask_order_id", END)
    graph.add_edge("order_not_found", END)
    graph.add_edge("answer_order", END)
    graph.add_edge("human_confirm", END)
    graph.add_edge("answer_refund", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


async def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "我要找人工客服。",
        "售后规则是什么？",
        "帮我查一下订单 10001。",
        "帮我查一下订单。",
        "帮我查一下订单 99999。",
        "我的订单 10002 还没发货，可以退款吗？",
        "我的订单 10003 已经签收，可以退款吗？",
        "我的订单 10002 申请大额退款。",
    ]

    for question in questions:
        print("question:", question)
        print("=" * 80)

        result = await app.ainvoke(
            create_initial_state(question),
            config={
                "recursion_limit": 30
            },
        )

        print("intent:", result["intent"])
        print("final_answer:", result["final_answer"])

        print("\nlogs:")
        for log in result["logs"]:
            print("-", log)

        print("\ntool_calls:")
        for tool_call in result["tool_calls"]:
            print("-", tool_call)

        print("\nsources:")
        for source in result["sources"]:
            print("-", source)

        print("\nerrors:")
        for error in result["errors"]:
            print("-", error)

        print("=" * 120)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg33_10_ecommerce_full_routing_graph.py
```

写入：

```python
import asyncio

from app.langgraph_routing.demo_10_ecommerce_full_routing_graph import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重要提醒】
上面综合图里，有一个故意保留的教学点：

```python
graph.add_conditional_edges(
    "retrieve_policy",
    route_after_policy_only,
    ...
)

graph.add_conditional_edges(
    "retrieve_policy",
    route_after_refund_policy,
    ...
)
```

这表示同一个节点 `retrieve_policy` 后面挂了两套路由。

真实项目里不推荐这么写。

因为同一个节点后面最好只有一种主要路由方式，否则流程会难以理解。

更推荐拆成两个节点：

```plain
retrieve_policy_for_policy_only
retrieve_policy_for_refund
```

或者在 State 里增加：

```plain
policy_flow_type
```

再写一个统一路由函数：

```python
def route_after_retrieve_policy(state) -> Literal[
    "answer_policy",
    "assess_risk",
    "policy_fallback",
]:
    ...
```

下面给出推荐修正版。

---

# 二十二、19｜综合图推荐修正版：统一 retrieve_policy 路由
推荐把 `retrieve_policy` 后面的两个路由合并成一个：

```python
def route_after_retrieve_policy(
    state: RoutingState,
) -> Literal["answer_policy", "assess_risk", "policy_fallback"]:
    if not state["rag_hit"] or not state["sources"]:
        return "policy_fallback"

    if state["intent"] == "refund":
        return "assess_risk"

    return "answer_policy"
```

然后 Graph 里只写一次：

```python
graph.add_conditional_edges(
    "retrieve_policy",
    route_after_retrieve_policy,
    {
        "answer_policy": "answer_policy",
        "assess_risk": "assess_risk",
        "policy_fallback": "policy_fallback",
    },
)
```

---

## 【重点内容】
这个修正版是正式项目里更推荐的写法。

同一个节点后面只保留一个条件路由。

路由函数内部根据 State 判断：

```plain
如果 RAG 没命中
  -> policy_fallback

如果当前是 refund 流程
  -> assess_risk

否则
  -> answer_policy
```

这样清晰很多。

---

# 二十三、20｜正式项目推荐的路由层次
电商客服 Agent 推荐分四层路由。

## 第一层：意图路由
```plain
general
human_service
after_sales
query_order / logistics / refund
```

## 第二层：参数路由
```plain
有订单号
没订单号
```

## 第三层：工具结果路由
```plain
订单查询成功
订单不存在
工具异常
```

## 第四层：业务决策路由
```plain
是否需要查规则
是否需要人工确认
是否可以生成回答
是否进入兜底
```

---

## 【重点内容】
这四层非常实用。

不要把所有判断写在一个 route 函数里。

分层之后，你的流程会非常清楚。

比如退款问题：

```plain
先识别 intent=refund
再提取 order_id
再查订单
再根据订单状态查规则
再根据风险决定是否人工确认
最后生成回答
```

这就是企业 Agent 的标准流程。

---

# 二十四、21｜条件路由和 Structured Output 的关系
第 24 章我们讲过 Structured Output。

它可以识别：

```plain
intent
need_order_id
risk_level
```

LangGraph 里可以这样用：

```plain
classify_intent_node
  -> 调用 Structured Output
  -> 写入 State.intent

route_by_intent
  -> 根据 State.intent 路由
```

---

## 【重点内容】
注意，模型识别和路由不是一回事。

模型节点负责识别。

路由函数负责读识别结果。

比如：

```plain
classify_intent_node 调模型
route_by_intent 不调模型
```

这样职责很清楚。

---

# 二十五、22｜条件路由和 Tool Calling 的关系
Tool Node 执行后可以写入：

```plain
tool_success
tool_calls
errors
order_info
```

然后路由函数判断：

```plain
tool_success=True
  -> 下一步

tool_success=False
  -> error_handler

order_not_found
  -> order_not_found
```

---

## 【重点内容】
不要在 Tool Node 里直接把所有错误都变成最终回答。

更好的方式是：

```plain
Tool Node 负责执行工具
Route 负责判断下一步
Error Node 负责生成兜底
```

这样错误处理更可控。

---

# 二十六、23｜条件路由和 RAG 的关系
RAG Node 执行后可以写入：

```plain
rag_hit
sources
policy_answer
```

然后路由函数判断：

```plain
rag_hit=True and sources
  -> answer_with_sources

rag_hit=False
  -> fallback
```

---

## 【重点内容】
RAG 的路由很重要。

知识库没命中时，不要让模型编。

直接走 fallback：

```plain
根据当前知识库无法确认，建议联系人工客服。
```

这比硬回答安全得多。

---

# 二十七、24｜条件路由和 Human-in-the-loop 的关系
风险节点写入：

```plain
risk_level
need_human_confirm
pending_action
```

路由：

```plain
need_human_confirm=True
  -> human_confirm

need_human_confirm=False
  -> generate_answer
```

---

## 【重点内容】
Human-in-the-loop 不是在最后硬插一个确认框。

它应该是图里的一个分支。

也就是说：

```plain
assess_risk_node
 ↓
route_after_risk
 ↓
human_confirm 或 generate_answer
```

第 35 章我们会在 human_confirm 节点真正实现 interrupt。

---

# 二十八、25｜路由函数不要更新 State
不推荐：

```python
def route(state):
    state["retry_count"] += 1
    return "retry"
```

推荐：

```python
def increase_retry_node(state):
    return {
        "retry_count": state["retry_count"] + 1
    }

def route_after_retry(state):
    if state["retry_count"] < state["max_retry"]:
        return "retry"
    return "fallback"
```

---

## 【重点内容】
路由函数最好是纯函数。

它只根据 State 返回路由结果。

不要在里面改 State。

这样图更可测试，也更容易理解。

如果要更新 State，要写 Node。

或者用 Command。

---

# 二十九、26｜条件路由常见模式总结
## 模式一：意图分流
```plain
intent -> 不同业务流程
```

## 模式二：参数检查
```plain
order_id None -> ask_order_id
```

## 模式三：工具结果判断
```plain
tool_success False -> error_handler
```

## 模式四：RAG 命中判断
```plain
rag_hit False -> fallback
```

## 模式五：风险判断
```plain
need_human_confirm True -> human_confirm
```

## 模式六：循环重试
```plain
retry_count < max_retry -> retry
```

## 模式七：提前结束
```plain
is_finished True -> END
```

---

# 三十、27｜常见错误一：路由函数返回值和 path_map 不一致
错误：

```python
def route(state):
    return "refund_flow"

graph.add_conditional_edges(
    "router",
    route,
    {
        "refund": "refund_node",
    },
)
```

问题：

```plain
route 返回 refund_flow
path_map 里没有 refund_flow
```

正确：

```python
def route(state) -> Literal["refund"]:
    return "refund"
```

---

# 三十一、28｜常见错误二：路由函数不写 Literal
不推荐：

```python
def route(state):
    return state["intent"]
```

推荐：

```python
def route(
    state: RoutingState,
) -> Literal["general", "order", "refund"]:
    ...
```

---

# 三十二、29｜常见错误三：路由函数里调模型
不推荐：

```python
def route(state):
    response = model.invoke(...)
    return response.content
```

推荐：

```plain
LLM Node 写入 intent
Route 函数读取 intent
```

---

# 三十三、30｜常见错误四：同一个节点挂多个条件路由
不推荐：

```python
graph.add_conditional_edges("retrieve_policy", route_a, ...)
graph.add_conditional_edges("retrieve_policy", route_b, ...)
```

推荐：

```python
graph.add_conditional_edges(
    "retrieve_policy",
    route_after_retrieve_policy,
    {
        "answer_policy": "answer_policy",
        "assess_risk": "assess_risk",
        "fallback": "fallback",
    },
)
```

---

# 三十四、31｜常见错误五：静态边和条件边混用
不推荐：

```python
graph.add_edge("classify_intent", "node_a")
graph.add_conditional_edges("classify_intent", route_func, ...)
```

正确：

```plain
固定流程用 add_edge。
动态流程用 add_conditional_edges。
同一个节点尽量选择一种。
```

---

# 三十五、32｜常见错误六：循环没有退出条件
错误：

```plain
retry -> call_tool -> retry
```

没有 max_retry。

正确：

```plain
retry_count >= max_retry
  -> fallback
```

并且调用时加：

```python
config={"recursion_limit": 30}
```

---

# 三十六、33｜常见错误七：把业务判断全塞进一个 route 函数
不推荐：

```plain
route_all：
判断意图
判断订单号
判断订单状态
判断 RAG
判断风险
判断错误
```

推荐拆成多层：

```plain
route_by_intent
route_after_extract_order_id
route_after_query_order
route_after_rag
route_after_risk
```

---

# 三十七、34｜面试回答：Conditional Routing 怎么理解
## 回答话术一：基础版
```plain
LangGraph 的 Conditional Routing 可以理解成根据当前 State 决定下一步执行哪个节点。

普通 Edge 适合固定流程，比如 A 执行完一定到 B。

Conditional Edge 适合动态分支，比如意图是订单查询就进入 query_order，意图是退款就进入 refund_flow，缺少订单号就进入 ask_order_id。

实现上用 add_conditional_edges，传入前置节点、路由函数和 path_map。路由函数只读取 State，返回一个路由 key，再由 path_map 映射到具体节点。
```

---

## 回答话术二：项目版
```plain
在电商客服 Agent 里，我会用多层 Conditional Routing。

第一层根据 intent 路由，普通问题走普通 Chat，人工问题走 transfer_human，订单和退款问题进入订单流程。

第二层判断 order_id，如果没有订单号就追问用户，有订单号才查订单。

第三层判断 query_order 的结果，如果订单不存在就返回订单不存在，如果工具失败就进入 error_handler，如果成功再继续。

第四层针对退款问题检索售后规则，如果 RAG 未命中就 fallback，如果命中就继续做风险评估。

第五层判断 need_human_confirm，如果高风险就进入人工确认，否则生成最终回答。
```

---

## 回答话术三：工程版
```plain
工程上，Conditional Routing 的价值是把复杂业务分支显式化。

它比把一堆 if/else 写在一个大函数里更清晰，也比完全让 Agent 自由选择工具更可控。

我会要求路由函数保持纯粹，只读 State，不调用模型、不查数据库、不修改 State。复杂判断先放到前置 Node 里计算结果，再由路由函数根据结果选择下一步。

同时路由函数要写 Literal 返回类型，add_conditional_edges 要写 path_map，这样类型清晰，图可视化也准确。
```

---

# 三十八、35｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Conditional Routing | 第 30 章核心概念 |
| State 路由字段 | 第 31 章 State 设计 |
| Node 输出路由依据 | 第 32 章 Node |
| add_conditional_edges | 第 32 章 Edge |
| route_by_intent | 第 24 章 Structured Output |
| 缺订单号追问 | 第 19 章项目一客服场景 |
| tool_success 路由 | 第 25 章 Tool |
| rag_hit 路由 | 第 27 章 RAG |
| need_human_confirm 路由 | 第 35 章 Human-in-the-loop |
| retry_count 路由 | 工具失败重试 |
| END 路由 | 图终止 |
| Command 对比 | 第 30 章 Command |
| 电商完整路由 | 第 38 章项目二基础 |


---

# 三十九、36｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Conditional Routing 是什么
2. 理解为什么复杂 Agent 必须有条件路由
3. 理解 add_conditional_edges 基本语法
4. 理解 Literal 返回类型的作用
5. 创建 langgraph_routing 目录
6. 定义 RoutingState
7. 准备 mock query_order 和 mock_search_policy
8. 写出最小条件路由
9. 实现根据 intent 路由
10. 实现缺少订单号路由
11. 实现根据工具结果路由
12. 实现根据 RAG 是否命中路由
13. 实现风险评估触发人工确认
14. 实现路由到 END
15. 实现循环重试路由
16. 对比 Command 和 Conditional Edge
17. 总结路由函数设计原则
18. 完成电商客服完整条件路由图
19. 给出综合图推荐修正版
20. 设计正式项目路由层次
21. 理解条件路由和 Structured Output 的关系
22. 理解条件路由和 Tool Calling 的关系
23. 理解条件路由和 RAG 的关系
24. 理解条件路由和 Human-in-the-loop 的关系
25. 总结条件路由常见模式
26. 总结常见错误
27. 准备面试回答话术
```

---

# 四十、37｜课后任务一：跑通最小条件路由
要求：

```plain
1. 运行 scripts/test_lg33_01_basic_conditional_routing.py
2. 输入普通问题和代码问题
3. 查看 answer_type 如何影响路由
4. 说明 path_map 的作用
```

---

# 四十一、38｜课后任务二：跑通 intent 路由
要求：

```plain
1. 运行 scripts/test_lg33_02_route_by_intent.py
2. 输入普通问题、人工客服、订单查询、退款问题
3. 查看不同 intent 进入不同节点
4. 说明第一层意图路由怎么设计
```

---

# 四十二、39｜课后任务三：跑通缺订单号路由
要求：

```plain
1. 运行 scripts/test_lg33_03_route_missing_order_id.py
2. 输入“帮我查一下订单 10001”
3. 输入“帮我查一下订单”
4. 查看是否进入 ask_order_id
```

---

# 四十三、40｜课后任务四：跑通工具结果路由
要求：

```plain
1. 运行 scripts/test_lg33_04_route_tool_result.py
2. 测试订单 10001
3. 测试订单 99999
4. 查看成功、not_found、error 分支如何设计
```

---

# 四十四、41｜课后任务五：跑通 RAG 命中路由
要求：

```plain
1. 运行 scripts/test_lg33_05_route_rag_result.py
2. 测试“订单未发货可以退款吗？”
3. 测试“公司下午茶制度是什么？”
4. 查看 RAG 命中和 fallback 分支
```

---

# 四十五、42｜课后任务六：跑通人工确认路由
要求：

```plain
1. 运行 scripts/test_lg33_06_route_risk_human_confirm.py
2. 输入普通退款
3. 输入大额退款
4. 查看 need_human_confirm 如何影响路由
```

---

# 四十六、43｜课后任务七：跑通路由到 END
要求：

```plain
1. 运行 scripts/test_lg33_07_route_to_end.py
2. 输入“不用处理了”
3. 查看是否直接结束
4. 说明什么时候适合路由到 END
```

---

# 四十七、44｜课后任务八：跑通循环重试路由
要求：

```plain
1. 运行 scripts/test_lg33_08_loop_retry_routing.py
2. 查看 retry_count 如何增加
3. 查看 max_retry 如何控制退出
4. 修改 max_retry 再观察结果
```

---

# 四十八、45｜课后任务九：对比 Command 和 Conditional Edge
要求：

```plain
1. 运行 scripts/test_lg33_09_command_vs_conditional.py
2. 查看 Command 如何同时 update 和 goto
3. 用 conditional edge 改写同样逻辑
4. 对比两种写法可读性
```

---

# 四十九、46｜课后任务十：跑通完整电商客服路由图
要求：

```plain
1. 运行 scripts/test_lg33_10_ecommerce_full_routing_graph.py
2. 测试普通问题
3. 测试人工客服
4. 测试售后规则
5. 测试订单查询
6. 测试缺少订单号
7. 测试订单不存在
8. 测试未发货退款
9. 测试已签收退款
10. 测试大额退款
```

---

# 五十、47｜课后任务十一：修正完整图中的 retrieve_policy 双路由问题
要求：

```plain
1. 删除 retrieve_policy 后面的两套 conditional edges
2. 新增 route_after_retrieve_policy
3. 根据 intent 和 rag_hit 统一路由
4. 确保 retrieve_policy 后面只有一套条件路由
```

参考路由：

```python
def route_after_retrieve_policy(
    state: RoutingState,
) -> Literal["answer_policy", "assess_risk", "policy_fallback"]:
    if not state["rag_hit"] or not state["sources"]:
        return "policy_fallback"

    if state["intent"] == "refund":
        return "assess_risk"

    return "answer_policy"
```

---

# 五十一、48｜课后任务十二：设计自己的路由表
请为电商客服 Agent 画一张路由表：

| 前置节点 | 路由函数 | 条件 | 下一个节点 |
| --- | --- | --- | --- |
| classify_intent | route_by_intent | general | general_answer |
| classify_intent | route_by_intent | human | transfer_human |
| extract_order_id | route_after_extract_order_id | order_id=None | ask_order_id |
| query_order | route_after_query_order | tool_success=False | error_handler |
| retrieve_policy | route_after_retrieve_policy | rag_hit=False | policy_fallback |
| assess_risk | route_after_risk | need_human_confirm=True | human_confirm |


---

# 五十二、49｜本章总结
## 【重点内容】
好了，到这里，第 33 章我们就讲完了。

这一章我们专门讲了 LangGraph 的 Conditional Routing。

大家一定要记住：

```plain
Node 负责做事。
State 保存结果。
Route 函数负责根据 State 判断下一步。
Conditional Edge 负责把路由结果映射到具体节点。
```

条件路由的核心写法是：

```python
graph.add_conditional_edges(
    "some_node",
    route_func,
    {
        "route_key": "next_node",
    },
)
```

路由函数最好写成：

```python
def route_func(state: State) -> Literal["a", "b", "c"]:
    ...
```

并且要遵守几个原则：

```plain
1. 路由函数只读 State
2. 不调用模型
3. 不调用工具
4. 不修改 State
5. 返回值必须和 path_map 对齐
6. 复杂判断拆成前置 Node
7. 循环必须有退出条件
8. 同一个节点不要混用多套路由
```

这一章完成后，大家就真正掌握了 LangGraph 复杂分支流程的核心能力。

---


