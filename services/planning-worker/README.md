# Planning worker

Python 3.12 Temporal worker on task queue `voyage-trip-planning`, with separate
uv.lock. Expanded trips use OpenAI structured recommendations and optional SerpApi
flight/hotel offers. Legacy trips use synthetic providers. No reservations are made.

```bash
cd services/planning-worker
uv sync --locked --dev --no-install-project --python 3.12
# Set DATABASE_URL and optional provider keys in a protected local .env.
# Start PostgreSQL, apply API migrations, and start Temporal first.
uv run --no-sync python -m app.worker
```

The internal probe server listens on 8081. Liveness checks the event loop; readiness
checks worker state and Temporal connectivity. SIGTERM drains the worker with a
90-second grace period; provider work may resume through Temporal retries.

```bash
uv run --no-sync ruff check app tests
DATABASE_URL=postgresql+psycopg://voyage:unit-only@localhost:5432/voyage \
  OPENAI_API_KEY= SERPAPI_API_KEY= uv run --no-sync pytest -q
```

Tests remove live provider credentials and mock external services. Planning modules
are mirrored in the API build context; contract tests enforce matching copies.
See [environment settings](../../docs/environment.md) and
[workflow deployment limitations](../../docs/operations.md) before changing workers.
