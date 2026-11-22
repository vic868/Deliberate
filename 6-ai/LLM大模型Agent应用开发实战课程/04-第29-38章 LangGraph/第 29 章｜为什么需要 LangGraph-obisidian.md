---
title: "第 29 章｜为什么需要 LangGraph"
chapter: "29"
source: "第 29 章｜为什么需要 LangGraph.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langgraph
  - 框架选型
---

# 第 29 章｜为什么需要 LangGraph

> [!abstract] 本章重点
>
> - ==LangChain Agent 的循环是黑盒== — 想插入人工确认、暂停恢复、精细控制步数就很难。
> - ==LangGraph 把流程显式画成图== — State、Node、Edge、条件路由都是看得见、可测试的代码。
> - ==带状态、会循环、可暂停的场景才需要它== — 一条直线流程用 LCEL 就够。
> - ==Checkpoint 让流程可恢复== — 中断后从断点继续，而不是重跑。
> - ==和工作流引擎的区别是「节点里是模型」== — 分支由模型输出决定，不是写死的条件。

> [!note] 大白话
>
> - **图 Graph**：把每一步画成节点、把走向画成边，流程一眼看得懂。

> [!info] 导航与来源
> - 原始讲义：[[第 29 章｜为什么需要 LangGraph|打开原始讲义]]
> - [[第 28 章｜LangChain Agent + RAG|上一章｜第 28 章]]
> - [[第 30 章｜LangGraph 核心概念|下一章｜第 30 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#LangGraph]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜先看 LangChain Agent 的优势]]
- [[#七、03｜但是 LangChain Agent 的问题也很明显]]
- [[#八、04｜不用 LangGraph 时，代码会变成什么样]]
- [[#九、05｜LangGraph 到底解决什么问题]]
- [[#十、06｜LangChain 和 LangGraph 的关系]]
- [[#十一、07｜核心概念一：State]]
- [[#十二、08｜核心概念二：Node]]
- [[#十三、09｜核心概念三：Edge]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面我们已经完成了 LangChain 阶段：

```text
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
第 25 章｜LangChain Tool
第 26 章｜LangChain Agent
第 27 章｜LangChain RAG
第 28 章｜LangChain Agent + RAG
```

到第 28 章，我们已经能做一个比较完整的电商客服 Agent：

```text
用户问题
 ↓
Agent
 ↓
调用订单工具
 ↓
调用知识库工具
 ↓
综合生成回答
```

比如用户问：

```text
我的订单 10002 还没发货，这种情况可以退款吗？
```

Agent 可以：

```text
1. 调用 query_order 查询订单状态
2. 调用 search_knowledge_base 查询退款规则
3. 综合订单状态和售后规则生成回答
```

这已经很像一个智能客服了。

但是，真实企业项目里，Agent 很快会遇到更复杂的问题。

比如：

```text
1. 必须先识别意图
2. 必须提取订单号
3. 必须查订单
4. 根据订单状态决定下一步
5. 如果未发货，查退款规则
6. 如果已发货，查退货规则
7. 如果金额较大，需要人工确认
8. 如果用户缺少信息，要追问
9. 如果用户补充信息，要从上次中断处继续
10. 整个过程要能保存、恢复、审计和追踪
```

这个时候，仅仅使用：

```python
create_agent(...)
```

就不够了。

我们需要更底层、更可控的 Agent 编排方式。

这就是：

## LangGraph
---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. 为什么 LangChain Agent 不够
2. 为什么复杂 Agent 需要显式状态
3. LangGraph 到底解决什么问题
4. LangGraph 和 LangChain 是什么关系
5. State 是什么
6. Node 是什么
7. Edge 是什么
8. Conditional Routing 是什么
9. Checkpoint 是什么
10. Human-in-the-loop 为什么需要图
11. Multi-Agent 为什么适合图编排
12. LangGraph 和工作流引擎有什么区别
13. LangGraph 和普通 if/else 有什么区别
14. LangGraph 在企业级 AI Agent 平台中的位置
15. 什么时候用 LangChain Agent
16. 什么时候用 LangGraph
17. 如何写第一个最小 StateGraph
18. 如何把第 28 章 Agent + RAG 思路迁移到 LangGraph
19. LangGraph 阶段的后续学习路线
20. 面试中怎么回答“为什么需要 LangGraph”
```

---

## 三、本章版本口径
本课程 LangGraph 阶段统一使用：

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
from langgraph.graph import StateGraph, START, END
```

LangGraph 官方 Graph API 文档说明，LangGraph 的节点通常是 Python 同步或异步函数，节点读取 graph state 并返回状态更新；`StateGraph` 则通过节点和边来描述状态流转。

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langgraph_intro/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── demo_problem_without_graph.py
│   │   ├── demo_first_state_graph.py
│   │   ├── demo_conditional_routing.py
│   │   ├── demo_graph_vs_agent.py
│   │   ├── demo_graph_for_ecommerce.py
│   │   └── notes.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg29_problem_without_graph.py
│   ├── test_lg29_first_state_graph.py
│   ├── test_lg29_conditional_routing.py
│   └── test_lg29_ecommerce_graph.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 29 章。

从这一章开始，我们正式进入 LangGraph 阶段。

==前面我们已经学完了 LangChain 的核心能力：==

```text
Model
Message
Prompt
Structured Output
Tool
Agent
RAG
Agent + RAG
```

第 28 章我们已经做到了 Agent + RAG。

也就是 Agent 既能查订单，也能查知识库。

那为什么还要学 LangGraph？

因为真实企业 Agent 不是简单地：

```text
用户问
 ↓
Agent 自己判断
 ↓
调用工具
 ↓
回答
```

真实企业 Agent 更多是：

```text
有固定流程
有复杂分支
有状态保存
有人工确认
有失败重试
有权限校验
有审计日志
有中断恢复
有多 Agent 协作
```

这些能力如果都靠一个 `create_agent` 让模型自由发挥，风险会比较高。

LangGraph 要解决的核心问题就是：

**把 Agent 从“模型自由决策”，升级成“可控的状态图编排”。**

---

## 六、02｜先看 LangChain Agent 的优势
LangChain Agent 很适合快速起步。

比如第 26 章我们写：

```python
agent = create_agent(
    model=model,
    tools=tools,
    system_prompt="你是一个电商客服 Agent。",
)
```

然后：

```python
result = await agent.ainvoke({
    "messages": [
        {
            "role": "user",
            "content": "帮我查一下订单 10001 到哪了？",
        }
    ]
})
```

它可以自动：

```text
1. 判断是否需要工具
2. 选择工具
3. 生成工具参数
4. 执行工具
5. 观察工具结果
6. 生成最终回答
```

---

### 【重点内容】
LangChain Agent 的好处很明显。

它上手快。

你给它模型、工具、Prompt，它就能跑起来。

适合：

```text
Demo
原型验证
简单客服
简单工具调用
低风险自动化
```

这也是为什么我们先学 LangChain Agent。

因为它能让学员快速看到 Agent 的效果。

---

## 七、03｜但是 LangChain Agent 的问题也很明显
LangChain Agent 的问题不是“不能用”。

而是：

```text
当业务流程复杂时，自由 Agent 不够可控。
```

比如下面这个客服流程：

```text
用户：我的订单 10002 还没发货，这种情况可以退款吗？

理想流程：
1. 提取订单号 10002
2. 查订单状态
3. 判断订单是否未发货
4. 如果未发货，查退款规则
5. 如果已发货，查退货规则
6. 生成最终回答
7. 如果金额较大，进入人工确认
```

如果直接交给 Agent，它可能：

```text
只查订单，不查规则
只查规则，不查订单
两个都没查，直接回答
先查了错误工具
工具结果没看清楚
该转人工没转人工
```

---

### 【重点内容】
这里一定要讲清楚。

Agent 不稳定，不代表 LangChain 不行。

而是 Agent 这种模式本来就有概率性。

模型会自己判断下一步。

但企业业务有时候需要确定流程。

比如退款流程，不是模型想怎么走就怎么走。

你必须明确：

```text
先查订单
再查规则
再判断风险
再决定是否人工确认
```

这种流程更适合 LangGraph。

---

## 八、04｜不用 LangGraph 时，代码会变成什么样
打开：

```text
app/langgraph_intro/demo_problem_without_graph.py
```

写入：

```python
def handle_customer_request_without_graph(user_question: str) -> str:
    """
    这是一个没有 LangGraph 的伪代码示例。

    问题：
    1. if/else 很快变复杂。
    2. 状态散落在局部变量里。
    3. 中断恢复很难。
    4. 人工确认很难插入。
    5. 每一步的输入输出不好追踪。
    """

    intent = None
    order_id = None
    order_info = None
    policy_answer = None
    need_human_confirm = False

    if "退款" in user_question:
        intent = "refund"
    elif "订单" in user_question or "物流" in user_question:
        intent = "query_order"
    else:
        intent = "general_chat"

    if intent == "general_chat":
        return "这是一个普通问题，可以走普通 Chat。"

    if intent in ["refund", "query_order"]:
        if "10001" in user_question:
            order_id = "10001"
        elif "10002" in user_question:
            order_id = "10002"
        else:
            return "请您提供订单号，我帮您继续处理。"

    if order_id == "10001":
        order_info = {
            "order_id": "10001",
            "status": "shipped",
            "status_text": "已发货",
        }
    elif order_id == "10002":
        order_info = {
            "order_id": "10002",
            "status": "paid",
            "status_text": "已付款，待发货",
        }
    else:
        return "没有查询到该订单，请检查订单号是否正确。"

    if intent == "refund":
        if order_info["status"] == "paid":
            policy_answer = "订单未发货时，可以申请取消订单并退款。"
        elif order_info["status"] == "shipped":
            policy_answer = "订单已发货后，需要收到商品后再发起退货退款申请。"
        else:
            policy_answer = "根据当前状态，建议转人工确认。"

    if need_human_confirm:
        return "该请求需要人工客服确认，我先帮您创建工单。"

    if intent == "refund":
        return (
            f"您的订单 {order_info['order_id']} 当前状态是：{order_info['status_text']}。"
            f"{policy_answer}"
        )

    return (
        f"您的订单 {order_info['order_id']} 当前状态是：{order_info['status_text']}。"
    )


def main():
    questions = [
        "我的订单 10002 还没发货，这种情况可以退款吗？",
        "帮我查一下订单 10001 到哪了？",
        "我要退款，但是忘记订单号了。",
    ]

    for question in questions:
        print("question:", question)
        print(handle_customer_request_without_graph(question))
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建测试脚本：

```text
scripts/test_lg29_problem_without_graph.py
```

写入：

```python
from app.langgraph_intro.demo_problem_without_graph import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg29_problem_without_graph.py
```

---

### 【重点内容】
这个例子故意写得很普通。

你看，现在只是一个退款和查订单流程，代码就已经开始有点乱了。

里面有：

```text
intent
order_id
order_info
policy_answer
need_human_confirm
```

这些状态都散落在函数局部变量里。

如果后面再加：

```text
物流异常
优惠券补偿
人工审批
用户补充订单号
失败重试
中断恢复
```

这个函数会越来越难维护。

==这就是为什么我们需要 LangGraph。==

---

## 九、05｜LangGraph 到底解决什么问题
### 【实操】
```text
LangGraph 解决的是：

复杂 Agent 的状态编排问题。
```

更具体一点：

```text
1. 状态统一管理
2. 步骤拆成节点
3. 节点之间用边连接
4. 条件分支显式表达
5. 每一步可以观察
6. 每一步可以保存
7. 失败后可以恢复
8. 高风险步骤可以中断等待人工确认
9. 多 Agent 可以协作
```

LangGraph 官方概览说明，它关注 Agent 编排中的底层能力，比如 durable execution、streaming、human-in-the-loop、memory 等，并且可以和 LangChain 组件一起使用，但不强制依赖 LangChain。

---

### 【重点内容】
LangGraph 不是为了替代 LangChain。

LangGraph 解决的是另一个层面的问题：

```text
LangChain 更像组件库和 Agent 快速入口。
LangGraph 更像复杂 Agent 的状态编排框架。
```

如果你只是：

```text
Prompt | Model | Parser
```

用 LangChain 就够了。

如果你只是简单工具调用，LangChain Agent 也够了。

但如果你要控制复杂流程，就需要 LangGraph。

---

## 十、06｜LangChain 和 LangGraph 的关系
### 【实操】
```text
LangChain
  ↓
Model / Prompt / Tool / Agent / RAG

LangGraph
  ↓
State / Node / Edge / Conditional Routing / Checkpoint / HITL
```

再看一层：

```text
LangChain Agent
  ↓
内部基于 LangGraph
```

LangGraph v1 发布说明提到，它被设计为和 LangChain v1 协同工作，LangChain 的 `create_agent` 构建在 LangGraph 之上；如果需要更细粒度控制，可以从高级 Agent 入口下钻到 LangGraph 的底层图控制。

---

### 【重点内容】
大家不要把 LangChain 和 LangGraph 看成竞争关系。

它们不是二选一。

更准确的关系是：

```text
LangChain 负责 LLM 组件。
LangGraph 负责 Agent 状态流转。
```

比如后面我们写 LangGraph 的 node 时，node 里面仍然会用：

```text
ChatOpenAI
ChatPromptTemplate
PydanticOutputParser
Tool
Retriever
```

这些还是 LangChain 的能力。

==所以 LangGraph 不是把前面的东西推倒。==

而是把前面的能力放进图里。

---

## 十一、07｜核心概念一：State

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
State
=
整个 Agent 执行过程中共享的数据
```

比如电商客服 State：

```python
class EcommerceState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    order_info: dict | None
    policy_answer: str | None
    need_human_confirm: bool
    final_answer: str
```

---

### 【重点内容】
State 是 LangGraph 的核心。

你可以把它理解成：

Agent 执行过程中的共享上下文。

不用 LangGraph 时，这些状态散落在函数变量里。

用了 LangGraph 后，这些状态统一放在 State 里。

每个节点读取 State，返回 State 的一部分更新。

比如：

```text
意图识别节点写入 intent
订单号提取节点写入 order_id
订单查询节点写入 order_info
知识库节点写入 policy_answer
最终回答节点写入 final_answer
```

这样流程就清楚很多。

---

## 十二、08｜核心概念二：Node

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Node
=
图里的一个处理步骤
=
一个 Python 函数
```

示例：

```python
def classify_intent_node(state: EcommerceState) -> dict:
    return {
        "intent": "refund"
    }
```

---

### 【重点内容】
Node 就是节点。

在 LangGraph 里，一个节点通常就是一个 Python 函数。

它接收 State，返回 State 更新。

比如：

```text
classify_intent_node：
负责识别意图

extract_order_id_node：
负责提取订单号

query_order_node：
负责查订单

retrieve_policy_node：
负责查规则

generate_answer_node：
负责生成回答
```

每个节点只做一件事。

这和我们前面 Service 分层思想是一样的。

---

## 十三、09｜核心概念三：Edge

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Edge
=
节点之间的连线
=
执行顺序
```

示例：

```python
graph.add_edge("classify_intent", "extract_order_id")
graph.add_edge("extract_order_id", "query_order")
graph.add_edge("query_order", "generate_answer")
```

---

### 【重点内容】
Edge 就是边。

它表示节点之间的执行顺序。

比如：

```text
先识别意图
再提取订单号
再查订单
再生成回答
```

如果没有 Edge，节点只是零散函数。

有了 Edge，流程才变成图。

---

## 十四、10｜核心概念四：Conditional Routing

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Conditional Routing
=
根据 State 决定下一步走哪条边
```

示例：

```text
intent=general_chat -> general_answer
intent=query_order -> query_order
intent=refund -> retrieve_policy
```

---

### 【重点内容】
Conditional Routing 是 LangGraph 非常重要的能力。

复杂 Agent 不是一条直线。

它有很多分支。

比如：

```text
如果是普通问题，走普通回答。
如果是订单问题，走订单查询。
如果是退款问题，先查订单，再查规则。
如果缺少订单号，走追问用户。
如果金额大，走人工确认。
```

这些分支用 LangGraph 可以显式写出来。

而不是藏在一堆 if/else 里。

LangGraph 的使用文档也展示了通过 conditional edge 决定循环继续还是停止的模式。

---

## 十五、11｜核心概念五：Checkpoint

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Checkpoint
=
图执行过程中的状态快照
```

它可以支持：

```text
1. 保存执行状态
2. 中断后恢复
3. 多轮对话记忆
4. Human-in-the-loop
5. 失败恢复
```

LangGraph checkpoint 参考文档说明，使用 checkpointer 时，图会在每个 superstep 保存 graph state 的 checkpoint，从而支持 human-in-the-loop、交互之间的 memory 等能力；checkpoint 本身是某个时间点 graph state 的快照。

---

### 【重点内容】
Checkpoint 是企业级 Agent 非常重要的能力。

比如用户发起退款申请。

流程走到：

```text
需要人工确认
```

这时候不能继续执行。

系统要暂停。

等人工审批通过后，再从原来的状态恢复。

如果没有 checkpoint，你就很难知道：

```text
当时用户问了什么
订单状态是什么
已经执行到哪一步
下一步应该做什么
```

LangGraph 的 checkpoint 就是为这种场景准备的。

---

## 十六、12｜核心概念六：Human-in-the-loop

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Human-in-the-loop
=
Agent 执行到高风险步骤时暂停
等待人类确认
再继续执行
```

比如：

```text
退款
发短信
删数据
改订单
执行 SQL
发邮件
```

LangGraph 的 `interrupt` 能在节点中暂停图执行，并把需要人工输入或确认的信息暴露给客户端；恢复执行时，客户端使用 `Command` 提供恢复值继续执行。

---

### 【重点内容】
==Human-in-the-loop 是企业 Agent 必须掌握的能力。==

模型不能自己决定退款。

正确流程应该是：

```text
Agent 判断需要退款
 ↓
暂停
 ↓
展示订单信息和退款建议
 ↓
人工或用户确认
 ↓
确认后继续执行
```

这类流程用普通 Agent 很难写稳。

用 LangGraph 会更合适。

---

## 十七、13｜核心概念七：Streaming

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

LangGraph 支持多种 stream mode，比如：

```text
values
updates
messages
custom
checkpoints
tasks
debug
```

LangGraph 协议参考文档列出了这些 stream mode：`values` 可以输出每一步后的完整 state，`updates` 可以输出节点更新，`messages` 可以输出节点或任务里的 LLM token 流，`checkpoints` 可以在 checkpoint 创建时发出事件。

---

### 【重点内容】
前面我们讲过普通 Chat Streaming。

也讲过 Agent Streaming。

LangGraph 的 Streaming 更强。

因为它可以流式输出：

```text
每个节点的状态变化
每个任务的开始和结束
LLM token
自定义进度
checkpoint 信息
```

这对前端展示 Agent 执行过程非常重要。

比如：

```text
正在识别意图
正在提取订单号
正在查询订单
正在检索售后规则
等待人工确认
正在生成最终回答
```

这些都可以通过图的执行过程展示出来。

---

## 十八、14｜核心概念八：Multi-Agent

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【重点内容】
Multi-Agent 就是多个 Agent 协作。

比如一个数据分析任务：

```text
Planner Agent：
拆解任务

SQL Agent：
查数据库

Chart Agent：
生成图表

Report Agent：
生成报告

Reviewer Agent：
检查结果
```

如果让一个 Agent 自由完成所有事，可能会乱。

用 LangGraph 可以把每个 Agent 变成一个节点。

然后通过边控制它们的协作流程。

==这就是后面 Multi-Agent 阶段的基础。==

---

## 十九、15｜LangGraph 和工作流引擎的区别
| 对比项 | 传统工作流 | LangGraph |
| --- | --- | --- |
| 节点行为 | 固定业务代码 | 可以包含 LLM / Tool / Agent |
| 路由逻辑 | 规则为主 | 规则 + 模型判断 |
| 状态 | 表单 / 流程变量 | Agent State |
| 中断恢复 | 支持 | 支持 Checkpoint / Interrupt |
| 流式输出 | 通常弱 | 支持多种 stream mode |
| 适合场景 | 审批流、业务流程 | LLM Agent 编排 |
| 是否面向 LLM | 不一定 | 是 |


---

### 【重点内容】
LangGraph 很像工作流引擎，但不是普通工作流引擎。

它特别适合 LLM 应用。

因为它的节点可以是：

```text
模型调用
Prompt 渲染
工具调用
RAG 检索
Agent 执行
人工确认
多 Agent 协作
```

所以它更适合 AI Agent 编排。

---

## 二十、16｜LangGraph 和普通 if/else 的区别
普通 if/else：

```text
逻辑散落
状态散落
难观察
难恢复
难中断
难复用
```

LangGraph：

```text
状态统一
节点清晰
边显式
分支可视
可 streaming
可 checkpoint
可 interrupt
可组合
```

---

### 【重点内容】
很多同学会说：

我不用 LangGraph，用 if/else 不也能写吗？

简单流程当然可以。

但复杂后会出问题。

比如你要实现：

```text
用户补充订单号后，从上次缺订单号的地方继续
```

用 if/else 就很麻烦。

因为你要自己保存状态、恢复状态、判断下一步。

LangGraph 把这些抽象成状态图，更适合复杂 Agent。

---

## 二十一、17｜什么时候用 LangChain Agent，什么时候用 LangGraph
### 推荐判断标准
| 场景 | 推荐 |
| --- | --- |
| 简单问答 | 普通 Chat |
| Prompt → Model → Parser | LangChain Chain |
| 简单工具调用 | Tool Calling |
| 快速 Agent 原型 | LangChain Agent |
| 固定多步骤业务流程 | LangGraph |
| 复杂条件分支 | LangGraph |
| 需要中断恢复 | LangGraph |
| 需要人工确认 | LangGraph |
| 需要状态持久化 | LangGraph |
| 多 Agent 协作 | LangGraph |
| 企业级 Agent 平台 | LangGraph |


---

### 【重点内容】
这个表很重要。

不是所有东西都用 LangGraph。

也不是所有东西都用 Agent。

正确选择是：

```text
简单问题简单做。
复杂流程再上图。
```

比如：

```text
什么是 LangChain？
普通 Chat

根据知识库回答年假制度？
RAG Chain

查订单 10001？
Tool Calling / Agent

退款审批流程？
LangGraph

多 Agent 数据分析？
LangGraph
```

---

## 二十二、18｜第一个最小 StateGraph
现在写一个最小 LangGraph。

打开：

```text
app/langgraph_intro/demo_first_state_graph.py
```

写入：

```python
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SimpleState(TypedDict):
    user_question: str
    answer: str


def answer_node(state: SimpleState) -> dict:
    question = state["user_question"]

    return {
        "answer": f"你问的是：{question}。这是 LangGraph 的第一个节点回答。"
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
        "user_question": "为什么需要 LangGraph？",
        "answer": "",
    })

    print(result)


if __name__ == "__main__":
    main()
```

创建测试脚本：

```text
scripts/test_lg29_first_state_graph.py
```

写入：

```python
from app.langgraph_intro.demo_first_state_graph import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg29_first_state_graph.py
```

---

### 【重点内容】
这是第一个最小 StateGraph。

大家先记住四步：

```text
1. 定义 State
2. 定义 Node
3. 添加 Edge
4. compile 后 invoke
```

代码对应：

```python
graph = StateGraph(SimpleState)
graph.add_node("answer", answer_node)
graph.add_edge(START, "answer")
graph.add_edge("answer", END)
app = graph.compile()
```

==这就是最小 LangGraph。==

它现在还没有模型，也没有工具。

但流程已经是图了。

---

## 二十三、19｜带条件路由的 StateGraph
打开：

```text
app/langgraph_intro/demo_conditional_routing.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class RouterState(TypedDict):
    user_question: str
    intent: str
    answer: str


def classify_intent_node(state: RouterState) -> dict:
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
    state: RouterState,
) -> Literal["general_answer", "order_answer", "refund_answer"]:
    intent = state["intent"]

    if intent == "refund":
        return "refund_answer"

    if intent == "order":
        return "order_answer"

    return "general_answer"


def general_answer_node(state: RouterState) -> dict:
    return {
        "answer": "这是普通问题，走普通 Chat。"
    }


def order_answer_node(state: RouterState) -> dict:
    return {
        "answer": "这是订单问题，下一步应该查询订单系统。"
    }


def refund_answer_node(state: RouterState) -> dict:
    return {
        "answer": "这是退款问题，下一步应该查询订单状态和退款规则。"
    }


def build_graph():
    graph = StateGraph(RouterState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("order_answer", order_answer_node)
    graph.add_node("refund_answer", refund_answer_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general_answer": "general_answer",
            "order_answer": "order_answer",
            "refund_answer": "refund_answer",
        },
    )

    graph.add_edge("general_answer", END)
    graph.add_edge("order_answer", END)
    graph.add_edge("refund_answer", END)

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
            "intent": "",
            "answer": "",
        })

        print("question:", question)
        print("result:", result)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建测试脚本：

```text
scripts/test_lg29_conditional_routing.py
```

写入：

```python
from app.langgraph_intro.demo_conditional_routing import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg29_conditional_routing.py
```

---

### 【重点内容】
这个例子就开始像真实 Agent 流程了。

它先走：

```text
classify_intent
```

然后根据 intent 路由到不同节点。

如果是 general，走普通回答。

如果是 order，走订单节点。

如果是 refund，走退款节点。

==这就是 Conditional Routing。==

下一章我们会专门深入讲 State。

后面还会专门讲 Node、Edge 和 Conditional Routing。

这一章先建立感觉。

---

## 二十四、20｜电商客服图的雏形
打开：

```text
app/langgraph_intro/demo_graph_for_ecommerce.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class EcommerceGraphState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    order_status: str | None
    policy_answer: str | None
    final_answer: str


def classify_intent_node(state: EcommerceGraphState) -> dict:
    question = state["user_question"]

    if "退款" in question:
        return {"intent": "refund"}

    if "订单" in question or "物流" in question:
        return {"intent": "order"}

    return {"intent": "general"}


def extract_order_id_node(state: EcommerceGraphState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        return {"order_id": "10001"}

    if "10002" in question:
        return {"order_id": "10002"}

    return {"order_id": None}


def route_after_extract_order_id(
    state: EcommerceGraphState,
) -> Literal["ask_order_id", "query_order"]:
    if not state.get("order_id"):
        return "ask_order_id"

    return "query_order"


def query_order_node(state: EcommerceGraphState) -> dict:
    order_id = state["order_id"]

    if order_id == "10001":
        return {"order_status": "已发货"}

    if order_id == "10002":
        return {"order_status": "已付款，待发货"}

    return {"order_status": "未查询到订单"}


def retrieve_policy_node(state: EcommerceGraphState) -> dict:
    order_status = state.get("order_status")

    if order_status == "已付款，待发货":
        return {
            "policy_answer": "根据售后规则，订单未发货时可以申请取消订单并退款。"
        }

    if order_status == "已发货":
        return {
            "policy_answer": "根据售后规则，订单已发货后，需要收到商品后再发起退货退款申请。"
        }

    return {
        "policy_answer": "当前状态无法确认退款规则，建议转人工客服。"
    }


def ask_order_id_node(state: EcommerceGraphState) -> dict:
    return {
        "final_answer": "请您提供订单号，我帮您继续查询和判断。"
    }


def generate_general_answer_node(state: EcommerceGraphState) -> dict:
    return {
        "final_answer": "这是一个普通问题，可以走普通 Chat。"
    }


def generate_order_answer_node(state: EcommerceGraphState) -> dict:
    return {
        "final_answer": f"您的订单当前状态是：{state.get('order_status')}。"
    }


def generate_refund_answer_node(state: EcommerceGraphState) -> dict:
    return {
        "final_answer": (
            f"您的订单当前状态是：{state.get('order_status')}。"
            f"{state.get('policy_answer')}"
        )
    }


def route_by_intent(
    state: EcommerceGraphState,
) -> Literal["general", "order_or_refund"]:
    if state["intent"] == "general":
        return "general"

    return "order_or_refund"


def route_after_query_order(
    state: EcommerceGraphState,
) -> Literal["retrieve_policy", "generate_order_answer"]:
    if state["intent"] == "refund":
        return "retrieve_policy"

    return "generate_order_answer"


def build_graph():
    graph = StateGraph(EcommerceGraphState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("retrieve_policy", retrieve_policy_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("generate_general_answer", generate_general_answer_node)
    graph.add_node("generate_order_answer", generate_order_answer_node)
    graph.add_node("generate_refund_answer", generate_refund_answer_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "general": "generate_general_answer",
            "order_or_refund": "extract_order_id",
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
        },
    )

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
        result = app.invoke({
            "user_question": question,
            "intent": "",
            "order_id": None,
            "order_status": None,
            "policy_answer": None,
            "final_answer": "",
        })

        print("question:", question)
        print("final_answer:", result["final_answer"])
        print("full_state:", result)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建测试脚本：

```text
scripts/test_lg29_ecommerce_graph.py
```

写入：

```python
from app.langgraph_intro.demo_graph_for_ecommerce import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子还没有接大模型。

也没有接真实 Tool。

但是它已经体现出 LangGraph 的价值了。

你可以清楚看到每个节点：

```text
classify_intent
extract_order_id
query_order
retrieve_policy
generate_answer
```

也可以清楚看到每个分支：

```text
缺订单号 -> ask_order_id
退款问题 -> retrieve_policy
订单问题 -> generate_order_answer
普通问题 -> generate_general_answer
```

这比把所有逻辑塞进一个 Agent prompt 里更可控。

---

## 二十五、21｜LangGraph 不是不用大模型
### 【重点内容】
这一章的代码很多都是规则写死的。

这只是为了让大家先理解图结构。

后面真实项目里，节点里面可以放大模型。

比如：

```text
classify_intent_node：
调用 Structured Output 做意图识别

extract_order_id_node：
调用模型或正则提取订单号

query_order_node：
调用 Tool

retrieve_policy_node：
调用 RAG

generate_answer_node：
调用 ChatModel 生成最终回复
```

也就是说，LangGraph 不是不用 LangChain。

而是把 LangChain 的能力放进每个节点里。

---

## 二十六、22｜LangGraph 在项目一中的位置
第 19 章项目现在大概是：

```text
FastAPI Router
 ↓
ChatService
 ↓
普通 Chat / Tool Calling / Agent / RAG
```

引入 LangGraph 后：

```text
FastAPI Router
 ↓
ChatService
 ↓
GraphService
 ↓
LangGraph StateGraph
  ├── classify_intent_node
  ├── extract_order_id_node
  ├── query_order_node
  ├── retrieve_policy_node
  ├── human_confirm_node
  └── generate_answer_node
```

---

### 【重点内容】
LangGraph 不会替代 FastAPI。

也不会替代 PostgreSQL、Redis、权限系统。

它在我们的项目里属于：

```text
Agent 编排层
```

也就是 ChatService 后面的一层。

业务接口还是 FastAPI。

数据还是 PostgreSQL。

缓存还是 Redis。

Graph 负责复杂 Agent 流程。

---

## 二十七、23｜为什么企业级 Agent 平台必须有图编排
企业级 Agent 平台通常需要：

```text
1. 可视化流程
2. 多节点编排
3. 条件分支
4. 工具节点
5. 知识库节点
6. 人工确认节点
7. 失败重试节点
8. 审批节点
9. 多 Agent 协作
10. 执行日志和状态回放
```

这些都天然适合图。

---

### 【重点内容】
==你看现在很多 Agent 平台，比如工作流型 Agent，本质都是图。==

左边拖节点。

中间连线。

右边配置节点参数。

为什么都这样设计？

因为复杂流程必须可视化。

LangGraph 就是代码层面的状态图编排。

后面我们做企业级 AI Agent 平台时，就会把这些能力做成：

```text
可视化编排
节点配置
流程运行
执行记录
调试面板
```

---

## 二十八、24｜LangGraph 阶段学习路线
接下来 LangGraph 阶段会这样走：

```text
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
第 34 章｜LangGraph Persistence
第 35 章｜LangGraph Human-in-the-loop
第 36 章｜LangGraph Agent Memory
第 37 章｜LangGraph Multi-Agent
第 38 章｜项目二：LangGraph 电商客服 Agent
```

---

### 【重点内容】
这一阶段会比 LangChain 阶段更偏架构。

LangChain 是组件。

LangGraph 是编排。

学完这一阶段，大家就能把前面的：

```text
Prompt
Model
Tool
RAG
Agent
```

编排成一个企业级可控 Agent 流程。

---

## 二十九、25｜面试回答：为什么需要 LangGraph
### 回答话术一：通用版
```text
我理解 LangGraph 主要解决的是复杂 Agent 的状态编排问题。

LangChain Agent 适合快速实现一个能调用工具的 Agent，但如果业务流程变复杂，比如需要多步骤、条件分支、人工确认、中断恢复、状态持久化、多 Agent 协作，单纯靠 create_agent 或者手写 if/else 就会很难维护。

LangGraph 把 Agent 流程抽象成 State、Node、Edge 和 Conditional Routing。每个节点负责一个明确步骤，State 负责保存执行上下文，Edge 负责控制执行顺序，条件边负责根据状态选择下一步。再配合 checkpoint，就可以支持暂停、恢复、人类介入和执行过程追踪。

所以我会把 LangChain 理解成 LLM 组件层，把 LangGraph 理解成复杂 Agent 的流程编排层。
```

---

### 回答话术二：项目版
```text
比如我做一个电商客服 Agent，用户问“我的订单 10002 还没发货，可以退款吗？”

如果用普通 Agent，模型可能自由决定调用订单工具或知识库工具，但这个流程不够稳定。

用 LangGraph，我可以把流程拆成几个节点：

第一步识别意图；
第二步提取订单号；
第三步查询订单状态；
第四步根据订单状态检索退款规则；
第五步判断是否需要人工确认；
第六步生成最终客服回复。

这样每一步都可控、可观测、可测试，也方便后续加 checkpoint 和 human-in-the-loop。
```

---

### 回答话术三：架构版
```text
在架构上，我不会让业务层直接依赖一个黑盒 Agent。

我会让 FastAPI 负责接口层，Service 负责业务编排入口，LangGraph 负责 Agent 状态流转，LangChain 负责模型、Prompt、Tool、Retriever 等组件。

这样做的好处是，业务系统仍然保留权限、日志、缓存、数据库和审计能力，而 Agent 的复杂流程通过 StateGraph 显式表达，后续也方便做可视化编排和企业级 Agent 平台。
```

---

## 三十、26｜常见错误一：把 LangGraph 当成 LangChain 的替代品
错误理解：

```text
学了 LangGraph，就不用 LangChain 了。
```

正确理解：

```text
LangGraph 负责图编排。
LangChain 负责模型、Prompt、Tool、Retriever 等组件。
两者经常一起用。
```

---

## 三十一、27｜常见错误二：所有场景都用 LangGraph
错误：

```text
普通 Chat 也用 LangGraph。
```

正确：

```text
简单问题用简单方案。
复杂流程再用 LangGraph。
```

比如：

```text
普通问答：Chat
知识库问答：RAG Chain
简单工具调用：Agent
复杂状态流程：LangGraph
```

---

## 三十二、28｜常见错误三：State 设计太随意
错误：

```python
class State(TypedDict):
    data: dict
```

问题：

```text
字段不清晰
节点输入输出混乱
难调试
难维护
```

推荐：

```python
class EcommerceState(TypedDict):
    user_question: str
    intent: str
    order_id: str | None
    order_info: dict | None
    policy_answer: str | None
    final_answer: str
```

---

## 三十三、29｜常见错误四：Node 里什么都做
错误：

```text
一个 node 里完成意图识别、查订单、查知识库、生成回答
```

正确：

```text
一个 node 只负责一个明确步骤
```

比如：

```text
classify_intent_node
extract_order_id_node
query_order_node
retrieve_policy_node
generate_answer_node
```

---

## 三十四、30｜常见错误五：条件分支写在节点里太深
错误：

```text
所有 if/else 都写在一个 node 里面
```

正确：

```text
节点负责更新状态
条件边负责路由下一步
```

---

## 三十五、31｜常见错误六：没有考虑中断恢复
很多企业流程都需要中断：

```text
缺少用户信息
等待用户补充
等待人工审批
等待外部系统回调
等待支付结果
```

如果没有 checkpoint 和状态保存，就很难恢复。

---

## 三十六、32｜常见错误七：忽略可观测性
LangGraph 每一步都应该记录：

```text
node_name
input_state
output_update
latency
error
trace_id
tool_calls
model_usage
```

否则 Agent 出问题时很难排查。

---

## 三十七、33｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| LangChain Agent 不够可控 | 第 26 章 Agent |
| Agent + RAG 复杂流程 | 第 28 章 Agent + RAG |
| State | 第 19 章 ChatService 中散落的上下文 |
| Node | Service 里的单个处理步骤 |
| Edge | 业务执行顺序 |
| Conditional Routing | 第 24 章意图识别后的路由 |
| Checkpoint | Redis / PostgreSQL 状态保存升级 |
| Human-in-the-loop | 第 25 章高风险工具确认 |
| Streaming | 第 16 章流式输出升级 |
| Multi-Agent | 后续多智能体协作 |
| 企业级 Agent 平台 | 后续毕业项目 |


---

## 三十八、34｜本章完整复习
这一章我们完成了：

```text
1. 复习 LangChain Agent 的优势
2. 分析 LangChain Agent 在复杂业务里的不足
3. 用 if/else 示例展示复杂流程的问题
4. 理解 LangGraph 解决复杂 Agent 状态编排
5. 理解 LangChain 和 LangGraph 的关系
6. 理解 State 的作用
7. 理解 Node 的作用
8. 理解 Edge 的作用
9. 理解 Conditional Routing 的作用
10. 理解 Checkpoint 的作用
11. 理解 Human-in-the-loop 的作用
12. 理解 Streaming 在图执行中的作用
13. 理解 Multi-Agent 为什么适合图编排
14. 对比 LangGraph 和传统工作流
15. 对比 LangGraph 和普通 if/else
16. 明确什么时候用 LangChain Agent
17. 明确什么时候用 LangGraph
18. 写出第一个最小 StateGraph
19. 写出条件路由 StateGraph
20. 写出电商客服图雏形
21. 理解 LangGraph 在项目一中的位置
22. 理解企业级 Agent 平台为什么需要图编排
23. 明确 LangGraph 阶段学习路线
24. 准备面试回答话术
25. 总结 LangGraph 常见错误
```

---

## 三十九、35｜课后任务一：跑通 if/else 复杂流程示例
要求：

```text
1. 运行 scripts/test_lg29_problem_without_graph.py
2. 观察 handle_customer_request_without_graph 的代码复杂度
3. 说出这个写法的 3 个问题
```

参考回答：

```text
1. 状态散落在局部变量里
2. 分支越来越多后难维护
3. 无法很好支持中断恢复和人工确认
```

---

## 四十、36｜课后任务二：跑通第一个 StateGraph
要求：

```text
1. 运行 scripts/test_lg29_first_state_graph.py
2. 找到 SimpleState
3. 找到 answer_node
4. 找到 START 和 END
5. 说明 invoke 输入和输出分别是什么
```

---

## 四十一、37｜课后任务三：跑通条件路由 Graph
要求：

```text
1. 运行 scripts/test_lg29_conditional_routing.py
2. 输入普通问题、订单问题、退款问题
3. 观察不同问题进入不同节点
4. 说明 add_conditional_edges 的作用
```

---

## 四十二、38｜课后任务四：跑通电商客服图雏形
要求：

```text
1. 运行 scripts/test_lg29_ecommerce_graph.py
2. 输入“我的订单 10002 还没发货，可以退款吗？”
3. 观察经过哪些节点
4. 查看最终 full_state
5. 说明 State 中每个字段的作用
```

---

## 四十三、39｜课后任务五：给电商客服图增加物流分支
要求新增：

```text
intent=logistics
```

并增加节点：

```text
query_logistics_node
generate_logistics_answer_node
```

测试问题：

```text
帮我查一下订单 10001 的物流。
```

---

## 四十四、40｜课后任务六：设计退款人工确认节点
要求设计：

```text
human_confirm_node
```

触发条件：

```text
1. 退款金额大于 500
2. 订单状态异常
3. 工具返回风险标记
```

本章先画流程，不要求实现 interrupt。

后面第 35 章再真正实现 Human-in-the-loop。

---

## 四十五、41｜课后任务七：画出 LangGraph 电商客服流程图
要求包含：

```text
START
classify_intent
extract_order_id
ask_order_id
query_order
retrieve_policy
generate_order_answer
generate_refund_answer
human_confirm
END
```

并标注条件：

```text
intent=general
intent=order
intent=refund
order_id=None
need_human_confirm=True
```

---

## 四十六、42｜课后任务八：准备面试回答
题目：

```text
为什么你们项目里需要 LangGraph？
```

要求从三个角度回答：

```text
1. 技术角度：State / Node / Edge / Conditional Routing
2. 业务角度：电商客服退款流程、订单流程、人工确认
3. 工程角度：可观测、可恢复、可测试、可扩展
```

---

## 四十七、43｜本章总结
### 【重点内容】
好了，到这里，第 29 章我们就讲完了。

这一章是 LangGraph 阶段的第一章。

我们重点解决一个问题：

```text
为什么已经有 LangChain Agent 了，还要 LangGraph？
```

答案很简单：

LangChain Agent 适合快速构建 Agent，LangGraph 适合构建复杂、可控、可恢复、可观察的企业级 Agent 流程。

==大家一定要记住 LangGraph 的几个核心概念：==

```text
State：保存执行上下文
Node：一个处理步骤
Edge：节点之间的执行顺序
Conditional Routing：根据状态决定下一步
Checkpoint：保存状态快照，支持恢复
Human-in-the-loop：高风险步骤等待人工确认
Streaming：观察图执行过程
Multi-Agent：多个 Agent 节点协作
```

这一章我们还写了三个示例：

```text
1. 不用 LangGraph 时 if/else 会变复杂
2. 第一个最小 StateGraph
3. 带条件路由的电商客服图雏形
```

从下一章开始，我们会正式深入 LangGraph 核心概念。

---

---

> [!success] 一句话带走
> ==当 Agent 从「能跑」走向「可控、可恢复、可审计」，就需要 LangGraph。==

> [!quote] 关于本文档
> 由原始讲义 `第 29 章｜为什么需要 LangGraph.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
