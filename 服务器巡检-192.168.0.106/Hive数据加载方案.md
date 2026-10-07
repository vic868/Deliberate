# Hive 数据加载方案（192.168.0.106）

> 编写日期：2026-10-06 · 适用栈：Hadoop 3.3.6 + Hive 4.0.0（Tez）+ Hue · 单节点 HDFS（余 137G）
> 关联：[[部署记录-Hadoop+Hue]] · [[巡检报告]]

---

## 一、先回答你的问题：对，但"挂法"有讲究

**"先写 HDFS，再加载进 Hive"就是大数据批量入库的标准姿势**，你的直觉完全正确。但"加载"有三种做法，量级和场景不同，选错会很痛苦：

| 做法 | 本质 | 适用量级 | 代价 |
|---|---|---|---|
| ① `INSERT INTO ... VALUES` | 逐条走 SQL 引擎 | 造数、百行以内 | ❌ 大数据量下极慢且产生垃圾小文件 |
| ② `INSERT INTO ... SELECT` | Tez 计算作业搬运/加工 | 中大批量 | 起作业有开销，但能顺带转换格式 |
| ③ **数据直接落 HDFS → 挂给表** | 纯文件操作，**不消耗计算资源** | **任意量级（推荐主路径）** | 需要自己管理目录/分区元数据 |

> [!important] 核心原则
> **数据搬运用文件操作（hdfs dfs），格式加工才用计算引擎（INSERT SELECT）。** 能不进 SQL 引擎的纯搬运就不要进。

---

## 二、推荐三层目录/表设计

```text
HDFS:
/data/staging/<表名>/dt=<日期>/          ← 原始文件暂存区（CSV/文本/JSON，宿主机 put 上来的）
/user/hive/warehouse/ods.db/<表>/dt=…/   ← ODS 层：外部表，指到 staging 数据
/user/hive/warehouse/dwd.db/<表>/dt=…/   ← DWD 层：ORC 内表（清洗+格式转换后），真正用于分析查询
```

为什么分两层：
- **ODS 外表**（`EXTERNAL` + TextFile）：原始数据原样进 Hive，坏了随时可重灌，删表不删数据
- **DWD 内表**（`STORED AS ORC` + Snappy）：列存压缩后查询快、省磁盘；一次性 `INSERT SELECT` 生成
- 以后学分区裁剪、数据倾斜、compaction 都在这套结构上做，和生产数仓习惯一致

---

## 三、四种加载场景落地

### 场景 A：宿主机/外部文件（CSV、日志）批量入库 —— 主路径

```bash
# ① 宿主机文件推到 HDFS staging（按日期分区）
hdfs dfs -mkdir -p /data/staging/t1/dt=2026-10-06
hdfs dfs -put /path/on/host/data.csv /data/staging/t1/dt=2026-10-06/

# ② 挂分区（外表已建好时，一行搞定；纯文件移动，秒级）
beeline -u "jdbc:hive2://localhost:10000" -n hive \
  -e "ALTER TABLE ods.t1 ADD IF NOT EXISTS PARTITION (dt='2026-10-06') LOCATION '/data/staging/t1/dt=2026-10-06';"
```

ODS 外表建表模板：

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS ods.t1 (
  id INT, name STRING
)
PARTITIONED BY (dt STRING)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
LOCATION '/data/staging/t1';
```

> [!warning] 两个经典坑
> - `LOAD DATA LOCAL INPATH` 的 **LOCAL 指 beeline 客户端所在的机器**——你用别名在宿主机执行时，"本地"其实是 hive-server **容器内部**。宿主机文件要么先 `hdfs dfs -put`，要么先 `docker cp` 进容器。**统一用 put 到 HDFS 的路径，别用 LOCAL。**
> - `LOAD DATA INPATH` 是**移动**（原 staging 文件会消失），`ADD PARTITION` 不动文件。要保留原始文件做重放，用 **ADD PARTITION**。

### 场景 B：ODS → DWD（格式转换 ORC）

```sql
-- 每天分区加载后跑一次（可放同一脚本）
INSERT OVERWRITE TABLE dwd.t1 PARTITION (dt='2026-10-06')
SELECT id, name FROM ods.t1 WHERE dt='2026-10-06';
```

DWD 内表模板：

```sql
CREATE TABLE IF NOT EXISTS dwd.t1 (
  id INT, name STRING
)
PARTITIONED BY (dt STRING)
STORED AS ORC
LOCATION '/user/hive/warehouse/dwd.db/t1'
TBLPROPERTIES ('orc.compress'='SNAPPY');
```

### 场景 C：MySQL 业务数据进来（无 Sqoop 的轻量做法）

这台机器没装 Sqoop/DataX（Sqoop 对 Hadoop3 支持也老了），轻量路径：

```bash
# mysql 容器内导出 CSV（secure_file_priv 目录）
docker exec mysql sh -c "mysql -uroot -p\$MYSQL_ROOT_PASSWORD -e \"
  SELECT id,name FROM mydb.t1 INTO OUTFILE '/var/lib/mysql-files/t1.csv'
  FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n';\""
docker cp mysql:/var/lib/mysql-files/t1.csv /tmp/t1.csv
# 之后走场景 A
```

量大/要定时同步时，值得装一个 **DataX**（单机 json 配置，比 Sqoop 轻）——学习成本一次性。

### 场景 D：Kafka 流式数据持续落 Hive

机器上 Kafka 和 Flink（k3s）都是现成的，实时链路：

```text
Kafka → Flink FileSink（按 dt=yyyy-MM-dd 滚动写 HDFS, Text/ORC）→ 定时脚本 ADD PARTITION
```

Flink 侧用 `FileSink` 的 `OnCheckpointRollingPolicy`（或桶策略按日期分桶），落盘目录对齐 `/data/staging/<表>/dt=…`，分区注册复用场景 A 的脚本。**进阶**（暂不展开）：Hudi/Iceberg 可以免去手工 ADD PARTITION，学完基础再来。

### 场景 E：小批量即席

几行造数/临时验证：直接 Hue 里 `INSERT INTO ... VALUES`，无所谓。**这条永远不要用于批量。**

---

## 四、定时加载脚本模板（可直接抄）

宿主机 `/opt/hadoop-docker/scripts/load_t1.sh`：

```bash
#!/bin/bash
set -euo pipefail
DT=$(date +%F)
CSV="/data/export/t1-${DT}.csv"                       # 当天待入库文件（上游生成）
STAGE="/data/staging/t1/dt=${DT}"

# 1. 上传 staging（覆盖重跑幂等）
hdfs dfs -mkdir -p "$STAGE"
hdfs dfs -put -f "$CSV" "$STAGE/"

# 2. 挂分区 + 转 ORC（两条 beeline）
beeline -u "jdbc:hive2://localhost:10000" -n hive --silent=true -f /opt/hadoop-docker/scripts/load_t1.sql \
  --hivevar DT="$DT"

# 3. 校验：行数比对（文件行数 vs 表行数）
LINES=$(( $(wc -l < "$CSV") ))
CNT=$(beeline -u "jdbc:hive2://localhost:10000" -n hive --silent=true \
  --outputformat=tsv2 -e "SELECT COUNT(*) FROM dwd.t1 WHERE dt='${DT}';" 2>/dev/null | tail -1)
echo "文件行数=$LINES 表行数=$CNT"
[ "$LINES" = "$CNT" ] || { echo "行数不一致，人工检查！"; exit 1; }

# 4. 清理 CSV（staging 是 ODS 数据源，保留）
rm -f "$CSV"
```

`load_t1.sql`：

```sql
ALTER TABLE ods.t1 ADD IF NOT EXISTS PARTITION (dt='${hivevar:DT}');
INSERT OVERWRITE TABLE dwd.t1 PARTITION (dt='${hivevar:DT}')
SELECT id, name FROM ods.t1 WHERE dt='${hivevar:DT}';
```

cron（宿主机）：

```cron
0 2 * * * /opt/hadoop-docker/scripts/load_t1.sh >> /var/log/load_t1.log 2>&1
```

> [!note] 前置：给宿主机加 beeline 别名
> `alias beeline='docker exec -i hive-server beeline -u jdbc:hive2://localhost:10000 -n hive'`
> （脚本里用 `docker exec -i` 不加 `-t`，cron 下才能正常执行。要我现在就把它加到 root/vic 的 bashrc 说一声。）

---

## 五、规范与性能要点

1. **分区键用 `dt STRING`（yyyy-MM-dd）**，一天一分区；**不要**用小时级/用户级等高基数分区（单节点会被小文件拖死）
2. **文件大小控制在 128M~1G**：上游切好再 put；已产生的小文件用 `hive.merge.tezfiles=true`（set 后 INSERT SELECT 自动合并）
3. **重跑幂等**：加载一律 `INSERT OVERWRITE ... PARTITION(dt=…)`，配合上游 `-put -f`，同一天数据随便重跑
4. **校验三件套**：行数比对（如上）、`hdfs dfs -count /data/staging/...`、抽样 `SELECT * LIMIT 10` 人工瞄
5. **staging 保留策略**：ODS 数据是原始凭证，保留；导出的 CSV 在校验通过后删除，别把宿主机磁盘塞满
6. **HDFS 权限已关**（学习环境），生产化时第一件事是开 `dfs.permissions.enabled=true` + 按目录授权

---

## 六、这台机器的现实约束

| 约束 | 影响 | 对策 |
|---|---|---|
| 单盘剩余 137G | 原始 CSV + ORC 双份存储 | CSV 校验完就删；ORC 有压缩通常省 3~5 倍 |
| YARN 只给了 8G / 4 vcores | INSERT SELECT 转换并发有限 | 单次转换数据 ≤ 几十 GB 没问题；别和 ES/Kafka 高峰撞车 |
| 单节点 = 无真正分布式 | 感受不到数据本地性 | 学习目标聚焦 SQL/分层/分区，集群课题留到多节点 |

---

## 七、速查

```sql
-- 挂分区
ALTER TABLE ods.t1 ADD IF NOT EXISTS PARTITION (dt='2026-10-06') LOCATION '/data/staging/t1/dt=2026-10-06';
-- 批量修复所有分区（目录结构对齐后一次全挂；分区多时慢，日常用上面那条）
MSCK REPAIR TABLE ods.t1;
-- 覆盖重跑某天
INSERT OVERWRITE TABLE dwd.t1 PARTITION (dt='2026-10-06') SELECT ... ;
-- 查看分区
SHOW PARTITIONS ods.t1;
-- 删某天重灌
ALTER TABLE dwd.t1 DROP IF EXISTS PARTITION (dt='2026-10-06');
```
