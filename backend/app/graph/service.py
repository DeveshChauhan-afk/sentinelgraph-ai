"""
Graph service.

Coordinates graph construction and persistence for the
Fraud Intelligence Graph.
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger

from app.graph.builder import GraphBuilder
from app.graph.models import GraphPersistenceResult
from app.graph.repository import GraphRepository
from app.schemas.entity_extraction import ExtractedEntities


class GraphService:
    """
    Coordinates graph creation and persistence.

    The service orchestrates the graph builder and repository while
    keeping business logic outside the persistence layer.
    """

    def __init__(
        self,
        builder: GraphBuilder,
        repository: GraphRepository,
    ) -> None:
        """
        Initialize the graph service.

        Args:
            builder:
                Graph builder.

            repository:
                Graph repository.
        """
        self._builder = builder
        self._repository = repository

    async def build_and_persist(
        self,
        complaint_id: UUID,
        entities: ExtractedEntities,
    ) -> GraphPersistenceResult:
        """
        Build and persist a fraud intelligence graph.

        Args:
            complaint_id:
                Complaint identifier.

            entities:
                Extracted entities from the AI pipeline.

        Returns:
            Graph persistence statistics.
        """
        logger.info(
            "Building fraud intelligence graph for complaint '{}'.",
            complaint_id,
        )

        graph = self._builder.build(
            complaint_id=complaint_id,
            entities=entities,
        )
        logger.debug(
            "Graph built successfully "
            "(nodes={}, relationships={}).",
            len(graph.nodes),
            len(graph.relationships),
        )

        result = await self._repository.save_graph(
            graph,
        )

        logger.success(
            "Fraud intelligence graph persisted "
            "for complaint '{}' "
            "(nodes={}, relationships={}, {:.2f} ms).",
            complaint_id,
            result.nodes_persisted,
            result.relationships_persisted,
            result.duration_ms,
        )

        return result