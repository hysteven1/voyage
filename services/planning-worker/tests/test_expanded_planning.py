import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from temporalio.exceptions import ApplicationError

from app import places, workflows
from app.planning import TripOptions, build_plan, propose_route


@pytest.fixture
def trip(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    data = {
        "id": "trip-id",
        "origin": None,
        "destination": "Paris, France",
        "start_date": "2026-11-01",
        "end_date": "2026-11-08",
        "travelers": 2,
        "budget": "10000",
        "preferences": ["Food"],
        "options": TripOptions(
            journey="already_there",
            endpoint="one_way",
            adults=2,
            route=[{"location": "Paris, France"}],
        ).model_dump(mode="json"),
    }
    data["options"] = propose_route(data)["options"]
    return data


def advice():
    return places.PlaceAdvice(
        cities=[
            places.CityAdvice(
                location="Paris, France",
                area="Central neighborhood",
                days=[
                    places.DayIdea(
                        title=f"Neighborhood {i}",
                        area=f"District {i}",
                        full_day=False,
                        travel_minutes=0,
                        rain="Indoor gallery",
                        activities=[
                            places.Place(
                                name=f"Museum {i}",
                                category="culture",
                                area=f"District {i}",
                                estimated_price=10,
                                duration_minutes=120,
                                travel_minutes=15,
                            )
                        ],
                    )
                    for i in range(7)
                ],
            )
        ],
        conflicts=[],
    )


def test_optional_places_and_grouped_days(trip, monkeypatch):
    assert places.suggest_places(trip) == {}
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=advice()
    )
    monkeypatch.setattr(places, "OpenAI", client)
    suggestions = places.suggest_places(trip)
    plan = build_plan(trip, suggestions)
    for day in plan["days"]:
        if day["activities"]:
            assert {a["area"] for a in day["activities"]} == {day["area"]}
    assert plan["days"][0]["kind"] == "full"
    names = [a["name"] for d in plan["days"] for a in d["activities"]]
    assert len(names) == len(set(names))
    assert client.return_value.responses.parse.call_args.kwargs["store"] is False


def test_invalid_or_failed_places_fall_back(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    client.return_value.responses.parse.side_effect = RuntimeError(
        "Provider unavailable"
    )
    monkeypatch.setattr(places, "OpenAI", client)
    assert places.suggest_places(trip) == {}
    client.return_value.responses.parse.side_effect = None
    invalid = advice()
    invalid.cities[0].days[0].activities[0].duration_minutes = 1000
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=invalid
    )
    assert places.suggest_places(trip) == {}


def test_notes_conflicts_are_actionable(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    invalid = advice()
    invalid.conflicts = ["Requested arrival is outside your date range"]
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=invalid
    )
    monkeypatch.setattr(places, "OpenAI", client)
    with pytest.raises(
        ApplicationError, match="Resolve these planning conflicts"
    ) as caught:
        places.suggest_places(trip)
    assert caught.value.non_retryable


@pytest.mark.parametrize("fail", [False, True])
def test_expanded_workflow_completes_or_records_failure(trip, monkeypatch, fail):
    calls = []

    async def execute(fn, arg, **kwargs):
        calls.append((fn, arg))
        if fn is workflows.load_trip:
            return trip
        if fn is workflows.suggest_places:
            return {}
        if fn is workflows.build_itinerary:
            if fail:
                raise ApplicationError(
                    "Estimated cost exceeds your ceiling", non_retryable=True
                )
            return build_plan(trip)
        if fn is workflows.select_travel_options:
            return arg["plan"]
        if fn is workflows.personalize_itinerary:
            return {"title": "Trip", "days": []}
        return None

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "logger", Mock())
    monkeypatch.setattr(workflows.workflow, "patched", lambda _: True)
    if fail:
        with pytest.raises(ApplicationError, match="exceeds"):
            asyncio.run(workflows.PlanTripWorkflow().run(trip["id"]))
        assert calls[-1][1]["status"] == "failed"
        assert "exceeds" in calls[-1][1]["error"]
    else:
        result = asyncio.run(workflows.PlanTripWorkflow().run(trip["id"]))
        assert result["version"] == 2
        assert calls[-1] == (
            workflows.complete_trip,
            {"trip_id": trip["id"], "plan": result},
        )
        assert not any(fn is workflows.search_flights for fn, _ in calls)
