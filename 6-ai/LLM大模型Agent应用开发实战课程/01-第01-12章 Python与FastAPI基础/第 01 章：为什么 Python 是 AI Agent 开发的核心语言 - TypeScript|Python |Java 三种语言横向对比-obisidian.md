---
title: "第 01 章｜三语言横向对比"
chapter: "01"
source: "第 01 章：为什么 Python 是 AI Agent 开发的核心语言 - TypeScript|Python |Java 三种语言横向对比.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - python
  - typescript
  - java
  - 对比
---

# 第 01 章｜三语言横向对比

> [!abstract] 本章重点
>
> - ==类型写法一一对应== — TS 的 string / number / boolean，在 Python 里就是 str / int / bool，只是换了个名字。
> - ==Python 用 None 统一空值== — TS 里的 null 和 undefined，Python 只有一个 None。
> - ==异步语法几乎同名== — 两边都是 async / await，前端经验可以直接搬过来。
> - ==self 对应 this== — 类里定义方法时，Python 把 self 显式写成第一个参数。
>
> [!note] 大白话
>
> - **Type Hint**：给变量标个类型，主要给人看、给工具检查，运行时默认不管。
> - **snake_case**：Python 习惯下划线命名，JS/TS 习惯小驼峰。
>
> [!info] 导航与来源
> - 原始讲义：`第 01 章：为什么 Python 是 AI Agent 开发的核心语言 - TypeScript|Python |Java 三种语言横向对比.md`
> - [[第 02 章｜Python AI 开发环境搭建|下一章｜第 02 章]]
> - 本章所有内容均保留，未删改原文。

---
| **概念 / 场景** | **TypeScript** | **Python** | **Java** |
| --- | --- | --- | --- |
| **字符串** | `**string**` | `**str**` | `**String**` |
| **整数** | `**number**` | `**int**` | `**int / long**` |
| **小数** | `**number**` | `**float**` | `**float / double**` |
| **布尔值** | `**boolean**` | `**bool**` | `**boolean**` |
| **空值** | `**null**` | `**None**` | `**null**` |
| **未定义** | `**undefined**` | **通常用 **`**None**` | **通常用 **`**null**` |
| **可选值** | `**value?: string**`<br/>** / **`**string | null**` | `**Optional[str]**`<br/>** / **`**str | None**` | `**Optional<String>**`<br/>** / **`**null**` |
| **数组 / 列表** | `**Array<T>**`<br/>** / **`**T[]**` | `**list**`<br/>** / **`**list[T]**` | `**List<T>**`<br/>** / **`**ArrayList<T>**` |
| **对象 / 字典** | `**Object**`<br/>** / **`**Record<K,V>**` | `**dict**` | `**Map<K,V>**` |
| **键值映射** | `**Map<K,V>**` | `**dict[K,V]**` | `**Map<K,V>**` |
| **集合** | `**Set<T>**` | `**set**` | `**Set<T>**` |
| **元组** | `**[string, number]**` | `**tuple**` | **无原生 Tuple，常用 **`**record / class**` |
| **函数定义** | `**function**`<br/>** / **`**=>**` | `**def**` | **方法** |
| **类** | `**class**` | `**class**` | `**class**` |
| **当前对象** | `**this**` | `**self**` | `**this**` |
| **构造函数** | `**constructor()**` | `**__init__()**` | `**ClassName()**` |
| **继承** | `**extends**` | `**class A(B)**` | `**extends**` |
| **接口** | `**interface**` | `**Protocol / ABC**` | `**interface**` |
| **泛型** | `**<T>**` | `**TypeVar / Generic**` | `**<T>**` |
| **异步** | `**async / await**` | `**async / await**` | `**CompletableFuture**`<br/>** / 虚拟线程等** |
| **Promise / Future** | `**Promise<T>**` | `**Future / Coroutine**` | `**Future<T> / CompletableFuture<T>**` |
| **普通 for 循环** | `**for**` | `**for**` | `**for**` |
| **遍历集合** | `**for...of**` | `**for...in**` | `**for...each**` |
| **遍历对象 key** | `**for...in**` | `**for key in dict**` | `**map.keySet()**` |
| **条件判断** | `**if / else**` | `**if / elif / else**` | `**if / else if / else**` |
| **多分支** | `**switch**` | `**match**` | `**switch**` |
| **异常捕获** | `**try / catch / finally**` | `**try / except / finally**` | `**try / catch / finally**` |
| **抛异常** | `**throw**` | `**raise**` | `**throw**` |
| **导入模块** | `**import / export**` | `**import / from**` | `**import**` |
| **包 / 模块** | **npm package / module** | **package / module** | **package / Maven artifact** |
| **访问修饰符** | `**public/private/protected**` | **主要靠约定** | `**public/private/protected**` |
| **常量** | `**const**` | **通常大写变量约定** | `**final**` |
| **枚举** | `**enum**` | `**Enum**` | `**enum**` |
| **Lambda** | `**=>**` | `**lambda**` | `**->**` |
| **类型判断** | `**typeof / instanceof**` | `**type / isinstance**` | `**instanceof**` |
| **字符串模板** | `**`${name}`**` | `**f"{name}"**` | `**"..." + name**`<br/>** / **`**formatted()**` |
| **长度** | `**.length**` | `**len()**` | `**.length / .size()**` |
| **JSON 转对象** | `**JSON.parse()**` | `**json.loads()**` | **Jackson **`**ObjectMapper**` |
| **对象转 JSON** | `**JSON.stringify()**` | `**json.dumps()**` | **Jackson **`**ObjectMapper**` |


#### **重点**
因为 Python 和 JavaScript / TypeScript/Java 有很多思想其实是相通的。

比如：

```markdown
变量
函数
对象
数组
类
异步
Promise / async-await
模块
异常处理
```

**<font style="color:#DF2A3F;">这些概念你都已经学过。只是语法不同。</font>**

**其实对于一个已经会 ****TypeScript 或 Java**** 的程序员来说，学习 Python 并不是重新学习编程，而主要是学习：**

**同一个编程概念，在 Python 里面换了一种写法。**

**比如定义变量。**

```javascript
// TypeScript
const name: string = "大伟";
const age: number = 18;
const enabled: boolean = true;
```

```python
# Python
name: str = "大伟"
age: int = 18
enabled: bool = True
```

```java
// Java
String name = "大伟";
int age = 18;
boolean enabled = true;
```

**定义集合也是一样。**

```typescript
// TypeScript
const users: string[] = ["张三", "李四"];

const user = {
  name: "张三",
  age: 18
};
```

```python
# Python
users: list[str] = ["张三", "李四"]

user = {
    "name": "张三",
    "age": 18
}
```

```java
// Java
List<String> users = List.of("张三", "李四");

Map<String, Object> user = new HashMap<>();
user.put("name", "张三");
user.put("age", 18);
```

**再比如定义函数：**

```typescript
// TypeScript
function add(a: number, b: number): number {
  return a + b;
}
```

```python
# Python
def add(a: int, b: int) -> int:
    return a + b
```

```java
// Java
public int add(int a, int b) {
    return a + b;
}
```

**再比如面向对象：**

```typescript
// TypeScript
class User {
  constructor(public name: string) {}

  sayHello() {
    console.log(this.name);
  }
}
```

```python
# Python
class User:
    def __init__(self, name: str):
        self.name = name

    def say_hello(self):
        print(self.name)
```

```java
// Java
class User {

    private String name;

    public User(String name) {
        this.name = name;
    }

    public void sayHello() {
        System.out.println(this.name);
    }
}
```

#### **重点**
**如果你已经会 JavaScript 或 Java，学 Python 最开始千万不要把它当成一门全新的编程语言。**

**变量、条件判断、循环、函数、类、异常、集合、异步，这些编程思想你全部都学过。**

**真正要适应的就是三件事：**

**第一，语法换了。****  
**`**string**`** 变成 **`**str**`**，**`**null**`** 变成 **`**None**`**，**`**try/catch**`** 变成 **`**try/except**`**。**

**第二，Python 更动态。  
****Java 和 TypeScript 比较强调类型，而 Python  JavaScript很多地方类型可以省略。**

**第三，生态换了。  
****前端以前学 npm  pnpm、React、NestJS，**

**Java 学 Maven、Spring Boot**

**现在 Python 主要学习 **`**pip/uv**`**、FastAPI、Pydantic、 LangChain、LangGraph。**

**所以对于有开发经验的人来说，Python 语法根本不是转 AI 最大的门槛，真正的重点应该放在 AI 应用开发生态上。**

**不是在重新学 Python，把原来的编程能力迁移到 AI Agent 开发。**

---

> [!success] 一句话带走
> ==三种语言不是三套思维，只是同一套编程概念的三种写法。==

> [!quote] 关于本文档
> 由原始讲义 `第 01 章：为什么 Python 是 AI Agent 开发的核心语言 - TypeScript|Python |Java 三种语言横向对比.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
