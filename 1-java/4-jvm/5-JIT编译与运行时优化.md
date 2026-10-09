---
title: JVM JIT 编译与运行时优化
tags: [JVM, JIT, 性能优化, 面试]
status: 进行中
created: 2026-10-09
---

# ⚙️ 五、JIT 编译与运行时优化

> 本篇回答：Java 为什么"越跑越快"、解释器和 C1/C2 是怎么分工的、"热点"到底怎么判定、为什么方法内联是**所有优化的前提**、逃逸分析到底能不能把对象分配到栈上、`-XX:+PrintCompilation` 的输出每一列是什么意思、JMH 为什么是不可替代的、以及那些"跑一会儿突然变慢"的诡异现象背后的机制。
> 关键词：**分层编译 / 热点探测 / 方法内联 / 逃逸分析 / 标量替换 / 去虚化 / 去优化 / Code Cache / JMH**。
> 边界：字节码与类加载见 [[3-类加载机制与字节码]]；GC 与内存布局见 [[2-GC机制深度]]、[[1-JVM内存区域与对象布局]]；参数怎么选见 [[6-JVM参数与调优实战]]；性能问题怎么排查见 [[7-JVM故障排查实战]]。
> 关联：[[0-JVM总览]]、[[0-Java总览]]、[[4-多线程与内存模型]]（锁语义）、[[9-Java版本特性]]（`invokedynamic` 与字符串拼接）、[[1-集合框架]]（集合操作的可优化点）、[[10-面试高频题]]。

---

## 一、为什么需要 JIT

### 1.1 纯解释执行的问题

解释器的工作方式是：**读一条字节码 → 查表找到对应的机器码片段 → 执行 → 再读下一条**。这个循环本身的开销（分派、查表、维护操作数栈、无法跨指令优化）会让同一个操作的执行成本比编译后的机器码高出**一个数量级甚至更多**。

| 开销来源 | 说明 |
|---|---|
| 指令分派 | 每条字节码都要经过一次间接跳转（switch/查表） |
| 无跨指令优化 | 无法做寄存器分配、常量传播、公共子表达式消除、循环优化 |
| 栈式架构 | 大量 `iload`/`istore` 在操作数栈与局部变量表之间搬运数据，无法直接用寄存器 |
| 类型检查 | 每次操作都要按字节码语义做检查（如 `checkcast`） |

**关键点**：这些开销是**静态**的——不管这段代码要跑一次还是十亿次，解释器每次都付同样的成本。但对"跑十亿次"的代码，我们完全可以把编译成本**摊销**掉。这正是 JIT 的核心思想。

### 1.2 混合模式：启动快 + 执行快

```text
                    ┌──────────────────────────────────────────────┐
                    │   Java 的执行引擎：解释器 + JIT 编译器协作     │
                    └──────────────────────────────────────────────┘

   字节码 ──▶ ┌──────────┐   热点方法    ┌────────┐  更热   ┌────────┐   机器码
              │  解释器  │ ───────────▶ │  C1    │ ──────▶ │  C2    │ ────────▶ CPU
              └──────────┘   计数达标    └────────┘  再达标  └────────┘
                   ▲                                              │
                   │              去优化（假设失效）                │
                   └──────────────────────────────────────────────┘
```

| 模式 | 优点 | 缺点 | 适用 |
|---|---|---|---|
| **纯解释** | 启动立即执行，无编译开销，内存占用小 | 峰值性能差（数倍到十倍以上） | 只跑一两次的代码（启动路径、配置解析） |
| **C1 编译** | 编译快、代码量小、优化保守但稳健 | 峰值性能不如 C2 | 短生命周期、中等热度的方法 |
| **C2 编译** | 优化激进，峰值性能最好 | 编译慢、编译线程消耗 CPU、编译期内存占用高 | 真正的热点（循环体、核心方法） |
| **混合模式（默认）** | 启动快 + 峰值高 | 需要预热；内存与 CPU 有额外开销 | 服务端长生命周期应用 |

**设计哲学**：**把编译成本花在真正值得的地方，并且尽可能晚地做决定。** 这也解释了为什么 Java 长期在"服务端吞吐"上胜过静态编译语言，而在"启动时间"上落后——直到 GraalVM Native Image / AOT 出现才改变这一格局。

> [!note] 默认就是混合模式
> `java -version` 会打印 `Java HotSpot(TM) 64-Bit Server VM (build ...)`；如果打印 `(interpreted mode)` 说明被显式关了 JIT（`-Xint`）。
> - `-Xint`：强制纯解释执行（**排查用**，可以用来证明"某问题是不是 JIT 引起的"）
> - `-Xcomp`：强制编译所有方法（几乎不用，会让启动极慢）
> - `-Xmixed`：默认，混合模式

### 1.3 为什么不用 AOT 完全替代 JIT

**根本原因：Java 的动态性让"编译期"拿不到足够的信息。**

| 动态特性 | 为什么 AOT 吃亏 |
|---|---|
| **反射** | `Class.forName`、`Method.invoke` 的目标在编译期不可知 |
| **动态代理 / CGLIB** | 代理类在运行期生成，AOT 世界里不存在 |
| **多态与类加载** | 运行期可能加载新实现类，改变调用点形态（这正是去优化的来源） |
| **`invokedynamic`** | 调用点本身就是"运行期才绑定"的设计（lambda、字符串拼接） |
| **JIT 的运行期信息** | **类型 Profile、分支频率、实际参数类型**——这些只有跑起来才知道，而它们恰恰是内联与去虚化的依据 |

**这就是 JIT 真正的护城河**：它能看到**这段代码在真实负载下长什么样**，然后专门为这个形态生成代码。静态编译器只能做最保守的假设。

### 1.4 GraalVM Native Image / AOT：对比方向

| 维度 | JIT（HotSpot） | GraalVM Native Image |
|---|---|---|
| 启动时间 | 秒级（依赖预热） | **毫秒级** |
| 内存占用 | 需要 JIT 元数据、Profile、Code Cache | **低很多**（无 JIT、无 Profile） |
| 峰值吞吐 | **通常更高**（运行期 Profile 指导优化） | 可能略低（只能做编译期能确定的优化） |
| 编译前提 | 无（运行期编译） | **闭世界假设（closed-world）**：编译期必须知道所有可达代码 |
| 反射 / 动态代理 | 开箱即用 | **需要提供 reachability metadata 配置**（或 Agent 采集） |
| 动态类加载 | 支持 | **不支持**（无法在运行期 defineClass 新类） |
| 适用场景 | 长驻服务、高吞吐、需要动态性 | Serverless、CLI 工具、短生命周期任务 |

> [!warning] "Native Image 一定更快"是误解
> 它快在**启动**和**内存**，不一定快在**吞吐**。有大量基准显示长驻高吞吐服务上 JIT 版本峰值更高。
> 而且迁移到 Native Image 的主要成本不在性能，而在**动态特性**：反射、动态代理、资源加载、`ServiceLoader`、序列化框架都需要逐一配置，漏一个就是**运行期才暴露的失败**（因为静态编译无法发现）。
> **决策原则**：先问"启动时间和内存是不是真瓶颈"，如果是（Serverless 冷启动、容器密度），才值得付这个迁移成本。

### 1.5 还有个"中间路线"：AOT Cache / CDS

不想承担 Native Image 的代价，又需要改善启动：**类数据共享（CDS）与 AOT 缓存**（JDK 12+ 的默认 CDS、后续版本的 AOT 类加载与链接缓存）。它们把"类加载 → 验证 → 解析"的产物持久化，**不改变 JIT 模型**，因此不牺牲峰值性能，也没有反射配置问题。这是现代 JDK 启动优化的主推方向。详见 [[6-JVM参数与调优实战]]。

---

## 二、执行引擎结构

### 2.1 解释器

HotSpot 的解释器是**模板解释器（Template Interpreter）**：JVM 启动时为每条字节码生成一段机器码模板（汇编片段），执行时直接跳到对应模板。相比早期的"字节码 `switch` 循环"实现，省掉了一次分派查表。

| 组件 | 作用 |
|---|---|
| 字节码模板 | 每条字节码对应的机器码片段，`monitorenter`、`invokevirtual` 等都在这里 |
| 字节码分派表 | 按操作码索引到模板入口 |
| 操作数栈 / 局部变量表 | 解释器的数据区（在栈帧里） |
| **Profile 收集** | 解释执行与 C1 代码都会记录**类型、分支、调用次数**信息，供 C2 使用 |

**一个常被忽略的事实：解释器不只是"慢版本"，它还是 Profile 的采集器。** C2 的激进优化（内联、去虚化）依赖 Profile；没有解释器和 C1 阶段收集的 Profile，C2 就只能盲目保守。

### 2.2 C1 与 C2

| | **C1（Client Compiler）** | **C2（Server Compiler）** |
|---|---|---|
| 别名 | 客户端编译器 | 服务端编译器，早期叫 **Opto** |
| 编译速度 | 快（约 C2 的 3~5 倍） | 慢 |
| 优化强度 | 保守（线性扫描寄存器分配、少量内联） | 激进（图着色寄存器分配、全局值编号、激进内联、逃逸分析、向量化） |
| 代码质量 | 一般 | 高（峰值性能来源） |
| 编译期内存 | 低 | 高（IR 图、Profile、内联预算） |
| 典型编译时间 | 微秒~毫秒级 | 毫秒~数十毫秒（巨型方法可能更久） |
| 是否有逃逸分析 | **没有**（不做） | **有** |

> [!important] 一句话记住分工
> **C1 负责"尽快脱离解释器"，C2 负责"最终跑得快"。** 分层编译就是把这两个目标串成一条流水线，而不是二选一。

### 2.3 分层编译的五个层级

JDK 7 起 **分层编译（Tiered Compilation）默认开启**。它把"编译"拆成 5 个层级：

| 层级 | 执行方式 | 是否收集 Profile | 说明 |
|---|---|---|---|
| **0** | 解释执行 | 收集（轻量） | 所有方法都从这里开始 |
| **1** | C1 编译，**不做 Profiling** | ❌ | 极简方法（如 getter/setter、`equals`）走这条快车道 |
| **2** | C1 编译 + **轻量 Profile**（调用次数、回边计数） | 部分 | 当 C2 编译队列积压时作为过渡 |
| **3** | C1 编译 + **完整 Profile**（类型、分支、方法调用） | ✅ | **最主流的中转站**，为 C2 准备数据 |
| **4** | **C2 编译** | 不再收集 | 最终形态 |

**典型迁移路径**：

```text
   0 ──(调用次数/回边数达标)──▶ 3 ──(Profile 足够 + 热度更高)──▶ 4
                                   │
                                   ├─▶ 2（C2 队列繁忙时的过渡）
                                   └─▶ 1（方法足够简单，不需要 Profile，直接跳过 3）
```

**两个关键推论**：

1. **`0 → 3 → 4` 是最常见路径**。所以一个方法在被 C2 优化之前，至少经历过"解释 + C1 编译"两次形态变化。**这就是"预热"的机制来源。**
2. **简单方法会直接走 1**，这正是"getter 痴迷"不必要的原因：现代 JIT 对简单的 getter 编译极快、内联极好，手写 `public final int getX()` 的收益接近零。

| 相关参数 | 作用 |
|---|---|
| `-XX:-TieredCompilation` | **关闭分层编译**：所有方法直接由 C2 编译（`CompileThreshold` 生效）。启动变慢、峰值相近，长驻服务一般不需要关 |
| `-XX:TieredStopAtLevel=1` | **只用到 C1**：启动最快、内存最省，峰值性能明显下降。适合 CLI、批处理、短生命周期进程 |
| `-XX:TieredStopAtLevel=4` | 一路到 C2（默认行为） |

> [!tip] 实战记忆点
> 客户端/工具类应用（启动 1~2 秒就退出的）设 `-XX:TieredStopAtLevel=1` 往往比调堆参数更有效。
> 反过来，**任何压测或性能对比都必须让程序跑到 level 4 之后再采样**——否则测的是 C1 甚至解释器的性能。

### 2.4 编译线程

JIT 编译发生在**独立的编译线程**里（`C1 CompilerThread*` / `C2 CompilerThread*`），不阻塞应用线程执行（编译器要在安全点读取方法的 Profile 与字节码，但编译本身是并发的）。

```bash
# 看编译线程
jcmd <pid> Thread.print | grep -i compiler
```

```text
"C2 CompilerThread0" #7 daemon prio=9 os_prio=31 cpu=18432.55ms elapsed=302.11s tid=0x...
   at <compiler stub>
"C2 CompilerThread1" #9 daemon prio=9 os_prio=31 cpu=9120.31ms elapsed=302.11s tid=0x...
"CodeCache Sweeper" #6 daemon ...
```

| 观察 | 含义 |
|---|---|
| `cpu=` 很大（占应用总 CPU 比例高） | **编译开销大**：热点方法太多、或方法太大导致编译慢。火焰图里会看到 `C2 CompilerThread` |
| 编译线程数很少 | 编译跟不上，方法堆积在队列里 |
| `CodeCache Sweeper` 活跃 | 代码缓存接近满，正在清扫（可能伴随去优化） |

---

## 三、热点探测

### 3.1 两个计数器

HotSpot 用**基于计数器**的热点探测（不是采样）：

| 计数器 | 埋点位置 | 计什么 | 触发什么 |
|---|---|---|---|
| **方法调用计数器** | 方法入口 | 方法被调用的次数 | 达到阈值 → **标准编译（standard compilation）** |
| **回边计数器** | 字节码的跳转回边（`goto` 往回跳、循环条件判断） | 循环体执行的次数 | 达到阈值 → **OSR 编译（栈上替换）** |

```text
   方法 f() 被调用
        │
        ▼
  ┌──────────────────────┐
  │ invocation_counter++ │──── 达到阈值 ───▶ 提交编译请求（整方法）
  └──────────────────────┘

   循环体第 N 次迭代的 iinc/goto 回边
        │
        ▼
  ┌──────────────────────┐
  │  backedge_counter++  │──── 达到阈值 ───▶ 提交 OSR 编译请求
  └──────────────────────┘
```

**为什么需要两个计数器**：一个"只调用一次但内部跑十亿次循环"的方法（典型如 `main`、批处理入口），调用计数永远达不到阈值，但它绝对值得编译——**回边计数器就是为这种场景准备的**。

### 3.2 `-XX:CompileThreshold`

| 配置 | 默认值 | 说明 |
|---|---|---|
| **关闭分层编译时**（`-XX:-TieredCompilation`） | Server 模式 **10000**（Client 模式 1500） | 唯一的编译阈值，达到就送 C2 |
| **开启分层编译时（默认）** | `CompileThreshold` **不生效**，改用下面一组分层阈值 | —— |

**分层编译下的阈值（JDK 8/17 上的典型默认值）**：

| 参数 | 典型默认值 | 含义 |
|---|---|---|
| `-XX:Tier3InvocationThreshold` | 200 | 调用 200 次 → 进 level 3（C1 + 完整 Profile） |
| `-XX:Tier3BackEdgeThreshold` | 60000 | 回边 6 万次 → 进 level 3 |
| `-XX:Tier3CompileThreshold` | 2000 | "综合热度"达 2000 → level 3 |
| `-XX:Tier3MinInvocationThreshold` | 100 | 进 level 3 的调用次数下限 |
| `-XX:Tier4InvocationThreshold` | 5000 | 调用 5000 次 → 进 level 4（C2） |
| `-XX:Tier4BackEdgeThreshold` | 140000 | 回边 14 万次 → 进 level 4 |
| `-XX:Tier4CompileThreshold` | 15000 | 综合热度 15000 → level 4 |
| `-XX:Tier4MinInvocationThreshold` | 600 | 进 level 4 的调用次数下限 |

> [!note] 不要死记这些数字
> 不同 JDK 版本、不同 CPU 架构上默认值会有差异。**面试要答的是"机制"而不是"数字"**：方法是"调用次数或回边次数达到分层阈值后，从解释器升到 C1，再升到 C2"。
> 如果一定要说数字，就说"服务端默认 `CompileThreshold` 是 1 万次左右（关闭分层时）"，比硬背 `Tier3InvocationThreshold=200` 更安全。

### 3.3 计数器热度衰减

**问题**：如果调用计数只增不减，一个启动时被调用 1 万次、之后再也不用的方法，会在很久以后突然被编译——浪费编译资源。

**解法：热度衰减（Counter Decay）**。JVM 在**安全点**（safepoint）周期性地把计数器**减半**（不是清零，是折半）。折半的周期由 `-XX:CounterHalfLifeTime` 控制（单位秒，默认约 30 秒量级）。

```text
调用计数
  10000 ┤        ╭╮
        │       ╱  ╲
   5000 ┤      ╱    ╲          ← 每过半衰期折半
        │     ╱      ╲
   2500 ┤    ╱        ╲＿＿＿
        │   ╱                ╲＿＿＿
      0 └──┴──────────────────────────────▶ 时间
```

**实战含义**：

- **长期稳定运行的服务**（每天都有流量），热点方法靠不断调用维持热度，衰减不影响它。
- **"高峰期热、低谷期冷"的方法**：低谷期计数被衰减掉，等到下一个高峰期**又要重新预热**。这是"每天早高峰响应变慢"的一个隐藏原因（另一个原因是 GC 与 JIT 无关）。
- `-XX:-UseCounterDecay` 可以关掉衰减，但会让"曾经热过"的方法长期占用 Code Cache，一般**不要关**。

### 3.4 OSR：栈上替换（On-Stack Replacement）

**问题场景**：

```java
public static void main(String[] args) {
    long sum = 0;
    for (int i = 0; i < 1_000_000_000; i++) {   // ★ 这个循环要跑十亿次
        sum += i;
    }
    System.out.println(sum);
}
```

`main` 只会被调用**一次**，调用计数器永远达不到阈值。但循环体要跑十亿次——如果不编译，就是十亿次解释执行。

**解法：OSR**。回边计数器达标后，JVM 为该方法**专门编译一个"从循环入口（或某条回边）进入"的版本**，然后把当前正在解释执行的栈帧**原地替换**成已编译的栈帧，从循环中间继续跑。

```text
   解释执行的栈帧                     编译后的栈帧
   ┌─────────────┐                  ┌─────────────┐
   │ 局部变量表   │  ──── 复制 ───▶  │  寄存器/栈    │
   │ 操作数栈     │                  │  （重建状态）  │
   │ 循环已跑到 i=12000 │ ───────▶  │  从 i=12000 继续 │
   └─────────────┘                  └─────────────┘
                    ↑ 栈帧被"替换"，方法没有重新进入
```

| 特性 | 说明 |
|---|---|
| 触发条件 | 回边计数器达到阈值（方法不必是"热方法"） |
| 编译单元 | 方法的一个**特定入口版本**，不是完整方法 |
| 代价 | OSR 编译被视为**一次性编译**：OSR 版本不会像普通编译那样频繁重编译，且如果 Profile 不足，优化质量可能不如标准编译 |
| 观测 | `-XX:+PrintCompilation` 输出里的 **`%`** 标记 |
| 相关参数 | `-XX:OSRCompileThreshold`（部分版本）、`-XX:-UseOnStackReplacement` 可关闭（不建议） |

> [!important] OSR 的面试价值
> "一个只调用一次的方法，里面有个大循环，会被 JIT 编译吗？"——**会，通过 OSR**。
> 追问"怎么证明"：`-XX:+PrintCompilation` 输出里带 `%` 的那一行就是这个方法被 OSR 编译。
> 再追问"OSR 编译和方法编译有什么区别"：OSR 需要**在编译代码中重建解释器栈帧的状态**（把局部变量表和操作数栈映射到寄存器/内存），并为每个可能的循环入口生成对应的进入点，所以它比普通编译更"专一"，也更容易因为 Profile 不足而保守。

---

## 四、编译线程与 Code Cache

### 4.1 编译线程数与编译队列

| 参数 | 作用 | 默认 |
|---|---|---|
| `-XX:CICompilerCount` | 编译线程总数（C1 + C2 共享） | 由 CPU 核数推导；分层编译下**至少 2**，典型是"核数的对数级别"（如 8 核上常见 3~5） |
| `-XX:+BackgroundCompilation` | 后台编译（默认开），编译不阻塞应用线程 | true |
| `-XX:-BackgroundCompilation` | 同步编译，方法在编译完成前被阻塞（**只用于调试**） | false |

**编译队列积压时会发生什么**：

```text
   方法达到阈值 → 提交编译任务 → 进编译队列
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
              队列空闲，很快编译完成           队列积压 → 方法继续解释执行
                                                       │
                                              分层编译会自动降级策略：
                                              - 优先走 level 2（轻量 Profile）
                                              - 减少 C2 任务，多做 C1
```

**这意味着：编译线程不足时，"热点"会被延迟优化，表现为吞吐上不去、CPU 却不高。** 在容器化环境（CPU limit 很小时）特别容易碰到——JVM 看到的核数是宿主的，编译线程数可能过多，反而与应用线程抢 CPU。

> [!warning] 容器里要注意 `CICompilerCount`
> 容器 CPU limit 为 1 核时，默认的编译线程数可能让 JIT 编译吃掉大量 CPU，导致应用线程饥饿。此时应该显式限制编译线程数，或干脆降低编译投入（`-XX:TieredStopAtLevel=1`）。
> 相关容器感知参数见 [[6-JVM参数与调优实战]]。

### 4.2 Code Cache

**JIT 编译出来的机器码放在哪里？** 不在堆里，也不在元空间——在 **Code Cache**（代码缓存），一块独立的本地内存区域。

| 特性 | 说明 |
|---|---|
| JDK 8 | 单一区域，默认上限 **240 MB**（开启分层编译时；关闭分层时约 48 MB） |
| JDK 9+ | **分段代码缓存（Segmented Code Cache）**：profiled / non-profiled / non-method 三段，分别存放不同层级与用途的代码，减少碎片 |
| 其他内容 | 除 JIT 代码外，还存解释器的字节码模板、`invokevirtual` 的虚方法表桩（vtable stub）、适配器（adapter）等 |
| `-XX:InitialCodeCacheSize` | 初始大小（默认约 2.5 MB） |
| `-XX:ReservedCodeCacheSize` | **上限**，最需要关注的参数 |

**Code Cache 也会被 GC 吗？** 会。HotSpot 有 **Code Cache Sweeper** 线程，会回收"不再使用"的方法代码（被去优化标记为 not entrant 的、长期未执行的）。这样能延缓 Code Cache 填满。

### 4.3 Code Cache 满了会怎样（高频面试题）

```text
CodeCache: size=245760Kb used=245351Kb max_used=245351Kb free=408Kb
 bounds [0x0000000112a00000, 0x0000000121a00000, 0x0000000121a00000]
 total_blobs=8432 nmethods=7901 adapters=444
 compilation: enabled
```

一旦占满：

```text
Java HotSpot(TM) 64-Bit Server VM warning: CodeCache is full.
Compiler has been disabled.
Java HotSpot(TM) 64-Bit Server VM warning: Try increasing the code cache size
using -XX:ReservedCodeCacheSize=
```

**后果链条**：

| 阶段 | 现象 |
|---|---|
| 1. Code Cache 接近满 | Sweeper 频繁清扫，可能触发**去优化**（把代码丢掉腾空间） |
| 2. Code Cache 满 | **JIT 编译器被完全禁用**（`Compiler has been disabled`），此后所有方法**永远停留在解释执行** |
| 3. 结果 | **性能断崖式下跌**（可能掉到原来的几分之一），CPU 可能因为解释执行而**变高** |
| 4. 更糟 | 如果之前的代码被清扫掉，已经到 level 4 的热点方法退回解释器 → 抖动 |
| 5. 迷惑点 | **应用不会崩溃、不会抛异常**，只是"慢慢变慢"。很多人会先去怀疑 GC 或数据库，其实根因在 Code Cache |

> [!danger] 最容易误判的性能问题之一
> 典型特征：**运行一段时间后吞吐持续下降，重启后恢复，一段时间后又下降**；GC 指标正常，线程池正常，DB 正常。
> **验证方式**：
> ```bash
> jcmd <pid> Compiler.codecache          # 看 used / max_used / free
> java -Xlog:codecache=info -jar app.jar # JDK 9+ 日志
> ```
> **修复方式**：调大 `-XX:ReservedCodeCacheSize`（比如 256m/512m），或**减少动态类生成**（CGLIB 代理、脚本引擎、反射 inflate）。
> **JDK 8 上的补充**：还有 `-XX:+UseCodeCacheFlushing`（默认开启）作为兜底，它会丢弃旧的已编译代码来腾空间，代价是**去优化抖动**。较新 JDK 采用分段缓存与不同清扫策略，行为有差异——**以实际版本的日志为准**，不要照搬旧博客。

### 4.4 观测 Code Cache

```bash
# JDK 8
java -XX:+PrintCodeCache -jar app.jar

# JDK 9+（推荐，统一日志框架）
java -Xlog:codecache=info -jar app.jar
java -Xlog:codecache*=debug -jar app.jar          # 含清扫与扩容

# 运行时查看
jcmd <pid> Compiler.codecache
jcmd <pid> Compiler.codelist                      # 列出所有已编译方法（输出很大）
jcmd <pid> Compiler.queue                         # 编译队列积压情况
jcmd <pid> Compiler.CodeHeap_Analytics            # 各段代码缓存使用分析
jcmd <pid> Compiler.perfmap                       # 写入 perf map 文件，供 perf 采样解析符号
```

**`Compiler.perfmap` 是一个被严重低估的命令**：它把 JIT 编译出的方法地址写到 `/tmp/perf-<pid>.map`，让 `perf` 之类的采样工具能把地址翻译成 Java 方法名。**没有它，原生火焰图里全是 `[unknown]` 或纯地址。**

```text
CodeCache: size=245760Kb used=52134Kb max_used=61230Kb free=193625Kb
 bounds [0x0000000112a00000, 0x0000000121a00000, 0x0000000121a00000]
 total_blobs=2312 nmethods=1893 adapters=332
 compilation: enabled
```

| 字段 | 读法 |
|---|---|
| `used` | 当前占用（包括已被标记为不可用、等待清扫的） |
| `max_used` | **历史峰值**——判断"是否曾经接近上限"的关键指标 |
| `free` | 剩余 |
| `nmethods` | 编译后的方法数（不含 adapter） |
| `compilation: enabled` | **如果变成 `disabled`，就是 Code Cache 满了的铁证** |

---

## 五、核心优化手段

### 5.1 方法内联——最重要的优化

**为什么内联排第一**：因为**绝大多数其他优化都以"能看到跨方法的数据流"为前提**。

| 优化 | 为什么必须内联才能做 |
|---|---|
| 常量传播 | 参数是常量，只有内联后才能把"参数 = 常量"这个事实传播到被调方法内部 |
| 逃逸分析 | 对象在被调方法里"创建后立即返回/仅内部使用"，不内联就看不到它的使用范围 |
| 锁消除 | "这段 `synchronized` 只在调用链内部、锁对象不逃逸"——不内联看不出来 |
| 死代码消除 | 被调方法的某个分支在特定调用点永远走不到，不内联就不知道 |
| 去虚化 + 内联的飞轮 | 去虚化让内联成为可能，内联又提供更多类型信息，进一步去虚化 |

**触发条件与限制**：

| 参数 | 典型默认值 | 作用 |
|---|---|---|
| `-XX:MaxInlineSize` | **35 字节** | **非热点方法**的内联字节码上限 |
| `-XX:FreqInlineSize` | **325 字节**（不同平台/版本有差异） | **热点方法**（被频繁调用）的内联字节码上限，明显更宽松 |
| `-XX:MaxTrivialSize` | 6 字节 | 极简方法（`return x`）无条件内联 |
| `-XX:InlineSmallCode` | 1000~2000 字节 | 已编译代码超过此大小则不再内联 |
| `-XX:MaxInlineLevel` | 9 | 内联调用链最大深度 |
| `-XX:MaxRecursiveInlineLevel` | 1 | 递归内联的层数 |
| `-XX:+Inline` / `-XX:-Inline` | 开 | **`-XX:-Inline` 是性能调试的"核武器"**：关掉内联能让性能掉一个数量级，也可以用来证明"某优化确实生效了" |

> [!important] "把大方法拆小反而更快"的机制解释
> 一段 500 字节的方法，作为**热点方法**时，`FreqInlineSize=325` 依然会**拒绝内联**它。而如果把它拆成 3 个 150 字节的小方法，每个都能被内联进调用方——**跨方法优化重新变得可能**，最终性能反而更好。
> 这不是"代码风格建议"，而是**内联预算（inline budget）**的直接后果。反过来说：
> - 方法体过大 → 不被内联 → 调用开销 + 看不到内部信息 → 其他优化全部失效
> - **巨型方法还更容易让 C2 编译变慢**，占用编译线程和 Code Cache
> 结论：**保持方法精悍（几十行以内、字节码几百字节以内）是有真实性能收益的**，但不要为了"拆"而拆——**在压测热点路径上拆才有效**。

**观测内联**：

```bash
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining -jar app.jar
```

输出形态（示意）：

```text
@ 12   com.demo.OrderService::calc (28 bytes)   inline (hot)
  @ 5   com.demo.PriceRule::apply (18 bytes)    inline (hot)
  @ 14  com.demo.TaxRule::apply (412 bytes)     too big
  @ 21  com.demo.FeeRule::apply (22 bytes)      already compiled into a big method
  @ 30  java.lang.String::length (6 bytes)      inline (hot)
  @ 35  com.demo.Discount::compute (30 bytes)   virtual call, no profile data
@ 48   com.demo.Slow::run (1024 bytes)          hot method too big
```

| 输出关键字 | 含义 | 怎么处理 |
|---|---|---|
| `inline (hot)` | ✅ 内联成功 | —— |
| `too big` / `hot method too big` | ❌ 超过 `MaxInlineSize` / `FreqInlineSize` | 拆分方法，或（谨慎）调大 `-XX:FreqInlineSize` |
| `already compiled into a big method` | ❌ 目标方法已经变得太大 | 同上 |
| `virtual call, no profile data` | ❌ 没有类型 Profile，无法去虚化 | 让调用点更"单态"（见 §5.5） |
| `call site not monomorphic` / megamorphic | ❌ 调用点类型太多 | 重构调用点 |
| `recursive` / `recursion too deep` | 递归限制 | 一般无需处理 |
| `not an osr compilation` / `callee is too large` | OSR 相关的拒绝 | 理解即可 |

### 5.2 逃逸分析（Escape Analysis）

**做什么**：C2 在编译时分析一个对象（或它的引用）**是否会"逃出"当前方法或线程**。

| 逃逸状态 | 定义 | 可做的优化 |
|---|---|---|
| **不逃逸（NoEscape）** | 对象只在方法内部使用，不被返回、不被存入堆结构、不被其他线程看到 | **标量替换**、**锁消除** |
| **方法内逃逸（ArgEscape）** | 对象作为参数传给其他方法，但那些方法不会让它逃出去 | 有限优化 |
| **全局逃逸（GlobalEscape）** | 对象被返回、被赋给静态字段、被其他线程持有 | **无法优化**，只能正常堆分配 |

**三个经典应用**：

```text
逃逸分析
   │
   ├──▶ 不逃逸 ──▶ ① 标量替换：把对象拆成字段，字段放寄存器/栈，连对象头都不分配
   │              └▶ ② 锁消除：独占的锁直接删掉 monitorenter/monitorexit
   │
   └──▶ 逃逸   ──▶ 正常堆分配（TLAB）
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `-XX:+DoEscapeAnalysis` | **true**（Server/C2） | 总开关 |
| `-XX:+EliminateAllocations` | true | 标量替换（依赖逃逸分析） |
| `-XX:+EliminateLocks` | true | 锁消除（依赖逃逸分析） |
| `-XX:+EliminateNestedLocks` | true | 嵌套锁消除 |
| `-XX:+PrintEscapeAnalysis` | false | 打印逃逸分析结论（需 `UnlockDiagnosticVMOptions`） |
| `-XX:+PrintEliminateAllocations` | false | 打印被消除的分配（需诊断开关） |

**观测示例**（示意）：

```bash
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintEliminateAllocations -jar app.jar
```

```text
++++ Eliminated: 3 Allocations
```

**必须讲清楚的三个局限（面试加分点）**：

| 局限 | 说明 |
|---|---|
| **只在 C2（level 4）生效** | C1 不做逃逸分析。所以**没有预热到 level 4 的程序，完全享受不到这些优化**——这是"压测必须预热到 C2"的直接原因 |
| **不改变程序语义** | 它只是把"语义等价的分配"从堆搬到寄存器。所以**用逃逸分析解释"对象引用失效/GC 看不到对象"是错的**——语义没变 |
| **HotSpot 并没有真正的"栈上分配"** | 关键细节：HotSpot 的实现方式是**标量替换 + 分配消除**，而不是在栈上开辟一块对象内存。所以"对象分配到栈上"这个说法在 HotSpot 上**不准确**，准确说法是"这个对象根本没有被分配" |
| **分析能力有限** | 复杂控制流、跨方法调用、被 `synchronized` 之外的方式共享、被写入数组/集合 → 直接判定逃逸 |

> [!important] 一个可以直接演示的效果
> ```java
> static long sum() {
>     long total = 0;
>     for (int i = 0; i < 1_000_000; i++) {
>         total += new Point(i, i).norm();   // 每次迭代 new 一个 Point
>     }
>     return total;
> }
> ```
> 在 C2 上（跑够预热次数后），`new Point(...)` 会被**标量替换**掉：`x`、`y` 变成两个局部变量，堆分配次数为 0。
> **验证方式**：`-XX:+PrintEliminateAllocations` 能看到消除记录；或者用 JMH 的 `-prof gc` 看 `gc.alloc.rate.norm` 在预热后是否降为 0。
> **注意**：如果 `Point` 被存进静态集合、被返回、或被另一个线程访问，消除立刻失效。

### 5.3 标量替换（Scalar Replacement）

**"标量"指无法再分解的值**（基本类型、对象引用）；**"聚合量"指对象**。标量替换就是把对象拆成它的字段，让字段以标量形式参与寄存器分配与优化。

```java
// 源码
static int calc() {
    Point p = new Point(3, 4);   // p 不逃逸
    return p.x + p.y;
}
```

```text
// 不开启标量替换（概念上的行为）
new Point(3,4)  →  堆上分配对象（对象头 12/16 字节 + 2 个 int）
p.x             →  getfield
p.y             →  getfield
p 变成垃圾      →  等 GC

// 开启标量替换后
p.x = 3         →  直接常量折叠为 3
p.y = 4         →  直接常量折叠为 4
return 3 + 4    →  常量折叠为 7
// ★ 连 Point 类都不需要实例化，对象头、字段内存、GC 压力全部消失
```

**收益**：

| 收益 | 说明 |
|---|---|
| 消除分配开销 | TLAB 分配、指针碰撞、对象头写入全部省掉 |
| 消除 GC 压力 | 对象不在堆上，Young GC 频率与晋升压力下降 |
| 让字段进入寄存器 | 原本要 `getfield` 的内存访问变成寄存器操作，并可被常量传播/folding |
| 触发更多优化 | 字段变成标量后，死代码消除、公共子表达式消除都能作用其上 |

> [!tip] 为什么这解释了"小对象不一定贵"
> 很多人以为"避免创建小对象"是铁律。实际上**只要对象不逃逸，创建它可能完全不花钱**。
> 所以真正的建议是：
> 1. **不要为了省对象写出难以维护的代码**（比如手写 "out parameter"）——先测量
> 2. 要关注的是**会逃逸的对象**：被放进集合、被返回、被缓存、被多线程共享的
> 3. 在 JMH 里用 `-prof gc` 看 `gc.alloc.rate.norm` 才是**唯一可靠的判断方式**

### 5.4 锁消除与锁粗化

| 优化 | 机制 | 触发条件 |
|---|---|---|
| **锁消除（Lock Elision）** | 逃逸分析发现锁对象**不会被其他线程访问**，直接把 `monitorenter`/`monitorexit`（或 `ACC_SYNCHRONIZED`）删掉 | 锁对象不逃逸 + C2 |
| **锁粗化（Lock Coarsening）** | 相邻的多次加解锁合并成一次，减少加锁开销 | 循环体内反复对同一对象加锁、相邻的连续加锁 |

**锁消除的经典例子**：

```java
public String concat(String a, String b) {
    StringBuffer sb = new StringBuffer();   // StringBuffer 的方法都是 synchronized
    sb.append(a);
    sb.append(b);
    return sb.toString();                   // sb 不逃逸
}
```

`StringBuffer` 的每次 `append` 都有同步语义，但 `sb` 只在方法内存在、不会被其他线程看到。C2 会把这三把锁**全部消除**——所以"`StringBuffer` 比 `StringBuilder` 慢"这个结论**在热点代码里并不总是成立**（但在非热点代码里成立，因为 C1/解释器不消除）。

**锁粗化的例子**：

```java
// 优化前（概念）
for (int i = 0; i < 1000; i++) {
    synchronized (lock) { counter++; }    // 1000 次加锁
}
// 优化后（概念）
synchronized (lock) {
    for (int i = 0; i < 1000; i++) { counter++; }   // 1 次加锁
}
```

> [!warning] 不要靠 JIT 兜底来写错误的并发代码
> 锁消除的**前提是"锁对象不逃逸"**，这是一个编译器推断。如果推断失败（比如你把对象存进了某个静态字段），锁回来，代码依然是正确的——**JIT 优化永远不改变语义**。
> 但反过来说：**不要把"反正 JIT 会优化掉"当作设计依据**。应该显式使用 `StringBuilder`、避免无意义的同步。
> `synchronized` 的**可见性与 happens-before 语义**属于 [[4-多线程与内存模型]]，本篇只讨论"JIT 会怎么处理它"。

### 5.5 去虚化（Devirtualization）与类型 Profile

**问题**：`invokevirtual` / `invokeinterface` 是虚调用——运行时才能确定调用哪个实现。虚调用意味着**无法直接内联**（不知道内联谁），性能损失很大。

**解法：C2 根据运行期收集的类型 Profile 来"猜"目标，猜对了就内联 + 插入类型检查（guard），猜错了就去优化。**

| 调用点形态 | 英文 | Profile 中的类型数 | C2 行为 |
|---|---|---|---|
| **单态** | monomorphic | **1** | 直接内联该实现，并插入 `if (receiver.getClass() != T) deopt` 守卫。**效果接近静态调用** |
| **双态** | bimorphic | **2** | 生成类型判断分支，**两个目标都内联**。性能依然很好 |
| **巨态** | megamorphic | **≥ 3** | **放弃内联**，退回真正的虚调用（查虚方法表 / itable）。这是性能悬崖 |

| 参数 | 默认 | 说明 |
|---|---|---|
| `-XX:TypeProfileWidth` | **2**（部分 JDK 版本为 2） | 每个调用点最多记录多少种接收者类型。**注意它小于 3，所以"第 3 种类型"往往是把调用点推向 megamorphic 的关键** |
| `-XX:+PrintInlining` | —— | 输出里的 `virtual call, no profile data` / `not monomorphic` 就是被拒的信号 |

> [!important] 为什么"接口默认方法 / 实现类众多"会拖性能
> 一个接口有 20 个实现类，只要某个调用点真的会收到超过 2 种类型，它就变成 **megamorphic**：
> - 无法内联 → 内联带来的所有下游优化（常量传播、逃逸分析、锁消除）全部失效
> - 每次调用都要走虚方法表/itable 查找
> - **这是"抽象层次越高越慢"的真实机制**，不是玄学
>
> **常见的 megamorphic 高发场景**：
> | 场景 | 说明 |
> |---|---|
> | 集合里混装多种子类，然后遍历调用同一个虚方法 | `List<Shape>` 里混 `Circle`/`Square`/`Triangle`，循环里调 `area()` |
> | 大量实现类 + 统一处理逻辑 | 插件架构、事件处理器、`Visitor` 模式 |
> | 泛型 + 多实现的框架回调 | `Handler`、`Converter`、`Mapper` |
> | 日志/序列化框架的适配器 | 每种类型一个 adapter，统一入口分派 |
>
> **缓解手段**：① 按类型分组处理（先分组再循环，把调用点变回单态）；② 用 `switch` + `instanceof` 显式分派（现代 JIT 对 `instanceof` 链有优化，且各分支内的调用点变小）；③ 减少无意义的抽象层；④ **先测量**——不要凭直觉重构。

```bash
# 看调用点是不是 megamorphic
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining -jar app.jar 2>&1 | grep -i -E 'megamorphic|not monomorphic|no profile'
```

### 5.6 循环优化

| 优化 | 机制 | 收益 |
|---|---|---|
| **循环展开（Loop Unrolling）** | 把循环体复制 N 份，减少回边判断与跳转次数 | 减少分支开销，给指令级并行更多空间 |
| **循环无关代码外提（LICM）** | 把循环里不变的计算挪到循环外 | 消除重复计算 |
| **循环剥离 / 版本化（Loop Unswitching）** | 把循环内的不变条件判断移到外面，生成两个版本的循环 | 消除每轮的分支 |
| **数组边界检查消除（Range Check Elimination）** | 证明索引不会越界后，删除 `arraylength` 比较 | **对数组密集代码提升很大** |
| **自动向量化（SuperWord / SIMD）** | 把多次标量运算合并成一条 SIMD 指令 | 数值计算场景数倍提升 |
| **循环判定（Loop Predication）** | 把循环内的检查提取成一次前置检查 | 减少每轮检查 |

**关于自动向量化（`-XX:+UseSuperWord`，默认开启）**：

```java
// 这种形态有机会被向量化
for (int i = 0; i < n; i++) {
    c[i] = a[i] + b[i];
}
```

限制很现实：

- 只对**可证明安全**的简单循环生效（无别名问题、无分支、步长为 1）
- 合并成 SIMD 需要循环具备一定的**长度与对齐**信息
- 一旦有方法调用、复杂分支、别名不确定，向量化就放弃

> [!tip] 别指望 JVM 自动向量化
> Java 在数值计算上打不过手写 SIMD 或 native 代码，这是重要原因之一。需要极致 SIMD 时用 `Vector` API（JDK 16+ 孵化、后续版本演进）或 Panama/FFM，而不是指望 C2。**面试时被问到"Java 能不能自动向量化"，答"能，叫 SuperWord，但条件苛刻、收益有限"就足够。**

### 5.7 常量折叠、常量传播、死代码消除

| 优化 | 说明 | 例子 |
|---|---|---|
| **常量折叠（Constant Folding）** | 编译期/运行期把常量运算直接算掉 | `3 + 4` → `7`（javac 就做了）；`x * 2 / 2` → `x`（C2 做） |
| **常量传播（Constant Propagation）** | 把已知的常量值沿数据流传播下去 | 内联后发现参数恒为 `true`，`if (!flag)` 分支消失 |
| **死代码消除（DCE）** | 删除永远不会执行、或结果不会被使用的代码 | **JMH 要防的就是这个** |
| **公共子表达式消除（CSE）** | 相同表达式只算一次 | `a.b().c()` 重复调用且无副作用 → 合并 |
| **无用代码消除** | 局部变量赋值后从未使用 | —— |

**死代码消除为什么对性能测试是灾难**：

```java
// 手写的"天真基准测试"
long start = System.nanoTime();
long sum = 0;
for (int i = 0; i < 1_000_000; i++) {
    sum += i * i;                  // ★ 结果没被使用
}
long cost = System.nanoTime() - start;
System.out.println("cost = " + cost);   // 只打印耗时，不打印 sum
```

JIT 的逻辑链：`sum` 从未被使用 → 整个循环对程序状态无影响 → **整个循环被消除**。测出来"耗时 0.3ms"，实际什么都没算。

**这就是 §5.8 要讲 JMH 的根本原因。**

### 5.8 内置函数（Intrinsics）——顺带一提

JIT 认识一批"特殊方法"，遇到时**直接替换成最优机器指令**，而不是调用方法本身：

| 类别 | 例子 |
|---|---|
| 数组操作 | `System.arraycopy`、`Arrays.copyOf`、`Arrays.equals` |
| 数学 | `Math.sqrt`、`Math.abs`、`Integer.numberOfLeadingZeros`、`Math.fma` |
| 字符串 | `String.indexOf`、`String.equals`、`StringLatin1` 系列 |
| 并发 | `Unsafe.compareAndSwapInt`、`AtomicInteger.compareAndSet`、`Thread.onSpinWait` |
| 位运算 | `Long.rotateLeft`、`Integer.reverseBytes` |
| 编码 | `String.getBytes`、`new String(byte[])` 的编解码路径 |

**这解释了一个反直觉现象**：`System.arraycopy` 的**声明**是 `native`，但在热点路径上它往往是纯粹的汇编内联展开（可能用上 SIMD），比手写 `for` 循环快得多。所以"复制数组用 `System.arraycopy`"是有 JIT 层面依据的（`-XX:-Inline` 下优势会大幅缩小，因为退化成了真正的 native 调用）。

**用 `@IntrinsicCandidate`（JDK 内部注解）标记**：JDK 源码里可以看到这些方法的注解。也可以用 `-XX:+PrintIntrinsics`（需诊断开关，部分版本）观察内联情况。

---

## 六、JIT 带来的"反直觉"现象（面试加分区）

### 6.1 预热（Warm-up）

**同一段代码，在不同时间点执行，性能可能差 5~20 倍。** 原因链条：

```text
t=0        解释执行（慢）        ← 第一次调用
   │
t=几十次   C1 编译（中等）       ← 达到 Tier3 阈值
   │
t=几千次   C2 编译（快）         ← 达到 Tier4 阈值 + Profile 充分
   │
t=上万次   优化充分生效           ← 内联到位、逃逸分析生效、Profile 稳定
   │
（其间）  Profile 变化 → 去优化 → 回到解释器 → 重新预热（抖动）
```

| 阶段 | 现象 | 观测 |
|---|---|---|
| 冷启动 | 吞吐低、延迟毛刺多，编译线程忙 | `-XX:+PrintCompilation` 输出密集 |
| 过渡期 | 性能爬升，可能出现**比冷启动更差的瞬时抖动**（去优化） | 输出里有 `made not entrant` |
| 稳态 | 性能最高且稳定 | 编译输出变稀疏 |

> [!warning] 压测不预热 = 测了个寂寞
> 典型错误：**"我用 `ab` 压了 30 秒 QPS 只有 3000"**，而生产上稳态是 8000。因为压测的前十几秒全在预热。
> **正确姿势**：
> - 至少预热到"编译日志不再密集输出"再开始计时
> - 长稳测试跑 10 分钟以上，观察前 2 分钟与后 8 分钟的差异
> - **对比两个版本时，预热条件必须完全一致**（同样的迭代次数、同样的启动参数、同样的机器状态）
> - 用 JMH 时自然满足（它有专门的 warmup 阶段）

**生产上的对应实践**：容器启动后**先跑一段流量预热**（Kubernetes 的 readiness probe 加延迟、LoadBalancer 加 warm-up 策略、网关做慢启动），否则滚动发布时新实例会集中出现延迟毛刺。

### 6.2 基准测试必须用 JMH

**为什么手写 `System.currentTimeMillis()` 不可靠**：

| 陷阱 | 机制 | 后果 |
|---|---|---|
| **死代码消除（DCE）** | 计算结果没被使用 → JIT 删掉整个计算 | 测出"零耗时" |
| **常量折叠** | 输入是常量、方法可内联 → 整个计算在编译期算完 | 同上 |
| **循环优化** | 循环被展开/消除，或者被测代码被提到循环外 | 测的不是你要测的东西 |
| **预热不足** | 测的是解释器/C1 版本 | 数据偏慢且不可复现 |
| **计时精度与系统噪声** | `nanoTime` 粒度、GC 暂停、其他进程、CPU 频率调节 | 方差巨大 |
| **OSR 偏差** | 方法被 OSR 编译，测的是特殊的 OSR 版本 | 与真实稳态不符 |
| **虚假共享 / 缓存效应** | 测量代码改变了内存布局 | 不可复现 |
| **单次 fork** | 同一 JVM 里跑多个基准，前面的会污染 Profile 与 Code Cache | 后测的基准被前一个影响 |

**JMH（Java Microbenchmark Harness）做了什么**：

| 机制 | 作用 |
|---|---|
| **`@Warmup`** | 单独跑预热迭代，不计入结果 |
| **`@Measurement`** | 正式测量迭代 |
| **`@Fork`** | 每个基准在**独立 JVM 进程**里跑（可指定 fork 次数），消除跨基准污染与 JIT 状态残留 |
| **`Blackhole`** | 强制"消费"结果，让 JIT 无法消除死代码（`bh.consume(value)`） |
| **`@State(Scope)`** | 定义状态对象的作用域（`Benchmark` / `Thread` / `Group`），避免虚假共享与错误的初始化时机 |
| **`@Setup` / `@TearDown`** | 分 `Trial` / `Iteration` / `Invocation` 三级的初始化/清理，保证不把准备动作算进计时 |
| **结果统计** | 输出平均值、标准差、置信区间、百分位数，直接给"可信/不可信"判断 |
| **`-prof gc` / `-prof stack`** | 内置 profiler，看分配率、GC 时间、热点栈 |

```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1)          // 5 轮 × 1 秒预热
@Measurement(iterations = 5, time = 1)     // 5 轮 × 1 秒测量
@Fork(2)                                   // 2 个独立 JVM 进程
@State(Scope.Thread)                       // 每个线程一个状态实例
public class StringConcatBenchmark {

    private String a = "hello";
    private String b = "world";

    @Benchmark
    public String plus() {
        return a + "-" + b;                // 返回值会被 JMH 消费，不会被 DCE
    }

    @Benchmark
    public String builder() {
        return new StringBuilder().append(a).append('-').append(b).toString();
    }

    @Benchmark
    public int withBlackhole(Blackhole bh) {
        int r = 0;
        for (int i = 0; i < 100; i++) {
            r += i;
        }
        bh.consume(r);                     // ★ 显式消费，防 DCE
        return r;
    }
}
```

```bash
# 运行（推荐用 shade 插件打出 benchmarks.jar 后单进程运行）
java -jar benchmarks.jar -f 2 -wi 5 -i 5 -prof gc
```

**输出形态（示意）**：

```text
Benchmark                          Mode  Cnt     Score     Error   Units
StringConcatBenchmark.plus        avgt   10    14.230 ±   0.412   ns/op
StringConcatBenchmark.builder     avgt   10    13.980 ±   0.355   ns/op
StringConcatBenchmark.withBlackhole avgt  10    28.110 ±   0.902   ns/op
```

> [!important] 面试标准答案：为什么必须用 JMH
> 一句话版本：**"因为 JIT 会把你真正想测的代码优化掉，或者优化成你没想到的样子。"**
> 展开三点：
> 1. **DCE / 常量折叠 / 循环优化**会删掉"结果没被使用"的计算 → 必须用 `Blackhole` 或返回结果让 JMH 消费
> 2. **预热与 Profile 演化**让同一段代码在不同时间点性能不同 → 必须有独立 warmup 阶段
> 3. **JVM 内状态污染**（Profile、Code Cache、Heap 布局）让多个基准互相影响 → 必须 `@Fork` 到独立进程
> 加分点：主动提"即使有了 JMH，微基准结论也常常**不能直接外推到生产**——真实系统里 JIT 形态受调用链、数据分布、并发度影响，微基准只能验证'哪个实现更省 CPU'这类局部问题"。这句话能让面试官知道你真的做过性能工作。

### 6.3 `-XX:+PrintCompilation` 的输出怎么读

```bash
java -XX:+PrintCompilation -XX:+PrintCodeCache -jar app.jar
```

**输出形态（示意）**：

```text
     45    1       3       java.lang.String::hashCode (55 bytes)
     62    2       3       java.lang.String::indexOf (70 bytes)
     78    3 %     4       com.demo.Hot::loop @ 12 (25 bytes)
     90    4       4       com.demo.Hot::loop (25 bytes)
    102    5     n 0       java.lang.Object::hashCode (1 bytes)
    115    6       4       com.demo.OrderService::calc (28 bytes)
    130    7       3       com.demo.OrderService::calc (28 bytes)   made not entrant
    145    8       4       com.demo.OrderService::calc (28 bytes)
    160    9 s     4       com.demo.SyncService::update (42 bytes)
```

**列的含义**：

| 列 | 含义 |
|---|---|
| 第 1 列 | **时间戳**（毫秒，自 JVM 启动） |
| 第 2 列 | **编译任务 ID**（自增） |
| 第 3 列 | **属性字符**，可组合：`%` = **OSR 编译**；`s` = synchronized 方法；`!` = 有异常处理器；`b` = 阻塞（blocking）编译；`n` = native 方法包装 |
| 第 4 列 | **层级**（分层编译开启时）：0/1/2/3/4。**看到 `4` 才说明 C2 编译完成** |
| 第 5 列 | 方法名（`类::方法`） |
| 第 6 列 | 字节码大小（bytes），**可以用来判断是否触发了内联预算** |
| 尾部 | `made not entrant` = **这段编译代码已被标记为不可再进入（去优化）**；`made zombie` = 已被彻底回收 |

**观察清单**：

| 想确认什么 | 看什么 |
|---|---|
| 是否已到 C2 | 层级列有没有出现 `4` |
| 是否有 OSR | 属性列有没有 `%` |
| 是否发生去优化 | 有没有 `made not entrant`；**同一方法是否反复出现在不同层级**（如 4 → 3 → 4 循环） |
| 编译是否过于频繁 | 启动后几十秒里输出行数是否成百上千（编译 CPU 开销的迹象） |
| 方法是否过大 | 字节码 size 列超过 325（`FreqInlineSize`）就是"内联预算吃紧"的信号 |
| 是否被无限重编译 | 同一方法名大量重复出现 → 通常伴随去优化抖动 |

**常用组合命令**：

```bash
# 只看 C2 编译 + 只看带 OSR 的
java -XX:+PrintCompilation -jar app.jar | grep -E '%| 4 '

# 统计去优化次数
java -XX:+PrintCompilation -jar app.jar 2>&1 | grep -c 'made not entrant'

# 完整 JIT 日志（给 JITWatch 用，输出是 XML）
java -XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation -XX:LogFile=hotspot.log -jar app.jar

# 看内联决策
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining -jar app.jar

# 看汇编（需要 hsdis 插件，见下）
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly -XX:CompileCommand=print,com.demo.Hot::loop -jar app.jar
```

> [!tip] `PrintAssembly` 需要 hsdis
> 要看到真正的机器码，需要把 `hsdis` 动态库（`libhsdis-amd64.dylib` / `libhsdis-amd64.so`）放到 JVM 能找到的路径。没有它就只会打印警告。
> 配合 `-XX:CompileCommand=print,类名::方法名` 可以**只打印指定的方法**，避免输出淹没屏幕。

### 6.4 去优化（Deoptimization）

**为什么会有去优化**：C2 的激进优化建立在**推测（speculation）**之上——"这个调用点只有一个实现类"、"这个分支从没走过"、"这个数组访问不会越界"。一旦推测被现实推翻，就必须**放弃已编译代码，回到解释器或较低层级**，这个过程叫去优化。

```text
   C2 编译时: "调用点只有一个实现类 Foo" → 内联 Foo，插入 guard
                     │
                     ▼
   运行期: 突然加载了新的实现类 Bar，调用点收到 Bar 实例
                     │
                     ▼
   guard 失败 → uncommon trap → 去优化
                     │
                     ▼
   栈帧变回解释执行（状态从编译代码"反向映射"回解释器栈帧）
                     │
                     ▼
   重新收集 Profile → 可能重新编译成双态/巨态版本
```

**触发的典型原因**：

| 原因 | 例子 |
|---|---|
| **类型 Profile 失效** | 新的实现类被加载/被使用（**插件热加载、Spring 动态代理、Mock 框架**） |
| 分支预测失效 | 一直走 `if` 的某个分支，突然走另一个 |
| 类层次变化 | 加载了新的子类，使"只有一个子类"的假设失效 |
| `uncommon trap` | 编译时代码里生成了"这不该发生"的陷阱，运行时真的发生了 |
| **Code Cache 满** | Sweeper 丢弃旧代码，或编译器被禁用 |
| **NMethod 失效** | 依赖的类被卸载/重定义（`Instrumentation.retransformClasses`、热部署） |
| 逃逸分析失效 | 对象的逃逸状态在运行期发生变化（罕见但存在） |

**观测方式**：

```bash
# 打印去优化详细信息（需诊断开关）
java -XX:+UnlockDiagnosticVMOptions -XX:+TraceDeoptimization -jar app.jar

# 只需次数，看 PrintCompilation 里的 "made not entrant"
java -XX:+PrintCompilation -jar app.jar 2>&1 | grep -c 'made not entrant'
```

`TraceDeoptimization` 输出形态（示意）：

```text
DEOPT PACKING thread 0x...  compiled method (c2)   115   6  com.demo.OrderService::calc (28 bytes)
     total frame size in caller: 64
     scope 0 (sp)  com.demo.OrderService::calc @ 5
     scope 1 (sp)  com.demo.PriceRule::apply @ 12
DEOPT UNPACKING thread 0x...  pc=0x... does not match
     ...
     reason: no such class loaded
     reason: constraint
uncommon trap occurred in com.demo.OrderService::calc
```

**关键：去优化不是 bug，是设计特性。** 它是"激进优化但保证语义正确"的代价与保险。问题在于**频繁去优化**会造成性能抖动。

> [!warning] 无限去优化循环
> 如果一个方法被反复"编译 → 去优化 → 重编译 → 再去优化"，会消耗大量 CPU 且性能一直不稳定。HotSpot 有保护机制：当同一方法的去优化次数超过上限（`-XX:PerMethodRecompilationCutoff` / `-XX:PerBytecodeRecompilationCutoff` 控制）后，**该方法会被永久放弃 C2 编译，永远解释执行**——在日志里表现为 `made zombie`。
> **这是"某个方法突然一直很慢"的一个真实根因**，尤其在用 Mock/代理框架的测试环境和热部署频繁的环境里。

### 6.5 "同一个方法跑一会儿突然变慢"的排查清单

```text
现象：某接口 p99 从 20ms 涨到 200ms，且持续不恢复（或周期性抖动）
   │
   ├─ ① 去优化（Deoptimization）
   │     · 特征：PrintCompilation 里出现 made not entrant，同一方法反复编译
   │     · 常见触发：动态加载了新实现类、热部署、Instrumentation retransform
   │     · 验证：-XX:+TraceDeoptimization
   │
   ├─ ② Code Cache 满 / 编译器被禁用
   │     · 特征：日志出现 "CodeCache is full. Compiler has been disabled."
   │     · 验证：jcmd <pid> Compiler.codecache 看 max_used 是否逼近上限
   │     · 结果：所有方法退回解释执行 → 性能断崖
   │
   ├─ ③ 调用点变 megamorphic
   │     · 特征：上线新业务分支/新实现类后变慢；PrintInlining 里出现 megamorphic
   │     · 验证：-XX:+PrintInlining 找 "not monomorphic"
   │
   ├─ ④ 热度衰减导致重新预热
   │     · 特征：每天高峰初期慢，稳定后恢复
   │     · 机制：CounterHalfLifeTime 让计数折半，低谷期后需重新升温
   │
   ├─ ⑤ GC 变化（不是 JIT，但表现一样）
   │     · 特征：GC 日志里 Full GC / Mixed GC 频率上升；老年代增长
   │     · 验证：-Xlog:gc* 对比变慢前后的停顿与频率
   │
   ├─ ⑥ 锁膨胀 / 竞争加剧（不是 JIT 优化，是相反方向）
   │     · 特征：线程 BLOCKED 增多；jstack 看到同一监视器
   │     · 注意：JIT 的锁消除是"减少锁"，竞争加剧是"锁更多线程"
   │
   ├─ ⑦ 编译线程抢 CPU
   │     · 特征：火焰图里 C2 CompilerThread 占用显著；应用线程被抢占
   │     · 验证：jcmd Thread.print | grep Compiler；perf/jfr 看编译事件
   │
   └─ ⑧ 外部因素
         · 连接池耗尽、下游变慢、容器 CPU throttling、内存 swap
         · 验证：容器指标、下游延迟、CPU throttling 计数
```

**排查顺序建议**：先看 **GC 日志**（最常见）→ 再看 **Code Cache 的 `max_used`**（最容易漏）→ 再看 **去优化次数**（最隐蔽）→ 最后怀疑 JIT 之外的系统因素。

具体排障流程与工具细节见 [[7-JVM故障排查实战]]。

---

## 七、观测与诊断工具

### 7.1 命令行速查表

| 目的 | JDK 8 | JDK 9+ |
|---|---|---|
| 看编译了哪些方法 | `-XX:+PrintCompilation` | 同（仍然有效） |
| 看内联决策 | `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining` | 同 |
| 看 Code Cache 使用 | `-XX:+PrintCodeCache` | `-Xlog:codecache=info`（推荐），`PrintCodeCache` 已废弃 |
| 看汇编 | `-XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly`（需 hsdis） | 同 |
| 完整 JIT 日志（XML） | `-XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation -XX:LogFile=x.log` | 同 |
| 看去优化 | `-XX:+UnlockDiagnosticVMOptions -XX:+TraceDeoptimization` | 同 |
| 强制编译指定方法 | `-XX:CompileCommand=compileonly,类::方法` | 同 |
| 排除某方法不编译 | `-XX:CompileCommand=exclude,类::方法` | 同 |
| 打印内联/逃逸详情 | `-XX:+PrintEscapeAnalysis`、`-XX:+PrintEliminateAllocations` | 同（诊断开关） |

**`-XX:CompileCommand` 是排查利器**：

```bash
# 只编译这一个方法，其他都不编译（隔离变量，看它到底能优化到什么程度）
java -XX:CompileCommand=compileonly,com.demo.Hot::loop -XX:+PrintCompilation ...

# 排除某个方法的内联（验证"是不是内联带来的收益"）
java -XX:CompileCommand=dontinline,com.demo.Rule::apply -jar app.jar

# 把汇编打印限定到某个方法
java -XX:+UnlockDiagnosticVMOptions -XX:+PrintAssembly \
     -XX:CompileCommand=print,com.demo.Hot::loop -jar app.jar
```

### 7.2 JITWatch

**JITWatch 是读 JIT 日志的图形化工具**（开源，Swing 界面）。它的价值在于：`-XX:+LogCompilation` 生成的 XML 日志有几十万行，肉眼看基本不可能。

| 功能 | 作用 |
|---|---|
| **主界面** | 按包/类浏览被编译的方法，颜色区分 C1/C2/OSR/native |
| **内联决策树** | 展示每个方法的内联链条，以及**被拒绝的原因**（too big / megamorphic / no profile） |
| **字节码 ↔ 汇编对照** | 左边字节码、右边机器码，能看出某条字节码被优化成了什么 |
| **失败原因统计** | 汇总所有内联拒绝原因，一眼看出瓶颈在哪类方法 |
| **Code Cache 时间线** | 代码缓存随时间的占用曲线 |
| **去优化列表** | 哪些方法、什么原因被去优化 |

**使用步骤**：

```bash
# 1. 生成日志（日志会很大，别在生产长时间开）
java -XX:+UnlockDiagnosticVMOptions -XX:+LogCompilation \
     -XX:LogFile=hotspot_pid%p.log -XX:+PrintInlining -jar app.jar

# 2. 用 JITWatch 打开 hotspot_pid*.log
```

> [!tip] JITWatch 的现实定位
> 它是**离线分析工具**，适合"我已经知道哪段代码慢，想搞清楚 JIT 到底怎么处理它"。
> 不适合线上常态化开启（日志量大、有性能开销）。
> 日常排查更轻量的做法是：`-XX:+PrintInlining` 配合 `grep`，只看热点方法的内联情况。

### 7.3 JIT 相关的 JFR 事件

**JFR（JDK Flight Recorder）是生产环境首选的观测手段**——开销低（通常 1% 量级）、内置、无需第三方 agent。

```bash
# 启动时开启
java -XX:StartFlightRecording=filename=app.jfr,duration=300s,settings=profile -jar app.jar

# 运行中开启
jcmd <pid> JFR.start name=jit settings=profile duration=120s filename=jit.jfr
jcmd <pid> JFR.dump name=jit filename=jit.jfr
jcmd <pid> JFR.stop name=jit
```

**与 JIT 相关的事件**：

| 事件 | 内容 | 用途 |
|---|---|---|
| `jdk.Compilation` | 每次编译：方法名、层级、是否 OSR、编译耗时、字节码大小 | **编译开销分析**：哪个方法编译最久 |
| `jdk.CompilerConfiguration` | 编译器配置：线程数、层级、Code Cache 大小 | 环境核对 |
| `jdk.CompilerPhase` | C2 各优化阶段的耗时 | 深入分析编译慢的原因 |
| `jdk.CompilerInlining` | 内联决策 | 替代 `PrintInlining` 的低开销方案 |
| `jdk.Deoptimization` | 去优化：方法、原因、次数 | **定位性能抖动** |
| `jdk.CodeCacheConfiguration` | 代码缓存配置与使用 | 容量规划 |
| `jdk.CodeCacheFull` | **代码缓存满事件** | **直接告警项** |
| `jdk.CodeSweeperStatistics` | 清扫统计 | 判断是否在反复清扫 |
| `jdk.CompilerStatistics` | 编译次数/耗时汇总 | 趋势观察 |

> [!important] 生产上最该配的两个 JIT 告警
> 1. **`jdk.CodeCacheFull`** —— 出现即意味着 JIT 即将/已经停摆，是明确的性能悬崖前兆
> 2. **`jdk.Deoptimization` 的频率** —— 突然升高说明运行期形态发生了剧变（新类加载、热部署、Mock 注入）
> 用 JDK Mission Control（JMC）打开 `.jfr` 文件即可看到这些事件的图形化展示。

### 7.4 火焰图里的编译线程

用 `async-profiler` / `perf` 采样时，会看到：

```text
C2 CompilerThread0
  └─ Compile::Code_Gen
     └─ PhaseIdealLoop::optimize
        └─ ...
C2 CompilerThread1
  └─ ...
CodeCache Sweeper
```

| 现象 | 解读 | 处理 |
|---|---|---|
| 编译线程占 CPU **个位数百分比** | 正常（启动/预热期会高） | 无需处理 |
| 编译线程占 **20%+ 且持续** | **编译开销过大**的强信号 | ① 检查是否有大量动态类生成（代理/脚本）；② 检查是否有超巨方法反复编译；③ 用 `jdk.Compilation` 事件找出"编译最耗时的方法"；④ 必要时限制 `CICompilerCount` |
| 火焰图全是 `[unknown]` | 缺 `perfmap` | `jcmd <pid> Compiler.perfmap` 生成符号映射后再采样 |
| 启动很久后编译线程仍很忙 | 可能在**反复重编译某个方法** | 看 `PrintCompilation` 是否有同一方法大量重复行 |

**用 perf 采样的完整流程（Linux）**：

```bash
# 1. 生成 perf map（让 perf 能解析 JIT 方法名）
jcmd <pid> Compiler.perfmap
# 或启动时加 -XX:+PreserveFramePointer（老版本 async-profiler 需要）

# 2. 采样
perf record -F 99 -p <pid> -g -- sleep 30
perf script > out.perf

# 3. 生成火焰图
./FlameGraph/stackcollapse-perf.pl out.perf > out.folded
./FlameGraph/flamegraph.pl out.folded > flamegraph.svg
```

> [!tip] 首选 async-profiler
> 它直接读取 JVM 内部结构，**不需要 perfmap、不需要 `-XX:+PreserveFramePointer`**，还支持按分配、锁、wall-clock 采样，是 Java 火焰图的事实标准。
> ```bash
> ./asprof -d 30 -f flamegraph.html <pid>
> ./asprof -e alloc -d 30 -f alloc.html <pid>      # 分配火焰图
> ./asprof -e lock  -d 30 -f lock.html  <pid>      # 锁竞争火焰图
> ```

### 7.5 一个可直接套用的"JIT 体检"组合

```bash
java \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:+PrintCompilation \
  -XX:+PrintInlining \
  -Xlog:codecache=info \
  -Xlog:class+load=info:file=classload.log \
  -XX:StartFlightRecording=filename=app.jfr,settings=profile,duration=600s \
  -jar app.jar
```

| 输出 | 看什么 |
|---|---|
| `PrintCompilation` | 层级分布、OSR、`made not entrant` 次数 |
| `PrintInlining` | `too big` / `megamorphic` / `no profile data` 的分布 |
| `codecache=info` | `max_used` 是否逼近上限、编译器是否 `disabled` |
| `classload.log` | 是否有异常大量的动态类加载（代理、脚本） |
| `app.jfr` | 编译耗时 Top、去优化频率、Code Cache 事件 |

**注意**：这套组合**开销很大**，只适合在预发/压测环境短时开启，不要长期挂生产。

---

## 八、代码层面的写法建议（把 JIT 当"协作者"）

### 8.1 内联预算视角

| 建议 | 机制依据 |
|---|---|
| ✅ **方法保持精悍**（几十行，字节码几百字节内） | 超过 `FreqInlineSize`（约 325 字节）就拒绝内联，进而丢失所有跨方法优化 |
| ✅ **热点路径上避免巨型 `switch` / 巨型 `if-else` 链** | 方法体膨胀 → 不被内联；分支多 → 分支预测与 Profile 质量下降 |
| ✅ **把冷逻辑（异常处理、日志、校验）抽出去** | 让热方法变小。**注意**：`if (log.isDebugEnabled())` 这种模式本身就同时服务于"避免不必要的字符串拼接"与"缩小热方法体"，是双重收益 |
| ✅ **避免同一个方法既做核心计算又做 I/O** | I/O 的阻塞语义会阻止一些优化（blocking 标记），且方法必然变大 |
| ❌ **不要为了内联把一个方法拆成十几个 3 行的碎片** | 内联有层级限制（`MaxInlineLevel`）；拆太碎会让 Profile 分散、可读性变差 |

### 8.2 调用点形态视角

| 建议 | 机制依据 |
|---|---|
| ✅ **减少 megamorphic 调用点**：按类型分组处理，而不是在一个循环里对多种子类统一调用虚方法 | 类型数 > 2 就放弃内联 |
| ✅ **避免无意义的抽象层**（一个接口一个实现的 `XxxService`/`XxxServiceImpl`） | 虽然单态调用能被完美内联，但每层抽象都增加一次"能否内联"的不确定性；**有测试/替换需求时该抽象就抽象，但别为抽象而抽象** |
| ✅ **对确定不需要重写的小方法，`final` 或 `private` 有帮助** | 静态绑定省掉一次类型 Profile 判断。**但收益在现代 JIT 上很小，不要为此写"`final` 痴迷"代码** |
| ✅ **`getter` 不必要手写** | 简单的 getter 通常被直接内联并消除，收益接近零。真正有收益的是**避免在热循环里反复调用有复杂逻辑的 getter** |
| ✅ **显式 `@FunctionalInterface` 的 lambda 尽量无捕获** | 无捕获 lambda 复用单例；有捕获每次实例化（虽然能被逃逸分析消除，但不保证） |

### 8.3 数据与内存视角

| 建议 | 机制依据 |
|---|---|
| ✅ **局部作用域内的小对象不必规避** | 不逃逸 → 标量替换 → 零分配 |
| ✅ **警惕"让对象逃逸"的无意操作**：放进静态集合、返回、传给线程池、加 `synchronized` 后跨线程共享 | 逃逸立刻使标量替换与锁消除失效 |
| ✅ **字符串拼接：单条语句用 `+`，循环里用 `StringBuilder`/`StringJoiner`** | 见 [[3-类加载机制与字节码]] §9.4：`javac` 的优化只覆盖"一条语句" |
| ✅ **数组复制用 `System.arraycopy`** | 有 intrinsics 实现，可能展开为向量化指令 |
| ✅ **避免在热路径上创建 `Stream` 管道** | 每次 `stream()` 都创建对象，且 lambda 捕获环境；**先测量**——现代 JIT 对短 `Stream` 的处理已相当好，但超长链仍不如循环 |
| ✅ **`String.format` / 正则 `Pattern.compile` 不要放热路径** | 解析开销大且 `Pattern.compile` 每次新建对象 |

### 8.4 心态与流程视角（最重要的一条）

> [!important] 先测量，再优化；不要为了"讨好 JIT"而写难维护的代码
> JIT 优化的第一原则是 **"先测量（measure first）"**。上面所有建议都是**在确认存在热点之后**才考虑的微调，而不是编码前的教条。
> 反面教材：
> - 手写"对象池"来豁免 GC，结果因为逃逸/线程安全反而更慢
> - 把所有方法都写成 3 行以内，可读性崩塌而性能没变
> - 到处加 `final`，代码变长、JIT 无感
> - 用 `StringBuilder` 替换单条语句里的 `+`，可读性下降、字节码更差
>
> **正确的流程**：
> ```text
> 1. 用 JMH / 压测找出真正的热点（火焰图 + 分配火焰图）
> 2. 用 PrintInlining / JFR 确认热点方法的 JIT 形态
> 3. 只针对确认的瓶颈做修改（拆方法、减少类型、避免逃逸）
> 4. 用同样的 JMH 配置验证收益，并检查是否引入了回归
> 5. 记录结论（哪个优化、在什么数据形态下有效）
> ```

---

## 九、必答

> [!question] 1. 为什么 Java 需要预热？预热到底预热了什么？
> 三个层面：
> ① **执行层级**：方法从解释执行（level 0）→ C1（1/2/3）→ C2（4），每一级都要达到对应的热度阈值（分层编译下由 `Tier3*` / `Tier4*` 一组阈值控制）。
> ② **Profile 质量**：C2 的激进优化依赖运行期收集的**类型 Profile、分支频率、逃逸信息**，数据不足时它只能保守。方法调用次数越多，Profile 越"真实"，优化才越到位。
> ③ **优化生效**：内联、逃逸分析、标量替换、去虚化、锁消除这些优化**只在 C2 生效**，所以必须等到 level 4 才能吃到。
> **实战推论**：压测必须预热到 level 4；两个版本对比必须用完全相同的预热条件；滚动发布时新实例要做流量预热。

> [!question] 2. 为什么基准测试必须用 JMH？
> 因为 **JIT 会把你真正想测的代码优化掉**：
> - 结果没被使用 → **死代码消除**直接删掉整个循环
> - 输入是常量 → **常量折叠**在编译期算完
> - 循环被展开/消除 → 测的不是你想测的
> JMH 用 `Blackhole` 强制消费结果、用 `@Warmup`/`@Measurement` 分离预热与测量、用 `@Fork` 在独立 JVM 进程里跑以避免 Profile 与 Code Cache 污染、用 `@State` 控制状态作用域、并给出置信区间与标准差。
> **加分**：微基准的结论不能直接外推到生产，它只能验证"哪个实现更省 CPU"这类局部问题；真实性能必须靠全链路压测 + 火焰图。

> [!question] 3. 逃逸分析能带来什么？有什么局限？
> **能带来三件事**（对象不逃逸的前提下，仅 C2 生效）：
> ① **标量替换**——把对象拆成字段放进寄存器/栈，**连堆分配都不发生**（`EliminateAllocations`）
> ② **锁消除**——独占的锁直接删掉 `monitorenter`/`monitorexit`（`EliminateLocks`）
> ③ 由此**打开下游优化**：字段成为标量后，常量折叠、CSE、DCE 才能作用其上
> **局限**：
> ① **只在 C2（level 4）生效**，没预热就享受不到
> ② **不改变语义**，只是把等价分配搬到寄存器——不能用它解释"对象看不见了"
> ③ **HotSpot 没有真正的"栈上分配"**，准确说法是"分配被消除"，说"对象在栈上"技术上不准确
> ④ 一旦对象逃逸（返回、存入静态字段、跨线程共享），优化全部失效

> [!question] 4. 方法内联为什么是最重要的优化？
> 因为它是**其他所有优化的前提**：只有把被调方法的代码"看进来"，C2 才能做常量传播、逃逸分析、锁消除、死代码消除。不内联，这些优化全部无从谈起。
> 相关参数：`-XX:MaxInlineSize`（非热点，默认约 35 字节）、`-XX:FreqInlineSize`（热点，默认约 325 字节）、`-XX:MaxInlineLevel`（深度约 9）。
> **"把大方法拆小反而更快"的机制**：超过 `FreqInlineSize` 就拒绝内联 → 丢失全部跨方法优化 → 拆成小方法后每个都能被内联，性能回升。
> 观测：`-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining`，关注 `too big` 与 `megamorphic`。

> [!question] 5. Code Cache 满了会怎样？
> **JIT 编译器被完全禁用**（日志：`CodeCache is full. Compiler has been disabled.`），此后所有方法**永远停留在解释执行**，性能断崖式下跌——但**应用不崩溃、不抛异常**，只是持续变慢。JDK 8 上还有 `UseCodeCacheFlushing` 作为兜底，会丢弃旧编译代码来腾空间，代价是去优化抖动。
> **观测**：`jcmd <pid> Compiler.codecache` 看 `used` / `max_used` 是否逼近上限、`compilation:` 是否变成 `disabled`；JDK 9+ 用 `-Xlog:codecache=info`；JFR 里有 `jdk.CodeCacheFull` 事件。
> **修复**：调大 `-XX:ReservedCodeCacheSize`，并排查是否有大量动态类生成（CGLIB、脚本引擎、反射 inflate）。

> [!question] 6. 分层编译的 5 个层级分别是什么？
> **level 0** 解释执行（收集轻量 Profile）；**level 1** C1 编译但不做 Profiling（极简方法走这条）；**level 2** C1 + 轻量 Profile（C2 队列繁忙时的过渡）；**level 3** C1 + 完整 Profile（最主流中转站）；**level 4** C2 编译（最终形态）。
> 典型路径 `0 → 3 → 4`。`-XX:-TieredCompilation` 关闭分层（直接 C2，阈值用 `CompileThreshold`）；`-XX:TieredStopAtLevel=1` 只用 C1（启动快、峰值低，适合 CLI）。

> [!question] 7. OSR 是什么？为什么需要它？
> **栈上替换（On-Stack Replacement）**：为一个正在执行的长循环，在循环中间把解释执行的栈帧**原地替换**成编译后的栈帧，方法是"编译一个从循环入口进入的版本"。
> **为什么需要**：只被调用一次但内部跑十亿次循环的方法（`main`、批处理入口），调用计数器永远达不到阈值，只有**回边计数器**能发现它热。
> **观测**：`-XX:+PrintCompilation` 输出里的 **`%`** 标记。
> **代价**：需要把解释器栈帧状态映射到编译代码，为每个可能的循环入口生成进入点，因此优化质量可能不如标准编译。

> [!question] 8. 去优化是什么？什么时候会发生？
> **去优化（Deoptimization）**是"编译期的激进推测被运行期推翻"时的回退：已编译代码被标记为 `made not entrant`，栈帧从编译代码反向映射回解释器栈帧，重新收集 Profile，之后可能重新编译。
> **触发原因**：新的实现类被加载使类型 Profile 失效、分支预测失效、类层次变化、`uncommon trap` 命中、Code Cache 满导致清扫、类被重定义或卸载（热部署 / `retransformClasses`）。
> **观测**：`-XX:+UnlockDiagnosticVMOptions -XX:+TraceDeoptimization`；或 `PrintCompilation` 里的 `made not entrant` / `made zombie`。
> **注意**：去优化是**设计特性而非 bug**；但**频繁去优化**（尤其超过 `PerMethodRecompilationCutoff` 后方法被永久放弃编译）会导致性能持续抖动。

> [!question] 9. 为什么"抽象层次高"会变慢？
> 因为**多态调用点的类型越多，内联越难**：单态（1 种类型）可完美内联并加类型守卫；双态（2 种）两个目标都内联；**巨态（≥ 3 种）直接放弃内联**，退回虚方法表查找。而内联是其他优化的前提，于是"不能内联"意味着常量传播、逃逸分析、锁消除一起失效。
> `-XX:TypeProfileWidth` 默认是 2，这也是"第 3 种类型很致命"的原因。
> **缓解**：按类型分组处理、减少不必要的抽象层、避免在同一个循环里对多种子类统一调用虚方法。

> [!question] 10. 一个方法"跑一会儿突然变慢"，你会怎么查？
> 按这个顺序（详见 §6.5）：
> ① **GC 日志**——最常见，看 Full/Mixed GC 频率与老年代增长
> ② **Code Cache**——`jcmd <pid> Compiler.codecache` 看 `max_used` 与 `compilation: disabled`
> ③ **去优化**——`PrintCompilation` 里 `made not entrant` 的计数、`TraceDeoptimization` 的原因
> ④ **调用点是否变 megamorphic**——`PrintInlining` 找 `not monomorphic`
> ⑤ **热度衰减/重新预热**——是否每天高峰初期慢
> ⑥ **编译线程抢 CPU**——火焰图里 `C2 CompilerThread`
> ⑦ **JIT 之外**：锁竞争、下游变慢、连接池、容器 CPU throttling
> 排查工具与完整流程见 [[7-JVM故障排查实战]]。

> [!tip] 相关笔记
> · 字节码结构、`invokedynamic`、类的加载与卸载 → [[3-类加载机制与字节码]]
> · GC 与内存布局（逃逸分析与分配的关系） → [[2-GC机制深度]]、[[1-JVM内存区域与对象布局]]
> · `synchronized` 的语义（锁消除的语义前提） → [[4-多线程与内存模型]]
> · JIT 相关参数怎么设（Code Cache、编译线程、TieredStopAtLevel） → [[6-JVM参数与调优实战]]
> · CPU 高 / 抖动 / 性能下降的完整排查流程 → [[7-JVM故障排查实战]]
> · 字符串拼接与 lambda 的版本演进 → [[9-Java版本特性]]
> · 集合框架的 JIT 友好写法 → [[1-集合框架]]
> · 线程池中的 TCCL 与线程复用带来的问题 → [[5-线程池]]
> · 题库 → [[面试准备/技术面试题库/03-JVM与性能调优]]
