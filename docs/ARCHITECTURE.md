# PreMock AI — Architecture

## System Overview

```mermaid
graph LR
    subgraph Frontend ["Frontend (Next.js 16)"]
        A[Landing Page] --> B[Auth - Supabase]
        B --> C[Dashboard]
        C --> D[Interview Session]
        D --> E[Report Viewer]
    end

    subgraph Backend ["Backend (FastAPI)"]
        F[POST /api/setup]
        G[POST /api/answer]
        H[WS /api/stream]
    end

    subgraph Services ["AI Services"]
        I[LLM Engine - GPT-4o]
        J[Audio Parser - Deepgram]
        K[Resume Parser - PyPDF2]
    end

    subgraph External ["External APIs"]
        L[OpenAI API]
        M[Deepgram API]
        N[Supabase]
    end

    D -->|HTTP| F
    D -->|HTTP| G
    D -->|WebSocket| H

    F --> I
    G --> I
    H --> J

    I --> L
    J --> M
    B --> N
    K --> N
```

## Interview Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant AI as OpenAI GPT-4o
    participant DG as Deepgram

    U->>FE: Start Interview (role, difficulty, resume)
    FE->>BE: POST /api/setup
    BE->>AI: Generate first question
    AI-->>BE: Question text
    BE-->>FE: { session_id, first_question }
    FE->>U: Display question

    loop For each answer
        U->>FE: Speak / Type answer
        FE->>DG: Stream audio (WebSocket)
        DG-->>FE: Real-time transcript
        FE->>BE: POST /api/answer
        BE->>AI: Evaluate + next question
        AI-->>BE: Follow-up question
        BE-->>FE: { next_question }
        FE->>U: Display next question
    end

    U->>FE: End Interview
    FE->>U: Display Report
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Fallback question banks** | If OpenAI API is unavailable/quota exceeded, the engine serves curated questions from a static bank per role and difficulty — ensuring 100% uptime. |
| **In-memory sessions** | Active interview sessions are stored in-memory for low-latency access. Acceptable for MVP; future work: Redis-backed sessions. |
| **Supabase for Auth + Storage** | Single platform for authentication (Google OAuth) and resume PDF storage, reducing infrastructure complexity. |
| **WebSocket for audio** | Real-time speech-to-text requires low-latency bidirectional communication; WebSocket is the natural choice over HTTP polling. |

## Deployment Topology

| Service | Platform | URL |
|---------|----------|-----|
| Frontend | Vercel | `premock.vercel.app` |
| Backend | Railway / Render | `api.premock.ai` |
| Database + Auth | Supabase | Managed |
| AI | OpenAI API | Managed |
| Speech | Deepgram API | Managed |
