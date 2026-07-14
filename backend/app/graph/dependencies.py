"""
Dependency providers for the graph module.

Provides FastAPI dependency injection helpers for graph-related
components.
"""

from __future__ import annotations

from fastapi import Depends

from app.graph.builder import GraphBuilder
from app.graph.repository import GraphRepository
from app.graph.service import GraphService


def get_graph_builder() -> GraphBuilder:
    """
    Return a GraphBuilder instance.

    Returns:
        Configured graph builder.
    """
    return GraphBuilder()


def get_graph_repository() -> GraphRepository:
    """
    Return a GraphRepository instance.

    Returns:
        Configured graph repository.
    """
    return GraphRepository()


def get_graph_service(
    builder: GraphBuilder = Depends(
        get_graph_builder,
    ),
    repository: GraphRepository = Depends(
        get_graph_repository,
    ),
) -> GraphService:
    """
    Return a GraphService instance.

    Args:
        builder:
            Graph builder dependency.

        repository:
            Graph repository dependency.

    Returns:
        Configured graph service.
    """
    return GraphService(
        builder=builder,
        repository=repository,
    )