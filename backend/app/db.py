from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# Use SQLite for persistence
DATABASE_URL = "sqlite+aiosqlite:///./compliai.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")

async def get_db():
    """Dependency to get a database session."""
    async with async_session_maker() as session:
        yield session
