"""
Normalize raw API responses into canonical macro observation format.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any


def parse_fred_observation(obs: dict[str, Any]) -> tuple[date | None, float | None]:
    """Extract (release_date, value) from FRED observation. Value can be '.' for missing."""
    d = obs.get("date")
    v = obs.get("value")
    if not d:
        return None, None
    try:
        release_date = date.fromisoformat(d)
    except (TypeError, ValueError):
        return None, None
    if v is None or v == ".":
        return release_date, None
    try:
        return release_date, float(v)
    except (TypeError, ValueError):
        return release_date, None


def normalize_observation(
    *,
    release_date: date,
    actual: float | None,
    previous: float | None = None,
    forecast: float | None = None,
) -> dict[str, Any]:
    """Build canonical observation row. Surprise = actual - forecast when both present."""
    surprise = None
    if actual is not None and forecast is not None:
        try:
            surprise = float(Decimal(str(actual)) - Decimal(str(forecast)))
        except (TypeError, ValueError):
            pass

    return {
        "release_date": release_date,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
        "surprise": surprise,
        "surprise_normalized": None,  # filled by processing layer
        "time": datetime(release_date.year, release_date.month, release_date.day, tzinfo=timezone.utc),
    }
