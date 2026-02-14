"""
Smoke test: run when DB is available (e.g. docker compose up).
1. Migrate 2. Seed + ingestion (if FRED key) 3. Processing 4. Bias 5. Hit API.
Usage: PYTHONPATH=. python scripts/smoke_test.py
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def db_ok() -> bool:
    try:
        from services.core.db import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        print("DB not available:", e)
        return False


async def run_smoke() -> None:
    print("=== MacroEdge smoke test ===\n")
    if not await db_ok():
        print("Skip: start Docker (docker compose up -d) and run migrations (python scripts/migrate.py)")
        return
    print("1. Run migrations...")
    import subprocess
    r = subprocess.run(
        [sys.executable, "scripts/migrate.py"],
        cwd=ROOT,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print("   stderr:", r.stderr)
    print("   OK" if r.returncode == 0 else "   (migrate had warnings)")
    print("2. Ingestion (FRED)...")
    from services.core.config import get_settings
    if not get_settings().fred_api_key:
        print("   Skip (no FRED_API_KEY)")
    else:
        from services.ingestion.job import run_daily_ingestion
        out = await run_daily_ingestion()
        print("   ", out)
    print("3. Processing (surprise normalization)...")
    from services.processing.surprise import run_surprise_normalization
    out = await run_surprise_normalization(max_days_back=60)
    print("   ", out)
    print("4. Bias (seed + compute)...")
    from services.bias_engine.seed_weights import run_seed
    await run_seed()
    from services.bias_engine.scorer import run_bias_computation
    from datetime import date
    out = await run_bias_computation(date.today())
    print("   ", out)
    print("5. API (TestClient)...")
    from fastapi.testclient import TestClient
    from services.api.main import app
    with TestClient(app) as c:
        h = c.get("/health")
        assert h.status_code == 200
        s = c.get("/api/v1/bias/summary")
        assert s.status_code == 200
        j = s.json()
        n = len(j.get("scores", []))
        print(f"   /health 200, /api/v1/bias/summary 200, scores={n}")
    print("\n=== Smoke test done ===")


if __name__ == "__main__":
    asyncio.run(run_smoke())
