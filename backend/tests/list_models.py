# tests/list_models.py

from google import genai

from app.core.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY.get_secret_value())

for model in client.models.list():
    print(model.name)
