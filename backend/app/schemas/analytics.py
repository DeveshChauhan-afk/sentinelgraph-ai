"""
Schemas for graph analytics endpoints.

These models provide high-level insights into the fraud intelligence graph,
including graph statistics, entity rankings, and fraud ring summaries.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GraphSummary(BaseModel):
    """
    Overall statistics about the fraud intelligence graph.
    """

    total_nodes: int = Field(
        description="Total number of graph nodes.",
    )

    total_edges: int = Field(
        description="Total number of graph relationships.",
    )

    complaints: int = Field(
        description="Number of complaint nodes.",
    )

    phones: int = Field(
        description="Number of phone entities.",
    )

    emails: int = Field(
        description="Number of email entities.",
    )

    upis: int = Field(
        description="Number of UPI entities.",
    )

    organizations: int = Field(
        description="Number of organization entities.",
    )

    persons: int = Field(
        description="Number of person entities.",
    )

    locations: int = Field(
        description="Number of location entities.",
    )

    bank_accounts: int = Field(
        description="Number of bank account entities.",
    )

    average_degree: float = Field(
        description="Average node degree across the graph.",
    )


class TopConnectedEntity(BaseModel):
    """
    Represents one of the most connected entities in the graph.
    """

    id: str = Field(
        description="Graph node identifier.",
    )

    label: str = Field(
        description="Display label.",
    )

    type: str = Field(
        description="Entity type.",
    )

    connection_count: int = Field(
        description="Number of connected relationships.",
    )

    complaint_count: int = Field(
        description="Number of linked complaints.",
    )


class EntityDistribution(BaseModel):
    """
    Distribution of entity types within the graph.
    """

    entity_type: str = Field(
        description="Entity type.",
    )

    count: int = Field(
        description="Number of entities of this type.",
    )


class FraudRingSummary(BaseModel):
    """
    Summary of a detected fraud ring.
    """

    ring_id: str = Field(
        description="Unique fraud ring identifier.",
    )

    entity_count: int = Field(
        description="Number of entities in the fraud ring.",
    )

    complaint_count: int = Field(
        description="Number of complaints linked to the fraud ring.",
    )

    relationship_count: int = Field(
        description="Number of relationships inside the fraud ring.",
    )

    risk_score: float = Field(
        description="Computed fraud risk score.",
    )

class SharedEntityAnalysis(BaseModel):
    """
    Represents a shared entity linking multiple complaints.
    """

    entity_id: str = Field(
        description="Unique graph identifier.",
    )

    entity_label: str = Field(
        description="Display value of the entity.",
    )

    entity_type: str = Field(
        description="Entity type.",
    )

    complaint_count: int = Field(
        description="Number of linked complaints.",
    )

    complaint_ids: list[str] = Field(
        description="Linked complaint identifiers.",
    )