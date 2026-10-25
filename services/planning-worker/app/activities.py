import asyncio
import json
import logging
import os
import uuid
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.optimizer import optimize_trip
from app.planning import build_plan

logger = logging.getLogger("voyage.activities")


@contextmanager
def log_activity(trip_id, message):
    logger.info(message, extra={"trip_id": trip_id})
    try:
        yield
    except Exception:
        logger.exception("Trip planning activity failed", extra={"trip_id": trip_id})
        raise


load_dotenv()

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
    hide_parameters=True,
)


@activity.defn
def update_trip_status(data: dict) -> None:
    with log_activity(data.get("trip_id"), "Updating trip status"):
        trip_id = uuid.UUID(data["trip_id"])
        new_status = data["status"]

        if new_status not in {"planning", "completed", "failed"}:
            raise ValueError("Invalid trip status")

        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE trips
                    SET status = :status, planning_error = :planning_error
                    WHERE id = :trip_id
                """),
                {
                    "status": new_status,
                    "trip_id": trip_id,
                    "planning_error": data.get("error")
                    if new_status == "failed"
                    else None,
                },
            )

            if result.rowcount != 1:
                raise ValueError(f"Trip not found: {trip_id}")

        logger.info(
            "Trip %s updated to %s",
            trip_id,
            new_status,
            extra={"trip_id": str(trip_id)},
        )


@activity.defn
async def generate_sample_plan(trip_id: str) -> dict:
    logger.info("Generating sample plan", extra={"trip_id": trip_id})

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
    with log_activity(trip_id, "Loading trip"):
        with engine.connect() as connection:
            row = (
                connection.execute(
                    text("""
                    SELECT id, origin, destination,
                           start_date, end_date, travelers,
                           budget, preferences, options
                    FROM trips
                    WHERE id = :trip_id
                """),
                    {"trip_id": uuid.UUID(trip_id)},
                )
                .mappings()
                .first()
            )

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
            "budget": str(row["budget"]) if row["budget"] is not None else None,
            "preferences": row["preferences"],
            "options": row["options"],
        }


@activity.defn
def save_itinerary(plan: dict) -> None:
    with (
        log_activity(plan.get("trip_id"), "Saving itinerary"),
        engine.begin() as connection,
    ):
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
def complete_trip(data: dict) -> None:
    with log_activity(data.get("trip_id"), "Completing trip"):
        trip_id = data["trip_id"]
        plan = data["plan"]
        if plan.get("incomplete_destinations") or any(
            day.get("needs_personalization") for day in plan.get("days", [])
        ):
            raise ApplicationError(
                "Activity planning did not finish. Please retry planning."
            )

        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO itineraries (trip_id, plan, created_at)
                    VALUES (
                        CAST(:trip_id AS uuid),
                        CAST(:plan AS jsonb),
                        NOW()
                    )
                    ON CONFLICT (trip_id)
                    DO UPDATE SET plan = EXCLUDED.plan
                """),
                {"trip_id": trip_id, "plan": json.dumps(plan)},
            )
            result = connection.execute(
                text("""
                    UPDATE trips
                    SET status = 'completed', planning_error = NULL
                    WHERE id = CAST(:trip_id AS uuid)
                """),
                {"trip_id": trip_id},
            )
            if result.rowcount != 1:
                raise ValueError(f"Trip not found: {trip_id}")
    logger.info("Trip completed successfully", extra={"trip_id": data["trip_id"]})


@activity.defn
def build_itinerary(data: dict) -> dict:
    with log_activity(data.get("trip", {}).get("id"), "Building itinerary"):
        try:
            if data["trip"].get("options"):
                return build_plan(data["trip"], data.get("suggestions"))
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
