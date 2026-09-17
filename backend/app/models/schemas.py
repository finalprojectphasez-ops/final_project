from pydantic import BaseModel
from typing import List, Dict, Optional


class InterviewContext(BaseModel):
    """Core context for an interview session."""
    role: str
    difficulty: str
    resume_text: str


class SetupRequest(BaseModel):
    """Request body for POST /api/setup."""
    role: str
    difficulty: str
    resume_text: str


class AnswerRequest(BaseModel):
    """Request body for POST /api/answer."""
    session_id: str
    answer: str
