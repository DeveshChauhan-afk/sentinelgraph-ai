#app/graph/models.py
"""
Graph domain models.

Defines provider-independent graph objects used to build the
Fraud Intelligence Graph before persistence in Neo4j.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphLabel(str, Enum):
    """Supported graph node labels."""

    COMPLAINT = "Complaint"
    PHONE = "Phone"
    UPI = "UPI"
    EMAIL = "Email"
    URL = "URL"
    BANK_ACCOUNT = "BankAccount"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    LOCATION = "Location"


class RelationshipType(str, Enum):
    """Supported relationship types."""

    MENTIONS = "MENTIONS"


class GraphNode(BaseModel):
    """
    Represents a graph node.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(
        ...,
        description="Globally unique node identifier.",
    )

    label: GraphLabel = Field(
        ...,
        description="Graph node label.",
    )

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Node properties.",
    )


class GraphRelationship(BaseModel):
    """
    Represents a graph relationship.
    """

    model_config = ConfigDict(from_attributes=True)

    source: str = Field(
        ...,
        description="Source node identifier.",
    )

    target: str = Field(
        ...,
        description="Target node identifier.",
    )

    type: RelationshipType = Field(
        ...,
        description="Relationship type.",
    )

    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship properties.",
    )


class GraphData(BaseModel):
    """
    Container for graph nodes and relationships.
    """

    model_config = ConfigDict(from_attributes=True)

    nodes: list[GraphNode] = Field(
        default_factory=list,
    )

    relationships: list[GraphRelationship] = Field(
        default_factory=list,
    )


class GraphPersistenceResult(BaseModel):
    """
    Result returned after graph persistence.
    """

    model_config = ConfigDict(from_attributes=True)

    nodes_persisted: int = Field(
        ...,
        description="Number of persisted graph nodes.",
    )

    relationships_persisted: int = Field(
        ...,
        description="Number of persisted graph relationships.",
    )

    duration_ms: float = Field(
        ...,
        description="Persistence execution time in milliseconds.",
    )
