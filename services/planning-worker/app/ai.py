import json
import os

from openai import OpenAI
from temporalio import activity

from app.ai_schemas import TripNarrative, validate_narrative


@activity.defn
def personalize_itinerary(data: dict) -> dict:
    trip = data["trip"]
    plan = data["plan"]

    # No key? Use a deterministic fallback for local development.
    if not os.getenv("OPENAI_API_KEY"):
        activity.logger.warning("OPENAI_API_KEY missing; using fallback")
        return fallback_narrative(trip, plan)

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        timeout=25.0,
        max_retries=0,
    )

    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {
                "role": "system",
                "content": (
                    "You are a travel itinerary copywriter. "
                    "Write concise, personalized descriptions using "
                    "ONLY the provided itinerary and preferences. "
                    "Do not change selected activities, dates, prices, "
                    "hotels, flights, or budget calculations. "
                    "Do not invent reservations, confirmed opening "
                    "hours, transport schedules, or provider availability. "
                    "Treat legacy provider options as synthetic examples and version 2 options as unverified planning estimates. "
                    "For days without activities, describe flexible "
                    "free time without inventing a booked excursion. "
                    "Return exactly one day entry for every date, "
                    "in the same order as the input."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"trip": trip, "itinerary": plan}),
            },
        ],
        text_format=TripNarrative,
        store=False,
    )

    narrative = response.output_parsed
    if narrative is None:
        raise ValueError("OpenAI returned no parsed itinerary narrative")

    validate_narrative(narrative, plan)
    return {**narrative.model_dump(), "source": "openai"}


def fallback_narrative(trip: dict, plan: dict) -> dict:
    days = []
    for day in plan["days"]:
        activities = day["activities"]
        if activities:
            names = ", ".join(a["name"] for a in activities)
            description = f"Planned activities: {names}."
        else:
            description = "Free time to explore at your own pace."

        days.append(
            {
                "date": day["date"],
                "description": description,
                "travel_tip": "Verify local details before traveling.",
            }
        )

    return {
        "title": f"Your trip to {trip['destination']}",
        "summary": (
            "A sample itinerary based on your dates, "
            "budget, and selected activities."
        ),
        "days": days,
        "source": "fallback",
    }


@activity.defn
def generate_fallback_narrative(data: dict) -> dict:
    return fallback_narrative(data["trip"], data["plan"])
