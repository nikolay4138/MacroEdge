# Macro Monitoring & Bias Trading Support System

Production-ready система за макро мониторинг и подкрепа на bias търговия, фокусирана върху **S&P 500**, **NASDAQ 100**, **DAX 40** и **Nikkei 225**.

## Цели

- Ежедневно събиране и версиониране на макроикономически данни (FRED, ECB, BoJ, Investing, TradingEconomics и др.)
- Timezone-aware обработка (US, EU, Japan)
- **Bias Engine:** scoring от -100 до +100, regime (Risk-On/Off, Inflationary, Recessionary), confidence и risk flag
- Dashboard: heatmap, breakdown по индекси, исторически bias, correlation matrix, yield curve, export (CSV/PDF)

## Документация

| Документ                                           | Описание                                                             |
| -------------------------------------------------- | -------------------------------------------------------------------- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)       | Висока и модулна архитектура, microservice-ready, cloud              |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | ER, таблици (TimescaleDB + PostgreSQL), versioning                   |
| [docs/BIAS_ALGORITHM.md](docs/BIAS_ALGORITHM.md)   | Математическа спецификация на scoring, regime, confidence, risk flag |
| [docs/DATA_FLOW.md](docs/DATA_FLOW.md)             | Data flow диаграми, ingestion → processing → bias → API/UI           |
| [docs/TECH_STACK.md](docs/TECH_STACK.md)           | Backend, DB, cache, scheduler, CI/CD, containers, cloud              |
| [docs/ROADMAP.md](docs/ROADMAP.md)                 | MVP → V1 → V2 roadmap                                                |
| [docs/RISKS.md](docs/RISKS.md)                     | Рискове и mitigation стратегии                                       |

## Конфигурация

- `config/indicators.example.yaml` — макро индикатори (модулни, конфигурируеми)
- `config/indices.example.yaml` — индекси и региони
- `config/bias_engine.example.yaml` — параметри на Bias Engine (λ, VIX, risk flag thresholds)

Копирайте `*.example.yaml` към `*.yaml` и попълнете според средата (и премахнете example от имената ако използвате тези имена в кода).

## Структура на проекта (целева)

```
MacroEdge/
├── docs/                    # Архитектура, schema, алгоритъм, roadmap, risks
├── config/                  # YAML конфиги (indicators, indices, bias_engine)
├── migrations/              # SQL миграции (TimescaleDB + PostgreSQL)
├── services/
│   ├── ingestion/           # Data ingestion (connectors, normalizer, versioning)
│   ├── processing/          # Surprise, rolling stats, regime inputs
│   ├── bias_engine/         # Scoring, regime, confidence, risk flag
│   ├── api/                 # REST API (FastAPI)
│   └── ui/                  # Frontend (React + charts)
├── docker-compose.yml       # Local dev (Postgres/TimescaleDB, Redis)
└── README.md
```

## Tech Stack (препоръка)

- **Backend:** Python 3.11+, FastAPI
- **DB:** TimescaleDB (time-series) + PostgreSQL (metadata)
- **Cache:** Redis
- **Scheduler:** Apache Airflow или Kubernetes CronJobs
- **Frontend:** React 18+ (TypeScript), Vite, Recharts/Lightweight Charts
- **Containers:** Docker; оркестрация: Kubernetes / OpenShift
- **Cloud:** AWS или GCP

## Лиценз и отговорност

Това е система за изследователска и оперативна подкрепа. **Не представлява инвестиционно съветване.** Използвайте на свой риск и при нужда консултирайте правни/съответни лица.
