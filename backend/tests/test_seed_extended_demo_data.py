"""
Tests for seed_extended_demo_data.py:
1. Deterministic case reference generation and stability.
2. Resolution of precomputed entities.
3. Fallback deterministic regex entity extraction.
4. Fixture file loading.
5. Idempotent database handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.scripts.seed_extended_demo_data import (
    DATA_DIR,
    get_deterministic_case_reference,
    load_demo_fixtures,
    resolve_entities_for_record,
    seed_extended_demo_data,
)
from app.schemas.entity_extraction import ExtractedEntities


def test_get_deterministic_case_reference_preserves_explicit() -> None:
    record = {"title": "Test Title", "description": "Test Desc", "case_reference": "CR-2026-9999"}
    ref = get_deterministic_case_reference(record)
    assert ref == "CR-2026-9999"


def test_get_deterministic_case_reference_generates_stable_identifier() -> None:
    record1 = {"title": "Fake SBI KYC Verification Call", "description": "I received a call from +91 9876543210"}
    record2 = {"title": "Fake SBI KYC Verification Call", "description": "I received a call from +91 9876543210"}
    ref1 = get_deterministic_case_reference(record1)
    ref2 = get_deterministic_case_reference(record2)
    assert ref1 == ref2
    assert ref1.startswith("DEMO-FAKESBIKYC")
    assert len(ref1) <= 100


def test_resolve_entities_for_record_precomputed() -> None:
    record = {
        "title": "Sample",
        "description": "Sample description",
        "precomputed_entities": {
            "phone_numbers": [{"value": "+919876543210", "confidence": 0.99}],
            "upi_ids": [{"value": "securekyc@ibl", "confidence": 0.99}],
            "organizations": [{"value": "State Bank of India", "confidence": 0.95}],
        },
    }
    entities = resolve_entities_for_record(record)
    assert isinstance(entities, ExtractedEntities)
    assert len(entities.phone_numbers) == 1
    assert entities.phone_numbers[0].value == "+919876543210"
    assert entities.upi_ids[0].value == "securekyc@ibl"
    assert entities.organizations[0].value == "State Bank of India"


def test_resolve_entities_for_record_deterministic_extraction() -> None:
    record = {
        "title": "Fake SBI KYC Verification Call",
        "description": (
            "I received a call from +91 9876543210 from an executive of State Bank of India. "
            "Transferred ₹48,500 to securekyc@ibl and contacted support@useddealshop.com. "
            "Check tracking at https://trackparcel-support.in and Telegram @PrimeReturnsVIP. "
            "Deposit to bank account 456789XXXX5528."
        ),
    }
    entities = resolve_entities_for_record(record)
    assert any(p.value == "+919876543210" for p in entities.phone_numbers)
    assert any(u.value == "securekyc@ibl" for u in entities.upi_ids)
    assert any(o.value == "State Bank of India" for o in entities.organizations)
    assert any(e.value == "support@useddealshop.com" for e in entities.emails)
    assert any(url.value == "https://trackparcel-support.in" for url in entities.urls)
    assert any(url.value == "@PrimeReturnsVIP" for url in entities.urls)
    assert any(b.value == "456789XXXX5528" for b in entities.bank_accounts)


def test_load_demo_fixtures() -> None:
    fixtures = load_demo_fixtures(DATA_DIR)
    assert len(fixtures) == 100
    sample = fixtures[0]
    assert "title" in sample
    assert "description" in sample
    assert "reporter_type" in sample


@pytest.mark.asyncio
async def test_seed_extended_demo_data_idempotency() -> None:
    records = [
        {
            "title": "Fake KYC Call",
            "description": "Call from +91 9876543210 regarding securekyc@ibl",
            "reporter_type": "citizen",
            "source": "web_portal",
            "case_reference": "DEMO-TEST-001",
        }
    ]

    mock_session = AsyncMock()
    mock_incident_repo = AsyncMock()
    mock_existing_incident = MagicMock()
    mock_existing_incident.title = "Fake KYC Call"
    mock_existing_incident.id = "00000000-0000-0000-0000-000000000001"
    mock_existing_incident.created_at = "2026-09-17T00:00:00Z"

    # First pass: returns None (record does not exist yet)
    # Second pass: returns existing incident
    mock_incident_repo.get_by_case_reference.side_effect = [None, mock_existing_incident]
    mock_incident_repo.create.return_value = mock_existing_incident

    with patch("app.scripts.seed_extended_demo_data.AsyncSessionLocal") as mock_session_local, \
         patch("app.scripts.seed_extended_demo_data.IncidentRepository", return_value=mock_incident_repo):

        mock_session_local.return_value.__aenter__.return_value = mock_session

        # Run 1: Created
        stats1 = await seed_extended_demo_data(records, skip_neo4j=True)
        assert stats1["postgres_created"] == 1
        assert stats1["postgres_reused"] == 0

        # Run 2: Reused (Idempotent)
        stats2 = await seed_extended_demo_data(records, skip_neo4j=True)
        assert stats2["postgres_created"] == 0
        assert stats2["postgres_reused"] == 1
