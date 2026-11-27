import asyncio
import json
from collections.abc import AsyncIterator
from datetime import date, timedelta
from time import perf_counter

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import ItineraryDay, PlanDraft, PlanRequest
from tripplanner.providers.base import ProviderCompletion


class MockProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def generate(self, request: PlanRequest, prompt: str = "") -> ProviderCompletion:
        started = perf_counter()
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

        draft = PlanDraft(
            days=[
            ItineraryDay(
                date=day,
                activities=[
                    f"Прогуляйтеся містом {request.destination} у спокійному темпі; перед подорожжю перевірте актуальну інформацію."
                ],
            )
            for day in self._dates(request.start_date, request.end_date)
            ],
            missing_data=[
                "live_weather",
                "current_prices",
                "opening_hours",
                "budget_estimates",
            ],
        )
        content = draft.model_dump_json()
        return ProviderCompletion(
            content=content,
            input_tokens=max(1, len(prompt) // 4),
            output_tokens=max(1, len(content) // 4),
            model="deterministic-mock",
            source="mock",
            latency_ms=(perf_counter() - started) * 1000,
        )

    async def stream(self, request: PlanRequest, prompt: str = "") -> AsyncIterator[str]:
        if self._settings.mock_failure_mode == "stream_interrupted":
            yield '{"partial":'
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)

        result = await self.generate(request, prompt)
        payload = result.content
        midpoint = max(1, len(payload) // 2)
        yield payload[:midpoint]
        yield payload[midpoint:]

    @staticmethod
    def _dates(start: date, end: date) -> list[date]:
        return [
            start + timedelta(days=offset)
            for offset in range((end - start).days + 1)
        ]
