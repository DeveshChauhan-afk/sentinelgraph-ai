"""
Golden Investigation Dataset (Sprint 9.5 Phase 9.5.1).

Provides fixed, reproducible investigation scenarios for regression testing, quality evaluation,
and hallucination benchmarking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation_summary import (
    FindingType,
    InvestigationDataQuality,
    InvestigationEntitySummary,
    InvestigationEvidenceSummary,
    InvestigationEvolutionSummary,
    InvestigationFinding,
    InvestigationMetadata,
    InvestigationOverview,
    InvestigationPresentation,
    InvestigationRecommendation,
    InvestigationStatistics,
    InvestigationSummary,
    InvestigationTimelineSummary,
)


class GoldenScenario(BaseModel):
    """
    Representation of a golden investigation scenario for evaluation.
    """

    model_config = ConfigDict(frozen=True)

    scenario_id: str = Field(..., description="Unique scenario identifier.")
    name: str = Field(..., description="Human-readable scenario name.")
    description: str = Field(..., description="Scenario description.")
    summary: InvestigationSummary = Field(..., description="Canonical InvestigationSummary for scenario.")
    expected_risk_level: str = Field(..., description="Expected overall risk level.")
    expected_finding_count: int = Field(..., description="Expected number of critical findings.")
    expected_citation_ids: tuple[str, ...] = Field(..., description="Expected valid citation IDs.")


def get_golden_scenarios() -> dict[str, GoldenScenario]:
    """
    Construct and return all fixed golden investigation scenarios.
    """
    summary_service = InvestigationSummaryService_MockFactory()

    # 1. Simple Fraud Case
    summary_simple = summary_service.build_scenario(
        target_value="+919876543210",
        target_type="phone",
        risk_level="HIGH",
        risk_score=78.5,
        complaint_count=2,
        entity_count=3,
        findings=[
            InvestigationFinding(
                finding_id="FINDING-EVD-001",
                type=FindingType.ENTITY_REUSE,
                title="Phone Number Reuse",
                description="Phone number reused across 2 complaints.",
                severity="HIGH",
                confidence=0.85,
                source_service="EvidenceEngine",
                supporting_entity_ids=("+919876543210",),
                supporting_complaint_ids=("C-101", "C-102"),
                supporting_evidence_ids=("EVD-001",),
            )
        ],
        recommendations=[
            InvestigationRecommendation(
                recommendation_id="REC-001",
                action="Block Phone Number +919876543210",
                priority="HIGH",
                reason="Phone number reused across 2 complaints.",
                trigger="ENTITY_REUSE",
                target_entities=("+919876543210",),
            )
        ],
    )

    scenario_simple = GoldenScenario(
        scenario_id="SIMPLE_FRAUD_CASE",
        name="Simple Fraud Case",
        description="Standard 2-complaint phone reuse fraud scenario.",
        summary=summary_simple,
        expected_risk_level="HIGH",
        expected_finding_count=1,
        expected_citation_ids=("C-101", "C-102", "EVD-001", "+919876543210"),
    )

    # 2. Entity Reuse Case
    summary_reuse = summary_service.build_scenario(
        target_value="scammer@upi",
        target_type="upi",
        risk_level="CRITICAL",
        risk_score=92.0,
        complaint_count=5,
        entity_count=8,
        findings=[
            InvestigationFinding(
                finding_id="FINDING-EVD-002",
                type=FindingType.ENTITY_REUSE,
                title="High Volume UPI Reuse",
                description="UPI ID scammer@upi associated with 5 distinct complaints.",
                severity="CRITICAL",
                confidence=0.95,
                source_service="EvidenceEngine",
                supporting_entity_ids=("scammer@upi",),
                supporting_complaint_ids=("C-101", "C-102", "C-103", "C-104", "C-105"),
                supporting_evidence_ids=("EVD-002", "EVD-003"),
            )
        ],
        recommendations=[
            InvestigationRecommendation(
                recommendation_id="REC-002",
                action="Freeze UPI VPA scammer@upi",
                priority="CRITICAL",
                reason="UPI ID associated with 5 complaints.",
                trigger="HIGH_REUSE_COUNT",
                target_entities=("scammer@upi",),
            )
        ],
    )

    scenario_reuse = GoldenScenario(
        scenario_id="ENTITY_REUSE_CASE",
        name="Entity Reuse Case",
        description="High volume UPI ID reuse across 5 complaints.",
        summary=summary_reuse,
        expected_risk_level="CRITICAL",
        expected_finding_count=1,
        expected_citation_ids=("C-101", "C-102", "C-103", "C-104", "C-105", "EVD-002", "EVD-003", "scammer@upi"),
    )

    # 3. Large Fraud Ring
    summary_ring = summary_service.build_scenario(
        target_value="RING-999",
        target_type="fraud_ring",
        risk_level="CRITICAL",
        risk_score=98.0,
        complaint_count=12,
        entity_count=15,
        findings=[
            InvestigationFinding(
                finding_id="FINDING-EVO-001",
                type=FindingType.NETWORK_EXPANSION,
                title="Coordinated Fraud Syndicate",
                description="Organized fraud ring involving 15 nodes and 12 complaints.",
                severity="CRITICAL",
                confidence=0.99,
                source_service="FraudEvolutionService",
                supporting_entity_ids=("RING-999", "+919876543210", "scammer@upi"),
                supporting_complaint_ids=("C-101", "C-102", "C-103"),
                supporting_evidence_ids=("EVD-010",),
            )
        ],
        recommendations=[
            InvestigationRecommendation(
                recommendation_id="REC-003",
                action="Issue Law Enforcement Alert for Fraud Ring RING-999",
                priority="CRITICAL",
                reason="Coordinated fraud ring exceeding threshold.",
                trigger="FRAUD_RING_EXPANSION",
                target_entities=("RING-999",),
            )
        ],
    )

    scenario_ring = GoldenScenario(
        scenario_id="LARGE_FRAUD_RING",
        name="Large Fraud Ring",
        description="Complex 15-entity organized fraud syndicate.",
        summary=summary_ring,
        expected_risk_level="CRITICAL",
        expected_finding_count=1,
        expected_citation_ids=("RING-999", "C-101", "C-102", "C-103", "EVD-010"),
    )

    return {
        scenario_simple.scenario_id: scenario_simple,
        scenario_reuse.scenario_id: scenario_reuse,
        scenario_ring.scenario_id: scenario_ring,
    }


class InvestigationSummaryService_MockFactory:
    """Helper factory constructing mock InvestigationSummary scenario objects."""

    def build_scenario(
        self,
        target_value: str,
        target_type: str,
        risk_level: str,
        risk_score: float,
        complaint_count: int,
        entity_count: int,
        findings: list[InvestigationFinding],
        recommendations: list[InvestigationRecommendation],
    ) -> InvestigationSummary:
        t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 5, 14, 30, 0, tzinfo=timezone.utc)

        metadata = InvestigationMetadata(
            summary_version="1.0",
            generated_at=t1,
            target_type=target_type,
            target_value=target_value,
        )

        overview = InvestigationOverview(
            target_type=target_type,
            target_value=target_value,
            overall_risk_level=risk_level,
            overall_risk_score=risk_score,
            total_complaints=complaint_count,
            total_entities=entity_count,
            time_range_start=t0,
            time_range_end=t1,
        )

        presentation = InvestigationPresentation(
            executive_summary=f"Investigation summary for target {target_value} exhibiting {risk_level} risk.",
            risk_justification=f"Assigned risk level {risk_level} based on deterministic evidence synthesis.",
            key_takeaways=tuple(f.title for f in findings),
        )

        statistics = InvestigationStatistics(
            total_complaints=complaint_count,
            total_entities=entity_count,
            phone_count=1,
            upi_count=1,
            email_count=0,
            bank_account_count=0,
        )

        timeline = InvestigationTimelineSummary(
            total_events=complaint_count,
            start_time=t0,
            end_time=t1,
            duration_days=4,
            events=(),
        )

        entities = InvestigationEntitySummary(
            total_connected_entities=entity_count,
            primary_entity_types=(target_type,),
            top_risk_entities=(target_value,),
        )

        evolution = InvestigationEvolutionSummary(
            initial_appearance=t0,
            latest_activity=t1,
            evolution_stage="EXPANDING",
            network_growth_rate=1.5,
        )

        evidence = InvestigationEvidenceSummary(
            total_evidence_units=len(findings),
            high_confidence_count=len(findings),
            primary_evidence_types=("ENTITY_REUSE",),
            overall_evidence_score=0.9,
        )

        data_quality = InvestigationDataQuality(
            completeness_score=0.95,
            quality_rating="HIGH",
            missing_fields=(),
            warnings=(),
        )

        return InvestigationSummary(
            metadata=metadata,
            overview=overview,
            presentation=presentation,
            statistics=statistics,
            timeline=timeline,
            entities=entities,
            evolution=evolution,
            evidence=evidence,
            data_quality=data_quality,
            findings=tuple(findings),
            critical_findings=tuple(findings),
            recommendations=tuple(recommendations),
        )
