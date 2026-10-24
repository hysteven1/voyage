import asyncio

from temporalio import activity


@activity.defn
async def search_flights(trip: dict) -> list[dict]:
    await asyncio.sleep(1)

    origin = trip["origin"]
    destination = trip["destination"]

    return [
        {
            "id": "sample-flight-1",
            "provider": "Synthetic Airways",
            "origin": origin,
            "destination": destination,
            "price": "900.00",
            "duration_minutes": 840,
        },
        {
            "id": "sample-flight-2",
            "provider": "Demo Air",
            "origin": origin,
            "destination": destination,
            "price": "1150.00",
            "duration_minutes": 720,
        },
    ]


@activity.defn
async def search_hotels(trip: dict) -> list[dict]:
    await asyncio.sleep(1)

    return [
        {
            "id": "sample-hotel-1",
            "name": "Sample Central Hotel",
            "destination": trip["destination"],
            "price_per_night": "100.00",
            "capacity": 2,
        },
        {
            "id": "sample-hotel-2",
            "name": "Sample Boutique Hotel",
            "destination": trip["destination"],
            "price_per_night": "160.00",
            "capacity": 4,
        },
    ]


@activity.defn
async def search_activities(trip: dict) -> list[dict]:
    await asyncio.sleep(1)

    destination = trip["destination"]

    return [
        {
            "id": "activity-1",
            "name": f"Food tour in {destination}",
            "category": "food",
            "price_per_person": "45.00",
            "duration_hours": 3,
        },
        {
            "id": "activity-2",
            "name": f"Historical walking tour in {destination}",
            "category": "culture",
            "price_per_person": "25.00",
            "duration_hours": 2,
        },
        {
            "id": "activity-3",
            "name": f"Nature excursion near {destination}",
            "category": "nature",
            "price_per_person": "60.00",
            "duration_hours": 5,
        },
        {
            "id": "activity-4",
            "name": f"Adventure experience in {destination}",
            "category": "adventure",
            "price_per_person": "80.00",
            "duration_hours": 4,
        },
        {
            "id": "activity-5",
            "name": f"Relaxation experience in {destination}",
            "category": "relaxation",
            "price_per_person": "35.00",
            "duration_hours": 2,
        },
    ]
