from app.optimizer import optimize_trip


def sample_trip(budget="3000.00"):
    return {
        "id": "test-trip",
        "origin": "Washington, DC",
        "destination": "Tokyo, Japan",
        "start_date": "2026-11-10",
        "end_date": "2026-11-17",
        "travelers": 2,
        "budget": budget,
        "preferences": ["Food", "Culture"],
    }


FLIGHTS = [
    {"id": "f1", "price": "900.00"},
    {"id": "f2", "price": "1150.00"},
]

HOTELS = [
    {
        "id": "h1",
        "price_per_night": "100.00",
        "capacity": 2,
    }
]

ACTIVITIES = [
    {
        "id": "a1",
        "name": "Food tour",
        "category": "food",
        "price_per_person": "45.00",
        "duration_hours": 3,
    }
]


def test_itinerary_stays_within_budget():
    plan = optimize_trip(
        sample_trip(),
        FLIGHTS,
        HOTELS,
        ACTIVITIES,
    )

    assert float(plan["budget"]["total"]) <= 3000
    assert float(plan["budget"]["remaining"]) >= 0


def test_cheapest_feasible_flight_selected():
    plan = optimize_trip(
        sample_trip(),
        FLIGHTS,
        HOTELS,
        ACTIVITIES,
    )

    assert plan["flight"]["id"] == "f1"


def test_infeasible_budget_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        optimize_trip(
            sample_trip(budget="100.00"),
            FLIGHTS,
            HOTELS,
            ACTIVITIES,
        )
