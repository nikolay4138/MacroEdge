"""
Daily pipeline: ingestion -> surprise normalization -> bias computation.
Run: PYTHONPATH=. python scripts/run_daily.py [--skip-ingestion] [--skip-bias]
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def run_ingestion() -> dict:
    from services.ingestion.job import run_daily_ingestion
    return await run_daily_ingestion()


async def run_processing() -> dict:
    from services.processing.surprise import run_surprise_normalization
    return await run_surprise_normalization()


async def run_bias(seed: bool = False) -> dict:
    from services.bias_engine.run import main_async
    from datetime import date
    if seed:
        from services.bias_engine.seed_weights import run_seed
        await run_seed()
    from services.bias_engine.scorer import run_bias_computation
    return await run_bias_computation(date.today())


async def main(skip_ingestion: bool, skip_bias: bool, seed_weights: bool) -> None:
    print("=== MacroEdge daily pipeline ===")
    if not skip_ingestion:
        print("1. Ingestion...")
        r = await run_ingestion()
        print("   ", r)
        print("2. Surprise normalization...")
        r2 = await run_processing()
        print("   ", r2)
    else:
        print("2. Surprise normalization...")
        r2 = await run_processing()
        print("   ", r2)
    if not skip_bias:
        print("3. Bias computation" + (" (with seed)" if seed_weights else "") + "...")
        r3 = await run_bias(seed=seed_weights)
        print("   ", r3)
    print("Done.")


def cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-ingestion", action="store_true", help="Skip FRED ingestion")
    p.add_argument("--skip-bias", action="store_true", help="Skip bias computation")
    p.add_argument("--seed", action="store_true", help="Seed indices/weights before bias run")
    args = p.parse_args()
    asyncio.run(main(args.skip_ingestion, args.skip_bias, args.seed))


if __name__ == "__main__":
    cli()
