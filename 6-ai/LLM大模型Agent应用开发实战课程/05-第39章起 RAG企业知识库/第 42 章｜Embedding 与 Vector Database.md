---

# 一、本章定位
前面我们已经完成：

```plain
第 39 章｜RAG 原理
第 40 章｜企业文档解析
第 41 章｜Chunk 文档切分
```

现在链路已经走到了这里：

```plain
原始文件
 ↓
ParsedDocument
 ↓
ChunkDocument
 ↓
Embedding
 ↓
Vector Database
```

第 40 章解决：

```plain
文件怎么解析。
```

第 41 章解决：

```plain
文档怎么切成 Chunk。
```

这一章解决：

```plain
Chunk 怎么变成向量，并支持语义检索。
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Embedding 是什么
2. 为什么 RAG 需要 Embedding
3. 向量维度是什么
4. 为什么 query 和 document 必须使用同一个 Embedding 模型
5. Cosine Similarity 是什么
6. Dot Product 是什么
7. Euclidean Distance 是什么
8. Vector Database 是什么
9. Vector Database 和 MySQL 的区别
10. 向量库里到底存什么
11. chunk_id / content / embedding / metadata 如何设计
12. TopK 检索是什么
13. metadata filter 怎么做
14. similarity_search 怎么实现
15. 为什么要返回 score
16. Chroma 适合什么场景
17. pgvector 适合什么场景
18. Qdrant / Milvus / Elasticsearch 怎么选
19. 如何封装 EmbeddingService
20. 如何封装 VectorStoreService
21. 如何接入第 41 章 ChunkDocument
22. 如何设计 FastAPI 检索接口
23. 面试中如何讲 Embedding 和向量数据库
```

---

# 三、Embedding 一句话解释
## 【实操】
```plain
Embedding
=
把文本转换成一组能表示语义的数字向量。
```

比如：

```plain
订单未发货可以退款
```

转换成：

```plain
[0.013, -0.245, 0.786, ...]
```

---

## 【重点内容】
大家先记住一句话：

Embedding 就是把文本变成向量，让机器能用数学方式比较语义相似度。

普通关键词搜索看的是字面匹配。

Embedding 搜索看的是语义接近。

比如用户问：

```plain
没发货能退钱吗？
```

文档里写：

```plain
订单未发货时，可以申请取消订单并退款。
```

这两个句子字面不完全一样。

但是意思很接近。

Embedding 的作用，就是让它们在向量空间里靠得比较近。

LangChain Embeddings 文档也说明，Embedding 模型会把文本转换成固定长度的数字向量，用来做语义比较和搜索。

---

# 四、为什么 RAG 需要 Embedding
RAG 的核心问题是：

```plain
用户问一句自然语言问题，
系统要从大量文档 Chunk 里找出最相关的片段。
```

如果只靠关键词，会有问题：

```plain
用户说：没发货能退钱吗？
文档写：订单未发货时，可以申请取消订单并退款。
```

关键词不完全一致。

但是语义一致。

Embedding 可以解决：

```plain
同义表达
近义表达
口语表达
跨语言表达
行业术语表达
```

所以 RAG 需要：

```plain
Chunk -> Embedding
Question -> Embedding
相似度计算
返回最相关 Chunk
```

---

# 五、Embedding 的标准流程
离线阶段：

```plain
ChunkDocument.content
 ↓
Embedding Model
 ↓
chunk_embedding
 ↓
Vector Database
```

在线阶段：

```plain
User Question
 ↓
同一个 Embedding Model
 ↓
query_embedding
 ↓
Vector Database similarity_search
 ↓
TopK Chunk
```

---

## 【重点内容】
注意一个非常关键的点：

文档 Chunk 和用户问题，必须使用同一个 Embedding 模型。

如果入库时用模型 A，查询时用模型 B，向量空间可能不一致。

就像你用两套坐标系，一个用米，一个用英尺，直接比较会出问题。

所以工程里一定要保存：

```plain
embedding_model
embedding_dimension
embedding_version
```

---

# 六、向量维度是什么
Embedding 输出的是固定长度向量。

比如：

```plain
384 维
768 维
1024 维
1536 维
3072 维
```

可以理解成：

```plain
每个文本被映射到一个高维语义空间。
```

向量维度不是越大越好。

维度越大：

```plain
1. 存储更大
2. 检索成本更高
3. 索引更重
4. 可能效果更好，但不绝对
```

---

## 【重点内容】
大家不要只看维度。

Embedding 模型选型要看：

```plain
中文效果
行业语料效果
成本
延迟
维度
部署方式
是否支持私有化
是否支持批量 embedding
```

企业知识库里，Embedding 模型选错，后面召回效果会很受影响。

---

# 七、相似度计算
常见相似度有三种。

## 1. Cosine Similarity
```plain
看两个向量方向是否接近。
```

常用于文本语义相似度。

## 2. Dot Product
```plain
看两个向量点积大小。
```

如果向量已经归一化，点积和 cosine 很接近。

## 3. Euclidean Distance
```plain
看两个向量距离有多远。
```

距离越小越相似。

pgvector 官方文档支持 L2 distance、inner product、cosine distance、L1 distance 等多种向量距离操作符，用来在 PostgreSQL 中做向量相似度检索。

---

# 八、Vector Database 是什么
## 【实操】
```plain
Vector Database
=
专门存储向量，并支持相似度搜索的数据库。
```

它通常保存：

```plain
chunk_id
document_id
content
embedding
metadata
created_at
```

---

## 【重点内容】
向量数据库不是替代 MySQL。

MySQL 擅长：

```plain
精确查询
事务
关系数据
订单表
用户表
权限表
```

向量数据库擅长：

```plain
语义相似度搜索
TopK 检索
向量索引
近似最近邻查询
```

企业 RAG 里常见组合是：

```plain
PostgreSQL / MySQL：
存文档记录、权限、版本、任务状态。

Vector Database：
存 Chunk 向量，用于语义检索。
```

---

# 九、向量库里到底存什么
推荐最小结构：

```json
{
  "chunk_id": "doc_001_chunk_003",
  "document_id": "doc_001",
  "content": "订单未发货时，用户可以申请取消订单并退款。",
  "embedding": [0.013, -0.245, 0.786],
  "metadata": {
    "tenant_id": "tenant_001",
    "doc_type": "after_sales",
    "source_path": "after_sales.md",
    "page_number": 3,
    "heading": "退款规则",
    "version": "2026-08"
  }
}
```

注意：

```plain
content 和 metadata 都要保存。
```

只保存向量不够。

因为最终回答要展示：

```plain
召回内容
来源文档
页码
标题
相似度分数
```

LangChain Vector Store 文档里也把 `Document` 的 `page_content` 和 `metadata` 作为向量库添加与检索的重要结构，检索时可以使用 `similarity_search` 和 `filter`。

---

# 十、Vector Database 选型
常见选择：

```plain
1. Chroma
2. pgvector
3. Qdrant
4. Milvus
5. Elasticsearch
6. Pinecone
7. Weaviate
```

本课程重点讲：

```plain
本地教学：InMemoryVectorStore / Chroma
企业轻量：pgvector
中大型向量检索：Qdrant / Milvus
搜索 + 向量混合：Elasticsearch
```

---

## 选型表
| 方案 | 适合场景 | 优点 | 注意点 |
| --- | --- | --- | --- |
| InMemory | 教学 Demo | 简单、无需部署 | 重启丢数据 |
| Chroma | 本地开发、小型知识库 | 上手快、Python 友好 | 大规模生产要评估 |
| pgvector | 已经有 PostgreSQL 的企业 | SQL、权限、业务数据整合方便 | 大规模向量检索性能要调优 |
| Qdrant | 向量检索服务化 | 过滤能力强、部署清晰 | 多一套服务 |
| Milvus | 大规模向量检索 | 面向大规模向量场景 | 运维成本较高 |
| Elasticsearch | 关键词 + 向量混合搜索 | BM25 + dense vector 混合 | 配置复杂度更高 |


LangChain 官方维护了多个向量库集成，包括 Chroma、FAISS、Milvus、Qdrant、Elasticsearch、PGVector 等，并提供统一的 VectorStore 接口。

---

# 十一、Chroma 适合什么场景
Chroma 适合：

```plain
1. 本地开发
2. Demo
3. 中小型知识库
4. 快速验证 RAG 流程
5. Python 项目教学
```

Chroma 支持基于 metadata 的过滤，查询时可以结合 `where` 做 metadata filter，也支持传入 query embeddings 进行向量检索。

LangChain 的 Chroma 集成也支持添加文档、删除文档、相似度搜索、带 filter 的搜索、带 score 的搜索，以及 as retriever 用法。

---

# 十二、pgvector 适合什么场景
pgvector 适合：

```plain
1. 企业已经使用 PostgreSQL
2. 知识库规模不是特别巨大
3. 希望文档、权限、Chunk、向量都放在同一个数据库体系
4. 希望用 SQL 做 metadata filter
5. 希望降低额外运维成本
```

pgvector 是 PostgreSQL 的开源向量相似度搜索扩展，可以在 PostgreSQL 中存储向量并做相似度检索。

LangChain 的 PGVector 集成支持向量检索，也支持对文档 metadata 应用过滤条件。

---

# 十三、Qdrant / Milvus / Elasticsearch 怎么理解
Qdrant：

```plain
更像专业向量检索服务，适合需要服务化部署和复杂 filter 的场景。
```

LangChain 的 Qdrant 集成支持 similarity_search 和 similarity_search_with_score，并可以传入 Qdrant 的 filter 对象做过滤。

Milvus：

```plain
更偏大规模向量检索，适合数据量较大、检索要求高的场景。
```

LangChain 的 Milvus 集成支持相似度搜索，也可以在 retriever 调用时传入 filter。

Elasticsearch：

```plain
适合关键词检索 + 向量检索混合的企业搜索场景。
```

LangChain 的 Elasticsearch 集成支持向量检索，也可以配合 filter 做 metadata 条件过滤。

---

# 十四、本章代码目标
这一章我们先做一个：

```plain
不依赖真实大模型 Key
不依赖外部向量数据库
下载后可以直接运行
```

的教学版向量检索模块。

它包含：

```plain
1. DeterministicHashEmbedding
2. InMemoryVectorStore
3. EmbeddingService
4. VectorStoreService
5. KnowledgeIndexingService
6. similarity_search
7. metadata_filter
8. parse + chunk + embed + search 完整流程
9. FastAPI 检索接口
```

后面再给：

```plain
Chroma 示例
pgvector SQL 示例
LangChain VectorStore 示例
```

---

# 十五、本章项目结构
新增目录：

```plain
ai-agent-course/
├── app/
│   ├── vector_knowledge/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── embedding.py
│   │   ├── similarity.py
│   │   ├── vector_store.py
│   │   ├── service.py
│   │   ├── langchain_examples.py
│   │   ├── pgvector_examples.py
│   │   ├── demo_01_embedding.py
│   │   ├── demo_02_similarity.py
│   │   ├── demo_03_vector_store.py
│   │   ├── demo_04_metadata_filter.py
│   │   ├── demo_05_parse_chunk_embed_search.py
│   │   └── demo_06_rebuild_index.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── vector_knowledge.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_vector42_01_embedding.py
│   ├── test_vector42_02_similarity.py
│   ├── test_vector42_03_vector_store.py
│   ├── test_vector42_04_metadata_filter.py
│   ├── test_vector42_05_parse_chunk_embed_search.py
│   └── test_vector42_06_rebuild_index.py
│
└── README.md
```

---

# 十六、创建目录和文件
执行：

```bash
mkdir -p app/vector_knowledge

touch app/vector_knowledge/__init__.py
touch app/vector_knowledge/schemas.py
touch app/vector_knowledge/embedding.py
touch app/vector_knowledge/similarity.py
touch app/vector_knowledge/vector_store.py
touch app/vector_knowledge/service.py
touch app/vector_knowledge/langchain_examples.py
touch app/vector_knowledge/pgvector_examples.py
touch app/vector_knowledge/demo_01_embedding.py
touch app/vector_knowledge/demo_02_similarity.py
touch app/vector_knowledge/demo_03_vector_store.py
touch app/vector_knowledge/demo_04_metadata_filter.py
touch app/vector_knowledge/demo_05_parse_chunk_embed_search.py
touch app/vector_knowledge/demo_06_rebuild_index.py

touch app/api/v1/vector_knowledge.py

touch scripts/test_vector42_01_embedding.py
touch scripts/test_vector42_02_similarity.py
touch scripts/test_vector42_03_vector_store.py
touch scripts/test_vector42_04_metadata_filter.py
touch scripts/test_vector42_05_parse_chunk_embed_search.py
touch scripts/test_vector42_06_rebuild_index.py
```

Windows PowerShell：

```powershell
mkdir app\vector_knowledge

New-Item app\vector_knowledge\__init__.py
New-Item app\vector_knowledge\schemas.py
New-Item app\vector_knowledge\embedding.py
New-Item app\vector_knowledge\similarity.py
New-Item app\vector_knowledge\vector_store.py
New-Item app\vector_knowledge\service.py
New-Item app\vector_knowledge\langchain_examples.py
New-Item app\vector_knowledge\pgvector_examples.py
New-Item app\vector_knowledge\demo_01_embedding.py
New-Item app\vector_knowledge\demo_02_similarity.py
New-Item app\vector_knowledge\demo_03_vector_store.py
New-Item app\vector_knowledge\demo_04_metadata_filter.py
New-Item app\vector_knowledge\demo_05_parse_chunk_embed_search.py
New-Item app\vector_knowledge\demo_06_rebuild_index.py
```

---

# 十七、定义 Schema
打开：

```plain
app/vector_knowledge/schemas.py
```

写入：

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.document_chunking.schemas import ChunkDocument


class EmbeddingProvider(str, Enum):
    HASH = "hash"
    OPENAI = "openai"
    QWEN = "qwen"
    BGE = "bge"
    JINA = "jina"


class VectorStoreProvider(str, Enum):
    IN_MEMORY = "in_memory"
    CHROMA = "chroma"
    PGVECTOR = "pgvector"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class EmbeddingConfig:
    provider: EmbeddingProvider = EmbeddingProvider.HASH
    model_name: str = "deterministic-hash-embedding"
    dimension: int = 128
    normalize: bool = True


@dataclass
class EmbeddedChunk:
    chunk_id: str
    document_id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchRequest:
    query: str
    top_k: int = 5
    metadata_filter: dict[str, Any] | None = None


@dataclass
class VectorSearchResponse:
    query: str
    top_k: int
    results: list[VectorSearchResult]


@dataclass
class IndexBuildResult:
    total_chunks: int
    embedded_chunks: int
    provider: EmbeddingProvider
    vector_store: VectorStoreProvider
    warnings: list[str] = field(default_factory=list)


@dataclass
class ChunkEmbeddingRequest:
    chunk: ChunkDocument
    config: EmbeddingConfig
```

---

## 【重点内容】
这里我们定义几个核心对象。

`EmbeddingConfig` 表示使用什么 embedding 模型。

`EmbeddedChunk` 表示一个已经向量化的 Chunk。

`VectorSearchResult` 表示检索结果。

`VectorSearchRequest` 表示用户查询。

这里重点看：

```plain
chunk_id
document_id
content
embedding
metadata
score
```

这些字段是向量检索的核心。

---

# 十八、实现相似度计算
打开：

```plain
app/vector_knowledge/similarity.py
```

写入：

```python
import math


def dot_product(
    left: list[float],
    right: list[float],
) -> float:
    _validate_vector_size(left, right)

    return sum(
        a * b
        for a, b in zip(left, right)
    )


def vector_norm(
    vector: list[float],
) -> float:
    return math.sqrt(
        sum(value * value for value in vector)
    )


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    _validate_vector_size(left, right)

    left_norm = vector_norm(left)
    right_norm = vector_norm(right)

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot_product(left, right) / (left_norm * right_norm)


def euclidean_distance(
    left: list[float],
    right: list[float],
) -> float:
    _validate_vector_size(left, right)

    return math.sqrt(
        sum(
            (a - b) * (a - b)
            for a, b in zip(left, right)
        )
    )


def normalize_vector(
    vector: list[float],
) -> list[float]:
    norm = vector_norm(vector)

    if norm == 0:
        return vector

    return [
        value / norm
        for value in vector
    ]


def _validate_vector_size(
    left: list[float],
    right: list[float],
) -> None:
    if len(left) != len(right):
        raise ValueError(
            f"向量维度不一致：left={len(left)}, right={len(right)}"
        )
```

---

## 【重点内容】
这里手写了三个函数：

```plain
dot_product
cosine_similarity
euclidean_distance
```

真实向量库内部会帮我们做这些。

但这一章要先让大家理解底层原理。

如果你连相似度是什么都不知道，后面调向量库参数就会很虚。

---

# 十九、实现教学版 Embedding
打开：

```plain
app/vector_knowledge/embedding.py
```

写入：

```python
import hashlib
import re
from abc import ABC, abstractmethod

from app.vector_knowledge.schemas import EmbeddingConfig
from app.vector_knowledge.similarity import normalize_vector


class BaseEmbeddingModel(ABC):
    @abstractmethod
    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        raise NotImplementedError

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self.embed_text(text)
            for text in texts
        ]


class DeterministicHashEmbedding(BaseEmbeddingModel):
    """
    教学版 Embedding。

    特点：
    1. 不依赖外部 API Key。
    2. 同一段文本每次生成相同向量。
    3. 支持中文关键词和字符级 hash。
    4. 只用于教学，不代表真实语义 Embedding 效果。
    """

    def __init__(
        self,
        config: EmbeddingConfig,
    ):
        self.config = config
        self.dimension = config.dimension

        self.keyword_boosts = {
            "订单": 3.0,
            "未发货": 3.0,
            "发货": 2.0,
            "退款": 3.0,
            "退货": 2.5,
            "售后": 2.5,
            "物流": 3.0,
            "快递": 2.5,
            "发票": 3.0,
            "企业": 2.0,
            "个人": 2.0,
            "年假": 3.0,
            "报销": 3.0,
            "合同": 3.0,
            "付款": 2.5,
            "客服": 2.0,
        }

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        vector = [0.0 for _ in range(self.dimension)]

        tokens = self._tokenize(text)

        for token in tokens:
            index = self._hash_to_index(token)
            vector[index] += 1.0

        for keyword, weight in self.keyword_boosts.items():
            if keyword in text:
                index = self._hash_to_index(f"keyword:{keyword}")
                vector[index] += weight

        if self.config.normalize:
            vector = normalize_vector(vector)

        return vector

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:
        normalized = text.lower().strip()

        english_tokens = re.findall(
            r"[a-zA-Z0-9_]+",
            normalized,
        )

        chinese_chars = [
            char for char in normalized
            if "\u4e00" <= char <= "\u9fff"
        ]

        return english_tokens + chinese_chars

    def _hash_to_index(
        self,
        token: str,
    ) -> int:
        digest = hashlib.md5(
            token.encode("utf-8")
        ).hexdigest()

        return int(digest, 16) % self.dimension


class EmbeddingModelFactory:
    def create(
        self,
        config: EmbeddingConfig,
    ) -> BaseEmbeddingModel:
        if config.provider.value == "hash":
            return DeterministicHashEmbedding(config)

        raise ValueError(
            f"当前教学版暂不支持该 Embedding Provider：{config.provider}"
        )
```

---

## 【重点内容】
这里我们写的是教学版 Embedding。

它不是专业语义模型。

它的价值是：

```plain
不需要 API Key
下载就能跑
能理解文本 -> 向量 -> 相似度搜索的流程
```

真实项目里会替换成：

```plain
OpenAI Embedding
通义千问 Embedding
BGE Embedding
Jina Embedding
本地 Embedding 模型
```

但服务接口不用变。

只要替换 `EmbeddingModelFactory` 就行。

这就是工程抽象的意义。

---

# 二十、实现 InMemory Vector Store
打开：

```plain
app/vector_knowledge/vector_store.py
```

写入：

```python
from app.vector_knowledge.schemas import (
    EmbeddedChunk,
    VectorSearchResult,
)
from app.vector_knowledge.similarity import cosine_similarity


class InMemoryVectorStore:
    """
    教学版 Vector Store。

    特点：
    1. 不依赖外部数据库。
    2. 支持 add / delete / search。
    3. 支持 metadata_filter。
    4. 只用于教学，不适合生产。
    """

    def __init__(self):
        self.items: dict[str, EmbeddedChunk] = {}

    def add(
        self,
        embedded_chunk: EmbeddedChunk,
    ) -> None:
        self.items[embedded_chunk.chunk_id] = embedded_chunk

    def add_many(
        self,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        for item in embedded_chunks:
            self.add(item)

    def delete(
        self,
        chunk_id: str,
    ) -> None:
        self.items.pop(
            chunk_id,
            None,
        )

    def delete_by_document_id(
        self,
        document_id: str,
    ) -> int:
        chunk_ids = [
            chunk_id
            for chunk_id, item in self.items.items()
            if item.document_id == document_id
        ]

        for chunk_id in chunk_ids:
            self.delete(chunk_id)

        return len(chunk_ids)

    def clear(self) -> None:
        self.items.clear()

    def count(self) -> int:
        return len(self.items)

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        metadata_filter: dict | None = None,
    ) -> list[VectorSearchResult]:
        candidates = list(self.items.values())

        if metadata_filter:
            candidates = [
                item for item in candidates
                if self._match_metadata_filter(
                    item.metadata,
                    metadata_filter,
                )
            ]

        results: list[VectorSearchResult] = []

        for item in candidates:
            score = cosine_similarity(
                query_embedding,
                item.embedding,
            )

            results.append(
                VectorSearchResult(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    content=item.content,
                    score=score,
                    metadata=item.metadata,
                )
            )

        results.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return results[:top_k]

    def _match_metadata_filter(
        self,
        metadata: dict,
        metadata_filter: dict,
    ) -> bool:
        for key, expected_value in metadata_filter.items():
            actual_value = metadata.get(key)

            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            else:
                if actual_value != expected_value:
                    return False

        return True
```

---

## 【重点内容】
这个 InMemoryVectorStore 模拟真实向量库。

它支持：

```plain
add
delete
delete_by_document_id
similarity_search
metadata_filter
```

真实项目里换成 Chroma、pgvector、Qdrant、Milvus，本质也是这些能力。

区别只是底层实现不同。

---

# 二十一、封装 Service
打开：

```plain
app/vector_knowledge/service.py
```

写入：

```python
from app.document_chunking.schemas import (
    ChunkConfig,
    ChunkDocument,
    ChunkStrategy,
)
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service
from app.vector_knowledge.embedding import EmbeddingModelFactory
from app.vector_knowledge.schemas import (
    EmbeddedChunk,
    EmbeddingConfig,
    IndexBuildResult,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorStoreProvider,
)
from app.vector_knowledge.vector_store import InMemoryVectorStore


class EmbeddingService:
    def __init__(
        self,
        config: EmbeddingConfig | None = None,
    ):
        self.config = config or EmbeddingConfig()
        self.model = EmbeddingModelFactory().create(self.config)

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        return self.model.embed_text(text)

    def embed_chunks(
        self,
        chunks: list[ChunkDocument],
    ) -> list[EmbeddedChunk]:
        texts = [
            chunk.content
            for chunk in chunks
        ]

        embeddings = self.model.embed_texts(texts)

        embedded_chunks: list[EmbeddedChunk] = []

        for chunk, embedding in zip(chunks, embeddings):
            embedded_chunks.append(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    embedding=embedding,
                    metadata={
                        **chunk.metadata,
                        "embedding_provider": self.config.provider.value,
                        "embedding_model": self.config.model_name,
                        "embedding_dimension": self.config.dimension,
                    },
                )
            )

        return embedded_chunks


class VectorKnowledgeService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = InMemoryVectorStore()

    def index_chunks(
        self,
        chunks: list[ChunkDocument],
    ) -> IndexBuildResult:
        embedded_chunks = self.embedding_service.embed_chunks(
            chunks
        )

        self.vector_store.add_many(
            embedded_chunks
        )

        return IndexBuildResult(
            total_chunks=len(chunks),
            embedded_chunks=len(embedded_chunks),
            provider=self.embedding_service.config.provider,
            vector_store=VectorStoreProvider.IN_MEMORY,
            warnings=[
                "当前使用 InMemoryVectorStore，仅适合教学和本地 Demo。"
            ],
        )

    def index_file(
        self,
        file_path: str,
        tenant_id: str = "tenant_001",
        created_by: str = "system",
        chunk_strategy: ChunkStrategy = ChunkStrategy.HEADING,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ) -> IndexBuildResult:
        parsed_document = document_parsing_service.parse_file(
            file_path=file_path,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        chunk_result = document_chunking_service.split_document(
            parsed_document,
            config=ChunkConfig(
                strategy=chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_size=10,
            ),
        )

        return self.index_chunks(
            chunk_result.chunks
        )

    def search(
        self,
        request: VectorSearchRequest,
    ) -> VectorSearchResponse:
        query_embedding = self.embedding_service.embed_text(
            request.query
        )

        results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter,
        )

        return VectorSearchResponse(
            query=request.query,
            top_k=request.top_k,
            results=results,
        )

    def clear_index(self) -> None:
        self.vector_store.clear()

    def count(self) -> int:
        return self.vector_store.count()


vector_knowledge_service = VectorKnowledgeService()
```

---

## 【重点内容】
这里我们把能力分了两层。

第一层：

```plain
EmbeddingService
```

负责：

```plain
文本向量化
Chunk 向量化
```

第二层：

```plain
VectorKnowledgeService
```

负责：

```plain
解析文件
切 Chunk
Embedding
写入向量库
检索
```

这就是企业项目里的分层。

---

# 二十二、示例一：Embedding 向量化
打开：

```plain
app/vector_knowledge/demo_01_embedding.py
```

写入：

```python
from app.vector_knowledge.service import EmbeddingService


def main():
    service = EmbeddingService()

    texts = [
        "订单未发货时，可以申请取消订单并退款。",
        "没发货能不能退钱？",
        "企业发票需要填写公司名称和纳税人识别号。",
    ]

    for text in texts:
        vector = service.embed_text(text)

        print("text:", text)
        print("dimension:", len(vector))
        print("first 10 dims:", vector[:10])
        print("norm approx:", round(sum(v * v for v in vector) ** 0.5, 4))
        print("-" * 80)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_01_embedding.py
```

写入：

```python
from app.vector_knowledge.demo_01_embedding import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_vector42_01_embedding.py
```

---

# 二十三、示例二：相似度计算
打开：

```plain
app/vector_knowledge/demo_02_similarity.py
```

写入：

```python
from app.vector_knowledge.service import EmbeddingService
from app.vector_knowledge.similarity import (
    cosine_similarity,
    dot_product,
    euclidean_distance,
)


def main():
    service = EmbeddingService()

    query = "没发货能退钱吗？"

    docs = [
        "订单未发货时，可以申请取消订单并退款。",
        "用户可以在订单完成后申请电子发票。",
        "物流超过 7 天没有更新，建议联系客服。",
    ]

    query_vector = service.embed_text(query)

    print("query:", query)
    print("=" * 80)

    for doc in docs:
        doc_vector = service.embed_text(doc)

        print("doc:", doc)
        print("cosine:", round(cosine_similarity(query_vector, doc_vector), 4))
        print("dot:", round(dot_product(query_vector, doc_vector), 4))
        print("euclidean:", round(euclidean_distance(query_vector, doc_vector), 4))
        print("-" * 80)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_02_similarity.py
```

写入：

```python
from app.vector_knowledge.demo_02_similarity import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这个例子让大家看到：

```plain
退款问题和退款文档的 cosine 更高。
发票文档和物流文档分数更低。
```

这就是向量语义检索的基本逻辑。

---

# 二十四、示例三：向量库写入和检索
打开：

```plain
app/vector_knowledge/demo_03_vector_store.py
```

写入：

```python
from app.document_chunking.schemas import ChunkDocument, ChunkStrategy
from app.vector_knowledge.schemas import VectorSearchRequest
from app.vector_knowledge.service import VectorKnowledgeService


def build_mock_chunks() -> list[ChunkDocument]:
    return [
        ChunkDocument(
            chunk_id="chunk_after_sales_001",
            document_id="doc_after_sales",
            title="电商售后规则",
            content="订单未发货时，用户可以申请取消订单并退款。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "after_sales",
                "source_path": "after_sales.txt",
            },
        ),
        ChunkDocument(
            chunk_id="chunk_logistics_001",
            document_id="doc_logistics",
            title="物流说明",
            content="物流超过 7 天没有更新，建议联系客服协助核查。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "logistics",
                "source_path": "logistics.txt",
            },
        ),
        ChunkDocument(
            chunk_id="chunk_invoice_001",
            document_id="doc_invoice",
            title="发票规则",
            content="企业发票需要填写公司名称和纳税人识别号。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "invoice",
                "source_path": "invoice.txt",
            },
        ),
    ]


def main():
    service = VectorKnowledgeService()

    chunks = build_mock_chunks()

    index_result = service.index_chunks(chunks)

    print("index_result:")
    print(index_result)
    print("=" * 80)

    response = service.search(
        VectorSearchRequest(
            query="没发货可以退款吗？",
            top_k=3,
        )
    )

    print("search response:")
    for result in response.results:
        print("chunk_id:", result.chunk_id)
        print("score:", round(result.score, 4))
        print("content:", result.content)
        print("metadata:", result.metadata)
        print("-" * 80)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_03_vector_store.py
```

写入：

```python
from app.vector_knowledge.demo_03_vector_store import main


if __name__ == "__main__":
    main()
```

---

# 二十五、示例四：metadata filter
打开：

```plain
app/vector_knowledge/demo_04_metadata_filter.py
```

写入：

```python
from app.vector_knowledge.demo_03_vector_store import build_mock_chunks
from app.vector_knowledge.schemas import VectorSearchRequest
from app.vector_knowledge.service import VectorKnowledgeService


def print_results(title: str, response):
    print(title)
    print("=" * 80)

    for result in response.results:
        print("chunk_id:", result.chunk_id)
        print("score:", round(result.score, 4))
        print("doc_type:", result.metadata.get("doc_type"))
        print("content:", result.content)
        print("-" * 80)

    print("=" * 120)


def main():
    service = VectorKnowledgeService()
    service.index_chunks(build_mock_chunks())

    no_filter = service.search(
        VectorSearchRequest(
            query="退款规则是什么？",
            top_k=3,
        )
    )

    print_results("不加 filter", no_filter)

    after_sales_filter = service.search(
        VectorSearchRequest(
            query="退款规则是什么？",
            top_k=3,
            metadata_filter={
                "doc_type": "after_sales",
            },
        )
    )

    print_results("只查售后规则", after_sales_filter)

    invoice_filter = service.search(
        VectorSearchRequest(
            query="退款规则是什么？",
            top_k=3,
            metadata_filter={
                "doc_type": "invoice",
            },
        )
    )

    print_results("只查发票规则", invoice_filter)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_04_metadata_filter.py
```

写入：

```python
from app.vector_knowledge.demo_04_metadata_filter import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
metadata filter 非常重要。

比如用户问退款，就应该优先查：

```plain
doc_type=after_sales
```

而不是把发票、物流、合同都一起查。

企业知识库里，metadata filter 还能做：

```plain
租户隔离
部门隔离
权限过滤
版本过滤
文档类型过滤
```

LangChain VectorStore 接口也支持在相似度搜索中传入 filter，用来按 metadata 过滤检索结果。

---

# 二十六、示例五：解析 + 切分 + 向量化 + 检索
打开：

```plain
app/vector_knowledge/demo_05_parse_chunk_embed_search.py
```

写入：

```python
from app.document_chunking.schemas import ChunkStrategy
from app.vector_knowledge.schemas import VectorSearchRequest
from app.vector_knowledge.service import VectorKnowledgeService


def main():
    service = VectorKnowledgeService()

    files = [
        "data/sample_docs/after_sales.txt",
        "data/sample_docs/employee_handbook.md",
        "data/sample_docs/help_center.html",
    ]

    for file_path in files:
        result = service.index_file(
            file_path=file_path,
            tenant_id="tenant_001",
            created_by="u_10001",
            chunk_strategy=ChunkStrategy.HEADING,
            chunk_size=180,
            chunk_overlap=30,
        )

        print("indexed:", file_path)
        print(result)
        print("-" * 80)

    print("vector count:", service.count())
    print("=" * 120)

    questions = [
        "订单还没发货，可以退款吗？",
        "年假制度是什么？",
        "帮助中心可以查什么问题？",
        "企业发票需要什么？",
    ]

    for question in questions:
        response = service.search(
            VectorSearchRequest(
                query=question,
                top_k=3,
                metadata_filter={
                    "tenant_id": "tenant_001",
                },
            )
        )

        print("question:", question)
        for item in response.results:
            print("score:", round(item.score, 4))
            print("content:", item.content)
            print("source:", item.metadata.get("source_path"))
            print("heading:", item.metadata.get("heading"))
            print("-" * 80)

        print("=" * 120)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_05_parse_chunk_embed_search.py
```

写入：

```python
from app.vector_knowledge.demo_05_parse_chunk_embed_search import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_vector42_05_parse_chunk_embed_search.py
```

---

## 【重点内容】
这个示例就是完整入库和检索链路。

它做了：

```plain
文档解析
Chunk 切分
Embedding
写入向量库
用户问题向量化
相似度搜索
返回 TopK
返回 score 和 metadata
```

到这里，我们已经把企业知识库的骨架跑通了。

---

# 二十七、示例六：重建索引
打开：

```plain
app/vector_knowledge/demo_06_rebuild_index.py
```

写入：

```python
from app.document_chunking.schemas import ChunkStrategy
from app.vector_knowledge.schemas import VectorSearchRequest
from app.vector_knowledge.service import VectorKnowledgeService


def main():
    service = VectorKnowledgeService()

    service.index_file(
        file_path="data/sample_docs/after_sales.txt",
        tenant_id="tenant_001",
        created_by="u_10001",
        chunk_strategy=ChunkStrategy.PARAGRAPH,
        chunk_size=120,
        chunk_overlap=20,
    )

    print("first count:", service.count())

    response = service.search(
        VectorSearchRequest(
            query="退款规则是什么？",
            top_k=3,
        )
    )

    print("first search:")
    for item in response.results:
        print(item.chunk_id, round(item.score, 4), item.content)

    print("=" * 80)

    service.clear_index()

    print("after clear count:", service.count())

    service.index_file(
        file_path="data/sample_docs/after_sales.txt",
        tenant_id="tenant_001",
        created_by="u_10001",
        chunk_strategy=ChunkStrategy.PARAGRAPH,
        chunk_size=80,
        chunk_overlap=10,
    )

    print("second count:", service.count())

    response = service.search(
        VectorSearchRequest(
            query="退款规则是什么？",
            top_k=3,
        )
    )

    print("second search:")
    for item in response.results:
        print(item.chunk_id, round(item.score, 4), item.content)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_vector42_06_rebuild_index.py
```

写入：

```python
from app.vector_knowledge.demo_06_rebuild_index import main


if __name__ == "__main__":
    main()
```

---

# 二十八、FastAPI 向量检索接口
打开：

```plain
app/api/v1/vector_knowledge.py
```

写入：

```python
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.document_chunking.schemas import ChunkStrategy
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.vector_knowledge.schemas import VectorSearchRequest
from app.vector_knowledge.service import vector_knowledge_service


router = APIRouter()


class IndexFileRequest(BaseModel):
    file_path: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")
    chunk_strategy: str = Field(default="heading")
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=80, ge=0)


class SearchKnowledgeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    metadata_filter: dict[str, Any] | None = None


@router.post(
    "/knowledge/index-file",
    response_model=ApiResponse[dict],
)
async def index_file(
    request: IndexFileRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    result = vector_knowledge_service.index_file(
        file_path=request.file_path,
        tenant_id=request.tenant_id,
        created_by=current_user.user_id,
        chunk_strategy=ChunkStrategy(request.chunk_strategy),
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )

    return ApiResponse[dict](
        data={
            "total_chunks": result.total_chunks,
            "embedded_chunks": result.embedded_chunks,
            "provider": result.provider.value,
            "vector_store": result.vector_store.value,
            "warnings": result.warnings,
        }
    )


@router.post(
    "/knowledge/search",
    response_model=ApiResponse[dict],
)
async def search_knowledge(
    request: SearchKnowledgeRequest,
) -> ApiResponse[dict]:
    response = vector_knowledge_service.search(
        VectorSearchRequest(
            query=request.query,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter,
        )
    )

    return ApiResponse[dict](
        data={
            "query": response.query,
            "top_k": response.top_k,
            "results": [
                {
                    "chunk_id": item.chunk_id,
                    "document_id": item.document_id,
                    "content": item.content,
                    "score": item.score,
                    "metadata": item.metadata,
                }
                for item in response.results
            ],
        }
    )


@router.delete(
    "/knowledge/index",
    response_model=ApiResponse[dict],
)
async def clear_index() -> ApiResponse[dict]:
    vector_knowledge_service.clear_index()

    return ApiResponse[dict](
        data={
            "message": "向量索引已清空",
            "count": vector_knowledge_service.count(),
        }
    )
```

---

# 二十九、注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.vector_knowledge import router as vector_knowledge_router
```

注册：

```python
api_router.include_router(
    vector_knowledge_router,
    tags=["Vector Knowledge"],
)
```

---

# 三十、测试接口
启动：

```bash
uv run uvicorn app.main:app --reload
```

先索引文件：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/knowledge/index-file" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "file_path": "data/sample_docs/after_sales.txt",
    "tenant_id": "tenant_001",
    "chunk_strategy": "paragraph",
    "chunk_size": 120,
    "chunk_overlap": 20
  }'
```

再检索：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/knowledge/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "订单还没发货，可以退款吗？",
    "top_k": 3,
    "metadata_filter": {
      "tenant_id": "tenant_001"
    }
  }'
```

---

# 三十一、LangChain VectorStore 示例
打开：

```plain
app/vector_knowledge/langchain_examples.py
```

写入：

```python
"""
LangChain VectorStore 示例。

说明：
1. 需要安装 langchain-core。
2. 这里使用 InMemoryVectorStore 做教学。
3. 真实项目可以替换成 Chroma / PGVector / Qdrant / Milvus。
"""


def demo_langchain_in_memory_vector_store():
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import InMemoryVectorStore

    class SimpleEmbeddings(Embeddings):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [
                self.embed_query(text)
                for text in texts
            ]

        def embed_query(self, text: str) -> list[float]:
            vector = [0.0, 0.0, 0.0]

            if "退款" in text or "未发货" in text:
                vector[0] = 1.0

            if "物流" in text or "快递" in text:
                vector[1] = 1.0

            if "发票" in text:
                vector[2] = 1.0

            return vector

    documents = [
        Document(
            page_content="订单未发货时，可以申请取消订单并退款。",
            metadata={
                "source": "after_sales",
                "doc_type": "after_sales",
            },
        ),
        Document(
            page_content="物流超过 7 天没有更新，建议联系客服。",
            metadata={
                "source": "logistics",
                "doc_type": "logistics",
            },
        ),
        Document(
            page_content="企业发票需要填写公司名称和纳税人识别号。",
            metadata={
                "source": "invoice",
                "doc_type": "invoice",
            },
        ),
    ]

    vector_store = InMemoryVectorStore(
        embedding=SimpleEmbeddings()
    )

    vector_store.add_documents(documents)

    results = vector_store.similarity_search(
        "没发货可以退款吗？",
        k=2,
        filter={
            "doc_type": "after_sales",
        },
    )

    for doc in results:
        print(doc.page_content, doc.metadata)


def main():
    demo_langchain_in_memory_vector_store()


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
LangChain 的 VectorStore 接口比较统一。

基本就是：

```plain
add_documents
similarity_search
similarity_search_with_score
as_retriever
delete
```

LangChain 官方 Vector Store 文档中也展示了 `similarity_search("your query here")` 和 `filter={"source": "tweets"}` 这类用法。

---

# 三十二、Chroma 示例
安装：

```bash
uv add langchain-chroma chromadb
```

示例：

```python
from langchain_core.documents import Document
from langchain_chroma import Chroma

vector_store = Chroma(
    collection_name="enterprise_knowledge",
    embedding_function=embeddings,
    persist_directory="./data/chroma_db",
)

docs = [
    Document(
        page_content="订单未发货时，可以申请取消订单并退款。",
        metadata={
            "tenant_id": "tenant_001",
            "doc_type": "after_sales",
        },
    )
]

vector_store.add_documents(
    documents=docs,
    ids=["chunk_001"],
)

results = vector_store.similarity_search(
    query="没发货可以退款吗？",
    k=3,
    filter={
        "tenant_id": "tenant_001",
        "doc_type": "after_sales",
    },
)
```

LangChain 的 Chroma 集成支持 `add_documents`、`similarity_search`、`similarity_search_with_score`、异步搜索，以及 `as_retriever`；Chroma 自身查询也支持 `where` metadata filter。

---

# 三十三、pgvector 表设计
PostgreSQL + pgvector 示例：

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    document_id VARCHAR(128) NOT NULL,
    chunk_id VARCHAR(255) NOT NULL UNIQUE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_dimension INT NOT NULL,
    embedding vector(128),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

创建索引示例：

```sql
CREATE INDEX knowledge_chunks_embedding_idx
ON knowledge_chunks
USING hnsw (embedding vector_cosine_ops);
```

查询示例：

```sql
SELECT
    chunk_id,
    content,
    metadata,
    1 - (embedding <=> :query_embedding) AS score
FROM knowledge_chunks
WHERE tenant_id = :tenant_id
ORDER BY embedding <=> :query_embedding
LIMIT 5;
```

pgvector 官方文档提供了在 PostgreSQL 中创建 `vector` 扩展、定义 `vector(n)` 列、执行距离排序和创建索引的用法；也建议用约束确保向量维度符合预期。

---

# 三十四、pgvector Python 示例文件
打开：

```plain
app/vector_knowledge/pgvector_examples.py
```

写入：

```python
"""
pgvector 示例文件。

说明：
1. 这是生产环境思路示例，不在本章默认运行。
2. 需要 PostgreSQL 安装 pgvector 扩展。
3. 需要根据真实 embedding 维度修改 vector(128)。
"""


PGVECTOR_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    document_id VARCHAR(128) NOT NULL,
    chunk_id VARCHAR(255) NOT NULL UNIQUE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding_model VARCHAR(128) NOT NULL,
    embedding_dimension INT NOT NULL,
    embedding vector(128),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


PGVECTOR_SEARCH_SQL = """
SELECT
    chunk_id,
    document_id,
    content,
    metadata,
    1 - (embedding <=> %(query_embedding)s) AS score
FROM knowledge_chunks
WHERE tenant_id = %(tenant_id)s
ORDER BY embedding <=> %(query_embedding)s
LIMIT %(top_k)s;
"""


def print_pgvector_sql():
    print("建表 SQL:")
    print(PGVECTOR_TABLE_SQL)

    print("=" * 80)

    print("查询 SQL:")
    print(PGVECTOR_SEARCH_SQL)


if __name__ == "__main__":
    print_pgvector_sql()
```

---

# 三十五、向量检索为什么要返回 score
返回 score 可以做：

```plain
1. 判断结果相关性
2. 做低分兜底
3. Debug 召回效果
4. 做 RAG Evaluation
5. 给前端展示依据强弱
6. 做 rerank 前的候选排序
```

比如：

```plain
score >= 0.75：
强相关

0.45 <= score < 0.75：
可能相关

score < 0.45：
可能不相关，需要兜底
```

---

## 【重点内容】
这里分数阈值不能照抄。

不同 embedding 模型、不同向量库、不同距离函数，分数含义都可能不同。

工程上要用真实数据校准。

不要直接写死：

```plain
score > 0.8 一定相关
```

这不严谨。

---

# 三十六、TopK 怎么选
TopK 太小：

```plain
可能漏掉正确 Chunk。
```

TopK 太大：

```plain
噪音变多，Prompt 成本增加。
```

常见设置：

```plain
top_k=3
top_k=5
top_k=8
top_k=10
```

复杂链路：

```plain
先召回 top_k=20
再 rerank 到 top_k=5
最后给 LLM
```

---

# 三十七、metadata filter 的生产用法
企业知识库一定要过滤：

```plain
tenant_id
department
doc_type
version
is_latest
allowed_roles
created_by
visibility
```

示例：

```python
metadata_filter = {
    "tenant_id": "tenant_001",
    "department": "customer_service",
    "doc_type": "after_sales",
    "is_latest": True,
}
```

---

## 【重点内容】
不要全库乱搜。

企业知识库里，如果不做 metadata filter，可能出现：

```plain
跨租户召回
跨部门召回
召回旧版本文档
召回无权限文档
```

这是严重问题。

---

# 三十八、向量库和业务数据库的关系
推荐分层：

```plain
knowledge_documents：
文档主表

knowledge_chunks：
Chunk 文本和 metadata

knowledge_chunk_embeddings：
向量数据

knowledge_query_logs：
每次问答日志

knowledge_feedbacks：
用户反馈
```

向量库只解决：

```plain
语义检索。
```

业务数据库解决：

```plain
权限
版本
状态
审计
任务
反馈
```

---

# 三十九、生产环境索引流程
完整流程：

```plain
上传文档
 ↓
文档解析
 ↓
解析质量检查
 ↓
Chunk 切分
 ↓
Chunk 质量检查
 ↓
批量 Embedding
 ↓
写入 Vector Database
 ↓
更新 document status=indexed
```

如果失败：

```plain
记录失败原因
更新状态
支持重试
```

---

# 四十、生产环境检索流程
完整流程：

```plain
用户问题
 ↓
鉴权
 ↓
构造 metadata_filter
 ↓
Query Embedding
 ↓
Vector Search top_k
 ↓
低分兜底
 ↓
可选 Rerank
 ↓
Context Builder
 ↓
LLM Answer
 ↓
返回 answer + sources
 ↓
记录 query log
```

---

# 四十一、批量 Embedding
不要一条一条请求 embedding。

应该批量处理：

```python
embeddings = embedding_model.embed_documents(
    [
        chunk.content
        for chunk in chunks
    ]
)
```

好处：

```plain
1. 降低请求开销
2. 提高吞吐
3. 更容易做重试
4. 更容易统计成本
```

---

# 四十二、Embedding 成本控制
生产环境要记录：

```plain
embedding_model
input_tokens
chunk_count
batch_size
cost
latency_ms
error
```

建议表：

```sql
CREATE TABLE embedding_jobs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    document_id VARCHAR(128) NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    chunk_count INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

# 四十三、向量维度不一致问题
常见错误：

```plain
入库 embedding 是 1536 维
查询 embedding 是 1024 维
```

结果：

```plain
无法计算相似度
向量库报错
检索结果不可信
```

解决：

```plain
1. 保存 embedding_dimension
2. 同一 collection 只用同一维度
3. 模型升级时重建索引
4. 建表时明确 vector(n)
```

Chroma 查询文档也明确要求 query embedding 的维度必须和 collection 中 embedding 的维度匹配。

---

# 四十四、模型升级如何处理
比如你从：

```plain
embedding-v1
```

升级到：

```plain
embedding-v2
```

推荐：

```plain
1. 不覆盖原向量
2. 新建 embedding_model 字段
3. 后台重建索引
4. 双写或灰度检索
5. 对比召回效果
6. 切换默认索引
7. 保留回滚能力
```

---

# 四十五、常见错误一：文档和查询用不同 Embedding 模型
错误：

```plain
入库用模型 A
查询用模型 B
```

正确：

```plain
同一索引必须使用同一个 Embedding 模型和同一维度。
```

---

# 四十六、常见错误二：只存向量，不存 content
错误：

```plain
只存 embedding
```

问题：

```plain
召回后不知道原文是什么。
```

正确：

```plain
存 chunk_id、content、metadata、embedding。
```

---

# 四十七、常见错误三：不做 metadata filter
错误：

```plain
所有租户、所有部门、所有版本一起检索。
```

正确：

```plain
至少过滤 tenant_id、权限、doc_type、version。
```

---

# 四十八、常见错误四：TopK 乱设
错误：

```plain
top_k=50，直接把 50 个 Chunk 全塞给模型。
```

问题：

```plain
成本高
噪音多
答案容易跑偏
```

正确：

```plain
top_k 结合评估调优，必要时先召回多一点，再 rerank。
```

---

# 四十九、常见错误五：不记录 score
错误：

```plain
只返回 chunk 内容，不返回分数。
```

问题：

```plain
无法判断召回质量。
```

正确：

```plain
返回 score，用于 debug、评估和兜底。
```

---

# 五十、常见错误六：用 InMemoryVectorStore 上生产
错误：

```plain
生产环境用内存向量库。
```

问题：

```plain
服务重启丢数据
多实例不共享
无法持久化
无法扩容
```

正确：

```plain
本地 Demo 用 InMemory；
生产用 pgvector / Chroma Server / Qdrant / Milvus / Elasticsearch 等。
```

---

# 五十一、常见错误七：没有重建索引机制
文档更新后必须：

```plain
1. 删除旧 Chunk
2. 删除旧 Embedding
3. 重新解析
4. 重新切分
5. 重新 Embedding
6. 写入新索引
```

否则会召回过期内容。

---

# 五十二、面试回答：Embedding 是什么
```plain
Embedding 是把文本转换成固定长度数字向量的过程。

在 RAG 里，文档 Chunk 会先通过 Embedding 模型转成向量存到向量数据库；用户提问时，也会用同一个 Embedding 模型转成 query 向量，然后通过相似度搜索找到语义最接近的 Chunk。

它解决的是语义匹配问题，比如用户说“没发货能退钱吗”，文档写的是“订单未发货可以申请取消订单并退款”，字面不同，但语义接近，Embedding 可以让它们在向量空间里靠得更近。
```

---

# 五十三、面试回答：Vector Database 是什么
```plain
Vector Database 是专门存储向量并支持相似度搜索的数据库。

在企业知识库里，它通常保存 chunk_id、document_id、chunk content、embedding 和 metadata。用户查询时，系统把问题转成 query embedding，然后在向量库里做 TopK 相似度检索，返回最相关的 Chunk。

它和 MySQL 这类关系型数据库不冲突。MySQL 更适合存业务数据、权限、版本和状态，向量数据库更适合做语义搜索。
```

---

# 五十四、面试回答：pgvector 和专业向量库怎么选
```plain
如果企业已经使用 PostgreSQL，知识库规模中小，想减少运维成本，我会优先考虑 pgvector。它可以把文档、Chunk、metadata 和向量放在同一个数据库体系里，权限过滤和 SQL 查询也比较方便。

如果向量规模比较大，检索性能要求更高，或者需要更专业的向量索引能力，可以考虑 Qdrant 或 Milvus。

如果项目本身就有 Elasticsearch，并且需要关键词检索和向量检索混合，那可以考虑 Elasticsearch。

本地开发或课程 Demo，可以先用 Chroma 或 InMemoryVectorStore 快速验证流程。
```

---

# 五十五、面试回答：metadata filter 为什么重要
```plain
metadata filter 在企业 RAG 里非常重要。

因为企业知识库不是所有文档都能全局检索。不同租户、部门、角色、文档版本都有权限边界。

比如用户只能看 customer_service 部门的售后规则，那检索时必须带 tenant_id、department、doc_type、is_latest 等过滤条件。

否则就可能出现跨租户、跨部门、旧版本、无权限文档被召回的问题，这是企业级知识库不能接受的。
```

---

# 五十六、简历亮点怎么写
可以写成：

```plain
企业知识库向量化与检索模块：
负责设计并实现 RAG 入库链路中的 Embedding 与 Vector Database 模块，将文档解析和 Chunk 切分后的 ChunkDocument 批量向量化，并写入向量存储。模块抽象了 EmbeddingService 和 VectorKnowledgeService，支持 embedding_provider、embedding_model、embedding_dimension 等配置，便于后续切换 OpenAI、BGE、Qwen、Jina 或本地 embedding 模型。

在检索链路中，实现 query embedding、TopK 相似度检索、metadata filter、score 返回和来源 metadata 透传，支持按 tenant_id、department、doc_type、version 等字段做权限和版本过滤。生产环境可替换为 pgvector / Chroma / Qdrant / Milvus 等向量数据库，并支持索引重建、模型升级和召回效果评估。
```

---

# 五十七、本章知识点和后续章节对应表
| 本章知识点 | 后续用途 |
| --- | --- |
| EmbeddingService | 第 45 章项目三入库 |
| VectorKnowledgeService | 企业知识库检索服务 |
| EmbeddedChunk | 向量库写入数据 |
| VectorSearchResult | Retriever 返回结构 |
| similarity_search | 第 43 章高级 Retrieval |
| metadata_filter | 权限过滤和版本过滤 |
| score | 第 44 章 RAG Evaluation |
| pgvector | 生产持久化选型 |
| Chroma | 本地开发和 Demo |
| top_k | 召回策略调优 |
| embedding_dimension | 模型升级和建表 |


---

# 五十八、本章完整复习
这一章我们完成了：

```plain
1. 理解 Embedding 是什么
2. 理解为什么 RAG 需要 Embedding
3. 理解文档和查询必须使用同一个 Embedding 模型
4. 理解向量维度
5. 理解 cosine similarity
6. 理解 dot product
7. 理解 euclidean distance
8. 理解 Vector Database 是什么
9. 理解向量库和业务数据库的区别
10. 理解向量库里应该存什么
11. 对比 Chroma / pgvector / Qdrant / Milvus / Elasticsearch
12. 设计 EmbeddingConfig
13. 设计 EmbeddedChunk
14. 设计 VectorSearchRequest
15. 设计 VectorSearchResult
16. 实现 similarity.py
17. 实现 DeterministicHashEmbedding
18. 实现 InMemoryVectorStore
19. 实现 EmbeddingService
20. 实现 VectorKnowledgeService
21. 跑通单文本向量化
22. 跑通相似度计算
23. 跑通向量库写入和检索
24. 跑通 metadata filter
25. 跑通解析 + 切分 + 向量化 + 检索完整流程
26. 跑通重建索引示例
27. 创建 FastAPI 向量检索接口
28. 补充 LangChain VectorStore 示例
29. 补充 Chroma 示例
30. 补充 pgvector 表设计
31. 理解为什么要返回 score
32. 理解 TopK 怎么选
33. 理解生产环境索引流程
34. 理解生产环境检索流程
35. 理解批量 Embedding
36. 理解 Embedding 成本控制
37. 理解向量维度不一致问题
38. 理解模型升级和索引重建
39. 总结常见错误
40. 准备面试回答话术
41. 准备简历亮点描述
```

---

# 五十九、课后任务一：跑通 Embedding
要求：

```plain
1. 运行 scripts/test_vector42_01_embedding.py
2. 查看每段文本生成的向量维度
3. 查看向量 norm
4. 说明 normalize 的作用
```

---

# 六十、课后任务二：跑通相似度计算
要求：

```plain
1. 运行 scripts/test_vector42_02_similarity.py
2. 比较退款问题和三个文档的 cosine
3. 说明为什么退款文档得分更高
4. 修改 query 再观察变化
```

---

# 六十一、课后任务三：跑通向量库写入和检索
要求：

```plain
1. 运行 scripts/test_vector42_03_vector_store.py
2. 查看 index_result
3. 查看 search results
4. 查看 score 排序
```

---

# 六十二、课后任务四：测试 metadata filter
要求：

```plain
1. 运行 scripts/test_vector42_04_metadata_filter.py
2. 不加 filter 搜索一次
3. 加 doc_type=after_sales 搜索一次
4. 加 doc_type=invoice 搜索一次
5. 对比结果差异
```

---

# 六十三、课后任务五：跑通完整链路
要求：

```plain
1. 运行 scripts/test_vector42_05_parse_chunk_embed_search.py
2. 查看三个文件如何入库
3. 测试退款问题
4. 测试年假问题
5. 查看 source_path 和 heading metadata
```

---

# 六十四、课后任务六：测试重建索引
要求：

```plain
1. 运行 scripts/test_vector42_06_rebuild_index.py
2. 查看 clear_index 前后的 count
3. 修改 chunk_size
4. 观察重新索引后的 Chunk 数量变化
```

---

# 六十五、课后任务七：设计 pgvector 表
要求设计：

```plain
knowledge_chunks
knowledge_chunk_embeddings
embedding_jobs
```

说明：

```plain
1. 为什么要存 embedding_model
2. 为什么要存 embedding_dimension
3. 为什么需要 document_id
4. 为什么需要 metadata
```

---

# 六十六、课后任务八：替换真实 Embedding 模型
要求：

```plain
1. 新增 OpenAIEmbeddingModel 或 QwenEmbeddingModel
2. 实现 embed_text
3. 实现 embed_texts
4. 在 EmbeddingModelFactory 中注册
5. 保持 VectorKnowledgeService 不改
```

---

# 六十七、课后任务九：增加低分兜底
要求：

```python
if top_result.score < threshold:
    return "根据当前资料无法确认"
```

需要考虑：

```plain
1. threshold 不能拍脑袋
2. 不同模型分数分布不同
3. 需要用评估集校准
```

---

# 六十八、课后任务十：设计 Query Log
表名：

```plain
knowledge_query_logs
```

字段：

```plain
id
tenant_id
user_id
query
metadata_filter
top_k
retrieved_chunk_ids
retrieved_scores
latency_ms
created_at
```

---

# 六十九、本章总结 
## 【重点内容】
好了，到这里，第 42 章我们就讲完了。

这一章我们讲的是 Embedding 与 Vector Database。

大家一定要记住：

```plain
Embedding 是把文本转换成语义向量。
Vector Database 是存储向量并做相似度搜索的数据库。
```

RAG 的检索链路本质是：

```plain
Chunk 文本向量化
 ↓
写入向量库
 ↓
用户问题向量化
 ↓
相似度搜索
 ↓
返回 TopK Chunk
```

这一章我们实现了：

```plain
DeterministicHashEmbedding
cosine_similarity
InMemoryVectorStore
EmbeddingService
VectorKnowledgeService
metadata_filter
FastAPI 检索接口
parse + chunk + embed + search 完整链路
```

还要记住几个工程关键点：

```plain
1. 入库和查询必须使用同一个 Embedding 模型
2. 向量维度必须一致
3. 向量库里要保存 content 和 metadata
4. 企业知识库必须做 metadata filter
5. score 要返回，方便调试和评估
6. InMemory 只能用于教学
7. 生产要考虑 pgvector / Chroma / Qdrant / Milvus / Elasticsearch
8. 文档更新后要支持索引重建
```

下一章我们会在本章基础上继续做高级 Retrieval。

---
