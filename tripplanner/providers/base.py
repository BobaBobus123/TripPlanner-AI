from dataclasses import dataclass
from typing import Literal, Protocol

from tripplanner.models import PlanRequest


@dataclass(frozen=True)
class ProviderCompletion:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    source: Literal["main", "mock", "recorded"]
    latency_ms: float


class PlanProvider(Protocol):
    async def generate(self, request: PlanRequest, prompt: str) -> ProviderCompletion: ...
