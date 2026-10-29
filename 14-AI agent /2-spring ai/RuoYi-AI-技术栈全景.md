---
tags:
  - ruoyi
  - spring-ai
  - tech-stack
  - llm
  - milvus
  - embedding
  - rag
  - function-calling
created: 2026-10-29
status: completed
source: ruoyi-chat 模块 AI 技术栈梳理
---

# RuoYi × Spring AI 技术栈全景

> 按 **分层架构** 组织，从基础设施 → 框架 → 模型服务 → 向量存储 → 工程化，每一层都标注 **版本 / 用途 / 关键类 / 配置锚点**。

---

## 架构分层图

```
┌──────────────────────────────────────────────────────────────────┐
│                       前端 & 通信                                │
│  Vue 3  │  SSE (Server-Sent Events)  │  REST API                │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                   控制层 (ruoyi-chat Controller)                │
│  ChatController    │    UploadFileController                    │
│  (SSE 流式对话)     │    (文件上传 → RAG 入库)                    │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                   业务编排层 (Service)                            │
│  ChatServiceImpl        │  AiChatServiceImpl (DB CRUD)          │
│  (RAG + 历史 + Tools)   │  DocumentIngestService (文件向量化)    │
└──────┬───────────────┬──────────────────────┬──────────────────┘
       │               │                      │
┌──────▼──────┐  ┌─────▼──────┐  ┌────────────▼─────────────────┐
│ Spring AI   │  │  Milvus    │  │  Embedding (DashScope)       │
│  ChatClient │  │  Service   │  │  DashScopeEmbeddingModel      │
│  + @Tools   │  │            │  │  (自实现 EmbeddingModel)      │
└──────┬──────┘  └─────┬──────┘  └────────────┬─────────────────┘
       │               │                      │
┌──────▼──────┐  ┌─────▼──────┐  ┌────────────▼─────────────────┐
│  LLM 大模型  │  │ Milvus     │  │ Apache Tika                  │
│  DeepSeek   │  │ 向量数据库  │  │ 文档解析 (PDF/Word/Excel)     │
│  V4 Flash   │  │ v2.4.1     │  │  + TokenTextSplitter 分块     │
└─────────────┘  └────────────┘  └──────────────────────────────┘
```

---

## 一、应用框架层

### 1. Spring AI —— AI 能力的胶水框架

| 属性 | 值 |
|------|-----|
| **GroupId** | `org.springframework.ai` |
| **ArtifactId** | `spring-ai-openai-spring-boot-starter` |
| **版本** | `ruoyi-chat/pom.xml` 显式写 **1.0.0-M6**；父 pom 声明 `spring.ai.version=1.0.0-M4`（被覆盖） |
| **作用** | 统一 LLM / Embedding / VectorStore / Tool 的抽象 API |
| **核心类** | `ChatClient`（Builder 模式）、`EmbeddingModel`（接口）、`Document`（文档抽象）、`TokenTextSplitter`（分块） |

**本项目的用法**：

```java
// ChatConfig.java —— 高层 Builder 模式
ChatClient.builder(openAiChatModel)
    .defaultSystem(SystemPrompt.DEFAULT_PROMPT2)   // 系统 Prompt
    .defaultTools(orderTools, learningAssistantTools, weatherTool) // Function Calling 注册
    .defaultAdvisors(new SimpleLoggerAdvisor())    // 拦截器
    .build();

// ChatServiceImpl.java —— 低层 API
ollamaChatClient.prompt()
    .messages(contextMessages)   // System + History + RAG
    .user(content)
    .stream()                    // Flux<String> 流式
    .content();
```

**版本注意**：
- Spring AI 1.0.0-M6 属于 **Milestone 里程碑版**，不是 Release
- 父 pom 声明 M4 但 ruoyi-chat 写死 M6 → 实际生效的是 **M6**
- M4→M6 变化：`@Param` → `@ToolParam` 注解改名、ChatClient API 微调

---

### 2. Spring Boot —— 基座

| 属性 | 值 |
|------|-----|
| **版本** | `3.2.4`（父 pom） |
| **核心贡献** | `SseEmitter`（流式响应载体）、`@ConditionalOnProperty`（组件开关）、自动配置 |
| **响应式** | 引入了 Reactor（`Flux<String>` 用于流式 token 输出） |

---

## 二、LLM（大语言模型）

### DeepSeek V4 Flash —— 对话模型

| 属性 | 值 |
|------|-----|
| **厂商** | 深度求索 (OpenRouter 兼容) |
| **模型名** | `deepseek-v4-flash` |
| **接入方式** | OpenAI 兼容协议（`https://api.deepseek.com`） |
| **上下文窗口** | 128K tokens |
| **配置位置** | `application-druid.yml` → `spring.ai.openai.chat.options.model` |
| **注入 Bean** | Spring AI Starter 自动创建 `OpenAiChatModel`，被 `ChatConfig` 用来构建 `ChatClient` |

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY:sk-xxx}
      base-url: https://api.deepseek.com
      chat:
        options:
          model: deepseek-v4-flash
```

### 对比：sp-milvus-demo 里还试了 Alibaba DashScope

sp-milvus-demo 模块用的是 Spring AI Alibaba 全家桶：
```yaml
spring:
  ai:
    alibaba:
      embedding:
        api-key: sk-xxx
        model: text-embedding-v2
  vectorstore:
    milvus:       # ← Spring AI 原生 VectorStore 抽象
      embedding-dimension: 1536
```
**ruoyi-chat 没这么做** —— 因为 Spring AI Alibaba 还不成熟，手动写了 `DashScopeEmbeddingModel` 直调原生 API。

---

## 三、Embedding（向量嵌入）

### DashScope text-embedding-v4 —— 语义向量化

| 属性 | 值 |
|------|-----|
| **厂商** | 阿里云 DashScope |
| **模型名** | `text-embedding-v4` |
| **接口** | `POST https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding` |
| **输出维度** | **1024**（可配置 384 / 768 / 1024 / 1536） |
| **关键约束** | 输出维度 **必须 = Milvus Collection 的 vector 字段 dimension** |

### EmbeddingConfig —— 自实现 EmbeddingModel

Spring AI Starter 没提供 DashScope Embedding 的自动配置，所以 **手动实现** 了 Spring AI 的 `EmbeddingModel` 接口：

```java
// EmbeddingConfig.java —— 自建 Bean
@Bean
@Primary
public EmbeddingModel embeddingModel() {
    return new DashScopeEmbeddingModel(apiKey, model);  // 内部类，用 RestClient 调 DashScope 原生 API
}
```

**实现的 3 个方法**：

| 方法 | 作用 |
|------|------|
| `call(EmbeddingRequest)` | 批量文本 → 批量向量 |
| `embed(Document)` | 单个 Document → float[] |
| `dimensions()` | 返回缓存的维度（首次调用后记住） |

**API 请求结构**：
```json
{
  "model": "text-embedding-v4",
  "input": { "texts": ["文本1", "文本2"] },
  "parameters": { "text_type": "document" }
}
```

---

## 四、向量存储

### Milvus —— 向量数据库

| 属性 | 值 |
|------|-----|
| **版本** | `io.milvus:milvus-sdk-java:2.4.1`（父 pom 锁定） |
| **部署方式** | Docker 自部署（host: `192.168.0.106:19530`） |
| **本项目模块** | 两个：`MilvusService`（Spring Service）+ `DocumentIngestService`（文档入库编排） |

### Milvus Collection Schema 设计

```
Collection: chat_docs
┌──────────┬──────────────┬──────────┬─────────────────────────┐
│ 字段      │ 类型          │ 属性      │ 说明                     │
├──────────┼──────────────┼──────────┼─────────────────────────┤
│ id       │ Int64        │ PK,AutoID│ 自增主键                  │
│ vector   │ FloatVector  │ dim=1024 │ DashScope embedding 输出  │
│ text     │ VarChar      │ max=65535│ 分块后的原文              │
│ metadata │ VarChar      │ max=4096 │ JSON: filename/uploadedAt│
└──────────┴──────────────┴──────────┴─────────────────────────┘

索引: IVF_FLAT, MetricType=COSINE, nlist=128
```

### Milvus SDK vs Spring AI VectorStore

| 方案 | 本项目选哪个 | 原因 |
|------|-------------|------|
| `io.milvus` SDK 原生 API | ✅ **选了这个** | 控制粒度细（自管 schema / insert / search） |
| Spring AI VectorStore 抽象 | ❌ 没选 | 封装了 CRUD 但自定义字段不方便 |

### MilvusConfig —— 开关式装配

```java
@Configuration
@ConditionalOnProperty(prefix = "milvus", name = "enabled", havingValue = "true")
public class MilvusConfig {
    @Bean
    public MilvusServiceClient milvusClient() { ... }
}
```
`milvus.enabled=false` 时整个 Milvus 层不装配 → `@Autowired(required=false)` 处为 null → RAG 自动跳过 → **主应用不受影响**。

### 关键类速查

| 类 | 职责 |
|----|------|
| `MilvusConfig` | 创建 `MilvusServiceClient` Bean，受开关控制 |
| `MilvusService` | Collection 管理 + `insert()` + `search()` |
| `DocumentIngestService` | 文件 → Tika 解析 → Splitter 分块 → Embedding → 入库 |

---

## 五、文档处理链路

### Apache Tika —— 多格式解析

| 属性 | 值 |
|------|-----|
| **版本** | `2.9.2`（`tika-core` + `tika-parsers-standard-package`） |
| **支持格式** | PDF / Word / Excel / CSV / TXT / Markdown / HTML ... |
| **用法** | `new Tika().parseToString(inputStream)` —— 一行代码搞定多格式转纯文本 |

### TokenTextSplitter —— 分块

| 属性 | 值 |
|------|-----|
| **来源** | Spring AI 内置 |
| **切分依据** | Token 数量（而非字符数），避免句子截断 |
| **用法** | `splitter.apply(List.of(new Document(text, metadata)))` → `List<Document>` |

### 完整入库链路

```java
// DocumentIngestService.ingestLocalFile()
String text = tika.parseToString(inputStream);         // 1. 解析
List<Document> chunks = splitter.apply(List.of(doc));  // 2. 分块
for (Document chunk : chunks) {
    float[] embed = embeddingModel.embed(chunk);        // 3. 向量化
    vectors.add(convert(embed));
    texts.add(chunk.getText());
}
milvusService.insert(collectionName, vectors, texts, metadatas); // 4. 入库
```

### 文件类型白名单 & 大小限制

```java
Set<String> ALLOWED_EXT = {"md","txt","pdf","doc","docx","xlsx","csv"};
long MAX_SIZE = 20 * 1024 * 1024;  // 20MB
```

---

## 六、Function Calling（工具调用）

### Spring AI @Tool 注解

| 属性 | 值 |
|------|-----|
| **注解** | `@Tool(description = "...")` —— 方法级，写给 LLM 看的触发条件 |
| **参数注解** | `@ToolParam(description = "...")` —— 参数级 |
| **版本要求** | Spring AI M6（M4/M5 叫 `@Param`） |

### 本项目 4 个 Tool

| Tool 类 | 方法 | 触发条件示例 | 实际调用 |
|---------|------|-------------|---------|
| `WeatherTool` | `weather(String city)` | "明天北京天气" | REST 调第三方天气 API |
| `CourseTools` | `queryCourse(title, teacherName)` | "有没有 Java 课程" | MyBatis-Plus DB 查询 |
| `LearningAssistantTools` | `searchCourses(String keyword)` | "推荐个 Spring 课" | DB 查询（同上，功能类似） |
| `OrderTools` | `queryOrderStatus(orderId, phone)` | "我的订单 ODER2026 到哪了" | 模拟返回物流状态 |

### 注册方式

```java
// ChatConfig.java
ChatClient.builder(chatModel)
    .defaultTools(orderTools, learningAssistantTools, weatherTool) // ← 注册
    .build();
```
Spring AI 启动时反射这些 Bean，把方法签名序列化成 **JSON Schema** 发给 LLM。

### 调用流程

```
用户: "北京今天天气怎么样？"
  ↓
LLM 决定调用 WeatherTool.weather(city="北京")
  ↓
Spring AI 反序列化 tool_calls → 反射调用 WeatherTool.weather("北京")
  ↓
拿到返回字符串 → 追加到 tool message
  ↓
LLM 根据工具结果组织自然语言回复: "北京今天晴，25℃"
```

---

## 七、流式通信

### SSE + Flux 组合拳

| 组件 | 作用 |
|------|------|
| `Flux<String>` | Reactor 响应式流，Spring AI `.stream().content()` 的返回类型 |
| `SseEmitter` | Spring MVC 长连接载体 |
| `startWith("#CONV_xxx#")` | 第一帧注入会话 ID 标记 |

```java
Flux<String> flux = chatService.sendMessage(chatMessage);
flux.subscribe(
    chunk -> emitter.send(SseEmitter.event().data(chunk)),  // 每个 token 推送
    error -> emitter.completeWithError(error),
    () -> emitter.send(SseEmitter.event().data("[DONE]"))   // 结束标记
);
```

### 线程池隔离

```java
@Bean("aiStreamExecutor")
public Executor aiStreamExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(10);
    executor.setMaxPoolSize(50);
    executor.setQueueCapacity(100);
    executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
    return executor;
}
```
**为什么需要单独线程池**：AI 流式请求是长连接（几秒到几十秒），不跟 Tomcat 工作线程混在一起。

---

## 八、数据持久化

### MySQL + MyBatis-Plus

两张表存储 AI 对话：

| 表 | 实体 | 主键 | 说明 |
|----|------|------|------|
| `ai_conversation` | `AiConversation` | String UUID | 会话元数据（title / userId / createTime） |
| `ai_message` | `AiMessage` | Long AUTO_INCREMENT | 对话历史（role=user/assistant + content） |

```java
// AiChatServiceImpl —— CRUD 实现
conversationMapper.insert(conv);                     // 创建会话
messageMapper.insert(message);                       // 存消息
messageMapper.selectList(new LambdaQueryWrapper<>()  // 查历史
    .eq(AiMessage::getConversationId, convId)
    .orderByAsc(AiMessage::getCreateTime));
```

---

## 九、工程化 & 辅助

| 技术 | 版本 | 作用 |
|------|------|------|
| **MyBatis-Plus** | 父 pom 锁定 | DB CRUD，`LambdaQueryWrapper` 写条件 |
| **FastJSON2** | 2.0.57 | SSE 推送时把 Map 序列化成 JSON 字符串 |
| **Lombok** | 1.18.46 | `@Data` / `@Builder` / `@AllArgsConstructor` 减样板代码 |
| **Spring Retry** | Starter 自带 | `RetryTemplate` 配了 maxAttempts=10 + ExponentialBackOff |
| **Slf4j + Logback** | Spring Boot 自带 | 关键路径加了大量结构化日志（RAG 检查 / Embedding 维度 / Milvus 分数） |
| **Spring DevTools** | 3.2.4 自带 | 热重启，开发时改代码自动重启 |

---

## 十、版本依赖全景图

```
ruoyi-chat/pom.xml
├── spring-ai-openai-spring-boot-starter:1.0.0-M6  ← 显式写死，覆盖父 pom M4
├── milvus-sdk-java:2.4.1                          ← 父 pom 锁定
├── tika-core:2.9.2
├── tika-parsers-standard-package:2.9.2
├── ruoyi-common                                   ← 若依公共模块
├── spring-boot-starter-web:3.2.4
├── mybatis-plus                                   ← 父 pom 锁定
├── fastjson2:2.0.57
└── lombok:1.18.46

父 pom (ruoyi/pom.xml)
├── spring-boot.version:3.2.4
├── spring.ai.version:1.0.0-M4   ← ruoyi-chat 覆盖为 M6
├── milvus.sdk.version:2.4.1
└── tika:2.9.2 (未锁定，ruoyi-chat 自己写)
```

---

## 附录：技术选型速查表

| 需求 | 选型 | 为什么选 | 弃用的替代方案 |
|------|------|---------|---------------|
| 对话 LLM | DeepSeek V4 (OpenAI 兼容) | 便宜 + 中文好 + OpenAI 协议通用 | 通义千问 / ChatGPT |
| Embedding | DashScope text-embedding-v4 | 阿里云网络好 + 1024 维精度高 | BGE-M3 / OpenAI text-embedding-3 |
| 向量库 | Milvus 2.4.1 | 自部署免费 + 亿级性能 | Pinecone / FAISS / PGVector |
| AI 框架 | Spring AI 1.0.0-M6 | 统一抽象 + 与 Spring Boot 无缝 | LangChain4j / 手动 HTTP |
| 文档解析 | Apache Tika | 一行搞定多格式 | 各格式单独解析 |
| 分块策略 | TokenTextSplitter | Token 粒度不截断句子 | CharacterTextSplitter |
| 流式 | SSE + Flux | 打字机效果 + 长连接 | WebSocket |
| Function Calling | Spring AI @Tool | 注解自动转 JSON Schema | 手动拼 tools JSON |

