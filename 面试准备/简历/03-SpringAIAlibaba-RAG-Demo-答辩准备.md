---
title: Spring AI Alibaba · RAG Demo 答辩准备
tags: [面试, 简历, AI, RAG, SpringAIAlibaba]
status: 进行中
---
 
# 🧩 Spring AI Alibaba · RAG Demo 答辩准备

> 返回 [[00-AI经历怎么讲与简历改写策略]]

> [!info] 你的真实情况
> 学习了大模型开发，**做了一个 demo 版 RAG，技术栈是 Spring AI Alibaba**。
> 这不是短板——**demo 不掉价，讲不出细节才掉价**。
> 这篇的目标：让你把这个 demo 讲得比"号称做过企业级项目"的人更可信。

---

## 一、简历怎么写（诚实且有力）

> [!tip] 关键：写「Demo / 个人实践项目」，别写「企业级实战」
> 面试官对"个人 demo"的心理预期本来就低，你把细节讲透就是超额交付。
> 反之写了"实战"却答不出生产问题，落差是致命的。

### 推荐写法

> **AI 应用工程化**：熟悉 LLM 工程化落地，掌握 Spring AI / LangChain 开发；
> 基于 **Spring AI Alibaba** 独立完成企业知识库 RAG Demo——文档切分、向量检索、
> Advisor 检索增强、流式输出与来源引用，并具备将其与现有 Java 微服务架构结合的设计能力

### 面试口述版（更自然）

> "AI 这块我是系统学习 + 自己动手做的。我用 **Spring AI Alibaba** 做了一个知识库 RAG 的 demo，
> 走通了从文档解析、切分、向量化、检索到生成的完整链路，用的是 ChatClient + Advisor 的模型增强模式。
> **我很清楚它离生产还有距离**——权限隔离、效果评估、成本控制这些我还没做，但我很清楚该怎么做。"

最后那句是加分项，不是减分项。**主动说出差距 = 有工程判断力。**

---

## 二、Spring AI Alibaba 速查（**名字要记准，说错就露**）

### 定位
以 **Spring AI 为基础**、深度集成**阿里云百炼平台**的 AI 框架；支持 ChatBot、工作流、多智能体三种开发模式。
1.0 GA 版本（文档对应 1.0.0.2）。

### 核心组件（按需引入）

| 组件 | 作用 |
|---|---|
| `spring-ai-alibaba-bom` | 统一版本管理 |
| **`spring-ai-alibaba-starter-dashscope`** | **百炼模型服务适配（通义千问）** ← 你大概率用了这个 |
| `spring-ai-alibaba-graph-core` | 智能体 Graph 框架（工作流 / 多智能体） |
| `spring-ai-alibaba-starter-nl2sql` | 自然语言转 SQL（ChatBI） |
| `spring-ai-alibaba-starter-memory` | 会话记忆 |
| `spring-ai-alibaba-starter-nacos-prompt` | Nacos Prompt 管理 |
| `spring-ai-alibaba-starter-arms-observation` | ARMS 可观测 |
| `spring-ai-alibaba-starter-nacos-mcp-client/server` | Nacos MCP 注册与发现 |
| community：`spring-ai-alibaba-starter-document-reader-*` | 文档读取（PDF/Word 等） |

### 版本对应关系（被问到能报出来很加分）
Spring AI Alibaba `1.0.0.2` ↔ Spring AI `1.0.0` ↔ Spring Boot `3.4.5`

### 与 Spring AI 的联系和区别（**高频对比题**）
- **Spring AI**：Spring 官方社区维护，**底层原子能力抽象**——ChatModel、Prompt、RAG、ChatMemory、Tool、MCP，侧重与 Spring Boot 无缝集成
- **Spring AI Alibaba**：**基于 Spring AI 构建**，继承其全部原子能力，额外提供：
  - 阿里云百炼模型与 RAG 知识库适配
  - **Graph 多智能体框架**（借鉴 LangGraph，可理解为 Java 版 LangGraph）
  - 企业级生态：Nacos MCP Registry、Higress AI 网关、ARMS/Langfuse 可观测

### 核心 API（你的 demo 一定用过）
```java
Flux<String> response = chatClient.prompt(query)
        .tools(toolCallbacks)                    // 工具调用
        .advisors(new QuestionAnswerAdvisor())   // RAG 检索增强
        .stream()                                // 流式
        .content();
```

> [!important] 一个必须记住的概念：**The Augmented LLM（模型增强模式）**
> AI 应用 ≠ 裸调大模型。要在模型调用上挂载 **RAG（领域数据）+ Memory（会话记忆）+ Tools（工具）**。
> 这句话说出来，面试官会知道你懂"AI 应用开发"和"调 API"的区别。

---

## 三、Demo 里必须能讲清的 6 件事（**现在就回填**）

> [!danger] 这 6 个问题必被问，答不上就等于没做过
> 建议现在打开你的 demo 代码，把下面每一项的真实答案填进去。

- [ ] **1. 语料是什么、多少量**
      → 用了什么文档？（比如：某产品的接口文档 / 公司 FAQ / 公开资料）大概多少个文件、多少片段？
- [ ] **2. 切分策略**
      → chunk 多大？（token 或字符）重叠多少？为什么这么设？
      → 答法参考：300-500 token + 10-20% 重叠；太大稀释语义，太小丢上下文
- [ ] **3. Embedding 与向量库**
      → embedding 用的哪个模型？（DashScope 的 text-embedding-v? ）
      → 向量库用的什么？（内存版 / Redis / AnalyticDB / Milvus / pgvector）为什么选它？
- [ ] **4. 检索参数**
      → Top-K 设多少？相似度阈值？用的余弦还是内积？
      → 有没有做混合检索（向量 + 关键词）？如果没有，**要能说出为什么需要**
- [ ] **5. 增强怎么做的**
      → `QuestionAnswerAdvisor` 具体做了什么？（把检索到的文档拼进 Prompt）
      → 有没有做来源引用？（这个很关键，做了就一定要讲）
- [ ] **6. 效果怎么验证的**
      → 哪怕只是"我准备了 20 个问题，人工看答对了几个" —— **也比说"效果挺好的"强 10 倍**
      → 有数字就报数字，没有就诚实说"还没做系统评估"

---

## 四、高频追问与答法（Spring AI Alibaba 专属）

| 追问 | 得分骨架 |
|---|---|
| **为什么用 Spring AI Alibaba，不用 LangChain4j 或原生 Spring AI？** | ① 我主要用通义千问，SAA 对**百炼平台**的适配最直接 ② 基于 Spring AI，**和 Spring Boot 生态无缝**，我 Java 背景上手快 ③ 它还提供 Graph 多智能体、NL2SQL、Nacos MCP 这些企业级组件，后续扩展路径清楚 |
| **ChatClient 和 ChatModel 区别？** | `ChatModel` 是**底层模型抽象**（对应具体模型实现）；`ChatClient` 是**面向开发者的高层门面**，支持 fluent API、Advisor 链、流式，类似 `JdbcTemplate` vs `DataSource` |
| **Advisor 是什么？和 AOP 什么关系？** | 本质就是**拦截器/责任链**，在模型调用前后插入逻辑：RAG 检索、对话记忆、日志、内容审核；`QuestionAnswerAdvisor` 就是在调用前检索并把文档塞进 Prompt。**设计思路和 AOP 一致** |
| **RAG 在 Spring AI 里怎么实现？** | 两条路：① **Advisor 方式**（`QuestionAnswerAdvisor`，最简）② **ETL Pipeline**（`DocumentReader` → `TextSplitter` → `VectorStore` 写入）。生产上两者配合 |
| **向量库为什么选它？** | 按数据量/运维成本/是否已有中间件来选；demo 用内存版（`SimpleVectorStore`）最快，生产会考虑 pgvector（已有 PG）或 AnalyticDB/Milvus |
| **流式怎么做的？** | `stream().content()` 返回 `Flux<String>`，通过 **SSE** 推给前端；注意断线重连与半截输出 |
| **对话记忆怎么做？** | `ChatMemory` + `MessageWindowChatMemory`（窗口）+ 存储后端；多轮场景还要做 **Query 改写**（把"它多少钱"结合历史补全）再检索 |
| **Graph 框架了解吗？** | 知道：借鉴 LangGraph，用于**工作流和多智能体**，内置 ReAct Agent、Supervisor 模式，预置 `LlmNode`/`QuestionClassifierNode`/`ToolNode`，支持 Human-in-the-loop 和流程快照。**我没深入用，demo 用的是 ChatClient 路线**（诚实说法） |
| **MCP 是什么？** | Model Context Protocol，标准化"模型 ↔ 工具/数据源"接入；SAA 通过 **Nacos MCP Registry** 做分布式注册发现，还能把存量 HTTP API 零改造发布成 MCP 服务 |

---

## 五、⭐ 必杀题：「如果要上生产，你觉得还缺什么？」

> [!important] 这题是 demo 和生产的试金石
> 答好了，面试官会觉得"这人虽然只做了 demo，但工程意识是生产级的"。
> **按下面 8 条说，挑 4-5 条讲透就够。**

| # | 缺口 | 具体怎么做 |
|---|---|---|
| 1 | **文档级权限隔离** | 文档打租户/部门标签，**检索时强制过滤**；绝不能"先检索再过滤"（会泄漏） |
| 2 | **效果评估体系** | 建评测集（问答对），度量召回率、忠实度；离线回归 + 线上 A/B + 人工抽检 |
| 3 | **成本控制** | Prompt 缓存、结果缓存、模型分层（简单问题走小模型）、限制输出长度 |
| 4 | **稳定性** | 超时 + 重试（指数退避）、多模型降级、兜底话术、限流熔断 |
| 5 | **可观测** | Trace 串起检索→重排→生成，记录 token 与耗时；SAA 有 `arms-observation`，也可接 Langfuse |
| 6 | **安全** | Prompt 注入防护、输入输出内容审核、敏感信息脱敏 |
| 7 | **知识更新** | 增量索引 + 文档版本管理；删除要同步删向量；定期全量重建兜底 |
| 8 | **检索质量** | 混合检索（向量 + BM25）、Rerank 重排、Query 改写、元数据过滤 |

**话术**：
> "我这个 demo 只跑通了主链路。要上生产，我觉得最优先的是三件事：
> 一是**权限隔离**——企业知识库必须做文档级过滤，而且要在检索条件里过滤，不能检索完再筛；
> 二是**效果评估**——没有评测集就没法判断改动是变好还是变坏；
> 三是**成本和稳定性**——Prompt 缓存 + 模型分层控成本，超时重试和降级保可用。
> 这三块我心里有方案，只是 demo 阶段没做。"

---

## 六、把 demo 和你的业务经历接起来（**这是你的独特优势**）

> 面试官会问："你这个 demo 和我们业务有什么关系？"
> 你正好有两个真实业务场景可以对接（详见 [[01-酒店送物机器人-项目描述]] / [[02-回收站点积分平台-项目描述]]）：

- **回收平台的垃圾分类问答** → 各地标准不同且常更新，**正是 RAG 的标准场景**（微调不现实）
- **酒店送物机器人的语音下单** → LLM 做意图识别 + 槽位抽取 + Function Calling
- 两个场景都涉及**多租户/多站点隔离** → 正好对应 RAG 的权限过滤

**话术**：
> "我那个 demo 用的是通用文档。不过我很想把它用在实际业务上——
> 比如回收平台，各地垃圾分类标准都不一样，做成知识库让居民直接问，
> 这是 RAG 最典型的场景。我现在缺的就是一个真实业务场景。"

---

## 🔗 关联

- [[00-AI经历怎么讲与简历改写策略]]
- [[面试准备/专业技能/01-AI应用工程化]]（RAG / Agent 通用技术细节）

#面试 #简历 #AI #RAG #SpringAIAlibaba #待补
