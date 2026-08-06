# app/core/logger.py

import sys
from pathlib import Path
from typing import Any

from loguru import logger as loguru_logger

from app.core.config import settings

# Define log directory and file path (no filesystem side-effects during import)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Define standard format
# Format: Time | Level | Module | Function | Line | Message
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger() -> None:
    """
    Configures the global logger with console and optional rotating file handlers.
    Should be called once during application startup.
    """
    # Remove default handler
    loguru_logger.remove()

    # Add Console Handler (Colorful)
    loguru_logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{module}</cyan> | "
            "<cyan>{function}</cyan> | "
            "<cyan>{line}</cyan> | "
            "{message}"
        ),
        level=settings.LOG_LEVEL,
        colorize=True,
        catch=True,
        diagnose=True,
        backtrace=True,
    )

    # Add Rotating File Handler conditionally based on configuration
    if settings.LOG_TO_FILE:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(
            LOG_FILE,
            format=LOG_FORMAT,
            level=settings.LOG_LEVEL,
            rotation="1 day",
            retention="7 days",
            compression="zip",
            enqueue=True,  # Ensure thread safety for async apps
            catch=True,
            diagnose=True,
            backtrace=True,
        )

    loguru_logger.info("Logger initialized.")


def get_logger(module_name: str) -> Any:
    """
    Returns a logger instance bound to a specific module name.
    Useful for tracking the source of logs in larger applications.
    """
    return loguru_logger.bind(module=module_name)
