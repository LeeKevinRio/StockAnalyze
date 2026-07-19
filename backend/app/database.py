"""Async SQLAlchemy database engine and session management."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Managed Postgres (Render/Neon/Supabase) requires SSL; local/internal does not.
_connect_args = {}
_pool_kwargs = {}
if settings.async_database_url.startswith("sqlite"):
    # SQLite (tests / local dev) uses NullPool — pool sizing args are invalid.
    pass
else:
    if settings.database_ssl_required:
        _connect_args["ssl"] = "require"
    _pool_kwargs = {"pool_size": 20, "max_overflow": 10, "pool_pre_ping": True}

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.is_development,
    connect_args=_connect_args,
    **_pool_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (for development only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
