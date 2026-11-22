---
title: "第 27 章｜LangChain RAG"
chapter: "27"
source: "第 27 章｜LangChain RAG.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - langchain
  - rag
  - retriever
---

# 第 27 章｜LangChain RAG

> [!abstract] 本章重点
>
> - ==RAG = 先检索资料，再让模型照着答== — 不改模型参数，也能回答私有知识。
> - ==Document 带 content 和 metadata== — 来源、页码靠 metadata 保留，回答才能标出处。
> - ==Chunk 切分质量直接决定检索质量== — 太大塞不下，太小丢语义。
> - ==Retriever 把检索包装成标准组件== — 可以直接接进 LCEL 链。
> - ==RAG 和 Tool Calling 可以叠加== — 把检索做成一个工具，由 Agent 决定何时查。

> [!note] 大白话
>
> - **RAG**：开卷考试：先翻资料，再组织答案。

> [!info] 导航与来源
> - 原始讲义：[[第 27 章｜LangChain RAG|打开原始讲义]]
> - [[第 26 章｜LangChain Agent|上一章｜第 26 章]]
> - [[第 28 章｜LangChain Agent + RAG|下一章｜第 28 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章版本口径]]
- [[#四、本章最终项目结构]]
- [[#五、01｜本章开场]]
- [[#六、02｜RAG 一句话解释]]
- [[#七、03｜普通 Chat 和 RAG 的区别]]
- [[#八、04｜RAG 和 Tool Calling 的关系]]
- [[#九、05｜LangChain RAG 核心组件]]
- [[#十、06｜创建 langchain_rag 目录]]
- [[#十一、07｜准备本地知识库文档]]
- [[#十二、08｜Document 是什么]]
- [[#十三、09｜实现文档加载]]
- [[#十四、10｜测试 Document 加载]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

==前面我们已经完成了 LangChain 阶段的几个核心模块：==

```text
第 20 章｜为什么需要 LangChain
第 21 章｜LangChain 核心架构
第 22 章｜LangChain Model 与 Message
第 23 章｜LangChain Prompt
第 24 章｜LangChain Structured Output
第 25 章｜LangChain Tool
第 26 章｜LangChain Agent
```

第 26 章我们已经能做电商客服 Agent：

```text
用户问题
 ↓
Agent 判断是否需要工具
 ↓
调用 query_order / query_logistics
 ↓
拿到工具结果
 ↓
生成最终回答
```

这一章进入另一个非常核心的 AI 应用能力：

## RAG
也就是：

```text
Retrieval Augmented Generation
检索增强生成
```

简单理解：

**不要让模型只靠自己的记忆回答，而是先从企业知识库里检索相关内容，再让模型基于检索内容回答。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. RAG 到底是什么
2. 为什么企业 AI 应用必须学 RAG
3. RAG 和普通 Chat 的区别
4. RAG 和 Tool Calling 的关系
5. LangChain Document 是什么
6. Document.page_content 和 metadata 怎么用
7. Text Splitter 是什么
8. RecursiveCharacterTextSplitter 怎么用
9. Chunk Size 和 Chunk Overlap 怎么选
10. Embedding 是什么
11. VectorStore 是什么
12. Chroma 在本地 RAG Demo 中怎么用
13. Retriever 是什么
14. vectorstore.as_retriever 怎么用
15. Prompt + Retriever + Model 怎么组成 RAG Chain
16. 如何返回引用来源 citations
17. 如何实现最小企业知识库问答
18. 如何把 RAG 做成 Tool 给 Agent 使用
19. 如何把 RAG 接入第 19 章 AI Chat 项目
20. RAG 常见错误和优化方向
```

---

## 三、本章版本口径
本课程 LangChain 阶段统一使用：

```text
Python：3.12+
Pydantic：v2
LangChain：1.3.x
langchain-core：1.5.x
langchain-openai：1.5.x
LangGraph：1.2.x
```

本章新增依赖：

```bash
uv add "langchain-text-splitters" \
       "langchain-chroma" \
       "chromadb"
```

如果使用真实 OpenAI Embedding：

```bash
uv add "langchain-openai"
```

这一章为了让学员不配置 Embedding Key 也能跑通，会先实现一个教学用的本地 `SimpleHashEmbeddings`。

---

### 【重点内容】
这里先说明一下。

真实企业项目里，Embedding 一般会用模型服务商提供的 embedding 模型，比如 OpenAI、Qwen、bge、m3e、本地 embedding 服务等。

但是课程演示时，如果一开始就要求学员配置 embedding key，会增加门槛。

==所以这一章先提供一个本地教学版：==

```text
SimpleHashEmbeddings
```

它不是生产级 embedding，只是为了让 RAG 流程完整跑起来。

等后面企业知识库阶段，再切换到真正的 embedding 模型和 pgvector。

LangChain 的 Embedding 集成文档说明，LangChain 通过统一 `Embeddings` 接口接入不同文本 embedding 模型；向量库文档也说明，可以把 `Document` 添加到 vector store，再执行 similarity search。

---

## 四、本章最终项目结构
本章新增目录：

```text
ai-agent-course/
├── app/
│   ├── langchain_rag/
│   │   ├── __init__.py
│   │   ├── documents.py
│   │   ├── embeddings.py
│   │   ├── splitters.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   ├── prompts.py
│   │   ├── chains.py
│   │   ├── tools.py
│   │   ├── service.py
│   │   ├── demo_documents.py
│   │   ├── demo_splitter.py
│   │   ├── demo_vector_store.py
│   │   ├── demo_retriever.py
│   │   ├── demo_rag_chain.py
│   │   └── demo_rag_tool.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── langchain_rag.py
│   │
│   └── ...
│
├── data/
│   └── knowledge_base/
│       ├── employee_handbook.md
│       ├── ecommerce_after_sales.md
│       └── ai_agent_course.md
│
├── scripts/
│   ├── test_lc27_documents.py
│   ├── test_lc27_splitter.py
│   ├── test_lc27_vector_store.py
│   ├── test_lc27_retriever.py
│   ├── test_lc27_rag_chain.py
│   ├── test_lc27_rag_service.py
│   └── test_lc27_rag_tool.py
│
└── README.md
```

---

## 五、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 27 章。

这一章我们讲 LangChain RAG。

RAG 是企业 AI 应用里非常重要的一块。

为什么？

因为大模型本身有几个明显问题。

第一，它不知道你企业内部的私有知识。

比如：

```text
公司年假制度
售后规则
内部 SOP
产品手册
培训资料
项目文档
```

这些内容不在通用模型的训练数据里。

第二，它的知识可能过期。

第三，它可能会编造。

如果用户问：

```text
我们公司试用期年假怎么算？
```

你不能让模型凭空回答。

正确做法是：

```text
先去企业知识库检索相关制度
再把制度片段交给模型
让模型基于片段回答
```

这就是 RAG。

---

## 六、02｜RAG 一句话解释
### 【实操】
```text
RAG
=
先检索
再生成
```

完整链路：

```text
用户问题
 ↓
Retriever 检索相关文档
 ↓
把文档片段拼进 Prompt
 ↓
LLM 基于文档生成答案
 ↓
返回答案 + 引用来源
```

---

### 【重点内容】
RAG 最简单的解释就是：

先查资料，再回答。

普通 Chat 是：

```text
用户问
 ↓
模型直接回答
```

RAG 是：

```text
用户问
 ↓
先从知识库查相关资料
 ↓
把资料交给模型
 ↓
模型基于资料回答
```

==所以 RAG 的重点不是让模型更聪明。==

而是让模型回答时有依据。

---

## 七、03｜普通 Chat 和 RAG 的区别
| 对比项 | 普通 Chat | RAG |
| --- | --- | --- |
| 知识来源 | 模型自身参数 | 外部知识库 |
| 是否能回答企业私有知识 | 不可靠 | 可以 |
| 是否能引用来源 | 通常没有 | 可以 |
| 是否容易编造 | 更容易 | 可降低 |
| 是否需要文档处理 | 不需要 | 需要 |
| 是否需要向量库 | 不需要 | 通常需要 |
| 典型场景 | 通用问答 | 企业知识库、客服知识库、制度问答 |


---

### 【重点内容】
普通 Chat 和 RAG 最大区别是知识来源。

普通 Chat 的知识在模型参数里。

RAG 的知识在外部知识库里。

比如公司制度这种东西，模型不可能天然知道。

所以企业 AI 问答系统，不能只做 Chat。

一定要做 RAG。

---

## 八、04｜RAG 和 Tool Calling 的关系
### 【实操】
```text
RAG 可以看成一种特殊 Tool

search_knowledge_base(query)
 ↓
返回相关文档
 ↓
模型基于文档回答
```

---

### 【重点内容】
RAG 和 Tool Calling 不是对立关系。

RAG 本质上也可以封装成工具。

比如：

```text
search_knowledge_base
```

当用户问企业制度时，Agent 可以调用这个工具。

==所以后面我们会把 RAG 做成 Tool，接入 Agent。==

这样 Agent 就有了知识库能力。

---

## 九、05｜LangChain RAG 核心组件

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

### 【实操】
```text
Document
  ↓
Text Splitter
  ↓
Embedding
  ↓
VectorStore
  ↓
Retriever
  ↓
Prompt
  ↓
Model
  ↓
Answer
```

---

### 【重点内容】
LangChain 里的 RAG，可以拆成几个组件。

第一个是 Document。

它表示一段文档内容和元数据。

第二个是 Text Splitter。

它把长文档切成小 chunk。

第三个是 Embedding。

它把文本变成向量。

第四个是 VectorStore。

它保存向量和文档。

第五个是 Retriever。

它根据用户问题查相关文档。

第六个是 Prompt。

它把文档和用户问题拼起来。

第七个是 Model。

它基于上下文生成答案。

==这就是最小 RAG 链路。==

---

## 十、06｜创建 langchain_rag 目录
执行：

```bash
mkdir -p app/langchain_rag
mkdir -p data/knowledge_base

touch app/langchain_rag/__init__.py
touch app/langchain_rag/documents.py
touch app/langchain_rag/embeddings.py
touch app/langchain_rag/splitters.py
touch app/langchain_rag/vector_store.py
touch app/langchain_rag/retriever.py
touch app/langchain_rag/prompts.py
touch app/langchain_rag/chains.py
touch app/langchain_rag/tools.py
touch app/langchain_rag/service.py
touch app/langchain_rag/demo_documents.py
touch app/langchain_rag/demo_splitter.py
touch app/langchain_rag/demo_vector_store.py
touch app/langchain_rag/demo_retriever.py
touch app/langchain_rag/demo_rag_chain.py
touch app/langchain_rag/demo_rag_tool.py
```

Windows PowerShell：

```powershell
mkdir app\langchain_rag
mkdir data\knowledge_base

New-Item app\langchain_rag\__init__.py
New-Item app\langchain_rag\documents.py
New-Item app\langchain_rag\embeddings.py
New-Item app\langchain_rag\splitters.py
New-Item app\langchain_rag\vector_store.py
New-Item app\langchain_rag\retriever.py
New-Item app\langchain_rag\prompts.py
New-Item app\langchain_rag\chains.py
New-Item app\langchain_rag\tools.py
New-Item app\langchain_rag\service.py
New-Item app\langchain_rag\demo_documents.py
New-Item app\langchain_rag\demo_splitter.py
New-Item app\langchain_rag\demo_vector_store.py
New-Item app\langchain_rag\demo_retriever.py
New-Item app\langchain_rag\demo_rag_chain.py
New-Item app\langchain_rag\demo_rag_tool.py
```

---

## 十一、07｜准备本地知识库文档
创建：

```text
data/knowledge_base/employee_handbook.md
```

写入：

```markdown
# 员工手册

## 年假制度

员工入职满一年后，每年享有 5 天带薪年假。

员工入职满三年后，每年享有 10 天带薪年假。

员工申请年假需要提前 3 个工作日提交申请，并经过直属主管审批。

## 病假制度

员工请病假需要在当天上午 10 点前提交申请。

连续请病假 3 天及以上，需要提供医院证明。

## 远程办公制度

员工每周最多可以申请 2 天远程办公。

远程办公需要提前一天在系统中申请，并说明工作计划。
```

创建：

```text
data/knowledge_base/ecommerce_after_sales.md
```

写入：

```markdown
# 跨境电商售后规则

## 发货规则

普通商品付款后 48 小时内发货。

预售商品以商品详情页标注的发货时间为准。

海外仓商品通常 3 到 7 个工作日送达。

## 退款规则

订单未发货时，用户可以申请取消订单并退款。

订单已发货后，需要用户收到商品后再发起退货退款申请。

生鲜、定制类商品不支持无理由退货。

## 物流查询

用户提供订单号后，可以查询订单状态和物流信息。

如果订单已经发货，系统会返回物流公司、物流单号和最新物流节点。

如果没有查询到订单，建议用户检查订单号是否正确。
```

创建：

```text
data/knowledge_base/ai_agent_course.md
```

写入：

```markdown
# AI Agent 全栈开发课程说明

## 课程阶段

第 1 到 5 章是 Python 基础阶段。

第 6 到 12 章是 FastAPI、PostgreSQL、Redis 后端基础阶段。

第 13 到 19 章是原生大模型 API 和项目一 AI Chat 聊天系统阶段。

第 20 到 28 章是 LangChain 阶段。

第 29 到 38 章是 LangGraph 阶段。

第 39 到 45 章是 RAG 企业知识库阶段。

## 项目一

项目一是 AI Chat 聊天系统。

它支持会话管理、普通 Chat、Streaming Chat、Prompt 场景、Redis 缓存、PostgreSQL 消息保存和电商客服 Tool Calling。

## 项目二

项目二是 LangGraph 电商客服 Agent。

它会使用 LangGraph 的 State、Node、Edge、Conditional Routing 和 Persistence。
```

---

### 【重点内容】
为了让这一章可以本地跑通，我们先准备三份 Markdown 文档。

它们分别模拟：

```text
员工手册
电商售后规则
AI Agent 课程说明
```

==这就是我们的本地知识库。==

真实企业项目里，这些文档可能来自：

```text
PDF
Word
Excel
网页
飞书文档
Notion
Confluence
数据库
对象存储
```

这一章先用 Markdown，降低复杂度。

---

## 十二、08｜Document 是什么
LangChain 的 Document 包含：

```text
page_content：文本内容
metadata：元数据
```

示例：

```python
from langchain_core.documents import Document

doc = Document(
    page_content="员工入职满一年后，每年享有 5 天带薪年假。",
    metadata={
        "source": "employee_handbook.md",
        "document_id": "doc_employee_001",
    },
)
```

LangChain 的知识库教程使用 `Document` 表示可检索内容；Retriever 接收字符串 query 后返回 `Document` 列表。

---

### 【重点内容】
Document 是 RAG 的基础数据结构。

它不是数据库表。

它是 LangChain 里表示文档片段的对象。

最重要两个字段：

```text
page_content
metadata
```

`page_content` 是正文。

`metadata` 放来源、文件名、页码、文档 ID、业务标签等信息。

后面引用来源 citations，就是从 metadata 里拿。

---

## 十三、09｜实现文档加载
打开：

```text
app/langchain_rag/documents.py
```

写入：

```python
from pathlib import Path

from langchain_core.documents import Document


KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")


def load_markdown_documents(
    base_dir: Path = KNOWLEDGE_BASE_DIR,
) -> list[Document]:
    documents: list[Document] = []

    for file_path in sorted(base_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")

        document_id = file_path.stem

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "document_id": document_id,
                    "file_type": "markdown",
                },
            )
        )

    return documents


def print_documents(documents: list[Document]):
    for index, doc in enumerate(documents, start=1):
        print(f"Document {index}")
        print("metadata:", doc.metadata)
        print("content preview:", doc.page_content[:120])
        print("=" * 80)
```

---

## 十四、10｜测试 Document 加载
打开：

```text
app/langchain_rag/demo_documents.py
```

写入：

```python
from app.langchain_rag.documents import (
    load_markdown_documents,
    print_documents,
)


def main():
    documents = load_markdown_documents()

    print("documents count:", len(documents))
    print_documents(documents)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc27_documents.py
```

写入：

```python
from app.langchain_rag.demo_documents import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc27_documents.py
```

---

### 【重点内容】
这一步只做文档加载。

我们把 Markdown 文件读出来，转成 LangChain Document。

注意 metadata 非常重要。

如果没有 metadata，后面回答时就不知道引用来源。

==所以企业 RAG 一定要保留：==

```text
document_id
source
file_name
page
section
created_at
owner
permission
```

这些后面都可能用到。

---

## 十五、11｜Text Splitter 是什么
### 【实操】
```text
长文档
 ↓
Text Splitter
 ↓
多个 chunk
```

为什么要切分？

```text
1. 长文档放不进模型上下文
2. 向量检索需要更细粒度片段
3. 检索结果越精准，回答越稳定
4. 引用来源更明确
```

LangChain Text Splitter 文档说明，文本切分器会把大文档拆成更小的 chunk，使它们可以被单独检索，并且更容易适配模型上下文窗口。

---

### 【重点内容】
RAG 里不能把整篇文档都塞进向量库。

比如一个 100 页 PDF，如果整个文档作为一个 Document，检索很粗。

用户问年假制度，可能整篇员工手册都返回。

模型上下文就会浪费很多空间。

所以要切分成 chunk。

比如：

```text
年假制度一个 chunk
病假制度一个 chunk
远程办公一个 chunk
```

这样检索更精准。

---

## 十六、12｜RecursiveCharacterTextSplitter
打开：

```text
app/langchain_rag/splitters.py
```

写入：

```python
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_default_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=[
            "\n## ",
            "\n# ",
            "\n\n",
            "\n",
            "。",
            "，",
            " ",
            "",
        ],
    )


def split_documents(
    documents: list[Document],
) -> list[Document]:
    splitter = create_default_text_splitter()

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata = {
            **chunk.metadata,
            "chunk_id": f"{chunk.metadata.get('document_id', 'doc')}_chunk_{index}",
            "chunk_index": index,
        }

    return chunks


def format_docs(docs: list[Document]) -> str:
    lines = []

    for index, doc in enumerate(docs, start=1):
        document_id = doc.metadata.get("document_id", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "unknown")
        source = doc.metadata.get("source", "unknown")

        lines.append(
            f"[{index}] document_id={document_id}, chunk_id={chunk_id}, source={source}\n"
            f"{doc.page_content}"
        )

    return "\n\n".join(lines)
```

---

### 【重点内容】
这里我们使用：

```python
RecursiveCharacterTextSplitter
```

它会按照分隔符递归切分文本。

本章设置：

```text
chunk_size=500
chunk_overlap=80
```

含义是：

```text
每个 chunk 大约 500 字符
相邻 chunk 重叠 80 字符
```

重叠的作用是避免边界信息丢失。

比如一句话刚好被切断，有 overlap 可以保留上下文。

`RecursiveCharacterTextSplitter` 在 LangChain 文档中通过 `langchain_text_splitters` 包导入，常用于递归切分文档。

---

## 十七、13｜测试 Text Splitter
打开：

```text
app/langchain_rag/demo_splitter.py
```

写入：

```python
from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.splitters import split_documents


def main():
    documents = load_markdown_documents()
    chunks = split_documents(documents)

    print("documents count:", len(documents))
    print("chunks count:", len(chunks))
    print("=" * 80)

    for chunk in chunks:
        print("metadata:", chunk.metadata)
        print("content:")
        print(chunk.page_content[:300])
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc27_splitter.py
```

写入：

```python
from app.langchain_rag.demo_splitter import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc27_splitter.py
```

---

### 【重点内容】
这个脚本验证文档切分效果。

重点看：

```text
chunks count
chunk content
chunk metadata
```

如果 chunk 太大，检索不精准。

如果 chunk 太小，语义不完整。

==所以 chunk_size 要根据文档类型调。==

本章先用 500 字符演示。

后面企业知识库阶段，会继续讲 chunk 优化。

---

## 十八、14｜Embedding 是什么
### 【实操】
```text
文本
 ↓
Embedding Model
 ↓
向量
```

比如：

```text
"员工年假有几天？"
 ↓
[0.12, -0.34, 0.56, ...]
```

---

### 【重点内容】
Embedding 是把文本转换成向量。

为什么要转换成向量？

因为向量可以做相似度计算。

比如用户问：

```text
员工休假有几天？
```

知识库里写的是：

```text
员工入职满一年后，每年享有 5 天带薪年假。
```

虽然文字不完全一样，但语义相近。

Embedding 可以帮助我们找到语义相近的文档。

LangChain 的 Embedding 文档说明，embedding 模型会把文本转换成数字向量，使语义相近的文本在向量空间中更接近。

---

## 十九、15｜实现本地教学版 SimpleHashEmbeddings
打开：

```text
app/langchain_rag/embeddings.py
```

写入：

```python
import hashlib
import math
import re
from collections import Counter

from langchain_core.embeddings import Embeddings


class SimpleHashEmbeddings(Embeddings):
    """
    教学用本地 Embedding。

    说明：
    1. 不需要 API Key。
    2. 可以跑通 RAG 流程。
    3. 不适合生产环境。
    4. 生产环境请替换为 OpenAIEmbeddings / Qwen Embeddings / bge 等。
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self._embed(text)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        counter = Counter(tokens)

        vector = [0.0] * self.dimension

        for token, count in counter.items():
            index = self._hash_to_index(token)
            vector[index] += float(count)

        return self._normalize(vector)

    def _tokenize(self, text: str) -> list[str]:
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
        english_words = re.findall(r"[a-zA-Z0-9_]+", text.lower())

        return chinese_chars + english_words

    def _hash_to_index(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(digest, 16) % self.dimension

    def _normalize(
        self,
        vector: list[float],
    ) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))

        if norm == 0:
            return vector

        return [
            value / norm
            for value in vector
        ]


def create_embeddings() -> Embeddings:
    return SimpleHashEmbeddings(
        dimension=128,
    )
```

---

### 【重点内容】
这里我们自己实现了一个简单 Embedding。

它只是教学用。

它通过字符和词的 hash 生成向量。

优点是：

```text
不需要 key
不需要联网
可以本地跑通流程
```

缺点是：

```text
语义效果很弱
不能代表真实 embedding 质量
不适合生产
```

后面真实项目要替换成 embedding 模型。

==但这一章的重点是先掌握 RAG 链路。==

---

## 二十、16｜VectorStore 是什么
### 【实操】
```text
VectorStore
=
保存：
文本 chunk
chunk 向量
metadata
```

查询：

```text
用户问题
 ↓
Embedding
 ↓
相似度搜索
 ↓
Top K Documents
```

LangChain 的 vector store 文档说明，可以向 vector store 添加 `Document`，再通过 `similarity_search` 查询相似文档；Chroma 集成需要安装 `langchain-chroma` 包。

---

### 【重点内容】
VectorStore 就是向量库。

它保存两类东西：

```text
文本
向量
```

当用户提问时，系统先把问题转成向量。

然后在向量库里找最相似的 chunk。

这就是语义检索。

本章我们用 Chroma 做本地向量库。

后面企业项目会用：

```text
PostgreSQL + pgvector
```

这样更贴近企业部署。

---

## 二十一、17｜创建 Chroma VectorStore
打开：

```text
app/langchain_rag/vector_store.py
```

写入：

```python
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from app.langchain_rag.embeddings import create_embeddings


CHROMA_DIR = Path("data/chroma_langchain_rag")
COLLECTION_NAME = "ai_agent_course_kb"


def create_vector_store() -> Chroma:
    embeddings = create_embeddings()

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def rebuild_vector_store(
    chunks: list[Document],
) -> Chroma:
    if CHROMA_DIR.exists():
        import shutil
        shutil.rmtree(CHROMA_DIR)

    vector_store = create_vector_store()

    ids = [
        chunk.metadata.get("chunk_id", f"chunk_{index}")
        for index, chunk in enumerate(chunks)
    ]

    vector_store.add_documents(
        documents=chunks,
        ids=ids,
    )

    return vector_store


def similarity_search(
    query: str,
    k: int = 4,
) -> list[Document]:
    vector_store = create_vector_store()

    return vector_store.similarity_search(
        query=query,
        k=k,
    )
```

---

### 【重点内容】
这里我们创建 Chroma 向量库。

核心参数：

```text
collection_name
embedding_function
persist_directory
```

`persist_directory` 表示保存到本地目录。

这样第一次构建后，后面可以重复使用。

但是本章为了演示方便，提供了：

```python
rebuild_vector_store
```

每次重建时先删掉旧目录。

---

## 二十二、18｜测试 VectorStore
打开：

```text
app/langchain_rag/demo_vector_store.py
```

写入：

```python
from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.splitters import split_documents
from app.langchain_rag.vector_store import rebuild_vector_store


def main():
    documents = load_markdown_documents()
    chunks = split_documents(documents)

    vector_store = rebuild_vector_store(chunks)

    query = "员工年假有几天？"

    results = vector_store.similarity_search(
        query=query,
        k=3,
    )

    print("query:", query)
    print("=" * 80)

    for doc in results:
        print("metadata:", doc.metadata)
        print("content:")
        print(doc.page_content)
        print("=" * 80)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc27_vector_store.py
```

写入：

```python
from app.langchain_rag.demo_vector_store import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc27_vector_store.py
```

---

### 【重点内容】
这个脚本会完成：

```text
加载文档
切分 chunk
创建向量库
写入向量库
执行 similarity_search
```

如果结果里能看到员工手册年假制度，说明最小检索链路跑通了。

如果没检索到，也不要紧。

因为本章用的是教学版 SimpleHashEmbeddings。

真实 embedding 效果会好很多。

---

## 二十三、19｜Retriever 是什么
### 【实操】
```text
Retriever
=
输入 query
输出 Documents
```

示例：

```python
retriever = vector_store.as_retriever(
    search_kwargs={"k": 4}
)

docs = retriever.invoke("员工年假有几天？")
```

==LangChain retriever 文档说明，retriever 不一定负责存储文档，它的核心职责是接收字符串 query，并返回 `Document` 对象列表。==

---

### 【重点内容】
Retriever 是 RAG 里非常关键的抽象。

它不关心底层是：

```text
向量库
BM25
搜索引擎
数据库
外部 API
Graph RAG
```

它只关心：

```text
给我一个 query
我返回相关 documents
```

所以后面 Agent 里也可以把 Retriever 包成工具。

---

## 二十四、20｜创建 Retriever
打开：

```text
app/langchain_rag/retriever.py
```

写入：

```python
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.langchain_rag.vector_store import create_vector_store


def create_retriever(
    k: int = 4,
) -> BaseRetriever:
    vector_store = create_vector_store()

    return vector_store.as_retriever(
        search_kwargs={
            "k": k,
        }
    )


def retrieve_documents(
    query: str,
    k: int = 4,
) -> list[Document]:
    retriever = create_retriever(k=k)

    return retriever.invoke(query)
```

---

## 二十五、21｜测试 Retriever
打开：

```text
app/langchain_rag/demo_retriever.py
```

写入：

```python
from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.retriever import retrieve_documents
from app.langchain_rag.splitters import split_documents
from app.langchain_rag.vector_store import rebuild_vector_store


def main():
    documents = load_markdown_documents()
    chunks = split_documents(documents)
    rebuild_vector_store(chunks)

    questions = [
        "员工年假有几天？",
        "订单未发货可以退款吗？",
        "第 20 到 28 章属于哪个阶段？",
    ]

    for question in questions:
        print("question:", question)
        print("=" * 80)

        docs = retrieve_documents(
            query=question,
            k=3,
        )

        for doc in docs:
            print("metadata:", doc.metadata)
            print("content preview:", doc.page_content[:300])
            print("-" * 80)

        print("=" * 120)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc27_retriever.py
```

写入：

```python
from app.langchain_rag.demo_retriever import main


if __name__ == "__main__":
    main()
```

---

### 【重点内容】
这个脚本测试三个问题：

```text
年假制度
退款规则
课程阶段
```

每个问题应该检索到不同文档。

==这就是 RAG 的检索阶段。==

注意，Retriever 只负责返回文档。

它不会生成最终答案。

生成答案还要交给模型。

---

## 二十六、22｜RAG Prompt
打开：

```text
app/langchain_rag/prompts.py
```

写入：

```python
from langchain_core.prompts import ChatPromptTemplate


RAG_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "你是一个企业知识库问答助手。\n"
            "\n"
            "回答规则：\n"
            "1. 只能基于提供的知识库上下文回答。\n"
            "2. 如果上下文中没有答案，要明确说“根据当前知识库无法确认”。\n"
            "3. 不要编造制度、数字、流程和政策。\n"
            "4. 回答尽量简洁，先给结论，再说明依据。\n"
            "5. 如果可以回答，要列出引用来源 document_id。\n"
            "\n"
            "知识库上下文：\n"
            "{context}"
        ),
    ),
    (
        "human",
        "用户问题：{question}",
    ),
])
```

---

### 【重点内容】
RAG Prompt 的关键是告诉模型：

```text
只能基于上下文回答
没有答案就说无法确认
不要编造
要返回引用来源
```

这几条非常重要。

如果不限制，模型可能会把自己知道的内容也混进来。

企业知识库问答最怕模型编造制度。

---

## 二十七、23｜创建 RAG Chain
打开：

```text
app/langchain_rag/chains.py
```

写入：

```python
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

from app.langchain_models.model_factory import LangChainModelFactory
from app.langchain_rag.prompts import RAG_PROMPT
from app.langchain_rag.retriever import create_retriever
from app.langchain_rag.splitters import format_docs


def build_rag_chain(
    provider: str = "deepseek",
    model_name: str = "deepseek-chat",
    k: int = 4,
):
    retriever = create_retriever(k=k)

    model = LangChainModelFactory.create(
        provider=provider,
        model=model_name,
        temperature=0,
    )

    parser = StrOutputParser()

    def retrieve_context(inputs: dict[str, Any]) -> dict[str, Any]:
        question = inputs["question"]

        docs = retriever.invoke(question)

        return {
            "question": question,
            "context": format_docs(docs),
            "docs": docs,
        }

    def attach_sources(answer_inputs: dict[str, Any]) -> dict[str, Any]:
        return answer_inputs

    retrieve_runnable = RunnableLambda(retrieve_context)

    answer_chain = RAG_PROMPT | model | parser

    def run_answer(inputs: dict[str, Any]) -> dict[str, Any]:
        answer = answer_chain.invoke({
            "question": inputs["question"],
            "context": inputs["context"],
        })

        sources = []

        for doc in inputs["docs"]:
            sources.append({
                "document_id": doc.metadata.get("document_id"),
                "chunk_id": doc.metadata.get("chunk_id"),
                "source": doc.metadata.get("source"),
                "content_preview": doc.page_content[:160],
            })

        return {
            "answer": answer,
            "sources": sources,
        }

    return retrieve_runnable | RunnableLambda(run_answer)
```

---

### 【重点内容】
这个 RAG Chain 做了两步。

第一步：

```text
Retriever 检索文档
```

第二步：

```text
Prompt + Model + Parser 生成答案
```

最后返回：

```text
answer
sources
```

这里我没有直接用旧版本的一些 chain helper，而是用 RunnableLambda 手动组合。

原因是这样更容易让学员看懂每一步。

---

## 二十八、24｜测试 RAG Chain
打开：

```text
app/langchain_rag/demo_rag_chain.py
```

写入：

```python
import json

from app.langchain_rag.chains import build_rag_chain
from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.splitters import split_documents
from app.langchain_rag.vector_store import rebuild_vector_store


def main():
    documents = load_markdown_documents()
    chunks = split_documents(documents)
    rebuild_vector_store(chunks)

    chain = build_rag_chain(
        provider="deepseek",
        model_name="deepseek-chat",
        k=3,
    )

    result = chain.invoke({
        "question": "员工入职满一年后年假有几天？"
    })

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_lc27_rag_chain.py
```

写入：

```python
from app.langchain_rag.demo_rag_chain import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc27_rag_chain.py
```

---

### 【重点内容】
这个脚本就是最小 RAG 问答。

它会：

```text
构建知识库
检索相关文档
把文档拼进 Prompt
调用模型
返回答案和 sources
```

==这就是企业知识库问答的最小形态。==

---

## 二十九、25｜RAG Service
打开：

```text
app/langchain_rag/service.py
```

写入：

```python
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import AppException, ErrorCode
from app.core.logging import get_logger
from app.langchain_rag.chains import build_rag_chain
from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.splitters import split_documents
from app.langchain_rag.vector_store import rebuild_vector_store


logger = get_logger(__name__)


class RAGSource(BaseModel):
    document_id: str | None = Field(default=None)
    chunk_id: str | None = Field(default=None)
    source: str | None = Field(default=None)
    content_preview: str = Field(default="")


class RAGAnswer(BaseModel):
    answer: str = Field(..., description="RAG 回答")
    sources: list[RAGSource] = Field(
        default_factory=list,
        description="引用来源",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展信息",
    )


class LangChainRAGService:
    def rebuild_index(self) -> dict:
        documents = load_markdown_documents()
        chunks = split_documents(documents)

        rebuild_vector_store(chunks)

        return {
            "document_count": len(documents),
            "chunk_count": len(chunks),
        }

    def ask(
        self,
        question: str,
        provider: str = "deepseek",
        model_name: str = "deepseek-chat",
        k: int = 4,
    ) -> RAGAnswer:
        logger.info(
            f"langchain_rag_ask_start model={model_name} k={k}"
        )

        try:
            chain = build_rag_chain(
                provider=provider,
                model_name=model_name,
                k=k,
            )

            result = chain.invoke({
                "question": question,
            })

        except Exception as exc:
            logger.exception("langchain_rag_ask_failed")

            raise AppException(
                message="LangChain RAG 问答失败",
                code=ErrorCode.LLM_CALL_FAILED,
                status_code=500,
                data={
                    "error": repr(exc),
                    "provider": provider,
                    "model": model_name,
                },
            ) from exc

        sources = [
            RAGSource(**item)
            for item in result.get("sources", [])
        ]

        return RAGAnswer(
            answer=result["answer"],
            sources=sources,
            metadata={
                "provider": provider,
                "model": model_name,
                "k": k,
                "source_count": len(sources),
            },
        )


langchain_rag_service = LangChainRAGService()
```

---

### 【重点内容】
这里我们封装 RAGService。

它提供两个核心方法：

```text
rebuild_index
ask
```

`rebuild_index` 用来重建知识库索引。

`ask` 用来问答。

真实企业项目里，这两个能力通常分开。

比如：

```text
后台管理系统负责上传文档、构建索引
用户问答接口只负责查询
```

这一章先放在一个 Service 里，方便演示。

---

## 三十、26｜测试 RAG Service
创建：

```text
scripts/test_lc27_rag_service.py
```

写入：

```python
import json

from app.langchain_rag.service import langchain_rag_service


def main():
    index_result = langchain_rag_service.rebuild_index()
    print("index_result:")
    print(json.dumps(index_result, ensure_ascii=False, indent=2))
    print("=" * 80)

    answer = langchain_rag_service.ask(
        question="订单未发货时可以退款吗？",
        provider="deepseek",
        model_name="deepseek-chat",
        k=3,
    )

    print(answer.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_lc27_rag_service.py
```

---

## 三十一、27｜创建 RAG API
创建：

```text
app/api/v1/langchain_rag.py
```

写入：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.langchain_rag.service import RAGAnswer, langchain_rag_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class RAGAskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    provider: str = Field(default="deepseek", description="模型供应商")
    model: str = Field(default="deepseek-chat", description="模型名称")
    k: int = Field(default=4, ge=1, le=10, description="检索数量")


@router.post(
    "/langchain/rag/rebuild-index",
    response_model=ApiResponse[dict],
)
async def rebuild_rag_index(
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = langchain_rag_service.rebuild_index()

    return ApiResponse[dict](
        data=result
    )


@router.post(
    "/langchain/rag/ask",
    response_model=ApiResponse[RAGAnswer],
)
async def rag_ask(
    request: RAGAskRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[RAGAnswer]:
    result = langchain_rag_service.ask(
        question=request.question,
        provider=request.provider,
        model_name=request.model,
        k=request.k,
    )

    return ApiResponse[RAGAnswer](
        data=result
    )
```

---

## 三十二、28｜注册 RAG Router
打开：

```text
app/api/v1/api.py
```

增加：

```python
from app.api.v1.langchain_rag import router as langchain_rag_router
```

注册：

```python
api_router.include_router(
    langchain_rag_router,
    tags=["LangChain RAG"],
)
```

---

## 三十三、29｜测试 RAG API
启动：

```bash
uv run uvicorn app.main:app --reload
```

先重建索引：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/rag/rebuild-index" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei"
```

再问答：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/langchain/rag/ask" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "question": "员工入职满一年后年假有几天？",
    "provider": "deepseek",
    "model": "deepseek-chat",
    "k": 3
  }'
```

预期：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "员工入职满一年后，每年享有 5 天带薪年假。依据来源：employee_handbook。",
    "sources": [
      {
        "document_id": "employee_handbook",
        "chunk_id": "employee_handbook_chunk_0",
        "source": "data/knowledge_base/employee_handbook.md",
        "content_preview": "..."
      }
    ],
    "metadata": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "k": 3,
      "source_count": 3
    }
  }
}
```

---

## 三十四、30｜把 RAG 做成 Tool
打开：

```text
app/langchain_rag/tools.py
```

写入：

```python
import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.langchain_rag.service import langchain_rag_service


class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="用户问题或检索关键词",
    )


async def search_knowledge_base(query: str) -> str:
    """
    搜索企业知识库，并返回基于知识库的回答和引用来源。
    """
    result = langchain_rag_service.ask(
        question=query,
        provider="deepseek",
        model_name="deepseek-chat",
        k=4,
    )

    return json.dumps(
        result.model_dump(),
        ensure_ascii=False,
    )


search_knowledge_base_tool = StructuredTool.from_function(
    coroutine=search_knowledge_base,
    name="search_knowledge_base",
    description=(
        "搜索企业知识库。当用户询问公司制度、售后规则、课程阶段、内部文档内容时使用。"
        "如果知识库没有相关内容，应说明无法从知识库确认，不要编造。"
    ),
    args_schema=SearchKnowledgeBaseArgs,
)
```

---

### 【重点内容】
这里我们把 RAG 封装成了工具：

```text
search_knowledge_base
```

这样 Agent 就可以调用知识库。

这非常重要。

因为真实 Agent 不只是会查订单。

它还要能查企业知识库。

比如：

```text
公司年假制度
售后退款规则
课程章节说明
产品使用文档
```

---

## 三十五、31｜测试 RAG Tool
打开：

```text
app/langchain_rag/demo_rag_tool.py
```

写入：

```python
import asyncio

from app.langchain_rag.documents import load_markdown_documents
from app.langchain_rag.splitters import split_documents
from app.langchain_rag.tools import search_knowledge_base_tool
from app.langchain_rag.vector_store import rebuild_vector_store


async def main():
    documents = load_markdown_documents()
    chunks = split_documents(documents)
    rebuild_vector_store(chunks)

    result = await search_knowledge_base_tool.ainvoke({
        "query": "第 20 到 28 章属于什么阶段？"
    })

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

创建脚本：

```text
scripts/test_lc27_rag_tool.py
```

写入：

```python
import asyncio

from app.langchain_rag.demo_rag_tool import main


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_lc27_rag_tool.py
```

---

## 三十六、32｜项目一如何接入 RAG
第 19 章项目可以这样升级：

```text
ChatService
 ↓
如果 prompt_scenario=rag_qa
 ↓
调用 langchain_rag_service.ask
 ↓
返回 ChatResponse
```

示例：

```python
from app.langchain_rag.service import langchain_rag_service


if request.prompt_scenario == "rag_qa":
    rag_result = langchain_rag_service.ask(
        question=latest_user_message,
        provider="deepseek",
        model_name=model,
        k=4,
    )

    return ChatResponse(
        answer=rag_result.answer,
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
            for source in rag_result.sources
        ],
        trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        metadata={
            "rag": True,
            "source_count": len(rag_result.sources),
        },
    )
```

---

### 【重点内容】
这样第 19 章项目就多了一个场景：

```text
rag_qa
```

普通聊天走 general_chat。

电商客服走 Agent 或 Tool Calling。

知识库问答走 RAG。

同一个 `/chat` 接口，根据场景走不同能力。

==这就是 AI 应用平台的雏形。==

---

## 三十七、33｜RAG 和 Agent 如何结合
Agent 可以绑定：

```text
search_knowledge_base_tool
query_order_tool
query_logistics_tool
transfer_human_tool
```

这样它既能查知识库，也能查业务系统。

比如用户问：

```text
订单未发货时能退款吗？我的订单号是 10002。
```

理想流程：

```text
调用 search_knowledge_base 查询退款规则
 ↓
调用 query_order 查询订单状态
 ↓
结合规则和订单状态生成回答
```

---

### 【重点内容】
这就是 Agent + RAG 的价值。

RAG 负责知识。

Tool 负责业务操作。

Agent 负责决策和编排。

下一章：

```text
第 28 章｜LangChain Agent + RAG
```

我们就会把这两个能力组合起来。

---

## 三十八、34｜RAG 常见错误一：把整篇文档塞给模型

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
把整个员工手册直接放进 Prompt
```

问题：

```text
上下文太长
成本高
模型抓不住重点
引用不精准
```

正确：

```text
先切 chunk
再检索 Top K
只把相关 chunk 放进 Prompt
```

---

## 三十九、35｜RAG 常见错误二：Chunk 太大或太小
Chunk 太大：

```text
检索不精准
上下文浪费
```

Chunk 太小：

```text
语义不完整
回答缺上下文
```

建议：

```text
根据文档类型调 chunk_size
保留适当 chunk_overlap
用真实问题测试召回效果
```

---

## 四十、36｜RAG 常见错误三：没有 metadata

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
Document(page_content="员工年假 5 天")
```

正确：

```python
Document(
    page_content="员工年假 5 天",
    metadata={
        "document_id": "employee_handbook",
        "source": "employee_handbook.md",
        "section": "年假制度",
    },
)
```

---

### 【重点内容】
没有 metadata，就没有引用来源。

==企业知识库问答必须能回答：==

```text
依据来自哪份文档？
哪一页？
哪个章节？
哪个版本？
```

所以 metadata 是 RAG 工程化的关键。

---

## 四十一、37｜RAG 常见错误四：只看生成答案，不看召回结果
如果 RAG 答错，不要只怪模型。

先看：

```text
Retriever 有没有召回正确文档
Top K 是否合理
chunk 是否切得正确
query 是否需要改写
embedding 是否适合中文
metadata 是否丢失
```

---

### 【重点内容】
RAG 的问题通常分两类。

第一类是召回问题。

也就是没找到对的文档。

第二类是生成问题。

也就是找到文档了，但模型回答错。

排查时先看召回。

如果召回文档都不对，模型不可能答对。

---

## 四十二、38｜RAG 常见错误五：模型编造引用

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误回答：

```text
根据 doc_999，员工年假是 15 天。
```

但知识库没有 doc_999。

解决：

```text
1. Prompt 明确 citations 只能来自 context
2. 后端校验 citations 是否存在
3. 返回 sources 由后端生成，不完全相信模型
```

---

## 四十三、39｜RAG 常见错误六：Embedding 不适合中文
### 【重点内容】
==如果你的知识库主要是中文，embedding 模型一定要支持中文语义。==

本章 SimpleHashEmbeddings 只是教学用。

真实项目建议评估：

```text
中文 embedding 召回效果
跨语言检索效果
领域术语效果
成本和延迟
私有化部署能力
```

后面企业知识库阶段会专门讲 Embedding 选型。

---

## 四十四、40｜RAG 常见错误七：权限没控制
不同用户可能能看不同文档。

比如：

```text
普通员工不能看财务文档
外包员工不能看内部战略
销售不能看人事敏感资料
```

RAG 检索时必须加权限过滤。

不要把所有文档都放给所有用户检索。

---

## 四十五、41｜RAG 常见错误八：索引更新机制缺失

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

文档更新后，如果不重建索引：

```text
用户问到的还是旧内容
```

所以企业 RAG 要设计：

```text
文档上传
文档解析
chunk 切分
embedding 生成
索引写入
旧索引删除
版本管理
失败重试
```

这一章先手动 rebuild。

后面企业知识库项目会做完整流程。

---

## 四十六、42｜RAG 优化方向
常见优化：

```text
1. 更好的文档解析
2. 更合理的 Chunk 策略
3. 更好的 Embedding 模型
4. Hybrid Search：关键词 + 向量
5. Query Rewrite：查询改写
6. Rerank：重排序
7. Metadata Filter：元数据过滤
8. Parent-Child Retrieval
9. Multi-query Retrieval
10. RAG Evaluation
```

---

### 【重点内容】
这一章只是最小 RAG。

真正企业 RAG 会复杂很多。

但是无论怎么优化，基础链路都离不开：

```text
Document
Splitter
Embedding
VectorStore
Retriever
Prompt
Model
```

先把这条链路跑通，后面再谈优化。

---

## 四十七、43｜本章知识点和前面章节对应表
| 本章知识点 | 前面章节对应 |
| --- | --- |
| Document | 第 11 章数据库实体 / 文档数据 |
| Metadata | 引用来源 / 权限过滤 |
| Text Splitter | 后续企业文档解析 |
| Embedding | 向量检索基础 |
| VectorStore | 后续 pgvector |
| Retriever | LangChain 核心架构中的 Retriever |
| RAG Prompt | 第 23 章 LangChain Prompt |
| RAG Chain | 第 21 章 Runnable / LCEL |
| RAG Answer | 第 24 章 Structured Output |
| search_knowledge_base_tool | 第 25 章 Tool |
| Agent + RAG | 第 26 章 Agent |
| ChatService 接入 RAG | 第 19 章项目一升级 |


---

## 四十八、44｜本章完整复习
这一章我们完成了：

```text
1. 理解 RAG 是什么
2. 理解普通 Chat 和 RAG 的区别
3. 理解 RAG 和 Tool Calling 的关系
4. 理解 LangChain RAG 核心组件
5. 创建 langchain_rag 目录
6. 准备本地 Markdown 知识库
7. 理解 Document
8. 实现 Markdown 文档加载
9. 测试 Document 加载
10. 理解 Text Splitter
11. 使用 RecursiveCharacterTextSplitter
12. 测试文档切分
13. 理解 Embedding
14. 实现教学版 SimpleHashEmbeddings
15. 理解 VectorStore
16. 使用 Chroma 创建本地向量库
17. 测试 similarity_search
18. 理解 Retriever
19. 创建 Retriever
20. 测试 Retriever
21. 编写 RAG Prompt
22. 创建 RAG Chain
23. 测试 RAG Chain
24. 实现 LangChainRAGService
25. 测试 RAGService
26. 创建 RAG API
27. 测试 RAG API
28. 把 RAG 封装成 search_knowledge_base Tool
29. 测试 RAG Tool
30. 理解项目一如何接入 RAG
31. 理解 RAG 和 Agent 如何结合
32. 总结 RAG 常见错误
33. 总结 RAG 优化方向
```

---

## 四十九、45｜课后任务一：跑通 Document 加载
要求：

```text
1. 运行 scripts/test_lc27_documents.py
2. 打印 documents count
3. 打印每个 Document 的 metadata
4. 说明 page_content 和 metadata 的作用
```

---

## 五十、46｜课后任务二：跑通 Text Splitter
要求：

```text
1. 运行 scripts/test_lc27_splitter.py
2. 查看 chunks count
3. 调整 chunk_size=300
4. 调整 chunk_overlap=50
5. 对比 chunk 数量变化
```

---

## 五十一、47｜课后任务三：跑通 VectorStore
要求：

```text
1. 运行 scripts/test_lc27_vector_store.py
2. 查询“员工年假有几天？”
3. 查看是否召回 employee_handbook
4. 修改 query 再测试
```

---

## 五十二、48｜课后任务四：跑通 RAG Chain
要求：

```text
1. 运行 scripts/test_lc27_rag_chain.py
2. 查看 answer
3. 查看 sources
4. 判断回答是否基于检索文档
```

---

## 五十三、49｜课后任务五：新增一份知识库文档
新增：

```text
data/knowledge_base/frontend_interview.md
```

内容：

```markdown
# 前端面试知识库

## Vue 响应式

Vue3 使用 Proxy 实现响应式系统。

Vue2 主要使用 Object.defineProperty 实现响应式。

## React Fiber

React Fiber 是 React 16 引入的新协调架构，用于支持任务切片和优先级调度。
```

要求：

```text
1. 重新 rebuild index
2. 查询“Vue3 响应式怎么实现？”
3. 确认能召回 frontend_interview
```

---

## 五十四、50｜课后任务六：把 RAG 接入 ChatService
要求：

```text
1. ChatService 判断 prompt_scenario=rag_qa
2. 调用 langchain_rag_service.ask
3. 返回 ChatResponse
4. sources 映射为 SourceDocument
5. 前端 Demo 展示引用来源
```

---

## 五十五、51｜课后任务七：把 RAG Tool 接入 Agent
要求：

```text
1. 把 search_knowledge_base_tool 注册到 Agent tools
2. 用户问“订单未发货时可以退款吗？”
3. Agent 调用 search_knowledge_base
4. 返回基于知识库的答案
```

---

## 五十六、52｜课后任务八：画出 LangChain RAG 调用链路
画出：

```http
POST /api/v1/langchain/rag/ask
```

完整链路：

```text
HTTP Request
 ↓
RAG Router
 ↓
LangChainRAGService
 ↓
RAG Chain
 ↓
Retriever
 ↓
VectorStore
 ↓
Embedding Query
 ↓
Top K Documents
 ↓
format_docs
 ↓
RAG_PROMPT
 ↓
ChatModel
 ↓
StrOutputParser
 ↓
Answer + Sources
 ↓
ApiResponse
```

---

## 五十七、53｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 27 章我们就讲完了。

这一章我们完成了 LangChain RAG 的最小闭环。

==大家一定要记住 RAG 的核心链路：==

```text
Document
 ↓
Text Splitter
 ↓
Embedding
 ↓
VectorStore
 ↓
Retriever
 ↓
Prompt
 ↓
Model
 ↓
Answer
```

RAG 的本质不是让模型变聪明，而是让模型有资料可查、有依据可答。

这一章我们用本地 Markdown 文档做了一个最小知识库。

并完成了：

```text
Document 加载
Chunk 切分
SimpleHashEmbeddings
Chroma VectorStore
Retriever
RAG Prompt
RAG Chain
RAGService
RAG API
search_knowledge_base Tool
```

到这里，我们已经有了三类能力：

```text
普通 Chat
Tool Calling / Agent
RAG 知识库问答
```

下一章会把 Agent 和 RAG 组合起来。

---

---

> [!success] 一句话带走
> ==RAG 的难点不在模型，在文档切分、召回质量和来源可追溯。==

> [!quote] 关于本文档
> 由原始讲义 `第 27 章｜LangChain RAG.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
