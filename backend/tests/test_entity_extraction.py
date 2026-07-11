import asyncio

from app.ai.client import GeminiClient
from app.ai.prompts import PromptBuilder
from app.core.config import get_settings
from app.schemas.entity_extraction import ExtractedEntities


async def main():
    settings = get_settings()
    client = GeminiClient(settings)

    complaint = (
        "I received a call from 9876543210 claiming to be SBI. "
        "They asked me to send money to abc@okaxis."
    )

    prompt = PromptBuilder.build_entity_extraction_prompt(complaint)

    response = await client.generate_content(prompt)

    entities = ExtractedEntities.model_validate_json(response)

    import json

    print(
        json.dumps(
            entities.model_dump(),
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
