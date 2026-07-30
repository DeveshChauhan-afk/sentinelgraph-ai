"""
Report Quality Evaluator (Sprint 9.5 Phase 9.5.3).

Provides deterministic non-AI evaluation of report quality, citation coverage,
finding alignment, and data limitation completeness.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation_report_context import InvestigationReportContext
from app.schemas.report import ProfessionalInvestigationReport


class ReportQualityAssessment(BaseModel):
    """
    Immutable deterministic quality assessment score.
    """

    model_config = ConfigDict(frozen=True)

    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Citation coverage ratio.")
    evidence_utilization: float = Field(default=0.0, ge=0.0, le=1.0, description="Evidence utilization ratio.")
    finding_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Finding coverage ratio.")
    recommendation_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Recommendation coverage ratio.")
    timeline_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="Timeline milestone coverage ratio.")
    data_quality_mentioned: bool = Field(default=True, description="Whether data quality is explicitly assessed.")
    limitation_mentioned: bool = Field(default=True, description="Whether limitations section is non-empty.")
    overall_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Weighted overall quality score.")


class ReportQualityEvaluator:
    """
    Deterministic quality evaluation engine for investigation reports.
    """

    def evaluate(
        self,
        report: ProfessionalInvestigationReport,
        context: InvestigationReportContext,
    ) -> ReportQualityAssessment:
        """
        Compute deterministic quality metrics comparing report to source context.

        Args:
            report: ProfessionalInvestigationReport instance.
            context: Source InvestigationReportContext instance.

        Returns:
            Immutable ReportQualityAssessment.
        """
        # 1. Finding Coverage
        context_findings = len(context.critical_findings)
        report_findings = len(report.key_findings)
        finding_cov = min(1.0, report_findings / max(1, context_findings))

        # 2. Recommendation Coverage
        context_recs = len(context.recommendations)
        report_recs = len(report.recommendations)
        rec_cov = min(1.0, report_recs / max(1, context_recs))

        # 3. Timeline Coverage
        context_milestones = len(context.timeline_highlights.highlights)
        report_milestones = len(report.timeline_summary.milestones)
        time_cov = min(1.0, report_milestones / max(1, context_milestones))

        # 4. Evidence Utilization
        context_evidence = len(context.supporting_evidence)
        evid_util = min(1.0, report.evidence_assessment.supporting_evidence_count / max(1, context_evidence))

        # 5. Citation Coverage (findings with citations)
        findings_with_cites = sum(1 for f in report.key_findings if len(f.citations) > 0)
        cite_cov = findings_with_cites / max(1, report_findings)

        # 6. Data Quality & Limitations
        data_quality_mentioned = bool(report.limitations.data_quality_assessment)
        limitation_mentioned = len(report.limitations.limitations) > 0 or data_quality_mentioned

        # Weighted overall score
        overall = (
            (finding_cov * 0.25)
            + (rec_cov * 0.20)
            + (time_cov * 0.15)
            + (evid_util * 0.15)
            + (cite_cov * 0.15)
            + (0.10 if limitation_mentioned else 0.0)
        )
        overall_score = round(min(1.0, overall), 2)

        return ReportQualityAssessment(
            citation_coverage=round(cite_cov, 2),
            evidence_utilization=round(evid_util, 2),
            finding_coverage=round(finding_cov, 2),
            recommendation_coverage=round(rec_cov, 2),
            timeline_coverage=round(time_cov, 2),
            data_quality_mentioned=data_quality_mentioned,
            limitation_mentioned=limitation_mentioned,
            overall_quality_score=overall_score,
        )
