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
    IncidentQueryResult,
    TopRiskEntityResult,
)

from app.graph.query_results import (
    NeighborQueryResult,
    IncidentQueryResult,
    RiskMetricsResult,
)
from app.graph.query_results import FraudRingResult
from app.graph.query_results import NetworkSummaryResult

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

    '''async def find_entity(
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
        WHERE n.value = $value
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

            raise GraphPersistenceError("Failed to query graph entity.") from exc

        except Exception as exc:
            logger.exception("Unable to connect to Neo4j.")

            raise GraphConnectionError("Neo4j connection failed.") from exc

        if record is None:
            logger.debug(
                "No graph entity found for '{}'.",
                value,
            )
            return None

        node = record["n"]
        labels = record["labels"]

        if not labels:
            logger.warning(
                "Graph node '{}' has no labels.",
                node["id"],
            )
            return None

        properties = dict(node)
        properties.pop("id", None)

        return GraphNode(
            id=node["id"],
            label=GraphLabel(labels[0]),
            properties=properties,
        )'''

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
        WHERE n.value = $value
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
        MATCH (entity {value: $value})
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
    Retrieve all complaint nodes connected to an entity.

    Args:
        value:
            Entity value (phone number, UPI ID, email, etc.).

    Returns:
        RelatedIncidentsResponse if the entity exists, otherwise None.

    Raises:
        GraphConnectionError:
            If a Neo4j connection cannot be established.

        GraphQueryError:
            If the graph query fails.
    """
        logger.debug(
            "Finding related incidents for entity '{}'.",
            value,
        )

        query = """
        MATCH (entity {value: $value})
        OPTIONAL MATCH (entity)-[:MENTIONS]-(incident:Complaint)

        RETURN entity,
            labels(entity) AS entity_labels,
            collect({
               node: incident,
               labels: labels(incident)
           }) AS incidents
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
                "Failed to retrieve related incidents for '{}'.",
                value,
            )

            raise GraphQueryError(
                "Failed to retrieve related incidents.",
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

        incidents: list[GraphNode] = []

        for item in record["incidents"]:
            node = item["node"]

            if node is None:
                continue

            incidents.append(
                self._map_node(
                    node=node,
                    labels=item["labels"],
                )
            )

        return IncidentQueryResult (
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

        Args:
            value:
                Entity value (phone number, UPI ID, email, etc.).

        Returns:
            RiskMetricsResult if the entity exists, otherwise None.

        Raises:
            GraphConnectionError:
                If a Neo4j connection cannot be established.

            GraphQueryError:
                If the query execution fails.
        """
        logger.debug(
            "Retrieving risk metrics for entity '{}'.",
            value,
        )

        query = """
        MATCH (entity {value: $value})

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[]-(neighbor)
            RETURN count(DISTINCT neighbor) AS neighbor_count
        }

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[:MENTIONS]-(incident:Complaint)
            RETURN count(DISTINCT incident) AS incident_count
        }

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[]-(phone:Phone)
            RETURN count(DISTINCT phone) AS phone_count
        }

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[]-(upi:UPI)
            RETURN count(DISTINCT upi) AS upi_count
        }

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[]-(email:Email)
            RETURN count(DISTINCT email) AS email_count
        }

        CALL () {
            WITH entity
            OPTIONAL MATCH (entity)-[]-(organization:Organization)
            RETURN count(DISTINCT organization) AS organization_count
        }

        RETURN
            entity,
            labels(entity) AS entity_labels,
            incident_count,
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

        return RiskMetricsResult(
            entity=entity,
            incident_count=record["incident_count"],
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
        MATCH (entity {value:$value})

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
