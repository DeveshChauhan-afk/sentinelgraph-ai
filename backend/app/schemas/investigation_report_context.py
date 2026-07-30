"""
Schemas for InvestigationReportContext (Sprint 9 Phase 2).

Provides an immutable, token-optimized, report-oriented view model derived
deterministically from an InvestigationSummary for consumption by PromptBuilder / Gemini.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.investigation_summary import FindingType


class ReportContextMetadata(BaseModel):
    """
    Metadata for the report context instance.
    """

    model_config = ConfigDict(frozen=True)

    report_context_version: str = Field(
        default="1.0",
        description="Version of the report context schema.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this context was built.",
    )
    generated_from_summary_version: str = Field(
        default="1.0",
        description="Version of the source InvestigationSummary.",
    )
    generated_by: str = Field(
        default="ReportContextBuilder",
        description="Service identifier.",
    )


class ReportContextOverview(BaseModel):
    """
    Executive overview facts tailored for LLM report consumption.
    """

    model_config = ConfigDict(frozen=True)

    target_value: str = Field(..., description="Investigation target identifier.")
    target_type: str | None = Field(default=None, description="Target entity type.")
    overall_risk_level: str = Field(..., description="Deterministic overall risk level.")
    total_complaints: int = Field(default=0, description="Total connected complaints.")
    total_entities: int = Field(default=0, description="Total distinct entities.")
    investigation_duration_days: int = Field(default=0, description="Investigation duration in days.")
    time_range_start: datetime | None = Field(default=None, description="Earliest recorded timestamp.")
    time_range_end: datetime | None = Field(default=None, description="Latest recorded timestamp.")


class ReportContextExecutiveStatistics(BaseModel):
    """
    Concise executive statistics metrics without duplication.
    """

    model_config = ConfigDict(frozen=True)

    complaint_count: int = Field(default=0, description="Total connected complaints count.")
    entity_count: int = Field(default=0, description="Total distinct entities count.")
    evidence_count: int = Field(default=0, description="Synthesized evidence units count.")
    reused_entity_count: int = Field(default=0, description="Entities reused across multiple complaints.")
    fraud_ring_count: int = Field(default=0, description="Detected fraud rings count.")
    duration_days: int = Field(default=0, description="Activity duration in days.")


class ReportTimelineHighlight(BaseModel):
    """
    Compact executive timeline milestone.
    """

    model_config = ConfigDict(frozen=True)

    event_type: str = Field(..., description="Timeline event type.")
    timestamp: datetime = Field(..., description="Event timestamp.")
    title: str = Field(..., description="Event title.")
    description: str = Field(..., description="Event description.")
    category: str = Field(
        ...,
        description="Highlight category (FIRST_OBSERVED, FIRST_PAYMENT, FIRST_COMMUNICATION, MAJOR_EXPANSION, LATEST_OBSERVED).",
    )


class ReportTimelineHighlights(BaseModel):
    """
    Ordered executive timeline highlights.
    """

    model_config = ConfigDict(frozen=True)

    total_highlights: int = Field(default=0, description="Number of highlight milestones.")
    highlights: tuple[ReportTimelineHighlight, ...] = Field(
        default_factory=tuple,
        description="Chronologically sorted executive timeline milestones.",
    )


class ReportEntityHighlight(BaseModel):
    """
    High-value entity highlight record.
    """

    model_config = ConfigDict(frozen=True)

    entity_type: str = Field(..., description="Entity type.")
    entity_value: str = Field(..., description="Entity lookup value.")
    usage_count: int = Field(..., description="Usage count across complaints.")
    first_seen: datetime = Field(..., description="First seen timestamp.")
    complaint_ids: tuple[str, ...] = Field(default_factory=tuple, description="Linked complaint IDs.")
    rank_reason: str = Field(..., description="Deterministic ranking justification.")


class ReportEntityHighlights(BaseModel):
    """
    Ranked high-value entity highlights.
    """

    model_config = ConfigDict(frozen=True)

    total_highlights: int = Field(default=0, description="Number of entity highlights.")
    highlights: tuple[ReportEntityHighlight, ...] = Field(
        default_factory=tuple,
        description="Ranked list of highest-value entities.",
    )


class ReportEvolutionHighlights(BaseModel):
    """
    Concise fraud network evolution narrative milestones.
    """

    model_config = ConfigDict(frozen=True)

    network_origin: str | None = Field(default=None, description="Network start milestone.")
    payment_expansion: tuple[str, ...] = Field(default_factory=tuple, description="Payment infrastructure expansions.")
    communication_expansion: tuple[str, ...] = Field(default_factory=tuple, description="Communication channel expansions.")
    network_growth: tuple[str, ...] = Field(default_factory=tuple, description="Network expansion milestones.")
    current_network_stage: str = Field(default="INITIAL_STAGE", description="Current network stage.")


class ReportCriticalFinding(BaseModel):
    """
    Report-ready finding with complete provenance citations.
    """

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(..., description="Unique finding ID.")
    type: FindingType | str = Field(..., description="Finding category type.")
    severity: str = Field(..., description="Severity level.")
    confidence: float = Field(..., description="Confidence score.")
    title: str = Field(..., description="Finding title.")
    description: str = Field(..., description="Finding description.")
    supporting_complaint_ids: tuple[str, ...] = Field(default_factory=tuple, description="Supporting complaint IDs.")
    supporting_entity_ids: tuple[str, ...] = Field(default_factory=tuple, description="Supporting entity values.")
    supporting_evidence_ids: tuple[str, ...] = Field(default_factory=tuple, description="Supporting evidence IDs.")


class ReportRecommendation(BaseModel):
    """
    Deterministic explainable action recommendation for reports.
    """

    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(..., description="Unique recommendation ID.")
    action: str = Field(..., description="Recommended action.")
    priority: str = Field(..., description="Priority level.")
    reason: str = Field(..., description="Rationale.")
    trigger: str = Field(..., description="Trigger rule or event.")
    affected_entities: tuple[str, ...] = Field(default_factory=tuple, description="Target entities.")


class ReportSupportingEvidence(BaseModel):
    """
    Materially supporting evidence unit for LLM prompt context.
    """

    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(..., description="Evidence ID.")
    evidence_type: str = Field(..., description="Evidence category.")
    severity: str = Field(..., description="Severity level.")
    confidence: float = Field(..., description="Confidence score.")
    title: str = Field(..., description="Evidence title.")
    description: str = Field(..., description="Evidence description.")
    supporting_entities: tuple[str, ...] = Field(default_factory=tuple, description="Supporting entities.")
    supporting_complaints: tuple[str, ...] = Field(default_factory=tuple, description="Supporting complaints.")


class ReportCitationItem(BaseModel):
    """
    Citation map item linking findings to evidence, complaints, and entities.
    """

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(..., description="Target finding ID.")
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple, description="Linked evidence unit IDs.")
    complaint_ids: tuple[str, ...] = Field(default_factory=tuple, description="Linked complaint IDs.")
    entity_ids: tuple[str, ...] = Field(default_factory=tuple, description="Linked entity lookup values.")


class InvestigationReportContext(BaseModel):
    """
    Canonical immutable report context ('Report Context DTO') for LLM generation.
    """

    model_config = ConfigDict(frozen=True)

    metadata: ReportContextMetadata = Field(..., description="Context metadata.")
    overview: ReportContextOverview = Field(..., description="Executive overview facts.")
    executive_statistics: ReportContextExecutiveStatistics = Field(..., description="Executive statistics.")
    timeline_highlights: ReportTimelineHighlights = Field(..., description="Executive timeline highlights.")
    entity_highlights: ReportEntityHighlights = Field(..., description="High-value entity highlights.")
    evolution_highlights: ReportEvolutionHighlights = Field(..., description="Evolution milestones.")
    critical_findings: tuple[ReportCriticalFinding, ...] = Field(default_factory=tuple, description="Report-ready findings.")
    recommendations: tuple[ReportRecommendation, ...] = Field(default_factory=tuple, description="Explainable recommendations.")
    supporting_evidence: tuple[ReportSupportingEvidence, ...] = Field(default_factory=tuple, description="Material evidence items.")
    citation_map: tuple[ReportCitationItem, ...] = Field(default_factory=tuple, description="Structured citation map.")
