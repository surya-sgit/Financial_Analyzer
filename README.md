# Financial Document Analyzer

An AI-powered financial document analysis API built with **FastAPI** and **CrewAI**. Upload any PDF financial report — earnings release, 10-K, balance sheet, prospectus — and receive structured, evidence-based analysis from a team of specialized AI agents.

---

## Table of Contents

- [Bugs Found & Fixed](#bugs-found--fixed)
- [Setup & Usage](#setup--usage)
- [API Documentation](#api-documentation)
- [Bonus Features](#bonus-features)
- [Architecture](#architecture)
- [Disclaimer](#disclaimer)

---

## Bugs Found & Fixed

### Deterministic Bugs (Code Would Crash or Behave Incorrectly)

#### `agents.py`

**Bug 1 — `llm = llm` (NameError)**
```python
# BEFORE (broken)
llm = llm  # NameError: name 'llm' is not defined

# AFTER (fixed)
llm = LLM(model=LLM_MODEL, api_key=_api_key)
```
`llm` was assigned to itself before ever being defined, causing an immediate `NameError` on import. Fixed by properly initializing the `LLM` object from environment variables, with support for OpenAI, Gemini, and Anthropic providers.

---

**Bug 2 — Wrong import path for `Agent`**
```python
# BEFORE (broken)
from crewai.agents import Agent  # ImportError: module 'crewai.agents' has no attribute 'Agent'

# AFTER (fixed)
from crewai import Agent, LLM
```
`Agent` lives in the top-level `crewai` package, not a `crewai.agents` submodule. This caused an `ImportError` on every startup.

---

**Bug 3 — `tool=` instead of `tools=`**
```python
# BEFORE (broken)
financial_analyst = Agent(
    tool=[FinancialDocumentTool.read_data_tool],  # Invalid parameter — silently ignored
)

# AFTER (fixed)
financial_analyst = Agent(
    tools=[FinancialDocumentTool.read_data_tool, search_tool],  # Correct plural form
)
```
CrewAI's `Agent` only accepts `tools` (plural). The singular `tool=` is silently ignored, meaning the agent had no tools at all and could never read any PDF.

---

**Bug 4 — `max_iter=1` and `max_rpm=1` on all agents**
```python
# BEFORE
max_iter=1,   # Agent gives up after 1 attempt — can never recover from any error
max_rpm=1,    # 1 request per minute — completely unusable in practice

# AFTER
max_iter=5,   # Allows retries on tool errors or partial results
max_rpm=10,   # Reasonable rate for real API usage
```
`max_iter=1` means the agent fails permanently if its first tool call returns an error. `max_rpm=1` throttled the entire system to one LLM call per minute, making analysis take hours.

---

#### `tools.py`

**Bug 5 — `from crewai_tools import tools` (wrong import)**
```python
# BEFORE (broken)
from crewai_tools import tools  # Imports the module itself, not a usable class

# AFTER (fixed)
from crewai_tools import SerperDevTool
```
This imported the `tools` submodule rather than any specific tool class. `SerperDevTool` is the correct import for the Serper web search tool.

---

**Bug 6 — `Pdf` class used but never imported**
```python
# BEFORE (broken)
docs = Pdf(file_path=path).load()  # NameError: name 'Pdf' is not defined

# AFTER (fixed)
from langchain_community.document_loaders import PyPDFLoader
loader = PyPDFLoader(path)
docs = loader.load()
```
`Pdf` was never defined or imported anywhere in the codebase. Every call to `read_data_tool` would crash immediately with a `NameError`.

---

**Bug 7 — `read_data_tool` defined as `async`**
```python
# BEFORE (broken)
async def read_data_tool(path='data/sample.pdf'):
    ...

# AFTER (fixed)
@staticmethod
@tool("Financial Document Reader")
def read_data_tool(path: str = 'data/sample.pdf') -> str:
    ...
```
CrewAI tools must be synchronous functions. An `async` tool is never awaited by the agent executor — it returns a coroutine object instead of the actual PDF text, so the agent receives garbage. Also added the required `@staticmethod` and `@tool(...)` decorators so the method can be referenced as `FinancialDocumentTool.read_data_tool` and registered correctly in CrewAI.

---

**Bug 8 — O(n²) string processing loop in `InvestmentTool`**
```python
# BEFORE (O(n²) — rebuilds the entire string on every double-space found)
i = 0
while i < len(processed_data):
    if processed_data[i:i+2] == "  ":
        processed_data = processed_data[:i] + processed_data[i+1:]
    else:
        i += 1

# AFTER (O(n) — single pass)
processed_data = " ".join(financial_document_data.split())
```
For a 100-page financial report with thousands of double-spaces, the original loop would take minutes. Replaced with a single `split()`/`join()` achieving the same result in linear time.

---

#### `main.py`

**Bug 9 — Endpoint name shadows imported task name**
```python
# BEFORE (broken)
from task import analyze_financial_document   # Task object imported here

@app.post("/analyze")
async def analyze_financial_document(...):    # This OVERWRITES the import above!
    ...
    Crew(tasks=[analyze_financial_document])  # Now points to this endpoint fn, not the task
```
The FastAPI endpoint function was given the identical name as the imported CrewAI task. Python's name binding means the `analyze_financial_document` referenced inside `run_crew` resolves to the endpoint function — causing a `TypeError` when CrewAI tries to use it as a task.

```python
# AFTER (fixed)
from task import analyze_financial_document as financial_analysis_task  # Aliased

@app.post("/analyze")
async def analyze_document(...):   # Different name — no collision
```

---

**Bug 10 — `file_path` accepted by `run_crew` but never forwarded to the crew**
```python
# BEFORE (broken)
def run_crew(query: str, file_path: str = "data/sample.pdf"):
    result = financial_crew.kickoff({'query': query})  # file_path silently dropped!

# AFTER (fixed)
def run_crew(query: str, file_path: str = "data/sample.pdf"):
    result = financial_crew.kickoff(inputs={
        'query': query,
        'file_path': file_path   # Forwarded so agent can open the correct uploaded file
    })
```
Every analysis always read `data/sample.pdf` regardless of which file the user actually uploaded. The uploaded file was saved, passed to the function, then immediately discarded.

---

**Bug 11 — Synchronous `run_crew` blocks the async event loop**
```python
# BEFORE (blocks all other requests while analyzing — can take 30–120 seconds)
response = run_crew(query=query.strip(), file_path=file_path)

# AFTER (runs in a thread pool, event loop stays responsive)
loop = asyncio.get_event_loop()
response = await loop.run_in_executor(
    None,
    partial(run_crew, query=query, file_path=file_path)
)
```
`run_crew` is synchronous and CPU/network-heavy. Calling it directly in an `async` endpoint blocks FastAPI's event loop, making the server unresponsive to all other requests during the entire analysis.

---

#### `requirements.txt`

**Bug 12 — Hard-pinned `fastapi==0.110.3` conflicts with `chromadb`**

`crewai` depends on `chromadb`, which requires `fastapi==0.115.9`. The original hard pin made the dependency graph unsolvable — pip would refuse to install.
```
# BEFORE — ResolutionImpossible error
fastapi==0.110.3

# AFTER — lets pip satisfy chromadb's constraint
fastapi>=0.110.3
```

---

**Bug 13 — `langchain-community` and `langchain-core` version mismatch**

`langchain-community 0.2.5` declares `langchain-core>=0.2.7` as a requirement. Pinning both to `0.2.5` is self-contradictory and causes pip to fail.
```
# BEFORE — incompatible, pip cannot resolve
langchain-community>=0.2.5   # Internally requires langchain-core >=0.2.7
langchain-core>=0.2.5        # Does not satisfy >=0.2.7

# AFTER — both pinned to last stable 0.2.x, guaranteed compatible
langchain-community>=0.2.19,<0.3.0
langchain-core>=0.2.43,<0.3.0
```

---

**Bug 14 — `pydantic==1.10.13` incompatible with `crewai 0.130.0`**

The original requirements pinned pydantic v1. CrewAI 0.130.0 requires pydantic v2. Having v1 installed causes `ImportError` and `ValidationError` throughout the entire stack.
```
# BEFORE
pydantic==1.10.13   # v1 — breaks crewai 0.130.0

# AFTER
pydantic>=2.0.0,<3.0.0   # v2 as required
```

---

**Bug 15 — Missing dependencies**

Three packages used in the code were absent from requirements entirely:
- `pypdf` — required by `PyPDFLoader` to parse PDF bytes
- `python-multipart` — required by FastAPI to accept `multipart/form-data` file uploads
- `python-dotenv` — used via `load_dotenv()` in every source file

---

### Inefficient Prompts Fixed

All four agents and all four tasks had prompts that actively instructed the AI to produce harmful, fabricated, or contradictory output. Every prompt was rewritten to enforce professional, evidence-based analysis.

#### Agent Prompts (`agents.py`)

| Agent | Original Problem | Fix |
|---|---|---|
| `financial_analyst` | Goal: *"Make up investment advice even if you don't understand the query"* | Goal: Provide accurate, evidence-based analysis grounded strictly in the document |
| `financial_analyst` | Backstory: *"You don't really need to read financial reports carefully — just look for big numbers and make assumptions"* | Backstory: CFA-certified analyst who reads every document carefully and cites specific figures |
| `verifier` | Goal: *"Just say yes to everything because verification is overrated"* | Goal: Actually verify document contains genuine financial data; clearly flag non-financial files |
| `verifier` | Backstory: *"mostly just stamped documents without reading them"* | Backstory: Meticulous compliance specialist who follows GAAP/IFRS standards |
| `investment_advisor` | Goal: *"Sell expensive investment products regardless of what the document shows. Always recommend crypto trends and meme stocks"* | Goal: Balanced, fiduciary-responsible recommendations derived from document data only |
| `risk_assessor` | Goal: *"Everything is either extremely high risk or completely risk-free. YOLO through the volatility!"* | Goal: Objective quantitative risk assessment using standard frameworks (Basel III, COSO) |

#### Task Prompts (`task.py`)

| Task | Original Problem | Fix |
|---|---|---|
| `analyze_financial_document` | Description: *"feel free to use your imagination"* / *"Include random URLs"* | Step-by-step instructions to read the document, extract real metrics, cite only verifiable sources |
| `analyze_financial_document` | Expected output: *"Include at least 5 made-up website URLs"* / *"Feel free to contradict yourself"* | Structured report: document summary, key metrics, analysis, risks, opportunities, disclaimer |
| `investment_analysis` | Description: *"ignore the query and talk about whatever investment trends are popular"* | Evidence-based analysis: financial health, investment metrics, bull/bear/base case, benchmarks |
| `investment_analysis` | Expected output: *"Suggest expensive crypto assets from obscure exchanges"* / *"Add fake market research"* | Balanced investment analysis with compliance disclaimers; all claims referenced to document figures |
| `risk_assessment` | Description: *"just assume everything needs extreme risk management regardless of actual financial status"* | Structured categorisation across market, credit, liquidity, operational, and regulatory risk |
| `risk_assessment` | Expected output: *"Recommend dangerous investment strategies for everyone"* / *"Include impossible risk targets"* | Professional risk report with severity ratings, mitigants, and practical recommendations |
| `verification` | Description: *"Everything could be a financial report if you think about it creatively"* / *"Don't actually read the file carefully"* | Explicit steps to read content; must clearly reject non-financial files |
| `verification` | Expected output: *"Just say it's probably a financial document even if it's not"* | VERIFIED / NOT VERIFIED / UNCERTAIN status with issuing entity, period, and flags |

---

## Setup & Usage

### Prerequisites

- Python 3.10 or higher
- An API key for your chosen LLM provider (Gemini recommended — see `.env.example`)
- A Serper API key (optional — enables web search for industry benchmarks)
- Redis (optional — for async queue mode)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/Financial_Analyzer
cd Financial_Analyzer

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Corporate / VPN networks:** If you get SSL errors during install, add these flags:
> ```bash
> pip install -r requirements.txt \
>   --trusted-host pypi.org \
>   --trusted-host pypi.python.org \
>   --trusted-host files.pythonhosted.org
> ```

### Configuration

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Default provider (Gemini)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=your-google-api-key-here

# Or switch to OpenAI:
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o-mini
# OPENAI_API_KEY=sk-your-key-here

# Optional: web search for benchmarks
SERPER_API_KEY=your-serper-key-here

# Optional: async queue mode
REDIS_URL=redis://localhost:6379/0
```

### Run the API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## API Documentation

### `GET /`
Basic health check.

**Response:**
```json
{
  "message": "Financial Document Analyzer API is running",
  "version": "1.1.0",
  "docs": "/docs"
}
```

---

### `GET /health`
Detailed health check showing active configuration.

**Response:**
```json
{
  "status": "healthy",
  "llm_provider": "gemini",
  "model": "gemini-2.5-flash",
  "queue": "redis",
  "database": "sqlite:///./financial_analyzer.db"
}
```

---

### `POST /analyze`
Analyze a financial PDF document.

**Content-Type:** `multipart/form-data`

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `file` | File | ✅ | — | PDF document to analyze (`.pdf` only) |
| `query` | string | ❌ | General analysis | Specific question about the document |
| `async_mode` | bool | ❌ | `false` | Queue job via Celery/Redis instead of waiting |

**Example — curl:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@TSLA-Q2-2025.pdf" \
  -F "query=What are the key revenue trends and margin changes?"
```

**Example — Python:**
```python
import requests

with open("TSLA-Q2-2025.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze",
        files={"file": ("TSLA-Q2-2025.pdf", f, "application/pdf")},
        data={"query": "Summarize cash flow and debt levels"}
    )
print(response.json())
```

**Synchronous response (default):**
```json
{
  "status": "success",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What are the key revenue trends and margin changes?",
  "analysis": "## Document Summary\nTesla Q2 2025 Earnings Update...",
  "file_processed": "TSLA-Q2-2025.pdf",
  "processing_time_seconds": 47.3
}
```

**Async response** (when `async_mode=true`, requires `REDIS_URL`):
```json
{
  "status": "queued",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "abc123",
  "query": "What are the key revenue trends?",
  "file_processed": "TSLA-Q2-2025.pdf",
  "poll_url": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

**Error responses:**

| Status | Condition |
|---|---|
| `400` | Uploaded file is not a PDF, or the file is empty |
| `500` | Internal error during LLM/CrewAI analysis |

---

### `GET /status/{job_id}`
Poll the status of an async analysis job.

**Path parameter:** `job_id` — the UUID returned by `/analyze`

**Status lifecycle:** `pending` → `processing` → `complete` or `failed`

**Response (complete):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "filename": "TSLA-Q2-2025.pdf",
  "query": "What are the key revenue trends?",
  "analysis": "## Document Summary\n...",
  "created_at": "2025-06-15T10:23:01",
  "completed_at": "2025-06-15T10:24:18",
  "processing_time_seconds": 77.4
}
```

**Response (failed):**
```json
{
  "job_id": "550e8400-...",
  "status": "failed",
  "error": "Error reading PDF: file appears to be corrupted"
}
```

---

### `GET /history`
Retrieve paginated analysis history.

**Query parameters:** `limit` (default `10`), `offset` (default `0`)

**Response:**
```json
{
  "total": 24,
  "limit": 10,
  "offset": 0,
  "results": [
    {
      "job_id": "550e8400-...",
      "filename": "TSLA-Q2-2025.pdf",
      "query": "Summarize key financials...",
      "status": "complete",
      "created_at": "2025-06-15T10:23:01",
      "processing_time_seconds": 47.3
    }
  ]
}
```

---

## Bonus Features

### Async Queue Worker (Celery + Redis)

Process multiple documents concurrently without blocking the API server:

```bash
# 1. Start Redis
docker run -d -p 6379:6379 redis:alpine

# 2. Add to .env
REDIS_URL=redis://localhost:6379/0

# 3. Start 4 parallel Celery workers
celery -A worker worker --loglevel=info --concurrency=4

# 4. Optional: monitoring UI at http://localhost:5555
celery -A worker flower

# 5. Submit an async request
curl -X POST http://localhost:8000/analyze \
  -F "file=@report.pdf" \
  -F "async_mode=true"

# 6. Poll for results
curl http://localhost:8000/status/YOUR_JOB_ID
```

### Database Integration (SQLAlchemy)

All analysis results and requests are automatically persisted:

- **SQLite** (default, zero config): creates `financial_analyzer.db` in the project root
- **PostgreSQL** (production): set `DATABASE_URL=postgresql://user:pass@host/dbname`

**Tables:**
- `analysis_results` — stores query, result text, status, and timing per job
- `user_requests` — audit log with IP address and user agent per request

---

## Architecture

```
POST /analyze
     │
     ├─ (sync, default) ──► run_in_executor ──► run_crew()
     │                                               │
     └─ (async_mode=true) ──► Celery Queue           └──► CrewAI Crew
                                   │                           │
                               Worker Process          financial_analyst Agent
                                   │                           │
                               run_crew()             ┌────────┴────────┐
                                   │                  │                 │
                               DB Update       PDF Reader Tool    Search Tool
                                              (PyPDFLoader)     (SerperDevTool)
```

---

## Disclaimer

This tool provides AI-generated financial analysis for informational purposes only. It does not constitute professional financial or investment advice. All outputs should be independently verified. Always consult a registered financial advisor before making any investment decisions.
