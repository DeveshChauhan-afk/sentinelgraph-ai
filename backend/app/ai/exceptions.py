# app/ai/exceptions.py

"""
Custom exceptions for the AI layer.

These exceptions abstract provider-specific errors (e.g., Gemini SDK)
into application-level exceptions that can be handled consistently
throughout the service layer.
"""


class AIError(Exception):
    """
    Base exception for all AI-related errors.
    """


class AIConfigurationError(AIError):
    """
    Raised when the AI client is improperly configured.

    Examples:
        - Missing API key
        - Invalid model configuration
    """


class AIAuthenticationError(AIError):
    """
    Raised when authentication with the AI provider fails.
    """


class AIRateLimitError(AIError):
    """
    Raised when the AI provider rate limit or quota is exceeded.
    """


class AIRequestError(AIError):
    """
    Raised when an AI request cannot be completed.

    Examples:
        - Network timeout
        - Connection failure
        - Invalid request
    """


class AIResponseError(AIError):
    """
    Raised when the AI response is invalid or cannot be processed.

    Examples:
        - Empty response
        - Invalid JSON
        - Schema validation failure
    """


class AIUnavailableError(AIError):
    """
    Raised when the AI service is temporarily unavailable.
    """
