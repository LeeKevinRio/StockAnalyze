"""Pytest fixtures for the stock analysis platform test suite."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests.

    This overrides the default function-scoped loop so that the
    async engine and session factory can be shared across all tests
    in the session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create a session-scoped async SQLite in-memory engine.

    All tables defined on ``Base.metadata`` are created once for
    the entire test session.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_session_factory(async_engine):
    """Provide a session-scoped async session factory."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db(async_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide a per-test async database session with automatic rollback.

    Each test runs inside a transaction that is rolled back at the end,
    keeping the in-memory database clean between tests.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
