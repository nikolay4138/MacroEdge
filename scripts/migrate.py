"""
Run SQL migrations. Requires sync postgres URL.
Usage: PYTHONPATH=. python scripts/migrate.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent


def get_sync_url() -> str:
    url = os.environ.get("DATABASE_URL_SYNC", "postgresql://macro:macro@localhost:5432/macroedge")
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def run_migration(sql_path: Path) -> None:
    import asyncpg

    url = get_sync_url()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgres://", 1)
    conn = await asyncpg.connect(url)
    try:
        sql = sql_path.read_text(encoding="utf-8")
        # Split by semicolon but keep inside CREATE TABLE etc.; simple split
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--"):
                continue
            stmt = stmt + ";"
            try:
                if stmt.strip().upper().startswith("SELECT"):
                    await conn.fetch(stmt)
                else:
                    await conn.execute(stmt)
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  (skip) {e}")
                else:
                    raise
    finally:
        await conn.close()


def main() -> None:
    migrations_dir = ROOT / "migrations"
    if not migrations_dir.exists():
        print("No migrations dir")
        sys.exit(1)
    for f in sorted(migrations_dir.glob("*.sql")):
        print(f"Running {f.name}...")
        asyncio.run(run_migration(f))
    print("Done.")


if __name__ == "__main__":
    main()
