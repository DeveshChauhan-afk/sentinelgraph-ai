"""
Regression tests for Sprint 12.6B: Neo4j Failure Resilience:
1. Neo4j unavailable during startup (connect_neo4j failure handling, driver cleanup, health check, readiness endpoint).
2. Neo4j connection & query failures in GraphRepository are mapped to domain exceptions (GraphPersistenceError, GraphQueryError, GraphConnectionError).
3. Neo4j write failure during complaint ingestion does not corrupt or roll back committed PostgreSQL transactions.
4. Neo4j read failure during timeline/investigation propagates cleanly through domain/API layers.
5. Neo4j driver and session resources are cleaned up cleanly on success and on exception.
6. Neo4j errors are not silently swallowed.
7. PostgreSQL transactional behavior is unaffected by Neo4j failures.
8. Existing (:Complaint)-[:MENTIONS]->(:Entity) relationship invariant remains intact.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from neo4j.exceptions import Neo4jError, ServiceUnavailable
import pytest

from app.core.health.models import HealthStatus
from app.core.health.neo4j import Neo4jHealthChecker
from app.db.neo4j import connect_neo4j, disconnect_neo4j, get_neo4j_driver
import app.db.neo4j as neo4j_module
from app.db.neo4j_schema import init_neo4j_schema
from app.graph.builder import GraphBuilder
from app.graph.exceptions import (
    GraphConnectionError,
    GraphPersistenceError,
    GraphQueryError,
)
from app.graph.models import GraphData, RelationshipType
from app.graph.repository import GraphRepository
from app.main import app
from app.models.enums import IncidentSource, ReporterType
from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.schemas.entity_extraction import ExtractedEntities, ExtractedEntity
from app.schemas.incident import IncidentCreate
from app.services.entity_extraction_service import EntityExtractionService
from app.graph.service import GraphService
from app.services.incident_processing_service import IncidentProcessingService
from app.services.incident_service import IncidentService
from app.services.timeline_service import TimelineService


client = TestClient(app)


# ============================================================================
# 1. Startup & Connection Lifecycle Resilience Tests
# ============================================================================


@pytest.mark.asyncio
async def test_connect_neo4j_failure_cleans_up_driver_and_leaves_none() -> None:
    """
    Ensure connect_neo4j cleanly closes driver and leaves _driver as None
    if verify_connectivity fails.
    """
    neo4j_module._driver = None

    mock_driver = MagicMock()
    mock_driver.verify_connectivity = AsyncMock(
        side_effect=ServiceUnavailable("Failed to establish connection to Neo4j AuraDB")
    )
    mock_driver.close = AsyncMock()

    with patch("app.db.neo4j.AsyncGraphDatabase.driver", return_value=mock_driver):
        with pytest.raises(ServiceUnavailable):
            await connect_neo4j()

    assert neo4j_module._driver is None
    mock_driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_neo4j_closes_driver_cleanly() -> None:
    """
    Ensure disconnect_neo4j closes the active driver and resets _driver to None.
    """
    mock_driver = MagicMock()
    mock_driver.close = AsyncMock()
    neo4j_module._driver = mock_driver

    await disconnect_neo4j()

    assert neo4j_module._driver is None
    mock_driver.close.assert_awaited_once()


def test_get_neo4j_driver_uninitialized_raises_runtime_error() -> None:
    """
    Ensure get_neo4j_driver raises RuntimeError if driver has not been initialized.
    """
    neo4j_module._driver = None
    with pytest.raises(RuntimeError, match="Neo4j driver has not been initialized"):
        get_neo4j_driver()


def test_neo4j_health_checker_reports_unhealthy_on_connection_error() -> None:
    """
    Ensure Neo4jHealthChecker marks component as UNHEALTHY when connectivity check fails.
    """
    mock_driver = MagicMock()
    mock_driver.verify_connectivity = AsyncMock(
        side_effect=ServiceUnavailable("Connection refused by Neo4j host")
    )

    checker = Neo4jHealthChecker(
        driver_getter=lambda: mock_driver,
        critical=True,
        timeout=2.0,
    )
    result = asyncio.run(checker.check())

    assert result.status == HealthStatus.UNHEALTHY
    assert result.critical is True
    assert result.message == "Service check failed"


def test_readiness_endpoint_returns_503_when_neo4j_unhealthy() -> None:
    """
    Ensure GET /health/ready returns HTTP 503 when critical Neo4j dependency is UNHEALTHY.
    """
    from app.api.health import get_health_service
    from app.core.health.models import DependencyHealth
    from app.core.health.service import HealthService

    mock_deps = {
        "postgres": DependencyHealth(
            name="postgres",
            status=HealthStatus.HEALTHY,
            latency_ms=1.5,
            critical=True,
        ),
        "neo4j": DependencyHealth(
            name="neo4j",
            status=HealthStatus.UNHEALTHY,
            latency_ms=2.0,
            critical=True,
            message="Connection refused",
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
        assert data["dependencies"]["neo4j"]["status"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# 2. Neo4j Schema Constraint Initialization Resilience
# ============================================================================


@pytest.mark.asyncio
async def test_init_neo4j_schema_translates_neo4j_error_to_graph_persistence_error() -> None:
    """
    Ensure init_neo4j_schema wraps Neo4jError in GraphPersistenceError.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Constraint creation syntax error"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    with pytest.raises(GraphPersistenceError, match="Neo4j schema constraint initialization failed"):
        await init_neo4j_schema(driver=mock_driver)


@pytest.mark.asyncio
async def test_init_neo4j_schema_translates_connection_error_to_graph_connection_error() -> None:
    """
    Ensure init_neo4j_schema wraps general connection failure in GraphConnectionError.
    """
    mock_driver = MagicMock()
    mock_driver.session.side_effect = ServiceUnavailable("Cannot reach Neo4j instance")

    with pytest.raises(GraphConnectionError, match="Neo4j connection failed during schema initialization"):
        await init_neo4j_schema(driver=mock_driver)


# ============================================================================
# 3. Graph Repository Exception Translation & Session Cleanup Tests
# ============================================================================


@pytest.mark.asyncio
async def test_repository_save_graph_handles_neo4j_error_and_cleans_session() -> None:
    """
    Verify save_graph raises GraphPersistenceError on Neo4jError and cleans up session.
    """
    mock_session = MagicMock()
    mock_session.execute_write = AsyncMock(side_effect=Neo4jError("Write conflict"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    graph = GraphData(nodes=[], relationships=[])

    with pytest.raises(GraphPersistenceError, match="Failed to persist graph"):
        await repo.save_graph(graph)

    mock_driver.session.return_value.__aenter__.assert_awaited_once()
    mock_driver.session.return_value.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_save_graph_handles_connection_error() -> None:
    """
    Verify save_graph raises GraphConnectionError on connection loss.
    """
    mock_driver = MagicMock()
    mock_driver.session.side_effect = ConnectionResetError("Connection lost")

    repo = GraphRepository(driver=mock_driver)
    graph = GraphData(nodes=[], relationships=[])

    with pytest.raises(GraphConnectionError, match="Neo4j connection failed"):
        await repo.save_graph(graph)


@pytest.mark.asyncio
async def test_repository_find_entity_handles_neo4j_error() -> None:
    """
    Verify find_entity wraps Neo4jError into GraphPersistenceError.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Cypher syntax error"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    with pytest.raises(GraphPersistenceError, match="Failed to query graph entity"):
        await repo.find_entity("+919876543210")

    mock_driver.session.return_value.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_get_connected_complaints_handles_query_and_connection_errors() -> None:
    """
    Verify get_connected_complaints maps Neo4jError -> GraphQueryError and Exception -> GraphConnectionError.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Memory limit exceeded"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    with pytest.raises(GraphQueryError, match="Failed to retrieve connected complaints"):
        await repo.get_connected_complaints("+919876543210")

    # Connection error test
    mock_session.run = AsyncMock(side_effect=ServiceUnavailable("Connection timed out"))
    with pytest.raises(GraphConnectionError, match="Neo4j connection failed"):
        await repo.get_connected_complaints("+919876543210")


@pytest.mark.asyncio
async def test_repository_get_entity_occurrences_handles_errors() -> None:
    """
    Verify get_entity_occurrences raises GraphQueryError and GraphConnectionError appropriately.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Transaction terminated"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    with pytest.raises(GraphQueryError, match="Failed to retrieve entity occurrences"):
        await repo.get_entity_occurrences("test@upi")


@pytest.mark.asyncio
async def test_repository_get_subgraph_handles_query_and_connection_errors() -> None:
    """
    Verify get_subgraph wraps Neo4jError in GraphQueryError and Connection in GraphConnectionError.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Subgraph traversal limit reached"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    with pytest.raises(GraphQueryError, match="Failed to retrieve graph visualization subgraph"):
        await repo.get_subgraph("phone:+919876543210", depth=2)

    mock_session.run = AsyncMock(side_effect=ConnectionError("Server unreachable"))
    with pytest.raises(GraphConnectionError, match="Neo4j connection failed"):
        await repo.get_subgraph("phone:+919876543210", depth=2)


@pytest.mark.asyncio
async def test_repository_get_graph_summary_handles_query_and_connection_errors() -> None:
    """
    Verify get_graph_summary wraps Neo4jError in GraphQueryError and Connection in GraphConnectionError.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Database internal error"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)
    with pytest.raises(GraphQueryError, match="Failed to retrieve graph summary statistics"):
        await repo.get_graph_summary()

    mock_session.run = AsyncMock(side_effect=ServiceUnavailable("Connection timed out"))
    with pytest.raises(GraphConnectionError, match="Neo4j connection failed"):
        await repo.get_graph_summary()


@pytest.mark.asyncio
async def test_repository_get_top_connected_and_shared_entities_handle_errors() -> None:
    """
    Verify get_top_connected_entities and get_shared_entities handle Neo4j failures cleanly.
    """
    mock_session = MagicMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Query timed out"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=None)

    repo = GraphRepository(driver=mock_driver)

    with pytest.raises(GraphQueryError, match="Failed to retrieve top connected entities"):
        await repo.get_top_connected_entities(limit=5)

    with pytest.raises(GraphQueryError, match="Failed to retrieve shared entities"):
        await repo.get_shared_entities(minimum_complaints=2)


# ============================================================================
# 4. Ingestion Resilience & PostgreSQL Transaction Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_incident_creation_succeeds_and_postgres_committed_when_neo4j_write_fails() -> None:
    """
    Ensure IncidentService.create_incident commits PostgreSQL incident even if downstream
    Neo4j graph persistence raises GraphPersistenceError or GraphConnectionError.
    PostgreSQL transaction must NOT be rolled back.
    """
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock(spec=GraphService)

    created_incident = Incident(
        id=uuid4(),
        title="UPI Scam Complaint",
        description="Fake QR code scan requested ₹50,000 to victim@upi",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-NEO-001",
        created_at=datetime.now(timezone.utc),
    )

    mock_repo.get_by_case_reference.return_value = None
    mock_repo.create.return_value = created_incident
    mock_entity_service.extract_entities.return_value = ExtractedEntities()
    mock_graph_service.build_and_persist.side_effect = GraphPersistenceError(
        "Neo4j cluster unavailable during write transaction"
    )

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="UPI Scam Complaint",
        description="Fake QR code scan requested ₹50,000 to victim@upi",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-NEO-001",
    )

    result = await service.create_incident(payload)

    # Incident returned
    assert result == created_incident
    # PostgreSQL was committed
    mock_session.commit.assert_awaited_once()
    # PostgreSQL was NOT rolled back
    mock_session.rollback.assert_not_awaited()
    # Downstream graph write was attempted
    mock_graph_service.build_and_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_incident_processing_service_swallows_graph_error_safely() -> None:
    """
    Ensure IncidentProcessingService catches GraphError and logs it without crashing the task.
    """
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock(spec=GraphService)

    mock_entity_service.extract_entities.return_value = ExtractedEntities()
    mock_graph_service.build_and_persist.side_effect = GraphConnectionError(
        "Cannot reach Neo4j database"
    )

    processing_service = IncidentProcessingService(
        entity_extraction_service=mock_entity_service,
        graph_service=mock_graph_service,
    )

    incident = Incident(
        id=uuid4(),
        title="Test Incident",
        description="Description containing test@bank.com",
        created_at=datetime.now(timezone.utc),
    )

    # Should not raise exception
    await processing_service.process_incident(incident)
    mock_graph_service.build_and_persist.assert_awaited_once()


# ============================================================================
# 5. Read-Only Investigation Resilience & Error Propagation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_timeline_service_propagates_neo4j_error_without_swallowing() -> None:
    """
    Verify TimelineService does not silently swallow GraphQueryError or GraphConnectionError.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    mock_repo.get_connected_complaints.side_effect = GraphConnectionError(
        "AuraDB connection terminated"
    )

    timeline_service = TimelineService(repository=mock_repo)

    with pytest.raises(GraphConnectionError, match="AuraDB connection terminated"):
        await timeline_service.build_timeline("victim@upi")


def test_graph_api_endpoint_surfaces_500_on_neo4j_failure() -> None:
    """
    Ensure API endpoints surface HTTP 500 when Neo4j query fails unexpectedly.
    """
    mock_query_service = MagicMock()
    mock_query_service.get_entity = AsyncMock(
        side_effect=GraphConnectionError("Failed to reach Neo4j graph cluster")
    )

    from app.api.dependencies import get_graph_query_service

    app.dependency_overrides[get_graph_query_service] = lambda: mock_query_service
    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.get("/api/v1/graph/entity/test-entity")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Internal Server Error"
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# 6. Graph Model & Relationship Invariant Tests
# ============================================================================


def test_graph_builder_mentions_relationship_invariant() -> None:
    """
    Verify that (:Complaint)-[:MENTIONS]->(:Entity) relationship structure remains intact.
    """
    builder = GraphBuilder()
    complaint_id = uuid4()
    now = datetime.now(timezone.utc)

    extracted = ExtractedEntities(
        phone_numbers=[ExtractedEntity(value="+919876543210", confidence=0.95)],
        upi_ids=[ExtractedEntity(value="scammer@okhdfcbank", confidence=0.98)],
        emails=[ExtractedEntity(value="fake@scam.org", confidence=0.90)],
        urls=[ExtractedEntity(value="https://phishing.site/login", confidence=0.92)],
        bank_accounts=[ExtractedEntity(value="987654321012", confidence=0.88)],
        organizations=[ExtractedEntity(value="Scam Corp", confidence=0.85)],
        persons=[ExtractedEntity(value="John Scammer", confidence=0.80)],
        locations=[ExtractedEntity(value="Kolkata", confidence=0.75)],
    )

    graph = builder.build(
        complaint_id=complaint_id,
        created_at=now,
        entities=extracted,
    )

    complaint_node_id = f"complaint:{complaint_id}"
    assert len(graph.nodes) == 9  # 1 complaint + 8 entities
    assert len(graph.relationships) == 8

    for rel in graph.relationships:
        assert rel.source == complaint_node_id
        assert rel.type == RelationshipType.MENTIONS
        assert rel.target.split(":")[0] in (
            "phone",
            "upi",
            "email",
            "url",
            "bank",
            "org",
            "person",
            "location",
        )
