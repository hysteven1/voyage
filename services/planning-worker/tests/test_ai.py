import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from temporalio.testing import ActivityEnvironment

from app import ai
from app.ai import fallback_narrative
from app.ai_schemas import TripNarrative, validate_narrative


def test_fallback_matches_itinerary_dates():
    trip = {"destination": "Tokyo, Japan"}
    plan = {
        "days": [
            {
                "date": "2026-11-10",
                "activities": [{"name": "Historical walking tour"}],
            },
            {"date": "2026-11-11", "activities": []},
        ]
    }

    result = fallback_narrative(trip, plan)

    # Source is response metadata, outside the strict narrative schema.
    narrative = TripNarrative.model_validate(
        {key: value for key, value in result.items() if key != "source"}
    )
    validate_narrative(narrative, plan)

    assert result["source"] == "fallback"
    assert len(result["days"]) == 2
    assert "Historical walking tour" in result["days"][0]["description"]


@pytest.fixture
def data():
    return {
        "trip": {"destination": "Tokyo"},
        "plan": {
            "days": [
                {"date": "2026-11-10", "activities": [{"name": "Food tour"}]},
                {"date": "2026-11-11", "activities": []},
            ],
            "budget": {"total": "100.00"},
        },
    }


def parsed_narrative(data):
    result = ai.fallback_narrative(data["trip"], data["plan"])
    result.pop("source")
    return TripNarrative.model_validate(result)


@pytest.mark.parametrize("dates", [[], [0, 0], [1, 0], [0]])
def test_rejects_missing_duplicate_or_reordered_dates(data, dates):
    narrative = parsed_narrative(data)
    narrative.days = [narrative.days[i] for i in dates]
    with pytest.raises(ValueError, match="missing, duplicate, or reordered"):
        validate_narrative(narrative, data["plan"])


def test_schema_rejects_extra_fields(data):
    narrative = parsed_narrative(data).model_dump()
    narrative["price"] = 1
    with pytest.raises(ValidationError):
        TripNarrative.model_validate(narrative)


def test_missing_key_uses_fallback_without_changing_plan(data, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = Mock()
    monkeypatch.setattr(ai, "OpenAI", client)
    before = deepcopy(data)
    result = ActivityEnvironment().run(ai.personalize_itinerary, data)
    assert result["source"] == "fallback"
    assert result["days"][0]["description"] == "Planned activities: Food tour."
    assert result["days"][1]["description"] == "Free time to explore at your own pace."
    assert data == before
    client.assert_not_called()


@pytest.mark.parametrize("has_output", [True, False])
def test_parsed_response_and_missing_output(data, monkeypatch, has_output):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    client = Mock()
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=parsed_narrative(data) if has_output else None
    )
    monkeypatch.setattr(ai, "OpenAI", client)
    if has_output:
        result = ai.personalize_itinerary(data)
        assert result["source"] == "openai"
        request = client.return_value.responses.parse.call_args.kwargs
        assert request["store"] is False
        assert request["model"] == "test-model"
        assert request["text_format"] is TripNarrative
    else:
        with pytest.raises(ValueError, match="no parsed"):
            ai.personalize_itinerary(data)
    client.assert_called_once_with(api_key="test-key", timeout=25.0, max_retries=0)


@pytest.mark.parametrize("ai_fails", [False, True])
def test_workflow_preserves_plan_and_completes_atomically(data, monkeypatch, ai_fails):
    from app import workflows

    original = deepcopy(data["plan"])
    calls = []
    narrative = ai.fallback_narrative(data["trip"], data["plan"])

    async def execute(fn, arg, **kwargs):
        calls.append((fn.__name__, arg))
        if fn is workflows.load_trip:
            return data["trip"]
        if fn is workflows.build_itinerary:
            return data["plan"]
        if fn is workflows.personalize_itinerary:
            assert kwargs["start_to_close_timeout"].total_seconds() == 35
            if ai_fails:
                raise RuntimeError("Provider unavailable")
            return narrative
        if fn is workflows.generate_fallback_narrative:
            return narrative
        return []

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "logger", Mock())
    result = asyncio.run(workflows.PlanTripWorkflow().run("test-trip"))
    assert result == {**original, "narrative": narrative}
    assert data["plan"] == original
    assert calls[-1] == (
        "complete_trip", {"trip_id": "test-trip", "plan": result}
    )
    assert any(name == "generate_fallback_narrative" for name, _ in calls) == ai_fails
