"""
Base service class.

Provides common functionality shared across all
business services.
"""

from __future__ import annotations

from typing import Generic, TypeVar

RepositoryType = TypeVar("RepositoryType")


class BaseService(Generic[RepositoryType]):
    """
    Base class for all services.

    Encapsulates the repository dependency and provides
    a consistent foundation for domain services.
    """

    def __init__(self, repository: RepositoryType) -> None:
        self._repository = repository
