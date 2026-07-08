# app/schemas/incident.py

"""
Pydantic schemas for Incident domain entity.

Separates user-provided input from system-controlled output and 
segregates internal AI-pipeline updates from manual investigator updates.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import (
    IncidentStatus,
    Priority,
    ReporterType,
    ScamCategory,
    IncidentSource,
)

class IncidentBase(BaseModel):
    """Fields the client is permitted to provide upon creation."""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    reporter_type: ReporterType
    source: IncidentSource
    case_reference: Optional[str] = Field(None, max_length=100)

class IncidentCreate(IncidentBase):
    """Schema for reporting a new incident."""
    pass

class IncidentUpdate(BaseModel):
    """
    Schema for manual investigation updates.
    Used by authorized investigators to update incident triage status.
    """
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    status: Optional[IncidentStatus] = None
    priority: Optional[Priority] = None
    case_reference: Optional[str] = Field(None, max_length=100)

class IncidentAIUpdate(BaseModel):
    """
    Schema for internal AI pipeline updates.
    Used only by backend AI services to sync analysis results.
    """
    scam_category: Optional[ScamCategory] = None
    ai_summary: Optional[str] = None
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    graph_node_id: Optional[str] = Field(None, max_length=100)

class IncidentResponse(IncidentBase):
    """Detailed response schema including all system-governed fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: IncidentStatus
    priority: Priority
    scam_category: Optional[ScamCategory] = None
    ai_summary: Optional[str] = None
    risk_score: Optional[float] = None
    graph_node_id: Optional[str] = None

class IncidentListResponse(BaseModel):
    """Optimized schema for dashboard listings."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    title: str
    status: IncidentStatus
    priority: Priority
    created_at: datetime
    reporter_type: ReporterType
    risk_score: Optional[float] = None
    graph_node_id: Optional[str] = None