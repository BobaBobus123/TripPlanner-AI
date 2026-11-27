from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from threading import Lock

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, TripPlannerError


class DailyBudget:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = Lock()
        self._day = datetime.now(timezone.utc).date()
        self._reserved = Decimal("0")

    def reserve(self, input_tokens: int, output_tokens: int) -> Decimal:
        estimated_cost = (
            Decimal(input_tokens) * self._settings.input_cost_per_million_tokens
            + Decimal(output_tokens) * self._settings.output_cost_per_million_tokens
        ) / Decimal(1_000_000)
        now = datetime.now(timezone.utc)
        with self._lock:
            if now.date() != self._day:
                self._day = now.date()
                self._reserved = Decimal("0")
            if self._reserved + estimated_cost > self._settings.daily_budget_usd:
                retry_after = int(
                    (
                        datetime.combine(now.date() + timedelta(days=1), time.min, timezone.utc)
                        - now
                    ).total_seconds()
                )
                raise TripPlannerError(
                    ErrorCode.DAILY_BUDGET_EXCEEDED,
                    retry_after=max(1, retry_after),
                )
            self._reserved += estimated_cost
        return estimated_cost
