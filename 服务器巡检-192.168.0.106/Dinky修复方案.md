# Dinky 修复方案（1.14 变体 → 1.20 变体迁移）

> 修复日期：2026-10-07 · 目标：让 Dinky 能正常提交 FlinkSQL 到 Flink 1.20 集群
> 故障：Dinky 提交任务报 `NullPointerException: CatalogStoreHolder cannot be null`
> 关联：[[Kafka入Hive实操手册]] · [[Flink-on-K8s-vs-YARN]]

---

## 一、根因链（三层叠加，缺一不炸）

```text
┌─ 第 1 层：构建变体错配
│   Dinky Pod 镜像 = dinky-release-1.14-1.2.4（1.14 变体）
│   集群 = Flink 1.20.0
│   → 1.14 时代的执行器代码构建 CatalogManager 时不设置 CatalogStoreHolder
│   → 而 CatalogStoreHolder 是 Flink 1.19+ 的必填项（FLINK-33295）
│   → NPE: CatalogStoreHolder cannot be null
│
├─ 第 2 层：Deployment 环境变量钉死了版本
│   dinky Deployment 的 env: FLINK_VERSION="1.14"（2026-07-28 创建时配置）
│   → 它覆盖镜像内的 ENV，auto.sh 按 1.14 组 classpath
│   → 即使换成 1.20 变体镜像，不修这个 env 也白搭
│
└─ 第 3 层：1.20 变体缺 MySQL 驱动
    Dinky 元数据库 = mysql 容器里的 dinky 库（71 天来一直在用）
    1.20 变体的 lib/ 没有 mysql-connector-java → Druid init error → 启动失败
```

**教训**：Dinky 按集群 Flink 版本分发不同构建（官方 1.14~1.20 全有），**换 Flink 大版本 = 必须换 Dinky 的对应变体**，且要同步检查 Deployment env、lib 驱动、任务执行模式三件事。

---

## 二、修复执行记录（三次镜像迭代的真实过程）

### v1（失败）：COPY 覆盖不会删除旧目录

```dockerfile
FROM localhost:5000/dinky:1.2.4          # 以旧镜像为底
COPY dinky-release-1.20-1.2.4/ /opt/dinky/   # 叠加 1.20 变体
```
结果：Pod 里 `extends/` 同时有 flink1.14 和 flink1.20——**Docker COPY 是叠加不是替换**，auto.sh 的版本扫描选中了字母序靠前的 1.14。

### v2（失败）：环境变量被 Deployment 覆盖

- 删除了 `extends/flink1.14` ✓（extends 只剩 flink1.20）
- 修掉 Java 8 时代的 `PermSize=512M`（1.20 变体官方 auto.sh 带 Java 8 参数，Java 17 直接拒绝启动 → 改 MetaspaceSize）
- 但 Pod env `FLINK_VERSION` 仍是 **1.14**——Deployment 的 env 覆盖了镜像 ENV（`kubectl get deploy -o yaml` 才能看到）
- 且启动直接 **DruidDataSource init error**：1.20 变体的 lib 没有 mysql-connector（元数据库在 MySQL！）

### v3（成功 ✓）：三处齐修

```dockerfile
FROM eclipse-temurin:17-jre-jammy
ARG FLINK_VERSION=1.20
# ... 同原配方 ...
ENV FLINK_VERSION=1.20          # ★ 硬编码，不依赖 build-arg 传递
# lib/ 补入 mysql-connector-java-8.0.29.jar（从旧 Pod kubectl cp 出来）
```
且 CMD 硬编码：`./bin/auto.sh startOnPending 1.20`。

**最终验证**：Pod `FLINK_VERSION : 1.20` ✓ · `1/1 Ready`（readiness 探针通过）✓ · Web 200 ✓ · 启动日志无 NPE ✓

---

## 三、当前状态与布局

| 项 | 值 |
|---|---|
| 当前镜像 | `localhost:5000/dinky:1.2.4-flink20v3` |
| 内嵌变体 | `extends/flink1.20`（1.14 已移除） |
| 环境变量 | `FLINK_VERSION=1.20`（Deployment env 已改） |
| 元数据库 | mysql 容器 `dinky` 库（**任务配置全部保留**，未受影响） |
| 构建材料 | `/opt/dinky-build/`（1.20 tarball + dinky.db.backup + Dockerfile） |
| 回滚 | 旧镜像 `localhost:5000/dinky:1.2.4` 仍在，`kubectl set image` 即回滚 |

## 四、你在 Dinky UI 里要做的（提交验证）

1. **注册 Flink 集群**（如果之前没注册过）：`注册管理 → 集群管理 → 新建`
   - 类型：Flink Cluster（Standalone Session）
   - JobManager REST 地址：`http://flink-jobmanager.flink.svc.cluster.local:8081`
     （或 NodePort `http://192.168.0.106:30081`）
2. **任务配置**：打开 `flink-demo-di` 任务 → 执行环境/集群选择刚注册的集群
   - **执行模式建议用远程集群**，不要用 Local（Local 是在 Dinky 自己的 JVM 里跑，资源受限且和生产语义不符）
3. **重新提交**：观察日志不再出现 `CatalogStoreHolder` NPE，作业状态 → 运行中
4. Flink UI（http://192.168.0.106:30081）确认作业出现在集群上

## 五、遗留建议（不阻塞，后续优化）

- [ ] **升级 Dinky 1.2.5**：官方已有 release（含 1.20 构建与更多修复），升级时 Dinky 自动迁移元数据（先备份 mysql 的 dinky 库）
- [ ] **mysql 驱动版本**：当前 8.0.29，可升 8.4（与 flink lib 里的 8.4.0 对齐）
- [ ] **镜像瘦身**：构建时清理 extends 里的多版本残留（本次事故的根源之一）
- [ ] **H2 遗留文件**：`/opt/dinky/tmp/dinky.db` 是未使用的默认 H2 文件（元数据实际在 MySQL），可无视

## 六、事故方法论（本次浓缩）

1. **变体/发行版错配**：同一软件按依赖版本分发多个构建时，"能用"和"正确"之间隔着一个 API 断层——报错指向新版本的校验逻辑，根因却是旧版本的调用方
2. **三层配置优先级**：镜像 ENV < Deployment env < 命令行——排查时按这个顺序找"谁覆盖了谁"
3. **改文件 ≠ 改集群**：`kubectl apply` 才推进集群，`rollout restart` 只按旧 spec 重启（本次和上次两次踩中，务必形成肌肉记忆）
4. **发行版缺驱动**：按变体构建的发行版经常缺数据库驱动，迁移时对照旧环境的 lib 清单补齐


---

## 七、第二阶段：extends/flink1.20 空目录（v4 修复）

### 现象

变体迁移后 Dinky 能启动，但**保存任务后关联接口 500**：`NoClassDefFoundError: org/apache/flink/configuration/ConfigOption`、`CollectionUtils`。前端表现为"配置了 FlinkSQL 刷新后就没有了"。

> [!important] 澄清
> **SQL 实际已保存进 MySQL**（`dinky.dinky_task` statement 882 字符、update_time 即保存时刻）。"丢失"是保存成功后关联接口 500 的界面假象。

### 根因

Dinky 服务 classpath（bin/auto.sh 161 行）：

```bash
CLASS_PATH="...:${EXTENDS_HOME}/flink${FLINK_VERSION}/dinky/*:${EXTENDS_HOME}/flink${FLINK_VERSION}/flink/*:..."
```

**官方 tarball 的 `extends/flink1.20/` 里 `dinky/`（3 个 dinky 专属 jar）已带好，但 `flink/` 是空的——设计上要求用户自行放入 Flink 1.20 发行版 jar**。整个 Flink 1.20 类库缺失 → 类初始化连锁失败。

（对照：1.14 能跑是因为当年已放入 14 个 jar）

### 修复（v4）

下载 flink-1.20.0 发行版，精选 12 个 jar 放入 `extends/flink1.20/flink/`：flink-dist / table-api-java-uber / table-planner-loader / table-runtime / cep / connector-files / csv / json + log4j 全套（1.20 无 scala_2.12）。

---

## 八、第三层坑：Remote 模式 `NoClassDefFoundError: ExtendedParser`（v5 修复）

改 1.20 变体 + Remote 模式后，提交报：

```
NoClassDefFoundError: org.apache.flink.table.planner.parse.ExtendedParser
  at org.dinky.operations.CustomNewParserImpl.<init>
```

根因：`ExtendedParser` 在 **Flink 完整版 planner**（`flink-table-planner_2.12-1.20.0.jar`）里，而它**不在 lib/——在发行版的 opt/ 目录**。Flink 官方设计：lib 默认只放 planner-loader，完整 planner 需要用户从 opt/ 按需补入。Dinky 的自定义解析器继承 ExtendedParser，必须要完整版。

修复：

```bash
cd /opt/dinky-build
tar xzf flink-1.20.0-bin.tgz flink-1.20.0/opt/
cp flink-1.20.0/opt/flink-table-planner_2.12-1.20.0.jar dinky-release-1.20-1.2.4/extends/flink1.20/flink/
# 重建镜像 v5 → ctr import → set image（同前流程）
```

> [!note] 若报 `More than one PlannerFactory` 冲突
> 此时 `flink/` 里同时有 planner-loader 和完整 planner。若运行时报工厂冲突，移除 planner-loader 那个 jar 重建即可。

---

## 九、两个阶段的共同方法论

1. **`extends/flink<版本>/` 是"用户自备区"**：官方包只带自家 jar，`flink/`（发行版）和驱动按需自备——迁移时对照旧环境的该目录清单
2. **Flink 的 planner 分两套**：lib 默认是 loader，完整版在 opt/——Dinky 这类要扩展解析器的平台必须补完整版
3. **每补一个 jar 都要重建镜像 + import + 重新提交验证**，一次只改一个变量，报错逐层剥

---

## 十、第四层坑：Dinky 类路径缺 Kafka 连接器（v6 修复，2026-10-07）

### 现象

语法检查（explain）报：

```
Cannot discover a connector using option: 'connector'='kafka'
Available factory identifiers are: blackhole, datagen, dinky-mock, filesystem, print, printnet
```

### 根因

**SQL 编译发生在 Dinky 自己的 JVM 里**（explain/提交前编译），Kafka 连接器必须在 **Dinky 的 classpath** 里。而会话集群 TM 里的 kafka connector（flink-sql-connector-kafka-3.4.0-1.20.jar）是另一套 JVM——**TM 有 ≠ Dinky 有**（与 DN 地址问题同族：每一跳的 classpath/DNS 都要单独验证）。

且对照发现：**1.14 变体的 dinky/ 四件套（catalog×2/client/connector-jdbc）本来也不含 kafka 连接器**——之前从没通过 Dinky 跑过 Kafka 作业，缺口今天才暴露。

### 修复（v6）

```bash
cp /opt/flink/usrlib/flink-sql-connector-kafka-3.4.0-1.20.jar \
   /opt/dinky-build/dinky-release-1.20-1.2.4/extends/flink1.20/dinky/
# 重建镜像 v6 → ctr import → set image（同前流程）
```

### 方法论补充

**"编译在哪、类就在哪"**：Remote 模式下，SQL 的解析/编译在 Dinky JVM 完成，运行在 TM JVM——**两边的 classpath 都要有所需 connector**。以后每换一种数据源（jdbc/hive/pulsar…），都要问一句"Dinky 的 classpath 有了吗"。

