# deploy/nginx —— 106 服务统一入口的配置源文件

> 完整手册：[[12-nginx/0-106服务统一入口配置手册|106 服务统一入口配置手册]]

## 这是什么

192.168.0.106 上 **nginx 1.30.5**（源码编译，prefix `/opt/nginx`）的**配置源头**。
本目录是"版本管理副本"，服务器上的实际路径是 `/opt/nginx/conf/`。

改配置的正确姿势：**改这里 → 传到服务器 → `nginx -t` → `systemctl reload nginx`**。

## 文件对应关系

| 本目录 | 服务器路径 | 说明 |
|---|---|---|
| `conf/nginx.conf` | `/opt/nginx/conf/nginx.conf` | 主配置（worker、gzip、日志、WebSocket map） |
| `conf/conf.d/00-default.conf` | 同左 | 导航首页 + `/healthz` + `/nginx_status` + `/hue/` + `/es/` |
| `conf/conf.d/10-k8s.conf` | 同左 | Flink `:30081`、Dinky `:30888` |
| `conf/conf.d/20-hadoop.conf` | 同左 | HDFS `:9870`、YARN `:8088`、JobHistory `:19888`、Hive `:10002`、Hue `:8888` |
| `conf/conf.d/30-data.conf` | 同左 | Doris `:18030`、HBase `:16010`、Kibana `:5601`、Kafka UI `:28080` |
| `conf/conf.d/40-monitoring.conf` | 同左 | Grafana `:3100`、Prometheus `:9093` |
| `conf/conf.d/50-tools.conf` | 同左 | Portainer `:9000`、Neo4j `:7474`、MinIO `:9001`、Attu `:8000`、RedisInsight `:5540` |
| `conf/snippets/ssl-common.conf` | `/opt/nginx/conf/snippets/ssl-common.conf` | SSL 参数片段（各 HTTPS 站点 include 它） |
| `conf/https-staged/99-https.conf` | `/opt/nginx/conf/https-staged/99-https.conf` | **443 配置（暂存未启用）**，含 `map` 分发 |
| `html/index.html` | `/opt/nginx/html/index.html` | 服务导航首页 |
| `nginx.service` | `/etc/systemd/system/nginx.service` | systemd 单元 |

> 证书文件（`ca.crt`/`ca.key`/`106.crt`/`106.key`）**不入库**——私钥不应进 Git。
> 生成命令见 [[12-nginx/1-Nginx配置详解与HTTPS证书实践]] §5。

## HTTPS 启用 / 停用

```bash
# 启用 443
sudo cp /opt/nginx/conf/https-staged/99-https.conf /opt/nginx/conf/conf.d/ \
  && sudo /opt/nginx/sbin/nginx -t && sudo systemctl reload nginx

# 停用（回到只有 80）
sudo rm /opt/nginx/conf/conf.d/99-https.conf && sudo systemctl reload nginx
```

启用前**先在客户端导入 CA**（`/opt/nginx/conf/ssl/ca.crt`），否则浏览器会报证书错误。
⚠️ 自签证书**不要开 HSTS**，详见手册 §9.3。

## 部署命令

```bash
# 从 Mac 传（注意 COPYFILE_DISABLE，否则会带上 macOS 的 ._* 垃圾文件）
cd 服务器巡检-192.168.0.106/deploy/nginx
COPYFILE_DISABLE=1 tar czf /tmp/nginx-cfg.tgz .
scp /tmp/nginx-cfg.tgz vic@192.168.0.106:/tmp/

# 在 106 上
cd /tmp && rm -rf stage && mkdir stage && tar xzf nginx-cfg.tgz -C stage
sudo cp stage/conf/nginx.conf /opt/nginx/conf/nginx.conf
sudo cp stage/conf/conf.d/*.conf /opt/nginx/conf/conf.d/
sudo cp stage/html/index.html /opt/nginx/html/index.html
sudo cp stage/nginx.service /etc/systemd/system/nginx.service

# ★ 关键：修权限（不修会 403）
sudo chmod 644 /opt/nginx/conf/nginx.conf /opt/nginx/conf/conf.d/*.conf /opt/nginx/html/index.html
sudo rm -f /opt/nginx/conf/conf.d/._*

# 校验 + 重载
sudo /opt/nginx/sbin/nginx -t && sudo systemctl reload nginx
sudo systemctl daemon-reload   # 只有改了 nginx.service 才需要

# 验证
curl -s http://192.168.0.106/healthz
```

## ⚠️ 三个已踩过的坑

1. **权限**：`scp`/`tar` 过来的文件默认 `600`，worker（`www-data`）读不了 → **403**。必须 `chmod 644`。
2. **`._*` 垃圾文件**：macOS 打包会带上，用 `COPYFILE_DISABLE=1` 避免，或传完 `rm -f`。
3. **YARN 的 proxy_pass 必须写 LAN IP**（`192.168.0.106:8088`），因为它只绑 LAN IP、不绑 `127.0.0.1`。写错就是 502。

## 当前状态

- 2026-10-14 已上线：`systemctl is-enabled nginx` → `enabled`，`is-active` → `active`
- 实测 **18/18** 个服务域名入口正常，且所有跳转都指向公网域名，**未改动任何现有服务配置**
