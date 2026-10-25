"""Google Hotels search state: dates, guests, property type and rating.

The ts wire fields follow SerpApi's documented Google Hotels protobuf analysis:
https://serpapi.com/blog/decoding-protobuf-messages-without-schema/
"""

from base64 import urlsafe_b64encode
from datetime import date
from math import ceil
from urllib.parse import quote, urlencode


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
        "rental_alternatives_url": "https://www.airbnb.com/s/"
        + quote(stay["location"], safe="")
        + "/homes?"
        + urlencode(
            {
                "checkin": stay["check_in"],
                "checkout": stay["check_out"],
                "adults": options["adults"],
                "children": child_count(options),
                "room_types[]": "Entire home/apt",
            }
        ),
    }


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
