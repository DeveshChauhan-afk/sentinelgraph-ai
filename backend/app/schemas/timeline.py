from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.graph.models import GraphNode


class TimelineEntity(BaseModel):
    """
    Entity involved in a timeline event.
    """

    label: str = Field(
        description="Entity label (Phone, UPI, Email, etc.)."
    )

    value: str = Field(
        description="Entity lookup value."
    )

class TimelineEventType(str, Enum):
    """
    Types of investigation timeline events.
    """

    COMPLAINT_CREATED = "complaint_created"
    ENTITY_FIRST_SEEN = "entity_first_seen"
    ENTITY_REUSED = "entity_reused"
    NEW_LINK_DISCOVERED = "new_link_discovered"
    FRAUD_RING_EXPANDED = "fraud_ring_expanded"

class EventImportance(str, Enum):
    """
    Importance level of a timeline event.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TimelineEvent(BaseModel):
    """
    Represents a single chronological investigation event.
    """

    timestamp: datetime = Field(
        description="Timestamp of the event."
    )

    event_type: TimelineEventType = Field(
        description="Classification of the event."
    )

    title: str = Field(
        description="Short event title."
    )

    description: str = Field(
        description="Human-readable event description."
    )

    complaint_id: str = Field(
        description="Associated complaint identifier."
    )

    entities: list[GraphNode] = Field(
        default_factory=list,
        description="Graph entities involved in this event."
    )

    importance: EventImportance = Field(
        description="Investigative importance."
    )

class InvestigationTimeline(BaseModel):
    """
    Chronological reconstruction of an investigation.
    """

    target: str = Field(
        description="Lookup value that was investigated."
    )

    total_events: int = Field(
        description="Total number of reconstructed events."
    )

    start_date: datetime | None = Field(
        default=None,
        description="Earliest event timestamp."
    )

    end_date: datetime | None = Field(
        default=None,
        description="Latest event timestamp."
    )

    events: list[TimelineEvent] = Field(
        default_factory=list,
        description="Chronological investigation events."
    )