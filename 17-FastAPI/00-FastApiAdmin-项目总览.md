---
title: FastApiAdmin 项目总览 · 笔记集索引
tags: [FastAPI, Python, FastApiAdmin, 后端架构, 插件化, 索引]
created: 2026-11-07
source: /Users/vic/PycharmProjects/fastapiadmin
version: v3.1.0
---

# FastApiAdmin 项目总览 · 笔记集索引

> [!tldr] 一句话
> **FastApiAdmin = FastAPI 版的 RuoYi**：内核 + 插件、五层分层、RBAC + 数据权限、JWT 双 Token、国密加密、代码生成器。一套后端同时喂 Web(6110) / UniApp(6120) / Flutter(6150)。

这套笔记的目标不是"翻译项目文档"，而是**把 303 个 Python 文件讲成一个能上手改的结构**。写作时所有结论都回源码核对过，与 `docs/` 原文不一致的地方单独列在第 5 节。

---

## 一、这份笔记的来源

| 来源 | 内容 |
|---|---|
| `fastapiadmin/docs/` 5 份文档 | 快速入门与技术栈、后端技术文档、日志模块分析、国密加密实现、AI 工具规范 |
| `backend/app/` 源码 | 内核 21 个顶层模块（连子目录共 35 个 `.py`）、9 个业务插件（`app/` 内合计 270 个 `.py`） |
| `backend/pyproject.toml` | 真实依赖版本（**以此为准**，文档里的版本号有过时） |
| `AGENTS.md` + `core/plugin/README.md` | 项目自定的 4 条静默失败红线、迁移自检清单 |

---

## 二、项目地图

```mermaid
flowchart TB
    subgraph 入口层
        CLI["main.py<br/>Typer CLI"]
        UV["uvicorn<br/>factory 模式"]
        LIFE["lifespan<br/>启动与关闭"]
    end

    subgraph 内核 app/core
        DISC["discover.py<br/>路由自动发现"]
        PLG["plugin/<br/>插件装配"]
        DB["database.py<br/>异步引擎"]
        CRUD["base_crud.py<br/>泛型 CRUD"]
        AUTH["auth/<br/>JWT + 权限"]
        MW["middlewares.py<br/>中间件"]
        LIM["http_limit.py<br/>限流"]
        SCH["ap_scheduler.py<br/>调度器"]
    end

    subgraph 插件 app/plugin
        MS["module_system<br/>用户/角色/菜单/部门/日志"]
        MA["module_ai<br/>对话/知识库/RAG"]
        MT["module_task<br/>定时任务"]
        MG["module_generator<br/>代码生成"]
        MS2["module_storage<br/>对象存储"]
        MM["module_monitor<br/>监控"]
        MC["module_common<br/>上传/健康检查"]
        MAP["module_application<br/>门户"]
        ME["module_example<br/>示例模板"]
    end

    subgraph 数据层
        MYSQL[("MySQL<br/>asyncmy")]
        REDIS[("Redis<br/>缓存/会话/限流")]
        SQLITE[("SQLite<br/>测试")]
    end

    CLI --> UV --> LIFE
    LIFE --> DB
    LIFE --> PLG
    UV --> MW --> LIM --> DISC
    DISC --> MS
    DISC --> MA
    DISC --> MT
    PLG --> MS
    MS --> CRUD --> DB
    AUTH --> REDIS
    CRUD --> MYSQL
    CRUD --> SQLITE
    SCH --> REDIS
    MA --> MG
```

---

## 三、笔记导航

按"先看全貌 → 再拆内核 → 最后动手"的顺序编排：

| 编号 | 笔记 | 解决什么问题 | 关键图 |
|---|---|---|---|
| **01** | [[01-技术栈与工程结构]] | 用了哪些库、什么版本、目录怎么摆、怎么跑起来 | 三端架构图 |
| **02** | [[02-五层架构与请求全链路]] | 一次 `GET /api/v1/user/list` 到底经过哪些代码 | 请求链路时序图 |
| **03** | [[03-插件系统内核]] | 插件怎么被发现、怎么装配、槽位如何解耦 | 生命周期 + 槽位图 |
| **04** | [[04-数据层-Model-Schema-CRUD]] | ORM 基类怎么复用、CRUDBase 白送了什么 | 三层数据模型图 |
| **05** | [[05-认证鉴权-JWT与RBAC]] | Token 怎么发、Redis 存什么、权限怎么判、数据权限五档 | 登录时序图 |
| **06** | [[06-国密加密体系]] | SM2/SM3/SM4 各管什么、三端密文为何能互通 | 登录加密时序图 |
| **07** | [[07-操作日志与审计]] | 不改一行业务代码，怎么自动记录所有写操作 | 采集流程图 |
| **08** | [[08-启动流程与配置管理]] | `python main.py run` 之后按什么顺序发生了什么 | 启动时序图 |
| **09** | [[09-开发实战与踩坑清单]] | 新增一个业务模块的完整步骤 + 4 条静默失败红线 | 开发步骤图 |

> [!tip] 如果你只想先跑起来
> 跳到 [[01-技术栈与工程结构]] 第 6 节「启动三步」，5 分钟能起服务。剩下的慢慢看。

> [!info] 配套 drawio 图集
> `FastApiAdmin-架构图集.drawio`（同目录，7 页，可用 draw.io / VS Code Draw.io 插件打开继续编辑）：
> ① 系统全景（三端→内核→插件→数据层） ② 五层架构 + RuoYi 对照 ③ 请求全链路 ④ 插件发现/装配/槽位 ⑤ JWT 双 Token + RBAC ⑥ 国密加密时序 ⑦ 启动流程。
> 笔记内嵌的是 mermaid 速览图，要改图、导出大图时用这份 drawio。

---

## 四、三条阅读路径

不同目的走不同路线，不必从头读到尾：

| 路径 | 适合 | 顺序 |
|---|---|---|
| **A. 快速上手** | 只想把项目跑起来看看 | 01 → 08 → 09 |
| **B. 吃透架构** | 想理解"企业级 FastAPI 长什么样" | 02 → 03 → 04 → 05 |
| **C. 二次开发** | 要在这个模板上写业务 | 09 → 04 → 03 → 05 |

**如果只有两小时**：读 02（链路）+ 03（插件）+ 09（实战），这三篇覆盖了 80% 的日常理解成本。

---

## 五、与原始文档的 5 处偏差

整理时逐条回源码核对，发现 `docs/` 里有几处已过时或写错。**本笔记集一律以源码为准**：

| # | 原文说法 | 实际情况 | 影响 |
|---|---|---|---|
| 1 | FastAPI `^0.115`（快速入门篇） | `fastapi==0.141.1` | 版本跨度大，中间经历了 `_IncludedRouter` 兼容性变更 |
| 2 | `security.py` 负责"密码哈希" | `security.py` 只管 JWT；密码哈希在 `utils/sm_crypto_util.py` 的 `PwdUtil`（SM3 加盐） | 按原文找密码逻辑会找错文件 |
| 3 | 数据权限在 `core/auth/permission.py` | `core/auth/permission.py` 是 **RBAC 功能权限**；`core/permission.py` 才是**数据权限**（五档） | 两个文件同名易混，功能完全不同 |
| 4 | `module_example` "无 plugin.py，自动被发现" | 已有 `plugin.py` 且显式声明 `MODEL_PATHS` | 照旧描述新建插件会漏声明模型 |
| 5 | `fastapi-limiter` 用 0.2.0 | `requirements.txt` 冻结在 **0.1.6**，`pyproject.toml` 要求 `>=0.2.0` | 两处不一致；0.1.6 在 FastAPI ≥0.141 下会因遍历 `app.routes` 报错 |

> [!warning] 第 5 条值得你亲自确认
> 如果你用 `uv sync`（读 pyproject）会装到 0.2.x；如果按 `pip install -r requirements.txt` 会装到 0.1.6，**后者在 0.141 上启动会失败**。建议统一走 `uv sync`，并把 `requirements.txt` 重新冻结。

---

## 六、关键数字速查

| 项目 | 值 |
|---|---|
| 后端端口 | `6100`（`SERVER_PORT`） |
| API 前缀 | `/api/v1`（`ROOT_PATH`） |
| Swagger | `http://127.0.0.1:6100/api/v1/docs` |
| ReDoc | `http://127.0.0.1:6100/api/v1/redoc` |
| LangJin UI | `http://127.0.0.1:6100/api/v1/ljdoc` |
| 健康检查 | `GET /api/v1/common/health/ping` |
| Web 后台 | `6110` · UniApp H5 `6120` · Flutter Web `6150` |
| Python | `>= 3.14` |
| 业务插件数 | 9 个（system / ai / task / monitor / storage / generator / application / common / example） |
| 内核文件数 | 21 个顶层 `.py`，连子目录共 35 个（`app/core/`） |

---

## 七、和 Java 世界的对应关系

如果你像我一样从 RuoYi 过来，先建立这张映射表，后面所有篇章都会轻松很多：

| RuoYi / Spring 生态 | FastApiAdmin | 差异要点 |
|---|---|---|
| Spring Boot | FastAPI + Uvicorn | 一个是容器全家桶，一个只管 HTTP 层 |
| `@RestController` | `APIRouter` 模块级变量 | 路由靠**目录扫描**注册，不是注解扫描 |
| `@Autowired` | `Depends(...)` | 依赖注入是**函数式**的，不是容器托管 Bean |
| MyBatis-Plus `BaseMapper` | `CRUDBase[T, Create, Update]` | 泛型基类，Python 版更激进地"白送" |
| `@TableName` 实体 | `MappedBase` 子类 | 无 XML，无 Mapper，纯对象 |
| `@Valid` + DTO | Pydantic `Schema` | Schema 同时管**入参校验**和**出参序列化** |
| `@PreAuthorize("@ss.hasPermi('x')")` | `Depends(AuthPermission(["x"]))` | 权限字符串格式一致，形如 `模块:资源:动作` |
| `@DataScope` 注解 + AOP | `Permission(model, auth).filter_query()` | 项目里直接拼 `WHERE`，没有注解魔法 |
| `@Log` 注解 + AOP 切面 | `APIRouter(route_class=OperationLogRoute)` | 挂在**路由类**上，粒度是整组接口 |
| Spring 事件 `ApplicationEvent` | `event_bus` + `Slot` | 槽位是"可选依赖"的解法，Spring 里没有对应物 |

> [!tip] 最容易踩的认知差
> Spring 的 Bean 是**全局单例容器**；FastAPI 没有容器。所谓"依赖"就是一个可调用对象，`Depends` 负责在每次请求时调用它。所以**状态要自己管**——这就是为什么项目里到处是 `@lru_cache` 单例和模块级变量 `_limiter`。

---

## 八、下一步

- 想跑起来 → [[01-技术栈与工程结构]]
- 想看一次请求怎么走完 → [[02-五层架构与请求全链路]]
- 想加自己的业务 → [[09-开发实战与踩坑清单]]
