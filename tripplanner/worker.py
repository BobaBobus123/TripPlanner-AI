import asyncio
import logging
from typing import Any
from uuid import uuid4

from tripplanner.ai.orchestrator import PlanOrchestrator
from tripplanner.config import Settings
from tripplanner.errors import ERROR_CATALOG, TripPlannerError
from tripplanner.models import PlanRequest, PlanResponse
from tripplanner.providers.factory import create_provider
from tripplanner.storage.store import TripPlannerStore

logger = logging.getLogger("tripplanner.worker")


class JobWorker:
    def __init__(
        self,
        store: TripPlannerStore,
        orchestrator: PlanOrchestrator,
        settings: Settings,
        *,
        orchestrators: dict[str, PlanOrchestrator] | None = None,
    ) -> None:
        self._store = store
        self._orchestrator = orchestrator
        self._orchestrators = orchestrators or {settings.provider: orchestrator}
        self._settings = settings
        self._worker_id = str(uuid4())

    async def run(self) -> None:
        while True:
            job = await self._store.claim_job(
                self._worker_id, self._settings.worker_lease_seconds
            )
            if job is None:
                await asyncio.sleep(self._settings.worker_poll_seconds)
                continue
            await self.process(job)

    async def process(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        user_id = job["user_id"]
        request_data = dict(job["request_json"])
        provider_mode = request_data.pop("_provider_mode", self._settings.provider)
        orchestrator = self._orchestrators.get(provider_mode)
        if orchestrator is None:
            await self._store.update_job(
                job_id,
                "failed",
                "Вибраний AI-провайдер недоступний.",
                error_code="provider_unavailable",
            )
            return
        generation: asyncio.Task[PlanResponse] = asyncio.create_task(
            orchestrator.create(
                PlanRequest.model_validate(request_data),
                on_stage=lambda status, message: self._store.update_job(
                    job_id, status, message
                ),
            )
        )
        monitor = asyncio.create_task(self._monitor(job_id, generation))
        monitor.add_done_callback(
            lambda task: self._cancel_generation_after_monitor_failure(task, generation)
        )
        try:
            plan = await generation
            if await self._store.get_job_status(job_id) == "cancel_requested":
                await self._store.update_job(job_id, "cancelled", "Завдання скасовано.")
                return
            await self._store.save_plan(job_id, user_id, plan.model_dump(mode="json"))
        except asyncio.CancelledError:
            status = await self._store.get_job_status(job_id)
            if status == "cancel_requested":
                await self._store.update_job(job_id, "cancelled", "Завдання скасовано.")
            elif asyncio.current_task() and asyncio.current_task().cancelling():
                raise
        except TripPlannerError as exc:
            if await self._store.get_job_status(job_id) == "cancel_requested":
                await self._store.update_job(job_id, "cancelled", "Завдання скасовано.")
                return
            _, message, _ = ERROR_CATALOG[exc.code]
            logger.info("Trip planning job failed", extra={"job_id": job_id, "code": exc.code})
            await self._store.update_job(
                job_id, "failed", message, error_code=exc.code.value
            )
        except Exception:
            logger.exception("Unexpected trip planning worker failure", extra={"job_id": job_id})
            if await self._store.get_job_status(job_id) == "cancel_requested":
                await self._store.update_job(job_id, "cancelled", "Завдання скасовано.")
            else:
                await self._store.update_job(
                    job_id,
                    "failed",
                    "Не вдалося створити план. Спробуйте ще раз.",
                    error_code="internal",
                )
        finally:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)

    @staticmethod
    def _cancel_generation_after_monitor_failure(
        monitor: asyncio.Task, generation: asyncio.Task
    ) -> None:
        if monitor.cancelled():
            return
        error = monitor.exception()
        if error is not None:
            logger.error(
                "Job lease monitor failed",
                exc_info=(type(error), error, error.__traceback__),
            )
            generation.cancel()

    async def _monitor(self, job_id: str, generation: asyncio.Task) -> None:
        interval = min(
            max(1, self._settings.worker_poll_seconds),
            max(1, self._settings.worker_lease_seconds // 3),
        )
        while not generation.done():
            await asyncio.sleep(interval)
            status = await self._store.get_job_status(job_id)
            if status == "cancel_requested":
                generation.cancel()
                return
            if not await self._store.heartbeat(
                job_id, self._worker_id, self._settings.worker_lease_seconds
            ):
                generation.cancel()
                return


async def run_postgres_worker(settings: Settings) -> None:
    from tripplanner.ai.budget import DailyBudget
    from tripplanner.ai.orchestrator import PlanOrchestrator
    from tripplanner.storage.postgres import PostgresDatabase
    from tripplanner.storage.store import PostgresTripPlannerStore

    database = PostgresDatabase(settings)
    await database.open()
    try:
        from tripplanner.storage.postgres import initialize_schema

        await initialize_schema(database)
        store = PostgresTripPlannerStore(database)
        await store.initialize_provider_mode(settings.provider)
        providers = {
            mode: create_provider(settings, mode)
            for mode in ("mock", "openai_compat")
        }
        budget = DailyBudget(settings)
        orchestrators = {
            mode: PlanOrchestrator(provider, settings, budget)
            for mode, provider in providers.items()
        }
        await JobWorker(
            store,
            orchestrators[settings.provider],
            settings,
            orchestrators=orchestrators,
        ).run()
    finally:
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_postgres_worker(Settings()))
