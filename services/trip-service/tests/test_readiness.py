import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app import main


def test_liveness_and_legacy_health_do_not_need_database(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(main, "engine", engine)
    assert main.liveness() == {"status": "alive", "service": "trip-service"}
    assert main.health_check() == {"status": "ok", "service": "trip-service"}
    engine.connect.assert_not_called()


@pytest.mark.parametrize("unavailable", [False, True])
def test_readiness_queries_database(monkeypatch, unavailable):
    engine = MagicMock()
    monkeypatch.setattr(main, "engine", engine)
    connection = engine.connect.return_value.__enter__.return_value
    if unavailable:
        connection.execute.side_effect = SQLAlchemyError("private database details")

    async def run_check(fn):
        return fn()

    monkeypatch.setattr(main, "run_in_threadpool", run_check)
    if unavailable:
        with pytest.raises(HTTPException) as caught:
            asyncio.run(main.readiness())
        assert caught.value.status_code == 503
        assert caught.value.detail == "Database unavailable"
    else:
        assert asyncio.run(main.readiness()) == {
            "status": "ready", "service": "trip-service", "database": "connected",
        }
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"
    engine.connect.return_value.__exit__.assert_called_once()
