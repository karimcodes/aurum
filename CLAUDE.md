# CLAUDE.md — Weekend Macro Convexity Engine (WMCE)

## Internal Research Mandate | CONFIDENTIAL

**Codename:** AURUM
**Classification:** Alpha Research — Pre-Production
**Version:** 0.1.0
**Date:** 2025-02-15
**Principal Researcher:** Abdikarim
**Status:** Hypothesis Formalization & System Design

---

## I. VISION

We are building a systematic framework to detect, measure, and monetize elevated
weekend macro risk premium as expressed through gold (primary) and silver (secondary),
with structured options as the primary instrument.

**This is not a gold trading system.** It is a weekend risk premium extraction engine
that uses precious metals as the signal substrate and options as the convexity vehicle.

The system must be:
- Falsifiable before it is profitable
- Regime-aware before it is deployed
- Interpretable before it is automated

---

## II. PHILOSOPHY

### Core Beliefs (Testable)

1. **Weekend risk premium is real and has structurally increased.**
   Markets are not continuous. The Friday-close-to-Monday-open gap represents
   unhedgeable overnight risk. We hypothesize this premium has widened due to:
   - Geopolitical regime shift (multipolar instability)
   - Central bank policy divergence
   - Reduced weekend market-making depth
   - Algo withdrawal during off-hours

2. **Gold is the marginal absorber of weekend macro anxiety.**
   When institutions and macro tourists need to express fear over a weekend,
   gold is the most liquid, globally accessible, 24hr-adjacent asset.
   It moves first. Equities reprice after.

3. **Short-dated gold options misprice weekend gap risk.**
   Market makers price Friday afternoon options using realized vol from
   continuous trading. Weekend gaps introduce discontinuous moves that
   short-dated options are structurally unable to price correctly —
   particularly 0DTE and weekly expiries.

4. **Silver confirms but does not lead.**
   Silver's industrial component adds noise, but when silver gaps in
   sympathy with gold on Monday, it amplifies the signal. Divergence
   (gold gaps, silver doesn't) may indicate false positive or
   industrial-specific moves.

### Anti-Beliefs (Guardrails)

- We do NOT believe this edge is permanent.
- We do NOT believe we can predict the direction of Monday gaps.
- We do NOT believe options market makers are stupid — they will adapt.
- We do NOT believe backtests prove forward performance.
- We do NOT believe more complexity improves robustness.

---

## III. SYSTEM DESIGN PRINCIPLES

### Architecture Doctrine

```
PRINCIPLE                          IMPLEMENTATION
───────────────────────────────────────────────────────────────
Modularity over monoliths          Each layer is independently testable
Signals over predictions           We measure conditions, not forecast prices
Interpretability over accuracy     Every score component is human-readable
Regime gates over stop-losses      System turns OFF, not just sizes down
Convexity over directionality      We buy optionality, not delta
Robustness over optimization       Prefer 60% Sharpe with 0.3 drawdown over
                                   2.0 Sharpe with regime fragility
```

### Development Standards

- **Language:** Python 3.11+ (research), Rust (execution hot path if needed)
- **Data:** Parquet for historical, Redis for live state, PostgreSQL for metadata
- **Testing:** Every signal function has a unit test with synthetic edge cases
- **No black-box ML** unless: (a) interpretable wrapper exists, (b) feature
  importance is extractable, (c) performance degrades gracefully
- **Version control:** All signal parameters tracked in config YAML, never hardcoded
- **Reproducibility:** Every backtest is seeded, logged, and git-tagged

---

## IV. EDGE HYPOTHESIS — FORMAL STATEMENT

### Primary Hypothesis (H1)

> The Friday-to-Monday gold price gap exhibits statistically significant
> excess kurtosis relative to intra-week overnight gaps, and this excess
> has increased measurably over the trailing 6-10 week window.
> Short-dated gold options are systematically underpriced for this
> discontinuity, creating positive expected value in straddle/strangle
> structures purchased Friday afternoon.

### Secondary Hypothesis (H2)

> When silver exhibits sympathetic gap behavior (>70% correlation with
> gold's gap direction and >50% of gold's gap magnitude), the subsequent
> Monday session exhibits higher realized volatility in both metals and
> in equity indices, confirming a genuine macro risk event rather than
> a gold-specific flow artifact.

### Null Hypothesis (H0 — what kills the system)

> Weekend gold gaps are random, unpredictable, and not increasing in
> frequency or magnitude. Any apparent pattern is an artifact of
> small sample size (6-10 weeks ≈ 6-10 data points for weekly gaps)
> and survivorship bias in selecting gold as the observation asset.

**CRITICAL:** H0 is plausible. 6-10 weeks of data is NOT statistically
significant by any reasonable standard. The system MUST be designed to
continuously test H0 and shut down if it cannot be rejected at p < 0.05
over a rolling window.

---

## V. STRUCTURAL EDGE ANALYSIS

### Why This Edge May Exist

1. **Market structure:** Gold futures trade nearly 24h on weekdays but have
   a genuine gap from Friday 5PM ET to Sunday 6PM ET. Options expire or
   decay over this window without hedging ability.

2. **Behavioral:** Institutional risk managers reduce gross exposure before
   weekends. This creates artificial selling pressure Friday PM and buying
   pressure Monday AM if nothing bad happened (relief rally) or extreme
   gap-down if something did.

3. **Flow imbalance:** Retail and macro tourists use gold ETFs (GLD, IAU)
   which only trade during equity hours. Their Friday panic buying and
   Monday gap reaction creates predictable flow patterns.

4. **Vol surface mispricing:** The Black-Scholes assumption of continuous
   price paths is maximally violated at weekend boundaries. Short-dated
   options cannot incorporate jump risk efficiently.

### Why It May Persist (Near Term)

- Geopolitical instability is structural, not cyclical
- Central bank policy divergence (BOJ, Fed, ECB, PBOC) remains wide
- Weekend liquidity provision is not improving (opposite — algo makers
  are withdrawing from off-hours)
- Market structure changes (more 0DTE, more short-dated products) may
  actually increase the mispricing

### What Breaks It

- **Market maker adaptation:** Options desks add explicit weekend jump
  models. We'd see this as rising Friday PM IV with no change in
  realized gap magnitude.
- **Product innovation:** Weekend trading hours expand, closing the gap window.
- **Regime shift to stability:** Sustained low-vol regime compresses all
  risk premia including weekend.
- **Gold-specific structural change:** Gold ceases to be the marginal
  weekend hedge (replaced by Bitcoin, CHF, or other).
- **Crowding:** If this pattern is publicized and traded by others,
  Friday PM option prices will rise, compressing the edge.

---

## VI. SYSTEM ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────┐
│                        REGIME FILTER                             │
│            (Master switch — can disable entire system)            │
└──────────┬───────────────────────────────────────────────────────┘
           │ REGIME_ACTIVE = True/False
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                               │
│  Gold Spot/Futures │ Silver │ Equities │ Options │ News │ Vol    │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SIGNAL LAYER                              │
│  Friday Gold Behavior │ Vol Term Structure │ Gap History         │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CONFIRMATION LAYER                            │
│  Silver Sympathy │ Equity Pre-positioning │ Cross-Asset Check    │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        NLP LAYER                                 │
│  Narrative Pressure Score │ Event Calendar │ Headline Velocity   │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    RISK SCORING ENGINE                            │
│  Weekend Risk Score (0-100) │ Component Attribution              │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                  TRADE STRUCTURING ENGINE                         │
│  Instrument Selection │ Sizing │ Entry/Exit │ Greeks Mgmt        │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     EXECUTION LAYER                              │
│  Order Management │ Fill Tracking │ P&L Attribution              │
└──────────────────────────────────────────────────────────────────┘
```

### Module Specifications

#### 6.1 Data Layer

**Gold Data:**
- GC1 (front-month gold futures) — 1min bars, daily OHLCV
- GLD/IAU ETF — daily, for retail flow proxy
- XAUUSD spot — tick data if available, else 1min
- Gold futures Open Interest — daily, by expiry
- COT (Commitment of Traders) — weekly, for positioning

**Silver Data:**
- SI1 (front-month silver futures) — 1min bars, daily OHLCV
- SLV ETF — daily
- Gold/Silver ratio — derived, daily
- Silver OI — daily

**Equities:**
- ES1 (S&P 500 futures) — 1min, daily
- NQ1 (Nasdaq futures) — 1min, daily
- VIX index — daily close, intraday for Friday PM
- VIX term structure (VIX, VIX3M, VIX6M, VVIX)

**Options (Critical):**
- GC options chain — all strikes, all expiries available Friday PM
  - Key: IV by strike, IV by expiry, skew metrics
  - 0DTE (same-day or next-session expiry)
  - Weekly (5-7 DTE)
  - Monthly (20-30 DTE)
- SPX 0DTE options — IV surface Friday PM for cross-check
- Put-Call ratio on gold options — daily

**Volatility Surface:**
- GC ATM IV term structure (1D, 1W, 2W, 1M, 3M)
- GC 25-delta risk reversal by expiry
- GC variance swap levels if available (OTC proxy: VIX-equivalent for gold)
- Realized vol: 5D, 10D, 21D, 63D on GC1
- Weekend-specific realized vol (Friday close to Monday open, annualized)

**News/NLP:**
- Financial newswire headlines (Reuters, Bloomberg, Dow Jones)
- Central bank speech calendar
- Geopolitical event feeds
- Social media velocity on gold/macro keywords (optional, lower priority)

**Cross-Asset Confirmation:**
- DXY (Dollar Index) — daily, Friday PM level
- UST 10Y yield — daily
- TIP/TLT ratio — daily (inflation expectations proxy)
- Bitcoin — daily (alternative weekend hedge proxy)
- JPY, CHF — daily (safe haven currencies)

#### 6.2 Signal Layer

All signals measured as of **Friday 3:00 PM ET** (1 hour before gold futures
close on CME) to allow trade execution before weekend.

**Signal S1: Friday Gold Momentum**
```
Definition: gold_friday_return = (GC_price_friday_3pm - GC_price_friday_open) / GC_price_friday_open
Threshold:  |gold_friday_return| > 2 * median(|daily_return|, lookback=63)
Score:      0-25 based on percentile rank vs trailing 63-day distribution
```

**Signal S2: Friday Gold Volume Anomaly**
```
Definition: vol_ratio = GC_volume_friday / mean(GC_volume_weekday, lookback=21)
Threshold:  vol_ratio > 1.3
Score:      0-15 based on linear scaling from 1.0 to 2.0
```

**Signal S3: Gold Vol Term Structure Inversion**
```
Definition: vol_ts_slope = IV_1week - IV_1month (gold options ATM)
Normal:     vol_ts_slope > 0 (contango — short-dated < long-dated)
Signal:     vol_ts_slope < -2 vol points (backwardation — short-dated elevated)
Score:      0-20 based on magnitude of inversion vs trailing 63-day range
Inverse Signal: vol_ts_slope > +5 (short-dated vol crushed, possibly underpriced)
```

**Signal S4: Weekend Gap Trailing Momentum**
```
Definition: gap_magnitude = abs(monday_open - friday_close) / friday_close
Trailing:   mean(gap_magnitude, last_N_weekends) where N = 4, 8, 12
Signal:     trailing_4wk_gap_mean > trailing_12wk_gap_mean * 1.5
Score:      0-15 based on ratio magnitude
NOTE:       Extremely small sample. This is confirmatory, not primary.
```

**Signal S5: Cross-Asset Friday Stress**
```
Components:
  - VIX_change_friday > +1.5 points: +5
  - DXY_change_friday > +0.5%:       +3
  - UST10Y_change_friday > 5bps:     +2
  - Bitcoin_change_friday > +/-3%:    +5
Score:      0-15, sum of triggered components
```

#### 6.3 Confirmation Layer

**Confirmation C1: Silver Sympathy Score**
```
Definition: silver_friday_corr = correlation(GC_1min_returns, SI_1min_returns, friday_session)
            silver_friday_move = SI_friday_return / GC_friday_return
Signal:     silver_friday_corr > 0.7 AND silver_friday_move in [0.5, 2.0]
Score:      0-5 confirmation bonus
Anti-Signal: silver_friday_corr < 0.3 → reduce Weekend Risk Score by 10
             (Divergence suggests gold move is flow-driven, not macro)
```

**Confirmation C2: Equity Pre-Positioning**
```
Definition: sp500_friday_pm = ES1 return from 2PM-4PM ET
Signal:     sp500_friday_pm < -0.3% (equities selling into close)
Score:      0-5 confirmation bonus
Interpretation: Risk-off into weekend corroborates gold signal
```

#### 6.4 NLP Layer

**Narrative Pressure Score (NPS)**

Framework: Count-based with decay, NOT sentiment classification.
Rationale: Sentiment models are unreliable for financial text. Volume and
velocity of macro-risk keywords is more robust.

```python
# Pseudocode
RISK_KEYWORDS = {
    'tier1_geopolitical': ['war', 'invasion', 'nuclear', 'sanctions', 'escalation',
                           'missile', 'military', 'conflict', 'retaliation'],
    'tier1_financial':    ['default', 'contagion', 'liquidity crisis', 'bank run',
                           'margin call', 'systemic risk'],
    'tier2_central_bank': ['emergency meeting', 'rate decision', 'hawkish surprise',
                           'dovish pivot', 'QT', 'QE', 'intervention'],
    'tier2_macro':        ['recession', 'inflation surge', 'debt ceiling',
                           'downgrade', 'tariff', 'trade war'],
}

DECAY_HALFLIFE = 6  # hours

def narrative_pressure_score(headlines, timestamp_friday_3pm):
    """
    Score 0-10 based on weighted keyword velocity in trailing 48 hours.
    Tier1 keywords weighted 3x, Tier2 weighted 1x.
    Exponential decay from headline timestamp to measurement time.
    """
    score = 0
    for headline in headlines:
        age_hours = (timestamp_friday_3pm - headline.timestamp).total_seconds() / 3600
        decay = exp(-0.693 * age_hours / DECAY_HALFLIFE)
        weight = 3 if any(kw in headline.text.lower() for kw in RISK_KEYWORDS['tier1_geopolitical'] +
                          RISK_KEYWORDS['tier1_financial']) else 1
        if any(kw in headline.text.lower() for kw_list in RISK_KEYWORDS.values() for kw in kw_list):
            score += weight * decay
    return min(10, score)  # Cap at 10
```

**Event Calendar Score (ECS)**
```
Weekend events that matter:
  - G7/G20 meetings:           +5
  - OPEC meetings:             +3
  - Central bank speeches:     +2 each (max +6)
  - Election results expected: +5
  - Geopolitical deadlines:    +5

Score: 0-10, capped
```

**Combined NLP Score:** `NPS + ECS`, capped at 15, feeds into Weekend Risk Score.

#### 6.5 Risk Scoring Engine

**Weekend Risk Score (WRS) — Composite (0-100)**

```
Component                    Max Score    Type
─────────────────────────────────────────────────
S1: Friday Gold Momentum       25         Primary Signal
S2: Friday Gold Volume          15         Primary Signal
S3: Vol Term Structure          20         Primary Signal
S4: Weekend Gap Momentum        15         Confirmatory Signal
S5: Cross-Asset Stress          15         Confirmatory Signal
C1: Silver Sympathy             +5 / -10   Confirmation / Penalty
C2: Equity Pre-Positioning      +5         Confirmation
NLP: Narrative Pressure          15         Context

Gross Maximum:                  115
Penalties (C1 divergence):      -10
Net Range:                      0-105, capped at 100
```

**Score Interpretation:**
```
WRS 0-20:    No trade. Weekend premium appears normal.
WRS 21-40:   Monitor only. Log for research. Paper trade.
WRS 41-60:   Small position. Minimum viable size.
WRS 61-80:   Standard position. Core strategy size.
WRS 81-100:  Maximum position. Elevated conviction.
             BUT: If WRS > 90, also flag for potential liquidity trap
             (everyone sees the same risk → options may already be expensive)
```

**Critical Guardrail at WRS > 90:**
When the score is extremely high, it likely means the risk is obvious to all
market participants. In this case, Friday PM option premiums may already
reflect weekend risk. The system should check:
```
If WRS > 90 AND gold_option_IV_friday > 90th_percentile(trailing_63_day_IV):
    OVERRIDE: Reduce size by 50%. The edge may already be priced.
```

#### 6.6 Trade Structuring Engine

**Instrument Selection Matrix:**

```
WRS Range    Primary Structure           Sizing       Max Loss
──────────────────────────────────────────────────────────────────
41-60        Long 0DTE straddle          0.5% NAV     Premium paid
             (ATM gold options expiring
             Monday/next session)

61-80        Long weekly straddle        1.0% NAV     Premium paid
             + small 0DTE kicker         (+0.25%)
             (5-7 DTE gold options)

81-100       Long weekly strangle        1.5% NAV     Premium paid
             (5% OTM puts + calls)       (total)
             + 0DTE straddle
             + optional monthly hedge
             (sell further OTM monthly
             to fund weekly, if
             vol surface allows)
```

**Convexity Bleed Mitigation:**

The primary risk is paying theta on Fridays that produce no gap.
Mitigations:
1. **Size discipline:** Max loss per weekend = 1.5% NAV. This allows
   ~30 consecutive losing weekends before 50% drawdown — which would
   have triggered regime filter shutdown long before.
2. **Roll discipline:** Never hold 0DTE past Monday 11AM ET if gap has
   not materialized. Either take profit or cut.
3. **Spread conversion:** If WRS is 41-60 (low conviction), use debit
   spreads instead of naked straddles to reduce theta cost by ~40%.
4. **Calendar financing:** When vol term structure is in contango
   (short vol low, long vol high), sell monthly options to partially
   finance weekly purchases. Net theta should still be negative but
   reduced.

**Entry Timing:**
- Primary window: Friday 2:30-3:30 PM ET
- Gold futures options on CME close at 5:00 PM ET
- Must be filled by 4:00 PM ET to avoid last-hour illiquidity
- GLD options: close at 4:00 PM ET with equity market

**Exit Rules:**
```
Scenario                     Action
────────────────────────────────────────────────
Monday gap > 1.5%            Scale out 50% at open, trail rest
Monday gap 0.5-1.5%          Hold until 11AM, assess momentum
Monday gap < 0.5%            Cut 100% by 11AM Monday
No gap, vol crush Monday     Full loss. Log and move on.
```

#### 6.7 Regime Detection Layer

**Regime Variables:**

```python
REGIME_SIGNALS = {
    'weekend_gap_magnitude_trend': {
        # Rolling 8-week mean of |Monday gap| / |average overnight gap|
        # If this ratio falls below 1.2 for 4+ consecutive weeks → REGIME OFF
        'lookback': 8,
        'threshold': 1.2,
        'consecutive_weeks_below': 4,
    },
    'gold_vol_regime': {
        # GC 21-day realized vol percentile vs trailing 1 year
        # If below 20th percentile → REGIME OFF (low vol = no gaps)
        'lookback': 252,
        'percentile_threshold': 20,
    },
    'vix_regime': {
        # VIX level
        # If VIX < 14 for 4+ consecutive weeks → REGIME OFF
        'threshold': 14,
        'consecutive_weeks_below': 4,
    },
    'edge_profitability': {
        # Rolling 12-week P&L of the strategy
        # If cumulative return < -15% of allocated capital → REGIME OFF (hard stop)
        'lookback': 12,
        'drawdown_threshold': -0.15,
    },
    'options_pricing_adaptation': {
        # Friday PM gold IV vs Monday AM gold RV
        # If IV / RV > 1.3 consistently → edge is priced out → REGIME OFF
        'iv_rv_ratio_threshold': 1.3,
        'consecutive_weeks_above': 4,
    },
}
```

**Regime State Machine:**
```
STATES: [ACTIVE, MONITORING, DORMANT, KILLED]

ACTIVE → MONITORING:    Any 1 regime signal triggers
MONITORING → DORMANT:   2+ regime signals trigger simultaneously
DORMANT → ACTIVE:       All regime signals clear for 2 consecutive weeks
MONITORING → ACTIVE:    Triggered signal clears within 2 weeks
ANY → KILLED:           edge_profitability drawdown exceeded
KILLED → MONITORING:    Manual override only, requires written justification
```

---

## VII. RISK DOCTRINE

### Known Failure Modes

| # | Failure Mode | Probability | Impact | Mitigation |
|---|-------------|-------------|--------|------------|
| F1 | Small sample overfitting (6-10 wks) | HIGH | System is built on noise | Continuous H0 testing, regime filter |
| F2 | Options already priced for weekend risk | MEDIUM | Zero edge, pure theta bleed | IV/RV ratio check in WRS > 90 |
| F3 | Liquidity trap on Monday open | MEDIUM | Cannot exit at theoretical price | Size limits, staggered exits |
| F4 | Gold-specific event (ETF rebalance, etc.) | LOW-MEDIUM | False signal, no macro content | Silver confirmation required |
| F5 | Correlation breakdown (gold stops leading) | MEDIUM | Signal substrate changes | Cross-asset confirmation |
| F6 | Regime shift to sustained low vol | MEDIUM | No gaps to trade | VIX + gold vol regime filter |
| F7 | Industrial silver distortion | LOW | Silver gives false confirmation | Cap silver weight, monitor Au/Ag ratio |
| F8 | Sunday night liquidity gap | MEDIUM | Gaps occur in thin Asian session | Prefer CME options over OTC |
| F9 | Strategy crowding | LOW (now) → MEDIUM | Premium paid exceeds edge | IV/RV adaptation detector |

### Position Limits (Hard)

```
Maximum single-weekend risk:     1.5% of allocated NAV
Maximum rolling 4-week drawdown: 5% of allocated NAV (triggers pause)
Maximum rolling 12-week drawdown: 15% of allocated NAV (triggers KILLED state)
Maximum single instrument size:  Never > 20% of average daily volume in that option
Maximum correlated positions:    If also running equity vol, combined weekend
                                 exposure cannot exceed 2.5% NAV
```

### What We Don't Know (Explicit Uncertainty Register)

1. **Is 6-10 weeks enough data?** Almost certainly not for statistical significance.
   We are treating this as a structured hypothesis, not a proven edge.
2. **Is gold the right substrate?** Bitcoin trades 24/7 and may absorb some
   weekend risk. The signal may migrate.
3. **Are the 1000-2000% option returns real P&L or theoretical?** Need to verify
   against actual fill data. Mark-to-market ≠ realized.
4. **How much of the gap is priced into Friday PM options already?**
   This is the central question and must be answered empirically.
5. **Is the gap directional or non-directional?** If gaps are random direction,
   straddles work. If consistently one direction, we're overfitting.

---

## VIII. RESEARCH & VALIDATION PLAN

### Phase 0: Data Collection & Cleaning (Weeks 1-2)

```
Tasks:
  □ Source GC1 daily OHLCV (minimum 3 years, prefer 5)
  □ Source GC options daily snapshots (IV surface, minimum 2 years)
  □ Source SI1 daily OHLCV (same period)
  □ Source ES1, VIX, DXY daily (same period)
  □ Compute Friday-close-to-Monday-open gaps for all assets
  □ Build clean feature store in Parquet format
  □ Verify data quality: missing days, holidays, early closes

Deliverable: clean_data/ directory with verified datasets
```

### Phase 1: Manual Validation (Weeks 2-4)

```
Tasks:
  □ Manually review every weekend gap > 1% in gold over past 2 years
  □ For each: what was the macro context? Was silver sympathetic?
  □ What were Friday PM gold options priced at? (Implied vol)
  □ What was Monday realized vol? (Actual gap magnitude)
  □ Compute IV/RV ratio for each weekend
  □ Identify any structural breaks or outliers

Deliverable: manual_review.xlsx with annotated gap events
Critical Question: Is IV consistently underpricing weekend gaps?
If NO → the thesis is dead. Stop here.
```

### Phase 2: Signal Backtesting (Weeks 4-8)

```
Tasks:
  □ Implement all signals (S1-S5, C1-C2, NLP) on historical data
  □ Compute WRS for every Friday in the dataset
  □ Simulate option P&L using historical IV surfaces
  □ Use CONSERVATIVE fill assumptions:
    - Entry: Friday mid + 5% slippage toward ask
    - Exit: Monday mid - 5% slippage toward bid
    - On gap moves > 3%: assume 10% slippage
  □ Calculate strategy P&L with and without regime filter
  □ Compute: Sharpe, Sortino, max drawdown, win rate, avg win/loss

CRITICAL RULES:
  - NO parameter optimization yet. Use theoretically motivated thresholds.
  - If it doesn't work with reasonable defaults, the edge is weak.
  - Report both gross and net-of-fees P&L (assume $2/contract round-trip)

Deliverable: backtest_results/ with full P&L series and signal attribution
```

### Phase 3: Out-of-Sample Validation (Weeks 8-10)

```
Tasks:
  □ Hold out most recent 6 months of data from Phase 2
  □ Run strategy on held-out period with FROZEN parameters
  □ If in-sample Sharpe > 1.5 but out-of-sample < 0.5 → overfitting detected
  □ If WRS correctly identified high-gap weekends OOS → signal is real
  □ Compare to naive benchmark: buy straddle every Friday regardless

Deliverable: oos_results/ with comparison to in-sample and benchmarks
```

### Phase 4: Paper Trading (Weeks 10-18)

```
Tasks:
  □ Run system live every Friday, record WRS and recommended trades
  □ Track hypothetical P&L using live prices
  □ Compare to actual market outcomes
  □ After 8 weekends: formal review of signal accuracy

Decision Gate:
  If paper trading Sharpe > 0.8 AND signal correctly identifies
  4/8 gap weekends AND max single-weekend loss < 2% → proceed to live
  Otherwise → revise or shelve
```

### Phase 5: Live Deployment (Weeks 18+)

```
Tasks:
  □ Deploy with 25% of target allocation for first 4 weeks
  □ Scale to 50% if first 4 weeks confirm paper results
  □ Scale to 100% after 8 weeks if cumulative P&L positive
  □ Regime filter active from day 1

Ongoing:
  □ Weekly P&L review
  □ Monthly signal attribution review
  □ Quarterly regime reassessment
  □ Every signal retested for degradation every 13 weeks
```

---

## IX. DEVELOPMENT ROADMAP

```
Sprint   Duration   Focus                          Deliverable
──────────────────────────────────────────────────────────────────
S0       2 weeks    Data infrastructure             data_layer/ module
S1       2 weeks    Signal implementation            signal_layer/ module
S2       1 week     Confirmation layer               confirmation_layer/
S3       2 weeks    NLP pipeline                     nlp_layer/
S4       1 week     Risk scoring engine              scoring_engine/
S5       2 weeks    Backtesting framework            backtest/
S6       2 weeks    Trade structuring logic           trade_engine/
S7       1 week     Regime filter                    regime_filter/
S8       2 weeks    Integration & paper trading       system/
S9       Ongoing    Live deployment & monitoring      ops/
```

### Directory Structure

```
aurum/
├── CLAUDE.md                    # This file
├── config/
│   ├── signals.yaml             # All signal parameters (versioned)
│   ├── regime.yaml              # Regime thresholds
│   └── trading.yaml             # Position limits, sizing rules
├── data/
│   ├── ingest/                  # Raw data fetchers
│   ├── clean/                   # Cleaning & validation
│   └── store/                   # Parquet + Redis interface
├── signals/
│   ├── friday_gold.py           # S1, S2
│   ├── vol_surface.py           # S3
│   ├── gap_momentum.py          # S4
│   ├── cross_asset.py           # S5
│   └── tests/                   # Unit tests per signal
├── confirmation/
│   ├── silver.py                # C1
│   ├── equity.py                # C2
│   └── tests/
├── nlp/
│   ├── keyword_scorer.py        # NPS
│   ├── event_calendar.py        # ECS
│   └── tests/
├── scoring/
│   ├── weekend_risk_score.py    # WRS composite
│   ├── attribution.py           # Component decomposition
│   └── tests/
├── regime/
│   ├── detector.py              # Regime state machine
│   ├── signals.py               # Regime-level signals
│   └── tests/
├── trading/
│   ├── structurer.py            # Option structure selection
│   ├── sizer.py                 # Position sizing
│   ├── executor.py              # Order generation (not execution)
│   └── tests/
├── backtest/
│   ├── engine.py                # Backtest harness
│   ├── fill_model.py            # Realistic fill assumptions
│   ├── metrics.py               # Performance analytics
│   └── tests/
├── research/
│   ├── notebooks/               # Jupyter for exploration ONLY
│   ├── manual_review/           # Phase 1 artifacts
│   └── reports/                 # Formal research memos
└── ops/
    ├── scheduler.py             # Friday run trigger
    ├── alerting.py              # Discord/Slack notifications
    ├── logging.py               # Structured logging
    └── dashboard.py             # Performance dashboard
```

---

## X. TESTING DOCTRINE

### Every Signal Must Have:

1. **Unit test with synthetic data** — known input → known output
2. **Edge case test** — holidays, early closes, missing data, zero volume
3. **Monotonicity test** — if input risk increases, score must not decrease
4. **Stability test** — small input perturbations don't cause score jumps > 10%
5. **Historical sanity check** — does it flag known macro weekends? (COVID crash,
   SVB weekend, Russia/Ukraine invasion Friday, etc.)

### Backtest Must Report:

- Number of trades
- Win rate
- Average win / average loss ratio
- Maximum consecutive losses
- Maximum drawdown (peak-to-trough)
- Sharpe ratio (annualized, using Friday-to-Monday returns)
- Sortino ratio
- Calmar ratio
- P&L attribution by signal component
- Comparison to null strategy (random Friday straddle)

### Red Flags That Kill the Project:

- In-sample Sharpe > 3.0 (almost certainly overfit)
- Out-of-sample Sharpe < 0.3 (no edge)
- Win rate > 70% (suspicious for option buying strategy)
- More than 40% of P&L comes from < 5% of trades (tail dependence)
- Signal cannot identify any known macro weekends in backtesting

---

## XI. EXPANSION PATH

### Phase A: Cross-Asset Weekend Premium (Month 6+)

If gold weekend premium is real, test for:
- **Equity index options:** Do SPX/ES weekend gaps also exhibit excess kurtosis?
- **Currency options:** Do USDJPY/USDCHF gap at weekends?
- **Crypto:** Bitcoin trades 24/7 but Friday-Sunday vol may differ from weekday vol.
- **Rates:** Treasury futures gap behavior at weekend.

### Phase B: Broader Macro Stress Engine (Month 9+)

The signal framework (keyword NLP + vol surface + cross-asset confirmation) can
generalize beyond weekends:
- **FOMC week premium extraction**
- **Geopolitical event premium** (pre-election, pre-summit)
- **Earnings season vol surface dislocations**

### Phase C: Adaptive Regime Engine (Month 12+)

The regime detection layer can become a standalone product:
- **Regime classification:** Low-vol / Normal / Stress / Crisis
- **Dynamic allocation:** Shift from premium selling → premium buying as regime changes
- **Multi-strategy orchestration:** Turn strategies on/off based on regime state

---

## XII. HONEST ASSESSMENT

### Probability This Works as Described: ~25-35%

Reasons for skepticism:
1. 6-10 weeks of observation is not statistical evidence
2. Options market makers are sophisticated and well-capitalized
3. "1000-2000% returns" in options are usually mark-to-mid, not realizable
4. Weekend gaps in gold are not new; they've existed forever
5. The hypothesis conflates several potentially independent phenomena

Reasons for cautious optimism:
1. Structural market changes (geopolitical, monetary) are real
2. 0DTE option pricing is genuinely difficult and may be systematically wrong
3. The framework is designed to detect its own failure
4. Even if the edge is smaller than hypothesized, the structure captures what exists
5. The research infrastructure has value beyond this single strategy

### What We're Really Building:

Even if this specific trade doesn't work, we are building:
- A macro signal aggregation engine
- A regime detection framework
- An options backtesting infrastructure
- A disciplined research process

These have lasting value regardless of whether gold gaps on Monday.

---

## XIII. GLOSSARY

| Term | Definition |
|------|-----------|
| WRS | Weekend Risk Score — composite 0-100 |
| NPS | Narrative Pressure Score — NLP-derived |
| ECS | Event Calendar Score |
| GC1 | Front-month gold futures |
| SI1 | Front-month silver futures |
| IV | Implied Volatility |
| RV | Realized Volatility |
| 0DTE | Zero Days To Expiration (same-day options) |
| DTE | Days To Expiration |
| ATM | At The Money |
| OTM | Out of The Money |
| NAV | Net Asset Value (portfolio value) |
| COT | Commitment of Traders report |
| Theta | Time decay — cost of holding options |
| Gamma | Rate of change of delta — the "convexity" in option payoffs |
| Straddle | Long ATM call + ATM put (profit from large moves either direction) |
| Strangle | Long OTM call + OTM put (cheaper, needs bigger move) |

---

*This document is a living research mandate. It should be updated as
evidence accumulates. Every decision must be justified. Every assumption
must be testable. If the edge doesn't exist, the system should tell us
that clearly and early.*

**End of CLAUDE.md**
