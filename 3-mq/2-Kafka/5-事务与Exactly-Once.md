# Kafka 事务与 Exactly-Once

> 本篇回答四个问题：Kafka 的三种投递语义分别在什么条件下成立？幂等生产者为什么是事务的地基？事务的 `transactional.id` / Transaction Coordinator / `__transaction_state` 三者是怎么协作完成两阶段提交的？为什么开了 `read_committed` 之后消费者会"变慢"，这个慢到底慢在哪里？
> 前置阅读：[[2-架构与核心概念]]、[[2-生产者原理]]、[[3-消费者与Rebalance]]、[[4-日志存储与副本机制]]。实战集成见 [[9-SpringBoot实战]]，面试速答见 [[10-面试高频题]]。

---

## 一、投递语义：先把"保证什么"说清楚

### 1.1 三种语义的定义

投递语义讨论的从来不是"消息会不会丢"这一件事，而是**在故障（网络抖动、broker 重启、生产者进程崩溃、消费者 rebalance）发生时，一条消息被处理的次数**。

| 语义 | 定义 | 典型代价 | 典型场景 |
| --- | --- | --- | --- |
| at-most-once（至多一次） | 消息可能丢，但绝不会重复 | 不重试 / 先提交位移再处理 | 日志采集、监控埋点、可容忍丢样本的指标 |
| at-least-once（至少一次） | 消息不丢，但可能重复 | 重试 + 处理成功后再提交位移 | 绝大多数业务消息（配合下游幂等） |
| exactly-once（精确一次） | 不丢且不重，**在 Kafka 内部闭环** | 事务 + 幂等 + 隔离级别，吞吐下降、延迟上升 | 流式计算、账务类"读-算-写"链路 |

> [!warning] exactly-once 是一个"端到端"概念，不是单点能力
> Kafka 只能保证"**从 Kafka 读、写回 Kafka**"这一段是精确一次的。一旦链路中出现数据库、HTTP 接口、Redis、下游 MQ，Kafka 的事务**无法**把外部系统纳入同一个原子提交。此时"exactly-once"必然退化为 at-least-once + **业务侧幂等**。

### 1.2 三种语义在 Kafka 中如何达成

| 目标语义 | 生产者侧 | 消费者侧 | 关键点 |
| --- | --- | --- | --- |
| at-most-once | `retries=0`，`acks=0/1` | 先 `commitSync()` 再处理 | 处理前就提交位移，崩溃即丢 |
| at-least-once | `retries>0` + `acks=all`（默认 `enable.idempotence=true` 时天然满足） | 处理完再提交位移 | 崩溃后从上次位移重放 → 重复 |
| exactly-once（Kafka 内） | 幂等生产者 + 事务（`transactional.id`） | `isolation.level=read_committed` + 位移随事务提交 | 位移与输出记录在**同一个事务**里原子提交 |

**传统 at-least-once 的重复从哪来**：消费者 poll 到一批消息 → 处理完 → 写下游 → 提交位移。如果"写下游成功、提交位移前进程挂了"，重启后从旧位移重放，下游就多收到一遍。这就是"重复"的根因 —— **位移提交与业务副作用不在同一个原子单元里**。Kafka 事务的价值，恰恰是把"位移提交"也变成一个可回滚的 Kafka 写操作。

### 1.3 关键限制：闭环之外没有 exactly-once

```text
   [Kafka input-topic] --poll--> [你的处理逻辑] --send--> [Kafka output-topic]
            |                                                        |
            +------------ 位移提交（也写进同一个事务） ------------+
                                  ↑
                        这一段是原子的 ✅

   [Kafka input-topic] --poll--> [处理] --JDBC insert--> [MySQL]   ← 无法纳入事务 ❌
                                        --HTTP--> [下游服务]        ← 无法纳入事务 ❌
```

> [!note] 结论性的三句话
> 1. Kafka 事务提供的是 **Kafka 集群内多分区、多 topic 的原子写**，外加把消费位移捆绑进这个原子写。
> 2. 跨集群（多 Kafka 集群之间）默认**不保证**原子性。
> 3. 只要外部系统参与，就必须在该系统上做幂等（唯一键 / 状态机 / 版本号），否则重复一定会出现。

---

## 二、幂等生产者：事务的地基

事务能"回滚"，前提是**同一条消息不会因为重试而在日志里出现两次**。这正是幂等生产者解决的。

### 2.1 PID + epoch + sequence number

幂等生产者给每条消息打上三元组：

| 元素 | 作用域 | 说明 |
| --- | --- | --- |
| **PID**（Producer ID） | 由 broker 分配的全局唯一数字 | 生产者第一次发消息时通过 `InitProducerId` 获取 |
| **epoch**（生产者纪元） | 与 PID 绑定 | 每次用同一个 `transactional.id` 重新初始化时递增，用来"作废"旧实例 |
| **sequence number** | 每个 `<PID, TopicPartition>` 独立单调递增 | 从 0 开始，每批次 +1，用于 broker 侧判重与判序 |

broker 端为每个 `<PID, 分区>` 维护一份 `ProducerState`：

```text
ProducerStateManager (每个分区一份)
  producerId=1001, epoch=3
  lastSequence=7   ← 已接收的最大 sequence
  recentBatches = [ {seq:3..4}, {seq:5..6}, {seq:7..7} ]   ← 最近 5 个批次的 sequence 区间
```

收到一个批次时按 sequence 判断：

| 收到的 sequence | broker 行为 |
| --- | --- |
| 恰为 `lastSequence + 1` | 正常追加，更新 `lastSequence` |
| 落在 `recentBatches` 已记录区间内 | **判定为重复，丢弃并返回成功**（这就是去重） |
| 大于 `lastSequence + 1` | 出现空洞 → `OutOfOrderSequenceException`（生产者致命错误） |
| 小于已记录范围（超出去重窗口） | `DuplicateSequenceException` / `OutOfOrderSequenceException`，窗口外的历史无法判定 |

> [!warning] 去重窗口不是无限的
> broker 只为每个 `<PID, 分区>` 保留**最近若干个批次**的 sequence（实践上约为 5 个批次的窗口）。这意味着幂等只对"短时间内的重试"有效。如果一批消息在缓冲区滞留很久、或者生产者长时间停顿后重发，就可能落到窗口外。

### 2.2 `enable.idempotence` 的含义与默认

| 项 | 说明 |
| --- | --- |
| 参数名 | `enable.idempotence` |
| 默认值 | **3.0 起默认 `true`**（KIP-679）；2.8 及以前默认 `false` |
| 开启后的强制项 | `acks=all`、`retries>0`（默认为 `Integer.MAX_VALUE`）、`max.in.flight.requests.per.connection <= 5` |
| 冲突行为 | **显式**写 `enable.idempotence=true` 同时把 `acks` 设成 `1`/`0`，客户端会直接抛 `ConfigException`；只写了冲突项而没有显式声明幂等时，3.0+ 会**关闭幂等并打日志告警**（见 [KAFKA-13673](https://issues.apache.org/jira/browse/KAFKA-13673)）。不同小版本细节略有差异，以实际客户端版本为准 |

> [!tip] 实践建议
> 不要"顺着默认"赌它开着。生产配置里**显式写** `enable.idempotence=true` + `acks=all`，让配置评审一眼能看出来。如果你的业务真的只需要低延迟、允许丢，那也**显式写** `acks=1` 并接受幂等被自动关闭，而不是含糊地留空。

### 2.3 为什么 `max.in.flight.requests.per.connection <= 5`

`max.in.flight.requests.per.connection` 是**同一个 broker 连接上未收到响应的请求数上限**，默认 5。

- **没有幂等时**：如果 `max.in.flight > 1` 且第一批失败、第二批成功，生产者重试第一批 → broker 上写入顺序变成 `batch2, batch1`，**乱序**。所以老版本要"重试且有序"就得把 in-flight 压到 1，吞吐惨不忍睹。
- **有幂等时**：`sequence number` 让 broker 能识别乱序。broker 允许最多 5 个 in-flight 批次在途，若其中某个批次失败，broker 会**拒绝后续批次直到空洞被填上**（`OutOfOrderSequenceException` 或直接拒绝），从而保证分区内最终顺序与发送顺序一致。
- **为什么是 5**：5 是"乱序容忍度"和"吞吐"的折中。超过 5 时，失败批次重排需要回溯的空间变大，broker 端的状态跟踪与生产者的缓冲重排复杂度上升，收益递减。这个 5 是**硬上限**，不是"建议值"。

> [!note] 幂等只保证"单分区、单会话内不重复"
> - **单分区**：幂等的 sequence 是 per-partition 的，跨分区没有全局顺序，也没有跨分区去重。
> - **单会话**：PID 是会话级的。生产者进程重启 → 新 PID → broker 认为是"新生产者"，**之前的去重状态与它无关**。所以"进程崩溃后重启再发一遍"这件事，幂等生产者管不了，必须靠**事务**（稳定的 `transactional.id` 让重启后仍是同一个逻辑生产者，且 epoch 会递增）。

### 2.4 幂等 vs 事务：能力边界对比

| 能力 | 幂等生产者 | 事务 |
| --- | --- | --- |
| 单分区内重试不重复 | ✅ | ✅ |
| 生产者重启后不重复 | ❌（PID 变了） | ✅（`transactional.id` 稳定 + epoch 递增） |
| 一次 `send` 落多个分区，要么全成要么全败 | ❌ | ✅ |
| 把消费位移和输出记录绑定成原子操作 | ❌ | ✅ |
| 额外依赖 | 无 | Transaction Coordinator + `__transaction_state` |
| 吞吐/延迟代价 | 很小 | 明显（两阶段提交 + marker 写放大） |

---

## 三、事务的整体架构

### 3.1 Transaction Coordinator

Transaction Coordinator 不是一个独立进程，而是 **broker 上的一种角色**：当某个 broker 成为 `__transaction_state` 内部 topic 某个分区的 leader 时，它就承担该分区的协调者职责。

```text
Producer --FindCoordinator(key=transactional.id, keyType=1)--> 任意 Broker
                                                                  |
                                        返回: 该 transactional.id 对应的 Coordinator
                                                                  |
Producer <----------- InitProducerId / AddPartitionsToTxn / EndTxn ----------> Transaction Coordinator
                                                                  |
                                                     读写 __transaction_state
```

- 定位方式：对 `transactional.id` 做哈希 → 映射到 `__transaction_state` 的某个分区 → 该分区的 leader 就是 Coordinator。
- Coordinator 的职责：分配 PID/epoch、登记事务涉及的分区、登记要提交位移的消费组、决定提交或回滚、向各分区 leader 下发 marker、把最终状态落盘。

### 3.2 `__transaction_state` topic

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `transaction.state.log.replication.factor` | 3 | 内部 topic 副本数，通常与集群规模匹配 |
| `transaction.state.log.num.partitions` | 50 | 分区数，决定 Coordinator 的分散程度 |
| `transaction.state.log.min.isr` | 1 | 该 topic 的 min ISR（注意不要和业务 topic 的 `min.insync.replicas` 混淆） |
| `transactional.id.expiration.ms` | 604800000（7 天） | `transactional.id` 元数据多久没活动后过期清理 |
| `transaction.max.timeout.ms` | 900000（15 分钟） | broker 允许的 `transaction.timeout.ms` 上限 |

它在每个分区里持久化的核心状态：

```text
__transaction_state 的一条记录（简化）
  transactionalId : "ctp-tx-01"
  producerId      : 1001
  producerEpoch   : 7          ← fencing 的核心
  state           : Ongoing / PrepareCommit / PrepareAbort / CompleteCommit / CompleteAbort / Empty / Dead
  partitions      : [out-topic-0, out-topic-1]     ← 事务写到了哪些分区
  groupMetadata   : {groupId: "ctp-group", generation: 42, memberId: ...}  ← 要提交位移的消费组
  timeoutMs       : 60000
```

### 3.3 `transactional.id`：作用与 fencing

`transactional.id` 是**业务语义上的"生产者身份"**，它有两条硬要求：

| 要求 | 原因 |
| --- | --- |
| **稳定**：同一份逻辑任务重启后必须用同一个 `transactional.id` | 否则 Coordinator 无法把"重启前的未完成事务"和"重启后的新实例"关联起来 |
| **唯一**：同一时刻只能有一个实例使用它 | Coordinator 通过递增 epoch 来强制这一点 |

**fencing 机制**：epoch 是"投票权"。Coordinator 每次收到 `InitProducerId(transactional.id)`，就把该 `transactional.id` 的 epoch +1（首次使用则分配新 PID）。旧实例手里的 epoch 立即作废。

### 3.4 僵尸生产者场景（两个实例同 `transactional.id`）

这是面试最爱问的场景。假设部署脚本出问题，起了两个实例：

```text
t0: 实例A initTransactions()  → PID=1001, epoch=3   （在写入过程中）
t1: 实例B 也配了同一个 transactional.id，启动并 initTransactions()
                              → Coordinator 把 epoch 抬到 4，返回 PID=1001, epoch=4
t2: 实例A 继续 send()，请求里带 epoch=3
    → broker 侧 ProducerState 校验 epoch 不匹配 → 返回 INVALID_PRODUCER_EPOCH / PRODUCER_FENCED
    → 实例A 收到 ProducerFencedException（致命，不可重试）
t3: 实例A 必须立刻 close()，不能再尝试任何事务操作
t4: 实例B 带着 epoch=4 继续工作，且 Coordinator 会把实例A 遗留的 Ongoing 事务按超时/接管逻辑处理
```

> [!warning] 两个容易踩的点
> 1. `ProducerFencedException`、`OutOfOrderSequenceException`、`AuthorizationException` 都是**致命异常**，正确做法是：捕获 → 打日志 → `producer.close()` → 让进程退出（交给编排系统重启），**不要** `abortTransaction()` 后继续循环。
> 2. fencing 不只发生在 Coordinator。每个分区 leader 的 `ProducerStateManager` 也会校验 `(PID, epoch)`；即使 Coordinator 层面漏了，追加日志这一步也会拒绝旧 epoch 的写入。这是双重保险。

---

## 四、事务流程逐步拆解

### 4.1 `initTransactions()`

```java
producer.initTransactions();   // 阻塞，内部就是一次 InitProducerId 请求
```

做的事情：

1. 向任意 broker 发 `FindCoordinator(keyType=transaction, key=transactional.id)`，拿到 Transaction Coordinator。
2. 发 `InitProducerId(transactional.id, transaction.timeout.ms)`。
3. Coordinator 分配或复用 PID，**递增 epoch**，把 `(transactionalId → producerId, epoch)` 持久化到 `__transaction_state`。
4. 如果该 `transactional.id` 存在未完成的旧事务，Coordinator 会先把它按状态推进（提交或回滚）—— 这是"重启后不会卡住"的关键。

> [!note] `initTransactions()` 必须在任何 `send()` 之前调用，且每个生产者实例只能调一次。重复调用会抛 `IllegalStateException`。

### 4.2 `beginTransaction()`

**这是一个纯本地操作**，不产生任何网络请求。它只是把生产者内部状态从 `READY` 切到 `IN_TRANSACTION`，之后所有 `send()` 产生的批次都会被打上 `transactional` 标志。

### 4.3 `send()`

第一次向某个分区发送时，生产者会**懒注册**这个分区：

```text
Producer --AddPartitionsToTxn(transactionalId, producerId, epoch, [out-topic-0])--> Coordinator
Coordinator: 把 out-topic-0 追加到该事务的 partition 列表，持久化到 __transaction_state
Producer <------------------------ AddPartitionsToTxn Response (成功) --------------
Producer --ProduceRequest(batch with transactional flag)--> out-topic-0 的 leader
```

分区 leader 把批次追加进日志，但该批次带上 `isTransactional=true` 与 `lastOffsetOfTransaction` 等字段。**`read_committed` 的消费者此时看不到它**（因为事务未结束，它位于 LSO 之上）。

### 4.4 `sendOffsetsToTransaction()`：把位移纳入事务

这是 exactly-once 的灵魂所在。调用签名（现代客户端）：

```java
producer.sendOffsetsToTransaction(
        Map<TopicPartition, OffsetAndMetadata> offsets,
        ConsumerGroupMetadata groupMetadata);
```

内部两步：

```text
1) Producer --AddOffsetsToTxn(transactionalId, pid, epoch, groupId)--> Coordinator
   Coordinator 找到 __consumer_offsets 中该 group 对应的分区，把它登记进事务的分区列表

2) Producer --TxnOffsetCommit(groupId, generation, memberId, offsets)--> 该 group 的 GroupCoordinator
   GroupCoordinator 把位移写进 __consumer_offsets，但标记为"挂起（pending）"，
   只有等事务 COMMIT 之后才对外可见
```

> [!tip] 为什么要传 `ConsumerGroupMetadata`
> KIP-447（2.5+）引入。早期版本只传 `groupId`，导致"同一 group 里有两个存活消费者"时，GroupCoordinator 无法判断该位移属于哪一代（generation），僵尸消费者可能用旧 generation 提交位移造成数据错乱。带上 `ConsumerGroupMetadata`（含 `groupId`/`generation`/`memberId`/`groupInstanceId`）后，GroupCoordinator 能校验 generation，把僵尸消费者的位移提交直接拒绝。**用 2.5 以上的客户端，务必用两参数版本。**

### 4.5 `commitTransaction()` / `abortTransaction()`

```text
commitTransaction():
  Producer --EndTxn(commit=true)--> Coordinator
  Coordinator: 状态 Empty/Ongoing → PrepareCommit 并持久化
               （这一步落盘成功 = 事务已经"决定提交"，不可撤销）
  对事务涉及的每个分区 leader 发 WriteTxnMarkers(COMMIT)
  每个 leader 在该分区日志末尾写入一个 COMMIT 控制批次（control batch / transaction marker）
  所有 marker 写成功后 → 状态 → CompleteCommit，持久化
  Producer 收到成功响应

abortTransaction():
  完全对称：PREPARE_ABORT → WriteTxnMarkers(ABORT) → ABORT marker → COMPLETE_ABORT
  注意：已写入的**数据批次不会被删除**，只是被 ABORT marker 标记为"逻辑上不存在"
```

### 4.6 两阶段提交的本质

| 阶段 | 动作 | 持久化点 |
| --- | --- | --- |
| 阶段一（准备） | 收集所有参与者（输出分区 + `__consumer_offsets` 分区），全部登记成功 | Coordinator 写入 `PrepareCommit` / `PrepareAbort` |
| **提交点** | Coordinator 的 `PrepareCommit` 落盘 | 这一刻事务**已决定提交**，之后 Coordinator 崩溃重启也会继续提交 |
| 阶段二（执行） | 向各分区 leader 写 marker（`WriteTxnMarkers`） | 每个分区的 COMMIT/ABORT 控制批次 |
| 收尾 | Coordinator 写 `CompleteCommit` / `CompleteAbort`，清理事务元数据 | `__transaction_state` |

> [!note] 事务标记（control batch）是什么
> 它是**写在业务分区日志里的一种特殊批次**，不占用消费者可见的数据 offset（消费者读不到它的内容），但它的存在告诉所有读了这段日志的人："在这条 marker 之前、属于该 PID 的那些事务批次，是提交还是回滚"。消费者正是靠扫描 marker 来维护"哪些 offset 之前的记录已经确定状态"这一判断，从而算出 LSO。

### 4.7 时序总览

```text
Producer                TransactionCoordinator          Partition Leader        GroupCoordinator
   |                            |                            |                       |
   |--InitProducerId----------->| 分配PID, epoch+1           |                       |
   |<--(pid=1001, epoch=4)------|                            |                       |
   |                            |                            |                       |
   |--beginTransaction()  【本地】                            |                       |
   |                            |                            |                       |
   |--AddPartitionsToTxn------->| 登记 out-topic-0           |                       |
   |<--OK-----------------------|                            |                       |
   |--Produce(transactional)---------------------------------->| 追加进日志（不可见）   |
   |<--ACK-----------------------------------------------------|                       |
   |                            |                            |                       |
   |--AddOffsetsToTxn---------->| 登记 __consumer_offsets-N  |                       |
   |<--OK-----------------------|                            |                       |
   |--TxnOffsetCommit(offsets, groupMetadata)---------------------------------------->| 位移挂起
   |<--OK------------------------------------------------------------------------------|
   |                            |                            |                       |
   |--EndTxn(commit=true)------>| 持久化 PrepareCommit        |                       |
   |                            |---WriteTxnMarkers(COMMIT)-->| 写入 COMMIT 控制批次   |
   |                            |<--OK------------------------|                       |
   |                            | 持久化 CompleteCommit       |                       |
   |<--OK-----------------------|                            |                       |
```

---

## 五、关键参数一览

| 参数 | 位置 | 默认值 | 含义与调优要点 |
| --- | --- | --- | --- |
| `transactional.id` | Producer | 无（null） | 稳定唯一的逻辑生产者身份。**必须由业务显式提供**，通常用 `${app}-${partitionIndex}` 这类带分片的写法 |
| `transaction.timeout.ms` | Producer | 60000（1 分钟） | 事务"多久没进展就算超时"。**必须 <= broker 的 `transaction.max.timeout.ms`**，否则 `initTransactions()` 直接报 `InvalidTxnTimeoutException` |
| `transaction.max.timeout.ms` | Broker | 900000（15 分钟） | broker 侧上限，防止客户端配置一个超长事务把 LSO 长期钉住 |
| `enable.idempotence` | Producer | 3.0 起 `true` | 事务的前提，事务开启时隐式生效 |
| `acks` | Producer | 3.0 起 `all` | 事务下必须 `all` |
| `max.in.flight.requests.per.connection` | Producer | 5 | 幂等/事务下必须 `<= 5` |
| `isolation.level` | Consumer | `read_uncommitted` | `read_committed` 才会过滤未提交/已回滚的记录 |
| `enable.auto.commit` | Consumer | `true` | 事务模式下**必须设为 `false`**，位移由 `sendOffsetsToTransaction` 管理 |
| `max.poll.interval.ms` | Consumer | 300000（5 分钟） | 必须**大于**单次事务的最长耗时，否则事务进行中触发 rebalance |
| `transaction.state.log.*` | Broker | 见 3.2 | 内部 topic 配置，创建后改分区数非常麻烦，集群规划时一次定好 |

> [!warning] 三个最常见的配置事故
> 1. `transaction.timeout.ms` 大于 broker 的 `transaction.max.timeout.ms` → 启动即失败。
> 2. `max.poll.interval.ms` 小于"poll 到 commit 的耗时" → 事务还没提交，消费者已被踢出组，`sendOffsetsToTransaction` 抛 `CommitFailedException` 或 `RebalanceInProgressException`。
> 3. 忘记 `enable.auto.commit=false` → 自动提交的位移和事务里的位移互相打架，出现"消息被跳过"的诡异现象。

---

## 六、LSO 与 `read_committed`：面试重灾区

### 6.1 `read_committed` 到底过滤了什么

设 `isolation.level=read_committed`，消费者 fetch 时会做两件过滤：

| 过滤对象 | 说明 |
| --- | --- |
| **已回滚（aborted）的记录** | 事务被 `abortTransaction` 后，数据批次仍在日志里，但消费者读到对应的 ABORT marker 后会把它们全部跳过，**不会返回给应用** |
| **未结束（open transaction）的记录** | 事务还在 `Ongoing`，状态未定。消费者**直接不读**，即读取上界被 `LSO` 卡住 |

对比 `read_uncommitted`：**不做任何过滤**，日志里有什么就返回什么，包括已回滚的记录和未提交的记录。这也是为什么"用 `read_uncommitted` 读一张有事务写入的 topic，会看到一些最终并不存在的数据"。

### 6.2 LSO（Last Stable Offset）的定义

> **LSO = 分区日志中"最早的、仍未结束的事务"的第一条记录的 offset。**
> 换句话说：**offset < LSO 的所有事务都已经有了最终结论（committed 或 aborted）**，消费者可以放心读到这个位置为止。

```text
offset:  0    1    2    3    4    5    6    7    8    9   10   11
        [c ][c ][ T1 ][ T1 ][c ][ T2 ][ T2 ][ T2 ][c ][c ][ T3 ]
                   ↑                              ↑
                   T1 已提交                       T2 仍在 Ongoing
                                                  ↑
                                                  LSO = 5

read_committed 消费者最大可读到 offset 4。
offset 5~7 属于 T2，状态未定 → 不可读。
offset 8、9 虽然已提交，但位于 LSO 之后 → 同样不可读（必须保证 offset 递增语义）。
```

注意最后一点：**offset 8、9 已经提交了，但读不到**。因为消费者必须按 offset 顺序推进，不能"跳过 5~7 直接给 8、9"，否则一旦 T2 最终 abort，offset 顺序语义就崩了。这就是**队头阻塞（head-of-line blocking）**的直接来源。

### 6.3 为什么 `read_committed` 会变慢

| 慢在哪里 | 机制 |
| --- | --- |
| **LSO 被钉住** | 只要有一个长事务（或卡住的事务）的 `Ongoing` 状态存在，LSO 就停在它的第一条记录上，之后所有已提交数据都读不到 |
| **延迟被事务时长拉长** | 事务从 `beginTransaction` 到 `commitTransaction` 的耗时，直接变成下游 `read_committed` 消费者的**最小可见延迟**。事务 30 秒，下游平均就多 30 秒 |
| **broker 端要多做判断** | 需要维护每个分区的 LSO，fetch 时要按 LSO 截断；还要跟踪 aborted 事务的 offset 区间来过滤 |
| **客户端要缓冲** | 消费者在 LSO 之前仍需按批次解码并跳过 aborted 区间，CPU 与内存开销略高于 `read_uncommitted` |
| **超时事务的连锁反应** | 某个生产者挂了、事务一直不提交也不 abort → 直到 `transaction.timeout.ms` 到期 Coordinator 才 abort → 这段时间 LSO 一直不动，**整条链路的延迟都被拖住** |

> [!question] 面试口径：`read_committed` 为什么慢？
> 因为 `read_committed` 的读取上界是 **LSO**，而 LSO 等于"最早未结束事务的第一条记录 offset"。任何一个长事务或卡住的事务都会把 LSO 钉在原地，导致它后面**已经提交**的数据也不可见 —— 也就是队头阻塞。所以事务的持续时间直接决定了下游消费者的可见延迟；`transaction.timeout.ms` 实际上是这个阻塞的兜底上限，而不是一个"随便设大点"的参数。

### 6.4 工程上的应对

| 手段 | 说明 |
| --- | --- |
| 事务尽量短 | 一次事务只处理一批消息，不要攒几分钟。`max.poll.records` 调小反而更利于缩短事务 |
| `transaction.timeout.ms` 与业务耗时对齐 | 设太小 → 正常事务被误判超时 abort；设太大 → 卡住的事务会长时间钉住 LSO |
| 关键链路与事务链路隔离 | 需要低延迟的消费方，尽量读非事务 topic，别和事务 topic 混在一起 |
| 监控 LSO 滞后 | 关注 `LastStableOffsetLag` 相关的分区指标，或直接从消费延迟曲线上看"台阶状"停顿 |

---

## 七、事务的边界与限制

| 限制 | 具体表现 | 影响与规避 |
| --- | --- | --- |
| **只支持 Kafka topic 之间** | 无法把数据库、HTTP、Redis 纳入原子提交 | 外部系统靠业务幂等兜底（见第九节） |
| **不跨集群** | 两个独立 Kafka 集群之间没有分布式事务 | MirrorMaker 2 在 3.0 起通过 `exactly.once.support` 提供过有限的端到端保证，但该能力已被标记废弃并在后续版本移除；**不要把它当作跨集群 exactly-once 的方案** |
| **超时即 abort** | `transaction.timeout.ms` 内没有完成，Coordinator 主动 abort | 大数据量事务要么分批，要么调大超时并接受 LSO 滞后 |
| **长事务拖慢 `read_committed` 消费者** | 见第六节 | 控制事务粒度 |
| **`transactional.id` 必须稳定且唯一** | 不稳定 → 重启后旧事务无法收敛；不唯一 → 频繁 fencing | 用确定性的命名规则，例如 `订单同步-job-${shardId}` |
| **单生产者实例串行处理事务** | 一个 `KafkaProducer` 同一时刻只能有一个进行中的事务 | 要并行就多实例/多 `transactional.id` 分片 |
| **消费者必须禁用自动提交** | `enable.auto.commit=true` 与事务位移冲突 | 强制 `false` |
| **事务内有 poll 禁令** | 事务进行中再调用 `poll()` 会抛 `IllegalStateException` | 每轮"poll → 处理 → send → 提交位移 → commit"闭环 |
| **性能代价** | 每个分区都要写 marker，跨多个分区时是多次网络往返 + 额外 fsync | 事务涉及的分区越少越好 |

---

## 八、完整 Java 示例：consume-transform-produce

下面是一个可直接对照修改的骨架，覆盖配置、主循环、致命异常处理与重试。

### 8.1 消费者配置

```java
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.OffsetAndMetadata;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.time.Duration;
import java.util.*;

Properties consumerProps = new Properties();
consumerProps.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "broker1:9092,broker2:9092,broker3:9092");
consumerProps.put(ConsumerConfig.GROUP_ID_CONFIG, "ctp-group");
consumerProps.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
consumerProps.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());

// ① 读已提交：必须，否则会读到事务回滚掉的数据
consumerProps.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
// ② 关闭自动提交：位移由 sendOffsetsToTransaction 统一管理
consumerProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
// ③ 一批别拉太多，控制单次事务时长（也就能控制 LSO 被钉住的时间）
consumerProps.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, "200");
// ④ 必须显著大于"单次事务最长耗时"，否则事务中触发 rebalance
consumerProps.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, "300000");
consumerProps.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
```

### 8.2 生产者配置

```java
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;

Properties producerProps = new Properties();
producerProps.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "broker1:9092,broker2:9092,broker3:9092");

// transactional.id 必须稳定且唯一；按分片编号可以并行多个实例
producerProps.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "ctp-tx-shard-0");
producerProps.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
producerProps.put(ProducerConfig.ACKS_CONFIG, "all");
producerProps.put(ProducerConfig.RETRIES_CONFIG, Integer.toString(Integer.MAX_VALUE));
producerProps.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, "5");

// 必须 <= broker 的 transaction.max.timeout.ms（默认 900000）
producerProps.put(ProducerConfig.TRANSACTION_TIMEOUT_CONFIG, "60000");
// delivery.timeout.ms 必须 >= linger.ms + request.timeout.ms
producerProps.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, "120000");
producerProps.put(ProducerConfig.LINGER_MS_CONFIG, "10");

producerProps.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
producerProps.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
```

> [!note] `transactional.id` 的分片命名
> 如果同一个应用要起 N 个并行实例提高吞吐，就给每个实例一个不同的 `transactional.id`（如 `ctp-tx-shard-${i}`）。**不要**为了"高可用"让两个实例共用同一个 id —— 那不是高可用，那是互相 fencing 的故障源。高可用应该靠编排系统保证同一时刻只有一个实例在跑。

### 8.3 主循环

```java
import org.apache.kafka.common.KafkaException;
import org.apache.kafka.common.errors.AuthorizationException;
import org.apache.kafka.common.errors.OutOfOrderSequenceException;
import org.apache.kafka.common.errors.ProducerFencedException;
import org.apache.kafka.common.errors.TimeoutException;

KafkaProducer<String, String> producer = new KafkaProducer<>(producerProps);
KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);

// 必须在任何 send 之前调用；内部会做 Coordinator 定位 + PID/epoch 分配
producer.initTransactions();
consumer.subscribe(Collections.singletonList("input-topic"));

final int MAX_TX_RETRY = 3;

try {
    while (running) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
        if (records.isEmpty()) {
            continue;   // 空轮询不产生事务，避免无意义地写 marker
        }

        int attempt = 0;
        while (true) {
            producer.beginTransaction();          // 本地状态切换，无网络请求
            try {
                // ① 处理并写出：所有 send 都在事务内，未提交前 read_committed 不可见
                for (ConsumerRecord<String, String> record : records) {
                    String value = transform(record.value());
                    producer.send(new ProducerRecord<>("output-topic", record.key(), value));
                }

                // ② 位移也纳入同一个事务：输出记录 + 位移，原子提交
                Map<TopicPartition, OffsetAndMetadata> offsetsToCommit = new HashMap<>();
                for (TopicPartition tp : records.partitions()) {
                    List<ConsumerRecord<String, String>> partitionRecords = records.records(tp);
                    long nextOffset = partitionRecords.get(partitionRecords.size() - 1).offset() + 1;
                    offsetsToCommit.put(tp, new OffsetAndMetadata(nextOffset));
                }
                producer.sendOffsetsToTransaction(offsetsToCommit, consumer.groupMetadata());

                // ③ 提交：两阶段提交，返回成功即表示 marker 已写入所有相关分区
                producer.commitTransaction();
                break;

            } catch (TimeoutException e) {
                // 可重试：事务尚未到达提交点，回滚后重放这一批
                producer.abortTransaction();
                if (++attempt >= MAX_TX_RETRY) {
                    throw e;                      // 交给上层 / 死信处理
                }
                log.warn("transaction timeout, retry {}/{}", attempt, MAX_TX_RETRY, e);
            } catch (ProducerFencedException | OutOfOrderSequenceException | AuthorizationException e) {
                // 致命：本实例已被同 transactional.id 的新实例踢掉，或权限/序列不可恢复
                // 绝不能继续用这个 producer，也不能 abortTransaction 后继续循环
                throw e;
            } catch (KafkaException e) {
                // 其余 Kafka 异常：大概率是 broker 侧瞬时问题，回滚后可重试
                producer.abortTransaction();
                if (++attempt >= MAX_TX_RETRY) {
                    throw e;
                }
                log.warn("transaction aborted, retry {}/{}", attempt, MAX_TX_RETRY, e);
            }
        }
    }
} catch (ProducerFencedException | OutOfOrderSequenceException | AuthorizationException e) {
    // 致命异常：记录后让进程退出，由编排系统重启（重启后 epoch 会重新分配）
    log.error("fatal transaction error, shutting down", e);
    throw e;
} finally {
    try {
        producer.close(Duration.ofSeconds(10));
    } catch (Exception e) {
        log.warn("producer close failed", e);
    }
    consumer.close(Duration.ofSeconds(10));
}
```

### 8.4 几个必须注意的细节

| 细节 | 原因 |
| --- | --- |
| `consumer.poll()` **绝不能**出现在 `beginTransaction()` 和 `commitTransaction()` 之间 | 消费者在事务进行中 poll 会抛 `IllegalStateException`（客户端保护机制） |
| 每个批次重试时用**同一份 `records`** | 重试期间不要重新 poll，否则位移与数据不一致 |
| `abortTransaction()` 之后可以继续用同一个 producer | `abort` 是正常回滚路径，不是致命错误；致命的是 `ProducerFencedException` 系列 |
| `close()` 要给足够的超时 | 关生产者时可能需要把未完成的事务收敛掉 |
| 处理逻辑要**幂等或可重放** | 因为重试路径会把同一批 `records` 重新处理一遍，第二次处理时外部副作用（比如已写进 MySQL 的那条）已经生效了 —— 这就是为什么外部系统依然需要幂等表 |

> [!example] 一句话理解这套代码
> `beginTransaction` 开票 → `send` 记账 → `sendOffsetsToTransaction` 把"我读到哪儿了"也记进同一张票 → `commitTransaction` 一次性核销。要么全生效，要么全作废重来。

---

## 九、外部系统的兜底：幂等表 / 去重表

只要链路里有外部系统，Kafka 事务就帮不上忙。标准做法是**消费端幂等**，三条路线：

### 9.1 方案对比

| 方案 | 机制 | 优点 | 缺点 | 适用 |
| --- | --- | --- | --- | --- |
| **唯一索引 / 去重表** | 用消息的业务唯一键（订单号 + 事件类型）建唯一索引，重复插入时捕获 `DuplicateKeyException` 并当作成功 | 实现简单、数据库层强保证 | 每条消息一次写放大；需要一张额外的表或索引 | 写库场景，最常用 |
| **状态机** | 消息驱动的状态迁移只在"当前状态 → 目标状态"合法时执行（如 `待支付 → 已支付`），重复消息因状态不匹配被忽略 | 天然幂等，语义直观 | 需要设计完整的状态图；非法迁移要明确丢弃还是告警 | 订单、工单、审批流 |
| **版本号 / CAS** | 记录带 `version`，更新时 `update ... set version = version + 1 where id = ? and version = ?`，影响行数为 0 即视为已处理 | 无额外表，利用已有行 | 需要消息里携带版本；只适用于"更新已存在实体" | 对账、快照同步 |

### 9.2 去重表的最小实现

```sql
CREATE TABLE msg_dedup (
  biz_key    VARCHAR(128) NOT NULL,   -- 例如 orderId + ':' + eventType
  created_at DATETIME     NOT NULL,
  PRIMARY KEY (biz_key)               -- 唯一约束就是幂等的保证
) ENGINE = InnoDB;
```

```java
@Transactional
public void handle(String bizKey, Runnable businessLogic) {
    try {
        dedupMapper.insert(bizKey);      // 唯一键冲突 → 说明这条消息处理过了
    } catch (DuplicateKeyException e) {
        return;                          // 直接返回成功，不要抛给上层触发重试
    }
    businessLogic.run();                 // 与去重记录在同一个本地事务里
}
```

> [!warning] 去重表的两个坑
> 1. **"插入去重记录"和"执行业务逻辑"必须在同一个本地数据库事务里**，否则插入成功、业务失败会永久丢消息。
> 2. **去重表要能清理**。长期保留会无限增长，通常按时间分区，保留"大于 Kafka 最大重放窗口（`retention.ms` + 消费延迟上限）"即可。清理太早会重新出现重复。

### 9.3 为什么外部系统仍需它 —— 一句话回答

因为 Kafka 事务的原子性边界**止于 Kafka 的日志**。`commitTransaction()` 成功后、外部系统的写入还没有发生（或者已经发生但结果未知），这两步之间没有任何共同的提交点，进程崩溃、网络超时都会造成"Kafka 已提交但外部未写入"或"外部已写入但 Kafka 未提交"的错位。唯一可靠的解法是让外部写入本身可重放 —— 也就是幂等。

---

## 十、与 Flink / Spring Kafka 的事务集成

### 10.1 Spring Kafka

| 组件 | 作用 |
| --- | --- |
| `KafkaTransactionManager` | 把 `KafkaProducer` 绑定到 Spring 的事务同步器上，`@Transactional` 方法结束即 `commitTransaction` |
| `@Transactional` + `KafkaTemplate` | 声明式事务，`KafkaTemplate` 的 send 自动加入当前事务 |
| `ChainedTransactionManager` | 历史上用来"串联"Kafka 事务与 JDBC 事务，但它**不是真正的分布式事务**：按相反顺序提交、失败只能尽力回滚，且已在 Spring Kafka 2.7+ 被废弃、在新版本中移除 |
| `KafkaTransactionManager` + 监听容器 | 配置 `setTransactionManager` 后，容器会在事务里处理批次，并在事务中提交位移（等价于手写 `sendOffsetsToTransaction`） |

> [!warning] 关于 `ChainedTransactionManager`
> 它给人的"跨 Kafka + DB 事务"错觉非常危险。它的语义是：按注册顺序的**逆序**依次提交，任何一步失败只能对已经提交的部分"尽力回滚"，本质上仍是最终一致。**不要**基于它做资金类业务。正确做法是 Kafka 事务 + 业务侧幂等表。

详细的容器配置、`@Transactional` 边界、错误处理器（`DefaultErrorHandler` 的 `DeadLetterPublishingRecoverer`）写法见 [[9-SpringBoot实战]]。

### 10.2 Flink

Flink 的 Kafka connector 提供了两阶段提交的实现（`FlinkKafkaProducer` 的 `Semantic.EXACTLY_ONCE`），思路与 Kafka 原生事务一致：

1. 每个 checkpoint 周期开始时 `beginTransaction()`。
2. 数据在事务内写入下游 topic。
3. checkpoint 完成（状态在后端持久化成功）时 `commitTransaction()`。
4. 若 checkpoint 失败或作业重启，则 `abortTransaction()` 并从上一次成功的 checkpoint 重放。

关键点：**两阶段提交里的"准备阶段"是 Flink 的 checkpoint**，只有 checkpoint 全局成功才提交 Kafka 事务。因此：

| 注意项 | 说明 |
| --- | --- |
| `transaction.timeout.ms` 要大于 checkpoint 间隔 + 最大恢复时间 | 否则事务会在 checkpoint 完成前超时被 abort，作业反复失败 |
| 事务会跨越整个 checkpoint 周期 | 下游 `read_committed` 消费者的可见延迟**至少是一个 checkpoint 间隔**，这是 Flink EOS 的固有代价 |
| 依赖 Flink 的状态后端 | 状态后端不可靠会直接破坏 EOS 语义 |

---

## 十一、必答问题

> [!question] Q1：Kafka 如何实现 exactly-once？
> 三个机制叠加：
> 1. **幂等生产者**保证单分区单会话内重试不产生重复（PID + epoch + per-partition sequence，broker 侧保留最近批次的 sequence 做去重）。
> 2. **事务**通过稳定的 `transactional.id` 把身份延续到进程重启之后（epoch 递增 + fencing 踢掉旧实例），并把"写多个分区"变成原子操作。
> 3. **`sendOffsetsToTransaction` + `isolation.level=read_committed`** 把消费位移也纳入同一个事务，让"读了什么"和"写了什么"一起提交或一起回滚。
>
> 但这只在 Kafka 内部闭环成立；有外部系统参与时必须靠业务幂等。

> [!question] Q2：Kafka 事务消息能保证什么？
> - ✅ 多分区、多 topic 的写入**原子性**：全部提交或全部回滚。
> - ✅ 消费位移与输出记录的**原子提交**（consume-transform-produce 闭环不丢不重）。
> - ✅ 同一 `transactional.id` 的**僵尸实例隔离**（fencing，旧实例收到 `ProducerFencedException`）。
> - ✅ `read_committed` 消费者看不到已回滚的记录和未结束事务的记录。
> - ❌ 不保证跨集群原子性。
> - ❌ 不保证外部系统（DB/HTTP/Redis）的原子性。
> - ❌ 不保证消息顺序跨分区，也不保证事务内数据在 LSO 之前的可见性。
> - ❌ `abortTransaction` 不会删除已写入的数据，只是逻辑标记。

> [!question] Q3：为什么 `read_committed` 会变慢？
> 因为它的读取上界是 **LSO（Last Stable Offset）**，而 LSO 是"最早未结束事务的首条记录 offset"。任何长事务都会让 LSO 停住，导致 LSO 之后**已经提交**的数据也不可见 —— 队头阻塞。因此：
> - 事务的持续时间直接决定下游可见延迟；
> - `transaction.timeout.ms` 是这种阻塞的兜底上限；
> - broker 端多了 LSO 维护与 aborted 区间过滤的开销，客户端多了跳过 aborted 批次的 CPU 开销；
> - 工程手段是把事务做短（减小 `max.poll.records`）、把事务链路和低延迟链路隔离、监控 LSO 滞后。

> [!question] Q4：`transactional.id` 和 `client.id` 有什么区别？
> `client.id` 只是**日志和监控上的标识**，随便写，重复也无所谓。`transactional.id` 是**业务级的生产者身份**，必须稳定且全局唯一；它决定 Coordinator 上的 PID/epoch 归属、决定 fencing 的对象、决定重启后能否收敛旧事务。两者完全不是一个层面的东西。

> [!question] Q5：事务进行到一半，Coordinator 所在的 broker 挂了会怎样？
> 事务的中间状态（`Ongoing` / `PrepareCommit` 等）都持久化在 `__transaction_state` 里。`__transaction_state` 分区会在其他副本上选出新 leader，新 Coordinator 读取该 `transactional.id` 的记录：
> - 若状态是 `Ongoing` 且未过 `transaction.timeout.ms`，继续等待生产者；
> - 若状态是 `PrepareCommit` / `PrepareAbort`，**继续完成阶段二**（补发 marker），因为提交点已经落盘；
> - 若生产者始终不再出现，超时后 Coordinator 主动 abort。
>
> 所以 Coordinator 故障不会导致"一半提交一半回滚"的中间态永久存在 —— 这正是把事务状态写进 `__transaction_state` 而不是放在内存里的意义。

---

## 相关笔记

- [[1-Kafka总览]] —— 系列索引
- [[2-生产者原理]] —— 幂等生产者、`acks`、重试与 in-flight 的细节
- [[3-消费者与Rebalance]] —— `isolation.level`、位移提交、`max.poll.interval.ms`
- [[4-日志存储与副本机制]] —— 控制批次（control batch）在日志中的形态、`__transaction_state` 的副本
- [[6-运维与集群调优]] —— 事务相关指标监控、`transaction.state.log.*` 的容量规划
- [[9-SpringBoot实战]] —— `KafkaTransactionManager`、`@Transactional`、错误处理器
- [[10-面试高频题]] —— 本篇面试问题的精简版
