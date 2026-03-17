"""
AURUM NLP API Router
Endpoints for news analysis and NLP insights.
"""

import sys
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

router = APIRouter(prefix="/api/nlp", tags=["NLP Analysis"])


# ============================================================
# Response Models
# ============================================================

class HeadlineResponse(BaseModel):
    """Single headline."""
    text: str
    source: str
    url: str
    age_hours: float
    category: str


class KeywordMatchResponse(BaseModel):
    """Keyword match in headline."""
    keyword: str
    category: str
    weight: float
    direction: str
    headline: str
    source: str


class NLPAnalysisResponse(BaseModel):
    """Full NLP analysis response."""
    narrative_pressure_score: float
    raw_score: float
    direction: str
    wrs_contribution: float

    velocity_1h: float
    velocity_6h: float
    velocity_24h: float
    velocity_ratio: float

    total_headlines: int
    relevant_headlines: int
    escalation_count: int
    deescalation_count: int

    shift_detected: bool
    shift_type: str
    dominant_theme: str

    top_headlines: List[dict]
    interpretation: str

    sources_succeeded: List[str]
    sources_failed: List[str]
    fetch_timestamp: str


class QuickNLPResponse(BaseModel):
    """Quick NLP summary for dashboard."""
    score: float
    direction: str
    wrs_contribution: float
    headline_count: int
    velocity_ratio: float
    shift_detected: bool
    top_headline: Optional[str]
    interpretation: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/analysis", response_model=NLPAnalysisResponse)
async def get_nlp_analysis(
    newsapi_key: Optional[str] = Query(None, description="Optional NewsAPI.org API key"),
    finnhub_key: Optional[str] = Query(None, description="Optional Finnhub.io API key"),
):
    """
    Run full NLP analysis on current news.

    Fetches from:
    - RSS feeds (always available)
    - NewsAPI (if key provided)
    - Finnhub (if key provided)

    Returns comprehensive analysis including:
    - Narrative pressure score
    - Headline velocity
    - Shift detection
    - Top headlines
    """
    try:
        from intelligence.nlp_analyzer import run_full_nlp_analysis

        result = run_full_nlp_analysis(
            newsapi_key=newsapi_key,
            finnhub_key=finnhub_key,
        )

        return NLPAnalysisResponse(
            narrative_pressure_score=result.narrative_pressure_score,
            raw_score=result.raw_score,
            direction=result.direction,
            wrs_contribution=result.wrs_contribution,
            velocity_1h=result.velocity_1h,
            velocity_6h=result.velocity_6h,
            velocity_24h=result.velocity_24h,
            velocity_ratio=result.velocity_ratio,
            total_headlines=result.total_headlines,
            relevant_headlines=result.relevant_headlines,
            escalation_count=result.escalation_count,
            deescalation_count=result.deescalation_count,
            shift_detected=result.shift_detected,
            shift_type=result.shift_type,
            dominant_theme=result.dominant_theme,
            top_headlines=[
                {"headline": h[0], "score": h[1], "source": h[2]}
                for h in result.top_headlines
            ],
            interpretation=result.interpretation,
            sources_succeeded=result.fetch_result.sources_succeeded if result.fetch_result else [],
            sources_failed=result.fetch_result.sources_failed if result.fetch_result else [],
            fetch_timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLP analysis failed: {str(e)}")


@router.get("/quick", response_model=QuickNLPResponse)
async def get_quick_nlp():
    """
    Quick NLP summary for dashboard display.
    Faster than full analysis - uses cached data if available.
    """
    try:
        from intelligence.nlp_analyzer import run_full_nlp_analysis

        result = run_full_nlp_analysis()

        top_headline = result.top_headlines[0][0] if result.top_headlines else None

        return QuickNLPResponse(
            score=result.narrative_pressure_score,
            direction=result.direction,
            wrs_contribution=result.wrs_contribution,
            headline_count=result.relevant_headlines,
            velocity_ratio=result.velocity_ratio,
            shift_detected=result.shift_detected,
            top_headline=top_headline[:100] if top_headline else None,
            interpretation=result.interpretation,
        )

    except Exception as e:
        # Return minimal response on failure
        return QuickNLPResponse(
            score=0,
            direction="unknown",
            wrs_contribution=0,
            headline_count=0,
            velocity_ratio=1.0,
            shift_detected=False,
            top_headline=None,
            interpretation=f"NLP unavailable: {str(e)}",
        )


@router.get("/headlines", response_model=List[HeadlineResponse])
async def get_headlines(
    limit: int = Query(20, ge=1, le=100),
    hours: float = Query(24, ge=1, le=72),
):
    """
    Get recent relevant headlines.

    Args:
        limit: Maximum headlines to return
        hours: Only headlines from last N hours
    """
    try:
        from intelligence.news_fetcher import fetch_all_news

        result = fetch_all_news(max_age_hours=hours, filter_relevant=True)

        headlines = []
        for h in result.headlines_by_recency[:limit]:
            headlines.append(HeadlineResponse(
                text=h.text,
                source=h.source,
                url=h.url,
                age_hours=round(h.age_hours, 1),
                category=h.category,
            ))

        return headlines

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch headlines: {str(e)}")


@router.get("/keywords")
async def get_keyword_matches(
    hours: float = Query(24, ge=1, le=72),
):
    """
    Get keyword matches from recent headlines.
    Shows which gold/macro keywords are appearing in news.
    """
    try:
        from intelligence.nlp_analyzer import run_full_nlp_analysis

        result = run_full_nlp_analysis()

        # Group matches by category
        categories = {}
        for match in result.keyword_matches:
            cat = match.category
            if cat not in categories:
                categories[cat] = {
                    'count': 0,
                    'keywords': [],
                    'direction': match.direction,
                }
            categories[cat]['count'] += 1
            if match.keyword not in categories[cat]['keywords']:
                categories[cat]['keywords'].append(match.keyword)

        return {
            'total_matches': len(result.keyword_matches),
            'categories': categories,
            'dominant_theme': result.dominant_theme,
            'escalation_count': result.escalation_count,
            'deescalation_count': result.deescalation_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze keywords: {str(e)}")


@router.get("/velocity")
async def get_velocity_chart():
    """
    Get headline velocity data for charting.
    Returns hourly headline counts for last 24 hours.
    """
    try:
        from intelligence.news_fetcher import fetch_all_news
        import time

        result = fetch_all_news(max_age_hours=24, filter_relevant=True)

        # Bucket by hour
        now = time.time()
        hourly_counts = []

        for hour_offset in range(24):
            start = now - ((hour_offset + 1) * 3600)
            end = now - (hour_offset * 3600)
            count = sum(1 for h in result.headlines if start <= h.timestamp < end)
            hourly_counts.append({
                'hour': f"-{hour_offset}h",
                'count': count,
            })

        hourly_counts.reverse()

        return {
            'hourly_counts': hourly_counts,
            'total_24h': len(result.headlines),
            'avg_per_hour': len(result.headlines) / 24,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute velocity: {str(e)}")


@router.get("/events")
async def get_event_calendar():
    """
    Get upcoming scheduled events that could impact weekend gold gaps.

    Returns:
    - Event calendar score (0-10)
    - Upcoming events (FOMC, CPI, G20, etc.)
    - Weekend events
    - Friday events (affect positioning)
    """
    try:
        from intelligence.event_calendar import get_events_for_api
        return get_events_for_api()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get events: {str(e)}")
