---

# 一、本章定位
上一章我们完成了：

```plain
第 40 章｜企业文档解析
```

第 40 章的核心产物是：

```plain
ParsedDocument
ParsedElement
ParseStatus
DocumentParsingService
```

这一章继续往下走：

```plain
ParsedDocument
 ↓
Chunk 文档切分
 ↓
ChunkDocument
```

也就是说：

```plain
第 40 章解决“文件怎么读出来”
第 41 章解决“读出来的内容怎么切成适合检索的片段”
```

---

# 二、本章学习目标
学完这一章以后，学员需要掌握：

```plain
1. Chunk 是什么
2. 为什么 RAG 必须做 Chunk
3. Chunk 切得太大有什么问题
4. Chunk 切得太小有什么问题
5. chunk_size 怎么选
6. chunk_overlap 怎么选
7. 按字符切分怎么做
8. 按段落切分怎么做
9. 按页切分怎么做
10. 按标题结构切分怎么做
11. Markdown Header 切分怎么做
12. 表格 Chunk 怎么处理
13. 代码文档 Chunk 怎么处理
14. Chunk metadata 应该保存哪些字段
15. Chunk 和原文来源怎么关联
16. Chunk 如何支持权限过滤
17. Chunk 如何支持版本过滤
18. 如何封装 ChunkingService
19. 如何接入第 40 章 ParsedDocument
20. 如何为第 42 章 Embedding 做准备
21. 面试中如何讲 Chunk 切分
```

---

# 三、Chunk 一句话解释
## 【实操】
```plain
Chunk
=
文档被切分后的一个可检索片段。
```

更口语一点：

```plain
把一整份文档，切成一块一块适合搜索和喂给大模型的小内容。
```

---

## 【重点内容】
大家先记住一句话：

Chunk 是 RAG 的最小检索单元。

比如一份员工手册有 100 页。

用户问：

```plain
年假怎么申请？
```

我们不可能把 100 页都塞给大模型。

应该只召回和“年假申请”相关的几个 Chunk。

所以 RAG 的核心不是：

```plain
文档入库
```

而是：

```plain
文档切成什么样的检索单元。
```

Chunk 切得好，后面的召回才有基础。

Chunk 切得差，Embedding 和向量库再好也很难救。

---

# 四、为什么必须切 Chunk
大文档直接入向量库会有几个问题：

```plain
1. 文档太长，向量表达不精确
2. 用户问题通常只对应文档的一小段
3. 大文档召回后无法放进模型上下文
4. 答案来源不够精确
5. 检索粒度太粗
6. 无法按页码、标题、段落定位
```

举个例子：

```plain
员工手册 100 页
```

如果整本书作为一个向量：

```plain
用户问年假
用户问报销
用户问考勤
用户问离职
```

这些问题都可能召回同一个“大文档”。

模型拿到一大坨内容，很难准确定位。

所以要切成：

```plain
考勤制度 Chunk
年假制度 Chunk
报销制度 Chunk
离职流程 Chunk
```

LangChain Text Splitters 文档也说明，大文档需要被拆成可单独检索、且能放入模型上下文窗口的小片段。

---

# 五、Chunk 切得太大的问题
Chunk 太大：

```plain
1. 一个 Chunk 混入多个主题
2. 向量语义变模糊
3. 召回结果不够精准
4. Prompt 里噪音变多
5. token 成本变高
6. 来源引用不够精确
```

例子：

```plain
一个 Chunk 里同时包含：
考勤制度
年假制度
报销制度
离职流程
```

用户问：

```plain
报销需要什么材料？
```

召回这个 Chunk 以后，模型还要在里面找报销内容。

如果上下文很长，模型可能被年假或离职内容干扰。

---

# 六、Chunk 切得太小的问题
Chunk 太小：

```plain
1. 语义不完整
2. 上下文被切断
3. 召回到片段但缺前后解释
4. 表格行列关系丢失
5. 标题和正文分离
6. 需要召回更多 Chunk 才能回答
```

例子：

```plain
Chunk 1：订单未发货时
Chunk 2：用户可以申请取消订单并退款
```

用户问：

```plain
没发货可以退款吗？
```

如果只召回 Chunk 1，它根本不能完整回答。

所以 Chunk 不是越小越好。

---

# 七、chunk_size 和 chunk_overlap
两个核心参数：

```plain
chunk_size：
每个 Chunk 的目标长度。

chunk_overlap：
相邻 Chunk 之间保留多少重叠内容。
```

比如：

```python
chunk_size = 500
chunk_overlap = 80
```

表示：

```plain
每个 Chunk 大约 500 字符；
相邻 Chunk 之间重叠 80 字符。
```

LangChain 的 RecursiveCharacterTextSplitter 支持 `chunk_size` 和 `chunk_overlap`，并通过一组 separators 递归尝试按自然边界切分文本。

---

## 【重点内容】
为什么需要 overlap？

因为一个完整信息可能跨在两个 Chunk 之间。

适当 overlap 可以减少信息断裂。

但是 overlap 不能太大。

太大会导致：

```plain
重复内容太多
向量库膨胀
召回结果重复
Embedding 成本增加
```

所以这两个参数一定要结合业务文档来调。

---

# 八、Chunk 参数怎么选
没有万能参数。

常见参考：

```plain
FAQ / 短问答：
chunk_size 200～400 字符

制度文档：
chunk_size 500～1000 字符

技术文档：
chunk_size 800～1500 字符

表格文档：
按表格或行组切，不建议硬切字符

代码文档：
按函数、类、模块切
```

---

## 【重点内容】
这里不要给学生一个死答案。

比如：

```plain
chunk_size=500 永远最好
```

这是不对的。

Chunk 参数要靠：

```plain
文档类型
问题类型
Embedding 模型
模型上下文窗口
TopK
Rerank
评估集
```

综合调整。

企业项目里一定要做评估。

比如准备 100 个真实问题，看不同 chunk_size 下召回是否命中正确片段。

---

# 九、常见切分策略
这一章实现 7 种切分策略：

```plain
1. FixedSizeChunker：固定长度切分
2. ParagraphChunker：按段落切分
3. PageChunker：按页切分
4. ElementChunker：按 ParsedElement 切分
5. HeadingChunker：按标题结构切分
6. TableAwareChunker：表格感知切分
7. CodeAwareChunker：代码感知切分
```

后面也会补一个 LangChain 版本：

```plain
RecursiveCharacterTextSplitter
MarkdownHeaderTextSplitter
PythonCodeTextSplitter
```

LangChain text splitters 里也提供了 Markdown Header、HTML Header、Python Code、Recursive Character、Token 等多种切分器。

---

# 十、本章项目结构
新增目录：

```plain
ai-agent-course/
├── app/
│   ├── document_chunking/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── chunkers.py
│   │   ├── chunker_factory.py
│   │   ├── service.py
│   │   ├── langchain_examples.py
│   │   ├── demo_01_fixed_size_chunk.py
│   │   ├── demo_02_paragraph_chunk.py
│   │   ├── demo_03_element_chunk.py
│   │   ├── demo_04_heading_chunk.py
│   │   ├── demo_05_table_chunk.py
│   │   ├── demo_06_code_chunk.py
│   │   └── demo_07_parse_and_chunk.py
│   │
│   ├── api/
│   │   └── v1/
│   │       └── document_chunking.py
│   │
│   └── ...
│
├── scripts/
│   ├── test_chunk41_01_fixed_size.py
│   ├── test_chunk41_02_paragraph.py
│   ├── test_chunk41_03_element.py
│   ├── test_chunk41_04_heading.py
│   ├── test_chunk41_05_table.py
│   ├── test_chunk41_06_code.py
│   └── test_chunk41_07_parse_and_chunk.py
│
└── README.md
```

---

# 十一、安装依赖
基础代码不强依赖 LangChain。

如果要跑 LangChain 示例，安装：

```bash
uv add langchain-text-splitters
```

LangChain 文档里当前推荐从 `langchain_text_splitters` 导入切分器，例如 `RecursiveCharacterTextSplitter`。

---

# 十二、创建目录和文件
执行：

```bash
mkdir -p app/document_chunking

touch app/document_chunking/__init__.py
touch app/document_chunking/schemas.py
touch app/document_chunking/chunkers.py
touch app/document_chunking/chunker_factory.py
touch app/document_chunking/service.py
touch app/document_chunking/langchain_examples.py
touch app/document_chunking/demo_01_fixed_size_chunk.py
touch app/document_chunking/demo_02_paragraph_chunk.py
touch app/document_chunking/demo_03_element_chunk.py
touch app/document_chunking/demo_04_heading_chunk.py
touch app/document_chunking/demo_05_table_chunk.py
touch app/document_chunking/demo_06_code_chunk.py
touch app/document_chunking/demo_07_parse_and_chunk.py

touch app/api/v1/document_chunking.py

touch scripts/test_chunk41_01_fixed_size.py
touch scripts/test_chunk41_02_paragraph.py
touch scripts/test_chunk41_03_element.py
touch scripts/test_chunk41_04_heading.py
touch scripts/test_chunk41_05_table.py
touch scripts/test_chunk41_06_code.py
touch scripts/test_chunk41_07_parse_and_chunk.py
```

Windows PowerShell：

```powershell
mkdir app\document_chunking

New-Item app\document_chunking\__init__.py
New-Item app\document_chunking\schemas.py
New-Item app\document_chunking\chunkers.py
New-Item app\document_chunking\chunker_factory.py
New-Item app\document_chunking\service.py
New-Item app\document_chunking\langchain_examples.py
New-Item app\document_chunking\demo_01_fixed_size_chunk.py
New-Item app\document_chunking\demo_02_paragraph_chunk.py
New-Item app\document_chunking\demo_03_element_chunk.py
New-Item app\document_chunking\demo_04_heading_chunk.py
New-Item app\document_chunking\demo_05_table_chunk.py
New-Item app\document_chunking\demo_06_code_chunk.py
New-Item app\document_chunking\demo_07_parse_and_chunk.py
```

---

# 十三、定义 Chunk Schema
打开：

```plain
app/document_chunking/schemas.py
```

写入：

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.document_parsing.schemas import ParsedDocument


class ChunkStrategy(str, Enum):
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    PAGE = "page"
    ELEMENT = "element"
    HEADING = "heading"
    TABLE_AWARE = "table_aware"
    CODE_AWARE = "code_aware"


@dataclass
class ChunkConfig:
    strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH
    chunk_size: int = 500
    chunk_overlap: int = 80
    min_chunk_size: int = 30
    preserve_metadata: bool = True


@dataclass
class ChunkDocument:
    chunk_id: str
    document_id: str
    title: str
    content: str
    chunk_index: int
    strategy: ChunkStrategy
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkResult:
    document_id: str
    title: str
    total_chunks: int
    strategy: ChunkStrategy
    chunks: list[ChunkDocument]
    warnings: list[str] = field(default_factory=list)


@dataclass
class ChunkRequest:
    parsed_document: ParsedDocument
    config: ChunkConfig
```

---

## 【重点内容】
这里定义了四个对象。

第一个：

```plain
ChunkStrategy
```

表示切分策略。

第二个：

```plain
ChunkConfig
```

表示切分配置，比如 chunk_size 和 chunk_overlap。

第三个：

```plain
ChunkDocument
```

表示最终切出来的一个 Chunk。

第四个：

```plain
ChunkResult
```

表示整份文档的切分结果。

注意 `ChunkDocument.metadata` 很重要。

它后面要用于：

```plain
来源引用
权限过滤
版本过滤
页码定位
文档追踪
```

---

# 十四、实现 Chunker 基类
打开：

```plain
app/document_chunking/chunkers.py
```

先写入：

```python
import re
from abc import ABC, abstractmethod

from app.document_chunking.schemas import (
    ChunkConfig,
    ChunkDocument,
    ChunkResult,
    ChunkStrategy,
)
from app.document_parsing.schemas import (
    ParsedDocument,
    ParsedElement,
    ParsedElementType,
)


class BaseChunker(ABC):
    def __init__(
        self,
        config: ChunkConfig,
    ):
        if config.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")

        if config.chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")

        if config.chunk_overlap >= config.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

        self.config = config

    @abstractmethod
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        raise NotImplementedError

    def build_chunk_id(
        self,
        document_id: str,
        chunk_index: int,
    ) -> str:
        return f"{document_id}_chunk_{chunk_index}"

    def build_base_metadata(
        self,
        document: ParsedDocument,
        chunk_index: int,
    ) -> dict:
        metadata = {
            **document.metadata,
            "document_id": document.document_id,
            "document_title": document.title,
            "file_name": document.file_name,
            "file_type": document.file_type,
            "source_path": document.source_path,
            "chunk_index": chunk_index,
        }

        return metadata

    def create_chunk(
        self,
        document: ParsedDocument,
        content: str,
        chunk_index: int,
        strategy: ChunkStrategy,
        extra_metadata: dict | None = None,
    ) -> ChunkDocument:
        metadata = self.build_base_metadata(
            document=document,
            chunk_index=chunk_index,
        )

        if extra_metadata:
            metadata.update(extra_metadata)

        return ChunkDocument(
            chunk_id=self.build_chunk_id(
                document.document_id,
                chunk_index,
            ),
            document_id=document.document_id,
            title=document.title,
            content=content.strip(),
            chunk_index=chunk_index,
            strategy=strategy,
            metadata=metadata,
        )

    def should_keep_chunk(
        self,
        content: str,
    ) -> bool:
        return len(content.strip()) >= self.config.min_chunk_size
```

---

# 十五、实现 FixedSizeChunker
继续在：

```plain
app/document_chunking/chunkers.py
```

追加：

```python
class FixedSizeChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        text = document.text
        chunks: list[ChunkDocument] = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.config.chunk_size
            content = text[start:end]

            if self.should_keep_chunk(content):
                chunks.append(
                    self.create_chunk(
                        document=document,
                        content=content,
                        chunk_index=chunk_index,
                        strategy=ChunkStrategy.FIXED_SIZE,
                        extra_metadata={
                            "start_char": start,
                            "end_char": min(end, len(text)),
                        },
                    )
                )
                chunk_index += 1

            if end >= len(text):
                break

            start = end - self.config.chunk_overlap

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.FIXED_SIZE,
            chunks=chunks,
            warnings=[
                "FixedSizeChunker 只适合教学或兜底，不建议作为企业默认策略。"
            ],
        )
```

---

## 【重点内容】
固定长度切分最简单。

但是它的问题也最大。

它不理解标题、段落、表格、语义。

所以真实项目里，它适合当兜底方案，而不是默认方案。

比如解析后的文本没有结构，才考虑固定长度切。

---

# 十六、实现 ParagraphChunker
继续追加：

```python
class ParagraphChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", document.text)
            if paragraph.strip()
        ]

        chunks: list[ChunkDocument] = []
        current_parts: list[str] = []
        current_size = 0
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph_size = len(paragraph)

            if current_parts and current_size + paragraph_size > self.config.chunk_size:
                content = "\n\n".join(current_parts)

                if self.should_keep_chunk(content):
                    chunks.append(
                        self.create_chunk(
                            document=document,
                            content=content,
                            chunk_index=chunk_index,
                            strategy=ChunkStrategy.PARAGRAPH,
                            extra_metadata={
                                "paragraph_count": len(current_parts),
                            },
                        )
                    )
                    chunk_index += 1

                # 简单 overlap：保留最后一个段落作为上下文。
                if self.config.chunk_overlap > 0 and current_parts:
                    current_parts = [current_parts[-1]]
                    current_size = len(current_parts[-1])
                else:
                    current_parts = []
                    current_size = 0

            current_parts.append(paragraph)
            current_size += paragraph_size

        if current_parts:
            content = "\n\n".join(current_parts)

            if self.should_keep_chunk(content):
                chunks.append(
                    self.create_chunk(
                        document=document,
                        content=content,
                        chunk_index=chunk_index,
                        strategy=ChunkStrategy.PARAGRAPH,
                        extra_metadata={
                            "paragraph_count": len(current_parts),
                        },
                    )
                )

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.PARAGRAPH,
            chunks=chunks,
        )
```

---

## 【重点内容】
段落切分比固定长度更自然。

它尽量不打断段落。

适合：

```plain
制度文档
FAQ 文档
普通说明文档
售后规则
员工手册
```

但是它也有问题。

如果某个段落特别长，还是可能超过 chunk_size。

所以生产环境通常会组合：

```plain
先按结构切
再对过长块做递归切分
```

---

# 十七、实现 PageChunker
继续追加：

```python
class PageChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        chunks: list[ChunkDocument] = []
        chunk_index = 0

        page_elements = [
            element for element in document.elements
            if element.page_number is not None
        ]

        if not page_elements:
            return ChunkResult(
                document_id=document.document_id,
                title=document.title,
                total_chunks=0,
                strategy=ChunkStrategy.PAGE,
                chunks=[],
                warnings=["当前文档没有 page_number，无法按页切分。"],
            )

        for element in page_elements:
            content = element.content

            if not self.should_keep_chunk(content):
                continue

            chunks.append(
                self.create_chunk(
                    document=document,
                    content=content,
                    chunk_index=chunk_index,
                    strategy=ChunkStrategy.PAGE,
                    extra_metadata={
                        "page_number": element.page_number,
                        "element_id": element.element_id,
                        "element_type": element.type.value,
                    },
                )
            )

            chunk_index += 1

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.PAGE,
            chunks=chunks,
        )
```

---

## 【重点内容】
按页切适合 PDF。

优点是来源引用很清楚：

```plain
第几页
```

缺点是页本身不一定是语义边界。

一个章节可能跨多页。

一个页面也可能包含多个主题。

所以按页切适合：

```plain
需要强来源追踪的 PDF 场景
```

但不一定是召回效果最好的方案。

---

# 十八、实现 ElementChunker
继续追加：

```python
class ElementChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        chunks: list[ChunkDocument] = []
        chunk_index = 0

        for element in document.elements:
            content = element.content

            if not self.should_keep_chunk(content):
                continue

            chunks.append(
                self.create_chunk(
                    document=document,
                    content=content,
                    chunk_index=chunk_index,
                    strategy=ChunkStrategy.ELEMENT,
                    extra_metadata={
                        "element_id": element.element_id,
                        "element_type": element.type.value,
                        "page_number": element.page_number,
                        "order_index": element.order_index,
                    },
                )
            )

            chunk_index += 1

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.ELEMENT,
            chunks=chunks,
        )
```

---

## 【重点内容】
ElementChunker 是直接按上一章解析出来的元素切。

比如：

```plain
一个标题
一个段落
一个表格
一个代码块
一页文本
```

优点是结构清楚。

缺点是有些 element 可能太短。

比如标题单独成为一个 Chunk，语义不完整。

所以后面我们会做 HeadingChunker，把标题和下面的段落合并。

---

# 十九、实现 HeadingChunker
标题结构切分是企业知识库里非常常用的策略。

继续追加：

```python
class HeadingChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        chunks: list[ChunkDocument] = []
        current_heading = document.title
        current_parts: list[str] = []
        current_element_ids: list[str] = []
        current_page_numbers: set[int] = set()
        chunk_index = 0

        def flush_current():
            nonlocal chunk_index, current_parts, current_element_ids, current_page_numbers

            if not current_parts:
                return

            content = "\n\n".join(current_parts)

            if not self.should_keep_chunk(content):
                current_parts = []
                current_element_ids = []
                current_page_numbers = set()
                return

            chunks.append(
                self.create_chunk(
                    document=document,
                    content=content,
                    chunk_index=chunk_index,
                    strategy=ChunkStrategy.HEADING,
                    extra_metadata={
                        "heading": current_heading,
                        "element_ids": current_element_ids,
                        "page_numbers": sorted(current_page_numbers),
                    },
                )
            )

            chunk_index += 1
            current_parts = []
            current_element_ids = []
            current_page_numbers = set()

        for element in document.elements:
            if element.type == ParsedElementType.TITLE:
                flush_current()
                current_heading = element.content
                current_parts = [element.content]
                current_element_ids = [element.element_id]

                if element.page_number:
                    current_page_numbers.add(element.page_number)

                continue

            current_parts.append(element.content)
            current_element_ids.append(element.element_id)

            if element.page_number:
                current_page_numbers.add(element.page_number)

            current_content_size = len("\n\n".join(current_parts))

            if current_content_size >= self.config.chunk_size:
                flush_current()

                if self.config.chunk_overlap > 0:
                    current_parts = [f"上级标题：{current_heading}"]
                    current_element_ids = []
                    current_page_numbers = set()

        flush_current()

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.HEADING,
            chunks=chunks,
        )
```

---

## 【重点内容】
HeadingChunker 是这一章非常重要的策略。

它不是看到标题就单独切一个 Chunk。

而是：

```plain
标题 + 标题下面的正文
```

这样可以保证上下文完整。

比如：

```plain
## 年假制度
员工入职满一年后，可以申请年假。
申请年假需要提前提交审批。
```

应该作为一个整体。

而不是标题一个 Chunk，正文一个 Chunk。

LangChain 也提供 `MarkdownHeaderTextSplitter`，它可以基于 `#`、`##`、`###` 等 Markdown Header 切分，并把 header 信息保存在 metadata 中。

---

# 二十、实现 TableAwareChunker
表格要尽量保持完整。

继续追加：

```python
class TableAwareChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        chunks: list[ChunkDocument] = []
        chunk_index = 0
        text_buffer: list[str] = []

        def flush_text_buffer():
            nonlocal chunk_index, text_buffer

            if not text_buffer:
                return

            content = "\n\n".join(text_buffer)

            if self.should_keep_chunk(content):
                chunks.append(
                    self.create_chunk(
                        document=document,
                        content=content,
                        chunk_index=chunk_index,
                        strategy=ChunkStrategy.TABLE_AWARE,
                        extra_metadata={
                            "chunk_content_type": "text",
                        },
                    )
                )
                chunk_index += 1

            text_buffer = []

        for element in document.elements:
            if element.type == ParsedElementType.TABLE:
                flush_text_buffer()

                if self.should_keep_chunk(element.content):
                    chunks.append(
                        self.create_chunk(
                            document=document,
                            content=element.content,
                            chunk_index=chunk_index,
                            strategy=ChunkStrategy.TABLE_AWARE,
                            extra_metadata={
                                "chunk_content_type": "table",
                                "element_id": element.element_id,
                                "page_number": element.page_number,
                                "order_index": element.order_index,
                            },
                        )
                    )
                    chunk_index += 1

                continue

            text_buffer.append(element.content)

            if len("\n\n".join(text_buffer)) >= self.config.chunk_size:
                flush_text_buffer()

        flush_text_buffer()

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.TABLE_AWARE,
            chunks=chunks,
        )
```

---

## 【重点内容】
企业文档里很多关键信息在表格里。

比如：

```plain
报销标准
会员等级权益
退款时效
SLA
价格表
权限矩阵
```

如果你把表格硬切成几段，很容易丢掉行列关系。

所以 TableAwareChunker 的策略是：

```plain
表格尽量作为独立 Chunk
正文另外合并
```

当然，如果表格特别大，还需要表格专用切分策略。

比如按行组切，或者每行带上表头。

---

# 二十一、实现 CodeAwareChunker
代码文档不能乱切。

继续追加：

```python
class CodeAwareChunker(BaseChunker):
    def split(
        self,
        document: ParsedDocument,
    ) -> ChunkResult:
        chunks: list[ChunkDocument] = []
        chunk_index = 0
        text_buffer: list[str] = []

        def flush_text_buffer():
            nonlocal chunk_index, text_buffer

            if not text_buffer:
                return

            content = "\n\n".join(text_buffer)

            if self.should_keep_chunk(content):
                chunks.append(
                    self.create_chunk(
                        document=document,
                        content=content,
                        chunk_index=chunk_index,
                        strategy=ChunkStrategy.CODE_AWARE,
                        extra_metadata={
                            "chunk_content_type": "text",
                        },
                    )
                )
                chunk_index += 1

            text_buffer = []

        for element in document.elements:
            if element.type == ParsedElementType.CODE:
                flush_text_buffer()

                if self.should_keep_chunk(element.content):
                    chunks.append(
                        self.create_chunk(
                            document=document,
                            content=element.content,
                            chunk_index=chunk_index,
                            strategy=ChunkStrategy.CODE_AWARE,
                            extra_metadata={
                                "chunk_content_type": "code",
                                "element_id": element.element_id,
                                "language": element.metadata.get("language"),
                            },
                        )
                    )
                    chunk_index += 1

                continue

            text_buffer.append(element.content)

            if len("\n\n".join(text_buffer)) >= self.config.chunk_size:
                flush_text_buffer()

        flush_text_buffer()

        return ChunkResult(
            document_id=document.document_id,
            title=document.title,
            total_chunks=len(chunks),
            strategy=ChunkStrategy.CODE_AWARE,
            chunks=chunks,
        )
```

---

## 【重点内容】
代码切分也要特殊处理。

比如：

```python
def query_order():
    ...
```

不能把函数签名和函数体切开。

技术文档里经常有代码块。

如果代码块被切碎，后面问代码问题时召回质量会很差。

LangChain 也支持代码切分，可以通过 `RecursiveCharacterTextSplitter.from_language(...)` 按 Python、JS、Markdown 等语言的结构进行切分。

---

# 二十二、实现 Chunker Factory
打开：

```plain
app/document_chunking/chunker_factory.py
```

写入：

```python
from app.document_chunking.chunkers import (
    BaseChunker,
    CodeAwareChunker,
    ElementChunker,
    FixedSizeChunker,
    HeadingChunker,
    PageChunker,
    ParagraphChunker,
    TableAwareChunker,
)
from app.document_chunking.schemas import (
    ChunkConfig,
    ChunkStrategy,
)


class DocumentChunkerFactory:
    def create_chunker(
        self,
        config: ChunkConfig,
    ) -> BaseChunker:
        if config.strategy == ChunkStrategy.FIXED_SIZE:
            return FixedSizeChunker(config)

        if config.strategy == ChunkStrategy.PARAGRAPH:
            return ParagraphChunker(config)

        if config.strategy == ChunkStrategy.PAGE:
            return PageChunker(config)

        if config.strategy == ChunkStrategy.ELEMENT:
            return ElementChunker(config)

        if config.strategy == ChunkStrategy.HEADING:
            return HeadingChunker(config)

        if config.strategy == ChunkStrategy.TABLE_AWARE:
            return TableAwareChunker(config)

        if config.strategy == ChunkStrategy.CODE_AWARE:
            return CodeAwareChunker(config)

        raise ValueError(
            f"不支持的 Chunk 策略：{config.strategy}"
        )
```

---

# 二十三、实现 Chunking Service
打开：

```plain
app/document_chunking/service.py
```

写入：

```python
from app.document_chunking.chunker_factory import DocumentChunkerFactory
from app.document_chunking.schemas import (
    ChunkConfig,
    ChunkResult,
    ChunkStrategy,
)
from app.document_parsing.schemas import ParsedDocument


class DocumentChunkingService:
    def __init__(self):
        self.factory = DocumentChunkerFactory()

    def split_document(
        self,
        document: ParsedDocument,
        config: ChunkConfig | None = None,
    ) -> ChunkResult:
        if config is None:
            config = ChunkConfig(
                strategy=ChunkStrategy.PARAGRAPH,
                chunk_size=500,
                chunk_overlap=80,
            )

        chunker = self.factory.create_chunker(config)

        return chunker.split(document)

    def split_with_strategy(
        self,
        document: ParsedDocument,
        strategy: ChunkStrategy,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
        min_chunk_size: int = 30,
    ) -> ChunkResult:
        config = ChunkConfig(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
        )

        return self.split_document(
            document=document,
            config=config,
        )


document_chunking_service = DocumentChunkingService()
```

---

# 二十四、准备测试工具函数
为了打印方便，可以创建：

```plain
app/document_chunking/demo_utils.py
```

写入：

```python
from app.document_chunking.schemas import ChunkResult


def print_chunk_result(
    result: ChunkResult,
):
    print("document_id:", result.document_id)
    print("title:", result.title)
    print("strategy:", result.strategy)
    print("total_chunks:", result.total_chunks)

    if result.warnings:
        print("warnings:")
        for warning in result.warnings:
            print("-", warning)

    print("=" * 80)

    for chunk in result.chunks:
        print("chunk_id:", chunk.chunk_id)
        print("chunk_index:", chunk.chunk_index)
        print("strategy:", chunk.strategy)
        print("content:")
        print(chunk.content)
        print("metadata:")
        print(chunk.metadata)
        print("-" * 80)
```

---

# 二十五、示例一：固定长度切分
打开：

```plain
app/document_chunking/demo_01_fixed_size_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def main():
    parsed_document = document_parsing_service.parse_file(
        "data/sample_docs/after_sales.txt",
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.FIXED_SIZE,
            chunk_size=60,
            chunk_overlap=10,
            min_chunk_size=10,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_01_fixed_size.py
```

写入：

```python
from app.document_chunking.demo_01_fixed_size_chunk import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_chunk41_01_fixed_size.py
```

---

# 二十六、示例二：按段落切分
打开：

```plain
app/document_chunking/demo_02_paragraph_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def main():
    parsed_document = document_parsing_service.parse_file(
        "data/sample_docs/employee_handbook.md",
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.PARAGRAPH,
            chunk_size=120,
            chunk_overlap=20,
            min_chunk_size=10,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_02_paragraph.py
```

写入：

```python
from app.document_chunking.demo_02_paragraph_chunk import main


if __name__ == "__main__":
    main()
```

---

# 二十七、示例三：按 ParsedElement 切分
打开：

```plain
app/document_chunking/demo_03_element_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def main():
    parsed_document = document_parsing_service.parse_file(
        "data/sample_docs/help_center.html",
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.ELEMENT,
            chunk_size=500,
            chunk_overlap=0,
            min_chunk_size=5,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_03_element.py
```

写入：

```python
from app.document_chunking.demo_03_element_chunk import main


if __name__ == "__main__":
    main()
```

---

# 二十八、示例四：按标题结构切分
打开：

```plain
app/document_chunking/demo_04_heading_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def main():
    parsed_document = document_parsing_service.parse_file(
        "data/sample_docs/employee_handbook.md",
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.HEADING,
            chunk_size=180,
            chunk_overlap=20,
            min_chunk_size=10,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_04_heading.py
```

写入：

```python
from app.document_chunking.demo_04_heading_chunk import main


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
大家重点看这个示例。

HeadingChunker 的效果应该是：

```plain
标题和对应正文在同一个 Chunk 里。
```

这样用户问：

```plain
年假制度是什么？
```

召回到的 Chunk 会同时包含：

```plain
年假制度标题
年假制度正文
```

这个比单纯固定长度切分更适合制度类文档。

---

# 二十九、示例五：表格感知切分
打开：

```plain
app/document_chunking/demo_05_table_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.demo_04_parse_docx import create_sample_docx
from app.document_parsing.service import document_parsing_service


def main():
    file_path = create_sample_docx()

    parsed_document = document_parsing_service.parse_file(
        file_path,
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.TABLE_AWARE,
            chunk_size=180,
            chunk_overlap=20,
            min_chunk_size=5,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_05_table.py
```

写入：

```python
from app.document_chunking.demo_05_table_chunk import main


if __name__ == "__main__":
    main()
```

---

# 三十、示例六：代码感知切分
打开：

```plain
app/document_chunking/demo_06_code_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def main():
    parsed_document = document_parsing_service.parse_file(
        "data/sample_docs/employee_handbook.md",
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=ChunkStrategy.CODE_AWARE,
            chunk_size=150,
            chunk_overlap=20,
            min_chunk_size=5,
        ),
    )

    print_chunk_result(result)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_06_code.py
```

写入：

```python
from app.document_chunking.demo_06_code_chunk import main


if __name__ == "__main__":
    main()
```

---

# 三十一、示例七：解析 + 切分完整流程
打开：

```plain
app/document_chunking/demo_07_parse_and_chunk.py
```

写入：

```python
from app.document_chunking.demo_utils import print_chunk_result
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service


def run_case(
    file_path: str,
    strategy: ChunkStrategy,
):
    print("文件:", file_path)
    print("策略:", strategy)
    print("=" * 80)

    parsed_document = document_parsing_service.parse_file(
        file_path,
        tenant_id="tenant_001",
        created_by="u_10001",
    )

    result = document_chunking_service.split_document(
        parsed_document,
        config=ChunkConfig(
            strategy=strategy,
            chunk_size=180,
            chunk_overlap=30,
            min_chunk_size=10,
        ),
    )

    print_chunk_result(result)


def main():
    cases = [
        ("data/sample_docs/after_sales.txt", ChunkStrategy.PARAGRAPH),
        ("data/sample_docs/employee_handbook.md", ChunkStrategy.HEADING),
        ("data/sample_docs/help_center.html", ChunkStrategy.ELEMENT),
    ]

    for file_path, strategy in cases:
        run_case(file_path, strategy)
        print("=" * 120)


if __name__ == "__main__":
    main()
```

脚本：

```plain
scripts/test_chunk41_07_parse_and_chunk.py
```

写入：

```python
from app.document_chunking.demo_07_parse_and_chunk import main


if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/test_chunk41_07_parse_and_chunk.py
```

---

# 三十二、LangChain Text Splitter 示例
打开：

```plain
app/document_chunking/langchain_examples.py
```

写入：

```python
def demo_recursive_character_splitter():
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text = (
        "订单未发货时，用户可以申请取消订单并退款。\n\n"
        "订单已发货后，用户需要收到商品后再申请退货退款。\n\n"
        "如果商品存在质量问题，用户可以提交照片或视频凭证申请售后。"
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=50,
        chunk_overlap=10,
        separators=[
            "\n\n",
            "\n",
            "。",
            "，",
            "",
        ],
    )

    chunks = splitter.split_text(text)

    for index, chunk in enumerate(chunks):
        print("chunk", index)
        print(chunk)
        print("-" * 80)


def demo_markdown_header_splitter():
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    markdown_text = """
# 员工手册

## 考勤制度

员工需要按照公司规定时间打卡。

## 年假制度

员工入职满一年后，可以申请年假。
申请年假需要提前提交审批。

## 报销制度

差旅报销需要提交发票、行程单和审批记录。
"""

    headers_to_split_on = [
        ("#", "一级标题"),
        ("##", "二级标题"),
        ("###", "三级标题"),
    ]

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
    )

    docs = splitter.split_text(markdown_text)

    for index, doc in enumerate(docs):
        print("doc", index)
        print("content:", doc.page_content)
        print("metadata:", doc.metadata)
        print("-" * 80)


def demo_python_code_splitter():
    from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

    code = '''
class OrderService:
    def query_order(self, order_id: str):
        return {"order_id": order_id}

    def refund_order(self, order_id: str):
        return {"success": True}
'''

    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=80,
        chunk_overlap=0,
    )

    docs = splitter.create_documents([code])

    for index, doc in enumerate(docs):
        print("doc", index)
        print(doc.page_content)
        print("-" * 80)


def main():
    print("RecursiveCharacterTextSplitter:")
    demo_recursive_character_splitter()

    print("=" * 120)
    print("MarkdownHeaderTextSplitter:")
    demo_markdown_header_splitter()

    print("=" * 120)
    print("PythonCodeTextSplitter:")
    demo_python_code_splitter()


if __name__ == "__main__":
    main()
```

---

## 【重点内容】
这里给大家展示 LangChain 版本。

`RecursiveCharacterTextSplitter` 会递归尝试用不同 separators 切分，例如先按段落，再按换行，再按句号，最后才硬切。LangChain 官方文档也把它作为通用文本切分的常见起点。

`MarkdownHeaderTextSplitter` 适合 Markdown 文档，它会按 Header 切分，并把标题层级放到 metadata 里。

代码场景可以用语言感知切分器，LangChain 支持通过 `Language` 枚举选择 Python 等语言。

---

# 三十三、FastAPI Chunk 接口
打开：

```plain
app/api/v1/document_chunking.py
```

写入：

```python
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_user
from app.document_chunking.schemas import ChunkConfig, ChunkStrategy
from app.document_chunking.service import document_chunking_service
from app.document_parsing.service import document_parsing_service
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser


router = APIRouter()


class ChunkFileRequest(BaseModel):
    file_path: str = Field(..., min_length=1)
    tenant_id: str = Field(default="tenant_001")
    strategy: Literal[
        "fixed_size",
        "paragraph",
        "page",
        "element",
        "heading",
        "table_aware",
        "code_aware",
    ] = "paragraph"
    chunk_size: int = Field(default=500, gt=0)
    chunk_overlap: int = Field(default=80, ge=0)
    min_chunk_size: int = Field(default=30, ge=0)


@router.post(
    "/documents/chunk",
    response_model=ApiResponse[dict],
)
async def chunk_document(
    request: ChunkFileRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[dict]:
    parsed_document = document_parsing_service.parse_file(
        file_path=request.file_path,
        tenant_id=request.tenant_id,
        created_by=current_user.user_id,
    )

    config = ChunkConfig(
        strategy=ChunkStrategy(request.strategy),
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        min_chunk_size=request.min_chunk_size,
    )

    result = document_chunking_service.split_document(
        document=parsed_document,
        config=config,
    )

    return ApiResponse[dict](
        data={
            "document_id": result.document_id,
            "title": result.title,
            "strategy": result.strategy.value,
            "total_chunks": result.total_chunks,
            "warnings": result.warnings,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "strategy": chunk.strategy.value,
                    "metadata": chunk.metadata,
                }
                for chunk in result.chunks
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
from app.api.v1.document_chunking import router as document_chunking_router
```

注册：

```python
api_router.include_router(
    document_chunking_router,
    tags=["Document Chunking"],
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
curl -X POST "http://127.0.0.1:8000/api/v1/documents/chunk" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "file_path": "data/sample_docs/employee_handbook.md",
    "tenant_id": "tenant_001",
    "strategy": "heading",
    "chunk_size": 180,
    "chunk_overlap": 30,
    "min_chunk_size": 10
  }'
```

---

# 三十六、Chunk metadata 应该保存什么
推荐 metadata：

```plain
tenant_id
department
doc_type
version
document_id
document_title
file_name
file_type
source_path
chunk_index
chunk_strategy
page_number
page_numbers
element_id
element_ids
heading
section_path
created_by
created_at
```

---

## 【重点内容】
metadata 是后面召回和引用的基础。

比如用户问 HR 制度，Retriever 可以只搜索：

```python
metadata_filter = {
    "tenant_id": "tenant_001",
    "department": "hr",
    "doc_type": "employee_handbook",
}
```

如果 Chunk 没有这些 metadata，后面做权限过滤、版本过滤和来源引用都很麻烦。

---

# 三十七、Chunk 和来源引用
一个好的 Chunk 要能追溯到原文：

```json
{
  "chunk_id": "doc_001_chunk_3",
  "document_id": "doc_001",
  "document_title": "员工手册",
  "source_path": "employee_handbook.pdf",
  "page_number": 5,
  "heading": "年假制度",
  "chunk_index": 3
}
```

最终回答时可以展示：

```plain
来源：员工手册，第 5 页，年假制度
```

---

## 【重点内容】
RAG 项目不能只返回答案。

还要返回来源。

来源引用不是最后临时拼的。

它来自前面的 metadata。

所以从第 40 章文档解析开始，到第 41 章 Chunk 切分，都要把来源链条保留下来。

---

# 三十八、Chunk 和权限过滤
权限信息建议从文档解析阶段传到 Chunk：

```json
{
  "tenant_id": "tenant_001",
  "department": "finance",
  "allowed_roles": ["finance", "admin"]
}
```

后面检索时：

```python
filter = {
    "tenant_id": "tenant_001",
    "department": "finance",
}
```

---

## 【重点内容】
企业知识库一定要避免跨权限召回。

比如财务制度不能被普通员工随便召回。

如果权限 metadata 没有进入 Chunk，后面向量检索时就无法过滤。

所以 Chunk metadata 不只是为了引用，也是为了安全。

---

# 三十九、Chunk 和版本过滤
文档版本也要进入 Chunk：

```json
{
  "version": "2026-08",
  "is_latest": true,
  "effective_date": "2026-08-01"
}
```

检索时优先：

```python
filter = {
    "is_latest": True
}
```

---

# 四十、Chunk 质量检查
切完 Chunk 后，要做质量检查：

```plain
1. total_chunks 是否为 0
2. 是否有大量过短 chunk
3. 是否有大量重复 chunk
4. chunk 是否超过最大长度
5. metadata 是否完整
6. 表格 chunk 是否保留结构
7. 标题 chunk 是否包含正文
8. page_number 是否保留
```

示例函数：

```python
def validate_chunk_result(result: ChunkResult) -> list[str]:
    warnings = []

    if result.total_chunks == 0:
        warnings.append("没有生成任何 chunk")

    short_count = sum(
        1 for chunk in result.chunks
        if len(chunk.content) < 30
    )

    if short_count > result.total_chunks * 0.5:
        warnings.append("过短 chunk 占比过高")

    for chunk in result.chunks:
        if not chunk.metadata.get("document_id"):
            warnings.append(f"{chunk.chunk_id} 缺少 document_id")

    return warnings
```

---

# 四十一、Chunk 数据表设计
项目三可以设计：

```sql
CREATE TABLE knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    document_id VARCHAR(128) NOT NULL,
    chunk_id VARCHAR(255) NOT NULL UNIQUE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    strategy VARCHAR(64) NOT NULL,
    token_count INT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

如果要保存向量，可以另建表：

```sql
CREATE TABLE knowledge_chunk_embeddings (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    chunk_id VARCHAR(255) NOT NULL,
    embedding_model VARCHAR(128) NOT NULL,
    embedding VECTOR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 【重点内容】
Chunk 表和 Embedding 表可以分开。

原因是：

```plain
Chunk 文本可能不变
Embedding 模型可能升级
```

比如你从一个 embedding 模型换到另一个 embedding 模型，Chunk 不需要重新生成，只需要重新生成 embedding。

所以分表更灵活。

---

# 四十二、Chunk 和第 42 章 Embedding 的衔接
第 42 章会接收本章输出：

```python
chunk_result = document_chunking_service.split_document(parsed_document)

for chunk in chunk_result.chunks:
    embedding = embedding_service.embed_text(chunk.content)
    vector_store.add(
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        embedding=embedding,
        metadata=chunk.metadata,
    )
```

流程：

```plain
ParsedDocument
 ↓
ChunkDocument
 ↓
Embedding
 ↓
Vector Database
```

---

# 四十三、生产环境推荐策略
不同文档推荐不同策略：

```plain
TXT FAQ：
ParagraphChunker

Markdown 技术文档：
HeadingChunker / MarkdownHeaderTextSplitter

HTML 帮助中心：
HTMLHeaderTextSplitter 或 ElementChunker

PDF 制度文档：
PageChunker + HeadingChunker 混合

Word 合同文档：
HeadingChunker + TableAwareChunker

代码文档：
CodeAwareChunker / PythonCodeTextSplitter
```

---

# 四十四、不要盲目相信固定参数
企业项目要建立评估集。

比如：

```plain
100 个真实用户问题
每个问题对应正确文档和正确 chunk
```

然后测试：

```plain
chunk_size=300
chunk_size=500
chunk_size=800
chunk_overlap=50
chunk_overlap=100
heading chunk
paragraph chunk
rerank
```

看：

```plain
Recall@3
Recall@5
MRR
答案准确率
答案引用正确率
```

第 44 章会专门讲 RAG Evaluation。

---

# 四十五、常见错误一：标题和正文分离
错误 Chunk：

```plain
Chunk 1：
年假制度

Chunk 2：
员工入职满一年后，可以申请年假。
```

问题：

```plain
用户问年假制度，可能只召回标题，或者只召回正文，语义不完整。
```

正确：

```plain
Chunk：
年假制度
员工入职满一年后，可以申请年假。
```

---

# 四十六、常见错误二：表格被切碎
错误：

```plain
Chunk 1：
级别 | 年假天数

Chunk 2：
P6 | 10 天
P7 | 15 天
```

正确：

```plain
表格作为完整 Chunk，或者每行带上表头。
```

---

# 四十七、常见错误三：只按字符硬切
错误：

```plain
每 500 字符切一次，不管语义。
```

正确：

```plain
优先按标题、段落、页、表格等结构切。
```

---

# 四十八、常见错误四：chunk_overlap 太大
错误：

```plain
chunk_size=500
chunk_overlap=400
```

问题：

```plain
大量重复
成本增加
召回结果重复
```

---

# 四十九、常见错误五：Chunk 没有 metadata
错误：

```python
{
    "content": "订单未发货可以退款"
}
```

正确：

```python
{
    "chunk_id": "...",
    "content": "...",
    "metadata": {
        "document_id": "...",
        "source_path": "...",
        "page_number": 3,
        "heading": "退款规则",
        "tenant_id": "tenant_001"
    }
}
```

---

# 五十、常见错误六：短 Chunk 太多
短 Chunk 太多会导致：

```plain
召回不稳定
语义不完整
向量表达弱
```

可以通过：

```plain
min_chunk_size
短段落合并
标题和正文合并
```

解决。

---

# 五十一、面试回答：Chunk 是什么
```plain
Chunk 是 RAG 里的最小检索单元。

企业文档通常比较长，不能直接整篇入向量库，也不能整篇塞给模型。所以需要先把文档切成多个语义相对完整的片段，每个片段就是一个 Chunk。

用户提问时，Retriever 实际召回的是 Chunk，而不是整篇文档。Chunk 的质量会直接影响召回质量和最终回答准确率。
```

---

# 五十二、面试回答：Chunk 怎么切
```plain
我不会简单固定长度切分，而是会结合文档结构。

比如 Markdown 技术文档可以按 Header 切；制度类文档可以按标题和段落切；PDF 可以按页码和标题混合切；Word 合同要保留标题、段落和表格；代码文档尽量按函数、类或代码块切。

同时每个 Chunk 要保留 metadata，比如 document_id、source_path、page_number、heading、tenant_id、version，这样后面才能做来源引用、权限过滤和版本过滤。
```

---

# 五十三、面试回答：chunk_size 和 chunk_overlap 怎么选
```plain
chunk_size 和 chunk_overlap 没有固定答案，要结合文档类型、问题类型、Embedding 模型、模型上下文窗口和评估结果来调。

一般来说，FAQ 可以小一些，制度文档可以中等，技术文档可以稍大一些。chunk_overlap 用来避免语义被切断，但不能过大，否则会导致重复内容增加、向量库膨胀和召回结果重复。

工程上我会准备一批真实问题做评估，对比不同 chunk_size、overlap 和切分策略下的 Recall@K 和答案准确率。
```

---

# 五十四、面试回答：为什么 Chunk 切分会影响 RAG 效果
```plain
因为 Retriever 召回的是 Chunk。

如果 Chunk 太大，一个片段里会混入多个主题，向量语义不够精准，模型拿到的上下文也会有很多噪音。

如果 Chunk 太小，语义不完整，可能标题和正文分离，或者表格行列关系丢失，模型即使召回了相关片段，也无法回答完整问题。

所以 Chunk 切分是 RAG 质量的上限之一，不能只依赖向量数据库和大模型。
```

---

# 五十五、简历亮点怎么写
可以写成：

```plain
企业知识库 Chunk 切分模块：
负责设计 RAG 入库链路中的 Chunk 切分模块，基于文档解析阶段产出的 ParsedDocument / ParsedElement，实现固定长度、段落、页码、标题结构、表格感知、代码感知等多种切分策略。通过 ChunkConfig 统一管理 chunk_size、chunk_overlap、min_chunk_size 等参数，并在 Chunk metadata 中保留 document_id、source_path、page_number、heading、tenant_id、version、element_ids 等信息，为后续 Embedding、向量检索、权限过滤和来源引用提供基础。

针对制度类和 Markdown 文档，优先使用标题结构切分，避免标题和正文分离；针对 Word / PDF 中的表格内容，采用表格感知切分，尽量保留表格结构，提升企业知识库问答的召回质量和可追溯性。
```

---

# 五十六、本章知识点和后续章节对应表
| 本章知识点 | 后续用途 |
| --- | --- |
| ChunkDocument | 第 42 章 Embedding 输入 |
| chunk_id | 向量库主键 |
| chunk_index | 来源排序 |
| chunk_size | 召回粒度控制 |
| chunk_overlap | 避免上下文断裂 |
| metadata | 第 43 章过滤和引用 |
| heading | 标题召回 |
| page_number | 来源引用 |
| TableAwareChunker | 表格问答 |
| CodeAwareChunker | 技术文档问答 |
| ChunkResult | 项目三入库流程 |


---

# 五十七、本章完整复习
这一章我们完成了：

```plain
1. 理解 Chunk 是什么
2. 理解为什么 RAG 必须做 Chunk
3. 理解 Chunk 太大的问题
4. 理解 Chunk 太小的问题
5. 理解 chunk_size
6. 理解 chunk_overlap
7. 总结 Chunk 参数选择方法
8. 设计 ChunkStrategy
9. 设计 ChunkConfig
10. 设计 ChunkDocument
11. 设计 ChunkResult
12. 实现 BaseChunker
13. 实现 FixedSizeChunker
14. 实现 ParagraphChunker
15. 实现 PageChunker
16. 实现 ElementChunker
17. 实现 HeadingChunker
18. 实现 TableAwareChunker
19. 实现 CodeAwareChunker
20. 实现 ChunkerFactory
21. 实现 DocumentChunkingService
22. 跑通固定长度切分
23. 跑通段落切分
24. 跑通 Element 切分
25. 跑通标题结构切分
26. 跑通表格感知切分
27. 跑通代码感知切分
28. 跑通解析 + 切分完整流程
29. 补充 LangChain Text Splitter 示例
30. 创建 FastAPI Chunk 接口
31. 理解 Chunk metadata 设计
32. 理解 Chunk 和来源引用
33. 理解 Chunk 和权限过滤
34. 理解 Chunk 和版本过滤
35. 理解 Chunk 质量检查
36. 设计 Chunk 数据表
37. 理解 Chunk 和第 42 章 Embedding 的衔接
38. 总结生产环境推荐策略
39. 总结常见错误
40. 准备面试回答话术
41. 准备简历亮点描述
```

---

# 五十八、课后任务一：跑通固定长度切分
要求：

```plain
1. 运行 scripts/test_chunk41_01_fixed_size.py
2. 查看每个 Chunk 的 start_char / end_char
3. 修改 chunk_size=30 再运行
4. 观察语义是否被切断
```

---

# 五十九、课后任务二：跑通段落切分
要求：

```plain
1. 运行 scripts/test_chunk41_02_paragraph.py
2. 查看段落是否被完整保留
3. 修改 chunk_size
4. 观察段落合并情况
```

---

# 六十、课后任务三：跑通 Element 切分
要求：

```plain
1. 运行 scripts/test_chunk41_03_element.py
2. 查看 HTML 解析出来的 h1 / p / li 是否变成 Chunk
3. 思考 Element 太短时有什么问题
```

---

# 六十一、课后任务四：跑通标题结构切分
要求：

```plain
1. 运行 scripts/test_chunk41_04_heading.py
2. 查看 heading metadata
3. 查看标题和正文是否在同一个 Chunk
4. 思考为什么制度文档适合标题结构切分
```

---

# 六十二、课后任务五：跑通表格感知切分
要求：

```plain
1. 运行 scripts/test_chunk41_05_table.py
2. 查看表格是否单独成为 Chunk
3. 查看 chunk_content_type=table
4. 思考大表格应该怎么进一步切
```

---

# 六十三、课后任务六：跑通代码感知切分
要求：

```plain
1. 运行 scripts/test_chunk41_06_code.py
2. 查看代码块是否单独成为 Chunk
3. 思考函数和类被切断会造成什么问题
```

---

# 六十四、课后任务七：跑通解析 + 切分完整链路
要求：

```plain
1. 运行 scripts/test_chunk41_07_parse_and_chunk.py
2. 对比 TXT / Markdown / HTML 的切分结果
3. 说明不同文档为什么要选不同策略
```

---

# 六十五、课后任务八：测试 LangChain Text Splitter
要求：

```plain
1. 安装 langchain-text-splitters
2. 运行 app/document_chunking/langchain_examples.py
3. 查看 RecursiveCharacterTextSplitter 效果
4. 查看 MarkdownHeaderTextSplitter metadata
5. 查看 Python 代码切分效果
```

---

# 六十六、课后任务九：设计 Chunk 质量检测
实现：

```python
validate_chunk_result(result: ChunkResult) -> list[str]
```

检查：

```plain
1. total_chunks 是否为 0
2. 短 Chunk 占比是否过高
3. 是否缺少 document_id
4. 是否缺少 tenant_id
5. 是否缺少 source_path
6. 是否有重复内容
```

---

# 六十七、课后任务十：设计项目三 Chunk 入库表
要求设计：

```plain
knowledge_chunks
```

必须包含：

```plain
tenant_id
document_id
chunk_id
chunk_index
content
strategy
metadata
token_count
created_at
```

---

# 六十八、课后任务十一：对比不同切分策略
用同一个 Markdown 文档分别测试：

```plain
FixedSizeChunker
ParagraphChunker
ElementChunker
HeadingChunker
```

对比：

```plain
1. Chunk 数量
2. 每个 Chunk 是否语义完整
3. 标题是否保留
4. metadata 是否丰富
5. 哪个更适合企业知识库
```

---

# 六十九、本章总结
## 【重点内容】
好了，到这里，第 41 章我们就讲完了。

这一章我们讲的是 Chunk 文档切分。

大家一定要记住：

```plain
Chunk 是 RAG 的最小检索单元。
Chunk 切得好不好，直接影响召回质量和最终答案质量。
```

Chunk 不能只靠固定长度硬切。

企业项目里要根据文档结构来切：

```plain
制度文档按标题和段落切
PDF 可以结合页码切
Word 要保留段落和表格
Markdown 要按 Header 切
代码文档要按代码结构切
```

这一章我们实现了：

```plain
FixedSizeChunker
ParagraphChunker
PageChunker
ElementChunker
HeadingChunker
TableAwareChunker
CodeAwareChunker
DocumentChunkingService
FastAPI Chunk 接口
```

还要记住：

```plain
Chunk metadata 非常重要。
```

它决定后面能不能做：

```plain
来源引用
权限过滤
版本过滤
问题排查
召回评估
```

Chunk 不是 RAG 里最炫的部分，但它是最影响效果的部分之一。

下一章我们就会基于这些 Chunk，继续做 Embedding 和 Vector Database。

---
