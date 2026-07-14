"""
Neo4j database configuration.

Provides lifecycle management for the Neo4j async driver.
"""

from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase
from loguru import logger

from app.core.config import settings

_driver: AsyncDriver | None = None


async def connect_neo4j() -> None:
    """
    Initialize the Neo4j driver.
    """
    global _driver

    if _driver is not None:
        return

    logger.info("Connecting to Neo4j...")

    _driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(
            settings.NEO4J_USERNAME,
            settings.NEO4J_PASSWORD.get_secret_value(),
        ),
    )

    await _driver.verify_connectivity()

    logger.success("Connected to Neo4j.")


async def disconnect_neo4j() -> None:
    """
    Close the Neo4j driver.
    """
    global _driver

    if _driver is None:
        return

    await _driver.close()

    _driver = None

    logger.info("Neo4j connection closed.")


def get_neo4j_driver() -> AsyncDriver:
    """
    Return the initialized Neo4j driver.

    Raises:
        RuntimeError:
            If Neo4j has not been initialized.
    """
    if _driver is None:
        raise RuntimeError("Neo4j driver has not been initialized.")

    return _driver
