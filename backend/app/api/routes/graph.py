"""
Graph query API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_graph_query_service
from app.graph.exceptions import GraphEntityNotFoundError
from app.graph.models import GraphNode
from app.graph.query_service import GraphQueryService
from app.graph.query_models import FraudRingResponse

router = APIRouter(
    prefix="/graph",
    tags=["Graph"],
)


@router.get(
    "/entity/{value}",
    response_model=GraphNode,
    summary="Retrieve a graph entity",
)
async def get_entity(
    value: str,
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> GraphNode:
    """
    Retrieve a graph entity by its value.
    """
    try:
        return await service.get_entity(value)

    except GraphEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/entity/{value}/ring",
    response_model=FraudRingResponse,
)
async def get_fraud_ring(
    value: str,
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> FraudRingResponse:
    """
    Retrieve the connected fraud ring for an entity.
    """
    return await service.get_fraud_ring(value)
