"""
Visualization service.

Coordinates graph retrieval and mapping for visualization APIs.
"""

from __future__ import annotations

from loguru import logger

from app.graph.repository import GraphRepository
from app.schemas.visualization import GraphResponse
from app.services.visualization.visualization_mapper import (
    VisualizationMapper,
)


class VisualizationService:
    """
    Service responsible for graph visualization.
    """

    MIN_DEPTH = 1
    MAX_DEPTH = 5

    def __init__(
        self,
        repository: GraphRepository | None = None,
        mapper: VisualizationMapper | None = None,
    ) -> None:
        self._repository = repository or GraphRepository()
        self._mapper = mapper or VisualizationMapper()

    async def get_entity_graph(
        self,
        node_id: str,
        depth: int = 2,
    ) -> GraphResponse:
        """
        Retrieve a visualization graph centered on a graph node.
        """
        if depth < self.MIN_DEPTH or depth > self.MAX_DEPTH:
            raise ValueError(
                f"Depth must be between " f"{self.MIN_DEPTH} and {self.MAX_DEPTH}."
            )

        logger.info(
            "Generating visualization graph for '{}' (depth={}).",
            node_id,
            depth,
        )

        paths = await self._repository.get_subgraph(
            node_id=node_id,
            depth=depth,
        )

        if not paths:
            logger.warning(
                "No graph found for node '{}'.",
                node_id,
            )

        response = self._mapper.map_paths(
            paths=paths,
            depth=depth,
        )

        logger.info(
            "Visualization graph generated ({} nodes, {} edges).",
            response.metadata.node_count,
            response.metadata.edge_count,
        )

        return response
