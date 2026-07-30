"""
Unit tests for ReportQualityEvaluator (Sprint 9.5 Phase 9.5.3).
"""

from __future__ import annotations

import pytest

from app.evaluation.golden_dataset import get_golden_scenarios
from app.evaluation.quality_evaluator import ReportQualityAssessment, ReportQualityEvaluator
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
    TimelineSection,
)
from app.services.report_context_builder import ReportContextBuilder


@pytest.fixture
def sample_report_and_context():
    golden = get_golden_scenarios()["SIMPLE_FRAUD_CASE"]
    summary = golden.summary
    context = ReportContextBuilder().build_report_context(summary)

    report = ProfessionalInvestigationReport(
        report_id="RPT-TEST-003",
        target_value=context.overview.target_value,
        executive_summary=ExecutiveSummarySection(
            summary_text="Summary text", overall_risk_level="HIGH", key_takeaways=("T1",)
        ),
        investigation_scope=InvestigationScopeSection(
            target_value=context.overview.target_value,
            target_type="phone",
            total_complaints=2,
            total_entities=3,
            duration_days=4,
        ),
        timeline_summary=TimelineSection(timeline_narrative="Timeline text", milestones=()),
        key_findings=(
            FindingSection(
                finding_id="FINDING-EVD-001",
                title="Phone Number Reuse",
                description="Reused phone",
                severity="HIGH",
                confidence=0.85,
                citations=("[Complaint: C-101]", "[Evidence: EVD-001]"),
            ),
        ),
        fraud_network_evolution=EvolutionSection(
            evolution_narrative="Evo text", network_stage="EXPANDING"
        ),
        evidence_assessment=EvidenceSection(
            evidence_summary="Evid summary", supporting_evidence_count=1
        ),
        recommendations=(
            RecommendationSection(
                recommendation_id="REC-001",
                action="Block Phone",
                priority="HIGH",
                rationale="Reuse",
                trigger="ENTITY_REUSE",
                target_entities=("+919876543210",),
            ),
        ),
        limitations=LimitationSection(
            data_quality_assessment="HIGH", limitations=("Limitation 1",)
        ),
        conclusion=ConclusionSection(summary_conclusion="Conclusion text"),
        telemetry=ReportTelemetry(
            correlation_id="CORR-3",
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            latency_ms=100.0,
            prompt_hash="c" * 64,
        ),
    )
    return report, context


def test_quality_evaluator_scores(sample_report_and_context):
    report, context = sample_report_and_context
    evaluator = ReportQualityEvaluator()
    assessment = evaluator.evaluate(report=report, context=context)

    assert isinstance(assessment, ReportQualityAssessment)
    assert assessment.overall_quality_score > 0.50
    assert assessment.citation_coverage == 1.0
    assert assessment.data_quality_mentioned is True
