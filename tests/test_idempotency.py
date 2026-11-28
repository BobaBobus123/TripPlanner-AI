import asyncio

import pytest

from tripplanner.errors import ErrorCode, TripPlannerError
from tripplanner.storage.store import MemoryTripPlannerStore


def test_store_returns_same_durable_job_for_the_same_owner_and_key() -> None:
    async def run():
        store = MemoryTripPlannerStore()
        user = await store.register_user("traveler@example.com", "password-hash")
        payload = {"destination": "Львів"}
        first, created = await store.enqueue_job(
            user["id"], payload, "fingerprint-a", "request-key"
        )
        replay, replay_created = await store.enqueue_job(
            user["id"], payload, "fingerprint-a", "request-key"
        )
        return first, created, replay, replay_created

    first, created, replay, replay_created = asyncio.run(run())
    assert created is True
    assert replay_created is False
    assert replay["id"] == first["id"]


def test_store_rejects_reusing_a_key_with_different_request_data() -> None:
    async def run():
        store = MemoryTripPlannerStore()
        user = await store.register_user("traveler@example.com", "password-hash")
        await store.enqueue_job(user["id"], {}, "fingerprint-a", "request-key")
        await store.enqueue_job(user["id"], {}, "fingerprint-b", "request-key")

    with pytest.raises(TripPlannerError) as error:
        asyncio.run(run())
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_cancellation_racing_with_save_does_not_persist_the_plan() -> None:
    async def run():
        store = MemoryTripPlannerStore()
        user = await store.register_user("traveler@example.com", "password-hash")
        job, _ = await store.enqueue_job(user["id"], {}, "fingerprint", "key")
        await store.claim_job("worker", 30)
        await store.update_job(job["id"], "generating", "Створюємо маршрут.")
        await store.request_cancel(job["id"], user["id"])
        await store.save_plan(job["id"], user["id"], {"id": "plan"})
        return await store.get_job(job["id"], user["id"])

    job = asyncio.run(run())
    assert job["status"] == "cancelled"
    assert job["plan_json"] is None


def test_login_rate_limit_expires_and_can_be_cleared() -> None:
    async def run():
        store = MemoryTripPlannerStore()
        attempts = [
            await store.record_login_attempt("client", 900, 2)
            for _ in range(3)
        ]
        await store.clear_login_attempts("client")
        allowed_after_clear = await store.record_login_attempt("client", 900, 2)
        return attempts, allowed_after_clear

    attempts, allowed_after_clear = asyncio.run(run())
    assert attempts == [True, True, False]
    assert allowed_after_clear is True
