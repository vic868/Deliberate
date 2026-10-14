#!/usr/bin/env bash
# ============================================================
# 一键验证：业务是否真的跑起来了、能不能连上 Docker 中间件
# 用法：bash scripts/verify.sh
# ============================================================
set -uo pipefail
NS="demo"
PASS=0; FAIL=0
ok(){ echo "   ✅ $1"; PASS=$((PASS+1)); }
ng(){ echo "   ❌ $1"; FAIL=$((FAIL+1)); }
sec(){ echo; echo "── $1 ─────────────────────────────────"; }

sec "1. 集群与命名空间"
kubectl get ns "${NS}" >/dev/null 2>&1 && ok "namespace ${NS} 存在" || ng "namespace ${NS} 不存在"

sec "2. Deployment / Pod"
kubectl -n "${NS}" get deploy demo-api 2>/dev/null || ng "没有 demo-api Deployment"
READY=$(kubectl -n "${NS}" get deploy demo-api -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
DESIRED=$(kubectl -n "${NS}" get deploy demo-api -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)
[[ "${READY:-0}" == "${DESIRED:-0}" && "${READY:-0}" != "0" ]] \
  && ok "副本就绪 ${READY}/${DESIRED}" || ng "副本未就绪 ${READY:-0}/${DESIRED:-0}"
kubectl -n "${NS}" get pods -o wide 2>/dev/null

sec "3. Service 与 Endpoints"
kubectl -n "${NS}" get svc demo-api 2>/dev/null | tail -n +1
EP=$(kubectl -n "${NS}" get endpoints demo-api -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
[[ -n "${EP}" ]] && ok "Service 有后端: ${EP}" || ng "Service 没有后端（selector 不匹配？）"

sec "4. 外部中间件接线（Endpoints / 节点 IP）"
for s in mysql-ext redis-ext; do
  if kubectl -n "${NS}" get svc "${s}" >/dev/null 2>&1; then
    E=$(kubectl -n "${NS}" get endpoints "${s}" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null)
    [[ -n "${E}" ]] && ok "${s} → ${E}" || ng "${s} 没有地址"
  else
    echo "   ℹ️  ${s} 未创建（用的是直接写节点 IP 的方式，可忽略）"
  fi
done

sec "5. 从集群内部调用业务接口"
POD=$(kubectl -n "${NS}" get pod -l app=demo-api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [[ -n "${POD}" ]]; then
  echo "   使用 Pod: ${POD}"
  for path in /api/health /api/db /api/redis; do
    echo "   --- ${path} ---"
    if kubectl -n "${NS}" exec "${POD}" -- curl -fsS --max-time 8 "http://127.0.0.1:8080${path}" 2>/dev/null; then
      echo; ok "${path}"
    else
      echo; ng "${path} 调用失败"
    fi
  done
else
  ng "找不到业务 Pod"
fi

sec "6. 通过 Service（验证 kube-proxy / DNS）"
if [[ -n "${POD}" ]]; then
  kubectl -n "${NS}" exec "${POD}" -- curl -fsS --max-time 8 \
    "http://demo-api.demo.svc.cluster.local:8080/api/health" 2>/dev/null \
    && { echo; ok "Service DNS 可用"; } || ng "Service DNS 不可用"
fi

sec "7. 通过 Ingress（外部入口）"
if kubectl get ingressclass nginx >/dev/null 2>&1; then
  for u in "http://127.0.0.1/api/health" "http://192.168.0.106.nip.io/api/health"; do
    echo "   --- ${u} (Host 头 = 192.168.0.106.nip.io) ---"
    curl -fsS --max-time 8 -H "Host: 192.168.0.106.nip.io" "http://192.168.0.106${u#*106}" 2>/dev/null \
      && { echo; ok "Ingress 可达"; break; } || echo "   ⚠️ 不可达（可能还没装 Ingress 或规则未生效）"
  done
else
  echo "   ℹ️  未安装 Ingress Controller，跳过（用 NodePort 或 port-forward 也能测）"
  echo "      临时验证： kubectl -n demo port-forward svc/demo-api 8080:8080"
fi

sec "8. 事件与常见错误"
kubectl -n "${NS}" get events --sort-by=.lastTimestamp 2>/dev/null | tail -n 10

echo
echo "=============================================="
echo " 通过 ${PASS} 项，失败 ${FAIL} 项"
echo "=============================================="
[[ "${FAIL}" -eq 0 ]] && echo "🎉 全部通过" || echo "⚠️  有失败项，看上面的 ❌ 和事件输出"
