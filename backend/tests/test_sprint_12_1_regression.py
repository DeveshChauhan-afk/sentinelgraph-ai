"""
Regression and lifecycle tests for Sprint 12.1:
1. Incident creation single transaction commit (no redundant commit).
2. Investigation timer lifecycle and idempotency on duplicate stop calls.
3. Investigation flow timer stop call verification (no duplicate stop).
4. Explicit SQLAlchemy async engine disposal on application shutdown.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.events import shutdown
from app.core.exceptions import DuplicateCaseReferenceError
from app.db.database import close_db
from app.main import app, lifespan
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
from app.schemas.incident import IncidentCreate
from app.schemas.investigation import (
    InvestigationEvidence,
    InvestigationReport,
    InvestigationRequest,
    InvestigationResponse,
    InvestigationTargetType,
)
from app.services.entity_extraction_service import EntityExtractionService
from app.services.incident_service import IncidentService
from app.services.investigation.performance import InvestigationTimer
from app.services.investigation.prompt_builder import PromptBuilder
from app.services.investigation.report_parser import ReportParser
from app.services.investigation_service import InvestigationService


# ============================================================================
# 1. Incident Creation Single Transaction Commit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_incident_creation_performs_single_commit() -> None:
    """
    Ensure IncidentService.create_incident executes session.commit() exactly once.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    incident_id = uuid4()
    created_dt = datetime.now(timezone.utc)
    created_incident = Incident(
        id=incident_id,
        title="Test Scam Incident",
        description="Fake lottery scam message demanding UPI transfer.",
        status=IncidentStatus.NEW,
        priority=Priority.HIGH,
        scam_category=ScamCategory.UPI_FRAUD,
        case_reference="CASE-12-001",
        created_at=created_dt,
    )

    mock_repo.get_by_case_reference.return_value = None
    mock_repo.create.return_value = created_incident
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

    persist_result_mock = MagicMock(
        nodes_persisted=2,
        relationships_persisted=1,
        duration_ms=12.5,
    )
    mock_graph_service.build_and_persist.return_value = persist_result_mock

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Test Scam Incident",
        description="Fake lottery scam message demanding UPI transfer.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-12-001",
    )

    result = await service.create_incident(payload)

    assert result.id == incident_id
    assert mock_session.commit.await_count == 1
    assert mock_session.rollback.await_count == 0
    mock_repo.create.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_incident_creation_rollback_on_repository_error() -> None:
    """
    Ensure IncidentService.create_incident rolls back and does not commit on error.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    mock_repo.get_by_case_reference.return_value = None
    mock_repo.create.side_effect = RuntimeError("DB write error")

    service = IncidentService(
        repository=mock_repo,
        entity_extraction_service=mock_entity_service,
        session=mock_session,
        graph_service=mock_graph_service,
    )

    payload = IncidentCreate(
        title="Test Scam Incident",
        description="Fake lottery scam message demanding UPI transfer.",
        reporter_type=ReporterType.CITIZEN,
        source=IncidentSource.WEB_PORTAL,
        case_reference="CASE-12-002",
    )

    with pytest.raises(RuntimeError, match="DB write error"):
        await service.create_incident(payload)

    assert mock_session.commit.await_count == 0
    assert mock_session.rollback.await_count == 1


@pytest.mark.asyncio
async def test_incident_creation_duplicate_case_reference_aborts_before_transaction() -> None:
    """
    Ensure DuplicateCaseReferenceError prevents repository create and commit.
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_repo = AsyncMock(spec=IncidentRepository)
    mock_entity_service = AsyncMock(spec=EntityExtractionService)
    mock_graph_service = AsyncMock()

    existing = Incident(
        id=uuid4(),
        title="Existing Incident",
        description="Existing incident description with sufficient length.",
        case_reference="CASE-DUP",
    )
    mock_repo.get_by_case_reference.return_value = existing

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
        case_reference="CASE-DUP",
    )

    with pytest.raises(DuplicateCaseReferenceError):
        await service.create_incident(payload)

    assert mock_repo.create.await_count == 0
    assert mock_session.commit.await_count == 0


# ============================================================================
# 2. Investigation Timer Lifecycle and Correctness Tests
# ============================================================================


def test_investigation_timer_measures_elapsed_duration() -> None:
    """
    Ensure start and stop accurately compute duration in milliseconds.
    """
    timer = InvestigationTimer()

    with patch("app.services.investigation.performance.perf_counter") as mock_perf:
        mock_perf.side_effect = [10.0, 10.05]
        timer.start("Gemini")
        timer.stop("Gemini")

    assert "Gemini" in timer._marks
    assert timer._marks["Gemini"] == pytest.approx(50.0)


def test_investigation_timer_repeated_stop_cannot_corrupt_state() -> None:
    """
    Ensure repeated stop() calls on the same stage do not recalculate or corrupt timing.
    """
    timer = InvestigationTimer()

    with patch("app.services.investigation.performance.perf_counter") as mock_perf:
        # start at 100.0, first stop at 100.04 (40ms)
        mock_perf.side_effect = [100.0, 100.04, 100.10, 100.50]
        timer.start("Graph Queries")
        timer.stop("Graph Queries")

        initial_duration = timer._marks["Graph Queries"]
        assert initial_duration == pytest.approx(40.0)

        # Duplicate stop calls must be safely ignored and not corrupt the duration
        timer.stop("Graph Queries")
        assert timer._marks["Graph Queries"] == pytest.approx(40.0)

        timer.stop("Graph Queries")
        assert timer._marks["Graph Queries"] == pytest.approx(40.0)


def test_investigation_timer_stop_unstarted_stage_is_noop() -> None:
    """
    Ensure stopping an unstarted stage does not raise an exception or create invalid entries.
    """
    timer = InvestigationTimer()
    timer.stop("UnstartedStage")
    assert "UnstartedStage" not in timer._marks


def test_investigation_timer_restart_stage_records_new_timing() -> None:
    """
    Ensure calling start() again after stop() allows a fresh measurement.
    """
    timer = InvestigationTimer()

    with patch("app.services.investigation.performance.perf_counter") as mock_perf:
        # 1st cycle: 10.0 -> 10.02 (20ms)
        # 2nd cycle: 20.0 -> 20.05 (50ms)
        mock_perf.side_effect = [10.0, 10.02, 20.0, 20.05]
        timer.start("Gemini")
        timer.stop("Gemini")
        assert timer._marks["Gemini"] == pytest.approx(20.0)

        timer.start("Gemini")
        timer.stop("Gemini")
        assert timer._marks["Gemini"] == pytest.approx(50.0)


def test_investigation_timer_summary_logging() -> None:
    """
    Ensure timer.summary executes cleanly and formats metrics without error.
    """
    timer = InvestigationTimer()
    with patch("app.services.investigation.performance.perf_counter") as mock_perf:
        mock_perf.side_effect = [1.0, 1.01, 1.02, 1.05, 1.06]
        timer.start("Stage A")
        timer.stop("Stage A")
        timer.start("Stage B")
        timer.stop("Stage B")

    assert len(timer._marks) == 2
    # summary() should run without exception
    timer.summary()


# ============================================================================
# 3. Investigation Service Timer Stops Verification
# ============================================================================


@pytest.mark.asyncio
async def test_investigation_service_stops_each_timer_once() -> None:
    """
    Ensure InvestigationService.investigate stops every stage exactly once (no duplicate stop for Gemini).
    """
    mock_graph = AsyncMock()
    mock_ai = AsyncMock()
    mock_prompt_builder = MagicMock(spec=PromptBuilder)
    mock_report_parser = MagicMock(spec=ReportParser)

    mock_prompt_builder.build.return_value = "Generated Prompt"
    mock_ai.generate_content.return_value = '{"risk_level": "LOW", "confidence": 0.9, "findings": []}'

    parsed_report = InvestigationReport(
        summary="Low risk entity",
        risk_level="LOW",
        confidence=0.9,
        findings=[],
        key_entities=[],
        recommended_actions=[],
    )
    mock_report_parser.parse.return_value = parsed_report

    service = InvestigationService(
        graph_service=mock_graph,
        ai_client=mock_ai,
        prompt_builder=mock_prompt_builder,
        report_parser=mock_report_parser,
    )

    mock_evidence = MagicMock(spec=InvestigationEvidence)
    service.build_evidence = AsyncMock(return_value=mock_evidence)

    request = InvestigationRequest(
        target_type=InvestigationTargetType.PHONE,
        target_value="+919876543210",
    )

    # Track start and stop calls on InvestigationTimer
    start_calls: list[str] = []
    stop_calls: list[str] = []

    original_start = InvestigationTimer.start
    original_stop = InvestigationTimer.stop

    def tracked_start(self: InvestigationTimer, stage: str) -> None:
        start_calls.append(stage)
        original_start(self, stage)

    def tracked_stop(self: InvestigationTimer, stage: str) -> None:
        stop_calls.append(stage)
        original_stop(self, stage)

    with (
        patch.object(InvestigationTimer, "start", side_effect=tracked_start, autospec=True),
        patch.object(InvestigationTimer, "stop", side_effect=tracked_stop, autospec=True),
        patch.object(service._cache, "get", return_value=None),
        patch.object(service._cache, "set"),
    ):
        response = await service.investigate(request)

    assert isinstance(response, InvestigationResponse)
    assert response.report.risk_level == "LOW"

    # Verify each stage was started and stopped exactly once in correct order
    assert start_calls == ["Cache", "Graph Queries", "Prompt", "Gemini", "Parser"]
    assert stop_calls == ["Cache", "Graph Queries", "Prompt", "Gemini", "Parser"]

    # Explicitly verify Gemini was stopped only once
    assert stop_calls.count("Gemini") == 1


# ============================================================================
# 4. SQLAlchemy Engine Disposal on Application Shutdown
# ============================================================================


@pytest.mark.asyncio
async def test_close_db_disposes_engine() -> None:
    """
    Ensure close_db() calls async_engine.dispose().
    """
    mock_engine = AsyncMock(spec=AsyncEngine)
    with patch("app.db.database.async_engine", mock_engine):
        await close_db()
        mock_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_events_shutdown_invokes_close_db_and_disconnect_neo4j() -> None:
    """
    Ensure core events shutdown invokes both close_db and disconnect_neo4j.
    """
    with (
        patch("app.core.events.disconnect_neo4j", new_callable=AsyncMock) as mock_neo4j_disconnect,
        patch("app.core.events.close_db", new_callable=AsyncMock) as mock_close_db,
    ):
        mock_app = MagicMock()
        await shutdown(mock_app)

        mock_neo4j_disconnect.assert_awaited_once()
        mock_close_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_context_executes_startup_and_shutdown() -> None:
    """
    Ensure FastAPI lifespan context manager executes startup and shutdown.
    """
    with (
        patch("app.main.startup", new_callable=AsyncMock) as mock_startup,
        patch("app.main.shutdown", new_callable=AsyncMock) as mock_shutdown,
    ):
        async with lifespan(app):
            mock_startup.assert_awaited_once_with(app)
            assert mock_shutdown.await_count == 0

        mock_shutdown.assert_awaited_once_with(app)
