# Trip service

FastAPI on port 8000, SQLAlchemy/psycopg PostgreSQL persistence, Alembic migrations,
route proposals, and Temporal workflow initiation/progress. Python 3.12, uv lockfile.

From this directory, after provisioning local PostgreSQL/Temporal:

```bash
uv sync --locked --dev --no-install-project --python 3.12
# Set DATABASE_URL in a protected local .env; TEMPORAL_ADDRESS defaults to localhost:7233.
uv run --no-sync python -m app.migrate
uv run --no-sync uvicorn app.main:app --reload --port 8000
```

Unit checks use a syntactically valid dummy DB URL; DB/provider/Temporal operations
are mocked. No running database is required for these tests.

```bash
uv run --no-sync ruff check app tests
DATABASE_URL=postgresql+psycopg://voyage:unit-only@localhost:5432/voyage \
  OPENAI_API_KEY= SERPAPI_API_KEY= uv run --no-sync pytest -q
```

`/api/v1/health/live` checks the process; `/api/v1/health/ready` queries PostgreSQL.
`python -m app.migrate` serializes upgrades using a PostgreSQL advisory lock; it
never downgrades. [Environment reference](../../docs/environment.md) and
[architecture](../../docs/architecture.md) describe external configuration.
