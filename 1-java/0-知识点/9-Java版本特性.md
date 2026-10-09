---
title: Java 版本特性（8 → 25）
tags: [Java, 版本, 新特性, Lambda]
status: 进行中
created: 2026-10-09
---

# 🚀 十一、Java 版本特性

> 本篇回答：Java 8 到底带来了什么（为什么它是面试默认基线）、9 到 25 各版本有哪些**真正影响工程**的特性、以及虚拟线程为什么是并发模型的分水岭。
> 关联：[[0-Java总览]]（版本速览表）、[[5-线程池]]（虚拟线程）、[[1-集合框架]]（不可变集合）、[[1-JVM内存区域与对象布局]]（Metaspace 与 GC 演进）。

---

## 一、Java 8：最重要的一次升级

Java 8 是**存量项目的基线**，也是面试默认假设的版本。核心是四个字：**函数式编程**。

### 1.1 Lambda 与函数式接口

```java
// 从匿名内部类到 Lambda
Runnable r1 = new Runnable() { public void run() { System.out.println("old"); } };
Runnable r2 = () -> System.out.println("new");

// 函数式接口：只有一个抽象方法的接口（可用 @FunctionalInterface 标注）
@FunctionalInterface
interface Calculator { int calc(int a, int b); }
Calculator add = (a, b) -> a + b;
```

| 要点 | 说明 |
|---|---|
| 前提 | 必须是**函数式接口**（只有一个抽象方法） |
| 类型推断 | 参数类型可省略；返回值单表达式时可省略 `return` |
| `this` 指向 | Lambda 的 `this` 指向**外围实例**（匿名内部类指向自身）——这是两者的关键差异 |
| 字节码 | Lambda 用 **`invokedynamic` + `LambdaMetafactory`**，不为每个 Lambda 生成一个类（匿名内部类会生成 `Outer$1.class`） |
| 变量捕获 | 只能捕获 **effectively final** 的局部变量（值被拷贝进 Lambda） |

> [!important] 为什么局部变量必须 effectively final
> Lambda 捕获的是**变量的副本**（存在栈上/Lambda 对象里），如果允许后续修改，Lambda 里的值与外部就会不一致。
> **成员变量不受此限制**（因为 `this` 可用，访问的是堆上的字段）。

### 1.2 内置函数式接口（必背）

| 接口 | 签名 | 用途 |
|---|---|---|
| `Function<T,R>` | `R apply(T)` | 转换 |
| `Consumer<T>` | `void accept(T)` | 消费（无返回） |
| `Supplier<T>` | `T get()` | 供给（无输入） |
| `Predicate<T>` | `boolean test(T)` | 判断 |
| `BiFunction<T,U,R>` | `R apply(T,U)` | 双入参转换 |
| `UnaryOperator<T>` / `BinaryOperator<T>` | 同类型进出的 `Function` | 累加、归约 |

（另有大量基本类型特化版本如 `IntFunction`、`ToIntFunction`，**用特化版本可以避免装箱**。）

### 1.3 Stream

```java
// 一段典型的流式处理
Map<String, Integer> top = orders.stream()
    .filter(o -> o.getAmount().compareTo(BigDecimal.ZERO) > 0)   // 中间操作（惰性）
    .sorted(Comparator.comparing(Order::getAmount).reversed())
    .limit(10)
    .collect(Collectors.toMap(Order::getUserId, o -> 1, Integer::sum));  // 终端操作（触发执行）
```

| 概念 | 要点 |
|---|---|
| **惰性求值** | 中间操作（`filter`/`map`/`sorted`）不执行，**只有终端操作（`collect`/`forEach`/`count`）才触发** |
| **一次性** | Stream 只能消费一次，复用会抛 `IllegalStateException` |
| **并行流** | `parallelStream()` 底层用 **`ForkJoinPool.commonPool`**；**若 commonPool 被阻塞任务占满，并行流会受影响**（见 [[5-线程池]]） |
| **短路操作** | `findFirst`/`anyMatch`/`limit` 可提前结束（对无限流很重要） |
| **`Collectors`** | `toMap`（**key 重复会抛异常，必须给合并函数**）、`groupingBy`、`joining`、`partitioningBy`、`teeing` |
| **`map` vs `flatMap`** | 一对一 vs **一对多并扁平化** |
| **`reduce`** | 归约；注意**并行流下必须有结合律**，否则结果错误 |
| **基本类型流** | `IntStream`/`LongStream`/`DoubleStream` 避免装箱 |

> [!warning] Stream 的三个性能陷阱
> ① **`boxed()`/基本类型混用**导致大量装箱；
> ② **并行流用在 IO 或数据量小时反而更慢**（线程调度与合并开销 > 收益）；
> ③ **`Collectors.toMap` 未给合并函数**在 key 重复时直接抛 `IllegalStateException`。

### 1.4 Optional

```java
// 优雅地处理可能为空的链路
String city = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("UNKNOWN");
```

| 方法 | 说明 |
|---|---|
| `of` / `ofNullable` / `empty` | 创建（**`of(null)` 会抛 NPE**） |
| `map` / `flatMap` | 转换（`flatMap` 用于返回 `Optional` 的场景） |
| `orElse` / `orElseGet` / `orElseThrow` | **`orElse` 无论是否为空都会计算参数**（有副作用或昂贵时要改用 `orElseGet`） |
| `ifPresent` / `ifPresentOrElse` | 存在则消费 |
| `filter` | 条件过滤 |

> [!note] Optional 的正确用法
> **它是"返回值"的容器，不是字段/参数类型**——把字段声明成 `Optional` 会增加内存与序列化麻烦，属于误用。

### 1.5 接口默认方法与静态方法

```java
public interface OrderService {
    void create(Order o);
    default boolean isValid(Order o) { return o != null && o.getId() != null; }  // 默认实现
    static OrderService noop() { return o -> {}; }                               // 静态方法
}
```

**目的**：让接口可以**演进**（新增方法而不破坏已有实现类），也是 Stream/集合 API 能大规模扩展的基础。

**菱形冲突规则**：若多个接口提供同签名默认方法 → ① 类中重写优先；② 否则**子接口更具体者优先**；③ 仍冲突则**必须显式重写**并可用 `Interface.super.method()` 指定。

### 1.6 其它重要变化

| 特性 | 说明 |
|---|---|
| **`Metaspace` 取代永久代** | 方法区移到本地内存，见 [[1-JVM内存区域与对象布局]] |
| **`HashMap` 引入红黑树** | 链表长度 ≥ 8 且容量 ≥ 64 时树化，见 [[1-集合框架]] |
| **`CompletableFuture`** | 真正的异步编排能力（`Future` 只能阻塞 `get`），见 [[6-JUC并发工具]] |
| **`LongAdder`** | 高并发计数替代 `AtomicLong` |
| **新的日期时间 API** | `LocalDate`/`LocalDateTime`/`Duration`/`DateTimeFormatter`，**不可变且线程安全**，取代 `SimpleDateFormat`（**后者线程不安全**） |
| **`Base64`** | 标准库内置，不再依赖第三方 |
| **PermGen 参数失效** | `-XX:PermSize` 等不再有效 |

> [!tip] `SimpleDateFormat` 线程不安全的替代方案
> ① 每次方法内新建（可接受但浪费）；② 用 `ThreadLocal<SimpleDateFormat>`；③ **首选 `DateTimeFormatter`（Java 8+ 不可变、线程安全）**。

---

## 二、Java 9 → 25：真正影响工程的特性

> 版本节奏：Java 9 之后改为**每 6 个月一个特性版本**，每 2 年（后改为 2 年一轮）出一个 **LTS**。主流 LTS：**11、17、21、25**。

### 2.1 按版本速览

| 版本 | 真正值得记的特性 | 工程影响 |
|---|---|---|
| **9** | **模块系统 JPMS**；`List.of`/`Map.of` 不可变集合工厂；接口私有方法；**G1 成为默认 GC**；`Optional.ifPresentOrElse` | 模块化带来**反射强封装**的麻烦；不可变集合成为首选 |
| **10** | `var` 局部变量类型推断；**容器感知（`UseContainerSupport`）** | 容器里 JVM 终于能正确识别 limit |
| **11 (LTS)** | `HttpClient` 标准化；`String` 新增 `isBlank`/`lines`/`strip`/`repeat`；**单个 `.java` 文件直接运行**（`java Foo.java`）；ZGC 实验性 | 日常工具方法大幅丰富 |
| **12~15** | `switch` 表达式（12 预览/14 标准）；**文本块 Text Blocks**（15 标准）；`instanceof` 模式匹配（16 标准）；**Records**（14 预览/16 标准）；`NullPointerException` 增强提示（14）；**偏向锁废弃**（15） | 写 POJO 与多行字符串的方式改变 |
| **16** | Records 标准；`instanceof` 模式匹配标准；`Stream.toList()`；强封装 JDK 内部 API（**默认生效**） | 反射访问 JDK 内部会报错，升级要留意 |
| **17 (LTS)** | **密封类 sealed**（标准）；switch 模式匹配（预览）；移除 SecurityManager（弃用）；**Spring Boot 3.x 的最低要求** | 承上启下的企业基线 |
| **18~20** | 简单 Web 服务器；`@snippet` 文档；**虚拟线程预览**（19/20）；结构化并发预览；Scoped Values 预览 | 为 21 的并发变革铺路 |
| **21 (LTS)** | **虚拟线程正式**；**记录模式**；**switch 模式匹配正式**；**分代 ZGC**；`SequencedCollection` 接口；结构化并发/Scoped Values 仍预览 | **当前主流 LTS**，并发模型分水岭 |
| **22~24** | 未命名变量 `_`；构造器前序语句；**字符串模板（预览后调整）**；模式匹配继续演进；ZGC 持续优化 | 语言表达力继续收敛 |
| **25 (LTS)** | 最新 LTS，继续打磨虚拟线程/结构化并发/模式匹配等 | 新项目选型的新基线 |

> [!warning] 别把"预览特性"当稳定特性
> 预览（Preview）特性需要加 `--enable-preview` 才能编译运行，**且可能在下个版本变更或移除**。生产选型只应依赖**已正式（Standard）**的特性。

### 2.2 `var`（Java 10）

```java
var list = new ArrayList<String>();   // 推断为 ArrayList<String>
// var x;         ❌ 必须有初始值
// var f = a -> a+1;   ❌ Lambda 无法推断
```

| 要点 | 说明 |
|---|---|
| 只用于**局部变量** | 不能用于字段、方法参数、返回值 |
| 是**编译期推断** | 与 JS 的动态类型完全不同，运行时类型确定 |
| 是否用 | 类型显而易见时提升可读性；**类型不明显时反而降低可读性**（如 `var r = service.call()`） |

### 2.3 文本块（Java 15）

```java
String sql = """
        SELECT id, name
        FROM users
        WHERE status = ?
        """;
```

自动处理换行与缩进（按最小缩进裁剪），适合 SQL/JSON/HTML。

### 2.4 Records（Java 16）

```java
public record OrderDTO(Long id, String userId, BigDecimal amount) {}

// 等价于：final 类 + 全参构造 + 访问器 id()/userId()/amount()
//        + equals/hashCode/toString
```

| 要点 | 说明 |
|---|---|
| 本质 | **不可变的"数据载体"**（字段 final、无 setter） |
| 适合 | DTO、值对象、多返回值、Map 的复合 key |
| 不适合 | 需要可变状态、需要继承（record 不能继承类） |
| 注意 | 访问器是 `id()` **而不是 `getId()`** → 某些序列化框架/MyBatis 需要额外配置 |

### 2.5 模式匹配与密封类（Java 16/17/21）

```java
// instanceof 模式匹配（16 正式）
if (obj instanceof Order o && o.getAmount().signum() > 0) { ... }

// 密封类（17 正式）：限制谁能继承
public sealed interface Shape permits Circle, Rect {}
public record Circle(double r) implements Shape {}
public record Rect(double w, double h) implements Shape {}

// switch 模式匹配（21 正式）—— 配合 record 做"代数数据类型"式分支
double area = switch (shape) {
    case Circle c -> Math.PI * c.r() * c.r();
    case Rect r   -> r.w() * r.h();
};   // 密封 + 穷尽性检查：编译器能验证你漏了哪个分支
```

> [!tip] 这套组合的价值
> **密封类 + record + switch 模式匹配**让 Java 能表达"**受控的代数数据类型**"，把原本靠 `instanceof` 链或访问者模式做的事写得更安全（**穷尽性检查**）。

### 2.6 集合新 API

| 特性 | 版本 | 说明 |
|---|---|---|
| `List.of` / `Set.of` / `Map.of` | 9 | **不可变**集合工厂（**不接受 null，`add` 抛异常**） |
| `copyOf` | 10 | 创建不可变副本 |
| `Stream.toList()` | 16 | 比 `collect(Collectors.toList())` 更简洁，**返回不可变列表** |
| `SequencedCollection` | 21 | `List`/`Deque` 统一了 `getFirst`/`getLast`/`reversed` |

---

## 三、虚拟线程（Java 21 正式）

### 3.1 它解决什么问题

传统 `Thread` 是**平台线程**，与操作系统线程**1:1** 绑定。一个平台线程约 1MB 栈，几千个就吃光内存，且**线程切换由内核调度、成本高**。
于是高并发 IO 场景只能靠"**线程池 + 异步回调/响应式**"，代价是**代码复杂、难调试、上下文传递困难**。

> **虚拟线程**由 JVM 调度，大量虚拟线程**复用少量平台线程（载体线程 carrier）**；当虚拟线程阻塞在 IO 上时，JVM 会把它**卸载**，让载体线程去跑别的虚拟线程。

### 3.2 关键结论

| 要点 | 说明 |
|---|---|
| 创建 | `Thread.ofVirtual().start(runnable)` 或 `Executors.newVirtualThreadPerTaskExecutor()` |
| **不要池化** | 虚拟线程**很廉价**，池化反而阻碍其扩展；应该"**一个任务一个虚拟线程**" |
| 适用 | **高并发 IO 密集**（HTTP 调用、DB 访问、消息收发） |
| 不适用 | **CPU 密集**（不会更快，仍受核数限制） |
| 阻塞的坑 | **`synchronized` 阻塞会钉住（pin）载体线程**，使扩展性下降；应改用 `ReentrantLock`（这是官方明确指出的迁移点） |
| 线程本地 | `ThreadLocal` 在虚拟线程数量巨大时开销显著 → 关注 **Scoped Values**（预览） |
| 生态适配 | 连接池、`ThreadLocal` 缓存、`synchronized` 老代码都可能成为瓶颈 |

> [!important] 面试答题口径
> **虚拟线程不是"更快的线程"，而是"更便宜的线程"**——它把"高并发 IO"从"异步回调/响应式"带回**同步阻塞式写法**，同时保持高吞吐。
> 对 CPU 密集型任务**没有收益**；对依赖 `synchronized` 或大量 `ThreadLocal` 的存量代码**需要适配**。

### 3.3 结构化并发（预览）

把"一个任务派生出的多个子任务"当成一个整体：**要么全部成功，要么全部取消**，并保证子任务不会逃逸出作用域（避免线程泄漏与取消遗漏）。
它解决的是虚拟线程大规模使用后的**生命周期管理**问题。**注意：截至 Java 21 仍为预览特性。**

---

## 四、升级到新版本要留意什么

| 风险点 | 说明 | 应对 |
|---|---|---|
| **反射强封装** | Java 16 起默认强封装 JDK 内部 API（Java 17 更彻底） | 依赖 `--add-opens`/`--add-exports`（**这是升级报错最常见的原因**） |
| **移除/废弃的 API** | 如 CMS 收集器在 14 被移除、SecurityManager 弃用、部分 JDK 内部类不可访问 | 升级前查废弃清单 |
| **依赖与框架兼容** | Spring Boot 3.x 要求 Java 17+；老版本 CGLIB/ASM 可能不识别新字节码 | 对齐框架与构建插件版本 |
| **第三方库的字节码增强** | Lombok、Mockito、ByteBuddy 等需要支持新版本 | 升级到兼容版本 |
| **GC 默认值变化** | 默认收集器随版本变化（9 起 G1） | 显式指定收集器，避免"升级后 GC 行为变了" |
| **容器内存** | 老 JDK 不感知容器 limit | 选 JDK 10+ 或显式设 `-Xmx` |

> [!tip] 稳妥的升级顺序
> ① 先升级**构建工具与依赖**（保证能编译）→ ② 在**测试环境**跑完整回归 + 压测（看 GC/延迟变化）→ ③ 用 **`jdeps`/`jdeprscan`** 扫描废弃 API 与模块依赖 → ④ 灰度发布 → ⑤ 观察 GC 日志与错误率。

---

## 五、本篇必答

> [!question] 面试官可能这样问
> **Q：Java 8 有哪些重要特性？**
> A：**Lambda 与函数式接口、Stream API、Optional、接口默认/静态方法、新的日期时间 API、`CompletableFuture`、`Metaspace` 取代永久代、`HashMap` 引入红黑树、`LongAdder`**。其中最核心的是**函数式编程能力**，它改变了集合处理与异步编排的写法。
>
> **Q：Lambda 和匿名内部类有什么区别？**
> A：① **`this` 指向不同**（Lambda 指外围实例，匿名类指自身）；② Lambda 经 **`invokedynamic`** 动态生成，不会为每个 Lambda 产生 `class` 文件，而匿名内部类会生成 `Outer$1.class`；③ Lambda 只能用于函数式接口。
>
> **Q：Stream 的中间操作和终端操作有什么区别？**
> A：**中间操作是惰性的**（`filter`/`map`/`sorted` 只记录流水线），**只有终端操作（`collect`/`forEach`/`count`）才真正触发执行**；Stream 只能消费一次。并行流的底层是 `ForkJoinPool.commonPool`，所以**被阻塞任务占满时并行流会受影响**。
>
> **Q：`orElse` 和 `orElseGet` 有什么区别？**
> A：**`orElse(T)` 无论 Optional 是否为空都会先求值参数**（若参数是方法调用会有副作用或性能开销）；`orElseGet(Supplier)` 只在为空时才调用。所以**需要惰性求值时用 `orElseGet`**。
>
> **Q：虚拟线程是什么？什么时候用？**
> A：Java 21 正式特性。由 **JVM 调度**、大量复用平台线程（载体线程），在 IO 阻塞时**卸载**虚拟线程。适合**高并发 IO 密集**场景，**不要池化**；对 CPU 密集无收益。注意 **`synchronized` 会 pin 住载体线程**（改用 `ReentrantLock`），且大量 `ThreadLocal` 会有开销。

---
> 回到 → [[0-Java总览]] ｜ 并发深入 → [[5-线程池]]、[[4-多线程与内存模型]] ｜ JVM → [[1-JVM内存区域与对象布局]]
