"""
AURUM Trade Structuring Engine
================================
Converts Weekend Risk Score into specific option trade recommendations.

This module does NOT execute trades. It produces structured trade tickets
that can be reviewed by a human or passed to an execution engine.

Key principles:
  - Convexity over directionality (we buy optionality, not delta)
  - Size discipline: max loss per weekend is hard-capped
  - Instrument selection is deterministic given WRS and vol surface
  - Every trade ticket includes max loss, rationale, and exit rules
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OptionType(Enum):
    CALL = "call"
    PUT = "put"


class Structure(Enum):
    STRADDLE = "straddle"          # ATM call + ATM put
    STRANGLE = "strangle"          # OTM call + OTM put
    DEBIT_SPREAD = "debit_spread"  # Long near + short far (same type)
    CALENDAR = "calendar"          # Long short-dated + short long-dated
    RATIO = "ratio"                # Unequal legs


class Tenor(Enum):
    ZERO_DTE = "0dte"       # Expiring same session / Monday AM
    WEEKLY = "weekly"       # 5-7 DTE
    MONTHLY = "monthly"     # 20-30 DTE


@dataclass
class OptionLeg:
    """Single leg of an option trade."""
    option_type: OptionType
    tenor: Tenor
    strike_offset_pct: float   # 0.0 = ATM, 0.05 = 5% OTM, -0.05 = 5% ITM
    quantity: int              # Positive = long, negative = short
    estimated_premium: float   # Per contract, in dollars
    estimated_iv: float        # Implied vol at entry


@dataclass
class TradeTicket:
    """Complete trade recommendation."""
    structure: Structure
    legs: list[OptionLeg]
    total_premium: float           # Total cost (debit) or credit
    max_loss: float                # Absolute worst case
    max_loss_pct_nav: float        # As percentage of allocated NAV
    conviction: str                # "LOW" | "MEDIUM" | "HIGH"
    wrs_score: float               # The WRS that generated this ticket
    rationale: str
    entry_window: str              # e.g., "Friday 2:30-3:30 PM ET"
    exit_rules: list[str]
    warnings: list[str] = field(default_factory=list)


class TradeStructuringEngine:
    """
    Maps WRS score → option structures.

    Configuration:
      nav: Allocated NAV for this strategy
      max_single_weekend_risk: Maximum loss as fraction of NAV (default 0.015)
      max_position_pct_adv: Maximum position as % of average daily volume
    """

    def __init__(
        self,
        nav: float,
        max_single_weekend_risk: float = 0.015,
        max_position_pct_adv: float = 0.20,
    ):
        self.nav = nav
        self.max_single_weekend_risk = max_single_weekend_risk
        self.max_position_pct_adv = max_position_pct_adv

    def _max_premium_budget(self, conviction_multiplier: float = 1.0) -> float:
        """Maximum premium we can spend this weekend."""
        return self.nav * self.max_single_weekend_risk * conviction_multiplier

    def _estimate_contracts(
        self,
        premium_per_contract: float,
        budget: float,
        avg_daily_volume: int,
    ) -> int:
        """
        Compute number of contracts respecting both budget and liquidity.
        """
        if premium_per_contract <= 0:
            return 0

        by_budget = int(budget / premium_per_contract)
        by_liquidity = int(avg_daily_volume * self.max_position_pct_adv)
        return max(1, min(by_budget, by_liquidity))

    def structure_trade(
        self,
        wrs_score: float,
        trade_recommendation: str,
        # Vol surface inputs (simplified)
        gold_spot_price: float,
        atm_iv_0dte: float,            # ATM implied vol, 0DTE
        atm_iv_weekly: float,          # ATM implied vol, weekly
        atm_iv_monthly: float,         # ATM implied vol, monthly
        straddle_price_0dte: float,    # Market price of ATM straddle, per oz
        straddle_price_weekly: float,
        strangle_price_weekly: float,  # 5% OTM strangle, weekly
        # Liquidity
        avg_daily_option_volume: int,  # Average daily volume, relevant strikes
        # Override flag
        iv_override_active: bool = False,
    ) -> Optional[TradeTicket]:
        """
        Generate trade ticket from WRS score and market data.

        Returns None if recommendation is NO_TRADE or MONITOR.
        """
        if trade_recommendation in ("NO_TRADE", "MONITOR"):
            return None

        # Determine conviction and budget
        if trade_recommendation == "SMALL":
            conviction = "LOW"
            budget_multiplier = 0.33
        elif trade_recommendation == "STANDARD":
            conviction = "MEDIUM"
            budget_multiplier = 0.67
        elif trade_recommendation == "MAXIMUM":
            conviction = "HIGH"
            budget_multiplier = 1.0
        else:
            return None

        # Apply IV override
        if iv_override_active:
            budget_multiplier *= 0.5

        budget = self._max_premium_budget(budget_multiplier)
        warnings = []

        # --- Structure Selection Logic ---

        if trade_recommendation == "SMALL":
            # Low conviction: debit spread to reduce theta cost
            # Long ATM weekly straddle, capped premium
            n_contracts = self._estimate_contracts(
                straddle_price_weekly, budget, avg_daily_option_volume
            )
            legs = [
                OptionLeg(OptionType.CALL, Tenor.WEEKLY, 0.0, n_contracts,
                         straddle_price_weekly / 2, atm_iv_weekly),
                OptionLeg(OptionType.PUT, Tenor.WEEKLY, 0.0, n_contracts,
                         straddle_price_weekly / 2, atm_iv_weekly),
            ]
            total_premium = straddle_price_weekly * n_contracts
            rationale = (
                f"Low conviction (WRS={wrs_score:.0f}). Weekly ATM straddle "
                f"provides exposure to weekend gap with manageable theta. "
                f"{n_contracts} contracts at ${straddle_price_weekly:.2f}/straddle."
            )
            exit_rules = [
                "Monday gap > 1.5%: Scale out 50% at open, trail remainder.",
                "Monday gap 0.5-1.5%: Hold until 11AM ET, reassess.",
                "Monday gap < 0.5%: Hold through Tuesday (weekly has time).",
                "Cut all by Wednesday if no movement.",
            ]
            structure = Structure.STRADDLE

        elif trade_recommendation == "STANDARD":
            # Standard: weekly straddle + small 0DTE kicker
            weekly_budget = budget * 0.80
            dte0_budget = budget * 0.20

            n_weekly = self._estimate_contracts(
                straddle_price_weekly, weekly_budget, avg_daily_option_volume
            )
            n_0dte = self._estimate_contracts(
                straddle_price_0dte, dte0_budget, avg_daily_option_volume
            )

            legs = [
                # Weekly straddle
                OptionLeg(OptionType.CALL, Tenor.WEEKLY, 0.0, n_weekly,
                         straddle_price_weekly / 2, atm_iv_weekly),
                OptionLeg(OptionType.PUT, Tenor.WEEKLY, 0.0, n_weekly,
                         straddle_price_weekly / 2, atm_iv_weekly),
                # 0DTE kicker
                OptionLeg(OptionType.CALL, Tenor.ZERO_DTE, 0.0, n_0dte,
                         straddle_price_0dte / 2, atm_iv_0dte),
                OptionLeg(OptionType.PUT, Tenor.ZERO_DTE, 0.0, n_0dte,
                         straddle_price_0dte / 2, atm_iv_0dte),
            ]
            total_premium = (straddle_price_weekly * n_weekly +
                           straddle_price_0dte * n_0dte)
            rationale = (
                f"Standard conviction (WRS={wrs_score:.0f}). "
                f"Weekly straddle ({n_weekly}x) for core exposure + "
                f"0DTE kicker ({n_0dte}x) for maximum Monday AM convexity."
            )
            exit_rules = [
                "0DTE: Close by Monday 11AM regardless.",
                "Monday gap > 1.5%: Scale out 50% weekly at open.",
                "Monday gap 0.5-1.5%: Hold weekly, take profit on 0DTE.",
                "Monday gap < 0.5%: Cut 0DTE at open, hold weekly to Wed.",
            ]
            structure = Structure.STRADDLE

        elif trade_recommendation == "MAXIMUM":
            # Maximum: weekly strangle + 0DTE straddle + optional calendar
            strangle_budget = budget * 0.50
            dte0_budget = budget * 0.30
            calendar_budget = budget * 0.20

            n_strangle = self._estimate_contracts(
                strangle_price_weekly, strangle_budget, avg_daily_option_volume
            )
            n_0dte = self._estimate_contracts(
                straddle_price_0dte, dte0_budget, avg_daily_option_volume
            )

            legs = [
                # Weekly 5% OTM strangle
                OptionLeg(OptionType.CALL, Tenor.WEEKLY, 0.05, n_strangle,
                         strangle_price_weekly / 2, atm_iv_weekly),
                OptionLeg(OptionType.PUT, Tenor.WEEKLY, -0.05, n_strangle,
                         strangle_price_weekly / 2, atm_iv_weekly),
                # 0DTE ATM straddle
                OptionLeg(OptionType.CALL, Tenor.ZERO_DTE, 0.0, n_0dte,
                         straddle_price_0dte / 2, atm_iv_0dte),
                OptionLeg(OptionType.PUT, Tenor.ZERO_DTE, 0.0, n_0dte,
                         straddle_price_0dte / 2, atm_iv_0dte),
            ]

            # Calendar: sell further OTM monthly to partially fund weekly
            # Only if vol surface is in contango (monthly IV > weekly IV)
            if atm_iv_monthly > atm_iv_weekly * 1.05:
                warnings.append(
                    "Vol surface in contango — calendar financing available "
                    "but NOT auto-included. Review monthly OTM strikes manually."
                )

            total_premium = (strangle_price_weekly * n_strangle +
                           straddle_price_0dte * n_0dte)
            rationale = (
                f"Maximum conviction (WRS={wrs_score:.0f}). "
                f"Weekly 5% OTM strangle ({n_strangle}x) for wings + "
                f"0DTE straddle ({n_0dte}x) for ATM convexity. "
                f"Total premium: ${total_premium:,.0f}."
            )
            exit_rules = [
                "0DTE: Close by Monday 11AM regardless.",
                "Monday gap > 2%: Take profit on 50% of strangle at open.",
                "Monday gap 1-2%: Hold strangle, take 0DTE profit.",
                "Monday gap < 0.5%: Cut 0DTE at loss, hold strangle to Wed.",
                "If WRS was > 90 and gap doesn't materialize: full exit Monday.",
            ]
            structure = Structure.STRANGLE

            if iv_override_active:
                warnings.append(
                    "IV override active — size reduced 50%. "
                    "Market may already be pricing weekend risk."
                )
        else:
            return None

        # Liquidity check
        if total_premium > budget * 1.05:
            warnings.append(
                f"Estimated premium ${total_premium:,.0f} exceeds budget "
                f"${budget:,.0f}. Reduce contracts."
            )

        return TradeTicket(
            structure=structure,
            legs=legs,
            total_premium=total_premium,
            max_loss=total_premium,  # For long options, max loss = premium
            max_loss_pct_nav=total_premium / self.nav if self.nav > 0 else 0,
            conviction=conviction,
            wrs_score=wrs_score,
            rationale=rationale,
            entry_window="Friday 2:30-3:30 PM ET",
            exit_rules=exit_rules,
            warnings=warnings,
        )

    def format_ticket(self, ticket: TradeTicket) -> str:
        """Human-readable trade ticket."""
        lines = [
            "=" * 60,
            "  AURUM TRADE TICKET",
            "=" * 60,
            f"  Structure:    {ticket.structure.value.upper()}",
            f"  Conviction:   {ticket.conviction}",
            f"  WRS Score:    {ticket.wrs_score:.0f}",
            f"  Entry Window: {ticket.entry_window}",
            "",
            f"  Total Premium:   ${ticket.total_premium:>12,.2f}",
            f"  Max Loss:        ${ticket.max_loss:>12,.2f}",
            f"  Max Loss % NAV:  {ticket.max_loss_pct_nav:>11.2%}",
            "",
            "  LEGS:",
        ]

        for i, leg in enumerate(ticket.legs, 1):
            direction = "LONG" if leg.quantity > 0 else "SHORT"
            strike_desc = "ATM" if leg.strike_offset_pct == 0 else f"{abs(leg.strike_offset_pct)*100:.0f}% OTM"
            lines.append(
                f"    {i}. {direction} {leg.quantity}x {leg.tenor.value} "
                f"{leg.option_type.value.upper()} ({strike_desc}) "
                f"@ ${leg.estimated_premium:.2f} | IV={leg.estimated_iv:.1f}%"
            )

        lines.append("")
        lines.append("  EXIT RULES:")
        for rule in ticket.exit_rules:
            lines.append(f"    • {rule}")

        if ticket.warnings:
            lines.append("")
            lines.append("  WARNINGS:")
            for w in ticket.warnings:
                lines.append(f"    ⚠ {w}")

        lines.append("")
        lines.append(f"  RATIONALE: {ticket.rationale}")
        lines.append("=" * 60)
        return "\n".join(lines)


# --- Example ---
if __name__ == "__main__":
    engine = TradeStructuringEngine(nav=500_000)

    ticket = engine.structure_trade(
        wrs_score=72,
        trade_recommendation="STANDARD",
        gold_spot_price=2950.0,
        atm_iv_0dte=28.0,
        atm_iv_weekly=24.0,
        atm_iv_monthly=21.0,
        straddle_price_0dte=15.0,     # $15 per oz for 0DTE straddle
        straddle_price_weekly=45.0,   # $45 per oz for weekly straddle
        strangle_price_weekly=22.0,   # $22 per oz for 5% OTM weekly strangle
        avg_daily_option_volume=5000,
        iv_override_active=False,
    )

    if ticket:
        print(engine.format_ticket(ticket))
