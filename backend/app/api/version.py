# app/api/version.py

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_version():
    return {"version": settings.VERSION}