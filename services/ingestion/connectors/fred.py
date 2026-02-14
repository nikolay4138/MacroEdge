"""
FRED API client. Fetches time series observations.
API docs: https://fred.stlouisfed.org/docs/api/fred/
"""
from datetime import date
from typing import Any

import httpx

from services.core.config import get_settings


class FREDConnector:
    BASE = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_settings().fred_api_key

    def _url(self, endpoint: str, **params: Any) -> str:
        from urllib.parse import urlencode

        p = {**params, "api_key": self.api_key, "file_type": "json"}
        return f"{self.BASE}/{endpoint}?{urlencode(p)}"

    async def get_series_observations(
        self,
        series_id: str,
        *,
        observation_start: date | None = None,
        observation_end: date | None = None,
        limit: int = 500,
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Fetch observations for a series. Returns list of {date, value}."""
        params: dict[str, Any] = {
            "series_id": series_id,
            "sort_order": sort_order,
            "limit": limit,
        }
        if observation_start is not None:
            params["observation_start"] = observation_start.isoformat()
        if observation_end is not None:
            params["observation_end"] = observation_end.isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(self._url("series/observations", **params))
            r.raise_for_status()
            data = r.json()
        return data.get("observations", [])

    async def get_release_dates(self, release_id: int, limit: int = 30) -> list[dict[str, Any]]:
        """Fetch release dates for a FRED release (for release-based series)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                self._url(
                    "release/dates",
                    release_id=release_id,
                    limit=limit,
                    sort_order="desc",
                )
            )
            r.raise_for_status()
            data = r.json()
        return data.get("release_dates", [])
