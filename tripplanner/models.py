import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Invalid email address")
        return normalized


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Invalid email address")
        return normalized


class ResendVerificationRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Invalid email address")
        return normalized


class VerifyEmailRequest(StrictModel):
    token: str = Field(min_length=32, max_length=128)


class PlanRequest(StrictModel):
    destination: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    budget: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    traveler_count: int = Field(ge=1, le=20)
    interests: list[str] = Field(default_factory=list, max_length=10)
    constraints: list[str] = Field(default_factory=list, max_length=10)
    weather_required: bool = False

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

    @field_validator("interests", "constraints")
    @classmethod
    def normalize_preferences(cls, values: list[str]) -> list[str]:
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


class ProviderModeRequest(StrictModel):
    mode: Literal["mock", "openai_compat"]


class ItineraryDay(StrictModel):
    date: date
    activities: list[str] = Field(min_length=1)
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class WeatherDay(StrictModel):
    date: date
    temperature_min: float | None = None
    temperature_max: float | None = None
    precipitation_probability: int | None = Field(default=None, ge=0, le=100)
    weather_code: int | None = None


class LivePlace(StrictModel):
    name: str
    category: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class LiveTravelInfo(StrictModel):
    latitude: float | None = None
    longitude: float | None = None
    weather: list[WeatherDay] = Field(default_factory=list)
    attractions: list[LivePlace] = Field(default_factory=list)
    accommodations: list[LivePlace] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class PlanDraft(StrictModel):
    days: list[ItineraryDay]
    missing_data: list[str] = Field(default_factory=list)
    live_info: LiveTravelInfo | None = None


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
    live_info: LiveTravelInfo | None = None
    source: Literal["main", "fallback", "cache", "mock", "recorded"]
    created_at: datetime


class JobStatusResponse(StrictModel):
    id: UUID
    destination: str
    start_date: date
    end_date: date
    provider_mode: Literal["mock", "openai_compat"] = "mock"
    status: Literal[
        "queued",
        "preparing",
        "generating",
        "validating",
        "completed",
        "failed",
        "cancel_requested",
        "cancelled",
        "interrupted",
    ]
    message: str
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    latest_event_id: int
    plan: PlanResponse | None


class JobEnvelope(StrictModel):
    job: JobStatusResponse


class JobCreatedResponse(JobEnvelope):
    created: bool


class JobListResponse(StrictModel):
    jobs: list[JobStatusResponse]
