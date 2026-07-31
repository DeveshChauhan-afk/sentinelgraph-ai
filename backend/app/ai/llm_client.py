#app/ai/llm_client.py
"""
Abstract LLM Client Interface (Sprint 9 Phase 4.1).

Defines a provider-independent interface for executing LLM completions from PromptRequest inputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.llm_response import LLMResponse
from app.schemas.prompt import PromptRequest


class LLMClient(ABC):
    """
    Abstract base class for all provider-independent LLM clients.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: PromptRequest,
    ) -> LLMResponse:
        """
        Execute an LLM completion for the given PromptRequest.

        Args:
            prompt: Provider-independent PromptRequest package.

        Returns:
            Normalized LLMResponse containing completion text and metadata.

        Raises:
            LLMProviderError: If the provider request fails.
            LLMTimeoutError: If the request times out.
        """
        raise NotImplementedError
