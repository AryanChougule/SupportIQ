# SupportIQ

SupportIQ is an AI-powered customer-support analytics prototype built for the DOTMappers AI Engineer assessment.

It provides:

- CSV ingestion and validation
- Natural-language questions over support tickets
- Deterministic DuckDB analytics
- Explainable anomaly detection
- FastAPI REST endpoints
- A minimal Gradio UI mounted at `/`

### Run the application

Clone the repository:

```bash
In command Prompt run the following three commands

git clone https://github.com/AryanChougule/SupportIQ.git
cd SupportIQ
start.bat

Note: At start you have to provide the gemini api key to start
## Architecture

```text
User
  |
  v
FastAPI + Gradio
  |
  v
Gemini query planner
  |
  v
Pydantic query-plan validation
  |
  +--> DuckDB query executor --> computed result
  |
  +--> deterministic anomaly engine --> anomaly report
  |
  v
Answer formatter
```

Gemini is used for natural-language understanding and explanation. It does not directly execute SQL or determine numeric results.





## Run with Docker

### Prerequisites

- Docker Desktop or Docker Engine
- Internet connection for downloading Docker dependencies
- A Gemini API key from Google AI Studio

## Dataset

The assessment expects `support_tickets.csv` with these columns:

- ticket_id
- created_at
- category
- priority
- status
- response_time_hrs
- resolution_time_hrs
- agent_id
- customer_rating
- issue_summary

A small sample dataset is included so the application can run immediately. Replace `data/support_tickets.csv` with the assessment CSV before evaluation.

## Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
copy .env.example .env
```

or on Linux/macOS:

```bash
cp .env.example .env
```

Add your Gemini API key to `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

The Gemini model name is configurable. Use a model available to your Google AI Studio project and free-tier quota.

## Run

```bash
uvicorn app.main:app --reload
```

Open:

- UI: http://127.0.0.1:8000/
- Swagger docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

## API examples

Health:

```bash
curl http://127.0.0.1:8000/health
```

Natural-language query:

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"How many critical tickets are unresolved?\"}"
```

Anomaly detection:

```bash
curl -X POST http://127.0.0.1:8000/anomalies ^
  -H "Content-Type: application/json" ^
  -d "{\"anomaly_type\":\"all\"}"
```

On Linux/macOS, replace `^` with `\`.

## Anomaly logic

1. Long resolution time: IQR upper-bound rule.
2. Old unresolved high-priority tickets: High/Critical tickets that are Open/Escalated and older than the configured age relative to the latest dataset timestamp.
3. Long response time: IQR upper-bound rule.

Anomalies are labelled as potential anomalies, not guaranteed business failures.

## Testing

```bash
pytest -q
```

## Free-tier and reliability notes

- The evaluator needs to provide their own Gemini API key.
- The Gemini key must never be committed.
- Gemini quota errors should be surfaced as API errors.
- All numeric calculations come from DuckDB or deterministic Python logic.
- The sample CSV is only for local smoke testing and must be replaced with the assessment dataset.

## Known limitations

- The query planner supports a deliberately limited set of operations.
- Date phrases such as "this month" require further extension if exact calendar semantics are needed.
- The prototype uses one local DuckDB database and is not intended for concurrent multi-user production traffic.
- The anomaly thresholds are configurable heuristics.
