from app.day_planning import daily_plans, tokyo_days


def test_tokyo_week_has_variety_realistic_stops_and_full_day_excursions():
    days = daily_plans(
        "Tokyo, Japan",
        7,
        "balanced",
        arrival=True,
        advice={"days": tokyo_days(), "reference_plan": True},
    )
    assert days[0]["kind"] == "arrival"
    assert sum(a["duration_minutes"] for a in days[0]["activities"]) == 45
    full_days = days[1:]
    assert len({d["area"] for d in full_days}) == 6
    names = [a["name"] for d in days for a in d["activities"]]
    assert len(names) == len(set(names))
    hachiko = next(a for d in days for a in d["activities"] if "Hachiko" in a["name"])
    assert hachiko["duration_minutes"] == 5
    shibuya = next(d for d in days if d["area"] == "Shibuya & Harajuku")
    assert len(shibuya["activities"]) >= 5
    disney = next(d for d in days if "Disney" in d["area"])
    assert len(disney["activities"]) == 1
    assert disney["activities"][0]["duration_minutes"] == 480
    assert disney["travel_minutes"] == 120
    hakone = next(d for d in days if "Hakone" in d["area"])
    assert hakone["travel_minutes"] == 210
    assert hakone["estimated_minutes"] >= 450
    assert all(d["estimated_minutes"] <= 660 for d in full_days)


def test_already_there_uses_first_day_and_long_trips_never_recycle_sights():
    days = daily_plans(
        "Tokyo, Japan", 12, "balanced", arrival=False, advice={"days": tokyo_days()}
    )
    assert days[0]["kind"] == "full"
    names = [a["name"] for d in days for a in d["activities"]]
    assert len(names) == len(set(names))
    assert days[-1]["unfilled"]


def test_ai_photo_stop_is_short_and_food_suggestions_are_removed():
    advice = {
        "days": [
            {
                "title": "Shibuya",
                "area": "Shibuya",
                "activities": [
                    {"name": "Hachiko statue", "duration_minutes": 120},
                    {"name": "Shibuya Scramble Crossing", "duration_minutes": 120},
                    {
                        "name": "Ramen restaurant",
                        "category": "food",
                        "duration_minutes": 60,
                    },
                    {
                        "name": "Local art museum",
                        "category": "culture",
                        "duration_minutes": 120,
                    },
                ],
            }
        ]
    }
    days = daily_plans("Tokyo, Japan", 1, "balanced", arrival=False, advice=advice)
    assert [a["duration_minutes"] for a in days[0]["activities"]] == [5, 15, 120]
    assert all("restaurant" not in a["name"] for a in days[0]["activities"])


def test_pace_changes_sightseeing_time_and_explicit_notes_prioritize_day_trip():
    durations = [
        daily_plans(
            "Tokyo, Japan", 1, pace, arrival=False, advice={"days": tokyo_days()}
        )[0]["estimated_minutes"]
        for pace in ("relaxed", "balanced", "busy")
    ]
    assert durations[0] < durations[1] <= durations[2]
    packed = daily_plans(
        "Tokyo, Japan", 1, "busy", arrival=False, advice={"days": tokyo_days()}
    )[0]
    assert packed["estimated_minutes"] >= 540
    assert len(packed["activities"]) >= 7
    days = daily_plans(
        "Tokyo, Japan",
        5,
        "balanced",
        arrival=True,
        notes="Please include Hakone",
        advice={"days": tokyo_days(), "reference_plan": True},
    )
    assert days[1]["area"] == "Hakone day trip"


def test_short_stays_prioritize_city_sights_in_every_destination():
    for city in ["Paris, France", "Lisbon, Portugal", "Rome, Italy"]:
        advice = {
            "days": [
                {
                    "title": "Nearby day trip",
                    "area": "Nearby town",
                    "day_trip": True,
                    "full_day": True,
                    "activities": [
                        {"name": "Excursion palace", "duration_minutes": 180}
                    ],
                },
                *[
                    {
                        "title": f"City district {i}",
                        "area": city,
                        "activities": [
                            {"name": f"City landmark {i}", "duration_minutes": 120}
                        ],
                    }
                    for i in range(4)
                ],
            ]
        }
        short = daily_plans(city, 3, "balanced", arrival=False, advice=advice)
        assert all(not day["day_trip"] for day in short)
        assert not any(
            "Excursion palace" == a["name"] for day in short for a in day["activities"]
        )
        longer = daily_plans(city, 5, "balanced", arrival=False, advice=advice)
        assert sum(day["day_trip"] for day in longer) == 1


def test_missing_suggestions_never_turn_into_priced_timed_placeholder_activities():
    for location in ["Tokyo, Japan", "Kyoto, Japan", "Osaka, Japan", "Paris, France"]:
        days = daily_plans(location, 6, "busy", arrival=False)
        assert all(day["activities"] == [] for day in days)
        assert all(day["unfilled"] for day in days)
        assert all(day.get("estimated_minutes") is None for day in days)
