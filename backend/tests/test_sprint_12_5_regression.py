"""
Regression tests for Sprint 12.5A: Sensitive Logging Cleanup:
1. Raw Gemini response text is NOT logged during investigation or entity extraction.
2. Full prompt contents and complaint text are NOT logged.
3. Sensitive entity values (phone numbers, UPI IDs, emails, bank accounts, names) are NOT logged in investigation/entity flows.
4. Safe operational metadata (request/correlation ID, status, counts, latency, risk levels) is retained.
5. Prometheus metrics and label design remain unchanged and correct.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest
from loguru import logger
from pydantic import SecretStr

from app.core.config import Settings
from app.core.logger import setup_logger
from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_total,
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)
from app.schemas.entity_extraction import ExtractedEntities
from app.schemas.investigation import (
    InvestigationReport,
    InvestigationRequest,
    InvestigationResponse,
    InvestigationTargetType,
)
from app.schemas.timeline import (
    TimelineResponse,
)
from app.services.entity_extraction_service import EntityExtractionService
from app.services.investigation.cache import InvestigationCache
from app.services.investigation_report_service import InvestigationReportService
from app.services.investigation_service import InvestigationService
from app.services.timeline_service import TimelineService


def _build_test_settings() -> Settings:
    return Settings(
        SECRET_KEY=SecretStr("test-secret-key-01234567890123456789012345678901"),
        DATABASE_HOST="localhost",
        DATABASE_NAME="test_db",
        DATABASE_USER="test_user",
        DATABASE_PASSWORD=SecretStr("test_pass"),
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD=SecretStr("neo4j_pass"),
        GEMINI_API_KEY=SecretStr("test-gemini-key"),
        GEMINI_MODEL="gemini-3.5-flash-lite",
        GEMINI_TIMEOUT_SECONDS=60.0,
        GEMINI_MAX_RETRIES=3,
    )


# ============================================================================
# 1. Sensitive Investigation Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_investigation_service_does_not_log_raw_response_or_target_value() -> None:
    """
    Ensure InvestigationService does not log raw Gemini response or sensitive target_value.
    """
    sensitive_phone = "+919876543210"
    sensitive_raw_llm = '{"risk_level": "HIGH", "confidence": 0.95, "findings": ["Suspicious payment pattern"]}'

    from app.graph.models import GraphNode
    from app.graph.query_models import (
        EntityRiskResponse,
        FraudRingResponse,
        GraphNeighborsResponse,
        RelatedIncidentsResponse,
        RiskMetrics,
        SharedEntityResponse,
    )
    from app.schemas.investigation import InvestigationEvidence

    node = GraphNode(id="n1", label="Phone", properties={"value": sensitive_phone})
    mock_evidence = InvestigationEvidence(
        neighbors=GraphNeighborsResponse(entity=node, neighbors=[]),
        related_incidents=RelatedIncidentsResponse(entity=node, incidents=[]),
        risk=EntityRiskResponse(
            entity=node,
            risk_score=90,
            risk_level="HIGH",
            metrics=RiskMetrics(
                incident_count=1,
                neighbor_count=0,
                phone_count=1,
                upi_count=0,
                email_count=0,
                organization_count=0,
            ),
            reasons=["High risk score"],
        ),
        fraud_ring=FraudRingResponse(
            entity=node,
            nodes=[],
            incidents=[],
            total_nodes=0,
            total_incidents=0,
        ),
        shared_entities=SharedEntityResponse(
            entity=node,
            complaints=[],
            complaint_count=0,
        ),
    )

    mock_graph = MagicMock()
    mock_ai = MagicMock()
    mock_ai.generate_content = AsyncMock(return_value=sensitive_raw_llm)

    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build = MagicMock(return_value="structured prompt text")

    mock_parser = MagicMock()
    mock_parser.parse = MagicMock(
        return_value=InvestigationReport(
            summary="High risk fraud network detected.",
            risk_level="HIGH",
            confidence=0.95,
            findings=["Suspicious payment pattern"],
            key_entities=["phone"],
            recommended_actions=["Freeze payment identifiers"],
        )
    )

    service = InvestigationService(
        graph_service=mock_graph,
        ai_client=mock_ai,
        prompt_builder=mock_prompt_builder,
        report_parser=mock_parser,
    )
    service.build_evidence = AsyncMock(return_value=mock_evidence)

    captured_logs: list[str] = []
    handler_id = logger.add(lambda msg: captured_logs.append(msg))

    try:
        req = InvestigationRequest(
            target_type=InvestigationTargetType.PHONE,
            target_value=sensitive_phone,
        )
        res = await service.investigate(req)
        assert isinstance(res, InvestigationResponse)

        combined_logs = " ".join(captured_logs)

        # 1. Verify sensitive phone number is NOT logged
        assert sensitive_phone not in combined_logs

        # 2. Verify raw Gemini response is NOT logged
        assert "RAW GEMINI RESPONSE" not in combined_logs
        assert sensitive_raw_llm not in combined_logs

        # 3. Verify safe operational metadata IS logged
        assert "target_type" in combined_logs
        assert "Investigation complete" in combined_logs

    finally:
        logger.remove(handler_id)


# ============================================================================
# 2. Sensitive Entity Extraction Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_entity_extraction_service_does_not_log_sensitive_entities_or_complaint() -> None:
    """
    Ensure EntityExtractionService logs only entity counts and not raw extracted entities.
    """
    sensitive_complaint = "Victim transferred 50000 to fraudster@okaxis from account 1234567890."
    sensitive_entities_json = (
        '{"phone_numbers": [], "upi_ids": [{"value": "fraudster@okaxis", "confidence": 0.9}], '
        '"emails": [], "urls": [], "bank_accounts": [{"value": "1234567890", "confidence": 0.95}], '
        '"organizations": [], "persons": [{"value": "John Doe", "confidence": 0.85}], "locations": []}'
    )

    mock_ai = MagicMock()
    mock_ai.generate_content = AsyncMock(return_value=sensitive_entities_json)

    service = EntityExtractionService(ai_client=mock_ai)

    captured_logs: list[str] = []
    handler_id = logger.add(lambda msg: captured_logs.append(msg))

    try:
        result = await service.extract_entities(sensitive_complaint)
        assert isinstance(result, ExtractedEntities)

        combined_logs = " ".join(captured_logs)

        # 1. Verify sensitive values are NOT logged
        assert "fraudster@okaxis" not in combined_logs
        assert "1234567890" not in combined_logs
        assert "John Doe" not in combined_logs

        # 2. Verify safe counts metadata IS logged
        assert "counts=" in combined_logs
        assert "Entity extraction completed successfully" in combined_logs

    finally:
        logger.remove(handler_id)


# ============================================================================
# 3. Investigation Cache Logging Tests
# ============================================================================


def test_investigation_cache_does_not_log_target_values() -> None:
    """
    Ensure InvestigationCache logs only target_type and not the raw sensitive target value in cache key.
    """
    cache = InvestigationCache(ttl_seconds=60)
    sensitive_key = "phone:+919988776655"

    captured_logs: list[str] = []
    handler_id = logger.add(lambda msg: captured_logs.append(msg), level="DEBUG")

    try:
        # Cache Miss
        assert cache.get(sensitive_key) is None
        # Cache Set
        cache.set(sensitive_key, {"dummy": "data"})
        # Cache Hit
        assert cache.get(sensitive_key) == {"dummy": "data"}

        combined_logs = " ".join(captured_logs)

        # Verify sensitive phone number in key is NOT logged
        assert "+919988776655" not in combined_logs
        assert "phone:+919988776655" not in combined_logs

        # Verify operational cache status is logged with target_type
        assert "Investigation cache MISS (target_type=phone)" in combined_logs
        assert "Investigation cache HIT (target_type=phone)" in combined_logs

    finally:
        logger.remove(handler_id)


# ============================================================================
# 4. Investigation Report Service Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_investigation_report_service_does_not_log_target_value() -> None:
    """
    Ensure InvestigationReportService logs correlation IDs and report IDs without exposing target_value.
    """
    sensitive_email = "suspect_hacker@darknet.org"

    mock_summary_service = MagicMock()
    mock_summary_service.build_summary = AsyncMock()

    mock_context_builder = MagicMock()
    mock_context_builder.build_report_context = MagicMock()

    mock_prompt_builder = MagicMock()
    mock_prompt_builder.build_prompt_request = MagicMock()

    mock_llm_client = MagicMock()
    mock_llm_client.generate = AsyncMock()

    mock_report = MagicMock()
    mock_report.report_id = "RPT-TEST12345"
    mock_report.telemetry = MagicMock(latency_ms=123.45)

    mock_parser = MagicMock()
    mock_parser.parse_report = MagicMock(return_value=mock_report)

    service = InvestigationReportService(
        summary_service=mock_summary_service,
        context_builder=mock_context_builder,
        prompt_builder=mock_prompt_builder,
        llm_client=mock_llm_client,
        report_parser=mock_parser,
    )

    captured_logs: list[str] = []
    handler_id = logger.add(lambda msg: captured_logs.append(msg))

    try:
        report = await service.generate_report(
            entity_value=sensitive_email,
            target_type="EMAIL",
        )
        assert report.report_id == "RPT-TEST12345"

        combined_logs = " ".join(captured_logs)

        # 1. Verify sensitive email is NOT logged
        assert sensitive_email not in combined_logs

        # 2. Verify correlation_id, report_id, and telemetry are logged
        assert "Starting end-to-end report generation" in combined_logs
        assert "RPT-TEST12345" in combined_logs
        assert "123.45ms" in combined_logs

    finally:
        logger.remove(handler_id)


# ============================================================================
# 5. Timeline Service Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_timeline_service_does_not_log_raw_target() -> None:
    """
    Ensure TimelineService logs operational summary without dumping raw target values.
    """
    sensitive_account = "ACC-9988112233"

    mock_repo = MagicMock()
    mock_repo.get_connected_complaints = AsyncMock(return_value=[])

    service = TimelineService(repository=mock_repo)

    captured_logs: list[str] = []
    handler_id = logger.add(lambda msg: captured_logs.append(msg))

    try:
        res = await service.build_timeline(sensitive_account)
        assert isinstance(res, TimelineResponse)

        combined_logs = " ".join(captured_logs)

        # Verify sensitive account is NOT logged
        assert sensitive_account not in combined_logs

        # Verify operational message logged
        assert "Orchestrating timeline reconstruction for investigation target" in combined_logs

    finally:
        logger.remove(handler_id)


# ============================================================================
# 6. Prometheus Metrics Invariant Tests
# ============================================================================


def test_prometheus_metrics_names_and_labels_unchanged() -> None:
    """
    Verify all 5 required Prometheus metric names and label definitions remain strictly unchanged.
    """
    from prometheus_client import generate_latest, REGISTRY

    # 1. http_requests_total
    assert http_requests_total._name == "http_requests"
    assert set(http_requests_total._labelnames) == {"method", "path", "status_code"}

    # 2. http_request_duration_seconds
    assert http_request_duration_seconds._name == "http_request_duration_seconds"
    assert set(http_request_duration_seconds._labelnames) == {"method", "path"}

    # 3. llm_requests_total
    assert llm_requests_total._name == "llm_requests"
    assert set(llm_requests_total._labelnames) == {"provider", "model", "status"}

    # 4. llm_request_duration_seconds
    assert llm_request_duration_seconds._name == "llm_request_duration_seconds"
    assert set(llm_request_duration_seconds._labelnames) == {"provider", "model"}

    # 5. llm_tokens_total
    assert llm_tokens_total._name == "llm_tokens"
    assert set(llm_tokens_total._labelnames) == {"provider", "model", "type"}

    # Verify standard Prometheus exposition output format
    exposition = generate_latest(REGISTRY).decode("utf-8")
    assert "http_requests_total" in exposition
    assert "http_request_duration_seconds" in exposition
    assert "llm_requests_total" in exposition
    assert "llm_request_duration_seconds" in exposition
    assert "llm_tokens_total" in exposition


# ============================================================================
# 7. Sprint 12.5B: Production Loguru Diagnostics Tests
# ============================================================================


def test_settings_default_debug_is_false() -> None:
    """
    Ensure Settings.DEBUG defaults to False in production.
    """
    settings_instance = _build_test_settings()
    assert settings_instance.DEBUG is False


def test_production_logger_diagnose_disabled_no_local_variable_leak(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Verify that in production mode (DEBUG=False):
    1. Loguru `diagnose` is disabled: local variable names and values are NOT logged in exception tracebacks.
    2. Loguru `backtrace` remains enabled: complete traceback structure and error messages are preserved.
    """
    prod_settings = _build_test_settings()
    prod_settings.DEBUG = False
    setup_logger(prod_settings)

    def _vulnerable_operation() -> None:
        local_db_password = "PROD_SECRET_PASSWORD_998877"
        bad_divisor = 0
        _ = len(local_db_password) / bad_divisor

    try:
        try:
            _vulnerable_operation()
        except ZeroDivisionError:
            logger.exception("Production error occurred during processing.")

        captured = capsys.readouterr()
        err_output = captured.err

        # 1. Verify traceback and error messages are preserved (backtrace=True)
        assert "_vulnerable_operation" in err_output
        assert "division by zero" in err_output
        assert "Production error occurred during processing." in err_output

        # 2. Verify local variable inspection is NOT emitted (diagnose=False)
        assert "PROD_SECRET_PASSWORD_998877" not in err_output

    finally:
        setup_logger()


def test_development_logger_diagnose_enabled_when_debug_true(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Verify that in development mode (DEBUG=True), Loguru diagnose is enabled for debugging convenience.
    """
    dev_settings = _build_test_settings()
    dev_settings.DEBUG = True
    setup_logger(dev_settings)

    def _dev_failing_operation() -> None:
        debug_dev_var = "DEV_LOCAL_VALUE_DEBUG_123"
        zero_div = 0
        _ = len(debug_dev_var) / zero_div

    try:
        try:
            _dev_failing_operation()
        except ZeroDivisionError:
            logger.exception("Dev error captured.")

        captured = capsys.readouterr()
        err_output = captured.err

        # In DEBUG=True mode, diagnose=True inspects local variable expressions
        assert "_dev_failing_operation" in err_output
        assert "division by zero" in err_output
        assert "DEV_LOCAL_VALUE_DEBUG_123" in err_output

    finally:
        setup_logger()


# ============================================================================
# 8. Sprint 12.5C: Observability Contract & Invariant Tests
# ============================================================================


def test_observability_label_cardinality_and_safety() -> None:
    """
    Verify all 5 Prometheus metric definitions satisfy:
    1. Strictly bounded label cardinality.
    2. Zero sensitive user data fields (PII, request IDs, entity values) in label names.
    3. Ascending, positive latency buckets.
    """
    forbidden_label_names = {
        "request_id",
        "req_id",
        "correlation_id",
        "report_id",
        "entity_value",
        "target_value",
        "phone",
        "email",
        "upi",
        "account",
        "name",
        "prompt",
        "response",
    }

    metrics = [
        http_requests_total,
        http_request_duration_seconds,
        llm_requests_total,
        llm_request_duration_seconds,
        llm_tokens_total,
    ]

    for m in metrics:
        labels = set(m._labelnames)
        # 1. No forbidden/sensitive label names
        assert not (labels & forbidden_label_names), f"Metric {m._name} contains sensitive labels: {labels}"
        # 2. Bounded label count (<= 3 labels per metric)
        assert len(labels) <= 3, f"Metric {m._name} has excessive label cardinality: {labels}"

    # 3. Verify histogram buckets are strictly increasing and positive
    for hist in [http_request_duration_seconds, llm_request_duration_seconds]:
        buckets = hist._upper_bounds
        assert len(buckets) > 0
        for b in buckets[:-1]:  # Exclude +Inf
            assert b > 0
        assert list(buckets) == sorted(buckets)


def test_http_route_normalization_bounds_cardinality_and_redacts_identifiers() -> None:
    """
    Verify that dynamic endpoints with arbitrary paths/UUIDs:
    1. Normalize route paths to static parameter templates (e.g. `/{incident_id}`).
    2. Return 'unmatched' for arbitrary non-existent paths.
    3. Never register raw IDs, phone numbers, or emails as Prometheus labels.
    """
    from fastapi.testclient import TestClient
    from prometheus_client import REGISTRY
    from app.main import app

    test_client = TestClient(app)

    sensitive_dynamic_phone_path = "/api/v1/nonexistent-endpoint/+919876543210"
    res = test_client.get(sensitive_dynamic_phone_path)
    assert res.status_code == 404

    # 1. Verify metric recorded with 'unmatched' path
    val_unmatched = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": "unmatched", "status_code": "404"},
    )
    assert val_unmatched is not None and val_unmatched > 0

    # 2. Verify raw sensitive path was NEVER created as a label
    val_raw = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "path": sensitive_dynamic_phone_path, "status_code": "404"},
    )
    assert val_raw is None


@pytest.mark.asyncio
async def test_llm_metrics_accuracy_on_retries_and_usage_metadata() -> None:
    """
    Verify that LLM telemetry tracks:
    1. Exact attempt count on retry (1 error attempt + 1 success attempt).
    2. Exact duration observations without backoff sleep inflation.
    3. Exact prompt and completion token counts from Gemini SDK usage metadata.
    """
    from unittest.mock import patch
    from google.genai.errors import ServerError
    from app.ai.client import GeminiClient
    from app.schemas.prompt import PromptConstraints, PromptMetadata, PromptRequest

    settings = _build_test_settings()
    client = GeminiClient(settings)

    mock_usage = MagicMock(
        prompt_token_count=150,
        candidates_token_count=75,
        total_token_count=225,
    )
    mock_success_response = MagicMock(
        text='{"summary": "Test report", "risk_level": "LOW", "confidence": 0.9, "findings": [], "key_entities": [], "recommended_actions": []}',
        usage_metadata=mock_usage,
        candidates=[MagicMock(finish_reason="STOP")],
    )

    server_error = ServerError(503, {"error": {"message": "Service overloaded"}})
    client._client.models.generate_content = MagicMock(
        side_effect=[server_error, mock_success_response]
    )

    with (
        patch.object(llm_requests_total, "labels") as mock_req_labels,
        patch.object(llm_request_duration_seconds, "labels") as mock_dur_labels,
        patch.object(llm_tokens_total, "labels") as mock_tok_labels,
    ):
        mock_req_counter = MagicMock()
        mock_req_labels.return_value = mock_req_counter

        mock_dur_hist = MagicMock()
        mock_dur_labels.return_value = mock_dur_hist

        mock_tok_counter = MagicMock()
        mock_tok_labels.return_value = mock_tok_counter

        from app.schemas.prompt import (
            DeveloperInstructions,
            ExpectedReportSection,
            ExpectedReportStructure,
            PromptConstraints,
            PromptMetadata,
            PromptRequest,
            SerializedContext,
            SystemPrompt,
        )

        prompt_req = PromptRequest(
            metadata=PromptMetadata(prompt_hash="a" * 64, model_name="gemini-3.5-flash-lite"),
            system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
            developer_instructions=DeveloperInstructions(
                citation_instructions=("Cite 1",), style_guidelines=("Style 1",)
            ),
            context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
            expected_structure=ExpectedReportStructure(
                sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),)
            ),
            constraints=PromptConstraints(temperature=0.0, max_tokens=1024),
        )

        res = await client.generate(prompt_req)
        assert res.usage.prompt_tokens == 150
        assert res.usage.completion_tokens == 75
        assert res.usage.total_tokens == 225

        # 1. Total requests: 1 error + 1 success
        assert mock_req_counter.inc.call_count == 2
        assert mock_req_labels.call_args_list[0].kwargs["status"] == "error"
        assert mock_req_labels.call_args_list[1].kwargs["status"] == "success"

        # 2. Duration observed for both attempts
        assert mock_dur_hist.observe.call_count == 2

        # 3. Tokens recorded for prompt and completion
        assert mock_tok_counter.inc.call_count == 2
        mock_tok_counter.inc.assert_any_call(150)
        mock_tok_counter.inc.assert_any_call(75)


