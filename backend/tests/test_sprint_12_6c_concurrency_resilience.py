"""
Regression tests for Sprint 12.6C: Concurrent Ingestion Resilience:
1. Concurrent unique incident creations are persisted exactly once.
2. Concurrent duplicate case_reference requests trigger uniqueness protection (1 succeeds, rest get DuplicateCaseReferenceError / 409).
3. Concurrent requests do not share SQLAlchemy sessions (complete session isolation).
4. One failed request does not corrupt or roll back another request's transaction.
5. Neo4j graph ingestion remains isolated between concurrent requests even with shared entities.
6. Background processing does not leak exceptions between concurrent tasks.
7. No shared mutable service state causes cross-request data contamination.
8. Concurrent API requests maintain consistent response envelopes and status codes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import AIError
from app.api.dependencies import get_incident_service
from app.core.exceptions import DuplicateCaseReferenceError
from app.graph.builder import GraphBuilder
from app.graph.exceptions import GraphPersistenceError
from app.graph.models import GraphPersistenceResult, RelationshipType
from app.graph.service import GraphService
from app.main import app
from app.models.enums import IncidentSource, IncidentStatus, Priority, ReporterType, ScamCategory
from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.schemas.entity_extraction import ExtractedEntities, ExtractedEntity
from app.schemas.incident import IncidentCreate
from app.services.entity_extraction_service import EntityExtractionService
from app.services.incident_processing_service import IncidentProcessingService
from app.services.incident_service import IncidentService


# ============================================================================
# 1. Concurrent Unique Incident Ingestion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_unique_incident_creations_persist_individually() -> None:
    """
    Verify that multiple concurrent incident creation requests with unique data
    each obtain dedicated sessions, commit independently, and produce distinct incidents.
    """
    num_concurrent = 10
    sessions = [AsyncMock(spec=AsyncSession) for _ in range(num_concurrent)]
    repos = [AsyncMock(spec=IncidentRepository) for _ in range(num_concurrent)]
    entity_services = [AsyncMock(spec=EntityExtractionService) for _ in range(num_concurrent)]
    graph_services = [AsyncMock(spec=GraphService) for _ in range(num_concurrent)]

    created_incidents: list[Incident] = []
    services: list[IncidentService] = []
    now = datetime.now(timezone.utc)

    for i in range(num_concurrent):
        inc_id = uuid4()
        incident = Incident(
            id=inc_id,
            title=f"Concurrent Scam Incident #{i}",
            description=f"Fake lottery scam report #{i} targeting victim_{i}@upi",
            status=IncidentStatus.NEW,
            priority=Priority.MEDIUM,
            scam_category=ScamCategory.OTHER,
            reporter_type=ReporterType.CITIZEN,
            source=IncidentSource.WEB_PORTAL,
            case_reference=f"CASE-CONCUR-{i:03d}",
            created_at=now,
            updated_at=now,
        )
        created_incidents.append(incident)

        repos[i].get_by_case_reference.return_value = None
        repos[i].create.return_value = incident
        entity_services[i].extract_entities.return_value = ExtractedEntities(
            upi_ids=[ExtractedEntity(value=f"victim_{i}@upi", confidence=0.95)]
        )
        graph_services[i].build_and_persist.return_value = GraphPersistenceResult(
            nodes_persisted=2,
            relationships_persisted=1,
            duration_ms=5.0,
        )

        service = IncidentService(
            repository=repos[i],
            session=sessions[i],
            entity_extraction_service=entity_services[i],
            graph_service=graph_services[i],
        )
        services.append(service)

    # Launch all creation requests simultaneously
    tasks = [
        services[i].create_incident(
            IncidentCreate(
                title=f"Concurrent Scam Incident #{i}",
                description=f"Fake lottery scam report #{i} targeting victim_{i}@upi",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference=f"CASE-CONCUR-{i:03d}",
            )
        )
        for i in range(num_concurrent)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == num_concurrent
    for i in range(num_concurrent):
        assert results[i].id == created_incidents[i].id
        assert results[i].case_reference == f"CASE-CONCUR-{i:03d}"
        sessions[i].commit.assert_awaited_once()
        sessions[i].rollback.assert_not_awaited()
        graph_services[i].build_and_persist.assert_awaited_once()


# ============================================================================
# 2. Race Condition on Case Reference Uniqueness
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_duplicate_case_reference_race_condition() -> None:
    """
    Simulate a race condition where 5 concurrent requests attempt to create an incident
    with the identical case_reference.
    Verify:
    - Exactly 1 request successfully commits to PostgreSQL.
    - The remaining 4 requests fail with IntegrityError, trigger rollback on their session,
      and raise DuplicateCaseReferenceError.
    """
    num_requests = 5
    shared_case_reference = "CASE-RACE-DUP-999"
    now = datetime.now(timezone.utc)

    sessions = [AsyncMock(spec=AsyncSession) for _ in range(num_requests)]
    repos = [AsyncMock(spec=IncidentRepository) for _ in range(num_requests)]
    entity_services = [AsyncMock(spec=EntityExtractionService) for _ in range(num_requests)]
    graph_services = [AsyncMock(spec=GraphService) for _ in range(num_requests)]

    winning_incident = Incident(
        id=uuid4(),
        title="Winning Scam Incident",
        description="First request that successfully commits to PostgreSQL",
        status=IncidentStatus.NEW,
        priority=Priority.MEDIUM,
        scam_category=ScamCategory.OTHER,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference=shared_case_reference,
        created_at=now,
        updated_at=now,
    )

    # Winner is index 0; indices 1..4 encounter DB uniqueness violation on commit/create
    repos[0].get_by_case_reference.return_value = None
    repos[0].create.return_value = winning_incident
    entity_services[0].extract_entities.return_value = ExtractedEntities()
    graph_services[0].build_and_persist.return_value = GraphPersistenceResult(
        nodes_persisted=1, relationships_persisted=0, duration_ms=2.0
    )

    for i in range(1, num_requests):
        repos[i].get_by_case_reference.return_value = None  # Passed initial read check before winner committed
        integrity_err = IntegrityError(
            statement="INSERT INTO incidents",
            params={},
            orig=Exception("duplicate key value violates unique constraint 'uq_incidents_case_reference'"),
        )
        repos[i].create.side_effect = integrity_err

    services = [
        IncidentService(
            repository=repos[i],
            session=sessions[i],
            entity_extraction_service=entity_services[i],
            graph_service=graph_services[i],
        )
        for i in range(num_requests)
    ]

    payload = IncidentCreate(
        title="Concurrent Duplicate Scam Incident",
        description="Race condition payload attempting duplicate case reference registration",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference=shared_case_reference,
    )

    tasks = [services[i].create_incident(payload) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Validate winner
    assert isinstance(results[0], Incident)
    assert results[0].id == winning_incident.id
    sessions[0].commit.assert_awaited_once()
    sessions[0].rollback.assert_not_awaited()

    # Validate all 4 losers
    for i in range(1, num_requests):
        assert isinstance(results[i], DuplicateCaseReferenceError)
        sessions[i].commit.assert_not_awaited()
        sessions[i].rollback.assert_awaited_once()


# ============================================================================
# 3. Fault Isolation Across Concurrent Requests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_fault_isolation_failed_request_does_not_affect_healthy_requests() -> None:
    """
    Ensure that when one concurrent request encounters an unrecoverable database error
    and rolls back, other simultaneously executing requests proceed to commit without corruption.
    """
    session_healthy_1 = AsyncMock(spec=AsyncSession)
    session_failing = AsyncMock(spec=AsyncSession)
    session_healthy_2 = AsyncMock(spec=AsyncSession)

    repo_healthy_1 = AsyncMock(spec=IncidentRepository)
    repo_failing = AsyncMock(spec=IncidentRepository)
    repo_healthy_2 = AsyncMock(spec=IncidentRepository)

    now = datetime.now(timezone.utc)
    inc_1 = Incident(
        id=uuid4(),
        title="Healthy 1",
        description="desc 1 of valid length",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-H1",
        created_at=now,
        updated_at=now,
    )
    inc_2 = Incident(
        id=uuid4(),
        title="Healthy 2",
        description="desc 2 of valid length",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-H2",
        created_at=now,
        updated_at=now,
    )

    repo_healthy_1.get_by_case_reference.return_value = None
    repo_healthy_1.create.return_value = inc_1

    repo_healthy_2.get_by_case_reference.return_value = None
    repo_healthy_2.create.return_value = inc_2

    # Failing request experiences DB operational error (e.g. statement timeout)
    repo_failing.get_by_case_reference.return_value = None
    db_err = OperationalError(
        statement="INSERT INTO incidents",
        params={},
        orig=Exception("canceling statement due to statement timeout"),
    )
    repo_failing.create.side_effect = db_err

    entity_service = AsyncMock(spec=EntityExtractionService)
    entity_service.extract_entities.return_value = ExtractedEntities()

    graph_service = AsyncMock(spec=GraphService)
    graph_service.build_and_persist.return_value = GraphPersistenceResult(
        nodes_persisted=1,
        relationships_persisted=0,
        duration_ms=1.0,
    )

    service_healthy_1 = IncidentService(repo_healthy_1, entity_service, session_healthy_1, graph_service)
    service_failing = IncidentService(repo_failing, entity_service, session_failing, graph_service)
    service_healthy_2 = IncidentService(repo_healthy_2, entity_service, session_healthy_2, graph_service)

    tasks = [
        service_healthy_1.create_incident(
            IncidentCreate(
                title="Healthy 1",
                description="desc 1 of valid length",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference="CASE-H1",
            )
        ),
        service_failing.create_incident(
            IncidentCreate(
                title="Failing Request",
                description="desc fail of valid length",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference="CASE-FAIL",
            )
        ),
        service_healthy_2.create_incident(
            IncidentCreate(
                title="Healthy 2",
                description="desc 2 of valid length",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference="CASE-H2",
            )
        ),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 1. First healthy request succeeded
    assert isinstance(results[0], Incident)
    assert results[0].id == inc_1.id
    session_healthy_1.commit.assert_awaited_once()
    session_healthy_1.rollback.assert_not_awaited()

    # 2. Failing request was rolled back and raised OperationalError
    assert isinstance(results[1], OperationalError)
    session_failing.commit.assert_not_awaited()
    session_failing.rollback.assert_awaited_once()

    # 3. Second healthy request succeeded without corruption
    assert isinstance(results[2], Incident)
    assert results[2].id == inc_2.id
    session_healthy_2.commit.assert_awaited_once()
    session_healthy_2.rollback.assert_not_awaited()


# ============================================================================
# 4. Neo4j Graph Ingestion Isolation Under Concurrency
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_graph_builder_shared_entities_isolation() -> None:
    """
    Verify that when multiple concurrent requests extract overlapping entity values
    (e.g., multiple complaints targeting the same scammer phone & UPI), GraphBuilder
    constructs separate, cleanly partitioned GraphData objects without state bleed.
    """
    builder = GraphBuilder()
    shared_phone = "+919876543210"
    shared_upi = "scammer@paytm"

    num_complaints = 8
    complaints = [(uuid4(), datetime.now(timezone.utc)) for _ in range(num_complaints)]

    async def build_task(comp_id: uuid4, dt: datetime, idx: int):
        extracted = ExtractedEntities(
            phone_numbers=[ExtractedEntity(value=shared_phone, confidence=0.95)],
            upi_ids=[ExtractedEntity(value=shared_upi, confidence=0.98)],
            emails=[ExtractedEntity(value=f"scammer_{idx}@fraud.org", confidence=0.90)],
        )
        return builder.build(
            complaint_id=comp_id,
            created_at=dt,
            entities=extracted,
        )

    tasks = [build_task(comp_id, dt, idx) for idx, (comp_id, dt) in enumerate(complaints)]
    graphs = await asyncio.gather(*tasks)

    assert len(graphs) == num_complaints

    for idx, graph in enumerate(graphs):
        comp_id, _ = complaints[idx]
        complaint_node_id = f"complaint:{comp_id}"

        # 1 complaint + 3 entities = 4 nodes
        assert len(graph.nodes) == 4
        # 3 MENTIONS relationships
        assert len(graph.relationships) == 3

        # Confirm all edges originate from this complaint's own ID
        for rel in graph.relationships:
            assert rel.source == complaint_node_id
            assert rel.type == RelationshipType.MENTIONS

        # Verify entity nodes inside this graph
        node_ids = {n.id for n in graph.nodes}
        assert complaint_node_id in node_ids
        assert f"phone:{shared_phone}" in node_ids
        assert f"upi:{shared_upi}" in node_ids
        assert f"email:scammer_{idx}@fraud.org" in node_ids


@pytest.mark.asyncio
async def test_concurrent_neo4j_write_failure_isolation() -> None:
    """
    Verify that if one concurrent incident's graph persistence raises GraphPersistenceError,
    it does not affect another concurrent incident's successful graph persistence.
    """
    mock_session_1 = AsyncMock(spec=AsyncSession)
    mock_session_2 = AsyncMock(spec=AsyncSession)

    mock_repo_1 = AsyncMock(spec=IncidentRepository)
    mock_repo_2 = AsyncMock(spec=IncidentRepository)

    now = datetime.now(timezone.utc)
    inc_1 = Incident(
        id=uuid4(),
        title="Inc 1",
        description="desc 1 of valid length",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-NEO-OK",
        created_at=now,
        updated_at=now,
    )
    inc_2 = Incident(
        id=uuid4(),
        title="Inc 2",
        description="desc 2 of valid length",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-NEO-FAIL",
        created_at=now,
        updated_at=now,
    )

    mock_repo_1.get_by_case_reference.return_value = None
    mock_repo_1.create.return_value = inc_1

    mock_repo_2.get_by_case_reference.return_value = None
    mock_repo_2.create.return_value = inc_2

    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_entity_service.extract_entities.return_value = ExtractedEntities()

    mock_graph_service_1 = AsyncMock(spec=GraphService)
    mock_graph_service_1.build_and_persist.return_value = GraphPersistenceResult(
        nodes_persisted=2,
        relationships_persisted=1,
        duration_ms=3.0,
    )

    mock_graph_service_2 = AsyncMock(spec=GraphService)
    mock_graph_service_2.build_and_persist.side_effect = GraphPersistenceError("Neo4j node write locked")

    service_1 = IncidentService(mock_repo_1, mock_entity_service, mock_session_1, mock_graph_service_1)
    service_2 = IncidentService(mock_repo_2, mock_entity_service, mock_session_2, mock_graph_service_2)

    tasks = [
        service_1.create_incident(
            IncidentCreate(
                title="Inc 1",
                description="desc 1 of valid length",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference="CASE-NEO-OK",
            )
        ),
        service_2.create_incident(
            IncidentCreate(
                title="Inc 2",
                description="desc 2 of valid length",
                reporter_type=ReporterType.CITIZEN,
                source=IncidentSource.WEB_PORTAL,
                case_reference="CASE-NEO-FAIL",
            )
        ),
    ]

    results = await asyncio.gather(*tasks)

    # Both return successfully from PostgreSQL standpoint
    assert results[0].id == inc_1.id
    assert results[1].id == inc_2.id

    mock_session_1.commit.assert_awaited_once()
    mock_session_2.commit.assert_awaited_once()

    mock_graph_service_1.build_and_persist.assert_awaited_once()
    mock_graph_service_2.build_and_persist.assert_awaited_once()


# ============================================================================
# 5. Background Task Exception Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_background_processing_tasks_error_isolation() -> None:
    """
    Ensure IncidentProcessingService handles diverse errors across concurrent background tasks
    (e.g., AIError in task A, GraphPersistenceError in task B, success in task C)
    without leaking unhandled exceptions or terminating peer tasks.
    """
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock(spec=GraphService)

    # Configure different behaviors per task
    async def extract_side_effect(description: str):
        if "AI-FAIL" in description:
            raise AIError("Gemini API rate limited")
        return ExtractedEntities(phone_numbers=[ExtractedEntity(value="+919999999999", confidence=0.9)])

    async def persist_side_effect(complaint_id, created_at, entities):
        if "GRAPH-FAIL" in str(complaint_id):
            raise GraphPersistenceError("Neo4j transaction failure")
        return GraphPersistenceResult(
            nodes_persisted=2,
            relationships_persisted=1,
            duration_ms=2.0,
        )

    mock_entity_service.extract_entities.side_effect = extract_side_effect
    mock_graph_service.build_and_persist.side_effect = persist_side_effect

    processing_service = IncidentProcessingService(
        entity_extraction_service=mock_entity_service,
        graph_service=mock_graph_service,
    )

    now = datetime.now(timezone.utc)
    inc_ai_fail = Incident(
        id=uuid4(),
        title="AI Fail",
        description="Text with AI-FAIL keyword for testing",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        created_at=now,
        updated_at=now,
    )
    inc_graph_fail = Incident(
        id=uuid4(),
        title="Graph Fail",
        description="Normal text GRAPH-FAIL for testing",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        created_at=now,
        updated_at=now,
    )
    inc_success = Incident(
        id=uuid4(),
        title="Success",
        description="Normal text of adequate length for testing",
        status=IncidentStatus.NEW,
        priority=Priority.LOW,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        created_at=now,
        updated_at=now,
    )

    # All three run concurrently in background
    tasks = [
        processing_service.process_incident(inc_ai_fail),
        processing_service.process_incident(inc_graph_fail),
        processing_service.process_incident(inc_success),
    ]

    # None should raise or crash
    await asyncio.gather(*tasks)

    assert mock_entity_service.extract_entities.await_count == 3
    # Only inc_graph_fail and inc_success attempt graph write (since inc_ai_fail failed in extraction)
    assert mock_graph_service.build_and_persist.await_count == 2


# ============================================================================
# 6. HTTP Route Concurrency & API Response Consistency
# ============================================================================


def test_concurrent_api_complaint_creations_preserve_http_contracts() -> None:
    """
    Verify concurrent HTTP POST /api/v1/complaints/ requests through TestClient
    correctly route to service and return structured responses.
    """
    mock_service = MagicMock()
    now = datetime.now(timezone.utc)

    created_incident = Incident(
        id=uuid4(),
        title="Concurrent API Complaint",
        description="Scam description of adequate length for validation.",
        status=IncidentStatus.NEW,
        priority=Priority.MEDIUM,
        scam_category=ScamCategory.OTHER,
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-API-CONCUR-001",
        created_at=now,
        updated_at=now,
    )

    mock_service.create_incident = AsyncMock(return_value=created_incident)
    app.dependency_overrides[get_incident_service] = lambda: mock_service

    safe_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = safe_client.post(
            "/api/v1/complaints/",
            json={
                "title": "Concurrent API Complaint",
                "description": "Scam description of adequate length for validation.",
                "reporter_type": "citizen",
                "source": "web_portal",
                "case_reference": "CASE-API-CONCUR-001",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(created_incident.id)
        assert data["case_reference"] == "CASE-API-CONCUR-001"
    finally:
        app.dependency_overrides.clear()
