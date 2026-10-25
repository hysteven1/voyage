import asyncio
import logging
import os
import time
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from app.database import engine, get_db
from app.logging_config import configure_logging
from app.models import Itinerary, Trip
from app.planning import build_plan, propose_route, validate_route
from app.schemas import TripCreate, TripResponse
from app.temporal_config import connection_options

app = FastAPI(
    title="Voyage Trip Service",
    version="0.2.0",
)

configure_logging()
logger = logging.getLogger("voyage.api")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    request.state.request_id = request_id
    fields = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    }
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "HTTP request failed",
            extra={
                **fields,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        raise

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "HTTP request completed",
        extra={
            **fields,
            "status_code": response.status_code,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        },
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "trip-service",
    }


@app.get("/api/v1/health/live")
def liveness():
    return {
        "status": "alive",
        "service": "trip-service",
    }


@app.get("/api/v1/health/ready")
async def readiness():
    def check_database():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    try:
        await run_in_threadpool(check_database)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    return {
        "status": "ready",
        "service": "trip-service",
        "database": "connected",
    }


@app.post("/api/v1/trips/route-proposal")
def route_proposal(payload: TripCreate):
    if payload.options is None:
        raise HTTPException(422, "Provide destinations and trip options")
    try:
        return propose_route(payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post(
    "/api/v1/trips",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trip(
    payload: TripCreate,
    db: Annotated[Session, Depends(get_db)],
):
    if payload.options:
        try:
            validate_route(payload.model_dump(mode="json"))
            build_plan({**payload.model_dump(mode="json"), "id": "draft"})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
    values = payload.model_dump()
    if payload.options:
        values["options"] = payload.options.model_dump(mode="json")
    trip = Trip(**values)

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

    statement = select(Trip).order_by(Trip.created_at.desc()).limit(100)

    return db.scalars(statement).all()


@app.get("/api/v1/trips/{trip_id}/progress")
async def trip_planning_progress(trip_id: uuid.UUID):
    def read_status():
        with Session(engine) as db:
            trip = db.get(Trip, trip_id)
            if trip is None:
                raise HTTPException(status_code=404, detail="Trip not found")
            return trip.status

    trip_status = await run_in_threadpool(read_status)
    if trip_status == "completed":
        return {
            "stage": "completed",
            "label": "Your itinerary is ready",
            "percent": 100,
        }
    if trip_status == "failed":
        return {
            "stage": "failed",
            "label": "Planning needs another attempt",
            "percent": 0,
        }

    async def query_progress():
        client = await Client.connect(
            os.getenv("TEMPORAL_ADDRESS", "localhost:7233"), **connection_options()
        )
        return await client.get_workflow_handle(f"plan-trip-{trip_id}").query(
            "planning_progress"
        )

    try:
        return await asyncio.wait_for(query_progress(), timeout=3)
    except Exception:  # noqa: BLE001 - progress is optional; older workers may not expose the query.
        return {
            "stage": "planning",
            "label": "Building your itinerary",
            "percent": None,
        }


@app.post("/api/v1/trips/{trip_id}/plan")
async def start_trip_planning(
    trip_id: uuid.UUID,
    request: Request,
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

            existing_itinerary = db.get(Itinerary, trip_id)
            return trip.status, existing_itinerary is not None

    trip_state = await run_in_threadpool(check_trip)

    if trip_state is None:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    trip_status, itinerary_exists = trip_state

    if itinerary_exists:
        return {
            "status": "completed",
            "message": "An itinerary already exists for this trip.",
            "trip_id": str(trip_id),
        }

    if trip_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Trip planning already completed",
        )

    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233"), **connection_options()
    )

    workflow_id = f"plan-trip-{trip_id}"

    try:
        await client.start_workflow(
            "PlanTripWorkflow",
            str(trip_id),
            id=workflow_id,
            task_queue="voyage-trip-planning",
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
        )
    except WorkflowAlreadyStartedError:
        raise HTTPException(
            status_code=409,
            detail="Trip planning workflow already completed",
        ) from None

    logger.info(
        "Trip planning requested",
        extra={
            "trip_id": str(trip_id), "workflow_id": workflow_id,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
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
