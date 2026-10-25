import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.planning import TripOptions


class TripCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    origin: str | None = Field(default=None, min_length=2, max_length=255)
    destination: str = Field(default="", max_length=255)

    start_date: date
    end_date: date

    travelers: int = Field(ge=1, le=20)
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    preferences: list[str] = Field(default_factory=list)
    options: TripOptions | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        if self.options and (self.end_date - self.start_date).days > 90:
            raise ValueError("Trips must be at most 90 nights")
        if self.options:
            options = self.options
            if options.journey != "already_there" and not self.origin:
                raise ValueError("Origin is required for flying or driving")
            if options.endpoint == "return" and not self.origin:
                raise ValueError(
                    "Choose one-way or a final destination when origin is omitted"
                )
            if options.budget_mode == "flexible" and (
                options.maximum_budget is None or options.maximum_budget < self.budget
            ):
                raise ValueError(
                    "Flexible budgets need a maximum at or above the target"
                )
            self.travelers = options.adults + len(options.child_ages)
            self.destination = " → ".join(s.location for s in options.route)[:255]
        elif len(self.destination) < 2 or not self.origin:
            raise ValueError("Supply origin and destination, or expanded trip options")
        return self


class TripResponse(TripCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    planning_error: str | None = None
