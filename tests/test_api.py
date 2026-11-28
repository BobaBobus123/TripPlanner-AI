import time
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from tripplanner.config import Settings
from tripplanner.main import create_app


def valid_request() -> dict:
    return {
        "destination": "  Lviv ",
        "start_date": "2027-05-10",
        "end_date": "2027-05-12",
        "currency": "uah",
        "budget": 12000,
        "traveler_count": 2,
        "interests": ["architecture"],
    }


def register(client: TestClient, email: str = "traveler@example.com") -> str:
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert registration.status_code == 201
    verification_url = registration.json()["verification_url"]
    token = parse_qs(urlsplit(verification_url).fragment)["token"][0]
    verified = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    return login.json()["csrf_token"]


def test_health_does_not_call_provider() -> None:
    response = TestClient(create_app(Settings(mock_failure_mode="timeout"))).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"]["ai_mode"] == "demo"


def test_health_reports_live_provider_without_exposing_credentials() -> None:
    secret = "test-key-never-return-this"
    settings = Settings(
        provider="openai_compat",
        openai_compat_api_key=secret,
        input_cost_per_million_tokens="0.15",
        output_cost_per_million_tokens="0.60",
    )
    response = TestClient(create_app(settings)).get("/health")

    assert response.status_code == 200
    assert response.json()["checks"]["ai_mode"] == "live"
    assert response.json()["checks"]["model"] == settings.openai_compat_model
    assert secret not in response.text


def test_global_provider_mode_can_only_be_changed_by_configured_admin() -> None:
    settings = Settings(
        app_admin_email="owner@example.com",
        openai_compat_api_key="test-key-never-return-this",
        input_cost_per_million_tokens="0.15",
        output_cost_per_million_tokens="0.60",
    )
    client = TestClient(create_app(settings))
    admin_csrf = register(client, "owner@example.com")

    initial = client.get("/api/v1/settings/provider")
    switched = client.put(
        "/api/v1/settings/provider",
        json={"mode": "openai_compat"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    health = client.get("/health")
    client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": admin_csrf},
    )
    register(client, "traveler@example.com")
    regular_user_settings = client.get("/api/v1/settings/provider")
    forbidden_switch = client.put(
        "/api/v1/settings/provider",
        json={"mode": "mock"},
        headers={
            "X-CSRF-Token": client.get("/api/v1/auth/me").json()["csrf_token"]
        },
    )

    assert initial.json()["mode"] == "mock"
    assert initial.json()["is_admin"] is True
    assert "openai_compat" in initial.json()["available_modes"]
    assert switched.status_code == 200
    assert switched.json()["mode"] == "openai_compat"
    assert health.json()["checks"]["ai_mode"] == "live"
    assert regular_user_settings.json()["mode"] == "openai_compat"
    assert regular_user_settings.json()["is_admin"] is False
    assert forbidden_switch.status_code == 404


def test_registration_requires_email_verification_before_login() -> None:
    with TestClient(create_app()) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "Traveler@Example.com", "password": "correct horse battery staple"},
        )
        login_before_verification = client.post(
            "/api/v1/auth/login",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )
        verification_url = registration.json()["verification_url"]
        token = parse_qs(urlsplit(verification_url).fragment)["token"][0]
        verification = client.post("/api/v1/auth/verify-email", json={"token": token})
        replay = client.post("/api/v1/auth/verify-email", json={"token": token})
        login_after_verification = client.post(
            "/api/v1/auth/login",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )

    assert registration.status_code == 201
    assert registration.json()["development_only"] is True
    assert urlsplit(verification_url).query == ""
    assert registration.headers["referrer-policy"] == "no-referrer"
    assert "set-cookie" not in registration.headers
    assert login_before_verification.status_code == 403
    assert login_before_verification.json()["error"]["code"] == "email_not_verified"
    assert verification.status_code == 200
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "invalid_verification_token"
    assert login_after_verification.status_code == 200
    assert "password" not in login_after_verification.json()
    cookie = login_after_verification.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_resending_verification_invalidates_previous_token_without_leaking_hashes() -> None:
    app = create_app()
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "traveler@example.com", "password": "correct horse battery staple"},
        )
        old_token = parse_qs(urlsplit(registration.json()["verification_url"]).fragment)["token"][0]
        resend = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "traveler@example.com"},
        )
        new_token = parse_qs(urlsplit(resend.json()["verification_url"]).fragment)["token"][0]
        old_link = client.post("/api/v1/auth/verify-email", json={"token": old_token})
        verified = client.post("/api/v1/auth/verify-email", json={"token": new_token})

    assert resend.status_code == 200
    assert "traveler@example.com" not in resend.json()["message"]
    assert old_link.status_code == 400
    assert verified.status_code == 200
    assert old_token not in app.state.store._email_verification_tokens
    assert new_token not in app.state.store._email_verification_tokens


def test_login_uses_same_error_for_unknown_email_and_wrong_password() -> None:
    with TestClient(create_app()) as client:
        register(client)
        logout = client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": client.get("/api/v1/auth/me").json()["csrf_token"]},
        )
        wrong_password = client.post(
            "/api/v1/auth/login",
            json={"email": "traveler@example.com", "password": "wrong password"},
        )
        unknown_email = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong password"},
        )

    assert logout.status_code == 204
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


def test_jobs_require_a_session_and_csrf_proof() -> None:
    with TestClient(create_app()) as client:
        payload = valid_request()
        assert client.get("/api/v1/jobs").status_code == 401
        csrf = register(client)
        no_csrf = client.post("/api/v1/jobs", json=payload)
        wrong_origin = client.post(
            "/api/v1/jobs",
            json=payload,
            headers={"X-CSRF-Token": csrf, "Origin": "https://attacker.example"},
        )
        accepted = client.post(
            "/api/v1/jobs", json=payload, headers={"X-CSRF-Token": csrf}
        )

    assert no_csrf.status_code == wrong_origin.status_code == 401
    assert accepted.status_code == 202
    assert accepted.json()["job"]["destination"] == "Lviv"
    assert accepted.json()["job"]["start_date"] == "2027-05-10"
    assert accepted.json()["job"]["end_date"] == "2027-05-12"
    assert accepted.json()["job"]["provider_mode"] == "mock"


def test_job_idempotency_is_persistent_in_the_store_and_payload_scoped() -> None:
    with TestClient(create_app()) as client:
        csrf = register(client)
        headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "same-request"}
        first = client.post("/api/v1/jobs", json=valid_request(), headers=headers)
        duplicate = client.post("/api/v1/jobs", json=valid_request(), headers=headers)
        changed = valid_request()
        changed["destination"] = "Kyiv"
        conflict = client.post("/api/v1/jobs", json=changed, headers=headers)

    assert first.status_code == duplicate.status_code == 202
    assert first.json()["job"]["id"] == duplicate.json()["job"]["id"]
    assert duplicate.json()["created"] is False
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_job_ownership_and_logout_revoke_session() -> None:
    with TestClient(create_app()) as client:
        csrf_a = register(client, "first@example.com")
        created = client.post(
            "/api/v1/jobs",
            json=valid_request(),
            headers={"X-CSRF-Token": csrf_a},
        )
        job_id = created.json()["job"]["id"]
        client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_a})
        csrf_b = register(client, "second@example.com")
        hidden = client.get(f"/api/v1/jobs/{job_id}")
        logged_out = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_b})
        revoked = client.get("/api/v1/jobs")

    assert hidden.status_code == 404
    assert logged_out.status_code == 204
    assert revoked.status_code == 401


def test_worker_persists_result_and_emits_replayable_events() -> None:
    with TestClient(create_app(Settings(mock_delay_seconds=0.01))) as client:
        csrf = register(client)
        created = client.post(
            "/api/v1/jobs",
            json=valid_request(),
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "worker-job"},
        )
        job_id = created.json()["job"]["id"]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            response = client.get(f"/api/v1/jobs/{job_id}")
            job = response.json()["job"]
            if job["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        events = client.get(f"/api/v1/jobs/{job_id}/events?after_id=0")
        replay_after_latest = client.get(
            f"/api/v1/jobs/{job_id}/events?after_id={job['latest_event_id']}"
        )

    assert job["status"] == "completed"
    assert len(job["plan"]["days"]) == 3
    assert "event: progress" in events.text
    assert '"status": "generating"' in events.text
    assert '"status": "completed"' in events.text
    assert replay_after_latest.text == ""


def test_cancellation_during_generation_does_not_save_a_plan() -> None:
    with TestClient(create_app(Settings(mock_delay_seconds=2))) as client:
        csrf = register(client)
        created = client.post(
            "/api/v1/jobs",
            json=valid_request(),
            headers={"X-CSRF-Token": csrf},
        )
        job_id = created.json()["job"]["id"]
        cancel = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"X-CSRF-Token": csrf},
        )
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            response = client.get(f"/api/v1/jobs/{job_id}")
            job = response.json()["job"]
            if job["status"] in {"cancelled", "completed"}:
                break
            time.sleep(0.02)

    assert cancel.status_code == 200
    assert job["status"] == "cancelled"
    assert job["plan"] is None


def test_invalid_dates_are_rejected_without_leaking_input() -> None:
    payload = valid_request()
    payload["end_date"] = "2027-05-01"
    with TestClient(create_app(Settings(mock_failure_mode="unavailable"))) as client:
        csrf = register(client)
        response = client.post(
            "/api/v1/jobs", json=payload, headers={"X-CSRF-Token": csrf}
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["fields"] == ["end_date"]


def test_unknown_request_fields_are_not_echoed() -> None:
    payload = valid_request()
    payload["unexpected"] = "private-user-content"
    with TestClient(create_app()) as client:
        csrf = register(client)
        response = client.post(
            "/api/v1/jobs", json=payload, headers={"X-CSRF-Token": csrf}
        )

    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["request"]
    assert "private-user-content" not in response.text


def test_ui_and_openapi_describe_the_authenticated_job_flow_in_ukrainian() -> None:
    client = TestClient(create_app())
    page = client.get("/")
    login_page = client.get("/login")
    register_page = client.get("/register")
    verify_page = client.get("/verify-email")
    dashboard = client.get("/dashboard")
    trips = client.get("/trips")
    new_trip = client.get("/new")
    detail = client.get("/trips/00000000-0000-4000-8000-000000000001")
    unknown_ui_page = client.get("/trips/not-a-job-id")
    specification = client.get("/openapi.json").json()

    assert page.status_code == login_page.status_code == 200
    assert register_page.status_code == verify_page.status_code == 200
    assert dashboard.status_code == trips.status_code == new_trip.status_code == detail.status_code == 200
    assert unknown_ui_page.status_code == 404
    assert 'lang="uk"' in page.text
    assert "Створити обліковий запис" in page.text
    assert 'id="register-password-confirm"' in register_page.text
    assert "Підтвердьте електронну пошту" in verify_page.text
    assert 'href="/register"' in login_page.text
    assert 'href="/login"' in register_page.text
    assert "Мої подорожі" in page.text
    assert 'data-view="dashboard"' in page.text
    assert 'data-view="trips"' in page.text
    assert 'data-view="new"' in page.text
    assert 'data-view="detail"' in page.text
    assert "EventSource" in page.text
    assert "Як створюється план" in page.text
    assert "не підключений до чату Copilot" in page.text
    assert 'id="check-service"' in page.text
    assert "X-Owner-ID" not in page.text
    assert specification["info"]["title"] == "TripPlanner AI — планування подорожей"
    assert specification["paths"]["/api/v1/jobs"]["post"]["summary"] == "Поставити створення плану в чергу"
