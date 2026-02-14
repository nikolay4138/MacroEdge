"""
Seed index and index_indicator_weight from config. Equal weights per indicator per index.
Run once or when config changes.
"""
from services.core.config import get_settings
from services.core.db import get_conn


async def seed_indices() -> dict[str, int]:
    """Insert indices from config. Returns index code -> id."""
    cfg = get_settings().get_indices_config()
    indices = cfg.get("indices", [])
    code_to_id: dict[str, int] = {}
    async with get_conn() as conn:
        for idx in indices:
            code = idx.get("code")
            name = idx.get("name") or code
            region = idx.get("region") or "US"
            currency = idx.get("currency") or "USD"
            tz = idx.get("timezone") or "America/New_York"
            row = await conn.fetchrow("SELECT id FROM index WHERE code = $1", code)
            if row:
                code_to_id[code] = row["id"]
            else:
                row = await conn.fetchrow(
                    """
                    INSERT INTO index (code, name, region, currency, timezone)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    code,
                    name,
                    region,
                    currency,
                    tz,
                )
                code_to_id[code] = row["id"]
    return code_to_id


async def seed_index_indicator_weights() -> None:
    """
    Ensure every (index, indicator) has a weight. Use equal weights: 1/N per index.
    """
    index_ids = await seed_indices()
    async with get_conn() as conn:
        ind_rows = await conn.fetch("SELECT id FROM macro_indicator")
    indicator_ids = [r["id"] for r in ind_rows]
    n = len(indicator_ids)
    if n == 0:
        return
    weight = round(1.0 / n, 4)
    if weight <= 0:
        weight = 0.0001
    async with get_conn() as conn:
        for index_id in index_ids.values():
            for indicator_id in indicator_ids:
                await conn.execute(
                    """
                    INSERT INTO index_indicator_weight (indicator_id, index_id, weight)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (indicator_id, index_id)
                    DO UPDATE SET weight = EXCLUDED.weight
                    """,
                    indicator_id,
                    index_id,
                    weight,
                )


async def run_seed() -> dict[str, any]:
    """Seed indices and equal weights. Call after ingestion has created macro_indicator."""
    await seed_indices()
    await seed_index_indicator_weights()
    return {"status": "ok", "message": "Indices and weights seeded"}
