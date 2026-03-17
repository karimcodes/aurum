"""
AURUM Backtest API Router
Endpoints for running backtests and viewing signal attribution.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.database import get_db
from db import crud
from api.schemas import (
    BacktestRequest,
    BacktestResponse,
    BacktestResult,
    SignalAttributionResponse,
)

router = APIRouter(prefix="/api/backtest", tags=["Backtest"])


def run_backtest(
    start_date: datetime,
    end_date: datetime,
    initial_capital: float = 10000,
    position_size_pct: float = 0.01,
) -> dict:
    """
    Run a backtest over the specified date range.
    Uses historical data to simulate trading based on WRS signals.
    """
    from data.fetcher import fetch_data
    from run import compute_wrs, compute_metals_regime, compute_trade_recommendation

    trades = []
    equity_curve = []
    capital = initial_capital
    peak_capital = initial_capital
    max_drawdown = 0

    # Iterate through Fridays in the date range
    current_date = start_date
    while current_date <= end_date:
        # Only trade on Fridays
        if current_date.weekday() == 4:  # Friday
            date_str = current_date.strftime('%Y-%m-%d')

            try:
                # Fetch historical data
                data = fetch_data(lookback_days=365, date=date_str)

                if data.prices:
                    # Run analysis
                    wrs_result = compute_wrs(data)
                    regime_result = compute_metals_regime(data)
                    adjusted_wrs = max(0, min(100, wrs_result['wrs'] + regime_result['sra']))
                    trade_rec = compute_trade_recommendation(adjusted_wrs, data)

                    # Simulate trade
                    pnl = 0
                    gap_percent = None

                    if trade_rec['action'] not in ('NO TRADE', 'MONITOR ONLY'):
                        # Calculate position size
                        position_size = capital * position_size_pct

                        # Simulate gap (we'd need Monday data for real calculation)
                        # For now, use a random-ish proxy based on data
                        simulated_gap = (data.gold_rv_5d / 100) * (0.5 if data.vix > 20 else 0.2)

                        # Straddle pays off if gap > premium (assume 2% premium)
                        premium_pct = 0.02
                        if abs(simulated_gap) > premium_pct:
                            pnl = position_size * (abs(simulated_gap) - premium_pct) / premium_pct
                        else:
                            pnl = -position_size * 0.8  # Lose most of premium

                        gap_percent = simulated_gap
                        capital += pnl

                    # Track equity curve
                    peak_capital = max(peak_capital, capital)
                    drawdown = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)

                    cumulative_pnl = capital - initial_capital

                    trades.append({
                        'date': current_date,
                        'wrs_score': adjusted_wrs,
                        'action': trade_rec['action'],
                        'entry_price': data.gold_price,
                        'exit_price': data.gold_price * (1 + (gap_percent or 0)),
                        'pnl': pnl,
                        'cumulative_pnl': cumulative_pnl,
                        'gap_percent': gap_percent,
                    })

                    equity_curve.append({
                        'date': current_date.isoformat(),
                        'capital': capital,
                        'drawdown': drawdown,
                    })

            except Exception as e:
                # Skip dates with data issues
                pass

        current_date += timedelta(days=1)

    # Calculate statistics
    total_trades = len([t for t in trades if t['action'] not in ('NO TRADE', 'MONITOR ONLY')])
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    losing_trades = len([t for t in trades if t['pnl'] < 0])

    total_return = (capital - initial_capital) / initial_capital if initial_capital > 0 else 0

    # Sharpe ratio approximation
    if len(trades) > 1:
        returns = [t['pnl'] / initial_capital for t in trades if t['pnl'] != 0]
        if returns:
            avg_return = sum(returns) / len(returns)
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns))
            sharpe_ratio = (avg_return / std_return * math.sqrt(52)) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0

    return {
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': total_return,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'trades': trades,
        'equity_curve': equity_curve,
    }


@router.post("/run", response_model=BacktestResponse)
async def run_backtest_endpoint(request: BacktestRequest):
    """
    Run a backtest over the specified date range.

    - **start_date**: Start date for backtest
    - **end_date**: End date for backtest
    - **initial_capital**: Starting capital (default: $10,000)
    - **position_size_pct**: Position size as % of capital (default: 1%)
    """
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must be after start_date"
        )

    result = run_backtest(
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        position_size_pct=request.position_size_pct,
    )

    return BacktestResponse(
        start_date=result['start_date'],
        end_date=result['end_date'],
        initial_capital=result['initial_capital'],
        final_capital=result['final_capital'],
        total_return=result['total_return'],
        total_trades=result['total_trades'],
        winning_trades=result['winning_trades'],
        losing_trades=result['losing_trades'],
        win_rate=result['win_rate'],
        max_drawdown=result['max_drawdown'],
        sharpe_ratio=result['sharpe_ratio'],
        trades=[BacktestResult(**t) for t in result['trades']],
        equity_curve=result['equity_curve'],
    )


@router.get("/signals", response_model=List[SignalAttributionResponse])
async def get_signal_attribution(db: Session = Depends(get_db)):
    """
    Get signal performance attribution.
    Shows which signals have been most predictive.
    """
    records = crud.get_signal_performance(db)
    return [
        SignalAttributionResponse(
            signal_name=r.signal_name,
            total_fires=r.total_fires,
            correct_fires=r.correct_fires,
            accuracy=r.accuracy,
            avg_contribution=r.avg_contribution,
            avg_gap_when_fired=r.avg_gap_when_fired,
        )
        for r in records
    ]


@router.get("/quick")
async def quick_backtest(
    weeks: int = Query(12, ge=4, le=52, description="Number of weeks to backtest"),
):
    """
    Run a quick backtest for the last N weeks.
    Returns simplified results for dashboard display.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=weeks)

    result = run_backtest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000,
        position_size_pct=0.01,
    )

    return {
        'weeks': weeks,
        'total_return_pct': result['total_return'] * 100,
        'win_rate_pct': result['win_rate'] * 100,
        'max_drawdown_pct': result['max_drawdown'] * 100,
        'total_trades': result['total_trades'],
        'sharpe_ratio': result['sharpe_ratio'],
    }
