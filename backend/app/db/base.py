# app/db/base.py

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Define a naming convention for constraints to ensure predictable
# names in database migrations (e.g., cleaner Foreign Key names).
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Centralized metadata registry
metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base.

    All ORM models inherit from this class.

    This module serves as the central metadata registry for
    SQLAlchemy and Alembic migrations.

    Common model mixins (UUID, timestamps, soft delete)
    will be introduced separately and inherited by models
    as the project evolves.
    """

    metadata = metadata
