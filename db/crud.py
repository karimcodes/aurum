"""
AURUM CRUD Operations
Database operations for WRS history, outcomes, trades, and signal performance.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from .models import WRSHistory, Outcome, Trade, SignalPerformance


# ============================================================
# WRS History CRUD
# ============================================================

def create_wrs_history(
    db: Session,
    date: datetime,
    wrs_score: float,
    regime_state: str,
    metals_regime: str,
    signals_json: dict,
    recommendation: str,
    gold_price: float = None,
    silver_price: float = None,
    vix: float = None,
) -> WRSHistory:
    """Create a new WRS history record."""
    record = WRSHistory(
        date=date,
        wrs_score=wrs_score,
        regime_state=regime_state,
        metals_regime=metals_regime,
        signals_json=signals_json,
        recommendation=recommendation,
        gold_price=gold_price,
        silver_price=silver_price,
        vix=vix,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_wrs_history(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    start_date: datetime = None,
    end_date: datetime = None,
    regime: str = None,
) -> List[WRSHistory]:
    """Get WRS history records with optional filters."""
    query = db.query(WRSHistory)

    if start_date:
        query = query.filter(WRSHistory.date >= start_date)
    if end_date:
        query = query.filter(WRSHistory.date <= end_date)
    if regime:
        query = query.filter(WRSHistory.regime_state == regime)

    return query.order_by(desc(WRSHistory.date)).offset(skip).limit(limit).all()


def get_wrs_by_id(db: Session, wrs_id: int) -> Optional[WRSHistory]:
    """Get a single WRS history record by ID."""
    return db.query(WRSHistory).filter(WRSHistory.id == wrs_id).first()


def get_wrs_by_date(db: Session, target_date: date) -> Optional[WRSHistory]:
    """Get WRS history for a specific date."""
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())
    return db.query(WRSHistory).filter(
        WRSHistory.date >= start,
        WRSHistory.date <= end
    ).first()


def get_latest_wrs(db: Session) -> Optional[WRSHistory]:
    """Get the most recent WRS history record."""
    return db.query(WRSHistory).order_by(desc(WRSHistory.date)).first()


# ============================================================
# Outcome CRUD
# ============================================================

def create_outcome(
    db: Session,
    wrs_history_id: int,
    friday_gold_close: float,
    monday_gold_open: float,
) -> Outcome:
    """Create an outcome record for a WRS history entry."""
    gap_percent = (monday_gold_open - friday_gold_close) / friday_gold_close

    if gap_percent > 0.001:
        gap_direction = 'UP'
    elif gap_percent < -0.001:
        gap_direction = 'DOWN'
    else:
        gap_direction = 'FLAT'

    # Get WRS to determine if outcome was correctly predicted
    wrs = db.query(WRSHistory).filter(WRSHistory.id == wrs_history_id).first()
    outcome_correct = None
    pnl_theoretical = None

    if wrs:
        # High WRS should predict larger gaps
        high_wrs = wrs.wrs_score >= 41
        large_gap = abs(gap_percent) >= 0.005  # 0.5% gap
        outcome_correct = high_wrs == large_gap

        # Theoretical P&L for straddle strategy (simplified)
        if high_wrs:
            # Assume 2% premium for straddle
            premium_pct = 0.02
            # Profit if gap exceeds premium
            pnl_theoretical = abs(gap_percent) - premium_pct

    record = Outcome(
        wrs_history_id=wrs_history_id,
        friday_gold_close=friday_gold_close,
        monday_gold_open=monday_gold_open,
        gap_percent=gap_percent,
        gap_direction=gap_direction,
        outcome_correct=outcome_correct,
        pnl_theoretical=pnl_theoretical,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_outcomes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    correct_only: bool = None,
) -> List[Outcome]:
    """Get outcome records with optional filters."""
    query = db.query(Outcome)

    if correct_only is True:
        query = query.filter(Outcome.outcome_correct == True)
    elif correct_only is False:
        query = query.filter(Outcome.outcome_correct == False)

    return query.order_by(desc(Outcome.id)).offset(skip).limit(limit).all()


def get_outcome_stats(db: Session) -> dict:
    """Get aggregate outcome statistics."""
    total = db.query(func.count(Outcome.id)).scalar() or 0
    correct = db.query(func.count(Outcome.id)).filter(Outcome.outcome_correct == True).scalar() or 0
    avg_gap = db.query(func.avg(func.abs(Outcome.gap_percent))).scalar() or 0

    return {
        'total_outcomes': total,
        'correct_predictions': correct,
        'accuracy': correct / total if total > 0 else 0,
        'avg_gap_percent': avg_gap,
    }


# ============================================================
# Trade CRUD
# ============================================================

def create_trade(
    db: Session,
    structure: str,
    entry_date: datetime,
    entry_premium: float,
    contracts: int = 1,
    strike: str = None,
    wrs_history_id: int = None,
    notes: str = None,
) -> Trade:
    """Create a new trade record."""
    record = Trade(
        wrs_history_id=wrs_history_id,
        structure=structure,
        entry_date=entry_date,
        entry_premium=entry_premium,
        contracts=contracts,
        strike=strike,
        status='OPEN',
        notes=notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_trade(
    db: Session,
    trade_id: int,
    exit_date: datetime = None,
    exit_value: float = None,
    notes: str = None,
    status: str = None,
) -> Optional[Trade]:
    """Update an existing trade."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        return None

    if exit_date:
        trade.exit_date = exit_date
    if exit_value is not None:
        trade.exit_value = exit_value
        trade.pnl_actual = (exit_value - trade.entry_premium) * trade.contracts * 100
        if trade.entry_premium > 0:
            trade.pnl_percent = (exit_value - trade.entry_premium) / trade.entry_premium
    if notes:
        trade.notes = notes
    if status:
        trade.status = status

    db.commit()
    db.refresh(trade)
    return trade


def close_trade(
    db: Session,
    trade_id: int,
    exit_date: datetime,
    exit_value: float,
    notes: str = None,
) -> Optional[Trade]:
    """Close a trade with exit details."""
    return update_trade(
        db,
        trade_id,
        exit_date=exit_date,
        exit_value=exit_value,
        notes=notes,
        status='CLOSED',
    )


def get_trades(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: str = None,
) -> List[Trade]:
    """Get trade records with optional status filter."""
    query = db.query(Trade)

    if status:
        query = query.filter(Trade.status == status)

    return query.order_by(desc(Trade.entry_date)).offset(skip).limit(limit).all()


def get_trade_by_id(db: Session, trade_id: int) -> Optional[Trade]:
    """Get a single trade by ID."""
    return db.query(Trade).filter(Trade.id == trade_id).first()


def get_trade_stats(db: Session) -> dict:
    """Get aggregate trade statistics."""
    total = db.query(func.count(Trade.id)).scalar() or 0
    closed = db.query(func.count(Trade.id)).filter(Trade.status == 'CLOSED').scalar() or 0

    wins = db.query(func.count(Trade.id)).filter(
        Trade.status == 'CLOSED',
        Trade.pnl_actual > 0
    ).scalar() or 0

    total_pnl = db.query(func.sum(Trade.pnl_actual)).filter(
        Trade.status == 'CLOSED'
    ).scalar() or 0

    avg_pnl = db.query(func.avg(Trade.pnl_actual)).filter(
        Trade.status == 'CLOSED'
    ).scalar() or 0

    return {
        'total_trades': total,
        'closed_trades': closed,
        'open_trades': total - closed,
        'winning_trades': wins,
        'win_rate': wins / closed if closed > 0 else 0,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
    }


# ============================================================
# Signal Performance CRUD
# ============================================================

def update_signal_performance(
    db: Session,
    signal_name: str,
    fired: bool,
    contribution: float,
    correct: bool = None,
    gap_percent: float = None,
) -> SignalPerformance:
    """Update signal performance metrics."""
    record = db.query(SignalPerformance).filter(
        SignalPerformance.signal_name == signal_name
    ).first()

    if not record:
        record = SignalPerformance(signal_name=signal_name)
        db.add(record)

    if fired:
        record.total_fires += 1
        # Update running average contribution
        record.avg_contribution = (
            (record.avg_contribution * (record.total_fires - 1) + contribution)
            / record.total_fires
        )

        if correct is not None and correct:
            record.correct_fires += 1

        if gap_percent is not None:
            record.avg_gap_when_fired = (
                (record.avg_gap_when_fired * (record.total_fires - 1) + abs(gap_percent))
                / record.total_fires
            )

    db.commit()
    db.refresh(record)
    return record


def get_signal_performance(db: Session) -> List[SignalPerformance]:
    """Get all signal performance records."""
    return db.query(SignalPerformance).order_by(
        desc(SignalPerformance.total_fires)
    ).all()


def get_signal_by_name(db: Session, signal_name: str) -> Optional[SignalPerformance]:
    """Get a single signal performance record."""
    return db.query(SignalPerformance).filter(
        SignalPerformance.signal_name == signal_name
    ).first()


# ============================================================
# Aggregate Queries
# ============================================================

def get_wrs_with_outcomes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> List[WRSHistory]:
    """Get WRS history with joined outcomes."""
    return db.query(WRSHistory).outerjoin(Outcome).order_by(
        desc(WRSHistory.date)
    ).offset(skip).limit(limit).all()


def get_performance_summary(db: Session) -> dict:
    """Get overall performance summary."""
    outcome_stats = get_outcome_stats(db)
    trade_stats = get_trade_stats(db)

    latest_wrs = get_latest_wrs(db)

    return {
        'prediction_accuracy': outcome_stats['accuracy'],
        'total_predictions': outcome_stats['total_outcomes'],
        'win_rate': trade_stats['win_rate'],
        'total_pnl': trade_stats['total_pnl'],
        'total_trades': trade_stats['total_trades'],
        'latest_wrs': latest_wrs.wrs_score if latest_wrs else None,
        'latest_regime': latest_wrs.regime_state if latest_wrs else None,
    }
