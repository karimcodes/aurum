"""
AURUM FastAPI Application
Main entry point for the API server.

Usage:
    python -m api.main              # Start the API server
    uvicorn api.main:app --reload   # Development mode with hot reload

API Documentation:
    http://localhost:8000/docs      # Swagger UI
    http://localhost:8000/redoc     # ReDoc
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db
from api.routers import analysis_router, history_router, backtest_router, trades_router, nlp_router

# Initialize FastAPI app
app = FastAPI(
    title="AURUM API",
    description="""
    Weekend Macro Convexity Engine API

    AURUM analyzes weekend risk premium in gold markets and generates
    trade recommendations for options strategies.

    ## Features

    - **Analysis**: Run live or demo WRS analysis
    - **History**: Track historical WRS scores and outcomes
    - **Backtest**: Run backtests over historical data
    - **Trades**: Trade journal for logging actual trades
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis_router)
app.include_router(history_router)
app.include_router(backtest_router)
app.include_router(trades_router)
app.include_router(nlp_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("AURUM API started. Database initialized.")


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "AURUM API",
        "version": "0.1.0",
        "description": "Weekend Macro Convexity Engine",
        "docs": "/docs",
        "endpoints": {
            "analysis": "/api/analysis",
            "history": "/api/history",
            "backtest": "/api/backtest",
            "trades": "/api/trades",
            "nlp": "/api/nlp",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/stats/summary")
async def get_stats_summary():
    """
    Get overall performance summary.
    Redirects to trades summary endpoint.
    """
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from db.database import get_db
    from db import crud

    # Get a database session
    from db.database import SessionLocal
    db = SessionLocal()
    try:
        summary = crud.get_performance_summary(db)
        return summary
    finally:
        db.close()


# Run with uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
