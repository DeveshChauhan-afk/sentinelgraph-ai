#app/scipts/rebuild_graph.py
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
from app.db.neo4j import connect_neo4j, disconnect_neo4j
from app.graph.builder import GraphBuilder
from app.graph.repository import GraphRepository
from app.repositories.incident import IncidentRepository
from app.services.entity_extraction_service import EntityExtractionService
from app.services.graph_service import GraphService
from app.core.config import settings

REQUEST_DELAY_SECONDS = 2


async def rebuild_graph() -> None:
    """
    Rebuild the Neo4j graph from all stored complaints.
    """
    await connect_neo4j()

    try:
        repository = GraphRepository()

        # Task 1: Clear Neo4j graph
        await repository.clear_graph()

        logger.info("Rebuilding graph...")

        total_nodes_persisted = 0
        total_relationships_persisted = 0
        success = 0
        failed = 0

        async with AsyncSessionLocal() as session:
            incident_repository = IncidentRepository(session)
            incidents = await incident_repository.get_all()
            total = len(incidents)

            logger.info(
                "Found {} complaints to process.",
                total,
            )

            ai_client = GeminiClient(settings=settings)
            entity_service = EntityExtractionService(
                ai_client=ai_client,
            )
            graph_service = GraphService(
                builder=GraphBuilder(),
                repository=repository,
            )

            for index, incident in enumerate(incidents, start=1):
                logger.info("Processed {}/{}", index, total)

                try:
                    entities = await entity_service.extract_entities(
                        incident.description,
                    )

                    result = await graph_service.build_and_save_graph(
                        complaint_id=incident.id,
                        created_at=incident.created_at,
                        entities=entities,
                    )

                    if result:
                        total_nodes_persisted += result.nodes_persisted
                        total_relationships_persisted += result.relationships_persisted

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

                await asyncio.sleep(REQUEST_DELAY_SECONDS)

        logger.info("=" * 60)
        logger.success("Graph rebuild completed.")
        logger.info("Nodes persisted: {}", total_nodes_persisted)
        logger.info("Relationships persisted: {}", total_relationships_persisted)
        logger.info("Total complaints : {}", total)
        logger.info("Successful       : {}", success)
        logger.info("Failed           : {}", failed)
        logger.info("=" * 60)

        # Task 4: Validation
        complaints_count, timestamps_count = await repository.verify_complaint_timestamps()
        logger.info("Complaint nodes: {}", complaints_count)
        logger.info("Complaint timestamps: {}", timestamps_count)

        if complaints_count != timestamps_count:
            raise ValueError(
                f"Timestamp verification failed: Complaint nodes ({complaints_count}) "
                f"do not match Complaint timestamps ({timestamps_count})."
            )

        # Task 5: Final Verification
        sample_timestamps = await repository.get_sample_complaint_timestamps(limit=5)
        logger.info("First 5 complaint timestamps:")
        for lookup_val, ts in sample_timestamps:
            logger.info("  Complaint {} -> {}", lookup_val, ts)

    finally:
        await disconnect_neo4j()


def main() -> None:
    asyncio.run(rebuild_graph())


if __name__ == "__main__":
    main()

