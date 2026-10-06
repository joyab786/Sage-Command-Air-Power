"""Integration tests for Aero Health Check API endpoints."""

from fastapi.testclient import TestClient


def test_root_health_endpoint(test_client: TestClient):
    """GET /health must return HTTP 200 with complete diagnostics envelope."""
    response = test_client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "data" in payload

    data = payload["data"]
    assert data["status"] == "HEALTHY"
    assert "Aero" in data["app_name"]
    assert "testing" in data["environment"].lower() or "development" in data["environment"].lower()
    assert data["database"]["connected"] is True
    assert data["database"]["status"] == "HEALTHY"

    # Verify correlation headers
    assert "x-correlation-id" in response.headers
    assert "x-process-time-ms" in response.headers


def test_versioned_health_endpoint(test_client: TestClient):
    """GET /api/v1/health must return identical diagnostics payload."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "HEALTHY"


def test_custom_correlation_id_propagation(test_client: TestClient):
    """Client-provided X-Correlation-ID must be echoed back in response headers."""
    client_corr_id = "corr_custom_test_header_99"
    response = test_client.get("/health", headers={"X-Correlation-ID": client_corr_id})
    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == client_corr_id
