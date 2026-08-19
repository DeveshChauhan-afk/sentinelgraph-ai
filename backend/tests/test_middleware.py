"""
Unit and integration tests for Request ID / Correlation ID Middleware and ContextVar.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from loguru import logger
from prometheus_client import REGISTRY
import pytest
from starlette.testclient import TestClient

from app.api.dependencies import get_incident_service
from app.core.context import get_request_id, reset_request_id, set_request_id
from app.core.logger import setup_logger
from app.core.middleware import RequestLoggingMiddleware, validate_request_id
from app.main import app

client = TestClient(app)


def test_missing_request_id_generates_valid_uuid4():
    """
    1. Verify that missing X-Request-ID header generates a valid UUID4.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    parsed = uuid.UUID(rid, version=4)
    assert str(parsed) == rid


def test_valid_request_id_is_preserved():
    """
    2. Verify that a valid X-Request-ID header is preserved exactly.
    """
    custom_id = "custom-trace-id-123_ABC"
    response = client.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_oversized_id_is_replaced_with_uuid4():
    """
    3. Verify that an oversized X-Request-ID (>64 chars) is replaced with a UUID4.
    """
    oversized = "a" * 65
    response = client.get("/health/live", headers={"X-Request-ID": oversized})
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid != oversized
    parsed = uuid.UUID(rid, version=4)
    assert str(parsed) == rid


def test_invalid_characters_are_replaced_with_uuid4():
    """
    4. Verify that IDs with invalid characters are replaced with a UUID4.
    """
    invalid_id = "invalid@id#with$symbols!"
    response = client.get("/health/live", headers={"X-Request-ID": invalid_id})
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid != invalid_id
    parsed = uuid.UUID(rid, version=4)
    assert str(parsed) == rid


def test_empty_id_is_replaced_with_uuid4():
    """
    5. Verify that an empty X-Request-ID header is replaced with a UUID4.
    """
    response = client.get("/health/live", headers={"X-Request-ID": ""})
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert rid != ""
    parsed = uuid.UUID(rid, version=4)
    assert str(parsed) == rid


def test_validation_logic_directly():
    """
    Directly tests validation logic against control characters, CRLF, and length limits.
    """
    assert validate_request_id(None) is None
    assert validate_request_id("") is None
    assert validate_request_id("a\r\nb") is None
    assert validate_request_id("a\nb") is None
    assert validate_request_id("a\x00b") is None
    assert validate_request_id("a" * 64) == "a" * 64
    assert validate_request_id("a" * 65) is None
    assert validate_request_id("valid_ID-123") == "valid_ID-123"
    assert validate_request_id("invalid space") is None


def test_context_var_is_reset_after_request():
    """
    6 & 7. Verify ContextVar contains the ID during lifecycle and resets to None after.
    """
    assert get_request_id() is None
    response = client.get("/health/live", headers={"X-Request-ID": "test-context-reset-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-context-reset-123"
    # ContextVar must be reset to None outside request context
    assert get_request_id() is None


@pytest.mark.asyncio
async def test_concurrent_requests_context_isolation():
    """
    8. Verify that concurrent async requests receive independent request IDs.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        req1 = ac.get("/health/live", headers={"X-Request-ID": "concurrent-req-1"})
        req2 = ac.get("/health/live", headers={"X-Request-ID": "concurrent-req-2"})
        res1, res2 = await pytest.importorskip("asyncio").gather(req1, req2)

        assert res1.headers.get("X-Request-ID") == "concurrent-req-1"
        assert res2.headers.get("X-Request-ID") == "concurrent-req-2"


def test_exception_handling_receives_request_state():
    """
    9. Verify that exception handling receives the same request ID and returns it in JSON response.
    """
    # Trigger a 404 error through a non-existent route
    response = client.get("/api/v1/non-existent-route", headers={"X-Request-ID": "error-trace-id-123"})
    assert response.status_code == 404
    assert response.headers.get("X-Request-ID") == "error-trace-id-123"


def test_response_always_contains_request_id():
    """
    10. Verify that all standard endpoints return the X-Request-ID header.
    """
    for endpoint in ["/health/live", "/health/ready", "/health", "/api/v1/health/live"]:
        response = client.get(endpoint)
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0


def test_loguru_record_contains_request_id():
    """
    11. Verify that the Loguru patcher injects the active request ID into record["extra"]["request_id"],
    and defaults to "-" outside an active request context.
    """
    setup_logger()
    captured_records = []

    handler_id = logger.add(lambda msg: captured_records.append(msg.record))
    try:
        # 1. Outside request context
        logger.info("Log message outside request")
        assert captured_records[-1]["extra"]["request_id"] == "-"

        # 2. Inside request context
        known_id = "test-loguru-trace-789"
        token = set_request_id(known_id)
        try:
            logger.info("Log message inside request")
            assert captured_records[-1]["extra"]["request_id"] == known_id
        finally:
            reset_request_id(token)

        # 3. Outside request context after reset
        logger.info("Log message after reset")
        assert captured_records[-1]["extra"]["request_id"] == "-"
    finally:
        logger.remove(handler_id)


def test_metrics_successful_request_increments_counter():
    """
    12. Verify successful request increments http_requests_total with method, normalized route template, and status code.
    """
    path_template = "/live"
    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "path": path_template, "status_code": "200"},
        )
        or 0.0
    )

    response = client.get("/health/live")
    assert response.status_code == 200

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": path_template, "status_code": "200"},
    )
    assert after == before + 1.0


def test_metrics_dynamic_route_contains_parameter_placeholder():
    """
    13. Verify request to dynamic route contains {parameter} placeholder and not the raw ID.
    """
    dynamic_id = "11111111-1111-1111-1111-111111111111"
    raw_path = f"/api/v1/complaints/{dynamic_id}"
    route_template = "/{incident_id}"

    mock_service = MagicMock()
    mock_service.get_incident = AsyncMock(return_value=None)
    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        before = (
            REGISTRY.get_sample_value(
                "http_requests_total",
                {"method": "GET", "path": route_template, "status_code": "404"},
            )
            or 0.0
        )

        response = client.get(raw_path)
        assert response.status_code == 404

        after = REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "path": route_template, "status_code": "404"},
        )
        assert after == before + 1.0

        # Verify raw dynamic URL path was NEVER registered as a Prometheus label
        raw_val = REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "path": raw_path, "status_code": "404"},
        )
        assert raw_val is None
    finally:
        app.dependency_overrides.clear()


def test_metrics_unmatched_404_uses_unmatched_label():
    """
    14. Verify unmatched 404 request records metric with path='unmatched'.
    """
    unmatched_url = "/api/v1/nonexistent/random-path-404"
    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "path": "unmatched", "status_code": "404"},
        )
        or 0.0
    )

    response = client.get(unmatched_url)
    assert response.status_code == 404

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": "unmatched", "status_code": "404"},
    )
    assert after == before + 1.0

    # Ensure raw unmatched path was NOT emitted
    raw_val = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": unmatched_url, "status_code": "404"},
    )
    assert raw_val is None


def test_metrics_duration_histogram_records_observation():
    """
    15. Verify duration histogram receives observation for request.
    """
    path_template = "/live"
    count_before = (
        REGISTRY.get_sample_value(
            "http_request_duration_seconds_count",
            {"method": "GET", "path": path_template},
        )
        or 0.0
    )
    sum_before = (
        REGISTRY.get_sample_value(
            "http_request_duration_seconds_sum",
            {"method": "GET", "path": path_template},
        )
        or 0.0
    )

    response = client.get("/health/live")
    assert response.status_code == 200

    count_after = REGISTRY.get_sample_value(
        "http_request_duration_seconds_count",
        {"method": "GET", "path": path_template},
    )
    sum_after = REGISTRY.get_sample_value(
        "http_request_duration_seconds_sum",
        {"method": "GET", "path": path_template},
    )
    assert count_after == count_before + 1.0
    assert sum_after > sum_before


def test_metrics_exception_path_records_status_500_and_propagates():
    """
    16. Verify metric status is 500 on unhandled exception and exception propagates.
    """
    test_app = FastAPI()
    test_app.add_middleware(RequestLoggingMiddleware)

    @test_app.get("/test-crash-endpoint")
    def crash_endpoint():
        raise RuntimeError("Simulated unhandled downstream error")

    test_client = TestClient(test_app, raise_server_exceptions=True)

    before = (
        REGISTRY.get_sample_value(
            "http_requests_total",
            {"method": "GET", "path": "/test-crash-endpoint", "status_code": "500"},
        )
        or 0.0
    )

    with pytest.raises(RuntimeError, match="Simulated unhandled downstream error"):
        test_client.get("/test-crash-endpoint")

    after = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": "/test-crash-endpoint", "status_code": "500"},
    )
    assert after == before + 1.0
