import asyncio
import concurrent.futures
import logging
import os

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from app.activities import (
    build_itinerary,
    complete_trip,
    load_trip,
    save_itinerary,
    update_trip_status,
)
from app.ai import generate_fallback_narrative, personalize_itinerary
from app.logging_config import configure_logging
from app.places import suggest_places
from app.providers import (
    search_activities,
    search_flights,
    search_hotels,
)
from app.workflows import PlanTripWorkflow

load_dotenv()


async def main():
    configure_logging()
    logger = logging.getLogger("voyage.worker")
    logger.info("Starting Temporal planning worker")
    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=10
    ) as executor:
        worker = Worker(
            client,
            task_queue="voyage-trip-planning",
            workflows=[PlanTripWorkflow],
            activities=[
                load_trip,
                update_trip_status,
                search_flights,
                search_hotels,
                search_activities,
                build_itinerary,
                personalize_itinerary,
                generate_fallback_narrative,
                save_itinerary,
                complete_trip,
                suggest_places,
            ],
            activity_executor=executor,
        )

        logger.info("Voyage planning worker started")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
