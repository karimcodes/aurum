"""
AURUM API Pydantic Schemas
Request and response models for the API.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Analysis Schemas
# ============================================================

class SignalScore(BaseModel):
    """Individual signal component score."""
    name: str
    value: float
    max_value: float
    description: Optional[str] = None


class RegimeInfo(BaseModel):
    """Market regime classification."""
    regime: str
    sra: float
    gold_rank: int
    stack_of: int
    dispersion: float
    stack_returns: List[tuple]


class TradeRecommendation(BaseModel):
    """Trade recommendation from WRS analysis."""
    action: str
    reason: str
    instrument: Optional[str] = None
    structure: Optional[str] = None
    strike: Optional[Any] = None
    premium: Optional[Any] = None
    contracts: int = 0
    max_loss: Optional[Any] = None
    exit_rules: Optional[List[str]] = None


class AnalysisResponse(BaseModel):
    """Full analysis response."""
    timestamp: datetime
    wrs_score: float
    adjusted_wrs: float
    signals: Dict[str, float]
    warnings: List[str]
    regime: RegimeInfo
    recommendation: TradeRecommendation
    market_data: Dict[str, Any]

    class Config:
        from_attributes = True


# ============================================================
# History Schemas
# ============================================================

class WRSHistoryBase(BaseModel):
    """Base schema for WRS history."""
    date: datetime
    wrs_score: float
    regime_state: str
    metals_regime: Optional[str] = None
    recommendation: str
    gold_price: Optional[float] = None
    silver_price: Optional[float] = None
    vix: Optional[float] = None


class WRSHistoryCreate(WRSHistoryBase):
    """Schema for creating WRS history."""
    signals_json: Dict[str, Any]


class WRSHistoryResponse(WRSHistoryBase):
    """Schema for WRS history response."""
    id: int
    signals_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class OutcomeBase(BaseModel):
    """Base schema for outcome."""
    friday_gold_close: float
    monday_gold_open: float


class OutcomeCreate(OutcomeBase):
    """Schema for creating outcome."""
    wrs_history_id: int


class OutcomeResponse(BaseModel):
    """Schema for outcome response."""
    id: int
    wrs_history_id: int
    friday_gold_close: float
    monday_gold_open: float
    gap_percent: float
    gap_direction: str
    outcome_correct: Optional[bool] = None
    pnl_theoretical: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WRSWithOutcomeResponse(WRSHistoryResponse):
    """WRS history with joined outcome data."""
    outcome: Optional[OutcomeResponse] = None


# ============================================================
# Trade Schemas
# ============================================================

class TradeBase(BaseModel):
    """Base schema for trade."""
    structure: str
    entry_date: datetime
    entry_premium: float
    contracts: int = 1
    strike: Optional[str] = None
    notes: Optional[str] = None


class TradeCreate(TradeBase):
    """Schema for creating trade."""
    wrs_history_id: Optional[int] = None


class TradeUpdate(BaseModel):
    """Schema for updating trade."""
    exit_date: Optional[datetime] = None
    exit_value: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class TradeResponse(TradeBase):
    """Schema for trade response."""
    id: int
    wrs_history_id: Optional[int] = None
    exit_date: Optional[datetime] = None
    exit_value: Optional[float] = None
    pnl_actual: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Backtest Schemas
# ============================================================

class BacktestRequest(BaseModel):
    """Request for running a backtest."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000
    position_size_pct: float = 0.01  # 1% per trade


class BacktestResult(BaseModel):
    """Single backtest trade result."""
    date: datetime
    wrs_score: float
    action: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: float = 0
    cumulative_pnl: float = 0
    gap_percent: Optional[float] = None


class BacktestResponse(BaseModel):
    """Full backtest response."""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    trades: List[BacktestResult]
    equity_curve: List[Dict[str, Any]]


class SignalAttributionResponse(BaseModel):
    """Signal performance attribution."""
    signal_name: str
    total_fires: int
    correct_fires: int
    accuracy: float
    avg_contribution: float
    avg_gap_when_fired: float


# ============================================================
# Stats Schemas
# ============================================================

class PerformanceStats(BaseModel):
    """Overall performance statistics."""
    prediction_accuracy: float
    total_predictions: int
    win_rate: float
    total_pnl: float
    total_trades: int
    latest_wrs: Optional[float] = None
    latest_regime: Optional[str] = None


class OutcomeStats(BaseModel):
    """Outcome statistics."""
    total_outcomes: int
    correct_predictions: int
    accuracy: float
    avg_gap_percent: float


class TradeStats(BaseModel):
    """Trade statistics."""
    total_trades: int
    closed_trades: int
    open_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
