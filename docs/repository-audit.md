# Repository audit (2026-10-25)

Baseline: `8651098`. The working tree was clean. Only `apps/web/AGENTS.md`
provides repository-specific instructions. No CI, Helm, Kubernetes, Argo CD,
Terraform or monitoring deployment existed at audit time.

| Component | Actual implementation | Runtime / dependencies |
| --- | --- | --- |
| Web | Next.js 16.4.3, React 19.3, TypeScript, Material UI | Node 24; npm/package-lock.json; port 3000 |
| API | FastAPI, SQLAlchemy, psycopg | Python 3.12; uv/uv.lock; Uvicorn port 8000 |
| Worker | Temporal Python SDK, OpenAI structured output, SerpApi searches | Python 3.12; separate uv.lock; no HTTP listener |
| Application DB | PostgreSQL 17 | Trips and itinerary JSON; four Alembic revisions, head `f8b4a1c209e6` |
| Workflow engine | Temporal CLI `server start-dev` | gRPC 7233, UI 8233; SQLite on a separate named volume |
| Migrations | API image, `alembic upgrade head` | Compose one-shot dependency before API/worker |

The browser first requests a route proposal, creates a trip, then starts
`plan-trip-{trip_id}` on task queue `voyage-trip-planning`. The worker loads the
trip, generates city/day recommendations, builds a deterministic budget/schedule,
optionally selects live flights/hotels, adds narrative, and atomically saves the
itinerary and completed status. The UI polls status/progress and retrieves the plan.
Expanded day planning requires OpenAI. Legacy requests without `options` retain
synthetic providers. SerpApi is optional; estimates remain when unavailable.
Airbnb URLs are searches, not inventory or reservations. Location autocomplete
uses bundled GeoNames cities and an airportsdata extract, not a paid geocoder.

## Differences from tutorial assumptions

- Kubernetes, Helm and Argo CD were listed in the README but not implemented.
- There are three application build contexts, not one Python package. API and
  worker deliberately share duplicated planning modules; contract tests compare them.
- There are two itinerary formats and both must remain supported.
- The worker has no web health endpoint. It needs worker-specific readiness.
- Compose's frontend used `next dev`; browser API URLs defaulted to localhost.
- Temporal's persisted SQLite development server is not production infrastructure.
- Application PostgreSQL and Temporal persistence are separate and must stay so.
- Trips have no owners or authentication. A private link alone is not access control.
- Frontend state is memory-only; a page refresh does not recover the active trip.

## Checks and risks at audit

Python tests mostly mock DB/provider/Temporal calls. API tests need a syntactically
valid `DATABASE_URL` at import time, not a live DB. Worker fixtures remove provider
credentials. Browser tests mock planning APIs but exercise real local autocomplete
and calendar UI; their clock must be fixed before November 2026. Location tests
run with Node. Ruff, pytest, TypeScript, ESLint and Next build have local tooling.

Docker access requires sandbox approval (approved for local testing). No Kubernetes
context is configured. Helm, kind, actionlint and kubeconform are initially missing.
No remote settings, registry writes, public deployment or paid provider calls are
authorized. All cluster tests must use a dedicated disposable cluster and must
not touch the existing Compose volumes. Provider-free integration coverage should
use the explicit legacy synthetic flow and label it accordingly.

Important delivery risks: unbounded paid requests if exposed publicly; development
container commands; missing Temporal TLS/namespace configuration; worker shutdown;
migration ordering on both Helm and Argo first installs; immutable image promotion;
and workflow replay compatibility across worker releases.

See [validation.md](validation.md) for results obtained during implementation.
