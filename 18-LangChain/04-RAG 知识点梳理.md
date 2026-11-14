---
title: RAG 数据连接与检索 · 知识点梳理
tags: [langchain, rag, 速查, 知识点整理, python]
created: 2026-11-14
related:
  - "[[04-RAG 数据连接与检索]]"
  - "[[04.1-Retriever 检索器]]"
  - "[[09-LangChain 1.0 API 速查菜单]]"
  - "[[08-Day03 课堂复盘 RAG 实战与工具中间件]]"
source: "整理自 [[04-RAG 数据连接与检索]]（讲义 P35–P45）"
---

# RAG 数据连接与检索 · 知识点梳理

> [!abstract] 一句话
> 模型里没有你的数据 → 把外部数据接进来：**离线建库（加载 → 切分 → 嵌入 → 入库） + 在线问答（检索 → 拼 Prompt → 生成）**。全链路流通的数据单元是 `Document`。

> [!info] 检索（Retriever）部分已单独拆出
> 见 [[04.1-Retriever 检索器]]。本篇只保留它在全链路中的位置与接口。

---

## 0. 全链路速览

```mermaid
flowchart LR
    subgraph OFF["离线 · 建库"]
        S["数据源<br/>txt/pdf/html/md/db/网页"] -->|load()| L["Loader"]
        L -->|Document| C["TextSplitter"]
        C -->|Document[]| E["Embeddings"]
        E -->|向量| V[("VectorStore<br/>Chroma/FAISS/Milvus")]
    end
    subgraph ON["在线 · 问答"]
        Q["问题"] -->|同一 Embeddings| R["Retriever"]
        V -.相似度检索.-> R
        R -->|Document[] = context| P["Prompt<br/>question + context"]
        P --> M["LLM"] --> A["answer"]
    end
```

**关键分界**：`Embeddings` 同时服务于建库（嵌文档）和问答（嵌问题），两边必须是同一个模型，否则不在同一向量空间。

---

## 1. 核心组件速查表

| # | 环节 | 核心类 / 方法 | 输入 → 输出 | 记住这一句 |
|---|---|---|---|---|
| 0 | 数据单元 | `Document(page_content, metadata)` | — | `page_content` 拿去嵌入；`metadata` 存来源、页码、章节，检索结果可回溯出处 |
| 1 | 加载 | `WebBaseLoader(...).load()` | 数据源 → `list[Document]` | 统一接口就是 `load()`；第三方集成大多在 `langchain_community.document_loaders` |
| 2 | 切分 | `RecursiveCharacterTextSplitter(...).split_documents(docs)` | `list[Document]` → `list[Document]` | 转换器两步：① 切分 ② 转成 Document 对象 |
| 3 | 嵌入 | `DashScopeEmbeddings(model="text-embedding-v3")` | 文本 → 向量 | 「嵌入模型包装器」，与 LLM / Chat Model 包装器并称三大模型包装器 |
| 4 | 存储 | `Chroma.from_documents(documents, embedding)` | 向量 → 向量库 | `similarity_search` / `similarity_search_with_score` 是库自带查询 |
| 5 | 检索 | `vector_store.as_retriever()` | 问题 → `list[Document]` | **检索器 = 向量库的包装器**，换库不改查询代码 → [[04.1-Retriever 检索器]] |
| 6 | 生成 | `ChatPromptTemplate` + `client` | `question + context` → `AIMessage` | Prompt 里明确约束「只用上下文；不知道就说不知道」 |

### 1.1 支持的数据源
CSV、文件目录、HTML、JSON、Markdown、PDF，甚至网页、视频转录字幕。

> [!tip] `bs4.SoupStrainer` 不是可选项
> 网页直接 `load()` 会把导航、广告、页脚一起塞进上下文，浪费 Token 还干扰回答。按 CSS class / id 圈定正文是实战第一步：
> `bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("main-left left", "title")))`

---

## 2. 切分器与参数

| 切分器 | 特点 |
|---|---|
| `CharacterTextSplitter` | 按字符（默认 `\n\n`）切，用字符数衡量块大小 |
| `RecursiveCharacterTextSplitter` | **最常用**；递归按分隔符切，还支持按编程语言（python/java/go/cpp/js/php…）切代码 |
| `MarkdownHeaderTextSplitter` | 按 Markdown 标题层级切，保留章节结构 |

| 参数 | 作用 | 讲义示例值 |
|---|---|---|
| `chunk_size` | 每块大小 | 500 / 1000 |
| `chunk_overlap` | 相邻块重叠量，避免把一句完整语义切断 | 50 / 100 |

更多内置切分器：https://python.langchain.com/api_reference/text_splitters/index.html

---

## 3. 四种「查」的写法（最易混）

| 写法 | 返回 | 适用 |
|---|---|---|
| `vector_store.similarity_search("狸花猫")` | `list[Document]` | 调试直查 |
| `vector_store.similarity_search_with_score("狸花猫")` | `(Document, score)` | 需要看分数；**Chroma 默认 L2 距离，分数越小越相似** |
| `RunnableLambda(vector_store.similarity_search).bind(k=1).batch([...])` | 批量 `list[Document]` | 把「库方法」包装成 Runnable 后塞进 LCEL |
| `retriever.invoke("狸花猫")` | `list[Document]` | 生产链路，统一接口 |

> [!warning] 别把两个客户端搞混
> `get_lc_model_client()` 是**对话模型**（`ChatOpenAI`）；`DashScopeEmbeddings` 是**嵌入模型**。用途、模型名、计费都不同，但 RAG 里两个都要用。

---

## 4. 两条组装 RAG 链的路

### 4.1 LCEL 手写（V1.0 推荐）

```python
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([("human", "仅使用提供的上下文回答：{question}\n上下文：{context}")])

chain = (
    {"question": RunnablePassthrough(), "context": docs_find}
    | prompt
    | client
)
chain.invoke("请介绍一下猫")
```

**为什么必须 `RunnablePassthrough()`**：定义链时还不知道用户要问什么，它把输入**动态透传**为 `question`，同时并行查出 `context`。字典字面量在 LCEL 里会变成 `RunnableParallel`，**每个值必须是 Runnable 或可调用对象**——不能把「文档列表」或裸方法结果直接塞进去。详见 [[03.2-RunnableParallel]] / [[03.3-RunnablePassthrough]]。

### 4.2 classic 链路（讲义原写法）

```python
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain

chain1 = create_stuff_documents_chain(client, prompt_template)   # 把检索到的文档 stuff 进 prompt
chain2 = create_retrieval_chain(retriever, chain1)              # 先检索，再交给文档链
resp = chain2.invoke({"input": "张成刚是谁？"})                  # 返回 dict
print(resp["answer"])                                           # 还有 resp["context"] / resp["input"]
```

| 对比 | LCEL 手写 | classic 链路 |
|---|---|---|
| V1.0 状态 | 推荐，一等公民 | 已移到 `langchain_classic` |
| 灵活性 | 任意增删步骤 | 固定「检索 → stuff 文档 → 生成」 |
| 输入键 | 自定义（`question` / `input` 都行） | 约定 `input` |
| 输出 | `AIMessage`，可再接 `StrOutputParser` | `dict`，取 `["answer"]` |

> [!warning] 版本坑
> 讲义用的是 `from langchain.chains...`（v0.3 路径）。V1.0 里这两个函数都在 **`langchain_classic`**；新项目更推荐 LCEL 手写等价式：`{"context": retriever, "question": RunnablePassthrough()} | prompt | model | parser`。
> 据 [[08-Day03 课堂复盘 RAG 实战与工具中间件]] 逐页对比：RAG 这一章在 V0.3 → V1.0 **几乎逐字未改**，知识跨版本通用，唯一变化就是上面这个 import 路径。

---

## 5. import 路径速查（V1.0）

| 组件 | 路径 |
|---|---|
| `Document` | `langchain_core.documents` |
| `ChatPromptTemplate` | `langchain_core.prompts` |
| `RunnableLambda` / `RunnablePassthrough` | `langchain_core.runnables` |
| `WebBaseLoader` | `langchain_community.document_loaders` |
| `DashScopeEmbeddings` | `langchain_community.embeddings` |
| `RecursiveCharacterTextSplitter` | `langchain_text_splitters` |
| `Chroma` | `langchain_chroma`（§5）/ `langchain_community.vectorstores`（§7 讲义写法，两者并存） |
| `create_stuff_documents_chain` / `create_retrieval_chain` | `langchain_classic.chains.*` |

---

## 6. 踩坑清单

| 坑 | 处理 |
|---|---|
| 检索结果牛头不对马嘴 | `bs4.SoupStrainer` 圈正文；调 `chunk_size` / `chunk_overlap`；换更合适的 embedding 模型 |
| 以为分数越大越相关 | **反了**：Chroma 默认 L2 距离，越小越相似 |
| 切换向量库要改一堆代码 | 统一用 `as_retriever()`，别直接调各家 API |
| 把「检索结果」当 `context` 的值 | 值必须是 Runnable，用 `RunnablePassthrough` + 字典字面量组成 `RunnableParallel` |
| V1.0 找不到 `create_retrieval_chain` | 已移到 `langchain_classic`，或改 LCEL |
| 模型回答夹着 SQL 代码围栏 | 讲义 SQL 实战专门写了 `SQLCleaner(StrOutputParser)` 清理 → [[05-Agent 工具调用与中间件]] |

---

## 7. 自测 6 问

> [!question]- ① 全链路七个环节是什么？前后半段如何分界？
> 加载 → 切分 → 嵌入 → 存储 → 检索 → 拼 Prompt → 生成。前四步离线建库，后三步在线问答；`Embeddings` 横跨两边。

> [!question]- ② `Document` 两个字段各干什么？
> `page_content` 是会被拿去嵌入的文本；`metadata` 存来源/页码/章节，用于检索结果回溯出处。

> [!question]- ③ 为什么网页加载必须配 `SoupStrainer`？
> 否则导航/广告/页脚一起进上下文，浪费 Token 且干扰回答。

> [!question]- ④ 向量库自己就能查，为什么还要 Retriever？
> 屏蔽 Chroma / FAISS / Pinecone / Milvus 各自查询语法差异，提供统一 Runnable 接口；换库不改查询代码。→ [[04.1-Retriever 检索器]]

> [!question]- ⑤ `similarity_search_with_score` 的分数怎么读？
> Chroma 默认 L2 距离，**越小越相似**。

> [!question]- ⑥ LCEL 里为什么不能把文档列表直接写进 `context`？
> 字典字面量会变成 `RunnableParallel`，每个值必须是 Runnable 或可调用对象，才能在链执行时被真正调用。

---

## 8. 关联笔记

- 原文：[[04-RAG 数据连接与检索]]
- 检索专题：[[04.1-Retriever 检索器]]
- 链与 Runnable：[[03-链与 LCEL]]、[[03.1-RunnableLambda]]、[[03.2-RunnableParallel]]、[[03.3-RunnablePassthrough]]
- 速查与复盘：[[09-LangChain 1.0 API 速查菜单]]（§4.4/4.5）、[[08-Day03 课堂复盘 RAG 实战与工具中间件]]（§4.2 四种检索器）
- 延伸：[[Milvus 学习文档]]、[[pgvector vs Milvus 选型对比]]
- 往哪走：查询改写、重排、混合检索、RAG 效果评估（Advanced RAG）
