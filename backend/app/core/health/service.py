# app/core/health/service.py

import asyncio
from typing import Iterable

from app.core.health.base import BaseHealthChecker
from app.core.health.models import DependencyHealth, HealthStatus


class HealthService:
    """
    Orchestrates concurrent execution of registered dependency health checkers
    and computes aggregate status and traffic readiness.
    """

    def __init__(
        self,
        checkers: Iterable[BaseHealthChecker] | None = None,
    ) -> None:
        if checkers is not None:
            self._checkers = list(checkers)
        else:
            from app.core.health.gemini import GeminiConfigHealthChecker
            from app.core.health.neo4j import Neo4jHealthChecker
            from app.core.health.postgres import PostgresHealthChecker

            self._checkers = [
                PostgresHealthChecker(),
                Neo4jHealthChecker(),
                GeminiConfigHealthChecker(),
            ]

    async def check_dependencies(self) -> dict[str, DependencyHealth]:
        """
        Executes all registered dependency health checks concurrently.

        Returns:
            dict[str, DependencyHealth]: Mapping of dependency name to health record.
        """
        if not self._checkers:
            return {}

        results: list[DependencyHealth] = await asyncio.gather(
            *[checker.check() for checker in self._checkers]
        )
        return {res.name: res for res in results}

    @staticmethod
    def determine_status(dependencies: dict[str, DependencyHealth]) -> HealthStatus:
        """
        Evaluates overall application health status from dependency states:
        - UNHEALTHY: If ANY critical dependency is not HEALTHY.
        - DEGRADED: If ALL critical dependencies are HEALTHY, but >= 1 non-critical dependency is not HEALTHY.
        - HEALTHY: If ALL dependencies are HEALTHY (or if dependency map is empty).
        """
        if not dependencies:
            return HealthStatus.HEALTHY

        has_critical_failure = any(
            dep.status != HealthStatus.HEALTHY
            for dep in dependencies.values()
            if dep.critical
        )
        if has_critical_failure:
            return HealthStatus.UNHEALTHY

        has_non_critical_failure = any(
            dep.status != HealthStatus.HEALTHY
            for dep in dependencies.values()
            if not dep.critical
        )
        if has_non_critical_failure:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    @staticmethod
    def determine_readiness(dependencies: dict[str, DependencyHealth]) -> bool:
        """
        Determines if the application instance can safely accept user traffic:
        - True: If ALL critical dependencies are HEALTHY (or if dependency map is empty).
        - False: If ANY critical dependency is not HEALTHY.

        Non-critical dependencies (e.g. Gemini) have ZERO impact on readiness.
        """
        if not dependencies:
            return True

        return all(
            dep.status == HealthStatus.HEALTHY
            for dep in dependencies.values()
            if dep.critical
        )
