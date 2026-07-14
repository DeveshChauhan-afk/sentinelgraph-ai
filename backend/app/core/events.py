from fastapi import FastAPI
from loguru import logger
from app.db.neo4j import connect_neo4j
from app.core.logger import setup_logger
from app.db.neo4j import disconnect_neo4j


async def startup(app: FastAPI) -> None:
    setup_logger()
    await connect_neo4j()
    banner = """
==================================================
SentinelGraph AI - Digital Public Safety Platform
Status: ONLINE
==================================================
"""

    logger.info(banner)
    logger.info("Configuration validation complete.")
    logger.info("Application ready.")


async def shutdown(app: FastAPI) -> None:
    await disconnect_neo4j()
    logger.info("SentinelGraph AI shutting down...")
    logger.info("Shutdown complete.")
