"""
Regression and integrity tests for Sprint 12.2:
1. PostgreSQL database-level uniqueness constraint on case_reference.
2. SQLAlchemy model declaration of UniqueConstraint on case_reference.
3. Service-level race condition handling: IntegrityError translated to DuplicateCaseReferenceError.
4. Selective translation: unrelated IntegrityErrors (e.g., check constraints) are NOT converted to duplicate-case errors.
5. Concurrent creation race-condition simulation.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateCaseReferenceError
from app.models.enums import (
    IncidentSource,
    IncidentStatus,
    Priority,
    ReporterType,
    ScamCategory,
)
from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.schemas.entity_extraction import ExtractedEntities
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.entity_extraction_service import EntityExtractionService
from app.services.incident_service import IncidentService


# ============================================================================
# 1. Model & Schema Invariant Tests
# ============================================================================


def test_incident_model_declares_unique_constraint_on_case_reference() -> None:
    """
    Ensure the SQLAlchemy Incident model declares a unique constraint on case_reference.
    """
    table = Incident.__table__

    # Verify column exists and remains nullable
    case_ref_col = table.c.case_reference
    assert case_ref_col is not None
    assert case_ref_col.nullable is True

    # Verify unique constraint is defined on case_reference
    unique_constraints = [
        c for c in table.constraints if isinstance(c, UniqueConstraint)
    ]
    matching_constraints = [
        c for c in unique_constraints if "case_reference" in [col.name for col in c.columns]
    ]

    assert len(matching_constraints) == 1, "Expected UniqueConstraint on case_reference"
    constraint = matching_constraints[0]
    assert constraint.name == "uq_incidents_case_reference"


# ============================================================================
# 2. Duplicate / Race Condition Exception Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_incident_early_duplicate_check_preserved() -> None:
    """
    Ensure application-level pre-check immediately raises DuplicateCaseReferenceError
    before initiating database write operations.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    existing_incident = Incident(
        id=uuid4(),
        title="Existing Incident",
        description="Existing incident description with sufficient length.",
        case_reference="CASE-EARLY-DUP",
    )
    mock_repo.get_by_case_reference.return_value = existing_incident

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="New Incident Title",
        description="New incident description with sufficient length.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-EARLY-DUP",
    )

    with pytest.raises(DuplicateCaseReferenceError, match="already exists"):
        await service.create_incident(payload)

    # Repository create and session commit must not be called
    assert mock_repo.create.await_count == 0
    assert mock_session.commit.await_count == 0


@pytest.mark.asyncio
async def test_create_incident_catches_database_uniqueness_integrity_error() -> None:
    """
    Ensure when concurrent requests race past the application check and hit the
    database unique constraint, the IntegrityError is translated to DuplicateCaseReferenceError.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    # Pre-check passes (e.g. concurrent race)
    mock_repo.get_by_case_reference.return_value = None

    # Simulate database unique constraint violation
    db_integrity_error = IntegrityError(
        statement="INSERT INTO incidents (case_reference) VALUES ('CASE-RACE-001')",
        params={"case_reference": "CASE-RACE-001"},
        orig=Exception('duplicate key value violates unique constraint "uq_incidents_case_reference"'),
    )
    mock_repo.create.side_effect = db_integrity_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Race Incident Title",
        description="Detailed description of fraudulent incident for race test.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-RACE-001",
    )

    with pytest.raises(DuplicateCaseReferenceError) as exc_info:
        await service.create_incident(payload)

    assert "CASE-RACE-001" in str(exc_info.value)
    # Session must be rolled back
    assert mock_session.rollback.await_count == 1
    assert mock_session.commit.await_count == 0


@pytest.mark.asyncio
async def test_create_incident_does_not_convert_unrelated_integrity_errors() -> None:
    """
    Ensure unrelated database IntegrityErrors (such as check constraints or NOT NULL)
    are NOT converted to DuplicateCaseReferenceError and are re-raised.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    mock_repo.get_by_case_reference.return_value = None

    # Simulate unrelated check constraint failure (e.g. risk score range)
    unrelated_integrity_error = IntegrityError(
        statement="INSERT INTO incidents (risk_score) VALUES (1.5)",
        params={"risk_score": 1.5},
        orig=Exception('new row for relation "incidents" violates check constraint "ck_incidents_check_risk_score_range"'),
    )
    mock_repo.create.side_effect = unrelated_integrity_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Invalid Risk Score Incident",
        description="Detailed description of incident that fails check constraint.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-VALID-REF",
    )

    with pytest.raises(IntegrityError) as exc_info:
        await service.create_incident(payload)

    # Must be the raw IntegrityError, not DuplicateCaseReferenceError
    assert "ck_incidents_check_risk_score_range" in str(exc_info.value)
    assert mock_session.rollback.await_count == 1


@pytest.mark.asyncio
async def test_update_incident_handles_uniqueness_integrity_error() -> None:
    """
    Ensure updating an incident with a conflicting case_reference translates
    database IntegrityError to DuplicateCaseReferenceError.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    incident_id = uuid4()
    existing_incident = Incident(
        id=incident_id,
        title="Incident to Update",
        description="Existing incident description with sufficient length.",
        case_reference="CASE-ORIGINAL",
    )
    mock_repo.get_by_id.return_value = existing_incident

    db_integrity_error = IntegrityError(
        statement="UPDATE incidents SET case_reference = 'CASE-CONFLICT' WHERE id = ...",
        params={"case_reference": "CASE-CONFLICT"},
        orig=Exception('duplicate key value violates unique constraint "uq_incidents_case_reference"'),
    )
    mock_repo.update.side_effect = db_integrity_error

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    update_payload = IncidentUpdate(
        case_reference="CASE-CONFLICT",
    )

    with pytest.raises(DuplicateCaseReferenceError):
        await service.update_incident(incident_id, update_payload)

    assert mock_session.rollback.await_count == 1


# ============================================================================
# 3. Concurrency Simulation Test
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_incident_creation_race_condition_handled() -> None:
    """
    Simulate two concurrent requests A and B creating the same case_reference.
    Request A succeeds, Request B encounters database unique violation and is
    safely caught and translated into DuplicateCaseReferenceError.
    """
    mock_session_a = AsyncMock(spec=AsyncSession)
    mock_session_b = AsyncMock(spec=AsyncSession)

    mock_repo_a = AsyncMock(spec=IncidentRepository)
    mock_repo_b = AsyncMock(spec=IncidentRepository)

    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_entity_service.extract_entities.return_value = ExtractedEntities(
        phone_numbers=[],
        upi_ids=[],
        emails=[],
        urls=[],
        bank_accounts=[],
        organizations=[],
        persons=[],
        locations=[],
    )
    mock_graph_service = AsyncMock()
    mock_graph_service.build_and_persist.return_value = MagicMock(
        nodes_persisted=1,
        relationships_persisted=0,
        duration_ms=5.0,
    )

    # Both requests check get_by_case_reference at the same time and find None
    mock_repo_a.get_by_case_reference.return_value = None
    mock_repo_b.get_by_case_reference.return_value = None

    # Request A succeeds
    incident_a = Incident(
        id=uuid4(),
        title="Concurrent Incident A",
        description="Detailed description for concurrent test incident A.",
        status=IncidentStatus.NEW,
        priority=Priority.HIGH,
        scam_category=ScamCategory.UPI_FRAUD,
        case_reference="CASE-CONCURRENT-001",
        created_at=datetime.now(timezone.utc),
    )
    mock_repo_a.create.return_value = incident_a

    # Request B fails with database unique constraint violation
    db_integrity_error = IntegrityError(
        statement="INSERT INTO incidents (case_reference) VALUES ('CASE-CONCURRENT-001')",
        params={"case_reference": "CASE-CONCURRENT-001"},
        orig=Exception('duplicate key value violates unique constraint "uq_incidents_case_reference"'),
    )
    mock_repo_b.create.side_effect = db_integrity_error

    service_a = IncidentService(
        repository=mock_repo_a,
        entity_extraction_service=mock_entity_service,
        session=mock_session_a,
        graph_service=mock_graph_service,
    )

    service_b = IncidentService(
        repository=mock_repo_b,
        entity_extraction_service=mock_entity_service,
        session=mock_session_b,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Concurrent Incident",
        description="Detailed description for concurrent test incident.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-CONCURRENT-001",
    )

    # Execute both concurrently
    results = await asyncio.gather(
        service_a.create_incident(payload),
        service_b.create_incident(payload),
        return_exceptions=True,
    )

    # One must succeed with Incident, one must fail with DuplicateCaseReferenceError
    assert isinstance(results[0], Incident)
    assert results[0].id == incident_a.id
    assert mock_session_a.commit.await_count == 1

    assert isinstance(results[1], DuplicateCaseReferenceError)
    assert mock_session_b.rollback.await_count == 1
