from enum import StrEnum

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    EMAIL_NOT_VERIFIED = "email_not_verified"
    INVALID_VERIFICATION_TOKEN = "invalid_verification_token"
    EMAIL_DELIVERY_FAILED = "email_delivery_failed"
    ACCOUNT_EXISTS = "account_exists"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    INVALID_OUTPUT = "invalid_output"
    DAILY_BUDGET_EXCEEDED = "daily_budget_exceeded"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    INTERNAL = "internal"


ERROR_CATALOG: dict[ErrorCode, tuple[int, str, bool]] = {
    ErrorCode.INVALID_REQUEST: (422, "Не вдалося перевірити дані запиту.", False),
    ErrorCode.UNAUTHORIZED: (401, "Потрібно увійти або повторно авторизуватися.", False),
    ErrorCode.EMAIL_NOT_VERIFIED: (
        403,
        "Підтвердіть електронну пошту за посиланням із листа.",
        False,
    ),
    ErrorCode.INVALID_VERIFICATION_TOKEN: (
        400,
        "Посилання недійсне або застаріло. Запросіть новий лист.",
        False,
    ),
    ErrorCode.EMAIL_DELIVERY_FAILED: (
        503,
        "Не вдалося надіслати лист. Спробуйте повторно трохи пізніше.",
        True,
    ),
    ErrorCode.ACCOUNT_EXISTS: (409, "Не вдалося створити обліковий запис із цими даними.", False),
    ErrorCode.NOT_FOUND: (404, "Запитаний ресурс не знайдено.", False),
    ErrorCode.RATE_LIMITED: (429, "Тимчасово перевищено ліміт запитів.", True),
    ErrorCode.PROVIDER_UNAVAILABLE: (
        503,
        "Сервіс планування тимчасово недоступний.",
        True,
    ),
    ErrorCode.PROVIDER_TIMEOUT: (504, "Час очікування відповіді сервісу вичерпано.", True),
    ErrorCode.INVALID_OUTPUT: (
        502,
        "Сервіс планування повернув некоректний результат.",
        False,
    ),
    ErrorCode.DAILY_BUDGET_EXCEEDED: (429, "Денний бюджет на AI вичерпано.", True),
    ErrorCode.IDEMPOTENCY_CONFLICT: (
        409,
        "Ключ ідемпотентності вже використано з іншими даними.",
        False,
    ),
    ErrorCode.INTERNAL: (500, "Сталася неочікувана помилка.", False),
}


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    retryable: bool
    retry_after: int | None = None
    request_id: str
    fields: list[str] | None = None


class TripPlannerError(Exception):
    def __init__(self, code: ErrorCode, retry_after: int | None = None) -> None:
        self.code = code
        self.retry_after = retry_after
        super().__init__(code.value)


class ProviderFailure(TripPlannerError):
    pass


def error_response(
    request: Request,
    code: ErrorCode,
    *,
    fields: list[str] | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    status_code, message, retryable = ERROR_CATALOG[code]
    body = ErrorResponse(
        code=code,
        message=message,
        retryable=retryable,
        retry_after=retry_after,
        request_id=request.state.request_id,
        fields=fields,
    )
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(
        status_code=status_code,
        content={"error": body.model_dump(mode="json", exclude_none=True)},
        headers=headers,
    )
