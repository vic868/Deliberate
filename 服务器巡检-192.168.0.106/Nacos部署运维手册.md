# Nacos 部署运维手册（192.168.0.106）

> 编写日期：2026-11-05 · 环境：vic-MS-7B23（Ubuntu，Docker 29.1.3）
> 版本：Nacos **3.2.4**（`nacos/nacos-server:v3.2.4`），单机 standalone + MySQL 外部存储
> 关联：[[Nacos-Seata学习环境建设方案|Nacos + Seata 学习环境建设方案]] · [[巡检报告|106 巡检报告]]

---

## 一、快速信息卡

| 项目 | 值 |
|---|---|
| 宿主机 | `192.168.0.106`（vic-MS-7B23） |
| 容器名 | `nacos` |
| 容器 IP | `172.26.0.6`（所在网络 `hadoop-net`） |
| 镜像 | `nacos/nacos-server:v3.2.4` |
| 运行模式 | `standalone`（单机） |
| 部署方式 | `merged`（API 服务 + 控制台同一进程） |
| 重启策略 | `unless-stopped`（开机自启） |
| 启动脚本 | `/opt/nacos/start_nacos.sh` |
| 配置文件 | `/opt/nacos/conf-rw/application.properties` |
| 日志目录 | `/opt/nacos/logs`（挂载到容器 `/home/nacos/logs`） |
| 后端存储 | MySQL `mysql:3306/nacos`（复用 106 已有 mysql 容器，16 张表） |
| 状态 | ✅ 运行中，API 与控制台均验证通过 |

---

## 二、访问地址

| 用途 | 地址 | 说明 |
|---|---|---|
| **控制台（Web 管理端）** | **http://192.168.0.106:28880/** | 自动跳转 `/next/`（Nacos 3.x 新版界面） |
| Server API | http://192.168.0.106:28848/nacos | HTTP 接口根路径 |
| 健康检查 | http://192.168.0.106:28848/nacos/actuator/health | 返回 `{"status":"UP"}` |
| gRPC（SDK 客户端用） | `192.168.0.106:29848` | 服务注册发现长连接 |
| gRPC（集群通信） | `192.168.0.106:29849` | 单机模式一般不用 |

### 端口映射对照

| 宿主机端口 | 容器端口 | 用途 |
|---|---|---|
| `28848` | 8848 | HTTP Server API |
| `28880` | 8080 | **Console 控制台** |
| `29848` | 9848 | gRPC（SDK） |
| `29849` | 9849 | gRPC（集群） |

> **为什么不是标准的 8848？** 106 上端口规划统一加了 `2` 前缀做隔离，避免和宿主机其他服务冲突。
> **特别注意 8080**：宿主机 8080 已被 `hbase` 容器占用，所以控制台改用 **28880**。

---

## 三、账号密码

| 项目 | 值 |
|---|---|
| 用户名 | `nacos` |
| 密码 | `j8sA#mfC` |
| 权限 | `ROLE_ADMIN` / `globalAdmin = true`（超级管理员） |

**使用范围说明**：

- **控制台登录**：需要上述账号密码（`nacos.core.auth.console.enabled=true`）。
- **SDK 客户端接入**：**不需要**鉴权（`nacos.core.auth.enabled=false`），配置中心/注册中心可直接读写。
- 该密码是 Nacos 3.x 初始化接口**自动生成**的随机密码，不是手工设置。

### 修改密码

```bash
# 在 106 上执行
curl -X PUT "http://127.0.0.1:28848/nacos/v3/auth/user" \
  -d "username=nacos&newPassword=你的新密码"
```

> 注意：初始化接口 `POST /nacos/v3/auth/user/admin` **会忽略传入的 password 字段**，由服务端生成随机密码并返回，所以别指望用它指定密码。

### 遗留账号

`nacos.users` 表里还有一个 `admin` 账号：**未绑定任何角色、密码未知**，是初始化过程产生的空壳，不影响使用。如需清理：

```bash
docker exec mysql mysql -uroot -proot123 \
  -e "delete from nacos.users where username='admin';"
```

---

## 四、Docker 启动命令

完整脚本（`/opt/nacos/start_nacos.sh`）：

```bash
docker run -d --name nacos \
  --network hadoop-net \
  --restart unless-stopped \
  -p 28848:8848 -p 28880:8080 -p 29848:9848 -p 29849:9849 \
  -e MODE=standalone \
  -e DEPLOYMENT=merged \
  -e JVM_XMS=512m -e JVM_XMX=512m -e JVM_XMN=256m \
  -e NACOS_AUTH_ENABLE=false \
  -e NACOS_AUTH_TOKEN='Dc1EaFexZEEQZ/xU3nj4E0DF5CbSC1YYoRhv8ESykf8=' \
  -e NACOS_AUTH_IDENTITY_KEY=serverIdentity \
  -e NACOS_AUTH_IDENTITY_VALUE=securityPass123456 \
  -v /opt/nacos/conf-rw/application.properties:/home/nacos/conf/application.properties \
  -v /opt/nacos/logs:/home/nacos/logs \
  --entrypoint /bin/bash \
  nacos/nacos-server:v3.2.4 \
  -c 'exec bin/docker-startup.sh'
```

### 参数逐条说明

| 参数 | 作用 |
|---|---|
| `--network hadoop-net` | 加入 hadoop 网络，才能用 `mysql` 主机名连数据库 |
| `--restart unless-stopped` | 开机自启，异常退出自动拉起 |
| `-p 28848:8848` | HTTP API |
| `-p 28880:8080` | 控制台 |
| `-p 29848:9848` | gRPC SDK 端口 |
| `-p 29849:9849` | gRPC 集群端口 |
| `MODE=standalone` | 单机模式，内嵌 derby 的替代是外部 MySQL |
| `DEPLOYMENT=merged` | 3.x 关键项：API 服务与控制台合并成一个进程 |
| `JVM_XMS/XMX/XMN` | JVM 堆 512m，学习环境够用 |
| `NACOS_AUTH_ENABLE=false` | 关闭客户端鉴权，避免 SDK 连不上 |
| `NACOS_AUTH_TOKEN` | 3.x 必填，集群间通信密钥（Base64） |
| `NACOS_AUTH_IDENTITY_KEY/VALUE` | 3.x 必填，服务端身份标识 |
| `-v .../application.properties` | 用宿主机配置覆盖容器内默认配置 |
| `-v /opt/nacos/logs` | 日志外挂，方便排查 |
| `--entrypoint /bin/bash -c 'exec ...'` | 覆盖入口，显式执行 docker-startup.sh |

---

## 五、配置文件

路径：`/opt/nacos/conf-rw/application.properties`

```properties
# ---- 基础 ----
nacos.server.main.port=8848
nacos.server.contextPath=/nacos
# 3.x：控制台独立端口与 gRPC 端口
nacos.console.port=8080
# nacos.remote.server.grpc.cluster.port=9849

# ---- 数据库（复用 106 现有 mysql 容器）----
spring.sql.init.platform=mysql
db.num=1
db.url.0=jdbc:mysql://mysql:3306/nacos?characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true&useUnicode=true&useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true
db.user.0=root
db.password.0=root123

# ---- 鉴权 ----
# 学习环境先关掉客户端鉴权，避免 SDK 连不上；控制台账号密码仍然生效
nacos.core.auth.enabled=false
nacos.core.auth.admin.enabled=true
nacos.core.auth.console.enabled=true
nacos.core.auth.caching.enabled=true
nacos.core.auth.system.type=nacos
# 3.x 必填，否则起不来
nacos.core.auth.server.identity.key=serverIdentity
nacos.core.auth.server.identity.value=securityPass123456
nacos.core.auth.plugin.nacos.token.secret.key=VGhpc0lzTXlDdXN0b21TZWNyZXRLZXkwMTIzNDU2Nzg5MDEyMzQ1Ng==
```

### 关键配置说明

| 配置项 | 说明 |
|---|---|
| `nacos.server.main.port` | **3.x 的主服务端口**。2.x 时代写 `server.port`，3.x 已废弃 |
| `nacos.console.port` | **3.x 新增**，控制台独立端口，默认 8080 |
| `nacos.core.auth.enabled` | 客户端（SDK）鉴权总开关，学习环境关掉 |
| `nacos.core.auth.console.enabled` | 控制台登录鉴权，保持开启 |
| `nacos.core.auth.plugin.nacos.token.secret.key` | 3.x **必填**，Base64 编码且解码后 ≥ 32 字节 |
| `db.url.0` | 用容器名 `mysql` 而非 IP，依赖 `hadoop-net` 网络 |
| `spring.sql.init.platform=mysql` | 指定使用 MySQL 建表脚本 |

---

## 六、常用运维命令

```bash
# 查看状态
docker ps --filter name=nacos

# 启动 / 停止 / 重启
docker start nacos
docker stop nacos
docker restart nacos

# 重建（改配置后必须重建，因为配置是启动时加载的）
docker rm -f nacos && bash /opt/nacos/start_nacos.sh

# 查看日志
docker logs -f --tail 200 nacos

# 只看启动关键节点
docker logs nacos 2>&1 | grep -iE "started successfully|FAILED|Port"

# 健康检查
curl http://127.0.0.1:28848/nacos/actuator/health

# 进容器
docker exec -it nacos bash

# 查数据库
docker exec mysql mysql -uroot -proot123 -e "use nacos; show tables;"
```

### 启动成功的标志

日志里应出现这三行（缺任何一行都说明有问题）：

```text
Nacos started successfully in stand alone mode with external storage
Nacos Server API started successfully
Nacos Console started successfully      ← 控制台起没起来就看这行
```

---

## 七、客户端接入

### Spring Boot / Spring Cloud Alibaba

```yaml
spring:
  cloud:
    nacos:
      discovery:
        server-addr: 192.168.0.106:28848
        # gRPC 端口由客户端自动按「主端口 + 1000」推导 = 29848
      config:
        server-addr: 192.168.0.106:28848
        file-extension: yaml
```

> **重要**：客户端连上 `28848` 后，会自动把端口 `+1000` 推导出 gRPC 端口 `29848`。这就是为什么必须同时映射 `29848`——只映射 8848 的话，服务注册会一直失败并报连接超时。

### 命令行验证（3.x 接口）

> ⚠️ **Nacos 3.x 已移除大部分 v1 接口**（`/v1/ns/...`、`/v1/cs/configs` 均返回 404/501），
> 且 `/v3/admin/*` 管理接口**必须携带 accessToken**，不能用「免鉴权」方式直接调。

```bash
# 第 1 步：登录拿 token
TOK=$(curl -s -X POST "http://192.168.0.106:28848/nacos/v3/auth/user/login" \
  -d "username=nacos&password=j8sA#mfC" \
  | sed -E 's/.*"accessToken":"([^"]+)".*/\1/')

# 第 2 步：查服务列表
curl -H "Authorization: Bearer $TOK" \
  "http://192.168.0.106:28848/nacos/v3/admin/ns/service/list?pageNo=1&pageSize=10"

# 查命名空间
curl -H "Authorization: Bearer $TOK" \
  "http://192.168.0.106:28848/nacos/v3/admin/core/namespace/list"

# 查配置列表
curl -H "Authorization: Bearer $TOK" \
  "http://192.168.0.106:28848/nacos/v3/admin/cs/config/list?pageNo=1&pageSize=10&dataId=&groupName=&namespaceId="
```

实测返回示例（2026-11-05）：

```json
// 服务列表
{"code":0,"message":"success","data":{"totalCount":0,"pageItems":[]}}

// 命名空间（当前已有 1979 条配置）
{"code":0,"message":"success","data":[{"namespace":"public","configCount":1979}]}
```

> 注意：`/v3/admin/*` 是「管理员接口」，即使 `nacos.core.auth.enabled=false` 也要求 token，
> 因为受 `nacos.core.auth.admin.enabled=true` 控制。而 SDK 的注册/配置读写走 gRPC，不受影响。

---

## 八、本次故障与修复记录

### 现象

1. Nacos 容器不存在，`docker run` 执行后容器起不来
2. 日志反复刷 `PortInUseException: Port 8848 is already in use` / `APPLICATION FAILED TO START`
3. 控制台完全打不开
4. 即便容器起来，登录始终提示 `User not found!`

### 根因

**问题 1：配置项用了 Nacos 2.x 的写法**

配置文件里写的是 `server.port=8848`。Nacos 3.x 已改为 `nacos.server.main.port`，而 `server.port` 是 Spring Boot 的通用配置，会被**控制台上下文一并复用**，导致控制台也去绑 8848 → 与主服务冲突 → 控制台启动失败并抛异常。

**问题 2：控制台端口没映射**

脚本没映射 8080，控制台即使起来也访问不到。

**问题 3：认证数据处于互相矛盾的卡死状态**

- `nacos.users` 表 → **0 行**（无任何账号）
- `nacos.roles` 表 → 残留 `nacos / ROLE_ADMIN`

于是形成死循环：登录报 `User not found!`，初始化接口却报 `409 have admin user cannot use it.`（它看到 ROLE_ADMIN 就认为 admin 已存在）。

### 修复动作

| # | 操作 | 说明 |
|---|---|---|
| 1 | `server.port=8848` → `nacos.server.main.port=8848` | 改用 3.x 正确配置项 |
| 2 | 补充 `nacos.console.port=8080` | 显式声明控制台端口 |
| 3 | 端口映射增加 `-p 28880:8080` | 让控制台可访问（8080 被 hbase 占用） |
| 4 | 删除 `roles` 表残留的 `ROLE_ADMIN` 行 | 解除初始化接口的误判 |
| 5 | `docker restart nacos` 清认证缓存 | **关键**：不重启则改库无效 |
| 6 | 重新调用初始化接口 | 成功创建账号并返回随机密码 |

### 修复后验证

```text
Nacos Server API started successfully in 3488 ms
Nacos Console   started successfully in 1971 ms
```

- 控制台 `http://192.168.0.106:28880/` → 200
- 健康检查 → `{"status":"UP"}`
- 登录 `nacos / j8sA#mfC` → `accessToken` + `globalAdmin: true`

---

## 九、排障速查表

| 报错 / 现象 | 原因 | 处理 |
|---|---|---|
| `Port 8848 is already in use` | 配了 `server.port`，控制台抢主端口 | 删掉 `server.port`，改 `nacos.server.main.port` |
| 控制台 404 / 打不开 | 8080 未映射，或 `nacos.console.port` 配置错误 | 检查 `-p` 映射和 `nacos.console.port` |
| `User not found!` | `users` 表为空 | 重新走初始化流程 |
| `409 have admin user cannot use it.` | `roles` 表有残留 ROLE_ADMIN，或认证缓存未刷新 | 删残留行 + `docker restart nacos` |
| SDK 注册失败 / 连接超时 | gRPC 端口 9848 未映射 | 补 `-p 29848:9848` |
| 启动报数据库连接失败 | 容器不在 `hadoop-net`，解析不到 `mysql` | 检查 `--network` |
| 日志刷 `127.0.0.53:53 i/o timeout` | systemd-resolved 解析 `host.docker.internal` 超时 | 无害，可忽略或加 hosts |

---

## 十、已知隐患与待办

### 1. ⚠️ 两台机器共用一个 nacos 库（优先处理）

`192.168.0.107` 上运行着**另一个 Nacos 3.x 实例**（8848 和 console 8080 均在线），并且它正以 `root` 身份连接**本机同一个 `nacos` 数据库**（实测 4 个常驻连接）。

两个 standalone 实例共用一个后端库会互相覆盖配置、服务实例和用户数据——本次「用户表空、角色表有」的错乱，很可能就是这个原因造成的。

**建议**：二选一
- 停掉 107 上的 Nacos，统一走 106；或
- 让 107 指向独立数据库（`nacos_107`）

### 2. 宿主机 8080 端口冲突

8080 被 `hbase` 容器占用，控制台只能走 28880。若日后调整 hbase 端口，可把控制台改回 8080 更符合习惯。

### 3. 其他异常容器

| 容器 | 状态 | 说明 |
|---|---|---|
| `doris` | Exited (0)，10 天前 | 正常退出，确认是否还需要 |
| `registry` | Exited (2)，3 个月前 | 异常退出码，私有镜像仓库已停用 |

---

## 十一、变更备份清单

本次修改产生的备份文件（均在 106 上）：

```text
/opt/nacos/conf-rw/application.properties.bak.20261105-142624
/opt/nacos/start_nacos.sh.bak.20261105-142624
/tmp/nacos_auth_backup_20261105-142900.sql   # roles / permissions 表备份
```

回滚方式：

```bash
cd /opt/nacos
cp conf-rw/application.properties.bak.20261105-142624 conf-rw/application.properties
cp start_nacos.sh.bak.20261105-142624 start_nacos.sh
docker rm -f nacos && bash start_nacos.sh
```

---

> 文档由 2026-11-05 实机排查过程整理，命令与配置均与线上一致。
