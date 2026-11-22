---
title: "第 30 章｜LangGraph 核心概念"
chapter: "30"
source: "第 30 章｜LangGraph 核心概念.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langgraph
  - state
  - reducer
---

# 第 30 章｜LangGraph 核心概念

> [!abstract] 本章重点
>
> - ==StateGraph 是入口，compile 后才能 invoke== — 先声明图，再编译成可运行对象。
> - ==Node 是函数，输入输出都围绕 State== — 每个节点只做一件事，返回 State 的局部更新。
> - ==Edge 决定下一步走哪== — 固定边走顺序，条件边按 State 动态选。
> - ==Reducer 决定同名字段怎么合并== — 默认覆盖，add_messages 改成追加。
> - ==MessagesState 内置消息追加规则== — 多轮对话不用自己写 Reducer。

> [!note] 大白话
>
> - **Reducer**：规定「同一个字段被多个节点写」时，是覆盖还是累加。

> [!info] 导航与来源
> - 原始讲义：[[第 30 章｜LangGraph 核心概念|打开原始讲义]]
> - [[第 29 章｜为什么需要 LangGraph|上一章｜第 29 章]]
> - [[第 31 章｜LangGraph State|下一章｜第 31 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#LangGraph 核心概念]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜LangGraph 最小心智模型]]
- [[#七、03｜创建 langgraph_core 目录]]
- [[#八、04｜概念一：StateGraph]]
- [[#九、05｜示例一：最小 StateGraph]]
- [[#十、06｜概念二：State]]
- [[#十一、07｜示例二：State 局部更新]]
- [[#十二、08｜概念三：Node]]
- [[#十三、09｜概念四：Edge]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们讲了：

```text
第 29 章｜为什么需要 LangGraph
```

重点回答了一个问题：

```text
为什么已经有 LangChain Agent 了，还要学 LangGraph？
```

结论是：

```text
LangChain Agent 适合快速实现 Agent；
LangGraph 适合复杂、可控、可恢复、可观察的企业级 Agent 流程。
```

这一章开始，我们不再只讲“为什么”。

而是进入：

## LangGraph 核心概念
这一章会把 LangGraph 最常用的基础语法讲清楚：

```markdown
StateGraph
State
Node
Edge
START
END
Reducer
add_messages
Command
Checkpointer
RunnableConfig
stream_mode
compile
invoke
stream
```

这章学完以后，后面第 31～38 章再深入 State、Node、Edge、条件路由、持久化、人工确认、多 Agent，就会顺很多。

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. StateGraph 是什么
2. State 是什么
3. Node 是什么
4. Edge 是什么
5. START / END 是什么
6. compile 的作用是什么
7. invoke 和 ainvoke 怎么用
8. stream 和 astream 怎么用
9. 普通字段状态如何更新
10. list 类型状态为什么需要 Reducer
11. add_messages 是什么
12. Command 是什么
13. Command 和 conditional edge 的区别
14. Checkpointer 是什么
15. thread_id 为什么重要
16. RunnableConfig 怎么传递上下文
17. stream_mode=updates 和 values 有什么区别
18. 如何打印 Graph 执行过程
19. 如何把 LangGraph 和第 19 章项目一关联起来
20. 面试时如何讲 LangGraph 核心概念
```

---

## 三、本章版本口径
本课程 LangGraph 阶段统一使用：

```text
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
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
```

LangGraph 官方 Graph API 文档说明，State 可以用 `TypedDict`、Pydantic model 或 dataclass 定义；Node 通常是 Python 函数，它读取当前 State 并返回更新；Graph 可以通过 normal edges、conditional edges、entry point 等方式控制执行流。

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langgraph_core/
│   │   ├── __init__.py
│   │   ├── demo_01_minimal_graph.py
│   │   ├── demo_02_state_update.py
│   │   ├── demo_03_sequence_graph.py
│   │   ├── demo_04_conditional_edges.py
│   │   ├── demo_05_reducer.py
│   │   ├── demo_06_messages_state.py
│   │   ├── demo_07_command.py
│   │   ├── demo_08_stream_updates.py
│   │   ├── demo_09_checkpointer.py
│   │   ├── demo_10_runnable_config.py
│   │   ├── demo_11_async_graph.py
│   │   └── demo_12_ecommerce_core_graph.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg30_01_minimal_graph.py
│   ├── test_lg30_02_state_update.py
│   ├── test_lg30_03_sequence_graph.py
│   ├── test_lg30_04_conditional_edges.py
│   ├── test_lg30_05_reducer.py
│   ├── test_lg30_06_messages_state.py
│   ├── test_lg30_07_command.py
│   ├── test_lg30_08_stream_updates.py
│   ├── test_lg30_09_checkpointer.py
│   ├── test_lg30_10_runnable_config.py
│   ├── test_lg30_11_async_graph.py
│   └── test_lg30_12_ecommerce_core_graph.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 30 章。

==这一章我们正式进入 LangGraph 核心概念。==

上一章我们已经知道，LangGraph 主要解决复杂 Agent 的状态编排问题。

但很多同学第一次看 LangGraph 会觉得：

```text
StateGraph 是什么？
State 是什么？
Node 是什么？
Edge 是什么？
START 和 END 又是什么？
为什么还要 compile？
stream_mode 又是干什么的？
```

这一章就专门把这些基础概念拆开讲。

大家不要一上来就想着做复杂 Agent。

先把最小图跑通。

然后再理解状态更新、条件分支、Reducer、Command、Checkpointer、Streaming。

这些概念一旦打通，后面做电商客服 Agent、Human-in-the-loop、多 Agent，就会很自然。

---

## 六、02｜LangGraph 最小心智模型
### 【实操】
```text
LangGraph
=
State
+
Node
+
Edge
```

展开：

```text
State：
当前执行上下文

Node：
处理 State 的函数

Edge：
决定下一个节点是谁
```

再展开：

```text
输入 State
 ↓
Node A 执行，返回部分 State 更新
 ↓
Edge 决定走到 Node B
 ↓
Node B 执行，继续更新 State
 ↓
直到 END
```

---

### 【重点内容】
==大家先记住这个最小模型。==

LangGraph 其实不是特别神秘。

它就是把一个复杂流程拆成三块：

```text
第一块：State，保存所有上下文。
第二块：Node，每个节点处理一小步。
第三块：Edge，控制节点之间怎么走。
```

以前我们写 if/else，是把流程写在一个函数里。

LangGraph 是把流程拆成图。

所以它更适合复杂 Agent。

---

## 七、03｜创建 langgraph_core 目录
执行：

```bash
mkdir -p app/langgraph_core

touch app/langgraph_core/__init__.py
touch app/langgraph_core/demo_01_minimal_graph.py
touch app/langgraph_core/demo_02_state_update.py
touch app/langgraph_core/demo_03_sequence_graph.py
touch app/langgraph_core/demo_04_conditional_edges.py
touch app/langgraph_core/demo_05_reducer.py
touch app/langgraph_core/demo_06_messages_state.py
touch app/langgraph_core/demo_07_command.py
touch app/langgraph_core/demo_08_stream_updates.py
touch app/langgraph_core/demo_09_checkpointer.py
touch app/langgraph_core/demo_10_runnable_config.py
touch app/langgraph_core/demo_11_async_graph.py
touch app/langgraph_core/demo_12_ecommerce_core_graph.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_core

New-Item app\langgraph_core\__init__.py
New-Item app\langgraph_core\demo_01_minimal_graph.py
New-Item app\langgraph_core\demo_02_state_update.py
New-Item app\langgraph_core\demo_03_sequence_graph.py
New-Item app\langgraph_core\demo_04_conditional_edges.py
New-Item app\langgraph_core\demo_05_reducer.py
New-Item app\langgraph_core\demo_06_messages_state.py
New-Item app\langgraph_core\demo_07_command.py
New-Item app\langgraph_core\demo_08_stream_updates.py
New-Item app\langgraph_core\demo_09_checkpointer.py
New-Item app\langgraph_core\demo_10_runnable_config.py
New-Item app\langgraph_core\demo_11_async_graph.py
New-Item app\langgraph_core\demo_12_ecommerce_core_graph.py
```

---

## 八、04｜概念一：StateGraph
### 【实操】
```python
graph = StateGraph(State)
```

它表示：

```text
我要创建一个基于 State 的图。
```

---

### 【重点内容】
StateGraph 是 LangGraph 最常用的图构建入口。

你可以把它理解成：

```text
图的草稿
```

注意，它还不能直接执行。

你需要：

```python
compiled_graph = graph.compile()
```

compile 以后，才得到真正可以执行的图。

官方 StateGraph 参考文档也说明，需要先调用 `.compile()` 创建可执行图，编译后的图才支持 `invoke()`、`stream()`、`ainvoke()`、`astream()` 等方法。

---

## 九、05｜示例一：最小 StateGraph
打开：

```text
app/langgraph_core/demo_01_minimal_graph.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class HelloState(TypedDict):
    user_name: str
    greeting: str


def greeting_node(state: HelloState) -> dict:
    user_name = state["user_name"]

    return {
        "greeting": f"你好，{user_name}，欢迎进入 LangGraph 阶段。"
    }


def build_graph():
    graph = StateGraph(HelloState)

    graph.add_node("greeting", greeting_node)

    graph.add_edge(START, "greeting")
    graph.add_edge("greeting", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_name": "大伟",
        "greeting": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_01_minimal_graph.py
```

写入：

```python
from app.langgraph_core.demo_01_minimal_graph import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_01_minimal_graph.py
```

---

### 【重点内容】
这个例子是最小 LangGraph。

它只有一个节点：

```text
greeting
```

执行顺序是：

```text
START
 ↓
greeting
 ↓
END
```

大家注意四行核心代码：

```python
graph = StateGraph(HelloState)
graph.add_node("greeting", greeting_node)
graph.add_edge(START, "greeting")
graph.add_edge("greeting", END)
```

==这就是 LangGraph 的最基础形态。==

---

## 十、06｜概念二：State
### 【实操】
```python
class HelloState(TypedDict):
    user_name: str
    greeting: str
```

State 表示：

```text
图运行时共享的数据结构。
```

---

### 【重点内容】
State 是 LangGraph 里最重要的概念之一。

你可以把它理解成：

```text
整个流程的上下文对象。
```

比如电商客服流程里，State 可能有：

```text
user_question
intent
order_id
order_info
policy_answer
final_answer
```

每个节点都可以读取 State。

每个节点也可以返回一部分 State 更新。

比如：

```python
return {"intent": "refund"}
```

这表示这个节点只更新了 intent 字段。

不是重新返回完整 State。

---

## 十一、07｜示例二：State 局部更新
打开：

```text
app/langgraph_core/demo_02_state_update.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class ProfileState(TypedDict):
    user_name: str
    role: str
    intro: str


def fill_role_node(state: ProfileState) -> dict:
    return {
        "role": "AI Agent 全栈课程学员"
    }


def generate_intro_node(state: ProfileState) -> dict:
    return {
        "intro": f"{state['user_name']} 是一名 {state['role']}。"
    }


def build_graph():
    graph = StateGraph(ProfileState)

    graph.add_node("fill_role", fill_role_node)
    graph.add_node("generate_intro", generate_intro_node)

    graph.add_edge(START, "fill_role")
    graph.add_edge("fill_role", "generate_intro")
    graph.add_edge("generate_intro", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_name": "小陈",
        "role": "",
        "intro": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_02_state_update.py
```

写入：

```python
from app.langgraph_core.demo_02_state_update import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_02_state_update.py
```

---

### 【重点内容】
这个例子演示 State 的局部更新。

第一个节点：

```python
fill_role_node
```

只返回：

```python
{"role": "AI Agent 全栈课程学员"}
```

第二个节点读取更新后的 role，再生成 intro。

==这就是 LangGraph 的执行方式：==

```text
节点读取当前 State
返回部分字段更新
LangGraph 合并到 State
下一个节点继续读取最新 State
```

---

## 十二、08｜概念三：Node
### 【实操】
```python
def node_name(state: State) -> dict:
    return {
        "some_field": "new value"
    }
```

Node 是：

```text
接收 State，返回 State 更新的函数。
```

---

### 【重点内容】
Node 最好遵循一个原则：

```text
一个节点只做一件事。
```

不要一个节点里又识别意图、又查订单、又查知识库、又生成回答。

推荐拆成：

```text
classify_intent_node
extract_order_id_node
query_order_node
retrieve_policy_node
generate_answer_node
```

这样每一步都清楚，也方便测试和调试。

---

## 十三、09｜概念四：Edge
### 【实操】
```python
graph.add_edge("node_a", "node_b")
```

Edge 表示：

```text
从 node_a 执行完以后，接着执行 node_b。
```

---

### 【重点内容】
Edge 就是节点之间的连线。

最简单的是普通边：

```python
graph.add_edge("fill_role", "generate_intro")
```

表示 fill_role 执行完以后，继续 generate_intro。

还有特殊边：

```python
graph.add_edge(START, "fill_role")
graph.add_edge("generate_intro", END)
```

START 表示图入口。

END 表示图结束。

---

## 十四、10｜示例三：顺序图 Sequence Graph
打开：

```text
app/langgraph_core/demo_03_sequence_graph.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class LessonState(TypedDict):
    topic: str
    outline: str
    script: str
    summary: str


def generate_outline_node(state: LessonState) -> dict:
    return {
        "outline": f"《{state['topic']}》课程大纲：概念、代码、项目、总结。"
    }


def generate_script_node(state: LessonState) -> dict:
    return {
        "script": f"根据大纲生成重点内容：{state['outline']}"
    }


def generate_summary_node(state: LessonState) -> dict:
    return {
        "summary": f"本节课围绕 {state['topic']}，完成了大纲和重点内容。"
    }


def build_graph():
    graph = StateGraph(LessonState)

    graph.add_node("generate_outline", generate_outline_node)
    graph.add_node("generate_script", generate_script_node)
    graph.add_node("generate_summary", generate_summary_node)

    graph.add_edge(START, "generate_outline")
    graph.add_edge("generate_outline", "generate_script")
    graph.add_edge("generate_script", "generate_summary")
    graph.add_edge("generate_summary", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "topic": "LangGraph 核心概念",
        "outline": "",
        "script": "",
        "summary": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_03_sequence_graph.py
```

写入：

```python
from app.langgraph_core.demo_03_sequence_graph import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这是顺序图。

流程非常固定：

```text
生成大纲
 ↓
生成重点内容
 ↓
生成总结
```

这种流程用普通 Edge 就够了。

以后如果业务流程是固定顺序，比如：

```text
上传文件
解析文件
切分 chunk
生成 embedding
写入向量库
```

也可以用这种顺序图表达。

---

## 十五、11｜概念五：Conditional Edges
### 【实操】
```python
graph.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "general": "general_answer",
        "refund": "refund_answer",
    },
)
```

Conditional Edge 表示：

```text
根据 State 的内容，决定下一步走哪里。
```

LangGraph Graph API 文档说明，conditional edge 会在指定节点执行后调用 routing function；routing function 读取当前 State 并返回下一步节点名，或者返回映射字典中的 key。

---

### 【重点内容】
==条件边是复杂 Agent 的核心。==

比如：

```text
intent=general -> general_answer
intent=order -> query_order
intent=refund -> query_order + retrieve_policy
```

如果没有条件边，你只能写一条固定路线。

但真实业务流程经常不是固定的。

所以条件边非常重要。

---

## 十六、12｜示例四：条件路由
打开：

```text
app/langgraph_core/demo_04_conditional_edges.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class IntentState(TypedDict):
    user_question: str
    intent: str
    answer: str


def classify_intent_node(state: IntentState) -> dict:
    question = state["user_question"]

    if "退款" in question:
        intent = "refund"
    elif "订单" in question or "物流" in question:
        intent = "order"
    else:
        intent = "general"

    return {
        "intent": intent
    }


def route_by_intent(
    state: IntentState,
) -> Literal["general", "order", "refund"]:
    return state["intent"]  # type: ignore[return-value]


def general_node(state: IntentState) -> dict:
    return {
        "answer": "这是普通问题，走普通聊天。"
    }


def order_node(state: IntentState) -> dict:
    return {
        "answer": "这是订单问题，应该查询订单工具。"
    }


def refund_node(state: IntentState) -> dict:
    return {
        "answer": "这是退款问题，应该查询订单状态和退款规则。"
    }


def build_graph():
    graph = StateGraph(IntentState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_node", general_node)
    graph.add_node("order_node", order_node)
    graph.add_node("refund_node", refund_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "general_node",
            "order": "order_node",
            "refund": "refund_node",
        },
    )

    graph.add_edge("general_node", END)
    graph.add_edge("order_node", END)
    graph.add_edge("refund_node", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "帮我查一下订单 10001。",
        "我的订单没发货，可以退款吗？",
    ]

    for question in questions:
        result = app.invoke({
            "user_question": question,
            "intent": "",
            "answer": "",
        })

        print("question:", question)
        print("intent:", result["intent"])
        print("answer:", result["answer"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_04_conditional_edges.py
```

写入：

```python
from app.langgraph_core.demo_04_conditional_edges import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_04_conditional_edges.py
```

---

### 【重点内容】
这个示例非常重要。

它展示了 LangGraph 最常见的分支模式：

```text
先识别意图
再根据意图路由
```

这和我们第 24 章 Structured Output 的思路是一致的。

只不过现在它变成了图里的一个节点和条件边。

---

## 十七、13｜概念六：Reducer
### 【实操】
普通字段默认是覆盖：

```python
return {"count": 1}
```

如果下一个节点再返回：

```python
return {"count": 2}
```

最终 count 是：

```text
2
```

但 list 有时候不想覆盖，而是想追加。

这时需要 Reducer。

---

### 【重点内容】
Reducer 是很多人学 LangGraph 时第一个容易卡住的点。

默认情况下，State 字段更新是覆盖。

比如：

```python
{"logs": ["A"]}
```

后面节点返回：

```python
{"logs": ["B"]}
```

如果没有 reducer，最终 logs 可能就是：

```text
["B"]
```

但我们想要的是：

```text
["A", "B"]
```

这时就需要告诉 LangGraph：

```text
这个字段要累加，不要覆盖。
```

LangGraph 文档里也展示了使用 `Annotated` 和 reducer 控制 list 类型状态如何合并；消息列表则常用内置的 `add_messages` reducer。

---

## 十八、14｜示例五：Reducer 追加日志
打开：

```text
app/langgraph_core/demo_05_reducer.py
```

写入：

```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class LogState(TypedDict):
    user_question: str
    logs: Annotated[list[str], operator.add]
    answer: str


def step_one_node(state: LogState) -> dict:
    return {
        "logs": ["step_one：开始分析用户问题。"]
    }


def step_two_node(state: LogState) -> dict:
    return {
        "logs": ["step_two：准备生成最终回答。"]
    }


def answer_node(state: LogState) -> dict:
    return {
        "logs": ["answer：回答生成完成。"],
        "answer": f"你问的是：{state['user_question']}",
    }


def build_graph():
    graph = StateGraph(LogState)

    graph.add_node("step_one", step_one_node)
    graph.add_node("step_two", step_two_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "step_one")
    graph.add_edge("step_one", "step_two")
    graph.add_edge("step_two", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "Reducer 有什么作用？",
        "logs": [],
        "answer": "",
    })

    print("answer:", result["answer"])
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_05_reducer.py
```

写入：

```python
from app.langgraph_core.demo_05_reducer import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这里的关键是：

```python
logs: Annotated[list[str], operator.add]
```

这表示 logs 字段每次更新时，不是覆盖，而是用 `operator.add` 累加。

==所以三个节点分别返回日志，最终 logs 会保留三条。==

后面我们做 Agent 执行记录时，这个能力很常用。

---

## 十九、15｜概念七：MessagesState 和 add_messages
AI Agent 最常见的状态字段是：

```text
messages
```

但是 messages 不是普通 list。

因为它需要支持：

```text
追加消息
更新已有消息
OpenAI message 格式兼容
序列化和反序列化
```

所以 LangGraph 提供了内置的 `add_messages` reducer。官方文档建议在消息列表状态里使用 `add_messages`，它可以处理消息追加、消息格式兼容以及更新已有消息等问题。

---

### 【重点内容】
如果你的 State 里有 messages，不建议简单写：

```python
messages: list
```

更推荐写：

```python
messages: Annotated[list[AnyMessage], add_messages]
```

这样每个节点返回新的消息时，LangGraph 会帮你追加到 messages 中。

这对聊天 Agent 非常重要。

---

## 二十、16｜示例六：messages 状态
打开：

```text
app/langgraph_core/demo_06_messages_state.py
```

写入：

```python
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def assistant_node(state: ChatState) -> dict:
    last_message = state["messages"][-1]

    return {
        "messages": [
            AIMessage(
                content=f"我收到你的问题了：{last_message.content}"
            )
        ]
    }


def build_graph():
    graph = StateGraph(ChatState)

    graph.add_node("assistant", assistant_node)

    graph.add_edge(START, "assistant")
    graph.add_edge("assistant", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "messages": [
            HumanMessage(content="LangGraph 的 add_messages 是什么？")
        ]
    })

    for message in result["messages"]:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_06_messages_state.py
```

写入：

```python
from app.langgraph_core.demo_06_messages_state import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_06_messages_state.py
```

---

### 【重点内容】
这个例子里，我们输入了一条 HumanMessage。

assistant_node 返回了一条 AIMessage。

因为 messages 字段用了：

```python
add_messages
```

==所以最终结果里会同时包含：==

```text
HumanMessage
AIMessage
```

这就是聊天型 Agent 的常见写法。

---

## 二十一、17｜概念八：Command
### 【实操】
```python
return Command(
    update={"intent": "refund"},
    goto="refund_node",
)
```

Command 可以同时做两件事：

```text
1. 更新 State
2. 指定下一步去哪个节点
```

LangGraph 文档说明，如果想在同一个函数里同时做状态更新和路由跳转，可以使用 `Command`；它可以作为 conditional edges 的替代方案。

---

### 【重点内容】
一般情况下，我们用：

```text
节点返回 State 更新
条件边负责路由
```

但有时候你想在一个节点里同时决定：

```text
我要更新什么状态
下一步要去哪里
```

这时就可以用 Command。

不过建议初学者先用 conditional edges。

Command 等你熟悉以后再用。

---

## 二十二、18｜示例七：Command 路由
打开：

```text
app/langgraph_core/demo_07_command.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


class CommandState(TypedDict):
    user_question: str
    intent: str
    answer: str


def router_node(
    state: CommandState,
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


def general_node(state: CommandState) -> dict:
    return {
        "answer": "这是普通问题。"
    }


def refund_node(state: CommandState) -> dict:
    return {
        "answer": "这是退款问题，后续需要查询订单状态和退款规则。"
    }


def build_graph():
    graph = StateGraph(CommandState)

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
            "intent": "",
            "answer": "",
        })

        print("question:", question)
        print(result)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_07_command.py
```

写入：

```python
from app.langgraph_core.demo_07_command import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子没有使用 add_conditional_edges。

router_node 直接返回 Command。

Command 里：

```python
update={"intent": "refund"}
goto="refund_node"
```

表示更新 intent，然后跳转 refund_node。

Command 很适合一些“边判断边更新”的场景。

但不要滥用。

==如果路由逻辑很复杂，还是建议单独写 routing function。==

---

## 二十三、19｜概念九：compile
### 【实操】
```python
compiled_graph = graph.compile()
```

compile 之后图才可以执行。

常见执行方法：

```text
invoke
ainvoke
stream
astream
batch
```

---

### 【重点内容】
StateGraph 本身只是构建器。

你加节点、加边，都是在搭图。

真正要运行，需要 compile。

compile 会把图变成一个可执行对象。

这个对象可以像 LangChain Runnable 一样调用。

所以后面我们常看到：

```python
app = build_graph()
result = app.invoke(...)
```

这里的 app 就是 compile 后的图。

---

## 二十四、20｜概念十：stream
LangGraph 的 stream 很适合观察执行过程。

常见模式：

```python
for chunk in app.stream(input_state, stream_mode="updates"):
    print(chunk)
```

`updates` 通常输出每一步节点返回的状态更新；`values` 则输出每一步之后的完整状态。官方 StreamMode 参考说明，`updates` 会发出节点或任务返回的更新，`values` 会发出每一步后的完整 state。

---

### 【重点内容】
invoke 是一次性拿最终结果。

stream 可以看到中间过程。

对于 Agent 来说，这很重要。

比如你想看到：

```text
classify_intent 返回了什么
query_order 返回了什么
retrieve_policy 返回了什么
generate_answer 返回了什么
```

那就用 stream。

---

## 二十五、21｜示例八：stream_mode=updates
打开：

```text
app/langgraph_core/demo_08_stream_updates.py
```

写入：

```python
from app.langgraph_core.demo_03_sequence_graph import build_graph


def main():
    app = build_graph()

    input_state = {
        "topic": "LangGraph Streaming",
        "outline": "",
        "script": "",
        "summary": "",
    }

    print("stream_mode=updates")
    print("=" * 80)

    for chunk in app.stream(
        input_state,
        stream_mode="updates",
    ):
        print(chunk)

    print("=" * 80)
    print("stream_mode=values")
    print("=" * 80)

    for chunk in app.stream(
        input_state,
        stream_mode="values",
    ):
        print(chunk)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_08_stream_updates.py
```

写入：

```python
from app.langgraph_core.demo_08_stream_updates import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_08_stream_updates.py
```

---

### 【重点内容】
这个示例对比两个模式。

`updates` 输出的是每个节点的更新。

比如：

```json
{"generate_outline": {"outline": "..."}}
```

`values` 输出的是每一步后的完整 State。

比如：

```json
{
  "topic": "...",
  "outline": "...",
  "script": "",
  "summary": ""
}
```

调试时，updates 更轻量。

排查状态时，values 更直观。

---

## 二十六、22｜概念十一：Checkpointer
### 【实操】
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

调用时传：

```python
config = {
    "configurable": {
        "thread_id": "user_10001_session_001"
    }
}
```

LangGraph 的 Persistence 文档说明，checkpointer 会把某个 thread 的 graph state 保存成 checkpoints，适合短期、线程级记忆，比如对话连续性、human-in-the-loop、time travel 和故障恢复；调用图时通常通过 config 传入 `thread_id`。

---

### 【重点内容】
Checkpointer 是 LangGraph 企业级能力的基础。

如果没有 Checkpointer，图执行完就结束了。

如果你要支持：

```text
多轮对话
中断恢复
人工确认
失败重试
状态回放
```

就需要保存状态。

本章先用内存版：

```python
InMemorySaver
```

生产环境要换成 PostgresSaver 或其他持久化方案。

官方文档也提醒，`MemorySaver` / `InMemorySaver` 是内存存储，进程重启后 checkpoint 会丢失，生产环境应该使用持久化 checkpointer。

---

## 二十七、23｜示例九：Checkpointer 保存对话状态
打开：

```text
app/langgraph_core/demo_09_checkpointer.py
```

写入：

```python
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class MemoryChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def chat_node(state: MemoryChatState) -> dict:
    user_message = state["messages"][-1]

    return {
        "messages": [
            AIMessage(
                content=f"我记住这一轮了：{user_message.content}"
            )
        ]
    }


def build_graph():
    graph = StateGraph(MemoryChatState)

    graph.add_node("chat", chat_node)

    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    checkpointer = InMemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
    )


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_demo_001"
        }
    }

    first_result = app.invoke(
        {
            "messages": [
                HumanMessage(content="我叫大伟。")
            ]
        },
        config=config,
    )

    print("first run:")
    for message in first_result["messages"]:
        print(message.type, ":", message.content)

    print("=" * 80)

    second_result = app.invoke(
        {
            "messages": [
                HumanMessage(content="你还记得我刚才说什么吗？")
            ]
        },
        config=config,
    )

    print("second run:")
    for message in second_result["messages"]:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_09_checkpointer.py
```

写入：

```python
from app.langgraph_core.demo_09_checkpointer import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg30_09_checkpointer.py
```

---

### 【重点内容】
这个例子非常重要。

两次 invoke 使用了同一个：

```python
thread_id = "thread_demo_001"
```

==所以第二次调用时，图可以继续沿用这个 thread 的历史状态。==

这就是短期记忆的基础。

注意，本章只是演示 memory checkpointer。

真正项目里，应该把 thread_id 设计成：

```text
user_id + conversation_id
```

比如：

```text
u_10001_conv_abc123
```

这样才能做到每个用户、每个会话独立保存。

---

## 二十八、24｜概念十二：RunnableConfig
### 【实操】
```python
config = {
    "configurable": {
        "thread_id": "thread_001",
        "user_id": "u_10001",
        "tenant_id": "t_001",
    }
}
```

---

### 【重点内容】
RunnableConfig 可以理解成：

```text
这次图运行的配置上下文。
```

最常用的是：

```text
thread_id
```

但你也可以放：

```text
user_id
tenant_id
conversation_id
trace_id
```

节点里如果需要读取 config，可以在节点参数里加 config。

---

## 二十九、25｜示例十：RunnableConfig 传递上下文
打开：

```text
app/langgraph_core/demo_10_runnable_config.py
```

写入：

```python
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph


class ConfigState(TypedDict):
    user_question: str
    answer: str


def answer_node(
    state: ConfigState,
    config: RunnableConfig,
) -> dict:
    configurable = config.get("configurable", {})

    user_id = configurable.get("user_id", "unknown")
    tenant_id = configurable.get("tenant_id", "unknown")
    trace_id = configurable.get("trace_id", "unknown")

    return {
        "answer": (
            f"用户 {user_id} 来自租户 {tenant_id}，"
            f"trace_id={trace_id}，"
            f"问题是：{state['user_question']}"
        )
    }


def build_graph():
    graph = StateGraph(ConfigState)

    graph.add_node("answer", answer_node)

    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        {
            "user_question": "RunnableConfig 有什么用？",
            "answer": "",
        },
        config={
            "configurable": {
                "thread_id": "thread_001",
                "user_id": "u_10001",
                "tenant_id": "tenant_001",
                "trace_id": "trace_abc123",
            }
        },
    )

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_10_runnable_config.py
```

写入：

```python
from app.langgraph_core.demo_10_runnable_config import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子展示了 config 怎么传进节点。

真实项目里，节点里可能需要：

```text
当前用户
租户 ID
trace_id
会话 ID
权限上下文
```

==这些不一定都适合放在 State 里。==

因为 State 是业务流程状态。

config 更像运行上下文。

---

## 三十、26｜概念十三：Async Graph
### 【实操】
```python
result = await app.ainvoke(input_state)

async for chunk in app.astream(input_state):
    ...
```

---

### 【重点内容】
FastAPI 项目里，我们大部分服务是异步的。

所以 LangGraph 也要会写 async node。

比如节点里要调用：

```text
LLM API
数据库
Redis
HTTP 工具
RAG 检索
```

这些都可能是异步操作。

所以后面项目里会大量用：

```text
ainvoke
astream
```

---

## 三十一、27｜示例十一：Async Graph
打开：

```text
app/langgraph_core/demo_11_async_graph.py
```

写入：

```python
import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AsyncState(TypedDict):
    user_question: str
    answer: str


async def async_answer_node(state: AsyncState) -> dict:
    await asyncio.sleep(0.1)

    return {
        "answer": f"异步节点已经处理完成：{state['user_question']}"
    }


def build_graph():
    graph = StateGraph(AsyncState)

    graph.add_node("async_answer", async_answer_node)

    graph.add_edge(START, "async_answer")
    graph.add_edge("async_answer", END)

    return graph.compile()


async def main():
    app = build_graph()

    result = await app.ainvoke({
        "user_question": "LangGraph 支持异步节点吗？",
        "answer": "",
    })

    print(result)

    print("=" * 80)
    print("astream updates:")

    async for chunk in app.astream(
        {
            "user_question": "再测试一下异步 stream。",
            "answer": "",
        },
        stream_mode="updates",
    ):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```text
scripts/test_lg30_11_async_graph.py
```

写入：

```python
import asyncio

from app.langgraph_core.demo_11_async_graph import main


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 【重点内容】
这个例子说明 LangGraph 可以直接支持 async node。

以后我们接入 FastAPI 的时候，GraphService 里就会用：

```python
await graph.ainvoke(...)
```

如果要做流式接口，就会用：

```python
async for chunk in graph.astream(...):
    ...
```

这和前面第 16 章 Streaming、以及第 26 章 Agent Streaming 能接起来。

---

## 三十二、28｜概念十四：Graph 里的循环
Graph 可以有循环。

例如：

```text
model_node
 ↓
tools_node
 ↓
model_node
 ↓
END
```

==这就是 Agent 工具调用循环的形态。==

但循环必须有退出条件。

LangGraph 文档说明，创建循环时通常用 conditional edge 路由到 `END` 作为终止条件；也可以通过 config 设置 `recursion_limit` 限制图执行步数，避免无限循环。

---

### 【重点内容】
Agent 之所以适合用图，是因为它经常有循环。

比如：

```text
模型判断要不要调用工具
如果要调用工具 -> tools_node
工具执行完 -> 回到 model_node
如果不需要工具 -> END
```

这就是 ReAct Agent 的基本图结构。

但一定要注意，循环要有退出条件。

否则 Agent 可能一直转圈。

---

## 三十三、29｜概念十五：Graph 可视化
LangGraph 编译后的图可以通过：

```python
app.get_graph().draw_mermaid()
```

查看 Mermaid 图结构。

有些环境也可以生成 PNG：

```python
app.get_graph().draw_mermaid_png()
```

---

### 【重点内容】
Graph 可视化对教学和调试非常有用。

你可以把流程展示成：

```text
START --> classify_intent --> extract_order_id
extract_order_id --> ask_order_id
extract_order_id --> query_order
query_order --> generate_answer
generate_answer --> END
```

后面做企业级 Agent 平台时，图可视化会变成产品能力。

也就是用户可以在前端看到节点和连线。

---

## 三十四、30｜电商客服核心图：综合示例

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

打开：

```text
app/langgraph_core/demo_12_ecommerce_core_graph.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class EcommerceCoreState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    order_status: str | None
    policy_type: str | None
    policy_answer: str | None
    final_answer: str
    logs: Annotated[list[str], operator.add]


def classify_intent_node(state: EcommerceCoreState) -> dict:
    question = state["user_question"]

    if "退款" in question or "退货" in question:
        intent = "refund"
    elif "订单" in question or "物流" in question:
        intent = "order"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：识别意图为 {intent}"],
    }


def route_by_intent(
    state: EcommerceCoreState,
) -> Literal["general", "need_order"]:
    if state["intent"] == "general":
        return "general"

    return "need_order"


def extract_order_id_node(state: EcommerceCoreState) -> dict:
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


def route_after_extract_order_id(
    state: EcommerceCoreState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: EcommerceCoreState) -> dict:
    return {
        "final_answer": "请您提供订单号，我才能继续查询订单状态和售后规则。",
        "logs": ["ask_order_id：缺少订单号，追问用户。"],
    }


def query_order_node(state: EcommerceCoreState) -> dict:
    order_id = state["order_id"]

    if order_id == "10001":
        order_status = "shipped"
        status_text = "已发货"
    elif order_id == "10002":
        order_status = "paid"
        status_text = "已付款，待发货"
    else:
        order_status = "not_found"
        status_text = "未查询到订单"

    return {
        "order_status": order_status,
        "logs": [f"query_order：订单状态为 {status_text}"],
    }


def route_after_query_order(
    state: EcommerceCoreState,
) -> Literal["retrieve_policy", "generate_order_answer"]:
    if state["intent"] == "refund":
        return "retrieve_policy"

    return "generate_order_answer"


def decide_policy_type_node(state: EcommerceCoreState) -> dict:
    order_status = state["order_status"]

    if order_status == "paid":
        policy_type = "refund_before_shipping"
    elif order_status == "shipped":
        policy_type = "refund_after_shipping"
    else:
        policy_type = "unknown"

    return {
        "policy_type": policy_type,
        "logs": [f"decide_policy_type：规则类型为 {policy_type}"],
    }


def retrieve_policy_node(state: EcommerceCoreState) -> dict:
    policy_type = state["policy_type"]

    if policy_type == "refund_before_shipping":
        policy_answer = "根据售后规则，订单未发货时，用户可以申请取消订单并退款。"
    elif policy_type == "refund_after_shipping":
        policy_answer = "根据售后规则，订单已发货后，需要收到商品后再发起退货退款申请。"
    else:
        policy_answer = "当前状态无法从规则中确认，建议转人工客服。"

    return {
        "policy_answer": policy_answer,
        "logs": ["retrieve_policy：完成售后规则查询。"],
    }


def generate_general_answer_node(state: EcommerceCoreState) -> dict:
    return {
        "final_answer": "这是普通问题，后续可以接入普通 ChatModel 生成回答。",
        "logs": ["generate_general_answer：普通回答完成。"],
    }


def generate_order_answer_node(state: EcommerceCoreState) -> dict:
    order_status = state["order_status"]

    status_map = {
        "paid": "已付款，待发货",
        "shipped": "已发货",
        "not_found": "未查询到订单",
    }

    return {
        "final_answer": f"您的订单当前状态是：{status_map.get(order_status, '未知')}。",
        "logs": ["generate_order_answer：订单回答完成。"],
    }


def generate_refund_answer_node(state: EcommerceCoreState) -> dict:
    order_status = state["order_status"]

    status_map = {
        "paid": "已付款，待发货",
        "shipped": "已发货",
        "not_found": "未查询到订单",
    }

    return {
        "final_answer": (
            f"您的订单当前状态是：{status_map.get(order_status, '未知')}。"
            f"{state.get('policy_answer')}"
        ),
        "logs": ["generate_refund_answer：退款回答完成。"],
    }


def build_graph():
    graph = StateGraph(EcommerceCoreState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("decide_policy_type", decide_policy_type_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("generate_general_answer", generate_general_answer_node)
    graph.add_node("generate_order_answer", generate_order_answer_node)
    graph.add_node("generate_refund_answer", generate_refund_answer_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "generate_general_answer",
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
            "retrieve_policy": "decide_policy_type",
            "generate_order_answer": "generate_order_answer",
        },
    )

    graph.add_edge("decide_policy_type", "retrieve_policy")
    graph.add_edge("retrieve_policy", "generate_refund_answer")

    graph.add_edge("ask_order_id", END)
    graph.add_edge("generate_general_answer", END)
    graph.add_edge("generate_order_answer", END)
    graph.add_edge("generate_refund_answer", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "你好，介绍一下 LangGraph。",
        "帮我查一下订单 10001。",
        "我的订单 10002 还没发货，可以退款吗？",
        "我要退款，但是忘记订单号了。",
    ]

    for question in questions:
        print("question:", question)
        print("=" * 80)

        result = app.invoke({
            "user_question": question,
            "intent": "",
            "order_id": None,
            "order_status": None,
            "policy_type": None,
            "policy_answer": None,
            "final_answer": "",
            "logs": [],
        })

        print("final_answer:", result["final_answer"])
        print("logs:")
        for log in result["logs"]:
            print("-", log)

        print("=" * 120)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg30_12_ecommerce_core_graph.py
```

写入：

```python
from app.langgraph_core.demo_12_ecommerce_core_graph import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这是本章综合示例。

虽然现在还没有接真实模型、真实工具和真实 RAG，但图结构已经很接近后面的项目二。

它包含：

```text
意图识别
订单号提取
缺订单号追问
订单查询
规则类型判断
规则查询
最终回答生成
执行日志累加
```

==这就是 LangGraph 的价值。==

每一步都可以单独测试。

每个节点都能看输入和输出。

每条边都能看清楚怎么走。

后面第 38 章项目二，我们会把这些 mock 节点替换成真实能力：

```text
Structured Output
query_order Tool
RAG Retriever
ChatModel
Checkpoint
Human-in-the-loop
```

---

## 三十五、31｜LangGraph 核心概念关系图

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

```text
StateGraph
  ↓
定义 State Schema
  ↓
add_node 添加 Node
  ↓
add_edge / add_conditional_edges 添加 Edge
  ↓
compile 编译成可执行 Graph
  ↓
invoke / ainvoke 执行
  ↓
stream / astream 观察过程
  ↓
checkpointer 保存状态
  ↓
thread_id 区分会话
```

---

## 三十六、32｜LangGraph 和第 19 章项目一的关系
第 19 章项目一现在是：

```text
FastAPI Router
 ↓
ChatService
 ↓
普通 Chat / Tool Calling / Agent / RAG
```

引入 LangGraph 后可以变成：

```text
FastAPI Router
 ↓
ChatService
 ↓
GraphService
 ↓
CompiledStateGraph
 ↓
Node:
  classify_intent
  extract_order_id
  query_order
  retrieve_policy
  generate_answer
```

---

### 【重点内容】
LangGraph 不替代 FastAPI。

也不替代 ChatService。

它是在 Service 后面新增一个复杂流程编排层。

也就是说：

```text
Router 负责接口
Service 负责业务入口
Graph 负责 Agent 流程
Node 负责单个步骤
Tool / RAG / Model 负责具体能力
```

==这就是企业项目里比较清晰的分层方式。==

---

## 三十七、33｜LangGraph 常见错误一：没有 compile 就 invoke

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
graph = StateGraph(State)
graph.invoke(...)
```

正确：

```python
app = graph.compile()
app.invoke(...)
```

---

### 【重点内容】
StateGraph 是构建器，不是可执行图。

一定要 compile。

---

## 三十八、34｜常见错误二：Node 返回完整 State
不推荐：

```python
def node(state):
    state["answer"] = "xxx"
    return state
```

推荐：

```python
def node(state):
    return {
        "answer": "xxx"
    }
```

---

### 【重点内容】
节点最好返回它更新的字段。

不要直接修改原 State 后完整返回。

这样更清晰，也更符合 LangGraph 的状态更新模型。

---

## 三十九、35｜常见错误三：list 字段忘记 Reducer

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
class State(TypedDict):
    logs: list[str]
```

多个节点返回 logs 时，可能覆盖。

推荐：

```python
import operator
from typing import Annotated

class State(TypedDict):
    logs: Annotated[list[str], operator.add]
```

---

## 四十、36｜常见错误四：messages 不用 add_messages
不推荐：

```python
class State(TypedDict):
    messages: list[AnyMessage]
```

推荐：

```python
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

---

## 四十一、37｜常见错误五：所有逻辑都塞进一个 Node

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
一个 node 里完成：
意图识别、订单号提取、查订单、查规则、生成回答
```

正确：

```text
一个节点只做一件事。
```

---

## 四十二、38｜常见错误六：条件路由和普通边混用
==不推荐从同一个节点同时写：==

```python
graph.add_edge("classify_intent", "some_node")
graph.add_conditional_edges("classify_intent", route_func)
```

因为这样可能让流程变得难以理解。

官方 Graph API 文档也提醒，对同一个节点最好选择一种路由机制：静态流程用 normal edge，动态流程用 conditional edges 或 Command，避免从同一个节点混用静态和动态路由。

---

## 四十三、39｜常见错误七：thread_id 设计随意
不推荐：

```text
thread_id = "1"
```

推荐：

```text
thread_id = user_id + conversation_id
```

例如：

```python
thread_id = f"{user_id}:{conversation_id}"
```

---

### 【重点内容】
thread_id 是 checkpoint 的关键。

如果多个用户共用一个 thread_id，状态就会串。

如果每次都用新 thread_id，就没有记忆。

所以它要和业务会话绑定。

---

## 四十四、40｜常见错误八：把业务上下文都塞进 State

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

State 适合放流程状态：

```text
intent
order_id
order_info
policy_answer
final_answer
messages
```

Config 更适合放运行上下文：

```text
user_id
tenant_id
trace_id
request_id
role
permissions
```

---

## 四十五、41｜面试回答：LangGraph 核心概念
### 回答话术一：基础版
```text
LangGraph 的核心可以概括成 State、Node、Edge。

State 是整个 Agent 执行过程中的共享状态，比如用户问题、意图、订单号、工具结果、最终回答。

Node 是处理步骤，本质上是 Python 函数，读取 State 后返回部分状态更新。

Edge 是节点之间的连接，决定执行顺序。固定流程用 add_edge，动态分支用 add_conditional_edges。

最后通过 StateGraph 定义图，compile 成可执行图，再用 invoke、stream、ainvoke、astream 执行。
```

---

### 回答话术二：项目版
```text
在电商客服 Agent 里，我会用 LangGraph 把流程拆成多个节点：

classify_intent 负责识别意图；
extract_order_id 负责提取订单号；
query_order 负责查询订单；
retrieve_policy 负责检索售后规则；
generate_answer 负责生成最终回复。

这些节点共享一个 EcommerceState。流程分支通过 conditional edge 控制，比如缺少订单号就走 ask_order_id，退款问题就走 retrieve_policy，普通订单查询就直接生成订单状态回答。

这样比让一个 Agent 自由发挥更可控，也更适合企业级流程。
```

---

### 回答话术三：工程版
```text
工程上 LangGraph 的价值在于可控、可观测、可恢复。

可控是因为流程被拆成节点和边；
可观测是因为每个节点的输入输出都可以记录和 stream；
可恢复是因为 checkpointer 可以保存 thread 的 state，配合 thread_id 支持多轮对话、中断恢复和 human-in-the-loop。

所以我一般会把 LangChain 作为模型、Prompt、Tool、RAG 的组件层，把 LangGraph 作为复杂 Agent 的流程编排层。
```

---

## 四十六、42｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| StateGraph | 第 29 章图编排概念 |
| State | 第 19 章 ChatService 中的上下文 |
| Node | Service 中单个处理步骤 |
| Edge | 业务流程顺序 |
| Conditional Edge | 第 24 章意图识别后的路由 |
| Reducer | 执行日志、消息累加 |
| add_messages | 第 22 章 Message |
| Command | 状态更新 + 路由 |
| Checkpointer | 会话记忆、中断恢复 |
| thread_id | conversation_id / session_id |
| RunnableConfig | 用户、租户、trace 上下文 |
| stream_mode | 第 16 章 Streaming 升级 |
| Async Graph | FastAPI 异步服务 |
| 电商客服核心图 | 第 38 章项目二基础 |


---

## 四十七、43｜本章完整复习
这一章我们完成了：

```text
1. 理解 LangGraph 最小心智模型
2. 创建 langgraph_core 目录
3. 理解 StateGraph
4. 写出第一个最小 StateGraph
5. 理解 State
6. 理解 State 局部更新
7. 理解 Node
8. 理解 Edge
9. 写出顺序图
10. 理解 START 和 END
11. 理解 Conditional Edges
12. 写出条件路由图
13. 理解 Reducer
14. 使用 operator.add 累加 logs
15. 理解 add_messages
16. 写出 messages 状态图
17. 理解 Command
18. 使用 Command 同时更新状态和路由
19. 理解 compile
20. 理解 invoke / ainvoke
21. 理解 stream / astream
22. 对比 stream_mode=updates 和 values
23. 理解 Checkpointer
24. 使用 InMemorySaver 保存会话状态
25. 理解 thread_id
26. 理解 RunnableConfig
27. 在节点里读取 user_id / tenant_id / trace_id
28. 写出异步 Graph
29. 理解循环和 recursion_limit
30. 理解 Graph 可视化
31. 写出电商客服核心图
32. 理解 LangGraph 和项目一的关系
33. 总结常见错误
34. 准备面试回答话术
```

---

## 四十八、44｜课后任务一：跑通最小 Graph
要求：

```text
1. 运行 scripts/test_lg30_01_minimal_graph.py
2. 找到 HelloState
3. 找到 greeting_node
4. 找到 START 和 END
5. 说明 result 为什么包含 greeting 字段
```

---

## 四十九、45｜课后任务二：理解 State 局部更新
要求：

```text
1. 运行 scripts/test_lg30_02_state_update.py
2. 看 fill_role_node 返回了什么
3. 看 generate_intro_node 读取到了什么
4. 说明节点为什么不需要返回完整 State
```

---

## 五十、46｜课后任务三：跑通 Conditional Edges
要求：

```text
1. 运行 scripts/test_lg30_04_conditional_edges.py
2. 输入普通问题、订单问题、退款问题
3. 观察 route_by_intent 返回值
4. 说明 add_conditional_edges 的作用
```

---

## 五十一、47｜课后任务四：测试 Reducer
要求：

```text
1. 运行 scripts/test_lg30_05_reducer.py
2. 查看 logs 是否保留了所有节点日志
3. 去掉 Annotated[list[str], operator.add]
4. 再运行一次，观察结果差异
```

---

## 五十二、48｜课后任务五：测试 messages 状态
要求：

```text
1. 运行 scripts/test_lg30_06_messages_state.py
2. 查看 HumanMessage 和 AIMessage 是否都存在
3. 说明 add_messages 的作用
4. 思考为什么 Chat Agent 不能简单使用普通 list
```

---

## 五十三、49｜课后任务六：测试 Command
要求：

```text
1. 运行 scripts/test_lg30_07_command.py
2. 输入“你好”
3. 输入“我的订单可以退款吗？”
4. 查看 intent 和 answer 的变化
5. 说明 Command 和 conditional edge 的区别
```

---

## 五十四、50｜课后任务七：测试 stream
要求：

```text
1. 运行 scripts/test_lg30_08_stream_updates.py
2. 对比 updates 和 values
3. 说明 updates 更适合展示节点进度
4. 说明 values 更适合调试完整 State
```

---

## 五十五、51｜课后任务八：测试 Checkpointer
要求：

```text
1. 运行 scripts/test_lg30_09_checkpointer.py
2. 两次 invoke 使用同一个 thread_id
3. 查看第二次结果里是否保留第一次 messages
4. 修改 thread_id，再观察结果变化
```

---

## 五十六、52｜课后任务九：测试 RunnableConfig
要求：

```text
1. 运行 scripts/test_lg30_10_runnable_config.py
2. 在 config.configurable 里传 user_id
3. 在节点里读取 user_id
4. 思考哪些字段应该放 State，哪些字段应该放 config
```

---

## 五十七、53｜课后任务十：跑通电商客服核心图

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

要求：

```text
1. 运行 scripts/test_lg30_12_ecommerce_core_graph.py
2. 输入“我的订单 10002 还没发货，可以退款吗？”
3. 查看 logs 经过了哪些节点
4. 查看 final_answer
5. 画出这条请求的节点执行路径
```

---

## 五十八、54｜本章总结
### 【重点内容】
好了，到这里，第 30 章我们就讲完了。

这一章是 LangGraph 阶段非常重要的一章。

==我们系统讲了 LangGraph 的核心概念：==

```text
StateGraph：图构建器
State：共享状态
Node：处理步骤
Edge：节点连线
START：图入口
END：图结束
Reducer：状态合并规则
add_messages：消息累加 reducer
Command：状态更新和路由合并
Checkpointer：状态持久化
thread_id：会话维度
RunnableConfig：运行上下文
stream_mode：观察执行过程
```

大家一定要记住：

```text
LangGraph 的本质是：
把复杂 Agent 流程拆成状态图。
```

每个节点只做一件事。

每条边表达执行顺序。

每个分支显式可控。

每一步都可以观察、保存、恢复。

这就是它相比自由 Agent 的价值。

---

---

> [!success] 一句话带走
> ==State → Node → Edge → Reducer，四个词就是 LangGraph 的全部地基。==

> [!quote] 关于本文档
> 由原始讲义 `第 30 章｜LangGraph 核心概念.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
