# app/core/health/models.py

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: float
    critical: bool
    message: Optional[str] = None


class LivenessResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReadinessResponse(BaseModel):
    status: HealthStatus
    is_ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dependencies: Dict[str, DependencyHealth]


class HealthSummaryResponse(BaseModel):
    status: HealthStatus
    service: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dependencies: Dict[str, DependencyHealth]
