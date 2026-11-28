from typing import Literal

from tripplanner.config import Settings
from tripplanner.providers.base import PlanProvider
from tripplanner.providers.mock import MockProvider
from tripplanner.providers.openai_compat import OpenAICompatProvider
from tripplanner.providers.recorded import RecordedProvider


ProviderMode = Literal["mock", "openai_compat"]


def create_provider(settings: Settings, mode: ProviderMode) -> PlanProvider:
    provider: PlanProvider
    if mode == "mock":
        provider = MockProvider(settings)
    else:
        provider = OpenAICompatProvider(settings)

    if settings.recorded_mode in {"replay", "record", "passthrough"}:
        return RecordedProvider(
            provider,
            settings.recorded_path,
            settings.recorded_mode,
            fingerprint=(
                f"{mode}:{settings.openai_compat_model}:"
                f"{settings.max_output_tokens}:temperature=0.2"
            ),
        )
    return provider
