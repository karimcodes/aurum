<div align="center">

# Nexus Alpha

### Quantitative Signal Aggregation & Market Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178c6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  <strong>A sophisticated quantitative trading system that detects market regime shifts, aggregates multi-factor signals, and generates risk-adjusted trade recommendations using real-time market data.</strong>
</p>

[Live Demo](#) · [Documentation](#architecture) · [API Reference](#api-endpoints)

</div>

---

## Overview

**Nexus Alpha** is a full-stack quantitative finance platform that combines signal processing, regime detection, and NLP-driven market intelligence to identify asymmetric risk/reward opportunities in derivatives markets.

Built with a microservices architecture, the system processes 19+ market instruments in real-time, applies a 7-signal composite scoring engine, and delivers actionable trade recommendations through both a REST API and a real-time dashboard.

### Key Highlights

- **Multi-Factor Signal Engine** — Aggregates momentum, volatility, cross-asset correlation, and sentiment signals into a unified risk score
- **Regime Detection State Machine** — 5-signal system that monitors edge degradation and automatically disables trading during unfavorable conditions
- **NLP Market Intelligence** — Real-time headline analysis with keyword velocity tracking, narrative shift detection, and event calendar integration
- **Full-Stack Dashboard** — Dark-mode trading terminal UI with real-time WebSocket updates, historical analysis, and backtesting visualizations

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│            Next.js 14 │ React 18 │ TailwindCSS │ Recharts           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API / WebSocket
┌────────────────────────────────▼────────────────────────────────────┐
│                           API LAYER                                 │
│                    FastAPI │ Pydantic │ SQLAlchemy                  │
│   /analysis │ /history │ /backtest │ /trades │ /nlp │ /regime       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────┐
│                        INTELLIGENCE LAYER                           │
├─────────────────┬─────────────────┬─────────────────┬───────────────┤
│  Signal Engine  │ Regime Detector │  NLP Analyzer   │ Risk Scoring  │
│  (7 signals)    │ (5-state FSM)   │ (keyword+decay) │ (composite)   │
└─────────────────┴─────────────────┴─────────────────┴───────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────┐
│                          DATA LAYER                                 │
│              Yahoo Finance │ SQLite │ Redis (optional)              │
│           19 instruments │ 252-day rolling window │ 1-min bars      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Signal Processing Engine
| Signal | Description | Weight |
|--------|-------------|--------|
| **S1** Momentum Analysis | Friday price momentum vs 63-day distribution | 25% |
| **S2** Volume Anomaly | Institutional flow detection via volume spikes | 15% |
| **S3** Volatility Term Structure | IV curve inversion detection | 20% |
| **S4** Gap Momentum | Rolling gap magnitude trend analysis | 15% |
| **S5** Cross-Asset Stress | VIX, DXY, UST, BTC correlation signals | 15% |
| **C1** Confirmation Layer | Silver sympathy / divergence detection | ±10% |
| **NLP** Narrative Pressure | Headline velocity + keyword scoring | 15% |

### Regime Detection
Finite state machine with automatic edge monitoring:

```
ACTIVE ──▶ MONITORING ──▶ DORMANT ──▶ KILLED
   ▲            │              │
   └────────────┴──────────────┘
         (recovery path)
```

- **Gap magnitude degradation** — Detects when market structure changes
- **Volatility regime shifts** — Monitors RV percentile vs historical
- **Edge profitability tracking** — Rolling P&L with automatic shutdown
- **IV/RV adaptation** — Detects when options markets price in the edge

### NLP Intelligence
- Real-time headline ingestion from multiple sources
- Tier-weighted keyword scoring (geopolitical, financial, macro)
- Exponential decay model (6-hour half-life)
- Velocity tracking across 1h/6h/24h windows
- Narrative shift detection with acceleration alerts

### Dashboard
- **Real-time score gauge** with signal attribution
- **Historical performance** charts with outcome tracking
- **Backtesting engine** with equity curves and drawdown analysis
- **Trade journal** with P&L tracking and annotations
- **Event calendar** integration for scheduled market events

---

## Tech Stack

**Backend**
- Python 3.11+
- FastAPI (async REST API)
- SQLAlchemy 2.0 (ORM)
- Pydantic v2 (validation)
- NumPy / Pandas (numerical computing)

**Frontend**
- Next.js 14 (React framework)
- TypeScript 5.0+
- TailwindCSS (styling)
- Recharts (visualizations)
- React Query (server state)

**Infrastructure**
- SQLite (development) / PostgreSQL (production)
- Redis (optional caching layer)
- Railway / Vercel (deployment)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/karimcodes/nexus-alpha.git
cd nexus-alpha

# Backend setup
pip install -r requirements.txt

# Frontend setup
cd web && npm install && cd ..
```

### Running Locally

```bash
# Terminal 1: Start API server
python -m api.main

# Terminal 2: Start frontend
cd web && npm run dev
```

- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000

### CLI Mode

```bash
# Live analysis (real market data)
python run.py

# Demo mode (simulated data)
python run.py --demo

# Historical backtest
python run.py --date 2025-01-10
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analysis/current` | GET | Run live signal analysis |
| `/api/analysis/demo` | GET | Run with simulated data |
| `/api/history/wrs` | GET | Historical score data |
| `/api/history/outcomes` | GET | Prediction vs outcome tracking |
| `/api/backtest/run` | POST | Execute backtest simulation |
| `/api/backtest/signals` | GET | Signal performance attribution |
| `/api/trades` | GET/POST | Trade journal CRUD |
| `/api/nlp/analysis` | GET | Full NLP intelligence report |
| `/api/regime/status` | GET | Current regime state |

Full API documentation available at `/docs` (Swagger UI) or `/redoc`.

---

## Project Structure

```
nexus-alpha/
├── api/                    # FastAPI application
│   ├── main.py             # App entry point
│   ├── schemas.py          # Pydantic models
│   └── routers/            # Route handlers
├── scoring/                # Signal processing engine
│   └── weekend_risk_score.py
├── regime/                 # Regime detection FSM
│   └── detector.py
├── intelligence/           # NLP & market analysis
│   ├── market_intelligence.py
│   ├── nlp_analyzer.py
│   └── event_calendar.py
├── metals/                 # Sector analysis
│   ├── dispersion/         # Cross-asset metrics
│   └── regime/             # Sector regime classifier
├── trading/                # Trade structuring
│   └── structurer.py
├── temporal/               # Time-based modules
│   └── tde_engine.py
├── db/                     # Database layer
│   ├── models.py
│   ├── crud.py
│   └── database.py
├── web/                    # Next.js frontend
│   ├── app/                # App router pages
│   ├── components/         # React components
│   └── lib/                # API client & utilities
├── config/                 # Configuration files
│   ├── signals.yaml
│   └── signals_metals.yaml
└── run.py                  # CLI entry point
```

---

## Configuration

All signal parameters are externalized in YAML for easy tuning without code changes:

```yaml
# config/signals.yaml
s1_friday_momentum:
  max_score: 25
  lookback_days: 63
  threshold_multiplier: 2.0

s3_vol_term_structure:
  max_score: 20
  inversion_threshold: -2.0
```

---

## Performance

The system is designed for low-latency signal generation:

| Operation | Latency |
|-----------|---------|
| Full signal computation | ~200ms |
| NLP headline analysis | ~150ms |
| API response (cached) | <50ms |
| Dashboard render | <100ms |

---

## Roadmap

- [ ] WebSocket real-time updates
- [ ] Options Greeks integration
- [ ] ML-based signal weighting
- [ ] Multi-asset expansion (FX, crypto)
- [ ] Mobile app (React Native)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with precision for the modern quant.**

[⬆ Back to Top](#nexus-alpha)

</div>
