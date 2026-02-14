"""
Run bias computation: optional seed, then compute scores for all indices.
Run: PYTHONPATH=. python -m services.bias_engine.run [--seed] [--date YYYY-MM-DD]
"""
import argparse
import asyncio
from datetime import date, datetime


async def main_async(seed: bool, as_of: date | None) -> None:
    if seed:
        from services.bias_engine.seed_weights import run_seed

        r = await run_seed()
        print("Seed:", r)
    from services.bias_engine.scorer import run_bias_computation

    r = await run_bias_computation(as_of)
    print("Bias:", r)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", action="store_true", help="Seed indices and weights first")
    p.add_argument("--date", type=str, help="As-of date YYYY-MM-DD (default today)")
    args = p.parse_args()
    as_of = None
    if args.date:
        try:
            as_of = date.fromisoformat(args.date)
        except ValueError:
            as_of = date.today()
    asyncio.run(main_async(seed=args.seed, as_of=as_of))


if __name__ == "__main__":
    main()
