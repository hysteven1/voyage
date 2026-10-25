import asyncio
import concurrent.futures
import logging
import os
import signal
from datetime import timedelta

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
from app.booking import select_travel_options
from app.health import serve_health
from app.logging_config import configure_logging
from app.places import suggest_places
from app.providers import (
    search_activities,
    search_flights,
    search_hotels,
)
from app.temporal_config import connection_options
from app.workflows import PlanTripWorkflow

load_dotenv()


async def main():
    configure_logging()
    logger = logging.getLogger("voyage.worker")
    logger.info("Starting Temporal planning worker")
    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233"), **connection_options()
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
                select_travel_options,
            ],
            activity_executor=executor,
            max_concurrent_activities=int(os.getenv("WORKER_MAX_CONCURRENT_ACTIVITIES", "4")),
            graceful_shutdown_timeout=timedelta(seconds=90),
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop.set)
        server = await serve_health(worker, client)
        try:
            async with server, worker:
                logger.info("Voyage planning worker started")
                await stop.wait()
        finally:
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
