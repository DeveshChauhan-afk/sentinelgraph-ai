from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):

    """
    Types of events that can occur on an investigation timeline.
    """

    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    ENTITY_FIRST_SEEN = "ENTITY_FIRST_SEEN"
    ENTITY_REUSED = "ENTITY_REUSED"
    NETWORK_EXPANDED = "NETWORK_EXPANDED"


class TimelineEvent(BaseModel):
    """
    Represents a single event in the chronological timeline.
    """

    event_type: TimelineEventType = Field(
        description="Type of the timeline event."
    )
    timestamp: datetime = Field(
        description="Timestamp when the event occurred."
    )
    title: str = Field(
        description="Short summary title of the event."
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the event (optional)."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured arbitrary metadata associated with the event."
    )


class EntityTimelineInfo(BaseModel):
    """
    Timeline information regarding an entity's evolution and usage.
    """

    entity_type: str = Field(
        description="Type/Label of the entity (e.g. Phone, UPI, Email)."
    )
    entity_value: str = Field(
        description="Lookup value of the entity."
    )
    first_seen: datetime = Field(
        description="Earliest timestamp when the entity appeared."
    )
    first_seen_complaint: str = Field(
        description="Complaint ID where the entity was first observed."
    )
    usage_count: int = Field(
        description="Total number of complaints in which this entity was referenced."
    )
    complaint_ids: list[str] = Field(
        default_factory=list,
        description="List of all complaint IDs referencing this entity."
    )



class TimelineStatistics(BaseModel):
    """
    Statistical summary of complaints and entity categories in the timeline.
    """

    total_complaints: int = Field(
        default=0,
        description="Total number of connected complaints."
    )
    total_entities: int = Field(
        default=0,
        description="Total distinct entities participating in the network."
    )
    phones: int = Field(
        default=0,
        description="Number of phone entities."
    )
    upis: int = Field(
        default=0,
        description="Number of UPI entities."
    )
    emails: int = Field(
        default=0,
        description="Number of email entities."
    )
    urls: int = Field(
        default=0,
        description="Number of URL entities."
    )
    bank_accounts: int = Field(
        default=0,
        description="Number of bank account entities."
    )
    organizations: int = Field(
        default=0,
        description="Number of organization entities."
    )
    people: int = Field(
        default=0,
        description="Number of person entities."
    )
    locations: int = Field(
        default=0,
        description="Number of location entities."
    )


class InsightSeverity(str, Enum):
    """
    Severity level of a timeline insight.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TimelineInsight(BaseModel):
    """
    Deterministic insight generated from timeline and entity analysis.
    """

    title: str = Field(
        description="Short title summarizing the insight."
    )
    description: str = Field(
        description="Deterministic description of the finding."
    )
    severity: InsightSeverity = Field(
        description="Severity level of the insight."
    )


class EvolutionEventType(str, Enum):
    """
    Types of fraud network evolution events.
    """

    NETWORK_STARTED = "NETWORK_STARTED"
    ENTITY_TYPE_INTRODUCED = "ENTITY_TYPE_INTRODUCED"
    PAYMENT_INFRASTRUCTURE_EXPANDED = "PAYMENT_INFRASTRUCTURE_EXPANDED"
    COMMUNICATION_CHANNEL_EXPANDED = "COMMUNICATION_CHANNEL_EXPANDED"
    NETWORK_EXPANDED = "NETWORK_EXPANDED"
    NETWORK_MILESTONE = "NETWORK_MILESTONE"


class FraudEvolutionEvent(BaseModel):
    """
    Represents a single structural or behavioral evolution event in a fraud network.
    """

    event_type: EvolutionEventType = Field(
        description="Type of the fraud network evolution event."
    )
    timestamp: datetime = Field(
        description="Timestamp when the evolution milestone or change occurred."
    )
    title: str = Field(
        description="Title summarizing the evolution event."
    )
    description: str = Field(
        description="Detailed deterministic explanation of the evolution event."
    )
    related_entities: list[str] = Field(
        default_factory=list,
        description="List of entity lookup values associated with this event."
    )
    related_complaints: list[str] = Field(
        default_factory=list,
        description="List of complaint IDs associated with this event."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured arbitrary metadata associated with the event."
    )


class EvidenceSeverity(str, Enum):
    """
    Severity level for investigation evidence.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceType(str, Enum):
    """
    Extensible types of structured investigation evidence.
    """

    ENTITY_REUSE = "ENTITY_REUSE"
    NETWORK_EXPANSION = "NETWORK_EXPANSION"
    PAYMENT_EXPANSION = "PAYMENT_EXPANSION"
    COMMUNICATION_EXPANSION = "COMMUNICATION_EXPANSION"
    FRAUD_PATTERN = "FRAUD_PATTERN"
    NETWORK_MILESTONE = "NETWORK_MILESTONE"


class InvestigationEvidence(BaseModel):
    """
    Structured evidence unit supporting investigative conclusions with deterministic confidence scoring.
    """

    evidence_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the evidence unit."
    )
    evidence_type: EvidenceType = Field(
        description="Category/Type of the evidence."
    )
    severity: EvidenceSeverity = Field(
        description="Severity level of the evidence."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic confidence score between 0.0 and 1.0."
    )
    title: str = Field(
        description="Title summarizing the evidence finding."
    )
    description: str = Field(
        description="Detailed explanation of the evidence finding."
    )
    supporting_entities: list[str] = Field(
        default_factory=list,
        description="List of entity lookup values supporting this evidence."
    )
    supporting_complaints: list[str] = Field(
        default_factory=list,
        description="List of complaint IDs supporting this evidence."
    )
    supporting_events: list[str] = Field(
        default_factory=list,
        description="List of event titles or descriptions supporting this evidence."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured arbitrary metadata associated with the evidence."
    )


class TimelineResponse(BaseModel):
    """
    Response schema for timeline reconstruction queries.
    """

    investigation_target: str = Field(
        description="Target entity or lookup value being investigated."
    )
    total_events: int = Field(
        description="Total number of events in the timeline."
    )
    start_time: datetime | None = Field(
        default=None,
        description="Timestamp of the earliest event in the timeline."
    )
    end_time: datetime | None = Field(
        default=None,
        description="Timestamp of the latest event in the timeline."
    )
    events: list[TimelineEvent] = Field(
        default_factory=list,
        description="Chronological list of timeline events."
    )
    entity_first_seen: list[EntityTimelineInfo] = Field(
        default_factory=list,
        description="Chronological list of entities and their first appearance."
    )
    statistics: TimelineStatistics | None = Field(
        default=None,
        description="Statistical summary of the investigation network."
    )
    insights: list[TimelineInsight] = Field(
        default_factory=list,
        description="Deterministic investigative insights."
    )
    fraud_evolution: list[FraudEvolutionEvent] = Field(
        default_factory=list,
        description="Chronological fraud network evolution events."
    )
    evidence: list[InvestigationEvidence] = Field(
        default_factory=list,
        description="Structured investigation evidence units with confidence scoring."
    )