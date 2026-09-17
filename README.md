<div align="center">

# 🎯 PreMock AI

**Real-Time AI-Powered Interview Practice Platform**

[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20%2B%20Storage-3ECF8E?logo=supabase)](https://supabase.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

PreMock AI is a full-stack interview preparation platform that simulates realistic technical interviews using AI. It provides real-time speech-to-text transcription, adaptive question generation, and detailed performance reports.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, TypeScript, TailwindCSS |
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **AI Engine** | OpenAI GPT-4o (with fallback question banks) |
| **Speech** | Deepgram Nova-2 (real-time transcription) |
| **Auth** | Supabase Auth (Google OAuth + Email) |
| **Storage** | Supabase Storage (resume PDFs) |
| **Deployment** | Vercel (frontend), Railway/Render (backend) |

## Project Structure

```
premock-ai/
├── backend/               # FastAPI API server
│   ├── app/               # Python application package
│   │   ├── main.py        # App entry point
│   │   ├── config.py      # Environment configuration
│   │   ├── models/        # Pydantic schemas
│   │   ├── routes/        # API endpoints
│   │   └── services/      # Business logic (LLM, audio, resume)
│   ├── requirements.txt
│   └── venv/              # Virtual environment (gitignored)
│
├── frontend/              # Next.js web application
│   ├── src/
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Utilities (Supabase, storage)
│   │   └── types/         # TypeScript definitions
│   └── package.json
│
├── docs/                  # Architecture documentation
├── docker-compose.yml     # Local development orchestration
└── README.md              # ← You are here
```

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- API keys: [OpenAI](https://platform.openai.com/), [Deepgram](https://deepgram.com/), [Supabase](https://supabase.com/)

### 1. Clone & Setup

```bash
git clone https://github.com/finalprojectphasez-ops/final_project.git
cd final_project
```

### 2. Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
cp .env.example .env               # Fill in your API keys
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local         # Fill in your Supabase keys
npm run dev
```

### 4. Open

Navigate to [http://localhost:3000](http://localhost:3000)

## Using Docker Compose

```bash
docker-compose up --build
```

This starts both services:
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000

## License

This project is licensed under the [MIT License](LICENSE).
