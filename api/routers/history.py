"""
AURUM History API Router
Endpoints for WRS history and outcome tracking.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from api.schemas import (
    WRSHistoryResponse,
    WRSHistoryCreate,
    OutcomeResponse,
    OutcomeCreate,
    WRSWithOutcomeResponse,
    OutcomeStats,
)

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("/wrs", response_model=List[WRSHistoryResponse])
async def get_wrs_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    regime: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get WRS history records with optional filters.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **start_date**: Filter records after this date
    - **end_date**: Filter records before this date
    - **regime**: Filter by regime state (e.g., "MACRO_STRESS")
    """
    records = crud.get_wrs_history(
        db=db,
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        regime=regime,
    )
    return records


@router.get("/wrs/latest", response_model=WRSHistoryResponse)
async def get_latest_wrs(db: Session = Depends(get_db)):
    """Get the most recent WRS history record."""
    record = crud.get_latest_wrs(db)
    if not record:
        raise HTTPException(status_code=404, detail="No WRS history found")
    return record


@router.get("/wrs/{wrs_id}", response_model=WRSWithOutcomeResponse)
async def get_wrs_by_id(wrs_id: int, db: Session = Depends(get_db)):
    """Get a specific WRS history record by ID with outcome data."""
    record = crud.get_wrs_by_id(db, wrs_id)
    if not record:
        raise HTTPException(status_code=404, detail="WRS record not found")
    return record


@router.post("/wrs", response_model=WRSHistoryResponse)
async def create_wrs_history(
    wrs: WRSHistoryCreate,
    db: Session = Depends(get_db),
):
    """Manually create a WRS history record."""
    record = crud.create_wrs_history(
        db=db,
        date=wrs.date,
        wrs_score=wrs.wrs_score,
        regime_state=wrs.regime_state,
        metals_regime=wrs.metals_regime,
        signals_json=wrs.signals_json,
        recommendation=wrs.recommendation,
        gold_price=wrs.gold_price,
        silver_price=wrs.silver_price,
        vix=wrs.vix,
    )
    return record


@router.get("/outcomes", response_model=List[OutcomeResponse])
async def get_outcomes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    correct_only: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    Get outcome records with optional filters.

    - **correct_only**: Filter to only correct (True) or incorrect (False) predictions
    """
    records = crud.get_outcomes(
        db=db,
        skip=skip,
        limit=limit,
        correct_only=correct_only,
    )
    return records


@router.post("/outcomes", response_model=OutcomeResponse)
async def create_outcome(
    outcome: OutcomeCreate,
    db: Session = Depends(get_db),
):
    """
    Record the outcome of a weekend (Monday prices).
    Links to an existing WRS history record.
    """
    # Verify WRS history exists
    wrs = crud.get_wrs_by_id(db, outcome.wrs_history_id)
    if not wrs:
        raise HTTPException(
            status_code=404,
            detail=f"WRS history record {outcome.wrs_history_id} not found"
        )

    record = crud.create_outcome(
        db=db,
        wrs_history_id=outcome.wrs_history_id,
        friday_gold_close=outcome.friday_gold_close,
        monday_gold_open=outcome.monday_gold_open,
    )
    return record


@router.get("/outcomes/stats", response_model=OutcomeStats)
async def get_outcome_stats(db: Session = Depends(get_db)):
    """Get aggregate outcome statistics."""
    stats = crud.get_outcome_stats(db)
    return stats


@router.get("/combined", response_model=List[WRSWithOutcomeResponse])
async def get_wrs_with_outcomes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get WRS history with joined outcome data."""
    records = crud.get_wrs_with_outcomes(db, skip=skip, limit=limit)
    return records
