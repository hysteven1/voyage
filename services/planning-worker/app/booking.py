"""Optional SerpApi Google Flights/Hotels integration. No reservations are made."""

import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import airportsdata
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.booking_links import (
    child_count,
    google_flights_url,
    hotel_room_options,
    stay_search_links,
)
from app.planning import build_plan, money

logger = logging.getLogger("voyage.activities")


class ProviderError(Exception):
    pass


@lru_cache(maxsize=1)
def airport_timezones():
    return {code: data["tz"] for code, data in airportsdata.load("IATA").items()}


def airport_timezone_fields(code, local_time, prefix):
    zone = airport_timezones().get(code)
    if not zone:
        return {}
    try:
        when = datetime.fromisoformat(local_time).replace(tzinfo=ZoneInfo(zone))
    except (ValueError, ZoneInfoNotFoundError):
        return {}
    return {
        f"{prefix}_timezone": zone,
        f"{prefix}_timezone_abbreviation": when.tzname(),
    }


def safe_link(value, google_product=None):
    if not isinstance(value, str):
        return None
    url = urlparse(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or "api_key=" in value.lower()
    ):
        return None
    if url.hostname.endswith("serpapi.com"):
        return None
    if google_product:
        paths = (f"/travel/{google_product}",)
        if google_product == "hotels":
            paths += ("/travel/search",)
        if url.hostname not in {
            "google.com",
            "www.google.com",
        } or not url.path.startswith(paths):
            return None
    return value


def amount(data):
    if not isinstance(data, dict):
        return None
    value = next(
        (
            data[k]
            for k in (
                "extracted_after_taxes_fees",
                "extracted_lowest",
                "extracted_display_price",
            )
            if isinstance(data.get(k), (int, float))
        ),
        None,
    )
    return money(value) if value is not None and value > 0 else None


class SerpApi:
    def __init__(self):
        self.key = os.getenv("SERPAPI_API_KEY")
        self._lock = threading.Lock()
        self._city_lock = threading.Lock()
        self._cities = {}
        self._count = 0

    def query(self, **params):
        with self._lock:
            self._count += 1
            if self._count > 40:
                raise ProviderError("Search allowance reached")
        params.update(api_key=self.key, hl="en", gl="us", currency="USD")
        try:
            with urlopen(
                "https://serpapi.com/search.json?" + urlencode(params),
                timeout=45 if params.get("deep_search") else 25,
            ) as response:
                result = json.load(response)
        except Exception:  # noqa: BLE001 - provider failures must not leak credential-bearing URLs.
            # Never include request URLs or credentials in errors/logs.
            raise ProviderError("Travel search unavailable") from None
        if result.get("error") or result.get("search_metadata", {}).get(
            "status"
        ) not in {None, "Success"}:
            raise ProviderError("Travel provider could not complete this search")
        return result

    def city_id(self, location):
        if re.fullmatch(r"[A-Z]{3}", location.strip()):
            return location.strip()
        with self._city_lock:
            if location in self._cities:
                return self._cities[location]
            # Our city picker includes state names. Google's autocomplete often
            # returns no results for that full label (including Washington DC).
            parts = [p.strip() for p in location.split(",") if p.strip()]
            if re.fullmatch(r"Washington\s+D\.?C\.?", parts[0], re.IGNORECASE):
                parts = ["Washington", "United States"]
            elif (
                parts[0].casefold() == "washington"
                and len(parts) == 2
                and parts[1].replace(".", "").casefold() == "dc"
            ):
                parts[1] = "United States"
            queries = list(
                dict.fromkeys(
                    [
                        ", ".join([parts[0], parts[-1]])
                        if len(parts) > 2
                        else location,
                        parts[0],
                    ]
                )
            )
            city = parts[0].casefold().removesuffix(" city")
            candidates = []
            for query in queries:
                try:
                    result = self.query(
                        engine="google_flights_autocomplete",
                        q=query,
                        exclude_regions="true",
                    )
                except ProviderError:
                    continue
                candidates = [
                    s
                    for s in result.get("suggestions", [])
                    if s.get("type") == "city"
                    and city in s.get("name", "").casefold()
                    and str(s.get("id", "")).startswith(("/m/", "/g/"))
                ]
                if candidates:
                    break
            if not candidates:
                raise ProviderError("Could not resolve the flight location")
            # Country/state tokens help disambiguate places with the same name.
            words = set(re.findall(r"\w+", location.casefold()))
            chosen = max(
                candidates,
                key=lambda s: (
                    s["name"].split(",")[0].casefold().strip() == city,
                    len(words & set(re.findall(r"\w+", s["name"].casefold()))),
                ),
            )
            self._cities[location] = chosen["id"]
            return chosen["id"]

    def flight(self, leg, options):
        prefs = leg.get("restrictions") or options.get("flight_preferences", {})
        origin_id = self.city_id(leg["origin"])
        destination_id = self.city_id(leg["destination"])
        fallback = google_flights_url(leg, options, origin_id, destination_id)
        leg["alternatives_url"] = fallback
        if options["adults"] + child_count(options) > 9:
            return {
                "selection_status": "group_search_only",
                "alternatives_url": fallback,
                "search_travelers": 1,
                "search_note": "Google Flights supports searches for up to 9 travelers. This link shows 1 adult. Contact the airline for availability and a quote for your full group.",
            }
        unknown_child_rates = child_count(options) > 0 and not options.get("child_ages")
        params = {
            "engine": "google_flights",
            "departure_id": origin_id,
            "arrival_id": destination_id,
            "outbound_date": leg["departure_date"],
            "type": 2,
            "adults": options["adults"]
            + (
                child_count(options)
                if unknown_child_rates
                else sum(age >= 12 for age in options["child_ages"])
            ),
            "children": sum(2 <= age < 12 for age in options["child_ages"]),
            "infants_in_seat": sum(age < 2 for age in options["child_ages"]),
            "stops": int(prefs.get("max_stops", 1)) + 1,
            "deep_search": "true",
        }
        if prefs.get("earliest_departure") or prefs.get("latest_arrival"):
            earliest = int((prefs.get("earliest_departure") or "00:00").split(":")[0])
            latest = int((prefs.get("latest_arrival") or "23:59").split(":")[0])
            params["outbound_times"] = f"{earliest},23,0,{latest}"
        result = self.query(**params)
        alternatives = safe_link(
            result.get("search_metadata", {}).get("google_flights_url"), "flights"
        )
        if alternatives and not parse_qs(urlparse(alternatives).query).get("tfs"):
            alternatives = None
        candidates = []
        for option in result.get("best_flights", []) + result.get("other_flights", []):
            segments = option.get("flights", [])
            if (
                not segments
                or len(segments) - 1 > prefs.get("max_stops", 1)
                or not isinstance(option.get("price"), (int, float))
                or option["price"] <= 0
            ):
                continue
            try:
                departure = datetime.fromisoformat(
                    segments[0]["departure_airport"]["time"]
                )
                arrival = datetime.fromisoformat(
                    segments[-1]["arrival_airport"]["time"]
                )
                # Arrival dates in the initial route are estimates. Crossing
                # time zones must not rule out an otherwise matching flight.
                # The caller bounds arrival by the next stay/whole trip window.
                latest = leg.get("latest_arrival_date", leg["arrival_date"])
                if str(departure.date()) != leg["departure_date"] or not (
                    departure.date() <= arrival.date() <= date.fromisoformat(latest)
                ):
                    continue
                if (
                    prefs.get("earliest_departure")
                    and departure.strftime("%H:%M") < prefs["earliest_departure"]
                ):
                    continue
                if (
                    prefs.get("latest_arrival")
                    and arrival.strftime("%H:%M") > prefs["latest_arrival"]
                ):
                    continue
                if not prefs.get("allow_overnight", True):
                    segment_dates = [
                        (
                            datetime.fromisoformat(s["departure_airport"]["time"]),
                            datetime.fromisoformat(s["arrival_airport"]["time"]),
                        )
                        for s in segments
                    ]
                    if (
                        any(
                            a.date() != b.date()
                            or a.hour < 6
                            or b.hour < 6
                            or a.hour >= 22
                            or b.hour >= 23
                            for a, b in segment_dates
                        )
                        or departure.date() != arrival.date()
                    ):
                        continue
                    if any(l.get("overnight") for l in option.get("layovers", [])):
                        continue
                candidates.append(option)
            except (KeyError, ValueError, TypeError):
                continue
        if not candidates:
            return {
                "selection_status": "no_matching_offer",
                "alternatives_url": alternatives or fallback,
            }
        # Respect hard preferences first; trade a little fare for shorter travel at value/upscale tiers.
        weight = {"budget": 0, "value": 0.25, "upscale": 0.6}[
            options.get("spending_style", "value")
        ]
        selected = min(
            candidates, key=lambda c: c["price"] + c.get("total_duration", 0) * weight
        )
        segments = selected["flights"]
        pinned = {
            "outbound": [
                {
                    "flight_number": re.sub(r"\s+", "", s["flight_number"]),
                    "departure_id": s["departure_airport"]["id"],
                    "arrival_id": s["arrival_airport"]["id"],
                    "date": s["departure_airport"]["time"].split(" ")[0].split("T")[0],
                }
                for s in segments
            ]
        }
        pinned_params = {
            k: v
            for k, v in params.items()
            if k
            not in {
                "departure_id",
                "arrival_id",
                "outbound_date",
                "outbound_times",
                "stops",
            }
        }
        try:
            exact = self.query(
                **pinned_params, selected_flights_json=json.dumps(pinned)
            )
            selected_url = safe_link(
                exact.get("search_metadata", {}).get("google_flights_url"), "flights"
            )
        except ProviderError:
            selected_url = None
        # Never label a bare route/search page as a pinned flight link.
        if selected_url and not any(
            k in urlparse(selected_url).query for k in ("tfs=", "flt=")
        ):
            selected_url = None
        return {
            "selection_status": "selected",
            "alternatives_url": alternatives or fallback,
            "selected_flight": {
                "airlines": list(dict.fromkeys(s.get("airline", "") for s in segments)),
                "flight_numbers": [s["flight_number"] for s in segments],
                "departure_airport": segments[0]["departure_airport"]["id"],
                "arrival_airport": segments[-1]["arrival_airport"]["id"],
                "departure_time": segments[0]["departure_airport"]["time"],
                "arrival_time": segments[-1]["arrival_airport"]["time"],
                **airport_timezone_fields(
                    segments[0]["departure_airport"]["id"],
                    segments[0]["departure_airport"]["time"],
                    "departure",
                ),
                **airport_timezone_fields(
                    segments[-1]["arrival_airport"]["id"],
                    segments[-1]["arrival_airport"]["time"],
                    "arrival",
                ),
                "stops": len(segments) - 1,
                "duration_minutes": selected.get("total_duration"),
                "price": str(money(selected["price"])),
                "price_basis": "adult_fare_estimate"
                if unknown_child_rates
                else "requested_party",
                "price_note": "Uses adult fares for all travelers; child fares may differ when booking."
                if unknown_child_rates
                else "",
                "google_flights_url": selected_url,
                "checked_at": datetime.now(UTC).isoformat(),
                "source": "SerpApi / Google Flights",
            },
        }

    def stay(self, stay, options):
        search_options = (
            hotel_room_options(options)
            if options["lodging"] != "apartment"
            else options
        )
        params = {
            "engine": "google_hotels",
            # AI area descriptions contain prose, not search terms. Keep the
            # location query stable regardless of the number of destinations.
            "q": f"{stay['location']} hotels"
            if options["lodging"] != "apartment"
            else f"{stay['location']} vacation rentals",
            "check_in_date": stay["check_in"],
            "check_out_date": stay["check_out"],
            "adults": search_options["adults"],
            "children": len(search_options["child_ages"]),
            "rating": 8,
        }
        if search_options["child_ages"]:
            params["children_ages"] = ",".join(
                str(max(1, age)) for age in search_options["child_ages"]
            )
        if options["lodging"] == "apartment":
            params.update(vacation_rentals="true", bedrooms=options["rooms"])
        result = self.query(**params)
        candidates = []
        for prop in result.get("properties", []):
            price = amount(prop.get("total_rate"))
            if (
                price is None
                or prop.get("overall_rating", 0) < 4
                or prop.get("reviews", 0) < 30
                or not prop.get("property_token")
            ):
                continue
            if prop.get("location_rating") is not None and prop["location_rating"] < 4:
                continue
            if options["lodging"] == "hotel" and prop.get("type") != "hotel":
                continue
            if options["lodging"] == "apartment":
                capacity = re.search(
                    r"Sleeps\s+(\d+)",
                    " ".join(prop.get("essential_info", [])),
                    re.IGNORECASE,
                )
                if not capacity or int(capacity[1]) < options["adults"] + len(
                    options["child_ages"]
                ):
                    continue
            # Prefer the combination of reviews, location, and value over lowest price alone.
            score = float(price) / (
                prop["overall_rating"] ** 2 * max(1, prop.get("location_rating", 4))
            )
            candidates.append((score, prop))
        updates = stay_search_links(stay, options)
        if not candidates:
            return {**updates, "selection_status": "no_matching_offer"}
        _, selected = min(candidates, key=lambda item: item[0])
        try:
            details = self.query(**params, property_token=selected["property_token"])
        except ProviderError:
            # The search already supplied a real property and stay quote.
            # A failed price-source expansion must not erase that recommendation.
            details = selected
        if (
            details.get("property_token", selected["property_token"])
            != selected["property_token"]
        ):
            raise ProviderError("Property detail mismatch")
        prices = [
            p
            for p in details.get("prices", [])
            if safe_link(p.get("link")) and amount(p.get("total_rate")) is not None
        ]
        quoted_price = (
            min(prices, key=lambda p: amount(p["total_rate"])) if prices else None
        )
        booking_url = (
            quoted_price["link"]
            if quoted_price
            else safe_link(details.get("link")) or safe_link(selected.get("link"))
        )
        return {
            **updates,
            "selection_status": "selected",
            "selected_stay": {
                "name": selected["name"],
                "type": selected.get("type", "hotel"),
                "rating": selected["overall_rating"],
                "reviews": selected["reviews"],
                "location_rating": selected.get("location_rating"),
                "quoted_total": str(
                    amount(quoted_price["total_rate"])
                    if quoted_price
                    else amount(details.get("total_rate"))
                    or amount(selected["total_rate"])
                ),
                "booking_url": booking_url,
                "rooms_requested": options["rooms"],
                "quoted_guests": search_options["adults"]
                + len(search_options["child_ages"]),
                "price_basis": "per_room_stay"
                if options["lodging"] != "apartment"
                else "provider_search_stay",
                "capacity_note": f"Plan for {options['rooms']} room(s) at this property. Confirm that all rooms are available for your dates, and check guest capacity, child rates and final fees with the hotel before booking.",
                "checked_at": datetime.now(UTC).isoformat(),
                "source": "SerpApi / Google Hotels",
            },
        }


def refresh_estimates(plan):
    budget = plan["budget"]
    budget["transport"] = str(
        sum((money(leg["estimated_cost"]) for leg in plan["legs"]), Decimal(0))
    )
    budget["lodging"] = str(
        sum((money(stay["estimated_cost"]) for stay in plan["stays"]), Decimal(0))
    )
    for item in plan.get("destination_estimates", []):
        stay = next(s for s in plan["stays"] if s["location"] == item["location"])
        item["lodging"] = stay["estimated_cost"]
        item["subtotal"] = str(
            money(item["lodging"]) + money(item["food"]) + money(item["activities"])
        )
    subtotal = sum(
        money(budget[k]) for k in ("transport", "lodging", "food", "activities", "car")
    )
    contingency = money(subtotal * Decimal("0.15"))
    total = subtotal + contingency
    people = max(1, int(plan.get("travelers", 1)))
    target = money(budget["target"]) if budget.get("target") is not None else None
    ceiling = money(budget["limit"]) if budget.get("limit") is not None else None
    if ceiling is not None and total > ceiling:
        raise ApplicationError(
            f"Selected travel quotes bring the estimate to ${total}, above your ${ceiling} ceiling. Adjust the dates, stays, or budget.",
            non_retryable=True,
        )
    budget.update(
        total=str(total),
        contingency=str(contingency),
        per_person_total=str(money(total / people)),
        remaining=str((ceiling if ceiling is not None else target) - total)
        if target is not None
        else None,
        above_target=str(max(Decimal(0), total - target))
        if target is not None
        else None,
        per_person_above_target=str(money(max(Decimal(0), total - target) / people))
        if target is not None
        else None,
    )
    plan["data_source"] = "quotes_and_estimates"


@activity.defn
def select_travel_options(data):
    plan, trip = deepcopy(data["plan"]), data["trip"]
    for leg in plan["legs"]:
        if leg["mode"] == "flight":
            leg["search_url"] = "https://www.google.com/travel/flights"
            if trip["options"]["adults"] + child_count(trip["options"]) > 9:
                leg.update(
                    selection_status="group_search_only",
                    search_travelers=1,
                    search_note="Google Flights supports searches for up to 9 travelers. Search for 1 adult to explore routes, then contact the airline for your full group.",
                )
    for stay in plan["stays"]:
        stay.update(stay_search_links(stay, trip["options"]))
    provider = SerpApi()
    if not provider.key:
        plan["booking_source"] = "not_configured"
        return plan
    # Resolve flights first: real arrival dates determine hotel check-in dates.
    flight_tasks = []
    for i, leg in enumerate(plan["legs"]):
        if leg["mode"] != "flight":
            continue
        stay = next(
            (s for s in plan["stays"] if s["location"] == leg.get("destination")), None
        )
        search = {**leg}
        if stay:
            search["latest_arrival_date"] = str(
                date.fromisoformat(stay["check_out"]) - timedelta(days=1)
            )
        elif trip.get("end_date"):
            search["latest_arrival_date"] = trip["end_date"]
        flight_tasks.append(("flight", i, search))

    def select(task):
        kind, index, item = task
        try:
            update = (
                provider.flight(item, trip["options"])
                if kind == "flight"
                else provider.stay(item, trip["options"])
            )
            return kind, index, update
        except Exception as exc:  # noqa: BLE001 - provider failures must not leak credential-bearing URLs.
            logger.warning(
                "Travel search unavailable for %s (%s)",
                kind,
                type(exc).__name__,
                extra={"trip_id": trip["id"]},
            )
            return (
                kind,
                index,
                {
                    "selection_status": "unavailable",
                    **(
                        {"alternatives_url": item["alternatives_url"]}
                        if item.get("alternatives_url")
                        else {}
                    ),
                },
            )

    with ThreadPoolExecutor(max_workers=4) as executor:
        flights = list(executor.map(select, flight_tasks))
        adjusted_trip = deepcopy(trip)
        changed = False
        for _, index, update in flights:
            selected = update.get("selected_flight", {})
            if not selected.get("arrival_time"):
                continue
            leg = plan["legs"][index]
            arrival = datetime.fromisoformat(selected["arrival_time"]).date()
            for stop, stay in zip(
                adjusted_trip["options"].get("route", []), plan["stays"], strict=False
            ):
                if stay["location"] != leg.get("destination"):
                    continue
                if str(arrival) != stay["check_in"]:
                    stop["travel_days"] = (
                        arrival - date.fromisoformat(leg["departure_date"])
                    ).days
                    stop["nights"] = (
                        date.fromisoformat(stay["check_out"]) - arrival
                    ).days
                    changed = True
        if changed:
            # Rebuild with the original AI ideas so budget, easy arrival day,
            # transit days and all booking dates stay in sync with real flights.
            plan = build_plan(adjusted_trip, data.get("suggestions"))
            plan["assumptions"].append(
                "Hotel check-in and daily plans use the selected flights' local arrival dates."
            )
        for _, index, update in flights:
            leg = plan["legs"][index]
            leg.update(update)
            selected = update.get("selected_flight")
            if selected:
                leg["estimated_cost"] = selected["price"]
                if selected.get("duration_minutes"):
                    leg["estimated_hours"] = round(selected["duration_minutes"] / 60, 1)
                if selected.get("arrival_time"):
                    leg["arrival_date"] = str(
                        datetime.fromisoformat(selected["arrival_time"]).date()
                    )
        for stay in plan["stays"]:
            stay.update(stay_search_links(stay, trip["options"]))
        stays = [("stay", i, stay) for i, stay in enumerate(plan["stays"])]
        for _, index, update in executor.map(select, stays):
            plan["stays"][index].update(update)
            if update.get("selected_stay"):
                rooms = (
                    1
                    if trip["options"]["lodging"] == "apartment"
                    else trip["options"]["rooms"]
                )
                total = str(money(update["selected_stay"]["quoted_total"]) * rooms)
                update["selected_stay"]["estimated_group_total"] = total
                plan["stays"][index]["estimated_cost"] = total
    if any(leg.get("selected_flight") for leg in plan["legs"]) or any(
        stay.get("selected_stay") for stay in plan["stays"]
    ):
        refresh_estimates(plan)
    plan["booking_source"] = "serpapi"
    plan["assumptions"].append(
        "Travel searches use city airport groups unless an airport code is entered. Selected travel quotes can change; confirm group, room and luggage fees on the booking page."
    )
    return plan
