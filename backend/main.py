from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="../frontend/.env.local")

# Import Routes
from routes import interview

app = FastAPI(
    title="PreMock AI API",
    description="Real-Time AI Interview Proctored Engine",
    version="1.0.0"
)

# CORS Policy to allow frontend Next.js on localhost:3000 / 127.0.0.1:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "AuraMock AI Engine is running"}
