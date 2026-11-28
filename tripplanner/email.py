import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from tripplanner.config import Settings
from tripplanner.errors import ErrorCode, TripPlannerError


class VerificationMailer(Protocol):
    async def send_verification(self, email: str, verification_url: str) -> None: ...


class DevelopmentVerificationMailer:
    async def send_verification(self, email: str, verification_url: str) -> None:
        del email, verification_url


class SMTPVerificationMailer:
    def __init__(self, settings: Settings) -> None:
        if not settings.smtp_host or not settings.email_from:
            raise ValueError("SMTP settings were not validated")
        self._settings = settings
        self._smtp_host = settings.smtp_host
        self._email_from = settings.email_from

    async def send_verification(self, email: str, verification_url: str) -> None:
        try:
            await asyncio.to_thread(self._send_sync, email, verification_url)
        except (OSError, smtplib.SMTPException) as exc:
            raise TripPlannerError(ErrorCode.EMAIL_DELIVERY_FAILED) from exc

    def _send_sync(self, email: str, verification_url: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Підтвердження електронної пошти — TripPlanner AI"
        message["From"] = self._email_from
        message["To"] = email
        message.set_content(
            "Вітаємо!\n\n"
            "Щоб підтвердити електронну пошту для TripPlanner AI, відкрийте посилання:\n"
            f"{verification_url}\n\n"
            f"Посилання діє {self._settings.email_verification_ttl_minutes} хвилин. "
            "Якщо ви не створювали обліковий запис, проігноруйте цей лист."
        )

        with smtplib.SMTP(
            self._smtp_host,
            self._settings.smtp_port,
            timeout=15,
        ) as client:
            client.ehlo()
            if self._settings.smtp_starttls:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if self._settings.smtp_username and self._settings.smtp_password:
                client.login(
                    self._settings.smtp_username,
                    self._settings.smtp_password.get_secret_value(),
                )
            client.send_message(message)
