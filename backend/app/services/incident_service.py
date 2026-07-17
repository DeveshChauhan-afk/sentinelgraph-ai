"""
Incident Service.

Contains business logic for Incident operations.
Acts as the intermediary between API routes and the repository layer.
"""

from __future__ import annotations

from uuid import UUID

from app.models.enums import IncidentStatus, Priority, ScamCategory
from app.models.incident import Incident
from app.repositories.incident import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate

from app.services.base import BaseService
from app.core.exceptions import (
    DuplicateCaseReferenceError,
    IncidentNotFoundError,
)
from loguru import logger

from app.ai.exceptions import AIError
from app.graph.exceptions import GraphError
from app.graph.service import GraphService
from app.services.entity_extraction_service import (
    EntityExtractionService,
)
from sqlalchemy.ext.asyncio import AsyncSession


class IncidentService(BaseService[IncidentRepository]):
    """
    Service responsible for business operations related to incidents.

    This layer coordinates repository interactions and will later
    incorporate validation, graph synchronization, AI workflows,
    notifications, and audit logging.
    """

    def __init__(
        self,
        repository: IncidentRepository,
        entity_extraction_service: EntityExtractionService,
        session: AsyncSession,
        graph_service: GraphService,
    ) -> None:
        """
        Initialize the IncidentService.

        Args:
            repository:
                Repository for incident persistence.

            entity_extraction_service:
                AI-powered entity extraction service.

            graph_service:
                Fraud graph service.
        """
        super().__init__(repository)
        self._session = session

        self._entity_extraction_service = entity_extraction_service
        self._graph_service = graph_service

    async def _get_required_incident(
        self,
        incident_id: UUID,
    ) -> Incident:
        """
        Retrieve an incident or raise if it does not exist.
        """
        incident = await self._repository.get_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident '{incident_id}' was not found.")

        return incident

    async def create_incident(
        self,
        incident_data: IncidentCreate,
    ) -> Incident:
        """
        Create a new incident.

        The incident is first persisted to PostgreSQL. After the
        transaction succeeds, AI-powered entity extraction and graph
        persistence are executed. Failures in downstream AI processing
        are logged without affecting the successfully created incident.

        Args:
            incident_data:
                Incident creation payload.

        Returns:
            Newly created incident.
        """
        if incident_data.case_reference:
            existing = await self._repository.get_by_case_reference(
                incident_data.case_reference,
            )

            if existing:
                raise DuplicateCaseReferenceError(
                    (
                        "Case reference "
                        f"'{incident_data.case_reference}' "
                        "already exists."
                    )
                )

        logger.info(
            "Creating incident with case reference: {}",
            incident_data.case_reference or "N/A",
        )

        try:
            incident = await self._repository.create(
                incident_data,
            )

            await self._session.commit()

        except Exception:
            await self._session.rollback()
            raise
        await self._session.commit()

        try:
            entities = await self._entity_extraction_service.extract_entities(
                incident.description,
            )

            result = await self._graph_service.build_and_persist(
                complaint_id=incident.id,
                entities=entities,
            )

            logger.info(
                (
                    "Graph persisted for incident '{}' "
                    "(nodes={}, relationships={}, {:.2f} ms)."
                ),
                incident.id,
                result.nodes_persisted,
                result.relationships_persisted,
                result.duration_ms,
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

        return incident

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        """
        Retrieve an incident by its unique identifier.

        Args:
            incident_id: Incident UUID.

        Returns:
            Incident if found, otherwise None.
        """
        return await self._repository.get_by_id(incident_id)

    async def list_incidents(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Retrieve paginated incidents.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            List of incidents.
        """
        return await self._repository.get_all(skip=skip, limit=limit)

    async def update_incident(
        self,
        incident_id: UUID,
        incident_data: IncidentUpdate,
    ) -> Incident:
        """
        Update an existing incident.

        Args:
            incident_id: Incident UUID.
            incident_data: Updated incident data.

        Returns:
            Updated Incident.

        Raises:
            IncidentNotFoundError:
                If the incident does not exist.
        """
        incident = await self._repository.get_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident '{incident_id}' was not found.")
        logger.info(
            "Updating incident: {}",
            incident_id,
        )
        return await self._repository.update(incident, incident_data)

    async def delete_incident(self, incident_id: UUID) -> None:
        """
        Delete an incident.

        Args:
            incident_id: Incident UUID.

        Raises:
            IncidentNotFoundError:
                If the incident does not exist.
        """

        logger.info(
            "Deleting incident: {}",
            incident_id,
        )
        incident = await self._repository.get_by_id(incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident '{incident_id}' was not found.")
        await self._repository.delete(incident)

    async def search_incidents(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Search incidents by keyword.

        Args:
            query: Search keyword.
            skip: Pagination offset.
            limit: Maximum results.

        Returns:
            Matching incidents.
        """
        return await self._repository.search(query, skip=skip, limit=limit)

    async def get_recent_incidents(
        self,
        limit: int = 10,
    ) -> list[Incident]:
        """
        Retrieve the most recently created incidents.

        Args:
            limit: Maximum number of incidents.

        Returns:
            Recent incidents.
        """
        return await self._repository.get_recent(limit=limit)

    async def get_processing_queue(
        self,
        limit: int = 20,
    ) -> list[Incident]:
        """
        Retrieve incidents awaiting processing.

        Args:
            limit: Maximum queue size.

        Returns:
            Processing queue.
        """
        return await self._repository.get_processing_queue(limit=limit)

    async def get_high_risk_incidents(
        self,
        threshold: float = 0.8,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Retrieve high-risk incidents.

        Args:
            threshold: Minimum risk score.
            skip: Pagination offset.
            limit: Maximum results.

        Returns:
            High-risk incidents.
        """
        return await self._repository.get_high_risk(
            threshold=threshold,
            skip=skip,
            limit=limit,
        )

    async def get_incidents_by_status(
        self,
        status: IncidentStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Retrieve incidents filtered by status.
        """
        return await self._repository.get_by_status(
            status=status,
            skip=skip,
            limit=limit,
        )

    async def get_incidents_by_priority(
        self,
        priority: Priority,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Retrieve incidents filtered by priority.
        """
        return await self._repository.get_by_priority(
            priority=priority,
            skip=skip,
            limit=limit,
        )

    async def get_incidents_by_scam_category(
        self,
        category: ScamCategory,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Incident]:
        """
        Retrieve incidents filtered by scam category.
        """
        return await self._repository.get_by_scam_category(
            category=category,
            skip=skip,
            limit=limit,
        )
