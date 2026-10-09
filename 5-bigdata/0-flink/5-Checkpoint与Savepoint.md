---
title: Checkpoint 与 Savepoint
tags: [Flink, Checkpoint, Savepoint, 容错]
status: 进行中
created: 2026-10-09
---

# 📸 五、Checkpoint 与 Savepoint

> 本篇聚焦**快照机制本身**：Checkpoint 怎么触发、里面到底存了什么、状态存在哪、怎么做增量、恢复时发生了什么、以及 Savepoint 和它的区别与正确用法。
> 语义与算法原理（Barrier 对齐、Chandy-Lamport、端到端 EOS）见 [[4-容错与ExactlyOnce]]；本篇更偏"**配置与运维视角**"。
> 关联：[[3-状态管理]]（状态是什么）、[[6-背压与性能调优]]（Checkpoint 调优）、[[9-部署与运维]]（升级与扩缩容）。

---

## 一、Checkpoint 到底解决了什么问题

### 1.1 一句话定义

> **Checkpoint 是 Flink 周期性生成的、全局一致的作业状态快照；作业故障时，从最近一次成功的 Checkpoint 恢复，使结果与"没有发生故障"等价。**

### 1.2 它必须满足的两个性质

| 性质 | 含义 | 靠什么保证 |
|---|---|---|
| **一致性** | 快照对应"数据流上的某一个逻辑时间点"，不能出现"上游算了、下游没算"的错位 | **Barrier 对齐** + 快照包含 source 位点 |
| **可恢复性** | 恢复后能从正确位置继续，不丢不重（配合 Sink 能力） | 位点 + 状态 + Sink 提交协议 |

> [!note] 与"存盘"的本质区别
> 普通业务系统"定期把内存写到磁盘"不保证一致性：写盘过程中并发修改会导致**撕裂的状态**（一部分是旧值、一部分是新值）。
> Flink 的一致性快照要保证**所有算子看到的是同一个逻辑时间点**——这才是 Barrier 存在的意义（原理见 [[4-容错与ExactlyOnce]]）。

### 1.3 Checkpoint 里存了什么

| 内容 | 说明 |
|---|---|
| **算子状态** | 每个算子的 Keyed State / Operator State（如聚合中间值、join 的缓存、去重集合） |
| **Source 位点** | Kafka offset、文件位置等，**恢复时从这里重放** |
| **元信息** | 各算子的 uid、状态句柄、并行度、`maxParallelism` 等 |

> [!warning] 最容易答错的一点
> **Kafka Consumer 提交回 Kafka 的 offset 与 Flink 恢复无关！**
> Flink 恢复只使用 **Checkpoint 中记录的位点**。`commit.offsets.on.checkpoint` 把位点提交给 Kafka 只是为了让**外部监控/其他消费者**看到进度。
> 面试若答"Kafka 提交了 offset 所以能恢复"，直接扣分。

---

## 二、触发与生命周期

### 2.1 配置

```java
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

// 每 60 秒触发一次 checkpoint，10 分钟超时
env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);

CheckpointConfig cfg = env.getCheckpointConfig();
cfg.setCheckpointTimeout(600_000);              // 单次 CK 超时时间
cfg.setMinPauseBetweenCheckpoints(30_000);       // 两次 CK 之间的最小间隔（防 CK 霸占资源）
cfg.setMaxConcurrentCheckpoints(1);              // 同时进行的 CK 数（>1 会放宽一致性）
cfg.setTolerableCheckpointFailureNumber(3);      // 连续失败多少次才判定作业失败
cfg.setExternalizedCheckpointCleanup(            // 作业取消后是否保留 CK
    CheckpointConfig.ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION);

// 存储位置（与状态后端解耦，见 §4）
cfg.setCheckpointStorage("hdfs:///flink/checkpoints");
```

或 `flink-conf.yaml`：

```yaml
execution.checkpointing.interval: 60s
execution.checkpointing.mode: EXACTLY_ONCE
execution.checkpointing.timeout: 10min
execution.checkpointing.min-pause: 30s
execution.checkpointing.max-concurrent-checkpoints: 1
execution.checkpointing.tolerable-failed-checkpoints: 3
execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION
state.checkpoints.dir: hdfs:///flink/checkpoints
```

> [!tip] 关键参数怎么权衡
> | 参数 | 调大的好处 | 调大的代价 |
> |---|---|---|
> | `interval`（间隔） | CK 开销小、吞吐高 | **故障后重放的数据多**（重复量大、恢复慢） |
> | `timeout` | 大状态作业不易失败 | 卡住的 CK 会拖很久才判定失败 |
> | `min-pause` | 给数据处理让路，避免 CK 抢占资源 | 高负载下 CK 触发频率下降 |
> | `max-concurrent` | CK 不易堆积失败 | **>1 时全局一致性变弱**（配合 `AT_LEAST_ONCE` 语义） |
> 经验：从 **1~5 分钟间隔**起步，按"可接受的重复数据量"倒推调整。

### 2.2 生命周期（6 步）

| 步骤 | 动作 | 负责者 |
|---|---|---|
| 1 | 触发：到达间隔时间，或手动触发 | **JobMaster**（CheckpointCoordinator） |
| 2 | 向所有 Source 注入 **Barrier** | JobMaster → Source |
| 3 | Barrier 随数据流传播，算子**对齐**后快照本地状态 | 各 Task |
| 4 | 状态异步上传到 **Checkpoint Storage**（DFS/对象存储） | 各 Task |
| 5 | 各 subtask 上报 ack 给 JobMaster | Task → JM |
| 6 | 全部 ack 到齐 → 标记为 **completed**，新 CK 成为恢复点 | JobMaster |

> [!important] "完成"才有效
> 只有**全部 subtask 都确认**的 Checkpoint 才是 completed；任何一步失败/超时，这次 Checkpoint 作废。**恢复只使用最近的 completed Checkpoint**。
> 这也是为什么"Checkpoint 一直失败"是严重事故：作业一直在跑，但**没有可用的恢复点**。

---

## 三、Barrier 与对齐（配置视角）

算法细节见 [[4-容错与ExactlyOnce]]，这里只讲**对齐的代价与选择**。

| 模式 | 行为 | 语义 | 速度 |
|---|---|---|---|
| **对齐 (Aligned)** | 等到所有输入的 Barrier 都到齐，期间**先到的数据要缓存** | `EXACTLY_ONCE` | 反压时**慢**（可能超时） |
| **不对齐 (Unaligned)** | Barrier **越过**缓冲区，把 in-flight 数据一起快照 | `EXACTLY_ONCE` | **快**，但 CK 体积更大 |
| 不保证（`AT_LEAST_ONCE`） | 不对齐、不阻塞 | 至少一次 | 最快 |

```yaml
# 开启非对齐 checkpoint（1.11+）
execution.checkpointing.unaligned: true
execution.checkpointing.aligned-checkpoint-timeout: 30s   # 对齐超过该时长则转为非对齐
# 非对齐 CK 允许的 in-flight 数据上限（保护 CK 体积）
execution.checkpointing.unaligned.max-subtasks-per-channel-state-file: 5
```

> [!tip] 什么时候用非对齐
> **持续背压导致 Checkpoint 频繁超时**时首选。代价：CK 体积变大（含 in-flight 数据）、恢复时要重放这些数据。
> 若作业**没有明显背压**，用默认的对齐模式即可，不必付额外代价。详见 [[6-背压与性能调优]]。

---

## 四、状态后端与 Checkpoint 存储（1.13+ 已解耦）

这是 Flink 状态管理最重要的一个认知更新：**"状态放在哪"与"快照放在哪"是两件独立的事**。

| 维度 | 状态后端（State Backend） | Checkpoint 存储（Checkpoint Storage） |
|---|---|---|
| 管什么 | 运行时**工作状态**存在哪 | **快照**写到哪 |
| 选项 | `HashMapStateBackend`（JVM 堆）<br>`EmbeddedRocksDBStateBackend`（本地磁盘 RocksDB） | JobManager 堆内存<br>文件系统 / 对象存储（HDFS/S3/OSS） |
| 配置 | `state.backend: hashmap` / `rocksdb` | `state.checkpoints.dir` / `state.savepoints.dir` |

```yaml
# 大状态推荐组合：RocksDB + 分布式存储
state.backend: rocksdb
state.checkpoints.dir: hdfs:///flink/checkpoints
state.savepoints.dir: hdfs:///flink/savepoints

# 增量 checkpoint（仅 RocksDB 支持，能极大降低 CK 体积与耗时）
state.backend.incremental: true

# RocksDB 本地目录（建议多盘分摊）
state.backend.rocksdb.localdir: /data1/flink/rocksdb,/data2/flink/rocksdb
```

| 组合 | 状态位置 | 适用 |
|---|---|---|
| HashMap + JM 内存 | 堆内存 | 本地测试/极小状态 |
| HashMap + DFS | 堆内存 | 中小状态、要求低延迟 |
| **RocksDB + DFS** | 本地磁盘 | **大状态（TB 级）、生产标准配置** |

> [!warning] RocksDB 的本地磁盘不是"可丢弃缓存"
> RocksDB 状态落在 TaskManager 的**本地磁盘**，但它**不是纯缓存**——恢复时 Flink 仍会从 Checkpoint 拉取全量状态重建。因此：
> ① 本地盘要有足够空间与 IOPS；② 恢复速度受**从 DFS 下载状态的时间**影响；③ 用**增量 Checkpoint** 可显著缩短恢复（只上传/下载变化的 SST 文件）。
> Flink 2.0 的 **Disaggregated State（ForSt）**正是为了解决"本地磁盘受限 + 扩缩容慢"，把远程 DFS 作为主存储（见 [[3-状态管理]]）。

### 4.1 增量 Checkpoint 的原理

| 普通（全量）Checkpoint | 增量 Checkpoint |
|---|---|
| 每次把**全部状态**上传到 DFS | 只上传**自上次以来新增/变化的 SST 文件** |
| 状态越大，CK 越慢、体积越大 | 首次全量，之后增量；**体积与耗时大幅下降** |
| 不支持并发上传的优化 | 依赖 RocksDB 的不可变 SST 特性 |

> [!note] 代价
> 增量 Checkpoint 保留了历史 SST 引用，因此**旧的 Checkpoint 之间会共享文件**；删旧 CK 时要小心（Flink 会做引用管理）。
> 另外，**Savepoint 始终是全量的**（为了可移植性）。

---

## 五、恢复过程

### 5.1 恢复做了什么

| 步骤 | 动作 |
|---|---|
| 1 | 作业失败 → JobMaster 按**重启策略**决定是否重启 |
| 2 | 选择**最近一次 completed Checkpoint** |
| 3 | 各 Task 从 Checkpoint Storage **下载状态** |
| 4 | Source 从 Checkpoint 中记录的**位点**重新开始消费（**会重放**） |
| 5 | 从该位点之后的数据被重新处理 → **产生重复** |

> [!important] 为什么"恢复必然重放"
> Checkpoint 是周期性的，两次 CK 之间的数据没有被打快照。恢复回到**上一次 CK 的位置**，这段区间的数据必然被**再处理一次**。
> 所以 Flink 内部是 **at-least-once 的打底**，要达成 exactly-once 必须靠 **Sink 事务或幂等**去消除重复（见 [[4-容错与ExactlyOnce]] 与 [[11-端到端一致性]]）。

### 5.2 重启策略

```yaml
# 固定延迟：每次失败后等 10s 重启，最多 3 次
restart-strategy: fixed-delay
restart-strategy.fixed-delay.attempts: 3
restart-strategy.fixed-delay.delay: 10s

# 失败率：5 分钟内失败不超过 3 次
restart-strategy: failure-rate
restart-strategy.failure-rate.max-failures-per-interval: 3
restart-strategy.failure-rate.failure-rate-interval: 5min
restart-strategy.failure-rate.delay: 10s

# 指数延迟（1.19+）
restart-strategy: exponential-delay
```

| 策略 | 适用 |
|---|---|
| `fixed-delay` | 通用，故障可自愈（多数生产选择） |
| `failure-rate` | 抑制**反复失败**的作业（防无限重启风暴） |
| `exponential-delay` | 故障恢复耗时较长的场景（避免重启过于密集） |
| `none` | 重要作业，**希望故障时人工介入** |

> [!tip] 生产建议
> 用 `fixed-delay` + **`tolerable-failed-checkpoints`** 组合。同时配上**告警**：作业重启次数、Checkpoint 连续失败次数——否则作业会"默默重启一整天"而无人知晓（见 [[9-部署与运维]]）。

---

## 六、Checkpoint vs Savepoint

| 维度 | Checkpoint | Savepoint |
|---|---|---|
| **触发者** | Flink **自动**（周期性） | **用户手动**（CLI/REST） |
| **目的** | 故障恢复 | **升级、迁移、扩缩容、备份** |
| **格式** | 内部格式，可含增量（依赖后端） | **标准格式、始终全量**、更稳定 |
| **生命周期** | 按 `externalized` 配置保留/清理 | **不会被自动清理**（需手动删） |
| **性能开销** | 设计为轻量、周期执行 | 较重（全量 + 可能暂停作业） |
| **可否带状态改并行度** | 可以（但同样受 `maxParallelism` 限制） | 可以，是标准用法 |
| **删旧的** | Flink 自动管理 | 需人工管理（否则磁盘爆） |

### 6.1 Savepoint 的典型用法

```bash
# 1) 优雅停止并生成 Savepoint（推荐，先"停干净"再变更）
flink stop --savepointPath hdfs:///flink/savepoints <jobId>

# 2) 或对运行中的作业手动触发 Savepoint（不停作业）
flink savepoint <jobId> hdfs:///flink/savepoints

# 3) 从 Savepoint 恢复（可改并行度）
flink run -s hdfs:///flink/savepoints/savepoint-xxxx -p 8 -d my-job.jar

# 4) 允许跳过无法映射的状态（危险！见下）
flink run -s <savepoint> --allowNonRestoredState my-job.jar

# 5) 取消作业但保留 Savepoint
flink cancel -s hdfs:///flink/savepoints <jobId>
```

> [!danger] `--allowNonRestoredState` 是"逃生舱门"，不是常规操作
> 它允许**丢弃无法映射到新算子的状态**，常被用来"强行让作业跑起来"。
> 后果：**静默丢失状态**，可能表现为结果错误（例如去重集合丢了、join 缓存丢了）而不报错。只在明确知道"这状态不要了"时使用。

### 6.2 为什么改并行度要用 Savepoint

- Savepoint 是全量、格式稳定的快照，恢复时 Flink 按 **key group** 把状态重新分配给新的 subtask 集合。
- Checkpoint 理论上也支持改并行度恢复，但生产实践**统一走 Savepoint**（语义清晰、可审计、可回滚）。

---

## 七、Checkpoint 调优速查

| 症状 | 可能原因 | 处理方向 |
|---|---|---|
| CK 耗时长 | 状态太大 / 全量上传 / 网络带宽不足 | 用 **RocksDB + 增量 CK**；加大间隔；检查 DFS 带宽 |
| CK 频繁超时 | **持续背压** + Barrier 对齐等待 | 开**非对齐 CK**；先解决背压（见 [[6-背压与性能调优]]） |
| CK 体积巨大 | 状态膨胀、无 TTL、全量 | 配**状态 TTL**（见 [[3-状态管理]]）；确认增量 CK 已开 |
| CK 之间互相干扰 | `max-concurrent-checkpoints > 1` | 设为 1，并用 `min-pause` 隔开 |
| 恢复特别慢 | 从 DFS 下载全量状态 | 增量 CK；本地恢复（`state.backend.local-recovery`）；就近存储 |
| CK 一直失败但作业在跑 | 只看作业状态不知道 | **必须监控 `numberOfFailedCheckpoints` 与 recent CK 成功率** |
| 作业取消后 CK 被删 | 未配置 externalized retention | 设 `RETAIN_ON_CANCELLATION` |

> [!important] 一个必须记住的运维红线
> **作业在跑 ≠ 作业健康**。如果所有 Checkpoint 都在失败，作业一旦重启就会**从很早的位置重放**（甚至无 CK 可用而无法恢复）。
> 所以 **Checkpoint 成功率必须进监控告警**。

---

## 八、动手验证

```bash
# 1) 命令行查看 Checkpoint 配置与状态
flink list                     # 找到 jobId
curl localhost:8081/jobs/<jobId>/checkpoints | jq
#   关注: counts.completed / counts.failed / latest.completed

# 2) 手动触发一次 Checkpoint
curl -X POST localhost:8081/jobs/<jobId>/checkpoints

# 3) 查看某次 Checkpoint 的详细内容（各算子状态大小、对齐耗时）
curl localhost:8081/jobs/<jobId>/checkpoints/<ckId> | jq
#   关注: checkpointAlignmentTime, syncDuration, asyncDuration, stateSize

# 4) 触发 Savepoint 并查看目录结构
flink savepoint <jobId> /tmp/flink-sp
ls -R /tmp/flink-sp
#   可见 _metadata（算子 uid 与状态映射）与各算子的状态文件

# 5) 故意杀掉 TaskManager，观察恢复行为
#   恢复后对比输出：应能观察到"重复处理"（验证 at-least-once 打底）
```

**验证清单**：
- [ ] 观察到 Checkpoint 的**对齐耗时**（若占比很高，说明有背压 → 考虑非对齐）
- [ ] 对比开启增量 Checkpoint 前后的 `stateSize` 与 `asyncDuration`
- [ ] 确认作业取消后 Checkpoint 是否按配置保留
- [ ] 杀掉 TM 后确认作业从最近 CK 恢复，且**没有数据丢失**（可能有重复）

---

## 九、本篇必答

> [!question] 面试官可能这样问
> **Q：Checkpoint 和 Savepoint 有什么区别？**
> A：**触发方式**（自动 vs 手动）、**目的**（故障恢复 vs 升级迁移扩缩容）、**格式**（内部可增量 vs 标准全量稳定）、**生命周期**（可自动清理 vs 需手动管理）。生产上**改并行度、升级版本、跨集群迁移统一走 Savepoint**。
>
> **Q：Checkpoint 存了什么？存在哪？**
> A：存**算子状态 + Source 位点 + 元信息**。**状态后端**决定运行时状态放哪（堆内存的 HashMap 或本地磁盘的 RocksDB），**Checkpoint Storage** 决定快照写哪（JobManager 内存或 HDFS/S3 等）。自 1.13 起这两者**解耦**，生产标准配置是 **RocksDB + 分布式存储 + 增量 Checkpoint**。
>
> **Q：Checkpoint 一直失败会怎样？**
> A：作业会继续运行，但**没有可用的恢复点**。一旦故障，只能从很早的 Checkpoint 恢复（重放大量数据），甚至因为连续失败超过 `tolerable-failed-checkpoints` 而**判定作业失败**。所以 Checkpoint 成功率必须纳入监控。
>
> **Q：大状态作业怎么让 Checkpoint 更快？**
> A：① 换 **RocksDB 状态后端 + 开启增量 Checkpoint**；② 从源头治理状态（**状态 TTL**、减少 key 基数、用增量聚合替代全量缓存）；③ 若瓶颈是反压导致的对齐等待，开**非对齐 Checkpoint**；④ 适当加大间隔、设置 `min-pause` 避免 CK 互相干扰；⑤ 把 Checkpoint 存到带宽和就近性更好的存储。
>
> **Q：Kafka Source 提交了 offset，是不是就能恢复了？**
> A：**不是**。Flink 恢复只依赖 **Checkpoint 中记录的位点**；提交给 Kafka 的 offset 只用于外部监控。这是高频陷阱。

---
> 上一篇 → [[3-状态管理]] ｜ 下一篇 → [[6-背压与性能调优]]
