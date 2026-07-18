"""
Graph-RAG investigation service.

Coordinates graph retrieval before passing evidence to the
LLM reasoning layer.
"""

from __future__ import annotations

from loguru import logger

from app.graph.query_service import GraphQueryService
from app.schemas.investigation import (
    InvestigationEvidence,
    InvestigationRequest,
    InvestigationResponse,
)
from app.ai.client import GeminiClient
from app.graph.query_service import GraphQueryService
from app.schemas.investigation import (
    InvestigationEvidence,
    InvestigationReport,
    InvestigationRequest,
    InvestigationResponse,
)
from app.services.investigation.prompt_builder import PromptBuilder
from app.services.investigation.report_parser import ReportParser



class InvestigationService:
    """
    Service responsible for collecting graph evidence for an
    investigation.
    """

    def __init__(
        self,
        graph_service: GraphQueryService,
        ai_client: GeminiClient,
        prompt_builder: PromptBuilder,
        report_parser: ReportParser,
    ) -> None:
        """
        Initialize InvestigationService.
        """

        self._graph_service = graph_service
        self._ai_client = ai_client
        self._prompt_builder = prompt_builder
        self._report_parser = report_parser

    async def build_evidence(
        self,
        request: InvestigationRequest,
    ) -> InvestigationEvidence:
        """
        Collect all graph evidence required for an investigation.

        Args:
            request:
                Investigation request.

        Returns:
            InvestigationEvidence containing the complete graph context.
        """

        logger.info(
            "Building investigation evidence for '{}'.",
            request.target_value,
        )

        neighbors = await self._graph_service.get_neighbors(
            request.target_value,
        )

        related_incidents = (
            await self._graph_service.get_related_incidents(
                request.target_value,
            )
        )

        risk = await self._graph_service.get_entity_risk(
            request.target_value,
        )

        fraud_ring = await self._graph_service.get_fraud_ring(
            request.target_value,
        )

        shared_entities = (
            await self._graph_service.get_shared_entity(
                request.target_value,
            )
        )

        logger.info(
            "Successfully collected investigation evidence for '{}'.",
            request.target_value,
        )

        return InvestigationEvidence(
            neighbors=neighbors,
            related_incidents=related_incidents,
            risk=risk,
            fraud_ring=fraud_ring,
            shared_entities=shared_entities,
        )
    
    async def investigate(
        self,
        request: InvestigationRequest,
    ) -> InvestigationResponse:
        """
        Perform a complete Graph-RAG investigation.
        """

        logger.info(
            "Starting investigation for '{}'.",
            request.target_value,
        )

        evidence = await self.build_evidence(
            request,
        )

        prompt = self._prompt_builder.build(
            evidence,
        )

        raw_response = await self._ai_client.generate_content(
            prompt,
        )

        report = self._report_parser.parse(
            raw_response,
        )

        logger.info(
            "Investigation completed for '{}'.",
            request.target_value,
        )

        return InvestigationResponse(
            target=request.target_value,
            evidence=evidence,
            report=report,
        )