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
