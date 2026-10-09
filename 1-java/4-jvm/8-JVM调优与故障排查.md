---
title: Java JVM 调优与故障排查
tags: [Java, JVM, 调优, 排查]
status: 进行中
created: 2026-10-09
---

# 🔧 十、JVM 调优与故障排查

> 本篇回答：JVM 参数怎么配、常见 OOM 与 CPU 飙高怎么定位、内存泄漏怎么确认、线上该用哪些命令行与可视化工具、以及一套能照着走完的排查流程。
> 偏**实战操作**；内存区域与 GC 原理见 [[7-JVM内存与GC]]。
> 关联：[[0-Java总览]]、[[5-线程池]]（拒绝与堆积）、[[4-多线程与内存模型]]（死锁）、[[1-集合框架]]（容器导致的内存膨胀）。

---

## 一、常用 JVM 参数速查

### 1.1 堆与栈

| 参数 | 含义 | 建议 |
|---|---|---|
| `-Xms` | 初始堆大小 | **与 `-Xmx` 设为相同值**，避免运行时反复扩缩容 |
| `-Xmx` | 最大堆大小 | 容器内要给容器内存留出堆外空间（见 §1.4） |
| `-Xmn` | 新生代大小 | 或用 `-XX:NewRatio`（老年代/新生代比例）间接设置 |
| `-XX:SurvivorRatio` | Eden 与单个 Survivor 的比例（默认 8） | 一般不动 |
| `-XX:MetaspaceSize` / `-XX:MaxMetaspaceSize` | 元空间初始/上限 | **上线必须设 `MaxMetaspaceSize`**，否则元空间泄漏会吃光机器内存 |
| `-Xss` | 每线程栈大小 | 递归深/线程多时调整；**治不了无限递归** |
| `-XX:MaxDirectMemorySize` | 直接内存上限 | Netty/NIO 场景要设，否则报 `OutOfMemoryError: Direct buffer memory` |

### 1.2 GC 与收集器

| 参数 | 含义 |
|---|---|
| `-XX:+UseG1GC` / `-XX:+UseParallelGC` / `-XX:+UseZGC` | 选择收集器 |
| `-XX:MaxGCPauseMillis` | **G1 的目标停顿时间**（软目标，别设过小） |
| `-XX:InitiatingHeapOccupancyPercent` | G1 触发并发标记的堆占用阈值 |
| `-XX:ParallelGCThreads` | 并行 GC 线程数 |
| `-XX:MaxTenuringThreshold` | 晋升年龄阈值（默认 15） |
| `-XX:PretenureSizeThreshold` | 大对象直接进老年代的阈值（对 G1 无效） |
| `-XX:+DisableExplicitGC` | 禁用 `System.gc()` 触发的 Full GC（**慎用**，有些框架依赖它回收直接内存） |

### 1.3 排查必备参数（**生产强烈建议开**）

```bash
-XX:+HeapDumpOnOutOfMemoryError          # OOM 时自动 dump 堆，救命参数
-XX:HeapDumpPath=/data/dump/             # dump 落盘路径（要有足够空间）
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=10,filesize=50m   # JDK9+
-XX:ErrorFile=/data/dump/hs_err_%p.log   # JVM 崩溃日志
-XX:+ExitOnOutOfMemoryError              # OOM 后直接退出（让编排系统重启，避免僵死）
```

> [!danger] 生产最常见的三个配置疏漏
> ① **没开 `HeapDumpOnOutOfMemoryError`** → OOM 现场丢失，只能靠现象猜；
> ② **没设 `MaxMetaspaceSize`** → 元空间泄漏把宿主机内存吃满，容器被杀但看不到 OOM；
> ③ **容器里 JVM 不感知限制**（老版本 JDK 或未设 `-XX:+UseContainerSupport`）→ 按宿主机内存算堆，被 OOMKilled。
> JDK 10+ 默认支持容器感知，但仍建议**显式写清 `-Xmx`**。

### 1.4 容器里的内存账（K8s 场景必须算）

```
容器 limit (例如 2Gi)
 ├── JVM 堆 (-Xmx)            例如 1.2Gi
 ├── Metaspace                 例如 256Mi
 ├── 线程栈 (线程数 × -Xss)     例如 200 × 1Mi = 200Mi
 ├── 直接内存 / Netty          例如 128Mi
 ├── JIT code cache / 符号表    ~100Mi
 └── 其他 native 开销
```

> [!important] 结论
> **`-Xmx` 必须小于容器 limit**，并给堆外留足空间（经验上堆占 limit 的 **50%~75%** 较稳，具体看线程数与直接内存）。
> 症状识别：**容器被 `OOMKilled`（exit code 137）而不是抛 Java OOM** → 说明是**堆外/native 内存**超了容器限制，要调的是 `-Xmx` 与堆外参数，不是加堆。

---

## 二、OOM 的八种形态

| 错误信息 | 含义 | 常见原因 | 处置方向 |
|---|---|---|---|
| `Java heap space` | **堆**内存不足 | 内存泄漏、大对象、缓存无上限、一次性查全表 | 抓 dump → MAT 分析；查大集合与缓存 |
| `GC overhead limit exceeded` | GC 花在回收上的时间占比过高却回收不到什么 | 堆几乎被存活对象占满（**泄漏的典型信号**） | 同上，重点找泄漏 |
| `Metaspace` | 元空间不足 | **动态生成类**（CGLIB/反射/热部署/脚本引擎）、类加载器泄漏 | 设上限 + 查谁在生成类 |
| `Direct buffer memory` | 直接内存不足 | Netty/NIO 未释放 `ByteBuf`、`-XX:MaxDirectMemorySize` 太小 | 查 Netty 引用计数泄漏 |
| `unable to create new native thread` | 线程数达上限 | 线程池无界、每请求建线程、`ulimit` 限制 | 查线程数来源 + 改线程池 |
| `Requested array size exceeds VM limit` | 数组过大 | 一次分配超大数组 | 改成分批处理 |
| `Compressed class space` | 压缩类空间不足 | 类太多（与元空间相关） | 调 `-XX:CompressedClassSpaceSize` |
| `Out of swap space` / `Native memory` | 本地内存耗尽 | 堆外、JNI、线程栈合计超限 | 算总账，见 §1.4 |

> [!tip] 区分"真泄漏"与"配置不足"的快速判据
> **做了 Full GC 之后，老年代占用仍然居高不下** → 大概率是**真泄漏**；
> 如果 Full GC 后能降下去、但很快又涨回来 → 是**分配速率过高或堆太小**。

---

## 三、命令行工具

### 3.1 基础四件套

| 工具 | 用途 | 常用命令 |
|---|---|---|
| **jps** | 列出 Java 进程 | `jps -lvm`（看 pid、主类、启动参数） |
| **jstat** | **GC 与内存统计**（轻量，可高频采样） | `jstat -gcutil <pid> 1000 10`（每秒一次共 10 次） |
| **jmap** | 堆与对象统计、**生成堆 dump** | `jmap -histo:live <pid> \| head -30`、`jmap -dump:live,format=b,file=/tmp/heap.hprof <pid>` |
| **jstack** | **线程栈**，查死锁/卡顿/CPU 高 | `jstack <pid> > /tmp/stack.txt` |

**`jstat -gcutil` 各列含义**：

| 列 | 含义 | 关注 |
|---|---|---|
| `S0`/`S1` | 两个 Survivor 使用率 | —— |
| `E` | Eden 使用率 | 上涨速率反映**分配速率** |
| `O` | **老年代使用率** | 持续接近 100% → 危险 |
| `M` | 元空间使用率 | 持续上涨 → 类加载泄漏 |
| `YGC`/`YGCT` | Young GC 次数/总耗时 | 频率过高说明新生代偏小 |
| `FGC`/`FGCT` | **Full GC 次数/总耗时** | **核心告警指标** |
| `GCT` | GC 总耗时 | 与运行时长对比算占比 |

### 3.2 排查专用工具

| 工具 | 用途 |
|---|---|
| **jcmd** | JDK7+ 的"瑞士军刀"，多数 jmap/jstack 功能都能做：`jcmd <pid> GC.heap_info`、`jcmd <pid> Thread.print`、`jcmd <pid> VM.native_memory summary`（需开 NMT） |
| **jinfo** | 查看/动态调整部分参数：`jinfo -flags <pid>` |
| **jhat** | 老旧的堆分析工具，**已被 MAT 取代** |
| **MAT (Eclipse Memory Analyzer)** | **堆 dump 分析首选**：Histogram、Dominator Tree、Leak Suspects |
| **VisualVM / JConsole** | 图形化，本地/远程连接，看线程、内存、MBean |
| **Arthas** | **线上诊断神器**（阿里开源）：`dashboard`、`thread -n 3`、`jad`、`watch`、`trace`、`profiler`、`heapdump` |
| **async-profiler** | **火焰图**，定位 CPU 热点与内存分配热点（比 `perf` 更适合 JVM） |
| **GCViewer / GCeasy** | 可视化 GC 日志 |

> [!important] 生产慎用与安全姿势
> - `jmap -dump` 会 **STW**（`live` 更明显），大堆可能停顿数秒甚至分钟级 → **尽量在低峰执行**，或直接依赖 `HeapDumpOnOutOfMemoryError` 的自动 dump。
> - `jmap -histo:live` 会触发一次 Full GC，**不要在高并发下随手执行**。
> - 优先用 **Arthas / async-profiler** 这类低侵入工具先看现象，再决定要不要抓 dump。

---

## 四、三大高频故障的排查流程

### 4.1 CPU 飙高（100%）

```bash
# 1) 找到最耗 CPU 的进程
top

# 2) 找到该进程内最耗 CPU 的线程（-H 显示线程）
top -Hp <pid>

# 3) 把线程 ID 转成十六进制（jstack 里是 hex）
printf '%x\n' <tid>

# 4) 在线程栈里定位这个 nid
jstack <pid> | grep -A 30 'nid=0x<hex>'

# 5) 更高阶：直接看火焰图
#   ./profiler.sh -d 30 -f /tmp/flame.html <pid>     (async-profiler)
#   arthas: thread -n 3                              (看最忙的 3 个线程)
```

| 栈里看到什么 | 说明 | 处置 |
|---|---|---|
| 业务方法在跑大循环/复杂计算 | 算法或数据量问题 | 优化逻辑、加缓存、分页 |
| `GC task thread` / 大量 `GCT` | **GC 导致 CPU 高** | 转 §4.3 内存方向排查 |
| `RUNNABLE` 且卡在某个 `socketRead`/`lock` | 可能是**自旋**或锁竞争 | 看 `jstack` 锁信息 |
| 大量线程处于 `BLOCKED` | 锁竞争严重 | 缩小锁范围/换细粒度锁 |
| 正则表达式相关栈 | **正则回溯爆炸** | 改写正则（避免嵌套量词） |

> [!warning] 一个反直觉的经典案例
> 线程处于 **`RUNNABLE`** 也可能在"**自旋等待**"（如 CAS 失败重试、`while` 忙等），并不代表它在做有效工作。
> 判断依据是**火焰图**里这段栈的 CPU 占比，而不是线程状态。

### 4.2 内存泄漏

```bash
# 1) 观察趋势：老年代是否只涨不降
jstat -gcutil <pid> 5000 20

# 2) 触发一次 Full GC 后再看（若能降下去，倾向"堆太小/分配太快"）
jcmd <pid> GC.run
jstat -gcutil <pid> 1000 5

# 3) 抓堆 dump（低峰执行）
jmap -dump:live,format=b,file=/data/dump/heap.hprof <pid>
#   或 arthas: heapdump /data/dump/heap.hprof

# 4) MAT 分析：先看 Leak Suspects，再看 Dominator Tree 找"支配"大内存的对象，
#    然后沿引用链（Path to GC Roots）找到是谁在持有它
```

| MAT 里的关键视图 | 用途 |
|---|---|
| **Histogram** | 谁的对象最多、占多少字节 |
| **Dominator Tree** | **谁"支配"了内存**（最有效）——找根因从这看 |
| **Leak Suspects** | 自动给出的泄漏嫌疑报告 |
| **Path to GC Roots** | 顺着引用链找持有者（**排除弱引用/软引用**后再看强引用） |
| **Thread Overview** | 线程栈上持有的对象 |

**常见泄漏源清单**：

| 来源 | 机制 |
|---|---|
| **静态集合**（`static Map`） | 生命周期与类相同，只增不减 |
| **ThreadLocal** | key 弱引用回收后 value 滞留（**线程池下必现**）→ 见 [[4-多线程与内存模型]] |
| **自定义缓存无淘汰** | 该用 `Caffeine`/`Guava Cache` 并设容量与 TTL |
| **监听器/回调注册未注销** | 观察者被长期持有 |
| **连接/流未关闭** | 用 `try-with-resources` |
| **内部类持有外部类** | 非静态内部类隐式持有 `Outer.this` |
| **类加载器泄漏** | 热部署/动态代理反复生成类 → 元空间涨 |

### 4.3 GC 问题定位

| 现象 | 可能原因 | 处置 |
|---|---|---|
| **Full GC 频繁** | 堆偏小、晋升过快、**大对象直接进老年代**、内存泄漏、`System.gc()` 被调用 | 先判断是否泄漏（§4.2）；再看晋升速率与阈值 |
| **单次 STW 过长** | 堆过大 + 收集器不合适、`MaxGCPauseMillis` 与堆规模不匹配 | 换 G1/ZGC；控制堆上限；减少大对象 |
| **Young GC 极频繁** | Eden 太小、分配速率过高（如循环里建大对象） | 调大新生代；优化代码减少临时对象 |
| **老年代增长快** | 对象过早晋升（Survivor 太小 / `MaxTenuringThreshold` 太小） | 调 Survivor 比例与晋升阈值 |
| **GC 后内存不降** | 真泄漏 | 走 §4.2 流程 |
| **元空间持续增长** | 动态生成类（CGLIB、Groovy、热部署、反射调用 `Proxy`） | 查生成来源；限制 `MaxMetaspaceSize`；缓存代理类 |

### 4.4 线程与死锁

```bash
# 看是否有死锁（jstack 输出里会直接给出 Found one Java-level deadlock）
jstack <pid> | grep -A 20 "Found one Java-level deadlock"

# Arthas
thread                    # 线程总览（按 CPU 排序）
thread -b                 # 直接找阻塞其他线程的"元凶"
thread -n 5               # 最忙的 5 个线程
```

**线程数异常增长**通常来自：`new Thread` 没复用、线程池无界（`newCachedThreadPool`）、`Executors` 用法不当 → 见 [[5-线程池]]。

---

## 五、调优的基本方法（顺序很重要）

> [!important] 调优的正确顺序
> **① 先确认业务指标（延迟/吞吐 SLA）→ ② 再测量（GC 日志 + 监控 + 火焰图）→ ③ 找瓶颈（CPU/内存/GC/IO/锁）→ ④ 改一处 → ⑤ 再测量验证。**
> **不要凭感觉一次改十个参数**——那样即使变好了也不知道是哪个起的作用。

| 步骤 | 做什么 | 产出 |
|---|---|---|
| 1. 定目标 | 明确 P99 延迟、QPS、可用性目标 | SLA |
| 2. 建基线 | 压测或线上采样，记录 GC 次数/停顿/CPU/内存曲线 | 基线数据 |
| 3. 定位 | GC 日志看频率与停顿；火焰图看 CPU 热点；dump 看内存构成 | 瓶颈点 |
| 4. 小步调整 | 一次只改一个维度（堆大小 / 收集器 / 新生代比例 / 代码） | 可归因的结论 |
| 5. 回归验证 | 与基线对比，确认无副作用 | 调优报告 |

### 5.1 两个典型场景的参数画像

**场景 A：在线服务，低延迟优先**

```bash
-Xms4g -Xmx4g                      # 固定堆，避免抖动
-XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200           # 目标停顿
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/data/dump/
-Xlog:gc*:file=/var/log/gc.log:time,uptime:level,tags:filecount=10,filesize=50m
```

**场景 B：离线批处理，吞吐优先**

```bash
-Xms16g -Xmx16g
-XX:+UseParallelGC                 # 吞吐优先
-XX:ParallelGCThreads=8
-XX:MaxTenuringThreshold=15
-Xlog:gc*:file=/var/log/gc.log:time,uptime:level,tags
```

> [!tip] 关于"要不要设 -Xmn"
> G1 下**不建议手动设 `-Xmn`**（会干扰 G1 的自适应新生代调整），用 `MaxGCPauseMillis` 与 `G1NewSizePercent/G1MaxNewSizePercent` 引导即可。
> Parallel/CMS 场景下显式设新生代更有意义。

### 5.2 代码层面的"调优"往往收益更大

| 手段 | 收益 |
|---|---|
| 减少临时对象（循环内拼接、装箱、日志字符串） | 降低分配速率与 GC 频率 |
| 用基本类型集合库或数组替代 `List<Integer>` | 显著降内存与 GC |
| 缓存热点数据（`Caffeine`，设容量 + TTL） | 减少重复计算与 IO |
| 批量化（批量查库/批量写） | 减少往返与对象数 |
| 避免一次性全量查询 | 防大对象与 OOM |
| 合理设置集合初始容量 | 减少扩容与复制 |

---

## 六、常见坑速查表

| 坑 | 现象 | 正解 |
|---|---|---|
| 容器 OOMKilled（137） | 容器被杀但无 Java OOM | `-Xmx` 太大，堆外没留空间；按 §1.4 算账 |
| 没开 HeapDump | OOM 后无从分析 | 加 `-XX:+HeapDumpOnOutOfMemoryError` |
| 元空间无上限 | 宿主机内存被吃满 | 设 `-XX:MaxMetaspaceSize` |
| `jmap -dump:live` 在高并发执行 | 长时间 STW 影响线上 | 低峰执行或依赖自动 dump |
| 只看 CPU 不看 GC | 误判为"业务代码慢" | 先用 `jstat` 排除 GC 因素 |
| 线程 `RUNNABLE` 就认为在干活 | 漏掉自旋/忙等 | 用火焰图看 CPU 占比 |
| `System.gc()` 被框架调用 | 频繁 Full GC | 定位调用方；必要时 `-XX:+DisableExplicitGC`（注意直接内存回收） |
| 直接内存没设上限 | `Direct buffer memory` OOM | 设 `-XX:MaxDirectMemorySize`，查 Netty `ByteBuf` 泄漏 |
| 动态代理/热部署反复生成类 | 元空间只涨不降 | 缓存代理类；限制上限；查加载器泄漏 |
| 递归太深指望调 `-Xss` | `StackOverflowError` 依旧 | **改成迭代**，`-Xss` 只是权宜 |

---

## 七、动手验证

```bash
# 1) 看当前 JVM 生效参数与收集器
java -XX:+PrintFlagsFinal -version | grep -Ei 'UseG1GC|MaxHeapSize|MetaspaceSize'
jinfo -flags <pid>

# 2) 观察 GC 趋势（每秒一次，共 20 次）
jstat -gcutil <pid> 1000 20

# 3) 触发一次 GC 并对比老年代变化（验证是否泄漏）
jcmd <pid> GC.run && jstat -gcutil <pid> 1000 3

# 4) 看堆内对象排行（会触发 Full GC，低峰执行）
jmap -histo:live <pid> | head -30

# 5) 抓线程栈并找死锁
jstack <pid> | grep -A 20 "Found one Java-level deadlock"

# 6) Arthas 一把梭
#   dashboard          —— 全局概览（内存/GC/线程）
#   thread -n 5        —— 最忙线程
#   thread -b          —— 阻塞元凶
#   heapdump /tmp/h.hprof
#   trace com.x.Service method   —— 方法内部耗时分布
```

**验证清单**：
- [ ] 能说清当前服务用的是哪个收集器、堆多大、新生代多大
- [ ] 能从 `jstat` 输出判断"是否发生泄漏"
- [ ] 能独立完成一次"CPU 100%"定位（`top -Hp` → `printf %x` → `jstack`）
- [ ] 能用 MAT 的 Dominator Tree 找到一个内存占用最大对象的持有链

---

## 八、本篇必答

> [!question] 面试官可能这样问
> **Q：线上 CPU 100% 你怎么排查？**
> A：`top` 找进程 → `top -Hp <pid>` 找最耗 CPU 的线程 → `printf '%x' <tid>` 转十六进制 → `jstack <pid>` 搜 `nid=0x...` 定位栈。**同时用 `jstat -gcutil` 排除 GC 导致的 CPU 高**。更高效的做法是用 **async-profiler 火焰图**或 **Arthas `thread -n`** 直接看热点。定位后按栈的性质处理（死循环、正则回溯、锁自旋、GC）。
>
> **Q：怎么判断是不是内存泄漏？**
> A：① 看趋势：**`jstat` 里老年代（O）只涨不降**；② **手动 Full GC 后仍不降** → 基本确认泄漏（若降下去又快速涨回则是堆小/分配率高）；③ 开 `HeapDumpOnOutOfMemoryError` 或低峰抓 dump，用 **MAT 的 Dominator Tree + Path to GC Roots** 找持有链。常见泄漏源：静态集合、**ThreadLocal**、无淘汰的缓存、未注销的监听器、类加载器泄漏。
>
> **Q：JVM 参数怎么调？**
> A：先定 SLA → 建基线 → 定位瓶颈（GC 日志/火焰图/dump）→ **一次只改一个维度** → 回归验证。经验起点：`-Xms` 与 `-Xmx` 相同、给元空间设上限、在线服务用 **G1** 并设 `MaxGCPauseMillis`、离线吞吐用 **Parallel**、**务必开 OOM 自动 dump 与 GC 日志**。容器里还要保证 **`-Xmx` 小于容器 limit**，给堆外留空间。
>
> **Q：容器里被 OOMKilled 但没看到 Java OOM，为什么？**
> A：说明超的是**容器总内存**而不是 Java 堆——堆外还有元空间、线程栈、直接内存、JIT 代码缓存等。**此时加 `-Xmx` 会更糟**，应该**减小 `-Xmx`**、限制元空间与直接内存、或降低线程数，并核算 §1.4 的总账。

---
> 回到 → [[0-Java总览]] ｜ GC 原理 → [[7-JVM内存与GC]] ｜ 线程问题 → [[5-线程池]]、[[4-多线程与内存模型]]
