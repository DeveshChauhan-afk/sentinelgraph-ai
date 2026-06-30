"""
Database infrastructure.

This module provides:

- Async SQLAlchemy engine
- Async session factory
- FastAPI database dependency

Transaction management is intentionally delegated
to the service layer.
"""
# app/db/database.py

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# Create the async engine with production-ready connection pool settings
# pool_reset_on_return="rollback" ensures connections are clean before returning to the pool
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    pool_reset_on_return="rollback",
    echo=False,
    future=True,
)

# Create the async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.

    Transaction management (commit/rollback) is explicitly handled by 
    the service layer to ensure data consistency across multi-resource operations.
    """
    async with AsyncSessionLocal() as session:
        yield session