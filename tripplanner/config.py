from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    provider: Literal["mock"] = "mock"
    storage_backend: Literal["memory"] = "memory"
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
