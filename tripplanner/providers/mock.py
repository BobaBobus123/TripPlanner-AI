import asyncio
import json
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import ItineraryDay, PlanRequest, PlanResponse


class MockProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, request: PlanRequest) -> PlanResponse:
        mode = self._settings.mock_failure_mode
        if mode == "delay":
            await asyncio.sleep(self._settings.mock_delay_seconds)
        elif mode == "timeout":
            raise ProviderFailure(ErrorCode.PROVIDER_TIMEOUT)
        elif mode == "rate_limit":
            raise ProviderFailure(ErrorCode.RATE_LIMITED, retry_after=1)
        elif mode == "unavailable":
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)
        elif mode == "invalid_json":
            try:
                json.loads("{invalid-json")
            except json.JSONDecodeError as exc:
                raise ProviderFailure(ErrorCode.INVALID_OUTPUT) from exc

        days = [
            ItineraryDay(
                date=day,
                activities=[
                    f"Explore {request.destination} at a relaxed pace; confirm current details before travel."
                ],
            )
            for day in self._dates(request.start_date, request.end_date)
        ]
        return PlanResponse(
            id=str(uuid4()),
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            currency=request.currency,
            budget=request.budget,
            traveler_count=request.traveler_count,
            days=days,
            missing_data=["live_weather", "current_prices", "opening_hours"],
            source="mock",
            created_at=datetime.now(timezone.utc),
        )

    async def stream(self, request: PlanRequest) -> AsyncIterator[str]:
        if self._settings.mock_failure_mode == "stream_interrupted":
            yield '{"partial":'
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)

        result = await self.generate(request)
        payload = result.model_dump_json()
        midpoint = max(1, len(payload) // 2)
        yield payload[:midpoint]
        yield payload[midpoint:]

    @staticmethod
    def _dates(start: date, end: date) -> list[date]:
        return [
            start + timedelta(days=offset)
            for offset in range((end - start).days + 1)
        ]
