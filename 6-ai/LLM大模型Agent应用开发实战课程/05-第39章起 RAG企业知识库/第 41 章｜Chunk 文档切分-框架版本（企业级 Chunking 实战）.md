**核心技术：** LangChain Text Splitters、RecursiveCharacterTextSplitter、MarkdownHeaderTextSplitter、TokenTextSplitter、ParentDocumentRetriever、Document Metadata

**课程定位：** 掌握企业知识库文档切分策略，理解 Chunk Size、Chunk Overlap、语义切分、结构化切分及 Parent-Child Chunking，并完成文档切分工程实战。

---

## 一、本章学习目标
在第 40 章中，我们已经完成企业文档解析。

解析后的文档通常是一整篇文本：

```plain
员工手册

第一章：考勤制度

员工每日需要按时打卡。
迟到需要按照公司制度进行处理。

第二章：请假制度

员工申请年假需要提前三个工作日。
员工申请病假需要提交相关证明。
```

但是，企业知识库不能直接将整篇文档作为一个向量存储。

原因：

+ 文档太长，Embedding 模型存在输入限制。
+ 文档内容过多，检索时容易引入无关内容。
+ 一篇文档可能包含多个不同主题。
+ 文档过大，检索精度可能下降。
+ LLM 上下文有限，无法无限输入原始文档。

因此，需要对文档进行切分。

本章重点掌握：

1. Chunk 是什么？
2. 为什么 RAG 需要 Chunk？
3. Chunk Size 如何选择？
4. Chunk Overlap 如何设置？
5. RecursiveCharacterTextSplitter 如何使用？
6. TokenTextSplitter 与字符切分有什么区别？
7. Markdown 文档如何保留标题结构？
8. Parent-Child Chunking 如何实现？
9. 企业知识库如何设计 Chunk Metadata？
10. 如何评估 Chunking 的效果？

---

## 二、Chunk 是什么？
Chunk 可以理解为文档切分之后的一个文本片段。

例如原始文档：

```plain
员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
年假天数根据员工工龄及公司制度确定。
```

切分后：

```plain
Chunk 1：
员工申请年假需要提前三个工作日提交申请。

Chunk 2：
审批通过后才能休假。

Chunk 3：
年假天数根据员工工龄及公司制度确定。
```

每一个 Chunk 都可以独立进行 Embedding。

```plain
Document
   ↓
Chunking
   ↓
Chunk 1
Chunk 2
Chunk 3
   ↓
Embedding
   ↓
Vector Database
```

在 RAG 系统中：

**通常以 Chunk 为单位进行向量化、存储、检索和上下文组织。**

注意：

Chunk 不一定等于一句话，也不一定等于一个段落。

Chunk 的设计目标是：

在保证语义完整性的前提下，让每个文本片段能够有效参与检索。

---

## 三、为什么 Chunking 会影响 RAG 效果？
Chunking 是 RAG 中非常重要的一个环节。

同样的 Embedding 模型、同样的 Vector Database，仅仅调整 Chunking 策略，就可能导致检索效果发生明显变化。

### 3.1 Chunk 太大
假设一个 Chunk 包含：

```plain
考勤制度
请假制度
报销制度
员工晋升制度
薪资制度
```

用户提问：

```plain
年假需要提前多久申请？
```

虽然这个 Chunk 包含答案，但同时包含大量无关内容。

可能产生的问题：

+ 检索内容不够聚焦
+ 上下文噪声增加
+ LLM 需要从大段文本中提取答案
+ Token 消耗增加
+ 相关信息容易被无关信息干扰

### 3.2 Chunk 太小
如果切分为：

```plain
Chunk 1：
员工申请

Chunk 2：
年假

Chunk 3：
需要提前三个

Chunk 4：
工作日
```

原本完整的语义被破坏。

可能产生的问题：

+ 语义不完整
+ 检索结果缺少上下文
+ 关键条件与结论被拆开
+ 需要召回更多 Chunk 才能恢复完整信息

### 3.3 Chunking 的核心目标
```plain
Chunk 太大
   ↓
上下文噪声增加

Chunk 太小
   ↓
语义信息丢失

合理 Chunk
   ↓
语义完整 + 内容聚焦 + 检索准确
```

因此：

**Chunking 不是单纯的文本切割，而是面向检索的知识组织策略。**

---

## 四、Chunk Size 与 Chunk Overlap
### 4.1 Chunk Size
Chunk Size 表示一个 Chunk 的最大长度。

例如：

```plain
chunk_size = 500
```

在 RecursiveCharacterTextSplitter 默认配置下，长度通常按照字符数计算。

注意：

```plain
500 Characters
≠
500 Tokens
```

中文、英文、代码等内容的 Token 数量与字符数并不完全相同。

### 4.2 Chunk Overlap
Chunk Overlap 表示相邻 Chunk 之间保留的重叠内容。

例如：

```plain
原始文本：

A B C D E F G H I J
```

Chunk Size = 6

Overlap = 2

切分结果：

```plain
Chunk 1：
A B C D E F

Chunk 2：
E F G H I J
```

这里 E、F 被保留在两个 Chunk 中。

Overlap 的作用：

+ 保留跨 Chunk 的上下文
+ 降低重要信息被边界切断的风险
+ 增强相邻内容之间的连续性

但 Overlap 过大也会带来：

+ 重复向量
+ 向量数据库体积增加
+ Embedding 成本增加
+ 检索重复内容
+ 上下文冗余

### 4.3 企业常用参数参考
| 场景 | Chunk Size 参考 | Overlap 参考 |
| --- | --- | --- |
| 普通文本知识库 | 400–800 字符 | 50–100 |
| 企业制度文档 | 500–1000 字符 | 50–150 |
| 技术文档 | 500–1200 字符 | 80–150 |
| FAQ | 100–500 字符 | 0–50 |
| 长篇文档 | 800–1500 字符 | 100–200 |


这些是初始实验范围，不是统一标准。

实际参数应该根据：

+ Embedding 模型
+ 文档结构
+ 用户问题
+ 检索准确率
+ Recall@K
+ Context Precision
+ 最终答案质量

进行调整。

---

## 五、LangChain RecursiveCharacterTextSplitter
这是企业 RAG 中最常用的通用切分方式之一。

官方推荐使用 RecursiveCharacterTextSplitter 作为通用文本切分器。

它不是直接按照固定长度截断，而是优先寻找合理的文本边界。

默认分隔符：

```plain
[
    "\n\n",
    "\n",
    " ",
    "",
]
```

切分优先级：

```plain
段落
  ↓
换行
  ↓
空格
  ↓
字符
```

尽可能保留完整段落。

官方文档：

[https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)

### 5.1 项目初始化
```plain
uv init chunking-demo --python 3.12

cd chunking-demo

uv add langchain-core langchain-text-splitters
```

项目结构：

```plain
chunking-demo/
├── pyproject.toml
├── data/
│   └── employee-handbook.txt
├── chunking_demo.py
├── markdown_chunking.py
├── token_chunking.py
└── parent_child_chunking.py
```

### 5.2 准备测试文档
创建 `data/employee-handbook.txt`：

```plain
员工手册

第一章：考勤制度

员工每日需要按时打卡。
迟到需要按照公司制度进行处理。
员工因特殊情况无法打卡，需要及时向直属领导说明。

第二章：请假制度

员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
员工申请病假需要提交医院相关证明。

第三章：报销制度

员工出差产生的交通费用可以申请报销。
报销需要提供合法有效的票据。
报销申请需要经过直属领导审批。
```

### 5.3 创建 chunking_demo.py
```python
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def main():
    file_path = Path("data/employee-handbook.txt")

    text = file_path.read_text(encoding="utf-8")

    document = Document(
        page_content=text,
        metadata={
            "source": str(file_path),
            "document_id": "employee-handbook",
            "department": "HR",
        },
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=30,
        length_function=len,
        separators=[
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            "；",
            "，",
            " ",
            "",
        ],
    )

    chunks = splitter.split_documents([document])

    print(f"原文长度：{len(text)}")
    print(f"Chunk 数量：{len(chunks)}")

    for index, chunk in enumerate(chunks, start=1):
        print(f"\n===== Chunk {index} =====")
        print("Content:", chunk.page_content)
        print("Metadata:", chunk.metadata)


if __name__ == "__main__":
    main()
```

运行：

```plain
uv run python chunking_demo.py
```

这里的切分结果会尽可能保留中文句子、段落和标点边界。

### 5.4 create_documents 与 split_documents
`split_text()`：

```plain
chunks = splitter.split_text(text)
```

返回：

```plain
list[str]
```

`create_documents()`：

```python
documents = splitter.create_documents(
    [text],
    metadatas=[
        {
            "source": "employee-handbook",
        }
    ],
)
```

返回：

```plain
list[Document]
```

`split_documents()`：

```plain
chunks = splitter.split_documents(documents)
```

适用于已经存在 LangChain Document 对象的情况。

企业 RAG 项目建议优先使用 Document 方式，方便保留 Metadata。

---

## 六、Token-Based Chunking
字符切分不一定等于 Token 切分。

对于 LLM 上下文、Token 预算敏感的场景，可以使用 TokenTextSplitter。

### 6.1 安装依赖
```plain
uv add langchain-text-splitters tiktoken
```

### 6.2 token_chunking.py
```python
from langchain_text_splitters import TokenTextSplitter


def main():
    text = """
    RAG 是 Retrieval Augmented Generation 的缩写。
    它通过检索外部知识，为大语言模型提供额外上下文。
    企业知识库通常使用 RAG 实现文档问答、制度查询和知识助手。
    """

    splitter = TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = splitter.split_text(text)

    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index}")
        print(chunk)


if __name__ == "__main__":
    main()
```

### 6.3 Token 切分适用场景
+ 控制 LLM 输入 Token
+ 控制上下文窗口
+ 需要按照 Token 长度进行切分
+ Token 成本敏感
+ 需要进行模型上下文预算管理

注意：

`TokenTextSplitter` 可能直接按照 Token 边界切分文本，不保证保留完整句子或语义结构。

对于普通企业文档，建议优先使用 RecursiveCharacterTextSplitter，再根据 Token 预算进行调整。

---

## 七、MarkdownHeaderTextSplitter
企业知识库中经常存在 Markdown 文档：

```plain
# 员工手册

## 请假制度

### 年假

员工申请年假需要提前三个工作日提交申请。

### 病假

员工申请病假需要提交医院相关证明。

## 报销制度

员工出差产生的交通费用可以申请报销。
```

如果直接使用普通字符切分：

```plain
Chunk 1：
员工手册
请假制度
年假
员工申请年假需要提前三个工作日...

Chunk 2：
病假
员工申请病假需要提交医院相关证明...
```

可能丢失章节层级信息。

因此，Markdown 文档建议先按照标题切分。

### 7.1 markdown_chunking.py
```python
from pathlib import Path

from langchain_text_splitters import (
MarkdownHeaderTextSplitter,
RecursiveCharacterTextSplitter,
)


def main():
    text = Path(
        "data/employee-handbook.md"
    ).read_text(encoding="utf-8")

    # 第一步：按照 Markdown 标题切分
    headers_to_split_on = [
        ("#", "Header1"),
        ("##", "Header2"),
        ("###", "Header3"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )

    header_documents = markdown_splitter.split_text(text)

    print("标题切分数量:", len(header_documents))

    # 第二步：对过长的章节进一步切分
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
    )

    chunks = recursive_splitter.split_documents(
        header_documents
    )

    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index}")
        print("Content:", chunk.page_content)
        print("Metadata:", chunk.metadata)


if __name__ == "__main__":
    main()
```

示例 Metadata：

```plain
{
    "Header1": "员工手册",
    "Header2": "请假制度",
    "Header3": "年假"
}
```

这种方式能够保留：

+ 文档标题
+ 一级章节
+ 二级章节
+ 三级章节

后续检索时可以利用章节信息。

### 7.2 为什么 Markdown Header 很重要？
用户提问：

```plain
年假申请规则是什么？
```

检索到的内容：

```plain
员工申请年假需要提前三个工作日提交申请。
```

如果同时保留：

```plain
Header1 = 员工手册
Header2 = 请假制度
Header3 = 年假
```

那么上下文可以更加明确：

```plain
员工手册 > 请假制度 > 年假

员工申请年假需要提前三个工作日提交申请。
```

这有助于减少章节语义丢失。

---

## 八、Parent-Child Chunking
普通 Chunking 的一个问题：

Chunk 越小，检索越精准，但上下文可能不足。

Chunk 越大，上下文越完整，但检索精度可能下降。

Parent-Child Chunking 用于解决这个问题。

### 8.1 Parent 与 Child 的概念
```plain
Parent Document
        ↓
Child Chunk 1
Child Chunk 2
Child Chunk 3
Child Chunk 4
```

其中：

+ Parent：较大的原始文本片段
+ Child：较小的检索片段

检索时：

```plain
用户问题
   ↓
Child Vector Search
   ↓
找到最相关的 Child
   ↓
映射回 Parent
   ↓
返回 Parent Context
   ↓
LLM 生成答案
```

例如：

```plain
Parent：

员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
年假天数根据员工工龄及公司制度确定。
```

Child：

```plain
Child 1：
员工申请年假需要提前三个工作日提交申请。

Child 2：
审批通过后才能休假。

Child 3：
年假天数根据员工工龄及公司制度确定。
```

用户查询：

```plain
年假提前多久申请？
```

通过 Child 精准定位，再返回 Parent 提供上下文。

### 8.2 ParentDocumentRetriever
LangChain 提供 ParentDocumentRetriever。

安装：

```plain
uv add langchain-classic langchain-core langchain-text-splitters langchain-ollama
```

注意：

ParentDocumentRetriever 当前位于 `langchain_classic.retrievers`，属于 LangChain 经典 Retriever 集成模块。

### 8.3 parent_child_chunking.py
```python
from langchain_classic.retrievers import ParentDocumentRetriever

from langchain_core.documents import Document
from langchain_core.stores import InMemoryStore

from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from langchain_text_splitters import RecursiveCharacterTextSplitter


def main():
    embeddings = OllamaEmbeddings(
        model="qwen3-embedding:0.6b"
    )

    vector_store = InMemoryVectorStore(
        embedding=embeddings
    )

    docstore = InMemoryStore()

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=40,
    )

    retriever = ParentDocumentRetriever(
        vectorstore=vector_store,
        docstore=docstore,
        parent_splitter=parent_splitter,
        child_splitter=child_splitter,
    )

    documents = [
        Document(
            page_content=(
                "员工申请年假需要提前三个工作日提交申请。"
                "审批通过后才能休假。"
                "年假天数根据员工工龄及公司制度确定。"
            ),
            metadata={
                "source": "employee-handbook",
                "department": "HR",
            },
        )
    ]

    retriever.add_documents(documents)

    results = retriever.invoke(
        "年假需要提前多久申请？"
    )

    for document in results:
        print(document.page_content)
        print(document.metadata)


if __name__ == "__main__":
    main()
```

### 8.4 InMemoryStore 的限制
上面使用：

```plain
InMemoryStore()
```

仅用于演示。

应用重启后，Parent 文档数据可能丢失。

企业生产环境需要考虑：

+ Redis
+ PostgreSQL
+ 持久化 Docstore
+ Parent ID 与 Child ID 映射
+ 文档版本
+ 删除与更新同步

另外，Child Vector Store 与 Parent Docstore 必须保持数据一致。

---

## 九、Chunk Metadata 设计
企业 Chunk 不应该只有：

```python
{
    "source": "employee-handbook"
}
```

建议至少设计以下字段：

```python
metadata = {
    "tenant_id": "tenant_001",
    "knowledge_base_id": "kb_hr_001",
    "document_id": "doc_001",
    "document_version": "v1",
    "chunk_id": "doc_001_chunk_001",
    "source": "employee-handbook.pdf",
    "page": 3,
    "department": "HR",
    "category": "leave",
    "header_path": "员工手册/请假制度/年假",
}
```

Metadata 作用：

+ 数据隔离
+ 文档溯源
+ 权限过滤
+ 章节定位
+ 检索过滤
+ 文档更新
+ 版本管理
+ 引用来源
+ 审计

企业知识库中，Metadata 设计应在 Chunking 阶段统一完成。

---

## 十、企业级 Chunking Pipeline
推荐将文档切分流程设计为：

```plain
Document
   ↓
Document Loader
   ↓
Document Normalization
   ↓
Metadata Enrichment
   ↓
Structure-aware Chunking
   ↓
Recursive Chunking
   ↓
Chunk Validation
   ↓
Chunk ID Generation
   ↓
Embedding
   ↓
Vector Store
```

### 10.1 Chunk Validation
切分完成后，需要检查：

+ Chunk 是否为空
+ Chunk 是否超长
+ Chunk 是否重复
+ Chunk 是否丢失 Metadata
+ Chunk 是否包含乱码
+ Chunk 是否包含无意义页眉页脚
+ Chunk 是否保留章节信息
+ Chunk 是否满足 Embedding 模型输入限制

### 10.2 Chunk ID 设计
推荐：

```plain
document_id + document_version + chunk_index
```

例如：

```plain
doc_001_v1_chunk_001
doc_001_v1_chunk_002
doc_001_v1_chunk_003
```

不要简单使用随机 ID 作为唯一管理方案。

稳定 ID 更便于：

+ 幂等入库
+ 文档更新
+ 删除旧 Chunk
+ 数据对账
+ 版本管理

---

## 十一、Chunking 效果如何评估？
Chunking 不应该仅仅通过查看文本判断效果。

建议构建一组真实业务问题。

例如：

| 问题 | 预期答案 | 相关文档 |
| --- | --- | --- |
| 年假需要提前多久申请？ | 3 个工作日 | 请假制度 |
| 病假需要什么材料？ | 医院证明 | 请假制度 |
| 交通费用如何报销？ | 需要有效票据及审批 | 报销制度 |


对比不同 Chunking 配置：

```plain
方案 A：
Chunk Size = 300
Overlap = 50

方案 B：
Chunk Size = 500
Overlap = 80

方案 C：
Chunk Size = 800
Overlap = 100
```

评估：

+ Recall@K
+ Precision@K
+ MRR
+ Context Precision
+ Context Recall
+ Faithfulness
+ Answer Correctness

其中：

+ Recall@K：相关文档是否被检索出来
+ Precision@K：检索结果中相关文档占比
+ MRR：正确结果在排名中的位置
+ Context Precision：上下文是否足够精准
+ Context Recall：上下文是否覆盖回答需要的信息

这些指标会在第 44 章 RAG Evaluation 中进一步实战。

---

## 十二、企业级 Chunking 常见问题
### 问题 1：所有文档都使用相同 Chunk Size 吗？
不建议。

FAQ、PDF 制度、Markdown 技术文档、代码、合同、表格的结构不同。

建议：

+ FAQ：按问题和答案整体切分
+ Markdown：先按照标题切分
+ PDF：结合页码、标题、段落
+ 合同：按照条款编号切分
+ 表格：保持表头与数据关联
+ 技术文档：代码块与说明文字尽量保持结构

### 问题 2：Chunk Overlap 越大越好吗？
不是。

Overlap 过大容易导致：

+ 内容重复
+ 向量存储膨胀
+ 检索重复
+ 上下文冗余

需要结合实际检索效果调整。

### 问题 3：Chunk Size 是否必须按照 Token？
不一定。

RecursiveCharacterTextSplitter 默认按照字符长度切分。

如果业务对 Token 预算敏感，可以使用 TokenTextSplitter 或自定义 Token 长度函数。

### 问题 4：Chunking 可以完全依靠大模型吗？
可以使用大模型辅助语义切分，但不建议所有文档都依赖 LLM。

原因：

+ 切分成本
+ 处理速度
+ 输出稳定性
+ 数据一致性
+ 结构化结果校验

通常建议：

结构化规则切分 + 必要场景 LLM 辅助。

---

## 十三、本章实战验收
```plain
[ ] 理解 Chunk 的作用
[ ] 理解 Chunk Size
[ ] 理解 Chunk Overlap
[ ] 使用 RecursiveCharacterTextSplitter
[ ] 使用 TokenTextSplitter
[ ] 使用 MarkdownHeaderTextSplitter
[ ] 使用 ParentDocumentRetriever
[ ] 实现 Chunk Metadata
[ ] 实现 Chunk ID
[ ] 理解企业级 Chunking Pipeline
[ ] 能够设计 Chunking Evaluation
```

最终产出：

```plain
chunking-demo/
├── data/
│   └── employee-handbook.txt
├── chunking_demo.py
├── markdown_chunking.py
├── token_chunking.py
└── parent_child_chunking.py
```

---

## 十四、本章总结
本章核心：

```plain
Document
   ↓
Chunking
   ↓
Chunk
   ↓
Embedding
   ↓
Vector Database
```

Chunking 不是简单地将文档切成固定长度。

企业级 Chunking 的关键在于：

+ 保留语义完整性
+ 保留文档结构
+ 合理控制 Chunk Size
+ 合理设置 Overlap
+ 保留 Metadata
+ 支持 Parent-Child
+ 支持文档更新
+ 支持检索效果评估

### 官方参考文档
1. Recursive Character Text Splitter  
[https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
2. Markdown Header Text Splitter  
[https://reference.langchain.com/python/langchain-text-splitters/markdown](https://reference.langchain.com/python/langchain-text-splitters/markdown)
3. LangChain Text Splitters  
[https://reference.langchain.com/python/langchain-text-splitters](https://reference.langchain.com/python/langchain-text-splitters)
4. ParentDocumentRetriever  
[https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever)

** **
