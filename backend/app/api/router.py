# app/api/router.py

from fastapi import APIRouter
from app.api import health, version, auth, complaints, investigation, graph

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["General"])
api_router.include_router(version.router, prefix="/version", tags=["General"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(complaints.router, prefix="/complaints", tags=["Complaints"])
api_router.include_router(
    investigation.router, prefix="/investigation", tags=["Investigation"]
)
api_router.include_router(graph.router, prefix="/graph", tags=["Graph Intelligence"])
