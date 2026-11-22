**核心技术：** LangChain Document Loaders、PyPDFLoader、Docx2txtLoader、Unstructured、CSVLoader、JSONLoader、HTML、Markdown、OCR、Metadata

**课程定位：** 掌握企业知识库中 PDF、Word、Excel、Markdown、HTML、TXT 等文档的解析、清洗、元数据提取与异常处理，构建完整的 Document Loader Pipeline。

---

## 一、本章学习目标
在第 39 章中，我们将理解 RAG 的整体架构。

但在企业真实项目中，知识通常不是直接以纯文本形式存在，而是来自：

+ PDF 文件
+ Word 文档
+ Excel 表格
+ Markdown 文档
+ HTML 网页
+ TXT 文件
+ CSV 数据
+ JSON 数据
+ 企业内部知识系统
+ 数据库
+ OCR 识别结果

因此，RAG 的第一步并不是直接调用 Embedding，而是：

**将不同来源、不同格式的数据统一转换为 LangChain Document。**

本章重点掌握：

1. Document 与 Document Loader 是什么？
2. LangChain Document 的数据结构是什么？
3. 如何解析 PDF？
4. 如何解析 Word？
5. 如何解析 Markdown？
6. 如何解析 Excel、CSV、JSON？
7. 如何解析 HTML？
8. 扫描版 PDF 如何处理？
9. 文档清洗如何实现？
10. Metadata 如何设计？
11. 企业文档解析 Pipeline 如何设计？
12. 如何实现批量文档解析与异常处理？

---

## 二、Document 是什么？
LangChain 中的 Document 是统一的文档数据结构。

它主要包含：

```python
Document(
    page_content="文档内容",
    metadata={
        "source": "文件来源",
    },
) 
```

其中：

+ `page_content`：文本内容
+ `metadata`：文档元数据

例如：

```python
from langchain_core.documents import Document

document = Document(
    page_content="员工申请年假需要提前三个工作日。",
    metadata={
        "source": "employee-handbook.pdf",
        "page": 3,
        "department": "HR",
    },
)

print(document.page_content)
print(document.metadata)
```

输出：

```python
员工申请年假需要提前三个工作日。

{
    'source': 'employee-handbook.pdf',
    'page': 3,
    'department': 'HR'
}
```

为什么需要统一 Document？

因为不同文件格式的数据结构完全不同。

例如：

```plain
PDF
Word
Excel
Markdown
HTML
```

如果每种格式都使用不同的业务接口，后续 RAG Pipeline 会非常复杂。

LangChain Document Loader 的核心价值：

**将不同来源的数据统一转换为 Document，方便后续统一清洗、切分、Embedding 和存储。**

官方参考：

[https://docs.langchain.com/oss/python/integrations/document_loaders](https://docs.langchain.com/oss/python/integrations/document_loaders)

---

## 三、项目初始化
创建项目：

```python
uv init document-loader-demo --python 3.12

cd document-loader-demo
```

安装依赖：

```bash
uv add langchain-core langchain-community langchain-text-splitters pypdf docx2txt unstructured python-dotenv
```

Excel 支持：

```plain
uv add openpyxl
```

CSV 支持：

```plain
uv add pandas
```

HTML 支持：

```plain
uv add beautifulsoup4 lxml
```

扫描 PDF OCR：

```plain
uv add pymupdf pytesseract pillow
```

注意：

OCR 还需要安装系统级 Tesseract OCR 引擎。

macOS：

```plain
brew install tesseract
```

项目结构：

```markdown
document-loader-demo/
├── pyproject.toml
├── data/
│   ├── employee-handbook.pdf
│   ├── employee-handbook.docx
│   ├── employee-handbook.md
│   ├── employee-handbook.txt
│   ├── employee-handbook.csv
│   ├── employee-handbook.xlsx
│   ├── employee-handbook.json
│   └── employee-handbook.html
├── loaders/
│   ├── pdf_loader.py
│   ├── word_loader.py
│   ├── markdown_loader.py
│   ├── csv_loader.py
│   ├── excel_loader.py
│   ├── json_loader.py
│   └── html_loader.py
├── document_cleaner.py
├── metadata_enrichment.py
├── batch_loader.py
└── main.py
```

---

## 四、PDF 文档解析
PDF 是企业知识库中非常常见的文档格式。

例如：

+ 企业制度
+ 产品手册
+ 技术方案
+ 研究报告
+ 业务流程
+ 项目文档
+ 合同文件

LangChain 提供 PyPDFLoader。

底层使用 pypdf 解析 PDF。

### 4.1 安装依赖
```plain
uv add langchain-community pypdf
```

### 4.2 创建 loaders/pdf_loader.py
```python
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(file_path)

    loader = PyPDFLoader(
        file_path=str(path),
        mode="page",
    )

    documents = loader.load()

    print(f"PDF 文件：{path.name}")
    print(f"解析页数：{len(documents)}")

    for document in documents:
        print("Page:", document.metadata.get("page"))
        print("Content:", document.page_content[:100])

    return documents


if __name__ == "__main__":
    load_pdf("data/employee-handbook.pdf")
```

运行：

```plain
uv run python loaders/pdf_loader.py
```

### 4.3 PDF 解析结果
通常会得到：

```python
Document(
    page_content="员工申请年假需要提前三个工作日...",
    metadata={
        "source": "employee-handbook.pdf",
        "page": 2,
    },
)
```

这里的页码通常从 0 开始。

例如：

```plain
PDF 第 1 页 → page = 0
PDF 第 2 页 → page = 1
PDF 第 3 页 → page = 2
```

具体 Metadata 结构以 Loader 实际返回为准。

### 4.4 PDF 解析的常见问题
PDF 可能存在：

+ 双栏布局
+ 表格
+ 图片
+ 页眉
+ 页脚
+ 水印
+ 扫描图片
+ 字体编码异常
+ 文本顺序混乱

PyPDFLoader 主要适用于 PDF 中存在可提取文本的情况。

对于复杂版面、扫描件或表格密集型 PDF，可以考虑：

+ PyMuPDF
+ Docling
+ Unstructured
+ MinerU
+ OCR + Layout Parsing

企业项目不应该认为所有 PDF 都能够通过一个 Loader 完整解析。

---

## 五、Word 文档解析
企业内部常见：

+ 员工手册
+ 项目方案
+ 产品需求文档
+ 技术设计文档
+ 业务流程文档

LangChain 提供 Docx2txtLoader。

### 5.1 安装依赖
```plain
uv add langchain-community docx2txt
```

### 5.2 创建 loaders/word_loader.py
```python
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader


def load_word(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(file_path)

    loader = Docx2txtLoader(
        file_path=str(path)
    )

    documents = loader.load()

    print(f"Word 文件：{path.name}")
    print(f"Document 数量：{len(documents)}")

    for document in documents:
        print(document.page_content[:500])
        print(document.metadata)

    return documents


if __name__ == "__main__":
    load_word("data/employee-handbook.docx")
```

运行：

```plain
uv run python loaders/word_loader.py
```

### 5.3 Word 解析的注意事项
Docx2txtLoader 主要用于提取 DOCX 文本。

如果 Word 文档中存在：

+ 复杂表格
+ 图片
+ 图表
+ 文本框
+ 多级标题
+ 特殊布局

可能需要更复杂的解析方案。

可以考虑：

+ python-docx
+ Unstructured
+ Docling

如果需要保留 Word 的标题层级、表格结构及内容关联，不能仅依赖纯文本提取。

---

## 六、Markdown 文档解析
Markdown 是非常适合企业知识库的文档格式。

原因：

+ 文本结构清晰
+ 标题层级明确
+ 适合版本管理
+ 适合 Git 仓库
+ 方便技术文档管理
+ 适合后续 Chunking

### 6.1 Markdown Loader
创建 `loaders/markdown_loader.py`：

```python
from pathlib import Path

from langchain_community.document_loaders import TextLoader


def load_markdown(file_path: str):
    path = Path(file_path)

    loader = TextLoader(
        file_path=str(path),
        encoding="utf-8",
    )

    documents = loader.load()

    for document in documents:
        print(document.page_content)
        print(document.metadata)

    return documents


if __name__ == "__main__":
    load_markdown(
        "data/employee-handbook.md"
    )
```

运行：

```plain
uv run python loaders/markdown_loader.py
```

注意：

Markdown Loader 通常只负责读取文本。

Markdown 的标题结构切分应在后续使用：

```plain
MarkdownHeaderTextSplitter
```

这部分在第 41 章详细讲解。

---

## 七、TXT 文档解析
TXT 是最简单的文档格式。

使用 TextLoader：

```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader(
    "data/employee-handbook.txt",
    encoding="utf-8",
)

documents = loader.load()

print(documents)
```

企业项目建议明确指定编码。

如果编码不确定，可以在文件预处理阶段检测或统一编码，避免出现乱码。

---

## 八、CSV 文档解析
CSV 通常用于：

+ 产品信息
+ FAQ
+ 客户数据
+ 业务配置
+ 指标说明
+ 结构化知识

### 8.1 CSVLoader
```python
from langchain_community.document_loaders import CSVLoader

loader = CSVLoader(
    file_path="data/employee-handbook.csv",
    encoding="utf-8",
)

documents = loader.load()

for document in documents:
    print(document.page_content)
    print(document.metadata)
```

例如 CSV：

```plain
question,answer
年假需要提前多久申请,需要提前三个工作日
病假需要什么材料,需要医院相关证明
```

Loader 可以将每一行转换为 Document。

但要注意：

CSV 每行是否应该独立成为一个 Chunk，取决于业务语义。

对于 FAQ：

```plain
Question + Answer
```

建议保持在同一个 Document 中。

不要将问题和答案拆开。

---

## 九、Excel 文档解析
企业知识库中经常存在 Excel：

+ 业务规则表
+ 产品价格表
+ 指标说明表
+ 业务配置表
+ FAQ 表
+ 数据字典

对于简单 Excel，可以使用 Python 的 openpyxl 进行解析，再转换为 LangChain Document。

### 9.1 安装依赖
```plain
uv add openpyxl langchain-core
```

### 9.2 创建 loaders/excel_loader.py
```python
from pathlib import Path

from openpyxl import load_workbook

from langchain_core.documents import Document


def load_excel(file_path: str):
    path = Path(file_path)

    workbook = load_workbook(
        filename=path,
        read_only=True,
        data_only=True,
    )

    documents = []

    for sheet in workbook.worksheets:
        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            continue

        headers = [
            str(value).strip()
            if value is not None
            else f"column_{index}"
            for index, value in enumerate(
                rows[0],
                start=1,
            )
        ]

        for row_index, row in enumerate(
            rows[1:],
            start=2,
        ):
            values = []

            for header, value in zip(headers, row):
                if value is None:
                    continue

                values.append(
                    f"{header}: {value}"
                )

            if not values:
                continue

            content = "\n".join(values)

            document = Document(
                page_content=content,
                metadata={
                    "source": path.name,
                    "sheet": sheet.title,
                    "row": row_index,
                    "document_type": "excel",
                },
            )

            documents.append(document)

    workbook.close()

    print(f"Excel 解析完成，共 {len(documents)} 条记录")

    return documents


if __name__ == "__main__":
    load_excel("data/employee-handbook.xlsx")
```

### 9.3 Excel 转换后的 Document
例如：

```plain
产品名称: 企业版
价格: 999
适用客户: 企业用户
```

Metadata：

```json
{
  "source": "product.xlsx",
  "sheet": "产品价格",
  "row": 2,
  "document_type": "excel",
}
```

### 9.4 Excel 解析注意事项
上面是一个简单的结构化表格解析案例。

复杂 Excel 可能包含：

+ 多级表头
+ 合并单元格
+ 多 Sheet 关联
+ 公式
+ 图片
+ 业务规则
+ 跨行数据

对于复杂表格，建议先分析业务结构，再设计专用解析器。

不要将所有 Excel 简单转换成字符串后直接进行向量化。

---

## 十、JSON 文档解析
JSON 常见于：

+ API 返回数据
+ 配置文件
+ 产品数据
+ FAQ
+ 业务知识
+ 系统规则

LangChain 提供 JSONLoader。

### 10.1 安装依赖
```plain
uv add langchain-community jq
```

JSONLoader 需要 jq 支持。

### 10.2 示例 JSON
创建 `data/employee-handbook.json`：

```python
{
    "policies": [
        {
            "title": "年假制度",
            "content": "员工申请年假需要提前三个工作日提交申请。"
        },
        {
            "title": "病假制度",
            "content": "员工申请病假需要提交医院相关证明。"
        }
    ]
}
```

### 10.3 创建 loaders/json_loader.py
```python
from langchain_community.document_loaders import JSONLoader


def load_json(file_path: str):
    loader = JSONLoader(
        file_path=file_path,
        jq_schema=".policies[]",
        content_key="content",
        metadata_func=lambda record, metadata: {
            **metadata,
            "title": record.get("title"),
            "document_type": "json",
        },
    )

    documents = loader.load()

    for document in documents:
        print(document.page_content)
        print(document.metadata)

    return documents


if __name__ == "__main__":
    load_json("data/employee-handbook.json")
```

### 10.4 JSONLoader 的作用
JSONLoader 可以：

+ 使用 jq_schema 选择数据
+ 提取指定字段
+ 提取 Metadata
+ 将 JSON 数据转换为 Document

企业项目中，JSONLoader 非常适合处理结构化知识数据。

---

## 十一、HTML 文档解析
HTML 常见来源：

+ 企业官网
+ 技术文档
+ 内部 Wiki
+ 产品说明
+ 帮助中心
+ 在线知识库

### 11.1 使用 BeautifulSoup 解析
安装：

```plain
uv add beautifulsoup4 lxml langchain-core
```

创建 `loaders/html_loader.py`：

```python
from pathlib import Path

from bs4 import BeautifulSoup

from langchain_core.documents import Document


def load_html(file_path: str):
    path = Path(file_path)

    html = path.read_text(
        encoding="utf-8"
    )

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    # 移除无关内容
    for tag in soup.select(
        "script, style, nav, footer, header"
    ):
        tag.decompose()

    title = (
        soup.title.get_text(strip=True)
        if soup.title
        else path.stem
    )

    content = soup.get_text(
        separator="\n",
        strip=True,
    )

    document = Document(
        page_content=content,
        metadata={
            "source": path.name,
            "title": title,
            "document_type": "html",
        },
    )

    return [document]


if __name__ == "__main__":
    documents = load_html(
        "data/employee-handbook.html"
    )

    for document in documents:
        print(document.page_content)
        print(document.metadata)
```

### 11.2 HTML 解析的注意事项
简单 HTML：

```plain
HTML
  ↓
BeautifulSoup
  ↓
纯文本
```

复杂网页可能存在：

+ 页面导航
+ 动态内容
+ DOM 层级
+ 代码块
+ 表格
+ 图片
+ 页面结构
+ JavaScript 动态渲染

如果需要保留 HTML 标题结构，可以进一步使用：

```plain
HTMLHeaderTextSplitter
```

对于需要保留结构的 HTML 文档，可以考虑：

```plain
HTMLSemanticPreservingSplitter
```

企业知识库应优先保留标题、正文、表格与内容关联，而不是仅仅提取全部文本。

---

## 十二、扫描版 PDF 与 OCR
这是企业文档解析中的一个重要问题。

有些 PDF 不是文本 PDF，而是扫描图片。

例如：

```plain
扫描纸质合同
    ↓
PDF 图片
    ↓
没有可提取文本
```

使用 PyPDFLoader 可能返回：

```plain
page_content = ""
```

或者只有少量文本。

这时需要 OCR。

### 12.1 OCR 的基本流程
```plain
PDF
  ↓
PDF 页面渲染
  ↓
图片
  ↓
OCR
  ↓
文本
  ↓
Document
```

OCR 负责识别图片中的文字。

### 12.2 PyMuPDF + Tesseract OCR
安装：

```plain
uv add pymupdf pytesseract pillow langchain-core
```

系统安装 Tesseract：

```plain
brew install tesseract
```

创建 OCR 示例：

```python
from pathlib import Path

import fitz
import pytesseract

from PIL import Image

from langchain_core.documents import Document


def load_scanned_pdf(file_path: str):
    path = Path(file_path)

    pdf = fitz.open(path)

    documents = []

    for page_index, page in enumerate(pdf):
        pixmap = page.get_pixmap(
            dpi=200,
        )

        image_path = (
            f"/tmp/pdf_page_{page_index}.png"
        )

        pixmap.save(image_path)

        image = Image.open(image_path)

        text = pytesseract.image_to_string(
            image,
            lang="chi_sim+eng",
        )

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": path.name,
                    "page": page_index,
                    "document_type": "scanned_pdf",
                },
            )
        )

    pdf.close()

    return documents


if __name__ == "__main__":
    documents = load_scanned_pdf(
        "data/scanned-contract.pdf"
    )

    for document in documents:
        print(document.page_content)
```

注意：

OCR 需要配置对应语言包。

对于中文 OCR，需要安装中文语言数据。

### 12.3 企业 OCR 选型
| 方案 | 适用场景 |
| --- | --- |
| Tesseract | 本地 OCR、成本低 |
| PaddleOCR | 中文 OCR、复杂文字识别 |
| Docling | 文档结构解析、表格及版面处理 |
| Unstructured | 多格式文档解析 |
| MinerU | PDF、论文及复杂文档解析 |
| 云 OCR API | 高质量识别、快速集成 |


扫描 PDF 的 OCR 结果可能存在：

+ 错别字
+ 文字顺序错误
+ 表格错位
+ 数字识别错误
+ 章节丢失

因此，OCR 之后还需要进行文本质量检测和必要的人工校验。

---

## 十三、Document Cleaner：文档清洗
文档解析完成后，不建议直接向量化。

企业文档可能包含：

```plain
页眉
页脚
版权声明
重复标题
无效空白
乱码
重复段落
导航菜单
```

这些内容会影响后续检索。

### 13.1 创建 document_cleaner.py
```python
import re

from langchain_core.documents import Document


def clean_document(
    document: Document,
) -> Document:
    text = document.page_content

    # 去除空白行
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    # 去除连续空格
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    # 去除首尾空白
    text = text.strip()

    # 过滤无效内容
    if not text:
        return Document(
            page_content="",
            metadata=document.metadata,
        )

    return Document(
        page_content=text,
        metadata=document.metadata,
    )


def clean_documents(
    documents: list[Document],
) -> list[Document]:
    cleaned = []

    for document in documents:
        result = clean_document(document)

        if result.page_content:
            cleaned.append(result)

    return cleaned
```

注意：

清洗规则需要根据业务文档设计。

不能随意删除所有特殊字符、数字、标点或换行。

例如：

```plain
产品编号：A-100
合同编号：2026-001
版本号：V1.2.3
```

这些信息对于企业知识库可能非常重要。

---

## 十四、Metadata Enrichment：元数据增强
企业知识库需要保留文档来源与业务属性。

例如：

```json
{
  "source": "employee-handbook.pdf",
  "document_id": "doc_001",
  "department": "HR",
  "category": "policy",
  "tenant_id": "tenant_001",
  "version": "v1",
}
```

### 14.1 创建 metadata_enrichment.py
```python
from pathlib import Path

from langchain_core.documents import Document


def enrich_metadata(
    documents: list[Document],
    file_path: str,
    tenant_id: str,
    department: str,
    category: str,
):
    path = Path(file_path)

    enriched = []

    for document in documents:
        metadata = {
            **document.metadata,
            "source": path.name,
            "document_id": path.stem,
            "tenant_id": tenant_id,
            "department": department,
            "category": category,
            "file_type": path.suffix.lower(),
        }

        enriched.append(
            Document(
                page_content=document.page_content,
                metadata=metadata,
            )
        )

    return enriched
```

Metadata 作用：

+ 检索过滤
+ 文档溯源
+ 租户隔离
+ 部门权限
+ 文档管理
+ 数据更新
+ 审计
+ 引用展示

注意：

Metadata 不能仅依赖用户输入。

租户、部门、权限等字段应由服务端身份认证与业务数据确定。

---

## 十五、批量 Document Loader
企业知识库通常需要批量处理文件。

例如：

```plain
knowledge/
├── hr/
│   ├── employee-handbook.pdf
│   └── leave-policy.docx
├── devops/
│   ├── deployment.md
│   └── docker-guide.txt
└── product/
    └── product-faq.csv
```

需要统一：

```plain
文件识别
   ↓
Loader 选择
   ↓
Document
   ↓
清洗
   ↓
Metadata
   ↓
输出
```

### 15.1 创建 batch_loader.py
```python
from pathlib import Path

from langchain_community.document_loaders import (
PyPDFLoader,
Docx2txtLoader,
TextLoader,
CSVLoader,
)

from document_cleaner import clean_documents


def load_file(file_path: Path):
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(
            str(file_path),
        )

    elif suffix == ".docx":
        loader = Docx2txtLoader(
            str(file_path),
        )

    elif suffix in [".txt", ".md"]:
        loader = TextLoader(
            str(file_path),
            encoding="utf-8",
        )

    elif suffix == ".csv":
        loader = CSVLoader(
            str(file_path),
            encoding="utf-8",
        )

    else:
        raise ValueError(
            f"不支持的文件类型：{suffix}"
        )

    documents = loader.load()

    return clean_documents(documents)


def clean_documents(documents):
    return [
        document
        for document in documents
        if document.page_content.strip()
    ]


def load_directory(directory: str):
    root = Path(directory)

    documents = []

    supported_extensions = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
        ".csv",
    }

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in supported_extensions:
            continue

        try:
            loaded_documents = load_file(
                file_path
            )

            documents.extend(
                loaded_documents
            )

            print(
                f"成功解析：{file_path}"
                f" | Documents: {len(loaded_documents)}"
            )

        except Exception as error:
            print(
                f"解析失败：{file_path}"
                f" | Error: {error}"
            )

    return documents


if __name__ == "__main__":
    documents = load_directory(
        "data"
    )

    print(
        f"总共解析 {len(documents)} 条 Documents"
    )
```

这里需要注意：

`load_directory()` 只是一个简单批量解析示例。

真实企业项目需要进一步实现：

+ 文件类型检测
+ 解析任务队列
+ 任务状态管理
+ 文件大小限制
+ 超时处理
+ 解析失败重试
+ 错误日志
+ 文档去重
+ 版本管理
+ 幂等入库

---

## 十六、企业级 Document Loader Pipeline
推荐架构：

```plain
             文件上传
                ↓
         File Storage
                ↓
        File Type Detection
                ↓
         Document Loader
                ↓
       Document Extraction
                ↓
       OCR / Table Parsing
                ↓
        Document Cleaner
                ↓
      Metadata Enrichment
                ↓
        Document Validation
                ↓
          Text Splitter
                ↓
          Embedding
                ↓
        Vector Database
```

建议拆分模块：

```plain
DocumentService
    ├── FileUploadService
    ├── DocumentLoaderFactory
    ├── PDFLoaderService
    ├── WordLoaderService
    ├── ExcelLoaderService
    ├── OCRService
    ├── DocumentCleaner
    ├── MetadataService
    └── DocumentValidationService
```

企业级系统不要将文件上传、解析、切分、Embedding、入库全部放在同一个 HTTP 请求中同步执行。

建议：

```plain
上传文件
   ↓
创建解析任务
   ↓
后台任务处理
   ↓
解析完成
   ↓
Chunking
   ↓
Embedding
   ↓
Vector Store
   ↓
更新任务状态
```

---

## 十七、企业文档解析常见问题
### 17.1 为什么 PDF 解析结果为空？
可能原因：

+ PDF 是扫描图片
+ PDF 没有文本层
+ 字体编码异常
+ PDF 加密
+ 文档损坏

解决：

+ OCR
+ PyMuPDF
+ Docling
+ Unstructured
+ 专业文档解析服务

### 17.2 为什么 Excel 不应该简单全部转换为字符串？
因为 Excel 可能包含：

+ 多级表头
+ 多 Sheet 关联
+ 业务规则
+ 表格关系
+ 计算公式

简单转换可能丢失业务结构。

### 17.3 为什么 Metadata 必须保留？
因为企业知识库不仅需要回答问题，还需要：

+ 显示来源
+ 定位原始文件
+ 定位页码
+ 过滤部门
+ 控制权限
+ 文档版本管理

### 17.4 为什么解析完成后不能直接 Embedding？
因为原始文档可能包含：

+ 无关内容
+ 重复页眉页脚
+ 乱码
+ 空文本
+ 错误识别
+ 不合理的结构

需要先进行清洗和切分。

---

## 十八、本章实战验收
```plain
[ ] 理解 LangChain Document
[ ] 使用 PyPDFLoader
[ ] 使用 Docx2txtLoader
[ ] 使用 TextLoader
[ ] 使用 CSVLoader
[ ] 使用 JSONLoader
[ ] 实现 Excel Loader
[ ] 实现 HTML Loader
[ ] 理解 OCR
[ ] 实现 Document Cleaner
[ ] 实现 Metadata Enrichment
[ ] 实现批量文件解析
[ ] 实现文件类型识别
[ ] 理解企业 Document Pipeline
```

最终项目：

```plain
document-loader-demo/
├── data/
├── loaders/
│   ├── pdf_loader.py
│   ├── word_loader.py
│   ├── markdown_loader.py
│   ├── csv_loader.py
│   ├── excel_loader.py
│   ├── json_loader.py
│   └── html_loader.py
├── document_cleaner.py
├── metadata_enrichment.py
├── batch_loader.py
└── main.py
```

---

## 十九、本章总结
企业 Document Loader 的核心职责：

```plain
多格式文件
    ↓
统一 Document
    ↓
文本提取
    ↓
内容清洗
    ↓
Metadata
    ↓
Document Validation
    ↓
Chunking
```

本章重点：

+ LangChain Document
+ Document Loader
+ PDF / Word / Excel / Markdown / HTML
+ OCR
+ Document Cleaner
+ Metadata Enrichment
+ Batch Loader
+ 企业文档解析 Pipeline

### 官方参考文档
1. LangChain Document Loaders  
[https://docs.langchain.com/oss/python/integrations/document_loaders](https://docs.langchain.com/oss/python/integrations/document_loaders)
2. LangChain Document Loaders Reference  
[https://reference.langchain.com/python/langchain-community/document_loaders](https://reference.langchain.com/python/langchain-community/document_loaders)
3. PyPDFLoader  
[https://reference.langchain.com/python/langchain-community/document_loaders/pdf/PyPDFLoader](https://reference.langchain.com/python/langchain-community/document_loaders/pdf/PyPDFLoader)
4. Docx2txtLoader  
[https://reference.langchain.com/python/langchain-community/document_loaders/word_document/Docx2txtLoader](https://reference.langchain.com/python/langchain-community/document_loaders/word_document/Docx2txtLoader)
5. LangChain Document  
[https://reference.langchain.com/python/langchain-core/documents/base/Document](https://reference.langchain.com/python/langchain-core/documents/base/Document)

** **
