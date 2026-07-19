"""
Schemas for Graph-RAG fraud investigations.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field
from app.graph.query_models import (
    EntityRiskResponse,
    FraudRingResponse,
    GraphNeighborsResponse,
    RelatedIncidentsResponse,
    SharedEntityResponse,
)


class InvestigationTargetType(str, Enum):
    """
    Supported investigation target types.
    """

    COMPLAINT = "complaint"
    PHONE = "phone"
    EMAIL = "email"
    UPI = "upi"
    BANK_ACCOUNT = "bank_account"
    DEVICE = "device"
    IP = "ip"
    PERSON = "person"


class InvestigationRequest(BaseModel):
    """
    Request for generating an investigation report.
    """

    target_type: InvestigationTargetType = Field(
        ...,
        description="Type of entity being investigated.",
    )

    target_value: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Identifier or value of the investigation target.",
    )


class ConnectedEntity(BaseModel):
    """
    Connected entity discovered during graph retrieval.
    """

    entity_type: str
    entity_value: str
    relationship: str


class InvestigationEvidence(BaseModel):
    """
    Complete graph evidence collected for an investigation.
    This object acts as the Graph-RAG retrieval context.
    """

    neighbors: GraphNeighborsResponse

    related_incidents: RelatedIncidentsResponse

    risk: EntityRiskResponse

    fraud_ring: FraudRingResponse

    shared_entities: SharedEntityResponse


class InvestigationReport(BaseModel):
    """
    AI-generated investigation report.
    """

    summary: str

    risk_level: str

    confidence: float

    findings: list[str]

    key_entities: list[str]

    recommended_actions: list[str]


class InvestigationResponse(BaseModel):
    """
    Complete investigation response.
    """

    target_type: InvestigationTargetType

    target_value: str

    evidence: InvestigationEvidence

    report: InvestigationReport
