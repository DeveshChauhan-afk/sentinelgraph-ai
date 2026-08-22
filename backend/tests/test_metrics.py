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


def test_metrics_self_metric_recording():
    """
    Verify that GET /metrics requests are recorded as self-metrics in http_requests_total.
    """
    # First request increments the self-metric on exit
    initial_res = client.get("/metrics")
    assert initial_res.status_code == 200

    # Subsequent request exposes the recorded series
    response = client.get("/metrics")
    assert response.status_code == 200
    assert (
        'http_requests_total{method="GET",path="/metrics",status_code="200"}'
        in response.text
    )


def test_metrics_unsupported_method():
    """
    Verify that POST /metrics returns HTTP 405 and the failure is recorded in metrics.
    """
    post_res = client.post("/metrics")
    assert post_res.status_code == 405

    response = client.get("/metrics")
    assert response.status_code == 200
    assert (
        'http_requests_total{method="POST",path="/metrics",status_code="405"}'
        in response.text
    )


def test_metrics_request_id_propagation():
    """
    Verify that X-Request-ID header is propagated correctly through GET /metrics.
    """
    custom_id = "test-metrics-request-123"
    response = client.get("/metrics", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_metrics_consecutive_scrapes():
    """
    Verify that consecutive GET /metrics scrapes return consistent and valid exposition.
    """
    response1 = client.get("/metrics")
    assert response1.status_code == 200
    assert response1.headers["content-type"] == CONTENT_TYPE_LATEST
    assert "http_requests_total" in response1.text
    assert "http_request_duration_seconds" in response1.text

    response2 = client.get("/metrics")
    assert response2.status_code == 200
    assert response2.headers["content-type"] == CONTENT_TYPE_LATEST
    assert "http_requests_total" in response2.text
    assert "http_request_duration_seconds" in response2.text
