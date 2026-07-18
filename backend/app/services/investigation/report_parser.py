"""
Parser for LLM investigation reports.
"""

from __future__ import annotations

import json
import re

from loguru import logger

from app.schemas.investigation import InvestigationReport


class ReportParser:
    """
    Parses structured JSON responses returned by the LLM.
    """

    def parse(
        self,
        response: str,
    ) -> InvestigationReport:
        """
        Parse the LLM response into an InvestigationReport.
        """

        cleaned = response.strip()

        # Remove markdown code fences.
        cleaned = re.sub(
            r"^```(?:json)?",
            "",
            cleaned,
            flags=re.IGNORECASE | re.MULTILINE,
        )

        cleaned = re.sub(
            r"```$",
            "",
            cleaned,
            flags=re.MULTILINE,
        ).strip()

        # Extract the first JSON object from the response.
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1:
            logger.error(
                "No JSON object found in LLM response:\n{}",
                response,
            )
            raise ValueError(
                "LLM response did not contain valid JSON."
            )

        cleaned = cleaned[start : end + 1]

        try:
            data = json.loads(cleaned)

        except json.JSONDecodeError:
            logger.exception(
                "Invalid JSON returned by Gemini:\n{}",
                response,
            )
            raise

        return InvestigationReport.model_validate(data)