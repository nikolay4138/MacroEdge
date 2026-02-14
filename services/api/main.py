"""
FastAPI application — MacroEdge API.
Run from project root: PYTHONPATH=. uvicorn services.api.main:app --reload
"""
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.core.config import get_settings
from services.core.db import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(
    title="MacroEdge API",
    description="Macro Monitoring & Bias Trading Support System",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, Any]:
    """Liveness: is the process up."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> dict[str, Any]:
    """Readiness: can we serve traffic (DB, etc.)."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@app.get("/api/v1/indices", tags=["indices"])
async def list_indices() -> dict[str, Any]:
    """List supported indices (from DB or config). Placeholder: return config."""
    settings = get_settings()
    cfg = settings.get_indices_config()
    indices = cfg.get("indices", [])
    return {"indices": indices}


@app.get("/api/v1/bias/summary", tags=["bias"])
async def bias_summary() -> dict[str, Any]:
    """Latest bias score per index from DB."""
    from services.core.db import fetch_all

    rows = await fetch_all(
        """
        SELECT bs.time, bs.bias_score, bs.confidence_pct, bs.risk_flag, bs.regime_id,
               i.code AS index_code, i.name AS index_name,
               r.code AS regime_code
        FROM bias_score bs
        JOIN index i ON i.id = bs.index_id
        LEFT JOIN market_regime r ON r.id = bs.regime_id
        WHERE bs.time = (SELECT MAX(time) FROM bias_score)
        ORDER BY i.code
        """
    )
    if not rows:
        return {"date": None, "scores": [], "message": "No bias scores yet. Run ingestion, then processing, then bias engine."}
    date_val = rows[0]["time"].date() if rows[0]["time"] else None
    scores = [
        {
            "index": r["index_code"],
            "name": r["index_name"],
            "bias_score": float(r["bias_score"]),
            "confidence_pct": float(r["confidence_pct"]),
            "risk_flag": r["risk_flag"],
            "regime": r["regime_code"],
        }
        for r in rows
    ]
    return {"date": date_val.isoformat() if date_val else None, "scores": scores}


@app.get("/api/v1/bias/history", tags=["bias"])
async def bias_history(
    index: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 365,
) -> dict[str, Any]:
    """Time series of bias scores. Optional filter by index code."""
    from datetime import datetime, timezone
    from services.core.db import fetch_all

    q = """
        SELECT bs.time, bs.bias_score, bs.confidence_pct, bs.risk_flag, i.code AS index_code
        FROM bias_score bs
        JOIN index i ON i.id = bs.index_id
        WHERE 1=1
    """
    params: list[Any] = []
    n = 0
    if index:
        n += 1
        q += f" AND i.code = ${n}"
        params.append(index)
    if from_date:
        n += 1
        q += f" AND bs.time >= ${n}"
        try:
            dt = datetime.strptime(from_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        params.append(dt)
    if to_date:
        n += 1
        q += f" AND bs.time <= ${n}"
        try:
            dt = datetime.strptime(to_date[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        params.append(dt)
    params.append(min(limit, 1000))
    n += 1
    q += f" ORDER BY bs.time DESC LIMIT ${n}"
    rows = await fetch_all(q, *params)
    series = [
        {
            "time": r["time"].isoformat() if r["time"] else None,
            "date": r["time"].date().isoformat() if r["time"] else None,
            "index": r["index_code"],
            "bias_score": float(r["bias_score"]),
            "confidence_pct": float(r["confidence_pct"]),
            "risk_flag": r["risk_flag"],
        }
        for r in rows
    ]
    return {"series": series, "count": len(series)}


@app.get("/api/v1/macro/latest", tags=["macro"])
async def macro_latest(days: int = 30) -> dict[str, Any]:
    """Latest macro observations per indicator (for heatmap/surprise tracker)."""
    from services.core.db import fetch_all

    rows = await fetch_all(
        """
        SELECT DISTINCT ON (m.id)
            m.code, m.name, m.category, m.unit, m.direction,
            o.release_date, o.actual, o.forecast, o.previous, o.surprise, o.surprise_normalized
        FROM macro_observation o
        JOIN macro_indicator m ON m.id = o.indicator_id
        WHERE o.release_date >= CURRENT_DATE - $1::int
        ORDER BY m.id, o.release_date DESC
        """,
        min(days, 365),
    )
    items = [
        {
            "code": r["code"],
            "name": r["name"],
            "category": r["category"],
            "unit": r["unit"],
            "direction": r["direction"],
            "release_date": r["release_date"].isoformat() if r["release_date"] else None,
            "actual": float(r["actual"]) if r["actual"] is not None else None,
            "forecast": float(r["forecast"]) if r["forecast"] is not None else None,
            "previous": float(r["previous"]) if r["previous"] is not None else None,
            "surprise": float(r["surprise"]) if r["surprise"] is not None else None,
            "surprise_normalized": float(r["surprise_normalized"]) if r["surprise_normalized"] is not None else None,
        }
        for r in rows
    ]
    return {"observations": items, "count": len(items)}
