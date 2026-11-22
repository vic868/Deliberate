---

# 一、本章定位
前面三章我们已经完成了 RAG 的基础链路：

```plain
第 40 章｜企业文档解析
第 41 章｜Chunk 文档切分
第 42 章｜Embedding 与 Vector Database
```

现在系统已经具备：

```plain
原始文档
 ↓
ParsedDocument
 ↓
ChunkDocument
 ↓
Embedding
 ↓
Vector Search
 ↓
TopK Chunk
```

第 42 章解决的是：

```plain
能不能搜到相关 Chunk。
```

第 43 章解决的是：

```plain
怎么搜得更准。
```

---

# 二、为什么需要高级 Retrieval
基础向量检索流程是：

```plain
用户问题
 ↓
Embedding
 ↓
Vector Search
 ↓
TopK
```

这个流程能跑，但在真实企业项目里经常出问题：

```plain
1. 用户问题太口语，和文档表达不一致
2. 用户问题太短，语义不完整
3. 用户问题太长，包含多个意图
4. 向量检索召回了语义相似但不能回答的 Chunk
5. TopK 结果重复
6. 文档里有编号、缩写、专有名词，向量检索不稳定
7. 不做权限过滤，召回错误文档
8. 不做版本过滤，召回旧制度
9. 不做 rerank，最相关结果不一定排第一
10. 检索结果太长，塞给模型成本高
```

所以高级 Retrieval 的目标是：

```plain
提高召回率
提高排序质量
减少噪音
减少重复
控制上下文长度
保留来源依据
降低幻觉
```

---

## 【重点内容】
大家注意，第 42 章我们已经能搜了。

但是“能搜”和“搜得准”是两回事。

比如用户问：

```plain
没发货能退钱吗？
```

文档里可能写的是：

```plain
订单未发货时，可以申请取消订单并退款。
```

这个基础向量检索大概率能搜到。

但如果用户问：

```plain
我刚买的课还没开始学，现在不想要了怎么办？
```

这句话里面没有明显的“订单未发货”“退款”这些关键词。

这时候就需要 Query Rewrite，把问题改写成更适合检索的表达。

---

# 三、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. 为什么简单 TopK 不够
2. Query Rewrite 是什么
3. Multi-query Retrieval 是什么
4. HyDE 是什么
5. Hybrid Search 是什么
6. BM25 和向量检索怎么结合
7. Metadata Filter 在高级检索里的位置
8. MMR 是什么
9. Rerank 是什么
10. Cross Encoder Reranker 是什么
11. Context Compression 是什么
12. Context Builder 怎么设计
13. 低分兜底怎么做
14. 来源去重怎么做
15. 多路召回怎么合并
16. 检索日志怎么记录
17. 高级 Retrieval Service 怎么封装
18. FastAPI 高级检索接口怎么设计
19. 面试中如何讲高级 RAG 检索优化
```

---

# 四、高级 Retrieval 总体架构
```plain
User Question
    ↓
Query Analysis
    ↓
Query Rewrite
    ↓
Multi Query Expansion
    ↓
┌──────────────────────────────┐
│ Hybrid Retrieval              │
│ 1. Vector Search              │
│ 2. Keyword / BM25 Search      │
│ 3. Metadata Filter            │
└──────────────────────────────┘
    ↓
Merge + Deduplicate
    ↓
MMR Diversity Selection
    ↓
Rerank
    ↓
Low Score Fallback
    ↓
Context Builder
    ↓
LLM Answer
```

---

# 五、Retrieval 优化口诀
```plain
问题不好，先改写；
表达不全，多路问；
关键词强，走 BM25；
语义模糊，走向量；
结果重复，用 MMR；
排序不准，上 Rerank；
上下文太长，做 Compression；
分数太低，就兜底。
```

---

# 六、Query Rewrite 是什么
Query Rewrite 就是：

```plain
把用户原始问题，改写成更适合检索的查询语句。
```

用户原始问题：

```plain
我刚买的课还没开始学，现在不想要了怎么办？
```

改写后：

```plain
订单未发货或课程未使用时的退款规则
```

---

## 【重点内容】
用户问问题时，不一定会用文档里的标准表达。

文档里写：

```plain
售后规则
退款申请
未发货订单
审核通过
```

用户会说：

```plain
不想要了
能退吗
钱啥时候回来
快递一直没动
```

Query Rewrite 的作用就是把口语问题改写成知识库更容易召回的表达。

LangGraph 的 Agentic RAG 官方示例里也包含“generate query / rewrite question / grade documents”这类步骤，用于让检索 Agent 决定是否检索、生成查询、评估文档并必要时改写问题。

---

# 七、Multi-query Retrieval 是什么
Multi-query Retrieval 就是：

```plain
针对一个用户问题，生成多个不同角度的查询语句，然后分别检索，再合并结果。
```

比如用户问：

```plain
没发货能退钱吗？
```

可以扩展成：

```plain
1. 订单未发货退款规则
2. 取消订单退款流程
3. 未发货订单如何申请退款
4. 退款到账时间
```

LangChain 的 `MultiQueryRetriever` 参考文档说明，它会使用 LLM 为原始 query 生成一组查询，并分别检索文档。

---

## 【重点内容】
Multi-query 的核心是提高召回率。

一个 query 搜不到，就换几个表达搜。

但是它也有代价：

```plain
检索次数变多
成本变高
噪音可能变多
需要去重和排序
```

所以 Multi-query 不能只扩展，不治理。

后面必须做：

```plain
merge
dedupe
rerank
top_n
```

---

# 八、HyDE 是什么
HyDE 全称是：

```plain
Hypothetical Document Embeddings
```

中文可以理解为：

```plain
先让模型生成一个“假想答案文档”，再把这个假想文档拿去做向量检索。
```

流程：

```plain
用户问题
 ↓
LLM 生成假想答案
 ↓
对假想答案做 embedding
 ↓
用假想答案向量检索真实文档
```

LangChain JavaScript 的 HyDE 文档解释了这个思想：先根据问题生成 hypothetical answer，再对生成文档做 embedding，并把它作为最终检索示例。

---

## 【重点内容】
HyDE 适合什么场景？

适合用户问题太短、太抽象的时候。

比如：

```plain
报销？
```

这个 query 太短。

如果先生成一个假想答案：

```plain
差旅报销需要提交发票、行程单和审批记录。
```

再拿这段去检索，可能更容易召回报销制度。

但 HyDE 也有风险：

```plain
假想答案可能方向错
会增加一次 LLM 调用
不适合强事实严谨场景乱用
```

所以本章只做教学版 HyDE，不做强依赖。

---

# 九、Hybrid Search 是什么
Hybrid Search 就是：

```plain
关键词检索 + 向量检索一起用。
```

为什么需要混合？

因为向量检索擅长语义。

BM25 擅长关键词。

比如这些问题很适合关键词：

```plain
订单号 10002
API 字段 refund_status
制度编号 HR-2026-001
合同条款 3.2.1
SKU 编码 AIGC-199
```

这些问题很适合向量：

```plain
没发货能退钱吗？
怎么申请售后？
报销需要准备什么？
```

LangChain Retrieval 文档也把 Hybrid RAG 作为常见架构之一，通常会结合多种检索策略。

---

# 十、BM25 是什么
BM25 是一种经典关键词检索排序算法。

它更关注：

```plain
关键词出现情况
词频
文档长度
词的区分度
```

LangChain 的 `BM25Retriever` 参考文档里，BM25Retriever 保存 `docs`、`k` 和 `preprocess_func`，用于从文档集合中返回前 k 个相关文档。

---

## 【重点内容】
BM25 不懂深层语义。

但它对关键词非常敏感。

比如用户查：

```plain
HR-2026-001
```

向量检索不一定稳。

BM25 这种关键词检索就很合适。

企业知识库最好不是二选一，而是：

```plain
BM25 + Vector Search
```

---

# 十一、MMR 是什么
MMR 全称：

```plain
Maximum Marginal Relevance
```

中文可以理解为：

```plain
既要相关，也要多样。
```

普通 TopK 可能返回 5 个很相似的 Chunk。

MMR 会尽量避免重复，选择更多样的结果。

LangChain VectorStore 的 `max_marginal_relevance_search` 文档说明，MMR 会先 fetch 一批候选文档，再选择兼顾相关性和多样性的文档；其中 `fetch_k` 控制候选数量，`lambda_mult` 控制多样性，0 更偏多样，1 更偏相关。

---

# 十二、Rerank 是什么
Rerank 是：

```plain
先召回一批候选结果，再用更精细的模型重新排序。
```

常见流程：

```plain
Vector Search top 20
 ↓
Reranker 重新打分
 ↓
取 top 5
 ↓
给 LLM
```

Cross Encoder Reranker 会直接对 `(query, document)` 对进行打分，通常比只比较独立 embedding 排序更精确，但会多一次推理成本。LangChain 的 Cross Encoder Reranker 文档也建议常见做法是向量检索 top-20，再 rerank 到 top-5。

---

# 十三、Context Compression 是什么
Context Compression 是：

```plain
不是直接把召回文档原样放进 Prompt，
而是根据用户问题压缩出真正相关的内容。
```

比如召回 Chunk：

```plain
订单未发货可以退款。
订单已发货后需要收到商品再退货。
退款到账时间通常 1 到 3 个工作日。
发票可在订单完成后申请。
```

用户问：

```plain
没发货可以退款吗？
```

压缩后只保留：

```plain
订单未发货可以申请取消订单并退款。
```

LangChain 的 Contextual Compression 思路是：不要直接返回原始检索文档，而是结合 query 压缩文档，只返回与问题相关的内容；它也可以和 reranker 一起通过 `ContextualCompressionRetriever` 使用。

---

# 十四、本章代码目标
这一章我们实现一个：

```plain
高级 Retrieval 教学版模块
```

特点：

```plain
1. 不依赖真实大模型 Key
2. 不依赖外部向量数据库
3. 基于第 42 章 InMemoryVectorStore
4. 实现 Query Rewrite
5. 实现 Multi-query Expansion
6. 实现 Keyword Search
7. 实现 Hybrid Search
8. 实现 MMR
9. 实现 Simple Rerank
10. 实现 Context Builder
11. 实现低分兜底
12. 实现 FastAPI 高级检索接口
```

---

# 十五、本章项目结构
新增目录：

```plain
ai-agent-course/
├── app/
│   ├── advanced_retrieval/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── query_rewrite.py
│   │   ├── keyword_search.py
│   │   ├── hybrid_search.py
│   │   ├── mmr.py
│   │   ├── reranker.py
│   │   ├── context_builder.py
│   │   ├── service.py
│   │   ├── langchain_examples.py
│   │   ├── demo_01_query_rewrite.py
│   │   ├── demo_02_multi_query.py
│   │   ├── demo_03_keyword_search.py
│   │   ├── demo_04_hybrid_search.py
│   │   ├── demo_05_mmr.py
│   │   ├── demo_06_rerank.py
│   │   ├── demo_07_context_builder.py
│   │   └── demo_08_full_advanced_retrieval.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── advanced_retrieval.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_retrieval43_01_query_rewrite.py
│   ├── test_retrieval43_02_multi_query.py
│   ├── test_retrieval43_03_keyword_search.py
│   ├── test_retrieval43_04_hybrid_search.py
│   ├── test_retrieval43_05_mmr.py
│   ├── test_retrieval43_06_rerank.py
│   ├── test_retrieval43_07_context_builder.py
│   └── test_retrieval43_08_full.py
│
└── README.md
```

---

# 十六、创建目录和文件
执行：

```bash
mkdir -p app/advanced_retrieval

touch app/advanced_retrieval/__init__.py
touch app/advanced_retrieval/schemas.py
touch app/advanced_retrieval/query_rewrite.py
touch app/advanced_retrieval/keyword_search.py
touch app/advanced_retrieval/hybrid_search.py
touch app/advanced_retrieval/mmr.py
touch app/advanced_retrieval/reranker.py
touch app/advanced_retrieval/context_builder.py
touch app/advanced_retrieval/service.py
touch app/advanced_retrieval/langchain_examples.py
touch app/advanced_retrieval/demo_01_query_rewrite.py
touch app/advanced_retrieval/demo_02_multi_query.py
touch app/advanced_retrieval/demo_03_keyword_search.py
touch app/advanced_retrieval/demo_04_hybrid_search.py
touch app/advanced_retrieval/demo_05_mmr.py
touch app/advanced_retrieval/demo_06_rerank.py
touch app/advanced_retrieval/demo_07_context_builder.py
touch app/advanced_retrieval/demo_08_full_advanced_retrieval.py

touch app/api/v1/advanced_retrieval.py

touch scripts/test_retrieval43_01_query_rewrite.py
touch scripts/test_retrieval43_02_multi_query.py
touch scripts/test_retrieval43_03_keyword_search.py
touch scripts/test_retrieval43_04_hybrid_search.py
touch scripts/test_retrieval43_05_mmr.py
touch scripts/test_retrieval43_06_rerank.py
touch scripts/test_retrieval43_07_context_builder.py
touch scripts/test_retrieval43_08_full.py
```

Windows PowerShell：

```powershell
mkdir app\advanced_retrieval

New-Item app\advanced_retrieval\__init__.py
New-Item app\advanced_retrieval\schemas.py
New-Item app\advanced_retrieval\query_rewrite.py
New-Item app\advanced_retrieval\keyword_search.py
New-Item app\advanced_retrieval\hybrid_search.py
New-Item app\advanced_retrieval\mmr.py
New-Item app\advanced_retrieval\reranker.py
New-Item app\advanced_retrieval\context_builder.py
New-Item app\advanced_retrieval\service.py
New-Item app\advanced_retrieval\langchain_examples.py
New-Item app\advanced_retrieval\demo_01_query_rewrite.py
```

---

# 十七、定义高级检索 Schema
打开：

```plain
app/advanced_retrieval/schemas.py
```

写入：

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.vector_knowledge.schemas import VectorSearchResult


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    intent: str
    keywords: list[str]
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiQueryResult:
    original_query: str
    queries: list[str]


@dataclass
class KeywordSearchResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HybridSearchResult:
    chunk_id: str
    document_id: str
    content: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    final_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    matched_by: list[str] = field(default_factory=list)


@dataclass
class RetrievalConfig:
    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k: int = 5
    candidate_k: int = 20
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    use_query_rewrite: bool = True
    use_multi_query: bool = True
    use_mmr: bool = True
    use_rerank: bool = True
    min_score: float = 0.05
    max_context_chars: int = 2000
    metadata_filter: dict[str, Any] | None = None


@dataclass
class AdvancedRetrievalRequest:
    query: str
    config: RetrievalConfig = field(default_factory=RetrievalConfig)


@dataclass
class AdvancedRetrievalResponse:
    original_query: str
    rewritten_query: str
    queries: list[str]
    results: list[HybridSearchResult]
    context: str
    sources: list[dict[str, Any]]
    fallback_reason: str | None = None
    debug: dict[str, Any] = field(default_factory=dict)
```

---

## 【重点内容】
这里重点看 `RetrievalConfig`。

它把高级检索能力都配置化了：

```plain
mode：
vector / keyword / hybrid

top_k：
最终返回多少条

candidate_k：
先召回多少候选

vector_weight：
向量分数权重

keyword_weight：
关键词分数权重

use_query_rewrite：
是否启用问题改写

use_multi_query：
是否启用多 query 扩展

use_mmr：
是否启用多样性选择

use_rerank：
是否启用重排

min_score：
低分兜底阈值

max_context_chars：
上下文最大长度
```

这个配置化非常重要。

因为不同业务场景，检索策略不一样。

---

# 十八、实现 Query Rewrite
打开：

```plain
app/advanced_retrieval/query_rewrite.py
```

写入：

```python
import re

from app.advanced_retrieval.schemas import (
    MultiQueryResult,
    QueryRewriteResult,
)


class RuleBasedQueryRewriter:
    """
    教学版 Query Rewrite。

    说明：
    生产环境可以替换成 LLM + Structured Output。
    """

    def rewrite(
        self,
        query: str,
    ) -> QueryRewriteResult:
        normalized = query.strip()

        intent = "general"
        keywords: list[str] = []
        filters: dict[str, str] = {}

        if any(word in normalized for word in ["退钱", "退款", "不想要", "取消订单"]):
            intent = "refund"
            keywords.extend(["退款", "取消订单", "未发货", "售后"])
            filters["doc_type"] = "after_sales"

        elif any(word in normalized for word in ["快递", "物流", "配送", "没动"]):
            intent = "logistics"
            keywords.extend(["物流", "快递", "配送", "更新"])
            filters["doc_type"] = "logistics"

        elif any(word in normalized for word in ["发票", "抬头", "纳税人"]):
            intent = "invoice"
            keywords.extend(["发票", "企业", "个人", "纳税人识别号"])
            filters["doc_type"] = "invoice"

        elif any(word in normalized for word in ["年假", "请假", "休假"]):
            intent = "leave"
            keywords.extend(["年假", "请假", "员工手册"])
            filters["doc_type"] = "employee_handbook"

        elif any(word in normalized for word in ["报销", "差旅", "行程单"]):
            intent = "reimbursement"
            keywords.extend(["报销", "差旅", "发票", "审批记录"])
            filters["doc_type"] = "employee_handbook"

        rewritten_query = self._build_rewritten_query(
            original_query=normalized,
            intent=intent,
            keywords=keywords,
        )

        return QueryRewriteResult(
            original_query=query,
            rewritten_query=rewritten_query,
            intent=intent,
            keywords=keywords,
            filters=filters,
        )

    def _build_rewritten_query(
        self,
        original_query: str,
        intent: str,
        keywords: list[str],
    ) -> str:
        if intent == "refund":
            return "订单未发货取消订单退款规则 退款到账时间 售后规则"

        if intent == "logistics":
            return "物流配送进度 快递超过 7 天未更新 客服核查"

        if intent == "invoice":
            return "电子发票 企业发票 抬头 纳税人识别号"

        if intent == "leave":
            return "员工手册 年假制度 年假申请 条件"

        if intent == "reimbursement":
            return "差旅报销 发票 行程单 审批记录 报销制度"

        if keywords:
            return f"{original_query} {' '.join(keywords)}"

        return original_query


class RuleBasedMultiQueryExpander:
    def expand(
        self,
        query: str,
        rewrite_result: QueryRewriteResult | None = None,
    ) -> MultiQueryResult:
        queries = [query]

        if rewrite_result:
            queries.append(rewrite_result.rewritten_query)

            if rewrite_result.intent == "refund":
                queries.extend([
                    "未发货订单可以退款吗",
                    "取消订单退款流程",
                    "退款审核通过后多久到账",
                ])

            elif rewrite_result.intent == "logistics":
                queries.extend([
                    "物流超过 7 天没有更新怎么办",
                    "如何查询快递配送进度",
                ])

            elif rewrite_result.intent == "invoice":
                queries.extend([
                    "企业发票需要填写什么",
                    "电子发票申请规则",
                ])

            elif rewrite_result.intent == "leave":
                queries.extend([
                    "员工入职多久可以申请年假",
                    "年假制度",
                ])

            elif rewrite_result.intent == "reimbursement":
                queries.extend([
                    "差旅报销需要什么材料",
                    "报销需要发票和审批记录吗",
                ])

        # 去重并保持顺序。
        deduped = []
        seen = set()

        for item in queries:
            cleaned = re.sub(r"\s+", " ", item.strip())

            if cleaned and cleaned not in seen:
                deduped.append(cleaned)
                seen.add(cleaned)

        return MultiQueryResult(
            original_query=query,
            queries=deduped,
        )
```

---

## 【重点内容】
这个 Query Rewrite 是规则版。

真实项目里可以换成 LLM：

```plain
输入用户问题
输出 intent、rewritten_query、keywords、metadata_filter
```

但教学阶段先用规则版，优点是：

```plain
稳定
可解释
不用 API Key
方便看流程
```

---

# 十九、实现 Keyword Search
打开：

```plain
app/advanced_retrieval/keyword_search.py
```

写入：

```python
import math
import re
from collections import Counter

from app.advanced_retrieval.schemas import KeywordSearchResult
from app.vector_knowledge.schemas import EmbeddedChunk


class SimpleKeywordSearchEngine:
    """
    教学版关键词检索。

    不是完整 BM25，但保留关键词匹配 + 简单 IDF 思路。
    """

    def __init__(self):
        self.items: dict[str, EmbeddedChunk] = {}
        self.doc_freq: Counter[str] = Counter()
        self.total_docs = 0

    def add_many(
        self,
        chunks: list[EmbeddedChunk],
    ) -> None:
        for chunk in chunks:
            self.items[chunk.chunk_id] = chunk

        self._rebuild_doc_freq()

    def clear(self) -> None:
        self.items.clear()
        self.doc_freq.clear()
        self.total_docs = 0

    def search(
        self,
        query: str,
        top_k: int = 10,
        metadata_filter: dict | None = None,
    ) -> list[KeywordSearchResult]:
        query_terms = self._tokenize(query)

        candidates = list(self.items.values())

        if metadata_filter:
            candidates = [
                item for item in candidates
                if self._match_metadata_filter(
                    item.metadata,
                    metadata_filter,
                )
            ]

        results: list[KeywordSearchResult] = []

        for item in candidates:
            score = self._score(
                query_terms=query_terms,
                content=item.content,
            )

            if score <= 0:
                continue

            results.append(
                KeywordSearchResult(
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

    def _score(
        self,
        query_terms: list[str],
        content: str,
    ) -> float:
        if not query_terms:
            return 0.0

        content_terms = self._tokenize(content)
        term_count = Counter(content_terms)
        content_len = max(len(content_terms), 1)

        score = 0.0

        for term in query_terms:
            tf = term_count.get(term, 0)

            if tf == 0:
                continue

            df = self.doc_freq.get(term, 0)
            idf = math.log(
                (self.total_docs + 1) / (df + 1)
            ) + 1

            score += (tf / content_len) * idf

        return score

    def _rebuild_doc_freq(self) -> None:
        self.doc_freq.clear()
        self.total_docs = len(self.items)

        for item in self.items.values():
            terms = set(
                self._tokenize(item.content)
            )

            for term in terms:
                self.doc_freq[term] += 1

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:
        normalized = text.lower().strip()

        english_terms = re.findall(
            r"[a-zA-Z0-9_\\-]+",
            normalized,
        )

        chinese_terms = [
            char for char in normalized
            if "\u4e00" <= char <= "\u9fff"
        ]

        business_terms = []

        for term in [
            "未发货",
            "已发货",
            "退款",
            "退货",
            "物流",
            "快递",
            "发票",
            "年假",
            "报销",
            "合同",
            "付款",
            "审批记录",
            "纳税人识别号",
        ]:
            if term in text:
                business_terms.append(term)

        return english_terms + chinese_terms + business_terms

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
这里我们没有完整实现 BM25，而是做了一个教学版关键词检索。

它包含：

```plain
term frequency
document frequency
simple idf
metadata_filter
```

真实项目中可以直接使用 BM25Retriever、Elasticsearch BM25，或者数据库全文检索。

重点是让大家理解：

```plain
关键词检索和向量检索是互补的。
```

---

# 二十、实现 Hybrid Search
打开：

```plain
app/advanced_retrieval/hybrid_search.py
```

写入：

```python
from app.advanced_retrieval.keyword_search import SimpleKeywordSearchEngine
from app.advanced_retrieval.schemas import (
    HybridSearchResult,
    RetrievalConfig,
)
from app.vector_knowledge.schemas import (
    VectorSearchRequest,
)
from app.vector_knowledge.service import VectorKnowledgeService


class HybridRetriever:
    def __init__(
        self,
        vector_service: VectorKnowledgeService,
        keyword_engine: SimpleKeywordSearchEngine,
    ):
        self.vector_service = vector_service
        self.keyword_engine = keyword_engine

    def retrieve(
        self,
        query: str,
        config: RetrievalConfig,
    ) -> list[HybridSearchResult]:
        merged: dict[str, HybridSearchResult] = {}

        if config.mode.value in ["vector", "hybrid"]:
            vector_response = self.vector_service.search(
                VectorSearchRequest(
                    query=query,
                    top_k=config.candidate_k,
                    metadata_filter=config.metadata_filter,
                )
            )

            for item in vector_response.results:
                merged[item.chunk_id] = HybridSearchResult(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    content=item.content,
                    vector_score=item.score,
                    keyword_score=0.0,
                    final_score=item.score * config.vector_weight,
                    metadata=item.metadata,
                    matched_by=["vector"],
                )

        if config.mode.value in ["keyword", "hybrid"]:
            keyword_results = self.keyword_engine.search(
                query=query,
                top_k=config.candidate_k,
                metadata_filter=config.metadata_filter,
            )

            for item in keyword_results:
                existing = merged.get(item.chunk_id)

                if existing:
                    existing.keyword_score = item.score
                    existing.final_score += item.score * config.keyword_weight

                    if "keyword" not in existing.matched_by:
                        existing.matched_by.append("keyword")
                else:
                    merged[item.chunk_id] = HybridSearchResult(
                        chunk_id=item.chunk_id,
                        document_id=item.document_id,
                        content=item.content,
                        vector_score=0.0,
                        keyword_score=item.score,
                        final_score=item.score * config.keyword_weight,
                        metadata=item.metadata,
                        matched_by=["keyword"],
                    )

        results = list(merged.values())

        results.sort(
            key=lambda item: item.final_score,
            reverse=True,
        )

        return results[:config.candidate_k]
```

---

## 【重点内容】
Hybrid Search 的关键是合并分数。

这里我们用了简单加权：

```plain
final_score = vector_score * vector_weight + keyword_score * keyword_weight
```

真实项目中要做分数归一化。

因为不同检索器的 score 范围不一定一样。

比如向量分数可能是 0 到 1。

关键词分数可能没有固定上限。

所以生产环境要结合评估数据调权重。

---

# 二十一、实现 MMR
打开：

```plain
app/advanced_retrieval/mmr.py
```

写入：

```python
from app.advanced_retrieval.schemas import HybridSearchResult
from app.vector_knowledge.similarity import cosine_similarity
from app.vector_knowledge.service import VectorKnowledgeService


class MMRSelector:
    def __init__(
        self,
        vector_service: VectorKnowledgeService,
    ):
        self.vector_service = vector_service

    def select(
        self,
        query: str,
        candidates: list[HybridSearchResult],
        top_k: int,
        lambda_mult: float = 0.7,
    ) -> list[HybridSearchResult]:
        if not candidates:
            return []

        if top_k >= len(candidates):
            return candidates

        query_embedding = self.vector_service.embedding_service.embed_text(
            query
        )

        candidate_embeddings = {
            item.chunk_id: self.vector_service.embedding_service.embed_text(
                item.content
            )
            for item in candidates
        }

        selected: list[HybridSearchResult] = []
        remaining = candidates[:]

        while remaining and len(selected) < top_k:
            best_item = None
            best_score = -999999.0

            for item in remaining:
                relevance = cosine_similarity(
                    query_embedding,
                    candidate_embeddings[item.chunk_id],
                )

                if not selected:
                    diversity_penalty = 0.0
                else:
                    diversity_penalty = max(
                        cosine_similarity(
                            candidate_embeddings[item.chunk_id],
                            candidate_embeddings[selected_item.chunk_id],
                        )
                        for selected_item in selected
                    )

                mmr_score = (
                    lambda_mult * relevance
                    - (1 - lambda_mult) * diversity_penalty
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_item = item

            if best_item is None:
                break

            selected.append(best_item)
            remaining = [
                item for item in remaining
                if item.chunk_id != best_item.chunk_id
            ]

        return selected
```

---

## 【重点内容】
MMR 解决的是“结果太重复”的问题。

比如 TopK 返回：

```plain
退款规则 chunk 1
退款规则 chunk 2
退款规则 chunk 3
退款规则 chunk 4
退款规则 chunk 5
```

看起来相关，但信息重复。

MMR 会尽量选择：

```plain
退款规则
退款到账时间
退货流程
售后凭证
```

这样上下文更丰富。

---

# 二十二、实现 Simple Reranker
打开：

```plain
app/advanced_retrieval/reranker.py
```

写入：

```python
from app.advanced_retrieval.schemas import HybridSearchResult


class SimpleRuleReranker:
    """
    教学版 Reranker。

    生产环境可以换成：
    1. Cross Encoder Reranker
    2. Cohere Rerank
    3. BGE Reranker
    4. VoyageAI Rerank
    """

    def rerank(
        self,
        query: str,
        candidates: list[HybridSearchResult],
        top_k: int,
    ) -> list[HybridSearchResult]:
        query_keywords = self._extract_business_keywords(query)

        reranked: list[HybridSearchResult] = []

        for item in candidates:
            bonus = 0.0
            content = item.content

            for keyword in query_keywords:
                if keyword in content:
                    bonus += 0.2

            if item.metadata.get("is_latest") is True:
                bonus += 0.1

            if item.metadata.get("doc_type") and item.metadata.get("doc_type") in query:
                bonus += 0.1

            item.final_score = item.final_score + bonus
            reranked.append(item)

        reranked.sort(
            key=lambda item: item.final_score,
            reverse=True,
        )

        return reranked[:top_k]

    def _extract_business_keywords(
        self,
        query: str,
    ) -> list[str]:
        keywords = []

        for keyword in [
            "退款",
            "未发货",
            "退货",
            "物流",
            "快递",
            "发票",
            "年假",
            "报销",
            "合同",
            "付款",
        ]:
            if keyword in query:
                keywords.append(keyword)

        if "退钱" in query or "不想要" in query:
            keywords.extend(["退款", "未发货"])

        return list(dict.fromkeys(keywords))
```

---

## 【重点内容】
真实 rerank 一般用模型。

比如 Cross Encoder。

它会直接看：

```plain
query + document
```

然后判断这个 document 是否真的能回答 query。

LangChain 的 Cross Encoder Reranker 文档展示了 `HuggingFaceCrossEncoder`、`CrossEncoderReranker` 和 `ContextualCompressionRetriever` 的组合方式。

本章为了可运行，先用规则版 reranker。

---

# 二十三、实现 Context Builder
打开：

```plain
app/advanced_retrieval/context_builder.py
```

写入：

```python
from app.advanced_retrieval.schemas import HybridSearchResult


class RAGContextBuilder:
    def build_context(
        self,
        results: list[HybridSearchResult],
        max_chars: int = 2000,
    ) -> tuple[str, list[dict]]:
        context_parts: list[str] = []
        sources: list[dict] = []
        used_chars = 0

        for index, item in enumerate(results, start=1):
            source = {
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "document_title": item.metadata.get("document_title") or item.metadata.get("title"),
                "source_path": item.metadata.get("source_path"),
                "page_number": item.metadata.get("page_number"),
                "page_numbers": item.metadata.get("page_numbers"),
                "heading": item.metadata.get("heading"),
                "score": item.final_score,
                "matched_by": item.matched_by,
            }

            content = item.content.strip()

            part = (
                f"资料 {index}：\n"
                f"来源：{source.get('source_path')}\n"
                f"标题：{source.get('heading') or source.get('document_title')}\n"
                f"匹配方式：{','.join(item.matched_by)}\n"
                f"分数：{item.final_score:.4f}\n"
                f"内容：{content}"
            )

            if used_chars + len(part) > max_chars:
                break

            context_parts.append(part)
            sources.append(source)
            used_chars += len(part)

        context = "\n\n".join(context_parts)

        return context, sources
```

---

## 【重点内容】
Context Builder 的作用是：

```plain
把检索结果组织成模型可用的上下文。
```

它不是简单：

```python
"\n".join(chunks)
```

而是要包含：

```plain
资料编号
来源
标题
分数
内容
```

这样模型回答时更容易引用来源。

---

# 二十四、实现 Advanced Retrieval Service
打开：

```plain
app/advanced_retrieval/service.py
```

写入：

```python
from app.advanced_retrieval.context_builder import RAGContextBuilder
from app.advanced_retrieval.hybrid_search import HybridRetriever
from app.advanced_retrieval.keyword_search import SimpleKeywordSearchEngine
from app.advanced_retrieval.mmr import MMRSelector
from app.advanced_retrieval.query_rewrite import (
    RuleBasedMultiQueryExpander,
    RuleBasedQueryRewriter,
)
from app.advanced_retrieval.reranker import SimpleRuleReranker
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    AdvancedRetrievalResponse,
    HybridSearchResult,
    RetrievalConfig,
)
from app.document_chunking.schemas import ChunkDocument, ChunkStrategy
from app.vector_knowledge.service import VectorKnowledgeService


class AdvancedRetrievalService:
    def __init__(self):
        self.vector_service = VectorKnowledgeService()
        self.keyword_engine = SimpleKeywordSearchEngine()
        self.query_rewriter = RuleBasedQueryRewriter()
        self.multi_query_expander = RuleBasedMultiQueryExpander()
        self.hybrid_retriever = HybridRetriever(
            vector_service=self.vector_service,
            keyword_engine=self.keyword_engine,
        )
        self.mmr_selector = MMRSelector(
            vector_service=self.vector_service,
        )
        self.reranker = SimpleRuleReranker()
        self.context_builder = RAGContextBuilder()

    def index_chunks(
        self,
        chunks: list[ChunkDocument],
    ) -> None:
        embedded_chunks = self.vector_service.embedding_service.embed_chunks(
            chunks
        )

        self.vector_service.vector_store.add_many(
            embedded_chunks
        )

        self.keyword_engine.add_many(
            embedded_chunks
        )

    def clear_index(self) -> None:
        self.vector_service.clear_index()
        self.keyword_engine.clear()

    def retrieve(
        self,
        request: AdvancedRetrievalRequest,
    ) -> AdvancedRetrievalResponse:
        query = request.query
        config = request.config

        rewrite_result = None
        rewritten_query = query
        merged_filters = dict(config.metadata_filter or {})

        if config.use_query_rewrite:
            rewrite_result = self.query_rewriter.rewrite(query)
            rewritten_query = rewrite_result.rewritten_query

            # 教学策略：
            # 如果用户没有显式传 metadata_filter，则使用 rewrite 推断出的 filter。
            if not config.metadata_filter and rewrite_result.filters:
                merged_filters.update(rewrite_result.filters)

        effective_config = RetrievalConfig(
            mode=config.mode,
            top_k=config.top_k,
            candidate_k=config.candidate_k,
            vector_weight=config.vector_weight,
            keyword_weight=config.keyword_weight,
            use_query_rewrite=config.use_query_rewrite,
            use_multi_query=config.use_multi_query,
            use_mmr=config.use_mmr,
            use_rerank=config.use_rerank,
            min_score=config.min_score,
            max_context_chars=config.max_context_chars,
            metadata_filter=merged_filters or None,
        )

        queries = [rewritten_query]

        if config.use_multi_query:
            expanded = self.multi_query_expander.expand(
                query=query,
                rewrite_result=rewrite_result,
            )
            queries = expanded.queries

        candidates = self._retrieve_multi_queries(
            queries=queries,
            config=effective_config,
        )

        candidates = self._deduplicate_results(candidates)

        if config.use_mmr:
            candidates = self.mmr_selector.select(
                query=rewritten_query,
                candidates=candidates,
                top_k=min(config.candidate_k, len(candidates)),
                lambda_mult=0.7,
            )

        if config.use_rerank:
            final_results = self.reranker.rerank(
                query=rewritten_query,
                candidates=candidates,
                top_k=config.top_k,
            )
        else:
            final_results = candidates[:config.top_k]

        fallback_reason = None

        if not final_results:
            fallback_reason = "no_retrieval_results"
        elif final_results[0].final_score < config.min_score:
            fallback_reason = "top_score_below_threshold"

        if fallback_reason:
            context = ""
            sources = []
        else:
            context, sources = self.context_builder.build_context(
                results=final_results,
                max_chars=config.max_context_chars,
            )

        return AdvancedRetrievalResponse(
            original_query=query,
            rewritten_query=rewritten_query,
            queries=queries,
            results=[] if fallback_reason else final_results,
            context=context,
            sources=sources,
            fallback_reason=fallback_reason,
            debug={
                "candidate_count": len(candidates),
                "metadata_filter": effective_config.metadata_filter,
                "use_query_rewrite": config.use_query_rewrite,
                "use_multi_query": config.use_multi_query,
                "use_mmr": config.use_mmr,
                "use_rerank": config.use_rerank,
            },
        )

    def _retrieve_multi_queries(
        self,
        queries: list[str],
        config: RetrievalConfig,
    ) -> list[HybridSearchResult]:
        all_results: list[HybridSearchResult] = []

        for query in queries:
            results = self.hybrid_retriever.retrieve(
                query=query,
                config=config,
            )
            all_results.extend(results)

        all_results.sort(
            key=lambda item: item.final_score,
            reverse=True,
        )

        return all_results

    def _deduplicate_results(
        self,
        results: list[HybridSearchResult],
    ) -> list[HybridSearchResult]:
        merged: dict[str, HybridSearchResult] = {}

        for item in results:
            existing = merged.get(item.chunk_id)

            if not existing:
                merged[item.chunk_id] = item
                continue

            existing.final_score = max(
                existing.final_score,
                item.final_score,
            )
            existing.vector_score = max(
                existing.vector_score,
                item.vector_score,
            )
            existing.keyword_score = max(
                existing.keyword_score,
                item.keyword_score,
            )

            for source in item.matched_by:
                if source not in existing.matched_by:
                    existing.matched_by.append(source)

        deduped = list(merged.values())
        deduped.sort(
            key=lambda item: item.final_score,
            reverse=True,
        )

        return deduped


def build_sample_chunks() -> list[ChunkDocument]:
    return [
        ChunkDocument(
            chunk_id="after_sales_001",
            document_id="doc_after_sales",
            title="电商售后规则",
            content="订单未发货时，用户可以申请取消订单并退款。退款通常会在审核通过后 1 到 3 个工作日原路返回。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "after_sales",
                "source_path": "data/sample_docs/after_sales.txt",
                "heading": "未发货退款规则",
                "is_latest": True,
            },
        ),
        ChunkDocument(
            chunk_id="after_sales_002",
            document_id="doc_after_sales",
            title="电商售后规则",
            content="订单已发货后，用户需要收到商品后再发起退货退款申请。如果商品存在质量问题，可以提交照片或视频凭证。",
            chunk_index=1,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "after_sales",
                "source_path": "data/sample_docs/after_sales.txt",
                "heading": "已发货退货规则",
                "is_latest": True,
            },
        ),
        ChunkDocument(
            chunk_id="logistics_001",
            document_id="doc_logistics",
            title="物流说明",
            content="订单发货后，用户可以通过物流单号查询配送进度。如果物流超过 7 天没有更新，建议联系客服协助核查。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "logistics",
                "source_path": "data/sample_docs/logistics.txt",
                "heading": "物流异常处理",
                "is_latest": True,
            },
        ),
        ChunkDocument(
            chunk_id="invoice_001",
            document_id="doc_invoice",
            title="发票规则",
            content="用户可以在订单完成后申请开具电子发票。企业发票需要填写公司名称和纳税人识别号。",
            chunk_index=0,
            strategy=ChunkStrategy.PARAGRAPH,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "invoice",
                "source_path": "data/sample_docs/invoice.txt",
                "heading": "发票申请规则",
                "is_latest": True,
            },
        ),
        ChunkDocument(
            chunk_id="employee_001",
            document_id="doc_employee_handbook",
            title="员工手册",
            content="员工入职满一年后，可以按照公司制度申请年假。年假申请需要提前提交审批。",
            chunk_index=0,
            strategy=ChunkStrategy.HEADING,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "employee_handbook",
                "source_path": "data/sample_docs/employee_handbook.md",
                "heading": "年假制度",
                "department": "hr",
                "is_latest": True,
            },
        ),
        ChunkDocument(
            chunk_id="employee_002",
            document_id="doc_employee_handbook",
            title="员工手册",
            content="差旅报销需要提交发票、行程单和审批记录。报销申请需要按照公司流程提交。",
            chunk_index=1,
            strategy=ChunkStrategy.HEADING,
            metadata={
                "tenant_id": "tenant_001",
                "doc_type": "employee_handbook",
                "source_path": "data/sample_docs/employee_handbook.md",
                "heading": "报销制度",
                "department": "finance",
                "is_latest": True,
            },
        ),
    ]


advanced_retrieval_service = AdvancedRetrievalService()
advanced_retrieval_service.index_chunks(build_sample_chunks())
```

---

## 【重点内容】
这个 Service 是本章核心。

它把高级检索链路串起来：

```plain
Query Rewrite
Multi Query
Hybrid Search
Deduplicate
MMR
Rerank
Low Score Fallback
Context Builder
```

后面项目三企业知识库会直接复用这个结构。

---

# 二十五、示例一：Query Rewrite
打开：

```plain
app/advanced_retrieval/demo_01_query_rewrite.py
```

写入：

```python
from app.advanced_retrieval.query_rewrite import RuleBasedQueryRewriter


def main():
    rewriter = RuleBasedQueryRewriter()

    queries = [
        "我刚买的课还没开始学，现在不想要了怎么办？",
        "快递好几天没动了怎么处理？",
        "企业发票需要填什么？",
        "年假怎么申请？",
        "差旅报销要哪些材料？",
    ]

    for query in queries:
        result = rewriter.rewrite(query)

        print("original:", result.original_query)
        print("intent:", result.intent)
        print("rewritten:", result.rewritten_query)
        print("keywords:", result.keywords)
        print("filters:", result.filters)
        print("=" * 100)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_01_query_rewrite.py
```

写入：

```python
from app.advanced_retrieval.demo_01_query_rewrite import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_retrieval43_01_query_rewrite.py
```

---

# 二十六、示例二：Multi-query Expansion
打开：

```plain
app/advanced_retrieval/demo_02_multi_query.py
```

写入：

```python
from app.advanced_retrieval.query_rewrite import (
    RuleBasedMultiQueryExpander,
    RuleBasedQueryRewriter,
)


def main():
    query = "没发货能退钱吗？"

    rewriter = RuleBasedQueryRewriter()
    expander = RuleBasedMultiQueryExpander()

    rewrite_result = rewriter.rewrite(query)
    multi_query_result = expander.expand(
        query=query,
        rewrite_result=rewrite_result,
    )

    print("original:", multi_query_result.original_query)
    print("queries:")

    for item in multi_query_result.queries:
        print("-", item)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_02_multi_query.py
```

写入：

```python
from app.advanced_retrieval.demo_02_multi_query import main


if __name__ == "__main__":
    main()
```

---

# 二十七、示例三：Keyword Search
打开：

```plain
app/advanced_retrieval/demo_03_keyword_search.py
```

写入：

```python
from app.advanced_retrieval.keyword_search import SimpleKeywordSearchEngine
from app.advanced_retrieval.service import build_sample_chunks
from app.vector_knowledge.service import EmbeddingService


def main():
    embedding_service = EmbeddingService()

    chunks = build_sample_chunks()
    embedded_chunks = embedding_service.embed_chunks(chunks)

    engine = SimpleKeywordSearchEngine()
    engine.add_many(embedded_chunks)

    queries = [
        "退款",
        "HR 年假",
        "纳税人识别号",
    ]

    for query in queries:
        print("query:", query)
        results = engine.search(
            query=query,
            top_k=5,
        )

        for item in results:
            print(item.chunk_id, round(item.score, 4), item.content)
        print("=" * 100)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_03_keyword_search.py
```

写入：

```python
from app.advanced_retrieval.demo_03_keyword_search import main


if __name__ == "__main__":
    main()
```

---

# 二十八、示例四：Hybrid Search
打开：

```plain
app/advanced_retrieval/demo_04_hybrid_search.py
```

写入：

```python
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service


def main():
    queries = [
        "没发货能退钱吗？",
        "物流超过 7 天没动怎么办？",
        "企业发票需要填写什么？",
    ]

    for query in queries:
        response = advanced_retrieval_service.retrieve(
            AdvancedRetrievalRequest(
                query=query,
                config=RetrievalConfig(
                    mode=RetrievalMode.HYBRID,
                    top_k=5,
                    candidate_k=10,
                    use_query_rewrite=True,
                    use_multi_query=True,
                    use_mmr=False,
                    use_rerank=False,
                    min_score=0.01,
                    metadata_filter={
                        "tenant_id": "tenant_001",
                    },
                ),
            )
        )

        print("query:", query)
        print("rewritten:", response.rewritten_query)
        print("expanded queries:", response.queries)
        print("results:")

        for item in response.results:
            print("chunk_id:", item.chunk_id)
            print("final_score:", round(item.final_score, 4))
            print("vector_score:", round(item.vector_score, 4))
            print("keyword_score:", round(item.keyword_score, 4))
            print("matched_by:", item.matched_by)
            print("content:", item.content)
            print("-" * 80)

        print("=" * 120)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_04_hybrid_search.py
```

写入：

```python
from app.advanced_retrieval.demo_04_hybrid_search import main


if __name__ == "__main__":
    main()
```

---

# 二十九、示例五：MMR 去重和多样性
打开：

```plain
app/advanced_retrieval/demo_05_mmr.py
```

写入：

```python
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service


def run_case(use_mmr: bool):
    response = advanced_retrieval_service.retrieve(
        AdvancedRetrievalRequest(
            query="退款和售后规则是什么？",
            config=RetrievalConfig(
                mode=RetrievalMode.HYBRID,
                top_k=4,
                candidate_k=10,
                use_query_rewrite=True,
                use_multi_query=True,
                use_mmr=use_mmr,
                use_rerank=False,
                min_score=0.01,
                metadata_filter={
                    "tenant_id": "tenant_001",
                },
            ),
        )
    )

    print("use_mmr:", use_mmr)

    for item in response.results:
        print(item.chunk_id, round(item.final_score, 4), item.metadata.get("heading"))
        print(item.content)
        print("-" * 80)

    print("=" * 120)


def main():
    run_case(use_mmr=False)
    run_case(use_mmr=True)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_05_mmr.py
```

写入：

```python
from app.advanced_retrieval.demo_05_mmr import main


if __name__ == "__main__":
    main()
```

---

# 三十、示例六：Rerank
打开：

```plain
app/advanced_retrieval/demo_06_rerank.py
```

写入：

```python
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service


def run_case(use_rerank: bool):
    response = advanced_retrieval_service.retrieve(
        AdvancedRetrievalRequest(
            query="企业发票需要填写什么？",
            config=RetrievalConfig(
                mode=RetrievalMode.HYBRID,
                top_k=3,
                candidate_k=10,
                use_query_rewrite=True,
                use_multi_query=True,
                use_mmr=False,
                use_rerank=use_rerank,
                min_score=0.01,
                metadata_filter={
                    "tenant_id": "tenant_001",
                },
            ),
        )
    )

    print("use_rerank:", use_rerank)

    for item in response.results:
        print("chunk:", item.chunk_id)
        print("score:", round(item.final_score, 4))
        print("heading:", item.metadata.get("heading"))
        print("content:", item.content)
        print("-" * 80)

    print("=" * 120)


def main():
    run_case(use_rerank=False)
    run_case(use_rerank=True)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_06_rerank.py
```

写入：

```python
from app.advanced_retrieval.demo_06_rerank import main


if __name__ == "__main__":
    main()
```

---

# 三十一、示例七：Context Builder
打开：

```plain
app/advanced_retrieval/demo_07_context_builder.py
```

写入：

```python
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service


def main():
    response = advanced_retrieval_service.retrieve(
        AdvancedRetrievalRequest(
            query="没发货可以退款吗？退款多久能到账？",
            config=RetrievalConfig(
                mode=RetrievalMode.HYBRID,
                top_k=3,
                candidate_k=10,
                use_query_rewrite=True,
                use_multi_query=True,
                use_mmr=True,
                use_rerank=True,
                min_score=0.01,
                max_context_chars=800,
                metadata_filter={
                    "tenant_id": "tenant_001",
                },
            ),
        )
    )

    print("context:")
    print(response.context)

    print("=" * 80)
    print("sources:")
    for source in response.sources:
        print(source)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_07_context_builder.py
```

写入：

```python
from app.advanced_retrieval.demo_07_context_builder import main


if __name__ == "__main__":
    main()
```

---

# 三十二、示例八：完整高级检索链路
打开：

```plain
app/advanced_retrieval/demo_08_full_advanced_retrieval.py
```

写入：

```python
from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service


def main():
    cases = [
        "我刚买的课还没开始学，现在不想要了怎么办？",
        "快递超过 7 天没动怎么办？",
        "企业发票需要填写什么？",
        "年假怎么申请？",
        "公司班车路线是什么？",
    ]

    for query in cases:
        response = advanced_retrieval_service.retrieve(
            AdvancedRetrievalRequest(
                query=query,
                config=RetrievalConfig(
                    mode=RetrievalMode.HYBRID,
                    top_k=3,
                    candidate_k=10,
                    vector_weight=0.7,
                    keyword_weight=0.3,
                    use_query_rewrite=True,
                    use_multi_query=True,
                    use_mmr=True,
                    use_rerank=True,
                    min_score=0.05,
                    max_context_chars=1200,
                    metadata_filter={
                        "tenant_id": "tenant_001",
                    },
                ),
            )
        )

        print("original_query:", response.original_query)
        print("rewritten_query:", response.rewritten_query)
        print("queries:", response.queries)
        print("fallback_reason:", response.fallback_reason)

        print("=" * 80)
        print("results:")
        for item in response.results:
            print("chunk_id:", item.chunk_id)
            print("score:", round(item.final_score, 4))
            print("matched_by:", item.matched_by)
            print("heading:", item.metadata.get("heading"))
            print("content:", item.content)
            print("-" * 80)

        print("context:")
        print(response.context)

        print("=" * 120)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_retrieval43_08_full.py
```

写入：

```python
from app.advanced_retrieval.demo_08_full_advanced_retrieval import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_retrieval43_08_full.py
```

---

# 三十三、FastAPI 高级检索接口
打开：

```plain
app/api/v1/advanced_retrieval.py
```

写入：

```python
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.advanced_retrieval.schemas import (
    AdvancedRetrievalRequest,
    RetrievalConfig,
    RetrievalMode,
)
from app.advanced_retrieval.service import advanced_retrieval_service
from app.schemas.response import ApiResponse


router = APIRouter()


class AdvancedRetrievalApiRequest(BaseModel):
    query: str = Field(..., min_length=1)

    mode: Literal["vector", "keyword", "hybrid"] = "hybrid"
    top_k: int = Field(default=5, ge=1, le=20)
    candidate_k: int = Field(default=20, ge=1, le=100)

    vector_weight: float = Field(default=0.7, ge=0, le=1)
    keyword_weight: float = Field(default=0.3, ge=0, le=1)

    use_query_rewrite: bool = True
    use_multi_query: bool = True
    use_mmr: bool = True
    use_rerank: bool = True

    min_score: float = Field(default=0.05, ge=0)
    max_context_chars: int = Field(default=2000, ge=100)

    metadata_filter: dict[str, Any] | None = None


@router.post(
    "/knowledge/advanced-search",
    response_model=ApiResponse[dict],
)
async def advanced_search(
    request: AdvancedRetrievalApiRequest,
) -> ApiResponse[dict]:
    config = RetrievalConfig(
        mode=RetrievalMode(request.mode),
        top_k=request.top_k,
        candidate_k=request.candidate_k,
        vector_weight=request.vector_weight,
        keyword_weight=request.keyword_weight,
        use_query_rewrite=request.use_query_rewrite,
        use_multi_query=request.use_multi_query,
        use_mmr=request.use_mmr,
        use_rerank=request.use_rerank,
        min_score=request.min_score,
        max_context_chars=request.max_context_chars,
        metadata_filter=request.metadata_filter,
    )

    response = advanced_retrieval_service.retrieve(
        AdvancedRetrievalRequest(
            query=request.query,
            config=config,
        )
    )

    return ApiResponse[dict](
        data={
            "original_query": response.original_query,
            "rewritten_query": response.rewritten_query,
            "queries": response.queries,
            "fallback_reason": response.fallback_reason,
            "context": response.context,
            "sources": response.sources,
            "debug": response.debug,
            "results": [
                {
                    "chunk_id": item.chunk_id,
                    "document_id": item.document_id,
                    "content": item.content,
                    "vector_score": item.vector_score,
                    "keyword_score": item.keyword_score,
                    "final_score": item.final_score,
                    "matched_by": item.matched_by,
                    "metadata": item.metadata,
                }
                for item in response.results
            ],
        }
    )
```

---

# 三十四、注册 Router
打开：

```plain
app/api/v1/api.py
```

增加：

```python
from app.api.v1.advanced_retrieval import router as advanced_retrieval_router
```

注册：

```python
api_router.include_router(
    advanced_retrieval_router,
    tags=["Advanced Retrieval"],
)
```

---

# 三十五、测试接口
启动：

```bash
uv run uvicorn app.main:app --reload
```

测试：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/knowledge/advanced-search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "我刚买的课还没开始学，现在不想要了怎么办？",
    "mode": "hybrid",
    "top_k": 3,
    "candidate_k": 10,
    "use_query_rewrite": true,
    "use_multi_query": true,
    "use_mmr": true,
    "use_rerank": true,
    "metadata_filter": {
      "tenant_id": "tenant_001"
    }
  }'
```

---

# 三十六、LangChain 高级 Retrieval 示例
打开：

```plain
app/advanced_retrieval/langchain_examples.py
```

写入：

```python
"""
LangChain 高级 Retrieval 示例。

说明：
1. 这些示例展示真实 LangChain 生态写法。
2. 本章默认运行教学版 advanced_retrieval。
3. 真实项目可逐步替换为 LangChain 内置组件。
"""


def demo_vectorstore_as_mmr_retriever(vectorstore):
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,
            "lambda_mult": 0.5,
        },
    )

    return retriever.invoke("订单未发货可以退款吗？")


def demo_bm25_retriever(documents):
    from langchain_community.retrievers import BM25Retriever

    retriever = BM25Retriever.from_documents(
        documents
    )
    retriever.k = 5

    return retriever.invoke("退款 未发货")


def demo_multi_query_retriever(llm, base_retriever):
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever

    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
    )

    return retriever.invoke("没发货能退钱吗？")


def demo_cross_encoder_reranker(base_retriever):
    from langchain_classic.retrievers.contextual_compression import (
        ContextualCompressionRetriever,
    )
    from langchain_classic.retrievers.document_compressors import (
        CrossEncoderReranker,
    )
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder

    cross_encoder = HuggingFaceCrossEncoder(
        model_name="BAAI/bge-reranker-v2-m3"
    )

    reranker = CrossEncoderReranker(
        model=cross_encoder,
        top_n=3,
    )

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever,
    )

    return compression_retriever.invoke("订单未发货可以退款吗？")
```

---

## 【重点内容】
这几个是真实 LangChain 风格写法。

`vectorstore.as_retriever(search_type="mmr")` 可以把向量库转成 MMR 检索器；`BM25Retriever` 可以做关键词检索；`MultiQueryRetriever` 可以用 LLM 生成多个 query；`ContextualCompressionRetriever` 可以和 reranker 组合，用来做压缩式检索。

---

# 三十七、生产环境高级检索推荐链路
企业知识库推荐：

```plain
1. 用户提问
2. 权限鉴定
3. 构造 metadata_filter
4. Query Rewrite
5. Multi-query Expansion
6. Vector Search top 30
7. BM25 Search top 30
8. Merge + Deduplicate
9. Rerank top 8
10. MMR 选 top 5
11. Context Compression
12. Context Builder
13. LLM Answer
14. Source Citation
15. Query Log
16. Feedback
```

---

# 三十八、metadata filter 必须前置
高级 Retrieval 不是先全库召回，再过滤。

推荐：

```plain
先根据权限构造 metadata_filter，
再送到 vector search / keyword search。
```

因为全库召回再过滤有风险：

```plain
1. 可能在日志里暴露无权限内容
2. 可能 rerank 时看到无权限文档
3. 可能生成阶段误用无权限资料
4. 性能更差
```

所以企业项目里，metadata filter 是检索前置条件。

---

# 三十九、低分兜底策略
不要低质量结果也强行回答。

推荐：

```plain
没有结果：
根据当前资料无法确认。

最高分太低：
根据当前资料无法确认。

结果来源冲突：
提示资料存在冲突，需要人工确认。

权限过滤后无结果：
当前权限范围内没有找到相关资料。
```

示例：

```python
if not results:
    return "根据当前资料无法确认。"

if results[0].final_score < min_score:
    return "根据当前资料无法确认。"
```

---

# 四十、Context Builder 设计原则
Context 不是越多越好。

原则：

```plain
1. 控制最大长度
2. 高分结果优先
3. 去掉重复内容
4. 保留来源信息
5. 保留标题和页码
6. 对表格保持结构
7. 对冲突内容做标记
8. 不要把 debug log 塞进 Prompt
```

---

# 四十一、检索日志怎么设计
建议表：

```sql
CREATE TABLE knowledge_retrieval_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128),
    query TEXT NOT NULL,
    rewritten_query TEXT,
    expanded_queries JSONB,
    retrieval_mode VARCHAR(32),
    metadata_filter JSONB,
    top_k INT,
    candidate_k INT,
    retrieved_chunk_ids JSONB,
    retrieved_scores JSONB,
    fallback_reason VARCHAR(128),
    latency_ms INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 【重点内容】
检索日志非常重要。

RAG 答错的时候，不能只看最终回答。

要看：

```plain
原始问题是什么
改写后是什么
扩展了几个 query
用了什么 filter
召回了哪些 chunk
分数是多少
有没有 rerank
有没有 fallback
```

这才叫可排查。

---

# 四十二、高级 Retrieval 和 RAG Evaluation 的关系
第 44 章要讲 Evaluation。

高级 Retrieval 的效果要靠指标验证：

```plain
Recall@K
MRR
NDCG
Precision@K
Answer Groundedness
Faithfulness
Source Accuracy
```

不要凭感觉说：

```plain
我感觉加了 rerank 更准。
```

要拿真实问题集测试。

---

# 四十三、常见错误一：只做 Vector Search
错误：

```plain
所有问题都只走向量检索。
```

问题：

```plain
编号、代码、条款、订单号、专有名词可能搜不准。
```

正确：

```plain
Vector Search + Keyword Search + Metadata Filter。
```

---

# 四十四、常见错误二：多 Query 不去重
错误：

```plain
一个问题扩展 5 个 query，每个 query 返回 5 条，直接拼 25 条。
```

问题：

```plain
重复多
成本高
上下文噪音大
```

正确：

```plain
Merge + Deduplicate + Rerank。
```

---

# 四十五、常见错误三：Rerank 候选太少
错误：

```plain
先召回 top 3，再 rerank top 3。
```

这样 rerank 没有发挥空间。

正确：

```plain
先召回 top 20 或 top 30，再 rerank 到 top 5。
```

---

# 四十六、常见错误四：filter 做得太晚
错误：

```plain
全库召回后再按权限过滤。
```

正确：

```plain
检索前就带 tenant_id、department、role、version。
```

---

# 四十七、常见错误五：把低分结果强行喂给模型
错误：

```plain
没有相关资料也让模型硬答。
```

正确：

```plain
低分兜底，资料不足就明确说无法确认。
```

---

# 四十八、常见错误六：Context 里塞太多 Chunk
错误：

```plain
top_k=30 全部进 Prompt。
```

问题：

```plain
成本高
噪音大
模型注意力分散
答案容易混乱
```

正确：

```plain
Rerank + Compression + max_context_chars。
```

---

# 四十九、常见错误七：没有 source
企业 RAG 最终必须保留：

```plain
chunk_id
document_id
source_path
page_number
heading
score
```

否则答案无法追溯。

---

# 五十、面试回答：高级 Retrieval 怎么优化 RAG
```plain
我会从检索链路分层优化，而不是只调向量库。

第一层是 Query Rewrite，把用户口语化、模糊的问题改写成更适合知识库检索的表达。

第二层是 Multi-query Retrieval，为同一个问题生成多个不同角度的查询，提高召回率。

第三层是 Hybrid Search，把向量检索和 BM25 关键词检索结合起来，既能处理语义相似，也能处理编号、术语、条款这类关键词强的问题。

第四层是 Metadata Filter，在检索前按 tenant_id、department、doc_type、version、role 做权限和版本过滤。

第五层是 Rerank，先召回更多候选，再用 reranker 重新排序，取最相关的内容。

最后还会做低分兜底、来源去重和 Context Builder，保证最终给模型的上下文干净、可信、可追溯。
```

---

# 五十一、面试回答：为什么需要 Hybrid Search
```plain
因为向量检索和关键词检索各有优势。

向量检索适合语义相似，比如用户说“没发货能退钱吗”，文档写“订单未发货可以申请取消订单并退款”，这种字面不完全一致但语义一致的问题。

关键词检索适合编号、代码、条款、字段名、订单号、SKU 等精确匹配场景。

企业知识库通常既有自然语言制度，也有编号和专业术语，所以我会把 Vector Search 和 BM25 结合起来，再通过加权融合、去重和 rerank 得到最终结果。
```

---

# 五十二、面试回答：Rerank 为什么有用
```plain
向量检索召回快，但排序不一定最准确。

比如向量检索 top 20 里可能包含很多语义相关但不能直接回答问题的 Chunk。Rerank 会基于 query 和 document 的匹配关系重新打分，把真正能回答问题的内容排到前面。

工程上常见做法是先用向量检索和关键词检索召回较多候选，比如 top 20 或 top 30，再用 reranker 重排到 top 5，最后再交给模型生成回答。
```

---

# 五十三、面试回答：MMR 是什么
```plain
MMR 是 Maximum Marginal Relevance，核心是让检索结果既相关又多样。

普通 TopK 可能返回多个非常相似的 Chunk，虽然分数高，但信息重复。MMR 会在选择结果时同时考虑和 query 的相关性，以及和已选结果之间的相似度，尽量避免重复内容。

它适合用户问题需要多个角度资料的时候，比如既需要退款规则，也需要退款到账时间和售后凭证要求。
```

---

# 五十四、简历亮点怎么写
可以写成：

```plain
高级 Retrieval 优化模块：
负责企业知识库 RAG 检索链路优化，基于基础向量检索实现 Query Rewrite、Multi-query Expansion、Hybrid Search、MMR 多样性选择、Rerank 重排、低分兜底和 Context Builder。通过将 Vector Search 与关键词检索结合，提升对口语化问题、专业术语、条款编号和业务关键词的召回能力。

在工程实现上，将高级检索能力封装为 AdvancedRetrievalService，支持 top_k、candidate_k、vector_weight、keyword_weight、metadata_filter、use_mmr、use_rerank 等配置项；检索前基于 tenant_id、department、doc_type、version 等 metadata 做权限和版本过滤，检索后进行去重、重排和上下文裁剪，并返回 chunk_id、document_id、source_path、heading、score 等来源信息，增强 RAG 答案可追溯性和可评估性。
```

---

# 五十五、本章知识点和后续章节对应表
| 本章知识点 | 后续用途 |
| --- | --- |
| Query Rewrite | 第 45 章企业知识库问答 |
| Multi-query | 提升召回率 |
| Hybrid Search | 向量 + 关键词混合检索 |
| BM25 | 专业名词、编号、条款检索 |
| Metadata Filter | 权限和版本控制 |
| MMR | 减少重复结果 |
| Rerank | 提升排序质量 |
| Context Builder | LLM 生成前上下文拼接 |
| Low Score Fallback | 减少幻觉 |
| Retrieval Logs | 第 44 章 Evaluation |
| AdvancedRetrievalService | 项目三核心检索服务 |


---

# 五十六、本章完整复习
这一章我们完成了：

```plain
1. 理解为什么简单 TopK 不够
2. 理解 Query Rewrite
3. 理解 Multi-query Retrieval
4. 理解 HyDE
5. 理解 Hybrid Search
6. 理解 BM25
7. 理解 MMR
8. 理解 Rerank
9. 理解 Cross Encoder Reranker
10. 理解 Context Compression
11. 设计 RetrievalConfig
12. 设计 QueryRewriteResult
13. 设计 MultiQueryResult
14. 设计 HybridSearchResult
15. 实现 RuleBasedQueryRewriter
16. 实现 RuleBasedMultiQueryExpander
17. 实现 SimpleKeywordSearchEngine
18. 实现 HybridRetriever
19. 实现 MMRSelector
20. 实现 SimpleRuleReranker
21. 实现 RAGContextBuilder
22. 实现 AdvancedRetrievalService
23. 跑通 Query Rewrite 示例
24. 跑通 Multi-query 示例
25. 跑通 Keyword Search 示例
26. 跑通 Hybrid Search 示例
27. 跑通 MMR 示例
28. 跑通 Rerank 示例
29. 跑通 Context Builder 示例
30. 跑通完整高级检索链路
31. 创建 FastAPI 高级检索接口
32. 补充 LangChain 高级检索示例
33. 理解生产环境高级检索链路
34. 理解 metadata filter 必须前置
35. 理解低分兜底
36. 理解 Context Builder 设计
37. 设计检索日志表
38. 总结常见错误
39. 准备面试回答话术
40. 准备简历亮点描述
```

---

# 五十七、课后任务一：跑通 Query Rewrite
要求：

```plain
1. 运行 scripts/test_retrieval43_01_query_rewrite.py
2. 测试退款、物流、发票、年假、报销问题
3. 查看 rewritten_query
4. 查看 filters
5. 思考为什么 Query Rewrite 可以提升召回率
```

---

# 五十八、课后任务二：跑通 Multi-query
要求：

```plain
1. 运行 scripts/test_retrieval43_02_multi_query.py
2. 查看一个问题被扩展成几个 query
3. 思考多 query 为什么需要去重
4. 修改扩展规则，增加“退款到账时间”
```

---

# 五十九、课后任务三：跑通 Keyword Search
要求：

```plain
1. 运行 scripts/test_retrieval43_03_keyword_search.py
2. 测试“退款”
3. 测试“纳税人识别号”
4. 测试“HR 年假”
5. 说明关键词检索适合什么场景
```

---

# 六十、课后任务四：跑通 Hybrid Search
要求：

```plain
1. 运行 scripts/test_retrieval43_04_hybrid_search.py
2. 查看 vector_score
3. 查看 keyword_score
4. 查看 final_score
5. 修改 vector_weight 和 keyword_weight，观察排序变化
```

---

# 六十一、课后任务五：跑通 MMR
要求：

```plain
1. 运行 scripts/test_retrieval43_05_mmr.py
2. 对比 use_mmr=false 和 true
3. 查看结果是否更分散
4. 修改 lambda_mult 测试相关性和多样性的平衡
```

---

# 六十二、课后任务六：跑通 Rerank
要求：

```plain
1. 运行 scripts/test_retrieval43_06_rerank.py
2. 对比 use_rerank=false 和 true
3. 查看发票问题是否把 invoice chunk 排到更前
4. 思考真实 Cross Encoder Reranker 会怎么替换
```

---

# 六十三、课后任务七：跑通 Context Builder
要求：

```plain
1. 运行 scripts/test_retrieval43_07_context_builder.py
2. 查看 context 格式
3. 查看 sources
4. 修改 max_context_chars，观察输出变化
```

---

# 六十四、课后任务八：跑通完整高级检索链路
要求：

```plain
1. 运行 scripts/test_retrieval43_08_full.py
2. 测试退款问题
3. 测试物流问题
4. 测试发票问题
5. 测试知识库不存在的问题
6. 查看 fallback_reason
```

---

# 六十五、课后任务九：增加 Retrieval Log
要求实现：

```plain
knowledge_retrieval_logs
```

记录：

```plain
original_query
rewritten_query
expanded_queries
retrieval_mode
metadata_filter
retrieved_chunk_ids
retrieved_scores
fallback_reason
latency_ms
```

---

# 六十六、课后任务十：替换真实 Reranker
要求：

```plain
1. 新增 RealReranker
2. 使用 BGE Reranker 或 Cohere Rerank
3. 输入 query 和 candidates
4. 输出 reranked candidates
5. 保持 AdvancedRetrievalService 主流程不变
```

---

# 六十七、课后任务十一：实现权限过滤
要求：

```plain
1. 模拟 current_user.roles
2. 构造 metadata_filter
3. 普通用户只能查 customer_service 文档
4. HR 用户可以查 employee_handbook
5. admin 可以查全部
```

---

# 六十八、课后任务十二：设计检索评估集
准备 20 条问题：

```plain
1. 每条问题对应 expected_chunk_id
2. 运行 advanced retrieval
3. 判断 expected_chunk_id 是否出现在 top_k
4. 计算 Recall@3
5. 对比开启和关闭 rerank 的效果
```

---

# 六十九、本章总结
## 【重点内容】
好了，到这里，第 43 章我们就讲完了。

这一章我们把企业知识库从基础向量检索升级成了高级 Retrieval。

大家要记住：

```plain
RAG 答得准不准，很大程度取决于 Retrieval。
```

简单 TopK 经常不够，所以我们引入了：

```plain
Query Rewrite
Multi-query Retrieval
Hybrid Search
BM25 + Vector Search
Metadata Filter
MMR
Rerank
Context Builder
Low Score Fallback
```

核心链路是：

```plain
用户问题
 ↓
问题改写
 ↓
多路查询
 ↓
向量检索 + 关键词检索
 ↓
合并去重
 ↓
MMR 多样性选择
 ↓
Rerank 重排
 ↓
低分兜底
 ↓
构建上下文
```

企业项目里，高级 Retrieval 不是炫技，而是为了解决真实问题：

```plain
用户表达不标准
文档术语不一致
召回结果重复
排序不准确
权限和版本混乱
上下文噪音太多
模型容易幻觉
```

下一章我们就要进入 RAG Evaluation。

因为所有优化都不能凭感觉。

要用评估集和指标证明：

```plain
有没有召回正确 Chunk
有没有排到前面
答案是否忠于资料
来源是否正确
```

---
