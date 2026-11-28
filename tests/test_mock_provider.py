import asyncio

import pytest

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import PlanDraft, PlanRequest
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


def test_mock_plan_contains_distinct_actions_and_respects_user_interests() -> None:
    payload = request().model_copy(
        update={"interests": ["історія"], "constraints": ["уникати довгих переходів"]}
    )
    provider = MockProvider(Settings())

    async def generate() -> PlanDraft:
        completion = await provider.generate(payload)
        return PlanDraft.model_validate_json(completion.content)

    draft = asyncio.run(generate())
    activities = draft.days[0].activities

    assert len(activities) == 3
    assert len({activity.casefold() for activity in activities}) == 3
    assert "історія" in activities[1]
    assert "обмеження" in activities[1]
