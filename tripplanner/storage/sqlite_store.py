import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from tripplanner.errors import ErrorCode, TripPlannerError

TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled", "interrupted"}

_INITIAL_JOB_MESSAGE = "Запит прийнято. Очікуємо на обробку."
_INTERRUPTED_MESSAGE = "Обробку перервано. Створіть нову спробу."
_CANCELLED_MESSAGE = "Завдання скасовано."

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS email_verification_tokens_expires_idx
    ON email_verification_tokens (expires_at);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions (expires_at);
CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_key TEXT PRIMARY KEY,
    window_started_at TEXT NOT NULL,
    attempts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS login_attempts_window_idx
    ON login_attempts (window_started_at);
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_json TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'preparing', 'generating', 'validating', 'completed',
                   'failed', 'cancel_requested', 'cancelled', 'interrupted')
    ),
    stage_message TEXT NOT NULL,
    error_code TEXT,
    worker_id TEXT,
    lease_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs (created_at)
    WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS jobs_lease_idx ON jobs (lease_until)
    WHERE status IN ('preparing', 'generating', 'validating');
CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS job_events_job_id_idx ON job_events (job_id, id);
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    parent_plan_id TEXT REFERENCES plans(id) ON DELETE SET NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS plans_user_created_idx ON plans (user_id, created_at DESC);
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _from_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _decode_json(value: str | None) -> Any:
    return json.loads(value) if value is not None else None


class SQLiteTripPlannerStore:
    """SQLite-backed local store; call ``initialize`` before using store methods."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA busy_timeout = 30000")

    async def initialize(self) -> None:
        with self._lock:
            try:
                self._connection.executescript(f"BEGIN IMMEDIATE;\n{_SCHEMA}\nCOMMIT;")
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    async def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _transaction(self):
        return _SQLiteTransaction(self._connection)

    async def initialize_provider_mode(self, default: str) -> None:
        with self._lock, self._transaction():
            self._connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value, updated_at)
                VALUES ('provider_mode', ?, ?)
                ON CONFLICT (setting_key) DO NOTHING
                """,
                (default, _to_iso(_utc_now())),
            )

    async def get_provider_mode(self, default: str) -> str:
        with self._lock:
            row = self._connection.execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = 'provider_mode'"
            ).fetchone()
            return row["setting_value"] if row else default

    async def set_provider_mode(self, mode: str) -> None:
        with self._lock, self._transaction():
            self._connection.execute(
                """
                INSERT INTO app_settings (setting_key, setting_value, updated_at)
                VALUES ('provider_mode', ?, ?)
                ON CONFLICT (setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = excluded.updated_at
                """,
                (mode, _to_iso(_utc_now())),
            )

    async def register_user(self, email: str, password_hash: str) -> dict[str, Any] | None:
        with self._lock, self._transaction():
            user_id = str(uuid4())
            cursor = self._connection.execute(
                """
                INSERT INTO users (id, email, password_hash, email_verified, created_at)
                VALUES (?, ?, ?, 0, ?)
                ON CONFLICT (email) DO NOTHING
                """,
                (user_id, email, password_hash, _to_iso(_utc_now())),
            )
            if cursor.rowcount == 0:
                return None
            return {
                "id": user_id,
                "email": email,
                "password_hash": password_hash,
                "email_verified": False,
            }

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, email, password_hash, email_verified
                FROM users WHERE email = ?
                """,
                (email,),
            ).fetchone()
            return self._user_row(row) if row else None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id, email, email_verified FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if row is None:
                return None
            return {**dict(row), "email_verified": bool(row["email_verified"])}

    async def create_email_verification(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        with self._lock, self._transaction():
            self._connection.execute(
                "DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,)
            )
            self._connection.execute(
                """
                INSERT INTO email_verification_tokens
                    (token_hash, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (token_hash, user_id, _to_iso(expires_at), _to_iso(_utc_now())),
            )

    async def verify_email_token(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock, self._transaction():
            row = self._connection.execute(
                """
                SELECT user_id FROM email_verification_tokens
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, _to_iso(_utc_now())),
            ).fetchone()
            if row is None:
                return None
            user_id = row["user_id"]
            user = self._connection.execute(
                """
                UPDATE users SET email_verified = 1
                WHERE id = ? RETURNING id, email, email_verified
                """,
                (user_id,),
            ).fetchone()
            self._connection.execute(
                "DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,)
            )
            if user is None:
                return None
            return {
                "id": user["id"],
                "email": user["email"],
                "email_verified": bool(user["email_verified"]),
            }

    async def record_login_attempt(
        self, attempt_key: str, window_seconds: int, maximum: int
    ) -> bool:
        with self._lock, self._transaction():
            now = _utc_now()
            now_iso = _to_iso(now)
            self._connection.execute(
                "DELETE FROM login_attempts WHERE window_started_at < ?",
                (_to_iso(now - timedelta(days=1)),),
            )
            row = self._connection.execute(
                "SELECT window_started_at, attempts FROM login_attempts WHERE attempt_key = ?",
                (attempt_key,),
            ).fetchone()
            if row is None:
                attempts = 1
                started = now_iso
                self._connection.execute(
                    """
                    INSERT INTO login_attempts (attempt_key, window_started_at, attempts)
                    VALUES (?, ?, ?)
                    """,
                    (attempt_key, started, attempts),
                )
            else:
                previous_started = _from_iso(row["window_started_at"])
                if previous_started is None or previous_started + timedelta(
                    seconds=window_seconds
                ) <= now:
                    attempts = 1
                    started = now_iso
                else:
                    attempts = row["attempts"] + 1
                    started = row["window_started_at"]
                self._connection.execute(
                    """
                    UPDATE login_attempts SET window_started_at = ?, attempts = ?
                    WHERE attempt_key = ?
                    """,
                    (started, attempts, attempt_key),
                )
            return attempts <= maximum

    async def clear_login_attempts(self, attempt_key: str) -> None:
        with self._lock, self._transaction():
            self._connection.execute(
                "DELETE FROM login_attempts WHERE attempt_key = ?", (attempt_key,)
            )

    async def create_session(
        self, token_hash: str, user_id: str, csrf_token: str, expires_at: datetime
    ) -> None:
        with self._lock, self._transaction():
            self._connection.execute(
                """
                INSERT INTO sessions (token_hash, user_id, csrf_token, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    token_hash,
                    user_id,
                    csrf_token,
                    _to_iso(expires_at),
                    _to_iso(_utc_now()),
                ),
            )

    async def get_session(self, token_hash: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT user_id, csrf_token, expires_at FROM sessions
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, _to_iso(_utc_now())),
            ).fetchone()
            if row is None:
                return None
            return {
                "user_id": row["user_id"],
                "csrf_token": row["csrf_token"],
                "expires_at": _from_iso(row["expires_at"]),
            }

    async def delete_session(self, token_hash: str) -> None:
        with self._lock, self._transaction():
            self._connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    async def enqueue_job(
        self, user_id: str, payload: dict[str, Any], fingerprint: str, key: str
    ) -> tuple[dict[str, Any], bool]:
        with self._lock, self._transaction():
            existing = self._connection.execute(
                """
                SELECT id, request_fingerprint FROM jobs
                WHERE user_id = ? AND idempotency_key = ?
                """,
                (user_id, key),
            ).fetchone()
            if existing is not None:
                if existing["request_fingerprint"] != fingerprint:
                    raise TripPlannerError(ErrorCode.IDEMPOTENCY_CONFLICT)
                return self._job_with_plan(existing["id"]), False

            now = _to_iso(_utc_now())
            job_id = str(uuid4())
            self._connection.execute(
                """
                INSERT INTO jobs (
                    id, user_id, request_json, request_fingerprint, idempotency_key,
                    status, stage_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (
                    job_id,
                    user_id,
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                    fingerprint,
                    key,
                    _INITIAL_JOB_MESSAGE,
                    now,
                    now,
                ),
            )
            self._append_event(job_id, "queued", _INITIAL_JOB_MESSAGE)
            return self._job_with_plan(job_id), True

    async def get_job(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id FROM jobs WHERE id = ? AND user_id = ?", (job_id, user_id)
            ).fetchone()
            return self._job_with_plan(job_id) if row else None

    async def list_jobs(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id FROM jobs WHERE user_id = ?
                ORDER BY created_at DESC LIMIT 100
                """,
                (user_id,),
            ).fetchall()
            return [self._job_with_plan(row["id"]) for row in rows]

    async def get_job_events(self, job_id: str, after_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, job_id, status, message, created_at FROM job_events
                WHERE job_id = ? AND id > ? ORDER BY id
                """,
                (job_id, after_id),
            ).fetchall()
            return [
                {
                    **dict(row),
                    "created_at": _from_iso(row["created_at"]),
                }
                for row in rows
            ]

    async def claim_job(self, worker_id: str, lease_seconds: int) -> dict[str, Any] | None:
        with self._lock, self._transaction():
            now = _utc_now()
            now_iso = _to_iso(now)
            expired = self._connection.execute(
                """
                SELECT id, status FROM jobs
                WHERE status IN ('preparing', 'generating', 'validating', 'cancel_requested')
                  AND lease_until IS NOT NULL AND lease_until < ?
                """,
                (now_iso,),
            ).fetchall()
            for row in expired:
                if row["status"] == "cancel_requested":
                    status = "cancelled"
                    message = _CANCELLED_MESSAGE
                    error_code = None
                else:
                    status = "interrupted"
                    message = _INTERRUPTED_MESSAGE
                    error_code = "worker_interrupted"
                self._connection.execute(
                    """
                    UPDATE jobs SET status = ?, stage_message = ?, error_code = ?,
                        updated_at = ?, worker_id = NULL, lease_until = NULL
                    WHERE id = ?
                    """,
                    (status, message, error_code, now_iso, row["id"]),
                )
                self._append_event(row["id"], status, message)

            job = self._connection.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if job is None:
                return None
            message = "Перевіряємо параметри подорожі."
            self._connection.execute(
                """
                UPDATE jobs SET status = 'preparing', stage_message = ?, worker_id = ?,
                    lease_until = ?, updated_at = ? WHERE id = ?
                """,
                (
                    message,
                    worker_id,
                    _to_iso(now + timedelta(seconds=lease_seconds)),
                    _to_iso(now),
                    job["id"],
                ),
            )
            self._append_event(job["id"], "preparing", message)
            return self._job_with_plan(job["id"])

    async def update_job(
        self, job_id: str, status: str, message: str, *, error_code: str | None = None
    ) -> None:
        with self._lock, self._transaction():
            row = self._connection.execute(
                "SELECT status FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if (
                row is None
                or row["status"] in TERMINAL_JOB_STATUSES
                or (row["status"] == "cancel_requested" and status != "cancelled")
            ):
                return
            lease_until = None if status in TERMINAL_JOB_STATUSES else (
                self._connection.execute(
                    "SELECT lease_until FROM jobs WHERE id = ?", (job_id,)
                ).fetchone()["lease_until"]
            )
            self._connection.execute(
                """
                UPDATE jobs SET status = ?, stage_message = ?, error_code = ?,
                    updated_at = ?, lease_until = ? WHERE id = ?
                """,
                (status, message, error_code, _to_iso(_utc_now()), lease_until, job_id),
            )
            self._append_event(job_id, status, message)

    async def save_plan(self, job_id: str, user_id: str, plan: dict[str, Any]) -> None:
        with self._lock, self._transaction():
            row = self._connection.execute(
                "SELECT status, user_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if row is None or row["user_id"] != user_id:
                raise TripPlannerError(ErrorCode.NOT_FOUND)
            if row["status"] == "cancel_requested":
                self._connection.execute(
                    """
                    UPDATE jobs SET status = 'cancelled', stage_message = ?,
                        updated_at = ?, lease_until = NULL WHERE id = ?
                    """,
                    (_CANCELLED_MESSAGE, _to_iso(_utc_now()), job_id),
                )
                self._append_event(job_id, "cancelled", _CANCELLED_MESSAGE)
                return
            if row["status"] in TERMINAL_JOB_STATUSES:
                return
            self._connection.execute(
                """
                INSERT INTO plans (id, job_id, user_id, plan_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (job_id) DO NOTHING
                """,
                (
                    plan["id"],
                    job_id,
                    user_id,
                    json.dumps(plan, separators=(",", ":"), ensure_ascii=False),
                    _to_iso(_utc_now()),
                ),
            )
            message = "План готовий."
            self._connection.execute(
                """
                UPDATE jobs SET status = 'completed', stage_message = ?,
                    updated_at = ?, lease_until = NULL WHERE id = ?
                """,
                (message, _to_iso(_utc_now()), job_id),
            )
            self._append_event(job_id, "completed", message)

    async def request_cancel(self, job_id: str, user_id: str) -> dict[str, Any] | None:
        with self._lock, self._transaction():
            row = self._connection.execute(
                "SELECT status FROM jobs WHERE id = ? AND user_id = ?",
                (job_id, user_id),
            ).fetchone()
            if row is None:
                return None
            status = row["status"]
            if status not in TERMINAL_JOB_STATUSES and status != "cancel_requested":
                if status == "queued":
                    updated_status = "cancelled"
                    message = _CANCELLED_MESSAGE
                else:
                    updated_status = "cancel_requested"
                    message = "Надіслано запит на скасування."
                lease = None if updated_status == "cancelled" else (
                    self._connection.execute(
                        "SELECT lease_until FROM jobs WHERE id = ?", (job_id,)
                    ).fetchone()["lease_until"]
                )
                self._connection.execute(
                    """
                    UPDATE jobs SET status = ?, stage_message = ?, updated_at = ?,
                        lease_until = ? WHERE id = ?
                    """,
                    (updated_status, message, _to_iso(_utc_now()), lease, job_id),
                )
                self._append_event(job_id, updated_status, message)
            return self._job_with_plan(job_id)

    async def get_job_status(self, job_id: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT status FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            return row["status"] if row else None

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int) -> bool:
        with self._lock, self._transaction():
            cursor = self._connection.execute(
                """
                UPDATE jobs SET lease_until = ?
                WHERE id = ? AND worker_id = ?
                  AND status IN ('preparing', 'generating', 'validating')
                """,
                (
                    _to_iso(_utc_now() + timedelta(seconds=lease_seconds)),
                    job_id,
                    worker_id,
                ),
            )
            return cursor.rowcount > 0

    def _append_event(self, job_id: str, status: str, message: str) -> None:
        self._connection.execute(
            """
            INSERT INTO job_events (job_id, status, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, status, message, _to_iso(_utc_now())),
        )

    def _job_with_plan(self, job_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            """
            SELECT j.*,
                   p.plan_json AS plan_json,
                   COALESCE((SELECT max(id) FROM job_events WHERE job_id = j.id), 0)
                       AS latest_event_id
            FROM jobs j LEFT JOIN plans p ON p.job_id = j.id
            WHERE j.id = ?
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            raise LookupError(f"Job does not exist: {job_id}")
        result = dict(row)
        result["request_json"] = _decode_json(result["request_json"])
        result["plan_json"] = _decode_json(result["plan_json"])
        for field in ("created_at", "updated_at", "lease_until"):
            result[field] = _from_iso(result[field])
        return result

    @staticmethod
    def _user_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "email": row["email"],
            "password_hash": row["password_hash"],
            "email_verified": bool(row["email_verified"]),
        }


class _SQLiteTransaction:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __enter__(self) -> None:
        self.connection.execute("BEGIN IMMEDIATE")
        return None

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        del exc_value, traceback
        if exc_type is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        return False
