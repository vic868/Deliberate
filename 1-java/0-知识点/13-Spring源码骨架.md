---
title: Java Spring 源码骨架
tags: [Java, Spring, 源码]
status: 进行中
created: 2026-10-09
---

# 🌱 十三、Spring 源码骨架

> 本篇是一份**骨架**：把 Spring 面试里真正会被追问到源码层的主干脉络画清楚——`refresh()` 十二步、Bean 生命周期、三级缓存解决循环依赖、AOP 代理时机、`@Transactional` 链路、MVC 请求链路、Boot 自动配置、MyBatis 集成。
> 只给"能答到点子上"的骨架与关键类名，不展开逐行源码分析；**完整的源码级分析见 [[面试准备/技术面试题库/13-Spring源码专题]]**。
> 关联：[[2-面向对象与设计模式]]（Spring 里用到的设计模式）、[[1-语言基础与面向对象]]（反射与动态代理）、[[3-泛型反射与注解]]（注解与 `@Import` 机制）、[[0-Java总览]]。

---

## 一、IoC 容器启动主线

### 1.1 入口

```java
ApplicationContext ctx = new AnnotationConfigApplicationContext(AppConfig.class);
```

构造过程只做三件事：`AnnotatedBeanDefinitionReader`（读注解配置类）、`ClassPathBeanDefinitionScanner`（扫描 `@Component`）、`register(...)` 把配置类注册成 `BeanDefinition`，最后调用 **`refresh()`**。

> [!important] 一句话认知
> **`refresh()` 是整个 Spring 容器的"总入口与总模板"**——`ApplicationContext` 的一切初始化都在这一条线上。它同时是**模板方法模式**的教科书案例：十二步固定，`onRefresh()`/`postProcessBeanFactory()` 交给子类。
> `ClassPathXmlApplicationContext`、`AnnotationConfigApplicationContext`、`SpringApplication` 用的 `ServletWebServerApplicationContext` 共用这一份 `refresh()`。

### 1.2 `refresh()` 十二步

| # | 方法 | 一句话职责 | 关键点 |
|---|---|---|---|
| 1 | `prepareRefresh()` | 准备上下文：记录启动时间、设置 `active` 标志、初始化 `PropertySource`、校验必需属性、初始化早期事件集合 | 只做准备，**不创建 Bean** |
| 2 | `obtainFreshBeanFactory()` | 获取 `ConfigurableListableBeanFactory` | 内部 `refreshBeanFactory()`；决定**是否允许 BeanDefinition 覆盖**、**是否允许循环依赖**；`GenericApplicationContext` 不重建工厂 |
| 3 | `prepareBeanFactory(beanFactory)` | 给 BeanFactory 装上"基础设施" | 设置 ClassLoader、SpEL 解析器、加 `ApplicationContextAwareProcessor`、`ignoreDependencyInterface(...)`、`registerResolvableDependency(BeanFactory/ResourceLoader/ApplicationEventPublisher/ApplicationContext)`、注册 `ApplicationListenerDetector` |
| 4 | `postProcessBeanFactory(beanFactory)` | **模板钩子**，子类扩展 | web 场景在此注册 `request`/`session` 作用域、`ServletContextAwareProcessor` |
| 5 | **`invokeBeanFactoryPostProcessors(beanFactory)`** | 执行所有 `BeanFactoryPostProcessor` | **最关键一步**：先跑 `BeanDefinitionRegistryPostProcessor`（`PriorityOrdered` → `Ordered` → 其余），其中 **`ConfigurationClassPostProcessor` 解析 `@Configuration`/`@ComponentScan`/`@Import`/`@Bean`，把 BeanDefinition 全部注册进来**；再跑普通 `BeanFactoryPostProcessor`（如 `PropertySourcesPlaceholderConfigurer`） |
| 6 | **`registerBeanPostProcessors(beanFactory)`** | 注册所有 `BeanPostProcessor` | 按 `PriorityOrdered` → `Ordered` → 无序 → `MergedBeanDefinitionPostProcessor` 分类注册，最后补 `ApplicationListenerDetector`；**此时只是注册，还没生效** |
| 7 | `initMessageSource()` | 初始化国际化 `MessageSource` | 没有则用空的 `DelegatingMessageSource` |
| 8 | `initApplicationEventMulticaster()` | 初始化事件广播器 | 没有则用 `SimpleApplicationEventMulticaster` |
| 9 | `onRefresh()` | **模板钩子** | **Spring Boot 在此创建内嵌 Tomcat**（`ServletWebServerApplicationContext.createWebServer()`），但此时还没启动 |
| 10 | `registerListeners()` | 注册监听器 | 把 `ApplicationListener` 注册进广播器，并补发早期事件 |
| 11 | **`finishBeanFactoryInitialization(beanFactory)`** | 冻结配置 + **实例化所有非懒加载单例** | 注册 `LoadTimeWeaverAware`、设置 `ConversionService`、`freezeConfiguration()`、**`preInstantiateSingletons()`**——Bean 生命周期真正发生的地方 |
| 12 | `finishRefresh()` | 收尾并广播 | `clearResourceCaches()`、`initLifecycleProcessor()`、**`getLifecycleProcessor().onRefresh()` 启动 WebServer（Tomcat 真正开始监听）**、**`publishEvent(new ContextRefreshedEvent(this))`** |

> [!tip] 三步必须能复述
> **第 5 步把 BeanDefinition 攒齐**（`@Configuration`/`@ComponentScan`/`@Import` 都在这一步解析）；
> **第 6 步把 `BeanPostProcessor` 注册好**（AOP、`@Autowired`、`@PostConstruct` 全靠它们）；
> **第 11 步才真正 new 出单例 Bean**（前面都是"元数据准备"）。
> 面试常问"`@Bean` 什么时候被解析"→ 第 5 步；"AOP 代理什么时候生成"→ 第 11 步里每个 Bean 初始化的最后。

> [!warning] 一个高频误区
> **第 12 步才启动内嵌 Tomcat**，第 9 步只是"创建对象"。所以"Bean 初始化时报端口占用"这类问题，实际是第 12 步才抛出的——日志时间点会误导排查方向。

---

## 二、Bean 生命周期（源码级骨架）

### 2.1 调用链主干

```
getBean(name)
 └─ doGetBean(name, type, args, false)
     ├─ transformedBeanName()   // 去掉 & 前缀、解析别名
     ├─ getSingleton(beanName, true)   // ★ 先查三级缓存（可能拿到半成品）
     ├─ 未命中 → getSingleton(beanName, singletonFactory)
     │            └─ createBean(beanName, mbd, args)
     │                └─ doCreateBean(beanName, mbdToUse, args)
     └─ getObjectForBeanInstance()   // 若是 FactoryBean，取 getObject()
```

```java
protected Object doCreateBean(String beanName, RootBeanDefinition mbd, Object[] args) {
    // ① 实例化
    BeanWrapper instanceWrapper = createBeanInstance(beanName, mbd, args);
    Object bean = instanceWrapper.getWrappedInstance();

    // ② 解析注入点（@Autowired/@Value 在此被解析成 InjectionMetadata 并缓存）
    applyMergedBeanDefinitionPostProcessors(mbd, beanType, beanName);

    // ③ ★ 提前暴露：把"能生成早期引用"的工厂放进三级缓存
    boolean earlySingletonExposure = (mbd.isSingleton() && this.allowCircularReferences &&
            isSingletonCurrentlyInCreation(beanName));
    if (earlySingletonExposure) {
        addSingletonFactory(beanName, () -> getEarlyBeanReference(beanName, mbd, bean));
    }

    // ④ 属性填充（@Autowired 注入在这里发生）
    populateBean(beanName, mbd, instanceWrapper);

    // ⑤ 初始化（Aware 回调 → 前置处理 → init 方法 → 后置处理，AOP 代理在此生成）
    exposedObject = initializeBean(beanName, exposedObject, mbd);

    // ⑥ 循环依赖的"代理一致性"校验（不一致就抛异常，见 §3.3）
    if (earlySingletonExposure) { /* getSingleton(beanName,false) 比对 */ }
    // ⑦ 注册销毁回调
    registerDisposableBeanIfNecessary(beanName, bean, mbd);
    return exposedObject;
}
```

### 2.2 各阶段细节

| 阶段 | 关键方法 | 做了什么 |
|---|---|---|
| **① 实例化** | `createBeanInstance` → `determineConstructorsFromBeanPostProcessors` | 由 `SmartInstantiationAwareBeanPostProcessor.determineCandidateConstructors` 推断构造器（`AutowiredAnnotationBeanPostProcessor` 实现：单个有参构造器可省略 `@Autowired`，或有 `@Autowired` 的那个）；再 `autowireConstructor` 或 `instantiateBean`（`CglibSubclassingInstantiationStrategy` 用 CGLIB 生成子类绕过构造器） |
| **② 解析注入点** | `applyMergedBeanDefinitionPostProcessors` | `AutowiredAnnotationBeanPostProcessor.postProcessMergedBeanDefinition` 扫描字段/方法上的 `@Autowired`/`@Value`，构建 `InjectionMetadata` 并缓存；`CommonAnnotationBeanPostProcessor` 记录 `@PostConstruct`/`@PreDestroy` |
| **③ 提前暴露** | `addSingletonFactory` | 把 `ObjectFactory`（`() -> getEarlyBeanReference(...)`）放进**三级缓存** |
| **④ 属性填充** | `populateBean` | `InstantiationAwareBeanPostProcessor.postProcessAfterInstantiation` → **`postProcessProperties`（`@Autowired`/`@Value` 真正注入）** → `applyPropertyValues`（XML `<property>`） |
| **⑤ 初始化** | `initializeBean` | 见下表四小步 |
| **⑥ 销毁注册** | `registerDisposableBeanIfNecessary` | 实现了 `DisposableBean`/有 `@PreDestroy`/有 `destroy-method` 才注册 |

**`initializeBean` 四小步（顺序不能错）**：

| 顺序 | 动作 | 处理者 |
|---|---|---|
| 1 | `invokeAwareMethods` | `BeanNameAware`、`BeanClassLoaderAware`、`BeanFactoryAware`（**只这三个走硬编码**，其余 Aware 走 `ApplicationContextAwareProcessor`） |
| 2 | `applyBeanPostProcessorsBeforeInitialization` | `ApplicationContextAwareProcessor` 处理 `EnvironmentAware`/`ApplicationContextAware` 等；`CommonAnnotationBeanPostProcessor` 处理 **`@PostConstruct`** |
| 3 | `invokeInitMethods` | `InitializingBean.afterPropertiesSet()` → `init-method`（`@Bean(initMethod=...)`） |
| 4 | `applyBeanPostProcessorsAfterInitialization` | **`AbstractAutoProxyCreator.postProcessAfterInitialization` → AOP 代理在此生成** |

> [!important] 三句话把这个生命周期答完整
> **`createBeanInstance`（反射/CGLIB 实例化）→ `populateBean`（`@Autowired` 由 `AutowiredAnnotationBeanPostProcessor` 在 `postProcessProperties` 中完成）→ `initializeBean`（Aware → 前置处理器含 `@PostConstruct` → `afterPropertiesSet`/`init-method` → 后置处理器含 AOP）**。
> 记住："**构造器 → 属性 → 初始化 → 代理 → 销毁回调**"，每一步都有对应的扩展点。

> [!question] `@PostConstruct` 和 `afterPropertiesSet` 谁先？
> `@PostConstruct` 先——它是 `BeanPostProcessor.postProcessBeforeInitialization`，而 `afterPropertiesSet` 在 `invokeInitMethods` 里，**在前置处理器之后**。
> 完整顺序：构造器 → `@Autowired` 注入 → `@PostConstruct` → `InitializingBean.afterPropertiesSet` → `init-method` → AOP 代理 → `@PreDestroy` → `DisposableBean.destroy` → `destroy-method`。

---

## 三、循环依赖与三级缓存（面试必考）

### 3.1 三级缓存是什么

```java
// DefaultSingletonBeanRegistry
private final Map<String, Object> singletonObjects = new ConcurrentHashMap<>(256);       // ① 一级：成品
private final Map<String, Object> earlySingletonObjects = new ConcurrentHashMap<>(16);   // ② 二级：半成品
private final Map<String, ObjectFactory<?>> singletonFactories = new HashMap<>(16);      // ③ 三级：工厂
private final Set<String> singletonsCurrentlyInCreation = ...;                           // 正在创建中的标记
```

| 级别 | Map | 存什么 | 谁放进去 |
|---|---|---|---|
| 一级 | `singletonObjects` | **完整可用的单例** | `addSingleton`（初始化完成后） |
| 二级 | `earlySingletonObjects` | **提前暴露的半成品**（可能已被 AOP 包装） | `getSingleton(name, allowEarlyReference=true)` 里从三级取出后升级 |
| 三级 | `singletonFactories` | **`ObjectFactory`**（延迟决定要不要生成代理） | `doCreateBean` 里的 `addSingletonFactory` |

```java
// 依赖注入时查找 Bean 的实际路径
protected Object getSingleton(String beanName, boolean allowEarlyReference) {
    Object singletonObject = this.singletonObjects.get(beanName);                  // 查一级
    if (singletonObject == null && isSingletonCurrentlyInCreation(beanName)) {
        singletonObject = this.earlySingletonObjects.get(beanName);                // 查二级
        if (singletonObject == null && allowEarlyReference) {
            synchronized (this.singletonObjects) {
                singletonObject = this.singletonObjects.get(beanName);
                if (singletonObject == null) {
                    singletonObject = this.earlySingletonObjects.get(beanName);
                    if (singletonObject == null) {
                        ObjectFactory<?> singletonFactory = this.singletonFactories.get(beanName);  // 查三级
                        if (singletonFactory != null) {
                            singletonObject = singletonFactory.getObject();   // ★ 此刻才生成早期引用
                            this.earlySingletonObjects.put(beanName, singletonObject);   // 升级到二级
                            this.singletonFactories.remove(beanName);                    // 移出三级
                        }
                    }
                }
            }
        }
    }
    return singletonObject;
}
```

**A ↔ B 的解析过程**：

| 步骤 | 动作 | 缓存状态 |
|---|---|---|
| 1 | 创建 A：`getSingleton("A", factory)` → 标记 A 在创建中 | —— |
| 2 | `createBeanInstance` 造出 A 的原始对象 | —— |
| 3 | **`addSingletonFactory("A", () -> getEarlyBeanReference(...))`** | 三级有 A |
| 4 | `populateBean(A)` 发现依赖 B → `getBean("B")` | —— |
| 5 | 创建 B：同样提前暴露 B 到三级，再 `populateBean(B)` 发现依赖 A | 三级有 A、B |
| 6 | **`getSingleton("A", true)`**：一级没有、二级没有 → 从三级取工厂 → **调 `getEarlyBeanReference` 得到 A 的早期引用** → 放二级、删三级 | 二级有 A |
| 7 | B 注入到 A 的早期引用，B 初始化完成 → `addSingleton(B)` | 一级有 B |
| 8 | A 拿到 B，完成 `populateBean`、`initializeBean` → `addSingleton(A)` | 一级有 A、B |

### 3.2 为什么要第三级，而不是两级？

**因为需要"延迟决定是否提前生成 AOP 代理"，并且保证代理只生成一次。**

```java
// 三级缓存的工厂实际做的事
protected Object getEarlyBeanReference(String beanName, RootBeanDefinition mbd, Object bean) {
    Object exposedObject = bean;
    for (BeanPostProcessor bp : getBeanPostProcessors()) {
        if (bp instanceof SmartInstantiationAwareBeanPostProcessor ibp) {
            exposedObject = ibp.getEarlyBeanReference(exposedObject, beanName);   // ★ AOP 在这
        }
    }
    return exposedObject;
}

// AbstractAutoProxyCreator：既实现提前生成，又实现"只生成一次"
public Object getEarlyBeanReference(Object bean, String beanName) {
    Object cacheKey = getCacheKey(bean.getClass(), beanName);
    this.earlyProxyReferences.put(cacheKey, bean);       // 记账：提前代理过了
    return wrapIfNecessary(bean, beanName, cacheKey);    // 真的生成代理
}
public Object postProcessAfterInitialization(Object bean, String beanName) {
    Object cacheKey = getCacheKey(bean.getClass(), beanName);
    if (this.earlyProxyReferences.remove(cacheKey) != bean) {   // ★ 已经提前代理过 → 不重复包装
        return wrapIfNecessary(bean, beanName, cacheKey);
    }
    return bean;
}
```

| 方案 | 问题 |
|---|---|
| **只有两级**（一级成品 + 二级早期引用） | 要在**实例化后立刻**决定"要不要生成代理"。但**正常情况下代理是在 `postProcessAfterInitialization` 才生成的**，提前生成意味着：① 所有被循环依赖牵涉的 Bean 都被提前代理，破坏"按需代理"的设计；② 无法保证"只代理一次"，可能出现"注入的是代理、最终放进一级缓存的是另一个代理"的不一致 |
| **有三级**（工厂） | 只有**真的发生循环依赖**（有人来 `getSingleton(name, true)` 查早期引用）时才调工厂生成代理；没发生循环依赖时，代理仍在 `postProcessAfterInitialization` 生成。**一个 Bean 只会被包装一次**——靠 `earlyProxyReferences` 记账保证 |

> [!important] 面试就答这两句
> **"三级缓存不是为了让对象能被提前引用（两级也能做到），而是为了把'是否生成 AOP 代理'这个决策延迟到'真的发生循环依赖时'，并用 `earlyProxyReferences` 记账保证代理只生成一次。"**
> 如果面试官追问"为什么二级不行"——把上面"只有两级的问题"①②说出来即可。

### 3.3 哪些循环依赖能解决、哪些不能

| 场景 | 能否解决 | 原因 |
|---|---|---|
| **单例 + setter/字段注入**（`@Autowired` 字段） | ✅ 能 | 对象先实例化、后注入，可以走三级缓存提前暴露 |
| **单例 + 构造器注入** | ❌ **不能** | 构造器需要参数才能造对象 → 连"实例化"都完不成，**根本没有对象可以提前暴露**，直接抛 `BeanCurrentlyInCreationException` |
| **prototype 作用域** | ❌ 不能 | Spring **不缓存** prototype（每次都新建），`isSingletonCurrentlyInCreation` 逻辑不适用，直接抛 "Requested bean is currently in creation" |
| **`@Async` / 额外被另一个后置处理器包装** | ❌ 通常不能 | 提前暴露的是**原始对象**（`@Async` 的处理器没实现 `getEarlyBeanReference`），最终 Bean 又被 `AsyncAnnotationBeanPostProcessor` 包装 → 两者不一致，抛 `BeanCurrentlyInCreationException`："Bean with name 'x' has been injected into other beans [...] **in its raw version as part of a circular reference, but has eventually been wrapped**" |
| `@Lazy` 标注其中一个注入点 | ✅ 能 | 注入的是代理，第一次真正调用时才去容器取，切断了创建链 |
| 使用 `ObjectProvider`/`ApplicationContext` 延迟获取 | ✅ 能 | 同上，延迟到运行时再取 |

> [!danger] Spring Boot 2.6+ 默认**禁止**循环依赖
> 2.6 起 `spring.main.allow-circular-references` **默认为 `false`**，机制是把 `AbstractAutowireCapableBeanFactory.allowCircularReferences` 置为 `false`，于是 `doCreateBean` 里 `earlySingletonExposure` 为 `false`——**三级缓存根本不会被写入**，循环依赖直接在创建阶段失败。
> 官方意图很明确：**循环依赖是设计问题，不是配置问题**。
> **实践建议：不要用 `spring.main.allow-circular-references=true` 掩盖问题**，正确做法是重构：
> ① 抽出双方共同依赖的第三个 Bean；
> ② 用 `@Lazy` 打断其中一个注入点；
> ③ 用 `ApplicationEventPublisher` 做解耦（A 发事件，B 监听）；
> ④ 用 `ObjectProvider<T>` 延迟获取。
> 反例：用 `@Lazy` 到处糊，会让启动期错误推迟到运行期才暴露，更难排查。

---

## 四、AOP 骨架

### 4.1 自动代理器的注册与创建时机

```java
@EnableAspectJAutoProxy            // → @Import(AspectJAutoProxyRegistrar.class)
// AspectJAutoProxyRegistrar 做的事：
// AopConfigUtils.registerAspectJAnnotationAutoProxyCreatorIfNecessary(registry);
//   → 注册 AnnotationAwareAspectJAutoProxyCreator
//     beanName = "org.springframework.aop.config.internalAutoProxyCreator"
// 并按注解属性设置 proxyTargetClass / exposeProxy
```

| 环节 | 内容 |
|---|---|
| 注册Bean | `AnnotationAwareAspectJAutoProxyCreator` extends `AspectJAwareAdvisorAutoProxyCreator` extends `AbstractAdvisorAutoProxyCreator` extends **`AbstractAutoProxyCreator`**（既实现 `SmartInstantiationAwareBeanPostProcessor`，又实现 `BeanPostProcessor`） |
| **创建时机** | **`postProcessAfterInitialization`** → `wrapIfNecessary` → `getAdvicesAndAdvisorsForBean`（找到匹配的 Advisor）→ `createProxy` → `ProxyFactory` → `DefaultAopProxyFactory.createAopProxy` |
| 跳过代理 | 基础设施类（`Advice`/`Pointcut`/`Advisor`/`AopInfrastructureBean`）、没有匹配 Advisor、已在 `targetSourcedBeans`/`advisedBeans` 缓存中 |
| 提前创建 | 若发生循环依赖，则由 `getEarlyBeanReference` 提前创建（见 §3.2） |

### 4.2 JDK 动态代理 vs CGLIB

```java
// DefaultAopProxyFactory
public AopProxy createAopProxy(AdvisedSupport config) {
    if (config.isOptimize() || config.isProxyTargetClass() || hasNoUserSuppliedProxyInterfaces(config)) {
        Class<?> targetClass = config.getTargetClass();
        if (targetClass.isInterface() || Proxy.isProxyClass(targetClass)) return new JdkDynamicAopProxy(config);
        return new ObjenesisCglibAopProxy(config);       // ★ CGLIB
    }
    return new JdkDynamicAopProxy(config);               // ★ JDK
}
```

| 维度 | JDK 动态代理 | CGLIB |
|---|---|---|
| 原理 | `Proxy.newProxyInstance` + `InvocationHandler` | 生成**目标类的子类**并覆写方法（`MethodInterceptor`） |
| 前提 | **目标类必须实现接口**，注入时用接口类型 | **类不能 final、方法不能 final/static/private** |
| 实例化 | 需要接口 | Spring 用 **`ObjenesisCglibAopProxy`**（Objenesis 绕过构造器创建实例），所以**可以没有无参构造器** |
| 性能 | 反射调用，略慢（JDK 8+ 有 `MethodHandle` 优化） | 生成字节码，调用快，但**首次创建代理慢**（生成类） |
| 注入类型 | 必须用接口声明，否则 `BeanNotOfRequiredTypeException` | 可以用具体类声明 |
| Spring 中的默认 | `proxyTargetClass=false` 且目标有接口时 | **`spring.aop.proxy-target-class=true` 是 Spring Boot 自 2.0 起的默认值 → 默认 CGLIB** |

> [!important] Spring Boot 默认偏 CGLIB，以及它的副作用
> 因为 `AopAutoConfiguration` 的默认配置就是 `proxyTargetClass = true`。好处是**不需要接口也能代理**；代价有三：
> ① `final` 类/`final` 方法无法代理（**不报错，只是默默不生效**）；
> ② 目标类的**所有**非 `final` 方法都会被拦截（包括 `toString` 等），多一层调用开销；
> ③ 同一个类如果既被 CGLIB 代理又被强行按接口注入，可能出现类型问题。
> 想改回 JDK：`spring.aop.proxy-target-class=false`。

### 4.3 增强链的调用顺序

```java
// ReflectiveMethodInvocation.proceed()：责任链
public Object proceed() throws Throwable {
    if (this.currentInterceptorIndex == this.interceptorsAndDynamicMethodMatchers.size() - 1)
        return invokeJoinpoint();                              // 链尾 → 真正调用目标方法
    Object interceptorOrInterceptionAdvice =
            this.interceptorsAndDynamicMethodMatchers.get(++this.currentInterceptorIndex);
    if (interceptorOrInterceptionAdvice instanceof InterceptorAndDynamicMethodMatcher dm) {
        if (dm.methodMatcher.matches(this.method, this.targetClass, this.arguments))
            return dm.interceptor.invoke(this);
        return proceed();                                      // 不匹配就跳过
    }
    return ((MethodInterceptor) interceptorOrInterceptionAdvice).invoke(this);
}
```

| 规则 | 说明 |
|---|---|
| 结构 | **责任链**（`ReflectiveMethodInvocation` 持有 advisor 列表与游标 `currentInterceptorIndex`），每个通知调 `proceed()` 推进 |
| 单个切面内顺序 | `@Around` → `@Before` → 目标方法 → `@After` / `@AfterReturning` / `@AfterThrowing` → `@Around` 收尾 |
| 多个切面之间 | 按 `@Order`/`Ordered`（值小的在外层，即**前置先执行、后置后执行**，洋葱模型） |
| `exposeProxy` | 开启后在链首插入 `ExposeInvocationInterceptor`，把 `MethodInvocation` 放进 `ThreadLocal`，供 `AopContext.currentProxy()` 使用 |

### 4.4 AOP 失效场景（必背）

| 场景 | 为什么失效 | 解决 |
|---|---|---|
| **同类自调用**（`this.foo()`） | 走的是原始对象，**没经过代理** | 拆到另一个 Bean；注入自身；`AopContext.currentProxy()` + `exposeProxy=true` |
| `private` / `static` 方法 | JDK 代理靠接口，CGLIB 靠覆写，两者都覆盖不到 | 改 `public` 并走代理 |
| `final` 类 | CGLIB 无法继承 | 去掉 `final`，或抽接口用 JDK 代理 |
| `final` 方法 | CGLIB 无法覆写 | 去掉 `final` |
| 未从容器获取 Bean（自己 `new`） | 没有代理对象 | 交给容器管理 |
| 切点表达式不匹配 | 如 `execution(* com.a.service.*.*(..))` 不覆盖子包 | 检查 `@Pointcut` 表达式 |
| **`@Transactional` 加在接口上但用 CGLIB** | 代理类不继承接口注解（新版本有兜底，但不应依赖） | 注解写在实现类/方法上 |

---

## 五、`@Transactional` 链路

### 5.1 从代理到 `TransactionInterceptor`

```java
@EnableTransactionManagement
// → @Import(TransactionManagementConfigurationSelector.class)
//   → ProxyTransactionManagementConfiguration 注册三个东西：
//      BeanFactoryTransactionAttributeSourceAdvisor（切面）
//      TransactionInterceptor（通知）
//      AnnotationTransactionAttributeSource（解析 @Transactional 属性）
```

```java
// TransactionInterceptor.invoke(MethodInvocation)
public Object invoke(MethodInvocation invocation) throws Throwable {
    Class<?> targetClass = (invocation.getThis() != null ? AopUtils.getTargetClass(invocation.getThis()) : null);
    return invokeWithinTransaction(invocation.getMethod(), targetClass, invocation::proceed);
}

protected Object invokeWithinTransaction(Method method, Class<?> targetClass, InvocationCallback invocation) {
    TransactionAttributeSource tas = getTransactionAttributeSource();
    final TransactionAttribute txAttr = (tas != null ? tas.getTransactionAttribute(method, targetClass) : null);
    final TransactionManager tm = determineTransactionManager(txAttr);
    // 无事务属性 → 直接放行
    TransactionInfo txInfo = createTransactionIfNecessary(tm, txAttr, joinpointIdentification);  // ★ 开启事务
    Object retVal;
    try {
        retVal = invocation.proceedWithInvocation();          // ★ 执行目标方法
    } catch (Throwable ex) {
        completeTransactionAfterThrowing(txInfo, ex);         // ★ 按规则回滚
        throw ex;
    } finally {
        cleanupTransactionInfo(txInfo);                       // 恢复线程绑定的旧事务信息
    }
    commitTransactionAfterReturning(txInfo);                  // 正常返回 → 提交
    return retVal;
}

protected void completeTransactionAfterThrowing(TransactionInfo txInfo, Throwable ex) {
    if (txInfo.transactionAttribute != null && txInfo.transactionAttribute.rollbackOn(ex)) {
        txInfo.getTransactionManager().rollback(txInfo.getTransactionStatus());    // 回滚
    } else {
        // ★ 不满足回滚条件 → 竟然还是 commit！（受检异常默认就是这个分支）
        txInfo.getTransactionManager().commit(txInfo.getTransactionStatus());
    }
}

// DefaultTransactionAttribute
public boolean rollbackOn(Throwable ex) {
    return (ex instanceof RuntimeException || ex instanceof Error);   // ★ 默认只回滚这两个
}
```

### 5.2 传播行为

| 传播行为 | 语义 | 关键机制 |
|---|---|---|
| `REQUIRED`（默认） | 有事务就加入，没有就新建 | 复用线程绑定的连接 |
| `SUPPORTS` | 有就加入，没有就以非事务方式执行 | —— |
| `MANDATORY` | 必须已有事务，否则抛异常 | —— |
| **`REQUIRES_NEW`** | **总是新建独立事务，挂起当前事务** | `getTransaction` 中 `if (propagation == REQUIRES_NEW) { SuspendedResourcesHolder suspendedResources = suspend(transaction); ... }` → **解绑当前连接的 ThreadLocal、重新取一条新连接** |
| `NOT_SUPPORTED` | 以非事务执行，挂起当前事务 | 同上 suspend |
| `NEVER` | 必须无事务，否则抛异常 | —— |
| **`NESTED`** | 嵌套事务，**依赖 savepoint** | `if (propagation == NESTED) { if (useSavepointForNestedTransaction()) { status.createAndHoldSavepoint(); } }`；`DataSourceTransactionManager.useSavepointForNestedTransaction()` 返回 `true` → `connection.setSavepoint()` |

| 对比 | `REQUIRES_NEW` | `NESTED` |
|---|---|---|
| 连接 | **新连接**（挂起外层） | **同一个连接** |
| 底层机制 | 真正的新事务 | **JDBC savepoint** |
| 内层回滚 | 只影响自己，**外层不受影响**（外层可继续提交） | 回滚到 savepoint，**外层可继续**；若外层也回滚则全部回滚 |
| 内层提交 | **独立提交**（外层回滚了内层也已落库） | 内层"提交"只是**释放 savepoint**，真正提交由外层决定 |
| 外层回滚对内层 | **无影响**（内层已提交） | **一起回滚** |
| 数据库要求 | 无特殊要求 | **必须支持 savepoint**（MySQL InnoDB 支持；JTA 下会退化为 `REQUIRES_NEW`） |
| 死锁风险 | 高（两条连接争同一行） | 低（同一连接） |

> [!danger] `REQUIRES_NEW` 最容易被误解的一点
> "外层回滚，内层也回滚"——**错**。`REQUIRES_NEW` 是真正独立的物理事务，**内层提交后外层回滚不会撤销它**。想"外层回滚则内层一起回滚"，要用 `NESTED`（savepoint）。
> 反过来，"内层回滚不影响外层"——`REQUIRES_NEW` 和 `NESTED` **都能做到**，前提是内层异常被 `try/catch` 住没有继续往外抛。

### 5.3 事务失效的常见场景（必背）

| 场景 | 原因 |
|---|---|
| **同类自调用** | `this.method()` 不走代理，事务拦截器根本没被执行（最常见） |
| **方法非 `public`** | `AbstractFallbackTransactionAttributeSource` 默认 `allowPublicMethodsOnly()`，非 public 直接返回 null 属性 → 无事务。**注意 Spring 6.x 对基于类代理的限制有放宽，答题时点明版本更稳妥** |
| **异常被自己吞掉** | `try/catch` 后不抛，拦截器看到的是"正常返回"→ **提交** |
| **默认只回滚 `RuntimeException`/`Error`** | 抛受检异常（`IOException` 等）默认**会提交**！必须写 `@Transactional(rollbackFor = Exception.class)` |
| **多线程** | 子线程拿的是**新连接**，不在当前事务里（见 §5.4） |
| **数据库引擎不支持事务** | 如 MySQL `MyISAM` 表 |
| **注解位置不对** | 加在接口上但用 CGLIB 代理，或加到 `final` 方法/私有方法上 |
| **`@Transactional` 加在 Controller 上** | 通常无效果也无意义（没有跨 DB 的原子性需求），且容易被 AOP 顺序影响 |
| **事务已提交后抛异常** | 提交后 `finally` 里抛异常，事务已经提交，无法回滚 |

> [!important] `rollbackFor` 的正确写法
> ```java
> @Transactional(rollbackFor = Exception.class)   // ✅ 受检异常也回滚
> public void doWork() throws IOException { ... }
> ```
> 顺带：`@Transactional` 还有一个容易被忽略的属性 `propagation`（默认 `REQUIRED`）、`isolation`、`timeout`、`readOnly`。**`readOnly=true` 不是"优化"，它只是提示**（MySQL 下可让驱动走只读连接、跳过部分检查），真正的只读要靠库/账号权限或读写分离路由。

### 5.4 `TransactionSynchronizationManager` 与跨线程

```java
public abstract class TransactionSynchronizationManager {
    private static final ThreadLocal<Map<Object, Object>> resources = ...;      // ★ 连接/会话绑定在这
    private static final ThreadLocal<Set<TransactionSynchronization>> synchronizations = ...;
    private static final ThreadLocal<String> currentTransactionName = ...;
    private static final ThreadLocal<Boolean> currentTransactionReadOnly = ...;
    private static final ThreadLocal<Integer> currentTransactionIsolationLevel = ...;
    private static final ThreadLocal<Boolean> actualTransactionActive = ...;
}
```

| 结论 | 说明 |
|---|---|
| 事务的本质是 **ThreadLocal 绑定连接** | `DataSourceTransactionManager.doBegin` 里 `TransactionSynchronizationManager.bindResource(dataSource, txObject.getConnectionHolder())` |
| **跨线程必然失效** | 新线程的 `ThreadLocal` 是空的 → 拿不到已绑定的连接 → 要么新开事务，要么报"no transaction"。`@Async`、`CompletableFuture`、`new Thread`、线程池**全都算跨线程** |
| 想让子线程共享事务 | 只能是 **`TransactionSynchronization` 回调**（在事务提交/回滚后执行），或者子线程自己做补偿；**没有"跨线程共享同一个 JDBC 连接"的正当做法**（连接不是线程安全的） |
| 常见误用 | "在事务方法里 `CompletableFuture.runAsync(() -> dao.insert(...))`，外层回滚了但数据还在"——因为子线程是**独立事务且已提交** |

> [!danger] `@Async` 与事务混用的三个坑
> 1. **异步方法读不到调用方未提交的数据**：`@Async` 方法在另一个线程、另一个连接上执行，默认隔离级别下读不到调用方未提交的修改，于是"明明刚 insert 了却查不到"。
> 2. **异步方法里写的数据不受调用方事务保护**：调用方回滚，异步写的数据**已经落库**，造成脏数据。
> 3. **同一方法上同时标 `@Async` + `@Transactional`**：两个通知都通过 `BeanPostProcessor` 生成代理，**AOP 顺序决定了谁能生效**——常见结果是事务属性被"跳过"或事务在异步线程里另开一个，实际语义和你以为的不一样。
> **正确做法**：
> ① 把"必须先提交再异步"的流程改成**事务提交后触发**——`TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() { public void afterCommit() { asyncService.doIt(); } })`，或 Spring 的 `@TransactionalEventListener(phase = AFTER_COMMIT)`；
> ② 异步方法自己显式加 `@Transactional`，把它当**独立事务**看待；
> ③ 不要在异步方法里依赖调用方的事务上下文。

---

## 六、Spring MVC 请求链路

### 6.1 `DispatcherServlet.doDispatch` 主干

```java
protected void doDispatch(HttpServletRequest request, HttpServletResponse response) throws Exception {
    processedRequest = checkMultipart(request);                        // ① 文件上传包装
    mappedHandler = getHandler(processedRequest);                      // ② HandlerMapping → HandlerExecutionChain
    if (mappedHandler == null) { noHandlerFound(processedRequest, response); return; }
    HandlerAdapter ha = getHandlerAdapter(mappedHandler.getHandler());  // ③ 找适配器
    if (!mappedHandler.applyPreHandle(processedRequest, response)) return;  // ④ 拦截器 preHandle
    mv = ha.handle(processedRequest, response, mappedHandler.getHandler()); // ⑤ 执行 Controller
    if (asyncManager.isConcurrentHandlingStarted()) return;             // 异步请求直接返回
    applyDefaultViewName(processedRequest, mv);
    mappedHandler.applyPostHandle(processedRequest, response, mv);      // ⑥ 拦截器 postHandle
    processDispatchResult(processedRequest, response, mappedHandler, mv, dispatchException);  // ⑦ 异常/视图
}
```

| 步骤 | 关键接口 | 实现类 |
|---|---|---|
| ② 找 handler | `HandlerMapping` | `RequestMappingHandlerMapping`（`@RequestMapping`）、`SimpleUrlHandlerMapping`、`BeanNameUrlHandlerMapping`。内部 `AbstractHandlerMethodMapping.lookupHandlerMethod` 用 `RequestMappingInfo` 匹配，含 `@PathVariable` 的路径优先 |
| ③ 适配 | `HandlerAdapter` | `RequestMappingHandlerAdapter`（`@RequestMapping` 方法）、`HttpRequestHandlerAdapter`、`SimpleControllerHandlerAdapter` |
| ④⑥ 拦截 | `HandlerInterceptor` | `preHandle`（返回 false 则中断）→ 目标 → `postHandle` → 视图渲染 → `afterCompletion` |
| ⑤ 执行 | `ServletInvocableHandlerMethod.invokeAndHandle` | 参数解析 + 反射调用 + 返回值处理 |
| ⑦ 异常 | `HandlerExceptionResolver` | `ExceptionHandlerExceptionResolver`（处理 `@ExceptionHandler`/`@ControllerAdvice`）→ `ResponseStatusExceptionResolver`（`@ResponseStatus`）→ `DefaultHandlerExceptionResolver`（Spring 内置异常） |

### 6.2 参数解析与返回值处理

```java
// InvocableHandlerMethod.invokeForRequest → getMethodArgumentValues
Object[] args = new Object[parameters.length];
for (int i = 0; i < parameters.length; i++) {
    MethodParameter parameter = parameters[i];
    if (this.argumentResolvers.supportsParameter(parameter)) {
        args[i] = this.argumentResolvers.resolveArgument(parameter, mavContainer, request, this.dataBinderFactory);
    }
}
doInvoke(args);
```

| 方向 | 接口 | 主要实现 |
|---|---|---|
| **入参** | `HandlerMethodArgumentResolver` | `RequestParamMethodArgumentResolver`（`@RequestParam`）、`PathVariableMethodArgumentResolver`（`@PathVariable`）、`RequestHeaderMethodArgumentResolver`、`CookieValueMethodArgumentResolver`、`SessionAttributeMethodArgumentResolver`、`ServletRequestMethodArgumentResolver`（`HttpServletRequest`/`InputStream`）、`ModelAttributeMethodProcessor`（`@ModelAttribute`/表单对象）、**`RequestResponseBodyMethodProcessor`（`@RequestBody`）**、`RequestPartMethodArgumentResolver`（`@RequestPart`/`MultipartFile`） |
| **返回值** | `HandlerMethodReturnValueHandler` | **`RequestResponseBodyMethodProcessor`（`@ResponseBody`）**、`ModelAndViewMethodReturnValueHandler`、`ViewNameMethodReturnValueHandler`、`HttpEntityMethodProcessor`、`ResponseBodyEmitterReturnValueHandler`、`StreamingResponseBodyReturnValueHandler` |
| **消息转换** | `HttpMessageConverter` | `MappingJackson2HttpMessageConverter`（JSON）、`StringHttpMessageConverter`、`FormHttpMessageConverter`、`ByteArrayHttpMessageConverter`、`ResourceHttpMessageConverter` |

**`@RequestBody` / `@ResponseBody` 的转换器机制**：

| 方向 | 选择转换器的依据 | 过程 |
|---|---|---|
| `@RequestBody` | Content-Type + `canRead(targetType, contentType)` | `readWithMessageConverters` → 选转换器 → `MappingJackson2HttpMessageConverter.read` → `ObjectMapper.readValue` |
| `@ResponseBody` | **`Accept` 头 + `produces`** 求可产生的 media type，再 `canWrite(targetType, mediaType)` | `writeWithMessageConverters` → 选转换器 → 写响应，`Content-Type` 由转换器决定 |

> [!note] 两个实用细节
> ① **`@RestController` = `@Controller` + `@ResponseBody`**；`@ControllerAdvice`/`@RestControllerAdvice` 用来集中 `@ExceptionHandler`/`@InitBinder`/`@ModelAttribute`。
> ② **`@RequestBody` 的流只能读一次**：如果在 `Filter` 里读了 `getInputStream()`，Controller 里就读不到了，必须用 `ContentCachingRequestWrapper` 包装后重读。这是"加了日志 Filter 后 `@RequestBody` 变 null"的根因。

### 6.3 拦截器 vs 过滤器

| 维度 | `Filter`（`jakarta.servlet.Filter`） | `HandlerInterceptor` |
|---|---|---|
| 规范 | **Servlet 规范**，由 Servlet 容器管理 | **Spring MVC 规范**，由 `DispatcherServlet` 管理 |
| 位置 | 在 `DispatcherServlet` **之前** | 在 `DispatcherServlet` **内部** |
| 能拿到什么 | 原始 `ServletRequest`/`ServletResponse`（**可包装/改写请求体**） | `HttpServletRequest` + **`HandlerMethod`（知道要执行哪个方法）** |
| 能否依赖注入 | 由容器管理（Spring Boot 里能注入，但属于 Web 组件） | ✅ 完全是 Spring Bean，可自由注入 |
| 回调 | `doFilter`（前后包一段） | `preHandle` / `postHandle` / `afterCompletion`（`afterCompletion` 在**视图渲染之后**） |
| 异常 | 抛出的异常可能绕过 Spring MVC 的 `HandlerExceptionResolver` | 异常能被 `@ControllerAdvice` 处理 |
| 执行顺序 | `Filter` → `DispatcherServlet` → `preHandle` → (AOP 代理) → **Controller** → `postHandle` → 视图渲染 → `afterCompletion` | —— |

> [!tip] 选型口诀
> 要**改写请求/响应**（如请求体缓存、CORS、编码、Servlet 级鉴权）→ `Filter`；
> 要**基于 Controller 方法做拦截**（登录校验、日志埋点、幂等、限流注解）→ `Interceptor`。

---

## 七、Spring Boot 自动配置

### 7.1 `@SpringBootApplication` 的组成

```java
@SpringBootApplication
// = 以下三个注解的组合
@SpringBootConfiguration            // 本质就是 @Configuration
@EnableAutoConfiguration            // = @AutoConfigurationPackage + @Import(AutoConfigurationImportSelector.class)
@ComponentScan(excludeFilters = { @Filter(type = FilterType.CUSTOM, classes = TypeExcludeFilter.class),
                                  @Filter(type = FilterType.CUSTOM, classes = AutoConfigurationExcludeFilter.class) })
```

### 7.2 候选配置的加载与过滤

| 环节 | 内容 |
|---|---|
| 触发 | `AutoConfigurationImportSelector.selectImports` → `getAutoConfigurationEntry(annotationMetadata)` |
| **加载候选** | 2.7+：`ImportCandidates.load(AutoConfiguration.class, classLoader)` 读 **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`**；2.7 之前：`SpringFactoriesLoader.loadFactoryNames(EnableAutoConfiguration.class, classLoader)` 读 **`META-INF/spring.factories`**。**2.7 起迁移（`.imports` 为准，`spring.factories` 方式废弃，3.0 移除）** |
| 去重与排除 | `removeDuplicates` + `getExclusions`（来自 `spring.autoconfigure.exclude` 属性 + `@EnableAutoConfiguration(exclude=...)`）；被排除的会**校验是不是合法自动配置类**，不合法直接抛异常 |
| **条件裁剪** | `filter(configurations, autoConfigurationMetadata)` 用 `AutoConfigurationImportFilter`（`OnClassCondition`、`OnBeanCondition`、`OnWebApplicationCondition`）做**快速过滤**——目的不是语义判断，而是**避免加载大量无关自动配置类**（性能优化：能用 `@ConditionalOnClass` 快速裁掉的，就不去解析类内容） |
| 排序 | `@AutoConfigureBefore`/`@AutoConfigureAfter`/`@AutoConfigureOrder` |
| 生效 | 回到第 5 步 `invokeBeanFactoryPostProcessors` 时，这些自动配置类作为 `@Configuration` 被 `ConfigurationClassPostProcessor` 解析 |

### 7.3 条件注解

| 注解 | 判断依据 | 典型用途 |
|---|---|---|
| `@ConditionalOnClass` / `@ConditionalOnMissingClass` | classpath 是否有某类 | "引入 Redis 依赖才配置 RedisTemplate" |
| **`@ConditionalOnMissingBean`** | 容器里是否**还没有**该类型 Bean | **用户自定义 Bean 优先**——自动配置的兜底机制 |
| `@ConditionalOnBean` | 容器里**已有**该类型 Bean | 依赖其他自动配置的产物 |
| `@ConditionalOnProperty` | 配置项的值/是否存在 | `spring.xxx.enabled=true` |
| `@ConditionalOnWebApplication` | `WebApplicationType`（SERVLET/REACTIVE） | 区分 Web / 非 Web |
| `@ConditionalOnSingleCandidate` | 该类型**只有一个**（或标了 `@Primary`）Bean | 自动配置强依赖 |
| `@ConditionalOnResource` | 资源文件是否存在 | —— |
| `@ConditionalOnExpression` | SpEL 表达式 | 复杂条件 |
| `@ConditionalOnJava` | JDK 版本区间 | —— |

> [!important] `@ConditionalOnMissingBean` 为什么"只在自动配置里可靠"？
> 因为它依赖**处理顺序**：普通用户配置类先被解析注册，自动配置类后被解析，此时"容器里有没有这个 Bean"才有意义。
> 若把它写在**自己的 `@Configuration`** 里，它可能在你自己的另一个 `@Bean` 之前求值，结果不可预测。**它是一套"兜底"机制，不是"防重复注册"的通用工具。**

### 7.4 覆盖与排除的四种方式

| 方式 | 做法 | 适用 | 风险 |
|---|---|---|---|
| **自定义 Bean 覆盖** | 自己声明同类型 `@Bean` | 改行为（如自定义 `ObjectMapper`） | 依赖 `@ConditionalOnMissingBean` 生效，否则可能两个 Bean 共存导致 `NoUniqueBeanDefinitionException` |
| **排除自动配置** | `spring.autoconfigure.exclude=org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration` | 完全不想要某个自动配置 | 要写全类名，写错会启动失败（有校验） |
| **注解排除** | `@SpringBootApplication(exclude = XxxAutoConfiguration.class)` 或 `excludeName` | 代码内声明 | 需要编译期依赖该类 |
| **属性覆盖** | `application.yml` 里覆盖属性（`@ConfigurationProperties` 宽松绑定：`my-app.max-size`、`MY_APP_MAX_SIZE`、`myApp.maxSize` 都可绑定） | 只改参数不改结构 | 优先级：命令行 > 环境变量 > `application-{profile}.yml` > `application.yml` |

### 7.5 启动主线（简）

```
SpringApplication.run(主类, args)
 ├─ new SpringApplication(...)   // 推断 WebApplicationType、加载 ApplicationContextInitializer/Listener（spring.factories）
 ├─ run(args)
 │   ├─ prepareEnvironment()     // 加载配置文件、发布 ApplicationEnvironmentPreparedEvent
 │   ├─ createApplicationContext() // ServletWebServerApplicationContext
 │   ├─ prepareContext()         // 注册主类 BeanDefinition、执行 Initializer、发布 ContextPreparedEvent
 │   ├─ refreshContext()         // ★ 就是 §1.2 的 refresh()，onRefresh 建 Tomcat、finishRefresh 启动它
 │   ├─ afterRefresh()
 │   └─ listeners.started()      // 发布 ApplicationStartedEvent / ApplicationReadyEvent
```

---

## 八、MyBatis 与 Spring 集成骨架

### 8.1 Mapper 接口是怎么变成 Bean 的

```
@MapperScan("com.x.mapper")
 └─ @Import(MapperScannerRegistrar.class)
     └─ 注册 MapperScannerConfigurer (BeanDefinitionRegistryPostProcessor)
         └─ postProcessBeanDefinitionRegistry → ClassPathMapperScanner.scan(...)
             └─ processBeanDefinitions：把接口的 beanClass 改成 MapperFactoryBean
                 · 构造参数 = 接口全类名
                 · setAutowireMode(AUTOWIRE_BY_TYPE)
                 · 注入 sqlSessionFactory / sqlSessionTemplate
```

| 环节 | 关键类 | 说明 |
|---|---|---|
| 扫接口 | `ClassPathMapperScanner` extends `ClassPathBeanDefinitionScanner` | 只认 `interface`，默认 `addIncludeFilter` 扫所有接口 |
| 变 Bean | `MapperFactoryBean<T> extends SqlSessionDaoSupport implements FactoryBean<T>` | **`FactoryBean`**，所以容器里真正暴露的对象是 `getObject()` 的返回值 |
| 生成代理 | `getObject()` → `getSqlSession().getMapper(mapperInterface)` → `MapperRegistry.getMapper` → `MapperProxyFactory.newInstance(sqlSession)` → **`Proxy.newProxyInstance`（JDK 动态代理）** | Mapper 接口**没有实现类**，全靠 JDK 代理 |
| 调用 | `MapperProxy implements InvocationHandler` → `cachedInvoker(method)` → `MapperMethod.execute(sqlSession, args)` | `SqlCommand` 决定 statement id 与类型（INSERT/UPDATE/DELETE/SELECT/FLUSH），`MethodSignature` 决定 `selectOne`/`selectList`/`selectMap` |

> [!warning] Mapper 接口**不支持方法重载**
> statement id = `namespace + "." + methodName`。同名方法（即使参数不同）会导致 "Mapped Statements collection already contains value" 或直接绑错语句。这是实际开发中容易踩的坑。

### 8.2 `SqlSessionTemplate` 为什么线程安全

```java
public class SqlSessionTemplate implements SqlSession, DisposableBean {
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
        SqlSession sqlSession = getSqlSession(SqlSessionTemplate.this.sqlSessionFactory,
                SqlSessionTemplate.this.executorType, SqlSessionTemplate.this.exceptionTranslator);
        try {
            Object result = method.invoke(sqlSession, args);
            if (!isSqlSessionTransactional(sqlSession, SqlSessionTemplate.this.sqlSessionFactory)) {
                sqlSession.commit(true);              // 非事务环境：每次操作后自动提交
            }
            return result;
        } catch (Throwable t) {
            Throwable unwrapped = unwrapThrowable(t);
            if (SqlSessionTemplate.this.exceptionTranslator != null && unwrapped instanceof PersistenceException) {
                closeSqlSession(sqlSession, ...);
                sqlSession = null;
                Throwable translated = ...translateExceptionIfPossible((PersistenceException) unwrapped);
                if (translated != null) unwrapped = translated;
            }
            throw unwrapped;
        } finally {
            if (sqlSession != null) closeSqlSession(sqlSession, SqlSessionTemplate.this.sqlSessionFactory);
        }
    }
}
```

| 要点 | 说明 |
|---|---|
| `SqlSession` 本身**非线程安全** | 官方文档明确说明 |
| `SqlSessionTemplate` 是**线程安全的** | 它内部持有一个 JDK 动态代理（`SqlSessionInterceptor`），**每次调用都从 `SqlSessionUtils.getSqlSession` 拿"当前线程"的 SqlSession** |
| 与事务同步 | `getSqlSession` → `TransactionSynchronizationManager.getResource(sessionFactory)`：**在事务里就复用同一个 `SqlSessionHolder`**；不在事务里就 `openSession()` 然后注册 `TransactionSynchronization` 在事务结束时关闭 |
| 结论 | **同一个事务（同一线程）共享同一个 `SqlSession` 与同一个数据库连接** → 这既保证了事务性，也解释了为什么"跨线程必然失效"（与 §5.4 同源） |
| Executor | `SimpleExecutor`（每次新建 `Statement`）、`ReuseExecutor`（复用 `Statement`）、`BatchExecutor`（批处理）；`newExecutor` 后再包一层 `CachingExecutor` |

### 8.3 一级 / 二级缓存

| 维度 | 一级缓存 | 二级缓存 |
|---|---|---|
| 位置 | `BaseExecutor.localCache`（默认 `PerpetualCache`，本质是 `HashMap`） | `CachingExecutor` + `MappedStatement.cache`（**namespace 级**） |
| 作用域 | **`SqlSession` 级** | **namespace（Mapper 接口）级**，跨 `SqlSession` |
| 默认 | **开启** | 需显式开启（`<cache/>` / `@CacheNamespace`）；`configuration.cacheEnabled` 默认 true |
| 失效 | 同一 `SqlSession` 内执行 `update`/`insert`/`delete`、`commit`/`rollback`、`clearCache` | **该 namespace 的写操作提交后**清空本 namespace 缓存 |
| Spring 下的实际效果 | 因为同一事务共享一个 `SqlSession`，所以**一级缓存在一个事务内有效**；事务结束（`SqlSession` 关闭）即失效 | 跨事务有效，**多节点部署会数据不一致** |
| 缓存 key | statement id + sql + 参数 + rowbounds（`CacheKey`） | 同左 |
| 生产建议 | 不要依赖（容易"查不到刚改的数据"） | **单机可用；分布式一律用 Redis 等外部缓存替代，或直接关闭**（`mybatis.configuration.cache-enabled=false`） |

> [!danger] 二级缓存的经典事故
> 两个服务实例共享同一 DB，实例 A 更新数据后清了自己 JVM 里的二级缓存，实例 B 的二级缓存**仍然是旧值** → 用户看到"改了但没生效"。**分布式环境下二级缓存必须换成集中式缓存或关闭。**

---

## 九、设计模式视角小结

| 模式 | Spring 中的体现 |
|---|---|
| **模板方法** | `AbstractApplicationContext.refresh()`（十二步固定、`onRefresh` 钩子）、`JdbcTemplate`/`RestTemplate`、`AbstractPlatformTransactionManager`、`AbstractBeanDefinitionReader` |
| **工厂** | `BeanFactory`、`FactoryBean`（`MapperFactoryBean`）、`ProxyFactory`、`SqlSessionFactory`、`AnnotationConfigApplicationContext` |
| **单例** | 容器内单例 + **三级缓存**（`singletonObjects`）；注意 Spring 单例是"每个容器一个"，不是 GoF 的进程级单例 |
| **代理** | AOP（JDK/CGLIB）、`MapperProxy`、`SqlSessionTemplate` 内部代理、`@Transactional` |
| **观察者** | `ApplicationEvent` / `ApplicationListener` / `ApplicationEventMulticaster` / `@EventListener` |
| **责任链** | `ReflectiveMethodInvocation`、`HandlerExecutionChain` + `HandlerInterceptor`、`FilterChain`、`MethodArgumentResolverComposite` |
| **策略** | `Resource`/`ResourceLoader`、`HandlerMapping`、`InstantiationStrategy`、`PlatformTransactionManager`、`HttpMessageConverter` |
| **适配器** | `HandlerAdapter`（把各种 Handler 适配成统一调用）、`AdvisorAdapter`、`MethodArgumentResolver` |
| **装饰器** | `TransactionAwareCacheDecorator`、`HttpServletRequestWrapper`、`BeanWrapper` |
| **建造者** | `BeanDefinitionBuilder`、`MockMvcBuilders`、`SpringApplicationBuilder` |

> [!note] 面试怎么答"Spring 用到了哪些设计模式"
> 不要背清单，**挑三个讲透**：① **模板方法**——`refresh()` 十二步里 `onRefresh`/`postProcessBeanFactory` 是钩子，这是"骨架固定、细节可变"的典范；② **工厂 + 单例**——`BeanFactory` 生产 Bean，`getSingleton` 三级缓存保证单例与提前暴露，两者结合解决了循环依赖；③ **代理 + 责任链**——AOP 用 `AbstractAutoProxyCreator` 生成代理，`ReflectiveMethodInvocation` 串起通知链。
> 展开见 [[2-面向对象与设计模式]]。

---

## 十、常见面试追问速查表

| # | 问题 | 一句话答案骨架 |
|---|---|---|
| 1 | `BeanFactory` vs `ApplicationContext` | `BeanFactory` 是最底层容器（**延迟加载**、只有 DI 能力）；`ApplicationContext` 是它的超集，**启动时实例化非懒加载单例**，多了事件、国际化、资源、AOP、环境等能力 |
| 2 | `FactoryBean` vs `BeanFactory` | `BeanFactory` 是**容器**；`FactoryBean` 是**容器里的一个 Bean**，其 `getObject()` 的产物才是"这个 Bean 对外暴露的对象"，`&beanName` 取工厂本身 |
| 3 | `@Autowired` vs `@Resource` | `@Autowired` 是 **Spring** 的，**按类型**注入（多个候选时靠 `@Qualifier`/`@Primary` 决策）；`@Resource` 是 **JSR-250**，**默认按名称**、找不到再按类型 |
| 4 | Bean 的作用域 | `singleton`（默认）、`prototype`、`request`、`session`、`application`、`websocket`；后四者需 Web 环境。**prototype 不参与循环依赖解决、不管理销毁** |
| 5 | Spring 单例 Bean 线程安全吗 | **不安全**——单例 + 无状态才安全。有可变成员变量就必须自己保证同步（这也是为什么 Service/DAO 都写成无状态的） |
| 6 | `@Configuration` 的 `proxyBeanMethods` | 默认 `true` → CGLIB 增强配置类，保证 `@Bean` 方法之间互相调用仍返回**同一个单例**；`false` → 不增强（"lite 模式"），启动更快，但 `@Bean` 方法内互调会**new 出新对象** |
| 7 | `BeanPostProcessor` vs `BeanFactoryPostProcessor` | `BeanFactoryPostProcessor` 在**所有 Bean 实例化之前**修改 **BeanDefinition**（如 `ConfigurationClassPostProcessor`、占位符解析）；`BeanPostProcessor` 在**每个 Bean 初始化前后**修改 **Bean 实例**（如 `@Autowired`、`@PostConstruct`、AOP） |
| 8 | 三级缓存为什么是三级 | 见 §3.2：把"是否生成 AOP 代理"延迟到真的发生循环依赖时，并用 `earlyProxyReferences` 保证代理只生成一次 |
| 9 | 哪些循环依赖解决不了 | 构造器注入、prototype、`@Async` 等额外包装场景；**Boot 2.6+ 默认全禁**（`spring.main.allow-circular-references=false`） |
| 10 | AOP 什么时候生成代理 | `AbstractAutoProxyCreator.postProcessAfterInitialization`（Bean 初始化的最后一步）；发生循环依赖时会由 `getEarlyBeanReference` 提前生成 |
| 11 | 为什么 AOP 有时不生效 | 自调用、private/static、final 类/方法、未从容器获取、切点不匹配（见 §4.4） |
| 12 | `@Transactional` 默认回滚什么 | **`RuntimeException` 和 `Error`**；受检异常默认**提交**，要写 `rollbackFor = Exception.class` |
| 13 | `REQUIRES_NEW` vs `NESTED` | 前者**挂起外层 + 新连接 + 独立提交**；后者**同一连接 + savepoint**，外层回滚则一起回滚（见 §5.2） |
| 14 | 事务为什么会失效 | 自调用、非 public、异常被吞、默认不回滚受检异常、多线程、DB 引擎不支持、注解位置不对（见 §5.3） |
| 15 | 跨线程能共享事务吗 | **不能**。事务靠 `TransactionSynchronizationManager` 的 `ThreadLocal` 绑定连接；`@Async`/`CompletableFuture` 一律是新事务，只能用 `afterCommit` 回调或 `@TransactionalEventListener(AFTER_COMMIT)` 串联 |
| 16 | `@ConditionalOnMissingBean` 为何只在自动配置可靠 | 它依赖"用户配置先解析、自动配置后解析"的顺序；写在业务 `@Configuration` 里求值时机不可控 |
| 17 | Boot 2.7 自动配置有什么变化 | 从 `META-INF/spring.factories` 迁到 **`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`**；2.7 兼容两者（`spring.factories` 废弃），3.0 移除 |
| 18 | `DispatcherServlet` 完整链路 | `HandlerMapping` 找 handler → `HandlerAdapter` 适配 → `HandlerMethodArgumentResolver` 解析参数 → 反射调用 → `HandlerMethodReturnValueHandler` → `HttpMessageConverter` 写响应 |
| 19 | 拦截器与过滤器的区别 | Filter 是 Servlet 规范、在 `DispatcherServlet` 之外、能改写请求响应；Interceptor 是 Spring MVC 的、在 `DispatcherServlet` 之内、能拿到 `HandlerMethod` 和注入 Bean（见 §6.3） |
| 20 | `SqlSessionTemplate` 为什么线程安全 | 内部每次调用都从 `ThreadLocal`（`TransactionSynchronizationManager`）取当前线程的 `SqlSession`，事务内复用、非事务自动提交 |
| 21 | MyBatis 一二级缓存 | 一级 = `SqlSession` 级（Spring 下一个事务内有效，默认开启）；二级 = namespace 级（跨 `SqlSession`，**分布式下会不一致，建议关闭或换 Redis**） |
| 22 | Mapper 接口为什么能注入 | `@MapperScan` → `MapperScannerConfigurer` 把接口注册成 `MapperFactoryBean`（`FactoryBean`），其 `getObject()` 用 **JDK 动态代理** 生成 `MapperProxy` |

---

> 以上是面试可复述的**骨架**；逐行级源码分析（`refresh()` 完整调用栈、`ConfigurationClassPostProcessor` 解析细节、`ConfigurationClassParser` 的 `@Import` 三级处理、`RequestMappingInfo` 匹配算法、`AutoConfigurationImportSelector` 全部过滤路径等）见 [[面试准备/技术面试题库/13-Spring源码专题]]。
