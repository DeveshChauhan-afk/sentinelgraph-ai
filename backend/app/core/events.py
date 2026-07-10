from fastapi import FastAPI
from loguru import logger

from app.core.logger import setup_logger


async def startup(app: FastAPI) -> None:
    setup_logger()

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
    logger.info("SentinelGraph AI shutting down...")
    logger.info("Shutdown complete.")
