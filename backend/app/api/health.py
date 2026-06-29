# app/api/health.py

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}
