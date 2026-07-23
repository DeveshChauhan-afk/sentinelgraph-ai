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
from app.graph.query_models import GraphNeighborsResponse
from app.graph.query_models import RelatedIncidentsResponse
from app.graph.exceptions import GraphQueryError
from app.graph.query_results import (
    NeighborQueryResult,
    TopRiskEntityResult,
)

from app.graph.query_results import (
    RiskMetricsResult,
)
from app.graph.query_results import FraudRingResult
from app.graph.query_results import NetworkSummaryResult
from app.graph.query_results import PathResult
from app.graph.query_results import SharedEntityResult
from typing import Any
from neo4j.graph import Path
from app.schemas.analytics import FraudRingSummary, GraphSummary
from app.schemas.analytics import TopConnectedEntity
from app.schemas.analytics import SharedEntityAnalysis


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
            raise GraphPersistenceError("Failed to persist graph.") from exc

        except Exception as exc:
            logger.exception("Unable to connect to Neo4j.")
            raise GraphConnectionError("Neo4j connection failed.") from exc

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

    async def find_entity(
        self,
        value: str,
    ) -> GraphNode | None:
        """
        Find a graph entity by its value.

        Args:
            value:
                Entity value (phone number, email, UPI ID, etc.).

        Returns:
            The matching graph node if found, otherwise None.

        Raises:
            GraphConnectionError:
                If a Neo4j connection cannot be established.

            GraphPersistenceError:
                If the query execution fails.
        """
        logger.debug(
            "Searching graph entity with value '{}'.",
            value,
        )

        query = """
        MATCH (n)
        WHERE n.lookup_value = $value
        RETURN n, labels(n) AS labels
        LIMIT 1
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=value,
                )

                record = await result.single()

        except Neo4jError as exc:
            logger.exception(
                "Failed to query graph entity '{}'.",
                value,
            )

            raise GraphPersistenceError(
                "Failed to query graph entity.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if record is None:
            logger.debug(
                "No graph entity found for '{}'.",
                value,
            )
            return None

        return self._map_node(
            node=record["n"],
            labels=record["labels"],
        )

    async def _get_connected_complaints(
        self,
        entity: GraphNode,
    ) -> list[GraphNode]:
        """
        Return complaints connected to the supplied node.
        """

        if entity.label == GraphLabel.COMPLAINT:
            query = """
            MATCH (complaint:Complaint {lookup_value:$value})
            MATCH (complaint)-[:MENTIONS]->(e)
            MATCH (e)<-[:MENTIONS]-(related:Complaint)
            WHERE related <> complaint
            RETURN DISTINCT related, labels(related) AS labels
            """
        else:
            query = """
            MATCH (entity {lookup_value:$value})
            MATCH (entity)<-[:MENTIONS]-(complaint:Complaint)
            RETURN DISTINCT complaint, labels(complaint) AS labels
            """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=entity.properties["lookup_value"],
                )

                records = await result.data()

        except Neo4jError as exc:
            logger.exception("Failed to retrieve connected complaints.")
            raise GraphQueryError("Failed to retrieve connected complaints.") from exc

        except Exception as exc:
            logger.exception("Unable to connect to Neo4j.")
            raise GraphConnectionError("Neo4j connection failed.") from exc

        complaints: list[GraphNode] = []

        for record in records:
            node = (
                record["related"]
                if entity.label == GraphLabel.COMPLAINT
                else record["complaint"]
            )

            complaints.append(
                self._map_node(
                    node=node,
                    labels=record["labels"],
                )
            )

        return complaints

    async def find_neighbors(
        self,
        value: str,
    ) -> GraphNeighborsResponse | None:
        """
        Retrieve an entity and all directly connected neighbors.

        Args:
            value:
                Entity value (phone number, UPI ID, email, etc.).

        Returns:
            GraphNeighborsResponse if the entity exists, otherwise None.

        Raises:
            GraphConnectionError:
                If a Neo4j connection cannot be established.

            GraphQueryError:
                If the graph query fails.
        """
        logger.debug(
            "Finding neighbors for entity '{}'.",
            value,
        )

        query = """
        MATCH (entity {lookup_value: $value})
        OPTIONAL MATCH (entity)-[]-(neighbor)
        RETURN entity,
            labels(entity) AS entity_labels,
            collect({
                node: neighbor,
                labels: labels(neighbor)
            }) AS neighbors
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=value,
                )

                record = await result.single()

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve neighbors for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve graph neighbors.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if record is None or record["entity"] is None:
            return None

        entity = self._map_node(
            node=record["entity"],
            labels=record["entity_labels"],
        )

        neighbors: list[GraphNode] = []

        for item in record["neighbors"]:
            node = item["node"]

            if node is None:
                continue

            neighbors.append(
                self._map_node(
                    node=node,
                    labels=item["labels"],
                )
            )

        return NeighborQueryResult(
            entity=entity,
            neighbors=neighbors,
        )

    async def find_related_incidents(
        self,
        value: str,
    ) -> RelatedIncidentsResponse | None:
        """
        Retrieve all complaint nodes connected to the supplied node.

        Args:
            value:
                Lookup value of the target node.

        Returns:
            RelatedIncidentsResponse if the entity exists, otherwise None.

        Raises:
            GraphConnectionError:
                If a Neo4j connection cannot be established.

            GraphQueryError:
                If the graph query fails.
        """

        logger.debug(
            "Finding related incidents for '{}'.",
            value,
        )

        entity = await self.find_entity(value)

        if entity is None:
            return None

        try:
            incidents = await self._get_connected_complaints(entity)

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve related incidents for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve related incidents.",
            ) from exc

        except GraphConnectionError:
            raise

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        return RelatedIncidentsResponse(
            entity=entity,
            incidents=incidents,
        )

    def _map_node(
        self,
        node,
        labels: list[str],
    ) -> GraphNode:
        """
        Convert a Neo4j node into a provider-independent GraphNode.

        Args:
            node:
                Neo4j node returned by the driver.

            labels:
                Labels associated with the node.

        Returns:
            A GraphNode domain model.

        Raises:
            GraphPersistenceError:
                If the node has no labels or contains an unsupported label.
        """
        if not labels:
            raise GraphPersistenceError(
                "Graph node does not contain any labels.",
            )

        properties = dict(node)
        properties.pop("id", None)

        try:
            label = GraphLabel(labels[0])

        except ValueError as exc:
            raise GraphPersistenceError(
                f"Unsupported graph label '{labels[0]}'.",
            ) from exc

        return GraphNode(
            id=node["id"],
            label=label,
            properties=properties,
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

    async def get_risk_metrics(
        self,
        value: str,
    ) -> RiskMetricsResult | None:
        """
        Retrieve graph metrics required for risk analysis.
        """

        logger.debug(
            "Retrieving risk metrics for '{}'.",
            value,
        )

        query = """
        MATCH (entity {lookup_value: $value})

        CALL (entity) {
            OPTIONAL MATCH (entity)-[]-(neighbor)
            RETURN count(DISTINCT neighbor) AS neighbor_count
        }

        CALL (entity) {
            OPTIONAL MATCH (entity)-[]-(phone:Phone)
            RETURN count(DISTINCT phone) AS phone_count
        }

        CALL (entity) {
            OPTIONAL MATCH (entity)-[]-(upi:UPI)
            RETURN count(DISTINCT upi) AS upi_count
        }

        CALL (entity) {
            OPTIONAL MATCH (entity)-[]-(email:Email)
            RETURN count(DISTINCT email) AS email_count
        }

        CALL (entity) {
            OPTIONAL MATCH (entity)-[]-(organization:Organization)
            RETURN count(DISTINCT organization) AS organization_count
        }

        RETURN
            entity,
            labels(entity) AS entity_labels,
            neighbor_count,
            phone_count,
            upi_count,
            email_count,
            organization_count
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=value,
                )

                record = await result.single()

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve risk metrics for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve risk metrics.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if record is None:
            return None

        entity = self._map_node(
            node=record["entity"],
            labels=record["entity_labels"],
        )

        # Reuse the centralized traversal logic
        incidents = await self._get_connected_complaints(entity)

        return RiskMetricsResult(
            entity=entity,
            incident_count=len(incidents),
            neighbor_count=record["neighbor_count"],
            phone_count=record["phone_count"],
            upi_count=record["upi_count"],
            email_count=record["email_count"],
            organization_count=record["organization_count"],
        )

    async def find_fraud_ring(
        self,
        value: str,
    ) -> FraudRingResult | None:
        """
        Retrieve every node belonging to the same connected fraud ring.

        Args:
            value:
                Entity value.

        Returns:
            FraudRingResult if the entity exists, otherwise None.

        Raises:
            GraphConnectionError:
                If Neo4j cannot be reached.

            GraphQueryError:
                If query execution fails.
        """
        logger.debug(
            "Finding fraud ring for entity '{}'.",
            value,
        )

        query = """
        MATCH (entity {lookup_value:$value})

        MATCH (entity)-[*0..6]-(connected)

        RETURN DISTINCT
            entity,
            labels(entity) AS entity_labels,
            connected,
            labels(connected) AS connected_labels
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=value,
                )

                records = await result.data()

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve fraud ring for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve fraud ring.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if not records:
            return None

        entity = self._map_node(
            node=records[0]["entity"],
            labels=records[0]["entity_labels"],
        )

        nodes: list[GraphNode] = []
        incidents: list[GraphNode] = []

        seen_ids: set[str] = set()

        for record in records:
            node = self._map_node(
                node=record["connected"],
                labels=record["connected_labels"],
            )

            if node.id in seen_ids:
                continue

            seen_ids.add(node.id)

            if node.label == GraphLabel.COMPLAINT:
                incidents.append(node)
            else:
                nodes.append(node)

        return FraudRingResult(
            entity=entity,
            nodes=nodes,
            incidents=incidents,
        )

    async def get_network_summary(
        self,
    ) -> NetworkSummaryResult:
        """
        Retrieve graph-wide statistics.

        Returns:
            NetworkSummaryResult.

        Raises:
            GraphConnectionError:
                If Neo4j cannot be reached.

            GraphQueryError:
                If query execution fails.
        """

        logger.debug(
            "Retrieving network summary.",
        )

        query = """
        CALL () {
            MATCH (n)
            RETURN count(n) AS total_nodes
        }

        CALL () {
            MATCH ()-[r]->()
            RETURN count(r) AS total_relationships
        }

        CALL () {
            MATCH (n:Complaint)
            RETURN count(n) AS complaints
        }

        CALL () {
            MATCH (n:Phone)
            RETURN count(n) AS phones
        }

        CALL () {
            MATCH (n:UPI)
            RETURN count(n) AS upis
        }

        CALL () {
            MATCH (n:Email)
            RETURN count(n) AS emails
        }

        CALL () {
            MATCH (n:Organization)
            RETURN count(n) AS organizations
        }

        RETURN
            total_nodes,
            total_relationships,
            complaints,
            phones,
            upis,
            emails,
            organizations
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(query)

                record = await result.single()

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve network summary.",
            )

            raise GraphQueryError(
                "Failed to retrieve network summary.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if record is None:
            return NetworkSummaryResult(
                total_nodes=0,
                total_relationships=0,
                complaints=0,
                phones=0,
                upis=0,
                emails=0,
                organizations=0,
            )

        return NetworkSummaryResult(
            total_nodes=record["total_nodes"],
            total_relationships=record["total_relationships"],
            complaints=record["complaints"],
            phones=record["phones"],
            upis=record["upis"],
            emails=record["emails"],
            organizations=record["organizations"],
        )

    async def get_top_risk_entities(
        self,
        limit: int = 10,
    ) -> list[TopRiskEntityResult]:
        """
        Retrieve the highest-risk entities in the graph.
        """

        logger.debug(
            "Retrieving top risk entities.",
        )

        query = """
        MATCH (entity)
        WHERE NOT entity:Complaint

        OPTIONAL MATCH (entity)<-[:MENTIONS]-(incident:Complaint)

        WITH
            entity,
            count(DISTINCT incident) AS incident_count

        OPTIONAL MATCH (entity)--(neighbor)

        RETURN
            entity,
            labels(entity) AS labels,
            incident_count,
            count(DISTINCT neighbor) AS neighbor_count

        ORDER BY
            incident_count DESC,
            neighbor_count DESC

        LIMIT $limit
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    limit=limit,
                )

                entities = []

                async for record in result:
                    entities.append(
                        TopRiskEntityResult(
                            entity=self._map_node(
                                record["entity"],
                                record["labels"],
                            ),
                            incident_count=record["incident_count"],
                            neighbor_count=record["neighbor_count"],
                        )
                    )

                return entities

        except Neo4jError as exc:
            logger.exception(
                "Failed to retrieve top risk entities.",
            )

            raise GraphQueryError(
                "Failed to retrieve top risk entities.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Neo4j connection failed.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

    async def find_shortest_path(
        self,
        source: str,
        target: str,
    ) -> PathResult | None:
        """
        Find the shortest path between two entities.
        """

        logger.debug(
            "Finding shortest path from '{}' to '{}'.",
            source,
            target,
        )

        query = """
        MATCH (source {lookup_value: $source})
        MATCH (target {lookup_value: $target})

        MATCH path = shortestPath(
            (source)-[*..10]-(target)
        )

        RETURN
            nodes(path) AS nodes
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    source=source,
                    target=target,
                )

                record = await result.single()

        except Neo4jError as exc:
            logger.exception(
                "Shortest path query failed.",
            )

            raise GraphQueryError(
                "Failed to retrieve shortest path.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Neo4j connection failed.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        if record is None:
            return None

        graph_nodes = []

        for node in record["nodes"]:
            graph_nodes.append(
                self._map_node(
                    node,
                    list(node.labels),
                )
            )

        return PathResult(
            found=True,
            length=len(graph_nodes) - 1,
            nodes=graph_nodes,
        )

    async def find_shared_entity(
        self,
        value: str,
    ) -> SharedEntityResult | None:
        """
        Find all complaints connected to the supplied node.
        """

        logger.debug(
            "Finding complaints sharing entity '{}'.",
            value,
        )

        entity = await self.find_entity(value)

        if entity is None:
            return None

        try:
            complaints = await self._get_connected_complaints(entity)

        except Neo4jError as exc:
            logger.exception(
                "Shared entity query failed.",
            )

            raise GraphQueryError(
                "Failed to retrieve shared entity analysis.",
            ) from exc

        except GraphConnectionError:
            raise

        except Exception as exc:
            logger.exception(
                "Neo4j connection failed.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        return SharedEntityResult(
            entity=entity,
            complaints=complaints,
        )

    def _map_nodes(
        self,
        nodes: list[Any],
    ) -> list[GraphNode]:
        """
        Convert Neo4j nodes into GraphNode models.
        """

        return [
            self._map_node(
                node,
                list(node.labels),
            )
            for node in nodes
            if node is not None
        ]

    async def get_subgraph(
        self,
        node_id: str,
        depth: int = 2,
    ) -> list[Path]:
        """
        Retrieve a neighborhood subgraph centered around a graph node.

        Args:
            node_id:
                Graph node identifier (e.g. phone:+919876543210).

            depth:
                Maximum traversal depth.

        Returns:
            List of Neo4j Path objects.
        """
        logger.debug(
            "Fetching visualization subgraph for node '{}' (depth={}).",
            node_id,
            depth,
        )

        query = f"""
        MATCH (start {{id: $node_id}})
        MATCH path = (start)-[*1..{depth}]-(neighbor)
        WHERE ALL(
            node IN nodes(path)
            WHERE single(x IN nodes(path) WHERE x = node)
        )
        RETURN DISTINCT path
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                node_id=node_id,
            )

            paths: list[Path] = [record["path"] async for record in result]

        logger.debug(
            "Retrieved {} graph paths for node '{}'.",
            len(paths),
            node_id,
        )

        return paths

    async def get_graph_summary(
        self,
    ) -> GraphSummary:
        """
        Retrieve overall statistics about the fraud intelligence graph.

        Returns:
            GraphSummary containing node, relationship, and entity counts.
        """
        logger.debug(
            "Fetching graph summary statistics.",
        )

        query = """
        CALL {
            MATCH (n)
            RETURN count(n) AS total_nodes
        }

        CALL {
            MATCH ()-[r]->()
            RETURN count(r) AS total_edges
        }

        CALL {
            MATCH (n:Complaint)
            RETURN count(n) AS complaints
        }

        CALL {
            MATCH (n:Phone)
            RETURN count(n) AS phones
        }

        CALL {
            MATCH (n:Email)
            RETURN count(n) AS emails
        }

        CALL {
            MATCH (n:UPI)
            RETURN count(n) AS upis
        }

        CALL {
            MATCH (n:Organization)
            RETURN count(n) AS organizations
        }

        CALL {
            MATCH (n:Person)
            RETURN count(n) AS persons
        }

        CALL {
            MATCH (n:Location)
            RETURN count(n) AS locations
        }

        CALL {
            MATCH (n:BankAccount)
            RETURN count(n) AS bank_accounts
        }

        CALL {
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS degree
            RETURN avg(degree) AS average_degree
        }

        RETURN
            total_nodes,
            total_edges,
            complaints,
            phones,
            emails,
            upis,
            organizations,
            persons,
            locations,
            bank_accounts,
            coalesce(average_degree, 0.0) AS average_degree
        """

        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()

        if record is None:
            logger.warning(
                "Unable to retrieve graph summary statistics.",
            )

            return GraphSummary(
                total_nodes=0,
                total_edges=0,
                complaints=0,
                phones=0,
                emails=0,
                upis=0,
                organizations=0,
                persons=0,
                locations=0,
                bank_accounts=0,
                average_degree=0.0,
            )

        summary = GraphSummary(
            total_nodes=record["total_nodes"],
            total_edges=record["total_edges"],
            complaints=record["complaints"],
            phones=record["phones"],
            emails=record["emails"],
            upis=record["upis"],
            organizations=record["organizations"],
            persons=record["persons"],
            locations=record["locations"],
            bank_accounts=record["bank_accounts"],
            average_degree=round(record["average_degree"], 2),
        )

        logger.debug(
            "Graph summary statistics retrieved successfully.",
        )

        return summary

    async def get_top_connected_entities(
        self,
        limit: int = 10,
    ) -> list[TopConnectedEntity]:
        """
        Retrieve the most connected non-complaint entities.

        Args:
            limit:
                Maximum number of entities to return.

        Returns:
            Ranked list of connected entities.
        """
        logger.debug(
            "Fetching top connected entities (limit={}).",
            limit,
        )

        query = """
        MATCH (entity)
        WHERE NOT entity:Complaint

        OPTIONAL MATCH (entity)-[r]-()
        WITH
            entity,
            count(DISTINCT r) AS connection_count

        OPTIONAL MATCH (entity)<-[:MENTIONS]-(c:Complaint)
        WITH
            entity,
            connection_count,
            count(DISTINCT c) AS complaint_count

        RETURN
            entity,
            connection_count,
            complaint_count

        ORDER BY
            connection_count DESC,
            complaint_count DESC,
            entity.id

        LIMIT $limit
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                limit=limit,
            )

            records = [record async for record in result]

        entities: list[TopConnectedEntity] = []

        for record in records:
            node = record["entity"]

            properties = dict(node)
            labels = list(node.labels)

            entity_type = labels[0] if labels else "UNKNOWN"

            label = properties.get(
                "lookup_value",
                properties["id"],
            )

            entities.append(
                TopConnectedEntity(
                    id=properties["id"],
                    label=label,
                    type=entity_type,
                    connection_count=record["connection_count"],
                    complaint_count=record["complaint_count"],
                )
            )

        logger.debug(
            "Retrieved {} top connected entities.",
            len(entities),
        )

        return entities

    async def get_shared_entities(
        self,
        minimum_complaints: int = 2,
    ) -> list[SharedEntityAnalysis]:
        """
        Retrieve entities referenced by multiple complaints.

        Args:
            minimum_complaints:
                Minimum number of complaints sharing an entity.

        Returns:
            Shared entity analysis.
        """
        logger.debug(
            "Fetching shared entities (minimum_complaints={}).",
            minimum_complaints,
        )

        query = """
        MATCH (c:Complaint)-[:MENTIONS]->(entity)
        WHERE NOT entity:Complaint

        WITH
            entity,
            collect(DISTINCT c.id) AS complaint_ids,
            count(DISTINCT c) AS complaint_count

        WHERE complaint_count >= $minimum_complaints

        RETURN
            entity,
            complaint_count,
            complaint_ids

        ORDER BY
            complaint_count DESC,
            entity.id
        """

        async with self._driver.session() as session:
            result = await session.run(
                query,
                minimum_complaints=minimum_complaints,
            )

            records = [record async for record in result]

        shared_entities: list[SharedEntityAnalysis] = []

        for record in records:
            node = record["entity"]

            properties = dict(node)

            labels = list(node.labels)

            shared_entities.append(
                SharedEntityAnalysis(
                    entity_id=properties["id"],
                    entity_label=properties.get(
                        "lookup_value",
                        properties["id"],
                    ),
                    entity_type=labels[0] if labels else "UNKNOWN",
                    complaint_count=record["complaint_count"],
                    complaint_ids=record["complaint_ids"],
                )
            )

        logger.debug(
            "Retrieved {} shared entities.",
            len(shared_entities),
        )

        return shared_entities

    async def get_fraud_rings(
        self,
    ) -> list[FraudRingSummary]:
        """
        Detect connected fraud rings.

        Returns:
            Summary of each fraud ring.
        """

        logger.debug(
            "Detecting fraud rings.",
        )

        query = """
        MATCH (n)
        WHERE NOT n:Complaint

        CALL {
            WITH n
            MATCH (n)
            OPTIONAL MATCH (n)-[*]-(connected)
            WHERE NOT connected:Complaint
            RETURN collect(DISTINCT connected) + n AS component
        }

        WITH apoc.coll.toSet(component) AS component

        WITH DISTINCT component

        WHERE size(component) > 1

        UNWIND component AS entity

        OPTIONAL MATCH (entity)<-[:MENTIONS]-(c:Complaint)

        WITH
            component,
            collect(DISTINCT c) AS complaints

        WITH
            component,
            complaints,
            size(component) AS entity_count,
            size(complaints) AS complaint_count

        OPTIONAL MATCH (a)-[r]-(b)
        WHERE a IN component
        AND b IN component

        WITH
            component,
            entity_count,
            complaint_count,
            count(DISTINCT r) AS relationship_count

        RETURN
            toString(id(component[0])) AS ring_id,
            entity_count,
            complaint_count,
            relationship_count

        ORDER BY
            complaint_count DESC,
            entity_count DESC
        """

        try:
            async with self._driver.session() as session:
                result = await session.run(query)
                records = await result.data()

        except Neo4jError as exc:
            logger.exception(
                "Fraud ring detection failed.",
            )

            raise GraphQueryError(
                "Failed to detect fraud rings.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Neo4j connection failed.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        rings: list[FraudRingSummary] = []

        for record in records:
            entity_count = record["entity_count"]
            complaint_count = record["complaint_count"]
            relationship_count = record["relationship_count"]

            # Same scoring heuristic used elsewhere
            risk_score = min(
                100.0,
                complaint_count * 5 + entity_count * 2 + relationship_count,
            )

            rings.append(
                FraudRingSummary(
                    ring_id=record["ring_id"],
                    entity_count=entity_count,
                    complaint_count=complaint_count,
                    relationship_count=relationship_count,
                    risk_score=risk_score,
                )
            )

        return rings


    async def get_investigation_timeline_data(
        self,
        value: str,
    ) -> list[dict] | None:
        """
        Retrieve chronological complaint evidence for timeline reconstruction.

        Args:
            value:
                Lookup value of the investigation target.

        Returns:
            Chronological complaint evidence, or None if the target does not exist.

        Raises:
            GraphConnectionError:
                If Neo4j cannot be reached.

            GraphQueryError:
                If the graph query fails.
        """

        logger.debug(
            "Building investigation timeline for '{}'.",
            value,
        )

        entity = await self.find_entity(value)

        if entity is None:
            return None

        if entity.label == GraphLabel.COMPLAINT:
            query = """
            MATCH (target:Complaint {lookup_value:$value})
            MATCH (target)-[:MENTIONS]->(:Phone|UPI|Email|BankAccount|Organization|Person|Location|URL)<-[:MENTIONS]-(c:Complaint)
            WITH collect(DISTINCT target) + collect(DISTINCT c) AS complaints
            UNWIND complaints AS complaint
            OPTIONAL MATCH (complaint)-[:MENTIONS]->(e)
            RETURN DISTINCT
                complaint,
                labels(complaint) AS complaint_labels,
                complaint.created_at AS created_at,
                collect(DISTINCT e) AS entities
            ORDER BY created_at ASC
            """
        else:
            query = """
            MATCH (target {lookup_value:$value})
            MATCH (target)<-[:MENTIONS]-(complaint:Complaint)
            OPTIONAL MATCH (complaint)-[:MENTIONS]->(e)
            RETURN
                complaint,
                labels(complaint) AS complaint_labels,
                complaint.created_at AS created_at,
                collect(DISTINCT e) AS entities
            ORDER BY created_at ASC
            """

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    query,
                    value=value,
                )

                records = await result.data()

        except Neo4jError as exc:
            logger.exception(
                "Failed to build investigation timeline for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve investigation timeline.",
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unable to connect to Neo4j.",
            )

            raise GraphConnectionError(
                "Neo4j connection failed.",
            ) from exc

        timeline: list[dict] = []

        for record in records:
            timeline.append(
                {
                    "complaint": self._map_node(
                        node=record["complaint"],
                        labels=record["complaint_labels"],
                    ),
                    "created_at": record["created_at"],
                    "entities": self._map_nodes(
                        record["entities"],
                    ),
                }
            )

        return timeline
