import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from tripplanner.ai.budget import DailyBudget
from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure, TripPlannerError
from tripplanner.models import PlanRequest
from tripplanner.providers.base import ProviderCompletion
from tripplanner.providers.openai_compat import OpenAICompatProvider
from tripplanner.providers.recorded import RecordedProvider


def make_request(destination: str = "SecretDestination") -> PlanRequest:
    return PlanRequest(
        destination=destination,
        start_date="2027-05-10",
        end_date="2027-05-10",
        currency="UAH",
        budget=1000,
        traveler_count=1,
        interests=["private interest"],
    )


def test_openai_compatible_provider_sends_structured_request() -> None:
    content = '{"days":[],"missing_data":[]}'
    settings = Settings(
        provider="openai_compat",
        openai_compat_api_key="test-key-never-log",
        input_cost_per_million_tokens="0.15",
        output_cost_per_million_tokens="0.60",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key-never-log"
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"}
        assert body["messages"][0]["content"] == "safe prompt"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    provider = OpenAICompatProvider(settings, httpx.MockTransport(handler))
    result = asyncio.run(provider.generate(make_request(), "safe prompt"))

    assert result.content == content
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.source == "main"


def test_openai_rate_limit_is_controlled_and_does_not_echo_body() -> None:
    secret = "api-secret-should-not-leak"
    settings = Settings(
        provider="openai_compat",
        openai_compat_api_key=secret,
        input_cost_per_million_tokens="0.15",
        output_cost_per_million_tokens="0.60",
    )
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            429,
            headers={"Retry-After": "7"},
            json={"error": {"message": secret}},
        )
    )
    provider = OpenAICompatProvider(settings, transport)

    with pytest.raises(ProviderFailure) as error:
        asyncio.run(provider.generate(make_request(), "prompt"))

    assert error.value.code == ErrorCode.RATE_LIMITED
    assert error.value.retry_after == 7
    assert secret not in str(error.value)


class FixedProvider:
    async def generate(self, request: PlanRequest, prompt: str) -> ProviderCompletion:
        del request, prompt
        return ProviderCompletion(
            content='{"days":[],"missing_data":[]}',
            input_tokens=11,
            output_tokens=4,
            model="mock",
            source="mock",
            latency_ms=2,
        )

def test_recorded_provider_stores_only_hash_key_and_replays(tmp_path) -> None:
    path = tmp_path / "recordings.jsonl"
    request = make_request()
    recording = RecordedProvider(FixedProvider(), path, "record")
    asyncio.run(recording.generate(request, "prompt"))
    content = path.read_text(encoding="utf-8")

    assert "SecretDestination" not in content
    assert "private interest" not in content
    record = json.loads(content)
    assert len(record["key"]) == 64

    replay = RecordedProvider(FixedProvider(), path, "replay")
    result = asyncio.run(replay.generate(request, "prompt"))
    assert result.source == "recorded"
    assert result.content == '{"days":[],"missing_data":[]}'

    with pytest.raises(ProviderFailure) as error:
        asyncio.run(replay.generate(request, "different prompt"))
    assert error.value.code == ErrorCode.PROVIDER_UNAVAILABLE


def test_daily_budget_rejects_estimated_cost_over_configured_limit() -> None:
    settings = Settings(
        daily_budget_usd="1.00",
        input_cost_per_million_tokens="1000",
        output_cost_per_million_tokens="0",
    )

    with pytest.raises(TripPlannerError) as error:
        DailyBudget(settings).reserve(input_tokens=2000, output_tokens=0)

    assert error.value.code == ErrorCode.DAILY_BUDGET_EXCEEDED


def test_live_provider_requires_configuration_at_startup() -> None:
    with pytest.raises(ValidationError, match="OPENAI_COMPAT_API_KEY is required"):
        Settings(provider="openai_compat")
