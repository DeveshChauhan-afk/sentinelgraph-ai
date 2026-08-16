"""
Unit tests for production health endpoints (/health/live, /health/ready, /health)
and concrete dependency health checkers (Postgres, Neo4j, Gemini).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.health.base import BaseHealthChecker
from app.core.health.gemini import GeminiConfigHealthChecker
from app.core.health.models import HealthStatus
from app.core.health.neo4j import Neo4jHealthChecker
from app.core.health.postgres import PostgresHealthChecker
from app.main import app

client = TestClient(app)


def test_liveness_endpoint():
    """
    Test GET /health/live returns HTTP 200 and healthy status.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

    # Also verify via API v1 prefix
    v1_response = client.get("/api/v1/health/live")
    assert v1_response.status_code == 200
    assert v1_response.json() == {"status": "healthy"}


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_readiness_endpoint_success(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health/ready returns HTTP 200 when all dependencies are healthy.
    """
    mock_postgres.return_value = True
    mock_neo4j.return_value = True

    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["neo4j"] == "healthy"
    assert data["dependencies"]["gemini"] == "configured"


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_readiness_endpoint_failure(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health/ready returns HTTP 503 when a required dependency fails.
    """
    mock_postgres.return_value = False
    mock_neo4j.return_value = True

    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unready"
    assert data["dependencies"]["postgres"] == "unhealthy"
    assert data["dependencies"]["neo4j"] == "healthy"


@patch("app.services.health_service.HealthService.check_postgres", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_neo4j", new_callable=AsyncMock)
@patch("app.services.health_service.HealthService.check_gemini", return_value=True)
def test_health_summary_endpoint(mock_gemini, mock_neo4j, mock_postgres):
    """
    Test GET /health returns structured operational health document.
    """
    mock_postgres.return_value = True
    mock_neo4j.return_value = True

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["neo4j"] == "healthy"
    assert data["dependencies"]["gemini"] == "configured"


# ============================================================================
# BaseHealthChecker Unit Tests
# ============================================================================


class DummySuccessChecker(BaseHealthChecker):
    async def _check_health(self) -> None:
        pass


class DummyTimeoutChecker(BaseHealthChecker):
    async def _check_health(self) -> None:
        await asyncio.sleep(0.5)


class DummyErrorChecker(BaseHealthChecker):
    async def _check_health(self) -> None:
        raise RuntimeError("Sensitive internal database connection failure")


@pytest.mark.asyncio
async def test_base_health_checker_success():
    checker = DummySuccessChecker(name="test_dep", critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "test_dep"
    assert result.status == HealthStatus.HEALTHY
    assert result.critical is True
    assert result.message is None
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_base_health_checker_timeout():
    checker = DummyTimeoutChecker(name="timeout_dep", critical=True, timeout=0.05)
    result = await checker.check()

    assert result.name == "timeout_dep"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Operation timed out"
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_base_health_checker_unexpected_exception():
    checker = DummyErrorChecker(name="error_dep", critical=False, timeout=1.0)
    result = await checker.check()

    assert result.name == "error_dep"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is False
    assert result.message == "Service check failed"
    assert "Sensitive" not in (result.message or "")


# ============================================================================
# PostgresHealthChecker Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_postgres_checker_success():
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    checker = PostgresHealthChecker(engine=mock_engine, critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "postgres"
    assert result.status == HealthStatus.HEALTHY
    assert result.critical is True
    assert result.message is None
    assert result.latency_ms >= 0.0
    mock_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_postgres_checker_connection_failure():
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = ConnectionRefusedError("Could not connect to server")

    checker = PostgresHealthChecker(engine=mock_engine, critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "postgres"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Service check failed"


@pytest.mark.asyncio
async def test_postgres_checker_timeout():
    class HangingConnection:
        async def __aenter__(self):
            await asyncio.sleep(0.5)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def execute(self, query):
            pass

    mock_engine = MagicMock()
    mock_engine.connect.return_value = HangingConnection()

    checker = PostgresHealthChecker(engine=mock_engine, critical=True, timeout=0.05)
    result = await checker.check()

    assert result.name == "postgres"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message == "Operation timed out"


# ============================================================================
# Neo4jHealthChecker Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_neo4j_checker_success():
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock()

    checker = Neo4jHealthChecker(driver_getter=lambda: mock_driver, critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "neo4j"
    assert result.status == HealthStatus.HEALTHY
    assert result.critical is True
    assert result.message is None
    mock_driver.verify_connectivity.assert_awaited_once()


@pytest.mark.asyncio
async def test_neo4j_checker_uninitialized():
    def uninitialized_getter():
        raise RuntimeError("Neo4j driver has not been initialized.")

    checker = Neo4jHealthChecker(driver_getter=uninitialized_getter, critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "neo4j"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Service check failed"


@pytest.mark.asyncio
async def test_neo4j_checker_connectivity_failure():
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock(side_effect=Exception("Cluster unreachable"))

    checker = Neo4jHealthChecker(driver_getter=lambda: mock_driver, critical=True, timeout=1.0)
    result = await checker.check()

    assert result.name == "neo4j"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Service check failed"


# ============================================================================
# GeminiConfigHealthChecker Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_gemini_config_checker_valid():
    mock_settings = MagicMock(spec=Settings)
    mock_settings.GEMINI_API_KEY = SecretStr("valid_production_gemini_api_key_12345")
    mock_settings.GEMINI_MODEL = "gemini-3.5-flash-lite"

    checker = GeminiConfigHealthChecker(settings_instance=mock_settings, critical=False)
    result = await checker.check()

    assert result.name == "gemini"
    assert result.status == HealthStatus.HEALTHY
    assert result.critical is False
    assert result.message is None


@pytest.mark.asyncio
async def test_gemini_config_checker_empty_key():
    mock_settings = MagicMock(spec=Settings)
    mock_settings.GEMINI_API_KEY = SecretStr("")
    mock_settings.GEMINI_MODEL = "gemini-3.5-flash-lite"

    checker = GeminiConfigHealthChecker(settings_instance=mock_settings, critical=False)
    result = await checker.check()

    assert result.name == "gemini"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is False
    assert result.message == "Service check failed"


@pytest.mark.asyncio
async def test_gemini_config_checker_placeholder_key():
    mock_settings = MagicMock(spec=Settings)
    mock_settings.GEMINI_API_KEY = SecretStr("your_gemini_api_key_here")
    mock_settings.GEMINI_MODEL = "gemini-3.5-flash-lite"

    checker = GeminiConfigHealthChecker(settings_instance=mock_settings, critical=False)
    result = await checker.check()

    assert result.name == "gemini"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is False
    assert result.message == "Service check failed"


@pytest.mark.asyncio
async def test_gemini_config_checker_missing_model():
    mock_settings = MagicMock(spec=Settings)
    mock_settings.GEMINI_API_KEY = SecretStr("valid_production_gemini_api_key_12345")
    mock_settings.GEMINI_MODEL = ""

    checker = GeminiConfigHealthChecker(settings_instance=mock_settings, critical=False)
    result = await checker.check()

    assert result.name == "gemini"
    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is False
    assert result.message == "Service check failed"
