---

# 一、本章定位
前面我们已经完成了 LangChain 阶段的几个核心模块：

```plain
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
第 25 章｜LangChain Tool
```

第 25 章我们完成了 LangChain Tool Calling：

```plain
@tool
StructuredTool
model.bind_tools
AIMessage.tool_calls
ToolMessage
LangChainToolExecutor
LangChainToolCallingService
```

但是第 25 章还是我们自己手动写循环：

```plain
第一次调用模型
 ↓
拿到 tool_calls
 ↓
执行工具
 ↓
追加 ToolMessage
 ↓
第二次调用模型
 ↓
生成最终回答
```

这一章继续升级：

# LangChain Agent
Agent 会把这套循环进一步封装起来。

它可以根据用户目标自动决定：

```plain
是否需要工具
调用哪个工具
工具参数是什么
工具结果是否足够
是否继续调用工具
什么时候生成最终回答
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Agent 到底是什么
2. Agent 和普通 Chat 的区别
3. Agent 和 Tool Calling 的区别
4. LangChain create_agent 怎么用
5. create_agent 返回的是什么
6. Agent 为什么构建在 LangGraph 之上
7. Agent 的输入 messages 怎么写
8. Agent 的输出 messages 怎么看
9. Agent 如何自动调用工具
10. Agent 多步骤执行是怎么发生的
11. Agent stream 怎么看中间步骤
12. Agent 如何接入 query_order 工具
13. Agent 如何接入 query_logistics 工具
14. Agent 如何处理工具失败
15. Agent 如何做电商客服场景
16. AgentService 如何封装
17. Agent API 如何设计
18. Agent 和第 19 章 AI Chat 项目如何整合
19. Agent 的安全边界在哪里
20. 为什么复杂 Agent 最终还要学 LangGraph
```

---

# 三、本章版本口径
本课程 LangChain 阶段统一使用：

```plain
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
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
```

LangChain v1 的 Agent 文档使用 `from langchain.agents import create_agent` 作为标准创建方式；`create_agent` 的参考文档也说明它会创建一个在循环中调用工具直到满足停止条件的 agent graph。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langchain_agents/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── factory.py
│   │   ├── service.py
│   │   ├── ecommerce_agent.py
│   │   ├── demo_create_agent_basic.py
│   │   ├── demo_ecommerce_agent.py
│   │   ├── demo_agent_streaming.py
│   │   ├── demo_agent_error_handling.py
│   │   └── demo_project_adapter.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langchain_agents.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc26_create_agent_basic.py
│   ├── test_lc26_ecommerce_agent.py
│   ├── test_lc26_agent_streaming.py
│   ├── test_lc26_agent_service.py
│   └── test_lc26_project_adapter.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 26 章。

这一章我们讲 LangChain Agent。

前面第 25 章，我们已经能让模型调用工具了。

但是第 25 章的工具调用循环是我们自己手写的。

我们手动做了这些事情：

```plain
绑定工具
第一次调用模型
读取 tool_calls
执行工具
构造 ToolMessage
追加消息
第二次调用模型
返回最终回答
```

这已经是 Agent 的雏形。

但是它还不是真正完整的 Agent 框架。

因为如果任务变复杂，比如：

```plain
先查订单
再根据订单里的物流单号查物流
如果查不到就转人工
如果信息不足就追问用户
如果工具失败就重试
```

手动写循环就会越来越复杂。

LangChain Agent 的价值就是：

**把模型、工具和循环执行封装起来，让模型可以围绕目标自动行动。**

这一章我们就从手动 Tool Calling Loop，升级到 LangChain Agent。

---

# 六、02｜Agent 到底是什么
## 【实操】
```plain
Agent
=
LLM
+
Tools
+
Decision Loop
+
State
```

更口语一点：

```plain
普通 Chat：
用户问，模型答。

Tool Calling：
模型调用一次工具，再答。

Agent：
模型围绕目标，多次判断、多次调用工具，直到完成任务。
```

---

## 【重点内容】
Agent 不是一个固定函数。

Agent 是一种执行模式。

它的核心是：

```plain
模型可以根据目标决定下一步做什么。
```

比如用户说：

```plain
帮我查一下订单 10001 到哪了，如果已经发货，就告诉我物流状态。
```

普通 Chat 只能回答一段话。

Tool Calling 可以调用一个工具。

Agent 更像是：

```plain
先理解目标
 ↓
决定查订单
 ↓
调用 query_order
 ↓
观察订单结果
 ↓
发现有物流单号
 ↓
可能继续调用 query_logistics
 ↓
观察物流结果
 ↓
生成最终客服回复
```

这就是 Agent 的基本思想。

---

# 七、03｜Agent 和普通 Chat 的区别
| 对比项 | 普通 Chat | Agent |
| --- | --- | --- |
| 输入 | 用户问题 | 用户目标 |
| 输出 | 一段回答 | 完成任务后的回答 |
| 是否调用工具 | 不调用 | 可以调用 |
| 是否多步骤 | 通常不是 | 可以多步骤 |
| 是否有状态 | 简单 messages | 有执行状态 |
| 是否适合复杂任务 | 不适合 | 更适合 |
| 典型场景 | 问答、解释、总结 | 客服、搜索、分析、执行任务 |


---

## 【重点内容】
普通 Chat 更像问答。

用户问一句，模型答一句。

Agent 更像任务执行器。

用户给一个目标，Agent 自己判断怎么完成。

比如：

```plain
普通 Chat：
“解释一下什么是 RAG。”

Agent：
“帮我查一下订单状态，如果没发货，告诉我下一步怎么处理。”
```

后者明显需要工具和多步骤判断。

---

# 八、04｜Agent 和 Tool Calling 的区别
| 对比项 | Tool Calling | Agent |
| --- | --- | --- |
| 工具绑定 | 有 | 有 |
| 模型返回 tool_calls | 有 | 有 |
| 工具执行 | 手动写 | Agent 帮忙编排 |
| 循环次数 | 通常手动控制 | Agent 自动循环 |
| 状态管理 | 自己维护 messages | Agent graph 维护 |
| 适合阶段 | 理解原理 | 构建复杂应用 |
| 安全控制 | 后端必须做 | 后端仍然必须做 |


---

## 【重点内容】
第 25 章我们已经讲过 bind_tools。

但是 bind_tools 不是 Agent。

bind_tools 只是：

```plain
把工具告诉模型
```

模型返回：

```plain
AIMessage.tool_calls
```

然后你要自己执行。

Agent 则会在框架层帮你处理更多循环。

LangChain 的 Agents 文档说明，LLM Agent 会在循环中调用工具来实现目标；而 `create_agent` 返回的 Agent 也遵循 LangGraph Graph API，支持 `invoke`、`stream` 等调用方式。

但是注意：

```plain
Agent 帮你编排工具调用
不代表你可以放弃权限、安全、审计
```

---

# 九、05｜LangChain Agent 和 LangGraph 的关系
## 【实操】
```plain
LangChain Agent
  ↓
基于 LangGraph 构建

LangGraph
  ↓
负责状态图、节点、边、持久化、流式、人类介入
```

---

## 【重点内容】
LangChain v1 里的 Agent 已经和 LangGraph 关系非常紧。

官方文档说明，LangChain Agent 构建在 LangGraph 之上，用来获得持久化、流式、人类介入等能力。

你可以这样理解：

```plain
LangChain Agent：
提供更简单的 Agent 使用入口。

LangGraph：
提供更底层、更可控的图编排能力。
```

所以这一章我们先用 LangChain Agent。

后面 LangGraph 阶段，再深入讲：

```plain
State
Node
Edge
Conditional Routing
Checkpoint
Human-in-the-loop
Multi-Agent
```

---

# 十、06｜create_agent 是什么
## 【实操】
```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=tools,
    system_prompt="你是一个客服助手。",
)
```

调用：

```python
result = agent.invoke({
    "messages": [
        {"role": "user", "content": "帮我查订单 10001。"}
    ]
})
```

---

## 【重点内容】
`create_agent` 是 LangChain v1 创建 Agent 的标准入口。

它接收：

```plain
model
tools
system_prompt
middleware
response_format
```

这些参数。

最小使用就是：

```python
agent = create_agent(
    model=model,
    tools=tools,
    system_prompt="..."
)
```

然后调用：

```python
agent.invoke({"messages": [...]})
```

`create_agent` 参考文档说明，它创建的是一个会在循环中调用工具直到满足停止条件的 agent graph；model 既可以是字符串标识，也可以是直接传入的 ChatModel 实例。

本课程里，我们更推荐直接传入我们创建好的 `ChatOpenAI` 模型对象，这样可以复用前面第 22 章的 `LangChainModelFactory`。

---

# 十一、07｜创建 langchain_agents 目录
执行：

```bash
mkdir -p app/langchain_agents

touch app/langchain_agents/__init__.py
touch app/langchain_agents/schemas.py
touch app/langchain_agents/factory.py
touch app/langchain_agents/service.py
touch app/langchain_agents/ecommerce_agent.py
touch app/langchain_agents/demo_create_agent_basic.py
touch app/langchain_agents/demo_ecommerce_agent.py
touch app/langchain_agents/demo_agent_streaming.py
touch app/langchain_agents/demo_agent_error_handling.py
touch app/langchain_agents/demo_project_adapter.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_agents

New-Item app\langchain_agents\__init__.py
New-Item app\langchain_agents\schemas.py
New-Item app\langchain_agents\factory.py
New-Item app\langchain_agents\service.py
New-Item app\langchain_agents\ecommerce_agent.py
New-Item app\langchain_agents\demo_create_agent_basic.py
New-Item app\langchain_agents\demo_ecommerce_agent.py
New-Item app\langchain_agents\demo_agent_streaming.py
New-Item app\langchain_agents\demo_agent_error_handling.py
New-Item app\langchain_agents\demo_project_adapter.py
```

---

# 十二、08｜定义 Agent 响应 Schema
打开：

```plain
app/langchain_agents/schemas.py
```

写入：

```python
from typing import Any

from pydantic import BaseModel, Field


class AgentMessageItem(BaseModel):
    type: str = Field(..., description="消息类型")
    content: str = Field(default="", description="消息内容")
    name: str | None = Field(default=None, description="工具名称或消息名称")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="工具调用列表",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="工具调用 ID",
    )


class AgentRunResponse(BaseModel):
    answer: str = Field(..., description="最终回答")

    messages: list[AgentMessageItem] = Field(
        default_factory=list,
        description="Agent 执行过程中的消息列表",
    )

    used_tools: bool = Field(
        default=False,
        description="是否使用了工具",
    )

    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="执行过程中出现的工具调用",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展信息",
    )


class AgentStreamEvent(BaseModel):
    event: str = Field(..., description="事件类型")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="事件数据",
    )
```

---

## 【重点内容】
这里定义 Agent 返回结构。

为什么不直接把 LangChain 原始 result 返回给前端？

因为原始 result 里有 LangChain Message 对象，前端不一定好用。

所以我们转换成自己的：

```plain
AgentRunResponse
```

里面有：

```plain
answer
messages
used_tools
tool_calls
metadata
```

这样更适合 API 返回。

---

# 十三、09｜实现 Agent 消息转换工具
打开：

```plain
app/langchain_agents/factory.py
```

先写入基础工具函数：

```python
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage

from app.langchain_agents.schemas import AgentMessageItem, AgentRunResponse
from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_tools.registry import langchain_tool_registry


def build_agent_model(
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
    temperature: float = 0,
):
    return LangChainModelFactory.create(
        provider=provider,
        model=model_name,
        temperature=temperature,
    )


def build_ecommerce_agent(
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
):
    model = build_agent_model(
        provider=provider,
        model_name=model_name,
        temperature=0,
    )

    tools = langchain_tool_registry.get_many([
        "query_order",
        "query_logistics",
        "transfer_human",
    ])

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "你是一个跨境电商平台的智能客服 Agent。\n"
            "\n"
            "你可以使用工具查询订单、物流和创建转人工工单。\n"
            "\n"
            "核心规则：\n"
            "1. 用户询问订单状态、发货状态、物流状态时，优先调用工具查询真实信息。\n"
            "2. 不要编造订单状态、物流公司或物流单号。\n"
            "3. 如果用户没有提供订单号，要先追问订单号，不要调用 query_order。\n"
            "4. 如果工具返回未查询到订单，要礼貌说明，并建议用户检查订单号。\n"
            "5. 如果问题超出客服范围，建议转人工。\n"
            "6. 回复要简洁、礼貌、可执行。"
        ),
    )


def message_to_item(message: BaseMessage) -> AgentMessageItem:
    tool_calls = getattr(message, "tool_calls", None) or []
    tool_call_id = getattr(message, "tool_call_id", None)
    name = getattr(message, "name", None)

    content = message.content

    if isinstance(content, list):
        content_text = str(content)
    else:
        content_text = str(content or "")

    return AgentMessageItem(
        type=message.type,
        content=content_text,
        name=name,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
    )


def parse_agent_result(result: dict[str, Any]) -> AgentRunResponse:
    messages = result.get("messages", [])

    items = [
        message_to_item(message)
        for message in messages
    ]

    answer = ""

    if messages:
        answer = str(messages[-1].content or "")

    all_tool_calls: list[dict[str, Any]] = []

    for message in messages:
        tool_calls = getattr(message, "tool_calls", None) or []
        all_tool_calls.extend(tool_calls)

    return AgentRunResponse(
        answer=answer,
        messages=items,
        used_tools=bool(all_tool_calls),
        tool_calls=all_tool_calls,
        metadata={
            "message_count": len(messages),
            "tool_call_count": len(all_tool_calls),
        },
    )
```

---

## 【重点内容】
这个文件做两件事。

第一，创建 Agent：

```python
build_ecommerce_agent()
```

第二，把 Agent 原始 result 转成我们的 API 响应：

```python
parse_agent_result()
```

`create_agent` 返回的是一个 graph 风格的对象，调用后 result 里通常会有 messages。

我们需要从 messages 里提取：

```plain
最终回答
工具调用
中间消息
```

再转换成我们自己的 AgentRunResponse。

---

# 十四、10｜示例一：最小 create_agent
打开：

```plain
app/langchain_agents/demo_create_agent_basic.py
```

写入：

```python
from langchain.agents import create_agent
from langchain_core.tools import tool

from app.langchain_models.model_factory import LangChainModelFactory


@tool
def get_course_progress(chapter: int) -> str:
    """查询 AI Agent 课程指定章节的学习阶段。"""
    if chapter <= 19:
        return "前 19 章属于原生 AI 应用开发和项目一阶段。"

    if 20 <= chapter <= 28:
        return "第 20 到 28 章属于 LangChain 阶段。"

    if 29 <= chapter <= 38:
        return "第 29 到 38 章属于 LangGraph 阶段。"

    return "该章节属于后续高级项目阶段。"


def main():
    model = LangChainModelFactory.create(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0,
    )

    agent = create_agent(
        model=model,
        tools=[get_course_progress],
        system_prompt=(
            "你是一个 AI Agent 课程助教。"
            "当用户询问课程章节、阶段、进度时，可以调用工具查询。"
        ),
    )

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "第 26 章属于哪个阶段？",
            }
        ]
    })

    for message in result["messages"]:
        print(message.type, ":", message.content)
        print("tool_calls:", getattr(message, "tool_calls", None))
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc26_create_agent_basic.py
```

写入：

```python
from app.langchain_agents.demo_create_agent_basic import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc26_create_agent_basic.py
```

---

## 【重点内容】
这是最小 Agent 示例。

核心代码是：

```python
agent = create_agent(
    model=model,
    tools=[get_course_progress],
    system_prompt="..."
)
```

然后：

```python
agent.invoke({"messages": [...]})
```

返回 result 里有 messages。

你会看到中间可能出现：

```plain
AIMessage with tool_calls
ToolMessage
Final AIMessage
```

这就说明 Agent 已经自动完成了工具调用循环。

---

# 十五、11｜Agent 输出 messages 怎么看
典型 messages 顺序：

```plain
HumanMessage
AIMessage(tool_calls=[...])
ToolMessage(content=工具结果)
AIMessage(content=最终回答)
```

---

## 【重点内容】
Agent 的输出不是只有最终回答。

它会把中间过程也放在 messages 里。

我们要重点看三类信息。

第一：

```plain
AIMessage.tool_calls
```

说明模型决定调用了哪些工具。

第二：

```plain
ToolMessage
```

说明工具执行结果是什么。

第三：

```plain
最后一个 AIMessage.content
```

这通常就是最终回答。

做调试时，不要只看最终 answer。

要把 messages 打印出来，看 Agent 到底做了什么。

---

# 十六、12｜示例二：电商客服 Agent
打开：

```plain
app/langchain_agents/demo_ecommerce_agent.py
```

写入：

```python
import json

from app.langchain_agents.factory import (
    build_ecommerce_agent,
    parse_agent_result,
)


def main():
    agent = build_ecommerce_agent(
        provider="deepseek",
        model_name="deepseek-chat",
    )

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "帮我查一下订单 10001 到哪了？",
            }
        ]
    })

    parsed = parse_agent_result(result)

    print(json.dumps(
        parsed.model_dump(),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc26_ecommerce_agent.py
```

写入：

```python
from app.langchain_agents.demo_ecommerce_agent import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc26_ecommerce_agent.py
```

---

## 【重点内容】
这个示例把第 25 章的工具接入 Agent。

用户问：

```plain
订单 10001 到哪了？
```

Agent 会自己判断：

```plain
需要调用 query_order
```

然后工具返回订单结果。

Agent 再生成最终客服回复。

我们不再手写：

```plain
model.bind_tools
first_response.tool_calls
ToolExecutor
ToolMessage
second model call
```

这些循环由 Agent 封装了。

---

# 十七、13｜Agent 自动循环的价值
## 【重点内容】
Agent 自动循环的价值在复杂任务里更明显。

比如用户说：

```plain
帮我查订单 10001，如果已经发货，再查物流详情。
```

理想执行过程是：

```plain
调用 query_order
 ↓
拿到 tracking_no=SF10001
 ↓
调用 query_logistics
 ↓
拿到最新物流节点
 ↓
生成最终回答
```

如果手写，就要自己维护多轮逻辑。

Agent 会把这类模式封装起来。

但是要注意：

```plain
Agent 自动循环不是无限自由
```

我们仍然要控制工具范围、最大步骤、权限和风险。

---

# 十八、14｜Agent 不是越自主越好
## 【重点内容】
很多人一听 Agent，就想让它越自主越好。

但企业项目里，不是这样的。

Agent 自主能力越强，风险也越高。

比如：

```plain
自动退款
自动发短信
自动改订单
自动删数据
自动发送邮件
```

这些都不能完全交给模型。

Agent 更适合先做：

```plain
查询类工具
推荐类任务
辅助分析
内容生成
知识检索
低风险自动化
```

高风险动作要加：

```plain
人工确认
权限校验
审计日志
回滚机制
```

后面 Human-in-the-loop 和 LangGraph 会专门讲。

LangChain 的 Human-in-the-loop 文档也说明，高风险工具可以通过中断机制暂停执行，等待用户或人工审批后再恢复。

---

# 十九、15｜创建 LangChainAgentService
打开：

```plain
app/langchain_agents/service.py
```

写入：

```python
from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.langchain_agents.factory import (
    build_ecommerce_agent,
    parse_agent_result,
)
from app.langchain_agents.schemas import AgentRunResponse


logger = get_logger(__name__)


class LangChainAgentService:
    async def run_ecommerce_agent(
        self,
        user_question: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> AgentRunResponse:
        logger.info(
            f"langchain_agent_start provider={provider} model={model_name}"
        )

        try:
            agent = build_ecommerce_agent(
                provider=provider,
                model_name=model_name,
            )

            result = await agent.ainvoke({
                "messages": [
                    {
                        "role": "user",
                        "content": user_question,
                    }
                ]
            })

            parsed = parse_agent_result(result)

        except Exception as exc:
            logger.exception("langchain_agent_run_failed")

            raise AppException(
                message="LangChain Agent 执行失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "provider": provider,
                    "model": model_name,
                    "error": repr(exc),
                },
            ) from exc

        logger.info(
            f"langchain_agent_success used_tools={parsed.used_tools} "
            f"tool_call_count={len(parsed.tool_calls)}"
        )

        return parsed


langchain_agent_service = LangChainAgentService()
```

---

## 【重点内容】
这里我们封装 LangChainAgentService。

它的作用和前几章 Service 一样：

```plain
屏蔽底层 LangChain 细节
统一异常处理
统一日志
统一返回结构
给 Router 和 ChatService 使用
```

不要在 Router 里直接写 create_agent。

企业项目要保持分层：

```plain
Router
 ↓
Service
 ↓
Agent
 ↓
Tools
```

---

# 二十、16｜测试 AgentService
创建：

```plain
scripts/test_lc26_agent_service.py
```

写入：

```python
import asyncio
import json

from app.langchain_agents.service import langchain_agent_service


async def main():
    result = await langchain_agent_service.run_ecommerce_agent(
        user_question="帮我查一下订单 10001 到哪了？",
        provider="deepseek",
        model_name="deepseek-chat",
    )

    print(json.dumps(
        result.model_dump(),
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc26_agent_service.py
```

---

# 二十一、17｜Agent Streaming
## 【实操】
```python
for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "..."}]},
    stream_mode="updates",
):
    print(chunk)
```

---

## 【重点内容】
Agent 不只是一次性返回结果。

它还可以 stream 中间步骤。

这对前端非常重要。

因为 Agent 可能执行很久。

用户需要看到：

```plain
正在分析问题
正在调用 query_order
工具返回结果
正在生成最终回复
```

LangChain Streaming 文档说明，Agent 可以按 steps 或 tokens 流式输出；例如工具节点会产生包含工具执行结果的 ToolMessage。

这一章先演示 `stream_mode="updates"`。

后面 LangGraph 会更深入讲 stream modes。

---

# 二十二、18｜示例三：Agent Streaming
打开：

```plain
app/langchain_agents/demo_agent_streaming.py
```

写入：

```python
from app.langchain_agents.factory import build_ecommerce_agent


def main():
    agent = build_ecommerce_agent(
        provider="deepseek",
        model_name="deepseek-chat",
    )

    for chunk in agent.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "帮我查一下订单 10001 到哪了？",
                }
            ]
        },
        stream_mode="updates",
    ):
        print("chunk:")
        print(chunk)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```plain
scripts/test_lc26_agent_streaming.py
```

写入：

```python
from app.langchain_agents.demo_agent_streaming import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc26_agent_streaming.py
```

---

## 【重点内容】
这个脚本可以看到 Agent 执行过程。

你可能会看到：

```plain
model 节点输出 tool_calls
tools 节点输出 ToolMessage
model 节点输出最终回答
```

这就是 Agent 的执行轨迹。

后面如果要在前端显示：

```plain
正在调用订单查询工具...
```

就可以基于 stream 事件做。

---

# 二十三、19｜Agent Streaming 和普通 Streaming 的区别
| 对比项 | 普通模型 Streaming | Agent Streaming |
| --- | --- | --- |
| 流的内容 | token / chunk | step / token / tool result |
| 是否包含工具调用 | 通常不包含 | 包含 |
| 是否能看到中间步骤 | 很少 | 可以 |
| 适合场景 | 普通 Chat 打字机 | Agent 执行过程展示 |
| 前端展示 | 持续追加文本 | 状态栏 + 工具步骤 + 最终回答 |


---

## 【重点内容】
普通 Chat Streaming 主要是打字机效果。

Agent Streaming 更像任务执行进度。

比如：

```plain
用户：帮我查订单

前端展示：
正在分析问题...
正在调用 query_order...
查询完成...
正在生成回复...
最终回答...
```

这对 Agent 产品体验非常重要。

---

# 二十四、20｜创建 Agent API
创建：

```plain
app/api/v1/langchain_agents.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langchain_agents.schemas import AgentRunResponse
from app.langchain_agents.service import langchain_agent_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class LangChainAgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    provider: str = Field(default="deepseek", description="模型供应商")
    model: str = Field(default="deepseek-chat", description="模型名称")


@router.post(
    "/langchain/agents/ecommerce/chat",
    response_model=ApiResponse[AgentRunResponse],
)
async def ecommerce_agent_chat(
    request: LangChainAgentChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[AgentRunResponse]:
    result = await langchain_agent_service.run_ecommerce_agent(
        user_question=request.question,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[AgentRunResponse](
        data=result
    )
```

---

# 二十五、21｜注册 Agent Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langchain_agents import router as langchain_agents_router
```

注册：

```python
api_router.include_router(
    langchain_agents_router,
    tags=["LangChain Agents"],
)
```

---

# 二十六、22｜测试 Agent API
启动项目：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/agents/ecommerce/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "帮我查一下订单 10001 到哪了？",
    "provider": "deepseek",
    "model": "deepseek-chat"
  }'
```

预期返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "您好，您的订单 10001 已发货，物流公司是顺丰，物流单号是 SF10001，最新物流节点为：包裹已到达成都高新区中转站。",
    "used_tools": true,
    "tool_calls": [
      {
        "name": "query_order",
        "args": {
          "order_id": "10001"
        },
        "id": "call_xxx",
        "type": "tool_call"
      }
    ],
    "metadata": {
      "message_count": 4,
      "tool_call_count": 1
    }
  },
  "trace_id": null
}
```

---

# 二十七、23｜项目一如何接入 LangChain Agent
第 19 章项目可以这样升级：

```plain
ChatService
 ↓
判断 prompt_scenario=ecommerce_customer_service
 ↓
调用 LangChainAgentService
 ↓
返回 ChatResponse
```

示例：

```python
from app.langchain_agents.service import langchain_agent_service


if request.prompt_scenario == "ecommerce_customer_service":
    agent_result = await langchain_agent_service.run_ecommerce_agent(
        user_question=latest_user_message,
        provider="deepseek",
        model_name=model,
    )

    return ChatResponse(
        answer=agent_result.answer,
        model=model,
        session_id=request.session_id,
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=TokenUsage(),
        sources=[],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "agent": True,
            "used_tools": agent_result.used_tools,
            "tool_calls": agent_result.tool_calls,
            "agent_messages": [
                item.model_dump()
                for item in agent_result.messages
            ],
        },
    )
```

---

## 【重点内容】
这里我们把电商客服场景从 Tool Calling 再升级成 Agent。

第 19 章项目最开始是：

```plain
普通 Chat
```

后来第 18 章加入：

```plain
Tool Calling
```

现在第 26 章可以升级成：

```plain
Agent
```

但是接口仍然可以是：

```plain
/api/v1/chat
```

只是内部根据场景走不同 Service。

---

# 二十八、24｜Agent 和 ChatService 的边界
## 【重点内容】
不要把所有 Chat 都变成 Agent。

Agent 有成本。

因为它可能：

```plain
多次调用模型
多次调用工具
产生更多 token
产生更长延迟
```

所以建议：

```plain
普通问答：
走普通 Chat

需要工具：
走 Tool Calling

复杂任务：
走 Agent
```

比如：

```plain
“什么是 LangChain？”
普通 Chat 即可。

“帮我查订单 10001”
Tool Calling 或 Agent。

“帮我分析这批客户并生成运营策略”
更适合 Agent / Multi-Agent。
```

---

# 二十九、25｜Agent 成本控制
Agent 可能比普通 Chat 更贵。

原因：

```plain
1. 多次模型调用
2. 多次工具调用
3. messages 越来越长
4. 中间步骤也消耗 token
```

所以要控制：

```plain
最大执行步数
最大工具调用次数
最大 token
超时时间
用户级限流
任务级成本预算
```

---

## 【重点内容】
Agent 一定要做成本控制。

不能让模型无限循环。

比如用户问一个复杂问题，Agent 不停调用工具。

如果没有限制，会带来成本和稳定性风险。

本章先讲基础 Agent。

后面企业级阶段会专门讲：

```plain
AI 应用限流与成本控制
```

---

# 三十、26｜Agent 错误处理
Agent 可能失败在多个地方：

```plain
模型调用失败
工具参数错误
工具执行失败
工具超时
模型循环过多
模型不按预期调用工具
最终回答为空
```

---

## 示例：错误处理 Demo
打开：

```plain
app/langchain_agents/demo_agent_error_handling.py
```

写入：

```python
import asyncio

from app.langchain_agents.service import langchain_agent_service


async def main():
    try:
        result = await langchain_agent_service.run_ecommerce_agent(
            user_question="帮我查一下订单 unknown_999 到哪了？",
            provider="deepseek",
            model_name="deepseek-chat",
        )

        print(result.model_dump())

    except Exception as exc:
        print("Agent 执行失败：")
        print(repr(exc))


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 【重点内容】
Agent 错误处理要分层。

工具查不到订单，不一定是系统错误。

应该返回用户可理解的话术：

```plain
没有查询到该订单，请检查订单号是否正确。
```

但模型 API 失败、服务超时、工具程序异常，就要走 AppException 和日志。

不要把技术错误直接返回给用户。

---

# 三十一、27｜Agent Prompt 设计
Agent Prompt 比普通 Chat 更重要。

它要告诉模型：

```plain
你是什么角色
有哪些工具
什么时候用工具
什么时候不要用工具
没有信息时怎么做
工具结果怎么处理
不能编造什么
什么时候转人工
```

示例：

```plain
你是跨境电商客服 Agent。
当用户询问订单状态、发货状态、物流状态时，优先调用工具查询真实信息。
如果用户没有提供订单号，先追问订单号，不要调用 query_order。
工具返回结果后，用礼貌、简洁的中文回复用户。
不要编造订单状态、物流公司或物流单号。
```

---

## 【重点内容】
Agent Prompt 是 Agent 的行为约束。

工具描述是单个工具的使用说明。

System Prompt 是整个 Agent 的行为规则。

两者都重要。

不要只写工具 description，不写 Agent system_prompt。

---

# 三十二、28｜Agent 工具选择不稳定怎么办
可能出现：

```plain
该调用 query_order 却没调用
没有订单号却调用了工具
该转人工却继续回答
调用了不合适的工具
```

解决方向：

```plain
1. 优化 system_prompt
2. 优化工具 description
3. 减少同场景工具数量
4. 先用结构化输出识别意图
5. 按场景绑定工具
6. 高风险工具加人工确认
7. 对关键动作做后端规则兜底
```

---

## 【重点内容】
Agent 不稳定很正常。

不要以为用了 Agent，就所有决策都正确。

模型选择工具是概率行为。

所以关键业务不能只靠模型判断。

比如没有订单号时，不调用工具这个规则，不只是写在 Prompt 里。

后端也可以检查：

```plain
tool_call.name == "query_order"
但 args 里没有 order_id
```

那就拒绝执行，并返回让用户补充订单号。

---

# 三十三、29｜Agent 和 Structured Output 如何配合
推荐流程：

```plain
用户问题
 ↓
Structured Output 意图识别
 ↓
判断是否需要 Agent
 ↓
如果是复杂任务，进入 Agent
 ↓
Agent 调用工具完成任务
```

---

## 【重点内容】
不是所有请求都直接进入 Agent。

可以先用第 24 章结构化输出做路由。

比如：

```plain
intent=general_chat
走普通 Chat

intent=query_order
走电商 Agent

intent=human_service
直接转人工

intent=refund
进入人工确认流程
```

这样比全部请求都给 Agent 更稳定、更安全、更省钱。

---

# 三十四、30｜Agent 和 ToolExecutor 如何配合
LangChain Agent 默认会执行工具。

但是企业项目里，我们仍然需要安全包装。

思路：

```plain
LangChain Tool 函数内部
不要直接查真实系统

而是调用我们的安全 ToolExecutor
```

例如：

```python
@tool
async def query_order(order_id: str) -> str:
    result = await secure_tool_executor.execute(
        tool_name="query_order",
        arguments={"order_id": order_id},
        current_user=current_user,
    )
    return result
```

---

## 【重点内容】
本章为了教学，工具里直接调了 mock 函数。

真实项目里更建议：

```plain
LangChain Tool
只是入口包装

真正执行
走我们的 ToolExecutor
```

这样可以统一：

```plain
权限
脱敏
日志
限流
人工确认
```

---

# 三十五、31｜Agent 和 Human-in-the-loop
## 【重点内容】
高风险 Agent 必须有人类介入。

比如：

```plain
退款
删除数据
发短信
发邮件
修改订单
执行 SQL
```

这些动作不能自动执行。

LangChain 提供 Human-in-the-loop 中间件能力，结合 LangGraph 持久化，可以让 Agent 在高风险工具前暂停，等待审批后再继续执行。

这一章先不展开实现。

后面 LangGraph Human-in-the-loop 章节会专门讲。

---

# 三十六、32｜Agent Streaming API 设计思路
未来可以设计：

```plain
POST /api/v1/langchain/agents/ecommerce/stream
```

SSE 事件：

```plain
event: start
data: {"message": "Agent 开始执行"}

event: step
data: {"message": "正在分析用户问题"}

event: tool_call
data: {"tool_name": "query_order", "args": {"order_id": "10001"}}

event: tool_result
data: {"tool_name": "query_order", "success": true}

event: message
data: {"content": "您好，您的订单..."}

event: done
data: {"finish_reason": "stop"}
```

---

## 【重点内容】
Agent Streaming 不只是打字机效果。

它更适合展示任务进度。

比如前端可以显示：

```plain
AI 正在调用订单查询工具
AI 已完成物流查询
AI 正在生成回复
```

这会让用户更信任 Agent。

---

# 三十七、33｜Agent 不适合什么场景
Agent 不适合：

```plain
1. 简单问答
2. 单轮解释
3. 固定模板输出
4. 高实时低延迟场景
5. 高风险自动执行场景
6. 强确定性业务流程
```

---

## 【重点内容】
不要滥用 Agent。

比如用户问：

```plain
什么是 LangChain？
```

直接普通 Chat 就可以。

没必要创建 Agent、绑定工具、执行图。

Agent 适合有目标、有工具、有多步骤的不确定任务。

简单任务用 Agent，反而成本更高、延迟更大、稳定性更差。

---

# 三十八、34｜Agent 常见错误一：以为 Agent 等于自动化万能工具
错误理解：

```plain
用了 Agent，业务系统就不用写流程了。
```

正确理解：

```plain
Agent 负责智能决策和工具调用。
业务系统仍然负责规则、权限、安全和数据一致性。
```

---

# 三十九、35｜Agent 常见错误二：把所有工具都给 Agent
错误：

```plain
Agent 绑定所有系统工具
```

正确：

```plain
按场景绑定最小必要工具
```

比如电商客服 Agent 只绑定：

```plain
query_order
query_logistics
transfer_human
```

不要把：

```plain
refund_order
delete_user
execute_sql
send_sms
```

随便绑定进去。

---

# 四十、36｜Agent 常见错误三：没有限制执行成本
错误：

```plain
Agent 可以一直推理和调用工具
```

正确：

```plain
限制最大步骤
限制超时时间
限制 token
限制工具次数
用户级限流
```

---

# 四十一、37｜Agent 常见错误四：没有观察中间步骤
错误：

```plain
只看最终 answer
```

正确：

```plain
打印 messages
查看 tool_calls
查看 ToolMessage
查看 stream updates
```

---

## 【重点内容】
Agent 出问题时，一定要看中间过程。

比如：

```plain
它到底有没有调用工具？
调用了哪个工具？
参数对不对？
工具结果是什么？
最终回答有没有基于工具结果？
```

这些都在 messages 和 stream 里。

---

# 四十二、38｜Agent 常见错误五：Prompt 规则只写一遍就不管
Agent Prompt 要不断调优。

要看真实日志：

```plain
哪些问题没调用工具
哪些问题误调用工具
哪些工具参数错误
哪些回复太啰嗦
哪些情况该转人工没转
```

然后优化：

```plain
system_prompt
tool description
工具参数 schema
路由策略
后端兜底规则
```

---

# 四十三、39｜Agent 常见错误六：把高风险动作交给模型直接执行
错误：

```plain
用户说退款
Agent 自动调用 refund_order
```

正确：

```plain
Agent 只提出建议
系统进入确认流程
用户确认后后端执行
```

---

# 四十四、40｜Agent 常见错误七：不用 LangGraph 也硬做复杂流程
如果流程包含：

```plain
复杂分支
状态持久化
人工审批
中断恢复
多 Agent 协作
长任务
```

就不适合只用简单 Agent。

应该进入：

```plain
LangGraph
```

---

## 【重点内容】
LangChain Agent 适合快速构建 Agent。

但如果你要做企业级复杂 Agent 平台，最终还是要学 LangGraph。

因为 LangGraph 提供更底层的：

```plain
State
Node
Edge
Checkpoint
Interrupt
Persistence
```

这就是后面阶段的重点。

---

# 四十五、41｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| `create_agent` | 第 25 章手动 Tool Calling Loop |
| Agent messages | 第 22 章 Message |
| Agent system_prompt | 第 23 章 Prompt |
| Agent tool_calls | 第 25 章 AIMessage.tool_calls |
| ToolMessage | 第 25 章工具结果 |
| Agent 自动循环 | 第 18 章 ToolCallingService 升级 |
| Agent streaming | 第 16 章 Streaming 升级 |
| AgentService | 第 19 章 ChatService 分层 |
| 电商客服 Agent | 第 19 章项目一 + 第 25 章工具 |
| Human-in-the-loop | 后续 LangGraph |
| Agent 路由 | 第 24 章 Structured Output |
| LangGraph | 第 29 章以后 |


---

# 四十六、42｜本章完整复习
这一章我们完成了：

```plain
1. 理解 Agent 是什么
2. 理解 Agent 和普通 Chat 的区别
3. 理解 Agent 和 Tool Calling 的区别
4. 理解 LangChain Agent 和 LangGraph 的关系
5. 理解 create_agent 的作用
6. 创建 langchain_agents 目录
7. 定义 AgentRunResponse
8. 定义 AgentMessageItem
9. 实现 build_agent_model
10. 实现 build_ecommerce_agent
11. 实现 message_to_item
12. 实现 parse_agent_result
13. 编写最小 create_agent 示例
14. 理解 Agent 输出 messages
15. 编写电商客服 Agent 示例
16. 理解 Agent 自动循环价值
17. 理解 Agent 自主能力风险
18. 实现 LangChainAgentService
19. 创建 AgentService 测试脚本
20. 理解 Agent Streaming
21. 编写 Agent Streaming 示例
22. 理解 Agent Streaming 和普通 Streaming 的区别
23. 创建 Agent API
24. 注册 Agent Router
25. 测试 Agent API
26. 理解项目一如何接入 LangChain Agent
27. 理解 Agent 和 ChatService 的边界
28. 理解 Agent 成本控制
29. 理解 Agent 错误处理
30. 理解 Agent Prompt 设计
31. 理解 Agent 工具选择不稳定怎么处理
32. 理解 Agent 和 Structured Output 如何配合
33. 理解 Agent 和 ToolExecutor 如何配合
34. 理解 Agent 和 Human-in-the-loop 的关系
35. 总结 Agent 常见错误
```

---

# 四十七、43｜课后任务一：跑通最小 Agent
要求：

```plain
1. 运行 scripts/test_lc26_create_agent_basic.py
2. 输入“第 26 章属于哪个阶段？”
3. 观察 Agent 是否调用 get_course_progress
4. 打印 result["messages"]
5. 找到 AIMessage.tool_calls 和 ToolMessage
```

---

# 四十八、44｜课后任务二：跑通电商客服 Agent
要求：

```plain
1. 运行 scripts/test_lc26_ecommerce_agent.py
2. 输入“帮我查一下订单 10001 到哪了？”
3. 查看 used_tools 是否为 true
4. 查看 tool_calls 里的工具名和参数
5. 查看最终 answer 是否基于工具结果
```

---

# 四十九、45｜课后任务三：测试缺少订单号
输入：

```plain
帮我查一下订单到哪了？
```

要求：

```plain
1. Agent 不应该调用 query_order
2. 应该追问用户提供订单号
3. 如果错误调用了工具，优化 system_prompt 和工具 description
```

---

# 五十、46｜课后任务四：测试未查询到订单
输入：

```plain
帮我查一下订单 99999 到哪了？
```

要求：

```plain
1. Agent 可以调用 query_order
2. 工具返回 not_found
3. 最终回答要礼貌说明未查询到订单
4. 不要编造物流信息
```

---

# 五十一、47｜课后任务五：跑通 Agent Streaming
要求：

```plain
1. 运行 scripts/test_lc26_agent_streaming.py
2. 查看 stream updates
3. 找到 model 节点输出
4. 找到 tools 节点输出
5. 思考如何转成 SSE 返回前端
```

---

# 五十二、48｜课后任务六：项目一接入 Agent
要求：

```plain
1. ChatService 判断 prompt_scenario=ecommerce_customer_service
2. 调用 langchain_agent_service.run_ecommerce_agent
3. 返回 ChatResponse
4. metadata 中包含 agent=True、used_tools、tool_calls
5. 前端 Demo 能展示 tool_calls 信息
```

---

# 五十三、49｜课后任务七：设计 Agent 成本控制
要求设计配置：

```python
AGENT_LIMITS = {
    "max_steps": 5,
    "max_tool_calls": 3,
    "timeout_seconds": 60,
    "max_tokens": 3000,
}
```

并思考：

```plain
1. 超过 max_steps 怎么办？
2. 工具调用失败是否重试？
3. 用户频繁调用 Agent 如何限流？
4. 如何记录 Agent 成本？
```

---

# 五十四、50｜课后任务八：画出 LangChain Agent 调用链路
画出：

```plain
POST /api/v1/langchain/agents/ecommerce/chat
```

完整链路：

```plain
HTTP Request
 ↓
Agent Router
 ↓
LangChainAgentService
 ↓
build_ecommerce_agent
 ↓
create_agent
 ↓
model + tools + system_prompt
 ↓
agent.ainvoke({"messages": [...]})
 ↓
Agent Graph
 ↓
Model Node
 ↓
Tool Calls
 ↓
Tool Node
 ↓
ToolMessage
 ↓
Model Node
 ↓
Final AIMessage
 ↓
parse_agent_result
 ↓
AgentRunResponse
 ↓
ApiResponse
```

---

# 五十五、51｜本章总结
## 【重点内容】
好了，到这里，第 26 章我们就讲完了。

这一章我们把第 25 章的手动 Tool Calling Loop，升级成了 LangChain Agent。

大家一定要记住：

```plain
Tool Calling
是模型可以调用工具。

Agent
是模型围绕目标，在循环中选择工具、执行工具、观察结果，直到完成任务。
```

LangChain v1 里，我们通过：

```python
from langchain.agents import create_agent
```

创建 Agent。

Agent 会接收：

```plain
model
tools
system_prompt
```

然后通过：

```python
agent.invoke({"messages": [...]})
```

或：

```python
await agent.ainvoke({"messages": [...]})
```

执行。

本章我们完成了：

```plain
最小 Agent
电商客服 Agent
AgentService
Agent API
Agent Streaming 示例
项目一接入方案
Agent 安全边界
Agent 成本控制思路
```

但是也要记住：

Agent 不是万能自动化系统。

企业项目里，Agent 仍然要受限于：

```plain
工具白名单
权限控制
参数校验
敏感信息脱敏
高风险人工确认
日志审计
成本控制
```

到这里，我们已经完成了 LangChain 阶段最核心的几个模块：

```plain
Model
Message
Prompt
Structured Output
Tool
Agent
```

下一步，我们会进入 LangChain RAG。

---
