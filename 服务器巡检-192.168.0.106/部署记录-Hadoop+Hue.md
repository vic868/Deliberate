# 部署记录：Hadoop 3.3.6 + Hue（全 Docker）

> 部署日期：2026-10-06 · 机器：192.168.0.106 · 方案：B（全 Docker + 宿主机别名）
> 关联：[[巡检报告]] · 配置备份在本 vault `服务器巡检-192.168.0.106/deploy/hadoop-docker/`

---

## 一、架构

```text
docker network: hadoop-net (bridge)
├── hadoop 容器  apache/hadoop:3.3.6（镜像自带 JDK 8，符合 3.3.6 要求）
│     NameNode + DataNode + ResourceManager + NodeManager + JobHistoryServer
│     单容器伪分布式，自定义 /opt/startup.sh 拉起全部进程
└── hue 容器     gethue/hue:4.11.0（Web 图形界面）
      经 z-hue-overrides.ini 连接 HDFS(WebHDFS)/YARN/JobHistory
```

**宿主机端口分配**（9000 被 Portainer 占用，NN RPC 改用 8020）：

| 端口 | 服务 |
|---|---|
| 8020 | HDFS RPC（`fs.defaultFS = hdfs://hadoop:8020`） |
| 9870 | NameNode Web UI |
| 8088 | YARN ResourceManager UI |
| 19888 | MapReduce JobHistory UI |
| 8888 | **Hue Web UI** |

## 二、文件布局（全部在 /opt/hadoop-docker/）

```text
/opt/hadoop-docker/
├── docker-compose.yml          # 两容器 + hadoop-net 网络
├── startup.sh                  # hadoop 容器入口（首次自动格式化 NN）755
├── hadoop/core-site.xml        # fs.defaultFS、hue 代理用户
├── hadoop/hdfs-site.xml        # replication=1、权限关闭、数据目录
├── hadoop/yarn-site.xml        # NM 8G / 4 vcores、日志聚合
├── hadoop/mapred-site.xml      # yarn 框架、HADOOP_MAPRED_HOME
├── hue/hue.ini                 # → 挂载为容器 z-hue-overrides.ini
└── data/namenode|datanode/     # HDFS 数据（chown 1000:1000 ← 容器内 hadoop 用户）
```

## 三、访问入口与账号

| 入口 | 地址 | 账号 |
|---|---|---|
| **Hue** | http://192.168.0.106:8888 | **admin / Hadoop@2026**（建议登录后改密） |
| NameNode UI | http://192.168.0.106:9870 | 无鉴权 |
| YARN UI | http://192.168.0.106:8088 | 无鉴权 |
| JobHistory | http://192.168.0.106:19888 | 无鉴权 |

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
> 配置的镜像源失效后 daemon 回落直连 104.26.x.x 持续 reset。**解法：显式镜像源前缀拉取再 retag**（本机可用：`docker.m.daocloud.io`（hadoop）、`docker.1ms.run`（hue）；daocloud 对 gethue/hue 返回 403）。另：这台机器 SSH 并发连接会被拒，拉大文件时 SSH 还可能超时，用 `nohup` 脱离会话跑长任务。

## 六、部署验证结果（2026-10-06）

- [x] `docker ps`：hadoop **healthy**、hue Up
- [x] HDFS：`dfsadmin -report` → Live datanodes (1)，容量 233G；put/cat 往返 ✓
- [x] YARN：`yarn node -list` → hadoop RUNNING（8192M / 4 vcores）
- [x] MapReduce：示例作业 `pi 4 200` → **FINISHED SUCCEEDED 100%**（application_1791295297153_0001）
- [x] WebHDFS API 返回 JSON（Hue 文件浏览可用）
- [x] 四个 Web UI（9870/8088/19888/8888）全部 HTTP 302/200
- [x] Hue 超级用户 admin 创建并验证（is_superuser=True）

## 七、后续可玩（与现有生态整合）

- Kafka → Flink（k3s 里已在跑）→ HDFS 落地的实时管道
- HBase（/opt/hbase 容器）可考虑迁到 HDFS 做底层存储
- Hue 里装 Hive connector 需要先部署 metastore（可选）
