# 部署记录：Hadoop 3.3.6 + Hue + Hive（全 Docker）

> 部署日期：2026-10-06 · 机器：192.168.0.106 · 方案：B（全 Docker + 宿主机别名）
> 关联：[[巡检报告]] · 配置备份在本 vault `服务器巡检-192.168.0.106/deploy/hadoop-docker/`

---

## 一、架构

```text
docker network: hadoop-net (bridge)
├── hadoop   容器  apache/hadoop:3.3.6（自带 JDK 8，符合 3.3.6 要求）
│     NameNode + DataNode + ResourceManager + NodeManager + JobHistoryServer
│     单容器伪分布式，自定义 /opt/startup.sh 拉起全部进程
├── hue      容器  gethue/hue:4.11.0（Web 图形界面）
│     元数据库已迁至 mysql（DESKTOP_DB_CONFIG），sqlite 并发锁库问题根除
│     经 z-hue-overrides.ini 连接 HDFS(WebHDFS)/YARN/JobHistory/HiveServer2
├── hive-metastore 容器  apache/hive:4.0.0  → metastore 库在 mysql 容器里（MySQL 版）
├── hive-server    容器  apache/hive:4.0.0  → HiveServer2，Tez 引擎跑在 YARN 上
└── mysql    容器  （原有 mysql:8.0，docker network connect 接入 hadoop-net）
```

**宿主机端口分配**（9000 被 Portainer 占用，NN RPC 改用 8020）：

| 端口 | 服务 |
|---|---|
| 8020 | HDFS RPC（`fs.defaultFS = hdfs://hadoop:8020`） |
| 9870 | NameNode Web UI |
| 8088 | YARN ResourceManager UI |
| 19888 | MapReduce JobHistory UI |
| 8888 | **Hue Web UI** |
| 10000 | HiveServer2 thrift（JDBC/beeline 连接入口） |
| 10002 | HiveServer2 Web UI |
| 9083 | Hive metastore thrift |

## 二、文件布局（全部在 /opt/hadoop-docker/）

```text
/opt/hadoop-docker/
├── docker-compose.yml          # 两容器 + hadoop-net 网络
├── startup.sh                  # hadoop 容器入口（首次自动格式化 NN）755
├── hadoop/core-site.xml        # fs.defaultFS、hue 代理用户
├── hadoop/hdfs-site.xml        # replication=1、权限关闭、数据目录
├── hadoop/yarn-site.xml        # NM 8G / 4 vcores、日志聚合
├── hadoop/mapred-site.xml      # yarn 框架、HADOOP_MAPRED_HOME
├── hue/hue.ini                 # → 挂载为容器 z-hue-overrides.ini（含 [beeswax] Hive 配置）
├── hive/lib/mysql-connector-j-8.0.33.jar   # metastore 的 MySQL 驱动（阿里云 maven 下载）
└── data/namenode|datanode/     # HDFS 数据（chown 1000:1000 ← 容器内 hadoop 用户）
```

## 三、访问入口与账号

| 入口 | 地址 | 账号 |
|---|---|---|
| **Hue** | http://192.168.0.106:8888 | **admin / Hadoop@2026**（建议登录后改密） |
| NameNode UI | http://192.168.0.106:9870 | 无鉴权 |
| YARN UI | http://192.168.0.106:8088 | 无鉴权 |
| JobHistory | http://192.168.0.106:19888 | 无鉴权 |
| HiveServer2 (JDBC) | `jdbc:hive2://192.168.0.106:10000` | hive / 无密码（auth=NONE） |
| MySQL metastore | mysql 容器 3306 / 库 `metastore` | hive / Hive@2026 |

## 四、命令行用法（宿主机别名，root 和 vic 的 .bashrc 已加）

```bash
hdfs dfs -ls /              # = docker exec hadoop hdfs dfs -ls /
yarn node -list
mapred job -list all
hadoop version
# 别名原理：alias hdfs='docker exec hadoop hdfs'，体验与原生一致
```

常用运维：

```bash
cd /opt/hadoop-docker
docker compose ps                 # 状态
docker compose restart hadoop     # 重启
docker compose logs -f hadoop     # 日志
docker compose down / up -d       # 停/起
```

## 五、部署中踩的坑（重要经验）

> [!warning] 1. scp 上传的文件默认 600 权限
> 容器内非 root 用户读不了 → NameNode 报 `error parsing conf core-site.xml (Permission denied)`、Hue 的 kt_renewer 崩溃循环。**修复：`chmod 644` 配置文件、`755` 脚本。** 注意：脚本没读权限时报 "Permission denied"（解释器要先读文件），和 CRLF 问题症状不同。

> [!warning] 2. 宿主机挂载的数据目录属主
> 镜像以 `hadoop`（uid 1000）运行，root 建的目录它写不了 → NN 格式化报 `Cannot create directory /hadoop/dfs/name/current`。**修复：`chown -R 1000:1000 data/namenode data/datanode`。**

> [!note] 3. Docker Hub 直连被重置
> 配置的镜像源失效后 daemon 回落直连 104.26.x.x 持续 reset。**解法：显式镜像源前缀拉取再 retag**（本机可用：`docker.m.daocloud.io`（hadoop/hive）、`docker.1ms.run`（hue）；daocloud 对 gethue/hue 返回 403）。另：这台机器 SSH 并发连接会被拒，拉大文件时 SSH 还可能超时，用 `nohup` 脱离会话跑长任务。

> [!warning] 4. Hue 连 Hive 报 `failed to resolve sockaddr for hive:10000`
> hue.ini 里写的 `hive_server_host = hive`，但 compose 里容器名是 `hive-server`，网络里根本没有叫 `hive` 的主机名（DNS 解析失败）。**解法：给 hive-server 服务加网络别名**——compose 里 `networks.hadoop-net.aliases: [hive]`。注意：容器内 `localhost` 的 beeline 测试验证不到这个问题，跨容器连接必须用别名/服务名测。

> [!note] 6. 刷新 Hue 报 `Solr server could not be contacted properly: localhost:8983 Connection refused`
> Hue 默认启用的 Search 应用在探测 Solr，而这套栈没部署 Solr。**解法：hue.ini `[desktop]` 段加 `app_blacklist = search,oozie,pig,sqoop`**，把没有服务端支撑的应用禁掉（以后要用了从黑名单移除即可）。

> [!danger] 5. Hue 执行查询报 `An error occurred in the current transaction... atomic block`
> 根因是 Hue 自带的 **sqlite 元数据库在编辑器并发请求下 `database is locked`**（error.log 里 34 次），事务被打断后 Django 的 `validate_no_broken_transaction` 把后续所有查询拦下。**解法：Hue 元数据库迁到 MySQL**——
> ① mysql 建 `hue` 库 + `hue` 用户；② compose 里 hue 服务加环境变量 `DESKTOP_DB_CONFIG=django.db.backends.mysql:hue:hue_test:hue:<密码>:mysql:3306`（冒号分隔 7 字段，这是镜像认的官方机制）；③ `hue dumpdata` 备份 sqlite 数据 → 重建容器（启动自动向 mysql 迁移，84 张表）→ `hue loaddata` 恢复。
> **教训：hue.ini 的 `[database]` 段在这个镜像里不生效（被 DESKTOP_DB_CONFIG 机制架空），而 `[beeswax]` 等应用段却生效——别用 ini 猜，用环境变量。**

## 六、部署验证结果（2026-10-06）

- [x] `docker ps`：hadoop **healthy**、hue Up
- [x] HDFS：`dfsadmin -report` → Live datanodes (1)，容量 233G；put/cat 往返 ✓
- [x] YARN：`yarn node -list` → hadoop RUNNING（8192M / 4 vcores）
- [x] MapReduce：示例作业 `pi 4 200` → **FINISHED SUCCEEDED 100%**（application_1791295297153_0001）
- [x] WebHDFS API 返回 JSON（Hue 文件浏览可用）
- [x] 四个 Web UI（9870/8088/19888/8888）全部 HTTP 302/200
- [x] Hue 超级用户 admin 创建并验证（is_superuser=True）

### Hive 部分（2026-10-06 晚追加）

- [x] apache/hive:4.0.0 镜像（daocloud 拉取）；mysql 容器接入 hadoop-net，metastore 库 + hive 用户已建
- [x] hive-metastore：INIT_SCHEMA 自动初始化成功，9083 就绪
- [x] hive-server：10000 就绪，Tez 引擎跑在 YARN 上
- [x] **beeline 端到端**：建库 testdb → 建表 t1 → INSERT → SELECT 返回 `1, hello-hive` ✓
- [x] hue.ini 增加 `[beeswax]`（hive_server_host=hive:10000）并重启 Hue，beeswax 应用加载 ✓
- [x] 用户已从浏览器实际使用 Hue 的 Hive 元数据浏览页（hue 日志可见 connector_id=hive 请求）

> [!note] Hive 使用提示
> Hive 4.0 的执行引擎是 **Tez**（不再支持 MR），INSERT/CTAS 会起 Tez AM 容器跑在 YARN 上，所以作业记录同时在 YARN 8088 可见。beeline 直连示例：
> `beeline -u "jdbc:hive2://192.168.0.106:10000" -n hive`
> Hue 里：左上 Query Editors → Hive，选 testdb 库即可写查询。

## 七、后续可玩（与现有生态整合）

- Kafka → Flink（k3s 里已在跑）→ HDFS 落地的实时管道
- HBase（/opt/hbase 容器）可考虑迁到 HDFS 做底层存储
- Hive 已就绪：Hue 里直接写 HiveSQL； metastore 也可供 Spark/Dinky 等共用
