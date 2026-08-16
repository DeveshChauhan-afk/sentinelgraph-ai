"""
Health service module for SentinelGraph AI.

Provides production-grade dependency checks for PostgreSQL, Neo4j,
and Gemini API configuration for cloud-native liveness and readiness probes.
"""

from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import get_logger
from app.db.neo4j import get_neo4j_driver

logger = get_logger(__name__)


class HealthService:
    """
    Service encapsulating health check logic for application dependencies.
    """

    @staticmethod
    def check_liveness() -> Dict[str, str]:
        """
        Process liveness check. Always returns healthy as long as the
        FastAPI process is running. Does not touch external services.
        """
        return {"status": "healthy"}

    @staticmethod
    async def check_postgres(db: AsyncSession | None = None) -> bool:
        """
        Executes lightweight SELECT 1 query on PostgreSQL.
        """
        try:
            if db is not None:
                await db.execute(text("SELECT 1"))
            else:
                from app.db.database import AsyncSessionLocal

                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning(f"PostgreSQL health check failed: {exc}")
            return False

    @staticmethod
    async def check_neo4j() -> bool:
        """
        Verifies connectivity to Neo4j graph database using driver verification.
        """
        try:
            driver = get_neo4j_driver()
            await driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning(f"Neo4j health check failed: {exc}")
            return False

    @staticmethod
    def check_gemini() -> bool:
        """
        Verifies Gemini API key configuration exists without calling external API.
        """
        try:
            if (
                settings.GEMINI_API_KEY
                and settings.GEMINI_API_KEY.get_secret_value()
                and settings.GEMINI_API_KEY.get_secret_value() != "your_gemini_api_key_here"
            ):
                return True
            return False
        except Exception as exc:
            logger.warning(f"Gemini configuration check failed: {exc}")
            return False

    @classmethod
    async def check_readiness(cls, db: AsyncSession | None = None) -> Dict[str, Any]:
        """
        Checks readiness of required dependencies.
        Returns readiness status dict and boolean indicating overall health.
        """
        postgres_ok = await cls.check_postgres(db)
        neo4j_ok = await cls.check_neo4j()
        gemini_ok = cls.check_gemini()

        is_ready = postgres_ok and neo4j_ok and gemini_ok

        return {
            "is_ready": is_ready,
            "details": {
                "postgres": "healthy" if postgres_ok else "unhealthy",
                "neo4j": "healthy" if neo4j_ok else "unhealthy",
                "gemini": "configured" if gemini_ok else "not_configured",
            },
        }

    @classmethod
    async def get_health_summary(cls, db: AsyncSession | None = None) -> Dict[str, Any]:
        """
        Provides detailed operational health summary.
        """
        readiness = await cls.check_readiness(db)
        is_healthy = readiness["is_ready"]

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "dependencies": readiness["details"],
        }
