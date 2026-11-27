from tripplanner.errors import ErrorCode, ProviderFailure, TripPlannerError
from tripplanner.models import PlanRequest, PlanResponse
from tripplanner.providers.base import PlanProvider
from tripplanner.storage.base import PlanRepository


class PlanService:
    def __init__(self, provider: PlanProvider, repository: PlanRepository) -> None:
        self._provider = provider
        self._repository = repository

    async def create(self, owner_id: str, request: PlanRequest) -> PlanResponse:
        try:
            plan = await self._provider.generate(request)
        except ProviderFailure:
            raise
        self._repository.save(owner_id, plan)
        return plan

    def get(self, owner_id: str, plan_id: str) -> PlanResponse:
        plan = self._repository.get_for_owner(plan_id, owner_id)
        if plan is None:
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        return plan
