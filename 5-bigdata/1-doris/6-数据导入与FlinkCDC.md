---
title: Doris 数据导入与 Flink CDC
tags: [Doris, 数据导入, FlinkCDC, StreamLoad]
status: 进行中
created: 2026-10-09
---

# 🚰 六、数据导入与 Flink CDC

> 本篇回答：**数据怎么进 Doris，以及"不重不丢"到底靠什么保证。**
> 内容覆盖七种导入方式的选型、Stream Load 的协议与 `label` 幂等语义、Routine Load 管理、Flink Doris Connector 的完整配置、Flink CDC → Doris 端到端链路、导入性能调优与故障排查。
> 表模型怎么选（为什么 CDC 用 Unique）见 [[2-数据模型]]；分区分桶怎么建见 [[4-建表与分区分桶]]；导入与 Compaction 的相互影响见 [[8-运维与调优]]；端到端一致性的算法层推导见 [[5-bigdata/0-flink/11-端到端一致性|Flink 11-端到端一致性]]。

---

## 一、导入方式全景对比

### 1.1 七种方式速览（核心表）

| 方式 | 数据源 | 同步/异步 | 适用数据量 | 事务/幂等 | 典型场景 | 主要缺点 |
|---|---|---|---|---|---|---|
| **Stream Load** | 本地文件 / HTTP 客户端 / 程序 | **同步**（HTTP 请求内完成） | 单次 GB 级（受 `streaming_load_max_mb` 约束） | **靠 `label` 幂等**；支持两阶段提交 | 实时链路下游写入（Flink/Spark/自研服务）、小批量高频导入 | 需要自己管批次、重试、label；单次量大时超时风险高 |
| **Broker Load** | HDFS / S3 / 对象存储 | **异步**（提交作业后轮询） | **TB 级** | 事务性导入，失败回滚 | 离线批量导入、数仓 T+1 大批量灌数据 | 依赖 Broker 进程或对象存储；延迟高，不适合实时 |
| **Routine Load** | **Kafka** | 常驻任务，**持续消费** | 持续流式，单批可配 | Doris 内部管理事务 | Kafka 数据直接入仓，**不需要 Flink 就能做简单 ETL** | 只支持 Kafka；表达能力弱（`COLUMNS`/`WHERE` 做不了复杂转换） |
| **INSERT INTO (SELECT)** | Doris 内部表 / External Catalog | 同步（或异步提交） | 中大批量 | 事务性 | 仓内表到表加工、湖到仓的批式导入、External Catalog → Internal | 走的是 SQL 执行路径，占用查询资源；大事务内存压力大 |
| **Spark Load** | HDFS / 对象存储 | 异步（Spark 作业） | TB 级 | 事务性 | **历史遗留方案**，用 Spark 做预处理与全局字典 | 3.x 已不是推荐路径，运维复杂，加了一个 Spark 依赖 |
| **Flink Connector** | Flink 作业（流/批） | 流任务常驻 | 持续流式，可精确控批 | **`label` 幂等 + 可选 2PC** | **实时数仓主链路**（CDC/Kafka → Flink → Doris） | 需要维护 Flink 作业；攒批参数与 checkpoint 需要协同调 |
| **JDBC (INSERT)** | 任意客户端 | 同步 | **小** | 每条 `INSERT` 一个事务 | 少量维表数据、脚本初始化、临时补数 | 吞吐极低，**绝不要用 JDBC 做大批量导入** |

> [!important] 一句话选型
> - **实时链路** → Flink Connector（或 Kafka 场景直接用 Routine Load 省掉 Flink）
> - **离线大批量** → Broker Load
> - **仓内加工** → `INSERT INTO ... SELECT`
> - **少量补数** → JDBC `INSERT`
> - **不要**用 JDBC 扛吞吐，**不要**用 Stream Load 传 TB 级文件。

### 1.2 同步 vs 异步：这个区别比想象中重要

| | Stream Load / INSERT | Broker Load / Spark Load | Routine Load |
|---|---|---|---|
| **调用方是否阻塞** | **阻塞到导入完成**（拿到最终 JSON 才返回） | 只阻塞到"作业提交成功" | 提交后常驻，不阻塞 |
| **失败怎么知道** | 看 HTTP 响应体 | `SHOW LOAD WHERE LABEL='...'` 轮询 | `SHOW ROUTINE LOAD` 看状态与 `ErrorLogUrls` |
| **超时风险** | **高**：HTTP 超时了但导入可能还在跑 | 低 | 低 |
| **适合放进 Flink 的 checkpoint 吗** | 适合（尤其配 2PC） | 不适合 | 不适用 |

> [!warning] "HTTP 超时"最常见的误判
> Stream Load 的 HTTP 请求超时，**不代表导入失败**。BE 可能还在写数据、还在做事务提交。
> 这时候如果用**新的 label** 重试 → **数据重复**；用**同一个 label** 重试 → Doris 会返回 `Label Already Exists`，**这才是正确的重试姿势**（详见 §2.3）。

---

## 二、Stream Load 详解

### 2.1 协议与认证

Stream Load 就是一个 **HTTP PUT/POST** 请求，走 FE 的 HTTP 端口（默认 8030）或直接打 BE 的 HTTP 端口（默认 8040）。

```
PUT /api/{db}/{table}/_stream_load
```

| 项 | 说明 |
|---|---|
| **协议** | HTTP/1.1，`PUT` 或 `POST` 均可 |
| **地址** | `http://<fe_host>:8030/api/{db}/{tbl}/_stream_load`（推荐走 FE，FE 会重定向到 BE） |
| **或直连 BE** | `http://<be_host>:8040/api/{db}/{tbl}/_stream_load`（Flink 连接器内部会向 FE 要 BE 列表再直连） |
| **认证** | HTTP Basic Auth：`-u user:password`；或用 `Authorization` header |
| **请求体** | 就是**数据本身**（CSV / JSON / Parquet 等），不是表单 |
| **响应** | JSON，见 §2.4 |

### 2.2 关键 Header 一览

所有导入参数都通过 HTTP Header 传递（Header 名前缀 `label:` 之外一般无前缀；也有 `Expect: 100-continue` 的用法）。

| Header | 作用 | 取值/示例 | 注意事项 |
|---|---|---|---|
| **`label`** | **本次导入的唯一标识**，幂等的核心 | `label: order_20241009_001` | 见 §2.3，**这是本篇最重要的机制** |
| **`column_separator`** | CSV 列分隔符 | `column_separator: ,` | 特殊字符用 `\x01` 这类十六进制转义 |
| **`line_delimiter`** | 行分隔符 | `line_delimiter: \n` | 默认换行；Windows 文件可能是 `\r\n` |
| **`format`** | 数据格式 | `csv` / `json` / `parquet` / `orc` | JSON 通常还要配 `strip_outer_array` / `jsonpaths` |
| **`columns`** | 列映射与表达式 | `columns: k1,k2,tmp_k3,tmp_k4` | 顺序映射 + 临时列 + 表达式（见下） |
| **`where`** | 导入前过滤 | `where: k1 > 100` | **被过滤掉的行算 unselected**，不算错误 |
| **`max_filter_ratio`** | 允许的**错误行比例**上限 | `max_filter_ratio: 0.1` | **危险参数**，见 §6.3 |
| **`strict_mode`** | 严格模式 | `strict_mode: true` | 见 §6.3，与 `max_filter_ratio` 配合使用 |
| **`merge_type`** | 数据合并类型 | `APPEND` / `DELETE` / `MERGE` | Unique 表的删除/部分列更新语义 |
| **`partial_columns`** | **部分列更新** | `partial_columns: true` | 只写部分列，其余列保留旧值 |
| **`timeout`** | 导入超时（秒） | `timeout: 600` | 大手一批时要显式调大 |
| **`exec_mem_limit`** | 本次导入的内存上限 | `exec_mem_limit: 8589934592` | 大事务所需要 |
| **`two_phase_commit`** | 开启两阶段提交 | `two_phase_commit: true` | 见 §2.5 |
| **`jsonpaths` / `strip_outer_array`** | JSON 解析控制 | `strip_outer_array: true` | JSON 数组导入必配 |
| **`num_as_string`** | 数字按字符串解析 | `num_as_string: true` | 避免大整数精度丢失 |
| **`Expect`** | `Expect: 100-continue` | —— | 让客户端先等服务器确认再传数据体，避免白传 |

**`columns` 的三种用法（很实用）**：

```
# ① 纯顺序映射
columns: order_id,user_id,amount,dt

# ② 跳过文件里的某些列（用临时列承接后丢弃）
columns: order_id,user_id,tmp_ignore,amount,dt

# ③ 用表达式做简单转换（导数 + 常量）
columns: order_id,user_id,amount,dt=now(),src='mysql'
```

### 2.3 `label` 的幂等语义（讲透）

> [!important] 一句话定义
> **`label` 是"这次导入"的全局唯一标识。Doris 保证：同一个 label 在一次成功导入之后，不会产生第二次效果。**
> 这就是 Flink / 自研程序做"不重"的**根本机制**——不是靠客户端记状态，而是靠 Doris 端把这个 label 落盘成事务记录。

**行为矩阵**：

| 场景 | Doris 的响应 | 客户端应该怎么做 |
|---|---|---|
| 首次提交 label | 正常导入，`Status = Success` | 记录成功 |
| **用同一 label 重复提交（前一次已成功）** | 返回失败，`Status = Label Already Exists`，并带出前一次的 `ExistingJobStatus` | **把它当作"成功"处理**——数据已经在里面了 |
| 用同一 label 提交（前一次还在跑） | 拒绝，提示 label 正在被使用 | 等待后重查，或换 label（但要自己保证不重） |
| 用新 label 重传同一批数据 | **正常导入 → 数据重复** | ⚠️ **这是数据重复的头号原因** |
| label 为空 | 大部分版本允许（Doris 内部生成），但**你就失去了幂等能力** | **生产环境永远显式指定 label** |

**所以"不重"的完整逻辑是：**

```
批次数据  ──────►  label = f(批次标识)
                      │
   失败重试 ──────────┘  label 不变
                      │
                      ▼
              Doris 判重（label 已存在）
                      │
          ┌───────────┴───────────┐
          │                       │
     已成功 → 忽略（幂等）      未成功 → 重新导入
```

> [!danger] 三个把幂等搞坏的致命操作
> 1. **用时间戳/UUID 生成 label**：`label = "order_" + System.currentTimeMillis()` —— 每次重试都是新 label，**完全丧失幂等**，重复数据必然产生。
> 2. **Flink 作业重启后改了 `sink.label-prefix`**：新 label 前缀 → 同一批数据换了身份证 → 重复导入。
> 3. **用同一 label 跑了不同批次的数据**（label 复用）：后一批数据会被 Doris **静默拒绝**，你以为是成功，其实**数据丢了**。这比重复更可怕。
>
> **正确做法**：label 必须**由业务批次标识或 Flink 的 checkpoint/batch 编号确定性生成**，且**全局唯一、可重现**。

**label 的命名建议**：

| 组成部分 | 作用 | 示例 |
|---|---|---|
| 业务/表前缀 | 便于 `SHOW LOAD` 里定位 | `dwd_order` |
| 作业/来源标识 | 区分不同链路 | `mysql_cdc` |
| 确定性序号 | **保证重放时一致** | checkpoint id / 批次号 / 上游 binlog 位点 |

### 2.4 返回 JSON 各字段含义

Stream Load 的响应是一个 JSON，**排查问题时每一个字段都有用**：

```json
{
  "TxnId": 1000001,
  "Label": "dwd_order_20241009_0001",
  "Status": "Success",
  "ExistingJobStatus": "FINISHED",
  "Message": "OK",
  "NumberTotalRows": 1000000,
  "NumberLoadedRows": 999900,
  "NumberFilteredRows": 100,
  "NumberUnselectedRows": 0,
  "LoadBytes": 123456789,
  "LoadTimeMs": 5230,
  "BeginTxnTimeMs": 12,
  "StreamLoadPutTimeMs": 45,
  "ReadDataTimeMs": 1200,
  "WriteDataTimeMs": 3100,
  "CommitAndPublishTimeMs": 870,
  "ErrorURL": "http://be:8040/api/_load_error_log?file=__shard_0/error_log_xxx"
}
```

| 字段 | 含义 | 怎么用 |
|---|---|---|
| `TxnId` | 本次导入的事务 ID | 两阶段提交时要用它 commit/abort |
| `Label` | 回显的 label | 对账、重试时确认 |
| **`Status`** | `Success` / `Publish Timeout` / `Fail` / `Label Already Exists` | **`Publish Timeout` 要特别注意**：事务已提交但版本还没可见，**此时重试同一 label 是安全的** |
| `ExistingJobStatus` | 同 label 已存在时的历史状态 | 判断"重复提交"前的状态是 `FINISHED`（已成功）还是 `CANCELLED`（可重试） |
| `Message` | 文本信息 / 错误详情 | 失败原因 |
| **`NumberTotalRows`** | 读取到的总行数 | 与上游对账的基准 |
| **`NumberLoadedRows`** | **实际写入的行数** | 和 Total 差距大就要查过滤原因 |
| **`NumberFilteredRows`** | **因数据质量被过滤的行数** | ⚠️ **这个数字 > 0 就意味着你可能在丢数据**（§6.3） |
| `NumberUnselectedRows` | 被 `WHERE` 条件过滤的行数 | 这是**业务有意过滤**，是正常的 |
| `LoadBytes` | 实际传输字节数 | 评估吞吐 |
| **`LoadTimeMs`** | 总耗时 | SLO 监控 |
| `BeginTxnTimeMs` / `StreamLoadPutTimeMs` / `ReadDataTimeMs` / `WriteDataTimeMs` / `CommitAndPublishTimeMs` | **分阶段耗时** | **定位瓶颈在哪一段**（见下表） |
| **`ErrorURL`** | **错误数据的下载地址** | 拿它去下被拒的具体行，交给上游修数据 |

**分阶段耗时怎么读**：

| 耗时字段大 | 说明瓶颈在 |
|---|---|
| `BeginTxnTimeMs` | FE 事务开启（通常很小，异常大 = FE 压力大/元数据锁） |
| `StreamLoadPutTimeMs` | FE 生成导入执行计划（异常大 = FE 繁忙） |
| `ReadDataTimeMs` | **读取数据**（文件/网络读取慢，或客户端上传慢） |
| `WriteDataTimeMs` | **BE 写数据 + 排序 + 建索引**（最常见的大头；BE 磁盘/CPU 瓶颈） |
| `CommitAndPublishTimeMs` | **事务提交与版本可见**（异常大 = Compaction 压力大 / 版本堆积，见 [[8-运维与调优]]） |

> [!tip] `CommitAndPublishTimeMs` 是"导入变慢"的隐藏凶手
> 很多人只盯 `WriteDataTimeMs`，但**高频小批导入**场景下，`CommitAndPublishTimeMs` 会因为**版本数堆积、Compaction 追不上**而持续变大。
> 这时优化写入批次本身没用——**要治的是 Compaction 和小版本**（§7.5）。

### 2.5 两阶段提交（`two_phase_commit`）

默认情况下，Stream Load 是**一次请求内完成全部阶段**（写数据 → 提交事务 → 发布版本）。这对"和外部系统的原子性"不够用。

**两阶段提交把它拆成两步**：

| 阶段 | 操作 | 结果 |
|---|---|---|
| **① prepare（写数据）** | 正常 `_stream_load` 请求，加 `two_phase_commit: true` | 数据写入成功，但**事务未提交、版本不对外可见**；响应里返回 `TxnId` |
| **② commit / abort** | 调 `_stream_load_2pc` 接口 | `commit` → 数据可见；`abort` → 丢弃本次数据 |

```bash
# 阶段①：preCommit，拿到 TxnId
curl --location-trusted -u root: \
  -H "label: order_txn_1001" \
  -H "two_phase_commit:true" \
  -H "column_separator:," \
  -T /data/order_1001.csv \
  -XPUT http://fe:8030/api/dwd/orders/_stream_load
# → 返回 {"TxnId": 1000001, "Label": "order_txn_1001", "Status": "Success", ...}

# 阶段②：提交
curl --location-trusted -u root: \
  -H "txn_operation: commit" \
  -H "txn_id: 1000001" \
  -XPUT http://fe:8030/api/dwd/orders/_stream_load_2pc

# 或者回滚
curl --location-trusted -u root: \
  -H "txn_operation: abort" \
  -H "txn_id: 1000001" \
  -XPUT http://fe:8030/api/dwd/orders/_stream_load_2pc
```

> [!important] 两阶段提交解决的是什么问题
> 它让"**Doris 的数据可见性**"可以和"**外部系统的提交时机**"对齐——这正是 Flink 做端到端 exactly-once 的思路：
> **checkpoint 期间只 prepare，checkpoint 成功后才 commit。**
> 如果 checkpoint 失败（作业回滚），就 abort 掉未提交的事务，数据不落地，于是"不重"。
>
> 代价：**事务从 prepare 到 commit 之间有生命周期限制**（事务超时），所以它和 checkpoint 间隔是耦合的——**checkpoint 间隔不能超过 Doris 侧的事务超时时间**，否则 commit 会失败。

### 2.6 完整 curl 示例（CSV 与 JSON）

```bash
# ① CSV 导入（含列映射、过滤、严格模式）
curl --location-trusted -u root: \
  -H "label: dwd_order_20241009_0001" \
  -H "column_separator:," \
  -H "line_delimiter:\n" \
  -H "columns: order_id,user_id,tmp_ignore,amount,dt" \
  -H "where: amount > 0" \
  -H "max_filter_ratio:0.01" \
  -H "strict_mode:true" \
  -H "timeout:600" \
  -T /data/order_20241009.csv \
  -XPUT http://fe:8030/api/dwd/orders/_stream_load

# ② JSON 数组导入
curl --location-trusted -u root: \
  -H "label: dwd_order_20241009_0002" \
  -H "format:json" \
  -H "strip_outer_array:true" \
  -H "jsonpaths:[\"$.order_id\",\"$.user_id\",\"$.amount\",\"$.dt\"]" \
  -H "columns: order_id,user_id,amount,dt" \
  -H "max_filter_ratio:0.01" \
  -T /data/order_20241009.json \
  -XPUT http://fe:8030/api/dwd/orders/_stream_load

# ③ 查看导入记录（Broker Load 与 Stream Load 的记录都在 SHOW LOAD 里）
#    注意：SHOW LOAD 才是查导入记录的命令，按 label 过滤最方便
SHOW LOAD WHERE LABEL = 'dwd_order_20241009_0002';
SHOW LOAD ORDER BY CreateTime DESC LIMIT 10;
```

> [!note] 关于"SHOW STREAM LOAD"
> 有些资料会提到 `SHOW STREAM LOAD`。**在 Doris 里查导入作业记录的标准命令是 `SHOW LOAD`**——`SHOW LOAD` 会同时列出 Broker Load 与 Stream Load 的记录，用 `WHERE LABEL = '...'` 精确定位最可靠。
> 如果你的版本确实提供了 `SHOW STREAM LOAD` 之类的语法，它做的事也是"按 label 查这次导入"，**不要**把它当成一个独立的作业系统。

### 2.7 Java HttpClient 示例

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;

public class DorisStreamLoad {

    /**
     * 关键点：
     * 1) label 必须由调用方确定性生成（可重放、全局唯一），绝不能每次 new 一个 UUID
     * 2) 重试时必须复用同一个 label —— Doris 端会判重，这才是"不重"的保证
     * 3) 超时不等于失败：先查 SHOW LOAD WHERE LABEL='...' 再决定是否重试
     */
    public static String streamLoad(String feHost, String db, String table,
                                    String user, String password,
                                    String label, byte[] payload) throws Exception {

        String url = String.format("http://%s:8030/api/%s/%s/_stream_load", feHost, db, table);
        String auth = Base64.getEncoder()
                .encodeToString((user + ":" + password).getBytes(StandardCharsets.UTF_8));

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofMinutes(10))
                .header("Authorization", "Basic " + auth)
                .header("label", label)                     // 幂等键
                .header("column_separator", ",")
                .header("format", "csv")
                .header("strict_mode", "true")
                .header("max_filter_ratio", "0")            // 不放过任何脏数据
                .header("timeout", "600")
                .PUT(HttpRequest.BodyPublishers.ofByteArray(payload))
                .build();

        HttpResponse<String> response = HttpClient.newHttpClient()
                .send(request, HttpResponse.BodyHandlers.ofString());

        // 解析响应：Status 为 Success 或 Label Already Exists 都算"数据已在"
        String body = response.body();
        if (body.contains("\"Status\":\"Success\"")
                || body.contains("Label Already Exists")) {
            return body;
        }
        throw new IllegalStateException("stream load failed: " + body);
    }
}
```

> [!tip] 生产代码里还应该做的事
> - **对 `NumberFilteredRows > 0` 报警**：静默丢数据的唯一信号；
> - 把 `LoadTimeMs`、`CommitAndPublishTimeMs` 打进监控；
> - 重试要有**指数退避**，避免把一个繁忙的 BE 打死；
> - 失败时抓取 `ErrorURL` 存档，便于追查脏数据。

---

## 三、Routine Load

**定位**：Kafka → Doris 的**官方直连方案**。不需要 Flink，Doris FE 自己起消费任务，按批次攒批后走 Stream Load 内部导入。

### 3.1 完整语法

```sql
CREATE ROUTINE LOAD dwd.rl_order ON orders
COLUMNS(order_id, user_id, amount, dt, tmp_col)       -- 列映射（可含临时列）
WHERE amount > 0                                       -- 导入前过滤
PROPERTIES (
  "desired_concurrent_number" = "3",                   -- 期望消费并发（≈ Kafka 分区数）
  "max_batch_interval"        = "20",                  -- 攒批最大时间（秒）
  "max_batch_rows"            = "300000",              -- 攒批最大行数
  "max_batch_size"            = "209715200",           -- 攒批最大字节数（约 200MB）
  "max_error_number"          = "1000",                -- 允许的错误行数
  "strict_mode"               = "true",
  "timezone"                  = "Asia/Shanghai",
  "format"                    = "json",
  "strip_outer_array"         = "true",
  "jsonpaths"                 = "[\"$.order_id\",\"$.user_id\",\"$.amount\",\"$.dt\"]",
  "partial_columns"           = "false"
)
FROM KAFKA
(
  "kafka_broker_list"       = "kafka1:9092,kafka2:9092",
  "kafka_topic"             = "order_topic",
  "property.group.id"       = "doris_rl_order_group",
  "property.kafka_default_offsets" = "OFFSET_BEGINNING"   -- 首次消费从哪开始
);
```

**攒批三兄弟的关系**：`max_batch_interval`、`max_batch_rows`、`max_batch_size` **任意一个满足就触发一次导入**。

| 参数 | 调大 | 调小 |
|---|---|---|
| `max_batch_interval` | 批次更大、导入次数更少、**延迟变高** | 延迟低、**导入更频繁 → 小版本/compaction 压力大** |
| `max_batch_rows` / `max_batch_size` | 单次导入数据量大，吞吐高，但对内存/超时更敏感 | 更平滑，但导入次数多 |
| `desired_concurrent_number` | 并发消费更高，受 **Kafka 分区数**上限约束 | 并发不足，消费滞后 |

> [!warning] `desired_concurrent_number` 超过 Kafka 分区数是无效的
> Kafka 的消费并发上限 = 分区数。设 `desired_concurrent_number = 10` 但 topic 只有 3 个分区 → **实际并发只有 3**。
> 想提高 Routine Load 吞吐，**先去扩 Kafka 分区**，光调 Doris 参数没用。

### 3.2 管理命令

```sql
-- 查看运行中的任务（含状态、进度、错误）
SHOW ROUTINE LOAD FOR dwd.rl_order;
SHOW ROUTINE LOAD;                              -- 当前 db 下的所有任务

-- 暂停 / 恢复 / 停止
PAUSE  ROUTINE LOAD FOR dwd.rl_order;
RESUME ROUTINE LOAD FOR dwd.rl_order;
STOP   ROUTINE LOAD FOR dwd.rl_order;           -- 停止后不可恢复，需要重建

-- 修改参数（部分属性支持 ALTER）
ALTER ROUTINE LOAD FOR dwd.rl_order
PROPERTIES ("max_batch_interval" = "10");

-- 查看被暂停任务的错误原因
SHOW ROUTINE LOAD FOR dwd.rl_order\G
-- 关注：State（RUNNING/PAUSED/STOPPED/NEED_SCHEDULE）、
--       Statistic（总消费行数/已导入行数/错误行数）、
--       ErrorLogUrls、OtherMsg / ReasonOfStateChanged
```

`SHOW ROUTINE LOAD` 里最该看的几列：

| 列 | 含义 | 异常判读 |
|---|---|---|
| `State` | 任务状态 | `PAUSED` 一定是出了问题，看 `ReasonOfStateChanged` |
| `Statistic` | `receivedBytes` / `loadedRows` / `errorRows` | **errorRows 持续增长 = 数据质量问题** |
| `Progress` | 各分区的消费位点与 lag | **lag 持续增长 = 消费跟不上生产** |
| `ErrorLogUrls` | 错误数据的下载地址 | 直接下载看脏数据长什么样 |
| `ReasonOfStateChanged` | 状态变化原因 | **PAUSED 的第一手线索** |

### 3.3 Routine Load 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| **任务变成 `PAUSED`** | ① 错误行数超过 `max_error_number`；② 所有批次都被 `max_filter_ratio` 过滤掉；③ Kafka 连不上/认证失败；④ 表结构变更导致列不匹配 | 看 `ReasonOfStateChanged` 与 `ErrorLogUrls`；修正数据/表结构后 `RESUME` |
| **消费滞后（lag 一直涨）** | Kafka 分区数不足 / `desired_concurrent_number` 太小 / 单批太大导致每次导入耗时长 / BE 写入慢 | 扩 Kafka 分区 → 调并发 → 调小批次提高频率 → 查 BE 是否 compaction 压力大 |
| **`max_filter_ratio` 过滤掉整批** | 脏数据比例超过阈值，Doris 判定"整批不可信"→ **任务暂停而不是丢数据**（这是保护机制） | 这是**好事**：去修数据。**不要**为了让它跑起来就把 filter ratio 调到 1.0 —— 那会静默丢数据 |
| **`errorRows` 缓慢增长但任务正常** | 少量脏数据在 `max_error_number` 容忍范围内 | 下载 `ErrorLogUrls` 修数据源；同时**给 errorRows 加监控告警** |
| **删表重建后任务没了** | Routine Load 是表级任务 | 重新 `CREATE ROUTINE LOAD` |
| **重复消费** | 通常是因为 Routine Load 的重试机制 + **Duplicate 模型**（Duplicate 表没有主键，重放就会重复） | **CDC/Kafka 入仓应该用 Unique 模型**（§5.2） |

> [!important] Routine Load 的"不重"能力从哪来
> Routine Load 内部**自动管理事务**：每个批次一个事务，成功后提交；失败重试时**复用该批次的事务**，所以对 **Unique/Aggregate 模型**是幂等的。
> 但对 **Duplicate 模型**，"重试"就等于"再插一遍"——**因为 Duplicate 模型的设计目标就是保留所有行**。
> 这就是"CDC / Kafka 入仓必须用 Unique 模型"的另一个理由。

---

## 四、Flink Doris Connector（重点）

### 4.1 依赖坐标与版本对应

**坐标规律**：`org.apache.doris:flink-doris-connector-<flink版本>:<connector版本>`

```xml
<!-- 坐标中的 1.17 / 1.18 / 1.19 / 1.20 指的是 Flink 版本，不是 Doris 版本 -->
<dependency>
  <groupId>org.apache.doris</groupId>
  <artifactId>flink-doris-connector-1.17</artifactId>
  <version>${flink-doris-connector.version}</version>
</dependency>
```

| 关注点 | 说明 |
|---|---|
| **后缀跟 Flink 版本走** | 用 Flink 1.17 就必须选 `flink-doris-connector-1.17`，选错直接 `NoSuchMethodError` / `ClassNotFoundException` |
| **Connector 版本跟能力走** | 连接器自身有小版本演进（2PC、部分列更新、删除传递、schema change 等能力是逐版本加进来的） |
| **Doris 3.x / 4.x 上新坐标** | Doris 3.x 起，随着 Flink 与 Doris 双方版本演进，**连接器有新的版本线与坐标形式**（例如面向更新 Flink 大版本、以及面向 Doris 3.x/4.x 新能力的分支） |
| **⚠️ 不要凭记忆写版本号** | 接入前**必须核对官方兼容矩阵**：Doris 版本 × Flink 版本 × Connector 版本是三方约束 |
| **打包注意** | Flink 集群上跑要打成 shaded jar 或用 `flink run -C` 附上依赖，避免与 Flink 自带包冲突 |

> [!danger] 版本不匹配的三种典型报错
> - `java.lang.NoSuchMethodError: org.apache.doris.flink.cfg.DorisExecutionOptions.builder()` → connector 与代码 API 不匹配；
> - `ClassNotFoundException: org.apache.doris.flink.sink.DorisSink` → 依赖没打进去 / scope 写成了 provided 但集群上没有；
> - 运行时 `ScopedFileSystem` / `No FileSystem for scheme` → 与 Flink 的 hadoop 依赖冲突。
>
> **统一原则**：先在本地用 `mvn dependency:tree` 确认 connector 版本唯一，再上集群。

### 4.2 四大配置对象

| 类 | 作用 | 关键方法（示意，方法名随 connector 版本略有差异） |
|---|---|---|
| **`DorisOptions`** | **连哪里、写哪张表、用什么账号** | `setFenodes(host:8030)`、`setTableIdentifier(db.tbl)`、`setUsername()`、`setPassword()` |
| **`DorisExecutionOptions`** | **怎么写**：label、攒批、删除、2PC、Stream Load 参数 | `setLabelPrefix()`、`setStreamLoadProp()`、`setDeletable()`、`setEnableDelete()`、`setEnable2PC()`、`setBufferFlushMaxRows()`、`setBufferFlushMaxBytes()`、`setBufferFlushIntervalMs()`、`setMaxRetries()` |
| **`DorisReadOptions`** | **怎么读**（Doris Source / 维表 join 场景） | `setReadFields()`、`setTabletSize()`、`setBeNodeSize()` 等 |
| **`DorisSink` / `DorisSource`** | 把上面三者组装成 Flink 的 Sink/Source | `DorisSink.builder()` + `setSerializer(...)` |

**`DorisOptions`**

```java
DorisOptions dorisOptions = DorisOptions.builder()
        .setFenodes("fe1:8030,fe2:8030")     // FE 的 HTTP 端口，不是 9030
        .setTableIdentifier("dwd.orders")     // db.table
        .setUsername("root")
        .setPassword("")
        .build();
```

> [!warning] `fenodes` 是 **HTTP 端口（8030）**，不是 MySQL 协议端口（9030）
> 写错端口是最常见的"连不上"原因。Source 读取时另外还需要 BE 的地址，connector 会自己从 FE 获取。

**`DorisExecutionOptions` + Stream Load 参数**

```java
Properties streamLoadProp = new Properties();
streamLoadProp.setProperty("format", "json");
streamLoadProp.setProperty("read_json_by_line", "true");   // 一行一条 JSON
streamLoadProp.setProperty("strict_mode", "true");
streamLoadProp.setProperty("max_filter_ratio", "0");       // 生产别乱放大
streamLoadProp.setProperty("timezone", "Asia/Shanghai");
// streamLoadProp.setProperty("partial_columns", "true");  // 部分列更新时开

DorisExecutionOptions execOptions = DorisExecutionOptions.builder()
        .setLabelPrefix("mysql-cdc-orders")   // ⚠️ 全局唯一且稳定，见 §4.4
        .setStreamLoadProp(streamLoadProp)
        .setDeletable(false)                  // 旧接口：sink 是否可删除
        .setEnableDelete(true)                // 新接口：把 CDC 删除事件传给 Doris
        .setEnable2PC(true)                   // 开启两阶段提交（§4.3）
        .setBufferFlushMaxRows(50000)         // 攒到多少行 flush
        .setBufferFlushMaxBytes(64L * 1024 * 1024)
        .setBufferFlushIntervalMs(10_000)     // 或多久 flush 一次
        .setMaxRetries(3)                     // 失败重试次数
        .build();
```

### 4.3 `DeliveryGuarantee` 与两阶段提交的配合

| 档位 | 怎么实现 | 故障恢复后的表现 | 需要 Doris 表是什么模型 |
|---|---|---|---|
| **`AT_LEAST_ONCE`**（默认） | 攒批 → Stream Load，靠 **label 幂等**去重 | 可能重放，但同 label 被 Doris 判重 → **最终不重** | **Unique / Aggregate**（Duplicate 会重复！） |
| **`EXACTLY_ONCE`** | 攒批 → **preCommit（2PC）** → checkpoint 完成后 **commit** | checkpoint 失败则 abort，**数据从未可见** → 严格一次 | Unique / Aggregate + 支持事务 |

```
AT_LEAST_ONCE（label 幂等）:
  批次 ──► Stream Load(label=L) ──► 成功
  失败重放 ──► Stream Load(label=L) ──► "Label Already Exists" ──► 视为成功 ──► 不重 ✅

EXACTLY_ONCE（2PC）:
  批次 ──► preCommit(label=L, txn=T)  [数据未可见]
            │
     checkpoint 成功 ──► commit(txn=T)   ──► 数据可见 ✅
     checkpoint 失败 ──► (txn 超时自动 abort) ──► 数据不存在 ✅
```

> [!important] 该选哪个？这是一个权衡
> - **开 2PC 的收益**：数据可见性与 checkpoint 严格对齐，不会出现"checkpoint 回滚了但数据已经进 Doris"的中间态。
> - **开 2PC 的代价**：
>   ① 事务从 preCommit 到 commit 之间**必须活着**，所以 **checkpoint 间隔不能超过 Doris 侧的事务超时**，否则 commit 失败、作业报错；
>   ② 事务期间占用 Doris 的资源与版本；
>   ③ 链路复杂度上升，出问题时排查面更大。
>
> **实践结论**：因为 **Doris 的 Unique 模型 + label 幂等本身就能保证"不重"**，所以**很多场景用 `AT_LEAST_ONCE` + 正确的 label + Unique 表就够了**，不必上 2PC。
> 当**链路上有非幂等的下游**、或者**要求数据可见性与 checkpoint 严格一致**时，才开 2PC。
> （更完整的取舍推导见 [[5-bigdata/0-flink/11-端到端一致性|Flink 11-端到端一致性]]）

### 4.4 `labelPrefix` + checkpoint 如何保证不重不丢

> [!important] 核心机制：label 是 Doris 端的幂等键，checkpoint 是 Flink 端的重放边界
> **两者的组合 = 端到端的"不重"**：Flink 保证"失败后从 checkpoint 重放"，Doris 保证"同一批数据即使重放也只生效一次"。

**具体是怎么拼出来的**：

| 环节 | 谁负责 | 做什么 |
|---|---|---|
| **① 批次编号确定性** | Flink Connector | 每批数据的 label 由 **`labelPrefix` + 作业内确定的批次/checkpoint 序号**拼成。**同一个 checkpoint 周期重启后，重放的批次会算出相同的 label** |
| **② Doris 端判重** | Doris FE | 收到 label → 发现已存在且成功 → 返回 `Label Already Exists` → 数据不重复写 |
| **③ Connector 的容错处理** | Flink Connector | 把 `Label Already Exists` **当作成功**处理（因为它意味着这批数据已经在了） |
| **④ "不丢"** | Flink Checkpoint | checkpoint 记录了 Kafka 位点；失败从 checkpoint 恢复 → 从正确位点重放 → 数据不会跳过 |

**"不丢"的真正依赖链**：

```
不丢 = ① source 位点被 checkpoint 正确记录（Flink / Kafka offset）
     + ② sink 在 checkpoint 成功前不丢数据（要么 2PC 未 commit，要么已写入且幂等可重放）
     + ③ 重放的数据能被下游吸收（label 幂等 / 主键 upsert）
```

> [!danger] 让"不重不丢"彻底失效的四个操作
> 1. **`labelPrefix` 每次部署都改**（比如加了 git commit id / 时间戳）→ 幂等链条断裂 → **重复数据**。
> 2. **`labelPrefix` 多个作业共用** → 作业 A 的批次和作业 B 的批次撞 label → 一个作业的数据被**静默拒绝** → **丢数据**（比重复更可怕）。
> 3. **Doris 侧表用 Duplicate 模型** → 没有主键覆盖语义，重放就是重复插入 → **重复数据**。
> 4. **Doris 表的主键列与 Flink 写入的 key 不一致** → 覆盖语义作用在错误的行上 → **数据错乱**。
>
> **自检清单**：`labelPrefix` 全局唯一且从不改动 ✅；Doris 表是 Unique + MoW ✅；表的主键列 == 业务主键 ✅；`max_filter_ratio` 没有设成 1.0 ✅。

### 4.5 攒批参数（吞吐与延迟的旋钮）

| 参数 | 含义 | 调大的影响 | 调小的影响 |
|---|---|---|---|
| `sink.buffer-flush.max-rows` | 攒够多少行就 flush | 吞吐高、Stream Load 次数少 | 延迟低、导入次数多 → **小版本/compaction 压力大** |
| `sink.buffer-flush.max-bytes` | 攒够多少字节就 flush | 单批更大 | 同上 |
| `sink.buffer-flush.interval` | 多久强制 flush 一次（兜底延迟） | **延迟变高**（数据在 buffer 里等） | 延迟低，但可能攒不出批 → 空转 |
| `sink.max-retries` | 单批失败重试次数 | 更耐抖动 | 更容易因瞬时故障失败 |
| **`checkpoint 间隔`** | 与上面协同 | checkpoint 太长 → 2PC 事务超时风险 | 太短 → 小文件、compaction 压力 |

> [!warning] 攒批与 checkpoint 的耦合（最容易被忽略）
> - **开 2PC 时**：checkpoint 间隔必须 **< Doris 侧事务超时**，否则 preCommit 的事务已经超时了才来 commit → 失败。
> - **高频小批导入**：每次 flush 都是一次 Stream Load、一个事务、一批新版本。**导入频率越高，Compaction 压力越大**，`CommitAndPublishTimeMs` 会越来越大，最终形成恶性循环（见 §7.5 与 [[8-运维与调优]]）。
> **经验取向**：宁可"**攒大一点、flush 少一点**"，也不要"每 1 秒 flush 一次"。**秒级新鲜度通常不是靠缩短 flush 间隔换来的，而是靠链路整体设计。**

### 4.6 Flink SQL 完整示例

```sql
-- ① 源表：MySQL CDC
CREATE TABLE mysql_orders (
  order_id BIGINT,
  user_id  BIGINT,
  amount   DECIMAL(18, 2),
  status   STRING,
  dt       DATE,
  PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
  'connector'      = 'mysql-cdc',
  'hostname'       = 'mysql-host',
  'port'           = '3306',
  'username'       = 'cdc_user',
  'password'       = '******',
  'database-name'  = 'shop',
  'table-name'     = 'orders',
  'scan.startup.mode' = 'initial',          -- initial：先全量快照，再增量
  'server-time-zone'  = 'Asia/Shanghai'
);

-- ② 目标表：Doris（Unique 模型 + MoW）
CREATE TABLE doris_orders (
  order_id BIGINT,
  user_id  BIGINT,
  amount   DECIMAL(18, 2),
  status   STRING,
  dt       DATE,
  PRIMARY KEY (order_id) NOT ENFORCED
) WITH (
  'connector'                    = 'doris',
  'fenodes'                      = 'fe1:8030,fe2:8030',
  'table.identifier'             = 'dwd.orders',
  'username'                     = 'root',
  'password'                     = '',
  'sink.label-prefix'            = 'mysql-cdc-shop-orders',   -- 全局唯一、稳定！
  'sink.properties.format'       = 'json',
  'sink.properties.read_json_by_line' = 'true',
  'sink.properties.strict_mode'  = 'true',
  'sink.properties.max_filter_ratio' = '0',
  'sink.enable-delete'           = 'true',      -- 传递 CDC 删除事件
  'sink.enable-2pc'              = 'true',      -- 与 checkpoint 配合做严格一次
  'sink.buffer-flush.max-rows'   = '50000',
  'sink.buffer-flush.interval'   = '10s',
  'sink.max-retries'             = '3'
);

-- ③ 执行
INSERT INTO doris_orders
SELECT order_id, user_id, amount, status, dt
FROM mysql_orders;
```

**对应的 Doris 侧建表**：

```sql
CREATE TABLE dwd.orders (
  order_id BIGINT       NOT NULL,
  user_id  BIGINT,
  amount   DECIMAL(18,2),
  status   VARCHAR(32),
  dt       DATE
)
UNIQUE KEY(order_id)
DISTRIBUTED BY HASH(order_id) BUCKETS 32
PROPERTIES (
  "replication_num" = "3",
  "enable_unique_key_merge_on_write" = "true"    -- MoW：写入时合并，读取更快
);
```

> [!note] 关于 DDL 层面的容错选项
> 有些容错相关的能力在 Table API 与 DataStream API 上的暴露方式不完全一致（例如 DeliveryGuarantee 在 DataStream 侧是显式设置的语义档位，在 DDL 侧由若干 `sink.*` 选项共同体现）。
> **具体选项名以你所用 connector 版本的官方文档为准**，先 `SHOW` 不出来的东西不要凭记忆写。

### 4.7 DataStream 完整示例

```java
import org.apache.doris.flink.cfg.DorisExecutionOptions;
import org.apache.doris.flink.cfg.DorisOptions;
import org.apache.doris.flink.cfg.DorisReadOptions;
import org.apache.doris.flink.sink.DorisSink;
import org.apache.doris.flink.sink.writer.serializer.SimpleStringSerializer;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import com.ververica.cdc.connectors.mysql.source.MySqlSource;
import com.ververica.cdc.connectors.mysql.table.StartupOptions;
import com.ververica.cdc.debezium.JsonDebeziumDeserializationSchema;

import java.util.Properties;

public class MysqlCdcToDoris {

    public static void main(String[] args) throws Exception {

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // ① 必须开启 checkpoint —— label 幂等和 2PC 都依赖它
        env.enableCheckpointing(60_000);          // 60s 一次 CK
        env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30_000);

        // ② Doris 连接信息
        DorisOptions dorisOptions = DorisOptions.builder()
                .setFenodes("fe1:8030,fe2:8030")
                .setTableIdentifier("dwd.orders")
                .setUsername("root")
                .setPassword("")
                .build();

        // ③ Stream Load 参数
        Properties streamLoadProp = new Properties();
        streamLoadProp.setProperty("format", "json");
        streamLoadProp.setProperty("read_json_by_line", "true");
        streamLoadProp.setProperty("strict_mode", "true");
        streamLoadProp.setProperty("max_filter_ratio", "0");
        streamLoadProp.setProperty("timezone", "Asia/Shanghai");

        // ④ 写入行为
        DorisExecutionOptions execOptions = DorisExecutionOptions.builder()
                .setLabelPrefix("mysql-cdc-shop-orders")   // 幂等键的前缀，稳定且唯一
                .setStreamLoadProp(streamLoadProp)
                .setEnableDelete(true)                     // CDC 删除事件传递到 Doris
                .setEnable2PC(true)                        // 两阶段提交
                .setBufferFlushMaxRows(50_000)
                .setBufferFlushIntervalMs(10_000)
                .setMaxRetries(3)
                .build();

        // ⑤ 组装 Sink（工厂方法名随 connector 版本略有差异，以目标版本为准）
        DorisSink<String> dorisSink = DorisSink.<String>builder()
                .setDorisOptions(dorisOptions)
                .setDorisReadOptions(DorisReadOptions.builder().build())
                .setDorisExecutionOptions(execOptions)
                .setSerializer(new SimpleStringSerializer())
                .build();

        // ⑥ MySQL CDC Source
        MySqlSource<String> mySqlSource = MySqlSource.<String>builder()
                .hostname("mysql-host")
                .port(3306)
                .databaseList("shop")
                .tableList("shop.orders")
                .username("cdc_user")
                .password("******")
                .startupOptions(StartupOptions.initial())      // 先全量再增量
                .deserializer(new JsonDebeziumDeserializationSchema())
                .build();

        env.fromSource(mySqlSource, WatermarkStrategy.noWatermarks(), "mysql-orders")
           .uid("mysql-orders-source")
           .sinkTo(dorisSink)
           .uid("doris-orders-sink");

        env.execute("mysql-cdc-orders-to-doris");
    }
}
```

> [!tip] 生产环境必须补的三件事
> 1. **给每个算子设置 `uid()`**（上面已经加了）——**不设 uid，作业升级时状态无法恢复，等于丢失不重不丢能力**；
> 2. **状态后端与 checkpoint 目录要配好**（HDFS/S3），见 [[5-bigdata/0-flink/5-Checkpoint与Savepoint|Flink 5-Checkpoint与Savepoint]]；
> 3. **Doris 侧的 label 前缀写进配置中心**，不允许代码里随便改。

---

## 五、Flink CDC → Doris 端到端链路

### 5.1 完整链路图

```
MySQL (binlog)
   │  Debezium / Flink CDC
   ▼
Flink CDC Source  ──►  转换/清洗/打宽/去重  ──►  DorisSink
   (initial + 增量)         (Flink SQL / DataStream)      │
                                                    Stream Load (label)
                                                          ▼
                                                    Doris Unique 表 (MoW)
                                                          │
                                                    BI / 大屏 / 点查
```

### 5.2 为什么 CDC 场景必须选 Unique 模型

| CDC 事件的语义 | 对应到 Doris 表模型 |
|---|---|
| **INSERT** 一条新记录 | 任何模型都能插 |
| **UPDATE** 主键不变、字段变化 | **需要"按主键覆盖"** → Unique 模型 |
| **DELETE** 删除某主键 | **需要"能删"** → Unique 模型 + 删除标记（或 `enable_delete`） |
| 一条主键在源库被改了 100 次 | **只关心最新状态** → Unique 模型（同主键覆盖，保留最后版本） |

> [!important] 关键结论
> **CDC 的本质是"同步主键的最新状态"，而 Doris 的 Unique 模型（特别是 Merge-on-Write）就是"按主键 upsert + 最新值可见"。两者语义天然匹配。**
>
> 反面教材：
> - **Duplicate 模型**：没有主键，同一主键的 100 次更新会变成 100 行 → 上游一次 UPDATE 就在 Doris 里多一行，**数据完全是错的**；
> - **Aggregate 模型**：适合做 SUM/MAX 这类聚合，但无法表达"删除"和"整行最新值覆盖"。
>
> **所以：CDC → Doris，表模型选 Unique，没有第二个正确答案。**

**MoW（Merge-on-Write）为什么重要**：

| | Merge-on-Read（旧） | Merge-on-Write（`enable_unique_key_merge_on_write=true`） |
|---|---|---|
| 写入时 | 只记 delta，不合并 | **写入时就合并同主键**，形成完整最新行 |
| 读取时 | **要在线合并多个版本** | 直接读，**无需在线 merge** |
| 点查性能 | 差（要合并） | 好（这是高并发点查的基础，见 [[5-查询优化]]） |
| 写入开销 | 低 | 略高（但换来读性能） |
| 是否支持删除标记 | 支持 | 支持（`__DORIS_DELETE_SIGN__`） |

### 5.3 删除事件的传递

CDC 的 DELETE 事件怎么变成 Doris 的删除？**通过一行带删除标记的记录。**

**机制**：Doris 的 Unique 表有一个隐藏列 **`__DORIS_DELETE_SIGN__`**。写入一条主键相同、且该列为 `1` 的记录，就表示"删除这个主键"。

```
Flink CDC 收到 DELETE (order_id = 100) 
        │
        ▼
connector 生成一条记录：{ order_id: 100, __DORIS_DELETE_SIGN__: 1 }
        │
        ▼
Stream Load 写入 Doris → Unique 表按 order_id 覆盖 → 该行被标记删除
```

**Flink 侧的开关**：

| 配置 | 含义 | 注意 |
|---|---|---|
| `sink.enable-delete = 'true'` / `setEnableDelete(true)` | **把 CDC 的删除事件传递给 Doris** | 需要 Doris 表是 **Unique 模型** |
| `setDeletable(true)` | sink 层面允许删除语义（旧接口） | **不同 connector 版本语义略有差异**，以目标版本文档为准 |
| `merge_type: DELETE`（Stream Load header） | 手动指定本次导入是删除 | 自研链路可用 |

> [!warning] 删除相关的两个坑
> 1. **表不是 Unique 模型**：删除标记无处生效，删除事件被忽略 → **源库删了、Doris 还在**。
> 2. **`enable_unique_key_merge_on_write` 与删除标记的配合**：MoW 下删除标记会被正确处理并参与合并；但在非常老的版本/非 MoW 路径下行为不同。**升级或换模型时一定要验证删除语义**——这类问题往往几个月后才被业务发现。

### 5.4 全量与增量切换时的写入压力

Flink CDC 的 `scan.startup.mode = 'initial'` 会**先做全量快照，再切到 binlog 增量**。这个切换点是**整条链路最危险的时刻**：

| 问题 | 原因 | 缓解 |
|---|---|---|
| **写入压力尖峰** | 全量阶段一次性读几千万/上亿行，全部灌向 Doris | **限速**：调小 `sink.buffer-flush.max-rows`、限制 source 并行度、必要时限流 |
| **Doris Compaction 被打爆** | 海量数据在短时间内产生大量版本 | 在全量阶段**临时调大 flush 批次、减少导入次数**，或**错峰**（业务低峰期发起） |
| **全量阶段的变更丢失** | 全量读的过程中源库还在改 | **Flink CDC 的增量快照算法**保证了这一点（全量期间变更会被记录并在切换时补齐）——**不要自己实现"全量 + 增量"两段式**，除非你很清楚自己在做什么 |
| **切换后延迟突增** | binlog 位点回追 | 监控 source 的 lag，留足资源 |
| **全量期间 Doris 查询变慢** | 导入与查询争抢 BE 资源 | 用 **Workload Group** 隔离导入与查询（见 [[5-查询优化]]） |

> [!tip] 全量阶段的正确姿势
> - **优先在业务低峰做首次全量**；
> - **全量阶段把攒批调大**（例如 `max-rows` 提到几十万）以减少导入次数 —— 目的不是"快"，而是**减少事务数和版本数**，避免 compaction 雪崩；
> - **监控 `CommitAndPublishTimeMs`**，它是 Doris 侧压力的最早信号；
> - 给 Doris 留足 compaction 资源（见 [[8-运维与调优]]）。

---

## 六、导入的一致性与幂等

### 6.1 三层机制总结

| 层次 | 机制 | 保证什么 | 依赖什么 |
|---|---|---|---|
| **① Doris 内部** | 每个导入是**一个事务**；Stream Load 一次请求内完成"写 + 提交 + 发布" | **单次导入的原子性**：要么全部可见，要么全不可见 | Doris 的事务与版本机制 |
| **② 跨次导入** | **`label` 幂等** | **同一批数据重复提交只生效一次** | label 全局唯一 + 客户端重试时复用 label |
| **③ 与外部系统对齐** | **两阶段提交（2PC）** | **Doris 的数据可见性与外部 checkpoint 严格对齐** | Doris 事务 + Flink checkpoint |

> [!important] 这三层要分开理解和表述
> 面试里如果只说"用 2PC 保证不丢不重"是不完整的：
> - **"不重"的底座是 label 幂等**（即使没有 2PC 也能做到，前提是表是 Unique）；
> - **2PC 解决的是"可见性时机与 checkpoint 对齐"**，它是更严格的一档，不是唯一手段；
> - **"不丢"靠的是 Flink 的 checkpoint 位点管理 + 导入失败的重试**，Doris 侧只负责"你重放了我能正确吸收"。

### 6.2 `label` 机制回顾（关键三条）

1. **label 必须全局唯一**（同一集群范围内）。
2. **重试必须复用同一 label**，这是幂等的充要条件。
3. **不同数据绝不能复用同一 label** —— 会被静默拒绝，是**丢数据**而不是重复。

### 6.3 `max_filter_ratio` 与 `strict_mode`（危险区）

**`max_filter_ratio`**：允许被过滤掉的行占总行数的比例上限。

| 取值 | 含义 | 后果 |
|---|---|---|
| `0` | **不允许任何被过滤的行** | 一行脏数据就导致**整个导入失败** | 数据质量要求极高的场景：仓位、账户 |
| `0.01` ~ `0.1` | 容忍少量脏数据 | 导入成功率提升，但**脏数据被静默丢掉** | 需要配合"对过滤行数报警" |
| `1.0` | **允许 100% 被过滤** | ⚠️ **全部数据被过滤掉也算导入成功** —— 你得到一条"成功"的记录和一张空表 | **永远不要这样设** |

> [!danger] `max_filter_ratio` 设大了就是静默丢数据
> 最危险的场景：上游改了字段格式/编码，导致**所有行**都被判定为脏数据。
> `max_filter_ratio = 1.0` 时，Doris 认为"过滤率 100% ≤ 100%"，**导入状态是 Success**，`NumberLoadedRows = 0`。
> 你的监控只看"导入成功/失败"，于是**业务表从此不再更新，而你以为一切正常**。
>
> **唯一的防线**：把 `NumberFilteredRows` 作为指标上报，并和 `NumberTotalRows` 一起做比例告警。
> **成功 ≠ 数据进去了。** 这个认知是运维 Doris 导入链路的核心。

**`strict_mode`**：对列类型转换失败、精度丢失等情况的处理方式。

| `strict_mode` | 行为 | 适用 |
|---|---|---|
| `false`（默认） | 转换失败的行**按 `max_filter_ratio` 过滤**，能转的照常导入 | 兼容性优先、脏数据多但可容忍 |
| `true` | **转换失败直接判定为错误**，不静默丢弃 | 数据质量优先；**建议生产开启** |

> [!tip] 推荐的组合
> ```
> strict_mode = true
> max_filter_ratio = 0        （数据质量要求高）
> 或 max_filter_ratio = 0.01  （有少量已知脏数据，同时开过滤行数告警）
> ```
> **无论选哪个，`NumberFilteredRows` 都必须有监控。**

### 6.4 导入失败的排查路径

按这个顺序走，效率最高：

```
① 拿到 label  ──► SHOW LOAD WHERE LABEL = '<label>';      -- 看 State / ErrorMsg
② 看错误 URL  ──► 从响应或 SHOW LOAD 里拿 ErrorURL，curl 下来看具体脏数据
③ 看 BE 日志  ──► be.INFO / be.WARNING，按 label 或 txn_id 搜
④ 分阶段耗时  ──► 响应里的 *TimeMs 字段定位瓶颈段（§2.4）
⑤ 看版本压力  ──► SHOW TABLET / 版本数，确认是不是 compaction 问题（[[8-运维与调优]]）
⑥ 看状态一致  ──► 同 label 的 ExistingJobStatus 是 FINISHED 还是 CANCELLED，决定能不能重试
```

| 命令 | 用途 |
|---|---|
| `SHOW LOAD WHERE LABEL = 'xxx';` | 查导入作业的最终状态与错误信息 |
| `SHOW LOAD ORDER BY CreateTime DESC LIMIT 20;` | 看最近的导入记录 |
| `SHOW ROUTINE LOAD FOR <db.job>;` | 查常驻任务状态、进度、错误日志地址 |
| `SHOW PROC '/current_queries';` | 导入/查询正在占用什么资源 |
| `SHOW TABLET FROM <tbl>;` | 看分片的版本数、数据量（判断小版本堆积） |
| `SHOW TRANSACTION WHERE LABEL = 'xxx';` | 查事务状态（排查 2PC 问题时很有用） |

---

## 七、导入性能调优

### 7.1 先分清瓶颈在哪一段

用响应里的分阶段耗时（§2.4）判断：

| 大头耗时 | 瓶颈 | 优化方向 |
|---|---|---|
| `ReadDataTimeMs` | 客户端上传慢 / 源读取慢 | 客户端并发上传、源侧限速、压缩传输 |
| **`WriteDataTimeMs`** | **BE 写入：排序、建索引、写磁盘** | 攒大批次、减少索引数量、提升 BE 磁盘性能、增加 BE |
| **`CommitAndPublishTimeMs`** | **版本发布：compaction 追不上、版本堆积** | **减少导入频率（攒大批）**、调 compaction 参数（[[8-运维与调优]]） |
| `StreamLoadPutTimeMs` | FE 繁忙 | 减轻 FE 压力、减少元数据操作 |

> [!important] 90% 的"导入慢"其实是"导入太频繁"
> 高频小批导入（每秒/每几秒一次）会产生**大量小版本**，导致：
> ① `CommitAndPublishTimeMs` 逐渐变大；
> ② Compaction 持续追赶，CPU/IO 被吃掉；
> ③ 查询也因为要合并过多版本而变慢。
> **优化顺序应该是：先把批次攒大，再考虑加机器。** 反过来做通常是白花钱。

### 7.2 攒批：导入调优的第一旋钮

| 维度 | 太小 | 太大 | 建议取向 |
|---|---|---|---|
| 批次行数 | 导入次数多、版本多 | 内存/超时风险、失败重传代价大 | 找到"能持续跟上上游速率"的最小导入频率，再据此定批次大小 |
| 批次间隔 | 延迟低但版本多 | 延迟高 | 按业务可接受的新鲜度定，**不要为了"实时"设成 1 秒** |
| 单次请求字节 | 效率低 | 超过 BE 限制直接失败 | 注意 **`streaming_load_max_mb`**（BE 侧对单次 Stream Load 数据量的限制），超了要调大或拆批 |

```sql
-- 查看 BE 侧导入相关配置（调参前先确认实际值）
ADMIN SHOW CONFIG LIKE 'streaming_load_max_mb';
ADMIN SHOW CONFIG LIKE 'streaming_load_rpc_max_alive_time_sec';
```

### 7.3 并发度

| 方式 | 并发旋钮 | 上限约束 |
|---|---|---|
| Stream Load（自研） | 客户端并发请求数 | **单表导入并发**：同一张表的并发导入会争抢版本与 compaction，**并发不是越高越好** |
| Routine Load | `desired_concurrent_number` | **Kafka 分区数** |
| Flink Sink | Flink 作业并行度 + 攒批大小 | Doris 单表导入能力与 BE 数量 |
| Broker Load | `desired_concurrent_number` | BE 数量 |

> [!warning] "单表导入并发"是隐形天花板
> 对**同一张表**高并发导入，每个导入都会产生新版本，Doris 需要在版本链上做合并。
> **表级并发导入的能力是有上限的**（受版本数、compaction 能力约束）。
> 加客户端并发到某个点之后，吞吐**不会上升，`CommitAndPublishTimeMs` 反而会飙升**。
> 这时候正确的动作是：**减少并发、加大批次**。

### 7.4 导入与 Compaction 的关系（重点）

```
导入 ──► 产生新版本 ──► 表上的版本数增加
                            │
                            ▼
                    Compaction 负责合并小版本
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
   Compaction 跟得上                      Compaction 跟不上
        │                                       │
   版本数稳定，查询快                    版本数堆积 → 查询要合并更多版本 → 变慢
                                                → CommitAndPublish 变慢 → 导入变慢
                                                → 更多导入堆积（恶性循环）
```

**这是一条正反馈的恶化链路**，也是"导入高峰期集群整体变慢"的最常见根因：

| 阶段 | 现象 |
|---|---|
| ① | 上游流量上升 / 有人缩短了 flush 间隔 → 导入频率变高 |
| ② | 小版本快速增多，`max_tablet_version_num` 逼近上限 |
| ③ | Compaction 线程 / IO / CPU 被占满，追不上新版本 |
| ④ | 查询要合并更多版本 → 查询变慢 → 更多人重试查询 → 负载上升 |
| ⑤ | `CommitAndPublishTimeMs` 上升 → 导入超时 → 上游重试 → **导入频率更高** |
| ⑥ | 集群整体雪崩 |

**治理方向（顺序很重要）**：

1. **降频**：把导入批次攒大（治本，立刻缓解版本增长）；
2. **限流**：给导入链路加 Workload Group 或上游限速；
3. **调 compaction**：查看并调整 compaction 相关配置（[[8-运维与调优]]）；
4. **扩容量**：加 BE 分担 compaction 压力；
5. **治表设计**：分桶数是否合理（分桶过多 → 每个 tablet 都要 compaction，压力被放大）。

### 7.5 "小文件 / 小版本"问题与治理

| 现象 | 检查方法 | 治理 |
|---|---|---|
| 表上版本数很多 | `SHOW TABLET FROM tbl` 看版本数 / `max_tablet_version_num` 相关配置 | 降导入频率、调 compaction |
| 查询变慢但数据量没变 | PROFILE 里看 Scan 打开的 segment 数 | 同上；必要时手动触发 compaction |
| 导入 `CommitAndPublishTimeMs` 越来越高 | 分阶段耗时趋势图 | 降频 + 扩容 |
| 某几个 tablet 特别大 | `SHOW TABLET FROM tbl` 看数据量分布 | 检查分桶键是否倾斜（见 [[5-查询优化]] 的倾斜治理） |

---

## 八、常见问题排查表

| 现象 | 可能原因 | 排查动作 | 处理 |
|---|---|---|---|
| **`label already exists`** | 同 label 重复提交 | `SHOW LOAD WHERE LABEL='...'` 看前一次的 `State` | **`FINISHED` → 就当成功**（幂等生效）；`CANCELLED` → 换新 label 重试 |
| **`-235` / `-238` 这类负数错误码** | 通常是 **Doris 内部的事务/状态类错误**（事务已提交、事务不存在、提交超时等语义），多见于**两阶段提交**或**同 label 并发提交**的路径 | 看 `SHOW LOAD` 的 `ErrorMsg`、`SHOW TRANSACTION WHERE LABEL='...'`、BE 日志 | **不要猜**：先拿到 `ErrorMsg` 原文判断是"重复提交"还是"事务生命周期超时"，再决定是重试、改 label 策略还是调 checkpoint 间隔 |
| **`Status = Publish Timeout`** | 事务已提交但版本还没可见 | 用**同一个 label** 重试 | 重试是安全的（幂等）；持续出现要看 compaction/版本压力 |
| **导入失败、`NumberFilteredRows` 很大** | 数据格式/类型与表不匹配、`strict_mode` 严格、编码问题 | 下载 `ErrorURL` 看具体行 | 修数据源；或明确评估后放宽 `strict_mode`（**同时加过滤行数告警**） |
| **导入频繁失败、无明显规律** | BE 磁盘/IO 抖动、compaction 抢占、`exec_mem_limit` 不够、`timeout` 太短 | 看分阶段耗时、BE 日志、集群负载 | 调大 `timeout` / `exec_mem_limit`；错峰；加资源隔离 |
| **Routine Load `PAUSED`** | 错误行数超限 / 全部被过滤 / Kafka 连不上 / 表结构变更 | `SHOW ROUTINE LOAD ...\G` 看 `ReasonOfStateChanged`、`ErrorLogUrls` | 修数据或表结构 → `RESUME`；**不要**为了让任务跑起来把过滤阈值调成 1.0 |
| **Routine Load 一直滞后** | 分区数不够 / 并发小 / 单批耗时过长 | 看 `Progress` 的 lag、Kafka 分区数 | 扩分区、调 `desired_concurrent_number`、调小批次提高频率 |
| **Flink sink 写不进去 / 超时** | `fenodes` 端口写错（写成 9030）、网络不通、BE 列表拿不到、`streaming_load_max_mb` 超限、批次太大 | Flink 任务日志里的 Stream Load 响应；`curl` 手动打一次 FE | 先手动 `curl` 验证连通性与权限，再看批次大小 |
| **Flink sink 报 label 冲突** | 多个作业共用同一 `labelPrefix` | 检查所有作业的 `sink.label-prefix` | **立即改成全局唯一**；注意已发生的丢数据需要回补 |
| **数据重复** | ① label 每次重试都变（UUID/时间戳）；② Doris 表是 **Duplicate 模型**；③ `labelPrefix` 被改过 | 查 label 生成逻辑、表模型、作业配置历史 | 改 label 生成策略 → 改成 Unique 模型 → 回补/去重 |
| **数据丢失** | ① `max_filter_ratio` 太大导致整批被过滤；② 不同数据复用了同一 label（被静默拒绝）；③ 删除事件没传递导致"删了还在"（严格说是数据不一致） | **看 `NumberFilteredRows` 与 `NumberLoadedRows`**；查 label 是否复用 | 收紧 `max_filter_ratio`、加过滤行数告警、label 保证唯一 |
| **时间错乱（差 8 小时）** | 时区不一致：源库 / Flink 作业 / Doris 会话 三处时区不同 | 查 `timezone` Stream Load 参数、Flink `server-time-zone`、源库时区 | 三处统一（例如都设 `Asia/Shanghai`）；**不要靠改数据来"修"时区** |
| **导入后查询变慢** | 小版本堆积、compaction 追不上 | `SHOW TABLET FROM tbl` 看版本数 | 降导入频率、调 compaction（[[8-运维与调优]]） |
| **同一批数据部分成功** | 单次导入是原子的，"部分成功"通常是你的批次被拆成了多次导入 | 查 label 数量与每批的 `NumberLoadedRows` | 这是正常行为；用 label 粒度做对账 |
| **权限报错（403 / Access denied）** | 账号没有该表的 LOAD 权限 | `SHOW GRANTS FOR user;` | `GRANT LOAD_PRIV ON db.tbl TO 'user'@'%';` |

> [!tip] 排查的第一步永远是"先确认是哪一类问题"
> **重复 / 丢失 / 慢 / 失败** 是四类完全不同的问题，根因和处理手段完全不同。
> - **重复** → 查 label 生成逻辑 + 表模型；
> - **丢失** → 查 `NumberFilteredRows` + label 是否复用；
> - **慢** → 查分阶段耗时 + 版本压力；
> - **失败** → 查 `SHOW LOAD` + `ErrorURL` + BE 日志。
>
> 先归类，再动手，不要一上来就翻源码。

---

## 九、必答问题

> [!question] 必答：Flink 写 Doris 怎么保证不重不丢？
> 我会把答案拆成 **"不丢"** 和 **"不重"** 两条独立机制来讲，因为它们依赖的东西完全不同：
>
> **【不丢】靠 Flink 的 checkpoint + 失败重试，Doris 只负责"能正确吸收重放"。**
> - Kafka/binlog 的消费位点被 **Checkpoint** 记录，作业失败后从最近一次成功的 checkpoint 恢复，**从正确的位置重放**，不会跳过数据；
> - Sink 侧在 checkpoint 成功前**不释放**已缓冲的数据；导入失败会按 `sink.max-retries` 重试；
> - 注意：**没设 `uid()` 的算子在作业升级时无法恢复状态**，等于自废武功。
>
> **【不重】底座是 Doris 的 `label` 幂等，而不是 2PC。**
> - 每次 Stream Load 都带一个 **label**，它是 Doris 端的**幂等键**；
> - Connector 会把 label 拼成 `labelPrefix + 作业内确定的批次/检查点编号`，所以**同一批数据在重放时会生成相同的 label**；
> - Doris 收到重复 label → 返回 `Label Already Exists` → **Connector 把它当作成功**（因为数据已经在了）→ 不重；
> - **前提条件**：Doris 表必须是 **Unique 模型（推荐 MoW）**。如果表是 Duplicate 模型，重放就是重复插入，label 幂等也没用——因为 Duplicate 表的设计目标就是保留所有行；
> - **前提条件**：`labelPrefix` 必须**全局唯一且从不改动**。改了前缀、或者多个作业共用前缀，幂等链条就断了（共用前缀还会导致被静默拒绝而**丢数据**）。
>
> **【更严格的一档：2PC】**
> 如果要让"数据可见性"与 checkpoint 严格对齐（例如链路上有不可重放的下游），可以开 **`sink.enable-2pc = true`**：
> - checkpoint 期间只做 **preCommit**，数据写入但**不可见**；
> - checkpoint 成功后调 `_stream_load_2pc` 的 **commit**，数据才可见；
> - checkpoint 失败则事务超时 abort，数据从未可见 → 严格的 exactly-once；
> - **代价**：事务从 preCommit 到 commit 之间必须活着，所以 **checkpoint 间隔不能超过 Doris 侧事务超时**，否则 commit 会失败。
>
> **【我的选择】**
> 我们的链路是 MySQL CDC → Flink → Doris，Doris 侧是 **Unique + MoW**：
> - 因为 **label 幂等 + 主键覆盖**已经能保证"不重"，所以**默认用 at-least-once 就够了**，不必为了 exactly-once 把 checkpoint 压得很短；
> - 只有在**业务要求"数据可见性不能先于 checkpoint"**时才开 2PC，并相应把 checkpoint 间隔和 Doris 事务超时对齐；
> - 另外还会做两件兜底：① **把 `NumberFilteredRows` 做监控告警**（防静默丢数据）；② 定时用**对账任务**比对源库与 Doris 的行数/关键指标（**纯技术监控发现不了"数据算错了"**）。

> [!question] 必答：为什么 CDC 场景必须用 Unique 模型？
> 因为 **CDC 的语义是"同步主键的最新状态"**：
> - 源库一条记录 UPDATE 100 次，我只要**最新的一行**；
> - 源库 DELETE 了，Doris 这边也要消失。
>
> | 模型 | 能不能满足 |
> |---|---|
> | **Unique（MoW）** | **能**：按主键 upsert，只保留最新；支持删除标记 `__DORIS_DELETE_SIGN__` |
> | Duplicate | **不能**：没有主键，每次 UPDATE 都变成新的一行，数据直接是错的 |
> | Aggregate | **不能**：能做 SUM/MAX 聚合，但无法表达"整行最新值覆盖"和"删除" |
>
> 顺带一个性能理由：**MoW 在写入时就合并好同主键**，读取时不需要在线 merge —— 这既让 CDC 链路读得快，也是高并发点查的基础（见 [[5-查询优化]]）。

> [!question] 必答：`label` 到底保证什么？用它的时候最容易犯什么错？
> **`label` 是 Doris 端的导入幂等键**：同一个 label 在一次成功导入之后不会产生第二次效果。
> 它是"重试安全"的基础——**只要重试时复用同一个 label，就不会产生重复数据**。
>
> **最容易犯的三个错**：
> 1. **用时间戳/UUID 生成 label** → 每次重试都是新 label → **幂等完全失效，必然重复**；
> 2. **不同数据复用同一 label** → 后一批被 Doris **静默拒绝** → **丢数据**（这比重复更危险，因为你看不到报错）；
> 3. **Flink 作业重新部署时改了 `labelPrefix`** → 同一批数据换了身份证 → **重复导入**。
>
> **正确原则**：label 必须**确定性生成、全局唯一、可重现**——由业务批次标识或 Flink 的 checkpoint/批次编号推导，而不是随机数。

> [!question] 必答：`max_filter_ratio` 设成 1.0 会怎样？
> 会**静默丢数据，而且导入状态是 Success**。
> `max_filter_ratio` 是"允许被过滤掉的行占比的上限"。设成 1.0 意味着**即使 100% 的行都被判定为脏数据、全部过滤掉，Doris 依然认为这次导入是成功的**。
> 于是你会看到：`Status = Success`、`NumberTotalRows = 100万`、**`NumberLoadedRows = 0`**、`NumberFilteredRows = 100万`。
>
> 最典型的事故场景：上游改了字段格式或编码 → 所有行都转换失败 → 表从此不再更新 → **监控显示导入一直成功** → 几周后业务才发现报表数据是旧的。
>
> **防线**：把 **`NumberFilteredRows`** 单独作为指标上报，并对"过滤率"做告警；同时 `strict_mode` 开 `true`、`max_filter_ratio` 设小甚至设 0。**核心认知是：导入成功 ≠ 数据进去了。**

> [!question] 必答：导入变慢了，你会先看什么？
> **先看 Stream Load 响应里的分阶段耗时**，它直接告诉你瓶颈在哪一段：
> - `ReadDataTimeMs` 大 → 客户端上传慢或源读取慢；
> - `WriteDataTimeMs` 大 → BE 写入（排序/建索引/磁盘）是瓶颈；
> - **`CommitAndPublishTimeMs` 大 → 版本发布慢，几乎一定是"导入太频繁 + compaction 追不上"**。
>
> 然后我会确认一件事：**导入频率是不是太高了？** 因为高频小批导入会产生大量小版本，形成"版本堆积 → compaction 追不上 → 查询和导入一起变慢"的正反馈恶化链路。
>
> **处理顺序**（顺序很重要）：① **先把批次攒大、降低导入频率**（立刻缓解，且不花钱）；② 用 Workload Group 隔离导入与查询；③ 再考虑调 compaction 参数；④ 最后才考虑加 BE。
> **反过来做（先加机器）通常只是让雪崩来得晚一点，钱却花了。**

> [!question] 必答：`AT_LEAST_ONCE` 和 `EXACTLY_ONCE` 怎么选？
> 关键认知是：**因为 Doris 有 label 幂等 + Unique 主键覆盖，`AT_LEAST_ONCE` 在"不重"这个目标上已经够用了**——重放的数据会被幂等吸收掉，最终结果和 exactly-once 是一样的（只是过程中可能多写一次）。
>
> | | `AT_LEAST_ONCE` + label 幂等 | `EXACTLY_ONCE`（2PC） |
> |---|---|---|
> | 最终数据正确性 | ✅ 不重（前提：Unique 表 + label 稳定） | ✅ 不重 |
> | 中间状态 | 可能出现"checkpoint 回滚了但数据已可见" | 可见性与 checkpoint 严格对齐 |
> | 约束 | 表必须 Unique；label 必须稳定唯一 | 额外要求 **checkpoint 间隔 < Doris 事务超时** |
> | 复杂度 / 排查面 | 低 | 高 |
>
> **我的选择逻辑**：默认 `AT_LEAST_ONCE`（因为够用且简单）；只有当"数据可见性不能先于 checkpoint"是硬要求时，才开 2PC，并同时把 checkpoint 间隔与 Doris 事务超时对齐。
> **不要为了"看起来更严格"而默认开 2PC** —— 它带来的是一个必须长期维护的时序约束。

---

## 相关笔记

- [[0-Doris总览]] —— 全系列索引与阅读顺序
- [[1-架构与原理]] —— FE/BE 分工、事务与版本机制
- [[2-数据模型]] —— 为什么 CDC 必须用 Unique 模型
- [[3-表设计]] —— 导入场景下的表设计取舍
- [[4-建表与分区分桶]] —— 分区分桶与导入并发的关系
- [[5-查询优化]] —— 导入与查询共享 BE 资源，互相影响
- [[7-湖仓一体]] —— 写湖（Iceberg/Paimon）与写 Doris 的选型
- [[8-运维与调优]] —— Compaction、小版本治理、BE 参数
- [[9-对比StarRocks与ClickHouse]] —— 各引擎导入能力的横向对比
- [[10-面试高频题]] —— 本系列面试题的汇总入口
- [[5-bigdata/0-flink/7-FlinkCDC与实时数仓|Flink 7-FlinkCDC与实时数仓]] —— CDC 原理与增量快照
- [[5-bigdata/0-flink/11-端到端一致性|Flink 11-端到端一致性]] —— 端到端一致性的算法层推导
