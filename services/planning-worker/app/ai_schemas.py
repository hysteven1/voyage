from pydantic import BaseModel, ConfigDict


class DayDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    description: str
    travel_tip: str


class TripNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    days: list[DayDescription]


def validate_narrative(narrative: TripNarrative, plan: dict) -> None:
    expected_dates = [day["date"] for day in plan["days"]]
    actual_dates = [day.date for day in narrative.days]

    if actual_dates != expected_dates:
        raise ValueError("AI returned missing, duplicate, or reordered dates")
