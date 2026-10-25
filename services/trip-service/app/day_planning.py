"""Day clusters, realistic visit allowances, and an offline Tokyo reference itinerary.

Durations are planning estimates, not opening hours or reservations. Reference
sources: Tokyo Disney Resort, Sunshine City, JNTO, and Hakone tourism (README).
Keep the worker copy identical.
"""

import re
from copy import deepcopy


def place(name, minutes, price=0, category="culture", area="", travel=15, url=None):
    return {
        "name": name,
        "duration_minutes": minutes,
        "estimated_price": price,
        "category": category,
        "area": area,
        "travel_minutes": travel,
        "source_url": url,
    }


def cluster(area, activities, full_day=False, travel_minutes=0):
    return {
        "title": area,
        "area": area,
        "activities": activities,
        "full_day": full_day,
        "travel_minutes": travel_minutes,
        "rain": f"Choose an indoor museum or exhibition around {area}",
    }


def tokyo_days():
    return [
        cluster(
            "Shibuya & Harajuku",
            [
                place("Hachiko statue", 5, area="Shibuya", travel=0),
                place("Shibuya Scramble Crossing", 15, area="Shibuya", travel=5),
                place(
                    "Shibuya Sky observation deck", 90, 25, area="Shibuya", travel=10
                ),
                place("Meiji Jingu shrine grounds", 75, area="Harajuku", travel=25),
                place(
                    "Harajuku and Cat Street shops",
                    75,
                    category="shopping",
                    area="Harajuku",
                    travel=15,
                ),
                place("Yoyogi Park", 45, category="nature", area="Harajuku", travel=15),
            ],
        ),
        cluster(
            "Shinjuku",
            [
                place(
                    "Shinjuku Gyoen National Garden",
                    120,
                    5,
                    "nature",
                    "Shinjuku",
                    15,
                    "https://fng.or.jp/shinjuku/en/",
                ),
                place(
                    "Tokyo Metropolitan Government observation deck",
                    60,
                    area="Shinjuku",
                    travel=25,
                ),
                place(
                    "Shinjuku department stores and streets",
                    90,
                    category="shopping",
                    area="Shinjuku",
                    travel=15,
                ),
                place("Hanazono Shrine", 30, area="Shinjuku", travel=15),
                place(
                    "Shinjuku evening lights and photography",
                    45,
                    area="Shinjuku",
                    travel=10,
                ),
            ],
        ),
        cluster(
            "Odaiba & Toyosu",
            [
                place(
                    "Odaiba waterfront and Rainbow Bridge views",
                    60,
                    category="nature",
                    area="Odaiba",
                    travel=30,
                ),
                place("Miraikan science museum", 120, 8, "museum", "Odaiba", 20),
                place(
                    "DiverCity and the life-size Gundam",
                    60,
                    category="shopping",
                    area="Odaiba",
                    travel=15,
                ),
                place("teamLab Planets", 120, 35, "culture", "Toyosu", 30),
            ],
        ),
        cluster(
            "Ikebukuro & Sunshine City",
            [
                place(
                    "Sunshine Aquarium",
                    90,
                    20,
                    "nature",
                    "Ikebukuro",
                    20,
                    "https://sunshinecity.jp/en/aquarium/",
                ),
                place(
                    "Sunshine 60 Observatory Tenbou-Park",
                    60,
                    10,
                    "culture",
                    "Ikebukuro",
                    10,
                    "https://sunshinecity.jp/en/observatory/",
                ),
                place("NAMJATOWN attractions", 120, 15, "adventure", "Ikebukuro", 10),
                place(
                    "Sunshine City shops and Ikebukuro streets",
                    75,
                    category="shopping",
                    area="Ikebukuro",
                    travel=10,
                ),
            ],
        ),
        cluster(
            "Hakone day trip",
            [
                place(
                    "Hakone Open-Air Museum",
                    120,
                    20,
                    "museum",
                    "Hakone",
                    0,
                    "https://www.hakone-oam.or.jp/en/",
                ),
                place("Lake Ashi scenery", 90, 15, "nature", "Hakone", 45),
                place("Hakone Shrine", 45, 0, "culture", "Hakone", 20),
            ],
            full_day=True,
            travel_minutes=210,
        ),
        cluster(
            "Tokyo Disney Resort · Maihama",
            [
                place(
                    "Tokyo Disneyland OR DisneySea — choose one park",
                    480,
                    90,
                    "theme_park",
                    "Maihama",
                    0,
                    "https://www.tokyodisneyresort.jp/en/",
                )
            ],
            full_day=True,
            travel_minutes=120,
        ),
        cluster(
            "Asakusa & Ueno",
            [
                place("Senso-ji temple", 60, area="Asakusa", travel=20),
                place(
                    "Nakamise shopping street",
                    45,
                    category="shopping",
                    area="Asakusa",
                    travel=5,
                ),
                place(
                    "Sumida Park riverside",
                    45,
                    category="nature",
                    area="Asakusa",
                    travel=10,
                ),
                place("Ueno Park", 60, category="nature", area="Ueno", travel=25),
                place("Tokyo National Museum", 120, 10, "museum", "Ueno", 10),
            ],
        ),
        cluster(
            "Akihabara & central Tokyo",
            [
                place(
                    "Akihabara electronics and hobby shops",
                    150,
                    category="shopping",
                    area="Akihabara",
                    travel=20,
                ),
                place("Kanda Myojin shrine", 45, area="Kanda", travel=15),
                place(
                    "Tokyo Station architecture and Marunouchi",
                    60,
                    area="Marunouchi",
                    travel=25,
                ),
                place(
                    "Imperial Palace East Gardens",
                    90,
                    category="nature",
                    area="Marunouchi",
                    travel=15,
                ),
            ],
        ),
    ]


def is_food(item):
    return item.get("category", "").lower() in {"food", "restaurant", "dining"} or bool(
        re.search(
            r"\b(restaurant|café|cafe|ramen|sushi|meal|lunch|dinner|breakfast|food tour)\b",
            item.get("name", ""),
            re.IGNORECASE,
        )
    )


def visit_minutes(item):
    name = item.get("name", "").casefold()
    if "hachiko" in name or "hachikō" in name:
        return 5
    if "scramble crossing" in name or "shibuya crossing" in name:
        return 15
    return max(5, min(600, int(item.get("duration_minutes", 60))))


def daily_plans(location, nights, pace, arrival, advice=None, notes=""):
    advice = advice or {}
    city = location.split(",")[0].strip().casefold()
    ideas = deepcopy(advice.get("days") or (tokyo_days() if city == "tokyo" else []))
    if not ideas and advice.get("activities"):
        # Older in-flight activity histories remain readable; never cycle their attractions.
        ideas = [cluster(advice.get("area", location), advice["activities"])]
    if not ideas:
        themes = [
            "Historic center",
            "Art and museums",
            "Parks and gardens",
            "Architecture and viewpoints",
            "Local crafts and shopping",
            "Waterfront or scenic surroundings",
            "Cultural exhibitions",
            "Nearby excursion",
        ]
        for theme in themes:
            ideas.append(
                cluster(
                    f"{location}: {theme}",
                    [
                        place(
                            f"{theme} — explore {topic} in {location}",
                            60,
                            10,
                            area=location,
                        )
                        for topic in [
                            "main sights",
                            "local collections",
                            "public spaces",
                            "independent venues",
                            "a viewpoint",
                            "a second exhibition",
                            "local streets",
                        ]
                    ],
                )
            )
    if city == "tokyo" and not advice.get("days"):
        # Explicit notes can prioritize a full-day experience without piling it onto other sightseeing.
        ideas.sort(
            key=lambda d: (
                not any(
                    word in notes.casefold() and word in d["title"].casefold()
                    for word in ["disney", "hakone", "sunshine"]
                )
            )
        )
    seen = set()
    result = []
    if arrival:
        result.append(
            {
                "title": "Settle in near your stay",
                "area": advice.get("area") or location,
                "activities": [
                    place(
                        "Check in and explore the immediate neighborhood",
                        45,
                        area=advice.get("area") or location,
                        travel=0,
                    )
                ],
                "travel_minutes": 0,
                "rain": "Rest or visit an indoor exhibition near your stay",
                "kind": "arrival",
            }
        )
    target = {"relaxed": 180, "balanced": 360, "busy": 480}[pace]
    cap = {"relaxed": 300, "balanced": 540, "busy": 660}[pace]
    for idea in ideas:
        if len(result) >= nights:
            break
        activities = []
        elapsed = int(idea.get("travel_minutes", 0))
        maximum = max(cap, 660) if idea.get("full_day") else cap
        for raw in idea.get("activities", []):
            item = deepcopy(raw)
            name = re.sub(r"\W+", " ", item.get("name", "").casefold()).strip()
            if not name or name in seen or is_food(item):
                continue
            duration = visit_minutes(item)
            travel = max(0, min(180, int(item.get("travel_minutes", 15))))
            if elapsed + duration + travel > maximum:
                continue
            item.update(
                duration_minutes=duration,
                travel_minutes=travel,
                area=item.get("area") or idea.get("area", location),
            )
            activities.append(item)
            seen.add(name)
            elapsed += duration + travel
            if elapsed >= target:
                break
        if activities:
            result.append(
                {
                    **idea,
                    "activities": activities,
                    "kind": "full",
                    "estimated_minutes": elapsed,
                }
            )
    while len(result) < nights:
        # No recycled attractions or fictional place names when suggestions run out.
        result.append(
            {
                "title": "Flexible exploration",
                "area": location,
                "kind": "full",
                "activities": [
                    place(
                        f"Choose an additional local experience in {location} (day {len(result) + 1})",
                        180,
                        area=location,
                        travel=0,
                    )
                ],
                "travel_minutes": 0,
                "rain": "Choose an indoor exhibition; verify current listings",
                "unfilled": True,
            }
        )
    return result
