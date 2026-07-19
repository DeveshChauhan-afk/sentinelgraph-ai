"""
Visualization schemas for graph rendering APIs.

These models provide a frontend-friendly representation of graph data,
independent of the underlying graph database implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """
    Represents a node in the visualization graph.
    """

    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """
    Represents an edge in the visualization graph.
    """

    id: str
    source: str
    target: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphMetadata(BaseModel):
    """
    Metadata describing the generated graph.
    """

    node_count: int
    edge_count: int
    depth: int
    generated_at: datetime


class GraphResponse(BaseModel):
    """
    Complete graph response returned by visualization endpoints.
    """

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: GraphMetadata
