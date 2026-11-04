---
title: WeKnora 部署文档
host: 192.168.0.103
date: 2026-11-04
version: 0.9.0
status: 已上线
tags: [weknora, docker, 部署, rag]
---

# WeKnora 部署文档

> 部署主机：`192.168.0.103`（hadoop-Aspire-V5-572G）
> 项目路径：`/opt/weknora/WeKnora`
> 部署日期：2026-11-04
> WeKnora 版本：`0.9.0`

---

## 一、快速访问

| 服务 | 地址 | 说明 |
|---|---|---|
| **Web 界面** | http://192.168.0.103:8082 | 日常使用入口 |
| 后端 API | http://192.168.0.103:8081 | 前端反向代理到这里 |
| API 文档 | http://192.168.0.103:8081/swagger/index.html | Swagger |
| Neo4j 浏览器 | http://192.168.0.103:7474 | 用户名 `neo4j` / 密码 `password` |
| Neo4j Bolt | `bolt://192.168.0.103:7687` | 程序连接用 |

> ⚠️ 原 80 端口被占用，前端映射到 **8082**；原 8080 被 Java 服务占用，后端映射到 **8081**。

---

## 二、登录账号

### 没有默认账号，首次使用需自己注册

```text
1. 打开 http://192.168.0.103:8082
2. 点击 Sign Up
3. 填写：用户名 / 邮箱 / 密码（密码至少 6 位）
4. 第一个注册的账号即为管理员
```

**注册模式**：`self_serve`（开放注册）。如需限制，可在系统设置里改为 `invite_register` 或 `invite_only`。

### 当前已知账号

| 用户名 | 邮箱 | 备注 |
|---|---|---|
| — | — | 部署时未创建，请自行注册 |

---

## 三、架构与组件

| 组件 | 部署方式 | 说明 |
|---|---|---|
| **frontend** | Docker 容器 `WeKnora-frontend` | Nginx 静态页 + 反代，端口 8082→80 |
| **app** | Docker 容器 `WeKnora-app` | Go 后端主服务，端口 8081→8080 |
| **docreader** | Docker 容器 `WeKnora-docreader` | 文档解析服务，gRPC 50051（仅内网） |
| **postgres** | Docker 容器 `WeKnora-postgres` | **ParadeDB v0.25.11-pg17**，自带 pg_search（BM25） |
| **redis** | **使用宿主机已有 Redis** | `192.168.0.103:6379`，无密码 |
| **neo4j** | Docker 容器 `WeKnora-neo4j` | 知识图谱，7474/7687 |

### 为什么数据库用 ParadeDB 而不是本机 PG

WeKnora 的数据库迁移强制要求三个扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector，本机 PG 已装
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- 本机 PG 自带
CREATE EXTENSION IF NOT EXISTS pg_search;  -- ❌ 本机 PG 16 没有，Ubuntu 源里也没有
```

`pg_search` 是 ParadeDB 的 BM25 全文检索扩展，官方只提供 ParadeDB 镜像和 ParadeDB 自己的 apt 源。
本机 PG 16 装不上的原因：

- `upstream.paradedb.com` / `repo.paradedb.com` 网络不通（超时）
- 服务器上 Clash 代理持续重启，无法借用
- ParadeDB 的 pg_search 主要跟随 PG 17 发布，PG 16 的包不一定存在

**结论**：用官方推荐的 `paradedb/paradedb:v0.25.11-pg17` 镜像，零风险，不动本机 PG（`retail` 等库不受影响）。

---

## 四、关键配置（`.env`）

### 4.1 端口

```ini
APP_PORT=8081          # 后端对外端口（容器内 8080）
FRONTEND_PORT=8082     # 前端对外端口（容器内 80）
```

### 4.2 数据库（容器内 ParadeDB）

```ini
DB_DRIVER=postgres
DB_HOST=postgres
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres123!@#
DB_NAME=WeKnora
```

### 4.3 Redis（用宿主机本机 Redis）

```ini
STREAM_MANAGER_TYPE=redis
REDIS_ADDR=host.docker.internal:6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_PREFIX=stream:
```

> `host.docker.internal` 依赖 compose 里的 `extra_hosts: host.docker.internal:host-gateway`，已在 app 服务中配置。

### 4.4 检索与存储

```ini
RETRIEVE_DRIVER=postgres   # 向量检索走 pgvector
STORAGE_TYPE=local         # 文件存本地卷（可改 minio）
```

### 4.5 Neo4j

```ini
# 未在 .env 中显式设置，使用 compose 默认值
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=password
```

---

## 五、对 docker-compose.yml 的修改

为适配「数据库用容器 + Redis 用宿主机」，对 compose 做了两处改动：

### 5.1 给 redis 服务加 profile（阻止其启动）

```yaml
  redis:
    profiles: ["container-redis"]     # ← 新增：默认不启动
    image: redis:7.0-alpine
```

原因：`.env` 中 `REDIS_PASSWORD` 为空，redis 容器启动命令 `--requirepass` 会失败导致一直重启。
既然用宿主机 Redis，这个容器就不需要了。

### 5.2 app 的 depends_on 去掉 redis

```yaml
    depends_on:
      postgres:
        condition: service_healthy
      docreader:
        condition: service_healthy
      # redis 已移除——使用宿主机 Redis，不在 compose 内
```

> 备份文件：`docker-compose.yml.bak`、`.env.bak.20261103-232328`

---

## 六、日常运维命令

```bash
cd /opt/weknora/WeKnora

# 查看状态
docker compose ps

# 启动（含 neo4j）
docker compose --profile neo4j up -d

# 停止（保留数据）
docker compose down

# 停止并删除数据卷（⚠️ 会清空知识库）
docker compose down -v

# 重启单个服务
docker compose restart app

# 看日志
docker compose logs -f app
docker compose logs --tail 100 frontend
```

### 6.1 健康检查

```bash
# 后端（期望 200 或 401，401 表示服务正常但需鉴权）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8081/

# 容器健康状态（app / docreader / postgres 应为 healthy）
docker compose ps --format "table {{.Name}}\t{{.Status}}"

# 数据库迁移状态（期望 dirty=f）
docker exec WeKnora-postgres psql -U postgres -d WeKnora -tAc "select version, dirty from schema_migrations;"

# 表数量（当前 89）
docker exec WeKnora-postgres psql -U postgres -d WeKnora -tAc "select count(*) from information_schema.tables where table_schema='public';"

# 扩展列表（应有 vector / pg_search / pg_trgm）
docker exec WeKnora-postgres psql -U postgres -d WeKnora -tAc "select extname from pg_extension;"
```

### 6.2 数据备份

```bash
# 备份数据库
docker exec WeKnora-postgres pg_dump -U postgres -d WeKnora | gzip > ~/backup/weknora-$(date +%F).sql.gz

# 备份文件存储（数据卷）
docker run --rm -v weknora_data-files:/data -v ~/backup:/backup alpine \
  tar czf /backup/weknora-files-$(date +%F).tar.gz -C /data .
```

### 6.3 恢复

```bash
gunzip -c ~/backup/weknora-2026-11-04.sql.gz | docker exec -i WeKnora-postgres psql -U postgres -d WeKnora
```

---

## 七、数据卷

```bash
docker volume ls | grep weknora
```

| 数据卷 | 用途 |
|---|---|
| `weknora_postgres-data` | 数据库全部数据 |
| `weknora_data-files` | 上传的文档、知识库文件 |
| `weknora_docreader-tmp` | 文档解析临时文件 |
| `weknora_neo4j-data` | Neo4j 图谱数据 |

---

## 八、已验证项

| 检查项 | 结果 | 时间 |
|---|---|---|
| 数据库迁移完成 | ✅ `134\|f`（dirty=false） | 2026-11-04 09:46 |
| 建表数量 | ✅ 89 张 | 2026-11-04 09:46 |
| 扩展安装 | ✅ vector、pg_search、pg_ivm、postgis、pg_trgm 等 | 2026-11-04 09:46 |
| 注册接口 | ✅ `{"success":true}` | 2026-11-04 09:46 |
| app 健康检查 | ✅ healthy | 2026-11-04 09:46 |
| docreader | ✅ healthy | 2026-11-04 09:46 |
| 宿主机 Redis 连通 | ✅（dbsize 29，有 WeKnora 写入的 key） | 2026-11-04 09:46 |

---

## 九、已知问题与说明

### 9.1 langfuse 追踪报错（无害）

```text
traces export: processor export timeout: ... lookup langfuse-web ... server misbehaving
```

**原因**：`.env` 里启用了 Langfuse LLM 观测，但未部署 langfuse 服务。
**影响**：仅日志噪音，不影响功能。如需关闭：

```bash
grep -n "LANGFUSE" .env | head
# 将 LANGFUSE_ENABLED 设为 false
```

### 9.2 宿主机 PG 未使用

本机 PostgreSQL 16（端口 5432）保持原样，WeKnora 未使用它。
之前为它创建的库和用户可保留或清理：

```bash
# 如需清理（不影响 retail 等其他库）
PGPASSWORD='Leihen2000.' psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS weknora;"
PGPASSWORD='Leihen2000.' psql -h 127.0.0.1 -U postgres -c "DROP ROLE IF EXISTS weknora;"
```

### 9.3 宿主机 Redis 与 WeKnora 共用

WeKnora 使用宿主机 Redis 的 **DB 0**，key 前缀 `stream:`。
如果有其他应用也用 DB 0，建议给 WeKnora 换一个 DB 索引：

```bash
sed -i 's|^REDIS_DB=0|REDIS_DB=1|' .env
docker compose up -d app
```

### 9.4 没有默认管理员账号

WeKnora 无内置账号，第一个注册的用户即为管理员。务必在开放注册后立刻注册，避免他人抢注。

---

## 十、下一步：配置 LLM 模型

WeKnora 需要配置至少一个 LLM 才能做问答。在 Web 界面里：

```text
登录 → 设置（Settings）→ 模型配置（Models）→ 添加模型
```

需要填：
- 模型提供方（OpenAI / DeepSeek / 通义千问 / Ollama 等）
- API Key
- Base URL（国内用兼容 OpenAI 协议的服务）
- 模型名（如 `deepseek-chat`、`qwen-plus`）

**本地模型方案**：如机器上有 Ollama，可把 Base URL 指向 `http://host.docker.internal:11434/v1`。

---

## 十一、故障排查速查

| 现象 | 排查命令 | 常见原因 |
|---|---|---|
| 前端打不开 | `docker compose ps frontend`<br>`ss -lntp \| grep 8082` | 端口冲突 |
| 登录后空白 | `docker logs WeKnora-app \| tail -50` | 数据库迁移未完成 |
| 注册报 `failed to create workspace` | `select version,dirty from schema_migrations;` | 迁移 dirty=true（扩展缺失） |
| 文档上传失败 | `docker logs WeKnora-docreader` | docreader unhealthy |
| 检索无结果 | 检查 Neo4j / pgvector 状态 | 向量未生成，检查模型配置 |
| Redis 连接失败 | `docker exec WeKnora-app sh -c "nc -zv host.docker.internal 6379"` | 宿主机 Redis 未启动 |

---

## 十二、变更记录

| 日期 | 操作 |
|---|---|
| 2026-11-03 23:20 | 备份 `.env` |
| 2026-11-03 23:25 | 尝试用宿主机 PG 16（失败：缺 pg_search） |
| 2026-11-04 09:40 | 切换 ParadeDB 容器 |
| 2026-11-04 09:44 | redis 容器加 profile，改用宿主机 Redis |
| 2026-11-04 09:46 | 迁移完成、注册测试通过，部署上线 |
