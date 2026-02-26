"""
Database models for storing analysis results and user data.
Bonus feature: SQLAlchemy ORM with SQLite (or PostgreSQL) backend.
"""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./financial_analyzer.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AnalysisResult(Base):
    """Stores completed financial document analysis results."""
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, index=True)        # UUID
    filename = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    analysis = Column(Text, nullable=True)                    # Crew output
    status = Column(String, default="pending")               # pending / processing / complete / failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)


class UserRequest(Base):
    """Tracks user requests for audit and rate limiting."""
    __tablename__ = "user_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Database session context manager."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
