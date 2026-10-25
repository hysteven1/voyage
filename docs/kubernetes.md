# Kubernetes and Helm

## Prerequisites

Use Linux/WSL2 with Docker Desktop Linux containers, kubectl compatible with
Kubernetes 1.34, Python 3, and enough Docker resources (about 4 CPUs / 6 GiB).
Install the pinned Linux amd64 tools:

```bash
scripts/install-infra-tools.sh /tmp/voyage-tools
export PATH=/tmp/voyage-tools:$PATH
scripts/validate-infrastructure.sh
```

The installer verifies executable checksums. Other platforms can install Helm 3,
kind 0.30.0, actionlint 1.7.7 and kubeconform 0.7.0 using their official releases.

`scripts/kind-smoke.sh` automates the fresh-cluster path below, refuses to overwrite
an existing cluster, and leaves the cluster/data for inspection. The manual
`Integration smoke` GitHub workflow runs the same script on an ephemeral runner.

## Dedicated local environment

These commands never attach to Compose volumes. The kubeconfig stays in `/tmp`;
all mutations explicitly target `kind-voyage-infra`.

```bash
export KUBECONFIG=/tmp/voyage-infra.kubeconfig
kind create cluster --name voyage-infra --image kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a \
  --config infrastructure/local/kind.yaml --kubeconfig "$KUBECONFIG" --wait 120s
kubectl --context kind-voyage-infra create namespace voyage-dev
python3 scripts/local-secrets.py
kubectl --context kind-voyage-infra -n voyage-dev apply -f infrastructure/local/dependencies.yaml
kubectl --context kind-voyage-infra -n voyage-dev rollout status statefulset/postgres --timeout=180s
kubectl --context kind-voyage-infra -n voyage-dev rollout status statefulset/temporal --timeout=180s

docker build -t voyage-api:local services/trip-service
docker build -t voyage-worker:local services/planning-worker
docker build -t voyage-web:local apps/web
kind load docker-image --name voyage-infra voyage-api:local voyage-worker:local voyage-web:local
helm upgrade --install voyage infrastructure/helm/voyage \
  --kube-context kind-voyage-infra -n voyage-dev \
  -f infrastructure/helm/voyage/values-development.yaml --wait --timeout 5m
kubectl --context kind-voyage-infra -n voyage-dev get pods,svc,pvc,jobs
kubectl --context kind-voyage-infra -n voyage-dev port-forward svc/voyage-voyage-web 3000:3000
```

Open http://localhost:3000. In another terminal:

```bash
python3 scripts/smoke-trip.py --base-url http://127.0.0.1:3000
```

This creates a real persisted trip through real Temporal activities using the
explicit legacy synthetic-provider path. It incurs no provider costs if provider
keys are absent. It leaves its trip for inspection and tests repeated planning
requests against the completed result. It does not verify expanded AI planning.

For the actual web form, add `OPENAI_API_KEY` to the existing `voyage-runtime`
Secret using a secret manager or `kubectl edit secret` locally; keys are base64
encoded, not encrypted by base64. Avoid shell history and screenshots of values.
Optional `SERPAPI_API_KEY` enables live travel searches. Restart the API and worker
after changing the Secret, then plan a short future trip through the UI. This
consumes paid provider quota and is a manual opt-in test, never a CI requirement.
Do not regenerate the local DB password after the PVC has initialized.

For repeated local builds, prefer unique tags and update values; reusing `local`
requires loading the new image and restarting Pods explicitly. GitOps examples
instead use a committed full source-SHA tag.

## Configuration

The chart has no external chart dependencies. `values.yaml` documents every setting.
`values-development.yaml` uses loaded local images. `values-production.yaml`
intentionally requires real endpoints and image revisions before it can render.
No application database or Temporal server is bundled in the application chart.

| Value | Purpose |
| --- | --- |
| `images.{api,worker,web}.repository/tag/digest` | All three source-aligned images; digest takes precedence |
| `imagePullPolicy`, `imagePullSecrets` | Local Never vs registry pulls; Secret names only |
| `existingSecret` | Precreated Secret with DATABASE_URL and optional provider/Temporal keys |
| `config.temporalAddress/temporalNamespace/temporalTls` | External Temporal endpoint, namespace and TLS |
| `config.openai*Model` | Model selection; no credentials |
| `resources`, `replicas` | Requests, limits, fixed small deployment size |
| `worker.maxConcurrentActivities` | Bound simultaneous activities per worker |
| `migrations` | Enabled by default; serialized upgrade Job before app rollout |
| `ingress` | Optional TLS web ingress; disabled by default |
| `networkPolicy` | Optional coarse allowlist; requires enforcing CNI |

Application Pods run as UID/GID 10001 with no API token, no added capabilities,
RuntimeDefault seccomp, and read-only roots. Only temporary/cache emptyDirs are
writable. Worker uses Recreate to avoid overlapping incompatible worker versions;
this alone does not make existing workflow histories replay-compatible.

Migration hooks use the same API image and an externally created Secret. Their
advisory lock serializes migrations; retries only upgrade to head. The pre-install
Job deliberately does not depend on chart-created ConfigMaps or ServiceAccounts.
Failed Jobs remain for inspection. No automatic downgrade, PVC deletion, or database
reset is performed. Migration credentials need DDL privileges; application runtime
credentials currently use the same URL. A separate migration role is future work.

## Production-oriented installation

Provision application PostgreSQL with backups, restore testing, encryption/TLS,
and a production Temporal Service with its own persistence and namespace first.
The API and worker support Temporal TLS and API-key authentication; custom mTLS
certificate mounts are not implemented. Use a TLS/API-key endpoint or adapt the
client explicitly for mTLS before choosing that authentication mode.

Create the target namespace and Secret securely before installing. Commit a
nonsecret values file containing actual image digests, Temporal settings and TLS
web ingress configuration. If enabled, NetworkPolicy permits TLS egress broadly
because provider IPs vary; it is not an FQDN firewall. Configure DB/Temporal ports
for your endpoints. Do not enable policy on kind expecting enforcement.

```bash
helm upgrade --install voyage infrastructure/helm/voyage \
  --kube-context YOUR_APPROVED_CONTEXT -n voyage-prod \
  -f infrastructure/helm/voyage/values-production.yaml \
  -f /path/to/reviewed-production-values.yaml --wait --timeout 10m
```

No command here provisions cloud resources. Configure private access and TLS before
exposing the app; application authentication and ownership checks are still absent.

## Troubleshooting and recovery

```bash
kubectl --context kind-voyage-infra -n voyage-dev get events --sort-by=.lastTimestamp
kubectl --context kind-voyage-infra -n voyage-dev logs job/voyage-voyage-migrate
kubectl --context kind-voyage-infra -n voyage-dev logs deployment/voyage-voyage-api --tail=100
kubectl --context kind-voyage-infra -n voyage-dev logs deployment/voyage-voyage-worker --tail=100
kubectl --context kind-voyage-infra -n voyage-dev describe pod POD_NAME
kubectl --context kind-voyage-infra -n voyage-dev port-forward svc/temporal 8233:8233
helm history voyage --kube-context kind-voyage-infra -n voyage-dev
```

Inspect `plan-trip-<trip_id>` in the local Temporal UI at http://localhost:8233.
ImagePullBackOff: check tag, access Secret, node architecture, and local image load.
Migration failure: inspect the retained Job and DB connectivity before retrying.
Worker unready: check its Temporal endpoint/namespace, TLS, and logs. API readiness
checks application PostgreSQL; worker readiness checks Temporal. They are separate.

For a Helm-managed release, use `helm rollback voyage REVISION --kube-context
kind-voyage-infra -n voyage-dev --wait` only if the old app supports the current
schema and workflow histories. Helm rollback does not reverse migrations. For an
Argo-managed release, revert the values/image commit and sync; do not use Helm to
fight Argo's desired state. Restore data only through a deliberate recovery plan.

## Safe cleanup

`helm uninstall voyage --kube-context kind-voyage-infra -n voyage-dev` removes the
application only. The separately managed database/Temporal StatefulSets and PVCs
remain. Stop port-forwards with Ctrl-C. Do not use `docker compose down -v`.

Only when you intentionally want to destroy **all data in this disposable kind
cluster**, run `kind delete cluster --name voyage-infra`. This cannot recover its
PVCs; back up anything valuable first. It does not delete Compose volumes. Cleanup
is documented, not automatically performed by the setup commands.
