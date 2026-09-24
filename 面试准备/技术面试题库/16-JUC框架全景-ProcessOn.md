---
title: 16-JUC框架全景（ProcessOn 思维导图）
tags: [面试, Java, 技术题库, JUC, 并发, 思维导图]
status: 进行中
来源: https://www.processon.com/view/5da7bfcbe4b0ea86c2b3dbae
---

# 🗺️ 16 · JUC 框架全景（ProcessOn 思维导图）

> 返回 [[00-总览与使用说明]] · 姊妹篇：[[15-Java并发专题]]（原理详解）· [[02-并发与多线程]]（速查）· [[juc.excalidraw]]（自己的手绘图）

> [!info] 来源与定位
> - 原图：[ProcessOn · JUC 思维导图模板](https://www.processon.com/view/5da7bfcbe4b0ea86c2b3dbae)（2019 年模板，内容框架与 skywang12345《Java 多线程系列》一致）
> - 原图已下载到本笔记同目录 `attachments/JUC-ProcessOn.png`（3301×4718，可放大细看）
> - **分工**：这张图 = **JUC 类库全景**（四大块的类与继承关系）；
>   [[15-Java并发专题]] = **面试原理详解**（JMM/AQS/线程池源码）。两者互补，先看这张建立地图，再进 15 深挖。

> [!warning] 时效性标注（重要）
> 这张图基于 **Java 8 早期视角**（2019 年制作）：
> - ❗ **ConcurrentHashMap 部分讲的是 1.7 的 Segment 分段锁**——现在面试主考 **1.8 的 CAS + synchronized 锁桶头**（见 [[15-Java并发专题]] 第八节）
> - ✅ 原子类分类、AQS 结构、线程池体系、阻塞队列分类至今仍然准确
> - 偏向锁：图的时代还默认开启，**JDK15 起默认禁用（JEP 374）**

![[JUC-ProcessOn.png]]

---

## 一、JUC 原子类（四大类）

- **基本类型**：AtomicInteger、AtomicLong、AtomicBoolean
	- AtomicLong：对长整型原子操作
- **数组类型**：AtomicIntegerArray、AtomicLongArray、AtomicReferenceArray
	- 对"数组内元素"原子操作
- **引用类型**：AtomicReference、AtomicStampedReference、AtomicMarkableReference
	- AtomicReference：对"对象"原子操作
	- **AtomicStampedReference：带版本号 → 解决 ABA**（高频考点）
- **对象属性更新器**：AtomicIntegerFieldUpdater、AtomicLongFieldUpdater、AtomicReferenceFieldUpdater
	- 基于**反射**，对指定类的 volatile 字段原子更新（不用改类结构）

> 对应详解 → [[15-Java并发专题]] 第四节（CAS 三大问题、LongAdder、伪共享）

---

## 二、JUC 锁（框架与 AQS）

### 2.1 框架分层
- **接口层**：Lock、ReadWriteLock、LockSupport（阻塞原语）、Condition
- **抽象类**：AbstractOwnableSynchronizer / **AbstractQueuedSynchronizer(AQS)** / AbstractQueuedLongSynchronizer
- **实现层**：ReentrantLock（独占）、ReentrantReadWriteLock（读写）
- CountDownLatch、CyclicBarrier、Semaphore **都是基于 AQS 共享模式实现**

### 2.2 三个基本概念
- **AQS**：AbstractQueuedSynchronizer，分"独占锁"和"共享锁"两种模式
- **CLH 队列**：Craig, Landin, and Hagersen queue——AQS 中"等待锁"的线程队列
- **CAS 函数**：Compare And Swap，原子比较并交换

### 2.3 AQS 独占模式核心流程（★背）
`acquire()`
1. **tryAcquire()**：尝试直接获取资源，成功直接返回
2. **addWaiter()**：失败则将当前线程加入等待队列队尾
3. **acquireQueued()**：在队列中自旋 + 阻塞地获取资源；返回值表示等待过程中是否被中断过
4. **selfInterrupt()**：补上中断标记

`release()`
- **tryRelease()**：释放资源；成功且有等待线程 → **unparkSuccessor(Node)** 唤醒队头后继

### 2.4 关键组件
- **Mutex 示例**：不可重入互斥锁的最简 AQS 实现（state 0/1 两态）
- **Condition**：更精细的多线程休眠/唤醒控制（多条件队列）
- **LockSupport**：park()/unpark() 阻塞原语；**避免 Thread.suspend/resume 的死锁问题**（先 unpark 后 park 也不会卡死）
- **ReentrantReadWriteLock**：读写分离，读读共享

### 2.5 三大同步工具（都是 AQS 共享锁）
- **CountDownLatch**：计数器初始 count，`countDown()` 减 1，**减到 0** 时等待的线程才能继续；**一次性**
- **CyclicBarrier**：一组线程互相等待到**公共屏障点**；可复用
- **Semaphore**：计数信号量（共享锁）；acquire 取许可、release 还许可

> 对应详解 → [[15-Java并发专题]] 第五节（AQS 源码骨架、公平锁、Condition）

---

## 三、JUC 线程池

### 3.1 类图体系
```
Executor（接口：execute）
  └─ ExecutorService（接口：submit / invokeAll / invokeAny / shutdown）
       └─ AbstractExecutorService（抽象类：默认实现）
            ├─ ThreadPoolExecutor            ← 核心实现
            └─ ScheduledThreadPoolExecutor
                 （ScheduledExecutorService：延时 + 周期执行）
```
- **Executor 存在的目的**：将"**任务提交**"与"**任务如何运行**"分离
- **Callable + Future**：Callable 有返回值可抛异常；Future 表示异步计算结果

### 3.2 线程池 5 种状态
RUNNING → SHUTDOWN → STOP → TIDYING → TERMINATED

### 3.3 四种拒绝策略
| 策略 | 行为 |
|---|---|
| AbortPolicy（默认） | 抛 RejectedExecutionException |
| CallerRunsPolicy | **由提交任务的线程自己执行**（天然背压，但会拖慢调用方） |
| DiscardOldestPolicy | 丢队列最老任务，腾位给新任务 |
| DiscardPolicy | 静默丢弃 |

### 3.4 ThreadPoolExecutor 三大入口
- **创建**：构造 7 参数（core/max/keepAlive/unit/workQueue/threadFactory/handler）
	- ThreadFactory：统一创建线程（命名、daemon）
	- RejectedExecutionHandler：拒绝策略句柄
- **提交**：execute()（核心）；submit() **底层也是 execute()**
- **关闭**：shutdown() / shutdownNow()

### 3.5 Executors 四个工厂的坑（★高频）
| 工厂 | 参数 | 风险 |
|---|---|---|
| newCachedThreadPool | core=0, max=**Integer.MAX_VALUE**, SynchronousQueue | **线程数爆炸** |
| newSingleThreadExecutor | core=max=1, **LinkedBlockingQueue（无界）** | **队列堆积 OOM** |
| newFixedThreadPool | core=max=N, **LinkedBlockingQueue（无界）** | **队列堆积 OOM** |
| newScheduledThreadPool | 定长，延时/周期 | 任务异常会中断周期（需捕获） |

> 结论：**生产手动 new ThreadPoolExecutor**（阿里规约同款结论）
> 对应详解 → [[15-Java并发专题]] 第六节（ctl 位运算、execute 源码、Worker）

---

## 四、JUC 集合

### 4.1 普通集合的线程安全性
- List：LinkedList / ArrayList / Vector(线程安全) / Stack
- Map：HashMap(不安全) / **Hashtable(线程安全，全表锁，过时)** / TreeMap / WeakHashMap（键弱引用）
- 结论：**普通集合单线程用；并发场景一律进 JUC 包**

### 4.2 JUC 集合分类记忆
| 类别 | 类 |
|---|---|
| **写时复制** | CopyOnWriteArrayList / CopyOnWriteArraySet（内部就是 COWArrayList） |
| **锁分段/桶级锁** | ConcurrentHashMap（图中讲 1.7 Segment；**1.8 改 CAS+synchronized** → [[15-Java并发专题]]） |
| **跳表** | ConcurrentSkipListMap / ConcurrentSkipListSet（跳表替代红黑树，插入删除简单） |
| **阻塞队列** | ArrayBlockingQueue（数组**有界**）/ LinkedBlockingQueue（链表，**默认 Integer.MAX_VALUE 无界**）/ LinkedBlockingDeque（双向）/ ConcurrentLinkedQueue（CAS 无界非阻塞） |

> [!tip] CopyOnWriteArrayList 原理两句话
> ① 动态数组机制：内部 **volatile 数组**，增删改都"新建数组 → 拷贝 → 替换引用"
> ② 线程安全机制：改动时**先拿互斥锁**，更新 volatile 数组后释放——读永远读旧/新完整版本，**弱一致**

---

## 五、这张图怎么用（复习路径）

1. **先用这张图建框架**：JUC 四大块（原子类 / 锁 / 线程池 / 集合）的类与继承关系
2. **再进 [[15-Java并发专题]] 深挖原理**：JMM、AQS 源码、线程池源码、CHM 1.8
3. **自查两张图差集**：这张图没有的（但面试常问）→ happens-before、CompletableFuture、虚拟线程（JDK21）、StampedLock → 都在 15 里
4. 你自己的手绘版 → [[juc.excalidraw]]（线程基础部分，可把这张图的四分支补画进去）

## 📥 待补充
- [ ] 把四大分支各自手画一遍（照着上图默画，比看十遍有效）

## 🔗 关联
[[15-Java并发专题]] · [[02-并发与多线程]] · [[juc.excalidraw]] · [[面试准备/专业技能/05-并发]]

#面试 #JUC #并发 #思维导图 #待补
