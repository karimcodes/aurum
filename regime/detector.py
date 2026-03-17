"""
AURUM Regime Detection Layer
==============================
Determines whether the weekend gap edge is active, degrading, or dead.

The regime filter is the MASTER SWITCH. It can turn the entire system off.
This is the most important risk management component.

State machine:
  ACTIVE → MONITORING → DORMANT → KILLED
  Recovery paths exist for all states except KILLED (requires manual override).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import json


class RegimeState(Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    DORMANT = "dormant"
    KILLED = "killed"


@dataclass
class RegimeSignal:
    """Individual regime-level signal."""
    name: str
    triggered: bool
    value: float
    threshold: float
    consecutive_weeks: int
    required_weeks: int
    description: str


@dataclass
class RegimeAssessment:
    """Complete regime assessment output."""
    state: RegimeState
    previous_state: RegimeState
    signals: list[RegimeSignal]
    triggered_count: int
    transition_reason: str
    timestamp: str
    manual_override: bool = False


class RegimeDetector:
    """
    Monitors structural health of the weekend gap edge.

    Called once per week (Sunday night or Monday morning) with updated data.
    Maintains state across calls via a simple JSON persistence layer.
    """

    DEFAULT_CONFIG = {
        'gap_magnitude_trend': {
            'lookback_weeks': 8,
            'ratio_threshold': 1.2,     # Weekend gap / avg overnight gap
            'weeks_below_to_trigger': 4,
        },
        'gold_vol_regime': {
            'lookback_days': 252,
            'percentile_threshold': 20,  # Below 20th → low vol regime
        },
        'vix_regime': {
            'level_threshold': 14,
            'weeks_below_to_trigger': 4,
        },
        'edge_profitability': {
            'lookback_weeks': 12,
            'drawdown_threshold': -0.15,  # -15% of allocated capital
        },
        'options_pricing_adaptation': {
            'iv_rv_ratio_threshold': 1.3,  # If IV/RV > 1.3, edge is priced out
            'weeks_above_to_trigger': 4,
        },
        'recovery': {
            'weeks_clear_for_active': 2,   # All signals must be clear for 2 weeks
        },
    }

    def __init__(self, config: Optional[dict] = None, state_file: Optional[str] = None):
        self.config = config or self.DEFAULT_CONFIG
        self.state_file = state_file
        self.current_state = RegimeState.ACTIVE
        self.previous_state = RegimeState.ACTIVE
        self.consecutive_clear_weeks = 0

        # Track consecutive weeks for each signal
        self._signal_streak = {
            'gap_magnitude_trend': 0,
            'vix_regime': 0,
            'options_pricing_adaptation': 0,
        }

        if state_file:
            self._load_state()

    def _load_state(self):
        """Load persisted state."""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.current_state = RegimeState(data.get('state', 'active'))
                self.previous_state = RegimeState(data.get('previous_state', 'active'))
                self.consecutive_clear_weeks = data.get('consecutive_clear_weeks', 0)
                self._signal_streak = data.get('signal_streak', self._signal_streak)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        """Persist state."""
        if not self.state_file:
            return
        data = {
            'state': self.current_state.value,
            'previous_state': self.previous_state.value,
            'consecutive_clear_weeks': self.consecutive_clear_weeks,
            'signal_streak': self._signal_streak,
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def assess(
        self,
        # Gap trend data
        weekend_gap_magnitudes_8wk: list[float],   # Last 8 weekend |gaps|
        avg_overnight_gap: float,                    # Mean |overnight gap| (non-weekend)
        # Vol regime
        gold_rv_21d_percentile: float,               # Current 21d RV percentile (0-100)
        # VIX
        vix_level: float,
        # Profitability
        rolling_12wk_pnl_pct: float,                 # Strategy P&L as % of allocated capital
        # Options pricing
        trailing_iv_rv_ratios: list[float],           # Last 4-8 weeks of Friday IV / Monday RV
        # Metadata
        timestamp: str = "",
    ) -> RegimeAssessment:
        """
        Run weekly regime assessment.

        Returns RegimeAssessment with new state and full signal breakdown.
        """
        signals = []

        # 1. Gap magnitude trend
        cfg = self.config['gap_magnitude_trend']
        if weekend_gap_magnitudes_8wk and avg_overnight_gap > 0:
            gap_ratio = (sum(weekend_gap_magnitudes_8wk) / len(weekend_gap_magnitudes_8wk)) / avg_overnight_gap
            gap_below = gap_ratio < cfg['ratio_threshold']
            if gap_below:
                self._signal_streak['gap_magnitude_trend'] += 1
            else:
                self._signal_streak['gap_magnitude_trend'] = 0
            triggered = self._signal_streak['gap_magnitude_trend'] >= cfg['weeks_below_to_trigger']
        else:
            gap_ratio = 0
            triggered = False
            gap_below = False

        signals.append(RegimeSignal(
            name="Gap Magnitude Trend",
            triggered=triggered,
            value=gap_ratio,
            threshold=cfg['ratio_threshold'],
            consecutive_weeks=self._signal_streak['gap_magnitude_trend'],
            required_weeks=cfg['weeks_below_to_trigger'],
            description=f"Weekend/overnight gap ratio: {gap_ratio:.2f} (need >{cfg['ratio_threshold']})",
        ))

        # 2. Gold vol regime
        cfg = self.config['gold_vol_regime']
        low_vol = gold_rv_21d_percentile < cfg['percentile_threshold']
        signals.append(RegimeSignal(
            name="Gold Vol Regime",
            triggered=low_vol,
            value=gold_rv_21d_percentile,
            threshold=cfg['percentile_threshold'],
            consecutive_weeks=0,  # Immediate trigger
            required_weeks=0,
            description=f"Gold 21d RV at {gold_rv_21d_percentile:.0f}th percentile (need >{cfg['percentile_threshold']}th)",
        ))

        # 3. VIX regime
        cfg = self.config['vix_regime']
        vix_low = vix_level < cfg['level_threshold']
        if vix_low:
            self._signal_streak['vix_regime'] += 1
        else:
            self._signal_streak['vix_regime'] = 0
        vix_triggered = self._signal_streak['vix_regime'] >= cfg['weeks_below_to_trigger']
        signals.append(RegimeSignal(
            name="VIX Regime",
            triggered=vix_triggered,
            value=vix_level,
            threshold=cfg['level_threshold'],
            consecutive_weeks=self._signal_streak['vix_regime'],
            required_weeks=cfg['weeks_below_to_trigger'],
            description=f"VIX at {vix_level:.1f} (need >{cfg['level_threshold']})",
        ))

        # 4. Edge profitability (HARD STOP)
        cfg = self.config['edge_profitability']
        drawdown_exceeded = rolling_12wk_pnl_pct < cfg['drawdown_threshold']
        signals.append(RegimeSignal(
            name="Edge Profitability",
            triggered=drawdown_exceeded,
            value=rolling_12wk_pnl_pct,
            threshold=cfg['drawdown_threshold'],
            consecutive_weeks=0,  # Immediate
            required_weeks=0,
            description=f"12wk P&L: {rolling_12wk_pnl_pct:+.1%} (kill at {cfg['drawdown_threshold']:.0%})",
        ))

        # 5. Options pricing adaptation
        cfg = self.config['options_pricing_adaptation']
        if trailing_iv_rv_ratios:
            recent_ratio = sum(trailing_iv_rv_ratios[-4:]) / len(trailing_iv_rv_ratios[-4:])
            priced_out = recent_ratio > cfg['iv_rv_ratio_threshold']
            if priced_out:
                self._signal_streak['options_pricing_adaptation'] += 1
            else:
                self._signal_streak['options_pricing_adaptation'] = 0
            adapt_triggered = self._signal_streak['options_pricing_adaptation'] >= cfg['weeks_above_to_trigger']
        else:
            recent_ratio = 0
            adapt_triggered = False

        signals.append(RegimeSignal(
            name="Options Pricing Adaptation",
            triggered=adapt_triggered,
            value=recent_ratio,
            threshold=cfg['iv_rv_ratio_threshold'],
            consecutive_weeks=self._signal_streak['options_pricing_adaptation'],
            required_weeks=cfg['weeks_above_to_trigger'],
            description=f"Avg IV/RV ratio: {recent_ratio:.2f} (edge priced out >{cfg['iv_rv_ratio_threshold']})",
        ))

        # --- State Transition Logic ---
        triggered_count = sum(1 for s in signals if s.triggered)
        self.previous_state = self.current_state
        transition_reason = ""

        # KILLED is a hard stop — only manual override recovers
        if drawdown_exceeded:
            self.current_state = RegimeState.KILLED
            self.consecutive_clear_weeks = 0
            transition_reason = (
                f"KILLED: 12-week drawdown {rolling_12wk_pnl_pct:+.1%} "
                f"exceeds {cfg['drawdown_threshold']:.0%} threshold. Manual override required."
            )

        elif self.current_state == RegimeState.KILLED:
            transition_reason = "Remains KILLED. Manual override required to resume."

        elif triggered_count >= 2:
            self.current_state = RegimeState.DORMANT
            self.consecutive_clear_weeks = 0
            triggered_names = [s.name for s in signals if s.triggered]
            transition_reason = f"DORMANT: {triggered_count} signals triggered ({', '.join(triggered_names)})"

        elif triggered_count == 1:
            if self.current_state == RegimeState.ACTIVE:
                self.current_state = RegimeState.MONITORING
                self.consecutive_clear_weeks = 0
                triggered_name = next(s.name for s in signals if s.triggered)
                transition_reason = f"MONITORING: {triggered_name} triggered"
            elif self.current_state == RegimeState.DORMANT:
                # Stay dormant until fully clear
                transition_reason = f"Remains DORMANT: {triggered_count} signal still active"
            else:
                transition_reason = f"Remains {self.current_state.value}: {triggered_count} signal active"

        elif triggered_count == 0:
            self.consecutive_clear_weeks += 1
            recovery_weeks = self.config['recovery']['weeks_clear_for_active']

            if self.current_state in (RegimeState.MONITORING, RegimeState.DORMANT):
                if self.consecutive_clear_weeks >= recovery_weeks:
                    self.current_state = RegimeState.ACTIVE
                    transition_reason = (
                        f"ACTIVE: All signals clear for {self.consecutive_clear_weeks} "
                        f"consecutive weeks (required: {recovery_weeks})"
                    )
                else:
                    transition_reason = (
                        f"Remains {self.current_state.value}: "
                        f"{self.consecutive_clear_weeks}/{recovery_weeks} clear weeks for recovery"
                    )
            else:
                transition_reason = f"ACTIVE: All signals clear"

        assessment = RegimeAssessment(
            state=self.current_state,
            previous_state=self.previous_state,
            signals=signals,
            triggered_count=triggered_count,
            transition_reason=transition_reason,
            timestamp=timestamp,
        )

        self._save_state()
        return assessment

    def manual_override(self, target_state: RegimeState, reason: str) -> RegimeAssessment:
        """
        Manual override — for KILLED recovery only.
        Requires explicit justification.
        """
        self.previous_state = self.current_state
        self.current_state = target_state
        self.consecutive_clear_weeks = 0
        self._save_state()

        return RegimeAssessment(
            state=self.current_state,
            previous_state=self.previous_state,
            signals=[],
            triggered_count=0,
            transition_reason=f"MANUAL OVERRIDE to {target_state.value}: {reason}",
            timestamp=datetime.utcnow().isoformat(),
            manual_override=True,
        )

    def format_assessment(self, assessment: RegimeAssessment) -> str:
        """Human-readable regime report."""
        lines = [
            "=" * 60,
            "  AURUM REGIME ASSESSMENT",
            "=" * 60,
            f"  State:     {assessment.state.value.upper()}",
            f"  Previous:  {assessment.previous_state.value.upper()}",
            f"  Signals Triggered: {assessment.triggered_count} / {len(assessment.signals)}",
            f"  Transition: {assessment.transition_reason}",
            "",
        ]

        for s in assessment.signals:
            status = "🔴 TRIGGERED" if s.triggered else "🟢 OK"
            lines.append(f"  {status}  {s.name}")
            lines.append(f"           {s.description}")
            if s.required_weeks > 0:
                lines.append(f"           Streak: {s.consecutive_weeks}/{s.required_weeks} weeks")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    detector = RegimeDetector()

    # Simulate a healthy regime
    assessment = detector.assess(
        weekend_gap_magnitudes_8wk=[0.012, 0.008, 0.015, 0.010, 0.013, 0.009, 0.011, 0.014],
        avg_overnight_gap=0.005,
        gold_rv_21d_percentile=55.0,
        vix_level=22.0,
        rolling_12wk_pnl_pct=0.03,    # +3% over 12 weeks
        trailing_iv_rv_ratios=[0.9, 1.0, 0.85, 1.1],
        timestamp="2025-02-16T08:00:00Z",
    )

    print(detector.format_assessment(assessment))
