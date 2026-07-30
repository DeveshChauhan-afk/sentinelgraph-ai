"""
Integration tests for Report Output Contract & Parser Validation (Sprint 9 Phase 4.1 Hotfix).

Simulates realistic LLM completion payloads and verifies strict schema validation,
field name compliance, markdown stripping, and failure on malformed structures.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from app.exceptions.investigation import InvalidReportSchemaError, ReportParsingError
from app.schemas.llm_response import LLMMetadata, LLMResponse, LLMUsage
from app.schemas.prompt import (
    DeveloperInstructions,
    ExpectedReportSchema,
    ExpectedReportSection,
    ExpectedReportStructure,
    PromptConstraints,
    PromptMetadata,
    PromptRequest,
    SerializedContext,
    SystemPrompt,
)
from app.schemas.report import ProfessionalInvestigationReport
from app.services.investigation.report_parser import ReportParser


@pytest.fixture
def mock_prompt_request():
    """
    Fixture providing a valid PromptRequest.
    """
    expected_schema = ExpectedReportSchema(
        json_skeleton='{"report_id": "string"}',
        required_field_names=("report_id", "target_value"),
    )
    return PromptRequest(
        metadata=PromptMetadata(prompt_hash="f" * 64),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(
            citation_instructions=("Cite 1",),
            style_guidelines=("Style 1",),
            output_formatting_rules=("Return raw JSON",),
        ),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),),
            expected_schema=expected_schema,
        ),
        constraints=PromptConstraints(),
    )


@pytest.fixture
def canonical_valid_report_dict():
    """
    Fixture returning a dictionary matching ProfessionalInvestigationReport schema.
    """
    return {
        "report_id": "RPT-HOTFIX-001",
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
            "limitations": ["Data is complete."],
        },
        "conclusion": {
            "summary_conclusion": "Target presents immediate fraud risk.",
        },
    }


def test_correct_schema_validates_cleanly(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that LLM response matching canonical schema validates into ProfessionalInvestigationReport.
    """
    parser = ReportParser()
    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R1", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        response_text=json.dumps(canonical_valid_report_dict),
    )

    report = parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)
    assert isinstance(report, ProfessionalInvestigationReport)
    assert report.report_id == "RPT-HOTFIX-001"
    assert report.executive_summary.summary_text.startswith("Investigation of target")


def test_markdown_wrapped_json_handled(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that ReportParser handles JSON wrapped in markdown code blocks.
    """
    parser = ReportParser()
    wrapped_text = f"```json\n{json.dumps(canonical_valid_report_dict)}\n```"
    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R2", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(),
        response_text=wrapped_text,
    )

    report = parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)
    assert report.target_value == "+919876543210"


def test_missing_required_field_rejected(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that missing top-level required fields cause InvalidReportSchemaError.
    """
    parser = ReportParser()
    corrupt_dict = canonical_valid_report_dict.copy()
    del corrupt_dict["executive_summary"]  # Missing required section

    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R3", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(),
        response_text=json.dumps(corrupt_dict),
    )

    with pytest.raises(InvalidReportSchemaError):
        parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)


def test_wrong_field_name_rejected(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that LLM inventing field names (e.g. 'overview' instead of 'summary_text') is rejected.
    """
    parser = ReportParser()
    corrupt_dict = canonical_valid_report_dict.copy()
    corrupt_dict["executive_summary"] = {
        "overview": "Overview text instead of summary_text",  # Invalid key name
        "overall_risk_level": "HIGH",
    }

    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R4", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(),
        response_text=json.dumps(corrupt_dict),
    )

    with pytest.raises(InvalidReportSchemaError):
        parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)


def test_list_instead_of_object_rejected(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that evidence_assessment returned as a list instead of object is rejected.
    """
    parser = ReportParser()
    corrupt_dict = canonical_valid_report_dict.copy()
    corrupt_dict["evidence_assessment"] = ["evidence 1", "evidence 2"]  # List instead of object

    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R5", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(),
        response_text=json.dumps(corrupt_dict),
    )

    with pytest.raises(InvalidReportSchemaError):
        parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)


def test_missing_nested_object_rejected(canonical_valid_report_dict, mock_prompt_request):
    """
    Test that missing nested object (e.g. missing timeline_summary object) is rejected.
    """
    parser = ReportParser()
    corrupt_dict = canonical_valid_report_dict.copy()
    corrupt_dict["timeline_summary"] = None  # None instead of dict

    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini-3.5-flash-lite", request_id="R6", latency_ms=10.0, prompt_hash="f" * 64),
        usage=LLMUsage(),
        response_text=json.dumps(corrupt_dict),
    )

    with pytest.raises(InvalidReportSchemaError):
        parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)
