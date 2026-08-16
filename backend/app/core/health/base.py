# app/core/health/base.py

import asyncio
import time
from abc import ABC, abstractmethod

from app.core.health.models import DependencyHealth, HealthStatus
from app.core.logger import get_logger

logger = get_logger(__name__)


class BaseHealthChecker(ABC):
    """
    Abstract base class for dependency health checkers.
    """

    def __init__(
        self,
        name: str,
        critical: bool = True,
        timeout: float = 2.0,
    ) -> None:
        self.name = name
        self.critical = critical
        self.timeout = timeout

    @abstractmethod
    async def _check_health(self) -> None:
        """
        Subclasses implement dependency-specific check logic.
        Completing without exception indicates HEALTHY status.
        """
        pass

    async def check(self) -> DependencyHealth:
        """
        Executes check with timeout enforcement, latency measurement,
        and exception containment.
        """
        start_time = time.perf_counter()

        try:
            await asyncio.wait_for(self._check_health(), timeout=self.timeout)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return DependencyHealth(
                name=self.name,
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                critical=self.critical,
                message=None,
            )

        except asyncio.TimeoutError:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "Health check timed out for dependency '{}' after {}s",
                self.name,
                self.timeout,
            )
            return DependencyHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                critical=self.critical,
                message="Operation timed out",
            )

        except Exception:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Health check failed unexpectedly for dependency '{}'",
                self.name,
            )
            return DependencyHealth(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                critical=self.critical,
                message="Service check failed",
            )
