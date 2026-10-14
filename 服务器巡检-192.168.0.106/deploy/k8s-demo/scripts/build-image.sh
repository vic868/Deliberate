#!/usr/bin/env bash
# ============================================================
# 构建镜像并导入 k3s（106 上执行）
#
# 用法：
#   bash scripts/build-image.sh              # 构建 + 导入
#   bash scripts/build-image.sh --skip-build # 只导入已有镜像
# 版本号改这里（同时要改 k8s/30-app.yaml 里的 image:）
# ============================================================
set -euo pipefail

IMAGE="demo-api"
TAG="1.0.0"
FULL="${IMAGE}:${TAG}"

# k3s 二进制位置：你机器上装在 vic 用户目录，root 下要用全路径
K3S_BIN="/home/vic/.local/bin/k3s"
SKIP_BUILD=0
[[ "${1:-}" == "--skip-build" ]] && SKIP_BUILD=1

cd "$(dirname "$0")/.."
echo "==> 工作目录: $(pwd)"

# ---------- 1. 构建镜像 ----------
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo "==> [1/4] docker build -t ${FULL} ."
  docker build -t "${FULL}" .
else
  echo "==> [1/4] 跳过构建"
fi

echo "==> [2/4] 镜像信息"
docker images "${IMAGE}" --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'

# ---------- 2. 导出 ----------
TAR="/tmp/${IMAGE}-${TAG}.tar"
echo "==> [3/4] 导出到 ${TAR}"
docker save -o "${TAR}" "${FULL}"
ls -lh "${TAR}"

# ---------- 3. 导入 k3s containerd ----------
echo "==> [4/4] 导入 k3s"
if ! command -v "${K3S_BIN}" >/dev/null 2>&1 && [[ ! -x "${K3S_BIN}" ]]; then
  echo "!! 找不到 k3s: ${K3S_BIN}，请修改脚本里的 K3S_BIN"
  exit 1
fi

# k3s ctr 需要 root
sudo "${K3S_BIN}" ctr images import "${TAR}"

# ---------- 4. 校验 ----------
echo "==> 校验 k3s 里是否已有该镜像"
sudo "${K3S_BIN}" ctr images ls | grep -i "${IMAGE}" || {
  echo "!! 导入后没找到镜像，请检查上面的输出"
  exit 1
}

rm -f "${TAR}"
echo
echo "✅ 完成：${FULL} 已进入 k3s"
echo "   下一步："
echo "     kubectl apply -f k8s/00-namespace.yaml"
echo "     kubectl apply -f k8s/10-config.yaml"
echo "     kubectl apply -f k8s/30-app.yaml"
echo "     kubectl -n demo rollout status deploy/demo-api"
