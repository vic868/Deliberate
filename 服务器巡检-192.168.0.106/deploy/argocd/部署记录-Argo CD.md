# 部署记录：Argo CD（k3s @ 192.168.0.106）

> 部署日期：2026-10-27　|　版本：Argo CD **v3.5.6**（最新 stable）　|　命名空间：`argocd`
> 目标机：192.168.0.106（k3s v1.36.2 单节点，vic 用户，6C/45G）

---

## 一、访问信息

| 项目 | 值 |
|---|---|
| Web UI | **https://192.168.0.106:30443** |
| 备用入口 | http://192.168.0.106:30080（307 自动跳 https） |
| 用户名 | `admin` |
| 初始密码 | 见 `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' \| base64 -d` |
| 暴露方式 | Service `argocd-server` 类型 NodePort（未占用现有 80/443） |

> 首次登录后建议 `argocd account update-password` 改密，并删除 `argocd-initial-admin-secret`。
> UI 走自签证书，浏览器会告警；要正式证书需配 ingress + 域名（本机当前无 ingress class，k3s 装时 `--disable=traefik`）。

## 二、组件拓扑

| 工作负载 | 作用 | 副本 |
|---|---|---|
| `argocd-server` | API + Web UI | 1 |
| `argocd-repo-server` | 拉 Git 仓库、渲染 Helm/Kustomize | 1 |
| `argocd-application-controller` | 比对期望/实际状态并 sync（StatefulSet） | 1 |
| `argocd-applicationset-controller` | ApplicationSet（批量生成 Application） | 1 |
| `argocd-dex-server` | SSO（OIDC/LDAP 对接） | 1 |
| `argocd-notifications-controller` | 事件通知 | 1 |
| `argocd-redis` | controller/repo-server 缓存 | 1 |

实测内存占用约 500MB～700MB，对这台机器无压力。

## 三、安装过程（可复用）

```bash
# 1. 命名空间 + 官方清单（server-side apply，CRD 较大）
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.6/manifests/install.yaml

# 2. 暴露 NodePort
kubectl -n argocd patch svc argocd-server --type=merge -p '{"spec":{"type":"NodePort","ports":[
  {"name":"http","port":80,"targetPort":8080,"nodePort":30080},
  {"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}'

# 3. 取初始密码
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

## 四、踩到的大坑：containerd 拉镜像静默挂死

这是本次部署最耗时的部分，记录下来避免下次重踩。

**现象**：Pod 一直 `ContainerCreating`，事件只有 `Pulling image ...`，**不报错、不超时**，磁盘每分钟只涨 2MB。

**已排除**：

| 怀疑点 | 实测结果 |
|---|---|
| 网络不通 | curl 到同一镜像站 blob 有 **5MB/s**，正常 |
| 镜像站限速 | 换 3 个 IP、HTTP/1.1 与 HTTP/2 都正常 |
| DNS / IPv6 | 解析正常，三个 A 记录均可访问 |
| conntrack 打满 | 335 / 196608，远未满 |
| kubelet 串行拉取（`pull QPS exceeded`） | 用 `ctr` 直接拉同样卡住，排除 |
| 磁盘空间 | 100G 可用 |

**定位**：`ss -tnp` 显示 containerd 到镜像站是 **ESTAB 连接但收发均为 0 字节**——TCP 通了、TLS 也过了，但 HTTP 请求体不流动。

**关键对照**：**同一台机器上的 Docker（29.1.3）从同一个镜像站拉同一个 1.5G 镜像，跑 12MB/s**，两分钟拉完。所以不是网络，是 containerd 的 HTTP 拉取路径。

**绕过方案（已落地）**：

```bash
# Docker 拉（走 daocloud 镜像站）→ 导出 → 导入 containerd 的 k8s.io 命名空间
docker pull quay.m.daocloud.io/argoproj/argocd:v3.5.6
docker save quay.m.daocloud.io/argoproj/argocd:v3.5.6 -o /tmp/img.tar
k3s ctr -a /run/k3s/containerd/containerd.sock -n k8s.io images import /tmp/img.tar

# 再 tag 回官方名，清单保持原样不用改
k3s ctr -n k8s.io images tag quay.m.daocloud.io/argoproj/argocd:v3.5.6 quay.io/argoproj/argocd:v3.5.6
```

三个镜像都已按此处理并打回官方名：`quay.io/argoproj/argocd`、`public.ecr.aws/docker/library/redis`、`ghcr.io/dexidp/dex`。

**各源实测速度**（这台机器）：

| 源 | 速度 | 结论 |
|---|---|---|
| `docker.m/quay.m/ghcr.m.daocloud.io` | 5～12 MB/s | 可用 |
| `quay.io` 直连 | **64 KB/s** | 1.5G 要 7 小时 |
| `public.ecr.aws` | **86 B/s** | 不可用 |
| `registry-1.docker.io` | 超时 | 不可达 |
| `registry.k8s.io` | 跳到 Google，超时 | 不可达 |

## 五、遗留风险与建议

> [!warning] 后续 Pod 拉新镜像仍可能卡住
> containerd 的拉取问题没有根治，只是这次用「预导入」绕过了。以后部署新应用（尤其 Docker Hub 上的镜像）大概率复现。

建议的长期动作（按性价比排序）：

1. **给 k3s 配镜像源**：`/etc/rancher/k3s/registries.yaml` 里给 `docker.io` / `quay.io` / `ghcr.io` 都配 daocloud 镜像端点。注意现有文件只配了 `docker.io → docker.1panel.live / docker.1ms.run`（2026-07 留的），quay/ghcr 没有镜像源。
2. **查 containerd 的 HTTP 卡死**：在 k3s 服务里加 `GODEBUG=http2client=0` 试一次（要重启 k3s），或升级/降级 containerd 版本对比。这类「ESTAB 但零字节」多半是 Go HTTP/2 与链路上某个中间设备不兼容。
3. **建私有 registry**：这台机器原本有 `registry:2`（已停），可以拉起来做本地缓存，配合 `docker pull` + push 使用。
4. 关键镜像建议提前 `docker pull` + `ctr import`，写进部署脚本。

## 六、验证结果

- `kubectl get pods -n argocd`：**7/7 Running**
- `curl -sk https://192.168.0.106:30443/` → `<title>Argo CD</title>`
- `GET /api/v1/session` → 405（正常，该接口只接受 POST 登录）
