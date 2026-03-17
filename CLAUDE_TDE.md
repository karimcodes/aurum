# CLAUDE.md — Appendix B: Temporal Discontinuity Engine (TDE)

## Version 0.3.0 — Generalized Temporal Convexity Framework

**Codename:** AURUM / CHRONOS
**Classification:** Alpha Research — Pre-Production
**Version:** 0.3.0
**Date:** 2026-02-15
**Principal Researcher:** Abdikarim
**Status:** Framework Design — Pending Phase 0 Data Collection
**Prerequisites:**
  - WMCE (v0.1.0) must pass Phase 1 manual validation before TDE modules go live
  - Each TDE sub-module validates independently — no cross-subsidy of evidence

---

## PREAMBLE — THE GENERALIZED THESIS

WMCE identifies a specific instance of a broader structural phenomenon:

> **When the ability to hedge is restricted by market structure — time gaps,
> blackout periods, liquidity holes, expiry misalignments — options pricing
> systematically underestimates the risk of discontinuous moves.**

Gold weekend gaps are the most visible instance. But the same mechanic recurs
wherever markets impose temporal constraints on hedging:

```
TEMPORAL DISCONTINUITY = Any window where:
  (a) Positions are exposed to risk, AND
  (b) The ability to hedge or exit is impaired, AND
  (c) Options pricing uses models that assume continuous hedging

When (a) + (b) + (c) are true simultaneously, options are structurally
underpriced for the actual risk, and buying convexity has positive expected value.
```

**This appendix defines 7 temporal discontinuity modules (TD-1 through TD-7).**
Each is independently testable, independently tradeable, and independently
killable. They share infrastructure but not risk budgets.

**Relationship to existing system:**

```
┌───────────────────────────────────────────────────────────────┐
│              TEMPORAL DISCONTINUITY ENGINE (TDE)               │
│                                                               │
│   TD-1: Weekend Gap Premium (= WMCE)        ← EXISTING       │
│   TD-2: Holiday Gap Premium                  ← NEW           │
│   TD-3: Sunday Night Liquidity Hole          ← NEW           │
│   TD-4: FOMC Blackout Vol Compression        ← NEW           │
│   TD-5: Gold-Equity Sequencing Lag           ← NEW           │
│   TD-6: Options Expiry Cycle Misalignment    ← NEW           │
│   TD-7: Central Bank Bid Skew                ← NEW           │
│                                                               │
│   MSIL (v0.2.0) provides regime context to ALL modules        │
│   Each module has independent risk budget                     │
│   Combined exposure hard-capped at 3.5% NAV                  │
└───────────────────────────────────────────────────────────────┘
```

**Critical design principle:** These modules are NOT seven versions of the same
trade. Each exploits a different structural mechanism. If they are empirically
correlated > 0.5 in P&L, they should be merged or one should be killed.

---

## TD-1: WEEKEND GAP PREMIUM

**This is WMCE (v0.1.0). Already fully specified.**

Included here for completeness within the TDE taxonomy.
See CLAUDE.md v0.1.0 for full specification.

```
Mechanism:        48-hour hedging gap, Friday 5PM → Sunday 6PM ET
Instrument:       GC/GLD options (straddles, strangles)
Frequency:        Weekly (every Friday)
Max Risk/Event:   1.5% NAV
Status:           Designed, pending Phase 1 validation
```

---

## TD-2: HOLIDAY GAP PREMIUM

### Thesis

Three-day weekends (and longer holidays) create 72+ hour hedging gaps —
50% longer than regular weekends. If weekend gap premium exists (TD-1),
holiday gap premium should be larger. Options models price theta decay
linearly across calendar days, but the actual risk is concentrated in
unhedgeable hours, making holiday-period options systematically cheap.

### Structural Mechanism

US markets observe ~9 three-day weekends per year:
```
Martin Luther King Jr. Day      (January)
Presidents' Day                 (February)
Good Friday*                    (March/April) *Equity markets close, CME partial
Memorial Day                    (May)
Juneteenth                      (June)
Independence Day                (July)
Labor Day                       (September)
Thanksgiving                    (November) — 1.5 day closure
Christmas                       (December) — variable, sometimes 1.5 days
```

Additionally, non-US holidays create asymmetric gaps:
- Chinese New Year → Shanghai Gold Exchange closed, London/CME open but
  without Chinese flow → gold can move on Chinese-absent liquidity
- Japanese holidays → JPY and Asian gold markets absent
- European holidays → LBMA closed, CME open → reduced arb capacity

### Hypotheses

**H1_TD2:** Three-day-weekend gold gaps have statistically larger magnitude
than regular weekend gaps. Test: compare distributions of |Monday gap| for
3-day weekends vs regular weekends over 5+ year sample.

**H2_TD2:** Friday PM implied vol before 3-day weekends does NOT fully
compensate for the additional 24+ hours of unhedgeable risk. Test: compute
IV/RV ratio for 3-day weekends vs regular weekends. If 3-day IV/RV is not
proportionally higher, options are underpriced.

**H0_TD2 (null):** Holiday gaps are no different from regular weekend gaps
once controlling for calendar theta. Options models correctly account for
the extra day. If H0 holds at p > 0.1, TD-2 adds no value beyond TD-1.

### Measurable Features

```python
TD2_FEATURES = {
    'is_three_day_weekend': bool,           # Binary
    'holiday_hours_gap': float,             # Actual hours market is closed
    'friday_pm_iv_atm_weekly': float,       # GC ATM weekly IV at 3PM ET
    'pre_holiday_iv_premium': float,        # friday_IV - mean(IV, trailing_4_fridays)
    'prior_3day_gap_magnitude': float,      # Last 3-day weekend's gap
    'international_holiday_flag': bool,     # Is a major non-US market also closed?
    'holiday_type': str,                    # Classification for potential regime effect
}
```

### Signal: Holiday Premium Score (HPS)

```
HPS components (0-100):
  - Is 3-day weekend:                         +30 base
  - International market also closed:         +15
  - WRS (from TD-1) already elevated:        +20 max (use Friday WRS * 0.25)
  - Pre-holiday IV NOT elevated:              +20 (options are cheap)
  - Prior 3-day weekend produced > 1% gap:   +15 (momentum confirmation)
```

### Trade Structure

```
HPS Range     Structure                    Sizing
──────────────────────────────────────────────────────
60-80         Weekly straddle              0.75% NAV
              (same as TD-1 STANDARD)
80-100        Weekly strangle + 0DTE       1.0% NAV
              (same as TD-1 MAXIMUM)

NOTE: TD-2 uses SAME instruments as TD-1.
      When TD-2 is active (3-day weekend), it REPLACES TD-1 for that week,
      it does not stack on top. Combined weekend exposure remains capped.
```

### Data Requirements

- Same as TD-1 (GC options, GLD options, VIX, etc.)
- Additional: US market holiday calendar (verified, not estimated)
- Additional: International market holiday calendar (China, Japan, Europe)
- Minimum sample: ~45 three-day weekends per 5-year period

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD2-F1 | Only ~9 3-day weekends/year → tiny sample | Combine with international holidays for larger N |
| TD2-F2 | Markets may price holidays correctly | IV premium check before trade entry |
| TD2-F3 | Some holidays are low-vol (Christmas) | Holiday-type filter: exclude low-activity holidays |

### Shutdown Criteria

- If 3-day weekend gaps are NOT larger than regular weekend gaps (p > 0.1
  after 3 years of data) → kill TD-2, fold into TD-1 as seasonal weight
- If pre-holiday IV premium fully prices the extra risk → no edge

---

## TD-3: SUNDAY NIGHT LIQUIDITY HOLE

### Thesis

Gold futures reopen Sunday at 6PM ET. From 6PM to ~9PM ET (and arguably
until London opens at 3AM ET), liquidity is extremely thin. The largest
weekend moves often occur in this window, not at Monday's equity open.
Extreme moves made in thin liquidity systematically overshoot and revert
by the time full liquidity returns.

### Structural Mechanism

```
Sunday 6PM ET:   CME gold futures reopen. Globex session begins.
                 Participants: Asian desks (Tokyo, Hong Kong, Shanghai),
                 some algorithmic market makers, almost no US discretionary.
                 Bid-ask spread: 2-5x wider than US session.

Sunday 9PM ET:   Shanghai Gold Exchange opens (Monday morning Asia).
                 Chinese flow enters. Liquidity improves but is still thin.

Monday 3AM ET:   London opens. LBMA market makers enter.
                 Liquidity normalizes to full depth.
                 If Sunday night move was fear-driven and reality is benign,
                 REVERSION happens here.

Monday 9:30AM ET: US equity markets open. Full global liquidity.
```

**The key insight:** If you hold Friday PM options, your payoff is determined
by the Sunday night move, but you cannot manage the position until Monday
morning at earliest. However, if you're a *futures* trader, you CAN trade
the Sunday night session. This creates a distinct sub-strategy.

### Hypotheses

**H1_TD3:** Gold moves between Sunday 6PM and 9PM ET that exceed 0.5%
revert by at least 40% by Monday 3AM ET (London open), more often than
similar-magnitude intraday moves during regular US sessions.

**H2_TD3:** The reversion rate is highest when the Sunday night move
contradicts the trailing macro regime (e.g., gold spikes up on Sunday night
during a low-vol stability regime → likely to revert).

**H0_TD3 (null):** Sunday night gold moves are no more mean-reverting than
equivalent-magnitude moves during any other 3-hour window. If true, there
is no liquidity-specific edge.

### Measurable Features

```python
TD3_FEATURES = {
    'sunday_6pm_to_9pm_return': float,       # GC1 return in this window
    'sunday_6pm_to_9pm_volume': int,         # Very low = higher reversion probability
    'sunday_6pm_to_london_open_return': float, # Full overnight return
    'sunday_bid_ask_spread_avg': float,      # Spread during 6-9PM window
    'friday_close_to_sunday_9pm_gap': float, # Total gap including thin session
    'news_catalyst_present': bool,           # Was there an actual event?
    'wmce_wrs_friday': float,                # Was the system already on alert?
    'asian_session_volume_zscore': float,    # Abnormal volume = real event
}
```

### Signal: Sunday Reversion Score (SRS)

```
SRS activates ONLY when:
  |sunday_6pm_to_9pm_return| > 0.5%

SRS components (0-100):
  - Move magnitude > 0.5%:            +20 base
  - Move magnitude > 1.0%:            +15 additional
  - Volume during move < 30th pctl:   +25 (thin liquidity → more likely overshoot)
  - No identifiable news catalyst:    +20 (fear-driven, not event-driven)
  - WRS was LOW on Friday:            +20 (move contradicts calm setup)
  - Move contradicts MSIL regime:     +10 (e.g., gold down in macro stress regime)

If SRS > 60: Fade the move via futures.
If SRS < 40 OR news catalyst present: Do NOT fade. Move may be real.
```

### Trade Structure

**THIS IS A FUTURES TRADE, NOT OPTIONS.**

```
Structure: Mean-reversion via GC1 futures
Entry:     Sunday ~9PM ET if SRS > 60
Direction: Opposite to 6-9PM move
Size:      Micro gold futures (MGC) for small accounts.
           Max risk = 0.3% NAV with stop-loss.
Stop:      If move extends 50% beyond entry in the wrong direction → cut.
Target:    50% reversion of the Sunday night move by London open (3AM ET).
Hard Exit: Must be flat by Monday 8:00 AM ET regardless.
           This is a 11-hour maximum hold. No overnight US risk.
```

### Why This Is Structurally Different from TD-1

```
TD-1 (WMCE):  Buy options Friday → profit from gap → exit Monday
TD-3:         Trade futures Sunday night → profit from reversion → exit pre-US-open

TD-1 profits when gaps are LARGE.
TD-3 profits when gaps REVERT.
These are negatively correlated by design.

Combined: TD-1 wins on real macro weekends. TD-3 wins on fear-driven
overshoot weekends. Together they bracket the outcome space.
```

### Data Requirements

- GC1 tick or 1-minute data including Sunday evening session (5+ years)
- Bid-ask spread data for Sunday session (if available; proxied by
  volume if not)
- News timestamps (Reuters/Bloomberg) for Sunday PM catalyst identification
- Minimum: ~260 Sunday sessions per 5-year period

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD3-F1 | Sunday moves don't revert more than random | Kill module. H0 holds. |
| TD3-F2 | Execution in thin market is worse than modeled | Use MGC micro contracts, aggressive stop |
| TD3-F3 | Can't distinguish real events from overshoot in real-time | News catalyst filter, volume filter |
| TD3-F4 | Trading while sleeping (Sunday night US time) | Limit order + stop-loss, or skip and use London session only |

### Shutdown Criteria

- If Sunday 6-9PM moves > 0.5% do NOT revert by London open with > 55% hit
  rate over 1 year of data → kill TD-3
- If slippage in Sunday night futures exceeds 0.15% per trade → edge is
  consumed by execution cost

---

## TD-4: FOMC BLACKOUT VOL COMPRESSION

### Thesis

The Federal Reserve's blackout period (~10 days before each FOMC meeting)
suppresses narrative flow — no Fed speeches, no forward guidance leaks.
This creates an artificial reduction in headline volatility, which compresses
implied vol across assets. But the actual underlying macro risk doesn't
disappear — it's merely deferred until FOMC day. Gold options priced during
blackout may be systematically cheap for the volatility that arrives when
the blackout lifts and the FOMC decision drops.

### Structural Mechanism

```
Typical FOMC cycle (8 meetings per year):

Day -14 to -10:  Pre-blackout. Fed speakers active. Vol normal.
Day -10:         Blackout begins. No Fed speeches.
Day -10 to -1:   Blackout period. Headline velocity drops.
                 NLP score (from WMCE) naturally falls.
                 Gold IV may compress because "nothing is happening."
Day 0:           FOMC decision + press conference at 2PM ET.
                 Massive vol spike. Gold moves 1-3%.
Day +1 to +3:    Post-FOMC digestion. Vol stays elevated.
```

**The mispricing window:** Friday before FOMC week, during blackout.
Gold weekly options expiring FOMC-day or day-after are priced using
compressed blackout-period IV, but will be exposed to FOMC vol spike.

### Hypotheses

**H1_TD4:** Gold ATM weekly IV on the Friday before FOMC week is lower
than gold ATM weekly IV on non-FOMC Fridays, after controlling for VIX
and realized vol. The blackout suppresses gold option premiums.

**H2_TD4:** Gold straddles purchased on the Friday before FOMC week
(expiring day-of or day-after FOMC) are profitable on average, because
the FOMC vol spike exceeds the premium paid.

**H0_TD4 (null):** Options market makers correctly anticipate FOMC vol
and price it into Friday pre-FOMC options via event vol modeling. The
blackout narrative compression does not affect option pricing because
dealers use forward-looking event vol, not trailing realized vol.

**IMPORTANT:** H0 is plausible. Sophisticated dealers DO model event vol
for FOMC. But gold options desks may be less sophisticated than equity
options desks (SPX 0DTE market makers have extremely refined event models).
The question is whether this sophistication gap exists in gold.

### Measurable Features

```python
TD4_FEATURES = {
    'is_fomc_week_minus_one': bool,           # Friday before FOMC week
    'blackout_active': bool,                  # Fed blackout confirmed
    'days_until_fomc': int,                   # 3-5 typically (Fri before Wed meeting)
    'gc_atm_weekly_iv': float,                # IV of options expiring FOMC week
    'gc_atm_weekly_iv_zscore': float,         # vs trailing 63-day IV
    'gc_atm_weekly_iv_vs_monthly': float,     # Term structure: weekly/monthly
    'vix_level': float,                       # Cross-check
    'prior_fomc_gold_move': float,            # |gold move| at last FOMC
    'trailing_8_fomc_gold_moves_mean': float, # Average |gold move| on FOMC days
    'nps_score_trailing_48h': float,          # Narrative Pressure Score — should be low
    'fed_funds_futures_implied_move': float,  # Market-implied rate change
}
```

### Signal: FOMC Blackout Compression Score (FBCS)

```
FBCS activates ONLY on:
  Friday where is_fomc_week_minus_one == True AND blackout_active == True

FBCS components (0-100):
  - Blackout active + FOMC within 5 days:      +25 base
  - Gold weekly IV z-score < -0.5:             +25 (vol is compressed)
  - Gold weekly IV < monthly IV:               +15 (term structure confirms)
  - NPS < 3 (low narrative pressure):          +10 (blackout is working)
  - Prior FOMC moved gold > 1%:                +10 (FOMC gold sensitivity confirmed)
  - Fed funds futures pricing > 15bp move:     +15 (FOMC will be material)
```

### Trade Structure

```
FBCS Range    Structure                          Sizing      DTE
──────────────────────────────────────────────────────────────────
50-70         Long GC weekly straddle             0.5% NAV    Expiry FOMC+1
              (expire day after FOMC)
70-100        Long GC weekly straddle             0.75% NAV   Expiry FOMC+1
              + small GLD 0DTE on FOMC day        +0.25% NAV  Expiry FOMC day
              (intraday play on decision)

Entry:    Friday 2:30-3:30 PM ET (blackout period)
Exit:     FOMC day, 3:30 PM ET (after press conference volatility)
          OR FOMC+1 if position is profitable and momentum continues
Max Hold: FOMC+2 days. After that, theta kills you.
```

### Frequency & Sample Size

- 8 FOMC meetings per year
- 5 years = 40 data points
- This is small but larger than 3-day weekends
- Each FOMC meeting is a "natural experiment" — known event, known timing

### Why This Differs from TD-1

```
TD-1 (WMCE):  Profits from UNPREDICTABLE weekend events
TD-4:          Profits from a KNOWN event (FOMC) that is underpriced due
               to blackout-induced vol compression

TD-1 risk: event doesn't happen → premium lost
TD-4 risk: event is priced correctly → premium lost (but at least the
           event WILL happen, reducing pure time-decay risk)
```

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD4-F1 | Gold options desks DO model event vol correctly | IV z-score check: if IV is NOT compressed, don't trade |
| TD4-F2 | FOMC is a non-event (no change, no surprise) | Fed funds futures filter: skip if < 5bp implied move |
| TD4-F3 | Gold moves against you between Friday and Wednesday | Accept: max loss is premium paid (0.75% NAV) |
| TD4-F4 | Blackout period is shortened or eliminated by Fed | Monitor Fed calendar; kill module if blackout ends |

### Shutdown Criteria

- If FOMC-week gold straddles are not profitable > 50% of the time
  over 16 consecutive FOMC cycles (2 years) → kill TD-4
- If pre-FOMC gold IV is NOT compressed vs non-FOMC weeks (t-test
  p > 0.1) → the thesis is wrong, kill TD-4

---

## TD-5: GOLD-EQUITY SEQUENCING LAG

### Thesis

When gold gaps significantly on Monday morning, US equity markets may
not have fully repriced the information gold is reflecting. SPX options
priced at Monday open may still embed Friday's vol assumptions while gold
has already moved. Buying SPX options in the direction implied by gold's
move exploits this temporal information lag.

### Structural Mechanism

```
Sunday 6PM ET:    Gold futures reopen. Gap occurs.
Sunday 9PM ET:    Asian equities react (Nikkei, Hang Seng).
Monday 3AM ET:    European equities react (DAX, FTSE).
Monday 8AM ET:    US equity futures have adjusted — but how much?
Monday 9:30AM ET: US equity market opens. SPX 0DTE options begin trading.

KEY QUESTION: At 9:30 AM Monday, have SPX 0DTE options FULLY priced in
the information that gold revealed at 6PM Sunday?

If not, buying SPX puts (when gold gaped up on fear) or SPX calls
(when gold gaped down on relief) has positive EV.
```

### Hypotheses

**H1_TD5:** When gold gaps > 1% on Monday open, SPX same-day directional
return is predictable with > 55% accuracy based on the direction of gold's
gap and the macro regime.

**H2_TD5:** SPX 0DTE options purchased at Monday 9:30 AM, when gold has
already gapped > 1%, are profitable on average — specifically because SPX
vol surface at 9:30 AM hasn't fully incorporated gold's information.

**H0_TD5 (null):** By 9:30 AM Monday, all gold gap information is already
priced into SPX futures and options. SPX 0DTE options correctly reflect
the updated risk landscape and buying them based on gold's gap is not
systematically profitable.

**IMPORTANT WARNING:** This is the most fragile hypothesis. Equity options
desks are the most sophisticated in the world. SPX 0DTE is the most liquid
options market on Earth. The assumption that they're slow to price gold
information is a strong claim. The bar for evidence should be highest here.

### Measurable Features

```python
TD5_FEATURES = {
    'monday_gold_gap_pct': float,            # (Mon open - Fri close) / Fri close
    'gold_gap_direction': str,               # "up" or "down"
    'gold_gap_magnitude_percentile': float,  # vs trailing 252 gaps
    'silver_confirms_direction': bool,       # Silver gapped same direction
    'msil_regime': str,                      # Macro stress vs other
    'spx_futures_gap_pct': float,            # ES1 gap at Monday open
    'gold_spx_gap_ratio': float,             # |gold gap| / |spx gap|
    'vix_monday_open': float,
    'spx_0dte_atm_iv_monday_open': float,
    'spx_0dte_atm_iv_zscore': float,         # vs trailing 63 Monday opens
    'time_since_gold_gap': float,            # Hours from gold reopen to SPX open
    'asian_equity_reaction': float,          # Nikkei/HSI Monday return
}
```

### Signal: Sequencing Lag Score (SLS)

```
SLS activates ONLY when:
  |monday_gold_gap_pct| > 1.0%

SLS components (0-100):
  - Gold gap > 1%:                           +20 base
  - Gold gap > 2%:                           +15 additional
  - Silver confirms (same direction):        +15
  - MSIL regime = MACRO_STRESS:              +15 (gold is leading)
  - SPX futures gap < 50% of gold gap:       +20 (equities haven't caught up)
  - SPX 0DTE IV z-score < +1.0:             +15 (equity vol not yet elevated)

Threshold: SLS > 50 to trade.
```

### Trade Structure

```
Direction Logic:
  Gold GAP UP (fear/haven bid):
    → SPX likely to DECLINE or at minimum stay volatile
    → Buy SPX 0DTE ATM puts
    → OR buy SPX 0DTE straddle if direction is uncertain

  Gold GAP DOWN (risk-on/relief):
    → SPX likely to RALLY
    → Buy SPX 0DTE ATM calls
    → OR buy SPX 0DTE straddle

PREFERENCE: Straddles over directional in ALL cases until we have
> 100 data points proving directional accuracy > 60%. Until then,
we're trading vol expansion, not direction.

Structure          Sizing      Entry             Exit
────────────────────────────────────────────────────────────────
SPX 0DTE straddle  0.5% NAV   Monday 9:35 AM    Monday 2:00 PM
                               (5 min after open  (before EOD
                               for spread to set)  theta crush)

Max Hold: Must close by 3:00 PM ET.
          0DTE theta accelerates exponentially after 2PM.
```

### Why SPX 0DTE Is The Vehicle

- SPX 0DTE is the most liquid option in the world. Spreads are tight.
- Gold options Monday morning are ILLIQUID (everyone is hitting the same
  side of the book). SPX gives you a way to monetize gold's information
  without competing in the gold options market.
- Higher gamma per dollar in SPX 0DTE than in GC options due to liquidity.

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD5-F1 | SPX desks are too fast — gold info is priced by 9:30 | IV z-score check: if SPX vol already elevated, skip |
| TD5-F2 | Gold gap doesn't predict SPX direction | Use straddles, not directional trades |
| TD5-F3 | 0DTE theta destroys you by afternoon | Hard exit by 2PM. Accept time decay risk. |
| TD5-F4 | Correlation between gold gaps and SPX is unstable | Rolling 63-day correlation check; pause if < 0.3 |

### Shutdown Criteria

- If gold gaps > 1% do NOT predict same-day SPX direction > 55% over
  100 events → directional thesis is dead (may still trade straddles)
- If SPX straddles purchased on Monday gap mornings are not profitable
  > 45% of the time over 1 year → kill TD-5 entirely
- If SPX 0DTE IV is already elevated (z-score > +1.5) on Monday mornings
  when gold has gapped → market has priced it, no edge

---

## TD-6: OPTIONS EXPIRY CYCLE MISALIGNMENT

### Thesis

GLD equity options and GC futures options expire on different schedules.
When one market's options are expiring (creating gamma-driven hedging flow)
and the other market's options are not expiring, the hedging dynamics create
temporary mispricings. Specifically, GLD Friday expiry options may overvalue
weekend risk (nervous equity options traders) while GC options with Monday+
expiry may undervalue it (futures traders using standard models).

### Structural Mechanism

```
GLD options:    Expire Friday 4:00 PM ET (equity options)
GC options:     Various: daily, weekly (various days), monthly (last biz day)
                CME gold futures options have their own expiry calendar.

Misalignment scenario:
  - GLD weeklies expire Friday 4PM (0DTE by Friday afternoon)
  - GC weeklies expire Monday or Tuesday (still 2-3 DTE on Friday)
  - GLD market makers are hedging gamma into Friday close
  - GC market makers are NOT hedging for immediate expiry

This creates divergent IV dynamics:
  GLD Friday PM IV may be elevated (gamma hedging, weekend fear priced in)
  GC same-strike equivalent IV may be lower (no immediate expiry pressure)

If the spread is wide enough: sell GLD Friday straddle + buy GC equivalent
```

### Hypotheses

**H1_TD6:** On Fridays where GLD options expire but equivalent GC options
do not, the GLD/GC implied vol spread widens by > 2 vol points beyond
the normal spread, creating a relative value opportunity.

**H0_TD6 (null):** GLD and GC implied vol maintain a stable relationship
regardless of expiry cycle alignment. Any spread widening is within normal
arbitrage bounds and not tradeable after costs.

**COMPLEXITY WARNING:** This is the most operationally complex module.
It requires simultaneous positions in two different options markets
(equity and futures), precise Greeks management, and careful cross-margining.
This should be the LAST module developed.

### Trade Structure (Conceptual)

```
When GLD Friday IV > GC equivalent IV + 3 vol points:
  Sell GLD ATM straddle (0DTE, expiring today)
  Buy GC weekly straddle (2-5 DTE)
  Net position: short gamma today, long gamma over weekend

Profit if:
  GLD straddle expires worthless (or near) Friday → keep premium
  GC straddle profits from Monday gap → capture convexity

Risk:
  Gold makes a big move DURING Friday before GLD expiry → GLD straddle
  loses, GC straddle gains, but GLD losses may be larger due to 0DTE gamma

Max Size: 0.3% NAV per side (total 0.6% NAV exposure)
```

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD6-F1 | GLD-GC IV spread is too narrow to profit after costs | Minimum spread threshold: 3 vol points |
| TD6-F2 | GLD gamma risk during Friday session | Strict delta-hedging if GLD moves against |
| TD6-F3 | Cross-market margining complexity | Paper trade for 3 months before live |
| TD6-F4 | Execution across two different option markets simultaneously | Pre-program both legs; accept some slippage |

### Shutdown Criteria

- If GLD-GC IV spread exceeds 3 vol points on < 20% of misaligned Fridays
  → opportunity is too rare to trade
- If net P&L of the spread trade is negative over 20 occurrences → kill

---

## TD-7: CENTRAL BANK BID SKEW

### Thesis

Central bank gold purchases (China, India, Turkey, Poland, etc.) at
record pace since 2022 create a persistent structural bid under gold.
This bid reduces downside gap risk on weekends (central banks don't sell
in panic) while upside gap risk remains (geopolitical events spike gold up).
This creates a directional skew in weekend gaps that symmetric straddles
don't optimally capture.

### Structural Mechanism

```
Central bank buying characteristics:
  - Persistent, not reactive to price
  - Typically executed through intermediaries on London fix
  - NOT reflected in real-time flow data
  - Reported with 1-2 month lag (WGC quarterly, IMF monthly)
  - Creates a "floor" effect below current spot

Impact on weekend gaps:
  - Upside gap: geopolitical shock + no central bank selling = full gap
  - Downside gap: risk-off selling MEETS persistent central bank bid
    → gap is cushioned, reversion is faster

If this asymmetry is real:
  - Straddles are suboptimal (too much downside premium wasted)
  - Risk reversals (long OTM calls, short OTM puts) are better
  - Or: wide call spreads + tight put spreads (asymmetric strangle)
```

### Hypotheses

**H1_TD7:** Monday gold gaps are positively skewed (more up-gaps than
down-gaps, or larger up-gaps than down-gaps) in the post-2022 period
compared to the 2017-2021 period.

**H2_TD7:** The positive skew is proportional to reported central bank
buying volume (with a lag). Quarters with higher CB buying show more
skewed Monday gaps.

**H0_TD7 (null):** Monday gold gaps show no directional skew. Central
bank buying is too slow and price-insensitive to affect gap dynamics.
Skew, if any, is driven by geopolitical regime, not CB flows.

### Measurable Features

```python
TD7_FEATURES = {
    'trailing_12m_gap_skewness': float,     # Skewness of Monday gaps
    'trailing_12m_upside_gap_pct': float,   # % of gaps that are positive
    'trailing_12m_avg_upside_gap': float,   # Mean positive gap size
    'trailing_12m_avg_downside_gap': float, # Mean negative gap size
    'cb_buying_quarterly_tonnes': float,    # WGC data (lagged 1-2 months)
    'shanghai_premium_to_london': float,    # Real-time proxy for Chinese demand
    'lbma_forward_rate': float,             # Forward rate as demand proxy
    'etf_holdings_change_weekly': float,    # GLD/IAU holdings (inverse of CB buying)
    'gold_put_call_ratio': float,           # Options market's directional view
    'gold_25d_risk_reversal': float,        # Call IV - Put IV (25-delta)
}
```

### Signal: Central Bank Skew Score (CBSS)

```
CBSS modifies TD-1 (WMCE) trade structure, it does not generate
independent trades.

CBSS components (0-100):
  - Trailing 12m gap skewness > +0.3:        +25
  - Trailing 12m upside gap frequency > 55%: +20
  - CB buying > 250 tonnes/quarter:          +15
  - Shanghai premium > $10/oz:               +15
  - Gold 25d risk reversal > +1.0:           +15 (options market agrees)
  - ETF holdings declining:                   +10 (Western selling, CB buying)

If CBSS > 60:
  WMCE trade structure shifts from straddle → call-heavy structure:
    Replace ATM straddle with:
      Long ATM call + Long 3% OTM put (instead of ATM put)
      This captures full upside gap while reducing downside premium by ~30%
```

### Why This Is Not A Directional Bet

We are NOT predicting gold goes up. We are observing that the *distribution*
of weekend gaps may have become asymmetric. If the distribution is symmetric,
straddles are optimal. If it's right-skewed, we adjust the structure to
match the actual distribution. This is a statistical adaptation, not a view.

### Failure Modes

| # | Failure Mode | Mitigation |
|---|-------------|------------|
| TD7-F1 | Skewness is sample noise, not structural | Require p < 0.05 on skewness test |
| TD7-F2 | CB buying stops or reverses | Monitor quarterly. If buying < 100 tonnes/qtr, pause |
| TD7-F3 | Skew priced into gold options (risk reversal already elevated) | Check 25d RR: if already > +2.0, edge is priced |
| TD7-F4 | Directional bet risk: we're wrong about skew | Keep ATM put (just move it OTM), don't remove downside entirely |

### Shutdown Criteria

- If gold weekend gap skewness is not significantly different from zero
  (p > 0.1) over 2-year rolling window → revert to pure straddles
- If CB buying drops below 100 tonnes/quarter for 2 consecutive quarters
  → revert to pure straddles

---

## UNIFIED RISK DOCTRINE — TDE

### Combined Position Limits (Hard)

```
Module          Max Per-Event Risk    Max Open Exposure    Notes
──────────────────────────────────────────────────────────────────────────
TD-1 (WMCE)     1.50% NAV            1.50% NAV           Primary module
TD-2 (Holiday)  1.00% NAV            1.00% NAV           Replaces TD-1 on holidays
TD-3 (Sunday)   0.30% NAV            0.30% NAV           Futures, not options
TD-4 (FOMC)     0.75% NAV            1.00% NAV           8x per year
TD-5 (Seq Lag)  0.50% NAV            0.50% NAV           SPX 0DTE, intraday only
TD-6 (Expiry)   0.60% NAV            0.60% NAV           Last to develop
TD-7 (CB Skew)  N/A (modifies TD-1)  N/A                 Structure adjustment only

MTCE (v0.2.0)   0.50% NAV            0.75% NAV           Metals equities

COMBINED HARD CAP:  3.50% NAV across all TDE + MTCE modules simultaneously
                    This is an ABSOLUTE maximum. Cannot be overridden.

WEEKEND SPECIFIC:   TD-1 + TD-2 + TD-3 combined never exceeds 2.0% NAV
                    (These are all weekend-exposed)

CORRELATION RULE:   If any two modules show > 0.6 rolling 30-day P&L
                    correlation, the junior module (lower priority) has
                    its allocation halved until correlation drops.
```

### Module Priority Hierarchy

```
Priority 1 (cannot be reduced):  TD-1 (WMCE) — primary alpha module
Priority 2:                      TD-2 (Holiday) — natural extension of TD-1
Priority 3:                      TD-4 (FOMC) — known event calendar
Priority 4:                      TD-7 (CB Skew) — modifies TD-1, low cost
Priority 5:                      TD-5 (Seq Lag) — SPX, different market
Priority 6:                      TD-3 (Sunday) — futures, different mechanism
Priority 7:                      MTCE (v0.2.0) — metals equities
Priority 8:                      TD-6 (Expiry) — most complex, build last
```

### Correlation Matrix Expectations

```
Expected P&L correlations (to be validated empirically):

         TD-1  TD-2  TD-3  TD-4  TD-5  TD-6  TD-7  MTCE
TD-1      1.0   0.8  -0.3   0.2   0.3   0.4   0.7   0.3
TD-2            1.0  -0.2   0.1   0.3   0.3   0.7   0.3
TD-3                  1.0   0.0  -0.1   0.0  -0.2   0.0
TD-4                        1.0   0.1   0.1   0.2   0.1
TD-5                              1.0   0.1   0.2   0.2
TD-6                                    1.0   0.3   0.1
TD-7                                          1.0   0.3
MTCE                                                1.0

KEY: TD-1/TD-2 will be HIGHLY correlated (same mechanism, different calendar).
     TD-2 should REPLACE TD-1 on holidays, not stack.
     TD-1/TD-3 should be NEGATIVELY correlated (gap vs reversion).
     TD-4 should be largely INDEPENDENT (different mechanism entirely).
```

---

## DEVELOPMENT ROADMAP — TDE

### Phase Sequencing

**Do NOT build all modules simultaneously.** Sequence by priority and
dependency:

```
Phase    Weeks    Module     Gate
──────────────────────────────────────────────────────────────────
1        1-2      Data       Pull GC 5-year data with Sunday sessions
2        2-4      TD-1       Manual validation (already defined in v0.1.0)
3        4-6      TD-7       Gap skewness analysis (modifies TD-1, no new infra)
4        6-8      TD-2       Holiday gap analysis (uses TD-1 infra)
5        8-10     TD-4       FOMC blackout analysis (independent data needed)
6        10-12    TD-5       Gold-equity lag analysis (needs SPX 0DTE data)
7        12-14    TD-3       Sunday session analysis (needs tick/1min data)
8        16+      TD-6       Expiry misalignment (needs dual options chains)

EACH phase has a kill gate:
  If the module's primary hypothesis fails (H0 not rejected at p < 0.05),
  STOP that module and proceed to the next.
  Do not carry dead modules forward.
```

### Data Priority

```
Needed immediately (Phase 1):
  □ GC1 daily OHLCV, 5 years (have from WMCE)
  □ GC1 1-minute data INCLUDING Sunday PM session
  □ GC options Friday PM IV snapshots
  □ US market holiday calendar

Needed for Phase 3-4:
  □ Gold gap directional history (up vs down classification)
  □ WGC quarterly central bank buying data
  □ Shanghai Gold Exchange premium to London

Needed for Phase 5:
  □ FOMC calendar + blackout period dates
  □ Fed funds futures implied rate move history
  □ GC options IV during blackout vs non-blackout weeks

Needed for Phase 6:
  □ SPX 0DTE options Monday AM IV snapshots
  □ Nikkei/DAX Monday open returns (Asian/European reaction)

Needed for Phase 7:
  □ GC1 tick data Sunday 6-9 PM ET with bid-ask
  □ Asian session volume data

Needed for Phase 8:
  □ GLD options expiry calendar
  □ GC options expiry calendar
  □ Simultaneous IV snapshots from both markets
```

---

## HONEST ASSESSMENT — TDE v0.3.0

### Module-Level Probability of Success

```
Module      P(Edge Exists)    P(Tradeable)    P(Profitable After Costs)
──────────────────────────────────────────────────────────────────────────
TD-1        40-50%            35-45%          25-35% (already assessed)
TD-2        50-60%            40-50%          30-40% (natural extension of TD-1)
TD-3        30-40%            20-30%          15-25% (execution is hard)
TD-4        40-50%            30-40%          25-35% (known event, testable)
TD-5        20-30%            15-25%          10-20% (SPX too efficient)
TD-6        25-35%            15-25%          10-15% (most complex, most fragile)
TD-7        45-55%            40-50%          30-40% (structural, measurable)
```

**Note:** TD-2, TD-4, and TD-7 have the highest probability of adding value
because they exploit the clearest structural mechanisms. TD-5 and TD-6 are
most likely to fail because they assume market inefficiency in the most
liquid options markets in the world.

### Portfolio-Level Probability

```
P(at least 1 module is profitable):  ~70-80%
P(at least 3 modules are profitable): ~25-35%
P(all modules are profitable):        ~2-5%

This means: expect most modules to fail. That's fine.
The system is designed so that 1-2 working modules justify
the entire research investment.
```

### What We're Really Building

The Temporal Discontinuity Engine is ultimately a framework for thinking
about market microstructure through the lens of hedging impairments.
Even if every specific module fails, the research produces:

1. A deep empirical understanding of gold gap dynamics across calendars
2. A framework for evaluating any future "temporal edge" hypothesis
3. Infrastructure (data, backtesting, regime classification) that transfers
   to other strategies
4. A disciplined process for killing ideas that don't work

The most valuable output may be knowing what DOESN'T work — that saves
capital that would otherwise be lost to untested intuitions.

---

*This appendix is subordinate to CLAUDE.md v0.1.0 and v0.2.0.
Each TDE module validates independently. No module can increase another
module's risk allocation. Combined exposure is hard-capped at 3.5% NAV.*

**End of CLAUDE.md Appendix B — TDE v0.3.0**
