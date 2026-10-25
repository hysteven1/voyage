#!/usr/bin/env bash
# Creates a dedicated disposable cluster, but leaves it for local inspection.
set -euo pipefail
export KUBECONFIG=${KUBECONFIG:-/tmp/voyage-infra.kubeconfig}
if kind get clusters | grep -qx voyage-infra; then
  echo 'Refusing to overwrite an existing voyage-infra cluster. Follow docs/kubernetes.md to inspect or reuse it.' >&2
  exit 1
fi
# No credentials enter these build contexts; the runtime Secret contains only a local DB URL.
docker build -t voyage-api:local services/trip-service
docker build -t voyage-worker:local services/planning-worker
docker build -t voyage-web:local apps/web
kind create cluster --name voyage-infra \
  --image kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a \
  --config infrastructure/local/kind.yaml --kubeconfig "$KUBECONFIG" --wait 120s
kubectl --context kind-voyage-infra create namespace voyage-dev
python3 scripts/local-secrets.py
kubectl --context kind-voyage-infra -n voyage-dev apply -f infrastructure/local/dependencies.yaml
kubectl --context kind-voyage-infra -n voyage-dev rollout status statefulset/postgres --timeout=180s
kubectl --context kind-voyage-infra -n voyage-dev rollout status statefulset/temporal --timeout=180s
kind load docker-image --name voyage-infra voyage-api:local voyage-worker:local voyage-web:local
helm upgrade --install voyage infrastructure/helm/voyage \
  --kube-context kind-voyage-infra -n voyage-dev \
  -f infrastructure/helm/voyage/values-development.yaml --wait --timeout 5m
kubectl --context kind-voyage-infra -n voyage-dev port-forward svc/voyage-voyage-web 18081:3000 > /tmp/voyage-port-forward.log 2>&1 &
forward_pid=$!
trap 'kill "$forward_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18081/api/health > /dev/null 2>&1; then break; fi
  sleep 1
done
python3 scripts/smoke-trip.py --base-url http://127.0.0.1:18081
kubectl --context kind-voyage-infra -n voyage-dev get pods,pvc
