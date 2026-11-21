---
title: "第 06 章｜FastAPI 快速入门"
chapter: "06"
source: "第 06 章｜FastAPI 快速入门.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - uvicorn
  - api
---

# 第 06 章｜FastAPI 快速入门

> [!abstract] 本章重点
>
> - ==uvicorn app.main:app 是「模块路径:实例名」== — 冒号前找文件，冒号后找 app 对象。
> - ==/docs 自动生成 Swagger 文档== — 类型写清楚，接口文档就顺带有了。
> - ==Path 参数在路径里，Query 参数在 ? 后面== — 要加校验就用 Query(...)。
> - ==POST 用 Pydantic 模型接请求体== — 字段不合规自动返回 422，不用手写判断。
> - ==response_model 约束返回形状== — 多返回的字段会被自动过滤掉。
> - ==Controller / Service 分层== — 接口只管收参返参，业务逻辑放到 Service。
>
> [!note] 大白话
>
> - **422**：请求参数没通过校验时，FastAPI 返回的状态码。
>
> [!info] 导航与来源
> - 原始讲义：[[第 06 章｜FastAPI 快速入门|打开原始讲义]]
> - [[第 05 章｜Python 异步编程 async ｜ await|上一章｜第 05 章]]
> - [[第 07 章｜Pydantic 请求参数与响应模型|下一章｜第 07 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#FastAPI AI 后端开发]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#五、02｜确认当前环境]]
- [[#六、03｜安装 FastAPI 和 Uvicorn]]
- [[#七、04｜第一个 FastAPI 应用]]
- [[#八、05｜理解 uvicorn app.main:app]]
- [[#九、06｜访问 Swagger 文档]]
- [[#十、07｜FastAPI 和 NestJS / Express 对比]]
- [[#十一、08｜添加应用基础信息]]
- [[#十二、09｜添加健康检查接口 /health]]
- [[#十三、10｜Path 参数]]

---
适合人群：已经完成 Python 基础、Pydantic、async / await，准备正式进入 Python AI 后端开发的学员。

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面几章我们已经完成了 Python AI 开发的基础能力：

```text
第 02 章：Python AI 开发环境搭建
第 03 章：Python AI 开发快速入门
第 04 章：Python 类型系统与 Pydantic 深入
第 05 章：Python 异步编程 async / await
```

从这一章开始，我们正式进入：

## FastAPI AI 后端开发
为什么 AI 应用开发里面非常适合使用 FastAPI？

因为 AI 后端经常需要：

```text
HTTP API
请求参数校验
响应模型
异步接口
流式输出
Swagger 文档
前后端联调
LLM API 调用
RAG 检索接口
Agent 执行接口
```

这些能力 FastAPI 都非常适合承载。

后面我们的 AI 项目基本都会围绕 FastAPI 展开。

比如：

```http
POST /chat
POST /chat/stream
POST /rag/query
POST /agent/run
POST /tool/call
GET /health
```

==所以这一章不是普通 Web 后端入门，而是：==

**为 AI Chat、RAG、Agent、MCP、多智能体平台打后端基础。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. FastAPI 是什么
2. FastAPI 在 AI 后端里负责什么
3. 如何创建 FastAPI 应用
4. 如何启动 FastAPI 服务
5. 如何访问 Swagger 文档
6. GET 接口怎么写
7. POST 接口怎么写
8. Path 参数怎么写
9. Query 参数怎么写
10. Body 请求体怎么写
11. Pydantic 如何和 FastAPI 结合
12. Response Model 怎么写
13. async def 路由函数怎么理解
14. 如何写一个 /health 健康检查接口
15. 如何写一个 /chat AI 对话接口雏形
16. 如何组织本章项目目录
17. 如何处理基础异常
18. 如何理解 FastAPI 和 NestJS / Express 的关系
```

---

## 三、本章最终项目结构
本章结束之后，项目结构会变成：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       └── chat.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── chat.py
│   │
│   └── services/
│       ├── __init__.py
│       └── chat_service.py
│
├── tests/
├── .env
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

这一章我们会先从最简单的单文件 FastAPI 开始，然后逐步拆成：

```text
main.py
api/
schemas/
services/
```

这样后面项目继续扩展到：

```text
LLM
RAG
Agent
Tool
MCP
Multi-Agent
```

时，目录不会乱。

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 06 章。

从这一章开始，我们正式进入 FastAPI。

前面我们已经学了：

```text
Python 基础
Pydantic
async / await
```

这三个东西在这一章会全部用上。

FastAPI 可以理解成 Python 生态里非常适合做 API 服务的 Web 框架。

如果你是前端或者 Node.js 开发，可以先这样类比：

```text
FastAPI ≈ NestJS / Express / Koa
```

当然，它们不是完全一样。

但是从职责上看，FastAPI 主要负责：

```text
接收 HTTP 请求
解析请求参数
校验请求体
调用业务逻辑
返回 JSON 响应
生成 API 文档
支持异步接口
```

这和我们后面做 AI 应用非常匹配。

比如用户在前端输入一个问题：

```text
什么是 AI Agent？
```

后端收到：

```http
POST /chat
```

然后 FastAPI 做：

```text
解析请求体
 ↓
Pydantic 校验
 ↓
调用 ChatService
 ↓
ChatService 调用 LLM
 ↓
返回 AI 回答
```

==所以这一章我们要把 FastAPI 的基础打牢。==

---

## 五、02｜确认当前环境
### 【显示】
进入项目根目录：

```bash
cd ai-agent-course
```

激活虚拟环境：

Mac / Linux：

```bash
uv venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
```

检查 Python：

```bash
python --version
```

检查 uv：

```bash
uv --version
```

---

### 【重点内容】
我们先确认一下当前环境。

如果终端前面能看到：

```bash
(.venv)
```

说明虚拟环境已经激活。

这一章我们会继续使用前面创建好的：

```text
ai-agent-course
```

项目。

==如果你前面的环境没有搭好，建议先回到第 02 章，把 Python、uv、虚拟环境、FastAPI 安装完成。==

---

## 六、03｜安装 FastAPI 和 Uvicorn
### 【实操】
执行：

```bash
uv add fastapi
```

安装 Uvicorn：

```bash
uv add "uvicorn[standard]"
```

检查依赖：

```bash
uv pip list
```

---

### 【重点内容】
这里我们安装两个核心依赖。

第一个：

```text
FastAPI
```

它是 Web 框架。

第二个：

```text
Uvicorn
```

它是 ASGI Server。

可以这样理解：

```text
FastAPI
= 写接口的框架

Uvicorn
= 把接口服务跑起来的服务器
```

如果你是前端开发，可以稍微类比一下：

```text
FastAPI
≈ Express / NestJS

Uvicorn
≈ Node.js HTTP Server 的运行承载层
```

这个类比不完全严谨，但是有助于建立第一层直觉。

---

## 七、04｜第一个 FastAPI 应用
### 【创建文件】
创建或修改：

```text
app/main.py
```

写入：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "Hello FastAPI"
    }
```

启动服务：

```bash
uv run uvicorn app.main:app --reload
```

如果已经激活虚拟环境，也可以：

```bash
uvicorn app.main:app --reload
```

看到类似：

```http
Uvicorn running on http://127.0.0.1:8000
```

浏览器访问：

```http
http://127.0.0.1:8000
```

返回：

```json
{
  "message": "Hello FastAPI"
}
```

---

### 【重点内容】
现在我们写了第一个 FastAPI 应用。

代码很少：

```python
from fastapi import FastAPI
```

先导入 FastAPI。

然后：

```python
app = FastAPI()
```

创建一个应用对象。

再写：

```python
@app.get("/")
```

表示定义一个 GET 接口，路径是：

```text
/
```

最后：

```python
async def root():
```

这是接口处理函数。

它返回一个字典：

```python
{"message": "Hello FastAPI"}
```

FastAPI 会自动把它转换成 JSON 返回给浏览器。

---

## 八、05｜理解 uvicorn app.main:app
### 【重点内容】
==这里我们重点解释一下这个命令：==

```bash
uvicorn app.main:app --reload
```

很多新手第一次看到会懵。

它可以拆成三部分：

```text
uvicorn
= 启动服务器

app.main
= Python 模块路径

:app
= main.py 里面的 app 对象

--reload
= 开发模式，代码变更后自动重启
```

也就是说：

```bash
uvicorn app.main:app --reload
```

意思是：

启动 Uvicorn，找到 app/main.py 文件里面的 app 对象，把它作为 Web 应用跑起来。

这里大家要特别注意：

如果你的文件是：

```text
app/main.py
```

命令就是：

```bash
uvicorn app.main:app --reload
```

如果你的文件是：

```text
main.py
```

在项目根目录，那命令可能是：

```bash
uvicorn main:app --reload
```

==所以这个命令和你的文件路径有关。==

---

## 九、06｜访问 Swagger 文档
### 【实操】
浏览器打开：

```http
http://127.0.0.1:8000/docs
```

你会看到自动生成的接口文档。

再打开：

```http
http://127.0.0.1:8000/redoc
```

可以看到 ReDoc 文档。

---

### 【重点内容】
FastAPI 非常方便的一点是：

**自动生成 API 文档。**

我们只写了：

```python
@app.get("/")
async def root():
```

它就自动生成了：

```http
GET /
```

接口文档。

这个能力非常适合前后端联调。

以后我们开发：

```http
POST /chat
POST /chat/stream
POST /rag/query
POST /agent/run
```

都会自动出现在 Swagger 文档里面。

前端同学不用再等后端单独写接口文档。

后端只要把 Pydantic 模型写清楚，接口文档就自动生成。

---

## 十、07｜FastAPI 和 NestJS / Express 对比
### 展示【展示】
| 后端能力 | Express | NestJS | FastAPI |
| --- | --- | --- | --- |
| 应用对象 | `const app = express()` | `NestFactory.create()` | `app = FastAPI()` |
| GET 路由 | `app.get()` | `@Get()` | `@app.get()` |
| POST 路由 | `app.post()` | `@Post()` | `@app.post()` |
| DTO 校验 | 手动/中间件 | DTO + class-validator | Pydantic |
| 接口文档 | 额外配置 Swagger | Swagger 模块 | 自动 OpenAPI |
| 异步 | Promise / async-await | Promise / async-await | async / await |
| 路由拆分 | Router | Module / Controller | APIRouter |


---

### 【重点内容】
如果你以前写过 Express，大概可以这样理解：

Express：

```typescript
app.get("/", (req, res) => {
  res.json({ message: "hello" });
});
```

FastAPI：

```python
@app.get("/")
async def root():
    return {"message": "hello"}
```

如果你写过 NestJS：

```typescript
@Get()
findAll() {
  return { message: "hello" };
}
```

FastAPI：

```python
@app.get("/")
async def root():
    return {"message": "hello"}
```

所以核心概念非常接近：

```text
路由
请求
响应
参数
校验
业务逻辑
```

只是语法和框架风格不同。

---

## 十一、08｜添加应用基础信息
修改：

```text
app/main.py
```

代码：

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "Hello FastAPI"
    }
```

重新访问：

```http
http://127.0.0.1:8000/docs
```

---

### 【重点内容】
这里我们给 FastAPI 应用加了一些元信息：

```python
title
description
version
```

这些信息会显示到 Swagger 文档里面。

后面企业项目里，我们通常会写：

```python
app = FastAPI(
    title="Enterprise AI Agent Platform",
    description="企业级 AI Agent 平台接口文档",
    version="1.0.0",
)
```

这样前端、测试、后端自己看文档的时候会更清晰。

---

## 十二、09｜添加健康检查接口 /health
继续修改：

```text
app/main.py
```

代码：

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "message": "Hello FastAPI"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-agent-course",
        "version": "0.1.0"
    }
```

访问：

```http
http://127.0.0.1:8000/health
```

返回：

```json
{
  "status": "ok",
  "service": "ai-agent-course",
  "version": "0.1.0"
}
```

---

### 【重点内容】
现在我们添加一个：

```text
/health
```

健康检查接口。

这个接口在企业项目里非常常见。

它的作用是告诉外部系统：

```text
服务是否正常启动
服务是否可以访问
```

后面我们接入 Docker、Nginx、Kubernetes 或云平台的时候，健康检查接口非常有用。

现在我们只返回：

```json
{
  "status": "ok"
}
```

后面项目复杂之后，health 接口还可以检查：

```text
数据库是否连接正常
Redis 是否连接正常
向量数据库是否连接正常
LLM 服务是否可用
```

---

## 十三、10｜Path 参数
继续修改：

```text
app/main.py
```

增加：

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {
        "user_id": user_id,
        "name": f"用户 {user_id}"
    }
```

完整代码片段：

```python
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {
        "user_id": user_id,
        "name": f"用户 {user_id}"
    }
```

访问：

```http
http://127.0.0.1:8000/users/10001
```

返回：

```json
{
  "user_id": 10001,
  "name": "用户 10001"
}
```

---

### 【重点内容】
这里我们写了一个 Path 参数。

路径：

```python
"/users/{user_id}"
```

里面的：

```text
{user_id}
```

就是路径参数。

函数里写：

```python
user_id: int
```

FastAPI 会自动把 URL 里面的字符串转换成 int。

比如访问：

```text
/users/10001
```

FastAPI 会把：

```text
"10001"
```

转换成：

```python
10001
```

==这就是 FastAPI 类型系统和 Pydantic / Type Hint 结合的优势。==

如果你访问：

```text
/users/abc
```

它会自动返回参数校验错误。

---

## 十四、11｜Query 参数
继续增加：

```python
@app.get("/search")
async def search(q: str, page: int = 1, page_size: int = 10):
    return {
        "q": q,
        "page": page,
        "page_size": page_size
    }
```

访问：

```http
http://127.0.0.1:8000/search?q=agent&page=2&page_size=20
```

返回：

```json
{
  "q": "agent",
  "page": 2,
  "page_size": 20
}
```

---

### 【重点内容】
Query 参数就是 URL 问号后面的参数。

比如：

```text
/search?q=agent&page=2&page_size=20
```

这里：

```text
q
page
page_size
```

都是 Query 参数。

FastAPI 里面写：

```python
async def search(q: str, page: int = 1, page_size: int = 10):
```

如果参数没有默认值：

```python
q: str
```

说明它是必填。

如果有默认值：

```python
page: int = 1
```

说明它是可选。

这个和我们前面讲 Pydantic Optional 的逻辑类似：

**是否必填，不只看类型，还要看有没有默认值。**

---

## 十五、12｜用 Query 增加参数校验
修改导入：

```python
from fastapi import FastAPI, Query
```

修改 search 接口：

```python
@app.get("/search")
async def search(
    q: str = Query(..., min_length=1, max_length=50, description="搜索关键词"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页数量"),
):
    return {
        "q": q,
        "page": page,
        "page_size": page_size
    }
```

访问：

```http
http://127.0.0.1:8000/docs
```

查看 search 接口参数说明。

---

### 【重点内容】
这里我们使用了：

```python
Query
```

它可以给 Query 参数增加校验规则。

比如：

```python
q: str = Query(..., min_length=1, max_length=50)
```

表示 q 必填，最少 1 个字符，最多 50 个字符。

```python
page: int = Query(default=1, ge=1)
```

==表示 page 默认是 1，并且必须大于等于 1。==

```python
page_size: int = Query(default=10, ge=1, le=100)
```

表示 page_size 默认 10，范围 1 到 100。

这个在 AI 项目里也会经常用到。

比如：

```text
知识库搜索关键词
Top K 数量
分页参数
历史消息数量
```

都需要做 Query 校验。

---

## 十六、13｜POST 请求和 Pydantic 请求体
### 【创建 schema】
创建目录和文件：

```text
app/schemas/chat.py
```

写入：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=False, description="是否流式输出")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
```

---

### 【修改 main.py】
```python
from fastapi import FastAPI, Query
from app.schemas.chat import ChatRequest, ChatResponse

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(
        answer=f"你问的是：{request.message}",
        model=request.model
    )
```

访问：

```http
http://127.0.0.1:8000/docs
```

找到：

```http
POST /chat
```

点击：

```text
Try it out
```

输入：

```json
{
  "message": "什么是 AI Agent？",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

返回：

```json
{
  "answer": "你问的是：什么是 AI Agent？",
  "model": "deepseek-chat"
}
```

---

### 【重点内容】
现在我们写了第一个 POST 接口：

```python
@app.post("/chat")
```

这个接口接收一个：

```python
ChatRequest
```

返回一个：

```python
ChatResponse
```

==这就是后面 AI Chat 接口的雏形。==

大家注意这里：

```python
async def chat(request: ChatRequest):
```

因为 request 是 Pydantic 模型，所以 FastAPI 会自动把它当作请求体。

也就是说，前端传 JSON：

```json
{
  "message": "什么是 AI Agent？"
}
```

FastAPI 会自动变成：

```python
request.message
```

这就是 FastAPI + Pydantic 非常强的地方。

---

## 十七、14｜请求体校验错误
### 【操作】
在 Swagger 里测试：

```json
{
  "message": "",
  "model": "deepseek-chat",
  "temperature": 3,
  "stream": false
}
```

你会看到类似校验错误：

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character"
    },
    {
      "type": "less_than_equal",
      "loc": ["body", "temperature"],
      "msg": "Input should be less than or equal to 2"
    }
  ]
}
```

---

### 【重点内容】
这里我们故意传错参数。

```json
"message": ""
```

违反了：

```python
min_length=1
```

```json
"temperature": 3
```

违反了：

```python
le=2
```

==所以 FastAPI 自动返回了参数错误。==

这说明：

```text
Pydantic 校验
+
FastAPI 请求体解析
```

已经生效了。

我们不用自己写：

```python
if not request.message:
    return error
```

FastAPI 已经帮我们处理了基础校验。

---

## 十八、15｜response_model 是什么
### 【重点内容】
这里我们写了：

```python
@app.post("/chat", response_model=ChatResponse)
```

这个：

```python
response_model
```

表示响应模型。

它有几个作用。

第一：

```text
告诉 Swagger 这个接口返回什么结构
```

第二：

```text
对返回数据进行序列化
```

第三：

```text
过滤不应该返回的字段
```

比如我们后面用户接口里，User 模型可能有：

```text
id
name
email
password
```

但是响应模型只定义：

```text
id
name
email
```

FastAPI 就不会把 password 返回出去。

==所以企业项目里面推荐明确写 response_model。==

---

## 十九、16｜用返回类型标注响应模型
除了 `response_model`，也可以写：

```python
@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=f"你问的是：{request.message}",
        model=request.model
    )
```

---

### 【重点内容】
这里有两种写法。

第一种：

```python
@app.post("/chat", response_model=ChatResponse)
```

第二种：

```python
async def chat(request: ChatRequest) -> ChatResponse:
```

实际项目里面，两种都能看到。

我建议课程里先使用：

```python
response_model=ChatResponse
```

因为它更直观。

同时函数返回类型也可以保留：

```python
async def chat(request: ChatRequest) -> ChatResponse:
```

这样 IDE 类型提示更好。

---

## 二十、17｜模拟 ChatService
现在不要把业务逻辑都写在路由函数里。

创建：

```text
app/services/chat_service.py
```

写入：

```python
import asyncio

from app.schemas.chat import ChatRequest, ChatResponse


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    return ChatResponse(
        answer=f"AI 模拟回答：你刚才问的是「{request.message}」",
        model=request.model
    )
```

修改：

```text
app/main.py
```

```python
from fastapi import FastAPI, Query

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_with_ai

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await chat_with_ai(request)
```

---

### 【重点内容】
这里我们做了一个非常重要的工程化动作。

之前我们把逻辑直接写在路由函数里：

```python
return ChatResponse(...)
```

现在我们抽成了：

```python
chat_with_ai()
```

放在：

```text
services/chat_service.py
```

里面。

为什么要这样？

因为路由函数只应该负责：

```text
接收请求
调用业务服务
返回响应
```

不要把大量业务逻辑写在接口里面。

后面我们真正调用 LLM、RAG、Agent 时，逻辑会越来越复杂。

如果都写在：

```python
@app.post("/chat")
```

里面，代码很快就乱了。

==所以从现在开始，我们就按照企业项目方式写。==

---

## 二十一、18｜理解 Controller / Service 分层
### 【展示】
```text
前端请求
   ↓
FastAPI Router
   ↓
Service
   ↓
LLM / Database / Redis / RAG / Agent
```

---

### 【重点内容】
如果你做过 NestJS，可以这样理解：

```text
FastAPI 路由函数
≈ Controller

Service
≈ Service
```

Controller / Router 负责接收请求。

Service 负责业务逻辑。

比如后面：

```http
POST /chat
```

路由函数负责接收 ChatRequest。

然后调用：

```python
chat_service.chat_with_ai()
```

Service 里面再去调用：

```text
LLM Provider
Prompt Template
Redis
数据库
```

==所以不要让接口层变成“大杂烩”。==

---

## 二十二、19｜添加 AI 风格的 Chat 模拟逻辑
修改：

```text
app/services/chat_service.py
```

代码：

```python
import asyncio

from app.schemas.chat import ChatRequest, ChatResponse


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    if "AI Agent" in request.message:
        answer = (
            "AI Agent 可以理解为具备目标理解、任务规划、工具调用和结果反馈能力的智能体。"
        )
    elif "RAG" in request.message:
        answer = (
            "RAG 是 Retrieval Augmented Generation，也就是检索增强生成，"
            "通常用于让大模型结合企业私有知识库回答问题。"
        )
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{request.message}」。"

    return ChatResponse(
        answer=answer,
        model=request.model
    )
```

测试：

```json
{
  "message": "什么是 AI Agent？",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

返回：

```json
{
  "answer": "AI Agent 可以理解为具备目标理解、任务规划、工具调用和结果反馈能力的智能体。",
  "model": "deepseek-chat"
}
```

---

### 【重点内容】
这里我们还没有真正接入大模型。

但是我们先把接口结构跑通。

为什么要这样？

因为做项目时，不要一开始就把：

```text
FastAPI
LLM
数据库
Redis
前端
```

全部混在一起调试。

正确方式是：

```text
第一步：接口跑通
第二步：请求体校验跑通
第三步：Service 跑通
第四步：用假数据模拟返回
第五步：再替换成真实 LLM 调用
```

这是一种非常重要的开发习惯。

---

## 二十三、20｜创建 APIRouter
现在我们把接口拆出来。

创建目录：

```bash
mkdir -p app/api/v1
```

Windows：

```powershell
mkdir app\api
mkdir app\api\v1
```

创建文件：

```text
app/api/__init__.py
app/api/v1/__init__.py
app/api/v1/health.py
app/api/v1/chat.py
```

---

### `app/api/v1/health.py`
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-agent-course",
        "version": "0.1.0"
    }
```

---

### `app/api/v1/chat.py`
```python
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await chat_with_ai(request)
```

---

### 修改 `app/main.py`
```python
from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])


@app.get("/")
async def root():
    return {
        "message": "AI Agent Course API"
    }
```

访问：

```http
http://127.0.0.1:8000/api/v1/health
```

访问 Swagger：

```http
http://127.0.0.1:8000/docs
```

---

### 【重点内容】
现在我们开始拆分路由。

在小 Demo 里面，所有代码写在：

```text
main.py
```

没问题。

但是项目稍微一大，就会出现：

```text
main.py 几百行
接口全部混在一起
无法维护
```

==所以 FastAPI 提供了：==

```python
APIRouter
```

我们可以把健康检查接口放到：

```text
health.py
```

把聊天接口放到：

```text
chat.py
```

最后在：

```text
main.py
```

里面统一注册。

这就类似 NestJS 里面的 Controller 拆分。

---

## 二十四、21｜prefix 和 tags 的作用
### 【重点内容】
这里我们写了：

```python
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
```

其中：

```python
prefix="/api/v1"
```

表示这个 router 下面的所有接口，都加上统一前缀。

所以：

```python
@router.get("/health")
```

最终变成：

```text
/api/v1/health
```

这里：

```python
tags=["Health"]
```

表示 Swagger 文档里的分组。

这样接口多了之后，文档不会全部混在一起。

后面我们可能会有：

```text
Health
Chat
RAG
Agent
Tool
MCP
User
Auth
```

这些分组。

---

## 二十五、22｜接口版本为什么用 /api/v1
### 【重点内容】
企业项目里通常会给 API 加版本号。

比如：

```text
/api/v1/chat
/api/v2/chat
```

为什么？

因为接口一旦上线，就会有前端、移动端、第三方系统依赖它。

如果后面接口结构发生变化，不能随便破坏老版本。

==所以可以通过版本号隔离：==

```text
v1 老接口继续兼容
v2 新接口逐步升级
```

我们这门课从一开始就使用：

```text
/api/v1
```

这是为了让项目更接近真实企业开发。

---

## 二十六、23｜统一响应结构
很多企业项目会统一返回格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

创建：

```text
app/schemas/response.py
```

写入：

```python
from typing import Any
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: Any = Field(default=None, description="响应数据")
```

修改 `chat.py`：

```python
from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.schemas.response import ApiResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ApiResponse)
async def chat(request: ChatRequest) -> ApiResponse:
    result = await chat_with_ai(request)

    return ApiResponse(
        data=result.model_dump()
    )
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "AI Agent 可以理解为具备目标理解、任务规划、工具调用和结果反馈能力的智能体。",
    "model": "deepseek-chat"
  }
}
```

---

### 【重点内容】
企业项目里面经常会有统一响应格式。

比如：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

这样前端处理起来比较统一。

但是这里我要提醒一点。

统一响应格式有优点，也有一些争议。

因为 REST API 本身也可以通过 HTTP 状态码表达成功和失败。

比如：

```text
200
400
401
404
500
```

但是国内很多业务系统依然喜欢统一格式。

==所以我们课程里会先采用这种方式，方便前后端理解。==

后面讲异常处理的时候，我们会进一步优化。

---

## 二十七、24｜基础异常处理 HTTPException
修改 `chat_service.py`：

```python
import asyncio
from fastapi import HTTPException

from app.schemas.chat import ChatRequest, ChatResponse


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

    if request.model not in supported_models:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模型：{request.model}"
        )

    if "AI Agent" in request.message:
        answer = "AI Agent 可以理解为具备目标理解、任务规划、工具调用和结果反馈能力的智能体。"
    elif "RAG" in request.message:
        answer = "RAG 是检索增强生成，通常用于让大模型结合企业私有知识库回答问题。"
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{request.message}」。"

    return ChatResponse(
        answer=answer,
        model=request.model
    )
```

测试：

```json
{
  "message": "你好",
  "model": "unknown-model",
  "temperature": 0.7,
  "stream": false
}
```

返回：

```json
{
  "detail": "不支持的模型：unknown-model"
}
```

---

### 【重点内容】
这里我们第一次使用：

```python
HTTPException
```

它可以直接返回 HTTP 错误。

比如：

```python
raise HTTPException(status_code=400, detail="不支持的模型")
```

FastAPI 会自动返回：

```text
400 Bad Request
```

以及错误信息。

后面我们会专门讲全局异常处理。

这一章先知道：

**如果接口里面遇到明确的请求错误，可以先用 HTTPException。**

---

## 二十八、25｜把模型校验放回 Pydantic
==不过更推荐把模型校验放到 Pydantic 里面。==

修改：

```text
app/schemas/chat.py
```

```python
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=False, description="是否流式输出")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
```

---

### 【重点内容】
这里大家注意一个分层问题。

如果是参数格式或者字段规则错误，比如：

```text
message 不能为空
temperature 不能超过 2
model 必须是支持的模型
```

这些更适合放在 Pydantic 模型里校验。

因为这是请求体本身的规则。

如果是业务执行过程中的错误，比如：

```text
用户不存在
知识库不存在
订单不存在
权限不足
```

这些更适合在 Service 里面抛业务异常。

这就是：

```text
数据校验
和
业务校验
```

的区别。

---

## 二十九、26｜完整代码：app/schemas/chat.py
```python
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度")
    stream: bool = Field(default=False, description="是否流式输出")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        supported_models = ["deepseek-chat", "qwen-plus", "gpt-4o-mini"]

        if value not in supported_models:
            raise ValueError(f"不支持的模型：{value}")

        return value


class ChatResponse(BaseModel):
    answer: str = Field(..., description="AI 回答")
    model: str = Field(..., description="模型名称")
```

---

## 三十、27｜完整代码：app/services/chat_service.py
```python
import asyncio

from app.schemas.chat import ChatRequest, ChatResponse


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    await asyncio.sleep(0.5)

    if "AI Agent" in request.message:
        answer = "AI Agent 可以理解为具备目标理解、任务规划、工具调用和结果反馈能力的智能体。"
    elif "RAG" in request.message:
        answer = "RAG 是 Retrieval Augmented Generation，也就是检索增强生成，通常用于让大模型结合企业私有知识库回答问题。"
    elif "LangGraph" in request.message:
        answer = "LangGraph 适合用来开发有状态、有流程控制、有条件分支的复杂 Agent。"
    else:
        answer = f"这是一个模拟回答：你刚才问的是「{request.message}」。"

    return ChatResponse(
        answer=answer,
        model=request.model
    )
```

---

## 三十一、28｜完整代码：app/api/v1/chat.py
```python
from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.schemas.response import ApiResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ApiResponse)
async def chat(request: ChatRequest) -> ApiResponse:
    result = await chat_with_ai(request)

    return ApiResponse(
        data=result.model_dump()
    )
```

---

## 三十二、29｜完整代码：app/api/v1/health.py
```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-agent-course",
        "version": "0.1.0"
    }
```

---

## 三十三、30｜完整代码：app/schemas/response.py
```python
from typing import Any
from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    code: int = Field(default=0, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: Any = Field(default=None, description="响应数据")
```

---

## 三十四、31｜完整代码：app/main.py
```python
from fastapi import FastAPI

from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router

app = FastAPI(
    title="AI Agent Course API",
    description="Python + FastAPI + LLM + Agent 开发实战",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])


@app.get("/")
async def root():
    return {
        "message": "AI Agent Course API"
    }
```

---

## 三十五、32｜测试完整接口
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

访问：

```http
http://127.0.0.1:8000
```

返回：

```json
{
  "message": "AI Agent Course API"
}
```

访问：

```http
http://127.0.0.1:8000/api/v1/health
```

返回：

```json
{
  "status": "ok",
  "service": "ai-agent-course",
  "version": "0.1.0"
}
```

访问 Swagger：

```http
http://127.0.0.1:8000/docs
```

测试：

```http
POST /api/v1/chat
```

请求：

```json
{
  "message": "什么是 LangGraph？",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "LangGraph 适合用来开发有状态、有流程控制、有条件分支的复杂 Agent。",
    "model": "deepseek-chat"
  }
}
```

---

## 三十六、33｜用 curl 测试接口
除了 Swagger，也可以用 curl。

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Chat 接口：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "什么是 AI Agent？",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false
  }'
```

---

### 【重点内容】
Swagger 很适合开发调试。

但是后面真实项目里，我们也会经常用：

```text
curl
Postman
Apifox
前端代码
```

来调用接口。

==所以这里我们也演示一下 curl。==

如果接口能在 Swagger 和 curl 里都正常返回，说明后端服务已经正常。

---

## 三十七、34｜使用 Python requests 测试接口
安装：

```bash
uv add requests
```

创建：

```text
tests/test_chat_api.py
```

写入：

```python
import requests


url = "http://127.0.0.1:8000/api/v1/chat"

payload = {
    "message": "什么是 RAG？",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": False
}

response = requests.post(url, json=payload)

print(response.status_code)
print(response.json())
```

运行前确保 FastAPI 服务正在启动。

然后执行：

```bash
python tests/test_chat_api.py
```

---

### 【重点内容】
这个脚本模拟了一个客户端请求。

也就是说，FastAPI 服务启动后，其他程序可以通过 HTTP 调用它。

后面前端页面、移动端、小程序，都是这么调用。

我们现在用 Python requests 模拟一下。

当然，后面真正做异步客户端时，我们也可以用：

```text
httpx
```

这一章先知道接口是可以被外部程序调用的。

---

## 三十八、35｜常见错误一：ModuleNotFoundError

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
ModuleNotFoundError: No module named 'app'
```

常见原因：

```text
没有在项目根目录运行
命令路径不对
缺少 __init__.py
```

解决：

确保在：

```text
ai-agent-course
```

项目根目录执行：

```bash
uv run uvicorn app.main:app --reload
```

确认存在：

```text
app/__init__.py
app/api/__init__.py
app/api/v1/__init__.py
```

---

## 三十九、36｜常见错误二：端口被占用
错误：

```text
Address already in use
```

说明：

```text
8000 端口已经被占用
```

解决：

换端口：

```bash
uv run uvicorn app.main:app --reload --port 8001
```

访问：

```http
http://127.0.0.1:8001
```

---

## 四十、37｜常见错误三：忘记安装依赖

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
ModuleNotFoundError: No module named 'fastapi'
```

解决：

```bash
uv add fastapi
uv add "uvicorn[standard]"
```

或者：

```bash
pip install fastapi "uvicorn[standard]"
```

确认虚拟环境已激活。

---

## 四十一、38｜常见错误四：请求体字段写错
错误请求：

```json
{
  "msg": "你好"
}
```

但是后端模型要求：

```python
message: str
```

所以会返回 422。

正确请求：

```json
{
  "message": "你好"
}
```

---

### 【重点内容】
422 是 FastAPI 里非常常见的错误。

它通常表示：

```text
请求参数校验失败
```

比如：

```text
字段缺失
字段类型错误
字段范围不符合规则
字段长度不符合规则
```

遇到 422，不要慌。

先看返回的 detail，里面会告诉你具体哪个字段有问题。

---

## 四十二、39｜常见错误五：async 函数忘记 await

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    result = chat_with_ai(request)
    return ApiResponse(data=result.model_dump())
```

这里：

```python
chat_with_ai(request)
```

返回的是 coroutine，不是结果。

正确：

```python
@router.post("/chat")
async def chat(request: ChatRequest):
    result = await chat_with_ai(request)
    return ApiResponse(data=result.model_dump())
```

---

### 【重点内容】
这个错误和上一章异步编程直接相关。

只要函数定义是：

```python
async def chat_with_ai()
```

调用时就要：

```python
await chat_with_ai()
```

否则你拿到的是协程对象，不是真正结果。

---

## 四十三、40｜本章知识点和 AI 开发场景对应表
| FastAPI 知识点 | AI 开发场景 |
| --- | --- |
| `FastAPI()` | 创建 AI 后端应用 |
| `@app.get()` | 健康检查、配置查询、模型列表 |
| `@app.post()` | Chat、RAG、Agent、Tool 调用 |
| Path 参数 | 查询某个会话、知识库、Agent |
| Query 参数 | 搜索关键词、分页、Top K |
| Pydantic 请求体 | ChatRequest、AgentRunRequest |
| Response Model | ChatResponse、RAGResponse |
| Swagger `/docs` | 前后端联调、接口测试 |
| `async def` | 异步调用 LLM、数据库、Redis |
| `APIRouter` | 拆分 Chat / RAG / Agent 模块 |
| `prefix` | API 版本管理 |
| `tags` | Swagger 接口分组 |
| Service 分层 | 路由和业务逻辑解耦 |
| HTTPException | 基础错误处理 |
| 统一响应结构 | 前端统一处理接口结果 |


---

## 四十四、41｜本章完整复习
这一章我们完成了 FastAPI 快速入门。

完整路线是：

```text
安装 FastAPI / Uvicorn
 ↓
创建 app = FastAPI()
 ↓
编写 GET /
 ↓
启动 uvicorn
 ↓
访问 /docs
 ↓
编写 /health
 ↓
学习 Path 参数
 ↓
学习 Query 参数
 ↓
学习 POST 请求体
 ↓
Pydantic 请求校验
 ↓
Response Model
 ↓
抽离 ChatService
 ↓
拆分 APIRouter
 ↓
统一 /api/v1 前缀
 ↓
统一响应结构
 ↓
基础异常处理
 ↓
完成 /api/v1/chat 接口雏形
```

现在我们的项目已经具备了一个 AI 后端的基础形态：

```text
FastAPI
 ↓
Router
 ↓
Schema
 ↓
Service
 ↓
模拟 AI 回答
```

下一步，我们会继续把这个项目工程化。

---

## 四十五、42｜课后任务一：新增 /api/v1/models 接口
要求：

```text
1. 创建 app/api/v1/models.py
2. 使用 APIRouter
3. 返回支持的模型列表
4. 注册到 main.py
5. Swagger 中显示 Models 分组
```

参考答案：

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/models")
async def list_models():
    return {
        "models": [
            "deepseek-chat",
            "qwen-plus",
            "gpt-4o-mini"
        ]
    }
```

`main.py` 注册：

```python
from app.api.v1.models import router as models_router

app.include_router(models_router, prefix="/api/v1", tags=["Models"])
```

---

## 四十六、43｜课后任务二：新增 /api/v1/chat/simple
要求：

```text
1. 接收 Query 参数 message
2. message 必填
3. 长度 1 到 200
4. 返回模拟回答
```

参考答案：

```python
from fastapi import Query


@router.get("/chat/simple")
async def simple_chat(
    message: str = Query(..., min_length=1, max_length=200)
):
    return {
        "answer": f"你问的是：{message}"
    }
```

---

## 四十七、44｜课后任务三：新增会话查询接口
要求：

```text
1. GET /api/v1/conversations/{conversation_id}
2. conversation_id 是字符串
3. 返回会话 ID 和模拟消息列表
```

参考答案：

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": "user",
                "content": "什么是 AI Agent？"
            },
            {
                "role": "assistant",
                "content": "AI Agent 是可以调用工具完成任务的智能体。"
            }
        ]
    }
```

---

## 四十八、45｜课后任务四：给 ChatRequest 增加 session_id
要求：

```text
1. session_id 可以为空
2. 如果为空，后端返回 None
3. 如果传入，响应里返回 session_id
```

参考答案：

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    model: str = "deepseek-chat"
    temperature: float = Field(default=0.7, ge=0, le=2)
    stream: bool = False
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    model: str
    session_id: str | None = None
```

Service：

```python
return ChatResponse(
    answer=answer,
    model=request.model,
    session_id=request.session_id
)
```

---

## 四十九、46｜课后任务五：错误请求测试
使用 Swagger 或 curl 测试以下错误：

```json
{
  "message": "",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "stream": false
}
```

观察：

```text
message 长度错误
```

再测试：

```json
{
  "message": "你好",
  "model": "unknown-model",
  "temperature": 0.7,
  "stream": false
}
```

观察：

```text
model 校验错误
```

---

## 五十、47｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 06 章我们就讲完了。

这一章我们正式进入了 FastAPI。

==大家现在要记住的是，FastAPI 不是孤立学习的。==

它和我们前面几章的内容是连在一起的。

```text
Python 基础
 ↓
写业务逻辑

Pydantic
 ↓
定义请求体和响应体

async / await
 ↓
异步调用 LLM、数据库、Redis、Tool

FastAPI
 ↓
把这些能力暴露成 HTTP API
```

这一章我们完成了：

```http
GET /
GET /api/v1/health
GET /users/{user_id}
GET /search
POST /api/v1/chat
```

同时我们也完成了一个比较重要的工程化拆分：

```text
main.py
 ↓
api/v1/chat.py
 ↓
schemas/chat.py
 ↓
services/chat_service.py
```

这就是后面企业级 AI 项目的基本雏形。

现在我们的 Chat 接口还是模拟回答。

下一阶段，我们会继续往里面加入真正的大模型调用。

但是在这之前，我们还需要继续完善 FastAPI 的核心能力，比如：

```text
请求参数与响应模型
Router 分层
Dependency Injection
Middleware
异常处理
日志
跨域
```

这些都是企业级后端必须具备的能力。

下一章，我们进入：

## 第 07 章｜Pydantic 请求参数与响应模型
这一章会继续强化：

```text
Request Model
Response Model
嵌套模型
列表模型
错误响应
统一响应结构
前后端字段命名
Swagger 文档
```

学完之后，我们的接口定义会更加标准，也更接近真实企业项目。

---

> [!success] 一句话带走
> ==把类型写清楚，FastAPI 就顺手把校验、文档、序列化全做了。==

> [!quote] 关于本文档
> 由原始讲义 `第 06 章｜FastAPI 快速入门.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
