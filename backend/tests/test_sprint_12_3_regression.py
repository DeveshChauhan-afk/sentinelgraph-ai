"""
Regression and integrity tests for Sprint 12.3: Neo4j Schema Hardening:
1. Neo4j uniqueness constraints cover all 9 persisted node labels on the 'id' property.
2. Idempotent schema initialization via init_neo4j_schema.
3. Schema initialization error handling (surfacing Neo4jError and connection failures).
4. Startup lifecycle integration (init_neo4j_schema runs after connect_neo4j).
5. Graph persistence preserves the only valid relationship: (:Complaint)-[:MENTIONS]->(:Entity).
6. Idempotent MERGE behavior on node identity 'id' is preserved.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from neo4j.exceptions import Neo4jError

from app.core.events import startup
from app.db.neo4j_schema import NEO4J_CONSTRAINTS, init_neo4j_schema
from app.graph.builder import GraphBuilder
from app.graph.exceptions import (
    GraphConnectionError,
    GraphPersistenceError,
)
from app.graph.models import (
    GraphLabel,
    GraphNode,
    GraphRelationship,
    RelationshipType,
)
from app.graph.repository import GraphRepository
from app.main import app
from app.schemas.entity_extraction import (
    ExtractedEntities,
    ExtractedEntity,
)


# ============================================================================
# 1. Node Identity Model & Constraint Inventory Tests
# ============================================================================


def test_neo4j_constraints_cover_all_persisted_node_labels() -> None:
    """
    Ensure every persisted node label in GraphLabel has a corresponding
    uniqueness constraint on property 'id' in NEO4J_CONSTRAINTS.
    """
    all_labels = list(GraphLabel)
    assert len(all_labels) == 9

    for label in all_labels:
        # Find matching constraint for this label
        matching = [
            (name, cypher)
            for name, cypher in NEO4J_CONSTRAINTS.items()
            if f":{label.value}" in cypher
        ]
        assert len(matching) == 1, f"Missing uniqueness constraint for label '{label.value}'"
        constraint_name, cypher = matching[0]

        # Verify Cypher syntax invariant
        assert "CREATE CONSTRAINT" in cypher
        assert "IF NOT EXISTS" in cypher
        assert f"FOR (n:{label.value})" in cypher
        assert "REQUIRE n.id IS UNIQUE" in cypher


# ============================================================================
# 2. Schema Initialization & Idempotency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_init_neo4j_schema_applies_all_constraints() -> None:
    """
    Ensure init_neo4j_schema executes all 9 constraints on the active driver session.
    """
    mock_session = AsyncMock()
    mock_session.run = AsyncMock()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    applied = await init_neo4j_schema(driver=mock_driver)

    assert len(applied) == 9
    assert mock_session.run.await_count == 9

    # Verify each Cypher statement was executed
    executed_statements = [call.args[0] for call in mock_session.run.await_args_list]
    for cypher in NEO4J_CONSTRAINTS.values():
        assert cypher in executed_statements


@pytest.mark.asyncio
async def test_init_neo4j_schema_is_idempotent() -> None:
    """
    Ensure init_neo4j_schema can safely execute multiple times without error.
    """
    mock_session = AsyncMock()
    mock_session.run = AsyncMock()

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    # Run twice
    first_run = await init_neo4j_schema(driver=mock_driver)
    second_run = await init_neo4j_schema(driver=mock_driver)

    assert first_run == second_run
    assert len(first_run) == 9
    assert mock_session.run.await_count == 18


# ============================================================================
# 3. Schema Initialization Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_init_neo4j_schema_surfaces_neo4j_error() -> None:
    """
    Ensure database-level Neo4jError is surfaced as GraphPersistenceError.
    """
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=Neo4jError("Syntax error or permission denied"))

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    with pytest.raises(GraphPersistenceError, match="Neo4j schema constraint initialization failed"):
        await init_neo4j_schema(driver=mock_driver)


@pytest.mark.asyncio
async def test_init_neo4j_schema_surfaces_connection_failure() -> None:
    """
    Ensure connectivity failure is surfaced as GraphConnectionError.
    """
    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__.side_effect = ConnectionRefusedError("Cannot reach Neo4j")

    with pytest.raises(GraphConnectionError, match="Neo4j connection failed"):
        await init_neo4j_schema(driver=mock_driver)


# ============================================================================
# 4. Lifecycle Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_startup_lifecycle_executes_connect_and_schema_init() -> None:
    """
    Ensure application startup invokes connect_neo4j followed by init_neo4j_schema.
    """
    with (
        patch("app.core.events.connect_neo4j", new_callable=AsyncMock) as mock_connect,
        patch("app.core.events.init_neo4j_schema", new_callable=AsyncMock) as mock_init_schema,
    ):
        await startup(app)

        mock_connect.assert_awaited_once()
        mock_init_schema.assert_awaited_once()


# ============================================================================
# 5. Graph Ingestion, Relationship Preservation & MERGE Invariant Tests
# ============================================================================


def test_graph_builder_persists_only_mentions_relationship_for_all_entities() -> None:
    """
    Critical Invariant Test:
    Verify that GraphBuilder creates ONLY (:Complaint)-[:MENTIONS]->(:Entity) relationships
    and never creates forbidden relationship types (e.g. REPORTED_IN, ASSOCIATED_WITH, TRANSFERRED_TO).
    """
    complaint_id = uuid4()
    created_at = datetime.now(timezone.utc)

    entities = ExtractedEntities(
        phone_numbers=[ExtractedEntity(value="+919876543210", confidence=0.99)],
        upi_ids=[ExtractedEntity(value="scam@okaxis", confidence=0.95)],
        emails=[ExtractedEntity(value="scammer@fraud.com", confidence=0.90)],
        urls=[ExtractedEntity(value="https://phishing.example.com", confidence=0.92)],
        bank_accounts=[ExtractedEntity(value="987654321098", confidence=0.88)],
        organizations=[ExtractedEntity(value="FakeBank Ltd", confidence=0.85)],
        persons=[ExtractedEntity(value="John Scammer", confidence=0.80)],
        locations=[ExtractedEntity(value="New Delhi", confidence=0.75)],
    )

    builder = GraphBuilder()
    graph = builder.build(complaint_id, created_at, entities)

    # 1 Complaint + 8 Entities = 9 nodes
    assert len(graph.nodes) == 9
    assert len(graph.relationships) == 8

    # Verify every node has a stable, non-empty id property
    for node in graph.nodes:
        assert node.id.strip() != ""
        assert ":" in node.id  # e.g., 'complaint:...', 'phone:...', 'upi:...'

    # Verify every relationship is MENTIONS from Complaint to Entity
    complaint_node_id = f"complaint:{complaint_id}"
    for rel in graph.relationships:
        assert rel.type == RelationshipType.MENTIONS
        assert rel.type.value == "MENTIONS"
        assert rel.source == complaint_node_id
        assert rel.target != complaint_node_id


@pytest.mark.asyncio
async def test_repository_merge_node_preserves_id_invariant() -> None:
    """
    Ensure GraphRepository._merge_node uses MERGE with the node 'id' property.
    """
    mock_driver = MagicMock()
    repo = GraphRepository(driver=mock_driver)

    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock()

    node = GraphNode(
        id="phone:+919876543210",
        label=GraphLabel.PHONE,
        properties={"value": "+919876543210", "lookup_value": "+919876543210"},
    )

    await repo._merge_node(mock_tx, node)

    mock_tx.run.assert_awaited_once()
    cypher_executed = mock_tx.run.await_args[0][0]

    assert "MERGE (n:Phone {id: $id})" in cypher_executed
    assert "SET n += $properties" in cypher_executed


@pytest.mark.asyncio
async def test_repository_merge_relationship_preserves_mentions_type() -> None:
    """
    Ensure GraphRepository._merge_relationship uses MERGE with MENTIONS type.
    """
    mock_driver = MagicMock()
    repo = GraphRepository(driver=mock_driver)

    mock_tx = AsyncMock()
    mock_tx.run = AsyncMock()

    rel = GraphRelationship(
        source="complaint:11111111-1111-1111-1111-111111111111",
        target="phone:+919876543210",
        type=RelationshipType.MENTIONS,
        properties={},
    )

    await repo._merge_relationship(
        tx=mock_tx,
        relationship=rel,
        source_label=GraphLabel.COMPLAINT,
        target_label=GraphLabel.PHONE,
    )

    mock_tx.run.assert_awaited_once()
    cypher_executed = mock_tx.run.await_args[0][0]

    assert "MATCH (source:Complaint {id: $source_id})" in cypher_executed
    assert "MATCH (target:Phone {id: $target_id})" in cypher_executed
    assert "MERGE (source)-[r:MENTIONS]->(target)" in cypher_executed
