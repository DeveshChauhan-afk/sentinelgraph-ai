"""
Graph domain exceptions.

Defines application-specific exceptions for the graph layer,
preventing Neo4j driver exceptions from leaking into the
service layer.
"""


class GraphError(Exception):
    """
    Base exception for all graph-related errors.
    """


class GraphConfigurationError(GraphError):
    """
    Raised when the graph database configuration is invalid.
    """


class GraphConnectionError(GraphError):
    """
    Raised when a connection to the graph database cannot be established.
    """


class GraphPersistenceError(GraphError):
    """
    Raised when graph data cannot be persisted.
    """


class GraphQueryError(GraphError):
    """
    Raised when execution of a graph query fails.
    """


class GraphNodeError(GraphError):
    """
    Raised when graph node creation or validation fails.
    """


class GraphRelationshipError(GraphError):
    """
    Raised when graph relationship creation or validation fails.
    """


class GraphEntityNotFoundError(GraphError):
    """
    Raised when a graph entity cannot be found.
    """