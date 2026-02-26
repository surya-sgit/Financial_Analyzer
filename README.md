# Financial Document Analyzer — Fixed & Enhanced

A FastAPI + CrewAI system for AI-powered financial document analysis. Upload a PDF (earnings report, 10-K, prospectus, etc.) and receive structured, evidence-based analysis from a team of specialized AI agents.

---

## 🐛 Bugs Found & Fixed

### Deterministic Bugs (Code Crashes / Wrong Behavior)

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `agents.py` | `llm = llm` — NameError, variable used before definition | Replaced with proper `LLM(model=..., api_key=...)` initialization from env vars |
| 2 | `agents.py` | `tool=[...]` — invalid Agent parameter name | Changed to `tools=[...]` (plural), which is the correct CrewAI parameter |
| 3 | `agents.py` | `from crewai.agents import Agent` — wrong module path | Fixed to `from crewai import Agent, LLM` |
| 4 | `tools.py` | `from crewai_tools import tools` — imports a module, not a class; unused and incorrect | Removed; replaced with `from crewai_tools import SerperDevTool` |
| 5 | `tools.py` | `Pdf` class used but never imported | Replaced with `PyPDFLoader` from `langchain_community.document_loaders` |
| 6 | `tools.py` | `read_data_tool` defined as `async` — CrewAI tools must be synchronous | Converted to synchronous function |
| 7 | `tools.py` | `FinancialDocumentTool.read_data_tool` used as static reference but lacks `@staticmethod` | Added `@staticmethod` and `@tool(...)` decorators |
| 8 | `main.py` | Endpoint function named `analyze_financial_document` shadows the imported CrewAI task of the same name | Renamed endpoint to `analyze_document` |
| 9 | `main.py` | `file_path` passed to `run_crew` but never forwarded to the crew/task | Now passed as `file_path` in `crew.kickoff(inputs={...})` |
| 10 | `task.py` | Imports `verifier` agent but never uses it in any active task | Removed unused import |
| 11 | `requirements.txt` | Missing `pypdf`, `langchain-community`, `python-multipart`, `python-dotenv` | Added all missing dependencies |
| 12 | `main.py` | `run_crew` called directly in async endpoint, blocking the event loop | Wrapped with `loop.run_in_executor(None, partial(...))` |

---

### Inefficient / Harmful Prompts Fixed

All original prompts actively instructed agents to produce bad, dangerous, or hallucinated output. Every goal, backstory, task description, and expected_output was rewritten.

#### `agents.py` — Agent Prompts

| Agent | Original Problem | Fix |
|-------|-----------------|-----|
| `financial_analyst` | Goal: "Make up investment advice even if you don't understand" | Goal: "Provide accurate, evidence-based analysis strictly from the document" |
| `financial_analyst` | Backstory: "You don't need to read reports carefully — just look for big numbers" | Backstory: Professional CFA analyst who reads documents carefully and cites sources |
| `verifier` | Goal: "Just say yes to everything because verification is overrated" | Goal: Properly verify document contains genuine financial data |
| `investment_advisor` | Goal: "Sell expensive products regardless of what the document shows" | Goal: Evidence-based recommendations with fiduciary responsibility |
| `risk_assessor` | Goal: "Everything is either extremely high risk or completely risk-free" | Goal: Objective quantitative risk analysis using standard frameworks |
| All agents | `max_iter=1` — agent couldn't retry on failure | Increased to `max_iter=5` |
| All agents | `max_rpm=1` — 1 request/minute, extremely throttled | Increased to `max_rpm=10` |

#### `task.py` — Task Prompts

| Task | Original Problem | Fix |
|------|-----------------|-----|
| `analyze_financial_document` | "Feel free to use your imagination" / "Include random URLs" | Step-by-step instructions to read document, extract real metrics, cite sources |
| `analyze_financial_document` | Expected output: "Include at least 5 made-up website URLs" | Expected output: Structured report with document-sourced data and disclaimers |
| `investment_analysis` | "Recommend expensive investment products regardless of financials" | Balanced bull/bear/base case analysis with compliance disclaimers |
| `risk_assessment` | "Ignore actual risk factors" / "YOLO through the volatility" | Professional risk categorization (market/credit/liquidity/operational) |
| `verification` | "Feel free to hallucinate financial terms" | Actual document verification with VERIFIED/NOT VERIFIED status |

---

## 🚀 Setup & Usage

### Prerequisites

- Python 3.10+
- An OpenAI API key (or Anthropic/Google API key)
- Optional: Redis (for async queue), Docker

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/financial-document-analyzer
cd financial-document-analyzer

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your API keys:
```

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-key-here
SERPER_API_KEY=your-serper-key   # optional, for web search
```

### Run the API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for the interactive Swagger UI.

---

## 📡 API Documentation

### `GET /`
Health check.

**Response:**
```json
{"message": "Financial Document Analyzer API is running", "version": "1.1.0"}
```

---

### `POST /analyze`
Analyze a financial PDF document.

**Form Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | File | ✅ | — | PDF file to analyze |
| `query` | string | ❌ | General analysis | Specific question about the document |
| `async_mode` | bool | ❌ | `false` | Submit to queue instead of waiting |

**Example (curl):**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@TSLA-Q2-2025.pdf" \
  -F "query=What are the key revenue trends and risks?"
```

**Synchronous Response:**
```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What are the key revenue trends and risks?",
  "analysis": "## Document Summary\n...",
  "file_processed": "TSLA-Q2-2025.pdf",
  "processing_time_seconds": 42.3
}
```

**Async Response** (when `async_mode=true`):
```json
{
  "status": "queued",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "poll_url": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### `GET /status/{job_id}`
Poll status of an async analysis job.

**Response:**
```json
{
  "job_id": "550e8400...",
  "status": "complete",
  "analysis": "## Document Summary\n...",
  "processing_time_seconds": 38.1
}
```

Status values: `pending` → `processing` → `complete` | `failed`

---

### `GET /history`
Retrieve paginated analysis history.

**Query params:** `limit` (default 10), `offset` (default 0)

**Response:**
```json
{
  "total": 47,
  "results": [
    {"job_id": "...", "filename": "report.pdf", "status": "complete", ...}
  ]
}
```

---

### `GET /health`
Detailed system health check showing LLM configuration and queue status.

---

## ⚡ Bonus Features

### Queue Worker (Celery + Redis)

Handles concurrent requests without blocking:

```bash
# 1. Start Redis
docker run -d -p 6379:6379 redis:alpine

# 2. Add to .env
REDIS_URL=redis://localhost:6379/0

# 3. Start Celery workers (4 concurrent)
celery -A worker worker --loglevel=info --concurrency=4

# 4. Optional: monitoring dashboard at http://localhost:5555
celery -A worker flower

# 5. Submit async request
curl -X POST http://localhost:8000/analyze \
  -F "file=@report.pdf" \
  -F "async_mode=true"
```

### Database Integration (SQLAlchemy)

All analysis results and requests are automatically stored:

- **SQLite** (default, zero config): `financial_analyzer.db`
- **PostgreSQL** (production): set `DATABASE_URL=postgresql://user:pass@host/db`

Tables:
- `analysis_results` — stores query, result, status, timing
- `user_requests` — audit log of all API requests

---

## 🏗️ Architecture

```
POST /analyze
     │
     ├─ (sync) ──► run_crew() ──► CrewAI Crew
     │                                 │
     └─ (async) ──► Celery Queue       └─► financial_analyst Agent
                        │                        │
                    Worker Process          PDF Reader Tool
                        │                  (PyPDFLoader)
                    run_crew()             Search Tool
                        │                  (SerperDev)
                    DB Update
```

---

## 🔒 Disclaimer

This tool provides AI-generated financial analysis for informational purposes only. It does not constitute professional financial or investment advice. Always consult a registered financial advisor before making investment decisions.
