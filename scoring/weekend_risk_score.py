"""
AURUM Weekend Risk Score Engine
================================
Computes the composite Weekend Risk Score (WRS) from individual signal components.

All signals are measured as of Friday ~3:00 PM ET.
Score range: 0-100 (capped).

This module is the single source of truth for score composition.
Signal weights and thresholds are loaded from config, never hardcoded in logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math


class RegimeState(Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    DORMANT = "dormant"
    KILLED = "killed"


@dataclass
class SignalOutput:
    """Individual signal contribution to WRS."""
    name: str
    raw_value: float          # The measured quantity (e.g., return, ratio)
    score: float              # Contribution to WRS (0 to max_score)
    max_score: float          # Maximum possible contribution
    triggered: bool           # Whether threshold was exceeded
    description: str          # Human-readable explanation
    confidence: float = 1.0   # 0-1, reduced for data quality issues


@dataclass
class WeekendRiskScore:
    """Complete WRS output with full attribution."""
    composite_score: float                    # 0-100
    signal_outputs: list[SignalOutput]         # All component signals
    regime_state: RegimeState
    trade_recommendation: str                 # "NO_TRADE" | "MONITOR" | "SMALL" | "STANDARD" | "MAXIMUM"
    override_active: bool = False             # True if WRS>90 IV check triggered
    override_reason: str = ""
    timestamp: str = ""                       # ISO format, Friday measurement time
    warnings: list[str] = field(default_factory=list)


class WeekendRiskScoreEngine:
    """
    Computes the Weekend Risk Score from pre-computed signal inputs.

    This engine does NOT fetch data or compute raw signals.
    It receives signal values and applies the scoring logic.
    Separation of concerns: data → signals → scoring → trading.
    """

    # Default weights — should be overridden by config/signals.yaml
    DEFAULT_CONFIG = {
        's1_friday_gold_momentum': {
            'max_score': 25,
            'lookback_days': 63,
            'threshold_multiplier': 2.0,  # |return| > 2x median
        },
        's2_friday_gold_volume': {
            'max_score': 15,
            'lookback_days': 21,
            'threshold_low': 1.0,
            'threshold_high': 2.0,
            'trigger_threshold': 1.3,
        },
        's3_vol_term_structure': {
            'max_score': 20,
            'lookback_days': 63,
            'inversion_threshold': -2.0,  # vol points
        },
        's4_gap_momentum': {
            'max_score': 15,
            'short_window': 4,   # weeks
            'long_window': 12,   # weeks
            'threshold_ratio': 1.5,
        },
        's5_cross_asset_stress': {
            'max_score': 15,
            'vix_change_threshold': 1.5,
            'dxy_change_threshold': 0.005,
            'ust_change_threshold': 0.05,  # 5bps
            'btc_change_threshold': 0.03,
        },
        'c1_silver_sympathy': {
            'bonus_score': 5,
            'penalty_score': -10,
            'corr_threshold_high': 0.7,
            'corr_threshold_low': 0.3,
            'move_ratio_range': (0.5, 2.0),
        },
        'c2_equity_preposition': {
            'bonus_score': 5,
            'threshold': -0.003,  # -0.3%
        },
        'nlp_narrative_pressure': {
            'max_score': 15,
        },
        'composite': {
            'cap': 100,
            'iv_override_threshold': 90,
            'iv_percentile_threshold': 90,
            'iv_override_size_reduction': 0.5,
        },
    }

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self.DEFAULT_CONFIG

    def score_s1_friday_gold_momentum(
        self,
        friday_return: float,
        median_abs_daily_return: float,
    ) -> SignalOutput:
        """
        S1: Friday Gold Momentum.
        Measures whether Friday's gold move is outsized relative to recent history.
        """
        cfg = self.config['s1_friday_gold_momentum']
        threshold = cfg['threshold_multiplier'] * median_abs_daily_return

        abs_return = abs(friday_return)
        triggered = abs_return > threshold

        if not triggered or median_abs_daily_return == 0:
            score = 0.0
        else:
            # Linear scaling: threshold → max at 4x median
            ratio = abs_return / median_abs_daily_return
            score = min(cfg['max_score'],
                       cfg['max_score'] * (ratio - cfg['threshold_multiplier']) /
                       (4.0 - cfg['threshold_multiplier']))
            score = max(0.0, score)

        return SignalOutput(
            name="S1_Friday_Gold_Momentum",
            raw_value=friday_return,
            score=score,
            max_score=cfg['max_score'],
            triggered=triggered,
            description=f"Friday return {friday_return:.4f} vs {cfg['threshold_multiplier']}x "
                       f"median {median_abs_daily_return:.4f} (threshold={threshold:.4f})",
        )

    def score_s2_friday_gold_volume(
        self,
        friday_volume: float,
        mean_weekday_volume: float,
    ) -> SignalOutput:
        """
        S2: Friday Gold Volume Anomaly.
        Elevated volume suggests institutional repositioning.
        """
        cfg = self.config['s2_friday_gold_volume']

        if mean_weekday_volume == 0:
            return SignalOutput(
                name="S2_Friday_Gold_Volume",
                raw_value=0, score=0, max_score=cfg['max_score'],
                triggered=False, description="No volume data", confidence=0.0,
            )

        vol_ratio = friday_volume / mean_weekday_volume
        triggered = vol_ratio > cfg['trigger_threshold']

        score = 0.0
        if triggered:
            # Linear from trigger to threshold_high
            score = cfg['max_score'] * min(1.0,
                (vol_ratio - cfg['threshold_low']) /
                (cfg['threshold_high'] - cfg['threshold_low']))
            score = max(0.0, score)

        return SignalOutput(
            name="S2_Friday_Gold_Volume",
            raw_value=vol_ratio,
            score=score,
            max_score=cfg['max_score'],
            triggered=triggered,
            description=f"Volume ratio {vol_ratio:.2f}x (trigger={cfg['trigger_threshold']})",
        )

    def score_s3_vol_term_structure(
        self,
        iv_1week: float,
        iv_1month: float,
        trailing_slope_percentile: float,  # Where current slope sits in 63-day dist (0-100)
    ) -> SignalOutput:
        """
        S3: Gold Vol Term Structure Inversion.
        Backwardation (short-dated > long-dated) suggests elevated near-term fear.
        """
        cfg = self.config['s3_vol_term_structure']
        slope = iv_1week - iv_1month
        triggered = slope < cfg['inversion_threshold']

        score = 0.0
        if triggered:
            # Scale by how extreme the inversion is relative to history
            score = cfg['max_score'] * min(1.0, trailing_slope_percentile / 100.0)

        return SignalOutput(
            name="S3_Vol_Term_Structure",
            raw_value=slope,
            score=score,
            max_score=cfg['max_score'],
            triggered=triggered,
            description=f"IV slope {slope:+.1f} vol pts (1W-1M). "
                       f"Percentile: {trailing_slope_percentile:.0f}th",
        )

    def score_s4_gap_momentum(
        self,
        trailing_4wk_gap_mean: float,
        trailing_12wk_gap_mean: float,
    ) -> SignalOutput:
        """
        S4: Weekend Gap Trailing Momentum.
        Are recent gaps getting larger?
        CAUTION: Very small sample. This is confirmatory only.
        """
        cfg = self.config['s4_gap_momentum']

        if trailing_12wk_gap_mean == 0:
            return SignalOutput(
                name="S4_Gap_Momentum",
                raw_value=0, score=0, max_score=cfg['max_score'],
                triggered=False, description="Insufficient gap history",
                confidence=0.3,
            )

        ratio = trailing_4wk_gap_mean / trailing_12wk_gap_mean
        triggered = ratio > cfg['threshold_ratio']

        score = 0.0
        if triggered:
            score = cfg['max_score'] * min(1.0,
                (ratio - cfg['threshold_ratio']) / (3.0 - cfg['threshold_ratio']))
            score = max(0.0, score)

        return SignalOutput(
            name="S4_Gap_Momentum",
            raw_value=ratio,
            score=score,
            max_score=cfg['max_score'],
            triggered=triggered,
            description=f"4wk/12wk gap ratio {ratio:.2f} (trigger={cfg['threshold_ratio']})",
            confidence=0.5,  # Always low confidence — small sample
        )

    def score_s5_cross_asset_stress(
        self,
        vix_change: float,         # VIX points change on Friday
        dxy_change_pct: float,     # DXY % change on Friday
        ust10y_change_bps: float,  # 10Y yield change in bps
        btc_change_pct: float,     # Bitcoin % change on Friday
    ) -> SignalOutput:
        """
        S5: Cross-Asset Friday Stress.
        Multiple assets showing stress simultaneously confirms macro event.
        """
        cfg = self.config['s5_cross_asset_stress']

        components = []
        score = 0.0

        if vix_change > cfg['vix_change_threshold']:
            score += 5
            components.append(f"VIX +{vix_change:.1f}")

        if dxy_change_pct > cfg['dxy_change_threshold']:
            score += 3
            components.append(f"DXY +{dxy_change_pct*100:.2f}%")

        if abs(ust10y_change_bps) > cfg['ust_change_threshold'] * 100:
            score += 2
            components.append(f"10Y {ust10y_change_bps:+.0f}bps")

        if abs(btc_change_pct) > cfg['btc_change_threshold']:
            score += 5
            components.append(f"BTC {btc_change_pct*100:+.1f}%")

        score = min(cfg['max_score'], score)
        triggered = score > 0

        return SignalOutput(
            name="S5_Cross_Asset_Stress",
            raw_value=score,
            score=score,
            max_score=cfg['max_score'],
            triggered=triggered,
            description=f"Triggered: {', '.join(components) if components else 'None'}",
        )

    def score_c1_silver_sympathy(
        self,
        intraday_correlation: float,   # Gold-silver 1min return correlation on Friday
        silver_gold_move_ratio: float,  # |SI_return| / |GC_return|
    ) -> SignalOutput:
        """
        C1: Silver Sympathy Score.
        Confirmation when silver moves with gold. Penalty when it diverges.
        """
        cfg = self.config['c1_silver_sympathy']
        lo, hi = cfg['move_ratio_range']

        if (intraday_correlation > cfg['corr_threshold_high'] and
                lo <= silver_gold_move_ratio <= hi):
            score = cfg['bonus_score']
            triggered = True
            desc = f"Silver confirms: corr={intraday_correlation:.2f}, ratio={silver_gold_move_ratio:.2f}"
        elif intraday_correlation < cfg['corr_threshold_low']:
            score = cfg['penalty_score']  # Negative!
            triggered = True
            desc = f"Silver DIVERGES: corr={intraday_correlation:.2f} — possible false signal"
        else:
            score = 0.0
            triggered = False
            desc = f"Silver neutral: corr={intraday_correlation:.2f}, ratio={silver_gold_move_ratio:.2f}"

        return SignalOutput(
            name="C1_Silver_Sympathy",
            raw_value=intraday_correlation,
            score=score,
            max_score=cfg['bonus_score'],
            triggered=triggered,
            description=desc,
        )

    def score_c2_equity_preposition(
        self,
        sp500_friday_pm_return: float,  # ES1 return from 2PM-4PM ET
    ) -> SignalOutput:
        """
        C2: Equity Pre-Positioning.
        Equities selling into Friday close confirms risk-off.
        """
        cfg = self.config['c2_equity_preposition']
        triggered = sp500_friday_pm_return < cfg['threshold']
        score = cfg['bonus_score'] if triggered else 0.0

        return SignalOutput(
            name="C2_Equity_PrePosition",
            raw_value=sp500_friday_pm_return,
            score=score,
            max_score=cfg['bonus_score'],
            triggered=triggered,
            description=f"SPX PM return {sp500_friday_pm_return*100:.2f}% "
                       f"(trigger={cfg['threshold']*100:.1f}%)",
        )

    def compute_wrs(
        self,
        # Primary signals
        friday_gold_return: float,
        median_abs_daily_return: float,
        friday_gold_volume: float,
        mean_weekday_gold_volume: float,
        gold_iv_1week: float,
        gold_iv_1month: float,
        vol_slope_percentile: float,
        trailing_4wk_gap_mean: float,
        trailing_12wk_gap_mean: float,
        vix_change: float,
        dxy_change_pct: float,
        ust10y_change_bps: float,
        btc_change_pct: float,
        # Confirmation
        gold_silver_intraday_corr: float,
        silver_gold_move_ratio: float,
        sp500_friday_pm_return: float,
        # NLP (pre-computed)
        narrative_pressure_score: float,  # 0-15
        # Regime
        regime_state: RegimeState = RegimeState.ACTIVE,
        # Override check
        friday_gold_iv_percentile: float = 50.0,  # Current IV vs 63-day percentile
        # Metadata
        timestamp: str = "",
    ) -> WeekendRiskScore:
        """
        Master scoring function. Computes WRS from all inputs.

        Returns WeekendRiskScore with full attribution and trade recommendation.
        """
        warnings = []

        # Check regime first
        if regime_state in (RegimeState.DORMANT, RegimeState.KILLED):
            return WeekendRiskScore(
                composite_score=0,
                signal_outputs=[],
                regime_state=regime_state,
                trade_recommendation="NO_TRADE",
                timestamp=timestamp,
                warnings=[f"System in {regime_state.value} state. No trading."],
            )

        # Compute all signals
        s1 = self.score_s1_friday_gold_momentum(friday_gold_return, median_abs_daily_return)
        s2 = self.score_s2_friday_gold_volume(friday_gold_volume, mean_weekday_gold_volume)
        s3 = self.score_s3_vol_term_structure(gold_iv_1week, gold_iv_1month, vol_slope_percentile)
        s4 = self.score_s4_gap_momentum(trailing_4wk_gap_mean, trailing_12wk_gap_mean)
        s5 = self.score_s5_cross_asset_stress(vix_change, dxy_change_pct, ust10y_change_bps, btc_change_pct)
        c1 = self.score_c1_silver_sympathy(gold_silver_intraday_corr, silver_gold_move_ratio)
        c2 = self.score_c2_equity_preposition(sp500_friday_pm_return)

        all_signals = [s1, s2, s3, s4, s5, c1, c2]

        # Composite score
        raw_score = sum(s.score for s in all_signals) + min(15, narrative_pressure_score)

        # Cap
        cfg = self.config['composite']
        composite = max(0, min(cfg['cap'], raw_score))

        # IV override check for WRS > 90
        override_active = False
        override_reason = ""
        if (composite > cfg['iv_override_threshold'] and
                friday_gold_iv_percentile > cfg['iv_percentile_threshold']):
            override_active = True
            override_reason = (
                f"WRS={composite:.0f} but Friday gold IV at {friday_gold_iv_percentile:.0f}th "
                f"percentile. Weekend risk may already be priced. Size reduced "
                f"{cfg['iv_override_size_reduction']*100:.0f}%."
            )
            warnings.append(override_reason)

        # Low confidence warnings
        low_conf_signals = [s for s in all_signals if s.confidence < 0.8]
        if low_conf_signals:
            warnings.append(
                f"Low confidence signals: {', '.join(s.name for s in low_conf_signals)}. "
                f"Score may be less reliable."
            )

        # Trade recommendation
        if regime_state == RegimeState.MONITORING:
            if composite > 60:
                recommendation = "SMALL"
                warnings.append("Regime in MONITORING state — position capped at SMALL.")
            else:
                recommendation = "MONITOR"
        elif composite <= 20:
            recommendation = "NO_TRADE"
        elif composite <= 40:
            recommendation = "MONITOR"
        elif composite <= 60:
            recommendation = "SMALL"
        elif composite <= 80:
            recommendation = "STANDARD"
        else:
            recommendation = "MAXIMUM"

        return WeekendRiskScore(
            composite_score=composite,
            signal_outputs=all_signals,
            regime_state=regime_state,
            trade_recommendation=recommendation,
            override_active=override_active,
            override_reason=override_reason,
            timestamp=timestamp,
            warnings=warnings,
        )

    def format_report(self, wrs: WeekendRiskScore) -> str:
        """Human-readable WRS report for Friday afternoon review."""
        lines = [
            "=" * 70,
            f"  AURUM WEEKEND RISK SCORE — {wrs.timestamp or 'N/A'}",
            "=" * 70,
            "",
            f"  COMPOSITE SCORE:  {wrs.composite_score:.0f} / 100",
            f"  RECOMMENDATION:   {wrs.trade_recommendation}",
            f"  REGIME STATE:     {wrs.regime_state.value.upper()}",
            "",
        ]

        if wrs.override_active:
            lines.append(f"  ⚠️  OVERRIDE: {wrs.override_reason}")
            lines.append("")

        lines.append("  SIGNAL BREAKDOWN:")
        lines.append("  " + "-" * 66)

        for s in wrs.signal_outputs:
            flag = "✓" if s.triggered else "○"
            conf = f" [conf={s.confidence:.0%}]" if s.confidence < 1.0 else ""
            lines.append(
                f"  {flag} {s.name:<30} {s.score:>6.1f} / {s.max_score:>5.1f}{conf}"
            )
            lines.append(f"    {s.description}")

        if wrs.warnings:
            lines.append("")
            lines.append("  WARNINGS:")
            for w in wrs.warnings:
                lines.append(f"    ⚠ {w}")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# --- Example usage / smoke test ---
if __name__ == "__main__":
    engine = WeekendRiskScoreEngine()

    # Simulate a moderately stressed Friday
    result = engine.compute_wrs(
        friday_gold_return=0.018,           # +1.8% Friday (elevated)
        median_abs_daily_return=0.007,      # Typical daily |return| ~0.7%
        friday_gold_volume=280000,          # Elevated volume
        mean_weekday_gold_volume=200000,
        gold_iv_1week=22.0,                 # Short-dated IV elevated
        gold_iv_1month=18.0,               # Monthly IV lower
        vol_slope_percentile=85.0,          # 85th percentile inversion
        trailing_4wk_gap_mean=0.012,        # Recent gaps ~1.2%
        trailing_12wk_gap_mean=0.006,       # Longer-term gaps ~0.6%
        vix_change=2.1,                     # VIX up 2.1 points
        dxy_change_pct=0.003,               # DXY +0.3%
        ust10y_change_bps=3.0,              # 10Y +3bps
        btc_change_pct=-0.04,              # BTC -4%
        gold_silver_intraday_corr=0.75,     # Silver confirms
        silver_gold_move_ratio=0.8,
        sp500_friday_pm_return=-0.004,      # SPX selling into close
        narrative_pressure_score=8.0,       # Moderate headline pressure
        regime_state=RegimeState.ACTIVE,
        friday_gold_iv_percentile=65.0,     # IV not extremely elevated
        timestamp="2025-02-14T15:00:00-05:00",
    )

    print(engine.format_report(result))
