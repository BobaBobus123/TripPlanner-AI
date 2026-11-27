import asyncio

import pytest

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import PlanRequest
from tripplanner.providers.mock import MockProvider


def request() -> PlanRequest:
    return PlanRequest(
        destination="Kyiv",
        start_date="2027-05-10",
        end_date="2027-05-10",
        currency="UAH",
        budget=1000,
        traveler_count=1,
    )


def test_mock_failure_modes_surface_controlled_errors() -> None:
    provider = MockProvider(Settings(mock_failure_mode="rate_limit"))

    with pytest.raises(ProviderFailure) as error:
        asyncio.run(provider.generate(request()))

    assert error.value.code == ErrorCode.RATE_LIMITED
    assert error.value.retry_after == 1


def test_stream_failure_is_explicit() -> None:
    provider = MockProvider(Settings(mock_failure_mode="stream_interrupted"))

    async def collect() -> list[str]:
        chunks = []
        async for chunk in provider.stream(request()):
            chunks.append(chunk)
        return chunks

    with pytest.raises(ProviderFailure) as error:
        asyncio.run(collect())

    assert error.value.code == ErrorCode.PROVIDER_UNAVAILABLE
