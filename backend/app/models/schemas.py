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
# Models for Resume-Based AI Interview Engine
# ---------------------------------------------------------

class ProfessionalProfile(BaseModel):
    current_title: Optional[str] = None
    previous_titles: List[str] = []
    current_company: Optional[str] = None
    previous_companies: List[str] = []
    years_experience: Optional[float] = None
    seniority: Optional[str] = None  # "intern", "junior", "mid", "senior", "lead", "principal"
    primary_domain: Optional[str] = None
    industries: List[str] = []
    core_skills: List[str] = []
    secondary_skills: List[str] = []
    tools: List[str] = []
    leadership_experience: Optional[bool] = None
    key_achievements: List[str] = []
    location: Optional[str] = None
    summary: Optional[str] = None


class ResumeUploadResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    page_count: Optional[int] = None
    text: Optional[str] = None
    profile: Optional[ProfessionalProfile] = None
    error: Optional[str] = None


class CandidateQuestionResponse(BaseModel):
    question: str
    topic: str
    kind: str  # "main" | "follow_up" | "clarify"
    difficulty: str  # "beginner" | "intermediate" | "advanced"
    # Note: expected_points is deliberately omitted to prevent exposing answer keys


class InterviewQuestionInternal(BaseModel):
    question: str
    topic: str
    kind: str = "main"  # "main" | "follow_up" | "clarify"
    difficulty: str = "intermediate"  # "beginner" | "intermediate" | "advanced"
    expected_points: List[str] = []
    review_status: str = "unreviewed"  # "reviewed" | "unreviewed"


class InterviewSessionCreateRequest(BaseModel):
    role: str
    difficulty: str  # "Easy" / "beginner", "Medium" / "intermediate", "Hard" / "advanced"
    duration_minutes: int = 30  # 15, 30, 45
    resume_profile: Optional[ProfessionalProfile] = None
    resume_text: Optional[str] = None
    job_description: Optional[str] = None


class InterviewSessionResponse(BaseModel):
    session_id: str
    role: str
    difficulty: str
    duration_minutes: int
    target_questions: int
    planned_topics: List[str]
    current_turn: int
    current_topic_index: int
    question: CandidateQuestionResponse
    deadline_timestamp: float
    is_complete: bool = False


class TurnSubmitRequest(BaseModel):
    session_id: Optional[str] = None
    answer: str
    turn_id: Optional[str] = None
    next_main_difficulty: Optional[str] = None


class TurnSubmitResponse(BaseModel):
    action: str  # "follow_up" | "clarify" | "next_topic" | "end"
    next_question: Optional[CandidateQuestionResponse] = None
    session_id: str
    turn_index: int
    current_topic_index: int
    followups_used: int
    remaining_topics_count: int
    is_complete: bool
    deadline_expired: bool = False
    evaluation: Optional[Dict[str, Any]] = None


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
    score: int = 50
    relevance: int = 50
    technical_depth: int = 50
    clarity: int = 50
    completeness: int = 50
    strengths: List[str] = []
    improvements: List[str] = []
    evaluation: str = "Evaluation completed."
    follow_up_needed: bool = False
    follow_up_question: Optional[str] = None


class InterviewTurnRequest(BaseModel):
    resume_text: str
    job_role: str
    difficulty: str = "Medium"
    question: str
    answer: str
    turn_index: int = 1
    phase: str = "intro"


class InterviewTurnResponse(BaseModel):
    score: int = 70
    relevance: int = 70
    technical_depth: int = 70
    clarity: int = 70
    completeness: int = 70
    strengths: List[str] = []
    improvements: List[str] = []
    evaluation: str = "Answer evaluated successfully."
    next_question: str
    next_phase: str
    is_followup: bool = False
