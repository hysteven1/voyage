from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import product

CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def optimize_trip(
    trip: dict,
    flights: list[dict],
    hotels: list[dict],
    activities: list[dict],
) -> dict:
    start = date.fromisoformat(trip["start_date"])
    end = date.fromisoformat(trip["end_date"])

    nights = (end - start).days
    if nights < 1:
        raise ValueError("Trip must have at least one night")

    travelers = trip["travelers"]
    budget = money(trip["budget"])
    preferences = {
        p.lower() for p in trip["preferences"]
    }

    # Find the cheapest feasible flight/hotel combination.
    combinations = []

    for flight, hotel in product(flights, hotels):
        if hotel["capacity"] < travelers:
            continue

        flight_cost = money(flight["price"]) * travelers
        hotel_cost = money(hotel["price_per_night"]) * nights
        base_cost = flight_cost + hotel_cost

        if base_cost <= budget:
            combinations.append(
                (base_cost, flight, hotel, flight_cost, hotel_cost)
            )

    if not combinations:
        raise ValueError(
            "No flight and hotel combination fits the budget"
        )

    (
        _,
        selected_flight,
        selected_hotel,
        flight_cost,
        hotel_cost,
    ) = min(combinations, key=lambda item: item[0])

    remaining = budget - flight_cost - hotel_cost

    # Prefer activities matching traveler interests.
    ranked_activities = sorted(
        activities,
        key=lambda a: (
            a["category"].lower() not in preferences,
            money(a["price_per_person"]),
            a["id"],
        ),
    )

    selected_activities = []
    activity_cost = Decimal("0.00")

    # Simple MVP assumption: one activity per day.
    # Arrival and departure travel times are not modeled yet.
    for activity in ranked_activities:
        if len(selected_activities) >= nights + 1:
            break

        cost = money(activity["price_per_person"]) * travelers

        if cost <= remaining:
            selected_activities.append(activity)
            activity_cost += cost
            remaining -= cost

    days = []
    current_day = start

    while current_day <= end:
        index = (current_day - start).days

        day_activities = []
        if index < len(selected_activities):
            day_activities = [selected_activities[index]]

        days.append(
            {
                "date": current_day.isoformat(),
                "activities": day_activities,
            }
        )

        current_day += timedelta(days=1)

    total = flight_cost + hotel_cost + activity_cost

    return {
        "trip_id": trip["id"],
        "data_source": "synthetic_sample_data",
        "currency": "USD",
        "flight": selected_flight,
        "hotel": selected_hotel,
        "days": days,
        "budget": {
            "limit": str(budget),
            "flight": str(flight_cost),
            "hotel": str(hotel_cost),
            "activities": str(activity_cost),
            "total": str(total),
            "remaining": str(budget - total),
        },
    }
