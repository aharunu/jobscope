"""Health endpoint verification tests."""

from fastapi.testclient import TestClient


def test_health_check_returns_200_and_valid_payload(client: TestClient) -> None:
    """Verify GET /health returns HTTP 200 with required health metadata."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "JobScope-Test"
    assert data["environment"] == "test"
    assert data["version"] == "0.1.0-test"


def test_health_check_api_prefix_returns_200(client: TestClient) -> None:
    """Verify GET /api/health returns HTTP 200 with required health metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
