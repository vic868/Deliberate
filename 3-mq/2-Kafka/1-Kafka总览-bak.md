---
title: Kafka 总览
tags: [MQ, Kafka, 索引, MOC]
status: 进行中
created: 2026-10-09
---

# 🚀 Kafka 总览

> 这是 Kafka 系列笔记的**总入口（MOC）**。
> 本系列回答四个层次的问题：**① Kafka 是什么、怎么运转的（原理）② 代码怎么写（实战）③ 线上怎么运维调优（运维）④ 面试怎么答（面试）**。
> 关联：[[2-架构与核心概念]]、[[8-性能优化与高吞吐原理]]、[[10-面试高频题]]。

---

## 一、系列导航

| # | 笔记 | 一句话定位 | 核心内容 |
|---|---|---|---|
| — | **[[0-概念脑图.excalidraw\|概念脑图]]** | 概念脑图速览 | MQ 概念、Kafka 定位、Topic/Partition/Segment 等基础图示 |
| 1 | **[[1-Kafka总览]]** | 你现在看的这篇 | 导航、速查表、学习路径、版本演进 |
| 2 | **[[2-架构与核心概念]]** | 建立整体地图 | 角色、Topic/Partition/Replica、Controller、KRaft、核心 API |
| 3 | **[[3-生产者原理]]** | 消息怎么发出去 | 发送主流程、RecordAccumulator、分区器、acks、幂等、顺序性 |
| 4 | **[[4-消费者与Rebalance]]** | 消息怎么读进来 | 消费组、位移提交、Rebalance 协议、分配策略、Lag |
| 5 | **[[5-日志存储与副本机制]]** | 消息怎么存、怎么容错 | Segment、稀疏索引、Compaction、ISR/HW/LEO、Leader Epoch |
| 6 | **[[6-事务与Exactly-Once]]** | 消息怎么做到不重不丢 | 幂等生产者、Transaction Coordinator、LSO、read_committed |
| 7 | **[[7-运维与集群调优]]** | 集群怎么管 | 集群规划、OS/JVM 调优、运维命令、监控指标、故障速查 |
| 8 | **[[8-性能优化与高吞吐原理]]** | 为什么快、怎么更快 | 顺序写、PageCache、零拷贝、批量、压缩、端到端调优清单 |
| 9 | **[[9-SpringBoot实战]]** | 工程里怎么落地 | Spring Kafka、可靠生产、批量消费、重试与死信、长事务 |
| 10 | **[[10-面试高频题]]** | 面试怎么答 | 六道必答大题 + 快问快答 + 易错陷阱 |

---

> [!tip] 画图约定
> 本库支持 Mermaid（已装 mermaid-popup / mermaid-zoom）。本系列的图**优先用 Mermaid**，只有"依赖精确对齐"的图（内存字节/位布局、字节码、GC 日志、命令输出样本）才保留 ASCII。规范详见 [[0-Java总览]] §七「文档写作约定」。

## 二、按需求的阅读路径

> [!tip] 三条路径，按需选择
> **面试突击（1～2 天）**：[[10-面试高频题]] → [[2-架构与核心概念]] → [[8-性能优化与高吞吐原理]] → [[5-日志存储与副本机制]]（ISR/HW/LEO 部分）
> **上手干活（1 周）**：[[2-架构与核心概念]] → [[9-SpringBoot实战]] → [[3-生产者原理]] → [[4-消费者与Rebalance]] → [[7-运维与集群调优]]
> **系统吃透（持续）**：从 1 顺序读到 7，跟着每篇的"动手验证"跑命令；5 和 4 值得反复读。

---

## 三、30 秒速查表

| 问题 | 一句话答案 | 详见 |
|---|---|---|
| Kafka 是什么 | 分布式、分区、多副本的**提交日志（Commit Log）**，兼作消息系统/存储系统/流处理平台 | [[2-架构与核心概念]] |
| 消息有序吗 | **分区内有序，Topic 全局无序**；要全局有序只能单分区（等于放弃并行） | [[3-生产者原理]] |
| 消息会丢吗 | 生产端 `acks=all` + 重试，副本 `min.insync.replicas>=2`，消费端**处理完再提交位移** | [[10-面试高频题]] |
| 消息会重吗 | 默认 at-least-once，**重复不可避免**；消费端幂等（唯一键/去重表/状态机），Kafka 内部可用事务 | [[6-事务与Exactly-Once]] |
| 消费者能读到哪里 | 只能读到 **HW（高水位）**；`read_committed` 则进一步受 **LSO** 限制 | [[5-日志存储与副本机制]] |
| 为什么快 | 顺序追加写 + PageCache + 零拷贝(sendfile) + 批次 + 压缩 + 分区并行 + 稀疏索引 | [[8-性能优化与高吞吐原理]] |
| 位移存哪 | 现代版本存在内部压缩 Topic **`__consumer_offsets`**（老版本在 ZooKeeper） | [[4-消费者与Rebalance]] |
| Rebalance 是什么 | 消费组成员/订阅变化导致分区重新分配，**期间 Stop-The-World** | [[4-消费者与Rebalance]] |
| 元数据存哪 | **KRaft**：存储在 Controller Quorum 的 `__cluster_metadata` 日志；ZooKeeper 模式在 4.0 已移除 | [[2-架构与核心概念]] |
| 什么决定并行度 | **分区数**：生产并行、消费并行、单机顺序性的基本单位 | [[2-架构与核心概念]] |

---

## 四、核心概念最小记忆集

一张表把最容易混淆的概念钉死（详细展开见对应笔记）：

| 概念 | 精确定义 | 常见误解 |
|---|---|---|
| **Topic** | 逻辑分类，相当于表/文件夹 | 以为 Topic 有物理实体 |
| **Partition** | 物理单位，一个**有序、不可变、追加**的日志文件目录 | 以为分区越多越好 |
| **Segment** | Partition 的物理切分文件（`.log`/`.index`/`.timeindex`） | 与 Partition 混为一谈 |
| **Replica** | 分区的副本；1 leader + N-1 follower | 以为 follower 也能被消费 |
| **ISR** | 与 leader **保持同步**的副本集合（含 leader，**基于时间**判定） | 以为 ISR 是"全部存活副本" |
| **LEO** | Log End Offset，每个副本自己的日志末端位置 | 与 HW 混淆 |
| **HW** | High Watermark，**ISR 中所有副本都已同步到的位置**，消费者可见上限 | 以为等于 leader 的 LEO |
| **LSO** | Last Stable Offset，`read_committed` 下消费者可见上限 | 与 HW 混淆 |
| **Offset** | 分区内消息的唯一递增编号 | 以为全局唯一 |
| **Consumer Group** | 一组消费者共同消费一个 Topic，**分区与消费者一一对应** | 以为消费者越多越快 |
| **Controller** | 集群中负责分区/副本状态管理的 broker（KRaft 下由 controller 角色承担） | 以为它负责收发消息 |
| **Coordinator** | 负责消费组管理与位移提交的 broker（Group Coordinator） | 与 Controller 混淆 |

下面逐个展开。每个概念的"详见"指向系列里对应笔记。

---

### 1. Topic —— 逻辑分类，无物理实体

- **精确定义**：Topic 是消息的**逻辑分类/主题名**，相当于数据库的表或文件系统的文件夹，是生产者发送、消费者订阅的**命名空间**。它只存在于元数据层面。
- **物理承载**：一个 Topic 会被拆成多个 **Partition**，这些 Partition 以目录的形式分散在集群的各个 broker 上。Topic 本身不对应任何一块具体的"文件"或"目录"。
- **核心属性**：名称（全局唯一）、分区数、副本因子、保留策略（`retention.ms` / `retention.bytes`）、清理策略（`delete` 或 `compact`）。
- **常见误解**：以为"Topic 越大越占空间""Topic 有物理实体"。Topic 只是逻辑壳，真正的 I/O 与存储压力落在 Partition 上。扩分区可以增加并行度，但**分区数一旦扩了就不能安全缩回去**；分区数过多会带来元数据膨胀、文件句柄暴涨、Rebalance 成本上升。

### 2. Partition —— 物理并行单位，有序追加日志

- **精确定义**：Partition 是 Topic 的**物理分片**，本质是一个**有序、不可变、只追加（append-only）**的日志。每个 Partition 独占一个目录（命名形如 `topic-0`），目录下是若干个 Segment 文件。
- **三个关键性质**：
  1. **有序性**：分区内消息按写入顺序分配连续递增的 Offset，是 Kafka 提供顺序保证的最小粒度。
  2. **不可变性**：消息一旦写入就不被修改删除（清理/压缩是整体段级别的操作，不是原地改）。
  3. **追加写**：新消息永远追加到末尾（LEO 处），这就是"顺序写"性能的根基。
- **它是并行的原子单位**：生产者按 `linger.ms`/`batch.size` 攒批发送、消费者按分区并行拉取、副本按分区复制，**全都是以 Partition 为粒度**。分区数 ≈ 最大并行度。
- **常见误解**：以为"分区越多越好"。分区膨胀的代价：每个分区在内存中占用副本对象与索引、broker 上是一堆文件句柄、Controller 要维护更多状态、`__consumer_offsets` 里条目激增。经验上单 broker 数千分区是警戒线，需结合实际压测。

### 3. Segment —— 日志的物理切分文件组

- **精确定义**：Segment 是 Partition 日志在**磁盘上**的切分单位。一个 Partition 目录里包含多组 Segment，每组由一个数据文件和两个索引文件组成：
  - `0000...log`：实际消息体（含 offset、size、crc、timestamp、key、value、headers）。
  - `0000...index`：**稀疏位移索引**，按固定字节间隔采样，把 Offset → 物理文件位置映射起来。
  - `0000...timeindex`：**稀疏时间索引**，把时间戳 → Offset 映射起来，服务于"按时间回溯/清理"。
- **切分触发**：达到 `log.segment.bytes`（默认 1GB）或 `log.roll.hours`（默认 7 天）就滚动生成新 Segment。
- **清理粒度**：删除/压缩都是**以 Segment 为最小单位**整体回收，单个 Segment 内部不会去删除某几条消息——这也是为什么"顺序写 + 批量回收"能保持磁盘高效。
- **常见误解**：把 Segment 和 Partition 混为一谈。一句话区分：**Partition 是逻辑分片，Segment 是该分片在磁盘上的文件切分**。

### 4. Replica —— 分区副本，1 leader + N-1 follower

- **精确定义**：Replica 是 Partition 的**副本**，分布在不同的 broker 上，实现容错与高可用。副本集合由 `replication.factor` 决定，其中一个是 **leader**，其余为 **follower**。
- **leader 职责**：**承接全部的生产和消费请求**——生产者只往 leader 写，普通消费者只从 leader 读。
- **follower 职责**：**只做被动同步**，定期向 leader 拉取消息（fetch），写入自己的日志。follower **不对外提供读写服务**（这也是 Kafka 与某些"读副本分担读"系统的区别）。
- **ISR 关系**：只有"跟得上"的副本才留在 ISR 里；leader 故障后，只能从 ISR 中选举新 leader。
- **常见误解**：以为 follower 可以分担消费读请求。Kafka 的设计是"读写都在 leader"，follower 纯粹为容错；想提高读吞吐只能加分区。

### 5. ISR —— 与 leader 保持同步的副本集合

- **精确定义**：ISR（In-Sync Replicas）是**包含 leader 在内**、与 leader **保持同步**的副本子集。它**不是"所有存活副本"**。
- **判定标准**：以时间为准——`replica.lag.time.max.ms`（默认 30s）内，follower 必须**持续向 leader 发起 fetch 且基本追平**。卡住、宕机、或严重落后的副本会被**踢出 ISR**。
- **关键作用**：① 新 leader 只能从 ISR 里选，保证不丢已提交数据；② `acks=all` 的语义是"写入**所有 ISR 副本**"才算成功，而不是"所有存活副本"。
- **常见误解**：以为"存活即 ISR"。网络抖动或消费慢导致 follower 落后超过阈值就会被移出 ISR，此时 ISR 可能只剩 leader 一个，集群仍然能写，但可靠性降级。

### 6. LEO —— 每个副本自己的日志末端

- **精确定义**：LEO（Log End Offset）是**每个副本各自**日志中下一条待写入消息的 Offset，即该副本当前的末尾位置。leader 有 leader LEO，每个 follower 也有自己的 LEO，它们**彼此不同**。
- **更新时机**：副本每追加一条消息，自己的 LEO 就 +1。leader 会记录每个 follower 的 LEO（用来判断谁同步到哪、谁该留在 ISR）。
- **与 HW 的关系**：HW 是 ISR 中**最小 LEO** 的边界——所有副本都同步到的位置。所以 `HW ≤ 任意副本的 LEO`，leader 的 LEO 通常大于等于 HW。
- **常见误解**：把 LEO 当成全局唯一的"日志长度"。它是**副本级别**的、每个副本独立维护的偏移量。

### 7. HW —— 消费者可见的高水位

- **精确定义**：HW（High Watermark，高水位）是 **ISR 中所有副本都已同步到的位置**，即所有副本 LEO 的**最小值**。它是**消费者可见的消息上界**。
- **为什么需要它**：leader 刚写入但还没同步给 follower 的消息（位于 LEO 与 HW 之间）是"未提交"的，一旦 leader 此刻崩溃，这些消息会丢失；所以对消费者**屏蔽**，保证"读到的一定不会丢"。
- **更新时机**：follower fetch 请求里会带上自己的 LEO，leader 据此重新计算最小值来推进 HW。
- **截断机制**：旧 leader 在故障恢复后要**把自己的日志截断到 HW**，丢弃未同步的部分，避免"幽灵读"（与 Leader Epoch 配合）。
- **常见误解**：以为 HW 等于 leader 的 LEO。leader LEO 领先于 HW 的那段正是"已写未同步"的不可见区。

### 8. LSO —— 事务下的稳定上界

- **精确定义**：LSO（Last Stable Offset）是 `read_committed` 隔离级别下**消费者可见的上界**。它等于**第一个未完成事务的开头位置**；其前面的消息（含已提交事务、非事务消息）全部可见，其位置之后的消息（含进行中事务、已中止事务）对消费者不可见。
- **解决的问题**：事务场景下，一个事务可能包含多条消息且跨批次。`read_uncommitted` 会读到未提交甚至最终 abort 的消息；`read_committed` 靠 LSO 拦住，等事务提交/中止后再放行，实现**读不读到半成品**。
- **与 HW 的关系**：`read_uncommitted` 受 HW 限制；`read_committed` 取 `min(HW, LSO)`。非事务 Topic 中两者基本等价。
- **常见误解**：把 LSO 和 HW 当成一回事。HW 解决"副本未同步"，LSO 解决"事务未完结"，是两个维度的可见性边界。

### 9. Offset —— 分区内的唯一递增值

- **精确定义**：Offset 是消息在**某个 Partition 内**的**唯一、单调递增、连续**的整数编号，从 0 开始，由 broker 在消息落盘时分配。
- **两个层面的 Offset**：
  - **日志 Offset**：消息在分区日志里的物理位置标识，用于定位与索引。
  - **消费位移**：消费者组在 `__consumer_offsets` 里记录的"**下一条要消费的消息 Offset**"（注意是"下一条"，不是"最后一条已消费的"）。
- **常见误解**：以为 Offset 全局唯一。它是**分区级别**的，不同分区之间毫无关联，这也是"全局有序只能靠单分区"的根本原因。

### 10. Consumer Group —— 共同消费、分区一一绑定

- **精确定义**：Consumer Group（消费组）是一组**共同消费一个或多个 Topic** 的消费者实例，对外表现为一个"逻辑订阅者"。组内通过**分区分配**实现负载均衡：**一个分区在同一时刻只被组内的一个消费者持有**。
- **再均衡（Rebalance）**：组成员变化、订阅变化、分区数变化时触发，重新分配分区，**期间整个组暂停消费（Stop-The-World）**。
- **常见误解**：以为"消费者越多消费越快"。事实上**消费者数不应超过分区总数**，多出来的消费者会处于空闲（assign 不到分区）；且消费者过多反而让 Rebalance 更频繁、代价更高。吞吐量上限由分区数决定。

### 11. Controller —— 集群的"大脑"，不收发消息

- **精确定义**：Controller 是集群中**负责元数据与状态管理**的那个 broker，由 Controller Quorum（KRaft 模式下）选举产生，全程**只有一个**在任。
- **核心职责**：
  - 分区与副本的状态机管理（Leader 选举、副本分配、ISR 变更通知）。
  - Topic 的创建/删除、分区扩缩容。
  - broker 上下线感知与分区重分配（`kafka-reassign-partitions`）。
- **KRaft 下的变化**：3.x/4.x 采用 KRaft，元数据从 ZooKeeper 迁移到 Controller Quorum 的 `__cluster_metadata` 日志，Controller 由 quorum 选举；4.0 起 ZooKeeper 模式被彻底移除。
- **常见误解**：以为 Controller 负责消息的收发。它的工作是**管状态、管分配**，生产消费的 I/O 流量走的是各 broker 自己，与 Controller 无关。

### 12. Coordinator —— 消费组与事务的"管家"

- **精确定义**：Coordinator 是**为某个消费组（或事务）服务的 broker**，分为两类：
  - **Group Coordinator**：管理消费组的成员关系、心跳、位移提交（`__consumer_offsets`），驱动 Rebalance。
  - **Transaction Coordinator**：管理事务的生命周期（开启、提交、中止），写入事务日志 Topic（`__transaction_state`）。
- **定位规则**：消费组对应的 Coordinator 由 `Utils.abs(groupId.hashCode) % offsets.topic.num.partitions` 决定，组内所有成员都和它通信。
- **常见误解**：把 Coordinator 和 Controller 混为一谈。一句话区分：**Controller 管集群级状态（分区/副本/broker），Coordinator 管组级状态（消费组成员/位移、事务）**。两者职责不重叠。

> [!warning] 三个最经典的面试陷阱
> 1. **`auto.offset.reset=latest` 不等于"不消费历史"** —— 它只在**没有已提交位移**时生效；组一旦提交过位移，重启会从提交位移继续。
> 2. **`acks=all` 不等于"消息绝对不丢"** —— 若 ISR 收缩到小于 `min.insync.replicas`，broker 会**直接拒绝写入**（保可靠性、牺牲可用性）；反之若 `unclean.leader.election.enable=true`，非 ISR 副本可被选为 leader，**会丢数据**。
> 3. **消费者存活是"双条件"** —— 既要 `session.timeout.ms` 内的心跳，也要 `max.poll.interval.ms` 内的 `poll()` 调用；处理逻辑太慢导致的是后者，调 `session.timeout.ms` 没用。

---

## 五、版本演进与选型要点

| 版本 | 里程碑 | 对使用者的影响 |
|---|---|---|
| 0.8 | 引入副本机制、消费组位移外置 | 生产可用起点 |
| 0.10 | 消息带时间戳；Kafka Streams 发布 | 流处理能力成型 |
| 0.11 | **幂等生产者 + 事务 + Leader Epoch**；`__consumer_offsets` 承担位移 | Exactly-Once 与"副本截断不丢数据"的基础 |
| 1.0 | 正式宣布生产就绪 | 稳定版本分界 |
| 2.1 | 支持 ZStandard 压缩；`delivery.timeout.ms` 语义完善 | 压缩与超时语义更清晰 |
| 2.4 | 消费端**增量/粘性分区分配**（Cooperative Sticky） | Rebalance 不再全量 STW |
| 2.8 | **KRaft 模式（实验性）** | 摆脱 ZooKeeper 的第一步 |
| 3.0 | 幂等生产者**默认开启**（无冲突配置时）；KRaft 优化 | 默认更安全 |
| 3.3 | **KRaft 生产就绪**，成为新集群推荐模式 | 新集群可直接上 KRaft |
| 3.7~3.9 | **新一代消费组协议 KIP-848** 逐步可用；Broker 端分配器 | Rebalance 更快、更少 STW |
| **4.0** | **ZooKeeper 模式被移除**；KRaft 为唯一选择；新增队列语义（Queues for Kafka） | 升级前必须完成 ZK → KRaft 迁移 |

> [!note] 本系列的口径
> 默认以 **Kafka 3.x / 4.x + KRaft** 为背景表述；涉及 ZooKeeper 的地方会明确标注为"旧版本/legacy"。客户端 API 以官方 `kafka-clients` 与 `spring-kafka` 为准。
> 升级到 4.0 的前置动作是完成 KRaft 迁移，详见 [[7-运维与集群调优]]。

---

## 六、与 MQ 家族的选型对照

| 维度 | Kafka | RocketMQ | RabbitMQ |
|---|---|---|---|
| 吞吐 | **最高**（十万～百万级/秒） | 高（十万级） | 中（万级） |
| 延迟 | ms 级 | ms 级 | **微秒级** |
| 顺序消息 | 分区内有序 | 支持队列级严格顺序 | 队列内有序 |
| 事务消息 | 支持（Producer 事务） | **原生支持**（半消息+回查） | 不支持 |
| 延迟消息 | 不原生支持（需自建/外部调度） | **支持多级延迟** | 插件支持 |
| 消息回溯 | **按 offset/时间自由回溯**（本质是日志） | 支持 | 消费即删，回溯弱 |
| 生态 | 流处理/连接器/大数据生态**最强** | 电商业务场景成熟 | 路由灵活、协议丰富 |
| 典型场景 | 日志采集、埋点、CDC、流计算、事件总线 | 交易、订单、业务消息 | 企业集成、复杂路由 |

> Kafka 的独特定位：**它首先是一个分布式提交日志（存储），其次才是消息队列**。这句话解释了很多"反直觉"的设计——消息可以被重复读、可以保留很久、消费者只是按自己的位移在"追日志"。完整选型讨论见 [[10-面试高频题]]。

---

## 七、本库相关：Kafka 落地实操

本系列讲**原理与通用工程实践**；下面几篇是本库里已有的 **Kafka 数据入湖（topic → Hive/HDFS）** 实操记录，属于"具体环境下的落地方案"，可与本系列的 [[7-运维与集群调优]]、[[9-SpringBoot实战]] 对照阅读：

| 笔记 | 定位 |
|---|---|
| [[Kafka入湖标准流程与方案选型]] | 把 "topic → HDFS" 抽象成可复用的八步法 + 参数化模板 |
| [[Kafka入Hive实操手册]] | 具体环境下的建表、采集、挂分区操作手册 |
| [[Kafka消息入Hive方案]] | 入 Hive 的方案设计与取舍 |
| [[数据流全链路执行手册]] | 从采集到加工到调度的端到端链路 |
| [[Flink-on-K8s-vs-YARN]] | 消费侧流处理作业的部署形态选型 |

> [!note] 阅读关系
> 本系列提供"为什么这样设计"（分区、副本、位移、Lag、延迟与吞吐取舍），上面几篇提供"在这套环境里怎么做"。排查线上入湖问题时，建议先回本系列确认机制，再照实操手册执行。

---

## 八、学习检查清单

- [ ] 能画出 Producer → Broker(Partition/Replica) → Consumer Group 的完整链路，并说清每个组件职责
- [ ] 能解释 HW / LEO / LSO 三者的区别与各自限制谁
- [ ] 能说出至少 6 个生产者关键参数及其副作用
- [ ] 能解释 Rebalance 的触发条件、危害与治理手段
- [ ] 能完整描述"消息不丢"在三个环节各自要做什么
- [ ] 能说清幂等生产者与事务分别解决什么问题、边界在哪
- [ ] 能列举"Kafka 为什么快"的 6 个以上原因并解释原理
- [ ] 能用命令排查一次消费 Lag 或分区不均衡

---
> [!question] 还需要补充什么？
> 本系列可继续扩展的方向：Kafka Connect（数据集成）、Kafka Streams（流处理）、MirrorMaker 2（跨集群容灾）、Schema Registry（消息契约治理）、Kafka on K8s（Strimzi）。需要哪块就新开一篇并在上方导航表登记。
