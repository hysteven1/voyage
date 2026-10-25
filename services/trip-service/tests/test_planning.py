from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app import main, planning
from app.planning import TripOptions, build_plan, propose_route, validate_route
from app.schemas import TripCreate, TripResponse


@pytest.fixture
def trip(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return {
        "id": "trip-id",
        "origin": "London, UK",
        "destination": "Paris, France",
        "start_date": "2026-11-01",
        "end_date": "2026-11-08",
        "travelers": 2,
        "budget": "10000",
        "preferences": ["Food"],
        "options": TripOptions(
            route=[{"location": "Paris, France"}], adults=2
        ).model_dump(mode="json"),
    }


def approved(trip):
    return {**trip, "options": propose_route(trip)["options"]}


def test_contract_copies_match():
    root = Path(__file__).resolve().parents[3]
    for filename in ("planning.py", "day_planning.py"):
        assert (root / "services/trip-service/app" / filename).read_bytes() == (
            root / "services/planning-worker/app" / filename
        ).read_bytes()


def test_country_route_and_dates(trip):
    trip["options"]["route"] = [{"location": "Japan"}, {"location": "Kyoto, Japan"}]
    result = approved(trip)
    assert {s["location"] for s in result["options"]["route"]} == {
        "Tokyo, Japan",
        "Kyoto, Japan",
    }
    validate_route(result)
    plan = build_plan(result)
    assert [d["date"] for d in plan["days"]] == [
        str(date(2026, 11, 1) + timedelta(days=i)) for i in range(8)
    ]
    assert len(plan["stays"]) == 2
    assert all(
        len(d["activities"]) == 1 for d in plan["days"] if d["kind"] == "arrival"
    )
    assert len(plan["legs"]) == 3


def test_already_there_without_origin_and_one_way(trip):
    trip["origin"] = None
    trip["options"].update(journey="already_there", endpoint="one_way")
    plan = build_plan(approved(trip))
    assert plan["legs"] == []
    assert plan["stays"][0]["check_in"] == trip["start_date"]


def test_different_endpoint_and_driving(trip):
    trip["options"].update(
        journey="driving", endpoint="different", end_location="Rome, Italy"
    )
    result = approved(trip)
    assert all(s["mode"] == "drive" for s in result["options"]["route"])
    plan = build_plan(result)
    assert plan["legs"][-1]["destination"] == "Rome, Italy"
    assert all(leg["mode"] == "drive" for leg in plan["legs"])


def test_insufficient_nights_and_invalid_allocation(trip):
    trip["end_date"] = "2026-11-02"
    trip["options"]["route"] = [{"location": "Tokyo, Japan"}]
    with pytest.raises(ValueError, match="Not enough nights"):
        propose_route(trip)
    trip["end_date"] = "2026-11-08"
    result = approved(trip)
    result["options"]["route"][0]["nights"] += 1
    with pytest.raises(ValueError, match="must total"):
        validate_route(result)


def test_pace_and_rain_swaps(trip):
    counts = []
    for pace in ["relaxed", "balanced", "busy"]:
        trip["options"]["pace"] = pace
        advice = {
            "Paris, France": {
                "days": [
                    {
                        "title": "Museum district",
                        "area": "City center",
                        "activities": [
                            {
                                "name": f"Museum collection {i}",
                                "duration_minutes": 60,
                                "travel_minutes": 15,
                                "estimated_price": 10,
                            }
                            for i in range(10)
                        ],
                    }
                ]
            }
        }
        plan = build_plan(approved(trip), advice)
        counts.append(
            len(next(d for d in plan["days"] if d["kind"] == "full")["activities"])
        )
        assert all(
            d["rain_alternative"]["excluded_from_total"]
            for d in plan["days"]
            if d["rain_alternative"]
        )
    assert counts == sorted(set(counts))
    assert counts[1] >= 4


def test_budget_arithmetic_and_flexible_ceiling(trip):
    result = approved(trip)
    plan = build_plan(result)
    b = plan["budget"]
    subtotal = sum(
        Decimal(b[k]) for k in ("transport", "lodging", "food", "activities", "car")
    )
    assert Decimal(b["total"]) == subtotal + Decimal(b["contingency"])
    assert Decimal(b["remaining"]) == Decimal(b["limit"]) - Decimal(b["total"])
    result["budget"] = "1"
    with pytest.raises(ValueError, match="exceeds"):
        build_plan(result)
    result["options"].update(budget_mode="flexible", maximum_budget=b["total"])
    assert build_plan(result)["budget"]["above_target"] == str(Decimal(b["total"]) - 1)
    result["options"]["maximum_budget"] = "2"
    with pytest.raises(ValueError, match="exceeds"):
        build_plan(result)


def test_flight_links_and_local_restrictions(trip):
    result = approved(trip)
    result["options"]["route"][0].update(
        mode="flight",
        flight_preferences={
            "max_stops": 0,
            "earliest_departure": "17:00",
            "latest_arrival": "22:00",
            "allow_overnight": False,
        },
    )
    plan = build_plan(result)
    leg = plan["legs"][0]
    query = parse_qs(urlparse(leg["search_url"]).query)["q"][0]
    assert "London, UK" in query and "Paris, France" in query
    assert "17:00" in query and "no overnight" in query
    assert leg["restrictions"]["max_stops"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"adults": 0},
        {"adults": 20, "child_ages": [5]},
        {"child_ages": [18]},
        {"adults": 5, "rooms": 1},
        {"route": [{"location": "Paris"}, {"location": "paris"}]},
    ],
)
def test_invalid_travelers_and_stops_rejected(trip, change):
    trip["options"].update(change)
    with pytest.raises(ValidationError):
        TripCreate.model_validate(trip)


def test_origin_flexible_budget_and_legacy_contract(trip):
    legacy = {k: v for k, v in trip.items() if k not in {"options", "id"}}
    assert TripCreate.model_validate(legacy).destination == "Paris, France"
    assert (
        TripResponse.model_validate(
            {
                **legacy,
                "id": "00000000-0000-0000-0000-000000000001",
                "status": "completed",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ).options
        is None
    )
    trip["origin"] = None
    with pytest.raises(ValidationError, match="Origin"):
        TripCreate.model_validate(trip)
    trip["origin"] = "London"
    trip["options"].update(budget_mode="flexible", maximum_budget=None)
    with pytest.raises(ValidationError, match="maximum"):
        TripCreate.model_validate(trip)


def test_ai_route_failure_and_invalid_response_fall_back(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(
        planning,
        "ai_route",
        lambda _: planning.RouteSuggestion(
            stops=[], return_travel_days=0, assumptions=[], conflicts=[]
        ),
    )
    result = propose_route(trip)
    assert result["source"] == "offline_estimates"
    assert len(result["options"]["route"]) == 1


def test_api_validates_budget_before_writing(trip):
    result = approved(trip)
    result["budget"] = 1
    db = MagicMock()
    with pytest.raises(HTTPException) as caught:
        main.create_trip(TripCreate.model_validate(result), db)
    assert caught.value.status_code == 422
    assert "exceeds" in caught.value.detail
    db.add.assert_not_called()


def test_api_stores_json_safe_preferences(trip):
    result = approved(trip)
    result["options"].update(budget_mode="flexible", maximum_budget="11000.50")
    db = MagicMock()
    saved = main.create_trip(TripCreate.model_validate(result), db)
    assert saved.options["maximum_budget"] == "11000.50"
    assert saved.travelers == 2
    db.commit.assert_called_once()


def test_route_endpoint_does_not_persist_and_rejects_legacy_shape(trip):
    result = main.route_proposal(TripCreate.model_validate(trip))
    assert result["source"] == "offline_estimates"
    assert result["options"]["route"][0]["nights"] == 7
    legacy = {k: v for k, v in trip.items() if k not in {"options", "id"}}
    with pytest.raises(HTTPException) as caught:
        main.route_proposal(TripCreate.model_validate(legacy))
    assert caught.value.status_code == 422


def test_road_route_cannot_cross_known_ocean(trip):
    trip["options"].update(journey="driving")
    trip["options"]["route"] = [{"location": "Tokyo, Japan"}]
    result = approved(trip)
    with pytest.raises(ValueError, match="ocean"):
        validate_route(result)


def test_short_international_routes_do_not_assume_train(trip):
    assert planning.suggested_mode("Tokyo, Japan", "Seoul, South Korea") == "flight"
    assert planning.suggested_mode("London, UK", "Paris, France") == "train"


def test_rental_searches_cover_each_stay(trip):
    trip["options"].update(rental_car=True)
    trip["options"]["route"] = [
        {"location": "Paris, France"},
        {"location": "Rome, Italy"},
    ]
    plan = build_plan(approved(trip))
    assert len(plan["rental_car"]["searches"]) == 2
    for stay, search in zip(plan["stays"], plan["rental_car"]["searches"], strict=True):
        query = parse_qs(urlparse(search["search_url"]).query)["q"][0]
        assert stay["check_in"] in query and stay["check_out"] in query


def test_valid_ai_route_is_reviewable(trip, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(
        planning,
        "ai_route",
        lambda _: planning.RouteSuggestion(
            stops=[
                planning.SuggestedStop(
                    input_index=0, city="Paris, France", mode="flight", travel_days=1
                )
            ],
            return_travel_days=0,
            assumptions=["Review your local arrival date"],
            conflicts=[],
        ),
    )
    proposal = propose_route(trip)
    assert proposal["source"] == "ai_suggestion"
    assert "Review your local arrival date" in proposal["assumptions"]
    assert proposal["options"]["route"][0]["nights"] == 6
    validate_route({**trip, "options": proposal["options"]})


def test_route_conflicts_are_returned_for_review(trip, monkeypatch):
    trip["options"]["notes"] = "I must return on November 10."
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(
        planning,
        "ai_route",
        lambda _: planning.RouteSuggestion(
            stops=[
                planning.SuggestedStop(
                    input_index=0, city="Paris, France", mode="flight", travel_days=0
                )
            ],
            return_travel_days=0,
            assumptions=[],
            conflicts=[
                planning.NoteConflict(
                    message="Notes require returning after the end date",
                    note_excerpt="I must return on November 10.",
                    constraint="dates",
                )
            ],
        ),
    )
    result = main.route_proposal(TripCreate.model_validate(trip))
    assert result["conflicts"] == ["Notes require returning after the end date"]


def test_http_route_review_and_trip_creation(trip, monkeypatch):
    import uuid
    from datetime import UTC, datetime

    from fastapi.testclient import TestClient

    db = MagicMock()

    def initialize(saved):
        saved.id = uuid.uuid4()
        saved.status = "draft"
        saved.created_at = datetime.now(UTC)

    db.add.side_effect = initialize

    def override_db():
        yield db

    monkeypatch.setitem(main.app.dependency_overrides, main.get_db, override_db)
    with TestClient(main.app) as client:
        proposal = client.post("/api/v1/trips/route-proposal", json=trip)
        assert proposal.status_code == 200
        assert proposal.headers["X-Request-ID"]
        response = client.post(
            "/api/v1/trips", json={**trip, "options": proposal.json()["options"]}
        )
        assert response.status_code == 201
        saved = response.json()
        assert saved["options"]["route"][0]["nights"] == 7
        assert saved["destination"] == "Paris, France"
        assert saved["status"] == "draft"
        assert saved["planning_error"] is None


def test_optional_budget_uses_style_without_a_ceiling(trip):
    trip["budget"] = None
    trip["options"].update(budget_enforcement="target", spending_style="value")
    data = approved(trip)
    payload = TripCreate.model_validate(data)
    assert payload.budget is None
    plan = build_plan(data)
    assert plan["budget"]["target"] is None
    assert plan["budget"]["limit"] is None
    assert plan["budget"]["remaining"] is None
    assert Decimal(plan["budget"]["total"]) > 0
    saved = main.create_trip(payload, MagicMock())
    assert saved.budget is None
    assert main.Trip.__table__.c.budget.nullable


def test_budget_per_person_and_group_are_distinct(trip):
    data = approved(trip)
    data["budget"] = "1000"
    data["options"].update(budget_basis="per_person", budget_enforcement="target")
    per_person = build_plan(data)
    assert per_person["budget"]["target"] == "2000.00"
    assert per_person["budget"]["entered_amount"] == "1000.00"
    assert per_person["budget"]["basis"] == "per_person"
    assert per_person["budget"]["limit"] is None
    data["options"]["budget_basis"] = "group"
    group = build_plan(data)
    assert group["budget"]["target"] == "1000.00"
    assert group["budget"]["total"] == per_person["budget"]["total"]


def test_optional_amount_is_a_target_with_a_clear_overage(trip):
    data = approved(trip)
    data["budget"] = "1"
    data["options"].update(budget_enforcement="target", budget_basis="per_person")
    plan = build_plan(data)
    assert (
        Decimal(plan["budget"]["above_target"]) == Decimal(plan["budget"]["total"]) - 2
    )
    assert Decimal(plan["budget"]["per_person_above_target"]) > 0


def test_spending_style_changes_estimates_without_requiring_an_amount(trip):
    data = approved(trip)
    data["budget"] = None
    totals = []
    for style in ["budget", "value", "upscale"]:
        data["options"]["spending_style"] = style
        plan = build_plan(data)
        assert plan["budget"]["spending_style"] == style
        totals.append(Decimal(plan["budget"]["total"]))
    assert totals[0] < totals[1] < totals[2]


def test_global_flight_preferences_apply_to_every_flight_leg(trip):
    preferences = {
        "departure_scope": "all_flights",
        "max_stops": 0,
        "allow_overnight": False,
        "earliest_departure": "17:00",
        "latest_arrival": "22:00",
    }
    trip["options"]["flight_preferences"] = preferences
    data = approved(trip)
    assert data["options"]["route"][0]["flight_preferences"] == preferences
    assert data["options"]["return_flight_preferences"] == preferences
    plan = build_plan(data)
    assert all(
        leg["restrictions"] == preferences
        for leg in plan["legs"]
        if leg["mode"] == "flight"
    )


@pytest.mark.parametrize("notes", ["", "Prefer a convenient hotel."])
def test_optional_interests_cannot_become_route_conflicts(trip, monkeypatch, notes):
    trip["preferences"] = ["Adventure & hiking"]
    trip["options"]["notes"] = notes
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(
        planning,
        "ai_route",
        lambda _: planning.RouteSuggestion(
            stops=[
                planning.SuggestedStop(
                    input_index=0, city="Paris, France", mode="flight", travel_days=0
                )
            ],
            return_travel_days=0,
            assumptions=[],
            conflicts=[
                planning.NoteConflict(
                    message="Traveler's preference for adventure & hiking may not align with urban activities.",
                    note_excerpt="Adventure & hiking",
                    constraint="required_stop",
                )
            ],
        ),
    )
    result = propose_route(trip)
    assert result["conflicts"] == []
    assert result["source"] == "ai_suggestion"


def test_route_request_excludes_optional_activity_interests(trip, monkeypatch):
    import io
    import json

    response = planning.RouteSuggestion(
        stops=[
            planning.SuggestedStop(
                input_index=0, city="Paris, France", mode="flight", travel_days=0
            )
        ],
        return_travel_days=0,
        assumptions=[],
        conflicts=[],
    )

    def capture(request, **kwargs):
        body = json.loads(request.data)
        route_input = json.loads(body["input"][1]["content"])
        assert "preferences" not in route_input
        assert "pace" not in route_input["options"]
        return io.BytesIO(
            json.dumps(
                {
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": response.model_dump_json(),
                                }
                            ]
                        }
                    ]
                }
            ).encode()
        )

    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(planning, "urlopen", capture)
    assert planning.ai_route(trip).conflicts == []


def test_planning_model_supports_quality_model_and_legacy_override(monkeypatch):
    monkeypatch.delenv("OPENAI_PLANNING_MODEL", raising=False)
    assert planning.planning_model_options() == {
        "model": "gpt-6.1-sol",
        "reasoning": {"effort": "medium"},
    }
    monkeypatch.setenv("OPENAI_PLANNING_MODEL", "gpt-4o-mini")
    assert planning.planning_model_options() == {"model": "gpt-4o-mini"}
