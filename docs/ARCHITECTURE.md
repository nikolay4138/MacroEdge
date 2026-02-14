# Macro Monitoring & Bias Trading Support System — Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Web UI     │  │  REST API    │  │  Export      │  │  Alerts      │          │
│  │  (Dashboard) │  │  (BFF/API)   │  │  CSV/PDF     │  │  Telegram    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼─────────────────┼─────────────────┼─────────────────┼──────────────────┘
          │                 │                 │                 │
┌─────────┼─────────────────┼─────────────────┼─────────────────┼──────────────────┐
│         │     APPLICATION / BIAS ENGINE LAYER │                 │                  │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌───────▼──────┐  ┌───────▼──────┐           │
│  │ Bias Engine  │  │ Regime       │  │ Scoring      │  │ Alert        │           │
│  │ (Core Logic) │  │ Detector     │  │ Calculator   │  │ Service      │           │
│  └──────┬───────┘  └──────┬───────┘  └───────┬──────┘  └───────┬──────┘           │
│         │                 │                  │                 │                  │
│  ┌──────▼─────────────────▼──────────────────▼─────────────────▼──────┐           │
│  │                    Event Bus (Kafka / Redis Streams)                 │           │
│  └──────┬─────────────────────────────────────────────────────────────┘           │
└─────────┼─────────────────────────────────────────────────────────────────────────┘
          │
┌─────────┼─────────────────────────────────────────────────────────────────────────┐
│         │     PROCESSING / DATA LAYER                                              │
│  ┌──────▼───────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐         │
│  │ Macro Data   │  │ Surprise      │  │ Rolling       │  │ Regime        │         │
│  │ Processor    │  │ Index Calc    │  │ Window Calc   │  │ Classifier    │         │
│  └──────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘         │
│         │                  │                  │                  │                 │
│  ┌──────▼──────────────────▼──────────────────▼──────────────────▼──────┐        │
│  │                    Data Ingestion Layer (Orchestrator)                 │        │
│  │  FRED │ Investing │ TradingEconomics │ ECB │ Fed │ BoJ │ Custom       │        │
│  └──────┬───────────────────────────────────────────────────────────────┘        │
└─────────┼─────────────────────────────────────────────────────────────────────────┘
          │
┌─────────┼─────────────────────────────────────────────────────────────────────────┐
│         │     PERSISTENCE & CACHE                                                  │
│  ┌──────▼───────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐         │
│  │ TimescaleDB  │  │ PostgreSQL    │  │ Redis         │  │ S3 / Blob     │         │
│  │ (Time-series)│  │ (Metadata)    │  │ (Cache/Queue) │  │ (Exports)     │         │
│  └──────────────┘  └───────────────┘  └───────────────┘  └───────────────┘         │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Modular Component Boundaries

| Layer              | Responsibility                                       | Key Modules                                           |
| ------------------ | ---------------------------------------------------- | ----------------------------------------------------- |
| **Data Ingestion** | Fetch, normalize, version, store macro + market data | Connectors (FRED, ECB, etc.), Normalizer, Versioning  |
| **Processing**     | Surprise index, rolling stats, regime inputs         | SurpriseCalculator, RollingStats, YieldCurveProcessor |
| **Bias Engine**    | Scoring, regime, confidence, risk flags              | BiasScorer, RegimeDetector, WeightResolver            |
| **Visualization**  | Dashboards, charts, export                           | Web UI, API (BFF), ExportService                      |
| **Orchestration**  | Scheduling, events, refresh                          | Scheduler (Airflow/Cron), Event Bus                   |

---

## 3. Microservice-Ready Design

- **Data Ingestion Service** — standalone; can scale by region/source.
- **Bias Engine Service** — stateless; consumes events, writes scores.
- **API / BFF** — REST + optional GraphQL; auth, rate limit, caching.
- **UI** — SPA; talks only to API.
- **Scheduler** — triggers ingestion and engine runs; idempotent jobs.

**Inter-service communication:**

- **Sync:** REST for UI → API, API → Bias Engine (on-demand).
- **Async:** Event-driven refresh (e.g. "macro_data_updated", "bias_computed"); Kafka or Redis Streams.

---

## 4. Security & Operations

- **Auth:** JWT/OAuth2 for API; API keys for external data sources (vault/secrets).
- **Network:** API behind WAF; ingestion in private subnet; DB no public access.
- **Logging:** Structured JSON (request id, user, service); centralised (e.g. ELK/Loki).
- **Monitoring:** Metrics (Prometheus), health endpoints, alerting (PagerDuty/Opsgenie).
- **Secrets:** Vault / cloud secret manager; no secrets in code or config repo.

---

## 5. Cloud-Ready Deployment (AWS Example)

- **Compute:** ECS/EKS for API + Bias Engine; Lambda for lightweight ingestion triggers.
- **Data:** RDS (PostgreSQL) + TimescaleDB extension or dedicated TimescaleDB; ElastiCache (Redis).
- **Events:** MSK (Kafka) or Redis Streams.
- **Storage:** S3 for exports, backup, versioned configs.
- **Scheduler:** EventBridge + Step Functions or MWAA (Airflow).
- **CI/CD:** CodeBuild/CodePipeline or GitLab CI; images in ECR; deploy to ECS/EKS.

Same concepts map to GCP (Cloud Run, GKE, Pub/Sub, BigQuery for analytics, Cloud Scheduler) and OpenShift (same containers, OpenShift pipelines).

---

## 6. Extensibility Hooks

- **ML Regime Detection:** New consumer of "macro_data_updated"; writes "regime_signal" to event bus; Bias Engine subscribes.
- **Sentiment Layer:** Separate ingestion → events → optional extra input into Bias Engine (future weight).
- **Backtesting:** Read-only use of stored macro + bias time series; separate Backtest Service.
- **Alerts:** Alert Service subscribes to "bias_computed" and "regime_changed"; rules engine → email/Telegram.

All new features integrate via events and REST without changing core ingestion or scoring contracts.
