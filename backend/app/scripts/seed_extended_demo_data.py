# app/scripts/seed_extended_demo_data.py
"""
Fast demo-data seeding engine for SentinelGraph AI.

Performs high-velocity, deterministic bulk ingestion into PostgreSQL and Neo4j:
- Completely offline: Zero Gemini API calls.
- Reuses existing domain models: IncidentRepository, GraphBuilder, GraphRepository, ExtractedEntities.
- Supports precomputed entities embedded in fixtures or deterministic regex extraction.
- Fully idempotent: Uses deterministic case_reference identifiers and Cypher MERGE.
- Scales safely to 100+ demo incidents in seconds.

Usage:
    python -m app.scripts.seed_extended_demo_data
    python app/scripts/seed_extended_demo_data.py
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Ensure backend root is on sys.path regardless of execution directory
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BACKEND_ROOT / ".env")
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.db.database import AsyncSessionLocal  # noqa: E402
from app.db.neo4j import connect_neo4j, disconnect_neo4j  # noqa: E402
from app.graph.builder import GraphBuilder  # noqa: E402
from app.graph.repository import GraphRepository  # noqa: E402
from app.models.enums import IncidentSource, ReporterType  # noqa: E402
from app.repositories.incident import IncidentRepository  # noqa: E402
from app.schemas.entity_extraction import ExtractedEntities, ExtractedEntity  # noqa: E402
from app.schemas.incident import IncidentCreate  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_FIXTURE_FILES = [
    "ring_alpha_kyc.json",
    "ring_beta_marketplace.json",
    "ring_gamma_courier.json",
    "ring_delta_investment.json",
    "ring_bridges.json",
    "cluster_loan_app.json",
    "cluster_task_scam.json",
    "independent_cases.json",
]


def resolve_entities_for_record(record: dict[str, Any]) -> ExtractedEntities:
    """
    Resolve ExtractedEntities for a demo record without invoking external LLMs.

    1. Uses explicit 'precomputed_entities' or 'entities' if present on the record.
    2. Otherwise, deterministically extracts verified fraud entities from the narrative
       (phone numbers, UPI IDs, URLs, emails, bank accounts, and known organizations).
    """
    if "precomputed_entities" in record and record["precomputed_entities"]:
        return ExtractedEntities.model_validate(record["precomputed_entities"])
    if "entities" in record and record["entities"]:
        return ExtractedEntities.model_validate(record["entities"])

    desc = record.get("description", "")

    # 1. Phone Numbers (+91 normalized without spaces)
    phone_numbers: list[ExtractedEntity] = []
    for raw_phone in re.findall(r"\+91[\s-]?\d{10}", desc):
        normalized = "+91" + "".join(filter(str.isdigit, raw_phone))[-10:]
        if not any(e.value == normalized for e in phone_numbers):
            phone_numbers.append(ExtractedEntity(value=normalized, confidence=0.99))

    # 2. UPI IDs (e.g. securekyc@ibl, rajeshstore@okaxis, customfees@paytm, microloanrepay@hdfc)
    upi_ids: list[ExtractedEntity] = []
    for raw_upi in re.findall(
        r"[\w.\-]+@(?:ibl|okaxis|paytm|okhdfcbank|oksbi|ybl|axl|icici|hdfc|yesbank|pay)",
        desc,
        re.IGNORECASE,
    ):
        upi_clean = raw_upi.lower()
        if not any(e.value == upi_clean for e in upi_ids):
            upi_ids.append(ExtractedEntity(value=upi_clean, confidence=0.99))

    # 3. Emails (distinguished from UPI by standard top-level domain extensions)
    emails: list[ExtractedEntity] = []
    for raw_email in re.findall(
        r"[\w.\-]+@[\w.\-]+\.(?:com|in|org|net|io|co)",
        desc,
        re.IGNORECASE,
    ):
        email_clean = raw_email.lower()
        if not any(e.value == email_clean for e in emails):
            emails.append(ExtractedEntity(value=email_clean, confidence=0.99))

    # 4. URLs and Telegram Handles
    urls: list[ExtractedEntity] = []
    for raw_url in re.findall(r"https?://[^\s,]+", desc):
        url_clean = raw_url.rstrip(".,;")
        if not any(e.value == url_clean for e in urls):
            urls.append(ExtractedEntity(value=url_clean, confidence=0.99))

    for raw_tg in re.findall(r"@[A-Za-z0-9_]+", desc):
        # Exclude UPI handle tails
        if not raw_tg.lower().endswith(
            ("@ibl", "@okaxis", "@paytm", "@okhdfcbank", "@oksbi", "@ybl", "@axl", "@icici", "@hdfc", "@yesbank", "@pay")
        ):
            if not any(e.value == raw_tg for e in urls):
                urls.append(ExtractedEntity(value=raw_tg, confidence=0.99))

    # 5. Bank Accounts
    bank_accounts: list[ExtractedEntity] = []
    for raw_acc in re.findall(
        r"(?:bank\s+account|account\s+number|account)\s+([0-9X]{8,20})",
        desc,
        re.IGNORECASE,
    ):
        if not any(e.value == raw_acc for e in bank_accounts):
            bank_accounts.append(ExtractedEntity(value=raw_acc, confidence=0.99))

    # 6. Organizations
    organizations: list[ExtractedEntity] = []
    known_orgs = [
        "State Bank of India",
        "SBI",
        "RBI",
        "Used Deal Shop",
        "Express Logistics India",
        "Prime Wealth Advisory",
        "CashNow Finance",
        "Global Media Marketing",
    ]
    for org_name in known_orgs:
        if re.search(rf"\b{re.escape(org_name)}\b", desc, re.IGNORECASE):
            if not any(e.value.lower() == org_name.lower() for e in organizations):
                organizations.append(ExtractedEntity(value=org_name, confidence=0.95))

    return ExtractedEntities(
        phone_numbers=phone_numbers,
        upi_ids=upi_ids,
        emails=emails,
        urls=urls,
        bank_accounts=bank_accounts,
        organizations=organizations,
    )


def get_deterministic_case_reference(item: dict[str, Any], default_prefix: str = "DEMO") -> str:
    """
    Generate a deterministic, RFC-safe case reference identifier.

    Preserves explicit case_reference if provided. Otherwise, generates a stable
    unique reference derived from the title and narrative hash.
    """
    if item.get("case_reference"):
        return str(item["case_reference"])

    title = item.get("title", "INCIDENT")
    desc = item.get("description", "")
    content_hash = hashlib.sha256(f"{title}|{desc}".encode("utf-8")).hexdigest()[:8].upper()
    title_slug = "".join(c for c in title if c.isalnum())[:16].upper()
    return f"{default_prefix}-{title_slug}-{content_hash}"


def load_demo_fixtures(data_dir: Path, fixture_files: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Load all available demo complaint fixtures from disk.
    """
    files = fixture_files or DEFAULT_FIXTURE_FILES
    all_records: list[dict[str, Any]] = []

    for filename in files:
        filepath = data_dir / filename
        if not filepath.exists():
            logger.warning("Fixture file not found: {}", filepath)
            continue

        with filepath.open("r", encoding="utf-8") as f:
            records = json.load(f)
            if isinstance(records, list):
                all_records.extend(records)
                logger.debug("Loaded {} complaints from {}", len(records), filename)

    if not all_records:
        demo_combined = data_dir / "demo_dataset.json"
        if demo_combined.exists():
            with demo_combined.open("r", encoding="utf-8") as f:
                all_records = json.load(f)
                logger.info("Loaded {} complaints from fallback demo_dataset.json", len(all_records))

    return all_records


async def seed_extended_demo_data(
    records: list[dict[str, Any]],
    skip_neo4j: bool = False,
) -> dict[str, int]:
    """
    Execute fast, offline ingestion of demo records into PostgreSQL and Neo4j.

    Args:
        records: List of complaint dictionary payloads.
        skip_neo4j: If True, bypasses Neo4j persistence.

    Returns:
        Statistics dictionary of operations executed.
    """
    stats = {
        "total_records": len(records),
        "postgres_created": 0,
        "postgres_reused": 0,
        "neo4j_persisted": 0,
        "neo4j_nodes": 0,
        "neo4j_relationships": 0,
    }

    graph_builder = GraphBuilder()
    graph_repo: GraphRepository | None = None

    neo4j_active = False
    if not skip_neo4j:
        try:
            await connect_neo4j()
            neo4j_active = True
            graph_repo = GraphRepository()
            logger.info("Neo4j driver active for graph persistence.")
        except Exception as exc:
            logger.warning("Neo4j unavailable ({}); proceeding with PostgreSQL only.", exc)

    try:
        async with AsyncSessionLocal() as session:
            incident_repo = IncidentRepository(session)

            for index, item in enumerate(records, start=1):
                case_ref = get_deterministic_case_reference(item)

                # 1. PostgreSQL Idempotent Persistence
                existing = await incident_repo.get_by_case_reference(case_ref)
                if existing is not None:
                    incident = existing
                    stats["postgres_reused"] += 1
                    logger.debug(
                        "[{}/{}] Reusing existing incident in PostgreSQL: {} ({})",
                        index,
                        len(records),
                        incident.title,
                        case_ref,
                    )
                else:
                    incident_in = IncidentCreate(
                        title=item["title"],
                        description=item["description"],
                        reporter_type=ReporterType(item.get("reporter_type", "citizen")),
                        source=IncidentSource(item.get("source", "web_portal")),
                        case_reference=case_ref,
                    )
                    incident = await incident_repo.create(incident_in)
                    await session.commit()
                    stats["postgres_created"] += 1
                    logger.debug(
                        "[{}/{}] Created incident in PostgreSQL: {} ({})",
                        index,
                        len(records),
                        incident.title,
                        case_ref,
                    )

                # 2. Neo4j Idempotent Persistence (Zero Gemini calls)
                if neo4j_active and graph_repo is not None:
                    entities = resolve_entities_for_record(item)
                    graph = graph_builder.build(
                        complaint_id=incident.id,
                        created_at=incident.created_at,
                        entities=entities,
                    )
                    res = await graph_repo.save_graph(graph)
                    stats["neo4j_persisted"] += 1
                    stats["neo4j_nodes"] += res.nodes_persisted
                    stats["neo4j_relationships"] += res.relationships_persisted

            logger.info("=" * 60)
            logger.success("Demo data seeding completed successfully.")
            logger.info("Total Records Processed   : {}", stats["total_records"])
            logger.info("PostgreSQL New Incidents  : {}", stats["postgres_created"])
            logger.info("PostgreSQL Existing Incidents: {}", stats["postgres_reused"])
            logger.info("Neo4j Complaints Merged   : {}", stats["neo4j_persisted"])
            logger.info("Neo4j Nodes Merged        : {}", stats["neo4j_nodes"])
            logger.info("Neo4j Relationships Merged: {}", stats["neo4j_relationships"])
            logger.info("=" * 60)

    finally:
        if neo4j_active:
            await disconnect_neo4j()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast SentinelGraph Demo Data Seeder")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Optional path to a single JSON dataset file (e.g. data/demo_dataset.json)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing individual ring JSON files",
    )
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Seed PostgreSQL only without connecting to Neo4j",
    )
    args = parser.parse_args()

    if args.dataset:
        with open(args.dataset, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = load_demo_fixtures(args.data_dir)

    logger.info("Loaded {} demo complaint records for fast seeding.", len(records))
    asyncio.run(seed_extended_demo_data(records, skip_neo4j=args.skip_neo4j))


if __name__ == "__main__":
    main()
