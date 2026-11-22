---
title: "第 12 章｜Redis 在 AI 应用中的使用"
chapter: "12"
source: "第 12 章｜Redis 在 AI 应用中的使用.md"
type: obsidian-note
created: 2026-11-22
status: 整理中
tags:
  - course/llm-agent
  - fastapi
  - redis
  - 缓存
---

# 第 12 章｜Redis 在 AI 应用中的使用

> [!abstract] 本章重点
>
> - ==Redis 不是数据库替代品== — 它快，但主打临时数据；持久业务数据仍放 PostgreSQL。
> - ==AI 场景：会话缓存、限流、幂等、临时状态== — 共同点是读得快、丢了也能重建。
> - ==key 命名要统一规范== — 业务:对象:ID 这种结构，排查和清理都省事。
> - ==Redis Client 抽成依赖== — 和数据库 Session 一个套路，接口里直接注入。
> - ==常见坑：没设过期时间、大 key、连接没复用== — 缓存最容易在这三处出问题。

> [!note] 大白话
>
> - **TTL**：给缓存设个保质期，到点自动删。
> - **缓存**：把常读的东西放内存里，下次不用再查库。

> [!info] 导航与来源
> - 原始讲义：[[第 12 章｜Redis 在 AI 应用中的使用|打开原始讲义]]
> - [[第 11 章｜PostgreSQL + SQLAlchemy 数据库开发|上一章｜第 11 章]]
> - [[第 13 章｜大模型 API 原理|下一章｜第 13 章]]
> - 本章所有内容均保留，未删改原文。

## 本章导航

- [[#一、本章定位]]
- [[#Redis]]
- [[#二、本章学习目标]]
- [[#三、本章最终项目结构]]
- [[#四、01｜本章开场]]
- [[#五、02｜Redis 和 PostgreSQL 的区别]]
- [[#六、03｜Redis 在 AI 应用中的典型场景]]
- [[#七、04｜Redis 安装方式总览]]
- [[#八、05｜方式一：Docker Compose 安装 Redis]]
- [[#九、06｜方式二：macOS 安装 Redis]]
- [[#十、07｜Redis 客户端工具推荐]]
- [[#十一、08｜使用 Redis Insight 连接 Redis]]
- [[#十二、09｜Redis 基础命令快速入门]]
- [[#十三、10｜配置 Redis 连接字符串]]

---

## 一、本章定位

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

前面第 11 章，我们完成了 PostgreSQL + SQLAlchemy 数据库开发。

现在项目已经可以把数据持久化到 PostgreSQL：

```text
users
conversations
messages
```

PostgreSQL 负责的是：

```text
长期保存
关系型数据
事务一致性
历史记录
业务主数据
```

但是 AI 应用里，不是所有数据都适合直接放 PostgreSQL。

比如：

```text
接口限流计数
验证码
登录态
API Key 缓存
短期会话状态
Agent 运行状态
分布式锁
LLM 响应缓存
临时任务进度
```

这些数据有几个特点：

```text
访问频率高
生命周期短
读写速度要求高
可以设置过期时间
不一定需要永久保存
```

这类场景就非常适合 Redis。

==所以这一章我们正式引入：==

## Redis
这一章的核心目标是：

**让学员理解 Redis 在 AI Agent 后端里不是“背八股”，而是真正解决缓存、限流、锁、短期记忆、任务状态的问题。**

---

## 二、本章学习目标

> [!abstract] 本节定位
> 先看清这一节要解决什么问题。

学完这一章以后，学员需要掌握：

```bash
1. Redis 是什么
2. Redis 和 PostgreSQL 的区别
3. Redis 在 AI 项目中解决什么问题
4. Redis 如何安装
5. Docker Compose 如何启动 Redis
6. Redis 客户端工具怎么选
7. Redis Insight 如何使用
8. Python 如何连接 Redis
9. redis.asyncio 如何使用
10. FastAPI 如何注入 Redis Client
11. 如何写 Redis Dependency
12. 如何做会话缓存
13. 如何做短期记忆缓存
14. 如何做 API Key 缓存
15. 如何做接口限流
16. 如何做 LLM 响应缓存
17. 如何做 Agent 任务状态缓存
18. 如何做简单分布式锁
19. Redis key 命名规范
20. Redis 常见坑和排查方式
```

---

## 三、本章最终项目结构
本章结束后，项目结构会升级成：

```text
ai-agent-course/
├── app/
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
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── redis/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── keys.py
│   │   ├── cache.py
│   │   ├── rate_limit.py
│   │   ├── lock.py
│   │   └── agent_state.py
│   │
│   ├── dependencies/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── llm.py
│   │   └── settings.py
│   │
│   ├── models/
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
│   │   ├── rag_service.py
│   │   └── redis_demo_service.py
│   │
│   └── repositories/
│       ├── conversation_repository.py
│       └── knowledge_repository.py
│
├── scripts/
│   ├── test_db.py
│   └── test_redis.py
│
├── docker-compose.yml
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

本章重点新增：

```text
app/redis/
app/dependencies/redis.py
app/services/redis_demo_service.py
scripts/test_redis.py
```

---

## 四、01｜本章开场
### 【重点内容】
大家好，欢迎来到第 12 章。

这一章我们讲 Redis 在 AI 应用中的使用。

前面我们刚刚讲完 PostgreSQL。

很多同学可能会问：

老师，有了 PostgreSQL，为什么还要 Redis？

这是非常好的问题。

因为 PostgreSQL 和 Redis 解决的问题不一样。

PostgreSQL 更适合做：

```text
长期存储
关系型数据
事务
历史记录
复杂查询
```

Redis 更适合做：

```text
高速缓存
临时状态
过期数据
计数器
限流
分布式锁
任务进度
短期记忆
```

在 AI Agent 项目里，Redis 非常有用。

比如用户正在和 AI 对话，我们可以把最近几轮消息放 Redis 里，减少数据库查询。

比如某个用户 1 分钟内最多调用 20 次 Chat 接口，可以用 Redis 做限流。

比如 Agent 正在执行一个长任务，任务状态、进度、当前步骤可以放 Redis。

比如某个 LLM 问题已经回答过，可以用 Redis 做响应缓存。

==所以 Redis 不是“可有可无”。==

它是 AI 后端里非常重要的性能和状态管理组件。

---

## 五、02｜Redis 和 PostgreSQL 的区别
### 【实操】
| 对比项 | PostgreSQL | Redis |
| --- | --- | --- |
| 数据定位 | 主数据库 | 缓存 / 临时状态 |
| 存储方式 | 磁盘为主 | 内存为主 |
| 数据生命周期 | 长期保存 | 通常设置过期时间 |
| 查询能力 | SQL、关系查询、事务 | Key-Value、计数器、集合、队列 |
| 适合场景 | 用户、会话、消息、文档、Agent 配置 | 缓存、限流、锁、任务状态、短期记忆 |
| 数据丢失影响 | 通常严重 | 大部分场景可重建 |
| AI 项目用途 | 历史消息、知识库、Agent Run 记录 | 最近上下文、响应缓存、任务进度、限流 |


---

### 【重点内容】
大家不要把 Redis 当成数据库替代品。

Redis 很强，但它不是用来替代 PostgreSQL 的。

PostgreSQL 是主库。

Redis 是辅助组件。

比如：

```text
会话历史
```

要永久保存，应该放 PostgreSQL。

但是：

```text
最近 5 分钟的会话摘要
```

可以放 Redis。

比如：

```text
用户 API Key
```

主数据应该放 PostgreSQL。

但是：

```text
API Key 校验结果
```

可以缓存到 Redis。

比如：

```text
Agent 执行记录
```

最终应该入库。

但是：

```text
Agent 当前执行到第几步
```

可以先放 Redis。

所以要记住一句话：

**PostgreSQL 存长期事实，Redis 存高频临时状态。**

---

## 六、03｜Redis 在 AI 应用中的典型场景
### 【实操】
```text
AI Chat
├── 最近对话缓存
├── session 状态
├── LLM 响应缓存
└── 用户调用频率限制

RAG
├── 检索结果缓存
├── embedding 任务状态
├── 文档解析进度
└── query cache

Agent
├── Agent Run 状态
├── 当前执行步骤
├── Tool Call 锁
├── 长任务进度
└── 中间结果缓存

平台能力
├── API Key 缓存
├── 登录态缓存
├── 验证码缓存
├── 分布式锁
└── 计数器
```

---

### 【重点内容】
这张图很重要。

后面我们会做很多 AI 项目。

比如 AI Chat。

Redis 可以用来做：

```text
最近对话缓存
LLM 响应缓存
接口限流
```

RAG 项目里，Redis 可以用来做：

```text
检索结果缓存
文档解析任务进度
embedding 任务状态
```

Agent 项目里，Redis 可以用来做：

```text
Agent Run 状态
当前步骤
中间结果
分布式锁
```

平台能力里，Redis 可以用来做：

```text
API Key 缓存
登录态缓存
验证码
计数器
```

==所以这章不是单纯讲 Redis 命令。==

我们会结合 AI 项目场景来讲。

---

## 七、04｜Redis 安装方式总览
### 【实操】
```bash
Redis 安装方式

1. Docker Compose
2. macOS Homebrew
3. Linux apt / yum
4. Windows 使用 Docker
```

---

### 【重点内容】
Redis 安装有多种方式。

推荐：

```bash
Docker Compose
```

原因和 PostgreSQL 一样：

```text
环境统一
安装简单
方便删除重建
适合课程教学
```

Redis 官方安装文档也提供 Docker、Linux、macOS 等方式；Windows 侧官方文档当前更偏向通过 Docker 使用 Redis Open Source。

这一章我们重点讲 Docker Compose。

如果你是 macOS，也可以用 Homebrew。

Windows 同学建议直接使用 Docker Desktop。

---

## 八、05｜方式一：Docker Compose 安装 Redis
### 【修改 docker-compose.yml】
在第 11 章的 `docker-compose.yml` 基础上增加 Redis。

完整示例：

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

  redis:
    image: redis:7-alpine
    container_name: ai_agent_redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass redis123
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

启动：

```bash
docker compose up -d
```

查看容器：

```bash
docker ps
```

查看 Redis 日志：

```bash
docker logs ai_agent_redis
```

进入 Redis CLI：

```bash
docker exec -it ai_agent_redis redis-cli -a redis123
```

测试：

```bash
PING
```

返回：

```text
PONG
```

退出：

```bash
exit
```

---

### 【重点内容】
这里我们把 Redis 加到 Docker Compose 里。

重点看这行：

```yaml
command: redis-server --appendonly yes --requirepass redis123
```

其中：

```text
--appendonly yes
```

表示开启 AOF 持久化。

```text
--requirepass redis123
```

表示设置 Redis 密码。

开发环境可以用简单密码。

==生产环境一定要使用强密码，并且不要把 Redis 直接暴露到公网。==

官方 Redis Docker 镜像支持通过 `redis-server` 命令传入配置参数，例如持久化、日志级别等；Redis 官方也有 Docker 安装和运行 Redis 的文档。

---

## 九、06｜方式二：macOS 安装 Redis
如果你用 macOS，并且安装了 Homebrew，可以执行：

```bash
brew install redis
```

启动：

```bash
brew services start redis
```

检查：

```bash
redis-server --version
redis-cli --version
```

连接：

```bash
redis-cli
```

测试：

```bash
PING
```

返回：

```text
PONG
```

---

### 【重点内容】
macOS 可以用 Homebrew 安装 Redis。

但是为了课程统一，我建议优先使用 Docker Compose。

因为后面我们还要同时跑：

```text
PostgreSQL
Redis
pgAdmin / Redis Insight
```

Docker Compose 更容易维护。

---

## 十、07｜Redis 客户端工具推荐
### 【实操】
| 工具 | 是否免费 | 适合人群 | 推荐程度 |
| --- | --- | --- | --- |
| Redis Insight | 免费 | 官方 GUI / CLI 工具 | 强烈推荐 |
| Tiny RDM | 免费 / 开源 | 喜欢轻量客户端的同学 | 推荐 |
| Another Redis Desktop Manager | 开源项目 | 国内开发者常用 | 可选 |
| TablePlus | 部分免费 / 付费 | macOS 用户 | 可选 |
| 命令行 redis-cli | 免费 | 后端开发必备 | 必学 |


---

### 1. Redis Insight
Redis Insight 是 Redis 官方提供的免费 GUI 和 CLI 开发工具，可以查看 key、执行命令、浏览数据结构、格式化 JSON 等。Redis 官方文档也说明 Redis Insight 支持 GUI 与 CLI 两种交互方式。

适合：

```text
初学者
课程统一演示
查看 Key
调试缓存
执行 Redis 命令
```

课程建议：

```text
优先推荐 Redis Insight。
```

---

### 2. Tiny RDM
Tiny RDM 是一个轻量的跨平台 Redis GUI 客户端，项目说明支持 Mac、Windows、Linux，也提供 Web 版本。

适合：

```text
喜欢轻量工具
不想用太重客户端
本地调试 Redis
```

---

### 3. Another Redis Desktop Manager
Another Redis Desktop Manager 是一个开源 Redis GUI 客户端，项目介绍支持 Linux、Windows、Mac。

适合：

```text
国内开发者
习惯桌面客户端
查看大量 key
```

---

### 4. redis-cli
==redis-cli 是必须掌握的命令行工具。==

比如：

```bash
redis-cli -a redis123
```

常用命令：

```bash
PING
SET name dawei
GET name
DEL name
KEYS *
TTL name
EXPIRE name 60
```

---

### 【重点内容】
客户端工具我建议这样选：

```bash
课程演示：Redis Insight
喜欢轻量：Tiny RDM
喜欢命令行：redis-cli
已有习惯：Another Redis Desktop Manager / TablePlus
```

不要在工具选择上浪费太多时间。

核心是理解 Redis 在项目中的用法。

---

## 十一、08｜使用 Redis Insight 连接 Redis
### 【操作步骤】
打开 Redis Insight。

点击：

```text
Add Redis Database
```

填写：

```text
Host: localhost
Port: 6379
Username: 留空
Password: redis123
Database Alias: ai-agent-redis
```

点击：

```text
Test Connection
```

连接成功后点击：

```text
Add Redis Database
```

进入后可以看到：

```text
Browser
Workbench
CLI
```

---

### 【重点内容】
Redis Insight 可以直接查看 Redis 里的 key。

后面我们写入：

```text
chat:cache:xxx
rate_limit:user:xxx
agent:run:xxx
```

都可以在 Redis Insight 里看到。

这对学员理解 Redis 非常有帮助。

因为不是只在代码里操作，而是能看到真实数据。

---

## 十二、09｜Redis 基础命令快速入门
进入 Redis CLI：

```bash
docker exec -it ai_agent_redis redis-cli -a redis123
```

---

### 字符串 String
```bash
SET name dawei
GET name
DEL name
```

---

### 过期时间
```bash
SET verify_code 123456 EX 60
TTL verify_code
GET verify_code
```

---

### 计数器
```bash
INCR api_count
INCR api_count
GET api_count
EXPIRE api_count 60
```

---

### Hash
```bash
HSET user:u_10001 username dawei role user
HGET user:u_10001 username
HGETALL user:u_10001
```

---

### List
```bash
LPUSH chat:recent "你好"
LPUSH chat:recent "什么是 AI Agent？"
LRANGE chat:recent 0 -1
```

---

### Set
```bash
SADD online_users u_10001
SADD online_users u_10002
SMEMBERS online_users
```

---

### 【重点内容】
这一章我们不会把 Redis 所有命令都背一遍。

先掌握几个最常用的：

```text
SET / GET
EXPIRE / TTL
INCR
HSET / HGETALL
LPUSH / LRANGE
SADD / SMEMBERS
```

AI 项目里，最常用的是：

```text
String
Hash
List
计数器
过期时间
```

后面用到更复杂的数据结构时再补。

---

## 十三、10｜配置 Redis 连接字符串
打开 `.env`：

```text
REDIS_URL=redis://:redis123@localhost:6379/0
```

`.env.example` 也加上：

```text
REDIS_URL=redis://:redis123@localhost:6379/0
```

---

### 【重点内容】
Redis 连接字符串拆开看：

```text
redis://
= Redis 协议

:redis123
= 密码

localhost
= 主机

6379
= 端口

/0
= Redis database index
```

Redis 默认有多个逻辑数据库，编号从 0 开始。

课程里统一使用：

```text
db 0
```

---

## 十四、11｜更新 Settings 配置
打开：

```text
app/core/config.py
```

增加：

```python
redis_url: str = Field(default="redis://:redis123@localhost:6379/0")
redis_default_ttl_seconds: int = Field(default=300)
rate_limit_window_seconds: int = Field(default=60)
rate_limit_max_requests: int = Field(default=20)
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

    redis_url: str = Field(default="redis://:redis123@localhost:6379/0")
    redis_default_ttl_seconds: int = Field(default=300)
    rate_limit_window_seconds: int = Field(default=60)
    rate_limit_max_requests: int = Field(default=20)
```

---

### 【重点内容】
现在 Redis 配置也放到 Settings 里。

包括：

```text
redis_url
redis_default_ttl_seconds
rate_limit_window_seconds
rate_limit_max_requests
```

以后如果想调整缓存时间、限流窗口、限流次数，只改 `.env` 即可。

---

## 十五、12｜安装 redis-py
执行：

```bash
uv add redis
```

如果使用 pip：

```bash
pip install redis
```

检查：

```bash
uv pip list
```

---

### 【重点内容】
Python 连接 Redis 使用：

```text
redis-py
```

它现在已经支持 asyncio。

也就是说，我们可以写：

```python
import redis.asyncio as redis
```

然后：

```python
await client.get("key")
await client.set("key", "value")
```

Redis 官方 redis-py 文档说明，异步 API 位于 `redis.asyncio` 命名空间，适合非阻塞访问 Redis。

---

## 十六、13｜创建 Redis 目录
执行：

```bash
mkdir -p app/redis
touch app/redis/__init__.py
touch app/redis/client.py
touch app/redis/keys.py
touch app/redis/cache.py
touch app/redis/rate_limit.py
touch app/redis/lock.py
touch app/redis/agent_state.py
```

Windows PowerShell：

```powershell
mkdir app\redis
New-Item app\redis\__init__.py
New-Item app\redis\client.py
New-Item app\redis\keys.py
New-Item app\redis\cache.py
New-Item app\redis\rate_limit.py
New-Item app\redis\lock.py
New-Item app\redis\agent_state.py
```

---

### 【重点内容】
现在我们创建：

```text
app/redis
```

目录。

这里专门放 Redis 相关逻辑。

比如：

```text
client.py
= 创建 Redis 客户端

keys.py
= 统一管理 key 命名

cache.py
= 缓存封装

rate_limit.py
= 限流

lock.py
= 分布式锁

agent_state.py
= Agent 状态缓存
```

不要把 Redis 逻辑散落在 Router 里。

---

## 十七、14｜编写 Redis Client
打开：

```text
app/redis/client.py
```

写入：

```python
import redis.asyncio as redis

from app.core.config import settings


redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def close_redis():
    await redis_client.aclose()
```

---

### 【重点内容】
这里我们创建了全局 Redis Client。

重点看：

```python
decode_responses=True
```

这表示 Redis 返回字符串，而不是 bytes。

如果不加这个参数，你可能会拿到：

```python
b"hello"
```

加上后就是：

```python
"hello"
```

对课程学员更友好。

这里还有：

```python
await redis_client.aclose()
```

用于关闭 Redis 连接。

redis-py 的 asyncio 文档也提醒，异步 Redis 连接需要显式关闭。

---

## 十八、15｜编写 Redis Dependency
创建：

```text
app/dependencies/redis.py
```

写入：

```python
from redis.asyncio import Redis

from app.redis.client import redis_client


async def get_redis_client() -> Redis:
    return redis_client
```

---

### 【重点内容】
现在我们把 Redis Client 封装成 FastAPI 依赖。

后面接口里可以写：

```python
redis: Redis = Depends(get_redis_client)
```

这样和数据库一样，都是通过 Depends 注入。

目前 Redis Client 是全局连接池对象。

真实项目里也经常这样使用。

---

## 十九、16｜创建 Redis 测试脚本
创建：

```text
scripts/test_redis.py
```

写入：

```python
import asyncio

from app.redis.client import close_redis, redis_client


async def main():
    pong = await redis_client.ping()
    print("PING:", pong)

    await redis_client.set("course:name", "AI Agent 全栈开发实战", ex=60)
    value = await redis_client.get("course:name")
    print("course:name =", value)

    ttl = await redis_client.ttl("course:name")
    print("ttl =", ttl)

    await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/test_redis.py
```

预期输出：

```text
PING: True
course:name = AI Agent 全栈开发实战
ttl = 60
```

---

### 【重点内容】
这个脚本用于验证 Python 是否能连上 Redis。

如果这里能成功，说明：

```text
Redis 容器正常
REDIS_URL 正确
redis-py 正常
密码正确
```

后面接口里用 Redis 就不会有太大问题。

---

## 二十、17｜Redis key 命名规范
创建：

```text
app/redis/keys.py
```

写入：

```python
def chat_response_cache_key(question_hash: str) -> str:
    return f"chat:response:{question_hash}"


def rate_limit_key(user_id: str, api_name: str) -> str:
    return f"rate_limit:{api_name}:{user_id}"


def api_key_cache_key(api_key_hash: str) -> str:
    return f"api_key:{api_key_hash}"


def conversation_recent_messages_key(conversation_id: str) -> str:
    return f"conversation:{conversation_id}:recent_messages"


def agent_run_state_key(run_id: str) -> str:
    return f"agent:run:{run_id}:state"


def lock_key(resource: str, resource_id: str) -> str:
    return f"lock:{resource}:{resource_id}"
```

---

### 【重点内容】
Redis key 命名非常重要。

不要随便写：

```text
user1
data
cache
test
```

项目稍微一大，Redis 里会非常乱。

推荐使用这种格式：

```text
业务模块:资源类型:资源ID:字段
```

比如：

```text
chat:response:hash_xxx
rate_limit:chat:u_10001
conversation:c_10001:recent_messages
agent:run:run_10001:state
lock:knowledge_base:kb_001
```

这样一看 key 就知道它是什么。

---

## 二十一、18｜会话最近消息缓存
创建：

```text
app/redis/cache.py
```

写入：

```python
import json

from redis.asyncio import Redis

from app.core.config import settings
from app.redis.keys import conversation_recent_messages_key
from app.schemas.chat import ChatMessage, MessageRole


async def cache_recent_messages(
    redis: Redis,
    conversation_id: str,
    messages: list[ChatMessage],
    ttl_seconds: int | None = None,
):
    key = conversation_recent_messages_key(conversation_id)

    data = [
        {
            "role": message.role.value,
            "content": message.content,
        }
        for message in messages
    ]

    await redis.set(
        key,
        json.dumps(data, ensure_ascii=False),
        ex=ttl_seconds or settings.redis_default_ttl_seconds,
    )


async def get_cached_recent_messages(
    redis: Redis,
    conversation_id: str,
) -> list[ChatMessage] | None:
    key = conversation_recent_messages_key(conversation_id)
    value = await redis.get(key)

    if not value:
        return None

    data = json.loads(value)

    return [
        ChatMessage(
            role=MessageRole(item["role"]),
            content=item["content"],
        )
        for item in data
    ]
```

---

### 【重点内容】
这里我们实现了会话最近消息缓存。

为什么要缓存最近消息？

因为 AI Chat 经常要读取最近几轮上下文。

如果每次都查 PostgreSQL，压力会比较大。

我们可以把最近几轮消息缓存到 Redis。

比如 key：

```text
conversation:c_10001:recent_messages
```

value 是 JSON：

```json
[
  {
    "role": "user",
    "content": "什么是 AI Agent？"
  },
  {
    "role": "assistant",
    "content": "AI Agent 是..."
  }
]
```

设置过期时间：

```text
300 秒
```

这样既能提升性能，又不会长期占用内存。

---

## 二十二、19｜在 ConversationService 中使用缓存
打开：

```text
app/services/conversation_service.py
```

修改 `get_conversation_messages`，新增 Redis 参数：

```python
from redis.asyncio import Redis

from app.redis.cache import (
    cache_recent_messages,
    get_cached_recent_messages,
)
```

修改函数：

```python
async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: str,
    redis: Redis | None = None,
) -> ConversationMessagesResponse:
    if redis:
        cached_messages = await get_cached_recent_messages(
            redis=redis,
            conversation_id=conversation_id,
        )

        if cached_messages is not None:
            return ConversationMessagesResponse(
                conversation_id=conversation_id,
                messages=cached_messages,
            )

    messages = await conversation_repository.get_messages(
        db=db,
        conversation_id=conversation_id,
    )

    if redis:
        await cache_recent_messages(
            redis=redis,
            conversation_id=conversation_id,
            messages=messages[-10:],
        )

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )
```

---

### 【重点内容】
现在查询会话消息时，流程变成：

```text
先查 Redis
 ↓
Redis 命中，直接返回
 ↓
Redis 没命中，查 PostgreSQL
 ↓
把最近消息写入 Redis
 ↓
返回结果
```

这就是典型缓存模式：

```text
Cache Aside
```

也叫旁路缓存。

后面我们很多场景都会用这个模式。

---

## 二十三、20｜改造 Conversations Router 注入 Redis
打开：

```text
app/api/v1/conversations.py
```

导入：

```python
from redis.asyncio import Redis
from app.dependencies.redis import get_redis_client
```

修改获取消息接口：

```python
@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[ConversationMessagesResponse],
)
async def get_messages(
    conversation_id: str = Path(..., description="会话 ID"),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> ApiResponse[ConversationMessagesResponse]:
    result = await get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        redis=redis,
    )

    return ApiResponse[ConversationMessagesResponse](
        data=result
    )
```

---

### 【重点内容】
现在 Router 同时注入：

```python
db: AsyncSession = Depends(get_db_session)
redis: Redis = Depends(get_redis_client)
```

这就是典型企业接口。

一个接口可能同时依赖：

```text
数据库
Redis
当前用户
权限
LLM Provider
```

Depends 的价值在这里就体现出来了。

---

## 二十四、21｜测试会话缓存
第一步，创建会话并发送消息。

第二步，第一次查询：

```bash
curl "http://127.0.0.1:8000/api/v1/conversations/c_xxxxxxxx/messages" \
  -H "x-api-key: dev-api-key-123"
```

第一次会查 PostgreSQL，然后写入 Redis。

第三步，打开 Redis Insight，查看 key：

```text
conversation:c_xxxxxxxx:recent_messages
```

第四步，第二次查询，会从 Redis 返回。

---

### 【重点内容】
演示时可以在 Service 里加两行日志：

```python
logger.info("conversation_messages_cache_hit")
logger.info("conversation_messages_cache_miss")
```

这样学员能清楚看到：

```text
第一次 miss
第二次 hit
```

这比单纯讲缓存概念更直观。

---

## 二十五、22｜LLM 响应缓存
有些问题用户会反复问。

比如：

```text
什么是 AI Agent？
什么是 RAG？
LangChain 和 LangGraph 区别？
```

这些回答可以短时间缓存。

创建缓存方法：

修改：

```text
app/redis/cache.py
```

增加：

```python
import hashlib

from app.redis.keys import chat_response_cache_key


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


async def get_cached_chat_response(
    redis: Redis,
    question: str,
) -> str | None:
    key = chat_response_cache_key(hash_text(question))
    return await redis.get(key)


async def cache_chat_response(
    redis: Redis,
    question: str,
    answer: str,
    ttl_seconds: int = 300,
):
    key = chat_response_cache_key(hash_text(question))

    await redis.set(
        key,
        answer,
        ex=ttl_seconds,
    )
```

---

### 【重点内容】
这里我们做 LLM 响应缓存。

注意不要直接把完整问题当 key。

因为问题可能很长，也可能包含特殊字符。

所以我们用：

```python
sha256
```

做一个 hash。

比如问题：

```text
什么是 AI Agent？
```

变成：

```text
chat:response:abc123...
```

然后把回答缓存 300 秒。

---

## 二十六、23｜ChatService 使用响应缓存
打开：

```text
app/services/chat_service.py
```

增加导入：

```python
from redis.asyncio import Redis

from app.redis.cache import (
    cache_chat_response,
    get_cached_chat_response,
)
```

修改函数签名：

```python
async def chat_with_ai(
    request: ChatRequest,
    db: AsyncSession | None = None,
    redis: Redis | None = None,
) -> ChatResponse:
```

在生成 answer 前增加：

```python
if redis:
    cached_answer = await get_cached_chat_response(
        redis=redis,
        question=latest_user_message,
    )

    if cached_answer:
        logger.info("chat_response_cache_hit")

        return ChatResponse(
            answer=cached_answer,
            model=model,
            session_id=request.session_id,
            message_id=f"m_{uuid.uuid4().hex[:8]}",
            usage=TokenUsage(),
            sources=[],
            trace_id=f"trace_{uuid.uuid4().hex[:8]}",
        )
```

在生成 answer 后增加：

```python
if redis:
    await cache_chat_response(
        redis=redis,
        question=latest_user_message,
        answer=answer,
    )
```

---

### 【重点内容】
现在 ChatService 会先查 Redis。

如果缓存命中，直接返回。

如果缓存没命中，才继续执行模拟 LLM 逻辑。

真实项目里，这可以降低：

```text
LLM 调用成本
接口耗时
第三方模型压力
```

但是注意，不是所有问题都适合缓存。

比如：

```text
带用户隐私的问题
强依赖实时数据的问题
强上下文相关的问题
```

不适合简单缓存。

这一章只是让大家掌握基础模式。

---

## 二十七、24｜改造 Chat Router 注入 Redis
打开：

```text
app/api/v1/chat.py
```

导入：

```python
from redis.asyncio import Redis
from app.dependencies.redis import get_redis_client
```

修改 Chat 接口：

```python
@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(
        request=request,
        db=db,
        redis=redis,
    )

    result.trace_id = f"{result.trace_id}_user_{current_user.user_id}"

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

## 二十八、25｜测试 LLM 响应缓存
第一次请求：

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
    "stream": false
  }'
```

第二次请求相同问题。

终端日志应该看到：

```text
chat_response_cache_hit
```

Redis Insight 里可以看到类似 key：

```text
chat:response:xxxxxxxxxxxxxxxx
```

---

### 【重点内容】
现在相同问题第二次请求会命中 Redis。

你可以看两点：

```text
接口耗时变短
日志出现 cache_hit
Redis 里出现 chat:response:xxx
```

这就是缓存效果。

---

## 二十九、26｜接口限流 Rate Limit
AI 接口很容易被刷。

比如某个用户疯狂调用：

```http
POST /chat
```

会导致：

```text
模型成本暴涨
服务压力变大
其他用户受影响
```

所以要限流。

打开：

```text
app/redis/rate_limit.py
```

写入：

```python
from redis.asyncio import Redis

from app.core.config import settings
from app.redis.keys import rate_limit_key


async def check_rate_limit(
    redis: Redis,
    user_id: str,
    api_name: str,
) -> tuple[bool, int, int]:
    key = rate_limit_key(user_id=user_id, api_name=api_name)

    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, settings.rate_limit_window_seconds)

    ttl = await redis.ttl(key)

    allowed = current <= settings.rate_limit_max_requests

    return allowed, current, ttl
```

---

### 【重点内容】
这里我们用 Redis 做最简单的固定窗口限流。

逻辑是：

```text
用户第一次请求
 ↓
INCR key 得到 1
 ↓
设置过期时间 60 秒
 ↓
后续请求继续 INCR
 ↓
超过 20 次就拒绝
```

比如 key：

```text
rate_limit:chat:u_10001
```

过期时间 60 秒。

最多请求 20 次。

这就是最基础的限流。

---

## 三十、27｜创建限流依赖
打开：

```text
app/dependencies/auth.py
```

或者新建：

```text
app/dependencies/rate_limit.py
```

推荐新建：

```text
app/dependencies/rate_limit.py
```

写入：

```python
from fastapi import Depends, HTTPException, status
from redis.asyncio import Redis

from app.dependencies.auth import get_current_user
from app.dependencies.redis import get_redis_client
from app.redis.rate_limit import check_rate_limit
from app.schemas.user import CurrentUser


async def chat_rate_limit(
    current_user: CurrentUser = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client),
):
    allowed, current, ttl = await check_rate_limit(
        redis=redis,
        user_id=current_user.user_id,
        api_name="chat",
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求太频繁，请 {ttl} 秒后再试。当前窗口请求次数：{current}",
        )
```

---

### 【重点内容】
现在我们把限流封装成依赖：

```python
chat_rate_limit
```

它依赖：

```text
当前用户
Redis Client
```

如果超过限制，就抛：

```text
429 Too Many Requests
```

==这就是 AI 接口保护的基础。==

---

## 三十一、28｜在 Chat Router 上加限流
修改：

```text
app/api/v1/chat.py
```

导入：

```python
from app.dependencies.rate_limit import chat_rate_limit
```

在 Chat 接口增加依赖：

```python
@router.post(
    "/chat",
    response_model=ApiResponse[ChatResponse],
    dependencies=[Depends(chat_rate_limit)],
)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> ApiResponse[ChatResponse]:
    result = await chat_with_ai(
        request=request,
        db=db,
        redis=redis,
    )

    result.trace_id = f"{result.trace_id}_user_{current_user.user_id}"

    return ApiResponse[ChatResponse](
        data=result
    )
```

---

### 【重点内容】
现在 Chat 接口有了限流。

注意这里：

```python
dependencies=[Depends(chat_rate_limit)]
```

表示只执行限流依赖，不需要在函数里拿返回值。

限流通过，继续执行接口。

限流失败，直接返回 429。

==这就是第 09 章 Depends 的实际应用。==

---

## 三十二、29｜测试接口限流
为了方便测试，可以先把 `.env` 改小一点：

```text
RATE_LIMIT_MAX_REQUESTS=3
RATE_LIMIT_WINDOW_SECONDS=60
```

重启服务。

连续请求 4 次 Chat。

第 4 次应该返回：

```json
{
  "code": 40000,
  "message": "请求太频繁，请 56 秒后再试。当前窗口请求次数：4",
  "data": null,
  "trace_id": "trace_xxx"
}
```

---

### 【重点内容】
这里我们的异常处理器会把 HTTPException 统一成错误响应。

HTTP 状态码是：

```text
429
```

业务 code 这里可能仍然映射成：

```text
40000
```

后面可以在 ErrorCode 里单独增加：

```text
RATE_LIMITED = 42900
```

这是课后任务。

---

## 三十三、30｜Agent 任务状态缓存
Agent 经常是长任务。

比如：

```text
Deep Research
生成报告
批量分析数据
多工具调用
长流程任务
```

这类任务不能只靠同步接口返回。

我们可以用 Redis 保存任务状态。

打开：

```text
app/redis/agent_state.py
```

写入：

```python
import json
from typing import Any

from redis.asyncio import Redis

from app.redis.keys import agent_run_state_key


async def set_agent_run_state(
    redis: Redis,
    run_id: str,
    state: dict[str, Any],
    ttl_seconds: int = 3600,
):
    key = agent_run_state_key(run_id)

    await redis.set(
        key,
        json.dumps(state, ensure_ascii=False),
        ex=ttl_seconds,
    )


async def get_agent_run_state(
    redis: Redis,
    run_id: str,
) -> dict[str, Any] | None:
    key = agent_run_state_key(run_id)
    value = await redis.get(key)

    if not value:
        return None

    return json.loads(value)
```

---

### 【重点内容】
这里我们实现 Agent Run 状态缓存。

比如 run_id 是：

```text
run_10001
```

Redis key 是：

```text
agent:run:run_10001:state
```

value 可以是：

```json
{
  "status": "running",
  "current_step": "search_web",
  "progress": 40
}
```

这样前端可以轮询查询任务状态。

---

## 三十四、31｜新增 Agent 状态接口
修改：

```text
app/api/v1/agents.py
```

增加导入：

```python
import uuid

from redis.asyncio import Redis

from app.dependencies.redis import get_redis_client
from app.redis.agent_state import (
    get_agent_run_state,
    set_agent_run_state,
)
```

新增接口：

```python
@router.post("/agents/run-async", response_model=ApiResponse[dict])
async def run_agent_async(
    request: AgentRunRequest,
    redis: Redis = Depends(get_redis_client),
    context: AgentContext = Depends(get_agent_context),
) -> ApiResponse[dict]:
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    await set_agent_run_state(
        redis=redis,
        run_id=run_id,
        state={
            "run_id": run_id,
            "agent_id": request.agent_id,
            "question": request.question,
            "status": "running",
            "current_step": "planning",
            "progress": 10,
            "trace_id": context.trace_id,
        },
    )

    return ApiResponse[dict](
        data={
            "run_id": run_id,
            "status": "running",
            "trace_id": context.trace_id,
        }
    )


@router.get("/agents/runs/{run_id}", response_model=ApiResponse[dict])
async def get_agent_run(
    run_id: str,
    redis: Redis = Depends(get_redis_client),
) -> ApiResponse[dict]:
    state = await get_agent_run_state(
        redis=redis,
        run_id=run_id,
    )

    if not state:
        return ApiResponse[dict](
            code=40400,
            message="Agent Run 不存在或已过期",
            data=None,
        )

    return ApiResponse[dict](
        data=state
    )
```

---

### 【重点内容】
现在我们模拟了一个异步 Agent 任务。

第一个接口：

```http
POST /agents/run-async
```

创建任务，把状态写入 Redis。

第二个接口：

```http
GET /agents/runs/{run_id}
```

查询任务状态。

==这就是很多 Agent 平台里的基本模式。==

真实项目里，后面可以配合：

```text
Celery
RQ
Dramatiq
Background Task
消息队列
```

异步执行任务。

Redis 保存任务状态。

---

## 三十五、32｜分布式锁入门
在 AI 项目里，有些操作不能并发执行。

比如：

```text
同一个知识库不能同时重复向量化
同一个订单不能同时被多个 Agent 修改
同一个文档不能同时被多个任务解析
同一个 Agent Run 不能重复启动
```

这时候可以用 Redis 做简单分布式锁。

打开：

```text
app/redis/lock.py
```

写入：

```python
import uuid

from redis.asyncio import Redis

from app.redis.keys import lock_key


async def acquire_lock(
    redis: Redis,
    resource: str,
    resource_id: str,
    ttl_seconds: int = 30,
) -> str | None:
    key = lock_key(resource, resource_id)
    token = str(uuid.uuid4())

    success = await redis.set(
        key,
        token,
        ex=ttl_seconds,
        nx=True,
    )

    if success:
        return token

    return None


async def release_lock(
    redis: Redis,
    resource: str,
    resource_id: str,
    token: str,
) -> bool:
    key = lock_key(resource, resource_id)

    current_token = await redis.get(key)

    if current_token != token:
        return False

    await redis.delete(key)
    return True
```

---

### 【重点内容】
这里是一个简单分布式锁。

加锁：

```python
SET key token EX 30 NX
```

其中：

```text
NX
= key 不存在才设置成功

EX 30
= 30 秒后自动过期
```

释放锁时，要先检查 token。

为什么？

因为不能释放别人加的锁。

如果当前 token 不一致，说明锁可能已经过期并被别人拿到了。

这个版本适合入门。

生产级分布式锁还要考虑更复杂的问题，比如续期、超时、Redlock 等。

这一章先掌握基本思想。

---

## 三十六、33｜缓存 API Key 校验结果
现在我们的 API Key 是直接和 settings 比较。

真实项目里，API Key 可能存数据库。

每次都查数据库会有压力。

可以用 Redis 缓存校验结果。

打开：

```text
app/redis/cache.py
```

增加：

```python
from app.redis.keys import api_key_cache_key


async def cache_api_key_user(
    redis: Redis,
    api_key_hash: str,
    user_id: str,
    ttl_seconds: int = 600,
):
    key = api_key_cache_key(api_key_hash)

    await redis.set(
        key,
        user_id,
        ex=ttl_seconds,
    )


async def get_cached_api_key_user(
    redis: Redis,
    api_key_hash: str,
) -> str | None:
    key = api_key_cache_key(api_key_hash)

    return await redis.get(key)
```

---

### 【重点内容】
这里先写 API Key 缓存工具方法。

后面真实项目中流程是：

```text
读取 x-api-key
 ↓
对 api_key 做 hash
 ↓
先查 Redis
 ↓
命中，直接拿 user_id
 ↓
未命中，查 PostgreSQL
 ↓
写入 Redis
```

这比每次都查数据库更高效。

注意，千万不要直接把明文 API Key 当 key 或 value 存 Redis。

应该存 hash。

---

## 三十七、34｜Redis 健康检查
修改：

```text
app/api/v1/health.py
```

增加导入：

```python
from fastapi import Depends
from redis.asyncio import Redis

from app.dependencies.redis import get_redis_client
```

新增接口：

```python
@router.get("/health/redis")
async def redis_health(
    redis: Redis = Depends(get_redis_client),
):
    pong = await redis.ping()

    return {
        "status": "ok" if pong else "error",
        "redis": pong,
    }
```

---

### 【重点内容】
现在我们给 Redis 加一个健康检查接口。

访问：

```text
/api/v1/health/redis
```

如果返回：

```json
{
  "status": "ok",
  "redis": true
}
```

说明 Redis 正常。

后面生产环境里，健康检查会检查：

```text
PostgreSQL
Redis
LLM Provider
Vector Database
```

这一章先把 Redis 加进去。

---

## 三十八、35｜关闭 Redis 连接
我们前面在 `client.py` 里写了：

```python
async def close_redis():
    await redis_client.aclose()
```

可以在 FastAPI lifespan 中统一关闭。

打开：

```text
app/main.py
```

引入：

```python
from contextlib import asynccontextmanager
from app.redis.client import close_redis
```

修改：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()
```

然后：

```python
app = FastAPI(
    title=settings.app_name,
    description="Python + FastAPI + LLM + Agent 开发实战",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)
```

完整片段：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import register_middleware
from app.redis.client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app_name,
        description="Python + FastAPI + LLM + Agent 开发实战",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root():
        return {
            "message": settings.app_name,
            "env": settings.app_env,
            "version": settings.app_version,
        }

    return app


app = create_app()
```

---

### 【重点内容】
这里我们使用 FastAPI lifespan。

应用关闭时，执行：

```python
await close_redis()
```

这样可以优雅关闭 Redis 连接。

这也是企业项目里比较规范的资源管理方式。

---

## 三十九、36｜Redis 常见错误一：连接失败

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

错误：

```text
ConnectionError: Error connecting to localhost:6379
```

检查 Redis 是否启动：

```bash
docker ps
```

如果没有：

```bash
docker compose up -d
```

查看日志：

```bash
docker logs ai_agent_redis
```

---

## 四十、37｜Redis 常见错误二：密码错误
错误：

```text
Authentication required
```

或者：

```text
invalid password
```

检查 `.env`：

```text
REDIS_URL=redis://:redis123@localhost:6379/0
```

检查 docker-compose：

```yaml
command: redis-server --appendonly yes --requirepass redis123
```

密码要一致。

---

## 四十一、38｜Redis 常见错误三：拿到 bytes

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

如果没有设置：

```python
decode_responses=True
```

可能拿到：

```python
b"hello"
```

解决：

```python
redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)
```

---

## 四十二、39｜Redis 常见错误四：忘记设置过期时间
错误做法：

```python
await redis.set(key, value)
```

如果是缓存类数据，应该设置过期时间：

```python
await redis.set(key, value, ex=300)
```

否则 Redis key 会越来越多。

---

## 四十三、40｜Redis 常见错误五：使用 KEYS * 扫描生产环境

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

开发环境可以：

```bash
KEYS *
```

生产环境不建议。

因为 key 很多时可能阻塞 Redis。

生产环境更推荐：

```bash
SCAN 0 MATCH chat:* COUNT 100
```

---

## 四十四、41｜Redis 常见错误六：缓存雪崩 / 击穿 / 穿透
### 【重点内容】
缓存系统里有几个常见概念。

第一：

```text
缓存雪崩
```

大量 key 同时过期，瞬间打到数据库。

第二：

```text
缓存击穿
```

某个热点 key 过期，大量请求同时打到数据库。

第三：

```text
缓存穿透
```

请求的数据本来就不存在，每次都查数据库。

这章先不深入展开，先知道这几个概念。

后面做 RAG 检索缓存、LLM 响应缓存时会继续遇到。

---

## 四十五、42｜Redis 常见错误七：把大对象塞 Redis

> [!warning] 易错点
> 这一节是易错点，动手时对照检查。

==不建议把特别大的内容直接放 Redis。==

比如：

```text
完整 PDF 内容
大段文档全文
超长 Prompt
大量 RAG chunks
```

Redis 是内存数据库。

大对象太多会浪费内存。

更合理的方式：

```text
PostgreSQL / 对象存储保存完整数据
Redis 只保存摘要、状态、ID、短期缓存
```

---

## 四十六、43｜Redis key 清理命令
开发环境可以清理课程相关 key：

```bash
redis-cli -a redis123
```

查看：

```bash
KEYS *
```

删除单个：

```bash
DEL chat:response:xxx
```

清空当前 db：

```bash
FLUSHDB
```

注意：

```text
FLUSHDB 会删除当前 Redis DB 的所有 key
生产环境不要随便执行
```

---

## 四十七、44｜本章知识点和 AI 开发场景对应表
| Redis 知识点 | AI 应用场景 |
| --- | --- |
| SET / GET | LLM 响应缓存 |
| EXPIRE / TTL | 会话缓存、验证码、临时状态 |
| INCR | API 限流、调用次数统计 |
| Hash | 用户信息缓存、API Key 缓存 |
| List | 最近消息、任务日志 |
| Redis Insight | 查看 key、调试缓存 |
| redis.asyncio | FastAPI 异步 Redis 访问 |
| Depends(get_redis_client) | 注入 Redis Client |
| Cache Aside | 会话消息缓存、RAG 检索缓存 |
| Rate Limit | 限制用户调用 AI 接口频率 |
| 分布式锁 | 防止重复处理文档、重复执行 Agent |
| Agent State | 长任务状态、进度、当前步骤 |
| Key 命名规范 | 避免 Redis key 混乱 |
| TTL | 避免缓存长期占用内存 |
| LLM Response Cache | 降低模型调用成本 |
| API Key Cache | 减少数据库查询 |


---

## 四十八、45｜本章完整复习
这一章我们完成了：

```bash
1. 理解 Redis 和 PostgreSQL 的区别
2. 理解 Redis 在 AI 项目中的作用
3. 使用 Docker Compose 安装 Redis
4. 学习 macOS Redis 安装方式
5. 推荐 Redis Insight / Tiny RDM / redis-cli 等客户端工具
6. 使用 Redis Insight 连接 Redis
7. 学习 Redis 基础命令
8. 配置 REDIS_URL
9. 安装 redis-py
10. 使用 redis.asyncio 连接 Redis
11. 创建 app/redis 目录
12. 创建 Redis Client
13. 创建 Redis Dependency
14. 创建 Redis 测试脚本
15. 设计 Redis key 命名规范
16. 实现会话最近消息缓存
17. 改造 ConversationService 使用 Redis 缓存
18. 实现 LLM 响应缓存
19. 改造 ChatService 使用响应缓存
20. 实现 Redis 接口限流
21. 使用 Depends 加 Chat 限流
22. 实现 Agent 任务状态缓存
23. 新增 Agent Run 状态接口
24. 实现简单分布式锁
25. 设计 API Key 缓存思路
26. 新增 Redis 健康检查
27. 使用 lifespan 关闭 Redis 连接
28. 总结 Redis 常见错误和排查方式
```

现在我们的项目已经具备：

```text
PostgreSQL 持久化
+
Redis 缓存与状态管理
```

==这就是企业级 AI 后端非常关键的两层数据能力。==

---

## 四十九、46｜课后任务一：新增 RAG 检索缓存
### 要求
```text
1. 在 app/redis/keys.py 新增 rag_query_cache_key
2. 在 app/redis/cache.py 新增 get_cached_rag_result
3. 新增 cache_rag_result
4. 在 rag_service.py 中先查 Redis
5. 命中 Redis 直接返回
6. 未命中再执行模拟查询
```

参考 key：

```python
def rag_query_cache_key(question_hash: str, knowledge_base_id: str) -> str:
    return f"rag:query:{knowledge_base_id}:{question_hash}"
```

---

## 五十、47｜课后任务二：新增 RATE_LIMITED 错误码
### 要求
```text
1. 在 ErrorCode 中新增 RATE_LIMITED = 42900
2. 修改 exception_handlers.py 的状态码映射
3. 429 返回 42900
4. 测试 Chat 限流错误
```

参考：

```python
if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
    return 42900
```

---

## 五十一、48｜课后任务三：实现验证码缓存
### 要求
```text
1. 创建 verification_code_key
2. 实现 cache_verification_code
3. 实现 get_verification_code
4. TTL 设置 300 秒
```

参考 key：

```python
def verification_code_key(email: str) -> str:
    return f"verification_code:{email}"
```

---

## 五十二、49｜课后任务四：实现文档解析任务状态
### 要求
```text
1. 创建 document_parse_state_key
2. 实现 set_document_parse_state
3. 实现 get_document_parse_state
4. 状态包括 pending / running / success / failed
5. 模拟 POST /documents/parse 和 GET /documents/tasks/{task_id}
```

---

## 五十三、50｜课后任务五：画出 Redis 调用链路
画出：

```http
POST /api/v1/chat
```

使用 Redis 缓存时的完整链路：

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
get_redis_client
 ↓
Chat Router
 ↓
ChatService
 ↓
Redis get chat:response:xxx
 ↓
命中：直接返回
 ↓
未命中：生成回答
 ↓
Redis set chat:response:xxx EX 300
 ↓
Response
```

---

## 五十四、51｜本章总结

> [!success] 复盘要点
> 复盘时重点看这一节。

### 【重点内容】
好了，到这里，第 12 章我们就讲完了。

这一章我们正式把 Redis 接入到了 AI Agent 后端项目里。

大家一定要记住：

```text
PostgreSQL
负责长期持久化

Redis
负责高频缓存和临时状态
```

在 AI 项目里，Redis 非常重要。

它可以用来做：

```text
会话最近消息缓存
LLM 响应缓存
RAG 检索缓存
API Key 缓存
接口限流
分布式锁
Agent 任务状态
文档解析进度
验证码
登录态
```

==这一章我们已经完成了几个核心能力：==

```bash
Redis Docker 安装
Redis Insight 调试
redis.asyncio 连接
FastAPI Depends 注入 Redis
会话缓存
LLM 响应缓存
限流
Agent 状态
分布式锁
```

现在我们的项目数据层已经从：

```text
只有 PostgreSQL
```

升级成：

```text
PostgreSQL + Redis
```

这就是企业级 AI 应用非常常见的数据架构。

---

> [!success] 一句话带走
> ==Redis 负责「快」，PostgreSQL 负责「稳」，别让它们抢活。==

> [!quote] 关于本文档
> 由原始讲义 `第 12 章｜Redis 在 AI 应用中的使用.md` 转换为 Obsidian 风格笔记；原文完整保留，未做任何删改。
> 整理日期：2026-11-22
