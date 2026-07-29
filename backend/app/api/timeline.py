"""
Timeline Reconstruction Engine temporary validation API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_timeline_service
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import TimelineService

router = APIRouter()


@router.get(
    "/{entity_value}",
    response_model=TimelineResponse,
    summary="Reconstruct chronological timeline for an entity",
    description="Validation endpoint for Timeline Reconstruction Engine Phase 1.",
)
async def get_timeline(
    entity_value: str,
    service: Annotated[
        TimelineService,
        Depends(get_timeline_service),
    ],
) -> TimelineResponse:
    """
    Reconstruct chronological timeline of connected complaints for a target entity.
    """
    return await service.build_timeline(entity_value)
