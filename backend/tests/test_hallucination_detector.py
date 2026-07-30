"""
Unit tests for HallucinationDetector (Sprint 9.5 Phase 9.5.4).
"""

from __future__ import annotations

import pytest

from app.evaluation.golden_dataset import get_golden_scenarios
from app.evaluation.hallucination_detector import HallucinationCheckResult, HallucinationDetector
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
    """
    Fixture creating valid report and context.
    """
    golden = get_golden_scenarios()["SIMPLE_FRAUD_CASE"]
    summary = golden.summary
    context = ReportContextBuilder().build_report_context(summary)

    report = ProfessionalInvestigationReport(
        report_id="RPT-TEST-002",
        target_value=context.overview.target_value,
        executive_summary=ExecutiveSummarySection(
            summary_text="Summary", overall_risk_level="HIGH", key_takeaways=("T1",)
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
            correlation_id="CORR-2",
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            latency_ms=100.0,
            prompt_hash="b" * 64,
        ),
    )
    return report, context


def test_hallucination_detector_clean(sample_report_and_context):
    """
    Test HallucinationDetector on a clean grounded report.
    """
    report, context = sample_report_and_context
    detector = HallucinationDetector()
    result = detector.detect(report=report, context=context)

    assert isinstance(result, HallucinationCheckResult)
    assert result.is_clean is True
    assert result.status == "NO_HALLUCINATION"


def test_hallucination_detector_unsupported_entity(sample_report_and_context):
    """
    Test HallucinationDetector detecting hallucinated entity target.
    """
    report, context = sample_report_and_context

    hacked_rec = RecommendationSection(
        recommendation_id="REC-001",
        action="Freeze Unknown Account",
        priority="HIGH",
        rationale="Unknown",
        trigger="ENTITY_REUSE",
        target_entities=("fake_scammer_account_999",),
    )
    hacked_report = report.model_copy(update={"recommendations": (hacked_rec,)})

    detector = HallucinationDetector()
    result = detector.detect(report=hacked_report, context=context)

    assert result.is_clean is False
    assert "fake_scammer_account_999" in result.unsupported_entities
