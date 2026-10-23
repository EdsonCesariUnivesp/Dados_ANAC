from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_has_security_headers():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_rejects_invalid_month():
    response = client.get(
        "/api/v1/summary", params={"start_month": "2025-13", "end_month": "2025-12"}
    )
    assert response.status_code == 422
