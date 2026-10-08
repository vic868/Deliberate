# Kafka → Hive 实操手册（flink-demo 实战）

> 编写日期：2026-10-06 · 目标：**你亲手**把 Kafka 消息落到 Hive，理解每一步为什么这么做
> 环境：192.168.0.106 · Kafka(bitnami 3.9) + Hive 4.0 + MySQL metastore + Hue
> 数据源：topic `flink-demo`（KafkaDataGenerator 已在推，JSON 订单数据）
> 关联：[[Kafka消息入Hive方案]] · [[Hive数据加载方案]]（幂等/对账规范）· [[部署记录-Hadoop+Hue]]
> 实测前置：`flink-demo` offset 已 222 万+；镜像里有 Kafka 连接器、**没有 Hadoop 客户端**（决定走路径 A）

---

## 第 0 步：理解全局（动手前必读 3 分钟）

```text
Kafka topic flink-demo
   │ ① 消费（consumer group 管位点，断点续拉）
   ▼
宿主机文件（JSON 行） ──► 按事件时间分桶（python 解析 timestamp → dt）
   │ ② hdfs put（stdin 管道进 hadoop 容器）
   ▼
HDFS /data/staging/flink-demo/dt=2026-10-07/xxx.jsonl
   │ ③ ADD PARTITION（把目录"登记"进 Hive 元数据）
   ▼
ods.flink_demo_di 外表（JSON 原样）
   │ ④ INSERT OVERWRITE + 去重（Tez 作业）
   ▼
dwd.flink_demo_di 内表（ORC）──► Hue 查询
```

**三个必须建立的概念**：
1. **位点（offset）**：消费组在每个分区上记住"读到哪了"。用 `--group` 消费，下次自动续读——这就是为什么不用你记进度
2. **分区（partition）**：Hive 表按 `dt` 分目录。HDFS 上建了目录 ≠ Hive 能查到，**必须 ADD PARTITION 登记元数据**（上次的 sockaddr 事故同理：目录存在和元数据存在是两回事）
3. **幂等**：脚本重复跑结果必须一致。本方案靠三件套：consumer group 位点 + 唯一文件名 + DWD `INSERT OVERWRITE`

**两条路径，先 A 后 B**：

| 路径 | 做法 | 前提 | 适合 |
|---|---|---|---|
| **A（本手册主路径）** | 宿主机消费者脚本拉增量 → hdfs put | 无（所有工具都是现成的） | 今天就能跑通 |
| B（进阶） | Flink SQL FileSink 直写 HDFS | 需给 Flink 镜像补 hadoop 依赖（第 8 步） | 想学流式引擎 |

---

## 第 1 步：认识你的数据（1 分钟）

```bash
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 --topic flink-demo \
  --from-beginning --max-messages 2
```
预期输出（字段清单就是建表依据）：
```json
{"orderId":"a1b2c3...","userId":"U12345","product":"手机","amount":358.2,"city":"北京","platform":"App","timestamp":1791302288937}
```
✅ 检查点：能打出 JSON，7 个字段：`orderId, userId, product, amount, city, platform, timestamp(毫秒)`。
> 注意容器内用 **29092**（INTERNAL listener），9092 是给外部用的——容器内连 9092 会拿到广播地址 192.168.0.106 绕一圈甚至超时。

---

## 第 2 步：建库建表（Hive 元数据）

进 beeline（宿主机执行，全路径）：

```bash
docker exec -i hive-server beeline -u "jdbc:hive2://localhost:10000" -n hive
```

```sql
-- ① 两个库：分层是数仓的地基
CREATE DATABASE IF NOT EXISTS ods;   -- Operational Data Store：原样暂存
CREATE DATABASE IF NOT EXISTS dwd;   -- Data Warehouse Detail：清洗后的明细

-- ② ODS 外部表：列名必须和 JSON 的 key 完全一致（JsonSerDe 按名字映射）
CREATE EXTERNAL TABLE IF NOT EXISTS ods.flink_demo (
  `orderId`  STRING,
  `userId`   STRING,
  product    STRING,
  amount     DECIMAL(12,2),,
  city       STRING,
  platform   STRING,
  `timestamp` BIGINT          -- 毫秒时间戳，原样存 BIGINT（解析放 DWD）
)
PARTITIONED BY (dt STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.JsonSerDe'
LOCATION '/data/staging/flink-demo';

-- ③ DWD 内表：类型收紧 + 事件时间解析好
CREATE TABLE IF NOT EXISTS dwd.flink_demo (
  orderId     STRING,
  userId      STRING,
  product     STRING,
  amount      DECIMAL(12,2),
  city        STRING,
  platform    STRING,
  event_time  TIMESTAMP
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/user/hive/warehouse/dwd.db/flink_demo'
TBLPROPERTIES ('orc.compress'='SNAPPY');
```

✅ 检查点：`SHOW DATABASES;` 见 ods/dwd；`SHOW CREATE TABLE ods.flink_demo_di;` 正常。
> **为什么 ODS 用外部表**：外表 DROP 时只删元数据不删文件——试错成本为零。`timestamp` 是 Hive 关键字，DDL/DML 里都要用反引号 `` ` `` 包起来。

---

## 第 3 步：准备 staging 目录 + 加载脚本

在 **106 宿主机**上创建：

```bash
mkdir -p /opt/hadoop-docker/scripts /data/export
hdfs dfs -mkdir -p /data/staging/flink-demo     # 通过 hadoop 容器执行
```

写入 `/opt/hadoop-docker/scripts/load_kafka.sh`（完整内容见下，建议手敲体会）：

```bash
#!/bin/bash
# Kafka → ODS → DWD 增量加载（幂等，可重复执行）
set -euo pipefail
export TZ=Asia/Shanghai
GROUP=hive_loader
WORK=/tmp/kafka_loader; mkdir -p $WORK
exec 9>/tmp/load_kafka.lock; flock -n 9 || { echo "已有实例在跑"; exit 0; }

# ① 拉增量：group 记录位点，断点续拉；90 秒无新消息自动退出
#    首次补历史：BACKFILL=1 ./load_kafka.sh（从最早开始读）
if [ "${BACKFILL:-0}" = "1" ]; then FB="--from-beginning"; else FB=""; fi
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:29092 --topic flink-demo \
  --group $GROUP $FB --timeout-ms 90000 > $WORK/raw.jsonl
LINES=$(wc -l < $WORK/raw.jsonl | tr -d ' ')
echo "[$(date '+%F %T')] 拉取 $LINES 条"
[ "$LINES" -eq 0 ] && echo "无新消息" && exit 0

# ② 按事件时间分桶：解析消息里的 timestamp 毫秒 → dt=YYYY-MM-DD 目录
RUN=$(date +%s)
cat $WORK/raw.jsonl | RUN=$RUN python3 -c '
import sys, json, datetime, os
run = os.environ["RUN"]
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: o = json.loads(line)
    except Exception: continue
    t = o.get("timestamp")
    if not t: continue
    dt = datetime.datetime.fromtimestamp(t/1000).strftime("%Y-%m-%d")
    d = f"/tmp/split/dt={dt}"; os.makedirs(d, exist_ok=True)
    with open(f"{d}/{run}.jsonl", "a") as f: f.write(line + "\n")
'

# ③ 每个分区目录：上传（唯一文件名，重跑不覆盖别人的数据）+ 挂分区
for DTDIR in /tmp/split/dt=*; do
  DT=$(basename "$DTDIR" | cut -d= -f2)
  STAGE=/data/staging/flink-demo/dt=$DT
  docker exec hadoop hdfs dfs -mkdir -p "$STAGE"
  cat "$DTDIR"/*.jsonl | docker exec -i hadoop hdfs dfs -put -f - "$STAGE/${RUN}.jsonl"
  docker exec -i hive-server beeline -u "jdbc:hive2://localhost:10000" -n hive --silent=true \
    -e "ALTER TABLE ods.flink_demo_di ADD IF NOT EXISTS PARTITION (dt='${DT}');" 2>/dev/null >/dev/null
  echo "ODS 分区 $DT 就绪"

  # ④ DWD 转换：按 orderId 去重 + 时间戳解析（OVERWRITE=幂等，重跑安全）
  docker exec -i hive-server beeline -u "jdbc:hive2://localhost:10000" -n hive --silent=true \
    -e "SET hive.merge.tezfiles=true;
        INSERT OVERWRITE TABLE dwd.flink_demo_di PARTITION (dt='${DT}')
        SELECT orderId, userId, product, amount, city, platform,
               FROM_UNIXTIME(CAST(`timestamp`/1000 AS BIGINT)) AS event_time
        FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY orderId ORDER BY \`timestamp\` DESC) AS rn
              FROM ods.flink_demo_di WHERE dt='${DT}') t
        WHERE rn = 1;" 2>/dev/null >/dev/null
  echo "DWD 分区 $DT 转换完成"
done

# ⑤ 对账：DWD 行数应等于 ODS 该分区去重后的行数
echo "对账: $(docker exec -i hive-server beeline -u 'jdbc:hive2://localhost:10000' -n hive --silent=true \
  --outputformat=tsv2 -e "SELECT COUNT(*) FROM dwd.flink_demo_di WHERE dt='$(date +%F)';" 2>/dev/null | tail -1) 行"
```

cron 定时（学习期可先手动跑）：

```shell
crontab -e  #编辑，保存后直接生效

crontab -l #查看
```



```cron
20 * * * * /opt/hadoop-docker/scripts/load_kafka.sh >> /var/log/load_kafka.log 2>&1
```

---

## 第 4 步：执行并观察（学习重点）

```bash
# 首次（补历史 222 万条，约 1-3 分钟）
# 注意：你已是 root，不用 sudo；且 BACKFILL=1 要放在命令前（sudo 默认会重置环境变量）
chmod +x /opt/hadoop-docker/scripts/load_kafka.sh    # 新建脚本先补执行位
BACKFILL=1 /opt/hadoop-docker/scripts/load_kafka.sh

# 之后（每小时 cron 自动跑，也可手动）
/opt/hadoop-docker/scripts/load_kafka.sh
```

**每一步观察什么（这才是学习）**：

```bash
# ① staging 目录结构 = 事件时间的物化
hdfs dfs -ls -R /data/staging/flink-demo | head -10

# ② 位点前进：每次跑完 group 的 offset 往后走
docker exec kafka kafka-consumer-groups.sh --bootstrap-server localhost:29092 \
  --describe --group hive_loader
# LAG 列 = 还没消费的量；CURRENT-OFFSET = 读到哪了

# ③ 元数据里"分区"出现了
docker exec -i hive-server beeline -u "jdbc:hive2://localhost:10000" -n hive \
  --silent=true -e "SHOW PARTITIONS ods.flink_demo_di;"

# ④ 转 ORC 后文件大小对比（通常缩 3~5 倍）
hdfs dfs -du -h /data/staging/flink-demo/dt=2026-10-07
hdfs dfs -du -h /user/hive/warehouse/dwd.db/flink_demo_di/dt=2026-10-07

# ⑤ Hue 里查（http://192.168.0.106:8888 → Query Editors → Hive）
SELECT city, COUNT(*) cnt, ROUND(SUM(amount),2) gmv
FROM dwd.flink_demo_di WHERE dt = '2026-10-07'
GROUP BY city ORDER BY gmv DESC;
```

---

## 第 5 步：必踩的坑与解释（对照检查你遇到过没有）

| 报错/现象 | 为什么 | 怎么办 |
|---|---|---|
| `sudo: cannot execute xxx.sh: Permission denied` | 新建脚本默认 `644` 没有 **x 执行位**；而且脚本是给解释器读的文本，**有 x 没 r 也一样报错**（exec 需要 r+x） | `chmod +x 脚本`。另外 root 下 `sudo` 多余；`VAR=1 sudo cmd` 会被 sudo 的 `env_reset` 把变量丢掉——要传环境变量用 `sudo VAR=1 cmd` 或干脆不用 sudo |
| 建外表报 `file:/xxx is not a directory or unable to create one` | LOCATION 被解析到**容器本地文件系统**——compose 里的 `-Dfs.defaultFS` 对 DDL 不生效，且 HDFS 目录没建 | 已修：挂载 `core-site.xml` 进 hive 容器（compose 已加）+ 手册第 3 步先 `hdfs dfs -mkdir`。**建外部表前目录必须存在** |
| 首次跑没有历史数据（0 条） | group 默认从 latest 开始；且一旦 group 有了已提交位点，`--from-beginning` 就被忽略——首次不带 BACKFILL 的运行会把位点提交到末尾，"毒化"该组 | 重置位点（组无活跃成员时）：`kafka-consumer-groups.sh --reset-offsets --to-earliest --execute --group hive_loader --topic flink-demo`，然后再 `BACKFILL=1` 重跑 |
| `TimeoutException ... terminating consumer process` | `--timeout-ms` 空闲超时的正常退出方式 | 不是故障，脚本就是靠它结束的 |
| consumer-groups 显示 LAG=0 但 Hive 没数据 | 位点≠已入仓：LAG 只说明 Kafka 消费完了，加载/转换可能还没跑 | 看 staging 目录和 dwd 行数对账 |
| `InaccessibleObjectException`（本地跑 Flink 1.14 时） | JDK17 模块封装 | 用 `start.sh`（15 个 add-opens 已配全） |
| Hue 连 Hive 报 sockaddr | 主机名解析问题 | 服务名/别名一致（已修） |
| `database is locked` | Hue 元数据 sqlite 并发 | 已迁 MySQL |
| 查询报 `Timestamp`/字段 NULL | JSON key 和列名不一致 | JsonSerDe 按名字映射，列名必须等于 key |
| 对账行数不等 | 有重复 orderId | 正常，DWD 去重后看 DWD 数 |
| 对账/转换报 `from_unixtime takes only int/long types. Got DOUBLE` | Hive 除法 `/1000` 产生 DOUBLE，Hive 4 的 from_unixtime 不收 DOUBLE | `CAST(\`timestamp\`/1000 AS BIGINT)` 再传入；**别把 beeline 的 stderr 全部 /dev/null**，至少打到日志文件 |
| SUM(amount) 出 `511058.11999999994` 多位小数 | DOUBLE 是二进制浮点，0.2 无法精确表示，单条被显示舍入掩盖，SUM 累积放大 | 展示层 `ROUND(SUM(amount),2)`；治本：金额列用 **DECIMAL(12,2)**（DWD 建表规范），ODS 可保持原样 |
| Dinky 提交报 `CatalogStoreHolder cannot be null`
| Flink 作业反复重启，日志 `Failed to deserialize consumer record due to` | `earliest-offset` 扫全史时撞上 topic 里混着的旧非 JSON 消息（wordcount 实验等），且作业从失败点循环重启（checkpoint 未成功→位点不前进→永远撞同一条） | kafka_src 加 `'json.ignore-parse-errors'='true'`；**查根因用 REST `/jobs/<id>/exceptions` 看第一次失败**——`Checkpoint Coordinator is suspending` 只是重启噪音 | | Dinky 1.2.4 的 1.14 构建内嵌执行器 + Flink 1.20 类 → API 断层（1.19+ 要求必填 CatalogStoreHolder） | 首选 sql-client 直跑（版本一致）；长期：换 `dinky-release-1.20-1.2.4` 构建（官方有）或升级 1.2.5 |
| 容器内 9092 超时 | 9092 是 EXTERNAL listener | 容器内操作一律 29092 |

---

## 第 6 步（进阶）：路径 B —— Flink 直写 HDFS

跑通路径 A 后再玩。要做的事：

> [!danger] Dinky 1.2.4（1.14 构建）驱动 Flink 1.20 会 NPE（实测）
> 在 Dinky 里提交 FlinkSQL 报 `CatalogStoreHolder cannot be null`——Dinky Pod 内嵌 Flink 1.14 变体（`extends/flink1.14`），其执行器构建 CatalogManager 时不设置 1.19+ 新增的必填项 CatalogStoreHolder。**别用 Dinky 的 Local 模式跑这个任务**（本机实测 NPE），用下面 sql-client 直跑（版本零错配）；要继续用 Dinky 就换 `dinky-release-1.20-1.2.4`（官方有 1.20 构建）重建镜像，或升级 1.2.5。

1. **补 Hadoop 依赖**：`flink-shaded-hadoop-2-uber-2.8.3-10.0.jar` 已在宿主机 `/opt/flink/usrlib/`，通过 usrlib 中转法进 lib 并重启的**完整已验证步骤**见 [[Flink-on-K8s-vs-YARN]] 的"实操记录"一节（JM/TM 都要生效，重启会杀 session 上已有作业）
2. **Flink SQL**（Dinky http://192.168.0.106:30888 或 `kubectl exec ... sql-client.sh`）：

```sql
SET execution.checkpointing.interval = 60s;
CREATE TABLE kafka_src (orderId STRING, userId STRING, product STRING,
  amount DOUBLE, city STRING, platform STRING, `timestamp` BIGINT) WITH (
  'connector'='kafka', 'topic'='flink-demo',
  'properties.bootstrap.servers'='192.168.0.106:9092',
  'properties.group.id'='flink_hdfs_sink',
  'scan.startup.mode'='latest-offset',
  'json.ignore-parse-errors'='true',   -- ★ 2026-10-07 事故修复：跳过 topic 里混着的旧非 JSON 消息
  'format'='json');
CREATE TABLE hdfs_ods (orderId STRING, userId STRING, product STRING,
  amount DOUBLE, city STRING, platform STRING, `timestamp` BIGINT,
  dt STRING) PARTITIONED BY (dt) WITH (
  'connector'='filesystem', 'path'='hdfs://192.168.0.106:8020/data/staging/flink-demo',
  'format'='json', 'sink.rolling-policy.rollover-interval'='15 min');
INSERT INTO hdfs_ods
SELECT *, DATE_FORMAT(TO_TIMESTAMP_LTZ(`timestamp`,3), 'yyyy-MM-dd') AS dt FROM kafka_src;
```
3. 之后分区注册/转换/对账与路径 A 完全相同（脚本复用）
4. 注意 Flink 里 HDFS 地址写 IP：`hdfs://192.168.0.106:8020`（`hadoop` 别名对 k3s Pod 不可见）

> [!danger] 首跑实测报错：`NoOffsetForPartitionException: Undefined offset with no reset policy for partitions: [flink-demo-0]`（2026-10-07）
> 原因：`scan.startup.mode='group-offsets'` 要求 group 有**已提交位点**，新 group `flink_hdfs_sink` 没有任何位点且消费端没配 reset 策略 → Kafka 直接抛异常。**修正（三选一，推荐第一种）：**
>
> ```sql
> -- ① 补历史：从最早开始（推荐，能一并入仓存量消息）
> 'scan.startup.mode' = 'earliest-offset',
>
> -- ② 只消费新消息
> 'scan.startup.mode' = 'latest-offset',
>
> -- ③ 保留 group-offsets 但加兜底
> 'properties.auto.offset.reset' = 'earliest',
> ```
>
> **操作序列**：先取消失败的作业（`SHOW JOBS;` → `CANCEL JOB '<jobId>';`，或 Flink UI 30081 上 cancel）→ 按修正版重建 kafka_src → 重新 INSERT。

> [!warning] 布局冲突：路径 B 不要和路径 A 混用同一个 staging 根目录
> Flink 产出的是 `dt=…/hr=…` **子目录**，路径 A 写的是 `dt=…/data.jsonl` **直接文件**——混在同一个 Hive 分区目录里，Hive 默认不递归子目录，会互相看不见。**修正：路径 B 用独立目录 + 双级分区表：**

```sql
-- 路径 B 专用表（dt+hr 双级分区，与 Flink 落盘目录 dt=…/hr=… 一一对应）
CREATE EXTERNAL TABLE IF NOT EXISTS ods.flink_demo_hi (
  orderId STRING, userId STRING, product STRING, amount DOUBLE,
  city STRING, platform STRING, `timestamp` BIGINT
) PARTITIONED BY (dt STRING, hr STRING)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.JsonSerDe'
LOCATION '/data/staging/flink-demo-stream';

CREATE TABLE IF NOT EXISTS dwd.flink_demo_hi (
  orderId STRING, userId STRING, product STRING, amount DECIMAL(12,2),
  city STRING, platform STRING, event_time TIMESTAMP
) PARTITIONED BY (dt STRING, hr STRING)
STORED AS ORC LOCATION '/user/hive/warehouse/dwd.db/flink_demo_hi'
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- Flink 滚动落盘后（checkpoint 周期到了再看目录）挂分区 + 转换（幂等）：
ALTER TABLE ods.flink_demo_hi ADD IF NOT EXISTS
  PARTITION (dt='2026-10-07', hr='15');
INSERT OVERWRITE TABLE dwd.flink_demo_hi PARTITION (dt='2026-10-07', hr='15')
SELECT orderId, userId, product, CAST(amount AS DECIMAL(12,2)), city, platform,
       FROM_UNIXTIME(CAST(`timestamp`/1000 AS BIGINT))
FROM ods.flink_demo_hi WHERE dt='2026-10-07' AND hr='15';
```

---

## 附：本手册学到的东西清单（自测）

- [ ] 说出 consumer group / offset / LAG 的关系
- [ ] 说出"目录存在"和"分区存在"的区别（ADD PARTITION 做了什么）
- [ ] 说出 ODS 用外部表、DWD 用内表的理由
- [ ] 手动模拟：删掉 DWD 某分区数据再重跑脚本，验证幂等
- [ ] 解释为什么分区注册要延后/去重要放 DWD
- [ ] 改造练习：把脚本改成按小时分桶（dt + hr）
