import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities import (
        build_itinerary,
        load_trip,
        save_itinerary,
        update_trip_status,
    )
    from app.ai import generate_fallback_narrative, personalize_itinerary
    from app.providers import (
        search_activities,
        search_flights,
        search_hotels,
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

        async def execute(fn, arg, timeout=30):
            return await workflow.execute_activity(
                fn,
                arg,
                start_to_close_timeout=timedelta(seconds=timeout),
                retry_policy=retry_policy,
            )

        try:
            await execute(
                update_trip_status,
                {"trip_id": trip_id, "status": "planning"},
            )

            trip = await execute(load_trip, trip_id)

            # All three searches run concurrently.
            flights, hotels, activities = await asyncio.gather(
                execute(search_flights, trip),
                execute(search_hotels, trip),
                execute(search_activities, trip),
            )

            plan = await execute(
                build_itinerary,
                {
                    "trip": trip,
                    "flights": flights,
                    "hotels": hotels,
                    "activities": activities,
                },
            )

            # Personalization is optional enrichment.
            # A failure must not invalidate the budget-safe plan.
            try:
                narrative = await execute(
                    personalize_itinerary,
                    {"trip": trip, "plan": plan},
                    timeout=35,
                )
            except Exception:  # noqa: BLE001 - optional enrichment must fall back on any failure.
                workflow.logger.warning(
                    "AI personalization failed for %s; using fallback",
                    trip_id,
                )
                narrative = await execute(
                    generate_fallback_narrative,
                    {"trip": trip, "plan": plan},
                )

            # Preserve deterministic selections and calculations.
            enriched_plan = {**plan, "narrative": narrative}
            await execute(save_itinerary, enriched_plan)

            await execute(
                update_trip_status,
                {"trip_id": trip_id, "status": "completed"},
            )

            return enriched_plan

        except Exception:
            # Best-effort failure status update.
            try:
                await execute(
                    update_trip_status,
                    {"trip_id": trip_id, "status": "failed"},
                )
            except Exception:  # noqa: BLE001 - best-effort status update must not mask the original failure.
                workflow.logger.exception(
                    "Unable to update failed status for %s",
                    trip_id,
                )
            raise
