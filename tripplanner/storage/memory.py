from threading import Lock

from tripplanner.models import PlanResponse


class InMemoryPlanRepository:
    def __init__(self) -> None:
        self._plans: dict[str, tuple[str, PlanResponse]] = {}
        self._lock = Lock()

    def save(self, owner_id: str, plan: PlanResponse) -> None:
        with self._lock:
            self._plans[plan.id] = (owner_id, plan)

    def get_for_owner(self, plan_id: str, owner_id: str) -> PlanResponse | None:
        with self._lock:
            stored = self._plans.get(plan_id)
        if stored is None or stored[0] != owner_id:
            return None
        return stored[1]
