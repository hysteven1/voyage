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
    assert result["alternatives_url"].startswith(
        "https://www.google.com/travel/flights/search?tfs="
    )


def test_large_flight_group_does_not_submit_unsupported_party_size(
    monkeypatch, options, leg
):
    options.update(adults=10)
    provider = booking.SerpApi()
    monkeypatch.setattr(
        provider,
        "query",
        lambda **_: pytest.fail("Large group must not request a misleading quote"),
    )
    result = provider.flight(leg, options)
    assert result["selection_status"] == "group_search_only"
    assert result["search_travelers"] == 1
    assert "9 travelers" in result["search_note"]
    assert "selected_flight" not in result
    assert "/travel/flights/search?tfs=" in result["alternatives_url"]


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
    assert result["alternatives_url"].startswith(
        "https://www.google.com/travel/search?"
    )
    assert "ts=" in result["alternatives_url"]
    assert searches[0]["q"] == "Tokyo, Japan hotels"
    assert searches[0]["check_out_date"] == "2027-02-10"
    assert searches[0]["adults"] == 4
    assert "children_ages" not in searches[0]
    assert "checkin=2027-02-03" in result["rental_alternatives_url"]
    assert "children=2" in result["rental_alternatives_url"]


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
        "stays": [
            {
                "location": "Tokyo",
                "estimated_cost": "700",
                "check_in": "2027-02-03",
                "check_out": "2027-02-10",
            }
        ],
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
    assert "airbnb.com" in result["stays"][0]["rental_alternatives_url"]


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
    assert "airbnb.com" in result["stays"][0]["rental_alternatives_url"]


def test_large_group_selects_one_hotel_and_multiplies_room_estimate(
    plan, options, monkeypatch
):
    monkeypatch.setenv("SERPAPI_API_KEY", "unit-test-only")
    options.update(adults=8, children=4, child_ages=[], rooms=3)
    plan["travelers"] = 12
    searches = []
    prop = {
        "name": "Example Family Hotel",
        "type": "hotel",
        "overall_rating": 4.5,
        "reviews": 400,
        "property_token": "family",
        "total_rate": {"extracted_lowest": 300},
        "link": "https://example.com/hotel",
    }

    def query(self, **params):
        searches.append(params)
        if params.get("property_token"):
            raise booking.ProviderError("Detail expansion temporarily unavailable")
        return {"properties": [prop]}

    monkeypatch.setattr(booking.SerpApi, "query", query)
    monkeypatch.setattr(booking.SerpApi, "flight", lambda *_: {})
    result = booking.select_travel_options(
        {"trip": {"id": "trip", "options": options}, "plan": plan}
    )
    assert all(p["adults"] == 4 and p["children"] == 0 for p in searches)
    assert all("children_ages" not in p for p in searches)
    stay = result["stays"][0]
    assert stay["selected_stay"]["name"] == prop["name"]
    assert stay["selected_stay"]["quoted_total"] == "300.00"
    assert stay["selected_stay"]["estimated_group_total"] == "900.00"
    assert stay["estimated_cost"] == "900.00"
    assert stay["selected_stay"]["rooms_requested"] == 3
    assert "all rooms are available" in stay["selected_stay"]["capacity_note"]
    assert "adults=8" in stay["rental_alternatives_url"]
    assert "children=4" in stay["rental_alternatives_url"]


def test_unknown_child_ages_use_labeled_adult_fare_estimate(monkeypatch, options, leg):
    options.update(children=2, child_ages=[])
    provider = booking.SerpApi()
    searches = []

    def query(**params):
        searches.append(params)
        return {"best_flights": [offer()]}

    monkeypatch.setattr(provider, "query", query)
    result = provider.flight(leg, options)
    assert searches[0]["adults"] == 4
    assert searches[0]["children"] == 0
    assert result["selected_flight"]["price_basis"] == "adult_fare_estimate"
    assert "child fares may differ" in result["selected_flight"]["price_note"]


def test_provided_ages_use_infant_child_and_adult_fare_categories(
    monkeypatch, options, leg
):
    options.update(children=3, child_ages=[0, 7, 14])
    provider = booking.SerpApi()
    searches = []

    def query(**params):
        searches.append(params)
        return {"best_flights": [offer()]}

    monkeypatch.setattr(provider, "query", query)
    result = provider.flight(leg, options)
    assert searches[0]["adults"] == 3
    assert searches[0]["children"] == 1
    assert searches[0]["infants_in_seat"] == 1
    assert result["selected_flight"]["price_basis"] == "requested_party"


def test_long_city_label_resolves_the_google_city_airport_group_and_caches(monkeypatch):
    provider = booking.SerpApi()
    calls = []

    def query(**params):
        calls.append(params)
        return {
            "suggestions": [
                {"type": "city", "name": "Lake Washington", "id": "/m/lake"},
                {"type": "city", "name": "Washington", "id": "/m/0rh6k"},
            ]
        }

    monkeypatch.setattr(provider, "query", query)
    label = "Washington, District of Columbia, United States"
    assert provider.city_id(label) == "/m/0rh6k"
    assert provider.city_id(label) == "/m/0rh6k"
    assert len(calls) == 1
    assert calls[0]["q"] == "Washington, United States"


def test_city_lookup_retries_short_name_without_choosing_a_single_airport(monkeypatch):
    provider = booking.SerpApi()
    calls = []

    def query(**params):
        calls.append(params["q"])
        if len(calls) == 1:
            raise booking.ProviderError("No suggestions")
        return {
            "suggestions": [{"type": "city", "name": "Washington", "id": "/m/0rh6k"}]
        }

    monkeypatch.setattr(provider, "query", query)
    assert (
        provider.city_id("Washington, District of Columbia, United States")
        == "/m/0rh6k"
    )
    assert calls == ["Washington, United States", "Washington"]


def test_overnight_arrival_uses_booking_window_not_estimated_arrival_date(
    monkeypatch, options, leg
):
    provider = booking.SerpApi()
    leg.update(
        departure_date="2026-11-01",
        arrival_date="2026-11-01",
        latest_arrival_date="2026-11-06",
        restrictions={"max_stops": 0, "allow_overnight": True},
    )
    monkeypatch.setattr(
        provider,
        "query",
        lambda **_: {
            "best_flights": [
                offer("2026-11-01 12:20", "2026-11-02 16:50"),
                offer("2026-11-01 12:20", "2026-11-07 16:50", price=50),
            ]
        },
    )
    result = provider.flight(leg, options)
    assert result["selection_status"] == "selected"
    assert result["selected_flight"]["arrival_time"] == "2026-11-02 16:50"


def test_arrival_rebuilds_stay_and_daily_plans_before_hotel_search(monkeypatch):
    from app.planning import TripOptions, build_plan

    trip = {
        "id": "trip",
        "origin": "Washington, District of Columbia, United States",
        "destination": "Tokyo, Japan",
        "start_date": "2026-11-01",
        "end_date": "2026-11-07",
        "travelers": 2,
        "budget": None,
        "preferences": [],
        "options": TripOptions(
            adults=2,
            route=[{"location": "Tokyo, Japan", "nights": 6, "travel_days": 0}],
            budget_enforcement="target",
        ).model_dump(mode="json"),
    }
    trip["options"]["route"][0]["mode"] = "flight"
    plan = build_plan(trip)
    monkeypatch.setenv("SERPAPI_API_KEY", "test-only")

    def flight(_, leg, options):
        assert leg["latest_arrival_date"] in ("2026-11-06", "2026-11-07")
        return {
            "selection_status": "selected",
            "selected_flight": {
                "price": "500",
                "duration_minutes": 840,
                "arrival_time": "2026-11-02 16:50"
                if leg["destination"] == "Tokyo, Japan"
                else "2026-11-07 15:40",
            },
        }

    hotel_dates = []

    def stay(_, stay, options):
        hotel_dates.append((stay["check_in"], stay["check_out"]))
        return {
            "selection_status": "selected",
            "selected_stay": {"quoted_total": "550"},
        }

    monkeypatch.setattr(booking.SerpApi, "flight", flight)
    monkeypatch.setattr(booking.SerpApi, "stay", stay)
    result = booking.select_travel_options({"trip": trip, "plan": plan})
    assert hotel_dates == [("2026-11-02", "2026-11-07")]
    assert result["days"][0]["date"] == "2026-11-01"
    assert result["days"][0]["kind"] == "transit"
    assert result["days"][0]["activities"] == []
    assert result["days"][1]["kind"] == "arrival"
    assert result["legs"][0]["arrival_date"] == "2026-11-02"
    assert result["legs"][0]["estimated_hours"] == 14
    assert result["route"][0]["nights"] == 5
    assert result["route"][0]["travel_days"] == 1
    assert result["budget"]["lodging"] == "550.00"
    assert plan["stays"][0]["check_in"] == "2026-11-01"


@pytest.mark.parametrize(
    ("code", "when", "label"),
    [
        ("IAD", "2026-11-22 12:20", "EST"),
        ("IAD", "2026-07-22 12:20", "EDT"),
        ("HND", "2026-11-23 16:50", "JST"),
        ("LHR", "2026-07-22 12:20", "BST"),
        ("CDG", "2026-11-22 12:20", "CET"),
    ],
)
def test_airport_timezone_uses_airport_and_travel_date(code, when, label):
    result = booking.airport_timezone_fields(code, when, "departure")
    assert result["departure_timezone_abbreviation"] == label


def test_unknown_airport_does_not_invent_timezone():
    assert booking.airport_timezone_fields("???", "2026-11-22 12:20", "departure") == {}
