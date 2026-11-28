import asyncio
import logging

import pytest

from tripplanner.ai.budget import DailyBudget
from tripplanner.ai.context import ContextBuilder
from tripplanner.ai.orchestrator import PlanOrchestrator
from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.models import PlanDraft, PlanRequest
from tripplanner.providers.base import ProviderCompletion


def plan_request(**updates: object) -> PlanRequest:
    value: dict[str, object] = {
        "destination": "Kyiv",
        "start_date": "2027-05-10",
        "end_date": "2027-05-11",
        "currency": "UAH",
        "budget": 1000,
        "traveler_count": 1,
        "interests": ["history"],
    }
    value.update(updates)
    return PlanRequest.model_validate(value)


def completion(content: str) -> ProviderCompletion:
    return ProviderCompletion(
        content=content,
        input_tokens=100,
        output_tokens=50,
        model="test-model",
        source="mock",
        latency_ms=1,
    )


class SequenceProvider:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.prompts: list[str] = []

    async def generate(self, request: PlanRequest, prompt: str) -> ProviderCompletion:
        del request
        self.prompts.append(prompt)
        return completion(self.contents.pop(0))

    async def stream(self, request: PlanRequest, prompt: str):
        yield (await self.generate(request, prompt)).content


def valid_draft() -> str:
    return PlanDraft(
        days=[
            {
                "date": "2027-05-10",
                "activities": [
                    "Visit a local museum and choose an exhibit that matches your interests.",
                    "Walk through a nearby public area and leave time for a relaxed break.",
                ],
            },
            {
                "date": "2027-05-11",
                "activities": [
                    "Explore a different neighborhood and check current transit options.",
                    "Choose a cultural stop based on verified opening information.",
                ],
            },
        ],
        missing_data=[
            "live_weather",
            "current_prices",
            "opening_hours",
            "budget_estimates",
        ],
    ).model_dump_json()


def test_invalid_schema_gets_exactly_one_retry() -> None:
    provider = SequenceProvider(["not-json", valid_draft()])
    settings = Settings()
    orchestrator = PlanOrchestrator(provider, settings, DailyBudget(settings))

    result = asyncio.run(orchestrator.create(plan_request()))

    assert result.source == "mock"
    assert len(provider.prompts) == 2
    assert "schema_validation_failed" in provider.prompts[1]


def test_domain_invalid_dates_get_one_retry_then_safe_error() -> None:
    invalid = PlanDraft(
        days=[
            {
                "date": "2027-05-09",
                "activities": [
                    "Outside trip dates and should be rejected.",
                    "Choose a different route option for this day.",
                ],
            },
            {
                "date": "2027-05-11",
                "activities": [
                    "Explore a suitable local museum.",
                    "Take a relaxed break in a public area.",
                ],
            },
        ],
        missing_data=[
            "live_weather",
            "current_prices",
            "opening_hours",
            "budget_estimates",
        ],
    ).model_dump_json()
    provider = SequenceProvider([invalid, invalid])
    settings = Settings()
    orchestrator = PlanOrchestrator(provider, settings, DailyBudget(settings))

    with pytest.raises(TripPlannerError) as error:
        asyncio.run(orchestrator.create(plan_request()))

    assert error.value.code == ErrorCode.INVALID_OUTPUT
    assert len(provider.prompts) == 2
    assert "Outside trip dates" not in str(error.value)


def test_underplanned_day_gets_one_retry() -> None:
    underplanned = PlanDraft(
        days=[
            {"date": "2027-05-10", "activities": ["Visit a local museum"]},
            {
                "date": "2027-05-11",
                "activities": [
                    "Explore a different neighborhood at a relaxed pace.",
                    "Choose a cultural stop after checking current opening details.",
                ],
            },
        ],
        missing_data=[
            "live_weather",
            "current_prices",
            "opening_hours",
            "budget_estimates",
        ],
    ).model_dump_json()
    provider = SequenceProvider([underplanned, valid_draft()])
    settings = Settings()
    orchestrator = PlanOrchestrator(provider, settings, DailyBudget(settings))

    result = asyncio.run(orchestrator.create(plan_request()))

    assert len(result.days[0].activities) == 2
    assert len(provider.prompts) == 2
    assert "2 to 5 distinct" in provider.prompts[0]
    assert "domain_validation_failed" in provider.prompts[1]


def test_context_truncates_optional_interests_and_keeps_user_text_in_data(caplog) -> None:
    caplog.set_level(logging.INFO, logger="tripplanner.ai")
    request = plan_request(
        interests=["x" * 80, "second interest", "third interest"]
    )

    context = ContextBuilder(token_budget=75).build(request)

    assert context.truncated
    assert context.estimated_tokens <= 75
    assert context.serialized_data.startswith('{"preferences"')
    assert "UNTRUSTED" not in context.serialized_data
    assert "x" * 80 not in caplog.text
