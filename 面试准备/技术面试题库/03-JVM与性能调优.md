---
title: 03-JVM与性能调优
tags: [面试, Java, 技术题库, JVM, 调优]
status: 进行中
---

# ⚙️ 03 · JVM 与性能调优

> 返回 [[00-总览与使用说明]]

---

## 一、内存结构 `#高频`

| 区域 | 说明 | 线程 |
|---|---|---|
| **程序计数器** | 当前字节码行号；唯一不会 OOM 的区域 | 私有 |
| **虚拟机栈** | 栈帧（局部变量表、操作数栈、动态链接、返回地址）；`-Xss` | 私有 |
| **本地方法栈** | native 方法 | 私有 |
| **堆** | 对象实例；分新生代（Eden + 2×Survivor）和老年代 | 共享 |
| **方法区 / 元空间** | 类元信息、常量、静态变量；JDK8 后用**本地内存**（Metaspace） | 共享 |
| **直接内存** | NIO DirectByteBuffer；`-XX:MaxDirectMemorySize` | 共享 |

**对象创建过程**：类加载检查 → 分配内存（**指针碰撞 / 空闲列表**）→ 零值初始化 → 设置对象头 → 执行 `<init>`

**对象内存布局**：对象头（Mark Word + 类型指针）+ 实例数据 + 对齐填充

**对象分配优化**：TLAB（线程本地分配缓冲）、栈上分配、标量替换、逃逸分析

**引用类型**：强 / 软（内存不足才回收，做缓存）/ 弱（下次 GC 必回收）/ 虚（回收通知）

**判断对象已死**：引用计数（有循环引用问题）→ **可达性分析**（GC Roots：栈中引用、静态变量、常量、JNI 引用）

---

## 二、垃圾回收 `#高频`

| 问题 | 得分骨架 |
|---|---|
| GC 算法 | 标记-清除（碎片）、标记-复制（新生代）、标记-整理（老年代）、分代收集 |
| 为什么分代 | 大部分对象朝生夕死（弱分代假说）→ 新生代用复制、老年代用整理，各取所长 |
| Minor / Major / Full GC | 新生代 / 老年代 / 整堆（含方法区）；Full GC 要尽量避免 |
| 对象何时进老年代 | 年龄达阈值（默认 15）、大对象直接进、动态年龄判定（Survivor 同年龄总和 > 50%）、Survivor 放不下 |
| **收集器对比** | Serial（单线程）→ ParNew（多线程新生代）→ Parallel Scavenge（吞吐优先）→ **CMS**（并发标记清除，低延迟，有碎片+并发失败）→ **G1**（分 Region，可预测停顿，JDK9 默认）→ **ZGC**（染色指针+读屏障，停顿 <10ms，超大堆） |
| G1 特点 | Region 分区、`-XX:MaxGCPauseMillis` 目标停顿、Remembered Set 处理跨代引用、Mixed GC |
| CMS 四个阶段 | 初始标记（STW）→ 并发标记 → 重新标记（STW）→ 并发清除；**并发失败会退化 Full GC** |
| 三色标记与漏标 | 黑/灰/白；漏标需**增量更新**（CMS）或**原始快照 SATB**（G1）解决 |
| STW 发生在哪 | 初始标记、重新标记（以及新生代回收） |

**常用参数**：
```
-Xms -Xmx              堆初始/最大（建议设为相同，避免动态扩容）
-Xmn / -XX:NewRatio    新生代大小
-Xss                   栈大小
-XX:MetaspaceSize      元空间
-XX:+UseG1GC           指定收集器
-XX:MaxGCPauseMillis   目标停顿
-XX:+HeapDumpOnOutOfMemoryError   OOM 自动 dump
-Xlog:gc*              GC 日志（JDK9+）
```

---

## 三、类加载 `#高频`

- **过程**：加载 → 验证 → 准备 → 解析 → 初始化（+ 使用 + 卸载）
- **准备阶段**：静态变量赋**零值**（`final` 常量直接赋真值）
- **双亲委派**：App → Ext/Platform → Bootstrap；先委派父加载器，父加载不了才自己加载
- **双亲委派的好处**：安全（防止自定义 `java.lang.String` 覆盖核心类）、避免重复加载
- **打破双亲委派**：Tomcat（Web 应用隔离）、SPI（`Thread.currentThread().getContextClassLoader()`）、OSGi、热部署
- **类初始化时机**：new / 反射 / 访问静态字段或方法 / 子类初始化 / 主类
- **类加载器**：Bootstrap（C++，`getClassLoader()` 返回 null）、Platform、App、自定义

---

## 四、线上排查实战 `#高频`

### CPU 100%
```bash
top -Hp <pid>              # 找占用高的线程 id
printf "%x\n" <tid>        # 转 16 进制
jstack <pid> | grep -A 30 <hex-tid>   # 看线程栈
```
常见原因：死循环、频繁 GC、正则回溯、大量线程上下文切换

### 内存泄漏 / OOM
```bash
jmap -dump:live,format=b,file=heap.hprof <pid>
jstat -gcutil <pid> 1000     # 看 GC 频率与各区占用
```
用 MAT / JVisualVM 分析支配树、找 GC Roots 引用链

### 其他
- `jinfo` 查参数、`jstat` 看 GC、**Arthas**（`dashboard`/`thread`/`trace`/`watch`/`jad`）
- `-XX:+HeapDumpOnOutOfMemoryError` 一定要开

### OOM 类型
| 类型 | 原因 |
|---|---|
| `Java heap space` | 堆内存不足 / 内存泄漏 |
| `Metaspace` | 类太多（动态代理、热部署） |
| `GC overhead limit exceeded` | GC 占用过高但回收很少 |
| `unable to create new native thread` | 线程数超系统限制 |
| `Direct buffer memory` | 直接内存不足（NIO/Netty） |

---

## 五、调优思路

1. **先定位再调优**，别瞎调参数
2. 看 GC 日志：频率、停顿、回收效果
3. 常见方向：堆大小、新生代比例、收集器选型、减少大对象、优化对象生命周期
4. **延迟优先选 G1/ZGC，吞吐优先选 Parallel**
5. 容量评估 + 压测验证，调完必须回归

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与使用说明]] · [[02-并发与多线程]]

#面试 #JVM #调优 #待补
