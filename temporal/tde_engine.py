"""
AURUM Temporal Discontinuity Engine (TDE)
==========================================
Unified scoring layer for all temporal discontinuity modules.

TD-1: Weekend Gap Premium (WMCE — already exists, imported)
TD-2: Holiday Gap Premium
TD-3: Sunday Night Liquidity Hole
TD-4: FOMC Blackout Vol Compression
TD-5: Gold-Equity Sequencing Lag
TD-7: Central Bank Bid Skew (modifies TD-1 structure, not independent)

TD-6 (Expiry Misalignment) is deferred — too complex for v0.3.0.

Each module computes an independent score and trade recommendation.
The TDE orchestrator enforces combined position limits.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime, date
import math


# ============================================================
# TD-2: Holiday Gap Premium
# ============================================================

@dataclass
class HolidayPremiumOutput:
    """Holiday Premium Score (HPS) output."""
    score: float                    # 0-100
    is_three_day_weekend: bool
    international_holiday: bool
    holiday_name: str
    gap_hours: float                # Actual hours market is closed
    iv_premium_detected: bool       # Is Friday IV elevated above normal?
    trade_recommendation: str       # "NO_TRADE" | "WEEKLY_STRADDLE" | "WEEKLY_STRANGLE_PLUS_0DTE"
    sizing_pct_nav: float
    rationale: str


US_THREE_DAY_WEEKENDS = {
    "MLK Day", "Presidents Day", "Good Friday", "Memorial Day",
    "Juneteenth", "Independence Day", "Labor Day", "Thanksgiving",
    "Christmas",
}

# Holidays where vol tends to be low (less useful for gap trades)
LOW_ACTIVITY_HOLIDAYS = {"Thanksgiving", "Christmas"}


def compute_holiday_premium_score(
    is_three_day_weekend: bool,
    holiday_name: str,
    international_holiday_also_closed: bool,
    friday_wrs: float,                    # WRS from TD-1 (WMCE)
    friday_iv_vs_trailing_mean: float,    # Friday IV / mean(IV, last 4 fridays)
    prior_three_day_gap_magnitude: float, # |gap| from last 3-day weekend
    gap_hours: float = 72.0,
) -> HolidayPremiumOutput:
    """
    Compute Holiday Premium Score.

    This REPLACES TD-1 on 3-day weekends (does not stack).
    """
    if not is_three_day_weekend:
        return HolidayPremiumOutput(
            score=0, is_three_day_weekend=False, international_holiday=False,
            holiday_name="", gap_hours=48, iv_premium_detected=False,
            trade_recommendation="NO_TRADE", sizing_pct_nav=0,
            rationale="Not a 3-day weekend. Use TD-1 (WMCE) instead.",
        )

    score = 0.0
    components = []

    # Base: it's a 3-day weekend
    score += 30
    components.append("3-day weekend +30")

    # International market also closed
    if international_holiday_also_closed:
        score += 15
        components.append("International market closed +15")

    # WRS from TD-1 adds context
    wrs_bonus = min(20, friday_wrs * 0.25)
    score += wrs_bonus
    components.append(f"WRS context +{wrs_bonus:.0f}")

    # IV NOT elevated = options are cheap = edge exists
    if friday_iv_vs_trailing_mean < 1.05:
        score += 20
        iv_premium = False
        components.append("IV not elevated +20")
    else:
        iv_premium = True
        components.append("IV already elevated +0 (priced in)")

    # Prior 3-day weekend gap was large
    if prior_three_day_gap_magnitude > 0.01:
        score += 15
        components.append(f"Prior 3-day gap {prior_three_day_gap_magnitude:.2%} +15")

    # Reduce for low-activity holidays
    if holiday_name in LOW_ACTIVITY_HOLIDAYS:
        score *= 0.6
        components.append(f"Low-activity holiday ({holiday_name}) — score reduced 40%")

    score = min(100, max(0, score))

    # Trade recommendation
    if score < 50:
        recommendation = "NO_TRADE"
        sizing = 0.0
    elif score < 80:
        recommendation = "WEEKLY_STRADDLE"
        sizing = 0.0075  # 0.75% NAV
    else:
        recommendation = "WEEKLY_STRANGLE_PLUS_0DTE"
        sizing = 0.01    # 1.0% NAV

    return HolidayPremiumOutput(
        score=score,
        is_three_day_weekend=True,
        international_holiday=international_holiday_also_closed,
        holiday_name=holiday_name,
        gap_hours=gap_hours,
        iv_premium_detected=iv_premium,
        trade_recommendation=recommendation,
        sizing_pct_nav=sizing,
        rationale=f"HPS={score:.0f}. Components: {'; '.join(components)}",
    )


# ============================================================
# TD-3: Sunday Night Liquidity Hole
# ============================================================

@dataclass
class SundayReversionOutput:
    """Sunday Reversion Score (SRS) output."""
    score: float                    # 0-100
    sunday_move_pct: float          # 6-9PM ET return
    volume_percentile: float        # Where Sunday volume sits (0-100)
    news_catalyst_detected: bool
    trade_recommendation: str       # "NO_TRADE" | "FADE_VIA_FUTURES"
    direction: str                  # "LONG" or "SHORT" (opposite of Sunday move)
    sizing_pct_nav: float
    stop_loss_pct: float           # Distance for hard stop
    target_pct: float              # Target: 50% reversion
    hard_exit_time: str
    rationale: str


def compute_sunday_reversion_score(
    sunday_6pm_to_9pm_return: float,       # GC1 return
    sunday_volume_percentile: float,        # vs trailing 252 Sunday volumes (0-100)
    news_catalyst_present: bool,
    friday_wrs: float,
    msil_regime_contradicts: bool,          # Move contradicts detected regime
) -> SundayReversionOutput:
    """
    Compute Sunday Reversion Score.

    Only activates when Sunday 6-9PM move exceeds 0.5%.
    This is a FUTURES trade, not options.
    """
    abs_move = abs(sunday_6pm_to_9pm_return)

    if abs_move < 0.005:  # < 0.5%
        return SundayReversionOutput(
            score=0, sunday_move_pct=sunday_6pm_to_9pm_return,
            volume_percentile=sunday_volume_percentile,
            news_catalyst_detected=news_catalyst_present,
            trade_recommendation="NO_TRADE", direction="NONE",
            sizing_pct_nav=0, stop_loss_pct=0, target_pct=0,
            hard_exit_time="N/A",
            rationale="Sunday move < 0.5%. No trade.",
        )

    score = 0.0
    components = []

    # Move magnitude
    score += 20
    components.append("Move > 0.5% +20")
    if abs_move > 0.01:
        score += 15
        components.append("Move > 1.0% +15")

    # Thin volume = more likely overshoot
    if sunday_volume_percentile < 30:
        score += 25
        components.append(f"Thin volume ({sunday_volume_percentile:.0f}th pctl) +25")
    elif sunday_volume_percentile < 50:
        score += 10
        components.append(f"Below-avg volume ({sunday_volume_percentile:.0f}th pctl) +10")

    # No news catalyst = fear-driven, not event-driven
    if not news_catalyst_present:
        score += 20
        components.append("No news catalyst +20")
    else:
        # News present — move may be real, reduce score
        score -= 15
        components.append("News catalyst detected -15 (move may be justified)")

    # WRS was low on Friday = move contradicts calm setup
    if friday_wrs < 30:
        score += 20
        components.append(f"Friday WRS was low ({friday_wrs:.0f}) +20")

    # Move contradicts regime
    if msil_regime_contradicts:
        score += 10
        components.append("Move contradicts MSIL regime +10")

    score = min(100, max(0, score))

    # Direction: FADE the move
    if sunday_6pm_to_9pm_return > 0:
        direction = "SHORT"  # Gold went up, fade it
    else:
        direction = "LONG"   # Gold went down, fade it

    # Trade recommendation
    if score < 40 or news_catalyst_present:
        recommendation = "NO_TRADE"
        sizing = 0.0
        direction = "NONE"
    else:
        recommendation = "FADE_VIA_FUTURES"
        sizing = 0.003  # 0.3% NAV max

    # Stop and target
    stop_pct = abs_move * 0.5    # Stop if move extends 50% further
    target_pct = abs_move * 0.5  # Target 50% reversion

    return SundayReversionOutput(
        score=score,
        sunday_move_pct=sunday_6pm_to_9pm_return,
        volume_percentile=sunday_volume_percentile,
        news_catalyst_detected=news_catalyst_present,
        trade_recommendation=recommendation,
        direction=direction,
        sizing_pct_nav=sizing,
        stop_loss_pct=stop_pct,
        target_pct=target_pct,
        hard_exit_time="Monday 8:00 AM ET",
        rationale=f"SRS={score:.0f}. {direction} gold. Components: {'; '.join(components)}",
    )


# ============================================================
# TD-4: FOMC Blackout Vol Compression
# ============================================================

@dataclass
class FOMCBlackoutOutput:
    """FOMC Blackout Compression Score (FBCS) output."""
    score: float                    # 0-100
    is_pre_fomc_friday: bool
    blackout_active: bool
    days_until_fomc: int
    gc_weekly_iv_zscore: float
    term_structure_inverted: bool   # Weekly IV < monthly IV
    prior_fomc_gold_move: float
    implied_rate_move_bps: float
    trade_recommendation: str
    sizing_pct_nav: float
    target_expiry: str              # "FOMC+1" typically
    rationale: str


def compute_fomc_blackout_score(
    is_pre_fomc_friday: bool,
    blackout_active: bool,
    days_until_fomc: int,
    gc_weekly_iv_zscore: float,       # vs trailing 63-day weekly IV
    gc_weekly_iv: float,
    gc_monthly_iv: float,
    nps_score: float,                  # Narrative Pressure Score (should be low)
    prior_fomc_gold_move_pct: float,   # |gold move| at last FOMC
    trailing_8_fomc_moves_mean: float, # Mean |gold move| over last 8 FOMCs
    implied_rate_move_bps: float,      # From fed funds futures
) -> FOMCBlackoutOutput:
    """
    Compute FOMC Blackout Compression Score.

    Only activates on Friday before FOMC week, during blackout.
    """
    if not is_pre_fomc_friday or not blackout_active:
        return FOMCBlackoutOutput(
            score=0, is_pre_fomc_friday=is_pre_fomc_friday,
            blackout_active=blackout_active, days_until_fomc=days_until_fomc,
            gc_weekly_iv_zscore=0, term_structure_inverted=False,
            prior_fomc_gold_move=0, implied_rate_move_bps=0,
            trade_recommendation="NO_TRADE", sizing_pct_nav=0,
            target_expiry="N/A",
            rationale="Not a pre-FOMC blackout Friday.",
        )

    score = 0.0
    components = []

    # Base: blackout + FOMC within 5 days
    if days_until_fomc <= 5:
        score += 25
        components.append(f"FOMC in {days_until_fomc} days during blackout +25")
    else:
        score += 10
        components.append(f"FOMC in {days_until_fomc} days (far) +10")

    # Vol compression detected
    if gc_weekly_iv_zscore < -0.5:
        score += 25
        components.append(f"Weekly IV compressed (z={gc_weekly_iv_zscore:+.2f}) +25")
    elif gc_weekly_iv_zscore < 0:
        score += 10
        components.append(f"Weekly IV slightly below avg (z={gc_weekly_iv_zscore:+.2f}) +10")

    # Term structure: weekly IV < monthly IV (contango = short-dated cheap)
    term_inverted = gc_weekly_iv < gc_monthly_iv
    if term_inverted:
        score += 15
        components.append("Weekly IV < Monthly IV (contango confirms compression) +15")

    # Low narrative pressure (blackout is working)
    if nps_score < 3:
        score += 10
        components.append(f"NPS low ({nps_score:.1f}) — blackout suppressing news +10")

    # Prior FOMC moved gold significantly
    if prior_fomc_gold_move_pct > 0.01:
        score += 10
        components.append(f"Last FOMC moved gold {prior_fomc_gold_move_pct:.1%} +10")

    # Fed funds pricing a material move
    if implied_rate_move_bps > 15:
        score += 15
        components.append(f"Market pricing {implied_rate_move_bps:.0f}bp move +15")
    elif implied_rate_move_bps > 5:
        score += 5
        components.append(f"Market pricing {implied_rate_move_bps:.0f}bp move +5")

    score = min(100, max(0, score))

    # Trade recommendation
    if score < 50:
        recommendation = "NO_TRADE"
        sizing = 0.0
    elif score < 70:
        recommendation = "GC_WEEKLY_STRADDLE"
        sizing = 0.005   # 0.5% NAV
    else:
        recommendation = "GC_WEEKLY_STRADDLE_PLUS_0DTE_FOMC"
        sizing = 0.0075  # 0.75% main + 0.25% 0DTE on FOMC day

    return FOMCBlackoutOutput(
        score=score,
        is_pre_fomc_friday=True,
        blackout_active=True,
        days_until_fomc=days_until_fomc,
        gc_weekly_iv_zscore=gc_weekly_iv_zscore,
        term_structure_inverted=term_inverted,
        prior_fomc_gold_move=prior_fomc_gold_move_pct,
        implied_rate_move_bps=implied_rate_move_bps,
        trade_recommendation=recommendation,
        sizing_pct_nav=sizing,
        target_expiry="FOMC+1 day",
        rationale=f"FBCS={score:.0f}. Components: {'; '.join(components)}",
    )


# ============================================================
# TD-5: Gold-Equity Sequencing Lag
# ============================================================

@dataclass
class SequencingLagOutput:
    """Sequencing Lag Score (SLS) output."""
    score: float
    monday_gold_gap_pct: float
    spx_futures_gap_pct: float
    gold_spx_gap_ratio: float
    silver_confirms: bool
    msil_regime_is_stress: bool
    spx_iv_elevated: bool
    trade_recommendation: str       # "NO_TRADE" | "SPX_0DTE_STRADDLE" | "SPX_0DTE_DIRECTIONAL"
    direction_hint: str             # "PUTS" | "CALLS" | "STRADDLE"
    sizing_pct_nav: float
    hard_exit_time: str
    rationale: str


def compute_sequencing_lag_score(
    monday_gold_gap_pct: float,
    silver_gap_same_direction: bool,
    msil_regime: str,
    spx_futures_gap_pct: float,
    spx_0dte_iv_zscore: float,        # SPX 0DTE IV at Monday open vs trailing
) -> SequencingLagOutput:
    """
    Compute Sequencing Lag Score.

    Activates on Monday morning when gold has gapped > 1%.
    Uses SPX 0DTE options, not gold options.
    """
    abs_gold_gap = abs(monday_gold_gap_pct)
    abs_spx_gap = abs(spx_futures_gap_pct) if spx_futures_gap_pct != 0 else 0.001

    if abs_gold_gap < 0.01:  # < 1%
        return SequencingLagOutput(
            score=0, monday_gold_gap_pct=monday_gold_gap_pct,
            spx_futures_gap_pct=spx_futures_gap_pct,
            gold_spx_gap_ratio=0, silver_confirms=False,
            msil_regime_is_stress=False, spx_iv_elevated=False,
            trade_recommendation="NO_TRADE", direction_hint="NONE",
            sizing_pct_nav=0, hard_exit_time="N/A",
            rationale="Gold gap < 1%. No sequencing trade.",
        )

    score = 0.0
    components = []
    is_stress = msil_regime in ("macro_stress", "energy_geopolitics")

    # Gold gap magnitude
    score += 20
    components.append(f"Gold gap {monday_gold_gap_pct:+.2%} +20")
    if abs_gold_gap > 0.02:
        score += 15
        components.append("Gold gap > 2% +15")

    # Silver confirms
    if silver_gap_same_direction:
        score += 15
        components.append("Silver confirms +15")

    # MSIL macro stress regime
    if is_stress:
        score += 15
        components.append(f"MSIL regime: {msil_regime} +15")

    # SPX hasn't caught up
    gap_ratio = abs_gold_gap / abs_spx_gap
    if gap_ratio > 2.0:  # Gold moved 2x more than SPX
        score += 20
        components.append(f"Gold/SPX gap ratio {gap_ratio:.1f}x +20 (SPX lagging)")
    elif gap_ratio > 1.5:
        score += 10
        components.append(f"Gold/SPX gap ratio {gap_ratio:.1f}x +10")

    # SPX IV not yet elevated
    spx_iv_elevated = spx_0dte_iv_zscore > 1.5
    if not spx_iv_elevated:
        score += 15
        components.append(f"SPX 0DTE IV z={spx_0dte_iv_zscore:+.1f} (not elevated) +15")
    else:
        components.append(f"SPX 0DTE IV z={spx_0dte_iv_zscore:+.1f} (already elevated) +0")

    score = min(100, max(0, score))

    # Direction logic
    # Gold UP (haven bid) → SPX likely DOWN → buy puts
    # Gold DOWN (risk-on) → SPX likely UP → buy calls
    # BUT: default to straddle until directional accuracy > 60%
    if monday_gold_gap_pct > 0:
        direction_hint = "PUTS"  # Gold up = fear = SPX down
    else:
        direction_hint = "CALLS"  # Gold down = relief = SPX up

    # Until we validate direction, prefer straddle
    default_to_straddle = True  # Flip this after 100+ data points prove direction

    if score < 50 or spx_iv_elevated:
        recommendation = "NO_TRADE"
        direction_hint = "NONE"
        sizing = 0.0
    elif default_to_straddle:
        recommendation = "SPX_0DTE_STRADDLE"
        direction_hint = "STRADDLE"
        sizing = 0.005  # 0.5% NAV
    else:
        recommendation = "SPX_0DTE_DIRECTIONAL"
        sizing = 0.005

    return SequencingLagOutput(
        score=score,
        monday_gold_gap_pct=monday_gold_gap_pct,
        spx_futures_gap_pct=spx_futures_gap_pct,
        gold_spx_gap_ratio=gap_ratio,
        silver_confirms=silver_gap_same_direction,
        msil_regime_is_stress=is_stress,
        spx_iv_elevated=spx_iv_elevated,
        trade_recommendation=recommendation,
        direction_hint=direction_hint,
        sizing_pct_nav=sizing,
        hard_exit_time="Monday 2:00 PM ET",
        rationale=f"SLS={score:.0f}. {direction_hint}. Components: {'; '.join(components)}",
    )


# ============================================================
# TD-7: Central Bank Bid Skew (Modifies TD-1 Structure)
# ============================================================

@dataclass
class CBSkewOutput:
    """Central Bank Skew Score (CBSS) output."""
    score: float
    gap_skewness_12m: float
    upside_gap_frequency: float      # % of gaps that are positive
    avg_upside_gap: float
    avg_downside_gap: float
    cb_buying_tonnes_quarterly: float
    shanghai_premium: float
    risk_reversal_25d: float
    structure_modification: str      # "NONE" | "CALL_HEAVY" | "RISK_REVERSAL"
    rationale: str


def compute_cb_skew_score(
    trailing_12m_gap_skewness: float,
    trailing_12m_upside_gap_pct: float,  # % of Monday gaps that are positive
    avg_upside_gap: float,
    avg_downside_gap: float,
    cb_buying_quarterly_tonnes: float,
    shanghai_premium_usd: float,         # Shanghai Gold Exchange premium to London
    gold_25d_risk_reversal: float,       # Call IV - Put IV (positive = calls more expensive)
) -> CBSkewOutput:
    """
    Compute Central Bank Skew Score.

    This does NOT generate independent trades. It modifies TD-1 (WMCE)
    trade structure from symmetric straddle to call-heavy structure.
    """
    score = 0.0
    components = []

    # Gap skewness
    if trailing_12m_gap_skewness > 0.3:
        score += 25
        components.append(f"Gap skewness {trailing_12m_gap_skewness:+.2f} +25")
    elif trailing_12m_gap_skewness > 0.15:
        score += 10
        components.append(f"Gap skewness {trailing_12m_gap_skewness:+.2f} +10")

    # Upside gap frequency
    if trailing_12m_upside_gap_pct > 0.55:
        score += 20
        components.append(f"Upside gap freq {trailing_12m_upside_gap_pct:.0%} +20")
    elif trailing_12m_upside_gap_pct > 0.52:
        score += 10
        components.append(f"Upside gap freq {trailing_12m_upside_gap_pct:.0%} +10")

    # Central bank buying
    if cb_buying_quarterly_tonnes > 250:
        score += 15
        components.append(f"CB buying {cb_buying_quarterly_tonnes:.0f}t/quarter +15")
    elif cb_buying_quarterly_tonnes > 150:
        score += 5
        components.append(f"CB buying {cb_buying_quarterly_tonnes:.0f}t/quarter +5")

    # Shanghai premium
    if shanghai_premium_usd > 10:
        score += 15
        components.append(f"Shanghai premium ${shanghai_premium_usd:.0f}/oz +15")
    elif shanghai_premium_usd > 5:
        score += 5
        components.append(f"Shanghai premium ${shanghai_premium_usd:.0f}/oz +5")

    # Options market agrees (risk reversal)
    if gold_25d_risk_reversal > 1.0:
        score += 15
        components.append(f"25d RR {gold_25d_risk_reversal:+.1f} (calls rich) +15")
    elif gold_25d_risk_reversal > 0.5:
        score += 5
        components.append(f"25d RR {gold_25d_risk_reversal:+.1f} +5")

    # ETF outflows (Western selling, CB buying)
    # Omitted here — add when data available
    score += 10  # Placeholder for ETF flow signal
    components.append("ETF flow signal +10 (placeholder)")

    score = min(100, max(0, score))

    # Structure modification
    if score > 60:
        modification = "CALL_HEAVY"
        mod_desc = (
            "Replace ATM straddle with: Long ATM call + Long 3% OTM put. "
            "Captures full upside gap, reduces downside premium ~30%."
        )
    elif score > 40:
        modification = "SLIGHT_CALL_BIAS"
        mod_desc = (
            "Slight call bias: buy 1 extra ATM call per 3 straddles. "
            "Marginal upside exposure without abandoning downside."
        )
    else:
        modification = "NONE"
        mod_desc = "No modification. Use symmetric straddle."

    return CBSkewOutput(
        score=score,
        gap_skewness_12m=trailing_12m_gap_skewness,
        upside_gap_frequency=trailing_12m_upside_gap_pct,
        avg_upside_gap=avg_upside_gap,
        avg_downside_gap=avg_downside_gap,
        cb_buying_tonnes_quarterly=cb_buying_quarterly_tonnes,
        shanghai_premium=shanghai_premium_usd,
        risk_reversal_25d=gold_25d_risk_reversal,
        structure_modification=modification,
        rationale=f"CBSS={score:.0f}. {mod_desc} Components: {'; '.join(components)}",
    )


# ============================================================
# TDE Orchestrator — Combined Position Management
# ============================================================

@dataclass
class TDEPortfolioState:
    """Combined state across all TDE modules."""
    active_modules: list[str]
    total_exposure_pct_nav: float
    weekend_exposure_pct_nav: float
    module_exposures: dict[str, float]
    cap_breached: bool
    warnings: list[str]
    recommendation_summary: str


MAX_COMBINED_EXPOSURE = 0.035      # 3.5% NAV
MAX_WEEKEND_EXPOSURE = 0.020       # 2.0% NAV (TD-1 + TD-2 + TD-3)


def compute_tde_portfolio_state(
    td1_sizing: float,     # WMCE sizing as fraction of NAV
    td2_sizing: float,     # Holiday (replaces TD-1 when active)
    td3_sizing: float,     # Sunday futures
    td4_sizing: float,     # FOMC blackout
    td5_sizing: float,     # Sequencing lag (SPX 0DTE)
    mtce_sizing: float,    # Metals equities (from v0.2.0)
    td2_is_active: bool = False,  # If True, TD-2 replaces TD-1
) -> TDEPortfolioState:
    """
    Enforce combined position limits across all TDE modules.
    """
    warnings = []
    exposures = {}

    # TD-2 replaces TD-1 on holidays
    if td2_is_active:
        exposures["TD-1 (WMCE)"] = 0.0
        exposures["TD-2 (Holiday)"] = td2_sizing
    else:
        exposures["TD-1 (WMCE)"] = td1_sizing
        exposures["TD-2 (Holiday)"] = 0.0

    exposures["TD-3 (Sunday)"] = td3_sizing
    exposures["TD-4 (FOMC)"] = td4_sizing
    exposures["TD-5 (Seq Lag)"] = td5_sizing
    exposures["MTCE (Metals)"] = mtce_sizing

    total = sum(exposures.values())
    weekend = exposures.get("TD-1 (WMCE)", 0) + exposures.get("TD-2 (Holiday)", 0) + exposures.get("TD-3 (Sunday)", 0)

    active = [name for name, size in exposures.items() if size > 0]
    cap_breached = False

    if total > MAX_COMBINED_EXPOSURE:
        cap_breached = True
        warnings.append(
            f"COMBINED EXPOSURE {total:.2%} exceeds cap {MAX_COMBINED_EXPOSURE:.2%}. "
            f"Reduce lowest-priority modules."
        )

    if weekend > MAX_WEEKEND_EXPOSURE:
        cap_breached = True
        warnings.append(
            f"WEEKEND EXPOSURE {weekend:.2%} exceeds cap {MAX_WEEKEND_EXPOSURE:.2%}. "
            f"Reduce TD-3 (lowest weekend priority)."
        )

    summary_parts = []
    for name, size in exposures.items():
        if size > 0:
            summary_parts.append(f"{name}: {size:.2%}")
    summary = f"Total: {total:.2%} NAV. Active: {', '.join(summary_parts)}"

    return TDEPortfolioState(
        active_modules=active,
        total_exposure_pct_nav=total,
        weekend_exposure_pct_nav=weekend,
        module_exposures=exposures,
        cap_breached=cap_breached,
        warnings=warnings,
        recommendation_summary=summary,
    )


# ============================================================
# Unified Report
# ============================================================

def format_tde_report(
    td2: Optional[HolidayPremiumOutput] = None,
    td3: Optional[SundayReversionOutput] = None,
    td4: Optional[FOMCBlackoutOutput] = None,
    td5: Optional[SequencingLagOutput] = None,
    td7: Optional[CBSkewOutput] = None,
    portfolio: Optional[TDEPortfolioState] = None,
    timestamp: str = "",
) -> str:
    """Unified TDE report."""
    lines = [
        "=" * 70,
        f"  AURUM TEMPORAL DISCONTINUITY ENGINE — {timestamp or 'N/A'}",
        "=" * 70,
        "",
    ]

    modules = [
        ("TD-2 HOLIDAY PREMIUM", td2),
        ("TD-3 SUNDAY REVERSION", td3),
        ("TD-4 FOMC BLACKOUT", td4),
        ("TD-5 SEQUENCING LAG", td5),
        ("TD-7 CB SKEW", td7),
    ]

    for name, mod in modules:
        if mod is None:
            continue
        lines.append(f"  {name}")
        lines.append(f"    Score: {mod.score:.0f}")
        rec = getattr(mod, 'trade_recommendation', getattr(mod, 'structure_modification', 'N/A'))
        lines.append(f"    Recommendation: {rec}")
        if hasattr(mod, 'sizing_pct_nav') and mod.sizing_pct_nav > 0:
            lines.append(f"    Sizing: {mod.sizing_pct_nav:.2%} NAV")
        lines.append(f"    {mod.rationale}")
        lines.append("")

    if portfolio:
        lines.append("  PORTFOLIO STATE")
        lines.append(f"    Total Exposure:   {portfolio.total_exposure_pct_nav:.2%} NAV")
        lines.append(f"    Weekend Exposure:  {portfolio.weekend_exposure_pct_nav:.2%} NAV")
        lines.append(f"    Cap Breached:      {'YES ⚠' if portfolio.cap_breached else 'No'}")
        lines.append(f"    Active Modules:    {', '.join(portfolio.active_modules)}")
        if portfolio.warnings:
            for w in portfolio.warnings:
                lines.append(f"    ⚠ {w}")

    lines.extend(["", "=" * 70])
    return "\n".join(lines)


# ============================================================
# Smoke Test
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  TDE SMOKE TEST")
    print("=" * 70)

    # TD-2: Presidents' Day weekend
    td2 = compute_holiday_premium_score(
        is_three_day_weekend=True,
        holiday_name="Presidents Day",
        international_holiday_also_closed=False,
        friday_wrs=65.0,
        friday_iv_vs_trailing_mean=0.98,
        prior_three_day_gap_magnitude=0.015,
    )
    print(f"\nTD-2: {td2.rationale}")
    print(f"  Score: {td2.score:.0f}, Rec: {td2.trade_recommendation}")

    # TD-3: Sunday night spike
    td3 = compute_sunday_reversion_score(
        sunday_6pm_to_9pm_return=0.012,  # +1.2% spike
        sunday_volume_percentile=15.0,
        news_catalyst_present=False,
        friday_wrs=22.0,
        msil_regime_contradicts=True,
    )
    print(f"\nTD-3: {td3.rationale}")
    print(f"  Score: {td3.score:.0f}, Rec: {td3.trade_recommendation}, Dir: {td3.direction}")

    # TD-4: FOMC blackout
    td4 = compute_fomc_blackout_score(
        is_pre_fomc_friday=True,
        blackout_active=True,
        days_until_fomc=4,
        gc_weekly_iv_zscore=-0.8,
        gc_weekly_iv=19.0,
        gc_monthly_iv=21.0,
        nps_score=1.5,
        prior_fomc_gold_move_pct=0.018,
        trailing_8_fomc_moves_mean=0.012,
        implied_rate_move_bps=22.0,
    )
    print(f"\nTD-4: {td4.rationale}")
    print(f"  Score: {td4.score:.0f}, Rec: {td4.trade_recommendation}")

    # TD-5: Monday morning gold gap
    td5 = compute_sequencing_lag_score(
        monday_gold_gap_pct=0.022,
        silver_gap_same_direction=True,
        msil_regime="macro_stress",
        spx_futures_gap_pct=-0.008,
        spx_0dte_iv_zscore=0.5,
    )
    print(f"\nTD-5: {td5.rationale}")
    print(f"  Score: {td5.score:.0f}, Rec: {td5.trade_recommendation}")

    # TD-7: Central bank skew
    td7 = compute_cb_skew_score(
        trailing_12m_gap_skewness=0.42,
        trailing_12m_upside_gap_pct=0.58,
        avg_upside_gap=0.011,
        avg_downside_gap=-0.007,
        cb_buying_quarterly_tonnes=290,
        shanghai_premium_usd=15.0,
        gold_25d_risk_reversal=1.3,
    )
    print(f"\nTD-7: {td7.rationale}")
    print(f"  Score: {td7.score:.0f}, Modification: {td7.structure_modification}")

    # Portfolio state
    portfolio = compute_tde_portfolio_state(
        td1_sizing=0.01,
        td2_sizing=0.0,
        td3_sizing=0.003,
        td4_sizing=0.005,
        td5_sizing=0.005,
        mtce_sizing=0.005,
    )
    print(f"\n{format_tde_report(td2, td3, td4, td5, td7, portfolio, '2026-02-15')}")
