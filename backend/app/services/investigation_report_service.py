#app/services/investigation_report_service.py
"""
InvestigationReportService Orchestration Layer (Sprint 9 Phase 4.7).

Coordinates end-to-end report generation pipeline from deterministic investigation
summarization to report context building, prompt assembly, LLM client generation,
and structured response parsing.
"""

from __future__ import annotations

from uuid import uuid4
from loguru import logger

from app.ai.llm_client import LLMClient
from app.schemas.report import ProfessionalInvestigationReport
from app.services.investigation.report_parser import ReportParser
from app.services.investigation_summary_service import InvestigationSummaryService
from app.services.prompt_builder import PromptBuilder
from app.services.report_context_builder import ReportContextBuilder


class InvestigationReportService:
    """
    Orchestration service for generating structured professional investigation reports.
    """

    def __init__(

        self,
        summary_service: InvestigationSummaryService,
        context_builder: ReportContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
        report_parser: ReportParser | None = None,
    ) -> None:
        """
        Initialize InvestigationReportService with dependency injection.

        Args:
            summary_service: Service constructing canonical InvestigationSummary objects.
            context_builder: Service constructing token-optimized ReportContext view models.
            prompt_builder: Service building PromptRequest objects.
            llm_client: LLMClient provider implementation.
            report_parser: Parser parsing LLM JSON completions into ProfessionalInvestigationReport.
        """
        self._summary_service = summary_service
        self._context_builder = context_builder or ReportContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client
        self._report_parser = report_parser or ReportParser()

    async def generate_report(
        self,
        entity_value: str,
        target_type: str | None = None,
        template_id: str = "EXECUTIVE_INVESTIGATION_REPORT",
    ) -> ProfessionalInvestigationReport:
        """
        Generate a validated, immutable ProfessionalInvestigationReport for a target entity.

        Args:
            entity_value: Target identifier (phone, email, upi, complaint_id, etc.).
            target_type: Optional target entity type classification.
            template_id: Template identifier for report style (e.g. EXECUTIVE_INVESTIGATION_REPORT).

        Returns:
            Validated immutable ProfessionalInvestigationReport with execution telemetry.
        """
        correlation_id = f"CORR-{uuid4().hex[:10].upper()}"

        logger.info(
            "Starting end-to-end report generation (correlation_id='{}', template_id='{}', target_type={}).",
            correlation_id,
            template_id,
            target_type or "unspecified",
        )

        if self._llm_client is None:
            raise ValueError("LLMClient dependency is required for generate_report execution.")

        # Step 1: Build Canonical InvestigationSummary
        summary = await self._summary_service.build_summary(
            entity_value=entity_value,
            target_type=target_type,
        )

        # Step 2: Build Report Context (Token-optimized view model)
        report_context = self._context_builder.build_report_context(summary)

        # Step 3: Build PromptRequest (Deterministic prompt assembly)
        prompt_request = self._prompt_builder.build_prompt_request(
            report_context=report_context,
            template_id=template_id,
        )

        # Step 4: Execute LLM Completion
        llm_response = await self._llm_client.generate(prompt_request)

        # Step 5: Parse and Validate Response JSON
        report = self._report_parser.parse_report(
            llm_response=llm_response,
            prompt_request=prompt_request,
            correlation_id=correlation_id,
        )

        logger.info(
            "Completed end-to-end report generation: report_id='{}', correlation_id='{}', latency={:.2f}ms.",
            report.report_id,
            correlation_id,
            report.telemetry.latency_ms,
        )

        return report
