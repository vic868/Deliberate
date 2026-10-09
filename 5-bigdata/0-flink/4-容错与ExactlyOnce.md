---
title: Flink 容错机制与 Exactly-Once
tags: [Flink, Exactly-Once, Checkpoint, 容错]
status: 进行中
created: 2026-10-09
---

# 🛡️ 四、容错机制与 Exactly-Once

> 本篇回答六个问题：at-most-once / at-least-once / exactly-once 在流处理里到底由谁决定，为什么说它是"端到端"概念？Chandy-Lamport 分布式快照是怎么落地的，barrier 对齐（alignment）为什么是 exactly-once 的必需品，而它又为什么会引发反压？Unaligned Checkpoint 用"把 in-flight 数据一起快照"解决了什么问题，代价是什么？两阶段提交（2PC）的 `preCommit` 和 `commit` 分别在什么时刻发生，为什么 Kafka Sink 的事务超时配置必须和 checkpoint 间隔挂钩？幂等写入和事务写入怎么选，"幂等 + at-least-once"为什么是工程上最常见的折中？checkpoint 超时、恢复后重复数据激增、2PC 事务超时这三类故障怎么定位？
> 前置阅读：[[0-Flink总览]]、[[1-架构与运行时]]、[[3-状态管理]]。相关：[[5-Checkpoint与Savepoint]]（checkpoint/savepoint 的完整参数与运维细节）、[[6-背压与性能调优]]（对齐与反压的相互作用）、[[8-FlinkSQL与TableAPI]]（SQL 层的 exactly-once 配置）、[[9-部署与运维]]、[[10-面试高频题]]。

---

## 一、投递语义：先把"保证什么"说清楚

### 1.1 三种语义的定义

投递语义讨论的从来不是"数据会不会丢"这一件事，而是**在故障发生时，一条数据被处理的次数**。

| 语义 | 定义 | 在 Flink 中如何实现 | 典型代价 |
| --- | --- | --- | --- |
| at-most-once（至多一次） | 数据可能丢，但绝不会重复 | checkpoint 用 `AT_LEAST_ONCE` 模式（或干脆不开启）；故障后不重放或重放时跳过 | 丢数据，但吞吐最高 |
| at-least-once（至少一次） | 数据不丢，但可能重复 | Checkpoint + 从最近完成的 checkpoint 恢复并**重放** source 位点之后的数据 | 重复处理，需要下游幂等 |
| exactly-once（精确一次） | 不丢且不重，**对状态的影响恰好一次** | Checkpoint（EXACTLY_ONCE 模式）+ 可重放 source + 事务/幂等 sink | 延迟上升、吞吐下降、依赖 sink 能力 |

> [!important] exactly-once 说的是"状态"而不是"数据"
> 一个必须澄清的点：Flink 的 exactly-once 保证的是 **"每条数据对算子状态的更新恰好生效一次"**——即使底层数据被重放过多次，最终状态和"只处理一次"是一样的。
> 这就是所谓的 **"effectively once"（效果上一次）**。数据本身当然可能被物理重放，但因为 sink 的事务或幂等，**外部可见的结果**只有一份。

### 1.2 语义取决于三方：Source + 内部状态 + Sink

这是理解全部容错机制的主线。

```text
   ┌──────────┐      ┌──────────────────────┐      ┌──────────┐
   │  Source  │ ───► │  Flink 内部状态计算   │ ───► │   Sink   │
   │ 可重放？  │      │  能一致性快照？       │      │ 事务/幂等？│
   └──────────┘      └──────────────────────┘      └──────────┘
        │                       │                        │
   决定"能不能              决定"恢复后             决定"重复会不会
   从位点重放"              从哪继续"               泄漏到外部"
```

| 环节 | 需要的能力 | 缺失的后果 |
| --- | --- | --- |
| **Source** | 可重放（能按位点重新消费）、位点能进 checkpoint | 位点不可靠 → 恢复后丢数据（at-most-once） |
| **内部状态** | 能被一致性快照并在恢复后精确还原 | 状态不一致 → 结果错误，且无法从 checkpoint 继续 |
| **Sink** | 事务提交（2PC）或幂等写入 | 恢复重放时重复写入外部系统 → 只能 at-least-once |

> [!warning] 三者只要有一个不满足，端到端 exactly-once 就退化
> - Source 不可重放（比如一个不记录位点的 HTTP 轮询源）→ 恢复后必然丢数据，连 at-least-once 都保证不了。
> - Sink 不支持事务也不幂等（比如一个普通日志文件、一个 `redis.incr` 计数器）→ 恢复后会重复写入，语义退化为 at-least-once。
> - **最常见的现实**：Source 和内部状态都没问题，卡在 Sink 上。这是第七章要重点解决的问题。

### 1.3 为什么必须用"端到端"视角

单看 Flink 内部，checkpoint 确实能保证状态的一致性。但这只解决了"Flink 自己算得对"，没解决"外部系统看到什么"。

```text
   场景：Checkpoint 每 1 分钟一次

   t=0      处理数据 A,B,C …… 状态 = f(A,B,C)
   t=1:00   checkpoint #1 完成 ✅
   t=1:30   处理数据 D,E …… 状态 = f(A,B,C,D,E)
            ↓ 此时把 D,E 的结果写进了下游（非事务 sink）
   t=1:40   TaskManager 挂了 💥
            ↓
   恢复：从 checkpoint #1 恢复 → 状态回到 f(A,B,C)
         source 从 t=1:00 的位点重放 → 重新处理 D,E
            ↓
         D,E 被写了第二遍 ❌  → at-least-once
```

要消灭这第二遍，只有两条路：

1. **让"写下游"也变成可回滚/可延迟提交的操作** → 事务（2PC）；
2. **让"写下游"重复执行的结果和只执行一次一样** → 幂等。

---

## 二、一致性检查点的核心思想

### 2.1 分布式快照与 Chandy-Lamport

Flink 的容错机制源于 **Chandy-Lamport 分布式快照算法**（1985）。原始算法解决的问题是：**如何在不停止整个系统的情况下，给一个分布式系统拍一张"全局一致"的快照？**

原始算法的关键设定：

| 设定 | 含义 |
| --- | --- |
| 进程与通道 | 一组进程，进程之间通过有向通道通信 |
| **通道 FIFO** | 通道是先进先出的（消息不会乱序）——**这是算法成立的关键前提** |
| 无故障 | 拍快照期间假设不发生故障 |
| 快照的定义 | 一组"进程本地状态 + 通道中在途消息"的集合，且这个集合对应某个"全局一致的切面" |

算法的做法：

```text
1. 任意一个进程（发起者）先保存自己的本地状态，然后在每条出向通道上发送一个
   "marker"（标记）消息。
2. 进程收到某条入向通道上的第一个 marker 时：
     a. 如果还没保存过自己的状态 → 保存本地状态，并向所有出向通道发送 marker；
     b. 记录该入向通道此刻的状态为"空"（在这个 marker 之后到达的消息，
        属于下一个快照，需要被记录为通道状态）。
3. 进程已经保存过状态之后，继续从其他入向通道接收数据：
     - 在收到该通道的 marker 之前，收到的消息记录为该通道的"通道状态"。
     - 收到该通道的 marker 后，该通道的状态收集完毕。
4. 所有通道的状态都收集完 → 快照完成。
```

**Flink 的映射关系：**

| Chandy-Lamport | Flink |
| --- | --- |
| 进程（Process） | 算子（Operator）实例 / subtask |
| 通道（Channel） | 网络连接（上游 subtask → 下游 subtask 的 output buffer） |
| marker 消息 | **CheckpointBarrier** |
| 进程本地状态 | 算子状态（keyed / operator / broadcast state + timer） |
| 通道状态 | **in-flight 数据**（只有 unaligned checkpoint 才需要显式快照） |
| 发起者（Initiator） | **JobManager 的 CheckpointCoordinator** |
| 快照 ID | checkpoint ID（单调递增） |

> [!important] 一个关键差异：Flink 全量快照，不用"通道状态"
> 原始的 Chandy-Lamport 算法需要记录"通道中在途的消息"。**Flink 的对齐式 checkpoint（aligned checkpoint）通过 barrier 同步机制把这个需求消掉了**：barrier 沿着数据流走，一个算子只有在确认"该通道上 barrier 之前的数据都已处理完"之后才拍快照，所以不存在"属于本快照但还没处理完的在途数据"。
> 这就是为什么对齐式 checkpoint 不需要快照网络缓冲区——而 **unaligned checkpoint 恰恰放弃了这一点**，于是必须把 in-flight 数据显式地作为"通道状态"快照下来（见第四章）。

### 2.2 Barrier 的注入与传播

**注入**：`CheckpointCoordinator`（运行在 JobManager 上）按 `execution.checkpointing.interval` 周期性地触发 checkpoint，向所有 **Source 算子**注入一个带 checkpoint ID 的 barrier。

**传播**：barrier 像一条"特殊的数据记录"在数据流里向下游流动，**与普通记录共享同一条通道、保持相对顺序**（这正是依赖 FIFO 的地方）。

```text
JobManager / CheckpointCoordinator
        │  注入 barrier(n)
        ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Source  │──►│  map    │──►│  sink   │
   └─────────┘   └─────────┘   └─────────┘
        │             │              │
   收到 barrier  收到 barrier   收到 barrier
   → 快照 source  → 快照算子     → 快照 sink
     状态(位点)     状态           状态(2PC 事务)
        │             │              │
        └─────────────┴──────────────┘
                      │ 逐级向上 ack
                      ▼
              CheckpointCoordinator
              （收齐所有 subtask 的 ack）
                      │
                      ▼
              标记 checkpoint 为 completed
              （触发 notifyCheckpointComplete）
```

普通数据流经过 barrier 时是这样的：

```text
上游 ──► [r1][r2][r3] ... [BARRIER n] [r4][r5] ... [BARRIER n+1] [r6] ──► 下游

        └── 属于快照 n ──┘          └── 属于快照 n+1 ──┘
```

**barrier 不打断数据流**：算子收到 barrier 之后，普通数据依然继续处理，只是这些数据属于下一个 checkpoint 的区间。这也是 Flink 的快照能做到"不停止流"的原因。

### 2.3 快照里到底包含什么

| 内容 | 说明 | 归属 |
| --- | --- | --- |
| **Source 的读取位点** | Kafka offset、文件读取位置、CDC 的 binlog 位点 | Source 的 Operator State |
| **算子状态** | Keyed State（Value/List/Map/Reducing/Aggregating）、Operator State、Broadcast State | 算子 |
| **定时器（Timer）** | `registerEventTimeTimer` / `registerProcessingTimeTimer` 注册的 timer | 算子的内部状态 |
| **窗口状态** | 各窗口的累加器 / 缓存元素、窗口的 trigger 状态 | WindowOperator 的内部状态 |
| **Sink 的待提交事务** | 2PC sink 中 preCommit 但还没 commit 的事务句柄 | Sink 的 Operator State |
| **in-flight 数据（仅 unaligned）** | 网络缓冲区里还没被下游处理的数据 | 通道状态（Channel State） |
| **不在快照里的** | 对齐式 checkpoint 下网络缓冲区里的数据、JobManager 的运行时元数据 | —— |

> [!note] 快照是"异步"的
> Flink 的 checkpoint 采用**异步快照**：算子在持有 **checkpoint lock** 的短时间内把状态"复制/引用"出来（对 RocksDB 是生成 SST 快照引用，不拷贝数据），随后在后台线程把状态上传到 checkpoint 存储。
> 这意味着：**快照期间数据处理基本不中断**（阻塞时间通常远小于上传时间）。这也是 RocksDB 后端在大状态下依然可用的原因——它靠"快照文件引用 + 增量上传"避免全量拷贝。

### 2.4 为什么这样能保证一致性

**核心不变量**：barrier n 把数据流切成了"属于快照 n"和"属于快照 n+1"两段。因为在每条通道上 barrier 之前的数据一定会被先处理完，所以当算子处理完 barrier n 时，它的状态**恰好等于"处理完所有属于快照 n 的数据后的状态"**。

这个"切面"性质保证了：

| 保证 | 原因 |
| --- | --- |
| 快照内部一致 | 每个算子的状态都对应同一个 barrier 切面 |
| 恢复后不重不漏 | 从快照恢复 = 回到那个切面，从该切面对应的 source 位点继续 |
| 无"孤儿数据" | 不存在"某个上游进程已计入快照、但下游还没处理"的数据 |

---

## 三、Barrier 对齐（Barrier Alignment）

对齐是 exactly-once 最核心、也最容易引起性能问题的机制。

### 3.1 对齐的完整流程

**前提**：只有**多输入的算子**才需要对齐（`union`、`connect`、双流 join、`CoProcessFunction` 等）。单输入算子直接透传 barrier，没有对齐问题。

假设某算子有两个输入 A 和 B：

```text
时刻 1：A 的 barrier 先到
   A: ──────────────[BARRIER n]──► ┌─────────────┐
                                   │   算子      │
   B: ────────────────────────►    └─────────────┘
                                   
   → 算子收到 A 的 barrier，立刻【阻塞通道 A】
     （A 后续的数据被缓存，不处理——因为它们属于快照 n+1）
   → 继续处理通道 B 的数据（它们属于快照 n，必须计入状态）

时刻 2：继续从 B 收数据，同时 A 的数据在缓冲区堆积
   A: ──────────────[BARRIER n]──► │ 阻塞，缓存后续数据 │
                                   │ 继续处理 B 的数据   │
   B: ──────────────────►          └─────────────┘

时刻 3：B 的 barrier 到达
   A: ──────────────[BARRIER n]──► ┌─────────────┐
                                   │ 两个 barrier │
   B: ──────────────[BARRIER n]──► │ 都到齐了     │
                                   └─────────────┘
   → 快照本地状态
   → 向下游广播 barrier n
   → 解除阻塞，继续处理 A 缓存的、以及 B 后续的数据
```

**关键点复述（防止记反）：**

| 通道 | 处理方式 |
| --- | --- |
| **已经送出 barrier 的通道** | **阻塞**，其后续数据被**缓存**（不能处理，否则会混入下一个快照的数据） |
| **还没送出 barrier 的通道** | **继续处理**（它们的数据属于当前快照，必须计入状态） |
| 所有 barrier 到齐后 | 快照本地状态 → 下游广播 barrier → 解除阻塞 |

### 3.2 为什么 exactly-once 需要对齐

因为**状态的快照必须对应一个明确的"数据切面"**。

如果不对齐——比如 A 的 barrier 到了就直接处理 A 后续的数据（属于快照 n+1）——那么快照出来的状态里就**混入了快照 n+1 的数据**。

```text
不对齐时的错误：
  A 的 barrier n 到达
  → 继续处理 A 的 r4（属于 n+1）→ 状态被 r4 更新
  B 的 barrier n 还没到，B 的 r5（属于 n）还没处理
  → 快照状态 = f(n 的数据, 部分 n+1 的数据)   ❌ 不是一个合法切面

恢复后：
  source 从快照 n 的位点重放 → r4 被再次处理
  但 r4 的效果已经在快照里了 → r4 被处理了两次 ❌ → at-least-once
```

> [!important] 对齐是 exactly-once 的**代价**，不是可选优化
> 只要选择了 `execution.checkpointing.mode: EXACTLY_ONCE`，多输入算子就会做 barrier 对齐。这不是可配置的性能开关，而是语义要求。

### 3.3 at-least-once 为什么不对齐、为什么更快

把 checkpoint 模式设为 `AT_LEAST_ONCE` 时：

```yaml
execution.checkpointing.mode: AT_LEAST_ONCE
```

算子**收到第一个 barrier 就直接快照本地状态**，不再等待其他输入的 barrier，也不阻塞任何通道。

| 维度 | EXACTLY_ONCE（对齐） | AT_LEAST_ONCE（不对齐） |
| --- | --- | --- |
| 是否阻塞通道 | 是 | 否 |
| 是否需要缓存数据 | 是（内存压力） | 否 |
| 快照耗时 | 取决于最慢输入（长尾效应） | 取决于本地速度，很快 |
| 是否受反压影响 | **强受影响**：反压时 bar位迟迟到不了 | 几乎不受影响 |
| 恢复后语义 | 不重不丢（配合事务/幂等 sink） | **可能重复**（快照混入了下一个 epoch 的数据） |
| 吞吐 | 较低 | 较高 |
| 适用 | 计费、账务、对账类 | 可容忍重复的监控、统计、日志类 |

**为什么 at-least-once 会重复**：因为它允许快照混入下一个 epoch 的数据，恢复时这些数据会被再次处理，也就是"快照状态里已经包含了某些数据的处理结果，但 source 位点还没推进到那里，所以会重放"。**这正好是 at-least-once 的定义**（不丢但可能重）。

### 3.4 对齐导致的反压（重点）

对齐最致命的副作用是：**它把最慢输入的延迟放大了**。

```text
算子有两个输入 A（快）和 B（慢）：
  A: ──►▮▮▮▮▮▮▮▮▮▮  （barrier 早就到了，数据在缓冲区堆着）
  B: ──────────────  （慢，barrier 还没来）

后果：
  ① A 的数据在内存缓冲区堆积 → 内存压力 → 可能触发网络栈反压
  ② 算子停止处理 A 的数据 → A 的上游被反压 → 一路传回 A 的 source
  ③ 整个 checkpoint 的耗时 = 最慢输入的 barrier 到达时间
  ④ 如果 B 被反压卡住（比如 B 的下游很慢），B 的 barrier 也动不了
     → barrier 永远不齐 → checkpoint 超时失败
```

这形成一个恶性循环：

```text
反压 ──► barrier 传播变慢 ──► 对齐等待时间变长 ──► checkpoint 耗时增加
  ▲                                                        │
  └────────── 对齐期间缓冲区堆积、处理停滞 ◄────────────────┘
```

| 对齐引发的问题 | 表现 |
| --- | --- |
| checkpoint 耗时随反压增长 | 反压越重，checkpoint 越慢，最终超时失败 |
| checkpoint 超时率上升 | `execution.checkpointing.timeout` 频繁触发 |
| 内存压力 | 对齐缓冲区堆积，可能导致 TM OOM |
| 长尾效应 | 个别慢 subtask 拖慢整个 checkpoint |
| 吞吐抖动 | 对齐期间部分通道被阻塞，处理效率下降 |

> [!danger] "反压 → checkpoint 超时 → 重启 → 又反压"是最常见的死循环
> 一个作业先因为数据倾斜出现反压，然后 checkpoint 开始超时，超时后触发重启，重启后要重放积压数据，反压更严重，checkpoint 更超时……**最后表现为作业不停地重启，看起来像"checkpoint 有问题"，根因其实是反压。**
> 排查顺序应该是：**先看反压（哪个算子、哪个 subtask），再看 checkpoint**。反压的定位方法见 [[6-背压与性能调优]]。

> [!tip] 缓解对齐开销的几个方向
> | 手段 | 说明 |
> | --- | --- |
> | 解决反压根因 | 最有效的办法。倾斜加盐、扩容、优化算子 |
> | **Unaligned Checkpoint** | 让 barrier 越过缓冲区，彻底消除对齐等待（见第四章） |
> | 增大 `execution.checkpointing.timeout` | 治标不治本，但能减少误报重启 |
> | 增大 `execution.checkpointing.min-pause` | 给作业喘息时间，避免 checkpoint 连轴转 |
> | `max-concurrent-checkpoints: 1` | 避免多个 checkpoint 同时抢资源 |
> | 减少状态大小 | 状态小 → 快照快 → 对齐窗口短（增量 checkpoint 见 [[3-状态管理]]） |
> | 降低 checkpoint 频率 | 间隔拉长，但故障时重放的数据更多 |

---

## 四、Unaligned Checkpoint（1.11+）

### 4.1 动机：反压场景下对齐会失败

对齐的问题本质是：**barrier 必须排队等着前面的数据被处理完**。而在反压场景下，前面堆积了大量还没处理的数据，barrier 要等很久。

Unaligned Checkpoint 的想法很直接：**既然等不了，那就让 barrier 插队越过缓冲区，把那些 in-flight 的数据一起快照下来。**

### 4.2 原理

```text
对齐式（Aligned）：
  A: ──d1─d2─d3─d4─d5─[BARRIER]──►   等 d1~d5 全部处理完才能快照
  B: ──d1─d2─[BARRIER]──────────►
                    ↑
              必须等 A 的 barrier，A 的 d1~d5 都要处理完

Unaligned：
  A: ──d1─d2─d3─d4─d5─[BARRIER]──►   barrier 立刻越过 d1~d5
  B: ──d1─d2─[BARRIER]──────────►
                    ↑
        barrier 不等待：直接把 d1~d5 和 B 的 in-flight 数据
        作为"通道状态"写进 checkpoint，然后立刻快照本地状态
```

**关键变化**：快照的内容多了一样东西——**Channel State（通道状态）**，即"barrier 之后、但还没被下游处理的数据"。

恢复时：

```text
从 checkpoint 恢复
  → 先还原算子状态
  → 再把 Channel State 里的 in-flight 数据重新放回输入缓冲区
  → 这些数据会被重新处理（但因为快照和它们是一起拍的，所以不重不漏）
```

### 4.3 代价

| 代价 | 说明 |
| --- | --- |
| **checkpoint 变大** | 要额外保存所有 in-flight 数据。反压越重、缓冲区堆积越多，checkpoint 越大（可能显著变大） |
| **恢复时要重放 in-flight** | 恢复后必须先处理这些数据，恢复时间变长 |
| **上传/下载带宽增加** | 更大的快照意味着更多的 DFS 写入和读取 |
| **对某些算子不友好** | 部分不支持的算子会导致 checkpoint 无法 unaligned；广播/迭代等特殊结构有额外限制 |
| **并发的 unaligned checkpoint 受限** | 一般只能同时进行一个 unaligned checkpoint |
| **不容易调试** | 从日志和指标上看，"checkpoint 变慢了"的原因更难归因 |

### 4.4 配置与适用条件

```yaml
execution.checkpointing.unaligned: true
```

| 项 | 说明 |
| --- | --- |
| 配置键 | `execution.checkpointing.unaligned`（布尔） |
| 生效条件 | 只有**存在反压/对齐等待**时才真正体现价值；无反压时它和对齐式差别不大 |
| 与 mode 的关系 | 与 `execution.checkpointing.mode: EXACTLY_ONCE` 配合使用，语义仍是 exactly-once |
| 版本演进 | 早期版本还提供过 `execution.checkpointing.aligned-checkpoint-timeout`（先尝试对齐，超时后降级为 unaligned）；后续版本把这种"自动降级"逻辑做了调整，具体行为请以所用版本文档为准 |
| 恢复兼容 | 从 aligned checkpoint 恢复到 unaligned 配置通常可行；反向（unaligned → aligned）需要注意版本支持情况 |

**什么时候该开 unaligned？**

| 场景 | 建议 |
| --- | --- |
| checkpoint 因对齐超时频繁失败，且短期无法消除反压 | ✅ 开。这是最主要的使用场景 |
| 反压严重且 checkpoint 间隔较紧 | ✅ 开 |
| 状态非常大、checkpoint 本身就很慢（瓶颈在状态上传而不是对齐） | ❌ 没用。unaligned 解决的是"对齐等待"，不解决"状态太大" |
| 作业无显著反压，checkpoint 正常 | ❌ 没必要，反而增加快照体积 |
| 网络/DFS 带宽紧张 | ⚠️ 谨慎。unaligned 会让快照变大，可能加剧带宽压力 |

> [!warning] unaligned 是"止血"而不是"治病"
> 它让 checkpoint 在反压下能完成，但**反压本身还在，端到端延迟还在**。它的正确用法是"**在生产环境救急、给排查和优化争取时间**"，而不是当成长期方案掩盖反压。
> 一个健康的作业应该是：反压被消除 → aligned checkpoint 自然快速完成 → 不需要 unaligned。**长期开着 unaligned 且反压很高，说明技术债在累积。**

---

## 五、Checkpoint 的触发与完成流程（概述）

本节只做流程概述与故障定位，参数与运维细节见 [[5-Checkpoint与Savepoint]]。

### 5.1 参与者

| 角色 | 位置 | 职责 |
| --- | --- | --- |
| `CheckpointCoordinator` | JobManager | 周期性触发 checkpoint；注入 barrier；收集 ack；决定完成/失败 |
| `CheckpointBarrierHandler` | 每个 Task | 处理 barrier 的对齐与转发 |
| Source 算子 | TaskManager | 收到触发后立刻快照位点，并把 barrier 注入数据流 |
| 各算子 | TaskManager | 对齐、快照状态、上报 ack、向下游广播 barrier |
| Sink 算子 | TaskManager | 快照 sink 状态（如 2PC 的待提交事务） |
| CheckpointStorage | 分布式文件系统 | 存放状态数据与元数据 |

### 5.2 全流程

```text
① JM 的 CheckpointCoordinator 按 interval 触发 checkpoint(n)
        │
② 向所有 Source subtask 发送"注入 barrier n"的触发消息
        │
③ Source：
     - 在 checkpoint lock 保护下快照自身状态（位点）
     - 把 barrier n 注入数据流
        │
④ barrier 沿数据流传播，各算子：
     - 多输入算子做对齐
     - 快照本地状态（异步上传到 CheckpointStorage）
     - 向下游广播 barrier n
     - 向上游（JM）上报 ack
        │
⑤ JM 的 CheckpointCoordinator 收齐所有 subtask 的 ack
        │
⑥ 标记 checkpoint n 为 COMPLETED
        │
⑦ 回调每个算子的 notifyCheckpointComplete(n)
     - 2PC sink 在这里 commit 事务
     - Kafka source 在这里把 offset 提交到 Kafka（如果开启）
        │
⑧ 清理旧的 checkpoint（按 retention 策略）
```

> [!important] 第 ⑥⑦ 步是整个 exactly-once 的"提交点"
> **checkpoint 完成的通知（`notifyCheckpointComplete`）才是真正的提交时刻。** 两阶段提交的"第二阶段"（commit）就发生在这里。这解释了 2PC sink 为什么必须等 checkpoint 完成才能 commit——如果 checkpoint 还没完成就 commit，而作业在 commit 后、checkpoint 完成前挂了，恢复后这份数据会被重复写入。

### 5.3 失败与超时

| 情况 | 行为 |
| --- | --- |
| 某个 subtask 快照失败 | 整个 checkpoint 失败；按 `tolerable-failed-checkpoints` 决定是否容忍 |
| 超过 `execution.checkpointing.timeout` | checkpoint 被丢弃（declined/expired），作业**默认不会重启**（除非触发了别的故障） |
| checkpoint 失败次数超过 `tolerable-failed-checkpoints` | **触发作业重启** |
| 收到更新 checkpoint 的 barrier（后发的先到） | 旧的 checkpoint 被 subsumed/丢弃 |
| 作业重启 | 从**最近一个 COMPLETED 的 checkpoint** 恢复 |

### 5.4 关键配置一览

```yaml
# ---- 触发与超时 ----
execution.checkpointing.interval: 60000              # 触发间隔
execution.checkpointing.timeout: 600000              # 单次 checkpoint 超时（含对齐等待）
execution.checkpointing.min-pause: 30000             # 两次 checkpoint 之间的最小间隔
execution.checkpointing.max-concurrent-checkpoints: 1 # 最大并发 checkpoint 数

# ---- 语义与对齐 ----
execution.checkpointing.mode: EXACTLY_ONCE            # EXACTLY_ONCE / AT_LEAST_ONCE
execution.checkpointing.unaligned: false             # 是否启用非对齐 checkpoint

# ---- 容错与保留 ----
execution.checkpointing.tolerable-failed-checkpoints: 3   # 容忍几次失败后重启
execution.checkpointing.externalized-checkpoint-retention: RETAIN_ON_CANCELLATION

# ---- 存储 ----
state.backend: rocksdb
state.backend.incremental: true
state.checkpoint-storage: filesystem
state.checkpoints.dir: hdfs:///flink/checkpoints
state.savepoints.dir: hdfs:///flink/savepoints
```

| 配置 | 调优方向 |
| --- | --- |
| `interval` | 越小 → 故障重放的数据越少、但开销越大。要在"恢复成本"和"运行开销"之间取平衡 |
| `timeout` | 应设为"正常 checkpoint 耗时的 3-5 倍"。太小会误报；太大会让问题发现得更晚 |
| `min-pause` | 给状态后端喘息时间，避免 checkpoint 连轴转影响正常处理 |
| `max-concurrent-checkpoints` | 生产建议 1。并发 checkpoint 会互相抢 IO/CPU，反而更慢 |
| `tolerable-failed-checkpoints` | 设 0 表示一次失败就重启（抖动大）；设几个可以容忍偶发失败 |

> [!tip] checkpoint 间隔怎么定
> 从"可接受的重放数据量"倒推：
> ```text
> 故障恢复后要重放的数据 ≈ 峰值吞吐 × checkpoint interval
> ```
> 如果峰值 10 万条/秒、希望最多重放 100 万条，那 interval 就应该是 10 秒左右。
> 但 interval 也不能太小：checkpoint 本身有开销，间隔太小会让作业大部分时间在做快照。**经验做法是从 1 分钟起步，根据实际 checkpoint 耗时和恢复时间调整。**

---

## 六、重启策略（Restart Strategy）

### 6.1 四种策略

| 策略 | 行为 | 适用 |
| --- | --- | --- |
| `fixed-delay` | 固定延迟后重启，最多尝试 `attempts` 次 | 大多数流作业。故障通常可恢复（如上游抖动） |
| `failure-rate` | 在 `failure-rate-interval` 内失败超过 `max-failures-per-interval` 次就**放弃** | 需要"限流式重试"的场景，避免疯狂重启 |
| `exponential-delay` | 重启间隔指数退避（带抖动），避免重启风暴 | 依赖外部系统长时间不可用（数据库宕机、上游 Kafka 挂） |
| `none` | 不重启，失败即终止 | 定时批作业、需要人工介入的关键任务、测试 |

### 6.2 配置方式

```java
// 代码方式
env.setRestartStrategy(RestartStrategies.fixedDelayRestart(
        3,                                    // 最大尝试次数
        Time.seconds(10)));                    // 每次重启的延迟

env.setRestartStrategy(RestartStrategies.failureRateRestart(
        3,                                    // 一个区间内最大失败次数
        Time.minutes(5),                      // 失败率统计区间
        Time.seconds(10)));                    // 重启延迟

env.setRestartStrategy(RestartStrategies.noRestart());
```

```yaml
# 配置文件方式（推荐，运维可调）

# ---- 固定延迟 ----
restart-strategy.type: fixed-delay
restart-strategy.fixed-delay.attempts: 3
restart-strategy.fixed-delay.delay: 10s

# ---- 失败率 ----
restart-strategy.type: failure-rate
restart-strategy.failure-rate.max-failures-per-interval: 3
restart-strategy.failure-rate.failure-rate-interval: 5min
restart-strategy.failure-rate.delay: 10s

# ---- 指数退避 ----
restart-strategy.type: exponential-delay
restart-strategy.exponential-delay.initial-backoff: 1s
restart-strategy.exponential-delay.max-backoff: 5min
restart-strategy.exponential-delay.backoff-multiplier: 1.5
restart-strategy.exponential-delay.reset-backoff-threshold: 10min
restart-strategy.exponential-delay.jitter: 0.1

# ---- 不重启 ----
restart-strategy.type: none
```

| 参数 | 含义 | 调优建议 |
| --- | --- | --- |
| `fixed-delay.attempts` | 最多重启几次 | 设太小会在偶发抖动时直接放弃；设太大会掩盖持续故障。**不要设成无限**（否则坏数据会导致永久重启循环） |
| `fixed-delay.delay` | 每次重启的等待 | 太短会重启风暴；太长恢复慢。10-30 秒是常见起点 |
| `failure-rate.max-failures-per-interval` | 区间内容忍的失败次数 | 需要按"正常抖动频率"设定 |
| `failure-rate.failure-rate-interval` | 统计区间 | —— |
| `exponential-delay.initial-backoff` | 首次退避 | 通常 1s |
| `exponential-delay.max-backoff` | 退避上限 | 别设太大（否则故障恢复后要等很久才重启）。几分钟量级 |
| `exponential-delay.backoff-multiplier` | 退避倍数 | 1.5-2 |
| `exponential-delay.reset-backoff-threshold` | 稳定运行多久后重置退避 | 避免"偶尔失败一次就一直处于长退避" |
| `exponential-delay.jitter` | 抖动比例 | **多作业共享集群时建议开启**，避免所有作业同时重启打爆集群 |

> [!warning] 不配置重启策略是一个隐患
> 未显式配置时，Flink 会使用默认策略。**生产作业必须显式配置**，理由是：
> - 默认行为可能在不同版本间变化，运维迁移时容易踩坑；
> - 需要根据"故障是否可自愈"来选择策略（可自愈 → fixed-delay/exponential；不可自愈如坏数据 → failure-rate 或 none）；
> - 重启策略直接影响故障恢复时间（RTO），必须和 SLO 对齐。
>
> **强烈建议：任何"无限重试"的配置都要谨慎。** 一条永远解析不了的坏数据会导致作业无限重启，看起来像"作业一直在跑"其实什么也没处理。

> [!danger] 坏数据导致的重启循环
> **现象**：作业不停地重启，每次都在同一个地方失败（看异常栈总是同一条数据/同一个 key）。
> **原因**：重启策略设成了"无限重试"，而故障是**确定性**的（同一条脏数据每次都会失败）。
> **解法**：① 把重启策略改成 `failure-rate` 或有限的 `attempts`，让它最终失败并告警；② 在业务代码里对脏数据做容错（`try/catch` + 侧输出到死信队列）；③ 用 `OutputTag` 把解析失败的数据旁路出去，让主流程不被污染。

### 6.3 恢复过程

```text
① 检测到故障（subtask 失败 / TM 失联 / checkpoint 失败超限）
        │
② 根据重启策略决定：重启 or 放弃
        │
③ 取消失败的执行尝试（cancel），释放资源
        │
④ 从最近一个 COMPLETED 的 checkpoint 恢复：
     - 重新分配 subtask（可能在不同的 TM 上）
     - 从 CheckpointStorage 下载状态（增量 checkpoint 只需下载差异部分）
     - 按 key group 重新分配状态（见 [[3-状态管理]]）
     - 恢复定时器、窗口状态、2PC 待提交事务
        │
⑤ Source 从 checkpoint 里记录的位点重新开始消费
     - Kafka：seek 到记录的 offset
        │
⑥ 重新处理 [checkpoint 位点, 故障时刻] 之间的所有数据
     ⚠️ 这一段数据是【必然重复处理】的
```

### 6.4 为什么"恢复过程中重复处理是必然的"

这是面试和工程实践都要能说清楚的一点。

**根本原因**：checkpoint 是**周期性**的，而故障是**随机**的。checkpoint 只能记录"某一时刻"的进度，故障发生在两次 checkpoint 之间。

```text
时间轴：
   t=0        t=60s       t=90s(故障)      t=120s
    │           │            │              │
 checkpoint#1  checkpoint#2   💥            checkpoint#3(永远没发生)
    │           │
    └───────────┴────────────┘
        这 30 秒的数据处理结果，
        在 checkpoint#2 里【没有】
        （因为 checkpoint#2 在 t=60s 就拍完了）

恢复：从 checkpoint#2 (t=60s) 恢复
     → source 从 t=60s 的位点重放
     → t=60s ~ t=90s 的数据被【再处理一遍】
```

| 事实 | 说明 |
| --- | --- |
| 重复的范围 | 最多一个 checkpoint 间隔的数据量（实际是"上次 checkpoint 到故障时刻"） |
| 是否可避免 | ❌ **不可能避免**。除非 checkpoint 间隔为 0（等于每条数据都拍快照，性能不可接受） |
| 重复对内部状态的影响 | ✅ 无影响。状态从 checkpoint 恢复后重新计算，结果和"只处理一次"一致（这正是 exactly-once 的含义） |
| 重复对外部的影响 | ⚠️ **取决于 Sink**。事务/幂等 sink 能吸收重复；普通 sink 会写出重复 |
| 减小重复的手段 | 缩短 checkpoint 间隔（代价是开销上升） |

> [!important] 一句话回答"Flink 恢复后为什么会重复数据"
> **因为 checkpoint 是周期性的，故障发生在两次 checkpoint 之间，这段时间的数据在恢复后必须重放。这不影响 Flink 内部状态的正确性（exactly-once 说的是状态），但会冲击没有事务/幂等能力的下游。**
> 这也再次印证了 1.2 节的结论：**端到端 exactly-once 的短板永远在 Sink 上。**

---

## 七、端到端 Exactly-Once

### 7.1 三个前提

| 前提 | 具体要求 | Flink 侧对应能力 |
| --- | --- | --- |
| **① Source 可重放** | 能按位点重新消费，位点能进 checkpoint | `CheckpointedFunction` 保存 offset；Kafka/File/Pulsar 等 source 天然支持 |
| **② 状态能快照** | 内部状态可一致性快照、可恢复 | Checkpoint 机制（见第二~五章） |
| **③ Sink 支持事务或幂等** | 要么 2PC，要么幂等写入 | `TwoPhaseCommitSinkFunction` / 新版 `Sink` API 的 `Committer` / 幂等 upsert |

> [!note] 三者缺一不可
> 只有 ①② 满足 → 内部 exactly-once，外部 at-least-once。
> 只有 ②③ 满足 → source 位点不可靠，可能丢数据。
> 只有 ①③ 满足 → 状态不一致，恢复后计算结果错误。

### 7.2 两阶段提交（2PC）原理

2PC 的目标：**让"写外部系统"这个动作可以延迟到 checkpoint 确认完成之后再真正生效**。

```text
第一阶段（preCommit / 预提交）：
  在 checkpoint 期间，sink 把当前事务的数据 flush 到外部系统，
  但【不提交】——数据对外部系统的读者还不可见（或处于未提交状态）。
  同时把这个事务的句柄写进 sink 的 state（随 checkpoint 一起持久化）。

第二阶段（commit / 提交）：
  当 checkpoint 被确认【完成】后，Flink 回调 sink 的
  notifyCheckpointComplete()，此时才真正 commit 事务，
  数据对外部系统可见。

如果 checkpoint 没完成就故障了：
  恢复后从更早的 checkpoint 恢复 →
  这个未提交的事务根本不在恢复出来的状态里 →
  它的数据对外部永远不可见 → 相当于没发生过（abort）
```

**为什么这样是对的？**

| 情况 | 结果 |
| --- | --- |
| checkpoint 完成 → commit 成功 | 数据可见，且 source 位点也已推进 → 不会重放 ✅ |
| checkpoint 完成 → commit 前故障 | 恢复后从该 checkpoint 恢复，state 里有这个待提交事务 → 重新 commit ✅ |
| checkpoint 未完成 → 故障 | 那个事务不在恢复状态的来源里 → 不会被提交（abort）→ 数据被丢弃，但 source 会重放它 ✅ |

> [!important] "迟到但正确"比"早到但可能错"重要
> 2PC 的本质是**牺牲一部分可见性延迟，换取原子性**。preCommit 之后到 commit 之前的这段窗口里，数据在外部系统是"不可见/未提交"的。这个窗口的长度至少是"checkpoint 从开始到完成的时间"，通常是秒级到分钟级。
> **这是端到端 exactly-once 的延迟代价**，也是为什么很多业务最终选择幂等而不是事务。

### 7.3 `TwoPhaseCommitSinkFunction` 的生命周期

```java
public abstract class TwoPhaseCommitSinkFunction<IN, TXN, CONTEXT>
        extends RichSinkFunction<IN>
        implements CheckpointedFunction, CheckpointListener {

    // ---- 必须实现的四个抽象方法 ----
    protected abstract TXN beginTransaction() throws Exception;
    protected abstract void preCommit(TXN transaction) throws Exception;
    protected abstract void commit(TXN transaction);
    protected abstract void abort(TXN transaction);

    // ---- 恢复时的钩子，有默认实现 ----
    protected void recoverAndCommit(TXN transaction) { commit(transaction); }
    protected void recoverAndAbort(TXN transaction) { abort(transaction); }

    // ---- 框架调用的时机 ----
    // invoke()              → 在当前事务里写数据（写不下就 preCommit 旧事务 + beginTransaction）
    // snapshotState()       → 对当前事务 preCommit，并把它加入 pending 事务状态  ← 第一阶段
    // notifyCheckpointComplete() → commit 该 checkpoint 对应的所有 pending 事务     ← 第二阶段
    // initializeState()     → 恢复 pending 事务（这些属于已完成的 checkpoint → recoverAndCommit）
    // close()               → 中止未提交事务
}
```

**完整生命周期时序：**

```text
时间 →
  invoke(r1) ─ 开启事务 T1，写入 r1
  invoke(r2) ─ 写入 T1
  ┌───────────── checkpoint #1 触发 ─────────────┐
  │ snapshotState()：                             │
  │   preCommit(T1)   ← T1 的数据已发送到外部系统  │
  │                     但未提交（不可见）        │
  │   state.add(T1)   ← 事务句柄进 checkpoint      │
  └───────────────────────────────────────────────┘
  invoke(r3) ─ 开启事务 T2（T1 已经 preCommit 了），写入 r3
  ┌──── checkpoint #1 完成（收到所有 ack）────┐
  │ notifyCheckpointComplete(1)：              │
  │   commit(T1)   ← 真正的提交！数据可见       │
  └────────────────────────────────────────────┘
  invoke(r4) ─ 写入 T2
  ... 循环 ...

故障恢复场景：
  从 checkpoint #1 恢复（假设 #2 没完成）
    → state 里有 T1
    → recoverAndCommit(T1)  ✅（因为 #1 是已完成的 checkpoint）
  假设故障发生在 #1 完成前、从 #0 恢复
    → state 里没有 T1（T1 是 #1 期间才加的）
    → T1 永远不会被 commit → 相当于 abort ✅
```

> [!warning] `invoke` 里的事务切换逻辑
> `TwoPhaseCommitSinkFunction` 默认的 `invoke` 会在事务达到一定条件（如数据量、时间）时执行 `preCommit` 并开启新事务。**这个"提前 preCommit"的机制是有意义的**：它把大事务拆小，避免单个事务持续时间超过外部系统的事务超时限制。
> 但这也带来一个坑：**如果 `preCommit` 的阈值设置不当，`commit` 会在 `notifyCheckpointComplete` 之前发生**（对于某些外部系统，preCommit 就已经让数据可见了）。所以实现 `preCommit` 时必须明确外部系统的语义——**preCommit 绝不能等价于 commit**。

**1.15+ 的新 Sink API**：`TwoPhaseCommitSinkFunction` 已标记为废弃，推荐用新的 Sink API（`Sink` / `SinkWriter` / `Committer`）：

```java
// 新 API 的结构（概念示意）
Sink<IN> sink = Sink
        .<IN>builder()
        .setWriter(...)                  // SinkWriter：负责写
        .setCommitter(...)               // Committer：负责提交（在 checkpoint 完成时被调用）
        .build();
```

新 API 把"sink 的写入逻辑"和"提交逻辑"彻底分离，`Committer` 只做提交，职责更清晰，也更利于和连接器的 checkpoint 生命周期对齐。**新写连接器应该用新 API；读老代码时看到 `TwoPhaseCommitSinkFunction` 也不要意外。**

### 7.4 Kafka Sink 的事务实现

Kafka 的事务能力（producer 的 `transactional.id` + `commitTransaction` + 消费者 `isolation.level=read_committed`）天然适合做 2PC 的底层。

**映射关系：**

| 2PC 阶段 | Kafka 实现 |
| --- | --- |
| `beginTransaction()` | `producer.beginTransaction()` |
| 写入数据 | `producer.send(...)`（在事务内） |
| `preCommit(txn)` | `producer.flush()` —— 把缓冲区数据发送到 broker，但**不提交事务**。此时数据对 `read_committed` 消费者不可见 |
| `commit(txn)` | `producer.commitTransaction()` —— 数据可见 |
| `abort(txn)` | `producer.abortTransaction()` |
| `transactional.id` | 由 `transactionalIdPrefix` + subtask 索引构成，**必须稳定且唯一**，用于跨重启的身份延续和僵尸实例隔离（fencing） |

**Flink 1.15+ 的 `KafkaSink` 配置：**

```java
KafkaSink<String> sink = KafkaSink.<String>builder()
        .setBootstrapServers("kafka:9092")
        .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                .setTopic("output-topic")
                .setValueSerializationSchema(new SimpleStringSchema())
                .build())
        .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
        .setTransactionalIdPrefix("my-flink-job-")     // ⚠️ 见下方说明
        .setProperty("transaction.timeout.ms", "900000")   // 15 分钟
        .build();

stream.sinkTo(sink);
```

```yaml
# 也可以用 SQL 层配置（见 [[8-FlinkSQL与TableAPI]]）
# 'sink.delivery-guarantee' = 'exactly-once'
# 'sink.transactional-id-prefix' = 'my-flink-job-'
```

| 配置 | 说明 |
| --- | --- |
| `DeliveryGuarantee.EXACTLY_ONCE` | 启用事务写入 |
| `DeliveryGuarantee.AT_LEAST_ONCE` | 不开启事务（默认通常也是这个级别） |
| `DeliveryGuarantee.NONE` | 不做任何保证 |
| `transactionalIdPrefix` | 事务 ID 前缀。**不同作业必须用不同的前缀**，同一作业的不同版本也应考虑区分，否则会互相 fencing |
| `transaction.timeout.ms` | ⚠️ **必须满足两个约束**（见下） |

> [!danger] `transaction.timeout.ms` 与 checkpoint 间隔的硬约束
> 这是 Kafka exactly-once 最容易配错、也最容易在生产上炸的地方。
>
> **约束一：`transaction.timeout.ms` <= broker 的 `transaction.max.timeout.ms`**
> broker 端默认上限通常是 15 分钟。producer 侧设得比它大，broker 会直接拒绝，报类似：
> ```
> The transaction timeout is larger than the maximum value allowed by the broker
> ```
>
> **约束二：`transaction.timeout.ms` 必须显著大于 checkpoint 间隔 + checkpoint 耗时**
> 因为事务从 `preCommit`（checkpoint 开始时）到 `commit`（checkpoint 完成后）之间必须保持"活着"。如果这个窗口超过了 `transaction.timeout.ms`：
> ```
> TransactionalId ... : transaction timeout expired   （broker 主动 abort 事务）
> → 之后 commitTransaction() 失败
> → 报 InvalidTxnStateException / ProducerFencedException
> → 作业反复重启
> ```
>
> **实践规则：**
> ```text
> transaction.timeout.ms  >  checkpoint interval + checkpoint duration + 安全余量
> 同时  transaction.timeout.ms  <=  broker 的 transaction.max.timeout.ms
> ```
> 例：checkpoint 间隔 1 分钟、耗时最长 2 分钟 → 事务至少需要 3 分钟以上的存活窗口，可以设成 10 分钟（小于 broker 的 15 分钟上限）。**如果 checkpoint 间隔是 10 分钟，那这个组合基本不可行**，必须缩短 checkpoint 间隔或调大 broker 上限。

> [!warning] `transactionalIdPrefix` 的 fencing 语义
> Kafka 用 `transactional.id` 做**僵尸实例隔离**：同一个 `transactional.id` 的新 producer 一旦初始化，旧 producer 就会被"隔离"（fenced），它后续的操作会抛 `ProducerFencedException`。
>
> **这是好事**（保证僵尸实例不会写入脏数据），但前提是 `transactional.id` 的构造正确：
> - ✅ **同一作业 + 同一 subtask** → 重启前后 `transactional.id` 相同 → 新实例能隔离旧实例
> - ❌ **不同作业用了相同前缀** → 两个作业会互相 fencing，表现为"随机地某一方反复报 `ProducerFencedException` 重启" → **这种故障很难查，因为两边看起来都是随机的**
>
> **规则：每个作业的 `transactionalIdPrefix` 必须全局唯一**（建议加上作业名或环境标识）。

### 7.5 为什么 Kafka Sink 能而 ClickHouse Sink 不能

| Sink | 是否有原生事务 | 结论 |
| --- | --- | --- |
| Kafka | ✅ 有 `transactional.id` + `commitTransaction` | 可以做到 2PC，端到端 exactly-once |
| 支持事务的关系库（MySQL/PG） | ✅ 有 BEGIN/COMMIT | 可以 2PC，但要注意连接必须在 checkpoint 之间保持 |
| Doris | ✅ 有 Stream Load 的 2PC（`sink.enable-2pc`） | 可以 2PC（需 Doris 版本支持） |
| ClickHouse | ❌ 没有事务 | **只能幂等**（`ReplacingMergeTree` + 主键） |
| HDFS/对象存储文件 | ⚠️ 靠"临时文件 + rename 原子改名"模拟 | 可以做（rename 是原子的） |
| Elasticsearch | ❌ 无事务 | 幂等（按 `_id` 覆盖） |
| Redis | ❌ 无事务（MULTI 不是分布式事务） | 幂等（SET 覆盖；`INCR` 不幂等！） |
| HTTP 接口 | ❌ | 幂等（业务侧唯一键）+ at-least-once |

> [!important] 结论
> **端到端 exactly-once 不是 Flink 单方面能给的能力，它需要外部系统的配合。** 当外部系统不支持事务时，唯一的出路是幂等——这就是下一章的内容。

---

## 八、Sink 幂等 vs 事务

### 8.1 幂等写入

**幂等**：同一个操作执行多次，对外部系统的影响和只执行一次相同。

实现方式：**用业务主键做 upsert**，让"重复写入"变成"覆盖同一行"。

| 存储 | 幂等实现 | 注意点 |
| --- | --- | --- |
| **Doris** | Unique Key 模型（按主键 upsert） | 需要保证主键就是业务的唯一标识 |
| **ClickHouse** | `ReplacingMergeTree` + `ORDER BY` 主键 | ⚠️ **去重发生在后台 merge 时**，查询期间可能读到重复行；要精确读需要 `FINAL` 或 `OPTIMIZE`。**这是最容易踩的坑** |
| **MySQL / PG** | `INSERT ... ON DUPLICATE KEY UPDATE` / `INSERT ... ON CONFLICT DO UPDATE` | 需要唯一索引 |
| **Elasticsearch** | 指定 `_id`（同 ID 覆盖） | 版本冲突需要重试 |
| **HBase** | RowKey put（同 key 覆盖） | 天然幂等 |
| **Kafka** | ❌ 只能靠下游幂等 | 用 compacted topic + 主键作为 key 可以缓解（但 compact 是异步的） |
| **Redis** | `SET k v` 幂等；**`INCR` 不幂等** | 计数器类操作不能直接幂等 |

> [!danger] "幂等"的三个前提，缺一不可
> 1. **有稳定的业务主键**。如果主键里包含随机数、时间戳、UUID，那每次重放都会生成"新行"，幂等失效。
> 2. **是覆盖写而不是累加写**。`SET total = 100` 幂等；`INCR total` 不幂等。**累加类语义必须先做聚合（把结果算成一个确定值），再覆盖写。**
> 3. **写入本身是原子的（或至少能收敛）**。部分写入 + 重试可能产生中间态，需要外部系统支持行级原子性。

### 8.2 对比表与选型

| 维度 | 事务写入（2PC） | 幂等写入 |
| --- | --- | --- |
| 原理 | preCommit + checkpoint 完成后 commit | 主键覆盖，重复写等于没写 |
| 是否需要外部系统支持事务 | ✅ 必须 | ❌ 不需要（只需唯一键/主键） |
| 对外部系统的要求 | 支持事务、事务有超时、能按 ID fencing | 支持主键 upsert |
| 数据可见延迟 | **更高**：要等 checkpoint 完成才可见 | **更低**：写完即可见 |
| 抗重复能力 | 强（未提交的事务直接不可见） | 取决于主键设计（设计不好会失效） |
| 抗乱序能力 | 强（事务隔离） | **弱**：后到的旧数据可能覆盖新数据（需要版本号/时间戳判断） |
| 吞吐/延迟代价 | 较大（事务开销 + 可见性延迟） | 很小 |
| 实现复杂度 | 高（事务生命周期、超时、fencing、恢复） | 低（只要保证主键正确） |
| 失败模式 | 事务超时、fencing、`ProducerFencedException` | 主键设计错误导致的静默数据错误 |
| 典型实现 | Kafka Sink（`EXACTLY_ONCE`）、Doris 2PC | Doris Unique Key、ClickHouse ReplacingMergeTree、MySQL upsert |
| 适用 | 计费、账务、对账、金融级链路 | 绝大多数实时数仓链路、大屏、报表 |

> [!tip] 选型口诀
> **能幂等的就幂等，不能幂等的才上事务。**
> 原因：幂等的实现成本和运行时成本都远低于事务，而且**不依赖外部系统的特殊能力**（现实中的存储绝大多数不支持分布式事务）。事务只在"必须绝对不重且无法设计出稳定主键"时才必要。
> 补充一句面试加分项：**幂等方案要注意乱序**。重放的数据可能比已经写入的数据"更旧"，如果无条件覆盖会写入过期值。解法是在数据里带版本号/时间戳，写入时做条件更新（如 Doris 的 `SEQUENCE` 列、ClickHouse 的 `version` 列）。

### 8.3 "幂等 + at-least-once"：最常见的工程折中

这是生产中使用最广的组合，值得单独讲清楚。

```text
Kafka (at-least-once) ──► Flink (checkpoint, AT_LEAST_ONCE 或 EXACTLY_ONCE) ──► Doris (Unique Key upsert)
```

**为什么它能达到"最终一致"？**

| 环节 | 行为 |
| --- | --- |
| Flink 故障恢复 | 从最近的 checkpoint 恢复，重放 [checkpoint 位点, 故障时刻] 的数据 |
| 重放时 | 同一批数据可能被处理两次 → 写出两次 |
| Sink 幂等 | 两次写入的是**同一个主键**，第二次是覆盖 → 外部只看到一份 ✅ |
| 结果 | 最终一致（可能短暂地"看不到"某条数据，但不会重复、不会错） |

| 优点 | 说明 |
| --- | --- |
| 实现简单 | 不需要事务、不需要改外部系统 |
| 延迟低 | 写完即可见，没有 preCommit→commit 的窗口 |
| 兼容性强 | 几乎所有存储都支持主键 upsert |
| 成本低 | 事务开销为零，吞吐更高 |
| 容错好 | 幂等天然吸收任意次重放 |

| 前提/风险 | 说明 |
| --- | --- |
| 必须有稳定主键 | 主键设计错误 → 幂等失效 → 静默产生重复数据（最难查的故障） |
| 必须处理乱序 | 后到的旧数据覆盖新数据 → 需要版本号/时间戳条件写入 |
| 中间态可能可见 | 大屏在恢复期间可能短暂显示偏小/偏大的值（但因为会立即被覆盖修正，影响可控） |
| 计数类指标不适用 | `SUM` 类结果如果按明细行 upsert 是可以的，但如果直接 `INCR` 一个计数器就不行 |

> [!important] 面试回答的完整姿势
> 被问到"你们怎么保证 exactly-once"时，最好的回答不是"我们开了 exactly-once"，而是：
> **"我们的 Kafka Source 可重放，用 checkpoint 保证内部状态精确一次；Sink 端我们用的是 Doris Unique Key 模型做幂等 upsert，所以整体是 at-least-once + 幂等，达到最终一致。之所以不用 Kafka 的 2PC 事务，是因为我们要写 Doris 而不是 Kafka，而且幂等方案延迟更低、不依赖外部事务能力。为了防乱序，我们在数据里带了版本号做条件更新。"**
> 这个回答覆盖了：**语义分层、方案选型理由、乱序处理、成本权衡** —— 比背概念高一个层次。

---

## 九、端到端链路示例

### 9.1 链路：Kafka → Flink（有状态计算）→ Kafka

**目标**：真正的端到端 exactly-once（Kafka 事务）。

```java
public class KafkaToKafkaExactlyOnce {

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // ---- ① Checkpoint 配置 ----
        env.enableCheckpointing(60_000);                       // 1 分钟一次
        env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
        env.getCheckpointConfig().setCheckpointTimeout(300_000);
        env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30_000);
        env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);
        env.getCheckpointConfig().setTolerableCheckpointFailureNumber(3);
        env.getCheckpointConfig().setExternalizedCheckpointCleanup(
                ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION);
        env.getCheckpointConfig().setCheckpointStorage("hdfs:///flink/checkpoints");

        // ---- ② 状态后端 ----
        env.setStateBackend(new EmbeddedRocksDBStateBackend(true));  // 增量 checkpoint

        // ---- ③ Source：可重放，offset 进 checkpoint ----
        KafkaSource<OrderEvent> source = KafkaSource.<OrderEvent>builder()
                .setBootstrapServers("kafka:9092")
                .setTopics("order-topic")
                .setGroupId("order-job")
                .setStartingOffsets(OffsetsInitializer.committedOffsets(OffsetResetStrategy.EARLIEST))
                .setValueOnlyDeserializer(new OrderEventDeserializer())
                // commit.offsets.on.checkpoint 默认开启：
                // Flink 会在 checkpoint 完成时把 offset 提交到 Kafka 的消费者组
                .setProperty("commit.offsets.on.checkpoint", "true")
                .build();

        DataStream<OrderEvent> orders = env.fromSource(
                source,
                WatermarkStrategy.<OrderEvent>forBoundedOutOfOrderness(Duration.ofSeconds(5))
                        .withTimestampAssigner((e, ts) -> e.getOrderTime())
                        .withIdleness(Duration.ofMinutes(1)),
                "order-source")
                .uid("order-source");

        // ---- ④ 有状态计算 ----
        SingleOutputStreamOperator<OrderResult> result = orders
                .keyBy(OrderEvent::getUserId)
                .window(TumblingEventTimeWindows.of(Time.minutes(5)))
                .allowedLateness(Time.minutes(2))
                .aggregate(new OrderAggregate(), new OrderWindowResult())
                .uid("order-window");

        // ---- ⑤ Sink：Kafka 事务（端到端 exactly-once）----
        KafkaSink<OrderResult> sink = KafkaSink.<OrderResult>builder()
                .setBootstrapServers("kafka:9092")
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic("order-result-topic")
                        .setValueSerializationSchema(new OrderResultSerializationSchema())
                        .build())
                .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
                .setTransactionalIdPrefix("order-job-v1-")     // ⚠️ 全局唯一
                // transaction.timeout.ms 必须 > checkpoint 间隔 + 耗时，
                // 且 <= broker 的 transaction.max.timeout.ms
                .setProperty("transaction.timeout.ms", "600000")   // 10 分钟
                .build();

        result.sinkTo(sink).uid("order-kafka-sink");

        // ---- ⑥ 重启策略 ----
        env.setRestartStrategy(RestartStrategies.fixedDelayRestart(3, Time.seconds(10)));

        env.execute("kafka-to-kafka-exactly-once");
    }
}
```

**配置清单（逐项解释"为什么"）：**

| 配置 | 值 | 为什么 |
| --- | --- | --- |
| `enableCheckpointing` | 60s | 间隔越短，故障重放越少；但不能太短，否则开销大 |
| `CheckpointingMode` | EXACTLY_ONCE | 启用 barrier 对齐，保证快照是合法切面 |
| `CheckpointStorage` | HDFS | 生产必须持久化存储。JM 内存 checkpoint 会在 JM 挂掉时全丢 |
| `StateBackend` | RocksDB + 增量 | 状态可能超内存，增量 checkpoint 降低成本 |
| `commit.offsets.on.checkpoint` | true | offset 提交到 Kafka 消费者组，便于外部监控消费进度（也便于切换到其他消费者） |
| `setStartingOffsets` | committedOffsets | 优先从**已提交的 offset** 恢复；这是 Flink 恢复的正确起点 |
| `DeliveryGuarantee` | EXACTLY_ONCE | 启用 Kafka 事务 |
| `transactionalIdPrefix` | 全局唯一 | 避免不同作业互相 fencing |
| `transaction.timeout.ms` | > checkpoint interval + duration | 保证事务在 preCommit→commit 窗口内不超时 |
| `RestartStrategy` | fixed-delay 3 次 | 不要无限重启；坏数据导致的确定性故障应该暴露出来 |

> [!warning] `read_committed`：下游消费者必须配
> Kafka Sink 写了未提交事务的数据，**只有配置了 `isolation.level=read_committed` 的消费者才看不到**。默认的 `read_uncommitted` 消费者会读到未提交甚至最终被 abort 的数据！
> **检查清单**：你的下游消费者（包括另一个 Flink 作业、Spark、业务服务）是否都配了 `isolation.level=read_committed`？如果有任何一个没配，端到端 exactly-once 就漏了。
> 另外注意：`read_committed` 消费者的读取上界是 **LSO（Last Stable Offset）**，长事务会造成队头阻塞（Kafka 侧的细节见 [[6-事务与Exactly-Once]]）。

### 9.2 链路：Kafka → Flink → Doris（幂等方案）

**目标**：最终一致（at-least-once + 幂等），这是实时数仓最主流的方案。

```java
// Doris Sink（Flink-Doris-Connector）
DorisSink dorisSink = DorisSink.builder()
        .setDorisReadOptions(DorisReadOptions.builder().build())
        .setDorisExecutionOptions(DorisExecutionOptions.builder()
                .setLabelPrefix("order-result-" + jobId)     // 幂等标签
                .setDeletable(false)
                // 可选：开启 2PC（需要 Doris 版本支持）
                // .enable2PC()
                .build())
        .setDorisOptions(DorisOptions.builder()
                .setFenodes("doris-fe:8030")
                .setTableIdentifier("db.order_result")
                .setUsername("root")
                .setPassword("***")
                .build())
        .build();

result.sinkTo(dorisSink);
```

```sql
-- Doris 表必须建为 Unique Key 模型，主键是业务唯一标识
CREATE TABLE db.order_result (
    user_id       VARCHAR(64),
    window_start  DATETIME,
    window_end    DATETIME,
    order_cnt     BIGINT,
    total_amount  DECIMAL(20, 2)
)
UNIQUE KEY(user_id, window_start, window_end)     -- ✅ 幂等的关键
DISTRIBUTED BY HASH(user_id) BUCKETS 16
PROPERTIES ("replication_num" = "3");
```

| 配置 | 要点 |
| --- | --- |
| Doris 表模型 | **Unique Key**，主键必须包含业务唯一标识（如 `user_id + window_start + window_end`） |
| `labelPrefix` | 用于 Doris 的导入事务标识。**同一作业重启后必须能生成相同的 label 才能保证幂等**——通常用"作业 ID + checkpoint ID + subtask"构造 |
| Flink 侧 | `AT_LEAST_ONCE` 或 `EXACTLY_ONCE` 都可以（幂等由 Doris 保证），但 checkpoint 必须开 |
| 乱序防护 | 如果重放的数据可能"更旧"，用 Doris 的 `SEQUENCE` 列做条件更新；或者在主键里带上版本信息 |
| 窗口结果多次输出 | 因为 `allowedLateness` 会让同一窗口输出多次，Doris 的 Unique Key upsert 正好能吸收（**这也是为什么"窗口 + upsert 存储"是天生一对**） |

> [!important] 为什么这是实时数仓的主流
> 1. **延迟低**：不需要等 checkpoint 完成，数据写完即可见；
> 2. **兼容性好**：不依赖 Doris 的事务能力（`enable2pc` 可选）；
> 3. **天然处理窗口的多次输出**：Unique Key upsert 让"同一个窗口的修正结果覆盖旧结果"变得自然；
> 4. **成本低**：事务开销为零。
>
> 代价是：**必须保证主键设计正确**。主键设计错了（比如把 `window_end` 漏了，或者主键包含时间戳），幂等就失效，而这类 bug 往往在故障恢复后才暴露，非常难查。

### 9.3 外部系统不支持事务时的降级方案

| 降级手段 | 做法 | 效果 |
| --- | --- | --- |
| **幂等（首选）** | 主键 upsert、覆盖写、条件更新 | 最终一致，延迟低 |
| **业务侧去重表** | 下游系统自己维护"已处理 ID"表，处理前先查 | 效果好但增加下游负担和延迟 |
| **数据带唯一 ID + 下游去重** | 每条记录带全局唯一 ID，下游按 ID 去重 | 通用，但下游必须有去重能力 |
| **改成 at-least-once + 离线对账** | 接受重复，用离线批次任务做最终修正 | 简单粗暴，适合容忍窗口较大的场景 |
| **只有状态精确一次，sink 不保证** | 明确告知业务方"sink 侧可能重复" | 诚实但需要业务接受 |
| **换 sink** | 把不幂等的存储换成幂等的存储（如 ClickHouse 换 Doris，或加一层 Kafka 中转） | 成本高但根治 |

> [!danger] 最危险的降级是"没意识到自己降级了"
> 很多团队以为"我们开了 checkpoint 就是 exactly-once"，但 sink 是个普通的 ClickHouse `INSERT`（MergeTree，非 Replacing）。平时跑起来完全正常，**只有在故障重启后才会出现重复数据**——而故障可能是几个月才发生一次，到那时已经没人记得当初的设计了。
> **建议**：在作业的文档/注释里明确写清"本作业的端到端语义是什么、依赖什么前提、如果前提被破坏会怎样"。这是技术负责人应该建立的规范。

---

## 十、常见故障与排查

### 10.1 Checkpoint 超时 / 失败

| 现象 | 可能原因 | 排查手段 | 处理 |
| --- | --- | --- | --- |
| `Checkpoint expired before completing` | 超过 `execution.checkpointing.timeout` | 看 Web UI 的 checkpoint 详情：是对齐慢还是状态上传慢 | 见下方逐一分析 |
| checkpoint 耗时随反压增长 | **barrier 对齐等待** | 看 BackPressure 面板，看各算子的 `checkpointAlignmentTime` | 消除反压；或开 unaligned |
| 状态上传慢 | 状态太大 / DFS 慢 / 网络带宽不足 | 看 checkpoint size 趋势、DFS 的写入耗时 | 增量 checkpoint；减小状态（TTL）；换 DFS |
| 个别 subtask 特别慢 | **数据倾斜** | 看各 subtask 的 checkpoint duration 分布 | 加盐、预聚合、换 key |
| checkpoint 频繁失败后重启 | 状态过大导致不可持续 | 看 size 是否单调增长 | 治理状态膨胀（见 [[3-状态管理]]） |
| `Received barrier from a checkpoint that has already been subsumed` | 并发 checkpoint / 版本不一致 | —— | 通常无需处理，属于正常丢弃 |

**排查的黄金三步：**

```text
1. 看【反压】——checkpoint 慢的第一嫌疑人是对齐等待
2. 看【各 subtask 的耗时分布】——是否倾斜
3. 看【checkpoint size 趋势】——状态是否失控
```

```yaml
# 缓解配置（按优先级）
execution.checkpointing.unaligned: true            # ① 对齐慢 → 开 unaligned
execution.checkpointing.timeout: 600000            # ② 适度放大超时
execution.checkpointing.min-pause: 60000           # ③ 给作业喘息
execution.checkpointing.max-concurrent-checkpoints: 1
state.backend.incremental: true                    # ④ 增量 checkpoint
```

> [!tip] 区分"对齐慢"和"状态上传慢"
> 在 Web UI 的 Checkpoint 详情里能看到每个 subtask 的 **`Sync Duration`（同步阶段，含对齐）** 和 **`Async Duration`（异步上传阶段）**。
> - `Sync Duration` 高 → 对齐等待 / checkpoint lock 竞争 → **unaligned 有帮助**
> - `Async Duration` 高 → 状态上传 / DFS 慢 → **unaligned 没用**，要治状态大小和存储
>
> 这个区分是面试和实战的分水岭：**很多人一看到 checkpoint 慢就开 unaligned，但如果瓶颈在状态上传，开了完全没用。**

### 10.2 恢复后重复数据激增

| 排查项 | 说明 |
| --- | --- |
| 是否有大量重放？ | 从 checkpoint 恢复必然重放 [checkpoint 位点, 故障点] 的数据。看恢复时的 lag 和 source 读取量 |
| **Sink 是否幂等/事务？** | 这是根本。非幂等 sink + 重放 = 必然重复 |
| **主键设计是否正确？** | 幂等 sink 里，主键包含随机数/时间戳会导致"每次都是新行" |
| checkpoint 间隔是否过长？ | 间隔越长，重放越多，重复越多 |
| 是不是重启了多次？ | 反复重启会反复重放，重复量累积 |
| 是否开启了 `AT_LEAST_ONCE` 模式？ | 该模式本身就允许重复 |
| 下游是否有乱序覆盖问题？ | 重放的旧数据覆盖了已写入的新数据 → 看起来像"数据错误"而不是"重复" |

> [!important] 关键结论：重复不是 bug，是设计
> **从 checkpoint 恢复后重放数据是**必然**的**（见 6.4）。所以"恢复后重复数据激增"这个现象本身是预期的，真正的问题是"**你的 sink 没有吸收重复的能力**"。
> 排查方向不是"怎么让 Flink 不重放"，而是"**为什么 sink 没有幂等**"。

### 10.3 2PC Sink 事务超时

**症状**：

```text
org.apache.kafka.common.errors.InvalidTxnStateException:
  TransactionalId order-job-v1-0: transaction timeout expired

或

org.apache.kafka.common.errors.ProducerFencedException
```

| 原因 | 诊断 | 处理 |
| --- | --- | --- |
| **事务存活时间 > `transaction.timeout.ms`** | 对比 `transaction.timeout.ms` 与 (checkpoint interval + checkpoint duration) | 调大 `transaction.timeout.ms`（注意 broker 上限），或缩短 checkpoint 间隔/耗时 |
| broker 的 `transaction.max.timeout.ms` 小于 producer 配置 | 看 broker 日志 | 调大 broker 配置，或调小 producer 配置 |
| checkpoint 长时间无法完成 | 见 10.1 | 先把 checkpoint 治好 |
| **不同作业用了相同的 `transactionalIdPrefix`** | 看是否有另一个作业在报 `ProducerFencedException` | **每作业唯一前缀** |
| 恢复后旧实例没被清理 | 看是否有僵尸 TM | 靠 transactional.id fencing 自动解决；确认前缀稳定 |
| 状态恢复时事务被 abort | 恢复日志里找 `recoverAndAbort` | 检查 checkpoint 是否真的完成 |

> [!danger] 这个故障的连锁反应
> 事务超时 → `commitTransaction` 失败 → sink 抛异常 → 作业重启 → 恢复后又要提交同样的事务（可能再次超时）→ **重启循环**。
> 而且**在重启循环期间，下游 `read_committed` 消费者看不到任何数据**（因为事务一直没提交）→ 业务感知为"数据完全不产出了"。
> **这是最容易造成生产事故的一类配置错误**，因为它在压力小的时候完全正常，只在"checkpoint 变慢 + 数据量上涨"时爆发。**上线前必须把 `transaction.timeout.ms` 和 checkpoint 参数一起做过压测。**

### 10.4 状态恢复不兼容（savepoint 恢复失败）

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| `Could not find a state with name xxx` | 状态名改了，或算子结构变了 | 恢复状态名；或接受无法恢复 |
| `Cannot map checkpoint/savepoint state for operator xxx to the new program` | 算子 `uid()` 变了（没设 uid 时会自动生成哈希） | **给所有有状态算子显式设 `uid()`**，且上线后永不修改 |
| `Failed to deserialize state` | 状态类型/serializer 变了 | 见 [[3-状态管理]] 的 schema 演进规则 |
| `The new parallelism exceeds the max parallelism` | `maxParallelism` 不够 | 只能重导数据或用 `--allowNonRestoredState`（会丢状态） |
| Kryo 相关的反序列化失败 | 状态类型退化成 Kryo，且类结构变了 | 改成 POJO/Avro |

```java
// ✅ 每个有状态算子都必须设 uid，且上线后永不修改
stream.keyBy(...)
      .window(...)
      .aggregate(...)
      .uid("order-window-agg")          // 恢复契约的一部分，改了就恢复不了
      .name("Order Window Aggregate");  // name 只是显示用，随便改
```

> [!important] savepoint 兼容性是"设计约束"而不是"运维问题"
> 它必须在**代码设计阶段**就考虑：状态名、类型、`uid()`、`maxParallelism` 都是**一旦上线就不可变的契约**。
> 建议做法：把 state 名称和 uid 集中定义成常量，加上注释说明"不可修改"。详细内容见 [[5-Checkpoint与Savepoint]]。

### 10.5 其他常见现象

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| checkpoint 一直显示 `IN_PROGRESS` | 某个 subtask 卡住（反压、GC、死锁） | 看 thread dump、看反压面板 |
| checkpoint 成功但作业仍重启 | 故障不是 checkpoint 相关的（如 OOM、上游异常） | 看 TM 日志和异常栈 |
| 恢复后水位不推进 | 空闲分区、时间戳单位错误 | 见 [[2-时间与窗口]] |
| 恢复后窗口重复输出 | 正常的（`allowedLateness` + 恢复重放） | 下游必须支持 upsert |
| unaligned 开启后 checkpoint 更大但没变快 | 瓶颈不在对齐，在状态大小 | 关掉 unaligned，去治状态 |
| 作业反复 `ProducerFencedException` | 两个作业用了相同 `transactionalIdPrefix` | 保证前缀全局唯一 |

---

## 十一、必答问题

> [!question] 必答：Flink 怎么保证精确一次？
>
> **三段式答题骨架（Source 位点 + Checkpoint + Sink 提交）。**
>
> ---
>
> **第一段：Source 位点——解决"从哪重放"。**
> Source 必须是**可重放的**，并且位点要能进 checkpoint。Flink 的 Source 通过 `CheckpointedFunction` 把自己的读取位置（Kafka offset、文件位置、binlog 位点）写进快照。恢复时从这个位点继续消费。
> 这是 exactly-once 的前提——如果源不可重放，丢了就是丢了，谈不上语义。
>
> ---
>
> **第二段：Checkpoint——解决"Flink 自己算得对"。**
> 核心是 **Chandy-Lamport 分布式快照**的 Flink 实现：
> 1. JobManager 的 `CheckpointCoordinator` 周期性触发 checkpoint，向 Source 注入 **barrier**；
> 2. barrier 随数据流向下游传播，多输入算子做 **barrier 对齐**（收到某个输入的 barrier 后阻塞该通道、缓存其后续数据，继续处理其他输入直到所有 barrier 到齐）；
> 3. 对齐保证每个算子的快照都对应同一个"数据切面"——**barrier 之前的数据全部计入状态，barrier 之后的数据全部不计入**；
> 4. 各算子异步把状态上传到 CheckpointStorage，向 JM 上报 ack；
> 5. JM 收齐所有 ack 后把 checkpoint 标记为 **completed**。
> 恢复时从最近一个 completed 的 checkpoint 还原：状态按 key group 重新分配，source 位点回退，**重放 [checkpoint 位点, 故障点] 的数据**。
> 注意：**重放是必然的**（checkpoint 是周期性的，故障是随机的），但这不影响 Flink 内部状态的正确性——重放后重新计算得到的状态和"只处理一次"一致。**这就是 exactly-once 说的"effectively once"：保证的是状态效果，不是"数据不被物理重放"。**
>
> ---
>
> **第三段：Sink 提交——解决"外部看到什么"。**
> 前面两段只保证 Flink 内部，**端到端 exactly-once 的短板在 sink**。两条路：
> - **两阶段提交（2PC）**：checkpoint 期间 sink 做 `preCommit`（数据发出去但不提交，外部不可见），事务句柄随 checkpoint 持久化；**checkpoint 完成通知（`notifyCheckpointComplete`）后才 `commit`**。恢复时，如果对应 checkpoint 没完成，这个事务根本不在恢复出来的状态里 → 相当于 abort。Kafka Sink 的 `DeliveryGuarantee.EXACTLY_ONCE` 就是用 Kafka 事务实现的：`beginTransaction` / `flush`（preCommit）/ `commitTransaction`，配合 `transactionalIdPrefix` 做僵尸实例隔离。
> - **幂等写入**：用业务主键 upsert（Doris Unique Key、ClickHouse ReplacingMergeTree、MySQL upsert），重复写入等于覆盖。**这是工程上更常用的方案**，因为它延迟更低、不依赖外部系统的事务能力。
>
> ---
>
> **收尾：加上工程判断（这是拉开差距的部分）。**
> - **"我们实际用的是 at-least-once + 幂等写 Doris，达到最终一致。** 因为我们的目标是 Doris 而不是 Kafka，Doris 没有分布式事务的普遍能力，而幂等方案延迟更低、成本更小。为了防乱序，我们在数据里带版本号做条件更新。"
> - **"如果外部系统既不支持事务也不能幂等，那端到端 exactly-once 在理论上就不成立**，只能降级为 at-least-once + 下游去重，或者换成幂等的存储。"
> - **"2PC 有个必须注意的配置约束**：`transaction.timeout.ms` 必须大于 checkpoint 间隔加耗时，同时不能超过 broker 的 `transaction.max.timeout.ms`，否则会出现事务超时导致的重启循环。"

> [!question] 必答：Barrier 对齐的流程是什么，为什么要对齐？
> **流程**（多输入算子）：收到某个输入的 barrier 后，**立刻阻塞该通道**（其后续数据被缓存，不能处理），**继续处理其他输入的数据**；直到所有输入的 barrier 都到齐，才快照本地状态、向下游广播 barrier、解除阻塞。
> **为什么要对齐**：状态的快照必须对应一个明确的"数据切面"。如果不对齐——比如 A 的 barrier 到了就继续处理 A 之后的数据（属于下一个 epoch）——快照的状态里就混入了下一轮的数据。恢复时这部分数据会被重放并再次处理，语义就退化为 at-least-once。
> **代价**：对齐等待时间取决于**最慢的输入**，所以反压会直接转化为 checkpoint 耗时增长，甚至导致 checkpoint 超时，形成"反压 → checkpoint 超时 → 重启 → 更严重的反压"的恶性循环。
> **解法**：`execution.checkpointing.mode: AT_LEAST_ONCE`（放弃 exactly-once，不对齐、更快）、`unaligned` checkpoint（barrier 越过缓冲区）、或者从根因上消除反压。

> [!question] 必答：Unaligned Checkpoint 解决了什么问题，代价是什么？
> **解决的问题**：在反压场景下，barrier 要排在被阻塞的数据后面，对齐等待时间极长导致 checkpoint 超时。unaligned 让 barrier **越过缓冲区直接传播**，把还没被处理的数据（in-flight data）作为 **Channel State** 一起写进快照，从而消除对齐等待。
> **代价**：① checkpoint 变大（要保存所有 in-flight 数据）；② 恢复时需要先重放这些 in-flight 数据，恢复时间变长；③ 上传/下载带宽压力增加；④ 部分算子和特殊拓扑不支持。
> **关键判断**：unaligned 只解决"对齐等待"，**不解决"状态太大"**。如果 checkpoint 慢是因为状态上传（`Async Duration` 高）而不是对齐（`Sync Duration` 高），开 unaligned 完全没用。**所以要先区分瓶颈在哪。**
> **定位**：在 Web UI 的 checkpoint 详情里看每个 subtask 的 Sync / Async Duration。

> [!question] 必答：为什么恢复后一定会重复处理数据？
> 因为 **checkpoint 是周期性的，而故障是随机的**。checkpoint 只能记录"某一时刻"的进度（比如 t=60s 的状态和位点），而故障可能发生在 t=90s。那么 t=60s 到 t=90s 之间的数据处理结果**不在任何 checkpoint 里**，恢复时只能从 t=60s 的位点重放，这 30 秒的数据就被处理了两遍。
> 重复的范围是"最近一次完成的 checkpoint 到故障时刻"，最坏是一个 checkpoint 间隔的数据量。
> **这个重复无法避免**（除非 checkpoint 间隔为 0，性能不可接受）。但它**不影响 Flink 内部状态的正确性**——状态从 checkpoint 恢复后重新计算，结果和"只处理一次"相同。**它影响的是外部系统**：没有事务/幂等能力的 sink 会写出重复数据。
> **所以正确的应对不是"让 Flink 不重放"（做不到），而是"让 sink 能吸收重复"（幂等或事务）；或者缩短 checkpoint 间隔来减小重复的量。**

> [!question] 必答：2PC 的 `preCommit` 和 `commit` 分别在什么时刻发生？
> - **`preCommit` 在 checkpoint 进行期间发生**：sink 把当前事务的数据 flush 到外部系统，但**不提交**——数据对 `read_committed` 的读者还不可见。同时这个事务的句柄被写进 sink 的 state，随 checkpoint 一起持久化。这保证了"如果 checkpoint 没完成，事务可以被安全地放弃"。
> - **`commit` 在 checkpoint 完成之后发生**：JM 收齐所有 ack 后把 checkpoint 标记为 completed，然后回调每个算子的 **`notifyCheckpointComplete()`**，sink 在这里才真正 `commitTransaction()`，数据对外可见。
> **为什么必须这样分**：如果 checkpoint 还没完成就 commit，而作业在 commit 之后、checkpoint 完成之前挂了，恢复后会从更早的 checkpoint 恢复，那批数据会被再次写入 → 重复。
> **恢复时的行为**：state 里保存的 pending 事务属于"已完成的 checkpoint"，所以通过 `recoverAndCommit` 提交；而对应的 checkpoint 未完成的事务根本不会出现在被恢复的状态里，等效于 abort。
> **工程约束**：`transaction.timeout.ms` 必须大于 checkpoint 间隔加耗时，否则事务会在 preCommit→commit 窗口内被 broker 主动 abort（Kafka 场景下表现为 `InvalidTxnStateException` / `ProducerFencedException` 导致的重启循环）。

> [!question] 必答：幂等写入和事务写入怎么选？
> **原则：能幂等的就幂等，不能幂等的才上事务。**
> | | 事务（2PC） | 幂等 |
> | --- | --- | --- |
> | 是否需要外部系统支持事务 | ✅ 必须 | ❌ 只需主键 upsert |
> | 数据可见延迟 | 较高（等 checkpoint 完成） | 低（写完即可见） |
> | 抗乱序 | 强 | 弱（需版本号/时间戳做条件更新） |
> | 实现复杂度 | 高（超时、fencing、恢复） | 低 |
> | 典型 | Kafka Sink EXACTLY_ONCE、Doris 2PC | Doris Unique Key、ClickHouse ReplacingMergeTree |
>
> **现实中的选择**：绝大多数实时数仓链路选幂等（Kafka → Flink → Doris Unique Key），因为延迟低、不依赖外部事务能力、成本小。代价是**主键必须设计正确**——主键里如果混入随机数/时间戳，幂等就失效，而且这类 bug 只在故障恢复后才暴露，极难排查。
> **幂等的三个前提**：① 有稳定的业务主键；② 是覆盖写而不是累加写（`INCR` 不幂等）；③ 写入是原子的或能收敛。
> **加分点**：主动提"幂等方案要注意乱序——重放的数据可能比已写入的更旧，需要版本号做条件更新"，以及"`ReplacingMergeTree` 的去重发生在后台 merge 时，查询期间可能读到重复行，需要 `FINAL` 或 `OPTIMIZE`"。

> [!question] 必答：`transaction.timeout.ms` 怎么配，为什么？
> **两个硬约束：**
> 1. **必须 <= broker 的 `transaction.max.timeout.ms`**（broker 默认上限通常是 15 分钟），否则 broker 直接拒绝，报 "transaction timeout is larger than the maximum value allowed by the broker"。
> 2. **必须显著大于 `checkpoint interval + checkpoint duration + 安全余量`**，因为事务要在 `preCommit`（checkpoint 开始）到 `commit`（checkpoint 完成后）这个窗口内保持存活。如果超时：broker 主动 abort 事务 → 之后的 `commitTransaction()` 失败 → 报 `InvalidTxnStateException` / `ProducerFencedException` → 作业重启 → 恢复后可能再次超时 → **重启循环**。
>
> **实践公式**：
> ```text
> transaction.timeout.ms > checkpoint interval + checkpoint duration + 余量
> transaction.timeout.ms <= broker 的 transaction.max.timeout.ms
> ```
> **为什么这个故障特别危险**：它在压力小的时候完全正常，只在"checkpoint 变慢 + 数据量上涨"时爆发；而且重启循环期间下游 `read_committed` 消费者看不到任何数据，业务表现为"完全不产出"。**所以上线前必须把这两个参数和 checkpoint 参数一起做过压测。**

> [!question] 必答：Flink 的 exactly-once 到底"精确"在什么上？
> **精确在"状态更新的效果"上，不是"数据被处理的物理次数"上。** 恢复后数据**一定会被重放**（见上），但重放后状态重算的结果和"只处理一次"一致。这叫 **effectively once（效果上一次）**。
> 所以当有人说"Flink 保证 exactly-once，所以数据不会重复"时，需要立刻追问：**"你的 sink 是什么？"**
> - sink 是 Kafka + `DeliveryGuarantee.EXACTLY_ONCE` → 端到端 exactly-once（需下游配 `read_committed`）
> - sink 是幂等 upsert → at-least-once + 幂等 → 最终一致
> - sink 是普通 append（如非 Replacing 的 ClickHouse MergeTree、HTTP 接口）→ **实际只是 at-least-once**，恢复后会重复写入
>
> **这个澄清是这道题的真正考点**：区分"Flink 内部语义"和"端到端语义"，并且知道瓶颈永远在 sink 上。

---

## 相关笔记

- [[0-Flink总览]] —— 系列索引
- [[1-架构与运行时]] —— barrier 在 TaskManager 网络栈中的处理、checkpoint lock
- [[2-时间与窗口]] —— checkpoint 恢复后 watermark 与定时器的行为
- [[3-状态管理]] —— 状态后端选型、增量 checkpoint、状态 schema 演进与 savepoint 兼容
- [[5-Checkpoint与Savepoint]] —— checkpoint/savepoint 的完整参数、存储配置、运维操作
- [[6-背压与性能调优]] —— 反压定位、对齐开销、Sync/Async Duration 的区分
- [[7-FlinkCDC与实时数仓]] —— CDC source 的位点管理与端到端链路设计
- [[8-FlinkSQL与TableAPI]] —— SQL 层的 `sink.delivery-guarantee`、`sink.transactional-id-prefix`
- [[9-部署与运维]] —— checkpoint 目录规划、重启策略的运维配置、故障处理流程
- [[10-面试高频题]] —— 本篇问题的精简速答版
- [[11-端到端一致性]] —— **本篇讲内部原理（快照算法、barrier 对齐、unaligned、重启恢复），那一篇讲工程落地（各环节配置前提、EOS 验证方法、降级矩阵），建议对照阅读**
