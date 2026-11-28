import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.storage.sqlite_store import SQLiteTripPlannerStore


def test_initialize_is_repeatable_and_users_and_sessions_survive_reopening(tmp_path) -> None:
    async def run():
        database_path = tmp_path / "tripplanner.sqlite3"
        store = SQLiteTripPlannerStore(database_path)
        await store.initialize()
        await store.initialize()
        user = await store.register_user("traveler@example.com", "password-hash")
        duplicate = await store.register_user("traveler@example.com", "other-hash")
        await store.create_session(
            "session-hash",
            user["id"],
            "csrf-value",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )
        await store.close()

        reopened = SQLiteTripPlannerStore(database_path)
        await reopened.initialize()
        persisted_user = await reopened.get_user_by_email("traveler@example.com")
        persisted_session = await reopened.get_session("session-hash")
        await reopened.close()
        return user, duplicate, persisted_user, persisted_session

    user, duplicate, persisted_user, persisted_session = asyncio.run(run())
    assert user is not None
    assert duplicate is None
    assert persisted_user == user
    assert persisted_session["user_id"] == user["id"]
    assert persisted_session["csrf_token"] == "csrf-value"
    assert persisted_session["expires_at"].tzinfo == timezone.utc


def test_constructor_defers_schema_creation_and_initialize_can_repeat(tmp_path) -> None:
    async def run():
        database_path = tmp_path / "deferred.sqlite3"
        store = SQLiteTripPlannerStore(database_path)
        before = store._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        await store.initialize()
        await store.initialize()
        after = store._connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        await store.close()
        return before, after

    before, after = asyncio.run(run())
    assert before is None
    assert after is not None


def test_job_ownership_idempotency_events_and_plan_persist(tmp_path) -> None:
    async def run():
        store = SQLiteTripPlannerStore(tmp_path / "jobs.sqlite3")
        await store.initialize()
        owner = await store.register_user("owner@example.com", "hash")
        stranger = await store.register_user("stranger@example.com", "hash")

        first, created = await store.enqueue_job(
            owner["id"], {"destination": "Lviv"}, "fingerprint", "key"
        )
        replay, replay_created = await store.enqueue_job(
            owner["id"], {"destination": "Lviv"}, "fingerprint", "key"
        )
        stranger_job, stranger_created = await store.enqueue_job(
            stranger["id"], {"destination": "Lviv"}, "fingerprint", "key"
        )
        inaccessible = await store.get_job(first["id"], stranger["id"])
        stranger_cancel = await store.request_cancel(first["id"], stranger["id"])
        await store.claim_job("worker", 30)
        await store.update_job(first["id"], "generating", "Generating")
        await store.save_plan(
            first["id"], owner["id"], {"id": "plan-1", "destination": "Lviv"}
        )
        await store.close()

        reopened = SQLiteTripPlannerStore(tmp_path / "jobs.sqlite3")
        await reopened.initialize()
        completed = await reopened.get_job(first["id"], owner["id"])
        events = await reopened.get_job_events(first["id"], 0)
        await reopened.close()
        return (
            first,
            created,
            replay,
            replay_created,
            stranger_job,
            stranger_created,
            inaccessible,
            stranger_cancel,
            completed,
            events,
        )

    (
        first,
        created,
        replay,
        replay_created,
        stranger_job,
        stranger_created,
        inaccessible,
        stranger_cancel,
        completed,
        events,
    ) = asyncio.run(run())
    assert created is True
    assert replay_created is False
    assert replay["id"] == first["id"]
    assert stranger_created is True
    assert stranger_job["id"] != first["id"]
    assert inaccessible is None
    assert stranger_cancel is None
    assert completed["status"] == "completed"
    assert completed["plan_json"] == {"id": "plan-1", "destination": "Lviv"}
    assert [event["status"] for event in events] == [
        "queued",
        "preparing",
        "generating",
        "completed",
    ]
    assert completed["latest_event_id"] == events[-1]["id"]


def test_idempotency_conflict_and_save_plan_enforces_ownership(tmp_path) -> None:
    async def run():
        store = SQLiteTripPlannerStore(tmp_path / "conflict.sqlite3")
        await store.initialize()
        owner = await store.register_user("owner@example.com", "hash")
        stranger = await store.register_user("stranger@example.com", "hash")
        job, _ = await store.enqueue_job(owner["id"], {}, "one", "same-key")
        with pytest.raises(TripPlannerError) as error:
            await store.enqueue_job(owner["id"], {}, "two", "same-key")
        with pytest.raises(TripPlannerError) as ownership_error:
            await store.save_plan(job["id"], stranger["id"], {"id": "plan"})
        await store.close()
        return error.value.code, ownership_error.value.code

    conflict_code, ownership_code = asyncio.run(run())
    assert conflict_code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert ownership_code == ErrorCode.NOT_FOUND


def test_cancellation_and_expired_worker_lease_recovery(tmp_path) -> None:
    async def run():
        store = SQLiteTripPlannerStore(tmp_path / "leases.sqlite3")
        await store.initialize()
        user = await store.register_user("traveler@example.com", "hash")

        queued, _ = await store.enqueue_job(user["id"], {}, "queued", "queued-key")
        cancelled_queued = await store.request_cancel(queued["id"], user["id"])
        assert cancelled_queued["status"] == "cancelled"

        interrupted, _ = await store.enqueue_job(user["id"], {}, "work", "work-key")
        claimed = await store.claim_job("worker-a", 0)
        assert claimed["id"] == interrupted["id"]
        assert await store.heartbeat(interrupted["id"], "worker-a", 30)
        assert not await store.heartbeat(interrupted["id"], "worker-b", 30)
        store._connection.execute(
            "UPDATE jobs SET lease_until = ? WHERE id = ?",
            ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), interrupted["id"]),
        )
        assert await store.claim_job("worker-b", 30) is None
        recovered = await store.get_job(interrupted["id"], user["id"])

        active, _ = await store.enqueue_job(user["id"], {}, "cancel", "cancel-key")
        await store.claim_job("worker-c", 30)
        requested = await store.request_cancel(active["id"], user["id"])
        assert requested["status"] == "cancel_requested"
        assert not await store.heartbeat(active["id"], "worker-c", 30)
        store._connection.execute(
            "UPDATE jobs SET lease_until = ? WHERE id = ?",
            ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), active["id"]),
        )
        await store.claim_job("worker-d", 30)
        recovered_cancel = await store.get_job(active["id"], user["id"])
        await store.close()
        return recovered, recovered_cancel

    recovered, recovered_cancel = asyncio.run(run())
    assert recovered["status"] == "interrupted"
    assert recovered["error_code"] == "worker_interrupted"
    assert recovered_cancel["status"] == "cancelled"


def test_provider_mode_verification_tokens_and_login_throttling(tmp_path) -> None:
    async def run():
        store = SQLiteTripPlannerStore(tmp_path / "account.sqlite3")
        await store.initialize()
        await store.initialize_provider_mode("mock")
        await store.set_provider_mode("openai_compat")
        user = await store.register_user("traveler@example.com", "hash")
        await store.create_email_verification(
            user["id"], "verification-hash", datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        verified = await store.verify_email_token("verification-hash")
        reused = await store.verify_email_token("verification-hash")
        attempts = [
            await store.record_login_attempt("client", 900, 2)
            for _ in range(3)
        ]
        await store.clear_login_attempts("client")
        after_clear = await store.record_login_attempt("client", 900, 2)
        mode = await store.get_provider_mode("mock")
        await store.close()
        return mode, verified, reused, attempts, after_clear

    mode, verified, reused, attempts, after_clear = asyncio.run(run())
    assert mode == "openai_compat"
    assert verified["email_verified"] is True
    assert reused is None
    assert attempts == [True, True, False]
    assert after_clear is True
