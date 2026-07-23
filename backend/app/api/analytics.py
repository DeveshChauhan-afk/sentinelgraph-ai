"""
Graph analytics API endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.schemas.analytics import GraphSummary
from app.services.analytics.analytics_service import AnalyticsService
from app.schemas.analytics import TopConnectedEntity, SharedEntityAnalysis
from fastapi import Query

router = APIRouter(
    prefix="/analytics",
    tags=["Graph Analytics"],
)


@router.get(
    "/summary",
    response_model=GraphSummary,
    summary="Get graph summary",
)
async def get_graph_summary() -> GraphSummary:
    """
    Retrieve overall statistics for the fraud intelligence graph.
    """
    logger.info("Graph summary request received.")

    service = AnalyticsService()

    try:
        summary = await service.get_graph_summary()

        logger.info("Graph summary returned successfully.")

        return summary

    except Exception:
        logger.exception("Failed to retrieve graph summary.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve graph summary.",
        )


@router.get(
    "/top-connected",
    response_model=list[TopConnectedEntity],
    summary="Get top connected entities",
)
async def get_top_connected_entities(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of entities to return.",
    ),
) -> list[TopConnectedEntity]:
    """
    Retrieve the most connected entities in the fraud graph.
    """
    logger.info(
        "Top connected entities request received (limit={}).",
        limit,
    )

    service = AnalyticsService()

    try:
        entities = await service.get_top_connected_entities(
            limit=limit,
        )

        logger.info(
            "Returned {} top connected entities.",
            len(entities),
        )

        return entities

    except Exception:
        logger.exception(
            "Failed to retrieve top connected entities.",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top connected entities.",
        )


@router.get(
    "/shared-entities",
    response_model=list[SharedEntityAnalysis],
    summary="Get shared entities",
)
async def get_shared_entities(
    minimum_complaints: int = Query(
        default=2,
        ge=2,
        description="Minimum number of complaints sharing an entity.",
    ),
) -> list[SharedEntityAnalysis]:
    """
    Retrieve entities shared across multiple complaints.
    """
    logger.info(
        "Shared entity analysis request received (minimum_complaints={}).",
        minimum_complaints,
    )

    service = AnalyticsService()

    try:
        entities = await service.get_shared_entities(
            minimum_complaints=minimum_complaints,
        )

        logger.info(
            "Returned {} shared entities.",
            len(entities),
        )

        return entities

    except Exception:
        logger.exception(
            "Failed to retrieve shared entity analysis.",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shared entity analysis.",
        )
