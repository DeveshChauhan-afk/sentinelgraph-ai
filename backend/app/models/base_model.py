# app/models/base_model.py

"""
Abstract base model for the application.

All concrete ORM models inherit from this class to ensure
consistent primary key (UUID) and audit (timestamp) functionality.
"""

from app.db.base import Base
from app.models.mixins import UUIDMixin, TimestampMixin

class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Abstract base class providing UUID primary key and automatic timestamps.
    """
    __abstract__ = True