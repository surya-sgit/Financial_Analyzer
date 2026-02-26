from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
import os
import time
import uuid
import asyncio
from functools import partial
from datetime import datetime

from crewai import Crew, Process
from agents import financial_analyst
# BUG FIX: Import task with alias to avoid name collision with the endpoint function
from task import analyze_financial_document as financial_analysis_task

# Bonus: database integration
from database import init_db, get_db, AnalysisResult, UserRequest

app = FastAPI(
    title="Financial Document Analyzer",
    description=(
        "AI-powered financial document analysis using CrewAI agents. "
        "Upload a PDF financial report and receive evidence-based analysis."
    ),
    version="1.1.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and directories on startup."""
    init_db()
    os.makedirs("data", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)


# BUG FIX: file_path was received but never used — now passed into crew inputs
def run_crew(query: str, file_path: str = "data/sample.pdf") -> str:
    """Run the CrewAI financial analysis crew synchronously.

    Args:
        query: The user's analysis question
        file_path: Path to the uploaded PDF file

    Returns:
        Analysis result as string
    """
    financial_crew = Crew(
        agents=[financial_analyst],
        tasks=[financial_analysis_task],
        process=Process.sequential,
        verbose=True,
    )

    # BUG FIX: Pass file_path into crew inputs so the agent reads the correct uploaded PDF
    result = financial_crew.kickoff(inputs={
        'query': query,
        'file_path': file_path
    })
    return result


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "1.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with configuration info."""
    return {
        "status": "healthy",
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "queue": "redis" if os.getenv("REDIS_URL") else "disabled",
        "database": os.getenv("DATABASE_URL", "sqlite:///./financial_analyzer.db"),
    }


# BUG FIX: Renamed endpoint from `analyze_financial_document` to `analyze_document`
# — original name shadowed the imported CrewAI task of the same name
@app.post("/analyze")
async def analyze_document(
    request: Request,
    file: UploadFile = File(..., description="PDF financial document to analyze"),
    query: str = Form(
        default="Analyze this financial document and provide key financial insights, "
                "risk factors, and investment considerations.",
        description="Specific question or analysis request for the document"
    ),
    async_mode: bool = Form(
        default=False,
        description="Submit to Redis queue for async processing (requires REDIS_URL env var)"
    )
):
    """
    Analyze a financial document and provide comprehensive investment insights.

    **Synchronous mode** (default): Waits for analysis and returns results directly.

    **Async mode** (`async_mode=true`): Submits job to Redis/Celery queue and returns
    a `job_id`. Poll `/status/{job_id}` to retrieve results when complete.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )

    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"

    # Normalize query
    if not query or not query.strip():
        query = ("Analyze this financial document and provide key financial insights, "
                 "risk factors, and investment considerations.")
    query = query.strip()

    try:
        # Save uploaded file
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with open(file_path, "wb") as f:
            f.write(content)

        # Record request in database (bonus feature)
        with get_db() as db:
            result_record = AnalysisResult(
                id=file_id,
                filename=file.filename,
                query=query,
                status="pending",
            )
            db.add(result_record)

            user_record = UserRequest(
                analysis_id=file_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            db.add(user_record)

        # --- Async queue mode (bonus feature) ---
        if async_mode and os.getenv("REDIS_URL"):
            try:
                from worker import analyze_document_task
                task = analyze_document_task.delay(
                    analysis_id=file_id,
                    query=query,
                    file_path=file_path
                )
                return {
                    "status": "queued",
                    "job_id": file_id,
                    "celery_task_id": task.id,
                    "query": query,
                    "file_processed": file.filename,
                    "poll_url": f"/status/{file_id}"
                }
            except Exception as e:
                # Fall back to synchronous mode if queue unavailable
                print(f"Queue submission failed, falling back to sync: {e}")

        # --- Synchronous mode ---
        # BUG FIX: Use run_in_executor to avoid blocking the async event loop
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        response = await loop.run_in_executor(
            None,
            partial(run_crew, query=query, file_path=file_path)
        )

        elapsed = loop.time() - start_time

        # Persist result to database
        with get_db() as db:
            record = db.query(AnalysisResult).filter(AnalysisResult.id == file_id).first()
            if record:
                record.status = "complete"
                record.analysis = str(response)
                record.completed_at = datetime.utcnow()
                record.processing_time_seconds = round(elapsed, 2)

        return {
            "status": "success",
            "job_id": file_id,
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename,
            "processing_time_seconds": round(elapsed, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        # Update DB with failure info
        with get_db() as db:
            record = db.query(AnalysisResult).filter(AnalysisResult.id == file_id).first()
            if record:
                record.status = "failed"
                record.error_message = str(e)
                record.completed_at = datetime.utcnow()

        raise HTTPException(
            status_code=500,
            detail=f"Error processing financial document: {str(e)}"
        )

    finally:
        # Synchronous mode handles file cleanup here; async worker handles its own cleanup
        if not async_mode and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@app.get("/status/{job_id}")
async def get_analysis_status(job_id: str):
    """
    Poll the status of an async analysis job.

    Returns one of: pending | processing | complete | failed
    """
    with get_db() as db:
        record = db.query(AnalysisResult).filter(AnalysisResult.id == job_id).first()
        if not record:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

        response = {
            "job_id": job_id,
            "status": record.status,
            "filename": record.filename,
            "query": record.query,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "processing_time_seconds": record.processing_time_seconds,
        }

        if record.status == "complete":
            response["analysis"] = record.analysis
        elif record.status == "failed":
            response["error"] = record.error_message

        return response


@app.get("/history")
async def get_analysis_history(limit: int = 10, offset: int = 0):
    """Retrieve paginated analysis history."""
    with get_db() as db:
        total = db.query(AnalysisResult).count()
        records = (
            db.query(AnalysisResult)
            .order_by(AnalysisResult.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "job_id": r.id,
                    "filename": r.filename,
                    "query": r.query[:100] + "..." if r.query and len(r.query) > 100 else r.query,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "processing_time_seconds": r.processing_time_seconds,
                }
                for r in records
            ]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
