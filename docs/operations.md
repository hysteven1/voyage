# Operations, security and observability

## Signals that exist

API/worker logs use JSON with timestamp, level, service and message. API request
middleware creates an X-Request-ID, status and duration. The planning-start log
joins request_id, trip_id and workflow_id; worker activity logs include trip_id and
Temporal workflow_id. Search `plan-trip-<trip_id>` in Temporal. This is correlation,
not a complete OpenTelemetry distributed trace. Provider URLs containing keys are
not logged by the travel-search wrapper. Do not enable verbose HTTP wire logging
or export Temporal payloads/traveler notes publicly.

| Probe | Meaning |
| --- | --- |
| Web `/api/health` | Production Next server is answering; does not prove API availability |
| API `/api/v1/health/live` | API process is alive |
| API `/api/v1/health/ready` | Application PostgreSQL answers SELECT 1 |
| Worker `:8081/health/live` | Worker event loop/probe server is alive |
| Worker `:8081/health/ready` | Worker is running and Temporal health check succeeds |

Worker health has no public Kubernetes Service. Startup probes allow warm-up;
liveness does not restart API Pods just because PostgreSQL briefly fails. Readiness
stops routing to failed dependencies. Worker startup failures are retried by the
container restart policy. Worker SIGTERM stops polling and grants 90 seconds for
graceful activity shutdown; Kubernetes allows 240 seconds before forced termination.
Synchronous provider calls may still need retries/checkpoints after interruption.

Use `kubectl get pods`, `describe`, events, `logs --previous`, and Temporal workflow
history before restarting anything. `kubectl top pods` requires metrics-server,
which this repository does not install. CPU/memory limits and Pod restart counts
are visible without a full monitoring stack.

## Practical metrics and alerts

Start with cluster/container monitoring supplied by the host, JSON log queries,
and Temporal workflow visibility. Suggested signals:

- API error ratio and p95 request latency from request logs.
- Planning completion/failure counts and end-to-end duration from DB timestamps,
  workflow histories and completion logs; no custom metrics endpoint exists yet.
- Temporal queue delay/backlog and worker poller availability.
- Pod restart/OOM events, sustained CPU throttling and memory pressure.
- PostgreSQL storage, connections, backup age, and restore-test results.
- Provider account quota/spend dashboards; activity request allowances are not
  account-wide spending limits and retries may repeat billable work.

For this low-traffic project, alert on a worker absent for several minutes,
repeated failed plans, exhausted disk, or stale backups. Tune thresholds after
observing normal behavior. Prometheus/Grafana can be added later if they answer a
specific question; they are not installed by this chart. No alert delivery has
been configured or tested.

## Security and production limitations

- The application has no login, per-trip authorization, rate limiter, or global
  paid-request budget. A URL shared privately is not access control. Keep it local
  or behind an authenticated access gateway covering every route before exposure.
  A gateway restricts entry, but friends who can access the app still share trip
  visibility. Do not expose the backend, database, Temporal gRPC/UI or Argo UI.
- Ingress is disabled by default; configure TLS and access protection before enabling
  it. No DNS, certificate issuer, public load balancer or cloud resource is created.
- Compose requires an explicit POSTGRES_PASSWORD with no hardcoded fallback. The
  old development default remains in Git history; if an initialized database uses
  it, rotate the role password and update its clients together before hosting.
  Removing a fallback from current source does not rotate existing credentials.
- Runtime Secrets are external to Git and Helm values. Kubernetes base64 is not
  encryption; restrict RBAC and enable encryption at rest/managed secret storage
  for a real cluster. Secret env updates require Pod restarts.
- App images run non-root with pinned base digests; no build receives provider keys.
  Kubernetes Pods drop capabilities, use seccomp and read-only roots, and do not
  mount API tokens. Local Compose Temporal retains its original root setting for
  compatibility with existing volume ownership; it is development-only.
- Optional NetworkPolicy needs an enforcing CNI; kind's default does not enforce it.
  TLS egress remains broad. There is no service-to-service mTLS implementation.
- PostgreSQL and SQLite Temporal in local Kubernetes are single-node development
  dependencies. Production requires independent durable services, backups,
  restore verification and endpoint authentication. Managed Temporal TLS/API keys
  are supported; client-certificate mounts need additional implementation.
- SHA tags are source-addressed, not registry-enforced write-once references.
  Promote image digests for strict content pinning. Review base-image/action updates
  and vulnerability scans before releases. No vulnerability-free guarantee is made.
- Workflow upgrades need replay compatibility. Drain active runs before incompatible
  changes or introduce Temporal worker versioning; Recreate deployment alone does
  not solve replay incompatibility. No automatic DB downgrade is supported.
- Helm migration hooks serialize via a PostgreSQL advisory lock. The application
  still shares a DDL-capable DB credential with migrations. Backups and backward-
  compatible expand/contract migrations are needed before significant schema changes.
- Browser refresh recovery, account history, and data deletion/retention controls
  remain application work. The infrastructure does not change those behaviors.

## Backup and rollback

Compose and local Kubernetes have independent storage. Never run `docker compose
down -v`, delete PostgreSQL/Temporal PVCs, or reset histories to fix an application
error. Export PostgreSQL with pg_dump to protected storage and test restore into a
separate DB. Back up Temporal through the selected production service's supported
procedure, independently of application data. Do not copy a live SQLite file as a
production backup strategy.

For app rollback, select a previously verified digest/revision, check schema and
workflow compatibility, then change Git/Argo or use Helm rollback for Helm-managed
releases. A successful rollout is not proof of recoverability: a full backup/restore
drill and a production failure exercise remain manual work.
