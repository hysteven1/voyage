from app.day_planning import daily_plans


def test_tokyo_week_has_variety_realistic_stops_and_full_day_excursions():
    days = daily_plans("Tokyo, Japan", 7, "balanced", arrival=True)
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
    days = daily_plans("Tokyo, Japan", 12, "balanced", arrival=False)
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
        daily_plans("Tokyo, Japan", 1, pace, arrival=False)[0]["estimated_minutes"]
        for pace in ("relaxed", "balanced", "busy")
    ]
    assert durations[0] < durations[1] <= durations[2]
    days = daily_plans(
        "Tokyo, Japan", 2, "balanced", arrival=True, notes="Please include Hakone"
    )
    assert days[1]["area"] == "Hakone day trip"
