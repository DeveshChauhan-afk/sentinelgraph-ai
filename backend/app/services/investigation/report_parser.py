"""
ReportParser Service (Sprint 9 Phase 4.6).

Parses raw LLM responses into canonical immutable ProfessionalInvestigationReport objects,
validating JSON structures, preserving citations, attaching telemetry, and translating schema errors.
"""

from __future__ import annotations

import json
import re
from uuid import uuid4

from loguru import logger
from pydantic import ValidationError

from app.exceptions.investigation import InvalidReportSchemaError, ReportParsingError
from app.schemas.investigation import InvestigationReport
from app.schemas.llm_response import LLMResponse
from app.schemas.prompt import PromptRequest
from app.schemas.report import ProfessionalInvestigationReport, ReportTelemetry


class ReportParser:
    """
    Deterministic parser for structured LLM investigation reports.
    """

    def parse_report(
        self,
        llm_response: LLMResponse,
        prompt_request: PromptRequest,
        correlation_id: str | None = None,
    ) -> ProfessionalInvestigationReport:
        """
        Parse an LLMResponse into an immutable ProfessionalInvestigationReport.

        Args:
            llm_response: Normalized LLMResponse from LLMClient.
            prompt_request: Source PromptRequest sent to LLM.
            correlation_id: Optional correlation tracking identifier.

        Returns:
            Validated immutable ProfessionalInvestigationReport.

        Raises:
            ReportParsingError: If JSON extraction or parsing fails.
            InvalidReportSchemaError: If schema validation fails.
        """
        raw_text = llm_response.response_text
        corr_id = correlation_id or f"CORR-{uuid4().hex[:10].upper()}"

        logger.info(
            "Parsing report response for correlation_id='{}' (prompt_hash='{}').",
            corr_id,
            llm_response.metadata.prompt_hash[:12],
        )

        data_dict = self._extract_json_dict(raw_text)

        # Build telemetry metadata
        telemetry = ReportTelemetry(
            correlation_id=corr_id,
            provider=llm_response.metadata.provider,
            model=llm_response.metadata.model,
            latency_ms=llm_response.metadata.latency_ms,
            prompt_tokens=llm_response.usage.prompt_tokens,
            completion_tokens=llm_response.usage.completion_tokens,
            total_tokens=llm_response.usage.total_tokens,
            prompt_hash=llm_response.metadata.prompt_hash,
            template_version=prompt_request.metadata.template_version,
            summary_version=prompt_request.metadata.summary_version,
            report_context_version=prompt_request.metadata.report_context_version,
        )

        # Attach telemetry and report_id if missing from LLM JSON
        if "telemetry" not in data_dict or not data_dict["telemetry"]:
            data_dict["telemetry"] = telemetry.model_dump(mode="json")
        if "report_id" not in data_dict or not data_dict["report_id"]:
            data_dict["report_id"] = f"RPT-{uuid4().hex[:10].upper()}"

        try:
            report = ProfessionalInvestigationReport.model_validate(data_dict)
            logger.info("Successfully validated ProfessionalInvestigationReport report_id='{}'.", report.report_id)
            return report
        except ValidationError as exc:
            logger.error("Schema validation failed for LLM report JSON: {}", exc)
            raise InvalidReportSchemaError(f"LLM response failed report schema validation: {exc}") from exc

    def _extract_json_dict(self, raw_text: str) -> dict:
        """Extract and parse JSON dictionary from raw response text."""
        cleaned = raw_text.strip()

        # Strip Markdown code fences
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1:
            logger.error("No JSON object bounds found in LLM response text.")
            raise ReportParsingError("LLM response did not contain a valid JSON object.")

        json_str = cleaned[start : end + 1]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.error("Failed to decode JSON from LLM response string.")
            raise ReportParsingError(f"LLM response JSON decoding error: {exc}") from exc

    def parse(self, response: str) -> InvestigationReport:
        """Legacy parse method for Sprint 8 backward compatibility."""
        data_dict = self._extract_json_dict(response)
        return InvestigationReport.model_validate(data_dict)
