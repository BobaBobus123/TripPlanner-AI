import asyncio
from datetime import datetime, timezone

from tripplanner.config import Settings
from tripplanner.models import ItineraryDay, PlanResponse
from tripplanner.storage.store import MemoryTripPlannerStore
from tripplanner.worker import JobWorker


class TrackingOrchestrator:
    def __init__(self) -> None:
        self.calls = 0

    async def create(self, request, on_stage=None) -> PlanResponse:
        self.calls += 1
        if on_stage is not None:
            await on_stage("generating", "Створюємо маршрут.")
        return PlanResponse(
            id="plan-id",
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            currency=request.currency,
            budget=request.budget,
            traveler_count=request.traveler_count,
            days=[
                ItineraryDay(
                    date=request.start_date,
                    activities=["Відвідайте місцевий музей."],
                )
            ],
            missing_data=[],
            source="main",
            created_at=datetime.now(timezone.utc),
        )


def test_worker_uses_provider_mode_saved_with_the_queued_job() -> None:
    async def scenario() -> tuple[int, int, str]:
        store = MemoryTripPlannerStore()
        user = await store.register_user("traveler@example.com", "password-hash")
        assert user is not None
        payload = {
            "destination": "Львів",
            "start_date": "2027-05-10",
            "end_date": "2027-05-10",
            "currency": "UAH",
            "budget": "1000",
            "traveler_count": 1,
            "interests": [],
            "constraints": [],
            "weather_required": False,
            "_provider_mode": "openai_compat",
        }
        await store.enqueue_job(user["id"], payload, "fingerprint", "request-key")
        job = await store.claim_job("worker", 30)
        assert job is not None

        mock = TrackingOrchestrator()
        live = TrackingOrchestrator()
        settings = Settings()
        await JobWorker(
            store,
            mock,
            settings,
            orchestrators={"mock": mock, "openai_compat": live},
        ).process(job)
        saved = await store.get_job(job["id"], user["id"])
        assert saved is not None
        return mock.calls, live.calls, saved["status"]

    mock_calls, live_calls, status = asyncio.run(scenario())

    assert mock_calls == 0
    assert live_calls == 1
    assert status == "completed"
