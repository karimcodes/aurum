"""
AURUM Market Intelligence Layer (MIL)
=======================================
Replaces the basic NLP layer from WMCE v0.1.0 with a comprehensive
market intelligence framework covering:

  1. Narrative Analysis (upgraded NLP — sentiment, not just keywords)
  2. Smart Money Positioning (COT, options flow, dark pool signals)
  3. Narrative Shift Detection (acceleration/deceleration of themes)
  4. Institutional Flow Scoring (what large players are doing Friday PM)

Feeds into WRS as a richer, more informative context layer.

Design Principles:
  - No black-box sentiment models (they fail on financial text)
  - Measurable, backtestable features only
  - Smart money signals are lagging but directional — use as confirmation
  - Narrative shifts are leading — use as primary NLP signal
  - All features have null hypotheses
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from math import exp


# ============================================================
# 1. UPGRADED NARRATIVE ANALYSIS
# ============================================================

class NarrativeDirection(Enum):
    ESCALATING = "escalating"
    STABLE = "stable"
    DE_ESCALATING = "de_escalating"


@dataclass
class Headline:
    """Single headline from news feed."""
    text: str
    source: str           # "reuters", "bloomberg", "dowjones"
    timestamp: float      # Unix timestamp
    tier: int = 0         # 0 = no match, 1 = tier1, 2 = tier2
    is_escalation: bool = False   # True if headline signals INCREASE in risk
    is_deescalation: bool = False # True if headline signals DECREASE in risk


# Keyword dictionaries with DIRECTION awareness
RISK_KEYWORDS = {
    'tier1_geopolitical': {
        'escalation': ['war', 'invasion', 'nuclear', 'escalation', 'missile strike',
                       'military operation', 'retaliation', 'mobilization', 'ultimatum',
                       'blockade', 'attack', 'offensive'],
        'deescalation': ['ceasefire', 'peace talks', 'de-escalation', 'withdrawal',
                         'diplomatic resolution', 'agreement reached', 'stand down',
                         'truce', 'negotiations resume'],
    },
    'tier1_financial': {
        'escalation': ['default', 'contagion', 'liquidity crisis', 'bank run',
                       'margin call', 'systemic risk', 'credit freeze', 'insolvency',
                       'emergency lending', 'circuit breaker'],
        'deescalation': ['bailout', 'rescue package', 'liquidity injection',
                         'crisis averted', 'stabilization', 'recovery', 'contained'],
    },
    'tier2_central_bank': {
        'escalation': ['emergency meeting', 'hawkish surprise', 'rate hike shock',
                       'QT acceleration', 'intervention', 'currency crisis',
                       'policy error'],
        'deescalation': ['dovish pivot', 'rate pause', 'policy support',
                         'accommodation', 'easing signal', 'forward guidance calm'],
    },
    'tier2_macro': {
        'escalation': ['recession confirmed', 'inflation surge', 'debt ceiling breach',
                       'downgrade', 'tariff escalation', 'trade war expansion',
                       'sanctions expanded', 'embargo'],
        'deescalation': ['soft landing', 'inflation cooling', 'debt deal reached',
                         'tariff reduction', 'trade deal', 'sanctions lifted',
                         'growth surprise'],
    },
}

# Weights
TIER_WEIGHTS = {1: 3.0, 2: 1.0}
DIRECTION_MULTIPLIERS = {
    'escalation': 1.0,      # Full weight for risk-increasing headlines
    'deescalation': -0.6,   # Partial negative weight — deescalation is less impactful
    'neutral': 0.3,         # Matched keyword but can't determine direction
}


@dataclass
class NarrativeAnalysisOutput:
    """Enhanced Narrative Pressure Score with direction awareness."""
    nps_raw: float                        # Raw score (can be negative if deescalating)
    nps_capped: float                     # Capped 0-12 for WRS integration
    direction: NarrativeDirection
    escalation_count: int
    deescalation_count: int
    net_direction_score: float            # Positive = escalating, negative = deescalating
    top_headlines: List[str]              # Top 5 most impactful headlines
    velocity_1h: float                    # Headlines per hour, trailing 1h
    velocity_6h: float                    # Headlines per hour, trailing 6h
    velocity_24h: float                   # Headlines per hour, trailing 24h
    interpretation: str


def analyze_narrative(
    headlines: List[Headline],
    measurement_time: float,              # Unix timestamp (Friday 3PM ET)
    decay_halflife_hours: float = 6.0,
) -> NarrativeAnalysisOutput:
    """
    Enhanced narrative analysis with direction awareness.

    Key improvement over v0.1.0:
    - Distinguishes escalation from deescalation
    - Measures headline velocity (acceleration)
    - Weights by source credibility
    - Produces a DIRECTIONAL score, not just magnitude
    """
    score = 0.0
    escalation_count = 0
    deescalation_count = 0
    scored_headlines = []

    for headline in headlines:
        age_hours = (measurement_time - headline.timestamp) / 3600
        if age_hours < 0 or age_hours > 48:
            continue

        decay = exp(-0.693 * age_hours / decay_halflife_hours)
        text_lower = headline.text.lower()

        # Source credibility weight
        source_weight = {'reuters': 1.2, 'bloomberg': 1.2, 'dowjones': 1.0}.get(
            headline.source.lower(), 0.8
        )

        matched = False
        direction = 'neutral'
        tier = 0

        for tier_name, directions in RISK_KEYWORDS.items():
            tier_num = 1 if 'tier1' in tier_name else 2

            # Check escalation keywords
            for kw in directions.get('escalation', []):
                if kw in text_lower:
                    matched = True
                    direction = 'escalation'
                    tier = tier_num
                    escalation_count += 1
                    break

            # Check deescalation keywords (only if no escalation match)
            if not matched:
                for kw in directions.get('deescalation', []):
                    if kw in text_lower:
                        matched = True
                        direction = 'deescalation'
                        tier = tier_num
                        deescalation_count += 1
                        break

            if matched:
                break

        if matched:
            tier_weight = TIER_WEIGHTS.get(tier, 1.0)
            dir_mult = DIRECTION_MULTIPLIERS[direction]
            contribution = tier_weight * dir_mult * decay * source_weight
            score += contribution
            scored_headlines.append((abs(contribution), headline.text[:80]))

    # Headline velocity (raw count per hour)
    def velocity_window(hours):
        cutoff = measurement_time - (hours * 3600)
        count = sum(1 for h in headlines if h.timestamp >= cutoff and h.timestamp <= measurement_time)
        return count / max(hours, 0.01)

    vel_1h = velocity_window(1)
    vel_6h = velocity_window(6)
    vel_24h = velocity_window(24)

    # Net direction
    net_direction = escalation_count - (deescalation_count * 0.6)

    if net_direction > 3:
        direction_state = NarrativeDirection.ESCALATING
    elif net_direction < -2:
        direction_state = NarrativeDirection.DE_ESCALATING
    else:
        direction_state = NarrativeDirection.STABLE

    # Cap for WRS integration (0-12)
    nps_capped = max(0, min(12, score))

    # Top headlines by impact
    scored_headlines.sort(key=lambda x: x[0], reverse=True)
    top_5 = [h[1] for h in scored_headlines[:5]]

    # Interpretation
    if direction_state == NarrativeDirection.ESCALATING and nps_capped > 6:
        interp = f"HIGH alert: narrative escalating ({escalation_count} escalation headlines). Weekend gap probability elevated."
    elif direction_state == NarrativeDirection.DE_ESCALATING:
        interp = f"De-escalation detected ({deescalation_count} de-escalation headlines). Weekend gap may be downside (haven unwind)."
    elif vel_1h > vel_24h * 3:
        interp = f"Headline velocity SPIKING: {vel_1h:.1f}/hr vs {vel_24h:.1f}/hr avg. Something is developing."
    else:
        interp = f"Narrative stable. {escalation_count} risk, {deescalation_count} de-risk headlines."

    return NarrativeAnalysisOutput(
        nps_raw=score,
        nps_capped=nps_capped,
        direction=direction_state,
        escalation_count=escalation_count,
        deescalation_count=deescalation_count,
        net_direction_score=net_direction,
        top_headlines=top_5,
        velocity_1h=vel_1h,
        velocity_6h=vel_6h,
        velocity_24h=vel_24h,
        interpretation=interp,
    )


# ============================================================
# 2. SMART MONEY POSITIONING
# ============================================================

@dataclass
class COTData:
    """Commitment of Traders report data for gold futures."""
    report_date: str                      # Friday date
    managed_money_net_long: int           # Net long contracts (managed money)
    managed_money_net_long_change: int    # Week-over-week change
    commercial_net_short: int             # Commercial hedger net short
    commercial_net_short_change: int
    open_interest_total: int
    open_interest_change: int
    managed_money_pct_oi: float           # Managed money as % of total OI


@dataclass
class SmartMoneyOutput:
    """Smart money positioning analysis."""
    positioning_score: float              # -100 to +100
    crowding_risk: str                    # "LOW" | "MODERATE" | "HIGH" | "EXTREME"
    managed_money_percentile: float       # Where current positioning sits (0-100)
    position_change_signal: str           # "ADDING" | "REDUCING" | "FLAT"
    options_flow_score: float             # -50 to +50 (positive = smart money buying protection)
    dark_pool_signal: str                 # "INSTITUTIONAL_SELLING" | "NEUTRAL" | "INSTITUTIONAL_BUYING"
    interpretation: str
    wrs_adjustment: float                 # -5 to +10 points for WRS


class SmartMoneyAnalyzer:
    """
    Analyzes institutional positioning and flow data.

    Data sources:
      - COT report (released Friday 3:30 PM ET — in our trading window!)
      - Options flow (large block trades in GC options, GDX options)
      - Dark pool / block trade data (GDX, NEM, FCX)

    Key insight: Smart money positioning is LAGGING (tells you where they
    were as of Tuesday, reported Friday). But CHANGES in positioning are
    more informative — a big reduction in managed money longs going into
    a weekend signals institutional fear.
    """

    def __init__(self, lookback_weeks: int = 52):
        self.lookback_weeks = lookback_weeks

    def analyze_cot(
        self,
        current: COTData,
        historical_net_longs: List[int],    # Trailing 52 weeks of managed money net longs
    ) -> dict:
        """Analyze COT positioning."""
        if not historical_net_longs:
            return {
                'percentile': 50.0,
                'crowding': 'UNKNOWN',
                'change_signal': 'FLAT',
            }

        # Percentile of current positioning
        count_below = sum(1 for v in historical_net_longs if v < current.managed_money_net_long)
        percentile = (count_below / len(historical_net_longs)) * 100

        # Crowding assessment
        if percentile > 90:
            crowding = "EXTREME"
        elif percentile > 75:
            crowding = "HIGH"
        elif percentile > 50:
            crowding = "MODERATE"
        else:
            crowding = "LOW"

        # Week-over-week change
        if current.managed_money_net_long_change > 5000:
            change = "ADDING"
        elif current.managed_money_net_long_change < -5000:
            change = "REDUCING"
        else:
            change = "FLAT"

        return {
            'percentile': percentile,
            'crowding': crowding,
            'change_signal': change,
        }

    def analyze_options_flow(
        self,
        friday_large_put_volume: int,     # Large (>100 contract) put trades on GC/GDX
        friday_large_call_volume: int,    # Large (>100 contract) call trades
        friday_avg_large_put_vol: float,  # 21-day average
        friday_avg_large_call_vol: float,
    ) -> dict:
        """
        Analyze Friday options flow for institutional hedging signals.

        Large put buying on Friday = institutions hedging weekend downside.
        Large call buying on Friday = institutions positioning for upside gap.
        Both elevated = institutions expect BIG move (direction uncertain).
        """
        if friday_avg_large_put_vol == 0 or friday_avg_large_call_vol == 0:
            return {'score': 0, 'signal': 'NO_DATA'}

        put_ratio = friday_large_put_volume / friday_avg_large_put_vol
        call_ratio = friday_large_call_volume / friday_avg_large_call_vol

        # Score: positive = smart money buying protection (bearish/fearful)
        #        negative = smart money buying upside (bullish)
        score = (put_ratio - call_ratio) * 25  # Scale to ~±50

        if put_ratio > 2.0 and call_ratio > 2.0:
            signal = "BOTH_ELEVATED"  # Expect big move, direction unclear
        elif put_ratio > 2.0:
            signal = "HEAVY_PUT_BUYING"  # Institutional hedging
        elif call_ratio > 2.0:
            signal = "HEAVY_CALL_BUYING"  # Institutional upside positioning
        else:
            signal = "NORMAL"

        return {'score': max(-50, min(50, score)), 'signal': signal}

    def analyze_dark_pool(
        self,
        gdx_block_trades_net: float,       # Net block trade value (positive = buying)
        gdx_block_trades_avg: float,       # 21-day average net
        nem_block_trades_net: float,
        nem_block_trades_avg: float,
    ) -> dict:
        """
        Analyze dark pool / block trade activity in gold miners.

        Large net selling in miners on Friday = institutions reducing weekend
        exposure = behavioral signal that institutions fear a weekend event.
        """
        gdx_z = 0.0
        if gdx_block_trades_avg != 0:
            gdx_z = (gdx_block_trades_net - gdx_block_trades_avg) / max(abs(gdx_block_trades_avg), 1)

        nem_z = 0.0
        if nem_block_trades_avg != 0:
            nem_z = (nem_block_trades_net - nem_block_trades_avg) / max(abs(nem_block_trades_avg), 1)

        avg_z = (gdx_z + nem_z) / 2

        if avg_z < -1.5:
            signal = "INSTITUTIONAL_SELLING"
        elif avg_z > 1.5:
            signal = "INSTITUTIONAL_BUYING"
        else:
            signal = "NEUTRAL"

        return {'signal': signal, 'z_score': avg_z}

    def compute_smart_money_score(
        self,
        cot: COTData,
        historical_net_longs: List[int],
        friday_large_put_volume: int,
        friday_large_call_volume: int,
        friday_avg_large_put_vol: float,
        friday_avg_large_call_vol: float,
        gdx_block_net: float,
        gdx_block_avg: float,
        nem_block_net: float,
        nem_block_avg: float,
    ) -> SmartMoneyOutput:
        """Compute unified smart money positioning score."""

        cot_analysis = self.analyze_cot(cot, historical_net_longs)
        flow_analysis = self.analyze_options_flow(
            friday_large_put_volume, friday_large_call_volume,
            friday_avg_large_put_vol, friday_avg_large_call_vol,
        )
        dark_pool = self.analyze_dark_pool(
            gdx_block_net, gdx_block_avg, nem_block_net, nem_block_avg,
        )

        # Composite positioning score (-100 to +100)
        # Positive = smart money is defensive (buying puts, selling miners)
        # This means THEY expect a weekend event — bullish for our straddle thesis
        positioning = 0.0

        # COT: extreme crowding in either direction adds risk
        if cot_analysis['crowding'] == "EXTREME":
            positioning += 30  # Crowded = vulnerable to weekend gap
        elif cot_analysis['crowding'] == "HIGH":
            positioning += 15

        # COT: managed money reducing = they're getting out before weekend
        if cot_analysis['change_signal'] == "REDUCING":
            positioning += 20  # Institutional fear
        elif cot_analysis['change_signal'] == "ADDING":
            positioning -= 10  # Complacency (less likely to gap on fear)

        # Options flow
        positioning += flow_analysis['score'] * 0.5

        # Dark pool
        if dark_pool['signal'] == "INSTITUTIONAL_SELLING":
            positioning += 25  # Institutions dumping miners = weekend fear
        elif dark_pool['signal'] == "INSTITUTIONAL_BUYING":
            positioning -= 15  # Institutions confident = less fear

        positioning = max(-100, min(100, positioning))

        # WRS adjustment
        if positioning > 50:
            wrs_adj = 10.0
            interp = "Smart money is DEFENSIVE. Institutions hedging weekend risk heavily. Straddle thesis supported."
        elif positioning > 20:
            wrs_adj = 5.0
            interp = "Smart money moderately cautious. Some institutional hedging detected."
        elif positioning > -20:
            wrs_adj = 0.0
            interp = "Smart money neutral. No strong positioning signal."
        elif positioning > -50:
            wrs_adj = -5.0
            interp = "Smart money complacent. Institutions NOT hedging weekend risk. Gap less likely."
        else:
            wrs_adj = -8.0
            interp = "Smart money aggressively bullish/complacent. Low weekend gap probability."

        return SmartMoneyOutput(
            positioning_score=positioning,
            crowding_risk=cot_analysis['crowding'],
            managed_money_percentile=cot_analysis['percentile'],
            position_change_signal=cot_analysis['change_signal'],
            options_flow_score=flow_analysis['score'],
            dark_pool_signal=dark_pool['signal'],
            interpretation=interp,
            wrs_adjustment=wrs_adj,
        )


# ============================================================
# 3. NARRATIVE SHIFT DETECTION
# ============================================================

@dataclass
class NarrativeShiftOutput:
    """Detects acceleration or deceleration of narrative themes."""
    shift_detected: bool
    shift_type: str                       # "NEW_THEME" | "ACCELERATION" | "DECELERATION" | "NONE"
    velocity_ratio: float                 # Current / trailing velocity
    theme_identified: str                 # e.g., "geopolitical_escalation", "trade_war"
    time_since_shift_hours: float
    wrs_adjustment: float                 # Shift bonus for WRS
    interpretation: str


def detect_narrative_shift(
    velocity_1h: float,
    velocity_6h: float,
    velocity_24h: float,
    velocity_48h: float,
    dominant_theme_current: str,          # Most common keyword category in last 6h
    dominant_theme_prior: str,            # Most common keyword category in prior 24h
    escalation_count_6h: int,
    escalation_count_prior_24h: int,
) -> NarrativeShiftOutput:
    """
    Detect narrative shifts — the CHANGE in narrative is more predictive
    than the level.

    A narrative shift occurs when:
    1. Headline velocity spikes (new development)
    2. The dominant theme changes (new topic)
    3. Escalation rate accelerates (existing topic getting worse)
    """
    shift_detected = False
    shift_type = "NONE"
    theme = "none"
    wrs_adj = 0.0

    # Velocity spike detection
    velocity_ratio = velocity_1h / max(velocity_24h, 0.01)

    # New development: velocity in last hour is 3x+ the 24h average
    if velocity_ratio > 3.0:
        shift_detected = True
        shift_type = "ACCELERATION"
        theme = dominant_theme_current
        wrs_adj = 8.0
    elif velocity_ratio > 2.0:
        shift_detected = True
        shift_type = "ACCELERATION"
        theme = dominant_theme_current
        wrs_adj = 4.0

    # Theme change: dominant topic shifted
    if dominant_theme_current != dominant_theme_prior and dominant_theme_current != "none":
        shift_detected = True
        if shift_type == "NONE":
            shift_type = "NEW_THEME"
        else:
            shift_type = "NEW_THEME_WITH_ACCELERATION"
        theme = dominant_theme_current
        wrs_adj = max(wrs_adj, 6.0)

    # Escalation acceleration
    # Normalize to per-hour rate
    esc_rate_recent = escalation_count_6h / 6
    esc_rate_prior = escalation_count_prior_24h / 24
    if esc_rate_prior > 0 and esc_rate_recent > esc_rate_prior * 2:
        shift_detected = True
        if "ACCELERATION" not in shift_type:
            shift_type = "ESCALATION_ACCELERATION"
        wrs_adj = max(wrs_adj, 7.0)

    # Deceleration detection (can REDUCE WRS)
    if velocity_ratio < 0.3 and velocity_24h > 1.0:
        # Headlines were flowing but have stopped — tension may be resolving
        shift_detected = True
        shift_type = "DECELERATION"
        wrs_adj = -5.0
        theme = dominant_theme_prior

    # Time since shift (approximate — would need actual event detection)
    time_since = 0.5 if velocity_ratio > 3.0 else 3.0 if velocity_ratio > 2.0 else 24.0

    # Interpretation
    if shift_type == "NEW_THEME_WITH_ACCELERATION":
        interp = f"⚠ NEW THEME emerging with accelerating coverage: {theme}. Highest-impact narrative shift."
    elif shift_type == "ACCELERATION":
        interp = f"Headline velocity spiking ({velocity_ratio:.1f}x normal). Developing situation on: {theme}."
    elif shift_type == "NEW_THEME":
        interp = f"Narrative theme shifted from {dominant_theme_prior} to {theme}. Market may be repricing."
    elif shift_type == "ESCALATION_ACCELERATION":
        interp = f"Escalation rate doubling on {theme}. Situation is deteriorating."
    elif shift_type == "DECELERATION":
        interp = f"Headlines decelerating on {theme}. Tension may be resolving. Potential relief gap Monday."
    else:
        interp = "No narrative shift detected. Steady state."

    return NarrativeShiftOutput(
        shift_detected=shift_detected,
        shift_type=shift_type,
        velocity_ratio=velocity_ratio,
        theme_identified=theme,
        time_since_shift_hours=time_since,
        wrs_adjustment=wrs_adj,
        interpretation=interp,
    )


# ============================================================
# 4. UNIFIED MARKET INTELLIGENCE SCORE
# ============================================================

@dataclass
class MarketIntelligenceOutput:
    """Combined output from all intelligence sources."""
    # Component scores
    narrative: NarrativeAnalysisOutput
    smart_money: SmartMoneyOutput
    narrative_shift: NarrativeShiftOutput
    event_calendar_score: float           # 0-5 (from v0.1.0 ECS)

    # Combined
    total_wrs_contribution: float         # Combined points for WRS
    max_contribution: float               # Cap
    interpretation: str


def compute_market_intelligence(
    narrative: NarrativeAnalysisOutput,
    smart_money: SmartMoneyOutput,
    narrative_shift: NarrativeShiftOutput,
    event_calendar_score: float,
) -> MarketIntelligenceOutput:
    """
    Combine all intelligence sources into a unified WRS contribution.

    Budget: up to 25 points of WRS (increased from 15 in v0.1.0
    because we now have richer, more informative signals).

    Breakdown:
      - Narrative (NPS):        0-12 points (upgraded from v0.1.0)
      - Smart Money:            -8 to +10 points
      - Narrative Shift:        -5 to +8 points
      - Event Calendar:         0-5 points
      Combined cap:             -5 to +25 points
    """
    total = (
        narrative.nps_capped +
        smart_money.wrs_adjustment +
        narrative_shift.wrs_adjustment +
        min(5, event_calendar_score)
    )

    total = max(-5, min(25, total))

    # Interpretation
    parts = []
    if narrative.nps_capped > 6:
        parts.append(f"narrative pressure HIGH ({narrative.nps_capped:.0f})")
    if smart_money.wrs_adjustment > 5:
        parts.append("smart money defensive")
    elif smart_money.wrs_adjustment < -3:
        parts.append("smart money complacent")
    if narrative_shift.shift_detected:
        parts.append(f"shift: {narrative_shift.shift_type}")
    if event_calendar_score > 3:
        parts.append("weekend events scheduled")

    if parts:
        interp = f"Intelligence contributing {total:+.0f} to WRS. Drivers: {'; '.join(parts)}"
    else:
        interp = f"Intelligence contributing {total:+.0f} to WRS. No strong signals."

    return MarketIntelligenceOutput(
        narrative=narrative,
        smart_money=smart_money,
        narrative_shift=narrative_shift,
        event_calendar_score=event_calendar_score,
        total_wrs_contribution=total,
        max_contribution=25,
        interpretation=interp,
    )


def format_intelligence_report(mil: MarketIntelligenceOutput, timestamp: str = "") -> str:
    """Human-readable intelligence report."""
    n = mil.narrative
    sm = mil.smart_money
    ns = mil.narrative_shift

    lines = [
        "=" * 70,
        f"  AURUM MARKET INTELLIGENCE REPORT — {timestamp or 'N/A'}",
        "=" * 70,
        "",
        f"  TOTAL WRS CONTRIBUTION: {mil.total_wrs_contribution:+.0f} / {mil.max_contribution:.0f} max",
        f"  {mil.interpretation}",
        "",
        "  ─── NARRATIVE ANALYSIS ───",
        f"    NPS Score:       {n.nps_capped:.0f} / 12",
        f"    Direction:       {n.direction.value.upper()}",
        f"    Escalation:      {n.escalation_count} headlines",
        f"    De-escalation:   {n.deescalation_count} headlines",
        f"    Velocity:        {n.velocity_1h:.1f}/hr (1h) | {n.velocity_6h:.1f}/hr (6h) | {n.velocity_24h:.1f}/hr (24h)",
        f"    {n.interpretation}",
    ]
    if n.top_headlines:
        lines.append("    Top Headlines:")
        for h in n.top_headlines[:3]:
            lines.append(f"      • {h}")

    lines.extend([
        "",
        "  ─── SMART MONEY POSITIONING ───",
        f"    Positioning Score:  {sm.positioning_score:+.0f} / 100",
        f"    Crowding Risk:      {sm.crowding_risk}",
        f"    Managed Money:      {sm.managed_money_percentile:.0f}th percentile",
        f"    Position Change:    {sm.position_change_signal}",
        f"    Options Flow:       {sm.options_flow_score:+.0f} (+ = put heavy)",
        f"    Dark Pool:          {sm.dark_pool_signal}",
        f"    WRS Adjustment:     {sm.wrs_adjustment:+.0f}",
        f"    {sm.interpretation}",
        "",
        "  ─── NARRATIVE SHIFT ───",
        f"    Shift Detected:     {'YES' if ns.shift_detected else 'No'}",
        f"    Type:               {ns.shift_type}",
        f"    Velocity Ratio:     {ns.velocity_ratio:.1f}x normal",
        f"    Theme:              {ns.theme_identified}",
        f"    WRS Adjustment:     {ns.wrs_adjustment:+.0f}",
        f"    {ns.interpretation}",
        "",
        "=" * 70,
    ])
    return "\n".join(lines)


# ============================================================
# Smoke Test
# ============================================================

if __name__ == "__main__":
    import time

    now = time.time()

    # Simulate Friday afternoon with escalating geopolitical headlines
    headlines = [
        Headline("Russia threatens nuclear retaliation over NATO expansion", "reuters", now - 3600),
        Headline("China announces expanded rare earth export controls", "bloomberg", now - 7200),
        Headline("US sanctions expanded to cover Russian gold exports", "reuters", now - 1800),
        Headline("NATO emergency meeting called for Saturday", "dowjones", now - 900),
        Headline("Oil prices surge on Middle East escalation fears", "bloomberg", now - 5400),
        Headline("Fed officials signal rate pause at next meeting", "reuters", now - 14400),
        Headline("Trade deal progress between US and EU reported", "bloomberg", now - 28800),
    ]

    # Narrative analysis
    narrative = analyze_narrative(headlines, now)
    print(f"Narrative: NPS={narrative.nps_capped:.0f}, Direction={narrative.direction.value}")

    # Smart money
    cot = COTData(
        report_date="2026-02-13",
        managed_money_net_long=185000,
        managed_money_net_long_change=-12000,  # Reducing!
        commercial_net_short=210000,
        commercial_net_short_change=-8000,
        open_interest_total=550000,
        open_interest_change=-15000,
        managed_money_pct_oi=0.34,
    )

    analyzer = SmartMoneyAnalyzer()
    smart_money = analyzer.compute_smart_money_score(
        cot=cot,
        historical_net_longs=[150000 + i * 500 for i in range(52)],
        friday_large_put_volume=450,
        friday_large_call_volume=180,
        friday_avg_large_put_vol=200,
        friday_avg_large_call_vol=200,
        gdx_block_net=-8500000,    # $8.5M net selling
        gdx_block_avg=-1200000,
        nem_block_net=-3200000,    # $3.2M net selling
        nem_block_avg=-500000,
    )
    print(f"Smart Money: {smart_money.positioning_score:+.0f}, {smart_money.interpretation}")

    # Narrative shift
    shift = detect_narrative_shift(
        velocity_1h=4.0,
        velocity_6h=2.5,
        velocity_24h=1.2,
        velocity_48h=0.8,
        dominant_theme_current="geopolitical_escalation",
        dominant_theme_prior="trade_policy",
        escalation_count_6h=5,
        escalation_count_prior_24h=3,
    )
    print(f"Narrative Shift: {shift.shift_type}, {shift.interpretation}")

    # Combined
    mil = compute_market_intelligence(narrative, smart_money, shift, event_calendar_score=5.0)
    print(f"\n{format_intelligence_report(mil, '2026-02-14 15:00 ET')}")
