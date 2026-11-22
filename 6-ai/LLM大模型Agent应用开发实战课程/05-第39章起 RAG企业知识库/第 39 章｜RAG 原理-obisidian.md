---
title: "第 39 章｜RAG 原理"
chapter: "39"
source: "第 39 章｜RAG 原理.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - rag
  - embedding
  - 检索
---

# 第 39 章｜RAG 原理

> [!abstract] 本章重点
>
> - ==RAG = 检索 + 增强 + 生成== — 先从知识库找相关片段，再塞进 Prompt 让模型作答。
> - ==不改模型参数就能补私有知识== — 比微调便宜，还能随时更新文档。
> - ==Chunk Size 与 Overlap 决定召回质量== — 切太大噪声多，切太小丢上下文，重叠用来接住边界语义。
> - ==Embedding 把语义变成向量== — 意思相近的文本，向量距离也近。
> - ==TopK / Metadata Filter / Rerank 层层收窄== — 先粗召回，再按条件过滤，最后重排序。
> - ==Grounded Answer 要能追溯来源== — 答案必须基于检索到的片段，减少胡编。

> [!note] 大白话
>
> - **Rerank**：把粗召回的一堆片段重新打分排序，把最相关的排前面。
> - **Chunk**：把长文档切成小块，是检索和塞进 Prompt 的基本单位。

> [!info] 导航与来源
> - 原始讲义：[[第 39 章｜RAG 原理|打开原始讲义]]
> - [[第 38 章｜项目二：LangGraph 电商客服 Agent|上一章｜第 38 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#RAG 企业知识库]]
- [[#二、本章学习目标]]
- [[#三、RAG 一句话解释]]
- [[#四、为什么需要 RAG]]
- [[#五、RAG 和普通 Chat 的区别]]
- [[#六、RAG 标准流程]]
- [[#七、RAG 的核心架构图]]
- [[#八、RAG 里的 Document 是什么]]
- [[#九、Chunk 是什么]]
- [[#十、Chunk Size 和 Chunk Overlap]]
- [[#十一、Embedding 是什么]]
- [[#十二、Vector Database 是什么]]
- [[#十三、Retriever 是什么]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面我们已经完成了两个项目：

```text
项目一：AI Chat 聊天系统
项目二：LangGraph 电商客服 Agent
```

从这一章开始，我们进入新的阶段：

## RAG 企业知识库
这个阶段最终要完成：

```text
第 45 章｜项目三：企业 AI 知识库
```

第 39～45 章的路线是：

```text
第 39 章｜RAG 原理
第 40 章｜企业文档解析
第 41 章｜Chunk 文档切分
第 42 章｜Embedding 与 Vector Database
第 43 章｜高级 Retrieval
第 44 章｜RAG Evaluation
第 45 章｜项目三：企业 AI 知识库
```

这一章先讲原理。

后面几章再逐步落代码。

---

## 二、本章学习目标
学完这一章以后，学员需要掌握：

```text
1. RAG 是什么
2. 为什么大模型需要 RAG
3. RAG 解决哪些问题
4. RAG 不能解决哪些问题
5. RAG 和 Fine-tuning 的区别
6. RAG 和普通搜索的区别
7. RAG 和 Memory 的区别
8. RAG 标准流程是什么
9. 文档为什么要切 Chunk
10. Embedding 是什么
11. Vector Database 是什么
12. Retriever 是什么
13. TopK 是什么
14. 相似度搜索是什么
15. Metadata Filter 是什么
16. Rerank 是什么
17. Context 拼接是什么
18. Grounded Answer 是什么
19. RAG 为什么会答错
20. 企业知识库架构怎么设计
21. RAG 在 Agent 项目里怎么用
22. 面试中如何讲 RAG
```

---

## 三、RAG 一句话解释
### 【实操】
```text
RAG = Retrieval-Augmented Generation

中文：
检索增强生成
```

更口语一点：

```text
先查资料，再让大模型根据资料回答。
```

---

### 【重点内容】
大家先记住一句话：

RAG 不是让模型凭空回答，而是先从知识库里查资料，再把查到的资料交给模型，让模型基于资料回答。

比如用户问：

```text
公司年假制度是什么？
```

不做 RAG 时：

```text
用户问题 -> 大模型 -> 回答
```

大模型可能不知道你公司的制度。

做 RAG 后：

```text
用户问题
 ↓
检索企业知识库
 ↓
找到年假制度相关文档
 ↓
把文档片段放进 Prompt
 ↓
大模型根据文档回答
```

这就是 RAG。

==LangChain 官方 Retrieval 文档里也强调，检索是在用户查询时获取外部相关知识，用来增强模型回答，而不是依赖模型训练时已经记住的内容。==

---

## 四、为什么需要 RAG
大模型有几个天然问题：

```text
1. 不知道企业内部私有知识
2. 训练数据有时间截止
3. 上下文窗口有限
4. 容易幻觉
5. 无法直接访问业务文档
6. 答案缺少来源依据
```

RAG 主要解决：

```text
1. 企业私有知识问答
2. 最新资料问答
3. 文档依据引用
4. 降低幻觉
5. 知识库可更新
6. 不用重新训练模型
```

---

### 【重点内容】
比如你公司有一堆内部文档：

```text
员工手册
报销制度
售后规则
产品说明书
项目文档
接口文档
培训资料
合同模板
FAQ 文档
```

这些内容，大模型默认不知道。

如果用户问：

```text
我们公司差旅报销标准是多少？
```

大模型只能猜。

但是 RAG 可以先查你自己的文档，再回答。

==所以企业落地 AI 问答，RAG 几乎是绕不开的。==

---

## 五、RAG 和普通 Chat 的区别
普通 Chat：

```text
用户问题
 ↓
LLM
 ↓
回答
```

RAG：

```text
用户问题
 ↓
Retriever 检索知识库
 ↓
返回相关文档片段
 ↓
LLM 基于文档片段生成回答
 ↓
回答 + 来源
```

---

### 【重点内容】
普通 Chat 更像“闭卷考试”。

RAG 更像“开卷考试”。

闭卷考试时，模型只能靠自己记忆。

开卷考试时，模型可以先查资料。

企业知识库场景肯定更适合开卷考试。

因为企业规则经常变，文档也经常更新。

---

## 六、RAG 标准流程
RAG 分两条链路：

```text
1. 离线入库链路
2. 在线问答链路
```

---

### 1. 离线入库链路
```text
原始文档
 ↓
文档解析
 ↓
文本清洗
 ↓
Chunk 切分
 ↓
Embedding 向量化
 ↓
写入 Vector Database
```

---

### 2. 在线问答链路
```text
用户问题
 ↓
问题向量化
 ↓
向量数据库相似度搜索
 ↓
TopK 文档片段
 ↓
可选 Rerank
 ↓
拼接 Prompt Context
 ↓
LLM 生成回答
 ↓
返回答案 + 来源
```

---

### 【重点内容】
==RAG 一定要拆成两条链路讲。==

第一条是入库链路。

也就是把企业文档处理成能检索的结构。

第二条是问答链路。

也就是用户提问时，从知识库里查相关内容，再让模型回答。

很多同学刚学 RAG，只盯着“向量数据库”。

其实完整 RAG 不只是向量数据库。

它至少包括：

```text
文档解析
文档清洗
Chunk 切分
Embedding
向量存储
召回
排序
Prompt 拼接
生成
引用来源
评估
```

LangChain Retrieval 文档也把 RAG 的模块拆成 loaders、text splitters、embedding models、vector stores、retrievers 等可替换组件。

---

## 七、RAG 的核心架构图

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

```text
┌──────────────────────────────────────┐
│            文档入库阶段               │
└──────────────────────────────────────┘

PDF / Word / Markdown / HTML / TXT
              ↓
        Document Loader
              ↓
        Text Cleaning
              ↓
        Text Splitter
              ↓
            Chunks
              ↓
        Embedding Model
              ↓
          Vector Store


┌──────────────────────────────────────┐
│            用户问答阶段               │
└──────────────────────────────────────┘

User Question
      ↓
Query Embedding
      ↓
Vector Similarity Search
      ↓
TopK Chunks
      ↓
Rerank
      ↓
Prompt Context
      ↓
LLM
      ↓
Answer + Sources
```

---

## 八、RAG 里的 Document 是什么
在 LangChain 里，文档通常会被封装成：

```python
Document(
    page_content="这里是正文内容",
    metadata={
        "source": "employee_handbook.pdf",
        "page": 3,
        "title": "年假制度",
    },
)
```

它有两个核心字段：

```text
page_content：
正文内容

metadata：
来源、页码、标题、文档类型、更新时间等元数据
```

---

### 【重点内容】
RAG 不是只存一段字符串。

==一定要存 metadata。==

因为最终回答要给用户看依据。

比如：

```text
来源：员工手册.pdf
页码：第 3 页
章节：年假制度
更新时间：2026-08-01
```

如果你只存文本，不存 metadata，后面就很难做引用来源。

---

## 九、Chunk 是什么
Chunk 就是：

```text
文档被切分后的一个小片段。
```

比如一份员工手册有 50 页。

不能直接把 50 页都塞进向量数据库当一个整体。

应该切成很多小片段：

```text
chunk_001：公司介绍
chunk_002：入职流程
chunk_003：考勤制度
chunk_004：年假制度
chunk_005：报销制度
```

LangChain 的 text splitters 文档说明，切分器会把大文档拆成更小的 chunk，使其可以被单独检索，并能放进模型上下文窗口；常见起点是 `RecursiveCharacterTextSplitter`，它会尽量保留段落、句子等自然结构。

---

### 【重点内容】
为什么要切 Chunk？

因为用户问的是一个具体问题。

比如：

```text
年假怎么算？
```

你只需要召回年假相关片段。

不需要把整本员工手册都拿出来。

Chunk 切得好，召回质量就高。

Chunk 切得差，RAG 后面很难救。

---

## 十、Chunk Size 和 Chunk Overlap
Chunk 有两个重要参数：

```text
chunk_size：
每个 chunk 大小

chunk_overlap：
相邻 chunk 之间重叠多少内容
```

例如：

```python
chunk_size = 500
chunk_overlap = 80
```

意思是：

```text
每个片段大约 500 字符；
相邻片段之间重叠 80 字符。
```

---

### 【重点内容】
为什么需要 overlap？

因为一个完整语义可能跨越两个 chunk。

如果完全不重叠，可能前半句在 chunk A，后半句在 chunk B。

检索时就容易丢上下文。

LangChain 的递归切分器文档也说明，`chunk_overlap` 可以缓解上下文被切开导致的信息丢失。

但是 overlap 也不能太大。

太大会导致：

```text
重复内容多
向量库变大
召回结果相似
成本增加
```

==所以后面第 41 章会专门讲 Chunk 设计。==

---

## 十一、Embedding 是什么
Embedding 可以理解成：

```text
把文本转换成一组数字向量。
```

比如：

```text
"订单未发货可以退款"
```

会被模型转成类似：

```text
[0.023, -0.145, 0.876, ...]
```

这组数字表示文本的语义。

---

### 【重点内容】
Embedding 不是普通关键词。

它关注语义相似。

比如用户问：

```text
没发货能不能退钱？
```

文档写的是：

```text
订单未发货时，可以申请取消订单并退款。
```

这两个句子字面不完全一样。

但是语义很接近。

Embedding 就能让它们在向量空间里靠得比较近。

LangChain Embedding 文档也说明，Embedding 模型会把原始文本转换成固定长度的数字向量，用来基于语义而不是精确字面匹配进行比较和搜索。

---

## 十二、Vector Database 是什么
Vector Database 可以理解成：

```text
专门存储和检索向量的数据库。
```

它存：

```text
chunk 文本
chunk 向量
metadata
```

常见能力：

```text
1. add_documents
2. delete
3. similarity_search
4. metadata filter
5. top_k 查询
```

LangChain Vector Store 文档说明，向量库用于保存 embedded data 并执行 similarity search；统一接口通常包含添加文档、删除文档、相似度查询，也支持 `k` 和 metadata filter 等参数。

---

### 【重点内容】
向量数据库不是替代 MySQL。

它是解决语义检索问题的。

比如 MySQL 擅长：

```text
根据 order_id 查订单
根据 user_id 查用户
根据 created_at 查记录
```

向量数据库擅长：

```text
根据语义查相似文本
```

比如用户问：

```text
没发货可以不要了吗？
```

它可以找到：

```text
订单未发货时可以取消并退款
```

这就是向量检索。

---

## 十三、Retriever 是什么
Retriever 是：

```text
根据用户问题，从知识库中返回相关文档的组件。
```

输入：

```text
query: str
```

输出：

```text
list[Document]
```

LangChain Retriever 文档也说明，Retriever 接收字符串查询，返回 `Document` 对象列表。

---

### 【重点内容】
Retriever 不是模型。

它是检索器。

你可以把它理解成：

```text
知识库搜索接口
```

比如：

```python
docs = retriever.invoke("订单未发货可以退款吗？")
```

返回：

```text
[
  Document(page_content="订单未发货时，可以申请取消订单并退款。"),
  Document(page_content="退款到账时间通常为 1-3 个工作日。")
]
```

然后把这些 docs 拼进 Prompt，让模型回答。

---

## 十四、TopK 是什么
TopK 就是：

```text
返回最相关的前 K 条文档片段。
```

比如：

```python
top_k = 3
```

表示：

```text
只返回最相似的 3 个 chunk。
```

---

### 【重点内容】
TopK 太小，可能召回不够。

TopK 太大，可能带入太多噪音。

比如：

```text
top_k=1：
可能只找到一个片段，但答案需要两个片段。

top_k=20：
可能相关和不相关的都塞进 Prompt。
```

实际项目里常见是：

```text
top_k=3
top_k=5
top_k=8
```

具体要靠评估调。

---

## 十五、Similarity Search 是什么
相似度搜索就是：

```text
把用户问题向量和知识库 chunk 向量做相似度比较，
找出最接近的 chunk。
```

常见相似度：

```text
Cosine Similarity
Dot Product
Euclidean Distance
```

LangChain Vector Store 文档也提到，相似度可以通过 cosine similarity、Euclidean distance、dot product 等方式计算，具体取决于向量库实现。

---

## 十六、Metadata Filter 是什么
Metadata Filter 是：

```text
根据文档元数据过滤检索范围。
```

比如：

```python
filter={
    "department": "hr",
    "doc_type": "employee_handbook",
}
```

表示：

```text
只在 HR 员工手册里检索。
```

---

### 【重点内容】
Metadata Filter 在企业知识库里非常重要。

比如：

```text
财务制度
HR 制度
研发规范
销售话术
售后规则
```

如果用户问：

```text
报销标准是多少？
```

就应该优先在财务制度里查。

而不是全库乱搜。

向量库统一接口通常支持 filter 这类元数据条件，用来缩小相似度搜索范围。

---

## 十七、Rerank 是什么
Rerank 是：

```text
先召回一批候选文档，
再用更精细的模型重新排序。
```

常见流程：

```text
Vector Search 召回 top 20
 ↓
Rerank 排序
 ↓
取 top 5
 ↓
交给 LLM
```

---

### 【重点内容】
为什么需要 Rerank？

==因为向量检索召回快，但不一定最精确。==

它可能召回语义相关但不一定能回答问题的片段。

Rerank 相当于二次筛选。

一般适合：

```text
知识库大
文档相似
召回噪音多
答案要求高
```

第 43 章我们会专门讲高级 Retrieval 和 Rerank。

---

## 十八、Context 拼接是什么
RAG 最后要把检索结果拼进 Prompt。

示例：

```text
你是企业知识库助手。
请只根据【参考资料】回答用户问题。
如果资料不足，请说“根据当前资料无法确认”。

【参考资料】
资料 1：
订单未发货时，可以申请取消订单并退款。

资料 2：
退款通常在审核通过后 1-3 个工作日原路返回。

【用户问题】
订单还没发货，可以退款吗？
```

---

### 【重点内容】
RAG 不是把 docs 找出来就完了。

还要把 docs 组织成模型能理解的上下文。

Prompt 很重要。

它要告诉模型：

```text
只基于资料回答
资料不足就说不知道
不要编造
给出来源
```

否则模型可能又开始自由发挥。

---

## 十九、Grounded Answer 是什么
Grounded Answer 可以理解成：

```text
有依据的回答。
```

比如：

```text
结论：订单未发货时可以申请退款。

依据：售后规则文档中提到，订单未发货时，用户可以申请取消订单并退款。
```

---

### 【重点内容】
企业知识库最怕什么？

不是回答短。

而是瞎编。

==所以 RAG 的回答最好有依据。==

至少要能返回：

```text
答案
引用来源
命中的文档
命中的 chunk
相似度分数
```

这样用户和后台才能追溯。

---

## 二十、RAG 和 Fine-tuning 的区别
| 对比项 | RAG | Fine-tuning |
| --- | --- | --- |
| 核心方式 | 检索外部知识 | 调整模型参数 |
| 适合知识更新 | 适合 | 不适合频繁更新 |
| 适合企业文档问答 | 适合 | 不一定 |
| 成本 | 相对低 | 通常更高 |
| 可追溯来源 | 容易 | 不容易 |
| 典型场景 | 知识库问答 | 风格、格式、特定任务能力 |


---

### 【重点内容】
很多人一上来就问：

```text
我要不要微调？
```

其实企业知识库问答，大多数优先考虑 RAG。

因为企业文档经常变。

今天制度改了，明天产品文档更新了。

RAG 只要更新知识库。

Fine-tuning 则更适合模型行为、风格、固定任务模式优化。

不是把所有企业文档都拿去微调。

---

## 二十一、RAG 和 Memory 的区别
| 对比项 | RAG | Memory |
| --- | --- | --- |
| 解决问题 | 查企业知识 | 记用户上下文和偏好 |
| 数据来源 | 文档、知识库、网页、制度 | 用户对话、偏好、历史行为 |
| 范围 | 企业级、业务级 | 用户级、会话级 |
| 示例 | 售后规则、员工手册 | 用户喜欢口语化回答 |
| 存储 | Vector DB / 文档库 | Checkpoint / Store |


---

### 【重点内容】
第 36 章我们讲过 Memory。

这里再强调一次。

用户偏好是 Memory。

企业制度是 RAG。

比如：

```text
用户喜欢先给结论：
Memory。

未发货订单可以退款：
RAG。
```

这两个都可以参与最终回答，但不要混在一起。

---

## 二十二、RAG 和搜索引擎的区别
普通搜索：

```text
输入关键词
返回网页列表
用户自己看
```

RAG：

```text
输入自然语言问题
检索相关文档片段
LLM 结合文档片段生成答案
返回答案和来源
```

---

### 【重点内容】
搜索引擎更像“找资料”。

RAG 更像“读完资料后帮你回答”。

==所以企业知识库问答要的是：==

```text
检索 + 理解 + 生成 + 引用
```

而不只是返回一堆链接。

---

## 二十三、RAG 常见架构类型
LangChain Retrieval 文档里把常见 RAG 架构分成 2-step RAG、Agentic RAG 和 Hybrid RAG 等类型；2-step RAG 通常每个问题只做一次检索和一次生成，适合简单问题，Agentic RAG 则允许模型根据需要决定是否以及如何检索，Hybrid RAG 会结合多种检索策略。

---

### 1. 2-step RAG
```text
检索
 ↓
生成
```

适合：

```text
简单知识库问答
FAQ
制度查询
```

---

### 2. Agentic RAG
```text
Agent 判断是否需要检索
 ↓
选择检索工具
 ↓
读取结果
 ↓
可能再次检索
 ↓
生成回答
```

适合：

```text
复杂问题
多跳问答
需要工具协同的场景
```

---

### 3. Hybrid RAG
```text
关键词检索
+
向量检索
+
Rerank
```

适合：

```text
文档量大
专业名词多
编号多
政策条款多
```

---

## 二十四、RAG 为什么会答错
==RAG 答错不一定是模型差。==

可能是整个链路的问题。

常见原因：

```text
1. 文档解析错了
2. 文本清洗丢信息
3. Chunk 切得太碎
4. Chunk 切得太大
5. Embedding 模型不适合中文或行业语料
6. 向量库召回不到正确片段
7. TopK 设置不合理
8. 没有 metadata filter
9. 没有 rerank
10. Prompt 没限制模型只基于资料
11. 检索结果里有冲突信息
12. 文档版本过旧
13. 用户问题太模糊
14. 模型没有正确引用资料
```

---

### 【重点内容】
这点非常重要。

RAG 不是接上向量数据库就一定准。

如果最终答错，要分段排查：

```text
第一，看文档是否解析正确。
第二，看 chunk 是否合理。
第三，看召回结果是否相关。
第四，看 rerank 是否排序正确。
第五，看 prompt 是否约束模型。
第六，看最终生成是否忠实于资料。
```

所以后面第 44 章会专门讲 RAG Evaluation。

---

## 二十五、RAG 质量排查口诀
```text
答错先别怪模型，
先看有没有召回。
召回不到看切分，
切分没错看向量。
向量不行看检索，
检索太乱上重排。
资料正确还答错，
再去调整 Prompt。
```

---

## 二十六、企业 RAG 架构设计
企业 RAG 通常分三层。

### 第一层：文档管理层
```text
上传文档
文档解析
文档版本
权限控制
文档状态
```

### 第二层：索引构建层
```text
文本清洗
Chunk 切分
Embedding
Vector Store
Metadata
```

### 第三层：问答服务层
```bash
问题改写
Retriever
Rerank
Context Builder
LLM Answer
Source Citation
Feedback
Evaluation
```

---

## 二十七、企业 RAG 数据表设计预览
后面项目三会用到这些表：

```text
knowledge_documents
knowledge_chunks
knowledge_embeddings
knowledge_query_logs
knowledge_feedbacks
```

---

### 1. knowledge_documents
```sql
CREATE TABLE knowledge_documents (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_uri TEXT,
    file_type VARCHAR(32),
    status VARCHAR(32) NOT NULL,
    version VARCHAR(64),
    created_by VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### 2. knowledge_chunks
```sql
CREATE TABLE knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    document_id BIGINT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    token_count INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

### 3. knowledge_query_logs
```sql
CREATE TABLE knowledge_query_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    user_id VARCHAR(128),
    question TEXT NOT NULL,
    rewritten_question TEXT,
    retrieved_chunk_ids JSONB,
    answer TEXT,
    latency_ms INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 二十八、本章代码目标
本章不急着接真实向量库。

先写一个“从原理角度能跑通的 Mini RAG”。

特点：

```text
1. 不依赖大模型 API Key
2. 不依赖真实向量数据库
3. 用 Python 实现简单 Embedding
4. 用余弦相似度检索
5. 返回 TopK 文档
6. 拼接 Context
7. 生成一个基于资料的模拟回答
```

目的：

```text
先理解 RAG 的底层流程。
```

---

## 二十九、本章项目结构
新增目录：

```text
ai-agent-course/
├── app/
│   ├── rag_principles/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── documents.py
│   │   ├── splitter.py
│   │   ├── embedding.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   ├── prompt_builder.py
│   │   ├── answer_generator.py
│   │   ├── pipeline.py
│   │   └── demo_01_mini_rag.py
│   │
│   └── ...
│
├── scripts/
│   └── test_rag39_mini_rag.py
│
└── README.md
```

创建目录：

```bash
mkdir -p app/rag_principles

touch app/rag_principles/__init__.py
touch app/rag_principles/schemas.py
touch app/rag_principles/documents.py
touch app/rag_principles/splitter.py
touch app/rag_principles/embedding.py
touch app/rag_principles/vector_store.py
touch app/rag_principles/retriever.py
touch app/rag_principles/prompt_builder.py
touch app/rag_principles/answer_generator.py
touch app/rag_principles/pipeline.py
touch app/rag_principles/demo_01_mini_rag.py

touch scripts/test_rag39_mini_rag.py
```

Windows PowerShell：

```powershell
mkdir app\rag_principles

New-Item app\rag_principles\__init__.py
New-Item app\rag_principles\schemas.py
New-Item app\rag_principles\documents.py
New-Item app\rag_principles\splitter.py
New-Item app\rag_principles\embedding.py
New-Item app\rag_principles\vector_store.py
New-Item app\rag_principles\retriever.py
New-Item app\rag_principles\prompt_builder.py
New-Item app\rag_principles\answer_generator.py
New-Item app\rag_principles\pipeline.py
New-Item app\rag_principles\demo_01_mini_rag.py

New-Item scripts\test_rag39_mini_rag.py
```

---

## 三十、定义 RAG Schema
打开：

```text
app/rag_principles/schemas.py
```

写入：

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawDocument:
    document_id: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkDocument:
    chunk_id: str
    document_id: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddedChunk:
    chunk: ChunkDocument
    embedding: list[float]


@dataclass
class RetrievedChunk:
    chunk: ChunkDocument
    score: float


@dataclass
class RAGAnswer:
    question: str
    answer: str
    retrieved_chunks: list[RetrievedChunk]
    context: str
```

---

## 三十一、准备模拟企业文档
打开：

```text
app/rag_principles/documents.py
```

写入：

```python
from app.rag_principles.schemas import RawDocument


def load_mock_documents() -> list[RawDocument]:
    return [
        RawDocument(
            document_id="doc_after_sales",
            title="电商售后规则",
            content=(
                "订单未发货时，用户可以申请取消订单并退款。"
                "退款通常会在审核通过后 1 到 3 个工作日原路返回。"
                "订单已发货后，用户需要收到商品后再发起退货退款申请。"
                "如果商品存在质量问题，用户可以提交照片或视频凭证申请售后。"
            ),
            metadata={
                "department": "customer_service",
                "doc_type": "after_sales",
                "version": "2026-08",
            },
        ),
        RawDocument(
            document_id="doc_logistics",
            title="物流说明",
            content=(
                "订单发货后，用户可以通过物流单号查询配送进度。"
                "普通快递通常 3 到 5 天送达，偏远地区可能需要更长时间。"
                "如果物流超过 7 天没有更新，建议联系客服协助核查。"
            ),
            metadata={
                "department": "customer_service",
                "doc_type": "logistics",
                "version": "2026-08",
            },
        ),
        RawDocument(
            document_id="doc_invoice",
            title="发票规则",
            content=(
                "用户可以在订单完成后申请开具电子发票。"
                "发票抬头可以选择个人或企业。"
                "企业发票需要填写公司名称和纳税人识别号。"
            ),
            metadata={
                "department": "finance",
                "doc_type": "invoice",
                "version": "2026-08",
            },
        ),
    ]
```

---

## 三十二、实现简单 Text Splitter
打开：

```text
app/rag_principles/splitter.py
```

写入：

```python
from app.rag_principles.schemas import ChunkDocument, RawDocument


class SimpleTextSplitter:
    def __init__(
        self,
        chunk_size: int = 60,
        chunk_overlap: int = 10,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_document(
        self,
        document: RawDocument,
    ) -> list[ChunkDocument]:
        text = document.content
        chunks: list[ChunkDocument] = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size
            content = text[start:end]

            chunk = ChunkDocument(
                chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                document_id=document.document_id,
                title=document.title,
                content=content,
                metadata={
                    **document.metadata,
                    "chunk_index": chunk_index,
                },
            )

            chunks.append(chunk)

            if end >= len(text):
                break

            start = end - self.chunk_overlap
            chunk_index += 1

        return chunks

    def split_documents(
        self,
        documents: list[RawDocument],
    ) -> list[ChunkDocument]:
        all_chunks: list[ChunkDocument] = []

        for document in documents:
            all_chunks.extend(
                self.split_document(document)
            )

        return all_chunks
```

---

### 【重点内容】
这是一个教学版切分器。

真实项目中不会这么简单切字符串。

后面第 41 章我们会讲：

```text
按标题切
按段落切
按 Markdown Header 切
按 token 切
按语义切
按表格切
按代码结构切
```

但是这一章先用简单版本理解流程。

---

## 三十三、实现简单 Embedding
打开：

```text
app/rag_principles/embedding.py
```

写入：

```python
import math
from collections import Counter


class SimpleKeywordEmbedding:
    """
    教学版 Embedding。

    说明：
    1. 不依赖外部模型。
    2. 用关键词词频构造一个小向量。
    3. 只用于理解 RAG 流程，不代表真实 Embedding 效果。
    """

    def __init__(self):
        self.vocabulary = [
            "订单",
            "未发货",
            "发货",
            "退款",
            "退货",
            "售后",
            "物流",
            "快递",
            "发票",
            "企业",
            "个人",
            "质量",
            "客服",
            "审核",
        ]

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        counter = Counter()

        for word in self.vocabulary:
            counter[word] = text.count(word)

        vector = [
            float(counter[word])
            for word in self.vocabulary
        ]

        norm = math.sqrt(
            sum(value * value for value in vector)
        )

        if norm == 0:
            return vector

        return [
            value / norm
            for value in vector
        ]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self.embed_text(text)
            for text in texts
        ]

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        return self.embed_text(query)
```

---

### 【重点内容】
这个 Embedding 是教学版。

它只是统计关键词。

真实项目中我们会换成：

```text
OpenAI Embeddings
通义千问 Embedding
BGE Embedding
Jina Embedding
Ollama 本地 Embedding
```

但原理都是：

```text
文本 -> 向量
```

LangChain 提供统一 Embeddings 接口，可以对接 OpenAI、Cohere、Hugging Face 等不同 embedding 模型。

---

## 三十四、实现简单 Vector Store
打开：

```text
app/rag_principles/vector_store.py
```

写入：

```python
import math

from app.rag_principles.schemas import (
    ChunkDocument,
    EmbeddedChunk,
    RetrievedChunk,
)


def cosine_similarity(
    left: list[float],
    right: list[float],
) -> float:
    if len(left) != len(right):
        raise ValueError("两个向量长度必须一致")

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


class SimpleVectorStore:
    def __init__(self):
        self.items: list[EmbeddedChunk] = []

    def add_documents(
        self,
        chunks: list[ChunkDocument],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks 和 embeddings 数量必须一致")

        for chunk, embedding in zip(chunks, embeddings):
            self.items.append(
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=embedding,
                )
            )

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> list[RetrievedChunk]:
        candidates = self.items

        if metadata_filter:
            candidates = [
                item for item in candidates
                if all(
                    item.chunk.metadata.get(key) == value
                    for key, value in metadata_filter.items()
                )
            ]

        scored: list[RetrievedChunk] = []

        for item in candidates:
            score = cosine_similarity(
                query_embedding,
                item.embedding,
            )

            scored.append(
                RetrievedChunk(
                    chunk=item.chunk,
                    score=score,
                )
            )

        scored.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        return scored[:top_k]
```

---

## 三十五、实现 Retriever
打开：

```text
app/rag_principles/retriever.py
```

写入：

```python
from app.rag_principles.embedding import SimpleKeywordEmbedding
from app.rag_principles.schemas import RetrievedChunk
from app.rag_principles.vector_store import SimpleVectorStore


class SimpleRetriever:
    def __init__(
        self,
        embedding_model: SimpleKeywordEmbedding,
        vector_store: SimpleVectorStore,
    ):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> list[RetrievedChunk]:
        query_embedding = self.embedding_model.embed_query(query)

        return self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
```

---

## 三十六、实现 Prompt Builder
打开：

```text
app/rag_principles/prompt_builder.py
```

写入：

```python
from app.rag_principles.schemas import RetrievedChunk


class RAGPromptBuilder:
    def build_context(
        self,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        if not retrieved_chunks:
            return "暂无可用参考资料。"

        context_parts = []

        for index, item in enumerate(retrieved_chunks, start=1):
            chunk = item.chunk

            context_parts.append(
                f"资料 {index}：\n"
                f"标题：{chunk.title}\n"
                f"来源文档：{chunk.document_id}\n"
                f"Chunk：{chunk.chunk_id}\n"
                f"相似度：{item.score:.4f}\n"
                f"内容：{chunk.content}"
            )

        return "\n\n".join(context_parts)

    def build_prompt(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        context = self.build_context(retrieved_chunks)

        return (
            "你是一个企业知识库问答助手。\n"
            "请严格根据【参考资料】回答用户问题。\n"
            "如果参考资料不足，请回答：根据当前资料无法确认。\n"
            "不要编造参考资料中没有的信息。\n\n"
            f"【参考资料】\n{context}\n\n"
            f"【用户问题】\n{question}\n"
        )
```

---

## 三十七、实现模拟 Answer Generator
打开：

```text
app/rag_principles/answer_generator.py
```

写入：

```python
from app.rag_principles.schemas import RetrievedChunk


class SimpleAnswerGenerator:
    """
    教学版回答生成器。

    真实项目里这里会调用 LLM。
    这里为了让代码下载后不用 API Key，也能跑通。
    """

    def generate(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        if not retrieved_chunks:
            return "根据当前资料无法确认。"

        valid_chunks = [
            item for item in retrieved_chunks
            if item.score > 0
        ]

        if not valid_chunks:
            return "根据当前资料无法确认。"

        best = valid_chunks[0]

        return (
            "根据知识库资料，可以这样回答："
            f"{best.chunk.content}\n\n"
            f"来源：{best.chunk.title} / {best.chunk.chunk_id}"
        )
```

---

## 三十八、实现 Mini RAG Pipeline
打开：

```text
app/rag_principles/pipeline.py
```

写入：

```python
from app.rag_principles.answer_generator import SimpleAnswerGenerator
from app.rag_principles.documents import load_mock_documents
from app.rag_principles.embedding import SimpleKeywordEmbedding
from app.rag_principles.prompt_builder import RAGPromptBuilder
from app.rag_principles.retriever import SimpleRetriever
from app.rag_principles.schemas import RAGAnswer
from app.rag_principles.splitter import SimpleTextSplitter
from app.rag_principles.vector_store import SimpleVectorStore


class MiniRAGPipeline:
    def __init__(self):
        self.embedding_model = SimpleKeywordEmbedding()
        self.vector_store = SimpleVectorStore()
        self.retriever = SimpleRetriever(
            embedding_model=self.embedding_model,
            vector_store=self.vector_store,
        )
        self.prompt_builder = RAGPromptBuilder()
        self.answer_generator = SimpleAnswerGenerator()

    def build_index(self) -> None:
        documents = load_mock_documents()

        splitter = SimpleTextSplitter(
            chunk_size=60,
            chunk_overlap=10,
        )

        chunks = splitter.split_documents(documents)

        embeddings = self.embedding_model.embed_documents(
            [
                chunk.content
                for chunk in chunks
            ]
        )

        self.vector_store.add_documents(
            chunks=chunks,
            embeddings=embeddings,
        )

    def ask(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> RAGAnswer:
        retrieved_chunks = self.retriever.retrieve(
            query=question,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )

        context = self.prompt_builder.build_context(
            retrieved_chunks
        )

        answer = self.answer_generator.generate(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

        return RAGAnswer(
            question=question,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            context=context,
        )
```

---

## 三十九、运行 Mini RAG Demo
打开：

```text
app/rag_principles/demo_01_mini_rag.py
```

写入：

```python
from app.rag_principles.pipeline import MiniRAGPipeline


def print_answer(question: str, result):
    print("用户问题:")
    print(question)

    print("=" * 80)
    print("最终回答:")
    print(result.answer)

    print("=" * 80)
    print("召回结果:")
    for item in result.retrieved_chunks:
        print("chunk_id:", item.chunk.chunk_id)
        print("title:", item.chunk.title)
        print("score:", round(item.score, 4))
        print("content:", item.chunk.content)
        print("metadata:", item.chunk.metadata)
        print("-" * 80)

    print("=" * 120)


def main():
    pipeline = MiniRAGPipeline()
    pipeline.build_index()

    questions = [
        "订单还没发货，可以退款吗？",
        "物流超过 7 天没更新怎么办？",
        "企业发票需要填写什么？",
        "会员积分规则是什么？",
    ]

    for question in questions:
        result = pipeline.ask(
            question=question,
            top_k=3,
        )

        print_answer(question, result)

    print("测试 metadata_filter:")
    result = pipeline.ask(
        question="退款规则是什么？",
        top_k=3,
        metadata_filter={
            "doc_type": "after_sales"
        },
    )

    print_answer("退款规则是什么？", result)


if __name__ == "__main__":
    main()
```

创建脚本：

```text
scripts/test_rag39_mini_rag.py
```

写入：

```python
from app.rag_principles.demo_01_mini_rag import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_rag39_mini_rag.py
```

---

### 【重点内容】
这个 Mini RAG 很简单，但它完整模拟了 RAG 链路：

```text
加载文档
切分 Chunk
计算 Embedding
写入 Vector Store
用户提问
问题向量化
相似度搜索
返回 TopK
拼接 Context
生成回答
返回来源
```

==这就是 RAG 的骨架。==

后面我们只是把每个模块替换成生产级实现。

---

## 四十、从 Mini RAG 到企业 RAG 的升级路径
| Mini RAG | 企业 RAG |
| --- | --- |
| mock documents | 文档上传、网盘、数据库、网页 |
| simple splitter | 结构化切分、语义切分 |
| keyword embedding | 专业 Embedding 模型 |
| simple vector store | pgvector / Milvus / Qdrant / Elasticsearch |
| cosine search | hybrid search / rerank |
| mock answer | LLM grounded answer |
| print result | FastAPI 接口 |
| 无权限 | 多租户权限 |
| 无评估 | RAG Evaluation |


---

## 四十一、RAG 在电商客服 Agent 里的位置
第 38 章电商客服 Agent 里已经出现过：

```text
retrieve_policy_node
```

它本质就是 RAG 节点。

流程：

```text
用户问退款
 ↓
查订单状态
 ↓
根据订单状态构造 policy_query
 ↓
RAG 检索售后规则
 ↓
根据规则生成回答
```

比如：

```text
订单 10002 状态：已付款，待发货
policy_query：订单未发货退款规则
RAG 返回：未发货订单可以申请取消订单并退款
最终回答：当前订单可以按规则申请退款
```

---

## 四十二、RAG 和 Agent 的结合方式
RAG 可以有三种接入方式。

### 方式一：固定 RAG Node
```text
固定流程里一定检索
```

适合：

```text
企业知识库问答
售后规则问答
制度问答
```

---

### 方式二：RAG Tool
```text
把 search_knowledge_base 做成 Tool
由 Agent 决定什么时候调用
```

适合：

```text
Agentic RAG
复杂多轮问答
不确定是否需要检索的任务
```

---

### 方式三：Multi-Agent RAG
```text
RAGAgent 专门负责知识检索
AnswerAgent 专门负责组织回答
ReviewerAgent 专门检查答案是否忠于资料
```

适合：

```text
大型企业知识库
复杂业务助手
多角色协作
```

---

## 四十三、企业 RAG 的核心难点

> [!important] 重点标记
> 这一节是本章核心，建议慢读。

企业 RAG 难点不在“会不会调向量库”。

真正难点是：

```text
1. 文档格式复杂
2. 表格解析难
3. PDF 扫描件难
4. Chunk 粒度难
5. 权限控制难
6. 多版本文档冲突
7. 召回结果不稳定
8. 中文语义检索效果差异大
9. RAG 幻觉不好排查
10. 评估体系难建立
```

---

### 【重点内容】
很多培训课把 RAG 讲得很简单：

```text
切文档
存向量
查出来
问模型
```

但真实企业项目不止这些。

比如文档里有表格。

比如一个 PDF 是扫描件。

比如同一制度有旧版和新版。

比如不同部门只能看自己的文档。

这些才是企业 RAG 的真实难点。

---

## 四十四、RAG 项目面试亮点
可以这样包装：

```text
基于 LangChain + pgvector 实现企业知识库 RAG 问答系统，支持 PDF / Markdown / Word 文档解析、结构化 Chunk 切分、Embedding 向量化、Metadata 过滤、TopK 召回、Rerank 重排、基于来源的回答生成和用户反馈评估。
```

进一步说：

```text
项目中对 RAG 链路做了模块化拆分，包括 DocumentLoader、TextSplitter、EmbeddingService、VectorStore、Retriever、ContextBuilder、AnswerGenerator 和 EvaluationService。通过 metadata 实现租户、部门、文档类型和版本过滤，避免跨权限召回。
```

---

## 四十五、面试回答：RAG 是什么
### 回答话术一：基础版
```text
RAG 是 Retrieval-Augmented Generation，中文叫检索增强生成。

它的核心思想是，大模型回答问题前，先从外部知识库检索相关资料，然后把资料作为上下文提供给模型，让模型基于资料回答。

这样可以解决大模型不知道企业私有知识、知识更新不及时、回答缺少依据和容易幻觉的问题。
```

---

### 回答话术二：项目版
```text
比如企业知识库项目里，用户问“公司年假制度是什么”。

系统不会直接让大模型回答，而是先把问题转成向量，到向量数据库里检索员工手册相关 chunk，拿到年假制度片段后，再把这些片段拼到 Prompt 里，让模型根据资料生成回答，并返回来源文档、页码和 chunk_id。

这样用户能看到答案依据，后续也方便排查和评估。
```

---

### 回答话术三：工程版
```text
工程上我会把 RAG 拆成离线入库和在线问答两条链路。

离线入库负责文档解析、清洗、Chunk 切分、Embedding 和写入向量数据库。

在线问答负责问题改写、query embedding、TopK 召回、metadata filter、rerank、context 拼接、LLM 生成和来源引用。

如果答案不准，我会分段排查：先看文档解析是否正确，再看 chunk 是否合理，再看召回是否命中，再看 rerank 和 prompt，最后才看模型生成。
```

---

## 四十六、面试回答：RAG 为什么比 Fine-tuning 更适合企业知识库
```text
企业知识库一般优先用 RAG，而不是 Fine-tuning。

因为企业文档更新频繁，比如制度、产品手册、售后规则都会变。如果用 Fine-tuning，每次文档变化都重新训练，成本高，也不方便追溯答案来源。

RAG 只需要更新知识库索引，用户提问时实时检索最新文档片段，再让模型基于片段回答，同时可以返回来源依据。

Fine-tuning 更适合优化模型行为、输出格式和特定任务风格，不适合作为频繁更新知识的主要承载方式。
```

---

## 四十七、面试回答：RAG 为什么会幻觉
```text
RAG 仍然可能幻觉，原因通常不止一个。

第一种是没召回到正确资料，模型只能根据不相关上下文回答。

第二种是召回到了冲突或过期资料，模型不知道该信哪个。

第三种是 chunk 切分不合理，关键信息被切断。

第四种是 Prompt 没有限制模型必须基于资料回答。

第五种是模型生成阶段没有做引用校验，导致它把资料里没有的信息补出来。

所以我会通过召回评估、答案忠实度评估、来源引用和人工反馈来持续优化。
```

---

## 四十八、常见错误一：把 RAG 等同于向量数据库

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误理解：

```text
RAG = 向量数据库
```

正确理解：

```text
RAG = 文档处理 + Chunk + Embedding + Vector Store + Retrieval + Rerank + Prompt + Generation + Evaluation
```

---

## 四十九、常见错误二：Chunk 随便切
错误：

```text
每 1000 个字符硬切一次，不管标题、段落、表格。
```

问题：

```text
语义被切断
召回片段不完整
答案缺上下文
```

正确：

```text
根据文档结构和业务语义切分。
```

---

## 五十、常见错误三：只做向量检索，不做 metadata filter
错误：

```text
所有文档放一起，全库搜索。
```

问题：

```text
跨部门召回
跨权限召回
旧版本召回
不相关文档混入
```

正确：

```text
根据 tenant_id、department、doc_type、version、permission 做过滤。
```

---

## 五十一、常见错误四：资料不足还强行回答

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误回答：

```text
根据资料无法确认，但我猜应该是……
```

正确回答：

```text
根据当前资料无法确认，建议查看最新制度或联系相关负责人。
```

---

## 五十二、常见错误五：没有返回来源
==企业知识库必须尽量返回：==

```text
document_id
document_title
chunk_id
page
source
score
```

否则用户不知道答案来自哪里。

---

## 五十三、常见错误六：不做评估
上线前至少要测：

```text
1. 召回是否命中正确 chunk
2. 最终答案是否基于资料
3. 是否引用来源
4. 资料不足时是否拒答
5. 旧版本文档是否被过滤
6. 无权限文档是否不会被召回
```

---

## 五十四、RAG 设计 Checklist
设计 RAG 前问自己：

```text
1. 知识库有哪些文档来源？
2. 文档格式有哪些？
3. 是否有扫描 PDF？
4. 是否包含表格？
5. 是否需要 OCR？
6. Chunk 怎么切？
7. Chunk metadata 存哪些？
8. Embedding 模型选哪个？
9. 向量数据库选哪个？
10. 是否需要混合检索？
11. 是否需要 Rerank？
12. 是否有权限过滤？
13. 是否有版本过滤？
14. 是否返回来源？
15. 是否记录 query log？
16. 是否收集用户反馈？
17. 是否有评估集？
18. 如何灰度上线？
```

---

## 五十五、本章知识点和后续章节对应表
| 本章知识点 | 后续章节 |
| --- | --- |
| RAG 原理 | 第 39 章 |
| 文档解析 | 第 40 章 |
| Chunk 切分 | 第 41 章 |
| Embedding | 第 42 章 |
| Vector Database | 第 42 章 |
| Retriever | 第 43 章 |
| Metadata Filter | 第 43 章 |
| Rerank | 第 43 章 |
| Evaluation | 第 44 章 |
| 企业知识库项目 | 第 45 章 |


---

## 五十六、本章完整复习
这一章我们完成了：

```text
1. 理解 RAG 是什么
2. 理解为什么大模型需要 RAG
3. 理解 RAG 和普通 Chat 的区别
4. 理解 RAG 的离线入库链路
5. 理解 RAG 的在线问答链路
6. 理解 Document 是什么
7. 理解 Chunk 是什么
8. 理解 chunk_size 和 chunk_overlap
9. 理解 Embedding 是什么
10. 理解 Vector Database 是什么
11. 理解 Retriever 是什么
12. 理解 TopK 是什么
13. 理解 Similarity Search 是什么
14. 理解 Metadata Filter 是什么
15. 理解 Rerank 是什么
16. 理解 Context 拼接
17. 理解 Grounded Answer
18. 区分 RAG 和 Fine-tuning
19. 区分 RAG 和 Memory
20. 区分 RAG 和普通搜索
21. 理解 2-step RAG
22. 理解 Agentic RAG
23. 理解 Hybrid RAG
24. 总结 RAG 答错原因
25. 设计企业 RAG 架构
26. 预览企业知识库数据表
27. 编写 Mini RAG 代码
28. 实现简单切分器
29. 实现简单 Embedding
30. 实现简单 Vector Store
31. 实现 Retriever
32. 实现 Prompt Builder
33. 实现 Answer Generator
34. 跑通 Mini RAG Pipeline
35. 理解从 Mini RAG 到企业 RAG 的升级路径
36. 理解 RAG 在电商客服 Agent 中的位置
37. 总结企业 RAG 难点
38. 准备面试回答话术
39. 总结常见错误
40. 准备 RAG 设计 Checklist
```

---

## 五十七、课后任务一：画出 RAG 两条链路
要求画出：

```text
1. 离线入库链路
2. 在线问答链路
```

必须包含：

```text
Document Loader
Text Splitter
Embedding
Vector Store
Retriever
Prompt
LLM
Source
```

---

## 五十八、课后任务二：跑通 Mini RAG
要求：

```text
1. 运行 scripts/test_rag39_mini_rag.py
2. 测试退款问题
3. 测试物流问题
4. 测试发票问题
5. 测试资料不存在的问题
6. 查看 retrieved_chunks
```

---

## 五十九、课后任务三：修改 Chunk 参数
要求：

```text
1. 修改 chunk_size=30
2. 修改 chunk_overlap=5
3. 再运行脚本
4. 查看召回结果是否变化
5. 思考 chunk 太小有什么问题
```

---

## 六十、课后任务四：测试 Metadata Filter
要求：

```text
1. 查询“退款规则是什么”
2. 不加 filter 跑一次
3. 加 doc_type=after_sales 跑一次
4. 加 doc_type=invoice 跑一次
5. 对比召回结果
```

---

## 六十一、课后任务五：增加一份知识文档
新增文档：

```text
会员积分规则
```

内容包含：

```text
积分获取
积分抵扣
积分过期
积分退回
```

然后测试：

```text
会员积分怎么退回？
```

---

## 六十二、课后任务六：回答为什么 RAG 会答错
要求从下面几层回答：

```text
1. 文档解析
2. Chunk 切分
3. Embedding
4. Retriever
5. Rerank
6. Prompt
7. LLM Generation
8. 文档版本
9. 权限过滤
```

---

## 六十三、课后任务七：设计企业知识库表
要求设计：

```text
knowledge_documents
knowledge_chunks
knowledge_query_logs
knowledge_feedbacks
```

并说明每张表解决什么问题。

---

## 六十四、课后任务八：整理面试话术
请准备 3 段话术：

```text
1. RAG 是什么
2. RAG 和 Fine-tuning 的区别
3. RAG 为什么会幻觉，怎么排查
```

---

## 六十五、本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 39 章我们就讲完了。

这一章我们正式进入 RAG 阶段。

大家一定要记住一句话：

```text
RAG 不是让大模型凭空回答，
而是先检索资料，再基于资料生成回答。
```

RAG 有两条链路：

```text
离线入库链路：
文档解析、清洗、切分、Embedding、写入向量库。

在线问答链路：
用户问题、query embedding、TopK 召回、Rerank、Context 拼接、LLM 生成、返回来源。
```

==RAG 的核心组件包括：==

```text
Document
Chunk
Embedding
Vector Store
Retriever
Rerank
Prompt
LLM
Source
Evaluation
```

还要记住：

```text
RAG 不等于向量数据库。
RAG 不等于 Fine-tuning。
RAG 不等于 Memory。
RAG 也不是接上就一定准。
```

真正企业级 RAG，要重点解决：

```text
文档解析
Chunk 设计
召回质量
权限过滤
版本控制
答案依据
评估体系
```

这一章我们还写了一个 Mini RAG，让大家从代码层面理解：

```text
文本怎么切分
怎么变成向量
怎么相似度搜索
怎么返回 TopK
怎么拼上下文
怎么生成带来源的回答
```

从下一章开始，我们正式进入企业文档解析。

---

---

> [!success] 一句话带走
> ==RAG 是一条流水线，任何一环偷懒，最后答案都会飘。==

> [!quote] 关于本文档
> 由原始讲义 `第 39 章｜RAG 原理.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
