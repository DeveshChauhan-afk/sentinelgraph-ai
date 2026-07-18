"""
Graph query API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.api.dependencies import get_graph_query_service
from app.graph.exceptions import GraphEntityNotFoundError
from app.graph.models import GraphNode
from app.graph.query_service import GraphQueryService
from app.graph.query_models import GraphNeighborsResponse
from app.graph.query_models import (
    GraphNeighborsResponse,
    RelatedIncidentsResponse,
    TopRiskEntityResponse,
)
from app.graph.query_models import EntityRiskResponse
from app.graph.query_models import FraudRingResponse
from app.graph.query_models import NetworkSummaryResponse
from app.graph.query_models import PathResponse
from app.graph.query_models import SharedEntityResponse

router = APIRouter()


@router.get(
    "/entity/{value}",
    response_model=GraphNode,
    summary="Retrieve a graph entity",
)
async def get_entity(
    value: str,
    service: Annotated[
        GraphQueryService,
        Depends(get_graph_query_service),
    ],
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
    "/entity/{value}/neighbors",
    response_model=GraphNeighborsResponse,
    summary="Retrieve neighboring graph entities",
)
async def get_neighbors(
    value: str,
    service: Annotated[
        GraphQueryService,
        Depends(get_graph_query_service),
    ],
) -> GraphNeighborsResponse:
    """
    Retrieve an entity together with its directly connected neighbors.
    """
    try:
        return await service.get_neighbors(value)

    except GraphEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.get(
    "/entity/{value}/incidents",
    response_model=RelatedIncidentsResponse,
    summary="Retrieve related incidents",
)
async def get_related_incidents(
    value: str,
    service: Annotated[
        GraphQueryService,
        Depends(get_graph_query_service),
    ],
) -> RelatedIncidentsResponse:
    """
    Retrieve all complaint nodes connected to an entity.
    """
    try:
        return await service.get_related_incidents(value)

    except GraphEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.get(
    "/entity/{value}/risk",
    response_model=EntityRiskResponse,
)
async def get_entity_risk(
    value: str,
    service: GraphQueryService = Depends(get_graph_query_service),
) -> EntityRiskResponse:
    """
    Retrieve risk assessment for a graph entity.
    """
    return await service.get_entity_risk(value)

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

@router.get(
    "/network/summary",
    response_model=NetworkSummaryResponse,
)
async def get_network_summary(
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> NetworkSummaryResponse:
    """
    Retrieve graph-wide statistics.
    """

    return await service.get_network_summary()

@router.get(
    "/network/top-risk",
    response_model=list[TopRiskEntityResponse],
)
async def get_top_risk_entities(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> list[TopRiskEntityResponse]:
    """
    Retrieve the highest-risk entities in the graph.
    """

    return await service.get_top_risk_entities(limit)

@router.get(
    "/path",
    response_model=PathResponse,
)
async def get_shortest_path(
    source: str,
    target: str,
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> PathResponse:
    """
    Find the shortest path between two graph entities.
    """

    return await service.get_shortest_path(
        source,
        target,
    )

@router.get(
    "/entity/{value}/shared",
    response_model=SharedEntityResponse,
)
async def get_shared_entity(
    value: str,
    service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
) -> SharedEntityResponse:
    """
    Find all complaints sharing the specified entity.
    """

    return await service.get_shared_entity(
        value,
    )

