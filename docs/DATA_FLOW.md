# Data Flow — Macro Monitoring & Bias Trading Support System

## 1. End-to-End Data Flow (High Level)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  FRED / ECB  │     │  Ingestion       │     │  Processing     │     │  Bias Engine    │
│  BoJ / etc.  │────▶│  Orchestrator    │────▶│  (Surprise,     │────▶│  (Score,        │
│  (APIs)      │     │  (Scheduler)     │     │   Rolling,      │     │   Regime,       │
└──────────────┘     └────────┬─────────┘     │   Regime input) │     │   Confidence)   │
                              │               └────────┬────────┘     └────────┬────────┘
                              │                        │                      │
                              ▼                        ▼                      ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │  TimescaleDB │ PostgreSQL │ Redis (cache)                    │
                     └─────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                     ┌─────────────────────────────────────────────────────────────┐
                     │  REST API / BFF  ────▶  Web Dashboard / Export / Alerts     │
                     └─────────────────────────────────────────────────────────────┘
```

---

## 2. Daily Ingestion Flow (Sequence)

```
Scheduler (e.g. 06:00 UTC)
    │
    ├─▶ [1] Fetch calendar (today’s releases by region: US, EU, JP)
    │
    ├─▶ [2] For each data source (FRED, ECB, …):
    │         - Call API with timezone-aware window
    │         - Normalize to common schema (indicator_id, release_date, actual, forecast, previous)
    │         - Compute surprise, optional surprise_normalized
    │         - Write to macro_observation (with data_version)
    │
    ├─▶ [3] Fetch auxiliary: yield curve (2Y, 10Y), VIX/MOVE
    │         - Write to yield_curve_snapshot, volatility_snapshot
    │
    ├─▶ [4] Emit event: "macro_data_updated" (date, regions)
    │
    └─▶ [5] Trigger Bias Engine run (or Engine subscribes to event)
```

---

## 3. Processing Layer Flow

```
Event: macro_data_updated
    │
    ├─▶ [1] Load latest macro_observation (per indicator, last N days)
    │
    ├─▶ [2] Surprise normalization (rolling μ, σ per indicator) → update or materialize
    │
    ├─▶ [3] Rolling stats (e.g. 30d/90d mean, std, trend) → macro_rolling_stats
    │
    ├─▶ [4] Regime classifier inputs: VIX, 2Y-10Y, recent surprises → regime_id
    │
    └─▶ [5] Pass to Bias Engine: normalized surprises, regime, weights, volatility
```

---

## 4. Bias Engine Flow

```
Inputs: normalized surprises, regime, weights (per index), VIX, yield spread
    │
    ├─▶ [1] Resolve regime-adjusted weights w_{i,j}(r)
    │
    ├─▶ [2] Compute S_raw,j = Σ w_{i,j}(r) * s_i
    │
    ├─▶ [3] Map to [-100, +100] (e.g. tanh), optional yield adjustment
    │
    ├─▶ [4] Confidence: C_data * C_coverage * ν
    │
    ├─▶ [5] Risk flag: thresholds on C, |S|, VIX, regime
    │
    └─▶ [6] Write bias_score (time, index_id, bias_score, regime_id, confidence_pct, risk_flag, components_json)
            Emit event: "bias_computed"
```

---

## 5. API → UI Flow

```
User opens Dashboard
    │
    ├─▶ GET /api/v1/bias/summary?date=latest  → Bias scores + regime + confidence + risk per index
    ├─▶ GET /api/v1/bias/history?index=SPX&from=&to=  → Time series for charts
    ├─▶ GET /api/v1/macro/heatmap?date=  → Actual/Forecast/Previous/Surprise by indicator
    ├─▶ GET /api/v1/macro/surprises?date=  → Surprise tracker list
    ├─▶ GET /api/v1/regime/current  → Regime + inputs (VIX, yield spread)
    ├─▶ GET /api/v1/correlation  → Correlation matrix (macro vs macro or macro vs index)
    └─▶ GET /api/v1/export/csv|pdf  → Export (filters: date range, index)
```

---

## 6. Timezone-Aware Processing

| Region | Primary timezone | Typical release time (local) | UTC window for fetch       |
| ------ | ---------------- | ---------------------------- | -------------------------- |
| US     | America/New_York | 08:30, 10:00                 | 13:30–15:00 UTC            |
| EU     | Europe/Berlin    | 10:00, 11:00                 | 09:00–10:00 UTC            |
| Japan  | Asia/Tokyo       | 08:50, 13:00                 | 23:50–04:00 UTC (prev day) |

- Store all times in DB as **UTC** (TIMESTAMPTZ).
- Scheduler runs multiple times per day (e.g. after US open, after EU close) or once daily with “as-of” date so that late releases are captured next run.
- UI shows dates/times in user-selected or index-specific timezone.

---

## 7. Event-Driven Refresh (Optional Detail)

```
[Ingestion Job]  ──▶  macro_data_updated  ──▶  [Processing]  ──▶  (optional) processed_data_ready
                                                      │
[Bias Engine]   ◀──  (trigger or subscribe)  ◀────────┘
       │
       └──▶  bias_computed  ──▶  [Alert Service] / [API cache invalidation]
```

This keeps UI and alerts in sync without polling and allows scaling of ingestion and engine independently.
