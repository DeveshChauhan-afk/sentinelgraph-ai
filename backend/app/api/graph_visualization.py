"""
Graph visualization API.

Provides frontend-ready graph data for visualization libraries such as
Cytoscape.js and React Flow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from app.schemas.visualization import GraphResponse
from app.services.visualization.visualization_service import (
    VisualizationService,
)

router = APIRouter(
    prefix="/graph",
    tags=["Graph Visualization"],
)


@router.get(
    "/visualization/{node_id}",
    response_model=GraphResponse,
    summary="Retrieve graph visualization",
)
async def get_graph_visualization(
    node_id: str,
    depth: int = Query(
        default=2,
        ge=1,
        le=5,
        description="Maximum traversal depth.",
    ),
) -> GraphResponse:
    service = VisualizationService()
    """
    Retrieve a graph centered around the given node.
    """
    logger.info(
        "Visualization request received for '{}' (depth={}).",
        node_id,
        depth,
    )

    try:
        graph = await service.get_entity_graph(
            node_id=node_id,
            depth=depth,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if graph.metadata.node_count == 0 and graph.metadata.edge_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No graph found for '{node_id}'.",
        )

    logger.info(
        "Visualization request completed for '{}'.",
        node_id,
    )

    return graph
