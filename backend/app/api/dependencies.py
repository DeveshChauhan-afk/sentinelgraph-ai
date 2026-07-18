"""
Application dependency providers.

This module acts as the composition root for the FastAPI application.
It wires together repositories, services, AI clients, and graph
components using FastAPI's dependency injection system.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import GeminiClient
from app.core.config import settings
from app.db.database import get_db
from app.graph.repository import GraphRepository
from app.graph.service import GraphService
from app.repositories.incident import IncidentRepository
from app.services.entity_extraction_service import (
    EntityExtractionService,
)
from app.services.incident_service import IncidentService
from app.graph.query_service import GraphQueryService


def get_ai_client() -> GeminiClient:
    """
    Return the application's Gemini AI client.
    """
    return GeminiClient(settings)


def get_entity_extraction_service(
    ai_client: GeminiClient = Depends(get_ai_client),
) -> EntityExtractionService:
    """
    Return the entity extraction service.
    """
    return EntityExtractionService(
        ai_client=ai_client,
    )


def get_graph_repository() -> GraphRepository:
    """
    Return the graph repository.
    """
    return GraphRepository()


def get_graph_service(
    repository: GraphRepository = Depends(
        get_graph_repository,
    ),
) -> GraphService:
    """
    Return the graph service.
    """
    return GraphService(
        repository=repository,
    )


def get_graph_query_service(
    repository: GraphRepository = Depends(
        get_graph_repository,
    ),
) -> GraphQueryService:
    """
    Return the graph query service.
    """
    return GraphQueryService(
        repository=repository,
    )


def get_incident_repository(
    session: AsyncSession = Depends(get_db),
) -> IncidentRepository:
    """
    Return the incident repository.
    """
    return IncidentRepository(
        session=session,
    )


def get_incident_service(
    session: AsyncSession = Depends(get_db),
    repository: IncidentRepository = Depends(
        get_incident_repository,
    ),
    entity_extraction_service: EntityExtractionService = Depends(
        get_entity_extraction_service,
    ),
    graph_service: GraphService = Depends(
        get_graph_service,
    ),
) -> IncidentService:
    """
    Return the incident service.
    """
    return IncidentService(
        repository=repository,
        session=session,
        entity_extraction_service=entity_extraction_service,
        graph_service=graph_service,
    )
