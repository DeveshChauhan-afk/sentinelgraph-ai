"""
Graph builder for Fraud Intelligence Graph.

Transforms extracted entities into provider-independent graph objects.
"""

from uuid import UUID

from app.graph.models import (
    GraphData,
    GraphLabel,
    GraphNode,
    GraphRelationship,
    RelationshipType,
)
from app.schemas.entity_extraction import (
    ExtractedEntities,
    ExtractedEntity,
)


class GraphBuilder:
    """
    Builds graph data from extracted entities.
    """

    def build(
        self,
        complaint_id: UUID,
        entities: ExtractedEntities,
    ) -> GraphData:
        """
        Build graph data for a complaint.
        """
        graph = GraphData()

        nodes: dict[str, GraphNode] = {}

        complaint = self._create_complaint_node(
            complaint_id,
        )

        nodes[complaint.id] = complaint

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.phone_numbers,
            GraphLabel.PHONE,
            "phone",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.upi_ids,
            GraphLabel.UPI,
            "upi",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.emails,
            GraphLabel.EMAIL,
            "email",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.urls,
            GraphLabel.URL,
            "url",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.bank_accounts,
            GraphLabel.BANK_ACCOUNT,
            "bank",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.organizations,
            GraphLabel.ORGANIZATION,
            "org",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.persons,
            GraphLabel.PERSON,
            "person",
        )

        self._add_entities(
            graph,
            nodes,
            complaint,
            entities.locations,
            GraphLabel.LOCATION,
            "location",
        )

        graph.nodes = list(nodes.values())

        return graph

    def _create_complaint_node(
        self,
        complaint_id: UUID,
    ) -> GraphNode:
        return GraphNode(
            id=f"complaint:{complaint_id}",
            label=GraphLabel.COMPLAINT,
            properties={
                "id": str(complaint_id),
            },
        )

    def _add_entities(
        self,
        graph: GraphData,
        nodes: dict[str, GraphNode],
        complaint: GraphNode,
        entities: list[ExtractedEntity],
        label: GraphLabel,
        prefix: str,
    ) -> None:
        for entity in entities:
            node_id = f"{prefix}:{entity.value}"

            if node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    label=label,
                    properties={
                        "value": entity.value,
                        "confidence": entity.confidence,
                    },
                )

            graph.relationships.append(
                GraphRelationship(
                    source=complaint.id,
                    target=node_id,
                    type=RelationshipType.MENTIONS,
                )
            )
