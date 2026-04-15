from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

if not settings.database_is_sqlite:
    raise RuntimeError("35gateway open-source backend only supports sqlite.")

_SYNC_CONNECT_ARGS: dict[str, object] = {"check_same_thread": False}
_ASYNC_CONNECT_ARGS: dict[str, object] = {}
_SYNC_ENGINE_KWARGS: dict[str, object] = {
    "pool_pre_ping": True,
    "future": True,
}
_ASYNC_ENGINE_KWARGS: dict[str, object] = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

sync_engine = create_engine(
    settings.database_url,
    connect_args=_SYNC_CONNECT_ARGS,
    **_SYNC_ENGINE_KWARGS,
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False, future=True)

async_engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    connect_args=_ASYNC_CONNECT_ARGS,
    **_ASYNC_ENGINE_KWARGS,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# 向后兼容旧平台命名
engine = sync_engine


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
