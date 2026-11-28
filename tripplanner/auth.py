import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from typing import Any
from urllib.parse import urlsplit

from fastapi import Request
from pwdlib import PasswordHash

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.storage.store import TripPlannerStore

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("constant timing-only password")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def auth_attempt_key(scope: str, client_ip: str) -> str:
    return hashlib.sha256(f"{scope}:{client_ip}".encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, store: TripPlannerStore, settings: Settings) -> None:
        self._store = store
        self._settings = settings

    async def register(self, email: str, password: str) -> dict[str, Any]:
        user = await self._store.register_user(email, password_hash.hash(password))
        if user is None:
            raise TripPlannerError(ErrorCode.ACCOUNT_EXISTS)
        return user

    async def issue_email_verification(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self._settings.email_verification_ttl_minutes
        )
        await self._store.create_email_verification(
            user_id,
            hash_token(token),
            expires_at,
        )
        return token

    async def verify_email(self, token: str) -> dict[str, Any] | None:
        return await self._store.verify_email_token(hash_token(token))

    async def login(
        self, email: str, password: str, attempt_key: str
    ) -> tuple[dict[str, Any], str, str]:
        if not await self._store.record_login_attempt(attempt_key, 900, 10):
            raise TripPlannerError(ErrorCode.RATE_LIMITED, retry_after=900)
        user = await self._store.get_user_by_email(email)
        stored_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
        valid_password = password_hash.verify(password, stored_hash)
        if user is None or not valid_password:
            raise TripPlannerError(ErrorCode.UNAUTHORIZED)
        if not user.get("email_verified", False):
            raise TripPlannerError(ErrorCode.EMAIL_NOT_VERIFIED)
        await self._store.clear_login_attempts(attempt_key)
        return user, *(await self._create_session(user["id"]))

    async def authenticate(self, request: Request) -> dict[str, Any]:
        token = request.cookies.get("tripplanner_session")
        session = await self._store.get_session(hash_token(token)) if token else None
        if session is None:
            raise TripPlannerError(ErrorCode.UNAUTHORIZED)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.validate_origin(request)
            csrf_token = request.headers.get("X-CSRF-Token", "")
            if not csrf_token or not compare_digest(csrf_token, session["csrf_token"]):
                raise TripPlannerError(ErrorCode.UNAUTHORIZED)
        user = await self._store.get_user_by_id(session["user_id"])
        if user is None or not user.get("email_verified", False):
            raise TripPlannerError(ErrorCode.UNAUTHORIZED)
        return {**user, "csrf_token": session["csrf_token"]}

    @staticmethod
    def validate_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin is None:
            return
        try:
            parsed_origin = urlsplit(origin)
            origin_host = parsed_origin.netloc
        except ValueError as exc:
            raise TripPlannerError(ErrorCode.UNAUTHORIZED) from exc
        if (
            parsed_origin.scheme not in {"http", "https"}
            or not compare_digest(origin_host, request.url.netloc)
            or parsed_origin.path not in {"", "/"}
        ):
            raise TripPlannerError(ErrorCode.UNAUTHORIZED)

    async def logout(self, request: Request) -> None:
        token = request.cookies.get("tripplanner_session")
        if token:
            await self._store.delete_session(hash_token(token))

    async def _create_session(self, user_id: str) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self._settings.session_ttl_hours
        )
        await self._store.create_session(
            hash_token(token),
            user_id,
            csrf_token,
            expires_at,
        )
        return token, csrf_token


async def require_user(request: Request) -> dict[str, Any]:
    return await request.app.state.auth_service.authenticate(request)
