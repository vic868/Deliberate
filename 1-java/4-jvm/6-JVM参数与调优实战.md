---
title: JVM 参数与调优实战
tags: [JVM, 调优, 参数, 运维]
status: 进行中
created: 2026-10-09
---

# 🎛️ 六、JVM 参数与调优实战

> 本篇回答：JVM 参数怎么配、什么场景选哪个收集器、调优应该按什么顺序做、容器里内存怎么算账、以及最容易配错的参数。
> 排查具体故障（CPU 100%、OOM、泄漏）见 [[7-JVM故障排查实战]]；机制原理见 [[1-JVM内存区域与对象布局]]、[[2-GC机制深度]]。
> 关联：[[0-JVM总览]]、[[5-JIT编译与运行时优化]]（Code Cache 相关参数）。

---

## 一、参数速查（按用途分组）

### 1.1 堆与内存

| 参数 | 含义 | 实践建议 |
|---|---|---|
| `-Xms` | 初始堆 | **与 `-Xmx` 设为相同**，避免运行时反复扩缩容 |
| `-Xmx` | 最大堆 | 容器内必须小于 limit，给堆外留空间（见 §4） |
| `-Xmn` | 新生代大小 | G1 下**不要设**（见 §3.2）；Parallel/CMS 场景可设 |
| `-XX:NewRatio` | 老年代/新生代比例 | `-Xmn` 与它二选一，别同时设 |
| `-XX:SurvivorRatio` | Eden 与单个 Survivor 比例（默认 8） | 一般不动 |
| `-XX:MaxTenuringThreshold` | 晋升年龄阈值（默认 15） | 晋升过快时可调大 |
| `-XX:PretenureSizeThreshold` | 大对象直接进老年代的阈值 | 对 G1 无效（G1 用 Humongous Region） |
| `-XX:MetaspaceSize` | 元空间**首次**触发 GC 的阈值 | 建议显式设置，避免启动期频繁 Full GC |
| `-XX:MaxMetaspaceSize` | 元空间上限 | **生产必须设**，否则泄漏会吃光机器内存 |
| `-Xss` | 每线程栈大小 | 递归深/线程多时调整；治不了无限递归 |
| `-XX:MaxDirectMemorySize` | 直接内存上限 | Netty/NIO 场景**必设** |
| `-XX:MaxRAMPercentage` | 按容器内存百分比设堆 | 容器里比写死 `-Xmx` 更可移植（见 §4） |
| `-XX:+UseCompressedOops` | 压缩指针 | 堆 > 32G 时自动失效（见 §3.4） |

### 1.2 GC 与收集器

| 参数 | 含义 |
|---|---|
| `-XX:+UseG1GC` / `+UseParallelGC` / `+UseZGC` / `+UseSerialGC` | 选择收集器 |
| `-XX:MaxGCPauseMillis` | **G1/ZGC 的目标停顿**（软目标；**别设得过小**，否则退化为频繁小回收） |
| `-XX:GCTimeRatio` | Parallel 的吞吐目标（默认 99，即 GC 时间 ≤ 1%） |
| `-XX:ParallelGCThreads` | 并行 GC 线程数 |
| `-XX:ConcGCThreads` | 并发 GC 线程数（G1/CMS） |
| `-XX:InitiatingHeapOccupancyPercent` | G1 触发并发标记的堆占用阈值（默认 45 左右，**大堆常需下调**） |
| `-XX:G1HeapRegionSize` | G1 的 Region 大小（1～32MB，2 的幂） |
| `-XX:G1NewSizePercent` / `G1MaxNewSizePercent` | G1 新生代占比范围（引导而非硬设） |
| `-XX:G1MixedGCLiveThresholdPercent` | 决定哪些老年代 Region 进入 Mixed GC |
| `-XX:+UseStringDeduplication` | G1 的字符串去重（可省内存，有 CPU 代价） |
| `-XX:+ExplicitGCInvokesConcurrent` | 让 `System.gc()` 走并发收集而不是 Full GC |
| `-XX:+DisableExplicitGC` | 完全禁用 `System.gc()`（**慎用**，见 §6） |

### 1.3 诊断与日志（生产强烈建议全开）

```bash
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/data/dump/                     # 要有足够磁盘空间
-XX:ErrorFile=/data/dump/hs_err_%p.log           # JVM 崩溃日志
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=10,filesize=50m   # JDK9+
-XX:+ExitOnOutOfMemoryError                      # OOM 后退出，交给编排系统重启
-XX:+HeapDumpOnOutOfMemoryError -XX:+CrashOnOutOfMemoryError   # 二选一，视重启策略
```

| 观测类参数 | 用途 |
|---|---|
| `-XX:+PrintFlagsFinal` | 打印**最终生效**的参数（排查"我配的到底生效没"） |
| `-XX:+PrintCompilation` | 打印 JIT 编译活动（见 [[5-JIT编译与运行时优化]]） |
| `-XX:+PrintCodeCache` | 退出时打印 Code Cache 使用（打满会导致 JIT 停摆） |
| `-XX:NativeMemoryTracking=summary` + `jcmd <pid> VM.native_memory` | **追踪堆外内存**（排查容器 OOMKilled 的关键） |
| `-Xlog:class+load` | 类加载日志（排查元空间泄漏） |

---

## 二、调优方法论（顺序比参数重要）

> [!important] 调优的正确顺序
> **① 定 SLA → ② 建基线 → ③ 测出瓶颈 → ④ 只改一个维度 → ⑤ 回归验证。**
> **不要凭感觉一次改十个参数** —— 那样即使变好了也不知道是哪个起了作用，下次出问题更没法归因。

| 步骤 | 做什么 | 产出 |
|---|---|---|
| 1. 明确目标 | P99 延迟？吞吐？内存成本？先把 SLA 写下来 | 可验证的目标 |
| 2. 建立基线 | 采集 GC 日志、`jstat`、CPU/内存曲线、火焰图 | 基线数据 |
| 3. 定位瓶颈 | 分清是 **GC / 内存 / CPU / IO / 锁 / 代码** 哪一类 | 瓶颈点 |
| 4. 小步调整 | 一次只动一个维度（堆大小 / 收集器 / 新生代 / 代码） | 可归因的结论 |
| 5. 回归验证 | 与基线对比，确认无副作用（尤其延迟与吞吐的权衡） | 调优报告 |

> [!tip] 先问"是不是真的需要调 JVM"
> 多数"性能问题"的根因在**代码或下游**：一次性全量查询、循环里建大对象、无缓存、下游慢、连接池太小。
> **JVM 参数调优的收益通常是 10%~30%，代码与架构优化的收益可能是数倍。** 先排除代码问题，再动参数。

### 2.1 从现象反推该调什么

| 现象 | 优先怀疑 | 先调这个 | 详见 |
|---|---|---|---|
| Young GC 极频繁 | 新生代偏小 / 分配速率过高 | 调大新生代（或 `MaxRAMPercentage`），优化代码减少临时对象 | [[2-GC机制深度]] |
| 单次 STW 过长 | 堆过大 + 收集器不合适 | 换 G1/ZGC；设 `MaxGCPauseMillis`；减少大对象 | [[2-GC机制深度]] |
| Full GC 频繁 | 晋升过快 / 泄漏 / 大对象 / `System.gc()` | **先判断是否泄漏**，再调晋升与阈值 | [[7-JVM故障排查实战]] |
| GC 后内存不降 | **真泄漏** | 抓 dump 分析，不是调参数 | [[7-JVM故障排查实战]] |
| 老年代增长快 | Survivor 太小 / 晋升阈值太小 | 调 `SurvivorRatio`/`MaxTenuringThreshold` | [[1-JVM内存区域与对象布局]] |
| 元空间持续涨 | 动态生成类 / 类加载器泄漏 | 查生成来源，设 `MaxMetaspaceSize` | [[3-类加载机制与字节码]] |
| 跑一段时间变慢 | Code Cache 满 / 去优化 | `PrintCodeCache`，加大 `ReservedCodeCacheSize` | [[5-JIT编译与运行时优化]] |
| 容器被 OOMKilled | 堆外超限 | **减小 `-Xmx`**，限制元空间与直接内存 | §4 |
| 线程创建失败 | 线程数过多 / `ulimit` | 改线程池（见 [[5-线程池]]），调 `ulimit` | [[7-JVM故障排查实战]] |

---

## 三、收集器选型与关键取舍

### 3.1 选型决策

| 场景 | 推荐 | 理由 |
|---|---|---|
| 在线服务，低延迟优先 | **G1**（JDK9+ 默认） | 可设 `MaxGCPauseMillis`，停顿可控 |
| 超大堆（数十 GB～TB）+ 毫秒级停顿 | **ZGC**（Java 15+ 生产可用） | 停顿与堆大小基本无关 |
| 离线批处理，吞吐优先 | **Parallel Scavenge + Parallel Old** | GC 总开销小，单次停顿可接受 |
| 小内存/客户端 | Serial | 简单、无线程切换开销 |
| 老项目仍在用 CMS | 尽快迁到 **G1** | CMS 已废弃并在较新版本移除 |

> [!warning] 版本提示
> **CMS 已被废弃并在较新 JDK 中移除**，不要再作为新项目的选型；`UseG1GC` 自 JDK9 起是默认值，很多场景**不显式指定也是 G1**。
> 具体版本行为以官方文档为准。

### 3.2 G1 的参数纪律

| 纪律 | 原因 |
|---|---|
| **不要手动设 `-Xmn`** | 会干扰 G1 自适应调整新生代；用 `MaxGCPauseMillis` + `G1NewSizePercent` 引导 |
| `MaxGCPauseMillis` 别设过小（如 20ms） | G1 会为了达标而频繁做小回收，反而降低吞吐 |
| 大堆适当下调 `InitiatingHeapOccupancyPercent` | 让并发标记更早开始，避免"来不及标记"导致 Full GC |
| 关注 **Humongous** 分配 | 大于 Region 一半的对象走 Humongous，频繁分配会触发 Full GC |
| 避免 **疏散失败（Evacuation Failure）** | 说明回收速度跟不上分配，需加大堆或提前触发 |

### 3.3 ZGC 的注意点

| 项 | 说明 |
|---|---|
| 适用 | 堆很大（数十 GB 以上）、要求停顿个位数毫秒 |
| 代价 | 更高内存开销（染色指针/转发表）、CPU 占用；早期版本不支持压缩指针 |
| 参数 | `-XX:+UseZGC`、`-XX:MaxGCPauseMillis`（并发 GC 的目标） |
| 分代 | **分代 ZGC 在 Java 21 引入**，提升了吞吐与内存效率 |

### 3.4 一个常被忽视的取舍：堆不要超过 32G

> [!important] 压缩指针的边界
> 开启压缩指针（`-XX:+UseCompressedOops`，默认开）时，对象引用占 **4 字节**；**堆超过约 32GB 时压缩指针自动失效**，引用变成 8 字节，**同样的对象占用更多内存**，缓存命中率下降，性能可能反而变差。
> **实践**：要么把堆控制在 32G 以内，要么干脆用更大堆并接受非压缩指针（此时通常配 ZGC 等大堆收集器）。**"堆越大越快"是错的。**

---

## 四、容器里的内存账（K8s 必算）

```
容器 memory limit (例如 2Gi)
 ├── JVM 堆 (-Xmx)              例如 1.2Gi
 ├── Metaspace                   例如 256Mi
 ├── 线程栈 (线程数 × -Xss)       例如 200 × 1Mi = 200Mi
 ├── 直接内存 / Netty            例如 128Mi
 ├── Code Cache / 符号表 / JIT   ~100Mi
 └── 其他 native 开销（GC 结构、JNI…）
```

| 做法 | 说明 |
|---|---|
| 显式写 `-Xmx` | 最可控，但迁移容器规格时要记得改 |
| `-XX:MaxRAMPercentage` | 按容器 limit 百分比设堆（如 60~70%），**更可移植** |
| 必须设 `MaxMetaspaceSize` | 否则元空间可能吃掉堆外配额 |
| 设 `MaxDirectMemorySize` | Netty/NIO 场景必做 |
| 控制线程数 | 线程栈累计可能很可观（见 [[5-线程池]]） |
| 开启 NMT 核查 | `-XX:NativeMemoryTracking=summary` + `jcmd <pid> VM.native_memory summary` |

> [!danger] 关键区分：两种"OOM"
> **Java 抛 `OutOfMemoryError`** → 是 JVM 内部（某区域）不够，方向是**调大对应区域或修泄漏**。
> **容器被 OOMKilled（exit 137）** → 是**容器总内存**超了，方向往往是**减小 `-Xmx`**、限制堆外、降低线程数。
> **搞反了会越调越糟。**

---

## 五、两组典型配置画像

### 5.1 在线服务（低延迟优先）

```bash
# 4C8G 容器，目标 P99 < 200ms
-Xms4g -Xmx4g                          # 固定堆，避免抖动
-XX:MaxMetaspaceSize=512m
-XX:MaxDirectMemorySize=256m
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200               # 目标停顿，别设太小
-XX:InitiatingHeapOccupancyPercent=40  # 大堆时适当提前并发标记
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/data/dump/
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=10,filesize=50m
```

### 5.2 离线批处理（吞吐优先）

```bash
# 16C64G 机器
-Xms16g -Xmx16g
-XX:+UseParallelGC
-XX:ParallelGCThreads=8
-XX:MaxTenuringThreshold=15
-XX:+UseCompressedOops
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags
```

### 5.3 超大堆 + 极低延迟

```bash
-Xms32g -Xmx32g
-XX:+UseZGC
-XX:MaxGCPauseMillis=10
# 注意：32G 边界附近要确认压缩指针状态（-XX:+PrintFlagsFinal | grep CompressedOops）
```

---

## 六、参数陷阱速查

| 陷阱 | 后果 | 正解 |
|---|---|---|
| `-Xms` 与 `-Xmx` 不一致 | 运行时扩缩容抖动、GC 行为变化 | 两者设相同 |
| 不设 `MaxMetaspaceSize` | 元空间泄漏吃光机器内存 | 必须显式设上限 |
| 不设 `MaxDirectMemorySize` | `Direct buffer memory` OOM | NIO/Netty 场景必设 |
| 容器里 `-Xmx` 接近 limit | 被 **OOMKilled**（137） | 预留堆外空间（堆占 50%~75%） |
| G1 下手动设 `-Xmn` | 干扰自适应，停顿与吞吐双输 | 不设，用 `MaxGCPauseMillis` 引导 |
| `MaxGCPauseMillis` 设过小 | 频繁小回收，吞吐下降 | 设为业务可接受的**真实**上限 |
| 堆 > 32G 且未评估压缩指针 | 引用膨胀，性能倒退 | 控制在 32G 内或换 ZGC 并接受 |
| 同时设 `-Xmn` 与 `-XX:NewRatio` | 后者被忽略，配置混乱 | 只留一个 |
| `-XX:+DisableExplicitGC` 随手加 | 直接内存无法靠 `System.gc()` 回收 → 堆外 OOM | 改用 `+ExplicitGCInvokesConcurrent`，或确保显式释放 |
| 不开 `HeapDumpOnOutOfMemoryError` | OOM 现场丢失，只能猜 | 生产默认开启 |
| 不开 GC 日志 | 无法判断 GC 是否是瓶颈 | 开启并归档 |
| 用 `PrintFlagsFinal` 前不确认 | 以为配了其实没生效（被后置参数覆盖） | 启动后用 `-XX:+PrintFlagsFinal` 核对 |

> [!tip] 一个必做的核对动作
> 参数写完（尤其在容器/脚本/环境变量多来源时），启动后执行：
> `java -XX:+PrintFlagsFinal -version | grep -Ei 'MaxHeapSize|MetaspaceSize|UseG1GC|UseZGC|MaxDirectMemorySize'`
> 或对运行中的进程 `jinfo -flags <pid>` —— **确认最终生效值**，而不是你"以为"的值。

---

## 七、动手验证

```bash
# 1) 查看最终生效参数
java -XX:+PrintFlagsFinal -version | grep -Ei 'MaxHeapSize|UseG1GC|MaxMetaspaceSize'
jinfo -flags <pid>

# 2) 看堆与元空间的实际使用
jcmd <pid> GC.heap_info
jstat -gcutil <pid> 1000 10          # 关注 O（老年代）与 FGC

# 3) 核对堆外内存（容器 OOMKilled 必做）
#    需启动时加 -XX:NativeMemoryTracking=summary
jcmd <pid> VM.native_memory summary

# 4) 看 Code Cache 是否打满
jcmd <pid> Compiler.codecache

# 5) 对比不同收集器（压测环境）
#    G1:        -XX:+UseG1GC -XX:MaxGCPauseMillis=200
#    Parallel:  -XX:+UseParallelGC
#    分别记录 P99、吞吐、Full GC 次数
```

**验证清单**：
- [ ] 用 `PrintFlagsFinal` 确认过所有关键参数**真的生效**
- [ ] 知道当前服务堆、元空间、直接内存各占容器多少
- [ ] 能在压测里对比两种收集器的 P99 与 Full GC 次数

---

## 八、本篇必答

> [!question] 面试官可能这样问
> **Q：JVM 参数怎么调？**
> A：先定 SLA → 建基线（GC 日志 + 监控）→ 定位瓶颈（GC/内存/CPU/IO/代码）→ **一次只改一个维度** → 回归验证。经验起点：`-Xms` 与 `-Xmx` 相同；**必须设 `MaxMetaspaceSize`**；在线用 **G1** 并设 `MaxGCPauseMillis`；离线吞吐用 **Parallel**；**务必开 `HeapDumpOnOutOfMemoryError` 与 GC 日志**。容器里保证 `-Xmx` 小于 limit。
>
> **Q：G1 和 Parallel 怎么选？**
> A：**G1 面向低延迟**（可预测停顿、可设目标停顿），适合在线服务；**Parallel 面向吞吐**（GC 总时间占比小，但单次停顿可能较长），适合离线批处理。选型依据是**业务的延迟 SLA**，不是"哪个新"。
>
> **Q：为什么堆不建议超过 32G？**
> A：压缩指针在堆超过约 32GB 时**自动失效**，对象引用从 4 字节变 8 字节，**内存占用上升、缓存命中率下降**，性能可能反而变差。要么控制在 32G 内，要么用更大堆并配 ZGC 这类收集器。
>
> **Q：容器里被 OOMKilled，是加堆还是减堆？**
> A：**通常要减 `-Xmx`**。容器 OOMKilled 说明超的是**容器总内存**，除堆之外还有元空间、线程栈、直接内存、Code Cache 等。此时加堆会让问题更严重。正确做法是核算堆外占用（可用 NMT 追踪），给堆外留足配额。

---
> 回到 → [[0-JVM总览]] ｜ 排障流程 → [[7-JVM故障排查实战]] ｜ GC 机制 → [[2-GC机制深度]]
