---
title: 02-Java核心与微服务
tags: [面试, 专业技能, Java, 并发, Spring, 微服务, 源码]
status: 进行中
---

# ☕ 02 · Java 核心与微服务

> 返回 [[00-总览与复习优先级]] · 基础八股见 [[面试准备/技术面试题库/02-并发与多线程|通用题库·并发]]

> [!quote] 简历原话
> 精通 Java、高并发编程，深入掌握 Spring Boot/Cloud、Spring MVC、MyBatis 框架源码与设计模式

> [!danger] 最高危模块
> 你写了「**源码**」和「**精通高并发**」——这两条会把面试官直接引向源码级追问。
> 本篇只放**深挖题**，基础题请回通用题库。

---

## 一、Java 高并发（深挖级）

| 问题                           | 得分骨架                                                                                                                                                           |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AQS 源码**                   | `state`（volatile int）+ CLH 变体双向队列；`acquire` → `tryAcquire` 失败 → `addWaiter` 入队 → `acquireQueued` 自旋 + `LockSupport.park`；释放时 `unparkSuccessor`；**模板方法模式**的典型应用 |
| **ReentrantLock 公平锁怎么实现**    | `hasQueuedPredecessors()` 判断队列前是否有等待者；非公平锁直接 CAS 抢                                                                                                             |
| **线程池源码**                    | `execute` → `addWorker`（CAS 增 ctl）→ `runWorker` 循环 `getTask`；`ctl` 高 3 位存状态、低 29 位存线程数；`allowCoreThreadTimeOut`                                                |
| **ConcurrentHashMap 1.8 扩容** | `transfer` 多线程协助扩容；`ForwardingNode` 标记已迁移；`sizeCtl` 控制；`helpTransfer`                                                                                          |
| **LongAdder 原理**             | 分段 Cell 数组分散 CAS 热点；`sum()` 非强一致（**用空间换竞争**）                                                                                                                   |
| **伪共享**                      | CPU 缓存行 64 字节；`@Contended` 填充；`LongAdder` 的 Cell 就做了填充                                                                                                         |
| **CAS 的 ABA**                | 版本号 `AtomicStampedReference`；`Unsafe.compareAndSwapObject`                                                                                                     |
| **happens-before 八条**        | 程序顺序、监视器锁、volatile、线程 start/join、传递性、中断、对象终结、并发工具                                                                                                              |
| **无锁编程**                     | CAS 循环、`AtomicXXX`、`VarHandle`（JDK9+）、`StampedLock` 乐观读                                                                                                        |
| **CompletableFuture 编排**     | `thenApply`（同类型转换）vs `thenCompose`（嵌套扁平化）、`thenCombine`、`allOf`/`anyOf`、`exceptionally`/`handle`；**默认用 ForkJoinPool，IO 任务要传自定义线程池**                            |
| **异步 vs 响应式**                | 异步（CompletableFuture）简单但会阻塞线程；响应式（Reactor）非阻塞但调试难、生态侵入强                                                                                                        |
| **锁优化实战**                    | 减小锁粒度、锁分离（读写锁）、无锁（CAS）、减少持有时间、避免锁嵌套、用 `LongAdder` 替代 `AtomicLong` 做统计                                                                                          |

---

## 二、Spring 源码（**写了"源码"就会被问**）

> [!tip] 完整源码专题 → [[面试准备/技术面试题库/13-Spring源码专题]]（refresh 十二步 / 三级缓存源码 / 事务链路 / MVC·Boot·MyBatis 源码 / 排查案例），下面只留速记骨架。

### 2.1 IoC 容器

| 问题 | 得分骨架 |
|---|---|
| **`refresh()` 十二步** | ①`prepareRefresh` ②`obtainFreshBeanFactory` ③`prepareBeanFactory` ④`postProcessBeanFactory` ⑤`invokeBeanFactoryPostProcessors` ⑥`registerBeanPostProcessors` ⑦`initMessageSource` ⑧`initApplicationEventMulticaster` ⑨`onRefresh`（**内嵌 Tomcat 在这里创建**）⑩`registerListeners` ⑪`finishBeanFactoryInitialization`（**单例 Bean 在这里实例化**）⑫`finishRefresh`（**WebServer.start 启动** + 发布 ContextRefreshedEvent） |
| **Bean 生命周期（源码级）** | `getBean` → `doGetBean` → `createBean` → `doCreateBean`：`createBeanInstance`（实例化）→ `populateBean`（属性填充）→ `initializeBean`（Aware → `applyBeanPostProcessorsBeforeInitialization` → `invokeInitMethods` → `applyBeanPostProcessorsAfterInitialization`，**AOP 代理在最后一步生成**） |
| **三级缓存源码** | `getSingleton` 里：一级 `singletonObjects`（成品）→ 二级 `earlySingletonObjects`（半成品）→ 三级 `singletonFactories`（`ObjectFactory`）。**第三级的存在是为了在需要时提前生成 AOP 代理** |
| **为什么要第三级而不是两级** | 若 A 需要被代理，B 注入的必须是代理对象。工厂可在"被依赖时"才决定是否生成代理，保证单例且代理正确 |
| **`@Autowired` 注入时机** | `AutowiredAnnotationBeanPostProcessor`（`InstantiationAwareBeanPostProcessor`）在 `populateBean` 阶段完成 |
| **`BeanFactoryPostProcessor` vs `BeanPostProcessor`** | 前者改**BeanDefinition**（更早）；后者改**Bean 实例** |

### 2.2 AOP 与事务

| 问题 | 得分骨架 |
|---|---|
| AOP 代理创建时机 | `AbstractAutoProxyCreator.postProcessAfterInitialization` |
| JDK 动态代理 vs CGLIB | 接口 vs 继承；Spring Boot 2.x 默认 `proxyTargetClass=true`（CGLIB） |
| **`@Transactional` 源码链路** | 代理 → `TransactionInterceptor.invoke` → `createTransactionIfNecessary`（拿 `PlatformTransactionManager`）→ `invokeWithinTransaction` → 异常时 `completeTransactionAfterThrowing` 回滚 |
| 事务传播源码 | `AbstractPlatformTransactionManager.handleExistingTransaction`；`REQUIRES_NEW` 会 `suspend` 当前事务 |
| 事务失效 8 场景 | 自调用、非 public、异常被吞、受检异常、类未被管理、多线程、引擎不支持、传播行为不当 |
| **事务同步** | `TransactionSynchronizationManager` 用 `ThreadLocal` 绑定连接 → **所以跨线程事务失效** |
| `@Async` 与事务 | 异步方法在子线程，拿不到父线程事务 → 常见坑 |

---

## 三、Spring MVC 源码

| 问题 | 得分骨架 |
|---|---|
| **`DispatcherServlet.doDispatch` 九步** | ① 取 HandlerMapping ② 找 HandlerExecutionChain（含拦截器）③ 取 HandlerAdapter ④ `applyPreHandle` ⑤ 实际调用 handler（参数解析 + 返回值处理）⑥ `applyPostHandle` ⑦ 处理返回 ModelAndView ⑧ `processDispatchResult`（视图渲染 / 异常处理）⑨ `triggerAfterCompletion` |
| 参数解析 | `HandlerMethodArgumentResolver` 链（`@RequestParam`/`@RequestBody`/`@PathVariable`） |
| 返回值处理 | `HandlerMethodReturnValueHandler` 链（`@ResponseBody` 走 `RequestResponseBodyMethodProcessor`） |
| 拦截器 vs 过滤器 | Filter 属 Servlet 规范（更外层、拿不到 handler）；Interceptor 属 Spring（能拿 handler、能拿 ModelAndView） |
| 异常处理 | `HandlerExceptionResolver` 链 + `@ControllerAdvice` |
| 为什么是九步 | 面试时能按顺序说清即可，**重点是能讲"扩展点在哪"**（HandlerMapping/Adapter/Resolver/Interceptor 都可替换） |

---

## 四、Spring Boot / Cloud 源码

| 问题 | 得分骨架 |
|---|---|
| **自动装配源码** | `@SpringBootApplication` → `@EnableAutoConfiguration` → `@Import(AutoConfigurationImportSelector)` → 读 `META-INF/spring.factories`（2.7+ 改 `AutoConfiguration.imports`）→ `@ConditionalOnClass/OnMissingBean/OnProperty` 过滤 → 注册 BeanDefinition |
| **`SpringApplication.run` 流程** | 推断应用类型 → 加载 `ApplicationContextInitializer` / `ApplicationListener`（spring.factories）→ 准备 Environment（配置加载）→ 创建容器 → `refresh()`（**内嵌容器在 `onRefresh` 启动**）→ `callRunners` |
| 配置加载优先级 | 命令行 > `SPRING_APPLICATION_JSON` > 环境变量 > `application-{profile}` > `application` |
| 内嵌 Tomcat 启动 | `ServletWebServerFactory` + `ServletWebServerApplicationContext.onRefresh` → `createWebServer` |
| 自定义 starter | 自动配置类 + `imports` 文件 + `@ConditionalOnMissingBean` 兜底 |
| **Spring Cloud 组件全景** | 注册中心 Nacos/Eureka、配置中心 Nacos/Apollo、网关 Gateway、负载均衡 LoadBalancer、声明式调用 Feign、熔断限流 Sentinel、链路追踪 SkyWalking、分布式事务 Seata |
| Gateway 原理 | 基于 WebFlux 响应式；`RoutePredicateHandlerMapping` 匹配断言 → 过滤器链（Global + Route） |
| 服务雪崩与治理 | 超时、重试（谨慎）、熔断、隔离、限流、降级 |
| 分布式事务 | 2PC/TCC/Saga/本地消息表/Seata AT（详见 [[面试准备/技术面试题库/09-分布式与微服务|通用题库·分布式]]） |

---

## 五、MyBatis 源码

| 问题 | 得分骨架 |
|---|---|
| **执行流程** | `SqlSessionFactoryBuilder` → `SqlSessionFactory` → `SqlSession` → `Executor` → `StatementHandler` → `ParameterHandler` → `ResultSetHandler` |
| **Executor 三种** | `SimpleExecutor`（默认）、`ReuseExecutor`（复用 Statement）、`BatchExecutor`（批量）；都被 `CachingExecutor` 包装（二级缓存） |
| **四大对象 + 插件** | `Executor` / `StatementHandler` / `ParameterHandler` / `ResultSetHandler`；插件通过 `Interceptor` + JDK 动态代理**层层包装**（责任链） |
| **Mapper 接口原理** | `MapperProxyFactory` 生成 JDK 动态代理，`MapperMethod` 分发到 `SqlSession` 对应方法 |
| **一级缓存** | `SqlSession` 级（`BaseExecutor.localCache`），默认开；**增删改会清空**；Spring 下同事务内有效 |
| **二级缓存** | `CachingExecutor` + namespace 级；需 `cacheEnabled`；**分布式下易脏读，慎用** |
| **`#{}` vs `${}`** | 预编译占位（防注入）vs 字符串拼接（**注入风险**，仅动态表名/排序用） |
| 动态 SQL 原理 | `SqlSource` + `SqlNode` 组合树，`DynamicContext` 拼装 |
| 延迟加载 | `ResultLoader` + `ProxyFactory` 生成代理，访问时才查 |

---

## 六、设计模式（要能说"在哪个框架里怎么用的"）

| 模式 | Spring/MyBatis 中的体现 |
|---|---|
| **单例** | Spring Bean 默认单例（`DefaultSingletonBeanRegistry`） |
| **工厂** | `BeanFactory`、`FactoryBean`、`SqlSessionFactory` |
| **模板方法** | `JdbcTemplate`、`AbstractPlatformTransactionManager`、**AQS 的 `tryAcquire`** |
| **代理** | AOP（JDK/CGLIB）、MyBatis 插件、`MapperProxy` |
| **责任链** | 拦截器链、过滤器链、MyBatis 插件链 |
| **策略** | `InstantiationStrategy`、`Resource` 加载策略、事务传播 |
| **观察者** | `ApplicationEvent` / `ApplicationListener` |
| **适配器** | `HandlerAdapter`、`AdvisorAdapter` |
| **装饰器** | `HttpServletRequestWrapper`、`CachingExecutor` |
| **建造者** | `SqlSessionFactoryBuilder`、`BeanDefinitionBuilder` |
| **组合** | `CompositeFilter`、`SqlNode` 树 |

> [!tip] 加分答法
> 别只背"XX 模式是啥"，要说**"Spring 哪里用了它、解决什么问题"**。
> 例：「AQS 用了模板方法，把获取锁的差异留给子类 `tryAcquire`，框架只负责排队和阻塞。」

---

## 七、⚠️ 翻车点自查

- [ ] 能说出 `refresh()` 的关键步骤，而不是"启动容器"
- [ ] 能讲**三级缓存为什么必须三级**（不是背结论）
- [ ] 能讲事务失效的**至少 5 个原因**及原理
- [ ] 能画出 `doDispatch` 主流程
- [ ] 能说出 MyBatis **四大对象**名字
- [ ] 设计模式能对应到**具体框架类名**
- [ ] AQS / 线程池能讲到**源码方法名**

> 任何一条打不上勾，面试时**主动降级表述**："这块我了解原理，源码细节我可能记不全。"

---

## 八、话术模板

> "Java 这块我最熟的是并发和 Spring 源码。并发上我系统看过 AQS 和线程池的实现，
> 在 X 项目里做过线程池参数调优和锁竞争优化，QPS 从 X 提到 Y。
> Spring 我理解得比较透的是 IoC 容器启动流程和事务的实现，
> 之前排查过一个事务失效问题（自调用导致代理没生效），最后用 AopContext 解决的。"

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与复习优先级]] · [[01-AI应用工程化]] · [[03-高并发中间件]]
- [[面试准备/技术面试题库/02-并发与多线程]] · [[面试准备/技术面试题库/05-Spring与框架]]

#面试 #Java #并发 #Spring #源码 #待补
