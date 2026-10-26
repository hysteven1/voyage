# Environment variables

Do not commit `.env`, Secret manifests with real values, kubeconfigs, passwords,
API keys, or registry credentials. The root `.env.example` has no working provider
credentials. Keep existing database passwords when reusing initialized volumes.

| Variable | Consumers | Default / purpose |
| --- | --- | --- |
| DATABASE_URL | API, migrations, worker | Required SQLAlchemy `postgresql+psycopg://...` URL; use TLS for external DBs |
| POSTGRES_USER / POSTGRES_DB | Compose PostgreSQL and URLs | voyage / voyage; changing these does not rename initialized DBs |
| POSTGRES_PASSWORD | Compose PostgreSQL and URLs | Required, no fallback; choose a unique URL-safe password for a new environment |
| API_INTERNAL_URL | Next server | http://localhost:8000 for native dev; Compose/Helm point to internal API |
| NEXT_PUBLIC_API_URL | Browser bundle | Empty/same-origin by default; optional build-time direct-API override |
| TEMPORAL_ADDRESS | API/worker | localhost:7233 natively; temporal:7233 in local containers |
| TEMPORAL_NAMESPACE | API/worker | default |
| TEMPORAL_TLS | API/worker | false locally; automatically true if a Temporal API key is present and no explicit setting exists |
| TEMPORAL_API_KEY | API/worker | Optional secret for a provisioned managed/TLS endpoint; TLS=false with a key is rejected |
| OPENAI_API_KEY | API/worker | Optional API route reasoning; required for expanded worker day recommendations |
| OPENAI_PLANNING_MODEL | API/worker | gpt-6.1-sol |
| OPENAI_RECOVERY_MODEL | Worker | gpt-4o-mini for bounded recovery |
| OPENAI_MODEL | Worker narrative | gpt-4o-mini |
| SERPAPI_API_KEY | Worker only | Optional live flight/hotel searches; no key means estimates/search links |
| WORKER_MAX_CONCURRENT_ACTIVITIES | Worker | 4; chart validates 1–10 |
| SERVICE_NAME | API/worker logs | Set by Compose/Helm |
| PORT / HOSTNAME | Production web image | 3000 / 0.0.0.0 |
| NEXT_TELEMETRY_DISABLED | Web build/runtime | 1 in container/CI |

Compose uses a local `.env` but does not currently forward managed Temporal
namespace/TLS/API-key settings; use Helm/native settings or an explicit reviewed
Compose override for an external service. Do not put an external URL into
TEMPORAL_ADDRESS while assuming localhost defaults are appropriate.

In Helm, nonsecret settings come from a ConfigMap. The precreated `voyage-runtime`
Secret supplies DATABASE_URL and optional OPENAI_API_KEY, SERPAPI_API_KEY and
TEMPORAL_API_KEY. Local PostgreSQL has a separate `voyage-postgres` Secret.
Production imagePullSecrets are separate credentials. The web Pod receives no
provider or database Secrets. Use externally managed secrets for deployment;
`kubectl create secret generic ... --from-env-file=/protected/path` is a local
alternative that avoids credentials appearing as command arguments.

URL-encode special characters in a manually supplied DATABASE_URL. Alembic escapes
percent characters for ConfigParser interpolation. Compose's assembled URL expects
URL-safe role/password/database components; for other credentials, provide a proper
DATABASE_URL via a reviewed override. Models/provider availability are account-
dependent; infrastructure validation does not verify access to a selected model.

Compose rejects a missing or empty POSTGRES_PASSWORD. Changing `.env` does not
change the password inside an initialized PostgreSQL volume: rotate the database
role and dependent configuration together, without deleting or resetting the volume.
The historical development fallback is publicly visible and must not be reused
for a hosted database or another service.
