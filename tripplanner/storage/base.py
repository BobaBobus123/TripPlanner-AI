from typing import Protocol

from tripplanner.models import PlanResponse


class PlanRepository(Protocol):
    def save(self, owner_id: str, plan: PlanResponse) -> None: ...

    def get_for_owner(self, plan_id: str, owner_id: str) -> PlanResponse | None: ...
