import asyncio

from loguru import logger

from app.ai.client import GeminiClient
from app.core.config import get_settings


async def main() -> None:
    """
    Simple integration test for the Gemini client.
    """
    settings = get_settings()
    print("API Key:", settings.GEMINI_API_KEY.get_secret_value()[:10] + "...")
    print("Model:", settings.GEMINI_MODEL)
    from pathlib import Path

    print(Path(".env").resolve())
    import os

    print(os.getcwd())
    client = GeminiClient(settings)

    prompt = (
        "Reply with exactly this sentence and nothing else: "
        "'Gemini client is working successfully.'"
    )

    try:
        response = await client.generate_content(prompt)

        logger.success("Gemini client test passed.")
        print("\n===== Gemini Response =====")
        print(response)

    except Exception:
        logger.exception("Gemini client test failed.")
        raise


if __name__ == "__main__":
    asyncio.run(main())
