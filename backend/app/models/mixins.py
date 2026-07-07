# app/models/mixins.py

"""
Reusable SQLAlchemy model mixins.

Provides common columns shared across ORM models.
"""

import uuid
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

class UUIDMixin:
    """
    Mixin that adds a UUID primary key to a model.
    Uses PostgreSQL UUID type for optimal performance.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

class TimestampMixin:
    """
    Mixin that adds timezone-aware created_at and updated_at timestamps.
    Automatically handles creation and update times.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )