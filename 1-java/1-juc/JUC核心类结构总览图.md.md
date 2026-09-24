以下为你整理的 JUC（`java.util.concurrent`）核心类结构总览图。

  

整个 JUC 体系按照职责可以清晰地划分为四大支柱：**锁与显式同步体系（AQS/AOS 衍生）**、**条件变量与协作体系**、**任务编排与线程池体系**、以及**并发容器与数据结构体系**。

  

### JUC 核心类与接口结构总览

Plaintext

```
==================================================================================================
                                    JUC 核心类结构总览
==================================================================================================

【一、锁与同步器抽象体系（底层同步骨架）】

                     java.lang.Object
                            │
              AbstractOwnableSynchronizer (AOS: 维护独占线程所有权)
                            │ extends
              AbstractQueuedSynchronizer (AQS: FIFO等待队列 + volatile int state)
                ▲                     ▲
                │                     │
          (内部继承 Sync)       (内部继承 Sync)
                │                     │
         ReentrantLock      ReentrantReadWriteLock ─── implements ──► ReadWriteLock (顶层接口)
       (implements Lock)      ├─ Sync.HoldCounter                       ├─ readLock() -> Lock
                              ├─ ReadLock (implements Lock)             └─ writeLock() -> Lock
                              └─ WriteLock (implements Lock)

  * 注：AQS 另有 64 位版本 AbstractQueuedLongSynchronizer (AQLS)。


--------------------------------------------------------------------------------------------------

【二、显式锁契约与条件变量体系】

      <<interface>>                                       <<interface>>
          Lock                                              Condition
    (显式互斥锁顶层契约)                                 (多条件变量等待/唤醒契约)
      ├─ lock()                                           ├─ await()
      ├─ tryLock()                                        ├─ signal()
      ├─ lockInterruptibly()                              └─ signalAll()
      ├─ unlock()                                                ▲
      └─ newCondition() ──── 创建关联 ────┐                      │ implements
            ▲                             │             AbstractQueuedSynchronizer
            │ implements                  └───────────►   .ConditionObject
     ┌──────┴────────────────┐                          (AQS 内部类: 条件等待单向队列)
ReentrantLock     ReentrantReadWriteLock
                  (ReadLock / WriteLock)


--------------------------------------------------------------------------------------------------

【三、任务执行与线程池服务体系（Executor 骨架）】

             <<interface>>
               Executor (最顶层单方法接口: void execute(Runnable))
                  ▲
                  │ extends
             <<interface>>
            ExecutorService (生命周期管理: submit, shutdown, invokeAll...)
            ▲             ▲
    extends │             │ extends
<<interface>>             AbstractExecutorService (骨架抽象实现)
ScheduledExecutorService    ▲            ▲
(支持定时与延时调度)        │            │ implements / extends
    ▲                       │            └─────────────────────────┐
    │ implements            │                                      │
ScheduledThreadPoolExecutor ┼──────────────────────────────┐       │
                            │                              │       │
                   ThreadPoolExecutor                 ForkJoinPool │
             (核心通用线程池: 核心数/队列/拒绝策略)       (分治计算与工作窃取)


  【关联的结果与辅助体系】
    <<interface>> Future<V> ◄─── FutureTask<V> (implements RunnableFuture<V>)
    <<interface>> CompletionService<V> ◄─── ExecutorCompletionService<V>


--------------------------------------------------------------------------------------------------

【四、并发容器与传输通道体系】

          java.util.Collection                         java.util.Map
                   ▲                                         ▲
                   │ extends                                 │ extends
           <<interface>> Queue                         <<interface>>
                   ▲                                   ConcurrentMap
                   │ extends                                 ▲
                   │                                         │ implements
           <<interface>> BlockingQueue ───────────────► ConcurrentHashMap
           (阻塞队列顶层接口: put/take)               ConcurrentSkipListMap
            ▲              ▲
            │ extends      │ implements
     <<interface>>         ├─ ArrayBlockingQueue (有界数组)
     TransferQueue         ├─ LinkedBlockingQueue (可选有界链表)
     (直接传递契约)        ├─ PriorityBlockingQueue (优先级堆)
            ▲              ├─ SynchronousQueue (零容量直接移交)
            │ implements   └─ DelayQueue (延时出队)
     LinkedTransferQueue
```

### 结构图核心脉络解析

1. **AOS / AQS 与 Lock 的关系（装饰与实现解耦）**：
    - `Lock` 和 `ReadWriteLock` 是**面向开发者**的公共 API 接口契约；
    - `AOS` / `AQS` 是**框架底层**的同步抽象类（非公共 API，专门供内部继承）；
    - `ReentrantLock` 并不是直接继承 AQS，而是在其内部定义了一个继承自 AQS 的私有静态内部类 `Sync`（进而派生出 `NonfairSync` 和 `FairSync`），采用了标准的**组合 + 模板方法模式**。
2. **Condition 与 AQS 的深层绑定**：
    - `Condition` 仅是一个抽象接口；
    - 它的真实实现在 AQS 内部的私有内部类 `ConditionObject` 中；
    - 一个 `ReentrantLock` 实例可以通过 `lock.newCondition()` 生成多个 `ConditionObject`，每个对象内部都维护一条独立的**单向条件队列**，从而实现对线程的精准分组挂起与唤醒。
3. **双轴线设计**：
    - **同步控制轴**：从最底层的线程持有者标记（`AOS`），到排队控制骨架（`AQS`），再到外层锁门面（`Lock` / `ReadWriteLock`）；
    - **异步计算轴**：从最顶层的命令执行器（`Executor`），到带状态控制的服务（`ExecutorService`），再到具体落地的线程池（`ThreadPoolExecutor`、`ForkJoinPool`）。