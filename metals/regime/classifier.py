"""
AURUM MSIL Regime Classifier
==============================
Classifies the current metals stack environment into one of 5 structural
regimes and produces a Stack Regime Adjustment (SRA) for the Weekend Risk Score.

Regime States:
  MACRO_STRESS         — Gold leading, safe haven bid, cyclicals weak
  AI_INFRA_CAPEX       — Industrial metals leading, copper/aluminum strong
  SPECULATIVE_ROTATION — High dispersion, thematic ETF volume spikes
  ENERGY_GEOPOLITICS   — Uranium/energy metals elevated, oil-metals correlation
  LOW_VOL_STABILITY    — Everything flat, low dispersion, low vol

SRA Range: -15 to +10 points applied to WRS.

Integration rule: SRA is ADVISORY. WMCE regime filter has veto authority.
MSIL cannot force a trade or override a WMCE shutdown.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Import from sibling module
from aurum.metals.dispersion.engine import MDIOutput, GLSOutput, SMBOutput, IMDIOutput


class MetalsRegime(Enum):
    MACRO_STRESS = "macro_stress"
    AI_INFRA_CAPEX = "ai_infra_capex"
    SPECULATIVE_ROTATION = "speculative_rotation"
    ENERGY_GEOPOLITICS = "energy_geopolitics"
    LOW_VOL_STABILITY = "low_vol_stability"
    UNDETERMINED = "undetermined"


@dataclass
class RegimeClassification:
    """Output of the MSIL regime classifier."""
    primary_regime: MetalsRegime
    confidence: float                      # 0-1
    regime_scores: dict[str, float]        # Score for each regime
    sra: float                             # Stack Regime Adjustment (-15 to +10)
    sra_rationale: str
    days_in_current_regime: int
    previous_regime: MetalsRegime
    warnings: list[str] = field(default_factory=list)


class MSILRegimeClassifier:
    """
    Classifies metals stack into structural regimes.

    This is a RULE-BASED classifier, not ML. Each regime has explicit
    conditions defined by thresholds on the dispersion metrics.

    The classifier scores each regime independently (0-100) and selects
    the highest-scoring regime. If no regime scores > 40, state is
    UNDETERMINED (no regime has strong evidence).
    """

    DEFAULT_CONFIG = {
        'macro_stress': {
            'gls_threshold': 50,           # GLS > +50
            'imdi_z_threshold': 1.0,       # IMDI z-score > +1.0
            'mdi_max': 60,                 # MDI < 60 (not too dispersed)
            'vix_min': 20,
            'sra_high_confidence': 10,     # SRA when confidence high
            'sra_moderate_confidence': 5,
        },
        'ai_infra_capex': {
            'gls_threshold': 0,            # GLS < 0 (gold not leading)
            'copper_gold_z_threshold': 1.0, # Copper/Gold ratio z > 1
            'mdi_max': 50,                 # Low dispersion (moving together)
            'vix_max': 18,
            'sra': -10,                    # Reduce WMCE confidence
            'sra_gold_still_leading': -5,  # Less reduction if gold still ok
        },
        'speculative_rotation': {
            'mdi_threshold': 75,           # High dispersion
            'single_outlier_z': 2.0,       # Any metal > 2σ
            'volume_spike_ratio': 2.0,     # Thematic ETF volume > 2x average
            'sra': -15,                    # Strong negative for WMCE
        },
        'energy_geopolitics': {
            'ura_z_threshold': 1.0,        # Uranium relative strength
            'energy_metals_corr_threshold': 0.3,  # Oil-metals correlation
            'gls_min': 0,                  # Gold not lagging
            'sra': 5,                      # Moderate positive for WMCE
        },
        'low_vol_stability': {
            'mdi_max': 25,                 # Low dispersion
            'gold_rv_percentile_max': 25,  # Gold vol in bottom quartile
            'vix_max': 14,
            'max_metal_z': 1.0,            # No outliers
            'sra': -10,                    # Reduce WMCE (already captured by WMCE filter)
        },
        'regime_change': {
            'min_days_for_confidence': 5,  # Must hold for 5 days before MTCE activates
            'undetermined_threshold': 40,  # Min score to declare any regime
        },
    }

    def __init__(self, config: Optional[dict] = None):
        self.config = config or self.DEFAULT_CONFIG
        self._current_regime = MetalsRegime.UNDETERMINED
        self._days_in_regime = 0
        self._previous_regime = MetalsRegime.UNDETERMINED

    def _score_macro_stress(
        self, gls: GLSOutput, imdi: IMDIOutput, mdi: MDIOutput, vix: float
    ) -> float:
        """Score evidence for Macro Stress regime (0-100)."""
        cfg = self.config['macro_stress']
        score = 0

        # Gold leadership (0-40)
        if gls.composite > cfg['gls_threshold']:
            score += 40
        elif gls.composite > 0:
            score += 20

        # Industrial-monetary divergence (0-25)
        if imdi.z_score > cfg['imdi_z_threshold']:
            score += 25
        elif imdi.z_score > 0.5:
            score += 10

        # Low-to-moderate dispersion (0-15)
        if mdi.percentile_score < cfg['mdi_max']:
            score += 15
        elif mdi.percentile_score < 75:
            score += 5

        # VIX elevated (0-20)
        if vix > cfg['vix_min']:
            score += 20
        elif vix > 16:
            score += 10

        return min(100, score)

    def _score_ai_infra_capex(
        self, gls: GLSOutput, mdi: MDIOutput,
        copper_gold_ratio_z: float, vix: float
    ) -> float:
        """Score evidence for AI Infrastructure Capex regime (0-100)."""
        cfg = self.config['ai_infra_capex']
        score = 0

        # Gold NOT leading (0-30)
        if gls.composite < cfg['gls_threshold']:
            score += 30
        elif gls.composite < 25:
            score += 15

        # Copper/Gold ratio elevated (0-30)
        if copper_gold_ratio_z > cfg['copper_gold_z_threshold']:
            score += 30
        elif copper_gold_ratio_z > 0.5:
            score += 15

        # Low dispersion (0-20)
        if mdi.percentile_score < cfg['mdi_max']:
            score += 20

        # Low VIX (0-20)
        if vix < cfg['vix_max']:
            score += 20
        elif vix < 22:
            score += 10

        return min(100, score)

    def _score_speculative_rotation(
        self, mdi: MDIOutput, metal_z_scores: dict[str, float],
        thematic_etf_volume_ratios: dict[str, float]
    ) -> float:
        """Score evidence for Speculative Rotation regime (0-100)."""
        cfg = self.config['speculative_rotation']
        score = 0

        # High dispersion (0-40)
        if mdi.percentile_score > cfg['mdi_threshold']:
            score += 40
        elif mdi.percentile_score > 60:
            score += 20

        # Single metal outlier (0-30)
        max_z = max(abs(z) for z in metal_z_scores.values()) if metal_z_scores else 0
        if max_z > cfg['single_outlier_z']:
            score += 30
        elif max_z > 1.5:
            score += 15

        # Thematic ETF volume spike (0-30)
        max_vol_ratio = max(thematic_etf_volume_ratios.values()) if thematic_etf_volume_ratios else 0
        if max_vol_ratio > cfg['volume_spike_ratio']:
            score += 30
        elif max_vol_ratio > 1.5:
            score += 15

        return min(100, score)

    def _score_energy_geopolitics(
        self, gls: GLSOutput, ura_z: float,
        energy_metals_corr: float
    ) -> float:
        """Score evidence for Energy Geopolitics regime (0-100)."""
        cfg = self.config['energy_geopolitics']
        score = 0

        # Uranium strength (0-35)
        if ura_z > cfg['ura_z_threshold']:
            score += 35
        elif ura_z > 0.5:
            score += 15

        # Oil-metals correlation (0-30)
        if energy_metals_corr > cfg['energy_metals_corr_threshold']:
            score += 30
        elif energy_metals_corr > 0.15:
            score += 15

        # Gold not lagging (0-20)
        if gls.composite > cfg['gls_min']:
            score += 20
        elif gls.composite > -25:
            score += 10

        # Bonus if copper also strong but gold/copper stable (0-15)
        # (energy geopolitics is NOT stress — it's a different mechanism)
        score += 15  # Placeholder — refined with actual data

        return min(100, score)

    def _score_low_vol_stability(
        self, mdi: MDIOutput, gold_rv_percentile: float,
        vix: float, metal_z_scores: dict[str, float]
    ) -> float:
        """Score evidence for Low Vol Stability regime (0-100)."""
        cfg = self.config['low_vol_stability']
        score = 0

        # Low dispersion (0-30)
        if mdi.percentile_score < cfg['mdi_max']:
            score += 30
        elif mdi.percentile_score < 40:
            score += 15

        # Gold vol low (0-25)
        if gold_rv_percentile < cfg['gold_rv_percentile_max']:
            score += 25
        elif gold_rv_percentile < 35:
            score += 10

        # VIX low (0-25)
        if vix < cfg['vix_max']:
            score += 25
        elif vix < 16:
            score += 10

        # No outliers (0-20)
        max_z = max(abs(z) for z in metal_z_scores.values()) if metal_z_scores else 0
        if max_z < cfg['max_metal_z']:
            score += 20
        elif max_z < 1.5:
            score += 10

        return min(100, score)

    def classify(
        self,
        mdi: MDIOutput,
        gls: GLSOutput,
        smb: SMBOutput,
        imdi: IMDIOutput,
        # Additional inputs not captured by the four metrics
        vix: float,
        copper_gold_ratio_z: float,
        gold_rv_percentile: float,
        metal_z_scores: dict[str, float],
        thematic_etf_volume_ratios: dict[str, float],
        ura_relative_strength_z: float,
        energy_metals_correlation: float,
    ) -> RegimeClassification:
        """
        Master classification function.

        Scores all 5 regimes and selects the highest. Computes SRA.
        """
        warnings = []

        # Score each regime
        scores = {
            MetalsRegime.MACRO_STRESS.value: self._score_macro_stress(gls, imdi, mdi, vix),
            MetalsRegime.AI_INFRA_CAPEX.value: self._score_ai_infra_capex(gls, mdi, copper_gold_ratio_z, vix),
            MetalsRegime.SPECULATIVE_ROTATION.value: self._score_speculative_rotation(mdi, metal_z_scores, thematic_etf_volume_ratios),
            MetalsRegime.ENERGY_GEOPOLITICS.value: self._score_energy_geopolitics(gls, ura_relative_strength_z, energy_metals_correlation),
            MetalsRegime.LOW_VOL_STABILITY.value: self._score_low_vol_stability(mdi, gold_rv_percentile, vix, metal_z_scores),
        }

        # Select highest-scoring regime
        best_regime_name = max(scores, key=scores.get)
        best_score = scores[best_regime_name]

        min_threshold = self.config['regime_change']['undetermined_threshold']
        if best_score < min_threshold:
            primary_regime = MetalsRegime.UNDETERMINED
            confidence = 0.0
            warnings.append(f"No regime scores above {min_threshold}. Environment is ambiguous.")
        else:
            primary_regime = MetalsRegime(best_regime_name)
            confidence = min(1.0, best_score / 100.0)

        # Track regime persistence
        if primary_regime == self._current_regime:
            self._days_in_regime += 1
        else:
            self._previous_regime = self._current_regime
            self._current_regime = primary_regime
            self._days_in_regime = 1

        if self._days_in_regime < self.config['regime_change']['min_days_for_confidence']:
            warnings.append(
                f"Regime {primary_regime.value} detected for only {self._days_in_regime} days. "
                f"Need {self.config['regime_change']['min_days_for_confidence']} for MTCE activation."
            )

        # Compute SRA
        sra, sra_rationale = self._compute_sra(primary_regime, gls, mdi, confidence)

        return RegimeClassification(
            primary_regime=primary_regime,
            confidence=confidence,
            regime_scores=scores,
            sra=sra,
            sra_rationale=sra_rationale,
            days_in_current_regime=self._days_in_regime,
            previous_regime=self._previous_regime,
            warnings=warnings,
        )

    def _compute_sra(
        self, regime: MetalsRegime, gls: GLSOutput, mdi: MDIOutput, confidence: float
    ) -> tuple[float, str]:
        """Compute Stack Regime Adjustment and its rationale."""
        cfg = self.config

        if regime == MetalsRegime.UNDETERMINED:
            return 0.0, "No regime detected — SRA is zero"

        if regime == MetalsRegime.MACRO_STRESS:
            if confidence > 0.7 and gls.composite > 50:
                sra = cfg['macro_stress']['sra_high_confidence']
                rationale = f"Macro stress confirmed (conf={confidence:.0%}, GLS={gls.composite:+.0f}) — SRA +{sra}"
            else:
                sra = cfg['macro_stress']['sra_moderate_confidence']
                rationale = f"Macro stress moderate (conf={confidence:.0%}, GLS={gls.composite:+.0f}) — SRA +{sra}"

        elif regime == MetalsRegime.AI_INFRA_CAPEX:
            if gls.composite > 0:
                sra = cfg['ai_infra_capex']['sra_gold_still_leading']
                rationale = f"AI capex regime but gold still leading (GLS={gls.composite:+.0f}) — SRA {sra}"
            else:
                sra = cfg['ai_infra_capex']['sra']
                rationale = f"AI capex regime, gold lagging (GLS={gls.composite:+.0f}) — SRA {sra}"

        elif regime == MetalsRegime.SPECULATIVE_ROTATION:
            sra = cfg['speculative_rotation']['sra']
            rationale = f"Speculative rotation detected (MDI={mdi.percentile_score:.0f}th pctl) — SRA {sra}"

        elif regime == MetalsRegime.ENERGY_GEOPOLITICS:
            sra = cfg['energy_geopolitics']['sra']
            rationale = f"Energy geopolitics regime — moderate WMCE boost — SRA +{sra}"

        elif regime == MetalsRegime.LOW_VOL_STABILITY:
            sra = cfg['low_vol_stability']['sra']
            rationale = f"Low vol stability — already captured by WMCE filter — SRA {sra}"

        else:
            sra = 0.0
            rationale = "Unknown regime"

        return sra, rationale

    def format_classification(self, result: RegimeClassification) -> str:
        """Human-readable regime classification report."""
        lines = [
            "=" * 70,
            "  AURUM MSIL REGIME CLASSIFICATION",
            "=" * 70,
            "",
            f"  PRIMARY REGIME:    {result.primary_regime.value.upper().replace('_', ' ')}",
            f"  CONFIDENCE:        {result.confidence:.0%}",
            f"  DAYS IN REGIME:    {result.days_in_current_regime}",
            f"  PREVIOUS REGIME:   {result.previous_regime.value.upper().replace('_', ' ')}",
            "",
            f"  STACK REGIME ADJUSTMENT (SRA): {result.sra:+.0f} points",
            f"  Rationale: {result.sra_rationale}",
            "",
            "  REGIME SCORES:",
        ]

        for regime_name, score in sorted(result.regime_scores.items(), key=lambda x: x[1], reverse=True):
            marker = " ◀" if regime_name == result.primary_regime.value else ""
            lines.append(f"    {regime_name:<25} {score:>5.0f} / 100{marker}")

        if result.warnings:
            lines.append("")
            lines.append("  WARNINGS:")
            for w in result.warnings:
                lines.append(f"    ⚠ {w}")

        lines.extend(["", "=" * 70])
        return "\n".join(lines)


# === Smoke Test ===

if __name__ == "__main__":
    # We can't import from the actual module in standalone mode,
    # so recreate the dataclasses locally for testing
    from dataclasses import dataclass as dc

    mdi = MDIOutput(
        raw_dispersion=0.028,
        percentile_score=42.0,
        lookback_days=21,
        interpretation="Normal dispersion",
        individual_returns={"GC1": 0.045, "SI1": 0.025, "HG1": -0.015, "ALI": -0.02, "PL1": 0.005, "PA1": -0.01},
    )

    gls = GLSOutput(
        rank_score=2.0, lead_lag_score=2.0, beta_score=2.0,
        composite=100.0, gold_rank=1, optimal_lag=3, gold_equity_beta=-0.3,
        interpretation="Gold leading with haven characteristics",
    )

    smb = SMBOutput(
        pct_above_20d_high=0.3, pct_above_50d_ma=0.5,
        industrial_precious_divergence=-0.047,
        breadth_score=45, interpretation="Mixed breadth",
    )

    imdi = IMDIOutput(
        raw_divergence=0.045, z_score=1.8,
        monetary_return=0.035, industrial_return=-0.010,
        interpretation="Strong monetary outperformance — macro stress",
    )

    classifier = MSILRegimeClassifier()
    result = classifier.classify(
        mdi=mdi, gls=gls, smb=smb, imdi=imdi,
        vix=24.0,
        copper_gold_ratio_z=-1.2,
        gold_rv_percentile=65.0,
        metal_z_scores={"GC1": 2.1, "SI1": 1.0, "HG1": -1.2, "ALI": -1.5, "PL1": 0.2, "PA1": -0.8},
        thematic_etf_volume_ratios={"LIT": 1.1, "URA": 1.3, "COPX": 0.9},
        ura_relative_strength_z=0.3,
        energy_metals_correlation=0.15,
    )

    print(classifier.format_classification(result))
