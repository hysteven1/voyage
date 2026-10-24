import asyncio
import json
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.optimizer import optimize_trip

load_dotenv()

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
)


@activity.defn
def update_trip_status(data: dict) -> None:
    trip_id = uuid.UUID(data["trip_id"])
    new_status = data["status"]

    if new_status not in {"planning", "completed", "failed"}:
        raise ValueError("Invalid trip status")

    with engine.begin() as connection:
        result = connection.execute(
            text("""
                UPDATE trips
                SET status = :status
                WHERE id = :trip_id
            """),
            {"status": new_status, "trip_id": trip_id},
        )

        if result.rowcount != 1:
            raise ValueError(f"Trip not found: {trip_id}")

    activity.logger.info(
        "Trip %s updated to %s",
        trip_id,
        new_status,
    )


@activity.defn
async def generate_sample_plan(trip_id: str) -> dict:
    activity.logger.info(
        "Generating sample plan for trip %s",
        trip_id,
    )

    # Simulates a provider search or planning operation.
    await asyncio.sleep(5)

    return {
        "trip_id": trip_id,
        "source": "sample_data",
        "activities": [
            "Explore local attractions",
            "Visit a cultural landmark",
            "Try regional cuisine",
        ],
    }


@activity.defn
def load_trip(trip_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT id, origin, destination,
                       start_date, end_date, travelers,
                       budget, preferences
                FROM trips
                WHERE id = :trip_id
            """),
            {"trip_id": uuid.UUID(trip_id)},
        ).mappings().first()

    if row is None:
        raise ApplicationError(
            f"Trip not found: {trip_id}",
            non_retryable=True,
        )

    return {
        "id": str(row["id"]),
        "origin": row["origin"],
        "destination": row["destination"],
        "start_date": row["start_date"].isoformat(),
        "end_date": row["end_date"].isoformat(),
        "travelers": row["travelers"],
        "budget": str(row["budget"]),
        "preferences": row["preferences"],
    }


@activity.defn
def save_itinerary(plan: dict) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO itineraries (trip_id, plan, created_at)
                VALUES (
                    :trip_id,
                    CAST(:plan AS jsonb),
                    NOW()
                )
                ON CONFLICT (trip_id)
                DO UPDATE SET
                    plan = EXCLUDED.plan,
                    created_at = EXCLUDED.created_at
            """),
            {
                "trip_id": uuid.UUID(plan["trip_id"]),
                "plan": json.dumps(plan),
            },
        )


@activity.defn
def build_itinerary(data: dict) -> dict:
    try:
        return optimize_trip(
            data["trip"],
            data["flights"],
            data["hotels"],
            data["activities"],
        )
    except ValueError as exc:
        raise ApplicationError(
            str(exc),
            non_retryable=True,
        ) from exc
