---
title: Flink 开发常用 API 速查（1.20 / 2.x 双版本对照）
tags: [Flink, API, 速查, DataStream, TableAPI, 开发手册]
status: 进行中
created: 2026-10-12
---

# 🧰 十四、Flink 开发常用 API 速查

> 本篇是**写代码时手边要翻的那一页**：把 Flink 开发中真正高频用到的 API 按"作业生命周期"顺序排好，**每个都标出 1.20 与 2.x 的差异**。
> 与系列其他篇的分工：本篇**只讲"怎么写"**（API 签名、模板、易错点）；**"为什么"**由 [[1-架构与运行时]]（运行时）、[[2-时间与窗口]]（时间语义）、[[3-状态管理]]（状态）、[[5-Checkpoint与Savepoint]]（容错）、[[8-FlinkSQL与TableAPI]]（SQL 深入）负责。

> [!warning] 先看版本：Flink 2.x 有一批**破坏性 API 变更**
> | 变更 | 1.20 | ⚠️ 2.x |
> | --- | --- | --- |
> | **Java 版本** | 8 / 11 | ⭐ **17+**（21 实验性） |
> | **Source** | `SourceFunction` + `env.addSource()` | ⭐ **只有新 Source API（FLIP-27）**：`env.fromSource()` |
> | **Sink** | `SinkFunction` + `stream.addSink()` | ⭐ **只有 Sink V2（FLIP-143）**：`stream.sinkTo()` |
> | **时间** | `Time.seconds(10)` | ⭐ **`Duration.ofSeconds(10)`**（`Time` 废弃） |
> | **时间语义** | `setStreamTimeCharacteristic()` | ⭐ **`TimeCharacteristic` 移除**（只剩事件时间语义） |
> | **函数 open()** | `open(Configuration)` | ⭐ **`open(OpenContext)`**（所有 `RichFunction` 子类） |
> | **配置 API** | `conf.setInteger("key", v)` | ⭐ **`conf.set(RestOptions.PORT, v)`**（类型安全 `ConfigOption`） |
> | **配置文件** | `flink-conf.yaml`（扁平 key） | ⭐ **`config.yaml`**（标准嵌套 YAML） |
> | **DataSet API** | 存在（已废弃） | ⭐ **整体移除** |
> | **Scala API** | 存在 | ⭐ **整体移除** |
> | **其它移除** | — | `IterativeStream`、`keyBy(0)`/`keyBy("f")`、`readTextFile/writeAsText`、`env.setStateBackend`、`env.setRestartStrategy`、env 上的 Kryo 注册方法 |
>
> 依据：[Flink 2.0 Release Notes](https://nightlies.apache.org/flink/flink-docs-release-2.0/release-notes/flink-2.0/)、[Flink 2.x Migration Guide](https://github.com/aws/agent-toolkit-for-aws/blob/ed19c44c46c9c3a12ef0ff5bbf88161b75d3efbe/skills/specialized-skills/analytics-skills/developing-applications-on-managed-service-for-apache-flink/references/flink-2x-migration.md)。逐项迁移对照见 [附录 A](#附录-a1x--2x-迁移逐项对照)。

---

## 〇、API 全景：选 DataStream 还是 Table/SQL？

```mermaid
flowchart TD
    S["要写一个 Flink 作业"] --> Q1{"数据是 SQL 能表达的吗？"}
    Q1 -->|"是（过滤/聚合/Join/窗口）"| Q2{"团队更熟 SQL 还是 Java？"}
    Q1 -->|"否（复杂状态机/自定义 CEP/精细控制）"| DS["✅ DataStream API"]
    Q2 -->|"SQL"| TB["✅ Table API / SQL<br/>（开发快、自动优化）"]
    Q2 -->|"Java"| DS
    DS --> MIX["⭐ 混合：SQL 做大头 + DataStream 处理个别算子<br/>（两套 API 可互转，见 §十）"]
    TB --> MIX
    DS --> DSX["算子见 §三｜窗口 §四｜状态 §五"]
    TB --> TBX["DDL / TVF / 维表 Join<br/>详见 8-FlinkSQL与TableAPI"]
```

**同一件事的两种写法**（对照记忆）：

| 需求 | DataStream API | Table API / SQL |
| --- | --- | --- |
| 过滤 | `stream.filter(e -> e.amount > 100)` | `SELECT * FROM t WHERE amount > 100` |
| 分组聚合 | `.keyBy(e -> e.uid).sum("amount")` | `SELECT uid, SUM(amount) FROM t GROUP BY uid` |
| 事件时间窗口聚合 | `.window(TumblingEventTimeWindows.of(...)).aggregate(...)` | `TABLE(TUMBLE(TABLE t, DESCRIPTOR(ts), INTERVAL '1' MINUTE))` |
| 双流 Join | `.intervalJoin(...)` / `.join(...)` | `JOIN ... ON a.uid = b.uid AND a.ts BETWEEN ...` |
| 维表关联 | `RichAsyncFunction` 手写 | ⭐ **Lookup Join**（`FOR SYSTEM_TIME AS OF`） |
| 去重 | 手写 `KeyedProcessFunction` + 状态 | ⭐ **`ROW_NUMBER() OVER (PARTITION BY ...)`** |
| 读 Kafka | `KafkaSource` | `'connector' = 'kafka'` |
| 写 Kafka | `KafkaSink` | `'connector' = 'kafka'` |

> [!tip] 选型口诀
> **能用 SQL 表达就用 SQL**（自动优化、状态管理更省心）；**SQL 表达不了才下沉到 DataStream**；两者可以互转（§十），不必二选一。

---

## 案例导读：一个作业贯穿全篇

> 单纯列 API 容易"看了就忘"。所以本篇**用同一个作业把所有 API 串起来**——每章末尾的「**用例子看**」都会回到它。
> **作业名**：`order-stats-job`（电商实时订单看板 + 大额告警）

### 业务需求（6 条）

| # | 需求 | 用到的 API |
| --- | --- | --- |
| 1 | 从 Kafka 读订单，按**事件时间**处理（容忍 5 秒乱序） | `KafkaSource` + `WatermarkStrategy` |
| 2 | 过滤掉脏数据（金额 ≤ 0） | `filter` |
| 3 | 按用户分组，**1 分钟滚动窗口**统计消费额 | `keyBy` + `window` + `aggregate` |
| 4 | 维护每个用户的**累计消费**，30 分钟无数据就清空状态 | `ValueState` + 定时器 + TTL |
| 5 | **大额订单（> 5000）** 实时告警（旁路输出） | `sideOutput` |
| 6 | **迟到数据**旁路输出，不静默丢弃 | `allowedLateness` + `sideOutputLateData` |
| 7 | 结果补上**用户等级**（异步查维表） | `AsyncDataStream` |
| 8 | 结果写 Kafka + 本地打印便于调试 | `sinkTo` + `print` |

### 样例数据（故意设计得"什么情况都覆盖"）

| 到达顺序 | orderId | userId | amount | 事件时间 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | o1 | u1 | 120.00 | 10:00:05 | 正常 |
| 2 | o2 | u2 | 80.00 | 10:00:20 | 正常 |
| 3 | o3 | u1 | **-5.00** | 10:00:40 | ⚠️ 脏数据 → 被 `filter` 丢弃 |
| 4 | o4 | u1 | **6000.00** | 10:01:10 | ⚠️ 大额 → 走**侧输出告警**；同时它的水位推进**触发了第一个窗口** |
| 5 | o6 | u3 | 300.00 | 10:01:30 | 正常 |
| 6 | o5 | u2 | 200.00 | **10:00:50** | ⚠️ **迟到**（到达时水位已过 10:01:00）→ 走**迟到侧输出** |

### 端到端数据流（这张图是全文的地图）

```mermaid
flowchart LR
    K["Kafka topic: orders<br/>3 个分区"] --> SRC["① KafkaSource<br/>+ 水位策略<br/>乱序容忍 5s"]
    SRC --> F["② filter<br/>amount 大于 0"]
    F --> KB["③ keyBy(userId)<br/>⭐ 按用户分组"]
    KB --> W["④ 1 分钟滚动窗口<br/>+ sideOutputLateData"]
    W --> AGG["⑤ aggregate<br/>sum(amount)"]
    AGG --> ASY["⑥ Async I/O<br/>补用户等级"]
    ASY --> S1["⑦ KafkaSink<br/>order-stats"]
    ASY --> S2["print 调试"]
    W -.->|"⭐ 迟到数据"| LATE["侧输出 late-data<br/>→ 补偿/告警"]
    F -.->|"⭐ amount 大于 5000"| BIG["侧输出 big-order<br/>→ 风控告警"]
    style W fill:#fff3cd,stroke:#e0a800
    style LATE fill:#f8d7da
    style BIG fill:#f8d7da
```

> [!tip] 怎么用这条案例
> ① 先看 [§三 的「用例子看」](#用例子看6-条订单是怎么被一步步处理的) —— **一条数据从进到出被怎么处理**；
> ② 再看 [§十三 完整实战](#十三完整实战把所有-api-串成一个作业) —— **完整可运行代码**；
> ③ 中间任何一章的「用例子看」都可以单独回看。

---

## 一、环境与作业骨架

### 1.1 DataStream 作业骨架（可直接复制）

```java
public class MyJob {
    public static void main(String[] args) throws Exception {
        // ① 环境（本地 IDE 直接跑，提交到集群时自动用集群环境）
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(4);

        // ② 容错（生产必开）
        env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);
        CheckpointConfig cp = env.getCheckpointConfig();
        cp.setMinPauseBetweenCheckpoints(30_000);
        cp.setCheckpointTimeout(10 * 60_000);
        cp.setMaxConcurrentCheckpoints(1);
        cp.setTolerableCheckpointFailureNumber(3);
        cp.setExternalizedCheckpointRetention(
                ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION);
        cp.setCheckpointStorage("s3://my-bucket/flink/ckp");

        // ③ Source
        KafkaSource<Order> source = KafkaSource.<Order>builder()
                .setBootstrapServers("kafka-1:9092,kafka-2:9092")
                .setTopics("orders")
                .setGroupId("order-job")
                // ⭐ 生产用 committedOffsets：优先续上次位点，没有才回退 earliest
                .setStartingOffsets(OffsetsInitializer.committedOffsets(
                        OffsetResetStrategy.EARLIEST))
                .setDeserializer(KafkaRecordDeserializationSchema.of(new OrderDeserializer()))
                .build();

        DataStream<Order> orders = env.fromSource(
                source,
                WatermarkStrategy.<Order>forBoundedOutOfOrderness(Duration.ofSeconds(5))
                        .withTimestampAssigner((e, ts) -> e.getEventTime())
                        .withIdleness(Duration.ofMinutes(1)),   // 空闲分区不拖住水位
                "kafka-orders");

        // ④ 转换
        DataStream<OrderStat> stat = orders
                .filter(o -> o.getAmount() > 0)
                .keyBy(Order::getUserId)
                .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
                .aggregate(new AmountAggregate(), new ResultProcessWindowFunction());

        // ⑤ Sink
        stat.sinkTo(KafkaSink.<OrderStat>builder()
                .setBootstrapServers("kafka-1:9092")
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic("order-stats")
                        .setValueSerializationSchema(new OrderStatSchema())
                        .build())
                .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
                .setTransactionalIdPrefix("order-stat-tx-")   // Exactly-Once 必填
                .build());

        // ⑥ 触发执行（⭐ 不调用 execute 作业不会跑）
        env.execute("order-stat-job");
    }
}
```

```mermaid
flowchart LR
    A["① getExecutionEnvironment"] --> B["② 容错配置<br/>enableCheckpointing"]
    B --> C["③ Source<br/>fromSource"]
    C --> D["④ Transformation<br/>map/keyBy/window"]
    D --> E["⑤ Sink<br/>sinkTo"]
    E --> F["⑥ env.execute()<br/>⭐ 提交作业"]
```

### 1.2 Table/SQL 作业骨架

```java
public static void main(String[] args) {
    StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
    EnvironmentSettings settings = EnvironmentSettings.newInstance()
            .inStreamingMode()          // 或 .inBatchMode()
            .build();
    StreamTableEnvironment tEnv = StreamTableEnvironment.create(env, settings);

    // 执行配置（SQL 层参数，等价于 SQL Client 里的 SET）
    tEnv.getConfig().set("table.exec.state.ttl", "24h");
    tEnv.getConfig().set("table.exec.mini-batch.enabled", "true");
    tEnv.getConfig().set("table.exec.mini-batch.allow-latency", "5s");

    // DDL 建表（详见 [[8-FlinkSQL与TableAPI]]）
    tEnv.executeSql("""
        CREATE TABLE orders (
          order_id   BIGINT,
          user_id    BIGINT,
          amount     DECIMAL(10,2),
          ts         TIMESTAMP(3),
          WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
        ) WITH (
          'connector' = 'kafka',
          'topic' = 'orders',
          'properties.bootstrap.servers' = 'kafka-1:9092',
          'properties.group.id' = 'order-job',
          'scan.startup.mode' = 'group-offsets',
          'format' = 'json'
        )
        """);

    // 查询 + 写出（INSERT INTO 直接提交作业；也可 sqlQuery 拿 Table 再转换）
    tEnv.executeSql("""
        INSERT INTO order_stats
        SELECT user_id, window_start, window_end, SUM(amount) AS total
        FROM TABLE(TUMBLE(TABLE orders, DESCRIPTOR(ts), INTERVAL '1' MINUTE))
        GROUP BY user_id, window_start, window_end
        """);
}
```

### 1.3 环境常用方法

| 方法 | 作用 | 备注 |
| --- | --- | --- |
| `getExecutionEnvironment()` | ⭐ **唯一入口** | 本地跑用本地环境，提交作业用集群环境 |
| `createLocalEnvironment(int)` | 本地指定并行度 | 仅调试 |
| `setParallelism(n)` | 作业级并行度 | 算子级用 `.setParallelism(n)` |
| `enableCheckpointing(ms)` | 开启 Checkpoint | 见 §九 |
| `setRuntimeMode(RuntimeExecutionMode.BATCH)` | 切换批模式 | ⭐ 流批一体 |
| `getConfig().setAutoWatermarkInterval(ms)` | 水位生成周期 | 默认 **200ms** |
| `registerCachedFile(...)` | 分发文件到 TM | 小配置文件场景 |
| `env.execute("name")` | ⭐ **触发执行** | 不调用作业不会跑；`executeAsync()` 返回 `JobClient` |

---

## 二、Source：数据源

### 2.1 新 Source API（1.12+，2.x 唯一方式）

```java
// ① Kafka（最常用）—— 详见 §十二 依赖
KafkaSource<String> kafka = KafkaSource.<String>builder()
        .setBootstrapServers("localhost:9092")
        .setTopics("topic-a", "topic-b")           // 或 setTopicPattern(Pattern)
        .setGroupId("my-group")
        .setStartingOffsets(OffsetsInitializer.committedOffsets(OffsetResetStrategy.LATEST))
        .setBounded(OffsetsInitializer.latest())   // ⭐ 有界读 → 批模式
        .setValueOnlyDeserializer(new SimpleStringSchema())
        .setProperty("partition.discovery.interval.ms", "60000")  // 动态发现新分区
        .build();

DataStream<String> stream = env.fromSource(
        kafka, WatermarkStrategy.noWatermarks(), "kafka-source");
```

### 用例子看：Kafka 3 个分区怎么读、水位怎么生成

以 [案例导读](#案例导读一个作业贯穿全篇) 的 `orders`（3 分区）为例：

```mermaid
sequenceDiagram
    autonumber
    participant P0 as Partition 0
    participant P1 as Partition 1
    participant P2 as Partition 2
    participant SRC as KafkaSource（并行度 3）
    participant WM as 水位生成器

    P0->>SRC: o1(u1,120,@10:00:05)
    P1->>SRC: o2(u2, 80,@10:00:20)
    P2->>SRC: o3(u1, -5,@10:00:40)
    SRC->>WM: 提取每条事件的 ts 作为事件时间
    Note over WM: 分区内水位 = 本分区最大事件时间 − 5s<br/>⭐ 算子整体水位 = 各分区水位的【最小值】
    WM-->>SRC: watermark = min(10:00:00, 10:00:15, 10:00:35) = 10:00:00
    P0->>SRC: o4(u1,6000,@10:01:10)
    WM-->>SRC: ⭐ 水位跳到 10:01:05（受最慢分区影响仍取 min）
    Note over SRC: 水位跨过 10:01:00 → 触发窗口 [10:00, 10:01)
```

**关键配置逐行解释**（对照 §2.1 的代码）：

| 配置 | 例子中的值 | 为什么这么设 |
| --- | --- | --- |
| `setTopics("orders")` | 订阅 3 个分区的 topic | 分区数决定**读取并行度的上限** |
| `setStartingOffsets(...)` | `committedOffsets(EARLIEST)` | ⭐ 生产必须用这个：**优先续上次位点**，没有才回退 |
| `setGroupId("order-job")` | 消费组，用于提交位点 | 位点提交到 `__consumer_offsets` |
| `forBoundedOutOfOrderness(Duration.ofSeconds(5))` | 容忍 5 秒乱序 | ⭐ 按"到达时间 − 事件时间"的 **P99** 定 |
| `withTimestampAssigner((e, ts) -> e.getEventTime())` | 用事件自带的 `ts` | 决定**窗口按哪个时间切** |
| `withIdleness(Duration.ofMinutes(1))` | 1 分钟无数据标记空闲 | ⭐ 防止**某个分区空转拖住全局水位**（例子中 P2 若长期无数据，水位会卡住） |
| `env.getConfig().setAutoWatermarkInterval(200)` | 默认 200ms | 水位不是每条都发，而是**周期性生成** |

> [!warning] 例子里的一个典型陷阱
> 如果 **Partition 2 一直没有新数据**，它的水位就停在旧值 → `min(...)` 导致**整个算子的水位卡住** → 窗口永远不触发。
> 这就是必须配 `withIdleness()` 的原因——**多分区场景下"空闲分区拖死水位"是最常见的事故**。

### 2.2 便捷 Source（测试/示例用）

| 方法 | 用途 | 版本提示 |
| --- | --- | --- |
| ⭐ `env.fromData(T...)` | **从内存集合造流**（推荐） | **1.19+ 新增**，替代下面两个 |
| `env.fromElements(T...)` | 同上 | ⚠️ 1.19 起废弃，2.x 建议改用 `fromData` |
| `env.fromCollection(Collection)` | 同上 | ⚠️ 同上 |
| `env.fromSequence(start, end)` | 数字序列 | 有界 |
| `env.socketTextStream(host, port)` | Socket 调试 | 仅调试 |
| `env.fromSource(new DataGeneratorSource<>(...))` | 造数（生产压测） | ⭐ 推荐替代手写造数 |

> [!warning] `env.addSource(...)` 在 2.x **已移除**
> 1.x：
> ```java
> env.addSource(new FlinkKafkaConsumer<>("topic", new SimpleStringSchema(), props));
> ```
> 2.x：**`addSource` 不存在，必须写 `env.fromSource(kafkaSource, watermarkStrategy, name)`**。
> 迁移时最典型的编译错误就是 `SourceFunction` 找不到（见 [附录 B](#附录-b常见报错速查)）。

### 2.3 CDC Source

| 方式 | 写法 | 适用 |
| --- | --- | --- |
| **DataStream 层** | `MySqlSource.<String>builder()...build()` + `env.fromSource(...)` | 需要在下游写 DataStream 逻辑 |
| ⭐ **SQL 层**（更常用） | `'connector' = 'mysql-cdc'` DDL | 直接进 SQL 管道 |

详见 [[7-FlinkCDC与实时数仓]]。

---

## 三、Transformation：算子速查

```mermaid
flowchart TB
    ROOT(("DataStream 算子"))
    ROOT --> A["① 逐条转换<br/>map / flatMap / filter"]
    ROOT --> B["② 分组聚合<br/>keyBy → reduce / aggregate<br/>（⭐ 有状态）"]
    ROOT --> C["③ 合并拆分<br/>union / connect / sideOutput"]
    ROOT --> D["④ 双流关联<br/>join / coGroup / intervalJoin"]
    ROOT --> E["⑤ 分区控制<br/>rebalance / rescale / forward / shuffle / partitionCustom"]
    ROOT --> F["⑥ 自定义处理<br/>process（ProcessFunction）"]
    ROOT --> G["⑦ 窗口<br/>window / windowAll（见 §四）"]
```

### 3.1 常用算子与语义

| 算子 | 作用 | 是否 Keyed | 是否改分区 | 备注 |
| --- | --- | --- | --- | --- |
| `map` | 1 → 1 转换 | ✗ | ✗ | 可成链 |
| `flatMap` | 1 → N（含 0） | ✗ | ✗ | 拆分/过滤合一 |
| `filter` | 过滤 | ✗ | ✗ | — |
| ⭐ `keyBy(KeySelector)` | 按 key 分组 | ✅ **变 KeyedStream** | ✅ shuffle | ⚠️ **2.x 移除 `keyBy(0)` / `keyBy("field")`** |
| `reduce` | 滚动聚合 | ✅ 必须 | ✗ | 输入输出同类型 |
| ⭐ `aggregate(AggregateFunction)` | 增量聚合 | ✅ 必须 | ✗ | **比 reduce 灵活**（中间态与结果类型可不同） |
| `process(ProcessFunction)` | 底层 API | 可选 | ✗ | KeyedStream 上用 `KeyedProcessFunction` |
| `union` | 多流合并 | ✗ | ✗ | **类型必须相同** |
| `connect` | 两流连接 | ✗ | ✗ | 类型可不同，需 `CoProcessFunction` |
| `sideOutput` | 侧输出分流 | — | — | 见 3.3 |
| `join` / `coGroup` | 双流关联 | ✅ | ✅ | 基于窗口/状态 |
| `intervalJoin` | 区间 Join | ✅ | ✅ | ⭐ 状态更省，优先用它 |
| `rebalance` | 轮询分区 | ✗ | ✅ | 打散倾斜 |
| `rescale` | 局部轮询 | ✗ | ✅ | 比 rebalance 轻 |
| `forward` | 同并行度直传 | ✗ | ✗ | 上下游并行度必须一致 |
| `shuffle` | 随机分区 | ✗ | ✅ | — |
| `partitionCustom` | 自定义分区器 | ✗ | ✅ | ⚠️ 2.x 移除字段位置重载 |

### 用例子看：6 条订单是怎么被一步步处理的

#### ① 先看 `keyBy` 把数据路由到哪里

假设作业**并行度为 2**（两个子任务），`keyBy(userId)` 后：

```mermaid
flowchart LR
    subgraph SRC["输入（3 条正常数据）"]
        direction TB
        A1["o1 · u1 · 120"]
        A2["o2 · u2 · 80"]
        A3["o6 · u3 · 300"]
    end
    A1 -->|"hash(u1) % 2 = 0"| T1["子任务 0<br/>⭐ 拿到全部 u1 的数据"]
    A2 -->|"hash(u2) % 2 = 1"| T2["子任务 1<br/>⭐ 拿到全部 u2 的数据"]
    A3 -->|"hash(u3) % 2 = 1"| T2
    T1 --> N["✅ 同一个用户的订单必定进同一个子任务<br/>→ 才能做有状态聚合（这就是 keyBy 的意义）"]
    T2 --> N
```

> 💡 **核心**：`keyBy` 保证"**同一 key 的数据一定在同一并行子任务上处理**"，这是所有 Keyed State 的前提。分区数 ≠ key 数，多个 key 会共享一个子任务。

#### ② 再看每条事件到达后发生了什么（⭐ 这张表把水位/窗口/状态/侧输出全串起来了）

| 到达 | 事件 | 事件时间 | 最大事件时间 | 当前水位（−5s） | 发生了什么 |
| --- | --- | --- | --- | --- | --- |
| 1 | o1 · u1 · 120 | 10:00:05 | 10:00:05 | 10:00:00 | 通过 `filter` → `keyBy(u1)` → 计入窗口 `[10:00,10:01)`，**u1 累计 120** |
| 2 | o2 · u2 · 80 | 10:00:20 | 10:00:20 | 10:00:15 | 计入窗口，**u2 累计 80** |
| 3 | o3 · u1 · **−5** | 10:00:40 | 10:00:40 | 10:00:35 | ⚠️ **被 `filter` 丢弃**（金额 ≤ 0），不进窗口 |
| 4 | o4 · u1 · **6000** | 10:01:10 | 10:01:10 | **10:01:05** | ① 水位跨过 `10:01:00` → ⭐ **窗口 `[10:00,10:01)` 触发**，输出 `u1=120`、`u2=80`；② 该订单计入窗口 `[10:01,10:02)`；③ **金额 > 5000 → 侧输出告警** |
| 5 | o6 · u3 · 300 | 10:01:30 | 10:01:30 | 10:01:25 | 计入窗口 `[10:01,10:02)`，**u3 累计 300** |
| 6 | o5 · u2 · 200 | **10:00:50** | — | 10:01:25 | ⚠️ **迟到**：它属于窗口 `[10:00,10:01)`，但该窗口已在第 4 步触发且 `allowedLateness=0` → ⭐ **进侧输出 `late-data`**，不静默丢弃 |

```mermaid
flowchart TB
    subgraph T0["t=10:00:05 ~ 10:00:35（水位还没到 10:01:00）"]
        direction LR
        E1["o1 u1 120"] --> W1["窗口[10:00,10:01)<br/>u1: 120"]
        E2["o2 u2 80"] --> W1b["窗口[10:00,10:01)<br/>u2: 80"]
        E3["o3 u1 -5"] --> X1["🗑️ filter 丢弃"]
    end
    subgraph T1["t=10:01:10 o4 到达 → 水位跳到 10:01:05"]
        direction LR
        E4["o4 u1 6000"] --> TRIG["⭐ 水位跨过 10:01:00<br/>窗口[10:00,10:01) 触发！"]
        TRIG --> OUT1["输出：u1=120<br/>u2=80"]
        E4 --> W2["窗口[10:01,10:02)<br/>u1: 6000"]
        E4 -.->|"amount 大于 5000"| BIG["侧输出：大额告警"]
    end
    subgraph T2["t=10:01:30 之后"]
        E5["o6 u3 300"] --> W2b["窗口[10:01,10:02)<br/>u3: 300"]
        E6["o5 u2 200<br/>（事件时间 10:00:50）"] -.->|"⭐ 迟到"| LATE["侧输出：late-data"]
    end
```

> [!important] 从这张表能学到的 4 件事
> ① **窗口不会"到点自动触发"**——它靠**水位推进**触发（第 4 条事件才把窗口顶出去）；
> ② **水位 = 最大事件时间 − 容忍度**，且多分区取 `min`；
> ③ **迟到数据的判定基准是水位**，不是"到达时间晚不晚"；
> ④ **侧输出是"不丢数据"的关键**——大额告警和迟到数据都不该被主流程吞掉。

#### ③ 最终输出长什么样

```
=========== 窗口 [10:00, 10:01) 触发 ===========
u1  120.00   （o1；o3 被过滤）
u2   80.00   （o2；o5 迟到未计入）
=========== 侧输出 ===========
[big-order]  u1  6000.00  @10:01:10    ← 大额告警
[late-data]  u2   200.00  @10:00:50    ← 迟到数据（可补偿）
=========== 窗口 [10:01, 10:02) 待水位推进后触发 ===========
u1  6000.00
u3   300.00
```

### 3.2 分组聚合三种写法

```java
// ① reduce：输入输出同类型（最简）
stream.keyBy(Order::getUserId)
      .reduce((a, b) -> new Order(a.getUserId(), a.getAmount() + b.getAmount()));

// ② ⭐ aggregate：增量聚合（推荐，状态小、性能好）
stream.keyBy(Order::getUserId)
      .aggregate(new AggregateFunction<Order, BigDecimal, BigDecimal>() {
          public BigDecimal createAccumulator() { return BigDecimal.ZERO; }
          public BigDecimal add(Order o, BigDecimal acc) { return acc.add(o.getAmount()); }
          public BigDecimal getResult(BigDecimal acc) { return acc; }
          public BigDecimal merge(BigDecimal a, BigDecimal b) { return a.add(b); }
      });

// ③ process：要拿到窗口元信息 + 全量数据时（状态最大，慎用）
stream.keyBy(Order::getUserId)
      .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
      .process(new ProcessWindowFunction<Order, Result, Long, TimeWindow>() {
          public void process(Long key, Context ctx, Iterable<Order> elems, Collector<Result> out) {
              // ctx.window() 拿到窗口起止；elems 是窗口内全量数据（⚠️ 状态成本高）
          }
      });

// ④ ⭐ aggregate + ProcessWindowFunction：既增量聚合、又能拿窗口元信息（最佳组合）
stream.keyBy(Order::getUserId)
      .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
      .aggregate(new AmountAggregate(), new ResultProcessWindowFunction());
```

### 3.3 侧输出流（分流不丢数据）

```java
// 定义标签
OutputTag<Order> LATE = new OutputTag<Order>("late-data") {};

SingleOutputStreamOperator<Result> main = stream
        .keyBy(Order::getUserId)
        .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
        .allowedLateness(Duration.ofSeconds(30))
        .sideOutputLateData(LATE)                   // ⭐ 迟到数据进侧流
        .aggregate(new AmountAggregate());

DataStream<Order> late = main.getSideOutput(LATE);  // 取出侧流
late.sinkTo(lateSink);                               // 单独处理（补算/告警）
```

### 3.4 双流 Join 三种写法对比

| 方式 | 状态成本 | 语义 | 推荐度 |
| --- | --- | --- | --- |
| `join`（窗口 Join） | 高（窗口内全量） | 内连接，仅窗口内匹配 | 中 |
| ⭐ `intervalJoin` | 中（按区间保留） | 按时间区间关联 + 可选外连接 | ⭐ **优先** |
| `coGroup` | 高 | 完全控制，可做外连接 | 特殊需求 |
| ⭐ **SQL Regular Join / Lookup Join / Window Join** | 看写法 | 表达力最强 | ⭐ **能用 SQL 就用 SQL** |

详见 [[8-FlinkSQL与TableAPI]] §六、§七。

---

## 四、窗口 API

### 4.1 窗口 API 的组成

```mermaid
flowchart LR
    A["KeyedStream"] --> B["① WindowAssigner<br/>窗口分配器"]
    B --> C["② Trigger（可选）<br/>何时触发计算"]
    C --> D["③ Evictor（可选）<br/>触发前剔除元素"]
    D --> E["④ WindowFunction<br/>reduce / aggregate / process"]
    E --> F["⑤ 迟到数据处理<br/>allowedLateness + sideOutput"]
```

### 用例子看：同一批订单被三种窗口切出来是什么样

还是案例里的数据（o1@10:00:05、o2@10:00:20、o3@10:00:40、o5@10:00:50、o4@10:01:10、o6@10:01:30）：

```mermaid
flowchart TB
    subgraph TL["⏱️ 事件时间轴"]
        direction LR
        T1["10:00:00"] --> T2["10:00:30"] --> T3["10:01:00"] --> T4["10:01:30"] --> T5["10:02:00"]
    end
    EV["事件落点：<br/>o1 ─┘10:00:05<br/>o2 10:00:20<br/>o3 10:00:40<br/>o5 10:00:50<br/>o4 10:01:10<br/>o6 10:01:30"]
```

| 窗口类型 | 切法 | 上面数据会被切成 | 特点 |
| --- | --- | --- | --- |
| **滚动 Tumbling**（例子用的）<br/>`TumblingEventTimeWindows.of(Duration.ofMinutes(1))` | 1 分钟一段，**不重叠** | `[10:00,10:01)`：o1 o2 o3 o5<br/>`[10:01,10:02)`：o4 o6 | ⭐ 每事件**只属于一个窗口**；最常用 |
| **滑动 Sliding**<br/>`of(Duration.ofMinutes(1), Duration.ofSeconds(30))` | 每 30 秒起一个 1 分钟窗口，**有重叠** | `[10:00:00,10:01:00)`：o1 o2 o3 o5<br/>`[10:00:30,10:01:30)`：o3 o5 o4 o6<br/>`[10:01:00,10:02:00)`：o4 o6 | ⚠️ **一个事件属于多个窗口** → 计算结果数 = 窗口数，状态 ×N |
| **会话 Session**<br/>`EventTimeSessionWindows.withGap(Duration.ofSeconds(30))` | 按**活跃间隔**切：gap 内没数据就结束 | o1~o5 间隔都 < 30s → 一个会话 `[10:00:05,10:01:20)`（含 o1 o2 o3 o5 o4）<br/>o6 距 o5 有 40s > 30s → 另一个会话 | 窗口**大小不固定**，由数据驱动 |

```mermaid
flowchart LR
    subgraph ROLL["滚动：切西瓜（不重叠）"]
        R1["[10:00,10:01)"] --- R2["[10:01,10:02)"]
    end
    subgraph SLIDE["滑动：两张网错开铺（重叠）"]
        S1["窗口A 10:00~10:01"] -.->|重叠 30s| S2["窗口B 10:00:30~10:01:30"]
        S2 -.-> S3["窗口C 10:01~10:02"]
    end
    subgraph SESS["会话：按『说话停顿』切"]
        SS1["会话1<br/>10:00:05~10:01:20"]
        SS2["会话2<br/>10:01:30~…"]
        SS1 -.->|"停顿 40s 大于 gap 30s"| SS2
    end
```

> [!warning] 选了滑动窗口要意识到的事
> 例子中 o3、o5、o4 都落在**两个窗口**里 → **它们会被计算两次**（这是滑动窗口的语义，不是 bug）。
> 副作用：① 输出条数变多；② 状态量约为滚动窗口的 **窗口大小 / 滑动步长** 倍。所以滑动窗口要谨慎用于大状态场景。

### 4.2 窗口分配器速查（⚠️ `Time` → `Duration`）

| 类型 | 1.20 及以前（旧写法） | ⭐ **2.x / 推荐写法** |
| --- | --- | --- |
| 滚动（事件时间） | `TumblingEventTimeWindows.of(Time.minutes(5))` | ⭐ `TumblingEventTimeWindows.of(Duration.ofMinutes(5))` |
| 滑动（事件时间） | `SlidingEventTimeWindows.of(Time.minutes(10), Time.minutes(1))` | ⭐ `SlidingEventTimeWindows.of(Duration.ofMinutes(10), Duration.ofMinutes(1))` |
| 会话（事件时间） | `EventTimeSessionWindows.withGap(Time.minutes(5))` | ⭐ `EventTimeSessionWindows.withGap(Duration.ofMinutes(5))` |
| 滚动（处理时间） | `TumblingProcessingTimeWindows.of(Time.seconds(10))` | ⭐ `...of(Duration.ofSeconds(10))` |
| 全局窗口 | `.window(GlobalWindows.create())` + 自定义 Trigger | 同 |
| 计数窗口 | `.countWindow(100)` / `.countWindow(100, 10)` | 同（快捷方法） |

> [!warning] DataStream 窗口 API 的现状
> 1.14 起 `Time` 被 `Duration` 取代；**2.x 里 `Time` 已废弃**。
> 另外**新项目更推荐用 SQL 的窗口 TVF**（`TUMBLE` / `HOP` / `CUMULATE` / `SESSION`）——它自带算子优化（mini-batch、状态清理），详见 [[8-FlinkSQL与TableAPI]] §四。

### 4.3 完整窗口写法模板

```java
DataStream<Result> result = stream
        .keyBy(Order::getUserId)
        .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
        .allowedLateness(Duration.ofSeconds(30))            // ⭐ 迟到数据再给机会
        .sideOutputLateData(LATE_TAG)                        // ⭐ 超出容忍的进侧流
        .trigger(ContinuousEventTimeTrigger.of(Duration.ofSeconds(10)))  // 可选：提前触发
        .evictor(CountEvictor.of(100))                       // 可选：只保留最后 100 条
        .aggregate(new AmountAggregate(), new ResultProcessWindowFunction());
```

| 配置 | 作用 | 常见取值 |
| --- | --- | --- |
| `allowedLateness` | 窗口触发后再保留一段时间，迟到数据仍可更新结果 | 10s~1min（电商），分钟级（金融对账） |
| `sideOutputLateData` | 超出容忍的数据进侧流 | 必配（否则静默丢弃） |
| `Trigger` | 何时触发窗口计算 | 默认事件时间水位触发；`ContinuousEventTimeTrigger` 可提前 |
| `Evictor` | 触发前剔除元素 | 少用（有状态成本） |

> 迟到的三层保障（水位 P99 + allowedLateness + 侧输出）详见 [[2-时间与窗口]]。

---

## 五、状态与定时器 API

### 5.1 状态类型速查

| 状态类型 | 存什么 | 获取方式 |
| --- | --- | --- |
| `ValueState<T>` | 单值（累计值、标志位） | `getRuntimeContext().getState(new ValueStateDescriptor<>("n", T.class))` |
| `ListState<T>` | 列表（最近 N 条） | `getListState(new ListStateDescriptor<>("n", T.class))` |
| `MapState<K,V>` | 映射（去重集合、关联表） | `getMapState(new MapStateDescriptor<>("n", K.class, V.class))` |
| `ReducingState<T>` | 滚动聚合 | `getReducingState(new ReducingStateDescriptor<>("n", reduceFn, T.class))` |
| `AggregatingState<I,O>` | 增量聚合 | `getAggregatingState(...)` |
| ⭐ **`MapState` 替代大 Map** | **不要用 `ValueState<Map<...>>`** | 见 §13 迁移坑 |

### 5.2 KeyedProcessFunction 模板（状态 + 定时器）

```java
public class OrderMonitor extends KeyedProcessFunction<Long, Order, Alert> {

    private transient ValueState<Long> countState;
    private transient MapState<String, Long> lastSeenState;

    // ⭐ 2.x 签名是 open(OpenContext)；1.x 是 open(Configuration)
    @Override
    public void open(OpenContext ctx) {
        ValueStateDescriptor<Long> d = new ValueStateDescriptor<>("count", Long.class);
        // TTL：⚠️ 2.x 用 Duration，1.x 用 Time
        d.enableTimeToLive(StateTtlConfig.newBuilder(Duration.ofHours(24))
                .setUpdateType(StateTtlConfig.UpdateType.OnReadAndWrite)
                .setStateVisibility(StateTtlConfig.StateVisibility.NeverReturnExpired)
                .build());
        countState = getRuntimeContext().getState(d);
        lastSeenState = getRuntimeContext().getMapState(
                new MapStateDescriptor<>("lastSeen", String.class, Long.class));
    }

    @Override
    public void processElement(Order o, Context ctx, Collector<Alert> out) throws Exception {
        Long c = countState.value();
        c = (c == null ? 1L : c + 1);
        countState.update(c);
        lastSeenState.put(o.getChannel(), ctx.timestamp());

        // ⭐ 注册事件时间定时器（水位过了这个时间就会回调 onTimer）
        ctx.timerService().registerEventTimeTimer(ctx.timestamp() + 60_000);
        // 处理时间定时器：registerProcessingTimeTimer(System.currentTimeMillis() + 60000)

        if (c > 100) out.collect(new Alert(o.getUserId(), "高频下单", c));
    }

    @Override
    public void onTimer(long ts, OnTimerContext ctx, Collector<Alert> out) throws Exception {
        countState.clear();                 // ⭐ 定时器里记得清理，否则状态膨胀
        out.collect(new Alert(ctx.getCurrentKey(), "窗口结束", ts));
    }
}
```

```mermaid
flowchart LR
    A["processElement<br/>（每条数据）"] --> B["读写状态<br/>ValueState / MapState"]
    B --> C["注册定时器<br/>registerEventTimeTimer"]
    C --> D["水位推进过定时器时间"]
    D --> E["onTimer 回调"]
    E --> F["⭐ 清理状态<br/>（防状态膨胀）"]
```

> [!warning] 三个高频坑
> ① **定时器必须在 `onTimer` 里清理状态**，否则状态只增不减（[[3-状态管理]]）；
> ② **`ValueState<Map<K,V>>` 是大坑**：Flink 2.x 迁移时这类泛型集合状态**序列化不兼容**，且内存效率差 → **改用 `MapState`**；
> ③ **TTL 只管"读过/写过"的 key**，不会让 Checkpoint 立刻变小（[[13-生产部署Checklist逐项解析]]）。

### 用例子看：状态和定时器在数据流里怎么变

需求 4 是"维护每个用户的**累计消费**，30 分钟无数据就清空"。用 `ValueState<BigDecimal>` + 定时器实现：

```mermaid
flowchart TB
    A["o1 u1 120 到达"] --> B["countState(u1).value() = null<br/>→ update(120.0)<br/>注册定时器 t=事件时间+30min"]
    B --> C["o4 u1 6000 到达"]
    C --> D["countState(u1).value() = 120.0<br/>→ update(6120.0)<br/>⭐ 重置定时器（删旧的、注册新的）"]
    D --> E["10:01:10 + 30min = 10:31:10 之前<br/>u1 再没有数据"]
    E --> F["⏰ 水位推进到 10:31:10<br/>→ onTimer 回调"]
    F --> G["输出 u1 累计 6120.0<br/>⭐ countState(u1).clear() 清理状态"]
    style F fill:#fff3cd,stroke:#e0a800
    style G fill:#d4edda
```

**状态值的逐条演化**（这就是"有状态计算"的本质）：

| 到达事件 | `countState(u1)` | `countState(u2)` | `countState(u3)` | 说明 |
| --- | --- | --- | --- | --- |
| （初始） | 空 | 空 | 空 | 每个 key 独立一份状态 |
| o1 u1 120 | **120.0** | 空 | 空 | 首次写入 |
| o2 u2 80 | 120.0 | **80.0** | 空 | 互不影响 |
| o3 u1 −5 | 120.0 | 80.0 | 空 | ⚠️ 已被 filter 丢弃，**不会进来** |
| o4 u1 6000 | **6120.0** | 80.0 | 空 | 累加 |
| o6 u3 300 | 6120.0 | 80.0 | **300.0** | 新 key 出现 → **状态条目 +1** |
| ⏰ 30min 后 | **被 clear** | 保留 | 保留 | 只有 u1 超时（其他用户后续还有数据） |

```mermaid
flowchart LR
    subgraph STATES["Keyed State 是『按 key 分片的']"]
        direction TB
        S1["u1 → ValueState: 6120.0<br/>+ 定时器 10:31:10"]
        S2["u2 → ValueState: 80.0<br/>+ 定时器 10:30:50"]
        S3["u3 → ValueState: 300.0<br/>+ 定时器 10:31:30"]
    end
    STATES --> NOTE["⚠️ key 越多 → 状态条目越多<br/>这正是 CEP/去重/Join 状态膨胀的同源问题<br/>→ 必须配 TTL 或超时清理"]
```

> [!important] 三个必须记住的点
> ① **状态是"按 key 分片"的**：`u1` 的状态和 `u2` 的状态互不可见（这就是 `getRuntimeContext()` 能直接拿到"当前 key 的状态"的原因）；
> ② ⭐ **定时器要"重置"**：每条新数据都应删掉旧定时器、注册新定时器，否则会在错误的时间触发；
> ③ ⭐ **`onTimer` 里必须 `clear()`**：不清理就永远留着 → 状态只增不减。**"任何长期运行的作业都必须有状态退出机制"**（详见 [[3-状态管理]]、[[13-生产部署Checklist逐项解析]]）。

### 5.3 广播状态（BroadcastState）

| 场景 | 模式 |
| --- | --- |
| 动态规则/配置下发 | 一条广播流（规则）+ 一条业务流 → `BroadcastProcessFunction` |
| 注意 | ⚠️ 广播状态在**运行时只读**（只能在广播侧修改）；Checkpoint 需 `MapStateDescriptor` 一致 |

---

## 六、Watermark API

```java
// ① 有界乱序（最常用）
WatermarkStrategy.<Order>forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((e, ts) -> e.getEventTime());

// ② 单调递增（理想情况）
WatermarkStrategy.<Order>forMonotonousTimestamps()
        .withTimestampAssigner((e, ts) -> e.getEventTime());

// ③ 不生成水位（处理时间语义）
WatermarkStrategy.noWatermarks();

// ④ ⭐ 多分区空闲问题：某个分区长时间无数据会拖住全局水位
WatermarkStrategy.<Order>forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((e, ts) -> e.getEventTime())
        .withIdleness(Duration.ofMinutes(1));      // 标记空闲分区
```

| 要点 | 说明 |
| --- | --- |
| 水位怎么设 | 统计"到达时间 − 事件时间"分布，**取 P99**（[[2-时间与窗口]]） |
| 多输入取 min | 算子有多个输入时，水位取**最小值** |
| 生成周期 | `env.getConfig().setAutoWatermarkInterval(200)`（默认 200ms） |
| ⭐ **2.x 变化** | `Time` → **`Duration`**；`TimeCharacteristic` **移除**（只剩事件时间语义） |

---

## 七、Sink：输出

### 7.1 Sink V2（1.12+，2.x 唯一方式）

```java
// ① Kafka（Exactly-Once 两阶段提交）
KafkaSink<String> kafkaSink = KafkaSink.<String>builder()
        .setBootstrapServers("localhost:9092")
        .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                .setTopic("out-topic")
                .setValueSerializationSchema(new SimpleStringSchema())
                .build())
        .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
        .setTransactionalIdPrefix("my-app-tx-")     // ⭐ EOS 必填
        .setProperty("transaction.timeout.ms", "900000")  // 需 ≤ broker 的 max.transaction.timeout.ms
        .build();
stream.sinkTo(kafkaSink);

// ② 文件（FileSink，天然 Exactly-Once）
FileSink<String> fileSink = FileSink
        .forRowFormat(new Path("s3://bucket/out"), new SimpleStringEncoder<String>("UTF-8"))
        .withRollingPolicy(DefaultRollingPolicy.builder()
                .withMaxPartSize(MemorySize.ofMebiBytes(128))
                .withRolloverInterval(Duration.ofMinutes(10))
                .build())
        .withBucketAssigner(new DateTimeBucketAssigner<>("yyyy-MM-dd/HH"))
        .build();
stream.sinkTo(fileSink);

// ③ 调试：打印到标准输出
stream.print("debug");           // 或 .printToErr()
```

### 用例子看：写 Kafka 的"两阶段提交"到底在做什么

需求 8 要把窗口结果写回 Kafka，并且要求 **Exactly-Once**。下面是它和 Checkpoint 配合的完整过程：

```mermaid
sequenceDiagram
    autonumber
    participant JM as JobManager<br/>（Checkpoint 协调器）
    participant SINK as KafkaSink
    participant KAFKA as Kafka（事务）
    participant APP as 上游算子（窗口聚合）

    Note over SINK,KAFKA: ① 预提交阶段
    APP->>SINK: 窗口[10:00,10:01) 结果：u1=120, u2=80
    SINK->>KAFKA: beginTransaction()（开启事务）
    SINK->>KAFKA: send(u1=120)、send(u2=80)<br/>⭐ 消息写入但【未提交】，下游消费者看不到
    JM->>SINK: 注入 barrier（触发 Checkpoint）
    SINK->>KAFKA: ⭐ flush + 预提交（pre-commit）事务
    SINK-->>JM: 反馈：我的状态快照完成
    Note over JM: 等所有算子都反馈完成

    Note over JM,KAFKA: ② 提交阶段
    JM-->>SINK: ⭐ Checkpoint 全局成功
    SINK->>KAFKA: commitTransaction()（真正提交）
    Note over KAFKA: 此刻下游才能读到这两条结果 ✅

    Note over SINK,KAFKA: ③ 失败会怎样
    JM-->>SINK: Checkpoint 失败 / 作业重启
    SINK->>KAFKA: ⭐ abortTransaction()（回滚未提交消息）
    Note over KAFKA: 消息被丢弃 → 从上次成功的 Checkpoint 重放<br/>✅ 不重（没提交）+ 不丢（会重算重发）
```

| 关键点 | 说明 |
| --- | --- |
| ⭐ **必须配 `transactionalIdPrefix`** | 否则无法开启事务，直接报错 |
| ⭐ **事务超时必须 ≤ broker 上限** | `transaction.timeout.ms`（默认 15min）要 ≤ broker 的 `transaction.max.timeout.ms`（默认 15min），否则事务被 broker 终止 |
| **提交时机** | 由 **Checkpoint 成功**驱动（不是每条消息都提交）→ 所以 `Checkpoint 间隔` = **数据可见延迟** |
| **消费端要求** | 下游要读已提交数据，需 `isolation.level=read_committed` |
| ❌ 不支持事务的 Sink | 只能靠**幂等写**（`INSERT ... ON DUPLICATE KEY UPDATE`）——例如 JDBC |

> [!warning] 端到端 Exactly-Once 的三段式（缺一不可）
> **① Source 位点可重放**（Kafka offset 随 Checkpoint 保存）+ **② 内部状态快照**（Checkpoint 开启）+ **③ Sink 事务或幂等**。
> 例子里的 `orders → 窗口聚合 → order-stats` 满足这三条，所以是真正的端到端 EOS。
> 详见 [[11-端到端一致性]]、[[4-容错与ExactlyOnce]]。

### 7.2 常见 Sink 与一致性

| Sink | 写法 | Exactly-Once | 备注 |
| --- | --- | --- | --- |
| **Kafka** | `KafkaSink` + `sinkTo` | ✅（两阶段提交） | 需 `transactionalIdPrefix` |
| ⭐ **文件 / 对象存储** | `FileSink` | ✅（提交时原子 rename） | 推荐 HDFS/S3 |
| **JDBC / MySQL** | `JdbcSink.sink(sql, builder, execOpts, connOpts)` | ⚠️ **至少要幂等**（`INSERT ... ON DUPLICATE KEY UPDATE`） | ⚠️ **2.x 尚无官方 JDBC connector 版本** |
| **Elasticsearch** | `Elasticsearch7SinkBuilder` | ⚠️ 幂等（按 doc id 覆盖） | — |
| **Doris** | `DorisSink.doris(...)` | ✅（两阶段提交） | 需 `flink-doris-connector` |
| `print` / `printToErr` | 标准输出 | ✗ | 仅调试 |

> [!important] 端到端 Exactly-Once 的前提
> **① Source 可重放**（Kafka 位点）+ **② 内部 Checkpoint 开启** + **③ Sink 支持事务或幂等**——三者缺一不可。
> 详见 [[11-端到端一致性]]、[[4-容错与ExactlyOnce]]。

> ⚠️ `stream.addSink(...)` 在 2.x **已移除**（`SinkFunction` 没了），必须用 `sinkTo(Sink)`。

---

## 八、异步 I/O（Async I/O）

```java
// 把"一条一条同步查外部系统"改成"并发批量查"
DataStream<Enriched> enriched = AsyncDataStream.unorderedWait(
        orders,
        new AsyncDatabaseRequest(),   // 实现 AsyncFunction
        5, TimeUnit.SECONDS,          // ⭐ 超时（超时走异常或降级）
        100);                         // ⭐ 最大并发请求数（capacity）

// 有序版本（结果顺序与输入一致，延迟更高）
AsyncDataStream.orderedWait(orders, fn, 5, TimeUnit.SECONDS, 100);
```

```java
public class AsyncDatabaseRequest extends RichAsyncFunction<Order, Enriched> {
    private transient DbClient client;

    @Override
    public void open(OpenContext ctx) {          // 1.x：open(Configuration)
        client = new DbClient();                  // ⭐ 连接池在 open 里初始化
    }

    @Override
    public void asyncInvoke(Order o, ResultFuture<Enriched> future) {
        client.query(o.getUserId())
              .whenComplete((r, e) -> {
                  if (e != null) future.completeExceptionally(e);
                  else future.complete(Collections.singleton(new Enriched(o, r)));
              });
    }

    @Override
    public void timeout(Order o, ResultFuture<Enriched> future) {
        future.complete(Collections.emptyList());  // ⭐ 超时降级：丢弃或补默认值
    }
}
```

| 参数 | 含义 | 建议 |
| --- | --- | --- |
| `timeout` | 单请求超时 | 略大于下游 P99；必配 `timeout()` 降级 |
| `capacity` | 并发上限 | ⭐ **注意下游连接池要 ≥ capacity**，否则请求排队 |
| `unorderedWait` vs `orderedWait` | 是否保序 | 不要求顺序就用 unordered（延迟低、吞吐高） |
| ⚠️ 前提 | 用**异步客户端** | 同步客户端套异步 IO **无效**（照样阻塞） |

---

### 用例子看：补"用户等级"这件事，同步和异步差多少

需求 7 要给每条结果补上用户等级（查维表，**单次耗时 50ms**）。假设一波来了 100 条结果：

```mermaid
sequenceDiagram
    autonumber
    participant OP as 算子线程
    participant DB as 维表（MySQL，每次 50ms）

    Note over OP,DB: ❌ 同步查询：一条一条排队
    OP->>DB: 查 u1（等 50ms）
    DB-->>OP: 等级 A
    OP->>DB: 查 u2（等 50ms）
    DB-->>OP: 等级 B
    OP->>DB: 查 u3（等 50ms）
    DB-->>OP: 等级 C
    Note over OP: 100 条 × 50ms = 5 秒（且期间算子一直阻塞）<br/>💥 吞吐被下游拖死，还会引发背压

    Note over OP,DB: ✅ 异步查询：100 个请求并发发出
    OP->>DB: 同时发出 u1,u2,u3 … 共 100 个请求
    DB-->>OP: 50ms 后陆续全部返回
    Note over OP: 总耗时 ≈ 50ms（并发度受 capacity 限制）<br/>✅ 吞吐提升约 100 倍
```

| 对比项 | 同步（`map` + JDBC） | ⭐ 异步（`AsyncDataStream`） |
| --- | --- | --- |
| 100 条 × 50ms | **约 5 秒**（串行） | **约 50ms**（并发） |
| 线程占用 | 算子线程全程阻塞 | 算子线程**不阻塞**，只发请求 |
| 背压风险 | 高（下游慢 → 拖垮上游） | 低 |
| 前提 | — | ⭐ **必须是异步客户端**（Netty/CompletableFuture） |

```mermaid
flowchart LR
    subgraph SYNC["❌ 同步"]
        direction LR
        S1["事件1"] -->|50ms| S2["事件2"] -->|50ms| S3["事件3"] -->|50ms| S4["…"]
    end
    subgraph ASYNC["✅ 异步 unorderedWait capacity=100"]
        direction LR
        A1["事件1"] --> P["并发发出<br/>（不等结果）"]
        A2["事件2"] --> P
        A3["事件3"] --> P
        P -->|"50ms 后一起回来"| R["结果（顺序可能乱）"]
    end
```

> [!warning] 用异步 I/O 时最容易踩的两个坑
> ① ⭐ **`capacity` 必须 ≤ 下游连接池大小**：设 100 但连接池只有 10，请求会在池子里排队，等于白开并发；
> ② ⭐ **同步客户端套异步 I/O 是无效的**：如果 `asyncInvoke` 里调用的是阻塞 JDBC，那么它照样占住线程，异步框架救不了你——**必须换异步客户端**（如 R2DBC、异步 HTTP 客户端）。
> 另外**一定要实现 `timeout()`** 做降级，否则下游抖动会把算子拖死。

## 九、容错配置 API

```java
// ① 开启 Checkpoint
env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);

// ② CheckpointConfig 全量配置
CheckpointConfig cp = env.getCheckpointConfig();
cp.setCheckpointTimeout(10 * 60_000);                        // 超时（建议 ≥ 间隔 × 3）
cp.setMinPauseBetweenCheckpoints(30_000);                    // ⭐ 两次 CK 最小间隔
cp.setMaxConcurrentCheckpoints(1);                           // ⭐ 必须 1
cp.setTolerableCheckpointFailureNumber(3);                   // 容忍几次失败
cp.setExternalizedCheckpointRetention(
        ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION);  // 取消时保留
cp.setCheckpointStorage("s3://bucket/flink/ckp");            // Checkpoint 存储
cp.enableUnalignedCheckpoints();                             // 背压下：非对齐 CK
cp.setAlignedCheckpointTimeout(Duration.ofSeconds(30));      // 对齐超时后转非对齐

// ③ 重启策略（⚠️ 2.x：env.setRestartStrategy 已移除 → 走配置）
// 1.x 写法（2.x 不再可用）：
// env.setRestartStrategy(RestartStrategies.fixedDelayRestart(3, Duration.ofSeconds(10)));
```

```properties
# 2.x：重启策略改为配置项（config.yaml）
restart-strategy:
  type: fixed-delay
  attempts: 3
  delay: 10s
# 其它类型：exponential-delay / failure-rate / none
```

| 配置项 | 推荐值 | 说明 |
| --- | --- | --- |
| `checkpointing.interval` | ≥ 1min | 太小抢资源，太大故障回退多 |
| `checkpointing.timeout` | ≥ 间隔 × 3 | 容忍抖动 |
| `min-pause-between` | 30s~1min | 避免 CK 连轴转 |
| `max-concurrent-checkpoints` | **1** | >1 会放宽一致性 |
| `tolerable-failed-checkpoints` | 3 | 别一次失败就挂作业 |
| 状态后端 | 大状态用 **RocksDB**；2.x 可用 **ForSt**（存算分离） | [[3-状态管理]] |

> 生产配置清单详见 [[13-生产部署Checklist逐项解析]]。

---

### 用例子看：作业挂了，数据会不会丢/重

假设例子作业在**窗口 `[10:01,10:02)` 还没触发时**崩了：

```mermaid
sequenceDiagram
    autonumber
    participant JOB as order-stats-job
    participant CK as Checkpoint 存储<br/>（S3）
    participant KAFKA as Kafka

    Note over JOB: t=10:01:25 触发 Checkpoint #7
    JOB->>CK: 保存快照：<br/>① Kafka 位点（orders 各分区 offset）<br/>② 窗口状态：窗口[10:01,10:02) 的 u1=6000<br/>③ Keyed State：u1 累计 6120
    CK-->>JOB: ✅ Checkpoint #7 成功
    Note over JOB: 继续处理…… t=10:01:40
    JOB--xJOB: 💥 某个 TaskManager 挂了

    Note over JOB: 按重启策略重启（如 fixed-delay 3 次）
    JOB->>CK: ⭐ 找最近一次成功的 Checkpoint（#7）
    CK-->>JOB: 返回快照
    JOB->>JOB: 恢复状态：窗口状态、Keyed State、Kafka 位点
    JOB->>KAFKA: 从 Checkpoint #7 记录的位点【重新消费】
    Note over JOB,KAFKA: t=10:01:25 ~ 10:01:40 的数据会【重放】<br/>但状态已恢复到 #7 → 计算结果正确（不重不丢）
```

| 问题 | 答案 |
| --- | --- |
| 会丢数据吗 | ❌ 不会：**位点也随 Checkpoint 保存**，恢复后从上次成功位点重放 |
| 会重复吗 | ⚠️ 内部计算不会（状态已回滚到一致点）；**但 Sink 端可能重复** → 靠**事务或幂等**解决 |
| 回退多少数据 | ≈ `Checkpoint 间隔` + 处理延迟 —— 所以**间隔太大 = 恢复时要重算很久** |
| 为什么间隔不能太小 | 太频繁会抢资源、拖慢吞吐；推荐 **≥ 1min**，且 `max-concurrent-checkpoints=1` |

```mermaid
flowchart LR
    A["正常运行"] -->|"每隔 60s"| B["Checkpoint<br/>（保存状态+位点）"]
    B --> A
    A -->|"💥 故障"| C["重启（重启策略）"]
    C --> D["从最近成功 Checkpoint 恢复状态"]
    D --> E["从保存的位点重放数据"]
    E --> A
    B -.->|"⭐ 没 Checkpoint = 只能从头重跑"| F["⚠️ 这就是为什么 Checkpoint 是生产必开项"]
```

> [!important] 三个配置的因果链（用例子理解）
> `enableCheckpointing(60_000)` → 决定**故障时最多回退 1 分钟的数据**；
> `setCheckpointTimeout(10min)` → 大状态要给它足够时间（≥ 间隔 × 3）；
> `setMinPauseBetweenCheckpoints(30s)` → 避免 Checkpoint 连轴转把流量挤掉。
> 生产配置清单见 [[13-生产部署Checklist逐项解析]]，原理见 [[5-Checkpoint与Savepoint]]。

## 十、Table/SQL API 与 DataStream 互转

```mermaid
flowchart LR
    DS["DataStream&lt;T&gt;"] -->|"fromDataStream / createTemporaryView"| TB["Table"]
    TB -->|"toDataStream / toChangelogStream"| DS
    CDC["CDC / Upsert 流"] -->|"fromChangelogStream"| TB
```

```java
// ① DataStream → Table
Table t1 = tEnv.fromDataStream(orders, $("orderId"), $("userId"), $("amount"),
        $("ts").rowtime());                       // ⭐ 用 .rowtime() 声明事件时间列
tEnv.createTemporaryView("orders_view", orders, $("userId"), $("amount"));  // 或注册成视图

// ② Table → DataStream
DataStream<Row> ds = tEnv.toDataStream(table);
DataStream<Row> changelog = tEnv.toChangelogStream(table);   // ⭐ 保留 +I/-U/+U/-D 语义
// ③ Changelog → Table（比如 CDC 结果再回灌）
Table back = tEnv.fromChangelogStream(changelog);

// ④ 查询
Table r1 = tEnv.sqlQuery("SELECT userId, SUM(amount) FROM orders_view GROUP BY userId");
Table r2 = tEnv.from("orders_view").filter($("amount").isGreater(100)).groupBy($("userId"))
        .select($("userId"), $("amount").sum().as("total"));
```

| 需求 | API |
| --- | --- |
| 拿流做 SQL | `fromDataStream` / `createTemporaryView` |
| 取回流继续写 DataStream 逻辑 | `toDataStream` / `toChangelogStream` |
| 保留更新语义（聚合结果） | ⭐ **`toChangelogStream`** |
| UDF | `createTemporarySystemFunction` + `call()`；或 SQL 里注册 |
| 窗口聚合 | ⭐ **窗口 TVF**：`TABLE(TUMBLE(TABLE t, DESCRIPTOR(ts), INTERVAL '1' MINUTE))` |
| 去重 | `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...) = 1` |
| 维表 | `FOR SYSTEM_TIME AS OF a.proc_time AS b`（Lookup Join） |

> [!tip] 两套 API 混用的推荐姿势
> **SQL 做主干（过滤、聚合、Join）→ `toChangelogStream` 取回 → DataStream 做个别精细算子（如自定义告警、异步 IO）→ `sinkTo` 写回**。
> 转换点越少越好（每次转换都有序列化成本）。

---

## 十一、配置 API（⚠️ 2.x 大变）

```java
// ⭐ 2.x：类型安全的 ConfigOption
Configuration conf = new Configuration();
conf.set(RestOptions.PORT, 8081);
conf.set(WebOptions.SUBMIT_ENABLE, true);
conf.set(CheckpointingOptions.CHECKPOINT_STORAGE, "filesystem");
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment(conf);

// SQL 层配置（运行时参数）
tEnv.getConfig().set("table.exec.state.ttl", "24h");

// 运行时参数（RichFunction 里读）
ParameterTool params = ParameterTool.fromArgs(args);
String broker = params.get("kafka.brokers", "localhost:9092");
```

```yaml
# 2.x：config.yaml（标准嵌套 YAML，替代扁平的 flink-conf.yaml）
jobmanager:
  rpc:
    address: localhost
    port: 6123
  memory:
    process:
      size: 1600m
taskmanager:
  memory:
    process:
      size: 1728m
  numberOfTaskSlots: 4
parallelism:
  default: 4
```

| 常用运行参数 | 说明 |
| --- | --- |
| `parallelism.default` | 默认并行度 |
| `execution.checkpointing.interval` | CK 间隔 |
| `execution.runtime-mode` | `STREAMING` / `BATCH` / `AUTOMATIC` |
| `pipeline.auto-watermark-interval` | 水位生成周期 |
| `table.exec.mini-batch.enabled` | SQL 微批（聚合优化） |
| `taskmanager.memory.process.size` | TM 总内存 |
| `taskmanager.numberOfTaskSlots` | Slot 数 |

⚠️ 旧写法 `conf.setInteger("rest.port", 8081)` 在 2.x **已移除**。

---

## 十二、依赖坐标速查

```xml
<properties>
    <flink.version>2.0.1</flink.version>      <!-- 1.20.x 也支持；按集群版本对齐 -->
    <java.version>17</java.version>           <!-- ⭐ 2.x 要求 17+ -->
</properties>

<dependencies>
    <!-- 核心（2.x 建议 compile；提交 fat-jar 时也可 provided+打包插件） -->
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-streaming-java</artifactId>
        <version>${flink.version}</version>
    </dependency>
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-clients</artifactId>   <!-- ⭐ 本地跑必须，否则 No ExecutorFactory -->
        <version>${flink.version}</version>
    </dependency>

    <!-- Kafka 连接器（⭐ 版本号带 Flink 版本后缀） -->
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-connector-kafka</artifactId>
        <!-- 1.20 → 3.4.0-1.20 ；2.0+ → 4.0.1-2.0 -->
        <version>4.0.1-2.0</version>
    </dependency>

    <!-- 文件 Sink -->
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-connector-files</artifactId>
        <version>${flink.version}</version>
    </dependency>

    <!-- Table API / SQL（三件套：bridge + planner-loader + runtime） -->
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-table-api-java-bridge</artifactId>
        <version>${flink.version}</version>
    </dependency>
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-table-planner-loader</artifactId>
        <version>${flink.version}</version>
    </dependency>
    <dependency>
        <groupId>org.apache.flink</groupId>
        <artifactId>flink-table-runtime</artifactId>
        <version>${flink.version}</version>
    </dependency>

    <!-- 状态后端：1.x RocksDB -->
    <!-- <artifactId>flink-statebackend-rocksdb</artifactId> -->
</dependencies>
```

| 连接器 | 1.20 版本 | 2.x 版本 | 备注 |
| --- | --- | --- | --- |
| Kafka | `flink-connector-kafka` 3.4.0-1.20 | 4.0.1-2.0 | ✅ 已支持 2.x |
| FileSystem | 内置 | 内置 | ✅ |
| **JDBC** | `flink-connector-jdbc` 3.3.0-1.20 | ⚠️ **暂无 2.x 版本** | 迁移前先确认 |
| Elasticsearch | ES7 connector | ⚠️ 暂无 2.x | 可考虑转 OpenSearch |
| Doris | `flink-doris-connector`（按 Flink 版本选 artifact） | 按官方矩阵 | ✅ 见 [[5-bigdata/1-doris/10-面试高频题\|Doris 笔记]] |

---

## 十三、完整实战：把所有 API 串成一个作业

把 [案例导读](#案例导读一个作业贯穿全篇) 的 6 条需求写成一个作业——**这就是前面各章 API 的组合方式**。

### 13.1 作业 DAG（带并行度）

```mermaid
flowchart LR
    K["Kafka: orders<br/>3 分区"] --> SRC["KafkaSource<br/>(p=2)"]
    SRC --> FIL["filter<br/>amount 大于 0"]
    FIL --> PROC["process<br/>⭐ 大额旁路"]
    PROC --> KB["keyBy(userId)"]
    KB --> WIN["窗口 1min<br/>+ 迟到侧输出"]
    WIN --> AGG["aggregate"]
    AGG --> ASY["Async I/O 补等级"]
    ASY --> SK["KafkaSink (EOS)"]
    PROC --> KB2["keyBy(userId)"]
    KB2 --> CUM["process<br/>累计 + 定时清理"]
    CUM --> ALERT["Alerts"]
    PROC -.->|"侧输出"| BIG["big-order 告警"]
    WIN -.->|"侧输出"| LATE["late-data 补偿"]
    CUM --> SAVE["(Keyed State + 定时器)"]
```

### 13.2 完整代码（骨架，各章已有细节实现）

```java
public class OrderStatsJob {

    // 侧输出标签：必须定义为 static final，便于跨算子复用
    public static final OutputTag<Order> BIG_ORDER = new OutputTag<>("big-order") {};
    public static final OutputTag<Order> LATE_DATA = new OutputTag<>("late-data") {};

    public static void main(String[] args) throws Exception {

        // ================= ① 环境与容错（§一、§九）=================
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.setParallelism(2);
        env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);
        CheckpointConfig cp = env.getCheckpointConfig();
        cp.setMinPauseBetweenCheckpoints(30_000);          // 别让 CK 连轴转
        cp.setCheckpointTimeout(10 * 60_000);              // 大状态给足时间
        cp.setMaxConcurrentCheckpoints(1);                 // ⭐ 必须 1
        cp.setTolerableCheckpointFailureNumber(3);         // 容忍偶发失败
        cp.setExternalizedCheckpointRetention(
                ExternalizedCheckpointRetention.RETAIN_ON_CANCELLATION);
        // 重启策略（2.x 走配置）：config.yaml → restart-strategy.type: fixed-delay

        // ================= ② Source + 水位（§二、§六）=================
        KafkaSource<Order> source = KafkaSource.<Order>builder()
                .setBootstrapServers("kafka-1:9092")
                .setTopics("orders")
                .setGroupId("order-stats-job")
                // ⭐ 生产：优先续上次位点，没有才回退最早
                .setStartingOffsets(OffsetsInitializer.committedOffsets(
                        OffsetResetStrategy.EARLIEST))
                .setDeserializer(KafkaRecordDeserializationSchema.of(
                        new OrderJsonDeserializer()))
                .build();

        DataStream<Order> orders = env.fromSource(
                source,
                WatermarkStrategy.<Order>forBoundedOutOfOrderness(Duration.ofSeconds(5))
                        .withTimestampAssigner((o, ts) -> o.getEventTime())
                        .withIdleness(Duration.ofMinutes(1)),   // ⭐ 防空闲分区拖住水位
                "kafka-orders");

        // ================= ③ 过滤脏数据 + 大额告警旁路（§三）=================
        SingleOutputStreamOperator<Order> valid = orders
                // 需求 2：丢掉金额 ≤ 0 的脏数据（例子里 o3）
                .filter(o -> o.getAmount().compareTo(BigDecimal.ZERO) > 0)
                // 需求 5：大额订单走侧输出告警（例子里 o4），主流程继续
                .process(new ProcessFunction<Order, Order>() {
                    @Override
                    public void processElement(Order o, Context ctx, Collector<Order> out) {
                        if (o.getAmount().compareTo(new BigDecimal("5000")) > 0) {
                            ctx.output(BIG_ORDER, o);      // → 告警流
                        }
                        out.collect(o);                    // → 主流程
                    }
                });

        // ================= ④ 窗口聚合 + 迟到侧输出（§四）=================
        SingleOutputStreamOperator<UserWindowStat> stats = valid
                .keyBy(Order::getUserId)                                   // 需求 3
                .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
                .allowedLateness(Duration.ZERO)                            // 例子设为 0
                .sideOutputLateData(LATE_DATA)                             // ⭐ 需求 6：o5 → 迟到流
                .aggregate(new AmountAggregator(), new StatWindowFunction());

        // ================= ⑤ 异步补用户等级（§八）=================
        DataStream<EnrichedStat> enriched = AsyncDataStream.unorderedWait(
                stats,
                new UserLevelAsyncFunction(),      // ⚠️ 必须是异步客户端 + 实现 timeout 降级
                2, TimeUnit.SECONDS,               // 超时
                100);                              // ⭐ capacity（要 ≤ 下游连接池）

        // ================= ⑥ 累计消费 + 定时清理（§五）=================
        DataStream<Alert> alerts = valid
                .keyBy(Order::getUserId)
                .process(new CumulativeAmountFunction());   // ValueState + 定时器 + TTL

        // ================= ⑦ Sink（§七）=================
        // 主结果：写 Kafka，端到端 Exactly-Once
        enriched.sinkTo(KafkaSink.<EnrichedStat>builder()
                .setBootstrapServers("kafka-1:9092")
                .setRecordSerializer(KafkaRecordSerializerSchema.<EnrichedStat>builder()
                        .setTopic("order-stats")
                        .setValueSerializationSchema(new EnrichedStatSchema())
                        .build())
                .setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
                .setTransactionalIdPrefix("order-stats-tx-")   // ⭐ EOS 必填
                .build());

        // 侧输出各自落地（不丢数据）
        valid.getSideOutput(BIG_ORDER).sinkTo(bigOrderSink);
        stats.getSideOutput(LATE_DATA).sinkTo(lateDataSink);

        // 调试用（生产去掉）
        enriched.print("stat");

        // ================= ⑧ 触发执行（§一）=================
        env.execute("order-stats-job");
    }
}
```

### 13.3 同一需求的 SQL 版本（对比看更清楚）

```sql
-- 需求 1~3 + 6：直接一条 INSERT 搞定（窗口 TVF）
INSERT INTO order_stats
SELECT
    user_id,
    window_start,
    window_end,
    SUM(amount) AS total
FROM TABLE(
    TUMBLE(TABLE orders, DESCRIPTOR(ts), INTERVAL '1' MINUTE)   -- ⭐ 窗口 TVF
)
WHERE amount > 0                                                 -- 需求 2：过滤脏数据
GROUP BY user_id, window_start, window_end;
```

| 需求 | DataStream 写法 | SQL 写法 | 差异 |
| --- | --- | --- | --- |
| 过滤脏数据 | `.filter(...)` | `WHERE amount > 0` | 等价 |
| 窗口聚合 | `.window(...).aggregate(...)` | ⭐ `TABLE(TUMBLE(...))` + `GROUP BY` | SQL 更短，且自带算子优化 |
| 大额旁路告警 | `process` + `ctx.output` | 另一个 `INSERT` + `WHERE amount > 5000` | SQL 要写两条作业 |
| 迟到数据旁路 | `sideOutputLateData` | ⚠️ SQL 无直接对应 | DataStream 更灵活 |
| 累计 + 定时清理 | `ValueState` + 定时器 | `GROUP BY` + `table.exec.state.ttl` | SQL 省心但控制力弱 |
| 异步补维表 | `AsyncDataStream` | ⭐ **Lookup Join**（`FOR SYSTEM_TIME AS OF`） | SQL 更简单 |

> [!tip] 结论（结合 [§〇 的选型](#〇api-全景选-datastream-还是-tablesql)）
> **主干的过滤 + 窗口聚合用 SQL 写（更短、自动优化）；需要"旁路 + 超时 + 精细状态"的部分下沉到 DataStream。**
> 两者用 `toChangelogStream` / `fromChangelogStream` 互转（[§十](#十tablesql-api-与-datastream-互转)）。

### 13.4 从这个例子能学到的 6 件事

| # | 结论 | 对应章节 |
| --- | --- | --- |
| 1 | **窗口靠水位触发，不是到点自动触发** | §三 用例子看、§六 |
| 2 | **迟到数据的判定基准是水位**，侧输出是"不丢"的关键 | §三 用例子看、§四 |
| 3 | **`keyBy` 保证同 key 同子任务**，这是有状态计算的前提 | §三 用例子看 |
| 4 | **状态按 key 分片，必须有退出机制**（TTL / 定时器 clear） | §五 用例子看 |
| 5 | **端到端 EOS = Source 可重放 + 状态快照 + Sink 事务/幂等** | §七 用例子看、§九 用例子看 |
| 6 | **SQL 写主干、DataStream 补细节**是最实用的组合 | §〇、§十、§十三 |

---

## 附录 A：1.x → 2.x 迁移逐项对照

```mermaid
flowchart LR
    A["Flink 1.20 作业"] --> B{"用了下列 API 吗？"}
    B -->|"SourceFunction / addSource"| C["⭐ 改 fromSource(Source)"]
    B -->|"SinkFunction / addSink"| D["⭐ 改 sinkTo(Sink V2)"]
    B -->|"Time.seconds()"| E["⭐ 改 Duration.ofSeconds()"]
    B -->|"open(Configuration)"| F["⭐ 改 open(OpenContext)"]
    B -->|"keyBy(0) 或 keyBy(字段名)"| G["⭐ 改 KeySelector"]
    B -->|"readTextFile / writeAsText"| H["⭐ 改 FileSource / FileSink"]
    B -->|"DataSet API"| I["⭐ 改 DataStream 或 SQL"]
    B -->|"setStateBackend / setRestartStrategy"| J["⭐ 改配置项"]
    C --> K["✅ 编译通过 + 状态兼容性验证"]
    D --> K
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
```

| 1.x 写法 | ⭐ 2.x 写法 |
| --- | --- |
| `env.addSource(new MySourceFunction<>())` | `env.fromSource(mySource, watermarkStrategy, "name")` |
| `stream.addSink(new MySinkFunction<>())` | `stream.sinkTo(mySinkV2)` |
| `TumblingEventTimeWindows.of(Time.minutes(5))` | `...of(Duration.ofMinutes(5))` |
| `env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime)` | **删除**（只剩事件时间语义） |
| `open(Configuration parameters)` | `open(OpenContext openContext)` |
| `stream.keyBy(0)` / `stream.keyBy("field")` | `stream.keyBy(KeySelector)` |
| `env.readTextFile("path")` | `env.fromSource(new FileSource.../FileSource.forRecordStreamFormat(...))` |
| `stream.writeAsText("path")` | `stream.sinkTo(FileSink.forRowFormat(...).build())` |
| `stream.timeWindowAll(Time.seconds(10))` | `.windowAll(TumblingProcessingTimeWindows.of(Duration.ofSeconds(10)))` |
| `conf.setInteger("rest.port", 8081)` | `conf.set(RestOptions.PORT, 8081)` |
| `env.setStateBackend(new RocksDBStateBackend(...))` | ⭐ **配置项**（`state.backend.type`）+ 2.x 的 ForSt |
| `env.setRestartStrategy(RestartStrategies.fixedDelayRestart(...))` | ⭐ **配置项** `restart-strategy.type` |
| `env.registerTypeWithKryoSerializer(...)` | ⭐ **移除**，改用 `env.getConfig()` 等价方法或专用序列化器 |
| `stream.iterate()`（IterativeStream） | ⭐ **移除**，需改写（状态机/循环算子在 SQL 或 process 里实现） |
| `flink-conf.yaml`（扁平 key） | ⭐ **`config.yaml`**（嵌套 YAML，官方提供迁移工具） |
| DataSet API（`ExecutionEnvironment`） | ⭐ **移除**，改用 DataStream（有界流）或 Table API |
| Scala API / Scala case class 状态 | ⭐ **Scala API 移除**；⚠️ Scala case class 状态**跨版本不兼容** |

> [!danger] 迁移的**状态兼容性**才是真正的坑（比编译错误更危险）
> Flink 2.x 把 **Kryo 2.x 升到 5.x**，并且为 **Map/List/Set 引入了专用序列化器**，导致**三类状态无法从 1.x 恢复到 2.x**：
> | 不兼容模式 | 报错特征 |
> | --- | --- |
> | 直接 Kryo 注册（`registerTypeWithKryoSerializer`） | `IndexOutOfBoundsException: Index 116 out of bounds` |
> | ⭐ **泛型集合状态**（`ValueState<List<T>>` / `Map<K,V>` / `Set<T>`） | `ClassNotFoundException: value2` |
> | ⭐ **POJO 里含集合字段**（`List` / `Map` / `Set` / `Queue`） | `StateMigrationException: PojoSerializer ... incompatible` |
>
> **最坑的是**：升级后作业**先显示 RUNNING，恢复状态时才失败**，然后进入**无限重启循环**——只有当 `numRestarts` 涨、`runningTime` 不涨时才发现。
> **规避手段**（写新代码时就照做）：
> ① ⭐ **用 `MapState` 而不是 `ValueState<Map<...>>`**；
> ② POJO **避免集合字段**（或改用 Avro/Protobuf）；
> ③ 开发期用 `env.getConfig().disableGenericTypes()` ⭐ **主动让 Kryo 兜底报错**，别等到升级才发现。
>
> 详见 [[3-状态管理]]（状态序列化与演进）、[[5-Checkpoint与Savepoint]]（状态兼容与迁移）。

## 附录 B：常见报错速查

| 报错 | 原因 | 解法 |
| --- | --- | --- |
| `ClassNotFoundException: SourceFunction` | 2.x 已移除旧 Source API | 改 `env.fromSource(newSource, wm, name)` |
| `NoSuchMethodError: open(Configuration)` | 2.x 签名改为 `open(OpenContext)` | 改签名（所有 `RichFunction` 子类） |
| `No ExecutorFactory found` | 缺 `flink-clients` 依赖 | 加 `flink-clients` |
| `The generic type ... cannot be used as a POJO type` | 类型不是合法 POJO / 走到 Kryo 兜底 | 实现 `Serializable` + 无参构造，或用 `AvroTypeInfo` |
| `Generic types have been disabled` | 主动开了 `disableGenericTypes()` | 说明该类型会用 Kryo → 改成受支持类型 |
| `StateMigrationException: PojoSerializer ... incompatible` | 1.x → 2.x 状态序列化不兼容 | 见附录 A（改 MapState / Avro / 重跑状态） |
| `Caused by: java.lang.IllegalArgumentException: WindowAssigner must be on a keyed stream` | 在非 keyed 流上用带 key 的窗口 | 先 `keyBy`，或改用 `windowAll` |
| 窗口一直不触发 | **没有水位**（未分配事件时间/没有事件数据） | 检查 `WatermarkStrategy` 与时间戳字段 |
| 数据莫名丢失 | 迟到数据被丢弃 | 配 `allowedLateness` + `sideOutputLateData` |
| Checkpoint 一直超时 | 状态太大 / 背压 / 间隔太短 | 见 [[5-Checkpoint与Savepoint]]、[[6-背压与性能调优]] |

## 附录 C：一页速查（最常用的 30 行）

```java
// 环境
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
env.setParallelism(4);
env.enableCheckpointing(60_000, CheckpointingMode.EXACTLY_ONCE);

// Source
DataStream<T> s = env.fromSource(source, WatermarkStrategy.forBoundedOutOfOrderness(Duration.ofSeconds(5))
        .withTimestampAssigner((e, ts) -> e.ts).withIdleness(Duration.ofMinutes(1)), "src");
// 便捷 source：env.fromData(...)（1.19+ 推荐）

// 转换
s.map(f).flatMap(f).filter(p)
 .keyBy(KeySelector)
 .window(TumblingEventTimeWindows.of(Duration.ofMinutes(1)))
 .allowedLateness(Duration.ofSeconds(30)).sideOutputLateData(tag)
 .aggregate(aggFn, processWindowFn)
 .process(new KeyedProcessFunction<...>() { ... });

// 状态（KeyedProcessFunction 内）
ValueState<V> st = getRuntimeContext().getState(new ValueStateDescriptor<>("n", V.class));
MapState<K,V> ms = getRuntimeContext().getMapState(new MapStateDescriptor<>("m", K.class, V.class));
ctx.timerService().registerEventTimeTimer(ts);

// Sink
out.sinkTo(KafkaSink.<T>builder().setBootstrapServers(...)
        .setRecordSerializer(...).setDeliveryGuarantee(DeliveryGuarantee.EXACTLY_ONCE)
        .setTransactionalIdPrefix("tx-").build());

// 执行
env.execute("job");
```

| 类别 | 最常用 API |
| --- | --- |
| 环境 | `getExecutionEnvironment()` / `enableCheckpointing()` / `execute(name)` |
| Source | ⭐ `fromSource(source, wm, name)` / `fromData(...)` |
| 转换 | `map` / `flatMap` / `filter` / ⭐ `keyBy(KeySelector)` / `aggregate` |
| 窗口 | ⭐ `Tumbling/Sliding/EventTimeSessionWindows.of(Duration)` + `allowedLateness` + `sideOutputLateData` |
| 状态 | ⭐ `getState/getListState/getMapState`（**别用 `ValueState<Map>`**）+ `StateTtlConfig` |
| 定时器 | `registerEventTimeTimer` / `registerProcessingTimeTimer` / `onTimer` |
| 水位 | ⭐ `forBoundedOutOfOrderness(Duration)` + `withTimestampAssigner` + `withIdleness` |
| Sink | ⭐ `sinkTo(KafkaSink/FileSink)` / `JdbcSink.sink(...)` / `print()` |
| 异步 | `AsyncDataStream.unorderedWait(stream, fn, timeout, unit, capacity)` |
| SQL | `StreamTableEnvironment.create` / `executeSql` / `sqlQuery` / ⭐ `toChangelogStream` |
| 互转 | `fromDataStream` / `toDataStream` / `toChangelogStream` / `fromChangelogStream` |

> [!note] 相关笔记
> [[0-Flink总览]]（MOC）｜[[1-架构与运行时]]｜[[2-时间与窗口]]｜[[3-状态管理]]｜[[4-容错与ExactlyOnce]]｜[[5-Checkpoint与Savepoint]]｜[[6-背压与性能调优]]｜[[7-FlinkCDC与实时数仓]]｜[[8-FlinkSQL与TableAPI]]｜[[9-部署与运维]]｜[[11-端到端一致性]]｜[[12-Tuple与Tuple4]]｜[[13-生产部署Checklist逐项解析]]｜[[Flink入门：1条河讲透实时数据处理（详细整理版）]]
