---

# 一、本章定位
前面我们已经完成：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
第 34 章｜LangGraph Persistence
第 35 章｜LangGraph Human-in-the-loop
```

第 34 章我们讲了：

```plain
Persistence
Checkpoint
Thread
thread_id
状态保存和恢复
```

第 35 章我们讲了：

```plain
interrupt
Command(resume=...)
高风险动作暂停
人工确认后恢复
```

这一章继续往前走：

# Agent Memory
也就是：

```plain
让 Agent 能记住上下文、用户偏好、历史事实和长期信息。
```

但是这里一定要先区分清楚：

```plain
Persistence 不等于 Memory。
Memory 也不等于 RAG。
```

它们三个很容易混。

这一章就是专门把这些概念和代码打通。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Agent Memory 到底是什么
2. Memory 和 Persistence 的区别
3. Memory 和 RAG 的区别
4. Short-term Memory 是什么
5. Long-term Memory 是什么
6. messages 如何作为短期记忆
7. checkpointer 如何保存短期记忆
8. thread_id 如何隔离短期记忆
9. 长对话为什么需要裁剪和摘要
10. trim_messages 怎么用
11. summary memory 怎么设计
12. Long-term Memory 为什么需要 Store
13. namespace 和 key 怎么设计
14. InMemoryStore 怎么用
15. PostgresStore 生产环境怎么用
16. Node 里如何通过 Runtime 读取 Store
17. Node 里如何写入长期记忆
18. 用户偏好记忆怎么设计
19. 电商客服怎么记住用户偏好
20. Memory 如何避免污染
21. Memory 如何做权限隔离
22. Memory 如何和 RAG 配合
23. Memory 如何接入 FastAPI
24. 面试中怎么讲 Agent Memory
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

如果要使用 PostgreSQL Store：

```bash
uv add "langgraph-checkpoint-postgres" "psycopg[binary,pool]"
```

本章主要用到：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.runtime import Runtime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, AnyMessage
```

LangGraph 官方文档里，短期记忆通过 checkpointer 保存到 thread-scoped state 中；长期记忆通过 Store 保存，并可以在节点中通过 Runtime 访问。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langgraph_memory/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── graph_factory.py
│   │   ├── service.py
│   │   ├── demo_01_short_term_memory.py
│   │   ├── demo_02_thread_memory_isolation.py
│   │   ├── demo_03_trim_messages.py
│   │   ├── demo_04_summary_memory.py
│   │   ├── demo_05_store_basic.py
│   │   ├── demo_06_runtime_store_node.py
│   │   ├── demo_07_write_user_preference.py
│   │   ├── demo_08_recall_user_preference.py
│   │   ├── demo_09_ecommerce_memory_graph.py
│   │   └── demo_10_memory_api_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langgraph_memory.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg36_01_short_term_memory.py
│   ├── test_lg36_02_thread_memory_isolation.py
│   ├── test_lg36_03_trim_messages.py
│   ├── test_lg36_04_summary_memory.py
│   ├── test_lg36_05_store_basic.py
│   ├── test_lg36_06_runtime_store_node.py
│   ├── test_lg36_07_write_user_preference.py
│   ├── test_lg36_08_recall_user_preference.py
│   ├── test_lg36_09_ecommerce_memory_graph.py
│   └── test_lg36_10_memory_service.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 36 章。

这一章我们讲 LangGraph Agent Memory。

前面第 34 章我们讲了 Persistence，能够让 Agent 的执行状态保存和恢复。

第 35 章我们讲了 Human-in-the-loop，能够让 Agent 执行到高风险动作时暂停，人工确认后继续。

但是这还不够。

一个真正好用的 Agent，不只是能恢复流程。

它还应该能记住：

```plain
这个用户之前说过什么
这个用户偏好什么
这个用户经常问什么
这个用户的常用订单场景是什么
这个用户希望回答简短还是详细
这个用户偏向中文还是英文
```

这就是 Agent Memory。

但是 Memory 不能乱做。

乱记会出问题。

比如用户只是随口说一句：

```plain
今天我想喝冰美式。
```

你不能永远记住“用户喜欢冰美式”。

这可能只是今天的临时偏好。

所以这一章我们不仅讲怎么实现 Memory，还要讲：

```plain
什么该记
什么不该记
什么时候记
记到哪里
什么时候召回
怎么防止记忆污染
```

---

# 六、02｜Memory 一句话解释
## 【实操】
```plain
Agent Memory
=
Agent 对历史上下文、用户偏好、长期事实的保存和召回能力。
```

再简单一点：

```plain
Memory 就是让 Agent 不要每次都像第一次见用户。
```

---

## 【重点内容】
没有 Memory 的 Agent，每一轮都像失忆。

用户上一轮说：

```plain
我叫大伟。
```

下一轮问：

```plain
你还记得我叫什么吗？
```

如果没有记忆，它就不知道。

这时候我们需要短期记忆。

再比如用户长期偏好：

```plain
回答尽量口语化
代码要给完整实现
面试题要给话术
不要太 AI 化
```

这些如果每次都重新告诉 Agent，就很麻烦。

这时候需要长期记忆。

---

# 七、03｜Memory 和 Persistence 的区别
| 对比项 | Persistence | Memory |
| --- | --- | --- |
| 核心作用 | 保存图执行状态 | 让 Agent 记住上下文和信息 |
| 典型数据 | State、checkpoint、next node | messages、用户偏好、长期事实 |
| 范围 | thread 维度为主 | thread 或跨 thread |
| 目的 | 恢复流程 | 改善对话和个性化 |
| 例子 | 暂停在 human_review 后恢复 | 记住用户喜欢简洁回答 |


---

## 【重点内容】
Persistence 更偏底层机制。

它解决的是：

```plain
图能不能恢复。
```

Memory 更偏 Agent 能力。

它解决的是：

```plain
Agent 能不能记住。
```

短期记忆通常依赖 Persistence。

比如 messages 保存在 State 里，再通过 checkpointer 持久化。

长期记忆通常依赖 Store。

比如用户偏好保存到 Store 里，跨会话都能召回。

---

# 八、04｜Memory 和 RAG 的区别
| 对比项 | Memory | RAG |
| --- | --- | --- |
| 记什么 | 用户相关信息、历史偏好、交互事实 | 企业文档、知识库、制度、产品说明 |
| 范围 | 用户或会话相关 | 企业或业务知识相关 |
| 数据来源 | 用户对话、行为、反馈 | 文档、网页、数据库 |
| 更新频率 | 持续更新 | 相对稳定或批量更新 |
| 例子 | 用户喜欢简短回答 | 退款规则、年假制度、产品手册 |


---

## 【重点内容】
Memory 和 RAG 很容易混。

比如：

```plain
用户喜欢口语化回答
```

这是 Memory。

```plain
订单未发货可以申请退款
```

这是 RAG 或业务知识库。

再比如：

```plain
用户上次问过订单 10002
```

这是短期或历史记忆。

```plain
公司售后规则第 3 条
```

这是知识库。

两者可以配合，但不能混成一坨。

---

# 九、05｜短期记忆 Short-term Memory
短期记忆是：

```plain
thread 内部的上下文记忆。
```

典型数据：

```plain
messages
当前任务状态
上传文件
工具结果
临时检索结果
当前流程信息
```

LangGraph 官方把短期记忆定义为 thread-scoped memory，也就是单个会话内的记忆；它作为 Agent State 的一部分通过 checkpointer 持久化，后续同一个 thread 可以恢复上下文。

---

## 【重点内容】
短期记忆适合解决多轮对话。

比如：

```plain
用户：我要退款。
Agent：请提供订单号。
用户：10002。
```

这里第二轮用户只说“10002”。

如果没有短期记忆，Agent 不知道 10002 是干什么的。

但如果同一个 thread 里保存了上一轮状态，Agent 就知道：

```plain
上一轮 intent=refund
waiting_for=order_id
所以这一轮 10002 是订单号
```

这就是短期记忆。

---

# 十、06｜长期记忆 Long-term Memory
长期记忆是：

```plain
跨 thread、跨 session 的用户或应用记忆。
```

典型数据：

```plain
用户偏好
用户常用语言
用户回答风格偏好
用户业务习惯
用户历史反馈
长期稳定事实
```

LangGraph / LangChain 文档说明，长期记忆不像短期记忆那样只属于单个 thread；它跨 conversation 和 session 生效，并通过 LangGraph Store 以 namespace + key 的 JSON 文档方式保存。

---

## 【重点内容】
长期记忆解决的是跨会话个性化。

比如用户今天开了一个 conversation，明天又开一个新的 conversation。

短期记忆因为 thread 变了，默认不会带过去。

但是长期记忆可以带过去。

比如：

```plain
用户喜欢中文
用户希望回答口语化
用户是前端工程师
用户喜欢代码完整
```

这些长期偏好，可以跨会话召回。

---

# 十一、07｜Memory 类型：Semantic / Episodic / Procedural
长期记忆可以粗略分三类：

| 类型 | 记什么 | 例子 |
| --- | --- | --- |
| Semantic Memory | 事实和偏好 | 用户喜欢简洁回答 |
| Episodic Memory | 过去经历和事件 | 用户上次申请过订单退款 |
| Procedural Memory | 行为规则和指令 | 回答面试题时要给话术和代码 |


LangGraph 官方概念文档也提到，AI Agent 可以类比人类记忆，把长期记忆分成 semantic、episodic、procedural 等类型；这些类型可以分别存储用户事实、过往行为和操作规则。

---

## 【重点内容】
这三个类型对企业 Agent 很有帮助。

比如电商客服：

```plain
Semantic：
用户偏好顺丰快递。

Episodic：
用户上次订单 10002 申请过退款。

Procedural：
用户希望客服回复尽量简短，不要太官方。
```

不同记忆类型，写入策略也不同。

不是所有东西都直接长期保存。

---

# 十二、08｜创建目录
执行：

```bash
mkdir -p app/langgraph_memory

touch app/langgraph_memory/__init__.py
touch app/langgraph_memory/schemas.py
touch app/langgraph_memory/graph_factory.py
touch app/langgraph_memory/service.py
touch app/langgraph_memory/demo_01_short_term_memory.py
touch app/langgraph_memory/demo_02_thread_memory_isolation.py
touch app/langgraph_memory/demo_03_trim_messages.py
touch app/langgraph_memory/demo_04_summary_memory.py
touch app/langgraph_memory/demo_05_store_basic.py
touch app/langgraph_memory/demo_06_runtime_store_node.py
touch app/langgraph_memory/demo_07_write_user_preference.py
touch app/langgraph_memory/demo_08_recall_user_preference.py
touch app/langgraph_memory/demo_09_ecommerce_memory_graph.py
touch app/langgraph_memory/demo_10_memory_api_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_memory

New-Item app\langgraph_memory\__init__.py
New-Item app\langgraph_memory\schemas.py
New-Item app\langgraph_memory\graph_factory.py
New-Item app\langgraph_memory\service.py
New-Item app\langgraph_memory\demo_01_short_term_memory.py
New-Item app\langgraph_memory\demo_02_thread_memory_isolation.py
New-Item app\langgraph_memory\demo_03_trim_messages.py
New-Item app\langgraph_memory\demo_04_summary_memory.py
New-Item app\langgraph_memory\demo_05_store_basic.py
New-Item app\langgraph_memory\demo_06_runtime_store_node.py
New-Item app\langgraph_memory\demo_07_write_user_preference.py
New-Item app\langgraph_memory\demo_08_recall_user_preference.py
New-Item app\langgraph_memory\demo_09_ecommerce_memory_graph.py
New-Item app\langgraph_memory\demo_10_memory_api_adapter.py
```

---

# 十三、09｜准备公共 State
打开：

```plain
app/langgraph_memory/schemas.py
```

写入：

```python
import operator
from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


class UserMemoryItem(TypedDict, total=False):
    key: str
    type: Literal["preference", "profile", "behavior", "note"]
    content: str
    confidence: float
    source: str


class MemoryState(TypedDict):
    user_question: str
    messages: Annotated[list[AnyMessage], add_messages]

    short_summary: str | None

    recalled_memories: Annotated[list[UserMemoryItem], operator.add]
    new_memories: Annotated[list[UserMemoryItem], operator.add]

    intent: Literal[
        "general",
        "remember_preference",
        "recall_preference",
        "ecommerce_service",
        "unknown",
    ]

    final_answer: str
    is_finished: bool

    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


@dataclass
class MemoryContext:
    user_id: str
    tenant_id: str = "tenant_001"


def create_initial_memory_state(
    user_question: str,
) -> MemoryState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "short_summary": None,

        "recalled_memories": [],
        "new_memories": [],

        "intent": "unknown",

        "final_answer": "",
        "is_finished": False,

        "logs": [],
        "errors": [],
    }
```

---

## 【重点内容】
这里我们设计了一个 MemoryState。

重点字段有：

```plain
messages：
短期对话消息。

short_summary：
长对话摘要。

recalled_memories：
从长期记忆里召回的信息。

new_memories：
本轮准备写入的新记忆。

intent：
当前用户是否在表达记住偏好、召回偏好、普通问答等。

final_answer：
最终回答。
```

另外还有一个 MemoryContext。

它不是 State。

它是运行上下文，用来告诉图：

```plain
当前 user_id 是谁
tenant_id 是谁
```

长期记忆必须按用户隔离，所以 user_id 很关键。

---

# 十四、10｜示例一：短期记忆 messages
打开：

```plain
app/langgraph_memory/demo_01_short_term_memory.py
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
    message_count = len(state["messages"])

    return {
        "messages": [
            AIMessage(
                content=(
                    f"我收到你的消息：{last_message.content}。"
                    f"当前 thread 里一共有 {message_count} 条消息。"
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
            "thread_id": "thread_memory_demo_001"
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
                HumanMessage(content="你还记得我刚才说什么吗？")
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
scripts/test_lg36_01_short_term_memory.py
```

写入：

```python
from app.langgraph_memory.demo_01_short_term_memory import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg36_01_short_term_memory.py
```

---

## 【重点内容】
这个例子是最小短期记忆。

核心点有两个：

```plain
messages 使用 add_messages
graph 编译时使用 checkpointer
```

只要两次 invoke 使用同一个 thread_id，第二轮就能看到第一轮 messages。

这就是最基础的短期记忆。

---

# 十五、11｜示例二：thread 记忆隔离
打开：

```plain
app/langgraph_memory/demo_02_thread_memory_isolation.py
```

写入：

```python
from langchain_core.messages import HumanMessage

from app.langgraph_memory.demo_01_short_term_memory import build_graph


def run_chat(app, thread_id: str, content: str):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = app.invoke(
        {
            "messages": [
                HumanMessage(content=content)
            ]
        },
        config=config,
    )

    print("thread_id:", thread_id)
    print("message_count:", len(result["messages"]))
    for message in result["messages"]:
        print(message.type, ":", message.content)
    print("=" * 80)


def main():
    app = build_graph()

    run_chat(app, "thread_user_a", "我叫用户 A。")
    run_chat(app, "thread_user_b", "我叫用户 B。")
    run_chat(app, "thread_user_a", "你还记得我是谁吗？")
    run_chat(app, "thread_user_b", "你还记得我是谁吗？")


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_02_thread_memory_isolation.py
```

写入：

```python
from app.langgraph_memory.demo_02_thread_memory_isolation import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子说明：

```plain
短期记忆是 thread 级别隔离的。
```

用户 A 的 thread 看不到用户 B 的 messages。

真实项目里，thread_id 仍然建议设计成：

```plain
tenant_id:user_id:conversation_id
```

这样才能避免串用户。

---

# 十六、12｜长对话为什么需要管理
短期记忆不是无限塞 messages。

长对话会有几个问题：

```plain
1. 消息越来越多
2. token 成本越来越高
3. 请求越来越慢
4. 超过模型上下文窗口
5. 旧消息干扰当前回答
6. 无关历史导致模型跑偏
```

官方 Memory 文档也提到，长 conversations 可能超过模型上下文窗口，即使没有超过，也会带来更慢、更贵和被旧上下文干扰的问题；常见处理方式包括 trim messages、delete messages、summarize messages、管理 checkpoints 等。

---

## 【重点内容】
这里一定要提醒学员。

不要以为短期记忆就是把所有 messages 永远塞给模型。

这会出问题。

正确做法是：

```plain
保留最近消息
摘要较早消息
删除无用消息
重要信息转为长期记忆
```

这就是 Memory 管理。

---

# 十七、13｜示例三：trim_messages 裁剪消息
打开：

```plain
app/langgraph_memory/demo_03_trim_messages.py
```

写入：

```python
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.messages.utils import (
    count_tokens_approximately,
    trim_messages,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class TrimMemoryState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    final_answer: str


def chat_node(state: TrimMemoryState) -> dict:
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=128,
        start_on="human",
        end_on=("human", "ai"),
    )

    answer = (
        f"原始消息数量：{len(state['messages'])}，"
        f"裁剪后消息数量：{len(trimmed_messages)}。"
    )

    return {
        "messages": [
            AIMessage(content=answer)
        ],
        "final_answer": answer,
    }


def build_graph():
    graph = StateGraph(TrimMemoryState)

    graph.add_node("chat", chat_node)

    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_trim_messages_demo"
        }
    }

    questions = [
        "第一轮：我叫大伟。",
        "第二轮：我在学习 LangGraph。",
        "第三轮：我想做电商客服 Agent。",
        "第四轮：我想让回答更口语化。",
        "第五轮：请总结一下你现在记住了什么。",
    ]

    for question in questions:
        result = app.invoke(
            {
                "messages": [
                    HumanMessage(content=question)
                ],
                "final_answer": "",
            },
            config=config,
        )

        print("question:", question)
        print("final_answer:", result["final_answer"])
        print("total_messages:", len(result["messages"]))
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_03_trim_messages.py
```

写入：

```python
from app.langgraph_memory.demo_03_trim_messages import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示的是裁剪消息。

注意，`trim_messages` 是在调用模型前裁剪上下文。

它不一定删除 State 里的原始 messages。

你可以理解成：

```plain
State 里保存完整历史；
调用模型时只拿一部分。
```

真实项目里，要根据 token、模型上下文和业务要求决定保留多少。

---

# 十八、14｜示例四：摘要记忆 Summary Memory
摘要记忆的思路：

```plain
长对话 messages 太多
 ↓
把早期对话压缩成 summary
 ↓
后续模型输入 = summary + 最近 messages
```

打开：

```plain
app/langgraph_memory/demo_04_summary_memory.py
```

写入：

```python
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class SummaryMemoryState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    short_summary: str | None
    final_answer: str


def summarize_if_needed_node(state: SummaryMemoryState) -> dict:
    messages = state["messages"]

    if len(messages) < 6:
        return {
            "short_summary": state.get("short_summary"),
        }

    old_text = "\n".join(
        f"{message.type}: {message.content}"
        for message in messages[:-4]
    )

    # 教学版：这里用简单拼接模拟摘要。
    # 真实项目里应该调用总结模型。
    summary = (
        "早期对话摘要：用户提到过自己叫大伟，"
        "正在学习 LangGraph，并且想做电商客服 Agent。"
        f"\n原始摘要依据：{old_text[:120]}..."
    )

    return {
        "short_summary": summary
    }


def answer_node(state: SummaryMemoryState) -> dict:
    summary = state.get("short_summary") or "暂无摘要"
    recent_messages = state["messages"][-4:]

    recent_text = "\n".join(
        f"{message.type}: {message.content}"
        for message in recent_messages
    )

    answer = (
        "我会结合摘要和最近消息回答。\n\n"
        f"【摘要】{summary}\n\n"
        f"【最近消息】\n{recent_text}"
    )

    return {
        "messages": [
            AIMessage(content=answer)
        ],
        "final_answer": answer,
    }


def build_graph():
    graph = StateGraph(SummaryMemoryState)

    graph.add_node("summarize_if_needed", summarize_if_needed_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "summarize_if_needed")
    graph.add_edge("summarize_if_needed", "answer")
    graph.add_edge("answer", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_summary_memory_demo"
        }
    }

    questions = [
        "我叫大伟。",
        "我正在学习 LangGraph。",
        "我想做电商客服 Agent。",
        "我希望回答口语化一点。",
        "我还想要代码完整。",
        "请你总结一下你记住了什么。",
    ]

    for question in questions:
        result = app.invoke(
            {
                "messages": [
                    HumanMessage(content=question)
                ],
                "short_summary": None,
                "final_answer": "",
            },
            config=config,
        )

        print("question:", question)
        print("summary:", result["short_summary"])
        print("final_answer:", result["final_answer"][:300])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_04_summary_memory.py
```

写入：

```python
from app.langgraph_memory.demo_04_summary_memory import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
摘要记忆适合长对话。

但是摘要也有风险。

如果摘要错了，后续 Agent 会一直带着错误摘要。

所以真实项目里，摘要要注意：

```plain
不要过度推断
不要加入用户没说过的信息
重要事实尽量结构化
摘要要可更新
必要时保留原始消息索引
```

---

# 十九、15｜长期记忆 Store 基本用法
长期记忆不建议放在 thread state 里。

推荐放 Store。

LangGraph Store 的基本结构是：

```plain
namespace + key + JSON value
```

比如：

```plain
namespace = ("tenant_001", "u_10001", "preferences")
key = "answer_style"
value = {"content": "用户喜欢口语化、完整代码示例"}
```

LangGraph Store 文档示例里，长期记忆通过 `InMemoryStore` 或数据库 Store 保存，数据以 namespace 和 key 组织，value 通常是 JSON 文档；在生产环境里应使用数据库型 Store，并按具体实现运行 setup 迁移。

---

# 二十、16｜示例五：InMemoryStore 基础操作
打开：

```plain
app/langgraph_memory/demo_05_store_basic.py
```

写入：

```python
from langgraph.store.memory import InMemoryStore


def main():
    store = InMemoryStore()

    tenant_id = "tenant_001"
    user_id = "u_10001"

    namespace = (tenant_id, user_id, "preferences")

    store.put(
        namespace,
        "answer_style",
        {
            "type": "preference",
            "content": "用户喜欢口语化、直接、代码完整的回答。",
            "confidence": 0.95,
            "source": "user_explicit_request",
        },
    )

    item = store.get(namespace, "answer_style")

    print("get memory:")
    print(item)

    print("=" * 80)

    items = store.search(namespace)

    print("search memories:")
    for memory in items:
        print("key:", memory.key)
        print("value:", memory.value)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_05_store_basic.py
```

写入：

```python
from app.langgraph_memory.demo_05_store_basic import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子没有 Graph。

只演示 Store。

大家先记住三个操作：

```plain
put：写入记忆
get：按 key 读取记忆
search：搜索 namespace 下的记忆
```

Store 是长期记忆的基础。

---

# 二十一、17｜Node 里访问 Store
LangGraph 推荐通过 Runtime 在节点里访问 Store。

官方示例里，Graph 编译时传入 `store=store`，节点函数通过 `runtime.store` 搜索和写入记忆，同时通过 `runtime.context.user_id` 获取当前用户上下文。

打开：

```plain
app/langgraph_memory/demo_06_runtime_store_node.py
```

写入：

```python
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore

from app.langgraph_memory.schemas import (
    MemoryContext,
    MemoryState,
    create_initial_memory_state,
)


def recall_memory_node(
    state: MemoryState,
    runtime: Runtime[MemoryContext],
) -> dict:
    namespace = (
        runtime.context.tenant_id,
        runtime.context.user_id,
        "preferences",
    )

    items = runtime.store.search(namespace)

    recalled_memories = []

    for item in items:
        value = item.value
        recalled_memories.append({
            "key": item.key,
            "type": value.get("type", "preference"),
            "content": value.get("content", ""),
            "confidence": value.get("confidence", 0.8),
            "source": value.get("source", "store"),
        })

    return {
        "recalled_memories": recalled_memories,
        "logs": [f"recall_memory：召回 {len(recalled_memories)} 条长期记忆"],
    }


def answer_node(state: MemoryState) -> dict:
    if state["recalled_memories"]:
        memory_text = "\n".join(
            f"- {item['content']}"
            for item in state["recalled_memories"]
        )
    else:
        memory_text = "暂无长期记忆"

    answer = (
        "我会结合你的长期偏好回答。\n\n"
        f"【召回记忆】\n{memory_text}"
    )

    return {
        "messages": [
            AIMessage(content=answer)
        ],
        "final_answer": answer,
        "is_finished": True,
        "logs": ["answer：基于长期记忆生成回答"],
    }


def build_graph():
    graph = StateGraph(
        MemoryState,
        context_schema=MemoryContext,
    )

    graph.add_node("recall_memory", recall_memory_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "recall_memory")
    graph.add_edge("recall_memory", "answer")
    graph.add_edge("answer", END)

    store = InMemoryStore()
    checkpointer = InMemorySaver()

    return graph.compile(
        store=store,
        checkpointer=checkpointer,
    )


def main():
    app = build_graph()

    tenant_id = "tenant_001"
    user_id = "u_10001"

    namespace = (tenant_id, user_id, "preferences")

    app.store.put(
        namespace,
        "answer_style",
        {
            "type": "preference",
            "content": "用户喜欢口语化、不要太官方的回答。",
            "confidence": 0.95,
            "source": "manual_seed",
        },
    )

    result = app.invoke(
        create_initial_memory_state("你应该怎么回答我？"),
        config={
            "configurable": {
                "thread_id": "thread_runtime_store_demo"
            }
        },
        context=MemoryContext(
            tenant_id=tenant_id,
            user_id=user_id,
        ),
    )

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
scripts/test_lg36_06_runtime_store_node.py
```

写入：

```python
from app.langgraph_memory.demo_06_runtime_store_node import main


if __name__ == "__main__":
    main()
```

---

## 【重要说明】
如果你本地运行时发现：

```plain
app.store
```

不可直接访问，可以把 `store` 变量放到外层工厂函数返回，写成：

```python
return graph.compile(...), store
```

然后在 main 里用返回的 store 写入种子数据。

课程录制时建议采用更显式的写法：

```python
app, store = build_graph()
store.put(...)
```

这样更稳。

---

# 二十二、18｜推荐改法：Graph 和 Store 一起返回
把上面的 `build_graph` 改成：

```python
def build_graph():
    graph = StateGraph(
        MemoryState,
        context_schema=MemoryContext,
    )

    graph.add_node("recall_memory", recall_memory_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "recall_memory")
    graph.add_edge("recall_memory", "answer")
    graph.add_edge("answer", END)

    store = InMemoryStore()
    checkpointer = InMemorySaver()

    app = graph.compile(
        store=store,
        checkpointer=checkpointer,
    )

    return app, store
```

main 改成：

```python
app, store = build_graph()

store.put(
    namespace,
    "answer_style",
    {
        "type": "preference",
        "content": "用户喜欢口语化、不要太官方的回答。",
        "confidence": 0.95,
        "source": "manual_seed",
    },
)
```

---

# 二十三、19｜示例七：写入用户偏好记忆
打开：

```plain
app/langgraph_memory/demo_07_write_user_preference.py
```

写入：

```python
import uuid

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore

from app.langgraph_memory.schemas import (
    MemoryContext,
    MemoryState,
    create_initial_memory_state,
)


def classify_memory_intent_node(state: MemoryState) -> dict:
    question = state["user_question"]

    if "记住" in question or "以后回答" in question or "以后你" in question:
        intent = "remember_preference"
    elif "你记得" in question or "我的偏好" in question:
        intent = "recall_preference"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_memory_intent：intent={intent}"],
    }


def write_preference_node(
    state: MemoryState,
    runtime: Runtime[MemoryContext],
) -> dict:
    namespace = (
        runtime.context.tenant_id,
        runtime.context.user_id,
        "preferences",
    )

    content = state["user_question"]

    memory = {
        "type": "preference",
        "content": content,
        "confidence": 0.85,
        "source": "user_explicit_request",
    }

    memory_key = f"pref_{uuid.uuid4().hex}"

    runtime.store.put(
        namespace,
        memory_key,
        memory,
    )

    return {
        "new_memories": [
            {
                "key": memory_key,
                **memory,
            }
        ],
        "final_answer": "好的，我已经记住你的这个偏好。",
        "is_finished": True,
        "messages": [
            AIMessage(content="好的，我已经记住你的这个偏好。")
        ],
        "logs": [f"write_preference：写入记忆 key={memory_key}"],
    }


def build_graph():
    graph = StateGraph(
        MemoryState,
        context_schema=MemoryContext,
    )

    graph.add_node("classify_memory_intent", classify_memory_intent_node)
    graph.add_node("write_preference", write_preference_node)

    graph.add_edge(START, "classify_memory_intent")
    graph.add_edge("classify_memory_intent", "write_preference")
    graph.add_edge("write_preference", END)

    store = InMemoryStore()
    checkpointer = InMemorySaver()

    app = graph.compile(
        store=store,
        checkpointer=checkpointer,
    )

    return app, store


def main():
    app, store = build_graph()

    tenant_id = "tenant_001"
    user_id = "u_10001"

    result = app.invoke(
        create_initial_memory_state(
            "记住：以后回答面试题，要给我口语化话术和代码示例。"
        ),
        config={
            "configurable": {
                "thread_id": "thread_write_preference_demo"
            }
        },
        context=MemoryContext(
            tenant_id=tenant_id,
            user_id=user_id,
        ),
    )

    print("final_answer:", result["final_answer"])
    print("new_memories:", result["new_memories"])

    print("=" * 80)

    namespace = (tenant_id, user_id, "preferences")
    items = store.search(namespace)

    print("store memories:")
    for item in items:
        print(item.key, item.value)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_07_write_user_preference.py
```

写入：

```python
from app.langgraph_memory.demo_07_write_user_preference import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示写入长期记忆。

这里有个非常重要的规则：

```plain
用户明确说“记住”时，才写入长期记忆。
```

这能减少记忆污染。

不要用户随便说一句话，你就自动存长期记忆。

尤其是用户临时状态、情绪、一次性需求，不要乱存。

---

# 二十四、20｜示例八：召回用户偏好记忆
打开：

```plain
app/langgraph_memory/demo_08_recall_user_preference.py
```

写入：

```python
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore

from app.langgraph_memory.schemas import (
    MemoryContext,
    MemoryState,
    create_initial_memory_state,
)


def recall_preference_node(
    state: MemoryState,
    runtime: Runtime[MemoryContext],
) -> dict:
    namespace = (
        runtime.context.tenant_id,
        runtime.context.user_id,
        "preferences",
    )

    items = runtime.store.search(namespace)

    recalled = []

    for item in items:
        value = item.value
        recalled.append({
            "key": item.key,
            "type": value.get("type", "preference"),
            "content": value.get("content", ""),
            "confidence": value.get("confidence", 0.8),
            "source": value.get("source", "store"),
        })

    return {
        "recalled_memories": recalled,
        "logs": [f"recall_preference：召回 {len(recalled)} 条偏好"],
    }


def answer_with_preference_node(state: MemoryState) -> dict:
    if not state["recalled_memories"]:
        answer = "我还没有记录到你的长期偏好。"
    else:
        preference_text = "\n".join(
            f"- {memory['content']}"
            for memory in state["recalled_memories"]
        )

        answer = (
            "我记得你的这些偏好：\n"
            f"{preference_text}\n\n"
            "后续回答我会尽量按这些要求来。"
        )

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["answer_with_preference：回答完成"],
    }


def build_graph():
    graph = StateGraph(
        MemoryState,
        context_schema=MemoryContext,
    )

    graph.add_node("recall_preference", recall_preference_node)
    graph.add_node("answer_with_preference", answer_with_preference_node)

    graph.add_edge(START, "recall_preference")
    graph.add_edge("recall_preference", "answer_with_preference")
    graph.add_edge("answer_with_preference", END)

    store = InMemoryStore()
    checkpointer = InMemorySaver()

    app = graph.compile(
        store=store,
        checkpointer=checkpointer,
    )

    return app, store


def main():
    app, store = build_graph()

    tenant_id = "tenant_001"
    user_id = "u_10001"
    namespace = (tenant_id, user_id, "preferences")

    store.put(
        namespace,
        "answer_style",
        {
            "type": "preference",
            "content": "回答要口语化，不要太像官方文档。",
            "confidence": 0.95,
            "source": "manual_seed",
        },
    )

    store.put(
        namespace,
        "code_style",
        {
            "type": "preference",
            "content": "涉及代码时，要给完整可运行示例。",
            "confidence": 0.95,
            "source": "manual_seed",
        },
    )

    result = app.invoke(
        create_initial_memory_state("你记得我的偏好吗？"),
        config={
            "configurable": {
                "thread_id": "thread_recall_preference_demo"
            }
        },
        context=MemoryContext(
            tenant_id=tenant_id,
            user_id=user_id,
        ),
    )

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
scripts/test_lg36_08_recall_user_preference.py
```

写入：

```python
from app.langgraph_memory.demo_08_recall_user_preference import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子演示召回长期偏好。

后面真实项目里，召回记忆后一般不会直接全部展示给用户。

而是把它放进 system prompt 或上下文里，用来影响回答风格。

比如：

```plain
用户喜欢口语化
用户喜欢完整代码
用户不要 AI 味
```

这些会影响最终生成。

---

# 二十五、21｜电商客服 Agent Memory 设计
电商客服 Agent 的记忆可以分成三类。

## 第一类：短期会话记忆
```plain
当前对话 messages
当前订单号
当前退款流程状态
当前等待用户补充什么
当前工具结果
```

## 第二类：长期用户偏好
```plain
用户常用语言
用户喜欢简短回答
用户偏好物流公司
用户希望先给结论再解释
用户是否经常需要人工客服
```

## 第三类：历史行为记忆
```plain
用户最近咨询过退款
用户上次订单投诉过物流
用户多次询问售后流程
```

---

## 【重点内容】
做企业客服 Agent，一定不要只记聊天记录。

真正有价值的是：

```plain
用户偏好
用户习惯
用户历史行为
用户当前流程状态
```

比如用户经常投诉物流慢，或者用户总是要找人工客服。

这些都可以作为后续客服体验优化的输入。

但也要注意隐私和合规。

---

# 二十六、22｜示例九：电商客服 Memory Graph
打开：

```plain
app/langgraph_memory/demo_09_ecommerce_memory_graph.py
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

from app.langgraph_memory.schemas import (
    MemoryContext,
    MemoryState,
    create_initial_memory_state,
)


def classify_intent_node(state: MemoryState) -> dict:
    question = state["user_question"]

    if "记住" in question or "以后" in question:
        intent = "remember_preference"
    elif "我的偏好" in question or "你记得" in question:
        intent = "recall_preference"
    elif "订单" in question or "退款" in question or "物流" in question:
        intent = "ecommerce_service"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：intent={intent}"],
    }


def route_by_intent(
    state: MemoryState,
) -> Literal["remember", "recall", "service", "general"]:
    if state["intent"] == "remember_preference":
        return "remember"

    if state["intent"] == "recall_preference":
        return "recall"

    if state["intent"] == "ecommerce_service":
        return "service"

    return "general"


def write_memory_node(
    state: MemoryState,
    runtime: Runtime[MemoryContext],
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

    runtime.store.put(namespace, key, memory)

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
        "logs": [f"write_memory：写入偏好 key={key}"],
    }


def recall_memory_node(
    state: MemoryState,
    runtime: Runtime[MemoryContext],
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
        "logs": [f"recall_memory：召回 {len(memories)} 条记忆"],
    }


def answer_recall_node(state: MemoryState) -> dict:
    if not state["recalled_memories"]:
        answer = "我现在还没有记录到你的长期偏好。"
    else:
        text = "\n".join(
            f"- {memory['content']}"
            for memory in state["recalled_memories"]
        )
        answer = f"我记得你的偏好：\n{text}"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["answer_recall：回答偏好记忆"],
    }


def ecommerce_service_node(state: MemoryState) -> dict:
    preference_text = "\n".join(
        memory["content"]
        for memory in state["recalled_memories"]
    )

    if preference_text:
        answer = (
            "我会结合你的偏好来回答。\n"
            f"你的偏好：{preference_text}\n\n"
            "针对电商客服问题：我会先给结论，再补充处理建议。"
        )
    else:
        answer = (
            "这是电商客服问题。"
            "我会先判断订单、退款或物流场景，再给处理建议。"
        )

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["ecommerce_service：结合记忆完成客服回答"],
    }


def general_answer_node(state: MemoryState) -> dict:
    answer = "这是普通问题，可以走普通 ChatModel。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["general_answer：普通回答"],
    }


def build_graph():
    graph = StateGraph(
        MemoryState,
        context_schema=MemoryContext,
    )

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("write_memory", write_memory_node)
    graph.add_node("recall_memory", recall_memory_node)
    graph.add_node("answer_recall", answer_recall_node)
    graph.add_node("ecommerce_service", ecommerce_service_node)
    graph.add_node("general_answer", general_answer_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "remember": "write_memory",
            "recall": "recall_memory",
            "service": "recall_memory",
            "general": "general_answer",
        },
    )

    graph.add_conditional_edges(
        "recall_memory",
        lambda state: "answer_recall" if state["intent"] == "recall_preference" else "service",
        {
            "answer_recall": "answer_recall",
            "service": "ecommerce_service",
        },
    )

    graph.add_edge("write_memory", END)
    graph.add_edge("answer_recall", END)
    graph.add_edge("ecommerce_service", END)
    graph.add_edge("general_answer", END)

    store = InMemoryStore()
    checkpointer = InMemorySaver()

    app = graph.compile(
        store=store,
        checkpointer=checkpointer,
    )

    return app, store


def main():
    app, store = build_graph()

    context = MemoryContext(
        tenant_id="tenant_001",
        user_id="u_10001",
    )

    config = {
        "configurable": {
            "thread_id": "thread_ecommerce_memory_demo"
        }
    }

    first = app.invoke(
        create_initial_memory_state(
            "记住：以后回答客服问题，先给结论，再给处理步骤。"
        ),
        config=config,
        context=context,
    )

    print("first:")
    print(first["final_answer"])
    print("=" * 80)

    second = app.invoke(
        create_initial_memory_state(
            "你记得我的偏好吗？"
        ),
        config=config,
        context=context,
    )

    print("second:")
    print(second["final_answer"])
    print("=" * 80)

    third = app.invoke(
        create_initial_memory_state(
            "我的订单 10002 可以退款吗？"
        ),
        config=config,
        context=context,
    )

    print("third:")
    print(third["final_answer"])
    print("=" * 80)

    print("logs:")
    for log in third["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg36_09_ecommerce_memory_graph.py
```

写入：

```python
from app.langgraph_memory.demo_09_ecommerce_memory_graph import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个综合示例有三个动作。

第一轮：

```plain
用户要求记住客服回答偏好。
```

第二轮：

```plain
用户询问你记得我的偏好吗。
```

第三轮：

```plain
用户问电商客服问题。
```

Graph 会先召回长期记忆，再结合记忆生成客服回答。

这就是 Memory 在真实 Agent 里的用法。

---

# 二十七、23｜Memory 写入策略
不是所有信息都要写入长期记忆。

推荐写入：

```plain
1. 用户明确要求记住的偏好
2. 多次重复出现的稳定偏好
3. 对未来任务有明显帮助的信息
4. 用户主动确认过的信息
5. 业务上允许保存的信息
```

不推荐写入：

```plain
1. 临时情绪
2. 一次性需求
3. 模糊猜测
4. 敏感信息
5. API Key / 密码 / 令牌
6. 用户没有确认的身份推断
7. 不稳定的短期状态
```

---

## 【重点内容】
记忆不是越多越好。

记忆越多，越容易污染。

比如用户说：

```plain
今天别讲太多。
```

这不代表他永远喜欢短回答。

再比如用户说：

```plain
我现在很烦。
```

你也不应该长期记住“用户脾气不好”。

Memory 一定要谨慎。

---

# 二十八、24｜Memory 召回策略
召回长期记忆时也不要全量塞进去。

推荐：

```plain
1. 只召回当前任务相关记忆
2. 限制数量，比如 top 3 / top 5
3. 按 namespace 隔离
4. 按 memory type 过滤
5. 低置信度记忆不要直接使用
6. 敏感记忆不要进入 Prompt
```

如果 Store 开启 semantic search，可以根据 query 召回相关记忆；官方示例也展示了带 embedding 的 InMemoryStore，通过 `store.search(namespace, query=..., limit=...)` 按语义相似度召回。

---

# 二十九、25｜Memory Namespace 设计
推荐 namespace：

```python
namespace = (
    tenant_id,
    user_id,
    memory_type,
)
```

例如：

```python
("tenant_001", "u_10001", "preferences")
("tenant_001", "u_10001", "profile")
("tenant_001", "u_10001", "behavior")
```

不推荐：

```python
("memories",)
("preferences",)
(user_id,)
```

---

## 【重点内容】
namespace 一定要有隔离意识。

企业项目里至少要有：

```plain
tenant_id
user_id
memory_type
```

多租户项目如果漏了 tenant_id，就可能串租户。

如果漏了 user_id，就可能串用户。

这类问题非常严重。

---

# 三十、26｜Memory 和权限
不是所有记忆都能被所有节点读取。

比如：

```plain
普通客服节点：
只能读取回答风格偏好。

风控节点：
可以读取风险相关历史行为。

财务节点：
可以读取退款审批历史摘要。

普通 Chat 节点：
不应该读取敏感业务记忆。
```

---

## 【重点内容】
Memory 也要做权限控制。

长期记忆不是一个全局大仓库，谁都能查。

尤其是企业系统里，不同角色、不同 Agent、不同节点应该读取不同 namespace。

比如客服 Agent 不应该随便读取财务审批记忆。

---

# 三十一、27｜Memory 和隐私安全
记忆系统要注意：

```plain
1. 不保存密钥
2. 不保存密码
3. 不保存完整身份证
4. 不保存完整银行卡
5. 不保存超出业务必要范围的信息
6. 支持用户删除记忆
7. 支持后台查看和审计
8. 支持租户隔离
9. 支持记忆过期
10. 支持记忆来源追踪
```

---

## 【重点内容】
Memory 是很敏感的能力。

因为你在长期保存用户信息。

所以企业项目一定要有：

```plain
可查看
可删除
可过期
可审计
可解释
```

不能悄悄记一堆东西。

---

# 三十二、28｜Memory 污染问题
Memory 污染指：

```plain
Agent 记住了错误、不稳定、不该记的信息，
后续一直影响回答。
```

例子：

```plain
用户临时说“今天回答短一点”
Agent 长期记成“用户永远喜欢短回答”
```

解决方式：

```plain
1. 明确记忆写入条件
2. 给记忆加 confidence
3. 给记忆加 source
4. 支持更新和删除
5. 对重要记忆要求用户确认
6. 低置信度记忆不直接影响回答
```

---

# 三十三、29｜Memory 和数据库的关系
| 类型 | 存什么 |
| --- | --- |
| Store | 长期记忆 JSON |
| Checkpoint | 短期 thread state |
| chat_messages | 原始聊天记录 |
| user_profiles | 用户正式资料 |
| memory_audit_logs | 记忆写入、更新、删除审计 |
| knowledge_base | 企业知识文档 |


---

## 【重点内容】
长期记忆可以存在 LangGraph Store。

但是正式用户资料不一定只放 Store。

比如：

```plain
用户手机号
会员等级
收货地址
```

这些应该在业务数据库里。

Store 更适合保存 Agent 使用的记忆片段。

---

# 三十四、30｜Memory 和 RAG 的协作
一个好的回答可能同时用：

```plain
Memory：
用户希望先给结论再给步骤。

RAG：
售后规则说未发货订单可以退款。

Tool：
订单 10002 状态是待发货。
```

最终回答：

```plain
结论：你的订单目前可以申请退款。

原因：订单 10002 当前是已付款、待发货状态。根据售后规则，未发货订单可以申请取消订单并退款。

处理方式：你可以在订单详情页点击申请退款，也可以让我帮你转人工。
```

---

## 【重点内容】
这就是企业 Agent 的组合能力。

Memory 负责个性化。

RAG 负责知识准确。

Tool 负责业务实时数据。

Graph 负责流程编排。

这几个合起来，才是完整 Agent。

---

# 三十五、31｜封装 Memory Service
打开：

```plain
app/langgraph_memory/service.py
```

写入：

```python
from app.langgraph_memory.demo_09_ecommerce_memory_graph import build_graph
from app.langgraph_memory.schemas import (
    MemoryContext,
    create_initial_memory_state,
)


class LangGraphMemoryService:
    def __init__(self):
        self.graph, self.store = build_graph()

    def build_thread_id(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
    ) -> str:
        return f"{tenant_id}:{user_id}:{conversation_id}"

    def chat(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: str,
        question: str,
    ) -> dict:
        thread_id = self.build_thread_id(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        result = self.graph.invoke(
            create_initial_memory_state(question),
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            },
            context=MemoryContext(
                tenant_id=tenant_id,
                user_id=user_id,
            ),
        )

        return {
            "thread_id": thread_id,
            "answer": result["final_answer"],
            "intent": result["intent"],
            "recalled_memories": result["recalled_memories"],
            "new_memories": result["new_memories"],
            "logs": result["logs"],
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

        items = self.store.search(namespace)

        return [
            {
                "key": item.key,
                "value": item.value,
            }
            for item in items
        ]


langgraph_memory_service = LangGraphMemoryService()
```

创建测试脚本：

```plain
scripts/test_lg36_10_memory_service.py
```

写入：

```python
from app.langgraph_memory.service import langgraph_memory_service


def main():
    tenant_id = "tenant_001"
    user_id = "u_10001"
    conversation_id = "conv_memory_001"

    first = langgraph_memory_service.chat(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question="记住：以后回答客服问题，先给结论，再给处理步骤。",
    )

    print("first:")
    print(first)
    print("=" * 80)

    second = langgraph_memory_service.chat(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question="你记得我的偏好吗？",
    )

    print("second:")
    print(second)
    print("=" * 80)

    memories = langgraph_memory_service.list_memories(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    print("memories:")
    for memory in memories:
        print(memory)


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg36_10_memory_service.py
```

---

# 三十六、32｜创建 Memory API
创建：

```plain
app/api/v1/langgraph_memory.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langgraph_memory.service import langgraph_memory_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class MemoryChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")


@router.post(
    "/langgraph/memory/chat",
    response_model=ApiResponse[dict],
)
async def memory_chat(
    request: MemoryChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langgraph_memory_service.chat(
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
        question=request.question,
    )

    return ApiResponse[dict](
        data=result
    )


@router.get(
    "/langgraph/memory/list",
    response_model=ApiResponse[list[dict]],
)
async def list_memory(
    tenant_id: str = "tenant_001",
    memory_type: str = "preferences",
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[list[dict]]:
    result = langgraph_memory_service.list_memories(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        memory_type=memory_type,
    )

    return ApiResponse[list[dict]](
        data=result
    )
```

---

# 三十七、33｜注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langgraph_memory import router as langgraph_memory_router
```

注册：

```python
api_router.include_router(
    langgraph_memory_router,
    tags=["LangGraph Memory"],
)
```

---

# 三十八、34｜测试 Memory API
启动：

```bash
uv run uvicorn app.main:app --reload
```

写入偏好：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/memory/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_memory_001",
    "question": "记住：以后回答客服问题，先给结论，再给处理步骤。"
  }'
```

召回偏好：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/memory/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_memory_001",
    "question": "你记得我的偏好吗？"
  }'
```

查看记忆列表：

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/langgraph/memory/list" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

---

# 三十九、35｜生产环境 Store 选择
教学：

```plain
InMemoryStore
```

生产：

```plain
PostgresStore
RedisStore
自定义 BaseStore
```

如果使用数据库型 Store，需要根据具体 Store 实现运行 setup / migration。官方文档也建议数据库型 checkpointer 或 Store 在使用前运行 schema migration，一般通过 `setup()` 完成。

---

# 四十、36｜PostgresStore 示例
生产环境可以这样写：

```python
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5432/ai_agent?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()

    namespace = ("tenant_001", "u_10001", "preferences")

    store.put(
        namespace,
        "answer_style",
        {
            "type": "preference",
            "content": "用户喜欢先给结论，再给步骤。",
            "confidence": 0.95,
            "source": "user_explicit_request",
        },
    )

    items = store.search(namespace)
```

---

## 【重点内容】
本课程示例用 InMemoryStore 是为了方便教学。

但是生产不要用 InMemoryStore。

服务一重启，记忆就没了。

多实例部署时，每个实例的内存也不共享。

生产推荐数据库型 Store。

---

# 四十一、37｜Memory 常见错误一：把所有消息都永久保存进 Prompt
错误：

```plain
每次调用模型都带全量 messages。
```

问题：

```plain
慢
贵
容易超上下文
旧信息干扰回答
```

正确：

```plain
最近 messages + summary + 相关长期记忆
```

---

# 四十二、38｜常见错误二：用户随便说一句就长期记忆
错误：

```plain
用户说“今天少说点”
长期记成“用户永远喜欢短回答”
```

正确：

```plain
明确记住
重复出现
用户确认
高置信度
才写长期记忆
```

---

# 四十三、39｜常见错误三：没有 namespace 隔离
错误：

```python
namespace = ("preferences",)
```

正确：

```python
namespace = (tenant_id, user_id, "preferences")
```

---

# 四十四、40｜常见错误四：长期记忆和业务资料混在一起
错误：

```plain
把退款规则写入 user memory。
```

正确：

```plain
退款规则放 RAG 知识库。
用户偏好放 Memory。
```

---

# 四十五、41｜常见错误五：不支持删除记忆
用户有权要求：

```plain
忘记这个偏好
删除我的记忆
不要再用这个信息
```

所以系统应该支持：

```plain
memory delete
memory update
memory audit
memory expire
```

---

# 四十六、42｜常见错误六：把敏感信息写入长期记忆
不要保存：

```plain
密码
API Key
Token
完整身份证
完整银行卡
完整地址
高度敏感隐私
```

---

# 四十七、43｜常见错误七：召回太多记忆
错误：

```plain
把用户所有长期记忆都塞给模型。
```

正确：

```plain
只召回和当前任务相关的 top 3 / top 5。
```

---

# 四十八、44｜面试回答：Agent Memory 怎么理解
## 回答话术一：基础版
```plain
Agent Memory 可以理解成 Agent 对上下文和用户信息的保存与召回能力。

在 LangGraph 里，一般分成短期记忆和长期记忆。

短期记忆是 thread 级别的，比如当前会话 messages、当前任务状态，它通常作为 State 的一部分，通过 checkpointer 保存。

长期记忆是跨会话的，比如用户偏好、长期稳定事实，它通常通过 LangGraph Store 保存，按照 namespace 和 key 组织。
```

---

## 回答话术二：项目版
```plain
比如电商客服 Agent 里，短期记忆可以保存当前退款流程状态：用户说要退款、系统追问订单号、用户补充订单号，然后继续退款流程。

长期记忆可以保存用户偏好，比如用户希望客服回答先给结论，再给处理步骤，或者用户喜欢简短回复。

当用户下一次再来咨询订单问题时，Agent 可以先从 Store 里召回这些偏好，再结合订单工具和售后知识库生成更符合用户习惯的回答。
```

---

## 回答话术三：工程版
```plain
工程上我会把 Memory 分层设计。

第一层是 short-term memory，放在 State 里，用 messages 和 checkpointer 管理，thread_id 负责会话隔离。

第二层是 long-term memory，放到 Store 里，用 namespace 做租户和用户隔离，比如 tenant_id:user_id:preferences。

第三层是知识库 RAG，保存企业文档和业务规则，不和用户 memory 混在一起。

同时要控制记忆写入策略，只有明确、稳定、对未来有帮助的信息才写入长期记忆，并且支持删除、更新、审计和权限隔离。
```

---

# 四十九、45｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Short-term Memory | 第 34 章 Persistence |
| messages | 第 22 章 Message |
| add_messages | 第 31 章 State |
| checkpointer | 第 34 章 Checkpoint |
| thread_id | 第 34 章 Thread |
| Long-term Memory | Store |
| InMemoryStore | 本章长期记忆 |
| Runtime | 第 32 章 Node 读取上下文 |
| namespace | 多租户隔离 |
| trim_messages | 长对话管理 |
| summary memory | 上下文压缩 |
| 用户偏好 | 个性化 Agent |
| Memory vs RAG | 第 27 章 RAG |
| 电商客服记忆 | 第 38 章项目二基础 |


---

# 五十、46｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Agent Memory 是什么
2. 区分 Memory 和 Persistence
3. 区分 Memory 和 RAG
4. 理解 Short-term Memory
5. 理解 Long-term Memory
6. 理解 Semantic / Episodic / Procedural Memory
7. 创建 langgraph_memory 目录
8. 定义 MemoryState
9. 实现短期 messages 记忆
10. 验证 thread 记忆隔离
11. 理解长对话为什么需要管理
12. 使用 trim_messages 裁剪上下文
13. 设计 summary memory
14. 理解 Store 的 namespace + key + value
15. 使用 InMemoryStore
16. 在 Node 中通过 Runtime 访问 Store
17. 写入用户偏好记忆
18. 召回用户偏好记忆
19. 设计电商客服 Memory Graph
20. 封装 Memory Service
21. 创建 Memory API
22. 测试 Memory API
23. 理解生产环境 Store 选择
24. 理解 PostgresStore
25. 总结 Memory 写入策略
26. 总结 Memory 召回策略
27. 总结 namespace 设计
28. 理解 Memory 权限和隐私
29. 理解 Memory 污染问题
30. 理解 Memory 和数据库的关系
31. 理解 Memory 和 RAG 的协作
32. 总结常见错误
33. 准备面试回答话术
```

---

# 五十一、47｜课后任务一：跑通短期记忆
要求：

```plain
1. 运行 scripts/test_lg36_01_short_term_memory.py
2. 两轮 invoke 使用同一个 thread_id
3. 查看 messages 是否累加
4. 说明 add_messages 和 checkpointer 的作用
```

---

# 五十二、48｜课后任务二：验证 thread 记忆隔离
要求：

```plain
1. 运行 scripts/test_lg36_02_thread_memory_isolation.py
2. 比较 thread_user_a 和 thread_user_b
3. 说明为什么短期记忆必须按 thread_id 隔离
```

---

# 五十三、49｜课后任务三：测试 trim_messages
要求：

```plain
1. 运行 scripts/test_lg36_03_trim_messages.py
2. 增加更多对话轮次
3. 调整 max_tokens
4. 观察裁剪后消息数量变化
```

---

# 五十四、50｜课后任务四：测试摘要记忆
要求：

```plain
1. 运行 scripts/test_lg36_04_summary_memory.py
2. 查看 short_summary 什么时候生成
3. 思考真实项目里应该如何用模型生成摘要
4. 说明摘要记忆可能带来的风险
```

---

# 五十五、51｜课后任务五：测试 Store 基础操作
要求：

```plain
1. 运行 scripts/test_lg36_05_store_basic.py
2. 查看 put / get / search 的结果
3. 修改 namespace
4. 观察不同 namespace 是否隔离
```

---

# 五十六、52｜课后任务六：测试 Runtime 读取 Store
要求：

```plain
1. 运行 scripts/test_lg36_06_runtime_store_node.py
2. 查看 recall_memory_node 如何读取 runtime.context.user_id
3. 查看 runtime.store.search 如何召回记忆
4. 说明 context 和 State 的区别
```

---

# 五十七、53｜课后任务七：测试写入用户偏好
要求：

```plain
1. 运行 scripts/test_lg36_07_write_user_preference.py
2. 输入“记住：以后回答要口语化”
3. 查看 Store 里是否写入记忆
4. 思考什么情况不应该写入长期记忆
```

---

# 五十八、54｜课后任务八：测试召回用户偏好
要求：

```plain
1. 运行 scripts/test_lg36_08_recall_user_preference.py
2. 查看召回了哪些偏好
3. 增加一个新的偏好
4. 观察回答是否变化
```

---

# 五十九、55｜课后任务九：跑通电商客服 Memory Graph
要求：

```plain
1. 运行 scripts/test_lg36_09_ecommerce_memory_graph.py
2. 第一轮写入客服回答偏好
3. 第二轮询问是否记得偏好
4. 第三轮询问订单退款问题
5. 查看客服回答是否结合记忆
```

---

# 六十、56｜课后任务十：设计记忆删除接口
要求设计：

```plain
DELETE /api/v1/langgraph/memory/{memory_key}
```

需要考虑：

```plain
1. 只能删除当前用户自己的记忆
2. 必须带 tenant_id 和 user_id
3. 删除动作写审计日志
4. 删除后再次召回不应该出现该记忆
```

---

# 六十一、57｜课后任务十一：设计 Memory 审计表
建议表名：

```plain
agent_memory_audit_logs
```

字段：

```plain
id
tenant_id
user_id
memory_namespace
memory_key
action
old_value
new_value
operator_id
created_at
```

---

# 六十二、58｜课后任务十二：设计电商客服记忆类型
要求设计三类记忆：

```plain
preferences：
用户回答风格偏好

behavior：
用户历史行为摘要

profile：
用户可用于客服体验优化的非敏感画像
```

并说明：

```plain
哪些可以自动写入；
哪些必须用户确认；
哪些不能写入。
```

---

# 六十三、59｜本章总结
## 【重点内容】
好了，到这里，第 36 章我们就讲完了。

这一章我们讲的是 LangGraph Agent Memory。

大家一定要记住：

```plain
Memory 不是简单保存聊天记录。
Memory 是 Agent 对上下文、偏好和长期信息的保存与召回能力。
```

Memory 最重要的分类是：

```plain
Short-term Memory：
短期记忆，thread 级别，通常放在 State 里，通过 checkpointer 保存。

Long-term Memory：
长期记忆，跨 thread、跨 session，通常放在 Store 里，通过 namespace 和 key 管理。
```

同时要区分：

```plain
Persistence 解决状态恢复。
Memory 解决记住用户。
RAG 解决知识检索。
```

真正企业 Agent 里，三者会一起用：

```plain
Persistence：
让流程可恢复。

Memory：
让 Agent 个性化。

RAG：
让回答有知识依据。

Tool：
让 Agent 获取实时业务数据。

LangGraph：
把这些能力编排起来。
```

最后一定要记住：

```plain
记忆不是越多越好。
长期记忆必须谨慎写入、权限隔离、支持删除、支持审计。
```

---
