# 一、本章定位
前面我们已经完成了 LangGraph 的几个核心能力：

```plain
第 29 章｜为什么需要 LangGraph
第 30 章｜LangGraph 核心概念
第 31 章｜LangGraph State
第 32 章｜LangGraph Node 与 Edge
第 33 章｜LangGraph Conditional Routing
第 34 章｜LangGraph Persistence
```

第 34 章我们讲了 Persistence。

也就是：

```plain
用 checkpointer 保存 Graph State，
让图可以暂停、恢复、继续、追踪。
```

这一章继续往前走，进入一个企业 Agent 非常关键的能力：

# Human-in-the-loop
也就是：

```plain
人在回路中
```

更口语一点：

**Agent 执行到高风险动作时，不允许模型直接干，必须暂停，等人确认后再继续。**

比如：

```plain
退款
发邮件
删数据
改订单
改价格
执行 SQL
创建合同
发送短信
调用支付接口
```

这些动作不能完全交给模型自动执行。

必须让人确认。

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Human-in-the-loop 到底解决什么问题
2. 为什么企业 Agent 必须有人类确认机制
3. LangGraph interrupt 是什么
4. Command(resume=...) 是什么
5. 为什么 interrupt 必须依赖 checkpointer
6. 为什么 resume 必须使用同一个 thread_id
7. 如何暂停图执行
8. 如何恢复图执行
9. 如何处理 approve / reject / edit
10. 如何在人审前查看当前 State
11. 如何让人工修改工具参数
12. 如何设计高风险工具暂停点
13. 如何避免 interrupt 前产生重复副作用
14. 如何设计电商退款 HITL 流程
15. 如何封装 HITL Service
16. 如何创建 FastAPI 审批接口
17. 前端如何展示待审批任务
18. 审批通过后如何继续执行
19. 审批拒绝后如何生成回复
20. 面试中如何讲 Human-in-the-loop
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
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END
```

`interrupt()` 会在节点内部暂停执行，并把一个值暴露给客户端；客户端恢复图时，要用 `Command(resume=...)` 提供人工输入或审批结果。官方参考文档还说明，恢复时节点会从头重新执行，所以 `interrupt()` 之前的副作用必须是幂等的，或者把真正副作用放到恢复之后。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langgraph_hitl/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── graph_factory.py
│   │   ├── service.py
│   │   ├── demo_01_basic_interrupt.py
│   │   ├── demo_02_approve_reject.py
│   │   ├── demo_03_edit_payload.py
│   │   ├── demo_04_get_state_before_resume.py
│   │   ├── demo_05_ecommerce_refund_hitl.py
│   │   ├── demo_06_validate_human_input.py
│   │   ├── demo_07_stream_interrupt.py
│   │   └── demo_08_hitl_api_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langgraph_hitl.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lg35_01_basic_interrupt.py
│   ├── test_lg35_02_approve_reject.py
│   ├── test_lg35_03_edit_payload.py
│   ├── test_lg35_04_get_state_before_resume.py
│   ├── test_lg35_05_ecommerce_refund_hitl.py
│   ├── test_lg35_06_validate_human_input.py
│   ├── test_lg35_07_stream_interrupt.py
│   └── test_lg35_08_hitl_service.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 35 章。

这一章我们讲 LangGraph Human-in-the-loop。

前面我们已经能写一个电商客服 Agent。

它可以：

```plain
识别用户意图
提取订单号
查询订单
检索退款规则
生成最终回答
```

但是如果用户说：

```plain
帮我把订单 10002 直接退款。
```

这个时候，Agent 不能直接执行退款。

因为退款是高风险动作。

它涉及钱。

涉及订单状态。

涉及用户权益。

涉及公司业务规则。

所以正确流程应该是：

```plain
Agent 分析退款请求
 ↓
查询订单
 ↓
生成退款建议
 ↓
暂停
 ↓
等待人工审核
 ↓
人工同意 / 拒绝 / 修改参数
 ↓
继续执行
```

这个暂停和恢复的能力，就是 Human-in-the-loop。

---

# 六、02｜Human-in-the-loop 一句话解释
## 【实操】
```plain
Human-in-the-loop
=
Agent 执行到关键动作时暂停，
让人审核后再继续。
```

例如：

```plain
退款申请
 ↓
需要人工确认
 ↓
interrupt 暂停
 ↓
人工 approve / reject / edit
 ↓
Command(resume=...) 恢复
 ↓
继续执行后续节点
```

---

## 【重点内容】
大家不要把 Human-in-the-loop 理解成简单弹窗。

它本质上是一个状态机问题。

图要知道：

```plain
为什么暂停
暂停在哪个节点
需要人确认什么
确认通过后做什么
拒绝后做什么
修改后怎么继续
```

所以它必须依赖上一章讲的 Persistence。

没有 checkpoint，就没有稳定的暂停和恢复。

LangGraph 文档也说明，interrupt 触发时会通过持久化层保存 graph state，并等待外部输入，直到客户端用相同 thread 恢复执行。

---

# 七、03｜什么时候必须 HITL
下面这些场景建议必须 Human-in-the-loop：

```plain
1. 涉及钱：退款、扣款、打款、报价
2. 涉及数据删除：删除用户、删除订单、删除文件
3. 涉及外部发送：发邮件、发短信、发通知
4. 涉及权限变更：开权限、改角色、重置密码
5. 涉及法律合同：生成并发送合同
6. 涉及高风险 SQL：update / delete / drop
7. 涉及不可逆操作：取消订单、关闭账号
8. 涉及用户隐私：查看敏感资料
```

---

## 【重点内容】
企业 Agent 不是越自动越好。

能自动回答是一回事。

能自动执行又是另一回事。

尤其是高风险动作，不能只靠 Prompt 写一句：

```plain
请谨慎操作
```

这不够。

必须在程序层面暂停。

让人确认以后，再继续。

这就是 Human-in-the-loop 的价值。

---

# 八、04｜interrupt 和 Command 的关系
## 【实操】
```python
decision = interrupt({
    "action": "refund_order",
    "order_id": "10002",
    "amount": 199.0,
})
```

恢复：

```python
app.invoke(
    Command(resume={
        "type": "approve"
    }),
    config=config,
)
```

关系：

```plain
interrupt：
暂停图，向外部抛出待确认信息。

Command(resume=...)：
把人工确认结果传回图，恢复执行。
```

---

## 【重点内容】
这两个 API 是本章核心。

`interrupt()` 写在 Node 里面。

它会暂停图执行。

暂停时会把你传进去的内容返回给外部。

比如：

```plain
我要退款订单 10002
退款金额 199 元
原因是用户申请未发货退款
```

人工审核完之后，用：

```python
Command(resume=...)
```

把审核结果传回来。

比如：

```plain
approve
reject
edit
```

然后图继续执行。

---

# 九、05｜为什么必须有 checkpointer
没有 checkpointer，interrupt 没法稳定恢复。

因为暂停后，需要保存：

```plain
当前 State
当前 thread
当前 checkpoint
当前待恢复位置
interrupt 信息
```

所以图编译时必须：

```python
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

调用时必须：

```python
config = {
    "configurable": {
        "thread_id": "thread_001"
    }
}
```

---

## 【重点内容】
大家要记住一个公式：

```plain
interrupt = checkpointer + thread_id + Command(resume)
```

缺任何一个，HITL 都不完整。

开发环境可以用 InMemorySaver。

生产环境推荐 AsyncPostgresSaver。

---

# 十、06｜创建目录
执行：

```bash
mkdir -p app/langgraph_hitl

touch app/langgraph_hitl/__init__.py
touch app/langgraph_hitl/schemas.py
touch app/langgraph_hitl/graph_factory.py
touch app/langgraph_hitl/service.py
touch app/langgraph_hitl/demo_01_basic_interrupt.py
touch app/langgraph_hitl/demo_02_approve_reject.py
touch app/langgraph_hitl/demo_03_edit_payload.py
touch app/langgraph_hitl/demo_04_get_state_before_resume.py
touch app/langgraph_hitl/demo_05_ecommerce_refund_hitl.py
touch app/langgraph_hitl/demo_06_validate_human_input.py
touch app/langgraph_hitl/demo_07_stream_interrupt.py
touch app/langgraph_hitl/demo_08_hitl_api_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langgraph_hitl

New-Item app\langgraph_hitl\__init__.py
New-Item app\langgraph_hitl\schemas.py
New-Item app\langgraph_hitl\graph_factory.py
New-Item app\langgraph_hitl\service.py
New-Item app\langgraph_hitl\demo_01_basic_interrupt.py
New-Item app\langgraph_hitl\demo_02_approve_reject.py
New-Item app\langgraph_hitl\demo_03_edit_payload.py
New-Item app\langgraph_hitl\demo_04_get_state_before_resume.py
New-Item app\langgraph_hitl\demo_05_ecommerce_refund_hitl.py
New-Item app\langgraph_hitl\demo_06_validate_human_input.py
New-Item app\langgraph_hitl\demo_07_stream_interrupt.py
New-Item app\langgraph_hitl\demo_08_hitl_api_adapter.py
```

---

# 十一、07｜准备公共 State
打开：

```plain
app/langgraph_hitl/schemas.py
```

写入：

```python
import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class RefundOrderInfo(TypedDict, total=False):
    order_id: str
    status: str
    status_text: str
    amount: float
    currency: str


class HumanDecision(TypedDict, total=False):
    type: Literal["approve", "reject", "edit"]
    reviewer_id: str
    reason: str | None
    edited_payload: dict | None


class HITLState(TypedDict):
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
    order_info: RefundOrderInfo | None

    refund_amount: float | None
    refund_reason: str | None

    risk_level: Literal["low", "medium", "high"]
    need_human_confirm: bool
    pending_action: str | None
    pending_payload: dict | None

    human_decision: HumanDecision | None
    action_result: dict | None

    final_answer: str
    is_finished: bool

    logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]
```

继续增加初始化函数：

```python
from langchain_core.messages import HumanMessage

from app.langgraph_hitl.schemas import HITLState


def create_initial_state(
    user_question: str,
) -> HITLState:
    return {
        "user_question": user_question,
        "messages": [
            HumanMessage(content=user_question)
        ],

        "intent": "unknown",

        "order_id": None,
        "order_info": None,

        "refund_amount": None,
        "refund_reason": None,

        "risk_level": "low",
        "need_human_confirm": False,
        "pending_action": None,
        "pending_payload": None,

        "human_decision": None,
        "action_result": None,

        "final_answer": "",
        "is_finished": False,

        "logs": [],
        "errors": [],
    }
```

---

## 【重点内容】
这个 State 专门为 Human-in-the-loop 设计。

重点字段是：

```plain
need_human_confirm
pending_action
pending_payload
human_decision
action_result
```

它们分别代表：

```plain
是否需要人工确认
当前等待确认的动作是什么
待确认动作的参数是什么
人工做了什么决定
最终动作执行结果是什么
```

这几个字段非常关键。

---

# 十二、08｜示例一：最小 interrupt
打开：

```plain
app/langgraph_hitl/demo_01_basic_interrupt.py
```

写入：

```python
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class BasicHITLState(TypedDict):
    user_question: str
    final_answer: str


def human_review_node(state: BasicHITLState) -> dict:
    decision = interrupt({
        "type": "human_review",
        "question": state["user_question"],
        "message": "请人工审核这个回答是否可以继续。",
    })

    return {
        "final_answer": f"人工审核结果：{decision}"
    }


def build_graph():
    graph = StateGraph(BasicHITLState)

    graph.add_node("human_review", human_review_node)

    graph.add_edge(START, "human_review")
    graph.add_edge("human_review", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg35_basic_interrupt"
        }
    }

    print("第一次执行，会在 interrupt 暂停：")
    first = app.invoke(
        {
            "user_question": "请帮我执行一个需要人工审核的动作。",
            "final_answer": "",
        },
        config=config,
    )

    print(first)

    print("=" * 80)
    print("第二次执行，用 Command(resume=...) 恢复：")

    second = app.invoke(
        Command(resume="approve"),
        config=config,
    )

    print(second)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_01_basic_interrupt.py
```

写入：

```python
from app.langgraph_hitl.demo_01_basic_interrupt import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg35_01_basic_interrupt.py
```

---

## 【重点内容】
这是最小 interrupt 示例。

第一次执行时，图不会直接结束。

它会返回类似：

```plain
__interrupt__
```

里面包含我们传给 interrupt 的信息。

第二次执行时，我们传：

```python
Command(resume="approve")
```

这时 `interrupt()` 会返回 `"approve"`。

然后节点继续执行后面的代码。

---

# 十三、09｜interrupt 节点会重新执行
这里有一个非常重要的点：

```plain
恢复后，包含 interrupt 的节点会从头重新执行。
```

比如：

```python
def node(state):
    print("before interrupt")

    decision = interrupt(...)

    print("after interrupt")
```

第一次执行：

```plain
会执行 before interrupt
然后暂停
```

恢复后：

```plain
会重新执行 before interrupt
interrupt 返回 resume 值
再执行 after interrupt
```

---

## 【重点内容】
这个点非常重要。

因为如果你在 interrupt 之前做了真实副作用，比如：

```plain
已经退款
已经发短信
已经删数据
已经发邮件
```

恢复时节点重新执行，就可能重复执行。

所以正式项目里要遵守：

```plain
interrupt 之前只做准备和展示
真正副作用放在 interrupt 之后
或者保证 interrupt 前的副作用幂等
```

官方 interrupts 文档也把这条列为规则：不要在 interrupt 前执行非幂等副作用，或者必须让这些副作用具备幂等性。

---

# 十四、10｜示例二：approve / reject
打开：

```plain
app/langgraph_hitl/demo_02_approve_reject.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ApproveRejectState(TypedDict):
    action_name: str
    action_payload: dict
    human_decision: dict | None
    final_answer: str


def review_action_node(state: ApproveRejectState) -> dict:
    decision = interrupt({
        "type": "review_action",
        "action_name": state["action_name"],
        "action_payload": state["action_payload"],
        "options": ["approve", "reject"],
    })

    return {
        "human_decision": decision
    }


def route_after_review(
    state: ApproveRejectState,
) -> Literal["approved", "rejected"]:
    decision = state["human_decision"] or {}

    if decision.get("type") == "approve":
        return "approved"

    return "rejected"


def execute_action_node(state: ApproveRejectState) -> dict:
    return {
        "final_answer": (
            f"人工已审批通过，开始执行动作：{state['action_name']}，"
            f"参数：{state['action_payload']}"
        )
    }


def reject_action_node(state: ApproveRejectState) -> dict:
    decision = state["human_decision"] or {}

    return {
        "final_answer": (
            "人工已拒绝执行该动作。"
            f"原因：{decision.get('reason', '未填写')}"
        )
    }


def build_graph():
    graph = StateGraph(ApproveRejectState)

    graph.add_node("review_action", review_action_node)
    graph.add_node("execute_action", execute_action_node)
    graph.add_node("reject_action", reject_action_node)

    graph.add_edge(START, "review_action")

    graph.add_conditional_edges(
        "review_action",
        route_after_review,
        {
            "approved": "execute_action",
            "rejected": "reject_action",
        },
    )

    graph.add_edge("execute_action", END)
    graph.add_edge("reject_action", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg35_approve_reject"
        }
    }

    first = app.invoke(
        {
            "action_name": "refund_order",
            "action_payload": {
                "order_id": "10002",
                "amount": 199.0,
            },
            "human_decision": None,
            "final_answer": "",
        },
        config=config,
    )

    print("first:")
    print(first)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "订单未发货，可以退款",
        }),
        config=config,
    )

    print("second:")
    print(second)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_02_approve_reject.py
```

写入：

```python
from app.langgraph_hitl.demo_02_approve_reject import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子支持 approve 和 reject。

第一次图在 review_action 暂停。

人工审核后传：

```python
Command(resume={
    "type": "approve"
})
```

如果 approve，就进入 execute_action。

如果 reject，就进入 reject_action。

这就是审批分支。

---

# 十五、11｜示例三：人工修改参数 edit
有时候人工不是简单同意或拒绝。

而是要修改参数。

比如模型建议退款 199 元。

人工审核后认为只能退 99 元。

这就需要 edit。

打开：

```plain
app/langgraph_hitl/demo_03_edit_payload.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class EditPayloadState(TypedDict):
    pending_action: str
    pending_payload: dict
    human_decision: dict | None
    final_payload: dict | None
    final_answer: str


def review_payload_node(state: EditPayloadState) -> dict:
    decision = interrupt({
        "type": "review_payload",
        "pending_action": state["pending_action"],
        "pending_payload": state["pending_payload"],
        "options": ["approve", "reject", "edit"],
        "message": "请审核动作参数，可以同意、拒绝或修改。",
    })

    return {
        "human_decision": decision
    }


def route_after_review(
    state: EditPayloadState,
) -> Literal["approved", "edited", "rejected"]:
    decision = state["human_decision"] or {}
    decision_type = decision.get("type")

    if decision_type == "approve":
        return "approved"

    if decision_type == "edit":
        return "edited"

    return "rejected"


def use_original_payload_node(state: EditPayloadState) -> dict:
    return {
        "final_payload": state["pending_payload"],
        "final_answer": f"使用原始参数执行：{state['pending_payload']}",
    }


def use_edited_payload_node(state: EditPayloadState) -> dict:
    decision = state["human_decision"] or {}
    edited_payload = decision.get("edited_payload") or {}

    return {
        "final_payload": edited_payload,
        "final_answer": f"使用人工修改后的参数执行：{edited_payload}",
    }


def reject_node(state: EditPayloadState) -> dict:
    decision = state["human_decision"] or {}

    return {
        "final_payload": None,
        "final_answer": f"人工拒绝执行。原因：{decision.get('reason', '未填写')}",
    }


def build_graph():
    graph = StateGraph(EditPayloadState)

    graph.add_node("review_payload", review_payload_node)
    graph.add_node("use_original_payload", use_original_payload_node)
    graph.add_node("use_edited_payload", use_edited_payload_node)
    graph.add_node("reject", reject_node)

    graph.add_edge(START, "review_payload")

    graph.add_conditional_edges(
        "review_payload",
        route_after_review,
        {
            "approved": "use_original_payload",
            "edited": "use_edited_payload",
            "rejected": "reject",
        },
    )

    graph.add_edge("use_original_payload", END)
    graph.add_edge("use_edited_payload", END)
    graph.add_edge("reject", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg35_edit_payload"
        }
    }

    first = app.invoke(
        {
            "pending_action": "refund_order",
            "pending_payload": {
                "order_id": "10002",
                "amount": 199.0,
                "reason": "用户申请未发货退款",
            },
            "human_decision": None,
            "final_payload": None,
            "final_answer": "",
        },
        config=config,
    )

    print("first:")
    print(first)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "edit",
            "reviewer_id": "admin_001",
            "reason": "优惠券不可退，只退实付金额",
            "edited_payload": {
                "order_id": "10002",
                "amount": 149.0,
                "reason": "人工修改为仅退实付金额",
            },
        }),
        config=config,
    )

    print("second:")
    print(second)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_03_edit_payload.py
```

写入：

```python
from app.langgraph_hitl.demo_03_edit_payload import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子很接近真实后台。

人工审核时不一定只有通过和拒绝。

还可能修改参数。

比如：

```plain
模型建议退款 199
人工改成退款 149
```

这种场景非常常见。

所以 Human-in-the-loop 最少要支持三种决策：

```plain
approve
reject
edit
```

---

# 十六、12｜示例四：恢复前查看 State
人工审批前，后台通常要展示当前 State。

比如：

```plain
用户问题
订单号
订单状态
退款金额
风险等级
待执行动作
```

打开：

```plain
app/langgraph_hitl/demo_04_get_state_before_resume.py
```

写入：

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.langgraph_hitl.demo_03_edit_payload import build_graph


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg35_get_state_before_resume"
        }
    }

    first = app.invoke(
        {
            "pending_action": "refund_order",
            "pending_payload": {
                "order_id": "10002",
                "amount": 199.0,
                "reason": "用户申请未发货退款",
            },
            "human_decision": None,
            "final_payload": None,
            "final_answer": "",
        },
        config=config,
    )

    print("first interrupt:")
    print(first)

    print("=" * 80)
    print("人工审核前查看当前 State:")

    snapshot = app.get_state(config)

    print(snapshot.values)

    print("=" * 80)
    print("人工审核通过后恢复:")

    second = app.invoke(
        Command(resume={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "审核通过",
        }),
        config=config,
    )

    print(second)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_04_get_state_before_resume.py
```

写入：

```python
from app.langgraph_hitl.demo_04_get_state_before_resume import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
真实后台审批时，不会只看 interrupt payload。

还会看当前 State。

比如：

```plain
这个用户问了什么
Agent 判断是什么
订单状态是什么
风险等级是什么
待执行动作是什么
```

这些信息可以通过：

```python
app.get_state(config)
```

查看。

---

# 十七、13｜电商退款 HITL 流程设计
我们现在设计一个真实一点的退款流程：

```plain
用户申请退款
 ↓
识别 intent=refund
 ↓
提取 order_id
 ↓
查询订单
 ↓
计算退款金额
 ↓
风险评估
 ↓
如果低风险，直接生成建议
 ↓
如果高风险，interrupt 等待人工确认
 ↓
人工 approve / reject / edit
 ↓
执行退款动作
 ↓
生成最终回答
```

---

## 【实操】
```plain
START
 ↓
classify_intent
 ↓
extract_order_id
 ↓
query_order
 ↓
prepare_refund
 ↓
assess_risk
 ↓
需要人工确认？
 ├── 是 -> human_review -> execute_refund / reject_refund
 └── 否 -> execute_refund
 ↓
generate_answer
 ↓
END
```

---

# 十八、14｜准备电商退款 Graph
打开：

```plain
app/langgraph_hitl/graph_factory.py
```

写入：

```python
from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.langgraph_hitl.schemas import HITLState


def classify_intent_node(state: HITLState) -> dict:
    question = state["user_question"]

    if "退款" in question or "退货" in question:
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


def route_by_intent(
    state: HITLState,
) -> Literal["refund", "general"]:
    if state["intent"] == "refund":
        return "refund"

    return "general"


def general_answer_node(state: HITLState) -> dict:
    answer = "这是普通问题，可以走普通 ChatModel。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["general_answer：普通回答完成"],
    }


def extract_order_id_node(state: HITLState) -> dict:
    question = state["user_question"]

    if "10001" in question:
        order_id = "10001"
    elif "10002" in question:
        order_id = "10002"
    elif "10003" in question:
        order_id = "10003"
    else:
        order_id = None

    return {
        "order_id": order_id,
        "logs": [f"extract_order_id：order_id={order_id}"],
    }


def route_after_extract_order_id(
    state: HITLState,
) -> Literal["ask_order_id", "query_order"]:
    if not state["order_id"]:
        return "ask_order_id"

    return "query_order"


def ask_order_id_node(state: HITLState) -> dict:
    answer = "请您提供订单号，我才能继续处理退款申请。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["ask_order_id：缺少订单号"],
    }


def query_order_node(state: HITLState) -> dict:
    order_id = state["order_id"]

    if order_id == "10001":
        order_info = {
            "order_id": "10001",
            "status": "shipped",
            "status_text": "已发货",
            "amount": 399.0,
            "currency": "CNY",
        }
    elif order_id == "10002":
        order_info = {
            "order_id": "10002",
            "status": "paid",
            "status_text": "已付款，待发货",
            "amount": 199.0,
            "currency": "CNY",
        }
    elif order_id == "10003":
        order_info = {
            "order_id": "10003",
            "status": "paid",
            "status_text": "已付款，待发货",
            "amount": 1299.0,
            "currency": "CNY",
        }
    else:
        order_info = {
            "order_id": order_id or "",
            "status": "not_found",
            "status_text": "未查询到订单",
            "amount": 0.0,
            "currency": "CNY",
        }

    return {
        "order_info": order_info,
        "logs": [f"query_order：{order_info['status_text']}"],
    }


def route_after_query_order(
    state: HITLState,
) -> Literal["order_not_found", "prepare_refund"]:
    order_info = state["order_info"]

    if not order_info or order_info["status"] == "not_found":
        return "order_not_found"

    return "prepare_refund"


def order_not_found_node(state: HITLState) -> dict:
    answer = "没有查询到该订单，请您检查订单号是否正确。"

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["order_not_found：订单不存在"],
    }


def prepare_refund_node(state: HITLState) -> dict:
    order_info = state["order_info"]

    refund_amount = float(order_info["amount"])

    if order_info["status"] == "paid":
        refund_reason = "订单未发货，用户申请取消订单并退款。"
    elif order_info["status"] == "shipped":
        refund_reason = "订单已发货，需要人工确认是否允许直接退款。"
    else:
        refund_reason = "订单状态异常，需要人工确认。"

    pending_payload = {
        "order_id": order_info["order_id"],
        "amount": refund_amount,
        "currency": order_info["currency"],
        "reason": refund_reason,
    }

    return {
        "refund_amount": refund_amount,
        "refund_reason": refund_reason,
        "pending_action": "refund_order",
        "pending_payload": pending_payload,
        "logs": [f"prepare_refund：pending_payload={pending_payload}"],
    }


def assess_risk_node(state: HITLState) -> dict:
    order_info = state["order_info"]
    refund_amount = state["refund_amount"] or 0

    if order_info["status"] != "paid":
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "logs": ["assess_risk：非待发货订单退款，高风险"],
        }

    if refund_amount >= 500:
        return {
            "risk_level": "high",
            "need_human_confirm": True,
            "logs": ["assess_risk：大额退款，高风险"],
        }

    return {
        "risk_level": "low",
        "need_human_confirm": False,
        "logs": ["assess_risk：低风险，可自动退款"],
    }


def route_after_risk(
    state: HITLState,
) -> Literal["human_review", "execute_refund"]:
    if state["need_human_confirm"]:
        return "human_review"

    return "execute_refund"


def human_review_node(state: HITLState) -> dict:
    decision = interrupt({
        "type": "refund_review",
        "risk_level": state["risk_level"],
        "pending_action": state["pending_action"],
        "pending_payload": state["pending_payload"],
        "order_info": state["order_info"],
        "options": ["approve", "reject", "edit"],
        "message": "该退款请求需要人工审核，请确认是否继续执行。",
    })

    return {
        "human_decision": decision,
        "logs": [f"human_review：收到人工决策 {decision}"],
    }


def route_after_human_review(
    state: HITLState,
) -> Literal["execute_refund", "reject_refund", "apply_edit"]:
    decision = state["human_decision"] or {}
    decision_type = decision.get("type")

    if decision_type == "approve":
        return "execute_refund"

    if decision_type == "edit":
        return "apply_edit"

    return "reject_refund"


def apply_edit_node(state: HITLState) -> dict:
    decision = state["human_decision"] or {}
    edited_payload = decision.get("edited_payload") or {}

    return {
        "pending_payload": edited_payload,
        "refund_amount": float(edited_payload.get("amount", 0)),
        "logs": [f"apply_edit：人工修改退款参数 {edited_payload}"],
    }


def execute_refund_node(state: HITLState) -> dict:
    payload = state["pending_payload"] or {}

    # 教学版：这里不调用真实支付或订单系统，只模拟执行。
    # 生产环境：这里才是真正调用退款工具的位置。
    action_result = {
        "success": True,
        "refund_id": f"rf_{payload.get('order_id', 'unknown')}",
        "executed_payload": payload,
    }

    return {
        "action_result": action_result,
        "logs": [f"execute_refund：退款执行成功 {action_result}"],
    }


def reject_refund_node(state: HITLState) -> dict:
    decision = state["human_decision"] or {}

    action_result = {
        "success": False,
        "reason": decision.get("reason", "人工拒绝退款"),
    }

    return {
        "action_result": action_result,
        "logs": [f"reject_refund：人工拒绝 {action_result}"],
    }


def generate_answer_node(state: HITLState) -> dict:
    action_result = state["action_result"] or {}

    if action_result.get("success"):
        payload = action_result.get("executed_payload") or {}
        answer = (
            f"退款已处理成功。订单号：{payload.get('order_id')}，"
            f"退款金额：{payload.get('amount')} {payload.get('currency')}。"
        )
    else:
        answer = (
            "本次退款暂未执行。"
            f"原因：{action_result.get('reason', '未说明')}。"
        )

    return {
        "final_answer": answer,
        "is_finished": True,
        "messages": [
            AIMessage(content=answer)
        ],
        "logs": ["generate_answer：最终回答完成"],
    }


def build_hitl_refund_graph(
    checkpointer=None,
):
    graph = StateGraph(HITLState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("general_answer", general_answer_node)
    graph.add_node("extract_order_id", extract_order_id_node)
    graph.add_node("ask_order_id", ask_order_id_node)
    graph.add_node("query_order", query_order_node)
    graph.add_node("order_not_found", order_not_found_node)
    graph.add_node("prepare_refund", prepare_refund_node)
    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("apply_edit", apply_edit_node)
    graph.add_node("execute_refund", execute_refund_node)
    graph.add_node("reject_refund", reject_refund_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "refund": "extract_order_id",
            "general": "general_answer",
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
            "prepare_refund": "prepare_refund",
        },
    )

    graph.add_edge("prepare_refund", "assess_risk")

    graph.add_conditional_edges(
        "assess_risk",
        route_after_risk,
        {
            "human_review": "human_review",
            "execute_refund": "execute_refund",
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
    graph.add_edge("execute_refund", "generate_answer")
    graph.add_edge("reject_refund", "generate_answer")

    graph.add_edge("general_answer", END)
    graph.add_edge("ask_order_id", END)
    graph.add_edge("order_not_found", END)
    graph.add_edge("generate_answer", END)

    return graph.compile(checkpointer=checkpointer)


def build_memory_hitl_graph():
    checkpointer = InMemorySaver()

    return build_hitl_refund_graph(
        checkpointer=checkpointer,
    )
```

---

## 【重点内容】
这个 Graph 是本章核心项目。

它有三个关键点。

第一，低风险退款不需要人工确认。

比如订单 10002，金额 199，状态是待发货，可以自动退款。

第二，高风险退款需要人工确认。

比如订单 10003，金额 1299，属于大额退款。

第三，已发货订单退款需要人工确认。

因为它不是普通未发货取消订单。

所以这里会进入：

```plain
human_review_node
```

然后触发：

```python
interrupt(...)
```

---

# 十九、15｜示例五：电商退款 HITL
打开：

```plain
app/langgraph_hitl/demo_05_ecommerce_refund_hitl.py
```

写入：

```python
from langgraph.types import Command

from app.langgraph_hitl.graph_factory import build_memory_hitl_graph
from app.langgraph_hitl.schemas import create_initial_state


def run_low_risk_refund(app):
    config = {
        "configurable": {
            "thread_id": "thread_low_risk_refund"
        }
    }

    result = app.invoke(
        create_initial_state("我的订单 10002 申请退款。"),
        config=config,
    )

    print("低风险退款：")
    print("final_answer:", result["final_answer"])
    print("need_human_confirm:", result["need_human_confirm"])
    print("logs:")
    for log in result["logs"]:
        print("-", log)

    print("=" * 120)


def run_high_risk_refund_with_approve(app):
    config = {
        "configurable": {
            "thread_id": "thread_high_risk_refund_approve"
        }
    }

    first = app.invoke(
        create_initial_state("我的订单 10003 申请退款。"),
        config=config,
    )

    print("高风险退款第一次执行，应该 interrupt：")
    print(first)

    print("=" * 80)

    snapshot = app.get_state(config)
    print("当前 State:")
    print(snapshot.values)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "大额退款人工审核通过",
        }),
        config=config,
    )

    print("人工 approve 后恢复：")
    print("final_answer:", second["final_answer"])
    print("human_decision:", second["human_decision"])
    print("action_result:", second["action_result"])
    print("logs:")
    for log in second["logs"]:
        print("-", log)

    print("=" * 120)


def run_high_risk_refund_with_reject(app):
    config = {
        "configurable": {
            "thread_id": "thread_high_risk_refund_reject"
        }
    }

    first = app.invoke(
        create_initial_state("我的订单 10003 申请退款。"),
        config=config,
    )

    print("高风险退款第一次执行，应该 interrupt：")
    print(first)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "reject",
            "reviewer_id": "admin_002",
            "reason": "金额较大，需要进一步核实用户身份",
        }),
        config=config,
    )

    print("人工 reject 后恢复：")
    print("final_answer:", second["final_answer"])
    print("human_decision:", second["human_decision"])
    print("action_result:", second["action_result"])

    print("=" * 120)


def run_high_risk_refund_with_edit(app):
    config = {
        "configurable": {
            "thread_id": "thread_high_risk_refund_edit"
        }
    }

    first = app.invoke(
        create_initial_state("我的订单 10003 申请退款。"),
        config=config,
    )

    print("高风险退款第一次执行，应该 interrupt：")
    print(first)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "edit",
            "reviewer_id": "admin_003",
            "reason": "部分优惠券不可退，人工调整退款金额",
            "edited_payload": {
                "order_id": "10003",
                "amount": 1099.0,
                "currency": "CNY",
                "reason": "人工调整后退款金额",
            },
        }),
        config=config,
    )

    print("人工 edit 后恢复：")
    print("final_answer:", second["final_answer"])
    print("pending_payload:", second["pending_payload"])
    print("action_result:", second["action_result"])

    print("=" * 120)


def main():
    app = build_memory_hitl_graph()

    run_low_risk_refund(app)
    run_high_risk_refund_with_approve(app)
    run_high_risk_refund_with_reject(app)
    run_high_risk_refund_with_edit(app)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_05_ecommerce_refund_hitl.py
```

写入：

```python
from app.langgraph_hitl.demo_05_ecommerce_refund_hitl import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg35_05_ecommerce_refund_hitl.py
```

---

## 【重点内容】
这个脚本测试四种情况。

第一种，低风险退款。

比如订单 10002，金额 199，未发货。

直接执行。

第二种，高风险 approve。

比如订单 10003，金额 1299，需要人工确认。

人工同意后继续执行退款。

第三种，高风险 reject。

人工拒绝后，不执行退款，返回拒绝原因。

第四种，高风险 edit。

人工修改退款金额后，再执行退款。

这就是一个完整的 Human-in-the-loop 流程。

---

# 二十、16｜示例六：校验人工输入
真实项目不能直接相信人工传回来的 resume。

要校验：

```plain
type 是否是 approve / reject / edit
reviewer_id 是否存在
edit 时 edited_payload 是否存在
amount 是否合法
```

打开：

```plain
app/langgraph_hitl/demo_06_validate_human_input.py
```

写入：

```python
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class ValidateState(TypedDict):
    pending_payload: dict
    human_decision: dict | None
    final_answer: str
    errors: list[str]


def validate_decision(decision: dict) -> list[str]:
    errors = []

    decision_type = decision.get("type")

    if decision_type not in ["approve", "reject", "edit"]:
        errors.append("type 必须是 approve / reject / edit")

    if not decision.get("reviewer_id"):
        errors.append("reviewer_id 不能为空")

    if decision_type == "edit":
        edited_payload = decision.get("edited_payload")

        if not isinstance(edited_payload, dict):
            errors.append("edit 时 edited_payload 必须是 dict")
        else:
            amount = edited_payload.get("amount")

            if not isinstance(amount, int | float) or amount <= 0:
                errors.append("edited_payload.amount 必须是大于 0 的数字")

    return errors


def review_node(state: ValidateState) -> dict:
    decision = interrupt({
        "type": "validate_review",
        "pending_payload": state["pending_payload"],
        "options": ["approve", "reject", "edit"],
    })

    errors = validate_decision(decision)

    if errors:
        return {
            "human_decision": decision,
            "errors": errors,
            "final_answer": "人工审核输入不合法，需要重新提交。",
        }

    return {
        "human_decision": decision,
        "errors": [],
    }


def route_after_review(
    state: ValidateState,
) -> Literal["invalid", "valid"]:
    if state["errors"]:
        return "invalid"

    return "valid"


def invalid_node(state: ValidateState) -> dict:
    return {
        "final_answer": "审核失败：" + "；".join(state["errors"])
    }


def valid_node(state: ValidateState) -> dict:
    return {
        "final_answer": f"审核通过，决策为：{state['human_decision']}"
    }


def build_graph():
    graph = StateGraph(ValidateState)

    graph.add_node("review", review_node)
    graph.add_node("invalid", invalid_node)
    graph.add_node("valid", valid_node)

    graph.add_edge(START, "review")

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "invalid": "invalid",
            "valid": "valid",
        },
    )

    graph.add_edge("invalid", END)
    graph.add_edge("valid", END)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


def main():
    app = build_graph()

    config = {
        "configurable": {
            "thread_id": "thread_validate_human_input"
        }
    }

    first = app.invoke(
        {
            "pending_payload": {
                "order_id": "10003",
                "amount": 1299.0,
            },
            "human_decision": None,
            "final_answer": "",
            "errors": [],
        },
        config=config,
    )

    print("first:")
    print(first)

    print("=" * 80)

    second = app.invoke(
        Command(resume={
            "type": "edit",
            "reviewer_id": "admin_001",
            "edited_payload": {
                "order_id": "10003",
                "amount": 1099.0,
            },
        }),
        config=config,
    )

    print("second:")
    print(second)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_06_validate_human_input.py
```

写入：

```python
from app.langgraph_hitl.demo_06_validate_human_input import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
人工输入也要校验。

不要以为是后台操作就完全可信。

尤其是：

```plain
金额
订单号
执行动作
审批人
审批原因
```

这些都要校验。

否则后台误操作也会造成事故。

---

# 二十一、17｜示例七：stream 观察 interrupt
打开：

```plain
app/langgraph_hitl/demo_07_stream_interrupt.py
```

写入：

```python
from langgraph.types import Command

from app.langgraph_hitl.graph_factory import build_memory_hitl_graph
from app.langgraph_hitl.schemas import create_initial_state


def main():
    app = build_memory_hitl_graph()

    config = {
        "configurable": {
            "thread_id": "thread_lg35_stream_interrupt"
        }
    }

    print("第一次 stream，观察 interrupt:")
    print("=" * 80)

    for chunk in app.stream(
        create_initial_state("我的订单 10003 申请退款。"),
        config=config,
        stream_mode="updates",
    ):
        print(chunk)

    print("=" * 80)
    print("恢复执行:")
    print("=" * 80)

    for chunk in app.stream(
        Command(resume={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "人工审核通过",
        }),
        config=config,
        stream_mode="updates",
    ):
        print(chunk)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lg35_07_stream_interrupt.py
```

写入：

```python
from app.langgraph_hitl.demo_07_stream_interrupt import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
stream 很适合前端展示 HITL 过程。

第一次 stream 可以看到：

```plain
执行到哪个节点
哪里触发了 interrupt
待审批信息是什么
```

恢复后继续 stream，可以看到：

```plain
human_review 收到决策
execute_refund 执行
generate_answer 生成回答
```

LangGraph 的事件流文档也说明，图在暂停时可以通过 interrupt 信息让客户端展示待处理内容，并在后续用 Command 恢复执行。

---

# 二十二、18｜封装 HITL Service
打开：

```plain
app/langgraph_hitl/service.py
```

写入：

```python
from langgraph.types import Command

from app.langgraph_hitl.graph_factory import build_memory_hitl_graph
from app.langgraph_hitl.schemas import create_initial_state


class LangGraphHITLService:
    def __init__(self):
        # 教学版用内存 checkpointer。
        # 生产环境替换成 AsyncPostgresSaver。
        self.graph = build_memory_hitl_graph()

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

    def start(
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

        result = self.graph.invoke(
            create_initial_state(user_question),
            config=config,
        )

        return {
            "thread_id": thread_id,
            "result": result,
        }

    def resume(
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

        result = self.graph.invoke(
            Command(resume=decision),
            config=config,
        )

        return {
            "thread_id": thread_id,
            "result": result,
        }

    def get_state(
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


langgraph_hitl_service = LangGraphHITLService()
```

创建测试脚本：

```plain
scripts/test_lg35_08_hitl_service.py
```

写入：

```python
from app.langgraph_hitl.service import langgraph_hitl_service


def main():
    tenant_id = "tenant_001"
    user_id = "u_10001"
    conversation_id = "conv_hitl_refund_001"

    first = langgraph_hitl_service.start(
        user_question="我的订单 10003 申请退款。",
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("first:")
    print(first)

    print("=" * 80)

    state = langgraph_hitl_service.get_state(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    print("state before resume:")
    print(state["values"])

    print("=" * 80)

    second = langgraph_hitl_service.resume(
        tenant_id=tenant_id,
        user_id=user_id,
        conversation_id=conversation_id,
        decision={
            "type": "approve",
            "reviewer_id": "admin_001",
            "reason": "审核通过",
        },
    )

    print("second:")
    print(second)


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lg35_08_hitl_service.py
```

---

# 二十三、19｜创建 HITL API
创建：

```plain
app/api/v1/langgraph_hitl.py
```

写入：

```python
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langgraph_hitl.service import langgraph_hitl_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class HITLStartRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")


class HITLDecisionRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")

    type: Literal["approve", "reject", "edit"]
    reason: str | None = None
    edited_payload: dict | None = None


@router.post(
    "/langgraph/hitl/refund/start",
    response_model=ApiResponse[dict],
)
async def start_hitl_refund(
    request: HITLStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langgraph_hitl_service.start(
        user_question=request.question,
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
    )

    return ApiResponse[dict](
        data=result
    )


@router.get(
    "/langgraph/hitl/refund/state/{conversation_id}",
    response_model=ApiResponse[dict],
)
async def get_hitl_state(
    conversation_id: str,
    tenant_id: str = "tenant_001",
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langgraph_hitl_service.get_state(
        tenant_id=tenant_id,
        user_id=current_user.user_id,
        conversation_id=conversation_id,
    )

    return ApiResponse[dict](
        data=result
    )


@router.post(
    "/langgraph/hitl/refund/resume",
    response_model=ApiResponse[dict],
)
async def resume_hitl_refund(
    request: HITLDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    decision = {
        "type": request.type,
        "reviewer_id": current_user.user_id,
        "reason": request.reason,
    }

    if request.type == "edit":
        decision["edited_payload"] = request.edited_payload

    result = langgraph_hitl_service.resume(
        tenant_id=request.tenant_id,
        user_id=current_user.user_id,
        conversation_id=request.conversation_id,
        decision=decision,
    )

    return ApiResponse[dict](
        data=result
    )
```

---

# 二十四、20｜注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langgraph_hitl import router as langgraph_hitl_router
```

注册：

```python
api_router.include_router(
    langgraph_hitl_router,
    tags=["LangGraph HITL"],
)
```

---

# 二十五、21｜测试 HITL API
启动：

```bash
uv run uvicorn app.main:app --reload
```

第一步：发起高风险退款

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/hitl/refund/start" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "conversation_id": "conv_hitl_refund_001",
    "question": "我的订单 10003 申请退款。"
  }'
```

预期会返回 interrupt 信息。

第二步：查看当前 State

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/langgraph/hitl/refund/state/conv_hitl_refund_001" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

第三步：人工审批通过

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/hitl/refund/resume" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: admin_001" \
  -H "x-username: admin" \
  -d '{
    "conversation_id": "conv_hitl_refund_001",
    "type": "approve",
    "reason": "人工审核通过"
  }'
```

第四步：人工修改参数

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langgraph/hitl/refund/resume" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: admin_001" \
  -H "x-username: admin" \
  -d '{
    "conversation_id": "conv_hitl_refund_002",
    "type": "edit",
    "reason": "优惠券不可退，只退实付金额",
    "edited_payload": {
      "order_id": "10003",
      "amount": 1099,
      "currency": "CNY",
      "reason": "人工修改后退款金额"
    }
  }'
```

---

# 二十六、22｜前端如何展示 HITL
前端可以分三块展示。

## 第一块：AI 处理进度
```plain
正在识别意图
正在查询订单
正在评估风险
需要人工确认
```

## 第二块：待审核卡片
```plain
动作：refund_order
订单号：10003
退款金额：1299 CNY
风险等级：high
原因：大额退款
```

## 第三块：审批按钮
```plain
同意
拒绝
修改参数后同意
```

---

## 【重点内容】
HITL 的前端体验很重要。

不要只显示：

```plain
系统暂停了
```

要让审核人知道：

```plain
为什么暂停
需要审核什么
原始参数是什么
风险点在哪里
确认后会执行什么
```

这样审核人才能做决定。

---

# 二十七、23｜HITL 和权限控制
审批接口必须做权限控制。

比如：

```plain
普通用户可以发起退款
客服主管可以审批 500 以下退款
财务可以审批大额退款
管理员可以修改退款金额
```

伪代码：

```python
if request.type in ["approve", "edit"]:
    if not current_user.has_permission("refund:approve"):
        raise AppException(
            message="无权审批退款",
            status_code=403,
        )
```

---

## 【重点内容】
Human-in-the-loop 不是谁都能点同意。

审批本身也是业务权限。

比如大额退款，普通客服可能没有权限。

这时候要结合：

```plain
用户角色
租户
部门
退款金额
订单状态
审批规则
```

做权限校验。

---

# 二十八、24｜HITL 和审计日志
每一次人工决策都要记录：

```plain
thread_id
conversation_id
reviewer_id
decision_type
reason
original_payload
edited_payload
created_at
ip
user_agent
```

推荐业务表：

```sql
CREATE TABLE agent_human_reviews (
    id BIGSERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL,
    reviewer_id VARCHAR(255) NOT NULL,
    decision_type VARCHAR(32) NOT NULL,
    reason TEXT,
    original_payload JSONB,
    edited_payload JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 【重点内容】
HITL 一定要有审计。

因为人工点了同意，就可能触发真实业务操作。

后面出了问题，要知道：

```plain
谁审批的
什么时候审批的
审批了什么
有没有改参数
原始参数是什么
修改后参数是什么
```

Checkpoint 保存的是图状态。

审计日志保存的是业务责任链。

两者都要有。

---

# 二十九、25｜interrupt 的安全规则
必须记住这些规则：

```plain
1. interrupt 必须配合 checkpointer
2. 恢复时必须使用同一个 thread_id
3. 不要把 interrupt 包在 try/except 里吞掉
4. 不要在同一个节点里随意调整多个 interrupt 的顺序
5. interrupt 返回值要简单、可序列化
6. interrupt 前不要执行非幂等副作用
7. 真正的业务副作用放在恢复之后
8. 人工 resume 输入必须校验
```

LangGraph interrupts 文档明确列出了这些规则，包括不要捕获 interrupt、不要重排同一节点中的 interrupt 调用、interrupt value 尽量简单、interrupt 前的副作用要幂等。

---

# 三十、26｜HITL 和 Tool Calling 的关系
普通 Tool Calling：

```plain
模型决定调用工具
工具直接执行
```

HITL Tool Calling：

```plain
模型或图准备工具参数
 ↓
高风险工具前 interrupt
 ↓
人工审核参数
 ↓
approve / reject / edit
 ↓
真正执行工具
```

---

## 【重点内容】
高风险工具不要让模型直接调用。

比如：

```plain
refund_order
delete_user
send_email
execute_sql
```

可以拆成两个节点：

```plain
prepare_tool_call_node
human_review_node
execute_tool_node
```

这样就能保证执行前有人确认。

---

# 三十一、27｜HITL 和 LangChain Agent Middleware 的关系
LangChain v1 也提供了 Human-in-the-loop middleware，可以对符合策略的 tool call 自动触发人工审核；它底层同样依赖 LangGraph 的持久化能力，调用时需要给 agent 配置 checkpointer 和 thread_id。

## 【重点内容】
这里给大家区分一下。

如果你用的是 LangChain 的 `create_agent`，并且想快速给工具加人工审核，可以看 HumanInTheLoopMiddleware。

如果你要做更可控的企业流程，比如电商退款图，我更推荐用 LangGraph 手写节点。

因为你可以明确控制：

```plain
什么时候查订单
什么时候查规则
什么时候评估风险
什么时候 interrupt
approve 后去哪里
reject 后去哪里
edit 后怎么处理
```

---

# 三十二、28｜HITL 和 Persistence 的边界
Persistence 保存：

```plain
Graph State
interrupt 位置
checkpoint
thread history
```

业务系统保存：

```plain
审批记录
退款申请单
真实退款流水
客服工单
操作审计
```

不要只依赖 checkpoint 保存审批结果。

---

## 【重点内容】
这一点要讲清楚。

Checkpoint 是图恢复用的。

不是业务审计表。

比如人工审核通过后，除了让图恢复执行，还要写业务审计表。

否则后面财务和客服查不到正式审批记录。

---

# 三十三、29｜HITL 常见错误一：没有 checkpointer
错误：

```python
app = graph.compile()
```

正确：

```python
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

---

# 三十四、30｜常见错误二：恢复时换了 thread_id
错误：

```python
# 暂停时
thread_id = "thread_001"

# 恢复时
thread_id = "thread_002"
```

结果：

```plain
恢复不到原来的 interrupt。
```

正确：

```plain
同一个 HITL 流程，start 和 resume 必须使用同一个 thread_id。
```

---

# 三十五、31｜常见错误三：interrupt 前执行真实退款
错误：

```python
def node(state):
    refund_order(...)
    decision = interrupt(...)
```

问题：

```plain
第一次执行已经退款；
恢复后节点重新执行，可能再次退款。
```

正确：

```python
def node(state):
    decision = interrupt(...)
    refund_order(...)
```

或者更好：

```plain
human_review_node 只审核
execute_refund_node 才执行退款
```

---

# 三十六、32｜常见错误四：人工输入不校验
错误：

```python
decision = interrupt(...)
return {"human_decision": decision}
```

但不校验：

```plain
type
reviewer_id
edited_payload
amount
permission
```

正确：

```plain
resume 输入必须经过 Pydantic / 业务规则校验。
```

---

# 三十七、33｜常见错误五：审批和业务动作写在一个节点
不推荐：

```plain
human_review_node：
interrupt + 退款执行 + 回答生成
```

推荐拆分：

```plain
human_review_node
route_after_human_review
apply_edit_node
execute_refund_node
reject_refund_node
generate_answer_node
```

---

# 三十八、34｜常见错误六：只支持 approve，不支持 reject / edit
真实审核一般至少支持：

```plain
approve：同意
reject：拒绝
edit：修改参数后同意
```

尤其是金额、收件人、邮件内容、SQL 等参数，经常需要 edit。

---

# 三十九、35｜常见错误七：没有审计日志
错误：

```plain
人工点了同意，但数据库里没有记录。
```

问题：

```plain
后面无法追责、无法复盘、无法审计。
```

正确：

```plain
checkpoint + human_review_log + business_action_log
```

---

# 四十、36｜常见错误八：审批接口没有权限控制
错误：

```plain
任何登录用户都能调用 /resume approve
```

正确：

```plain
根据 role / permission / refund_amount 做权限判断。
```

---

# 四十一、37｜面试回答：Human-in-the-loop 怎么理解
## 回答话术一：基础版
```plain
Human-in-the-loop 可以理解成 Agent 执行过程中的人工确认机制。

在 LangGraph 里，通常通过 interrupt 暂停图执行，把需要审核的信息返回给外部系统。外部系统展示给人工审核人，审核后再用 Command(resume=...) 把 approve、reject 或 edit 决策传回图里，图再从 checkpoint 恢复并继续执行。

这个能力依赖 Persistence，所以图必须配置 checkpointer，并且 start 和 resume 要使用同一个 thread_id。
```

---

## 回答话术二：项目版
```plain
比如电商客服退款场景，用户说“我的订单 10003 申请退款”。

Graph 会先识别退款意图，提取订单号，查询订单状态，然后准备退款参数。如果订单金额比较大，或者订单不是待发货状态，就进入 high risk。

这时图不会直接执行退款，而是在 human_review_node 里调用 interrupt，把订单信息、退款金额、风险等级和待执行动作返回给后台。客服主管可以选择 approve、reject 或 edit。

如果 approve，就进入 execute_refund_node 执行退款；如果 reject，就进入 reject_refund_node；如果 edit，就先更新退款参数，再执行退款。
```

---

## 回答话术三：工程版
```plain
工程上，我会把 Human-in-the-loop 拆成几个部分：

第一，风险评估节点，判断是否需要人工确认；
第二，human_review_node，专门负责 interrupt；
第三，resume 接口，接收人工审核结果；
第四，路由函数，根据 approve / reject / edit 决定下一步；
第五，业务执行节点，真正调用退款、发邮件、执行 SQL 等高风险工具；
第六，审计日志，记录审批人、审批时间、原始参数和修改后参数。

这样可以避免模型直接执行高风险动作，也能保证流程可恢复、可追踪、可审计。
```

---

# 四十二、38｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Human-in-the-loop | 第 29 章复杂 Agent 可控性 |
| interrupt | 第 30 章 Command / interrupt |
| Command(resume) | 第 30 章 Command |
| checkpointer | 第 34 章 Persistence |
| thread_id | 第 34 章 Thread |
| State 恢复 | 第 31 章 State |
| 条件路由 | 第 33 章 Conditional Routing |
| 高风险 Tool | 第 25 章 Tool |
| 退款流程 | 第 28 章 Agent + RAG 电商客服 |
| 审计日志 | 第 10 章日志 / 第 11 章 PostgreSQL |
| 权限控制 | 后续企业级权限体系 |
| FastAPI resume 接口 | 第 06～10 章 FastAPI 工程化 |
| 项目二基础 | 第 38 章 LangGraph 电商客服 Agent |


---

# 四十三、39｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Human-in-the-loop 解决什么问题
2. 理解企业 Agent 为什么不能直接执行高风险动作
3. 理解 interrupt 的作用
4. 理解 Command(resume=...) 的作用
5. 理解 HITL 必须依赖 checkpointer
6. 理解 start 和 resume 必须使用同一个 thread_id
7. 创建 langgraph_hitl 目录
8. 定义 HITLState
9. 实现最小 interrupt 示例
10. 理解 interrupt 节点恢复后会重新执行
11. 实现 approve / reject 示例
12. 实现 edit payload 示例
13. 使用 get_state 查看审批前状态
14. 设计电商退款 HITL 流程
15. 实现电商退款 HITL Graph
16. 测试低风险自动退款
17. 测试高风险 approve
18. 测试高风险 reject
19. 测试高风险 edit
20. 校验人工输入
21. 使用 stream 观察 interrupt
22. 封装 HITL Service
23. 创建 HITL API
24. 测试 HITL API
25. 设计前端 HITL 展示方式
26. 理解 HITL 权限控制
27. 理解 HITL 审计日志
28. 总结 interrupt 安全规则
29. 理解 HITL 和 Tool Calling 的关系
30. 理解 HITL 和 LangChain Agent Middleware 的关系
31. 理解 HITL 和 Persistence 的边界
32. 总结常见错误
33. 准备面试回答话术
```

---

# 四十四、40｜课后任务一：跑通最小 interrupt
要求：

```plain
1. 运行 scripts/test_lg35_01_basic_interrupt.py
2. 查看第一次 invoke 返回什么
3. 查看 Command(resume="approve") 后返回什么
4. 说明 interrupt 和 Command(resume) 的关系
```

---

# 四十五、41｜课后任务二：测试 approve / reject
要求：

```plain
1. 运行 scripts/test_lg35_02_approve_reject.py
2. 把 resume 改成 approve
3. 把 resume 改成 reject
4. 观察路由分支差异
```

---

# 四十六、42｜课后任务三：测试 edit payload
要求：

```plain
1. 运行 scripts/test_lg35_03_edit_payload.py
2. 修改 edited_payload.amount
3. 查看 final_payload 是否变成修改后的参数
4. 说明 edit 在真实业务中的价值
```

---

# 四十七、43｜课后任务四：审批前查看 State
要求：

```plain
1. 运行 scripts/test_lg35_04_get_state_before_resume.py
2. 查看 snapshot.values
3. 找到 pending_payload
4. 思考后台审批页面应该展示哪些字段
```

---

# 四十八、44｜课后任务五：跑通电商退款 HITL
要求：

```plain
1. 运行 scripts/test_lg35_05_ecommerce_refund_hitl.py
2. 测试订单 10002 低风险退款
3. 测试订单 10003 高风险 approve
4. 测试订单 10003 高风险 reject
5. 测试订单 10003 高风险 edit
6. 查看每种情况下 final_answer 和 action_result
```

---

# 四十九、45｜课后任务六：校验人工输入
要求：

```plain
1. 运行 scripts/test_lg35_06_validate_human_input.py
2. 删除 reviewer_id 再测试
3. edit 时传 amount=-1 再测试
4. 说明为什么 resume 输入必须校验
```

---

# 五十、46｜课后任务七：stream 观察 HITL
要求：

```plain
1. 运行 scripts/test_lg35_07_stream_interrupt.py
2. 查看第一次 stream 里哪个节点触发 interrupt
3. 查看 resume 后哪些节点继续执行
4. 思考前端如何展示执行进度
```

---

# 五十一、47｜课后任务八：跑通 HITL Service
要求：

```plain
1. 运行 scripts/test_lg35_08_hitl_service.py
2. 查看 start 返回的 thread_id
3. 查看 get_state 返回的 pending_payload
4. 查看 resume 后 final_answer
5. 说明 Service 为什么要统一封装 thread_id
```

---

# 五十二、48｜课后任务九：扩展真实权限控制
要求设计：

```plain
1. 退款金额 < 500，客服可审批
2. 退款金额 >= 500，客服主管可审批
3. 退款金额 >= 1000，财务可审批
4. 普通用户不能调用 resume approve
5. 所有审批动作写入 audit log
```

---

# 五十三、49｜课后任务十：设计 HITL 审计表
要求设计表：

```plain
agent_human_reviews
```

字段至少包含：

```plain
id
thread_id
conversation_id
reviewer_id
decision_type
reason
original_payload
edited_payload
created_at
```

并说明：

```plain
checkpoint 和 audit log 分别解决什么问题。
```

---

# 五十四、50｜课后任务十一：把退款工具改成真实 Tool
要求：

```plain
1. 把 execute_refund_node 中的 mock 逻辑改成真实 refund_order_tool
2. refund_order_tool 只能在 human_review 之后调用
3. 执行前记录 tool_call_log
4. 执行后记录 action_result
5. 失败时进入 error_handler
```

---

# 五十五、51｜本章总结
## 【重点内容】
好了，到这里，第 35 章我们就讲完了。

这一章我们完成了 LangGraph Human-in-the-loop。

大家一定要记住一句话：

```plain
Human-in-the-loop 的本质是：
让 Agent 在高风险动作前暂停，等待人类确认后再继续。
```

LangGraph 里核心就是两个 API：

```python
interrupt(...)
Command(resume=...)
```

但它不是孤立能力。

它必须依赖：

```plain
checkpointer
thread_id
State
Conditional Routing
```

所以从第 31 章到第 35 章其实是连起来的：

```plain
State 保存上下文
Node 执行步骤
Conditional Routing 控制分支
Persistence 保存状态
Human-in-the-loop 暂停和恢复
```

这一章我们还完成了电商退款场景：

```plain
低风险退款自动执行
高风险退款暂停审核
人工 approve 后执行
人工 reject 后拒绝
人工 edit 后修改参数再执行
```

这就是企业级 Agent 里非常关键的安全控制能力。

---
