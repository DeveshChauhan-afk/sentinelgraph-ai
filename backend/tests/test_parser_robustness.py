"""
Parser Robustness & Stress Tests (Sprint 9.5 Phase 9.5.6).
"""

from __future__ import annotations

import json
import pytest

from app.exceptions.investigation import InvalidReportSchemaError, ReportParsingError
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
from app.services.investigation.report_parser import ReportParser


@pytest.fixture
def mock_prompt_request():
    return PromptRequest(
        metadata=PromptMetadata(prompt_hash="d" * 64),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(citation_instructions=("Cite 1",), style_guidelines=("Style 1",)),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),)
        ),
        constraints=PromptConstraints(),
    )


def test_parser_handles_extra_whitespace_and_fences(mock_prompt_request):
    parser = ReportParser()
    valid_dict = {
        "report_id": "RPT-99",
        "target_value": "+919876543210",
        "executive_summary": {"summary_text": "Text", "overall_risk_level": "HIGH"},
        "investigation_scope": {"target_value": "+919876543210"},
        "timeline_summary": {"timeline_narrative": "Text"},
        "key_findings": [],
        "fraud_network_evolution": {"evolution_narrative": "Text", "network_stage": "STAGE"},
        "evidence_assessment": {"evidence_summary": "Text"},
        "recommendations": [],
        "limitations": {"data_quality_assessment": "HIGH"},
        "conclusion": {"summary_conclusion": "Text"},
    }

    raw = f"  \n\n```json\n{json.dumps(valid_dict)}\n``` \n\n"
    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini", request_id="R1", latency_ms=10.0, prompt_hash="d"*64),
        usage=LLMUsage(),
        response_text=raw,
    )

    report = parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)
    assert report.target_value == "+919876543210"


def test_parser_fails_on_corrupt_json(mock_prompt_request):
    parser = ReportParser()
    resp = LLMResponse(
        metadata=LLMMetadata(provider="Gemini", model="gemini", request_id="R1", latency_ms=10.0, prompt_hash="d"*64),
        usage=LLMUsage(),
        response_text="{ corrupt json string without closing quote ",
    )

    with pytest.raises(ReportParsingError):
        parser.parse_report(llm_response=resp, prompt_request=mock_prompt_request)
