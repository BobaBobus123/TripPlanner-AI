import asyncio
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse

from tripplanner.ai.budget import DailyBudget
from tripplanner.ai.orchestrator import PlanOrchestrator
from tripplanner.auth import AuthService, auth_attempt_key, require_user
from tripplanner.config import Settings
from tripplanner.email import (
    DevelopmentVerificationMailer,
    SMTPVerificationMailer,
    VerificationMailer,
)
from tripplanner.errors import ErrorCode, TripPlannerError, error_response
from tripplanner.models import (
    JobCreatedResponse,
    JobEnvelope,
    JobListResponse,
    LoginRequest,
    PlanRequest,
    ProviderModeRequest,
    RegisterRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from tripplanner.providers.factory import create_provider
from tripplanner.storage.postgres import PostgresDatabase, initialize_schema
from tripplanner.storage.store import (
    MemoryTripPlannerStore,
    PostgresTripPlannerStore,
    TripPlannerStore,
)
from tripplanner.storage.sqlite_store import SQLiteTripPlannerStore
from tripplanner.ui import index_page
from tripplanner.worker import JobWorker

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
    "plan_id",
}
TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


def create_app(
    settings: Settings | None = None,
    store: TripPlannerStore | None = None,
    email_sender: VerificationMailer | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    database = (
        PostgresDatabase(app_settings)
        if app_settings.storage_backend == "postgres"
        else None
    )
    repository = store or (
        PostgresTripPlannerStore(database)
        if database
        else (
            SQLiteTripPlannerStore(app_settings.sqlite_path)
            if app_settings.storage_backend == "sqlite"
            else MemoryTripPlannerStore()
        )
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        worker_task: asyncio.Task[None] | None = None
        try:
            if database is not None:
                await database.open()
                await initialize_schema(database)
            elif isinstance(repository, SQLiteTripPlannerStore):
                await repository.initialize()
            await repository.initialize_provider_mode(app_settings.provider)
            if app_settings.storage_backend in {"memory", "sqlite"}:
                worker = JobWorker(
                    repository,
                    orchestrator,
                    app_settings,
                    orchestrators=orchestrators,
                )
                worker_task = asyncio.create_task(worker.run())
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                await asyncio.gather(worker_task, return_exceptions=True)
            if database is not None:
                await database.close()
            elif isinstance(repository, SQLiteTripPlannerStore):
                await repository.close()

    app = FastAPI(
        title="TripPlanner AI — планування подорожей",
        description="Сервіс облікових записів, збережених подорожей і планування маршрутів.",
        version="0.2.0",
        lifespan=lifespan,
    )
    providers = {
        mode: create_provider(app_settings, mode)
        for mode in ("mock", "openai_compat")
    }
    provider = providers[app_settings.provider]
    daily_budget = DailyBudget(app_settings)
    orchestrators = {
        mode: PlanOrchestrator(selected_provider, app_settings, daily_budget)
        for mode, selected_provider in providers.items()
    }
    orchestrator = orchestrators[app_settings.provider]
    app.state.settings = app_settings
    app.state.provider = provider
    app.state.providers = providers
    app.state.plan_orchestrators = orchestrators
    app.state.database = database
    app.state.store = repository
    app.state.auth_service = AuthService(repository, app_settings)
    app.state.email_sender = email_sender or (
        SMTPVerificationMailer(app_settings)
        if app_settings.email_backend == "smtp"
        else DevelopmentVerificationMailer()
    )
    app.state.plan_orchestrator = orchestrator

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        candidate = request.headers.get("X-Request-ID", "")
        request_id = candidate if REQUEST_ID_PATTERN.fullmatch(candidate) else str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Referrer-Policy"] = "no-referrer"
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
        return error_response(
            request, ErrorCode.INVALID_REQUEST, fields=fields or ["request"]
        )

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

    @app.get("/login", include_in_schema=False)
    @app.get("/register", include_in_schema=False)
    @app.get("/verify-email", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    @app.get("/trips", include_in_schema=False)
    @app.get("/new", include_in_schema=False)
    async def ui_page():
        return index_page()

    @app.get("/trips/{job_id:uuid}", include_in_schema=False)
    async def trip_page(job_id: UUID):
        return index_page()

    @app.get("/health", summary="Перевірити стан сервісу")
    async def health():
        mode = await repository.get_provider_mode(app_settings.provider)
        return {
            "status": "ok",
            "checks": {
                "storage": app_settings.storage_backend,
                "provider": mode,
                "ai_mode": "demo" if mode == "mock" else "live",
                "model": (
                    app_settings.openai_compat_model
                    if mode == "openai_compat"
                    else None
                ),
            },
        }

    @app.get("/health/live", include_in_schema=False)
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness():
        if database is not None:
            await database.health_check()
        return {"status": "ready", "storage": app_settings.storage_backend}

    def set_session_cookie(response: Response, token: str) -> None:
        secure = (
            app_settings.session_cookie_secure
            if app_settings.session_cookie_secure is not None
            else app_settings.app_env == "production"
        )
        response.set_cookie(
            "tripplanner_session",
            token,
            max_age=app_settings.session_ttl_hours * 3600,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )

    def make_verification_url(token: str) -> str:
        if app_settings.email_backend == "development":
            return f"/verify-email#token={quote(token, safe='')}"
        base_url = str(app_settings.public_base_url).rstrip("/")
        return f"{base_url}/verify-email#token={quote(token, safe='')}"

    async def send_verification(user: dict[str, Any]) -> str | None:
        token = await app.state.auth_service.issue_email_verification(user["id"])
        verification_url = make_verification_url(token)
        await app.state.email_sender.send_verification(user["email"], verification_url)
        if app_settings.email_backend == "development":
            return verification_url
        return None

    @app.post("/api/v1/auth/register", status_code=201, summary="Створити обліковий запис")
    async def register(payload: RegisterRequest, request: Request):
        app.state.auth_service.validate_origin(request)
        client_ip = request.client.host if request.client else "unknown"
        attempt_key = auth_attempt_key("register", client_ip)
        if not await repository.record_login_attempt(attempt_key, 900, 10):
            raise TripPlannerError(ErrorCode.RATE_LIMITED, retry_after=900)
        await app.state.auth_service.register(payload.email, payload.password)
        return {
            "message": "Обліковий запис створено. Тепер можна увійти.",
        }

    @app.post(
        "/api/v1/auth/verify-email",
        summary="Підтвердити електронну пошту",
    )
    async def verify_email(payload: VerifyEmailRequest, request: Request):
        app.state.auth_service.validate_origin(request)
        user = await app.state.auth_service.verify_email(payload.token)
        if user is None:
            raise TripPlannerError(ErrorCode.INVALID_VERIFICATION_TOKEN)
        return {"message": "Електронну пошту підтверджено. Тепер можна увійти."}

    @app.post(
        "/api/v1/auth/resend-verification",
        summary="Повторно надіслати лист підтвердження",
    )
    async def resend_verification(
        payload: ResendVerificationRequest,
        request: Request,
    ):
        app.state.auth_service.validate_origin(request)
        client_ip = request.client.host if request.client else "unknown"
        attempt_key = auth_attempt_key(
            "resend-verification",
            f"{client_ip}:{payload.email}",
        )
        if not await repository.record_login_attempt(attempt_key, 900, 3):
            raise TripPlannerError(ErrorCode.RATE_LIMITED, retry_after=900)
        user = await repository.get_user_by_email(payload.email)
        verification_url = None
        if user is not None and not user.get("email_verified", False):
            verification_url = await send_verification(user)
        return {
            "message": "Якщо для цієї адреси є непідтверджений обліковий запис, ми надіслали лист.",
            "verification_url": verification_url,
            "development_only": app_settings.email_backend == "development",
        }

    @app.post("/api/v1/auth/login", summary="Увійти до облікового запису")
    async def login(payload: LoginRequest, request: Request, response: Response):
        app.state.auth_service.validate_origin(request)
        client_ip = request.client.host if request.client else "unknown"
        attempt_key = auth_attempt_key("login", client_ip)
        user, token, csrf_token = await app.state.auth_service.login(
            payload.email, payload.password, attempt_key
        )
        set_session_cookie(response, token)
        return {"user": {"id": user["id"], "email": user["email"]}, "csrf_token": csrf_token}

    @app.get("/api/v1/auth/me", summary="Перевірити активний обліковий запис")
    async def current_user(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return {
            "user": {"id": user["id"], "email": user["email"]},
            "csrf_token": user["csrf_token"],
        }

    @app.post("/api/v1/auth/logout", status_code=204, summary="Вийти з облікового запису")
    async def logout(
        request: Request,
        response: Response,
        _: dict[str, Any] = Depends(require_user),
    ) -> None:
        await app.state.auth_service.logout(request)
        response.delete_cookie(
            "tripplanner_session",
            path="/",
            httponly=True,
            secure=(
                app_settings.session_cookie_secure
                if app_settings.session_cookie_secure is not None
                else app_settings.app_env == "production"
            ),
            samesite="lax",
        )

    def is_app_admin(user: dict[str, Any]) -> bool:
        return bool(
            app_settings.app_admin_email
            and user.get("email", "").strip().lower() == app_settings.app_admin_email
        )

    def provider_settings(mode: str, user: dict[str, Any]) -> dict[str, Any]:
        available_modes = ["mock"]
        if app_settings.openai_compat_available:
            available_modes.append("openai_compat")
        return {
            "mode": mode,
            "available_modes": available_modes,
            "is_admin": is_app_admin(user),
            "admin_configured": app_settings.app_admin_email is not None,
            "model": (
                app_settings.openai_compat_model
                if "openai_compat" in available_modes
                else None
            ),
        }

    @app.get("/api/v1/settings/provider", summary="Перевірити режим AI-провайдера")
    async def get_provider_settings(
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        mode = await repository.get_provider_mode(app_settings.provider)
        return provider_settings(mode, user)

    @app.put("/api/v1/settings/provider", summary="Змінити глобальний режим AI")
    async def update_provider_settings(
        payload: ProviderModeRequest,
        user: dict[str, Any] = Depends(require_user),
    ) -> dict[str, Any]:
        if not is_app_admin(user):
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        if (
            payload.mode == "openai_compat"
            and not app_settings.openai_compat_available
        ):
            raise TripPlannerError(ErrorCode.PROVIDER_UNAVAILABLE)
        await repository.set_provider_mode(payload.mode)
        return provider_settings(payload.mode, user)

    @app.post(
        "/api/v1/jobs",
        status_code=202,
        response_model=JobCreatedResponse,
        summary="Поставити створення плану в чергу",
    )
    async def create_job(
        payload: PlanRequest,
        response: Response,
        user: dict[str, Any] = Depends(require_user),
        idempotency_key: str | None = Header(
            default=None, alias="Idempotency-Key", min_length=1, max_length=128
        ),
    ) -> dict[str, Any]:
        key = idempotency_key or str(uuid4())
        provider_mode = await repository.get_provider_mode(app_settings.provider)
        if (
            provider_mode == "openai_compat"
            and not app_settings.openai_compat_available
        ):
            raise TripPlannerError(ErrorCode.PROVIDER_UNAVAILABLE)
        normalized = payload.model_dump(mode="json")
        normalized["_provider_mode"] = provider_mode
        fingerprint_payload = {
            "request": payload.model_dump(mode="json"),
            "provider_mode": provider_mode,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                fingerprint_payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        job, created = await repository.enqueue_job(
            user["id"], normalized, fingerprint, key
        )
        response.headers["Location"] = f"/api/v1/jobs/{job['id']}"
        return {"job": serialize_job(job), "created": created}

    @app.get(
        "/api/v1/jobs",
        response_model=JobListResponse,
        summary="Отримати список подорожей",
    )
    async def list_jobs(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        return {"jobs": [serialize_job(job) for job in await repository.list_jobs(user["id"])]}

    @app.get(
        "/api/v1/jobs/{job_id}",
        response_model=JobEnvelope,
        summary="Перевірити стан створення плану",
    )
    async def get_job(
        job_id: UUID, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        job = await repository.get_job(str(job_id), user["id"])
        if job is None:
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        return {"job": serialize_job(job)}

    @app.post(
        "/api/v1/jobs/{job_id}/cancel",
        response_model=JobEnvelope,
        summary="Скасувати створення плану",
    )
    async def cancel_job(
        job_id: UUID, user: dict[str, Any] = Depends(require_user)
    ) -> dict[str, Any]:
        job = await repository.request_cancel(str(job_id), user["id"])
        if job is None:
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        return {"job": serialize_job(job)}

    @app.get("/api/v1/jobs/{job_id}/events", summary="Отримувати оновлення виконання плану")
    async def stream_job_events(
        job_id: UUID,
        request: Request,
        user: dict[str, Any] = Depends(require_user),
        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
        after_id: int = 0,
    ):
        job_id = str(job_id)
        job = await repository.get_job(job_id, user["id"])
        if job is None:
            raise TripPlannerError(ErrorCode.NOT_FOUND)
        try:
            cursor = max(after_id, int(last_event_id or 0))
        except ValueError:
            cursor = after_id

        async def events() -> AsyncIterator[str]:
            nonlocal cursor
            last_heartbeat = asyncio.get_running_loop().time()
            while True:
                if await request.is_disconnected():
                    return
                batch = await repository.get_job_events(job_id, cursor)
                for event in batch:
                    cursor = event["id"]
                    data = json.dumps(
                        {
                            "status": event["status"],
                            "message": event["message"],
                            "created_at": event["created_at"].isoformat(),
                        },
                        ensure_ascii=False,
                    )
                    yield f"id: {cursor}\nevent: progress\ndata: {data}\n\n"
                current = await repository.get_job(job_id, user["id"])
                if current is None or (
                    current["status"] in TERMINAL_JOB_STATUSES
                    and cursor >= current["latest_event_id"]
                ):
                    return
                now = asyncio.get_running_loop().time()
                if now - last_heartbeat >= 15:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now
                await asyncio.sleep(1)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def serialize_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(job["id"]),
        "destination": job["request_json"]["destination"],
        "start_date": job["request_json"]["start_date"],
        "end_date": job["request_json"]["end_date"],
        "provider_mode": job["request_json"].get("_provider_mode", "mock"),
        "status": job["status"],
        "message": job["stage_message"],
        "error_code": job["error_code"],
        "created_at": job["created_at"].isoformat(),
        "updated_at": job["updated_at"].isoformat(),
        "latest_event_id": job["latest_event_id"],
        "plan": job["plan_json"],
    }


app = create_app()
