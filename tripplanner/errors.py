from enum import StrEnum

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    INVALID_OUTPUT = "invalid_output"
    DAILY_BUDGET_EXCEEDED = "daily_budget_exceeded"
    INTERNAL = "internal"


ERROR_CATALOG: dict[ErrorCode, tuple[int, str, bool]] = {
    ErrorCode.INVALID_REQUEST: (422, "Request validation failed.", False),
    ErrorCode.NOT_FOUND: (404, "The requested resource was not found.", False),
    ErrorCode.RATE_LIMITED: (429, "The service is temporarily rate limited.", True),
    ErrorCode.PROVIDER_UNAVAILABLE: (503, "The planning service is temporarily unavailable.", True),
    ErrorCode.PROVIDER_TIMEOUT: (504, "The planning service timed out.", True),
    ErrorCode.INVALID_OUTPUT: (502, "The planning service returned an invalid result.", False),
    ErrorCode.DAILY_BUDGET_EXCEEDED: (429, "The daily AI budget has been reached.", True),
    ErrorCode.INTERNAL: (500, "An unexpected error occurred.", False),
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
