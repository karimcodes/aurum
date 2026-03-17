# AURUM — Weekend Macro Convexity Engine

## Quick Start

```bash
# 1. Clone/download the project
# 2. Install dependencies
pip install yfinance pandas numpy requests --break-system-packages

# 3. Run the Friday afternoon dashboard (uses free Yahoo Finance data)
python run.py

# 4. Or run with simulated data to see how the system works
python run.py --demo
```

## What This Does

Every Friday afternoon, `run.py`:

1. Pulls live gold, silver, copper, equity, and VIX data from Yahoo Finance
2. Computes the Weekend Risk Score (0-100)
3. Classifies the metals stack regime
4. Checks for holiday weekends, FOMC blackouts, and narrative shifts
5. Generates a specific trade recommendation with sizing and exit rules
6. Prints a complete dashboard to your terminal

## Project Structure

```
aurum/
├── run.py                          ← MAIN ENTRY POINT (start here)
├── data/
│   └── fetcher.py                  ← Pulls live market data (Yahoo Finance)
├── scoring/
│   └── weekend_risk_score.py       ← Weekend Risk Score engine
├── trading/
│   └── structurer.py               ← Converts WRS → option trades
├── regime/
│   └── detector.py                 ← WMCE regime state machine
├── metals/
│   ├── dispersion/
│   │   └── engine.py               ← MDI, GLS, SMB, IMDI metrics
│   └── regime/
│       └── classifier.py           ← Metals regime classifier + SRA
├── intelligence/
│   └── market_intelligence.py      ← NLP + smart money + narrative shifts
├── temporal/
│   └── tde_engine.py               ← Holiday, FOMC, Sunday night modules
└── config/
    ├── signals.yaml                ← All signal thresholds
    └── signals_metals.yaml         ← Metals stack config
```

## Usage Modes

### Mode 1: Live Friday Dashboard
```bash
python run.py
```
Run this Friday between 2:30-3:30 PM ET. It pulls real-time data and gives
you a trade/no-trade decision.

### Mode 2: Demo Mode
```bash
python run.py --demo
```
Uses simulated data to show you how the system works. Good for understanding
the output before going live.

### Mode 3: Specific Date Backtest
```bash
python run.py --date 2025-01-10
```
Runs the system as if it were that Friday, using historical data.

## What You Need

- **Python 3.10+**
- **Internet connection** (for Yahoo Finance data)
- **No API keys required** for basic operation

### Optional (for full intelligence layer):
- CFTC COT data (free, manual download from cftc.gov)
- News API key (newsapi.org, free tier = 100 requests/day)
- Broker options data (for IV surface — IBKR recommended)

## Reading the Output

The dashboard shows:

```
WEEKEND RISK SCORE:  67 / 100
RECOMMENDATION:      STANDARD
REGIME:              ACTIVE

→ Buy GLD weekly ATM straddle, 1.0% of your account
→ Entry: now (Friday 2:30-3:30 PM ET)
→ Exit: Monday 11AM if gap < 0.5%, scale out if gap > 1.5%
```

If WRS < 41, the system says NO TRADE. Trust it.
