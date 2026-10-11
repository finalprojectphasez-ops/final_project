from pydantic import BaseModel
from typing import List, Dict, Optional, Any


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


class EvaluateRequest(BaseModel):
    """Request body for POST /api/evaluate."""
    session_id: str


class QuestionFeedback(BaseModel):
    """Feedback for a single question-answer pair."""
    question: str
    answer: str
    score: int
    feedback: str


class EvaluationResponse(BaseModel):
    """Full structured evaluation returned by POST /api/evaluate."""
    overall_score: int
    technical_score: int
    communication_score: int
    answer_relevance: int
    strengths: List[str]
    weaknesses: List[str]
    question_feedback: List[QuestionFeedback]
    improvement_suggestions: List[str]
    practice_areas: List[str]
    general_feedback: str

# ---------------------------------------------------------
# New Models for Resume-Based AI Interview Engine
# ---------------------------------------------------------

class ResumeUploadResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    page_count: Optional[int] = None
    text: Optional[str] = None
    error: Optional[str] = None


class InterviewQuestionRequest(BaseModel):
    resume_text: str
    job_role: str
    difficulty: str


class InterviewQuestionResponse(BaseModel):
    question: str
    question_type: str
    topic: str
    source: str


class AnswerEvaluationRequest(BaseModel):
    resume_text: str
    job_role: str
    question: str
    answer: str


class AnswerEvaluationResponse(BaseModel):
    score: int
    relevance: int
    technical_depth: int
    clarity: int
    completeness: int
    strengths: List[str]
    improvements: List[str]
    evaluation: str
    follow_up_needed: bool
    follow_up_question: Optional[str] = None
