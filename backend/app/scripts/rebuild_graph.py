"""
Rebuild the Neo4j Fraud Intelligence Graph from PostgreSQL complaints.

Usage:
    python -m app.scripts.rebuild_graph
"""

from __future__ import annotations

import asyncio

from loguru import logger

from app.ai.client import GeminiClient
from app.db.database import AsyncSessionLocal
from app.graph.builder import GraphBuilder
from app.graph.repository import GraphRepository
from app.graph.service import GraphService
from app.repositories.incident import IncidentRepository
from app.services.entity_extraction_service import EntityExtractionService

REQUEST_DELAY_SECONDS = 2


async def rebuild_graph() -> None:
    """
    Rebuild the Neo4j graph from all stored complaints.
    """

    logger.info("Starting graph rebuild...")

    success = 0
    failed = 0

    async with AsyncSessionLocal() as session:

        incident_repository = IncidentRepository(session)

        incidents = await incident_repository.get_all()

        logger.info(
            "Found {} complaints to process.",
            len(incidents),
        )

        ai_client = GeminiClient()

        entity_service = EntityExtractionService(
            ai_client=ai_client,
        )

        graph_service = GraphService(
            builder=GraphBuilder(),
            repository=GraphRepository(),
        )

        total = len(incidents)

        for index, incident in enumerate(incidents, start=1):

            logger.info(
                "[{}/{}] Processing complaint {}",
                index,
                total,
                incident.id,
            )

            try:

                entities = await entity_service.extract_entities(
                    incident.description,
                )

                await graph_service.build_and_save_graph(
                    complaint_id=incident.id,
                    entities=entities,
                )

                success += 1

                logger.success(
                    "Complaint {} processed successfully.",
                    incident.id,
                )

            except Exception:

                failed += 1

                logger.exception(
                    "Failed to rebuild graph for complaint {}",
                    incident.id,
                )

            await asyncio.sleep(
                REQUEST_DELAY_SECONDS,
            )

    logger.info("=" * 60)
    logger.success("Graph rebuild completed.")
    logger.info("Total complaints : {}", total)
    logger.info("Successful       : {}", success)
    logger.info("Failed           : {}", failed)
    logger.info("=" * 60)


def main() -> None:
    asyncio.run(rebuild_graph())


if __name__ == "__main__":
    main()
