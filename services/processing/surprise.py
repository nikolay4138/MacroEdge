"""
Compute rolling mean/std of surprise per indicator and update surprise_normalized.
Formula: normalized = (surprise - mean) / max(eps, std), capped to [-cap, +cap].
"""
from datetime import date, datetime, timedelta, timezone
from math import tanh

from services.core.config import get_settings
from services.core.db import get_conn


async def get_surprise_rolling_stats(
    indicator_id: int,
    as_of_date: date,
    window_days: int = 252,
) -> tuple[float | None, float | None]:
    """Return (mean, std) of surprise for indicator over [as_of_date - window_days, as_of_date]."""
    start = as_of_date - timedelta(days=window_days)
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                AVG(surprise) AS mean_surprise,
                STDDEV(surprise) AS std_surprise
            FROM macro_observation
            WHERE indicator_id = $1
              AND release_date >= $2
              AND release_date <= $3
              AND surprise IS NOT NULL
            """,
            indicator_id,
            start,
            as_of_date,
        )
    if not row or row["mean_surprise"] is None:
        return None, None
    mean_val = float(row["mean_surprise"])
    std_val = float(row["std_surprise"]) if row["std_surprise"] is not None else None
    return mean_val, std_val


def normalize_surprise(
    surprise: float,
    mean: float | None,
    std: float | None,
    cap: float = 3.0,
    eps: float = 1e-8,
) -> float:
    """Normalized surprise; cap to [-cap, +cap]."""
    if mean is None:
        return 0.0
    scale = max(eps, std or 0.0)
    if scale <= 0:
        return 0.0
    raw = (surprise - mean) / scale
    return max(-cap, min(cap, raw))


async def update_surprise_normalized(
    indicator_id: int,
    release_date: date,
    normalized: float,
) -> None:
    """Update macro_observation.surprise_normalized for one row."""
    ts = datetime(release_date.year, release_date.month, release_date.day, tzinfo=timezone.utc)
    async with get_conn() as conn:
        await conn.execute(
            """
            UPDATE macro_observation
            SET surprise_normalized = $3
            WHERE time = $1 AND indicator_id = $2
            """,
            ts,
            indicator_id,
            normalized,
        )


async def run_surprise_normalization(
    window_days: int | None = None,
    cap: float = 3.0,
    max_days_back: int = 30,
) -> dict[str, int]:
    """
    For each indicator, compute rolling mean/std of surprise, then update
    surprise_normalized for observations in the last max_days_back days.
    Returns counts: indicators_processed, rows_updated.
    """
    cfg = get_settings().get_bias_engine_config()
    surprise_cfg = cfg.get("surprise", {})
    window_days = window_days or surprise_cfg.get("rolling_window_days", 252)
    cap = surprise_cfg.get("cap_std_multiple", cap)

    async with get_conn() as conn:
        indicator_rows = await conn.fetch("SELECT id FROM macro_indicator")
    indicators = [r["id"] for r in indicator_rows]
    end_date = date.today()
    start_date = end_date - timedelta(days=max_days_back)
    rows_updated = 0
    for ind_id in indicators:
        mean_s, std_s = await get_surprise_rolling_stats(ind_id, end_date, window_days)
        async with get_conn() as conn:
            obs = await conn.fetch(
                """
                SELECT time, release_date, surprise
                FROM macro_observation
                WHERE indicator_id = $1
                  AND release_date >= $2
                  AND release_date <= $3
                  AND surprise IS NOT NULL
                ORDER BY release_date DESC
                """,
                ind_id,
                start_date,
                end_date,
            )
        for row in obs:
            sur = row["surprise"]
            if sur is None:
                continue
            norm = normalize_surprise(float(sur), mean_s, std_s, cap=cap)
            await update_surprise_normalized(ind_id, row["release_date"], norm)
            rows_updated += 1
    return {"indicators_processed": len(indicators), "rows_updated": rows_updated}
