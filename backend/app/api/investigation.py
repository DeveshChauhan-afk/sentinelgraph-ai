#app/api/investigations.py
"""
Graph-RAG investigation API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_investigation_service
from app.graph.exceptions import GraphEntityNotFoundError
from app.schemas.investigation import (
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.investigation_service import (
    InvestigationService,
)

router = APIRouter()


@router.post(
    "/",
    response_model=InvestigationResponse,
    summary="Perform an AI-powered fraud investigation",
)
async def investigate(
    request: InvestigationRequest,
    service: Annotated[
        InvestigationService,
        Depends(get_investigation_service),
    ],
) -> InvestigationResponse:
    """
    Perform a Graph-RAG investigation using
    Neo4j evidence and Gemini reasoning.
    """

    try:
        return await service.investigate(request)

    except GraphEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc