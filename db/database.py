"""
AURUM Database Connection & Session Management
Uses SQLite for simplicity - file-based, no setup required.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from .models import Base

# Database file location - in the aurum directory
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'aurum.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with SQLite optimizations
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Allow multi-threaded access
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize the database, creating all tables if they don't exist.
    Safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency for FastAPI routes - yields a database session.
    Ensures session is properly closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Use in non-FastAPI contexts.

    Usage:
        with get_db_session() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
