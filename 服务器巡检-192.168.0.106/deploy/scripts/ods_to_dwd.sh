#!/bin/bash
# ODS → DWD 增量加工（幂等，可反复执行；只做加工不做消费）
# 用法: ods_to_dwd.sh [dt]      dt 默认今天（Asia/Shanghai）
# 说明: 每次执行都会把指定 dt 分区的 DWD 重算到与 ODS 一致 —— 跑多少次结果都一样
set -uo pipefail
export TZ=Asia/Shanghai
DT=${1:-$(date +%F)}
LOG=/var/log/ods_to_dwd.log
BL() { docker exec -i hive-server beeline -u "jdbc:hive2://localhost:10000" -n hive --silent=true "$@"; }

log() { echo "$(date '+%F %T') [ods_to_dwd/$DT] $*" | tee -a "$LOG"; }

log "开始"

# ① 挂分区（目录已就位时；幂等）
BL -e "ALTER TABLE ods.flink_demo_di ADD IF NOT EXISTS PARTITION (dt='${DT}');" >/dev/null 2>&1

# ② 加工：去重(orderId) + 金额转 DECIMAL(12,2) + 毫秒时间戳解析
#    注意：FROM_UNIXTIME 只收 int/long，必须先 CAST；时区见手册第七章
SQL=$(mktemp)
cat > "$SQL" <<EOF
INSERT OVERWRITE TABLE dwd.flink_demo_di PARTITION (dt='${DT}')
SELECT orderId, userId, product,
       CAST(amount AS DECIMAL(12,2)),
       city, platform,
       FROM_UNIXTIME(CAST(\`timestamp\`/1000 AS BIGINT))
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY orderId ORDER BY \`timestamp\` DESC) AS rn
  FROM ods.flink_demo_di WHERE dt='${DT}'
) t
WHERE rn = 1;
EOF
BL -f /dev/stdin < "$SQL" >/dev/null 2>&1
rm -f "$SQL"

# ③ 对账：DWD 行数必须等于 ODS 唯一订单数
ODS_UNIQ=$(BL --outputformat=tsv2 -e "SELECT COUNT(DISTINCT orderId) FROM ods.flink_demo_di WHERE dt='${DT}';" 2>/dev/null | tail -1)
DWD_CNT=$(BL --outputformat=tsv2 -e "SELECT COUNT(*) FROM dwd.flink_demo_di WHERE dt='${DT}';" 2>/dev/null | tail -1)

log "对账: ODS唯一=${ODS_UNIQ} DWD=${DWD_CNT}"
if [ "$ODS_UNIQ" = "$DWD_CNT" ]; then
  log "✓ 一致，加工完成"
else
  log "✗ 不一致！请检查（可能 ODS 在加工期间有新数据写入，重跑本脚本即可）"
  exit 1
fi

# ④ 顺便清理：删除 ODS 分区目录下失败写入的 .inprogress 孤儿文件（可选）
docker exec hadoop hdfs dfs -rm "$(docker exec hadoop hdfs dfs -ls /data/staging/flink-demo/dt=${DT}/ 2>/dev/null | grep -oE '/data/staging/flink-demo/dt='"${DT}"'/\.[^ ]*inprogress[^ ]*' | head -20)" >/dev/null 2>&1 || true
