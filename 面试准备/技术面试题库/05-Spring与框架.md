---
title: 05-Spring与框架
tags: [面试, Java, 技术题库, Spring, MyBatis]
status: 进行中
---

# 🌱 05 · Spring 与框架

> 返回 [[00-总览与使用说明]]

---

## 一、Spring 核心

| 问题 | 得分骨架 |
|---|---|
| IoC 是什么 | 控制反转：对象创建与依赖装配交给容器；好处：解耦、易测试 |
| DI 注入方式 | 构造器（**推荐**，可不变性、暴露循环依赖）、Setter、字段（@Autowired，不推荐） |
| AOP 原理 | 动态代理：**JDK 动态代理（接口）** / **CGLIB（继承，子类）**；Spring Boot 2.x 默认 CGLIB |
| AOP 应用 | 事务、日志、权限、缓存、埋点；通知类型：Before/After/AfterReturning/AfterThrowing/Around |
| **Bean 生命周期** | 实例化 → 属性填充 → Aware 接口 → BeanPostProcessor.before → `@PostConstruct` / `afterPropertiesSet` → BeanPostProcessor.after（**AOP 代理在此生成**）→ 使用 → `@PreDestroy` |
| **循环依赖三级缓存** `#高频` | ① singletonObjects 成品 ② earlySingletonObjects 半成品 ③ singletonFactories 工厂（**用于提前暴露 AOP 代理**） |
| 为什么需要第三级 | 若 A 需要被代理，注入 B 的必须是**代理对象**；第三级缓存存工厂，可在需要时提前生成代理，保证单例 |
| 循环依赖哪些解决不了 | **构造器注入**、**prototype**、`@Async` 场景 → 直接报错 |
| Bean 作用域 | singleton（默认）/ prototype / request / session / application |
| `@Autowired` vs `@Resource` | 前者按类型（可配 @Qualifier 按名）；后者按名字再按类型（JDK 注解） |
| BeanFactory vs ApplicationContext | 懒加载 vs 预加载；后者功能更全（事件、国际化、AOP） |

---

## 二、事务 `#高频`

**传播行为**（7 种，重点 3 个）
- `REQUIRED`（默认）：有则加入，无则新建
- `REQUIRES_NEW`：总是新建，挂起当前
- `NESTED`：嵌套，靠 savepoint（**父回滚子也回滚，子回滚父可继续**）

**隔离级别**：DEFAULT / READ_UNCOMMITTED / READ_COMMITTED / REPEATABLE_READ（MySQL 默认）/ SERIALIZABLE

**失效场景**（面试必问，能说 5 个以上）
1. **方法自调用**（不走代理）→ 解法：注入自己 / AopContext.currentProxy()
2. 方法**非 public**
3. 异常被 **catch 吞掉**（没抛出）
4. 抛出的是**受检异常**（默认只回滚 RuntimeException/Error）→ `rollbackFor = Exception.class`
5. 类**没被 Spring 管理**（自己 new）
6. 多线程（事务绑定 ThreadLocal，子线程拿不到）
7. 数据库引擎不支持事务（MyISAM）
8. 传播行为设置不当（如 NOT_SUPPORTED）

---

## 三、Spring MVC

**请求流程**：
```
DispatcherServlet → HandlerMapping 找 handler → HandlerAdapter 执行
→ 参数解析/数据绑定 → 调用 Controller → 返回 ModelAndView
→ ViewResolver 解析视图 → 渲染 → 响应
```
- 拦截器 vs 过滤器：Filter 是 Servlet 规范（更早、粒度粗）；Interceptor 是 Spring 的（能拿到 handler、更灵活）
- 常用注解：`@RestController` / `@RequestMapping` / `@RequestBody` / `@PathVariable` / `@RequestParam` / `@ControllerAdvice`

---

## 四、Spring Boot

| 问题 | 得分骨架 |
|---|---|
| 自动装配原理 | `@SpringBootApplication` = `@SpringBootConfiguration` + `@ComponentScan` + `@EnableAutoConfiguration`；后者通过 `@Import(AutoConfigurationImportSelector)` 读取 **`META-INF/spring.factories`**（2.7+ 改为 `AutoConfiguration.imports`），配合 `@ConditionalOnXxx` 按需生效 |
| 起步依赖 | starter 聚合依赖，简化版本管理 |
| 内嵌容器 | Tomcat / Jetty / Undertow |
| 配置优先级 | 命令行 > 环境变量 > `application-{profile}.yml` > `application.yml` |
| 如何自定义 starter | 写自动配置类 + `spring.factories` / `imports` 文件 |
| Actuator | 健康检查、指标、监控端点 |

---

## 五、MyBatis

| 问题 | 得分骨架 |
|---|---|
| 执行流程 | SqlSessionFactory → SqlSession → Executor → StatementHandler → ParameterHandler → ResultSetHandler |
| `#{}` vs `${}` | 前者**预编译占位符**（防 SQL 注入）；后者字符串拼接（**有注入风险**，仅用于动态表名/排序） |
| 一级缓存 | SqlSession 级，默认开启；**同一 SqlSession 内**生效（与 Spring 集成后事务内有效） |
| 二级缓存 | Mapper/namespace 级，需手动开启；跨 SqlSession；**分布式环境慎用**（脏读） |
| 延迟加载 | `fetchType="lazy"`，按需查询关联对象 |
| 动态 SQL | `<if>` / `<choose>` / `<foreach>` / `<trim>` |
| 分页 | PageHelper（拦截器改写 SQL）或手写 limit |
| Mapper 接口原理 | JDK 动态代理 + MapperProxy |

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与使用说明]] · [[06-MySQL与数据库]] · [[09-分布式与微服务]]

#面试 #Spring #MyBatis #待补
