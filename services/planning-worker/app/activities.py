import asyncio
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from temporalio import activity

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
