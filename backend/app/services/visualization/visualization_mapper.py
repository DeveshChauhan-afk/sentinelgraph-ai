"""
Maps Neo4j graph paths into visualization schemas.

This mapper transforms raw Neo4j Path objects into a frontend-friendly
graph representation that can be consumed by visualization libraries
such as Cytoscape.js, React Flow, and Vis.js.
"""

from __future__ import annotations

from datetime import datetime, timezone

from neo4j.graph import Node, Path, Relationship

from app.schemas.visualization import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphResponse,
)


class VisualizationMapper:
    """
    Maps Neo4j graph objects into visualization schemas.
    """

    def map_paths(
        self,
        paths: list[Path],
        depth: int,
    ) -> GraphResponse:
        """
        Convert Neo4j paths into a GraphResponse.
        """
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        for path in paths:

            for node in path.nodes:
                mapped = self._map_node(node)
                nodes[mapped.id] = mapped

            for relationship in path.relationships:
                mapped = self._map_relationship(relationship)
                edges[mapped.id] = mapped

        metadata = GraphMetadata(
            node_count=len(nodes),
            edge_count=len(edges),
            depth=depth,
            generated_at=datetime.now(timezone.utc),
        )

        return GraphResponse(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            metadata=metadata,
        )

    def _map_node(
        self,
        node: Node,
    ) -> GraphNode:
        """
        Convert a Neo4j node into a GraphNode.
        """
        properties = dict(node)

        node_id = properties["id"]

        labels = list(node.labels)
        node_type = labels[0] if labels else "UNKNOWN"

        label = self._node_label(
            node_type=node_type,
            properties=properties,
        )

        return GraphNode(
            id=node_id,
            label=label,
            type=node_type,
            properties=properties,
        )

    def _map_relationship(
        self,
        relationship: Relationship,
    ) -> GraphEdge:
        """
        Convert a Neo4j relationship into a GraphEdge.
        """
        source = relationship.start_node["id"]
        target = relationship.end_node["id"]

        relationship_type = relationship.type

        edge_id = f"{source}|" f"{relationship_type}|" f"{target}"

        return GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            label=relationship_type,
            properties=dict(relationship),
        )

    def _node_label(
        self,
        node_type: str,
        properties: dict,
    ) -> str:
        """
        Determine the display label for a node.
        """
        if node_type == "COMPLAINT":
            return properties.get(
                "complaint_id",
                properties["id"],
            )

        return properties.get(
            "value",
            properties["id"],
        )
