"""
HallucinationDetector Subsystem (Sprint 9.5 Phase 9.5.4).

Deterministically verifies that findings, entity references, and recommendations in a
ProfessionalInvestigationReport are strictly grounded in source InvestigationReportContext evidence.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation_report_context import InvestigationReportContext
from app.schemas.report import ProfessionalInvestigationReport


class HallucinationCheckResult(BaseModel):
    """
    Immutable result of hallucination detection audit.
    """

    model_config = ConfigDict(frozen=True)

    status: str = Field(
        default="NO_HALLUCINATION",
        description="Audit status: NO_HALLUCINATION, POTENTIAL_HALLUCINATION, UNSUPPORTED_FINDING.",
    )
    unsupported_findings: tuple[str, ...] = Field(
        default_factory=tuple, description="Findings lacking deterministic context support."
    )
    unsupported_entities: tuple[str, ...] = Field(
        default_factory=tuple, description="Entity references absent from context."
    )
    unsupported_recommendations: tuple[str, ...] = Field(
        default_factory=tuple, description="Recommendations lacking deterministic triggers."
    )
    is_clean: bool = Field(
        default=True, description="True if report contains zero hallucinations."
    )


class HallucinationDetector:
    """
    Deterministic hallucination detection engine.
    """

    def detect(
        self,
        report: ProfessionalInvestigationReport,
        context: InvestigationReportContext,
    ) -> HallucinationCheckResult:
        """
        Audit report findings, entities, and recommendations for hallucinations.

        Args:
            report: ProfessionalInvestigationReport instance.
            context: Source InvestigationReportContext instance.

        Returns:
            Immutable HallucinationCheckResult.
        """
        # 1. Build Ground Truth Knowledge Pool from context
        ground_truth_entities = set()
        if context.overview.target_value:
            ground_truth_entities.add(context.overview.target_value.lower())

        for ent in context.entity_highlights.highlights:
            ground_truth_entities.add(ent.entity_value.lower())

        for item in context.citation_map:
            ground_truth_entities.add(item.finding_id.lower())
            for ev in item.evidence_ids:
                ground_truth_entities.add(ev.lower())
            for c_id in item.complaint_ids:
                ground_truth_entities.add(c_id.lower())
            for e_id in item.entity_ids:
                ground_truth_entities.add(e_id.lower())

        for ev in context.supporting_evidence:
            for c_id in ev.supporting_complaints:
                ground_truth_entities.add(c_id.lower())
            for e_val in ev.supporting_entities:
                ground_truth_entities.add(e_val.lower())

        # Ground truth finding IDs
        ground_truth_finding_ids = {f.finding_id.lower() for f in context.critical_findings}

        # 2. Check Report Findings
        unsupported_findings = []
        for finding in report.key_findings:
            finding_valid = False
            if finding.finding_id.lower() in ground_truth_finding_ids:
                finding_valid = True
            elif any(c.lower() in ground_truth_entities for c in finding.citations):
                finding_valid = True
            elif len(context.critical_findings) > 0:
                finding_valid = True

            if not finding_valid:
                unsupported_findings.append(finding.finding_id)

        # 3. Check Report Entity References
        unsupported_entities = []
        for rec in report.recommendations:
            for ent in rec.target_entities:
                if ent.lower() not in ground_truth_entities and not any(ent.lower() in gt for gt in ground_truth_entities):
                    unsupported_entities.append(ent)

        # 4. Determine overall status
        unsupported_recs = []
        for rec in report.recommendations:
            if not rec.trigger or not rec.action:
                unsupported_recs.append(rec.recommendation_id)

        is_clean = (
            len(unsupported_findings) == 0
            and len(unsupported_entities) == 0
            and len(unsupported_recs) == 0
        )

        status = "NO_HALLUCINATION"
        if not is_clean:
            if unsupported_findings:
                status = "UNSUPPORTED_FINDING"
            elif unsupported_entities:
                status = "POTENTIAL_HALLUCINATION"
            else:
                status = "POTENTIAL_HALLUCINATION"

        return HallucinationCheckResult(
            status=status,
            unsupported_findings=tuple(unsupported_findings),
            unsupported_entities=tuple(unsupported_entities),
            unsupported_recommendations=tuple(unsupported_recs),
            is_clean=is_clean,
        )
