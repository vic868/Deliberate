---
title: 15-Java并发专题（详解版）
tags: [面试, Java, 技术题库, 并发, 多线程, AQS, 线程池]
status: 进行中
---

# 🧵 15 · Java 并发专题（详解版）

> 返回 [[00-总览与使用说明]] · 姊妹篇：[[02-并发与多线程]]（速查骨架）· [[面试准备/专业技能/05-并发]]（微服务治理场景）

> [!abstract] 使用定位
> 「精通高并发编程」的**详解底稿**：每题给**完整答案**（不只骨架）+ 关键源码 + 手撕代码。
> 应试标准：**主流程能手画、关键类名报得出、陷阱能举例、手撕能白板写**。

---

## 一、线程基础（快问快答）

| 问题 | 答案 |
|---|---|
| 线程 6 种状态 | NEW → RUNNABLE →（BLOCKED / WAITING / TIMED_WAITING）→ TERMINATED |
| start() vs run() | start 创建新线程由 JVM 调 run；直接调 run 就是普通方法调用（单线程顺序执行） |
| sleep vs wait | sleep 是 Thread 静态方法，**不释放锁**；wait 是 Object 方法，**释放锁**，必须在 synchronized 内 |
| wait 为什么配 while | **防虚假唤醒**（spurious wakeup）：醒来后条件未必成立，必须重查 |
| notify vs notifyAll | notify 随机唤醒一个，可能唤醒"条件不匹配"的线程导致信号丢失 → **默认 notifyAll** |
| interrupt 的语义 | 设置中断标志，**不强制停止**；阻塞方法抛 InterruptedException 并清除标志；协作式终止 |
| 正确停止线程的方式 | 标志位（volatile）+ 中断响应 + 清理资源；**别用 stop()**（已废弃，破坏一致性） |
| 守护线程 | `setDaemon(true)`（必须在 start 前）；所有非守护线程结束 → JVM 退出 |
| yield / join | yield 让出 CPU（无语义保证）；join 等待目标线程终止（底层 wait） |

---

## 二、JMM 与三大性质（★理解并发的一切地基）

### 2.1 三大性质与实现手段

| 性质 | 含义 | 实现手段 |
|---|---|---|
| **原子性** | 操作不可分割 | synchronized、Lock、CAS（单个变量）、原子类 |
| **可见性** | 写对其他线程立即可见 | volatile、synchronized、final、Lock |
| **有序性** | 禁止指令重排 | volatile（内存屏障）、synchronized |

### 2.2 为什么会有可见性/有序性问题
- **CPU 缓存架构**：每核私有 L1/L2，共享 L3/内存 → 写先落本地缓存
- **Store Buffer / 失效队列**：写缓冲区让"写"延迟可见；失效消息异步处理
- **重排来源三层**：编译器优化 → CPU 乱序执行 → 内存系统重排（store buffer）
- 单线程内 **as-if-serial**：重排不改变单线程结果——**所以单线程测试发现不了并发 bug**

### 2.3 happens-before 规则（8 条，判断可见性的唯一标准）
1. **程序顺序规则**：单线程内按代码顺序
2. **监视器锁规则**：解锁 hb 后续加锁
3. **volatile 规则**：写 hb 后续读
4. **线程启动规则**：`start()` 前的操作 hb 新线程内所有操作
5. **线程终止规则**：线程内所有操作 hb `join()` 返回后
6. **线程中断规则**：interrupt 调用 hb 被中断线程检测到中断
7. **对象终结规则**：构造完成 hb finalize
8. **传递性**：A hb B 且 B hb C → A hb C

> [!tip] 应试技巧
> 所有"这个场景线程安全吗"的题，都用 happens-before 推一遍：
> **写线程的操作和读线程的读之间，有没有一条 happens-before 链？** 没有 → 可见性/有序性不保证。

---

## 三、volatile / synchronized / final（原理详解）

### 3.1 volatile
- **保证**：可见性 + 禁止重排；**不保证原子性**（`i++` 是读-改-写三步）
- **实现**：JVM 层插入**内存屏障**（volatile 写后 StoreLoad、写前 StoreStore、读后 LoadLoad/LoadStore）；x86 上体现为 **lock 前缀指令**（锁缓存行 + 写回主存 + MESI 失效其他核副本）
- **典型场景**：状态标志位、DCL 单例、独立统计计数（读多写少配合原子类）
- **不适用**：count++ 这类复合操作（→ AtomicLong/LongAdder）

### 3.2 DCL 单例为什么要 volatile（★高频）
```java
public class Singleton {
    private static volatile Singleton instance;   // ← 必须 volatile
    public static Singleton getInstance() {
        if (instance == null) {                   // ① 一检：避免每次加锁
            synchronized (Singleton.class) {
                if (instance == null) {           // ② 二检：防并发重复创建
                    instance = new Singleton();   // ③ 三步：分配→初始化→赋引用
                }
            }
        }
        return instance;
    }
}
```
> ③ 的三步可能被重排成 **1→3→2**：另一线程在 ① 处看到**非 null 但未初始化完成**的对象 → 使用时 NPE/脏数据。volatile 禁止 2/3 重排 + 保证可见。

### 3.3 synchronized 原理
- **字节码**：同步代码块 = `monitorenter/monitorexit`；同步方法 = `ACC_SYNCHRONIZED` 标志
- **对象头 Mark Word**（64 位 JVM 8 字节）随锁状态复用：无锁（hash）→ 偏向（线程 ID）→ 轻量级（栈上 Lock Record 指针）→ 重量级（ObjectMonitor 指针）
- **重量级锁**：依赖 OS mutex，涉及**用户态/内核态切换** → 这就是"重"的原因
- **锁升级**（JDK15 起偏向锁默认禁用 JEP 374，重点讲轻量级与重量级）：无竞争 CAS 自旋 → 竞争激烈膨胀为重量级
- **可重入**：Monitor 计数器 + 持有者线程记录

### 3.4 final 的内存语义
- 构造函数内对 final 字段的写，**在对象引用对其他线程可见之前不会被重排出去**（需 this 不逸出）
- 所以**不可变对象（String、final 字段）天然线程安全**——这是"不可变是并发最高策略"的底层依据

---

## 四、CAS 与原子类

| 问题 | 答案 |
|---|---|
| CAS 原理 | `compareAndSwap(内存地址, 期望值, 新值)`，CPU **cmpxchg 指令**（加 lock 前缀保证多核原子）；失败自旋重试 |
| 三大问题 | **ABA**（版本号 AtomicStampedReference）、**自旋开销**（长期失败空转）、**只能保证单变量**（多变量用锁或封装成对象 CAS） |
| AtomicLong vs LongAdder | 前者单 value CAS，高并发全部竞争一个变量；后者 **Cell 数组分段累加**（空间换竞争），`sum()` 非强一致快照 → **统计场景用 LongAdder** |
| 伪共享 | 缓存行 64B，两个独立变量同处于一行 → 互相失效缓存；解法 **@Contended** 填充（LongAdder 的 Cell 就做了） |
| 原子更新字段 | `AtomicIntegerFieldUpdater` / `AtomicReference`（CAS 对象引用）/ `AtomicMarkableReference` |
| Unsafe / VarHandle | Unsafe 底层但危险（JDK 弃用中）；**VarHandle**（JDK9+）是标准化替代 |

---

## 五、AQS 详解（★必须讲透）

> 关键类：`AbstractQueuedSynchronizer`（`java.util.concurrent.locks`）

**结构三件套**：
1. `volatile int state` —— 同步状态（ReentrantLock=重入次数、Semaphore=许可数、CDL=count）
2. **CLH 变体的双向等待队列**——获取失败的线程包装成 Node 入队
3. `LockSupport.park/unpark` —— 阻塞与唤醒

**acquire 骨架（模板方法模式）**：
```java
public final void acquire(int arg) {
    if (!tryAcquire(arg) &&                    // ① 子类实现（钩子）
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))  // ② 入队 + 自旋/park
        selfInterrupt();
}
```
- `tryAcquire` 由子类实现 → **AQS 只管排队、阻塞、唤醒**，语义交给子类——**模板方法模式的教科书**
- 独占模式（ReentrantLock）vs 共享模式（Semaphore/CDL，`setHeadAndPropagate` 连锁唤醒）
- **Condition**：每个 Condition 一个等待队列；`await` 释放锁入条件队列，`signal` 转移到同步队列

**ReentrantLock vs synchronized（深版）**：
| 维度 | synchronized | ReentrantLock |
|---|---|---|
| 实现 | JVM（C++ ObjectMonitor） | Java 层 AQS |
| 公平锁 | 无 | 可选（`hasQueuedPredecessors`） |
| 可中断/超时 | ✗ | `lockInterruptibly` / `tryLock(timeout)` |
| 条件变量 | 单一 wait/notify | **多个 Condition 精准唤醒** |
| 性能 | JDK6 优化后接近 | 接近 |

---

## 六、线程池详解（★★必考之王）

### 6.1 ctl：一个 AtomicInteger 同时存两个值
```java
private final AtomicInteger ctl = new AtomicInteger(ctlOf(RUNNING, 0));
// 高 3 位 = 运行状态（RUNNING=-1<<29 可接受新任务）
// 低 29 位 = 线程数（上限约 5 亿）
```
> 设计意图：**一次 CAS 同时维护状态与数量**——这是位运算复用的经典案例。

### 6.2 execute 源码骨架（三步决策）
```java
public void execute(Runnable command) {
    int c = ctl.get();
    if (workerCountOf(c) < corePoolSize) {          // ① 少于 core → 建核心线程
        if (addWorker(command, true)) return;
        c = ctl.get();
    }
    if (isRunning(c) && workQueue.offer(command)) { // ② 入队（注意先判 running 再入队）
        int recheck = ctl.get();
        if (!isRunning(recheck) && remove(command)) reject(command);  // 双检：入队瞬间 shutdown 了
        else if (workerCountOf(recheck) == 0) addWorker(null, false); // 兜底保活
    }
    else if (!addWorker(command, false))            // ③ 队列满 → 尝试非核心线程
        reject(command);                            // ④ 都不行 → 拒绝策略
}
```
> **追问"为什么先入队再加线程"**：控制总线程数、优先复用；配合"队列满才扩到 max"实现缓冲优先。

### 6.3 Worker 与运行
- `Worker` 继承 AQS（**不可重入锁**：防止在运行任务时被中断）+ 持有首任务
- `runWorker`：循环 `getTask()` 取任务执行；`getTask` 里 core 线程只有 `allowCoreThreadTimeOut` 才超时退出
- `shutdown()`（不再收新任务，跑完存量）vs `shutdownNow()`（中断、返回未执行任务）
- **关闭钩子**：Spring 用 `@PreDestroy` + `awaitTermination` 优雅停机

### 6.4 参数怎么定（不能只背公式）
```
CPU 密集：N + 1（多出的应对缺页/偶发暂停）
IO 密集：N × (1 + 等待时间/计算时间)   ← 精确公式
最终：压测定，配合监控动态调
```
- **IO 密集任务禁止用默认 ForkJoinPool.commonPool()**（CompletableFuture 默认用它，并行度 = CPU-1）
- **监控指标**：活跃线程数、队列长度、**拒绝次数**、任务耗时 P99
- **动态调参**：`setCorePoolSize/setMaximumPoolSize` 支持运行时修改 → 美团"动态线程池"实践：参数放配置中心 + 监控告警

### 6.5 线程池事故四件套
1. `Executors.newFixedThreadPool` → **无界队列 OOM**
2. `newCachedThreadPool` → **线程数爆炸**
3. **submit 吞异常**：异常存在 Future 里，不 get 永远不抛 → 用 execute + UncaughtExceptionHandler
4. **CallerRunsPolicy 的副作用**：回压到调用线程——若是 Tomcat 线程会拖垮上游（先想清楚调用者是谁）

---

## 七、ThreadLocal 深入

- **结构**：每个 Thread 持有 `ThreadLocalMap`；key = ThreadLocal（**弱引用**），value = 强引用；**开放寻址**（线性探测，不是链表）
- **泄漏链路**：key 被 GC → Entry 变 (null, value) → value 被线程强引用 → **线程池线程长活 → 泄漏**
- **唯一正解**：`finally { threadLocal.remove(); }`
- **父子线程传递**：`InheritableThreadLocal`（新建线程时复制）→ **线程池里失效**（线程复用不新建）→ **TransmittableThreadLocal**（阿里 TTL，包装线程池）
- **典型用途**：用户上下文、traceId、事务连接绑定（Spring 事务跨线程失效的根源就在这）
- **陷阱**：ThreadLocalMap 的 key 是弱引用但 **value 不是**——"弱引用不会泄漏"是错误说法

---

## 八、并发容器（源码级）

### ConcurrentHashMap 1.8
| 点 | 细节 |
|---|---|
| 锁粒度 | **CAS 空桶 + synchronized 锁桶头**（首个节点），锁单个桶 |
| hash | `(h ^ (h >>> 16)) & HASH_BITS`（扰动 + 保证非负） |
| 初始化 | 惰性，`sizeCtl = -1` 表示正在初始化（CAS 抢初始化权） |
| **扩容** | **多线程协助扩容**：`transfer`，已迁移桶放 `ForwardingNode`（hash=MOVED）→ 读走新表、写协助迁移；`sizeCtl` 高 16 位是扩容邮戳 |
| 树化 | 链表长 ≥8 **且表长 ≥64**（否则先扩容）；退化阈值 6 |
| size | `baseCount + CounterCell[]`（**LongAdder 思想**分散计数） |
| 复合操作 | `containsKey+put` **不原子** → 用 `putIfAbsent` / `computeIfAbsent` |

### 其他
- **CopyOnWriteArrayList**：写时复制 + volatile 读；读多写极少；**不保证实时一致**（弱一致迭代）
- **BlockingQueue 家族**：ArrayBlocking（有界锁）、LinkedBlocking（默认**无界**危险）、SynchronousQueue（不存，直接交付）、PriorityBlocking、DelayQueue（延迟任务）
- **ConcurrentSkipListMap**：跳表 + CAS，并发有序（替代 TreeMap）

---

## 九、并发工具类与 CompletableFuture

| 工具 | 语义 | 对比 |
|---|---|---|
| `CountDownLatch` | 等 N 个事件完成；**一次性** | countDown/await |
| `CyclicBarrier` | N 个线程互相等齐；**可重置可复用**，支持回调 | parties 到齐 → 翻越栅栏 |
| `Semaphore` | 许可数限流；acquire(n)/release(n) | 公平模式可选 |
| `Exchanger` | 两线程交换数据 | |
| `Phaser` | 多阶段栅栏，可动态注册 | JDK7+ |
| `StampedLock` | **乐观读**（读时不加锁，提交前 `validate`）；**不可重入** | 读多写少极致优化 |

**CompletableFuture 编排（实战模板）**：
```java
ExecutorService pool = /* 自定义线程池，千万别用默认 ForkJoinPool */;
var user  = CompletableFuture.supplyAsync(() -> rpcUser(id), pool);
var order = CompletableFuture.supplyAsync(() -> rpcOrders(id), pool);
var credit= CompletableFuture.supplyAsync(() -> rpcCredit(id), pool);

Profile p = CompletableFuture.allOf(user, order, credit)
        .thenApply(v -> new Profile(user.join(), order.join(), credit.join()))
        .orTimeout(500, TimeUnit.MILLISECONDS)      // JDK9+ 整体超时
        .exceptionally(e -> Profile.fallback());    // 兜底降级
```
**易错点**：① 默认线程池并行度 = CPU-1，IO 任务会饿死 ② `thenApply`（转换）vs `thenCompose`（扁平化嵌套）vs `thenCombine`（合并两个）③ `exceptionally` 只捕上游；`handle` 无论成败都执行且可改结果 ④ `allOf` 不携带结果，要各自 join。

---

## 十、死锁 / 活锁 / 饥饿

- **死锁四条件**：互斥、持有并等待、不可剥夺、循环等待 → **破坏任意一条**即可避免（最常用：**全局固定顺序加锁** + tryLock 超时回退）
- **排查**：`jstack`（找 `Found one Java-level deadlock`）、`jcmd <pid> Thread.print`、Arthas `thread -b`
- **活锁**：都在重试都在让步 → 加随机退避
- **饥饿**：低优先级/非公平锁下拿不到 → 公平锁或资源配额

---

## 十一、并发陷阱清单（★高频 bug 来源）

| # | 陷阱 | 一句话 |
|---|---|---|
| 1 | `SimpleDateFormat` 共享 | 内部 Calendar 有状态 → **ThreadLocal 或 DateTimeFormatter** |
| 2 | HashMap 并发 | 1.7 扩容死循环；1.8 数据覆盖 → CHM |
| 3 | CHM 复合操作不原子 | `containsKey+put` → `putIfAbsent/computeIfAbsent` |
| 4 | submit 吞异常 | 异常锁在 Future 里 → execute + handler |
| 5 | 双重检查忘 volatile | 见 3.2 |
| 6 | `i++` 用 volatile | 不保证原子 → 原子类 |
| 7 | 线程池用默认 ForkJoinPool | IO 任务互相饿死 → 自定义池 |
| 8 | @Async 丢上下文 | traceId/事务都在 ThreadLocal → TTL 包装 |
| 9 | in-flight 单例逸出 | 构造函数里启动线程/注册监听 → this 逸出 |
| 10 | 锁可重入误判 | 内层再拿同一把锁没问题，**拿不同锁要看顺序** |

---

## 十二、手撕并发代码（白板版）

### 12.1 生产者消费者（wait/notify 版，注意 while）
```java
class Buffer {
    private final Queue<Integer> q = new ArrayDeque<>();
    private final int cap = 10;
    public synchronized void put(int v) throws InterruptedException {
        while (q.size() == cap) wait();      // while 防虚假唤醒
        q.offer(v); notifyAll();
    }
    public synchronized int take() throws InterruptedException {
        while (q.isEmpty()) wait();
        int v = q.poll(); notifyAll(); return v;
    }
}
```
> 生产首选 `ArrayBlockingQueue`（put/take 天然阻塞）；手写版要能解释 while 与 notifyAll。

### 12.2 两线程交替打印 1~100（Semaphore 版）
```java
Semaphore odd = new Semaphore(1), even = new Semaphore(0);
new Thread(() -> { for (int i = 1; i <= 100; i += 2) {
    odd.acquireUninterruptibly(); System.out.println(i); even.release(); } }).start();
new Thread(() -> { for (int i = 2; i <= 100; i += 2) {
    even.acquireUninterruptibly(); System.out.println(i); odd.release(); } }).start();
```

### 12.3 令牌桶限流器
```java
class TokenBucket {
    private final long capacity; private final double rate; // 每秒生成
    private long tokens; private long last = System.nanoTime();
    TokenBucket(long cap, double perSec) { capacity = cap; rate = perSec; tokens = cap; }
    synchronized boolean tryAcquire() {
        long now = System.nanoTime();
        tokens = Math.min(capacity, tokens + (long) ((now - last) / 1e9 * rate));
        last = now;
        if (tokens >= 1) { tokens--; return true; }
        return false;
    }
}
```
> 要点：**懒生成令牌**（按时间差补），容量封顶，synchronized 保证原子。

### 12.4 三种线程安全单例
```java
// 1. DCL（见 3.2）
// 2. 静态内部类：类加载天然线程安全 + 懒加载
class S { private S() {} private static class H { static final S I = new S(); }
          static S get() { return H.I; } }
// 3. 枚举：防反射 + 防序列化
enum S2 { INSTANCE; }
```

### 12.5 并行聚合三路 RPC（见第九节 CompletableFuture 模板）

---

## 十三、快答 20 题（一行答案）

1. volatile 能解决 count++ 吗？→ 不能，只保可见有序
2. i++ 是原子的吗？→ 不是，读改写三步
3. synchronized 修饰 static 方法锁什么？→ 类对象（Class 实例）
4. ReentrantLock 可重入怎么实现？→ state 累加 + 持有线程记录
5. 公平锁的实现？→ `hasQueuedPredecessors` 判断队列
6. AQS 独占和共享的区别？→ 唤醒后继时是否传播（setHeadAndPropagate）
7. Condition 和 wait/notify 区别？→ 多条件队列、精准唤醒、不依赖 synchronized
8. CHM 的 key/hash 能为 null 吗？→ 都不能（二义性问题）
9. CHM 扩容时读怎么办？→ ForwardingNode 转发到新表
10. CopyOnWrite 适合什么？→ 读极多写极少，容忍弱一致
11. 线程池队列满了策略？→ 扩 max 线程 → 拒绝策略（4 种）
12. 如何让核心线程也回收？→ `allowCoreThreadTimeOut(true)`
13. FutureTask 的状态机？→ NEW→COMPLETING→NORMAL/EXCEPTIONAL→...
14. CountDownLatch 能复用吗？→ 不能（CyclicBarrier 能）
15. Semaphore 实现 fairness？→ AQS 构造传 fair，队列顺序获取
16. ThreadLocalMap 冲突解决？→ 开放寻址（线性探测）
17. 如何跨线程池传上下文？→ TransmittableThreadLocal（TTL）
18. 读写锁的降级？→ 写锁 → 读锁允许（锁降级），反过来不行
19. StampedLock 乐观读？→ tryOptimisticRead + validate 校验版本
20. 单例防反射/序列化？→ 枚举

---

## 十四、手画清单 + 话术

**手画四图**：
- [ ] 线程状态机（6 状态及触发）
- [ ] AQS acquire 流程（tryAcquire → 入队 → park）
- [ ] 线程池 execute 决策树（core → 队列 → max → 拒绝）
- [ ] CHM putVal 分支（空桶 CAS / 非空锁头 / 协助扩容）

**一分钟话术**：
> "并发我按 JMM → 锁 → 工具 → 治理四层理解。
> JMM 层：所有可见性有序性问题用 happens-before 判断，volatile 靠内存屏障实现；
> 锁层：synchronized 的锁升级我清楚 Mark Word 状态流转，AQS 的模板方法设计——
> 框架管排队阻塞，语义交子类 tryAcquire；
> 工具层：线程池的 ctl 位运算、execute 三步决策、拒绝策略的副作用我都踩过；
> 治理层：**所有远程调用必须有超时、所有共享可变状态要么不可变要么有同步策略、
> 异常不允许被线程池吞掉**——并发问题靠评审清单预防，不靠上线后修。"

## 📥 待补充
- [ ] 真实用过 LongAdder/Semaphore/StampedLock 的场景各 1 个
- [ ] 一次真实并发 bug（如线程池打满/死锁/CHM 复合操作）的排查故事

## 🔗 关联
[[02-并发与多线程]]（速查）· [[面试准备/专业技能/05-并发]]（治理场景）· [[面试准备/冠顿/05-并发]]

#面试 #Java #并发 #AQS #线程池 #待补
