---
title: 06-自动化运维Shell
tags: [面试, 专业技能, Shell, 运维, Linux]
status: 进行中
---

# 🐚 06 · 自动化运维（Shell）

> 返回 [[00-总览与复习优先级]]

> [!quote] 简历原话
> 精通 Shell 脚本编程

> [!tip] 这个模块问得不深
> Java 岗对 Shell 的要求是"**你真的用它干过活**"，不是考你写编译器。
> 准备 **2 个能讲细节的实战脚本** + 几个常见陷阱，就够了。

---

## 一、基础陷阱（最容易被考）

| 问题 | 得分骨架 |
|---|---|
| `$*` 与 `$@` 区别 | 不加引号时一样；**加引号时 `"$@"` 展开成多个独立参数，`"$*"` 合成一个**；传参一律用 `"$@"` |
| `$?` 是什么 | 上一条命令的退出码；**0 成功，非 0 失败**；注意**管道只反映最后一个命令** |
| `set -euo pipefail` | `-e` 出错即退出；`-u` 用未定义变量报错；`-o pipefail` **管道中任一环节失败即失败**（补 `$?` 的坑）；**健壮脚本第一行** |
| 单引号 vs 双引号 | 单引号**完全字面量**；双引号允许变量/命令替换 |
| 反引号 vs `$()` | 功能相同，**`$()` 可嵌套、更可读**，推荐 |
| `[[ ]]` vs `[ ]` | `[[ ]]` 是 bash 内建，支持 `&&`、`||`、正则匹配、**不做单词分割**（更安全）；`[ ]` 是 POSIX |
| `$(...)` 里的变量 | 在**子 shell** 中执行，**改不了父 shell 的变量**（经典坑） |
| `while read` 丢变量 | 管道 `|` 会起子 shell → 用**进程替换** `while read ...; done < <(cmd)` |
| 变量未加引号 | 含空格会分词 → **一律 `"$var"`** |
| `local` 关键字 | 函数内声明局部变量，避免污染全局 |
| 退出码与 `&&` `||` | `cmd1 && cmd2 || cmd3` 的短路逻辑 |

---

## 二、文本处理三剑客

### grep
```bash
grep -rn "ERROR" /var/log/app/           # 递归 + 显示行号
grep -c "ERROR" app.log                  # 计数
grep -v "DEBUG" app.log                  # 反向匹配
grep -E "ERROR|FATAL" app.log            # 扩展正则
grep -oP 'cost=\K[0-9]+' app.log         # 只输出匹配部分（-P 需要 PCRE）
```

### sed
```bash
sed -i 's/old/new/g' file                # 全局替换（-i 原地修改，macOS 要 -i ''）
sed -n '10,20p' file                     # 打印 10-20 行
sed '/^#/d' file                         # 删除注释行
sed -i '/pattern/i\插入行' file          # 匹配行前插入
sed -E 's/([0-9]+)ms/\1 毫秒/' file      # 捕获组
```
> **注意**：macOS 的 `sed -i` 必须跟一个参数（`-i ''`），Linux 不用 —— 跨平台脚本的经典坑。

### awk（**最常被问**）
```bash
awk '{print $1, $3}' file                        # 打印第 1、3 列
awk -F: '{print $1}' /etc/passwd                 # 指定分隔符
awk '$3 > 100 {print $0}' file                   # 条件过滤
awk '{sum += $2} END {print sum}' file           # 求和
awk '{count[$1]++} END {for (k in count) print k, count[k]}' file   # 分组统计
awk 'NR>=10 && NR<=20' file                      # 按行号
awk -v limit=100 '$2 > limit' file               # 传外部变量
```

**awk 内建变量**：`NR`（当前行号）、`NF`（字段数）、`FS`（输入分隔符）、`OFS`（输出分隔符）、`$0`（整行）

### 其他常用
```bash
find /log -name "*.log" -mtime +7 -delete        # 删 7 天前日志
find . -type f -name "*.java" | xargs grep -l "TODO"   # 配合 xargs
sort file | uniq -c | sort -rn | head -10        # TOP 10 统计（经典组合）
cut -d',' -f1,3 data.csv                         # 按列切分
tr 'a-z' 'A-Z' < file                            # 字符替换
wc -l file                                       # 行数
date -d "-1 day" +%Y%m%d                         # 日期计算（Linux）
```

---

## 三、健壮脚本模板（**面试可以主动展示这个**）

```bash
#!/usr/bin/env bash
set -euo pipefail                    # 出错即停、未定义变量报错、管道失败即失败

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/myapp/cleanup.log"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG_FILE"; }

cleanup() {                          # 无论成功失败都执行
    local code=$?
    log "脚本退出，code=$code"
    rm -f "$TMP_FILE" 2>/dev/null || true
    exit $code
}
trap cleanup EXIT                    # 捕获退出
trap 'log "收到 SIGINT，正在退出"; exit 130' INT TERM

usage() { echo "用法: $0 -d <目录> -n <保留天数>"; exit 1; }

# 参数解析
while getopts ":d:n:h" opt; do
    case $opt in
        d) DIR="$OPTARG" ;;
        n) DAYS="$OPTARG" ;;
        h|*) usage ;;
    esac
done
: "${DIR:?必须指定目录}"              # 未设置则报错退出
: "${DAYS:=7}"                       # 默认值 7

log "开始清理 $DIR 下 $DAYS 天前的日志"
find "$DIR" -type f -name "*.log" -mtime "+$DAYS" -print0 |
    while IFS= read -r -d '' f; do
        log "删除 $f"
        rm -f "$f"
    done
log "清理完成"
```

> [!important] 面试时把这段讲出来，直接体现"工程化"
> 关键点：`set -euo pipefail`、`trap` 清理、`readonly`、`getopts`、`${VAR:?}` 校验、
> `-print0` + `read -d ''` 处理**含空格的文件名**、日志带时间戳。

---

## 四、并发与进程管理

```bash
# 方式一：后台任务 + wait
for host in "${HOSTS[@]}"; do
    ssh "$host" "restart.sh" &
done
wait                                  # 等所有后台任务结束

# 方式二：xargs 控制并发数（推荐）
cat hosts.txt | xargs -P 10 -I {} ssh {} "restart.sh"

# 方式三：GNU parallel
parallel -j 10 ssh {} restart.sh ::: $(cat hosts.txt)

# 控制并发（信号量思路）
while read -r job; do
    while [ "$(jobs -rp | wc -l)" -ge 10 ]; do sleep 0.2; done
    process "$job" &
done < jobs.txt
wait
```

**常用进程命令**
```bash
ps -ef | grep java | grep -v grep
nohup ./app.sh > app.log 2>&1 &
kill -15 <pid>      # 优雅停止（SIGTERM）
kill -9 <pid>       # 强杀（SIGKILL，不推荐首选）
```

---

## 五、实战场景（挑 2 个背熟）

### 场景 1：服务健康检查 + 自动重启
```bash
#!/usr/bin/env bash
set -euo pipefail
URL="http://127.0.0.1:8080/actuator/health"
if ! curl -sf --max-time 5 "$URL" > /dev/null; then
    echo "[$(date '+%F %T')] 健康检查失败，重启服务" >> /var/log/watchdog.log
    systemctl restart myapp
    sleep 10
    curl -sf --max-time 5 "$URL" > /dev/null || \
        echo "[$(date '+%F %T')] 重启后仍失败，请人工介入" >> /var/log/watchdog.log
fi
```
> 加分点：**`--max-time` 超时**、`-f` 让 HTTP 非 2xx 也返回失败、重启后**二次校验**、失败告警而不是无限重启。

### 场景 2：日志统计 TOP N（大促复盘常用）
```bash
# 统计访问量最高的 10 个接口
awk '{print $7}' access.log \
  | sed 's/?.*//' \
  | sort | uniq -c | sort -rn | head -10

# 统计 P99 耗时（简化版）
awk '{print $NF}' access.log | sort -n | awk '{a[NR]=$1} END {print a[int(NR*0.99)]}'
```

### 场景 3：数据库定时备份 + 保留 7 天
```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR=/data/backup/mysql
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
mysqldump --single-transaction --routines --triggers mydb \
  | gzip > "$BACKUP_DIR/mydb_$DATE.sql.gz"
find "$BACKUP_DIR" -name "mydb_*.sql.gz" -mtime +7 -delete
```
> 加分点：`--single-transaction`（**不锁表**的一致性备份）、`gzip` 压缩、`-mtime +7` 清理。

---

## 六、可能被追问

| 问题 | 答法 |
|---|---|
| 怎么调试 Shell 脚本？ | `bash -x script.sh` 打印执行轨迹；`set -x` 局部开启；`shellcheck` 静态检查 |
| 脚本里怎么发告警？ | curl 调 webhook（钉钉/企业微信/飞书）、发邮件 `mail`/`sendmail` |
| 定时任务怎么写？ | `crontab -e`；**注意环境变量不同**（PATH 精简，要用绝对路径）、输出重定向、`%` 要转义 |
| Shell 和 Python 怎么选？ | 简单流程编排、文件操作、调命令行 → Shell；复杂逻辑、JSON/HTTP、需要测试 → Python |
| 遇到过什么坑？ | ① macOS/Linux `sed -i` 差异 ② 管道起子 shell 导致变量丢失 ③ 文件名含空格 ④ `crontab` 环境变量 ⑤ 未加 `pipefail` 导致失败被吞 |

---

## 七、⚠️ 翻车点自查

- [ ] `set -euo pipefail` 三个选项分别解决什么问题
- [ ] `$*` 与 `$@` 加引号后的区别
- [ ] 管道为什么会"丢变量"，怎么解决
- [ ] awk 能现场写出**分组统计 + 排序取 TOP N**
- [ ] 能讲一个**完整的实战脚本**（健康检查 / 备份 / 日志清理）
- [ ] 知道 `crontab` 环境变量的坑

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与复习优先级]] · [[05-大数据与流计算]]

#面试 #Shell #Linux #运维 #待补
