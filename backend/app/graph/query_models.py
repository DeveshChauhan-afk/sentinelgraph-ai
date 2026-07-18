"""
Graph query models.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.graph.models import GraphNode


class GraphNeighborsResponse(BaseModel):
    """
    Response containing an entity and its directly connected neighbors.
    """

    entity: GraphNode
    neighbors: list[GraphNode]


class RelatedIncidentsResponse(BaseModel):
    """
    Response containing an entity and all related complaints.
    """

    entity: GraphNode
    incidents: list[GraphNode]


class RiskMetrics(BaseModel):
    """
    Risk metrics returned by the API.
    """

    incident_count: int
    neighbor_count: int
    phone_count: int
    upi_count: int
    email_count: int
    organization_count: int


class EntityRiskResponse(BaseModel):
    """
    Risk analysis response.
    """

    entity: GraphNode

    risk_score: int

    risk_level: str

    metrics: RiskMetrics

    reasons: list[str]


class FraudRingResponse(BaseModel):
    """
    Response containing every node belonging to the same fraud ring.
    """

    entity: GraphNode

    nodes: list[GraphNode]

    incidents: list[GraphNode]

    total_nodes: int

    total_incidents: int


class NetworkSummaryResponse(BaseModel):
    """
    Network-wide fraud graph statistics.
    """

    total_nodes: int

    total_relationships: int

    complaints: int

    phones: int

    upis: int

    emails: int

    organizations: int


class TopRiskEntityResponse(BaseModel):
    """
    Response describing a high-risk entity.
    """

    entity: GraphNode

    incident_count: int

    neighbor_count: int

    risk_score: int

    risk_level: str


class PathResponse(BaseModel):
    """
    API response representing the shortest path.
    """

    found: bool

    length: int

    nodes: list[GraphNode]


class SharedEntityResponse(BaseModel):
    """
    Shared entity analysis response.
    """

    entity: GraphNode

    complaints: list[GraphNode]

    complaint_count: int
