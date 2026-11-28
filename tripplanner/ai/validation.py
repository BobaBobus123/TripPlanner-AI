from datetime import timedelta
from decimal import Decimal

from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.models import PlanDraft, PlanRequest

REQUIRED_MISSING_DATA = {
    "live_weather",
    "current_prices",
    "opening_hours",
}


def validate_plan_draft(draft: PlanDraft, request: PlanRequest) -> None:
    expected_dates = [
        request.start_date + timedelta(days=offset)
        for offset in range((request.end_date - request.start_date).days + 1)
    ]
    actual_dates = [day.date for day in draft.days]
    if actual_dates != expected_dates:
        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)

    for day in draft.days:
        activities = [activity.strip().casefold() for activity in day.activities]
        if (
            not 2 <= len(activities) <= 5
            or any(len(activity) < 12 for activity in activities)
            or len(set(activities)) != len(activities)
        ):
            raise TripPlannerError(ErrorCode.INVALID_OUTPUT)

    if not REQUIRED_MISSING_DATA.issubset(draft.missing_data):
        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)

    costs = [day.estimated_cost for day in draft.days]
    if any(cost is not None and cost < Decimal("0") for cost in costs):
        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)
    if all(cost is None for cost in costs):
        if "budget_estimates" not in draft.missing_data:
            raise TripPlannerError(ErrorCode.INVALID_OUTPUT)
        return
    if any(cost is None for cost in costs):
        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)
    total_cost = sum((cost for cost in costs if cost is not None), Decimal("0"))
    if total_cost > request.budget:
        raise TripPlannerError(ErrorCode.INVALID_OUTPUT)
