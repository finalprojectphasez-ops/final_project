from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Import Routes
from app.routes import interview

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

app.include_router(interview.router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "PreMock AI Engine is running"}
