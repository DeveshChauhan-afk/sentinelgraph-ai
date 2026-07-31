"""
Unit tests for PerformanceBenchmarker & AIEvaluationReport (Sprint 9.5 Phase 9.5.9 & 9.5.10).
"""

from __future__ import annotations

import json
import pytest

from app.evaluation.benchmarking import PerformanceBenchmarkReport, PerformanceBenchmarker
from app.evaluation.golden_dataset import get_golden_scenarios
from app.evaluation.report_generator import AIEvaluationReport, AIEvaluationReportGenerator
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
    ProfessionalInvestigationReport,
)
from app.services.report_context_builder import ReportContextBuilder


@pytest.fixture
def sample_eval_fixtures():
    golden = get_golden_scenarios()["SIMPLE_FRAUD_CASE"]
    summary = golden.summary
    context = ReportContextBuilder().build_report_context(summary)

    report_dict = {
        "report_id": "RPT-EVAL-001",
        "target_value": context.overview.target_value,
        "executive_summary": {"summary_text": "Text", "overall_risk_level": "HIGH"},
        "investigation_scope": {"target_value": context.overview.target_value},
        "timeline_summary": {"timeline_narrative": "Text"},
        "key_findings": [
            {
                "finding_id": "FINDING-EVD-001",
                "title": "Title",
                "description": "Desc",
                "severity": "HIGH",
                "confidence": 0.85,
                "citations": ["[Complaint: C-101]", "[Evidence: EVD-001]"],
            }
        ],
        "fraud_network_evolution": {"evolution_narrative": "Text", "network_stage": "STAGE"},
        "evidence_assessment": {"evidence_summary": "Text", "supporting_evidence_count": 1},
        "recommendations": [
            {
                "recommendation_id": "REC-001",
                "action": "Block",
                "priority": "HIGH",
                "rationale": "Reason",
                "trigger": "TRIGGER",
                "target_entities": ["+919876543210"],
            }
        ],
        "limitations": {"data_quality_assessment": "HIGH", "limitations": ["L1"]},
        "conclusion": {"summary_conclusion": "Text"},
    }

    report = ProfessionalInvestigationReport.model_validate(
        {
            **report_dict,
            "telemetry": {
                "correlation_id": "CORR-EVAL",
                "provider": "Gemini",
                "model": "gemini",
                "latency_ms": 100.0,
                "prompt_hash": "e" * 64,
            },
        }
    )

    prompt_request = PromptRequest(
        metadata=PromptMetadata(prompt_hash="e" * 64),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(citation_instructions=("Cite 1",), style_guidelines=("Style 1",)),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),)
        ),
        constraints=PromptConstraints(),
    )

    return summary, context, report, prompt_request, json.dumps(report_dict)


def test_performance_benchmarker(sample_eval_fixtures):
    summary, context, report, prompt_req, raw_json = sample_eval_fixtures
    benchmarker = PerformanceBenchmarker()
    result = benchmarker.benchmark_pipeline(summary=summary, sample_llm_text=raw_json)

    assert isinstance(result, PerformanceBenchmarkReport)
    assert result.total_report_ms > 0
    assert result.llm_latency_ms == 150.0


def test_ai_evaluation_report_generator(sample_eval_fixtures):
    summary, context, report, prompt_req, raw_json = sample_eval_fixtures
    generator = AIEvaluationReportGenerator()
    eval_report = generator.evaluate_report(
        report=report,
        context=context,
        prompt_request=prompt_req,
        summary=summary,
        sample_llm_text=raw_json,
    )

    assert isinstance(eval_report, AIEvaluationReport)
    assert eval_report.overall_status == "PASS"
    assert eval_report.quality_score > 0.50
    assert eval_report.citation_verification.is_valid is True
    assert eval_report.hallucination_check.is_clean is True
