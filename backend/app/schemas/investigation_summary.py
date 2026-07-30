"""
Schemas for the deterministic InvestigationSummary architecture (Sprint 9 Phase 1.5 Refinements).

Serves as the canonical immutable 'Case File DTO' for the entire SentinelGraph platform,
aggregating deterministic outputs from Timeline, Entity Analysis, Timeline Analysis,
Fraud Evolution, Evidence Engine, and Data Quality without LLM or persistence dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.timeline import (
    EntityTimelineInfo,
    FraudEvolutionEvent,
    InvestigationEvidence,
    TimelineEvent,
)


class FindingType(str, Enum):
    """
    Supported types of deterministic investigation findings.
    """

    ENTITY_REUSE = "ENTITY_REUSE"
    NETWORK_EXPANSION = "NETWORK_EXPANSION"
    PAYMENT_EXPANSION = "PAYMENT_EXPANSION"
    COMMUNICATION_PATTERN = "COMMUNICATION_PATTERN"
    TIMELINE = "TIMELINE"
    RISK = "RISK"
    EVIDENCE = "EVIDENCE"


class InvestigationMetadata(BaseModel):
    """
    Metadata for the investigation summary session.
    """

    model_config = ConfigDict(frozen=True)

    target_value: str = Field(
        ...,
        description="Lookup entity value or identifier being investigated.",
    )
    target_type: str | None = Field(
        default=None,
        description="Type of the investigation target entity (e.g. phone, email, upi).",
    )
    summary_version: str = Field(
        default="1.0",
        description="Canonical schema version for the investigation summary.",
    )
    generated_by: str = Field(
        default="InvestigationSummaryService",
        description="Service identifier generating this summary.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the summary was computed.",
    )


class InvestigationOverview(BaseModel):
    """
    High-level executive overview of structured investigation facts.
    Excludes presentation narrative text (which lives in InvestigationPresentation).
    """

    model_config = ConfigDict(frozen=True)

    target_value: str = Field(
        ...,
        description="Investigation target entity value.",
    )
    total_complaints: int = Field(
        default=0,
        description="Total connected complaints in the investigation network.",
    )
    total_entities: int = Field(
        default=0,
        description="Total distinct entities in the investigation network.",
    )
    time_range_start: datetime | None = Field(
        default=None,
        description="Timestamp of the earliest recorded event.",
    )
    time_range_end: datetime | None = Field(
        default=None,
        description="Timestamp of the latest recorded event.",
    )
    overall_risk_level: str = Field(
        default="LOW",
        description="Deterministic overall risk level (LOW, MEDIUM, HIGH, CRITICAL).",
    )


class InvestigationPresentation(BaseModel):
    """
    Presentation-oriented section separating narrative summaries from structured facts.
    """

    model_config = ConfigDict(frozen=True)

    executive_summary: str = Field(
        ...,
        description="Deterministic presentation executive summary statement.",
    )
    risk_justification: str = Field(
        ...,
        description="Deterministic explanation for the assigned overall risk level.",
    )
    key_takeaways: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Bullet points for executive UI or report presentation.",
    )


class InvestigationStatistics(BaseModel):
    """
    Canonical investigation statistics breakdown.
    """

    model_config = ConfigDict(frozen=True)

    total_complaints: int = Field(
        default=0,
        description="Total connected complaints.",
    )
    total_entities: int = Field(
        default=0,
        description="Total distinct entities.",
    )
    phones: int = Field(default=0, description="Phone count.")
    upis: int = Field(default=0, description="UPI count.")
    emails: int = Field(default=0, description="Email count.")
    urls: int = Field(default=0, description="URL count.")
    bank_accounts: int = Field(default=0, description="Bank account count.")
    organizations: int = Field(default=0, description="Organization count.")
    people: int = Field(default=0, description="People count.")
    locations: int = Field(default=0, description="Location count.")
    entity_type_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of entity type names to their counts.",
    )


class InvestigationTimelineSummary(BaseModel):
    """
    Chronological timeline summary.
    """

    model_config = ConfigDict(frozen=True)

    total_events: int = Field(
        default=0,
        description="Total timeline events.",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Earliest event timestamp.",
    )
    end_time: datetime | None = Field(
        default=None,
        description="Latest event timestamp.",
    )
    duration_days: int = Field(
        default=0,
        description="Total duration of activity in days.",
    )
    events: tuple[TimelineEvent, ...] = Field(
        default_factory=tuple,
        description="List of chronological timeline events.",
    )


class InvestigationEntitySummary(BaseModel):
    """
    Entity evolution and usage summary.
    """

    model_config = ConfigDict(frozen=True)

    total_entities: int = Field(
        default=0,
        description="Total distinct entities.",
    )
    reused_entities_count: int = Field(
        default=0,
        description="Number of entities reused across multiple complaints.",
    )
    entities: tuple[EntityTimelineInfo, ...] = Field(
        default_factory=tuple,
        description="List of entity evolution records.",
    )


class InvestigationEvolutionSummary(BaseModel):
    """
    Fraud network structural evolution summary.
    """

    model_config = ConfigDict(frozen=True)

    total_evolution_events: int = Field(
        default=0,
        description="Total evolution events.",
    )
    events: tuple[FraudEvolutionEvent, ...] = Field(
        default_factory=tuple,
        description="List of fraud evolution milestone events.",
    )


class InvestigationEvidenceSummary(BaseModel):
    """
    Structured evidence summary with aggregate metrics.
    """

    model_config = ConfigDict(frozen=True)

    total_evidence_units: int = Field(
        default=0,
        description="Total evidence units synthesized.",
    )
    critical_count: int = Field(default=0, description="Critical evidence count.")
    high_count: int = Field(default=0, description="High evidence count.")
    medium_count: int = Field(default=0, description="Medium evidence count.")
    low_count: int = Field(default=0, description="Low evidence count.")
    highest_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Highest confidence score among synthesized evidence units.",
    )
    average_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average confidence score across evidence units.",
    )
    highest_severity: str = Field(
        default="NONE",
        description="Highest evidence severity level present.",
    )
    evidence_items: tuple[InvestigationEvidence, ...] = Field(
        default_factory=tuple,
        description="List of structured evidence units.",
    )


class InvestigationDataQuality(BaseModel):
    """
    Deterministic data quality and completeness metrics.
    """

    model_config = ConfigDict(frozen=True)

    missing_data: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Identified missing data items or unparsed fields.",
    )
    isolated_entities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Entities linked to only one complaint.",
    )
    timeline_gaps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Identified timeline gaps between consecutive events (>30 days).",
    )
    duplicate_entities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Identified potential duplicate entity values.",
    )
    overall_data_quality: str = Field(
        default="HIGH",
        description="Deterministic overall data quality assessment (HIGH, MEDIUM, LOW).",
    )


class InvestigationFinding(BaseModel):
    """
    Structured, strongly typed deterministic finding with full provenance citations.
    """

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(
        default_factory=lambda: f"FINDING-{uuid4().hex[:8].upper()}",
        description="Unique identifier for the finding.",
    )
    type: FindingType = Field(
        ...,
        description="Strongly typed category of the finding.",
    )
    severity: str = Field(
        default="MEDIUM",
        description="Severity level (LOW, MEDIUM, HIGH, CRITICAL).",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Deterministic confidence score.",
    )
    title: str = Field(
        ...,
        description="Title summarizing the finding.",
    )
    description: str = Field(
        ...,
        description="Deterministic description of the finding.",
    )
    supporting_evidence_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Linked evidence unit IDs.",
    )
    supporting_complaint_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Linked complaint identifiers.",
    )
    supporting_entity_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Linked entity lookup values.",
    )


class InvestigationRecommendation(BaseModel):
    """
    Deterministic and explainable action recommendation.
    """

    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(
        default_factory=lambda: f"REC-{uuid4().hex[:8].upper()}",
        description="Unique identifier for the recommendation.",
    )
    action: str = Field(
        ...,
        description="Recommended action to take.",
    )
    priority: str = Field(
        default="MEDIUM",
        description="Priority level (LOW, MEDIUM, HIGH).",
    )
    reason: str = Field(
        ...,
        description="Deterministic rationale supporting the recommendation.",
    )
    trigger: str = Field(
        ...,
        description="Deterministic trigger or rule that generated this recommendation.",
    )
    target_entities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Entities targeted by this recommendation.",
    )


class InvestigationSummary(BaseModel):
    """
    Canonical immutable 'Case File DTO' for the entire SentinelGraph platform.
    Consolidates deterministic outputs across all analysis engines.
    """

    model_config = ConfigDict(frozen=True)

    metadata: InvestigationMetadata = Field(
        ...,
        description="Metadata about the summary generation.",
    )
    overview: InvestigationOverview = Field(
        ...,
        description="Structured facts overview.",
    )
    presentation: InvestigationPresentation = Field(
        ...,
        description="Presentation narrative and takeaways.",
    )
    statistics: InvestigationStatistics = Field(
        ...,
        description="Aggregated investigation statistics.",
    )
    timeline: InvestigationTimelineSummary = Field(
        ...,
        description="Chronological timeline summary.",
    )
    entities: InvestigationEntitySummary = Field(
        ...,
        description="Entity evolution and reuse summary.",
    )
    evolution: InvestigationEvolutionSummary = Field(
        ...,
        description="Fraud network evolution summary.",
    )
    evidence: InvestigationEvidenceSummary = Field(
        ...,
        description="Structured evidence units and aggregate metrics.",
    )
    data_quality: InvestigationDataQuality = Field(
        ...,
        description="Data quality metrics.",
    )
    findings: tuple[InvestigationFinding, ...] = Field(
        default_factory=tuple,
        description="List of typed deterministic findings.",
    )
    recommendations: tuple[InvestigationRecommendation, ...] = Field(
        default_factory=tuple,
        description="List of explainable action recommendations.",
    )
