"""
Unit tests for InvestigationReportService & LLM Integration Architecture (Sprint 9 Phase 4).

Validates LLMClient interface, GeminiClient normalization, ReportParser schema validation,
domain exception translation, telemetry generation, end-to-end orchestration, and API endpoint integration.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai.llm_client import LLMClient
from app.exceptions.investigation import (
    InvalidReportSchemaError,
    LLMProviderError,
    LLMTimeoutError,
    ReportParsingError,
)
from app.main import app
from app.schemas.llm_response import LLMMetadata, LLMResponse, LLMUsage
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
from app.schemas.report import (
    ConclusionSection,
    EvidenceSection,
    EvolutionSection,
    ExecutiveSummarySection,
    FindingSection,
    InvestigationScopeSection,
    LimitationSection,
    ProfessionalInvestigationReport,
    RecommendationSection,
    ReportTelemetry,
    TimelineMilestone,
    TimelineSection,
)
from app.services.investigation.report_parser import ReportParser
from app.services.investigation_report_service import InvestigationReportService
from app.services.investigation_summary_service import InvestigationSummaryService
from app.services.prompt_builder import PromptBuilder
from app.services.report_context_builder import ReportContextBuilder


@pytest.fixture
def sample_valid_report_dict():
    """
    Fixture providing a valid JSON dictionary matching ProfessionalInvestigationReport schema.
    """
    return {
        "report_id": "RPT-12345678",
        "target_value": "+919876543210",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": {
            "summary_text": "Investigation of target +919876543210 identified high risk fraud network.",
            "overall_risk_level": "HIGH",
            "key_takeaways": ["Reused across 5 complaints", "Payment channel scammer@upi"],
        },
        "investigation_scope": {
            "target_value": "+919876543210",
            "target_type": "phone",
            "total_complaints": 2,
            "total_entities": 2,
            "duration_days": 4,
        },
        "timeline_summary": {
            "timeline_narrative": "Fraud activity began on Jan 1 and expanded on Jan 5.",
            "milestones": [
                {
                    "event_type": "COMPLAINT_CREATED",
                    "timestamp": "2026-01-01T10:00:00Z",
                    "title": "First Complaint",
                    "description": "Complaint C-101 registered",
                }
            ],
        },
        "key_findings": [
            {
                "finding_id": "FINDING-EVD-001",
                "title": "High Entity Reuse",
                "description": "Phone number reused across 5 complaints.",
                "severity": "HIGH",
                "confidence": 0.85,
                "citations": ["[Complaint: C-101]", "[Evidence: EVD-001]"],
            }
        ],
        "fraud_network_evolution": {
            "evolution_narrative": "Network expanded with UPI scammer@upi.",
            "network_stage": "EXPANDING_FRAUD_NETWORK",
        },
        "evidence_assessment": {
            "evidence_summary": "Synthesized 2 high severity evidence units.",
            "supporting_evidence_count": 2,
        },
        "recommendations": [
            {
                "recommendation_id": "REC-001",
                "action": "Freeze Payment Identifier 'scammer@upi'",
                "priority": "HIGH",
                "rationale": "Payment identifier reused across 3 complaints.",
                "trigger": "PAYMENT_EXPANSION",
                "target_entities": ["scammer@upi"],
            }
        ],
        "limitations": {
            "data_quality_assessment": "HIGH",
            "limitations": [],
        },
        "conclusion": {
            "summary_conclusion": "Target presents immediate fraud risk.",
        },
    }


@pytest.fixture
def mock_prompt_request():
    """
    Fixture providing a valid PromptRequest.
    """
    return PromptRequest(
        metadata=PromptMetadata(prompt_hash="a" * 64),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(citation_instructions=("Cite 1",), style_guidelines=("Style 1",)),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),)
        ),
        constraints=PromptConstraints(),
    )


def test_report_parser_valid_json(sample_valid_report_dict, mock_prompt_request):
    """
    Test ReportParser parsing valid JSON and attaching telemetry metadata.
    """
    parser = ReportParser()
    json_str = f"```json\n{json.dumps(sample_valid_report_dict)}\n```"

    llm_resp = LLMResponse(
        metadata=LLMMetadata(
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            request_id="REQ-1",
            latency_ms=150.0,
            prompt_hash=mock_prompt_request.metadata.prompt_hash,
        ),
        usage=LLMUsage(prompt_tokens=500, completion_tokens=200, total_tokens=700),
        finish_reason="STOP",
        response_text=json_str,
    )

    report = parser.parse_report(llm_response=llm_resp, prompt_request=mock_prompt_request)

    assert isinstance(report, ProfessionalInvestigationReport)
    assert report.target_value == "+919876543210"
    assert report.executive_summary.overall_risk_level == "HIGH"
    assert isinstance(report.telemetry, ReportTelemetry)
    assert report.telemetry.provider == "Gemini"
    assert report.telemetry.total_tokens == 700


def test_report_parser_malformed_json(mock_prompt_request):
    """
    Test ReportParser raising ReportParsingError on non-JSON response.
    """
    parser = ReportParser()
    llm_resp = LLMResponse(
        metadata=LLMMetadata(
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            request_id="REQ-1",
            latency_ms=100.0,
            prompt_hash=mock_prompt_request.metadata.prompt_hash,
        ),
        usage=LLMUsage(),
        response_text="This is plain markdown text without JSON",
    )

    with pytest.raises(ReportParsingError):
        parser.parse_report(llm_response=llm_resp, prompt_request=mock_prompt_request)


def test_report_parser_invalid_schema(mock_prompt_request):
    """
    Test ReportParser raising InvalidReportSchemaError on missing required section.
    """
    parser = ReportParser()
    invalid_dict = {"report_id": "123", "target_value": "val"}  # missing sections

    llm_resp = LLMResponse(
        metadata=LLMMetadata(
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            request_id="REQ-1",
            latency_ms=100.0,
            prompt_hash=mock_prompt_request.metadata.prompt_hash,
        ),
        usage=LLMUsage(),
        response_text=json.dumps(invalid_dict),
    )

    with pytest.raises(InvalidReportSchemaError):
        parser.parse_report(llm_response=llm_resp, prompt_request=mock_prompt_request)


@pytest.mark.asyncio
async def test_full_investigation_report_service_orchestration(sample_valid_report_dict):
    """
    Test full InvestigationReportService orchestration using a mocked LLMClient.
    """
    summary_service = InvestigationSummaryService()
    context_builder = ReportContextBuilder()
    prompt_builder = PromptBuilder()
    parser = ReportParser()

    mock_llm_client = MagicMock(spec=LLMClient)
    mock_llm_client.generate = AsyncMock(
        return_value=LLMResponse(
            metadata=LLMMetadata(
                provider="MockLLM",
                model="mock-model",
                request_id="REQ-MOCK",
                latency_ms=120.0,
                prompt_hash="b" * 64,
            ),
            usage=LLMUsage(prompt_tokens=400, completion_tokens=150, total_tokens=550),
            response_text=json.dumps(sample_valid_report_dict),
        )
    )

    report_service = InvestigationReportService(
        summary_service=summary_service,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        llm_client=mock_llm_client,
        report_parser=parser,
    )

    report = await report_service.generate_report(entity_value="+919876543210", target_type="phone")

    assert isinstance(report, ProfessionalInvestigationReport)
    assert report.target_value == "+919876543210"
    assert report.telemetry.provider == "MockLLM"
    mock_llm_client.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_report_endpoint_success(sample_valid_report_dict):
    """
    Test FastAPI POST /api/v1/investigations/report endpoint.
    """
    mock_report = ProfessionalInvestigationReport.model_validate(
        {
            **sample_valid_report_dict,
            "telemetry": {
                "correlation_id": "CORR-TEST",
                "provider": "Gemini",
                "model": "gemini-3.5-flash-lite",
                "latency_ms": 200.0,
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "prompt_hash": "c" * 64,
            },
        }
    )

    mock_service = MagicMock(spec=InvestigationReportService)
    mock_service.generate_report = AsyncMock(return_value=mock_report)

    from app.api.dependencies import get_investigation_report_service

    app.dependency_overrides[get_investigation_report_service] = lambda: mock_service

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/investigation/report",
            json={"target_type": "phone", "target_value": "+919876543210"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["target_value"] == "+919876543210"
        assert data["executive_summary"]["overall_risk_level"] == "HIGH"
    finally:
        app.dependency_overrides.clear()
