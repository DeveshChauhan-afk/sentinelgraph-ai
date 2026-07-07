# app/models/incident.py

"""
Incident ORM model.

Represents a reported fraudulent incident within the SentinelGraph AI platform.
"""

from typing import Optional
from sqlalchemy import String, Text, Float, Enum, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base_model import BaseModel
from app.models.enums import (
    IncidentStatus, 
    Priority, 
    ReporterType, 
    ScamCategory, 
    IncidentSource
)

class Incident(BaseModel):
    """
    Incident ORM model representing a fraudulent event.
    """
    __tablename__ = "incidents"

    __table_args__ = (
        Index("idx_incident_status", "status"),
        Index("idx_incident_priority", "priority"),
        Index("idx_incident_created", "created_at"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="check_risk_score_range"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    reporter_type: Mapped[ReporterType] = mapped_column(
        Enum(ReporterType, name="reporter_type_enum",values_callable=lambda enum: [e.value for e in enum],),
        nullable=False,
    )
    source: Mapped[IncidentSource] = mapped_column(
        Enum(IncidentSource, name="incident_source_enum",values_callable=lambda enum: [e.value for e in enum],),
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status_enum",values_callable=lambda enum: [e.value for e in enum],),
        nullable=False,
        server_default=IncidentStatus.NEW.value,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="priority_enum",values_callable=lambda enum: [e.value for e in enum],),
        nullable=False,
        server_default=Priority.MEDIUM.value,
    )
    scam_category: Mapped[Optional[ScamCategory]] = mapped_column(
        Enum(ScamCategory, name="scam_category_enum",values_callable=lambda enum: [e.value for e in enum],),
        nullable=True,
    )
    ai_summary: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True, 
        comment="AI-generated fraud summary"
    )
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    graph_node_id: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True, 
        index=True
    )
    
    case_reference: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="External reference identifier (e.g., FIR, Bank Complaint ID)"
    )

    def __repr__(self) -> str:
        return (
            f"<Incident("
            f"id={self.id}, "
            f"title='{self.title}', "
            f"status={self.status.value}, "
            f"priority={self.priority.value})>"
        )