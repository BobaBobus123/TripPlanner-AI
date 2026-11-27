from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanRequest(StrictModel):
    destination: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    traveler_count: int = Field(ge=1, le=20)
    interests: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("destination")
    @classmethod
    def normalize_destination(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Destination must not be blank")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("interests")
    @classmethod
    def normalize_interests(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 80 for value in normalized):
            raise ValueError("Interests must contain 1 to 80 characters")
        return normalized

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date: date, info: ValidationInfo) -> date:
        start_date = info.data.get("start_date")
        if start_date is not None and end_date < start_date:
            raise ValueError("End date must be on or after start date")
        if start_date is not None and (end_date - start_date).days > 30:
            raise ValueError("A plan cannot exceed 31 calendar days")
        return end_date


class ItineraryDay(StrictModel):
    date: date
    activities: list[str] = Field(min_length=1)


class PlanResponse(StrictModel):
    id: str
    destination: str
    start_date: date
    end_date: date
    currency: str
    budget: Decimal
    traveler_count: int
    days: list[ItineraryDay]
    missing_data: list[str]
    source: Literal["mock"]
    created_at: datetime
