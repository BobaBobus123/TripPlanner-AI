from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4

from psycopg.types.json import Jsonb

from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.storage.postgres import PostgresDatabase

TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


class TripPlannerStore(Protocol):
    async def initialize_provider_mode(self, default: str) -> None: ...

    async def get_provider_mode(self, default: str) -> str: ...

    async def set_provider_mode(self, mode: str) -> None: ...

    async def register_user(self, email: str, password_hash: str) -> dict[str, Any] | None: ...

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None: ...

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None: ...

    async def create_email_verification(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None: ...

    async def verify_email_token(self, token_hash: str) -> dict[str, Any] | None: ...

    async def record_login_attempt(
        self, attempt_key: str, window_seconds: int, maximum: int
    ) -> bool: ...

    async def clear_login_attempts(self, attempt_key: str) -> None: ...

    async def create_session(
        self, token_hash: str, user_id: str, csrf_token: str, expires_at: datetime
    ) -> None: ...

    async def get_session(self, token_hash: str) -> dict[str, Any] | None: ...

    async def delete_session(self, token_hash: str) -> None: ...

    async def enqueue_job(
        self, user_id: str, payload: dict[str, Any], fingerprint: str, key: str
    ) -> tuple[dict[str, Any], bool]: ...

    async def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None: ...

    async def list_jobs(self, user_id: str) -> list[dict[str, Any]]: ...

    async def get_job_events(self, job_id: str, after_id: int) -> list[dict[str, Any]]: ...

    async def claim_job(self, worker_id: str, lease_seconds: int) -> dict[str, Any] | None: ...

    async def update_job(
        self, job_id: str, status: str, message: str, *, error_code: str | None = None
    ) -> None: ...

    async def save_plan(self, job_id: str, user_id: str, plan: dict[str, Any]) -> None: ...

    async def request_cancel(self, job_id: str, user_id: str) -> dict[str, Any] | None: ...

    async def get_job_status(self, job_id: str) -> str | None: ...

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int) -> bool: ...


class MemoryTripPlannerStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._settings: dict[str, str] = {}
        self._users: dict[str, dict[str, Any]] = {}
        self._email_verification_tokens: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._login_attempts: dict[str, tuple[datetime, int]] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._plans: dict[str, dict[str, Any]] = {}
        self._next_event_id = 1

    async def initialize_provider_mode(self, default: str) -> None:
        with self._lock:
            self._settings.setdefault("provider_mode", default)

    async def get_provider_mode(self, default: str) -> str:
        with self._lock:
            return self._settings.get("provider_mode", default)

    async def set_provider_mode(self, mode: str) -> None:
        with self._lock:
            self._settings["provider_mode"] = mode

    async def register_user(self, email: str, password_hash: str) -> dict[str, Any] | None:
        with self._lock:
            if any(user["email"] == email for user in self._users.values()):
                return None
            user = {
                "id": str(uuid4()),
                "email": email,
                "password_hash": password_hash,
                "email_verified": False,
            }
            self._users[user["id"]] = user
            return dict(user)

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            return next(
                (dict(user) for user in self._users.values() if user["email"] == email),
                None,
            )

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            user = self._users.get(user_id)
            return dict(user) if user else None

    async def create_email_verification(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        with self._lock:
            if user_id not in self._users:
                return
            self._email_verification_tokens = {
                key: value
                for key, value in self._email_verification_tokens.items()
                if value["user_id"] != user_id
            }
            self._email_verification_tokens[token_hash] = {
                "user_id": user_id,
                "expires_at": expires_at,
            }

    async def verify_email_token(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock:
            token = self._email_verification_tokens.pop(token_hash, None)
            if token is None or token["expires_at"] <= datetime.now(timezone.utc):
                return None
            user = self._users.get(token["user_id"])
            if user is None:
                return None
            user["email_verified"] = True
            self._email_verification_tokens = {
                key: value
                for key, value in self._email_verification_tokens.items()
                if value["user_id"] != token["user_id"]
            }
            return {
                "id": user["id"],
                "email": user["email"],
                "email_verified": True,
            }

    async def record_login_attempt(
        self, attempt_key: str, window_seconds: int, maximum: int
    ) -> bool:
        with self._lock:
            now = datetime.now(timezone.utc)
            self._login_attempts = {
                key: value
                for key, value in self._login_attempts.items()
                if value[0] + timedelta(days=1) > now
            }
            window = self._login_attempts.get(attempt_key)
            if window is None or window[0] + timedelta(seconds=window_seconds) <= now:
                self._login_attempts[attempt_key] = (now, 1)
                return True
            attempts = window[1] + 1
            self._login_attempts[attempt_key] = (window[0], attempts)
            return attempts <= maximum

    async def clear_login_attempts(self, attempt_key: str) -> None:
        with self._lock:
            self._login_attempts.pop(attempt_key, None)

    async def create_session(
        self, token_hash: str, user_id: str, csrf_token: str, expires_at: datetime
    ) -> None:
        with self._lock:
            self._sessions[token_hash] = {
                "user_id": user_id,
                "csrf_token": csrf_token,
                "expires_at": expires_at,
            }

    async def get_session(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock:
            session = self._sessions.get(token_hash)
            if session is None:
                return None
            if session["expires_at"] <= datetime.now(timezone.utc):
                del self._sessions[token_hash]
                return None
            return dict(session)

    async def delete_session(self, token_hash: str) -> None:
        with self._lock:
            self._sessions.pop(token_hash, None)

    async def enqueue_job(
        self, user_id: str, payload: dict[str, Any], fingerprint: str, key: str
    ) -> tuple[dict[str, Any], bool]:
        with self._lock:
            identity = (user_id, key)
            existing_id = self._idempotency.get(identity)
            if existing_id is not None:
                existing = self._jobs[existing_id]
                if existing["request_fingerprint"] != fingerprint:
                    raise TripPlannerError(ErrorCode.IDEMPOTENCY_CONFLICT)
                return self._job_with_plan(existing_id), False
            now = datetime.now(timezone.utc)
            job = {
                "id": str(uuid4()),
                "user_id": user_id,
                "request_json": payload,
                "request_fingerprint": fingerprint,
                "idempotency_key": key,
                "status": "queued",
                "stage_message": "Запит прийнято. Очікуємо на обробку.",
                "error_code": None,
                "worker_id": None,
                "lease_until": None,
                "created_at": now,
                "updated_at": now,
            }
            self._jobs[job["id"]] = job
            self._idempotency[identity] = job["id"]
            self._events[job["id"]] = []
            self._append_event(job["id"], "queued", job["stage_message"])
            return self._job_with_plan(job["id"]), True

    async def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["user_id"] != user_id:
                return None
            return self._job_with_plan(job_id)

    async def list_jobs(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [
                self._job_with_plan(job_id)
                for job_id, job in self._jobs.items()
                if job["user_id"] == user_id
            ]
            return sorted(jobs, key=lambda job: job["created_at"], reverse=True)

    async def get_job_events(self, job_id: str, after_id: int) -> list[dict[str, Any]]:
        with self._lock:
            return [
                dict(event)
                for event in self._events.get(job_id, [])
                if event["id"] > after_id
            ]

    async def claim_job(self, worker_id: str, lease_seconds: int) -> dict[str, Any] | None:
        with self._lock:
            now = datetime.now(timezone.utc)
            for job in self._jobs.values():
                if (
                    job["status"] in {"preparing", "generating", "validating"}
                    and job["lease_until"] is not None
                    and job["lease_until"] <= now
                ):
                    self._update_job(job, "interrupted", "Обробку перервано. Створіть нову спробу.")
                elif (
                    job["status"] == "cancel_requested"
                    and job["lease_until"] is not None
                    and job["lease_until"] <= now
                ):
                    self._update_job(job, "cancelled", "Завдання скасовано.")
            job = next((item for item in self._jobs.values() if item["status"] == "queued"), None)
            if job is None:
                return None
            job["worker_id"] = worker_id
            job["lease_until"] = now + timedelta(seconds=lease_seconds)
            self._update_job(job, "preparing", "Перевіряємо параметри подорожі.")
            return self._job_with_plan(job["id"])

    async def update_job(
        self, job_id: str, status: str, message: str, *, error_code: str | None = None
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if (
                job is not None
                and job["status"] not in TERMINAL_JOB_STATUSES
                and not (job["status"] == "cancel_requested" and status != "cancelled")
            ):
                self._update_job(job, status, message, error_code=error_code)

    async def save_plan(self, job_id: str, user_id: str, plan: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job["user_id"] != user_id:
                raise TripPlannerError(ErrorCode.NOT_FOUND)
            if job["status"] == "cancel_requested":
                self._update_job(job, "cancelled", "Завдання скасовано.")
                return
            self._plans[job_id] = {"user_id": user_id, "plan_json": plan}
            self._update_job(job, "completed", "План готовий.")

    async def request_cancel(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["user_id"] != user_id:
                return None
            if job["status"] == "queued":
                self._update_job(job, "cancelled", "Завдання скасовано.")
            elif job["status"] in {"preparing", "generating", "validating"}:
                self._update_job(job, "cancel_requested", "Надіслано запит на скасування.")
            return self._job_with_plan(job_id)

    async def get_job_status(self, job_id: str) -> str | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job["status"] if job else None

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job["worker_id"] != worker_id:
                return False
            if job["status"] in TERMINAL_JOB_STATUSES or job["status"] == "cancel_requested":
                return False
            job["lease_until"] = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
            return True

    def _append_event(self, job_id: str, status: str, message: str) -> None:
        event = {
            "id": self._next_event_id,
            "job_id": job_id,
            "status": status,
            "message": message,
            "created_at": datetime.now(timezone.utc),
        }
        self._events[job_id].append(event)
        self._next_event_id += 1

    def _update_job(
        self, job: dict[str, Any], status: str, message: str, *, error_code: str | None = None
    ) -> None:
        job.update(
            status=status,
            stage_message=message,
            error_code=error_code,
            updated_at=datetime.now(timezone.utc),
        )
        self._append_event(job["id"], status, message)

    def _job_with_plan(self, job_id: str) -> dict[str, Any]:
        job = dict(self._jobs[job_id])
        plan = self._plans.get(job_id)
        job["plan_json"] = plan["plan_json"] if plan else None
        job["latest_event_id"] = (
            self._events[job_id][-1]["id"] if self._events[job_id] else 0
        )
        return job


class PostgresTripPlannerStore:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database

    async def initialize_provider_mode(self, default: str) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value)
                VALUES ('provider_mode', %s)
                ON CONFLICT (setting_key) DO NOTHING
                """,
                (default,),
            )

    async def get_provider_mode(self, default: str) -> str:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT setting_value FROM app_settings WHERE setting_key = 'provider_mode'"
                )
            ).fetchone()
        return row["setting_value"] if row else default

    async def set_provider_mode(self, mode: str) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value, updated_at)
                VALUES ('provider_mode', %s, now())
                ON CONFLICT (setting_key) DO UPDATE
                SET setting_value = EXCLUDED.setting_value, updated_at = now()
                """,
                (mode,),
            )

    async def register_user(self, email: str, password_hash: str) -> dict[str, Any] | None:
        from uuid import uuid4

        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    """
                    INSERT INTO users (id, email, password_hash, email_verified)
                    VALUES (%s, %s, %s, FALSE)
                    ON CONFLICT (email) DO NOTHING
                    RETURNING id, email, password_hash, email_verified
                    """,
                    (uuid4(), email, password_hash),
                )
            ).fetchone()
        return self._user_row(row) if row else None

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT id, email, password_hash, email_verified FROM users WHERE email = %s",
                    (email,),
                )
            ).fetchone()
        return self._user_row(row) if row else None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT id, email, email_verified FROM users WHERE id = %s::uuid",
                    (user_id,),
                )
            ).fetchone()
        return {**row, "id": str(row["id"])} if row else None

    async def create_email_verification(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                "DELETE FROM email_verification_tokens WHERE expires_at <= now()"
            )
            await connection.execute(
                """
                INSERT INTO email_verification_tokens (token_hash, user_id, expires_at)
                VALUES (%s, %s::uuid, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET token_hash = EXCLUDED.token_hash,
                    expires_at = EXCLUDED.expires_at,
                    created_at = now()
                """,
                (token_hash, user_id, expires_at),
            )

    async def verify_email_token(self, token_hash: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        """
                        DELETE FROM email_verification_tokens
                        WHERE token_hash = %s AND expires_at > now()
                        RETURNING user_id
                        """,
                        (token_hash,),
                    )
                ).fetchone()
                if row is None:
                    return None
                user = await (
                    await connection.execute(
                        """
                        UPDATE users SET email_verified = TRUE
                        WHERE id = %s::uuid
                        RETURNING id, email, email_verified
                        """,
                        (row["user_id"],),
                    )
                ).fetchone()
                await connection.execute(
                    "DELETE FROM email_verification_tokens WHERE user_id = %s::uuid",
                    (row["user_id"],),
                )
        return {**user, "id": str(user["id"])} if user else None

    async def record_login_attempt(
        self, attempt_key: str, window_seconds: int, maximum: int
    ) -> bool:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                "DELETE FROM login_attempts WHERE window_started_at < now() - interval '1 day'"
            )
            row = await (
                await connection.execute(
                    """
                    INSERT INTO login_attempts (attempt_key, window_started_at, attempts)
                    VALUES (%s, now(), 1)
                    ON CONFLICT (attempt_key) DO UPDATE SET
                        window_started_at = CASE
                            WHEN login_attempts.window_started_at
                                <= now() - (%s * interval '1 second')
                            THEN now() ELSE login_attempts.window_started_at END,
                        attempts = CASE
                            WHEN login_attempts.window_started_at
                                <= now() - (%s * interval '1 second')
                            THEN 1 ELSE login_attempts.attempts + 1 END
                    RETURNING attempts
                    """,
                    (attempt_key, window_seconds, window_seconds),
                )
            ).fetchone()
        return row["attempts"] <= maximum

    async def clear_login_attempts(self, attempt_key: str) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                "DELETE FROM login_attempts WHERE attempt_key = %s", (attempt_key,)
            )

    async def create_session(
        self, token_hash: str, user_id: str, csrf_token: str, expires_at: datetime
    ) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO sessions (token_hash, user_id, csrf_token, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (token_hash, user_id, csrf_token, expires_at),
            )

    async def get_session(self, token_hash: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    """
                    SELECT user_id, csrf_token, expires_at
                    FROM sessions WHERE token_hash = %s AND expires_at > now()
                    """,
                    (token_hash,),
                )
            ).fetchone()
        return dict(row) if row else None

    async def delete_session(self, token_hash: str) -> None:
        async with self._database.pool.connection() as connection:
            await connection.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))

    async def enqueue_job(
        self, user_id: str, payload: dict[str, Any], fingerprint: str, key: str
    ) -> tuple[dict[str, Any], bool]:
        from uuid import uuid4

        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        """
                        INSERT INTO jobs (
                            id, user_id, request_json, request_fingerprint,
                            idempotency_key, status, stage_message
                        )
                        VALUES (%s, %s, %s, %s, %s, 'queued', %s)
                        ON CONFLICT (user_id, idempotency_key) DO NOTHING
                        RETURNING *
                        """,
                        (
                            uuid4(),
                            user_id,
                            Jsonb(payload),
                            fingerprint,
                            key,
                            "Запит прийнято. Очікуємо на обробку.",
                        ),
                    )
                ).fetchone()
                created = row is not None
                if created:
                    await connection.execute(
                        "INSERT INTO job_events (job_id, status, message) VALUES (%s, %s, %s)",
                        (row["id"], "queued", row["stage_message"]),
                    )
                else:
                    row = await (
                        await connection.execute(
                            """
                            SELECT * FROM jobs
                            WHERE user_id = %s::uuid AND idempotency_key = %s
                            """,
                            (user_id, key),
                        )
                    ).fetchone()
                    if row["request_fingerprint"] != fingerprint:
                        raise TripPlannerError(ErrorCode.IDEMPOTENCY_CONFLICT)
                return await self._job_with_plan(connection, row), created

    async def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    """
                    SELECT j.*, p.plan_json,
                           COALESCE((SELECT max(id) FROM job_events WHERE job_id = j.id), 0)
                               AS latest_event_id
                    FROM jobs j LEFT JOIN plans p ON p.job_id = j.id
                    WHERE j.id = %s::uuid AND j.user_id = %s::uuid
                    """,
                    (job_id, user_id),
                )
            ).fetchone()
        return dict(row) if row else None

    async def list_jobs(self, user_id: str) -> list[dict[str, Any]]:
        async with self._database.pool.connection() as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT j.*, p.plan_json,
                           COALESCE((SELECT max(id) FROM job_events WHERE job_id = j.id), 0)
                               AS latest_event_id
                    FROM jobs j LEFT JOIN plans p ON p.job_id = j.id
                    WHERE j.user_id = %s::uuid ORDER BY j.created_at DESC LIMIT 100
                    """,
                    (user_id,),
                )
            ).fetchall()
        return [dict(row) for row in rows]

    async def get_job_events(self, job_id: str, after_id: int) -> list[dict[str, Any]]:
        async with self._database.pool.connection() as connection:
            rows = await (
                await connection.execute(
                    """
                    SELECT id, job_id, status, message, created_at
                    FROM job_events
                    WHERE job_id = %s::uuid AND id > %s
                    ORDER BY id
                    """,
                    (job_id, after_id),
                )
            ).fetchall()
        return [dict(row) for row in rows]

    async def claim_job(self, worker_id: str, lease_seconds: int) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                expired = await (
                    await connection.execute(
                        """
                        UPDATE jobs SET status = 'interrupted',
                            stage_message = 'Обробку перервано. Створіть нову спробу.',
                            error_code = 'worker_interrupted',
                            updated_at = now(), worker_id = NULL, lease_until = NULL
                        WHERE status IN ('preparing', 'generating', 'validating')
                          AND lease_until < now()
                        RETURNING id
                        """
                    )
                ).fetchall()
                for row in expired:
                    await connection.execute(
                        """
                        INSERT INTO job_events (job_id, status, message)
                        VALUES (%s, 'interrupted', %s)
                        """,
                        (row["id"], "Обробку перервано. Створіть нову спробу."),
                    )
                cancelled = await (
                    await connection.execute(
                        """
                        UPDATE jobs SET status = 'cancelled',
                            stage_message = 'Завдання скасовано.',
                            updated_at = now(), worker_id = NULL, lease_until = NULL
                        WHERE status = 'cancel_requested' AND lease_until < now()
                        RETURNING id
                        """
                    )
                ).fetchall()
                for row in cancelled:
                    await connection.execute(
                        """
                        INSERT INTO job_events (job_id, status, message)
                        VALUES (%s, 'cancelled', %s)
                        """,
                        (row["id"], "Завдання скасовано."),
                    )
                job = await (
                    await connection.execute(
                        """
                        SELECT * FROM jobs WHERE status = 'queued'
                        ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED
                        """
                    )
                ).fetchone()
                if job is None:
                    return None
                message = "Перевіряємо параметри подорожі."
                updated = await (
                    await connection.execute(
                        """
                        UPDATE jobs SET status = 'preparing', stage_message = %s,
                            worker_id = %s, lease_until = now() + (%s * interval '1 second'),
                            updated_at = now()
                        WHERE id = %s::uuid RETURNING *
                        """,
                        (message, worker_id, lease_seconds, job["id"]),
                    )
                ).fetchone()
                await connection.execute(
                    "INSERT INTO job_events (job_id, status, message) VALUES (%s, %s, %s)",
                    (job["id"], "preparing", message),
                )
                return await self._job_with_plan(connection, updated)

    async def update_job(
        self, job_id: str, status: str, message: str, *, error_code: str | None = None
    ) -> None:
        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        """
                        UPDATE jobs SET status = %s, stage_message = %s, error_code = %s,
                            updated_at = now(),
                            lease_until = CASE WHEN %s IN
                                ('completed', 'failed', 'cancelled', 'interrupted')
                                THEN NULL ELSE lease_until END
                        WHERE id = %s::uuid AND status NOT IN
                            ('completed', 'failed', 'cancelled', 'interrupted')
                          AND (status != 'cancel_requested' OR %s = 'cancelled')
                        RETURNING id
                        """,
                        (status, message, error_code, status, job_id, status),
                    )
                ).fetchone()
                if row:
                    await connection.execute(
                        "INSERT INTO job_events (job_id, status, message) VALUES (%s, %s, %s)",
                        (job_id, status, message),
                    )

    async def save_plan(self, job_id: str, user_id: str, plan: dict[str, Any]) -> None:
        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        "SELECT status, user_id FROM jobs WHERE id = %s::uuid FOR UPDATE",
                        (job_id,),
                    )
                ).fetchone()
                if row is None:
                    raise TripPlannerError(ErrorCode.NOT_FOUND)
                if str(row["user_id"]) != user_id:
                    raise TripPlannerError(ErrorCode.NOT_FOUND)
                if row["status"] == "cancel_requested":
                    message = "Завдання скасовано."
                    await connection.execute(
                        """
                        UPDATE jobs SET status = 'cancelled', stage_message = %s,
                            updated_at = now(), lease_until = NULL
                        WHERE id = %s::uuid
                        """,
                        (message, job_id),
                    )
                    await connection.execute(
                        "INSERT INTO job_events (job_id, status, message) VALUES (%s, 'cancelled', %s)",
                        (job_id, message),
                    )
                    return
                if row["status"] in TERMINAL_JOB_STATUSES:
                    return
                await connection.execute(
                    """
                    INSERT INTO plans (id, job_id, user_id, plan_json)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (job_id) DO NOTHING
                    """,
                    (plan["id"], job_id, row["user_id"], Jsonb(plan)),
                )
                message = "План готовий."
                await connection.execute(
                    """
                    UPDATE jobs SET status = 'completed', stage_message = %s,
                        updated_at = now(), lease_until = NULL
                    WHERE id = %s::uuid AND status != 'cancel_requested'
                    """,
                    (message, job_id),
                )
                await connection.execute(
                    """
                    INSERT INTO job_events (job_id, status, message)
                    SELECT %s::uuid, 'completed', %s
                    WHERE EXISTS (SELECT 1 FROM jobs WHERE id = %s::uuid AND status = 'completed')
                    """,
                    (job_id, message, job_id),
                )

    async def request_cancel(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        async with self._database.pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        """
                        UPDATE jobs SET
                            status = CASE WHEN status = 'queued' THEN 'cancelled'
                                          ELSE 'cancel_requested' END,
                            stage_message = CASE WHEN status = 'queued'
                                THEN 'Завдання скасовано.'
                                ELSE 'Надіслано запит на скасування.' END,
                            updated_at = now(),
                            lease_until = CASE WHEN status = 'queued' THEN NULL ELSE lease_until END
                        WHERE id = %s::uuid AND user_id = %s::uuid
                          AND status NOT IN
                            ('completed', 'failed', 'cancelled', 'interrupted', 'cancel_requested')
                        RETURNING *
                        """,
                        (job_id, user_id),
                    )
                ).fetchone()
                if row:
                    await connection.execute(
                        "INSERT INTO job_events (job_id, status, message) VALUES (%s, %s, %s)",
                        (job_id, row["status"], row["stage_message"]),
                    )
                if row is None:
                    row = await (
                        await connection.execute(
                            "SELECT * FROM jobs WHERE id = %s::uuid AND user_id = %s::uuid",
                            (job_id, user_id),
                        )
                    ).fetchone()
                return await self._job_with_plan(connection, row) if row else None

    async def get_job_status(self, job_id: str) -> str | None:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    "SELECT status FROM jobs WHERE id = %s::uuid", (job_id,)
                )
            ).fetchone()
        return row["status"] if row else None

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        async with self._database.pool.connection() as connection:
            row = await (
                await connection.execute(
                    """
                    UPDATE jobs SET lease_until = now() + (%s * interval '1 second')
                    WHERE id = %s::uuid AND worker_id = %s
                      AND status IN ('preparing', 'generating', 'validating')
                    RETURNING id
                    """,
                    (lease_seconds, job_id, worker_id),
                )
            ).fetchone()
        return row is not None

    @staticmethod
    async def _job_with_plan(connection: Any, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        result["id"] = str(result["id"])
        result["user_id"] = str(result["user_id"])
        result["latest_event_id"] = (
            await (
                await connection.execute(
                    "                    SELECT COALESCE(max(id), 0) AS latest_event_id FROM job_events WHERE job_id = %s::uuid",
                    (result["id"],),
                )
            ).fetchone()
        )["latest_event_id"]
        return result

    @staticmethod
    def _user_row(row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "id": str(row["id"])}
