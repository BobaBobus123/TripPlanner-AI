import asyncio
from time import perf_counter

import httpx

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import PlanRequest
from tripplanner.providers.base import ProviderCompletion


class OpenAICompatProvider:
    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def generate(self, request: PlanRequest, prompt: str) -> ProviderCompletion:
        del request
        key = self._settings.openai_compat_api_key
        if key is None:
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)
        headers = {"Authorization": f"Bearer {key.get_secret_value()}"}
        payload = {
            "model": self._settings.openai_compat_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": self._settings.max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        url = f"{str(self._settings.openai_compat_base_url).rstrip('/')}/chat/completions"
        timeout = httpx.Timeout(self._settings.provider_timeout_seconds)
        started = perf_counter()
        try:
            async with asyncio.timeout(self._settings.overall_deadline_seconds):
                async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                    response = await client.post(url, headers=headers, json=payload)
        except TimeoutError as exc:
            raise ProviderFailure(ErrorCode.PROVIDER_TIMEOUT) from exc
        except httpx.TimeoutException as exc:
            raise ProviderFailure(ErrorCode.PROVIDER_TIMEOUT) from exc
        except httpx.RequestError as exc:
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE) from exc

        if response.status_code == 429:
            retry_after = self._retry_after(response)
            raise ProviderFailure(ErrorCode.RATE_LIMITED, retry_after=retry_after)
        if response.status_code >= 500:
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)
        if response.is_error:
            raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)

        try:
            body = response.json()
            choices = body["choices"]
            content = choices[0]["message"]["content"]
            usage = body.get("usage", {})
            input_tokens = self._nonnegative_int(usage.get("prompt_tokens"))
            output_tokens = self._nonnegative_int(usage.get("completion_tokens"))
            if not isinstance(content, str) or not content:
                raise ValueError("Missing completion content")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderFailure(ErrorCode.INVALID_OUTPUT) from exc

        return ProviderCompletion(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._settings.openai_compat_model,
            source="main",
            latency_ms=(perf_counter() - started) * 1000,
        )

    @staticmethod
    def _nonnegative_int(value: object) -> int:
        return value if isinstance(value, int) and value >= 0 else 0

    @staticmethod
    def _retry_after(response: httpx.Response) -> int | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(1, min(3600, int(value)))
        except ValueError:
            return None
