---
title: 13-Spring 源码专题
tags: [面试, Java, 技术题库, Spring, 源码, MyBatis]
status: 进行中
---

# 🧬 13 · Spring 源码专题

> 返回 [[00-总览与使用说明]] · 基础篇见 [[05-Spring与框架]] · 按简历声明组织见 [[面试准备/专业技能/02-Java核心与微服务]]

> [!important] 策略先行
> 你简历写了「深入掌握源码」，JD 写了「深入代码和运行机制定位问题」。
> **面试官不要求你默写源码，要求你：① 说得出主流程 ② 报得出关键类名/方法名 ③ 讲得清设计意图 ④ 用它定位过真实问题。**
> 每题的答案骨架都按这四点组织。别背细节，**背主流程 + 类名 + 为什么这么设计**。

---

## 一、IoC 容器启动：refresh() 十二步

> 高频度 ★★★★★ ｜ 关键类：`AbstractApplicationContext`

| 步骤 | 方法 | 干什么（一句话） |
|---|---|---|
| 1 | `prepareRefresh` | 状态与事件准备 |
| 2 | `obtainFreshBeanFactory` | **创建 BeanFactory 并加载 BeanDefinition** |
| 3 | `prepareBeanFactory` | 填充容器基础能力（类加载器、环境、忽略的接口） |
| 4 | `postProcessBeanFactory` | 子类扩展点 |
| 5 | `invokeBeanFactoryPostProcessors` | **BFPP 执行**（`ConfigurationClassPostProcessor` 在这解析 `@Configuration`/`@ComponentScan`/`@Import`，注册 BeanDefinition） |
| 6 | `registerBeanPostProcessors` | **注册 BPP**（`AutowiredAnnotationBeanPostProcessor`、AOP 创建器等） |
| 7-8 | `initMessageSource` / `initApplicationEventMulticaster` | 国际化与事件广播器 |
| 9 | `onRefresh` | 子类扩展：**Servlet 容器在这里创建**（Tomcat `createWebServer`） |
| 10 | `registerListeners` | 注册监听器 |
| 11 | `finishBeanFactoryInitialization` | **实例化所有非懒加载单例**（`preInstantiateSingletons`） |
| 12 | `finishRefresh` | LifecycleProcessor 启动（**WebServer.start 在这**）+ 发布 `ContextRefreshedEvent` |

**两个高频追问**：
- **为什么第 6 步先注册 BPP、第 11 步才实例化单例？** 实例化过程中要应用 BPP（注入 `@Autowired`、生成 AOP 代理），所以 BPP 必须先就位。
- **内嵌 Tomcat 的创建与启动在哪？** **创建在 onRefresh（第 9 步），启动在 finishRefresh（第 12 步）**——两步分开，创建失败不影响容器其他初始化，启动放在最后保证一切就绪。
- **BeanDefinition 和 Bean 的区别？** 前者是"配方"（类名、作用域、构造参数），后者是"成品"。第 2-5 步都在造配方，第 11 步才按配方生产。

---

## 二、Bean 生命周期源码（带方法名）

> 关键类：`AbstractAutowireCapableBeanFactory`

```
getBean → doGetBean → createBean → doCreateBean
 ├─ createBeanInstance        实例化（推断构造器：@Autowired 构造器由
 │                             AutowiredAnnotationBeanPostProcessor#determineCandidateConstructors 决定）
 ├─ addSingletonFactory       ★ 提前暴露 ObjectFactory 进三级缓存（解决循环依赖）
 ├─ populateBean              属性填充（@Autowired 注入由
 │                             AutowiredAnnotationBeanPostProcessor#postProcessProperties 完成）
 └─ initializeBean
     ├─ invokeAwareMethods                              BeanName/ClassLoader/BeanFactory
     ├─ applyBeanPostProcessorsBeforeInitialization     ★ @PostConstruct 在这执行
     ├─ invokeInitMethods                               afterPropertiesSet → init-method
     └─ applyBeanPostProcessorsAfterInitialization      ★ AOP 代理在这里生成（wrapIfNecessary）
registerDisposableBeanIfNecessary   注册销毁回调
```

**初始化顺序**：`@PostConstruct` → `afterPropertiesSet` → `init-method`
**销毁顺序（倒序）**：`@PreDestroy` → `destroy()` → `destroy-method`

**追问：@Autowired 注入发生在构造之后、初始化之前——为什么？**
> 注入在 `populateBean`（`InstantiationAwareBeanPostProcessor#postProcessProperties`），因为要先有实例才能填属性；而 `@PostConstruct` 属于初始化阶段，所以**能用上注入的依赖**。这个顺序解释了"为什么构造器里不能用 @Autowired 的字段"。

---

## 三、循环依赖与三级缓存（★最高频，必须讲透）

> 关键类：`DefaultSingletonBeanRegistry`
> ★ 本主题已独立成篇 → [[14-Spring循环依赖专题]]（完整时序推演 / 为什么不是两级 / @Async 报错机制 / Boot 2.6 默认禁止 / 治理），下面只留速记。

**三级缓存**：

| 缓存 | 存什么 | 何时用 |
|---|---|---|
| 一级 `singletonObjects` | 成品 Bean | 平时获取 |
| 二级 `earlySingletonObjects` | 提前暴露的 Bean（可能是代理） | 循环依赖时 |
| 三级 `singletonFactories` | `ObjectFactory` 工厂 | **按需生成**提前引用 |

**查找逻辑（源码骨架，Spring 5.x；6.x 优化了锁粒度，思路不变）**：
```java
protected Object getSingleton(String beanName, boolean allowEarlyReference) {
    Object o = singletonObjects.get(beanName);                    // 一级
    if (o == null && isSingletonCurrentlyInCreation(beanName)) {
        o = earlySingletonObjects.get(beanName);                  // 二级
        if (o == null && allowEarlyReference) {
            synchronized (this.singletonObjects) {
                o = singletonObjects.get(beanName);
                if (o == null) o = earlySingletonObjects.get(beanName);
                if (o == null) {
                    ObjectFactory<?> f = singletonFactories.get(beanName);   // 三级
                    if (f != null) {
                        o = f.getObject();                        // 可能在这里生成 AOP 代理
                        earlySingletonObjects.put(beanName, o);   // 升级到二级
                        singletonFactories.remove(beanName);
                    }
                }
            }
        }
    }
    return o;
}
```

**★ 为什么必须三级、两级不行？（讲透这题就赢）**
> 如果 A 需要被 AOP 代理，B 注入的必须是**代理对象**。
> - 两级方案：实例化后立即生成代理放二级 → **违背"代理应在初始化后生成"的设计**，且没被循环依赖的正常 Bean 也白白提前代理
> - 三级方案：放的是**工厂**，只有真的发生循环依赖、被别人 `getEarlyBeanReference` 时才生成代理——**按需、且生成时机仍符合设计**
> 结果：注入的代理 == 最终暴露的代理，一致性得到保证。

**边界（必答）**：
- 只解决 **singleton + setter/field 注入**
- **构造器循环依赖**：实例化阶段就互相依赖，还没到能暴露的时机 → `BeanCurrentlyInCreationException`
- **prototype** 不缓存 → 不解决
- **`@Async` 为什么反而报错？** 普通 AOP 能通过 `getEarlyBeanReference` 提前给出代理（提前暴露 == 最终暴露，一致）；
  `@Async` 的代理由 `AsyncAnnotationBeanPostProcessor` 在**初始化后**才生成，提前暴露阶段给不出 → 注入的是原始对象、最终暴露的是代理 → Spring 检测到不一致且 `allowRawInjectionDespiteWrapping=false` → 抛异常。
  解法：拆 bean 或 `@Lazy`。

---

## 四、AOP 源码

**代理创建链路**：`AbstractAutoProxyCreator#postProcessAfterInitialization → wrapIfNecessary → getAdvicesAndAdvisorsForBean（找切面+匹配 Pointcut）→ createProxy`

**JDK vs CGLIB 的选择逻辑**：
```
proxyTargetClass = true  → CGLIB（Spring Boot 2.x 起默认）
有接口且 proxyTargetClass = false → JDK 动态代理
无接口 → 只能 CGLIB
```

| | JDK 动态代理 | CGLIB |
|---|---|---|
| 原理 | `Proxy.newProxyInstance` + `InvocationHandler`，**实现接口**反射调用 | **生成目标子类**，`MethodInterceptor` 回调；**FastClass** 索引避免反射 |
| 限制 | 必须有接口 | **final 类/final 方法不能代理**；private 不参与 |
| 调用链 | `ReflectiveMethodInvocation#proceed()` 递归推进拦截器链（**责任链**） | `CglibMethodInvocation` 同构 |

**AOP 失效的统一根因（一个解释覆盖所有场景）**：
> 所有失效都是**"没走代理对象，走了 this"**：
> 自调用（`this.method()`）、private/final/static 方法（CGLIB 无法覆写）、new 出来的对象（不经容器）、异常被吞（拦截器还在但事务标记被清）。
> 解法：注入自身代理 / `AopContext.currentProxy()`（需 `exposeProxy=true`）/ 把逻辑拆到另一个 bean。

---

## 五、事务源码（★必考）

> 关键类：`TransactionInterceptor`、`AbstractPlatformTransactionManager`、`TransactionSynchronizationManager`

**执行链路**：
```
代理拦截 → TransactionInterceptor#invoke
  → invokeWithinTransaction（TransactionAspectSupport）
     ├─ createTransactionIfNecessary
     │    └─ getTransaction（AbstractPlatformTransactionManager）
     │         ├─ 已有事务 → handleExistingTransaction（按传播行为分支）
     │         └─ 无事务且 REQUIRED/REQUIRES_NEW/NESTED → 开新事务：
     │            getConnection → setAutoCommit(false) → 绑定 ThreadLocal
     ├─ 执行业务方法（MethodInvocation.proceed）
     └─ 异常 → rollbackOn 判断 → 回滚；否则 commit
```

**源码级要点（背这四个）**：
1. **连接绑定靠 ThreadLocal**：`TransactionSynchronizationManager` 以 `DataSource → ConnectionHolder` 绑定 → **这就是跨线程事务失效的根源**
2. **`REQUIRES_NEW` = `suspend` 挂起当前**：把当前 Connection 存进 `SuspendedResourcesHolder`，新开连接执行完再恢复 → **两个事务用两条连接，外层会占着资源等**
3. **`NESTED` = Savepoint**：同一连接，子回滚到保存点，外层可选择继续
4. **默认回滚规则**：`RuntimeException` 和 `Error`；受检异常不回滚（`rollbackOn` 默认实现）→ 所以 `rollbackFor = Exception.class` 是常见修正

**事务失效的源码解释（一句话一个）**：
- 自调用：`this` 不是代理 → 拦截器根本没执行
- 非 public：属性解析与代理都不覆盖
- 受检异常：`rollbackOn` 返回 false
- 异常被 catch 吞了：拦截器认为正常返回 → commit
- 多线程：连接绑定在 ThreadLocal，子线程拿不到

---

## 六、Spring MVC 源码

**继承体系**：`HttpServlet → FrameworkServlet（processRequest，绑定 Locale/RequestContext）→ DispatcherServlet`

**`doDispatch` 主流程（按顺序报）**：
```
checkMultipart → getHandler（HandlerMapping → HandlerExecutionChain 含拦截器）
→ getHandlerAdapter → applyPreHandle（false 则触发 afterCompletion 并返回）
→ ha.handle（参数解析 + 调用 Controller + 返回值处理）→ applyPostHandle
→ processDispatchResult（视图渲染 或 handleException）
→ triggerAfterCompletion（finally 语义）
```

**三个可替换的扩展点（负责人视角：这就是 MVC 的设计亮点）**：
- `HandlerMapping`：`RequestMappingHandlerMapping` 把 `@RequestMapping` 注册进 `MappingRegistry`
- `HandlerMethodArgumentResolver`：`@RequestBody` 由 `RequestResponseBodyMethodProcessor` + `HttpMessageConverter`（Jackson）处理
- `HandlerMethodReturnValueHandler`：`@ResponseBody` 走同一个 Processor 直接写响应
- 异常：`HandlerExceptionResolver` 链，`@ControllerAdvice` 由 `ExceptionHandlerExceptionResolver` 处理

**追问：Controller 单例，线程安全吗？**
> 无状态（成员变量只有不可变依赖）就安全；有可变成员变量就有并发问题 → 用局部变量 / `ThreadLocal` / 无状态设计。这也是为什么**不要在 Controller 里写可变计数器**。

---

## 七、Spring Boot 源码

### 启动流程（`SpringApplication.run`）
```
new SpringApplication：推断应用类型（WebApplicationType）
  → 从 spring.factories 加载 Initializers / Listeners
run()：
  ① 准备 Environment（ConfigData 机制加载 application.yml，优先级生效）
  ② 创建 ApplicationContext
  ③ prepareContext（把启动类注册为 BeanDefinition，@ComponentScan 生效）
  ④ refresh()  ← 回到第一题的十二步（内嵌容器创建+启动）
  ⑤ callRunners（ApplicationRunner / CommandLineRunner）
```

### 自动装配（★★★）
`@EnableAutoConfiguration` → `@Import(AutoConfigurationImportSelector)`

**`getAutoConfigurationEntry` 四步**：
1. **读候选**：`META-INF/spring/...AutoConfiguration.imports`（2.7+；旧版 spring.factories）
2. **去重 + 排除**（exclude/excludeName）
3. **条件过滤**：`OnClassCondition`（类在不在 classpath）、`OnWebApplicationCondition`、`OnPropertyCondition`
4. **排序**：`@AutoConfigureOrder` / `@AutoConfigureBefore/After`

**为什么 2.7 改成 imports 文件？** spring.factories 是全局注册机制（多种 SPI 混在一起），拆出专属文件是为了 3.0 平滑移除对 spring.factories 的自动配置依赖。

**`@ConditionalOnMissingBean` 的顺序敏感性**：它依赖"用户 Bean 先注册"——这就是为什么自动配置类必须在用户配置之后处理（`@AutoConfigureAfter`），也是有时自己的 Bean 盖不掉默认 Bean 的原因。

---

## 八、MyBatis 源码

**执行链路**：
```
SqlSessionFactoryBuilder → XMLConfigBuilder 解析 → Configuration（全局大对象，含 MappedStatement）
→ DefaultSqlSessionFactory → SqlSession
→ Executor（Simple/Reuse/Batch；外层包 CachingExecutor 二级缓存）
→ StatementHandler → ParameterHandler（#{} 预编译占位）→ ResultSetHandler（映射结果）
```

**核心问答**：

| 问题 | 源码级答案 |
|---|---|
| **Mapper 没有实现类，为什么能注入？** | `MapperFactoryBean` 是 `FactoryBean`，`getObject()` 返回 `MapperProxy`（JDK 动态代理）→ 调用进 `MapperMethod#execute`，按 SQL 类型分发到 `sqlSession` 对应方法 |
| 插件原理 | `InterceptorChain#pluginAll` 把四大对象（Executor/StatementHandler/ParameterHandler/ResultSetHandler）**层层 JDK 代理包装**（责任链）——PageHelper 就是 Executor 级插件 |
| 一级缓存 | `BaseExecutor#localCache`（PerpetualCache），**增删改/commit/close 清空**；Spring 集成下同事务内有效 |
| 二级缓存 | `CachingExecutor` + namespace 级；装饰链（同步/序列化）；**跨 namespace 与分布式下易脏读，慎用** |
| `#{}` vs `${}` 源码差异 | `#{}` 经 `ParameterMappingTokenHandler` 生成 `?` 占位 → PreparedStatement 预编译；`${}` 是 `DynamicSqlSource` **文本拼接** |
| 延迟加载 | `ResultLoaderMap` + 代理（cglib/javassist），访问属性时才触发 `ResultLoader` 查询 |
| 一级缓存的坑 | 同一 SqlSession 内两次相同查询第二次不走 DB → **别的服务改了数据你读旧值**；Spring 下每事务一个 session，通常无感，但**长事务内要小心** |

---

## 九、设计模式 → 源码位置（说得出类名才算数）

| 模式 | 源码位置（类名级） |
|---|---|
| 模板方法 | `JdbcTemplate`、`AbstractPlatformTransactionManager`、AQS |
| 责任链 | `ReflectiveMethodInvocation#proceed`、拦截器链、MyBatis 插件 |
| 工厂 | `BeanFactory`、`FactoryBean`、`SqlSessionFactory` |
| 代理 | `AbstractAutoProxyCreator`、`MapperProxy` |
| 观察者 | `ApplicationEventMulticaster` / `ApplicationListener` |
| 适配器 | `HandlerAdapter`、`AdvisorAdapter` |
| 装饰器 | `CachingExecutor`（MyBatis 二级缓存） |
| 策略 | `InstantiationStrategy`、`AutoConfigurationImportFilter` |
| 建造者 | `SqlSessionFactoryBuilder`、`SpringApplicationBuilder` |
| 组合 | `SqlNode` 树、`CompositeMessageConverter` |

---

## 十、⭐ 用源码定位问题的真实场景（负责人视角收官）

> JD 原话是"**深入代码和运行机制定位问题**"——所以最后一定要落到排查案例上。

**案例模板 1：事务失效排查链路**
```
现象：@Transactional 方法没回滚
→ ① 确认 Bean 是不是代理（AopUtils.isAopProxy / 打印 getClass()）
→ ② 是不是自调用？（this.method() 不走代理）
→ ③ rollbackFor 对不对？（受检异常默认不回滚）
→ ④ 传播行为是不是 NOT_SUPPORTED/NEVER？
→ ⑤ 是不是多线程（ThreadLocal 连接绑定丢失）？
→ ⑥ 数据库引擎支持事务吗？
```

**案例模板 2：循环依赖启动报错**
```
BeanCurrentlyInCreationException
→ 看注入方式：构造器注入？（改 setter/字段，或 @Lazy）
→ 有 @Async？（代理时机问题，@Lazy 或拆 bean）
→ prototype？（天然不解决）
```

**案例模板 3：切面/拦截器不生效**
```
→ 代理方式是 JDK 还是 CGLIB？（接口方法才走 JDK 代理；final 方法 CGLIB 拦不住）
→ 切点表达式匹配吗？（execution 写错包路径）
→ Bean 是不是 new 出来的 / 是不是 @Configuration 问题
```

> [!tip] 学习与应试方法
> 1. **手画**：refresh 十二步、Bean 生命周期、doDispatch——画得出来就是真懂
> 2. **记类名**：每条流程记 2-3 个关键类（`AbstractAutoProxyCreator`、`TransactionInterceptor`、`MapperProxy`）
> 3. **备一个真实排查案例**：源码知识的最高形态是"我用它定位过问题"
> 4. **诚实降级话术**：如果被问到没看过的模块（如 Spring WebFlux 内部），
>    "这块我看过设计文档但没读源码，我的理解是……"——**远好于现编**

---

## 📥 待补充
- 

## 🔗 关联
- [[05-Spring与框架]]（基础篇）· [[02-并发与多线程]] · [[面试准备/专业技能/02-Java核心与微服务]]
- [[面试准备/冠顿/00-JD与匹配分析]]

#面试 #Spring #源码 #MyBatis #待补
