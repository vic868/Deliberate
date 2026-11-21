---
title: "第 11 章｜PostgreSQL + SQLAlchemy 数据库开发"
chapter: "11"
source: "第 11 章｜PostgreSQL + SQLAlchemy 数据库开发.md"
type: obsidian-note
created: 2026-11-21
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - postgresql
  - sqlalchemy
---

# 第 11 章｜PostgreSQL + SQLAlchemy 数据库开发

> [!abstract] 本章重点
>
> - ==PostgreSQL 存业务数据，是 AI 后端的底座== — 会话、消息、用户信息都要落库。
> - ==连接字符串统一放 Settings== — 地址、账号、密码不散落在代码里。
> - ==SQLAlchemy + asyncpg 走异步 ORM== — 和 FastAPI 的 async 路线保持一致。
> - ==Session 通过依赖注入管理== — 每个请求一个会话，用完自动关。
> - ==同步 ORM 与异步 ORM 差在驱动和 await== — 业务写法接近，但 I/O 行为不同。
>
> [!note] 大白话
>
> - **Session**：和数据库打交道的「一次会话」，事务和连接都挂在它身上。
> - **pgvector**：给 PostgreSQL 加向量检索能力的扩展，后面 RAG 阶段再引入。
>
> [!info] 导航与来源
> - 原始讲义：[[第 11 章｜PostgreSQL + SQLAlchemy 数据库开发|打开原始讲义]]
> - [[第 10 章｜Middleware、异常处理与日志|上一章｜第 10 章]]
> - [[第 12 章｜Redis 在 AI 应用中的使用|下一章｜第 12 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#五、02｜为什么 AI 后端需要 PostgreSQL]]
- [[#六、03｜PostgreSQL 安装方式总览]]
- [[#七、04｜方式一：Windows 安装 PostgreSQL]]
- [[#八、05｜方式二：macOS 安装 PostgreSQL]]
- [[#九、06｜方式三：Docker Compose 安装 PostgreSQL]]
- [[#十、07｜为什么这里不用 pgvector 镜像]]
- [[#十一、08｜PostgreSQL 客户端工具推荐]]
- [[#十二、09｜用 DBeaver 连接 PostgreSQL]]
- [[#十三、10｜创建数据库和用户]]
- [[#十四、11｜配置数据库连接字符串]]

---
---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面我们已经完成了 FastAPI 企业级后端的基础骨架：

```text
第 06 章｜FastAPI 快速入门
第 07 章｜Pydantic 请求参数与响应模型
第 08 章｜FastAPI Router 与项目工程化
第 09 章｜FastAPI Dependency Injection 依赖注入
第 10 章｜Middleware、异常处理与日志
```

目前项目已经具备：

```text
Router
Dependency
Service
Repository
Middleware
Exception Handler
Logger
trace_id
```

==但是现在还有一个核心问题：==

**所有数据都是假的。**

比如：

```text
会话数据是假数据
消息数据是假数据
知识库数据是假数据
用户数据是假数据
Agent 配置是假数据
```

现在我们要正式接入数据库。

这一章选择：

```text
PostgreSQL
+
SQLAlchemy
+
AsyncSession
```

原因很简单：

```text
PostgreSQL 是企业级后端非常常见的关系型数据库
SQLAlchemy 是 Python 生态非常主流的 ORM
FastAPI 项目天然适合使用 async / await
后面 RAG 阶段还会继续用 PostgreSQL + pgvector
```

这一章完成以后，我们的项目会从：

```text
内存假数据
```

升级成：

```text
真正可以持久化会话和消息的 AI Chat 后端
```

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```text
1. 为什么 AI 后端需要数据库
2. PostgreSQL 在 AI Agent 项目中的作用
3. PostgreSQL 如何安装
4. PostgreSQL 常用客户端工具如何选择
5. 如何用命令行连接 PostgreSQL
6. 如何创建数据库和用户
7. SQLAlchemy 是什么
8. ORM 是什么
9. 同步 ORM 和异步 ORM 的区别
10. asyncpg 是什么
11. 如何配置 DATABASE_URL
12. 如何创建 Async Engine
13. 如何创建 AsyncSession
14. 如何使用 Depends 注入数据库 Session
15. 如何定义 SQLAlchemy Base
16. 如何定义 User / Conversation / Message 数据库模型
17. 如何创建数据库表
18. 如何编写 Repository
19. 如何把内存 Repository 替换成数据库 Repository
20. 如何在 Chat 接口里保存消息
21. 如何查询会话消息
22. 如何处理数据库异常
23. 如何排查数据库连接问题
```

---

## 三、本章最终项目结构
本章结束后，项目结构会升级成：

```text
ai-agent-course/
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       ├── health.py
│   │       ├── chat.py
│   │       ├── conversations.py
│   │       ├── models.py
│   │       ├── agents.py
│   │       └── rag.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── exception_handlers.py
│   │   ├── logging.py
│   │   ├── middleware.py
│   │   └── request_context.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── dependencies/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── llm.py
│   │   └── settings.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── message.py
│   │
│   ├── schemas/
│   │   ├── response.py
│   │   ├── chat.py
│   │   ├── conversation.py
│   │   ├── rag.py
│   │   └── user.py
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── conversation_service.py
│   │   └── rag_service.py
│   │
│   └── repositories/
│       ├── conversation_repository.py
│       └── knowledge_repository.py
│
├── scripts/
│   ├── create_tables.py
│   └── test_db.py
│
├── docker-compose.yml
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

本章重点新增：

```text
app/db/
app/models/user.py
app/models/conversation.py
app/models/message.py
scripts/create_tables.py
scripts/test_db.py
docker-compose.yml
```

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 11 章。

从这一章开始，我们正式进入数据库开发。

前面我们已经把 FastAPI 的基础架构搭好了。

但是目前我们所有数据都是写死的。

比如创建会话：

```python
conversation_id = "c_xxxxx"
```

获取消息：

```python
messages = [
    ChatMessage(role="user", content="什么是 AI Agent？")
]
```

这些只是为了跑通接口。

真实项目肯定不能这样。

用户创建的会话要存起来。

用户发的消息要存起来。

AI 回复也要存起来。

后面还要存：

```text
用户信息
知识库信息
文档信息
Agent 配置
Tool 调用记录
Token 消耗记录
Trace 日志
```

==所以数据库是后端项目的核心基础。==

这一章我们会使用：

```text
PostgreSQL
+
SQLAlchemy
+
AsyncSession
```

完成一个真实的数据库接入。

到这一章结束时，我们会把：

```text
内存会话数据
```

替换成：

```text
PostgreSQL 真实数据
```

---

## 五、02｜为什么 AI 后端需要 PostgreSQL
### 【重点内容】
AI 应用不是只有大模型。

一个企业级 AI 应用，背后一定有大量业务数据。

比如 AI Chat 需要存：

```text
conversation
message
user
model
token_usage
```

RAG 需要存：

```text
knowledge_base
document
chunk
embedding_task
retrieval_log
```

Agent 需要存：

```text
agent_config
agent_run
agent_step
tool_call
memory
```

平台能力还需要存：

```text
organization
workspace
api_key
permission
billing
audit_log
```

==所以我们需要一个稳定的关系型数据库。==

PostgreSQL 的优势是：

```text
稳定
开源
生态成熟
支持 JSON / JSONB
支持全文检索
支持扩展
后面可以配合 pgvector 做向量检索
```

所以这门课选择 PostgreSQL 作为主数据库。

---

## 六、03｜PostgreSQL 安装方式总览
### 【实操】
```bash
PostgreSQL 安装方式

1. Windows 安装包
2. macOS Homebrew / 官方安装包
3. Linux apt / yum
4. Docker Compose
```

---

### 【重点内容】
PostgreSQL 有多种安装方式。

如果你是 Windows 用户，最简单的是使用 PostgreSQL 官方下载页推荐的 Windows installer，这个安装器由 EDB 托管。

如果你是 macOS 用户，可以用 Homebrew，也可以从 PostgreSQL 官方 macOS 下载页选择安装包。

如果你已经熟悉 Docker，我最推荐课程统一使用 Docker Compose。

因为 Docker 方式有几个优点：

```text
安装简单
环境一致
方便删除重建
方便和 Redis / pgAdmin 一起跑
适合课程教学
```

但是很多学员不一定熟悉 Docker，所以这一章会同时讲：

```bash
Windows 图形安装
macOS 安装
Docker Compose 安装
```

---

## 七、04｜方式一：Windows 安装 PostgreSQL
### 【安装步骤】
#### 第一步：下载 PostgreSQL Installer
打开 PostgreSQL 官方 Windows 下载页。

选择：

```text
Download the installer
```

这个 installer 是由 EDB 托管的 PostgreSQL 图形安装程序。

---

#### 第二步：运行安装程序
双击安装包。

一路点击：

```text
Next
```

---

#### 第三步：选择安装目录
可以保持默认：

```text
C:\Program Files\PostgreSQL\16
```

或者：

```text
C:\Program Files\PostgreSQL\17
```

==课程里不要纠结版本，建议固定使用一个稳定版本，比如 16 或 17。==

---

#### 第四步：选择组件
勾选：

```text
PostgreSQL Server
pgAdmin 4
Command Line Tools
```

其中：

```text
PostgreSQL Server
= 数据库服务

pgAdmin 4
= 图形化管理工具

Command Line Tools
= psql 命令行工具
```

---

#### 第五步：设置数据目录
保持默认即可。

比如：

```text
C:\Program Files\PostgreSQL\16\data
```

---

#### 第六步：设置 postgres 用户密码
设置超级用户密码。

课程建议：

```text
postgres
```

或者：

```text
postgres123
```

注意：这只是本地开发环境密码，生产环境不能这么简单。

---

#### 第七步：设置端口
默认端口：

```text
5432
```

不要随便改。

如果 5432 被占用，可以改成：

```text
5433
```

---

#### 第八步：Locale 保持默认
Locale 直接保持默认即可。

---

#### 第九步：完成安装
安装完成后，Windows 会有：

```text
PostgreSQL Server
pgAdmin 4
psql
```

---

### 【验证安装】
打开 PowerShell：

```powershell
psql --version
```

如果提示找不到命令，需要把 PostgreSQL 的 bin 目录加入 PATH。

常见路径：

```text
C:\Program Files\PostgreSQL\16\bin
```

---

### 【连接数据库】
```powershell
psql -U postgres
```

输入密码。

进入后执行：

```sql
SELECT version();
```

退出：

```sql
\q
```

---

### 【重点内容】
==Windows 安装最重要的几个点：==

第一，记住密码。

第二，记住端口。

第三，安装时要勾选 Command Line Tools。

第四，如果 psql 命令找不到，要配置环境变量 PATH。

第五，课程里本地开发统一用：

```text
host = localhost
port = 5432
user = postgres
password = postgres
database = ai_agent_course
```

这样后面代码配置会比较统一。

---

## 八、05｜方式二：macOS 安装 PostgreSQL
### 方案一：Homebrew 安装
如果你已经安装了 Homebrew，可以执行：

```bash
brew install postgresql@16
```

启动服务：

```bash
brew services start postgresql@16
```

查看服务：

```bash
brew services list
```

检查版本：

```bash
psql --version
```

---

### 创建数据库
进入 psql：

```bash
psql postgres
```

创建数据库：

```sql
CREATE DATABASE ai_agent_course;
```

查看数据库：

```sql
\l
```

退出：

```sql
\q
```

---

### 方案二：官方安装包
也可以从 PostgreSQL 官方 macOS 下载页选择图形安装包或其他包管理方式。

---

### 【重点内容】
==macOS 我比较推荐 Homebrew。==

命令简单：

```bash
brew install postgresql@16
brew services start postgresql@16
```

如果学员不熟悉命令行，也可以使用官方安装包。

macOS 上一定要确认：

```bash
psql --version
```

能正常输出。

---

## 九、06｜方式三：Docker Compose 安装 PostgreSQL
### 【创建 docker-compose.yml】
在项目根目录创建：

```text
docker-compose.yml
```

写入：

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: ai_agent_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ai_agent_course
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

启动：

```bash
docker compose up -d
```

查看容器：

```bash
docker ps
```

查看日志：

```bash
docker logs ai_agent_postgres
```

进入容器：

```bash
docker exec -it ai_agent_postgres psql -U postgres -d ai_agent_course
```

测试：

```sql
SELECT version();
```

退出：

```sql
\q
```

---

### 【重点内容】
==Docker 方式是我最推荐课程统一使用的方式。==

因为只需要一个：

```text
docker-compose.yml
```

就能把 PostgreSQL 跑起来。

这里我们用的是官方 PostgreSQL 镜像。

官方镜像支持通过环境变量初始化数据库，比如：

```text
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
```

这些变量会在容器第一次初始化数据目录时生效。

注意：

```text
如果你已经启动过容器，并且 postgres_data 里已经有数据
再改 POSTGRES_DB 可能不会重新初始化
```

因为数据库已经创建过了。

如果想完全重建，可以执行：

```bash
docker compose down -v
docker compose up -d
```

但是这个命令会删除数据卷，本地数据会清空。

---

## 十、07｜为什么这里不用 pgvector 镜像
### 【重点内容】
有些同学可能之前用过：

```text
pgvector/pgvector
```

这个镜像。

但是这一章我们先不用它。

原因是这一章只讲：

```text
PostgreSQL 基础表
SQLAlchemy
会话消息持久化
```

还没有进入向量数据库。

所以我们先用官方镜像：

```yaml
image: postgres:16-alpine
```

后面 RAG 阶段讲 pgvector 时，我们再切换到支持 pgvector 的镜像，或者在 PostgreSQL 里安装扩展。

这样课程节奏更清晰。

---

## 十一、08｜PostgreSQL 客户端工具推荐
### 【实操】
 

免费版本

[https://www.navicat.com.cn/download/navicat-premium-lite](https://www.navicat.com.cn/download/navicat-premium-lite)



| 工具 | 是否免费 | 适合人群 | 推荐程度 |
| --- | --- | --- | --- |
| pgAdmin | 免费 / 开源 | PostgreSQL 初学者 | 推荐 |
| DBeaver Community | 免费 / 开源 | 多数据库开发者 | 强烈推荐 |
| TablePlus | 部分免费 / 付费 | macOS 用户 | 推荐 |
| DataGrip | 付费 | JetBrains 用户 | 推荐 |
| Navicat | 付费 | 企业开发者 / 老用户 | 推荐但成本高 |
| VS Code 插件 | 免费 | 轻量查询 | 可选 |


---

### 1. pgAdmin
pgAdmin 是 PostgreSQL 官方生态里非常常见的图形化管理工具，官方文档称它是面向 PostgreSQL 的开源管理与开发平台；pgAdmin 下载页也说明它是免费软件项目。

适合：

```text
初学者
只管理 PostgreSQL
想要官方生态工具
```

优点：

```text
免费
PostgreSQL 支持完整
安装 PostgreSQL 时可一起安装
适合查看表、执行 SQL、管理数据库
```

缺点：

```text
界面略重
体验不如商业客户端顺滑
多数据库支持不是它的重点
```

---

### 2. DBeaver Community
DBeaver Community 是免费的开源跨平台数据库工具，官方页面说明它支持 PostgreSQL 等多种数据库。

适合：

```text
前端转后端
Java 后端
需要同时连 MySQL / PostgreSQL / SQLite
想要免费客户端
```

优点：

```text
免费开源
跨平台
支持多种数据库
SQL 编辑体验不错
适合课程学员统一使用
```

缺点：

```text
首次连接会下载驱动
功能多，界面对新手略复杂
```

课程推荐：

```text
如果你不知道选哪个，优先选 DBeaver Community。
```

---

### 3. Navicat
Navicat for PostgreSQL 是商业图形化数据库开发工具，官方资料介绍它可以连接本地或远程 PostgreSQL 服务，也支持一些云数据库。

适合：

```text
企业开发者
已经习惯 Navicat 的同学
愿意购买商业工具
```

优点：

```text
界面友好
操作简单
导入导出方便
很多国内开发者熟悉
```

缺点：

```text
付费
课程不建议强制要求学员购买
```

课程建议：

```text
如果你已经有 Navicat，可以继续用。
如果没有，不需要为了课程专门购买，DBeaver Community 足够。
```

---

### 4. TablePlus / DataGrip / VS Code 插件
可选工具：

```text
TablePlus
DataGrip
VS Code PostgreSQL 插件
```

选择建议：

```text
已经用 JetBrains 全家桶：可以用 DataGrip
macOS 喜欢轻量工具：可以用 TablePlus
只想简单执行 SQL：可以用 VS Code 插件
```

==但是课程演示建议统一使用：==

```text
DBeaver Community
或者
pgAdmin
```

因为免费、跨平台、容易跟学员对齐。

---

## 十二、09｜用 DBeaver 连接 PostgreSQL
### 【操作步骤】
第一步：打开 DBeaver。

第二步：点击：

```text
New Database Connection
```

第三步：选择：

```text
PostgreSQL
```

第四步：填写连接信息：

```text
Host: localhost
Port: 5432
Database: ai_agent_course
Username: postgres
Password: postgres
```

第五步：点击：

```text
Test Connection
```

如果提示下载驱动，点击下载。

第六步：连接成功后，点击：

```text
Finish
```

第七步：打开 SQL Editor，执行：

```sql
SELECT version();
```

---

### 【重点内容】
DBeaver 第一次连接 PostgreSQL 时，可能会提示下载驱动。

这个是正常的。

点击下载即可。

连接成功后，左侧可以看到：

```text
Databases
Schemas
Tables
Views
Functions
```

后面我们创建的表，比如：

```text
users
conversations
messages
```

都会在这里看到。

---

## 十三、10｜创建数据库和用户
### 如果使用 Docker Compose
前面的 Docker Compose 已经自动创建了：

```text
database: ai_agent_course
user: postgres
password: postgres
```

可以直接用。

---

### 如果是手动安装 PostgreSQL
进入 psql：

```bash
psql -U postgres
```

创建数据库：

```sql
CREATE DATABASE ai_agent_course;
```

查看数据库：

```sql
\l
```

连接数据库：

```sql
\c ai_agent_course
```

创建开发用户：

```sql
CREATE USER ai_agent_user WITH PASSWORD 'ai_agent_password';
```

授权：

```sql
GRANT ALL PRIVILEGES ON DATABASE ai_agent_course TO ai_agent_user;
```

退出：

```sql
\q
```

---

### 【重点内容】
本地课程里，为了简单，我们可以直接使用 postgres 超级用户。

==但是企业项目里，不建议应用直接使用超级用户。==

更推荐创建专门的业务用户：

```text
ai_agent_user
```

然后只给它需要的权限。

这一章为了降低学习成本，代码里先使用：

```text
postgres / postgres
```

后面讲部署和安全时，再升级权限设计。

---

## 十四、11｜配置数据库连接字符串
打开 `.env`：

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course
```

`.env.example` 也加上：

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course
```

---

### 【重点内容】
这个连接字符串非常重要。

我们拆开看：

```text
postgresql+asyncpg
= 使用 PostgreSQL，并通过 asyncpg 异步驱动连接

postgres
= 用户名

postgres
= 密码

localhost
= 数据库地址

5432
= 端口

ai_agent_course
= 数据库名
```

完整就是：

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course
```

后面 SQLAlchemy 会通过这个地址连接数据库。

---

## 十五、12｜更新 Settings 配置
打开：

```text
app/core/config.py
```

增加字段：

```python
database_url: str = Field(
    default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course"
)
```

完整片段：

```python
class Settings(BaseSettings):
    app_name: str = Field(default="AI Agent Course API")
    app_env: str = Field(default="development")
    app_version: str = Field(default="0.1.0")
    api_v1_prefix: str = Field(default="/api/v1")
    debug: bool = Field(default=True)

    app_api_key: str = Field(default="dev-api-key-123")

    default_model: str = Field(default="deepseek-chat")
    supported_models: str = Field(default="deepseek-chat,qwen-plus,gpt-4o-mini")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course"
    )
```

---

### 【重点内容】
现在数据库地址也从 `.env` 读取。

后面本地环境、测试环境、生产环境的数据库肯定不一样。

所以不能写死在代码里。

本地：

```text
localhost
```

Docker 内部服务之间：

```text
postgres
```

生产：

```text
真实数据库地址
```

都可以通过环境变量切换。

---

## 十六、13｜安装 SQLAlchemy 和 asyncpg
执行：

```bash
uv add sqlalchemy asyncpg
```

如果使用 pip：

```bash
pip install sqlalchemy asyncpg
```

检查：

```bash
uv pip list
```

---

### 【重点内容】
这里安装两个包。

第一个：

```text
sqlalchemy
```

它是 ORM 框架。

第二个：

```text
asyncpg
```

它是 PostgreSQL 的异步驱动。

==因为我们要使用 FastAPI 的异步能力，所以选择异步数据库访问。==

SQLAlchemy 官方文档里也提供了 asyncio 扩展，包括 AsyncSession 等对象。

---

## 十七、14｜ORM 是什么
### 【重点内容】
ORM 的全称是：

```text
Object Relational Mapping
```

对象关系映射。

简单说，就是把数据库表映射成 Python 类。

比如数据库表：

```sql
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,
    title VARCHAR
);
```

对应 Python 类：

```python
class Conversation(Base):
    __tablename__ = "conversations"

    id = mapped_column(String, primary_key=True)
    title = mapped_column(String)
```

这样我们就可以用 Python 对象操作数据库。

比如：

```python
conversation = Conversation(id="c_10001", title="AI Agent 学习")
session.add(conversation)
```

而不是每次手写 SQL。

---

## 十八、15｜同步 ORM 和异步 ORM 的区别
### 【实操】
| 方式 | 连接驱动 | Session | 使用方式 |
| --- | --- | --- | --- |
| 同步 ORM | psycopg2 | Session | `session.execute()` |
| 异步 ORM | asyncpg | AsyncSession | `await session.execute()` |


---

### 【重点内容】
同步数据库访问：

```python
result = session.execute(sql)
```

异步数据库访问：

```python
result = await session.execute(sql)
```

我们前面已经讲过 async / await。

AI 后端经常要同时等待：

```text
LLM
数据库
Redis
向量库
外部 Tool
```

==所以我们这门课统一使用异步写法。==

也就是：

```text
AsyncEngine
AsyncSession
asyncpg
```

注意：SQLAlchemy 官方文档提醒，AsyncSession 是可变、有状态对象，不适合在多个并发任务中共享同一个实例。

课程里我们会按照：

```text
每个请求一个 AsyncSession
```

来使用。

---

## 十九、16｜创建 db 目录
执行：

```bash
mkdir -p app/db
touch app/db/__init__.py
touch app/db/base.py
touch app/db/session.py
touch app/db/init_db.py
```

Windows PowerShell：

```powershell
mkdir app\db
New-Item app\db\__init__.py
New-Item app\db\base.py
New-Item app\db\session.py
New-Item app\db\init_db.py
```

---

### 【重点内容】
现在我们新增：

```text
app/db
```

目录。

它专门放数据库基础设施代码。

比如：

```text
base.py
= SQLAlchemy Base

session.py
= 数据库连接和 Session

init_db.py
= 初始化数据库表
```

这样数据库相关代码不会散落在业务模块里。

---

## 二十、17｜编写 db/base.py
打开：

```text
app/db/base.py
```

写入：

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

---

### 【重点内容】
这里我们定义了 SQLAlchemy 的 Base。

后面所有数据库模型都会继承它。

比如：

```python
class Conversation(Base):
    pass
```

这样 SQLAlchemy 才能知道：

```text
这些类是 ORM 模型
需要映射成数据库表
```

---

## 二十一、18｜编写 db/session.py
打开：

```text
app/db/session.py
```

写入：

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

---

### 【重点内容】
==这里我们创建了数据库连接核心对象。==

第一个：

```python
engine = create_async_engine(...)
```

它表示异步数据库引擎。

第二个：

```python
AsyncSessionLocal = async_sessionmaker(...)
```

它表示异步 Session 工厂。

后面每次请求进来，我们都会通过：

```python
AsyncSessionLocal()
```

创建一个新的数据库 Session。

这里有两个参数解释一下。

```python
echo=settings.debug
```

如果 debug 是 true，会打印 SQL。

开发阶段很有用。

```python
pool_pre_ping=True
```

表示连接池使用连接前先检查连接是否可用。

这可以减少数据库断开导致的错误。

---

## 二十二、19｜改造 database dependency
打开：

```text
app/dependencies/database.py
```

替换成：

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

---

### 【重点内容】
上一章我们用的是：

```python
MockDBSession
```

现在换成真正的：

```python
AsyncSession
```

这里仍然使用：

```python
yield
```

请求开始时创建 Session。

请求结束后关闭 Session。

后面接口里可以写：

```python
db: AsyncSession = Depends(get_db_session)
```

==这就是企业 FastAPI 项目里非常常见的数据库依赖写法。==

---

## 二十三、20｜定义 User 模型
打开：

```text
app/models/user.py
```

写入：

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
```

---

### 【重点内容】
这是我们的第一个数据库模型：

```python
User
```

它对应数据库表：

```text
users
```

字段包括：

```text
id
username
role
is_active
created_at
```

大家注意写法：

```python
id: Mapped[str] = mapped_column(...)
```

==这是 SQLAlchemy 2.x 推荐的 ORM 类型写法。==

---

## 二十四、21｜定义 Conversation 模型
打开：

```text
app/models/conversation.py
```

写入：

```python
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
```

---

### 【重点内容】
Conversation 表用来保存会话。

字段包括：

```text
id
title
user_id
status
created_at
updated_at
```

这里还有一个关系：

```python
messages = relationship(...)
```

表示一个会话有多条消息。

也就是：

```text
Conversation
  ↓
Message[]
```

这是典型的一对多关系。

---

## 二十五、22｜定义 Message 模型
打开：

```text
app/models/message.py
```

写入：

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )
```

---

### 【重点内容】
Message 表用来保存聊天消息。

字段包括：

```text
id
conversation_id
role
content
model
created_at
```

其中：

```python
conversation_id
```

是外键，关联：

```text
conversations.id
```

这样我们就能查：

```text
某个会话下所有消息
```

后面 AI Chat 的历史记录就靠这张表。

---

## 二十六、23｜整理 app/models/**init**.py
打开：

```text
app/models/__init__.py
```

写入：

```python
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


__all__ = [
    "Conversation",
    "Message",
    "User",
]
```

---

### 【重点内容】
这里我们把模型统一导出。

后面创建表的时候，需要确保这些模型都被导入。

否则 SQLAlchemy 不知道有这些表。

这是很多新手容易踩的坑。

---

## 二十七、24｜编写 init_db.py
打开：

```text
app/db/init_db.py
```

写入：

```python
from app.db.base import Base
from app.db.session import engine

# 必须导入 models，确保 metadata 里能收集到表
from app import models  # noqa: F401


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

### 【重点内容】
这里我们写了一个初始化数据库表的函数。

核心是：

```python
Base.metadata.create_all
```

它会根据 ORM 模型创建数据库表。

注意这里：

```python
from app import models
```

不是没用。

它的作用是确保：

```text
User
Conversation
Message
```

这些模型都被导入。

如果不导入，metadata 里可能没有表。

---

## 二十八、25｜创建 scripts/create_tables.py
创建目录：

```bash
mkdir -p scripts
touch scripts/create_tables.py
```

Windows：

```powershell
mkdir scripts
New-Item scripts\create_tables.py
```

写入：

```python
import asyncio

from app.db.init_db import init_db


async def main():
    await init_db()
    print("数据库表创建完成")


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/create_tables.py
```

---

### 【重点内容】
现在我们写一个脚本来创建数据库表。

运行：

```bash
python scripts/create_tables.py
```

如果没有报错，就说明表创建成功。

然后我们可以去 DBeaver 或 pgAdmin 里查看：

```text
users
conversations
messages
```

这三张表。

---

## 二十九、26｜用 DBeaver 查看表
### 【操作步骤】
第一步：打开 DBeaver。

第二步：连接：

```text
localhost:5432
database: ai_agent_course
user: postgres
password: postgres
```

第三步：展开：

```text
Databases
  ↓
ai_agent_course
  ↓
Schemas
  ↓
public
  ↓
Tables
```

第四步：应该看到：

```text
users
conversations
messages
```

第五步：右键表名，选择：

```text
View Data
```

---

### 【重点内容】
现在我们可以用客户端工具查看表了。

如果你看到：

```text
users
conversations
messages
```

说明 SQLAlchemy 已经成功把模型创建成了数据库表。

如果没有看到，检查：

```text
数据库连接是不是 ai_agent_course
脚本是否执行成功
models 是否被导入
DATABASE_URL 是否正确
```

---

## 三十、27｜创建数据库测试脚本
创建：

```text
scripts/test_db.py
```

写入：

```python
import asyncio

from sqlalchemy import text

from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT version()"))
        version = result.scalar_one()

        print(version)


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_db.py
```

---

### 【重点内容】
这个脚本用于测试 Python 是否能连上 PostgreSQL。

如果能输出 PostgreSQL 版本，说明：

```text
DATABASE_URL 正确
SQLAlchemy 正常
asyncpg 正常
数据库服务正常
```

这一步非常重要。

后面如果接口报数据库错误，我们可以先用这个脚本单独验证数据库连接。

---

## 三十一、28｜改造 ConversationRepository
打开：

```text
app/repositories/conversation_repository.py
```

替换成：

```python
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ChatMessage, MessageRole
from app.schemas.conversation import ConversationCreateRequest


class ConversationRepository:
    async def create(
        self,
        db: AsyncSession,
        request: ConversationCreateRequest,
        user_id: str | None = None,
    ) -> Conversation:
        conversation = Conversation(
            id=f"c_{uuid.uuid4().hex[:8]}",
            title=request.title,
            user_id=user_id,
        )

        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return conversation

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> list[ChatMessage]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )

        result = await db.execute(stmt)
        messages = result.scalars().all()

        return [
            ChatMessage(
                role=MessageRole(message.role),
                content=message.content,
            )
            for message in messages
        ]

    async def add_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        model: str | None = None,
    ) -> Message:
        message = Message(
            id=f"m_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        return message


conversation_repository = ConversationRepository()
```

---

### 【重点内容】
现在 ConversationRepository 真正开始操作数据库了。

创建会话：

```python
db.add(conversation)
await db.commit()
await db.refresh(conversation)
```

查询消息：

```python
stmt = select(Message).where(...)
result = await db.execute(stmt)
```

新增消息：

```python
db.add(message)
await db.commit()
```

这里大家要记住：

```text
查询用 select
执行用 await db.execute
新增用 db.add
提交用 await db.commit
刷新用 await db.refresh
```

这是 SQLAlchemy ORM 的基础操作。

---

## 三十二、29｜改造 ConversationService
打开：

```text
app/services/conversation_service.py
```

修改为：

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation_repository import conversation_repository
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationMessagesResponse,
    ConversationResponse,
)


async def create_conversation(
    db: AsyncSession,
    request: ConversationCreateRequest,
    user_id: str | None = None,
) -> ConversationResponse:
    conversation = await conversation_repository.create(
        db=db,
        request=request,
        user_id=user_id,
    )

    return ConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: str,
) -> ConversationMessagesResponse:
    messages = await conversation_repository.get_messages(
        db=db,
        conversation_id=conversation_id,
    )

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )
```

---

### 【重点内容】
现在 Service 层也升级了。

它不再调用内存假数据。

它接收：

```python
db: AsyncSession
```

然后传给 Repository。

调用链路变成：

```text
Router
 ↓
Depends(get_db_session)
 ↓
Service
 ↓
Repository
 ↓
PostgreSQL
```

==这就是我们要的真实数据库链路。==

---

## 三十三、30｜改造 Conversations Router
打开：

```text
app/api/v1/conversations.py
```

修改为：

```python
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db_session
from app.dependencies.pagination import PaginationParams
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationMessagesResponse,
    ConversationResponse,
)
from app.schemas.response import ApiResponse
from app.schemas.user import CurrentUser
from app.services.conversation_service import (
    create_conversation,
    get_conversation_messages,
)

router = APIRouter()


@router.post("/conversations", response_model=ApiResponse[ConversationResponse])
async def create_new_conversation(
    request: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> ApiResponse[ConversationResponse]:
    result = await create_conversation(
        db=db,
        request=request,
        user_id=current_user.user_id,
    )

    return ApiResponse[ConversationResponse](
        data=result
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[ConversationMessagesResponse],
)
async def get_messages(
    conversation_id: str = Path(..., description="会话 ID"),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ConversationMessagesResponse]:
    result = await get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
    )

    return ApiResponse[ConversationMessagesResponse](
        data=result
    )


@router.get("/conversations", response_model=ApiResponse[dict])
async def list_conversations(
    pagination: PaginationParams = Depends(PaginationParams),
) -> ApiResponse[dict]:
    return ApiResponse[dict](
        data={
            "page": pagination.page,
            "page_size": pagination.page_size,
            "offset": pagination.offset,
            "items": [],
        }
    )
```

---

### 【重点内容】
现在 Router 里通过 Depends 注入：

```python
db: AsyncSession = Depends(get_db_session)
```

同时也注入当前用户：

```python
current_user: CurrentUser = Depends(get_current_user)
```

创建会话时，会把：

```python
current_user.user_id
```

保存到数据库。

这样会话就和用户关联起来了。

---

## 三十四、31｜测试创建会话
启动服务：

```bash
uv run uvicorn app.main:app --reload
```

curl：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/conversations" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "title": "AI Agent 学习会话"
  }'
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_xxxxxxxx",
    "title": "AI Agent 学习会话",
    "status": "active",
    "created_at": "2026-08-24Txx:xx:xx",
    "updated_at": "2026-08-24Txx:xx:xx"
  },
  "trace_id": null
}
```

---

### 【重点内容】
现在创建会话不再是内存数据。

它会真正写入 PostgreSQL。

大家可以打开 DBeaver，查看：

```text
conversations
```

表。

应该能看到刚才创建的记录。

---

## 三十五、32｜用 SQL 查询数据
在 DBeaver 或 psql 里执行：

```sql
SELECT * FROM conversations;
```

可以看到类似：

```text
id          title              user_id     status
c_xxxxxxxx  AI Agent 学习会话   u_10001    active
```

---

### 【重点内容】
==这一步一定要演示给学员看。==

因为这能让学员建立一个非常重要的认知：

```text
接口调用
不是只返回 JSON
而是真正写进数据库了
```

这就是后端开发的闭环。

---

## 三十六、33｜让 Chat 接口保存消息
现在我们希望 Chat 接口做两件事：

```text
1. 保存用户消息
2. 保存 AI 回复
```

打开：

```text
app/services/chat_service.py
```

修改函数签名：

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.conversation_repository import conversation_repository
```

把：

```python
async def chat_with_ai(request: ChatRequest) -> ChatResponse:
```

改成：

```python
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession | None = None,
) -> ChatResponse:
```

在生成 answer 后、return 前增加：

```python
if db and request.session_id:
    latest_user_message = get_latest_user_message(request)

    await conversation_repository.add_message(
        db=db,
        conversation_id=request.session_id,
        role=MessageRole.USER.value,
        content=latest_user_message,
        model=request.model,
    )

    await conversation_repository.add_message(
        db=db,
        conversation_id=request.session_id,
        role=MessageRole.ASSISTANT.value,
        content=answer,
        model=model,
    )
```

---

### 【重点内容】
现在 ChatService 支持传入 db。

如果有：

```python
db
```

并且请求里有：

```python
session_id
```

就把用户消息和 AI 回复保存到数据库。

为什么要判断 session_id？

因为如果没有会话 ID，就不知道消息属于哪个会话。

后面我们会优化成：

```text
如果没有 session_id，自动创建会话
```

这一章先让大家理解数据库保存流程。

---

## 三十七、34｜改造 Chat Router 注入 db
打开：

```text
app/api/v1/chat.py
```

导入：

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db_session
```

修改 Chat 接口：

```python
@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(
        request=request,
        db=db,
    )

    result.trace_id = f"{result.trace_id}_user_{current_user.user_id}"

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

### 【重点内容】
现在 Chat 接口也注入数据库 Session。

调用 Service 时传进去：

```python
db=db
```

于是链路变成：

```text
Chat Router
 ↓
get_db_session
 ↓
ChatService
 ↓
ConversationRepository
 ↓
messages 表
```

这样 Chat 消息就能持久化了。

---

## 三十八、35｜测试 Chat 保存消息
第一步，先创建会话，拿到 conversation_id。

第二步，调用 Chat 接口：

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -H "x-api-key: dev-api-key-123" \
  -H "x-user-id: u_10001" \
  -H "x-username: dawei" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "什么是 AI Agent？"
      }
    ],
    "model": "deepseek-chat",
    "temperature": 0.7,
    "stream": false,
    "session_id": "替换成你刚才创建的 c_xxxxxxxx"
  }'
```

第三步，查询消息：

```bash
curl "http://127.0.0.1:8000/api/v1/conversations/替换成你的会话ID/messages" \
  -H "x-api-key: dev-api-key-123"
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": "c_xxxxxxxx",
    "messages": [
      {
        "role": "user",
        "content": "什么是 AI Agent？"
      },
      {
        "role": "assistant",
        "content": "AI Agent 是能够理解目标、规划步骤、调用工具并根据结果完成任务的智能体。"
      }
    ]
  },
  "trace_id": null
}
```

---

### 【重点内容】
现在我们完成了真正的闭环：

```text
创建会话
 ↓
发送消息
 ↓
AI 回复
 ↓
用户消息入库
 ↓
AI 消息入库
 ↓
查询历史消息
```

==这就是 AI Chat 系统的最小数据库闭环。==

---

## 三十九、36｜数据库异常处理
如果数据库连接失败，常见错误可能是：

```text
connection refused
password authentication failed
database does not exist
```

我们可以在 Repository 或 Service 里捕获异常，然后抛 AppException。

示例：

```python
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException, ErrorCode


try:
    await db.commit()
except SQLAlchemyError as e:
    await db.rollback()
    raise AppException(
        message="数据库操作失败",
        code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
        data={
            "reason": str(e)
        },
    ) from e
```

---

### 【重点内容】
数据库操作失败时，一定要注意：

```python
await db.rollback()
```

如果 commit 失败，不 rollback，Session 状态可能会异常。

这一章我们先不在每个 Repository 里都加完整异常处理。

后面讲 Repository 优化和事务时，会统一封装。

但大家现在先记住：

```text
commit 失败要 rollback
```

---

## 四十、37｜常见错误一：数据库服务没启动

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
ConnectionRefusedError
```

检查 Docker：

```bash
docker ps
```

如果没有 postgres：

```bash
docker compose up -d
```

检查日志：

```bash
docker logs ai_agent_postgres
```

---

## 四十一、38｜常见错误二：密码错误
错误：

```text
password authentication failed for user "postgres"
```

检查 `.env`：

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_course
```

确认密码和安装时设置的一致。

Docker 用户确认：

```yaml
POSTGRES_PASSWORD: postgres
```

---

## 四十二、39｜常见错误三：数据库不存在

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
database "ai_agent_course" does not exist
```

解决：

进入 psql：

```bash
psql -U postgres
```

创建数据库：

```sql
CREATE DATABASE ai_agent_course;
```

如果使用 Docker，可以直接重建：

```bash
docker compose down -v
docker compose up -d
```

注意这会清空数据。

---

## 四十三、40｜常见错误四：表没有创建
错误：

```text
relation "conversations" does not exist
```

说明表不存在。

运行：

```bash
python scripts/create_tables.py
```

然后去 DBeaver 查看表。

---

## 四十四、41｜常见错误五：忘记 await

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```python
db.commit()
```

正确：

```python
await db.commit()
```

异步 Session 的操作很多都需要：

```python
await
```

比如：

```python
await db.execute(...)
await db.commit()
await db.refresh(...)
await db.close()
```

---

## 四十五、42｜常见错误六：AsyncSession 多任务共享
不要在多个并发任务里共享同一个 AsyncSession。

错误思路：

```python
await asyncio.gather(
    save_message(db, msg1),
    save_message(db, msg2),
)
```

同一个请求里如果要并发做多个数据库操作，要特别小心。

SQLAlchemy 文档提醒 AsyncSession 是可变、有状态对象，不适合多个并发任务共享同一实例。

课程里先按顺序写：

```python
await save_user_message(...)
await save_ai_message(...)
```

稳定优先。

---

## 四十六、43｜当前数据库表设计复盘
### 【实操】
```text
users
├── id
├── username
├── role
├── is_active
└── created_at

conversations
├── id
├── title
├── user_id
├── status
├── created_at
└── updated_at

messages
├── id
├── conversation_id
├── role
├── content
├── model
└── created_at
```

---

### 【重点内容】
现在我们已经有了三张基础表。

它们支撑 AI Chat 最小闭环。

后面会继续扩展：

```text
token_usage
llm_call_logs
knowledge_bases
documents
document_chunks
agents
agent_runs
tool_calls
```

但是不要一开始就设计太多表。

先把：

```text
用户
会话
消息
```

跑通。

这是 AI Chat 的基础。

---

## 四十七、44｜本章知识点和 AI 开发场景对应表
| 知识点 | AI 开发场景 |
| --- | --- |
| PostgreSQL | 存用户、会话、消息、知识库、Agent 配置 |
| DBeaver / pgAdmin | 查看表、执行 SQL、调试数据 |
| Docker Compose | 统一开发环境 |
| DATABASE_URL | 不同环境切换数据库 |
| SQLAlchemy ORM | 用 Python 类操作数据库 |
| AsyncSession | FastAPI 异步数据库访问 |
| `Depends(get_db_session)` | 每个请求注入数据库会话 |
| `Base.metadata.create_all` | 根据 ORM 模型创建表 |
| Repository | 封装数据库访问逻辑 |
| Conversation 表 | 保存 AI 对话会话 |
| Message 表 | 保存用户消息和 AI 回复 |
| `select()` | 查询数据 |
| `db.add()` | 新增数据 |
| `db.commit()` | 提交事务 |
| `db.refresh()` | 刷新对象 |
| `rollback()` | 数据库异常回滚 |


---

## 四十八、45｜本章完整复习
这一章我们完成了：

```bash
1. 理解为什么 AI 后端需要数据库
2. 了解 PostgreSQL 的作用
3. 学习 Windows 安装 PostgreSQL
4. 学习 macOS 安装 PostgreSQL
5. 学习 Docker Compose 安装 PostgreSQL
6. 推荐 pgAdmin / DBeaver / Navicat 等客户端工具
7. 使用 DBeaver 连接 PostgreSQL
8. 创建 ai_agent_course 数据库
9. 配置 DATABASE_URL
10. 安装 SQLAlchemy 和 asyncpg
11. 理解 ORM
12. 理解同步 ORM 和异步 ORM
13. 创建 app/db 目录
14. 创建 SQLAlchemy Base
15. 创建 Async Engine
16. 创建 AsyncSessionLocal
17. 改造 get_db_session
18. 定义 User 模型
19. 定义 Conversation 模型
20. 定义 Message 模型
21. 编写 create_tables 脚本
22. 用 DBeaver 查看表
23. 编写 test_db 脚本
24. 改造 ConversationRepository
25. 改造 ConversationService
26. 改造 Conversations Router
27. 创建会话写入数据库
28. Chat 接口保存用户消息和 AI 回复
29. 查询会话历史消息
30. 总结数据库常见错误
```

现在我们的项目已经从：

```text
内存假数据
```

升级成：

```text
PostgreSQL 持久化数据
```

这一步非常关键。

因为后面所有复杂 AI 能力都需要数据库支撑。

---

## 四十九、46｜课后任务一：新增 list_conversations 数据库查询
要求：

```text
1. 在 ConversationRepository 中新增 list 方法
2. 支持 page / page_size
3. 按 created_at 倒序
4. 在 GET /conversations 接口中返回真实数据库数据
```

参考代码：

```python
async def list(
    self,
    db: AsyncSession,
    offset: int = 0,
    limit: int = 10,
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .order_by(Conversation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)

    return list(result.scalars().all())
```

---

## 五十、47｜课后任务二：新增 get_conversation_by_id
要求：

```text
1. 根据 conversation_id 查询会话
2. 如果不存在，抛 AppException
3. code 使用 40401
4. status_code 使用 404
```

参考代码：

```python
async def get_by_id(
    self,
    db: AsyncSession,
    conversation_id: str,
) -> Conversation | None:
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)

    return result.scalar_one_or_none()
```

---

## 五十一、48｜课后任务三：创建 UserRepository
要求：

```text
1. 创建 app/repositories/user_repository.py
2. 实现 create_user
3. 实现 get_user_by_id
4. 写一个 scripts/create_user.py 测试脚本
```

参考模型：

```python
user = User(
    id="u_10001",
    username="dawei",
    role="user",
    is_active=True,
)
```

---

## 五十二、49｜课后任务四：给 messages 表增加 token 字段
要求：

```text
1. Message 模型增加 prompt_tokens
2. Message 模型增加 completion_tokens
3. Message 模型增加 total_tokens
4. 删除旧表重新 create_tables
5. 测试保存消息
```

提示：

```bash
本章还没讲 Alembic 迁移，所以开发阶段可以先删除表重建。
下一章或后续章节再讲数据库迁移。
```

---

## 五十三、50｜课后任务五：画出数据库调用链路
画出：

```http
POST /api/v1/chat
```

保存消息的完整链路：

```text
HTTP Request
 ↓
Middleware
 ↓
verify_api_key
 ↓
get_current_user
 ↓
get_db_session
 ↓
Chat Router
 ↓
ChatService
 ↓
ConversationRepository.add_message
 ↓
AsyncSession
 ↓
PostgreSQL messages 表
```

---

## 五十四、51｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 11 章我们就讲完了。

这一章我们正式把数据库接入到了项目里。

前面我们的 AI Chat 系统只是一个接口 Demo。

现在它已经开始具备真实后端能力。

我们完成了：

```text
PostgreSQL 安装
客户端工具连接
SQLAlchemy 异步 ORM
AsyncSession
数据库依赖注入
User / Conversation / Message 模型
数据库表创建
Repository 数据访问
创建会话入库
聊天消息入库
查询历史消息
```

这一步非常关键。

因为 AI 应用不是只有模型调用。

==真正的 AI 应用一定要有数据层。==

比如：

```text
用户是谁
会话是什么
消息历史是什么
调用了哪个模型
消耗了多少 token
RAG 命中了哪些文档
Agent 调用了哪些工具
每一步执行结果是什么
```

这些都要靠数据库持久化。

现在我们的项目链路已经变成：

```text
FastAPI
 ↓
Middleware
 ↓
Dependency
 ↓
Router
 ↓
Service
 ↓
Repository
 ↓
PostgreSQL
```

这就是企业级 AI 后端的核心链路。

 

# 
---

> [!success] 一句话带走
> ==先把会话和模型落库，后面的 RAG 与记忆才有地方存。==

> [!quote] 关于本文档
> 由原始讲义 `第 11 章｜PostgreSQL + SQLAlchemy 数据库开发.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-21
