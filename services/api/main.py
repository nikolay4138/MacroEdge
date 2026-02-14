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
    """Latest bias score per index. Placeholder until Bias Engine is wired."""
    return {"date": None, "scores": [], "message": "Bias engine not yet populated"}
