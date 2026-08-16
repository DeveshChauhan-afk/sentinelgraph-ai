"""
Unit and integration tests for production health endpoints (/health/live, /health/ready, /health),
concrete dependency health checkers (Postgres, Neo4j, Gemini),
and HealthService aggregation.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from pydantic import SecretStr

from app.api.health import get_health_service
from app.core.config import Settings, settings
from app.core.health.base import BaseHealthChecker
from app.core.health.gemini import GeminiConfigHealthChecker
from app.core.health.models import DependencyHealth, HealthStatus
from app.core.health.neo4j import Neo4jHealthChecker
from app.core.health.postgres import PostgresHealthChecker
from app.core.health.service import HealthService
from app.main import app

client = TestClient(app)


# ============================================================================
# HTTP Health Endpoints Tests
# ============================================================================


def test_liveness_endpoint():
    """
    Test GET /health/live returns HTTP 200 with LivenessResponse and does not invoke HealthService.
    """
    with patch.object(HealthService, "check_dependencies") as mock_check:
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        mock_check.assert_not_called()

        # Also verify via API v1 prefix
        v1_response = client.get("/api/v1/health/live")
        assert v1_response.status_code == 200
        assert v1_response.json()["status"] == "healthy"
        mock_check.assert_not_called()


def test_readiness_endpoint_all_healthy():
    """
    Test GET /health/ready returns HTTP 200 when all dependencies are healthy.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres", status=HealthStatus.HEALTHY, latency_ms=1.5, critical=True
        ),
        "neo4j": DependencyHealth(
            name="neo4j", status=HealthStatus.HEALTHY, latency_ms=2.0, critical=True
        ),
        "gemini": DependencyHealth(
            name="gemini", status=HealthStatus.HEALTHY, latency_ms=0.1, critical=False
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["is_ready"] is True
        assert data["dependencies"]["postgres"]["status"] == "healthy"
        assert data["dependencies"]["neo4j"]["status"] == "healthy"
        assert data["dependencies"]["gemini"]["status"] == "healthy"

        # Also verify via API v1 prefix
        v1_response = client.get("/api/v1/health/ready")
        assert v1_response.status_code == 200
        assert v1_response.json()["is_ready"] is True
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_degraded_soft_failure():
    """
    Test GET /health/ready returns HTTP 200 and status=degraded when non-critical Gemini fails.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres", status=HealthStatus.HEALTHY, latency_ms=1.5, critical=True
        ),
        "neo4j": DependencyHealth(
            name="neo4j", status=HealthStatus.HEALTHY, latency_ms=2.0, critical=True
        ),
        "gemini": DependencyHealth(
            name="gemini",
            status=HealthStatus.UNHEALTHY,
            latency_ms=0.1,
            critical=False,
            message="Service check failed",
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["is_ready"] is True
        assert data["dependencies"]["gemini"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_critical_postgres_failure():
    """
    Test GET /health/ready returns HTTP 503 and status=unhealthy when critical PostgreSQL fails.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres",
            status=HealthStatus.UNHEALTHY,
            latency_ms=1.5,
            critical=True,
            message="Service check failed",
        ),
        "neo4j": DependencyHealth(
            name="neo4j", status=HealthStatus.HEALTHY, latency_ms=2.0, critical=True
        ),
        "gemini": DependencyHealth(
            name="gemini", status=HealthStatus.HEALTHY, latency_ms=0.1, critical=False
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["is_ready"] is False
        assert data["dependencies"]["postgres"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_critical_neo4j_failure():
    """
    Test GET /health/ready returns HTTP 503 and status=unhealthy when critical Neo4j fails.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres", status=HealthStatus.HEALTHY, latency_ms=1.5, critical=True
        ),
        "neo4j": DependencyHealth(
            name="neo4j",
            status=HealthStatus.UNHEALTHY,
            latency_ms=2.0,
            critical=True,
            message="Service check failed",
        ),
        "gemini": DependencyHealth(
            name="gemini", status=HealthStatus.HEALTHY, latency_ms=0.1, critical=False
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["is_ready"] is False
        assert data["dependencies"]["neo4j"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


def test_health_summary_endpoint_healthy():
    """
    Test GET /health returns structured operational health document with HTTP 200.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres", status=HealthStatus.HEALTHY, latency_ms=1.5, critical=True
        ),
        "neo4j": DependencyHealth(
            name="neo4j", status=HealthStatus.HEALTHY, latency_ms=2.0, critical=True
        ),
        "gemini": DependencyHealth(
            name="gemini", status=HealthStatus.HEALTHY, latency_ms=0.1, critical=False
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert data["environment"] == ("development" if settings.DEBUG else "production")
        assert "postgres" in data["dependencies"]
        assert "neo4j" in data["dependencies"]
        assert "gemini" in data["dependencies"]

        # Also verify via API v1 prefix
        v1_response = client.get("/api/v1/health")
        assert v1_response.status_code == 200
        assert v1_response.json()["status"] == "healthy"
    finally:
        app.dependency_overrides.clear()


def test_health_summary_endpoint_unhealthy_returns_200():
    """
    Test GET /health returns HTTP 200 diagnostic document even when a critical dependency fails.
    """
    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres",
            status=HealthStatus.UNHEALTHY,
            latency_ms=1.5,
            critical=True,
            message="Service check failed",
        ),
        "neo4j": DependencyHealth(
            name="neo4j", status=HealthStatus.HEALTHY, latency_ms=2.0, critical=True
        ),
        "gemini": DependencyHealth(
            name="gemini", status=HealthStatus.HEALTHY, latency_ms=0.1, critical=False
        ),
    }
    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["postgres"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


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


# ============================================================================
# HealthService Aggregation Unit Tests
# ============================================================================


class MockDependencyChecker(BaseHealthChecker):
    def __init__(self, name: str, critical: bool, should_succeed: bool):
        super().__init__(name=name, critical=critical, timeout=1.0)
        self.should_succeed = should_succeed

    async def _check_health(self) -> None:
        if not self.should_succeed:
            raise RuntimeError(f"Simulated failure for {self.name}")


@pytest.mark.asyncio
async def test_health_service_all_healthy():
    checkers = [
        MockDependencyChecker("postgres", critical=True, should_succeed=True),
        MockDependencyChecker("neo4j", critical=True, should_succeed=True),
        MockDependencyChecker("gemini", critical=False, should_succeed=True),
    ]
    service = HealthService(checkers=checkers)
    deps = await service.check_dependencies()

    assert len(deps) == 3
    assert deps["postgres"].status == HealthStatus.HEALTHY
    assert deps["neo4j"].status == HealthStatus.HEALTHY
    assert deps["gemini"].status == HealthStatus.HEALTHY
    assert service.determine_status(deps) == HealthStatus.HEALTHY
    assert service.determine_readiness(deps) is True


@pytest.mark.asyncio
async def test_health_service_degraded_non_critical_failure():
    checkers = [
        MockDependencyChecker("postgres", critical=True, should_succeed=True),
        MockDependencyChecker("neo4j", critical=True, should_succeed=True),
        MockDependencyChecker("gemini", critical=False, should_succeed=False),
    ]
    service = HealthService(checkers=checkers)
    deps = await service.check_dependencies()

    assert deps["postgres"].status == HealthStatus.HEALTHY
    assert deps["neo4j"].status == HealthStatus.HEALTHY
    assert deps["gemini"].status == HealthStatus.UNHEALTHY
    assert service.determine_status(deps) == HealthStatus.DEGRADED
    assert service.determine_readiness(deps) is True


@pytest.mark.asyncio
async def test_health_service_unhealthy_postgres_failure():
    checkers = [
        MockDependencyChecker("postgres", critical=True, should_succeed=False),
        MockDependencyChecker("neo4j", critical=True, should_succeed=True),
        MockDependencyChecker("gemini", critical=False, should_succeed=True),
    ]
    service = HealthService(checkers=checkers)
    deps = await service.check_dependencies()

    assert deps["postgres"].status == HealthStatus.UNHEALTHY
    assert deps["neo4j"].status == HealthStatus.HEALTHY
    assert deps["gemini"].status == HealthStatus.HEALTHY
    assert service.determine_status(deps) == HealthStatus.UNHEALTHY
    assert service.determine_readiness(deps) is False


@pytest.mark.asyncio
async def test_health_service_unhealthy_neo4j_failure():
    checkers = [
        MockDependencyChecker("postgres", critical=True, should_succeed=True),
        MockDependencyChecker("neo4j", critical=True, should_succeed=False),
        MockDependencyChecker("gemini", critical=False, should_succeed=True),
    ]
    service = HealthService(checkers=checkers)
    deps = await service.check_dependencies()

    assert deps["postgres"].status == HealthStatus.HEALTHY
    assert deps["neo4j"].status == HealthStatus.UNHEALTHY
    assert deps["gemini"].status == HealthStatus.HEALTHY
    assert service.determine_status(deps) == HealthStatus.UNHEALTHY
    assert service.determine_readiness(deps) is False


@pytest.mark.asyncio
async def test_health_service_multiple_critical_failures():
    checkers = [
        MockDependencyChecker("postgres", critical=True, should_succeed=False),
        MockDependencyChecker("neo4j", critical=True, should_succeed=False),
        MockDependencyChecker("gemini", critical=False, should_succeed=False),
    ]
    service = HealthService(checkers=checkers)
    deps = await service.check_dependencies()

    assert deps["postgres"].status == HealthStatus.UNHEALTHY
    assert deps["neo4j"].status == HealthStatus.UNHEALTHY
    assert deps["gemini"].status == HealthStatus.UNHEALTHY
    assert service.determine_status(deps) == HealthStatus.UNHEALTHY
    assert service.determine_readiness(deps) is False


@pytest.mark.asyncio
async def test_health_service_empty_checkers():
    service = HealthService(checkers=[])
    deps = await service.check_dependencies()

    assert deps == {}
    assert service.determine_status(deps) == HealthStatus.HEALTHY
    assert service.determine_readiness(deps) is True


class BarrierCheckerA(BaseHealthChecker):
    def __init__(self, entered_a: asyncio.Event, entered_b: asyncio.Event):
        super().__init__(name="barrier_a", critical=True, timeout=2.0)
        self.entered_a = entered_a
        self.entered_b = entered_b

    async def _check_health(self) -> None:
        self.entered_a.set()
        await asyncio.wait_for(self.entered_b.wait(), timeout=1.0)


class BarrierCheckerB(BaseHealthChecker):
    def __init__(self, entered_a: asyncio.Event, entered_b: asyncio.Event):
        super().__init__(name="barrier_b", critical=True, timeout=2.0)
        self.entered_a = entered_a
        self.entered_b = entered_b

    async def _check_health(self) -> None:
        self.entered_b.set()
        await asyncio.wait_for(self.entered_a.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_health_service_concurrent_execution():
    """
    Verifies that checkers execute concurrently using an asyncio.Event barrier.
    If executed sequentially, BarrierCheckerA would hang and timeout waiting for
    BarrierCheckerB's event.
    """
    event_a = asyncio.Event()
    event_b = asyncio.Event()

    checker_a = BarrierCheckerA(event_a, event_b)
    checker_b = BarrierCheckerB(event_a, event_b)

    service = HealthService(checkers=[checker_a, checker_b])
    deps = await service.check_dependencies()

    assert deps["barrier_a"].status == HealthStatus.HEALTHY
    assert deps["barrier_b"].status == HealthStatus.HEALTHY
    assert service.determine_status(deps) == HealthStatus.HEALTHY
    assert service.determine_readiness(deps) is True
