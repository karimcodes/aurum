"""
AURUM API Routers
"""
from .analysis import router as analysis_router
from .history import router as history_router
from .backtest import router as backtest_router
from .trades import router as trades_router
from .nlp import router as nlp_router

__all__ = [
    'analysis_router',
    'history_router',
    'backtest_router',
    'trades_router',
    'nlp_router',
]
