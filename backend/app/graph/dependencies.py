"""
Dependency providers for the graph module.

Provides FastAPI dependency injection helpers for graph-related
components.
"""

from fastapi import Depends

from app.graph.repository import GraphRepository
from app.graph.service import GraphService


def get_graph_repository() -> GraphRepository:
    """
    Return a GraphRepository instance.

    Returns:
        Configured graph repository.
    """
    return GraphRepository()


def get_graph_service(
    repository: GraphRepository = Depends(
        get_graph_repository,
    ),
) -> GraphService:
    """
    Return a GraphService instance.

    Args:
        repository:
            Graph repository dependency.

    Returns:
        Configured graph service.
    """
    return GraphService(
        repository=repository,
    )
