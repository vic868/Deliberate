# Flink on K8s vs Flink on YARN（含"加 jar 要重启"的根治方案）

> 编写日期：2026-10-07 · 适用：192.168.0.106（k3s session 集群 flink:1.20.0 + Dinky；hadoop 容器里 YARN 4C/8G 空闲）
> 关联：[[Kafka入Hive实操手册]] · [[部署记录-Hadoop+Hue]]

---

## 一、先回答痛点：加个 jar 必须重启所有作业吗？

**会重启，但锅不在 K8s——在 session 模式本身**。`lib/` 下的 jar 在 JM/TM **进程启动时**加载进父 classloader，进程不重启就吃不到新 jar。这一点 `K8s session` 和 `YARN session` **完全一样**（你昨天给 k3s 加 hadoop jar 要 rollout restart，换成 YARN session 加 jar 同样要重启）。

生产上根治这个问题靠三个方向，按优先级：

| 方向 | 做法 | 效果 |
|---|---|---|
| **① 依赖随作业走** ⭐ | connector 打进**作业自己的 fat jar**（maven-shade），Flink 对 user jar 是 **child-first** 类加载，优先用作业内版本 | 加依赖 = 重打自己的 jar，**完全不碰集群**，这是大厂主流 |
| **② 作业隔离** | 不用共享 session，每个作业独立集群：K8s **Application Mode**（配 Flink K8s Operator）或 YARN Application Mode | 加/改/停任何东西只影响单个作业 |
| **③ 优雅重启** | 必须动 lib 时：先 **savepoint** 停作业 → 重启集群 → 从 savepoint 恢复状态 | 状态不丢，业务秒级中断；Flink K8s Operator 可把这套自动化 |

> [!important] 结论
> 你的 `usrlib → cp → lib` 模式在"偶尔加基础依赖"的场景下已经够省事（改完 `rollout restart` 即可）。**真正要改的习惯是：作业的 connector 依赖打包进作业 jar，lib 里只留 hadoop 这类全集群基础设施**——从此"加 jar"和集群无关。

---

## 二、两种部署形态总览

```text
Flink on YARN                          Flink on K8s
─────────────────────────              ─────────────────────────
YARN RM/NM 管资源（Container）          K8s Scheduler 管资源（Pod）
作业 = 一组 YARN Container              作业 = 一组 Pod（JM Deployment + TM Deployment）
与 HDFS/Hive 同居一个 Hadoop 集群        计算与存储解耦（HDFS 在别处，网络可达即可）
hadoop classpath 天然存在               需要自带 hadoop client（lib/usrlib/镜像）
社区: 存量主流，进入维护态               社区: 官方首推，Operator 生态活跃
```

---

## 三、维度对比（12 项）

| 维度 | Flink on YARN | Flink on K8s |
|---|---|---|
| **部署模式** | session / **application**（per-job 已废弃） | session（Deployment）/ **application**（原生 K8s 或 Operator） |
| **资源单位** | Container（JVM 进程，超内存易被 NM 杀） | Pod（cgroup 硬隔离，OOMKilled 边界清晰） |
| **弹性伸缩** | 手动改 TM 数为主（reactive mode 实验性） | **Operator 自带 Autoscaler**（按反压/延迟自动扩缩 TM） |
| **Hadoop 依赖** | 提交端要配 `HADOOP_CLASSPATH`；作业容器天然有 hadoop 环境（NM 节点） | 必须自带（lib / usrlib / 镜像内），**正是你踩的坑** |
| **与 Hive/Tez 共存** | 同一 YARN，资源互相争抢（你的 YARN 只有 8G，还要跑 Hive） | 隔离干净，互不影响 |
| **存储耦合** | 存算耦合（通常与 HDFS 同部署，享受数据本地性） | 存算分离（网络访问 HDFS/对象存储，损失本地性） |
| **多版本共存** | 同集群多 Flink 版本麻烦（分布式缓存/多 installation） | 不同镜像随便起，天然多版本 |
| **升级/回滚** | 替换 installation + 重启 | 镜像版本 + `rollout undo`，Operator 支持 savepoint 滚动升级 |
| **高可用** | ZK HA（需要 ZK） | K8s 原生 HA（Leader 选举 ConfigMap/Operator） |
| **监控运维** | YARN Web UI + 自建 | K8s 生态全套（Prometheus/Grafana/Loki 你机器上都有） |
| **学习曲线** | 要懂 Hadoop 栈（队列/Container/本地性） | 要懂 K8s 栈（Deployment/Service/PV） |
| **社区趋势** | 存量维护，新特性少 | **官方文档首推**，新特性（Operator/Autoscaler）都在这 |

---

## 四、"加 jar"姿势对照（四种形态）

| 形态 | 加集群级 jar | 加作业级依赖 | 作业影响面 |
|---|---|---|---|
| K8s session（你的现状） | usrlib 放 jar → `rollout restart` → **全集群作业死** | 打进作业 fat jar → 重新提交该作业 | 全部 |
| K8s Application + Operator | 改镜像/挂卷 → Operator 滚动重启单作业集群 | 改镜像 tag → Operator 自动 savepoint 恢复 | **单个作业** |
| YARN session | lib 加 jar → 停 session → `yarn-session.sh` 重启 → 全死 | 同上 fat jar | 全部 |
| YARN Application | 作业容器自带（HADOOP_CLASSPATH），不需集群动 | fat jar | **单个作业** |

> [!note] 记忆锚点
> **session = 合租（动公物全屋遭殃），application = 独居（自己家随便改）**。生产的终极形态是"Application Mode + 依赖进作业镜像"。

---

## 五、结合你的环境：两条路都能走通

### 现状盘点

- k3s：flink:1.20.0 官方镜像 session 集群（usrlib→cp→lib 模式）+ Dinky(30888)，正在跑你的作业
- hadoop 容器：YARN RM/NM 活着（4 vcores / 8G，还要分给 Hive Tez）
- `usrlib` 里那个 `flink-shaded-hadoop-2-uber-2.8.3-10.0.jar` 是**双料备件**：k3s 用它连 HDFS，YARN 模式提交端也用它配 `HADOOP_CLASSPATH`

### 路线 1：继续 K8s session（现状优化）

1. connector 依赖打进作业 jar（学习期用 Dinky 的依赖配置也行，体会 child-first）
2. lib 只留 hadoop uber jar + kafka connector + mysql connector
3. 加 jar → `rollout restart` → 作业从 savepoint 恢复（学一下 savepoint 命令）

### 实操记录：usrlib 中转法补 hadoop 依赖（2026-10-07 已验证 ✓）

> 背景：K8s 里 `flink:1.20.0` 官方镜像**不带 hadoop 客户端**，filesystem connector 写 HDFS 会报 `ClassNotFoundException: org.apache.hadoop.fs.FileSystem`。补依赖用的就是你 yaml 里的 usrlib 中转法。

**原理**：你的 `flink-deployment.yaml` 把宿主机 `/opt/flink/usrlib` 挂进 Pod（hostPath），且两个 Deployment 的启动 args 都有这行——

```yaml
args: ["cp /opt/flink/usrlib/*.jar /opt/flink/lib/ 2>/dev/null;", "exec /docker-entrypoint.sh ..."]
```

即**容器每次启动时把 usrlib 的所有 jar 拷进 `lib/`**。usrlib=补给站，lib=战场。

| 目录 | 官方语义 | 你的用法 |
|---|---|---|
| `lib/` | 集群级依赖：所有作业父 classpath，JM/TM 全加载 | hadoop 这类基础设施 jar 的最终归宿 |
| `usrlib/` | K8s Application Mode 放"用户作业 jar" | 借道当补给站（cp 进 lib 后生效） |

**操作步骤**：

```bash
# ① jar 放进宿主机 usrlib
mv flink-shaded-hadoop-2-uber-2.8.3-10.0.jar /opt/flink/usrlib/

# ② 确认 JM 和 TM 两段 Deployment 的 args 都有 cp 行
grep -B2 "cp /opt/flink/usrlib" /opt/flink/flink-deployment.yaml

# ③ 修 kubectl：k3s 二进制是多路复用器（按调用名切角色），必须先过 kubectl 子命令
#    错误示范：k3s -n flink rollout restart ...  → flag provided but not defined: -n
ln -sf /home/vic/.local/bin/k3s /usr/local/bin/kubectl      # 裸 kubectl 可用
echo 'alias kubectl="k3s kubectl"' >> /root/.bashrc

# ④ 滚动重启（cp 重新执行；⚠️ session 上所有作业会被杀，之后去 Dinky 重新提交）
kubectl -n flink rollout restart deploy/flink-jobmanager deploy/flink-taskmanager

# ⑤ 验证 jar 已进 lib
kubectl -n flink exec deploy/flink-jobmanager -- ls /opt/flink/lib | grep hadoop

# ⑥ 验证 filesystem 写 HDFS（Dinky 或 sql-client 重跑 INSERT 后）
hdfs dfs -ls /data/staging/flink-demo      # 出现新文件即成功
```

> [!warning] 两个注意点
> ① `cp` 只在**容器启动时**执行一次——往 usrlib 加新 jar 后必须重启 Deployment 才生效，重启会杀 session 上所有作业（先 savepoint）
> ② flink-shaded-hadoop-uber（Hadoop 2.8.3 客户端）连 Hadoop 3.3.6 服务端协议兼容；三方依赖（guava 等）已被 relocate，与 connector 的冲突概率低

### 路线 2：体验 Flink on YARN（你的 YARN 是现成的）

```bash
# 思路：在 hadoop 容器里部署一个 flink 发行版（带 hadoop classpath），以 yarn application 提交
# ① 把 flink 发行版 + usrlib 里的 uber jar 拷进 hadoop 容器
docker cp apache-flink-1.20.tgz hadoop:/opt/
docker cp /opt/flink/usrlib/flink-shaded-hadoop-2-uber-2.8.3-10.0.jar hadoop:/opt/flink/lib/
# ② 提交（HADOOP_CLASSPATH 用容器里现成的 hadoop jar）
docker exec hadoop bash -c "export HADOOP_CLASSPATH=\$(hadoop classpath) && \
  /opt/flink/bin/flink run -t yarn-application ... "
```

> [!warning] 现实约束
> 你的 YARN 总共 4 vcores/8G 且要伺候 Hive Tez——**Flink on YARN 在这台机器上只适合"提交跑通、观察 Container 行为"，跑大作业会和 Hive 打架**。对比学习的重点放在架构差异，不是压测。

---

## 六、决策建议

```text
新平台/云上/微服务团队        → K8s + Flink K8s Operator（Autoscaler/滚动升级是硬价值）
已有 Hadoop 集群存量          → YARN Application Mode（迁移成本低，数据本地性）
单机/学习环境                 → K8s session 或 本地 mini-cluster 都行，别为了模式纠结
需要和 Hive 共用一套 YARN 资源 → 先做资源隔离（队列/配额），否则互相饿死
```

学习路线建议：把现在的 K8s session 玩透（savepoint/恢复/滚动重启）→ 用 YARN 提交一个 application mode 作业感受差异 → 再看 Flink K8s Operator（生产终极形态）。

---

## 七、命令速查

```bash
# K8s session（你的现状）
$K kubectl -n flink rollout restart deploy/flink-jobmanager deploy/flink-taskmanager   # 加 jar 后重启
$K -n flink exec deploy/flink-jobmanager -- flink list                          # 查看作业
$K -n flink exec deploy/flink-jobmanager -- flink savepoint <jobId> [path]      # 保存点

# YARN application mode（在 hadoop 容器内，需 flink 发行版 + HADOOP_CLASSPATH）
export HADOOP_CLASSPATH=$(hadoop classpath)
/opt/flink/bin/flink run -t yarn-application -c com.ruoyi.JobRunner /opt/flink/usrlib/app.jar produce

# savepoint 恢复（两种模式通用概念）
flink run -s <savepointPath> ...
```
