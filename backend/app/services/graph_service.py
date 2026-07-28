"""
Graph service.

Coordinates graph construction and persistence.
"""

from datetime import datetime
from uuid import UUID

from loguru import logger

from app.graph.builder import GraphBuilder
from app.graph.models import GraphData, GraphPersistenceResult
from app.graph.repository import GraphRepository
from app.schemas.entity_extraction import ExtractedEntities


class GraphService:
    """
    Coordinates graph construction and persistence.
    """

    def __init__(
        self,
        builder: GraphBuilder,
        repository: GraphRepository,
    ) -> None:
        self._builder = builder
        self._repository = repository

    async def build_and_save_graph(
        self,
        complaint_id: UUID,
        created_at: datetime,
        entities: ExtractedEntities,
    ) -> GraphPersistenceResult:
        """
        Build and persist the fraud intelligence graph.

        Args:
            complaint_id:
                Complaint identifier.

            created_at:
                Complaint creation timestamp.

            entities:
                Extracted entities.

        Returns:
            GraphPersistenceResult stats.
        """
        logger.info(
            "Building graph for complaint {}.",
            complaint_id,
        )

        graph: GraphData = self._builder.build(
            complaint_id=complaint_id,
            created_at=created_at,
            entities=entities,
        )

        logger.info(
            "Graph contains {} nodes and {} relationships.",
            len(graph.nodes),
            len(graph.relationships),
        )

        result = await self._repository.save_graph(graph)

        logger.info(
            "Graph persisted successfully.",
        )

        return result
