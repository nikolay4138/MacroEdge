# Database Schema — Macro Monitoring & Bias Trading Support System

## 1. Technology Choice

- **Primary time-series:** TimescaleDB (PostgreSQL extension) for macro observations, surprise series, and bias scores.
- **Metadata / config:** PostgreSQL (same cluster or separate): indices, indicators, weights, users.
- **Rationale:** Single SQL interface, hypertables for retention/compression, continuous aggregates for rolling stats.

---

## 2. Core Entities (ER Overview)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   data_source   │     │   macro_indicator│     │     index       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │     │ id              │
│ name            │     │ code            │     │ code            │
│ provider        │     │ name            │     │ name            │
│ config_json     │     │ category        │     │ region          │
│ timezone        │     │ unit            │     │ currency        │
└────────┬────────┘     │ source_id (FK)  │     └────────┬────────┘
         │              └────────┬────────┘              │
         │                       │                       │
         │              ┌────────▼────────┐     ┌───────▼────────┐
         │              │ indicator_index │     │ index_weight    │
         │              │ _mapping        │     │ (weight by      │
         │              ├─────────────────┤     │  index)         │
         │              │ indicator_id    │     ├─────────────────┤
         │              │ index_id        │     │ indicator_id    │
         │              │ weight          │     │ index_id        │
         │              └────────┬────────┘     │ weight          │
         │                       │             │ regime_weights  │
         │                       │             └─────────────────┘
         │              ┌────────▼────────────────────────┐
         │              │ macro_observation (HYPERTABLE)   │
         │              ├─────────────────────────────────┤
         │              │ time (TIMESTAMPTZ)               │
         │              │ indicator_id                     │
         │              │ release_date (date)             │
         │              │ actual, forecast, previous       │
         │              │ surprise, surprise_normalized   │
         │              │ data_version                     │
         │              └────────┬────────────────────────┘
         │                       │
         │              ┌────────▼────────────────────────┐
         │              │ bias_score (HYPERTABLE)         │
         │              ├────────────────────────────────┤
         │              │ time (TIMESTAMPTZ)              │
         │              │ index_id                        │
         │              │ bias_score (-100..+100)         │
         │              │ regime_id                       │
         │              │ confidence_pct                  │
         │              │ risk_flag                       │
         │              │ components_json                 │
         │              └────────────────────────────────┘
         │
         └─────────────┐
                       │
         ┌─────────────▼─────────────┐     ┌─────────────────┐
         │ market_regime (lookup)    │     │ yield_curve_snap │
         ├───────────────────────────┤     │ (HYPERTABLE)    │
         │ id                        │     ├─────────────────┤
         │ code (risk_on, risk_off..)│     │ time            │
         │ name                      │     │ region          │
         └──────────────────────────┘     │ yield_2y, 10y   │
                                           │ spread_2y10y    │
                                           └─────────────────┘
```

---

## 3. Table Definitions

### 3.1 Metadata Tables (PostgreSQL)

```sql
-- Data sources (FRED, ECB, Investing, etc.)
CREATE TABLE data_source (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(32) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    provider    VARCHAR(64) NOT NULL,
    config_json JSONB,
    timezone    VARCHAR(64) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Macro indicators (configurable, from screenshots/structure)
CREATE TABLE macro_indicator (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(64) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(64),  -- inflation, employment, growth, etc.
    unit        VARCHAR(32),
    source_id   INT REFERENCES data_source(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Supported indices (S&P 500, NASDAQ 100, DAX 40, Nikkei 225)
CREATE TABLE index (
    id         SERIAL PRIMARY KEY,
    code       VARCHAR(32) UNIQUE NOT NULL,
    name       VARCHAR(255) NOT NULL,
    region     VARCHAR(32) NOT NULL,
    currency   CHAR(3) NOT NULL,
    timezone   VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Which indicator affects which index and with what weight (and optional regime overrides)
CREATE TABLE index_indicator_weight (
    id              SERIAL PRIMARY KEY,
    indicator_id    INT NOT NULL REFERENCES macro_indicator(id),
    index_id       INT NOT NULL REFERENCES index(id),
    weight         NUMERIC(5,4) NOT NULL CHECK (weight >= 0 AND weight <= 1),
    regime_weights JSONB,  -- e.g. {"risk_on": 1.2, "risk_off": 0.8}
    UNIQUE (indicator_id, index_id)
);

-- Market regime lookup
CREATE TABLE market_regime (
    id     SERIAL PRIMARY KEY,
    code   VARCHAR(32) UNIQUE NOT NULL,
    name   VARCHAR(255) NOT NULL
);

INSERT INTO market_regime (code, name) VALUES
    ('risk_on', 'Risk-On'),
    ('risk_off', 'Risk-Off'),
    ('inflationary', 'Inflationary'),
    ('recessionary', 'Recessionary'),
    ('neutral', 'Neutral');
```

### 3.2 Time-Series Tables (TimescaleDB Hypertables)

```sql
-- Raw/normalized macro observations (one row per release)
CREATE TABLE macro_observation (
    time                TIMESTAMPTZ NOT NULL,
    indicator_id        INT NOT NULL,
    release_date        DATE NOT NULL,
    actual              NUMERIC(18,6),
    forecast            NUMERIC(18,6),
    previous           NUMERIC(18,6),
    surprise           NUMERIC(18,6),   -- actual - forecast
    surprise_normalized NUMERIC(18,6),  -- scaled for cross-indicator comparison
    data_version        INT NOT NULL DEFAULT 1,
    PRIMARY KEY (time, indicator_id)
);

SELECT create_hypertable('macro_observation', 'time', chunk_time_interval => INTERVAL '30 days');

-- Optional: rolling stats per indicator (materialized or computed on read)
CREATE TABLE macro_rolling_stats (
    time         TIMESTAMPTZ NOT NULL,
    indicator_id INT NOT NULL,
    window_days  INT NOT NULL,
    mean_actual  NUMERIC(18,6),
    std_actual   NUMERIC(18,6),
    trend_slope  NUMERIC(18,6),
    PRIMARY KEY (time, indicator_id, window_days)
);

SELECT create_hypertable('macro_rolling_stats', 'time', chunk_time_interval => INTERVAL '90 days');

-- Bias output per index per evaluation time
CREATE TABLE bias_score (
    time            TIMESTAMPTZ NOT NULL,
    index_id        INT NOT NULL,
    bias_score      NUMERIC(5,2) NOT NULL CHECK (bias_score >= -100 AND bias_score <= 100),
    regime_id       INT REFERENCES market_regime(id),
    confidence_pct  NUMERIC(5,2) NOT NULL CHECK (confidence_pct >= 0 AND confidence_pct <= 100),
    risk_flag       VARCHAR(16) NOT NULL,  -- low, medium, high
    components_json JSONB,
    PRIMARY KEY (time, index_id)
);

SELECT create_hypertable('bias_score', 'time', chunk_time_interval => INTERVAL '30 days');

-- Yield curve snapshots (for regime / volatility context)
CREATE TABLE yield_curve_snapshot (
    time        TIMESTAMPTZ NOT NULL,
    region      VARCHAR(32) NOT NULL,
    yield_2y    NUMERIC(8,4),
    yield_10y   NUMERIC(8,4),
    spread_2y10y NUMERIC(8,4),
    PRIMARY KEY (time, region)
);

SELECT create_hypertable('yield_curve_snapshot', 'time', chunk_time_interval => INTERVAL '90 days');

-- Volatility context (VIX, MOVE, etc.)
CREATE TABLE volatility_snapshot (
    time     TIMESTAMPTZ NOT NULL,
    symbol   VARCHAR(32) NOT NULL,
    value    NUMERIC(12,4) NOT NULL,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('volatility_snapshot', 'time', chunk_time_interval => INTERVAL '30 days');
```

### 3.3 Data Versioning

- `macro_observation.data_version`: increment when a release is revised (e.g. second estimate).
- Optional table `macro_observation_audit` (same columns + `updated_at`, `revision`) for full history; otherwise overwrite with new version and log in app.

---

## 4. Indexes (Additional)

```sql
CREATE INDEX idx_macro_obs_indicator_release ON macro_observation (indicator_id, release_date DESC);
CREATE INDEX idx_bias_score_index_time ON bias_score (index_id, time DESC);
CREATE INDEX idx_macro_rolling_indicator ON macro_rolling_stats (indicator_id, time DESC);
```

---

## 5. Retention & Compression (TimescaleDB)

- **macro_observation:** retain 15+ years; compression after 1 year.
- **bias_score:** retain 10+ years; compression after 1 year.
- **yield_curve_snapshot / volatility_snapshot:** retain 5+ years; compression after 6 months.

(Exact policies set via `add_retention_policy` and `add_compression_policy`.)

---

This schema supports: timezone-aware storage (TIMESTAMPTZ), versioning, per-index and per-regime weights, and all required outputs (bias score, regime, confidence, risk flag, components) for the Bias Engine and UI.
