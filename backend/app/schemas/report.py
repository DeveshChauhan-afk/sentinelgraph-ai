"""
Schemas for ProfessionalInvestigationReport & Telemetry (Sprint 9 Phase 4.5 & 4.10).

Defines canonical immutable Pydantic models for structured professional investigation reports
and runtime execution telemetry.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class ReportTelemetry(BaseModel):
    """
    Execution telemetry and version tracking metadata.
    """

    model_config = ConfigDict(frozen=True)

    correlation_id: str = Field(
        ..., description="Unique request correlation identifier."
    )
    provider: str = Field(
        ..., description="LLM provider name (e.g. Gemini)."
    )
    model: str = Field(..., description="Model name used for completion.")
    latency_ms: float = Field(
        ..., ge=0.0, description="End-to-end execution latency in ms."
    )
    prompt_tokens: int = Field(
        default=0, ge=0, description="Prompt token count."
    )
    completion_tokens: int = Field(
        default=0, ge=0, description="Completion token count."
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Total token count."
    )
    prompt_hash: str = Field(
        ..., description="SHA-256 fingerprint hash of input prompt."
    )
    template_version: str = Field(
        default="1.0", description="Prompt template version."
    )
    summary_version: str = Field(
        default="1.0", description="Investigation summary version."
    )
    report_context_version: str = Field(
        default="1.0", description="Report context version."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when report was generated.",
    )


class ExecutiveSummarySection(BaseModel):
    """
    Executive summary report section.
    """

    model_config = ConfigDict(frozen=True)

    summary_text: str = Field(
        ..., description="High-level narrative executive summary."
    )
    overall_risk_level: str = Field(
        ..., description="Overall risk level (LOW, MEDIUM, HIGH, CRITICAL)."
    )
    key_takeaways: tuple[str, ...] = Field(
        default_factory=tuple, description="Key executive takeaways."
    )


class InvestigationScopeSection(BaseModel):
    """
    Scope and targets report section.
    """

    model_config = ConfigDict(frozen=True)

    target_value: str = Field(..., description="Target identifier.")
    target_type: str | None = Field(
        default=None, description="Target entity type."
    )
    total_complaints: int = Field(
        default=0, description="Connected complaints count."
    )
    total_entities: int = Field(
        default=0, description="Distinct entities count."
    )
    duration_days: int = Field(
        default=0, description="Investigation duration in days."
    )


class TimelineMilestone(BaseModel):
    """
    Timeline milestone item.
    """

    model_config = ConfigDict(frozen=True)

    event_type: str = Field(..., description="Milestone event type.")
    timestamp: str = Field(..., description="Timestamp string.")
    title: str = Field(..., description="Milestone title.")
    description: str = Field(..., description="Milestone description.")


class TimelineSection(BaseModel):
    """
    Timeline highlights section.
    """

    model_config = ConfigDict(frozen=True)

    timeline_narrative: str = Field(
        ..., description="Narrative summary of chronological evolution."
    )
    milestones: tuple[TimelineMilestone, ...] = Field(
        default_factory=tuple, description="Key milestones."
    )


class FindingSection(BaseModel):
    """
    Detailed critical finding report item.
    """

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(..., description="Finding ID.")
    title: str = Field(..., description="Finding title.")
    description: str = Field(..., description="Detailed description.")
    severity: str = Field(..., description="Severity level.")
    confidence: float = Field(..., description="Confidence score.")
    citations: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Natural citations referencing complaint/evidence IDs.",
    )


class EvolutionSection(BaseModel):
    """
    Fraud network evolution section.
    """

    model_config = ConfigDict(frozen=True)

    evolution_narrative: str = Field(..., description="Evolution narrative.")
    network_stage: str = Field(..., description="Current network stage.")


class EvidenceSection(BaseModel):
    """
    Supporting evidence section.
    """

    model_config = ConfigDict(frozen=True)

    evidence_summary: str = Field(
        ..., description="Evidence assessment summary."
    )
    supporting_evidence_count: int = Field(
        default=0, description="Number of supporting evidence units."
    )


class RecommendationSection(BaseModel):
    """
    Actionable recommendation report item.
    """

    model_config = ConfigDict(frozen=True)

    recommendation_id: str = Field(..., description="Recommendation ID.")
    action: str = Field(..., description="Recommended action.")
    priority: str = Field(..., description="Priority level.")
    rationale: str = Field(..., description="Rationale.")
    trigger: str = Field(..., description="Trigger rule.")
    target_entities: tuple[str, ...] = Field(
        default_factory=tuple, description="Target entity values."
    )


class LimitationSection(BaseModel):
    """
    Data quality limitations section.
    """

    model_config = ConfigDict(frozen=True)

    data_quality_assessment: str = Field(
        ..., description="Overall data quality assessment."
    )
    limitations: tuple[str, ...] = Field(
        default_factory=tuple, description="Identified data limitations."
    )


class ConclusionSection(BaseModel):
    """
    Overall conclusion section.
    """

    model_config = ConfigDict(frozen=True)

    summary_conclusion: str = Field(..., description="Concluding statement.")


class ProfessionalInvestigationReport(BaseModel):
    """
    Canonical immutable ProfessionalInvestigationReport API model.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier.")
    target_value: str = Field(
        ..., description="Investigation target identifier."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when report was generated.",
    )
    executive_summary: ExecutiveSummarySection = Field(
        ..., description="Executive summary section."
    )
    investigation_scope: InvestigationScopeSection = Field(
        ..., description="Scope section."
    )
    timeline_summary: TimelineSection = Field(
        ..., description="Timeline section."
    )
    key_findings: tuple[FindingSection, ...] = Field(
        default_factory=tuple, description="Key findings."
    )
    fraud_network_evolution: EvolutionSection = Field(
        ..., description="Evolution section."
    )
    evidence_assessment: EvidenceSection = Field(
        ..., description="Evidence section."
    )
    recommendations: tuple[RecommendationSection, ...] = Field(
        default_factory=tuple, description="Recommendations."
    )
    limitations: LimitationSection = Field(
        ..., description="Limitations section."
    )
    conclusion: ConclusionSection = Field(
        ..., description="Conclusion section."
    )
    telemetry: ReportTelemetry = Field(
        ..., description="Execution telemetry metadata."
    )
