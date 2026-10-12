# PreMock AI — Backend

FastAPI-based AI interview engine powering real-time interview sessions.

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/rubric/config` | 100-mark rubric version, criteria & anchors |
| `POST` | `/api/rubric/assess` | Deterministic local evaluation across 7 criteria |
| `POST` | `/api/rubric/manual-review` | Human assessor override / spoken delivery rating |
| `GET` | `/api/rubric/export/{session_id}` | Export JSON/CSV provenance and evidence audit |
| `POST` | `/api/reports/save` | Persistent report storage on disk |
| `GET` | `/api/reports/{id}` | Retrieve report with rubric breakdown |
| `POST` | `/api/interview/next-turn` | Instant 3-part turn progression |

For complete documentation on the 100-mark assessment rubric, see [docs/RUBRIC_100_GUIDE.md](docs/RUBRIC_100_GUIDE.md).

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── config.py         # Centralized configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py    # Pydantic request/response models
│   ├── routes/
│   │   ├── __init__.py
│   │   └── interview.py  # Interview API endpoints
│   └── services/
│       ├── __init__.py
│       ├── llm_engine.py     # OpenAI GPT-4o interview engine

│       └── resume_parser.py  # PDF resume text extraction
├── requirements.txt
├── .env.example
└── venv/                 # Virtual environment (gitignored)
```
