"""
AURUM Trades API Router
Endpoints for trade journal management.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from api.schemas import (
    TradeResponse,
    TradeCreate,
    TradeUpdate,
    TradeStats,
    PerformanceStats,
)

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("", response_model=List[TradeResponse])
async def get_trades(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status: OPEN, CLOSED, EXPIRED"),
    db: Session = Depends(get_db),
):
    """
    Get all trades with optional status filter.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by trade status
    """
    records = crud.get_trades(
        db=db,
        skip=skip,
        limit=limit,
        status=status,
    )
    return records


@router.get("/stats", response_model=TradeStats)
async def get_trade_stats(db: Session = Depends(get_db)):
    """Get aggregate trade statistics."""
    stats = crud.get_trade_stats(db)
    return TradeStats(**stats)


@router.get("/summary", response_model=PerformanceStats)
async def get_performance_summary(db: Session = Depends(get_db)):
    """Get overall performance summary combining predictions and trades."""
    summary = crud.get_performance_summary(db)
    return PerformanceStats(**summary)


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get a specific trade by ID."""
    trade = crud.get_trade_by_id(db, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("", response_model=TradeResponse)
async def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    """
    Log a new trade.

    - **structure**: Option structure (e.g., "GLD ATM straddle")
    - **entry_date**: Date/time of entry
    - **entry_premium**: Premium paid per contract
    - **contracts**: Number of contracts
    - **strike**: Strike price(s)
    - **wrs_history_id**: Optional link to WRS analysis
    - **notes**: Optional trade notes
    """
    record = crud.create_trade(
        db=db,
        structure=trade.structure,
        entry_date=trade.entry_date,
        entry_premium=trade.entry_premium,
        contracts=trade.contracts,
        strike=trade.strike,
        wrs_history_id=trade.wrs_history_id,
        notes=trade.notes,
    )
    return record


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_update: TradeUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing trade.
    Use this to add exit details, update notes, or change status.
    """
    trade = crud.update_trade(
        db=db,
        trade_id=trade_id,
        exit_date=trade_update.exit_date,
        exit_value=trade_update.exit_value,
        notes=trade_update.notes,
        status=trade_update.status,
    )
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    exit_value: float = Query(..., description="Exit value per contract"),
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Close a trade with exit details.

    - **exit_value**: Exit value per contract
    - **notes**: Optional closing notes
    """
    trade = crud.close_trade(
        db=db,
        trade_id=trade_id,
        exit_date=datetime.now(),
        exit_value=exit_value,
        notes=notes,
    )
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.delete("/{trade_id}")
async def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """Delete a trade (soft delete - marks as CANCELLED)."""
    trade = crud.update_trade(
        db=db,
        trade_id=trade_id,
        status='CANCELLED',
    )
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade cancelled", "id": trade_id}


@router.get("/open/list", response_model=List[TradeResponse])
async def get_open_trades(db: Session = Depends(get_db)):
    """Get all currently open trades."""
    return crud.get_trades(db=db, status='OPEN')
