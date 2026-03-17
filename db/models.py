"""
AURUM Database Models
SQLAlchemy ORM models for storing WRS history, outcomes, trades, and signal performance.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class WRSHistory(Base):
    """
    Stores each Friday's WRS analysis for historical tracking.
    """
    __tablename__ = 'wrs_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    wrs_score = Column(Float, nullable=False)
    regime_state = Column(String(50), nullable=False)
    metals_regime = Column(String(50), nullable=True)
    signals_json = Column(JSON, nullable=False)
    recommendation = Column(String(50), nullable=False)
    gold_price = Column(Float, nullable=True)
    silver_price = Column(Float, nullable=True)
    vix = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    outcome = relationship("Outcome", back_populates="wrs_history", uselist=False)
    trades = relationship("Trade", back_populates="wrs_history")

    def __repr__(self):
        return f"<WRSHistory(id={self.id}, date={self.date}, wrs={self.wrs_score})>"


class Outcome(Base):
    """
    Stores the actual outcome of each weekend (Monday open vs Friday close).
    Used for tracking prediction accuracy.
    """
    __tablename__ = 'outcomes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    wrs_history_id = Column(Integer, ForeignKey('wrs_history.id'), nullable=False, unique=True)
    friday_gold_close = Column(Float, nullable=False)
    monday_gold_open = Column(Float, nullable=False)
    gap_percent = Column(Float, nullable=False)
    gap_direction = Column(String(10), nullable=False)  # 'UP', 'DOWN', 'FLAT'
    outcome_correct = Column(Boolean, nullable=True)  # Did WRS correctly predict risk?
    pnl_theoretical = Column(Float, nullable=True)  # Theoretical P&L if traded
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    wrs_history = relationship("WRSHistory", back_populates="outcome")

    def __repr__(self):
        return f"<Outcome(id={self.id}, gap={self.gap_percent:.2%}, direction={self.gap_direction})>"


class Trade(Base):
    """
    Stores actual trades taken based on AURUM recommendations.
    Tracks entry/exit and actual P&L.
    """
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    wrs_history_id = Column(Integer, ForeignKey('wrs_history.id'), nullable=True)
    structure = Column(String(100), nullable=False)  # e.g., "GLD ATM straddle"
    entry_date = Column(DateTime, nullable=False)
    entry_premium = Column(Float, nullable=False)
    contracts = Column(Integer, nullable=False, default=1)
    strike = Column(String(50), nullable=True)
    exit_date = Column(DateTime, nullable=True)
    exit_value = Column(Float, nullable=True)
    pnl_actual = Column(Float, nullable=True)
    pnl_percent = Column(Float, nullable=True)
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED, EXPIRED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    wrs_history = relationship("WRSHistory", back_populates="trades")

    def __repr__(self):
        return f"<Trade(id={self.id}, structure={self.structure}, status={self.status})>"


class SignalPerformance(Base):
    """
    Tracks performance attribution for each signal component.
    Used for identifying which signals are most predictive.
    """
    __tablename__ = 'signal_performance'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_name = Column(String(50), nullable=False, unique=True)
    total_fires = Column(Integer, default=0)  # Times signal was non-zero
    correct_fires = Column(Integer, default=0)  # Times it correctly predicted gap
    avg_contribution = Column(Float, default=0.0)  # Average score contribution when fired
    avg_gap_when_fired = Column(Float, default=0.0)  # Average gap % when signal fired
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def accuracy(self) -> float:
        """Calculate signal accuracy."""
        if self.total_fires == 0:
            return 0.0
        return self.correct_fires / self.total_fires

    def __repr__(self):
        return f"<SignalPerformance(signal={self.signal_name}, accuracy={self.accuracy:.1%})>"
