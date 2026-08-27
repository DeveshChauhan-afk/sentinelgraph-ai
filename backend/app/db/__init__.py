# app/db/__init__.py

"""
Database module initialization.

Exposes the core database components (engine, session factory, and declarative base)
to simplify imports across the application.
"""

from app.db.base import Base
from app.db.database import AsyncSessionLocal, async_engine, close_db, get_db
from app.db.neo4j_schema import NEO4J_CONSTRAINTS, init_neo4j_schema

__all__ = [
    "Base",
    "AsyncSessionLocal",
    "async_engine",
    "close_db",
    "get_db",
    "init_neo4j_schema",
    "NEO4J_CONSTRAINTS",
]
