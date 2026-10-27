---
title: LangChain 进阶学习地图
tags:
  - LangChain
  - LangGraph
  - RAG
  - Milvus
  - 学习计划
created: 2026-10-27
status: 进行中
next: RAG 进阶
---

# LangChain 进阶学习地图

> [!info] 这份笔记管什么
> 第一阶段（LangChain 基础 / 工具调用 / LangGraph 核心 / FastAPI+SSE / RAG+Milvus）已经完成。
> 这里把**下一阶段的全部内容**整理成「目标 → 知识点 → 动手任务 → 验收标准 → 资源」，并用下方清单跟踪进度。
> 配套图：[[0-LangChain.drawio]]（基础） · [[1-LangChain进阶.drawio]]（这一阶段的总览）
> 可编辑版（单个部分）：[[2-LangGraph进阶.vector.drawio]] · [[3-RAG进阶.vector.drawio]] · [[4-生产化改造.vector.drawio]] · [[5-可观测与评估.vector.drawio]]

## 0. 总览

| 方向 | 优先级 | 关键词 | 产出 | 完成 |
|---|---|---|---|---|
| RAG 进阶 | 🔴 先做 | 切分 / Embedding 选型 / Hybrid+BM25 / Rerank / 拼接 / 离线建库 | 检索指标有前后对比的「个人知识库问答」 | ⬜ |
| LangGraph 进阶 | 🟡 | HITL / Subgraph / Multi-Agent / update_state 修复 | 带人工审批 + 多 Agent 流水线的 Agent | ⬜ |
| 生产化改造 | 🟡 | PostgresSaver / Milvus Standalone / 多会话 UI / token 流式 | 重启不丢会话、可多会话切换的 Web 应用 | ⬜ |
| 可观测与评估 | 🟢 贯穿始终 | LangSmith / 自建 logging / 自动评估 | 一条命令跑出「改动前后」对比报告 | ⬜ |

**建议顺序**：RAG 进阶（1）→ LangGraph 进阶（2）→ 生产化（3）与可观测（4）并行。
理由：RAG 是现阶段收益最大的部分；生产化里的 **Milvus Standalone** 恰好是 RAG 里 **BM25 / 多租户** 的前置条件；可观测越早接入越好，能帮你做后面所有改动的对比。

> [!warning] 一个前置提醒
> 你的 conda 环境里 **base 是 langchain 0.2.14（旧版）**，没有 `create_agent` / `middleware`，`langchain-milvus` 也没装。
> 动手前先建独立环境：`conda create -n learn-lc python=3.12 -y && conda activate learn-lc && pip install -U langchain langchain-openai langgraph langgraph-checkpoint-postgres langchain-milvus pymilvus langsmith python-dotenv fastapi uvicorn`

---

## 1. RAG 进阶 🔴

> [!abstract] 目标
> 从「把整篇切块塞进向量库」升级到**能测、能调、能解释为什么变好**的检索系统。
> 验收：同一批 30 条 query，任意改动（切分 / embedder / rerank / 拼接）都能给出 Hit@5、MRR 的前后对比。

### 1.1 更聪明的切分
- [ ] **Recursive 递归切分**（默认基线）：`RecursiveCharacterTextSplitter` 按 `["\n\n", "\n", " ", ""]` 逐级降级；`chunk_size` 与 `chunk_overlap` 是两个主旋钮
- [ ] **中文要换分隔符**：默认分隔符对中文不友好，要加入全角逗号 `，`、顿号 `、`、句号 `。`，避免把词切成两半
- [ ] **按 Markdown 标题切**：`# / ##` 分层切，把标题层级写进 `metadata`（`section` / `h1` / `h2`），命中后能知道出自哪一节
- [ ] **语义切分（实验性）**：基于相邻句子向量相似度找断点，更贴合语义但更慢、不稳定，适合高价值语料
- [ ] 组合策略：**先按结构（标题/章节）切，再在段内用 Recursive 保底**
- [ ] 记录 `chunk_size` / `overlap` 与检索指标的对照表

> [!tip] 评测法
> 固定 embedder，扫 `chunk_size ∈ {256, 512, 1024}`、`overlap ∈ {0, 10%, 20%}`，在固定 query 集上看 Hit@5 和「拼接后的回答质量」。**没有评测就不要调参。**

### 1.2 Embedding 模型选型
- [ ] 候选池：`text-embedding-3-small/large`（API，1536/3072 维，中上）、`bge-m3`（1024 维，多语言，可同时出稠密+稀疏）、`nomic-embed-text`（768 维，本地 Ollama，免费快）
- [ ] 对比维度：中文效果、维度与存储成本、延迟、是否自托管、是否支持稀疏/多语言
- [ ] 对比方法：**同一份切分 + 同一批 query + 同一建库流程，只换 embedder**，看指标与成本
- [ ] 换 embedder = 全量重建向量库；把模型版本写进 collection 名或 `metadata`（便于回滚）

> [!note] 结论性经验
> 中文知识库（尤其是笔记类）优先试 `bge-m3`；要快、要免费、要私有部署选 `nomic-embed-text`；要最省心选 `text-embedding-3-small`。**最终用你自己的数据说话。**

### 1.3 检索后处理：Hybrid + Rerank
- [ ] **Hybrid Search = 向量 + BM25**：查询含编号、专有名词（如「TS-999」）时 BM25 命中精确串，稠密向量经常漏检
- [ ] Milvus 内置 BM25：`BM25BuiltInFunction()`，喂原始文本、由服务端生成稀疏向量，`vector_field=["dense", "sparse"]`
- [ ] 融合策略：`ranker_type="rrf"`（RRF，稳健默认）或 `ranker_type="weighted", ranker_params={"weights":[0.6, 0.4]}`
- [ ] **Rerank 精排**：初检 top 20~50 → 交叉编码器（如 bge-reranker）打分 → 取 top 3~5；把 `rerank_score` 写回 `metadata` 便于调试
- [ ] 混合检索 + 精排的收益要用指标量化

> [!warning] 坑
> **BM25 内置函数需要 Milvus Standalone / Distributed，Milvus Lite 不支持**（这正是「生产化」里要换 Docker 版的原因）。
> 中文分词要设置 `analyzer_params`，否则 BM25 可能按空格切。

> [!success] 为什么值得做
> Anthropic 的 Contextual Retrieval 实测：Contextual Embeddings 单独让 top-20 检索失败率降低 **35%**，再加上 Contextual BM25 共降低 **49%**，再加 rerank 共降低 **67%**。

### 1.4 Prompt 里怎么拼检索结果
- [ ] **带来源与定位**：每条标注 `[id]` + 标题 + 来源路径 + 段落号，要求回答引用 `[id]`
- [ ] **去重与截断**：按 parent doc 去重、单文档最多 k 条、每条截断到 800~1500 字
- [ ] **顺序有讲究**：最相关的放最前，其次最后（关键信息在开头结尾，中间容易丢）
- [ ] **上下文增强**：切分时给每个 chunk 拼上标题 / 上级标题 / 段落摘要（Contextual Retrieval 思路）
- [ ] **明确边界**：「只根据给定资料回答，资料里没有就说不知道」
- [ ] **稳定标签**：`<context>...</context>` 结构固定，区分「资料」与「指令」

### 1.5 离线建库脚本（PDF / Markdown / 网页批量 ingest）
- [ ] 流水线：`Loader → Splitter（+元数据）→ Embedding（批量）→ Milvus（写库+索引）→ Manifest`
- [ ] 每个 chunk 带 `source / title / section / page / content_hash`
- [ ] 用 `content_hash` 去重，用 manifest（文件名 + mtime + embedding 版本）做增量与幂等
- [ ] 先 100 篇跑通再全量；失败可断点续跑
- [ ] PDF 表格与扫描页单独处理（OCR）

### 1.6 先自建评估（可观测的前置）
- [ ] 固定 query 集 30~100 条（事实 / 多跳 / 口语各占一部分），标注正确 chunk id
- [ ] 检索指标：`Hit@5` / `Recall@20` / `MRR`（不需要 LLM，便宜且稳定）
- [ ] 回答指标：LLM-as-judge 评正确性 / 忠实度 / 引用是否支持结论
- [ ] 每次改动重跑同一批，指标不能掉

---

## 2. LangGraph 进阶 🟡

> [!abstract] 目标
> 从「线性图 + MemorySaver」升级到**能停下来等人、能嵌套、能多 Agent 协作、出错能修**的图。
> 验收：暂停 / 恢复 / 改 state 全部跑通；多 Agent 流水线能在 LangSmith 里看到一棵清晰的 trace 树。

### 2.1 Human-in-the-loop（人工确认 / 改 state / 补参数）
- [ ] 需要：`checkpointer` + `config={"configurable": {"thread_id": ...}}` + 在节点里调用 `interrupt(payload)`
- [ ] 恢复：`graph.invoke(Command(resume=<答案>), config)`，resume 值成为 `interrupt()` 的返回值
- [ ] 注意：**必须同一个 thread_id**；节点内 `interrupt()` **之前的代码在恢复后会重跑**，所以前面的逻辑要幂等
- [ ] 静态断点 = 在节点前后暂停；**动态中断** = 代码里任意位置、可带条件
- [ ] `interrupt(payload, response_schema=Decision)`（langgraph ≥ 1.2.12）可让 resume 值被 Pydantic 校验，不合规时用同 thread_id 重试

```python
from langgraph.types import interrupt, Command

def approval_node(state):
    decision = interrupt({"question": "Approve this action?", "details": state["action_details"]})
    return Command(goto="proceed" if decision else "cancel")

graph.invoke({"action_details": "Transfer $500"}, config)      # 暂停
# 结果里看 result["__interrupt__"]（或新版 stream 的 stream.interrupts）
graph.invoke(Command(resume=True), config)                     # 恢复
```

- [ ] **中途改 state**：`graph.update_state(config, {"draft": 新值}, as_node="上一节点名")` 再 `graph.invoke(None, config)`
- [ ] 易错点：忘了 checkpointer / thread_id；重复 resume 导致重复执行；在 `interrupt()` 前面写库造成重跑重复写

### 2.2 Subgraph 子图
- [ ] `graph.add_node("sub", compiled_subgraph)`：把编译后的图当节点塞进父图
- [ ] state 自动按 schema 映射；父图只暴露需要的字段，别让子图污染顶层 state
- [ ] 两种嵌法：当节点（内部节点不外露） vs 嵌套（父子各有 checkpointer，各自独立）
- [ ] 自检：父图 `get_state_history` 能看到子图调用；子图内部出错时父图 state 不半写；`graph.stream(subgraphs=True)` 能看到层级

### 2.3 Multi-Agent 协作（Researcher → Coder → Reviewer）
- [ ] Supervisor / Orchestrator：中央调度，决定谁干活、何时结束（易调试，多一跳）
- [ ] Swarm：Agent 之间直接交接（省一跳，难追踪）
- [ ] 状态设计：`messages`（共享对话）、`plan/todo`（任务清单）、`artifacts`（各 Agent 产出）、`review`（评审意见）、`next_agent`
- [ ] 交接与容错：每个 Agent 限制最大轮数；Reviewer 不通过要给出修改清单；一个 Agent 的产物写独立字段避免互相覆盖；关键交接点用 HITL
- [ ] 自检：LangSmith 里 trace 树清晰；没有 Agent 互相踢皮球；下游确实用到了上游产出

### 2.4 State 中断恢复（手动修复错误 state 后继续）
- [ ] `graph.get_state(config)`：看 `next` / `tasks` / 中断信息
- [ ] `graph.get_state_history(config)`：按 `metadata.step` 找快照；`metadata.source == "update"` 是手动改出来的
- [ ] **Replay**：`graph.invoke(None, 旧checkpoint的config)` 从该点重跑（会重新调 LLM，不是读缓存）
- [ ] **Fork**：`update_state(旧config, values, as_node=...)` 在旧 checkpoint 上新建分支，再 `invoke(None)`
- [ ] **恢复中断**：`Command(resume=...)`
- [ ] `as_node` 用于并行分支 / 新线程初始化 / 跳过节点；否则 LangGraph 会从版本历史推断
- [ ] **与「重试」的区别**：重试 = 同一输入再跑（要幂等）；update_state = 改输入再跑；Replay = 换起点重跑

> [!example] 练习
> 故意让一个工具抛异常 → `get_state` 看到失败节点 → `update_state` 修正参数 → `invoke(None)` 从失败处继续 → 在 `get_state_history` 里找到 `source=update` 的新快照。

---

## 3. 生产化改造 🟡

> [!abstract] 目标
> 从「本机 demo」升级到**敢重启、能多人用、前端体验好**的服务。
> 验收：重启服务后会话还在；两个进程共享同一 thread；前端逐字出现、可停止、可切换多会话。

### 3.1 会话持久化：MemorySaver → Postgres / Redis
| Saver | 安装包 | 适合 | 多进程 |
|---|---|---|---|
| `InMemorySaver` | `langgraph-checkpoint`（自带） | 本地开发 / 单测 | ✗ 重启即丢 |
| `SqliteSaver` | `langgraph-checkpoint-sqlite` | 单机 demo | ✗ 单写者 |
| **`PostgresSaver`** | `langgraph-checkpoint-postgres` | **生产首选**：事务、可查询 | ✓ |
| `Redis / Mongo Saver` | `langgraph-checkpoint-redis` 等 | 已有 Redis/Mongo 的团队 | ✓ |

- [ ] 启动时初始化一次 checkpointer（别每个请求 new）；`setup()` 首次建表
- [ ] FastAPI 用 `AsyncPostgresSaver` + `async with ... await cp.setup()`，全链路 async
- [ ] `thread_id` 用「用户 + 会话」规则生成，由前端传回
- [ ] thread 的标题 / 时间另存业务表，列表页别扫 checkpoint 表
- [ ] checkpoint 表增长要有 TTL / 归档策略；敏感会话可配 `EncryptedSerializer`
- [ ] 长期记忆：跨会话的 **Store**（InMemoryStore → PostgresStore / 向量 Store），与 checkpointer 分工

### 3.2 Milvus：Lite → Docker Standalone
- [ ] `curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh && bash standalone_embed.sh start`
- [ ] WebUI：<http://127.0.0.1:9091/webui>；连接 `http://localhost:19530`
- [ ] 动机：Lite 只有 FLAT 索引、**不支持 BM25 内置函数 / partition_key** → 混合检索与多租户必须上 Standalone
- [ ] 已有 Lite 数据：用建库脚本重新 ingest 最快
- [ ] 索引与 metric 建好后改动需重建 collection

> [!note] Milvus 3.0 方向（了解即可）
> 湖原生：External Collection 直接检索数据湖（Lance / Iceberg / Parquet）、在线增删字段、服务端 ORDER BY / 聚合、轻量 BM25 索引（体积约为 2.6 的 1/3）。个人项目先不用追新。

### 3.3 前端：多会话 + 知识库管理
- [ ] 多会话：列表（thread_id / 标题 / 时间）、新建、重命名、删除、切换后恢复历史（`get_state`）
- [ ] 流式展示：SSE 增量逐字渲染、显示当前节点（检索 / 生成）、停止按钮（AbortController）
- [ ] 知识库管理：上传、ingest 进度、文档列表（分块数 / 状态）、删除文档（按 metadata 过滤删向量）
- [ ] 调试面板：本次命中的 chunk 与分数、实际发送的 prompt 摘要、耗时拆解
- [ ] 交互：点赞 / 点踩 & 备注（回流到评估）；中断时展示「等待确认」按钮
- [ ] 接口约定：`POST /chat`（SSE）、`GET /threads`、`DELETE /threads/{id}`、`POST /kb/upload`、`GET /kb/docs`
- [ ] SSE 事件：`{type: token | node | tool | interrupt | error | done, data}`

### 3.4 token 级流式（`stream_mode="messages"`）
```python
async for chunk, meta in graph.astream(inputs, config, stream_mode="messages"):
    if chunk.content:
        yield sse({"type": "token", "text": chunk.content})
# 可叠加 stream_mode=["messages", "updates", "custom"]
```
- [ ] `messages` 是**所有 LLM 调用**的 token（含中间步骤），要区分最终答案就按节点名 / 标签过滤 `meta`
- [ ] 让模型真正逐字：用 `model.stream` / `astream`；`invoke` 也会发 token 事件（但一次性）
- [ ] 前端 fetch + ReadableStream 解析 SSE；Nginx 关 buffering；心跳保活
- [ ] 联调：断线重连（Last-Event-ID）、停止生成、错误事件统一格式、CORS

### 3.5 上线前自检
- [ ] 密钥全走环境变量 / 密钥服务，不进代码库
- [ ] 依赖锁版本（`uv lock` / `conda env export`），固定 embedder 与模型版本
- [ ] 并发限制与超时：单请求超时、LLM 重试（指数退避）、工具调用超时
- [ ] 日志含 `thread_id` / `run_id`，可与 trace 对齐
- [ ] `Docker Compose` 一键拉起：API + Milvus + Postgres

---

## 4. 可观测与评估 🟢

> [!abstract] 目标
> 任何一次线上问题，3 分钟内定位到「哪个节点 / 哪次 LLM 调用 / 命中了哪些 chunk」。
> 验收：一条命令跑出实验对比报告，并把「坏 case」沉淀进数据集。

### 4.1 LangSmith 追踪
- [ ] 开启：`LANGCHAIN_TRACING_V2=true`、`LANGCHAIN_API_KEY=...`、`LANGCHAIN_PROJECT=...`
- [ ] Run 树：graph invoke ▸ 节点 ▸ LLM ▸ tool；子图 / 子 Agent 自动展开
- [ ] 看什么：输入输出、延迟、Token、错误、命中的 chunk、实际 prompt
- [ ] 命名：给 run 加 `name` / `tags` / `metadata`（user_id、thread_id、知识库版本）
- [ ] 用法：定位慢/贵/错 → 加进数据集 → 把坏 case 一键转成评估样例
- [ ] 常见问题：一次请求几十个 LLM 调用 → Agent 循环没收住（ModelCallLimit / 限制轮次）
- [ ] 对比：两个 prompt / 两个模型各跑一批，用 experiments 并排看
- [ ] 隐私：用户原文脱敏，或只记 hash / 结构化摘要

### 4.2 自建 tracing + logging
- [ ] 请求层：`request_id` / `thread_id` / `user_id` / `trace_id`（贯穿日志与 trace）
- [ ] 每步节点：节点名、入参/出参摘要、耗时、重试次数、是否中断
- [ ] 每次 LLM：模型名、温度、prompt hash 与 token 数、输出摘要、费用估算
- [ ] 每次检索：query（改写后）、召回 id 与分数、融合方式、rerank 前后排名变化
- [ ] 每次工具：tool 名、参数、返回值摘要、异常栈、超时标记
- [ ] 落盘：结构化 JSON（ELK / Loki）或 SQLite，按 `trace_id` 串起一条链
- [ ] 最小实现：`@trace` 装饰器 + `contextvar` 传 `trace_id`，先保证「能串起来」，再谈可视化

### 4.3 自动评估（给定一批 query 自动跑）
- [ ] 数据集：LangSmith dataset，或本地 JSONL
- [ ] `target()`：调你的 RAG / Agent，返回 outputs
- [ ] evaluators：命中率 / 引用是否正确 / LLM-as-judge
- [ ] experiment：分数表 + 对比；不合格即阻断上线

```python
from langsmith import Client
client = Client()
results = client.evaluate(
    lambda inputs: {"answer": my_rag(inputs["q"])},
    data="my-rag-golden-v1",
    evaluators=[hit_at_5, citation_ok, llm_judge],
    experiment_prefix="v2-bge-m3+rerank",
)
```

- [ ] 指标分层：检索层（Hit@5 / Recall@20 / MRR）、生成层（正确性 / 忠实度 / 引用支持）、体验层（p95 延迟 / Token 成本 / 点赞率）
- [ ] 经验值：检索 20 条 → 精排 5 条喂模型；Hit@5 已 90%+ 时再堆 rerank 收益很小
- [ ] 先用 30 条小样本跑通闭环，再扩到 100+
- [ ] **DoD**：同一个 query 集上，任意改动都能一条命令出对比报告，坏 case 进数据集

> [!info] 替代方案
> 数据出境/合规敏感时用 **Langfuse** 或自建 OpenTelemetry（LangChain/LangGraph 内置 OTel 回调），接口不变，只换 SDK 配置。

---

## 5. 时间安排建议（约 6 周）

| 周 | 主题 | 本周要交付的东西 |
|---|---|---|
| 第 1 周 | 切分 + Embedding 选型 | 切分/embedder 对照表（Hit@5 / MRR） |
| 第 2 周 | Milvus Standalone + Hybrid + Rerank | 混合检索 vs 纯向量 vs +rerank 的三组指标 |
| 第 3 周 | 拼接优化 + 离线建库 | 一键 ingest 脚本 + 引用可回查的问答 |
| 第 4 周 | LangGraph：HITL + Subgraph | 带审批的 Agent（暂停/修改/恢复） |
| 第 5 周 | Multi-Agent + update_state 恢复 | Researcher→Coder→Reviewer 流水线 + 故障恢复演练 |
| 第 6 周 | 生产化 + 可观测 | PostgresSaver + 多会话 UI + token 流式 + LangSmith 评测报告 |

## 6. 参考资源

- LangChain / LangGraph 官方文档：<https://docs.langchain.com>
- LangGraph Interrupts（HITL 权威说明）：<https://docs.langchain.com/oss/python/langgraph/interrupts>
- LangGraph Checkpointers / Time travel（update_state、Replay、Fork）：<https://docs.langchain.com/oss/python/langgraph/use-time-travel>
- langchain-milvus（BM25 / Hybrid）：<https://docs.langchain.com/oss/python/integrations/vectorstores/milvus>
- Anthropic Contextual Retrieval（切分与混合检索的实测数据）：<https://www.anthropic.com/research/contextual-retrieval>
- Milvus 3.0 发布说明（湖原生方向）：<https://zilliz.com.cn/blog/milvus-3-0-release>
- Milvus 笔记：[[3-Milvus/0-Milvus.drawio]]

## 7. 进度记录

- [ ] RAG 进阶完成（指标对比表已建立）
- [ ] LangGraph 进阶完成（HITL + 多 Agent）
- [ ] 生产化完成（重启不丢会话、多会话 UI）
- [ ] 可观测完成（LangSmith + 自动化评测）
