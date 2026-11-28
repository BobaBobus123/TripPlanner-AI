import hashlib
import json
import logging
import math
from dataclasses import dataclass
from typing import Any

from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.models import PlanRequest

logger = logging.getLogger("tripplanner.ai")


@dataclass(frozen=True)
class BuiltContext:
    serialized_data: str
    context_hash: str
    estimated_tokens: int
    included_layers: tuple[str, ...]
    truncated: bool


class ContextBuilder:
    def __init__(self, token_budget: int) -> None:
        self._token_budget = token_budget

    def build(
        self,
        request: PlanRequest,
        live_info: dict[str, Any] | None = None,
    ) -> BuiltContext:
        core = {
            "destination": request.destination,
            "dates": {
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat(),
            },
            "budget": {
                "amount": str(request.budget),
                "currency": request.currency,
            },
            "traveler_count": request.traveler_count,
        }
        data = {
            "trip": {**core, "weather_required": request.weather_required},
            "preferences": {"interests": [], "constraints": []},
        }
        if live_info:
            data["live_information"] = live_info
        core_text = self._serialize(data)
        if self._estimate_tokens(core_text) > self._token_budget:
            raise TripPlannerError(ErrorCode.INVALID_REQUEST)

        included_preferences: dict[str, list[str]] = {
            "interests": [],
            "constraints": [],
        }
        truncated = False
        preference_layers = (
            ("interests", request.interests),
            ("constraints", request.constraints),
        )
        for layer, values in preference_layers:
            for value in values:
                candidate_preferences = {
                    key: list(items) for key, items in included_preferences.items()
                }
                candidate_preferences[layer].append(value)
                candidate = {**data, "preferences": candidate_preferences}
                if self._estimate_tokens(self._serialize(candidate)) > self._token_budget:
                    truncated = True
                    continue
                included_preferences[layer].append(value)

        data["preferences"] = included_preferences
        preference_layers_included = tuple(
            f"preferences.{key}" for key, values in included_preferences.items() if values
        )
        serialized = self._serialize(data)
        included_layers = ("trip", *preference_layers_included)
        context_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        token_count = self._estimate_tokens(serialized)
        logger.info(
            "AI context assembled",
            extra={
                "context_hash": context_hash,
                "context_tokens_estimate": token_count,
                "context_token_budget": self._token_budget,
                "context_layers": included_layers,
                "context_truncated": truncated,
            },
        )
        return BuiltContext(
            serialized_data=serialized,
            context_hash=context_hash,
            estimated_tokens=token_count,
            included_layers=included_layers,
            truncated=truncated,
        )

    @staticmethod
    def _serialize(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _estimate_tokens(value: str) -> int:
        return max(1, math.ceil(len(value) / 4))
