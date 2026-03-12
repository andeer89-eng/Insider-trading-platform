# FINTEL — Financial Intelligence Platform

A research-grade financial intelligence platform combining insider trading signals, institutional ownership analysis, and operational business metrics for all S&P 500 companies.

---

## Platform Overview

FINTEL combines the data depth of a Bloomberg Terminal with the visual storytelling of Our World in Data, applied to insider trading analytics and company operational metrics.

### Core Modules

| Module | Description |
|---|---|
| **Insider Signal Engine** | Scores every Form 4 trade 0–10 using role, size, ownership change, cluster detection, and historical alpha |
| **Cluster Detection** | Flags when multiple insiders buy the same company within a 14-day window |
| **Composite Opportunity Score** | Insider + Institutional + Business Momentum + Industry score |
| **Operational KPI Metrics** | Time-series data for 80+ company-specific KPIs (Tesla superchargers, NVIDIA datacenter revenue, AWS growth, etc.) |
| **Institutional 13F Tracker** | Parses SEC 13F filings to track BlackRock, Vanguard, Berkshire, and 12 other major holders |
| **Cross-Company Metric Comparison** | Compare any metric across multiple companies on the same chart |
| **Industry Buildout Trackers** | AI infrastructure, cloud computing, EV ecosystem, semiconductor capex |
| **KPI Discovery (AI)** | GPT-4o extracts recurring KPIs from earnings transcripts automatically |

---

## Architecture

```
External Sources (SEC EDGAR, yfinance, earnings transcripts)
        │
        ▼
ETL Pipelines (Python — daily/weekly scheduled)
        │
        ▼
PostgreSQL Database (star schema + metric registry)
        │
        ▼
FastAPI REST API (Python)
        │
        ▼
Next.js Frontend (React + TypeScript + Tailwind + Recharts)
```

### Database Design

Uses a **metric registry + time-series fact table** pattern:

```sql
metrics (id, name, category, unit, ...)
    ↓
company_metric_values (company_id, metric_id, date, value, yoy_growth)
```

This stores 500 companies × 200 metrics × 20 years = **730M+ data points** without schema changes.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) SEC EDGAR user agent email
- (Optional) OpenAI API key for KPI extraction

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start the platform

```bash
docker-compose up -d
```

### 3. Seed demo data

```bash
docker-compose exec backend python -m scripts.seed_demo_data
```

### 4. Open the app

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/api/docs

---

## Manual Setup (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=postgresql://fintel:fintel_secret@localhost:5432/fintel
uvicorn api.main:app --reload
```

### Database

```bash
# Apply migrations
psql -U fintel -d fintel -f database/migrations/001_initial_schema.sql
psql -U fintel -d fintel -f database/migrations/002_seed_data.sql
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Data Pipelines

Run manually or let the scheduler handle them:

```bash
# SEC Form 4 insider transactions (daily)
cd backend && python -m pipelines.sec_pipeline

# Market data + forward returns (daily)
python -m pipelines.market_data_pipeline

# Institutional 13F holdings (quarterly)
python -m pipelines.institutional_pipeline

# Signal scoring (daily)
python -m signals.scorer

# KPI extraction from transcripts (quarterly)
python -m pipelines.kpi_pipeline
```

### Scheduler

The `scheduler` service runs all pipelines on their configured schedules:
- SEC filings: daily 06:00 UTC
- Market data: daily 07:00 UTC
- Signal scoring: daily 08:00 UTC
- 13F holdings: weekly Monday 09:00 UTC
- KPI extraction: weekly Sunday 02:00 UTC

---

## Signal Score Methodology

Each insider purchase is scored 0–10:

| Component | Weight | Logic |
|---|---|---|
| Trade Size | 30% | $10M+ → 10, $1M+ → 7, etc. |
| Insider Role | 25% | CEO → 10, CFO → 8.5, Director → 6 |
| Ownership Change | 20% | +50% ownership → 10 |
| Historical Alpha | 15% | Win rate × avg alpha vs S&P 500 |
| Cluster Bonus | +1.0 | Multiple insiders buying within 14 days |

---

## Composite Opportunity Score

```
Composite = Insider(30%) + Institutional(25%) + Business Momentum(25%) + Industry(20%)
```

**High composite score** = insiders buying + institutions accumulating + business accelerating + industry expanding.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Charts | Recharts, D3.js |
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL 16 |
| ETL | Python (httpx, pandas, yfinance) |
| AI/LLM | OpenAI GPT-4o (KPI extraction) |
| Scheduler | APScheduler |
| Cache | Redis |
| Container | Docker Compose |

---

## API Reference

See full docs at `/api/docs` (Swagger UI) or `/api/redoc`.

Key endpoints:

```
GET  /api/dashboard                         — Homepage data
GET  /api/dashboard/signals/top             — Top insider signals
GET  /api/companies                         — All companies
GET  /api/companies/{ticker}                — Company detail
GET  /api/companies/{ticker}/summary        — Full company summary
GET  /api/insiders/transactions             — All insider trades
GET  /api/insiders/clusters/recent         — Cluster events
GET  /api/signals/sector-heatmap           — Sector sentiment
GET  /api/metrics                           — Metric registry
GET  /api/metrics/{metric}/compare          — Cross-company comparison
GET  /api/institutional/company/{ticker}    — Institutional ownership
GET  /api/institutional/net-accumulation    — Net accumulators
GET  /api/composite/leaderboard             — Opportunity leaderboard
POST /api/pipelines/run/sec-filings         — Trigger SEC pipeline
POST /api/pipelines/run/signal-scoring      — Trigger signal scoring
```

---

## Database Schema Summary

```
companies
   ├── insiders
   │      └── insider_transactions
   │                ├── insider_signal_scores
   │                └── insider_trade_outcomes
   ├── company_metric_values ← metrics (registry)
   ├── institutional_holdings ← institutional_firms
   ├── company_composite_scores
   └── insider_cluster_events
```

---

## Project Structure

```
├── backend/
│   ├── api/
│   │   ├── main.py                 — FastAPI app
│   │   └── routers/                — Endpoint modules
│   │       ├── companies.py
│   │       ├── insiders.py
│   │       ├── signals.py
│   │       ├── metrics.py
│   │       ├── institutional.py
│   │       ├── composite.py
│   │       ├── dashboard.py
│   │       └── pipelines.py
│   ├── models/
│   │   ├── database.py             — SQLAlchemy engine
│   │   └── schemas.py              — Pydantic models
│   ├── pipelines/
│   │   ├── sec_pipeline.py         — Form 4 ingestion
│   │   ├── market_data_pipeline.py — Prices + returns
│   │   ├── institutional_pipeline.py — 13F ingestion
│   │   ├── kpi_pipeline.py         — AI KPI extraction
│   │   └── scheduler.py            — APScheduler jobs
│   ├── signals/
│   │   └── scorer.py               — Signal scoring engine
│   └── scripts/
│       └── seed_demo_data.py       — Demo data generator
│
├── database/
│   └── migrations/
│       ├── 001_initial_schema.sql  — Full PostgreSQL schema
│       └── 002_seed_data.sql       — Companies + metrics registry
│
├── frontend/
│   ├── app/                        — Next.js App Router pages
│   │   ├── page.tsx                — Dashboard homepage
│   │   ├── companies/              — Company list + detail
│   │   ├── signals/                — Insider signal explorer
│   │   ├── insiders/               — All insider trades
│   │   ├── institutional/          — 13F ownership tracker
│   │   ├── metrics/                — KPI registry browser
│   │   ├── compare/                — Cross-company metric comparison
│   │   ├── industry/               — Industry buildout trackers
│   │   ├── leaderboard/            — Opportunity score leaderboard
│   │   └── settings/               — Pipeline management
│   ├── components/
│   │   ├── charts/                 — Recharts wrappers
│   │   ├── ui/                     — Reusable UI components
│   │   └── layout/                 — Sidebar + Topbar
│   └── lib/
│       ├── api.ts                  — Typed API client
│       └── utils.ts                — Formatting utilities
│
└── docker-compose.yml
```
