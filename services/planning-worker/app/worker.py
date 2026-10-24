import asyncio
import concurrent.futures
import os

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from app.activities import (
    generate_sample_plan,
    update_trip_status,
)
from app.workflows import PlanTripWorkflow

load_dotenv()

TASK_QUEUE = "voyage-trip-planning"


async def main():
    client = await Client.connect(
        os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=5
    ) as executor:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[PlanTripWorkflow],
            activities=[
                update_trip_status,
                generate_sample_plan,
            ],
            activity_executor=executor,
        )

        print("Voyage planning worker started")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
