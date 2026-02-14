-- Initial schema for Macro Monitoring & Bias Trading Support System
-- Requires: PostgreSQL with TimescaleDB extension
-- Run: psql $DATABASE_URL -f 001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ========== METADATA ==========
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

CREATE TABLE macro_indicator (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(64) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(64),
    unit        VARCHAR(32),
    source_id   INT REFERENCES data_source(id),
    direction   VARCHAR(16) DEFAULT 'positive',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE index (
    id         SERIAL PRIMARY KEY,
    code       VARCHAR(32) UNIQUE NOT NULL,
    name       VARCHAR(255) NOT NULL,
    region     VARCHAR(32) NOT NULL,
    currency   CHAR(3) NOT NULL,
    timezone   VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE index_indicator_weight (
    id              SERIAL PRIMARY KEY,
    indicator_id    INT NOT NULL REFERENCES macro_indicator(id),
    index_id        INT NOT NULL REFERENCES index(id),
    weight          NUMERIC(5,4) NOT NULL CHECK (weight >= 0 AND weight <= 1),
    regime_weights  JSONB,
    UNIQUE (indicator_id, index_id)
);

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

-- ========== TIME-SERIES (HYPERTABLES) ==========
CREATE TABLE macro_observation (
    time                TIMESTAMPTZ NOT NULL,
    indicator_id        INT NOT NULL,
    release_date        DATE NOT NULL,
    actual              NUMERIC(18,6),
    forecast            NUMERIC(18,6),
    previous            NUMERIC(18,6),
    surprise            NUMERIC(18,6),
    surprise_normalized NUMERIC(18,6),
    data_version        INT NOT NULL DEFAULT 1,
    PRIMARY KEY (time, indicator_id)
);

SELECT create_hypertable('macro_observation', 'time', chunk_time_interval => INTERVAL '30 days');

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

CREATE TABLE bias_score (
    time            TIMESTAMPTZ NOT NULL,
    index_id        INT NOT NULL,
    bias_score      NUMERIC(5,2) NOT NULL CHECK (bias_score >= -100 AND bias_score <= 100),
    regime_id       INT REFERENCES market_regime(id),
    confidence_pct  NUMERIC(5,2) NOT NULL CHECK (confidence_pct >= 0 AND confidence_pct <= 100),
    risk_flag       VARCHAR(16) NOT NULL,
    components_json JSONB,
    PRIMARY KEY (time, index_id)
);

SELECT create_hypertable('bias_score', 'time', chunk_time_interval => INTERVAL '30 days');

CREATE TABLE yield_curve_snapshot (
    time         TIMESTAMPTZ NOT NULL,
    region       VARCHAR(32) NOT NULL,
    yield_2y      NUMERIC(8,4),
    yield_10y     NUMERIC(8,4),
    spread_2y10y  NUMERIC(8,4),
    PRIMARY KEY (time, region)
);

SELECT create_hypertable('yield_curve_snapshot', 'time', chunk_time_interval => INTERVAL '90 days');

CREATE TABLE volatility_snapshot (
    time     TIMESTAMPTZ NOT NULL,
    symbol   VARCHAR(32) NOT NULL,
    value    NUMERIC(12,4) NOT NULL,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('volatility_snapshot', 'time', chunk_time_interval => INTERVAL '30 days');

-- ========== INDEXES ==========
CREATE INDEX idx_macro_obs_indicator_release ON macro_observation (indicator_id, release_date DESC);
CREATE INDEX idx_bias_score_index_time ON bias_score (index_id, time DESC);
CREATE INDEX idx_macro_rolling_indicator ON macro_rolling_stats (indicator_id, time DESC);
