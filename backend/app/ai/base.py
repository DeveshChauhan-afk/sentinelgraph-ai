"""
Abstract interface for AI clients.

Defines the contract that all AI providers must implement.
"""

from abc import ABC, abstractmethod


class AIClient(ABC):
    """
    Abstract base class for AI clients.
    """

    @abstractmethod
    async def generate_content(self, prompt: str) -> str:
        """
        Generate text content from the supplied prompt.

        Args:
            prompt: Input prompt.

        Returns:
            Generated text response.

        Raises:
            AIError: If generation fails.
        """
        raise NotImplementedError
