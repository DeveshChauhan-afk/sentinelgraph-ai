"""
Incident Processing Service.

Coordinates AI-powered processing workflows for newly created
incidents.

This service orchestrates entity extraction, graph construction,
graph persistence, and future AI workflows while keeping the
IncidentService focused on business operations.
"""

from __future__ import annotations

from loguru import logger

from app.ai.exceptions import AIError
from app.graph.exceptions import GraphError
from app.graph.service import GraphService
from app.models.incident import Incident
from app.services.entity_extraction_service import (
    EntityExtractionService,
)


class IncidentProcessingService:
    """
    Coordinates post-persistence AI processing for incidents.

    Responsibilities:

    - Entity extraction
    - Graph creation
    - Graph persistence

    Future responsibilities:

    - Risk scoring
    - Fraud classification
    - Timeline generation
    - Notification dispatch
    """

    def __init__(
        self,
        entity_extraction_service: EntityExtractionService,
        graph_service: GraphService,
    ) -> None:
        """
        Initialize the processing service.

        Args:
            entity_extraction_service:
                AI entity extraction service.

            graph_service:
                Fraud graph service.
        """
        self._entity_extraction_service = (
            entity_extraction_service
        )
        self._graph_service = graph_service

    async def process_incident(
        self,
        incident: Incident,
    ) -> None:
        """
        Execute the AI processing pipeline.

        The incident has already been committed to PostgreSQL.
        Failures in downstream AI processing are logged without
        affecting the transactional source of truth.

        Args:
            incident:
                Persisted incident.
        """
        logger.info(
            "Starting AI processing pipeline for incident '{}'.",
            incident.id,
        )
        try:
            entities = (
                await self._entity_extraction_service.extract_entities(
                    incident.description,
                )
            )

            logger.info(
                "Successfully extracted {} entities for incident '{}'.",
                sum(
                    (
                        len(entities.phone_numbers),
                        len(entities.upi_ids),
                        len(entities.emails),
                        len(entities.urls),
                        len(entities.bank_accounts),
                        len(entities.organizations),
                        len(entities.persons),
                        len(entities.locations),
                    )
                ),
                incident.id,
            )

            await self._graph_service.build_and_persist(
                complaint_id=incident.id,
                entities=entities,
            )

            logger.success(
                "AI processing pipeline completed for incident '{}'.",
                incident.id,
            )

        except AIError:
            logger.exception(
                "Entity extraction failed for incident '{}'.",
                incident.id,
            )

        except GraphError:
            logger.exception(
                "Graph persistence failed for incident '{}'.",
                incident.id,
            )