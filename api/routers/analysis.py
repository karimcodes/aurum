"""
AURUM Analysis API Router
Endpoints for running live and demo analysis.
"""

import sys
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.database import get_db
from db import crud
from api.schemas import AnalysisResponse, RegimeInfo, TradeRecommendation

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


def parse_timestamp(ts) -> datetime:
    """Parse timestamp from various formats."""
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        # Handle demo format like "2026-02-13 (DEMO)"
        clean_ts = ts.split(' (')[0].strip()
        try:
            return datetime.fromisoformat(clean_ts)
        except ValueError:
            pass
        try:
            return datetime.strptime(clean_ts, '%Y-%m-%d')
        except ValueError:
            pass
    return datetime.now()


def run_analysis(demo: bool = False, date: str = None) -> dict:
    """
    Run the AURUM analysis engine.
    Returns raw analysis data.
    """
    from data.fetcher import fetch_data, generate_demo_data
    from run import compute_wrs, compute_metals_regime, compute_trade_recommendation

    # Get data
    if demo:
        data = generate_demo_data()
    else:
        data = fetch_data(lookback_days=365, date=date)

    if not data.prices:
        raise HTTPException(status_code=503, detail="Unable to fetch market data")

    # Compute WRS
    wrs_result = compute_wrs(data)
    wrs = wrs_result['wrs']

    # Compute regime
    regime_result = compute_metals_regime(data)
    sra = regime_result['sra']

    # Adjusted WRS
    adjusted_wrs = max(0, min(100, wrs + sra))

    # Get trade recommendation
    trade = compute_trade_recommendation(adjusted_wrs, data)

    return {
        'timestamp': data.timestamp,
        'wrs_score': wrs,
        'adjusted_wrs': adjusted_wrs,
        'signals': wrs_result['components'],
        'warnings': wrs_result['warnings'],
        'regime': regime_result,
        'recommendation': trade,
        'market_data': {
            'gold_price': data.gold_price,
            'silver_price': data.silver_price,
            'vix': data.vix,
            'vxx': data.vxx,
            'gold_silver_ratio': data.gold_silver_ratio,
            'gold_rv_21d': data.gold_rv_21d,
        },
        'data': data,  # Keep for recording
    }


@router.get("/current", response_model=AnalysisResponse)
async def get_current_analysis():
    """
    Run full AURUM analysis with live market data.
    This fetches current prices from Yahoo Finance.
    """
    result = run_analysis(demo=False)

    return AnalysisResponse(
        timestamp=parse_timestamp(result['timestamp']),
        wrs_score=result['wrs_score'],
        adjusted_wrs=result['adjusted_wrs'],
        signals=result['signals'],
        warnings=result['warnings'],
        regime=RegimeInfo(**result['regime']),
        recommendation=TradeRecommendation(**result['recommendation']),
        market_data=result['market_data'],
    )


@router.get("/demo", response_model=AnalysisResponse)
async def get_demo_analysis():
    """
    Run AURUM analysis with simulated demo data.
    Use this for testing without internet connection.
    """
    result = run_analysis(demo=True)

    return AnalysisResponse(
        timestamp=parse_timestamp(result['timestamp']),
        wrs_score=result['wrs_score'],
        adjusted_wrs=result['adjusted_wrs'],
        signals=result['signals'],
        warnings=result['warnings'],
        regime=RegimeInfo(**result['regime']),
        recommendation=TradeRecommendation(**result['recommendation']),
        market_data=result['market_data'],
    )


@router.get("/historical/{date}")
async def get_historical_analysis(date: str):
    """
    Run AURUM analysis for a historical date.
    Date format: YYYY-MM-DD (must be a Friday).
    """
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    result = run_analysis(demo=False, date=date)

    return AnalysisResponse(
        timestamp=parse_timestamp(result['timestamp']),
        wrs_score=result['wrs_score'],
        adjusted_wrs=result['adjusted_wrs'],
        signals=result['signals'],
        warnings=result['warnings'],
        regime=RegimeInfo(**result['regime']),
        recommendation=TradeRecommendation(**result['recommendation']),
        market_data=result['market_data'],
    )


@router.post("/record")
async def record_analysis(db: Session = Depends(get_db)):
    """
    Run current analysis and save to database.
    Use this on Friday afternoon to record the week's analysis.
    """
    result = run_analysis(demo=False)

    # Save to database
    wrs_history = crud.create_wrs_history(
        db=db,
        date=datetime.now(),
        wrs_score=result['wrs_score'],
        regime_state=result['regime']['regime'],
        metals_regime=result['regime']['regime'],
        signals_json=result['signals'],
        recommendation=result['recommendation']['action'],
        gold_price=result['market_data']['gold_price'],
        silver_price=result['market_data']['silver_price'],
        vix=result['market_data']['vix'],
    )

    return {
        "message": "Analysis recorded successfully",
        "id": wrs_history.id,
        "wrs_score": result['wrs_score'],
        "recommendation": result['recommendation']['action'],
    }
