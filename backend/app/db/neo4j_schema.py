"""
Neo4j schema constraints and index initialization.

Provides idempotent initialization of database-level uniqueness constraints
for all persisted graph node labels in the Fraud Intelligence Graph.
"""

from __future__ import annotations

from typing import Mapping
from loguru import logger
from neo4j import AsyncDriver
from neo4j.exceptions import Neo4jError

from app.db.neo4j import get_neo4j_driver
from app.graph.exceptions import (
    GraphConnectionError,
    GraphPersistenceError,
)
from app.graph.models import GraphLabel


# Map of constraint name -> Cypher statement for every persisted node label
NEO4J_CONSTRAINTS: Mapping[str, str] = {
    "uq_complaint_id": f"CREATE CONSTRAINT uq_complaint_id IF NOT EXISTS FOR (n:{GraphLabel.COMPLAINT.value}) REQUIRE n.id IS UNIQUE",
    "uq_phone_id": f"CREATE CONSTRAINT uq_phone_id IF NOT EXISTS FOR (n:{GraphLabel.PHONE.value}) REQUIRE n.id IS UNIQUE",
    "uq_upi_id": f"CREATE CONSTRAINT uq_upi_id IF NOT EXISTS FOR (n:{GraphLabel.UPI.value}) REQUIRE n.id IS UNIQUE",
    "uq_email_id": f"CREATE CONSTRAINT uq_email_id IF NOT EXISTS FOR (n:{GraphLabel.EMAIL.value}) REQUIRE n.id IS UNIQUE",
    "uq_url_id": f"CREATE CONSTRAINT uq_url_id IF NOT EXISTS FOR (n:{GraphLabel.URL.value}) REQUIRE n.id IS UNIQUE",
    "uq_bank_account_id": f"CREATE CONSTRAINT uq_bank_account_id IF NOT EXISTS FOR (n:{GraphLabel.BANK_ACCOUNT.value}) REQUIRE n.id IS UNIQUE",
    "uq_organization_id": f"CREATE CONSTRAINT uq_organization_id IF NOT EXISTS FOR (n:{GraphLabel.ORGANIZATION.value}) REQUIRE n.id IS UNIQUE",
    "uq_person_id": f"CREATE CONSTRAINT uq_person_id IF NOT EXISTS FOR (n:{GraphLabel.PERSON.value}) REQUIRE n.id IS UNIQUE",
    "uq_location_id": f"CREATE CONSTRAINT uq_location_id IF NOT EXISTS FOR (n:{GraphLabel.LOCATION.value}) REQUIRE n.id IS UNIQUE",
}


async def init_neo4j_schema(driver: AsyncDriver | None = None) -> list[str]:
    """
    Initialize Neo4j database schema constraints.

    Ensures all persisted node labels have database-enforced uniqueness
    constraints on their primary 'id' property. The operation is idempotent
    and safe to run repeatedly.

    Args:
        driver:
            Optional AsyncDriver instance. If omitted, uses get_neo4j_driver().

    Returns:
        List of constraint names successfully initialized.

    Raises:
        GraphConnectionError:
            If a connection to Neo4j cannot be established.
        GraphPersistenceError:
            If constraint creation fails.
    """
    active_driver = driver or get_neo4j_driver()
    applied_constraints: list[str] = []

    logger.info("Initializing Neo4j schema constraints...")

    try:
        async with active_driver.session() as session:
            for constraint_name, cypher in NEO4J_CONSTRAINTS.items():
                logger.debug("Applying Neo4j constraint '{}'...", constraint_name)
                await session.run(cypher)
                applied_constraints.append(constraint_name)

        logger.success(
            "Neo4j schema constraints initialized ({} constraints).",
            len(applied_constraints),
        )
        return applied_constraints

    except Neo4jError as exc:
        logger.exception("Failed to initialize Neo4j schema constraints.")
        raise GraphPersistenceError(
            f"Neo4j schema constraint initialization failed: {exc}"
        ) from exc
    except Exception as exc:
        logger.exception("Unable to connect to Neo4j for schema initialization.")
        raise GraphConnectionError(
            "Neo4j connection failed during schema initialization."
        ) from exc
