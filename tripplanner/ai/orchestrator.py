import json
import logging
import math
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from tripplanner.ai.budget import DailyBudget
from tripplanner.ai.context import ContextBuilder
from tripplanner.ai.prompt import PROMPT_VERSION, PromptRenderer
from tripplanner.ai.validation import validate_plan_draft
from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure, TripPlannerError
from tripplanner.models import PlanDraft, PlanRequest, PlanResponse
from tripplanner.providers.base import PlanProvider

logger = logging.getLogger("tripplanner.ai")


class PlanOrchestrator:
    def __init__(
        self,
        provider: PlanProvider,
        settings: Settings,
        budget: DailyBudget,
        context_builder: ContextBuilder | None = None,
        prompt_renderer: PromptRenderer | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._budget = budget
        self._context_builder = context_builder or ContextBuilder(settings.max_context_tokens)
        self._prompt_renderer = prompt_renderer or PromptRenderer()

    async def create(self, request: PlanRequest) -> PlanResponse:
        started = perf_counter()
        context = self._context_builder.build(request)
        feedback = ""

        for attempt in range(2):
            prompt = self._prompt_renderer.render(context, feedback)
            estimated_input_tokens = max(1, math.ceil(len(prompt) / 4))
            self._budget.reserve(estimated_input_tokens, self._settings.max_output_tokens)
            try:
                completion = await self._provider.generate(request, prompt)
                draft = PlanDraft.model_validate_json(completion.content)
                validate_plan_draft(draft, request)
            except ProviderFailure:
                raise
            except (ValidationError, json.JSONDecodeError):
                feedback = "schema_validation_failed"
                if attempt == 1:
                    raise TripPlannerError(ErrorCode.INVALID_OUTPUT) from None
                continue
            except TripPlannerError as exc:
                if exc.code != ErrorCode.INVALID_OUTPUT:
                    raise
                feedback = "domain_validation_failed"
                if attempt == 1:
                    raise TripPlannerError(ErrorCode.INVALID_OUTPUT) from None
                continue

            actual_cost = (
                completion.input_tokens * self._settings.input_cost_per_million_tokens
                + completion.output_tokens * self._settings.output_cost_per_million_tokens
            ) / 1_000_000
            logger.info(
                "AI plan generated",
                extra={
                    "prompt_version": PROMPT_VERSION,
                    "provider": completion.source,
                    "model": completion.model,
                    "input_tokens": completion.input_tokens,
                    "output_tokens": completion.output_tokens,
                    "cost_usd_estimate": str(actual_cost),
                    "latency_ms": round(completion.latency_ms, 2),
                    "total_duration_ms": round((perf_counter() - started) * 1000, 2),
                    "validation_attempt": attempt + 1,
                    "context_hash": context.context_hash,
                },
            )
            return PlanResponse(
                id=str(uuid4()),
                destination=request.destination,
                start_date=request.start_date,
                end_date=request.end_date,
                currency=request.currency,
                budget=request.budget,
                traveler_count=request.traveler_count,
                days=draft.days,
                missing_data=draft.missing_data,
                source=completion.source,
                created_at=datetime.now(timezone.utc),
            )

        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)
