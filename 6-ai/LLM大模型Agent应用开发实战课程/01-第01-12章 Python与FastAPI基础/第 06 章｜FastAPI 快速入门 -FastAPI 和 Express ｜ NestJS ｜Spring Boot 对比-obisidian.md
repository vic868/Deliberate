---
title: "第 06 章补充｜FastAPI 与 Express / NestJS / Spring Boot 对比"
chapter: "06"
source: "第 06 章｜FastAPI 快速入门 -FastAPI 和 Express ｜ NestJS ｜Spring Boot 对比.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - 框架对比
---

# 第 06 章补充｜FastAPI 与 Express / NestJS / Spring Boot 对比

> [!abstract] 本章重点
>
> - ==本质上是同一件事== — Express / NestJS / Spring Boot / FastAPI 都是收请求、走逻辑、返响应。
> - ==装饰器对标注解== — FastAPI 的 @app.get 类似 Spring Boot 的 @GetMapping。
> - ==Pydantic 对标 DTO / class-validator== — 都是用类型描述请求和响应长什么样。
> - ==依赖注入对标 Spring DI / NestJS Provider== — 公共逻辑交给框架注入，而不是每个接口手写一遍。
>
> [!note] 大白话
>
> - **Swagger**：自动生成的可点接口文档，FastAPI 自带。
>
> [!info] 导航与来源
> - 原始讲义：[[第 06 章｜FastAPI 快速入门 -FastAPI 和 Express ｜ NestJS ｜Spring Boot 对比|打开原始讲义]]
> - [[第 05 章｜Python 异步编程 async ｜ await|上一章｜第 05 章]]
> - [[第 07 章｜Pydantic 请求参数与响应模型|下一章｜第 07 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#十、07｜FastAPI 和 Express / NestJS / Spring Boot 对比]]

---
## 十、07｜FastAPI 和 Express / NestJS / Spring Boot 对比
### 【展示】
| <font style="color:#FFFFFF;">后端能力</font> | <font style="color:#FFFFFF;">Express</font> | <font style="color:#FFFFFF;">NestJS</font> | <font style="color:#FFFFFF;">Spring Boot</font> | <font style="color:#FFFFFF;">FastAPI</font> |
| --- | --- | --- | --- | --- |
| 语言 | JavaScript / TypeScript | TypeScript | Java | Python |
| 应用入口 | `const app = express()` | `NestFactory.create()` | `@SpringBootApplication` | `app = FastAPI()` |
| GET 路由 | `app.get()` | `@Get()` | `@GetMapping()` | `@app.get()` |
| POST 路由 | `app.post()` | `@Post()` | `@PostMapping()` | `@app.post()` |
| Controller | 手动组织 Router | `@Controller()` | `@RestController` | `APIRouter` / 路由函数 |
| Service | 手动封装 | `@Injectable()` | `@Service` | 普通 Python 函数 / Class |
| DTO / 请求体 | 手动解析 | DTO + class-validator | DTO / VO / POJO | Pydantic BaseModel |
| 参数校验 | 手动 / 中间件 | class-validator | Bean Validation：`@Valid`、`@NotNull` | Pydantic / Field |
| 依赖注入 | 无内置 DI | 内置 DI | Spring IoC / DI | Depends |
| 接口文档 | 额外配置 Swagger | Swagger 模块 | SpringDoc / Swagger | 自动 OpenAPI / Swagger |
| 异步能力 | Promise / async-await | Promise / async-await | CompletableFuture / WebFlux | async / await |
| 路由拆分 | Router | Module / Controller | Controller 分层 | APIRouter |
| ORM | Prisma / Sequelize | Prisma / TypeORM | MyBatis / JPA / Hibernate | SQLAlchemy |
| 配置管理 | `.env` / config | ConfigModule | `application.yml` | `.env` / Settings |
| 启动方式 | `node app.js` | `npm run start` | `java -jar` / Maven / Gradle | `uvicorn app.main:app` |
| 典型使用场景 | 轻量 API | 企业 Node 后端 | 企业 Java 后端 | AI 应用 / 异步 API / LLM 后端 |


---

### 【课程核心重点】
这一节我们做一个对比。

因为我们这门课的学员，可能有前端同学，也可能有 Node.js 后端同学，也可能有 Java Spring Boot 后端同学。

==所以大家不要一看到 FastAPI 就觉得是一个完全陌生的东西。==

其实从后端框架的职责上看，它们解决的问题是类似的。

不管是 Express、NestJS、Spring Boot，还是 FastAPI，本质上都是在解决：

```latex
接收 HTTP 请求
解析请求参数
校验数据
调用业务逻辑
返回响应结果
组织项目结构
生成接口文档
处理异常
管理配置
```

只是不同技术栈的写法不一样。

---

### 1. Express 和 FastAPI 对比
如果你写过 Express，可能会写：

```javascript
import express from "express";

const app = express();

app.get("/", (req, res) => {
  res.json({
    message: "hello"
  });
});

app.listen(3000);
```

FastAPI 里面类似：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "message": "hello"
    }
```

你会发现，它们的核心思想是一样的：

```text
定义应用
 ↓
定义路由
 ↓
处理请求
 ↓
返回 JSON
```

只不过 Express 是：

```text
app.get("/", handler)
```

FastAPI 是：

```python
@app.get("/")
async def root():
```

FastAPI 这种写法使用的是 Python 的装饰器。

---

### 2. NestJS 和 FastAPI 对比
如果你写过 NestJS，你可能会写：

```typescript
import { Controller, Get } from "@nestjs/common";

@Controller("users")
  export class UserController {
    @Get()
    findAll() {
      return {
        message: "users"
      };
    }
  }
```

FastAPI 里面可以用 `APIRouter` 实现类似拆分：

```python

from fastapi import APIRouter

router = APIRouter()


@router.get("/users")
async def get_users():
    return {
        "message": "users"
    }
```

NestJS 里面有：

```text
Controller
Service
Module
DTO
Dependency Injection
```

FastAPI 里面也可以有类似分层：

```text
api / router
service
schemas
models
dependencies
```

比如：

```markdown
app/
├── api/
│   └── v1/
│       └── chat.py
├── services/
│   └── chat_service.py
├── schemas/
│   └── chat.py
└── main.py
```

这就和 NestJS 的工程化思路很接近。

---

### 3. Spring Boot 和 FastAPI 对比
如果你是 Java 后端，熟悉 Spring Boot，你可能会写：

```java
@RestController
@RequestMapping("/api/v1")
public class ChatController {

    @PostMapping("/chat")
    public ChatResponse chat(@RequestBody ChatRequest request) {
        return chatService.chat(request);
    }
}
```

FastAPI 里面类似：

```python
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_with_ai

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await chat_with_ai(request)
```

大家看一下，它们其实是一一对应的。

Spring Boot 里面：

```text
@RestController
```

对应 FastAPI 里面：

```text
APIRouter
```

Spring Boot 里面：

```text
@PostMapping("/chat")
```

对应 FastAPI：

```text
@router.post("/chat")
```

Spring Boot 里面：

```text
@RequestBody ChatRequest request
```

对应 FastAPI：

```text
request: ChatRequest
```

Spring Boot 里面：

```text
ChatResponse
```

对应 FastAPI：

```text
ChatResponse
```

==所以如果你之前是 Java Spring Boot 开发者，可以这样理解：==

```markdown

Spring Boot Controller
≈
FastAPI Router

Spring Boot Service
≈
Python Service 函数 / Service 类

Java DTO / VO
≈
Pydantic BaseModel

Bean Validation
≈
Pydantic Field / Validator

application.yml
≈
.env / Settings

SpringDoc Swagger
≈
FastAPI 自动 Swagger
```

---

### 4. Spring Boot DTO 和 Pydantic 对比
Spring Boot 里面，我们经常定义 DTO：

```javascript
public class ChatRequest {

  @NotBlank(message = "消息不能为空")
  private String message;

  private String model = "deepseek-chat";

  @Min(0)
  @Max(2)
  private Double temperature = 0.7;

  // getter / setter
}
```

FastAPI + Pydantic 里面写：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")
    model: str = Field(default="deepseek-chat", description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="模型温度")
```

这两个解决的问题是一样的：

```text
定义请求体结构
 ↓
校验字段类型
 ↓
校验字段规则
 ↓
生成接口文档
```

但是 Python + Pydantic 写起来会更简洁。

Java 里面需要写：

```markdown
class
字段
注解
getter / setter
构造方法
```

Python 里面用 Pydantic：

```markdown
class ChatRequest(BaseModel):
    message: str
```

就可以快速完成数据建模。

---

### 5. Spring Boot Service 和 Python Service 对比
Spring Boot 里面一般会写：

```java
@Service
public class ChatService {

    public ChatResponse chat(ChatRequest request) {
        return new ChatResponse("你问的是：" + request.getMessage());
    }
}
```

FastAPI 项目里，我们可以写：

```python
from app.schemas.chat import ChatRequest, ChatResponse


async def chat_with_ai(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        answer=f"你问的是：{request.message}",
        model=request.model
    )
```

Spring Boot 强调：

```text
Controller
 ↓
Service
 ↓
Repository
```

FastAPI 项目里我们也可以这样设计：

```text
Router
 ↓
Service
 ↓
Repository / LLM Provider / Tool / RAG
```

也就是说，FastAPI 虽然看起来很轻量，但是一样可以做企业级分层。

---

### 6. 为什么 AI 后端更适合 FastAPI
==这里大家要理解一个重点。==

Spring Boot 非常适合传统企业后端，比如：

```text
ERP
CRM
OA
订单系统
支付系统
权限系统
```

但是 AI 应用有一些新的特点：

```text
大量调用 LLM API
大量异步 IO
需要流式输出
需要快速定义请求和响应模型
需要快速生成接口文档
需要和 Python AI 生态集成
```

比如后面我们会用到：

```text
LangChain
LangGraph
DeepAgents
Embedding
Rerank
RAG
Vector Database
MCP
```

这些 AI 生态工具，Python 支持会更自然。

所以对于 AI 应用后端来说，FastAPI 有几个优势：

```text
1. 和 Python AI 生态结合非常顺
2. Pydantic 数据建模非常适合 LLM 输入输出
3. async / await 适合调用大模型、数据库、Redis、向量库
4. 自动 Swagger 方便前后端联调
5. 写法简洁，开发效率高
6. 适合快速构建 AI Chat、RAG、Agent 接口
```

所以我们这门课选择：

```text
Python + FastAPI
```

作为 AI Agent 后端技术栈。

---

### 7. 最后总结一下
大家可以这样对比：

```text
如果你是前端 / Node.js 开发：
FastAPI 可以类比 Express / NestJS。

如果你是 Java 后端开发：
FastAPI 可以类比 Spring Boot。

如果你是 AI 应用开发：
FastAPI 是 Python AI 生态里非常适合做后端 API 的框架。
```

但是要注意：

类比只是为了帮助理解，不代表它们完全一样。

FastAPI 最大的优势在于：

```text
Python 生态
Pydantic
异步能力
自动文档
AI 框架集成
```

后面我们会基于 FastAPI 一步一步开发：

```text
AI Chat
流式对话
RAG 知识库
Agent 接口
Tool Calling
MCP
Multi-Agent
```

==所以从这一章开始，大家要把 FastAPI 理解成：==

**整个 AI Agent 平台的后端入口。**

---

> [!success] 一句话带走
> ==换个框架，变的是写法，不变的是分层和请求生命周期。==

> [!quote] 关于本文档
> 由原始讲义 `第 06 章｜FastAPI 快速入门 -FastAPI 和 Express ｜ NestJS ｜Spring Boot 对比.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
