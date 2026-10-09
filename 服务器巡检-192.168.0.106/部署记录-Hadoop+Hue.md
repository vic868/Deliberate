# 部署记录：Hadoop 3.3.6 + Hue + Hive（全 Docker）

> 部署日期：2026-10-06 · 机器：192.168.0.106 · 方案：B（全 Docker + 宿主机别名）
> 关联：[[巡检报告]] · 配置备份在本 vault `服务器巡检-192.168.0.106/deploy/hadoop-docker/`

---

## 一、架构

> [!warning] 2026-10-07 变更：hadoop 已改为 `network_mode: host`
> 为了 **DataNode 以宿主机 IP（192.168.0.106）注册**，让 k3s Pod 和外部客户端能直连，hadoop 容器**脱离了 hadoop-net**，改用 host 网络；
> hue / hive-metastore / hive-server 则通过 `extra_hosts: hadoop:192.168.0.106` 回连宿主机。
> **副作用：host 网络的端口不再经 docker-proxy，因此受 UFW 管辖** → 见 [[#八、故障记录：局域网无法访问 Hadoop（2026-10-09）]]。

```text
docker network: hadoop-net (bridge)  +  hadoop 容器走 host 网络
├── hadoop   容器  apache/hadoop:3.3.6（自带 JDK 8，符合 3.3.6 要求）· network_mode: host
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

| 端口 | 服务 | 网络方式（决定是否受 UFW 管） |
|---|---|---|
| 8020 | HDFS RPC（`fs.defaultFS = hdfs://hadoop:8020`） | host 网络 · **受 UFW** |
| 9864 | DataNode HTTP（WebHDFS 重定向目标） | host 网络 · **受 UFW** |
| 9866 | DataNode 数据传输 | host 网络 · **受 UFW** |
| 9867 | DataNode HTTPS | host 网络 · **受 UFW** |
| 9870 | NameNode Web UI | host 网络 · **受 UFW** |
| 8088 | YARN ResourceManager UI | host 网络 · **受 UFW** |
| 19888 | MapReduce JobHistory UI | host 网络 · **受 UFW** |
| 8888 | **Hue Web UI** | docker-proxy · 绕过 UFW |
| 10000 | HiveServer2 thrift（JDBC/beeline 连接入口） | docker-proxy · 绕过 UFW |
| 10002 | HiveServer2 Web UI | docker-proxy · 绕过 UFW |
| 9083 | Hive metastore thrift | docker-proxy · 绕过 UFW |

> [!tip] 一句话判断法
> `ss -lntp` 看到 **`docker-proxy`** → 不受防火墙管；看到 **`java`**（host 网络/裸部署）→ 受 UFW 管，必须 `ufw allow`。

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

- **数据加载方案已整理：[[Hive数据加载方案]]**（staging→ODS 外表→DWD ORC 分层、定时脚本模板、MySQL/Kafka 数据源路径）
- **Kafka→Hive 链路方案已整理：[[Kafka消息入Hive方案]]**（Flink FileSink → staging → 分区注册，含建库建表 SQL 与 Flink 作业全文）
- **Kafka→Hive 实操手册已整理：[[Kafka入Hive实操手册]]**（flink-demo 实战、零改造路径 A / Flink 直写路径 B、逐步检查点、自测清单）
- **部署模式对比已整理：[[Flink-on-K8s-vs-YARN]]**（加 jar 重启痛点的根治方案、12 维度对比、四形态姿势对照）
- **Dinky 修复方案已整理：[[Dinky修复方案]]**（1.14→1.20 变体迁移、三层根因链、已修复验证）
- **端到端串联视图：[[数据流全链路执行手册]]**（Kafka→Flink→HDFS→ODS→DWD 五跳，含现状快照与一键复现命令）
- **标准化与选型：[[Kafka入湖标准流程与方案选型]]**（八步法 + 4 个变量、SeaTunnel/Kafka Connect/Paimon 等成熟方案对比与决策树）
- **微服务学习环境方案：[[Nacos-Seata学习环境建设方案]]**（106 放中间件 + 103 放业务服务的分阶段拓扑、版本矩阵、端口/库规划）
- Kafka → Flink（k3s 里已在跑）→ HDFS 落地的实时管道
- HBase（/opt/hbase 容器）可考虑迁到 HDFS 做底层存储
- Hive 已就绪：Hue 里直接写 HiveSQL； metastore 也可供 Spark/Dinky 等共用

---

## 八、故障记录：局域网无法访问 Hadoop（2026-10-09）

### 现象

Mac（192.168.0.102）访问 NameNode UI / YARN UI 全部不通；但 **Hue（8888）、HiveServer2（10000）、metastore（9083）、MySQL（3306）都正常**。

### 排查链路

| 步骤 | 结果 | 结论 |
|---|---|---|
| ping / SSH 22 | 通 | 机器和网络没问题 |
| 端口扫描 | 8020/9870/8088/19888 全 closed；8888/10000/9083/3306 OPEN | 只挂「一部分」，高度可疑 |
| `docker ps -a` | hadoop 容器 **Up 2 days (healthy)** | 容器根本没挂 |
| `docker compose ps` | hadoop 那行 **PORTS 为空**，hive/hue 都有映射 | 疑点 |
| `docker inspect hadoop` | **`NetworkMode=host`** | 关键 |
| 宿主机 `ss -lntp` | 9870/8020/8088/19888 **全在监听**（java 直接监听，非 docker-proxy） | **Hadoop 完全健康** |
| 宿主机 `curl localhost:9870` | **302** | 服务端没问题 |
| `ufw status verbose` | active · default **deny (incoming)**；8020/9866/9870 只放行 `172.16.0.0/12` + `10.42.0.0/16`；**8088/19888 一条规则都没有** | ✅ **根因** |

### 根因

`hadoop` 服务已改为 **`network_mode: host`**（2026-10-07 20:03 改，目的是让 DataNode 以宿主机 IP 注册，便于 k3s Pod 与外部客户端直连）。
改动之后：

- **bridge + 发布端口**：走 `docker-proxy`，写入 DOCKER 链，**绕过 UFW** → 之前局域网能访问
- **host 网络**：进程直接在宿主机上 `bind`，**逃不过 UFW 的 default deny** → 局域网被拦

> [!important] 通用规律（**值得记牢**）
> **判断一个端口能不能被局域网访问，先看它是 `docker-proxy` 还是 `java` 在监听**：
> - `docker-proxy` → 绕过 UFW，**不受防火墙管辖**
> - 原生进程（host 网络 / 直接部署）→ **受 UFW 管辖**
>
> 这也解释了 [[巡检报告]] 里「Docker 发布端口绕过 UFW 全部暴露在局域网」那条——同一个机制的两面。

### 修复（保留 host 网络，补 UFW 规则）

```bash
ufw allow from 192.168.0.0/24 to any port 8020  proto tcp comment 'HDFS NN RPC from LAN'
ufw allow from 192.168.0.0/24 to any port 9864  proto tcp comment 'HDFS DN http/webhdfs from LAN'
ufw allow from 192.168.0.0/24 to any port 9866  proto tcp comment 'HDFS DN data xfer from LAN'
ufw allow from 192.168.0.0/24 to any port 9867  proto tcp comment 'HDFS DN http from LAN'
ufw allow from 192.168.0.0/24 to any port 9870  proto tcp comment 'NameNode Web UI from LAN'
ufw allow from 192.168.0.0/24 to any port 8088  proto tcp comment 'YARN RM UI from LAN'
ufw allow from 192.168.0.0/24 to any port 19888 proto tcp comment 'JobHistory UI from LAN'
```

> [!warning] 坑中坑：DataNode 的 **9864** 最容易漏
> 只放行 9866/9867 是**不够**的。WebHDFS 的 `OPEN` 会 **307 重定向到 DataNode 的 `9864`**（HTTP 端口），
> 漏掉它就会出现「**UI 能打开、RPC 能连，但一读文件就失败**」这种最难查的半通状态。
> 判断方法：`ss -lntp | grep -E ':(9864|9866|9867)'` 看 DataNode 到底监听哪几个。

### 验证结果

- [x] 9870 / 8088 / 19888 → HTTP 302 ✓
- [x] 8020（HDFS RPC）、9866（DN 数据传输）→ OPEN ✓
- [x] WebHDFS `LISTSTATUS` 返回 JSON ✓
- [x] **端到端读真实文件**：`/data/staging/flink-demo/dt=2026-10-07/1791353363.jsonl`（1.24 MB）→ HTTP 200，耗时 **0.139s** ✓

### 待观察（次要）

`hdfs dfsadmin -report` 显示 **Under replicated blocks: 130**。
配置是 `replication=1` 单副本，正常不该长期存在欠副本，怀疑与「bridge → host」切换后 DataNode 注册 IP 变化、旧副本位置失效有关。
建议找时间 `hdfs fsck / -blocks` 核一次。
