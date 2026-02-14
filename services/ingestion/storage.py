"""
Write normalized macro observations to TimescaleDB.
"""
from datetime import date
from typing import Any

from services.core.db import get_conn


async def ensure_data_source(code: str, name: str, provider: str, timezone: str) -> int:
    """Insert or get data_source id."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM data_source WHERE code = $1",
            code,
        )
        if row:
            return row["id"]
        row = await conn.fetchrow(
            """
            INSERT INTO data_source (code, name, provider, timezone)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            code,
            name,
            provider,
            timezone,
        )
        return row["id"]


async def ensure_macro_indicator(
    code: str,
    name: str,
    category: str | None,
    unit: str | None,
    source_id: int,
    direction: str = "positive",
) -> int:
    """Insert or get macro_indicator id."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM macro_indicator WHERE code = $1",
            code,
        )
        if row:
            if category or unit or direction:
                await conn.execute(
                    """
                    UPDATE macro_indicator
                    SET name = $2, category = $3, unit = $4, direction = $5, updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                    name,
                    category,
                    unit,
                    direction,
                )
            return row["id"]
        row = await conn.fetchrow(
            """
            INSERT INTO macro_indicator (code, name, category, unit, source_id, direction)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            code,
            name,
            category,
            unit,
            source_id,
            direction,
        )
        return row["id"]


async def upsert_macro_observation(
    indicator_id: int,
    release_date: date,
    actual: float | None,
    forecast: float | None,
    previous: float | None,
    surprise: float | None,
    surprise_normalized: float | None = None,
    data_version: int = 1,
) -> None:
    """Insert or update one macro_observation. time = release_date at UTC midnight."""
    from datetime import datetime, timezone

    ts = datetime(release_date.year, release_date.month, release_date.day, tzinfo=timezone.utc)
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO macro_observation (
                time, indicator_id, release_date, actual, forecast, previous,
                surprise, surprise_normalized, data_version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (time, indicator_id)
            DO UPDATE SET
                actual = EXCLUDED.actual,
                forecast = EXCLUDED.forecast,
                previous = EXCLUDED.previous,
                surprise = EXCLUDED.surprise,
                surprise_normalized = EXCLUDED.surprise_normalized,
                data_version = EXCLUDED.data_version
            """,
            ts,
            indicator_id,
            release_date,
            actual,
            forecast,
            previous,
            surprise,
            surprise_normalized,
            data_version,
        )
