---
title: "第 37 章｜LangGraph Multi-Agent"
chapter: "37"
source: "第 37 章｜LangGraph Multi-Agent.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langgraph
  - multi-agent
  - supervisor
---

# 第 37 章｜LangGraph Multi-Agent

> [!abstract] 本章重点
>
> - ==Multi-Agent 是分工，不是多开几个模型== — 每个 Agent 有明确职责和自己的工具集。
> - ==Supervisor 负责派活，Worker 负责干活== — 一个做决策，多个做执行。
> - ==和 Tool Calling 的区别在「谁来决策」== — 工具没有自主性，子 Agent 有自己的循环。
> - ==共享 State 要定清楚读写边界== — 否则多个 Agent 互相覆盖字段。
> - ==能用单 Agent 就别上 Multi-Agent== — 复杂度、成本和调试难度都会翻倍。

> [!note] 大白话
>
> - **Supervisor**：调度员：看一眼任务，决定交给哪个工人。

> [!info] 导航与来源
> - 原始讲义：[[第 37 章｜LangGraph Multi-Agent|打开原始讲义]]
> - [[第 36 章｜LangGraph Agent Memory|上一章｜第 36 章]]
> - [[第 38 章｜项目二：LangGraph 电商客服 Agent|下一章｜第 38 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#Multi-Agent]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜Multi-Agent 一句话解释]]
- [[#七、03｜为什么需要 Multi-Agent]]
- [[#八、04｜Multi-Agent 和 Tool Calling 的区别]]
- [[#九、05｜Multi-Agent 和 Workflow 的区别]]
- [[#十、06｜Multi-Agent 常见模式]]
- [[#十一、07｜Supervisor Agent 是什么]]
- [[#十二、08｜Worker Agent 是什么]]
- [[#十三、09｜Multi-Agent 设计原则]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

==前面我们已经完成 LangGraph 的核心能力：==

```text
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
第 34 章｜LangGraph Persistence
第 35 章｜LangGraph Human-in-the-loop
第 36 章｜LangGraph Agent Memory
```

到这里，我们已经具备了：

```text
状态管理
节点编排
条件路由
状态持久化
人工确认
短期记忆
长期记忆
```

这一章开始进入一个更复杂的方向：

## Multi-Agent
也就是：

```text
多智能体协作
```

简单理解：

```text
不是让一个 Agent 什么都干，
而是让多个 Agent 分工协作。
```

比如一个 AI 数据分析任务：

```text
用户：帮我分析一下最近 30 天订单数据，找出销售下滑原因，并给出优化建议。
```

单 Agent 要做：

```text
理解需求
拆解任务
写 SQL
查数据
分析指标
生成图表
写报告
检查结论
```

这时候一个 Agent 很容易混乱。

更好的方式是拆成：

```text
Planner Agent：拆任务
SQL Agent：写 SQL / 查数据
Analysis Agent：分析指标
Chart Agent：生成图表
Report Agent：写报告
Reviewer Agent：检查结论
```

==这就是 Multi-Agent。==

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. Multi-Agent 到底是什么
2. 为什么需要 Multi-Agent
3. 单 Agent 的边界在哪里
4. Multi-Agent 和 Tool Calling 的区别
5. Multi-Agent 和 Workflow 的区别
6. Multi-Agent 常见模式有哪些
7. Supervisor Agent 是什么
8. Worker Agent 是什么
9. Planner / Researcher / Executor / Reviewer 怎么拆
10. 多 Agent 如何共享 State
11. 多 Agent 如何通过 Edge 路由
12. 多 Agent 如何通过 Command handoff
13. 多 Agent 如何做 review loop
14. 多 Agent 如何避免互相踢皮球
15. 多 Agent 如何避免无限循环
16. 多 Agent 如何控制上下文
17. 多 Agent 如何记录 trace
18. 电商客服场景如何拆多 Agent
19. 数据分析场景如何拆多 Agent
20. 什么时候不应该用 Multi-Agent
21. LangGraph Supervisor 预构建库怎么理解
22. LangGraph Swarm 怎么理解
23. 面试中如何讲 Multi-Agent
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

安装基础依赖：

```bash
uv add "langgraph>=1.2,<1.3" \
       "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6"
```

如果要使用官方预构建 Supervisor：

```bash
uv add "langgraph-supervisor"
```

如果要使用 Swarm 风格多 Agent：

```bash
uv add "langgraph-swarm"
```

LangGraph API 参考里把 `langgraph_supervisor` 描述为用于构建 supervisor agent 委派 sub-agents 的多智能体系统，把 `langgraph_swarm` 描述为支持 agent 动态 handoff 的 swarm-style 多智能体模式。

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langgraph_multi_agent/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── mock_services.py
│   │   ├── graph_factory.py
│   │   ├── service.py
│   │   ├── demo_01_simple_multi_agent.py
│   │   ├── demo_02_supervisor_routing.py
│   │   ├── demo_03_worker_agents.py
│   │   ├── demo_04_reviewer_loop.py
│   │   ├── demo_05_handoff_command.py
│   │   ├── demo_06_context_control.py
│   │   ├── demo_07_ecommerce_multi_agent.py
│   │   ├── demo_08_data_analysis_multi_agent.py
│   │   ├── demo_09_prebuilt_supervisor_style.py
│   │   └── demo_10_multi_agent_api_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langgraph_multi_agent.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg37_01_simple_multi_agent.py
│   ├── test_lg37_02_supervisor_routing.py
│   ├── test_lg37_03_worker_agents.py
│   ├── test_lg37_04_reviewer_loop.py
│   ├── test_lg37_05_handoff_command.py
│   ├── test_lg37_06_context_control.py
│   ├── test_lg37_07_ecommerce_multi_agent.py
│   ├── test_lg37_08_data_analysis_multi_agent.py
│   ├── test_lg37_09_prebuilt_supervisor_style.py
│   └── test_lg37_10_multi_agent_service.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 37 章。

这一章我们讲 LangGraph Multi-Agent。

前面我们写的 Agent，大多数还是一个 Agent 在处理所有事情。

比如电商客服 Agent：

```text
识别意图
查订单
查知识库
评估风险
生成回答
```

这其实还能接受。

但是任务再复杂一点，一个 Agent 就容易扛不住。

比如用户说：

```text
帮我分析最近 30 天订单数据，找出销售下滑原因，生成一份老板能看的报告。
```

这不是简单问答。

它里面有很多角色：

```text
需求分析
指标设计
SQL 查询
数据分析
图表生成
报告撰写
质量检查
```

如果全塞给一个 Agent，它可能会：

```text
一会儿写 SQL
一会儿做分析
一会儿写报告
中间忘了原始目标
结论没有证据
图表和文字对不上
```

所以复杂任务要拆。

把一个大 Agent 拆成多个小 Agent。

每个 Agent 做自己擅长的事。

==这就是 Multi-Agent。==

---

## 六、02｜Multi-Agent 一句话解释
### 【实操】
```text
Multi-Agent
=
多个专职 Agent 通过共享 State 和路由规则协作完成一个复杂任务。
```

更口语一点：

```text
一个人干不清楚的活，拆给一个小团队。
```

---

### 【重点内容】
你可以把 Multi-Agent 理解成一个项目小组。

比如：

```text
Supervisor Agent：项目经理
Planner Agent：任务拆解
Researcher Agent：资料收集
Executor Agent：执行动作
Reviewer Agent：质检
Reporter Agent：输出报告
```

每个 Agent 只负责一部分。

LangGraph 的作用就是把这些 Agent 编排起来。

谁先做，谁后做，做完交给谁，失败后怎么回退，都由 Graph 控制。

---

## 七、03｜为什么需要 Multi-Agent
单 Agent 的问题：

```text
1. Prompt 过长
2. 工具太多
3. 角色混乱
4. 任务边界不清
5. 中间结果不可控
6. 复杂任务容易跑偏
7. 很难做质量检查
8. 很难复用能力
```

Multi-Agent 的好处：

```text
1. 分工清晰
2. 每个 Agent Prompt 更短
3. 每个 Agent 工具更少
4. 方便复用
5. 方便插入 Reviewer
6. 方便做审计和 trace
7. 方便局部替换
8. 更适合复杂业务流程
```

---

### 【重点内容】
单 Agent 最大的问题是“什么都想让它干”。

但是能力越多，Agent 越容易乱。

比如你给一个 Agent 绑定 30 个工具。

==它不一定知道什么时候该用哪个。==

Prompt 里又写了很多角色要求：

```text
你既是客服，又是数据分析师，又是售后专家，又是财务审核员。
```

这就很容易混。

Multi-Agent 的核心思想就是：

```text
把复杂能力拆开。
```

一个 Agent 不要什么都懂。

只要在自己边界内做好就行。

---

## 八、04｜Multi-Agent 和 Tool Calling 的区别
| 对比项 | Tool Calling | Multi-Agent |
| --- | --- | --- |
| 核心对象 | 工具 | 智能体 |
| 主要作用 | 调用外部能力 | 分工协作 |
| 粒度 | 比较小 | 比较大 |
| 是否有独立角色 | 没有 | 有 |
| 是否有独立 Prompt | 通常没有 | 有 |
| 是否可有独立工具集 | 工具本身 | 每个 Agent 可以有自己的工具 |
| 适合场景 | 查订单、查天气、查数据库 | 研究、分析、计划、执行、审核 |


---

### 【重点内容】
Tool 是能力。

Agent 是角色。

比如：

```text
query_order 是工具。
OrderAgent 是智能体。
```

OrderAgent 可以用 query_order、query_logistics、query_refund_status 等多个工具。

所以不要把 Tool 和 Agent 混在一起。

一个 Agent 可以有多个 Tool。

多个 Agent 也可以共享某些 Tool。

---

## 九、05｜Multi-Agent 和 Workflow 的区别
| 对比项 | Workflow | Multi-Agent |
| --- | --- | --- |
| 流程 | 更固定 | 更动态 |
| 节点 | 普通函数 / 服务 | Agent / 子图 / LLM 节点 |
| 决策方式 | 规则为主 | LLM + 规则 |
| 适合场景 | 明确业务流程 | 复杂开放任务 |
| 可控性 | 强 | 需要设计约束 |
| 风险 | 低 | 更高，需要审计和限制 |


---

### 【重点内容】
Workflow 是固定流程。

比如：

```text
上传文件
解析文件
切 chunk
生成 embedding
入库
```

这个不需要 Multi-Agent。

用普通 LangGraph 工作流就够了。

Multi-Agent 更适合开放任务。

比如：

```text
分析市场趋势
生成投资报告
诊断系统问题
写数据分析报告
复杂客服协同处理
```

这些任务需要不同角色协作。

---

## 十、06｜Multi-Agent 常见模式
常见模式有四种。

### 模式一：Supervisor / Worker
```text
Supervisor 负责判断下一步交给谁。
Worker 负责执行具体任务。
```

### 模式二：Planner / Executor
```text
Planner 先拆任务。
Executor 按计划执行。
```

### 模式三：Researcher / Writer / Reviewer
```text
Researcher 收集资料。
Writer 生成内容。
Reviewer 检查质量。
```

### 模式四：Handoff / Swarm
```text
当前 Agent 可以把控制权交给另一个 Agent。
```

LangChain handoffs 文档里提到，handoff 模式的核心是通过工具或状态变量更新当前步骤或 active_agent，让系统根据状态切换配置或路由到不同 agent；它适合多阶段对话和客服类流程，比如先收集保修信息，再转给专家。

---

## 十一、07｜Supervisor Agent 是什么
### 【实操】
```text
Supervisor Agent
=
多 Agent 系统里的调度者
```

它负责：

```text
1. 理解用户任务
2. 判断应该调用哪个 Worker
3. 汇总 Worker 输出
4. 决定是否继续
5. 决定是否结束
6. 必要时交给 Reviewer
```

---

### 【重点内容】
Supervisor 就像项目经理。

它不是所有事情都自己干。

它主要决定：

```text
现在该让哪个 Agent 干活？
干完之后下一步是什么？
结果够不够？
要不要让 Reviewer 检查？
```

比如用户问退款。

Supervisor 判断：

```text
这是售后问题，交给 RefundAgent。
```

用户问物流。

Supervisor 判断：

```text
这是物流问题，交给 LogisticsAgent。
```

用户问复杂分析。

Supervisor 判断：

```text
先交给 PlannerAgent 拆任务，再交给 SQLAgent 查数据。
```

官方 `langgraph_supervisor` 包提供了 `create_supervisor`，用于创建一个 supervisor 来管理多个 agent；它还提供 handoff 相关工具，例如创建 handoff tool 和 forward message tool。

---

## 十二、08｜Worker Agent 是什么
Worker Agent 是具体干活的 Agent。

例如：

```text
OrderAgent：订单查询
RefundAgent：退款处理
RAGAgent：知识库问答
SQLAgent：数据查询
ChartAgent：图表生成
ReportAgent：报告生成
ReviewerAgent：质量检查
```

Worker 的特点：

```text
1. 角色单一
2. 工具有限
3. 输入明确
4. 输出结构化
5. 可复用
```

---

### 【重点内容】
==Worker Agent 一定要小而专。==

不要一个 Worker 既查订单，又写报告，又审核，又转人工。

这样又回到了单 Agent 混乱的问题。

一个好的 Worker 应该像一个函数一样清晰：

```text
输入是什么
输出是什么
能调用哪些工具
不能做什么
```

---

## 十三、09｜Multi-Agent 设计原则
### 原则一：先问自己能不能不用 Multi-Agent
如果普通 Workflow 能解决，不要强行 Multi-Agent。

### 原则二：每个 Agent 有清晰边界
```text
OrderAgent 只处理订单。
RefundAgent 只处理退款。
ReviewerAgent 只检查结果。
```

### 原则三：共享 State，不共享混乱上下文
Agent 之间通过 State 传递关键结果。

不要把所有消息全部丢给每个 Agent。

LangChain handoffs 文档特别强调：多个 subgraph handoff 时，要明确控制哪些消息在 agent 之间传递；如果传递上下文不当，会造成 conversation history 结构错误、上下文膨胀和下游 agent 混乱。

### 原则四：每一步都要有 trace
```text
哪个 Agent 执行了
输入是什么
输出是什么
下一步是谁
为什么这么路由
```

### 原则五：必须有终止条件
否则多个 Agent 会互相转来转去。

---

## 十四、10｜创建目录
执行：

```bash
mkdir -p app/langgraph_multi_agent

touch app/langgraph_multi_agent/__init__.py
touch app/langgraph_multi_agent/schemas.py
touch app/langgraph_multi_agent/mock_services.py
touch app/langgraph_multi_agent/graph_factory.py
touch app/langgraph_multi_agent/service.py
touch app/langgraph_multi_agent/demo_01_simple_multi_agent.py
touch app/langgraph_multi_agent/demo_02_supervisor_routing.py
touch app/langgraph_multi_agent/demo_03_worker_agents.py
touch app/langgraph_multi_agent/demo_04_reviewer_loop.py
touch app/langgraph_multi_agent/demo_05_handoff_command.py
touch app/langgraph_multi_agent/demo_06_context_control.py
touch app/langgraph_multi_agent/demo_07_ecommerce_multi_agent.py
touch app/langgraph_multi_agent/demo_08_data_analysis_multi_agent.py
touch app/langgraph_multi_agent/demo_09_prebuilt_supervisor_style.py
touch app/langgraph_multi_agent/demo_10_multi_agent_api_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_multi_agent

New-Item app\langgraph_multi_agent\__init__.py
New-Item app\langgraph_multi_agent\schemas.py
New-Item app\langgraph_multi_agent\mock_services.py
New-Item app\langgraph_multi_agent\graph_factory.py
New-Item app\langgraph_multi_agent\service.py
New-Item app\langgraph_multi_agent\demo_01_simple_multi_agent.py
New-Item app\langgraph_multi_agent\demo_02_supervisor_routing.py
New-Item app\langgraph_multi_agent\demo_03_worker_agents.py
New-Item app\langgraph_multi_agent\demo_04_reviewer_loop.py
New-Item app\langgraph_multi_agent\demo_05_handoff_command.py
New-Item app\langgraph_multi_agent\demo_06_context_control.py
New-Item app\langgraph_multi_agent\demo_07_ecommerce_multi_agent.py
New-Item app\langgraph_multi_agent\demo_08_data_analysis_multi_agent.py
New-Item app\langgraph_multi_agent\demo_09_prebuilt_supervisor_style.py
New-Item app\langgraph_multi_agent\demo_10_multi_agent_api_adapter.py
```

---

## 十五、11｜准备公共 State
打开：

```text
app/langgraph_multi_agent/schemas.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph.message import add_messages


class AgentTraceItem(TypedDict, total=False):
    agent_name: str
    input_summary: str
    output_summary: str
    next_agent: str | None
    reason: str


class WorkerResult(TypedDict, total=False):
    agent_name: str
    success: bool
    content: str
    data: dict
    confidence: float


class MultiAgentState(TypedDict):
    user_question: str
    messages: Annotated[list[AnyMessage], add_messages]

    task_type: Literal[
        "general",
        "ecommerce",
        "data_analysis",
        "research",
        "unknown",
    ]

    plan: Annotated[list[str], operator.add]

    current_agent: str | None
    next_agent: str | None
    active_agent: str | None

    order_result: WorkerResult | None
    refund_result: WorkerResult | None
    rag_result: WorkerResult | None
    sql_result: WorkerResult | None
    analysis_result: WorkerResult | None
    chart_result: WorkerResult | None
    report_result: WorkerResult | None
    review_result: WorkerResult | None

    final_answer: str
    is_finished: bool

    retry_count: int
    max_retry: int

    agent_trace: Annotated[list[AgentTraceItem], operator.add]
    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


def create_initial_multi_agent_state(
    user_question: str,
) -> MultiAgentState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "task_type": "unknown",

        "plan": [],

        "current_agent": None,
        "next_agent": None,
        "active_agent": None,

        "order_result": None,
        "refund_result": None,
        "rag_result": None,
        "sql_result": None,
        "analysis_result": None,
        "chart_result": None,
        "report_result": None,
        "review_result": None,

        "final_answer": "",
        "is_finished": False,

        "retry_count": 0,
        "max_retry": 2,

        "agent_trace": [],
        "logs": [],
        "errors": [],
    }
```

---

### 【重点内容】
这个 MultiAgentState 比前面的 State 更关注协作过程。

重点字段有：

```text
task_type：任务类型
plan：任务计划
current_agent：当前执行哪个 Agent
next_agent：下一步交给哪个 Agent
active_agent：handoff 模式下当前活跃 Agent
order_result / refund_result / rag_result：不同 Worker 的输出
review_result：Reviewer 的审核结果
agent_trace：记录每个 Agent 做了什么
retry_count：防止无限循环
```

==这就是 Multi-Agent 的核心。==

---

## 十六、12｜准备 Mock Services
打开：

```text
app/langgraph_multi_agent/mock_services.py
```

写入：

```python
def mock_query_order(order_id: str | None) -> dict:
    orders = {
        "10001": {
            "order_id": "10001",
            "status": "shipped",
            "status_text": "已发货",
        },
        "10002": {
            "order_id": "10002",
            "status": "paid",
            "status_text": "已付款，待发货",
        },
    }

    if not order_id:
        return {
            "success": False,
            "message": "缺少订单号",
            "data": None,
        }

    order = orders.get(order_id)

    if not order:
        return {
            "success": False,
            "message": "未查询到订单",
            "data": None,
        }

    return {
        "success": True,
        "message": "订单查询成功",
        "data": order,
    }


def mock_refund_policy(order_status: str | None) -> str:
    if order_status == "paid":
        return "订单未发货时，可以申请取消订单并退款。"

    if order_status == "shipped":
        return "订单已发货后，需要用户收到商品后再申请退货退款。"

    return "当前订单状态无法确认退款规则，建议转人工。"


def mock_query_sales_data() -> dict:
    return {
        "period": "最近 30 天",
        "total_orders": 1200,
        "total_amount": 368000,
        "last_period_orders": 1500,
        "last_period_amount": 450000,
        "top_category": "AI 课程",
        "weak_category": "传统前端课程",
    }


def extract_order_id(question: str) -> str | None:
    if "10001" in question:
        return "10001"

    if "10002" in question:
        return "10002"

    return None
```

---

## 十七、13｜示例一：最小 Multi-Agent 顺序协作
打开：

```text
app/langgraph_multi_agent/demo_01_simple_multi_agent.py
```

写入：

```python
from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def planner_agent(state: MultiAgentState) -> dict:
    return {
        "current_agent": "planner_agent",
        "plan": [
            "理解用户问题",
            "生成回答草稿",
            "检查回答质量",
        ],
        "agent_trace": [
            {
                "agent_name": "planner_agent",
                "input_summary": state["user_question"],
                "output_summary": "已生成三步计划",
                "next_agent": "writer_agent",
                "reason": "计划完成后交给写作 Agent",
            }
        ],
        "logs": ["planner_agent：完成任务拆解"],
    }


def writer_agent(state: MultiAgentState) -> dict:
    draft = (
        "LangGraph Multi-Agent 可以理解成多个 Agent "
        "通过共享 State 和路由协作完成复杂任务。"
    )

    return {
        "current_agent": "writer_agent",
        "report_result": {
            "agent_name": "writer_agent",
            "success": True,
            "content": draft,
            "data": {},
            "confidence": 0.8,
        },
        "agent_trace": [
            {
                "agent_name": "writer_agent",
                "input_summary": "根据 planner 计划生成回答",
                "output_summary": draft,
                "next_agent": "reviewer_agent",
                "reason": "回答需要检查质量",
            }
        ],
        "logs": ["writer_agent：完成回答草稿"],
    }


def reviewer_agent(state: MultiAgentState) -> dict:
    content = state["report_result"]["content"]

    return {
        "current_agent": "reviewer_agent",
        "review_result": {
            "agent_name": "reviewer_agent",
            "success": True,
            "content": "审核通过",
            "data": {
                "passed": True,
            },
            "confidence": 0.9,
        },
        "final_answer": content,
        "is_finished": True,
        "agent_trace": [
            {
                "agent_name": "reviewer_agent",
                "input_summary": content,
                "output_summary": "审核通过",
                "next_agent": None,
                "reason": "结果质量达标",
            }
        ],
        "logs": ["reviewer_agent：审核通过"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("planner_agent", planner_agent)
    graph.add_node("writer_agent", writer_agent)
    graph.add_node("reviewer_agent", reviewer_agent)

    graph.add_edge(START, "planner_agent")
    graph.add_edge("planner_agent", "writer_agent")
    graph.add_edge("writer_agent", "reviewer_agent")
    graph.add_edge("reviewer_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_multi_agent_state(
            "解释一下 LangGraph Multi-Agent。"
        )
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("plan:")
    for item in result["plan"]:
        print("-", item)

    print("=" * 80)
    print("agent_trace:")
    for item in result["agent_trace"]:
        print(item)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_01_simple_multi_agent.py
```

写入：

```python
from app.langgraph_multi_agent.demo_01_simple_multi_agent import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg37_01_simple_multi_agent.py
```

---

### 【重点内容】
这是最小 Multi-Agent。

它不是很智能，但结构很清楚：

```text
Planner
 ↓
Writer
 ↓
Reviewer
```

每个 Agent 都是一个 Node。

每个 Agent 都往 State 里写自己的结果。

最终 Reviewer 决定输出。

==这就是多 Agent 最基础的形态。==

---

## 十八、14｜示例二：Supervisor 路由
打开：

```text
app/langgraph_multi_agent/demo_02_supervisor_routing.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def supervisor_agent(state: MultiAgentState) -> dict:
    question = state["user_question"]

    if "订单" in question or "退款" in question or "物流" in question:
        task_type = "ecommerce"
        next_agent = "ecommerce_agent"
    elif "数据" in question or "销售" in question or "分析" in question:
        task_type = "data_analysis"
        next_agent = "data_agent"
    elif "调研" in question or "趋势" in question:
        task_type = "research"
        next_agent = "research_agent"
    else:
        task_type = "general"
        next_agent = "general_agent"

    return {
        "current_agent": "supervisor_agent",
        "task_type": task_type,
        "next_agent": next_agent,
        "agent_trace": [
            {
                "agent_name": "supervisor_agent",
                "input_summary": question,
                "output_summary": f"task_type={task_type}",
                "next_agent": next_agent,
                "reason": "根据用户问题选择合适的 Worker Agent",
            }
        ],
        "logs": [f"supervisor_agent：路由到 {next_agent}"],
    }


def route_by_supervisor(
    state: MultiAgentState,
) -> Literal[
    "ecommerce_agent",
    "data_agent",
    "research_agent",
    "general_agent",
]:
    return state["next_agent"]  # type: ignore[return-value]


def ecommerce_agent(state: MultiAgentState) -> dict:
    answer = "这是电商客服问题，应该交给订单、退款或物流 Agent 继续处理。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["ecommerce_agent：处理完成"],
    }


def data_agent(state: MultiAgentState) -> dict:
    answer = "这是数据分析问题，应该交给 SQL、Analysis、Report Agent 继续处理。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["data_agent：处理完成"],
    }


def research_agent(state: MultiAgentState) -> dict:
    answer = "这是研究调研问题，应该交给 Researcher 和 Writer Agent。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["research_agent：处理完成"],
    }


def general_agent(state: MultiAgentState) -> dict:
    answer = "这是普通问题，可以直接回答。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "logs": ["general_agent：处理完成"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("supervisor_agent", supervisor_agent)
    graph.add_node("ecommerce_agent", ecommerce_agent)
    graph.add_node("data_agent", data_agent)
    graph.add_node("research_agent", research_agent)
    graph.add_node("general_agent", general_agent)

    graph.add_edge(START, "supervisor_agent")

    graph.add_conditional_edges(
        "supervisor_agent",
        route_by_supervisor,
        {
            "ecommerce_agent": "ecommerce_agent",
            "data_agent": "data_agent",
            "research_agent": "research_agent",
            "general_agent": "general_agent",
        },
    )

    graph.add_edge("ecommerce_agent", END)
    graph.add_edge("data_agent", END)
    graph.add_edge("research_agent", END)
    graph.add_edge("general_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "我的订单 10002 可以退款吗？",
        "帮我分析最近 30 天销售数据。",
        "调研一下 AI Agent 平台趋势。",
        "你好，介绍一下 LangGraph。",
    ]

    for question in questions:
        result = app.invoke(
            create_initial_multi_agent_state(question)
        )

        print("question:", question)
        print("task_type:", result["task_type"])
        print("next_agent:", result["next_agent"])
        print("final_answer:", result["final_answer"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_02_supervisor_routing.py
```

写入：

```python
from app.langgraph_multi_agent.demo_02_supervisor_routing import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个示例就是 Supervisor 模式。

Supervisor 不直接解决所有问题。

它负责判断：

```text
这是电商任务？
这是数据分析任务？
这是研究任务？
还是普通任务？
```

然后写入：

```text
next_agent
```

条件路由函数再根据 next_agent 把任务交给对应 Worker。

==这就是 Supervisor + Worker 的基本结构。==

---

## 十九、15｜示例三：Worker Agents 分工
打开：

```text
app/langgraph_multi_agent/demo_03_worker_agents.py
```

写入：

```python
from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.mock_services import (
    extract_order_id,
    mock_query_order,
    mock_refund_policy,
)
from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def order_agent(state: MultiAgentState) -> dict:
    order_id = extract_order_id(state["user_question"])
    result = mock_query_order(order_id)

    return {
        "current_agent": "order_agent",
        "order_result": {
            "agent_name": "order_agent",
            "success": result["success"],
            "content": result["message"],
            "data": result.get("data") or {},
            "confidence": 0.95,
        },
        "agent_trace": [
            {
                "agent_name": "order_agent",
                "input_summary": state["user_question"],
                "output_summary": result["message"],
                "next_agent": "refund_agent",
                "reason": "退款问题需要继续判断售后规则",
            }
        ],
        "logs": ["order_agent：订单查询完成"],
    }


def refund_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"] or {}

    if not order_result.get("success"):
        content = "订单查询失败，无法判断退款规则。"
        success = False
    else:
        order_data = order_result.get("data") or {}
        policy = mock_refund_policy(order_data.get("status"))
        content = policy
        success = True

    return {
        "current_agent": "refund_agent",
        "refund_result": {
            "agent_name": "refund_agent",
            "success": success,
            "content": content,
            "data": {},
            "confidence": 0.9,
        },
        "agent_trace": [
            {
                "agent_name": "refund_agent",
                "input_summary": str(order_result),
                "output_summary": content,
                "next_agent": "answer_agent",
                "reason": "退款规则判断完成，交给回答 Agent",
            }
        ],
        "logs": ["refund_agent：退款规则判断完成"],
    }


def answer_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"] or {}
    refund_result = state["refund_result"] or {}

    if not order_result.get("success"):
        answer = "没有查询到订单，请您检查订单号是否正确。"
    else:
        order_data = order_result.get("data") or {}
        answer = (
            f"您的订单状态是：{order_data.get('status_text')}。"
            f"{refund_result.get('content')}"
        )

    return {
        "current_agent": "answer_agent",
        "final_answer": answer,
        "is_finished": True,
        "agent_trace": [
            {
                "agent_name": "answer_agent",
                "input_summary": "订单结果 + 退款规则",
                "output_summary": answer,
                "next_agent": None,
                "reason": "生成最终用户回答",
            }
        ],
        "logs": ["answer_agent：最终回答完成"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("order_agent", order_agent)
    graph.add_node("refund_agent", refund_agent)
    graph.add_node("answer_agent", answer_agent)

    graph.add_edge(START, "order_agent")
    graph.add_edge("order_agent", "refund_agent")
    graph.add_edge("refund_agent", "answer_agent")
    graph.add_edge("answer_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_multi_agent_state(
            "我的订单 10002 可以退款吗？"
        )
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("order_result:")
    print(result["order_result"])

    print("=" * 80)
    print("refund_result:")
    print(result["refund_result"])

    print("=" * 80)
    print("agent_trace:")
    for item in result["agent_trace"]:
        print(item)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_03_worker_agents.py
```

写入：

```python
from app.langgraph_multi_agent.demo_03_worker_agents import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子里有三个 Worker。

```text
OrderAgent：查订单
RefundAgent：判断退款规则
AnswerAgent：组织最终回答
```

每个 Worker 只做自己的事情。

这比一个大函数好维护很多。

后面要替换真实能力时也简单：

```text
OrderAgent 换真实订单工具。
RefundAgent 换 RAG 知识库。
AnswerAgent 换 LLM 生成。
```

---

## 二十、16｜示例四：Reviewer Loop
很多 Multi-Agent 都需要 Reviewer。

==因为 Worker 生成的结果不一定合格。==

流程：

```text
Writer Agent
 ↓
Reviewer Agent
 ↓
通过 -> END
不通过 -> Writer Agent 重写
```

打开：

```text
app/langgraph_multi_agent/demo_04_reviewer_loop.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def writer_agent(state: MultiAgentState) -> dict:
    retry_count = state["retry_count"]

    if retry_count == 0:
        content = "Multi-Agent 就是多个 Agent 一起干活。"
    else:
        content = (
            "LangGraph Multi-Agent 是把复杂任务拆给多个专职 Agent，"
            "通过共享 State、Node、Edge 和条件路由协作完成。"
            "比如 Planner 负责拆任务，Worker 负责执行，Reviewer 负责检查质量。"
        )

    return {
        "current_agent": "writer_agent",
        "report_result": {
            "agent_name": "writer_agent",
            "success": True,
            "content": content,
            "data": {},
            "confidence": 0.7 if retry_count == 0 else 0.92,
        },
        "logs": [f"writer_agent：生成第 {retry_count + 1} 版回答"],
    }


def reviewer_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}
    content = report.get("content", "")

    if len(content) < 50 and state["retry_count"] < state["max_retry"]:
        return {
            "current_agent": "reviewer_agent",
            "review_result": {
                "agent_name": "reviewer_agent",
                "success": False,
                "content": "回答太短，需要补充定义、机制和例子。",
                "data": {
                    "passed": False,
                },
                "confidence": 0.9,
            },
            "retry_count": state["retry_count"] + 1,
            "logs": ["reviewer_agent：审核不通过，要求重写"],
        }

    return {
        "current_agent": "reviewer_agent",
        "review_result": {
            "agent_name": "reviewer_agent",
            "success": True,
            "content": "审核通过",
            "data": {
                "passed": True,
            },
            "confidence": 0.95,
        },
        "logs": ["reviewer_agent：审核通过"],
    }


def route_after_review(
    state: MultiAgentState,
) -> Literal["rewrite", "finish"]:
    review = state["review_result"] or {}
    data = review.get("data") or {}

    if not data.get("passed") and state["retry_count"] <= state["max_retry"]:
        return "rewrite"

    return "finish"


def finish_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}

    return {
        "current_agent": "finish_agent",
        "final_answer": report.get("content", ""),
        "is_finished": True,
        "logs": ["finish_agent：输出最终结果"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("writer_agent", writer_agent)
    graph.add_node("reviewer_agent", reviewer_agent)
    graph.add_node("finish_agent", finish_agent)

    graph.add_edge(START, "writer_agent")
    graph.add_edge("writer_agent", "reviewer_agent")

    graph.add_conditional_edges(
        "reviewer_agent",
        route_after_review,
        {
            "rewrite": "writer_agent",
            "finish": "finish_agent",
        },
    )

    graph.add_edge("finish_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_multi_agent_state(
            "解释 LangGraph Multi-Agent。"
        ),
        config={
            "recursion_limit": 10
        },
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("retry_count:", result["retry_count"])

    print("=" * 80)
    print("review_result:")
    print(result["review_result"])

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_04_reviewer_loop.py
```

写入：

```python
from app.langgraph_multi_agent.demo_04_reviewer_loop import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
Reviewer Loop 是非常常见的模式。

写作、代码生成、数据分析、报告生成都可以加 Reviewer。

但是一定要注意：

```text
必须有 retry_count
必须有 max_retry
必须设置 recursion_limit
```

否则 Writer 和 Reviewer 可能一直循环。

---

## 二十一、17｜示例五：Command Handoff
Handoff 是 Multi-Agent 里的一个常见模式。

它的意思是：

```text
当前 Agent 主动把控制权交给另一个 Agent。
```

LangChain handoffs 文档里，handoff 可以通过工具返回 `Command` 来更新状态并改变下一步；多个 agent 作为不同 graph node 时，也可以通过 `Command(goto=..., graph=Command.PARENT)` 从子图切回父图并路由到另一个 agent。

打开：

```text
app/langgraph_multi_agent/demo_05_handoff_command.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def support_agent(
    state: MultiAgentState,
) -> Command[Literal["sales_agent", "answer_agent"]]:
    question = state["user_question"]

    if "购买" in question or "价格" in question:
        return Command(
            update={
                "current_agent": "support_agent",
                "active_agent": "sales_agent",
                "logs": ["support_agent：发现是购买/价格问题，handoff 给 sales_agent"],
                "agent_trace": [
                    {
                        "agent_name": "support_agent",
                        "input_summary": question,
                        "output_summary": "需要销售 Agent 处理",
                        "next_agent": "sales_agent",
                        "reason": "用户问题和购买价格相关",
                    }
                ],
            },
            goto="sales_agent",
        )

    return Command(
        update={
            "current_agent": "support_agent",
            "active_agent": "answer_agent",
            "report_result": {
                "agent_name": "support_agent",
                "success": True,
                "content": "这是售后支持问题，我可以直接处理。",
                "data": {},
                "confidence": 0.9,
            },
            "logs": ["support_agent：售后问题，直接交给 answer_agent"],
        },
        goto="answer_agent",
    )


def sales_agent(state: MultiAgentState) -> dict:
    content = "这是销售问题，我可以介绍套餐价格和购买流程。"

    return {
        "current_agent": "sales_agent",
        "report_result": {
            "agent_name": "sales_agent",
            "success": True,
            "content": content,
            "data": {},
            "confidence": 0.9,
        },
        "logs": ["sales_agent：完成销售回答"],
    }


def answer_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}

    return {
        "current_agent": "answer_agent",
        "final_answer": report.get("content", ""),
        "is_finished": True,
        "logs": ["answer_agent：最终回答完成"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("support_agent", support_agent)
    graph.add_node("sales_agent", sales_agent)
    graph.add_node("answer_agent", answer_agent)

    graph.add_edge(START, "support_agent")

    graph.add_edge("sales_agent", "answer_agent")
    graph.add_edge("answer_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "我的订单售后怎么处理？",
        "这个课程价格是多少，怎么买？",
    ]

    for question in questions:
        result = app.invoke(
            create_initial_multi_agent_state(question)
        )

        print("question:", question)
        print("active_agent:", result["active_agent"])
        print("final_answer:", result["final_answer"])
        print("logs:", result["logs"])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_05_handoff_command.py
```

写入：

```python
from app.langgraph_multi_agent.demo_05_handoff_command import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子演示 Command Handoff。

support_agent 如果发现问题和价格购买有关，就不自己处理。

它直接：

```python
goto="sales_agent"
```

==这就是 handoff。==

注意这里是教学版简单 handoff。

如果你使用真正的 LLM tool handoff，消息历史要保证结构完整，特别是工具调用和 ToolMessage 必须配对。LangChain 文档也强调，LLM 工具调用需要对应 ToolMessage，否则 conversation history 会变成不完整结构。

---

## 二十二、18｜示例六：控制 Agent 上下文
Multi-Agent 最大的坑之一：

```text
把所有上下文都丢给所有 Agent。
```

这样会导致：

```text
token 成本高
Agent 看到无关信息
角色混乱
输出跑偏
```

正确做法：

```text
每个 Agent 只拿自己需要的上下文。
```

打开：

```text
app/langgraph_multi_agent/demo_06_context_control.py
```

写入：

```python
from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def planner_agent(state: MultiAgentState) -> dict:
    plan = [
        "查询订单状态",
        "查询退款规则",
        "生成客服回答",
    ]

    return {
        "current_agent": "planner_agent",
        "plan": plan,
        "logs": ["planner_agent：生成任务计划"],
    }


def order_agent(state: MultiAgentState) -> dict:
    # OrderAgent 只需要用户问题和订单相关计划。
    local_context = {
        "user_question": state["user_question"],
        "plan": [
            item for item in state["plan"]
            if "订单" in item
        ],
    }

    return {
        "current_agent": "order_agent",
        "order_result": {
            "agent_name": "order_agent",
            "success": True,
            "content": "订单 10002 当前为已付款，待发货。",
            "data": {
                "order_id": "10002",
                "status": "paid",
            },
            "confidence": 0.95,
        },
        "agent_trace": [
            {
                "agent_name": "order_agent",
                "input_summary": str(local_context),
                "output_summary": "订单状态查询完成",
                "next_agent": "refund_agent",
                "reason": "订单状态会影响退款规则",
            }
        ],
        "logs": ["order_agent：使用裁剪后的上下文完成订单查询"],
    }


def refund_agent(state: MultiAgentState) -> dict:
    # RefundAgent 不需要全部 messages，只需要订单结果。
    order_result = state["order_result"] or {}
    local_context = {
        "order_result": order_result,
    }

    return {
        "current_agent": "refund_agent",
        "refund_result": {
            "agent_name": "refund_agent",
            "success": True,
            "content": "未发货订单可以取消并退款。",
            "data": {
                "used_context": local_context,
            },
            "confidence": 0.9,
        },
        "logs": ["refund_agent：只基于订单结果判断退款规则"],
    }


def answer_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"] or {}
    refund_result = state["refund_result"] or {}

    answer = (
        f"{order_result.get('content')}"
        f"{refund_result.get('content')}"
    )

    return {
        "current_agent": "answer_agent",
        "final_answer": answer,
        "is_finished": True,
        "logs": ["answer_agent：完成最终回答"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("planner_agent", planner_agent)
    graph.add_node("order_agent", order_agent)
    graph.add_node("refund_agent", refund_agent)
    graph.add_node("answer_agent", answer_agent)

    graph.add_edge(START, "planner_agent")
    graph.add_edge("planner_agent", "order_agent")
    graph.add_edge("order_agent", "refund_agent")
    graph.add_edge("refund_agent", "answer_agent")
    graph.add_edge("answer_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_multi_agent_state(
            "我的订单 10002 可以退款吗？"
        )
    )

    print("final_answer:")
    print(result["final_answer"])

    print("=" * 80)
    print("agent_trace:")
    for item in result["agent_trace"]:
        print(item)

    print("=" * 80)
    print("logs:")
    for log in result["logs"]:
        print("-", log)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_06_context_control.py
```

写入：

```python
from app.langgraph_multi_agent.demo_06_context_control import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个例子重点不是功能。

重点是上下文控制。

OrderAgent 不需要看到所有东西。

RefundAgent 也不需要看到完整 messages。

每个 Agent 只拿自己需要的信息。

==这就是 Multi-Agent 的 Context Engineering。==

在多 agent handoff 场景里，官方文档也建议不要把完整 subagent 历史都传给下游 agent，因为会增加 token 成本，并可能让接收方被无关内部信息干扰。

---

## 二十三、19｜电商客服 Multi-Agent 设计
我们把电商客服拆成这些 Agent：

```text
SupervisorAgent：
判断用户问题类型。

OrderAgent：
负责订单查询。

RefundAgent：
负责退款规则和退款建议。

LogisticsAgent：
负责物流查询。

RAGAgent：
负责售后知识库检索。

RiskAgent：
负责风险评估。

AnswerAgent：
负责最终客服回复。

ReviewerAgent：
检查回答是否安全、是否缺少依据。
```

---

### 【重点内容】
大家注意这个拆法。

电商客服不是所有场景都需要多 Agent。

简单 FAQ 不需要。

但如果是：

```text
订单 + 售后 + 退款 + 风险 + 人工确认
```

这种复杂流程，就适合拆。

比如退款问题：

```text
Supervisor
 ↓
OrderAgent
 ↓
RefundAgent
 ↓
RiskAgent
 ↓
AnswerAgent
 ↓
ReviewerAgent
```

这样每个环节都清楚。

---

## 二十四、20｜示例七：电商客服 Multi-Agent
打开：

```text
app/langgraph_multi_agent/demo_07_ecommerce_multi_agent.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.mock_services import (
    extract_order_id,
    mock_query_order,
    mock_refund_policy,
)
from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def supervisor_agent(state: MultiAgentState) -> dict:
    question = state["user_question"]

    if "退款" in question or "退货" in question:
        next_agent = "order_agent"
        task_type = "ecommerce"
        plan = [
            "查询订单状态",
            "判断退款规则",
            "评估回答风险",
            "生成客服回答",
            "检查回答质量",
        ]
    elif "物流" in question or "订单" in question:
        next_agent = "order_agent"
        task_type = "ecommerce"
        plan = [
            "查询订单状态",
            "生成客服回答",
            "检查回答质量",
        ]
    else:
        next_agent = "answer_agent"
        task_type = "general"
        plan = [
            "直接生成普通回答"
        ]

    return {
        "current_agent": "supervisor_agent",
        "next_agent": next_agent,
        "task_type": task_type,
        "plan": plan,
        "logs": [f"supervisor_agent：next_agent={next_agent}"],
        "agent_trace": [
            {
                "agent_name": "supervisor_agent",
                "input_summary": question,
                "output_summary": f"task_type={task_type}, next_agent={next_agent}",
                "next_agent": next_agent,
                "reason": "根据用户问题判断客服任务类型",
            }
        ],
    }


def route_after_supervisor(
    state: MultiAgentState,
) -> Literal["order_agent", "answer_agent"]:
    if state["next_agent"] == "order_agent":
        return "order_agent"

    return "answer_agent"


def order_agent(state: MultiAgentState) -> dict:
    order_id = extract_order_id(state["user_question"])
    result = mock_query_order(order_id)

    return {
        "current_agent": "order_agent",
        "order_result": {
            "agent_name": "order_agent",
            "success": result["success"],
            "content": result["message"],
            "data": result.get("data") or {},
            "confidence": 0.95,
        },
        "logs": [f"order_agent：{result['message']}"],
        "agent_trace": [
            {
                "agent_name": "order_agent",
                "input_summary": state["user_question"],
                "output_summary": result["message"],
                "next_agent": "refund_agent",
                "reason": "订单结果会决定后续退款或回答逻辑",
            }
        ],
    }


def route_after_order(
    state: MultiAgentState,
) -> Literal["refund_agent", "answer_agent"]:
    if "退款" in state["user_question"] or "退货" in state["user_question"]:
        return "refund_agent"

    return "answer_agent"


def refund_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"] or {}

    if not order_result.get("success"):
        content = "订单未查询成功，无法判断退款规则。"
        success = False
    else:
        order_data = order_result.get("data") or {}
        content = mock_refund_policy(order_data.get("status"))
        success = True

    return {
        "current_agent": "refund_agent",
        "refund_result": {
            "agent_name": "refund_agent",
            "success": success,
            "content": content,
            "data": {},
            "confidence": 0.9,
        },
        "logs": ["refund_agent：退款规则判断完成"],
        "agent_trace": [
            {
                "agent_name": "refund_agent",
                "input_summary": str(order_result),
                "output_summary": content,
                "next_agent": "risk_agent",
                "reason": "退款建议需要风险评估",
            }
        ],
    }


def risk_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"] or {}
    refund_result = state["refund_result"] or {}

    order_data = order_result.get("data") or {}
    status = order_data.get("status")

    if status == "shipped":
        content = "中风险：订单已发货，不能直接承诺立即退款。"
        confidence = 0.9
    elif not refund_result.get("success"):
        content = "高风险：缺少订单信息，不能给确定退款结论。"
        confidence = 0.9
    else:
        content = "低风险：可以按规则给出退款建议。"
        confidence = 0.9

    return {
        "current_agent": "risk_agent",
        "analysis_result": {
            "agent_name": "risk_agent",
            "success": True,
            "content": content,
            "data": {
                "risk_text": content,
            },
            "confidence": confidence,
        },
        "logs": ["risk_agent：风险评估完成"],
    }


def answer_agent(state: MultiAgentState) -> dict:
    order_result = state["order_result"]
    refund_result = state["refund_result"]
    risk_result = state["analysis_result"]

    if not order_result:
        answer = "这是普通问题，可以直接回答。"
    elif not order_result.get("success"):
        answer = "没有查询到订单，请您检查订单号是否正确。"
    else:
        order_data = order_result.get("data") or {}
        answer = f"您的订单状态是：{order_data.get('status_text')}。"

        if refund_result:
            answer += refund_result.get("content", "")

        if risk_result:
            answer += f" 风险提示：{risk_result.get('content')}"

    return {
        "current_agent": "answer_agent",
        "report_result": {
            "agent_name": "answer_agent",
            "success": True,
            "content": answer,
            "data": {},
            "confidence": 0.86,
        },
        "logs": ["answer_agent：客服回答草稿完成"],
    }


def reviewer_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}
    content = report.get("content", "")

    risky_words = ["保证", "一定", "立即到账"]

    has_risky_word = any(word in content for word in risky_words)

    if has_risky_word:
        review_content = "审核不通过：回答里包含过度承诺。"
        passed = False
    else:
        review_content = "审核通过：回答没有明显过度承诺。"
        passed = True

    return {
        "current_agent": "reviewer_agent",
        "review_result": {
            "agent_name": "reviewer_agent",
            "success": passed,
            "content": review_content,
            "data": {
                "passed": passed,
            },
            "confidence": 0.9,
        },
        "logs": [f"reviewer_agent：{review_content}"],
    }


def route_after_reviewer(
    state: MultiAgentState,
) -> Literal["finish", "rewrite"]:
    review = state["review_result"] or {}
    data = review.get("data") or {}

    if data.get("passed"):
        return "finish"

    if state["retry_count"] < state["max_retry"]:
        return "rewrite"

    return "finish"


def rewrite_answer_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}
    content = report.get("content", "")

    rewritten = (
        content
        .replace("保证", "通常")
        .replace("一定", "一般")
        .replace("立即到账", "以实际到账时间为准")
    )

    return {
        "current_agent": "rewrite_answer_agent",
        "retry_count": state["retry_count"] + 1,
        "report_result": {
            "agent_name": "rewrite_answer_agent",
            "success": True,
            "content": rewritten,
            "data": {},
            "confidence": 0.88,
        },
        "logs": ["rewrite_answer_agent：已根据审核意见改写回答"],
    }


def finish_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}

    return {
        "current_agent": "finish_agent",
        "final_answer": report.get("content", ""),
        "is_finished": True,
        "logs": ["finish_agent：输出最终客服回答"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("supervisor_agent", supervisor_agent)
    graph.add_node("order_agent", order_agent)
    graph.add_node("refund_agent", refund_agent)
    graph.add_node("risk_agent", risk_agent)
    graph.add_node("answer_agent", answer_agent)
    graph.add_node("reviewer_agent", reviewer_agent)
    graph.add_node("rewrite_answer_agent", rewrite_answer_agent)
    graph.add_node("finish_agent", finish_agent)

    graph.add_edge(START, "supervisor_agent")

    graph.add_conditional_edges(
        "supervisor_agent",
        route_after_supervisor,
        {
            "order_agent": "order_agent",
            "answer_agent": "answer_agent",
        },
    )

    graph.add_conditional_edges(
        "order_agent",
        route_after_order,
        {
            "refund_agent": "refund_agent",
            "answer_agent": "answer_agent",
        },
    )

    graph.add_edge("refund_agent", "risk_agent")
    graph.add_edge("risk_agent", "answer_agent")
    graph.add_edge("answer_agent", "reviewer_agent")

    graph.add_conditional_edges(
        "reviewer_agent",
        route_after_reviewer,
        {
            "finish": "finish_agent",
            "rewrite": "rewrite_answer_agent",
        },
    )

    graph.add_edge("rewrite_answer_agent", "reviewer_agent")
    graph.add_edge("finish_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    questions = [
        "我的订单 10002 可以退款吗？",
        "我的订单 10001 可以退款吗？",
        "帮我查一下订单 10002。",
        "你好。",
    ]

    for question in questions:
        result = app.invoke(
            create_initial_multi_agent_state(question),
            config={
                "recursion_limit": 20
            },
        )

        print("question:", question)
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
scripts/test_lg37_07_ecommerce_multi_agent.py
```

写入：

```python
from app.langgraph_multi_agent.demo_07_ecommerce_multi_agent import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个电商客服 Multi-Agent 已经很像企业项目了。

它包含：

```text
SupervisorAgent
OrderAgent
RefundAgent
RiskAgent
AnswerAgent
ReviewerAgent
RewriteAgent
FinishAgent
```

==这里最关键的是 Reviewer。==

因为客服场景不能乱承诺。

比如：

```text
保证退款
一定到账
立即到账
```

这些表达都很危险。

所以 ReviewerAgent 要检查安全性。

不通过就交给 RewriteAgent 改写。

---

## 二十五、21｜数据分析 Multi-Agent 设计
数据分析场景可以拆成：

```text
SupervisorAgent：判断是否是数据分析任务
PlannerAgent：拆分析步骤
SQLAgent：查询数据
AnalysisAgent：分析原因
ChartAgent：准备图表说明
ReportAgent：生成报告
ReviewerAgent：检查结论是否有数据支撑
```

---

### 【重点内容】
数据分析很适合 Multi-Agent。

因为它天然是多步骤任务。

尤其是：

```text
写 SQL
算指标
分析原因
生成报告
检查结论
```

这些职责非常不一样。

如果全让一个 Agent 做，很容易出幻觉。

比如数据里没查到，它也可能编一个原因。

ReviewerAgent 的作用就是检查：

```text
结论有没有数据依据？
有没有过度推断？
有没有把相关性说成因果？
```

---

## 二十六、22｜示例八：数据分析 Multi-Agent
打开：

```text
app/langgraph_multi_agent/demo_08_data_analysis_multi_agent.py
```

写入：

```python
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.langgraph_multi_agent.mock_services import mock_query_sales_data
from app.langgraph_multi_agent.schemas import (
    MultiAgentState,
    create_initial_multi_agent_state,
)


def planner_agent(state: MultiAgentState) -> dict:
    return {
        "current_agent": "planner_agent",
        "plan": [
            "查询最近 30 天销售数据",
            "对比上一周期订单量和销售额",
            "分析下滑原因",
            "生成优化建议",
            "检查报告是否有数据依据",
        ],
        "logs": ["planner_agent：完成数据分析计划"],
    }


def sql_agent(state: MultiAgentState) -> dict:
    data = mock_query_sales_data()

    content = (
        f"最近 30 天订单量 {data['total_orders']}，"
        f"销售额 {data['total_amount']}；"
        f"上一周期订单量 {data['last_period_orders']}，"
        f"销售额 {data['last_period_amount']}。"
    )

    return {
        "current_agent": "sql_agent",
        "sql_result": {
            "agent_name": "sql_agent",
            "success": True,
            "content": content,
            "data": data,
            "confidence": 0.98,
        },
        "logs": ["sql_agent：完成销售数据查询"],
    }


def analysis_agent(state: MultiAgentState) -> dict:
    sql_result = state["sql_result"] or {}
    data = sql_result.get("data") or {}

    order_drop = data["last_period_orders"] - data["total_orders"]
    amount_drop = data["last_period_amount"] - data["total_amount"]

    content = (
        f"订单量下降 {order_drop} 单，"
        f"销售额下降 {amount_drop}。"
        f"主要可能来自弱势品类：{data['weak_category']}。"
    )

    return {
        "current_agent": "analysis_agent",
        "analysis_result": {
            "agent_name": "analysis_agent",
            "success": True,
            "content": content,
            "data": {
                "order_drop": order_drop,
                "amount_drop": amount_drop,
            },
            "confidence": 0.86,
        },
        "logs": ["analysis_agent：完成指标分析"],
    }


def chart_agent(state: MultiAgentState) -> dict:
    content = (
        "建议生成两张图："
        "1）最近 30 天销售额 vs 上一周期销售额；"
        "2）不同品类销售贡献对比。"
    )

    return {
        "current_agent": "chart_agent",
        "chart_result": {
            "agent_name": "chart_agent",
            "success": True,
            "content": content,
            "data": {
                "charts": [
                    "period_sales_compare",
                    "category_sales_compare",
                ]
            },
            "confidence": 0.88,
        },
        "logs": ["chart_agent：完成图表建议"],
    }


def report_agent(state: MultiAgentState) -> dict:
    sql_result = state["sql_result"] or {}
    analysis_result = state["analysis_result"] or {}
    chart_result = state["chart_result"] or {}

    report = (
        "【数据分析报告】\n\n"
        "一、核心数据\n"
        f"{sql_result.get('content')}\n\n"
        "二、分析结论\n"
        f"{analysis_result.get('content')}\n\n"
        "三、图表建议\n"
        f"{chart_result.get('content')}\n\n"
        "四、优化建议\n"
        "建议重点优化传统前端课程的转化路径，"
        "同时加强 AI 课程的关联销售。"
    )

    return {
        "current_agent": "report_agent",
        "report_result": {
            "agent_name": "report_agent",
            "success": True,
            "content": report,
            "data": {},
            "confidence": 0.84,
        },
        "logs": ["report_agent：完成报告草稿"],
    }


def reviewer_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}
    content = report.get("content", "")

    has_data = "订单量" in content and "销售额" in content
    has_suggestion = "建议" in content

    passed = has_data and has_suggestion

    if passed:
        review_text = "审核通过：报告包含数据和建议。"
    else:
        review_text = "审核不通过：报告缺少数据依据或建议。"

    return {
        "current_agent": "reviewer_agent",
        "review_result": {
            "agent_name": "reviewer_agent",
            "success": passed,
            "content": review_text,
            "data": {
                "passed": passed,
            },
            "confidence": 0.9,
        },
        "logs": [f"reviewer_agent：{review_text}"],
    }


def route_after_review(
    state: MultiAgentState,
) -> Literal["finish", "rewrite"]:
    review = state["review_result"] or {}
    data = review.get("data") or {}

    if data.get("passed"):
        return "finish"

    if state["retry_count"] < state["max_retry"]:
        return "rewrite"

    return "finish"


def rewrite_report_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}
    old_content = report.get("content", "")

    new_content = (
        old_content
        + "\n\n【补充说明】以上结论基于 mock 销售数据，只能作为分析示例。"
    )

    return {
        "current_agent": "rewrite_report_agent",
        "retry_count": state["retry_count"] + 1,
        "report_result": {
            "agent_name": "rewrite_report_agent",
            "success": True,
            "content": new_content,
            "data": {},
            "confidence": 0.86,
        },
        "logs": ["rewrite_report_agent：根据审核意见补充报告"],
    }


def finish_agent(state: MultiAgentState) -> dict:
    report = state["report_result"] or {}

    return {
        "current_agent": "finish_agent",
        "final_answer": report.get("content", ""),
        "is_finished": True,
        "logs": ["finish_agent：输出最终数据分析报告"],
    }


def build_graph():
    graph = StateGraph(MultiAgentState)

    graph.add_node("planner_agent", planner_agent)
    graph.add_node("sql_agent", sql_agent)
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("chart_agent", chart_agent)
    graph.add_node("report_agent", report_agent)
    graph.add_node("reviewer_agent", reviewer_agent)
    graph.add_node("rewrite_report_agent", rewrite_report_agent)
    graph.add_node("finish_agent", finish_agent)

    graph.add_edge(START, "planner_agent")
    graph.add_edge("planner_agent", "sql_agent")
    graph.add_edge("sql_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "chart_agent")
    graph.add_edge("chart_agent", "report_agent")
    graph.add_edge("report_agent", "reviewer_agent")

    graph.add_conditional_edges(
        "reviewer_agent",
        route_after_review,
        {
            "finish": "finish_agent",
            "rewrite": "rewrite_report_agent",
        },
    )

    graph.add_edge("rewrite_report_agent", "reviewer_agent")
    graph.add_edge("finish_agent", END)

    return graph.compile()


def main():
    app = build_graph()

    result = app.invoke(
        create_initial_multi_agent_state(
            "帮我分析最近 30 天销售数据，找出下滑原因。"
        ),
        config={
            "recursion_limit": 20
        },
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

```text
scripts/test_lg37_08_data_analysis_multi_agent.py
```

写入：

```python
from app.langgraph_multi_agent.demo_08_data_analysis_multi_agent import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个数据分析 Multi-Agent 很适合后面第 59 章项目六。

它的流程是：

```text
Planner
 ↓
SQL
 ↓
Analysis
 ↓
Chart
 ↓
Report
 ↓
Reviewer
 ↓
Finish
```

大家注意，Reviewer 不只是看文字通不通顺。

它要检查：

```text
有没有数据依据
有没有建议
有没有过度推断
```

这才是数据分析 Agent 的质量控制。

---

## 二十七、23｜预构建 Supervisor 风格
除了手写 LangGraph，LangGraph 生态里也有预构建的 supervisor 包。

官方参考里 `create_supervisor` 用来创建多智能体 supervisor，可以传入 agents、model、tools、prompt、response_format、state_schema、output_mode 等参数。

打开：

```text
app/langgraph_multi_agent/demo_09_prebuilt_supervisor_style.py
```

写入：

```python
"""
这个文件是预构建 supervisor 风格示例。

注意：
1. 需要安装 langgraph-supervisor。
2. 需要配置真实模型。
3. 本课程核心仍然推荐先掌握手写 StateGraph。
"""

from langchain.agents import create_agent
from langgraph_supervisor import create_supervisor


def build_prebuilt_supervisor(model):
    order_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=(
            "你是 OrderAgent，只负责订单相关问题。"
            "不要处理退款政策，不要处理数据分析。"
        ),
    )

    refund_agent = create_agent(
        model=model,
        tools=[],
        system_prompt=(
            "你是 RefundAgent，只负责退款规则和退款建议。"
            "不要处理订单查询，不要处理数据分析。"
        ),
    )

    supervisor = create_supervisor(
        agents=[
            order_agent,
            refund_agent,
        ],
        model=model,
        prompt=(
            "你是 Supervisor。"
            "根据用户问题，把任务交给最合适的 Agent。"
            "如果是订单状态，交给 OrderAgent。"
            "如果是退款规则，交给 RefundAgent。"
        ),
    )

    return supervisor.compile()


def main():
    print("这是预构建 supervisor 风格示例，需要真实 model 才能运行。")
    print("课程项目中建议先使用手写 StateGraph 掌握原理。")


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lg37_09_prebuilt_supervisor_style.py
```

写入：

```python
from app.langgraph_multi_agent.demo_09_prebuilt_supervisor_style import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这里大家先看结构。

真实项目可以用预构建 supervisor。

但是我建议：

```text
先学手写 StateGraph。
```

因为手写能让你真正理解：

```text
State 怎么设计
Agent 之间怎么传结果
路由怎么控制
怎么防止死循环
怎么做审计
怎么插入人工确认
```

预构建库是加速器，不是替代理解。

---

## 二十八、24｜Swarm 模式怎么理解
Swarm 和 Supervisor 不太一样。

Supervisor 是中心调度。

Swarm 更像：

```text
每个 Agent 都可以根据自己的判断把任务交给下一个 Agent。
```

官方 `langgraph_swarm` 参考把 swarm 描述为一种多智能体架构：agents 可以根据各自专长动态地把控制权 hand off 给另一个 agent。

### 【重点内容】
Swarm 更灵活，但也更难控。

Supervisor 像：

```text
经理派活。
```

Swarm 像：

```text
团队成员之间互相转交。
```

==企业项目里，如果你追求稳定，我建议先用 Supervisor。==

Swarm 适合探索型任务，但要有更强的边界和退出机制。

---

## 二十九、25｜Multi-Agent 和 State 的关系
Multi-Agent 一定离不开 State。

Agent 之间不能靠“口口相传”。

要靠 State 传递结构化结果：

```text
order_result
refund_result
sql_result
analysis_result
chart_result
report_result
review_result
```

---

### 【重点内容】
这是很多人做 Multi-Agent 的坑。

他们让 Agent A 输出一大段自然语言，然后 Agent B 再读这段自然语言。

这可以跑 Demo，但工程上不稳定。

更推荐每个 Agent 输出结构化结果：

```python
{
    "agent_name": "sql_agent",
    "success": True,
    "content": "查询完成",
    "data": {
        "total_orders": 1200,
        "total_amount": 368000
    },
    "confidence": 0.98
}
```

这样后续 Agent 更好用。

---

## 三十、26｜Multi-Agent 和 Memory 的关系
Multi-Agent 也可以用 Memory。

比如：

```text
Supervisor 读取用户长期偏好
AnswerAgent 根据偏好调整回答风格
ReviewerAgent 读取历史风险规则
DataAgent 读取用户常用指标偏好
```

但是注意：

```text
不是每个 Agent 都能读所有 Memory。
```

要按角色控制。

---

## 三十一、27｜Multi-Agent 和 HITL 的关系
Multi-Agent 里也可以插入 Human-in-the-loop。

比如：

```text
RefundAgent 准备退款动作
RiskAgent 判断高风险
HumanReviewNode 暂停
人工 approve / reject / edit
ExecutorAgent 执行动作
```

这就是：

```text
Multi-Agent + HITL
```

---

### 【重点内容】
复杂企业 Agent 往往是组合拳：

```text
Multi-Agent 分工
Persistence 保存状态
Memory 记住上下文
RAG 提供知识依据
HITL 控制高风险动作
```

不要把这些能力割裂看。

---

## 三十二、28｜Multi-Agent 常见错误一：Agent 太多

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
一个简单客服问答拆 10 个 Agent。
```

问题：

```text
成本高
延迟高
调试难
路由复杂
收益不明显
```

正确：

```text
任务复杂到单 Agent 不好维护时，再拆 Multi-Agent。
```

---

## 三十三、29｜常见错误二：每个 Agent 都看到全部上下文
错误：

```text
把完整 messages、所有工具结果、所有内部日志都传给每个 Agent。
```

正确：

```text
每个 Agent 只读取自己需要的 State 字段。
```

---

## 三十四、30｜常见错误三：没有 Supervisor 或路由规则

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
多个 Agent 自己互相调用，没人管。
```

问题：

```text
容易互相踢皮球。
```

正确：

```text
用 Supervisor 或明确的 conditional routing 控制流程。
```

---

## 三十五、31｜常见错误四：没有 Reviewer
错误：

```text
Worker 输出什么就直接给用户。
```

推荐：

```text
高价值内容、数据分析、客服退款、代码生成，都加 Reviewer。
```

---

## 三十六、32｜常见错误五：没有终止条件
错误：

```text
Reviewer 不通过 -> Writer
Writer 写完 -> Reviewer
无限循环。
```

正确：

```text
retry_count
max_retry
recursion_limit
```

---

## 三十七、33｜常见错误六：Worker 输出非结构化

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

不推荐：

```text
SQLAgent 输出一大段自然语言。
```

推荐：

```python
{
    "success": True,
    "content": "查询完成",
    "data": {
        "rows": [...],
        "metrics": {...}
    },
    "confidence": 0.95
}
```

---

## 三十八、34｜常见错误七：把 Multi-Agent 当噱头
有些项目其实是固定流程：

```text
解析文档
切分文档
入向量库
检索回答
```

这种用普通 Graph 就够了。

不一定非要叫：

```text
ParserAgent
SplitterAgent
EmbeddingAgent
VectorAgent
```

如果只是包装名字，没有智能协作价值，就没必要。

---

## 三十九、35｜Multi-Agent 设计 Checklist
设计 Multi-Agent 前问自己：

```text
1. 这个任务是否真的复杂？
2. 能否用普通 Workflow 解决？
3. 每个 Agent 的职责是什么？
4. 每个 Agent 的输入是什么？
5. 每个 Agent 的输出是什么？
6. 每个 Agent 能用哪些工具？
7. 谁负责调度？
8. 谁负责审核？
9. Agent 之间共享哪些 State？
10. 哪些上下文不能传给下游 Agent？
11. 是否需要 Persistence？
12. 是否需要 Memory？
13. 是否需要 HITL？
14. 是否有 retry_count？
15. 是否有 END？
16. 如何记录 agent_trace？
17. 如何定位某个 Agent 的错误？
```

---

## 四十、36｜封装 Multi-Agent Graph Factory
打开：

```text
app/langgraph_multi_agent/graph_factory.py
```

写入：

```python
from app.langgraph_multi_agent.demo_07_ecommerce_multi_agent import (
    build_graph as build_ecommerce_multi_agent_graph,
)
from app.langgraph_multi_agent.demo_08_data_analysis_multi_agent import (
    build_graph as build_data_analysis_multi_agent_graph,
)


def create_multi_agent_graph(
    graph_type: str = "ecommerce",
):
    if graph_type == "data_analysis":
        return build_data_analysis_multi_agent_graph()

    return build_ecommerce_multi_agent_graph()
```

---

## 四十一、37｜封装 Multi-Agent Service
打开：

```text
app/langgraph_multi_agent/service.py
```

写入：

```python
from app.langgraph_multi_agent.graph_factory import create_multi_agent_graph
from app.langgraph_multi_agent.schemas import create_initial_multi_agent_state


class LangGraphMultiAgentService:
    def __init__(self):
        self.ecommerce_graph = create_multi_agent_graph("ecommerce")
        self.data_analysis_graph = create_multi_agent_graph("data_analysis")

    def chat(
        self,
        question: str,
        graph_type: str = "ecommerce",
    ) -> dict:
        graph = (
            self.data_analysis_graph
            if graph_type == "data_analysis"
            else self.ecommerce_graph
        )

        result = graph.invoke(
            create_initial_multi_agent_state(question),
            config={
                "recursion_limit": 30
            },
        )

        return {
            "answer": result["final_answer"],
            "task_type": result["task_type"],
            "plan": result["plan"],
            "agent_trace": result["agent_trace"],
            "logs": result["logs"],
        }


langgraph_multi_agent_service = LangGraphMultiAgentService()
```

创建测试脚本：

```text
scripts/test_lg37_10_multi_agent_service.py
```

写入：

```python
from app.langgraph_multi_agent.service import langgraph_multi_agent_service


def main():
    ecommerce_result = langgraph_multi_agent_service.chat(
        question="我的订单 10002 可以退款吗？",
        graph_type="ecommerce",
    )

    print("ecommerce_result:")
    print(ecommerce_result)
    print("=" * 120)

    data_result = langgraph_multi_agent_service.chat(
        question="帮我分析最近 30 天销售数据。",
        graph_type="data_analysis",
    )

    print("data_result:")
    print(data_result)


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg37_10_multi_agent_service.py
```

---

## 四十二、38｜创建 Multi-Agent API
创建：

```text
app/api/v1/langgraph_multi_agent.py
```

写入：

```python
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.langgraph_multi_agent.service import langgraph_multi_agent_service
from app.schemas.response import ApiResponse


router = APIRouter()


class MultiAgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    graph_type: Literal["ecommerce", "data_analysis"] = "ecommerce"


@router.post(
    "/langgraph/multi-agent/chat",
    response_model=ApiResponse[dict],
)
async def multi_agent_chat(
    request: MultiAgentChatRequest,
) -> ApiResponse[dict]:
    result = langgraph_multi_agent_service.chat(
        question=request.question,
        graph_type=request.graph_type,
    )

    return ApiResponse[dict](
        data=result
    )
```

---

## 四十三、39｜注册 Router
打开：

```text
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langgraph_multi_agent import router as langgraph_multi_agent_router
```

注册：

```python
api_router.include_router(
    langgraph_multi_agent_router,
    tags=["LangGraph Multi-Agent"],
)
```

---

## 四十四、40｜测试 Multi-Agent API
启动：

```bash
uv run uvicorn app.main:app --reload
```

测试电商客服：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/multi-agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_type": "ecommerce",
    "question": "我的订单 10002 可以退款吗？"
  }'
```

测试数据分析：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/multi-agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_type": "data_analysis",
    "question": "帮我分析最近 30 天销售数据。"
  }'
```

---

## 四十五、41｜Multi-Agent 和项目二的关系
第 38 章项目二是：

```text
LangGraph 电商客服 Agent
```

它可以有两个版本。

### 基础版
```text
一个 Graph
多个 Node
不是多 Agent
```

### 进阶版
```text
SupervisorAgent
OrderAgent
RefundAgent
RAGAgent
RiskAgent
AnswerAgent
ReviewerAgent
```

---

### 【重点内容】
==真实课程里建议先做基础版。==

基础版把业务流程跑通。

然后再升级成 Multi-Agent。

不要一上来就多 Agent。

否则学生会被概念绕晕。

---

## 四十六、42｜Multi-Agent 和项目六的关系
第 59 章项目六是：

```text
AI 数据分析 Multi-Agent
```

那一章会基于本章继续扩展：

```text
自然语言问题
 ↓
PlannerAgent
 ↓
SQLAgent
 ↓
AnalysisAgent
 ↓
ChartAgent
 ↓
ReportAgent
 ↓
ReviewerAgent
 ↓
最终分析报告
```

并接入：

```text
真实数据库
真实 SQL 安全检查
ECharts 图表配置生成
报告导出
权限控制
审计日志
```

---

## 四十七、43｜面试回答：Multi-Agent 怎么理解
### 回答话术一：基础版
```text
Multi-Agent 可以理解成多个专职 Agent 协作完成一个复杂任务。

在 LangGraph 里，我会把每个 Agent 设计成一个 Node，或者一个子 Graph。多个 Agent 通过共享 State 传递结构化结果，通过 Edge 或 Conditional Routing 控制下一步执行谁。

比如一个数据分析任务，可以拆成 PlannerAgent、SQLAgent、AnalysisAgent、ChartAgent、ReportAgent 和 ReviewerAgent。Planner 负责拆任务，SQL 负责查数据，Analysis 负责分析原因，Report 负责写报告，Reviewer 负责检查结论是否有数据依据。
```

---

### 回答话术二：项目版
```text
在电商客服场景里，如果只是普通问答，我不会上来就做 Multi-Agent。

但如果涉及订单查询、退款规则、风险评估、人工确认和回答审核，我会拆成多个 Agent：

SupervisorAgent 负责判断任务类型；
OrderAgent 负责订单查询；
RefundAgent 负责退款规则判断；
RiskAgent 负责风险评估；
AnswerAgent 负责生成客服回复；
ReviewerAgent 负责检查回答是否有过度承诺。

这些 Agent 之间通过 LangGraph State 共享 order_result、refund_result、risk_result、report_result 和 review_result。
```

---

### 回答话术三：工程版
```text
工程上设计 Multi-Agent，我会重点控制几个点：

第一，Agent 边界要清晰，每个 Agent 只做一类任务。

第二，Agent 输出要结构化，不能只是自然语言，否则下游 Agent 不好消费。

第三，Supervisor 或条件路由要明确，不能让多个 Agent 无规则互相调用。

第四，要有 Reviewer 和 retry_count，避免低质量结果直接返回，也避免无限循环。

第五，要控制上下文，每个 Agent 只拿自己需要的 State 字段，避免 token 浪费和角色混乱。

第六，高风险动作要接入 Human-in-the-loop，不能让 Agent 直接执行。
```

---

## 四十八、44｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Multi-Agent | 复杂 Agent 编排 |
| Supervisor | 第 33 章条件路由 |
| Worker Agent | 第 32 章 Node |
| Shared State | 第 31 章 State |
| Handoff | 第 30 章 Command |
| Reviewer Loop | 第 33 章循环路由 |
| Persistence | 第 34 章状态保存 |
| HITL | 第 35 章人工确认 |
| Memory | 第 36 章长期偏好 |
| Tool | 第 25 章工具调用 |
| RAG | 第 27 章知识库检索 |
| 电商客服 Multi-Agent | 第 38 章项目二进阶 |
| 数据分析 Multi-Agent | 第 59 章项目六 |


---

## 四十九、45｜本章完整复习
这一章我们完成了：

```text
1. 理解 Multi-Agent 是什么
2. 理解为什么复杂任务需要 Multi-Agent
3. 区分 Multi-Agent 和 Tool Calling
4. 区分 Multi-Agent 和 Workflow
5. 理解 Supervisor / Worker 模式
6. 理解 Planner / Executor 模式
7. 理解 Researcher / Writer / Reviewer 模式
8. 理解 Handoff / Swarm 模式
9. 理解 Supervisor Agent 的职责
10. 理解 Worker Agent 的职责
11. 总结 Multi-Agent 设计原则
12. 创建 langgraph_multi_agent 目录
13. 定义 MultiAgentState
14. 准备 mock services
15. 实现最小 Multi-Agent 顺序协作
16. 实现 Supervisor 路由
17. 实现 Worker Agents 分工
18. 实现 Reviewer Loop
19. 实现 Command Handoff
20. 实现 Agent 上下文控制
21. 设计电商客服 Multi-Agent
22. 实现电商客服 Multi-Agent Graph
23. 设计数据分析 Multi-Agent
24. 实现数据分析 Multi-Agent Graph
25. 理解预构建 Supervisor 风格
26. 理解 Swarm 模式
27. 理解 Multi-Agent 和 State 的关系
28. 理解 Multi-Agent 和 Memory 的关系
29. 理解 Multi-Agent 和 HITL 的关系
30. 总结 Multi-Agent 常见错误
31. 总结 Multi-Agent 设计 checklist
32. 封装 Multi-Agent Graph Factory
33. 封装 Multi-Agent Service
34. 创建 Multi-Agent API
35. 测试 Multi-Agent API
36. 理解 Multi-Agent 和项目二、项目六的关系
37. 准备面试回答话术
```

---

## 五十、46｜课后任务一：跑通最小 Multi-Agent
要求：

```text
1. 运行 scripts/test_lg37_01_simple_multi_agent.py
2. 查看 Planner / Writer / Reviewer 的执行顺序
3. 查看 agent_trace
4. 说明每个 Agent 写入了哪些 State 字段
```

---

## 五十一、47｜课后任务二：跑通 Supervisor 路由
要求：

```text
1. 运行 scripts/test_lg37_02_supervisor_routing.py
2. 测试订单问题
3. 测试数据分析问题
4. 测试研究问题
5. 查看 next_agent 如何变化
```

---

## 五十二、48｜课后任务三：跑通 Worker Agents
要求：

```text
1. 运行 scripts/test_lg37_03_worker_agents.py
2. 查看 order_result
3. 查看 refund_result
4. 说明 Worker Agent 为什么要输出结构化结果
```

---

## 五十三、49｜课后任务四：跑通 Reviewer Loop
要求：

```text
1. 运行 scripts/test_lg37_04_reviewer_loop.py
2. 查看第一版回答为什么不通过
3. 查看 retry_count 如何增加
4. 修改 max_retry 再观察结果
```

---

## 五十四、50｜课后任务五：跑通 Command Handoff
要求：

```text
1. 运行 scripts/test_lg37_05_handoff_command.py
2. 输入售后问题
3. 输入价格购买问题
4. 查看 support_agent 如何 handoff 给 sales_agent
```

---

## 五十五、51｜课后任务六：测试上下文控制
要求：

```text
1. 运行 scripts/test_lg37_06_context_control.py
2. 查看 OrderAgent 使用的 local_context
3. 查看 RefundAgent 使用的 local_context
4. 说明为什么不能把所有上下文都传给每个 Agent
```

---

## 五十六、52｜课后任务七：跑通电商客服 Multi-Agent
要求：

```text
1. 运行 scripts/test_lg37_07_ecommerce_multi_agent.py
2. 测试订单 10002 退款
3. 测试订单 10001 退款
4. 查看 OrderAgent / RefundAgent / RiskAgent / ReviewerAgent 的日志
5. 画出这条请求的执行路径
```

---

## 五十七、53｜课后任务八：跑通数据分析 Multi-Agent
要求：

```text
1. 运行 scripts/test_lg37_08_data_analysis_multi_agent.py
2. 查看 Planner 生成的计划
3. 查看 SQLAgent mock 数据
4. 查看 AnalysisAgent 分析结果
5. 查看 ReportAgent 报告
6. 查看 ReviewerAgent 审核结果
```

---

## 五十八、54｜课后任务九：扩展 LogisticsAgent
在电商客服 Multi-Agent 里新增：

```text
LogisticsAgent
```

要求：

```text
1. 当用户问物流时，Supervisor 路由到 OrderAgent
2. OrderAgent 查到 tracking_no
3. LogisticsAgent 查询物流
4. AnswerAgent 生成物流回答
5. ReviewerAgent 检查是否存在过度承诺
```

---

## 五十九、55｜课后任务十：扩展真实 LLM Worker
把这些 mock Agent 换成真实 LLM Agent：

```text
PlannerAgent
AnswerAgent
ReviewerAgent
```

要求：

```text
1. 每个 Agent 独立 system prompt
2. 每个 Agent 只拿必要上下文
3. 输出尽量结构化
4. 结果写入 State
5. 出错写入 errors
```

---

## 六十、56｜课后任务十一：设计 Multi-Agent Trace 表
建议表名：

```text
agent_run_traces
```

字段：

```text
id
trace_id
conversation_id
thread_id
agent_name
input_summary
output_summary
next_agent
reason
success
created_at
```

说明：

```text
agent_trace 放 State 里方便图内使用；
agent_run_traces 表用于长期审计和排查问题。
```

---

## 六十一、57｜课后任务十二：判断哪些场景不适合 Multi-Agent
请判断下面场景是否需要 Multi-Agent：

```text
1. 用户问“订单 10002 当前状态是什么？”
2. 用户上传 100 个 PDF，要求生成行业研究报告
3. 用户要求分析销售数据并输出图表
4. 用户问“今天星期几？”
5. 用户要求自动申请大额退款
6. 用户要求根据知识库回答一个制度问题
```

参考答案：

```text
1. 不一定需要，普通 Tool Node 即可。
2. 适合 Multi-Agent。
3. 适合 Multi-Agent。
4. 不需要。
5. 需要流程编排 + HITL，不一定要 Multi-Agent，但可以引入 RiskAgent。
6. 普通 RAG 即可，不一定需要 Multi-Agent。
```

---

## 六十二、58｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 37 章我们就讲完了。

这一章我们讲的是 LangGraph Multi-Agent。

大家一定要记住：

```text
Multi-Agent 不是为了炫技。
它是为了解决复杂任务中单 Agent 角色混乱、工具过多、上下文过大、质量不可控的问题。
```

最常见的设计是：

```text
Supervisor + Workers
```

Supervisor 负责调度。

Workers 负责执行。

复杂任务可以继续拆成：

```text
Planner
Researcher
SQL
Analysis
Chart
Report
Reviewer
Executor
```

==LangGraph 里，多 Agent 的核心还是前面几章：==

```text
State：保存共享上下文
Node：每个 Agent 是一个节点
Edge：控制执行流
Conditional Routing：决定下一个 Agent
Command：支持 handoff
Persistence：保存协作状态
Memory：提供长期偏好
HITL：控制高风险动作
```

真正做项目时，重点不是把 Agent 数量堆起来。

而是要设计清楚：

```text
谁负责什么
输入是什么
输出是什么
谁审核
怎么结束
怎么追踪
怎么防止失控
```

这才是企业级 Multi-Agent 的关键。

---

---

> [!success] 一句话带走
> ==多智能体解决的是职责拆分，不是模型不够聪明。==

> [!quote] 关于本文档
> 由原始讲义 `第 37 章｜LangGraph Multi-Agent.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
