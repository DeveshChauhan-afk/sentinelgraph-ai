# app/core/health/gemini.py

from app.core.config import Settings
from app.core.health.base import BaseHealthChecker


class GeminiConfigHealthChecker(BaseHealthChecker):
    """
    Health checker for Google Gemini configuration.
    Non-critical soft dependency. Verifies API key and model presence without network calls.
    """

    def __init__(
        self,
        settings_instance: Settings | None = None,
        critical: bool = False,
        timeout: float = 2.0,
    ) -> None:
        super().__init__(name="gemini", critical=critical, timeout=timeout)
        self._settings = settings_instance

    async def _check_health(self) -> None:
        from app.core.config import settings

        cfg = self._settings or settings

        if not cfg.GEMINI_API_KEY:
            raise ValueError("Gemini API key is not set")

        api_key = cfg.GEMINI_API_KEY.get_secret_value()
        if not api_key or not api_key.strip() or api_key == "your_gemini_api_key_here":
            raise ValueError("Gemini API key is unconfigured or contains default placeholder")

        if not cfg.GEMINI_MODEL or not cfg.GEMINI_MODEL.strip():
            raise ValueError("Gemini model is not configured")
