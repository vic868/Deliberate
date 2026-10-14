# k8s-demo —— 第一个业务服务上 k3s（含对接宿主机 Docker 中间件）

> 这是 **192.168.0.106 迁移路线「阶段 1 + 阶段 2」的可执行材料**。
> 配套讲解文档：[[9-k8s/6-实战-业务上k3s与对接Docker中间件|6-实战-业务上k3s与对接Docker中间件]]
> 规划背景：[[9-k8s/5-106服务梳理与K8s迁移规划|5-106服务梳理与K8s迁移规划]]

## 这套东西解决什么问题

106 上 k3s 已经在跑 Flink/Dinky，但**还没有自己的业务服务**；而所有中间件（MySQL/Redis/Kafka…）都在宿主机 Docker 里。
本目录提供一个**最小但完整**的 Spring Boot 服务，用来验证两件事：

1. **无状态业务能不能跑在 k3s 里**（Deployment + 探针 + 优雅停机 + HPA）
2. **k3s 里的业务 Pod 能不能连上宿主机 Docker 的中间件**（Endpoints / 节点 IP 两种接线方式）

## 目录结构

```
k8s-demo/
├── pom.xml                       Spring Boot 3.2.5 / Java 17
├── Dockerfile                    多阶段构建，最终只含 JRE + jar
├── src/main/java/com/demo/
│   ├── DemoApplication.java      启动类
│   └── DemoController.java       4 个验证接口：health / db / redis / echo
├── src/main/resources/
│   └── application.yml           地址全部走环境变量，默认指向 106
├── k8s/
│   ├── 00-namespace.yaml         命名空间 + 资源配额
│   ├── 10-config.yaml            ConfigMap + Secret（★ 改这里填密码）
│   ├── 20-middleware-endpoints.yaml  【可选】把外部中间件包装成集群 DNS 名
│   ├── 30-app.yaml               ★ Deployment + Service（核心）
│   ├── 40-ingress.yaml           Ingress（域名入口）
│   └── 50-hpa.yaml               HPA（按 CPU 2~6 副本）
└── scripts/
    ├── install-ingress-nginx.sh  裸机安装 ingress-nginx（含国内镜像处理）
    ├── build-image.sh            构建镜像并导入 k3s
    └── verify.sh                 一键验证
```

## 快速开始（在 106 上执行）

```bash
# 0. 把本目录拷到 106，例如 /opt/k8s-demo
cd /opt/k8s-demo

# 1. 【先改】k8s/10-config.yaml 里的 MySQL 密码
vi k8s/10-config.yaml

# 2. 构建镜像 + 导入 k3s
bash scripts/build-image.sh

# 3. 部署
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/10-config.yaml
kubectl apply -f k8s/30-app.yaml
kubectl -n demo rollout status deploy/demo-api

# 4. 验证（端口转发，不依赖 Ingress）
kubectl -n demo port-forward svc/demo-api 8080:8080
# 另开一个终端：
curl localhost:8080/api/health
curl localhost:8080/api/db       # 探测宿主机 MySQL
curl localhost:8080/api/redis    # 探测宿主机 Redis
curl localhost:8080/api/echo/hi  # 看 pod 字段，验证负载均衡

# 5. 一键体检
bash scripts/verify.sh
```

## 再往上走：加 Ingress 入口

```bash
# 装 ingress-nginx（裸机 + 国内镜像处理，脚本会自动打 hostNetwork 补丁）
bash scripts/install-ingress-nginx.sh

# 应用 Ingress 规则
kubectl apply -f k8s/40-ingress.yaml

# 浏览器访问（nip.io 免改 hosts）
open http://192.168.0.106.nip.io/api/health
```

## 最后：加自动扩缩容

```bash
kubectl apply -f k8s/50-hpa.yaml
kubectl -n demo get hpa -w
```

## 关键设计说明

| 设计点 | 为什么这么做 |
|---|---|
| `imagePullPolicy: IfNotPresent` | 镜像是从本地导入 k3s 的，没有 registry |
| 探针用 `/actuator/health/liveness`、`/readiness` | **不要**用 `/actuator/health`——它含 db/redis 检查，中间件一抖会把 Pod 判死 |
| `initialization-fail-timeout: -1` | MySQL 连不上时应用也能启动，避免 CrashLoopBackOff 难排障 |
| `preStop: sleep 8` + `terminationGracePeriodSeconds: 45` | 先让 Endpoints 摘掉本 Pod，再走优雅停机，避免 502 |
| `JAVA_OPTS: -XX:MaxRAMPercentage=70` | 让 JVM 按容器 limit 算堆，而不是按宿主机 48G |
| 中间件地址写**节点 IP** 而不是 `127.0.0.1` | Pod 里的 127.0.0.1 是 Pod 自己的回环，连不到宿主机 Docker |
| `20-middleware-endpoints.yaml` 用**无 selector 的 Service + Endpoints** | 让应用写 DNS 名，将来中间件搬进集群只改一处 |

## ⚠️ 注意事项

1. **`10-config.yaml` 里的密码是占位符**（`CHANGE_ME_mysql_password`），必须改成 106 上的真实密码。
2. `Endpoints` API 在较新 K8s 中已 deprecated，若被移除请改用 `EndpointSlice`（文件末尾有模板）。
3. 脚本未经在 106 上的实跑验证（本机无法 SSH），**首次执行请逐步确认输出**，尤其是 `install-ingress-nginx.sh` 的镜像拉取部分。
4. 学习环境把密码写进 YAML 可接受；**生产必须用 SealedSecrets / ExternalSecrets / Vault**。
