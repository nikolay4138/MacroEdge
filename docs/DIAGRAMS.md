# Architecture & Data Flow Diagrams (Mermaid)

## System Context

```mermaid
C4Context
    title System Context - Macro Edge
    Person(user, "Trader / Analyst", "Consumes bias and macro views")
    System(macro_edge, "Macro Edge", "Bias & macro monitoring")
    System_Ext(fred, "FRED / ECB / BoJ", "Macro data APIs")
    Rel(user, macro_edge, "Uses dashboard, export, alerts")
    Rel(macro_edge, fred, "Fetches macro data")
```

## Container Diagram (High Level)

```mermaid
flowchart TB
    subgraph "Macro Edge"
        UI[Web UI]
        API[REST API]
        Ingestion[Ingestion Service]
        Engine[Bias Engine]
        Scheduler[Scheduler]
    end
    subgraph "Data"
        TS[(TimescaleDB)]
        PG[(PostgreSQL)]
        Redis[(Redis)]
    end
    subgraph "External"
        FRED[FRED API]
        ECB[ECB API]
    end
    UI --> API
    API --> Engine
    API --> TS
    API --> Redis
    Ingestion --> FRED
    Ingestion --> ECB
    Ingestion --> TS
    Ingestion --> PG
    Scheduler --> Ingestion
    Scheduler --> Engine
    Engine --> TS
    Engine --> PG
    Engine --> Redis
```

## Data Flow (Simplified)

```mermaid
sequenceDiagram
    participant Sched as Scheduler
    participant Ing as Ingestion
    participant DB as TimescaleDB
    participant Eng as Bias Engine
    participant API as REST API
    participant UI as Dashboard

    Sched->>Ing: Trigger daily run
    Ing->>DB: Write macro_observation
    Ing->>Eng: Event: macro_data_updated
    Eng->>DB: Read weights, regime, history
    Eng->>DB: Write bias_score
    Eng->>API: Event: bias_computed
    UI->>API: GET /bias/summary, /macro/heatmap
    API->>DB: Query
    API->>UI: JSON
```

## Bias Scoring Flow (Logic)

```mermaid
flowchart LR
    A[Normalized surprises] --> B[Regime-adjusted weights]
    B --> C[S_raw = Σ w_i * s_i]
    C --> D[Map to -100..+100]
    D --> E[Bias Score]
    F[VIX / Yield] --> G[Confidence & Risk flag]
    E --> H[Output]
    G --> H
```

## Database ER (Simplified)

```mermaid
erDiagram
    data_source ||--o{ macro_indicator : has
    macro_indicator ||--o{ macro_observation : "time series"
    index ||--o{ index_indicator_weight : has
    macro_indicator ||--o{ index_indicator_weight : "weight by"
    index ||--o{ bias_score : "time series"
    market_regime ||--o{ bias_score : "regime"
    macro_observation }|--|| time : "partition by"
    bias_score }|--|| time : "partition by"
```

These diagrams can be rendered in any Mermaid-compatible viewer (e.g. GitHub, GitLab, or VS Code with a Mermaid extension).
