"""
Unit tests for CitationVerifier (Sprint 9.5 Phase 9.5.2).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.evaluation.citation_verifier import CitationVerificationResult, CitationVerifier
from app.evaluation.golden_dataset import get_golden_scenarios
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
    Fixture building valid ProfessionalInvestigationReport and InvestigationReportContext.
    """
    golden = get_golden_scenarios()["SIMPLE_FRAUD_CASE"]
    summary = golden.summary
    context = ReportContextBuilder().build_report_context(summary)

    report = ProfessionalInvestigationReport(
        report_id="RPT-TEST-001",
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
            correlation_id="CORR-1",
            provider="Gemini",
            model="gemini-3.5-flash-lite",
            latency_ms=100.0,
            prompt_hash="a" * 64,
        ),
    )
    return report, context


def test_citation_verifier_valid(sample_report_and_context):
    """
    Test CitationVerifier verifying valid citations in report.
    """
    report, context = sample_report_and_context
    verifier = CitationVerifier()
    result = verifier.verify(report=report, context=context)

    assert isinstance(result, CitationVerificationResult)
    assert result.is_valid is True
    assert result.citation_coverage_score == 1.0
    assert len(result.invalid_citations) == 0


def test_citation_verifier_invalid_citation(sample_report_and_context):
    """
    Test CitationVerifier detecting invalid fabricated citations.
    """
    report, context = sample_report_and_context

    # Inject fabricated citation
    hacked_finding = FindingSection(
        finding_id="FINDING-EVD-001",
        title="Phone Number Reuse",
        description="Reused phone",
        severity="HIGH",
        confidence=0.85,
        citations=("[Complaint: C-999999]",),  # Fabricated ID
    )
    invalid_report = report.model_copy(update={"key_findings": (hacked_finding,)})

    verifier = CitationVerifier()
    result = verifier.verify(report=invalid_report, context=context)

    assert result.is_valid is False
    assert result.citation_coverage_score < 1.0
    assert "[Complaint: C-999999]" in result.invalid_citations
