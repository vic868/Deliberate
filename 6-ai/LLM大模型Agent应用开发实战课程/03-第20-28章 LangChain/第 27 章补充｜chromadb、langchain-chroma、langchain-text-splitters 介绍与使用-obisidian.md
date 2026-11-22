---
title: "第 27 章补充｜切分、Chroma 与 Retriever"
chapter: "27"
source: "第 27 章补充｜chromadb、langchain-chroma、langchain-text-splitters 介绍与使用.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - rag
  - chromadb
  - text-splitter
---

# 第 27 章补充｜切分、Chroma 与 Retriever

> [!abstract] 本章重点
>
> - ==三个依赖分三层：切分、向量库、框架适配== — text-splitters 切文本，chromadb 存向量，langchain-chroma 把两者接进框架。
> - ==RecursiveCharacterTextSplitter 是默认首选== — 按段落、句子、字符逐级切，尽量不切断语义。
> - ==split_text 出字符串，create_documents 出 Document== — 后者带 metadata，入库时更方便。
> - ==VectorStore 负责存，Retriever 负责取== — Retriever 是给 Chain 用的统一检索接口。
> - ==Similarity Search 按向量距离找相近片段== — TopK 决定带几段进 Prompt。

> [!note] 大白话
>
> - **向量数据库**：把文本变成数字向量存起来，按「意思相近」而不是「关键词相同」来查。

> [!info] 导航与来源
> - 原始讲义：[[第 27 章补充｜chromadb、langchain-chroma、langchain-text-splitters 介绍与使用|打开原始讲义]]
> - [[第 26 章｜LangChain Agent|上一章｜第 26 章]]
> - [[第 28 章｜LangChain Agent + RAG|下一章｜第 28 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#二、langchain-text-splitters 是什么？]]
- [[#三、安装 langchain-text-splitters]]
- [[#四、RecursiveCharacterTextSplitter]]
- [[#五、最简单的文本切分案例]]
- [[#六、split_text 和 create_documents 的区别]]
- [[#七、chromadb 是什么？]]
- [[#八、什么叫向量数据库？]]
- [[#九、直接使用 chromadb]]
- [[#十、使用 ChromaDB 查询]]
- [[#十一、那 langchain-chroma 又是什么？]]
- [[#十二、可以把它们理解成三层]]
- [[#十三、安装 langchain-chroma]]
- [[#十四、三个依赖一起安装]]
- [[#十五、使用 LangChain + Chroma]]

在前面的 RAG 流程中，我们会涉及三个非常重要的 Python 包：

```bash
chromadb
langchain-chroma
langchain-text-splitters
```

很多刚开始学习 RAG 的同学看到这三个包会比较懵：

+ `chromadb` 是干什么的？
==+ `langchain-chroma` 和 `chromadb` 有什么区别？==
+ 为什么文本切分还要单独安装 `langchain-text-splitters`？
+ 它们三个在整个 RAG 流程中分别处于什么位置？

这一小节我们专门把这三个库讲清楚。

---

### 一、先从整个 RAG 流程理解它们的位置
一个最基础的 RAG 知识库流程，可以简化成：

```text
原始文档
   ↓
加载文档
   ↓
文本切分
langchain-text-splitters
   ↓
生成 Embedding 向量
   ↓
存入向量数据库
chromadb
   ↓
LangChain 操作 Chroma
langchain-chroma
   ↓
用户提问
   ↓
相似度检索
   ↓
找到相关 Chunk
   ↓
交给大模型生成答案
```

所以这三个库的职责其实完全不同。

| 包 | 主要作用 |
| --- | --- |
| `langchain-text-splitters` | 把长文档切成一个个 Chunk |
| `chromadb` | 真正负责存储和检索向量数据 |
| `langchain-chroma` | 把 ChromaDB 接入 LangChain 的适配层 |


可以先记住一句话：

`langchain-text-splitters` 负责切，`chromadb` 负责存，`langchain-chroma` 负责让 LangChain 更方便地操作 ChromaDB。

---

## 二、langchain-text-splitters 是什么？
### 2.1 为什么需要文本切分？
假设我们现在有一个企业员工手册：

```text
员工手册.pdf
```

里面可能有：

```text
200 页
10 万字
```

我们一般不会直接把整个 PDF 转成一个向量。

因为这样会产生很多问题。

比如用户问：

```text
员工一年有几天年假？
```

真正有用的信息可能只存在于第 57 页的一小段文字中。

如果整个 10 万字文档只有一个 Embedding：

```text
10 万字文档
    ↓
一个向量
```

那么这个向量表达的是整个文档的综合语义。

用户查询：

```text
一年有几天年假？
```

检索效果通常会非常差。

==所以 RAG 一般会先把大文档拆成很多小块：==

```text
员工手册

↓ 切分

Chunk 1：公司介绍

Chunk 2：考勤制度

Chunk 3：请假制度

Chunk 4：年假制度

Chunk 5：报销制度

Chunk 6：离职制度
```

然后每一个 Chunk 单独生成 Embedding。

```text
Chunk 1 → Vector 1

Chunk 2 → Vector 2

Chunk 3 → Vector 3

Chunk 4 → Vector 4
```

用户再问：

```text
一年有多少天年假？
```

就更容易检索到：

```text
Chunk 4：年假制度
```

这就是文本切分的意义。

---

## 三、安装 langchain-text-splitters
安装：

```bash
pip install langchain-text-splitters
```

如果使用 `uv`：

```bash
uv add langchain-text-splitters
```

现在 LangChain 已经把 Text Splitter 拆成了独立的 `langchain-text-splitters` 包，常用的文本切分器都可以从这里导入。

例如：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

---

## 四、RecursiveCharacterTextSplitter
在普通 RAG 场景中，我们最常用的是：

```python
RecursiveCharacterTextSplitter
```

它可以翻译成：

```text
递归字符文本切分器
```

LangChain 官方也把它作为通用文本场景下常用的切分方式之一。它会按照一组分隔符逐级尝试拆分文本，例如优先保留段落，然后换行、空格等结构。

导入：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

创建：

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
```

这里最重要的两个参数：

```text
chunk_size
chunk_overlap
```

---

### 4.1 chunk_size
```python
chunk_size=500
```

表示：

```text
每一个 Chunk 最大大约 500 个字符
```

例如原始文档：

```text
10000 字
```

可能被拆成：

```text
Chunk 1：500 字
Chunk 2：500 字
Chunk 3：500 字
...
```

需要注意：

`chunk_size` 并不意味着所有 Chunk 都严格等于 500 个字符。

因为切分器会尽量按照：

```text
段落
↓
换行
↓
空格
↓
字符
```

这样的结构进行拆分，尽量避免把完整语义从中间强行切断。

---

### 4.2 chunk_overlap
第二个非常重要的参数：

```python
chunk_overlap=50
```

表示相邻的两个 Chunk 之间保留一部分重复内容。

例如：

```text
Chunk 1

AAAA
BBBB
CCCC
DDDD
```

==下一个 Chunk 不一定直接从 EEEE 开始。==

而可能变成：

```text
Chunk 2

DDDD
EEEE
FFFF
GGGG
```

这里：

```text
DDDD
```

就是 overlap。

为什么需要重叠？

因为一句完整的话很可能刚好被切在两个 Chunk 中间。

例如原文：

```text
员工工作满一年之后，可以享受每年 5 天带薪年假。
```

如果正好切成：

```text
Chunk 1：

员工工作满一年之后，可以享受
```

```text
Chunk 2：

每年 5 天带薪年假。
```

两个 Chunk 的语义都不完整。

增加 overlap 后就可能变成：

```text
Chunk 1：

员工工作满一年之后，可以享受每年
```

```text
Chunk 2：

可以享受每年 5 天带薪年假。
```

这样检索效果通常会更稳定。

---

## 五、最简单的文本切分案例
例如：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter


text = """
公司员工工作满一年后，可以享受带薪年假。

工作满一年不满十年的员工，每年享受5天年假。

工作满十年不满二十年的员工，每年享受10天年假。

工作满二十年以上的员工，每年享受15天年假。

员工申请年假需要提前在OA系统提交申请，并由直属领导审批。
"""


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=80,
    chunk_overlap=20,
)


chunks = text_splitter.split_text(text)


for index, chunk in enumerate(chunks):
    print(f"Chunk {index + 1}")
    print(chunk)
    print("-" * 50)
```

可能得到：

```text
Chunk 1
公司员工工作满一年后，可以享受带薪年假。
工作满一年不满十年的员工，每年享受5天年假。

--------------------------------------------------

Chunk 2
工作满一年不满十年的员工，每年享受5天年假。
工作满十年不满二十年的员工，每年享受10天年假。

--------------------------------------------------
```

可以看到：

```text
长文本
↓
RecursiveCharacterTextSplitter
↓
多个小文本 Chunk
```

---

## 六、split_text 和 create_documents 的区别
这里还需要认识两个常见方法：

```python
split_text()
```

和：

```python
create_documents()
```

---

### 6.1 split_text
如果写：

```python
chunks = text_splitter.split_text(text)
```

得到的是：

```python
list[str]
```

类似：

```python
[
    "第一段文本",
    "第二段文本",
    "第三段文本",
]
```

适合单纯处理字符串。

---

### 6.2 create_documents
如果使用：

```python
documents = text_splitter.create_documents([text])
```

得到的是：

```text
Document
```

对象。

例如：

```python
for document in documents:
    print(document.page_content)
    print(document.metadata)
```

LangChain 的 `Document` 一般包含两个非常重要的部分：

```text
page_content
metadata
```

例如：

```python
Document(
    page_content="员工每年享受5天带薪年假。",
    metadata={
        "source": "员工手册.pdf"
    }
)
```

==在真正的 RAG 项目中，更推荐围绕：==

```text
Document
```

对象处理数据。

因为后面还需要保留：

```text
文件名
页码
文档ID
部门
知识库ID
更新时间
权限信息
```

等 Metadata。

LangChain 官方文档也区分了 `.split_text()` 和 `.create_documents()`：前者返回字符串切片，后者用于创建下游 LangChain 流程使用的 `Document`。

---

## 七、chromadb 是什么？
接下来进入第二个库：

```text
chromadb
```

安装：

```bash
pip install chromadb
```

或者：

```bash
uv add chromadb
```

ChromaDB 本质上是一个：

向量数据库。

它主要负责保存：

```text
Embedding Vector
Document
Metadata
ID
```

并提供向量相似度检索能力。

Chroma 的 Collection 可以存储文档、Embedding 和 Metadata，并对这些数据进行索引和检索。

---

## 八、什么叫向量数据库？
假设有三句话：

```text
苹果是一种水果

香蕉是一种水果

Python是一门编程语言
```

经过 Embedding 模型以后，它们可能变成：

```text
苹果是一种水果
↓
[0.23, 0.81, 0.19, 0.54, ...]

香蕉是一种水果
↓
[0.25, 0.79, 0.21, 0.51, ...]

Python是一门编程语言
↓
[0.91, 0.12, 0.67, 0.08, ...]
```

这些数组就是：

```text
Embedding Vector
```

也就是：

```text
向量
```

向量数据库主要就是帮助我们存储、索引这些向量。

用户提问：

```text
有哪些水果？
```

也生成一个 Query Vector：

```text
有哪些水果？

↓

[0.24, 0.80, 0.20, 0.52, ...]
```

然后寻找最接近的向量：

```text
Query Vector

    ↓ 相似度搜索

苹果是一种水果     0.95

香蕉是一种水果     0.93

Python是一门语言   0.31
```

最后找到：

```text
苹果
香蕉
```

相关内容。

这就是 RAG 中：

```text
Vector Search
```

最核心的原理。

---

## 九、直接使用 chromadb
其实我们完全可以不使用 LangChain，直接操作 ChromaDB。

例如：

```python
import chromadb


client = chromadb.Client()


collection = client.create_collection(
    name="company_knowledge"
)


collection.add(
    ids=[
        "doc_001",
        "doc_002",
        "doc_003",
    ],
    documents=[
        "员工工作满一年后可以享受5天带薪年假。",
        "员工报销需要通过OA系统提交申请。",
        "员工离职需要提前30天提交申请。",
    ],
)
```

这里：

```python
collection
```

可以理解成关系型数据库里面的一张：

```text
表
```

例如：

```text
company_knowledge
```

专门保存企业知识库数据。

Chroma 原生 Python API 支持创建 Collection、添加文档以及执行 Query。

---

## 十、使用 ChromaDB 查询
例如：

```python
results = collection.query(
    query_texts=[
        "员工有多少天年假？"
    ],
    n_results=2,
)


print(results)
```

这里：

```python
n_results=2
```

表示：

```text
返回最相似的两个结果
```

整个过程：

```text
用户问题

员工有多少天年假？

↓

Embedding

↓

Vector Search

↓

Top 2

↓

员工工作满一年后可以享受5天带薪年假
```

==这就是最基础的向量检索。==

---

## 十一、那 langchain-chroma 又是什么？
现在就到了很多同学最容易混淆的地方。

我们已经安装了：

```text
chromadb
```

为什么还需要：

```text
langchain-chroma
```

？

因为：

```text
chromadb
```

是 Chroma 自己提供的 Python SDK。

而：

```text
langchain-chroma
```

是：

LangChain 官方生态中用于连接 Chroma 的 VectorStore 集成包。

当前 LangChain 的 Chroma 集成通过独立的 `langchain-chroma` 包提供，其中核心类就是 `Chroma` Vector Store。

---

## 十二、可以把它们理解成三层
整个关系可以理解成：

```text
你的 RAG 业务代码

        ↓

LangChain

        ↓

langchain-chroma

        ↓

chromadb

        ↓

向量数据
```

也就是说：

```text
chromadb
```

是真正干活的数据库。

而：

```text
langchain-chroma
```

相当于一个：

```text
LangChain Adapter
```

也就是适配器。

它把 ChromaDB 包装成 LangChain 标准的：

```text
VectorStore
```

接口。

==所以以后我们可以非常方便地写：==

```python
vector_store.add_documents(...)
```

```python
vector_store.similarity_search(...)
```

```python
vector_store.as_retriever(...)
```

而不用直接操作底层 Chroma API。

---

## 十三、安装 langchain-chroma
安装：

```bash
pip install langchain-chroma
```

或者：

```bash
uv add langchain-chroma
```

导入：

```python
from langchain_chroma import Chroma
```

注意不要继续使用一些旧教程中的：

```python
from langchain.vectorstores import Chroma
```

新版本项目建议直接使用独立包：

```python
from langchain_chroma import Chroma
```

---

## 十四、三个依赖一起安装
我们的项目可以直接安装：

```bash
pip install chromadb langchain-chroma langchain-text-splitters
```

如果课程项目使用 `uv`：

```bash
uv add chromadb langchain-chroma langchain-text-splitters
```

安装完成以后：

```text
langchain-text-splitters
        ↓
负责切 Chunk

chromadb
        ↓
负责存储向量

langchain-chroma
        ↓
LangChain 操作 Chroma
```

---

## 十五、使用 LangChain + Chroma
假设前面的课程中我们已经创建好了：

```python
embeddings
```

Embedding 模型。

那么就可以创建一个 Chroma VectorStore：

```python
from langchain_chroma import Chroma


vector_store = Chroma(
    collection_name="company_knowledge",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)
```

这里几个参数分别是什么意思？

---

### collection_name
```python
collection_name="company_knowledge"
```

表示 Collection 名称。

可以理解成：

```text
知识库名称
```

例如：

```text
company_knowledge
product_knowledge
customer_service
employee_handbook
```

---

### embedding_function
```python
embedding_function=embeddings
```

表示：

文档和 Query 使用哪个 Embedding 模型转换成向量。

例如项目中可以使用：

```text
Qwen Embedding
OpenAI Embedding
BGE
HuggingFace Embedding
```

等等。

整个流程：

```text
Document

↓

Embedding Model

↓

Vector

↓

ChromaDB
```

---

### persist_directory
```python
persist_directory="./chroma_db"
```

表示：

```text
Chroma 数据保存目录
```

例如：

```text
项目目录

├── app
├── data
├── chroma_db
└── main.py
```

这样程序重新启动后，之前构建好的本地知识库还可以继续使用。

---

## 十六、完整 RAG 入库流程
现在把前面的内容串起来。

假设我们有一份企业员工制度。

首先创建 Document：

```python
from langchain_core.documents import Document


documents = [
    Document(
        page_content="""
        员工工作满一年后可以享受带薪年假。
        工作满一年不满十年的员工，每年享受5天年假。
        工作满十年不满二十年的员工，每年享受10天年假。
        工作满二十年以上的员工，每年享受15天年假。
        """,
        metadata={
            "source": "员工手册",
            "category": "年假制度",
        },
    ),
    Document(
        page_content="""
        员工发生业务费用以后，需要在OA系统提交报销申请。
        报销申请需要上传对应的发票以及费用明细。
        """,
        metadata={
            "source": "员工手册",
            "category": "报销制度",
        },
    ),
]
```

---

## 十七、第一步：切分 Document
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)


chunks = text_splitter.split_documents(documents)


print("原始文档数量：", len(documents))

print("切分后的 Chunk 数量：", len(chunks))
```

整个过程：

```text
Document

↓

Text Splitter

↓

Chunk

↓

Chunk

↓

Chunk
```

---

## 十八、第二步：保存到 Chroma
假设：

```python
embeddings
```

是课程前面已经创建好的 Embedding 对象。

```python
from langchain_chroma import Chroma


vector_store = Chroma(
    collection_name="company_knowledge",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)


vector_store.add_documents(chunks)
```

这时候内部会做几件事：

```text
Chunk

↓

Embedding Model

↓

Embedding Vector

↓

Chroma

↓

保存
```

最终大概形成：

```text
ChromaDB

├── Chunk 001
│   ├── document
│   ├── embedding
│   └── metadata
│
├── Chunk 002
│   ├── document
│   ├── embedding
│   └── metadata
│
└── Chunk 003
    ├── document
    ├── embedding
    └── metadata
```

---

## 十九、第三步：Similarity Search
知识库建好以后，就可以搜索了。

例如：

```python
query = "工作两年的员工有多少天年假？"


results = vector_store.similarity_search(
    query,
    k=3,
)


for index, document in enumerate(results):
    print(f"Result {index + 1}")

    print(document.page_content)

    print(document.metadata)

    print("-" * 50)
```

其中：

```python
k=3
```

表示：

```text
TopK = 3
```

也就是：

```text
找最相似的三个 Chunk
```

整个链路：

```text
工作两年的员工有多少天年假？

↓

Embedding

↓

Query Vector

↓

Chroma Vector Search

↓

Top3 Chunk
```

---

## 二十、使用 Retriever
LangChain 中通常不会一直直接调用：

```python
similarity_search()
```

而是把 VectorStore 转成：

```text
Retriever
```

例如：

```python
retriever = vector_store.as_retriever(
    search_kwargs={
        "k": 3,
    }
)
```

然后：

```python
documents = retriever.invoke(
    "工作两年的员工有多少天年假？"
)


for document in documents:
    print(document.page_content)
```

这一步非常重要。

因为到了后面的：

```text
RAG Chain
Agent
LangGraph
```

里面，我们大量使用的其实是：

```text
Retriever
```

而不是直接操作数据库。

---

## 二十一、VectorStore 和 Retriever 的关系
可以这样理解：

```text
Chroma

↓

VectorStore

↓

Retriever
```

`VectorStore` 更关注：

```text
向量怎么存
怎么搜索
怎么删除
怎么更新
```

而 Retriever 更关注：

```text
用户给我一个 Query

↓

我帮你找到相关 Document
```

Retriever 对上层业务隐藏了底层到底是：

```text
Chroma
pgvector
Milvus
Pinecone
Elasticsearch
```

==所以以后我们换向量数据库，上层很多代码都可以保持不变。==

---

## 二十二、三个库最终怎么配合？
到这里我们再完整看一次。

### 第一步：读取原始文档
```text
PDF
Word
Markdown
TXT
网页
```

变成：

```text
Document
```

---

### 第二步：langchain-text-splitters
```text
Document

↓

RecursiveCharacterTextSplitter

↓

Chunk 1
Chunk 2
Chunk 3
Chunk 4
```

作用：

```text
切文档
```

---

### 第三步：Embedding
```text
Chunk

↓

Embedding Model

↓

Vector
```

例如：

```text
[0.17, 0.72, 0.31, ...]
```

---

### 第四步：chromadb
```text
Vector
Document
Metadata

↓

ChromaDB
```

作用：

```text
存向量
建立索引
做相似度搜索
```

---

### 第五步：langchain-chroma
LangChain 不直接关心 Chroma 的底层 API。

而是通过：

```python
from langchain_chroma import Chroma
```

统一操作：

```text
ChromaDB
```

于是我们的业务代码可以直接：

```python
vector_store.add_documents()
```

```python
vector_store.similarity_search()
```

```python
vector_store.as_retriever()
```

---

## 二十三、最终关系图
把这三个库放到完整 RAG 流程里面：

```text
企业文档
                     │
                     ▼
                  Document
                     │
                     ▼
        langchain-text-splitters
                     │
                     ▼
              Text Splitter
                     │
                     ▼
             Chunk / Chunk
                     │
                     ▼
              Embedding Model
                     │
                     ▼
              Embedding Vector
                     │
                     ▼
              langchain-chroma
                     │
                     ▼
                  chromadb
                     │
                     ▼
               Vector Store


用户问题
   │
   ▼
Embedding
   │
   ▼
Query Vector
   │
   ▼
Chroma 相似度搜索
   │
   ▼
TopK Chunk
   │
   ▼
Prompt
   │
   ▼
LLM
   │
   ▼
最终答案
```

---

## 二十四、一个非常容易记忆的理解方式
以后如果再看到：

```text
chromadb
langchain-chroma
langchain-text-splitters
```

可以直接这样记。

#### langchain-text-splitters
负责：

```text
切
```

把：

```text
大文档
```

切成：

```text
小 Chunk
```

---

#### chromadb
负责：

```text
存 + 查
```

保存：

```text
Vector
Document
Metadata
```

并进行：

```text
Vector Search
```

---

#### langchain-chroma
负责：

```text
连接
```

把：

```text
LangChain
```

和：

```text
ChromaDB
```

连接起来。

最终就是一句话：

`langchain-text-splitters` 负责切文档，`chromadb` 负责存储和检索向量，`langchain-chroma` 负责让 LangChain 用统一的 VectorStore 接口操作 ChromaDB。

---

## 二十五、实际企业项目中应该怎么选？
需要特别说明：

Chroma 非常适合：

```text
学习 RAG
本地开发
课程 Demo
个人知识库
原型验证
POC
```

因为它：

```text
安装简单
API 简单
本地即可运行
开发成本低
```

所以在我们的：

**《从0到1大模型开发实战》**

课程中，用它学习：

```text
Document
Chunk
Embedding
Vector Store
Retriever
RAG
```

整个核心流程非常合适。

但是到了真正大型企业项目，需要综合考虑：

```text
数据规模
并发量
高可用
备份恢复
权限
Metadata Filter
混合检索
集群部署
运维成本
```

再选择：

```text
pgvector

Milvus

Elasticsearch

Pinecone

Qdrant
```

等方案。

==所以这里学习 Chroma 的重点，并不是要求以后所有企业项目都一定使用 Chroma。==

真正需要掌握的是：

```text
Document
      ↓
Chunk
      ↓
Embedding
      ↓
Vector Store
      ↓
Retriever
      ↓
LLM
```

这一整套 RAG 思维。

只要把这套流程真正理解了，后面从：

```text
Chroma
```

切换成：

```text
pgvector / Milvus / Qdrant
```

本质上只是：

```text
Vector Store 实现发生了变化
```

RAG 的核心思想没有变。

---

## 二十六、本小节总结

> [!success] 复盘要点
> 复盘时重点看这一节。

这一小节我们认识了三个非常重要的依赖：

```text
chromadb
langchain-chroma
langchain-text-splitters
```

其中：

```text
langchain-text-splitters
```

负责：

```text
文档切分
```

核心类：

```python
RecursiveCharacterTextSplitter
```

重点参数：

```python
chunk_size
chunk_overlap
```

---

`chromadb` 负责：

```text
Embedding Vector 存储

Document 存储

Metadata 存储

向量相似度检索
```

---

`langchain-chroma` 负责：

```text
把 ChromaDB 封装成 LangChain VectorStore
```

让我们可以统一使用：

```python
add_documents()
```

```python
similarity_search()
```

```python
as_retriever()
```

最终它们在 RAG 中形成：

```text
Document

↓

langchain-text-splitters

↓

Chunk

↓

Embedding

↓

langchain-chroma

↓

chromadb

↓

Retriever

↓

LLM
```

下一步，我们就可以在这个基础上继续完成真正完整的：

```text
文档加载
+
文档切分
+
Embedding
+
Vector Store
+
Retriever
+
Prompt
+
LLM
```

完整 LangChain RAG 流程。

---

> [!success] 一句话带走
> ==先分清切分、存储、适配三层，RAG 链路就不会混。==

> [!quote] 关于本文档
> 由原始讲义 `第 27 章补充｜chromadb、langchain-chroma、langchain-text-splitters 介绍与使用.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
