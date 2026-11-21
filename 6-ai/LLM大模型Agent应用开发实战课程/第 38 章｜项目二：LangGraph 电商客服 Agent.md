---

# 一、本章定位
前面我们已经完成了 LangGraph 的基础能力：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
第 34 章｜LangGraph Persistence
第 35 章｜LangGraph Human-in-the-loop
第 36 章｜LangGraph Agent Memory
第 37 章｜LangGraph Multi-Agent
```

这一章正式进入项目二：

# LangGraph 电商客服 Agent
这个项目不是简单聊天机器人。

它要处理真实客服场景：

```plain
1. 普通问答
2. 订单查询
3. 物流查询
4. 退款咨询
5. 售后规则问答
6. 缺订单号追问
7. 多轮上下文续聊
8. 用户偏好记忆
9. 高风险退款人工确认
10. 客服回答安全审核
```

也就是说，这一章要把前面学过的内容全部串起来。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 电商客服 Agent 的需求如何拆解
2. Agent 项目如何设计 State
3. 如何拆分客服流程 Node
4. 如何设计条件路由
5. 如何做意图识别
6. 如何提取订单号
7. 如何查询订单
8. 如何查询物流
9. 如何检索售后规则
10. 如何处理缺订单号追问
11. 如何实现同一会话断点续聊
12. 如何接入 InMemorySaver
13. 如何设计 thread_id
14. 如何接入长期偏好 Memory
15. 如何在节点里读取 Store
16. 如何做退款风险评估
17. 如何用 interrupt 做人工审核
18. 如何用 Command(resume=...) 恢复执行
19. 如何做客服回答 Reviewer
20. 如何封装 Graph Service
21. 如何接入 FastAPI
22. 如何设计前端调用协议
23. 如何包装项目亮点到简历
24. 面试中如何讲这个项目
```

---

# 三、本章版本口径
本项目统一使用：

```plain
Python：3.12+
FastAPI：0.115+
Pydantic：v2
LangChain：1.x
LangGraph：1.x
PostgreSQL：生产推荐
Redis：生产推荐
```

安装基础依赖：

```bash
uv add "langgraph>=1.2,<1.3" \
       "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6"
```

本章主要用到：

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.runtime import Runtime
```

`Command(resume=...)` 是恢复 `interrupt()` 的核心方式；恢复时必须使用同一个 `thread_id`，否则会开启新 thread，无法回到原来的暂停点。

---

# 四、项目最终效果
项目最终支持下面这些输入。

## 场景一：普通问题
用户：

```plain
你好，介绍一下你能做什么？
```

Agent：

```plain
您好，我可以帮您查询订单、查看物流、咨询退款规则，也可以在高风险场景下为您转接人工客服。
```

---

## 场景二：订单查询
用户：

```plain
帮我查一下订单 10002。
```

Agent：

```plain
您的订单当前状态是：已付款，待发货。
```

---

## 场景三：缺少订单号
用户：

```plain
帮我查一下订单。
```

Agent：

```plain
请您提供订单号，我才能继续查询订单状态。
```

用户第二轮：

```plain
订单号是 10002。
```

Agent：

```plain
您的订单当前状态是：已付款，待发货。
```

---

## 场景四：退款咨询
用户：

```plain
我的订单 10002 还没发货，可以退款吗？
```

Agent：

```plain
结论：当前订单可以申请退款。

您的订单状态是：已付款，待发货。根据售后规则，订单未发货时可以申请取消订单并退款。
```

---

## 场景五：高风险退款人工确认
用户：

```plain
我的订单 10003 申请大额退款。
```

Agent 执行到人工确认节点暂停：

```json
{
  "type": "refund_review",
  "risk_level": "high",
  "pending_action": "refund_order",
  "pending_payload": {
    "order_id": "10003",
    "amount": 1299.0,
    "currency": "CNY"
  }
}
```

人工审核通过后：

```plain
退款已提交处理。订单号：10003，退款金额：1299.0 CNY。
```

---

# 五、项目架构图
```plain
FastAPI Router
    ↓
EcommerceAgentService
    ↓
LangGraph Compiled Graph
    ↓
┌────────────────────────────────────┐
│ EcommerceAgentState                │
│ messages / intent / order_id       │
│ order_info / policy_answer         │
│ risk_level / pending_payload       │
│ human_decision / final_answer      │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ LangGraph Nodes                    │
│ recall_memory                      │
│ classify_intent                    │
│ extract_order_id                   │
│ query_order                        │
│ retrieve_policy                    │
│ assess_risk                        │
│ human_review                       │
│ execute_refund                     │
│ generate_answer                    │
│ review_answer                      │
└────────────────────────────────────┘
    ↓
┌────────────────────────────────────┐
│ Checkpointer + Store               │
│ InMemorySaver / PostgresSaver      │
│ InMemoryStore / PostgresStore      │
└────────────────────────────────────┘
```

---

# 六、项目技术亮点
这个项目可以包装成简历亮点：

```plain
1. 基于 LangGraph 设计电商客服 Agent 状态机
2. 使用 StateGraph 显式编排客服处理流程
3. 使用 Conditional Routing 实现订单、退款、物流、售后规则多分支路由
4. 使用 checkpointer 实现多轮会话状态持久化和缺参数续聊
5. 使用 Store 实现用户长期偏好记忆
6. 使用 interrupt + Command(resume) 实现高风险退款人工审核
7. 使用 Reviewer Node 检查客服回答是否存在过度承诺
8. 使用 agent_trace 记录每个节点执行过程，方便排查和审计
9. 通过 FastAPI 封装统一对话、状态查询、人工审核接口
```

---

# 七、创建目录
执行：

```bash
mkdir -p app/langgraph_ecommerce_agent

touch app/langgraph_ecommerce_agent/__init__.py
touch app/langgraph_ecommerce_agent/schemas.py
touch app/langgraph_ecommerce_agent/mock_services.py
touch app/langgraph_ecommerce_agent/graph_factory.py
touch app/langgraph_ecommerce_agent/service.py
touch app/langgraph_ecommerce_agent/demo_01_basic_chat.py
touch app/langgraph_ecommerce_agent/demo_02_missing_order_id.py
touch app/langgraph_ecommerce_agent/demo_03_refund_policy.py
touch app/langgraph_ecommerce_agent/demo_04_hitl_refund.py
touch app/langgraph_ecommerce_agent/demo_05_memory_preference.py
touch app/langgraph_ecommerce_agent/demo_06_stream_trace.py
```

创建 API 文件：

```bash
touch app/api/v1/langgraph_ecommerce_agent.py
```

创建脚本：

```bash
touch scripts/test_lg38_01_basic_chat.py
touch scripts/test_lg38_02_missing_order_id.py
touch scripts/test_lg38_03_refund_policy.py
touch scripts/test_lg38_04_hitl_refund.py
touch scripts/test_lg38_05_memory_preference.py
touch scripts/test_lg38_06_service.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_ecommerce_agent

New-Item app\langgraph_ecommerce_agent\__init__.py
New-Item app\langgraph_ecommerce_agent\schemas.py
New-Item app\langgraph_ecommerce_agent\mock_services.py
New-Item app\langgraph_ecommerce_agent\graph_factory.py
New-Item app\langgraph_ecommerce_agent\service.py
New-Item app\langgraph_ecommerce_agent\demo_01_basic_chat.py
New-Item app\langgraph_ecommerce_agent\demo_02_missing_order_id.py
New-Item app\langgraph_ecommerce_agent\demo_03_refund_policy.py
New-Item app\langgraph_ecommerce_agent\demo_04_hitl_refund.py
New-Item app\langgraph_ecommerce_agent\demo_05_memory_preference.py
New-Item app\langgraph_ecommerce_agent\demo_06_stream_trace.py
```

---

# 八、设计项目 State
打开：

```plain
app/langgraph_ecommerce_agent/schemas.py
```

写入：

```python
import operator
from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


class OrderInfo(TypedDict, total=False):
    order_id: str
    status: str
    status_text: str
    amount: float
    currency: str
    tracking_company: str | None
    tracking_no: str | None
    latest_event: str | None


class SourceInfo(TypedDict, total=False):
    document_id: str
    chunk_id: str
    source: str
    content_preview: str
    score: float


class AgentTraceItem(TypedDict, total=False):
    node_name: str
    input_summary: str
    output_summary: str
    route_to: str | None
    reason: str


class UserMemoryItem(TypedDict, total=False):
    key: str
    type: Literal["preference", "profile", "behavior", "note"]
    content: str
    confidence: float
    source: str


class HumanDecision(TypedDict, total=False):
    type: Literal["approve", "reject", "edit"]
    reviewer_id: str
    reason: str | None
    edited_payload: dict | None


class EcommerceAgentState(TypedDict):
    user_question: str
    messages: Annotated[list[AnyMessage], add_messages]

    intent: Literal[
        "general",
        "query_order",
        "logistics",
        "refund",
        "after_sales",
        "human_service",
        "remember_preference",
        "unknown",
    ]

    order_id: str | None
    order_info: OrderInfo | None

    policy_query: str | None
    policy_answer: str | None
    sources: Annotated[list[SourceInfo], operator.add]
    rag_hit: bool

    risk_level: Literal["low", "medium", "high"]
    need_human_confirm: bool
    pending_action: str | None
    pending_payload: dict | None
    human_decision: HumanDecision | None
    action_result: dict | None

    recalled_memories: Annotated[list[UserMemoryItem], operator.add]
    new_memories: Annotated[list[UserMemoryItem], operator.add]

    draft_answer: str
    final_answer: str
    is_finished: bool

    retry_count: int
    max_retry: int

    agent_trace: Annotated[list[AgentTraceItem], operator.add]
    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


@dataclass
class EcommerceAgentContext:
    tenant_id: str
    user_id: str
    conversation_id: str


def create_initial_state(
    user_question: str,
) -> EcommerceAgentState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "intent": "unknown",

        "order_id": None,
        "order_info": None,

        "policy_query": None,
        "policy_answer": None,
        "sources": [],
        "rag_hit": False,

        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,
        "pending_payload": None,
        "human_decision": None,
        "action_result": None,

        "recalled_memories": [],
        "new_memories": [],

        "draft_answer": "",
        "final_answer": "",
        "is_finished": False,

        "retry_count": 0,
        "max_retry": 2,

        "agent_trace": [],
        "logs": [],
        "errors": [],
    }


def append_user_message(
    user_question: str,
) -> dict:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],
    }
```

---

## 【重点内容】
这里的 State 是这个项目的核心。

它不是简单 messages。

而是完整客服流程状态。

重点看几类字段：

```plain
intent：
当前用户意图。

order_id / order_info：
订单上下文。

policy_answer / sources：
售后规则知识库结果。

risk_level / need_human_confirm：
风险评估结果。

pending_payload / human_decision：
人工确认相关状态。

recalled_memories / new_memories：
用户长期偏好记忆。

draft_answer / final_answer：
回答生成和审核结果。

agent_trace / logs / errors：
执行过程追踪。
```

这个 State 设计好了，后面的 Node 和 Edge 才好写。

---

# 九、准备 Mock Services
打开：

```plain
app/langgraph_ecommerce_agent/mock_services.py
```

写入：

```python
import asyncio


MOCK_ORDERS = {
    "10001": {
        "order_id": "10001",
        "status": "shipped",
        "status_text": "已发货",
        "amount": 399.0,
        "currency": "CNY",
        "tracking_company": "顺丰",
        "tracking_no": "SF10001",
        "latest_event": "包裹已到达成都高新区中转站。",
    },
    "10002": {
        "order_id": "10002",
        "status": "paid",
        "status_text": "已付款，待发货",
        "amount": 199.0,
        "currency": "CNY",
        "tracking_company": None,
        "tracking_no": None,
        "latest_event": None,
    },
    "10003": {
        "order_id": "10003",
        "status": "paid",
        "status_text": "已付款，待发货",
        "amount": 1299.0,
        "currency": "CNY",
        "tracking_company": None,
        "tracking_no": None,
        "latest_event": None,
    },
}


def extract_order_id_from_text(text: str) -> str | None:
    for order_id in MOCK_ORDERS:
        if order_id in text:
            return order_id

    if "99999" in text:
        return "99999"

    return None


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
                "amount": 0.0,
                "currency": "CNY",
                "tracking_company": None,
                "tracking_no": None,
                "latest_event": None,
            },
        }

    return {
        "success": True,
        "error": None,
        "data": order,
    }


async def mock_query_logistics(order_info: dict | None) -> dict:
    await asyncio.sleep(0.05)

    if not order_info:
        return {
            "success": False,
            "message": "缺少订单信息",
            "data": None,
        }

    if not order_info.get("tracking_no"):
        return {
            "success": False,
            "message": "当前订单暂无物流单号",
            "data": None,
        }

    return {
        "success": True,
        "message": "物流查询成功",
        "data": {
            "tracking_company": order_info.get("tracking_company"),
            "tracking_no": order_info.get("tracking_no"),
            "latest_event": order_info.get("latest_event"),
        },
    }


async def mock_retrieve_policy(query: str | None) -> dict:
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
            "answer": "根据售后规则，订单未发货时，用户可以申请取消订单并退款。",
            "sources": [
                {
                    "document_id": "ecommerce_after_sales",
                    "chunk_id": "refund_paid_order",
                    "source": "data/knowledge_base/ecommerce_after_sales.md",
                    "content_preview": "订单未发货时，用户可以申请取消订单并退款。",
                    "score": 0.93,
                }
            ],
        }

    if "已发货" in query or "已签收" in query:
        return {
            "hit": True,
            "answer": "根据售后规则，订单已发货后，需要用户收到商品后再发起退货退款申请。",
            "sources": [
                {
                    "document_id": "ecommerce_after_sales",
                    "chunk_id": "refund_shipped_order",
                    "source": "data/knowledge_base/ecommerce_after_sales.md",
                    "content_preview": "订单已发货后，需要用户收到商品后再发起退货退款申请。",
                    "score": 0.9,
                }
            ],
        }

    if "售后" in query:
        return {
            "hit": True,
            "answer": "售后问题需要结合订单状态、商品状态和平台规则综合判断。",
            "sources": [
                {
                    "document_id": "ecommerce_after_sales",
                    "chunk_id": "after_sales_general",
                    "source": "data/knowledge_base/ecommerce_after_sales.md",
                    "content_preview": "售后问题需要结合订单状态、商品状态和平台规则综合判断。",
                    "score": 0.82,
                }
            ],
        }

    return {
        "hit": False,
        "answer": "根据当前知识库无法确认。",
        "sources": [],
    }


async def mock_execute_refund(payload: dict) -> dict:
    await asyncio.sleep(0.05)

    return {
        "success": True,
        "refund_id": f"rf_{payload.get('order_id', 'unknown')}",
        "executed_payload": payload,
    }


async def mock_transfer_human(reason: str) -> dict:
    await asyncio.sleep(0.05)

    return {
        "success": True,
        "ticket_id": "ticket_10001",
        "reason": reason,
    }
```

---

## 【重点内容】
这里先用 mock services。

真实项目中可以替换成：

```plain
订单系统 API
物流系统 API
退款系统 API
售后规则 RAG
客服工单系统
```

先用 mock 的好处是让整个 Graph 先跑通。

不要一上来就接真实系统。

否则调试难度会非常高。

---

# 十、核心 Graph Factory
打开：

```plain
app/langgraph_ecommerce_agent/graph_factory.py
```

写入：

```python
import uuid
from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore
from langgraph.types import interrupt

from app.langgraph_ecommerce_agent.mock_services import (
    extract_order_id_from_text,
    mock_execute_refund,
    mock_query_logistics,
    mock_query_order,
    mock_retrieve_policy,
    mock_transfer_human,
)
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    EcommerceAgentState,
)


def recall_memory_node(
    state: EcommerceAgentState,
    runtime: Runtime[EcommerceAgentContext],
) -> dict:
    namespace = (
        runtime.context.tenant_id,
        runtime.context.user_id,
        "preferences",
    )

    items = runtime.store.search(namespace)

    memories = []

    for item in items:
        value = item.value
        memories.append({
            "key": item.key,
            "type": value.get("type", "preference"),
            "content": value.get("content", ""),
            "confidence": value.get("confidence", 0.8),
            "source": value.get("source", "store"),
        })

    return {
        "recalled_memories": memories,
        "logs": [f"recall_memory：召回 {len(memories)} 条用户偏好"],
        "agent_trace": [
            {
                "node_name": "recall_memory",
                "input_summary": "tenant_id + user_id",
                "output_summary": f"召回 {len(memories)} 条偏好",
                "route_to": "classify_intent",
                "reason": "回答前先获取用户长期偏好",
            }
        ],
    }


def classify_intent_node(state: EcommerceAgentState) -> dict:
    question = state["user_question"]

    if "记住" in question or "以后回答" in question or "以后你" in question:
        intent = "remember_preference"
    elif "人工" in question or "客服" in question and "人工" in question:
        intent = "human_service"
    elif "退款" in question or "退货" in question:
        intent = "refund"
    elif "物流" in question or "快递" in question:
        intent = "logistics"
    elif "售后" in question or "规则" in question:
        intent = "after_sales"
    elif "订单" in question:
        intent = "query_order"
    elif state.get("intent") in ["refund", "query_order", "logistics"]:
        # 支持多轮续聊。
        # 比如上一轮问“我要退款”，这一轮只补充“订单号是 10002”。
        intent = state["intent"]
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：intent={intent}"],
    }


def route_by_intent(
    state: EcommerceAgentState,
) -> Literal[
    "remember",
    "general",
    "human",
    "policy_only",
    "need_order",
]:
    intent = state["intent"]

    if intent == "remember_preference":
        return "remember"

    if intent == "general":
        return "general"

    if intent == "human_service":
        return "human"

    if intent == "after_sales":
        return "policy_only"

    return "need_order"


def write_memory_node(
    state: EcommerceAgentState,
    runtime: Runtime[EcommerceAgentContext],
) -> dict:
    namespace = (
        runtime.context.tenant_id,
        runtime.context.user_id,
        "preferences",
    )

    memory = {
        "type": "preference",
        "content": state["user_question"],
        "confidence": 0.85,
        "source": "user_explicit_request",
    }

    key = f"pref_{uuid.uuid4().hex}"

    runtime.store.put(
        namespace,
        key,
        memory,
    )

    answer = "好的，我已经记住这个偏好。"

    return {
        "new_memories": [
            {
                "key": key,
                **memory,
            }
        ],
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": [f"write_memory：写入用户偏好 key={key}"],
    }


def general_answer_node(state: EcommerceAgentState) -> dict:
    memory_text = "\n".join(
        memory["content"]
        for memory in state["recalled_memories"]
    )

    if memory_text:
        answer = (
            "您好，我可以帮您查询订单、查看物流、咨询退款和售后规则。"
            f"我也会参考你的偏好：{memory_text}"
        )
    else:
        answer = (
            "您好，我可以帮您查询订单、查看物流、咨询退款和售后规则。"
            "如果涉及高风险退款，我会先提交人工确认。"
        )

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["general_answer：普通回答完成"],
    }


async def transfer_human_node(state: EcommerceAgentState) -> dict:
    result = await mock_transfer_human(
        reason=state["user_question"],
    )

    answer = f"我已经为您转接人工客服，工单号：{result['ticket_id']}。"

    return {
        "action_result": result,
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["transfer_human：已创建人工客服工单"],
    }


def build_policy_query_node(state: EcommerceAgentState) -> dict:
    if state["intent"] == "after_sales":
        query = state["user_question"]
    elif state["order_info"] and state["order_info"].get("status") == "paid":
        query = "订单未发货退款规则"
    elif state["order_info"] and state["order_info"].get("status") == "shipped":
        query = "订单已发货退货退款规则"
    else:
        query = "售后规则"

    return {
        "policy_query": query,
        "logs": [f"build_policy_query：policy_query={query}"],
    }


async def retrieve_policy_node(state: EcommerceAgentState) -> dict:
    result = await mock_retrieve_policy(
        query=state["policy_query"],
    )

    return {
        "rag_hit": result["hit"],
        "policy_answer": result["answer"],
        "sources": result["sources"],
        "logs": [f"retrieve_policy：rag_hit={result['hit']}"],
    }


def route_after_policy(
    state: EcommerceAgentState,
) -> Literal["answer_policy", "assess_risk", "policy_fallback"]:
    if not state["rag_hit"] or not state["sources"]:
        return "policy_fallback"

    if state["intent"] == "refund":
        return "assess_risk"

    return "answer_policy"


def answer_policy_node(state: EcommerceAgentState) -> dict:
    answer = (
        f"{state['policy_answer']}"
        " 回答依据来自售后规则知识库。"
    )

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["answer_policy：售后规则回答完成"],
    }


def policy_fallback_node(state: EcommerceAgentState) -> dict:
    answer = "根据当前知识库无法确认，建议联系人工客服进一步处理。"

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["policy_fallback：知识库未命中"],
    }


def extract_order_id_node(state: EcommerceAgentState) -> dict:
    order_id = extract_order_id_from_text(
        state["user_question"]
    )

    if not order_id:
        order_id = state.get("order_id")

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


def route_after_extract_order_id(
    state: EcommerceAgentState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: EcommerceAgentState) -> dict:
    if state["intent"] == "refund":
        answer = "请您提供订单号，我才能继续判断退款规则。"
    elif state["intent"] == "logistics":
        answer = "请您提供订单号，我才能继续查询物流。"
    else:
        answer = "请您提供订单号，我才能继续查询订单状态。"

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["ask_order_id：缺少订单号，追问用户"],
    }


async def query_order_node(state: EcommerceAgentState) -> dict:
    result = await mock_query_order(
        order_id=state["order_id"],
    )

    if not result["success"]:
        return {
            "order_info": result.get("data"),
            "errors": [result["error"]],
            "logs": [f"query_order：失败 {result['error']}"],
        }

    return {
        "order_info": result["data"],
        "logs": [f"query_order：成功 {result['data']['status_text']}"],
    }


def route_after_query_order(
    state: EcommerceAgentState,
) -> Literal[
    "order_not_found",
    "logistics",
    "need_policy",
    "answer_order",
]:
    if state["errors"] and "order_not_found" in state["errors"]:
        return "order_not_found"

    if state["intent"] == "logistics":
        return "logistics"

    if state["intent"] == "refund":
        return "need_policy"

    return "answer_order"


def order_not_found_node(state: EcommerceAgentState) -> dict:
    answer = "没有查询到该订单，请您检查订单号是否正确。"

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["order_not_found：订单不存在"],
    }


async def query_logistics_node(state: EcommerceAgentState) -> dict:
    result = await mock_query_logistics(
        order_info=state["order_info"],
    )

    if not result["success"]:
        answer = result["message"]
    else:
        data = result["data"]
        answer = (
            f"物流公司：{data['tracking_company']}，"
            f"物流单号：{data['tracking_no']}，"
            f"最新节点：{data['latest_event']}"
        )

    return {
        "draft_answer": answer,
        "logs": ["query_logistics：物流查询完成"],
    }


def answer_order_node(state: EcommerceAgentState) -> dict:
    order_info = state["order_info"]

    answer = f"您的订单当前状态是：{order_info['status_text']}。"

    if order_info.get("tracking_no"):
        answer += (
            f"物流公司：{order_info['tracking_company']}，"
            f"物流单号：{order_info['tracking_no']}，"
            f"最新节点：{order_info['latest_event']}。"
        )

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["answer_order：订单回答完成"],
    }


def assess_risk_node(state: EcommerceAgentState) -> dict:
    order_info = state["order_info"] or {}
    amount = float(order_info.get("amount", 0))
    status = order_info.get("status")

    pending_payload = {
        "order_id": order_info.get("order_id"),
        "amount": amount,
        "currency": order_info.get("currency", "CNY"),
        "reason": "用户申请退款",
    }

    if status != "paid":
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "pending_action": "refund_order",
            "pending_payload": pending_payload,
            "logs": ["assess_risk：非待发货订单退款，高风险"],
        }

    if amount >= 500:
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "pending_action": "refund_order",
            "pending_payload": pending_payload,
            "logs": ["assess_risk：大额退款，高风险"],
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": "refund_order",
        "pending_payload": pending_payload,
        "logs": ["assess_risk：低风险，可自动给出退款建议"],
    }


def route_after_risk(
    state: EcommerceAgentState,
) -> Literal["human_review", "generate_refund_answer"]:
    if state["need_human_confirm"]:
        return "human_review"

    return "generate_refund_answer"


def human_review_node(state: EcommerceAgentState) -> dict:
    decision = interrupt({
        "type": "refund_review",
        "risk_level": state["risk_level"],
        "pending_action": state["pending_action"],
        "pending_payload": state["pending_payload"],
        "order_info": state["order_info"],
        "policy_answer": state["policy_answer"],
        "options": ["approve", "reject", "edit"],
        "message": "该退款请求需要人工审核，请确认是否继续处理。",
    })

    return {
        "human_decision": decision,
        "logs": [f"human_review：收到人工决策 {decision}"],
    }


def route_after_human_review(
    state: EcommerceAgentState,
) -> Literal["execute_refund", "reject_refund", "apply_edit"]:
    decision = state["human_decision"] or {}
    decision_type = decision.get("type")

    if decision_type == "approve":
        return "execute_refund"

    if decision_type == "edit":
        return "apply_edit"

    return "reject_refund"


def apply_edit_node(state: EcommerceAgentState) -> dict:
    decision = state["human_decision"] or {}
    edited_payload = decision.get("edited_payload") or {}

    return {
        "pending_payload": edited_payload,
        "logs": [f"apply_edit：人工修改退款参数 {edited_payload}"],
    }


async def execute_refund_node(state: EcommerceAgentState) -> dict:
    payload = state["pending_payload"] or {}

    result = await mock_execute_refund(payload)

    return {
        "action_result": result,
        "logs": [f"execute_refund：退款执行结果 {result}"],
    }


def reject_refund_node(state: EcommerceAgentState) -> dict:
    decision = state["human_decision"] or {}

    result = {
        "success": False,
        "reason": decision.get("reason", "人工拒绝退款"),
    }

    return {
        "action_result": result,
        "logs": [f"reject_refund：人工拒绝 {result}"],
    }


def generate_refund_answer_node(state: EcommerceAgentState) -> dict:
    order_info = state["order_info"] or {}
    policy_answer = state["policy_answer"] or ""
    action_result = state["action_result"]

    if action_result:
        if action_result.get("success"):
            payload = action_result.get("executed_payload") or {}
            answer = (
                f"退款已提交处理。订单号：{payload.get('order_id')}，"
                f"退款金额：{payload.get('amount')} {payload.get('currency')}。"
            )
        else:
            answer = (
                "本次退款暂未执行。"
                f"原因：{action_result.get('reason', '未说明')}。"
            )
    else:
        answer = (
            f"结论：您的订单当前可以按规则申请退款。\n\n"
            f"订单状态：{order_info.get('status_text')}。"
            f"{policy_answer}"
        )

    return {
        "draft_answer": answer,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["generate_refund_answer：退款回答生成完成"],
    }


def review_answer_node(state: EcommerceAgentState) -> dict:
    answer = state["draft_answer"]

    risky_words = [
        "保证退款",
        "一定退款",
        "立即到账",
        "百分百成功",
    ]

    has_risky_word = any(word in answer for word in risky_words)

    if has_risky_word and state["retry_count"] < state["max_retry"]:
        return {
            "errors": ["answer_has_risky_promise"],
            "logs": ["review_answer：回答包含过度承诺，需要改写"],
        }

    return {
        "logs": ["review_answer：回答审核通过"],
    }


def route_after_review(
    state: EcommerceAgentState,
) -> Literal["rewrite", "finish"]:
    if state["errors"] and "answer_has_risky_promise" in state["errors"]:
        if state["retry_count"] < state["max_retry"]:
            return "rewrite"

    return "finish"


def rewrite_answer_node(state: EcommerceAgentState) -> dict:
    rewritten = (
        state["draft_answer"]
        .replace("保证退款", "可按规则申请退款")
        .replace("一定退款", "通常可按规则处理")
        .replace("立即到账", "以实际到账时间为准")
        .replace("百分百成功", "以平台审核结果为准")
    )

    return {
        "draft_answer": rewritten,
        "retry_count": state["retry_count"] + 1,
        "logs": ["rewrite_answer：已移除过度承诺表达"],
    }


def finish_node(state: EcommerceAgentState) -> dict:
    answer = state["draft_answer"]

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "agent_trace": [
            {
                "node_name": "finish",
                "input_summary": "draft_answer",
                "output_summary": answer[:100],
                "route_to": None,
                "reason": "客服回答最终输出",
            }
        ],
        "logs": ["finish：流程结束"],
    }


def build_ecommerce_agent_graph(
    checkpointer=None,
    store=None,
):
    graph = StateGraph(
        EcommerceAgentState,
        context_schema=EcommerceAgentContext,
    )

    graph.add_node("recall_memory", recall_memory_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("write_memory", write_memory_node)
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
    graph.add_node("query_logistics", query_logistics_node)
    graph.add_node("answer_order", answer_order_node)

    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("apply_edit", apply_edit_node)
    graph.add_node("execute_refund", execute_refund_node)
    graph.add_node("reject_refund", reject_refund_node)
    graph.add_node("generate_refund_answer", generate_refund_answer_node)

    graph.add_node("review_answer", review_answer_node)
    graph.add_node("rewrite_answer", rewrite_answer_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "recall_memory")
    graph.add_edge("recall_memory", "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "remember": "write_memory",
            "general": "general_answer",
            "human": "transfer_human",
            "policy_only": "build_policy_query",
            "need_order": "extract_order_id",
        },
    )

    graph.add_edge("build_policy_query", "retrieve_policy")

    graph.add_conditional_edges(
        "retrieve_policy",
        route_after_policy,
        {
            "answer_policy": "answer_policy",
            "assess_risk": "assess_risk",
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
            "logistics": "query_logistics",
            "need_policy": "build_policy_query",
            "answer_order": "answer_order",
        },
    )

    graph.add_conditional_edges(
        "assess_risk",
        route_after_risk,
        {
            "human_review": "human_review",
            "generate_refund_answer": "generate_refund_answer",
        },
    )

    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "execute_refund": "execute_refund",
            "reject_refund": "reject_refund",
            "apply_edit": "apply_edit",
        },
    )

    graph.add_edge("apply_edit", "execute_refund")
    graph.add_edge("execute_refund", "generate_refund_answer")
    graph.add_edge("reject_refund", "generate_refund_answer")

    graph.add_edge("general_answer", "review_answer")
    graph.add_edge("transfer_human", "review_answer")
    graph.add_edge("answer_policy", "review_answer")
    graph.add_edge("policy_fallback", "review_answer")
    graph.add_edge("ask_order_id", "review_answer")
    graph.add_edge("order_not_found", "review_answer")
    graph.add_edge("query_logistics", "review_answer")
    graph.add_edge("answer_order", "review_answer")
    graph.add_edge("generate_refund_answer", "review_answer")

    graph.add_conditional_edges(
        "review_answer",
        route_after_review,
        {
            "rewrite": "rewrite_answer",
            "finish": "finish",
        },
    )

    graph.add_edge("rewrite_answer", "review_answer")
    graph.add_edge("write_memory", END)
    graph.add_edge("finish", END)

    if checkpointer is None:
        checkpointer = InMemorySaver()

    if store is None:
        store = InMemoryStore()

    app = graph.compile(
        checkpointer=checkpointer,
        store=store,
    )

    return app, store
```

---

## 【重点内容】
这个文件是整个项目最核心的地方。

我们把电商客服流程拆成了很多节点：

```plain
recall_memory：
先召回用户长期偏好。

classify_intent：
判断用户意图。

extract_order_id：
提取订单号。

query_order：
查询订单。

retrieve_policy：
检索售后规则。

assess_risk：
退款风险评估。

human_review：
高风险退款人工审核。

execute_refund：
真正执行退款动作。

review_answer：
检查客服回答是否有过度承诺。

finish：
输出最终结果。
```

这里有一个关键原则：

**高风险业务动作必须放在 interrupt 之后。**

也就是说，不能在 `human_review_node` 之前就执行真实退款。

因为 `interrupt()` 恢复时，节点会重新执行。真实业务副作用应该放到恢复后的节点里，例如 `execute_refund_node`。这和 LangGraph interrupts 文档里的安全规则一致：`interrupt` 前不要执行非幂等副作用。

---

# 十一、示例一：普通问题
打开：

```plain
app/langgraph_ecommerce_agent/demo_01_basic_chat.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    create_initial_state,
)


async def main():
    app, _store = build_ecommerce_agent_graph()

    result = await app.ainvoke(
        create_initial_state("你好，介绍一下你能做什么？"),
        config={
            "configurable": {
                "thread_id": "thread_lg38_basic_chat"
            },
            "recursion_limit": 30,
        },
        context=EcommerceAgentContext(
            tenant_id="tenant_001",
            user_id="u_10001",
            conversation_id="conv_basic_chat",
        ),
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg38_01_basic_chat.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.demo_01_basic_chat import main


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lg38_01_basic_chat.py
```

---

# 十二、示例二：缺订单号，多轮续聊
打开：

```plain
app/langgraph_ecommerce_agent/demo_02_missing_order_id.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    append_user_message,
    create_initial_state,
)


async def main():
    app, _store = build_ecommerce_agent_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg38_missing_order_id"
        },
        "recursion_limit": 30,
    }

    context = EcommerceAgentContext(
        tenant_id="tenant_001",
        user_id="u_10001",
        conversation_id="conv_missing_order_id",
    )

    first = await app.ainvoke(
        create_initial_state("帮我查一下订单。"),
        config=config,
        context=context,
    )

    print("first:")
    print("final_answer:", first["final_answer"])
    print("intent:", first["intent"])
    print("order_id:", first["order_id"])
    print("=" * 80)

    second = await app.ainvoke(
        append_user_message("订单号是 10002。"),
        config=config,
        context=context,
    )

    print("second:")
    print("final_answer:", second["final_answer"])
    print("intent:", second["intent"])
    print("order_id:", second["order_id"])
    print("order_info:", second["order_info"])


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg38_02_missing_order_id.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.demo_02_missing_order_id import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个示例非常关键。

第一轮用户没给订单号。

Graph 会输出：

```plain
请您提供订单号
```

第二轮用户只说：

```plain
订单号是 10002。
```

因为同一个 `thread_id` 里有 checkpoint，Graph 可以继承上一轮意图和状态继续处理。短期记忆就是 thread-scoped state，通过 checkpointer 在同一个 thread 里保存和恢复。

---

# 十三、示例三：退款规则查询
打开：

```plain
app/langgraph_ecommerce_agent/demo_03_refund_policy.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    create_initial_state,
)


async def main():
    app, _store = build_ecommerce_agent_graph()

    result = await app.ainvoke(
        create_initial_state("我的订单 10002 还没发货，可以退款吗？"),
        config={
            "configurable": {
                "thread_id": "thread_lg38_refund_policy"
            },
            "recursion_limit": 30,
        },
        context=EcommerceAgentContext(
            tenant_id="tenant_001",
            user_id="u_10001",
            conversation_id="conv_refund_policy",
        ),
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("policy_answer:")
    print(result["policy_answer"])

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
scripts/test_lg38_03_refund_policy.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.demo_03_refund_policy import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 十四、示例四：高风险退款 HITL
打开：

```plain
app/langgraph_ecommerce_agent/demo_04_hitl_refund.py
```

写入：

```python
import asyncio

from langgraph.types import Command

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    create_initial_state,
)


async def run_approve_case():
    app, _store = build_ecommerce_agent_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg38_hitl_approve"
        },
        "recursion_limit": 30,
    }

    context = EcommerceAgentContext(
        tenant_id="tenant_001",
        user_id="u_10001",
        conversation_id="conv_hitl_approve",
    )

    first = await app.ainvoke(
        create_initial_state("我的订单 10003 申请大额退款。"),
        config=config,
        context=context,
    )

    print("第一次执行，应该触发 interrupt：")
    print(first)

    print("=" * 80)
    print("当前 state：")
    snapshot = await app.aget_state(config)
    print(snapshot.values)

    print("=" * 80)
    print("人工 approve 后恢复：")

    second = await app.ainvoke(
        Command(resume={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "大额退款人工审核通过",
        }),
        config=config,
        context=context,
    )

    print("final_answer:")
    print(second["final_answer"])

    print("=" * 80)
    print("action_result:")
    print(second["action_result"])


async def run_edit_case():
    app, _store = build_ecommerce_agent_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg38_hitl_edit"
        },
        "recursion_limit": 30,
    }

    context = EcommerceAgentContext(
        tenant_id="tenant_001",
        user_id="u_10001",
        conversation_id="conv_hitl_edit",
    )

    await app.ainvoke(
        create_initial_state("我的订单 10003 申请大额退款。"),
        config=config,
        context=context,
    )

    second = await app.ainvoke(
        Command(resume={
            "type": "edit",
            "reviewer_id": "admin_002",
            "reason": "优惠券不可退，只退实付金额",
            "edited_payload": {
                "order_id": "10003",
                "amount": 1099.0,
                "currency": "CNY",
                "reason": "人工修改后的退款金额",
            },
        }),
        config=config,
        context=context,
    )

    print("edit case final_answer:")
    print(second["final_answer"])
    print("pending_payload:")
    print(second["pending_payload"])


async def main():
    await run_approve_case()
    print("=" * 120)
    await run_edit_case()


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg38_04_hitl_refund.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.demo_04_hitl_refund import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

# 十五、示例五：用户偏好记忆
打开：

```plain
app/langgraph_ecommerce_agent/demo_05_memory_preference.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    create_initial_state,
)


async def main():
    app, store = build_ecommerce_agent_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg38_memory_preference"
        },
        "recursion_limit": 30,
    }

    context = EcommerceAgentContext(
        tenant_id="tenant_001",
        user_id="u_10001",
        conversation_id="conv_memory_preference",
    )

    first = await app.ainvoke(
        create_initial_state("记住：以后回答客服问题，先给结论，再给处理步骤。"),
        config=config,
        context=context,
    )

    print("first:")
    print(first["final_answer"])
    print("new_memories:", first["new_memories"])
    print("=" * 80)

    second = await app.ainvoke(
        create_initial_state("你好，介绍一下你能做什么？"),
        config=config,
        context=context,
    )

    print("second:")
    print(second["final_answer"])
    print("recalled_memories:", second["recalled_memories"])
    print("=" * 80)

    namespace = ("tenant_001", "u_10001", "preferences")
    print("store memories:")
    for item in store.search(namespace):
        print(item.key, item.value)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg38_05_memory_preference.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.demo_05_memory_preference import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
这个示例说明长期记忆怎么用。

用户明确说：

```plain
记住：以后回答客服问题，先给结论，再给处理步骤。
```

我们才写入 Store。

下一轮再回答时，`recall_memory_node` 会先召回用户偏好。

长期记忆是跨 thread / session 的能力，通常用 Store 保存为 namespace + key 组织的 JSON 文档。

---

# 十六、示例六：stream 观察执行过程
打开：

```plain
app/langgraph_ecommerce_agent/demo_06_stream_trace.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    create_initial_state,
)


async def main():
    app, _store = build_ecommerce_agent_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg38_stream_trace"
        },
        "recursion_limit": 30,
    }

    context = EcommerceAgentContext(
        tenant_id="tenant_001",
        user_id="u_10001",
        conversation_id="conv_stream_trace",
    )

    async for chunk in app.astream(
        create_initial_state("我的订单 10002 还没发货，可以退款吗？"),
        config=config,
        context=context,
        stream_mode="updates",
    ):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
真实调试 LangGraph，不要只看 final_answer。

要看每一步：

```plain
走了哪个节点
节点输出了什么
路由到了哪里
有没有进入人工审核
有没有进入 Reviewer
```

LangGraph 的 streaming 文档说明，stream 可以观察节点更新、状态变化、interrupt 等运行时信息；恢复 interrupt 时也需要携带 checkpointer 和 thread_id。

---

# 十七、封装 Service
打开：

```plain
app/langgraph_ecommerce_agent/service.py
```

写入：

```python
from langgraph.types import Command

from app.langgraph_ecommerce_agent.graph_factory import build_ecommerce_agent_graph
from app.langgraph_ecommerce_agent.schemas import (
    EcommerceAgentContext,
    append_user_message,
    create_initial_state,
)


class LangGraphEcommerceAgentService:
    def __init__(self):
        self.graph, self.store = build_ecommerce_agent_graph()

    def build_thread_id(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> str:
        return f"{tenant_id}:{user_id}:{conversation_id}"

    def build_context(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> EcommerceAgentContext:
        return EcommerceAgentContext(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

    def build_config(
        self,
        thread_id: str,
    ) -> dict:
        return {
            "configurable": {
                "thread_id": thread_id
            },
            "recursion_limit": 30,
        }

    async def chat(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        question: str,
        is_new_conversation: bool = False,
    ) -> dict:
        thread_id = self.build_thread_id(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        config = self.build_config(thread_id)
        context = self.build_context(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        input_state = (
            create_initial_state(question)
            if is_new_conversation
            else append_user_message(question)
        )

        result = await self.graph.ainvoke(
            input_state,
            config=config,
            context=context,
        )

        return {
            "thread_id": thread_id,
            "answer": result.get("final_answer", ""),
            "intent": result.get("intent"),
            "order_id": result.get("order_id"),
            "order_info": result.get("order_info"),
            "risk_level": result.get("risk_level"),
            "need_human_confirm": result.get("need_human_confirm"),
            "pending_action": result.get("pending_action"),
            "pending_payload": result.get("pending_payload"),
            "recalled_memories": result.get("recalled_memories", []),
            "sources": result.get("sources", []),
            "logs": result.get("logs", []),
            "errors": result.get("errors", []),
        }

    async def resume(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        decision: dict,
    ) -> dict:
        thread_id = self.build_thread_id(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        config = self.build_config(thread_id)
        context = self.build_context(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        result = await self.graph.ainvoke(
            Command(resume=decision),
            config=config,
            context=context,
        )

        return {
            "thread_id": thread_id,
            "answer": result.get("final_answer", ""),
            "human_decision": result.get("human_decision"),
            "action_result": result.get("action_result"),
            "logs": result.get("logs", []),
            "errors": result.get("errors", []),
        }

    async def get_state(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> dict:
        thread_id = self.build_thread_id(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        config = self.build_config(thread_id)

        snapshot = await self.graph.aget_state(config)

        return {
            "thread_id": thread_id,
            "values": snapshot.values,
            "next": snapshot.next,
            "config": snapshot.config,
        }

    def list_memories(
        self,
        tenant_id: str,
        user_id: str,
        memory_type: str = "preferences",
    ) -> list[dict]:
        namespace = (
            tenant_id,
            user_id,
            memory_type,
        )

        return [
            {
                "key": item.key,
                "value": item.value,
            }
            for item in self.store.search(namespace)
        ]


langgraph_ecommerce_agent_service = LangGraphEcommerceAgentService()
```

---

# 十八、测试 Service
创建：

```plain
scripts/test_lg38_06_service.py
```

写入：

```python
import asyncio

from app.langgraph_ecommerce_agent.service import langgraph_ecommerce_agent_service


async def main():
    tenant_id = "tenant_001"
    user_id = "u_10001"
    conversation_id = "conv_lg38_service"

    first = await langgraph_ecommerce_agent_service.chat(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question="帮我查一下订单。",
        is_new_conversation=True,
    )

    print("first:")
    print(first)
    print("=" * 80)

    second = await langgraph_ecommerce_agent_service.chat(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question="订单号是 10002。",
    )

    print("second:")
    print(second)
    print("=" * 80)

    state = await langgraph_ecommerce_agent_service.get_state(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("state:")
    print(state["values"])


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lg38_06_service.py
```

---

# 十九、创建 FastAPI 接口
打开：

```plain
app/api/v1/langgraph_ecommerce_agent.py
```

写入：

```python
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langgraph_ecommerce_agent.service import (
    langgraph_ecommerce_agent_service,
)
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class EcommerceAgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")
    is_new_conversation: bool = Field(default=False)


class EcommerceAgentResumeRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")

    type: Literal["approve", "reject", "edit"]
    reason: str | None = None
    edited_payload: dict | None = None


@router.post(
    "/langgraph/ecommerce-agent/chat",
    response_model=ApiResponse[dict],
)
async def ecommerce_agent_chat(
    request: EcommerceAgentChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = await langgraph_ecommerce_agent_service.chat(
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
        question=request.question,
        is_new_conversation=request.is_new_conversation,
    )

    return ApiResponse[dict](
        data=result
    )


@router.get(
    "/langgraph/ecommerce-agent/state/{conversation_id}",
    response_model=ApiResponse[dict],
)
async def get_ecommerce_agent_state(
    conversation_id: str,
    tenant_id: str = "tenant_001",
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = await langgraph_ecommerce_agent_service.get_state(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )

    return ApiResponse[dict](
        data=result
    )


@router.post(
    "/langgraph/ecommerce-agent/resume",
    response_model=ApiResponse[dict],
)
async def resume_ecommerce_agent(
    request: EcommerceAgentResumeRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    decision = {
        "type": request.type,
        "reviewer_id": current_user.user_id,
        "reason": request.reason,
    }

    if request.type == "edit":
        decision["edited_payload"] = request.edited_payload

    result = await langgraph_ecommerce_agent_service.resume(
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
        decision=decision,
    )

    return ApiResponse[dict](
        data=result
    )


@router.get(
    "/langgraph/ecommerce-agent/memories",
    response_model=ApiResponse[list[dict]],
)
async def list_ecommerce_agent_memories(
    tenant_id: str = "tenant_001",
    memory_type: str = "preferences",
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[dict]]:
    result = langgraph_ecommerce_agent_service.list_memories(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        memory_type=memory_type,
    )

    return ApiResponse[list[dict]](
        data=result
    )
```

---

# 二十、注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langgraph_ecommerce_agent import router as ecommerce_agent_router
```

注册：

```python
api_router.include_router(
    ecommerce_agent_router,
    tags=["Project 2 - LangGraph Ecommerce Agent"],
)
```

---

# 二十一、接口测试
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

## 1. 普通对话
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_001",
    "is_new_conversation": true,
    "question": "你好，介绍一下你能做什么？"
  }'
```

---

## 2. 缺订单号追问
第一轮：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_002",
    "is_new_conversation": true,
    "question": "帮我查一下订单。"
  }'
```

第二轮：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_002",
    "question": "订单号是 10002。"
  }'
```

---

## 3. 退款咨询
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_003",
    "is_new_conversation": true,
    "question": "我的订单 10002 还没发货，可以退款吗？"
  }'
```

---

## 4. 高风险退款
第一步，触发人工确认：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_004",
    "is_new_conversation": true,
    "question": "我的订单 10003 申请大额退款。"
  }'
```

第二步，查看状态：

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/state/conv_ecommerce_004" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

第三步，人工审批通过：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/resume" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: admin_001" \
  -H "x-username: admin" \
  -d '{
    "conversation_id": "conv_ecommerce_004",
    "type": "approve",
    "reason": "大额退款人工审核通过"
  }'
```

---

## 5. 记住用户偏好
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_ecommerce_005",
    "is_new_conversation": true,
    "question": "记住：以后回答客服问题，先给结论，再给处理步骤。"
  }'
```

查看记忆：

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/langgraph/ecommerce-agent/memories" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

---

# 二十二、前端调用协议设计
前端建议按三类状态展示。

## 普通完成态
```json
{
  "answer": "您的订单当前状态是：已付款，待发货。",
  "intent": "query_order",
  "need_human_confirm": false,
  "pending_action": null,
  "errors": []
}
```

---

## 缺参数追问态
```json
{
  "answer": "请您提供订单号，我才能继续查询订单状态。",
  "intent": "query_order",
  "order_id": null
}
```

---

## 人工审核态
```json
{
  "answer": "",
  "intent": "refund",
  "risk_level": "high",
  "need_human_confirm": true,
  "pending_action": "refund_order",
  "pending_payload": {
    "order_id": "10003",
    "amount": 1299.0,
    "currency": "CNY"
  }
}
```

前端可以展示：

```plain
1. 用户原始问题
2. 订单信息
3. 售后规则依据
4. 风险等级
5. 待执行动作
6. approve / reject / edit 按钮
```

---

# 二十三、生产环境改造建议
当前课程版用了：

```plain
InMemorySaver
InMemoryStore
Mock Order Service
Mock RAG
Mock Refund
```

生产环境应该替换为：

```plain
AsyncPostgresSaver
PostgresStore
真实订单系统
真实物流系统
真实退款系统
真实 RAG Service
真实权限系统
真实审计日志
```

推荐架构：

```plain
FastAPI
 ↓
EcommerceAgentService
 ↓
Compiled LangGraph
 ↓
AsyncPostgresSaver
 ↓
PostgreSQL checkpoint tables

Long-term Memory
 ↓
PostgresStore

Business Data
 ↓
orders / refunds / tool_call_logs / human_reviews
```

生产环境中，checkpointer 用于保存图执行状态，不应该替代业务表；业务订单、退款申请、人工审核记录仍然应该写入正式业务数据库。这个边界在前面 Persistence 和 HITL 章节已经反复强调。LangGraph 的 persistence 层负责 checkpoint 和恢复，业务审计要由业务系统自己保存。

---

# 二十四、这个项目怎么写进简历
可以写成：

```plain
项目名称：基于 LangGraph 的电商客服 Agent 系统

项目描述：
基于 FastAPI + LangChain + LangGraph 设计并实现电商客服 Agent，支持订单查询、物流查询、退款咨询、售后规则问答、多轮追问、状态持久化、高风险退款人工审核和客服回答安全审核。系统通过 StateGraph 将复杂客服流程拆分为多个可观测节点，并使用 Conditional Routing 控制不同业务分支，提高 Agent 流程的可控性和可维护性。

核心职责：
1. 设计 EcommerceAgentState，统一管理用户问题、意图、订单信息、RAG 结果、风险等级、人工审核状态和最终回答。
2. 基于 LangGraph Node / Edge 拆分客服处理流程，包括意图识别、订单查询、售后规则检索、风险评估、人工确认和回答审核。
3. 使用 checkpointer + thread_id 实现多轮会话状态持久化，支持缺订单号追问后继续原流程。
4. 使用 Store 实现用户长期偏好记忆，支持按 tenant_id / user_id / memory_type 做隔离。
5. 使用 interrupt + Command(resume) 实现高风险退款人工审核，支持 approve / reject / edit 三种审批方式。
6. 设计 Reviewer Node，对客服回答中的“保证退款”“立即到账”等过度承诺表达进行检查和改写。
7. 通过 FastAPI 封装 chat / state / resume / memories 接口，支持前端对话和人工审核后台接入。
```

---

# 二十五、项目难点和亮点怎么讲
## 亮点一：不是普通 ChatBot，而是状态机 Agent
```plain
这个项目不是简单把用户问题丢给大模型，而是用 LangGraph 把客服流程建模成一个可控状态机。

每一步都是一个 Node，比如 classify_intent、query_order、retrieve_policy、assess_risk、human_review、review_answer。

流程分支通过 Conditional Routing 显式控制，比如缺订单号就追问，退款问题就查售后规则，高风险退款就进入人工审核。
```

---

## 亮点二：支持多轮断点续聊
```plain
比如用户第一轮说“我要退款”，系统发现缺少订单号，就记录 intent=refund 并追问订单号。

用户第二轮只说“10002”，系统通过 thread_id 恢复上一轮 State，知道这是继续退款流程，而不是一个新的普通订单查询。
```

---

## 亮点三：高风险动作接入 HITL
```plain
退款属于高风险操作，所以我没有让 Agent 直接执行退款。

系统会先准备 pending_payload，再通过 assess_risk 判断风险。如果是大额退款或者非待发货订单退款，就进入 human_review_node，通过 interrupt 暂停图执行。

人工审核后再用 Command(resume) 恢复，可以 approve、reject 或 edit 参数。
```

---

## 亮点四：长期偏好记忆
```plain
用户明确要求“以后回答先给结论，再给步骤”时，系统会把这个偏好写入 Store。

后续对话开始时，recall_memory_node 会按 tenant_id 和 user_id 从 Store 召回偏好，再影响客服回答风格。
```

---

## 亮点五：客服回答安全审核
```plain
客服场景不能乱承诺，比如“保证退款”“立即到账”这类话术有风险。

所以我加了 review_answer_node，对回答进行规则审核。如果命中过度承诺表达，就进入 rewrite_answer_node 改写，最后再输出。
```

---

# 二十六、面试回答话术
## 回答一：项目整体怎么介绍
```plain
这个项目是一个基于 LangGraph 的电商客服 Agent。

它不是简单问答机器人，而是把客服业务流程拆成了一个可控状态机。用户进来后，系统会先召回用户偏好，再识别意图，然后根据意图走不同分支。

比如订单问题会进入订单查询节点，退款问题会先查订单，再检索售后规则，再做风险评估。如果缺订单号，会追问用户；如果是高风险退款，会通过 interrupt 暂停，等待人工审核后再继续执行。

整个流程通过 StateGraph 编排，State 里保存用户问题、意图、订单信息、RAG 结果、风险等级、人工审核状态和最终回答。
```

---

## 回答二：为什么用 LangGraph
```plain
我选择 LangGraph 是因为客服 Agent 不是一轮问答，而是复杂流程。

比如退款咨询要经过意图识别、订单查询、售后规则检索、风险评估、人工确认和最终回答。如果用普通 LangChain Agent，模型自由调用工具，流程不够可控。

LangGraph 可以把每一步显式拆成 Node，通过 Edge 和 Conditional Routing 控制流程。这样可观测、可恢复、可插入人工确认，也更适合企业级场景。
```

---

## 回答三：怎么做多轮续聊
```plain
多轮续聊主要依赖 LangGraph Persistence。

我会把业务 conversation_id 映射成 thread_id，比如 tenant_id:user_id:conversation_id。

Graph 编译时配置 checkpointer，调用时传 thread_id。这样每轮对话的 State 都会保存到同一个 thread 下。

比如用户第一轮说“我要退款”，系统追问订单号；第二轮用户只说“10002”，系统可以从 checkpoint 恢复上一轮 intent=refund，然后继续退款流程。
```

---

## 回答四：怎么做高风险退款人工确认
```plain
我把退款流程拆成 prepare_refund、assess_risk、human_review、execute_refund 几个节点。

assess_risk 会判断订单状态和退款金额。如果是大额退款或者订单已发货，就设置 need_human_confirm=True，并生成 pending_payload。

然后路由到 human_review_node，在里面调用 interrupt，把待审核信息返回给前端或后台。人工审核后用 Command(resume) 传回 approve、reject 或 edit。

如果 approve，就执行退款；如果 reject，就生成拒绝说明；如果 edit，就先修改参数，再执行退款。
```

---

## 回答五：怎么避免 Agent 乱回答
```plain
我主要做了三层控制。

第一层是流程控制。不是让模型自由发挥，而是用 LangGraph 明确每一步走什么节点。

第二层是知识依据。售后规则通过 RAG 节点检索，没命中就 fallback，不让模型硬编。

第三层是回答审核。最终回答进入 review_answer_node，检查是否有“保证退款”“立即到账”这类过度承诺表达。如果有，就进入 rewrite_answer_node 改写。
```

---

# 二十七、常见错误一：一上来就让大模型自由处理全部客服流程
错误：

```plain
用户问题 -> LLM -> 最终回答
```

问题：

```plain
流程不可控
工具调用不可控
风险动作不可控
多轮上下文不好恢复
难以审计
```

正确：

```plain
用户问题 -> StateGraph -> 多节点流程 -> Reviewer -> 最终回答
```

---

# 二十八、常见错误二：缺订单号还继续查订单
错误：

```plain
order_id=None 还调用 query_order
```

正确：

```plain
route_after_extract_order_id:
  没有 order_id -> ask_order_id
  有 order_id -> query_order
```

---

# 二十九、常见错误三：高风险退款不做人工确认
错误：

```plain
Agent 判断可以退款 -> 直接执行退款
```

正确：

```plain
prepare_refund
 ↓
assess_risk
 ↓
high risk -> interrupt
 ↓
人工 approve / reject / edit
 ↓
execute_refund
```

---

# 三十、常见错误四：把 checkpoint 当业务表
错误：

```plain
退款记录只存在 checkpoint 里
```

正确：

```plain
checkpoint 保存图执行状态；
refund_requests / human_reviews / tool_call_logs 保存正式业务记录。
```

---

# 三十一、常见错误五：Memory 乱写
错误：

```plain
用户随便说一句“今天回答短一点”，就长期记成用户永远喜欢短回答。
```

正确：

```plain
只有用户明确要求记住，或者多次稳定出现的偏好，才写入长期 Memory。
```

---

# 三十二、常见错误六：Reviewer 只做摆设
错误：

```plain
review_answer_node 永远返回通过。
```

正确：

```plain
至少检查：
1. 是否过度承诺
2. 是否缺少依据
3. 是否和订单状态冲突
4. 是否需要人工确认但没确认
```

---

# 三十三、常见错误七：恢复 HITL 时换 thread_id
错误：

```plain
start 使用 thread_001
resume 使用 thread_002
```

结果：

```plain
恢复不到原来的 interrupt。
```

正确：

```plain
同一个人工审核流程必须使用同一个 tenant_id:user_id:conversation_id 生成 thread_id。
```

---

# 三十四、生产级扩展清单
后续可以继续扩展：

```plain
1. 接入真实 ChatModel 做意图识别
2. 使用 Structured Output 输出 intent / order_id / risk_level
3. 接入真实订单系统
4. 接入真实物流系统
5. 接入真实 RAG Service
6. 使用 AsyncPostgresSaver 替换 InMemorySaver
7. 使用 PostgresStore 替换 InMemoryStore
8. 设计 tool_call_logs 表
9. 设计 human_reviews 表
10. 设计 agent_run_traces 表
11. 增加权限控制
12. 增加限流和成本统计
13. 增加 LangSmith / OpenTelemetry 观测
14. 增加前端审核后台
15. 增加灰度发布和回放测试
```

---

# 三十五、课后任务一：跑通普通问题
要求：

```plain
1. 运行 scripts/test_lg38_01_basic_chat.py
2. 查看 final_answer
3. 查看 logs
4. 画出普通问题执行路径
```

---

# 三十六、课后任务二：跑通缺订单号续聊
要求：

```plain
1. 运行 scripts/test_lg38_02_missing_order_id.py
2. 第一轮输入“帮我查一下订单”
3. 第二轮输入“订单号是 10002”
4. 查看是否用同一个 thread_id 继续流程
```

---

# 三十七、课后任务三：跑通退款规则查询
要求：

```plain
1. 运行 scripts/test_lg38_03_refund_policy.py
2. 查看 query_order 是否成功
3. 查看 retrieve_policy 是否命中
4. 查看 sources 是否返回
5. 说明 RAG 在这个流程里的作用
```

---

# 三十八、课后任务四：跑通 HITL 退款
要求：

```plain
1. 运行 scripts/test_lg38_04_hitl_refund.py
2. 查看第一次执行是否 interrupt
3. 查看 snapshot.values 中的 pending_payload
4. 测试 approve
5. 测试 edit
6. 查看 execute_refund 是否在 resume 后执行
```

---

# 三十九、课后任务五：跑通用户偏好记忆
要求：

```plain
1. 运行 scripts/test_lg38_05_memory_preference.py
2. 第一轮写入偏好
3. 第二轮查看 recalled_memories
4. 查看 Store 中保存的 memory
```

---

# 四十、课后任务六：跑通 Service
要求：

```plain
1. 运行 scripts/test_lg38_06_service.py
2. 查看第一轮缺订单号响应
3. 查看第二轮订单号补充响应
4. 查看 get_state 返回的当前 State
```

---

# 四十一、课后任务七：接入真实 RAG
要求：

```plain
1. 用第 27 章 RAG Service 替换 mock_retrieve_policy
2. policy_query 使用订单状态生成
3. RAG 命中返回 answer 和 sources
4. RAG 未命中进入 policy_fallback
```

---

# 四十二、课后任务八：接入真实订单 Tool
要求：

```plain
1. 用第 25 章 query_order_tool 替换 mock_query_order
2. 订单查询失败写入 errors
3. 订单不存在进入 order_not_found
4. 成功结果写入 order_info
```

---

# 四十三、课后任务九：增加 tool_call_logs
设计表：

```sql
CREATE TABLE tool_call_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(128),
    conversation_id VARCHAR(128),
    user_id VARCHAR(128),
    tool_name VARCHAR(128),
    tool_args JSONB,
    tool_result JSONB,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

要求：

```plain
1. query_order 记录一次 tool log
2. retrieve_policy 记录一次 tool log
3. execute_refund 记录一次 tool log
4. tool error 也必须记录
```

---

# 四十四、课后任务十：增加 human_reviews
设计表：

```sql
CREATE TABLE human_reviews (
    id BIGSERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(128) NOT NULL,
    reviewer_id VARCHAR(128) NOT NULL,
    decision_type VARCHAR(32) NOT NULL,
    reason TEXT,
    original_payload JSONB,
    edited_payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

要求：

```plain
1. approve 记录审核日志
2. reject 记录审核日志
3. edit 记录原始参数和修改后参数
4. 审核接口必须校验权限
```

---

# 四十五、课后任务十一：把 Reviewer 做得更强
要求检查：

```plain
1. 是否包含过度承诺
2. 是否引用了订单状态
3. 是否引用了售后规则
4. RAG 未命中时是否给确定结论
5. 高风险退款未审核时是否执行退款
```

---

# 四十六、课后任务十二：画完整流程图
要求画出：

```plain
普通问题路径
订单查询路径
缺订单号路径
退款咨询路径
高风险退款 HITL 路径
记忆写入路径
```

---

# 四十七、本章总结
## 【最终内容】
好了，到这里，第 38 章我们就完成了项目二：LangGraph 电商客服 Agent。

这一章是前面 LangGraph 阶段的第一次完整落地。

我们不是做一个简单 ChatBot，而是做了一个真正有业务流程的 Agent：

```plain
能识别意图
能查订单
能查物流
能检索售后规则
能缺参数追问
能多轮续聊
能记住用户偏好
能处理高风险退款人工确认
能审核客服回答
能通过 FastAPI 对外提供接口
```

这个项目最核心的价值是：

```plain
把客服 Agent 从“模型自由回答”
升级成“可控、可恢复、可审核、可追踪的业务状态机”。
```

大家要记住这个项目的核心链路：

```plain
State 负责保存上下文。
Node 负责处理具体步骤。
Conditional Routing 负责分支。
Persistence 负责多轮恢复。
Memory 负责用户偏好。
HITL 负责高风险动作确认。
Reviewer 负责回答安全。
FastAPI 负责工程接口。
```

这就是一个能写进简历、也能在面试里讲清楚的 AI Agent 项目。

---
