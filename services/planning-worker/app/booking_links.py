"""Google Hotels search state: dates, guests, property type and rating.

The ts wire fields follow SerpApi's documented Google Hotels protobuf analysis:
https://serpapi.com/blog/decoding-protobuf-messages-without-schema/
"""

from base64 import urlsafe_b64encode
from datetime import date
from math import ceil
from urllib.parse import urlencode


def child_count(options):
    count = options.get("children")
    return count if count is not None else len(options.get("child_ages", []))


def hotel_room_options(options):
    """Search one representative room, rather than fitting the entire party in it."""
    people = options["adults"] + child_count(options)
    return {
        **options,
        "adults": min(4, max(1, ceil(people / options["rooms"]))),
        "children": 0,
        "child_ages": [],
        "rooms": 1,
    }


def stay_search_links(stay, options):
    return {
        "alternatives_url": google_hotels_url(stay, options),
        "rental_alternatives_url": "https://www.airbnb.com/s/homes?"
        + urlencode(
            {
                "query": stay["location"],
                "checkin": stay["check_in"],
                "checkout": stay["check_out"],
                "adults": options["adults"],
                "children": child_count(options),
                "room_types[]": "Entire home/apt",
            }
        ),
    }


def google_flights_url(leg, options, origin_id=None, destination_id=None):
    """One-way Google Flights state; wire fields documented by fast-flights.

    https://github.com/AWeirdDev/flights/blob/dev/fast_flights/pb/flights.proto
    """
    if not origin_id or not destination_id:
        return "https://www.google.com/travel/flights"
    prefs = leg.get("restrictions") or {}
    flight = (
        field(2, leg["departure_date"].encode())
        + field(13, field(2, origin_id.encode()))
        + field(14, field(2, destination_id.encode()))
        + field(5, prefs.get("max_stops", 1))
    )
    if prefs.get("earliest_departure"):
        flight += field(8, int(prefs["earliest_departure"].split(":")[0]))
    if prefs.get("latest_arrival"):
        flight += field(11, int(prefs["latest_arrival"].split(":")[0]))
    count = options["adults"] + child_count(options)
    if count > 9:
        passengers = [1]
    elif options.get("child_ages"):
        passengers = [1] * options["adults"] + [
            3 if age < 2 else 2 if age < 12 else 1 for age in options["child_ages"]
        ]
    else:
        passengers = [1] * count
    state = (
        field(3, flight)
        + b"".join(field(8, passenger) for passenger in passengers)
        + field(9, 1)
        + field(19, 2)
    )
    return "https://www.google.com/travel/flights/search?" + urlencode(
        {
            "tfs": urlsafe_b64encode(state).decode().rstrip("="),
            "hl": "en",
            "curr": "USD",
        }
    )


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def field(number, value):
    if isinstance(value, int):
        return varint(number << 3) + varint(value)
    return varint((number << 3) | 2) + varint(len(value)) + value


def google_hotels_url(stay, options):
    if options["lodging"] != "apartment":
        options = hotel_room_options(options)

    def calendar(value):
        day = date.fromisoformat(value)
        return field(1, day.year) + field(2, day.month) + field(3, day.day)

    guests = field(1, field(1, 3)) * options["adults"]
    guests += b"".join(
        field(1, field(1, 2) + field(2, age)) for age in options["child_ages"]
    ) + field(2, 1)
    dates = field(1, calendar(stay["check_in"])) + field(2, calendar(stay["check_out"]))
    dates += field(
        3,
        (
            date.fromisoformat(stay["check_out"]) - date.fromisoformat(stay["check_in"])
        ).days,
    )
    search = field(1, field(3, b"")) + field(2, field(2, dates) + field(6, field(1, 1)))
    filters = field(1, field(7, b"USD")) + field(5, 8)
    rental = options["lodging"] == "apartment"
    if rental:
        filters += field(3, field(2, options["rooms"]))
    state = (
        field(1, 2 if rental else 1)
        + field(2, guests)
        + field(3, search)
        + field(5, filters)
    )
    return "https://www.google.com/travel/search?" + urlencode(
        {
            "q": f"{stay['location']} {'vacation rentals' if rental else 'hotels'}",
            "ts": urlsafe_b64encode(state).decode().rstrip("="),
            "hl": "en",
            "gl": "us",
        }
    )
