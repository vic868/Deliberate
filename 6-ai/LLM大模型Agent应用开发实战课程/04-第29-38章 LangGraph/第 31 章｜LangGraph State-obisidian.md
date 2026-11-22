---
title: "第 31 章｜LangGraph State"
chapter: "31"
source: "第 31 章｜LangGraph State.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langgraph
  - state
  - typeddict
---

# 第 31 章｜LangGraph State

> [!abstract] 本章重点
>
> - ==State 是整张图共享的一份数据== — 节点之间不互相传参，都读写同一个 State。
> - ==TypedDict 轻，Pydantic 能校验== — 要运行时校验就选 Pydantic State。
> - ==MessagesState 自带 add_messages== — 消息列表自动追加，而不是被覆盖。
> - ==自定义 Reducer 控制合并逻辑== — 比如去重、截断、按租户隔离。
> - ==State 不是 Request / Response== — 它跨多步、可持久化，接口对象只活一轮。

> [!note] 大白话
>
> - **State**：一张图里所有节点共用、边走边改的「记事本」。

> [!info] 导航与来源
> - 原始讲义：[[第 31 章｜LangGraph State|打开原始讲义]]
> - [[第 30 章｜LangGraph 核心概念|上一章｜第 30 章]]
> - [[第 32 章｜LangGraph Node 与 Edge|下一章｜第 32 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#State]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜State 一句话解释]]
- [[#七、03｜State 和普通变量的区别]]
- [[#八、04｜State 和 Request / Response 的区别]]
- [[#九、05｜创建 langgraph_state 目录]]
- [[#十、06｜方式一：TypedDict State]]
- [[#十一、07｜示例一：TypedDict State]]
- [[#十二、08｜方式二：Pydantic State]]
- [[#十三、09｜示例二：Pydantic State]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

上一章我们讲了：

```text
第 30 章｜LangGraph 核心概念
```

重点讲了：

```text
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
```

这一章开始专门深入：

## State
也就是：

```text
LangGraph 图运行过程中的共享状态。
```

为什么要单独拿一章讲 State？

因为 LangGraph 项目做得好不好，很大程度取决于 State 设计得好不好。

如果 State 设计混乱，后面节点、边、条件路由、持久化、人工确认都会变乱。

如果 State 设计清晰，后面的 Agent 流程就会非常好维护。

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. State 在 LangGraph 中到底是什么
2. State 和普通变量有什么区别
3. State 和 Request / Response 有什么区别
4. TypedDict State 怎么写
5. Pydantic State 怎么写
6. MessagesState 怎么用
7. add_messages 为什么重要
8. Reducer 如何影响 State 更新
9. Input Schema 是什么
10. Output Schema 是什么
11. Private State 是什么
12. State 默认值怎么处理
13. State 字段应该怎么命名
14. 哪些数据应该放 State
15. 哪些数据不应该放 State
16. State 和 RunnableConfig 的区别
17. State 和 Checkpoint 的关系
18. State 和数据库的关系
19. State 和 Redis 的关系
20. 电商客服 Agent 的 State 如何设计
21. Agent 执行日志 State 如何设计
22. 多轮对话 State 如何设计
23. Human-in-the-loop State 如何设计
24. Multi-Agent State 如何设计
25. 面试中如何讲 LangGraph State
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
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
```

LangGraph 的 `StateGraph` 会基于 State schema 创建图；节点通常接收当前 State，并返回需要更新的字段，而不是完整覆盖整个状态。

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langgraph_state/
│   │   ├── __init__.py
│   │   ├── demo_01_typed_dict_state.py
│   │   ├── demo_02_pydantic_state.py
│   │   ├── demo_03_messages_state.py
│   │   ├── demo_04_state_reducer.py
│   │   ├── demo_05_input_output_schema.py
│   │   ├── demo_06_private_state.py
│   │   ├── demo_07_state_and_config.py
│   │   ├── demo_08_state_and_checkpoint.py
│   │   ├── demo_09_ecommerce_state.py
│   │   ├── demo_10_human_confirm_state.py
│   │   ├── demo_11_multi_agent_state.py
│   │   └── schemas.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg31_01_typed_dict_state.py
│   ├── test_lg31_02_pydantic_state.py
│   ├── test_lg31_03_messages_state.py
│   ├── test_lg31_04_state_reducer.py
│   ├── test_lg31_05_input_output_schema.py
│   ├── test_lg31_06_private_state.py
│   ├── test_lg31_07_state_and_config.py
│   ├── test_lg31_08_state_and_checkpoint.py
│   ├── test_lg31_09_ecommerce_state.py
│   ├── test_lg31_10_human_confirm_state.py
│   └── test_lg31_11_multi_agent_state.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 31 章。

这一章我们专门讲 LangGraph State。

上一章我们已经写了几个 StateGraph。

大家应该已经看到，每个图都会先定义一个 State。

比如：

```python
class EcommerceCoreState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    order_status: str | None
    final_answer: str
```

这个 State 就是整个图运行过程中的共享上下文。

你可以把它理解成：

```text
一次 Agent 任务的上下文对象。
```

在普通代码里，我们可能会写一堆局部变量：

```python
intent = None
order_id = None
order_info = None
policy_answer = None
final_answer = ""
```

但是在 LangGraph 里，这些都应该进入 State。

每个节点负责读取 State，然后返回一部分更新。

==这就是 LangGraph 编排的基础。==

---

## 六、02｜State 一句话解释
### 【实操】
```text
State
=
Graph 运行过程中的共享上下文
```

更口语一点：

```text
State 就是 Agent 做任务时随身携带的工作台。
```

里面放：

```text
用户问题
历史消息
意图识别结果
订单号
工具结果
知识库结果
人工确认状态
最终回答
执行日志
```

---

### 【重点内容】
大家可以把 State 理解成 Agent 的“任务上下文”。

比如电商客服 Agent 接到问题：

```text
我的订单 10002 还没发货，可以退款吗？
```

它执行过程中会产生很多中间信息：

```text
识别到 intent=refund
提取到 order_id=10002
查询订单得到 status=paid
检索规则得到 policy_answer
最后生成 final_answer
```

这些信息都应该放在 State 里。

这样每个节点都能看到当前执行到哪一步。

---

## 七、03｜State 和普通变量的区别
| 对比项 | 普通变量 | LangGraph State |
| --- | --- | --- |
| 作用范围 | 当前函数内部 | 整个图共享 |
| 是否跨节点 | 不跨节点 | 跨节点 |
| 是否可被 checkpoint 保存 | 需要自己处理 | 可以被 checkpointer 保存 |
| 是否利于中断恢复 | 弱 | 强 |
| 是否利于调试 | 一般 | 每一步状态可观察 |
| 是否适合复杂 Agent | 不适合 | 适合 |


---

### 【重点内容】
普通变量只在当前函数里有效。

但是 LangGraph 的 State 是整个图共享的。

节点 A 写入：

```python
{"intent": "refund"}
```

节点 B 可以读到：

```python
state["intent"]
```

节点 C 再继续更新：

```python
{"final_answer": "..."}
```

这就是跨节点状态传递。

更重要的是，State 可以被 Checkpointer 保存。

==所以后面中断恢复、人工确认、多轮对话，都依赖 State。==

---

## 八、04｜State 和 Request / Response 的区别
### 【实操】
```text
Request：
外部传进来的请求参数

State：
图执行中的完整上下文

Response：
最终返回给前端的数据
```

---

### 【重点内容】
很多同学会混淆 Request、State、Response。

比如 FastAPI 接口进来一个：

```python
ChatRequest
```

里面可能只有：

```text
question
session_id
model
```

但 Agent 执行过程中会产生：

```text
intent
order_id
tool_calls
sources
need_human_confirm
final_answer
```

这些不是 Request 原本就有的，而是图运行过程中慢慢生成的。

最终返回前端的是 Response。

所以三者关系是：

```text
Request
 ↓
初始化 State
 ↓
Graph 执行更新 State
 ↓
从 State 组装 Response
```

---

## 九、05｜创建 langgraph_state 目录
执行：

```bash
mkdir -p app/langgraph_state

touch app/langgraph_state/__init__.py
touch app/langgraph_state/schemas.py
touch app/langgraph_state/demo_01_typed_dict_state.py
touch app/langgraph_state/demo_02_pydantic_state.py
touch app/langgraph_state/demo_03_messages_state.py
touch app/langgraph_state/demo_04_state_reducer.py
touch app/langgraph_state/demo_05_input_output_schema.py
touch app/langgraph_state/demo_06_private_state.py
touch app/langgraph_state/demo_07_state_and_config.py
touch app/langgraph_state/demo_08_state_and_checkpoint.py
touch app/langgraph_state/demo_09_ecommerce_state.py
touch app/langgraph_state/demo_10_human_confirm_state.py
touch app/langgraph_state/demo_11_multi_agent_state.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_state

New-Item app\langgraph_state\__init__.py
New-Item app\langgraph_state\schemas.py
New-Item app\langgraph_state\demo_01_typed_dict_state.py
New-Item app\langgraph_state\demo_02_pydantic_state.py
New-Item app\langgraph_state\demo_03_messages_state.py
New-Item app\langgraph_state\demo_04_state_reducer.py
New-Item app\langgraph_state\demo_05_input_output_schema.py
New-Item app\langgraph_state\demo_06_private_state.py
New-Item app\langgraph_state\demo_07_state_and_config.py
New-Item app\langgraph_state\demo_08_state_and_checkpoint.py
New-Item app\langgraph_state\demo_09_ecommerce_state.py
New-Item app\langgraph_state\demo_10_human_confirm_state.py
New-Item app\langgraph_state\demo_11_multi_agent_state.py
```

---

## 十、06｜方式一：TypedDict State
==TypedDict 是课程里最推荐的入门方式。==

示例：

```python
from typing import TypedDict

class ChatState(TypedDict):
    user_question: str
    answer: str
```

优点：

```text
1. 写法简单
2. 类型提示清晰
3. 和 LangGraph 示例一致
4. 适合大多数 Agent 流程
```

---

### 【重点内容】
TypedDict 是我们这套课里最常用的 State 写法。

它不负责运行时校验。

但它能给 Python 类型提示。

比如你写：

```python
state["user_question"]
```

编辑器能知道这是字符串。

对于大多数 LangGraph 项目，TypedDict 已经够用了。

LangGraph 官方示例也大量使用 `TypedDict` 定义 State。

---

## 十一、07｜示例一：TypedDict State
打开：

```text
app/langgraph_state/demo_01_typed_dict_state.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class QAState(TypedDict):
    user_question: str
    answer: str


def answer_node(state: QAState) -> dict:
    question = state["user_question"]

    return {
        "answer": f"你问的是：{question}。这是 TypedDict State 示例。"
    }


def build_graph():
    graph = StateGraph(QAState)

    graph.add_node("answer", answer_node)

    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "TypedDict State 有什么用？",
        "answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_01_typed_dict_state.py
```

写入：

```python
from app.langgraph_state.demo_01_typed_dict_state import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg31_01_typed_dict_state.py
```

---

### 【重点内容】
这个例子很简单。

State 里有两个字段：

```text
user_question
answer
```

节点读取 user_question。

然后返回：

```python
{"answer": "..."}
```

最终 State 里 answer 被更新。

==这就是 TypedDict State 的基本用法。==

---

## 十二、08｜方式二：Pydantic State
Pydantic State 示例：

```python
from pydantic import BaseModel, Field

class QAStateModel(BaseModel):
    user_question: str = Field(..., min_length=1)
    answer: str = ""
```

优点：

```text
1. 可以做运行时校验
2. 可以设置默认值
3. 字段描述更清晰
4. 适合边界输入校验严格的场景
```

缺点：

```text
1. 写法比 TypedDict 重
2. 性能开销更高
3. Reducer 写法不如 TypedDict 直观
```

---

### 【重点内容】
Pydantic State 适合对输入要求比较严格的场景。

比如你希望 user_question 不能为空。

或者某些字段必须符合枚举。

那可以用 Pydantic。

但课程大多数章节还是用 TypedDict。

因为它更轻、更直观。

---

## 十三、09｜示例二：Pydantic State
打开：

```text
app/langgraph_state/demo_02_pydantic_state.py
```

写入：

```python
from pydantic import BaseModel, Field

from langgraph.graph import END, START, StateGraph


class PydanticQAState(BaseModel):
    user_question: str = Field(..., min_length=1, description="用户问题")
    answer: str = Field(default="", description="最终回答")


def answer_node(state: PydanticQAState) -> dict:
    return {
        "answer": f"你问的是：{state.user_question}。这是 Pydantic State 示例。"
    }


def build_graph():
    graph = StateGraph(PydanticQAState)

    graph.add_node("answer", answer_node)

    graph.add_edge(START, "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "Pydantic State 适合什么场景？",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_02_pydantic_state.py
```

写入：

```python
from app.langgraph_state.demo_02_pydantic_state import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg31_02_pydantic_state.py
```

---

### 【重点内容】
这个例子里，State 是 Pydantic Model。

==所以在节点里读取字段时，用：==

```python
state.user_question
```

不是：

```python
state["user_question"]
```

这点和 TypedDict 不一样。

大家根据项目习惯选择即可。

---

## 十四、10｜TypedDict State 和 Pydantic State 怎么选
| 场景 | 推荐 |
| --- | --- |
| 教学和快速开发 | TypedDict |
| 大多数 Agent 流程 | TypedDict |
| 需要复杂运行时校验 | Pydantic |
| 需要字段默认值和描述 | Pydantic |
| 需要 reducer 明确控制 | TypedDict 更直观 |
| 对性能敏感 | TypedDict |
| API 边界输入 | Pydantic Request / Response |
| Graph 内部流转 | TypedDict |


---

### 【重点内容】
我的建议是：

```text
FastAPI 的 Request / Response 用 Pydantic。
LangGraph 内部 State 优先用 TypedDict。
```

这样比较舒服。

因为 API 边界需要校验。

图内部更关注状态流转和 reducer。

当然，如果团队喜欢 Pydantic State，也可以用。

---

## 十五、11｜方式三：MessagesState
聊天型 Agent 最常见的 State 是：

```text
messages
```

LangGraph 提供了 `MessagesState`。

==它本质上就是一个包含 messages 字段的 State。==

`MessagesState` 的参考文档显示，它的核心字段是 `messages: Annotated[list[AnyMessage], add_messages]`，也就是用 `add_messages` 来合并消息列表。

---

### 【重点内容】
如果你的图就是一个聊天 Agent，最简单可以直接用 MessagesState。

比如：

```python
from langgraph.graph import MessagesState
```

然后节点里读取：

```python
state["messages"]
```

返回：

```python
{"messages": [AIMessage(content="...")]}
```

LangGraph 会自动把新消息追加进去。

---

## 十六、12｜示例三：MessagesState
打开：

```text
app/langgraph_state/demo_03_messages_state.py
```

写入：

```python
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph


def assistant_node(state: MessagesState) -> dict:
    last_message = state["messages"][-1]

    return {
        "messages": [
            AIMessage(
                content=f"我收到你的消息了：{last_message.content}"
            )
        ]
    }


def build_graph():
    graph = StateGraph(MessagesState)

    graph.add_node("assistant", assistant_node)

    graph.add_edge(START, "assistant")
    graph.add_edge("assistant", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "messages": [
            HumanMessage(content="MessagesState 有什么用？")
        ]
    })

    for message in result["messages"]:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_03_messages_state.py
```

写入：

```python
from app.langgraph_state.demo_03_messages_state import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
MessagesState 很适合最小聊天 Agent。

但是企业项目里，我们通常还需要更多字段。

比如：

```text
user_question
intent
order_id
sources
final_answer
```

这时候就可以自己定义 State，并手动加 messages 字段。

---

## 十七、13｜自定义 messages 字段
示例：

```python
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class CustomChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: str
    final_answer: str
```

---

### 【重点内容】
==这就是企业项目里更常见的写法。==

我们既保留 messages，又增加业务字段。

比如电商客服 Agent：

```text
messages：多轮对话
intent：用户意图
order_id：订单号
order_info：订单信息
policy_answer：知识库规则
final_answer：最终回答
```

这样比单纯 MessagesState 更灵活。

---

## 十八、14｜Reducer 再深入
上一章我们讲过：

```python
logs: Annotated[list[str], operator.add]
```

这表示：

```text
多个节点返回 logs 时，进行追加。
```

Reducer 的作用是：

```text
告诉 LangGraph：某个字段收到新值时，应该怎么和旧值合并。
```

默认行为通常可以理解为覆盖。

如果想追加、去重、合并 dict，就需要 reducer。

LangGraph 文档强调，Reducer 是理解节点更新如何应用到 State 的关键；对于 TypedDict State，可以用 `Annotated` 给字段绑定 reducer。

---

## 十九、15｜示例四：自定义 Reducer
打开：

```text
app/langgraph_state/demo_04_state_reducer.py
```

写入：

```python
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


def merge_unique_list(
    old: list[str],
    new: list[str],
) -> list[str]:
    result = list(old)

    for item in new:
        if item not in result:
            result.append(item)

    return result


class SourceState(TypedDict):
    question: str
    sources: Annotated[list[str], merge_unique_list]
    answer: str


def retrieve_employee_doc_node(state: SourceState) -> dict:
    return {
        "sources": ["employee_handbook"]
    }


def retrieve_policy_doc_node(state: SourceState) -> dict:
    return {
        "sources": ["ecommerce_after_sales", "employee_handbook"]
    }


def answer_node(state: SourceState) -> dict:
    return {
        "answer": f"最终引用来源：{', '.join(state['sources'])}"
    }


def build_graph():
    graph = StateGraph(SourceState)

    graph.add_node("retrieve_employee_doc", retrieve_employee_doc_node)
    graph.add_node("retrieve_policy_doc", retrieve_policy_doc_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "retrieve_employee_doc")
    graph.add_edge("retrieve_employee_doc", "retrieve_policy_doc")
    graph.add_edge("retrieve_policy_doc", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "question": "员工售后规则是什么？",
        "sources": [],
        "answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_04_state_reducer.py
```

写入：

```python
from app.langgraph_state.demo_04_state_reducer import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子自定义了一个 reducer：

```python
merge_unique_list
```

它的作用是合并 sources，并且去重。

第一个节点返回：

```text
employee_handbook
```

第二个节点返回：

```text
ecommerce_after_sales
employee_handbook
```

最终 sources 里不会重复出现 employee_handbook。

这类 reducer 在 RAG 引用来源里很实用。

---

## 二十、16｜Input Schema 和 Output Schema
默认情况下，图的输入、内部 State、输出 schema 可以是同一个。

但企业项目里，我们经常希望：

```text
输入只需要 question

内部 State 有很多中间字段

输出只返回 answer、sources、metadata
```

也就是：

```text
Input Schema
 ↓
Overall State
 ↓
Output Schema
```

LangGraph `StateGraph` 参考文档显示，它支持 `state_schema`、`input_schema`、`output_schema` 等 schema 配置，用来区分图内部状态、输入结构和输出结构。

---

### 【重点内容】
这个设计很重要。

比如电商客服图内部有：

```text
intent
order_id
order_info
policy_answer
logs
```

==这些不一定都要暴露给外部输入。==

外部输入可能只有：

```text
question
```

最终输出可能只有：

```text
answer
sources
```

所以 Input Schema 和 Output Schema 可以把边界控制得更清晰。

---

## 二十一、17｜示例五：Input / Output Schema
打开：

```text
app/langgraph_state/demo_05_input_output_schema.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class InputState(TypedDict):
    question: str


class OverallState(TypedDict):
    question: str
    intent: str
    answer: str
    debug_info: str


class OutputState(TypedDict):
    answer: str


def classify_node(state: OverallState) -> dict:
    question = state["question"]

    if "退款" in question:
        intent = "refund"
    else:
        intent = "general"

    return {
        "intent": intent,
        "debug_info": f"识别意图为 {intent}",
    }


def answer_node(state: OverallState) -> dict:
    return {
        "answer": f"当前意图是 {state['intent']}，问题是：{state['question']}"
    }


def build_graph():
    graph = StateGraph(
        OverallState,
        input_schema=InputState,
        output_schema=OutputState,
    )

    graph.add_node("classify", classify_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "question": "我的订单可以退款吗？"
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_05_input_output_schema.py
```

写入：

```python
from app.langgraph_state.demo_05_input_output_schema import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子里有三个 schema。

InputState 只有：

```text
question
```

OverallState 有：

```text
question
intent
answer
debug_info
```

OutputState 只有：

```text
answer
```

==所以最终 result 只会暴露 answer。==

内部 debug_info 不会返回给外部。

这对 API 设计很有用。

---

## 二十二、18｜Private State 是什么
Private State 可以理解成：

```text
图内部节点之间传递，但不想暴露给外部输入和输出的数据。
```

例如：

```text
debug_info
raw_model_response
raw_tool_result
retrieved_docs
risk_score
internal_logs
```

---

### 【重点内容】
Private State 不是某个神秘的新类型。

它更多是一种设计方式。

也就是：

```text
内部 OverallState 里有字段；
但 Input Schema 不要求用户传；
Output Schema 也不把它返回给用户。
```

这样它就只在图内部流转。

企业项目里非常常见。

比如 retrieved_docs 可以在内部用于生成回答。

但最终给前端的可能只是 sources 和 answer。

---

## 二十三、19｜示例六：Private State
打开：

```text
app/langgraph_state/demo_06_private_state.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class InputState(TypedDict):
    question: str


class OverallState(TypedDict):
    question: str
    internal_query: str
    raw_docs: list[str]
    answer: str


class OutputState(TypedDict):
    answer: str


def rewrite_query_node(state: OverallState) -> dict:
    return {
        "internal_query": f"知识库检索：{state['question']}"
    }


def retrieve_docs_node(state: OverallState) -> dict:
    return {
        "raw_docs": [
            "订单未发货时，用户可以申请取消订单并退款。",
            "订单已发货后，需要收到商品后再申请退货退款。",
        ]
    }


def answer_node(state: OverallState) -> dict:
    docs_text = "\n".join(state["raw_docs"])

    return {
        "answer": (
            f"根据内部检索到的规则：\n{docs_text}\n\n"
            f"针对你的问题：{state['question']}，未发货订单通常可以申请取消并退款。"
        )
    }


def build_graph():
    graph = StateGraph(
        OverallState,
        input_schema=InputState,
        output_schema=OutputState,
    )

    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("retrieve_docs", retrieve_docs_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "rewrite_query")
    graph.add_edge("rewrite_query", "retrieve_docs")
    graph.add_edge("retrieve_docs", "answer")
    graph.add_edge("answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "question": "订单未发货可以退款吗？"
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_06_private_state.py
```

写入：

```python
from app.langgraph_state.demo_06_private_state import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子里，外部只传 question。

内部有：

```text
internal_query
raw_docs
```

但最终只返回 answer。

==这就是 Private State 的常见设计。==

不要把所有中间状态都暴露给前端。

前端只需要它该看的内容。

---

## 二十四、20｜State 和 RunnableConfig 的区别
上一章我们讲过 RunnableConfig。

这里再明确一下：

| 类型 | 放什么 |
| --- | --- |
| State | 业务流程状态 |
| RunnableConfig | 运行上下文 |
| Request | 用户请求参数 |
| Response | 最终返回结构 |


State 适合放：

```text
intent
order_id
order_info
policy_answer
final_answer
messages
```

Config 适合放：

```text
thread_id
user_id
tenant_id
trace_id
permissions
```

---

### 【重点内容】
判断一个字段放 State 还是 config，可以看它是不是流程的一部分。

比如 order_id 是流程状态。

因为后面节点要根据它查订单。

所以放 State。

user_id 是运行上下文。

==很多节点可能需要用它做权限校验，但它不一定是 Agent 推理流程的一部分。==

所以可以放 config。

---

## 二十五、21｜示例七：State 和 Config 配合
打开：

```text
app/langgraph_state/demo_07_state_and_config.py
```

写入：

```python
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph


class OrderState(TypedDict):
    user_question: str
    order_id: str | None
    answer: str


def extract_order_id_node(state: OrderState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        return {"order_id": "10001"}

    return {"order_id": None}


def query_order_node(
    state: OrderState,
    config: RunnableConfig,
) -> dict:
    user_id = config.get("configurable", {}).get("user_id", "unknown")

    if not state["order_id"]:
        return {
            "answer": "请提供订单号。"
        }

    return {
        "answer": (
            f"用户 {user_id} 正在查询订单 {state['order_id']}。"
            "这里应该继续做订单归属校验。"
        )
    }


def build_graph():
    graph = StateGraph(OrderState)

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
            "answer": "",
        },
        config={
            "configurable": {
                "thread_id": "thread_order_001",
                "user_id": "u_10001",
                "tenant_id": "tenant_001",
            }
        },
    )

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_07_state_and_config.py
```

写入：

```python
from app.langgraph_state.demo_07_state_and_config import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子里：

```text
order_id 放 State
user_id 放 config
```

因为 order_id 是流程要处理的数据。

user_id 是当前运行上下文。

==后面真实查询订单时，一定要用 user_id 做订单归属校验。==

不能模型说查哪个订单就查哪个订单。

---

## 二十六、22｜State 和 Checkpoint 的关系
Checkpoint 保存的是某个 thread 的 State 快照。

也就是说：

```text
State 设计得越清楚，
Checkpoint 保存和恢复就越清楚。
```

如果 State 混乱，恢复也会混乱。

LangGraph Persistence 文档说明，checkpointer 会按 thread 保存 graph state 的 checkpoint；调用图时通过 config 传 `thread_id`，可以在同一个 thread 内保留状态。

---

### 【重点内容】
Checkpoint 保存什么？

保存 State。

所以 State 设计非常关键。

比如 Human-in-the-loop 场景：

```text
need_human_confirm=True
pending_action=refund_order
order_id=10002
risk_level=high
```

这些都要在 State 里。

否则暂停后恢复时，系统不知道当时停在哪里，为什么停，下一步要做什么。

---

## 二十七、23｜示例八：State + Checkpoint
打开：

```text
app/langgraph_state/demo_08_state_and_checkpoint.py
```

写入：

```python
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph


class UserProfileState(TypedDict):
    user_name: str | None
    favorite_topic: str | None
    answer: str


def remember_name_node(state: UserProfileState) -> dict:
    if state.get("user_name"):
        return {
            "answer": f"我记住你的名字了：{state['user_name']}"
        }

    return {
        "answer": "你还没有告诉我你的名字。"
    }


def remember_topic_node(state: UserProfileState) -> dict:
    if state.get("favorite_topic"):
        return {
            "answer": (
                f"我记住了，你关注的话题是：{state['favorite_topic']}。"
            )
        }

    return {}


def build_graph():
    graph = StateGraph(UserProfileState)

    graph.add_node("remember_name", remember_name_node)
    graph.add_node("remember_topic", remember_topic_node)

    graph.add_edge(START, "remember_name")
    graph.add_edge("remember_name", "remember_topic")
    graph.add_edge("remember_topic", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "state_checkpoint_demo"
        }
    }

    first_result = app.invoke(
        {
            "user_name": "大伟",
            "favorite_topic": None,
            "answer": "",
        },
        config=config,
    )

    print("first_result:")
    print(first_result)

    second_result = app.invoke(
        {
            "favorite_topic": "LangGraph State 设计",
        },
        config=config,
    )

    print("second_result:")
    print(second_result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_08_state_and_checkpoint.py
```

写入：

```python
from app.langgraph_state.demo_08_state_and_checkpoint import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子演示了 State 和 Checkpoint 的关系。

第一次调用传入 user_name。

第二次调用只传 favorite_topic。

因为使用了同一个 thread_id，图可以基于之前的 State 继续。

注意，这里用的是 InMemorySaver。

程序重启后状态会丢。

生产环境要用持久化 checkpointer。

---

## 二十八、24｜企业级 State 设计原则
### 原则一：字段要有明确业务含义
不推荐：

```python
data: dict
context: dict
result: dict
```

推荐：

```python
intent: str
order_id: str | None
order_info: dict | None
policy_answer: str | None
final_answer: str
```

---

### 原则二：不要把所有东西都塞进 State
State 不是垃圾桶。

不要把这些随便塞进去：

```text
完整用户画像
完整权限对象
完整数据库连接
完整 HTTP client
超大文档全文
完整日志大对象
```

---

### 原则三：State 要服务节点路由
好的 State 字段，应该能支撑路由。

比如：

```text
intent
order_id
need_human_confirm
risk_level
tool_success
is_answered
```

这些字段可以决定下一步走哪里。

---

### 原则四：中间字段和输出字段要分清楚
中间字段：

```text
raw_model_response
retrieved_docs
tool_result
debug_info
```

输出字段：

```text
final_answer
sources
metadata
```

---

### 原则五：大对象要谨慎
比如 retrieved_docs 可能很大。

如果直接放 State，Checkpoint 会变大。

建议只放必要字段：

```text
document_id
chunk_id
content_preview
score
```

完整文档可以放数据库或对象存储。

---

## 二十九、25｜电商客服 Agent State 设计
创建：

```text
app/langgraph_state/schemas.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


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


class EcommerceAgentState(TypedDict):
    # 输入和对话
    user_question: str
    messages: Annotated[list[AnyMessage], add_messages]

    # 意图和槽位
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
    tracking_no: str | None

    # 业务工具结果
    order_info: OrderInfo | None
    logistics_info: dict | None

    # RAG 结果
    policy_query: str | None
    policy_answer: str | None
    sources: Annotated[list[SourceInfo], operator.add]

    # 风险和人工确认
    risk_level: Literal["low", "medium", "high"]
    need_human_confirm: bool
    pending_action: str | None

    # 执行过程
    tool_calls: Annotated[list[ToolCallInfo], operator.add]
    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]

    # 输出
    final_answer: str
    is_finished: bool
```

---

### 【重点内容】
这是一个比较完整的电商客服 Agent State。

我把它分成几组。

第一组是输入和对话：

```text
user_question
messages
```

第二组是意图和槽位：

```text
intent
order_id
tracking_no
```

第三组是业务工具结果：

```text
order_info
logistics_info
```

第四组是 RAG 结果：

```text
policy_query
policy_answer
sources
```

第五组是风险和人工确认：

```text
risk_level
need_human_confirm
pending_action
```

第六组是执行过程：

```text
tool_calls
logs
errors
```

最后是输出：

```text
final_answer
is_finished
```

==这就是一个企业 Agent State 的雏形。==

---

## 三十、26｜为什么 sources、tool_calls、logs 用 Reducer
在上面的 State 里：

```python
sources: Annotated[list[SourceInfo], operator.add]
tool_calls: Annotated[list[ToolCallInfo], operator.add]
logs: Annotated[list[str], operator.add]
errors: Annotated[list[str], operator.add]
```

原因是这些字段可能由多个节点追加。

比如：

```text
query_order_node 追加一次 tool_call
retrieve_policy_node 追加一次 source
generate_answer_node 追加一条 log
error_handler_node 追加一条 error
```

如果不用 reducer，后面的更新可能覆盖前面的数据。

---

## 三十一、27｜初始化 EcommerceAgentState
建议提供一个初始化函数：

```python
from langchain_core.messages import HumanMessage

from app.langgraph_state.schemas import EcommerceAgentState


def create_initial_ecommerce_state(
    user_question: str,
) -> EcommerceAgentState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "intent": "unknown",
        "order_id": None,
        "tracking_no": None,

        "order_info": None,
        "logistics_info": None,

        "policy_query": None,
        "policy_answer": None,
        "sources": [],

        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,

        "tool_calls": [],
        "logs": [],
        "errors": [],

        "final_answer": "",
        "is_finished": False,
    }
```

---

### 【重点内容】
State 最好有初始化函数。

不要在每个 Router 或 Service 里手写一遍默认值。

否则后面字段一多，很容易漏。

比如忘记初始化：

```text
sources
tool_calls
logs
errors
```

后面 reducer 或节点读取时就可能出错。

---

## 三十二、28｜示例九：电商客服 State 图
打开：

```text
app/langgraph_state/demo_09_ecommerce_state.py
```

写入：

```python
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.langgraph_state.schemas import EcommerceAgentState


def create_initial_ecommerce_state(
    user_question: str,
) -> EcommerceAgentState:
    return {
        "user_question": user_question,
        "messages": [HumanMessage(content=user_question)],

        "intent": "unknown",
        "order_id": None,
        "tracking_no": None,

        "order_info": None,
        "logistics_info": None,

        "policy_query": None,
        "policy_answer": None,
        "sources": [],

        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,

        "tool_calls": [],
        "logs": [],
        "errors": [],

        "final_answer": "",
        "is_finished": False,
    }


def classify_intent_node(state: EcommerceAgentState) -> dict:
    question = state["user_question"]

    if "退款" in question or "退货" in question:
        intent = "refund"
    elif "物流" in question:
        intent = "logistics"
    elif "订单" in question:
        intent = "query_order"
    elif "人工" in question:
        intent = "human_service"
    else:
        intent = "general"

    return {
        "intent": intent,
        "logs": [f"classify_intent：识别意图为 {intent}"],
    }


def extract_order_id_node(state: EcommerceAgentState) -> dict:
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


def query_order_node(state: EcommerceAgentState) -> dict:
    order_id = state["order_id"]

    if order_id == "10001":
        order_info = {
            "order_id": "10001",
            "status": "shipped",
            "status_text": "已发货",
            "tracking_company": "顺丰",
            "tracking_no": "SF10001",
            "latest_event": "包裹已到达成都高新区中转站。",
        }
    elif order_id == "10002":
        order_info = {
            "order_id": "10002",
            "status": "paid",
            "status_text": "已付款，待发货",
            "tracking_company": None,
            "tracking_no": None,
            "latest_event": None,
        }
    else:
        order_info = {
            "order_id": order_id or "",
            "status": "not_found",
            "status_text": "未查询到订单",
            "tracking_company": None,
            "tracking_no": None,
            "latest_event": None,
        }

    return {
        "order_info": order_info,
        "tool_calls": [
            {
                "name": "query_order",
                "args": {"order_id": order_id},
                "id": "mock_query_order",
                "success": True,
                "result_preview": order_info["status_text"],
            }
        ],
        "logs": [f"query_order：订单状态为 {order_info['status_text']}"],
    }


def retrieve_policy_node(state: EcommerceAgentState) -> dict:
    order_info = state.get("order_info")

    if order_info and order_info.get("status") == "paid":
        policy_answer = "订单未发货时，用户可以申请取消订单并退款。"
        policy_query = "订单未发货退款规则"
    elif order_info and order_info.get("status") == "shipped":
        policy_answer = "订单已发货后，需要用户收到商品后再发起退货退款申请。"
        policy_query = "订单已发货退货退款规则"
    else:
        policy_answer = "当前状态无法确认退款规则，建议转人工客服。"
        policy_query = "退款规则"

    return {
        "policy_query": policy_query,
        "policy_answer": policy_answer,
        "sources": [
            {
                "document_id": "ecommerce_after_sales",
                "chunk_id": "ecommerce_after_sales_chunk_0",
                "source": "data/knowledge_base/ecommerce_after_sales.md",
                "content_preview": policy_answer,
                "score": 0.9,
            }
        ],
        "logs": ["retrieve_policy：完成售后规则查询"],
    }


def generate_answer_node(state: EcommerceAgentState) -> dict:
    order_info = state.get("order_info")
    policy_answer = state.get("policy_answer")

    if state["intent"] == "refund":
        answer = (
            f"您的订单当前状态是：{order_info['status_text']}。"
            f"{policy_answer}"
        )
    elif state["intent"] == "query_order":
        answer = f"您的订单当前状态是：{order_info['status_text']}。"
    else:
        answer = "这是普通问题，可以走普通 Chat。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["generate_answer：最终回答生成完成"],
    }


def build_graph():
    graph = StateGraph(EcommerceAgentState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "extract_order_id")
    graph.add_edge("extract_order_id", "query_order")
    graph.add_edge("query_order", "retrieve_policy")
    graph.add_edge("retrieve_policy", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_ecommerce_state(
            "我的订单 10002 还没发货，可以退款吗？"
        )
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("sources:")
    for source in result["sources"]:
        print(source)

    print("=" * 80)
    print("tool_calls:")
    for tool_call in result["tool_calls"]:
        print(tool_call)

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)

    print("=" * 80)
    print("messages:")
    for message in result["messages"]:
        print(message.type, ":", message.content)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_09_ecommerce_state.py
```

写入：

```python
from app.langgraph_state.demo_09_ecommerce_state import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
==这个例子重点不是图的路由。==

而是 State 设计。

你会看到一次请求执行完以后，State 里有：

```text
intent
order_id
order_info
policy_answer
sources
tool_calls
logs
final_answer
messages
```

这就是企业 Agent 需要保存和观察的内容。

---

## 三十三、29｜Human-in-the-loop State 设计
如果后面要做人工确认，State 里至少需要：

```python
need_human_confirm: bool
pending_action: str | None
risk_level: Literal["low", "medium", "high"]
human_confirm_status: Literal["pending", "approved", "rejected", "none"]
human_confirm_payload: dict | None
```

---

### 【重点内容】
Human-in-the-loop 本质上也是状态驱动。

不是简单地弹一个确认框。

你要知道：

```text
为什么需要确认
确认的动作是什么
确认的数据是什么
当前状态是 pending 还是 approved
用户拒绝后怎么处理
```

这些都要进入 State。

后面第 35 章我们会真正实现 interrupt。

这一章先把 State 设计好。

---

## 三十四、30｜示例十：Human Confirm State
打开：

```text
app/langgraph_state/demo_10_human_confirm_state.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RefundConfirmState(TypedDict):
    user_question: str
    order_id: str | None
    refund_amount: float
    risk_level: Literal["low", "medium", "high"]
    need_human_confirm: bool
    human_confirm_status: Literal["none", "pending", "approved", "rejected"]
    pending_action: str | None
    human_confirm_payload: dict | None
    final_answer: str


def assess_risk_node(state: RefundConfirmState) -> dict:
    refund_amount = state["refund_amount"]

    if refund_amount >= 500:
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "human_confirm_status": "pending",
            "pending_action": "refund_order",
            "human_confirm_payload": {
                "order_id": state["order_id"],
                "refund_amount": refund_amount,
                "reason": "大额退款需要人工确认",
            },
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "human_confirm_status": "none",
    }


def generate_answer_node(state: RefundConfirmState) -> dict:
    if state["need_human_confirm"]:
        return {
            "final_answer": (
                "该退款金额较高，需要人工客服确认后才能继续处理。"
            )
        }

    return {
        "final_answer": "该退款金额较低，可以进入自动退款流程。"
    }


def build_graph():
    graph = StateGraph(RefundConfirmState)

    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "assess_risk")
    graph.add_edge("assess_risk", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "user_question": "我要申请退款。",
        "order_id": "10002",
        "refund_amount": 899.0,
        "risk_level": "low",
        "need_human_confirm": False,
        "human_confirm_status": "none",
        "pending_action": None,
        "human_confirm_payload": None,
        "final_answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_10_human_confirm_state.py
```

写入：

```python
from app.langgraph_state.demo_10_human_confirm_state import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子里，如果 refund_amount 大于 500，就把：

```text
need_human_confirm=True
human_confirm_status=pending
pending_action=refund_order
human_confirm_payload=...
```

写入 State。

后面第 35 章我们会在这里接入 interrupt。

现在先让学员理解：人工确认不是口头说说，而是 State 里要有明确字段。

---

## 三十五、31｜Multi-Agent State 设计
Multi-Agent 场景里，State 通常需要记录：

```text
当前任务
任务拆解结果
每个 Agent 的输出
当前执行到哪个 Agent
最终汇总结果
review 结果
```

示例字段：

```python
task: str
plan: list[str]
current_agent: str
research_result: str | None
analysis_result: str | None
review_result: str | None
final_report: str
```

---

### 【重点内容】
后面 Multi-Agent 阶段会用到。

比如一个 AI 数据分析 Multi-Agent：

```text
Planner Agent
SQL Agent
Chart Agent
Report Agent
Reviewer Agent
```

这些 Agent 之间需要共享任务状态。

不是各干各的。

==所以 Multi-Agent 也离不开 State。==

---

## 三十六、32｜示例十一：Multi-Agent State
打开：

```text
app/langgraph_state/demo_11_multi_agent_state.py
```

写入：

```python
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


class MultiAgentState(TypedDict):
    task: str
    plan: Annotated[list[str], operator.add]
    current_agent: str
    research_result: str | None
    analysis_result: str | None
    review_result: str | None
    final_report: str
    logs: Annotated[list[str], operator.add]


def planner_node(state: MultiAgentState) -> dict:
    return {
        "current_agent": "planner",
        "plan": [
            "检索行业资料",
            "分析核心趋势",
            "生成总结报告",
            "检查报告质量",
        ],
        "logs": ["planner：完成任务拆解"],
    }


def researcher_node(state: MultiAgentState) -> dict:
    return {
        "current_agent": "researcher",
        "research_result": "检索到 3 条与 AI Agent 平台相关的行业趋势。",
        "logs": ["researcher：完成资料检索"],
    }


def analyst_node(state: MultiAgentState) -> dict:
    return {
        "current_agent": "analyst",
        "analysis_result": "核心趋势是企业从单点 Chatbot 转向多 Agent 工作流平台。",
        "logs": ["analyst：完成趋势分析"],
    }


def reviewer_node(state: MultiAgentState) -> dict:
    return {
        "current_agent": "reviewer",
        "review_result": "报告结构完整，可以输出。",
        "logs": ["reviewer：完成质量检查"],
    }


def report_node(state: MultiAgentState) -> dict:
    return {
        "current_agent": "reporter",
        "final_report": (
            f"任务：{state['task']}\n"
            f"研究结果：{state['research_result']}\n"
            f"分析结论：{state['analysis_result']}\n"
            f"审核意见：{state['review_result']}"
        ),
        "logs": ["reporter：完成最终报告"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("reporter", report_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "reviewer")
    graph.add_edge("reviewer", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke({
        "task": "分析 AI Agent 平台趋势",
        "plan": [],
        "current_agent": "",
        "research_result": None,
        "analysis_result": None,
        "review_result": None,
        "final_report": "",
        "logs": [],
    })

    print("final_report:")
    print(result["final_report"])

    print("=" * 80)
    print("plan:")
    for item in result["plan"]:
        print("-", item)

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg31_11_multi_agent_state.py
```

写入：

```python
from app.langgraph_state.demo_11_multi_agent_state import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子只是 Multi-Agent 的 State 雏形。

后面第 37 章会真正做 Multi-Agent。

现在先理解：

```text
多个 Agent 之间也需要共享 State。
```

每个 Agent 的输出都应该沉淀到 State。

最后 reporter 再综合所有结果输出 final_report。

---

## 三十七、33｜State 默认值怎么处理
TypedDict 本身不提供默认值。

所以建议：

```text
1. 写 create_initial_state 函数
2. 不要在 Router 里手写默认值
3. list 字段初始化为空列表
4. optional 字段初始化为 None
5. 状态枚举初始化为 unknown / none
```

示例：

```python
def create_initial_state(question: str) -> EcommerceAgentState:
    return {
        "user_question": question,
        "messages": [HumanMessage(content=question)],
        "intent": "unknown",
        "order_id": None,
        "sources": [],
        "logs": [],
        "final_answer": "",
        "is_finished": False,
        ...
    }
```

---

### 【重点内容】
==State 默认值一定要统一。==

否则不同入口初始化出来的 State 不一样。

比如 API 入口和测试脚本入口字段不一致，后面节点就会出现各种奇怪问题。

---

## 三十八、34｜哪些数据应该放 State
适合放 State 的数据：

```text
1. 当前任务输入
2. 多轮对话 messages
3. 意图识别结果
4. 槽位提取结果
5. 工具调用结果
6. RAG 检索摘要
7. 引用来源 sources
8. 人工确认状态
9. 风险等级
10. 最终回答
11. 节点执行日志
12. 错误信息
```

---

## 三十九、35｜哪些数据不应该放 State
不建议放 State：

```text
1. 数据库连接对象
2. Redis client
3. HTTP client
4. 完整用户权限大对象
5. 超大文档全文
6. 大量原始日志
7. 文件二进制内容
8. 不可序列化对象
9. 密钥和敏感凭证
```

---

### 【重点内容】
State 会被节点传递，也可能会被 checkpoint 保存。

所以不要放不可序列化对象。

也不要放敏感凭证。

比如 API Key 绝对不要放 State。

数据库连接也不要放 State。

这些应该通过依赖注入、Service 或 config 管理。

---

## 四十、36｜State 和数据库的关系
State 不是数据库。

State 是当前图执行上下文。

数据库是长期持久化。

例如：

```text
State：
当前订单号、当前工具结果、当前 final_answer

数据库：
会话记录、消息记录、订单数据、文档数据、审计日志
```

---

### 【重点内容】
State 不要承担数据库职责。

比如完整订单数据应该存在业务数据库。

State 里可以放当前流程需要的订单摘要。

比如：

```python
order_info = {
    "order_id": "10002",
    "status": "paid",
    "status_text": "已付款，待发货"
}
```

不是把订单所有字段都塞进来。

---

## 四十一、37｜State 和 Redis 的关系
Redis 适合：

```text
1. 缓存最近消息
2. 缓存工具结果
3. 限流计数
4. 临时任务状态
5. 分布式锁
```

State 适合：

```text
当前图执行状态
```

二者可以配合：

```text
Graph State 保存当前流程上下文；
Redis 缓存高频工具结果或限流状态。
```

---

## 四十二、38｜State 和 Checkpoint 的关系
Checkpoint 保存 State。

但是 Checkpoint 不是业务数据库的替代品。

建议：

```text
Checkpoint：
用于恢复图执行状态

业务数据库：
用于保存业务数据和审计记录
```

比如退款审批：

```text
Checkpoint 保存流程停在 human_confirm。
数据库保存真实退款申请单。
```

---

## 四十三、39｜State 字段命名建议
推荐命名：

```text
user_question
intent
order_id
order_info
policy_answer
tool_calls
sources
need_human_confirm
final_answer
is_finished
```

不推荐：

```text
data
result
obj
tmp
ctx
info
response
```

---

### 【重点内容】
State 字段要看名字就知道是什么意思。

不要写：

```python
data: dict
```

后面维护的人不知道里面是什么。

企业项目最怕这种状态黑盒。

---

## 四十四、40｜State 设计 checklist
设计 State 时可以问自己：

```text
1. 这个字段是不是流程必需？
2. 哪个节点写入它？
3. 哪个节点读取它？
4. 它会不会参与条件路由？
5. 它是否需要被 checkpoint 保存？
6. 它是否会很大？
7. 它是否包含敏感信息？
8. 它是否需要 reducer？
9. 它最终是否要返回给前端？
10. 它是否应该放到 config 而不是 State？
```

---

## 四十五、41｜面试回答：LangGraph State 怎么理解
### 回答话术一：基础版
```text
LangGraph 里的 State 可以理解成图执行过程中的共享上下文。

每个 Node 都会读取当前 State，然后返回部分字段更新。LangGraph 会把这些更新合并到 State 里，再传给后续节点。

比如一个电商客服 Agent 的 State 里可能包含 user_question、intent、order_id、order_info、policy_answer、sources、tool_calls、final_answer 等字段。

State 的好处是让复杂 Agent 的中间结果不再散落在函数局部变量里，而是统一管理、可观察、可 checkpoint 保存，也方便中断恢复和人工确认。
```

---

### 回答话术二：项目版
```text
在项目里我会把 State 按业务流程设计。

比如电商客服 Agent：

用户输入放 user_question；
多轮消息放 messages；
意图识别结果放 intent；
订单号放 order_id；
订单查询结果放 order_info；
知识库检索结果放 policy_answer 和 sources；
工具调用过程放 tool_calls；
高风险动作放 need_human_confirm、risk_level、pending_action；
最终输出放 final_answer。

这样每个节点只负责更新自己关心的字段，比如 classify_intent_node 更新 intent，query_order_node 更新 order_info，retrieve_policy_node 更新 policy_answer，generate_answer_node 更新 final_answer。
```

---

### 回答话术三：工程版
```text
工程上设计 State 时，我会注意几个点：

第一，State 字段要有明确业务含义，不使用 data、context 这种大而全字段。

第二，list 类型字段要考虑 reducer，比如 logs、sources、tool_calls 这种字段通常需要追加，而不是覆盖。

第三，messages 要使用 add_messages reducer，避免多轮对话消息丢失。

第四，输入、内部状态和输出可以分开设计，也就是 input_schema、overall state、output_schema，这样可以把内部中间状态隐藏起来。

第五，State 不放不可序列化对象、不放数据库连接、不放密钥和超大文档全文，避免 checkpoint 和安全问题。
```

---

## 四十六、42｜常见错误一：State 设计成一个 data dict

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
class State(TypedDict):
    data: dict
```

问题：

```text
字段不清晰
类型提示失效
节点依赖不明确
条件路由不好写
后期难维护
```

推荐：

```python
class State(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    final_answer: str
```

---

## 四十七、43｜常见错误二：把 Request 直接当 State
错误：

```text
ChatRequest 进来后直接传给 Graph
```

问题：

```text
Request 只代表外部输入
State 需要包含图执行中的中间结果
```

正确：

```text
ChatRequest
 ↓
create_initial_state
 ↓
Graph State
```

---

## 四十八、44｜常见错误三：list 字段没有 reducer

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
tool_calls: list[dict]
logs: list[str]
sources: list[dict]
```

推荐：

```python
tool_calls: Annotated[list[dict], operator.add]
logs: Annotated[list[str], operator.add]
sources: Annotated[list[dict], operator.add]
```

---

## 四十九、45｜常见错误四：messages 不用 add_messages
错误：

```python
messages: list[AnyMessage]
```

推荐：

```python
messages: Annotated[list[AnyMessage], add_messages]
```

`add_messages` 是 LangGraph 为消息列表设计的 reducer，它会把节点返回的新消息合并进现有消息列表，并把消息反序列化成 LangChain Message 对象；这就是聊天型 Agent 推荐使用它的原因。

---

## 五十、46｜常见错误五：State 里放超大对象
错误：

```text
retrieved_docs 里放完整 PDF 内容
```

问题：

```text
State 变大
Checkpoint 变大
性能变差
隐私风险增加
```

推荐：

```text
只放文档 ID、chunk ID、preview、score
完整内容从数据库或向量库重新取
```

---

## 五十一、47｜常见错误六：State 和 Config 混用

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
把 user_id 放 State
把 order_id 放 config
```

更合理：

```text
user_id / tenant_id / trace_id 放 config
order_id / intent / tool_result 放 State
```

---

## 五十二、48｜常见错误七：State 没有初始化函数
错误：

```text
每个测试脚本和接口里手写默认 State
```

问题：

```text
字段容易漏
默认值不一致
后续维护困难
```

推荐：

```python
create_initial_ecommerce_state(user_question)
```

---

## 五十三、49｜常见错误八：把敏感信息放 State

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不建议放：

```text
API Key
完整手机号
完整身份证号
完整地址
支付流水号
内部密钥
```

原因：

```text
State 可能会被日志记录
State 可能会被 checkpoint 保存
State 可能会被调试界面展示
```

---

## 五十四、50｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| State | 第 30 章核心概念 |
| TypedDict State | 第 29 / 30 章图示例 |
| Pydantic State | 第 04 章 Pydantic |
| MessagesState | 第 22 章 Message |
| add_messages | 第 30 章 Reducer |
| Reducer | 第 30 章 logs 累加 |
| Input Schema | FastAPI Request |
| Output Schema | FastAPI Response |
| Private State | 图内部中间变量 |
| RunnableConfig | 第 30 章运行上下文 |
| Checkpoint | 第 30 章状态保存 |
| EcommerceAgentState | 第 38 章项目二基础 |
| Human Confirm State | 第 35 章 Human-in-the-loop |
| Multi-Agent State | 第 37 章 Multi-Agent |


---

## 五十五、51｜本章完整复习
这一章我们完成了：

```text
1. 理解 State 是图执行共享上下文
2. 理解 State 和普通变量的区别
3. 理解 State 和 Request / Response 的区别
4. 创建 langgraph_state 目录
5. 使用 TypedDict State
6. 使用 Pydantic State
7. 对比 TypedDict 和 Pydantic
8. 使用 MessagesState
9. 自定义 messages 字段
10. 深入理解 Reducer
11. 编写自定义 merge_unique_list reducer
12. 理解 Input Schema
13. 理解 Output Schema
14. 理解 Private State
15. 理解 State 和 RunnableConfig 的区别
16. 编写 State + Config 示例
17. 理解 State 和 Checkpoint 的关系
18. 编写 State + Checkpoint 示例
19. 总结企业级 State 设计原则
20. 设计 EcommerceAgentState
21. 理解 sources / tool_calls / logs 为什么要 reducer
22. 编写 create_initial_ecommerce_state
23. 编写电商客服 State 图
24. 设计 Human-in-the-loop State
25. 编写 Human Confirm State 示例
26. 设计 Multi-Agent State
27. 编写 Multi-Agent State 示例
28. 理解 State 默认值处理
29. 理解哪些数据应该放 State
30. 理解哪些数据不应该放 State
31. 理解 State 和数据库的关系
32. 理解 State 和 Redis 的关系
33. 理解 State 和 Checkpoint 的关系
34. 总结 State 字段命名建议
35. 总结 State 设计 checklist
36. 准备面试回答话术
37. 总结 State 常见错误
```

---

## 五十六、52｜课后任务一：跑通 TypedDict State
要求：

```text
1. 运行 scripts/test_lg31_01_typed_dict_state.py
2. 找到 QAState
3. 说明 user_question 和 answer 的作用
4. 说明 answer_node 返回了什么
```

---

## 五十七、53｜课后任务二：跑通 Pydantic State
要求：

```text
1. 运行 scripts/test_lg31_02_pydantic_state.py
2. 修改 user_question 为空字符串
3. 观察是否触发校验
4. 对比 TypedDict State 的区别
```

---

## 五十八、54｜课后任务三：跑通 MessagesState
要求：

```text
1. 运行 scripts/test_lg31_03_messages_state.py
2. 查看 HumanMessage 和 AIMessage 是否都保留
3. 说明 MessagesState 内部为什么需要 add_messages
```

---

## 五十九、55｜课后任务四：测试自定义 Reducer
要求：

```text
1. 运行 scripts/test_lg31_04_state_reducer.py
2. 查看 sources 是否去重
3. 把 merge_unique_list 改成普通 operator.add
4. 观察 sources 是否出现重复
```

---

## 六十、56｜课后任务五：测试 Input / Output Schema
要求：

```text
1. 运行 scripts/test_lg31_05_input_output_schema.py
2. 查看最终 result 是否只包含 answer
3. 说明 debug_info 为什么没有输出
4. 思考这在 API 设计里有什么用
```

---

## 六十一、57｜课后任务六：测试 Private State
要求：

```text
1. 运行 scripts/test_lg31_06_private_state.py
2. 查看 result 里是否只有 answer
3. 说明 internal_query 和 raw_docs 为什么属于内部状态
```

---

## 六十二、58｜课后任务七：测试 State 和 Config
要求：

```text
1. 运行 scripts/test_lg31_07_state_and_config.py
2. 查看 order_id 从哪里来
3. 查看 user_id 从哪里来
4. 说明 order_id 为什么放 State，user_id 为什么放 config
```

---

## 六十三、59｜课后任务八：测试 State + Checkpoint
要求：

```text
1. 运行 scripts/test_lg31_08_state_and_checkpoint.py
2. 两次 invoke 使用同一个 thread_id
3. 观察第二次是否继承第一次的 user_name
4. 修改 thread_id 再运行一次，对比结果
```

---

## 六十四、60｜课后任务九：跑通电商客服 State 图
要求：

```text
1. 运行 scripts/test_lg31_09_ecommerce_state.py
2. 输入“我的订单 10002 还没发货，可以退款吗？”
3. 查看 intent / order_id / order_info / policy_answer
4. 查看 sources / tool_calls / logs
5. 说明 EcommerceAgentState 中每一组字段的作用
```

---

## 六十五、61｜课后任务十：扩展 EcommerceAgentState
新增字段：

```python
user_id: str
tenant_id: str
conversation_id: str
trace_id: str
```

思考：

```text
这些字段应该放 State，还是放 config？
```

建议答案：

```text
如果它们只是运行上下文，更适合放 config。
如果后续节点路由或输出强依赖，也可以同步写入 State，但要避免重复和混乱。
```

---

## 六十六、62｜课后任务十一：设计 RAG State
要求设计一个企业知识库 RAG State：

```text
question
rewritten_query
retrieved_docs
sources
answer
is_answered
confidence
logs
errors
```

并说明：

```text
哪些字段需要 reducer？
哪些字段适合 private state？
哪些字段应该输出给前端？
```

---

## 六十七、63｜课后任务十二：设计 Human-in-the-loop State
要求：

```text
1. 基于 demo_10_human_confirm_state.py
2. 增加 approved_by
3. 增加 approved_at
4. 增加 reject_reason
5. 设计 approved / rejected 后分别走什么节点
```

---

## 六十八、64｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 31 章我们就讲完了。

这一章我们专门深入讲了 LangGraph State。

大家一定要记住一句话：

```text
State 是整个图执行过程中的共享上下文。
```

它不是普通变量。

也不是 Request。

也不是 Response。

它是 Agent 执行过程中不断被节点读取、更新、保存和恢复的上下文对象。

本章我们讲了几种 State 写法：

```text
TypedDict State
Pydantic State
MessagesState
自定义 messages State
Input Schema
Output Schema
Private State
```

==也讲了 State 设计的核心原则：==

```text
字段要有明确业务含义
不要用一个 data dict 装所有东西
list 字段要考虑 reducer
messages 要用 add_messages
不要放不可序列化对象
不要放敏感凭证
不要放超大文档全文
State 和 config 要分清楚
State 和数据库、Redis、Checkpoint 要分清楚
```

最后我们设计了一个比较完整的：

```text
EcommerceAgentState
```

它会成为后面第 38 章 LangGraph 电商客服 Agent 项目的基础。

---

---

> [!success] 一句话带走
> ==State 设计错了，后面每个节点都别扭；先定字段和合并规则。==

> [!quote] 关于本文档
> 由原始讲义 `第 31 章｜LangGraph State.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
