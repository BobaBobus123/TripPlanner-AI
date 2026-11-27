import logging
import re
from uuid import uuid4

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tripplanner.config import Settings
from tripplanner.errors import (
    ErrorCode,
    ProviderFailure,
    TripPlannerError,
    error_response,
)
from tripplanner.models import PlanRequest, PlanResponse
from tripplanner.providers.mock import MockProvider
from tripplanner.services.plans import PlanService
from tripplanner.storage.memory import InMemoryPlanRepository
from tripplanner.ui import index_page

logger = logging.getLogger("tripplanner")
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
SAFE_ERROR_FIELDS = {
    "destination",
    "start_date",
    "end_date",
    "currency",
    "budget",
    "traveler_count",
    "interests",
    "owner_id",
    "plan_id",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title="TripPlanner AI", version="0.1.0")
    provider = MockProvider(app_settings)
    repository = InMemoryPlanRepository()
    service = PlanService(provider, repository)
    app.state.settings = app_settings
    app.state.provider = provider
    app.state.repository = repository
    app.state.plan_service = service

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        candidate = request.headers.get("X-Request-ID", "")
        request_id = candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = sorted(
            {
                str(part)
                for error in exc.errors()
                for part in error["loc"]
                if part in SAFE_ERROR_FIELDS
            }
        )
        if not fields:
            fields = ["request"]
        return error_response(request, ErrorCode.INVALID_REQUEST, fields=fields)

    @app.exception_handler(TripPlannerError)
    async def tripplanner_error_handler(
        request: Request, exc: TripPlannerError
    ) -> JSONResponse:
        return error_response(request, exc.code, retry_after=exc.retry_after)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled request failure",
            extra={
                "request_id": request.state.request_id,
                "exception_type": type(exc).__name__,
            },
        )
        return error_response(request, ErrorCode.INTERNAL)

    @app.get("/", include_in_schema=False)
    async def home():
        return index_page()

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "checks": {
                "storage": app_settings.storage_backend,
                "provider": app_settings.provider,
            },
        }

    @app.get("/health/live", include_in_schema=False)
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness():
        return {"status": "ready", "storage": app_settings.storage_backend}

    @app.post("/api/v1/plans", response_model=PlanResponse, status_code=201)
    async def create_plan(
        payload: PlanRequest,
        owner_id: str = Header(alias="X-Owner-ID", min_length=1, max_length=128),
    ) -> PlanResponse:
        return await service.create(owner_id, payload)

    @app.get("/api/v1/plans/{plan_id}", response_model=PlanResponse)
    async def get_plan(
        plan_id: str,
        owner_id: str = Header(alias="X-Owner-ID", min_length=1, max_length=128),
    ) -> PlanResponse:
        return service.get(owner_id, plan_id)

    return app


app = create_app()
