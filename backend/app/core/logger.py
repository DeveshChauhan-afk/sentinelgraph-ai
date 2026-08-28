from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger as loguru_logger

from app.core.config import Settings, settings
from app.core.context import get_request_id

# Define log directory and file path (no filesystem side-effects during import)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Define standard format
# Format: Time | Level | [Request ID] | Module:Function:Line - Message
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "[{extra[request_id]}] | "
    "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def _correlation_patcher(record: dict) -> None:
    """
    Injects the active request correlation ID from contextvars into Loguru records.
    """
    req_id = get_request_id()
    record["extra"]["request_id"] = req_id if req_id else "-"


def setup_logger(cfg: Settings | None = None) -> None:
    """
    Configures the global logger with console and optional rotating file handlers.
    Should be called once during application startup.

    In production (DEBUG=False), `diagnose` is disabled to prevent leaking local
    variable values in exception tracebacks, while `backtrace=True` is preserved
    to ensure complete and actionable stack traces.
    """
    active_settings = cfg or settings

    # Remove default handler
    loguru_logger.remove()

    # Configure global patcher for correlation ID propagation
    loguru_logger.configure(patcher=_correlation_patcher)

    # In production (DEBUG=False), diagnose must be False to prevent local variable exposure
    diagnose_mode = bool(active_settings.DEBUG)
    backtrace_mode = True

    # Add Console Handler (Colorful)
    loguru_logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<yellow>{extra[request_id]}</yellow> | "
            "<cyan>{module}</cyan> | "
            "<cyan>{function}</cyan> | "
            "<cyan>{line}</cyan> | "
            "{message}"
        ),
        level=active_settings.LOG_LEVEL,
        colorize=True,
        catch=True,
        diagnose=diagnose_mode,
        backtrace=backtrace_mode,
    )

    # Add Rotating File Handler conditionally based on configuration
    if active_settings.LOG_TO_FILE:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(
            LOG_FILE,
            format=LOG_FORMAT,
            level=active_settings.LOG_LEVEL,
            rotation="1 day",
            retention="7 days",
            compression="zip",
            enqueue=True,  # Ensure thread safety for async apps
            catch=True,
            diagnose=diagnose_mode,
            backtrace=backtrace_mode,
        )

    loguru_logger.info("Logger initialized.")


def get_logger(module_name: str) -> Any:
    """
    Returns a logger instance bound to a specific module name.
    Useful for tracking the source of logs in larger applications.
    """
    return loguru_logger.bind(module=module_name)
