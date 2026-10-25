"""Optional SerpApi Google Flights/Hotels integration. No reservations are made."""

import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import quote, urlencode, urlparse
from urllib.request import urlopen

from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.planning import money

logger = logging.getLogger("voyage.activities")


class ProviderError(Exception):
    pass


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
                "https://serpapi.com/search.json?" + urlencode(params), timeout=25
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
            result = self.query(
                engine="google_flights_autocomplete", q=location, exclude_regions="true"
            )
            city = location.split(",")[0].casefold().replace(" city", "").strip()
            candidates = [
                s
                for s in result.get("suggestions", [])
                if s.get("type") == "city"
                and city in s.get("name", "").casefold()
                and str(s.get("id", "")).startswith(("/m/", "/g/"))
            ]
            if not candidates:
                raise ProviderError("Could not resolve the flight location")
            # Country/state tokens help disambiguate places with the same name.
            words = set(re.findall(r"\w+", location.casefold()))
            chosen = max(
                candidates,
                key=lambda s: len(
                    words & set(re.findall(r"\w+", s["name"].casefold()))
                ),
            )
            self._cities[location] = chosen["id"]
            return chosen["id"]

    def flight(self, leg, options):
        prefs = leg.get("restrictions") or options.get("flight_preferences", {})
        params = {
            "engine": "google_flights",
            "departure_id": self.city_id(leg["origin"]),
            "arrival_id": self.city_id(leg["destination"]),
            "outbound_date": leg["departure_date"],
            "type": 2,
            "adults": options["adults"],
            "children": sum(age >= 2 for age in options["child_ages"]),
            "infants_in_seat": sum(age < 2 for age in options["child_ages"]),
            "stops": int(prefs.get("max_stops", 1)) + 1,
        }
        if prefs.get("earliest_departure") or prefs.get("latest_arrival"):
            earliest = int((prefs.get("earliest_departure") or "00:00").split(":")[0])
            latest = int((prefs.get("latest_arrival") or "23:59").split(":")[0])
            params["outbound_times"] = f"{earliest},23,0,{latest}"
        result = self.query(**params)
        alternatives = safe_link(
            result.get("search_metadata", {}).get("google_flights_url"), "flights"
        )
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
                if (
                    str(departure.date()) != leg["departure_date"]
                    or str(arrival.date()) != leg["arrival_date"]
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
                "alternatives_url": alternatives or leg["search_url"],
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
            "alternatives_url": alternatives or leg["search_url"],
            "selected_flight": {
                "airlines": list(dict.fromkeys(s.get("airline", "") for s in segments)),
                "flight_numbers": [s["flight_number"] for s in segments],
                "departure_airport": segments[0]["departure_airport"]["id"],
                "arrival_airport": segments[-1]["arrival_airport"]["id"],
                "departure_time": segments[0]["departure_airport"]["time"],
                "arrival_time": segments[-1]["arrival_airport"]["time"],
                "stops": len(segments) - 1,
                "duration_minutes": selected.get("total_duration"),
                "price": str(money(selected["price"])),
                "price_basis": "requested_party",
                "google_flights_url": selected_url,
                "checked_at": datetime.now(UTC).isoformat(),
                "source": "SerpApi / Google Flights",
            },
        }

    def stay(self, stay, options):
        params = {
            "engine": "google_hotels",
            "q": f"{stay['area']} {stay['location']}",
            "check_in_date": stay["check_in"],
            "check_out_date": stay["check_out"],
            "adults": options["adults"],
            "children": len(options["child_ages"]),
            "rating": 8,
        }
        if options["child_ages"]:
            params["children_ages"] = ",".join(
                str(max(1, age)) for age in options["child_ages"]
            )
        if options["lodging"] == "apartment":
            params.update(vacation_rentals="true", bedrooms=options["rooms"])
        result = self.query(**params)
        alternatives = safe_link(
            result.get("search_metadata", {}).get("google_hotels_url"), "hotels"
        )
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
        airbnb = (
            "https://www.airbnb.com/s/"
            + quote(stay["location"], safe="")
            + "/homes?"
            + urlencode(
                {
                    "checkin": stay["check_in"],
                    "checkout": stay["check_out"],
                    "adults": options["adults"],
                    "children": sum(age >= 2 for age in options["child_ages"]),
                    "infants": sum(age < 2 for age in options["child_ages"]),
                    "min_bedrooms": options["rooms"],
                }
            )
        )
        updates = {
            "alternatives_url": alternatives
            or "https://www.google.com/travel/hotels?"
            + urlencode(
                {
                    "q": f"{stay['location']} hotels {stay['check_in']} to {stay['check_out']} {options['adults']} adults {len(options['child_ages'])} children 4+ guest rating"
                }
            ),
            "rental_alternatives_url": airbnb,
        }
        if not candidates:
            return {**updates, "selection_status": "no_matching_offer"}
        _, selected = min(candidates, key=lambda item: item[0])
        details = self.query(**params, property_token=selected["property_token"])
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
                "price_basis": "provider_search_stay",
                "capacity_note": "Confirm room quantity, guest capacity, accessibility and final fees before booking.",
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
    provider = SerpApi()
    if not provider.key:
        plan["booking_source"] = "not_configured"
        return plan
    tasks = [
        ("flight", i, leg)
        for i, leg in enumerate(plan["legs"])
        if leg["mode"] == "flight"
    ] + [("stay", i, stay) for i, stay in enumerate(plan["stays"])]

    def select(task):
        kind, index, item = task
        try:
            update = (
                provider.flight(item, trip["options"])
                if kind == "flight"
                else provider.stay(item, trip["options"])
            )
            return kind, index, update
        except Exception:  # noqa: BLE001 - provider failures must not leak credential-bearing URLs.
            logger.warning(
                "Travel search unavailable for one leg or stay",
                extra={"trip_id": trip["id"]},
            )
            return kind, index, {"selection_status": "unavailable"}

    with ThreadPoolExecutor(max_workers=4) as executor:
        for kind, index, update in executor.map(select, tasks):
            collection = plan["legs"] if kind == "flight" else plan["stays"]
            collection[index].update(update)
            if update.get("selected_flight"):
                collection[index]["estimated_cost"] = update["selected_flight"]["price"]
                if update["selected_flight"].get("duration_minutes"):
                    collection[index]["estimated_hours"] = round(
                        update["selected_flight"]["duration_minutes"] / 60, 1
                    )
            if update.get("selected_stay") and (
                trip["options"]["rooms"] == 1
                or trip["options"]["lodging"] == "apartment"
            ):
                collection[index]["estimated_cost"] = update["selected_stay"][
                    "quoted_total"
                ]
    if any(leg.get("selected_flight") for leg in plan["legs"]) or any(
        stay.get("selected_stay") for stay in plan["stays"]
    ):
        refresh_estimates(plan)
    plan["booking_source"] = "serpapi"
    plan["assumptions"].append(
        "Selected travel options were retrieved from SerpApi. Prices and availability can change; group, room and luggage fees must be confirmed on the booking page."
    )
    return plan
