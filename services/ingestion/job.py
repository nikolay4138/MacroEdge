"""
Daily ingestion job: seed metadata from config, fetch FRED series, normalize, store.
Run: PYTHONPATH=. python -m services.ingestion.job
"""
import asyncio
from datetime import date, timedelta
from typing import Any

from services.core.config import get_settings
from services.ingestion.connectors.fred import FREDConnector
from services.ingestion.normalizer import normalize_observation, parse_fred_observation
from services.ingestion.storage import (
    ensure_data_source,
    ensure_macro_indicator,
    upsert_macro_observation,
)


async def seed_metadata() -> dict[str, int]:
    """Load indicators and indices from config into DB. Returns indicator_id by code."""
    settings = get_settings()
    ind_cfg = settings.get_indicators_config()
    indicators = ind_cfg.get("indicators", [])
    source_id = await ensure_data_source("FRED", "Federal Reserve Economic Data", "FRED", "America/New_York")
    code_to_id: dict[str, int] = {}
    for ind in indicators:
        if ind.get("source") != "FRED":
            continue
        code = ind.get("code") or ""
        name = ind.get("name") or code
        category = ind.get("category")
        unit = ind.get("unit")
        direction = ind.get("direction") or "positive"
        indicator_id = await ensure_macro_indicator(code, name, category, unit, source_id, direction)
        code_to_id[code] = indicator_id
    return code_to_id


async def run_fred_ingestion(indicator_id: int, series_id: str, limit: int = 100) -> int:
    """Fetch FRED series, normalize, store. Returns number of observations written."""
    client = FREDConnector()
    if not client.api_key:
        return 0
    end = date.today()
    start = end - timedelta(days=365 * 2)
    observations = await client.get_series_observations(
        series_id,
        observation_start=start,
        observation_end=end,
        limit=limit,
        sort_order="asc",
    )
    written = 0
    prev_value: float | None = None
    for obs in observations:
        release_date, value = parse_fred_observation(obs)
        if release_date is None:
            continue
        # previous = last period's value (we use next in loop as previous for current)
        row = normalize_observation(
            release_date=release_date,
            actual=value,
            previous=prev_value,
            forecast=None,
        )
        await upsert_macro_observation(
            indicator_id=indicator_id,
            release_date=release_date,
            actual=row["actual"],
            forecast=row["forecast"],
            previous=row["previous"],
            surprise=row["surprise"],
            surprise_normalized=row["surprise_normalized"],
        )
        written += 1
        if value is not None:
            prev_value = value
    return written


async def run_daily_ingestion() -> dict[str, Any]:
    """Full ingestion: seed metadata, then fetch all FRED indicators from config."""
    code_to_id = await seed_metadata()
    settings = get_settings()
    ind_cfg = settings.get_indicators_config()
    indicators = ind_cfg.get("indicators", [])
    results: dict[str, Any] = {"indicators_processed": 0, "observations_written": 0, "errors": []}
    for ind in indicators:
        if ind.get("source") != "FRED":
            continue
        code = ind.get("code")
        series_id = ind.get("series_id")
        if not code or not series_id:
            results["errors"].append(f"Missing code or series_id: {ind}")
            continue
        indicator_id = code_to_id.get(code)
        if not indicator_id:
            continue
        try:
            n = await run_fred_ingestion(indicator_id, series_id)
            results["indicators_processed"] += 1
            results["observations_written"] += n
        except Exception as e:
            results["errors"].append(f"{code}: {e}")
    return results


def main() -> None:
    result = asyncio.run(run_daily_ingestion())
    print(result)


if __name__ == "__main__":
    main()
