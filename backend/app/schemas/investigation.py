"""
Schemas for Graph-RAG fraud investigations.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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
    Structured graph evidence retrieved from Neo4j.
    """

    complaint_count: int = 0

    related_complaints: list[str] = Field(default_factory=list)
    connected_entities: list[ConnectedEntity] = Field(default_factory=list)
    shortest_paths: list[str] = Field(default_factory=list)
    shared_entities: list[str] = Field(default_factory=list)

    findings: list[str] = Field(default_factory=list)
    key_entities: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    connected_entities: list[ConnectedEntity] = []
    fraud_ring_detected: bool = False

    shortest_paths: list[str] = []
    shared_entities: list[str] = []
    risk_score: float = 0.0


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