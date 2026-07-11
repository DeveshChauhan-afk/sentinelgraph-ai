# app/ai/prompts.py

"""
Prompt templates for AI-powered workflows.

This module centralizes prompt construction for all Gemini interactions,
ensuring consistency, maintainability, and reusability across the
application.
"""

class PromptBuilder:
    """
    Factory class for constructing AI prompts.
    """

    @staticmethod
    def build_entity_extraction_prompt(
        complaint: str,
    ) -> str:
        """
        Build the prompt for extracting entities from a complaint.

        Args:
            complaint: Raw complaint text.

        Returns:
            Prompt formatted for Gemini.
        """
        return f"""
You are an expert cyber fraud intelligence analyst.

Your task is to extract entities that are explicitly mentioned in the complaint.

Rules:

1. Do NOT infer information.
2. Do NOT invent entities.
3. Normalize values whenever possible.
4. If an entity type is absent, return an empty array.
5. Confidence must be between 0.0 and 1.0.
6. Return ONLY valid JSON.
7. Do NOT include markdown.
8. Do NOT include explanations.
9. Do NOT wrap the JSON inside code fences.

The JSON MUST exactly follow this schema:

{{
  "phone_numbers": [
    {{
      "value": "...",
      "confidence": 0.95
    }}
  ],
  "upi_ids": [],
  "emails": [],
  "urls": [],
  "bank_accounts": [],
  "organizations": [],
  "persons": [],
  "locations": []
}}

Complaint:

{complaint}
""".strip()
