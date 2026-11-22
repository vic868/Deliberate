**课程定位：** 从 0 到 1 理解 Embedding 模型，掌握向量数据库的企业级应用，完成一个真实可运行的向量检索项目。

**核心技术：** Python + LangChain + Ollama + OpenAI Embeddings + PostgreSQL + pgvector + uv

---

## 一、本章学习目标
本章主要解决 6 个问题：

1. Embedding 到底是什么？为什么 RAG 必须使用 Embedding？
2. 文本如何通过 Embedding 模型转换为向量？
3. Embedding 模型应该如何选择？本地模型和云端模型有什么区别？
4. 向量数据库到底解决什么问题？与普通 PostgreSQL 有什么区别？
5. 如何使用 LangChain 将文档向量化，并存储到 PostgreSQL？
6. 如何实现向量相似度搜索，并构建企业级向量检索基础设施？

本章完成后，能够独立实现：

+ Embedding 模型调用
+ 文本向量化
+ 向量维度检测
+ PostgreSQL + pgvector 环境搭建
+ LangChain PGVectorStore 初始化
+ 文档向量入库
+ 相似度搜索
+ Metadata Filter
+ Vector Index
+ 向量数据删除与更新
+ Embedding 模型切换
+ 向量数据库选型

---

## 二、Embedding 到底是什么？
### 2.1 为什么大模型无法直接搜索企业知识库？
假设企业知识库里面有一篇文档：

```plain
员工申请年假需要提前3个工作日提交审批，
审批通过后才能休假。
```

用户提问：

```plain
我下周想休息几天，应该提前多久申请？
```

传统关键词搜索可能无法匹配：

+ 文档中没有出现“下周”
+ 文档中没有出现“休息几天”
+ 文档中没有出现“提前多久”

但是从语义角度来看，这个问题与年假审批规则高度相关。

因此，企业知识库需要具备一种能力：

**即使用户和文档使用不同的表达方式，也能够找到语义相关的内容。**

这就是 Embedding 的核心价值。

### 2.2 Embedding 的定义
Embedding，也叫文本嵌入、向量化。

它的核心作用是：

将文本转换为一个固定维度的数字向量，使具有相似语义的文本在向量空间中更加接近。

例如：

```plain
文本 A：
员工申请年假需要提前3个工作日。

文本 B：
休年假之前需要提前三个工作日提交申请。

文本 C：
公司服务器如何部署？
```

通过 Embedding 模型转换之后：

```plain
文本 A → [0.12, -0.23, 0.45, ...]
文本 B → [0.11, -0.21, 0.43, ...]
文本 C → [-0.56, 0.18, -0.32, ...]
```

A 和 B 的语义相似度通常更高。

注意：

上面只是为了演示的虚拟向量，不是真实模型计算结果。

### 2.3 Embedding 的核心原理
Embedding 模型通过训练学习文本语义表达，将文本映射到高维向量空间。

```plain
原始文本
   ↓
Tokenizer
   ↓
模型编码
   ↓
Pooling / 模型输出处理
   ↓
Embedding Vector
```

在实际开发中，我们不需要自己实现这些步骤。

直接使用成熟的 Embedding 模型即可。

LangChain 提供统一的 Embeddings 接口：

```plain
embed_documents(texts)
```

用于批量生成文档向量。

```plain
embed_query(text)
```

用于生成查询向量。

不同 Embedding 服务可以使用相同接口接入 LangChain。

官方文档：

[https://docs.langchain.com/oss/python/integrations/embeddings](https://docs.langchain.com/oss/python/integrations/embeddings)

---

## 三、Embedding 模型选型
企业级 RAG 项目中，Embedding 模型选型非常重要。

Embedding 模型直接影响：

+ 文档检索准确率
+ 向量维度
+ 向量存储成本
+ 文档索引构建速度
+ 查询响应速度
+ 数据安全
+ 部署成本

### 3.1 常见 Embedding 模型
| 模型 | 特点 | 适用场景 |
| --- | --- | --- |
| OpenAI text-embedding-3-small | 云端 API、接入简单 | 商业项目、快速开发 |
| OpenAI text-embedding-3-large | 高维度、高质量语义表达 | 高质量检索需求 |
| BAAI BGE 系列 | 开源模型、中文能力较好 | 企业私有化知识库 |
| BGE-M3 | 多语言、支持较长输入、检索能力较强 | 中文及多语言知识库 |
| Qwen3-Embedding | 开源、多尺寸模型、支持多语言 | 企业私有化部署 |
| mxbai-embed-large | 本地部署方便 | 本地知识库、开发测试 |
| Cohere Embed | 云端服务、支持多种任务 | 商业检索应用 |


选型原则：

+ 低成本快速上线：云端 Embedding API
+ 数据不能出企业网络：本地开源 Embedding
+ 中文知识库：优先测试 BGE-M3、Qwen3-Embedding 等模型
+ 高并发企业服务：考虑独立部署 Embedding 服务
+ 高准确率场景：基于真实业务数据评测，不要仅看排行榜

参考：

[https://docs.langchain.com/oss/python/integrations/embeddings](https://docs.langchain.com/oss/python/integrations/embeddings)

### 3.2 Embedding 模型与 Chat 模型有什么区别？
这是 AI 面试中经常出现的问题。

| 对比维度 | Chat Model | Embedding Model |
| --- | --- | --- |
| 核心用途 | 理解、推理、生成文本 | 文本向量化 |
| 输入 | 用户问题、上下文 | 文本 |
| 输出 | 自然语言 | 数字向量 |
| 是否生成答案 | 是 | 否 |
| 是否用于语义检索 | 可间接参与 | 核心组件 |
| 是否需要向量数据库 | 不一定 | RAG 通常需要 |


例如：

```plain
DeepSeek Chat
    ↓
根据上下文生成答案

Qwen3-Embedding
    ↓
将文本转换为向量

PostgreSQL + pgvector
    ↓
存储向量并进行相似度检索
```

需要特别注意：

**DeepSeek Chat API 并不等于 DeepSeek Embedding API。**

如果使用 DeepSeek 作为 Chat 模型，可以同时使用其他厂商或本地模型作为 Embedding 模型。

---

## 四、Embedding 模型实战：LangChain + Ollama
本节首先实现本地 Embedding 模型调用。

使用 Ollama 的原因：

+ 不需要调用外部 Embedding API
+ 数据可以保留在本地
+ 不需要按 Token 支付 Embedding 费用
+ 适合本地知识库开发
+ 可以用于企业私有化部署方案

### 4.1 环境准备
安装 Ollama：

[https://ollama.com/download](https://ollama.com/download)

拉取 Embedding 模型：

```plain
ollama pull qwen3-embedding:0.6b
```

检查模型：

```plain
ollama list
```

确认 Ollama 服务正常：

```plain
curl http://localhost:11434/api/tags
```

### 4.2 创建项目
```plain
uv init embedding-vector-demo --python 3.12

cd embedding-vector-demo
```

安装依赖：

```plain
uv add langchain-core langchain-ollama langchain-openai langchain-postgres asyncpg python-dotenv
```

项目目录：

```plain
embedding-vector-demo/
├── .env
├── pyproject.toml
├── docker-compose.yml
├── embedding_demo.py
├── embedding_factory.py
├── vector_store.py
├── ingest.py
├── search.py
└── data/ 
    └── knowledge.txt
```

### 4.3 Embedding 模型调用
创建 `embedding_demo.py`：

```python
from langchain_ollama import OllamaEmbeddings


embeddings = OllamaEmbeddings(
    model="qwen3-embedding:0.6b",
)

text = "员工申请年假需要提前三个工作日"

# 单文本向量化
query_vector = embeddings.embed_query(text)

print("向量维度：", len(query_vector))
print("向量前10个值：", query_vector[:10])

# 多文本向量化
texts = [
    "员工申请年假需要提前三个工作日",
    "员工请病假需要提交医院证明",
    "公司服务器部署需要配置Docker",
]

vectors = embeddings.embed_documents(texts)

print("文档数量：", len(vectors))
print("第一个文档向量维度：", len(vectors[0]))
```

运行：

```plain
uv run python embedding_demo.py
```

预期输出：

```plain
向量维度：1536
向量前10个值：[...]

文档数量：3
第一个文档向量维度：1536
```

说明：

这里的向量维度以实际加载的模型版本为准，代码会打印真实结果。

### 4.4 解释 embed_query 和 embed_documents
```plain
embeddings.embed_query("什么是年假？")
```

适用于：

+ 用户输入问题
+ 查询文本
+ Search Query

```plain
embeddings.embed_documents([
    "年假申请流程",
    "病假申请流程",
])
```

适用于：

+ 文档向量化
+ 批量 Embedding
+ 知识库索引构建

虽然两者都返回向量，但某些模型会对 Query 和 Document 使用不同的编码策略。

因此，不能简单认为所有 Embedding 模型都只需要一个通用编码方法。

---

## 五、Embedding 模型工厂：支持本地与云端切换
企业级项目不能将 Embedding 模型硬编码在业务代码中。

应该通过配置实现模型切换。

### 5.1 配置文件
创建 `.env`：

```plain
# embedding provider: ollama / openai
EMBEDDING_PROVIDER=ollama

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://langchain:langchain@localhost:5432/langchain
VECTOR_TABLE=enterprise_knowledge
```

### 5.2 创建 embedding_factory.py
```python
import os

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

load_dotenv()


def create_embeddings() -> Embeddings:
    provider = os.getenv(
        "EMBEDDING_PROVIDER",
        "ollama",
    )

    if provider == "ollama":
        return OllamaEmbeddings(
            model=os.getenv(
                "OLLAMA_EMBEDDING_MODEL",
                "qwen3-embedding:0.6b",
            ),
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://localhost:11434",
            ),
        )

    if provider == "openai":
        return OpenAIEmbeddings(
            model=os.getenv(
                "OPENAI_EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    raise ValueError(
        f"不支持的 Embedding Provider: {provider}"
    )
```

以后切换模型只需要修改：

```plain
EMBEDDING_PROVIDER=openai
```

或者：

```plain
EMBEDDING_PROVIDER=ollama
```

业务代码不需要修改。

注意：

切换 Embedding 模型时，如果新旧模型的向量空间不同，原有向量不能直接继续使用。

后续需要重新构建索引。

---

## 六、Vector Database 到底是什么？
### 6.1 为什么需要向量数据库？
Embedding 模型生成的结果是数字向量。

例如：

```plain
文档 A：

员工年假申请流程

Embedding：

[0.12, -0.32, 0.51, ...]
```

假设企业有 100 万个文档。

如果将这些向量全部放在 Python 内存中：

```plain
vectors = [
    [0.12, -0.32, 0.51, ...],
    [0.22, -0.13, 0.81, ...],
    ...
]
```

那么将面临：

+ 内存占用
+ 数据持久化
+ 向量搜索性能
+ 向量更新
+ 多用户并发
+ 数据管理
+ Metadata Filter
+ 权限隔离
+ 数据备份

因此，需要一个专门管理向量数据的存储系统。

### 6.2 Vector Database 的核心能力
向量数据库主要负责：

1. 存储 Embedding Vector
2. 存储原始文本或文档引用
3. 存储 Metadata
4. 向量相似度搜索
5. Top-K 检索
6. 向量索引加速
7. Metadata Filter
8. 数据插入、更新、删除
9. 多租户数据隔离

向量数据库不是大模型。

它主要负责：

**存储向量、管理向量、检索向量。**

---

## 七、向量数据库选型
### 7.1 常见 Vector Database
| 产品 | 类型 | 适用场景 |
| --- | --- | --- |
| PostgreSQL + pgvector | 关系数据库扩展 | 企业业务系统、RAG |
| Qdrant | 专业向量数据库 | 企业级向量检索 |
| Milvus | 专业向量数据库 | 大规模向量检索 |
| Chroma | 向量数据库 | 开发、实验、轻量应用 |
| Weaviate | 向量数据库 | 企业搜索、知识系统 |
| Pinecone | 托管向量数据库 | 云端 SaaS |
| Elasticsearch | 搜索引擎 + 向量检索 | 混合搜索、企业搜索 |


### 7.2 为什么本章使用 PostgreSQL + pgvector？
对于企业 AI Agent 项目，PostgreSQL + pgvector 是一个非常实用的方案。

原因：

+ 企业业务数据本身就可能使用 PostgreSQL
+ 关系数据与向量数据可以统一管理
+ 支持 SQL
+ 支持事务
+ 支持 Metadata Filter
+ 支持向量索引
+ 支持权限体系
+ 可以降低系统架构复杂度
+ 适合中小规模及不少中大型企业应用

例如企业知识库：

```plain
PostgreSQL
├── 用户表
├── 部门表
├── 知识库表
├── 文档表
├── 文档分块表
├── 向量数据
├── 权限数据
└── 审计日志
```

不一定需要额外引入一套独立向量数据库。

但是：

如果面临海量向量、复杂向量检索、高吞吐需求，也可以选择 Qdrant 或 Milvus。

---

## 八、PostgreSQL + pgvector 环境搭建
### 8.1 Docker Compose
创建 `docker-compose.yml`：

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: embedding-postgres
    restart: unless-stopped

    environment:
      POSTGRES_USER: langchain
      POSTGRES_PASSWORD: langchain
      POSTGRES_DB: langchain

    ports:
      - "5432:5432"

    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

启动：

```plain
docker compose up -d
```

查看状态：

```plain
docker compose ps
```

查看日志：

```plain
docker compose logs -f postgres
```

### 8.2 验证 PostgreSQL
进入容器：

```plain
docker exec -it embedding-postgres psql -U langchain -d langchain
```

查看数据库：

```plain
SELECT version();
```

检查 pgvector：

```plain
CREATE EXTENSION IF NOT EXISTS vector;
```

查看扩展：

```plain
SELECT * FROM pg_extension;
```

如果出现：

```plain
vector
```

说明 pgvector 已经安装成功。

---

## 九、LangChain + PGVectorStore 实战
本节正式实现：

**Embedding → PostgreSQL → Vector Search**

注意：

新版 `langchain-postgres` 中推荐使用 `PGVectorStore`，旧版 `PGVector` 在新版本中已经进入弃用迁移阶段。

官方：

[https://github.com/langchain-ai/langchain-postgres](https://github.com/langchain-ai/langchain-postgres)

### 9.1 创建 vector_store.py
```python
import os

from dotenv import load_dotenv

from langchain_postgres import PGEngine, PGVectorStore

from embedding_factory import create_embeddings

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
VECTOR_TABLE = os.getenv(
    "VECTOR_TABLE",
    "enterprise_knowledge",
)

embeddings = create_embeddings()

pg_engine = PGEngine.from_connection_string(
    url=DATABASE_URL,
)


async def initialize_vector_store():
    """
    初始化向量数据库表，并创建 PGVectorStore。
    """

    # 获取实际 Embedding 维度
    sample_vector = embeddings.embed_query(
        "向量维度初始化测试"
    )

    vector_size = len(sample_vector)

    print("Embedding Vector Size:", vector_size)

    # 初始化向量表
    await pg_engine.ainit_vectorstore_table(
        table_name=VECTOR_TABLE,
        vector_size=vector_size,
    )

    # 创建 Vector Store
    vector_store = await PGVectorStore.create(
        engine=pg_engine,
        table_name=VECTOR_TABLE,
        embedding_service=embeddings,
    )

    return vector_store
```

这里使用实际模型输出确定维度，而不是在代码中写死。

例如：

```plain
OpenAI text-embedding-3-small
    ↓
1536 维

Qwen3-Embedding-0.6B
    ↓
1536 维（默认配置）
```

具体维度以实际模型配置为准。

### 9.2 创建 ingest.py
实现文档向量入库。

```python
import asyncio
import uuid

from langchain_core.documents import Document

from vector_store import initialize_vector_store


async def main():
    vector_store = await initialize_vector_store()

    documents = [
        Document(
            id=str(uuid.uuid4()),
            page_content=(
                "员工申请年假需要提前三个工作日提交申请，"
                "审批通过后才能休假。"
            ),
            metadata={
                "source": "hr-policy",
                "category": "leave",
                "department": "HR",
                "tenant_id": "tenant_001",
            },
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=(
                "员工申请病假需要提交医院相关证明，"
                "并按照公司规定完成审批流程。"
            ),
            metadata={
                "source": "hr-policy",
                "category": "sick_leave",
                "department": "HR",
                "tenant_id": "tenant_001",
            },
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=(
                "企业服务器部署需要配置Docker环境，"
                "并完成应用镜像构建与容器启动。"
            ),
            metadata={
                "source": "devops-guide",
                "category": "deployment",
                "department": "IT",
                "tenant_id": "tenant_001",
            },
        ),
    ]

    await vector_store.aadd_documents(documents)

    print(f"成功入库 {len(documents)} 条文档")


if __name__ == "__main__":
    asyncio.run(main())
```

执行：

```plain
uv run python ingest.py
```

预期：

```plain
Embedding Vector Size: 1536
成功入库 3 条文档
```

实际入库过程：

```plain
Document
   ↓
Embedding Model
   ↓
Vector
   ↓
PGVectorStore
   ↓
PostgreSQL + pgvector
```

注意：

生产环境不能简单使用每次执行都重新生成的 UUID 作为业务唯一标识。

需要基于：

```plain
document_id
chunk_id
version
```

设计稳定 ID，才能实现幂等入库、重复数据更新及文档版本管理。

---

## 十、向量相似度检索
### 10.1 创建 search.py
```python
import asyncio

from vector_store import initialize_vector_store


async def main():
    vector_store = await initialize_vector_store()

    query = "员工休年假需要提前多久申请？"

    results = await vector_store.asimilarity_search(
        query=query,
        k=3,
    )

    print(f"Query: {query}")

    for index, document in enumerate(results, start=1):
        print(f"\nTop {index}")
        print("Content:", document.page_content)
        print("Metadata:", document.metadata)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```plain
uv run python search.py
```

预期：

```plain
Query: 员工休年假需要提前多久申请？

Top 1
Content: 员工申请年假需要提前三个工作日提交申请...

Top 2
Content: 员工申请病假需要提交医院相关证明...

Top 3
Content: 企业服务器部署需要配置Docker环境...
```

实际返回结果取决于模型和向量检索评分。

### 10.2 Top-K 是什么？
```plain
results = await vector_store.asimilarity_search(
    query="员工休年假需要提前多久申请？",
    k=5,
)
```

`k=5` 表示返回最相似的 5 条文档。

RAG 系统通常会设置：

```plain
Top-K = 3
Top-K = 5
Top-K = 10
```

但是：

**Top-K 越大，不代表 RAG 效果越好。**

检索数量过多可能带来：

+ 无关内容增加
+ Context Token 增加
+ LLM 成本提高
+ 上下文噪声增加
+ 答案质量下降

需要根据业务数据进行评测。

---

## 十一、向量相似度原理
向量数据库检索的核心，是计算 Query Vector 与 Document Vector 的相似度。

### 11.1 常见相似度算法
| 算法 | 说明 |
| --- | --- |
| Cosine Similarity | 计算向量夹角相似度 |
| Euclidean Distance | 计算向量空间中的欧氏距离 |
| Dot Product | 计算向量点积 |


在 RAG 场景中，Cosine Similarity 是非常常见的选择。

### 11.2 Cosine Similarity
公式：

```plain
cos(A, B) = A · B / (||A|| × ||B||)
```

其中：

+ A：Query Vector
+ B：Document Vector
+ A · B：向量点积
+ ||A||：A 的模长
+ ||B||：B 的模长

一般来说：

```plain
Cosine Similarity 越高
    ↓
语义方向越接近
```

但是需要注意：

不同模型、不同距离策略、不同向量归一化方式下，分数的含义不完全一样。

不能将某个固定分数阈值直接套用到所有模型。

---

## 十二、Metadata Filter 实战
企业级知识库检索不能只考虑语义相似度。

还必须考虑：

+ 所属企业
+ 所属部门
+ 知识库
+ 文档类型
+ 权限范围
+ 文档版本
+ 发布时间
+ 数据状态

### 12.1 为什么 Metadata Filter 很重要？
例如：

```plain
用户：
我想查询公司的年假政策。
```

系统有两个企业：

```plain
tenant_001
tenant_002
```

如果不进行租户过滤，可能检索到其他企业的年假政策。

这属于严重的数据隔离问题。

### 12.2 Metadata Filter 代码
使用 PGVectorStore：

```plain
results = await vector_store.asimilarity_search(
    query="员工年假申请流程",
    k=5,
    filter={
        "tenant_id": {
            "$eq": "tenant_001"
        }
    },
)
```

多个条件：

```python
results = await vector_store.asimilarity_search(
    query="员工年假申请流程",
    k=5,
    filter={
        "$and": [
            {
                "tenant_id": {
                    "$eq": "tenant_001"
                }
            },
            {
                "department": {
                    "$eq": "HR"
                }
            },
        ]
    },
)
```

注意：

Metadata Filter 的表达式与具体 Vector Store 实现有关。

PGVectorStore 的过滤语法不能直接套用 Chroma、Qdrant 等其他数据库的 API。

企业项目中，**租户隔离和权限过滤必须由服务端强制执行，不能依赖用户输入的过滤条件。**

---

## 十三、Vector Index：向量索引
### 13.1 为什么需要向量索引？
如果向量数据库存储：

```plain
100 条向量
```

可以直接搜索。

但是如果有：

```plain
100 万条向量
1000 万条向量
1 亿条向量
```

每次查询都扫描所有向量，性能可能无法满足业务需求。

因此，需要建立 Vector Index。

### 13.2 常见向量索引
| Index | 特点 |
| --- | --- |
| HNSW | 高性能近似最近邻检索，常见企业方案 |
| IVFFlat | 基于聚类的近似向量检索 |
| Flat | 精确检索，通常无 ANN 索引 |


### 13.3 使用 PGVectorStore 创建 HNSW Index
```python
from langchain_postgres.v2.indexes import HNSWIndex

from vector_store import initialize_vector_store


async def main():
    vector_store = await initialize_vector_store()

    index = HNSWIndex(
        name="enterprise_knowledge_hnsw"
    )

    await vector_store.aapply_vector_index(index)

    print("HNSW Index 创建成功")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

生产环境需要根据：

+ 数据量
+ 查询 QPS
+ 召回率要求
+ 内存
+ 索引构建时间
+ 数据更新频率

调整索引参数。

向量索引通常通过牺牲部分精确性换取查询性能。

因此，索引配置也需要通过 Retrieval Evaluation 验证。

参考：

[https://github.com/langchain-ai/langchain-postgres](https://github.com/langchain-ai/langchain-postgres)

---

## 十四、向量数据删除与更新
企业知识库不是一次性数据。

文档可能：

+ 更新
+ 删除
+ 重新上传
+ 修改权限
+ 重新切分
+ 更换 Embedding 模型

### 14.1 删除向量
```plain
await vector_store.adelete([
    "document_chunk_id_001",
])
```

### 14.2 更新向量
企业项目中的更新通常采用：

```plain
旧文档版本
    ↓
删除旧 Chunk
    ↓
重新切分
    ↓
重新 Embedding
    ↓
写入新 Chunk
```

也可以通过稳定 ID 覆盖旧记录，但必须明确当前 VectorStore 的 ID 更新行为。

### 14.3 为什么文档更新需要重新 Embedding？
假设原始文档：

```plain
年假申请需要提前3个工作日。
```

修改为：

```plain
年假申请需要提前5个工作日。
```

原有 Embedding Vector 代表旧文本语义。

因此，不能只更新原始文本而继续使用旧向量。

正确流程：

```plain
Document Update
    ↓
Chunk Rebuild
    ↓
Embedding Recompute
    ↓
Vector Update
```

---

## 十五、Embedding 缓存
在企业知识库中，重复 Embedding 可能产生不必要的成本。

例如：

```plain
10000 个文档
```

重新执行入库时，如果所有文档都重新 Embedding：

```plain
重复计算
    ↓
重复消耗 API
    ↓
增加成本
```

可以使用 LangChain 的 Embedding Cache。

官方提供：

```plain
CacheBackedEmbeddings
```

通过缓存减少重复向量化。

官方文档：

[https://docs.langchain.com/oss/python/integrations/embeddings](https://docs.langchain.com/oss/python/integrations/embeddings)

企业建议：

+ 文档内容 Hash
+ Embedding 模型版本
+ 缓存 Key
+ 缓存过期策略
+ 文档更新检测
+ Embedding 失败重试

需要注意：

更换 Embedding 模型后，缓存命名空间应包含模型标识，避免错误复用旧模型向量。

---

## 十六、企业级 Embedding 架构
一个真实企业知识库的 Embedding 架构可以设计为：

```plain
              文档上传
                   ↓
            Document Loader
                   ↓
            Text Splitter
                   ↓
         Document Normalization
                   ↓
          Embedding Service
                   ↓
          Embedding Cache
                   ↓
         Vector Store Adapter
                   ↓
        PostgreSQL + pgvector
                   ↓
             Vector Index
                   ↓
          Retrieval Service
                   ↓
          Metadata Filter
                   ↓
          Context Compression
                   ↓
             LLM Answer
```

建议在企业项目中将以下模块独立设计：

```plain
EmbeddingService
VectorStoreService
DocumentService
RetrievalService
KnowledgeBaseService
```

不要将文档上传、向量化、向量入库、搜索全部写在一个业务接口中。

### 16.1 Embedding Service
负责：

+ Embedding 模型调用
+ 批量向量化
+ 模型切换
+ Embedding Cache
+ 失败重试
+ Token 统计
+ 模型版本管理

### 16.2 VectorStore Service
负责：

+ Vector Store 初始化
+ 文档入库
+ 文档删除
+ 文档更新
+ 相似度搜索
+ Metadata Filter
+ Vector Index 管理

### 16.3 Retrieval Service
负责：

+ Query Embedding
+ Vector Search
+ Hybrid Search
+ Top-K
+ Reranking
+ Context Compression

第 43 章将进一步实现高级 Retrieval。

---

## 十七、Embedding 模型切换的企业级注意事项
假设原有系统使用：

```plain
text-embedding-3-small
```

后来决定切换：

```plain
Qwen3-Embedding
```

不能直接修改：

```plain
EMBEDDING_PROVIDER=ollama
```

然后继续查询旧向量。

原因：

1. 不同模型具有不同的向量空间。
2. 不同模型的维度可能不同。
3. 相同文本生成的向量也不相同。
4. 新 Query Vector 与旧 Document Vector 不具备可靠的可比性。

正确方案：

```plain
旧 Embedding Model
        ↓
旧 Vector Index

新 Embedding Model
        ↓
新 Vector Index

        ↓
数据验证

        ↓
切换 Retrieval
```

企业可以采用：

+ 双索引并行构建
+ 新旧模型召回效果对比
+ 灰度切换
+ 回滚机制
+ 完整重建后切换

这也是为什么企业知识库需要设计 Embedding Model Version。

---

## 十八、企业级项目中如何选择 Embedding 与 Vector Database？
### 18.1 中小企业知识库
```plain
Embedding：
Qwen3-Embedding / BGE-M3 / OpenAI

Vector DB：
PostgreSQL + pgvector

RAG：
LangChain + LangGraph

适用：
企业内部知识库、客服助手、研发助手
```

### 18.2 大规模知识检索平台
```plain
Embedding：
独立 Embedding Service

Vector DB：
Qdrant / Milvus

RAG：
LangChain + LangGraph

适用：
大规模文档检索、复杂向量搜索
```

### 18.3 企业数据分析 Agent
```plain
PostgreSQL
    ↓
业务结构化数据

ClickHouse
    ↓
分析型数据

pgvector
    ↓
业务知识与语义检索

LangGraph
    ↓
Agent Workflow
```

需要明确：

向量数据库不是万能数据库。

业务数据、关系数据、分析数据、知识向量应根据数据特点选择合理的存储架构。

---

## 十九、本章实战验收
完成本章后，需要能够完成以下操作：

```plain
[ ] 安装 Ollama
[ ] 下载 Qwen3-Embedding 模型
[ ] 使用 LangChain 调用 Embedding
[ ] 实现 embed_query
[ ] 实现 embed_documents
[ ] 检测向量维度
[ ] 搭建 PostgreSQL + pgvector
[ ] 初始化 PGVectorStore
[ ] 文档向量入库
[ ] 实现相似度搜索
[ ] 实现 Top-K 检索
[ ] 实现 Metadata Filter
[ ] 创建 HNSW Index
[ ] 实现向量删除
[ ] 实现 Embedding 模型切换
```

最终形成：

```plain
embedding-vector-demo/
├── embedding_factory.py
├── vector_store.py
├── ingest.py
├── search.py
├── embedding_demo.py
└── docker-compose.yml
```

---

## 二十、本章总结
本章需要重点掌握的核心概念：

| 概念 | 作用 |
| --- | --- |
| Embedding | 将文本转换为语义向量 |
| Embedding Model | 负责生成文本向量 |
| Vector Database | 存储与检索向量 |
| Vector Index | 提升向量检索性能 |
| Similarity Search | 根据语义相似度搜索 |
| Top-K | 返回最相似的 K 条结果 |
| Metadata Filter | 根据业务属性过滤数据 |
| Embedding Cache | 减少重复向量化 |
| Model Version | 管理 Embedding 模型版本 |


本章核心链路：

```plain
Document
    ↓
Embedding Model
    ↓
Vector
    ↓
PostgreSQL + pgvector
    ↓
Similarity Search
    ↓
Top-K Documents
    ↓
RAG Context
```

### 官方参考文档
1. LangChain Embedding Models  
[https://docs.langchain.com/oss/python/integrations/embeddings](https://docs.langchain.com/oss/python/integrations/embeddings)
2. LangChain Ollama Embeddings  
[https://reference.langchain.com/python/langchain-ollama/embeddings/OllamaEmbeddings](https://reference.langchain.com/python/langchain-ollama/embeddings/OllamaEmbeddings)
3. LangChain PostgreSQL Vector Store  
[https://github.com/langchain-ai/langchain-postgres](https://github.com/langchain-ai/langchain-postgres)
4. LangChain PGVectorStore  
[https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector](https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector)
5. Ollama  
[https://ollama.com](https://ollama.com/)

---

 
