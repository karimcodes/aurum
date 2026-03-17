# CLAUDE.md — Appendix A: Metals Stack Integration Layer (MSIL)

## Version 0.2.0 — Metals Stack Macro Regime Engine (MS-MRE)

**Codename:** AURUM / FERRUM
**Classification:** Alpha Research — Pre-Production
**Version:** 0.2.0
**Date:** 2026-02-15
**Principal Researcher:** Abdikarim
**Status:** Expansion Design — Pending Phase 0 Validation
**Prerequisite:** WMCE (v0.1.0) must pass Phase 2 backtest before MSIL goes live.

---

## PREAMBLE — WHAT THIS IS AND IS NOT

This appendix defines the **Metals Stack Integration Layer (MSIL)**, an expansion
module that adds cross-metal regime intelligence to the existing WMCE system.

**What this IS:**
- A regime classification layer that uses metals complex dispersion to improve
  WMCE signal quality and false positive filtering
- A structured framework for identifying *which type* of macro environment is
  driving gold behavior (stress vs. capex cycle vs. speculative rotation)
- An optional secondary convexity module for non-gold metals, with its own
  independent risk budget

**What this IS NOT:**
- A replacement for WMCE. Gold weekend convexity remains the primary alpha module.
- A metals momentum strategy. We are not buying "hot" metals.
- A thematic bet on AI infrastructure, uranium, or any narrative.
- An increase in system complexity without testable justification.

**Structural relationship:**

```
┌────────────────────────────────────────────────────┐
│              REGIME INTELLIGENCE LAYER              │
│                                                    │
│   WMCE Regime Filter (v0.1)                        │
│        +                                           │
│   MSIL Regime Classifier (v0.2) ← THIS DOCUMENT   │
│        =                                           │
│   Unified Regime State (AND logic, not OR)          │
│                                                    │
├────────────────────────────────────────────────────┤
│                                                    │
│   WMCE (PRIMARY)          MTCE (SECONDARY)         │
│   Gold Weekend Convexity   Metals Thematic         │
│   Max 1.5% NAV/weekend     Max 0.75% NAV/week     │
│   Proven edge required     Independent validation  │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Critical constraint:** MSIL cannot increase WMCE position size. It can only:
1. Improve regime classification (reduce false positives)
2. Add a secondary, independently budgeted convexity module
3. Provide research intelligence for future strategy development

---

## I. STRATEGIC FRAMEWORK — STRUCTURAL METALS REGIMES

We define 5 observable regime states across the metals complex. Each is
characterized by measurable cross-asset behaviors, not narratives.

### Regime 1: MACRO STRESS DOMINANT

**Observable behaviors:**
- Gold outperforms all base metals on 5/10/21-day basis
- Gold/Copper ratio rising (flight from cyclical to safe haven)
- Gold miners (GDX) underperform gold spot (miners are equities, gold is haven)
- VIX elevated and rising
- Silver underperforms gold (Au/Ag ratio expanding)
- USD strengthening against EM currencies

**Measurable indicators:**
```
gold_copper_ratio_z = z_score(GC/HG ratio, lookback=63 trading days)
gold_leadership = (GC_21d_return - median(stack_21d_returns)) / std(stack_21d_returns)
gdx_gc_divergence = GDX_21d_return - GC_21d_return
vix_level > 20
au_ag_ratio_change_21d > +2%
```

**Invalidating conditions:**
- Gold/Copper ratio falling while gold rises → capex regime, not stress
- GDX outperforming gold → risk-on, not stress
- VIX declining → stress narrative is wrong

**WMCE interaction:** This is the **highest-value regime for WMCE**. Weekend
gaps in gold are most likely to be large and macro-driven when this regime
is active. MSIL should boost WMCE confidence, not size.

### Regime 2: AI INFRASTRUCTURE CAPEX

**Observable behaviors:**
- Copper outperforms gold on 10/21-day basis
- Aluminum and silicon-adjacent proxies (RIO, FCX) outperform precious metals
- Uranium (URA) stable or rising (energy infrastructure)
- Gold flat or drifting — no safe-haven bid
- Rare earths (MP) showing relative strength
- Equity VIX low and stable

**Measurable indicators:**
```
copper_gold_ratio_z = z_score(HG/GC ratio, lookback=63)
industrial_precious_spread = mean(HG_ret, AL_ret) - mean(GC_ret, SI_ret), 21d
ura_momentum = URA_21d_return > 0 AND URA > URA_50d_MA
vix_level < 18
copx_gdx_spread = COPX_21d_return - GDX_21d_return
```

**Invalidating conditions:**
- Copper rolling over while gold accelerates → regime shift to stress
- VIX spiking → capex narrative is wrong
- Rare earths collapsing → supply chain thesis unwinding

**WMCE interaction:** This is a **low-value regime for WMCE**. Weekend gaps
in gold are less likely to be significant. MSIL should reduce WMCE conviction
but not force shutdown — gold can still gap on geopolitical events regardless
of capex environment.

**Null hypothesis:** "AI infrastructure capex" is a narrative, not a measurable
flow. Copper may be rallying for unrelated reasons (China stimulus, housing).
We test this by measuring whether copper/aluminum/rare earth correlation to
semiconductor capex announcements is > 0 with p < 0.05 over a 2-year window.
If not, this regime label is misleading and should be renamed "Industrial
Cyclical Strength."

### Regime 3: SPECULATIVE ROTATION

**Observable behaviors:**
- High dispersion across metals (some up sharply, others down)
- Lithium and/or nickel showing extreme moves (>2σ)
- Thematic ETFs (LIT, URA) experiencing volume spikes > 2x average
- Gold miners diverging from gold spot in both directions
- Short-interest changes in metals equities

**Measurable indicators:**
```
metals_dispersion_index (MDI) > 75th percentile
single_metal_outlier = any metal with |z_score(21d_return)| > 2.0
thematic_etf_volume_ratio = max(LIT_vol, URA_vol, COPX_vol) / mean(their_vol_21d) > 2.0
breadth_divergence = |pct_metals_above_20d_high - pct_metals_below_20d_low| < 0.2
```

**Invalidating conditions:**
- All metals moving together (low dispersion) → this is a macro move, not rotation
- Volume spikes are absent → price moves may be illiquid, not speculative

**WMCE interaction:** **Neutral to slightly negative** for WMCE. High
dispersion means gold's weekend gap may be driven by gold-specific flows
(rotation into gold as part of spec pattern) rather than macro risk.
Silver confirmation becomes more important.

### Regime 4: ENERGY GEOPOLITICS

**Observable behaviors:**
- Uranium (URA) showing relative strength
- Gold rising but Copper also stable (not risk-off pattern)
- Oil correlated with metals moves (energy cost pass-through)
- Aluminum elevated (energy-intensive production)
- Rare earths moving on supply chain concerns (MP, REMX)

**Measurable indicators:**
```
ura_relative_strength = URA_21d_return - median(stack_21d_returns)
energy_metals_corr = correlation(CL1_daily_returns, AL/HG_basket_returns, 21d)
gold_copper_ratio_stable = |z_score(GC/HG, 63d)| < 1.0
aluminum_energy_beta = rolling_beta(AL_returns, CL1_returns, 63d) > 0.3
```

**Invalidating conditions:**
- Oil declining while metals rally → metals move is demand-driven, not energy
- Uranium declining → energy geopolitics thesis is wrong for current period
- Gold/Copper ratio expanding → this is stress, not energy geopolitics

**WMCE interaction:** **Moderate value** for WMCE. Geopolitical weekends
(sanctions, military events) are high-gap-probability events. If energy
metals are confirming geopolitical stress, WMCE conviction should increase.

### Regime 5: LOW-VOL STABILITY

**Observable behaviors:**
- All metals in tight range (low dispersion, low vol)
- Gold realized vol in bottom quartile
- VIX < 14 sustained
- No single metal showing >1σ moves
- Open interest declining across complex (participants leaving)

**Measurable indicators:**
```
MDI < 25th percentile
gold_rv_21d_percentile < 25
vix_level < 14 for 3+ consecutive weeks
max_metal_zscore = max(|z_score(each_metal_21d_return)|) < 1.0
aggregate_OI_change_21d < -5%
```

**Invalidating conditions:**
- Any single metal breaking out (>2σ) → regime transitioning
- VIX jumping → stability ending

**WMCE interaction:** This triggers **WMCE regime filter shutdown** (already
defined in v0.1.0 via VIX + gold vol regime signals). MSIL confirms what
WMCE already suspects.

---

## II. METALS STACK DATA SPECIFICATION

### Futures

| Instrument | Symbol | Bucket | Frequency | Features Required |
|-----------|--------|--------|-----------|-------------------|
| Gold | GC1 | Precious/Monetary | 1min, Daily | OHLCV, OI, IV surface (already in WMCE) |
| Silver | SI1 | Precious/Industrial | 1min, Daily | OHLCV, OI (already in WMCE) |
| Copper | HG1 | Industrial/Cyclical | Daily | OHLCV, OI |
| Aluminum | ALI (LME) | Industrial/Energy | Daily | OHLCV, OI if available |
| Platinum | PL1 | Precious/Industrial | Daily | OHLCV |
| Palladium | PA1 | Industrial/Auto | Daily | OHLCV |

**Note on Uranium:** No liquid uranium futures exist. Use URA ETF as proxy.
This introduces ETF-specific risks (rebalancing, creation/redemption) that
must be accounted for. Uranium "price" via Sprott Physical Uranium Trust
(SRUUF/U.UN) can serve as a secondary cross-check.

### Equities / ETFs

| Instrument | Ticker | Bucket | Frequency | Features Required |
|-----------|--------|--------|-----------|-------------------|
| Gold Miners | GDX | Precious Mining | Daily | OHLCV, IV (options chain exists) |
| Copper Miners | COPX | Industrial Mining | Daily | OHLCV, Volume |
| Uranium ETF | URA | Energy/Nuclear | Daily | OHLCV, Volume |
| Lithium ETF | LIT | Battery/Speculative | Daily | OHLCV, Volume |
| Rare Earth | MP | Supply Chain | Daily | OHLCV, Volume |
| Freeport-McMoRan | FCX | Copper/Gold Major | Daily | OHLCV, IV (options chain) |
| Rio Tinto | RIO | Diversified Mining | Daily | OHLCV |
| Newmont | NEM | Gold Major | Daily | OHLCV, IV (options chain) |
| Agnico Eagle | AEM | Gold Major | Daily | OHLCV |
| Barrick Gold | GOLD | Gold Major | Daily | OHLCV |

### Derived Ratios (Computed Daily)

| Ratio | Formula | Interpretation |
|-------|---------|----------------|
| Gold/Copper | GC1 / HG1 | Monetary vs cyclical preference |
| Gold/Silver | GC1 / SI1 | Already in WMCE; stress gauge |
| Gold/Platinum | GC1 / PL1 | Monetary premium over industrial precious |
| GDX/GC | GDX / GC1 (normalized) | Miner leverage vs spot — equity risk appetite |
| COPX/GDX | COPX / GDX | Industrial vs precious mining sentiment |
| Industrial/Precious | (HG + AL basket) / (GC + SI basket) | Cyclical vs monetary macro state |

### Data Quality Requirements

- Minimum 5 years daily history for all instruments (2020-2025)
- For instruments that didn't exist 5 years ago (MP IPO'd 2020), use
  maximum available with explicit notation of shorter sample
- All prices adjusted for splits, distributions
- ETF data must note rebalancing dates
- Missing data: forward-fill max 1 day, then flag as gap
- Holiday alignment: use NYSE calendar, flag non-US holidays where
  LME (aluminum) trades but CME doesn't

---

## III. DISPERSION & RELATIVE STRENGTH ENGINE

### 3.1 Metals Dispersion Index (MDI)

**Purpose:** Measure how "spread out" metals returns are across the complex.
High dispersion → metals responding to different drivers (rotation, thematic).
Low dispersion → metals moving together (macro, risk-on/off).

**Formula:**
```python
def metals_dispersion_index(returns_dict: dict[str, float], lookback: int = 21) -> float:
    """
    MDI = cross-sectional standard deviation of trailing {lookback}-day
    returns across the metals stack, normalized to 0-100 scale using
    trailing 252-day percentile rank.

    Inputs:
        returns_dict: {ticker: cumulative_return_over_lookback}
        For stack: GC1, SI1, HG1, ALI, PL1, PA1
        (Futures only — ETFs excluded to avoid structural bias)

    Returns:
        MDI score 0-100 (percentile rank)
    """
    cross_sectional_std = std(list(returns_dict.values()))
    # Percentile rank vs trailing 252-day distribution of this metric
    return percentile_rank(cross_sectional_std, trailing_252d_values)
```

**Lookback:** 21 trading days (1 month) for primary signal.
Also compute 5-day MDI for rapid regime shift detection.

**Interpretation bands:**
```
MDI 0-25:     Low dispersion. Metals moving together. Macro-driven.
              → WMCE confidence: NEUTRAL to POSITIVE (macro = gold gaps likely)
MDI 25-50:    Normal dispersion. No strong signal.
              → WMCE confidence: No adjustment
MDI 50-75:    Elevated dispersion. Rotation or thematic activity.
              → WMCE confidence: SLIGHTLY NEGATIVE (gold may be rotation target, not macro)
MDI 75-100:   Extreme dispersion. Individual metals decoupled.
              → WMCE confidence: NEGATIVE (gold signal may be noise, not macro)
              → BUT: if gold is the OUTLIER, could be strong macro stress signal
```

**Null hypothesis (H0_MDI):** Metals dispersion has no predictive relationship
with gold weekend gap magnitude. Test: correlation between Friday MDI and
|Monday gold gap| over 5-year sample. If Pearson r < 0.1 and p > 0.1 → MDI
does not inform WMCE and should be used for research only, not live scoring.

### 3.2 Gold Leadership Score (GLS)

**Purpose:** Determine whether gold is leading the metals stack (suggesting
gold-driven macro stress) or following it (suggesting broad cyclical move).

**Formula:**
```python
def gold_leadership_score(daily_returns: pd.DataFrame, lookback: int = 21) -> dict:
    """
    GLS has three components:

    1. Gold Return Rank: Where does GC rank in the stack by trailing return?
       - Rank 1/6 (best performer) → Score +2
       - Rank 2/6 → Score +1
       - Rank 5-6/6 (worst performer) → Score -2

    2. Gold Lead-Lag: Does gold move BEFORE the stack?
       - Cross-correlate GC daily returns with stack average at lags -5 to +5 days
       - If max correlation is at lag > 0 (gold leads) → Score +2
       - If max correlation is at lag < 0 (gold lags) → Score -1
       - If max correlation is at lag 0 (simultaneous) → Score 0

    3. Gold Beta Deviation: Is gold's beta to equities abnormal?
       - Rolling 21d beta of GC to ES1
       - If beta < -0.2 (gold negatively correlated with equities) → Score +2
         (True haven behavior)
       - If beta > +0.2 (gold moving with equities) → Score -2
         (Risk-on, not haven)

    Total GLS range: -5 to +6
    Normalized to -100 to +100
    """
```

**Interpretation:**
```
GLS > +50:   Gold is leading the stack with haven characteristics.
             → WMCE relevance: HIGH. Weekend gaps likely macro-driven.
GLS 0 to +50: Gold moderately leading. Normal conditions.
             → WMCE relevance: NEUTRAL.
GLS -50 to 0: Gold lagging the stack. Cyclical metals leading.
             → WMCE relevance: REDUCED. Gold is not the marginal risk absorber.
GLS < -50:   Gold is a laggard. Stack is in industrial/cyclical mode.
             → WMCE relevance: LOW. Consider reducing WRS by 10-15 points.
```

**Null hypothesis (H0_GLS):** Gold's rank in the metals stack has no
relationship to the magnitude or probability of weekend gold gaps.
Test: Compare average |Monday gold gap| when GLS > +50 vs GLS < -50.
If difference is not significant at p < 0.05 → GLS does not inform WMCE.

### 3.3 Stack Momentum Breadth (SMB)

**Purpose:** Measure how many metals are in uptrends vs downtrends.
Provides context for whether gold strength is isolated or broad.

**Formula:**
```python
def stack_momentum_breadth(prices: pd.DataFrame) -> dict:
    """
    For universe: GC1, SI1, HG1, ALI, PL1, PA1, GDX, COPX, URA, NEM, FCX

    Compute:
    1. pct_above_20d_high: % of instruments at 20-day high
    2. pct_above_50d_ma: % of instruments above 50-day moving average
    3. industrial_precious_divergence:
         mean_return(HG, AL, PL, PA, COPX, FCX) - mean_return(GC, SI, GDX, NEM)
         over 21 days

    Breadth Score = (pct_above_50d_ma * 50) + (pct_above_20d_high * 30) +
                    (1 if industrial_precious_divergence < -2% else 0) * 20

    Range: 0-100
    """
```

**Interpretation:**
```
SMB > 70:    Broad metals strength. Risk-on environment.
             → WMCE impact: Gold gaps less likely to be stress-driven.
SMB 30-70:   Mixed. Normal.
             → WMCE impact: No adjustment.
SMB < 30:    Broad metals weakness OR precious-only strength.
             → If gold is strong AND SMB < 30 → strong macro stress signal
             → If gold is weak AND SMB < 30 → everything is selling, be cautious
```

**Null hypothesis (H0_SMB):** Breadth of metals momentum has no relationship
to gold weekend gap behavior. Test same framework as MDI and GLS.

### 3.4 Industrial-Monetary Divergence Index (IMDI)

**Purpose:** Directly measure whether "monetary" metals (gold, silver) are
diverging from "industrial" metals (copper, aluminum, platinum). This is
the clearest signal of macro stress vs cyclical expansion.

**Formula:**
```python
def industrial_monetary_divergence(prices: pd.DataFrame, lookback: int = 21) -> float:
    """
    IMDI = mean_return(GC, SI) - mean_return(HG, AL, PL) over lookback period.

    Positive: Monetary metals outperforming → stress or debasement fear
    Negative: Industrial metals outperforming → growth/capex cycle
    Near zero: No divergence → no clear regime signal

    Normalized as z-score against trailing 252 days.
    """
```

**Null hypothesis (H0_IMDI):** The industrial-monetary divergence provides
no incremental information beyond what the Gold/Copper ratio already captures.
Test: Regress IMDI on GC/HG ratio. If R² > 0.8, IMDI is redundant and should
be dropped to reduce complexity.

---

## IV. REGIME INTEGRATION WITH WMCE

### 4.1 Integration Architecture

MSIL feeds into WMCE's existing regime filter as an **advisory input**, not
a veto. The WMCE regime filter (v0.1.0) retains full authority to shut down
the system independently.

```
WMCE Regime Filter (v0.1.0)          MSIL Regime Classifier (v0.2.0)
     │                                        │
     │  5 existing signals                    │  MDI, GLS, SMB, IMDI
     │  (gap trend, gold vol,                 │  → Regime State:
     │   VIX, P&L, IV/RV)                    │    STRESS / CAPEX / ROTATION /
     │                                        │    ENERGY_GEO / LOW_VOL
     │                                        │
     └──────────────┬─────────────────────────┘
                    │
                    ▼
         UNIFIED REGIME STATE
         ─────────────────────
         Rule: WMCE filter can VETO independently.
               MSIL can only ADJUST WRS ±15 points.
               MSIL CANNOT force a trade.
               MSIL CANNOT override a WMCE shutdown.
```

### 4.2 WRS Adjustment Rules

MSIL produces a **Stack Regime Adjustment (SRA)** that modifies the Weekend
Risk Score from v0.1.0. Range: -15 to +10 points.

```
Detected Regime           GLS        MDI       SRA Adjustment
──────────────────────────────────────────────────────────────
MACRO STRESS              > +50      < 50      +10 (gold gaps more likely)
MACRO STRESS              > +50      > 50      +5  (mixed — stress but dispersed)
AI INFRA CAPEX            < 0        < 50      -10 (gold irrelevant)
AI INFRA CAPEX            > 0        < 50      -5  (gold still leading despite capex)
SPECULATIVE ROTATION      any        > 75      -15 (gold signal is noise)
ENERGY GEOPOLITICS        > 0        25-75     +5  (geopolitical = weekend gaps)
LOW VOL STABILITY         any        < 25      -10 (already captured by WMCE filter)
```

**Critical constraint:** SRA is additive to WRS but subject to:
1. WRS + SRA is still capped at 100
2. WRS + SRA cannot go below 0
3. SRA of +10 does NOT increase position size — it increases confidence
   that the regime is favorable, which may prevent premature shutdown
4. SRA of -15 CAN prevent a trade by pushing WRS below the 41-point threshold

### 4.3 Override Logic

```
IF WMCE_regime_state == KILLED:
    SRA is ignored entirely. System is off.

IF WMCE_regime_state == DORMANT:
    SRA is logged for research but not applied.

IF WMCE_regime_state == MONITORING:
    SRA is applied but trade recommendation capped at SMALL.

IF WMCE_regime_state == ACTIVE:
    SRA is fully applied to WRS.
    MSIL regime state is logged alongside WRS for attribution.
```

### 4.4 Example Scenarios

**Scenario A: Geopolitical escalation weekend**
```
WMCE signals: S1 high, S5 high, NLP high → WRS = 78
MSIL: GLS = +65, MDI = 35, IMDI = +1.8σ → Regime: MACRO STRESS
SRA: +10
Adjusted WRS: 88 → MAXIMUM position
```

**Scenario B: AI capex rotation, gold quiet**
```
WMCE signals: S1 low, S2 low → WRS = 25
MSIL: GLS = -40, MDI = 30, COPX leading → Regime: AI INFRA CAPEX
SRA: -10
Adjusted WRS: 15 → NO TRADE (correctly filtered)
```

**Scenario C: Speculative frenzy in lithium, gold spiking**
```
WMCE signals: S1 high (gold moved) → WRS = 55
MSIL: GLS = +20, MDI = 82 → Regime: SPECULATIVE ROTATION
SRA: -15
Adjusted WRS: 40 → MONITOR (gold spike may be rotation, not macro)
```

---

## V. METALS THEMATIC CONVEXITY ENGINE (MTCE)

### Secondary Alpha Module — Independent Risk Budget

MTCE is a **separate convexity extraction module** that activates only when
specific stack regimes are detected. It operates on metals equities options
rather than futures, and has its own risk budget completely independent of WMCE.

### 5.1 MTCE Design Principles

```
PRINCIPLE                              IMPLEMENTATION
───────────────────────────────────────────────────────────────
Independent of WMCE                    Separate P&L, separate risk budget
Regime-gated activation                Only trades when MSIL detects regime
No weekend-specific                    Can trade any day when conditions met
Lower conviction by default            Max 50% of WMCE allocation
Equity options, not futures            GDX, FCX, COPX, URA, NEM options
Must prove itself independently        Own backtest, own OOS validation
```

### 5.2 Trigger Conditions

MTCE can activate in **two regime states only:**

**Regime 1 — MACRO STRESS (Precious Metals Focus):**
```
Trigger:
  MSIL_regime == MACRO_STRESS
  AND GLS > +50
  AND GDX_IV_percentile < 50 (miners vol not yet elevated — edge exists)
  AND GDX_realized_vol_21d > GDX_implied_vol (RV > IV — options cheap)

Instrument: GDX calls/puts, NEM straddles
Logic: Gold miners tend to gap with gold but options price miner-specific
       risk (equity risk) rather than gold-gap risk. If gold is leading
       in macro stress AND miner vol is cheap, buy miner straddles.

Position Size: Max 0.5% NAV per trade
Max Open Exposure: 0.75% NAV (MTCE total, all positions)
```

**Regime 4 — ENERGY GEOPOLITICS (Uranium/Copper Focus):**
```
Trigger:
  MSIL_regime == ENERGY_GEOPOLITICS
  AND URA_21d_return_zscore > +1.5
  AND URA_option_IV < URA_realized_vol (if URA options exist with sufficient liquidity)
  OR
  AND FCX_21d_return_zscore > +1.5
  AND FCX_option_IV < FCX_realized_vol

Instrument: URA calls (if liquid), FCX straddles, COPX calls
Logic: Energy geopolitics creates sustained directional moves in uranium
       and copper miners. If vol is underpriced, buy optionality.

Position Size: Max 0.5% NAV per trade
Max Open Exposure: 0.75% NAV
```

### 5.3 Trade Structuring for MTCE

```
Instrument         Preferred Structure     Tenor        Max Premium
─────────────────────────────────────────────────────────────────────
GDX                ATM straddle            2-4 week     0.5% NAV
NEM                ATM straddle            2-4 week     0.3% NAV
FCX                ATM straddle            2-4 week     0.5% NAV
COPX               Long calls (if regime   2-4 week     0.3% NAV
                   is directional capex)
URA                Long calls (if liquid)  Monthly      0.3% NAV

CRITICAL: No single-name equity option > 0.3% NAV.
          ETF options (GDX, COPX, URA) may go to 0.5% NAV.
          Total MTCE exposure NEVER exceeds 0.75% NAV.
          MTCE allocation NEVER exceeds 50% of WMCE allocation
          without independent Phase 3 validation of MTCE specifically.
```

### 5.4 MTCE Exit Rules

```
Scenario                              Action
──────────────────────────────────────────────────────
MSIL regime changes away from trigger  Close all MTCE positions within 2 days
Position > +100% gain                  Take profit on 50%, trail remainder
Position at -50% of premium            Cut immediately
Time decay: 7 DTE remaining            Close unless position is profitable
WMCE enters KILLED state               Close all MTCE positions immediately
```

### 5.5 MTCE Failure Modes

| # | Failure Mode | Probability | Impact | Mitigation |
|---|-------------|-------------|--------|------------|
| M1 | Miner-specific idiosyncratic event (strike, accident, political) | MEDIUM | Position loss unrelated to thesis | Max 0.3% NAV single-name |
| M2 | ETF rebalancing distortion | LOW-MEDIUM | Artificial price moves at rebalance dates | Flag rebalance calendar, don't trade ±2 days |
| M3 | Illiquidity in URA/COPX options | MEDIUM | Can't exit at reasonable price | Strict 20% ADV limit, prefer monthly over weekly |
| M4 | Correlation with WMCE during stress | MEDIUM | Double loss on bad weekends | Combined exposure cap of 2.0% NAV |
| M5 | Regime misclassification | MEDIUM | Trade wrong metals in wrong regime | Regime must be confirmed for 5+ days before MTCE activates |

### 5.6 MTCE Regime Off Switch

```
MTCE shuts down independently of WMCE if:
  - MTCE rolling 8-week P&L < -5% of allocated MTCE capital
  - More than 60% of MTCE trades are losers over trailing 12 trades
  - MSIL regime classifier fails to identify regimes correctly for 4+ weeks
    (measured by: regime detected, trade placed, expected behavior doesn't occur)

MTCE can resume after:
  - All shutdown conditions clear for 2 consecutive weeks
  - Written review of what went wrong
```

---

## VI. TESTING & VALIDATION PLAN

### Phase 0-M: Data Collection for Metals Stack (Weeks 1-3)

```
Tasks:
  □ Source HG1, ALI, PL1, PA1 daily OHLCV (5 years)
  □ Source GDX, COPX, URA, LIT, MP, FCX, RIO, NEM, AEM, GOLD daily (5 years)
  □ Source GDX, FCX, NEM options IV snapshots (2+ years)
  □ Compute all derived ratios (Gold/Copper, Gold/Silver, IMDI, etc.)
  □ Build metals stack Parquet feature store
  □ Verify data quality, flag short-history instruments
  □ Note: LIT inception 2010, MP IPO July 2020, URA inception 2010

Deliverable: metals_data/ directory
```

### Phase 1-M: Historical Dispersion Analysis (Weeks 3-6)

```
Tasks:
  □ Compute MDI, GLS, SMB, IMDI for every trading day in 5-year sample
  □ Cluster analysis: Do the 5 proposed regimes appear naturally?
    - Use k-means on [MDI, GLS, IMDI, VIX] with k=3,4,5,6
    - Compare cluster composition to our proposed regime definitions
    - If clusters don't match proposed regimes → revise regime definitions
  □ Compute regime transition frequencies
    - How often does regime change? (If < 2x per year → too slow to be useful)
    - How long does each regime persist? (If < 5 days → too noisy)
  □ Visualize: regime timeline overlaid on gold price

Deliverable: regime_analysis/ with cluster results and regime timeline

CRITICAL QUESTION: Do these regimes actually exist in the data,
or are we imposing narrative structure on noise?
If cluster analysis produces no clear separation → stop. Regimes are fiction.
```

### Phase 2-M: Predictive Power Testing (Weeks 6-10)

```
Tasks:
  □ Test MDI → gold weekend gap relationship
    - Regress |Monday gold gap| on Friday MDI
    - Hypothesis: MDI is informative (R² > 0.05, p < 0.05)
  □ Test GLS → gold weekend gap relationship
    - Compare mean gap when GLS > +50 vs GLS < -50
    - Hypothesis: GLS > +50 produces larger gaps (p < 0.05)
  □ Test IMDI → next-week gold realized vol
    - Regress 5-day GC realized vol on trailing IMDI
    - Hypothesis: IMDI > 0 (monetary leading) → higher next-week vol
  □ Test SRA adjustment on historical WRS
    - Recompute WRS + SRA for all Fridays in backtest period
    - Does adjusted WRS predict gaps BETTER than unadjusted?
    - Measure: improvement in hit rate, improvement in Sharpe
  □ Test each metric INDEPENDENTLY before combining
    - No combining until individual metrics show significance

CRITICAL RULES:
  - If NO metric shows significance at p < 0.05 → MSIL adds no value.
    Keep it as research-only. Do not integrate into live WMCE.
  - If ONLY 1 metric shows significance → use only that metric.
    Do not drag in the others for "completeness."
  - R² thresholds are deliberately low (> 0.05). We're looking for
    marginal improvement, not prediction. In finance, R² of 0.05
    with stable OOS performance is excellent.

Deliverable: predictive_tests/ with regression outputs and significance tests
```

### Phase 3-M: Out-of-Sample Validation (Weeks 10-12)

```
Tasks:
  □ Hold out most recent 12 months from Phase 2-M
  □ Run regime classifier and SRA on held-out period
  □ Compare WRS+SRA performance vs WRS-only performance
  □ Does MSIL reduce false positives? (Weekends where WRS was high but gap was small)
  □ Does MSIL correctly identify regime shifts?

Decision Gate:
  If SRA improves WMCE Sharpe by > 0.15 OOS → integrate into live
  If SRA shows no improvement OOS → keep as research/dashboard only
  If SRA degrades WMCE OOS → kill MSIL integration entirely

Deliverable: oos_metals/ with side-by-side comparison
```

### Phase 4-M: MTCE Backtest (Weeks 12-16, only if Phase 3-M passes)

```
Tasks:
  □ Backtest MTCE trades using regime triggers
  □ Conservative fill assumptions (same as WMCE: 5-10% slippage)
  □ For mining equities: add additional 2% slippage for single names
  □ Compute MTCE standalone P&L
  □ Compute MTCE correlation with WMCE P&L
  □ If correlation > 0.6 → MTCE is just WMCE with more risk → kill it

Deliverable: mtce_backtest/ with standalone and combined metrics
```

### Red Flags That Kill Stack Expansion

```
1. Cluster analysis shows no natural regime separation → regimes are fiction
2. No individual metric (MDI, GLS, SMB, IMDI) is significant at p < 0.05 → noise
3. SRA adjustment degrades WMCE OOS → MSIL is counterproductive
4. MTCE P&L correlation with WMCE > 0.6 → not independent alpha
5. In-sample improvement > 3x out-of-sample improvement → overfit
6. Regime classifier changes state > 3x per month → too noisy to trade
7. Regime classifier changes state < 1x per quarter → too slow to be useful
```

---

## VII. RISK DOCTRINE EXTENSION

### New Failure Modes (Added to v0.1.0 Table)

| # | Failure Mode | Probability | Impact | Mitigation |
|---|-------------|-------------|--------|------------|
| F10 | Sector crowding in metals miners | MEDIUM | Correlated drawdowns across GDX/NEM/AEM | Max 0.3% NAV single-name, 0.75% total MTCE |
| F11 | ETF rebalancing distortion | LOW-MEDIUM | Artificial price/vol signals around rebalance | Flag rebalance dates, exclude ±2 trading days |
| F12 | Miner-specific idiosyncratic risk | MEDIUM | Mine accident, labor dispute, political expropriation | Diversify across 3+ miners, cap single-name |
| F13 | Liquidity trap in small-cap metals equities | MEDIUM | Can't exit MP, URA positions at fair value | 20% ADV limit, prefer ETFs over single names |
| F14 | Correlation collapse between gold and gold miners | LOW-MEDIUM | GDX decouples from GC, MTCE loses basis | Monitor GDX-GC beta weekly, pause MTCE if beta < 0.5 |
| F15 | Regime misclassification | MEDIUM | Trade wrong thesis in wrong regime | 5-day confirmation before MTCE activation |
| F16 | MSIL inducing overconfidence in WMCE | LOW | SRA boost causes oversizing on bad weekend | SRA capped at +10, cannot increase position size |
| F17 | Narrative drift — believing "AI metals" story | MEDIUM | Strategy becomes thematic bet, not systematic | All regime definitions are quantitative, no narrative inputs |

### Hard Limits (Extended)

```
v0.1.0 limits (UNCHANGED):
  Maximum single-weekend risk (WMCE):     1.5% of allocated NAV
  Maximum rolling 4-week drawdown (WMCE): 5% → pause
  Maximum rolling 12-week drawdown (WMCE): 15% → KILLED

v0.2.0 additions:
  Maximum MTCE single-trade risk:          0.5% of allocated NAV
  Maximum MTCE total open exposure:        0.75% of allocated NAV
  Maximum single-name equity option:       0.3% of allocated NAV
  Maximum combined WMCE + MTCE weekend:    2.0% of allocated NAV
  Maximum correlation-adjusted exposure:   If WMCE-MTCE 30d rolling corr > 0.6,
                                          reduce MTCE allocation by 50%
  Maximum single regime allocation:        Cannot have > 1.5% NAV in positions
                                          predicated on a single regime state
  MTCE cannot exceed 50% of WMCE allocation without independent Phase 4-M validation
```

### Uncertainty Register (Extended)

6. **Do metals regimes exist or are we imposing structure?**
   Cluster analysis may show continuous variation, not discrete states.
   If regimes are a spectrum, the state machine is wrong.

7. **Is cross-metal dispersion predictive or coincident?**
   MDI measured on Friday may only reflect what already happened, not
   what will happen over the weekend. Predictive power is the key test.

8. **Are mining equities options liquid enough?**
   GDX has decent liquidity. URA, COPX, LIT options may have wide spreads
   that eat the entire edge. Must verify bid-ask spreads empirically.

9. **Does MSIL add complexity without proportional value?**
   Every added signal increases the chance of spurious correlation.
   MSIL must clear a high bar: measurable OOS improvement to WMCE.

10. **Is the "AI infrastructure" regime real or a 2024-2025 narrative?**
    Copper demand from data centers is real but may be small relative to
    China construction demand. We test this, we don't assume it.

---

## VIII. DEVELOPMENT ROADMAP EXTENSION

```
Sprint    Duration   Focus                              Deliverable
────────────────────────────────────────────────────────────────────
S0-M      2 weeks    Metals data infrastructure          metals_data/ module
S1-M      2 weeks    Dispersion engine (MDI, GLS, etc.)  dispersion/ module
S2-M      2 weeks    Regime classifier                   regime_classifier/
S3-M      1 week     WRS integration (SRA)               Updated scoring/
S4-M      3 weeks    Phase 2-M testing                   predictive_tests/
S5-M      2 weeks    OOS validation (Phase 3-M)          oos_metals/
S6-M      2 weeks    MTCE backtest (if Phase 3-M passes) mtce_backtest/
S7-M      Ongoing    Paper trading MSIL + WMCE           ops/

Total new development: ~14 weeks
Starts AFTER WMCE Phase 2 backtest completes.
```

### Updated Directory Structure (Additions)

```
aurum/
├── CLAUDE.md                        # v0.1.0 base
├── CLAUDE_MSIL.md                   # THIS FILE (v0.2.0 appendix)
├── config/
│   ├── signals.yaml                 # v0.1.0 signals
│   ├── signals_metals.yaml          # NEW: metals stack parameters
│   ├── regime.yaml                  # v0.1.0 regime
│   ├── regime_metals.yaml           # NEW: MSIL regime classifier config
│   └── trading.yaml                 # Updated with MTCE limits
├── metals/                          # NEW: entire metals stack module
│   ├── data/
│   │   ├── ingest.py                # Metals data fetchers
│   │   ├── ratios.py                # Derived ratio computations
│   │   └── store.py                 # Metals Parquet interface
│   ├── dispersion/
│   │   ├── mdi.py                   # Metals Dispersion Index
│   │   ├── gls.py                   # Gold Leadership Score
│   │   ├── smb.py                   # Stack Momentum Breadth
│   │   ├── imdi.py                  # Industrial-Monetary Divergence
│   │   └── tests/
│   ├── regime/
│   │   ├── classifier.py            # Regime state machine
│   │   ├── sra.py                   # Stack Regime Adjustment
│   │   └── tests/
│   ├── mtce/
│   │   ├── trigger.py               # MTCE activation conditions
│   │   ├── structurer.py            # MTCE trade structuring
│   │   └── tests/
│   └── research/
│       ├── cluster_analysis.py      # Phase 1-M regime discovery
│       ├── predictive_tests.py      # Phase 2-M significance testing
│       └── notebooks/
├── scoring/
│   ├── weekend_risk_score.py        # UPDATED: accepts SRA input
│   └── ...
└── ...
```

---

## IX. HONEST ASSESSMENT — MSIL EXPANSION

### Probability MSIL Improves WMCE: ~30-40%

Reasons for skepticism:
1. Adding more signals usually adds noise, not signal
2. Metals regimes may be too slow-moving (quarterly) to help with
   weekly gold gap prediction
3. The "AI infrastructure" framing is heavily influenced by 2024-2025
   narrative — it may not persist
4. Cross-metal dispersion is well-studied; if it were predictive of
   gold weekends, someone would be trading it

Reasons for cautious optimism:
1. Gold/Copper ratio IS a known macro indicator — we're just formalizing it
2. Regime context (stress vs. capex) is logically useful for filtering
   gold signals even if the improvement is small
3. The integration is designed to be killable — worst case we learn
   something and move on
4. MTCE provides a path to new alpha even if MSIL doesn't help WMCE

### Probability MTCE Produces Independent Alpha: ~15-25%

This is lower than WMCE because:
1. Mining equity options are less liquid
2. Regime classification must be correct AND options must be mispriced
3. Two layers of hypothesis must both hold simultaneously
4. Single-name risk is harder to manage

### What We're Really Building:

Even if MSIL and MTCE both fail, we are building:
- A metals complex regime classifier that has standalone research value
- A cross-asset dispersion engine applicable to other asset classes
- Infrastructure for testing any thematic hypothesis systematically
- Discipline in evaluating expansion decisions quantitatively

This matters because the next expansion idea will be easier to evaluate.

---

*This appendix is subordinate to CLAUDE.md v0.1.0. In any conflict between
this document and the base system design, the base system prevails.
WMCE is the primary alpha module. MSIL is intelligence. MTCE is optional.*

**End of CLAUDE.md Appendix A — MSIL v0.2.0**
