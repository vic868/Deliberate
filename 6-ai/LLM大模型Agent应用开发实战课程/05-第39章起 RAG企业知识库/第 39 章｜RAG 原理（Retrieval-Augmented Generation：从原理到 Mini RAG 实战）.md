**核心技术：** RAG、LangChain、Document、Retriever、Embedding、Vector Store、Chat Model、Prompt Engineering、Mini RAG

**课程定位：** 从零理解 RAG 的整体架构、核心原理与企业应用价值，使用 LangChain 完成一个可运行的 Mini RAG 项目，为后续企业知识库、Advanced Retrieval、RAG Evaluation 等章节打下基础。

---

## 一、本章学习目标
很多开发者学习 AI Agent 时，都会遇到一个问题：

为什么大模型能够回答一些企业内部问题？

例如：

```plain
用户：

我们公司年假申请需要提前多久？
```

DeepSeek 等大模型本身并不知道企业内部最新的年假制度。

如果直接调用大模型：

```plain
response = llm.invoke(
    "我们公司年假申请需要提前多久？"
)
```

模型可能：

+ 不知道答案
+ 根据常见经验猜测
+ 输出错误信息
+ 生成看起来合理但实际错误的回答

企业系统不能接受这种结果。

因此，需要让大模型在回答问题之前，先检索企业知识库中的相关资料。

这就是 RAG。

本章重点掌握：

1. RAG 是什么？
2. 为什么企业 AI 应用需要 RAG？
3. RAG 与普通 LLM 调用有什么区别？
4. RAG 的完整架构是什么？
5. RAG 的离线索引流程是什么？
6. RAG 的在线检索流程是什么？
7. Embedding、Vector Database、Retriever 分别是什么？
8. 如何使用 LangChain 实现 Mini RAG？
9. 如何实现知识库问答？
10. 如何理解 RAG 的局限性？

---

## 二、RAG 是什么？
RAG 全称：

```plain
Retrieval-Augmented Generation
```

中文：

```plain
检索增强生成
```

它是一种将外部知识检索与大语言模型生成结合起来的技术架构。

核心思想：

**在大模型回答问题之前，先从外部知识库中检索相关信息，再将检索结果作为上下文提供给大模型，让大模型基于这些资料生成答案。**

例如：

```plain
用户：

公司年假申请需要提前多久？
```

RAG 系统：

```plain
第一步：

从企业知识库检索相关资料。

第二步：

找到年假制度。

第三步：

将年假制度作为上下文提供给大模型。

第四步：

大模型根据企业制度回答。
```

最终：

```plain
根据公司年假制度，员工申请年假需要提前三个工作日提交申请，审批通过后才能休假。
```

注意：

这里的回答来自企业知识库，而不是大模型凭借训练数据自行猜测。

---

## 三、为什么企业 AI 应用需要 RAG？
### 3.1 大模型存在知识边界
大模型的知识主要来自训练数据以及模型训练后的知识表达。

但是企业内部的数据通常具有以下特点：

+ 私有化
+ 实时变化
+ 企业内部专有
+ 业务规则复杂
+ 不对外公开
+ 需要权限控制

例如：

```plain
企业内部：

员工薪资制度
客户信息
产品报价
业务流程
项目文档
内部技术规范
售后处理方案
```

这些信息不一定存在于大模型的训练数据中。

因此，不能仅仅依赖大模型自身知识。

### 3.2 RAG 解决什么问题？
RAG 可以帮助企业 AI 应用：

| 问题 | RAG 的作用 |
| --- | --- |
| 大模型不了解企业内部知识 | 检索企业知识库 |
| 企业制度经常更新 | 更新外部知识库，不必重新训练模型 |
| 大模型容易编造信息 | 提供相关资料，降低无依据回答 |
| 回答需要来源 | 保留检索文档及其 Metadata |
| 企业知识规模大 | 使用向量检索等方式快速定位相关内容 |
| 不同部门知识不同 | 结合 Metadata Filter 与权限控制 |


需要注意：

RAG 不能保证大模型绝对不产生幻觉。

即使检索到了正确资料，模型仍然可能理解错误、遗漏条件或错误总结。

因此，企业级 RAG 还需要：

+ Retrieval Evaluation
+ Answer Evaluation
+ Prompt 约束
+ 引用来源
+ 权限过滤
+ 业务验证

这些内容会在后续章节展开。

---

## 四、RAG 与普通 LLM 调用的区别
### 4.1 普通 LLM 调用
```plain
用户问题
   ↓
Chat Model
   ↓
生成答案
```

代码：

```plain
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-chat",
)

response = llm.invoke(
    "公司年假需要提前多久申请？"
)

print(response.content)
```

这种方式没有接入企业知识库。

### 4.2 RAG 调用
```plain
用户问题
   ↓
Retriever
   ↓
企业知识库
   ↓
相关文档
   ↓
Prompt + Context + Question
   ↓
Chat Model
   ↓
最终答案
```

核心区别：

```plain
普通 LLM：

Question → LLM → Answer

RAG：

Question → Retrieval → Context → LLM → Answer
```

RAG 的关键不是更换大模型，而是：

**为大模型增加外部知识检索能力。**

---

## 五、RAG 的整体架构
RAG 通常分为两个阶段：

1. Offline Indexing：离线知识索引
2. Online Retrieval & Generation：在线检索与生成

### 5.1 离线索引流程
离线流程主要负责将企业文档转换为可检索的知识库。

```plain
企业文档
   ↓
Document Loader
   ↓
Document Parsing
   ↓
Document Cleaning
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Database
```

例如：

```plain
employee-handbook.pdf
       ↓
PDF Loader
       ↓
Document
       ↓
Chunking
       ↓
Chunk 1
Chunk 2
Chunk 3
       ↓
Embedding Model
       ↓
Vector
       ↓
PostgreSQL + pgvector
```

这里需要注意：

离线并不意味着一定不能实时处理。

企业可以在文档上传后触发后台索引任务。

所谓离线索引，是指知识索引构建与用户在线问答请求分离。

### 5.2 在线检索与生成流程
```plain
用户问题
   ↓
Query Embedding
   ↓
Vector Search
   ↓
Top-K Documents
   ↓
Context Assembly
   ↓
Prompt
   ↓
Chat Model
   ↓
Answer
```

例如：

```plain
用户：

年假需要提前多久申请？
```

Retriever 检索到：

```plain
员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
```

然后构造 Prompt：

```plain
你是企业 HR 助手。

请根据以下企业制度回答问题。

上下文：
员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。

问题：
年假需要提前多久申请？
```

最终模型回答：

```plain
根据公司制度，年假需要提前三个工作日提交申请，并且审批通过后才能休假。
```

---

## 六、RAG 的核心组件
### 6.1 Document Loader
负责将不同格式的数据加载为统一的 Document。

例如：

```plain
PDF
Word
Excel
Markdown
HTML
TXT
```

统一转换为：

```plain
Document(
    page_content="...",
    metadata={...},
)
```

对应第 40 章。

### 6.2 Text Splitter
负责将较长文档切分成多个 Chunk。

例如：

```plain
原始文档
   ↓
Chunk 1
Chunk 2
Chunk 3
```

对应第 41 章。

### 6.3 Embedding Model
负责将文本转换为向量。

例如：

```plain
文本：

年假需要提前三个工作日申请。

↓

Embedding：

[0.12, -0.32, 0.51, ...]
```

对应第 42 章。

### 6.4 Vector Database
负责存储：

+ Embedding Vector
+ Chunk Text
+ Metadata

并提供相似度检索能力。

例如：

```plain
PostgreSQL + pgvector
Qdrant
Milvus
Chroma
```

对应第 42 章。

### 6.5 Retriever
Retriever 负责根据用户问题，从知识库中获取相关文档。

例如：

```plain
documents = retriever.invoke(
    "年假需要提前多久申请？"
)
```

返回：

```plain
[
    Document(
        page_content="员工申请年假需要提前三个工作日...",
        metadata={...},
    )
]
```

Retriever 的职责是检索，而不是生成最终答案。

### 6.6 Chat Model
负责根据：

+ 用户问题
+ 检索上下文
+ System Prompt
+ 业务约束

生成最终回答。

例如：

```plain
llm.invoke(prompt)
```

---

## 七、Mini RAG 实战：从零实现企业知识库问答
本节完成一个完整的 Mini RAG 项目。

项目特点：

+ 使用 LangChain
+ 使用 Ollama 本地 Embedding
+ 使用 DeepSeek Chat API
+ 使用 InMemoryVectorStore
+ 不依赖独立向量数据库
+ 支持文档入库
+ 支持语义检索
+ 支持上下文组装
+ 支持大模型回答

注意：

本章使用 InMemoryVectorStore 作为教学演示。

第 42 章已经实现 PostgreSQL + pgvector。

后续企业项目可以将本章的 InMemoryVectorStore 替换为 PGVectorStore。

### 7.1 项目初始化
```plain
uv init mini-rag-demo --python 3.12

cd mini-rag-demo

uv add langchain-core langchain-ollama langchain-openai langchain-text-splitters python-dotenv
```

项目结构：

```plain
mini-rag-demo/
├── .env
├── pyproject.toml
├── data/
│   └── employee-handbook.txt
├── knowledge_loader.py
├── vector_store.py
├── retriever.py
├── rag_chain.py
└── main.py
```

### 7.2 配置文件
创建 `.env`：

```plain
# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Chat Model
CHAT_MODEL=deepseek-chat

# Embedding
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

安装 Ollama：

[https://ollama.com](https://ollama.com/)

下载模型：

```plain
ollama pull qwen3-embedding:0.6b
```

### 7.3 准备知识库文档
创建 `data/employee-handbook.txt`：

```plain
员工年假制度：

员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
年假天数根据员工工龄以及公司制度确定。

员工病假制度：

员工申请病假需要提交医院相关证明。
病假申请需要按照公司规定完成审批。

员工报销制度：

员工出差产生的交通费用可以申请报销。
报销需要提供合法有效的票据。
报销申请需要经过直属领导审批。

企业研发制度：

研发项目需要按照公司研发流程进行管理。
代码提交需要经过 Code Review。
生产环境发布需要经过测试和审批。
```

---

## 八、Document Loader：知识文档加载
创建 `knowledge_loader.py`：

```python
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_knowledge_documents():
    file_path = Path(
        "data/employee-handbook.txt"
    )

    text = file_path.read_text(
        encoding="utf-8"
    )

    document = Document(
        page_content=text,
        metadata={
            "source": file_path.name,
            "document_id": "employee-handbook",
            "category": "company-policy",
        },
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
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

    chunks = splitter.split_documents(
        [document]
    )

    print(f"原始文档长度：{len(text)}")
    print(f"Chunk 数量：{len(chunks)}")

    return chunks
```

这里使用：

```plain
RecursiveCharacterTextSplitter
```

完成文档切分。

具体切分策略在第 41 章详细讲解。

---

## 九、Vector Store：构建向量知识库
创建 `vector_store.py`：

```python
from langchain_ollama import OllamaEmbeddings

from langchain_core.vectorstores import InMemoryVectorStore

from knowledge_loader import load_knowledge_documents


def build_vector_store():
    # 1. 创建 Embedding Model
    embeddings = OllamaEmbeddings(
        model="qwen3-embedding:0.6b",
        base_url="http://localhost:11434",
    )

    # 2. 创建 Vector Store
    vector_store = InMemoryVectorStore(
        embedding=embeddings
    )

    # 3. 加载文档
    documents = load_knowledge_documents()

    # 4. 文档向量入库
    vector_store.add_documents(
        documents=documents
    )

    print(
        f"成功构建知识库，文档数量：{len(documents)}"
    )

    return vector_store
```

这里执行：

```plain
vector_store.add_documents(
    documents=documents
)
```

LangChain 会完成：

```plain
Document
   ↓
Embedding
   ↓
Vector
   ↓
Vector Store
```

不需要开发者自己计算向量。

---

## 十、Retriever：实现知识检索
创建 `retriever.py`：

```python
from vector_store import build_vector_store


def build_retriever():
    vector_store = build_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 3,
        }
    )

    return retriever


if __name__ == "__main__":
    retriever = build_retriever()

    results = retriever.invoke(
        "员工申请年假需要提前多久？"
    )

    for document in results:
        print(document.page_content)
        print(document.metadata)
```

执行：

```plain
uv run python retriever.py
```

预期检索到：

```plain
员工年假制度：

员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
年假天数根据员工工龄以及公司制度确定。
```

Retriever 的作用：

```plain
Query
   ↓
Query Embedding
   ↓
Vector Search
   ↓
Top-K Documents
```

---

## 十一、RAG Chain：构建问答流程
前面已经实现：

+ 文档加载
+ 文档切分
+ 向量化
+ 向量检索

现在将 Retriever 与 Chat Model 结合起来。

创建 `rag_chain.py`：

```python
import os

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from retriever import build_retriever


load_dotenv()


def build_rag_chain():
    # 1. 创建 Chat Model
    llm = ChatOpenAI(
        model=os.getenv(
            "CHAT_MODEL",
            "deepseek-chat",
        ),
        api_key=os.getenv(
            "DEEPSEEK_API_KEY",
        ),
        base_url=os.getenv(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        ),
        temperature=0,
    )

    # 2. 创建 Retriever
    retriever = build_retriever()

    # 3. 定义 Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
你是企业内部知识库助手。

请严格根据提供的上下文回答问题。

如果上下文没有相关信息，请明确回答：
“知识库中没有找到相关信息。”

不要编造企业制度、业务规则或数据。

上下文：
{context}
""",
            ),
            (
                "human",
                "{question}",
            ),
        ]
    )

    # 4. 构建 RAG 执行函数
    def invoke(question: str):
        # 检索文档
        documents = retriever.invoke(
            question
        )

        # 构建 Context
        context = "\n\n".join(
            document.page_content
            for document in documents
        )

        # 构建 Prompt
        messages = prompt.format_messages(
            question=question,
            context=context,
        )

        # 调用 LLM
        response = llm.invoke(
            messages
        )

        return {
            "question": question,
            "answer": response.content,
            "context": context,
            "documents": documents,
        }

    return invoke
```

这里使用 LangChain 的：

```plain
ChatPromptTemplate
```

负责构建 Prompt。

使用：

```plain
ChatOpenAI
```

接入 DeepSeek 兼容 OpenAI API 协议的 Chat Model。

注意：

本章将 RAG 的检索和生成过程显式拆开，方便理解执行链路。

后续章节会进一步使用 LangChain、LangGraph 构建更加完整的 RAG Chain 和 Agentic RAG。

---

## 十二、运行 Mini RAG
创建 `main.py`：

```python
from rag_chain import build_rag_chain


def main():
    rag = build_rag_chain()

    while True:
        question = input(
            "\n请输入问题（输入 exit 退出）："
        )

        if question.lower() == "exit":
            break

        result = rag(question)

        print("\n===== 回答 =====")
        print(result["answer"])

        print("\n===== 检索上下文 =====")
        print(result["context"])

        print("\n===== 来源 =====")

        for document in result["documents"]:
            print(document.metadata)


if __name__ == "__main__":
    main()
```

运行：

```plain
uv run python main.py
```

输入：

```plain
请输入问题：

员工申请年假需要提前多久？
```

输出：

```plain
===== 回答 =====

根据公司年假制度，员工申请年假需要提前三个工作日提交申请，并且审批通过后才能休假。

===== 检索上下文 =====

员工年假制度：

员工申请年假需要提前三个工作日提交申请。
审批通过后才能休假。
年假天数根据员工工龄以及公司制度确定。

===== 来源 =====

{
    'source': 'employee-handbook.txt',
    'document_id': 'employee-handbook',
    'category': 'company-policy'
}
```

至此，一个完整的 Mini RAG 已经实现。

---

## 十三、Mini RAG 的完整执行流程
```plain
离线索引
                │
                ▼
       employee-handbook.txt
                │
                ▼
        Document Loader
                │
                ▼
        Recursive Splitter
                │
                ▼
             Chunks
                │
                ▼
       Ollama Embedding
                │
                ▼
       InMemoryVectorStore
                │
                │
════════════════════════════
          在线问答
════════════════════════════
                │
                ▼
           Question
                │
                ▼
           Retriever
                │
                ▼
         Vector Search
                │
                ▼
          Top-K Context
                │
                ▼
       ChatPromptTemplate
                │
                ▼
         DeepSeek Chat
                │
                ▼
          Final Answer
```

本章实现的是一个最基础的 RAG Pipeline。

后续可以逐步扩展：

```plain
Mini RAG
   ↓
企业 RAG
   ↓
Advanced Retrieval
   ↓
Agentic RAG
   ↓
Enterprise Knowledge Agent
```

---

## 十四、RAG 的常见问题
### 14.1 为什么检索到了正确文档，回答仍然错误？
可能原因：

+ Context 不完整
+ Chunk 切分不合理
+ Top-K 太小
+ Top-K 太大导致噪声
+ Prompt 不明确
+ 模型没有正确使用上下文
+ 多条文档存在冲突
+ 文档本身过期

解决思路：

```plain
Retrieval Evaluation
        ↓
Chunking Optimization
        ↓
Context Optimization
        ↓
Prompt Optimization
        ↓
Answer Evaluation
```

### 14.2 为什么 RAG 不等于向量数据库？
RAG 是一种整体架构。

向量数据库只是 RAG 中的一种存储与检索组件。

完整 RAG 包含：

+ Document Loader
+ Text Splitter
+ Embedding Model
+ Vector Store
+ Retriever
+ Prompt
+ Chat Model

### 14.3 RAG 是否必须使用向量数据库？
不一定。

RAG 的核心是检索增强生成。

检索可以使用：

+ 向量检索
+ 关键词检索
+ BM25
+ SQL 查询
+ 搜索引擎
+ 企业 API
+ 混合检索

企业场景中通常会结合多种检索方式。

### 14.4 RAG 是否可以解决大模型幻觉？
RAG 可以降低模型缺乏知识依据导致的错误回答，但不能完全消除幻觉。

企业系统仍然需要：

+ 证据约束
+ 来源引用
+ 置信度策略
+ 评测
+ 人工审核
+ 业务规则校验

---

## 十五、RAG 与 Agent 的关系
RAG 和 Agent 不是同一个概念。

RAG 主要解决：

```plain
如何让大模型获取外部知识？
```

Agent 主要解决：

```plain
如何让大模型根据目标进行推理、决策并调用工具？
```

简单 RAG：

```plain
用户问题
   ↓
Retriever
   ↓
LLM
   ↓
Answer
```

Agentic RAG：

```plain
用户问题
   ↓
Agent
   ↓
判断是否需要检索
   ↓
选择检索工具
   ↓
执行 Retrieval
   ↓
判断检索结果
   ↓
必要时重新检索
   ↓
生成答案
```

企业项目中：

+ FAQ 问答可以使用普通 RAG
+ 企业知识助手可以使用 RAG + Workflow
+ 多步骤研究任务可以使用 Agentic RAG
+ 涉及审批、业务执行时，需要结合工具调用与权限控制

不是所有 RAG 都需要 Agent。

---

## 十六、本章实战验收
```plain
[ ] 理解 RAG 原理
[ ] 理解 RAG 与普通 LLM 的区别
[ ] 理解 RAG 离线索引流程
[ ] 理解 RAG 在线检索流程
[ ] 理解 Document Loader
[ ] 理解 Chunking
[ ] 理解 Embedding
[ ] 理解 Vector Store
[ ] 理解 Retriever
[ ] 使用 LangChain 构建 Mini RAG
[ ] 使用 Ollama Embedding
[ ] 使用 DeepSeek Chat
[ ] 实现 Context Assembly
[ ] 实现知识库问答
[ ] 实现无知识时的拒答
```

最终项目：

```plain
mini-rag-demo/
├── .env
├── pyproject.toml
├── data/
│   └── employee-handbook.txt
├── knowledge_loader.py
├── vector_store.py
├── retriever.py
├── rag_chain.py
└── main.py
```

---

## 十七、本章总结
本章核心：

```plain
RAG = Retrieval + Augmented Context + Generation
```

完整流程：

```plain
企业文档
   ↓
Document Loader
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Store
   ↓
Retriever
   ↓
Context
   ↓
LLM
   ↓
Answer
```

需要牢记：

+ RAG 是一种应用架构，不是一个模型。
+ Embedding 负责将文本转换为向量。
+ Vector Database 负责存储和检索向量。
+ Retriever 负责获取相关知识。
+ Chat Model 负责根据上下文生成答案。
+ Chunking 会影响检索效果。
+ RAG 不保证绝对消除幻觉。
+ 企业级 RAG 需要评测、权限、数据更新及监控。

### 官方参考文档
1. LangChain RAG 教程  
[https://docs.langchain.com/oss/python/langchain/rag](https://docs.langchain.com/oss/python/langchain/rag)
2. LangChain Document Loaders  
[https://docs.langchain.com/oss/python/integrations/document_loaders](https://docs.langchain.com/oss/python/integrations/document_loaders)
3. LangChain Text Splitters  
[https://docs.langchain.com/oss/python/integrations/splitters](https://docs.langchain.com/oss/python/integrations/splitters)
4. LangChain Embeddings  
[https://docs.langchain.com/oss/python/integrations/embeddings](https://docs.langchain.com/oss/python/integrations/embeddings)
5. LangChain Vector Stores  
[https://docs.langchain.com/oss/python/integrations/vectorstores](https://docs.langchain.com/oss/python/integrations/vectorstores)

---

 
