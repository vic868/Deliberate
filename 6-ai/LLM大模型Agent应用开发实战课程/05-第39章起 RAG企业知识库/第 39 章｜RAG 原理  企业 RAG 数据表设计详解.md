## 一、为什么企业级 RAG 需要设计这些数据表？
在学习 RAG 的时候，很多同学会认为，只需要把文档切分成 Chunk，再生成 Embedding 向量，存到向量数据库中，就完成了整个知识库的建设。

实际上，这只是 RAG 的一部分。

如果只是做一个简单的 Demo，我们确实可以把文档切分、向量化、检索和问答全部写在一个脚本里。

但是真正的企业级 RAG 系统，还需要考虑很多问题：

+ 用户上传的文档如何管理？
+ 不同企业、不同租户之间如何隔离知识？
+ 一份文档切分之后，如何知道每个 Chunk 属于哪份文档？
+ 文档更新之后，如何重新生成向量？
+ 用户提出的问题检索到了哪些知识片段？
+ 如果 AI 回答错误，如何定位问题？
+ 用户对回答不满意，如何收集反馈并持续优化？

这些问题都需要通过合理的数据模型来解决。

因此，我们设计以下五张表：

| 表名 | 核心作用 |
| --- | --- |
| `knowledge_documents` | 管理知识库中的原始文档 |
| `knowledge_chunks` | 保存文档切分之后的文本片段 |
| `knowledge_embeddings` | 保存文本片段对应的向量数据 |
| `knowledge_query_logs` | 记录用户提问、检索和回答过程 |
| `knowledge_feedbacks` | 记录用户对 AI 回答的评价和反馈 |


需要注意：目前课程给出的 SQL 只创建了前三类业务中的文档表、Chunk 表和查询日志表，还没有给出 `knowledge_embeddings`、`knowledge_feedbacks` 的建表语句。后面两张表会在本节中介绍设计思路。

---

## 二、先理解企业 RAG 的整体数据流转
在理解具体字段之前，我们先看一下这些表之间的关系。

```markdown
用户上传 PDF / Word / Markdown
          |
          v
knowledge_documents
文档登记、状态管理、版本管理
          |
          v
文档解析、清洗、文本切分
          |
          v
knowledge_chunks
保存每个文本片段
          |
          v
Embedding 模型生成向量
          |
          v
knowledge_embeddings
保存向量及其关联关系
          |
          v
    用户提出问题
          |
          v
向量检索 / 混合检索 / Rerank
          |
          v
knowledge_query_logs
记录问题、召回结果、回答及耗时
          |
          v
      用户评价回答
          |
          v
knowledge_feedbacks
保存满意度和具体反馈
```

这里有一个非常重要的设计思想：

**文档管理、文本管理、向量管理、查询记录和用户反馈，是五类不同的业务职责，不应该全部混在一张表中。**

这样做有几个好处：

1. 职责清晰，后续维护更容易。
2. 文档更新时，可以独立管理 Chunk 和向量的重新生成。
3. 检索失败时，可以根据查询日志定位问题。
4. 可以根据用户反馈优化切分策略、检索策略和 Prompt。
5. 支持多租户、权限控制和后续的企业级扩展。

---

# 三、knowledge_documents：知识文档表
## 3.1 这张表是做什么的？
`knowledge_documents` 用来管理知识库中的原始文档。

可以把它理解为企业知识库中的一份份文件档案。

例如，企业上传了以下资料：

+ 员工手册.pdf
+ 产品使用说明.docx
+ 售后服务规范.md
+ 企业内部规章制度.pdf

每上传一份文档，就可以在 `knowledge_documents` 中创建一条记录。

需要注意：这张表主要保存文档的元数据，并不一定直接保存文件二进制内容。原始文件通常存储在本地文件系统或对象存储中，例如 MinIO、阿里云 OSS 等，数据库通过 `source_uri` 记录文件位置。

## 3.2 字段逐个解释
### 1. id
```plain
id BIGSERIAL PRIMARY KEY
```

**作用：文档的唯一标识。**

+ `BIGSERIAL`：PostgreSQL 中用于生成自增整数主键的类型。
+ `PRIMARY KEY`：表示该字段是主键，不能重复，也不能为空。

例如：

| id | title |
| --- | --- |
| 1 | 员工手册.pdf |
| 2 | 产品使用说明.docx |
| 3 | 售后服务规范.md |


当系统需要查询某一份文档时，可以通过 `id` 精确定位。

例如，查询 ID 为 1 的文档：

```plsql
SELECT *
FROM knowledge_documents
WHERE id = 1;
```

### 2. tenant_id
```plsql
tenant_id VARCHAR(128) NOT NULL
```

**作用：标识这份文档属于哪个租户。**

企业级 AI 系统经常采用多租户架构。

例如：

+ A 公司使用自己的知识库。
+ B 公司使用自己的知识库。
+ 两家公司的知识不能互相访问。

可以这样理解：

| id | tenant_id | title |
| --- | --- | --- |
| 1 | company_a | 员工手册.pdf |
| 2 | company_a | 产品说明书.pdf |
| 3 | company_b | 员工手册.pdf |


虽然 A 公司和 B 公司都上传了员工手册，但是它们属于不同的租户，是两份独立的数据。

查询 A 公司的文档时：

```plsql
SELECT *
FROM knowledge_documents
WHERE tenant_id = 'company_a';
```

为什么这个字段重要？

因为企业级 RAG 必须考虑数据隔离。

不过，需要注意：**仅仅添加 **`**tenant_id**`** 字段并不代表已经实现了安全隔离。**

实际开发中，还需要在后端接口、数据库查询、向量检索和权限校验中统一实施租户隔离，不能直接信任前端传入的租户 ID。

### 3. title
```plsql
title VARCHAR(255) NOT NULL
```

**作用：保存文档名称。**

例如：

```plain
员工手册.pdf
产品使用说明.docx
2026年售后服务规范.md
```

这个字段主要用于：

+ 知识库文档列表展示。
+ 文档搜索。
+ 文档详情页展示。
+ 日志排查。
+ 帮助用户识别检索结果的来源。

为什么需要单独保存标题？

因为在实际业务中，用户往往需要知道某段答案来自哪份文档，而不只是看到一段文本。

### 4. source_type
```plain
source_type VARCHAR(64) NOT NULL
```

**作用：记录文档的来源类型。**

企业知识不一定全部来自用户上传的文件，还可能来自其他系统。

例如：

```plain
upload       用户手动上传
web          网页抓取
notion       Notion 知识源
feishu       飞书文档
database     数据库同步
api          外部 API 导入
```

具体枚举值可以由项目自行定义。

这个字段有什么价值？

假设企业接入了飞书文档和本地文件上传两种数据源，后续需要排查同步失败的问题，就可以通过 `source_type` 筛选数据。

例如：

```plsql
SELECT *
FROM knowledge_documents
WHERE tenant_id = 'company_a'
  AND source_type = 'feishu';
```

### 5. source_uri
```plsql
source_uri TEXT
```

**作用：记录原始文档的存储位置或来源地址。**

例如：

```plsql
s3://company-a/knowledge/employee-handbook.pdf
https://docs.example.com/product-manual
/var/app/uploads/employee-handbook.pdf
```

实际项目中，更推荐使用对象存储地址、文件存储 Key 或受控的文件 ID，而不是把服务器本地绝对路径作为长期稳定的文件标识。

这个字段可以用于：

+ 下载或重新解析原始文件。
+ 文档更新后重新构建索引。
+ 排查文件解析失败的问题。
+ 根据源文件进行增量同步。

需要注意：如果文件地址包含访问凭证或临时签名，不要直接写入长期日志或暴露给前端。

### 6. file_type
```plsql
file_type VARCHAR(32)
```

**作用：记录文档的文件类型。**

例如：

```plain
pdf
docx
md
txt
html
xlsx
```

为什么需要这个字段？

因为不同文件类型的解析方式不同。

例如：

+ PDF：需要解析 PDF 文本，部分文件还需要 OCR。
+ DOCX：需要提取 Word 文档中的段落和表格。
+ Markdown：可以直接解析标题、段落和代码块。
+ XLSX：需要提取工作表、行列数据等。

系统可以根据 `file_type` 选择对应的解析器。

```python
def parse_document(file_type: str, file_path: str):
    if file_type == "pdf":
        return parse_pdf(file_path)

    if file_type == "docx":
        return parse_docx(file_path)

    if file_type == "md":
        return parse_markdown(file_path)

    raise ValueError(f"暂不支持的文件类型: {file_type}")
```

这只是一个简化示例，实际项目中还需要考虑文件大小、编码、异常处理和安全检查。

### 7. status
```plsql
status VARCHAR(32) NOT NULL
```

**作用：记录文档当前的处理状态。**

企业级 RAG 不只是上传文件，还要经历解析、切分、向量化和索引构建等步骤。

可以定义以下状态：

| 状态 | 含义 |
| --- | --- |
| pending | 等待处理 |
| processing | 正在处理 |
| completed | 处理完成 |
| failed | 处理失败 |
| disabled | 已停用 |


例如：

```markdown
用户上传文件
    ↓
pending
    ↓
processing
    ↓
completed
```

如果解析失败，则进入 `failed` 状态。

为什么需要状态字段？

因为文档处理通常是异步任务。用户上传文件后，系统可能需要几十秒甚至更长时间才能完成解析和向量化。

前端可以通过接口查询状态，展示：

```plain
员工手册.pdf    处理中
产品说明书.pdf  已完成
售后规范.pdf    处理失败
```

需要注意：文档状态最好有明确的状态流转规则。例如，只有完成必要的解析、向量生成和索引写入后，才将文档标记为可检索状态。

### 8. version
```plsql
version VARCHAR(64)
```

**作用：记录文档的版本信息。**

例如：

```plain
v1
v2
2026-09
2026-12
```

假设企业的售后服务规范发生了变化。

旧版本规定：7 天内可以申请退货。

新版本规定：30 天内可以申请退货。

如果系统不管理文档版本，旧版本的内容可能仍然存在于向量索引中，导致 AI 检索到过期规则。

版本字段可以辅助系统识别文档的版本，支持：

+ 文档更新。
+ 版本追踪。
+ 历史版本管理。
+ 索引重建。
+ 过期知识排查。

不过，当前这个字段只是一个版本标识。真正的版本管理通常还需要设计版本记录、当前有效版本和版本切换机制。

### 9. created_by
```plain
created_by VARCHAR(128)
```

**作用：记录文档的创建者或上传者。**

例如：

```plain
user_1001
admin_001
```

这个字段主要用于：

+ 记录操作人。
+ 展示文档上传者。
+ 排查问题。
+ 实现文档管理权限。
+ 支持审计。

例如，企业管理员可以查看某份文档是谁上传的。

需要注意：这里保存的是用户标识，不一定是用户姓名。实际项目可以关联用户表查询姓名。

### 10. created_at
```plsql
created_at TIMESTAMP NOT NULL DEFAULT NOW()
```

**作用：记录文档创建时间。**

`DEFAULT NOW()` 表示插入记录时，如果没有显式指定时间，就使用数据库当前时间。

例如：

```plain
2026-10-12 09:00:00
```

这个字段可以用于：

+ 按时间排序。
+ 查询最近上传的文档。
+ 统计每天新增的知识文档。
+ 排查历史数据问题。

### 11. updated_at
```plsql
updated_at TIMESTAMP NOT NULL DEFAULT NOW()
```

**作用：记录文档最后更新时间。**

例如，文档最初上传于 10 月 1 日，10 月 12 日进行了更新。

此时：

```plain
created_at = 2026-10-01 10:00:00
updated_at = 2026-10-12 09:00:00
```

这两个字段的区别是：

+ `created_at`：记录什么时候创建。
+ `updated_at`：记录最后一次修改的时间。

需要特别注意：`DEFAULT NOW()` 只会在插入记录时提供默认值，后续执行 `UPDATE` 时不会自动刷新 `updated_at`。需要通过业务代码、数据库触发器等方式更新它。

---

# 四、knowledge_chunks：知识切片表
## 4.1 这张表是做什么的？
`knowledge_chunks` 用于保存文档经过解析、清洗和切分之后得到的文本片段。

这是 RAG 中非常重要的一张表。

为什么不能直接把整份 PDF 转成向量？

因为一份企业文档可能有几十页、几百页，甚至上千页。如果直接把整份文档当成一个整体，通常会遇到以下问题：

1. 文本太长，超出 Embedding 模型的输入限制。
2. 一份文档包含多个主题，难以精准检索。
3. 召回的内容太多，会增加大模型的上下文成本。
4. 无法精准定位答案对应的原始段落。

所以，我们通常会将文档拆成多个 Chunk。

例如，原始文档：

```markdown
《企业员工手册》

第一章：考勤制度
员工应当按照规定时间上下班。

第二章：请假制度
员工请假需要提前提交申请，并经过直属领导审批。

第三章：报销制度
员工报销需要提交发票和相关证明材料。
```

切分后可以得到：

```markdown
Chunk 0：员工应当按照规定时间上下班。

Chunk 1：员工请假需要提前提交申请，并经过直属领导审批。

Chunk 2：员工报销需要提交发票和相关证明材料。
```

每个 Chunk 都可以单独进行向量化、检索和排序。

## 4.2 字段逐个解释
### 1. id
```plsql
id BIGSERIAL PRIMARY KEY
```

**作用：每个 Chunk 的唯一标识。**

例如：

| id | document_id | chunk_index |
| --- | --- | --- |
| 101 | 1 | 0 |
| 102 | 1 | 1 |
| 103 | 1 | 2 |
| 104 | 2 | 0 |


即使多个 Chunk 来自同一份文档，每个 Chunk 也拥有独立的 ID。

检索时，系统可以通过 Chunk ID 找到具体文本。

### 2. tenant_id
```plsql
tenant_id VARCHAR(128) NOT NULL
```

**作用：标识 Chunk 所属的租户。**

为什么文档表已经有 `tenant_id`，Chunk 表还需要保存？

因为检索 Chunk 时，系统经常直接查询 Chunk 表，或者通过向量数据库进行相似度搜索。

如果 Chunk 自身就有租户标识，可以更方便地实施租户过滤，避免不同企业的知识混在一起。

例如：

```plsql
SELECT id, content
FROM knowledge_chunks
WHERE tenant_id = 'company_a';
```

这里需要强调：数据库和向量数据库中的租户过滤都要执行，不能仅在最终答案生成时才检查权限。

### 3. document_id
```plsql
document_id BIGINT NOT NULL
```

**作用：关联所属的原始文档。**

例如：

```markdown
knowledge_documents
        |
        | id = 1
        |
        v
knowledge_chunks
document_id = 1
```

假设文档 ID 为 1，切分后生成了 100 个 Chunk，那么这 100 条记录的 `document_id` 都是 1。

这个字段用于：

+ 查询某份文档的所有 Chunk。
+ 删除某份文档对应的知识片段。
+ 文档更新后重新构建索引。
+ 检索结果回溯到原始文档。
+ 展示回答的知识来源。

例如：

```plsql
SELECT *
FROM knowledge_chunks
WHERE document_id = 1
ORDER BY chunk_index;
```

这里有一个数据库设计细节：当前 SQL 只是声明了 `document_id BIGINT NOT NULL`，还没有声明外键约束。

如果希望数据库保证文档和 Chunk 之间的引用关系，可以进一步增加：

```plsql
FOREIGN KEY (document_id)
REFERENCES knowledge_documents(id)
```

对于多租户系统，还要结合删除策略和租户一致性约束进行设计。

### 4. chunk_index
```plsql
chunk_index INT NOT NULL
```

**作用：记录 Chunk 在原始文档中的切分顺序。**

例如：

| id | document_id | chunk_index | content |
| --- | --- | --- | --- |
| 101 | 1 | 0 | 第一段内容 |
| 102 | 1 | 1 | 第二段内容 |
| 103 | 1 | 2 | 第三段内容 |


为什么不直接依赖 `id` 判断顺序？

因为 ID 主要用于唯一标识，不一定能准确反映文档内部的逻辑顺序。重新切分、批量导入或者并发写入时，更应该使用明确的顺序字段。

这个字段可以用于：

+ 按原始顺序还原 Chunk。
+ 查看某个 Chunk 的前后文。
+ 调试切分策略。
+ 处理相邻 Chunk 的上下文拼接。

例如：

```plsql
SELECT chunk_index, content
FROM knowledge_chunks
WHERE document_id = 1
ORDER BY chunk_index;
```

### 5. content
```plsql
content TEXT NOT NULL
```

**作用：保存切分之后的实际文本内容。**

例如：

```plain
员工请假需要提前提交申请，并经过直属领导审批。
```

这是 RAG 检索后提供给大模型的重要上下文。

典型流程是：

```plain
用户提问
   ↓
问题向量化
   ↓
向量检索找到相关 Chunk
   ↓
读取 content
   ↓
将相关内容放进 Prompt
   ↓
大模型生成回答
```

例如，用户提问：

```plain
员工请假需要经过谁审批？
```

检索系统找到对应的 Chunk：

```plain
员工请假需要提前提交申请，并经过直属领导审批。
```

随后将这段文本作为上下文提供给大模型。

注意：`content` 保存的是文本内容，不是向量。向量通常单独存储在向量数据库中，或者存储在专门的向量字段中。

### 6. metadata
```plsql
metadata JSONB
```

**作用：保存 Chunk 的扩展元数据。**

`JSONB` 是 PostgreSQL 提供的 JSON 二进制存储类型，适合保存结构化的扩展信息。

例如：

```json
{
  "page": 12,
  "section": "请假制度",
  "heading": "请假审批流程",
  "source": "employee-handbook.pdf",
  "language": "zh-CN"
}
```

这些字段不一定每个 Chunk 都相同，因此使用 JSONB 可以提高扩展灵活性。

典型用途包括：

+ 记录 PDF 页码。
+ 记录所属章节。
+ 记录标题层级。
+ 记录文档来源。
+ 保存自定义标签。
+ 支持基于元数据的检索过滤。

例如，想要查询第 12 页的 Chunk：

```plsql
SELECT *
FROM knowledge_chunks
WHERE metadata ->> 'page' = '12';
```

为什么元数据对企业级 RAG 很重要？

因为企业检索不仅需要判断文本语义是否相似，还经常需要结合业务条件进行过滤。

例如：

```plain
查询：2026 年最新的售后退款规则
```

检索系统可能需要同时考虑：

+ 文本语义相似度。
+ 文档版本。
+ 生效时间。
+ 所属业务部门。
+ 用户的数据访问权限。

其中部分信息就可以通过元数据支持。

不过，权限信息不能只依赖任意可编辑的 JSON 字段，关键权限规则应该由可信的后端系统维护。

### 7. token_count
```plsql
token_count INT
```

**作用：记录当前 Chunk 的 Token 数量。**

Token 是大模型处理文本时使用的基本计量单位。

它不完全等于汉字数量，也不完全等于英文单词数量。

例如：

```plain
员工请假需要经过谁审批？
```

这段文本的 Token 数量取决于使用的分词器或模型，不能简单地认为一个汉字就是一个 Token。

为什么需要记录 `token_count`？

第一，控制 Chunk 大小。

例如，希望每个 Chunk 尽量控制在一定的 Token 范围内，避免过长或过短。

第二，控制大模型上下文长度。

检索到多个 Chunk 后，需要判断它们加起来是否超出模型上下文窗口。

第三，控制调用成本。

输入 Token 数量通常会影响模型调用成本。

第四，优化检索结果拼接。

当召回结果较多时，可以根据 Token 预算选择最有价值的片段。

需要注意：`token_count` 应尽量使用与目标模型或所选分词器匹配的方式计算，不能只用字符串长度代替。

### 8. created_at
```plsql
created_at TIMESTAMP NOT NULL DEFAULT NOW()
```

**作用：记录 Chunk 的创建时间。**

可以用于：

+ 排查知识入库时间。
+ 统计切分结果。
+ 定位文档更新后是否生成了新 Chunk。
+ 排查索引构建任务。

例如，文档于 10 月 12 日重新切分，可以通过时间查看新生成的 Chunk。

---

# 五、knowledge_embeddings：知识向量表
## 5.1 这张表是做什么的？
前面我们已经有了文档表和 Chunk 表。

但仅仅保存文本，还不能直接完成向量相似度检索。

RAG 通常会调用 Embedding 模型，把文本转换成一个数值向量。

例如：

```plain
原始文本：
 员工请假需要经过谁审批？
        ↓  
  Embedding 模型
向量：
[0.12, -0.08, 0.31, ..., 0.17]
```

这里的数值仅用于示意，并不是实际模型输出。

向量可以用于衡量不同文本之间的语义相似程度。

例如：

```plain
问题 A：员工请假需要经过谁审批？
问题 B：请假流程中需要哪个领导批准？
```

两句话的字面表达不同，但语义接近。向量检索有机会找到与问题相关的知识片段。

## 5.2 为什么单独设计 knowledge_embeddings？
一种简单方案是把向量直接放进 `knowledge_chunks`。

但是，独立的向量表也有一些优点：

+ 将文本数据和向量数据分开管理。
+ 记录使用的 Embedding 模型。
+ 支持模型升级和重新向量化。
+ 支持一个 Chunk 对应多个向量版本。
+ 更方便扩展向量索引策略。

需要注意：独立向量表不是所有项目的必选方案。如果项目直接使用 PostgreSQL + pgvector，也可以在 Chunk 表中增加向量字段。对于专门的向量数据库，也可能完全不需要创建同名的 PostgreSQL 表。

## 5.3 建议的表结构
下面是一个适用于课程演示的简化设计：

```plsql
CREATE TABLE knowledge_embeddings (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(128) NOT NULL,
  chunk_id BIGINT NOT NULL,
  embedding_model VARCHAR(128) NOT NULL,
  embedding_version VARCHAR(64),
  vector_dimension INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

这里先不放入具体的向量字段，是因为向量的实际存储方式取决于底层方案。

例如：

+ 使用 pgvector，可以增加 `vector(1024)` 等字段，维度必须与实际模型输出一致。
+ 使用独立向量数据库，可以将向量保存在外部系统中，在本表保存关联 ID、模型信息等元数据。

### 字段说明
| 字段 | 作用 |
| --- | --- |
| `id` | 向量记录的唯一标识 |
| `tenant_id` | 所属租户，用于数据隔离 |
| `chunk_id` | 关联原始文本 Chunk |
| `embedding_model` | 记录生成向量的模型名称 |
| `embedding_version` | 记录模型或向量生成版本 |
| `vector_dimension` | 记录向量维度 |
| `created_at` | 记录向量生成时间 |


例如：

```json
chunk_id = 101
embedding_model = Qwen3-Embedding
vector_dimension = 1024
```

这表示 Chunk 101 对应的文本由指定 Embedding 模型转换为一个 1024 维向量。这里的维度只是示例，实际值应以所使用模型的配置和输出为准。

还要注意：不同模型的向量空间通常不能直接混用。切换 Embedding 模型时，一般需要重新生成对应的文档向量，并确保查询向量和文档向量使用兼容的模型与配置。

---

# 六、knowledge_query_logs：知识查询日志表
## 6.1 这张表是做什么的？
`knowledge_query_logs` 用于记录用户每一次知识库查询的过程和结果。

前三张表主要解决的是：

```plain
知识从哪里来？
知识如何切分？
文本如何向量化？
```

查询日志解决的是另一个问题：

**用户问了什么，系统检索到了什么，最后回答了什么，整个过程耗时多久？**

例如：

```plain
用户问题：
员工请假需要经过谁审批？

系统召回：
员工手册第 12 页的相关 Chunk。

模型回答：
员工请假需要经过直属领导审批。

耗时：
850 ms
```

这些数据可以帮助开发人员排查 RAG 的问题。

例如：

+ 为什么没有检索到正确知识？
+ 为什么模型回答与原文不一致？
+ 为什么某次查询耗时很长？
+ 为什么同一个问题多次回答不同？
+ 某次回答究竟使用了哪些知识片段？

## 6.2 字段逐个解释
### 1. id
```plsql
id BIGSERIAL PRIMARY KEY
```

**作用：每次查询记录的唯一标识。**

每次用户发起一次查询，就可以生成一条新的日志记录。

例如：

| id | question |
| --- | --- |
| 1001 | 员工请假需要谁审批？ |
| 1002 | 报销需要哪些材料？ |
| 1003 | 退款政策是什么？ |


后续可以通过 ID 查询具体的请求记录。

### 2. tenant_id
```plain
tenant_id VARCHAR(128) NOT NULL
```

**作用：标识本次查询属于哪个租户。**

企业级系统需要知道某次查询来自哪家公司。

这个字段可用于：

+ 按租户统计查询次数。
+ 统计不同企业的知识库使用情况。
+ 分析不同租户的检索效果。
+ 进行查询日志的数据隔离。

日志本身也可能包含企业机密，因此同样需要权限控制。

### 3. user_id
```plsql
user_id VARCHAR(128)
```

**作用：记录发起查询的用户。**

例如：

```plain
user_1001
user_1002
admin_001
```

这个字段主要用于：

+ 查询某个用户的历史问题。
+ 分析用户的常见需求。
+ 处理用户反馈。
+ 排查特定用户的查询问题。

为什么没有设置 `NOT NULL`？

当前设计允许某些没有登录的匿名查询，或者某些无法确定用户身份的请求。

如果业务要求必须登录，可以改成非空约束，并在服务端从认证上下文中获取用户 ID。

不要直接信任客户端提交的 `user_id`，否则用户可能伪造其他用户的身份。

### 4. question
```plain
question TEXT NOT NULL
```

**作用：保存用户最初提出的问题。**

例如：

```plain
员工请假需要经过谁审批？
```

为什么要保留原始问题？

因为用户提出的问题可能比较口语化、不完整，甚至存在错别字。

系统可能会对问题进行改写，但原始问题可以用于：

+ 还原用户真实输入。
+ 分析用户提问习惯。
+ 评估问题改写效果。
+ 对比改写前后的检索结果。
+ 复现线上问题。

例如：

```plain
原始问题：
那个报销怎么弄？

改写问题：
企业员工报销的申请流程和所需材料是什么？
```

保留两者可以帮助开发人员判断问题改写是否有效。

### 5. rewritten_question
```plain
rewritten_question TEXT
```

**作用：保存经过 Query Rewriting 处理后的问题。**

Query Rewriting，也就是查询改写。

它通常用于将用户不完整、模糊或口语化的问题，转换成更适合检索的表达。

例如：

原始问题：

```plain
那这个要找谁？
```

如果结合对话上下文，系统可能改写为：

```plain
员工申请报销需要由哪个部门或负责人审批？
```

这样可以减少指代不清、信息缺失对检索的影响。

不过，并不是每个 RAG 系统都需要问题改写。

如果项目使用了 Query Rewriting，就可以记录改写后的内容；如果没有使用，这个字段可以为空。

### 6. retrieved_chunk_ids
```plain
retrieved_chunk_ids JSONB
```

**作用：记录本次检索召回的 Chunk ID。**

例如：

```plain
[101, 105, 109]
```

这表示系统在本次检索中返回了 ID 为 101、105、109 的三个文本片段。

为什么需要记录？

因为检索结果是影响 RAG 回答质量的关键因素。

当 AI 回答错误时，开发人员首先可以检查：

1. 是否检索到了正确的知识片段？
2. 召回的结果是否包含过期内容？
3. 是否召回了无关知识？
4. 正确知识是否被排在较低的位置？
5. 最终提供给大模型的上下文是否完整？

需要注意：如果只保存 ID，那么未来 Chunk 被删除后，历史日志就可能无法还原当时的完整内容。

在更完善的设计中，可以同时记录检索排名、相似度分数、检索策略和必要的结果快照。

例如：

```json
[
  {
    "chunk_id": 101,
    "rank": 1,
    "score": 0.92
  },
  {
    "chunk_id": 105,
    "rank": 2,
    "score": 0.86
  }
]
```

这里的分数仅为示意，实际含义取决于检索引擎。不同系统中的距离、相似度和重排分数不能简单地视为同一种指标。

### 7. answer
```plain
answer TEXT
```

**作用：保存最终返回给用户的 AI 回答。**

例如：

```plain
根据员工手册，员工请假需要提前提交申请，并经过直属领导审批。
```

这个字段可以用于：

+ 复现用户看到的回答。
+ 评估答案质量。
+ 分析模型幻觉。
+ 检查回答是否有知识依据。
+ 为人工审核提供上下文。

实际项目还可以考虑记录引用来源、模型名称、Prompt 版本等信息。

另外，如果系统使用 SSE 流式输出，可以在生成完成后保存最终答案；对于中途断开的请求，则可以根据业务要求记录部分输出和终止状态。

由于答案可能包含个人信息、企业机密或其他敏感内容，需要设置合理的访问权限、保留期限和脱敏规则。

### 8. latency_ms
```plain
latency_ms INT
```

**作用：记录本次查询的耗时，单位是毫秒。**

例如：

```plain
850
```

表示本次请求耗时约 850 毫秒。

这个字段可以用于：

+ 统计平均响应时间。
+ 分析 P95、P99 延迟。
+ 排查性能瓶颈。
+ 对比不同模型的响应速度。
+ 观察检索和生成的性能变化。

例如，某个时间段内查询耗时持续增加，就可以进一步拆解：

```plain
请求总耗时
  ├── 问题改写耗时
  ├── Embedding 耗时
  ├── 向量检索耗时
  ├── Rerank 耗时
  └── 大模型生成耗时
```

当前字段只记录总耗时。如果希望实现完整的性能监控，建议额外记录各阶段耗时，而不是只依赖 `latency_ms`。

### 9. created_at
```plsql
created_at TIMESTAMP NOT NULL DEFAULT NOW()
```

**作用：记录本次查询发生的时间。**

例如：

```plain
2026-10-12 09:00:00
```

可以用于：

+ 查询历史记录。
+ 按时间统计查询量。
+ 分析高峰时段。
+ 排查某个时间段的故障。
+ 观察系统上线前后的效果变化。

---

# 七、knowledge_feedbacks：知识反馈表
## 7.1 这张表是做什么的？
`knowledge_feedbacks` 用于收集用户对 AI 回答的评价。

前面已经记录了：

+ 用户问了什么。
+ 系统检索到了哪些 Chunk。
+ AI 最终回答了什么。
+ 请求耗时多久。

但这些信息还不能完全说明：**用户是否认可这个答案。**

例如：

```plain
问题：
员工请假需要经过谁审批？

AI 回答：
需要经过直属领导审批。

用户反馈：
有帮助。
```

另一种情况：

```plain
问题：
公司的退款政策是什么？

AI 回答：
退款期限为 7 天。

用户反馈：
答案过期了，应该是 30 天。
```

如果系统能持续收集这些反馈，就可以逐步优化知识库和检索流程。

## 7.2 建议的表结构
```plain
CREATE TABLE knowledge_feedbacks (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    query_log_id BIGINT NOT NULL,
    user_id VARCHAR(128),
    rating SMALLINT,
    feedback_type VARCHAR(32),
    comment TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## 7.3 字段说明
| 字段 | 作用 |
| --- | --- |
| `id` | 反馈记录的唯一标识 |
| `tenant_id` | 所属租户 |
| `query_log_id` | 关联本次查询日志 |
| `user_id` | 提交反馈的用户 |
| `rating` | 用户评分，例如 1～5 分 |
| `feedback_type` | 反馈类型，例如有帮助、无帮助、答案错误 |
| `comment` | 用户填写的具体意见 |
| `created_at` | 反馈提交时间 |


### query_log_id 有什么作用？
它用来关联用户的反馈与具体的一次 AI 回答。

例如：

```markdown
knowledge_query_logs
id = 1001
question = 员工请假需要谁审批？
answer = 需要直属领导审批。
           |
           v
knowledge_feedbacks
query_log_id = 1001
rating = 5
feedback_type = helpful
```

这样，当某条回答被用户标记为错误时，开发人员可以通过查询日志查看当时召回的知识、生成的答案和请求耗时。

### rating 和 feedback_type 有什么区别？
`rating` 用于表达评分。

例如：

```plain
1 分：非常不满意
2 分：不满意
3 分：一般
4 分：满意
5 分：非常满意
```

`feedback_type` 用于表达反馈的具体类别。

例如：

```plain
helpful          回答有帮助
not_helpful      回答没有帮助
incorrect        回答错误
outdated         知识已经过期
irrelevant       回答与问题无关
```

这两个字段可以结合使用。

不过，以上分类只是示例，实际项目需要定义统一的枚举规范，并根据产品需求决定是否允许多次反馈、修改反馈或匿名反馈。

---

# 八、五张表之间如何建立关系？
从数据模型的角度来看，可以理解为以下关系：

```markdown
knowledge_documents
        |
        | 一份文档对应多个 Chunk
        v
knowledge_chunks
        |
        | 一个 Chunk 可以对应一个或多个向量记录
        v
knowledge_embeddings

knowledge_query_logs
        |
        | 一次查询可以关联多个召回 Chunk
        | 当前通过 JSONB 保存 Chunk ID
        |
        v
knowledge_feedbacks
        |
        | 一次查询可以关联多条反馈记录
        | 也可以通过业务约束限制为一条
```

这里有几个细节需要特别注意。

第一，`knowledge_chunks.document_id` 关联 `knowledge_documents.id`。

第二，`knowledge_embeddings.chunk_id` 关联 `knowledge_chunks.id`。

第三，`knowledge_feedbacks.query_log_id` 关联 `knowledge_query_logs.id`。

第四，当前的 `retrieved_chunk_ids` 使用 JSONB 保存多个 ID，因此并不是传统的关系型外键关联。

如果后续需要统计某个 Chunk 被召回的次数、分析它在不同问题中的排名，可以进一步设计查询与 Chunk 的关联表。

另外，当前五张表只是课程中的基础数据模型。真正落地时，还需要根据业务补充索引、外键、唯一约束、删除策略和数据保留策略。

---

# 九、结合一个真实业务场景理解整个过程
假设我们正在开发一个企业智能知识助手。

企业上传了一份《员工手册.pdf》。

## 第一步：登记文档
系统在 `knowledge_documents` 中写入：

```json
id = 1
tenant_id = company_a
title = 员工手册.pdf
source_type = upload
file_type = pdf
status = processing
version = v1
```

此时，系统知道有一份文档需要处理。

## 第二步：解析并切分
解析 PDF 后，系统得到多段文本，并保存到 `knowledge_chunks`。

```json
id = 101
tenant_id = company_a
document_id = 1
chunk_index = 0
content = 员工应当按照规定时间上下班。
```

```json
id = 102
tenant_id = company_a
document_id = 1
chunk_index = 1
content = 员工请假需要提前提交申请，并经过直属领导审批。
```

```json
id = 103
tenant_id = company_a
document_id = 1
chunk_index = 2
content = 员工报销需要提交发票和相关证明材料。
```

## 第三步：生成 Embedding
系统使用 Embedding 模型，把每个 Chunk 转换为向量，并保存向量及其关联信息。

此时，文档就可以进入后续的检索流程。

等所有必要的处理步骤成功完成后，再将文档状态更新为 `completed`。

## 第四步：用户提问
用户问：

```plain
员工请假需要经过谁审批？
```

系统执行：

```plain
问题改写（如果需要）
        ↓
生成查询向量
        ↓
向量检索
        ↓
召回 Chunk 102
        ↓
将 Chunk 内容提供给大模型
        ↓
生成最终答案
```

## 第五步：记录查询日志
系统将查询过程保存到 `knowledge_query_logs`：

```json
id = 1001
tenant_id = company_a
user_id = user_1001
question = 员工请假需要经过谁审批？
rewritten_question = 员工请假申请需要由谁审批？
retrieved_chunk_ids = [102]
answer = 员工请假需要经过直属领导审批。
latency_ms = 850
```

## 第六步：用户提交反馈
用户认为回答正确，点击“有帮助”。

系统在 `knowledge_feedbacks` 中写入：

```json
tenant_id = company_a
query_log_id = 1001
user_id = user_1001
rating = 5
feedback_type = helpful
comment = 回答准确
```

至此，一次完整的知识库问答就形成了数据闭环。

---

# 十、面试中如何介绍这套 RAG 数据库设计？
如果面试官问：

“你们企业级 RAG 系统的数据表是怎么设计的？”

可以这样回答：

我们主要围绕知识管理、检索和效果评估设计了五类数据表。

第一类是文档表 `knowledge_documents`，负责管理原始文档的元数据，包括租户、文档来源、文件类型、处理状态和版本信息。

第二类是 Chunk 表 `knowledge_chunks`，负责保存文档切分后的文本片段，同时保留文档关联关系、切分顺序、Token 数量和扩展元数据。

第三类是向量表 `knowledge_embeddings`，用于管理 Chunk 对应的 Embedding 信息。如果底层使用 pgvector，可以直接存储向量；如果使用独立向量数据库，则可以保存向量记录的关联 ID 和模型版本信息。

第四类是查询日志表 `knowledge_query_logs`，记录用户原始问题、改写后的问题、召回的 Chunk、最终回答和请求耗时，便于定位检索和生成阶段的问题。

第五类是反馈表 `knowledge_feedbacks`，记录用户对回答的评分和具体意见，为 RAG 的效果评估和持续优化提供数据。

在企业级设计中，我们还会重点考虑多租户隔离、文档版本更新、向量索引重建、权限过滤、日志审计和数据保留等问题。

这套设计的核心目标不是简单地保存文本和向量，而是让知识能够被管理、被检索、被追踪，并且能够持续优化。

---

#  