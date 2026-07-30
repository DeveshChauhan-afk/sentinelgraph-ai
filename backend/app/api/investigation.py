# app/api/investigations.py
"""
Graph-RAG investigation & report generation API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_investigation_report_service,
    get_investigation_service,
)
from app.exceptions.investigation import (
    InvalidReportSchemaError,
    LLMProviderError,
    LLMTimeoutError,
    PromptValidationError,
    ReportParsingError,
)
from app.graph.exceptions import GraphEntityNotFoundError
from app.schemas.investigation import (
    InvestigationRequest,
    InvestigationResponse,
)
from app.schemas.report import ProfessionalInvestigationReport
from app.services.investigation_report_service import InvestigationReportService
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


@router.post(
    "/report",
    response_model=ProfessionalInvestigationReport,
    summary="Generate a professional structured investigation report",
)
async def generate_report(
    request: InvestigationRequest,
    report_service: Annotated[
        InvestigationReportService,
        Depends(get_investigation_report_service),
    ],
) -> ProfessionalInvestigationReport:
    """
    Generate an end-to-end validated ProfessionalInvestigationReport.
    Pipeline: InvestigationSummary -> ReportContext -> PromptRequest -> LLM -> ReportParser.
    """
    try:
        return await report_service.generate_report(
            entity_value=request.target_value,
            target_type=request.target_type.value if hasattr(request.target_type, "value") else str(request.target_type),
        )
    except GraphEntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (PromptValidationError, InvalidReportSchemaError, ReportParsingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Report Generation Error: {exc.message}",
        ) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM Provider Timeout: {exc.message}",
        ) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM Provider Error: {exc.message}",
        ) from exc
