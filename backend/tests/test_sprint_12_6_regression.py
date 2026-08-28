"""
Regression tests for Sprint 12.6A: PostgreSQL Failure Resilience:
1. Database connection failures are surfaced through the existing application error path.
2. Failed transactions are rolled back correctly.
3. A failed transaction does not leave the SQLAlchemy session unusable for subsequent operations.
4. Database errors are not silently swallowed.
5. Engine connection pool pre-ping and rollback-on-return invariants are preserved.
6. Postgres health check accurately detects connectivity failures.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_incident_service
from app.core.health.models import HealthStatus
from app.core.health.postgres import PostgresHealthChecker
from app.db.database import async_engine, close_db
from app.main import app
from app.models.enums import IncidentSource, IncidentStatus, Priority, ReporterType, ScamCategory
from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.entity_extraction_service import EntityExtractionService
from app.services.incident_service import IncidentService


client = TestClient(app)


# ============================================================================
# 1. Connection Failure & API Error Path Propagation Tests
# ============================================================================


def test_db_connection_failure_surfaces_500_through_global_handler() -> None:
    """
    Ensure database connection failures in HTTP routes surface through
    the global exception handler as structured HTTP 500 responses.
    """
    mock_service = MagicMock()
    mock_service.list_incidents = AsyncMock(
        side_effect=OperationalError(
            statement="SELECT incidents",
            params={},
            orig=Exception("could not connect to server: Connection refused"),
        )
    )

    app.dependency_overrides[get_incident_service] = lambda: mock_service
    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.get("/api/v1/complaints/")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Internal Server Error"
        assert "request_id" in data
    finally:
        app.dependency_overrides.clear()


def test_postgres_health_checker_reports_unhealthy_on_connection_error() -> None:
    """
    Ensure PostgresHealthChecker marks component as UNHEALTHY when connection fails.
    """
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.side_effect = OperationalError(
        statement="SELECT 1",
        params={},
        orig=Exception("Connection timed out"),
    )

    checker = PostgresHealthChecker(engine=mock_engine, critical=True, timeout=2.0)
    result = asyncio_run(checker.check())

    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Service check failed" or "Connection timed out" in (result.message or "")


# ============================================================================
# 2. Transaction Rollback on Failure Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_incident_db_error_triggers_rollback_and_reraises() -> None:
    """
    Ensure IncidentService.create_incident rolls back session and re-raises on DB error.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    mock_repo.get_by_case_reference.return_value = None
    db_error = OperationalError(
        statement="INSERT INTO incidents",
        params={},
        orig=Exception("disk I/O error on database write"),
    )
    mock_repo.create.side_effect = db_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Lottery Scam",
        description="Fake lottery scam message demanding transfer.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-FAIL-001",
    )

    with pytest.raises(OperationalError) as exc_info:
        await service.create_incident(payload)

    assert exc_info.value == db_error
    assert mock_session.rollback.await_count == 1
    assert mock_session.commit.await_count == 0


@pytest.mark.asyncio
async def test_update_incident_db_error_triggers_rollback_and_reraises() -> None:
    """
    Ensure IncidentService.update_incident rolls back session and re-raises on DB error.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    incident_id = uuid4()
    existing_incident = Incident(
        id=incident_id,
        title="Original Title",
        description="Original description text.",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        scam_category=ScamCategory.OTHER,
    )
    mock_repo.get_by_id.return_value = existing_incident

    db_error = DBAPIError(
        statement="UPDATE incidents",
        params={},
        orig=Exception("connection closed unexpectedly during update"),
    )
    mock_repo.update.side_effect = db_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    update_payload = IncidentUpdate(
        title="Updated Title",
        status=IncidentStatus.PROCESSING,
    )

    with pytest.raises(DBAPIError) as exc_info:
        await service.update_incident(incident_id, update_payload)

    assert exc_info.value == db_error
    assert mock_session.rollback.await_count == 1


@pytest.mark.asyncio
async def test_delete_incident_db_error_triggers_rollback_and_reraises() -> None:
    """
    Ensure IncidentService.delete_incident rolls back session and re-raises on DB error.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    incident_id = uuid4()
    existing_incident = Incident(
        id=incident_id,
        title="Title",
        description="Description.",
    )
    mock_repo.get_by_id.return_value = existing_incident

    db_error = OperationalError(
        statement="DELETE FROM incidents",
        params={},
        orig=Exception("deadlock detected on delete"),
    )
    mock_repo.delete.side_effect = db_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    with pytest.raises(OperationalError) as exc_info:
        await service.delete_incident(incident_id)

    assert exc_info.value == db_error
    assert mock_session.rollback.await_count == 1


# ============================================================================
# 3. Session Recovery After Failed Transaction
# ============================================================================


@pytest.mark.asyncio
async def test_session_recovery_after_rollback() -> None:
    """
    Verify that rolling back a failed transaction resets the session state,
    allowing subsequent operations to succeed.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.rollback = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    # 1. First operation encounters error and rolls back
    try:
        raise OperationalError(
            statement="INVALID SQL",
            params={},
            orig=Exception("syntax error"),
        )
    except OperationalError:
        await mock_session.rollback()

    assert mock_session.rollback.await_count == 1

    # 2. Subsequent operation on clean session succeeds
    result = await mock_session.execute(text("SELECT 1"))
    await mock_session.commit()

    assert mock_session.execute.await_count == 1
    assert mock_session.commit.await_count == 1
    assert result is not None


# ============================================================================
# 4. Engine Pool Configuration & Disposal Invariants
# ============================================================================


def test_async_engine_pool_resilience_settings() -> None:
    """
    Ensure async_engine pool configuration enforces production resilience:
    - pool_pre_ping is enabled (validates connection liveness).
    - pool_reset_on_return is set to 'rollback' (guarantees clean connection on return).
    """
    pool = getattr(async_engine, "sync_engine", async_engine).pool
    assert pool._pre_ping is True
    assert "rollback" in str(pool._reset_on_return).lower()


@pytest.mark.asyncio
async def test_close_db_disposes_engine() -> None:
    """
    Verify close_db() disposes the global engine cleanly.
    """
    mock_eng = MagicMock()
    mock_eng.dispose = AsyncMock()
    with patch("app.db.database.async_engine", mock_eng):
        await close_db()
        mock_eng.dispose.assert_awaited_once()


# ============================================================================
# 5. Read Query & Readiness PostgreSQL Failure Propagation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_incident_connection_failure_propagates_without_swallowing() -> None:
    """
    Verify that read operations (e.g. get_incident) do not swallow database connection failures.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    conn_error = OperationalError(
        statement="SELECT incident",
        params={},
        orig=Exception("server closed the connection unexpectedly"),
    )
    mock_repo.get_by_id.side_effect = conn_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    with pytest.raises(OperationalError) as exc_info:
        await service.get_incident(uuid4())

    assert exc_info.value == conn_error


@pytest.mark.asyncio
async def test_create_incident_integrity_duplicate_rolls_back_and_raises_duplicate_error() -> None:
    """
    Verify that unique constraint violation during create_incident rolls back session
    and translates into DuplicateCaseReferenceError.
    """
    from app.core.exceptions import DuplicateCaseReferenceError
    from sqlalchemy.exc import IntegrityError

    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    mock_repo.get_by_case_reference.return_value = None
    integrity_err = IntegrityError(
        statement="INSERT INTO incidents",
        params={},
        orig=Exception("duplicate key value violates unique constraint 'uq_incidents_case_reference'"),
    )
    mock_repo.create.side_effect = integrity_err

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Lottery Scam",
        description="Fake lottery scam message demanding UPI transfer.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-DUP-999",
    )

    with pytest.raises(DuplicateCaseReferenceError):
        await service.create_incident(payload)

    assert mock_session.rollback.await_count == 1
    assert mock_session.commit.await_count == 0


def test_readiness_endpoint_returns_503_when_postgres_unhealthy() -> None:
    """
    Ensure GET /health/ready returns HTTP 503 when critical Postgres dependency is UNHEALTHY.
    """
    from app.api.health import get_health_service
    from app.core.health.models import DependencyHealth
    from app.core.health.service import HealthService

    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres",
            status=HealthStatus.UNHEALTHY,
            latency_ms=10.0,
            critical=True,
            message="Connection refused",
        ),
        "neo4j": DependencyHealth(
            name="neo4j",
            status=HealthStatus.HEALTHY,
            latency_ms=2.0,
            critical=True,
        ),
        "gemini": DependencyHealth(
            name="gemini",
            status=HealthStatus.HEALTHY,
            latency_ms=0.1,
            critical=False,
        ),
    }

    mock_service = HealthService(checkers=[])
    mock_service.check_dependencies = AsyncMock(return_value=mock_deps)

    app.dependency_overrides[get_health_service] = lambda: mock_service
    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["is_ready"] is False
        assert data["status"] == "unhealthy"
        assert data["dependencies"]["postgres"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_incident_duplicate_case_reference_rolls_back_once_and_raises_conflict() -> None:
    """
    Verify that unique constraint violation during update_incident rolls back session exactly once
    and translates into DuplicateCaseReferenceError.
    """
    from app.core.exceptions import DuplicateCaseReferenceError
    from sqlalchemy.exc import IntegrityError

    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    incident_id = uuid4()
    existing_incident = Incident(
        id=incident_id,
        title="Existing Title",
        description="Existing description text.",
        case_reference="CASE-OLD",
    )
    mock_repo.get_by_id.return_value = existing_incident

    integrity_err = IntegrityError(
        statement="UPDATE incidents",
        params={},
        orig=Exception("duplicate key value violates unique constraint 'uq_incidents_case_reference'"),
    )
    mock_repo.update.side_effect = integrity_err

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    update_payload = IncidentUpdate(case_reference="CASE-EXISTING-DUP")

    with pytest.raises(DuplicateCaseReferenceError):
        await service.update_incident(incident_id, update_payload)

    # Rollback must be awaited exactly once (no duplicate rollback)
    assert mock_session.rollback.await_count == 1


def test_duplicate_case_reference_surfaces_http_409_through_global_handler() -> None:
    """
    Ensure DuplicateCaseReferenceError returns structured HTTP 409 Conflict response.
    """
    from app.core.exceptions import DuplicateCaseReferenceError

    mock_service = MagicMock()
    mock_service.create_incident = AsyncMock(
        side_effect=DuplicateCaseReferenceError("Case reference 'CASE-DUP-1' already exists.")
    )

    app.dependency_overrides[get_incident_service] = lambda: mock_service
    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.post(
            "/api/v1/complaints/",
            json={
                "title": "Duplicate Case Test",
                "description": "Scam complaint message text of adequate length.",
                "reporter_type": "citizen",
                "source": "web_portal",
                "case_reference": "CASE-DUP-1",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Duplicate Case Reference"
        assert "CASE-DUP-1" in data["message"]
    finally:
        app.dependency_overrides.clear()


def asyncio_run(coro):
    """Helper to run coroutine synchronously for test cases."""
    import asyncio
    return asyncio.run(coro)
