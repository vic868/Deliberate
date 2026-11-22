## 一、课程目标
本章围绕企业级 RAG 的高级检索技术展开，直接使用 LangChain、LangGraph、Cohere Rerank、LangSmith 等官方生态中的组件和 API，不再手写原生检索算法。

本章重点解决：

+ 为什么向量检索经常召回错误文档？
+ 为什么关键词检索和语义检索需要结合？
+ 如何使用 Multi-Query Retrieval 提高召回率？
+ 如何使用 Hybrid Search 实现混合检索？
+ 如何使用 EnsembleRetriever 融合多个检索器？
+ 如何使用 Reranker 提高检索排序质量？
+ 如何使用 Contextual Compression 减少无关上下文？
+ 如何使用 Parent Document Retriever 保留文档上下文？
+ 如何使用 Metadata Filter 实现精确检索？
+ 如何使用 LangGraph 构建 Agentic Retrieval？
+ 如何使用 LangSmith 评估高级检索效果？

本章最终目标：

**使用成熟的检索组件，将普通向量检索升级为支持多路召回、混合检索、重排序、上下文压缩以及动态检索决策的企业级 Retrieval Pipeline。**

---

## 二、为什么需要高级 Retrieval？
在第 45 章中，我们已经实现了基础 RAG：

```plain
用户问题
   ↓
Embedding
   ↓
Vector Search
   ↓
Top-K Documents
   ↓
LLM
   ↓
Answer
```

基础 RAG 可以解决简单的知识问答问题，但在企业真实场景中，通常存在以下问题。

### 2.1 问题一：语义相似，不代表业务相关
用户：

```plain
公司员工报销需要满足什么条件？
```

Vector Search 可能检索到：

```plain
员工请假制度
员工福利制度
员工差旅制度
财务管理制度
```

虽然这些文档在语义上可能比较接近，但并不都包含正确答案。

### 2.2 问题二：关键词检索和语义检索存在差异
用户：

```plain
ERP-2026-001 项目的审批状态是什么？
```

语义检索可能无法准确识别：

```plain
ERP-2026-001
```

这种精确业务编号。

但 BM25 关键词检索能够更好地匹配：

+ 项目编号
+ 产品型号
+ 错误码
+ 客户名称
+ 专业术语
+ 精确业务关键词

因此企业检索不能只依赖向量相似度。

### 2.3 问题三：检索结果排序不准确
向量数据库返回的 Top-K 文档，是按照 Embedding 相似度排序的。

但是：

**Embedding Similarity Score 不一定等于最终业务相关性。**

例如：

```plain
用户问题：
如何处理订单退款？

Vector Search：

1. 订单查询流程
2. 订单退款审批流程
3. 订单创建流程
4. 订单售后处理流程
5. 订单支付流程
```

实际最相关的文档可能排在第 2 位。

如果直接将 Top-3 文档传给大模型，可能会遗漏关键知识。

这时需要 Reranker 对检索结果重新排序。

### 2.4 问题四：复杂问题需要多次检索
用户：

```plain
结合产品手册和售后规范，
分析产品出现故障的原因，
并给出解决方案。
```

单次向量检索可能无法同时找到：

+ 产品功能说明
+ 故障处理方法
+ 售后流程
+ 历史解决方案

需要通过 Query Rewrite、Multi-Query Retrieval 或 Agentic Retrieval 进行多轮检索。

---

## 三、高级 Retrieval 技术架构
本章重点实现以下检索技术：

| 技术 | 解决的问题 |
| --- | --- |
| Query Rewrite | 优化用户原始问题 |
| Multi-Query Retrieval | 从多个查询角度提高召回 |
| BM25 Retrieval | 精确关键词检索 |
| Vector Retrieval | 语义检索 |
| Hybrid Search | 融合关键词和语义检索 |
| EnsembleRetriever | 多检索器融合与 RRF 排序 |
| Reranker | 对候选文档重新排序 |
| Contextual Compression | 压缩无关上下文 |
| Parent Document Retrieval | 检索小块，返回更完整上下文 |
| Metadata Filter | 按业务属性过滤文档 |
| LangGraph Agentic Retrieval | 根据检索质量动态决定下一步 |


整体架构：

```plain
                   用户问题
                       │
                       ▼
                  Query Rewrite
                       │
                       ▼
              Multi-Query Retrieval
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
        BM25 Search         Vector Search
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
                EnsembleRetriever
                  RRF 融合排序
                       │
                       ▼
                   Reranker
                       │
                       ▼
             Contextual Compression
                       │
                       ▼
                 Relevant Context
                       │
                       ▼
                  LangGraph
                       │
                       ▼
                 DeepSeek
                       │
                       ▼
                   Answer
```

---

## 四、创建高级 Retrieval 项目
### 4.1 初始化项目
```plain
mkdir chapter43-advanced-retrieval

cd chapter43-advanced-retrieval

uv init --python 3.12
```

安装依赖：

```bash
uv add langchain

uv add langchain-core

uv add langchain-openai

uv add langchain-classic

uv add langchain-community

uv add langchain-text-splitters

uv add langchain-postgres

uv add langchain-cohere

uv add langgraph

uv add langsmith

uv add rank-bm25

uv add python-dotenv
```

本章涉及的高级 Retriever 组件使用 LangChain Classic 提供的检索器实现，业务模型、Prompt、Document、Runnable 等继续使用 LangChain Core 和 LangChain 官方集成。

### 4.2 项目目录
```plain
chapter43-advanced-retrieval/
├── .env
├── .env.example
├── pyproject.toml
├── uv.lock
│
├── data/
│   └── knowledge/
│
└── app/
    ├── __init__.py
    ├── config.py
    ├── base_retrieval.py
    ├── multi_query.py
    ├── hybrid_retrieval.py
    ├── reranking.py
    ├── compression.py
    ├── parent_retrieval.py
    ├── agentic_retrieval.py
    └── main.py
```

### 4.3 配置环境变量
创建 `.env.example`：

```plain
DEEPSEEK_API_KEY=your_deepseek_api_key

COHERE_API_KEY=your_cohere_api_key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=chapter43-advanced-retrieval

POSTGRES_URL=postgresql+psycopg://rag:rag123@localhost:5432/rag_db
```

复制：

```plain
cp .env.example .env
```

说明：

+ DeepSeek：用于 Query Rewrite、回答生成等任务。
+ Cohere：用于 Reranker。
+ PostgreSQL + pgvector：使用第 45 章的知识库向量存储。
+ LangSmith：用于检索链路追踪和实验评估。

---

## 五、基础 Retrieval：统一 Retriever 接口
LangChain 中，Retriever 的核心职责是：

```plain
Query
  ↓
Retriever
  ↓
List[Document]
```

不同检索技术可以统一转换为 Retriever。

例如：

```plain
retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 5,
    }
)
```

调用：

```plain
docs = retriever.invoke(
    "订单退款需要什么条件？"
)
```

返回：

```plain
list[Document]
```

每个 Document 包含：

```plain
doc.page_content

doc.metadata
```

这样不同检索器可以组合使用，而不需要重新编写统一接口。

### 5.1 创建基础检索器
创建 `app/base_retrieval.py`：

```python
from app.knowledge import vector_store


vector_retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 10,
    }
)



def retrieve_documents(query: str):
    return vector_retriever.invoke(query)


if __name__ == "__main__":
    docs = retrieve_documents(
        "订单退款需要什么条件？"
    )

    for index, doc in enumerate(docs, start=1):
        print(f"\n文档 {index}")

        print(doc.page_content)

        print(doc.metadata)
```

这里的 `vector_store` 直接复用第 45 章的 PostgreSQL + pgvector 知识库。

如果使用其他 VectorStore，只需要替换向量数据库初始化部分即可。

---

## 六、Query Rewrite：查询改写
### 6.1 什么是 Query Rewrite？
用户输入的问题，不一定适合直接用于检索。

例如：

```plain
用户：
之前那个东西为什么不能用了？
```

这个问题缺少：

+ 具体产品
+ 问题描述
+ 业务上下文
+ 专业术语

直接进行 Vector Search，检索效果通常较差。

Query Rewrite 的作用：

**使用大模型将用户问题改写成更加适合检索的查询表达。**

### 6.2 Query Rewrite 实战
创建 `app/multi_query.py`：

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv

load_dotenv()


llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    temperature=0,
)


rewrite_prompt = ChatPromptTemplate.from_template(
    """
你是一名企业知识库检索专家。

请将用户问题改写为适合企业知识库检索的查询。

要求：
1. 保留原始问题的核心意图。
2. 补充必要的专业关键词。
3. 去除模糊表达。
4. 不要回答问题。
5. 只输出改写后的查询。

用户问题：
{question}
"""
)


rewrite_chain = rewrite_prompt | llm


def rewrite_query(question: str) -> str:
    result = rewrite_chain.invoke(
        {
            "question": question,
        }
    )

    return result.content


if __name__ == "__main__":
    result = rewrite_query(
        "之前那个东西为什么不能用了？"
    )

    print(result)
```

示例：

输入：

```plain
之前那个东西为什么不能用了？
```

改写后：

```plain
企业产品使用过程中出现功能异常的原因及故障排查方法。
```

注意：

Query Rewrite 不能凭空补充未经用户提供或上下文确认的事实。

实际业务中，应该结合历史对话、用户身份和已有业务实体进行改写，避免错误扩展用户意图。

---

## 七、Multi-Query Retrieval：多查询检索
### 7.1 为什么需要 Multi-Query？
用户问题可能只包含一种表达方式。

但企业知识文档中，同一个概念可能使用不同术语描述。

例如：

```plain
用户问题：
如何处理订单退款？
```

相关文档可能分别使用：

```plain
退款申请
退款审批
订单退费
售后退款
退款处理流程
```

只使用原始 Query 进行向量检索，可能无法充分召回这些知识。

Multi-Query Retrieval 的核心思想：

**使用 LLM 将一个问题生成多个不同角度的查询，并对每个查询分别执行检索，再合并结果。**

### 7.2 使用 LangChain MultiQueryRetriever
```python
from langchain_classic.retrievers import MultiQueryRetriever

from app.base_retrieval import vector_retriever
from app.multi_query import llm


multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=vector_retriever,
    llm=llm,
    include_original=True,
)
```

调用：

```plain
docs = multi_query_retriever.invoke(
    "如何处理订单退款？"
)
```

MultiQueryRetriever 会：

1. 调用 LLM 生成多个查询表达。
2. 对每个查询执行 Retriever。
3. 合并多个查询的检索结果。
4. 对重复文档进行去重。
5. 返回合并后的 Document 列表。

这里直接使用 LangChain 官方 `MultiQueryRetriever.from_llm()`。

不需要自己实现查询生成、并发检索和结果去重逻辑。

### 7.3 Multi-Query 的适用场景
适合：

+ 企业知识库
+ 技术文档检索
+ 售后问题
+ 专业术语检索
+ 用户问题表达不准确
+ 复杂业务问题
+ 召回率不足的场景

注意：

Multi-Query 会增加模型调用和检索次数。

对于简单 FAQ，不一定需要开启。

---

## 八、Hybrid Search：混合检索
### 8.1 什么是 Hybrid Search？
Hybrid Search 将两种检索方式结合：

+ Sparse Retrieval：关键词检索。
+ Dense Retrieval：向量语义检索。

其中：

**BM25 负责关键词匹配，Vector Search 负责语义理解。**

例如：

用户：

```plain
ERP-2026-001 项目的审批状态是什么？
```

BM25 可以精准匹配：

```plain
ERP-2026-001
```

Vector Search 可以理解：

```plain
项目审批状态
审批进度
项目审核情况
```

两种检索方式具有互补优势。

### 8.2 使用 BM25Retriever
安装：

```plain
uv add rank-bm25
```

创建 `app/hybrid_retrieval.py`：

```python
from langchain_community.retrievers import BM25Retriever

from langchain_core.documents import Document

from langchain_classic.retrievers import EnsembleRetriever

from app.base_retrieval import vector_retriever


documents = [
    Document(
        page_content="ERP-2026-001 项目审批状态为已通过。",
        metadata={
            "source": "project-approval.txt",
        },
    ),
    Document(
        page_content="ERP-2026-002 项目审批状态为待审核。",
        metadata={
            "source": "project-approval.txt",
        },
    ),
    Document(
        page_content="订单退款需要经过售后审核和财务审批。",
        metadata={
            "source": "refund-policy.txt",
        },
    ),
]


bm25_retriever = BM25Retriever.from_documents(
    documents
)

bm25_retriever.k = 5
```

这里使用 BM25Retriever 构建关键词检索器。

正式项目中，BM25 的文档来源应该与向量数据库保持一致。

### 8.3 使用 EnsembleRetriever 融合检索
```plain
hybrid_retriever = EnsembleRetriever(
    retrievers=[
        bm25_retriever,
        vector_retriever,
    ],
    weights=[
        0.4,
        0.6,
    ],
)
```

调用：

```plain
docs = hybrid_retriever.invoke(
    "ERP-2026-001 项目的审批状态是什么？"
)

for doc in docs:
    print(doc.page_content)
```

EnsembleRetriever 使用 Reciprocal Rank Fusion，即 RRF 排名融合算法，对多个 Retriever 的结果进行融合。

示例：

```plain
BM25：

1. ERP-2026-001 项目审批状态为已通过
2. ERP-2026-002 项目审批状态为待审核

Vector Search：

1. 项目审批流程说明
2. ERP-2026-001 项目审批状态为已通过
3. 项目审核规则

EnsembleRetriever：

1. ERP-2026-001 项目审批状态为已通过
2. 项目审批流程说明
3. ERP-2026-002 项目审批状态为待审核
4. 项目审核规则
```

这里的排序仅用于说明融合原理，不代表实际运行结果。

### 8.4 RRF 的作用
RRF 的基本思想：

```plain
RRF Score = Σ 1 / (k + rank)
```

不同 Retriever 的排序结果可以通过排名进行融合，而不是直接比较不同检索器的原始分数。

因此：

+ BM25 Score 不需要与 Vector Similarity Score 直接比较。
+ 多个 Retriever 可以统一融合。
+ 可以根据业务需要调整 Retriever 权重。

注意：

EnsembleRetriever 是检索结果融合组件，不是企业级搜索引擎。

对于大规模数据和高并发场景，应优先考虑 PostgreSQL、Elasticsearch、OpenSearch、Vespa 等具备原生 Hybrid Search 能力的搜索基础设施。

---

## 九、Reranker：重排序
### 9.1 为什么需要 Reranker？
Vector Search 和 BM25 的目标是：

**尽可能召回相关文档。**

Reranker 的目标是：

**从召回结果中进一步筛选和排序最相关的文档。**

例如：

```plain
用户问题：
如何处理订单退款？
```

第一阶段检索：

```plain
1. 订单查询流程
2. 订单退款审批流程
3. 订单创建流程
4. 订单售后处理流程
5. 订单支付流程
6. 退款异常处理流程
```

第二阶段 Reranker：

```plain
1. 订单退款审批流程
2. 退款异常处理流程
3. 订单售后处理流程
```

Reranker 可以提高最终传递给 LLM 的上下文质量。

### 9.2 安装 Cohere Rerank
```plain
uv add langchain-cohere
```

配置：

```plain
COHERE_API_KEY=your_cohere_api_key
```

Cohere 提供 Rerank API，并支持 LangChain 官方集成。

### 9.3 使用 CohereRerank
创建 `app/reranking.py`：

```python
from langchain_cohere import CohereRerank

from app.base_retrieval import vector_retriever


reranker = CohereRerank(
    model="rerank-v5.0-pro",
    top_n=5,
)


def rerank_documents(query: str):
    docs = vector_retriever.invoke(query)

    reranked_docs = reranker.compress_documents(
        documents=docs,
        query=query,
    )

    return reranked_docs


if __name__ == "__main__":
    docs = rerank_documents(
        "如何处理订单退款？"
    )

    for index, doc in enumerate(docs, start=1):
        print(f"\n排名：{index}")

        print(doc.page_content)

        print(doc.metadata)
```

这里的执行流程：

```plain
Query
  ↓
Vector Search Top-10
  ↓
Cohere Rerank
  ↓
Top-5 Documents
```

Cohere Rerank 会根据 Query 和 Document 的语义相关性重新排序。

注意：

`rerank-v5.0-pro` 适合复杂、多语言和高质量排序场景；高吞吐、低延迟场景可以选择 `rerank-v5.0-fast`。

具体模型是否可用，取决于当前 Cohere API 的服务和账号权限。

---

## 十、Contextual Compression：上下文压缩
### 10.1 为什么需要 Contextual Compression？
向量检索返回的 Document，通常包含大量无关内容。

例如：

```plain
文档：

员工出差需要经过审批。

公司员工享有年度体检福利。

员工出差需要符合差旅标准。

员工生日可以领取礼品。

报销需要提交合法费用凭证。
```

用户问题：

```plain
员工出差报销需要什么条件？
```

实际上只需要：

```plain
员工出差需要经过审批。

员工出差需要符合差旅标准。

报销需要提交合法费用凭证。
```

如果直接将整个文档传递给大模型，会增加：

+ Prompt Token
+ 模型成本
+ 上下文噪声
+ 生成延迟
+ 无关信息干扰

Contextual Compression 可以根据用户问题对检索结果进行压缩。

### 10.2 使用 ContextualCompressionRetriever
创建 `app/compression.py`：

```python
from langchain_classic.retrievers import (
ContextualCompressionRetriever,
)

from langchain_cohere import CohereRerank

from app.base_retrieval import vector_retriever


compressor = CohereRerank(
    model="rerank-v5.0-pro",
    top_n=4,
)


compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vector_retriever,
)


def retrieve_compressed_context(
    query: str,
):
    return compression_retriever.invoke(
        query
    )


if __name__ == "__main__":
    docs = retrieve_compressed_context(
        "员工出差报销需要什么条件？"
    )

    for doc in docs:
        print(doc.page_content)
```

这里使用：

+ `ContextualCompressionRetriever`
+ `CohereRerank`

构建上下文压缩检索流程。

它可以对基础 Retriever 返回的文档进行相关性筛选与排序。

需要注意：

本示例使用 Cohere Rerank 作为 Compressor，主要实现候选文档重排序与 Top-N 筛选，并不等同于逐句抽取式压缩。

真正的 Contextual Compression 还可以结合：

+ LLMChainExtractor：根据 Query 从文档中提取相关内容。
+ EmbeddingsFilter：基于 Embedding 相似度过滤文档。
+ Cohere Rerank：根据相关性筛选和排序文档。

不同 Compressor 的成本、延迟和上下文压缩效果不同。

---

## 十一、Parent Document Retrieval：父文档检索
### 11.1 为什么需要 Parent Document Retriever？
在第 41 章中，我们已经学习了 Chunk 文档切分。

但是 Chunk Size 存在一个矛盾：

+ Chunk 太小：Embedding 更精准，但上下文不足。
+ Chunk 太大：上下文完整，但语义向量容易包含多个主题。

Parent Document Retriever 可以解决这个问题。

核心思想：

**使用小 Chunk 进行向量检索，找到相关内容后，再返回更大的 Parent Document。**

例如：

```plain
原始文档
   │
   ▼
Parent Chunk
   │
   ├── Child Chunk 1
   ├── Child Chunk 2
   ├── Child Chunk 3
   └── Child Chunk 4
```

向量数据库存储 Child Chunk。

检索时：

```plain
Query
  ↓
检索 Child Chunk
  ↓
找到 Parent ID
  ↓
获取 Parent Document
  ↓
返回完整上下文
```

### 11.2 使用 ParentDocumentRetriever
创建 `app/parent_retrieval.py`：

```python
from langchain_classic.retrievers import (
ParentDocumentRetriever,
)

from langchain_core.documents import Document

from langchain_core.stores import InMemoryStore

from langchain_text_splitters import (
RecursiveCharacterTextSplitter,
)

from app.knowledge import vector_store


# 小 Chunk：用于精确向量检索
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=80,
)

# Parent Chunk：用于保留完整上下文
parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
)

docstore = InMemoryStore()

parent_retriever = ParentDocumentRetriever(
    vectorstore=vector_store,
    docstore=docstore,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)


def add_parent_documents(
    documents: list[Document],
):
    parent_retriever.add_documents(
        documents,
    )


def retrieve_parent_documents(
    query: str,
):
    return parent_retriever.invoke(
        query
    )
```

调用：

```plain
docs = retrieve_parent_documents(
    "员工出差报销需要什么条件？"
)

for doc in docs:
    print(doc.page_content)
```

ParentDocumentRetriever 会：

1. 对原始文档进行 Parent Splitter 切分。
2. 对 Parent Document 进一步生成 Child Chunk。
3. 将 Child Chunk 写入 VectorStore。
4. 将 Parent Document 保存到 DocStore。
5. 通过 Child Chunk 进行相似度检索。
6. 根据 Parent ID 获取对应 Parent Document。

注意：

这里使用 `InMemoryStore` 仅适用于教学演示和本地验证。

企业生产环境需要将 Parent Document 持久化到 Redis、数据库或其他持久化 DocStore，避免服务重启后丢失父文档。

另外，ParentDocumentRetriever 是 LangChain Classic 提供的检索器。项目使用时需要安装 `langchain-classic`。

---

## 十二、Metadata Filter：元数据过滤
### 12.1 为什么企业检索需要 Metadata Filter？
企业知识库不仅需要语义相关，还需要符合业务约束。

例如：

+ 只检索某个部门的文档。
+ 只检索指定知识库。
+ 只检索某个产品。
+ 只检索指定版本。
+ 只检索当前用户有权限访问的文档。
+ 只检索指定时间范围的内容。

这些条件不能仅依赖向量相似度。

需要通过 Metadata Filter 进行过滤。

### 12.2 Document Metadata
企业文档可以包含：

```python
metadata = {
    "tenant_id": "tenant_001",
    "department_id": "dept_tech",
    "knowledge_base_id": "kb_001",
    "document_id": "doc_001",
    "document_version": "v2",
    "product": "ERP",
    "source": "product-manual.pdf",
}
```

这些字段在文档入库时保存到 Document Metadata。

### 12.3 使用 VectorStore Retriever Filter
不同 VectorStore 的 Filter 表达式存在差异。

例如，Chroma：

```python
retriever = chroma_vector_store.as_retriever(
    search_kwargs={
        "k": 5,
        "filter": {
            "knowledge_base_id": "kb_001",
        },
    }
)
```

对于 PostgreSQL + pgvector，需要使用当前 `PGVectorStore` 支持的 Metadata Filter 语法。

原则上：

```plain
用户身份
  ↓
服务端权限校验
  ↓
生成可信 Metadata Filter
  ↓
Vector Search
  ↓
返回授权范围内的文档
```

重要：

**Metadata Filter 不能直接信任前端传入的 tenant_id 或 department_id。**

这些条件应该由后端根据用户身份、组织关系和权限体系生成。

检索过滤是数据权限控制的一部分，不能代替完整的企业 RBAC 权限体系。

---

## 十三、使用 LangGraph 构建 Agentic Retrieval
前面实现的检索流程属于固定 Pipeline：

```plain
Query
  ↓
Retriever
  ↓
Reranker
  ↓
LLM
```

但是企业中存在复杂问题：

```plain
用户：

结合产品手册、历史案例和售后规范，
分析产品故障原因，并给出解决方案。
```

这种问题可能需要：

+ 多次检索
+ 查询改写
+ 检索结果评估
+ 条件路由
+ 失败后重新检索
+ 最终答案生成

这时可以使用 LangGraph 构建 Agentic Retrieval。

### 13.1 Agentic Retrieval 架构
```plain
用户问题
   │
   ▼
Query Rewrite
   │
   ▼
Retrieve
   │
   ▼
Grade Documents
   │
   ├── 相关 ──────────┐
   │                  ▼
   │              Generate
   │                  │
   │                  ▼
   │                 END
   │
   └── 不相关
          │
          ▼
      Rewrite Query
          │
          ▼
       Retrieve
```

LangGraph 可以通过 State、Node、Edge、Conditional Edge 控制整个检索流程。

### 13.2 定义 Agentic Retrieval State
创建 `app/agentic_retrieval.py`：

```python
import os

from typing import TypedDict

from dotenv import load_dotenv

from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import (
START,
END,
StateGraph,
)

from app.base_retrieval import vector_retriever


load_dotenv()


llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    temperature=0,
)


class RetrievalState(TypedDict):
    question: str
    query: str
    documents: list
    answer: str
    retry_count: int
```

### 13.3 查询改写节点
```python
rewrite_prompt = ChatPromptTemplate.from_template(
    """
你是一名企业知识库检索专家。

请将问题改写为更适合检索的表达。

要求：
1. 保留核心业务意图。
2. 补充必要关键词。
3. 不要回答问题。
4. 只输出检索查询。

原始问题：
{question}
"""
)


def rewrite_node(state: RetrievalState):
    result = (
        rewrite_prompt
        | llm
    ).invoke(
        {
            "question": state["question"],
        }
    )

    return {
        "query": result.content,
    }
```

### 13.4 Retrieve 节点
```plain
def retrieve_node(state: RetrievalState):
    docs = vector_retriever.invoke(
        state["query"]
    )

    return {
        "documents": docs,
    }
```

这里直接使用 LangChain Retriever。

### 13.5 Grade Documents 节点
```python
class DocumentGrade(BaseModel):
    relevant: bool = Field(
        description="检索内容是否与问题相关",
    )

    reason: str = Field(
        description="判断理由",
    )


grade_llm = llm.with_structured_output(
    DocumentGrade
)


def grade_node(state: RetrievalState):
    documents = state["documents"]

    if not documents:
        return {
            "relevant": False,
        }

    context = "\n\n".join(
        doc.page_content
        for doc in documents
    )

    result = grade_llm.invoke(
        [
            {
                "role": "system",
                "content": """
判断检索内容是否包含回答问题所需的核心知识。

如果检索内容与问题无关，返回 relevant=false。
如果检索内容足以支持回答，返回 relevant=true。
""",
            },
            {
                "role": "user",
                "content": f"""
问题：
{state["question"]}

检索内容：
{context}
""",
            },
        ]
    )

    return {
        "relevant": result.relevant,
        "grade_reason": result.reason,
        "retry_count": state.get(
            "retry_count",
            0,
        ),
    }
```

### 13.6 Generate 节点
```python
def generate_node(state: RetrievalState):
    context = "\n\n".join(
        doc.page_content
        for doc in state["documents"]
    )

    response = llm.invoke(
        [
            {
                "role": "system",
                "content": """
你是企业知识库助手。

必须根据检索内容回答问题。

如果检索内容不足，请明确说明。
不得编造企业业务规则。
""",
            },
            {
                "role": "user",
                "content": f"""
问题：
{state["question"]}

知识内容：
{context}
""",
            },
        ]
    )

    return {
        "answer": response.content,
    }
```

### 13.7 条件路由
```python
def route_after_grade(state: RetrievalState):
    retry_count = state.get(
        "retry_count",
        0,
    )

    relevant = state.get(
        "relevant",
        False,
    )

    if relevant:
        return "generate"

    if retry_count >= 2:
        return "generate"

    return "rewrite"
```

### 13.8 重试节点
```plain
def retry_node(state: RetrievalState):
    return {
        "retry_count": state.get(
            "retry_count",
            0,
        ) + 1,
    }
```

### 13.9 构建 LangGraph
```python
builder = StateGraph(
    RetrievalState
)

builder.add_node(
    "rewrite",
    rewrite_node,
)

builder.add_node(
    "retrieve",
    retrieve_node,
)

builder.add_node(
    "grade",
    grade_node,
)

builder.add_node(
    "generate",
    generate_node,
)

builder.add_node(
    "retry",
    retry_node,
)

builder.add_edge(
    START,
    "rewrite",
)

builder.add_edge(
    "rewrite",
    "retrieve",
)

builder.add_edge(
    "retrieve",
    "grade",
)

builder.add_conditional_edges(
    "grade",
    route_after_grade,
    {
        "generate": "generate",
        "rewrite": "retry",
    },
)

builder.add_edge(
    "retry",
    "rewrite",
)

builder.add_edge(
    "generate",
    END,
)

agentic_retrieval_graph = builder.compile()
```

### 13.10 调用 Agentic Retrieval
```python
result = agentic_retrieval_graph.invoke(
    {
        "question": "结合产品手册分析产品故障原因",
        "query": "",
        "documents": [],
        "answer": "",
        "retry_count": 0,
    }
)

print(result["answer"])
```

这里通过 LangGraph 实现：

+ Query Rewrite
+ Retrieval
+ Document Grading
+ Conditional Routing
+ Retry
+ Answer Generation

注意：

这个示例展示的是可控的 Agentic Retrieval 工作流，不是无限自主 Agent。

生产环境应进一步增加：

+ 重试次数上限
+ 节点超时
+ 评估节点成本控制
+ 检索失败处理
+ 文档来源引用
+ 检索质量监控
+ LangSmith Trace

---

## 十四、使用 LangSmith 追踪高级 Retrieval
高级检索往往包含多个模型调用和检索步骤。

例如：

```plain
Query Rewrite
   ↓
Multi-Query
   ↓
BM25
   ↓
Vector Search
   ↓
Ensemble
   ↓
Reranker
   ↓
Compression
   ↓
Generate
```

如果只观察最终答案，很难判断问题到底发生在哪个环节。

LangSmith 可以对 LangChain 和 LangGraph 的运行过程进行追踪。

### 14.1 配置 LangSmith
```plain
LANGSMITH_TRACING=true

LANGSMITH_API_KEY=your_langsmith_api_key

LANGSMITH_PROJECT=chapter43-advanced-retrieval
```

重新启动应用。

### 14.2 查看 Trace
进入：

```plain
https://smith.langchain.com/
```

查看：

```plain
chapter43-advanced-retrieval
```

可以观察：

+ Query Rewrite 的结果
+ Multi-Query 生成的多个查询
+ 每个 Retriever 返回的文档
+ Ensemble 融合结果
+ Reranker 输出
+ Compression 后的上下文
+ LangGraph 节点执行顺序
+ 每个节点耗时
+ LLM 调用成本
+ 最终答案

LangSmith 不仅可以追踪最终 LLM，也可以追踪整个 Retrieval Pipeline。

---

## 十五、高级 Retrieval 如何进行评估？
高级 Retrieval 优化不能只看最终答案是否正确。

需要单独评估检索质量。

### 15.1 Retrieval 指标
| 指标 | 作用 |
| --- | --- |
| Recall@K | 相关文档是否被召回 |
| Precision@K | Top-K 文档中相关内容占比 |
| MRR | 首个相关文档排名 |
| Context Precision | 检索上下文相关性与排序质量 |
| Context Recall | 参考答案需要的知识是否被召回 |


### 15.2 使用第 44 章的 Dataset
第 44 章已经构建：

```plain
enterprise-rag-evaluation
```

本章可以直接复用该 Dataset。

分别评估：

```plain
Experiment 1：
Vector Retrieval

Experiment 2：
Multi-Query Retrieval

Experiment 3：
Hybrid Search

Experiment 4：
Hybrid + Reranker

Experiment 5：
Hybrid + Reranker + Compression

Experiment 6：
Agentic Retrieval
```

对比：

+ Answer Correctness
+ Faithfulness
+ Context Precision
+ Context Recall
+ Retrieval Latency
+ LLM Token Usage
+ Cost

### 15.3 评估原则
不要认为：

```plain
Reranker 一定比 Vector Search 好。
```

也不要认为：

```plain
Multi-Query 一定比 Single Query 好。
```

这些技术都有成本和延迟。

真正的企业级检索优化应该通过：

**固定 Dataset + 真实业务问题 + Retrieval Evaluation + LangSmith Experiment**

来确定最终方案。

---

## 十六、企业级 Retrieval Pipeline 推荐方案
对于普通企业知识问答：

```plain
Query
  ↓
Vector Search
  ↓
Reranker
  ↓
Generate
```

对于专业领域知识库：

```plain
Query Rewrite
  ↓
Multi-Query
  ↓
Hybrid Search
  ↓
EnsembleRetriever
  ↓
Reranker
  ↓
Contextual Compression
  ↓
Generate
```

对于复杂企业业务：

```plain
LangGraph
  ↓
Query Planning
  ↓
Multi-Query Retrieval
  ↓
Hybrid Search
  ↓
Reranker
  ↓
Document Grading
  ↓
Conditional Retrieval
  ↓
Generate
```

技术选型建议：

| 场景 | 推荐方案 |
| --- | --- |
| 普通 FAQ | Vector Search |
| 精确业务编号 | BM25 + Vector |
| 专业术语知识库 | Multi-Query + Vector |
| 企业制度知识库 | Hybrid + Reranker |
| 大量无关文档 | Contextual Compression |
| 长文档问答 | Parent Document Retriever |
| 多租户知识库 | Metadata Filter + 权限过滤 |
| 复杂问题 | LangGraph Agentic Retrieval |
| 检索优化验证 | LangSmith |


---

## 十七、本章总结
本章使用 LangChain、LangGraph、Cohere Rerank 和 LangSmith 完成了企业级高级 Retrieval 技术实践。

主要实现：

1. Query Rewrite 查询改写。
2. Multi-Query Retrieval 多查询检索。
3. BM25 关键词检索。
4. Vector Search 语义检索。
5. Hybrid Search 混合检索。
6. EnsembleRetriever 多检索器融合。
7. Reranker 重排序。
8. Contextual Compression 上下文压缩。
9. Parent Document Retriever 父文档检索。
10. Metadata Filter 元数据过滤。
11. LangGraph Agentic Retrieval。
12. LangSmith 检索追踪与评估。

核心思想：

**高级 Retrieval 的本质不是不断增加检索步骤，而是通过不同检索策略解决召回、排序、上下文、精确匹配和复杂问题分析等不同问题。**

企业实际落地时，需要根据业务场景选择检索策略，而不是将所有高级检索技术全部叠加。

---

## 十八、官方技术文档
### LangChain
+ Retrieval 官方文档：[https://docs.langchain.com/oss/python/langchain/retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
+ Retriever 概念：[https://docs.langchain.com/oss/python/langchain/retrievers](https://docs.langchain.com/oss/python/langchain/retrievers)
+ Multi-Query Retrieval：[https://reference.langchain.com/python/langchain-classic/retrievers/multi_query/MultiQueryRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/multi_query/MultiQueryRetriever)
+ EnsembleRetriever：[https://reference.langchain.com/python/langchain-classic/retrievers/ensemble/EnsembleRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/ensemble/EnsembleRetriever)
+ ParentDocumentRetriever：[https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever)
+ ContextualCompressionRetriever：[https://reference.langchain.com/python/langchain-classic/retrievers/contextual_compression/ContextualCompressionRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/contextual_compression/ContextualCompressionRetriever)

### Cohere Rerank
+ Cohere Rerank：[https://docs.cohere.com/docs/rerank](https://docs.cohere.com/docs/rerank)
+ Cohere + LangChain：[https://docs.cohere.com/docs/rerank-on-langchain](https://docs.cohere.com/docs/rerank-on-langchain)

### LangGraph
+ Agentic RAG：[https://docs.langchain.com/oss/python/langgraph/agentic-rag](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
+ LangGraph Graph API：[https://docs.langchain.com/oss/python/langgraph/graph-api](https://docs.langchain.com/oss/python/langgraph/graph-api)

### LangSmith
+ Evaluation：[https://docs.langchain.com/langsmith/evaluation](https://docs.langchain.com/langsmith/evaluation)
+ RAG Evaluation：[https://docs.langchain.com/langsmith/evaluate-rag-tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial)

### LangChain Classic
+ GitHub：[https://github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)

  

