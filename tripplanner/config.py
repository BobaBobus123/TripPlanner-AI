from decimal import Decimal
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    provider: Literal["mock", "openai_compat"] = "mock"
    recorded_mode: Literal["disabled", "replay", "record", "passthrough"] = "disabled"
    recorded_path: str = "recordings/plans.jsonl"
    storage_backend: Literal["memory"] = "memory"
    openai_compat_base_url: AnyHttpUrl = "https://api.openai.com/v1"
    openai_compat_api_key: SecretStr | None = None
    openai_compat_model: str = "gpt-4o-mini"
    provider_timeout_seconds: float = Field(default=30, gt=0, le=180)
    overall_deadline_seconds: float = Field(default=45, gt=0, le=240)
    max_context_tokens: int = Field(default=3000, ge=128, le=16000)
    max_output_tokens: int = Field(default=2000, ge=128, le=8000)
    daily_budget_usd: Decimal = Field(default=Decimal("5.00"), gt=0, max_digits=10, decimal_places=4)
    input_cost_per_million_tokens: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=10, decimal_places=4
    )
    output_cost_per_million_tokens: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=10, decimal_places=4
    )
    mock_failure_mode: Literal[
        "none",
        "delay",
        "timeout",
        "rate_limit",
        "unavailable",
        "invalid_json",
        "stream_interrupted",
    ] = "none"
    mock_delay_seconds: float = Field(default=0.05, ge=0, le=5)

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "Settings":
        if self.provider == "openai_compat" and self.recorded_mode != "replay":
            if self.openai_compat_api_key is None or not self.openai_compat_api_key.get_secret_value().strip():
                raise ValueError("OPENAI_COMPAT_API_KEY is required for the openai_compat provider")
            if not self.openai_compat_model.strip():
                raise ValueError("OPENAI_COMPAT_MODEL must not be blank")
            if (
                self.recorded_mode != "replay"
                and self.input_cost_per_million_tokens + self.output_cost_per_million_tokens <= 0
            ):
                raise ValueError(
                    "At least one token price must be configured for the openai_compat provider"
                )
        return self
