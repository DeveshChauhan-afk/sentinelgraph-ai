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
from app.services.investigation.prompt_builder import PromptBuilder
from app.services.investigation.report_parser import ReportParser
from app.services.investigation.cache import investigation_cache
from app.services.investigation.performance import (
    InvestigationTimer,
)



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
        self._cache = investigation_cache

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

        timer = InvestigationTimer()
        logger.info(
            "Starting investigation for '{}'.",
            request.target_value,
        )

        # ------------------------------------------------------------------
        # Check cache first
        # ------------------------------------------------------------------
        cache_key = (
            f"{request.target_type.value}:{request.target_value.strip().lower()}"
        )

        timer.start("Cache")
        cached_response = self._cache.get(cache_key)
        timer.stop("Cache")

        if cached_response is not None:
            logger.info(
                "Returning cached investigation for '{}'.",
                cache_key,
            )
            timer.summary()
            return cached_response

        # ------------------------------------------------------------------
        # Build evidence
        # ------------------------------------------------------------------
        timer.start("Graph Queries")
        evidence = await self.build_evidence(
            request,
        )
        timer.stop("Graph Queries")

        # ------------------------------------------------------------------
        # Build prompt
        # ------------------------------------------------------------------
        timer.start("Prompt")
        prompt = self._prompt_builder.build(
            evidence,
        )
        timer.stop("Prompt")

        # ------------------------------------------------------------------
        # Query Gemini
        # ------------------------------------------------------------------
        timer.start("Gemini")
        raw_response = await self._ai_client.generate_content(
            prompt,
        )
        timer.stop("Gemini")

        logger.debug(    
            "RAW GEMINI RESPONSE:\n{}",
            raw_response,
        )

        # ------------------------------------------------------------------
        # Parse report
        # ------------------------------------------------------------------
        timer.start("Parser")
        report = self._report_parser.parse(
            raw_response,
        )
        timer.stop("Parser")

        logger.info(
            "Investigation complete | Risk={} | Confidence={} | Findings={}",
            report.risk_level,
            report.confidence,
            len(report.findings),
        )

        logger.info(
            "Investigation completed for '{}'.",
            request.target_value,
        )

        logger.info(
            "Creating InvestigationResponse: target_type={} target_value={}",
            request.target_type,
            request.target_value,
        )

        response = InvestigationResponse(
            target_type=request.target_type,
            target_value=request.target_value,
            evidence=evidence,
            report=report,
        )

        # ------------------------------------------------------------------
        # Store in cache
        # ------------------------------------------------------------------
        self._cache.set(
            cache_key,
            response,
        )
        timer.summary()
        return response
