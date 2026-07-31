"""
Gemini LLM Provider Implementation (Sprint 9 Phase 4.3).

Provides a provider-independent implementation of LLMClient over the Google GenAI SDK,
normalizing outputs and metadata into canonical LLMResponse objects.
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError
from loguru import logger
from pydantic import BaseModel

from app.ai.base import AIClient
from app.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
    AIUnavailableError,
)
from app.ai.llm_client import LLMClient
from app.core.config import Settings
from app.exceptions.investigation import LLMProviderError, LLMTimeoutError
from app.schemas.investigation import InvestigationReport
from app.schemas.llm_response import LLMMetadata, LLMResponse, LLMUsage
from app.schemas.prompt import PromptRequest


class GeminiClient(LLMClient, AIClient):
    """
    Gemini implementation of LLMClient provider interface.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the Gemini LLM client.

        Args:
            settings: Application configuration settings.
        """
        self._settings = settings
        try:
            self._client = genai.Client(
                api_key=settings.GEMINI_API_KEY.get_secret_value(),
            )
        except Exception as exc:
            raise AIConfigurationError("Failed to initialize Gemini SDK client.") from exc

    async def generate(
        self,
        prompt: PromptRequest,
    ) -> LLMResponse:
        """
        Execute an LLM completion request for the given PromptRequest.

        Args:
            prompt: Provider-independent PromptRequest package.

        Returns:
            Normalized LLMResponse containing structured JSON completion text and telemetry.
        """
        model_name = prompt.metadata.model_name or self._settings.GEMINI_MODEL
        req_id = f"GEM-{uuid4().hex[:12].upper()}"

        logger.info(
            "Executing LLM completion via Gemini (request_id={}, model={}, prompt_hash={}).",
            req_id,
            model_name,
            prompt.metadata.prompt_hash[:12],
        )

        start_time = time.perf_counter()

        from app.schemas.report import ProfessionalInvestigationReport

        config = types.GenerateContentConfig(
            temperature=prompt.constraints.temperature,
            max_output_tokens=prompt.constraints.max_tokens,
            response_mime_type="application/json",
            response_schema=ProfessionalInvestigationReport,
        )

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=model_name,
                    contents=prompt.full_prompt,
                    config=config,
                ),
                timeout=60.0,
            )

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            text = getattr(response, "text", None)
            if not text:
                raise LLMProviderError("Gemini provider returned empty response text.")

            # Extract token usage if available from SDK response
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            usage_meta = getattr(response, "usage_metadata", None)
            if usage_meta:
                prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
                completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
                total_tokens = getattr(usage_meta, "total_token_count", 0) or (prompt_tokens + completion_tokens)

            finish_reason = "STOP"
            if hasattr(response, "candidates") and response.candidates:
                finish_reason = str(getattr(response.candidates[0], "finish_reason", "STOP"))

            metadata = LLMMetadata(
                provider="Gemini",
                model=model_name,
                request_id=req_id,
                latency_ms=duration_ms,
                prompt_hash=prompt.metadata.prompt_hash,
            )

            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )

            logger.info(
                "Gemini completion success: request_id={}, latency={:.2f}ms, total_tokens={}.",
                req_id,
                duration_ms,
                total_tokens,
            )

            return LLMResponse(
                metadata=metadata,
                usage=usage,
                finish_reason=finish_reason,
                response_text=text,
            )

        except asyncio.TimeoutError as exc:
            logger.error("Gemini API request timed out after 60 seconds.")
            raise LLMTimeoutError("Gemini completion request timed out.") from exc
        except Exception as exc:
            logger.exception("Gemini API execution error: {}", exc)
            if isinstance(exc, (ClientError, ServerError, APIError)):
                raise LLMProviderError(f"Gemini API Error: {exc}") from exc
            raise LLMProviderError(f"Unexpected LLM generation error: {exc}") from exc

    def _build_generation_config(
        self,
        response_schema: type[BaseModel] | None = InvestigationReport,
    ) -> types.GenerateContentConfig:
        """Legacy helper for Sprint 8 generate_content."""
        return types.GenerateContentConfig(
            temperature=self._settings.LLM_TEMPERATURE,
            max_output_tokens=self._settings.LLM_MAX_TOKENS,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

    async def generate_content(
        self,
        prompt: str,
        response_schema: type[BaseModel] | None = InvestigationReport,
    ) -> str:
        """Legacy method for Sprint 8 backward compatibility."""
        logger.info(
            "Sending legacy request to Gemini (model={}, prompt_length={})",
            self._settings.GEMINI_MODEL,
            len(prompt),
        )
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._settings.GEMINI_MODEL,
                contents=prompt,
                config=self._build_generation_config(response_schema),
            )
            text = getattr(response, "text", None)
            if not text:
                raise AIResponseError("Gemini returned an empty response.")
            return text
        except Exception as exc:
            self._translate_exception(exc)

    def _translate_exception(self, exc: Exception) -> None:
        """Translate legacy exceptions."""
        logger.exception("Gemini request failed.")
        if isinstance(exc, ClientError):
            status = getattr(exc, "status_code", None)
            if status in (401, 403):
                raise AIAuthenticationError(str(exc)) from exc
            if status == 404:
                raise AIConfigurationError(str(exc)) from exc
            if status == 429:
                raise AIRateLimitError(str(exc)) from exc
            raise AIRequestError(str(exc)) from exc
        if isinstance(exc, ServerError):
            raise AIUnavailableError(str(exc)) from exc
        if isinstance(exc, APIError):
            raise AIRequestError(str(exc)) from exc
        raise AIRequestError(str(exc)) from exc
