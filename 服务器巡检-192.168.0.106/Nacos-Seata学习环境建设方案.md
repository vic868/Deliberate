# Nacos + Seata 学习环境建设方案

> 编写日期：2026-10-08 · 基于 192.168.0.106（主力）+ 192.168.0.103（业务机）
> 目标：搭建可动手实践的微服务注册中心（Nacos）+ 分布式事务（Seata）学习环境
> 关联：[[服务器巡检-192.168.0.103/巡检报告|103 巡检报告]] · [[服务器巡检-192.168.0.106/巡检报告|106 巡检报告]]

---

## 一、资源评估（实测）

| | **106 vic-MS-7B23** | **103 hadoop-Aspire** |
|---|---|---|
| CPU | i5-8400 6C/6T | i5-3337U 2C/4T（2013 年） |
| 内存 | 45G（**可用 19G**） | 11G（**可用 8.6G**） |
| 磁盘 | 116G 可用 | 145G 可用 |
| 现状 | Kafka/MySQL/Redis/ELK/HDFS/Hive/Flink/k3s | 风控系统/MySQL/Redis/PostgreSQL |
| 候选端口 | 8848/9848/9849/7091/8091 全空闲 | 同样全空闲 |

**结论**：资源完全够——Nacos(~1G) + Seata(~1G) + 3 个 demo 服务(~2G) ≈ 4G，两台任一台都放得下。

---

## 二、推荐拓扑（分阶段，先通后分布）

### 阶段 1：单机跑通（推荐先做，1~2 小时见效果）

```text
106 一台全包，先理解"注册 + 分布式事务"的完整闭环
┌─────────────────────────── 192.168.0.106 ───────────────────────────┐
│  Nacos 2.x (8848/9848/9849)  ← 注册中心 + 配置中心                    │
│  Seata Server 2.x (7091/8091) ← TC 事务协调器                         │
│  MySQL 8.0 (3306, 已有容器)   ← nacos_config / seata / seata_demo 三库 │
│  order-service(8081) / stock-service(8082) / account-service(8083)    │
└──────────────────────────────────────────────────────────────────────┘
```

### 阶段 2：跨机分布式（学习价值最高的一步）

```text
106（中间件）                          103（业务机）
Nacos ◄──────── 服务注册 ────────────  order-service(8081)
Seata TC ◄────── 事务协调 ───────────  account-service(8082)
MySQL(元数据)                          stock-service(8083) ← 放 106 也行
                                       MySQL 8.0（业务库 seata_demo）
```

**为什么值得拆开**：只有跨机才能真实体会
- 服务注册时的 **IP 选取问题**（容器内注册成 172.x 内网 IP → 外界调不通，经典坑）
- Seata **TC 与 RM 的跨机通信**（`seata.registry`、`seata.service.grouplist` 配置）
- 网络延迟/断连对全局事务的影响

### 备选：全放 103

103 内存 8.6G 也够（Nacos 1G + Seata 1G + 3 服务 2G ≈ 4G），但 **CPU 只有 2C/4T**，三个 Spring Boot + Nacos + Seata 同时启动会明显卡；且 103 是业务机，学习环境炸了会影响风控系统。**不推荐**。

---

## 三、版本选型（兼容矩阵是踩坑重灾区）

**推荐现代栈**（理由见下）：

| 组件 | 版本 | 说明 |
|---|---|---|
| JDK | **17** | Boot 3.x 要求 17+；106 已有 `eclipse-temurin:17` 镜像 |
| Spring Boot | 3.2.x | |
| Spring Cloud | 2023.0.x | |
| **Spring Cloud Alibaba** | **2023.0.1.0 / 2023.0.3.x** | 与 Boot 3.2 匹配 |
| **Nacos** | **2.3.x / 2.4.x** | ⚠️ 2.x 必须放行 **三个端口**（8848/9848/9849） |
| **Seata** | **2.x**（2.0/2.1/2.3） | 2.x 控制台在 7091，TC 在 8091 |

**为什么不用经典版（Boot 2.7 + SCA 2021.0.x + JDK 8）**：
- 网上教程多、但已过时；106 主机上的 `/opt/jdk-25.0.3` 跑不动 Boot 2/3（太新），而 17 的镜像现成
- 现代栈的坑（配置键改名、gRPC 端口）本身就是当下生产环境要会的

> [!warning] 不要用 JDK 25 跑这套
> 106 主机上是 JDK 25（tarball）——Spring Boot 3.2 支持 17~21，**25 大概率启动报错**。统一用 17（容器镜像或 apt 装 openjdk-17）。

---

## 四、端口与数据库规划

### 端口（两台均实测空闲）

| 服务 | 端口 | 说明 |
|---|---|---|
| Nacos HTTP/控制台 | **8848** | 浏览器访问 `http://192.168.0.106:8848/nacos` |
| Nacos 客户端 gRPC | **9848** | = 8848+1000，**2.x 新增，必须放行** |
| Nacos 服务端 gRPC | **9849** | = 8848+1001 |
| Seata 控制台 | **7091** | `http://192.168.0.106:7091`（Seata 2.x） |
| Seata TC（事务协调） | **8091** | = 7091+1000，客户端连这个 |
| order/stock/account | **8081/8082/8083** | demo 微服务 |

### 数据库（复用 106 现有 MySQL 容器，新建 3 个库）

| 库 | 用途 | 初始化脚本 |
|---|---|---|
| `nacos_config` | Nacos 配置持久化（standalone + MySQL 模式） | Nacos 发行包的 `mysql-schema.sql` |
| `seata` | Seata Server 的事务日志（db 存储模式） | Seata 发行包的 `mysql.sql`（global_table/branch_table/lock_table/distributed_lock） |
| `seata_demo` | demo 业务库（order/stock/account 表 + **undo_log**） | 见第七节示例 |

> 103 的 MySQL 也可承担 `seata_demo`（业务库与业务服务同机，更贴近真实部署）。

---

## 五、安装方式：Docker Compose（推荐）而非 k8s

**为什么不用 k3s**（106 上已有）：
- 学习阶段要**看得见进程、改得动配置**；k8s 的 Service/ConfigMap 抽象会遮住关键细节（比如 Nacos 的 gRPC 端口、Seata 的注册 IP）
- Docker Compose 一个文件描述全部依赖，`docker compose logs -f` 直接看日志

**目录规范**（沿用你现有习惯，全部落 `/opt`）：

```text
/opt/nacos-seata/
├── docker-compose.yml
├── nacos/
│   ├── conf/application.properties     # 数据源指向 mysql
│   └── logs/
├── seata/
│   └── application.yml                 # 存储模式 db + 注册到 nacos
├── sql/
│   ├── nacos-mysql-schema.sql
│   ├── seata-mysql.sql
│   └── seata-demo.sql
└── demo/                               # demo 微服务（阶段 1/2）
```

**compose 骨架**（要点，完整版部署时补全）：

```yaml
services:
  nacos:
    image: nacos/nacos-server:v2.4.3
    environment:
      MODE: standalone
      SPRING_DATASOURCE_PLATFORM: mysql
      MYSQL_SERVICE_HOST: mysql          # 复用 106 现有 mysql 容器（需接入同一网络）
      MYSQL_SERVICE_DB_NAME: nacos_config
      MYSQL_SERVICE_USER: root
      MYSQL_SERVICE_PASSWORD: <106-mysql-密码>
    ports: ["8848:8848", "9848:9848", "9849:9849"]

  seata-server:
    image: seataio/seata-server:2.1.0
    environment:
      SEATA_IP: 192.168.0.106            # ★ 注册到 Nacos 的 IP（容器内网 IP 会导致调用失败）
      STORE_MODE: db
      SEATA_PORT: 8091
    volumes:
      - ./seata/application.yml:/seata-server/resources/application.yml
    ports: ["7091:7091", "8091:8091"]
```

**镜像拉取**：本机直连 Docker Hub 会被 reset，**必须走镜像源前缀**（实测可用）：

```bash
docker pull docker.m.daocloud.io/nacos/nacos-server:v2.4.3
docker tag  docker.m.daocloud.io/nacos/nacos-server:v2.4.3 nacos/nacos-server:v2.4.3
docker pull docker.m.daocloud.io/seataio/seata-server:2.1.0
```

> 或者直接 `docker save … | k3s ctr images import -`（若走 k3s）；纯 Docker 方式则用 tag 即可。

---

## 六、分阶段实施步骤

### 阶段 1：单机闭环（106）

- [ ] 建 3 个数据库 + 导入 schema（nacos_config / seata / seata_demo）
- [ ] 起 Nacos，浏览器登录（默认 nacos/nacos，**首次登录强制改密**）
- [ ] 起 Seata Server，确认 7091 控制台能看到它注册在 Nacos 的服务列表里
- [ ] 三个 demo 微服务注册到 Nacos（服务列表出现 3 个实例）
- [ ] 跑通"下单成功"链路（order → stock → account 全部提交）
- [ ] **故障注入**：让 account 扣款抛异常 → 观察全局回滚（stock/order 数据都回滚）
- [ ] 查看 `undo_log` 表和 Seata 控制台的全局事务记录

### 阶段 2：跨机分布式（103 加入）

- [ ] 103 上装 JDK 17（apt 或容器）
- [ ] 把 stock-service 部署到 103，注册到 106 的 Nacos
- [ ] 验证 Nacos 服务列表里出现**两个不同 IP** 的实例
- [ ] 再跑一次故障注入 → 观察**跨机回滚**
- [ ] 故意用错误 IP 注册（容器内网 IP）→ 体会"注册 IP 选错"的经典故障

### 阶段 3：进阶（可选）

- [ ] Seata 的 TCC / SAGA 模式（AT 之外）
- [ ] Nacos 配置中心动态刷新（`@RefreshScope`）+ 灰度发布
- [ ] Nacos 集群模式（3 节点，体会 Raft）
- [ ] Seata 高可用（多 TC 实例 + Nacos 注册）

---

## 七、学习要点（这些才是真正要掌握的）

### 7.1 Seata AT 模式的四张表与核心机制

```sql
-- 每个业务库都要有 undo_log（AT 模式的回滚依据）
CREATE TABLE undo_log (
  branch_id BIGINT NOT NULL, xid VARCHAR(100) NOT NULL,
  context VARCHAR(128) NOT NULL, rollback_info LONGBLOB NOT NULL,
  log_status INT NOT NULL, log_created DATETIME(6) NOT NULL,
  log_modified DATETIME(6) NOT NULL, UNIQUE KEY ux_undo_log (xid, branch_id)
) ENGINE=InnoDB;
```

| 机制 | 作用 |
|---|---|
| **两阶段提交** | 一阶段：业务 SQL + undo_log 一起提交（本地事务）；二阶段：全局提交删 undo_log / 全局回滚用 undo_log 反向补偿 |
| **全局锁** | TC 侧 lock_table 保证跨服务的写隔离 |
| **@GlobalTransactional** | 标注在入口方法上，一行注解开启全局事务 |
| **XID 传播** | 通过 RPC 上下文透传，跨服务/跨机器 |

### 7.2 Nacos 的两个角色

- **注册中心**：服务实例的 IP:PORT 列表（含健康检查、临时/持久实例）
- **配置中心**：`DataID / Group / Namespace` 三维定位配置，支持动态推送

### 7.3 必踩的经典坑（提前知道少走 3 天弯路）

| 坑 | 现象 | 原因/对策 |
|---|---|---|
| Nacos 2.x 只放行 8848 | 服务注册成功但调用失败 | **9848/9849 gRPC 端口没放**（防火墙/安全组） |
| 服务注册成容器内网 IP | Nacos 里看到 172.x，调用方连不上 | 显式指定注册 IP（`spring.cloud.nacos.discovery.ip`）或 `SEATA_IP` |
| Seata 报 `no available service 'default'` | 事务发起失败 | grouplist/registry 配置与 Nacos 注册名不一致；或 TC 没起来 |
| `undo_log` 表不存在 | AT 模式报错 | 每个业务库都要建 |
| 主键不是数字/无主键 | AT 模式不支持 | AT 依赖主键定位行 |
| JDK 版本过新 | 启动报模块/字节码错误 | 统一 JDK 17 |
| Nacos 首次登录 | 提示改密 | 改完记得更新配置文件里的密码 |

---

## 八、实施前清理项

| 机器 | 事项 | 原因 |
|---|---|---|
| **103** | **停掉/删除 clash 容器**（崩溃循环 3000+ 次） | 每 60 秒重启一次，白吃 CPU；它要解决的问题（代理）并未生效 |
| 106 | 确认 MySQL 有剩余连接数 | Nacos+Seata+业务库都连它，注意 `max_connections` |
| 两台 | 确认 ufw 放行所需端口 | 106 的 ufw 是 active（已加过 HDFS 规则），新端口要放行 8848/9848/9849/7091/8091 及 103→106 的访问 |
| 两台 | 103 → 106 的网络连通性验证 | `nc -z 192.168.0.106 8848` |

---

## 九、验收标准

- [ ] Nacos 控制台能登录，服务列表显示 3 个 demo 服务
- [ ] Seata 控制台能看到 TC 状态与全局事务记录
- [ ] 正常下单：order/stock/account 三表数据都正确落库
- [ ] 故障注入：account 异常后，三表数据**全部回滚**（这是 Seata 的核心价值）
- [ ] `undo_log` 在正常提交后被清理、回滚时被消费（可查表验证）
- [ ] 跨机场景：103 的服务与 106 的服务在同一全局事务里协同

---

## 十、我的最终建议

| 决策点 | 建议 |
|---|---|
| 放哪台 | **Nacos + Seata + MySQL 全放 106**；demo 服务阶段 1 放 106、阶段 2 迁一个到 103 |
| 安装方式 | **Docker Compose**（配置透明、日志直观），不用 k3s |
| 版本 | JDK 17 + Boot 3.2 + SCA 2023.0.x + Nacos 2.4 + Seata 2.1 |
| 顺序 | 先把 Nacos 单独跑通 → 再加 Seata → 再上 demo（**一次只加一个变量**） |
| 优先级 | 先做阶段 1（单机闭环），跨机留到阶段 2；**故障注入回滚是必须练的** |

需要的话我可以直接开始：建库导 schema → 写 compose → 拉镜像启动 → 验证 Nacos/Seata 控制台可访问。
