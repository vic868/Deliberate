好的，我先去拉取 OpenJDK 17 的 AQS 源码以及典型子类的源码，然后基于真实源码做原理 + 实战对照讲解。
# AbstractQueuedSynchronizer（AQS）源码原理与实战分析

> 基于 **OpenJDK 17u-dev** 真实源码（与 JDK 8 经典版有重大重构差异，下面会同时点出）。

---

## 一、AQS 是什么——一句话定位

AQS 是一个**基于 FIFO 等待队列、使用单一原子 int 状态字段**为各类同步器（锁、信号量、闸锁、屏障……）提供底层框架的抽象类。它本身不实现任何同步语义，只负责**"排队 +阻塞 + 唤醒"**这套机制；具体语义由子类通过覆写 5 个钩子方法（`tryAcquire` / `tryRelease` / `tryAcquireShared` / `tryReleaseShared` / `isHeldExclusively`）来决定。

设计哲学：
- **模板方法模式**：AQS 定义 acquire/release 顶层流程，子类只填"语义"那 1–2 行。
- **独占 + 共享两种模式**：互斥用独占，读写/计数用共享。
- **支持 Condition**：内置 `ConditionObject` 实现条件变量。

---

## 二、核心数据结构

### 2.1 三个 volatile 字段

```java
private transient volatile Node head;     // 队列头（懒初始化，首次争用才创建）
private transient volatile Node tail;     // 队列尾（仅通过 CAS 修改）
private volatile int state;               // 同步状态（子类语义核心）
```

### 2.2 Node（CLH 队列节点）— JDK 17 重构后变成抽象类

```java
abstract static class Node {
    volatile Node prev;        // 前驱
    volatile Node next;        // 后继
    volatile Thread waiter;    // 当前节点关联的线程
    volatile int status;       // 0 / WAITING(1) / CANCELLED(负) / COND(2)
}

static final class ExclusiveNode  extends Node { }   // 独占模式节点
static final class SharedNode     extends Node { }   // 共享模式节点
static final class ConditionNode  extends Node implements ForkJoinPool.ManagedBlocker { }
```

状态位常量：
```java
static final int WAITING   = 1;            // 必须为正，且 JDK 17 中必须为 1
static final int CANCELLED = 0x80000000;   // 必须为负，表示线程已取消
static final int COND      = 2;            // 节点在条件队列上
```

**关键点**：JDK 17 用 `status` 一个字段替代了 JDK 8 中的 `waitStatus(int)` + `nextWaiter(Node)` 模式，节点类型由具体子类决定。

### 2.3 状态访问（基于 Unsafe 的偏移量）

```java
private static final Unsafe U = Unsafe.getUnsafe();
private static final long STATE = U.objectFieldOffset(AbstractQueuedSynchronizer.class, "state");
private static final long HEAD  = U.objectFieldOffset(AbstractQueuedSynchronizer.class, "head");
private static final long TAIL  = U.objectFieldOffset(AbstractQueuedSynchronizer.class, "tail");

protected final int getState()          { return state; }
protected final void    setState(int newState) { state = newState; }
protected final boolean compareAndSetState(int expect, int update) {
    return U.compareAndSetInt(this, STATE, expect, update);
}
```

---

## 三、JDK 17 重构核心：统一的 `acquire` 方法

JDK 8时代 AQS 有 `addWaiter`、`enq`、`doAcquireInterruptibly`、`doAcquireNanos`、`doAcquireShared`、`doReleaseShared`、`parkAndCheckInterrupt` 等一长串方法。**JDK 14 之后被合并成一个统一的 `acquire(Node, ...)`**，通过参数切换行为：

```java
final int acquire(Node node, int arg, boolean shared,
                  boolean interruptible, boolean timed, long time) {
    Thread current = Thread.currentThread();
    byte spins = 0, postSpins = 0;        // 自适应自旋次数
    boolean interrupted = false, first = false;
    Node pred = null;

    for (;;) {
        // 1) 检查自己是不是队首（first = head == pred）
        if (!first && (pred = (node == null) ? null : node.prev) != null
            && !(first = (head == pred))) {
            if (pred.status < 0) { cleanQueue(); continue; }    // 前驱被取消
            else if (pred.prev == null) { Thread.onSpinWait(); continue; }
        }

        // 2) 是队首 → 尝试获取
        if (first || pred == null) {
            boolean acquired;
            try {
                acquired = shared ? (tryAcquireShared(arg) >= 0) : tryAcquire(arg);
            } catch (Throwable ex) {
                cancelAcquire(node, interrupted, false);
                throw ex;
            }
            if (acquired) {
                if (first) { /* 自己成为 head，断开与前任的链 */ /* ... */ }
                return 1;
            }
        }

        // 3) 尚未入队 → 创建并尝试 CAS 入队
        if (node == null) {
            node = shared ? new SharedNode() : new ExclusiveNode();
        } else if (pred == null) {
            node.waiter = current;
            Node t = tail;
            node.setPrevRelaxed(t);          // relaxed write，避免屏障开销
            if (t == null) tryInitializeHead();
            else if (!casTail(t, node)) node.setPrevRelaxed(null);
            else t.next = node;
        }
        // 4) 已是队首、自旋中
        else if (first && spins != 0) { --spins; Thread.onSpinWait(); }
        // 5) 还没设置 WAITING 状态        else if (node.status == 0) { node.status = WAITING; }
        // 6) park，等待唤醒
        else {
            long nanos;
            spins = postSpins = (byte)((postSpins << 1) | 1);   // 指数退避自旋
            if (!timed) LockSupport.park(this);
            else if ((nanos = time - System.nanoTime()) > 0L) LockSupport.parkNanos(this, nanos);
            else break;                                          // 超时
            node.clearStatus();
            if ((interrupted |= Thread.interrupted()) && interruptible) break;
        }
    }
    return cancelAcquire(node, interrupted, interruptible);
}
```

**这条 for 循环同时实现了 4 种获取语义**：

| 导出方法 | 调用 acquire时的参数 |
|---|---|
| `acquire(arg)` | `(null, arg, false, false, false, 0)` —独占、可中断否 |
| `acquireInterruptibly(arg)` | `(null, arg, false, true, false, 0)` — 独占、必须响应中断 |
| `tryAcquireNanos(arg, ns)` | `(null, arg, false, true, true, nanoTime+ns)` — 独占、定时 |
| `acquireShared(arg)` | `(null, arg, true, false, false, 0)` — 共享 |
| `acquireSharedInterruptibly(arg)` | `(null, arg, true, true, false, 0)` |
| `tryAcquireSharedNanos(arg, ns)` | `(null, arg, true, true, true, nanoTime+ns)` |

---

## 四、独占模式 acquire/release 完整时序

```
线程 T 调用 acquire(arg)
 │
  ├─► tryAcquire(arg) ── 成功 ──► 直接返回
  │      └─ 失败  ▼
入队 (CAS tail)
  │
  ▼
循环：
 if (我是队首) tryAcquire(arg) ─成功 ──► 设自己为 head，断链，返回 └失败
   设置 status = WAITING
   LockSupport.park(this)  ←——— 阻塞在这里 │
                别人 release(arg) 时
                                ▼
              signalNext(head) 唤醒队首节点
                                ▼重新进入循环，再 tryAcquire
```

`release` 的实现：
```java
public final boolean release(int arg) {
    if (tryRelease(arg)) {          // 子类覆写：state 归零才返回 true
        signalNext(head);           // 唤醒 head 的后继
        return true;
    }
    return false;
}

private static void signalNext(Node h) { // JDK 17 重命名自 unparkSuccessor
    Node s;
    if (h != null && (s = h.next) != null && s.status != 0) {
        s.getAndUnsetStatus(WAITING);        // 清除 WAITING 位
        LockSupport.unpark(s.waiter);
    }
}
```

---

## 五、共享模式 acquireShared / releaseShared

差别只在两点：
1. `tryAcquireShared(arg) >= 0` 视为成功，正数还能继续传播唤醒（连环 unpark）。
2. `releaseShared` 唤醒后还会回调 `signalNextIfShared` 继续向后传。

```java
public final void acquireShared(int arg) {
    if (tryAcquireShared(arg) < 0) acquire(null, arg, true, false, false, 0L);
}

public final boolean releaseShared(int arg) {
    if (tryReleaseShared(arg)) {
        signalNext(head);
        return true;
    }
    return false;
}
```

---

## 六、实战 1：`ReentrantLock`（独占模式）

### 6.1 类结构

```
ReentrantLock ─持有─► Sync (extends AbstractQueuedSynchronizer, abstract)
                        ├──抽象方法 initialTryLock()
                        │      ├── NonfairSync 实现 —— 不查队列，直接 CAS
                        │      └── FairSync    实现 —— 查 hasQueuedThreads()
                        └── final tryAcquire(int) 由两个子类各自覆写
```

### 6.2 NonfairSync.tryAcquire

```java
protected final boolean tryAcquire(int acquires) {
    if (getState() == 0 && compareAndSetState(0, acquires)) {
        setExclusiveOwnerThread(Thread.currentThread());
        return true;
    }
    return false;       // 注意:reentrant 由 initialTryLock 处理,这里不处理
}
```

### 6.3 FairSync.tryAcquire —— 唯一差别：多一个 `hasQueuedPredecessors()`

```java
protected final boolean tryAcquire(int acquires) {
    if (getState() == 0
        && !hasQueuedPredecessors()                       // 关键公平性保证
        && compareAndSetState(0, acquires)) {
        setExclusiveOwnerThread(Thread.currentThread());
        return true;
    }
    return false;
}
```

### 6.4 tryRelease —— 不分公平/非公平，在 `Sync` 里 final 实现

```java
@ReservedStackAccess
protected final boolean tryRelease(int releases) {
    int c = getState() - releases;
    if (getExclusiveOwnerThread() != Thread.currentThread())
        throw new IllegalMonitorStateException();
    boolean free = (c == 0);
    if (free) setExclusiveOwnerThread(null);
    setState(c);                                          // 单线程独占写,不必 CAS
    return free;
}
```

### 6.5 lock() 调用链对照源码

```
ReentrantLock.lock()
 └─► sync.lock()                                         [Sync, final]
      ├─► initialTryLock()                                [子类实现]
      │     ├─ Nonfair: 直接 CAS(0→1)，可插队
      │     └─ Fair   : CAS(0→1) 前先 !hasQueuedThreads()
      └─► 失败 → acquire(1)                               [AQS]
             └─► tryAcquire(1)                            [NonfairSync/FairSync 覆写]
                   └─►失败 → 入队 → park → 等前驱 unpark
```

**重要纠正（容易踩的坑）**：很多教程说 `ReentrantLock.FairSync` / `NonfairSync` 各自覆写了 `tryAcquire` 和 `tryRelease`。**JDK 17 实际只有 `tryAcquire` 被分叉覆写，`tryRelease` 写在 `Sync` 里且 `final`**——因为释放逻辑与公平性无关，不需要分叉。

---

## 七、实战 2：`CountDownLatch`（共享模式）

### 7.1 用 AQS 的 `state` 表示倒计数

```java
private static final class Sync extends AbstractQueuedSynchronizer {
    Sync(int count) { setState(count); }

    protected int tryAcquireShared(int acquires) {
        return (getState() == 0) ? 1 : -1;   // 计数为 0 才"获取成功"
    }

    protected boolean tryReleaseShared(int releases) {
        for (;;) {                           // 自旋 + CAS
            int c = getState();
            if (c == 0) return false;        // 已为 0,无效操作(一次性)
            int nextc = c - 1;
            if (compareAndSetState(c, nextc))
                return nextc == 0;           // 仅在归零瞬间返回 true
        }
    }
}
```

### 7.2 调用链

```
线程 A: latch.await()
   └─► acquireSharedInterruptibly(1)
         └─► tryAcquireShared ─► -1 ─► park 入队,等待

线程 B/C/D: latch.countDown()
   └─► releaseShared(1)
         └─► tryReleaseShared ─► CAS state-1
 └─► nextc == 0?
                     ├─ true  → signalNext(head) ─► 唤醒线程 A
                     └─ false → 仅计数减1,无唤醒
```

**三个亮点设计**：
1. **`countDown()` 不阻塞** —— `tryReleaseShared` 用 CAS 自旋递减，调用者立刻返回。
2. **"归零即唤醒"** —— 多个 `countDown` 并发时只在最后一次归零的瞬间触发一次唤醒。
3. **一次性语义** —— `c == 0` 时 `tryReleaseShared` 直接返回 false，无法再关门；要复用请用 `CyclicBarrier`。

---

## 八、模板方法模式——5 个钩子一览

| 钩子 | 调用方 | 默认实现 | 典型覆写者 |
|---|---|---|---|
| `tryAcquire(int)` | `acquire` | `throw UOE` | `ReentrantLock.NonfairSync/FairSync` |
| `tryRelease(int)` | `release` | `throw UOE` | `ReentrantLock.Sync`（final） |
| `tryAcquireShared(int)` | `acquireShared` | `throw UOE` | `CountDownLatch.Sync`、`Semaphore` |
| `tryReleaseShared(int)` | `releaseShared` | `throw UOE` | `CountDownLatch.Sync`、`Semaphore` |
| `isHeldExclusively()` | `ConditionObject` | `throw UOE` | `ReentrantLock.Sync` |

子类必须根据业务选择**独占 / 共享**之一（或两者都用），并决定 `state` 在该子类中代表什么（重入次数？许可数？倒计数？任务状态？）——这是 AQS 的"扩展点哲学"。

---

## 九、面试高频要点速记

1. **AQS 是模板方法模式的经典应用**——子类只覆写 5 个钩子。
2. **state 字段 + CLH 队列**是核心数据结构；JDK 17 把 `waitStatus + nextWaiter` 合并成 `status` 一个 int。
3. **公平/非公平的唯一差别**在于 `tryAcquire` 是否调用 `hasQueuedPredecessors()`，与释放路径无关。
4. **独占 vs 共享**：`acquire(arg)` 对应独占、`acquireShared(arg)` 对应共享；共享模式释放后会继续传播唤醒。
5. **park/unpark 机制**：`LockSupport.park(this)` 是核心阻塞原语；`signalNext`（JDK 17 改名自 `unparkSuccessor`）负责唤醒。
6. **JDK 14+ 重大重构**：原来 6 个 `doXxx` 方法被合并成一个统一 `acquire(Node, …)`，行为由 `shared/interruptible/timed/time` 4 个参数控制。
7. **`@ReservedStackAccess` 注解**：JDK 17 给锁的关键路径方法加上，避免持锁时栈溢出导致锁泄漏。

---

如果你想把上面任何一段（特别是 `acquire` 主循环、或 `signalNext` 的传播链路）做成可执行 demo（比如用 `ReentrantLock` + `CountDownLatch` 模拟一个多阶段并发任务），告诉我具体场景，我直接写到 `p2/src/test/java` 下给你跑。





# AQS 速记：5W1H

## 一图总览

| 维度 | 答案 |
|---|---|
| **What** | 抽象队列同步器，给锁/信号量/闸锁等同步器提供**"排队 + 阻塞 + 唤醒"**的框架 |
| **Who** | **Doug Lea** 主导设计（JSR-166 专家组协助），JDK 14+ 由 OpenJDK 协作者重构 |
| **Why** | 避免每个并发工具**重复造 CLH 队列与 park/unpark 逻辑**；用单一原子 int `state` 承载语义 |
| **When** | **JDK 1.5**（2004）首次引入；**JDK 14+** 重大重构（统一 acquire 方法、`Node` 拆三个具体子类） |
| **Where** | 包 `java.util.concurrent.locks.AbstractQueuedSynchronizer`；被 `ReentrantLock` / `ReentrantReadWriteLock` / `Semaphore` / `CountDownLatch` / `ThreadPoolExecutor.Worker` / `ForkJoinPool` 等直接或间接复用 |
| **How** | **模板方法模式**：AQS 定义 acquire/release 顶层流程，子类覆写 5 个钩子（`tryAcquire` / `tryRelease` / `tryAcquireShared` / `tryReleaseShared` / `isHeldExclusively`）填业务语义 |

---

## What —— AQS 到底是什么

一个**抽象类**，自身**不实现任何同步语义**，只做三件事：
1. 维护一个 **volatile int state**（子类语义的载体）。
2. 维护一个 **FIFO CLH 变体等待队列**（`head`/`tail` + `Node` 链表）。
3. 通过 **`LockSupport.park / unpark`** 阻塞/唤醒线程。

子类只需要告诉它"什么算获取成功 / 什么算释放成功"，剩下的排队、阻塞、唤醒、传播、中断、取消、超时它全包了。

---

## Who —— 谁造的 / 现在谁维护

- **作者**：**Doug Lea**，纽约州立大学石溪分校教授，JSR-166（Java 并发包）首席专家。
- **协作**：JSR-166 专家组（含 Joshua Bloch、Mark Reinhold 等）。
- **维护**：OpenJDK 社区；JDK 14 的"Jan Holloway（jdk-14+14-ga）"由 **Martin Buchholz** 等人把原来散落的 `doXxx` 方法合并为统一 `acquire(Node, …)`。
- **精神继承者**：`java.util.concurrent` 子包里几乎所有"等队列的同步器"都基于它。

---

## Why —— 为什么要造 AQS

**造之前的问题（2004 年前）**：
- `synchronized` 太重，不能中断、不能定时、不能公平。
- `Object.wait/notify` 太弱，没有等待队列、没有共享模式。
- 想写一个"公平可中断的互斥锁"得自己实现一遍 CLH 队列 + park/unpark，每个工具重复一遍。

**AQS 的解法**：
- **一次实现，到处复用** —— 把"排队 + 阻塞"这些公共机制抽到 AQS。
- **单一原子字段承载一切语义** —— 子类用 `state` 表示"重入次数 / 许可数 / 倒计数 / 任务状态"…由子类自己定义。
- **模板方法** —— 顶层流程稳定，子类只填 5 个钩子（默认全抛 `UnsupportedOperationException`），无法误用。

---

## When —— 何时诞生 / 何时用

**诞生**：`JDK 1.5`（2004-09 发布），包 `java.util.concurrent`同步部分的核心。

**关键演进节点**：

| 版本 | 变化 |
|---|---|
| **JDK 1.5** | 首次引入；雏形 `acquireQueue`、`addWaiter`、`unparkSuccessor` |
| **JDK 1.6** | 加入 `ConditionObject`、超时获取、CAS 优化 |
| **JDK 7** | `LockSupport.park` 优化 |
| **JDK 8** | 教学/经典版本，多数博客基于此 |
| **JDK 14+** | **重大重构**：`addWaiter`+`enq`+`doAcquire*`+`doReleaseShared` 全部合并为统一 `acquire(Node,…,shared,interruptible,timed,time)`；`unparkSuccessor` 改名 `signalNext`；`Node` 拆为 `ExclusiveNode / SharedNode / ConditionNode` |
| **JDK 17** | 加 `@ReservedStackAccess` 注解，避免持锁时栈溢出导致锁泄漏 |

**何时该用 AQS**：
- 自己写一个**新的同步原语**（自定义锁、一次性闸、信号量变种…）→ 直接用 `java.util.concurrent` 已有的即可。
- 想深入理解 **`ReentrantLock` / `Semaphore` / `CountDownLatch` 工作机制** → 必须读 AQS。
- 排查 **lock 性能、线程 hang、unfairness 问题** → 都要回到 AQS。

---

## Where —— 在 JDK 中的位置 / 影响范围

### 物理位置

```
src/java.base/share/classes/java/util/concurrent/locks/
  ├── AbstractQueuedSynchronizer.java   ←核心
  ├── AbstractOwnableSynchronizer.java  ← 父类,记录独占线程
  ├── ReentrantLock.java                ← 独占 + 非公平/公平
  ├── ReentrantReadWriteLock.java       ← 共享读 + 独占写
  ├── ConditionObject                   ← AQS 内部类
  └── LockSupport.java                  ← park/unpark 原语
```

### 直接/间接继承链

```
AbstractOwnableSynchronizer
    └── AbstractQueuedSynchronizer  (extends, implements Serializable)
            ├── ReentrantLock.Sync
            │ ├── FairSync
            │       └── NonfairSync
            ├── ReentrantReadWriteLock.Sync (内部更细分)
            ├── Semaphore.NonfairSync / FairSync
            ├── CountDownLatch.Sync
            ├── ThreadPoolExecutor(Worker 用 AQS 实现不可重入互斥)
            ├── ForkJoinPool / CompletableFuture (间接使用)
            └── FutureTask (内部 Sync extends AQS)
```

### 逻辑结构（一张图看懂）

```
                       ┌────────────────────────────┐
                       │   AbstractQueuedSynchronizer│
                       │   state (volatile int)      │
                       │   head / tail (CLH 队列)    │
                       └─────────┬──────────────────┘ │ 模板方法
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        acquire(arg)     acquireShared(arg)   newCondition()
        release(arg)     releaseShared(arg)        │
              │                  │                  ▼ ┌──────────┴───────┐  ┌───────┴────────┐  ConditionObject
   │  独占钩子 (5个)   │  │  共享钩子(2个) │   (await/signal)
   │ tryAcquire      │  │  tryAcquireShared
   │  tryRelease      │  │  tryReleaseShared
   └──────────────────┘  └────────────────┘
              ▲                  ▲
   ┌──────────┴───────┐  ┌───────┴────────┐
   │ ReentrantLock    │  │ CountDownLatch │
   │ Semaphore(int)   │  │ Semaphore      │
   │ (Reentrant Read │  │ (permits)      │
   │  Write Lock)     │  │                │
   └──────────────────┘  └────────────────┘
```

---

## How —— 怎样工作 / 怎样用

### 怎么用（最少代码示例，复用类注释给的 `Mutex`）

```java
class Mutex implements Lock {
    private static class Sync extends AbstractQueuedSynchronizer {
        protected boolean tryAcquire(int acquires) {
            assert acquires == 1;
            if (compareAndSetState(0, 1)) {               // 1. CAS 抢锁
                setExclusiveOwnerThread(Thread.currentThread());
                return true;
            }
            return false;
        }
        protected boolean tryRelease(int releases) {
            assert releases == 1;
            if (!isHeldExclusively()) throw new IllegalMonitorStateException();
            setExclusiveOwnerThread(null);
            setState(0);
            return true;
        }
        public boolean isHeldExclusively() {
            return getExclusiveOwnerThread() == Thread.currentThread();
        }
        public Condition newCondition() { return new ConditionObject(); }
    }

    private final Sync sync = new Sync();
    public void lock()   { sync.acquire(1); } // 失败自动入队
    public void unlock() { sync.release(1); }              // 释放 + 唤醒队首
}
```

### 怎么工作（一条主线：独占 acquire）

```
acquire(arg)
   ├─► tryAcquire(arg)  ───成功──► return
   │ │失败
   │           ▼
   │    创建 Node / SharedNode(非公平 CAS 入队(也可经 tryInitializeHead() 建头)
   │           │
   │           ▼
   │    for(;;){
   │       我是 head? ──是──► tryAcquire(arg) ─成功──► 设自己为 head,断链,return
   │       │否
   │       ▼
   │       node.status = WAITING
   │       LockSupport.park(this) ───────────► 阻塞在这
   │    }
   │
   │   (其他线程 release)
   │       │
   │       ▼
   │   signalNext(head) ─► unpark(head.next.waiter)
   │ │
   │       ▼
   │   唤醒线程回到 for 循环顶部,再 tryAcquire
```

### 怎么工作（共享 release 唤醒传播）

```java
public final boolean releaseShared(int arg) {
    if (tryReleaseShared(arg)) {     // 子类:CountDownLatch 在归零瞬间返回 true
        signalNext(head);            // 唤醒下一个;它会链式继续 signalNext
        return true;
    }
    return false;
}
```

——共享模式下，队首被唤醒并获取成功后，会通过 `signalNextIfShared(node)` 把后继共享节点也一并唤醒，实现"连环放行"。

### 工作机制小结（4 个原子动作）

| 原子动作 | 实现 |
|---|---|
| **状态变更** | `compareAndSetState`（Unsafe CAS） |
| **入队** | `casTail` + `setPrevRelaxed`（relaxed write 省屏障） |
| **阻塞** | `LockSupport.park(this)` |
| **唤醒** | `LockSupport.unpark(node.waiter)` |

---

## 一句话总结

**AQS = 一个 volatile int state + 一条 CLH 队列 + 一对 park/unpark 原语 + 一个模板方法框架**；子类只需回答"什么算获取 / 释放"，所有排队阻塞唤醒的脏活 AQS 全包。



我接着往深处挖，分四块补完上轮没展开的部分：JDK 8 ↔ JDK 17 源码对照、ConditionObject 原理、cancelAcquire / cleanQueue 取消机制，再加一个"自己写一个 AQS 子类"的实战演练。
# AQS 深入：版本对照、Condition、取消机制、自定义同步器

---

## 一、JDK 8 ↔ JDK 17 源码对照表

> 多数中文教程都基于 **JDK 8**，但生产环境基本是 **JDK 11/17+**。对照读两份源码才能彻底打通。

### 1.1 Node 内部类：分分合合

| 维度 | **JDK 8**（教学版） | **JDK 17**（重构版） |
|---|---|---|
| 类型 | `Node` 单类 + `SHARED`/`EXCLUSIVE` 哨兵 | `Node` 抽象类 + `ExclusiveNode`/`SharedNode`/`ConditionNode` |
| 状态字段 | `volatile int waitStatus` | `volatile int status` |
| 状态值 | `SIGNAL(-1)` / `CANCELLED(1)` / `CONDITION(-2)` / `PROPAGATE(-3)` / `0` | `WAITING(1)` / `CANCELLED(0x80000000)` / `COND(2)` / `0` |
| 模式字段 | `Node nextWaiter`（兼职：类型标记 + 条件队列下一节点） | **取消** —— 类型由具体子类决定 |
| 线程引用 | `volatile Thread thread` | `volatile Thread waiter`（仅在入队后才赋值） |

### 1.2 核心方法：6 合 1

```
JDK 8                                                  JDK 17
─────────────────────────                              ──────────────────────────────
addWaiter(mode)        ─┐                             acquire(Node node, int arg,
enq                    ▼  //      │
                    Node入队                         boolean shared,
acquireQueued ──── 独占·忽略中断                       boolean interruptible,
doAcquireInterruptibly ── 独占·可中断                   boolean timed, long time)
doAcquireNanos ──── 独占·定时                          // 同一方法,通过参数切换 4 种语义
doAcquireShared ──── 共享·忽略中断                      + relaxed-write 入队
doReleaseShared ──── 共享·传播唤醒                      + 自适应 spins / postSpins
```

### 1.3 关键代码片段对比

**入队（独占）**

```java
// JDK 8
private Node addWaiter(Node mode) {
    Node node = new Node(Thread.currentThread(), mode);
    Node pred = tail;
    if (pred != null) {
        node.prev = pred;
        if (compareAndSetTail(pred, node)) { pred.next = node; return node; }
    }
    enq(node);                                  // 失败回退到自旋
    return node;
}
```

```java
// JDK 17：合并到 acquire 主循环
if (pred == null) {
    node.waiter = current;
    Node t = tail;
    node.setPrevRelaxed(t);                     // relaxed write 省屏障
    if (t == null) tryInitializeHead();         // 首次争用才建头
    else if (!casTail(t, node)) node.setPrevRelaxed(null);
    else t.next = node;
}
```

**park 与中断检查**

```java
// JDK 8：封装成方法
private final boolean parkAndCheckInterrupt() {
    LockSupport.park(this);
    return Thread.interrupted();
}
```

```java
// JDK 17：直接内联到主循环
spins = postSpins = (byte)((postSpins << 1) | 1);   // 指数退避自旋
if (!timed) LockSupport.park(this);
else if ((nanos = time - System.nanoTime()) > 0L) LockSupport.parkNanos(this, nanos);
else break;
node.clearStatus();
if ((interrupted |= Thread.interrupted()) && interruptible) break;
```

**共享释放（关键差别）**

```java
// JDK 8：专有方法 doReleaseShared + PROPAGATE 状态传播
private void doReleaseShared() {
    for (;;) {
        Node h = head;
        if (h != null && h != tail) {
            int ws = h.waitStatus;
            if (ws == Node.SIGNAL) {
                if (!compareAndSetWaitStatus(h, Node.SIGNAL, 0)) continue;
                LockSupport.unpark(h.next.thread);
            } else if (ws == 0 && !compareAndSetWaitStatus(h, 0, Node.PROPAGATE))
                continue;
        }
        if (h == head) break;
    }
}
```

```java
// JDK 17：PROPAGATE 状态被取消,释放更简洁
public final boolean releaseShared(int arg) {
    if (tryReleaseShared(arg)) {
        signalNext(head);                  // 唤醒后继;它成功后调 signalNextIfShared 再传
        return true;
    }
    return false;
}
private static void signalNext(Node h) { ... LockSupport.unpark(s.waiter); ... }
private static void signalNextIfShared(Node h) { /* 仅唤醒 SharedNode 后继 */ ... }
```

### 1.4 阅读建议- **入门 / 教学**：先读 **JDK 8** 版本，方法多但职责单一（`addWaiter`/`enq`/`acquireQueued`/`parkAndCheckInterrupt` 各管一摊），便于理解。
- **生产 / 进阶**：读 **JDK 17** 版本，关注统一 `acquire` 主循环 + `status` 字段 + 自旋指数退避。
- **面试**：JDK 8 讲方法名，JDK 17 讲设计取舍（"6 合一"换来代码体积小但分支多）。

---

## 二、ConditionObject —— 条件变量

### 2.1 为什么需要 Condition

`synchronized` 配合 `wait/notify` 只能用在 monitor 上、不能跨锁。`Condition` 把"等待条件"和"持有锁"解耦，一个锁上可以有多组条件队列。

AQS 内置的 `ConditionObject` 就是 `Condition` 的标准实现。

### 2.2 数据结构

```java
public class ConditionObject implements Condition, java.io.Serializable {
    private transient ConditionNode firstWaiter; // 条件队列头    private transient ConditionNode lastWaiter;     // 条件队列尾
    // ConditionNode 继承自 Node,加一个 nextWaiter 字段
}
```

注意：**条件队列 ≠ 同步队列**。它们是两个独立的单向链表，await 时从 sync 队列搬到 condition 队列，signal 时反向搬回。

### 2.3 `await()` 完整流程（JDK 17）

```java
public final void await() throws InterruptedException {
    if (Thread.interrupted()) throw new InterruptedException();
    ConditionNode node = new ConditionNode();      // 1. 创建条件节点
    int savedState = enableWait(node);             // 2. 加入条件队列尾部,释放锁

    LockSupport.setCurrentBlocker(this);
    boolean interrupted = false, cancelled = false, rejected = false;
    while (!canReacquire(node)) {                  // 3. 直到被 signal/unpark        if (interrupted |= Thread.interrupted()) {
            if (cancelled = (node.getAndUnsetStatus(COND) & COND) != 0) break;
        } else if ((node.status & COND) != 0) {
            try {
                if (rejected) node.block();
                else ForkJoinPool.managedBlock(node);   // 关键:支持 ForkJoinPool
            } catch (RejectedExecutionException ex) { rejected = true; }
            catch (InterruptedException ie)   { interrupted = true; }
        } else Thread.onSpinWait();
    }
    LockSupport.setCurrentBlocker(null);
    node.clearStatus();
    acquire(node, savedState, false, false, false, 0L);   // 4. 重新抢锁    if (interrupted) { /* 清理 + 重抛异常 */ }
}
```

四步走：
1. 创建 `ConditionNode`，加入**条件队列**（单向链表）。
2. `enableWait()` 内部调用 `release(savedState)` —— **必须先释放锁**，否则别的线程永远拿不到锁去做 signal。
3. 在条件队列上 park（JDK 17 用 `ForkJoinPool.managedBlock`，可被 ForkJoin 工作线程借用而不占用其池子）。
4. 被 signal 后，重新走 `acquire(...)` 抢锁 —— **抢到锁才返回** await。

### 2.4 `signal()` 完整流程

```java
public final void signal() {
    if (!isHeldExclusively()) throw new IllegalMonitorStateException();
    ConditionNode first = firstWaiter;
    if (first != null) doSignal(first);
}

private void doSignal(ConditionNode first) {
    do {
        if ((firstWaiter = first.nextWaiter) == null) lastWaiter = null;
        first.nextWaiter = null;                                // 脱离    } while (!transferForQueue(first) && (first = firstWaiter) != null);
}

final boolean transferForQueue(ConditionNode node) {
    if (!compareAndSetStatus(node, COND | WAITING, 0))           // 1. 清状态
        return false;

    Node t = tail;
    node.setPrevRelaxed(t);                                     // 2. CAS 入同步队列
    if (t == null) tryInitializeHead();
    else if (!casTail(t, node)) node.setPrevRelaxed(null);
    else { t.next = node; LockSupport.unpark(node.waiter); }    // 3. unpark 唤醒
    return true;
}
```

要点：
- **signal 只是"挪位置 + unpark"，不是立刻让 await 返回**。await 还得重新抢锁（步骤 4）。
- `signalAll` 是把整个条件队列搬过去，效率 O(n)。
- `await()` 释放锁期间，**其他线程可以正常 lock/unlock**，这是 Condition 比 `wait/notify` 灵活的关键。

---

## 三、cancelAcquire + cleanQueue —— 取消与清理

### 3.1 何时触发取消

调用方在 park期间被 `interrupt` / 超时 / 主动 `cancel`，AQS 必须把它从队列中安全摘除。

### 3.2 JDK 8 的 cancelAcquire（教学版直观）

```java
private void cancelAcquire(Node node) {
    if (node == null) return;
    node.thread = null;                                          // 1. 抹掉线程引用

    // 2. 跳过已取消节点,找最近的非取消前驱
    Node pred = node.prev;
    while (pred.waitStatus > 0) node.prev = pred = pred.prev;

    // 3. 记录后继(可能被并发修改,后面 CAS 失败重试)
    Node next = node.next;
    if (pred != null) {
        int ws = pred.waitStatus;
        if (ws == Node.SIGNAL || (ws <= 0 && compareAndSetWaitStatus(pred, ws, Node.SIGNAL)))
            /* 用 pred 的 SIGNAL 状态保证 unparkSuccessor 能找到它 */;
        else pred.compareAndSetNext(node, next);

        if (next != null) next.prev = pred;
    } else if (next != null) next.prev = null;
}
```

要点：把"我"从双向链表中抹掉，让**前驱的 next** 和**后继的 prev** 都跳过自己。后续 `unparkSuccessor` 从 tail 反向扫描一定能找到。

### 3.3 JDK 17 的 cancelAcquire（更精简）

```java
private int cancelAcquire(Node node, boolean interrupted, boolean interruptible) {
    if (node != null) {
        node.waiter = null;                  // 抹线程引用
        node.status = CANCELLED;            // 标记        if (node.prev != null) cleanQueue();// 从 tail 反向扫描清理整条链
    }
    if (interrupted) {
        if (interruptible) return CANCELLED;
        else Thread.currentThread().interrupt();
    }
    return 0;
}
```

`cleanQueue()` 的关键 —— **从 tail 反向遍历，遇已取消节点就 CAS 跳过**：

```java
private void cleanQueue() {
    for (;;) {
        for (Node q = tail, s = null, p, n;;) {
            if (q == null || (p = q.prev) == null) return;       // 到头
            if (s == null ? tail != q : (s.prev != q || s.status < 0)) break;

            if (q.status < 0) {                                  // q 已取消
                if ((s == null ? casTail(q, p) : s.casPrev(q, p))
                    && q.prev == p) {
                    p.casNext(q, s);                            // 把 q 从链表里抠掉
                    if (p.prev == null) signalNext(p);          // 顺手唤醒
                }
                break;
            }
            if ((n = p.next) != q) {                             // 修补 p.next
                if (n != null && q.prev == p) {
                    p.casNext(n, q);
                    if (p.prev == null) signalNext(p);
                }
                break;
            }
            s = q; q = q.prev;                                  // 继续往上扫
        }
    }
}
```

**为什么要从 tail 反向**？因为 `next` 指针不是可靠的 —— 中间节点的 next 可能在并发的 cancel 中断链；反向走 prev 是稳定的。

### 3.4 取消状态的"传染"问题

一个节点取消可能让**它和 head 之间所有未取消节点**都被跳过清理。常见场景：

```
H(head, status=0) ── A(WAITING) ── B(CANCELLED) ── C(WAITING)
                                          ↑
唤醒时从 tail 反扫 → 命中 C → 跳过 B
 → 唤醒 C（C 发现自己前驱不是 head → cleanQueue）
 → cleanQueue 把 B 从链中抠掉
```

这就是 AQS "从尾反向清理" 的本质：**让 unpark 永远能找到活人**。

---

## 四、实战：写一个基于 AQS 的"令牌桶限流器"

> 比 `Semaphore` 多一道"令牌按时间补充"的逻辑，正好演示 AQS 共享模式 + CAS。

### 4.1 需求

- 容量 `capacity`，初始满。
- 每次 `acquire()` 取 1 个令牌，没有就阻塞。
- 后台按 `refillInterval` 自动补 1 个令牌（最多补到 `capacity`）。
- 简单的"令牌桶限流"。

### 4.2 实现

```java
public class TokenBucketLimiter {

    /** AQS 子类,用 state 表示当前令牌数(≤ capacity) */
    private static final class Sync extends AbstractQueuedSynchronizer {
        private final int capacity;
        private final long refillIntervalNanos;

        Sync(int capacity, long refillIntervalMillis) {
            this.capacity = capacity;
            this.refillIntervalNanos = refillIntervalMillis * 1_000_000L;
            setState(capacity);                            // 初始满桶
        }

        int available() { return getState(); }

        /** 共享模式 tryAcquire:有令牌就拿一个 */
        @Override
        protected int tryAcquireShared(int acquires) {
            for (;;) {
                int c = getState();
                if (c <= 0) return -1;                     // 没令牌,失败
                int next = c - acquires;
                if (next < 0) return -1;
                if (compareAndSetState(c, next)) return 1; // CAS 拿一个 // CAS 失败 → 重试
            }
        }

        /** 共享模式 tryRelease:归还(补)令牌,只在满桶前返回 true */
        @Override
        protected boolean tryReleaseShared(int token) {
            for (;;) {
                int c = getState();
                if (c >= capacity) return false;            // 已满,不补
                int next = Math.min(capacity, c + token);
                if (compareAndSetState(c, next)) {
                    signalNext(head);                       // 唤醒一个等待者
                    return true;
                }
            }
        }
    }

    private final Sync sync;

    public TokenBucketLimiter(int capacity, long refillIntervalMillis) {
        this.sync = new Sync(capacity, refillIntervalMillis);
    }

    /** 阻塞获取1 个令牌 */
    public void acquire() {
        sync.acquireSharedInterruptibly(1);
    }

    /** 后台定时调用,补 1 个令牌 */
    public void refill() {
        sync.releaseShared(1);
    }

    /** 启动一个守护线程,定时补给 */
    public ScheduledFuture<?> startAutoRefill(ScheduledExecutorService scheduler) {
        return scheduler.scheduleAtFixedRate(
            this::refill,
            sync.refillIntervalNanos / 1_000_000,
            sync.refillIntervalNanos / 1_000_000,
            TimeUnit.NANOSECONDS);
    }

    public int available() { return sync.available(); }
}
```

### 4.3 用法

```java
TokenBucketLimiter limiter = new TokenBucketLimiter(100, 50);  // 100 个令牌,每 50ms 补 1 个

ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
limiter.startAutoRefill(scheduler);

// 业务线程limiter.acquire();   // 没令牌就 park,被 refill 后唤醒
```

### 4.4 与 `Semaphore` 的对比

| 维度 | `Semaphore` | 本例 `TokenBucketLimiter` |
|---|---|---|
| state 含义 | 剩余许可数 | 剩余令牌数 |
| 释放方式 | 手动 `release()` | 手动 `refill()` 或定时补给 |
| 适用 | 资源池连接数 | 平滑限流 |
| AQS 模式 | 共享 | 共享 |
| 公平性 | 可选 FairSync | 默认非公平 |

---

## 六、下一步可以挑一个继续深入

1. **ReentrantReadWriteLock** —— AQS 同时用独占 + 共享两种模式，state 高 16 位持读锁计数、低 16 位持写锁计数。
2. **Semaphore** —— 纯共享模式 + 公平/非公平分叉（与 ReentrantLock 同构）。
3. **StampedLock** —— JDK 8 新增，**不基于 AQS**，用 state + 乐观读 + view 锁，对照 AQS 看另一条设计路线。
4. **AQS 在 HotSpot 层面的优化** —— `@ReservedStackAccess` 注解、Unsafe 的 `weakCompareAndSetReference`、`putReference` relaxed语义在 CPU 层面对应什么指令。

告诉我你想看哪个，我直接基于源码继续展开。
四个模块都完成了。如果想看 **ReentrantReadWriteLock（state 高低位切分）**、**Semaphore 的 FairSync/NonfairSync**、**StampedLock（AQS 之外的另一条路线）**，或者 **AQS 的 HotSpot 底层优化（@ReservedStackAccess + Unsafe）**，直接说哪一个就行。