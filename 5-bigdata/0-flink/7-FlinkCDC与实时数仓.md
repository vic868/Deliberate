---
title: Flink CDC 与实时数仓
tags: [Flink, CDC, 实时数仓]
status: 进行中
created: 2026-10-09
---

# 🚰 七、Flink CDC 与实时数仓

> 这一篇回答四个问题：**CDC 到底是什么、为什么生产只选基于日志的 CDC**；**Debezium / Flink CDC 的全量 + 增量是怎么"边读历史边追日志"而不停机的**；**一条 MySQL → Flink → Kafka/Doris 的实时数仓链路该怎么搭、DDL 怎么写**；**上线后位点失效、锁表、schema 变更、主键冲突这些真实的坑怎么排**。
>
> 前置阅读：[[8-FlinkSQL与TableAPI]]（动态表与 changelog 语义）、[[5-Checkpoint与Savepoint]]（位点为什么能续传）、[[3-状态管理]]（维表与状态膨胀）。链路一致性看 [[11-端到端一致性]]。

---

## 一、CDC 是什么，为什么它是实时数仓的地基

### 1.1 定位

CDC = Change Data Capture，**变更数据捕获**。它要做的事情只有一句话：

> 把数据库内部"一行数据从旧值变成新值"这件事，**变成一条可以被别的系统消费的消息**。

没有 CDC 的时候，业务库和数仓之间只有三种选择：

| 方式 | 本质 | 实时性 | 对源库影响 | 能捕获删除 | 业务是否要配合 |
| --- | --- | --- | --- | --- | --- |
| **基于日志的 CDC**（binlog / WAL / redo） | 伪装成 MySQL Slave 订阅日志 | 秒级甚至毫秒级 | 极低（顺序读日志） | ✅ 能拿到 `-D` | ❌ 不需要，业务零改动 |
| **基于查询的 CDC**（轮询 `WHERE update_time > last`） | 定时 SELECT | 取决于轮询周期，分钟级 | 高（每次全表/范围扫描，压力随时长线性增长） | ❌ 物理删除查不到 | ✅ 需要 `update_time`、不能硬删 |
| **触发器 / 应用双写** | DB trigger 或业务代码里同时写消息 | 高 | 触发器严重拖慢写入 | 能 | ✅ 改造业务，风险高 |

生产上 **几乎只有基于日志的 CDC** 这一个答案，原因不是"日志更高级"，而是上面这张表的后三列：**对源库压力可控、不侵入业务、能捕获物理删除**。基于查询的 CDC 在数据量小、源库是只读从库、或者对方 DBA 死活不给 binlog 权限时才会退而求其次。

> [!warning] 基于查询的 CDC 最致命的两个问题
> 1. **删除捕获不到**。物理 `DELETE` 在表里什么都不剩，轮询只能"发现这个人消失了"，但**无法区分"被删了"和"还没同步过来"**，只能靠全表比对，成本爆炸。
> 2. **压力与数据量强相关**。`update_time` 有索引也要扫增量区间；一旦有热点 `UPDATE`（比如批量刷字段），一次轮询就是几十万行。而 binlog 是**写入量**的函数，与表的总量无关。

### 1.2 日志型 CDC 能拿到的信息

以 MySQL binlog（`ROW` 格式）为例，一条 `UPDATE` 事件里包含：

- **前镜像 `before`**：改之前那一行的完整字段
- **后镜像 `after`**：改之后那一行的完整字段
- 执行的库、表、`ts_ms`、binlog 文件名 + 位点（或 GTID）
- 事件类型：`INSERT` / `UPDATE` / `DELETE` / `QUERY`（DDL）

这正好对应 Flink SQL 动态表的四种 changelog 消息：`+I`（插入）、`-U`（更新前）、`+U`（更新后）、`-D`（删除）。**前镜像是否存在，决定了下游能不能做撤回（retract）语义**——这是 `binlog_row_image=FULL` 必须配的原因，后面讲。

---

## 二、Debezium 原理：binlog、位点与全量增量的切换

Flink CDC 的 MySQL 连接器底层就是 **Debezium MySQL Connector**（`flink-connector-mysql-cdc` 内嵌，不是外部进程）。所以面试里问 "Flink CDC 原理" 时，一半答案其实是 Debezium 的答案。

### 2.1 伪装成从库

Debezium 做的事情和 MySQL 主从复制的从库一模一样：

1. 用 `REPLICATION SLAVE` / `REPLICATION CLIENT` 权限，连上 MySQL 发送 `COM_BINLOG_DUMP`
2. 声明一个**唯一的 `server-id`**（不能和真实从库、其他 CDC 实例撞）
3. 从指定 **`file + position`** 或 **`GTID set`** 开始，持续接收 binlog event
4. 把 event 反序列化成结构化变更记录，附带位点元数据

| 概念 | 说明 | 影响 |
| --- | --- | --- |
| `server-id` | CDC 实例在主库眼里的身份 | 撞号会导致主库踢掉其中一个连接，表现为**别人的 CDC 一上线你的作业就断连重连** |
| `file + position` | binlog 文件与偏移 | 最通用的位点，主从切换后可能失效 |
| `GTID set` | 全局事务 ID 集合 | 更适合主从切换/容灾，需要 `gtid_mode=ON` |
| `binlog_row_image=FULL` | 变更记录带全字段前后镜像 | `MINIMAL` 时 `before` 只有主键、`after` 只有变更列，下游拿不到完整行，**撤回和 upsert 都会出错** |

> [!important] 位点（offset）不是"存在 Kafka 里"
> Flink CDC 的位点是**算子状态**，跟着 Checkpoint 一起落到状态后端。所以：
> - 作业正常从 Checkpoint/Savepoint 恢复 → 位点自动续上；
> - 从**空状态**启动且 `scan.startup.mode=initial` → 重新走一遍全量 + 增量，**下游会收到重复数据**；
> - 位点是否有效，取决于**主库 binlog 是否还在**，而不是 Flink 存得对不对。
>
> 这就是"binlog 被清理导致位点失效"这一类线上事故的根因，详见第七节。

### 2.2 源库前置条件（上线前必须逐条确认）

| 项 | 要求 | 不满足时的现象 |
| --- | --- | --- |
| `binlog_format` | **ROW**（不能是 STATEMENT/MIXED） | 连接器启动直接报错 |
| `binlog_row_image` | **FULL** | 能跑，但 `before/after` 残缺，更新/删除语义错乱 |
| `binlog` 是否开启 | `log_bin=ON` | 无法订阅 |
| `server-id` | 每个 CDC 实例唯一；Flink CDC 会按 subtask 派生 | 连接被顶掉、反复重连 |
| `gtid_mode` | 用 GTID 位点时必须 `ON` + `enforce_gtid_consistency=ON` | 只能退回 file+position |
| binlog 保留时长 | 必须 **大于** 最长故障恢复窗口（`binlog_expire_logs_seconds` / 旧版 `expire_logs_days`） | 位点被清理，恢复即失败 |
| 时区 | 连接器用 `server-time-zone` 显式声明，不要依赖默认值 | 时间字段整体偏移 N 小时 |
| 权限 | 见下表 | 启动阶段或全量阶段报权限错 |

**权限清单（最小集）**：

```sql
-- 建议单独建账号，不要用 root
CREATE USER 'cdc_user'@'%' IDENTIFIED BY 'xxx';

GRANT SELECT, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'cdc_user'@'%';
-- 若快照阶段需要加锁/读一致性视图，按需追加：
GRANT RELOAD, LOCK TABLES ON *.* TO 'cdc_user'@'%';

FLUSH PRIVILEGES;
```

- `SELECT`：读全量数据
- `REPLICATION SLAVE` / `REPLICATION CLIENT`：订阅 binlog、读位点
- `SHOW DATABASES`：枚举库表
- `RELOAD`：`FLUSH TABLES WITH READ LOCK` 需要它（旧版快照加锁路径）
- 新版 MySQL 文档里对 `REPLICATION SLAVE` 有对应的新表述，按你实际版本用 `SHOW GRANTS` 验证即可

### 2.3 全量 + 增量怎么切换（这是 CDC 最难的部分）

用户真正关心的不是"能同步"，而是 **"同步的时候业务能不能继续写、能不能不锁表"**。历史上有两代做法。

**第一代：加锁快照（Debezium 经典模式）**

```
FLUSH TABLES WITH READ LOCK;   -- 全局读锁，业务写入阻塞
SHOW MASTER STATUS;            -- 记录位点
-- 事务里 SELECT 全表（可重复读，看到一致快照）
UNLOCK TABLES;                 -- 尽快释放
-- 然后从记录的位点开始追 binlog
```

- 优点：逻辑简单，一定能拿到一致快照
- 缺点：**全局读锁期间业务写入全部阻塞**。大表全量几十分钟，锁就是几十分钟，绝大多数生产库不可接受
- Debezium 提供了 `snapshot.locking.mode=minimal`（只锁极短时间）和 `none`（完全不加锁）来缓解，但 `none` 会带来一致性问题：**全量读到的行和 binlog 起点之间可能有缝隙**，需要靠 `SELECT ... FOR UPDATE` 之类的技巧补偿

**第二代：增量快照（Flink CDC 2.x 的 `scan.incremental.snapshot.enabled`，默认开启）**

核心思想是把"快照 + 追日志"揉成一个并行、可断点续传的过程：

1. **分片（chunk）**：按主键把表切成若干区间（`chunk` 大小由 `scan.incremental.snapshot.chunk.size` 控制，大致是每个分片的行数上限）
2. **每个分片独立读取**：多个 subtask 并行读不同分片，互不影响 → **这就是并行度能提速全量的原因**
3. **记录低水位 / 高水位位点**：读取某个分片前记录一次位点（低位点），分片读完后再记录一次（高位点）
4. **分片完成后继续消费该分片区间内的 binlog**：把"快照读到的静态数据"和"读取期间发生的变更"合并，输出**去重后的最新结果**
5. **位点与已完成分片状态一起进 Checkpoint**：作业挂掉重启，已完成的分片不重跑，未完成的从断点继续 → **断点续传**

> [!note] 为什么第二代能做到不停机、不锁表
> 因为一致性不再靠"锁住不许写"来保证，而是靠 **"快照 + 位点区间内的变更重放"** 保证：
> 分片读到的是某个时刻的行版本，位点区间内的 binlog 又覆盖了这个分片在读取期间发生的所有变更，两者合并后结果收敛到正确值。**没读到的靠日志补，读旧了的靠后写覆盖**。
>
> 代价是：全量阶段**下游会看到一部分中间态**（比如某行的值被更新了两次），所以要求**下游必须支持 upsert（按主键覆盖）**，不能用纯 append 语义消费。这是很多"实时数仓数据比离线多几条/差点"的根因之一。

### 2.4 并行度与分片的关系

```sql
-- 分片粒度：太大 → 并行低、单分片慢；太小 → 元数据/位点记录开销大、频繁切换
'scan.incremental.snapshot.chunk.size' = '8096',

-- 每个分片每次 fetch 的行数：影响内存与一次网络往返的量
'scan.snapshot.fetch.size' = '1024',

-- 一个分片内 binlog 回放的最大时长（超过就把剩余部分留给下一个分片继续）
'scan.incremental.snapshot.chunk.key-column' = 'id',   -- 默认取主键第一列，联合主键需显式指定
```

| 参数 | 作用 | 调大 | 调小 |
| --- | --- | --- | --- |
| `scan.incremental.snapshot.chunk.size` | 每个分片的行数上限 | 分片少、并行度利用不足、单点耗时长 | 并行度高、全量更快，但位点记录/切换开销上升 |
| `scan.snapshot.fetch.size` | 单次拉取行数 | 吞吐高、内存占用大 | 内存友好、往返次数多 |
| 源表并行度（在 DDL 里 `/*+ OPTIONS('scan.parallelism'='4') */` 或 source 的 `source.parallelism`） | 快照阶段实际并发 | 源库压力线性上升 | 全量慢 |

**关键结论：CDC Source 的并行度决定全量阶段的并发读**，而**增量阶段所有 subtask 都会各自连一个 binlog 连接**（这是 `server-id` 需要按 subtask 派生的原因）。所以：

- 全量阶段想快 → 提并行度（但要评估源库 IO/CPU）
- 增量阶段并行度太高没有收益，反而增加主库连接数
- 实践中常见做法：**全量用较高并行度，稳定后在线降并行度**（需要 Savepoint 且受 key group 限制，见 [[9-部署与运维]]）

### 2.5 无主键表：必须知道的限制

增量快照的**分片依赖主键**。没有主键时：

- 无法切分片 → 退化成**单并行度整表扫描**，大表会非常慢
- 无法保证分片读取的一致性边界 → 结果可能重复或遗漏
- 某些版本直接报错或需要显式打开兼容开关

> [!danger] 线上务必避免用无主键表做 CDC 源
> 正确做法是**推动业务加主键或唯一索引**，而不是找开关绕过。如果确实无法加，退路是：把表当 append 流处理（不要求 upsert），或者走基于查询的 CDC 全量比对 + 离线校准，但这两条都会显著抬高后续维护成本。

---

## 三、Flink CDC 连接器的两种用法

### 3.1 依赖与版本

```xml
<!-- DataStream API 用法 -->
<dependency>
  <groupId>com.ververica</groupId>
  <artifactId>flink-connector-mysql-cdc</artifactId>
  <version>${flink-cdc.version}</version>
</dependency>
```

```bash
# Flink SQL 用法：把带依赖的 uber jar 放进 lib/
$FLINK_HOME/lib/flink-sql-connector-mysql-cdc-<version>.jar

# 其他常见连接器，同样有 sql 版 uber jar
flink-sql-connector-postgres-cdc
flink-sql-connector-mongodb-cdc
flink-sql-connector-oracle-cdc
flink-sql-connector-sqlserver-cdc

# 通用连接器（Flink 官方仓库）
flink-connector-kafka
flink-sql-connector-kafka
flink-connector-jdbc
```

> [!warning] `flink-connector-mysql-cdc` 与 `flink-sql-connector-mysql-cdc` 的区别
> 前者是普通 jar（依赖需要你自己管理/打入 uber jar，容易和 Flink 内置的 Debezium、Jackson 版本冲突）；后者是**已打包全部依赖的 shaded uber jar，专用于 SQL CLI / SQL 作业**。搞混的典型症状是 `ClassNotFoundException` 或者 `NoSuchMethodError`（Jackson / Kafka client 版本冲突）。
>
> 生产建议：**SQL 作业统一用 `flink-sql-connector-*`，并且绝不要把普通 jar 和 sql jar 同时放进 lib/**。

### 3.2 DataStream API：`MySqlSource`

```java
import com.ververica.cdc.connectors.mysql.source.MySqlSource;
import com.ververica.cdc.connectors.mysql.table.StartupOptions;
import com.ververica.cdc.debezium.JsonDebeziumDeserializationSchema;

MySqlSource<String> source = MySqlSource.<String>builder()
    .hostname("mysql-host")
    .port(3306)
    .databaseList("order_db")            // 库级订阅
    .tableList("order_db.order_info")    // 表级订阅，必须写成 db.table
    .username("cdc_user")
    .password("xxx")
    .serverTimeZone("Asia/Shanghai")     // 必配，否则时间整体偏移
    .serverId("5401-5404")               // 支持区间，按 subtask 分配
    .startupOptions(StartupOptions.initial())
    .deserializer(new JsonDebeziumDeserializationSchema())
    .build();

env.fromSource(source, WatermarkStrategy.noWatermarks(), "mysql-cdc")
   .setParallelism(4)
   .print();
```

| Builder 方法 | 对应 SQL option | 说明 |
| --- | --- | --- |
| `hostname` / `port` | `hostname` / `port` | 建议给从库或专用只读实例 |
| `databaseList` / `tableList` | `database-name` / `table-name` | **都是正则**，`tableList` 必须 `db.table` 全名 |
| `serverTimeZone` | `server-time-zone` | 强烈建议显式设置 |
| `serverId` | `server-id` | 支持 `5401-5404` 区间写法 |
| `startupOptions` | `scan.startup.mode` | `initial` / `latest-offset` / `earliest-offset` / `specific-offset` / `timestamp` |
| `deserializer` | `format` | DataStream 用 Debezium 反序列化 schema |
| `debeziumProperties` | `debezium.*` | 透传给 Debezium，如 `debezium.snapshot.mode` |

### 3.3 Flink SQL：`connector = 'mysql-cdc'`（生产主流）

```sql
CREATE TABLE mysql_order (
    id            BIGINT,
    order_no      STRING,
    user_id       BIGINT,
    amount        DECIMAL(18, 2),
    status        INT,
    create_time   TIMESTAMP(3),
    update_time   TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector'                     = 'mysql-cdc',
    'hostname'                      = 'mysql-host',
    'port'                          = '3306',
    'username'                      = 'cdc_user',
    'password'                      = 'xxx',
    'database-name'                 = 'order_db',
    'table-name'                    = 'order_info',
    -- 启动位点：initial 全量+增量；latest-offset 只追增量；specific-offset 指定位点
    'scan.startup.mode'             = 'initial',
    -- 时区必须与源库一致，否则 TIMESTAMP 字段整体偏移
    'server-time-zone'              = 'Asia/Shanghai',
    -- 快照模式：initial / schema_only / schema_only_recovery / never 等
    'debezium.snapshot.mode'        = 'initial',
    -- 增量快照与分片
    'scan.incremental.snapshot.enabled'      = 'true',
    'scan.incremental.snapshot.chunk.size'   = '8096',
    'scan.snapshot.fetch.size'               = '1024',
    -- 心跳：源库长期无写入时，靠心跳推进位点、避免位点长时间不更新
    'heartbeat.interval'            = '30s',
    -- 连接与重试
    'connect.timeout'               = '30s',
    'connect.max-retries'           = '3',
    'connection.pool.size'          = '20'
);
```

**必须理解的几个细节：**

| 细节 | 为什么重要 |
| --- | --- |
| `PRIMARY KEY (id) NOT ENFORCED` | CDC 源必须声明主键，Flink SQL 才知道这是 **upsert/changelog 流**。注意 `NOT ENFORCED` 表示 Flink 不做校验，只是元数据声明 |
| `database-name` / `table-name` 是**正则** | 写 `order_db` 会匹配到 `order_db_2` 这类库；精确匹配要用 `^order_db$`。这个坑在多库分表的场景下非常常见 |
| `scan.startup.mode=initial` | 默认值。**第一次上线、且下游是 upsert sink** 时用；纯增量场景用 `latest-offset` |
| `scan.startup.mode=specific-offset` | 配合 `scan.startup.specific-offset.file` + `.pos`，或用 `scan.startup.specific-offset.gtid-set` |
| `debezium.snapshot.mode=schema_only` | 不导历史数据、只同步 DDL schema，然后从当前位点追增量。**表已经用离线灌过历史数据时用这个** |
| `server-time-zone` | 不配或配错，`create_time` 会整体差 8 小时。跨国/多时区集群尤其危险 |
| `heartbeat.interval` | 源库空闲时 binlog 不推进，位点在 checkpoint 里一直不变；心跳事件让位点持续前进，也能更快感知连接断开 |

### 3.4 启动模式选择决策表

| 场景 | 推荐 `scan.startup.mode` | 原因 |
| --- | --- | --- |
| 首次上线，下游是 upsert sink（Doris/StarRocks/PG） | `initial` | 历史 + 增量一次搞定，幂等吸收重复 |
| 首次上线，下游是 append-only（如 Kafka 归档） | `initial`（但下游要能容忍中间态）或先离线灌历史再 `latest-offset` | append 下游消化不了 upsert 语义 |
| 灰度/加一个新链路，只要增量 | `latest-offset` | 从当前位点开始 |
| 从某个已知时间点补数 | `timestamp` | 按时间戳找位点 |
| 明确知道 file+pos 或 GTID | `specific-offset` | 精确接续，适合灾后恢复 |
| 只想同步 schema、不要数据 | `debezium.snapshot.mode=schema_only` | 避免全量打爆源库 |
| 位点已失效、又不想重跑全量 | `debezium.snapshot.mode=schema_only_recovery` | 尝试从已有 schema 历史恢复位点；**失败率高，谨慎** |

---

## 四、CDC 到下游：三条生产链路

这一节是岗位热点——面试官问 "你们实时数仓怎么搭的"，答的就是这三种组合。

### 4.1 链路一：MySQL CDC → Kafka（ODS 解耦层）

**为什么要有这一层**：CDC 直连计算作业的问题是**耦合**——每加一个下游就要重新连一次源库（多一个 `server-id`、多一份主库压力、多一份权限申请）。加一层 Kafka 之后，**源库只被订阅一次**，下游各自消费。

```sql
-- ① CDC 源表
CREATE TABLE mysql_order (
    id          BIGINT,
    order_no    STRING,
    user_id     BIGINT,
    amount      DECIMAL(18, 2),
    status      INT,
    update_time TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector'      = 'mysql-cdc',
    'hostname'       = 'mysql-host',
    'port'           = '3306',
    'username'       = 'cdc_user',
    'password'       = 'xxx',
    'database-name'  = 'order_db',
    'table-name'     = 'order_info',
    'server-time-zone' = 'Asia/Shanghai'
);

-- ② Kafka sink：保留完整 changelog 语义
CREATE TABLE kafka_order_ods (
    id          BIGINT,
    order_no    STRING,
    user_id     BIGINT,
    amount      DECIMAL(18, 2),
    status      INT,
    update_time TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector'                    = 'kafka',
    'topic'                        = 'ods_order_info',
    'properties.bootstrap.servers' = 'kafka-1:9092,kafka-2:9092',
    'properties.group.id'          = 'flink-cdc-order-writer',
    -- 关键：用 changelog-json 或 debezium-json 保留 +I/-U/+U/-D
    'format'                       = 'changelog-json',
    'sink.partition-strategy'      = 'hash',
    'sink.parallelism'             = '4',
    'properties.enable.idempotence' = 'true'
);

INSERT INTO kafka_order_ods SELECT * FROM mysql_order;
```

> [!tip] `changelog-json` vs `debezium-json`：ODS 层怎么选
>
> | 格式 | 结构 | 适用 |
> | --- | --- | --- |
> | `debezium-json` | 保留 `before` / `after` / `op`（`c`/`u`/`d`/`r`）/ `source` 元数据 | 与 Debezium 生态对接；下游想拿到前后镜像 |
> | `changelog-json` | Flink 归一化格式 `{"data": {...}, "op": "+I"}` | Flink 内部链路的"普通话"，语义干净，推荐 |
> | `canal-json` / `maxwell-json` | 兼容 Canal / Maxwell 协议 | 已有历史消费方按这两种协议解析 |
>
> `op` 与 Flink SQL 的对应关系：`+I` = 插入、`-U` = 更新前、`+U` = 更新后、`-D` = 删除。**用 `debezium-json` 写 Kafka sink 时，只有 changelog 流才能写进去（`INSERT INTO ... SELECT` 的结果必须是 changelog）**——详细语义见 [[8-FlinkSQL与TableAPI]]。

**注意**：如果这一层要作为 ODS 长期存储，Kafka 必须**开启 log compaction** 或足够的 retention，否则位点失效时无法回放重建 ODS。与 [[11-端到端一致性]] 中的"下游幂等/可重放"是同一件事。

### 4.2 链路二：MySQL CDC → Flink SQL 清洗聚合 → Doris / StarRocks（实时数仓标准链路）

这是**最典型、面试最高频**的一条链路。

```sql
-- ============ ODS：CDC 原始贴源 ============
CREATE TABLE ods_order (
    id          BIGINT,
    order_no    STRING,
    user_id     BIGINT,
    product_id  BIGINT,
    amount      DECIMAL(18, 2),
    status      INT,
    create_time TIMESTAMP(3),
    update_time TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector'      = 'mysql-cdc',
    'hostname'       = 'mysql-host',
    'port'           = '3306',
    'username'       = 'cdc_user',
    'password'       = 'xxx',
    'database-name'  = 'order_db',
    'table-name'     = 'order_info',
    'server-time-zone' = 'Asia/Shanghai'
);

-- ============ 维表：用户维度（Lookup Join） ============
CREATE TABLE dim_user (
    user_id   BIGINT,
    user_name STRING,
    city      STRING,
    level     INT,
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector'      = 'mysql-cdc',
    'hostname'       = 'mysql-host',
    'port'           = '3306',
    'username'       = 'cdc_user',
    'password'       = 'xxx',
    'database-name'  = 'user_db',
    'table-name'     = 'user_info',
    'server-time-zone' = 'Asia/Shanghai'
);

-- ============ DWD：清洗 + 维表打宽 ============
CREATE TABLE dwd_order_detail (
    order_id    BIGINT,
    order_no    STRING,
    user_id     BIGINT,
    user_name   STRING,
    city        STRING,
    amount      DECIMAL(18, 2),
    status      INT,
    dt          STRING,
    PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
    'connector'     = 'doris',
    'fenodes'       = 'doris-fe:8030',
    'table.identifier' = 'dwd.dwd_order_detail',
    'username'      = 'root',
    'password'      = 'xxx',
    -- 幂等：靠 label 前缀 + 事务 label 保证重复提交被 Doris 去重
    'sink.label-prefix' = 'dwd_order_detail',
    -- 允许下发 -D / -U 语义（DELETE / UPDATE）
    'sink.enable-delete' = 'true',
    -- 开启两阶段提交，配合 checkpoint 做端到端一致
    'sink.properties.format'          = 'json',
    'sink.properties.read_json_by_line' = 'true'
);

INSERT INTO dwd_order_detail
SELECT
    o.id,
    o.order_no,
    o.user_id,
    u.user_name,
    u.city,
    o.amount,
    o.status,
    DATE_FORMAT(o.create_time, 'yyyyMMdd') AS dt
FROM ods_order AS o
LEFT JOIN dim_user FOR SYSTEM_TIME AS OF o.create_time AS u
    ON o.user_id = u.user_id;
```

```sql
-- ============ DWS：轻聚合（每分钟成交额） ============
CREATE TABLE dws_trade_minute (
    window_start TIMESTAMP(3),
    city         STRING,
    order_cnt    BIGINT,
    gmv          DECIMAL(20, 2),
    PRIMARY KEY (window_start, city) NOT ENFORCED
) WITH (
    'connector'        = 'starrocks',
    'jdbc-url'         = 'jdbc:mysql://starrocks-fe:9030',
    'load-url'         = 'starrocks-fe:8030',
    'database-name'    = 'dws',
    'table-name'       = 'dws_trade_minute',
    'username'         = 'root',
    'password'         = 'xxx',
    -- 主键模型下按主键 upsert，天然幂等
    'sink.properties.format'      = 'json',
    'sink.properties.strip_outer_array' = 'true'
);

INSERT INTO dws_trade_minute
SELECT
    TUMBLE_START(o.create_time, INTERVAL '1' MINUTE) AS window_start,
    u.city,
    COUNT(DISTINCT o.id)                             AS order_cnt,
    SUM(o.amount)                                    AS gmv
FROM ods_order AS o
LEFT JOIN dim_user FOR SYSTEM_TIME AS OF o.create_time AS u
    ON o.user_id = u.user_id
WHERE o.status = 2          -- 已支付
GROUP BY TUMBLE(o.create_time, INTERVAL '1' MINUTE), u.city;
```

**关键点逐个说明：**

| 点 | 说明 |
| --- | --- |
| **upsert sink 能力** | Doris/StarRocks 必须用 **Unique Key 模型 + Merge-on-Write**，才能接收 `-U/+U/-D` 并做覆盖。Aggregate/Duplicate 模型接 changelog 会出现重复行 |
| **主键声明** | sink DDL 里写 `PRIMARY KEY (...) NOT ENFORCED`，Flink 才知道要做 upsert。**不写主键，Flink 会按 append 写入，更新变成新增行** |
| **`sink.label-prefix`** | Doris 用事务 label 做幂等：同 label 的导入被判定为重复提交而丢弃。**checkpoint 恢复后重放的数据靠它去重**，必须显式且全局唯一 |
| **`sink.enable-delete`** | 不开则删除事件被忽略，下游出现"永远删不掉"的脏数据 |
| **`sink.properties.*`** | 透传给 Doris/StarRocks Stream Load 的参数（`format`、`read_json_by_line`、`strip_outer_array`、`partial_columns` 等），格式和 Stream Load 文档一致 |
| **两阶段提交** | Doris/StarRocks 连接器支持 2PC，让下游写入与 Flink checkpoint 对齐，从而实现**端到端精确一次**；不开则退化为至少一次（靠主键幂等兜底） |
| **维表 Join** | `FOR SYSTEM_TIME AS OF` 是 Temporal Join，本质是"按事件时间查维表当时的版本"。若维表是普通表，Lookup Join 的缓存有效期（`lookup.cache.ttl` / `lookup.cache.max-rows`）决定维表变更延迟。详见 [[8-FlinkSQL与TableAPI]] |

### 4.3 链路三：多源 CDC 汇聚

典型场景：订单库 + 支付库 + 用户库（异构库/异构源）汇聚成一张宽表，或者同一张逻辑表分库分表后要合并。

**Flink SQL 的多源合并有两种写法：**

```sql
-- 写法 A：UNION ALL 合并（要求字段对齐，且必须是 changelog 而非 append）
INSERT INTO dwd_trade_union
SELECT id, order_no, amount, update_time FROM ods_order_db1
UNION ALL
SELECT id, order_no, amount, update_time FROM ods_order_db2;

-- 写法 B：分库分表正则订阅（一个 source 直接吃多张表）
-- 'database-name' = 'order_db_[0-9]+'
-- 'table-name'    = 'order_info_[0-9]+'
```

| 写法 | 优点 | 风险 |
| --- | --- | --- |
| 正则多表订阅 | 一个 source、一份 `server-id`、走同一份状态 | 分片数量变化（新加表）会改变状态结构，**可能无法用 Savepoint 恢复** |
| `UNION ALL` 显式合并 | 拓扑清晰，加库只改 SQL 加源 | 每个源一份 `server-id`、各自一套状态，主库连接数上升 |
| 多源 + 主键冲突 | upsert sink 主键天然合并 | **不同库的自增主键会撞车**，必须用业务唯一键（如订单号）做主键 |

> [!danger] 分库分表合并时最容易踩的坑
> 表 A 的 `id=1001` 和表 B 的 `id=1001` 是两条完全不同的业务记录。如果 sink 主键用了 `id`，**它们会互相覆盖，数据静默丢失**。
>
> 正确做法：sink 主键用**全局唯一业务键**（`order_no`、`(db_tag, id)` 组合键），并在 DWD 层补一个 `source_db` 标识字段用于排查。

---

## 五、实时数仓分层：ODS / DWD / DWS / ADS

### 5.1 分层在实时链路里的对应物

| 层 | 职责 | 实时链路里是什么 | 典型存储 | 典型延迟 |
| --- | --- | --- | --- | --- |
| **ODS** | 贴源，尽量不做业务加工 | CDC 出来的 changelog 流，按表落到 Kafka 或直接进计算 | Kafka（开 compaction）/ Doris 明细表 | 秒级 |
| **DWD** | 清洗、去重、维表打宽、标准化 | `CDC + Lookup Join + 过滤/脱敏` 的 Flink SQL 作业 | Doris/StarRocks 明细大宽表 | 秒级~十秒级 |
| **DWS** | 轻度聚合，按主题/维度做宽表 | 窗口聚合（`TUMBLE/HOP`）+ `GROUP BY` 维度 | Doris/StarRocks 聚合表 | 分钟级 |
| **ADS** | 面向具体应用/报表的指标 | 再聚合 / 指标计算 / 直接写 OLAP 或 KV | Doris/StarRocks/ClickHouse/Redis | 分钟级 |

**关键认知**：实时分层不是"把离线的分层照搬一遍"，而是**在 Flink SQL 的作业 DAG 里体现**。一个作业里可以做 DWD，也可以 DWD+DWS 串起来（`INSERT INTO` 多条语句），但要注意：

- 串在同一个作业里 → 省一次落地、延迟更低，但**状态更大、故障影响面更大、扩缩容更难**
- 中间落地 Kafka/OLAP → 解耦、可独立扩缩容和重放，但**延迟 +1 跳、存储成本上升**

生产上常见折中：**ODS/DWD 落地 Kafka 或 Doris，DWS/ADS 串成独立作业**。

### 5.2 与离线数仓的关系：口径统一是最大难点

| 对比项 | 离线数仓 | 实时数仓 |
| --- | --- | --- |
| 计算引擎 | Hive/Spark，跑批 | Flink，常驻流 |
| 数据范围 | 全量、可回溯、可重跑 | 增量、状态有限、重跑成本高 |
| 时间口径 | 业务时间/分区时间，T+1 结算 | 事件时间 + watermark，有迟到数据问题 |
| 一致性 | 可重复执行，幂等重跑 | 依赖 checkpoint + 下游幂等 |
| 延迟 | 小时/天 | 秒/分钟 |
| 正确性验证 | 与历史对比、抽样 | 与离线 T+1 结果**对账** |

> [!important] 实时与离线结果对不上的排查顺序
> 1. **口径定义不同**（最常见）：离线 `dt` 按业务日期分区，实时按事件时间窗口，跨天订单归属不同
> 2. **迟到数据**：实时已输出的窗口结果没有包含迟到记录，离线包含了
> 3. **状态 TTL 过期**：实时关联的维表/历史状态被清理，导致 join 不上
> 4. **CDC 漏数据**：位点失效、无主键表分片遗漏
> 5. **去重语义**：实时 upsert 覆盖 vs 离线保留明细
>
> 结论：**口径统一要靠"统一定义层"**——把指标口径写成一份可复用的 SQL/配置，离线和实时都从它生成，而不是两拨人各写一遍。

### 5.3 Lambda vs Kappa

| 维度 | Lambda（批 + 流双链路） | Kappa（只有流） |
| --- | --- | --- |
| 链路数量 | 2 套（离线批 + 实时流） | 1 套 |
| 逻辑一致性 | 两套代码，**口径天然会漂移** | 一套代码，口径天然一致 |
| 实时链路复杂度 | 可以写"近似简化版"，压力小 | 必须做到和生产级一样正确 |
| 历史重算 | 批链路重跑，简单 | 需要回放 Kafka/数据湖，**依赖上游可重放 + 长保留** |
| 存储成本 | 离线存储 + 实时存储，双份 | 依赖 Kafka 长保留或数据湖（成本后置） |
| 团队要求 | 可以分批流两个团队 | 要求团队强、流处理能力成熟 |
| 适用 | 实时性要求不极致、历史重算频繁、团队流经验弱 | 实时性要求高、逻辑复杂易漂移、愿意投入流平台建设 |

**实践中的第三种：流批一体**。同一套 Flink SQL，用同一个 source 定义（Kafka + 离线表），批模式跑历史、流模式跑增量，逻辑一份。这是目前主流平台的演进方向——本质上是用"一份逻辑 + 两种执行模式"替代 Lambda 的两份逻辑。

### 5.4 维表：Lookup Join vs 广播状态

| 方式 | 实现 | 更新实时性 | 状态规模 | 适用 |
| --- | --- | --- | --- | --- |
| **Lookup Join**（`FOR SYSTEM_TIME AS OF`） | 每条流记录去外部存储查一次，带本地缓存 | 取决于 `lookup.cache.ttl` | 只在缓存里有，不占 Flink 状态 | 维表大（千万级以上）、变更不频繁 |
| **Temporal Join**（版本表） | 维表 changelog 全部进状态，按时间版本匹配 | 实时（随 changelog 更新） | **全量维表进状态**，很大 | 维表中等规模、要求精确历史版本 |
| **广播状态**（BroadcastState / `/*+ BROADCAST(dim) */`） | 小维表广播到每个 subtask 内存 | 实时 | 每并行度一份，**乘以并行度** | 维表小（万级以内）、变更频繁 |

```sql
-- Lookup Join 的缓存配置（DDL 里给维表）
'lookup.cache'            = 'PARTIAL',   -- 或 FULL
'lookup.partial-cache.max-rows' = '100000',
'lookup.partial-cache.expire-after-write' = '10min',
'lookup.partial-cache.cache-missing-key'  = 'true',
'lookup.max-retries'      = '3'
```

> [!warning] Lookup Join 的缓存代价
> `lookup.cache.ttl` 调大 → 维表变更可见延迟就是 TTL 那么久；调小 → 外部存储 QPS 飙升（**每条流记录一次查询**，高峰期能打爆维表库）。
> 需要"实时性 + 大维表"时，正确解法是**维表 changelog 进状态用 Temporal Join**，或者**读维表的 CDC 流做 interval join**，而不是硬调 TTL。状态膨胀的治理见 [[3-状态管理]]。

---

## 六、幂等与一致性：CDC 链路怎么做到不丢不重

**三段式**（与 [[11-端到端一致性]] 完全一致，只是把 Source 换成 CDC）：

```
① Source 端：binlog 位点 = 算子状态 → 进 Checkpoint（不丢的保证）
② 中间计算：状态快照 + 屏障对齐 → 故障后回到一致点（不重的保证，在 Flink 内部）
③ Sink 端：两阶段提交（2PC）或 主键 upsert 幂等（端到端不重的保证）
```

### 6.1 CDC 场景下的三段式逐段拆解

| 环节 | 机制 | 失效后果 |
| --- | --- | --- |
| **CDC 位点** | `file+pos` / GTID 存在 source 的 operator state 里，随 checkpoint 落盘 | 恢复后从错误位点开始 → 重复或丢数据 |
| **Checkpoint 间隔** | 决定"最多重放多少数据" | 间隔太长 → 恢复后重放量大，下游压力大 |
| **下游 upsert 主键** | 相同主键覆盖，天然幂等 | 主键选错 → 覆盖丢数据（见 4.3） |
| **两阶段提交** | Sink 先预写、checkpoint 完成后再提交 | 不开则 checkpoint 后、提交前挂掉 → 重复写入（靠主键幂等兜底） |
| **Doris label 幂等** | 相同 `label-prefix + checkpointId` 的事务被判重复 | label 不唯一或复用 → 重复导入 |

> [!note] CDC 链路为什么"比普通流更安全"
> 因为 CDC 是**重放安全**的：只要位点有效，重放同一段 binlog 得到的是同一批变更；再叠加下游主键 upsert，重复天然被吸收。
>
> 真正危险的从来不是"重复"，而是"位点失效后无法重放"（binlog 被清理）和"主键选错导致静默覆盖"。这两点在后文排查表里会重点出现。

---

## 七、生产问题与排查表

| 现象 | 根因 | 排查手段 | 解决 |
| --- | --- | --- | --- |
| 作业启动即失败：`Could not find first log file name` / `binlog ... is not available` | **binlog 被清理**，位点已失效 | `SHOW BINARY LOGS;` 看最早文件；`SHOW VARIABLES LIKE 'binlog_expire_logs_seconds'`（5.7 用 `expire_logs_days`） | 调大保留时长（必须 > 最长恢复窗口）；失效后只能重新全量或从最早可用位点 + 下游对账 |
| 全量阶段源库 CPU/IO 打满、业务告警 | 快照并行度过高 / 未走从库 | 看源库 `SHOW PROCESSLIST`、监控慢查询与 IO | 降低 `scan.parallelism`、调大 `chunk.size`、**CDC 连只读从库**、避开业务高峰 |
| 全量阶段业务写入被阻塞（旧版行为） | 快照走了加锁路径（`FLUSH TABLES WITH READ LOCK`） | 源库 `SHOW PROCESSLIST` 看是否有 `Waiting for global read lock` | 用增量快照（`scan.incremental.snapshot.enabled=true`），配 `debezium.snapshot.locking.mode` |
| 作业反复重连、日志刷 `server id conflict` | 多个 CDC 实例 / 真实从库 `server-id` 撞号 | `SHOW SLAVE HOSTS;` 或对比各 CDC 任务配置 | 为每个 CDC 任务分配独立 `server-id` 区间 |
| 下游出现"删不掉"的数据 | sink 未开删除语义 | 查 sink DDL 是否缺 `sink.enable-delete` / 表模型是否 Duplicate | 改 Unique Key + 开启删除下推 |
| 上游 `ALTER TABLE` 加字段后作业报错或字段错位 | schema 不一致 | 看异常里是否有 `schema` 相关报错；对比源表与 Flink DDL | 同步修改 Flink DDL 并重启（**注意 DDL 变更通常无法状态兼容**）；或用 `schema.change.behavior` 相关配置 |
| 时间字段整体偏移 N 小时 | `server-time-zone` 未配或与源库不一致 | 打印几条记录看 `ts_ms` / 时间字段 | 显式配 `server-time-zone`，并统一链路各环节时区 |
| 断点续传后重复数据大量出现 | 从 Savepoint 恢复失败，退回空状态重跑全量 | 看日志中是否有 `Cannot restore` / `allowNonRestoredState` 提示 | 检查状态兼容性、`maxParallelism`、算子 UID；详见 [[9-部署与运维]] |
| 下游 upsert 主键冲突、数据互相覆盖 | 主键不唯一（分库分表合并、联合主键选错） | 检查 sink 主键定义与业务唯一性 | 改用全局业务唯一键；详见 4.3 |
| 无主键表全量极慢、只有 1 个并发 | 无法分片 | `EXPLAIN` / 日志看 source 并行度 | 推动业务加主键，或改订阅方式 |
| 作业长期无写入时位点不推进 | 源库空闲，binlog 无事件 | 看 checkpoint 里的位点是否长期不变 | 配 `heartbeat.interval` |
| 增量阶段 state 持续增长 | CDC 的 binlog 缓冲/分片状态未释放，或下游聚合状态无 TTL | Flink UI 看 state size 趋势 | 检查是否有未完成的超大分片；给下游聚合配 `table.exec.state.ttl` |

> [!tip] 排查的第一入口永远是这几处
> 1. **Flink Web UI**：Backpressure 页、Checkpoints 页（大小/耗时/失败数）、Metrics 页（`numRecordsIn/Out`）
> 2. **JobManager / TaskManager 日志**：异常堆栈的 root cause 通常在 `.out` 和 `.log` 里
> 3. **源库侧**：`SHOW PROCESSLIST`、`SHOW BINARY LOGS`、`SHOW VARIABLES LIKE 'binlog%'`
> 4. **下游侧**：Doris/StarRocks 的 Stream Load 记录、Kafka 的 lag
>
> 监控指标与告警项的完整清单见 [[9-部署与运维]]。

---

## 八、动手验证：最小可跑的实验环境

> 目标是**建立直觉**，不是搭生产。用 Docker Compose 起三个组件即可。

### 8.1 组件与启动顺序

| 组件 | 作用 | 关键准备 |
| --- | --- | --- |
| **MySQL** | 源库 | 启动参数加 `--log-bin=mysql-bin --binlog-format=ROW --binlog-row-image=FULL --server-id=1`；建库建表、造 3~5 万行数据；建 CDC 账号并授权 |
| **Flink**（Local/Standalone 或 `flink:latest` 镜像 + SQL Client） | 计算 | 把 `flink-sql-connector-mysql-cdc`、`flink-sql-connector-kafka`、Doris/StarRocks 连接器 jar 放进 `lib/`；改 `taskmanager.numberOfTaskSlots` |
| **Kafka**（可选，看链路一） | ODS 解耦 | 建 topic（分区数 ≥ sink 并行度）；`kafka-console-consumer` 观察输出 |
| **Doris / StarRocks**（看链路二） | 下游 OLAP | 建 Unique Key 表；确认 FE/BE 端口（`8030` HTTP、`9030` MySQL 协议）可通 |

**验证点顺序（由简到难）：**

1. `SHOW VARIABLES LIKE 'binlog%'` 确认源库配置全部正确
2. 只跑 CDC → `print()` / Kafka console，确认能看到 `+I/-U/+U/-D` 四种消息
3. 加 OLAP sink，确认表里数据条数与源表一致
4. 再验证增量、断点续传、幂等

### 8.2 怎么确认"全量 + 增量都正确"

| 验证项 | 操作 | 期望 |
| --- | --- | --- |
| **全量正确** | `SELECT COUNT(*)` 对比源表与目标表 | 行数一致（若中途有变更，配合 4 的观察） |
| **增量插入** | 源库 `INSERT` 一行 | 目标表秒级出现该行 |
| **增量更新** | 源库 `UPDATE` 同一行的某字段 | 目标表该行**被覆盖**，不是新增一行 |
| **增量删除** | 源库 `DELETE` 该行 | 目标表该行消失（需 sink 支持删除） |
| **断点续传** | `flink stop` 或 kill 作业 → 源库继续写入若干行 → 从 Savepoint/Checkpoint 重启 | 停摆期间的变更**全部补齐**，无重复行、无丢失 |
| **幂等验证** | 人为从较早的 Savepoint 恢复（制造重放） | 目标表最终行数不变（upsert 吸收重复） |
| **位点失效演练** | 手动 `PURGE BINARY LOGS` 清掉位点所在文件 → 重启 | 观察到明确的"位点失效"报错，理解其不可恢复性 |

> [!example] 一个能立刻看出差异的小实验
> 在源库执行 `UPDATE order_info SET amount = amount + 1 WHERE id = 1;` 连续 5 次。
>
> - 目标表是 **Unique Key + upsert** → 只有 1 行，`amount` 是 +5 后的值
> - 目标表是 **Duplicate/Append** → 出现 6 行，每行一个中间值
>
> 这个实验直接说明"为什么实时数仓的下游必须支持 upsert"。

---

## 九、面试怎么答：CDC 与实时数仓

> [!question] 高频问题清单
> 1. 什么是 CDC？基于日志和基于查询的区别？
> 2. Flink CDC 的全量 + 增量是怎么做的？为什么能做到不停机、不锁表？
> 3. 增量快照的断点续传是怎么实现的？
> 4. CDC 链路怎么保证不丢不重？
> 5. 你们的实时数仓怎么分层？和离线怎么对齐口径？
> 6. 用过哪些下游？为什么选 Doris/StarRocks？
> 7. 线上遇到过什么问题？怎么排查的？
> 8. 无主键表、DDL 变更、时区这几个坑怎么处理？

> [!important] 必答：Flink CDC 怎么做全量 + 增量，为什么不停机
> **四句话骨架**：
> 1. **一次订阅**：CDC 连接器伪装成 MySQL 从库，先拿一份一致性快照，再从快照对应的 binlog 位点开始持续消费变更，**中间不需要停业务**。
> 2. **并行分片**：2.x 的增量快照把表按主键切成 chunk，多个 subtask 并行读不同 chunk；每个 chunk 记录**读取前后的 binlog 位点区间**，chunk 读完后继续消费区间内的变更，把快照数据与变更合并，得到最终一致结果 —— **一致性不靠锁，靠"日志回放补齐"。**
> 3. **断点续传**：已完成的分片 + 当前 binlog 位点都作为**算子状态**写进 Checkpoint。作业挂了从 Checkpoint 恢复，完成的分片不重跑，未完成的分片继续。
> 4. **端到端不重**：位点进 checkpoint 保证"不丢"，下游 upsert 主键（或 2PC）保证"不重"。**位点有效性依赖源库 binlog 保留时长**，这是唯一的硬约束。
>
> **可以主动加分的一句**：全量阶段下游会短暂看到中间态，所以实时数仓的下游必须支持 upsert；如果下游是 append-only 的（比如归档 Kafka），要么先离线灌历史再 `latest-offset` 追增量，要么接受后续对账。

---

> [!note] 关联笔记
> - 动态表与 changelog 语义：[[8-FlinkSQL与TableAPI]]
> - 状态与维表：[[3-状态管理]]
> - 快照与恢复：[[5-Checkpoint与Savepoint]]
> - 端到端一致性的三段式：[[11-端到端一致性]]
> - 部署、内存与监控：[[9-部署与运维]]
> - 回到索引：[[0-Flink总览]]
