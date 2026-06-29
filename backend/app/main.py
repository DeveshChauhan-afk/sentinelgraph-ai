from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.VERSION,
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to SentinelGraph AI",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }