from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    provider: Literal["mock", "openai_compat"] = "mock"
    app_admin_email: str | None = None
    email_backend: Literal["development", "smtp"] = "development"
    email_from: str | None = None
    public_base_url: AnyHttpUrl = "http://127.0.0.1:8000"
    email_verification_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    recorded_mode: Literal["disabled", "replay", "record", "passthrough"] = "disabled"
    recorded_path: str = "recordings/plans.jsonl"
    storage_backend: Literal["memory", "sqlite", "postgres"] = "sqlite"
    sqlite_path: Path = Path("data/tripplanner.sqlite3")
    database_url: SecretStr | None = None
    session_cookie_secure: bool | None = None
    session_ttl_hours: int = Field(default=336, ge=1, le=2160)
    worker_poll_seconds: float = Field(default=1, gt=0, le=30)
    worker_lease_seconds: int = Field(default=90, ge=15, le=600)
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

    @field_validator("app_admin_email")
    @classmethod
    def normalize_admin_email(cls, value: str | None) -> str | None:
        normalized = value.strip().lower() if value else ""
        return normalized or None

    @field_validator("email_from")
    @classmethod
    def validate_email_from(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.strip() or "\r" in value or "\n" in value
        ):
            raise ValueError("EMAIL_FROM must be a non-empty single-line address")
        return value.strip() if value else None

    @property
    def openai_compat_available(self) -> bool:
        has_key = bool(
            self.openai_compat_api_key
            and self.openai_compat_api_key.get_secret_value().strip()
        )
        has_prices = (
            self.input_cost_per_million_tokens
            + self.output_cost_per_million_tokens
            > 0
        )
        return self.recorded_mode == "replay" or (has_key and has_prices)

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "Settings":
        if (
            self.app_env == "production"
            and self.email_backend == "smtp"
            and urlsplit(str(self.public_base_url)).scheme != "https"
        ):
            raise ValueError("PUBLIC_BASE_URL must use HTTPS in production")
        if (
            self.app_env == "production"
            and self.email_backend == "smtp"
            and not self.smtp_starttls
        ):
            raise ValueError("SMTP_STARTTLS must be enabled in production")
        if self.email_backend == "smtp":
            if not self.smtp_host or not self.email_from:
                raise ValueError("SMTP_HOST and EMAIL_FROM are required for SMTP email")
            if bool(self.smtp_username) != bool(self.smtp_password):
                raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")
        if self.app_env == "production" and self.storage_backend != "postgres":
            raise ValueError("STORAGE_BACKEND=postgres is required in production")
        if self.app_env == "production" and self.session_cookie_secure is False:
            raise ValueError("SESSION_COOKIE_SECURE cannot be disabled in production")
        if self.storage_backend == "postgres" and self.database_url is None:
            raise ValueError("DATABASE_URL is required when STORAGE_BACKEND=postgres")
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
