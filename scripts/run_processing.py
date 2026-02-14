"""
Run only surprise normalization (processing layer).
PYTHONPATH=. python scripts/run_processing.py
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


async def main() -> None:
    from services.processing.surprise import run_surprise_normalization
    r = await run_surprise_normalization()
    print(r)


if __name__ == "__main__":
    asyncio.run(main())
