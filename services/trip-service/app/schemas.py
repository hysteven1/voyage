import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TripCreate(BaseModel):
    origin: str = Field(min_length=2, max_length=255)
    destination: str = Field(min_length=2, max_length=255)

    start_date: date
    end_date: date

    travelers: int = Field(ge=1, le=20)
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class TripResponse(TripCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
