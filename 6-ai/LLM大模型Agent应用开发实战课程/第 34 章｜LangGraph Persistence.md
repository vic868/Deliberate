---

# 一、本章定位
前面我们已经完成 LangGraph 的基础部分：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
```

现在我们已经能写出一个比较完整的电商客服图：

```plain
识别意图
 ↓
提取订单号
 ↓
查询订单
 ↓
检索售后规则
 ↓
判断风险
 ↓
人工确认 / 生成回答
```

但是到目前为止，我们的图还有一个问题：

# 图执行完就结束了
比如用户问：

```plain
我要退款。
```

系统发现缺少订单号，于是回答：

```plain
请您提供订单号，我才能继续查询。
```

用户下一轮补充：

```plain
订单号是 10002。
```

如果没有持久化，系统可能不知道上一轮为什么问订单号，也不知道当前流程执行到哪里。

所以我们需要：

# Persistence
也就是：

```plain
把图的 State 保存下来，
下一轮可以继续用。
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Persistence 到底解决什么问题
2. Checkpoint 是什么
3. Thread 是什么
4. thread_id 为什么重要
5. InMemorySaver 怎么用
6. 同一个 thread_id 如何保留状态
7. 不同 thread_id 如何隔离状态
8. Checkpoint 和 State 的关系
9. get_state 怎么查看当前状态
10. get_state_history 怎么查看历史状态
11. update_state 怎么人工修改状态
12. Time Travel 是什么
13. Human-in-the-loop 为什么必须依赖 Persistence
14. InMemorySaver 为什么不能用于生产
15. PostgresSaver 怎么用
16. AsyncPostgresSaver 怎么用
17. Postgres checkpointer 为什么要 setup
18. thread_id 和 conversation_id 怎么设计
19. State 里哪些内容适合 checkpoint
20. State 里哪些内容不适合 checkpoint
21. 电商客服 Agent 如何实现断点续聊
22. 项目一如何接入 LangGraph Persistence
23. 面试中如何讲 LangGraph Persistence
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

安装基础依赖：

```bash
uv add "langgraph>=1.2,<1.3" \
       "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6"
```

本章如果要演示 PostgreSQL checkpointer，再安装：

```bash
uv add "langgraph-checkpoint-postgres" "psycopg[binary,pool]"
```

本章主要用到：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
```

`InMemorySaver` 适合调试和测试；生产环境更适合使用 `PostgresSaver` 或 `AsyncPostgresSaver` 这类持久化 checkpointer。LangGraph checkpoint 参考文档也把 `InMemorySaver` 标注为 debugging / testing only，把 Postgres checkpointer 标注为生产工作负载可用。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langgraph_persistence/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── graph_factory.py
│   │   ├── service.py
│   │   ├── demo_01_inmemory_saver.py
│   │   ├── demo_02_thread_id_isolation.py
│   │   ├── demo_03_get_state.py
│   │   ├── demo_04_state_history.py
│   │   ├── demo_05_update_state.py
│   │   ├── demo_06_chat_memory.py
│   │   ├── demo_07_ecommerce_resume.py
│   │   ├── demo_08_postgres_saver.py
│   │   ├── demo_09_async_postgres_saver.py
│   │   └── demo_10_persistence_api_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langgraph_persistence.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg34_01_inmemory_saver.py
│   ├── test_lg34_02_thread_id_isolation.py
│   ├── test_lg34_03_get_state.py
│   ├── test_lg34_04_state_history.py
│   ├── test_lg34_05_update_state.py
│   ├── test_lg34_06_chat_memory.py
│   ├── test_lg34_07_ecommerce_resume.py
│   ├── test_lg34_08_postgres_saver.py
│   ├── test_lg34_09_async_postgres_saver.py
│   └── test_lg34_10_persistence_service.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 34 章。

这一章我们讲 LangGraph Persistence。

Persistence 翻译过来就是持久化。

它解决的问题非常关键：

Agent 执行过程不能只存在内存里，它要能保存、恢复、继续和追踪。

比如一个客服 Agent：

用户第一轮说：

```plain
我要退款。
```

系统说：

```plain
请提供订单号。
```

用户第二轮说：

```plain
订单号是 10002。
```

如果没有持久化，第二轮系统可能只看到“订单号是 10002”，不知道上一轮是在处理退款。

但如果有 Persistence，系统可以知道：

```plain
上一轮 intent=refund
上一轮缺少 order_id
当前用户补充了 order_id=10002
所以继续退款流程
```

这就是 Persistence 的价值。

---

# 六、02｜Persistence 一句话解释
## 【实操】
```plain
Persistence
=
把 Graph 的 State 保存成 Checkpoint
```

再展开：

```plain
Graph 每执行一步
 ↓
保存一次 State Snapshot
 ↓
按照 thread_id 归档
 ↓
下一次用同一个 thread_id 继续执行
```

---

## 【重点内容】
大家可以先这样理解。

LangGraph Persistence 就是：

```plain
保存图运行过程中的状态快照。
```

这个快照叫：

```plain
Checkpoint
```

多个 checkpoint 归属于一个：

```plain
Thread
```

Thread 用：

```plain
thread_id
```

区分。

比如：

```plain
用户 u_10001 的会话 c_abc123
```

可以生成：

```plain
thread_id = u_10001:c_abc123
```

这样用户下一轮继续对话时，图可以从这个 thread 里恢复状态。

---

# 七、03｜为什么复杂 Agent 必须持久化
复杂 Agent 会遇到这些场景：

```plain
1. 多轮对话
2. 用户补充信息
3. 缺参数追问
4. 人工审批
5. 高风险工具确认
6. 工具失败后重试
7. 服务中断后恢复
8. 执行过程审计
9. 调试历史步骤
10. 从某个 checkpoint 重新执行
```

没有 Persistence，这些都很难做稳。

---

## 【重点内容】
普通 Chat 可以不关心这么多。

但企业 Agent 不一样。

比如退款流程执行到一半，需要人工确认。

这个时候系统不能丢掉上下文。

它要保存：

```plain
用户问题
订单号
订单状态
退款规则
风险等级
待确认动作
执行到哪个节点
```

等人工确认后，再继续执行。

这就必须依赖 Persistence。

LangGraph 官方 Persistence 文档也明确说明，持久化层可以支撑 Human-in-the-loop、conversational memory、time travel debugging 和 fault-tolerant execution。

---

# 八、04｜Checkpoint 是什么
## 【实操】
```plain
Checkpoint
=
某一个时间点的 Graph State 快照
```

例如：

```json
{
  "user_question": "我的订单 10002 可以退款吗？",
  "intent": "refund",
  "order_id": "10002",
  "order_info": {
    "status": "paid",
    "status_text": "已付款，待发货"
  },
  "final_answer": ""
}
```

---

## 【重点内容】
Checkpoint 就是状态快照。

Graph 每执行到一个关键步骤，就会保存一次状态。

比如：

```plain
输入状态保存一次
classify_intent 后保存一次
extract_order_id 后保存一次
query_order 后保存一次
retrieve_policy 后保存一次
generate_answer 后保存一次
```

这些历史状态可以用来调试、恢复和回放。

官方文档里把 checkpoint 描述为某个 thread 在某个时间点的状态快照，并且它会在 super-step 边界创建。

---

# 九、05｜Thread 是什么
## 【实操】
```plain
Thread
=
一组 Checkpoint 的归属容器
=
一次会话 / 一条任务线
```

示例：

```plain
thread_id = user_id + conversation_id
```

比如：

```plain
u_10001:conv_abc123
```

---

## 【重点内容】
Thread 不是操作系统线程。

在 LangGraph 里，Thread 可以理解成一条会话线。

同一个 thread_id 下，会保存这个图的一系列 checkpoint。

比如用户和客服 Agent 的一次会话，就可以对应一个 thread。

只要后续请求继续用同一个 thread_id，就能读到之前的状态。

如果换一个 thread_id，就相当于新开一条会话。

官方 checkpoint 参考文档也说明，Thread 是由唯一 `thread_id` 标识的一系列 checkpoint；使用 checkpointer 时运行图必须指定 `thread_id`，也可以可选指定 `checkpoint_id`。

---

# 十、06｜thread_id 怎么设计
推荐：

```plain
thread_id = tenant_id:user_id:conversation_id
```

示例：

```python
def build_thread_id(
    tenant_id: str,
    user_id: str,
    conversation_id: str,
) -> str:
    return f"{tenant_id}:{user_id}:{conversation_id}"
```

不推荐：

```plain
thread_id = "1"
thread_id = user_id
thread_id = random 每次随机
```

---

## 【重点内容】
thread_id 设计非常重要。

如果多个用户共用同一个 thread_id，状态会串。

如果每次请求都用新 thread_id，就没有记忆。

所以它最好和业务会话绑定。

比如我们项目一已经有：

```plain
session_id
conversation_id
```

那就可以把它映射成 LangGraph 的 thread_id。

---

# 十一、07｜创建目录
执行：

```bash
mkdir -p app/langgraph_persistence

touch app/langgraph_persistence/__init__.py
touch app/langgraph_persistence/schemas.py
touch app/langgraph_persistence/graph_factory.py
touch app/langgraph_persistence/service.py
touch app/langgraph_persistence/demo_01_inmemory_saver.py
touch app/langgraph_persistence/demo_02_thread_id_isolation.py
touch app/langgraph_persistence/demo_03_get_state.py
touch app/langgraph_persistence/demo_04_state_history.py
touch app/langgraph_persistence/demo_05_update_state.py
touch app/langgraph_persistence/demo_06_chat_memory.py
touch app/langgraph_persistence/demo_07_ecommerce_resume.py
touch app/langgraph_persistence/demo_08_postgres_saver.py
touch app/langgraph_persistence/demo_09_async_postgres_saver.py
touch app/langgraph_persistence/demo_10_persistence_api_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_persistence

New-Item app\langgraph_persistence\__init__.py
New-Item app\langgraph_persistence\schemas.py
New-Item app\langgraph_persistence\graph_factory.py
New-Item app\langgraph_persistence\service.py
New-Item app\langgraph_persistence\demo_01_inmemory_saver.py
New-Item app\langgraph_persistence\demo_02_thread_id_isolation.py
New-Item app\langgraph_persistence\demo_03_get_state.py
New-Item app\langgraph_persistence\demo_04_state_history.py
New-Item app\langgraph_persistence\demo_05_update_state.py
New-Item app\langgraph_persistence\demo_06_chat_memory.py
New-Item app\langgraph_persistence\demo_07_ecommerce_resume.py
New-Item app\langgraph_persistence\demo_08_postgres_saver.py
New-Item app\langgraph_persistence\demo_09_async_postgres_saver.py
New-Item app\langgraph_persistence\demo_10_persistence_api_adapter.py
```

---

# 十二、08｜准备公共 State
打开：

```plain
app/langgraph_persistence/schemas.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PersistenceState(TypedDict):
    user_question: str
    messages: Annotated[list[AnyMessage], add_messages]

    intent: Literal[
        "general",
        "refund",
        "query_order",
        "human_service",
        "unknown",
    ]

    order_id: str | None
    order_status: str | None
    policy_answer: str | None

    need_user_input: bool
    waiting_for: str | None

    final_answer: str
    is_finished: bool

    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
```

再写一个初始化函数：

```python
from langchain_core.messages import HumanMessage

from app.langgraph_persistence.schemas import PersistenceState


def create_initial_state(
    user_question: str,
) -> PersistenceState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "intent": "unknown",

        "order_id": None,
        "order_status": None,
        "policy_answer": None,

        "need_user_input": False,
        "waiting_for": None,

        "final_answer": "",
        "is_finished": False,

        "logs": [],
        "errors": [],
    }
```

---

## 【重点内容】
这个 State 比之前简化了一点，主要为了演示 Persistence。

重点字段有：

```plain
messages：多轮消息
intent：意图
order_id：订单号
need_user_input：是否等待用户补充
waiting_for：当前等待什么
logs：执行日志
```

这些字段会被 checkpoint 保存。

下一轮用同一个 thread_id 调用时，这些状态还在。

---

# 十三、09｜准备 Graph Factory
打开：

```plain
app/langgraph_persistence/graph_factory.py
```

写入：

```python
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.langgraph_persistence.schemas import PersistenceState


def classify_intent_node(state: PersistenceState) -> dict:
    question = state["user_question"]

    if "退款" in question or state.get("intent") == "refund":
        intent = "refund"
    elif "订单" in question:
        intent = "query_order"
    elif "人工" in question:
        intent = "human_service"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：intent={intent}"],
    }


def extract_order_id_node(state: PersistenceState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    else:
        order_id = state.get("order_id")

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


def route_after_extract_order_id(
    state: PersistenceState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: PersistenceState) -> dict:
    answer = "请您提供订单号，我才能继续处理退款申请。"

    return {
        "need_user_input": True,
        "waiting_for": "order_id",
        "final_answer": answer,
        "is_finished": False,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["ask_order_id：等待用户补充订单号"],
    }


def query_order_node(state: PersistenceState) -> dict:
    order_id = state["order_id"]

    if order_id == "10001":
        order_status = "已发货"
    elif order_id == "10002":
        order_status = "已付款，待发货"
    else:
        order_status = "未查询到订单"

    return {
        "order_status": order_status,
        "need_user_input": False,
        "waiting_for": None,
        "logs": [f"query_order：order_status={order_status}"],
    }


def retrieve_policy_node(state: PersistenceState) -> dict:
    order_status = state["order_status"]

    if order_status == "已付款，待发货":
        policy_answer = "根据售后规则，订单未发货时可以申请取消订单并退款。"
    elif order_status == "已发货":
        policy_answer = "根据售后规则，订单已发货后，需要收到商品后再发起退货退款申请。"
    else:
        policy_answer = "当前订单状态无法确认退款规则，建议联系人工客服。"

    return {
        "policy_answer": policy_answer,
        "logs": ["retrieve_policy：完成售后规则判断"],
    }


def generate_answer_node(state: PersistenceState) -> dict:
    answer = (
        f"您的订单当前状态是：{state['order_status']}。"
        f"{state['policy_answer']}"
    )

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["generate_answer：最终回答完成"],
    }


def build_persistence_graph(
    checkpointer=None,
):
    graph = StateGraph(PersistenceState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "extract_order_id")

    graph.add_conditional_edges(
        "extract_order_id",
        route_after_extract_order_id,
        {
            "ask_order_id": "ask_order_id",
            "query_order": "query_order",
        },
    )

    graph.add_edge("query_order", "retrieve_policy")
    graph.add_edge("retrieve_policy", "generate_answer")

    graph.add_edge("ask_order_id", END)
    graph.add_edge("generate_answer", END)

    return graph.compile(checkpointer=checkpointer)


def build_memory_graph():
    checkpointer = InMemorySaver()

    return build_persistence_graph(
        checkpointer=checkpointer,
    )


def add_user_message_to_state(
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
这个 graph_factory 是本章核心。

它模拟一个“退款流程”。

如果用户没有订单号，就走：

```plain
ask_order_id
```

并把 State 写成：

```plain
need_user_input=True
waiting_for=order_id
intent=refund
```

下一轮用户补充订单号时，只要用同一个 thread_id，Graph 就能拿到之前的 intent 和等待状态。

这就是断点续聊的基础。

---

# 十四、10｜示例一：InMemorySaver 最小使用
打开：

```plain
app/langgraph_persistence/demo_01_inmemory_saver.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import build_memory_graph
from app.langgraph_persistence.schemas import create_initial_state


def main():
    app = build_memory_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg34_demo_001"
        }
    }

    result = app.invoke(
        create_initial_state("我的订单 10002 可以退款吗？"),
        config=config,
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_01_inmemory_saver.py
```

写入：

```python
from app.langgraph_persistence.demo_01_inmemory_saver import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg34_01_inmemory_saver.py
```

---

## 【重点内容】
这个例子只是在 compile 的时候传了：

```python
checkpointer = InMemorySaver()
```

然后 invoke 时传：

```python
config = {
    "configurable": {
        "thread_id": "thread_lg34_demo_001"
    }
}
```

这两个东西配合起来，LangGraph 就会保存这个 thread 的 checkpoints。

注意：

```plain
没有 checkpointer，就没有持久化。
没有 thread_id，就不知道状态保存到哪条会话。
```

---

# 十五、11｜示例二：thread_id 隔离状态
打开：

```plain
app/langgraph_persistence/demo_02_thread_id_isolation.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import build_memory_graph
from app.langgraph_persistence.schemas import create_initial_state


def run_once(app, thread_id: str, question: str):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = app.invoke(
        create_initial_state(question),
        config=config,
    )

    print("thread_id:", thread_id)
    print("question:", question)
    print("intent:", result["intent"])
    print("order_id:", result["order_id"])
    print("final_answer:", result["final_answer"])
    print("=" * 80)


def main():
    app = build_memory_graph()

    run_once(
        app,
        "thread_user_a",
        "我的订单 10002 可以退款吗？",
    )

    run_once(
        app,
        "thread_user_b",
        "我的订单 10001 可以退款吗？",
    )


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_02_thread_id_isolation.py
```

写入：

```python
from app.langgraph_persistence.demo_02_thread_id_isolation import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示 thread_id 隔离。

同一个 app。

两个不同 thread_id：

```plain
thread_user_a
thread_user_b
```

它们的 State 不会串。

真实项目里，不同用户、不同会话必须用不同 thread_id。

否则就会出现 A 用户看到 B 用户上下文的问题。

这在企业项目里是严重事故。

---

# 十六、12｜示例三：get_state 查看当前状态
打开：

```plain
app/langgraph_persistence/demo_03_get_state.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import build_memory_graph
from app.langgraph_persistence.schemas import create_initial_state


def main():
    app = build_memory_graph()

    config = {
        "configurable": {
            "thread_id": "thread_get_state_demo"
        }
    }

    app.invoke(
        create_initial_state("我的订单 10002 可以退款吗？"),
        config=config,
    )

    snapshot = app.get_state(config)

    print("snapshot values:")
    print(snapshot.values)

    print("=" * 80)
    print("next:")
    print(snapshot.next)

    print("=" * 80)
    print("config:")
    print(snapshot.config)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_03_get_state.py
```

写入：

```python
from app.langgraph_persistence.demo_03_get_state import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
`get_state` 可以查看某个 thread 当前最新的 StateSnapshot。

重点看：

```plain
snapshot.values
snapshot.next
snapshot.config
```

`values` 是状态值。

`next` 可以理解成后续待执行节点。

`config` 里会包含当前 checkpoint 的配置。

调试 Agent 时非常有用。

---

# 十七、13｜示例四：get_state_history 查看历史状态
打开：

```plain
app/langgraph_persistence/demo_04_state_history.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import build_memory_graph
from app.langgraph_persistence.schemas import create_initial_state


def main():
    app = build_memory_graph()

    config = {
        "configurable": {
            "thread_id": "thread_history_demo"
        }
    }

    app.invoke(
        create_initial_state("我的订单 10002 可以退款吗？"),
        config=config,
    )

    history = list(app.get_state_history(config))

    print("checkpoint count:", len(history))
    print("=" * 80)

    for index, snapshot in enumerate(history, start=1):
        print("snapshot:", index)
        print("checkpoint config:", snapshot.config)
        print("next:", snapshot.next)

        values = snapshot.values
        print("intent:", values.get("intent"))
        print("order_id:", values.get("order_id"))
        print("order_status:", values.get("order_status"))
        print("final_answer:", values.get("final_answer"))
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_04_state_history.py
```

写入：

```python
from app.langgraph_persistence.demo_04_state_history import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子可以看到每一步的历史状态。

这对调试非常有用。

比如你可以看到：

```plain
classify_intent 后 intent 是什么
extract_order_id 后 order_id 是什么
query_order 后 order_status 是什么
generate_answer 后 final_answer 是什么
```

以后 Agent 答错时，不要只看最终结果。

要看历史 checkpoint。

官方 Persistence 文档也介绍了通过状态历史查看和调试图执行过程，这也是 Time Travel 的基础。

---

# 十八、14｜示例五：update_state 人工修正状态
打开：

```plain
app/langgraph_persistence/demo_05_update_state.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import build_memory_graph
from app.langgraph_persistence.schemas import create_initial_state


def main():
    app = build_memory_graph()

    config = {
        "configurable": {
            "thread_id": "thread_update_state_demo"
        }
    }

    app.invoke(
        create_initial_state("我要退款，但是忘记订单号了。"),
        config=config,
    )

    before = app.get_state(config)

    print("before:")
    print(before.values)

    print("=" * 80)

    updated_config = app.update_state(
        config,
        {
            "order_id": "10002",
            "logs": ["manual_update：人工补充 order_id=10002"],
        },
    )

    print("updated_config:")
    print(updated_config)

    print("=" * 80)

    after = app.get_state(config)

    print("after:")
    print(after.values)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_05_update_state.py
```

写入：

```python
from app.langgraph_persistence.demo_05_update_state import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
`update_state` 可以手动修改 thread 的状态。

这个能力非常适合：

```plain
人工修正
调试
审批后写入结果
从外部系统回调更新状态
```

比如 Agent 提取订单号失败了，人工客服可以在后台补充：

```plain
order_id=10002
```

然后让图继续执行。

不过生产环境一定要做好权限和审计。

不是谁都能改 State。

---

# 十九、15｜示例六：多轮 Chat Memory
打开：

```plain
app/langgraph_persistence/demo_06_chat_memory.py
```

写入：

```python
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class ChatMemoryState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def chat_node(state: ChatMemoryState) -> dict:
    last_message = state["messages"][-1]

    history_count = len(state["messages"])

    return {
        "messages": [
            AIMessage(
                content=(
                    f"我收到了：{last_message.content}。"
                    f"当前 thread 里一共有 {history_count} 条历史消息。"
                )
            )
        ]
    }


def build_graph():
    graph = StateGraph(ChatMemoryState)

    graph.add_node("chat", chat_node)

    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_chat_memory_demo"
        }
    }

    first = app.invoke(
        {
            "messages": [
                HumanMessage(content="我叫大伟。")
            ]
        },
        config=config,
    )

    print("first:")
    for message in first["messages"]:
        print(message.type, ":", message.content)

    print("=" * 80)

    second = app.invoke(
        {
            "messages": [
                HumanMessage(content="你还记得我刚才说了什么吗？")
            ]
        },
        config=config,
    )

    print("second:")
    for message in second["messages"]:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_06_chat_memory.py
```

写入：

```python
from app.langgraph_persistence.demo_06_chat_memory import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示多轮 Chat Memory。

关键有两个：

```plain
messages 使用 add_messages
两次 invoke 使用同一个 thread_id
```

这样第二轮执行时，State 里还会有第一轮的 messages。

LangChain 的短期记忆文档也说明，短期记忆是 agent state 的一部分，通过 checkpointer 持久化后，同一个 thread 可以在交互之间恢复上下文。

---

# 二十、16｜示例七：电商客服断点续聊
打开：

```plain
app/langgraph_persistence/demo_07_ecommerce_resume.py
```

写入：

```python
from langgraph.checkpoint.memory import InMemorySaver

from app.langgraph_persistence.graph_factory import (
    add_user_message_to_state,
    build_persistence_graph,
)
from app.langgraph_persistence.schemas import create_initial_state


def main():
    checkpointer = InMemorySaver()

    app = build_persistence_graph(
        checkpointer=checkpointer,
    )

    config = {
        "configurable": {
            "thread_id": "thread_ecommerce_resume_demo"
        }
    }

    first_result = app.invoke(
        create_initial_state("我要退款。"),
        config=config,
    )

    print("first_result:")
    print("final_answer:", first_result["final_answer"])
    print("intent:", first_result["intent"])
    print("need_user_input:", first_result["need_user_input"])
    print("waiting_for:", first_result["waiting_for"])
    print("order_id:", first_result["order_id"])
    print("=" * 80)

    second_result = app.invoke(
        add_user_message_to_state("订单号是 10002。"),
        config=config,
    )

    print("second_result:")
    print("final_answer:", second_result["final_answer"])
    print("intent:", second_result["intent"])
    print("need_user_input:", second_result["need_user_input"])
    print("waiting_for:", second_result["waiting_for"])
    print("order_id:", second_result["order_id"])
    print("order_status:", second_result["order_status"])

    print("=" * 80)
    print("messages:")
    for message in second_result["messages"]:
        print(message.type, ":", message.content)

    print("=" * 80)
    print("logs:")
    for log in second_result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_07_ecommerce_resume.py
```

写入：

```python
from app.langgraph_persistence.demo_07_ecommerce_resume import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这是本章最重要的例子。

第一轮用户只说：

```plain
我要退款。
```

Graph 没找到订单号，于是保存状态：

```plain
intent=refund
need_user_input=True
waiting_for=order_id
```

第二轮用户说：

```plain
订单号是 10002。
```

因为使用同一个 thread_id，Graph 还记得上一轮 intent 是 refund。

所以它可以继续走退款流程，而不是把“订单号是 10002”当成一个孤立问题。

这就是 Persistence 在业务里的价值。

---

# 二十一、17｜InMemorySaver 的限制
`InMemorySaver` 的特点：

```plain
1. 简单
2. 不需要数据库
3. 适合本地测试
4. 进程重启数据会丢
5. 不适合生产环境
```

---

## 【重点内容】
InMemorySaver 只适合教学和本地 Demo。

为什么？

因为它保存在内存里。

服务一重启，状态就没了。

多实例部署时，每个实例内存也不一样。

真实生产环境要用数据库型 checkpointer。

最常见就是 PostgreSQL。

---

# 二十二、18｜PostgresSaver 同步版本
打开：

```plain
app/langgraph_persistence/demo_08_postgres_saver.py
```

写入：

```python
from langgraph.checkpoint.postgres import PostgresSaver

from app.langgraph_persistence.graph_factory import build_persistence_graph
from app.langgraph_persistence.schemas import create_initial_state


DB_URI = "postgresql://postgres:postgres@localhost:5432/ai_agent?sslmode=disable"


def main():
    config = {
        "configurable": {
            "thread_id": "thread_postgres_demo_001"
        }
    }

    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # 第一次使用时需要执行 setup。
        # 生产环境不要每次请求都执行，可以放到启动脚本或迁移流程里。
        checkpointer.setup()

        app = build_persistence_graph(
            checkpointer=checkpointer,
        )

        result = app.invoke(
            create_initial_state("我的订单 10002 可以退款吗？"),
            config=config,
        )

        print("final_answer:")
        print(result["final_answer"])

        snapshot = app.get_state(config)

        print("=" * 80)
        print("checkpoint config:")
        print(snapshot.config)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg34_08_postgres_saver.py
```

写入：

```python
from app.langgraph_persistence.demo_08_postgres_saver import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子使用 PostgresSaver。

真实项目里，你的 checkpoint 不应该只存在内存里。

应该保存到 PostgreSQL。

注意：

```python
checkpointer.setup()
```

首次使用时需要调用，用来创建或迁移 checkpoint 相关表结构。

Postgres checkpointer 文档也明确提醒，第一次使用时要调用 `.setup()`；如果手动创建 psycopg 连接，还需要注意 `autocommit=True` 和 `row_factory=dict_row`。

---

# 二十三、19｜AsyncPostgresSaver 异步版本
FastAPI 项目更常用异步版本。

打开：

```plain
app/langgraph_persistence/demo_09_async_postgres_saver.py
```

写入：

```python
import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.langgraph_persistence.graph_factory import build_persistence_graph
from app.langgraph_persistence.schemas import create_initial_state


DB_URI = "postgresql://postgres:postgres@localhost:5432/ai_agent?sslmode=disable"


async def main():
    config = {
        "configurable": {
            "thread_id": "thread_async_postgres_demo_001"
        }
    }

    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # 第一次使用时需要执行 setup。
        # 生产环境建议放到启动初始化或部署迁移流程中。
        await checkpointer.setup()

        app = build_persistence_graph(
            checkpointer=checkpointer,
        )

        result = await app.ainvoke(
            create_initial_state("我的订单 10002 可以退款吗？"),
            config=config,
        )

        print("final_answer:")
        print(result["final_answer"])

        snapshot = await app.aget_state(config)

        print("=" * 80)
        print("checkpoint config:")
        print(snapshot.config)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```plain
scripts/test_lg34_09_async_postgres_saver.py
```

写入：

```python
import asyncio

from app.langgraph_persistence.demo_09_async_postgres_saver import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
FastAPI 项目里，推荐用：

```python
AsyncPostgresSaver
```

因为我们的接口大多是 async。

官方参考文档里，AsyncPostgresSaver 的导入路径是：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
```

并且使用：

```python
async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    await checkpointer.setup()
```

这个写法更适合异步服务。

---

# 二十四、20｜Postgres checkpointer 表设计理解
我们不用手写 checkpoint 表。

`setup()` 会帮我们创建需要的表。

但是你要知道它大概保存什么：

```plain
thread_id
checkpoint_id
checkpoint namespace
state channel values
metadata
pending writes
created_at
```

这些数据是 LangGraph 用来恢复和回放状态的。

---

## 【重点内容】
这里不要把 LangGraph checkpoint 表当成业务表。

它是图执行状态表。

业务表还是业务表。

比如：

```plain
chat_messages
orders
refund_requests
tool_call_logs
```

这些还是我们自己设计。

Checkpoint 负责让图能恢复。

业务数据库负责业务数据持久化。

两者不要混在一起。

---

# 二十五、21｜Persistence 和项目一的关系
第 19 章项目一里有：

```plain
session_id
message_id
conversation_id
PostgreSQL message 记录
Redis 缓存
```

引入 LangGraph Persistence 后，可以这样设计：

```plain
conversation_id
 ↓
生成 thread_id
 ↓
Graph invoke 传 config
 ↓
checkpointer 保存 State
 ↓
PostgreSQL 保存业务消息和审计日志
```

示例：

```python
def build_thread_id(
    tenant_id: str,
    user_id: str,
    conversation_id: str,
) -> str:
    return f"{tenant_id}:{user_id}:{conversation_id}"
```

---

## 【重点内容】
项目一里的会话 ID 可以和 LangGraph thread_id 关联起来。

比如：

```plain
conversation_id = c_abc123
user_id = u_10001
tenant_id = t_001
```

生成：

```plain
thread_id = t_001:u_10001:c_abc123
```

这样一来：

```plain
业务消息存在 chat_messages 表
Graph 状态存在 checkpoint 表
两者通过 conversation_id / thread_id 关联
```

这是比较清晰的企业级设计。

---

# 二十六、22｜封装 Persistence Service
打开：

```plain
app/langgraph_persistence/service.py
```

写入：

```python
from app.langgraph_persistence.graph_factory import (
    add_user_message_to_state,
    build_memory_graph,
)
from app.langgraph_persistence.schemas import create_initial_state


class LangGraphPersistenceService:
    def __init__(self):
        # 教学版使用内存 checkpointer。
        # 生产环境应该替换成 PostgresSaver / AsyncPostgresSaver。
        self.graph = build_memory_graph()

    def build_thread_id(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> str:
        return f"{tenant_id}:{user_id}:{conversation_id}"

    def build_config(
        self,
        thread_id: str,
    ) -> dict:
        return {
            "configurable": {
                "thread_id": thread_id
            }
        }

    def start_refund_flow(
        self,
        user_question: str,
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

        return self.graph.invoke(
            create_initial_state(user_question),
            config=config,
        )

    def continue_flow(
        self,
        user_question: str,
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

        return self.graph.invoke(
            add_user_message_to_state(user_question),
            config=config,
        )

    def get_current_state(
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

        snapshot = self.graph.get_state(config)

        return {
            "thread_id": thread_id,
            "values": snapshot.values,
            "next": snapshot.next,
            "config": snapshot.config,
        }


langgraph_persistence_service = LangGraphPersistenceService()
```

---

## 【重点内容】
这里我们封装了一个 Service。

它做了几件事：

```plain
1. 创建 graph
2. 生成 thread_id
3. 创建 config
4. 启动流程
5. 继续流程
6. 查看当前 State
```

Router 不应该直接拼 thread_id。

Graph 执行细节也不应该散落在接口里。

统一放到 Service 里。

---

# 二十七、23｜测试 Persistence Service
创建：

```plain
scripts/test_lg34_10_persistence_service.py
```

写入：

```python
from app.langgraph_persistence.service import langgraph_persistence_service


def main():
    tenant_id = "tenant_001"
    user_id = "u_10001"
    conversation_id = "conv_refund_001"

    first = langgraph_persistence_service.start_refund_flow(
        user_question="我要退款。",
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("first:")
    print("final_answer:", first["final_answer"])
    print("intent:", first["intent"])
    print("waiting_for:", first["waiting_for"])
    print("=" * 80)

    second = langgraph_persistence_service.continue_flow(
        user_question="订单号是 10002。",
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("second:")
    print("final_answer:", second["final_answer"])
    print("intent:", second["intent"])
    print("order_id:", second["order_id"])
    print("order_status:", second["order_status"])
    print("=" * 80)

    current = langgraph_persistence_service.get_current_state(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("current state:")
    print(current["values"])


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg34_10_persistence_service.py
```

---

# 二十八、24｜创建 Persistence API
创建：

```plain
app/api/v1/langgraph_persistence.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langgraph_persistence.service import langgraph_persistence_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class PersistenceChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")


@router.post(
    "/langgraph/persistence/chat",
    response_model=ApiResponse[dict],
)
async def persistence_chat(
    request: PersistenceChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langgraph_persistence_service.continue_flow(
        user_question=request.question,
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
    )

    return ApiResponse[dict](
        data={
            "answer": result["final_answer"],
            "intent": result["intent"],
            "order_id": result["order_id"],
            "order_status": result["order_status"],
            "need_user_input": result["need_user_input"],
            "waiting_for": result["waiting_for"],
            "logs": result["logs"],
        }
    )


@router.get(
    "/langgraph/persistence/state/{conversation_id}",
    response_model=ApiResponse[dict],
)
async def get_persistence_state(
    conversation_id: str,
    tenant_id: str = "tenant_001",
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langgraph_persistence_service.get_current_state(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )

    return ApiResponse[dict](
        data=result
    )
```

---

# 二十九、25｜注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langgraph_persistence import router as langgraph_persistence_router
```

注册：

```python
api_router.include_router(
    langgraph_persistence_router,
    tags=["LangGraph Persistence"],
)
```

---

# 三十、26｜测试 Persistence API
启动：

```bash
uv run uvicorn app.main:app --reload
```

第一轮：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/persistence/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_refund_001",
    "question": "我要退款。"
  }'
```

预期：

```json
{
  "answer": "请您提供订单号，我才能继续处理退款申请。",
  "intent": "refund",
  "order_id": null,
  "need_user_input": true,
  "waiting_for": "order_id"
}
```

第二轮：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/persistence/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_refund_001",
    "question": "订单号是 10002。"
  }'
```

预期：

```json
{
  "answer": "您的订单当前状态是：已付款，待发货。根据售后规则，订单未发货时可以申请取消订单并退款。",
  "intent": "refund",
  "order_id": "10002",
  "order_status": "已付款，待发货",
  "need_user_input": false,
  "waiting_for": null
}
```

查看状态：

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/langgraph/persistence/state/conv_refund_001" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

---

# 三十一、27｜Persistence 和 Human-in-the-loop 的关系
Human-in-the-loop 需要暂停和恢复。

暂停时必须保存：

```plain
当前 State
当前 next node
待确认动作
工具参数
用户上下文
```

恢复时需要：

```plain
找到 thread_id
读取 checkpoint
写入人工确认结果
继续执行
```

LangGraph interrupts 文档说明，触发 interrupt 时会通过持久化层保存 graph state，并一直等待，直到用同一个 thread 恢复执行；LangChain Human-in-the-loop 文档也强调，HITL 需要配置 checkpointer 来跨中断保存状态。

---

## 【重点内容】
这就是为什么第 35 章讲 Human-in-the-loop 之前，必须先讲 Persistence。

如果没有 checkpoint，Agent 暂停后就不知道怎么恢复。

比如退款需要人工确认。

你要保存：

```plain
订单号
订单状态
退款金额
待执行动作
暂停位置
```

等人工点“同意”后，图才能继续执行退款节点。

---

# 三十二、28｜Persistence 和 Time Travel 的关系
Time Travel 可以理解成：

```plain
回到某一个历史 checkpoint
重新执行或调试
```

用途：

```plain
1. 调试 Agent 为什么答错
2. 回放某次执行路径
3. 从某一步重新运行
4. 修改历史状态后探索不同结果
```

LangGraph Time Travel 文档说明，可以从先前 checkpoint 恢复执行，也可以修改状态探索不同执行路径；如果图里有 interrupt，时间旅行过程中 interrupt 也会再次触发。

---

## 【重点内容】
Time Travel 这个能力很适合调试 Agent。

比如用户投诉：

```plain
刚才 AI 客服回答错了。
```

你可以查看历史 checkpoint：

```plain
当时 intent 是什么？
order_id 是不是提错了？
query_order 返回了什么？
RAG 有没有命中？
最后生成回答时 State 是什么？
```

这比只看日志强很多。

---

# 三十三、29｜Persistence 和失败恢复的关系
如果图执行到某一步失败：

```plain
节点 A 成功
节点 B 成功
节点 C 失败
```

有 checkpoint 后，可以从最近成功的状态恢复。

官方 Persistence 文档提到，checkpointing 支持 fault-tolerance 和 error recovery；如果某个 super-step 中部分节点失败，已经成功节点的 pending writes 会被保存，恢复时不需要重新运行这些成功节点。

---

## 【重点内容】
这对企业项目很重要。

比如一个节点调用外部物流接口失败。

你不希望整个流程从头重新来一遍。

能恢复，就可以减少重复工具调用，也方便排查问题。

---

# 三十四、30｜State 里哪些内容适合保存
适合进入 checkpoint 的内容：

```plain
1. 用户当前问题
2. messages
3. intent
4. order_id
5. 工具结果摘要
6. RAG 引用来源摘要
7. 风险等级
8. pending_action
9. need_user_input
10. waiting_for
11. final_answer
12. logs / errors 摘要
```

---

# 三十五、31｜State 里哪些内容不适合保存
不建议进入 checkpoint：

```plain
1. API Key
2. 数据库连接对象
3. Redis client
4. HTTP client
5. 文件二进制内容
6. 超大 PDF 全文
7. 完整用户敏感信息
8. 完整支付信息
9. 不可序列化对象
10. 长期用户画像
```

---

## 【重点内容】
Checkpoint 会被保存。

所以 State 一定要谨慎设计。

不要把敏感凭证放进去。

不要把超大对象放进去。

不要把数据库连接放进去。

State 保存的是流程状态，不是所有数据。

---

# 三十六、32｜Persistence 和安全
生产环境要考虑：

```plain
1. thread_id 不能串用户
2. checkpoint 里不要保存敏感凭证
3. checkpoint 表要有访问权限
4. 后台查看 State 要做权限控制
5. 修改 State 要有审计日志
6. 敏感场景可以考虑加密序列化
```

LangGraph Postgres checkpoint 文档还提醒，敏感场景可以使用加密 serializer，并且建议限制 msgpack 反序列化允许的模块，以降低数据库被攻破后的风险。

---

# 三十七、33｜Persistence 和业务数据库的边界
| 类型 | 作用 |
| --- | --- |
| Checkpoint | 保存图执行状态 |
| chat_messages 表 | 保存聊天消息记录 |
| tool_call_logs 表 | 保存工具调用审计 |
| orders 表 | 保存真实订单 |
| refund_requests 表 | 保存退款申请 |
| document_chunks 表 | 保存知识库 chunk |
| vector_store | 保存向量索引 |


---

## 【重点内容】
Checkpoint 不是万能业务数据库。

它保存的是 Agent 执行状态。

真实业务数据还要进业务表。

比如退款申请一定要写 refund_requests 表。

不能只存在 checkpoint 里。

否则后面财务、客服、风控、审计都不好查。

---

# 三十八、34｜企业项目推荐架构
```plain
FastAPI Router
 ↓
ChatService
 ↓
GraphService
 ↓
LangGraph Compiled Graph
 ↓
Checkpointer
 ↓
PostgreSQL checkpoint tables
```

旁路保存：

```plain
ChatService
 ├── chat_messages
 ├── tool_call_logs
 ├── agent_run_logs
 └── refund_requests
```

---

## 【重点内容】
这里要讲清楚企业项目分层。

Graph Persistence 解决 Agent 流程恢复。

业务表解决业务审计和数据查询。

两者都要有。

不要只用 checkpoint。

也不要自己手写一堆临时状态表替代 checkpoint。

---

# 三十九、35｜生产环境 checkpointer 建议
开发环境：

```plain
InMemorySaver
```

本地小 Demo：

```plain
SqliteSaver / AsyncSqliteSaver
```

生产环境：

```plain
PostgresSaver / AsyncPostgresSaver
```

异步 FastAPI：

```plain
AsyncPostgresSaver
```

LangGraph checkpoint 参考文档列出了常见 Saver：`InMemorySaver` 用于调试测试，SQLite 适合轻量 demo，小型项目可用；生产工作负载推荐 `PostgresSaver` 或 `AsyncPostgresSaver`。

---

# 四十、36｜thread_id 设计 checklist
设计 thread_id 前问自己：

```plain
1. 是否包含 tenant_id？
2. 是否包含 user_id？
3. 是否包含 conversation_id？
4. 是否能保证唯一？
5. 是否能避免跨用户串状态？
6. 是否方便根据会话查 checkpoint？
7. 是否会暴露敏感信息？
8. 是否和业务数据库会话 ID 能关联？
```

推荐：

```python
thread_id = f"{tenant_id}:{user_id}:{conversation_id}"
```

---

# 四十一、37｜常见错误一：没有传 thread_id
错误：

```python
app.invoke(state)
```

有 checkpointer 时，应该传：

```python
app.invoke(
    state,
    config={
        "configurable": {
            "thread_id": "thread_001"
        }
    },
)
```

---

# 四十二、38｜常见错误二：每次请求随机 thread_id
错误：

```python
thread_id = uuid.uuid4().hex
```

问题：

```plain
每次都是新 thread，没有历史状态。
```

正确：

```plain
同一个会话使用同一个 thread_id。
```

---

# 四十三、39｜常见错误三：所有用户共用一个 thread_id
错误：

```python
thread_id = "default"
```

问题：

```plain
不同用户状态串在一起。
```

正确：

```python
thread_id = f"{tenant_id}:{user_id}:{conversation_id}"
```

---

# 四十四、40｜常见错误四：把 InMemorySaver 用到生产
问题：

```plain
1. 服务重启状态丢失
2. 多实例状态不共享
3. 不能支撑正式审计
4. 不能支撑稳定 HITL
```

生产推荐：

```plain
PostgresSaver / AsyncPostgresSaver
```

---

# 四十五、41｜常见错误五：State 里保存敏感信息
错误：

```plain
api_key
完整手机号
完整身份证
银行卡
访问令牌
数据库密码
```

原因：

```plain
checkpoint 会持久化；
后续可能被调试工具或后台展示；
有安全和合规风险。
```

---

# 四十六、42｜常见错误六：把 checkpoint 当业务表
错误：

```plain
退款申请只存在 checkpoint 里。
```

正确：

```plain
checkpoint 保存流程状态；
refund_requests 保存真实业务申请。
```

---

# 四十七、43｜常见错误七：PostgresSaver 忘记 setup
错误：

```python
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
```

正确：

```python
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    app = graph.compile(checkpointer=checkpointer)
```

---

# 四十八、44｜常见错误八：Graph 每次请求重新创建且 checkpointer 不共享
教学代码可以这么写。

生产项目更推荐：

```plain
应用启动时初始化 checkpointer
应用启动时 compile graph
Service 复用 compiled graph
请求只传 input_state + config
```

---

# 四十九、45｜面试回答：LangGraph Persistence 怎么理解
## 回答话术一：基础版
```plain
LangGraph Persistence 可以理解成图执行状态的持久化。

它通过 checkpointer 在图执行过程中保存 checkpoint，也就是 State 的快照。多个 checkpoint 会按照 thread_id 组织成一个 thread。

后续同一个会话继续执行时，只要传相同 thread_id，就可以恢复之前的状态。这对多轮对话、缺参数追问、Human-in-the-loop、失败恢复和 Time Travel 调试都非常重要。
```

---

## 回答话术二：项目版
```plain
比如电商客服 Agent 里，用户第一轮说“我要退款”，系统发现缺少订单号，就在 State 里记录 intent=refund、need_user_input=True、waiting_for=order_id，并回答让用户补充订单号。

用户第二轮说“订单号是 10002”，我们用同一个 thread_id 调用图，LangGraph 会恢复上一轮 State，所以系统知道这是继续退款流程，而不是一个孤立的新问题。

然后图继续执行订单查询、售后规则检索和最终回答。
```

---

## 回答话术三：工程版
```plain
工程上我会把 conversation_id 映射成 LangGraph 的 thread_id，一般会设计成 tenant_id:user_id:conversation_id，避免多租户和多用户之间串状态。

开发环境可以用 InMemorySaver，生产环境会用 AsyncPostgresSaver。checkpoint 用来保存图执行状态，业务数据仍然写入业务表，比如 chat_messages、tool_call_logs、refund_requests。

另外 State 设计要注意安全，不能把 API Key、数据库连接、完整敏感信息和超大对象放进 checkpoint。
```

---

# 五十、46｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Persistence | 第 29 章复杂 Agent 可恢复 |
| Checkpoint | 第 30 章 Checkpointer |
| State Snapshot | 第 31 章 State |
| thread_id | 第 19 章 conversation_id |
| InMemorySaver | 第 30 章本地记忆 |
| PostgresSaver | 第 11 章 PostgreSQL |
| AsyncPostgresSaver | 第 05 章 async / await |
| 多轮记忆 | 第 22 章 Messages |
| 缺参数追问 | 第 33 章条件路由 |
| Human-in-the-loop | 第 35 章人工确认 |
| Time Travel | Agent 调试和回放 |
| 失败恢复 | 第 10 章异常处理 |
| 业务表边界 | 第 11 章数据库建模 |
| 电商断点续聊 | 第 38 章项目二基础 |


---

# 五十一、47｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Persistence 解决什么问题
2. 理解 Checkpoint 是 State 快照
3. 理解 Thread 是 checkpoint 的归属容器
4. 理解 thread_id 的重要性
5. 学会设计 thread_id
6. 创建 langgraph_persistence 目录
7. 定义 PersistenceState
8. 创建 build_persistence_graph
9. 使用 InMemorySaver
10. 验证 thread_id 隔离状态
11. 使用 get_state 查看当前状态
12. 使用 get_state_history 查看历史状态
13. 使用 update_state 人工修正状态
14. 实现多轮 Chat Memory
15. 实现电商客服断点续聊
16. 理解 InMemorySaver 的限制
17. 使用 PostgresSaver
18. 使用 AsyncPostgresSaver
19. 理解 Postgres checkpointer setup
20. 理解 Persistence 和项目一的关系
21. 封装 Persistence Service
22. 创建 Persistence API
23. 测试 Persistence API
24. 理解 Persistence 和 HITL 的关系
25. 理解 Persistence 和 Time Travel 的关系
26. 理解 Persistence 和失败恢复的关系
27. 总结 State 中适合保存和不适合保存的内容
28. 理解 Persistence 安全问题
29. 理解 checkpoint 和业务数据库边界
30. 总结生产环境 checkpointer 建议
31. 总结 thread_id checklist
32. 总结常见错误
33. 准备面试回答话术
```

---

# 五十二、48｜课后任务一：跑通 InMemorySaver
要求：

```plain
1. 运行 scripts/test_lg34_01_inmemory_saver.py
2. 查看 final_answer
3. 查看 logs
4. 说明 checkpointer 和 thread_id 分别有什么作用
```

---

# 五十三、49｜课后任务二：验证 thread_id 隔离
要求：

```plain
1. 运行 scripts/test_lg34_02_thread_id_isolation.py
2. 查看 thread_user_a 和 thread_user_b 的状态
3. 说明为什么不同用户不能共用 thread_id
```

---

# 五十四、50｜课后任务三：查看当前 State
要求：

```plain
1. 运行 scripts/test_lg34_03_get_state.py
2. 查看 snapshot.values
3. 查看 snapshot.config
4. 说明 get_state 在调试 Agent 时有什么用
```

---

# 五十五、51｜课后任务四：查看历史 State
要求：

```plain
1. 运行 scripts/test_lg34_04_state_history.py
2. 查看 checkpoint count
3. 观察每个 snapshot 里的 intent / order_id / final_answer
4. 说明 get_state_history 和 Time Travel 的关系
```

---

# 五十六、52｜课后任务五：测试 update_state
要求：

```plain
1. 运行 scripts/test_lg34_05_update_state.py
2. 查看 before 里的 order_id
3. 查看 after 里的 order_id
4. 思考生产环境谁有权限 update_state
```

---

# 五十七、53｜课后任务六：跑通 Chat Memory
要求：

```plain
1. 运行 scripts/test_lg34_06_chat_memory.py
2. 两轮 invoke 使用同一个 thread_id
3. 查看第二轮 messages 是否包含第一轮消息
4. 修改 thread_id 后再观察效果
```

---

# 五十八、54｜课后任务七：跑通电商客服断点续聊
要求：

```plain
1. 运行 scripts/test_lg34_07_ecommerce_resume.py
2. 第一轮输入“我要退款”
3. 查看 waiting_for=order_id
4. 第二轮输入“订单号是 10002”
5. 查看是否继续退款流程
```

---

# 五十九、55｜课后任务八：配置 PostgresSaver
要求：

```plain
1. 本地启动 PostgreSQL
2. 创建 ai_agent 数据库
3. 修改 DB_URI
4. 运行 scripts/test_lg34_08_postgres_saver.py
5. 查看 checkpoint 是否写入数据库
```

---

# 六十、56｜课后任务九：配置 AsyncPostgresSaver
要求：

```plain
1. 安装 langgraph-checkpoint-postgres 和 psycopg
2. 修改 DB_URI
3. 运行 scripts/test_lg34_09_async_postgres_saver.py
4. 说明 AsyncPostgresSaver 为什么更适合 FastAPI
```

---

# 六十一、57｜课后任务十：接入项目一 conversation_id
要求：

```plain
1. 使用项目一的 conversation_id
2. 生成 thread_id = tenant_id:user_id:conversation_id
3. ChatService 调用 GraphService 时传入 config
4. 验证同一个 conversation_id 可以继续上下文
5. 不同 conversation_id 状态隔离
```

---

# 六十二、58｜课后任务十一：设计 checkpoint 安全规范
要求写出团队规范：

```plain
1. State 不保存 API Key
2. State 不保存数据库连接
3. State 不保存完整敏感信息
4. 后台查看 checkpoint 需要权限
5. update_state 需要审计日志
6. 生产使用 PostgresSaver / AsyncPostgresSaver
7. thread_id 必须包含租户和用户隔离信息
```

---

# 六十三、59｜本章总结
## 【重点内容】
好了，到这里，第 34 章我们就讲完了。

这一章我们专门讲了 LangGraph Persistence。

大家一定要记住：

```plain
Persistence 的核心是：
用 checkpointer 保存 Graph State。
```

几个关键词要牢牢记住：

```plain
Checkpoint：某个时刻的 State 快照
Thread：一组 checkpoint 的会话线
thread_id：区分会话状态的唯一标识
InMemorySaver：本地测试用
PostgresSaver：生产同步版本
AsyncPostgresSaver：生产异步版本
get_state：查看当前状态
get_state_history：查看历史状态
update_state：人工修改状态
```

企业 Agent 里，Persistence 非常重要。

因为它支撑：

```plain
多轮对话
缺参数追问
人工确认
中断恢复
失败恢复
Time Travel 调试
状态审计
```

没有 Persistence，Agent 就很难从 Demo 走向生产。

---
