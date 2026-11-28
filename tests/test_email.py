import asyncio
import smtplib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tripplanner.auth import hash_token
from tripplanner.config import Settings
from tripplanner.email import SMTPVerificationMailer
from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.main import create_app


class CapturingMailer:
    def __init__(self) -> None:
        self.recipient = ""
        self.url = ""

    async def send_verification(self, email: str, verification_url: str) -> None:
        self.recipient = email
        self.url = verification_url


def test_smtp_mailer_sends_expiring_link_over_starttls(monkeypatch) -> None:
    sent = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            sent["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def ehlo(self) -> None:
            sent["ehlo"] = True

        def starttls(self, context) -> None:
            sent["starttls"] = context

        def login(self, username: str, password: str) -> None:
            sent["login"] = (username, password)

        def send_message(self, message) -> None:
            sent["message"] = message

    monkeypatch.setattr("tripplanner.email.smtplib.SMTP", FakeSMTP)
    settings = Settings(
        email_backend="smtp",
        email_from="TripPlanner <no-reply@example.com>",
        smtp_host="smtp.example.com",
        smtp_username="smtp-user",
        smtp_password="smtp-secret",
        email_verification_ttl_minutes=45,
    )

    asyncio.run(
        SMTPVerificationMailer(settings).send_verification(
            "traveler@example.com",
            "https://trips.example.com/verify-email#token=one-time-token",
        )
    )

    assert sent["connection"] == ("smtp.example.com", 587, 15)
    assert sent["login"] == ("smtp-user", "smtp-secret")
    assert sent["starttls"]
    assert sent["message"]["To"] == "traveler@example.com"
    assert "45 хвилин" in sent["message"].get_content()
    assert "one-time-token" in sent["message"].get_content()


def test_smtp_failure_is_mapped_without_exposing_provider_details(monkeypatch) -> None:
    class FailingSMTP:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def ehlo(self) -> None:
            pass

        def starttls(self, **_kwargs) -> None:
            pass

        def send_message(self, _message) -> None:
            raise smtplib.SMTPException("private smtp diagnostic")

    monkeypatch.setattr("tripplanner.email.smtplib.SMTP", FailingSMTP)
    settings = Settings(
        email_backend="smtp",
        email_from="no-reply@example.com",
        smtp_host="smtp.example.com",
    )

    with pytest.raises(TripPlannerError) as error:
        asyncio.run(
            SMTPVerificationMailer(settings).send_verification(
                "traveler@example.com",
                "https://trips.example.com/verify-email#token=secret",
            )
        )

    assert error.value.code == ErrorCode.EMAIL_DELIVERY_FAILED
    assert "private smtp diagnostic" not in str(error.value)
    assert "secret" not in str(error.value)


def test_expired_email_verification_token_is_rejected() -> None:
    app = create_app()
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )
        assert registration.status_code == 201
        user = asyncio.run(app.state.store.get_user_by_email("traveler@example.com"))
        expired_token = "expired-verification-token-value-123456"
        asyncio.run(
            app.state.store.create_email_verification(
                user["id"],
                hash_token(expired_token),
                datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        expired = client.post(
            "/api/v1/auth/verify-email",
            json={"token": expired_token},
        )
        valid_token = "valid-verification-token-value-123456"
        asyncio.run(
            app.state.store.create_email_verification(
                user["id"],
                hash_token(valid_token),
                datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        )
        verified = client.post(
            "/api/v1/auth/verify-email",
            json={"token": valid_token},
        )
        replay = client.post("/api/v1/auth/verify-email", json={"token": valid_token})

    assert expired.status_code == replay.status_code == 400
    assert verified.status_code == 200
    assert expired.json()["error"]["code"] == "invalid_verification_token"
    assert replay.json()["error"]["code"] == "invalid_verification_token"


def test_production_requires_postgres_and_smtp_uses_https() -> None:
    with pytest.raises(ValidationError, match="STORAGE_BACKEND=postgres is required"):
        Settings(app_env="production")

    with pytest.raises(ValidationError, match="PUBLIC_BASE_URL must use HTTPS"):
        Settings(
            app_env="production",
            storage_backend="postgres",
            database_url="postgresql://user:password@localhost/tripplanner",
            email_backend="smtp",
            email_from="no-reply@example.com",
            smtp_host="smtp.example.com",
        )


def test_standard_registration_does_not_send_email() -> None:
    mailer = CapturingMailer()
    settings = Settings(
        email_backend="smtp",
        email_from="no-reply@example.com",
        smtp_host="smtp.example.com",
    )
    with TestClient(create_app(settings, email_sender=mailer)) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )

    assert response.status_code == 201
    assert "verification_url" not in response.json()
    assert login.status_code == 200
    assert mailer.recipient == ""
