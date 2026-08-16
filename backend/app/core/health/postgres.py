# app/core/health/postgres.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.health.base import BaseHealthChecker


class PostgresHealthChecker(BaseHealthChecker):
    """
    Health checker for PostgreSQL database connectivity.
    Executes a lightweight 'SELECT 1' query via the shared connection pool.
    """

    def __init__(
        self,
        engine: AsyncEngine | None = None,
        critical: bool = True,
        timeout: float = 2.0,
    ) -> None:
        super().__init__(name="postgres", critical=critical, timeout=timeout)
        self._engine = engine

    async def _check_health(self) -> None:
        from app.db.database import async_engine

        engine = self._engine or async_engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
