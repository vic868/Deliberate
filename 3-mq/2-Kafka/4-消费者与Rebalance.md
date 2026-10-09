# Kafka 消费者与 Rebalance

> 本文回答四个问题：**消息是如何被"组"消费掉的**（消费模型与并行度上限）、**位移（offset）存在哪、什么时候提交**（重复消费与漏消费的根源）、**Rebalance 为什么发生、为什么危险、怎么治**（协议演进与参数取舍）、以及**消费滞后（Lag）怎么读、持续增长怎么排查**。
> 建议先看 [[2-架构与核心概念]] 建立 Topic / Partition / Replica / ISR 的概念；位移与事务的边界问题对照 [[6-事务与Exactly-Once]]；服务端存储细节见 [[5-日志存储与副本机制]]；生产端对照 [[3-生产者原理]]；Spring 落地见 [[9-SpringBoot实战]]；面试速查见 [[10-面试高频题]]。总览索引：[[1-Kafka总览]]。

## 一、消费模型：Consumer Group 与分区分配

### 1.1 唯一铁律

整个消费者体系只建立在一条约束上：

> **同一个 Consumer Group 内，一个分区在同一时刻只能被一个消费者实例消费。**

这条约束带来两个直接后果：

1. **组内是"队列语义"**——每条消息在组内只会被处理一次（进程层面，不是语义层面）。
2. **组间是"发布订阅语义"**——不同组各自持有一份独立的位移，同一份数据被多个组重复消费。

"Kafka 到底是队列还是发布订阅"这个经典问题的答案是：**取决于你有几个消费组**。一个组 → 队列（点对点，分摊）；N 个组 → 发布订阅（广播）。Kafka 不需要为此切换任何模式，这是模型的自然结果。

### 1.2 消费者与消费组关系图

```text
                        Topic: order-topic (3 partitions, 1 份日志)
        ┌─────────────────┬─────────────────┬─────────────────┐
        │   Partition 0   │   Partition 1   │   Partition 2   │
        └────────┬────────┴────────┬────────┴────────┬────────┘
                 │                 │                 │
   ┌─────────────┴─────────────────┴─────────────────┴─────────────┐
   │                  Consumer Group: order-cg                     │
   │                                                              │
   │   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐   │
   │   │ Consumer C1 │      │ Consumer C2 │      │ Consumer C3 │   │
   │   │   owns P0   │      │   owns P1   │      │   owns P2   │   │
   │   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘   │
   │          │ commit offset      │                    │          │
   │          └───────────┬────────┴────────────────────┘          │
   └──────────────────────┼────────────────────────────────────────┘
                          ▼
              __consumer_offsets (50 分区, RF=3)
              key   = groupId + topic + partition
              value = committed offset（下一条要读的位置）
```

再叠加一个组，就变成广播：

```text
   order-topic ──┬──> Consumer Group order-cg     (3 消费者, 分摊 3 个分区)
                 │
                 └──> Consumer Group bi-cg        (1 消费者, 独占 3 个分区, 各存一份位移)
```

### 1.3 并行度的硬上限

| 关系 | 结果 |
|---|---|
| 消费者数 < 分区数 | 每个消费者负责 ≥ 1 个分区，**分区是并行单元，不能拆分** |
| 消费者数 == 分区数 | 理想状态，一人一分区，吞吐上限最高 |
| 消费者数 > 分区数 | **多余的消费者分不到分区，完全空转（idle）**，仍会参与心跳与 rebalance |

推论：**消费并行度上限 = 该组订阅的所有 topic 的分区总数**。所以"消费跟不上"时，先看分区数，再加实例数；实例数超过分区数纯粹是浪费（还增加了 rebalance 成本与协调器压力）。注意单消费者可以同时消费多个分区，但它是**单线程**顺序处理这些分区的，串行度不会降低——这也是为什么"N 个消费者消费 N 个分区"和"1 个消费者消费 1 个分区"的处理速率相差不大，前者的收益来自 CPU 并行而不来自单分区吞吐。

> [!tip] 分区数是"事后很难改"的设计决策
> 分区只能增不能减（见 [[5-日志存储与副本机制]]）。增加分区会改变 key→partition 的映射（`hash(key) % 分区数` 变了），破坏**同一 key 的顺序性**。所以分区数应当按"未来 1~2 年的峰值并行度"预留，而不是按当前量。分区过多的代价见 [[7-运维与集群调优]]。

### 1.4 "一个分区只能被一个消费者消费"是怎么实现的

不是靠锁，而是靠**协调器（GroupCoordinator）+ 成员代际（Generation）**：

- 协调器为每个组维护一份成员表，重新分配时递增 `generation`；
- 消费者发心跳/提交位移时必须带上自己的 `generation`；
- 代际过期的请求会被拒绝（`ILLEGAL_GENERATION` / `REBALANCE_IN_PROGRESS`），旧消费者无法继续提交或继续消费；
- 分区归属由协调器下发的分配方案决定，不在方案里的消费者根本不会收到该分区的 fetch 结果。

这套机制是**软性的、最终一致**的：rebalance 期间存在极短的"两个消费者都认为自己拥有某分区"的窗口（eager 协议下尤甚），这正是重复消费难以完全根除的原因之一。

## 二、Offset（位移）管理

### 2.1 位移存在哪里：`__consumer_offsets`

| 项 | 说明 |
|---|---|
| 存储位置 | 内部 topic `__consumer_offsets`，本质就是一个普通 topic（key-value 日志） |
| 分区数 | 默认 `offsets.topic.num.partitions=50` |
| 副本数 | 默认 `offsets.topic.replication.factor=3` |
| 路由 | `abs(groupId.hashCode()) % 分区数`，同一组的所有位移落在同一个分区，因而由一个 coordinator 负责 |
| key | `groupId + topic + partition`（version 0/1 编码格式不同） |
| value | 已提交位移 + 元数据（如 leader epoch、提交时间戳） |
| 创建时机 | 第一个消费者提交位移时由协调器自动创建（或集群首次启用消费位移时） |
| 保留 | `offsets.retention.minutes` 默认 10080（7 天）。**组变空后**超过该时间位移被清理；清理后该组的 `auto.offset.reset` 会重新生效 |
| 手动提交 | 一般不直接写，用 `kafka-consumer-groups.sh --reset-offsets` 重置 |

定位 coordinator：

```bash
# 找某组的分区 -> 找该分区的 leader -> 那就是 coordinator
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --group order-cg --state
```

> [!warning] `__consumer_offsets` 是集群的关键路径
> 所有组的位移提交都写这个 topic，leader 落在少数 broker 上。如果它所在的 broker 磁盘抖动或 GC 停顿，现象是**全集群消费者出现 `commit-latency` 上升、`CommitFailedException`、`NOT_COORDINATOR`**。生产环境务必保证 `offsets.topic.replication.factor=3`，且不要把 50 个分区的 leader 人为堆到同一台机器上。

### 2.2 自动提交 vs 手动提交

```java
// 自动提交（默认）
props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "true");      // 默认 true
props.put(ConsumerConfig.AUTO_COMMIT_INTERVAL_MS_CONFIG, "5000"); // 默认 5000ms
```

自动提交的真实机制（很多人答错）：

- **不是后台线程定时提交**。它由 `poll()` 驱动：只有当 `poll()` 被调用、且距上次提交超过 `auto.commit.interval.ms` 时，才会在 poll 内部提交**上一次 poll 返回的位移**。
- 提交的是**已 poll 出来的位置**，而不是"已处理完成的位置"。因此自动提交 = **先提交后处理**，本质是 at-most-once，正常关闭或平衡期间会丢数据。
- 自动提交也可能发生在 rebalance 之前（`poll()` 内部检测到需要 rejoin 时先提交、再 rejoin），这会**放大重复窗口**。

| 维度 | 自动提交 | 手动提交 |
|---|---|---|
| 默认 | `true`，`auto.commit.interval.ms=5000` | 需显式 `enable.auto.commit=false` |
| 提交时机 | poll 内部按时间间隔，与业务处理无关 | 由代码决定，通常在业务处理成功后 |
| 语义 | 最好情况 at-least-once，故障时 at-most-once（丢消息） | 取决于提交位置，可做到 at-least-once |
| 优点 | 零代码，省事 | 可控、可批量、可在 rebalance 回调中兜底 |
| 适用 | 允许丢消息的指标/日志类管道 | **一切涉及数据的业务场景** |

> [!tip] 结论性建议
> 只要"丢一条消息"会让人来找你，就 `enable.auto.commit=false`，并把位移提交显式绑定到"业务处理成功"之后。自动提交的唯一优势是省代码，而它省下的代码正是你必须写的那几行。

### 2.3 `commitSync` vs `commitAsync`

| 维度 | `commitSync()` | `commitAsync()` |
|---|---|---|
| 阻塞 | 阻塞，直到提交成功或遇到不可重试异常 | 立即返回，结果通过回调异步通知 |
| 重试 | **自动重试**（可重试异常会一直重试直到 `request.timeout` 等上限） | **不重试**，失败只回调异常 |
| 吞吐 | 每批一次 RTT，批量大时影响明显 | 不阻塞消费循环 |
| 失败处理 | 抛 `CommitFailedException`（rebalance 导致代际失效）等 | 只能打日志 |
| 位移倒退风险 | 由于重试，**可能出现"旧位移覆盖新位移"**：异步提交 A 成功后在途的同步重试把更小的位移写回 | 低（不重试） |

**为什么 `commitAsync` 不重试？** 因为位移提交是"单调递增覆盖"语义，若一次提交失败（例如网络抖动）后你继续处理并提交了更大的位移，此时再重试那个**旧的、更小的**位移，就会把位移回退，造成大批重复消费。所以设计上选择"不重试，下一次提交自然覆盖"。

**工程上的标准写法**：循环内 `commitAsync`（不阻塞、失败仅记录），正常/异常退出前在 `finally` 里 `commitSync` 兜底一次。

```java
try {
    while (running.get()) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
        process(records);
        // 循环内异步提交：快，失败不阻塞
        consumer.commitAsync((offsets, ex) -> {
            if (ex != null) {
                log.warn("async commit failed, offsets={}, 下次提交会覆盖", offsets, ex);
            }
        });
    }
} finally {
    // 退出前同步提交：确保最后一次异步提交的"悬空结果"被确认
    try {
        consumer.commitSync();
    } finally {
        consumer.close(Duration.ofSeconds(30));
    }
}
```

`commitSync` 与 `commitAsync` 还有带参重载，可以只提交指定分区：

```java
Map<TopicPartition, OffsetAndMetadata> offsets = new HashMap<>();
offsets.put(new TopicPartition("order-topic", 0), new OffsetAndMetadata(record.offset() + 1));
consumer.commitSync(offsets);   // 按分区精细化提交，重复窗口更小
```

### 2.4 提交的是"下一条要消费的位置"

这是最容易搞错的一点，务必记死：

> `commit(offset)` 提交的是 **下一条要消费的位置（position）**，即"我已经处理完了 offset = X 的那条"，就提交 `X + 1`。

```text
Partition 0 log:   [0] [1] [2] [3] [4] [5] ...
                                  ▲
                          刚处理完 offset=2
提交值应为 3  ─────────────────────┘
重启后从 offset=3 开始消费，即下一条 [3]
```

对照 API：

| API | 含义 |
|---|---|
| `record.offset()` | 当前这条记录的位置 |
| `consumer.position(tp)` | 下一条将被 poll 的位置（**不是**已提交位置） |
| `consumer.committed(tp)` | 已提交的位置；无提交则返回 `null` |
| `new OffsetAndMetadata(record.offset() + 1)` | 处理完本条后应提交的值 |

> [!warning] `commitSync()` 无参版本是陷阱
> 无参 `commitSync()` / `commitAsync()` 提交的是**当前 position**，而 position 在 `poll()` 返回时就已经推进到整批记录的末尾了。如果你一次 poll 拿 500 条、处理到第 100 条时抛异常、然后在 `catch` 里调 `commitSync()`，就会把 500 条的位置全部提交掉——剩下 400 条永久丢失。**批量处理时必须自己维护"已成功处理到哪"的 map 并提交它。**

### 2.5 `auto.offset.reset`：只在"没有已提交位移"时生效

| 取值 | 语义 |
|---|---|
| `earliest` | 从该分区**最早**可用位移开始（受 `log.retention` 影响，最早的段可能已被删除） |
| `latest` | 从**当前 LEO（日志末尾）**开始，只消费新写入的数据 |
| `none` | 不自动重置，抛出 `NoOffsetForPartitionException`，由调用方捕获后自行 `seek` |

**默认值是 `latest`**（`ConsumerConfig.AUTO_OFFSET_RESET_DEFAULT = "latest"`）。

> [!question] 面试高频陷阱：设了 `earliest` 为什么还是收不到历史消息？
> 因为 `auto.offset.reset` **只在"该组在该分区没有已提交位移"时生效**。判定顺序是：
> 1. 先在 `__consumer_offsets` 查该组该分区有没有已提交位移 → **有就用它，`auto.offset.reset` 完全被忽略**；
> 2. 没有已提交位移时，才看 `auto.offset.reset`；
> 3. 若为 `none` 则抛异常。
>
> 所以"想从头消费历史数据"必须满足条件之一：**换一个全新的 `group.id`**，或者**用 `kafka-consumer-groups.sh --reset-offsets --to-earliest` 把位移重置**（且组必须处于非活跃状态）。

相关边界：

- 位移已过期（组空了超过 `offsets.retention.minutes`，默认 7 天）→ 视同"没有已提交位移"，`auto.offset.reset` 重新生效。**这是生产上"某组重启后突然从 latest 开始、丢了一批数据"的经典原因**，通常发生在业务停用一段时间后重新上线。
- 位移存在但目标位置已被 retention 删除 → 报 `OffsetOutOfRangeException`，此时同样按 `auto.offset.reset` 处理（`latest` 跳到末尾，`earliest` 跳到最早可用段，`none` 抛异常）。

### 2.6 位移提交与 Rebalance 的耦合

rebalance 会把分区从旧消费者移交给新消费者。**新消费者从哪个位置开始？** 从 `__consumer_offsets` 里该组该分区的已提交位移开始。

于是产生核心矛盾：

- 旧消费者"已经消费但还没提交"的部分 → 新消费者会**重新消费一遍**（重复）；
- 旧消费者"已经提交但还没处理完"的部分 → 新消费者跳过，那部分永远不处理（丢失）。

`ConsumerRebalanceListener.onPartitionsRevoked()` 是唯一的补偿点：在分区被回收**之前**同步提交已处理完成的位移，把重复窗口压缩到最小。

```java
consumer.subscribe(List.of("order-topic"), new ConsumerRebalanceListener() {
    @Override
    public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
        // 必须在 poll 线程内调用；协作式协议下只对"真正要交还"的分区触发
        consumer.commitSync(processedOffsetsOf(partitions));
    }
    @Override
    public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
        // 可从外部存储恢复位移：见 6.1 的 assign + seek 模式
    }
});
```

## 三、重复消费与漏消费：成因矩阵

### 3.1 成因矩阵

| 提交/处理顺序 | 场景 | 正常情况 | 故障时后果 | 语义 |
|---|---|---|---|---|
| **先处理后提交** | 手动提交，处理成功后再 `commit` | 不重不漏 | 处理完、提交前崩溃 → 该批**重复消费** | **at-least-once**（不丢，可能重） |
| **先提交后处理** | 手动提交，poll 后立刻 commit 再处理 | 不重不漏 | 提交后、处理前崩溃 → 那批**永久丢失** | at-most-once（不重，可能丢） |
| **自动提交** | `enable.auto.commit=true` | 提交点与处理点脱钩 | poll 已提交整批，处理中途崩溃 → **丢**；rebalance 前提交 → **重** | 视时序，既可能丢也可能重 |
| **rebalance 时未提交** | 处理完但没在 `onPartitionsRevoked` 提交 | 依赖周期提交 | 分区移交 → 新消费者从旧位移重放 → **重复消费** | at-least-once |
| **rebalance 时提前提交** | 在 `onPartitionsRevoked` 提交了"当前位置"而非"已处理位置" | 无 | 提交越界 → **漏消费** | at-most-once |
| **consumer 被踢出组** | 处理超过 `max.poll.interval.ms` | 无 | 消费者被判定死亡并踢出，位移未提交 → **重复消费**（且可能连环 rebalance） | at-least-once |
| **seek/reset 位移** | `--reset-offsets --to-earliest`、`--shift-by` | 无 | 人为回退 → 大批**重复消费**；前移 → **漏消费** | 人为 |
| **多线程异步处理 + 提交位移** | 单 consumer + 线程池，按接收顺序提交 | 无 | 后提交的位移越过尚未处理完的较前记录 → **漏消费** | 极易退化成 at-most-once |

一句话总结：**Kafka 只能保证"位移是单调推进的"，它不知道你的业务有没有处理成功。所以"不丢"的责任在提交时机，"不重"的责任在业务幂等。**

### 3.2 at-least-once 是如何成立的

只要满足两点，就能得到 at-least-once：

1. `enable.auto.commit=false`，**处理成功之后**才提交位移；
2. 处理逻辑**幂等**（见 3.3），使重复消费无害。

不丢的推理：消息只有在"被处理成功且位移被提交"之后才被认为消费完成；任何在处理与提交之间发生的崩溃，都会导致重启后重放，而不会跳过。

> [!warning] at-least-once 有个前提常被忽略
> "处理成功"如果包含**对外部系统写入**（写 DB / 发 HTTP / 发下游 MQ），那么崩溃点可能在"外部系统已写入、位移未提交"之间——重复消费时外部写入会再执行一次。Kafka 的位移提交**无法与外部系统组成原子操作**，这就是为什么幂等是必需的，而不是可选的优化。

### 3.3 为什么 exactly-once 需要事务

"消费-处理-生产"（consume-transform-produce）这条链路要做到恰好一次，需要同时原子地完成两件事：

1. 把处理结果写入下游 topic；
2. 提交上游分区的位移。

这两件事分别在两个 broker 上的不同日志里。Kafka 的解法是**事务**：把"下游写入"和"位移提交"放进同一个 `transactional.id` 的事务，由事务协调器统一提交或回滚，下游消费者用 `isolation.level=read_committed` 只读已提交数据。

```java
producer.initTransactions();
try {
    while (running.get()) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
        producer.beginTransaction();
        for (ConsumerRecord<String, String> r : records) {
            producer.send(new ProducerRecord<>("order-enriched", r.key(), transform(r.value())));
        }
        // 关键：位移随事务一起提交，而不是 consumer.commitSync()
        producer.sendOffsetsToTransaction(currentOffsets(records), consumer.groupMetadata());
        producer.commitTransaction();
    }
} catch (ProducerFencedException | OutOfOrderSequenceException | AuthorizationException e) {
    producer.close();
} catch (KafkaException e) {
    producer.abortTransaction();
}
```

> [!note] 边界必须说清楚
> - exactly-once 的保证范围**仅限 Kafka 内部**。一旦处理逻辑里写了 MySQL 或调了第三方接口，事务救不了它，仍然要靠幂等。
> - 事务有额外开销（`transaction.state.log`、`read_committed` 引入的 LSO 等待、每个分区要维护进行中的事务），不要为了"看起来严谨"而全链路开启。
> - 详细机制（`transactional.id`、`producer epoch`、`LSO`、`AddPartitionsToTxn`）见 [[6-事务与Exactly-Once]]。

## 四、核心参数详解

### 4.1 参数总表

| 参数 | 默认值 | 作用 | 调整后果 / 取舍 |
|---|---|---|---|
| `group.id` | 无（必填） | 消费组标识，决定位移归属与 coordinator 位置 | 改了就是**全新的组**，历史位移不带过去，`auto.offset.reset` 重新生效。多环境/多版本共用集群时用前缀区分 |
| `group.instance.id` | `null` | 静态成员标识，全局唯一 | 设为唯一值后可避免"重启触发 rebalance"（见 5.9）。**代价**：不能凭同一 id 改变订阅；真正宕机的成员要等 `session.timeout.ms` 才被踢，期间其分区无人消费 |
| `session.timeout.ms` | 45000（3.0 起；2.x 为 10000） | 心跳超时，超过则成员被判死并触发 rebalance | 调小 → 故障发现快，但网络抖动/长 GC 会**误判**导致无谓 rebalance；调大 → 误判少，但真宕机时分区闲置更久。受 broker 的 `group.min.session.timeout.ms`(6000) / `group.max.session.timeout.ms`(1800000) 约束 |
| `heartbeat.interval.ms` | 3000 | 心跳发送间隔 | 必须 < `session.timeout.ms`，官方建议约为其 1/3。调大 → 心跳开销小但发现延迟高；调小 → 心跳频繁，协调器压力大 |
| `max.poll.interval.ms` | 300000（5 分钟） | **两次 poll 之间的最大间隔**，超时则消费者主动离组 | **"处理太慢导致 rebalance"要调的是它，不是 `session.timeout.ms`**。调大有代价：真的卡死时，释放分区的时间被拉长 |
| `max.poll.records` | 500 | 单次 poll 最多返回的记录数 | 调小 → 单批处理时间短、更容易满足 `max.poll.interval.ms`、提交粒度细；代价是 poll 次数增多、吞吐略降。**处理单条耗时长时应优先调小它** |
| `fetch.min.bytes` | 1 | 一次 fetch 至少返回多少字节，不够就等服务端攒够 | 调大（如 1MB）→ 减少空 fetch、提升吞吐；代价是**低流量 topic 上延迟显著增加**（要等 `fetch.max.wait.ms`）。高吞吐、可容忍延迟的场景才调 |
| `fetch.max.bytes` | 52428800（50MB） | 单次 fetch 响应的**总**上限（跨所有分区） | 调大 → 单次拉更多、内存占用与 GC 压力上升。注意它是绝对上限，超出会切分 |
| `fetch.max.wait.ms` | 500 | 配合 `fetch.min.bytes`，最多等这么久 | 调大 → 攒批更充分但延迟上升；调小 → 响应更快但可能空转 |
| `max.partition.fetch.bytes` | 1048576（1MB） | 单分区单次 fetch 的**软**上限 | 注意：若某分区第一条记录批就大于该值，**仍会返回该批**以保证进度。所以要放大消息必须同时放宽它，否则消费端内存估算会失真 |
| `isolation.level` | `read_uncommitted` | 事务隔离级别 | `read_committed` 只读已提交事务的数据，**会跳过未提交/已回滚的记录**，并使消费位置受 LSO 限制（可能长时间停在原地等事务结束）。非事务场景不要开 |
| `partition.assignment.strategy` | 3.0 起默认 `RangeAssignor, CooperativeStickyAssignor`（有序列表，组内协商取交集） | 分区分配策略 | 见 5.8。多 topic 场景 Range 不均衡；要真正用上协作式，`CooperativeStickyAssignor` 必须在所有成员的列表里排第一 |
| `client.id` | `""` | 客户端逻辑名，出现在请求与 JMX 指标中 | **强烈建议显式设置**（含实例标识），否则排查 rebalance / 慢请求时无法定位到具体实例 |
| `connections.max.idle.ms` | 540000（9 分钟） | 空闲连接关闭时间 | 调小 → 长连接被频繁重建，影响时延；调大 → 在 NAT/LB 有连接老化（常见 350s/5min）时**更安全**。若前面有 LB，应设为小于 LB 的空闲超时，或调大 LB 超时 |
| `auto.offset.reset` | `latest` | 无已提交位移时的起点 | 见 2.5 |
| `enable.auto.commit` | `true` | 是否自动提交位移 | 业务场景务必改 `false` |
| `auto.commit.interval.ms` | 5000 | 自动提交的最小间隔 | 仅在自动提交时有效 |
| `request.timeout.ms` | 30000 | 单次请求超时 | 与 `max.poll.interval.ms` 的差值要留足重试空间 |
| `retry.backoff.ms` | 100 | 重试退避 | 网络抖动场景可适当调大 |
| `metadata.max.age.ms` | 300000 | 元数据强制刷新间隔 | 分区数变化后客户端感知延迟上限 |

### 4.2 双重存活判定：Heartbeat 与 Poll

这是本笔记最重要的一个概念区分。一个消费者"活着"需要**同时**满足两个条件：

| 判定 | 由谁检测 | 超时参数 | 检测的是什么 | 超时后的现象 |
|---|---|---|---|---|
| **心跳存活** | **协调器**（broker 端） | `session.timeout.ms`（默认 45s） | 进程/网络是否还能通信（后台心跳线程负责） | 协调器把成员**踢出组**，触发 rebalance；日志 `Removing member ... on heartbeat expiration` |
| **poll 存活** | 每个 **consumer 客户端自己** | `max.poll.interval.ms`（默认 5min） | 应用是否还在推进（业务处理是否卡住） | 客户端**主动**发 LeaveGroup 离开组、抛 `CommitFailedException`；日志 `Consumer poll timeout has expired` |

```text
        ┌─────────────────── 消费者进程 ────────────────────┐
        │                                                  │
        │   [后台心跳线程]  ──Heartbeat──> coordinator       │  判据 1：session.timeout.ms
        │        (KIP-62 引入, 不受业务阻塞影响)             │
        │                                                  │
        │   [用户线程] poll() ─> 处理 ─> 处理 ─> poll()      │  判据 2：max.poll.interval.ms
        │        └────── 这个间隔超了，自己退组 ──────┘      │
        └──────────────────────────────────────────────────┘
```

**为什么必须分成两个判据？** 因为两者的失败模式不同：

- 网络分区 / 进程崩溃 → 心跳停，需要**协调器**判死；
- 业务处理卡死（慢 SQL、死锁、下游超时）→ 进程活着、心跳照发，但**不再消费**。此时协调器认为它健康，分区却被一个"活死人"占着，必须由客户端自我了断，把分区让出去。

所以面试问"消费太慢导致一直 rebalance 怎么办"，正确答案是：

1. **先调 `max.poll.interval.ms`**（默认 5 分钟，通常调到 10~30 分钟）；
2. 同时**减小 `max.poll.records`**（默认 500，调到 50~200），让单批处理时间落在限制内；
3. 而不是去调 `session.timeout.ms`——那解决不了"活死人"问题。

> [!question] 为什么调大 `session.timeout.ms` 反而可能让问题更糟？
> 调大它会让"真宕机"的消费者长时间不被剔除，其持有的分区在 `session.timeout.ms` 内完全不被消费（lag 直接堆积）。KIP-735 把默认值从 10s 提高到 45s，就是为了平衡"减少误判"与"故障恢复时间"。这个值的调优方向是**跟你的 GC 停顿与网络质量匹配**，不是越大越好。

## 五、Rebalance 深度剖析

### 5.1 触发条件

| 触发源 | 具体原因 | 备注 |
|---|---|---|
| 成员加入 | 新消费者启动并 `subscribe` | 扩容、滚动发布都会触发 |
| 成员主动离开 | `consumer.close()` / 正常退出 | 优雅退出路径，会发 LeaveGroup |
| 成员崩溃/超时 | 心跳超时（`session.timeout.ms`）、poll 超时（`max.poll.interval.ms`）、OOM、GC 长停顿 | **生产上 rebalance 风暴的主因** |
| 订阅 topic 列表变化 | 同一组内成员订阅了**不同**的 topic，或用了正则订阅且匹配结果变化 | 组内订阅必须一致，否则分配结果不可预期 |
| 分区数变化 | 订阅的 topic 执行了 `--alter --partitions` | 每次扩分区都会触发一次 rebalance |
| topic 被删除/正则匹配到新 topic | 元数据变化 | |
| 协调器迁移 | 该组的 `__consumer_offsets` 分区 leader 换到别的 broker | 新协调器会重新加载组并可能触发 rebalance |

> [!tip] 运维启示
> "**扩分区**"和"**滚动重启消费者**"是两类完全可以避免的 rebalance 源头：前者规划分区数时一次到位；后者用静态成员（5.9）+ 协作式协议（5.6）把影响降到最低。

### 5.2 经典三阶段协议（Eager / Classic）

以**协调器**为中心的协议，共三个阶段：

```text
   消费者 C1, C2                                    GroupCoordinator
        │                                                  │
        │  ① JoinGroup(memberId="", protocols=[Range, ...]) │
        ├─────────────────────────────────────────────────>│
        │                                                  │ 收集所有成员,
        │  <── JoinGroup 响应: generation=G,               │ 选出第一个加入者
        │      leaderId=C1, members=[C1,C2]（只有 leader 有成员列表）│ 为 group leader
        │                                                  │
        │  ② C1(leader) 在客户端跑分配算法                   │
        │     SyncGroup(assignment={C1:[P0], C2:[P1]})      │
        ├─────────────────────────────────────────────────>│
        │  <── SyncGroup 响应: C1 得到自己的分配             │ 把 leader 的方案
        │  <── SyncGroup 响应: C2 得到自己的分配             │ 下发给所有成员
        │                                                  │
        │  ③ 开始 fetch；定期 Heartbeat(generation=G)        │
        ├─────────────────────────────────────────────────>│
        │  <── 心跳返回 REBALANCE_IN_PROGRESS → 重新 ①       │
```

关键细节：

- **Leader 不是协调器，而是组内第一个加入的消费者**。分配算法（assignor）运行在客户端 leader 上；协调器只负责收集成员和下发结果。这也意味着**分配逻辑由客户端代码决定**，所以组内客户端版本/配置不一致会导致诡异行为。（KIP-848 把这件事挪到了服务端，见 5.7。）
- **`memberId` 有"占位符"机制**：新版消费者首次以空 memberId 加入时，协调器会返回一个 `UNKNOWN_MEMBER_ID` + 临时 memberId，避免所有成员同时加入导致多次 rebalance（KIP-394）。
- **Generation 是 fencing 令牌**：`generation` 每次 rebalance 递增，旧代际的 `Heartbeat` / `OffsetCommit` 会被拒绝（`ILLEGAL_GENERATION`、`REBALANCE_IN_PROGRESS`），旧消费者因此无法继续写位移。`CommitFailedException` 基本都来自这里。
- **Rebalance 超时用的是客户端的 `max.poll.interval.ms`**：协调器等所有成员加入的时间上限就是各成员上报的这个值。所以 `max.poll.interval.ms` 调得过大会让 rebalance 卡得更久。
- Eager 协议下，**所有成员在 JoinGroup 之前先 revoke 全部分区**（`onPartitionsRevoked` 对全部已分配分区被调用），期间停止消费——这就是"stop-the-world"。

### 5.3 Coordinator 的角色

| 职责 | 说明 |
|---|---|
| 确定位置 | 由 `abs(groupId.hashCode()) % offsets.topic.num.partitions` 决定，本质是"承载该 `__consumer_offsets` 分区 leader 的那个 broker" |
| 成员管理 | 维护成员表、`memberId` 分配、代际递增、剔除超时成员 |
| 驱动 rebalance | 决定何时开始、何时结束 rebalance（收到全部成员加入或超时） |
| 选定 leader | 第一个加入的成员 |
| 处理位移 | 响应 `OffsetCommit` / `OffsetFetch`（位移读写都走协调器，不直连 `__consumer_offsets` 分区） |
| 组状态 | `Empty` → `PreparingRebalance` → `CompletingRebalance` → `Stable`；异常态 `Dead` |

```bash
# 查看组状态（Stable / PreparingRebalance / CompletingRebalance / Empty / Dead）
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --group order-cg --state
```

### 5.4 `group.initial.rebalance.delay.ms`

- **Broker 端参数**，默认 **3000（3 秒）**。
- 只作用于**一个"新组"的第一次 rebalance**：协调器在收到第一个成员加入后，**故意等待这段时间**，期望更多成员在同一窗口内加入，从而一次性分配完，避免"来一个分一次"造成 N 次 rebalance。
- 取舍：批量启动（如一次拉起 50 个 Pod）时，调大它（如 5000）能显著减少 rebalance 次数；但对**低频创建的组**来说是白等 3 秒，会拖慢消费启动。Kubernetes 里 pod 逐个滚动启动时，调大也救不了，只能靠静态成员。

> [!note] 组状态与它的关系
> 在等待窗口内，组状态是 `PreparingRebalance`，成员已经在组里但拿不到分配，也不消费。这就是"消费者启动后有几秒完全没消费"的原因。

### 5.5 心跳线程：KIP-62 带来的改变

**KIP-62（Kafka 0.10.1）之前**：心跳由 `poll()` 触发。`session.timeout.ms` 实际上约束的是"两次 poll 的间隔"，于是：

- 想减少网络抖动误判 → 必须调大 `session.timeout.ms`；
- 一旦调大，业务处理慢（比如一次批处理 30 秒）也**不会**被踢，但真宕机要等更久才能发现；
- 更糟的是，一次长 GC 或一次慢批处理就会把消费者踢出组，引发**无谓的 rebalance**。

**KIP-62 之后**：

1. 引入**独立的后台心跳线程**，按 `heartbeat.interval.ms` 持续发心跳，**不受业务处理阻塞影响**；
2. 把"处理是否推进"的判据从 `session.timeout.ms` 拆出来，独立成 `max.poll.interval.ms`；
3. 允许 `session.timeout.ms` 调到较小值（提高故障发现速度）而不会因慢处理导致误判。

所以今天你可以放心把 `session.timeout.ms` 设小（比如 10s）以获得快速故障转移，同时把 `max.poll.interval.ms` 设大（比如 10 分钟）以容纳慢批处理——这两个旋钮各管一件事，这是 KIP-62 最核心的价值。

### 5.6 协议演进：Eager → Cooperative Sticky（KIP-429）

| 维度 | Eager（Range / RoundRobin / Sticky） | Cooperative Sticky（KIP-429） |
|---|---|---|
| 分区回收范围 | **全部**：JoinGroup 前每个成员 revoke 所有分区 | **只 revoke 需要移交的分区** |
| 是否停止消费 | 是。全员 STW，直到拿到新分配 | 否。未涉及的分区**全程继续消费** |
| `onPartitionsRevoked/Assigned` 触发范围 | 每次都是全量分区 | 只对变化的分区触发 |
| Rebalance 轮数 | 1 轮 | 可能 2 轮（第一轮 revoke 多余分区，第二轮才拿到新分区） |
| 分配稳定性 | 依赖 Sticky 的"尽量保留"启发式 | 同样保留，且保留过程不打断消费 |
| 适用 | 老客户端、必须一次到位的小集群 | 3.x 生产环境的推荐选择 |

**协作式为什么不会全量 revoke？** 成员在 JoinGroup 时会上报自己**当前拥有的分区（ownedPartitions）**。leader 计算分配后，如果发现某分区需要从 A 移到 B，它不会直接塞给 B，而是先告诉 A "你 revoke 这个分区"。A revoke 完成后触发**第二轮 rebalance**，此时该分区已无人持有，才分配给 B。这样就避免了"B 拿到分区时 A 还在消费"的双重持有，也避免了无谓的全量 revoke。

> [!warning] 升级到协作式协议有个必须先做的动作
> 协议是在 JoinGroup 里协商的：**只有当组内所有成员的 `partition.assignment.strategy` 列表里都包含 `CooperativeStickyAssignor` 时，组才会使用协作式协议**（否则回退到 eager 的公共协议）。
>
> 正确升级路径是**两轮滚动升级**：
> 1. 第一轮：把客户端升级到支持 KIP-429 的版本（3.x 天然支持），**先不改 assignor 列表**，让所有成员都具备协作能力；
> 2. 第二轮：再把 `partition.assignment.strategy` 改成以 `CooperativeStickyAssignor` 开头（或只留它），滚动重启。
>
> 如果一次性改配置再滚动重启，中间的"混合状态"会退化成 eager 协议，反而引发更剧烈的 rebalance。

### 5.7 新一代消费协议：KIP-848（`group.protocol=consumer`）

KIP-848 是一次**把 rebalance 逻辑整体搬到服务端**的重构：

| 维度 | Classic（`group.protocol=classic`） | Consumer 协议（KIP-848） |
|---|---|---|
| 分配算法在哪跑 | 客户端 group leader | **服务端协调器**（`group.remote.assignor`，内置如 `uniform`/`range`） |
| 是否需要全员 JoinGroup | 是，`PreparingRebalance` 期间全员等待 | 否，成员增量加入即可收到分配 |
| 心跳语义 | 心跳同时承担存活与代际 | 会话与分配解耦，重新分配**不再要求全员重新加入** |
| STW | eager 全量 revoke | 天然增量（协作式），未变化分区不中断 |
| 客户端版本 | 全版本 | 需 3.7+（作为 early access 引入，4.0 GA），且需 broker 开启 `group.coordinator.rebalance.protocols` 包含 `consumer` |
| 启用方式 | 默认 | 客户端设 `group.protocol=consumer`，**opt-in**；组一旦以某协议建立，就不能在组存活期间切换 |

它解决的问题：大规模集群里"一次 rebalance 影响全组所有成员"、"分配计算在客户端导致版本漂移"、"成员数上万时 JoinGroup 风暴"。在新协议下，**增加一个成员只影响需要移动的那些分区**，其余消费者完全无感。

> [!note] 使用建议
> 3.x 上把它当作"可以试点但不要默认开"的特性：需要确认 broker 版本、监控工具（lag/组状态展示）对新协议的兼容性，并注意经典协议的 `session.timeout.ms` 等参数在新协议下由 broker 端配置（`group.consumer.*` 系列）接管。生产上更稳妥的路径是先在非核心集群验证。

### 5.8 分区分配策略对比

| 策略 | 类名 | 分配方式 | 均衡性 | Rebalance 时保留原分配 | 适用场景 |
|---|---|---|---|---|---|
| Range | `RangeAssignor` | 按 **topic** 把分区切成连续区间，组内按字典序每个消费者分一段 | 单 topic 下接近均衡；**多 topic 时严重不均衡** | 否，几乎全量重排 | 老集群默认；单 topic 且消费者数为分区数整除时 |
| RoundRobin | `RoundRobinAssignor` | 把所有订阅 topic 的分区**汇总后**逐个轮询分发 | 订阅一致时均衡；订阅不一致时可能不均衡 | 否 | 消费者订阅完全相同的一组 topic |
| Sticky | `StickyAssignor` | 先求均衡解，再在均衡前提下**尽量保留原有分配** | 均衡性最好（优于 Range/RoundRobin） | 是（但仍是 eager，需全员 revoke） | 想减少分区迁移，又不能上协作式（老客户端） |
| CooperativeSticky | `CooperativeStickyAssignor` | Sticky 的均衡目标 + **增量 revoke** | 均衡性最好 | 是，且**不打断**未变更分区的消费 | **3.x 生产环境推荐默认** |

**为什么 Range 在多 topic 时不均衡？** 因为它**逐个 topic 独立分配**。假设订阅 `t1`(3 分区)、`t2`(3 分区)，两个消费者：

```text
t1:  C1 -> [t1-0, t1-1]   C2 -> [t1-2]
t2:  C1 -> [t2-0, t2-1]   C2 -> [t2-2]
结果: C1 拥有 4 个分区, C2 只有 2 个  ← 2 倍差距
```

每个 topic 的"第一个消费者"总是同一个（按成员 ID 字典序），所以偏差会**跨 topic 累加**。topic 越多、分区数越接近消费者数，偏差越夸张（极端情况某个消费者拿 0 个分区，其他全包）。这是"消费 lag 一直集中在少数实例上"的常见根因之一。

> [!tip] 选型结论
> 3.x 新集群直接用 `CooperativeStickyAssignor`（配合 5.6 的两轮升级路径）。它同时解决了"不均衡"和"rebalance 期间停消费"两个问题，代价只是可能多一轮 rebalance。

### 5.9 静态成员（`group.instance.id`）

```java
// 每个实例一个稳定且全局唯一的值：hostname、pod 名、有序编号均可
props.put(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, "order-cg-worker-" + instanceIndex);
```

**机制**：设置 `group.instance.id` 后，消费者成为**静态成员**。协调器用它作为成员身份（而不是每次重新加入都分配新的 `memberId`）。因此：

- 成员重启后**在 `session.timeout.ms` 内**带上同一个 `group.instance.id` 重新加入 → 协调器认为"还是原来那个人回来了"，**不触发 rebalance**，直接下发给它原来的分区；
- 这对**滚动发布**极其有效：不再出现"重启一台就把全组打散一次"；
- 通常配合**调大 `session.timeout.ms`**（例如几分钟），给重启留出足够的回归窗口。上限受 broker 的 `group.max.session.timeout.ms`（默认 1800000，即 30 分钟）约束。

**代价与坑**：

| 坑 | 说明 |
|---|---|
| 故障检测变慢 | 成员真死掉时，分区要等整个 `session.timeout.ms` 才被重新分配，期间**该分区零消费**（lag 直线上升）。所以静态成员适合"重启快、故障少"的常驻服务，不适合频繁伸缩的批处理 |
| 不能改订阅 | 静态成员的订阅 topic 集合不能变；如果你想靠改配置让它订阅新 topic，**必须换一个新的 `group.instance.id`**，否则会拿到与新订阅不一致的旧分配 |
| ID 必须全局唯一 | 两个进程用同一个 `group.instance.id` → 协调器会把先到的踢掉（fencing），表现为**反复 rebalance、成员互相顶替**。Kubernetes 里严禁用 Deployment 名的固定值，要用 StatefulSet 序号或 pod 名 |
| 与缩容的语义冲突 | 缩容时要真正让成员退出（显式 `close()` 或让容器彻底消失），否则"幽灵成员"会占着分区 |
| 版本差异 | 不同版本对静态成员在显式 `close()` 时是否发送 LeaveGroup 的行为有过调整，涉及"重启是否复用分配"的验证请以实际版本实测为准 |

### 5.10 Rebalance 的危害与治理清单

**危害**：本质是**一段全员或部分成员停止消费的时间窗（STW）**。在窗内：

- 分区无人消费 → lag 堆积；
- 位移提交被拒（`CommitFailedException`）→ 可能出现大量重复消费；
- 客户端重新拉元数据、重新建连接 → 端到端延迟抖动；
- 与下游事务/幂等逻辑耦合时，重复窗口放大。

**监控什么**：

| 指标 | 意义 | 不健康的样子 |
|---|---|---|
| Consumer Lag（组级） | 消费是否跟上 | 台阶式上升且不回落 |
| `rebalance-rate-per-hour` / `rebalance-total`（JMX，`consumer-coordinator-metrics`） | rebalance 频率 | 每小时数十次以上即为"rebalance 风暴" |
| `rebalance-latency-avg/max` | 每次 rebalance 的耗时 | 几十秒以上，说明组内处理阻塞或成员多 |
| `last-rebalance-seconds-ago` | 距上次 rebalance | 长期接近 0 → 一直在 rebalance |
| `join-time-avg` / `sync-time-avg` | 加入/同步耗时 | 高 → 大组或大量分区 |
| 组状态 | `--describe --state` | 长期停在 `PreparingRebalance` |
| 消费者日志 | `Revoking previously assigned partitions` / `Attempt to heartbeat failed` / `Consumer poll timeout has expired` / `Removing member ... on heartbeat expiration` | 关键字出现即定位到具体原因 |

**减少 rebalance 的手段（按性价比排序）**：

1. **别让处理超过 `max.poll.interval.ms`**：调大该值（默认 5 分钟 → 10~30 分钟）+ 调小 `max.poll.records`（默认 500 → 50~200）。这是最高频的修复。
2. **静态成员**（5.9）：消灭"滚动重启 → rebalance"。
3. **协作式协议**（5.6）：把 STW 变成增量，未变更分区不中断。
4. **处理逻辑异步化 —— 但要极其小心**：poll 线程只做入队，处理交给线程池，确实能避免 poll 超时；可一旦"入队即提交位移"，语义就退化成 at-most-once（见 3.1 最后一行）。正确做法是：`pause()` 有界队列 + 背压，位移由"处理完成的连续水位线"驱动提交，或者干脆用 6.4 的"每线程一个 consumer"模型。
5. **组内订阅保持一致**：不要让同组的不同实例订阅不同 topic。
6. **不要频繁扩分区**：规划期一次到位。
7. **调大 `group.initial.rebalance.delay.ms`**（3s → 5~10s）：只对"同一窗口内批量启动"有效。
8. **会话与心跳匹配环境**：云上跨 AZ 或 LB 场景，网络抖动导致心跳超时，可适度调大 `session.timeout.ms` 并把 `heartbeat.interval.ms` 设为其 1/3。

> [!example] 一个真实故障的定位链条
> 现象：某组 lag 每小时出现一次"台阶式上涨"，随后慢慢回落。
> 排查：`kafka-consumer-groups.sh --describe --state` 看到组状态周期性进入 `PreparingRebalance`；消费者日志有 `Consumer poll timeout has expired`；JMX `rebalance-total` 每小时 +1。
> 原因：某个分区的数据触发了慢查询，单批 500 条处理耗时约 6 分钟 > `max.poll.interval.ms`=5 分钟 → 消费者自我退组。
> 处置：`max.poll.records` 降到 100，`max.poll.interval.ms` 提到 900000；同时把慢查询优化掉。lag 曲线恢复平稳。

## 六、Consumer 高级特性

### 6.1 `assign` + `seek`：手动分区消费

`assign()` 不走消费组协调逻辑（不订阅、不参与 rebalance），由你完全掌控分区：

```java
TopicPartition tp = new TopicPartition("order-topic", 0);
consumer.assign(List.of(tp));          // 直接指定分区，不 subscribe
consumer.seek(tp, 0);                  // 从最早重放
// consumer.seekToBeginning(List.of(tp));
// consumer.seekToEnd(List.of(tp));

while (running.get()) {
    for (ConsumerRecord<String, String> r : consumer.poll(Duration.ofMillis(500))) {
        handle(r);
        consumer.commitSync(Map.of(tp, new OffsetAndMetadata(r.offset() + 1)));
    }
}
```

| 用途 | 说明 |
|---|---|
| 数据重放 / 回补 | 指定分区 + `seek` 到目标位移，常用于"下游挂了，重放某几小时数据" |
| 精确控制并行 | 例如用 Kafka 做"任务队列"，每台机器 `assign` 自己的分区子集 |
| 与外部状态对齐 | 在 `onPartitionsAssigned` 里从外部存储读位移再 `seek`，实现"位移跟业务数据一起原子落库"（自定义位移管理） |

**注意**：`assign` 后若分区数变化或 broker 换 leader，客户端会自行刷新元数据，但如果分区被删除，会收到 `UNKNOWN_TOPIC_OR_PARTITION`。同时，**`assign` 与 `subscribe` 不能混用**；`group.id` 仍然可以设置，用于提交位移。

### 6.2 `pause` / `resume`：背压

当下游处理不过来（队列满、DB 慢、限流）时，与其让内存里堆满消息，不如暂停拉取：

```java
// 队列水位驱动的背压
for (TopicPartition tp : consumer.assignment()) {
    if (queueSize() > HIGH_WATERMARK) {
        consumer.pause(Set.of(tp));     // 停止从该分区返回数据
    } else if (queueSize() < LOW_WATERMARK) {
        consumer.resume(Set.of(tp));    // 恢复
    }
}
```

要点：

- `pause` 是**客户端行为**，协调器不知道；因此**仍然必须持续 `poll()`**，否则超过 `max.poll.interval.ms` 一样会被踢出组。pause 状态下 `poll()` 几乎立即返回空集合，成本极低。
- `pause` 不会取消已经在途的 fetch 请求，也不会清空已拉取到本地缓冲的数据（`ConsumerRecords` 里的数据仍会被返回）。
- 相比"降低 `max.poll.records`"，`pause` 是**动态**背压，能应对突发；两者常配合使用。

### 6.3 `wakeup`：打破阻塞的唯一手段

`poll()` 是阻塞的（可能阻塞到 `fetch.max.wait.ms` 或更久）。要让消费循环从外部线程停下来，标准做法是 `wakeup()`：

```java
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    running.set(false);
    consumer.wakeup();   // 从另一个线程调用，让阻塞中的 poll 抛 WakeupException
}, "consumer-shutdown"));

try {
    while (running.get()) { consumer.poll(Duration.ofMillis(500)); }
} catch (WakeupException e) {
    // 退出的正常路径，忽略
} finally {
    consumer.commitSync();
    consumer.close();
}
```

关键事实（来自 `KafkaConsumer` 的线程模型约定）：

- `KafkaConsumer` **不是线程安全的**；文档明确允许跨线程调用的方法只有 `wakeup()`（`close()` 的跨线程调用在部分版本可用，但不要依赖）。
- `wakeup()` 会让**当前或下一次**阻塞调用抛 `WakeupException`。如果调用时没有阻塞操作在进行，该异常会在下一次可中断调用时抛出。
- 抛出 `WakeupException` 后，消费者状态**没有损坏**，仍可以继续使用（例如清空 `wakeup` 标志后重新进入循环）——但通常的用法是直接退出。
- **不要用 `Thread.interrupt()`** 或 `stop()`/`suspend()` 之类的做法；那会破坏内部状态或让位移提交处于不确定状态。

### 6.4 多线程消费的两种模型

**模型 A：每线程一个 consumer（推荐）**

```text
   线程 1: Consumer#1  ->  分区 P0
   线程 2: Consumer#2  ->  分区 P1     (同一个 group.id)
   线程 3: Consumer#3  ->  分区 P2
```

- 位移提交天然按线程/分区隔离，没有跨线程提交越界问题；
- 每个 consumer 独立心跳、独立 rebalance（组内成员）；
- 缺点是消费者数受分区数限制，线程数超过分区数就浪费。

**模型 B：单 consumer 拉取 + 线程池处理**

```text
   [poll 线程] ──records──> [有界阻塞队列] ──> [处理线程池] ──> 业务
        │                                            │
        └────────── 位移提交？这里是最容易踩坑的地方 ──┘
```

| 危险 | 说明 |
|---|---|
| 提交越界（漏消费） | 线程池乱序完成，若按"处理完一条就提交一条"的方式提交，可能出现"offset=100 提交了，但 offset=50 还在处理"→ 崩溃后 50 丢失 |
| poll 超时 | 队列满后 poll 线程被处理能力牵着走，一旦超过 `max.poll.interval.ms` 就被踢出组 |
| 分区顺序被破坏 | 同一分区的记录被多个线程并行处理，key 级顺序全丢（除非按分区取模到固定线程） |
| 队列堆积 OOM | 无界队列 + 速度差 → 堆内存爆掉 |

**如果一定要用模型 B，必须做到三点**：

1. 队列**有界**，满了就 `pause()` 对应分区（背压），不要无界堆积；
2. **按分区 hash 到固定线程**，保证单分区串行，从而保证 key 顺序；
3. 位移只在"该分区所有小于等于 X 的记录都已处理完"（连续完成水位线）时提交，而不是每处理完一条就提交。这需要按分区维护一个"完成位点集合/滑动窗口"。

因为第 3 点实现复杂且极易写错，**优先选模型 A**。

## 七、消费滞后（Lag）的计算与排查

### 7.1 Lag 的定义

```text
Lag(分区) = LOG-END-OFFSET - CURRENT-OFFSET
          = （broker 端该分区最新可读位移） - （该组已提交的位移）
Lag(组)   = Σ 组内所有分区的 Lag
```

三个量的语义必须分清：

| 量 | 含义 | 谁的位置 |
|---|---|---|
| **LOG-END-OFFSET（LEO）** | 日志末尾的下一条待写位移，即"总共写了多少条" | broker 端 |
| **CURRENT-OFFSET** | 该组**已提交**的位移（下一条要消费的位置） | 消费者提交到 `__consumer_offsets` |
| **LAG** | 还没被该组"确认消费"的记录数 | 差值 |

> [!warning] 三种"lag"不是一回事
> 1. **`kafka-consumer-groups.sh` 的 LAG** = LEO − **已提交位移**。它能反映"消费者不在线"时的堆积，是运维口径的权威指标。
> 2. **客户端 JMX `records-lag-max` / `records-lag`** = LEO − **客户端本地 fetch position**。它反映"拉到手但还没提交"的距离，因此天然比运维口径**小**一个"已拉取未提交"的量；而且消费者下线后该指标直接消失（不再上报）。
> 3. `records-lead-min`：当它变成**负数/异常**时，说明消费者看到过的数据在 broker 上已经不存在（日志被截断，如 unclean 选举后的日志回退）——这是一个比 lag 更危险的信号。
>
> 所以"客户端说 lag 很小，运维平台说 lag 很大"不一定是 bug，先确认口径。

### 7.2 读 `kafka-consumer-groups.sh --describe`

```bash
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --group order-cg
```

```text
GROUP     TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG   CONSUMER-ID                     HOST          CLIENT-ID
order-cg  order-topic  0          1052            1052             0    consumer-order-cg-1-3f2a...    /10.0.1.11    order-cg-1
order-cg  order-topic  1          998             1520           522    consumer-order-cg-1-3f2a...    /10.0.1.11    order-cg-1
order-cg  order-topic  2          -               800              -    -                               -             -
```

逐列解读：

| 情况 | 含义 |
|---|---|
| 各分区 LAG 都接近 0 | 消费跟上 |
| 个别分区 LAG 高、其他为 0 | **分区热点 / key 倾斜**，或该分区的消费者线程被慢处理阻塞 |
| LAG 单调增长且 `CONSUMER-ID` 为空或 `-` | **没有消费者在消费**：进程挂了、被踢出组、或组内无成员 |
| `CURRENT-OFFSET` 为 `-` | 该组在该分区**没有已提交位移**（可能是从未消费过，或位移被 retention 清理）。注意：即使显式设了 `auto.offset.reset=earliest`，`--describe` 也不会显示未提交位移的分区，只会显示 `-` |
| 提示 `Consumer group 'order-cg' has no active members.` | 组内当前无活跃成员，但**位移可能仍然存在**（历史消费过），此时 LAG 表示"无人消费的积压" |
| `CONSUMER-ID` 为空但 LAG 有值 | 组处于 `Empty` 状态，位移还在 |

配套用法：

```bash
# 列出所有组
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --list

# 列出所有组的 lag 概览（3.x）
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --all-groups

# 看成员与各自持有的分区（定位"谁负责哪个分区"）
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --group order-cg --members --verbose

# 看组状态
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --describe --group order-cg --state

# 重置位移（组必须无活跃成员）
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --group order-cg \
  --reset-offsets --to-earliest --topic order-topic --execute
```

### 7.3 Lag 持续增长的排查思路

按"从外到内、从大到小"的顺序，逐层排除：

| 步骤 | 检查 | 典型结论 |
|---|---|---|
| 1 | 生产速率是否突增？`kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec`、`BytesInPerSec` | 上游放量 → 扩容消费者（需先确认分区数够） |
| 2 | 消费者是否还活着？`--describe --state` 是否 `Stable`、`CONSUMER-ID` 是否有值 | 掉线 / rebalance 风暴 → 转 5.10 |
| 3 | 是否所有分区都涨，还是个别分区涨？ | 个别 → **key 倾斜或分区热点**；全部 → 处理能力或下游瓶颈 |
| 4 | 消费者实例数是否已等于分区数？ | 是 → 加实例没用，必须**扩分区**（注意会破坏 key 顺序与触发 rebalance） |
| 5 | 消费线程是否阻塞在下游？看应用线程栈、DB/HTTP 耗时、GC 日志 | 下游慢 → 优化下游或用 6.2 背压 + 6.4 模型 A 扩并行 |
| 6 | 单批处理时间是否超过 `max.poll.interval.ms`？看 `poll` 到 `poll` 的间隔 | 调小 `max.poll.records`、调大 `max.poll.interval.ms` |
| 7 | fetch 是否慢？JMX `fetch-latency-avg`、broker 端 `TotalTimeMs,request=FetchConsumer` | 服务端慢（磁盘饱和、页缓存不足、网络带宽打满）→ 转 [[7-运维与集群调优]] |
| 8 | 客户端 GC 是否频繁？堆是否偏小？ | consumer 端内存/GC 问题：`max.partition.fetch.bytes` 调小，堆调大 |
| 9 | 提交是否慢？`commit-latency-avg`、`NOT_COORDINATOR` 报错 | `__consumer_offsets` 所在 broker 有问题 → 转 [[7-运维与集群调优]] |
| 10 | 是否开着 `isolation.level=read_committed` 而事务长时间未提交？ | 消费位置被 LSO 卡住，看似 lag 不降 → 检查事务超时/悬挂事务 |

> [!example] "lag 高但消费者 CPU 空闲"的三种典型原因
> 1. **分区数不足**：3 个分区、3 个消费者、每个都已打满单线程处理能力 → 加消费者无效，必须扩分区。
> 2. **下游限流**：消费者在等 HTTP/DB，CPU 自然空闲 → 看线程栈和下游耗时，而不是看 Kafka。
> 3. **key 倾斜**：某个热点 key 让一个分区独占 80% 流量 → 从 `--describe` 的单分区 lag 差异即可确认，解法是打散 key 或给热点 key 单独建 topic。

## 八、完整 Java 示例：手动提交 + 优雅关闭 + 幂等骨架

```java
package com.example.kafka;

import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.TopicPartition;
import org.apache.kafka.common.errors.WakeupException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * 手动提交 + 优雅关闭 + 幂等处理的消费者骨架。
 * 语义：at-least-once（处理成功才提交），重复由业务幂等吸收。
 */
public class OrderConsumer {

    private static final Logger log = LoggerFactory.getLogger(OrderConsumer.class);
    private static final String TOPIC = "order-topic";
    private static final String GROUP = "order-cg";

    /** 只记录"已成功处理完成"的位置，绝不使用 position() 做批量提交 */
    private final Map<TopicPartition, OffsetAndMetadata> processed = new HashMap<>();
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final KafkaConsumer<String, String> consumer;
    private final OrderService orderService;   // 业务：内部必须幂等

    public OrderConsumer(String instanceId, OrderService orderService) {
        this.orderService = orderService;

        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "broker1:9092,broker2:9092,broker3:9092");
        props.put(ConsumerConfig.GROUP_ID_CONFIG, GROUP);
        // 静态成员：滚动重启不触发 rebalance（需全局唯一，见 5.9）
        props.put(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, instanceId);
        props.put(ConsumerConfig.CLIENT_ID_CONFIG, "order-cg-" + instanceId);   // JMX 可定位到实例
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
                "org.apache.kafka.common.serialization.StringDeserializer");
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
                "org.apache.kafka.common.serialization.StringDeserializer");

        // ---- 位移语义 ----
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");        // 关键：关闭自动提交
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");        // 仅在无已提交位移时生效

        // ---- 存活与处理 ----
        props.put(ConsumerConfig.SESSION_TIMEOUT_MS_CONFIG, "45000");        // 心跳超时（协调器判死）
        props.put(ConsumerConfig.HEARTBEAT_INTERVAL_MS_CONFIG, "3000");      // ≈ session/3
        props.put(ConsumerConfig.MAX_POLL_INTERVAL_MS_CONFIG, "900000");     // 15min：容纳慢批处理
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, "100");            // 减小单批，降低超时风险
        props.put(ConsumerConfig.CONNECTIONS_MAX_IDLE_MS_CONFIG, "540000");

        // ---- 拉取性能 ----
        props.put(ConsumerConfig.FETCH_MIN_BYTES_CONFIG, "1");
        props.put(ConsumerConfig.FETCH_MAX_WAIT_MS_CONFIG, "500");
        props.put(ConsumerConfig.FETCH_MAX_BYTES_CONFIG, "52428800");        // 50MB
        props.put(ConsumerConfig.MAX_PARTITION_FETCH_BYTES_CONFIG, "1048576"); // 1MB
        props.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_uncommitted"); // 无事务则不要开 read_committed

        // ---- 分配策略：协作式，rebalance 不打断未变更分区 ----
        props.put(ConsumerConfig.PARTITION_ASSIGNMENT_STRATEGY_CONFIG,
                "org.apache.kafka.clients.consumer.CooperativeStickyAssignor");

        this.consumer = new KafkaConsumer<>(props);
    }

    public void run() {
        // wakeup() 是唯一允许从其他线程调用的方法
        Thread shutdownHook = new Thread(() -> {
            log.info("shutdown signal received, waking up consumer");
            running.set(false);
            consumer.wakeup();
        }, "order-consumer-shutdown");
        Runtime.getRuntime().addShutdownHook(shutdownHook);

        try {
            consumer.subscribe(List.of(TOPIC), new ConsumerRebalanceListener() {
                @Override
                public void onPartitionsRevoked(Collection<TopicPartition> partitions) {
                    // 交还分区前同步提交：把"已处理但未提交"的重复窗口压到最小
                    log.info("partitions revoked, committing processed offsets: {}", partitions);
                    commitSyncQuietly(partitions);
                    // 交还后这些分区的进度要从 map 中清理
                    partitions.forEach(processed::remove);
                }

                @Override
                public void onPartitionsAssigned(Collection<TopicPartition> partitions) {
                    log.info("partitions assigned: {}", partitions);
                    // 如需从外部存储恢复位移（位移与业务数据一起落库），在这里 seek：
                    // partitions.forEach(tp -> {
                    //     Long o = offsetStore.load(GROUP, tp);
                    //     if (o != null) consumer.seek(tp, o);
                    // });
                }

                @Override
                public void onPartitionsLost(Collection<TopicPartition> partitions) {
                    // 协作式协议下分区被"抢走"（不是正常交还）时触发，此时不允许提交（会抛异常）
                    log.warn("partitions lost (no commit allowed): {}", partitions);
                    partitions.forEach(processed::remove);
                }
            });

            while (running.get()) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
                if (records.isEmpty()) {
                    continue;
                }

                for (TopicPartition tp : records.partitions()) {
                    for (ConsumerRecord<String, String> record : records.records(tp)) {
                        // 幂等：业务侧用唯一键去重 / upsert / 版本号比较
                        orderService.handleIdempotent(record.key(), record.value(), record.offset());
                        // 只有处理成功后才推进提交位点
                        processed.put(tp, new OffsetAndMetadata(record.offset() + 1));
                    }
                }

                // 异步提交（带参、按分区精确提交）：不阻塞循环
                consumer.commitAsync(new HashMap<>(processed), (offsets, ex) -> {
                    if (ex != null) {
                        // 常见：RebalanceInProgressException（组在 rebalance）、CommitFailedException
                        // 这里不重试：下一次提交会覆盖；rebalance 场景由 onPartitionsRevoked 兜底
                        log.warn("async commit failed, will be superseded by next commit", ex);
                    }
                });
            }
        } catch (WakeupException e) {
            log.info("consumer woken up, exiting loop");   // 正常退出路径
        } catch (Exception e) {
            log.error("consume loop failed", e);
            running.set(false);                            // 让上层决定是否重启
        } finally {
            commitSyncQuietly(processed.keySet());         // 退出前同步兜底
            consumer.close(Duration.ofSeconds(30));        // 主动离开组，触发一次 rebalance
            try {
                Runtime.getRuntime().removeShutdownHook(shutdownHook);
            } catch (IllegalStateException ignored) {
                // JVM 已在关闭中
            }
            log.info("consumer closed");
        }
    }

    /** 只提交指定分区，避免 commitSync() 无参版本"提交整批 position"的丢数据陷阱 */
    private void commitSyncQuietly(Collection<TopicPartition> partitions) {
        Map<TopicPartition, OffsetAndMetadata> toCommit = new HashMap<>();
        for (TopicPartition tp : partitions) {
            OffsetAndMetadata om = processed.get(tp);
            if (om != null) {
                toCommit.put(tp, om);
            }
        }
        if (toCommit.isEmpty()) {
            return;
        }
        try {
            consumer.commitSync(toCommit);
        } catch (WakeupException | InterruptException ignored) {
            // 关闭途中被打断，交给下一轮或重启后的重放
        } catch (CommitFailedException e) {
            // 代际已失效（rebalance 已把分区转走），此时不应再提交
            log.warn("commit failed because generation changed, offsets may be replayed", e);
        }
    }
}
```

**这个骨架的四个设计点，值得在面试里主动讲**：

1. **提交逻辑独立于 `position()`**：用 `processed` map 显式记录"已处理成功的位置"，避免无参 `commitSync()` 把未处理记录一并提交。
2. **三段式提交**：循环内 `commitAsync`（快）→ `onPartitionsRevoked` 中 `commitSync`（保 rebalance 不丢进度）→ `finally` 中 `commitSync`（保退出不丢进度）。
3. **优雅关闭**：`wakeup()` 打破阻塞 + `close(30s)` 主动离开组，把"崩溃式退出（等 `session.timeout.ms`）"变成"秒级退出"，缩短分区无主的时间。
4. **幂等兜底而非追求不重复**：位移提交与业务写入无法原子，所以 `orderService.handleIdempotent` 是语义的最后一道防线。

> [!note] Spring Kafka 的对应写法
> `spring-kafka` 里对应的是 `AckMode.MANUAL_IMMEDIATE` + `Acknowledgment.acknowledge()`（处理成功后 ack）、`ContainerProperties.setConsumerRebalanceListener`、`ConcurrentKafkaListenerContainerFactory.setConcurrency`（对应"每分区一个消费线程"模型）、以及 `KafkaListenerEndpointRegistry` 的优雅停机。细节见 [[9-SpringBoot实战]]。

## 九、必答问题

> [!question] Q1：如何保证消息不重复消费、不丢失？
> **分层回答，先纠正问题本身**：Kafka 消费者侧**只能做到 at-least-once**，"不重复"必须在业务侧解决。
> - **不丢失**：`enable.auto.commit=false` + 处理成功后才提交位移 + 用"已处理位置"而非 `position()` 提交 + 在 `onPartitionsRevoked`/`finally` 中同步兜底提交。生产端配合 `acks=all` + `min.insync.replicas>=2`（见 [[3-生产者原理]] 与 [[5-日志存储与副本机制]]）。
> - **不重复**：位移提交与业务写入无法原子，因此**幂等是必需项**——唯一键去重表、`INSERT ... ON DUPLICATE KEY UPDATE` / upsert、带版本号的乐观更新、Redis setnx 去重窗口。
> - **真正要 exactly-once**：只在"消费 Kafka → 处理 → 写回 Kafka"的闭环内可用事务（`sendOffsetsToTransaction` + `isolation.level=read_committed`），一旦落到外部系统，仍然回到幂等。详见 [[6-事务与Exactly-Once]]。

> [!question] Q2：Rebalance 怎么优化？
> 按"先定位再优化"的结构答：
> 1. **先定位**：`--describe --state` 看组状态、看 `rebalance-rate-per-hour` / `last-rebalance-seconds-ago`、在消费者日志里找 `Consumer poll timeout has expired`（poll 超时）还是 `Removing member ... on heartbeat expiration`（心跳超时）——两者解法完全不同。
> 2. **poll 超时类**：调大 `max.poll.interval.ms`（默认 300000）、调小 `max.poll.records`（默认 500）、把慢下游优化掉；不要靠调 `session.timeout.ms` 解决。
> 3. **重启/扩缩容类**：静态成员 `group.instance.id` + 调大 `session.timeout.ms`。
> 4. **STW 类**：`CooperativeStickyAssignor`（注意两轮滚动升级）、新协议 `group.protocol=consumer`（KIP-848）。
> 5. **结构类**：组内订阅保持一致、别频繁扩分区、`group.initial.rebalance.delay.ms` 应对批量启动、关注"消费者数 ≤ 分区数"。

> [!question] Q3：位移提交的时机？自动提交有什么问题？
> - 提交的是**下一条要消费的位置**（处理完 offset=X 就提交 X+1）。
> - **自动提交**由 `poll()` 驱动（不是定时线程），提交的是"已 poll 出来的位置"，即先提交后处理 → 崩溃会丢消息；rebalance 前还会提交一次，放大重复窗口。因此只适合允许丢数据的管道。
> - **手动提交**的标准组合：循环内 `commitAsync`（不阻塞、失败仅记录、不重试以免位移回退）+ `onPartitionsRevoked` 与 `finally` 中 `commitSync`（保证交还分区与退出时不丢进度）+ 按分区精确提交（缩小重复窗口）+ 业务幂等（吸收重复）。
> - 若用事务：位移必须通过 `sendOffsetsToTransaction` 与下游写入一起提交，**不能再调 `consumer.commitSync()`**。

> [!question] Q4（加分）：`session.timeout.ms` 和 `max.poll.interval.ms` 有什么区别？
> 前者是**协调器**判定"这个成员是否还活着"的超时，由**后台心跳线程**维持（KIP-62 引入，不受业务阻塞影响）；后者是**客户端自己**判定"应用是否还在推进"的超时，超时后消费者主动 LeaveGroup。`session.timeout.ms` 超时 → 协调器剔除成员；`max.poll.interval.ms` 超时 → 成员自杀式离组并抛 `CommitFailedException`。前者管"进程/网络死活"，后者管"业务是否卡死"。所以"处理太慢"要调后者。

## 十、关联笔记

- [[1-Kafka总览]] —— 系列索引与学习路径
- [[2-架构与核心概念]] —— Topic / Partition / Replica / ISR / 协调器前置知识
- [[3-生产者原理]] —— 生产端的 `acks`、幂等生产者与重试
- [[5-日志存储与副本机制]] —— `__consumer_offsets` 的存储形态、LEO/HW、日志截断
- [[6-事务与Exactly-Once]] —— 事务、`read_committed`、`sendOffsetsToTransaction`
- [[7-运维与集群调优]] —— broker 端参数、监控指标、lag 飙升与 rebalance 风暴的集群侧处置
- [[8-性能优化与高吞吐原理]] —— 端到端吞吐优化的整体视角
- [[9-SpringBoot实战]] —— `@KafkaListener`、`AckMode`、容器并发与优雅停机
- [[10-面试高频题]] —— 本笔记的面试问题汇总与追问链
