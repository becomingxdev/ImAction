import logging
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("imaction")

# ==============================================================================
# Synchronous Database Configuration (Standard & Health Checks)
# ==============================================================================
try:
    sync_engine = create_engine(
        settings.sync_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=sync_engine
    )
except Exception as e:
    logger.error(f"Failed to initialize synchronous SQLAlchemy engine: {e}")
    sync_engine = None
    SessionLocal = None

# ==============================================================================
# Asynchronous Database Configuration (High-Performance Async Endpoints)
# ==============================================================================
try:
    async_engine = create_async_engine(
        settings.async_database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
except Exception as e:
    logger.error(f"Failed to initialize asynchronous SQLAlchemy engine: {e}")
    async_engine = None
    AsyncSessionLocal = None


# ==============================================================================
# Declarative Base for SQLAlchemy Models
# ==============================================================================
class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 style declarative base class.
    All database models will inherit from this base.
    """
    pass


# ==============================================================================
# Database Session Dependencies
# ==============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection provider for synchronous database sessions.
    Guarantees session teardown on request completion.
    """
    if SessionLocal is None:
        raise RuntimeError("Synchronous session maker is not initialized.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency injection provider for asynchronous database sessions.
    Guarantees session teardown on request completion.
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Asynchronous session maker is not initialized.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
