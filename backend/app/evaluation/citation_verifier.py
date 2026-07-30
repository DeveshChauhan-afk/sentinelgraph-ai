"""
CitationVerifier Subsystem (Sprint 9.5 Phase 9.5.2).

Deterministically verifies that every citation in a ProfessionalInvestigationReport exists
inside the source InvestigationReportContext, generating immutable audit results.
"""

from __future__ import annotations

import re
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation_report_context import InvestigationReportContext
from app.schemas.report import ProfessionalInvestigationReport


class CitationVerificationResult(BaseModel):
    """
    Immutable result of citation verification evaluation.
    """

    model_config = ConfigDict(frozen=True)

    total_citations: int = Field(default=0, ge=0, description="Total citations extracted.")
    valid_citations: int = Field(default=0, ge=0, description="Number of verified valid citations.")
    invalid_citations: tuple[str, ...] = Field(default_factory=tuple, description="Unmatched invalid citation strings.")
    citation_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of valid citations.")
    is_valid: bool = Field(default=True, description="True if zero invalid citations are found.")


class CitationVerifier:
    """
    Deterministic citation verification engine.
    """

    def verify(
        self,
        report: ProfessionalInvestigationReport,
        context: InvestigationReportContext,
    ) -> CitationVerificationResult:
        """
        Verify that all citations in report findings and recommendations exist in context.

        Args:
            report: ProfessionalInvestigationReport instance.
            context: Source InvestigationReportContext instance.

        Returns:
            Immutable CitationVerificationResult.
        """
        # 1. Collect valid context IDs and citation keys
        valid_keys = set()

        # Add target entity value
        if context.overview.target_value:
            valid_keys.add(context.overview.target_value.lower())

        # Add citation map keys & values
        for item in context.citation_map:
            valid_keys.add(item.finding_id.lower())
            for ev in item.evidence_ids:
                valid_keys.add(ev.lower())
            for c_id in item.complaint_ids:
                valid_keys.add(c_id.lower())
            for e_id in item.entity_ids:
                valid_keys.add(e_id.lower())

        # Add critical finding IDs
        for f in context.critical_findings:
            valid_keys.add(f.finding_id.lower())
            for c_id in f.supporting_complaint_ids:
                valid_keys.add(c_id.lower())
            for e_id in f.supporting_evidence_ids:
                valid_keys.add(e_id.lower())
            for ent_id in f.supporting_entity_ids:
                valid_keys.add(ent_id.lower())

        # Add supporting evidence IDs & complaint IDs
        for e in context.supporting_evidence:
            valid_keys.add(e.evidence_id.lower())
            for c_id in e.supporting_complaints:
                valid_keys.add(c_id.lower())
            for ent in e.supporting_entities:
                valid_keys.add(ent.lower())

        # Add entity highlights
        for h in context.entity_highlights.highlights:
            valid_keys.add(h.entity_value.lower())

        # 2. Extract citations from report findings & recommendations
        extracted_citations = []

        for finding in report.key_findings:
            for c in finding.citations:
                extracted_citations.append(c)

        for rec in report.recommendations:
            for target in rec.target_entities:
                extracted_citations.append(target)

        if not extracted_citations:
            return CitationVerificationResult(
                total_citations=0,
                valid_citations=0,
                invalid_citations=(),
                citation_coverage_score=1.0,
                is_valid=True,
            )

        valid_count = 0
        invalid_list = []

        for cite_str in extracted_citations:
            # Parse inner citation content if formatted like [Complaint: C-101] or [Evidence: EVD-001]
            match = re.search(r"\[(?:Complaint|Evidence|Entity|Finding):\s*([^\]]+)\]", cite_str, re.IGNORECASE)
            extracted_val = match.group(1).strip() if match else cite_str.strip()

            if extracted_val.lower() in valid_keys:
                valid_count += 1
            else:
                # Substring check fallback
                found_match = any(extracted_val.lower() in vk for vk in valid_keys)
                if found_match:
                    valid_count += 1
                else:
                    invalid_list.append(cite_str)

        total = len(extracted_citations)
        score = round(valid_count / total, 2) if total > 0 else 1.0

        return CitationVerificationResult(
            total_citations=total,
            valid_citations=valid_count,
            invalid_citations=tuple(invalid_list),
            citation_coverage_score=score,
            is_valid=(len(invalid_list) == 0),
        )
