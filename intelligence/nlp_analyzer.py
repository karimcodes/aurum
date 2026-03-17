"""
AURUM NLP Analyzer
==================
Institutional-grade NLP analysis for gold/macro news.

Connects:
  - news_fetcher.py (real-time headlines)
  - market_intelligence.py (scoring framework)

Outputs:
  - Narrative Pressure Score (NPS)
  - Narrative Direction (escalating/stable/de-escalating)
  - Top impactful headlines
  - Velocity metrics
  - WRS contribution
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from math import exp
import re

from .news_fetcher import fetch_all_news, NewsHeadline, NewsFetchResult
from .market_intelligence import (
    Headline,
    NarrativeDirection,
    NarrativeAnalysisOutput,
    analyze_narrative,
    detect_narrative_shift,
    NarrativeShiftOutput,
)


# ============================================================
# Enhanced Gold-Specific Keyword System
# ============================================================

GOLD_KEYWORDS = {
    # Tier 1: Highest Impact - Direct gold catalysts
    'tier1_bullish': {
        'keywords': [
            'gold surge', 'gold rally', 'gold breakout', 'gold hits high',
            'bullion demand', 'gold buying', 'safe haven demand',
            'central bank gold', 'gold reserves', 'de-dollarization',
            'dollar collapse', 'currency crisis', 'inflation surge',
        ],
        'weight': 4.0,
        'direction': 'bullish',
    },
    'tier1_bearish': {
        'keywords': [
            'gold crash', 'gold selloff', 'gold plunge', 'gold tumbles',
            'rate hike', 'hawkish fed', 'strong dollar', 'risk on',
            'gold outflows', 'etf redemption',
        ],
        'weight': 3.5,
        'direction': 'bearish',
    },
    'tier1_geopolitical': {
        'keywords': [
            'war', 'invasion', 'nuclear', 'military strike', 'missile',
            'attack', 'retaliation', 'escalation', 'troops deployed',
            'conflict', 'declaration of war', 'military operation',
        ],
        'weight': 4.5,
        'direction': 'risk_escalation',
    },

    # Tier 2: High Impact - Macro catalysts
    'tier2_fed': {
        'keywords': [
            'fed rate', 'fomc', 'powell', 'rate cut', 'rate hike',
            'fed pivot', 'quantitative', 'balance sheet', 'taper',
            'hawkish', 'dovish', 'fed statement', 'fed minutes',
        ],
        'weight': 3.0,
        'direction': 'macro',
    },
    'tier2_inflation': {
        'keywords': [
            'inflation', 'cpi', 'pce', 'consumer prices', 'producer prices',
            'inflation expectations', 'stagflation', 'deflation',
        ],
        'weight': 2.5,
        'direction': 'macro',
    },
    'tier2_crisis': {
        'keywords': [
            'bank failure', 'bank run', 'credit crisis', 'liquidity crisis',
            'default', 'bankruptcy', 'contagion', 'systemic risk',
            'emergency lending', 'bailout', 'rescue',
        ],
        'weight': 4.0,
        'direction': 'risk_escalation',
    },

    # Tier 3: Moderate Impact - Context
    'tier3_central_banks': {
        'keywords': [
            'ecb', 'boj', 'pboc', 'bank of england', 'rba', 'snb',
            'central bank', 'monetary policy', 'interest rate decision',
        ],
        'weight': 2.0,
        'direction': 'macro',
    },
    'tier3_geopolitical_context': {
        'keywords': [
            'russia', 'ukraine', 'china', 'taiwan', 'iran', 'israel',
            'middle east', 'north korea', 'sanctions', 'tariff',
            'trade war', 'embargo', 'nato',
        ],
        'weight': 2.0,
        'direction': 'geopolitical',
    },
    'tier3_market': {
        'keywords': [
            'vix', 'volatility', 'selloff', 'crash', 'correction',
            'bear market', 'risk off', 'flight to safety',
        ],
        'weight': 2.0,
        'direction': 'risk',
    },

    # De-escalation keywords (reduce score)
    'deescalation': {
        'keywords': [
            'ceasefire', 'peace talks', 'agreement', 'deal reached',
            'resolution', 'de-escalation', 'withdrawal', 'truce',
            'negotiations', 'diplomatic solution', 'tensions ease',
            'crisis averted', 'stabilization', 'calm',
        ],
        'weight': -2.5,
        'direction': 'deescalation',
    },
}

# Source credibility weights
SOURCE_WEIGHTS = {
    'reuters': 1.3,
    'bloomberg': 1.3,
    'nyt': 1.3,  # New York Times
    'new york times': 1.3,
    'wsj': 1.2,
    'financial times': 1.2,
    'cnbc': 1.0,
    'marketwatch': 1.0,
    'kitco': 1.1,  # Gold-specific source
    'bbc': 1.0,
    'yahoo': 0.9,
    'default': 0.8,
}


@dataclass
class KeywordMatch:
    """Single keyword match in a headline."""
    keyword: str
    category: str
    weight: float
    direction: str
    headline: str
    source: str
    timestamp: float


@dataclass
class NLPAnalysisResult:
    """Complete NLP analysis result."""
    # Scores
    narrative_pressure_score: float  # 0-12 for WRS
    raw_score: float
    direction: str  # 'escalating', 'stable', 'de_escalating'

    # Velocity
    velocity_1h: float
    velocity_6h: float
    velocity_24h: float
    velocity_ratio: float  # 1h / 24h

    # Counts
    total_headlines: int
    relevant_headlines: int
    escalation_count: int
    deescalation_count: int

    # Top matches
    top_headlines: List[Tuple[str, float, str]]  # (headline, score, source)
    keyword_matches: List[KeywordMatch]

    # Shift detection
    shift_detected: bool
    shift_type: str
    dominant_theme: str

    # WRS contribution
    wrs_contribution: float  # Final points for WRS
    interpretation: str

    # Raw data
    fetch_result: Optional[NewsFetchResult] = None


def get_source_weight(source: str) -> float:
    """Get credibility weight for a news source."""
    source_lower = source.lower()
    for key, weight in SOURCE_WEIGHTS.items():
        if key in source_lower:
            return weight
    return SOURCE_WEIGHTS['default']


def analyze_headline(headline: NewsHeadline, current_time: float) -> List[KeywordMatch]:
    """Analyze a single headline for keyword matches."""
    matches = []
    text_lower = headline.text.lower()

    for category, config in GOLD_KEYWORDS.items():
        for keyword in config['keywords']:
            if keyword in text_lower:
                matches.append(KeywordMatch(
                    keyword=keyword,
                    category=category,
                    weight=config['weight'],
                    direction=config['direction'],
                    headline=headline.text,
                    source=headline.source,
                    timestamp=headline.timestamp,
                ))
                break  # One match per category per headline

    return matches


def compute_nlp_score(
    headlines: List[NewsHeadline],
    current_time: float = None,
    decay_halflife_hours: float = 6.0,
) -> NLPAnalysisResult:
    """
    Compute NLP score from headlines.

    Uses time-decay weighting and source credibility.
    """
    if current_time is None:
        current_time = time.time()

    all_matches = []
    headline_scores = []
    escalation_count = 0
    deescalation_count = 0

    # Analyze each headline
    for headline in headlines:
        matches = analyze_headline(headline, current_time)
        if not matches:
            continue

        age_hours = (current_time - headline.timestamp) / 3600
        if age_hours < 0 or age_hours > 48:
            continue

        # Time decay
        decay = exp(-0.693 * age_hours / decay_halflife_hours)

        # Source weight
        source_weight = get_source_weight(headline.source)

        # Compute headline score
        headline_score = 0
        for match in matches:
            contribution = match.weight * decay * source_weight
            headline_score += contribution

            if match.direction == 'risk_escalation' or match.direction == 'bullish':
                escalation_count += 1
            elif match.direction == 'deescalation':
                deescalation_count += 1

            all_matches.append(match)

        headline_scores.append((headline.text, headline_score, headline.source, headline.timestamp))

    # Sort by score
    headline_scores.sort(key=lambda x: abs(x[1]), reverse=True)
    top_headlines = [(h[0][:100], h[1], h[2]) for h in headline_scores[:10]]

    # Raw score (sum of all contributions)
    raw_score = sum(h[1] for h in headline_scores)

    # Velocity calculations
    def count_in_window(hours: float) -> int:
        cutoff = current_time - (hours * 3600)
        return sum(1 for h in headlines if h.timestamp >= cutoff)

    count_1h = count_in_window(1)
    count_6h = count_in_window(6)
    count_24h = count_in_window(24)

    velocity_1h = count_1h / 1.0
    velocity_6h = count_6h / 6.0
    velocity_24h = count_24h / 24.0 if count_24h > 0 else 0.1

    velocity_ratio = velocity_1h / max(velocity_24h, 0.01)

    # Determine direction
    net_direction = escalation_count - (deescalation_count * 0.6)
    if net_direction > 3:
        direction = 'escalating'
    elif net_direction < -2:
        direction = 'de_escalating'
    else:
        direction = 'stable'

    # Detect dominant theme
    theme_counts = {}
    for match in all_matches:
        theme = match.category.split('_')[0]  # tier1, tier2, tier3
        direction = match.direction
        key = f"{theme}_{direction}"
        theme_counts[key] = theme_counts.get(key, 0) + 1

    dominant_theme = max(theme_counts.items(), key=lambda x: x[1])[0] if theme_counts else 'none'

    # Shift detection
    shift_detected = velocity_ratio > 2.5
    shift_type = 'ACCELERATION' if shift_detected else 'NONE'
    if shift_detected and velocity_ratio > 4.0:
        shift_type = 'MAJOR_ACCELERATION'

    # Cap score for WRS (0-12)
    nps_capped = max(0, min(12, raw_score / 3))  # Scale down

    # WRS contribution (can be negative for de-escalation)
    if direction == 'de_escalating':
        wrs_contribution = max(-5, nps_capped * -0.5)
    else:
        wrs_contribution = nps_capped

    # Add shift bonus
    if shift_detected:
        wrs_contribution += 3 if velocity_ratio > 4.0 else 1.5

    wrs_contribution = max(-5, min(15, wrs_contribution))

    # Interpretation
    if direction == 'escalating' and nps_capped > 6:
        interp = f"HIGH ALERT: Narrative escalating ({escalation_count} risk headlines). Velocity {velocity_ratio:.1f}x normal. Theme: {dominant_theme}"
    elif direction == 'de_escalating':
        interp = f"De-escalation: {deescalation_count} calming headlines. Weekend gap may be muted."
    elif shift_detected:
        interp = f"VELOCITY SPIKE: {velocity_ratio:.1f}x normal rate. Something developing. Theme: {dominant_theme}"
    elif nps_capped > 3:
        interp = f"Moderate narrative pressure ({escalation_count} risk headlines). Watch for developments."
    else:
        interp = f"Low narrative pressure. {len(headlines)} headlines scanned, {len(all_matches)} keyword matches."

    return NLPAnalysisResult(
        narrative_pressure_score=nps_capped,
        raw_score=raw_score,
        direction=direction,
        velocity_1h=velocity_1h,
        velocity_6h=velocity_6h,
        velocity_24h=velocity_24h,
        velocity_ratio=velocity_ratio,
        total_headlines=len(headlines),
        relevant_headlines=len(headline_scores),
        escalation_count=escalation_count,
        deescalation_count=deescalation_count,
        top_headlines=top_headlines,
        keyword_matches=all_matches,
        shift_detected=shift_detected,
        shift_type=shift_type,
        dominant_theme=dominant_theme,
        wrs_contribution=wrs_contribution,
        interpretation=interp,
    )


def run_full_nlp_analysis(
    newsapi_key: str = None,
    finnhub_key: str = None,
) -> NLPAnalysisResult:
    """
    Run complete NLP analysis: fetch news and analyze.

    This is the main entry point for the NLP layer.
    """
    print("  Running NLP analysis...")

    # Fetch news
    fetch_result = fetch_all_news(
        newsapi_key=newsapi_key,
        finnhub_key=finnhub_key,
        max_age_hours=48,
        filter_relevant=True,
    )

    print(f"  Fetched {fetch_result.relevant_count} relevant headlines from {len(fetch_result.sources_succeeded)} sources")

    # Analyze
    result = compute_nlp_score(fetch_result.headlines)
    result.fetch_result = fetch_result

    return result


def format_nlp_report(result: NLPAnalysisResult) -> str:
    """Format NLP analysis as human-readable report."""
    lines = [
        "=" * 60,
        "  AURUM NLP ANALYSIS REPORT",
        "=" * 60,
        "",
        f"  NARRATIVE PRESSURE SCORE: {result.narrative_pressure_score:.1f} / 12",
        f"  WRS CONTRIBUTION: {result.wrs_contribution:+.1f} points",
        f"  DIRECTION: {result.direction.upper()}",
        "",
        f"  Headlines analyzed: {result.total_headlines}",
        f"  Relevant matches: {result.relevant_headlines}",
        f"  Escalation: {result.escalation_count} | De-escalation: {result.deescalation_count}",
        "",
        f"  VELOCITY:",
        f"    1h:  {result.velocity_1h:.1f} headlines/hour",
        f"    6h:  {result.velocity_6h:.1f} headlines/hour",
        f"    24h: {result.velocity_24h:.1f} headlines/hour",
        f"    Ratio (1h/24h): {result.velocity_ratio:.1f}x",
        "",
        f"  SHIFT: {'DETECTED - ' + result.shift_type if result.shift_detected else 'None'}",
        f"  THEME: {result.dominant_theme}",
        "",
        f"  {result.interpretation}",
        "",
        "  TOP HEADLINES:",
    ]

    for headline, score, source in result.top_headlines[:5]:
        lines.append(f"    [{source}] {headline[:70]}...")
        lines.append(f"      Score: {score:+.1f}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    result = run_full_nlp_analysis()
    print(format_nlp_report(result))
