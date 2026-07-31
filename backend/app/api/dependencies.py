# app/api/dependencies.py
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
from app.services.investigation.prompt_builder import PromptBuilder
from app.services.investigation.report_parser import ReportParser
from app.services.investigation_service import InvestigationService
from app.services.entity_analysis_service import EntityAnalysisService
from app.services.timeline_analysis_service import TimelineAnalysisService
from app.services.fraud_evolution_service import FraudEvolutionService
from app.services.evidence_engine import EvidenceEngine
from app.services.timeline_service import TimelineService
from app.services.investigation_summary_service import (
        InvestigationSummaryService,
    )
from app.services.report_context_builder import ReportContextBuilder
from app.services.investigation_report_service import (
        InvestigationReportService,
    )
from app.ai.llm_client import LLMClient

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


def get_prompt_builder() -> PromptBuilder:
    """
    Return the Graph-RAG prompt builder.
    """
    return PromptBuilder()


def get_report_parser() -> ReportParser:
    """
    Return the Graph-RAG report parser.
    """
    return ReportParser()


def get_investigation_service(
    graph_service: GraphQueryService = Depends(
        get_graph_query_service,
    ),
    ai_client: GeminiClient = Depends(
        get_ai_client,
    ),
    prompt_builder: PromptBuilder = Depends(
        get_prompt_builder,
    ),
    report_parser: ReportParser = Depends(
        get_report_parser,
    ),
) -> InvestigationService:
    """
    Return the investigation service.
    """
    return InvestigationService(
        graph_service=graph_service,
        ai_client=ai_client,
        prompt_builder=prompt_builder,
        report_parser=report_parser,
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


def get_entity_analysis_service() -> EntityAnalysisService:
    """
    Return the entity analysis service.
    """

    return EntityAnalysisService()


def get_timeline_analysis_service() -> TimelineAnalysisService:
    """
    Return the timeline analysis service.
    """
    

    return TimelineAnalysisService()


def get_fraud_evolution_service() -> FraudEvolutionService:
    """
    Return the fraud evolution service.
    """
    

    return FraudEvolutionService()


def get_evidence_engine() -> EvidenceEngine:
    """
    Return the evidence engine.
    """
    

    return EvidenceEngine()


def get_timeline_service(
    repository: GraphRepository = Depends(
        get_graph_repository,
    ),
    entity_analysis_service: EntityAnalysisService = Depends(
        get_entity_analysis_service,
    ),
    timeline_analysis_service: TimelineAnalysisService = Depends(
        get_timeline_analysis_service,
    ),
    fraud_evolution_service: FraudEvolutionService = Depends(
        get_fraud_evolution_service,
    ),
    evidence_engine: EvidenceEngine = Depends(
        get_evidence_engine,
    ),
) -> TimelineService:
    """
    Return the timeline service.
    """
    

    return TimelineService(
        repository=repository,
        entity_analysis_service=entity_analysis_service,
        timeline_analysis_service=timeline_analysis_service,
        fraud_evolution_service=fraud_evolution_service,
        evidence_engine=evidence_engine,
    )


def get_investigation_summary_service(
    timeline_service: TimelineService = Depends(
        get_timeline_service,
    ),
    entity_analysis_service: EntityAnalysisService = Depends(
        get_entity_analysis_service,
    ),
    timeline_analysis_service: TimelineAnalysisService = Depends(
        get_timeline_analysis_service,
    ),
    fraud_evolution_service: FraudEvolutionService = Depends(
        get_fraud_evolution_service,
    ),
    evidence_engine: EvidenceEngine = Depends(
        get_evidence_engine,
    ),
) -> InvestigationSummaryService:
    """
    Return the investigation summary service.
    """
    

    return InvestigationSummaryService(
        timeline_service=timeline_service,
        entity_analysis_service=entity_analysis_service,
        timeline_analysis_service=timeline_analysis_service,
        fraud_evolution_service=fraud_evolution_service,
        evidence_engine=evidence_engine,
    )


def get_report_context_builder() -> ReportContextBuilder:
    """
    Return the ReportContextBuilder service.
    """
    

    return ReportContextBuilder()


def get_llm_client(
    ai_client: GeminiClient = Depends(get_ai_client),
) -> LLMClient:
    """
    Return the application LLMClient provider instance.
    """
    return ai_client


def get_investigation_report_service(
    summary_service: InvestigationSummaryService = Depends(
        get_investigation_summary_service,
    ),
    context_builder: ReportContextBuilder = Depends(
        get_report_context_builder,
    ),
    prompt_builder: PromptBuilder = Depends(
        get_prompt_builder,
    ),
    llm_client: LLMClient = Depends(
        get_llm_client,
    ),
    report_parser: ReportParser = Depends(
        get_report_parser,
    ),
) -> InvestigationReportService:
    """
    Return the investigation report orchestration service.
    """
    

    return InvestigationReportService(
        summary_service=summary_service,
        context_builder=context_builder,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
        report_parser=report_parser,
    )







