"""
Internal graph query result models.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.graph.models import GraphNode


class NeighborQueryResult(BaseModel):
    """
    Repository result for neighboring graph nodes.
    """

    entity: GraphNode
    neighbors: list[GraphNode]


class IncidentQueryResult(BaseModel):
    """
    Repository result for related complaint nodes.
    """

    entity: GraphNode
    incidents: list[GraphNode]


class RiskMetricsResult(BaseModel):
    """
    Raw graph metrics used for risk analysis.
    """

    entity: GraphNode

    incident_count: int
    neighbor_count: int
    phone_count: int
    upi_count: int
    email_count: int
    organization_count: int

class FraudRingResult(BaseModel):
    """
    Repository result representing an entire connected fraud ring.
    """

    entity: GraphNode
    nodes: list[GraphNode]
    incidents: list[GraphNode]

class NetworkSummaryResult(BaseModel):
    """
    Repository result containing network statistics.
    """

    total_nodes: int

    total_relationships: int

    complaints: int

    phones: int

    upis: int

    emails: int

    organizations: int
