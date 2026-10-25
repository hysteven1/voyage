import json
from copy import deepcopy

import pytest
from temporalio.exceptions import ApplicationError

from app import booking


@pytest.fixture
def options():
    return {
        "adults": 2,
        "child_ages": [],
        "rooms": 1,
        "lodging": "hotel",
        "spending_style": "value",
    }


@pytest.fixture
def leg():
    return {
        "origin": "LHR",
        "destination": "CDG",
        "departure_date": "2027-02-02",
        "arrival_date": "2027-02-02",
        "search_url": "https://www.google.com/travel/flights?q=fallback",
        "restrictions": {
            "max_stops": 0,
            "earliest_departure": "17:00",
            "latest_arrival": "22:00",
            "allow_overnight": False,
        },
    }


def offer(departure="2027-02-02 18:00", arrival="2027-02-02 20:00", price=200):
    return {
        "price": price,
        "total_duration": 120,
        "flights": [
            {
                "airline": "Example Air",
                "flight_number": "EA 123",
                "departure_airport": {"id": "LHR", "time": departure},
                "arrival_airport": {"id": "CDG", "time": arrival},
            }
        ],
    }


def test_flight_selection_respects_dates_times_and_returns_pinned_link(
    monkeypatch, options, leg
):
    provider = booking.SerpApi()
    searches = []
    alternatives = "https://www.google.com/travel/flights?tfs=route"
    pinned_url = "https://www.google.com/travel/flights?tfs=selected"

    def query(**params):
        searches.append(params)
        if "selected_flights_json" in params:
            assert "departure_id" not in params and "outbound_date" not in params
            assert (
                json.loads(params["selected_flights_json"])["outbound"][0][
                    "flight_number"
                ]
                == "EA123"
            )
            return {"search_metadata": {"google_flights_url": pinned_url}}
        return {
            "search_metadata": {"google_flights_url": alternatives},
            "best_flights": [
                offer(departure="2027-02-02 16:45", price=50),
                offer(arrival="2027-02-03 20:00", price=60),
                offer(),
            ],
        }

    monkeypatch.setattr(provider, "query", query)
    result = provider.flight(leg, options)
    assert result["selected_flight"]["price"] == "200.00"
    assert result["selected_flight"]["price_basis"] == "requested_party"
    assert result["selected_flight"]["google_flights_url"] == pinned_url
    assert result["alternatives_url"] == alternatives
    assert searches[0]["stops"] == 1
    assert searches[0]["adults"] == 2
    assert searches[0]["outbound_times"] == "17,23,0,22"


def test_no_matching_flight_preserves_search_link(monkeypatch, options, leg):
    provider = booking.SerpApi()
    monkeypatch.setattr(
        provider,
        "query",
        lambda **_: {"best_flights": [offer(arrival="2027-02-03 02:00")]},
    )
    result = provider.flight(leg, options)
    assert result["selection_status"] == "no_matching_offer"
    assert "selected_flight" not in result
    assert result["alternatives_url"] == leg["search_url"]


def test_bare_route_is_never_labeled_selected_flight_link(monkeypatch, options, leg):
    provider = booking.SerpApi()
    monkeypatch.setattr(
        provider,
        "query",
        lambda **_: {
            "best_flights": [offer()],
            "search_metadata": {
                "google_flights_url": "https://www.google.com/travel/flights?q=route"
            },
        },
    )
    assert (
        provider.flight(leg, options)["selected_flight"]["google_flights_url"] is None
    )


def test_hotel_selects_reviewed_property_and_preserves_dated_alternatives(
    monkeypatch, options
):
    provider = booking.SerpApi()
    options["child_ages"] = [0, 7]
    searches = []
    prop = {
        "name": "Example Central Hotel",
        "type": "hotel",
        "overall_rating": 4.6,
        "reviews": 200,
        "location_rating": 4.7,
        "property_token": "property-1",
        "total_rate": {"extracted_lowest": 700},
    }
    alternatives = "https://www.google.com/travel/search?dates=2027-02-03"
    booking_url = "https://www.example.com/reserve?checkin=2027-02-03"

    def query(**params):
        searches.append(params)
        if params.get("property_token"):
            return {
                **prop,
                "prices": [
                    {
                        "link": "https://www.example.com/higher-price",
                        "total_rate": {"extracted_lowest": 900},
                    },
                    {"link": booking_url, "total_rate": {"extracted_lowest": 700}},
                ],
            }
        return {
            "properties": [{**prop, "name": "Too few reviews", "reviews": 5}, prop],
            "search_metadata": {"google_hotels_url": alternatives},
        }

    monkeypatch.setattr(provider, "query", query)
    result = provider.stay(
        {
            "area": "Shinjuku",
            "location": "Tokyo, Japan",
            "check_in": "2027-02-03",
            "check_out": "2027-02-10",
        },
        options,
    )
    assert result["selected_stay"]["name"] == prop["name"]
    assert result["selected_stay"]["booking_url"] == booking_url
    assert result["selected_stay"]["quoted_total"] == "700.00"
    assert result["alternatives_url"] == alternatives
    assert searches[0]["check_out_date"] == "2027-02-10"
    assert searches[0]["children_ages"] == "1,7"
    assert "checkin=2027-02-03" in result["rental_alternatives_url"]
    assert "infants=1" in result["rental_alternatives_url"]


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "http://example.com",
        "https://serpapi.com/search.json",
        "https://example.com?api_key=secret",
    ],
)
def test_unsafe_links_are_rejected(url):
    assert booking.safe_link(url) is None


@pytest.fixture
def plan():
    return {
        "travelers": 2,
        "legs": [{"mode": "flight", "estimated_cost": "400"}],
        "stays": [{"location": "Tokyo", "estimated_cost": "700"}],
        "destination_estimates": [
            {"location": "Tokyo", "lodging": "600", "food": "100", "activities": "50"}
        ],
        "budget": {
            "transport": "300",
            "lodging": "600",
            "food": "100",
            "activities": "50",
            "car": "0",
            "target": "1000",
            "limit": None,
        },
        "assumptions": [],
    }


def test_quote_costs_recalculate_totals_and_preserve_hard_ceiling(plan):
    booking.refresh_estimates(plan)
    assert plan["budget"]["total"] == "1437.50"
    assert plan["budget"]["per_person_total"] == "718.75"
    assert plan["budget"]["above_target"] == "437.50"
    assert plan["destination_estimates"][0]["subtotal"] == "850.00"
    plan["budget"]["limit"] = "1000"
    with pytest.raises(ApplicationError, match="above") as caught:
        booking.refresh_estimates(plan)
    assert caught.value.non_retryable


def test_no_key_uses_existing_estimates(plan, options, monkeypatch):
    monkeypatch.setattr(
        booking.SerpApi, "query", lambda **_: pytest.fail("Unexpected live query")
    )
    result = booking.select_travel_options(
        {"trip": {"id": "trip", "options": options}, "plan": plan}
    )
    assert result["booking_source"] == "not_configured"
    assert result["budget"] == plan["budget"]


def test_activity_combines_quotes_and_does_not_mutate_input(plan, options, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "unit-test-only")
    monkeypatch.setattr(
        booking.SerpApi, "flight", lambda *_: {"selected_flight": {"price": "450"}}
    )
    monkeypatch.setattr(
        booking.SerpApi, "stay", lambda *_: {"selected_stay": {"quoted_total": "750"}}
    )
    original = deepcopy(plan)
    result = booking.select_travel_options(
        {"trip": {"id": "trip", "options": options}, "plan": plan}
    )
    assert result["budget"]["total"] == "1552.50"
    assert result["booking_source"] == "serpapi"
    assert plan == original


def test_provider_failure_logs_no_credentials(plan, options, monkeypatch, caplog):
    secret = "dummy-private-value"
    monkeypatch.setenv("SERPAPI_API_KEY", secret)

    def fail(*_):
        raise RuntimeError("https://serpapi.com/search?api_key=" + secret)

    monkeypatch.setattr(booking.SerpApi, "flight", fail)
    monkeypatch.setattr(booking.SerpApi, "stay", fail)
    result = booking.select_travel_options(
        {"trip": {"id": "trip", "options": options}, "plan": plan}
    )
    assert result["legs"][0]["selection_status"] == "unavailable"
    assert result["budget"] == plan["budget"]
    assert secret not in caplog.text
    assert "api_key=" not in caplog.text
