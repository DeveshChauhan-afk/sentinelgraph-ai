"""
Dependency providers for the service layer.
"""

from __future__ import annotations

from fastapi import Depends

from app.ai.dependencies import (
    get_entity_extraction_service,
)
from app.graph.dependencies import (
    get_graph_service,
)
from app.repositories.dependencies import (
    get_incident_repository,
)
from app.services.entity_extraction_service import (
    EntityExtractionService,
)
from app.services.incident_processing_service import (
    IncidentProcessingService,
)
from app.services.incident_service import (
    IncidentService,
)
from app.graph.service import GraphService
from app.repositories.incident import IncidentRepository


def get_incident_processing_service(
    entity_extraction_service: EntityExtractionService = Depends(
        get_entity_extraction_service,
    ),
    graph_service: GraphService = Depends(
        get_graph_service,
    ),
) -> IncidentProcessingService:
    """
    Return an IncidentProcessingService.
    """
    return IncidentProcessingService(
        entity_extraction_service=entity_extraction_service,
        graph_service=graph_service,
    )


def get_incident_service(
    repository: IncidentRepository = Depends(
        get_incident_repository,
    ),
    processing_service: IncidentProcessingService = Depends(
        get_incident_processing_service,
    ),
) -> IncidentService:
    """
    Return an IncidentService.
    """
    return IncidentService(
        repository=repository,
        processing_service=processing_service,
    )