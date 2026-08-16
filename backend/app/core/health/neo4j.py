# app/core/health/neo4j.py

from typing import Callable
from neo4j import AsyncDriver

from app.core.health.base import BaseHealthChecker


class Neo4jHealthChecker(BaseHealthChecker):
    """
    Health checker for Neo4j graph database connectivity.
    Uses the shared AsyncDriver to verify cluster/instance connectivity.
    """

    def __init__(
        self,
        driver_getter: Callable[[], AsyncDriver] | None = None,
        critical: bool = True,
        timeout: float = 2.0,
    ) -> None:
        super().__init__(name="neo4j", critical=critical, timeout=timeout)
        self._driver_getter = driver_getter

    async def _check_health(self) -> None:
        from app.db.neo4j import get_neo4j_driver

        getter = self._driver_getter or get_neo4j_driver
        driver = getter()
        await driver.verify_connectivity()
