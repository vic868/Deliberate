---
title: "第 05 章｜Python 异步编程 async / await"
chapter: "05"
source: "第 05 章｜Python 异步编程 async ｜ await.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - python
  - async
  - asyncio
---

# 第 05 章｜Python 异步编程 async / await

> [!abstract] 本章重点
>
> - ==调用 async 函数却不 await，拿到的是 coroutine== — 函数体根本没执行，只是拿到一张「待办条」。
> - ==await 只能写在 async 函数里== — 普通函数里写 await 直接语法错误。
> - ==asyncio.gather 并发跑多个任务== — 批量等大模型返回时，总耗时约等于最慢的那一个。
> - ==create_task 提前启动，gather 统一收结果== — 想让任务先跑起来、后面再收，就用 create_task。
> - ==事件循环是调度员== — 谁在等 I/O 就先让出，CPU 不空等。
>
> [!note] 大白话
>
> - **协程 coroutine**：一个可以中途暂停、等会儿再继续的函数。
> - **I/O 密集**：时间主要花在等网络或磁盘，不是在算 CPU。
>
> [!info] 导航与来源
> - 原始讲义：[[第 05 章｜Python 异步编程 async ｜ await|打开原始讲义]]
> - [[第 04 章｜Python 类型系统与 Pydantic 深入|上一章｜第 04 章]]
> - [[第 06 章｜FastAPI 快速入门|下一章｜第 06 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#async / await 异步编程]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#async / await 异步编程]]
- [[#五、02｜创建本章代码目录]]
- [[#六、03｜先看同步阻塞代码]]
- [[#七、04｜第一个 async 函数]]
- [[#八、05｜和 JavaScript async / await 对比]]
- [[#九、06｜什么是事件循环 Event Loop]]
- [[#十、07｜常见错误：调用 async 函数但没有 await]]
- [[#十一、08｜正确执行 coroutine]]
- [[#十二、09｜常见错误：await 写在普通函数里]]

---
已经掌握 Python 基础语法、Type Hint、Pydantic，准备进入 FastAPI、LLM、RAG、Agent 开发的学员。

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面几章我们已经完成了：

```text
第 02 章：Python AI 开发环境搭建
第 03 章：Python AI 开发快速入门
第 04 章：Python 类型系统与 Pydantic 深入
```

这一章我们进入 Python 后端开发里非常重要的一块：

## async / await 异步编程
==为什么 AI 开发必须单独讲异步？==

因为 AI 应用天然就是 IO 密集型系统。

后面我们会频繁调用：

```text
LLM API
Embedding API
Rerank API
数据库
Redis
向量数据库
外部业务系统
MCP Server
第三方 Tool
```

这些操作都有一个共同特点：

**不是 CPU 在疯狂计算，而是在等待网络、数据库、模型服务返回结果。**

如果每一步都同步等待，系统会非常慢。

比如一个 Agent 回答用户问题时，可能需要同时做：

```text
查询用户信息
查询订单信息
查询物流信息
检索知识库
调用大模型
```

如果每一步都串行：

```text
1 秒 + 1 秒 + 1 秒 + 1 秒 + 2 秒 = 6 秒
```

如果可以并发：

```text
max(1 秒, 1 秒, 1 秒, 1 秒, 2 秒) ≈ 2 秒
```

这就是异步编程在 AI Agent 项目里的价值。

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. 同步和异步到底有什么区别
2. 什么是阻塞 IO
3. 什么是事件循环 Event Loop
4. async def 是什么
5. await 是什么
6. asyncio.run 怎么用
7. coroutine 协程是什么
8. asyncio.gather 如何并发执行多个任务
9. asyncio.create_task 如何提前创建任务
10. async for 如何处理异步数据流
11. async generator 如何模拟 LLM 流式输出
12. async with 如何管理异步资源
13. asyncio.wait_for 如何做超时控制
14. asyncio.Semaphore 如何做并发限流
15. 如何处理异步任务异常
16. 如何模拟 Agent 并发调用多个 Tool
17. 如何模拟 LLM 流式输出
18. async / await 和 FastAPI、LLM、RAG、Agent 的关系
```

---

## 三、本章最终项目结构
本章继续使用前面的项目：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas/
│   └── async_demo/
│       ├── __init__.py
│       ├── 01_sync_blocking.py
│       ├── 02_async_basic.py
│       ├── 03_coroutine.py
│       ├── 04_gather.py
│       ├── 05_create_task.py
│       ├── 06_exceptions.py
│       ├── 07_timeout.py
│       ├── 08_semaphore.py
│       ├── 09_async_generator.py
│       ├── 10_async_context.py
│       ├── 11_llm_stream.py
│       ├── 12_agent_tools.py
│       └── 13_fastapi_preview.py
│
├── tests/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

本章所有异步相关练习都放在：

```text
app/async_demo/
```

里面。

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 05 章。

这一章我们要讲 Python 里面非常重要的一个知识点：

## async / await 异步编程
如果你是前端开发者，对 async / await 应该不陌生。

在 JavaScript 里面，我们经常写：

```typescript
async function fetchData() {
  const result = await request();
  return result;
}
```

Python 里面也有类似写法：

```python
async def fetch_data():
    result = await request()
    return result
```

==所以从概念上来说，Python 的 async / await 对前端开发者并不陌生。==

但是 Python 的异步编程有几个自己的特点。

比如：

```text
asyncio.run
asyncio.gather
asyncio.create_task
async for
async with
async generator
```

这些都是后面做 AI 应用非常常见的写法。

尤其是 AI Agent 项目里面，我们经常需要：

```text
并发调用多个 Tool
并发检索多个知识库
控制 LLM 超时时间
处理流式输出
限制并发数量
处理异步异常
```

所以这一章非常重要。

大家不要把它理解成普通 Python 语法。

这一章真正要解决的是：

**以后我们怎么用 Python 写高性能 AI 后端。**

---

## 五、02｜创建本章代码目录
### 【实操】
进入项目根目录：

```bash
cd ai-agent-course
```

创建目录：

```bash
mkdir -p app/async_demo
```

Windows PowerShell：

```powershell
mkdir app\async_demo
```

创建初始化文件：

```bash
touch app/async_demo/__init__.py
```

Windows PowerShell：

```powershell
New-Item app\async_demo\__init__.py
```

---

### 【重点内容】
这一章我们新建一个：

```text
app/async_demo
```

目录。

所有异步编程的示例都放在这里。

后面我们会从最简单的同步阻塞开始，一步一步升级到：

```text
async def
await
gather
create_task
async generator
async with
timeout
semaphore
Agent 并发 Tool
LLM 流式输出
```

这样大家会非常清楚：

**异步编程到底是为了解决什么问题。**

---

## 六、03｜先看同步阻塞代码
### 【创建文件】
新建：

```text
app/async_demo/01_sync_blocking.py
```

写入代码：

```python
import time


def query_user():
    print("开始查询用户信息")
    time.sleep(1)
    print("用户信息查询完成")
    return "用户信息"


def query_order():
    print("开始查询订单信息")
    time.sleep(1)
    print("订单信息查询完成")
    return "订单信息"


def query_llm():
    print("开始调用大模型")
    time.sleep(2)
    print("大模型返回结果")
    return "AI 回答"


def main():
    start = time.perf_counter()

    user = query_user()
    order = query_order()
    answer = query_llm()

    end = time.perf_counter()

    print(user)
    print(order)
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


main()
```

运行：

```bash
python app/async_demo/01_sync_blocking.py
```

输出类似：

```text
开始查询用户信息
用户信息查询完成
开始查询订单信息
订单信息查询完成
开始调用大模型
大模型返回结果
用户信息
订单信息
AI 回答
总耗时：4.00 秒
```

---

### 【重点内容】
我们先写一个同步代码。

这里有三个函数：

```python
query_user()
query_order()
query_llm()
```

分别模拟：

```text
查询用户信息：1 秒
查询订单信息：1 秒
调用大模型：2 秒
```

==因为我们现在是同步执行，所以执行顺序是：==

```text
先查用户
再查订单
再调用大模型
```

总耗时大约：

```text
1 + 1 + 2 = 4 秒
```

这个就是同步阻塞。

同步阻塞不是不能用。

如果任务非常简单，它完全可以。

但是 AI Agent 项目经常不是这样。

比如用户问：

```text
帮我查询订单 10001，并根据售后政策判断能不能退货。
```

系统可能要同时：

```text
查订单
查物流
查商品
查售后知识库
调用大模型
```

如果每一步都串行，用户体验会很差。

所以我们需要异步。

---

## 七、04｜第一个 async 函数
### 【创建文件】
新建：

```text
app/async_demo/02_async_basic.py
```

写入：

```python
import asyncio


async def query_user():
    print("开始查询用户信息")
    await asyncio.sleep(1)
    print("用户信息查询完成")
    return "用户信息"


async def main():
    result = await query_user()
    print(result)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/02_async_basic.py
```

输出：

```text
开始查询用户信息
用户信息查询完成
用户信息
```

---

### 【重点内容】
现在我们写了第一个异步函数。

Python 里面定义异步函数使用：

```python
async def
```

比如：

```python
async def query_user():
```

这里：

```python
await asyncio.sleep(1)
```

表示异步等待 1 秒。

注意：

```python
asyncio.sleep(1)
```

不是普通的：

```python
time.sleep(1)
```

`time.sleep` 会阻塞整个线程。

`asyncio.sleep` 是异步等待，它会把控制权交回事件循环，让事件循环可以去执行别的任务。

==这就是异步和同步最大的区别之一。==

---

## 八、05｜和 JavaScript async / await 对比
### 【重点内容】
如果你是前端开发者，可以这样理解。

JavaScript：

```typescript
async function queryUser() {
  await sleep(1000);
  return "用户信息";
}

async function main() {
  const result = await queryUser();
  console.log(result);
}

main();
```

Python：

```python
async def query_user():
    await asyncio.sleep(1)
    return "用户信息"


async def main():
    result = await query_user()
    print(result)


asyncio.run(main())
```

你会发现核心思想非常像。

只是 Python 有一个：

```python
asyncio.run(main())
```

这是用来启动整个异步程序的。

在 JavaScript 里面，Node.js 或浏览器已经天然有事件循环。

在 Python 脚本里面，需要我们用：

```python
asyncio.run()
```

来启动事件循环。

---

## 九、06｜什么是事件循环 Event Loop
### 【重点内容】
这里我们简单讲一下事件循环。

大家不要一听事件循环就觉得很抽象。

可以先这样理解：

```text
事件循环
=
一个不断调度异步任务的调度器
```

它的工作大概是：

```text
任务 A 开始执行
任务 A 遇到 await，开始等待网络返回
事件循环切换去执行任务 B
任务 B 遇到 await，开始等待数据库返回
事件循环切换去执行任务 C
任务 A 网络返回了
事件循环回来继续执行任务 A
```

==所以异步编程的核心不是：==

**让一个任务变快。**

而是：

**在一个任务等待的时候，不要让整个程序闲着。**

比如：

```text
等待 LLM 返回
等待数据库返回
等待 Redis 返回
等待 Tool 返回
```

这些等待期间，事件循环可以去做别的任务。

这就是异步编程提高吞吐能力的原因。

---

## 十、07｜常见错误：调用 async 函数但没有 await

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

### 【创建文件】
新建：

```text
app/async_demo/03_coroutine.py
```

写入：

```python
import asyncio


async def query_user():
    return "用户信息"


result = query_user()

print(result)
```

运行：

```bash
python app/async_demo/03_coroutine.py
```

你会看到类似：

```text
<coroutine object query_user at 0x...>
```

并且可能有警告：

```text
RuntimeWarning: coroutine 'query_user' was never awaited
```

---

### 【重点内容】
这里是新手非常容易踩的坑。

我们调用：

```python
query_user()
```

并没有真正拿到：

```text
用户信息
```

而是拿到了一个：

```text
coroutine object
```

也就是协程对象。

为什么？

因为：

```python
async def query_user()
```

定义的是异步函数。

调用异步函数时，不会马上执行完整逻辑，而是返回一个协程对象。

你必须：

```python
await query_user()
```

或者交给事件循环执行。

---

## 十一、08｜正确执行 coroutine
修改：

```text
app/async_demo/03_coroutine.py
```

代码：

```python
import asyncio


async def query_user():
    return "用户信息"


async def main():
    result = await query_user()
    print(result)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/03_coroutine.py
```

输出：

```text
用户信息
```

---

### 【重点内容】
正确方式是：

```python
async def main():
    result = await query_user()
```

然后：

```python
asyncio.run(main())
```

大家记住一句话：

**async 函数调用之后得到 coroutine，必须 await 才会真正执行并拿到结果。**

---

## 十二、09｜常见错误：await 写在普通函数里

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

继续写一个错误示例：

```python
import asyncio


async def query_user():
    return "用户信息"


def main():
    result = await query_user()
    print(result)


main()
```

运行会报错：

```text
SyntaxError: 'await' outside async function
```

---

### 【重点内容】
这个错误也非常常见。

Python 里面：

```python
await
```

只能写在：

```python
async def
```

函数里面。

所以普通函数：

```python
def main():
```

里面不能直接写：

```python
await
```

正确写法：

```python
async def main():
    result = await query_user()
```

然后用：

```python
asyncio.run(main())
```

启动。

后面我们写 FastAPI 接口时，通常会写：

```python
@app.post("/chat")
async def chat():
    result = await llm_service.chat()
```

因为这个接口函数本身是：

```python
async def
```

==所以里面可以 await。==

---

## 十三、10｜并发执行：asyncio.gather
### 【创建文件】
新建：

```text
app/async_demo/04_gather.py
```

写入：

```python
import asyncio
import time


async def query_user():
    print("开始查询用户信息")
    await asyncio.sleep(1)
    print("用户信息查询完成")
    return "用户信息"


async def query_order():
    print("开始查询订单信息")
    await asyncio.sleep(1)
    print("订单信息查询完成")
    return "订单信息"


async def query_llm():
    print("开始调用大模型")
    await asyncio.sleep(2)
    print("大模型返回结果")
    return "AI 回答"


async def main():
    start = time.perf_counter()

    user, order, answer = await asyncio.gather(
        query_user(),
        query_order(),
        query_llm()
    )

    end = time.perf_counter()

    print(user)
    print(order)
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/04_gather.py
```

输出类似：

```text
开始查询用户信息
开始查询订单信息
开始调用大模型
用户信息查询完成
订单信息查询完成
大模型返回结果
用户信息
订单信息
AI 回答
总耗时：2.00 秒
```

---

### 【重点内容】
现在我们使用：

```python
asyncio.gather()
```

把三个任务同时发出去：

```python
query_user()
query_order()
query_llm()
```

这三个任务的耗时分别是：

```text
1 秒
1 秒
2 秒
```

如果同步执行，总耗时是：

```text
4 秒
```

现在并发执行，总耗时大约是：

```text
2 秒
```

因为最长的那个任务是 2 秒。

这就是异步并发的价值。

---

## 十四、11｜AI 场景里的 gather
### 【重点内容】
在 AI Agent 里面，`asyncio.gather` 非常常见。

比如用户问：

```text
帮我分析订单 10001 为什么配送慢，并判断是否可以退款。
```

Agent 可能需要同时做：

```text
查询订单
查询物流
查询售后政策
查询用户等级
```

我们可以写成：

```python
order, logistics, policy, user = await asyncio.gather(
    query_order(order_id),
    query_logistics(order_id),
    search_policy("退款政策"),
    query_user(user_id)
)
```

这样比串行执行快很多。

==所以后面大家写 Agent 的时候，要有一个性能意识：==

**能并发的 IO 操作，不要无脑串行。**

---

## 十五、12｜gather 返回值顺序
继续修改：

```text
app/async_demo/04_gather.py
```

代码：

```python
import asyncio


async def task_a():
    await asyncio.sleep(2)
    return "A"


async def task_b():
    await asyncio.sleep(1)
    return "B"


async def task_c():
    await asyncio.sleep(0.5)
    return "C"


async def main():
    results = await asyncio.gather(
        task_a(),
        task_b(),
        task_c()
    )

    print(results)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/04_gather.py
```

输出：

```text
['A', 'B', 'C']
```

---

### 【重点内容】
这里大家注意。

虽然：

```text
task_c 最先完成
task_b 第二个完成
task_a 最后完成
```

但是 gather 返回结果的顺序仍然是：

```python
task_a, task_b, task_c
```

也就是你传进去的顺序。

所以：

```python
results = await asyncio.gather(
    task_a(),
    task_b(),
    task_c()
)
```

返回：

```python
["A", "B", "C"]
```

这点后面很重要。

比如：

```python
order, logistics, user = await asyncio.gather(
    query_order(),
    query_logistics(),
    query_user()
)
```

变量顺序要和任务顺序对应好。

---

## 十六、13｜create_task：提前启动任务
### 【创建文件】
新建：

```text
app/async_demo/05_create_task.py
```

写入：

```python
import asyncio
import time


async def query_llm():
    print("开始调用大模型")
    await asyncio.sleep(2)
    print("大模型返回结果")
    return "AI 回答"


async def query_user():
    print("开始查询用户")
    await asyncio.sleep(1)
    print("用户查询完成")
    return "用户信息"


async def main():
    start = time.perf_counter()

    llm_task = asyncio.create_task(query_llm())

    user = await query_user()

    answer = await llm_task

    end = time.perf_counter()

    print(user)
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/05_create_task.py
```

输出类似：

```text
开始查询用户
开始调用大模型
用户查询完成
大模型返回结果
用户信息
AI 回答
总耗时：2.00 秒
```

---

### 【重点内容】
这里我们用了：

```python
asyncio.create_task()
```

它的作用是：

**把一个协程包装成任务，并尽快交给事件循环调度。**

这里我们先创建：

```python
llm_task = asyncio.create_task(query_llm())
```

大模型调用就已经开始了。

然后我们继续执行：

```python
user = await query_user()
```

查询用户的时候，大模型任务也在等待执行。

最后：

```python
answer = await llm_task
```

拿到大模型结果。

这和 gather 有点像，但 create_task 更灵活。

---

## 十七、14｜gather 和 create_task 的区别
### 【重点内容】
简单来说：

```text
asyncio.gather
= 同时等待一组任务完成

asyncio.create_task
= 先把某个任务启动起来，后面再决定什么时候 await
```

常见使用方式：

```python
results = await asyncio.gather(
    task1(),
    task2(),
    task3()
)
```

适合：

```text
我现在明确有一组任务
我就等它们全部完成
```

而：

```python
llm_task = asyncio.create_task(call_llm())

# 中间做别的事情

answer = await llm_task
```

适合：

```text
我想提前启动一个任务
中间继续做别的逻辑
最后再取结果
```

后面开发 Agent 时，如果某个任务可以提前启动，就可以使用 create_task 做优化。

---

## 十八、15｜异步异常处理
### 【创建文件】
新建：

```text
app/async_demo/06_exceptions.py
```

写入：

```python
import asyncio


async def query_order():
    await asyncio.sleep(1)
    raise ValueError("订单服务异常")


async def main():
    try:
        result = await query_order()
        print(result)
    except ValueError as e:
        print(f"捕获异常：{e}")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/06_exceptions.py
```

输出：

```text
捕获异常：订单服务异常
```

---

### 【重点内容】
异步函数里面也可以用：

```python
try / except
```

捕获异常。

比如后面我们调用：

```text
LLM API
Embedding API
数据库
Redis
Tool
```

都有可能失败。

==所以异步代码也要写异常处理。==

不要写成：

```python
result = await query_order()
```

然后完全不管异常。

企业项目里面至少要处理：

```text
网络异常
超时异常
参数异常
模型异常
工具调用异常
```

---

## 十九、16｜gather 中的异常
继续写：

```python
import asyncio


async def query_order():
    await asyncio.sleep(1)
    raise ValueError("订单服务异常")


async def query_user():
    await asyncio.sleep(1)
    return "用户信息"


async def main():
    try:
        results = await asyncio.gather(
            query_order(),
            query_user()
        )
        print(results)
    except Exception as e:
        print(f"gather 捕获异常：{e}")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/06_exceptions.py
```

输出：

```text
gather 捕获异常：订单服务异常
```

---

### 【重点内容】
如果 gather 里面有一个任务抛异常，整个 gather 会抛出异常。

==所以在 Agent 并发调用多个 Tool 的时候要小心。==

比如：

```python
order, logistics, user = await asyncio.gather(
    query_order(),
    query_logistics(),
    query_user()
)
```

如果 query_logistics 报错，整个 gather 就会进入异常。

有些场景这是合理的。

但是有些场景，我们希望：

```text
某个 Tool 失败
其他 Tool 结果仍然保留
```

这时候可以用 `return_exceptions=True`。

---

## 二十、17｜gather return_exceptions
继续写：

```python
import asyncio


async def query_order():
    await asyncio.sleep(1)
    raise ValueError("订单服务异常")


async def query_user():
    await asyncio.sleep(1)
    return "用户信息"


async def main():
    results = await asyncio.gather(
        query_order(),
        query_user(),
        return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            print(f"任务失败：{result}")
        else:
            print(f"任务成功：{result}")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/06_exceptions.py
```

输出：

```text
任务失败：订单服务异常
任务成功：用户信息
```

---

### 【重点内容】
这里：

```python
return_exceptions=True
```

表示：

**不要因为某一个任务异常就直接抛出，而是把异常也作为结果返回。**

这在 Agent 场景很有用。

比如 Agent 同时调用：

```text
订单 Tool
物流 Tool
用户 Tool
商品 Tool
```

其中物流 Tool 失败了，但是订单、用户、商品都成功。

这时候我们可以告诉用户：

```text
订单和商品信息已查询到，但物流服务暂时不可用。
```

而不是整个请求直接失败。

==这就是企业级 AI 应用和 Demo 的区别。==

---

## 二十一、18｜超时控制 wait_for
### 【创建文件】
新建：

```text
app/async_demo/07_timeout.py
```

写入：

```python
import asyncio


async def call_llm():
    print("开始调用大模型")
    await asyncio.sleep(5)
    return "AI 回答"


async def main():
    try:
        result = await asyncio.wait_for(
            call_llm(),
            timeout=2
        )
        print(result)
    except asyncio.TimeoutError:
        print("调用大模型超时")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/07_timeout.py
```

输出：

```text
开始调用大模型
调用大模型超时
```

---

### 【重点内容】
AI 应用一定要有超时控制。

比如大模型调用：

```text
正常 1 到 3 秒返回
```

但是某一次因为网络抖动，可能 30 秒都不返回。

如果你没有超时控制，请求会一直卡住。

所以我们可以使用：

```python
asyncio.wait_for()
```

比如：

```python
await asyncio.wait_for(call_llm(), timeout=2)
```

表示：

**最多等待 2 秒。**

超过 2 秒，就抛出：

```python
asyncio.TimeoutError
```

后面我们调用 LLM、Tool、MCP Server，都应该考虑超时。

---

## 二十二、19｜AI 场景里的超时降级
继续写：

```python
import asyncio


async def call_advanced_model():
    print("调用高级模型")
    await asyncio.sleep(5)
    return "高级模型回答"


async def call_backup_model():
    print("调用备用模型")
    await asyncio.sleep(1)
    return "备用模型回答"


async def main():
    try:
        result = await asyncio.wait_for(
            call_advanced_model(),
            timeout=2
        )
    except asyncio.TimeoutError:
        print("高级模型超时，切换备用模型")
        result = await call_backup_model()

    print(result)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/07_timeout.py
```

输出：

```text
调用高级模型
高级模型超时，切换备用模型
调用备用模型
备用模型回答
```

---

### 【重点内容】
这个例子很接近真实 AI 项目。

我们可以先调用高级模型。

如果高级模型超时：

```text
切换备用模型
```

这就是模型降级。

比如：

```text
GPT-4o 超时
 ↓
切换 GPT-4o-mini

Claude 超时
 ↓
切换 DeepSeek

远程模型超时
 ↓
切换本地模型
```

==企业级 AI 应用一定要考虑：==

```text
超时
失败
重试
降级
熔断
```

这一章先把超时的基础讲清楚，后面我们会在 LLM Service 里面真正用上。

---

## 二十三、20｜并发限流 Semaphore
### 【创建文件】
新建：

```text
app/async_demo/08_semaphore.py
```

写入：

```python
import asyncio
import time


async def call_llm(index: int):
    print(f"任务 {index} 开始调用大模型")
    await asyncio.sleep(1)
    print(f"任务 {index} 调用完成")
    return f"结果 {index}"


async def main():
    start = time.perf_counter()

    tasks = [
        call_llm(i)
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    end = time.perf_counter()

    print(results)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/08_semaphore.py
```

输出会显示 10 个任务几乎同时开始。

---

### 【重点内容】
这里我们同时发起 10 个大模型请求。

```python
tasks = [
    call_llm(i)
    for i in range(10)
]
```

如果真实调用 LLM API，这样可能会有问题。

因为模型服务通常有限制：

```text
每分钟请求数 RPM
每分钟 Token 数 TPM
并发连接数
账户额度
```

所以我们不能无限并发。

这时候需要并发限流。

---

## 二十四、21｜使用 Semaphore 控制并发数量
修改代码：

```python
import asyncio
import time


semaphore = asyncio.Semaphore(3)


async def call_llm(index: int):
    async with semaphore:
        print(f"任务 {index} 开始调用大模型")
        await asyncio.sleep(1)
        print(f"任务 {index} 调用完成")
        return f"结果 {index}"


async def main():
    start = time.perf_counter()

    tasks = [
        call_llm(i)
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    end = time.perf_counter()

    print(results)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/08_semaphore.py
```

输出会看到每次最多 3 个任务同时执行。

---

### 【重点内容】
这里：

```python
semaphore = asyncio.Semaphore(3)
```

表示最多允许 3 个任务同时进入。

然后：

```python
async with semaphore:
```

表示进入并发控制区域。

这样即使我们创建了 10 个任务，也不会同时全部请求 LLM。

而是最多 3 个一起执行。

这在 AI 项目里非常重要。

比如：

```text
批量处理 100 个文档
批量生成 100 个 embedding
批量调用 50 个 Tool
批量总结 30 篇文章
```

都不能无脑全部并发。

要控制并发数量。

否则可能导致：

```text
API 限流
服务崩溃
Token 成本失控
数据库连接耗尽
```

---

## 二十五、22｜async generator 异步生成器
### 【创建文件】
新建：

```text
app/async_demo/09_async_generator.py
```

写入：

```python
import asyncio


async def generate_numbers():
    for i in range(5):
        await asyncio.sleep(0.5)
        yield i


async def main():
    async for num in generate_numbers():
        print(num)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/09_async_generator.py
```

输出：

```text
0
1
2
3
4
```

---

### 【重点内容】
这里我们接触一个非常重要的语法：

```python
yield
```

普通函数里面用：

```python
return
```

会一次性返回结果。

但是：

```python
yield
```

可以一点一点产出结果。

如果函数是：

```python
async def
```

里面又用了：

```python
yield
```

那么它就是异步生成器。

消费异步生成器，需要使用：

```python
async for
```

后面我们做大模型流式输出，会大量用这个思想。

---

## 二十六、23｜模拟 LLM 流式输出
修改：

```text
app/async_demo/09_async_generator.py
```

代码：

```python
import asyncio


async def stream_llm_answer(question: str):
    answer = f"你问的是：{question}。这是一个模拟的大模型流式回答。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield char


async def main():
    async for chunk in stream_llm_answer("什么是 AI Agent？"):
        print(chunk, end="", flush=True)

    print()


asyncio.run(main())
```

运行：

```bash
python app/async_demo/09_async_generator.py
```

你会看到文字一个字一个字输出：

```text
你问的是：什么是 AI Agent？这是一个模拟的大模型流式回答。
```

---

### 【重点内容】
这个例子非常接近我们后面的 AI Chat 流式输出。

大模型流式返回的时候，不是一次性返回完整答案。

它是不断返回：

```text
chunk
chunk
chunk
chunk
```

或者可以理解为：

```text
token
token
token
token
```

我们用：

```python
async def stream_llm_answer()
```

模拟一个大模型流。

然后用：

```python
async for chunk in stream_llm_answer()
```

一点一点消费它。

后面到 FastAPI 里面，我们会把这些 chunk 通过：

```text
SSE
```

返回给前端。

前端就可以实现：

```text
AI 逐字输出效果
```

---

## 二十七、24｜async with 异步上下文管理
### 【创建文件】
新建：

```text
app/async_demo/10_async_context.py
```

写入：

```python
import asyncio


class AsyncDatabase:
    async def __aenter__(self):
        print("打开数据库连接")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        print("关闭数据库连接")

    async def query(self, sql: str) -> str:
        await asyncio.sleep(1)
        return f"查询结果：{sql}"


async def main():
    async with AsyncDatabase() as db:
        result = await db.query("SELECT * FROM users")
        print(result)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/10_async_context.py
```

输出：

```text
打开数据库连接
查询结果：SELECT * FROM users
关闭数据库连接
```

---

### 【重点内容】
这里我们看到一个新语法：

```python
async with
```

它是异步上下文管理器。

它的作用是：

**自动管理资源的打开和关闭。**

比如：

```text
数据库连接
HTTP 客户端
Redis 连接
文件资源
MCP Client 连接
```

这些资源不能只打开不关闭。

==所以后面我们会经常看到：==

```python
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

或者：

```python
async with async_session() as session:
    result = await session.execute(sql)
```

只要看到：

```python
async with
```

你就理解成：

**异步资源的自动打开和关闭。**

---

## 二十八、25｜使用 httpx 模拟异步 HTTP 请求
### 【安装依赖】
执行：

```bash
uv add httpx
```

创建：

```text
app/async_demo/10_async_context.py
```

追加代码：

```python
import asyncio
import httpx


async def fetch_url(url: str) -> int:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.status_code


async def main():
    status_code = await fetch_url("https://example.com")
    print(status_code)


asyncio.run(main())
```

运行：

```bash
python app/async_demo/10_async_context.py
```

输出可能是：

```text
200
```

---

### 【重点内容】
这里我们使用了：

```python
httpx.AsyncClient()
```

它是一个异步 HTTP 客户端。

后面我们如果不用官方 SDK，而是直接通过 HTTP 调用大模型 API，就会写类似代码：

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        url,
        json=payload,
        headers=headers
    )
```

==所以 async with 和 await 在 AI 项目中非常常见。==

注意，如果你的网络环境访问不了 example.com，这个例子不影响理解。

核心是理解代码结构：

```python
async with 打开 HTTP 客户端
await client.get 发送请求
自动关闭连接
```

---

## 二十九、26｜模拟 LLM 流式输出封装
### 【创建文件】
新建：

```text
app/async_demo/11_llm_stream.py
```

写入：

```python
import asyncio
from collections.abc import AsyncGenerator


async def fake_llm_stream(prompt: str) -> AsyncGenerator[str, None]:
    answer = f"根据你的问题「{prompt}」，AI Agent 是能够理解目标、规划步骤并调用工具完成任务的智能体。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield char


async def main():
    async for token in fake_llm_stream("什么是 AI Agent？"):
        print(token, end="", flush=True)

    print()


asyncio.run(main())
```

运行：

```bash
python app/async_demo/11_llm_stream.py
```

---

### 【重点内容】
现在我们把流式输出写得更像真实项目。

这里：

```python
AsyncGenerator[str, None]
```

表示这是一个异步生成器。

它每次产出：

```python
str
```

后面的：

```python
None
```

表示不接收外部 send 进来的值。

大家不需要现在把这个类型记得特别深。

先知道：

```python
async def fake_llm_stream() -> AsyncGenerator[str, None]:
```

表示：

**这个函数会异步地、一段一段地产出字符串。**

==这就是后面真实 LLM Stream 的函数签名。==

---

## 三十、27｜流式输出加上 chunk 格式
继续修改：

```text
app/async_demo/11_llm_stream.py
```

代码：

```python
import asyncio
from collections.abc import AsyncGenerator


async def fake_llm_stream(prompt: str) -> AsyncGenerator[dict[str, str], None]:
    answer = f"根据你的问题「{prompt}」，AI Agent 是能够理解目标、规划步骤并调用工具完成任务的智能体。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield {
            "type": "token",
            "content": char
        }

    yield {
        "type": "done",
        "content": ""
    }


async def main():
    async for chunk in fake_llm_stream("什么是 AI Agent？"):
        if chunk["type"] == "token":
            print(chunk["content"], end="", flush=True)

        if chunk["type"] == "done":
            print("\n流式输出结束")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/11_llm_stream.py
```

---

### 【重点内容】
==真实项目里，我们流式返回的不一定只是字符串。==

有时候需要告诉前端：

```text
这是 token
这是工具调用
这是错误
这是结束标记
```

所以我们可以让每个 chunk 变成字典：

```python
{
    "type": "token",
    "content": char
}
```

最后再返回：

```python
{
    "type": "done",
    "content": ""
}
```

这就是后面设计 AI Chat 流式协议的基础。

---

## 三十一、28｜综合实战：模拟 Agent 并发调用多个 Tool
### 【创建文件】
新建：

```text
app/async_demo/12_agent_tools.py
```

写入：

```python
import asyncio
import time
from typing import Any
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    user_id: str = Field(..., description="用户 ID")
    order_id: str = Field(..., description="订单 ID")
    question: str = Field(..., description="用户问题")


async def query_user(user_id: str) -> dict[str, Any]:
    print("开始查询用户信息")
    await asyncio.sleep(1)
    print("用户信息查询完成")

    return {
        "user_id": user_id,
        "name": "大伟",
        "level": "VIP"
    }


async def query_order(order_id: str) -> dict[str, Any]:
    print("开始查询订单信息")
    await asyncio.sleep(1)
    print("订单信息查询完成")

    return {
        "order_id": order_id,
        "status": "已发货",
        "amount": 299
    }


async def query_logistics(order_id: str) -> dict[str, Any]:
    print("开始查询物流信息")
    await asyncio.sleep(2)
    print("物流信息查询完成")

    return {
        "order_id": order_id,
        "company": "顺丰",
        "status": "运输中",
        "eta": "明天送达"
    }


async def call_llm(
    question: str,
    user: dict[str, Any],
    order: dict[str, Any],
    logistics: dict[str, Any]
) -> str:
    print("开始调用大模型生成最终回答")
    await asyncio.sleep(1)

    return (
        f"用户 {user['name']}，您的订单 {order['order_id']} 当前状态是"
        f"{order['status']}，物流公司是{logistics['company']}，"
        f"当前物流状态：{logistics['status']}，预计{logistics['eta']}。"
    )


async def agent_run(request: AgentRequest) -> str:
    user, order, logistics = await asyncio.gather(
        query_user(request.user_id),
        query_order(request.order_id),
        query_logistics(request.order_id)
    )

    answer = await call_llm(
        question=request.question,
        user=user,
        order=order,
        logistics=logistics
    )

    return answer


async def main():
    start = time.perf_counter()

    request = AgentRequest(
        user_id="u_10001",
        order_id="o_10001",
        question="帮我查询一下订单物流状态"
    )

    answer = await agent_run(request)

    end = time.perf_counter()

    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

运行：

```bash
python app/async_demo/12_agent_tools.py
```

输出类似：

```text
开始查询用户信息
开始查询订单信息
开始查询物流信息
用户信息查询完成
订单信息查询完成
物流信息查询完成
开始调用大模型生成最终回答
用户 大伟，您的订单 o_10001 当前状态是已发货，物流公司是顺丰，当前物流状态：运输中，预计明天送达。
总耗时：3.00 秒
```

---

### 【重点内容】
这个例子非常重要。

因为它已经不是单纯讲异步语法了，而是在模拟一个真实 Agent 执行流程。

用户问：

```text
帮我查询一下订单物流状态
```

Agent 要做：

```text
查询用户
查询订单
查询物流
调用大模型组织回答
```

这里前三个任务：

```python
query_user()
query_order()
query_logistics()
```

==彼此之间没有强依赖，所以可以并发。==

我们使用：

```python
await asyncio.gather(...)
```

并发查询。

等数据都回来之后，再调用：

```python
call_llm()
```

生成最终回答。

这就是后面 Agent Tool Calling 的基础思想。

---

## 三十二、29｜加入 Tool 超时控制
继续修改：

```text
app/async_demo/12_agent_tools.py
```

增加一个安全调用函数：

```python
async def safe_call_tool(tool_name: str, coro, timeout: float = 2):
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return {
            "error": f"{tool_name} 调用超时"
        }
    except Exception as e:
        return {
            "error": f"{tool_name} 调用失败：{e}"
        }
```

修改 `agent_run`：

```python
async def agent_run(request: AgentRequest) -> str:
    user, order, logistics = await asyncio.gather(
        safe_call_tool("query_user", query_user(request.user_id)),
        safe_call_tool("query_order", query_order(request.order_id)),
        safe_call_tool("query_logistics", query_logistics(request.order_id)),
    )

    if "error" in logistics:
        return f"订单信息已查询到，但物流服务暂时不可用：{logistics['error']}"

    answer = await call_llm(
        question=request.question,
        user=user,
        order=order,
        logistics=logistics
    )

    return answer
```

---

### 【重点内容】
现在我们把 Tool 调用封装成：

```python
safe_call_tool()
```

这个函数做了两件事：

```text
1. 超时控制
2. 异常捕获
```

这在 Agent 项目里非常重要。

因为 Agent 不是只调用一个函数。

它可能调用：

```text
订单系统
物流系统
库存系统
CRM 系统
知识库系统
MCP Server
```

任何一个系统都有可能：

```text
超时
失败
返回异常
```

如果不做保护，一个 Tool 挂了，整个 Agent 就挂了。

企业级 Agent 要有容错能力。

---

## 三十三、30｜综合实战：FastAPI 异步接口预告
### 【创建文件】
新建：

```text
app/async_demo/13_fastapi_preview.py
```

写入：

```python
import asyncio
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


async def call_llm(message: str) -> str:
    await asyncio.sleep(1)
    return f"AI 回答：你问的是 {message}"


async def chat_service(request: ChatRequest) -> ChatResponse:
    answer = await call_llm(request.message)
    return ChatResponse(answer=answer)


async def main():
    request = ChatRequest(message="什么是 LangGraph？")
    response = await chat_service(request)
    print(response.model_dump())


asyncio.run(main())
```

运行：

```bash
python app/async_demo/13_fastapi_preview.py
```

输出：

```text
{'answer': 'AI 回答：你问的是 什么是 LangGraph？'}
```

---

### 【重点内容】
这个例子是下一阶段 FastAPI 的预告。

现在我们有：

```python
ChatRequest
ChatResponse
call_llm
chat_service
```

后面进入 FastAPI 之后，我们只需要再包一层接口：

```python
@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    return await chat_service(request)
```

所以你会发现：

```text
Pydantic
+
async / await
```

==是 FastAPI AI 后端的核心基础。==

---

## 三十四、31｜async / await 和 FastAPI 的关系
### 【重点内容】
为什么 FastAPI 里面经常写：

```python
@app.post("/chat")
async def chat():
    pass
```

而不是：

```python
def chat():
    pass
```

因为 AI 后端经常要等待：

```text
LLM API
数据库
Redis
向量库
外部工具
```

如果接口是异步的，在等待这些 IO 的时候，服务器可以处理其他请求。

比如：

```text
用户 A 调用 LLM，等待 3 秒
用户 B 也发起请求
用户 C 也发起请求
```

异步框架可以在 A 等待模型的时候继续处理 B、C。

这就是 FastAPI 适合 AI 后端的原因之一。

---

## 三十五、32｜async / await 和 RAG 的关系
### 【重点内容】
RAG 流程里面也有大量异步操作。

比如：

```text
用户问题
 ↓
生成 Query Embedding
 ↓
查询向量数据库
 ↓
Rerank
 ↓
调用 LLM
```

这些步骤里有很多都是 IO。

后面我们可能写：

```python
query_vector = await embedding_service.embed(question)

documents = await vector_store.search(query_vector)

reranked_docs = await rerank_service.rerank(question, documents)

answer = await llm_service.chat(question, reranked_docs)
```

如果再进一步优化，有些步骤还能并发。

比如同时查询多个知识库：

```python
docs_a, docs_b, docs_c = await asyncio.gather(
    search_kb_a(question),
    search_kb_b(question),
    search_kb_c(question)
)
```

==所以异步对 RAG 性能也非常关键。==

---

## 三十六、33｜async / await 和 Agent 的关系
### 【重点内容】
Agent 里面异步更重要。

因为 Agent 不是简单调用一次大模型。

它可能有多个步骤：

```text
理解问题
 ↓
选择工具
 ↓
调用工具
 ↓
观察结果
 ↓
继续思考
 ↓
再次调用工具
 ↓
生成最终答案
```

其中 Tool 调用可能是：

```text
订单系统
物流系统
商品系统
知识库
搜索引擎
数据库
MCP Server
```

这些都是 IO。

所以 Agent 如果写成同步，很容易慢。

后面我们会写：

```python
tool_results = await asyncio.gather(
    call_tool("query_order"),
    call_tool("query_logistics"),
    call_tool("search_policy")
)
```

这就是异步在 Agent 中的典型用法。

---

## 三十七、34｜async / await 和流式输出的关系
### 【重点内容】
AI Chat 和传统接口最大的不同之一，就是流式输出。

传统接口：

```text
请求
 ↓
等待
 ↓
一次性返回完整结果
```

AI Chat：

```text
请求
 ↓
模型生成一个 token
 ↓
返回一个 token
 ↓
继续生成
 ↓
继续返回
```

所以后面我们会写：

```python
async def stream_chat():
    async for chunk in llm.stream():
        yield chunk
```

FastAPI 里面会用：

```python
StreamingResponse
```

把它返回给前端。

这背后就依赖：

```text
async generator
async for
yield
```

这一章我们已经提前打好基础了。

---

## 三十八、35｜常见错误一：time.sleep 写在 async 函数里

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误写法：

```python
import time


async def query_data():
    time.sleep(1)
    return "数据"
```

正确写法：

```python
import asyncio


async def query_data():
    await asyncio.sleep(1)
    return "数据"
```

---

### 【重点内容】
在 async 函数里面，不要随便写：

```python
time.sleep()
```

因为它会阻塞线程。

异步代码里应该使用：

```python
await asyncio.sleep()
```

真实项目里也是一样。

如果一个库只有同步方法，它可能会阻塞异步事件循环。

所以选择第三方库时，要尽量选择支持异步的版本。

比如：

```text
httpx.AsyncClient
SQLAlchemy AsyncSession
async Redis client
```

---

## 三十九、36｜常见错误二：忘记 await

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
result = call_llm()
print(result)
```

输出：

```text
<coroutine object ...>
```

正确：

```python
result = await call_llm()
```

---

### 【重点内容】
看到：

```text
coroutine object
```

基本就是你忘了：

```python
await
```

这在刚开始写 Python 异步代码时非常常见。

记住：

**async 函数调用后，需要 await 才能拿到结果。**

---

## 四十、37｜常见错误三：普通函数里写 await

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
def main():
    result = await call_llm()
```

正确：

```python
async def main():
    result = await call_llm()
```

然后：

```python
asyncio.run(main())
```

---

## 四十一、38｜常见错误四：在已有事件循环中乱用 asyncio.run
### 【重点内容】
在普通 Python 脚本里面，可以写：

```python
asyncio.run(main())
```

但是在一些已经有事件循环的环境里，比如：

```text
FastAPI
Jupyter Notebook
某些异步框架
```

不要随便嵌套调用：

```python
asyncio.run()
```

在 FastAPI 路由里面，应该直接：

```python
await service.do_something()
```

而不是：

```python
asyncio.run(service.do_something())
```

错误示例：

```python
@app.post("/chat")
async def chat():
    result = asyncio.run(call_llm())
    return result
```

正确示例：

```python
@app.post("/chat")
async def chat():
    result = await call_llm()
    return result
```

---

## 四十二、39｜常见错误五：无限并发

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
tasks = [call_llm(i) for i in range(1000)]
results = await asyncio.gather(*tasks)
```

风险：

```text
API 被限流
数据库连接耗尽
服务内存飙升
成本失控
```

正确：

```python
semaphore = asyncio.Semaphore(10)


async def safe_call(i: int):
    async with semaphore:
        return await call_llm(i)
```

---

### 【重点内容】
异步并发不是越多越好。

尤其是 AI 项目。

因为模型调用是有成本的。

你并发 1000 个请求，不只是技术问题，还是钱的问题。

所以后面做批量文档处理、批量 embedding、批量总结时，一定要有并发限制。

---

## 四十三、40｜本章知识点和 AI 开发场景对应表
| 异步知识点 | AI 开发场景 |
| --- | --- |
| `async def` | 定义异步接口、异步 Service、异步 Tool |
| `await` | 等待 LLM、数据库、Redis、Tool 返回 |
| `asyncio.run` | 在普通脚本中启动异步程序 |
| coroutine | 异步函数调用后的协程对象 |
| `asyncio.gather` | 并发调用多个 Tool / 多个知识库 |
| `asyncio.create_task` | 提前启动任务，后续再等待结果 |
| `return_exceptions=True` | 某个 Tool 失败时保留其他结果 |
| `asyncio.wait_for` | 控制 LLM / Tool / MCP 超时时间 |
| `asyncio.Semaphore` | 限制并发调用数量 |
| `async for` | 消费 LLM 流式输出 |
| `async generator` | 生成流式 token / chunk |
| `async with` | 管理数据库、HTTP、Redis、MCP 连接 |
| `try / except` | 捕获异步任务异常 |
| `time.sleep`<br/> 避坑 | 避免阻塞事件循环 |


---

## 四十四、41｜本章完整复习
这一章我们从同步阻塞开始，一步一步讲到了 AI 项目里的异步实战。

完整路线是：

```text
同步阻塞
 ↓
async def
 ↓
await
 ↓
coroutine
 ↓
asyncio.run
 ↓
asyncio.gather
 ↓
asyncio.create_task
 ↓
异常处理
 ↓
超时控制
 ↓
并发限流
 ↓
async generator
 ↓
async with
 ↓
Agent 并发 Tool
 ↓
LLM 流式输出
```

这一章不是孤立的语法课。

后面我们做：

```text
FastAPI
LLM Service
RAG
Agent
Tool Calling
MCP
Multi-Agent
```

都会用到这些能力。

---

## 四十五、42｜课后任务一：把同步代码改成异步
要求：

```text
1. 定义 query_user，耗时 1 秒
2. 定义 query_order，耗时 1 秒
3. 定义 query_llm，耗时 2 秒
4. 使用 asyncio.gather 并发执行
5. 打印总耗时
```

参考答案：

```python
import asyncio
import time


async def query_user():
    await asyncio.sleep(1)
    return "用户信息"


async def query_order():
    await asyncio.sleep(1)
    return "订单信息"


async def query_llm():
    await asyncio.sleep(2)
    return "AI 回答"


async def main():
    start = time.perf_counter()

    user, order, answer = await asyncio.gather(
        query_user(),
        query_order(),
        query_llm()
    )

    end = time.perf_counter()

    print(user)
    print(order)
    print(answer)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

---

## 四十六、43｜课后任务二：模拟 LLM 超时降级
要求：

```text
1. call_primary_model 耗时 5 秒
2. call_backup_model 耗时 1 秒
3. primary 超过 2 秒就切换 backup
4. 最终打印备用模型结果
```

参考答案：

```python
import asyncio


async def call_primary_model():
    await asyncio.sleep(5)
    return "主模型回答"


async def call_backup_model():
    await asyncio.sleep(1)
    return "备用模型回答"


async def main():
    try:
        result = await asyncio.wait_for(
            call_primary_model(),
            timeout=2
        )
    except asyncio.TimeoutError:
        result = await call_backup_model()

    print(result)


asyncio.run(main())
```

---

## 四十七、44｜课后任务三：模拟流式输出
要求：

```text
1. 定义 stream_answer
2. 使用 async generator
3. 每次 yield 一个字符
4. 使用 async for 消费
5. 终端逐字打印
```

参考答案：

```python
import asyncio
from collections.abc import AsyncGenerator


async def stream_answer(question: str) -> AsyncGenerator[str, None]:
    answer = f"你问的是：{question}。这是一个模拟流式回答。"

    for char in answer:
        await asyncio.sleep(0.05)
        yield char


async def main():
    async for chunk in stream_answer("什么是 RAG？"):
        print(chunk, end="", flush=True)

    print()


asyncio.run(main())
```

---

## 四十八、45｜课后任务四：限制并发调用数量
要求：

```text
1. 模拟 20 个 embedding 任务
2. 每个任务耗时 1 秒
3. 使用 Semaphore 限制最多 5 个并发
4. 打印总耗时
```

参考答案：

```python
import asyncio
import time


semaphore = asyncio.Semaphore(5)


async def create_embedding(index: int):
    async with semaphore:
        print(f"开始生成第 {index} 个 embedding")
        await asyncio.sleep(1)
        print(f"第 {index} 个 embedding 完成")
        return f"embedding_{index}"


async def main():
    start = time.perf_counter()

    tasks = [
        create_embedding(i)
        for i in range(20)
    ]

    results = await asyncio.gather(*tasks)

    end = time.perf_counter()

    print(results)
    print(f"总耗时：{end - start:.2f} 秒")


asyncio.run(main())
```

---

## 四十九、46｜课后任务五：Agent 并发调用 Tool
要求：

```text
1. 定义 query_order
2. 定义 query_logistics
3. 定义 query_policy
4. 三个函数都是 async
5. 使用 gather 并发调用
6. 最后生成一个回答
```

参考答案：

```python
import asyncio


async def query_order(order_id: str):
    await asyncio.sleep(1)
    return {
        "order_id": order_id,
        "status": "已发货"
    }


async def query_logistics(order_id: str):
    await asyncio.sleep(2)
    return {
        "company": "顺丰",
        "status": "运输中"
    }


async def query_policy():
    await asyncio.sleep(1)
    return {
        "refund": "发货后如无质量问题，不支持直接退款"
    }


async def main():
    order, logistics, policy = await asyncio.gather(
        query_order("10001"),
        query_logistics("10001"),
        query_policy()
    )

    answer = (
        f"订单 {order['order_id']} 当前状态：{order['status']}；"
        f"物流：{logistics['company']}，{logistics['status']}；"
        f"售后政策：{policy['refund']}。"
    )

    print(answer)


asyncio.run(main())
```

---

## 五十、47｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【最终重点内容】
好了，到这里，第 05 章我们就讲完了。

这一章我们系统学习了 Python 的异步编程。

大家一定要记住，异步编程不是为了让代码看起来高级。

它解决的是 AI 应用里面非常现实的问题：

```text
LLM 调用慢
Tool 调用多
RAG 检索多
外部系统不稳定
流式输出需要持续返回
批量任务需要并发
```

所以我们才需要：

```text
async def
await
asyncio.gather
asyncio.create_task
asyncio.wait_for
asyncio.Semaphore
async for
async generator
async with
```

后面进入 FastAPI 之后，你会发现：

```python
@app.post("/chat")
async def chat():
    result = await llm_service.chat()
```

这其实就是今天学的内容。

后面做 RAG 时：

```python
docs = await retriever.search(question)
```

也是今天学的内容。

后面做 Agent 时：

```python
tool_results = await asyncio.gather(
    call_order_tool(),
    call_logistics_tool(),
    call_policy_tool()
)
```

也是今天学的内容。

后面做流式输出时：

```python
async for chunk in llm.stream():
    yield chunk
```

还是今天学的内容。

所以这一章非常关键。



---

> [!success] 一句话带走
> ==AI 应用大量时间都在等接口返回，异步就是把这些等待叠起来用。==

> [!quote] 关于本文档
> 由原始讲义 `第 05 章｜Python 异步编程 async ｜ await.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
