from base64 import urlsafe_b64decode
from urllib.parse import parse_qs, urlparse

from app.booking_links import google_hotels_url


def decode(data):
    """Minimal independent protobuf reader for the documented search contract."""
    cursor, fields = 0, {}

    def read_int():
        nonlocal cursor
        value, shift = 0, 0
        while True:
            byte = data[cursor]
            cursor += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7

    while cursor < len(data):
        tag = read_int()
        if tag & 7 == 2:
            size = read_int()
            value = data[cursor : cursor + size]
            cursor += size
        else:
            value = read_int()
        fields.setdefault(tag >> 3, []).append(value)
    return fields


def test_hotel_link_encodes_dates_party_and_rating():
    url = google_hotels_url(
        {
            "location": "Kyoto, Japan",
            "check_in": "2026-12-30",
            "check_out": "2027-01-04",
        },
        {"adults": 2, "child_ages": [7], "lodging": "hotel", "rooms": 1},
    )
    query = parse_qs(urlparse(url).query)
    assert urlparse(url).path == "/travel/search"
    assert query["q"] == ["Kyoto, Japan hotels"]
    state = decode(urlsafe_b64decode(query["ts"][0] + "=="))
    guests = decode(state[2][0])[1]
    assert [decode(guest)[1][0] for guest in guests] == [3, 3, 3]
    dates = decode(decode(decode(state[3][0])[2][0])[2][0])
    assert decode(dates[1][0]) == {1: [2026], 2: [12], 3: [30]}
    assert decode(dates[2][0]) == {1: [2027], 2: [1], 3: [4]}
    assert dates[3] == [5]
    assert decode(state[5][0])[5] == [8]
