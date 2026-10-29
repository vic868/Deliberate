---
title: LangChain4j 入门
tags:
  - LangChain4j
  - Java
  - AI
created: 2026-10-29
status: completed
aliases:
  - LangChain4j 是什么
  - LangChain4j 快速开始
---

# LangChain4j 入门

> [!info] 这份笔记管什么
> 用 10 分钟搞清：LangChain4j 是什么、凭什么这么设计、它和 Spring AI / Python LangChain 的边界在哪、包里都有什么、**版本变动在哪（抄旧教程会踩的雷）**。
> 下一篇：[[2-核心概念]]

---

## 1. 一句话定位

> **LangChain4j = 给 Java 应用接大模型的"统一抽象层 + 声明式开发框架"。**
> 它的口号是 *"Unified API for LLM providers & vector stores"*——换模型、换向量库只改一行依赖/配置，业务代码不动。

和 Spring AI 最大的设计差异在这里：

| | LangChain4j | Spring AI |
|---|---|---|
| 你写的代码 | **一个接口 + 注解**，框架生成实现 | 命令式链式调用（`ChatClient.prompt().user().call()`）+ Advisor |
| 抽象层数 | 模型接口之上直接是"AI Service" | 模型接口之上是 `ChatClient` + `Advisor` |
| 一句话 | **契约式（Declarative）** | **管道式（Pipeline/Advisors）** |

```java
// LangChain4j：声明"我要什么"，不写"怎么做"
interface Assistant {
    @SystemMessage("你是资深 Java 工程师，回答简洁")
    String chat(@UserMessage String question);
}

Assistant ai = AiServices.builder(Assistant.class).chatModel(model).build();
String answer = ai.chat("什么是 IOC？");
```

> [!tip] 记忆锚点
> Spring AI 像 **MyBatis 的 `SqlSession` 手写调用**；LangChain4j 更像 **Spring Data JPA 的 Repository 接口**——你声明方法，框架替你实现。
> 后面 [[3-契约式开发]] 会把这条线展开，这也是"和 Spring AI 比，到底差在哪"的答案。

---

## 2. 它解决的是哪类问题

LLM 应用在 Java 侧的痛点从来不是"调 API"，而是：

1. **模型不统一**：OpenAI / DeepSeek / 通义 / Ollama / vLLM 参数名、流式协议、错误码都不一样
2. **向量库不统一**：Milvus / pgvector / Qdrant / Redis 的 SDK 风格各异
3. **RAG 要做的事很长**：加载 → 切分 → 向量化 → 入库 → 检索 → 融合 → 拼 prompt → 生成
4. **Agent 的循环要自己写**：判断要不要调工具 → 执行 → 回灌结果 → 再问模型 → 直到收敛
5. **工程能力缺失**：多会话记忆、结构化输出、护栏、可观测

LangChain4j 的选择是：**前 2 个做成"统一接口"，后 3 个做成"框架能力"**。所以它比"HTTP 客户端"重，比"LangChain Python 那种万能胶"轻。

---

## 3. 生态地图（依赖怎么挑）

```
dev.langchain4j
├── langchain4j                        ← 主包：AiServices / RAG / Agent / Guardrail
├── langchain4j-core                   ← 被自动带入：所有接口、数据结构
├── langchain4j-open-ai                ← OpenAI 协议模型（最大覆盖：DeepSeek/通义/vLLM/Ollama 兼容口）
├── langchain4j-ollama                 ← 本地 Ollama 原生协议
├── langchain4j-<其它模型>            ← azure-open-ai / anthropic / google-ai-gemini / mistral / ...
├── langchain4j-spring-boot-starter    ← Spring Boot 自动装配（beta 号）
└── 社区（dev.langchain4j:langchain4j-community-*）
    ├── milvus / pgvector / qdrant / redis / elasticsearch ...   ← 向量库
    └── 各种 loader / splitter / reranker
```

**最省事的起步依赖组合**（覆盖 90% 的国内场景）：

```xml
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j</artifactId>
    <version>1.23.0</version>
</dependency>
<dependency>
    <groupId>dev.langchain4j</groupId>
    <artifactId>langchain4j-open-ai</artifactId>
    <version>1.23.0</version>
</dependency>
```

> [!note] 为什么"国产模型 + OpenAI 协议"就够了
> DeepSeek、通义千问、智谱、Kimi、vLLM、Ollama 都提供 **OpenAI 兼容端点**。用 `langchain4j-open-ai` 把 `baseUrl` 指过去即可，不需要找专用集成件。
> 见下面 §6 的写法。

---

## 4. 版本与迁移雷区（**必看**）

### 4.1 当前版本事实（2026-10-29 核对）

| 组件 | 版本 | 备注 |
|---|---|---|
| `langchain4j` / `-core` / `-open-ai` | **1.23.0** | Maven Central `lastUpdated=2026-10-28` |
| `langchain4j-spring-boot-starter` | **1.23.0-beta33** | 集成件仍是 beta 号 |
| JDK 基线 | **17** | 1.x 需要 Java 17+，老项目 JDK 8/11 要先升 |

### 4.2 改名：`ChatLanguageModel` → `ChatModel`（**精确是 `1.0.0-rc1`，非 1.0.0**）

逐版本下载 `langchain4j-core` 用 `unzip -l` 查类是否存在（完整数据见 [[9-版本记录#3. ⭐ 用 jar 实测验证的关键改名（能省你半天）|9-版本记录 §3]]）：

```
0.36.2        ChatLanguageModel.class                （0.x 时代的类名）
1.0.0-alpha1  ChatLanguageModel.class
1.0.0-beta3   ChatLanguageModel.class
1.0.0-rc1     ChatModel.class                        ← 就在这一版切换
1.23.0        ChatModel.class                        （ChatLanguageModel 已不存在）
```

> [!warning] 别笼统说"1.0 改的名"
> `1.0.0-alpha1 ~ 1.0.0-beta3`（2024-12 ~ 2025-04）**仍然是 `ChatLanguageModel`**。
> 准确分界线是 **`1.0.0-rc1`（2025-05-02）**。

**影响**：网上 2023~2024 年的大量教程、博客、甚至部分面试题写的 `ChatLanguageModel` / `model.generate(...)` 在 1.x 上**直接编译不过**。

| 0.x 写法（旧） | 1.x 写法（新） |
|---|---|
| `ChatLanguageModel` | `ChatModel` |
| `StreamingChatLanguageModel` | `StreamingChatModel` |
| `StreamingResponseHandler<AiMessage>` | `StreamingChatResponseHandler`（`onPartialResponse` / `onCompleteResponse`） |
| `model.generate(String)` | `model.chat(String)` |
| `OpenAiChatModel.withApiKey(...)` | `OpenAiChatModel.builder()...build()` |

> [!warning] 面试/简历里别混
> 这正是 [[面试准备/专业技能/01-AI应用工程化|AI 应用工程化]] 里提醒的点：**Python 的 LangChain ≠ Java 的 LangChain4j**；同理，**LangChain4j 0.x ≠ 1.x**。被追问版本时含糊，比说错更减分。

### 4.3 其它常见迁移坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `NoSuchMethodError` / 类找不到 | 主包与集成件版本不匹配 | 统一 `1.23.0` + `1.23.0-beta33`，用 BOM 管 |
| `ToolExecutionRequest.from(...)` 报错 | 参数是 JSON 字符串，不是可变参数 | `ToolExecutionRequest.builder().name(n).arguments(json)` |
| 编译期 `@Tool` 找不到 | 确认 `dev.langchain4j:langchain4j` 在主包（在 `langchain4j-core` 里也有同名包，别只加 core） | 加完整依赖 |
| `DocumentSplitters.recursive()` 运行时报 `NoClassDefFoundError: opennlp/...` | **切分器依赖 opennlp**（见 §5） | 加 opennlp 或用自实现切分 |

---

## 5. ⭐ 实测：切分器的隐藏依赖

```text
java.lang.NoClassDefFoundError: opennlp/tools/sentdetect/SentenceModel
    at dev.langchain4j.data.document.splitter.DocumentBySentenceSplitter.createSentenceModel
    at dev.langchain4j.data.document.splitter.DocumentByParagraphSplitter.defaultSubSplitter
    at dev.langchain4j.data.document.splitter.HierarchicalDocumentSplitter.<init>
```

- `DocumentSplitters.recursive(...)` / `DocumentByParagraphSplitter` / `DocumentByLineSplitter` 的**默认子切分器**是 `DocumentBySentenceSplitter`，它构造时就会 `new SentenceModel(...)`，而 `langchain4j-core` 的 pom **并不带 opennlp**
- 结论：**1.23.0 上用自带切分器，必须自己补 opennlp 依赖**，否则一运行就炸（编译期看不出来）

两种解法：

```java
// 解法 A：自己写切分（不依赖任何分词库，最稳，本笔记示例都用它）
static List<TextSegment> fixedSplit(String text, int size) {
    List<TextSegment> out = new ArrayList<>();
    int overlap = Math.max(0, size / 5);
    for (int start = 0; start < text.length(); start += (size - overlap)) {
        int end = Math.min(text.length(), start + size);
        out.add(TextSegment.from(text.substring(start, end)));
        if (end == text.length()) break;
    }
    return out;
}
```

```xml
<!-- 解法 B：把 opennlp 补上（注意版本与制品可用性，别盲抄） -->
<dependency>
    <groupId>org.apache.opennlp</groupId>
    <artifactId>opennlp</artifactId>
    <version>2.5.12</version>
</dependency>
```

> [!warning] opennlp 版本别乱写
> 核对 Maven Central 时发现：`opennlp` 的 2.5.x 目录下**只有 source-release 和 pom，没有 jar**（jar 可能拆到了 `opennlp-core` 等模块）。也就是说**解法 B 需要自己确认制品真实存在**，别抄一个版本号就上。
> 生产更推荐的方案：用更专业的切分（按标题/段落 + 递归），把工具库的选择决策写进 [[4-RAG]] 的评估里，而不是被一个默认值绑架。

---

## 6. 第一个可跑的例子（指向国产模型）

```java
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import java.time.Duration;

ChatModel model = OpenAiChatModel.builder()
        .baseUrl("https://api.deepseek.com/v1")   // 兼容 OpenAI 协议的任意端点
        .apiKey(System.getenv("DEEPSEEK_API_KEY"))
        .modelName("deepseek-chat")
        .temperature(0.3)
        .timeout(Duration.ofSeconds(60))
        .logRequests(true)       // 调试期打开，能看到真实请求体
        .logResponses(true)
        .build();

System.out.println(model.chat("用一句话解释 RAG"));
```

> [!tip] 没有 Key 怎么练
> 两个办法：
> 1. **Ollama 本地跑**：`langchain4j-ollama` 或直接用 openai 兼容口 `http://localhost:11434/v1`
> 2. **假模型**：自己实现 `ChatModel` 接口，返回脚本化的 `AiMessage`——本套笔记就是这么离线验证框架行为的（见 [[3-契约式开发]] §6 与 [[5-Agent工具调用]] §3）⭐

---

## 7. 什么时候该用 / 不该用

| 场景 | 建议 |
|---|---|
| 新项目、团队熟悉 Spring | **Spring AI 更顺**（和你的学习规划一致） |
| 要大量用"接口式"业务能力（客服、工单分类、摘要） | **LangChain4j 的 AiServices 更省代码** |
| 已经在用 LangChain4j 的老项目 / 要维护别人的代码 | 必须会 |
| 需要它的 RAG/Agent 抽象（QueryTransformer、ContentAggregator）开箱即用 | LangChain4j 模型更完整 |
| 只需要"调个模型 + 简单对话" | 两个框架都算重，直接 HTTP 都行 |
| 复杂多 Agent 图编排 | 都不是强项，看 LangGraph / 自研状态机（见 [[14-AI agent /1-LangChain/2-LangChain学习地图\|LangChain 学习地图]]） |

详细对比和面试讲法 → [[7-选型对比与面试]]

---

## 8. 延伸

- 官方文档：<https://docs.langchain4j.dev>
- GitHub：<https://github.com/langchain4j/langchain4j>
- 教程页：<https://docs.langchain4j.dev/tutorials/>
- 下一步：[[2-核心概念]] → [[3-契约式开发]]
