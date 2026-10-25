import asyncio
import json
from unittest.mock import MagicMock, Mock

import pytest

from app import activities, workflows


@pytest.fixture
def transaction(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(activities, "engine", engine)
    context = engine.begin.return_value
    context.__exit__.return_value = False
    connection = context.__enter__.return_value
    connection.execute.return_value.rowcount = 1
    return engine, context, connection


def test_completion_uses_one_transaction(transaction):
    engine, context, connection = transaction
    plan = {"days": [], "destination": "Tokyo"}
    activities.complete_trip({"trip_id": "trip-id", "plan": plan})

    engine.begin.assert_called_once_with()
    assert connection.execute.call_count == 2
    insert, update = connection.execute.call_args_list
    assert json.loads(insert.args[1]["plan"]) == plan
    assert "ON CONFLICT (trip_id)" in str(insert.args[0])
    assert "status = 'completed'" in str(update.args[0])
    assert update.args[1] == {"trip_id": "trip-id"}
    context.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("failure", ["insert", "update", "missing_trip"])
def test_completion_exits_transaction_with_error(transaction, failure):
    _, context, connection = transaction
    error = RuntimeError("Database unavailable")
    if failure == "insert":
        connection.execute.side_effect = error
    elif failure == "update":
        connection.execute.side_effect = [Mock(), error]
    else:
        connection.execute.return_value.rowcount = 0

    with pytest.raises((RuntimeError, ValueError)) as caught:
        activities.complete_trip({"trip_id": "trip-id", "plan": {}})

    # SQLAlchemy's begin context rolls back when an exception leaves the block.
    assert context.__exit__.call_args.args[1] is caught.value
    assert connection.execute.call_count == (1 if failure == "insert" else 2)


@pytest.mark.parametrize("status_update_fails", [False, True])
def test_persistence_failure_marks_failed_and_preserves_error(monkeypatch, status_update_fails):
    failure = RuntimeError("Persistence failed")
    calls = []

    async def execute(fn, arg, **kwargs):
        calls.append((fn, arg, kwargs))
        if fn is workflows.complete_trip:
            raise failure
        if (
            fn is workflows.update_trip_status
            and arg["status"] == "failed"
            and status_update_fails
        ):
            raise RuntimeError("Status update failed")
        return {}

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "logger", Mock())

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(workflows.PlanTripWorkflow().run("trip-id"))

    assert caught.value is failure
    fn, arg, options = calls[-1]
    assert fn is workflows.update_trip_status
    assert arg["trip_id"] == "trip-id"
    assert arg["status"] == "failed"
    assert "Try again" in arg["error"]
    assert options["start_to_close_timeout"].total_seconds() == 15
    assert options["retry_policy"].maximum_attempts == 3
