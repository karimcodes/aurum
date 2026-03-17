"""
AURUM Event Calendar
====================
Tracks scheduled high-impact events that could drive weekend gold gaps.

Event Types:
  - Central Bank: FOMC, ECB, BOJ decisions and speeches
  - Geopolitical: G7/G20 summits, elections, treaty deadlines
  - Economic: NFP, CPI, GDP releases
  - Market: Options expiry, futures rollover

Each event has a "weekend risk weight" based on:
  1. Proximity to weekend (Friday event = higher weight)
  2. Historical impact on gold
  3. Current market sensitivity
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import time


@dataclass
class ScheduledEvent:
    """A scheduled market-moving event."""
    name: str
    date: str  # YYYY-MM-DD
    time: Optional[str]  # HH:MM ET, if known
    category: str  # 'central_bank', 'geopolitical', 'economic', 'market'
    impact: str  # 'HIGH', 'MEDIUM', 'LOW'
    description: str
    gold_sensitivity: float  # 1.0 = normal, 2.0 = very sensitive to gold

    @property
    def datetime_obj(self) -> datetime:
        """Parse date string to datetime."""
        return datetime.strptime(self.date, '%Y-%m-%d')

    @property
    def days_until(self) -> int:
        """Days until this event."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        event_date = self.datetime_obj
        return (event_date - today).days

    @property
    def is_this_weekend(self) -> bool:
        """True if event falls on upcoming Sat/Sun."""
        days = self.days_until
        today_weekday = datetime.now().weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun

        # Calculate days until Saturday
        days_to_sat = (5 - today_weekday) % 7
        days_to_sun = (6 - today_weekday) % 7

        return days == days_to_sat or days == days_to_sun

    @property
    def is_friday(self) -> bool:
        """True if event is on Friday (affects weekend positioning)."""
        return self.datetime_obj.weekday() == 4


# ============================================================
# 2026 Event Calendar (Update quarterly)
# ============================================================

EVENTS_2026 = [
    # FOMC Meetings (2026 schedule)
    ScheduledEvent("FOMC Meeting", "2026-01-28", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-03-18", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-05-06", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-06-17", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-07-29", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-09-16", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-11-04", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),
    ScheduledEvent("FOMC Meeting", "2026-12-16", "14:00", "central_bank", "HIGH",
                   "Federal Reserve interest rate decision", 2.0),

    # Fed Chair Speeches (examples - update as scheduled)
    ScheduledEvent("Powell Speech", "2026-02-19", "10:00", "central_bank", "MEDIUM",
                   "Fed Chair Powell testimony to Congress", 1.5),
    ScheduledEvent("Powell Speech", "2026-02-20", "10:00", "central_bank", "MEDIUM",
                   "Fed Chair Powell testimony to Congress Day 2", 1.5),

    # ECB Meetings (2026)
    ScheduledEvent("ECB Meeting", "2026-01-30", "13:45", "central_bank", "MEDIUM",
                   "European Central Bank rate decision", 1.3),
    ScheduledEvent("ECB Meeting", "2026-03-06", "13:45", "central_bank", "MEDIUM",
                   "European Central Bank rate decision", 1.3),
    ScheduledEvent("ECB Meeting", "2026-04-17", "13:45", "central_bank", "MEDIUM",
                   "European Central Bank rate decision", 1.3),

    # Key Economic Data (Monthly - showing next few months)
    ScheduledEvent("US CPI", "2026-02-12", "08:30", "economic", "HIGH",
                   "Consumer Price Index - inflation gauge", 1.8),
    ScheduledEvent("US NFP", "2026-02-07", "08:30", "economic", "HIGH",
                   "Non-Farm Payrolls - employment report", 1.5),
    ScheduledEvent("US CPI", "2026-03-12", "08:30", "economic", "HIGH",
                   "Consumer Price Index - inflation gauge", 1.8),
    ScheduledEvent("US NFP", "2026-03-06", "08:30", "economic", "HIGH",
                   "Non-Farm Payrolls - employment report", 1.5),
    ScheduledEvent("US GDP", "2026-02-27", "08:30", "economic", "MEDIUM",
                   "Q4 2025 GDP Second Estimate", 1.3),

    # Options Expiry (Monthly - third Friday)
    ScheduledEvent("Options Expiry", "2026-02-20", "16:00", "market", "MEDIUM",
                   "Monthly equity options expiration", 1.2),
    ScheduledEvent("Options Expiry", "2026-03-20", "16:00", "market", "HIGH",
                   "Quarterly options expiration (Triple Witching)", 1.5),
    ScheduledEvent("Options Expiry", "2026-04-17", "16:00", "market", "MEDIUM",
                   "Monthly equity options expiration", 1.2),

    # Geopolitical (Known scheduled events)
    ScheduledEvent("G20 Summit", "2026-11-21", None, "geopolitical", "MEDIUM",
                   "G20 Leaders Summit - South Africa", 1.4),

    # Gold-specific
    ScheduledEvent("COMEX Gold Expiry", "2026-02-25", "13:30", "market", "MEDIUM",
                   "February gold futures last trading day", 1.6),
    ScheduledEvent("COMEX Gold Expiry", "2026-04-28", "13:30", "market", "MEDIUM",
                   "April gold futures last trading day", 1.6),
]


@dataclass
class EventCalendarOutput:
    """Event calendar analysis output."""
    upcoming_events: List[ScheduledEvent]
    weekend_events: List[ScheduledEvent]
    friday_events: List[ScheduledEvent]
    next_high_impact: Optional[ScheduledEvent]
    event_calendar_score: float  # 0-10 contribution to WRS
    interpretation: str


def analyze_event_calendar(
    reference_date: datetime = None,
    lookahead_days: int = 7,
) -> EventCalendarOutput:
    """
    Analyze upcoming events and compute weekend risk contribution.

    Args:
        reference_date: Date to analyze from (default: now)
        lookahead_days: How many days ahead to look

    Returns:
        EventCalendarOutput with events and WRS contribution
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Filter to upcoming events
    upcoming = []
    for event in EVENTS_2026:
        days = event.days_until
        if 0 <= days <= lookahead_days:
            upcoming.append(event)

    # Sort by date
    upcoming.sort(key=lambda e: e.datetime_obj)

    # Find weekend events
    weekend_events = [e for e in upcoming if e.is_this_weekend]

    # Find Friday events (affect weekend positioning)
    friday_events = [e for e in upcoming if e.is_friday and e.days_until <= 5]

    # Find next high-impact event
    high_impact = [e for e in upcoming if e.impact == "HIGH"]
    next_high = high_impact[0] if high_impact else None

    # Compute event calendar score (0-10)
    score = 0.0

    # Weekend events are highest weight
    for event in weekend_events:
        if event.impact == "HIGH":
            score += 4.0 * event.gold_sensitivity
        elif event.impact == "MEDIUM":
            score += 2.0 * event.gold_sensitivity
        else:
            score += 1.0 * event.gold_sensitivity

    # Friday events also contribute (positioning before weekend)
    for event in friday_events:
        if event.impact == "HIGH":
            score += 2.5 * event.gold_sensitivity
        elif event.impact == "MEDIUM":
            score += 1.5 * event.gold_sensitivity
        else:
            score += 0.5 * event.gold_sensitivity

    # Events in next 3 days contribute less
    for event in upcoming:
        if event not in weekend_events and event not in friday_events:
            if event.days_until <= 3:
                if event.impact == "HIGH":
                    score += 1.0 * event.gold_sensitivity
                elif event.impact == "MEDIUM":
                    score += 0.5 * event.gold_sensitivity

    # Cap at 10
    score = min(10.0, score)

    # Interpretation
    if score >= 7:
        interp = f"⚠️ HIGH EVENT RISK: {len(weekend_events)} weekend events, {len(friday_events)} Friday events. Elevated gap probability."
    elif score >= 4:
        interp = f"Moderate event risk: {len(upcoming)} events in next {lookahead_days} days. Watch positioning."
    elif score >= 1:
        interp = f"Low event risk: {len(upcoming)} minor events upcoming."
    else:
        interp = "No significant scheduled events in near term."

    if next_high:
        interp += f" Next major: {next_high.name} on {next_high.date}."

    return EventCalendarOutput(
        upcoming_events=upcoming,
        weekend_events=weekend_events,
        friday_events=friday_events,
        next_high_impact=next_high,
        event_calendar_score=score,
        interpretation=interp,
    )


def get_events_for_api() -> dict:
    """Get event calendar data formatted for API response."""
    result = analyze_event_calendar()

    return {
        "event_calendar_score": result.event_calendar_score,
        "interpretation": result.interpretation,
        "upcoming_events": [
            {
                "name": e.name,
                "date": e.date,
                "time": e.time,
                "category": e.category,
                "impact": e.impact,
                "description": e.description,
                "days_until": e.days_until,
            }
            for e in result.upcoming_events
        ],
        "weekend_events": [
            {
                "name": e.name,
                "date": e.date,
                "impact": e.impact,
            }
            for e in result.weekend_events
        ],
        "friday_events": [
            {
                "name": e.name,
                "date": e.date,
                "impact": e.impact,
            }
            for e in result.friday_events
        ],
        "next_high_impact": {
            "name": result.next_high_impact.name,
            "date": result.next_high_impact.date,
            "days_until": result.next_high_impact.days_until,
        } if result.next_high_impact else None,
    }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    result = analyze_event_calendar()

    print("=" * 60)
    print("  AURUM EVENT CALENDAR")
    print("=" * 60)
    print(f"\n  Event Score: {result.event_calendar_score:.1f} / 10")
    print(f"  {result.interpretation}")

    print(f"\n  Upcoming Events ({len(result.upcoming_events)}):")
    for event in result.upcoming_events[:10]:
        impact_icon = "🔴" if event.impact == "HIGH" else "🟡" if event.impact == "MEDIUM" else "⚪"
        print(f"    {impact_icon} {event.date} | {event.name} ({event.category})")
        print(f"       {event.description}")

    if result.weekend_events:
        print(f"\n  ⚠️  WEEKEND EVENTS:")
        for event in result.weekend_events:
            print(f"    - {event.name} on {event.date}")

    if result.friday_events:
        print(f"\n  📅 FRIDAY EVENTS (affects positioning):")
        for event in result.friday_events:
            print(f"    - {event.name} on {event.date}")
