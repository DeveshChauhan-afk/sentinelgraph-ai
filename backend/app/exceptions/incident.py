"""
Incident domain exceptions.
"""

from .base import SentinelGraphError


class IncidentNotFoundError(SentinelGraphError):
    """Raised when an incident cannot be found."""


class DuplicateCaseReferenceError(SentinelGraphError):
    """Raised when a case reference already exists."""


class InvalidIncidentStateError(SentinelGraphError):
    """Raised when an invalid state transition is attempted."""


class BusinessValidationError(SentinelGraphError):
    """Raised when business validation fails."""
