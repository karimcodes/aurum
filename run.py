#!/usr/bin/env python3
"""
AURUM — Weekend Macro Convexity Engine
=========================================
Main entry point. Run this on Friday afternoon.

Usage:
    python run.py              # Live data from Yahoo Finance
    python run.py --demo       # Simulated data (no internet needed)
    python run.py --date 2025-01-10  # Historical backtest for a specific Friday

Output:
    A complete trade recommendation with:
    - Weekend Risk Score (0-100)
    - Regime classification
    - Specific option trade (instrument, strike, size)
    - Exit rules
"""

import sys
import os
import math
import argparse
from datetime import datetime, date

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.fetcher import fetch_data, generate_demo_data, DataBundle


# ============================================================
# CORE ENGINE (self-contained — no cross-module imports needed)
# ============================================================
# We inline the scoring logic here so run.py works as a single
# entry point without complex import chains. The individual
# module files remain the source of truth for the math.

def compute_wrs(data: DataBundle) -> dict:
    """
    Compute Weekend Risk Score from data bundle.

    Simplified but faithful implementation of the full WRS engine.
    Scores 5 primary signals + 2 confirmations.
    """
    scores = {}
    warnings = []

    # S1: Friday Gold Momentum (0-20)
    # Strong Friday = likely continuation into weekend
    fri_ret = abs(data.gold_friday_return)
    if fri_ret > 0.02:
        scores['S1_friday_momentum'] = 20
    elif fri_ret > 0.015:
        scores['S1_friday_momentum'] = 15
    elif fri_ret > 0.01:
        scores['S1_friday_momentum'] = 12
    elif fri_ret > 0.005:
        scores['S1_friday_momentum'] = 6
    else:
        scores['S1_friday_momentum'] = 0

    # S2: Volume Anomaly (0-10)
    if data.gold_volume_zscore > 2.0:
        scores['S2_volume_anomaly'] = 10
    elif data.gold_volume_zscore > 1.0:
        scores['S2_volume_anomaly'] = 6
    elif data.gold_volume_zscore > 0.5:
        scores['S2_volume_anomaly'] = 3
    else:
        scores['S2_volume_anomaly'] = 0

    # S3: Vol Term Structure (0-15)
    # Using RV5/RV21 as proxy for term structure inversion
    # (real version needs options IV data)
    if data.gold_rv_21d > 0:
        rv_ratio = data.gold_rv_5d / data.gold_rv_21d
    else:
        rv_ratio = 1.0

    if rv_ratio > 1.5:
        scores['S3_vol_term_structure'] = 15
    elif rv_ratio > 1.2:
        scores['S3_vol_term_structure'] = 10
    elif rv_ratio > 1.0:
        scores['S3_vol_term_structure'] = 5
    else:
        scores['S3_vol_term_structure'] = 0

    # S4: Gap Momentum (0-15)
    # Using 5-day gold return as proxy (real version uses gap history)
    gold_5d = data.returns_5d.get('GC1', data.returns_5d.get('GLD', 0)) or 0
    if abs(gold_5d) > 0.03:
        scores['S4_gap_momentum'] = 15
    elif abs(gold_5d) > 0.02:
        scores['S4_gap_momentum'] = 10
    elif abs(gold_5d) > 0.01:
        scores['S4_gap_momentum'] = 5
    else:
        scores['S4_gap_momentum'] = 0

    # S5: Cross-Asset Stress (0-15)
    vix = data.vix
    if vix > 30:
        scores['S5_cross_asset_stress'] = 15
    elif vix > 25:
        scores['S5_cross_asset_stress'] = 12
    elif vix > 20:
        scores['S5_cross_asset_stress'] = 8
    elif vix > 16:
        scores['S5_cross_asset_stress'] = 4
    else:
        scores['S5_cross_asset_stress'] = 0

    # C1: Silver Sympathy (-10 to +5)
    silver_21d = data.returns_21d.get('SI1', 0) or 0
    gold_21d = data.returns_21d.get('GC1', data.returns_21d.get('GLD', 0)) or 0
    if gold_21d > 0.01 and silver_21d > 0.005:
        scores['C1_silver_sympathy'] = 5  # Silver confirming
    elif gold_21d > 0.01 and silver_21d < -0.005:
        scores['C1_silver_sympathy'] = -10  # Silver diverging — penalty
        warnings.append("Silver NOT confirming gold strength")
    else:
        scores['C1_silver_sympathy'] = 0

    # C2: Equity Pre-positioning (0-10)
    es_ret = data.returns_1d.get('ES1', 0) or 0
    if es_ret < -0.01 and data.gold_friday_return > 0.005:
        scores['C2_equity_preposition'] = 10  # Equities down, gold up = risk-off
    elif es_ret < -0.005:
        scores['C2_equity_preposition'] = 5
    else:
        scores['C2_equity_preposition'] = 0

    # NLP Analysis - Real news-based scoring
    try:
        from intelligence.nlp_analyzer import run_full_nlp_analysis
        nlp_result = run_full_nlp_analysis()
        scores['NLP_narrative_pressure'] = nlp_result.narrative_pressure_score

        # Add NLP insights to warnings if significant
        if nlp_result.shift_detected:
            warnings.append(f"NLP: {nlp_result.shift_type} - {nlp_result.interpretation[:80]}")
        if nlp_result.direction == 'escalating' and nlp_result.narrative_pressure_score > 6:
            warnings.append(f"NLP: High narrative pressure ({nlp_result.escalation_count} risk headlines)")

    except Exception as e:
        # Fallback to VIX-based proxy if NLP fails
        print(f"  NLP analysis unavailable: {e}")
        if vix > 25:
            scores['NLP_narrative_pressure'] = 8
        elif vix > 20:
            scores['NLP_narrative_pressure'] = 4
        else:
            scores['NLP_narrative_pressure'] = 0

    raw_wrs = sum(scores.values())
    wrs = max(0, min(100, raw_wrs))

    return {
        'wrs': wrs,
        'components': scores,
        'warnings': warnings,
    }


def compute_metals_regime(data: DataBundle) -> dict:
    """
    Simplified metals regime classification.
    Returns regime state and SRA adjustment.
    """
    gold_21d = data.returns_21d.get('GC1', data.returns_21d.get('GLD', 0)) or 0
    copper_21d = data.returns_21d.get('HG1', 0) or 0
    silver_21d = data.returns_21d.get('SI1', 0) or 0

    # Industrial vs precious spread
    industrial_ret = copper_21d
    precious_ret = (gold_21d + silver_21d) / 2

    # Gold leadership (is gold #1?)
    stack_returns = {
        'Gold': gold_21d,
        'Silver': silver_21d,
        'Copper': copper_21d,
    }

    for ticker in ['GDX', 'FCX', 'URA', 'COPX']:
        val = data.returns_21d.get(ticker, None)
        if val is not None and not math.isnan(val):
            stack_returns[ticker] = val

    sorted_stack = sorted(stack_returns.items(), key=lambda x: x[1], reverse=True)
    gold_rank = next((i + 1 for i, (k, _) in enumerate(sorted_stack) if k == 'Gold'), len(sorted_stack))

    # Dispersion
    if len(stack_returns) >= 3:
        vals = list(stack_returns.values())
        mean_r = sum(vals) / len(vals)
        dispersion = math.sqrt(sum((v - mean_r) ** 2 for v in vals) / len(vals))
    else:
        dispersion = 0

    # Regime classification (simplified)
    vix = data.vix
    sra = 0
    regime = "UNDETERMINED"

    if gold_rank <= 2 and precious_ret > industrial_ret + 0.01 and vix > 18:
        regime = "MACRO_STRESS"
        sra = 10
    elif copper_21d > gold_21d + 0.01 and vix < 20:
        regime = "AI_INFRA_CAPEX"
        sra = -10
    elif dispersion > 0.04:
        regime = "SPECULATIVE_ROTATION"
        sra = -15
    elif vix < 14 and dispersion < 0.01:
        regime = "LOW_VOL_STABILITY"
        sra = -10
    elif data.returns_21d.get('URA', 0) and (data.returns_21d.get('URA', 0) or 0) > 0.03:
        regime = "ENERGY_GEOPOLITICS"
        sra = 5
    else:
        regime = "NORMAL"
        sra = 0

    return {
        'regime': regime,
        'sra': sra,
        'gold_rank': gold_rank,
        'stack_of': len(sorted_stack),
        'dispersion': dispersion,
        'stack_returns': sorted_stack,
    }


def compute_trade_recommendation(wrs: float, data: DataBundle) -> dict:
    """
    Convert WRS into a specific, actionable trade recommendation.
    Uses GLD (equity options) for accessibility.
    """
    gold_price = data.gold_price
    gld_price = data.prices.get('GLD', gold_price / 10)  # GLD ≈ 1/10th of gold

    # Account size assumption (you should change this)
    account_nav = 10000  # Default $10K — user should customize

    if wrs < 21:
        return {
            'action': 'NO TRADE',
            'reason': f'WRS {wrs:.0f} below minimum threshold (21)',
            'instrument': None,
            'structure': None,
            'premium': 0,
            'contracts': 0,
            'max_loss': 0,
            'exit_rules': None,
        }
    elif wrs < 41:
        return {
            'action': 'MONITOR ONLY',
            'reason': f'WRS {wrs:.0f} in monitor zone (21-40). Watch but do not trade.',
            'instrument': None,
            'structure': None,
            'premium': 0,
            'contracts': 0,
            'max_loss': 0,
            'exit_rules': None,
        }
    elif wrs < 61:
        # SMALL position: weekly ATM straddle, 0.5% NAV
        budget = account_nav * 0.005
        est_premium = gld_price * 0.02  # Rough: ATM straddle ≈ 2% of underlying
        contracts = max(1, int(budget / (est_premium * 100)))
        total_cost = contracts * est_premium * 100

        return {
            'action': 'SMALL POSITION',
            'reason': f'WRS {wrs:.0f} in small zone (41-60)',
            'instrument': 'GLD weekly options',
            'structure': f'Buy {contracts}x GLD ATM straddle (weekly expiry)',
            'strike': f'${gld_price:.0f} (ATM)',
            'premium': f'~${total_cost:.0f} total ({total_cost/account_nav:.1%} of NAV)',
            'contracts': contracts,
            'max_loss': f'${total_cost:.0f} (premium paid)',
            'exit_rules': [
                'Monday 11AM: if gold gap < 0.3%, close entire position',
                'Monday 11AM: if gold gap 0.3-1.0%, hold until 2PM, then close',
                'Monday 11AM: if gold gap > 1.0%, close 50%, trail rest with 50% retracement stop',
                'Tuesday open: close any remaining position regardless',
            ],
        }
    elif wrs < 81:
        # STANDARD position: weekly straddle, 1.0% NAV
        budget = account_nav * 0.01
        est_premium = gld_price * 0.02
        contracts = max(1, int(budget / (est_premium * 100)))
        total_cost = contracts * est_premium * 100

        return {
            'action': 'STANDARD POSITION',
            'reason': f'WRS {wrs:.0f} in standard zone (61-80)',
            'instrument': 'GLD weekly options',
            'structure': f'Buy {contracts}x GLD ATM straddle (weekly expiry)',
            'strike': f'${gld_price:.0f} (ATM)',
            'premium': f'~${total_cost:.0f} total ({total_cost/account_nav:.1%} of NAV)',
            'contracts': contracts,
            'max_loss': f'${total_cost:.0f} (premium paid)',
            'exit_rules': [
                'Monday 10AM: if gold gap < 0.3%, close entire position',
                'Monday 10AM: if gold gap 0.3-1.5%, hold until 2PM, scale out 50%',
                'Monday 10AM: if gold gap > 1.5%, close 50%, trail rest with 40% stop',
                'If gap > 2.5%, close 75% immediately — take the win',
                'Tuesday open: close any remaining position regardless',
            ],
        }
    else:
        # MAXIMUM position: weekly strangle + wider wings, 1.5% NAV
        budget = account_nav * 0.015
        est_premium = gld_price * 0.015  # OTM strangle is cheaper per unit
        contracts = max(1, int(budget / (est_premium * 100)))
        total_cost = contracts * est_premium * 100

        otm_call = gld_price * 1.03
        otm_put = gld_price * 0.97

        return {
            'action': 'MAXIMUM POSITION',
            'reason': f'WRS {wrs:.0f} in maximum zone (81-100)',
            'instrument': 'GLD weekly options',
            'structure': f'Buy {contracts}x GLD weekly strangle: ${otm_call:.0f} calls + ${otm_put:.0f} puts',
            'strike': f'Call ${otm_call:.0f} / Put ${otm_put:.0f} (3% OTM)',
            'premium': f'~${total_cost:.0f} total ({total_cost/account_nav:.1%} of NAV)',
            'contracts': contracts,
            'max_loss': f'${total_cost:.0f} (premium paid)',
            'exit_rules': [
                'Monday 10AM: if gold gap < 0.5%, close losing leg, hold winning leg',
                'Monday 10AM: if gold gap > 1.5%, close winning leg for 50% profit',
                'Monday 2PM: close all remaining positions',
                'If gap > 3%, close immediately — take the exceptional win',
                'Do NOT hold past Tuesday under any circumstances',
            ],
        }


# ============================================================
# DASHBOARD OUTPUT
# ============================================================

def print_dashboard(data: DataBundle, wrs_result: dict, regime_result: dict, trade: dict):
    """Print the complete Friday afternoon dashboard."""

    wrs = wrs_result['wrs']
    regime = regime_result['regime']
    sra = regime_result['sra']
    adjusted_wrs = max(0, min(100, wrs + sra))

    # Header
    print()
    print("=" * 70)
    print("  ╔═══════════════════════════════════════════════════════════╗")
    print("  ║         AURUM — WEEKEND MACRO CONVEXITY ENGINE           ║")
    print("  ║              Friday Afternoon Dashboard                   ║")
    print("  ╚═══════════════════════════════════════════════════════════╝")
    print("=" * 70)
    print(f"  Date: {data.timestamp}")
    print(f"  Gold: ${data.gold_price:,.2f}   Silver: ${data.silver_price:.2f}   VIX: {data.vix:.1f}")
    print(f"  Au/Ag: {data.gold_silver_ratio:.1f}   Gold RV(21d): {data.gold_rv_21d:.1f}%")
    print()

    # WRS
    bar_len = 40
    filled = int(adjusted_wrs / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)

    print("  ─── WEEKEND RISK SCORE ───")
    print(f"  Raw WRS:      {wrs:.0f}")
    print(f"  Regime SRA:   {sra:+.0f} ({regime})")
    print(f"  Adjusted WRS: {adjusted_wrs:.0f} / 100")
    print(f"  [{bar}]")
    print()

    # Signal breakdown
    print("  ─── SIGNAL BREAKDOWN ───")
    for signal, value in wrs_result['components'].items():
        label = signal.replace('_', ' ').title()
        indicator = "●" if value > 0 else "○"
        print(f"    {indicator} {label:<30} {value:>+4.0f}")
    print(f"    {'─' * 38}")
    print(f"    {'Total':<32} {wrs:>4.0f}")
    print()

    if wrs_result['warnings']:
        print("  ─── WARNINGS ───")
        for w in wrs_result['warnings']:
            print(f"    ⚠ {w}")
        print()

    # Regime
    print("  ─── METALS REGIME ───")
    print(f"  Regime:     {regime}")
    print(f"  Gold Rank:  #{regime_result['gold_rank']} of {regime_result['stack_of']} metals")
    print(f"  Dispersion: {regime_result['dispersion']:.4f}")
    print(f"  Stack (21d returns):")
    for name, ret in regime_result['stack_returns']:
        marker = " ◀ GOLD" if name == 'Gold' else ""
        print(f"    {name:<10} {ret:>+7.2%}{marker}")
    print()

    # Trade recommendation
    print("  ═══════════════════════════════════════════════════════════")
    if trade['action'] in ('NO TRADE', 'MONITOR ONLY'):
        print(f"  RECOMMENDATION:  {trade['action']}")
        print(f"  Reason: {trade['reason']}")
    else:
        print(f"  RECOMMENDATION:  {trade['action']}")
        print(f"  {trade['reason']}")
        print()
        print(f"  Instrument:  {trade['instrument']}")
        print(f"  Trade:       {trade['structure']}")
        print(f"  Strike:      {trade['strike']}")
        print(f"  Cost:        {trade['premium']}")
        print(f"  Max Loss:    {trade['max_loss']}")
        print()
        print("  EXIT RULES:")
        for rule in trade['exit_rules']:
            print(f"    → {rule}")

    print()
    print("  ═══════════════════════════════════════════════════════════")

    # Errors
    if data.errors:
        print()
        print("  ─── DATA NOTES ───")
        for e in data.errors:
            print(f"    ℹ {e}")

    print()
    print("=" * 70)
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AURUM — Weekend Macro Convexity Engine",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        '--demo', action='store_true',
        help='Use simulated data (no internet needed)',
    )
    parser.add_argument(
        '--date', type=str, default=None,
        help='Historical date to evaluate (YYYY-MM-DD format)',
    )
    parser.add_argument(
        '--nav', type=float, default=10000,
        help='Account size in USD (default: $10,000)',
    )
    parser.add_argument(
        '--api', action='store_true',
        help='Start the API server instead of running CLI analysis',
    )
    parser.add_argument(
        '--port', type=int, default=8000,
        help='API server port (default: 8000)',
    )
    args = parser.parse_args()

    # Start API server if requested
    if args.api:
        print()
        print("  Starting AURUM API server...")
        print(f"  API docs: http://localhost:{args.port}/docs")
        print(f"  Dashboard: http://localhost:3000 (start Next.js separately)")
        print()
        try:
            import uvicorn
            uvicorn.run(
                "api.main:app",
                host="0.0.0.0",
                port=args.port,
                reload=True,
            )
        except ImportError:
            print("  ERROR: uvicorn not installed. Run: pip install uvicorn fastapi")
            sys.exit(1)
        return

    print()
    print("  AURUM starting...")

    # Step 1: Get data
    if args.demo:
        print("  Mode: DEMO (simulated data)")
        data = generate_demo_data()
    else:
        if args.date:
            print(f"  Mode: HISTORICAL ({args.date})")
        else:
            print("  Mode: LIVE (Yahoo Finance)")
        data = fetch_data(lookback_days=365, date=args.date)

    if not data.prices:
        print("  ERROR: No data available. Check your internet connection.")
        print("  Try: python run.py --demo")
        sys.exit(1)

    print(f"  Data loaded: {len(data.prices)} instruments, as of {data.timestamp}")

    # Step 2: Compute WRS
    wrs_result = compute_wrs(data)
    print(f"  WRS computed: {wrs_result['wrs']:.0f}")

    # Step 3: Compute regime
    regime_result = compute_metals_regime(data)
    print(f"  Regime: {regime_result['regime']} (SRA: {regime_result['sra']:+.0f})")

    # Step 4: Generate trade recommendation
    adjusted_wrs = max(0, min(100, wrs_result['wrs'] + regime_result['sra']))
    trade = compute_trade_recommendation(adjusted_wrs, data)
    print(f"  Recommendation: {trade['action']}")

    # Step 5: Print dashboard
    print_dashboard(data, wrs_result, regime_result, trade)


if __name__ == '__main__':
    main()
