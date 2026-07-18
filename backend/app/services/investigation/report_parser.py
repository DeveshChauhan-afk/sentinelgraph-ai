"""
Parser for LLM investigation reports.
"""

from __future__ import annotations

import json

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

        data = json.loads(response)

        return InvestigationReport.model_validate(data)