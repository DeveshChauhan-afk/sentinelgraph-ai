# app/ai/client.py
"""
Gemini AI client implementation.

Provides a reusable abstraction over the Google GenAI SDK.
"""

from __future__ import annotations
from google.genai.errors import (
    APIError,
    ClientError,
    ServerError,
)
import asyncio
import time

from google import genai
from google.genai import types
from loguru import logger

from app.ai.base import AIClient
from app.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIRequestError,
    AIResponseError,
    AIUnavailableError,
    AIRateLimitError,
)
from app.core.config import Settings


class GeminiClient(AIClient):
    """
    Client for interacting with the Gemini API.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the Gemini client.

        Args:
            settings: Application settings.
        """
        self._settings = settings

        try:
            self._client = genai.Client(
                api_key=settings.GEMINI_API_KEY.get_secret_value(),
            )
        except Exception as exc:
            raise AIConfigurationError("Failed to initialize Gemini client.") from exc

    def _build_generation_config(self) -> types.GenerateContentConfig:
        """
        Build Gemini generation configuration.

        Returns:
            Configured GenerateContentConfig instance.
        """
        return types.GenerateContentConfig(
            temperature=self._settings.LLM_TEMPERATURE,
            max_output_tokens=self._settings.LLM_MAX_TOKENS,
        )

    async def generate_content(
        self,
        prompt: str,
    ) -> str:
        """
        Generate content using Gemini.

        Args:
            prompt: Prompt sent to Gemini.

        Returns:
            Generated text response.

        Raises:
            AIError:
                If generation fails.
        """
        logger.info(
            "Sending request to Gemini " "(model={}, prompt_length={})",
            self._settings.GEMINI_MODEL,
            len(prompt),
        )

        start_time = time.perf_counter()

        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._settings.GEMINI_MODEL,
                contents=prompt,
                config=self._build_generation_config(),
            )

            text = getattr(response, "text", None)

            if not text:
                raise AIResponseError("Gemini returned an empty response.")

            duration = time.perf_counter() - start_time

            logger.info(
                "Gemini response received " "(duration={:.2f}s, response_length={})",
                duration,
                len(text),
            )

            return text

        except Exception as exc:
            self._translate_exception(exc)

    def _translate_exception(self, exc: Exception) -> None:
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
