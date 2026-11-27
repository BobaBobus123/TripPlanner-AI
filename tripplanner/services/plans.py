from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.models import PlanRequest, PlanResponse
from tripplanner.ai.orchestrator import PlanOrchestrator
from tripplanner.storage.base import PlanRepository


class PlanService:
    def __init__(self, orchestrator: PlanOrchestrator, repository: PlanRepository) -> None:
        self._orchestrator = orchestrator
        self._repository = repository

    async def create(self, owner_id: str, request: PlanRequest) -> PlanResponse:
        plan = await self._orchestrator.create(request)
        self._repository.save(owner_id, plan)
        return plan

    def get(self, owner_id: str, plan_id: str) -> PlanResponse:
        plan = self._repository.get_for_owner(plan_id, owner_id)
        if plan is None:
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        return plan
