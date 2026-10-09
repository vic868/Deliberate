---
title: JVM 内存区域与对象布局
tags: [JVM, 内存区域, 对象布局]
status: 进行中
created: 2026-10-09
---

# 🧠 一、JVM 内存区域与对象布局

> 本篇回答：JVM 运行时到底把内存切成哪几块、每块存什么、会不会 OOM；一个对象从 `new` 到可用的完整过程；对象在内存里长什么样（Mark Word / 类型指针 / 对齐）；指针碰撞与 TLAB 这些"分配细节"到底在解决什么问题；以及四种引用、`finalize`/`Cleaner`、字符串常量池这些高频面试点。
> 定位：**分配视角**。JIT、逃逸分析的优化细节见 [[5-JIT编译与运行时优化]]；回收视角（可达性分析、三色标记、各收集器）见 [[2-GC机制深度]]；参数与调优见 [[6-JVM参数与调优实战]]；线上排查见 [[7-JVM故障排查实战]]。
> 版本基线：以 **Java 8** 为下限，标注 17 / 21 / 25 的差异。文中所有默认值均来自 `-XX:+PrintFlagsFinal` 实测（本机 JDK 17.0.11），标注「示意」的输出为手写示例、非实测。
> 关联：[[0-JVM总览]]、[[0-Java总览]]、[[4-多线程与内存模型]]（JVM 内存布局 ≠ Java 内存模型）、[[3-类加载机制与字节码]]、[[1-集合框架]]、[[3-IO与网络编程]]、[[10-面试高频题]]、[[面试准备/技术面试题库/03-JVM与性能调优]]。

---

## 一、运行时数据区总览

### 1.1 一张图看清分区

```
┌──────────────────────────── JVM 运行时数据区（JVMS 规范定义） ───────────────────────────┐
│  线程私有（随线程生灭）              │  线程共享（随 JVM 生灭）                          │
│  ┌────────────────────────┐         │  ┌──────────────────────────────────────────┐  │
│  │ 程序计数器 PC           │         │  │ 堆 Heap                                   │  │
│  │  → 当前字节码行号        │         │  │  → 对象实例、数组                          │  │
│  ├────────────────────────┤         │  │  → 新生代(Eden + S0 + S1) + 老年代         │  │
│  │ 虚拟机栈 VM Stack       │         │  ├──────────────────────────────────────────┤  │
│  │  → 栈帧 Frame           │         │  │ 方法区 Method Area                         │  │
│  │    局部变量表/操作数栈/  │         │  │  → JDK7-: 永久代（堆内）                    │  │
│  │    动态链接/返回地址     │         │  │  → JDK8+ : 元空间（本地内存）               │  │
│  ├────────────────────────┤         │  │  → 类元信息、运行时常量池、静态变量         │  │
│  │ 本地方法栈 Native Stack │         │  └──────────────────────────────────────────┘  │
│  │  → native 方法栈帧      │         │                                                │
│  └────────────────────────┘         │  另有：直接内存（不属于运行时数据区）           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 每个区域：存什么 / 会不会 OOM / 抛什么错

| 区域 | 线程 | 存什么 | 会 OOM 吗 | 典型异常 |
|---|---|---|---|---|
| **程序计数器 PC** | 私有 | 当前线程正在执行的字节码指令地址（native 方法时为 undefined） | **不会**（规范明确唯一不会 OOM 的区域） | —— |
| **虚拟机栈** | 私有 | 栈帧：局部变量表、操作数栈、动态链接、返回地址 | 会 | `StackOverflowError`（深度超限）、`OutOfMemoryError`（无法申请栈内存） |
| **本地方法栈** | 私有 | native 方法（JNI）的栈帧 | 会 | 同虚拟机栈；HotSpot 把两者合并实现 |
| **堆** | **共享** | 对象实例、数组（含字符串常量池中的 String 对象） | 会 | `OutOfMemoryError: Java heap space` |
| **方法区** | **共享** | 类元数据（InstanceKlass）、运行时常量池、静态变量、JIT 编译后的代码（CodeCache 是独立区域） | 会 | JDK8+：`OutOfMemoryError: Metaspace`；JDK7-：`OutOfMemoryError: PermGen space` |
| **运行时常量池** | **共享** | class 文件常量池的运行时表示（符号引用、字面量） | 会 | 属于方法区的一部分，随方法区报错 |
| **直接内存** | —— | NIO `DirectByteBuffer` 的实际数据 | 会 | `OutOfMemoryError: Direct buffer memory`（另有本地内存耗尽被容器 kill） |

> [!important] 面试第一反应要点
> 1. **只有 PC 不会 OOM**，这是规范里唯一写死的。
> 2. **直接内存不是运行时数据区的一部分**，它由 NIO/`Unsafe` 直接向操作系统申请，但受 JVM 参数（`-XX:MaxDirectMemorySize`）约束，所以"JVM 内存"讨论里必须提到它。
> 3. **方法区是规范里的概念，永久代/元空间是 HotSpot 的实现**。面试问"方法区在哪"，正确答法是"看版本：JDK8 之前是堆内的永久代，JDK8 之后是本地内存中的元空间"。

### 1.3 直接内存为什么不在运行时数据区

JVMS（Java 虚拟机规范）定义的五块区域只覆盖 JVM 自己管理的内存。直接内存（Direct Memory）是：

- 由 `java.nio.DirectByteBuffer` 通过 `Unsafe.allocateMemory` → `malloc` 直接向操作系统申请；
- 不参与 GC 的复制/整理，不受堆大小限制；
- 但 JVM 用一个 `AtomicLong` 记账（`Bits.totalCapacity`），超过 `-XX:MaxDirectMemorySize` 就抛 OOM。

所以它是一个"**用 JVM 参数管着、却不由 JVM 分配和回收**"的灰色地带，是线上 RSS 比 `-Xmx` 高出一大截的常见原因。

### 1.4 一个常见混淆：JVM 内存布局 ≠ Java 内存模型

| 概念 | JVM 内存区域（本篇） | Java 内存模型 JMM |
|---|---|---|
| 讨论对象 | JVM 进程如何划分内存 | 多线程下共享变量的可见性/有序性规则 |
| 关键词 | 堆、栈、元空间、TLAB | 主内存、工作内存、`volatile`、happens-before |
| 规范出处 | JVMS 第 2 章 | JLS 第 17 章 / JSR-133 |
| 常见错误 | 把"工作内存"说成"线程栈"，或者把"主内存"说成"堆" | 同左 |

细节见 [[4-多线程与内存模型]]。面试时如果被问"JMM 的工作内存是不是就是虚拟机栈"，明确回答"**不是**，工作内存是抽象模型，涵盖寄存器、CPU 缓存、写缓冲区"。

---

## 二、虚拟机栈与栈帧

### 2.1 栈帧的完整结构

```
        ┌─────────────────────────── 栈帧 Frame ───────────────────────────┐
栈顶 →  │  局部变量表 Local Variable Table   ← 参数 + 局部变量，以 slot 为单位 │
        │  操作数栈 Operand Stack            ← 字节码运算的工作区，深度编译期确定 │
        │  动态链接 Dynamic Linking          ← 指向常量池中本方法的符号引用      │
        │  方法返回地址 Return Address       ← 正常/异常退出后回到调用者的位置    │
        │  附加信息（行号表、StackMapTable…） ← 调试与字节码验证用              │
        └──────────────────────────────────────────────────────────────────┘
```

一个方法从调用到结束，对应栈帧的**入栈 → 执行 → 出栈**；栈深度 = 当前线程调用链长度。

### 2.2 局部变量表：槽位（slot）与"作用域陷阱"

- 局部变量表以 **slot（变量槽）** 为最小单位，编译期就确定了大小（`Code` 属性的 `max_locals`）。
- 32 位以内的类型（`boolean/byte/char/short/int/float/reference/returnAddress`）占 **1 个 slot**；`long/double` 占 **2 个 slot**。
- 引用类型在 64 位 HotSpot 上仍然是 **1 个 slot**（4 或 8 字节取决于压缩指针，但 slot 记账按 1 个算）。

用 `javap -v` 看局部变量表（示意）：

```java
public static String f(int a, String b) {
    long c = 1L;
    Object d = b;
    return d + a;
}
```

```
LocalVariableTable:
  Start  Length  Slot  Name   Signature
      0      20     0     a   I                  // 实例方法从 slot 1 开始，slot 0 是 this
      0      20     1     b   Ljava/lang/String;
      4      16     2     c   J                  // long 占 2 个 slot（2、3）
      8      12     4     d   Ljava/lang/Object;
```

> [!warning] 「变量还在作用域内就不算不可达」——经典面试陷阱
> 局部变量表是 **GC Roots 的一部分**，只要某个 slot 里还存着对象的引用，这个对象就**可达**，哪怕它在源码里已经"出了作用域"。
>
> ```java
> public class SlotGCTest {
>     public static void main(String[] args) {
>         {
>             byte[] placeholder = new byte[64 * 1024 * 1024];  // 64MB
>         }
>         int a = 0;      // 关键：复用 placeholder 占用的那个 slot
>         System.gc();
>     }
> }
> ```
> - **注释掉 `int a = 0;`**：`placeholder` 的 slot 没有被覆盖，仍然引用着 64MB 数组 → `System.gc()` 后老年代/堆占用不下降。
> - **保留 `int a = 0;`**：新变量复用了同一个 slot，旧引用被覆盖 → 64MB 可被回收。
>
> 三个必须说清的细节：
> 1. 前提是**解释执行**（`-Xint`）观察。JIT 编译后会做活跃性分析（liveness analysis），失效的 slot 可能被当作死变量处理，行为不保证与解释器一致。
> 2. JVMS 明确说：slot 可以被复用，也可以不复用；**规范不要求 JVM 把失效引用清空**，这是实现自由度。
> 3. 实战含义：在长生命周期方法里持有一个只在开头用到的大对象，最好显式 `xxx = null;`，或者干脆把逻辑拆成小方法（栈帧出栈最干净）。

### 2.3 操作数栈 / 动态链接 / 返回地址 / 附加信息

| 组成 | 作用 | 常见问题 |
|---|---|---|
| 操作数栈 | 字节码的求值栈，`iadd`、`invokevirtual` 等都从栈上取操作数；最大深度编译期确定（`max_stack`） | 递归中每帧的栈是独立的，不会互相污染 |
| 动态链接 | 把栈帧里指向常量池的符号引用解析为直接引用 | 方法调用多态靠它；与类加载的"解析"阶段呼应，见 [[3-类加载机制与字节码]] |
| 返回地址 | 方法正常返回（`return`/`ireturn`…）或异常退出时的恢复点 | 异常退出不会给调用者返回值，异常表决定跳转 |
| 附加信息 | 行号表（定位异常行）、`StackMapTable`（字节码校验）、局部变量调试信息 | `-g:none` 编译会丢失调试信息 |

### 2.4 栈深度与 `-Xss`

```bash
# 查看默认值（实测本机 JDK 17 / macOS aarch64：2048 KB）
java -XX:+PrintFlagsFinal -version | grep -i ThreadStackSize
#     intx ThreadStackSize = 2048 {pd product} {default}
```

| 平台 | `-Xss` 常见默认 | 说明 |
|---|---|---|
| Linux / x86_64 | 1 MB（1024 KB） | 最常见 |
| macOS / aarch64 | 2 MB | 本机实测 2048 KB |
| Windows / x64 | 由 PE 头/系统决定 | 建议用 `PrintFlagsFinal` 实测 |

- 单帧大小 = 局部变量表 + 操作数栈 + 附加信息，**编译期完全确定**，所以在固定栈大小下，"能递归多少层"是确定的。
- 线程栈是创建线程时一次性申请的（`-Xss` 越大，每个线程占用的虚拟内存/物理内存越多，能创建的线程数越少）。
- 调大 `-Xss` 只能延缓 SOE，**不能解决**无限递归；调小 `-Xss` 是"线程数不够"时的常见手段。

### 2.5 `StackOverflowError` 与 `OutOfMemoryError` 的区别（必答）

| 维度 | `StackOverflowError` | `OutOfMemoryError` |
|---|---|---|
| 触发本质 | 线程请求的**栈深度**超过允许上限（HotSpot 里 Java 栈大小固定，不动态扩展） | 申请内存失败：可能是创建线程时申请栈失败，也可能是堆/元空间/直接内存不足 |
| 典型消息 | 无（栈顶是重复的递归帧） | `unable to create new native thread` / `Java heap space` / `Metaspace` / `Direct buffer memory` |
| 真实成因 | 无限递归、递归深度过大、单个栈帧太大（方法里局部变量极多）、`-Xss` 设得过小 | 线程数过多（每个线程一份栈）、`-Xss` 过大、`ulimit -u`/`threads-max` 限制、内存不足 |
| 与 `-Xss` 的关系 | 调大能缓解 | **调大反而更容易触发**（单线程占用变多） |

> [!danger] 实战踩坑
> 线上出现 `java.lang.OutOfMemoryError: unable to create new native thread` 时，很多人的第一反应是"内存不够"。真实原因排序：
> 1. **线程数被打爆**：线程池无界、`new Thread` 泄漏、定时任务重复创建。先看 `jstack` 的线程总数，再看 `/proc/<pid>/limits` 的 `max processes`、`/proc/sys/kernel/threads-max`。
> 2. `-Xss` 设置过大（比如为了"防栈溢出"设成 4m），每个线程多占几 MB。
> 3. 容器 memory limit 太小，导致 mmap 栈内存失败。
>
> 注意：这类问题的**排查动作**属于 [[7-JVM故障排查实战]]，这里只给成因判断。

---

## 三、堆的分代布局

### 3.1 Eden : S0 : S1

```
                    堆 Heap（-Xms/-Xmx）
┌──────────────────────────────────────────────────────────────────────┐
│  新生代 Young（1/3）                          │  老年代 Old（2/3）        │
│ ┌───────────────────────┬─────┬─────┐        │                        │
│ │ Eden（8/10）           │ S0  │ S1  │        │  长期存活对象、大对象    │
│ │ ┌─────────────────┐   │(1/10)│(1/10)│       │                        │
│ │ │ TLAB │ TLAB │ …  │   │     │     │        │                        │
│ │ └─────────────────┘   │     │     │        │                        │
│ └───────────────────────┴─────┴─────┘        │                        │
└──────────────────────────────────────────────────────────────────────┘
```

| 参数 | 含义 | 本机 JDK 17 默认 |
|---|---|---|
| `-Xms` / `-Xmx` | 堆初始 / 最大 | 初始 = 物理内存的 1.5625%，最大 = 25%（`InitialRAMPercentage` / `MaxRAMPercentage`） |
| `-Xmn` | 新生代大小（≈ `-XX:NewSize` + `-XX:MaxNewSize` 同时设定） | 未设，由 NewRatio 推算 |
| `-XX:NewRatio` | 老年代 : 新生代 | 2（即新生代占堆 1/3） |
| `-XX:SurvivorRatio` | Eden : 单个 Survivor | 8（即 8:1:1） |
| `-XX:MaxTenuringThreshold` | 晋升老年代的年龄阈值 | 15（年龄只有 4 bit，最大就是 15） |

> [!tip] 关于分代比例的三条实用认知
> 1. **8:1:1 不是"新生代平均分三份"**，而是 Eden 占 80%，两个 Survivor 各占 10%。设计成两个 Survivor 是为了让复制算法有一个**空的 to-space**。
> 2. `-XX:SurvivorRatio` 若设得很大（如 100），Survivor 极小 → 存活对象一多就直接晋升老年代（survivor overflow），表现为"老年代涨得飞快"。
> 3. **G1 下不要手动设 `-Xmn`**：G1 需要根据停顿目标自适应调整新生代 Region 数量（`-XX:G1NewSizePercent` 默认 5、`-XX:G1MaxNewSizePercent` 默认 60），固定新生代会破坏可预测停顿模型。详见 [[2-GC机制深度]]。

### 3.2 TLAB 在 Eden 中的位置

TLAB 不是独立区域，而是**Eden 内部按线程切分出来的分配缓冲**：Eden 的空间被切成"TLAB 区"和"共享区"，线程优先在自己的 TLAB 里分配。详见第八章。

---

## 四、方法区、永久代与元空间（重点）

### 4.1 规范 vs 实现

| 层 | 名称 | 说明 |
|---|---|---|
| 规范（JVMS） | **方法区 Method Area** | 逻辑上属于堆，存类结构、运行时常量池、字段与方法数据、方法代码；**不要求被 GC**（但 HotSpot 会回收） |
| HotSpot 实现（JDK 7-） | **永久代 PermGen** | 位于**堆内**，受 `-XX:PermSize`/`-XX:MaxPermSize` 限制，随 Full GC 回收 |
| HotSpot 实现（JDK 8+） | **元空间 Metaspace** | 位于**本地内存（堆外）**，受 `-XX:MetaspaceSize`/`-XX:MaxMetaspaceSize` 约束 |
| 独立的一部分 | **压缩类空间 Compressed Class Space** | JDK 8+ 为压缩的 Klass 指针准备的连续虚拟地址区，默认 1GB（本机实测 `CompressedClassSpaceSize` = 1073741824） |
| 独立的一部分 | **CodeCache** | JIT 编译后的机器码，不属于元空间，见 [[5-JIT编译与运行时优化]] |

### 4.2 两次关键迁移

| 版本 | 变化 | 影响 |
|---|---|---|
| **JDK 7** | 字符串常量池（StringTable）从永久代**移到堆**；类的静态变量一并移出（HotSpot 实现变化） | 从此 `String.intern()` 不再往永久代塞数据，`PermGen space` OOM 大幅减少 |
| **JDK 8** | 永久代被**元空间**取代，类元数据移到**本地内存**；`-XX:MaxPermSize` 被忽略（启动时打印 `Ignoring option MaxPermSize; support was removed in 8.0`） | 元空间默认**没有上限**，泄漏会吃光机器内存 |

> [!important] 别把两件事混成一件
> 「字符串常量池移到堆」是 **JDK 7** 的事；「永久代 → 元空间」是 **JDK 8** 的事。面试常问"JDK8 把字符串常量池移到了元空间"——这是错的，JDK 8 时字符串常量池**已经在堆里了**，元空间只放类元数据。

### 4.3 为什么必须迁走永久代

1. **大小难以预估**：永久代必须在启动时确定上限。设小了，大量动态生成类的应用（JSP、CGLIB/ASM 代理、OSGi、热部署）频繁 `OutOfMemoryError: PermGen space`；设大了浪费，而且永久代的溢出不那么容易通过调参解决。
2. **GC 复杂度高**：HotSpot 里永久代和老年代共用一套 GC 框架与卡表逻辑，永久代的回收只能搭 Full GC 的车，回收效率低、停顿长。独立成元空间后，元空间有自己的高水位与回收策略。
3. **JRockit 合并**：Oracle 收购 BEA 后要把 JRockit 的优秀特性（无永久代）并入 HotSpot，永久代是实现层面的历史包袱。
4. **为后续收集器铺路**：G1/ZGC 的 Region/染色指针模型下，把类元数据放在堆内会让回收粒度设计变得极其别扭。

### 4.4 `-XX:MetaspaceSize` 与 `-XX:MaxMetaspaceSize`

实测（JDK 17）：

```
   size_t MetaspaceSize        = 22020096                              // 21 MB
   size_t MaxMetaspaceSize     = 18446744073709551615                  // 约等于无上限
   size_t CompressedClassSpaceSize = 1073741824                        // 1 GB
```

| 参数 | 真实含义 | 注意 |
|---|---|---|
| `-XX:MetaspaceSize` | **不是初始大小**，而是"首次触发元空间 GC 的高水位线" | 达到后触发一次 GC（通常是 Full GC），随后根据 `MinMetaspaceFreeRatio`(40)/`MaxMetaspaceFreeRatio`(70) 调整高水位。设得太小 → 启动期反复 GC；设得太大 → GC 迟迟不触发 |
| `-XX:MaxMetaspaceSize` | 元空间上限 | **默认无上限**，用本地内存，泄漏时不会抛 Java OOM，而是先把机器/容器内存吃光 |
| `-XX:MinMetaspaceFreeRatio` / `MaxMetaspaceFreeRatio` | GC 后元空间的空闲比例目标 | 控制扩容/缩容的幅度 |

> [!danger] 元空间不设上限的两种死法
> 1. **容器里被 OOMKilled（exit code 137）**：进程 RSS 超过 cgroup limit，内核直接杀进程。此时 GC 日志、heap dump 都来不及产生，只能靠监控看到 RSS 曲线陡增。这比"抛 Java OOM"难排查得多。
> 2. **宿主机被拖死**：物理机跑多个 JVM，一个元空间泄漏把 swap 打满，影响同机所有服务。
>
> 结论：**生产环境必须显式设置 `-XX:MaxMetaspaceSize`**（例如 256m~512m，按类数量估算），并把它纳入监控。

### 4.5 元空间 OOM 的两类真实成因

| 成因 | 具体场景 | 特征 |
|---|---|---|
| **动态生成大量类** | CGLIB/ASM/ByteBuddy 字节码增强（Spring AOP 代理、MyBatis Mapper、Mockito、Groovy 脚本）、`LambdaMetafactory`、反射调用链生成的 `LambdaForm`、JSON 库动态建类 | 类数量持续增长，`Metaspace` 曲线单调上升，GC 后不回落 |
| **类加载器泄漏** | 每次请求 `new URLClassLoader`、Tomcat 热部署残留、OSGi、连接池/JDBC 驱动重载、脚本引擎（Nashorn/Groovy）每次编译新建 ClassLoader | 类数量与 ClassLoader 数量同增；dump 里能看到大量重复类名 + 不同 ClassLoader |

元空间里**只有类加载器可回收时，它加载的类才能被卸载**。所以"元空间涨上去不降"的本质往往是 **ClassLoader 被某个静态字段、ThreadLocal、线程上下文类加载器、JNI 全局引用钉住了**。

---

## 五、字符串常量池

### 5.1 三个容易混淆的概念

| 名称 | 位置 | 内容 |
|---|---|---|
| class 文件常量池 | class 文件里 | 字面量、符号引用 |
| **运行时常量池** | 方法区（元空间/永久代） | class 常量池的运行时表示，符号引用在这里被解析 |
| **字符串常量池 StringTable** | **JDK7 起在堆**（JDK7 之前在永久代） | 一张哈希表，存"已被 intern 的 String 对象引用"，可用 `-XX:StringTableSize` 调桶数（本机 JDK 17 默认 65536，JDK 8 的默认值不同，以 `PrintFlagsFinal` 为准） |

### 5.2 `String.intern()` 的语义变化（必答）

| 版本 | 语义 |
|---|---|
| **JDK 6** | 池中有 equals 相等的字符串 → 返回池中对象；没有 → **把该字符串复制一份到永久代**，返回副本引用 |
| **JDK 7+** | 池中有 → 返回池中对象；没有 → **直接把堆中这个对象的引用登记到 StringTable**（不复制），返回同一个引用 |

经典代码（网上流传最广的那段）：

```java
String s1 = new StringBuilder("计算机").append("软件").toString();
System.out.println(s1.intern() == s1);   // JDK7+ : true  —— "计算机软件" 首次出现，池里登记的就是 s1 本身
String s2 = new StringBuilder("ja").append("va").toString();
System.out.println(s2.intern() == s2);   // JDK7+ : false —— "java" 在 JVM 启动阶段已被 intern
```

第二个 `false` 是理解关键：`"java"` 这个字符串在 JVM 启动（`sun.misc.Version` 等类加载）时就已经进了池，所以 `intern()` 返回的是池中的老对象，与新建的 `s2` 不是同一个。

> [!note] StringTable 的条目对字符串是**弱引用**语义
> HotSpot 在 GC 时会清理 StringTable 中已经不可达的条目（`StringTable::unlink_or_oops_do`），所以 JDK7+ 的 intern **不会**造成"永久泄漏"。
> 但 `-XX:StringTableSize` 太小会导致哈希冲突严重（长链），表现为 `intern()` 变慢、GC 时 unlink 耗时变长。高 intern 场景（大量重复的小字符串）可以适当调大。

### 5.3 `new String("a")` 创建几个对象

严格答案：**1 个或 2 个，取决于常量池里是否已有 `"a"`**。

1. 执行 `new String("a")` 时，`"a"` 是字面量 → 类加载/常量解析阶段会确保堆中有一个 `"a"` 对象并把它 intern 进 StringTable（这是第 1 个对象，可能早就存在）；
2. `new` 一定会在堆上创建一个**新的** String 对象（这是第 2 个对象）。

所以"面试标准答案两个"的前提是"该字面量此前不存在"。追问"如果池里已有呢"要能答出 1 个。

### 5.4 双等号与常量池的经典题

```java
String a = "hello";              // 字面量 → 直接指向池中对象
String b = "hello";              // 复用池中对象
String c = new String("hello");  // 新对象
String d = c.intern();           // 池中对象

a == b          // true
a == c          // false
a == d          // true
c == d          // false

String e = "he" + "llo";         // 编译期折叠成 "hello"
e == a          // true

String h = "he";
String i = h + "llo";            // 运行期拼接（JDK9+ 用 invokedynamic makeConcat）
i == a          // false
i.intern() == a // true
```

要点：
- 编译期可折叠的常量表达式（字面量、`final` 常量、常量池字符串）走同一份池对象；
- 涉及**变量**的拼接在运行期产生新对象（JDK 8 走 `StringBuilder`，JDK 9+ 走 `invokedynamic`，见 [[9-Java版本特性]]），必须 `intern()` 才与池对象相同；
- 注意本仓库的书写规范：写这个运算符时用 **==**（加粗），不要写成反引号包起来的双等号，会与本 vault 的 Dataview 行内查询语法冲突。

---

## 六、直接内存

### 6.1 为什么 NIO / Netty 要用它

| 原因 | 说明 |
|---|---|
| 少一次拷贝 | 用堆内字节数组做 IO 时，数据要先从堆内复制到堆外的临时缓冲，再交给内核；直接用 DirectBuffer 时内核可以直接读这块内存 |
| 不受 GC 搬动影响 | 堆内数组会被复制算法搬走，IO 期间地址不能变；堆外内存地址固定（这也是 JNI/`Unsafe` 需要的） |
| 不占堆、不做 GC 扫描 | 大缓冲（如 Netty 的 pooled buffer）放堆外，减少 GC 压力和对象移动成本 |
| 支持零拷贝 | `FileChannel.transferTo`、`CompositeByteBuf` 等依赖堆外/文件映射 |

细节与 Netty 内存池见 [[3-IO与网络编程]]。

### 6.2 参数与释放机制

```bash
# 本机实测：0 表示"跟随 -Xmx"
java -XX:+PrintFlagsFinal -version | grep MaxDirectMemorySize
#     uint64_t MaxDirectMemorySize = 0 {product} {default}

# 显式限制
java -XX:MaxDirectMemorySize=256m -jar app.jar
```

释放链路（JDK 8）：

```
ByteBuffer.allocateDirect(cap)
  └─ Bits.reserveMemory(size, cap)      // 记账：totalCapacity += size，超过上限则 OOM
  └─ Unsafe.allocateMemory(size)        // 真正的 malloc
  └─ Cleaner.create(this, new Deallocator(base, size, cap))
        // Deallocator 是静态内部类，持有 base 地址而不是 ByteBuffer 本身
```

关键点：
- 这块内存**不被 GC 直接管理**：GC 只管堆里的 `DirectByteBuffer` 对象；只有当它不可达以后，`Cleaner` 才会在引用处理阶段执行 `Unsafe.freeMemory`。
- 因此释放是**滞后**的：需要一次 GC 让 ByteBuffer 变成不可达 + 引用处理器线程跑起来。
- Netty 的 `ByteBuf` 是**引用计数**的，必须 `release()`/`ReferenceCountUtil.release()`，不能指望 GC。

### 6.3 `OutOfMemoryError: Direct buffer memory` 的成因

| 成因 | 现象 | 定位手段 |
|---|---|---|
| `ByteBuf` 没 release | 堆内存平稳，RSS 单调上涨，最终 `Direct buffer memory` OOM | Netty 泄漏检测 `-Dio.netty.leakDetection.level=paranoid`；或看传入的 `ResourceLeakDetector` 日志 |
| `-XX:MaxDirectMemorySize` 没设 | 默认等于 `-Xmx`，堆外 + 堆内总量超过容器 limit → OOMKilled | `NMT`（`-XX:NativeMemoryTracking=summary` + `jcmd <pid> VM.native_memory`）看 internal/other 区 |
| Cleaner 迟迟不执行 | 堆很空闲、老年代不满，Full GC 很久不发生 → 堆外内存不释放 | GC 日志确认 Full GC 频率；堆外高峰与 Full GC 时间点对不上 |
| 申请过大单块 | 一次申请超过上限 | 检查 `allocateDirect` 的 size 来源（如按请求体大小分配） |

### 6.4 与 `-XX:+DisableExplicitGC` 的致命组合（高频实战坑）

`Bits.reserveMemory` 在**第一次申请失败**时会调用 `System.gc()` 尝试触发回收，然后再重试。而 `-XX:+DisableExplicitGC` 会让 `System.gc()` 变成 **no-op**：

- 堆内压力不大 → 自然的 GC（Young GC）频繁但没有 Full GC → 已经不可达的 `DirectByteBuffer` 迟迟等不到引用处理；
- 堆外记账持续增长 → 直接 `OutOfMemoryError: Direct buffer memory`。

正确做法（三选一）：
1. **不要用 `-XX:+DisableExplicitGC`**（它原本是为了防框架乱调 `System.gc()` 造成 Full GC 停顿）；
2. 用 `-XX:+ExplicitGCInvokesConcurrent`，让显式 GC 走并发收集（G1 支持该参数），既能回收又不会长时间 STW；
3. 改用显式资源管理（`try-with-resources` / Netty `release()`），并在业务上把 `-XX:MaxDirectMemorySize` 设成实际需要值。

> [!warning] 一句话记忆
> `DisableExplicitGC` + 大量 DirectBuffer + 堆压力小 = 稳定的 `Direct buffer memory` OOM。这三个条件同时出现时，先怀疑这个组合，而不是"内存泄漏"。

---

## 七、对象的创建过程

### 7.1 六个步骤

```
① 类加载检查       new 指令 → 常量池定位类的符号引用 → 检查是否已加载/解析/初始化
                   （未加载则先触发类加载，见 [[3-类加载机制与字节码]]）
② 分配内存         对象所需大小在类加载完成后就已确定
                   → 指针碰撞（内存规整）或空闲列表（内存不规整）
                   → 并发安全由 CAS 重试 或 TLAB 保证
③ 零值初始化       把分配到的内存全部置 0（不含对象头）
                   → 这就是"成员变量可以不赋初值直接用"的原因
④ 设置对象头       Mark Word（hashCode/GC 年龄/锁状态）、Klass Pointer、数组长度
⑤ 执行 <init>      构造方法：父类构造 → 实例变量显式初始化/实例代码块 → 构造体
⑥ 引用入栈         把引用压入操作数栈（字节码层面 dup + astore）
```

> [!tip] 「零值初始化」与「显式初始化」的区分
> 第 ③ 步是 JVM 层面的零值（`int` 为 0、引用为 null）；第 ⑤ 步才是 `private int a = 1;` 这类显式赋值。
> 所以 `static` 变量如果只声明不赋值，一定拿到 0/null；而局部变量**必须显式赋值**才能用（编译期检查，因为局部变量表不会自动清零，见前面 slot 复用陷阱）。

### 7.2 分配方式：指针碰撞 vs 空闲列表

| 方式 | 前提 | 过程 | 使用它的收集器 |
|---|---|---|---|
| **指针碰撞 Bump the Pointer** | 内存**规整**：已用在一侧、空闲在另一侧 | 一个指针作为分界点，分配 = 指针向空闲侧移动对象大小 | 带压缩/复制的收集器：Serial、ParNew、Parallel Scavenge（新生代）、Serial Old/Parallel Old（整理后） |
| **空闲列表 Free List** | 内存**不规整** | 维护可用内存块列表，分配时找一块足够大的，并更新列表 | 标记-清除类：**CMS 的老年代** |
| 线性分配（TLAB 内） | 线程私有缓冲内规整 | 就是指针碰撞的"无锁版" | 所有支持 TLAB 的收集器 |

**判断规则**：分配方式取决于 **GC 是否具备压缩整理（Compact）能力**。所以"用 CMS 时老年代用空闲列表，用 G1/Parallel 时用指针碰撞"是能自洽解释的。

### 7.3 并发分配安全

即使堆是规整的，多线程同时 `new` 也会出现"A 线程刚判断完指针，B 线程就把它移动了"的问题。两种解法：

| 方案 | 机制 | 优缺点 |
|---|---|---|
| **CAS + 失败重试** | 用 `Atomic::cmpxchg` 原子更新分配指针，失败就重试 | 无锁但高并发下自旋浪费 CPU；大对象分配只能走这条路 |
| **TLAB** | 每个线程先在自己私有的 Eden 缓冲里分配，用完再换一块 | 快路径几乎无同步开销；代价是空间浪费（见第八章） |

HotSpot 是**两者结合**：优先 TLAB，TLAB 不够用时退化到共享 Eden 并加锁/CAS，分配大对象时只能加锁。

---

## 八、TLAB（重点）

### 8.1 是什么 / 为什么能加速

**TLAB（Thread Local Allocation Buffer）**：在线程初始化时，在 **Eden 内**为它划分一小块私有内存；该线程的新对象优先在这里分配。

为什么快：
1. **避免全局指针竞争**：堆分配指针是全局共享资源，CAS 在几十上百个线程下会成为热点。
2. **快路径极短**：`top + size <= end` 判断 → 返回旧 top → 推进 top。本质上是几条指令 + 一次内存预取，JIT 还能把它内联成指针加法。
3. **更好的缓存局部性**：同一线程分配的对象在内存上相邻。

TLAB 的源码路径（JDK 8 `instanceKlass.cpp` / `threadLocalAllocBuffer.cpp`）：

```
InstanceKlass::allocate_instance
  → CollectedHeap::obj_allocate
  → GenCollectedHeap::mem_allocate
  → DefNewGeneration::allocate
  → allocate_from_tlab         // 快路径：TLAB 内指针碰撞
  → allocate_from_tlab_slow    // 慢路径：refill 或退回 Eden 共享分配
```

### 8.2 参数（本机 JDK 17 实测默认值）

| 参数 | 默认 | 作用 |
|---|---|---|
| `-XX:+UseTLAB` | true | 是否启用 TLAB |
| `-XX:TLABSize` | 0（自动） | TLAB 初始大小；0 表示由 JVM 按 Eden 与线程数自适应 |
| `-XX:+ResizeTLAB` | true | 允许在运行期动态调整每个线程的 TLAB 大小 |
| `-XX:TLABWasteTargetPercent` | 1 | TLAB 浪费量的上限 = **Eden 的 1%**；超过则缩小 TLAB 大小 |
| `-XX:TLABWasteIncrement` | 4 | 每次分配失败后浪费容忍度的增量（百分比） |
| `-XX:MinTLABSize` | 2048 | TLAB 最小字节数 |

### 8.3 分配路径与"TLAB 浪费（refill）"

```
线程分配对象 obj(size)
├── size > TLAB 剩余空间？
│   ├── 否 → fast path：top += size，返回（无锁）
│   └── 是 → slow path
│         ├── size > TLAB 最大容量（大对象）？→ 直接走 Eden 共享分配 / 老年代
│         ├── 剩余空间 < 容忍阈值（默认最多浪费 Eden 的 1%）→ 丢弃剩余，申请新 TLAB（refill）
│         │      └── 被丢弃的零头就是 tlab_waste，无法给别的线程用（无锁的代价）
│         └── 剩余空间还够浪费 → 本次对象退到 Eden 共享分配（加锁）
```

关键理解：
- **refill 时旧 TLAB 的零头被浪费**，所以 TLAB 太小 → refill 频繁（分配变慢 + 浪费多）；TLAB 太大 → 浪费比例高、GC 后 Eden 回收不干净。
- `-XX:TLABWasteTargetPercent=1` 就是"总体浪费不超过 Eden 的 1%"这个约束，JVM 用它反推每个 TLAB 的目标大小。
- 用 `-XX:+PrintTLAB`（debug 版本）或 JFR 的 `jdk.ObjectAllocationInNewTLAB` / `jdk.ObjectAllocationOutsideTLAB` 事件可以观测 TLAB 分配与浪费。

### 8.4 与"对象优先在 Eden 分配"的关系

这两句话不冲突，是**两层**关系：

| 层次 | 语义 | 决定因素 |
|---|---|---|
| 语义层 | 新对象优先在**新生代 Eden** 分配 | `-Xmn` / `NewRatio` / `SurvivorRatio` |
| 实现层 | Eden 内的分配尽量在**线程私有的 TLAB** 里完成 | `UseTLAB` / TLAB 系列参数 |

所以 TLAB 失效（`-XX:-UseTLAB`）不会改变对象的代数归属，只会让分配路径退化到共享 Eden 的加锁分配，在高并发下表现为明显的分配变慢。

---

## 九、对象的内存布局

### 9.1 总览

```
┌──────────────────────── 对象在堆中的布局（64 位、开启压缩指针） ───────────────────────┐
│  对象头 Object Header                                                                  │
│   ┌───────────────────────────────┬──────────────────────┬───────────────────────┐   │
│   │ Mark Word (8 B)                │ Klass Pointer (4 B)  │ 数组长度 (4 B，仅数组) │   │
│   │ hashCode/年龄/锁状态            │ 指向元空间的 InstanceKlass │ int 长度         │   │
│   └───────────────────────────────┴──────────────────────┴───────────────────────┘   │
│  实例数据 Instance Data（字段按宽度分组重排，父类字段在前）                             │
│  对齐填充 Padding（补齐到 8 字节的整数倍）                                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Mark Word 的位分配（必答）

64 位 Mark Word 在不同锁状态下复用同一块 8 字节空间：

| 状态 | 内容（高位 → 低位） | 锁标志位（低 2 位） |
|---|---|---|
| **无锁**（未计算 identity hash） | unused(25) + identity_hashcode(31) + unused(1) + 分代年龄(4) + 偏向锁位(1) | 01 |
| **偏向锁**（JDK 8~14 默认开，JDK 15 起默认关） | 线程 ID(54) + epoch(2) + unused(1) + 分代年龄(4) + 偏向锁位 1 | 01 |
| **轻量级锁** | 指向栈上锁记录 Lock Record 的指针(62) | 00 |
| **重量级锁** | 指向 ObjectMonitor 的指针(62) | 10 |
| **GC 标记** | GC 用来存放标记/转发信息（对象被复制后原位置放 forwarding pointer） | 11 |

4 个必须掌握的细节：
1. **identity hashCode 是惰性写入的**：只有调用了 `Object.hashCode()` 或 `System.identityHashCode()` 才会把 hash 写进 Mark Word。`hashCode()` 被重写但仍调 `super.hashCode()` 也算。
2. **hash 与偏向锁互斥**：对象一旦算过 identity hash，就再也无法进入偏向锁（那 31 位被 hash 占了），必须先撤销偏向。
3. **分代年龄只有 4 位**：所以 `-XX:MaxTenuringThreshold` 最大是 15，设 16 会被拒。
4. **偏向锁的版本变化**：JDK 15（JEP 374）默认禁用偏向锁，JDK 18 移除了相关开关。所以"偏向锁/epoch/撤销"这套内容在新版本上主要是**面试与历史包袱**，但 JDK 8 生产系统里仍然是真实性能点。锁的实现细节见 [[6-JUC并发工具]]。

### 9.3 类型指针与压缩指针

- **Klass Pointer** 指向元空间中的 `InstanceKlass`，JVM 靠它判断"这个对象是哪个类的"（反射、虚方法分派、`instanceof` 都依赖它）。
- **压缩指针**分两套：
  - `-XX:+UseCompressedOops`：压缩**对象引用**（4 字节），本机默认 true（ergonomic）；
  - `-XX:+UseCompressedClassPointers`：压缩对象头里的 **Klass 指针**（4 字节），本机默认 true，对应的地址空间就是 `CompressedClassSpaceSize`（默认 1GB）。
- 为什么是「堆小于 32GB 才生效」：压缩 oop 用 32 位存地址，**利用对象 8 字节对齐的特性左移 3 位**（`oop = base + (n << 3)`），所以可寻址范围是 2^32 × 8 B = **32 GB**。堆超过 32GB 时压缩 oop 自动关闭。
- 变通手段：`-XX:ObjectAlignmentInBytes=16` 可以把范围扩到 64GB，但代价是**最小对象粒度变成 16 字节**，小对象变多时反而更浪费。

验证方式：

```bash
java -XX:+PrintFlagsFinal -version | grep -E "UseCompressedOops|UseCompressedClassPointers"
# JDK 8 上还有 -XX:+PrintCompressedOopsMode（后续版本已移除）
# JDK 9+ 可用统一日志观察模式
java -Xlog:gc+heap+coops=info -Xmx4g -version
# [0.005s][info][gc,heap,coops] Compressed Oops mode: Zero based, Oop shift amount: 3   ← 示意
```

### 9.4 为什么"堆大了反而更慢"

从 32GB 提到 40GB，很多团队会发现：

| 变化 | 后果 |
|---|---|
| 引用字段从 4 字节变 8 字节 | 同样逻辑对象图占用内存上升（引用密集场景非常明显） |
| 对象变大 → 缓存行能装下的对象变少 | CPU cache 命中率下降，遍历类操作（如 GC 并发标记、业务遍历大集合）变慢 |
| 并发标记/复制的扫描量上升 | GC 绝对耗时上升，停顿变长 |
| 堆大 → 单次 Full GC 更久 | "堆大了但吞吐降了"的经典现象 |

实践建议：
- 单实例堆**尽量控制在 32GB 以内**，需要更大内存时优先**多实例 + 负载均衡**（每个实例 16~24GB），而不是单实例 64GB；
- 用 `-XX:MaxRAMPercentage=25`（本机默认 25%）配合容器 limit 比硬编码 `-Xmx` 更省心，但要显式设上限，避免 JVM 按宿主机内存算；
- 如果确实需要 32GB 以上且是引用稠密型负载，考虑 `-XX:ObjectAlignmentInBytes=16`（需重新评估小对象开销）。

### 9.5 实例数据与字段重排序

- HotSpot 会**把字段按宽度分组重排**（long/double → int/float → short/char → byte/boolean → 引用），并在父类字段与子类字段之间填充，目的是减少 padding。
- `-XX:+CompactFields`（默认开）允许把子类的小字段塞进父类字段对齐留下的空隙。
- **结论：手动按"从大到小"排布 Java 字段通常没有收益**（这点和 C/C++ 完全不同，JVM 已经替你做了）。真正能省内存的是"减少对象数量/用基本类型数组替换对象数组"。

用 JOL 观测（示意）：

```java
public class User {
    private int id;          // 4
    private boolean active;  // 1
}
// System.out.println(ClassLayout.parseInstance(new User()).toPrintable());
```

```
com.example.User object internals:
 OFFSET  SIZE      TYPE DESCRIPTION              VALUE
      0     4           (object header)          01 00 00 00 (Mark Word 低 4 字节)
      4     4           (object header)          00 00 00 00 (Mark Word 高 4 字节)
      8     4           (object header)          c0 3f 01 f8 (Klass Pointer，压缩后 4 字节)
     12     4       int User.id                   0
     16     1   boolean User.active               false
     17     7           (loss due to the next object alignment)
Instance size: 24 bytes
Space losses: 0 bytes internal + 7 bytes external = 7 bytes total
```

依赖：`org.openjdk.jol:jol-core`，或直接用 `jol-cli` 的 `java -jar jol-cli.jar internals <class>`。

### 9.6 对齐填充

- 默认 `-XX:ObjectAlignmentInBytes=8`（本机实测 8），即**对象大小必须是 8 字节的整数倍**。
- 目的：让字段/引用在内存中自然对齐，避免跨缓存行访问；也是压缩指针左移 3 位寻址的前提。
- 极端例子：`new Object()` 在开启压缩类指针时，对象头 = 8（Mark Word）+ 4（Klass）= 12 字节，填充 4 字节 → **16 字节**。"一个空对象占 16 字节"就是这么来的。

---

## 十、对象的定位方式：句柄 vs 直接指针

| 方式 | 结构 | 访问开销 | 对象移动时的代价 |
|---|---|---|---|
| **句柄池 Handle** | 栈引用 → 句柄（含实例指针 + 类型指针）→ 对象实例 | 两次间接寻址 | 只需更新句柄表中的实例指针，栈上的引用不用动 |
| **直接指针 Direct Pointer** | 栈引用 → 对象实例（对象头里存类型指针） | 一次间接寻址 | 需要更新所有指向该对象的引用（由 GC 用 forwarding pointer 完成） |

**HotSpot 使用直接指针**。原因：
1. 对象访问（读写字段）是**最高频**操作，省一次内存间接寻址意味着实打实的吞吐提升；
2. 对象移动发生在 GC 期间，本来就处于 STW/并发标记的受控环境，更新引用是 GC 的本职工作（复制算法靠 forwarding pointer 就地更新）；
3. 句柄池自己还要占内存、破坏局部性。

---

## 十一、内存分配策略

| # | 策略 | 触发条件 | 关键参数 | 为什么这么设计 |
|---|---|---|---|---|
| 1 | **对象优先在 Eden 分配** | 所有 `new`（TLAB 快路径优先） | `-Xmn` / `-XX:NewRatio` / `-XX:SurvivorRatio` | 朝生夕死的对象占绝大多数，把小对象集中放在 Eden，Minor GC 一次全清 |
| 2 | **大对象直接进老年代** | 对象大小 ≥ 阈值 | `-XX:PretenureSizeThreshold`（默认 0 = 不启用） | 避免大对象在 Eden/S0/S1 之间反复复制（复制成本与对象大小成正比） |
| 3 | **长期存活对象晋升** | 每熬过一次 Minor GC，年龄 +1；年龄 > 阈值进入老年代 | `-XX:MaxTenuringThreshold`（默认 15） | 熬过多次 GC 的是"长寿对象"，放老年代减少新生代复制量 |
| 4 | **动态年龄判定** | Survivor 中年龄 1..n 的对象大小累计超过 Survivor 空间的 `TargetSurvivorRatio`（默认 50%）→ 年龄 ≥ n 的直接晋升 | `-XX:TargetSurvivorRatio` | 避免 Survivor 溢出（overflow）时"被动晋升"，主动提前晋升更可控 |
| 5 | **空间分配担保** | Minor GC 前检查老年代最大连续可用空间 | `-XX:HandlePromotionFailure`（JDK 6u24 起已不再使用） | Minor GC 的前提是"最坏情况下所有存活对象都能进老年代"，否则必须先 Full GC 腾空间 |

三条容易答错的细节：

1. **`-XX:PretenureSizeThreshold` 只对 Serial 和 ParNew 有效**，Parallel Scavenge 会忽略它；G1 用的是另一套规则（对象 ≥ Region 大小的一半 → Humongous，直接在老年代 Region 分配）。所以"大对象直接进老年代"在不同收集器下行为不同，见 [[2-GC机制深度]]。
2. **动态年龄判定的准确表述**是："从小到大累计各年龄对象的大小，当累计值超过 Survivor 空间的 `TargetSurvivorRatio`(50%) 时，取该年龄为新的晋升阈值，且不超过 `MaxTenuringThreshold`"。不要背成"超过一半就全部晋升"。
3. **空间分配担保的现代规则**：JDK 6u24 之后 `HandlePromotionFailure` 不再生效，只要"老年代连续可用空间 > 新生代对象总大小"或"> 历次晋升的平均大小"，就允许 Minor GC，否则先 Full GC。

---

## 十二、对象一定在堆上吗？

这是"分配视角"最容易被问倒的一题。

**规范与语义层的答案**：不是。如果 JIT 通过**逃逸分析**证明一个对象不会逃逸出方法/线程，就可以：
- **标量替换（Scalar Replacement）**：把这个对象拆成若干基本类型/引用局部变量，根本不在堆上创建对象；
- **锁消除（Lock Elision）**：对象私有 → 它上面的同步操作可以直接删掉；
- 教科书式的**栈上分配**：把对象放栈帧里，随方法出栈自动销毁。

**HotSpot 的落地情况**：HotSpot 实际生效的是**标量替换 + 锁消除**；被拆散后对象头、对象引用都不存在了，宏观效果等同于"栈上分配"，所以很多资料直接把这个效果叫栈上分配。

**必须强调的三点**：
1. 这是**优化**，不是**语义**。只要对象被发布（返回、赋给成员/静态字段、传给未知方法、被其他线程读到），就必须在堆上并被 GC 管理。
2. 优化只在 **C2 编译后**生效，需要预热；解释执行（`-Xint`）或刚启动时看不到效果。
3. 相关参数：`-XX:+DoEscapeAnalysis`（默认开）、`-XX:+EliminateAllocations`（标量替换，默认开）、`-XX:+EliminateLocks`（锁消除，默认开）。用 `-XX:-DoEscapeAnalysis` 做对照实验是很好的演示手段。

优化细节、`PrintEliminateAllocations` 等诊断开关，全部见 [[5-JIT编译与运行时优化]]。

---

## 十三、四种引用

### 13.1 总览（必答表）

| 引用类型 | 类 | 回收时机 | 典型用途 | 主要风险 |
|---|---|---|---|---|
| **强引用** | 普通赋值 | 只要 GC Roots 可达就**永不回收**，宁可抛 OOM | 默认场景 | 无意识的长生命周期引用 = 内存泄漏 |
| **软引用** | `SoftReference` | 内存不足时（GC 后按空闲堆空间与 LRU 策略决定） | 内存敏感的缓存（图片、解析结果） | 回收时机不可控，可能"该清不clean、不该清就清" |
| **弱引用** | `WeakReference` | **每次 GC** 只要发现（且只被弱引用持有）就回收 | `ThreadLocalMap` 的 key、`WeakHashMap`、缓存 key、监听器列表 | 随时可能变 null，必须判空/重建 |
| **虚引用** | `PhantomReference` | 任何时候都可能被清除；`get()` **永远返回 null** | 对象被回收的**通知**，堆外内存释放 | 唯一用途是排队，不能访问对象 |

### 13.2 软引用：什么时候不该用它做缓存

```java
// 典型误用：把软引用当"自动清理的缓存"
private final Map<String, SoftReference<byte[]>> cache = new ConcurrentHashMap<>();

public byte[] get(String key) {
    SoftReference<byte[]> ref = cache.get(key);
    byte[] v = (ref == null) ? null : ref.get();
    if (v == null) {
        v = load(key);
        cache.put(key, new SoftReference<>(v));   // key 永远不会被移除 -> map 本身泄漏
    }
    return v;
}
```

四个问题：
1. **回收判定不是"业务内存不足"，而是"GC 后的空闲堆空间"**。HotSpot 用 `-XX:SoftRefLRUPolicyMSPerMB`（默认 1000）决定保留时间：
   保留窗口 ≈ 空闲堆 MB 数 × 1000 ms。堆空闲 1GB → 约 1000 秒不清理；老年代压力大时才被清。堆越大，软引用缓存越"赖着不走"。
2. **Map 的 key 是强引用**，`SoftReference` 被清了但 key 还在 → map 持续膨胀，这就是"缓存自己泄漏"。
3. **不是精确 LRU**：`SoftReference` 内部带时间戳，清除策略是近似 LRU，不能当业务淘汰策略。
4. **现代实践**：用 Caffeine/Guava 的 `maximumSize` + `expireAfterWrite/Access` + `weakKeys/softValues` 组合，让淘汰策略显式可控；`softValues()` 只能作为"内存兜底"，不能作为唯一淘汰手段。

### 13.3 弱引用：`ThreadLocalMap` 与 `WeakHashMap`

**为什么 `ThreadLocalMap` 的 Entry 要用弱引用做 key**：

```java
static class Entry extends WeakReference<ThreadLocal<?>> {
    Object value;                       // value 是强引用！
    Entry(ThreadLocal<?> k, Object v) { super(k); value = v; }
}
```

引用链（泄漏路径）：

```
Thread（线程池中长期存活）
  └─ ThreadLocalMap
       └─ Entry[] table
            └─ Entry(key = WeakReference<ThreadLocal>，value = 强引用 → 业务对象)
```

- `ThreadLocal` 实例被业务代码置为 null/被回收后，Entry 的 key 变 null（"stale entry"），但 **value 仍被 Entry 强引用** → value 无法回收；
- `ThreadLocalMap` 只在 `get/set/remove` 时**顺手**清理 stale entry（`expungeStaleEntry`），如果你再也不碰这个 ThreadLocal，清理就永远不会发生；
- 线程池里的线程活到进程结束 → 泄漏是**永久**的。

结论：**必须 `try { ... } finally { threadLocal.remove(); }`**。key 用弱引用只是"提供了自愈的可能"，不等于安全。

**`WeakHashMap`**：key 被回收后 Entry 会被 `ReferenceQueue` 机制清理（`expungeStaleEntries`），适合"以对象身份作为 key 的旁路缓存"，但同样要注意 value 反向引用 key 会造成循环强引用（value 引用 key 时 key 永远不死）。

> [!tip] 关联
> `ThreadLocal` 的完整用法与线程池实践见 [[6-JUC并发工具]]；引用可见性与 happens-before 见 [[4-多线程与内存模型]]。

### 13.4 虚引用与 `ReferenceQueue`

```java
ReferenceQueue<Object> queue = new ReferenceQueue<>();
Object obj = new Object();
PhantomReference<Object> pr = new PhantomReference<>(obj, queue);   // 必须传 queue
System.out.println(pr.get());   // 永远 null，即使 obj 还活着
obj = null;
System.gc();
Reference<?> ref = queue.remove(5000);   // 对象被回收后，虚引用被入队
```

- 虚引用的**唯一价值**：在对象被 GC 回收时收到"通知"，从而做资源清理（尤其是堆外资源）。
- `ReferenceQueue` 的四个状态（面试可加分的细节）：

| 状态 | 含义 |
|---|---|
| Active | 引用已创建，referent 可达 |
| Pending | GC 判定 referent 已死，引用对象被挂到 pending 链表，等待 `ReferenceHandler` 线程处理 |
| Enqueued | 引用对象已进入 `ReferenceQueue`，可以被 `poll()`/`remove()` 取到 |
| Inactive | 引用对象状态终态，不可再变 |

- 弱引用/软引用：referent 被清除**之后**入队；虚引用：referent 被判定可回收（`finalize` 之后）入队。清理动作发生在 `ReferenceHandler` 线程 → 这意味着**清理与 GC 是异步的**，不能假设"GC 完就立刻释放"。

### 13.5 `Cleaner`：虚引用的现代封装

`java.lang.ref.Cleaner`（JDK 9+；JDK 8 是 `sun.misc.Cleaner`，同样是 `PhantomReference` 子类）：

```java
public class NativeResource implements AutoCloseable {
    private static final Cleaner CLEANER = Cleaner.create();

    /** 清理动作必须是静态类或独立对象，绝不能持有 NativeResource 实例 */
    private static class Cleanup implements Runnable {
        private final long handle;
        Cleanup(long handle) { this.handle = handle; }
        @Override public void run() { nativeFree(handle); }   // 示意：释放本机资源
    }

    private final long handle;
    private final Cleaner.Cleanable cleanable;

    public NativeResource() {
        this.handle = nativeAlloc();
        this.cleanable = CLEANER.register(this, new Cleanup(handle));
    }

    @Override public void close() { cleanable.clean(); }      // 显式释放，幂等
}
```

**最经典的错误**：把 `Cleanup` 写成非静态内部类或匿名内部类（`() -> nativeFree(this.handle)`），于是 `Cleaner → Runnable → this` 构成强引用链 → 对象永远不可回收，清理永远不执行。这也是"用了 Cleaner 还是堆外泄漏"的最常见原因。

---

## 十四、对象回收前的最后挣扎：`finalize` 与 `Cleaner`

### 14.1 `finalize()` 的两次标记流程

```
① 可达性分析发现对象不可达
      ↓
② 判断：是否需要执行 finalize？
   ├─ 没重写 finalize，或已被调用过 → 直接回收
   └─ 重写了且未执行 → 放入 F-Queue
      ↓
③ 由 JVM 创建的 FinalizerThread（低优先级）执行 finalize()
      ↓
④ GC 对 F-Queue 中的对象做第二次小规模标记
   ├─ 对象在 finalize 里重新被 GC Roots 引用（"复活"）→ 移出待回收集合，本次不回收
   └─ 否则 → 真正回收
```

### 14.2 为什么"不保证执行"且"不推荐"

| 问题 | 说明 |
|---|---|
| 执行时机不确定 | GC 不等待 finalize 完成；`FinalizerThread` 优先级低，可能长时间抢不到 CPU |
| 可能根本不执行 | 程序退出前、GC 压力不足时，F-Queue 里的对象可能一直没被处理 |
| 异常被吞 | `finalize()` 抛出的异常会被忽略，且**不会中断**其他对象的 finalize，问题被静默掩盖 |
| **队列阻塞放大故障** | 某个对象的 `finalize()` 卡住（等锁、IO、死循环）→ 整个 FinalizerThread 卡住 → F-Queue 无限增长 → 大量对象堆积 → `Java heap space` OOM。这是"OOM 但堆 dump 里全是 Finalizer 队列对象"的经典现场 |
| 复活只给一次机会 | 对象被 finalize 复活后，第二次不可达时**直接回收**（`finalize` 不会被再次调用） |
| 性能损耗 | 有 finalize 的对象分配与回收都更慢（需要注册/排队） |
| 版本趋势 | JDK 9：`Object.finalize()` 标记 `@Deprecated`；**JDK 18（JEP 421）** 正式弃用 finalization for removal，并提供 `--finalization=disabled` 运行开关 |

### 14.3 正确替代：`Cleaner` + `AutoCloseable`

| 方案 | 适用 | 特点 |
|---|---|---|
| `try-with-resources` / 显式 `close()` | 一切可控生命周期的资源 | **首选**，确定性释放 |
| `java.lang.ref.Cleaner` | 兜底（调用者忘了 close 时） | 基于虚引用，异步、不保证及时，但不会像 finalize 那样阻塞全局队列（每个 Cleaner 有自己的线程） |
| `finalize()` | 无 | 不要在新代码中使用 |

**与直接内存的呼应**：`DirectByteBuffer`/`MappedByteBuffer` 的释放就是 `Cleaner`（JDK 8 是 `sun.misc.Cleaner` + `Deallocator` 静态内部类）。所以第六章讲的"堆外内存靠 GC 触发 Cleaner 释放"和这里的机制是同一套东西。详见 [[3-IO与网络编程]]。

---

## 十五、常见坑表

| # | 坑 | 现象 | 根因 | 正解 |
|---|---|---|---|---|
| 1 | 栈溢出只会调 `-Xss` | 调大后 `unable to create new native thread`，或线程池容量骤降 | `-Xss` 是**每线程**开销，调大 → 单线程内存变多、可创建线程数变少 | 先定位深调用/递归与单帧过大；线程数多的服务反而要调小 `-Xss` |
| 2 | 元空间不设上限 | 容器 OOMKilled(137) 而非 Java OOM；RSS 陡增无 dump | `MaxMetaspaceSize` 默认无限制、用本地内存 | 显式设 `-XX:MaxMetaspaceSize`，监控元空间曲线与类加载器数量 |
| 3 | 直接内存未设上限 | 堆平稳但 RSS 上涨，最后 `Direct buffer memory` | 默认 = `-Xmx`，且释放滞后 | 设 `-XX:MaxDirectMemorySize`，Netty 开泄漏检测并保证 `release()` |
| 4 | 堆超 32G 关掉压缩指针 | "堆从 32G 提到 40G，吞吐反而降、GC 更慢" | 引用 4→8 字节，cache 命中率下降 | 单实例堆控制在 32G 内；用多实例；或 `ObjectAlignmentInBytes=16` |
| 5 | `finalize` 复活对象 | 对象"回收不掉"，堆 dump 里全是待 finalize 对象 | finalize 中重新建立引用；FinalizerThread 阻塞 | 彻底不用 finalize，改 Cleaner/显式 close |
| 6 | 在递归里建大数组 | 很快 `StackOverflowError` 或内存爆 | 每层栈帧都持有大对象，帧大 + 对象多 | 大对象移到循环/方法外，递归改迭代 |
| 7 | `Integer` 缓存导致对象身份误判 | `a == b` 一会儿 true 一会儿 false | `Integer.valueOf` 缓存 -128~127 | 装箱对象比较永远用 `equals`/`Objects.equals`；`-XX:AutoBoxCacheMax` 只影响上界且不通用 |
| 8 | 局部变量表 slot 未复用 | 出了作用域的大对象仍不被回收 | 局部变量表是 GC Root，旧引用还在 slot 里 | 大对象显式置 null 或拆小方法；不要依赖"作用域结束就释放" |
| 9 | 把 `-Xmn` 用在 G1 上 | Young GC 频率异常、Mixed GC 不按预期、停顿目标失效 | G1 需要自适应调整新生代 | G1 下不设 `-Xmn`，用 `MaxGCPauseMillis` 与 `G1NewSizePercent`/`G1MaxNewSizePercent` |

> [!example] 第 4 条的现场对照实验（面试可讲）
> 同一份引用密集型程序，`-Xmx30g` 与 `-Xmx40g` 各跑一遍：
> - 40G 时用 `-XX:+PrintFlagsFinal` 能看到 `UseCompressedOops` 变成 false；
> - 同样的负载下老年代占用明显更高、GC 的并发标记阶段耗时更长；
> - 结论不是"堆越大越好"，而是"**32GB 是 HotSpot 分代堆的一个隐性门槛**"。

---

## 十六、必答清单

> [!question] 面试必答四连（先给一句话答案，再展开）
> **Q1：Metaspace 与永久代的区别？**
> 两者都是 HotSpot 对 JVMS 里"方法区"的**实现**。永久代（JDK 7-）在**堆内**，受 `-XX:MaxPermSize` 限制，随 Full GC 回收；元空间（JDK 8+）在**本地内存**，受 `-XX:MetaspaceSize`（首次 GC 高水位，实测默认 21MB）/`-XX:MaxMetaspaceSize`（默认无上限）约束。注意两件独立的事：**JDK 7 把字符串常量池移到堆**，**JDK 8 把类元数据移到元空间**。详见 §4。
>
> **Q2：TLAB 是什么？**
> Thread Local Allocation Buffer：Eden 内按线程切分的私有分配缓冲，让新对象走"指针碰撞"的快路径而无需 CAS 竞争全局分配指针；快路径几乎无同步开销，代价是 refill 时的零头浪费（`-XX:TLABWasteTargetPercent` 默认 1%，即最多浪费 Eden 的 1%）。默认开启（`-XX:+UseTLAB`），本机实测 true。详见 §8。
>
> **Q3：Mark Word 与锁状态？**
> 64 位 Mark Word 是 8 字节，在无锁（hash 31 位 + 分代年龄 4 位）、偏向锁（线程 ID 54 位 + epoch 2 位）、轻量级锁（指向栈上 Lock Record 的指针）、重量级锁（指向 ObjectMonitor 的指针）、GC 标记（转发指针）之间**复用**同一块空间，用低 2 位标志区分（01/00/10/11）。identity hash 惰性写入，写入后无法进入偏向锁；分代年龄 4 位决定 `MaxTenuringThreshold` 上限 15。JDK 15 起偏向锁默认关闭，JDK 18 移除相关开关。详见 §9.2。
>
> **Q4：对象一定在堆上吗？**
> **语义上不一定，实现上要分情况**。逃逸分析 + 标量替换可以把不逃逸的对象拆成局部变量（HotSpot 实际生效的是标量替换与锁消除，效果等价于栈上分配），但这是 **C2 的优化**，不影响语义：对象一旦被发布就必然在堆上由 GC 管理。见 [[5-JIT编译与运行时优化]]。详见 §12。

| 主题 | 一句话记住 | 深入 |
|---|---|---|
| 唯一不会 OOM 的区域 | 程序计数器 | §1.2 |
| 栈溢出的两种表现 | `StackOverflowError`（深度）/ `unable to create new native thread`（线程栈内存） | §2.5 |
| 分代默认比例 | 新生代占堆 1/3，Eden:S0:S1 = 8:1:1（NewRatio=2, SurvivorRatio=8） | §3.1 |
| 元空间默认上限 | 无上限（实测 `MaxMetaspaceSize` = 最大值），泄漏会吃光机器内存 | §4.4 |
| `intern()` 版本差异 | JDK 6 复制进永久代；JDK 7+ 只登记堆中已有对象的引用 | §5.2 |
| 指针碰撞 vs 空闲列表 | 取决于 GC 是否压缩整理；CMS 老年代用空闲列表 | §7.2 |
| 空对象大小 | 16 字节（12 字节头 + 4 字节对齐填充） | §9.6 |
| 引用类型速记 | 强（不回收）、软（内存不足清）、弱（每次 GC 清）、虚（只给通知） | §13.1 |

> [!note] 下一步
> 本篇讲"分配"，回收侧的完整机制（可达性分析、GC Roots 全集、三色标记与漏标、记忆集/卡表、各收集器算法级流程、GC 日志解读、安全点）见 [[2-GC机制深度]]；参数速查与调优方法见 [[6-JVM参数与调优实战]]；OOM/CPU/泄漏的排查动作见 [[7-JVM故障排查实战]]。
