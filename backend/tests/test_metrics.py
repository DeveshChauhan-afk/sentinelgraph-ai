"""
Unit and integration tests for Prometheus metrics exposition endpoint (/metrics).
"""

from fastapi.testclient import TestClient
from prometheus_client import CONTENT_TYPE_LATEST

from app.main import app

client = TestClient(app)


def test_metrics_endpoint_exposition():
    """
    Verify GET /metrics endpoint:
    1. Returns HTTP 200.
    2. Response Content-Type matches prometheus_client.CONTENT_TYPE_LATEST.
    3. Contains http_requests_total metric.
    4. Contains http_request_duration_seconds metric.
    """
    # Trigger at least one request so HTTP metrics are populated by middleware
    health_res = client.get("/health/live")
    assert health_res.status_code == 200

    response = client.get("/metrics")

    # 1. HTTP 200
    assert response.status_code == 200

    # 2. Content-Type equals CONTENT_TYPE_LATEST
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST

    # 3. Contains http_requests_total
    assert "http_requests_total" in response.text

    # 4. Contains http_request_duration_seconds
    assert "http_request_duration_seconds" in response.text
