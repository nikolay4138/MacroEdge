"""
Bias scoring: load observations + weights, compute score, regime, confidence, risk flag.
"""
from datetime import date, datetime, timedelta, timezone
from math import tanh
from typing import Any

from services.core.config import get_settings
from services.core.db import get_conn


async def get_regime_id(code: str) -> int | None:
    """Return market_regime.id for code (e.g. 'neutral')."""
    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT id FROM market_regime WHERE code = $1", code)
        return row["id"] if row else None


async def get_vix_latest(as_of: date) -> float | None:
    """Latest VIX value on or before as_of. Returns None if no data."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT value FROM volatility_snapshot
            WHERE symbol = 'VIX' AND time <= $1
            ORDER BY time DESC LIMIT 1
            """,
            datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc),
        )
        return float(row["value"]) if row and row["value"] is not None else None


async def get_latest_surprises(as_of: date, max_days_back: int = 14) -> list[dict[str, Any]]:
    """
    For each indicator, the most recent observation with surprise_normalized on or before as_of.
    Returns list of {indicator_id, direction, surprise_normalized, release_date}.
    """
    start = as_of - timedelta(days=max_days_back)
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (o.indicator_id)
                o.indicator_id,
                m.direction,
                o.surprise_normalized,
                o.release_date
            FROM macro_observation o
            JOIN macro_indicator m ON m.id = o.indicator_id
            WHERE o.release_date >= $1 AND o.release_date <= $2
              AND o.surprise_normalized IS NOT NULL
            ORDER BY o.indicator_id, o.release_date DESC
            """,
            start,
            as_of,
        )
    return [
        {
            "indicator_id": r["indicator_id"],
            "direction": r["direction"] or "positive",
            "surprise_normalized": float(r["surprise_normalized"]) if r["surprise_normalized"] is not None else 0.0,
            "release_date": r["release_date"],
        }
        for r in rows
    ]


async def get_weights_for_index(index_id: int, regime_code: str = "neutral") -> list[dict[str, Any]]:
    """Weights for index. regime_weights multiplier applied if present."""
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT indicator_id, weight, regime_weights
            FROM index_indicator_weight
            WHERE index_id = $1
            """,
            index_id,
        )
    result = []
    for r in rows:
        w = float(r["weight"])
        rw = r["regime_weights"]
        if isinstance(rw, dict) and regime_code in rw:
            try:
                w *= float(rw[regime_code])
            except (TypeError, ValueError):
                pass
        result.append({"indicator_id": r["indicator_id"], "weight": w})
    # Normalize
    total = sum(x["weight"] for x in result)
    if total and total > 0:
        for x in result:
            x["weight"] = x["weight"] / total
    return result


def signed_surprise(direction: str, surprise_norm: float) -> float:
    """sign_i * surprise_norm. positive direction = higher actual is bullish."""
    if direction == "negative":
        return -surprise_norm
    return surprise_norm


def score_raw(weighted_surprises: list[tuple[float, float]]) -> float:
    """S_raw = sum( w * signed_surprise )."""
    return sum(w * s for w, s in weighted_surprises)


def score_bounded(raw: float, lambda_j: float) -> float:
    """S = 100 * tanh(S_raw / lambda)."""
    return 100.0 * tanh(raw / max(0.01, lambda_j))


async def compute_confidence(
    as_of: date,
    n_indicators_used: int,
    min_expected: int = 5,
    stale_days: int = 7,
    vix: float | None = None,
) -> float:
    """C = coverage * nu, in [0, 100]. coverage = n_used / min_expected; nu from VIX."""
    cfg = get_settings().get_bias_engine_config()
    conf_cfg = cfg.get("confidence", {})
    min_expected = conf_cfg.get("min_indicators_expected", min_expected)
    stale_days = conf_cfg.get("stale_release_days", stale_days)
    coverage = min(1.0, n_indicators_used / max(1, min_expected))
    vol_cfg = cfg.get("volatility", {})
    vix_min = vol_cfg.get("vix_min", 10)
    vix_max = vol_cfg.get("vix_max", 40)
    if vix is not None:
        nu = 1.0 - min(1.0, max(0.0, (vix - vix_min) / max(1, vix_max - vix_min)))
    else:
        nu = 1.0
    return round(min(100.0, max(0.0, coverage * nu * 100)), 2)


def risk_flag_from_thresholds(
    confidence: float,
    bias_abs: float,
    vix: float | None,
    regime_code: str,
) -> str:
    """Low / Medium / High from config thresholds."""
    cfg = get_settings().get_bias_engine_config()
    rf = cfg.get("risk_flag", {})
    c_high = rf.get("confidence_high", 70)
    c_low = rf.get("confidence_low", 40)
    s_mod = rf.get("bias_moderate_abs", 50)
    vix_high = rf.get("vix_high", 35)
    vix_crit = rf.get("vix_critical", 45)
    if vix is not None and vix >= vix_crit:
        return "high"
    if confidence <= c_low or (regime_code == "recessionary" and bias_abs > 50):
        return "high"
    if confidence >= c_high and bias_abs <= s_mod and (vix is None or vix < vix_high):
        return "low"
    return "medium"


async def compute_bias_for_index(
    index_id: int,
    index_code: str,
    as_of: date,
    surprises: list[dict[str, Any]],
    regime_id: int,
    regime_code: str = "neutral",
    vix: float | None = None,
) -> dict[str, Any]:
    """
    Compute bias score, confidence, risk_flag for one index.
    surprises: from get_latest_surprises(); each has indicator_id, direction, surprise_normalized.
    """
    weights = await get_weights_for_index(index_id, regime_code)
    by_ind = {s["indicator_id"]: s for s in surprises}
    weighted: list[tuple[float, float]] = []
    for w in weights:
        ind_id = w["indicator_id"]
        s = by_ind.get(ind_id)
        if s is None:
            continue
        signed = signed_surprise(s["direction"], s["surprise_normalized"])
        weighted.append((w["weight"], signed))
    S_raw = score_raw(weighted)
    cfg = get_settings().get_bias_engine_config()
    lambdas = cfg.get("scoring", {}).get("lambda", {})
    lambda_j = float(lambdas.get(index_code, 2.0))
    S = score_bounded(S_raw, lambda_j)
    n_used = len(weighted)
    confidence = await compute_confidence(as_of, n_used, vix=vix)
    risk = risk_flag_from_thresholds(confidence, abs(S), vix, regime_code)
    return {
        "bias_score": round(S, 2),
        "regime_id": regime_id,
        "confidence_pct": confidence,
        "risk_flag": risk,
        "components_json": {"S_raw": S_raw, "n_indicators": n_used},
    }


async def run_bias_computation(as_of: date | None = None) -> dict[str, Any]:
    """
    Compute bias for all indices and write to bias_score.
    as_of: date to use for latest observations; default today.
    """
    as_of = as_of or date.today()
    regime_code = "neutral"
    regime_id = await get_regime_id(regime_code)
    if not regime_id:
        regime_id = 5  # fallback neutral id from migration
    vix = await get_vix_latest(as_of)
    surprises = await get_latest_surprises(as_of)
    async with get_conn() as conn:
        index_rows = await conn.fetch("SELECT id, code FROM index")
    ts = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)
    results = []
    for row in index_rows:
        index_id = row["id"]
        index_code = row["code"]
        out = await compute_bias_for_index(
            index_id,
            index_code,
            as_of,
            surprises,
            regime_id,
            regime_code,
            vix,
        )
        async with get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO bias_score (time, index_id, bias_score, regime_id, confidence_pct, risk_flag, components_json)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (time, index_id)
                DO UPDATE SET
                    bias_score = EXCLUDED.bias_score,
                    regime_id = EXCLUDED.regime_id,
                    confidence_pct = EXCLUDED.confidence_pct,
                    risk_flag = EXCLUDED.risk_flag,
                    components_json = EXCLUDED.components_json
                """,
                ts,
                index_id,
                out["bias_score"],
                out["regime_id"],
                out["confidence_pct"],
                out["risk_flag"],
                out["components_json"],
            )
        results.append({"index": index_code, **out})
    return {"date": as_of.isoformat(), "scores": results}
