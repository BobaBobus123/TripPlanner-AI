import hashlib
import json
from json import JSONDecodeError
from pathlib import Path
from threading import Lock

from tripplanner.errors import ErrorCode, ProviderFailure
from tripplanner.models import PlanRequest
from tripplanner.providers.base import PlanProvider, ProviderCompletion


class RecordedProvider:
    def __init__(
        self,
        provider: PlanProvider,
        path: str | Path,
        mode: str,
        fingerprint: str = "",
    ) -> None:
        if mode not in {"replay", "record", "passthrough"}:
            raise ValueError("RecordedProvider mode must be replay, record, or passthrough")
        self._provider = provider
        self._path = Path(path)
        self._mode = mode
        self._fingerprint = fingerprint
        self._lock = Lock()

    async def generate(self, request: PlanRequest, prompt: str) -> ProviderCompletion:
        if self._mode == "passthrough":
            return await self._provider.generate(request, prompt)

        key = self._key(request, prompt, self._fingerprint)
        if self._mode == "replay":
            completion = self._read(key)
            return ProviderCompletion(
                content=completion.content,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
                model=completion.model,
                source="recorded",
                latency_ms=completion.latency_ms,
            )

        completion = await self._provider.generate(request, prompt)
        self._append(key, completion)
        return completion

    @staticmethod
    def _key(request: PlanRequest, prompt: str, fingerprint: str) -> str:
        canonical = json.dumps(
            {
                "request": request.model_dump(mode="json"),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "fingerprint": fingerprint,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _read(self, key: str) -> ProviderCompletion:
        with self._lock:
            if not self._path.exists():
                raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)
            try:
                for line in self._path.read_text(encoding="utf-8").splitlines():
                    record = json.loads(line)
                    if record.get("key") == key:
                        value = record["completion"]
                        return ProviderCompletion(**value, source="recorded")
            except (JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ProviderFailure(ErrorCode.INVALID_OUTPUT) from exc
        raise ProviderFailure(ErrorCode.PROVIDER_UNAVAILABLE)

    def _append(self, key: str, completion: ProviderCompletion) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "key": key,
            "completion": {
                "content": completion.content,
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "model": completion.model,
                "latency_ms": completion.latency_ms,
            },
        }
        with self._lock, self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
