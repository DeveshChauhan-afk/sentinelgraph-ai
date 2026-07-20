"""
Service layer for graph analytics.

Coordinates analytics requests between the API layer and the graph repository.
"""

from __future__ import annotations

from loguru import logger

from app.graph.repository import GraphRepository
from app.schemas.analytics import (
    GraphSummary,
    TopConnectedEntity,
    SharedEntityAnalysis,
)


class AnalyticsService:
    """
    Provides high-level graph analytics operations.
    """

    def __init__(
        self,
        repository: GraphRepository | None = None,
    ) -> None:
        self._repository = repository or GraphRepository()

    async def get_graph_summary(
        self,
    ) -> GraphSummary:
        """
        Retrieve graph-wide summary statistics.
        """
        logger.info(
            "Generating graph summary analytics."
        )

        summary = await self._repository.get_graph_summary()

        logger.info(
            "Graph summary generated successfully."
        )

        return summary

    async def get_top_connected_entities(
        self,
        limit: int = 10,
    ) -> list[TopConnectedEntity]:
        """
        Retrieve the most connected entities in the graph.

        Args:
            limit:
                Maximum number of entities to return.

        Returns:
            Ranked list of connected entities.
        """
        logger.info(
            "Generating top connected entities (limit={}).",
            limit,
        )

        entities = await self._repository.get_top_connected_entities(
            limit=limit,
        )

        logger.info(
            "Generated {} top connected entities.",
            len(entities),
        )

        return entities
    
    async def get_shared_entities(
        self,
        minimum_complaints: int = 2,
    ) -> list[SharedEntityAnalysis]:
        """
        Retrieve entities shared across multiple complaints.
        """
        logger.info(
            "Generating shared entity analysis (minimum_complaints={}).",
            minimum_complaints,
        )

        entities = await self._repository.get_shared_entities(
            minimum_complaints=minimum_complaints,
        )

        logger.info(
            "Generated {} shared entities.",
            len(entities),
        )

        return entities