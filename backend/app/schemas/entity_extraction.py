# app/schemas/entity_extraction.py

"""
Pydantic schemas for AI-powered entity extraction.

These schemas define the structured output produced by the
Entity Extraction Service after processing complaint text
through the Gemini API.

The validated output serves as the contract between the AI
layer and downstream components such as the Neo4j Graph Builder
and Investigation Engine.
"""

from pydantic import BaseModel, ConfigDict, Field


class ExtractedEntity(BaseModel):
    """
    Represents a single entity extracted from complaint text.

    Attributes:
        value: The normalized value of the extracted entity.
        confidence: AI confidence score between 0.0 and 1.0.
    """

    model_config = ConfigDict(from_attributes=True)

    value: str = Field(
        ...,
        min_length=1,
        description="Normalized value of the extracted entity.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score assigned by the AI model.",
    )


class ExtractedEntities(BaseModel):
    """
    Collection of structured entities extracted from a complaint.

    Each category contains zero or more extracted entities
    with their corresponding confidence scores.
    """

    model_config = ConfigDict(from_attributes=True)

    phone_numbers: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted phone numbers.",
    )

    upi_ids: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted UPI IDs.",
    )

    emails: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted email addresses.",
    )

    urls: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted URLs.",
    )

    bank_accounts: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted bank account numbers.",
    )

    organizations: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted organization names.",
    )

    persons: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted person names.",
    )

    locations: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Extracted locations.",
    )
