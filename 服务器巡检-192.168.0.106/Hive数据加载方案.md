# Hive 数据加载生产方案 v2（含事故案例库）

> 版本：v2.0 · 2026-10-06 · 适用：192.168.0.106（Hadoop 3.3.6 + Hive 4.0.0/Tez + MySQL metastore + Hue）
> 定位：数据接入 SOP + 故障应对手册 · 关联：[[部署记录-Hadoop+Hue]] · [[巡检报告]]
> 声明：本方案按生产标准编写，其中"事故案例库"包含本机真实发生过的故障与业界高频事故；第七节列出了学习环境与生产环境的差距清单，每一条都是上生产前必须补的课。

---

## 一、目标与非目标

**目标**：任何规模的数据从外部进入 Hive，全程可校验、可重跑、可追溯、可告警；单点故障不丢数据；一次故障的修复成本 ≤ 一次重跑成本。

**非目标（当前环境不承诺）**：高可用（单节点）、多租户隔离、准实时（分钟级）入仓。这些在第七节差距清单中。

**两条铁律**（所有事故的通用解）：
1. **幂等优先**：任何加载任务，重跑 N 次的结果 == 跑 1 次的结果。做不到幂等的流程，故障恢复就等于赌博。
2. **先校验后可见**：数据没有过完校验关卡，下游不允许看到它。

---

## 二、总体架构与分层

```text
外部数据源                    HDFS                                Hive
──────────                ─────────────────────────────────    ─────────────────
MySQL 导出 CSV   ─┐        /data/staging/<表>/dt=日期/   ← 原始暂存（可重放）
日志/文件        ─┼─put──→        │ 原子 rename 归位           │
Kafka→Flink 落盘 ─┘        ↓                            ↓
                       .tmp → _SUCCESS 标记      ods 外部表（TextFile，原样保存）
                                                    │ INSERT OVERWRITE（Tez，清洗+转换）
                                                    ↓
                                           dwd 内部表（ORC+Snappy，分析用）
```

- **staging 是原始凭证**：出任何问题都能从这里重放，因此永远不清空、目录按 dt 组织
- **ODS 外表**：`EXTERNAL`，删表不删数据；列类型宽泛（STRING 优先），忠实保存原貌
- **DWD 内表**：ORC 列存 + 类型收紧 + 清洗逻辑，是给下游用的"合格品"
- 每一层之间以**分区**为单位流转，全链路 T+1 幂等

---

## 三、加载方式选型（决策树）

```text
数据从哪来？
├─ 文件/日志（宿主机或上游推送）
│   └─ 量大/要重放 → put 到 staging + 外表 ADD PARTITION   ★主路径
│   └─ 一次性小文件 → LOAD DATA INPATH（注意：是移动，不是复制）
├─ MySQL 业务库
│   └─ 小表/一次性 → SELECT INTO OUTFILE → CSV → 走文件路径
│   └─ 大表/定时   → 部署 DataX（json 配置，mysql→hdfs 直写）
├─ Kafka 流
│   └─ Flink FileSink 按 dt 滚动写 staging → 同文件路径（分区注册脚本共用）
│      ★ 完整落地版见 [[Kafka消息入Hive方案]]（建库建表 SQL、Flink 作业全文、验证流程）
└─ 几行造数
    └─ Hue 里 INSERT VALUES（永远不用于批量）
```

| 方式 | 走计算引擎 | 量级 | 幂等性 | 一句话 |
|---|---|---|---|---|
| put + ADD PARTITION | ❌ | 任意 | 目录可覆盖 | **首选**，纯文件操作 |
| LOAD DATA INPATH | ❌ | 任意 | 文件被移走，重跑需重新 put | 一次性小文件 |
| INSERT SELECT | ✅ Tez | 中大 | OVERWRITE 分区即幂等 | 用于**转换**，不是搬运 |
| INSERT VALUES | ✅ | <100 行 | 追加，不幂等 | 只造数 |

---

## 四、标准接入流程（七道关卡）

每个新表/新数据源上线，按此流程走一遍；日常加载是流程 3~7 的循环。

| # | 关卡 | 通过标准 | 不通过的后果 |
|---|---|---|---|
| 1 | **登记**：数据源、负责人、时效要求（T+1?）、体量预估、保留期 | 表登记存在 | 无主数据不许接入 |
| 2 | **建模**：ODS 外表 + DWD 内表 DDL 评审（分区键、类型、分隔符、编码） | DDL 入 git | 类型纠偏成本随数据量指数增长 |
| 3 | **上传**：文件 → `.tmp` → md5 记录 → 原子 rename 进分区目录 | `_SUCCESS` 就绪标记存在 | 下游读到半截文件 |
| 4 | **挂载**：`ADD PARTITION`（或 MSCK） | `SHOW PARTITIONS` 可见 | 数据在 HDFS 但 Hive 查无此人 |
| 5 | **对账**：文件行数 == `COUNT(*)`，主键无重复，关键列空值率/值域检查 | 校验 SQL 全绿 | 脏数据流向下游 |
| 6 | **转换**：`INSERT OVERWRITE` 到 DWD（ORC） | 转换后行数对账一致 | — |
| 7 | **发布**：校验通过后分区才算"就绪"（DWD 分区存在即发布） | — | — |

---

## 五、生产级加载脚本（模板）

```bash
#!/bin/bash
# load_t1.sh — T+1 加载 ods.t1 → dwd.t1
# 用法: load_t1.sh [日期，默认昨天]; 可重复执行（幂等）
set -uo pipefail
export TZ=Asia/Shanghai

DT=${1:-$(date -d yesterday +%F)}          # 数据归属日期（T-1），与调度周期解耦
TABLE=t1
HDFS_STAGE=/data/staging/${TABLE}/dt=${DT}
LOCAL_FILE=/data/export/${TABLE}/${TABLE}-${DT}.csv
LOCK=/tmp/load_${TABLE}.lock
LOG=/var/log/hive_load/${TABLE}/load_${DT}.log
mkdir -p /var/log/hive_load/${TABLE}

exec 9>"$LOCK"
flock -n 9 || { echo "$(date '+%F %T') 已有实例在跑，退出" >> "$LOG"; exit 0; }   # 防双跑

log(){ echo "$(date '+%F %T') [$TABLE/$DT] $*" | tee -a "$LOG"; }
alert(){ log "ALERT: $*"; exit 2; }        # 生产中此处接钉钉/企业微信 webhook

BL="docker exec -i hive-server beeline -u jdbc:hive2://localhost:10000 -n hive --silent=true"
hsql(){ $BL -e "$1" 2>>"$LOG" >/dev/null || alert "HiveSQL 失败: $1"; }
cnt(){ $BL --outputformat=tsv2 -e "$1" 2>>"$LOG" | tail -1; }

log "=== 开始 ==="

# G1 上游就绪
[ -s "$LOCAL_FILE" ] || alert "源文件不存在或为空: $LOCAL_FILE"
LINES=$(wc -l < "$LOCAL_FILE"); [ "$LINES" -gt 0 ] || alert "源文件 0 行"
MD5_NOW=$(md5 -q "$LOCAL_FILE" 2>/dev/null || md5sum "$LOCAL_FILE" | cut -d' ' -f1)

# G2 上传（tmp → 原子 rename，避免下游读到半截分区）
hdfs dfs -mkdir -p "${HDFS_STAGE}.tmp"
hdfs dfs -put -f "$LOCAL_FILE" "${HDFS_STAGE}.tmp/data.csv"
hdfs dfs -rm -r -f "$HDFS_STAGE" >/dev/null
hdfs dfs -mv "${HDFS_STAGE}.tmp" "$HDFS_STAGE"        # HDFS rename 原子
touch /tmp/_s && hdfs dfs -put -f /tmp/_s "$HDFS_STAGE/_SUCCESS" && rm /tmp/_s

# G3 挂载
hsql "ALTER TABLE ods.${TABLE} ADD IF NOT EXISTS PARTITION (dt='${DT}') LOCATION '${HDFS_STAGE}';"

# G4 对账
HIVE_CNT=$(cnt "SELECT COUNT(*) FROM ods.${TABLE} WHERE dt='${DT}';")
[ "$HIVE_CNT" = "$LINES" ] || alert "对账失败: 文件 $LINES 行, 表 $HIVE_CNT 行"
DUP=$(cnt "SELECT COUNT(*) FROM (SELECT id FROM ods.${TABLE} WHERE dt='${DT}' GROUP BY id HAVING COUNT(*)>1) t;")
[ "$DUP" = "0" ] || alert "主键重复 $DUP 组，先清洗再入仓"

# G5 转换（OVERWRITE = 幂等）
hsql "SET hive.merge.tezfiles=true;
INSERT OVERWRITE TABLE dwd.${TABLE} PARTITION (dt='${DT}')
SELECT CAST(id AS INT), name FROM ods.${TABLE} WHERE dt='${DT}';"

# G6 终检
DWD_CNT=$(cnt "SELECT COUNT(*) FROM dwd.${TABLE} WHERE dt='${DT}';")
[ "$DWD_CNT" = "$LINES" ] || alert "DWD 对账失败: $LINES vs $DWD_CNT"

log "=== 完成: $LINES 行, md5=${MD5_NOW:0:8} ==="
```

调度（生产用 Airflow/DolphinScheduler；本机用 cron 过渡）：

```cron
30 2 * * * /opt/hadoop-docker/scripts/load_t1.sh >> /var/log/hive_load/t1/cron.log 2>&1
```

> [!important] 就绪标记（_SUCCESS）是生产标配
> 上游把数据**写完之后**才放 `_SUCCESS` 文件，加载脚本见到它才开始——这就是"先校验后可见"的文件版。Flink/上游程序必须遵守这个约定，否则半截数据会被下游消费。

---

## 六、故障矩阵（可能会出的问题 · 全表）

按阶段列出，**每一行都来自真实事故**（★ = 本机 2026-10-06 部署当天真实发生）。

### 6.1 上传/落盘阶段

| 故障 | 现象 | 根因 | 预防 | 应急 |
|---|---|---|---|---|
| 磁盘写满 | HDFS 节点挂、NN 报错 | 没有水位监控+保留策略 | df 告警（85% 预警/90% 熔断加载） | 删过期分区/CSV，`hdfs dfsadmin -safemode` 等退出 |
| 半截文件入库 | 下游 COUNT 波动、解析错位 | 网络中断后直接 put 到正式目录 | `.tmp` → 原子 rename + `_SUCCESS` | 重跑该分区 |
| 并发双跑写同一分区 | 数据重复/文件互踩 | 调度器重复触发 | `flock` 锁 + 幂等 OVERWRITE | 杀一个，重跑分区 |
| 上游没写完就被加载 | 行数对不上 | 无就绪约定 | `_SUCCESS` 标记门禁 | 等上游补标记后重跑 |

### 6.2 数据本身

| 故障 | 现象 | 根因 | 预防 | 应急 |
|---|---|---|---|---|
| 编码乱码 | 中文变 `?`/锟斤拷 | 上游 GBK | 统一 UTF-8，入库前 `file` 检测 | 转码重灌分区 |
| 分隔符在字段内 | 列错位 | CSV 没加引号转义 | 与上游约定 `\001` 分隔符或 RFC4180 引号 | OpenCSVSERDE 或重新导出 |
| 空值语义错乱 | `NULL`/`\N`/空串混乱 | 没定义 NULL 表示 | 约定 `\N`；外表 `serialization.null.format='\\N'` | 清洗 SQL 兜底 |
| schema 变更列错位 | 某天起数据"串列" | 上游加列不通知 | 上游变更必须登记；对账加列数校验 | 按变更日切分区修复 |
| 时区错位 | dt 边界差 8 小时 | 脚本用 UTC 时间 | `export TZ=Asia/Shanghai` + 明确 T-1 定义 | 重跑正确日期分区 |

### 6.3 计算引擎（Tez/YARN）

| 故障 | 现象 | 根因 | 预防 | 应急 |
|---|---|---|---|---|
| Tez AM OOM | 作业重试后失败 | 大表 join/排序内存不足 | YARN 配额内调 `tez.am.resource.memory.mb`；分批 | 缩批次重跑 |
| 数据倾斜 | 个别 reducer 99% 卡死 | key 分布不均 | 大 key 预检查（`GROUP BY` 取 topN 看 分布） | 加盐/两阶段聚合 |
| 小文件爆炸 | 查询变慢、metastore 内存涨 | 高频小批量 INSERT | `hive.merge.tezfiles=true`；上游按天合文件 | 定期 INSERT OVERWRITE 重写分区合并 |
| 作业残留垃圾 | HDFS 冒出大量 `.staging`/tmp 目录 | 作业被 kill | 定期清理脚本 | `hdfs dfs -rm -r` 白名单清理 |

### 6.4 元数据/服务层

| 故障 | 现象 | 根因 | 预防 | 应急 |
|---|---|---|---|---|
| ★ Hue `atomic block` 报错 | 所有查询报事务错 | **Hue 自带 sqlite 并发锁库**（error.log 34 次 database is locked） | 元数据库用 MySQL，不用 sqlite | 已迁 MySQL；重跑=重启 Hue |
| ★ `failed to resolve sockaddr for hive:10000` | Hue 连不上 HS2 | 服务名 DNS 不通（容器名与配置名不一致） | 跨容器用网络别名；**在真实调用方验证连通性** | compose `aliases` 修复 |
| ★ NN 格式化失败 `Cannot create directory` | HDFS 起不来 | 挂载卷属主与容器运行用户不一致 | 容器挂载卷属主/权限写进部署清单（chown 1000） | chown 后重启 |
| HS2 会话句柄失效 | `Invalid OperationHandle` | HS2 容器重建后 Hue 持旧句柄 | 发布后让用户刷新页面/重启 Hue | 重启 Hue 清会话 |
| 忘挂分区 | HDFS 有文件查无数据 | 只 put 没 ADD PARTITION | 流程关卡 4 + 对账兜底 | 补 ADD/MSCK |
| 内表误 DROP | 数据真没了 | DROP 内表连数据删 | **ODS 一律外部表**；DROP 前确认 | 从 staging 重放 |

### 6.5 调度层

| 故障 | 现象 | 根因 | 预防 | 应急 |
|---|---|---|---|---|
| 调度器故障重放 | 同一天任务跑两遍 | 调度器 at-least-once 语义 | 幂等设计（本方案的 OVERWRITE+flock 就是为它） | 无需处理，结果一致 |
| 上游延迟 | 加载任务空跑/对账失败 | 上游 SLA 与下游启动时间没对齐 | 就绪标记+延迟重试（3 次×10 分钟）再告警 | 手动触发补跑 |
| 服务重启后任务全挂 | HDFS 处于 safemode | 机器重启 | 重启后先 `hdfs dfsadmin -safemode get` 确认 EXIT 再跑任务 | 等 safemode 退出 |

---

## 七、学习环境 vs 生产环境差距清单

> 本机为学习环境，以下是**上生产前必须补齐**的每一项——也是面试高频考点。

| # | 维度 | 本机现状 | 生产标准 |
|---|---|---|---|
| 1 | HDFS | 单节点，副本=1 | NN HA（2×NN+ZKFC/JN），副本=3，机架感知 |
| 2 | 权限 | `dfs.permissions=false` | 开权限 + Kerberos/Ranger，按库表授权 |
| 3 | YARN 资源 | 8G/4 vcores | 队列划分、公平/容量调度、用户配额 |
| 4 | 调度 | cron | Airflow/DolphinScheduler：DAG 依赖、重试、告警、补数 |
| 5 | 元数据库 | MySQL 单实例 | 主从/MGR + 定期备份 |
| 6 | 监控 | 无 | Prometheus+Grafana（机器上现成！）接 NN/DN/HS2 JMX：容量、文件数、HS2 活跃会话、作业失败率 |
| 7 | 数据质量 | 脚本内对账 | 质量平台（规则库、基线比对、阻断下发） |
| 8 | 压缩/格式 | ORC+Snappy | 同左，另评估 Parquet/合并层 Hudi-Iceberg（免手工 ADD PARTITION） |
| 9 | 密码管理 | 明文在 compose/脚本 | 配置中心/JCEKS vault |
| 10 | 多环境 | 一套 | dev/test/prod 三套，配置隔离 |

---

## 八、上线检查清单（Checklist）

- [ ] 表已登记：负责人、SLA、保留期、上游联系人
- [ ] ODS 为外部表，LOCATION 规范；DWD 为 ORC 内表
- [ ] 加载脚本带 flock 锁、日志、TMP+rename、`_SUCCESS` 门禁
- [ ] 对账 SQL（行数/主键/空值率）全部内置在脚本中，失败即告警退出
- [ ] 重跑演练过：连跑 2 次结果一致（幂等验证）
- [ ] 故障演练过：源文件缺失/行数不符时，脚本正确 alert 退出
- [ ] 保留策略配置：CSV 导出 7 天、staging 90 天、DWD 永久（按需）
- [ ] 磁盘水位告警接入（85% 预警 / 90% 熔断）

---

## 九、速查（高频命令）

```sql
SHOW PARTITIONS ods.t1;                                   -- 分区列表
ALTER TABLE ods.t1 ADD IF NOT EXISTS PARTITION (dt='2026-10-06') LOCATION '...';
MSCK REPAIR TABLE ods.t1;                                 -- 批量修复（分区多时慢，慎用）
INSERT OVERWRITE TABLE dwd.t1 PARTITION (dt='2026-10-06') SELECT ...;  -- 幂等重跑
ALTER TABLE dwd.t1 DROP IF EXISTS PARTITION (dt='2026-10-06');          -- 删分区重灌
SET hive.mapred.mode=strict;                              -- 强制分区谓词（防全表扫）
SET hive.merge.tezfiles=true;                             -- 合并小文件
```

```bash
hdfs dfs -mkdir -p /data/staging/t1/dt=2026-10-06 && hdfs dfs -put -f x.csv $_/   # 上传
hdfs dfs -count /data/staging/t1/dt=2026-10-06                                    # 文件数/大小
hdfs dfsadmin -report | grep -E "Live|Capacity"                                   # 集群健康
hdfs dfsadmin -safemode get                                                       # 重启后必查
```
