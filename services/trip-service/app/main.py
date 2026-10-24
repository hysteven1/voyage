import os
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.database import get_db
from app.models import Itinerary, Trip
from app.schemas import TripCreate, TripResponse

app = FastAPI(
    title="Voyage Trip Service",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "trip-service",
    }


@app.post(
    "/api/v1/trips",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trip(
    payload: TripCreate,
    db: Annotated[Session, Depends(get_db)],
):
    trip = Trip(**payload.model_dump())

    db.add(trip)
    db.commit()
    db.refresh(trip)

    return trip


@app.get(
    "/api/v1/trips/{trip_id}",
    response_model=TripResponse,
)
def get_trip(
    trip_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    return trip


@app.get(
    "/api/v1/trips",
    response_model=list[TripResponse],
)
def list_trips(
    db: Annotated[Session, Depends(get_db)],
):
    from sqlalchemy import select

    statement = (
        select(Trip)
        .order_by(Trip.created_at.desc())
        .limit(100)
    )

    return db.scalars(statement).all()


@app.post("/api/v1/trips/{trip_id}/plan")
async def start_trip_planning(
    trip_id: uuid.UUID,
):
    # This sync helper is intentionally called in a thread
    # so we don't block FastAPI's event loop.
    from fastapi.concurrency import run_in_threadpool

    from app.database import SessionLocal

    def check_trip():
        with SessionLocal() as db:
            trip = db.get(Trip, trip_id)

            if trip is None:
                return None

            return trip.status

    trip_status = await run_in_threadpool(check_trip)

    if trip_status is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    if trip_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Trip planning already completed",
        )

    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )

    workflow_id = f"plan-trip-{trip_id}"

    try:
        await client.start_workflow(
            "PlanTripWorkflow",
            str(trip_id),
            id=workflow_id,
            task_queue="voyage-trip-planning",
        )
    except WorkflowAlreadyStartedError:
        pass

    return {
        "trip_id": str(trip_id),
        "workflow_id": workflow_id,
        "message": "Trip planning requested",
    }


@app.get("/api/v1/trips/{trip_id}/itinerary")
def get_itinerary(
    trip_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    trip = db.get(Trip, trip_id)

    if trip is None:
        raise HTTPException(404, "Trip not found")

    itinerary = db.get(Itinerary, trip_id)

    if itinerary is None:
        raise HTTPException(
            status_code=404,
            detail="Itinerary not generated yet",
        )

    return itinerary.plan
