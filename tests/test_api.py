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


def test_health_does_not_call_provider() -> None:
    app = create_app(Settings(mock_failure_mode="timeout"))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_plan_is_structured_and_propagates_request_id() -> None:
    response = TestClient(create_app()).post(
        "/api/v1/plans",
        json=valid_request(),
        headers={"X-Owner-ID": "traveler-1", "X-Request-ID": "demo-request-01"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["destination"] == "Lviv"
    assert body["currency"] == "UAH"
    assert len(body["days"]) == 3
    assert body["source"] == "mock"
    assert body["missing_data"] == [
        "live_weather",
        "current_prices",
        "opening_hours",
        "budget_estimates",
    ]
    assert response.headers["X-Request-ID"] == "demo-request-01"


def test_plan_is_not_visible_to_another_owner() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/plans",
        json=valid_request(),
        headers={"X-Owner-ID": "owner-a"},
    )
    plan_id = created.json()["id"]

    response = client.get(
        f"/api/v1/plans/{plan_id}",
        headers={"X-Owner-ID": "owner-b"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_invalid_dates_are_rejected_before_provider_call() -> None:
    app = create_app(Settings(mock_failure_mode="unavailable"))
    payload = valid_request()
    payload["end_date"] = "2027-05-01"

    response = TestClient(app).post(
        "/api/v1/plans",
        json=payload,
        headers={"X-Owner-ID": "traveler-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["fields"] == ["end_date"]


def test_validation_error_does_not_echo_unknown_input() -> None:
    payload = valid_request()
    payload["attacker-controlled-field"] = "private-user-content"

    response = TestClient(create_app()).post(
        "/api/v1/plans",
        json=payload,
        headers={"X-Owner-ID": "traveler-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["request"]
    assert "private-user-content" not in response.text


def test_minimal_ui_is_served() -> None:
    response = TestClient(create_app()).get("/")

    assert response.status_code == 200
    assert "TripPlanner AI" in response.text
