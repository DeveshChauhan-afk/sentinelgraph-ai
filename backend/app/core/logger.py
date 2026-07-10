# app/core/logger.py

import sys
from pathlib import Path
from loguru import logger as loguru_logger
from typing import Any

# Define log directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

# Define standard format
# Format: Time | Level | Module | Function | Line | Message
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger() -> None:
    """
    Configures the global logger with console and rotating file handlers.
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
        level="INFO",
        colorize=True,
        catch=True,
        diagnose=True,
        backtrace=True,
    )

    # Add Rotating File Handler
    loguru_logger.add(
        LOG_FILE,
        format=LOG_FORMAT,
        level="INFO",
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
