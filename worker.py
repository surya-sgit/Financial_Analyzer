"""
Celery worker for handling concurrent financial document analysis requests.
Bonus feature: Redis-backed task queue with Celery.

Usage:
  Start worker: celery -A worker worker --loglevel=info --concurrency=4
  Monitor:      celery -A worker flower
"""
import os
import time
from datetime import datetime
from celery import Celery
from dotenv import load_dotenv
from database import get_db, AnalysisResult
from main import run_crew


load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app with Redis as broker and result backend
celery_app = Celery(
    "financial_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # Acknowledge after completion (safer for long tasks)
    worker_prefetch_multiplier=1, # One task per worker at a time (prevents memory pressure)
    task_time_limit=600,          # 10 minute hard timeout per task
    task_soft_time_limit=540,     # 9 minute soft timeout (sends exception before hard kill)
)


@celery_app.task(bind=True, name="analyze_document", max_retries=2)
def analyze_document_task(self, analysis_id: str, query: str, file_path: str):
    """
    Celery task: run CrewAI financial analysis in a worker process.
    
    Args:
        analysis_id: UUID for this analysis (used to update DB record)
        query: User's analysis question
        file_path: Path to the saved PDF file
        
    Returns:
        dict with status and analysis result
    """

    start_time = time.time()

    # Update status to "processing"
    with get_db() as db:
        record = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
        if record:
            record.status = "processing"

    try:
        # Import here to avoid circular imports at module load time

        result = run_crew(query=query, file_path=file_path)
        elapsed = time.time() - start_time

        # Update DB with success
        with get_db() as db:
            record = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
            if record:
                record.status = "complete"
                record.analysis = str(result)
                record.completed_at = datetime.utcnow()
                record.processing_time_seconds = round(elapsed, 2)

        return {
            "status": "complete",
            "analysis_id": analysis_id,
            "analysis": str(result),
            "processing_time_seconds": round(elapsed, 2)
        }

    except Exception as exc:
        elapsed = time.time() - start_time

        # Update DB with failure
        with get_db() as db:
            record = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
            if record:
                record.status = "failed"
                record.error_message = str(exc)
                record.completed_at = datetime.utcnow()
                record.processing_time_seconds = round(elapsed, 2)

        # Retry on transient errors (up to max_retries)
        raise self.retry(exc=exc, countdown=30)

    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
