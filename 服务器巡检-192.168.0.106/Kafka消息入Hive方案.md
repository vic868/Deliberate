# Kafka 消息入 Hive 方案（192.168.0.106）

> 编写日期：2026-10-06 · 链路：Kafka(bitnami 3.9) → Flink 1.20(k3s) → HDFS staging → Hive 4.0
> 关联：[[部署记录-Hadoop+Hue]] · [[Hive数据加载方案]]（分区注册/对账/幂等规范沿用该文档）
> 示例约定：topic = `user_events`，消息为 JSON：`{"id":1,"name":"vic","event_time":"2026-10-06 20:00:00"}`。换 topic/字段时替换对应名称即可。

---

## 一、链路与角色

```text
生产者 ──► Kafka topic: user_events (9092)
                │  Flink SQL 作业（k3s 里现成的 Flink，经 Dinky 提交）
                │  - 消费 → 按 事件时间 划分 dt/hour → FileSink 滚动写文件
                ▼
        HDFS: /data/staging/user_events/dt=…/hr=…/part-*.json   ← staging（ODS 数据源）
                │  定时脚本（cron）：ADD PARTITION → INSERT OVERWRITE → 对账
                ▼
        Hive: ods.user_events_di（JSON 外表） → dwd.user_events_di（ORC 内表）→ Hue 查询
```

- **为什么用 Flink FileSink 而不是 Hive 直接消费**：解耦。Hive 侧永远只做"文件挂表"，Kafka 的消费位点/重放/断点全交给 Flink 的 checkpoint 管——这正是 [[Hive数据加载方案]] 里"搬运用文件、加工用引擎"原则的流式版
- **延迟定位**：小时级（滚动文件 + 定时挂分区），不是秒级实时。秒级实时分析属于另一条链路（Hue 直查不现实，需 StarRocks/Doris 类 OLAP，暂不展开）

---

## 二、前置检查清单（动手前 5 分钟过一遍）

- [ ] **topic 确认**：`docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list`
- [ ] **消息格式确认**：抽一条看 JSON 字段（决定建表字段）
- [ ] **k3s → Kafka 连通**：Flink Pod 要能用 `192.168.0.106:9092` 连上。bitnami 镜像要确认广播地址含宿主机 IP：
      `docker exec kafka env | grep -i advertise`，若只有容器内网地址，在 `/opt/kafka/docker-compose.yml` 加
      `KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://:9092,PLAINTEXT_HOST://192.168.0.106:9092`（双 listener 配置）
- [ ] **k3s → HDFS 连通**：Flink Pod 访问 `hdfs://192.168.0.106:8020`（**不要写 `hdfs://hadoop:8020`**，`hadoop` 是 docker 网络里的别名，k3s Pod 解析不到——上一条 sockaddr 事故的同款坑）
- [ ] **flink-custom 镜像带 hadoop 依赖**：filesystem connector 写 HDFS 需要 hadoop client；自制镜像时确认打包了 flink-shaded-hadoop，缺了会报 `ClassNotFoundException: org.apache.hadoop...`
- [ ] HDFS 权限已关（当前如此），staging 根目录存在

---

## 三、建库建表（你问的核心）

### 1. 两个库

```sql
CREATE DATABASE IF NOT EXISTS ods;   -- 原始层：外表，JSON 原样保存
CREATE DATABASE IF NOT EXISTS dwd;   -- 明细层：ORC 内表，类型收紧后给分析用
```

命名规范：`ods_<系统>_<表>_di`（di=daily increment，小时级用 `_hi` 也可，分区里已有 hour 字段区分）。

### 2. ODS 外表（对接 staging 的 JSON 文件）

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS ods.user_events_di (
  id          BIGINT,
  name        STRING,
  event_time  STRING          -- 原样 STRING 入 ODS，解析放 DWD（忠实原则）
)
PARTITIONED BY (dt STRING, hr STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.JsonSerDe'
LOCATION '/data/staging/user_events';
```

> 分区列 `dt`/`hr` 必须与 Flink 落盘的目录名 `dt=…/hr=…` 完全一致——ADD PARTITION 就是把目录映射进元数据。

### 3. DWD 内表（ORC，分析用）

```sql
CREATE TABLE IF NOT EXISTS dwd.user_events_di (
  id          BIGINT,
  name        STRING,
  event_time  TIMESTAMP
)
PARTITIONED BY (dt STRING, hr STRING)
STORED AS ORC
LOCATION '/user/hive/warehouse/dwd.db/user_events_di'
TBLPROPERTIES ('orc.compress'='SNAPPY');
```

### 4. HDFS staging 根目录

```bash
hdfs dfs -mkdir -p /data/staging/user_events
```

---

## 四、Flink SQL 作业（经 Dinky 提交，或 sql-client.sh）

```sql
-- 会话级配置（Dinky 里放作业配置区 / sql-client 里先 SET）
SET execution.checkpointing.interval = 60s;   -- checkpoint 驱动文件滚动与容错，必开

-- ① Kafka 源表
CREATE TABLE kafka_src (
  id          BIGINT,
  name        STRING,
  event_time  TIMESTAMP(3)
) WITH (
  'connector' = 'kafka',
  'topic' = 'user_events',
  'properties.bootstrap.servers' = '192.168.0.106:9092',
  'properties.group.id' = 'flink_hive_loader',
  'scan.startup.mode' = 'group-offsets',       -- 断点续跑，不重复消费
  'format' = 'json',
  'json.ignore-parse-errors' = 'true'          -- 脏消息跳过（也可改成落死信）
);

-- ② HDFS 文件汇表（filesystem connector，分区目录 dt=…/hr=…）
CREATE TABLE hdfs_ods (
  id          BIGINT,
  name        STRING,
  event_time  TIMESTAMP(3),
  dt          STRING,
  hr          STRING
) PARTITIONED BY (dt, hr) WITH (
  'connector' = 'filesystem',
  'path' = 'hdfs://192.168.0.106:8020/data/staging/user_events',
  'format' = 'json',
  'sink.rolling-policy.rollover-interval' = '15 min',  -- 演示期可调 1 min
  'sink.rolling-policy.check-interval'   = '1 min',
  'sink.rolling-policy.file-size' = '64MiB'
);

-- ③ 主作业
INSERT INTO hdfs_ods
SELECT
  id, name, event_time,
  DATE_FORMAT(event_time, 'yyyy-MM-dd') AS dt,
  DATE_FORMAT(event_time, 'HH')         AS hr
FROM kafka_src;
```

要点：
- `PARTITIONED BY (dt, hr)` 让 filesystem connector 直接产出 `dt=…/hr=…` 目录，与 Hive 分区目录天然对齐
- **checkpoint 必开**：文件滚动和恢复语义都靠它；没 checkpoint 的 Flink 作业挂了会丢/重放整段数据
- 消费位点是 `group-offsets`：作业重启后从上次位点继续，配合 checkpoint 不丢不重（at-least-once，极端情况可能少量重复，见第六节去重）

---

## 五、分区注册 + 转换（定时脚本，复用生产方案模板）

Flink 只负责把文件写好；**分区元数据和转换由 Hive 侧脚本做**（每小时一次，如 `15 * * * *`，错开滚动周期）：

```bash
#!/bin/bash
# register_partitions.sh — 注册上一小时分区并转 ORC
set -euo pipefail
export TZ=Asia/Shanghai
DT=$(date -d '1 hour ago' +%F)
HR=$(date -d '1 hour ago' +%H)
BL="docker exec -i hive-server beeline -u jdbc:hive2://localhost:10000 -n hive --silent=true"

hsql(){ docker exec -i hive-server beeline -u jdbc:hive2://localhost:10000 -n hive \
        --silent=true -e "$1" 2>/dev/null >/dev/null || { echo "FAIL: $1"; exit 1; }; }

hsql "ALTER TABLE ods.user_events_di ADD IF NOT EXISTS PARTITION (dt='${DT}', hr='${HR}');"

hsql "SET hive.merge.tezfiles=true;
INSERT OVERWRITE TABLE dwd.user_events_di PARTITION (dt='${DT}', hr='${HR}')
SELECT id, name, CAST(event_time AS TIMESTAMP)
FROM ods.user_events_di WHERE dt='${DT}' AND hr='${HR}';"

echo "OK ${DT} ${HR}"
```

> 为什么"上一小时"而不是"当前小时"：当前小时的文件还在被 Flink 滚动写入，挂分区会读到半截文件——**延迟一个周期挂分区**就是流式场景下的"先校验后可见"。

---

## 六、验证流程（第一次跑通用 10 分钟）

```bash
# 1. 造两条消息
docker exec -i kafka kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic user_events \
  <<'EOF'
{"id":1,"name":"vic","event_time":"2026-10-06 20:00:00"}
{"id":2,"name":"hive","event_time":"2026-10-06 20:05:00"}
EOF

# 2. 等 Flink 滚动落盘（演示期把 rollover-interval 调 1 min），检查目录
hdfs dfs -ls -R /data/staging/user_events/dt=2026-10-06/

# 3. 手动挂分区 + 查询
beeline -e "ALTER TABLE ods.user_events_di ADD IF NOT EXISTS PARTITION (dt='2026-10-06', hr='20');
SELECT * FROM ods.user_events_di WHERE dt='2026-10-06' AND hr='20';"

# 4. 转 DWD 后在 Hue 里查
SELECT * FROM dwd.user_events_di WHERE dt='2026-10-06';
```

---

## 七、这条链路特有的坑（前置检查之外的补充）

| 问题 | 现象 | 对策 |
|---|---|---|
| Flink at-least-once 重复 | 作业故障恢复后少量消息重放 | `INSERT OVERWRITE` 幂等兜底；要求严格去重时 DWD 转换里按 `id+event_time` 用 `ROW_NUMBER()` 去重 |
| 半截文件被挂分区 | COUNT 波动/解析失败 | 分区注册延迟一个滚动周期；生产做法是 Flink 落 `_SUCCESS`（自定义 sink 发出）再注册 |
| `hadoop` 主机名解析失败 | Flink Pod 报 sockaddr 错误 | Flink 里 HDFS 一律写 `hdfs://192.168.0.106:8020`（docker 别名对 k3s 不可见） |
| Kafka 广播地址错误 | Flink 连上又断（0.0.0.0/内网地址） | bitnami 双 listener 配置（见前置检查） |
| 时区漂移 | dt/hr 归属错小时 | Flink `DATE_FORMAT` 受作业时区影响，统一 `Docker env TZ=Asia/Shanghai` 或用本地时间戳取值 |
| Hive 4 无 MR 引擎 | INSERT 报引擎不存在 | 正常，Tez 跑在 YARN 上（作业在 8088 可见） |

---

## 八、扩展方向（学完基础再看）

- **免手工挂分区**：Hudi/Iceberg 表（Flink 直接写，Hive metastore 共享，自动注册）；Hive 4 也可体验 ACID 表 + Streaming API，但复杂度高不建议入门用
- **Hue 直查 Kafka**：Hive 4 自带 `KafkaStorageHandler`（`STORED BY 'org.apache.hadoop.hive.kafka.KafkaStorageHandler'`），可以对 topic 做批扫描预览——学习用途可玩，生产别用它做入仓主链路
- **DataX 替代 Flink**：如果只要"定时把 Kafka 增量搬进 Hive"而不关心秒级延迟，一个消费者脚本 + cron 也能跑，但位点管理要自己做，不推荐超过 1 个 topic 的场景
