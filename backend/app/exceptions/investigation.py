"""
Domain exceptions for Investigation Report Generation and LLM integration.
"""

from __future__ import annotations

from app.exceptions.base import SentinelGraphError


class PromptValidationError(SentinelGraphError):
    """
    Raised when prompt validation fails prior to LLM submission.
    """


class LLMProviderError(SentinelGraphError):
    """
    Raised when an LLM provider request fails or returns an error.
    """


class LLMTimeoutError(LLMProviderError):
    """
    Raised when an LLM provider request times out.
    """


class ReportParsingError(SentinelGraphError):
    """
    Raised when response text cannot be parsed into structured JSON.
    """


class InvalidReportSchemaError(SentinelGraphError):
    """
    Raised when parsed JSON does not match ProfessionalInvestigationReport schema.
    """
