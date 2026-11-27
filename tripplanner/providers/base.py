from collections.abc import AsyncIterator
from typing import Protocol

from tripplanner.models import PlanRequest, PlanResponse


class PlanProvider(Protocol):
    async def generate(self, request: PlanRequest) -> PlanResponse: ...

    def stream(self, request: PlanRequest) -> AsyncIterator[str]: ...
