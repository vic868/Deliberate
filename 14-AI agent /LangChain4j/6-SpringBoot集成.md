---
title: LangChain4j Spring Boot 集成与生产化
tags:
  - LangChain4j
  - Spring Boot
  - 生产化
  - SSE
created: 2026-10-29
status: completed
aliases:
  - LangChain4j Spring Boot
---

# LangChain4j Spring Boot 集成与生产化

> [!info] 这份笔记管什么
> 把 LangChain4j 接进 Spring Boot：**两种装配方式**、配置文件全表、多模型/降级、SSE 流式、可观测、并发与成本控制。
> 依赖：`langchain4j-spring-boot-starter` + `langchain4j-open-ai-spring-boot-starter`（均 `1.23.0-beta33`）+ Spring Boot 3.5。
> ⭐ 部分是**真实启动 Spring 容器**验证过的（Bean 名、自动装配条件），不是照抄文档。

---

## 1. 依赖

```xml
<!-- 1) LangChain4j 核心 + Spring 装配（@AiService、ChatMemoryProvider 自动注入） -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-spring-boot-starter</artifactId>
    <version>1.23.0-beta33</version>
</dependency>

<!-- 2) 模型提供者：OpenAI 协议（DeepSeek / 通义 / vLLM / Ollama 兼容口都走它） -->
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-open-ai-spring-boot-starter</artifactId>
    <version>1.23.0-beta33</version>
</dependency>
```

> [!warning] 只加第一个是不够的
> `langchain4j-spring-boot-starter` 只提供 **`@AiService` 扫描 + RAG 配置**，**不会**自动创建任何 `ChatModel` Bean。
> 模型 Bean 来自 `langchain4j-<provider>-spring-boot-starter`。少了它，启动会报：
> `required a bean named 'openAiChatModel' that could not be found`（⭐ 实测，见 §6.2）

---

## 2. 配置（⭐ 键名来自 starter 的 `spring-configuration-metadata.json`）

```yaml
langchain4j:
  open-ai:
    chat-model:
      base-url: https://api.deepseek.com/v1   # 兼容 OpenAI 协议的任意端点
      api-key: ${DEEPSEEK_API_KEY}            # ⚠️ 必须存在（见 §6.1）
      model-name: deepseek-chat
      temperature: 0.3
      max-tokens: 2048
      timeout: PT60S
      max-retries: 2
      log-requests: true                      # 调试期开，生产关
      log-responses: true
    streaming-chat-model:                     # 流式是独立的一棵配置树
      base-url: https://api.deepseek.com/v1
      api-key: ${DEEPSEEK_API_KEY}
      model-name: deepseek-chat
    embedding-model:                          # 需要向量化时才配
      base-url: https://dashscope.aliyuncs.com/compatible-mode/v1
      api-key: ${DASHSCOPE_API_KEY}
      model-name: text-embedding-v4
      dimensions: 1024
```

`langchain4j.open-ai.*` 下实际存在的配置组（实测元数据）：

| 组 | Bean 名 | 备注 |
|---|---|---|
| `chat-model` | `openAiChatModel` | 同步对话 |
| `streaming-chat-model` | `openAiStreamingChatModel` | **流式（1.x 新增，与 chat-model 分开配）** |
| `embedding-model` | `openAiEmbeddingModel` | 向量化，`dimensions` 可配 |
| `image-model` | `openAiImageModel` | 图像生成 |
| `moderation-model` | `openAiModerationModel` | 国内模型多不支持 |
| `decision-model` | `openAiDecisionModel` | 内部决策小模型 |

> [!note] `language-model` / `streaming-language-model` 是旧键
> 元数据里还存在 `langchain4j.open-ai.language-model.*` 等，属兼容遗留。**新项目用 `chat-model` / `streaming-chat-model`**。

---

## 3. 两种装配方式

### 3.1 方式 A：`@AiService` 注解（声明式，最像 Spring）

```java
@AiService(
        wiringMode = AiServiceWiringMode.EXPLICIT,   // 显式 = 下面按 Bean 名引用；AUTOMATIC = 按类型自动找
        chatModel = "openAiChatModel",
        streamingChatModel = "openAiStreamingChatModel",
        chatMemoryProvider = "chatMemoryProvider"
)
public interface Assistant {
    @SystemMessage("你是企业知识库助手，只基于资料回答")
    String chat(@MemoryId String userId, @UserMessage String question);
}
```

```java
@Configuration
public class AiServicesConfig {
    @Bean
    ChatMemoryProvider chatMemoryProvider() {
        return memoryId -> MessageWindowChatMemory.builder()
                .id(memoryId)
                .maxMessages(20)
                .chatMemoryStore(new RedisChatMemoryStore(redis))   // 生产：会话落 Redis
                .build();
    }
}
```

**优点**：业务代码零装配；Spring 启动时构建 → **等于免费的配置校验**（注解写错启动就失败）。
**缺点**：`tools` / `contentRetriever` / guardrail 等复杂能力要按名称引用 Bean，配置分散。

### 3.2 方式 B：`@Bean` 手工构建（复杂场景推荐）

```java
@Configuration
public class AssistantConfig {

    @Bean
    Assistant assistant(ChatModel chatModel, ChatMemoryProvider memProvider,
                        ContentRetriever retriever, OrderTools orderTools) {
        return AiServices.builder(Assistant.class)
                .chatModel(chatModel)
                .chatMemoryProvider(memProvider)
                .contentRetriever(retriever)
                .tools(orderTools)
                .maxToolCallingRoundTrips(5)
                .inputGuardrails(new PromptInjectionGuardrail())
                .afterToolExecution(e -> auditInfo(e))
                .build();
    }
}
```

| | 方式 A `@AiService` | 方式 B `@Bean` |
|---|---|---|
| 代码量 | 最少 | 中 |
| 复杂配置（工具/护栏/过滤） | 受注解能力限制 | 完全可控 |
| IDE 可查性 | 差（靠字符串 Bean 名） | 好（构造器注入） |
| 适用 | 简单对话/分类接口 | 生产 RAG / Agent |

> [!tip] 我们的建议
> **简单能力用 A，主业务用 B**。两套可以共存：A 给你"一堆小接口"，B 给你"一个复杂的核心 Agent"。

---

## 4. 流式输出接 SSE

### 4.1 MVC + `SseEmitter`

```java
@RestController
public class ChatController {

    private final Assistant assistant;   // 方式 B 或 A 都行

    @GetMapping(value = "/api/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@RequestParam String userId, @RequestParam String q) {
        SseEmitter emitter = new SseEmitter(0L);   // 不超时（或按业务设）
        // 用独立线程池，避免占用 Tomcat 工作线程
        taskExecutor.execute(() -> {
            try {
                assistant.chat(userId, q)
                        .onPartialResponse(token -> emitter.send(token))
                        .onCompleteResponse(r -> { emitter.send("\n[done]"); emitter.complete(); })
                        .onError(e -> { emitter.send("[error] " + e.getMessage()); emitter.complete(); })
                        .start();
            } catch (Exception e) {
                emitter.completeWithError(e);
            }
        });
        return emitter;
    }
}
```

> [!warning] SSE 的 4 个坑
> 1. **必须 `produces = text/event-stream`**，否则前端 `EventSource` 收不到
> 2. **Nginx 要关 buffering**：`proxy_buffering off; proxy_read_timeout 600s;`
> 3. **客户端断开**后服务端要停止生成（否则继续计费）→ 监听 `emitter.onCompletion/onTimeout` 并取消
> 4. **不要用 Tomcat 默认线程池跑长流式**——连接数一多就饿死其他请求

### 4.2 Spring AI 与 LangChain4j 的流式对照

| | Spring AI | LangChain4j |
|---|---|---|
| 流式返回类型 | `Flux<String>`（Reactor） | `TokenStream` 回调 |
| 接 WebFlux | 天然 | 需要桥接 |
| 接 MVC | `SseEmitter` / `ResponseBodyEmitter` | 同左侧 |
| 取消能力 | `Flux` 天然可取消 | 需自行处理 |

> 如果团队是 **WebFlux**，Spring AI 的 `Flux<String>` 更顺手；**MVC + `SseEmitter`** 下两者工作量相当。

---

## 5. 生产化：稳定 / 成本 / 延迟 / 可观测 / 安全

### 5.1 稳定

```java
// ① 模型级：超时 + 重试（builder 上）
.maxRetries(2).timeout(Duration.ofSeconds(60))

// ② 业务级：主备模型降级
@Bean
ChatModel primaryChatModel(...) { ... }         // 主
@Bean
ChatModel backupChatModel(...) { ... }          // 备（另一家）

String ask(String q) {
    try { return primary.chat(q); }
    catch (RuntimeException e) { metrics.degraded(); return backup.chat(q); }
}

// ③ 工具级：出错回灌而不是抛给用户
.toolExecutionErrorHandler((err, ctx) -> ToolErrorHandlerResult.text("工具暂不可用，请稍后再试"))
```

**降级顺序建议**：主模型 → 备模型 → 规则兜底（返回"稍后再试"/转人工），**不要**让一个模型挂了拖垮整个聊天入口。

### 5.2 成本

| 手段 | 做法 |
|---|---|
| 计费埋点 | 从 `ChatResponse.tokenUsage()` / `Result<T>.tokenUsage()` 累计，按 `userId` / `tenant` 打点 |
| 上下文裁剪 | `MessageWindowChatMemory.maxMessages` / `TokenWindowChatMemory` |
| 元数据瘦身 | RAG 注入只带 `source/section`，别把整个 JSON 塞 prompt |
| 模型分层 | 意图识别/改写用小模型，最终回答用大模型 |
| 缓存 | 相同问题（向量近邻阈值）语义缓存 |
| 工具数量 | 每轮都发工具定义 → 按场景拆接口（见 [[5-Agent工具调用#6. 工具越多，prompt 越大：工具治理]]） |

### 5.3 延迟

- 流式优先（首 token 时间才是用户感知的延迟）
- RAG 的 `executor(...)` 并行多路检索
- `QueryTransformer`（改写）是额外一次 LLM 调用，只在多轮对话开
- 工具调用每轮都是一次完整 LLM 调用 → 合并工具、减少轮次

### 5.4 可观测

```java
// ① AiServices 事件
AiServices.builder(Assistant.class)
        .registerListener((AiServiceStartedEvent e) -> span.start())
        .registerListener((AiServiceCompletedEvent e) -> span.end())
        .afterToolExecution(e -> metrics.tool(e.request().name(), e.duration(), e.hasFailed()))
        .build();
```

```yaml
# ② 把 LangChain4j 内部 offload 到 Spring 的线程池，保证 MDC / trace / 安全上下文不丢
langchain4j:
  executor:
    use-spring-task-executor: true
```

> 这个开关是 1.x 明确提供的（`spring-configuration-metadata.json` 里有），**异步/流式场景下 traceId 丢失**就靠它解决。

### 5.5 安全

| 风险 | 手段 |
|---|---|
| 提示词注入 | 输入护栏（[[3-契约式开发#7. 护栏 Guardrail（生产必备）]]） |
| 数据越权 | 检索时 `dynamicFilter` 带 **服务端注入的 tenant**，绝不从用户输入取 |
| 工具越权 | 工具内部强校验（取 `SecurityContext`），不信任模型参数 |
| 写操作失控 | 审批门面（[[5-Agent工具调用#5. 人工审批（Human-in-the-loop）]]） |
| 密钥泄露 | 配置走环境变量/密钥管理；`log-requests=false`；输出护栏防 "sk-" 泄露 |
| 敏感数据留存 | `ChatMemoryStore.deleteMessages` 要能真删 |

---

## 6. ⭐ 真实启动验证（踩坑实录）

### 6.1 坑一：`api-key` 属性**不存在**时，模型 Bean 不创建

```text
AutoConfig#openAiChatModel:
   Did not match:
      - @ConditionalOnProperty (langchain4j.open-ai.chat-model.api-key)
        did not find property 'langchain4j.open-ai.chat-model.api-key' (OnPropertyCondition)
```

**结论**：
- 自动配置是 `@ConditionalOnProperty("...api-key")`，**只认配置项，不认环境变量是否已导出**
- 想在本地/CI 无 Key 起服务，必须**显式写一个占位**：

```yaml
api-key: ${DEEPSEEK_API_KEY:sk-local-placeholder}
```

> 这在"本地起服务、只想验证装配"的场景很实用；**生产绝不要留占位值**，启动校验里要检查 `api-key` 不以 `sk-local` 开头。

### 6.2 坑二：只引 `langchain4j-spring-boot-starter` 时启动失败

```text
Parameter 0 of constructor in demo.ChatController required a bean named 'openAiChatModel' that could not be found.
Consider defining a bean named 'openAiChatModel' in your configuration.
```

**原因**：模型 Bean 来自 provider 级 starter，不是 LangChain4j 主 starter。修法见 §1。

### 6.3 验证通过的 Bean 图（⭐ 实测输出）

```text
BEAN openAiChatModel            exists=true  type=dev.langchain4j.model.openai.OpenAiChatModel
BEAN openAiStreamingChatModel   exists=true  type=dev.langchain4j.model.openai.OpenAiStreamingChatModel
BEAN chatMemoryProvider         exists=true  type=demo.AiServicesConfig$$Lambda…
BEAN assistant                  exists=true  type=demo.$Proxy60        ← @AiService 接口被注册为 JDK 代理 Bean
AI-SERVICE-BEAN-TYPE = demo.$Proxy60
```

从这 4 行可以确认：

1. `@AiService` 接口确实**变成了 Spring Bean**（`demo.$Proxy60`，JDK 动态代理）——因为 `@AiService` 被 Spring 扫描到（`AiServicesRegisteringBeanFactoryPostProcessor`）
2. `chatMemoryProvider` Bean 被正确引用
3. `streaming-chat-model` 与 `chat-model` 是**两个 Bean**，可分别注入

> 验证方式：用 `SpringApplication` 以 `WebApplicationType.NONE` 起容器，打印 `ctx.containsBean(...)`，**不发起任何模型调用**（所以无 Key 也能跑）。

---

## 7. 测试策略

| 层级 | 怎么做 |
|---|---|
| 单元 | 脚本化假模型（[[3-契约式开发#9. 用"假模型"做单元测试 ⭐]]）验证编排 |
| 装配 | 起 `ApplicationContext` 断言关键 Bean 存在（本节 §6.3 的做法），无需 Key |
| 集成 | Testcontainers 起 Milvus/Redis，用假模型跑通全链路 |
| 效果 | 30~100 条评测集，真实模型打分（见 [[14-AI agent /3-Milvus/4-AI中的用法#3.4 离线评估（RAG 的硬门槛）]]） |

---

## 8. 上线 checklist

- [ ] provider starter 引全，版本与主包对齐（`1.23.0` / `1.23.0-beta33`）
- [ ] `log-requests` / `log-responses` 生产关闭
- [ ] `max-retries` + `timeout` 有值；有主备降级
- [ ] `chatMemoryProvider` 落 Redis/DB，能按会话清理
- [ ] `use-spring-task-executor: true`，确认 traceId 透传
- [ ] SSE 关 buffering、心跳保活、断连取消
- [ ] 护栏：输入注入 + 输出敏感信息
- [ ] 工具：轮次上限 + 审计日志 + 写操作审批
- [ ] 成本：token 按租户/用户打点，设日预算告警
- [ ] 无 Key 能起服务（占位仅限本地 profile）

---

## 9. 延伸

- Spring Boot 集成：<https://docs.langchain4j.dev/tutorials/spring-boot-integration>
- 与 Spring AI 的详细对比：[[7-选型对比与面试]]
- 速查：[[8-速查卡]]
