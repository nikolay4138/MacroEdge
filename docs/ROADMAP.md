# Development Roadmap — Macro Monitoring & Bias Trading Support System

## Phase Overview

| Phase   | Focus                                      | Duration (estimate) | Deliverables                                            |
| ------- | ------------------------------------------ | ------------------- | ------------------------------------------------------- |
| **MVP** | Data + single-index bias + minimal UI      | 8–10 weeks          | Ingestion (1–2 sources), bias for SPX, simple dashboard |
| **V1**  | All indices, full UI, production hardening | 6–8 weeks           | 4 indices, heatmap, regime, export, monitoring          |
| **V2**  | ML, sentiment, alerts, backtesting         | 10–12 weeks         | Regime ML, optional LSTM, alerts, backtest engine       |

---

## MVP (Months 1–2.5)

### Goals

- Prove data pipeline and bias logic end-to-end.
- One index (e.g. S&P 500), one region (US).
- Basic dashboard: today’s bias, simple history chart.

### Milestones

1. **Project & infra (Week 1–2)**
   - Repo structure, Docker Compose (Postgres/TimescaleDB, Redis).
   - DB migrations (schema from DATABASE_SCHEMA.md).
   - CI: lint, test, build images.

2. **Data ingestion (Week 2–4)**
   - FRED connector: fetch CPI, PMI, NFP, etc.; normalize; write to `macro_observation`.
   - Timezone-aware release dates (US).
   - Scheduler: daily job (Cron or Airflow DAG).

3. **Processing (Week 4–5)**
   - Surprise calculation (actual − forecast); optional normalization (rolling μ, σ).
   - Rolling stats (e.g. 30d) for a subset of indicators.

4. **Bias engine (Week 5–6)**
   - Implement scoring from BIAS_ALGORITHM.md (weights from DB, regime = neutral initially).
   - Output: bias_score, confidence, risk_flag for SPX.
   - Write to `bias_score`; optional event “bias_computed”.

5. **API (Week 6–7)**
   - REST: `GET /bias/summary`, `GET /bias/history`, `GET /macro/latest`.
   - OpenAPI docs.

6. **UI (Week 7–8)**
   - Dashboard: current bias (gauge or number), list of latest macro releases, one history chart (bias over time).
   - Export CSV (bias + macro for selected date range).

7. **MVP wrap-up (Week 8–10)**
   - Integration tests; deployment to staging (e.g. single node K8s or ECS).
   - Documentation: runbook, env vars, how to add an indicator.

**MVP exit criteria:** Daily US macro data ingested; SPX bias and confidence shown; CSV export works.

---

## V1 (Months 3–4.5)

### Goals

- All four indices (S&P 500, NASDAQ 100, DAX 40, Nikkei 225).
- Multiple data sources (FRED, ECB, BoJ or Investing/TradingEconomics).
- Full UI: heatmap, regime, correlation, yield curve, export PDF.
- Production-ready: monitoring, secrets, scaling.

### Milestones

1. **Multi-region ingestion (Week 1–2)**
   - Connectors: ECB (EU), BoJ or alternate (JP).
   - Calendar: which indicators release per region per day; timezone-aware fetch.
   - Versioning: `data_version` and handling revisions.

2. **Index-specific weights & regime (Week 2–3)**
   - Seed `index_indicator_weight` (and optional `regime_weights`) for SPX, NDX, DAX, NKY.
   - Rule-based regime detection (VIX, 2Y–10Y, recent surprises); persist regime_id in bias_score.

3. **Bias for all indices (Week 3–4)**
   - Engine runs once per day; computes bias for all four indices; volatility filter (ν) and confidence.

4. **Dashboard (Week 4–6)**
   - Heatmap: indicators × Actual/Forecast/Previous/Surprise.
   - Per-index breakdown; historical bias chart per index.
   - Correlation matrix (macro vs macro or vs index returns).
   - Yield curve (2Y, 10Y, spread); regime indicator; macro surprise tracker.
   - Export: CSV + PDF.

5. **Production (Week 6–8)**
   - Kubernetes/OpenShift (or ECS) deployment; secrets from Vault/Secrets Manager.
   - Prometheus + Grafana; alerting on ingestion failure and API errors.
   - Logging (structured JSON, centralised).

**V1 exit criteria:** Four indices; US/EU/JP data; full UI and export; monitoring and secrets in place.

---

## V2 (Months 5–7)

### Goals

- ML-based regime detection; optional macro forecasting (LSTM/Transformer).
- Sentiment layer (news/Fed speeches).
- Alerts (email/Telegram); backtesting engine; strategy overlay.

### Milestones

1. **ML regime (Weeks 1–3)**
   - Train classifier (e.g. Random Forest / XGBoost) on labeled regimes (or proxy: VIX + yield + returns).
   - Service consumes “macro_data_updated”; outputs “regime_signal”; Bias Engine uses it for weights.

2. **Sentiment (Weeks 3–5)**
   - Ingest headlines or Fed speech summaries; sentiment score (e.g. transformer-based).
   - Store time-series; optional extra feature in regime or bias (with small weight).

3. **Alerts (Weeks 4–5)**
   - Alert service: subscribes to “bias_computed” and “regime_changed”.
   - Rules: e.g. “bias &lt; -50 and confidence &gt; 70%” → Telegram/email.
   - Configurable rules in DB or config.

4. **Backtesting (Weeks 5–8)**
   - Backtest engine: historical bias + regime vs index returns; metrics (hit rate, drawdown).
   - API: run backtest for date range and index; return report.

5. **Strategy overlay (Weeks 7–10)**
   - Optional: map bias/regime to suggested exposure (swing/position); display on dashboard; disclaimer (not advice).

6. **Macro forecasting (optional, Weeks 8–12)**
   - LSTM or Transformer for selected indicators (e.g. CPI, PMI); research project; can feed into bias as “expected” component later.

**V2 exit criteria:** At least one of: ML regime live; alerts working; backtest report available; sentiment pipeline running.

---

## Dependencies Between Phases

- **V1** depends on MVP: ingestion and bias engine patterns are fixed in MVP.
- **V2** depends on V1: multi-index and regime in place; events and API stable for alerts and backtest.

---

## Resource Assumptions

- 1–2 backend engineers (Python, DB, APIs).
- 1 frontend engineer (React, charts) from V1.
- DevOps/cloud part-time for MVP (Docker, Compose), full-time from V1 (K8s, monitoring).

Adjust timeline if team size or scope changes.
