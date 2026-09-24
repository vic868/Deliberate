---
title: 01-Java基础与集合
tags: [面试, Java, 技术题库, 基础, 集合]
status: 进行中
---

# ☕ 01 · Java 基础与集合

> 返回 [[00-总览与使用说明]]

---

## 一、语言基础

| 问题                                    | 得分骨架                                                                                          |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| 双等号与 `equals` 的区别                     | 双等号（写法 `a == b`）比引用 / 基本类型值；`equals` 默认也是比较引用，被 String / 包装类重写为比值；**重写 equals 必须重写 hashCode** |
| 为什么重写 equals 要重写 hashCode             | HashMap/HashSet 先用 hashCode 定位桶，再用 equals 比较；只重写 equals 会导致两个"相等"对象落在不同桶 → 去重失效               |
| hashCode 契约                           | 相等对象 hashCode 必须相同；不相等对象 hashCode 尽量不同（哈希冲突影响性能）                                              |
| String 为什么不可变                         | `final class` + `private final char[]`（JDK9 后 `byte[]`）；好处：常量池复用、线程安全、hashCode 可缓存            |
| 字符串常量池 / intern                       | 字面量直接入池；`new String("a")` 创建 2 个对象（堆 + 池）；`intern()` 返回池中引用；JDK7 后池移到堆                        |
| String / StringBuilder / StringBuffer | 不可变 / 可变非线程安全 / 可变线程安全（synchronized）；循环拼接用 StringBuilder                                      |
| final / finally / finalize            | 修饰符 / 必执行代码块 / 对象回收前调用（已废弃，别用）                                                                |
| 重载 vs 重写                              | 编译期 vs 运行期；重写规则：两同两小一大（方法名参数同、返回值和异常更小、访问权限更大）                                                |
| 泛型擦除                                  | 编译后擦成 Object/上界；所以不能 `new T[]`、不能对泛型做 `instanceof`、静态方法不能用类泛型                                 |
| 深拷贝 vs 浅拷贝                            | 浅拷贝共享引用对象；深拷贝递归复制（序列化 / 手写 clone / 拷贝构造）                                                      |
| 自动装箱与缓存                               | `Integer.valueOf` 缓存 **-128~127**；`Integer a=127,b=127` 相等，128 不等                             |
| 异常体系                                  | Throwable → Error / Exception；受检 vs 非受检；`finally` 中 return 会吞掉异常                              |
| 接口 vs 抽象类                             | 多实现 vs 单继承；JDK8 后接口可有 default/static 方法                                                       |
| JDK 8 新特性                             | Lambda、Stream、Optional、函数式接口、`default` 方法、新日期 API、Metaspace 替代永久代                             |
| Stream 惰性求值                           | 中间操作惰性、终止操作触发；`map` vs `flatMap`；并行流用 ForkJoinPool（**注意线程池污染**）                               |
| Optional                              | 避免 NPE；`orElse` vs `orElseGet`（后者惰性）；别用 `get()`                                               |

---

## 二、集合框架

| 问题 | 得分骨架 |
|---|---|
| ArrayList vs LinkedList | 数组（随机访问 O(1)、增删 O(n)）vs 双向链表（增删 O(1)、访问 O(n)）；**实际几乎都用 ArrayList**（CPU 缓存友好） |
| ArrayList 扩容 | 默认 10；`grow` 为 `old + (old>>1)` 即 1.5 倍；`Arrays.copyOf`；建议预设容量 |
| **HashMap 底层** `#高频` | 数组 + 链表 + 红黑树；初始 16、负载因子 0.75、扩容 2 倍；**树化阈值 8、退化 6**（避免频繁转换）；hash 扰动 `h ^ (h>>>16)`；1.7 头插并发扩容成环，1.8 改尾插但仍非线程安全 |
| HashMap 容量为什么是 2 的幂 | 用 `(n-1) & hash` 代替取模，位运算快且分布均匀；扩容时元素要么原位要么 `原索引+oldCap` |
| HashMap 为什么树化阈值是 8 | 泊松分布下链表长度到 8 的概率约千万分之六，兼顾查询与转换成本 |
| HashMap 线程安全替代 | `ConcurrentHashMap`（推荐）/ `Collections.synchronizedMap`（全表锁，差） |
| LinkedHashMap 实现 LRU | 构造 `accessOrder=true` + 重写 `removeEldestEntry`；底层额外双向链表维护顺序 |
| TreeMap | 红黑树，按 key 排序；`Comparable` / `Comparator`；`subMap`/`headMap` 范围查询 |
| HashSet 原理 | 内部就是 HashMap，value 是同一个 `PRESENT` 对象 |
| fail-fast vs fail-safe | 前者遍历时检测 `modCount` 抛 `ConcurrentModificationException`（ArrayList/HashMap）；后者遍历副本（CopyOnWriteArrayList/ConcurrentHashMap） |
| CopyOnWriteArrayList | 写时复制、读无锁；**适合读多写极少**；写开销大、内存翻倍、数据非实时 |
| Iterator 与 for-each | for-each 底层是 Iterator；遍历中删除要用 `iterator.remove()` |

---

## 三、易错点 `#易错`

- `Arrays.asList()` 返回**固定长度**视图，`add` 会抛异常；且与原数组共享
- `List.subList()` 返回**视图**，原 list 结构改动会导致 `ConcurrentModificationException`
- `HashMap` 允许一个 null key、多个 null value；`Hashtable`/`ConcurrentHashMap` 不允许 null
- `String s = "a" + "b"` 编译期就优化成 `"ab"`；但循环内 `+=` 会不断创建对象
- `switch` 支持 String 是 JDK7+；本质是先 hashCode 再 equals
- `try-finally` 中 `finally` 里 return/抛异常会覆盖 try 的返回值

---

## 📥 待补充

- 

## 🔗 关联

- [[00-总览与使用说明]] · [[02-并发与多线程]] · [[12-String专题思维导图]]

#面试 #Java基础 #集合 #待补
