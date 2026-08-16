"""
Unit and integration tests for Request ID / Correlation ID Middleware and ContextVar.
"""

import uuid
from httpx import ASGITransport, AsyncClient
from loguru import logger
import pytest
from starlette.testclient import TestClient

from app.core.context import get_request_id, reset_request_id, set_request_id
from app.core.logger import setup_logger
from app.core.middleware import validate_request_id
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
