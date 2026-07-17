"""
Graph query service.

Contains business logic for querying the fraud intelligence graph.
Acts as the intermediary between API routes and the graph repository.
"""

from __future__ import annotations

from loguru import logger

from app.graph.exceptions import GraphEntityNotFoundError
from app.graph.models import GraphNode
from app.graph.repository import GraphRepository
from app.graph.query_models import GraphNeighborsResponse
from app.graph.query_models import RelatedIncidentsResponse

from app.graph.query_models import (
    GraphNeighborsResponse,
    RelatedIncidentsResponse,
)

from app.graph.query_models import (
    RiskMetrics,
    EntityRiskResponse,
)
from app.graph.query_models import FraudRingResponse

class GraphQueryService:
    """
    Service responsible for graph query operations.

    This layer coordinates graph repository interactions and
    encapsulates graph-specific business logic.
    """

    def __init__(
        self,
        repository: GraphRepository,
    ) -> None:
        """
        Initialize the GraphQueryService.

        Args:
            repository:
                Graph repository for Neo4j queries.
        """
        self._repository = repository

    async def get_entity(
        self,
        value: str,
    ) -> GraphNode:
        """
        Retrieve a graph entity by its value.

        Args:
            value:
                Entity value (phone number, UPI ID, email, etc.).

        Returns:
            Matching graph node.

        Raises:
            EntityNotFoundError:
                If no matching entity exists.
        """
        logger.info(
            "Retrieving graph entity '{}'.",
            value,
        )

        entity = await self._repository.find_entity(value)

        if entity is None:
            logger.warning(
                "Graph entity '{}' was not found.",
                value,
            )

            raise GraphEntityNotFoundError(
                f"Graph entity '{value}' was not found.",
            )

        return entity
    
    async def get_neighbors(
        self,
        value: str,
    ) -> GraphNeighborsResponse:
        """
        Retrieve an entity and all directly connected neighbors.

        Args:
            value:
                Entity value (phone number, UPI ID, email, etc.).

        Returns:
            Entity and its neighboring graph nodes.

        Raises:
            GraphEntityNotFoundError:
                If the entity does not exist.
        """
        logger.info(
            "Retrieving neighbors for graph entity '{}'.",
            value,
        )

        result = await self._repository.find_neighbors(value)

        if result is None:
            logger.warning(
                "Graph entity '{}' was not found.",
                value,
            )

            raise GraphEntityNotFoundError(
                f"Graph entity '{value}' was not found.",
            )

        return GraphNeighborsResponse(
            entity=result.entity,
            neighbors=result.neighbors,
        )
    
    async def get_related_incidents(
        self,
        value: str,
    ) -> RelatedIncidentsResponse:
        """
    Retrieve all complaints connected to an entity.

    Args:
        value:
            Entity value.

    Returns:
        Entity together with its related complaint nodes.

    Raises:
        GraphEntityNotFoundError:
            If the entity does not exist.
    """
        logger.info(
            "Retrieving related incidents for graph entity '{}'.",
            value,
        )

        result = await self._repository.find_related_incidents(
            value,
        )

        if result is None:
            logger.warning(
                "Graph entity '{}' was not found.",
                value,
            )

            raise GraphEntityNotFoundError(
                f"Graph entity '{value}' was not found.",
            )

        return RelatedIncidentsResponse(
            entity=result.entity,
            incidents=result.incidents,
        )
    
    async def get_entity_risk(
    self,
    value: str,
    ) -> EntityRiskResponse:
        """
    Retrieve risk assessment for a graph entity.

    Args:
        value:
            Entity value.

    Returns:
        EntityRiskResponse.

    Raises:
        GraphEntityNotFoundError:
            If the entity does not exist.
        """
        logger.info(
            "Calculating risk for graph entity '{}'.",
            value,
        )

        result = await self._repository.get_risk_metrics(
            value,
        )

        if result is None:
            logger.warning(
                "Graph entity '{}' was not found.",
                value,
            )

            raise GraphEntityNotFoundError(
                f"Graph entity '{value}' was not found.",
            )

        score = 0
        reasons: list[str] = []

        if result.incident_count > 0:
            score += min(result.incident_count * 25, 50)
            reasons.append(
                f"Linked to {result.incident_count} complaint(s)."
            )

        if result.neighbor_count > 3:
            score += 20
            reasons.append(
                "Connected to multiple entities."
            )

        if result.phone_count > 1:
            score += 10
            reasons.append(
                "Associated with multiple phone numbers."
            )

        if result.upi_count > 1:
            score += 10
            reasons.append(
                "Associated with multiple UPI IDs."
            )

        if result.email_count > 1:
            score += 5
            reasons.append(
                "Associated with multiple email addresses."
            )

        if result.organization_count > 1:
            score += 5
            reasons.append(
                "Associated with multiple organizations."
            )

        score = min(score, 100)

        if score >= 70:
            level = "HIGH"

        elif score >= 40:
            level = "MEDIUM"

        else:
            level = "LOW"

        return EntityRiskResponse(
            entity=result.entity,
            risk_score=score,
            risk_level=level,
            metrics=RiskMetrics(
                incident_count=result.incident_count,
                neighbor_count=result.neighbor_count,
                phone_count=result.phone_count,
                upi_count=result.upi_count,
                email_count=result.email_count,
                organization_count=result.organization_count,
            ),
            reasons=reasons,
        )
    
    async def get_fraud_ring(
        self,
        value: str,
    ) -> FraudRingResponse:
        """
        Retrieve the connected fraud ring for an entity.

        Args:
            value:
                Entity value.

        Returns:
            FraudRingResponse.

        Raises:
            GraphEntityNotFoundError:
                If the entity does not exist.
        """
        logger.info(
            "Retrieving fraud ring for '{}'.",
            value,
        )

        result = await self._repository.find_fraud_ring(
            value,
        )

        if result is None:
            logger.warning(
                "Graph entity '{}' was not found.",
                value,
            )

            raise GraphEntityNotFoundError(
                f"Graph entity '{value}' was not found.",
            )

        return FraudRingResponse(
            entity=result.entity,
            nodes=result.nodes,
            incidents=result.incidents,
            total_nodes=len(result.nodes),
            total_incidents=len(result.incidents),
        )