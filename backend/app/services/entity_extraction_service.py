# app/services/entity_extraction_service.py

"""
Service responsible for AI-powered entity extraction.
"""

from loguru import logger
from pydantic import ValidationError

from app.ai.base import AIClient
from app.ai.exceptions import AIResponseError
from app.ai.prompts import PromptBuilder
from app.schemas.entity_extraction import ExtractedEntities


class EntityExtractionService:
    """
    Service for extracting structured entities from complaint text.
    """

    def __init__(self, ai_client: AIClient) -> None:
        self._ai_client = ai_client

    async def extract_entities(
        self,
        complaint: str,
    ) -> ExtractedEntities:
        """
        Extract structured entities from a complaint.

        Args:
            complaint: Complaint text.

        Returns:
            Structured extracted entities.

        Raises:
            AIResponseError:
                If the AI response cannot be validated.
        """
        logger.info("Starting entity extraction.")

        prompt = PromptBuilder.build_entity_extraction_prompt(
            complaint,
        )

        response = await self._ai_client.generate_content(prompt)

        try:
            entities = ExtractedEntities.model_validate_json(
                response,
            )
        except ValidationError as exc:
            logger.exception("Failed to validate entity extraction response.")
            raise AIResponseError(
                "Gemini returned an invalid structured response."
            ) from exc

        logger.info("Entity extraction completed successfully.")

        return entities
