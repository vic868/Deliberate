---
tags:
  - ruoyi
  - spring-ai
  - interview
  - rag
  - milvus
  - function-calling
created: 2026-10-29
status: completed
source: ruoyi-chat 模块面试题整理
---

# RuoYi × Spring AI 面试题

> 基于 ruoyi-chat 模块的实际代码，覆盖 **RAG、Function Calling、SSE 流式、Milvus、Embedding** 五大核心领域。
> 
> 所有题目均有对应的源码锚点，面试官可直接 `grep` 定位。

---

## 〇、系统架构总览（必问开场白）

### Q1：用 3 分钟介绍一下你做的 AI 聊天模块的整体架构。

**参考答案要点**：

```
┌──────────┐     SSE      ┌──────────────────┐
│  Vue 前端 │ ──────────► │  ChatController   │
└──────────┘              └────────┬─────────┘
                                   │ Flux<String>
                                   ▼
                         ┌─────────────────────┐
                         │   ChatServiceImpl    │
                         │  (RAG + History +    │
                         │   Tools orchestrator)│
                         └────┬──────────┬─────┘
                              │          │
                 ┌────────────┘          └─────────────┐
                 ▼                                       ▼
     ┌────────────────┐                        ┌─────────────────┐
     │ MilvusService  │                        │   ChatClient     │
     │ vector search  │                        │  (Spring AI M6)  │
     └───────┬────────┘                        └────────┬────────┘
             │                                         │
     ┌───────┴────────┐                        ┌───────┴────────┐
     │ EmbeddingModel │                        │  @Tool 注解    │
     │ DashScope 1024d│                        │  (Function Call)│
     └────────────────┘                        └────────────────┘
```

- **基座**：若依 (RuoYi-Vue 3.9) + Spring Boot + MyBatis-Plus
- **AI 层**：Spring AI 1.0.0-M6 + OpenAI ChatModel（兼容 DeepSeek V4）
- **向量层**：Milvus + DashScope text-embedding-v4（1024 维）
- **RAG 链路**：Tika 解析文件 → TokenTextSplitter 分块 → Embedding → Milvus Insert → 查询时 COSINE search topK=4 → 拼入 SystemPrompt
- **Function Calling**：4 个 `@Tool` Bean（天气、课程、订单、学习助手）注册到 ChatClient.defaultTools()
- **对话持久化**：MySQL 存 AiConversation + AiMessage，MAX_HISTORY_ROUNDS=10
- **降级策略**：`@ConditionalOnProperty(milvus.enabled=true)` / `@Autowired(required=false)` 双保险，Milvus 挂了不阻塞主流程

---

## 一、RAG（检索增强生成）

### Q2：RAG 的完整链路是怎样的？你在项目中哪些环节做了优化？

**源码锚点**：`DocumentIngestService.ingestLocalFile()` | `ChatServiceImpl.buildRagContext()`

**链路**：
```
文件上传 → UploadFileController → DocumentIngestService.ingestLocalFile()
    → Apache Tika.parseToString()          // 多格式解析
    → TokenTextSplitter.apply()            // 分块
    → EmbeddingModel.embed(chunk)          // 向量化
    → MilvusService.insert()               // 写入向量库

用户提问 → ChatServiceImpl.sendMessage() → buildRagContext()
    → EmbeddingModel.embed(query)          // query 向量化
    → MilvusService.search(topK=4)         // 向量检索
    → 分数过滤 (RAG_SCORE_THRESHOLD=0.0)   // 质量把关
    → 拼成 SystemPrompt 注入 ChatClient    // 上下文增强
```

**优化点**：
1. **异常隔离**：RAG 检索异常时 `catch` 只 warn，不影响 LLM 正常回答（`ChatServiceImpl.java:141`）
2. **Collection 存在性检查**：`milvusService.hasCollection()` 提前跳过未初始化场景，避免空指针
3. **硬阈值过滤**：topK=4 + score ≥ 0.0 双重过滤，防止低质量文档污染 Prompt
4. **RAG 结果显式指令**：SystemPrompt 里写了"如果参考资料没有，说无法回答，不要编造"

---

### Q3：为什么分块用了 TokenTextSplitter？有哪些分块策略可以选？

**源码锚点**：`DocumentIngestService.java` 中 `new TokenTextSplitter()`

- **TokenTextSplitter**：按 token 数切分（而非字符数），避免一个句子被截断
- 其他策略：SentenceSplitter（按句子）、RecursiveCharacterTextSplitter（递归切分保边界）
- **本项目**：Spring AI 直接提供的 TokenTextSplitter，开箱即用

---

### Q4：RAG 检索到的文档是直接塞进 prompt 吗？有没有考虑 token 超限？

**源码锚点**：`ChatServiceImpl.buildRagContext()`

当前策略是 **topK=4 + 直接拼接**，没有做 token 预算。如果要生产化改进：
1. 先用 Embedding 粗筛 topK=100，再用 LLM rerank 到 topK=4
2. 按 chunk.text().length() 累加，超限时截断最不相关的
3. 用 Tokenizer 精确算 token 数（Spring AI 的 `TokenCountEstimator`）

---

## 二、Spring AI Function Calling（@Tool）

### Q5：`@Tool` 注解的工作原理？Spring AI 是怎么把你的 Java 方法暴露给大模型的？

**源码锚点**：`WeatherTool.java` | `OrderTools.java` | `ChatConfig.ollamaChatClient()`

**原理三步**：
1. **扫描期**：`ChatClient.builder().defaultTools(toolBeans...)` 传入 Bean，Spring AI 通过反射读 `@Tool(description=...)` 和 `@ToolParam(description=...)` 注解
2. **请求期**：Spring AI 把这些方法签名序列化成 JSON Schema，注入到 ChatCompletion 的 `tools` 参数中发给 LLM
3. **执行期**：LLM 返回 `tool_calls` → Spring AI 自动反序列化参数 → 调用真实方法 → 把返回值再作为 `tool` 消息追加到对话历史，让 LLM 最终给用户自然语言回复

**本项目的配置**：
```java
// ChatConfig.java
ChatClient.builder(chatModel)
    .defaultTools(orderTools, learningAssistantTools, weatherTool)  // 注册工具
    .defaultAdvisors(new SimpleLoggerAdvisor())                    // 日志切面
    .build();
```

---

### Q6：如果 @Tool 方法抛异常了会怎样？需要自己处理吗？

- Spring AI 会把异常信息作为 tool 的"回复"返回给 LLM
- LLM 看到错误后会尝试重新调用，或者告知用户出错了
- **最佳实践**：Tool 方法内部 try-catch，返回友好的错误字符串（而不是让异常抛到框架层）
- 本项目的 WeatherTool 就直接让 IOException 往上抛了，可以作为改进点

---

### Q7：Function Calling 和 RAG 可以结合吗？你们项目里怎么结合的？

**结合方式**：两者是独立的增强通道，可以同时生效：

```java
// ChatServiceImpl.sendMessage()
contextMessages.addAll(buildRagContext(content));  // 通道1: RAG 文档注入 SystemPrompt

ollamaChatClient.prompt()
    .messages(contextMessages)
    .user(content)
    .stream()
    .content();  // 通道2: ChatClient 自带 .defaultTools() 已注册 Function Calling
```

- LLM 收到的消息里既有 RAG 注入的 SystemPrompt，又有 tools schema
- 它自己决定用哪个（或都不用）
- 比如用户问"明天北京天气怎么样" → LLM 调用 WeatherTool
- 用户问"Milvus 是什么" → LLM 用 RAG 查到的文档回答

---

## 三、SSE 流式对话 & 多轮记忆

### Q8：SSE 流式响应和普通 HTTP 返回有什么区别？为什么聊天要用 SSE？

**源码锚点**：`ChatController.aiSend()` → `produces = MediaType.TEXT_EVENT_STREAM_VALUE`

| 维度 | 普通 HTTP | SSE |
|------|-----------|-----|
| 响应时机 | 全部生成完才返回 | token 到达即推 |
| 用户体感 | 等待 5-10 秒白屏 | 打字机效果 |
| 连接方式 | 短连接 | 长连接（同 HTTP） |
| 前端处理 | await + JSON.parse | EventSource.onmessage |

**本项目实现**：
```java
Flux<String> contentFlux = chatService.sendMessage(chatMessage);
contentFlux.subscribe(
    chunk -> emitter.send(SseEmitter.event().data(json)),
    error -> emitter.completeWithError(error),
    () -> emitter.send(SseEmitter.event().data("[DONE]"))
);
```

---

### Q9：Flux<String> 和 SseEmitter 是怎么串起来的？#CONV_xxx# 这个第一帧是干嘛的？

**源码锚点**：`ChatServiceImpl.sendMessage()` → `.startWith("#CONV_" + finalConversationId + "#")`

- `Flux<String>` 是 Reactor 的响应式流，Spring AI `.stream().content()` 返回的就是它
- SseEmitter 是 Spring MVC 的异步长连接载体，`Flux.subscribe()` 里 `.send()` 推数据
- **第一帧特殊标记**：Flux 用 `startWith()` 注入一个特殊 chunk，Controller 层检测到 `#CONV_xxx#` 后提取 conversationId 单独放入 JSON，让前端能在 LLM 还在输出时就拿到新会话的 ID

---

### Q10：多轮对话历史是怎么处理的？为什么有 MAX_HISTORY_ROUNDS 限制？

**源码锚点**：`ChatServiceImpl.buildContextMessages()` | `MAX_HISTORY_ROUNDS = 10`

```java
// 取最近 10 轮（20 条消息 + 可能 1 条 system）
int start = Math.max(0, history.size() - MAX_HISTORY_ROUNDS * 2 - 1);
for (int i = start; i < history.size() - 1; i++) { ... }
```

限制原因：
1. **Token 预算**：LLM context window 有限（DeepSeek V4 是 128K，但越长越贵越慢）
2. **Cost 控制**：每轮都要把历史发过去，消息越多 token 消耗越大
3. **噪声衰减**：早期对话对当前问题的参考价值递减

---

## 四、Milvus 向量数据库

### Q11：为什么选 Milvus 而不是 Pinecone / FAISS / PGVector？

- **Milvus**：开源、自部署、亿级向量毫秒级、支持混合检索（标量 + 向量）
- **Pinecone**：全托管云服务，免运维但收费
- **FAISS**：Meta 出品的本地库，不是独立服务，没有持久化
- **PGVector**：Postgres 插件，适合已有 PG 基础设施但向量规模大时性能不如专业库

**本项目选 Milvus 的理由**：自部署 + 开源免费 + Java SDK 成熟 + 跟 Spring AI 可以集成

---

### Q12：Milvus 的 Collection schema 是怎么设计的？为什么用 IVF_FLAT + COSINE？

**源码锚点**：`MilvusService.createCollection()` | `DocumentIngestService.ensureCollectionReady()`

```
Collection: chat_docs
├── id        (Int64, PK, AutoID)
├── vector    (FloatVector, dim=1024)   ← DashScope embedding 维度
├── text      (VarChar, max=65535)      ← 原文内容
└── metadata  (VarChar, max=4096)       ← JSON 格式的元信息

索引: IVF_FLAT, MetricType=COSINE, nlist=128
```

- **IVF_FLAT**：倒排索引，向量聚类分桶，查询时只搜最近的几个桶，比暴力 FLAT 快几十倍，精度损失 < 2%
- **COSINE**：余弦相似度，适合 Embedding 语义距离（因为 Embedding 模型训练时通常用 cosine loss）
- **nlist=128**：经验值，总向量数 / nlist ≈ 每桶 10K+ 效果好

---

### Q13：`@ConditionalOnProperty` 和 `@Autowired(required=false)` 双保险的设计意义？

**源码锚点**：`MilvusConfig` | `MilvusService` | `ChatServiceImpl`

```java
// 配置层
@ConditionalOnProperty(prefix = "milvus", name = "enabled", havingValue = "true")
public class MilvusConfig { ... }

// 使用层
@Autowired(required = false)
private MilvusService milvusService;
```

**意义**：
1. 开发机可能没装 Milvus，关掉 `milvus.enabled=false` 后 **整个 AI 模块正常启动**，只是 RAG 功能跳过
2. `required=false` 确保 Bean 不存在时不报错，代码里判 null 降级
3. 面试加分点：**这是生产级"可选组件"的标准写法**，别让一个外部依赖搞崩整个应用启动

---

## 五、Embedding & 向量检索

### Q14：Embedding 用的什么模型？1024 维是怎么定的？

**源码锚点**：`application-druid.yml` | `EmbeddingConfig.java`

- 模型：阿里云 DashScope `text-embedding-v4`
- 维度：1024（text-embedding-v4 支持 384 / 768 / 1024，选最大的）
- **重要约束**：Milvus Collection 的 dimension 必须 = Embedding 模型输出维度，否则 `createCollection` 时 schema 校验失败

---

### Q15：向量检索的 score 是什么意思？为什么阈值设 0.0？

**源码锚点**：`MilvusService.search()` | `RAG_SCORE_THRESHOLD = 0.0f`

- COSINE metric 下，Milvus 返回的 score = `1 - cosine_distance`，所以 **score 越接近 1.0 越相似**
- COSINE 的原始距离范围是 [0, 2]，转换后 score ∈ [-1, 1]
- 阈值 0.0 相当于"只保留正相关的"，实际生产可能设 0.5 或更高

---

## 六、Spring AI 核心概念

### Q16：Spring AI M6 的 ChatClient 怎么用？跟 ChatModel 有什么区别？

**源码锚点**：`ChatConfig.ollamaChatClient()`

```java
// 低层 API
chatModel.call(new Prompt(List.of(new UserMessage("你好"))));

// 高层 API (Builder 模式)
ChatClient.builder(chatModel)
    .defaultSystem(prompt)
    .defaultTools(toolBeans)
    .build()
    .prompt()
    .user("你好")
    .stream()
    .content();
```

- ChatModel：Spring AI 1.0 前的主要入口，同步调用为主
- ChatClient：Builder 模式，链式 API，原生支持 tools / advisors / system prompt / stream
- **本项目用 ChatClient**，因为 Stream + Function Calling 都需要它

---

### Q17：Advisor 是什么？你们用了吗？

**源码锚点**：`ChatConfig.java` → `.defaultAdvisors(new SimpleLoggerAdvisor())`

Advisor 是 Spring AI 的 **拦截器机制**，在 prompt 发送前 / response 返回后做增强：
- 内置：SimpleLoggerAdvisor（打印请求/响应）、MessageWindowChatMemory（自动管理对话窗口）
- 自定义：可以做 Prompt 注入、Token 计数、Cost 统计、敏感词过滤
- **本项目**：用了 SimpleLoggerAdvisor，日志里能看到完整的请求/响应

---

## 七、工程化 & 踩坑

### Q18：你说 YAML 重复 key 报错？怎么发现和排查的？

**源码锚点**：`application-druid.yml`（已修复）

**问题**：同一个 YAML 里写了两个顶层 `milvus:` key，SnakeYAML 不允许
**排查**：错误栈里直接写 `found duplicate key milvus in 'reader', line 105`
**修复**：删掉较早的那个，保留字段更全的那个

**面试引申**：YAML vs properties 的优劣？YAML 支持嵌套和列表但要求格式严谨、不允许同级重复 key。

---

### Q19：Spring AI 1.0.0-M6 版本的坑有哪些？升级要注意什么？

**本项目踩过的**：
1. Milvus SDK 版本要跟 Spring AI 配套，父 pom 做版本锁定
2. `@ToolParam` 注解在 M6 里才有早期版本叫 `@Param`
3. Milvus Collection schema 一旦创建不能改 dimension，只能 drop 重建
4. Embedding 模型换了（比如从 text-embedding-v2 换成 v4）dimension 变了，旧 Collection 必须删

---

### Q20：如果要把这个系统上线，你会加哪些东西？

| 层面 | 加什么 |
|------|--------|
| **RAG 质量** | Rerank 模型（BGE-Reranker）、Chunk Overlap、BM25 + 向量混合检索 |
| **可观测性** | Micrometer 埋点（LLM latency、Milvus search cost、token 用量）、SSE 心跳保活 |
| **成本控制** | Token 预算、Embedding 缓存、对话历史滚动摘要 |
| **安全** | API Key 加密存储、Tool 调用审计、敏感词过滤 |
| **高可用** | Milvus 集群部署、LLM Provider 熔断降级、会话 Redis 缓存 |

---

## 附录：关键类速查表

| 类名 | 职责 |
|------|------|
| `ChatController` | SSE 流式接口 / 会话管理 REST API |
| `ChatServiceImpl` | RAG 编排 + 历史拼接 + 调用 ChatClient |
| `AiChatServiceImpl` | Conversation / Message 的 MyBatis-Plus CRUD |
| `MilvusService` | Collection 管理 + 向量 Insert/Search |
| `DocumentIngestService` | 文件上传 → Tika 解析 → Splitter 分块 → Embedding → Insert |
| `ChatConfig` | ChatClient Bean + Tools 注册 + RetryTemplate |
| `MilvusConfig` | `@ConditionalOnProperty` 控制的 MilvusServiceClient Bean |
| `WeatherTool` / `CourseTools` / `OrderTools` | `@Tool` Function Calling 实现 |
| `EmbeddingConfig` | DashScope EmbeddingModel Bean 定义 |

