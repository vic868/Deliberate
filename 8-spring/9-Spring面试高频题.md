---
title: Spring 面试高频题
tags: [Spring, 面试, 高频, 复习]
status: 进行中
created: 2026-10-10
---

# 🎯 九、Spring 面试高频题

> 本篇按**面试问答**组织：每题先给"得分骨架"，再给深入追问与易错点，最后回链深度笔记。
> 覆盖 IoC/AOP/事务/MVC/Boot/进阶六类，共 12 道必答题。
> 答题原则：**骨架 + 一个类名或方法名 + 一个踩过的坑**（面试官不要求默写源码，要求说得出主流程、类名、设计意图）。
> 关联：[[0-Spring总览]]、[[面试准备/技术面试题库/13-Spring源码专题|Spring 源码专题（速答骨架）]]、[[面试准备/专业技能/02-Java核心与微服务]]。

---

## 一、十二道必答题

### Q1. IoC 和 DI 是什么关系？

> [!important] 得分骨架
> **IoC 是设计思想，DI 是实现方式。**
> - **IoC（控制反转）**：对象的创建与依赖装配的控制权，从**业务代码**反转给**容器**——从"我 new"变成"容器给我"。
> - **DI（依赖注入）**：容器把依赖**注入**进来的具体手段（构造器 / setter / 字段）。
> - **一句话**：IoC 是"谁控制"的问题，DI 是"怎么给"的问题，**它们是同一件事的两个视角**。

**追问：为什么推荐构造器注入？**
① 依赖可声明为 `final`，**不可变且非空**；② 依赖关系**显式暴露**（构造器参数多说明职责过重）；③ **便于单元测试**（不用容器也能 new）；④ **能暴露循环依赖**（Spring 会直接启动失败，而不是悄悄注入半成品）。
字段注入的问题：无法 final、测试要反射、隐藏了"这个类依赖太多东西"的信号。

详见 [[1-Spring架构与IoC容器]]。

---

### Q2. `BeanFactory` 和 `ApplicationContext` 有什么区别？

> [!important] 得分骨架
> `ApplicationContext` **继承并扩展**了 `BeanFactory`：
> | 能力 | BeanFactory | ApplicationContext |
> |---|---|---|
> | 依赖注入 | ✅ | ✅ |
> | **预实例化单例** | ❌（懒加载） | ✅（启动时创建） |
> | **事件发布** | ❌ | ✅ |
> | **国际化（MessageSource）** | ❌ | ✅ |
> | **资源加载（ResourcePatternResolver）** | ❌ | ✅ |
> | **自动注册 BFPP/BPP** | ❌ | ✅ |
>
> **本质区别**：`BeanFactory` 是**最底层的容器接口**（DI 的最小能力），`ApplicationContext` 是**面向应用的门面**。

**追问：为什么 ApplicationContext 默认预实例化单例？**
把配置错误**提前到启动时暴露**（fail-fast），而不是等第一次调用才发现。

**追问：父子容器是什么？为什么 Spring MVC 要分父子？**
`ContextLoaderListener` 创建**根容器**（Service/DAO），`DispatcherServlet` 创建**子容器**（Controller）。子容器能拿到父容器的 Bean，**反过来不行**。
**踩坑**：如果把 `@Transactional` 的 Service 扫进了子容器（只扫了 Controller 应该扫的包却扩大了范围），**事务可能失效或出现两个同名 Bean**；`web.xml`/配置类里**扫描范围重叠**是常见事故源。

详见 [[1-Spring架构与IoC容器]]。

---

### Q3. Bean 的生命周期？

> [!important] 得分骨架（顺序要记牢）
> **实例化 → 属性填充 → Aware 回调 → BPP 前置 → `@PostConstruct` → `afterPropertiesSet` → `init-method` → BPP 后置（AOP 代理在此生成）→ 就绪**
> 销毁：`@PreDestroy` → `DisposableBean.destroy` → `destroy-method`

**追问：`@PostConstruct` / `afterPropertiesSet` / `init-method` 谁先执行？**
**`@PostConstruct` → `afterPropertiesSet` → `init-method`**（注解在前，接口居中，配置最后）。

**追问：AOP 代理在哪一步生成？**
**`BeanPostProcessor.postProcessAfterInitialization`**（`AbstractAutoProxyCreator`）。**理解这一点就理解了"为什么自调用失效"**——代理是在初始化完成后包上去的，内部 `this` 调用走的是原始对象。

**追问：`prototype` 的 Bean 会被容器销毁吗？**
**不会**。容器只管理单例的完整生命周期（含销毁回调），prototype 创建后就不再跟踪 → **需要自己负责清理**。

详见 [[2-Bean生命周期与依赖注入]]。

---

### Q4. AOP 的实现原理？JDK 动态代理和 CGLIB 怎么选？

> [!important] 得分骨架
> **Spring AOP 是运行期动态代理**：容器在 Bean 初始化后，如果发现它有匹配的切面，就用代理对象替换原对象。
> | | JDK 动态代理 | CGLIB |
> |---|---|---|
> | 前提 | 目标类**实现接口** | 目标类**可被继承**（非 final） |
> | 原理 | `InvocationHandler` + `Proxy` | 生成子类字节码，重写方法 |
> | 限制 | 只能代理接口方法 | **不能代理 final 类/方法、private 方法** |
> | 性能 | 调用开销略高（反射） | 创建代理较慢，调用较快 |
>
> **Spring Boot 2.x 起默认 `proxyTargetClass=true`（CGLIB）**。

**追问：为什么自调用会导致 AOP 失效？**
因为**没走代理**。外部调用 → 代理 → 增强 → 目标方法；而目标方法内部 `this.otherMethod()` 是**直接调用原始对象**，绕过了代理。
解法：① 注入自身（`ObjectProvider`）；② 拆到另一个 Bean；③ `AopContext.currentProxy()`（需 `exposeProxy=true`）。

**追问：`@Around` 有什么坑？**
**必须调用 `proceed()` 并返回其结果**：
- 不调 `proceed()` → 目标方法**不执行**；
- 调了但**不返回** → 返回值丢失（接口返回 null）。
另外 `@Around` 里抛异常、吞异常都会影响后续通知。

详见 [[3-AOP原理与实战]]。

---

### Q5. AOP 失效有哪些场景？

> [!important] 得分骨架（列出至少 5 种）
> | 场景 | 原因 |
> |---|---|
> | **自调用**（this 调用） | 没走代理 |
> | 方法**非 public** | JDK 代理基于接口；CGLIB 也无法拦截 private |
> | **final** 类/方法 | CGLIB 无法继承/重写 |
> | `static` 方法 | 属于类不属于实例 |
> | 对象**不是 Spring 管理**的（自己 new） | 没有代理生成环节 |
> | 在 `@PostConstruct` 里调用 | 此时代理**还没生成**（代理在 BPP 后置阶段） |
> | **切点表达式写错** | 根本没匹配上（最常见但最容易忽略） |
>
> **排查手段**：打印 `AopUtils.isAopProxy(bean)` 确认是否被代理；开 `logging.level.org.springframework.aop=debug` 看切面匹配情况。

详见 [[3-AOP原理与实战]]。

---

### Q6. `@Transactional` 默认回滚哪些异常？

> [!important] 得分骨架
> **默认只回滚 `RuntimeException` 和 `Error`；受检异常（`Exception` 的子类但不是 `RuntimeException`）不回滚！**
> 所以**必须显式写 `rollbackFor = Exception.class`**。

**追问：为什么"catch 了异常事务没回滚"？**
两种典型原因：
① 异常被 `try-catch` 吞掉，**没有抛到代理层** → 代理认为执行成功 → 提交；
② 抛的是**受检异常**，默认规则不回滚。
正解：要么**不吞异常**，要么在 catch 里**手动 `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`**。

**追问：什么情况下 `rollbackFor` 设了也没用？**
如果**压根没走代理**（自调用）—— 那事务本身就没生效，和回滚规则无关。

详见 [[4-声明式事务]]。

---

### Q7. 事务的传播行为？

> [!important] 得分骨架（重点讲三个）
> | 传播行为 | 语义 |
> |---|---|
> | **`REQUIRED`（默认）** | 有事务就**加入**，没有就新建 |
> | **`REQUIRES_NEW`** | **挂起**当前事务，**开一个全新事务** |
> | **`NESTED`** | 基于 **savepoint** 嵌套；外层回滚会**带走内层**，内层回滚不影响外层 |
> | `SUPPORTS` | 有就用，没有就以非事务方式执行 |
> | `NOT_SUPPORTED` | 挂起当前事务，以非事务方式执行 |
> | `MANDATORY` | 必须在事务中，否则抛异常 |
> | `NEVER` | 必须不在事务中，否则抛异常 |

**追问：`REQUIRES_NEW` 和 `NESTED` 有什么区别？**
- **`REQUIRES_NEW`**：两个**独立**事务，内层提交后**外层回滚也不会撤销内层**（如记日志），代价是要**占用两个数据库连接**。
- **`NESTED`**：**同一个物理事务**里的 savepoint，外层回滚会**回滚到 savepoint 之前**（内层也白做），只占一个连接。

**追问：`REQUIRES_NEW` 为什么不生效？**
**自调用**。它同样依赖代理，必须**从另一个 Bean 调用**才能挂起当前事务。

详见 [[4-声明式事务]]。

---

### Q8. 事务失效有哪些场景？

> [!important] 得分骨架（列出至少 6 种）
> 1. **自调用**（同类方法调用，没走代理）
> 2. 方法**非 public**（Spring 6 之前要求 public）
> 3. **异常被 try-catch 吞掉**
> 4. **受检异常**且没配 `rollbackFor`
> 5. 类**没被 Spring 管理**
> 6. **多线程/异步**（事务绑定 ThreadLocal，跨线程必然失效）
> 7. 数据库**引擎不支持事务**（如 MyISAM）
> 8. 传播行为设置不当（如 `NOT_SUPPORTED`）
> 9. `@Transactional` 与 `@Async` 同用（异步在新线程，拿不到原事务）
> 10. 方法被 **final**（CGLIB 无法重写）

**追问：为什么跨线程会失效？**
`TransactionSynchronizationManager` 用 **`ThreadLocal`** 绑定连接和事务状态。**新线程拿不到原线程的 ThreadLocal**，所以要么开新事务，要么完全没有事务。

**追问：那怎么在事务提交后再做动作（发消息/通知）？**
① `TransactionSynchronizationManager.registerSynchronization`（`afterCommit`）；② **`@TransactionalEventListener(phase = AFTER_COMMIT)`**（推荐）；③ 本地消息表（最终一致，链接 [[7-分布式/2-分布式事务]]）。
**为什么不能直接在事务里发 MQ**：事务未提交消息先到 → 下游查不到数据 → **数据与消息不一致**。

详见 [[4-声明式事务]]。

---

### Q9. 讲一下 Spring MVC 处理一个请求的完整流程。

> [!important] 得分骨架
> 1. 请求进入 **`DispatcherServlet.doDispatch`**
> 2. `getHandler` → `HandlerMapping` 返回 **`HandlerExecutionChain`**（handler + 拦截器链）
> 3. `getHandlerAdapter` → 找到能处理该 handler 的 **`HandlerAdapter`**
> 4. **拦截器 `preHandle`**（返回 `false` 则中断）
> 5. `handle` → **参数解析** → 执行 Controller
> 6. 返回值处理（`ModelAndView`，或 `@ResponseBody` 走 **`HttpMessageConverter`**）
> 7. **拦截器 `postHandle`**（**抛异常时不执行**）
> 8. `ViewResolver` 解析 → `View.render` 渲染
> 9. **拦截器 `afterCompletion`**（**无论是否异常都执行**）
> 10. 异常由 `HandlerExceptionResolver` 处理

**追问：为什么需要 HandlerAdapter？**
**适配不同类型的 handler**（注解式 `@Controller`、函数式 `RouterFunction`、`HttpRequestHandler`、老的 `Controller` 接口）。没有它，DispatcherServlet 就要写一堆 `if-else instanceof`。

**追问：`@RequestBody` 和 `@RequestParam` 有什么区别？**
- `@RequestParam`：从**查询参数/表单**取，由 `RequestParamMethodArgumentResolver` 处理。
- `@RequestBody`：读**请求体**，由 `RequestResponseBodyMethodProcessor` + **`HttpMessageConverter`** 处理，需要匹配 `Content-Type`。
- **坑**：`@RequestBody` 读的是流，**只能读一次**；`Content-Type` 不对会报 415。

详见 [[5-SpringMVC请求全流程]]。

---

### Q10. 拦截器和过滤器有什么区别？

> [!important] 得分骨架
> | | Filter | Interceptor |
> |---|---|---|
> | 归属 | **Servlet 规范** | **Spring 框架** |
> | 时机 | 更外层（进入 Servlet 前） | 更内层（进入 Controller 前后） |
> | 能否拿到 handler | ❌ | ✅（知道要执行哪个方法） |
> | 能否拿到 ModelAndView | ❌ | ✅ |
> | 能否用 Spring 依赖注入 | 需要 `DelegatingFilterProxy` 桥接 | ✅ 天然是 Bean |
> | 执行次数 | 一次 | `preHandle`/`postHandle`/`afterCompletion` |
>
> **执行顺序**：`Filter → Interceptor.preHandle → Controller → Interceptor.postHandle → Interceptor.afterCompletion → Filter`
> **多个拦截器时**：`preHandle` **正序**执行，`postHandle` 与 `afterCompletion` **倒序**执行（类似栈）。

**追问：`postHandle` 什么时候不执行？**
**目标方法抛异常时**。而 `afterCompletion` **无论成功失败都会执行**（适合做资源清理、耗时统计）。

详见 [[5-SpringMVC请求全流程]]。

---

### Q11. Spring Boot 自动装配的原理？

> [!important] 得分骨架
> `@SpringBootApplication` = `@SpringBootConfiguration` + `@ComponentScan` + **`@EnableAutoConfiguration`**
> → `@EnableAutoConfiguration` 通过 `@Import(AutoConfigurationImportSelector)` 导入
> → 读取 **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`**（**Boot 2.7 起替代 `spring.factories`，3.0 移除旧方式**）
> → **条件过滤**（`@ConditionalOnClass` / `@ConditionalOnMissingBean` / `@ConditionalOnProperty` …）
> → 注册 BeanDefinition

**追问：`@ConditionalOnMissingBean` 为什么重要？**
它让**用户自定义的 Bean 优先**：自动配置只在"用户没提供"时才生效。**这是自动装配能与业务配置共存的关键**，也是"为什么我写的 Bean 覆盖了默认配置"的原因。

**追问：自动装配没生效怎么排查？**
① 启动加 `--debug` 或配 `debug=true`，看**自动配置报告**（`ConditionEvaluationReport`，会明确列出 matched / did not match 及原因）；
② 用 actuator 的 **`/actuator/conditions`** 端点；
③ 检查依赖是否引入（`@ConditionalOnClass` 依赖类不存在就不生效）；
④ 检查是否被 `exclude` 排除。

详见 [[6-SpringBoot自动装配]]。

---

### Q12. 扩展点有哪些？（负责人级加分题）

> [!important] 得分骨架（按执行时机串起来）
> `BeanDefinitionRegistryPostProcessor` → `BeanFactoryPostProcessor` → `InstantiationAwareBeanPostProcessor` → **`BeanPostProcessor`（前置/后置）** → `InitializingBean` → `SmartInitializingSingleton` → `ApplicationListener` / `@EventListener` → `CommandLineRunner` / `ApplicationRunner` → `DisposableBean`

**追问：`BeanFactoryPostProcessor` 和 `BeanPostProcessor` 有什么区别？**
- **BFPP**：**改 BeanDefinition**（配方），时机更早，在单例实例化**之前**。典型：`ConfigurationClassPostProcessor`（解析 `@Configuration`/`@ComponentScan`）。
- **BPP**：**改 Bean 实例**（成品），在**每个 Bean 初始化前后**回调。典型：`AutowiredAnnotationBeanPostProcessor`（处理 `@Autowired`）、`AbstractAutoProxyCreator`（生成 AOP 代理）。

**追问：`@TransactionalEventListener` 有什么用？**
让事件监听**绑定事务阶段**执行——`AFTER_COMMIT` 可以保证"事务提交成功后才发消息/发通知"，避免"消息先到、数据未落库"的不一致。

详见 [[7-Spring进阶专题]]。

---

## 二、快问快答

| 问题 | 要点 |
|---|---|
| Spring 的核心是什么？ | **IoC + AOP** |
| Bean 默认作用域？ | `singleton` |
| 单例 Bean 线程安全吗？ | **不保证**，关键看是否有可变共享状态 |
| `@Component` / `@Service` / `@Repository` 区别？ | 语义不同；**`@Repository` 额外提供异常转换** |
| `@Configuration` 与 `@Component` 区别？ | 前者默认被 **CGLIB 增强**，保证 `@Bean` 方法返回单例 |
| `proxyBeanMethods=false` 会怎样？ | 变 Lite 模式，`@Bean` 方法**每次调用都新建对象**（可能违背直觉） |
| `@Autowired` 注入不到怎么办？ | 检查类型唯一性、`@Primary`/`@Qualifier`、是否被扫描 |
| 同类型多个 Bean 怎么注入？ | `@Primary` 优先；`@Qualifier` 指定；否则按**字段名**匹配 |
| `@Resource` 按什么注入？ | **优先按名字**（JSR-250，非 Spring 提供） |
| `prototype` 注入进 `singleton` 会怎样？ | **只在创建时注入一次**，之后拿到的都是同一个 prototype 实例 |
| 怎么让 singleton 每次拿到新的 prototype？ | `@Lookup` / `ObjectProvider` / `ApplicationContext.getBean` |
| AOP 能拦截 private 方法吗？ | **不能** |
| AOP 能拦截 static 方法吗？ | **不能** |
| `@Around` 不调 `proceed()` 会怎样？ | 目标方法**不执行** |
| Spring AOP 和 AspectJ 区别？ | Spring 是**运行期代理**（只能拦方法）；AspectJ 支持编译期/类加载期织入 |
| 多个切面怎么排序？ | `@Order` / `Ordered` |
| `@Transactional` 加在接口上可以吗？ | 可以但**不推荐**（JDK 代理时才有意义；换 CGLIB 会失效） |
| `@Transactional` 能加在 private 方法上吗？ | Spring 6 之前**不生效**；新版有限放宽，但**仍建议 public** |
| `readOnly=true` 真的只读吗？ | 只是**提示**，最终看驱动与数据库；常用于**读写分离路由** |
| 大事务有什么危害？ | 占连接久、**锁范围大**、主从延迟、回滚代价高 |
| 怎么在事务提交后发消息？ | `@TransactionalEventListener(AFTER_COMMIT)` / `TransactionSynchronization` |
| Spring 事件默认同步吗？ | **同步**；异步要 `@Async` + `@EnableAsync` |
| `@Async` 不指定线程池会怎样？ | 用 `SimpleAsyncTaskExecutor`，**每次新建线程**（生产危险） |
| `@Scheduled` 默认几个线程？ | **1 个**，任务会互相阻塞 |
| 多实例下 `@Scheduled` 会重复执行吗？ | **会**，需要分布式锁或调度平台 |
| `@Cacheable` 自调用有效吗？ | **无效**（同样是代理问题） |
| 配置文件优先级最高的是什么？ | **命令行参数** |
| `@Value` 和 `@ConfigurationProperties` 选哪个？ | 复杂配置用后者（类型安全、松散绑定、可校验） |
| 返回 Long 前端精度丢失怎么办？ | 序列化成 **String** |
| 接口报 406 是什么原因？ | 找不到能把返回值写成客户端 Accept 类型的 `HttpMessageConverter` |
| 报 415 呢？ | `Content-Type` 与 `@RequestBody`/`consumes` 不匹配 |
| 跨域配了还报错？ | 检查**过滤器顺序**、网关层拦截、带 Cookie 时需 `allowCredentials` + 明确 origin |
| 启动慢怎么排查？ | Bean 太多、`@PostConstruct` 做重活、扫描范围过大 |
| 优雅停机怎么做？ | `server.shutdown=graceful` + 设置停机等待超时 |

---

## 三、易错陷阱 TOP 12

> [!danger] 这些答错比不答更扣分
> 1. **"`@Transactional` 会回滚所有异常"** —— **只回滚 `RuntimeException` 和 `Error`**，受检异常必须写 `rollbackFor`。
> 2. **"AOP 是编译期织入"** —— Spring AOP 是**运行期动态代理**（AspectJ 才支持编译期）。
> 3. **"加了 `@Transactional` 就一定有事务"** —— 自调用、非 public、没被容器管理都会**静默失效**。
> 4. **"`REQUIRES_NEW` 在内层回滚不影响外层"** —— 对，但**它和 `NESTED` 完全不同**；`NESTED` 外层回滚会带走内层。
> 5. **"单例 Bean 是线程安全的"** —— 容器只保证**单例**，**不保证线程安全**。
> 6. **"`prototype` 会被容器销毁"** —— **不会**，容器不跟踪 prototype 的销毁。
> 7. **"`@Async` 直接加注解就异步了"** —— 需要 `@EnableAsync`，且**自调用失效**，且**默认线程池有隐患**。
> 8. **"Spring 事件是异步的"** —— **默认同步**，监听器抛异常会影响发布方。
> 9. **"`@ConditionalOnMissingBean` 是可有可无的"** —— 它是**用户配置优先**的核心机制。
> 10. **"循环依赖加 `@Lazy` 或开开关就行"** —— 那是绕过症状；**正解是重构**（Spring Boot 2.6+ 默认直接禁止）。
> 11. **"事务里可以随便发 MQ"** —— 消息可能**先于数据**到达下游，必须用 `AFTER_COMMIT` 或本地消息表。
> 12. **"`postHandle` 一定会执行"** —— 目标方法抛异常时**不执行**；`afterCompletion` 才一定执行。

---

## 四、场景设计题

### 4.1 一个接口偶发"数据没保存但接口返回成功"，怎么排查？

**答题框架**：
1. **先确认事务是否真的生效**：打印 `AopUtils.isAopProxy(service)` 看有没有被代理 → **自调用是最常见原因**。
2. **看异常是否被吞**：`try-catch` 里只打日志没抛出 → 代理认为成功 → 提交（其实什么都没做或部分成功）。
3. **看回滚规则**：抛的是受检异常且没配 `rollbackFor`。
4. **看是否跨线程**：在事务里起线程/异步执行写操作 → 新线程没有事务。
5. **看数据库层**：引擎是否支持事务、是否被 `@Transactional` 外层包了但内层用了 `NOT_SUPPORTED`。
6. **加日志验证**：在事务方法进入/退出、提交/回滚回调打日志（`TransactionSynchronization`）。

### 4.2 设计一个"下单成功后发短信通知"的方案？

**要点（体现事务与异步的理解）**：
- **不能**在下单事务里直接调短信接口 → ① 外部调用会**拉长事务**；② 事务回滚了短信已发（**不可撤销**）。
- **正解**：`@TransactionalEventListener(phase = AFTER_COMMIT)` 监听"下单成功"事件 → **提交后**再异步发短信。
- **要注意**：监听器里再抛异常**不会回滚业务**（已提交），所以要有**重试与告警**；需要可靠投递就上**本地消息表 + 定时补偿**（链接 [[7-分布式/2-分布式事务]]）。
- **短信服务要幂等**（同一订单不重复发）。

### 4.3 系统启动报 `BeanCreationException`，怎么定位？

**答题框架**：
1. **看最底层的 `Caused by`**（异常链最深处才是根因）。
2. **判断类型**：`NoSuchBeanDefinitionException`（缺 Bean/没扫到）→ `NoUniqueBeanDefinitionException`（多个同类型）→ `BeanCurrentlyInCreationException`（循环依赖）→ 属性注入失败 / 构造器参数问题。
3. **定位手段**：IDEA 在 `AbstractAutowireCapableBeanFactory` 打断点看创建栈；开 debug 看自动配置报告；确认包扫描范围与 `@ComponentScan`。
4. **常见根因**：包路径写错没扫到、`@Configuration` 类被 new 出来而不是注入、条件装配没满足、依赖冲突导致类加载失败（`NoClassDefFoundError`）。

---

## 五、面试前 10 分钟速记卡

> [!abstract] 记住这 12 句
> 1. **IoC 是思想，DI 是实现**；推荐**构造器注入**。
> 2. `ApplicationContext` = `BeanFactory` + 事件/国际化/资源/AOP 集成 + **默认预实例化单例**。
> 3. Bean 生命周期关键：**实例化 → 属性填充 → `@PostConstruct` → `afterPropertiesSet` → init-method → BPP 后置（AOP 代理在此）**。
> 4. **单例 ≠ 线程安全**，无状态才安全。
> 5. Spring AOP = **运行期动态代理**；**Boot 2.x 起默认 CGLIB**。
> 6. **自调用是 AOP 与事务失效的头号原因**（没走代理）。
> 7. `@Transactional` **默认只回滚 RuntimeException 和 Error**。
> 8. **`REQUIRES_NEW` 开新事务（挂起外层）；`NESTED` 是 savepoint，外层回滚会带走内层**。
> 9. 事务跨线程失效，因为**绑定在 ThreadLocal**。
> 10. MVC：**DispatcherServlet → HandlerMapping → HandlerAdapter → 拦截器 → Controller → 返回值处理 → 视图**；**`postHandle` 异常时不执行**。
> 11. 自动装配：**`@EnableAutoConfiguration` → 读 `AutoConfiguration.imports` → 条件过滤**；**`@ConditionalOnMissingBean` 保证用户配置优先**。
> 12. **BFPP 改配方（BeanDefinition），BPP 改成品（Bean 实例）**。

---
> 回到 → [[0-Spring总览]] ｜ 源码速答骨架 → [[面试准备/技术面试题库/13-Spring源码专题]] ｜ 循环依赖专篇 → [[面试准备/技术面试题库/14-Spring循环依赖专题]]
