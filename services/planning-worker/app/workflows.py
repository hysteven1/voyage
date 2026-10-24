from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities import (
        generate_sample_plan,
        update_trip_status,
    )


@workflow.defn
class PlanTripWorkflow:

    @workflow.run
    async def run(self, trip_id: str) -> dict:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        await workflow.execute_activity(
            update_trip_status,
            {
                "trip_id": trip_id,
                "status": "planning",
            },
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        plan = await workflow.execute_activity(
            generate_sample_plan,
            trip_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        await workflow.execute_activity(
            update_trip_status,
            {
                "trip_id": trip_id,
                "status": "completed",
            },
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=retry_policy,
        )

        return plan
