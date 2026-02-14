"""Async database pool (asyncpg) for TimescaleDB/PostgreSQL."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from services.core.config import get_settings


def _database_url_for_asyncpg() -> str:
    url = get_settings().database_url
    # Convert sqlalchemy-style postgresql+asyncpg:// to postgres:// for asyncpg
    if "postgresql+asyncpg://" in url:
        url = url.replace("postgresql+asyncpg://", "postgres://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgres://", 1)
    return url


_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            _database_url_for_asyncpg(),
            min_size=1,
            max_size=10,
            command_timeout=60,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def fetch_one(
    query: str,
    *args: Any,
) -> asyncpg.Record | None:
    async with get_conn() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args: Any) -> list[asyncpg.Record]:
    async with get_conn() as conn:
        return await conn.fetch(query, *args)


async def execute(query: str, *args: Any) -> str:
    async with get_conn() as conn:
        return await conn.execute(query, *args)
