"""
AURUM Metals Stack — Dispersion & Relative Strength Engine
============================================================
Computes cross-metal dispersion, gold leadership, stack breadth, and
industrial-monetary divergence for regime classification.

These metrics feed into the MSIL Regime Classifier and produce the
Stack Regime Adjustment (SRA) that modifies the Weekend Risk Score.

All metrics are designed to be:
  - Independently testable (each has a null hypothesis)
  - Computed from daily closing prices only (no intraday required)
  - Interpretable without black-box transformation
"""

from dataclasses import dataclass
from typing import Optional
import math


# --- Constants ---

# Futures stack: the core metals for dispersion calculation
FUTURES_STACK = ["GC1", "SI1", "HG1", "ALI", "PL1", "PA1"]

# Monetary metals: gold, silver
MONETARY_METALS = ["GC1", "SI1"]

# Industrial metals: copper, aluminum, platinum, palladium
INDUSTRIAL_METALS = ["HG1", "ALI", "PL1", "PA1"]

# Full equity/ETF universe for breadth calculation
EQUITY_UNIVERSE = [
    "GDX", "COPX", "URA", "LIT", "MP", "FCX", "RIO", "NEM", "AEM", "GOLD"
]

# Combined universe for breadth
FULL_UNIVERSE = FUTURES_STACK + EQUITY_UNIVERSE


@dataclass
class MDIOutput:
    """Metals Dispersion Index output."""
    raw_dispersion: float         # Cross-sectional std of returns
    percentile_score: float       # 0-100 percentile rank
    lookback_days: int
    interpretation: str
    individual_returns: dict[str, float]  # Per-metal trailing returns


@dataclass
class GLSOutput:
    """Gold Leadership Score output."""
    rank_score: float             # -2 to +2 (gold rank in stack)
    lead_lag_score: float         # -1 to +2 (cross-correlation)
    beta_score: float             # -2 to +2 (gold-equity beta)
    composite: float              # -100 to +100 (normalized)
    gold_rank: int                # 1-based rank in stack
    optimal_lag: int              # Lead-lag in days
    gold_equity_beta: float       # Raw beta value
    interpretation: str


@dataclass
class SMBOutput:
    """Stack Momentum Breadth output."""
    pct_above_20d_high: float     # 0-1
    pct_above_50d_ma: float       # 0-1
    industrial_precious_divergence: float  # % return difference
    breadth_score: float          # 0-100
    interpretation: str


@dataclass
class IMDIOutput:
    """Industrial-Monetary Divergence Index output."""
    raw_divergence: float         # Monetary - Industrial return
    z_score: float                # Normalized
    monetary_return: float        # Mean return of monetary metals
    industrial_return: float      # Mean return of industrial metals
    interpretation: str


class DispersionEngine:
    """
    Computes all metals stack metrics from daily return data.

    Inputs are pre-computed daily returns (the data layer's job).
    This engine applies the metric formulas only.
    """

    def __init__(self, lookback: int = 21, long_lookback: int = 252):
        self.lookback = lookback
        self.long_lookback = long_lookback

    @staticmethod
    def _cross_sectional_std(values: list[float]) -> float:
        """Standard deviation across a list of values (population)."""
        if len(values) < 2:
            return 0.0
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _percentile_rank(value: float, distribution: list[float]) -> float:
        """Compute percentile rank of value within distribution (0-100)."""
        if not distribution:
            return 50.0
        count_below = sum(1 for v in distribution if v < value)
        return (count_below / len(distribution)) * 100

    @staticmethod
    def _z_score(value: float, distribution: list[float]) -> float:
        """Z-score of value against distribution."""
        if len(distribution) < 2:
            return 0.0
        mean_val = sum(distribution) / len(distribution)
        std_val = math.sqrt(sum((v - mean_val) ** 2 for v in distribution) / len(distribution))
        if std_val == 0:
            return 0.0
        return (value - mean_val) / std_val

    # === MDI ===

    def compute_mdi(
        self,
        trailing_returns: dict[str, float],
        historical_dispersions: list[float],
    ) -> MDIOutput:
        """
        Metals Dispersion Index.

        Args:
            trailing_returns: {ticker: cumulative_return_over_lookback}
                              for futures stack only
            historical_dispersions: trailing 252 daily dispersion values
                                    for percentile ranking

        Returns:
            MDIOutput with percentile score 0-100
        """
        # Filter to futures stack only
        stack_returns = {k: v for k, v in trailing_returns.items() if k in FUTURES_STACK}

        if len(stack_returns) < 3:
            return MDIOutput(
                raw_dispersion=0.0,
                percentile_score=50.0,
                lookback_days=self.lookback,
                interpretation="Insufficient data for MDI computation",
                individual_returns=stack_returns,
            )

        raw = self._cross_sectional_std(list(stack_returns.values()))
        percentile = self._percentile_rank(raw, historical_dispersions)

        if percentile < 25:
            interp = "Low dispersion — metals moving together (macro-driven)"
        elif percentile < 50:
            interp = "Normal dispersion — no strong signal"
        elif percentile < 75:
            interp = "Elevated dispersion — rotation or thematic activity"
        else:
            interp = "Extreme dispersion — metals decoupled, potential noise"

        return MDIOutput(
            raw_dispersion=raw,
            percentile_score=percentile,
            lookback_days=self.lookback,
            interpretation=interp,
            individual_returns=stack_returns,
        )

    # === GLS ===

    def compute_gls(
        self,
        stack_trailing_returns: dict[str, float],
        gold_lead_lag_corrs: dict[int, float],
        gold_equity_beta: float,
    ) -> GLSOutput:
        """
        Gold Leadership Score.

        Args:
            stack_trailing_returns: {ticker: trailing_return} for futures stack
            gold_lead_lag_corrs: {lag_days: correlation}
                                 e.g., {-5: 0.1, ..., 0: 0.5, ..., +5: 0.7}
                                 Positive lag = gold leads
            gold_equity_beta: Rolling beta of GC1 to ES1 (21-day)

        Returns:
            GLSOutput with composite score -100 to +100
        """
        # Component 1: Gold Return Rank
        sorted_returns = sorted(stack_trailing_returns.items(), key=lambda x: x[1], reverse=True)
        gold_rank = next((i + 1 for i, (k, _) in enumerate(sorted_returns) if k == "GC1"), len(sorted_returns))
        n_metals = len(sorted_returns)

        if n_metals == 0:
            rank_score = 0.0
        elif gold_rank == 1:
            rank_score = 2.0
        elif gold_rank == 2:
            rank_score = 1.0
        elif gold_rank >= n_metals - 1:
            rank_score = -2.0
        else:
            rank_score = 0.0

        # Component 2: Lead-Lag
        if gold_lead_lag_corrs:
            optimal_lag = max(gold_lead_lag_corrs, key=gold_lead_lag_corrs.get)
            if optimal_lag > 0:
                lead_lag_score = 2.0
            elif optimal_lag < 0:
                lead_lag_score = -1.0
            else:
                lead_lag_score = 0.0
        else:
            optimal_lag = 0
            lead_lag_score = 0.0

        # Component 3: Gold-Equity Beta
        if gold_equity_beta < -0.2:
            beta_score = 2.0  # True haven behavior
        elif gold_equity_beta > 0.2:
            beta_score = -2.0  # Risk-on, not haven
        else:
            beta_score = 0.0

        # Composite: raw range -5 to +6, normalize to -100 to +100
        raw_composite = rank_score + lead_lag_score + beta_score
        composite = (raw_composite / 6.0) * 100.0  # Scale to -100 to +100

        if composite > 50:
            interp = "Gold leading with haven characteristics — WMCE relevance HIGH"
        elif composite > 0:
            interp = "Gold moderately leading — WMCE relevance NEUTRAL"
        elif composite > -50:
            interp = "Gold lagging stack — WMCE relevance REDUCED"
        else:
            interp = "Gold is a laggard — WMCE relevance LOW"

        return GLSOutput(
            rank_score=rank_score,
            lead_lag_score=lead_lag_score,
            beta_score=beta_score,
            composite=composite,
            gold_rank=gold_rank,
            optimal_lag=optimal_lag,
            gold_equity_beta=gold_equity_beta,
            interpretation=interp,
        )

    # === SMB ===

    def compute_smb(
        self,
        prices_at_20d_high: dict[str, bool],
        prices_above_50d_ma: dict[str, bool],
        industrial_21d_return: float,
        precious_21d_return: float,
    ) -> SMBOutput:
        """
        Stack Momentum Breadth.

        Args:
            prices_at_20d_high: {ticker: True/False} for full universe
            prices_above_50d_ma: {ticker: True/False} for full universe
            industrial_21d_return: Mean 21d return of industrial metals + miners
            precious_21d_return: Mean 21d return of precious metals + miners
        """
        total_instruments = max(len(prices_at_20d_high), 1)
        pct_20d = sum(1 for v in prices_at_20d_high.values() if v) / total_instruments
        pct_50d = sum(1 for v in prices_above_50d_ma.values() if v) / total_instruments
        divergence = industrial_21d_return - precious_21d_return

        # Breadth score: weighted combination
        breadth = (pct_50d * 50) + (pct_20d * 30)
        if divergence < -0.02:  # Industrial lagging precious by >2%
            breadth += 20  # This means precious are strong = macro stress

        breadth = max(0.0, min(100.0, breadth))

        if breadth > 70:
            interp = "Broad metals strength — risk-on environment"
        elif breadth > 30:
            interp = "Mixed breadth — normal conditions"
        else:
            interp = "Narrow/weak breadth — potential stress or broad selloff"

        return SMBOutput(
            pct_above_20d_high=pct_20d,
            pct_above_50d_ma=pct_50d,
            industrial_precious_divergence=divergence,
            breadth_score=breadth,
            interpretation=interp,
        )

    # === IMDI ===

    def compute_imdi(
        self,
        monetary_mean_return: float,
        industrial_mean_return: float,
        historical_divergences: list[float],
    ) -> IMDIOutput:
        """
        Industrial-Monetary Divergence Index.

        Args:
            monetary_mean_return: Mean trailing return of GC1, SI1
            industrial_mean_return: Mean trailing return of HG1, ALI, PL1
            historical_divergences: Trailing 252 daily divergence values
        """
        raw = monetary_mean_return - industrial_mean_return
        z = self._z_score(raw, historical_divergences)

        if z > 1.5:
            interp = "Strong monetary outperformance — macro stress or debasement fear"
        elif z > 0.5:
            interp = "Moderate monetary outperformance — mild haven bid"
        elif z > -0.5:
            interp = "No clear divergence — balanced regime"
        elif z > -1.5:
            interp = "Moderate industrial outperformance — growth/capex cycle"
        else:
            interp = "Strong industrial outperformance — cyclical expansion"

        return IMDIOutput(
            raw_divergence=raw,
            z_score=z,
            monetary_return=monetary_mean_return,
            industrial_return=industrial_mean_return,
            interpretation=interp,
        )


# === Comprehensive Report ===

def format_dispersion_report(
    mdi: MDIOutput,
    gls: GLSOutput,
    smb: SMBOutput,
    imdi: IMDIOutput,
    timestamp: str = "",
) -> str:
    """Human-readable metals stack report."""
    lines = [
        "=" * 70,
        f"  AURUM METALS STACK REPORT — {timestamp or 'N/A'}",
        "=" * 70,
        "",
        "  METALS DISPERSION INDEX (MDI)",
        f"    Raw Dispersion:  {mdi.raw_dispersion:.4f}",
        f"    Percentile:      {mdi.percentile_score:.0f} / 100",
        f"    Interpretation:  {mdi.interpretation}",
        f"    Individual Returns ({mdi.lookback_days}d):",
    ]
    for ticker, ret in sorted(mdi.individual_returns.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"      {ticker:<6} {ret:>+8.2%}")

    lines.extend([
        "",
        "  GOLD LEADERSHIP SCORE (GLS)",
        f"    Composite:       {gls.composite:>+.0f} / 100",
        f"    Gold Rank:       {gls.gold_rank} in stack",
        f"    Optimal Lag:     {gls.optimal_lag:+d} days ({'gold leads' if gls.optimal_lag > 0 else 'gold lags' if gls.optimal_lag < 0 else 'simultaneous'})",
        f"    Gold-Equity β:   {gls.gold_equity_beta:+.2f}",
        f"    Components:      Rank={gls.rank_score:+.0f}  Lead/Lag={gls.lead_lag_score:+.0f}  Beta={gls.beta_score:+.0f}",
        f"    Interpretation:  {gls.interpretation}",
        "",
        "  STACK MOMENTUM BREADTH (SMB)",
        f"    Above 20d High:  {smb.pct_above_20d_high:.0%}",
        f"    Above 50d MA:    {smb.pct_above_50d_ma:.0%}",
        f"    Ind-Prec Spread: {smb.industrial_precious_divergence:>+.2%}",
        f"    Breadth Score:   {smb.breadth_score:.0f} / 100",
        f"    Interpretation:  {smb.interpretation}",
        "",
        "  INDUSTRIAL-MONETARY DIVERGENCE (IMDI)",
        f"    Raw Divergence:  {imdi.raw_divergence:>+.4f}",
        f"    Z-Score:         {imdi.z_score:>+.2f}",
        f"    Monetary Return: {imdi.monetary_return:>+.2%}",
        f"    Industrial Ret:  {imdi.industrial_return:>+.2%}",
        f"    Interpretation:  {imdi.interpretation}",
        "",
        "=" * 70,
    ])
    return "\n".join(lines)


# === Smoke Test ===

if __name__ == "__main__":
    engine = DispersionEngine(lookback=21, long_lookback=252)

    # Simulate a macro stress scenario
    trailing_returns = {
        "GC1": 0.045,    # Gold up 4.5% (leading)
        "SI1": 0.025,    # Silver up 2.5%
        "HG1": -0.015,   # Copper down 1.5%
        "ALI": -0.020,   # Aluminum down 2%
        "PL1": 0.005,    # Platinum flat
        "PA1": -0.010,   # Palladium down 1%
    }

    # Historical dispersions for percentile ranking
    import random
    random.seed(42)
    hist_dispersions = [random.gauss(0.02, 0.01) for _ in range(252)]

    mdi = engine.compute_mdi(trailing_returns, hist_dispersions)

    gls = engine.compute_gls(
        stack_trailing_returns=trailing_returns,
        gold_lead_lag_corrs={-5: 0.1, -3: 0.15, -1: 0.2, 0: 0.35, 1: 0.5, 3: 0.6, 5: 0.55},
        gold_equity_beta=-0.3,
    )

    smb = engine.compute_smb(
        prices_at_20d_high={"GC1": True, "SI1": False, "HG1": False, "ALI": False, "PL1": False,
                            "PA1": False, "GDX": True, "COPX": False, "URA": False, "NEM": True},
        prices_above_50d_ma={"GC1": True, "SI1": True, "HG1": False, "ALI": False, "PL1": True,
                              "PA1": False, "GDX": True, "COPX": False, "URA": True, "NEM": True},
        industrial_21d_return=-0.012,
        precious_21d_return=0.035,
    )

    imdi = engine.compute_imdi(
        monetary_mean_return=0.035,
        industrial_mean_return=-0.010,
        historical_divergences=[random.gauss(0.005, 0.025) for _ in range(252)],
    )

    print(format_dispersion_report(mdi, gls, smb, imdi, "2026-02-14"))
