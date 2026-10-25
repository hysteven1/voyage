import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app import main


@pytest.mark.parametrize("status", ["planning", "completed", "failed", "missing"])
def test_progress_queries_temporal_only_for_active_trip(monkeypatch, status):
    session = MagicMock()
    session.return_value.__enter__.return_value.get.return_value = (
        None if status == "missing" else SimpleNamespace(status=status)
    )
    monkeypatch.setattr(main, "Session", session)
    handle = MagicMock()
    handle.query = AsyncMock(
        return_value={"stage": "travel", "label": "Finding stays", "percent": 75}
    )
    client = MagicMock()
    client.get_workflow_handle.return_value = handle
    connect = AsyncMock(return_value=client)
    monkeypatch.setattr(main.Client, "connect", connect)
    if status == "missing":
        with pytest.raises(HTTPException) as exc:
            asyncio.run(main.trip_planning_progress(uuid.uuid4()))
        assert exc.value.status_code == 404
        return
    result = asyncio.run(main.trip_planning_progress(uuid.uuid4()))
    assert result["stage"] == ("travel" if status == "planning" else status)
    assert connect.await_count == int(status == "planning")
    if status == "planning":
        handle.query.assert_awaited_once_with("planning_progress")


def test_progress_survives_unavailable_temporal(monkeypatch):
    session = MagicMock()
    session.return_value.__enter__.return_value.get.return_value = SimpleNamespace(
        status="planning"
    )
    monkeypatch.setattr(main, "Session", session)
    monkeypatch.setattr(
        main.Client, "connect", AsyncMock(side_effect=RuntimeError("unavailable"))
    )
    assert asyncio.run(main.trip_planning_progress(uuid.uuid4()))["percent"] is None
