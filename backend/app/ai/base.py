"""
Abstract interface for AI clients.

Defines the contract that all AI providers must implement.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class AIClient(ABC):
    """
    Abstract base class for AI clients.
    """

    @abstractmethod
    async def generate_content(
        self,
        prompt: str,
        response_schema: type[BaseModel] | None = None,
    ) -> str:
        """
        Generate text content from the supplied prompt.

        Args:
            prompt: Input prompt.

            response_schema: Optional schema Gemini must use for its JSON response.

        Returns:
            Generated text response.

        Raises:
            AIError: If generation fails.
        """
        raise NotImplementedError
