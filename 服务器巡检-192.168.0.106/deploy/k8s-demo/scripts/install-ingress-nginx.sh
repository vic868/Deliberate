#!/usr/bin/env bash
# ============================================================
# 在 106（裸机 k3s）上安装 ingress-nginx
#
# 解决两个裸机/国内特有的问题：
#   1. 裸机没有云 LoadBalancer → 用 hostNetwork 直接占宿主机 80/443
#   2. 国内拉不动 registry.k8s.io → 从镜像源拉、改回原名、导入 k3s
#
# 用法：
#   bash scripts/install-ingress-nginx.sh              # 全自动
#   bash scripts/install-ingress-nginx.sh --offline    # 只用已下载的 yaml
# ============================================================
set -euo pipefail

# ---------- 可调参数 ----------
NGINX_VER="${NGINX_VER:-v1.11.3}"          # ingress-nginx 版本
MANIFEST="${MANIFEST:-/tmp/ingress-nginx-${NGINX_VER}.yaml}"
K3S_BIN="${K3S_BIN:-/home/vic/.local/bin/k3s}"
NS="ingress-nginx"

# 国内镜像源（按顺序尝试）。daocloud 支持任意上游前缀，最通用。
MIRRORS=(
  "m.daocloud.io"
  "docker.m.daocloud.io"
  "registry.cn-hangzhou.aliyuncs.com/google_containers"
)

OFFLINE=0
[[ "${1:-}" == "--offline" ]] && OFFLINE=1

echo "=============================================="
echo " 在 ${HOSTNAME} 安装 ingress-nginx ${NGINX_VER}"
echo "=============================================="

# ---------- 0. 前置检查 ----------
command -v docker   >/dev/null || { echo "!! 缺 docker"; exit 1; }
command -v kubectl  >/dev/null || { echo "!! 缺 kubectl（k3s 自带：${K3S_BIN} kubectl）"; exit 1; }
[[ -x "${K3S_BIN}" ]] || { echo "!! 找不到 k3s：${K3S_BIN}"; exit 1; }

echo "==> 检查 80/443 是否空闲（hostNetwork 会直接占用）"
if ss -lntp 2>/dev/null | grep -qE ':(80|443)\s'; then
  echo "!! 80 或 443 已被占用，请先停掉占用者（你 106 上应该是空闲的）："
  ss -lntp | grep -E ':(80|443)\s' || true
  echo "   注意：宝塔的 Nginx 只听 10591，不冲突；Hue 在 8888，也不冲突。"
  read -r -p "   仍要继续？(y/N) " ans
  [[ "${ans}" == "y" ]] || exit 1
else
  echo "   ✅ 80/443 空闲"
fi

# ---------- 1. 下载官方 bare-metal 清单 ----------
if [[ "${OFFLINE}" -eq 0 ]]; then
  echo "==> [1/5] 下载清单"
  URL="https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-${NGINX_VER}/deploy/static/provider/baremetal/deploy.yaml"
  if curl -fsSL --max-time 30 -o "${MANIFEST}" "${URL}"; then
    echo "   ✅ ${MANIFEST}"
  else
    echo "   ⚠️ 直连 GitHub 失败（国内常见）。请任选一种方式拿到清单后重跑 --offline："
    echo "      a) 代理下载： curl -x http://127.0.0.1:7899 -fsSL -o ${MANIFEST} '${URL}'"
    echo "      b) 浏览器打开后另存为 ${MANIFEST}"
    echo "      c) 用 gitee 镜像 / 其他可达源"
    exit 1
  fi
else
  [[ -f "${MANIFEST}" ]] || { echo "!! --offline 但找不到 ${MANIFEST}"; exit 1; }
  echo "==> [1/5] 使用本地清单 ${MANIFEST}"
fi

# ---------- 2. 从清单里提取需要的镜像 ----------
echo "==> [2/5] 解析所需镜像"
IMAGES=$(grep -oE 'image: +[^ ]+' "${MANIFEST}" | awk '{print $2}' | sort -u)
echo "${IMAGES}" | sed 's/^/   /'
[[ -n "${IMAGES}" ]] || { echo "!! 没从清单里解析出镜像"; exit 1; }

# ---------- 3. 逐个镜像：镜像源拉取 → 改回原名 → 导入 k3s ----------
echo "==> [3/5] 拉取并导入 k3s"
while read -r IMG; do
  [[ -z "${IMG}" ]] && continue
  # 已经导入过就跳过
  if sudo "${K3S_BIN}" ctr images ls -q 2>/dev/null | grep -qx "${IMG}"; then
    echo "   ⏭  k3s 已有: ${IMG}"
    continue
  fi
  # registry.k8s.io/xxx/yyy:v1 → <mirror>/xxx/yyy:v1
  PULLED=0
  for M in "${MIRRORS[@]}"; do
    SRC="${IMG/registry.k8s.io/${M}}"
    # 阿里云 google_containers 只镜像一部分，路径规则不同，失败就自动换下一个
    echo "   → 尝试 ${SRC}"
    if docker pull "${SRC}" >/dev/null 2>&1; then
      docker tag "${SRC}" "${IMG}"
      docker save "${IMG}" | sudo "${K3S_BIN}" ctr images import -
      echo "   ✅ ${IMG}"
      PULLED=1
      break
    fi
  done
  if [[ "${PULLED}" -eq 0 ]]; then
    echo "   ❌ 所有镜像源都拉不到 ${IMG}"
    echo "      请手动处理，例如："
    echo "        docker pull <某个可达源>/${IMG#registry.k8s.io/}"
    echo "        docker tag <那个> ${IMG}"
    echo "        docker save ${IMG} | sudo ${K3S_BIN} ctr images import -"
    exit 1
  fi
done <<< "${IMAGES}"

# ---------- 4. 应用清单 ----------
echo "==> [4/5] kubectl apply"
kubectl apply -f "${MANIFEST}"

# ---------- 5. 改成 hostNetwork（裸机关键一步）----------
echo "==> [5/5] 打补丁：hostNetwork 直占宿主机 80/443"
kubectl -n "${NS}" patch deploy ingress-nginx-controller --type=strategic -p '{
  "spec": {
    "template": {
      "spec": {
        "hostNetwork": true,
        "dnsPolicy": "ClusterFirstWithHostNet"
      }
    }
  }
}'

echo "==> 等待就绪..."
kubectl -n "${NS}" rollout status deploy/ingress-nginx-controller --timeout=180s

echo
echo "=============================================="
echo "✅ 安装完成"
echo "=============================================="
kubectl -n "${NS}" get pods -o wide
echo
echo "宿主机 80/443 应已被占用："
ss -lntp 2>/dev/null | grep -E ':(80|443)\s' || echo "   （没看到？检查 pod 是否 Running）"
echo
echo "下一步："
echo "  kubectl apply -f k8s/40-ingress.yaml"
echo "  浏览器访问 http://192.168.0.106.nip.io/api/health"
echo
echo "排错常用："
echo "  kubectl -n ${NS} logs -l app.kubernetes.io/component=controller --tail=100"
echo "  kubectl -n ${NS} describe pod -l app.kubernetes.io/component=controller"
echo "  kubectl get ingressclass"
