import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from app.activities import (
        build_itinerary,
        complete_trip,
        load_trip,
        update_trip_status,
    )
    from app.ai import generate_fallback_narrative, personalize_itinerary
    from app.booking import select_travel_options
    from app.places import suggest_places
    from app.providers import (
        search_activities,
        search_flights,
        search_hotels,
    )


@workflow.defn
class PlanTripWorkflow:
    def __init__(self):
        self.progress = {
            "stage": "starting",
            "label": "Getting your trip ready",
            "percent": 5,
        }

    @workflow.query
    def planning_progress(self) -> dict:
        return self.progress

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
                heartbeat_timeout=timedelta(seconds=30) if fn == suggest_places else None,
            )

        try:
            trip = await execute(load_trip, trip_id)

            await execute(
                update_trip_status,
                {"trip_id": trip_id, "status": "planning"},
            )

            if trip.get("options"):
                self.progress = {
                    "stage": "activities",
                    "label": "Building your day-by-day itinerary",
                    "percent": 20,
                }
                suggestions = await execute(
                    suggest_places,
                    trip,
                    timeout=30
                    + 180
                    * max(
                        (
                            (stop.get("nights", 1) + 2) // 3
                            for stop in trip["options"].get("route", [])
                        ),
                        default=1,
                    )
                    * max(1, (len(trip["options"].get("route", [])) + 3) // 4),
                )
                plan = await execute(
                    build_itinerary, {"trip": trip, "suggestions": suggestions}
                )
            else:
                # Preserve the original planner for existing saved trips.
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

            if trip.get("options") and workflow.patched("live-travel-selection-v1"):
                self.progress = {
                    "stage": "travel",
                    "label": "Finding flights and places to stay",
                    "percent": 75,
                }
                plan = await execute(
                    select_travel_options,
                    {"trip": trip, "plan": plan, "suggestions": suggestions},
                    timeout=300,
                )

            # Personalization is optional enrichment.
            # A failure must not invalidate the budget-safe plan.
            try:
                self.progress = {
                    "stage": "finishing",
                    "label": "Putting the finishing touches on your trip",
                    "percent": 90,
                }
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
            await execute(
                complete_trip,
                {"trip_id": trip_id, "plan": enriched_plan},
            )
            self.progress = {
                "stage": "completed",
                "label": "Your itinerary is ready",
                "percent": 100,
            }

            return enriched_plan

        except Exception as exc:
            self.progress = {
                "stage": "failed",
                "label": "Planning needs another attempt",
                "percent": 0,
            }
            cause = exc
            while getattr(cause, "cause", None) is not None:
                cause = cause.cause
            error = (
                cause.message[:1000]
                if isinstance(cause, ApplicationError) and cause.non_retryable
                else "Planning could not finish. Try again or adjust your trip inputs."
            )
            # Best-effort failure status update.
            try:
                await execute(
                    update_trip_status,
                    {"trip_id": trip_id, "status": "failed", "error": error},
                    timeout=15,
                )
            except Exception:  # noqa: BLE001 - best-effort status update must not mask the original failure.
                workflow.logger.exception(
                    "Unable to update failed status for %s",
                    trip_id,
                )
            raise
