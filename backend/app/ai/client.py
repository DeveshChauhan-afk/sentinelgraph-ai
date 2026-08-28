"""
Gemini LLM Provider Implementation (Sprint 9 Phase 4.3 / Sprint 12.4 Reliability Hardening).

Provides a provider-independent implementation of LLMClient over the Google GenAI SDK,
normalizing outputs and metadata into canonical LLMResponse objects with bounded retry,
configurable timeout, and exact per-attempt observability.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
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
from app.core.metrics import (
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)
from app.exceptions.investigation import LLMProviderError, LLMTimeoutError
from app.schemas.investigation import InvestigationReport
from app.schemas.llm_response import LLMMetadata, LLMResponse, LLMUsage
from app.schemas.prompt import PromptRequest


class GeminiClient(LLMClient, AIClient):
    """
    Gemini implementation of LLMClient and AIClient provider interface.
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

    def _extract_status_code(self, exc: Exception) -> int | None:
        """
        Extract numeric HTTP status code from an exception if available.
        """
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        if response is not None:
            resp_code = getattr(response, "status_code", None)
            if isinstance(resp_code, int):
                return resp_code
        return None

    def _is_transient_error(self, exc: Exception) -> bool:
        """
        Determine whether an exception represents a transient provider failure
        suitable for bounded retry.

        Retryable:
            - HTTP 429 (Rate Limit / Quota / Resource Exhausted)
            - HTTP 500, 502, 503, 504 (Provider Server Errors / Gateway / Unavailable)
            - ServerError instances from Google GenAI SDK
            - Transient network connection failures

        Non-retryable:
            - HTTP 400 (Bad Request / invalid prompt syntax)
            - HTTP 401, 403 (Unauthorized / Forbidden / Auth failure)
            - HTTP 404 (Not Found / Model not found / Config error)
            - Application timeouts (asyncio.TimeoutError) to avoid unbounded blocking
            - Internal schema / application processing errors
        """
        if isinstance(exc, (AIAuthenticationError, AIConfigurationError)):
            return False

        if isinstance(exc, asyncio.TimeoutError):
            return False

        code = self._extract_status_code(exc)
        if code is not None:
            if code == 429:
                return True
            if code in (500, 502, 503, 504):
                return True
            if 400 <= code < 500:
                return False

        if isinstance(exc, ServerError):
            return True

        status = getattr(exc, "status", None)
        if isinstance(status, str):
            status_upper = status.upper()
            if "RESOURCE_EXHAUSTED" in status_upper or "UNAVAILABLE" in status_upper:
                return True
            if "DEADLINE_EXCEEDED" in status_upper:
                return True

        if isinstance(exc, (ConnectionResetError, ConnectionRefusedError)):
            return True

        return False

    async def _execute_with_retry(
        self,
        model_name: str,
        contents: Any,
        config: types.GenerateContentConfig,
    ) -> Any:
        """
        Execute a single generate_content call against Gemini with bounded retry,
        configurable timeout, and exact per-attempt metric instrumentation.

        Retry Semantics:
            `GEMINI_MAX_RETRIES` represents the total attempt budget: 1 initial attempt
            plus up to `(GEMINI_MAX_RETRIES - 1)` retry attempts on transient errors (e.g. HTTP 429, 5xx).
            For example, GEMINI_MAX_RETRIES=3 yields at most 3 total provider calls on complete exhaustion.

        Timeout & Thread Behavior:
            - Synchronous SDK calls are offloaded to a worker thread via `asyncio.to_thread(...)`.
            - `asyncio.wait_for(..., timeout=timeout_seconds)` enforces the per-attempt timeout.
            - When timeout expires, the coroutine stops waiting and raises `asyncio.TimeoutError`.
            - In Python, `wait_for()` cancels the waiting task but does NOT forcibly terminate
              the underlying worker thread. The synchronous SDK invocation may continue running
              in the background thread until the network socket closes or the call completes.
            - The worker performs read-only LLM generation and performs no application, database
              (PostgreSQL), or Neo4j state mutations.
            - `asyncio.TimeoutError` is treated as non-retryable and is immediately re-raised,
              ensuring timed-out attempts do NOT schedule subsequent retries and cannot create
              overlapping uncontrolled provider attempts.

        Args:
            model_name: Gemini model name.
            contents: Prompt contents (string or structured prompt).
            config: Generation configuration.

        Returns:
            The raw response object returned by the Gemini SDK.

        Raises:
            asyncio.TimeoutError: If a request attempt times out (non-retryable).
            Exception: If provider fails permanently or retries are exhausted.
        """
        max_retries = max(1, self._settings.GEMINI_MAX_RETRIES)
        initial_delay = self._settings.GEMINI_RETRY_INITIAL_DELAY
        max_delay = self._settings.GEMINI_RETRY_MAX_DELAY
        timeout_seconds = self._settings.GEMINI_TIMEOUT_SECONDS

        last_exception: Exception | None = None

        for attempt in range(1, max_retries + 1):
            start_time = time.perf_counter()
            try:
                # Execute synchronous SDK call in threadpool. If wait_for times out,
                # the task is cancelled while the thread finishes in background without mutations.
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.models.generate_content,
                        model=model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=timeout_seconds,
                )
                duration_seconds = time.perf_counter() - start_time
                llm_request_duration_seconds.labels(
                    provider="gemini",
                    model=model_name,
                ).observe(duration_seconds)

                llm_requests_total.labels(
                    provider="gemini",
                    model=model_name,
                    status="success",
                ).inc()

                # Extract token usage metadata if available
                usage_meta = getattr(response, "usage_metadata", None)
                if usage_meta:
                    raw_prompt_tokens = getattr(usage_meta, "prompt_token_count", 0)
                    prompt_tokens = raw_prompt_tokens if isinstance(raw_prompt_tokens, int) else 0
                    raw_completion_tokens = getattr(usage_meta, "candidates_token_count", 0)
                    completion_tokens = raw_completion_tokens if isinstance(raw_completion_tokens, int) else 0
                    if prompt_tokens > 0:
                        llm_tokens_total.labels(
                            provider="gemini",
                            model=model_name,
                            type="prompt",
                        ).inc(prompt_tokens)
                    if completion_tokens > 0:
                        llm_tokens_total.labels(
                            provider="gemini",
                            model=model_name,
                            type="completion",
                        ).inc(completion_tokens)

                return response

            except asyncio.TimeoutError as exc:
                duration_seconds = time.perf_counter() - start_time
                llm_request_duration_seconds.labels(
                    provider="gemini",
                    model=model_name,
                ).observe(duration_seconds)

                llm_requests_total.labels(
                    provider="gemini",
                    model=model_name,
                    status="error",
                ).inc()

                logger.error(
                    "Gemini API request timed out after {:.1f}s (attempt {}/{}).",
                    timeout_seconds,
                    attempt,
                    max_retries,
                )
                raise exc

            except Exception as exc:
                duration_seconds = time.perf_counter() - start_time
                llm_request_duration_seconds.labels(
                    provider="gemini",
                    model=model_name,
                ).observe(duration_seconds)

                llm_requests_total.labels(
                    provider="gemini",
                    model=model_name,
                    status="error",
                ).inc()

                last_exception = exc
                is_transient = self._is_transient_error(exc)

                if is_transient and attempt < max_retries:
                    delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "Transient Gemini error on attempt {}/{}: {}. Retrying in {:.2f}s...",
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    if is_transient and attempt >= max_retries:
                        logger.error(
                            "Gemini retry exhausted after {} attempts. Last error: {}",
                            max_retries,
                            exc,
                        )
                    else:
                        logger.warning(
                            "Non-retryable Gemini error on attempt {}/{}: {}",
                            attempt,
                            max_retries,
                            exc,
                        )
                    raise exc

        if last_exception is not None:
            raise last_exception

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

        from app.schemas.report import ProfessionalInvestigationReport

        config = types.GenerateContentConfig(
            temperature=prompt.constraints.temperature,
            max_output_tokens=prompt.constraints.max_tokens,
            response_mime_type="application/json",
            response_schema=ProfessionalInvestigationReport,
        )

        overall_start = time.perf_counter()
        try:
            response = await self._execute_with_retry(
                model_name=model_name,
                contents=prompt.full_prompt,
                config=config,
            )
        except asyncio.TimeoutError as exc:
            raise LLMTimeoutError("Gemini completion request timed out.") from exc
        except Exception as exc:
            logger.exception("Gemini API execution error: {}", exc)
            if isinstance(exc, (ClientError, ServerError, APIError)):
                raise LLMProviderError(f"Gemini API Error: {exc}") from exc
            raise LLMProviderError(f"Unexpected LLM generation error: {exc}") from exc

        duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)

        text = getattr(response, "text", None)
        if not text:
            raise LLMProviderError("Gemini provider returned empty response text.")

        # Extract token usage if available from SDK response
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta:
            raw_prompt_tokens = getattr(usage_meta, "prompt_token_count", 0)
            prompt_tokens = raw_prompt_tokens if isinstance(raw_prompt_tokens, int) else 0
            raw_completion_tokens = getattr(usage_meta, "candidates_token_count", 0)
            completion_tokens = raw_completion_tokens if isinstance(raw_completion_tokens, int) else 0
            raw_total_tokens = getattr(usage_meta, "total_token_count", 0)
            total_tokens = (
                raw_total_tokens
                if isinstance(raw_total_tokens, int) and raw_total_tokens > 0
                else (prompt_tokens + completion_tokens)
            )

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
            response = await self._execute_with_retry(
                model_name=self._settings.GEMINI_MODEL,
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
        logger.exception("Gemini request failed: {}", exc)
        if isinstance(exc, (AIResponseError, AIAuthenticationError, AIConfigurationError, AIRateLimitError, AIRequestError, AIUnavailableError)):
            raise exc
        if isinstance(exc, asyncio.TimeoutError):
            raise AIRequestError("Gemini request timed out.") from exc
        if isinstance(exc, ClientError):
            code = self._extract_status_code(exc)
            if code in (401, 403):
                raise AIAuthenticationError(str(exc)) from exc
            if code == 404:
                raise AIConfigurationError(str(exc)) from exc
            if code == 429:
                raise AIRateLimitError(str(exc)) from exc
            raise AIRequestError(str(exc)) from exc
        if isinstance(exc, ServerError):
            raise AIUnavailableError(str(exc)) from exc
        if isinstance(exc, APIError):
            code = self._extract_status_code(exc)
            if code == 429:
                raise AIRateLimitError(str(exc)) from exc
            if code in (500, 502, 503, 504):
                raise AIUnavailableError(str(exc)) from exc
            raise AIRequestError(str(exc)) from exc
        raise AIRequestError(str(exc)) from exc
