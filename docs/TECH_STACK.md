# Tech Stack Recommendation — Macro Monitoring & Bias Trading Support System

## 1. Summary Table

| Layer                      | Technology                                                 | Rationale                                                                           |
| -------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Backend**                | Python 3.11+ (FastAPI)                                     | Async, type hints, quant libs (NumPy, Pandas), rich ecosystem for FRED/APIs         |
| **API**                    | FastAPI + Pydantic                                         | REST + OpenAPI, validation, async; optional GraphQL (Strawberry) later              |
| **Database (time-series)** | TimescaleDB (PostgreSQL)                                   | Hypertables, compression, retention, single SQL interface                           |
| **Database (metadata)**    | PostgreSQL (same or separate)                              | Config, users, indices, weights                                                     |
| **Caching**                | Redis                                                      | Cache API responses (bias summary, heatmap), rate limit, optional job queue/streams |
| **Scheduler**              | Apache Airflow (MWAA / self-hosted) or Kubernetes CronJobs | DAGs for ingestion + processing, retries, monitoring                                |
| **Event bus**              | Redis Streams (MVP) or Apache Kafka (scale)                | macro_data_updated, bias_computed; decouple services                                |
| **Frontend**               | React 18+ (TypeScript) + Vite                              | Component-based, charts (LightningChart / Recharts / Chart.js), tables              |
| **Charts**                 | Recharts or Lightweight Charts (TradingView)               | Heatmaps, time series, correlation matrix                                           |
| **CI/CD**                  | GitHub Actions / GitLab CI                                 | Lint, test, build image, deploy to staging/prod                                     |
| **Containers**             | Docker                                                     | Multi-stage builds; images for API, ingestion worker, bias engine                   |
| **Orchestration**          | Kubernetes (EKS/GKE) or OpenShift                          | Scaling, secrets, configmaps; alternative: ECS + Fargate                            |
| **Cloud**                  | AWS or GCP                                                 | RDS/TimescaleDB or Cloud SQL; ElastiCache/Memorystore; S3/GCS for exports           |
| **Secrets**                | AWS Secrets Manager / HashiCorp Vault                      | API keys (FRED, Investing, etc.)                                                    |
| **Logging**                | Structured JSON → CloudWatch / Stackdriver or ELK/Loki     | Request id, user, duration                                                          |
| **Monitoring**             | Prometheus + Grafana                                       | Latency, error rate, ingestion success; dashboards                                  |

---

## 2. Backend Framework

**Choice: FastAPI**

- Async I/O for many API calls (FRED, ECB) and DB connections.
- Pydantic for request/response and internal DTOs.
- OpenAPI for client generation and API docs.
- Easy to add background tasks (e.g. trigger bias run after ingestion).

Alternatives: Django + DRF (if team prefers Django ecosystem), Node.js (NestJS) if frontend team owns full-stack.

---

## 3. Database (Time-Series Optimized)

**Choice: TimescaleDB**

- PostgreSQL extension → existing SQL skills, JOINs with metadata.
- Hypertables partitioned by time → efficient range queries and compression.
- Continuous aggregates for rolling stats (e.g. 30d mean surprise per indicator).
- Retention and compression policies for cost control.

Alternative: InfluxDB if you need very high write throughput and are OK with a different query language.

---

## 4. Caching Layer

**Choice: Redis**

- Cache GET /api/v1/bias/summary, heatmap, regime (TTL e.g. 1 hour or until next run).
- Rate limiting (per API key / user).
- Optional: Redis Streams as lightweight event bus for MVP; replace with Kafka when scaling.

---

## 5. Scheduler

**Choice: Apache Airflow**

- DAGs: “daily_macro_ingestion” (per region), “rolling_stats”, “bias_engine”.
- Retries, alerting on failure, dependency between tasks.
- Run in MWAA (AWS) or GKE/OpenShift (KubernetesExecutor).

Simpler alternative: Kubernetes CronJobs + one “orchestrator” service that triggers ingestion and engine via HTTP or events.

---

## 6. CI/CD Pipeline (Conceptual)

```yaml
# Example: GitHub Actions
- Lint (Ruff/Black, ESLint)
- Unit tests (pytest, Jest/Vitest)
- Integration tests (Testcontainers: Postgres, Redis)
- Build Docker images (API, ingestion, bias-engine)
- Push to ECR/GCR
- Deploy to staging (e.g. EKS staging namespace)
- Smoke tests
- Manual approval → deploy to prod
```

- Use semantic versioning and tag images. Blue-green or canary if required later.

---

## 7. Containerization

- **Docker:** Multi-stage builds; slim base (python:3.11-slim); non-root user.
- **Images:** `macro-edge-api`, `macro-edge-ingestion`, `macro-edge-bias-engine` (and optionally UI as nginx + static).
- **Kubernetes/OpenShift:** Deployments, Services, ConfigMaps, Secrets (from Vault or cloud manager); HPA for API and workers.

---

## 8. Security

- **API:** JWT or OAuth2; API keys for programmatic access; rate limits.
- **Data sources:** All keys in Secrets Manager/Vault; no keys in repo.
- **Network:** API behind ALB/NLB with WAF; DB and Redis in private subnet; no public DB access.

---

This stack is **scalable**, **quant-grade** (Python + TimescaleDB + clear separation of layers), **production-ready** (logging, monitoring, secrets, CI/CD), and **extensible** (events, optional ML and sentiment services later).
