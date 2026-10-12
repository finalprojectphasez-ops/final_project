import sys
sys.modules['tensorflow'] = None

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import Routes
from app.routes import interview, emotion, resume, speech, reports, rubric

app = FastAPI(
    title="PreMock AI API",
    description="Real-Time AI Interview Proctored Engine",
    version="1.0.0"
)

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router, prefix="/api", tags=["Interview"])
app.include_router(emotion.router, prefix="/api/emotion", tags=["Emotion"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(speech.router, prefix="/api/speech", tags=["Speech"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(rubric.router, prefix="/api/rubric", tags=["Rubric"])

@app.get("/")
def health_check():
    return {"status": "ok", "message": "PreMock AI Engine is running"}
