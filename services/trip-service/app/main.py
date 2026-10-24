from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator


app = FastAPI(
    title="Voyage Trip Service",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class TripRequest(BaseModel):
    origin: str = Field(min_length=2)
    destination: str = Field(min_length=2)
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=20)
    budget: float = Field(gt=0)
    preferences: list[str] = []

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": "trip-service",
    }


@app.post("/api/v1/trips", status_code=201)
async def create_trip(trip: TripRequest):
    return {
        "message": "Trip request received",
        "trip": trip.model_dump(mode="json"),
    }