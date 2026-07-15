"""
Neo4j graph repository.

Provides persistence operations for the Fraud Intelligence Graph.
The repository is responsible only for communicating with Neo4j and
contains no business logic.
"""

from __future__ import annotations

from time import perf_counter

from loguru import logger
from neo4j import AsyncDriver
from neo4j.exceptions import Neo4jError

from app.db.neo4j import get_neo4j_driver
from app.graph.exceptions import (
    GraphConnectionError,
    GraphPersistenceError,
)
from app.graph.models import (
    GraphData,
    GraphNode,
    GraphRelationship,
    GraphLabel,
    GraphPersistenceResult,
)


class GraphRepository:
    """
    Repository responsible for persisting graph data into Neo4j.

    This repository encapsulates all Cypher queries and transaction
    management, ensuring that graph persistence remains isolated from
    the service layer.
    """

    def __init__(
        self,
        driver: AsyncDriver | None = None,
    ) -> None:
        """
        Initialize the repository.

        Args:
            driver:
                Optional Neo4j async driver. If omitted, the shared
                application driver is used.
        """
        self._driver = driver or get_neo4j_driver()

    async def save_graph(
        self,
        graph: GraphData,
    ) -> GraphPersistenceResult:  
        """
        Persist an entire graph inside a single Neo4j transaction.

        All nodes are merged first, followed by relationships.
        The operation is atomic.

        Args:
            graph:
                Graph data to persist.

        Returns:
            Statistics about the persistence operation.

        Raises:
            GraphConnectionError:
                If a database connection cannot be established.

            GraphPersistenceError:
                If graph persistence fails.
        """
        start = perf_counter()

        logger.info(
            "Persisting graph (nodes={}, relationships={}).",
            len(graph.nodes),
            len(graph.relationships),
        )

        try:
            async with self._driver.session() as session:
                await session.execute_write(
                    self._save_graph_tx,
                    graph,
                )

        except Neo4jError as exc:
            logger.exception("Neo4j persistence failed.")
            raise GraphPersistenceError(
                "Failed to persist graph."
            ) from exc

        except Exception as exc:
            logger.exception("Unable to connect to Neo4j.")
            raise GraphConnectionError(
                "Neo4j connection failed."
            ) from exc

        duration_ms = (perf_counter() - start) * 1000

        logger.success(
            "Graph persisted successfully ({:.2f} ms).",
            duration_ms,
        )

        return GraphPersistenceResult(
            nodes_persisted=len(graph.nodes),
            relationships_persisted=len(graph.relationships),
            duration_ms=duration_ms,
        )

    async def _save_graph_tx(
        self,
        tx,
        graph: GraphData,
    ) -> None:
        """
        Persist graph inside an existing transaction.

        Args:
            tx:
                Neo4j managed transaction.

            graph:
                Graph to persist.
        """
        await self._persist_nodes(
            tx,
            graph,
        )

        await self._persist_relationships(
            tx,
            graph,
        )

    async def _persist_nodes(
        self,
        tx,
        graph: GraphData,
    ) -> None:
        """
        Persist all graph nodes.

        Args:
            tx:
                Active Neo4j transaction.

            graph:
                Graph data containing nodes.

        Raises:
            GraphPersistenceError:
                If node persistence fails.
        """
        logger.debug(
            "Persisting {} graph nodes.",
            len(graph.nodes),
        )

        for node in graph.nodes:
            await self._merge_node(
                tx,
                node,
            )

    async def _merge_node(
        self,
        tx,
        node: GraphNode,
    ) -> None:
        """
        Merge a single graph node into Neo4j.

        MERGE guarantees idempotent writes. Existing nodes are updated
        with the latest properties while new nodes are created when
        necessary.

        Args:
            tx:
                Active Neo4j transaction.

            node:
                Graph node to persist.
        """
        cypher = f"""
        MERGE (n:{node.label.value} {{id: $id}})
        SET n += $properties
        """

        if "id" in node.properties:
            raise GraphPersistenceError(
                "Node properties cannot contain reserved key 'id'."
            )

        properties = {
            "id": node.id,
            **node.properties,
        }
        try:
            await tx.run(
                cypher,
                id=node.id,
                properties=properties,
            )

        except Neo4jError as exc:
            logger.exception(
                "Failed to merge node '{}'.",
                node.id,
            )
            raise GraphPersistenceError(f"Unable to persist node '{node.id}'.") from exc

    async def _persist_relationships(
        self,
        tx,
        graph: GraphData,
    ) -> None:
        """
        Persist all graph relationships.

        Args:
            tx:
                Active Neo4j transaction.

            graph:
                Graph data containing relationships.

        Raises:
            GraphPersistenceError:
                If relationship persistence fails.
        """
        logger.debug(
            "Persisting {} graph relationships.",
            len(graph.relationships),
        )

        node_lookup = {node.id: node for node in graph.nodes}

        for relationship in graph.relationships:
            source_node = node_lookup.get(
                relationship.source,
            )

            target_node = node_lookup.get(
                relationship.target,
            )

            if source_node is None or target_node is None:
                raise GraphPersistenceError("Relationship references unknown node.")

            await self._merge_relationship(
                tx=tx,
                relationship=relationship,
                source_label=source_node.label,
                target_label=target_node.label,
            )

    async def _merge_relationship(
        self,
        tx,
        relationship: GraphRelationship,
        source_label: GraphLabel,
        target_label: GraphLabel,
    ) -> None:
        """
        Merge a graph relationship.

        Args:
            tx:
                Active Neo4j transaction.

            relationship:
                Relationship to persist.

            source_label:
                Source node label.

            target_label:
                Target node label.
        """
        cypher = f"""
        MATCH (source:{source_label.value} {{id: $source_id}})
        MATCH (target:{target_label.value} {{id: $target_id}})
        MERGE (source)-[r:{relationship.type.value}]->(target)
        SET r += $properties
        """

        try:
            await tx.run(
                cypher,
                source_id=relationship.source,
                target_id=relationship.target,
                properties=relationship.properties,
            )

        except Neo4jError as exc:
            logger.exception(
                "Failed to merge relationship '{}' -> '{}'.",
                relationship.source,
                relationship.target,
            )

            raise GraphPersistenceError("Unable to persist relationship.") from exc
