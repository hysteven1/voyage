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
                highlights=[
                    places.Highlight(
                        name="Museum 0", reason="The city's signature collection"
                    )
                ],
                day_trips=[
                    places.DayTripIdea(
                        name="Versailles",
                        reason="A worthwhile palace excursion",
                        travel_minutes=120,
                    )
                ],
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
                                must_see=i == 0,
                                reason="A signature collection" if i == 0 else "",
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
    with pytest.raises(ApplicationError, match="not configured"):
        places.suggest_places(trip)
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
    assert plan["days"][0]["activities"][0]["must_see"]
    assert plan["destination_highlights"][0]["highlights"][0]["name"] == "Museum 0"
    assert plan["destination_highlights"][0]["day_trips"][0]["name"] == "Versailles"
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
    with pytest.raises(ApplicationError, match="temporarily unavailable"):
        places.suggest_places(trip)
    client.return_value.responses.parse.side_effect = None
    invalid = advice()
    invalid.cities[0].days[0].activities[0].duration_minutes = 1000
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=invalid
    )
    with pytest.raises(ApplicationError, match="temporarily unavailable"):
        places.suggest_places(trip)


def test_notes_conflicts_are_actionable(trip, monkeypatch):
    trip["options"]["notes"] = "I must arrive on November 12."
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    invalid = advice()
    invalid.conflicts = [
        places.NoteConflict(
            message="Requested arrival is outside your date range",
            note_excerpt="I must arrive on November 12.",
            constraint="dates",
        )
    ]
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


def test_ai_repairs_missing_days_for_destinations_beyond_tokyo(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    incomplete = advice()
    incomplete.cities[0].days = incomplete.cities[0].days[:3]
    client = Mock()
    client.return_value.responses.parse.side_effect = [
        SimpleNamespace(output_parsed=incomplete),
        SimpleNamespace(output_parsed=advice()),
    ]
    monkeypatch.setattr(places, "OpenAI", client)
    result = places.suggest_destination(
        trip, [{"location": "Paris, France", "day_plan_count": 7, "day_trip_limit": 1}]
    )
    assert len(result["Paris, France"]["days"]) == 7
    assert client.return_value.responses.parse.call_count == 2
    assert result["Paris, France"]["quality_notes"] == []


def test_short_ai_stays_do_not_surface_day_trip_recommendations(trip, monkeypatch):
    trip["options"]["route"][0]["nights"] = 3
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=advice()
    )
    monkeypatch.setattr(places, "OpenAI", client)
    result = places.suggest_places(trip)
    assert result["Paris, France"]["day_trips"] == []


def test_extra_day_trip_is_replaced_with_a_full_city_day(trip, monkeypatch):
    trip["end_date"] = "2026-11-06"
    trip["options"]["route"][0]["nights"] = 5
    trip["options"]["pace"] = "busy"
    initial = advice()
    city = initial.cities[0]
    city.days = city.days[:5]
    for day in city.days:
        day.activities[0].duration_minutes = 480
    for day in city.days[:2]:
        day.day_trip = True
        day.full_day = True
    supplemental = advice()
    supplemental.cities[0].days = [
        places.DayIdea(
            title="Additional city district",
            area="City center",
            full_day=False,
            day_trip=False,
            travel_minutes=0,
            rain="Local gallery",
            activities=[
                places.Place(
                    name="New major city collection",
                    category="museum",
                    area="City center",
                    estimated_price=20,
                    duration_minutes=480,
                    travel_minutes=30,
                )
            ],
        )
    ]
    client = Mock()
    client.return_value.responses.parse.side_effect = [
        SimpleNamespace(output_parsed=initial.model_copy(deep=True)),
        SimpleNamespace(output_parsed=initial.model_copy(deep=True)),
        SimpleNamespace(output_parsed=supplemental),
    ]
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(places, "OpenAI", client)
    result = places.suggest_destination(
        trip, [{"location": "Paris, France", "day_plan_count": 5, "day_trip_limit": 1}]
    )
    plan = build_plan(trip, result)
    full_days = [day for day in plan["days"] if day["kind"] == "full"]
    assert len(full_days) == 5
    assert sum(day["day_trip"] for day in full_days) == 1
    assert all(not day["needs_personalization"] for day in full_days)
    assert all(day["estimated_minutes"] >= 480 for day in full_days)
    assert client.return_value.responses.parse.call_count == 3
    assert result["Paris, France"]["quality_notes"] == []


@pytest.mark.parametrize("notes", ["", "Prefer a convenient hotel."])
def test_interests_are_optional_in_activity_planning(trip, monkeypatch, notes):
    trip["preferences"] = ["Adventure & hiking"]
    trip["options"]["notes"] = notes
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    suggestions = advice()
    suggestions.conflicts = [
        places.NoteConflict(
            message="Adventure & hiking may not align with urban activities.",
            note_excerpt="Adventure & hiking",
            constraint="required_stop",
        )
    ]
    client = Mock()
    client.return_value.responses.parse.return_value = SimpleNamespace(
        output_parsed=suggestions
    )
    monkeypatch.setattr(places, "OpenAI", client)
    result = places.suggest_places(trip)
    assert result["Paris, France"]["days"]


def test_multiple_destinations_do_not_complete_when_one_times_out(trip, monkeypatch):
    trip.update(
        origin="Washington, United States",
        start_date="2026-12-06",
        end_date="2026-12-26",
    )
    trip["options"].update(
        journey="flying",
        endpoint="return",
        return_travel_days=1,
        route=[
            {
                "location": "Tokyo, Japan",
                "nights": 6,
                "travel_days": 1,
                "mode": "flight",
            },
            {
                "location": "Kyoto, Japan",
                "nights": 6,
                "travel_days": 0,
                "mode": "train",
            },
            {
                "location": "Osaka, Japan",
                "nights": 6,
                "travel_days": 0,
                "mode": "train",
            },
        ],
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")

    def generate(_, requests):
        assert len(requests) == 1
        request = requests[0]
        location = request["location"]
        if location == "Kyoto, Japan":
            raise TimeoutError("simulated provider timeout")
        city = advice().cities[0].model_dump()
        city["location"] = location
        return {location: city}

    monkeypatch.setattr(places, "suggest_destination", generate)
    with pytest.raises(TimeoutError):
        places.suggest_places(trip)


def test_timeout_recovers_using_faster_model(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    client = Mock()
    client.return_value.responses.parse.side_effect = [
        TimeoutError("provider timeout"),
        SimpleNamespace(output_parsed=advice()),
    ]
    monkeypatch.setattr(places, "OpenAI", client)
    result = places.suggest_destination(
        trip, [{"location": "Paris, France", "day_plan_count": 7, "day_trip_limit": 1}]
    )
    assert len(result["Paris, France"]["days"]) == 7
    calls = client.return_value.responses.parse.call_args_list
    assert calls[0].kwargs["reasoning"]["effort"] == "low"
    assert calls[1].kwargs["model"] == "gpt-4o-mini"
    assert "reasoning" not in calls[1].kwargs


def test_long_stay_uses_small_batches_without_repeating_attractions(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    requests_seen = []

    def generate(batch_trip, requests):
        request = requests[0]
        requests_seen.append(request)
        offset = len(batch_trip["already_planned"])
        city = advice().cities[0].model_dump()
        city["days"] = city["days"][offset : offset + request["day_plan_count"]]
        return {request["location"]: city}

    monkeypatch.setattr(places, "suggest_destination", generate)
    result = places.suggest_places(trip)
    assert [r["day_plan_count"] for r in requests_seen] == [3, 3, 1]
    plan = build_plan(trip, result)
    assert not plan["incomplete_destinations"]
    assert all(d["activities"] for d in plan["days"] if d["kind"] == "full")
