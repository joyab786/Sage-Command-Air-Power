"""Integration tests for Aero application lifecycle and error handling."""

from fastapi.testclient import TestClient


def test_root_index_endpoint(test_client: TestClient):
    """GET / returns system operational banner."""
    response = test_client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "OPERATIONAL"
    assert "version" in payload


def test_404_not_found_handling(test_client: TestClient):
    """Accessing non-existent routes returns standard 404."""
    response = test_client.get("/non_existent_route")
    assert response.status_code == 404
