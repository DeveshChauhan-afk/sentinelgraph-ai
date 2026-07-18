"""
Performance timing utilities for investigation pipeline.
"""

from __future__ import annotations

from time import perf_counter

from loguru import logger


class InvestigationTimer:
    """
    Utility for measuring investigation performance.
    """

    def __init__(self) -> None:
        self._marks: dict[str, float] = {}
        self._start = perf_counter()

    def start(self, stage: str) -> None:
        self._marks[stage] = perf_counter()

    def stop(self, stage: str) -> None:
        if stage in self._marks:
            self._marks[stage] = (
                perf_counter() - self._marks[stage]
            ) * 1000

    def summary(self) -> None:
        total = (perf_counter() - self._start) * 1000

        logger.info("")
        logger.info("=" * 55)
        logger.info("Investigation Performance")
        logger.info("=" * 55)

        for stage, duration in self._marks.items():
            logger.info("{:<20}: {:>8.2f} ms", stage, duration)

        logger.info("-" * 55)
        logger.info("{:<20}: {:>8.2f} ms", "Total", total)
        logger.info("=" * 55)