---

# 一、本章定位
前面我们已经完成了 LangChain 阶段的大部分核心能力：

```plain
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
第 25 章｜LangChain Tool
第 26 章｜LangChain Agent
第 27 章｜LangChain RAG
```

第 26 章我们完成了：

```plain
电商客服 Agent
query_order
query_logistics
transfer_human
create_agent
AgentService
Agent API
```

第 27 章我们完成了：

```plain
Document
Text Splitter
Embedding
VectorStore
Retriever
RAG Chain
RAG Service
search_knowledge_base_tool
```

这一章要把两条线合并。

也就是：

# Agent + RAG
让 Agent 具备两种能力：

```plain
1. 查业务系统
   例如订单状态、物流状态、人工客服工单

2. 查企业知识库
   例如售后规则、退款规则、员工制度、课程说明
```

这样就从一个普通客服机器人，升级成真正的：

```plain
企业知识库增强型客服 Agent
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 为什么 Agent 需要 RAG
2. 为什么 RAG 可以作为 Tool
3. Agent + RAG 和普通 RAG 的区别
4. Agent + RAG 和普通 Agent 的区别
5. search_knowledge_base_tool 如何接入 Agent
6. Agent 如何判断查知识库还是查订单
7. Agent 如何同时调用 RAG Tool 和业务 Tool
8. 如何让 Agent 基于知识库规则回答
9. 如何让 Agent 基于订单工具结果回答
10. 如何避免 Agent 编造知识库内容
11. 如何保留 citations / sources
12. 如何设计 Agent + RAG Prompt
13. 如何封装 AgentRAGService
14. 如何创建 Agent + RAG API
15. 如何实现 Agent + RAG Streaming
16. 如何接入第 19 章 AI Chat 项目
17. Agent + RAG 的安全边界
18. Agent + RAG 的常见错误
19. Agent + RAG 的优化方向
20. 为什么复杂 Agent + RAG 后续要升级到 LangGraph
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

安装依赖继续沿用第 27 章：

```bash
uv add "langchain>=1.3,<1.4" \
       "langchain-core>=1.5,<1.6" \
       "langchain-openai>=1.5,<1.6" \
       "langgraph>=1.2,<1.3" \
       "langchain-text-splitters" \
       "langchain-chroma" \
       "chromadb"
```

本章主要使用：

```python
from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import BaseMessage
```

LangChain Streaming 文档说明，Agent 可以用 `stream_mode="updates"` 这类模式暴露执行过程，包括模型步骤、工具调用和工具结果，这对 Agent + RAG 的前端过程展示非常重要。

---

# 四、本章最终项目结构
本章新增目录：

```plain
ai-agent-course/
├── app/
│   ├── langchain_agent_rag/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── index.py
│   │   ├── factory.py
│   │   ├── service.py
│   │   ├── demo_agent_rag_basic.py
│   │   ├── demo_agent_rag_ecommerce.py
│   │   ├── demo_agent_rag_streaming.py
│   │   ├── demo_agent_rag_project_adapter.py
│   │   └── demo_agent_rag_sources.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langchain_agent_rag.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_lc28_agent_rag_basic.py
│   ├── test_lc28_agent_rag_ecommerce.py
│   ├── test_lc28_agent_rag_service.py
│   ├── test_lc28_agent_rag_streaming.py
│   └── test_lc28_agent_rag_sources.py
│
└── README.md
```

---

# 五、01｜本章开场
## 【重点内容】
大家好，欢迎来到第 28 章。

这一章我们讲 LangChain Agent + RAG。

前面第 26 章，我们已经做了 Agent。

这个 Agent 可以调用订单工具。

比如用户问：

```plain
帮我查一下订单 10001 到哪了？
```

Agent 可以调用：

```plain
query_order
```

然后基于订单工具结果回答。

第 27 章，我们做了 RAG。

比如用户问：

```plain
订单未发货可以退款吗？
```

系统可以先从售后规则知识库里检索，再基于知识库回答。

但是真实业务里，用户经常不是只问一个单点问题。

用户可能会问：

```plain
我的订单 10002 还没发货，这种情况可以退款吗？
```

这个问题同时需要两类信息。

第一类是业务系统信息：

```plain
订单 10002 当前是什么状态？
```

第二类是知识库规则：

```plain
订单未发货时能不能退款？
```

所以这就需要：

```plain
Agent + RAG
```

Agent 负责判断和编排。

RAG 负责查知识库。

业务 Tool 负责查订单系统。

最终 Agent 综合这些信息回答用户。

---

# 六、02｜为什么 Agent 需要 RAG
## 【实操】
```plain
Agent 没有 RAG：
只能靠模型自身知识 + 工具结果

Agent 有 RAG：
可以查企业知识库 + 调用业务工具
```

---

## 【重点内容】
Agent 如果没有 RAG，就缺少企业知识。

它可以调用订单工具，但不知道企业售后规则。

比如订单状态查出来是：

```plain
paid，已付款，待发货
```

但用户问：

```plain
这种情况可以退款吗？
```

Agent 如果不查售后规则，就只能凭模型自己的常识回答。

这是不可靠的。

所以企业 Agent 必须有 RAG。

RAG 给 Agent 提供：

```plain
制度
规则
SOP
文档
产品说明
课程资料
```

业务 Tool 给 Agent 提供：

```plain
订单状态
物流状态
用户数据
系统操作能力
```

两者结合，才是真正能落地的企业 Agent。

---

# 七、03｜为什么 RAG 可以作为 Tool
## 【实操】
```plain
RAG Tool:

search_knowledge_base(query)
 ↓
Retriever
 ↓
VectorStore
 ↓
Top K Documents
 ↓
RAG Chain
 ↓
Answer + Sources
```

---

## 【重点内容】
RAG 本质上可以看成一个工具。

这个工具叫：

```plain
search_knowledge_base
```

输入是用户问题或者检索关键词。

输出是知识库回答和引用来源。

所以对 Agent 来说，它有这些工具：

```plain
query_order
query_logistics
transfer_human
search_knowledge_base
```

当用户问订单状态时，调用 query_order。

当用户问售后规则时，调用 search_knowledge_base。

当用户的问题同时涉及订单和规则时，两个工具都可以调用。

这就是 Agent + RAG 的核心。

LangChain 的 Retriever 文档说明，Retriever 的职责是接收字符串 query 并返回 `Document` 列表；Agentic RAG 示例则展示了 Agent 可以决定什么时候使用 retriever 工具。

---

# 八、04｜Agent + RAG 和普通 RAG 的区别
| 对比项 | 普通 RAG | Agent + RAG |
| --- | --- | --- |
| 是否一定检索 | 通常每次都检索 | Agent 判断是否检索 |
| 是否能调用业务工具 | 通常不能 | 可以 |
| 是否能多步骤 | 通常是单轮链路 | 可以多步骤 |
| 是否能结合业务数据 | 弱 | 强 |
| 适合场景 | 企业知识库问答 | 智能客服、复杂业务助手 |
| 示例 | “年假有几天？” | “我的订单没发货，可以退款吗？” |


---

## 【重点内容】
普通 RAG 适合问知识库。

比如：

```plain
员工年假有几天？
```

这个问题只需要查知识库。

但是 Agent + RAG 适合更复杂的问题。

比如：

```plain
订单 10002 还没发货，这种情况可以退款吗？
```

它既要查订单状态，又要查退款规则。

这时就不是普通 RAG 能很好解决的了。

Agent 需要自己决定调用哪个工具，以及调用顺序。

---

# 九、05｜Agent + RAG 和普通 Agent 的区别
| 对比项 | 普通 Agent | Agent + RAG |
| --- | --- | --- |
| 工具类型 | 业务工具为主 | 业务工具 + 知识库工具 |
| 知识来源 | 模型自身 + 工具返回 | 模型 + 工具 + 企业知识库 |
| 是否有引用来源 | 不一定 | 应该有 |
| 是否适合企业问答 | 不完整 | 更完整 |
| 是否能回答制度类问题 | 不可靠 | 更可靠 |
| 是否需要检索质量优化 | 不一定 | 需要 |


---

## 【重点内容】
普通 Agent 可以调用业务工具。

但它不一定能回答企业制度问题。

Agent + RAG 把知识库也变成工具。

这样 Agent 遇到制度、规则、文档问题时，可以先查知识库，再回答。

所以 Agent + RAG 是很多企业 AI 应用的核心形态。

---

# 十、06｜Agent + RAG 总体架构
## 【实操】
```plain
用户问题
  ↓
Agent
  ↓
判断需要什么能力
  ├── query_order
  ├── query_logistics
  ├── transfer_human
  └── search_knowledge_base
          ↓
        Retriever
          ↓
        VectorStore
          ↓
        Documents
  ↓
综合工具结果
  ↓
最终回答 + 引用来源
```

---

## 【重点内容】
这一章的架构很清晰。

Agent 是入口。

它负责判断用户的问题需要什么能力。

如果是订单状态，就查订单。

如果是物流状态，就查物流。

如果是售后规则，就查知识库。

如果涉及两者，就两个都查。

最后基于工具结果生成回答。

---

# 十一、07｜先补一个 RAG 索引初始化工具
第 27 章我们已经写了：

```python
langchain_rag_service.rebuild_index()
```

但 Agent 调用 RAG Tool 前，最好先保证知识库索引已经构建。

创建：

```plain
app/langchain_agent_rag/index.py
```

写入：

```python
from pathlib import Path

from app.core.logging import get_logger
from app.langchain_rag.service import langchain_rag_service
from app.langchain_rag.vector_store import CHROMA_DIR


logger = get_logger(__name__)


def ensure_rag_index() -> dict:
    """
    确保本地 RAG 索引存在。

    教学版逻辑：
    1. 如果 Chroma 目录不存在，就 rebuild。
    2. 如果已经存在，就跳过。
    3. 生产环境应该使用文档版本、索引版本和任务状态判断。
    """
    if not Path(CHROMA_DIR).exists():
        logger.info("rag_index_missing_rebuild_start")
        result = langchain_rag_service.rebuild_index()
        logger.info(f"rag_index_rebuild_success result={result}")
        return {
            "rebuilt": True,
            **result,
        }

    return {
        "rebuilt": False,
        "message": "RAG 索引已存在",
    }
```

---

## 【重点内容】
这里我们做一个简单的索引检查。

如果本地 Chroma 目录不存在，就自动 rebuild。

这只是教学版。

真实企业项目不能只判断目录是否存在。

要看：

```plain
文档版本
chunk 版本
embedding 模型版本
索引构建状态
是否有失败任务
```

这些后面企业知识库项目会讲。

---

# 十二、08｜定义 Agent + RAG 返回 Schema
创建：

```plain
app/langchain_agent_rag/schemas.py
```

写入：

```python
from typing import Any

from pydantic import BaseModel, Field


class AgentRAGMessageItem(BaseModel):
    type: str = Field(..., description="消息类型")
    content: str = Field(default="", description="消息内容")
    name: str | None = Field(default=None, description="工具名称")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="工具调用列表",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="工具调用 ID",
    )


class AgentRAGSource(BaseModel):
    document_id: str | None = Field(default=None)
    chunk_id: str | None = Field(default=None)
    source: str | None = Field(default=None)
    content_preview: str = Field(default="")


class AgentRAGRunResponse(BaseModel):
    answer: str = Field(..., description="最终回答")

    used_tools: bool = Field(
        default=False,
        description="是否使用了工具",
    )

    used_rag: bool = Field(
        default=False,
        description="是否使用了知识库检索",
    )

    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="工具调用列表",
    )

    messages: list[AgentRAGMessageItem] = Field(
        default_factory=list,
        description="Agent 执行消息",
    )

    sources: list[AgentRAGSource] = Field(
        default_factory=list,
        description="知识库引用来源",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展信息",
    )
```

---

## 【重点内容】
Agent + RAG 的返回值比普通 Agent 多一个重点：

```plain
sources
```

也就是知识库引用来源。

前端可以展示：

```plain
回答依据来自 employee_handbook.md
引用了 employee_handbook_chunk_0
```

这对企业知识库非常重要。

不要只返回一段 answer。

---

# 十三、09｜创建 Agent + RAG Factory
创建：

```plain
app/langchain_agent_rag/factory.py
```

写入：

```python
import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage

from app.langchain_agent_rag.schemas import (
    AgentRAGMessageItem,
    AgentRAGRunResponse,
    AgentRAGSource,
)
from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_rag.tools import search_knowledge_base_tool
from app.langchain_tools.registry import langchain_tool_registry


def build_agent_rag_model(
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
    temperature: float = 0,
):
    return LangChainModelFactory.create(
        provider=provider,
        model=model_name,
        temperature=temperature,
    )


def build_ecommerce_agent_with_rag(
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
):
    model = build_agent_rag_model(
        provider=provider,
        model_name=model_name,
        temperature=0,
    )

    business_tools = langchain_tool_registry.get_many([
        "query_order",
        "query_logistics",
        "transfer_human",
    ])

    tools = [
        *business_tools,
        search_knowledge_base_tool,
    ]

    return create_agent(
        model=model,
        tools=tools,
        system_prompt=(
            "你是一个跨境电商平台的智能客服 Agent。\n"
            "\n"
            "你可以使用两类工具：\n"
            "1. 业务工具：查询订单、查询物流、创建人工客服工单。\n"
            "2. 知识库工具：查询售后规则、退款规则、课程说明、员工制度等文档内容。\n"
            "\n"
            "核心规则：\n"
            "1. 当用户询问订单状态、发货状态、物流状态时，优先调用 query_order 或 query_logistics。\n"
            "2. 当用户询问退款规则、售后规则、公司制度、课程阶段等知识性问题时，优先调用 search_knowledge_base。\n"
            "3. 当用户问题同时包含订单状态和规则判断时，可以先调用 query_order，再调用 search_knowledge_base。\n"
            "4. 不要编造订单状态、物流公司、物流单号。\n"
            "5. 不要编造售后规则、退款规则、公司制度。\n"
            "6. 如果知识库工具返回无法确认，要明确说明无法从知识库确认。\n"
            "7. 如果用户没有提供订单号，不要调用 query_order，要先追问订单号。\n"
            "8. 如果问题超出 AI 能力范围，建议转人工。\n"
            "9. 最终回答要简洁、礼貌、可执行。\n"
            "10. 如果回答使用了知识库内容，要在回答中说明依据来自知识库。"
        ),
    )


def message_to_item(message: BaseMessage) -> AgentRAGMessageItem:
    tool_calls = getattr(message, "tool_calls", None) or []
    tool_call_id = getattr(message, "tool_call_id", None)
    name = getattr(message, "name", None)

    content = message.content

    if isinstance(content, list):
        content_text = str(content)
    else:
        content_text = str(content or "")

    return AgentRAGMessageItem(
        type=message.type,
        content=content_text,
        name=name,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
    )


def extract_sources_from_tool_message_content(
    content: str,
) -> list[AgentRAGSource]:
    """
    从 search_knowledge_base 工具返回的 JSON 字符串中提取 sources。

    注意：
    本章 RAG Tool 返回的是 RAGAnswer.model_dump() 的 JSON。
    如果后面调整工具返回结构，这里也要同步调整。
    """
    try:
        data = json.loads(content)

    except Exception:
        return []

    raw_sources = data.get("sources") or []

    sources = []

    for item in raw_sources:
        if not isinstance(item, dict):
            continue

        sources.append(
            AgentRAGSource(
                document_id=item.get("document_id"),
                chunk_id=item.get("chunk_id"),
                source=item.get("source"),
                content_preview=item.get("content_preview", ""),
            )
        )

    return sources


def parse_agent_rag_result(
    result: dict[str, Any],
) -> AgentRAGRunResponse:
    messages = result.get("messages", [])

    items = [
        message_to_item(message)
        for message in messages
    ]

    answer = ""

    if messages:
        answer = str(messages[-1].content or "")

    all_tool_calls: list[dict[str, Any]] = []
    sources: list[AgentRAGSource] = []
    used_rag = False

    for message in messages:
        tool_calls = getattr(message, "tool_calls", None) or []
        all_tool_calls.extend(tool_calls)

        if message.type == "tool":
            name = getattr(message, "name", None)

            if name == "search_knowledge_base":
                used_rag = True
                sources.extend(
                    extract_sources_from_tool_message_content(
                        str(message.content or "")
                    )
                )

    return AgentRAGRunResponse(
        answer=answer,
        used_tools=bool(all_tool_calls),
        used_rag=used_rag,
        tool_calls=all_tool_calls,
        messages=items,
        sources=sources,
        metadata={
            "message_count": len(messages),
            "tool_call_count": len(all_tool_calls),
            "source_count": len(sources),
        },
    )
```

---

## 【重点内容】
这个 Factory 是本章核心。

它创建一个：

```plain
电商客服 Agent + RAG
```

这个 Agent 有四个工具：

```plain
query_order
query_logistics
transfer_human
search_knowledge_base
```

也就是说，它既能查业务数据，也能查知识库。

同时我们还写了：

```python
parse_agent_rag_result
```

把 Agent 返回的 messages 转成适合 API 返回的结构。

尤其是从 search_knowledge_base 的 ToolMessage 里提取 sources。

---

# 十四、10｜示例一：最小 Agent + RAG
创建：

```plain
app/langchain_agent_rag/demo_agent_rag_basic.py
```

写入：

```python
import json

from app.langchain_agent_rag.factory import (
    build_ecommerce_agent_with_rag,
    parse_agent_rag_result,
)
from app.langchain_agent_rag.index import ensure_rag_index


def main():
    ensure_rag_index()

    agent = build_ecommerce_agent_with_rag(
        provider="deepseek",
        model_name="deepseek-chat",
    )

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "订单未发货时可以退款吗？",
            }
        ]
    })

    parsed = parse_agent_rag_result(result)

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
scripts/test_lc28_agent_rag_basic.py
```

写入：

```python
from app.langchain_agent_rag.demo_agent_rag_basic import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc28_agent_rag_basic.py
```

---

## 【重点内容】
这个例子用户只问规则：

```plain
订单未发货时可以退款吗？
```

理想情况下，Agent 应该调用：

```plain
search_knowledge_base
```

因为这是售后规则问题。

它不需要查订单。

最终回答应该基于知识库里的售后规则。

比如：

```plain
订单未发货时，用户可以申请取消订单并退款。
```

并且 sources 里应该包含：

```plain
ecommerce_after_sales
```

---

# 十五、11｜示例二：电商订单 + RAG 综合问题
创建：

```plain
app/langchain_agent_rag/demo_agent_rag_ecommerce.py
```

写入：

```python
import json

from app.langchain_agent_rag.factory import (
    build_ecommerce_agent_with_rag,
    parse_agent_rag_result,
)
from app.langchain_agent_rag.index import ensure_rag_index


def main():
    ensure_rag_index()

    agent = build_ecommerce_agent_with_rag(
        provider="deepseek",
        model_name="deepseek-chat",
    )

    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": "我的订单 10002 还没发货，这种情况可以退款吗？",
            }
        ]
    })

    parsed = parse_agent_rag_result(result)

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
scripts/test_lc28_agent_rag_ecommerce.py
```

写入：

```python
from app.langchain_agent_rag.demo_agent_rag_ecommerce import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc28_agent_rag_ecommerce.py
```

---

## 【重点内容】
这个问题更接近真实客服场景：

```plain
我的订单 10002 还没发货，这种情况可以退款吗？
```

它同时需要：

```plain
query_order：
查询订单 10002 当前状态

search_knowledge_base：
查询未发货退款规则
```

理想回答应该是：

```plain
您的订单 10002 当前是已付款、待发货状态。
根据售后规则，订单未发货时可以申请取消订单并退款。
您可以在订单详情页提交取消订单申请。
```

这就是 Agent + RAG 的价值。

---

# 十六、12｜为什么 Agent 可能不会按预期调用两个工具
## 【重点内容】
这里要提前提醒学员。

Agent 不一定每次都完全按我们预期调用两个工具。

比如它可能：

```plain
只查知识库，不查订单
只查订单，不查知识库
先查知识库，再查订单
查了一个工具后就直接回答
```

这是因为模型选择工具是概率决策。

解决方式有几个。

第一，优化 system_prompt。

第二，优化工具 description。

第三，先用结构化输出做路由。

第四，对关键业务逻辑后端兜底。

比如问题里出现订单号，并且问“能不能退款”，后端可以强制要求：

```plain
必须查订单状态
必须查退款规则
```

复杂可控流程后面要用 LangGraph 做。

---

# 十七、13｜Agent + RAG 的 Prompt 设计重点
Agent + RAG 的 system_prompt 要讲清楚四件事：

```plain
1. 你有哪些工具
2. 什么情况查业务工具
3. 什么情况查知识库
4. 同时涉及业务和规则时，两个都要查
```

示例：

```plain
当用户询问订单状态、发货状态、物流状态时，优先调用 query_order 或 query_logistics。

当用户询问退款规则、售后规则、公司制度、课程阶段等知识性问题时，优先调用 search_knowledge_base。

当用户问题同时包含订单状态和规则判断时，可以先调用 query_order，再调用 search_knowledge_base。
```

---

## 【重点内容】
Agent + RAG 的 Prompt 比普通 Agent 更重要。

因为它要学会工具分工。

如果 Prompt 不清楚，模型很容易乱用工具。

比如售后规则问题不查知识库，而是自己回答。

或者订单状态问题不查订单工具，而是凭空猜。

所以 Prompt 要明确：

```plain
查事实状态用业务工具
查规则文档用知识库工具
两类问题都有就组合使用
```

---

# 十八、14｜Agent + RAG Service
创建：

```plain
app/langchain_agent_rag/service.py
```

写入：

```python
from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.langchain_agent_rag.factory import (
    build_ecommerce_agent_with_rag,
    parse_agent_rag_result,
)
from app.langchain_agent_rag.index import ensure_rag_index
from app.langchain_agent_rag.schemas import AgentRAGRunResponse


logger = get_logger(__name__)


class LangChainAgentRAGService:
    async def run_ecommerce_agent_rag(
        self,
        user_question: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
    ) -> AgentRAGRunResponse:
        logger.info(
            f"langchain_agent_rag_start provider={provider} model={model_name}"
        )

        try:
            index_result = ensure_rag_index()

            agent = build_ecommerce_agent_with_rag(
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

            parsed = parse_agent_rag_result(result)
            parsed.metadata["index"] = index_result

        except Exception as exc:
            logger.exception("langchain_agent_rag_failed")

            raise AppException(
                message="LangChain Agent + RAG 执行失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "provider": provider,
                    "model": model_name,
                    "error": repr(exc),
                },
            ) from exc

        logger.info(
            f"langchain_agent_rag_success used_tools={parsed.used_tools} "
            f"used_rag={parsed.used_rag} "
            f"tool_count={len(parsed.tool_calls)} "
            f"source_count={len(parsed.sources)}"
        )

        return parsed


langchain_agent_rag_service = LangChainAgentRAGService()
```

---

## 【重点内容】
这里封装 AgentRAGService。

它做三件事：

```plain
1. 确保 RAG 索引存在
2. 创建 Agent + RAG
3. 执行并解析结果
```

Router 和 ChatService 不应该直接操作 create_agent。

仍然走 Service 分层。

---

# 十九、15｜测试 Agent + RAG Service
创建：

```plain
scripts/test_lc28_agent_rag_service.py
```

写入：

```python
import asyncio
import json

from app.langchain_agent_rag.service import langchain_agent_rag_service


async def main():
    questions = [
        "订单未发货时可以退款吗？",
        "我的订单 10002 还没发货，这种情况可以退款吗？",
        "第 20 到 28 章属于什么阶段？",
    ]

    for question in questions:
        print("question:", question)
        print("=" * 80)

        result = await langchain_agent_rag_service.run_ecommerce_agent_rag(
            user_question=question,
            provider="deepseek",
            model_name="deepseek-chat",
        )

        print(json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        ))

        print("=" * 120)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc28_agent_rag_service.py
```

---

# 二十、16｜创建 Agent + RAG API
创建：

```plain
app/api/v1/langchain_agent_rag.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langchain_agent_rag.schemas import AgentRAGRunResponse
from app.langchain_agent_rag.service import langchain_agent_rag_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class AgentRAGChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    provider: str = Field(default="deepseek", description="模型供应商")
    model: str = Field(default="deepseek-chat", description="模型名称")


@router.post(
    "/langchain/agent-rag/ecommerce/chat",
    response_model=ApiResponse[AgentRAGRunResponse],
)
async def ecommerce_agent_rag_chat(
    request: AgentRAGChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[AgentRAGRunResponse]:
    result = await langchain_agent_rag_service.run_ecommerce_agent_rag(
        user_question=request.question,
        provider=request.provider,
        model_name=request.model,
    )

    return ApiResponse[AgentRAGRunResponse](
        data=result
    )
```

---

# 二十一、17｜注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langchain_agent_rag import router as langchain_agent_rag_router
```

注册：

```python
api_router.include_router(
    langchain_agent_rag_router,
    tags=["LangChain Agent RAG"],
)
```

---

# 二十二、18｜测试 Agent + RAG API
启动：

```bash
uv run uvicorn app.main:app --reload
```

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/agent-rag/ecommerce/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "我的订单 10002 还没发货，这种情况可以退款吗？",
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
    "answer": "您的订单 10002 当前为已付款、待发货状态。根据知识库中的售后规则，订单未发货时可以申请取消订单并退款。您可以在订单详情页提交取消订单申请。",
    "used_tools": true,
    "used_rag": true,
    "tool_calls": [
      {
        "name": "query_order",
        "args": {
          "order_id": "10002"
        },
        "id": "call_xxx",
        "type": "tool_call"
      },
      {
        "name": "search_knowledge_base",
        "args": {
          "query": "订单未发货可以退款吗"
        },
        "id": "call_xxx",
        "type": "tool_call"
      }
    ],
    "sources": [
      {
        "document_id": "ecommerce_after_sales",
        "chunk_id": "ecommerce_after_sales_chunk_0",
        "source": "data/knowledge_base/ecommerce_after_sales.md",
        "content_preview": "订单未发货时，用户可以申请取消订单并退款。"
      }
    ],
    "metadata": {
      "message_count": 6,
      "tool_call_count": 2,
      "source_count": 1
    }
  },
  "trace_id": null
}
```

---

# 二十三、19｜Agent + RAG Streaming
创建：

```plain
app/langchain_agent_rag/demo_agent_rag_streaming.py
```

写入：

```python
from app.langchain_agent_rag.factory import build_ecommerce_agent_with_rag
from app.langchain_agent_rag.index import ensure_rag_index


def main():
    ensure_rag_index()

    agent = build_ecommerce_agent_with_rag(
        provider="deepseek",
        model_name="deepseek-chat",
    )

    for chunk in agent.stream(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "我的订单 10002 还没发货，这种情况可以退款吗？",
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
scripts/test_lc28_agent_rag_streaming.py
```

写入：

```python
from app.langchain_agent_rag.demo_agent_rag_streaming import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc28_agent_rag_streaming.py
```

---

## 【重点内容】
Agent + RAG 的 Streaming 非常适合前端展示过程。

比如：

```plain
正在分析问题
正在查询订单
正在查询知识库
正在生成最终回答
```

这样用户能理解 Agent 正在做什么。

LangChain 的 Event Streaming 文档也说明，Agent 基于 LangGraph，因此可以流式输出 messages、tool calls、state 和自定义 updates。

---

# 二十四、20｜前端展示建议
Agent + RAG 前端不要只展示最终回答。

建议展示三块：

```plain
1. 最终回答 answer
2. 工具调用 tool_calls
3. 引用来源 sources
```

示例展示：

```plain
AI 回答：
您的订单 10002 当前为已付款、待发货状态。根据售后规则，未发货订单可以申请取消订单并退款。

使用的工具：
- query_order
- search_knowledge_base

引用来源：
- ecommerce_after_sales.md
```

---

## 【重点内容】
Agent 产品想让用户信任，一定要透明。

用户要知道：

```plain
你查了什么
依据是什么
有没有查知识库
有没有查订单
```

所以 sources 和 tool_calls 都要展示。

---

# 二十五、21｜项目一如何接入 Agent + RAG
第 19 章项目可以这样升级：

```plain
ChatService
 ↓
根据 prompt_scenario 判断
 ↓
ecommerce_customer_service
 ↓
调用 Agent + RAG
 ↓
返回 ChatResponse
```

示例：

```python
from app.langchain_agent_rag.service import langchain_agent_rag_service


if request.prompt_scenario == "ecommerce_customer_service":
    agent_rag_result = await langchain_agent_rag_service.run_ecommerce_agent_rag(
        user_question=latest_user_message,
        provider="deepseek",
        model_name=model,
    )

    return ChatResponse(
        answer=agent_rag_result.answer,
        model=model,
        session_id=request.session_id,
        message_id=f"m_{uuid.uuid4().hex[:8]}",
        usage=TokenUsage(),
        sources=[
            SourceDocument(
                document_id=source.document_id or "",
                title=source.source or "",
                content=source.content_preview,
                score=0,
                metadata={
                    "chunk_id": source.chunk_id,
                    "source": source.source,
                },
            )
            for source in agent_rag_result.sources
        ],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "agent_rag": True,
            "used_tools": agent_rag_result.used_tools,
            "used_rag": agent_rag_result.used_rag,
            "tool_calls": agent_rag_result.tool_calls,
            "agent_messages": [
                item.model_dump()
                for item in agent_rag_result.messages
            ],
        },
    )
```

---

## 【重点内容】
这一步是把项目一升级成更完整的客服 Agent。

原来项目一支持：

```plain
普通 Chat
Streaming
Prompt
Tool Calling
```

现在可以支持：

```plain
Agent + RAG
```

同样是 `/chat` 接口。

但内部根据场景走不同服务。

这就是 AI 应用平台化的关键。

---

# 二十六、22｜更稳的路由方式：Structured Output 先判断
直接让所有请求进 Agent + RAG，不一定划算。

推荐更稳的路线：

```plain
用户问题
 ↓
第 24 章 Structured Output 意图识别
 ↓
判断场景
 ↓
普通 Chat / RAG / Agent / Agent + RAG
```

示例：

```python
intent_result = await langchain_structured_output_service.classify_intent(
    user_question=latest_user_message,
    provider="deepseek",
    model_name=model,
)

if intent_result.intent == "product_question":
    return await normal_chat(...)

if intent_result.intent == "query_order":
    return await agent_rag_chat(...)

if intent_result.intent == "refund":
    return await agent_rag_chat(...)

if intent_result.intent == "human_service":
    return transfer_human_response(...)
```

---

## 【重点内容】
这比所有问题都扔给 Agent 更好。

因为 Agent 成本高、延迟高。

普通问题不需要 Agent。

知识库问题也可能普通 RAG 就够。

只有复杂任务才进入 Agent + RAG。

所以真实项目建议：

```plain
结构化输出做路由
Agent + RAG 做复杂任务
```

---

# 二十七、23｜如何避免 Agent 编造知识库内容
## 【重点内容】
Agent + RAG 最怕两种编造。

第一种：

```plain
没查知识库，自己编规则。
```

第二种：

```plain
查了知识库，但引用不存在的来源。
```

解决思路：

```plain
1. system_prompt 明确规则类问题必须查 search_knowledge_base。
2. RAG Tool 内部 Prompt 明确只能基于 context 回答。
3. 后端 sources 从工具结果提取，不让模型自己编。
4. 对最终回答做 source 校验。
5. 如果 used_rag=false，但问题属于规则类，后端可以拒绝直接回答并重新走 RAG。
```

也就是说，不能只相信模型最终回答。

要用后端规则兜底。

---

# 二十八、24｜如何保留 citations
本章的 sources 来自：

```plain
search_knowledge_base ToolMessage
```

而不是从最终回答里正则匹配。

流程：

```plain
RAG Tool 返回 JSON
 ↓
里面包含 sources
 ↓
Agent messages 里有 ToolMessage
 ↓
parse_agent_rag_result 提取 sources
 ↓
API 返回 sources
```

---

## 【重点内容】
这个设计很重要。

不要让模型自己随便写引用。

引用来源应该由后端从检索结果里生成。

模型可以在回答里说：

```plain
根据知识库内容
```

但最终 API 的 sources 应该以后端提取为准。

---

# 二十九、25｜Agent + RAG 的工具选择问题
可能出现：

```plain
该查知识库却没查
该查订单却没查
该两个都查却只查一个
工具调用顺序不理想
```

优化方向：

```plain
1. 优化 Agent system_prompt
2. 优化 search_knowledge_base_tool description
3. 优化 query_order_tool description
4. 用 Structured Output 做前置路由
5. 用 LangGraph 写显式流程
```

---

## 【重点内容】
工具选择不稳定是 Agent 的常见问题。

这不是你代码写错，而是 Agent 模式本身的特点。

如果你要更强可控性，就不要完全依赖模型自由选择。

比如退款咨询，可以设计固定流程：

```plain
提取订单号
 ↓
查订单
 ↓
查退款规则
 ↓
生成回答
```

这种就更适合 LangGraph。

---

# 三十、26｜为什么复杂 Agent + RAG 要用 LangGraph
## 【重点内容】
本章用 create_agent 很方便。

但它适合快速搭建。

如果流程变复杂，比如：

```plain
必须先查订单
再判断订单状态
再按状态查不同知识库
再决定是否转人工
再等待用户确认
```

这种就不适合完全交给自由 Agent。

应该用 LangGraph 明确写：

```plain
State
Node
Edge
Conditional Routing
```

比如：

```plain
extract_order_id_node
query_order_node
retrieve_policy_node
generate_answer_node
human_confirm_node
```

这就是后面 LangGraph 阶段要讲的内容。

---

# 三十一、27｜Agent + RAG 和权限控制
RAG 也要权限控制。

不要所有用户都能检索所有文档。

真实项目中 Retriever 应该支持：

```plain
user_id
tenant_id
department_id
role
document_acl
```

伪代码：

```python
retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 4,
        "filter": {
            "tenant_id": current_user.tenant_id,
            "visible_roles": {
                "$contains": current_user.role
            },
        },
    }
)
```

---

## 【重点内容】
企业知识库一定要做权限过滤。

比如：

```plain
普通员工不能查财务资料
外部客户不能查内部制度
销售不能查 HR 敏感文档
```

RAG Tool 返回给 Agent 的内容，必须是当前用户有权限看的内容。

否则 Agent 会把不该看的信息泄露出去。

---

# 三十二、28｜Agent + RAG 和成本控制
Agent + RAG 成本比普通 Chat 更高。

因为它可能包含：

```plain
1. 一次或多次模型调用
2. 一次或多次工具调用
3. RAG 检索
4. RAG 内部模型回答
5. 最终 Agent 总结
```

优化方向：

```plain
1. 先做意图识别，不必要不进 Agent
2. 缓存 RAG 检索结果
3. 缓存高频问题答案
4. 限制工具调用次数
5. 限制 Agent 最大步数
6. 限制 k 值
7. 对长文档做 rerank，而不是盲目塞上下文
```

---

## 【重点内容】
Agent + RAG 很强，但也更贵。

所以不是所有问题都走 Agent + RAG。

比如：

```plain
你好
什么是 LangChain
帮我写个标题
```

这种不需要 RAG，也不需要 Agent。

简单问题走普通 Chat。

规则问答走 RAG。

复杂任务再走 Agent + RAG。

---

# 三十三、29｜Agent + RAG 常见错误一：所有问题都进 Agent + RAG
错误：

```plain
无论用户问什么，都进 Agent + RAG
```

问题：

```plain
成本高
延迟高
工具误调用
回答不稳定
```

正确：

```plain
先路由，再选择能力
```

---

# 三十四、30｜常见错误二：RAG Tool 返回太长
错误：

```plain
search_knowledge_base 返回大量文档全文
```

问题：

```plain
Agent 上下文太长
成本高
模型抓不住重点
```

正确：

```plain
只返回必要答案 + sources + 少量 preview
```

---

# 三十五、31｜常见错误三：没有区分业务事实和知识规则
业务事实：

```plain
订单 10002 当前待发货
```

知识规则：

```plain
订单未发货可以取消并退款
```

两者来源不同：

```plain
业务事实来自 query_order
知识规则来自 search_knowledge_base
```

---

## 【重点内容】
Agent 最终回答时，最好区分这两类来源。

比如：

```plain
我先帮您查到订单 10002 当前是已付款、待发货状态。
根据售后规则，订单未发货时可以申请取消订单并退款。
```

这样用户更容易理解。

---

# 三十六、32｜常见错误四：只依赖 Prompt 防止编造
错误：

```plain
Prompt 写“不要编造”，就以为安全了。
```

正确：

```plain
Prompt + Tool 结果 + 后端校验 + sources 约束
```

---

# 三十七、33｜常见错误五：RAG 索引没初始化
现象：

```plain
Agent 调用了 search_knowledge_base
但返回空结果或报错
```

解决：

```plain
1. 启动前 rebuild index
2. Service 里 ensure_rag_index
3. 检查 Chroma 目录
4. 检查文档是否加载
5. 检查 chunk 是否写入
```

---

# 三十八、34｜常见错误六：知识库工具没有注册进 Agent
错误：

```python
tools = [
    query_order_tool,
    query_logistics_tool,
    transfer_human_tool,
]
```

缺少：

```python
search_knowledge_base_tool
```

正确：

```python
tools = [
    query_order_tool,
    query_logistics_tool,
    transfer_human_tool,
    search_knowledge_base_tool,
]
```

---

# 三十九、35｜常见错误七：Agent 调了 RAG，但最终回答没引用来源
解决：

```plain
1. RAG Tool 返回 sources
2. parse_agent_rag_result 提取 sources
3. API response 返回 sources
4. 前端展示 sources
5. 不完全依赖模型在 answer 中写引用
```

---

# 四十、36｜Agent + RAG 优化方向
后续可以优化：

```plain
1. 意图识别路由
2. Query Rewrite
3. Multi-query Retrieval
4. Hybrid Search
5. Rerank
6. Metadata Filter
7. 权限过滤
8. RAG Tool 缓存
9. Agent 最大步数限制
10. LangGraph 显式流程控制
11. Human-in-the-loop
12. RAG Evaluation
```

---

## 【重点内容】
这一章只是把 Agent 和 RAG 合起来。

但真正企业级 Agent + RAG 会继续优化。

比如先用意图识别判断是否需要知识库。

比如用 rerank 提升召回质量。

比如用 LangGraph 控制固定流程。

这些都是后续课程重点。

---

# 四十一、37｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Agent + RAG | 第 26 章 Agent + 第 27 章 RAG |
| search_knowledge_base_tool | 第 27 章 RAG Tool |
| query_order_tool | 第 25 章 Tool |
| create_agent | 第 26 章 Agent |
| sources / citations | 第 27 章 RAG 引用 |
| used_rag | Agent 是否调用知识库 |
| used_tools | Agent 是否调用工具 |
| AgentRAGService | 第 19 章项目一服务分层 |
| Structured Output 路由 | 第 24 章意图识别 |
| Agent Streaming | 第 26 章 Streaming |
| LangGraph 显式流程 | 后续 LangGraph 阶段 |


---

# 四十二、38｜本章完整复习
这一章我们完成了：

```plain
1. 理解为什么 Agent 需要 RAG
2. 理解为什么 RAG 可以作为 Tool
3. 理解 Agent + RAG 和普通 RAG 的区别
4. 理解 Agent + RAG 和普通 Agent 的区别
5. 理解 Agent + RAG 总体架构
6. 创建 langchain_agent_rag 目录
7. 实现 ensure_rag_index
8. 定义 AgentRAGMessageItem
9. 定义 AgentRAGSource
10. 定义 AgentRAGRunResponse
11. 创建 build_ecommerce_agent_with_rag
12. 把 query_order / query_logistics / transfer_human 加入 Agent
13. 把 search_knowledge_base_tool 加入 Agent
14. 实现 parse_agent_rag_result
15. 从 ToolMessage 中提取 sources
16. 编写最小 Agent + RAG 示例
17. 编写订单 + 售后规则综合示例
18. 理解 Agent 可能不按预期调用工具
19. 理解 Agent + RAG Prompt 设计重点
20. 实现 LangChainAgentRAGService
21. 创建 Agent + RAG Service 测试脚本
22. 创建 Agent + RAG API
23. 注册 Router
24. 测试 Agent + RAG API
25. 编写 Agent + RAG Streaming 示例
26. 理解前端如何展示 answer / tools / sources
27. 理解项目一如何接入 Agent + RAG
28. 理解为什么要用 Structured Output 做前置路由
29. 理解如何避免 Agent 编造知识库内容
30. 理解如何保留 citations
31. 理解 Agent + RAG 工具选择问题
32. 理解为什么复杂流程要升级 LangGraph
33. 总结 Agent + RAG 常见错误
34. 总结 Agent + RAG 优化方向
```

---

# 四十三、39｜课后任务一：跑通最小 Agent + RAG
要求：

```plain
1. 运行 scripts/test_lc28_agent_rag_basic.py
2. 输入“订单未发货时可以退款吗？”
3. 查看 Agent 是否调用 search_knowledge_base
4. 查看 used_rag 是否为 true
5. 查看 sources 是否包含 ecommerce_after_sales
```

---

# 四十四、40｜课后任务二：跑通订单 + 售后规则综合问题
输入：

```plain
我的订单 10002 还没发货，这种情况可以退款吗？
```

要求：

```plain
1. 查看是否调用 query_order
2. 查看是否调用 search_knowledge_base
3. 最终回答要同时包含订单状态和售后规则
4. 不允许编造物流信息
5. sources 中要有售后规则引用
```

---

# 四十五、41｜课后任务三：测试只查订单问题
输入：

```plain
帮我查一下订单 10001 到哪了？
```

要求：

```plain
1. Agent 应该调用 query_order
2. 不一定需要调用 search_knowledge_base
3. used_tools=true
4. used_rag 可以是 false
5. 最终回答基于订单工具结果
```

---

# 四十六、42｜课后任务四：测试只查知识库问题
输入：

```plain
第 20 到 28 章属于什么阶段？
```

要求：

```plain
1. Agent 应该调用 search_knowledge_base
2. 不需要调用 query_order
3. sources 应该包含 ai_agent_course
4. 最终回答是 LangChain 阶段
```

---

# 四十七、43｜课后任务五：优化 Agent + RAG Prompt
如果 Agent 没有按预期调用工具，要求优化：

```plain
1. build_ecommerce_agent_with_rag 里的 system_prompt
2. search_knowledge_base_tool description
3. query_order_tool description
4. query_logistics_tool description
```

目标：

```plain
规则类问题优先查知识库
订单类问题优先查订单
混合问题两个都查
```

---

# 四十八、44｜课后任务六：把 Agent + RAG 接入 ChatService
要求：

```plain
1. ChatService 判断 prompt_scenario=ecommerce_customer_service
2. 调用 langchain_agent_rag_service.run_ecommerce_agent_rag
3. 返回 ChatResponse
4. sources 映射成 SourceDocument
5. metadata 包含 agent_rag、used_tools、used_rag、tool_calls、agent_messages
```

---

# 四十九、45｜课后任务七：实现前端展示
前端需要展示：

```plain
1. 最终回答 answer
2. 使用工具 used_tools
3. 是否使用知识库 used_rag
4. tool_calls
5. sources
```

建议 UI：

```plain
回答区：
展示最终 answer

工具区：
展示 query_order / search_knowledge_base 等调用

引用区：
展示 document_id / source / content_preview
```

---

# 五十、46｜课后任务八：设计 Agent + RAG 路由策略
要求设计：

```plain
general_chat
  -> 普通 Chat

rag_qa
  -> RAG

ecommerce_customer_service
  -> Agent + RAG

human_service
  -> 转人工

refund
  -> Agent + RAG + 人工确认
```

---

# 五十一、47｜课后任务九：画出 Agent + RAG 调用链路
画出：

```plain
POST /api/v1/langchain/agent-rag/ecommerce/chat
```

完整链路：

```plain
HTTP Request
 ↓
Agent RAG Router
 ↓
LangChainAgentRAGService
 ↓
ensure_rag_index
 ↓
build_ecommerce_agent_with_rag
 ↓
create_agent
 ↓
Tools:
  query_order
  query_logistics
  transfer_human
  search_knowledge_base
 ↓
agent.ainvoke
 ↓
Model Node
 ↓
Tool Calls
 ↓
Business Tool / RAG Tool
 ↓
ToolMessage
 ↓
Model Node
 ↓
Final AIMessage
 ↓
parse_agent_rag_result
 ↓
answer + tool_calls + sources
 ↓
ApiResponse
```

---

# 五十二、48｜本章总结
## 【重点内容】
好了，到这里，第 28 章我们就讲完了。

这一章我们把第 26 章 Agent 和第 27 章 RAG 合在了一起。

大家一定要记住：

```plain
Agent 负责决策和编排
RAG 负责查企业知识库
业务 Tool 负责查业务系统
```

Agent + RAG 的核心价值是：

```plain
既能查业务事实
又能查知识规则
最后综合回答用户
```

比如用户问：

```plain
我的订单 10002 还没发货，这种情况可以退款吗？
```

系统需要：

```plain
query_order 查订单状态
search_knowledge_base 查退款规则
Agent 综合生成客服回复
```

这就是企业级 AI Agent 的雏形。

但是也要记住：

```plain
Agent + RAG 不等于完全可控
```

如果流程复杂、顺序固定、需要人工确认、需要状态持久化，就要进入 LangGraph。

到这里，LangChain 阶段基本完成了：

```plain
Model
Message
Prompt
Structured Output
Tool
Agent
RAG
Agent + RAG
```

下一阶段，我们会正式进入 LangGraph。

---
