"""Regression tests for entity extraction's graph handoff."""

import asyncio
from uuid import uuid4

from google.genai import _transformers

from app.ai.base import AIClient
from app.graph.builder import GraphBuilder
from app.schemas.entity_extraction import ExtractedEntities
from app.schemas.investigation import InvestigationReport
from app.services.entity_extraction_service import EntityExtractionService


class RecordingAIClient(AIClient):
    def __init__(self) -> None:
        self.response_schema = None

    async def generate_content(self, prompt, response_schema=None) -> str:
        self.response_schema = response_schema
        return """{
          "phone_numbers": [{"value": "9876543210", "confidence": 0.99}]
        }"""


def test_investigation_json_is_silently_coerced_to_empty_entities() -> None:
    """Document the failure mode caused by using the wrong Gemini schema."""
    investigation_json = """
    {
      "summary": "Fraud report",
      "risk_level": "high",
      "confidence": 0.99,
      "findings": ["A phone number was used"],
      "key_entities": ["9876543210"],
      "recommended_actions": ["Block the number"]
    }
    """

    entities = ExtractedEntities.model_validate_json(investigation_json)
    graph = GraphBuilder().build(uuid4(), entities)

    assert entities.model_dump() == {
        name: [] for name in ExtractedEntities.model_fields
    }
    assert len(graph.nodes) == 1
    assert graph.relationships == []


def test_entity_json_builds_entity_nodes_and_mentions_relationships() -> None:
    entities = ExtractedEntities.model_validate_json("""
        {
          "phone_numbers": [{"value": "9876543210", "confidence": 0.99}],
          "upi_ids": [{"value": "fraud@upi", "confidence": 0.95}],
          "emails": [], "urls": [], "bank_accounts": [],
          "organizations": [], "persons": [], "locations": []
        }
        """)

    graph = GraphBuilder().build(uuid4(), entities)

    assert len(graph.nodes) == 3
    assert len(graph.relationships) == 2


def test_extraction_requests_the_extracted_entities_schema() -> None:
    ai_client = RecordingAIClient()

    entities = asyncio.run(
        EntityExtractionService(ai_client).extract_entities("Call 9876543210")
    )

    assert ai_client.response_schema is ExtractedEntities
    assert len(entities.phone_numbers) == 1


def test_gemini_can_convert_every_response_schema() -> None:
    """Catch unsupported Pydantic JSON-schema metadata before any API call."""
    for response_schema in (ExtractedEntities, InvestigationReport):
        schema = _transformers.t_schema(None, response_schema)
        assert schema is not None
