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
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/setup` | Initialize interview session |
| `POST` | `/api/answer` | Submit answer, get next question |
| `WS` | `/api/stream/{session_id}` | Real-time audio streaming |

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
│       ├── audio_parser.py   # Deepgram real-time transcription
│       └── resume_parser.py  # PDF resume text extraction
├── requirements.txt
├── .env.example
└── venv/                 # Virtual environment (gitignored)
```
