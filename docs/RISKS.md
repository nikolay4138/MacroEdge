# Risks & Mitigation — Macro Monitoring & Bias Trading Support System

## 1. Data & API Risks

| Risk                                                   | Impact                                       | Likelihood | Mitigation                                                                                                                    |
| ------------------------------------------------------ | -------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **API rate limits / blocking** (FRED, Investing, etc.) | Ingestion fails; stale data                  | Medium     | Respect rate limits; backoff/retry; multiple sources per indicator where possible; cache responses; consider paid tiers       |
| **Schema or format changes** from providers            | Parsing errors; missing data                 | Medium     | Normalize behind adapters; contract tests per connector; alert on parsing failures; versioned raw response storage (optional) |
| **Revised macro figures** (e.g. second estimate GDP)   | Bias computed on stale actual                | Low        | Store `data_version`; re-run ingestion and bias when revisions are published; document revision policy in UI                  |
| **Missing or delayed releases** (holidays, late data)  | Lower confidence; incomplete heatmap         | Medium     | Confidence formula accounts for coverage; UI shows “missing” clearly; do not treat missing as zero surprise                   |
| **Timezone / release-time errors**                     | Wrong date attribution; double-count or skip | Medium     | Store all in UTC; use provider release calendar; integration tests with fixed fixtures per timezone                           |

---

## 2. Quant & Model Risks

| Risk                                                 | Impact                                  | Likelihood                | Mitigation                                                                                               |
| ---------------------------------------------------- | --------------------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Weights or regime rules wrong for current regime** | Misleading bias; poor trading decisions | Medium                    | Weights and regime rules in config/DB; backtesting in V2; periodic review with quant; disclaimer in UI   |
| **Overfitting** (future ML regime/bias)              | Good in-sample, poor out-of-sample      | High (if ML done naively) | Train/validation/test split; walk-forward; avoid too many features; regularisation                       |
| **Surprise normalization breaks** (e.g. new outlier) | Skewed contribution of one indicator    | Low                       | Cap normalized surprise (e.g. ±3σ); monitor distribution of surprises; alert on extreme values           |
| **Regime lag**                                       | Bias reflects previous regime           | Medium                    | Use leading inputs (yield curve, VIX); consider regime transition smoothing; document lag in methodology |

---

## 3. Operational & Infra Risks

| Risk                        | Impact                            | Likelihood | Mitigation                                                                                         |
| --------------------------- | --------------------------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| **DB or Redis down**        | API errors; no new bias           | Low        | HA for DB (replicas); Redis Sentinel or cluster; health checks and restart policies; runbooks      |
| **Scheduler/job failure**   | No daily ingestion or bias        | Medium     | Airflow retries and alerts; dead-letter queue; manual trigger path; monitor “last successful run”  |
| **Secrets leak** (API keys) | Abuse of third-party APIs; revoke | Low        | Secrets in Vault/Secrets Manager only; no secrets in code or config repo; rotate keys periodically |
| **Runaway cost** (cloud)    | Budget overrun                    | Medium     | Resource limits; retention/compression on time-series; cost alerts; review instance sizes          |

---

## 4. Security & Compliance Risks

| Risk                               | Impact           | Likelihood | Mitigation                                                                                     |
| ---------------------------------- | ---------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| **Unauthorised API access**        | Data leak; abuse | Medium     | Auth (JWT/OAuth2); API keys for services; rate limiting; WAF                                   |
| **Personal data** (if users added) | GDPR etc.        | Low        | Prefer minimal PII; document retention; consent and deletion process if needed                 |
| **Liability** (bias as “advice”)   | Legal/regulatory | Medium     | Clear disclaimer: not investment advice; for research/support only; optional compliance review |

---

## 5. Extensibility & Technical Debt

| Risk                                            | Impact                                | Likelihood | Mitigation                                                                  |
| ----------------------------------------------- | ------------------------------------- | ---------- | --------------------------------------------------------------------------- |
| **Tight coupling** (ingestion ↔ engine)         | Hard to add sources or change logic   | Medium     | Event-driven design; clear interfaces; config-driven weights and indicators |
| **Monolith growth**                             | Slow deployments; scaling limits      | Medium     | Keep services split (ingestion, engine, API); avoid shared “god” modules    |
| **Inconsistent config** (weights in code vs DB) | Confusion; wrong production behaviour | Medium     | Single source of truth (DB or config service); validate on deploy           |

---

## 6. Summary

- **Highest priority:** Reliable ingestion (rate limits, parsing, timezones) and **correct attribution of bias** (weights, regime, disclaimer).
- **Next:** Operational resilience (scheduler, DB/Redis HA, monitoring) and **cost control**.
- **Ongoing:** Backtesting and review of scoring/regime; secrets and auth; clear disclaimer and compliance where applicable.

All mitigations are aligned with the architecture (modular, config-driven, event-driven) and the roadmap (MVP → V1 → V2).
