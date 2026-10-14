"""
Pydantic Schemas for 100-Mark Interview Assessment Rubric.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class CriterionResult(BaseModel):
    criterion_id: str
    name: str
    rating: Optional[float] = None
    maximum_marks: float
    earned_marks: Optional[float] = None
    earned_marks_raw: Optional[float] = None
    is_assessed: bool
    reason: str = ""
    evidence: List[Any] = []
    anchors: Dict[int, str] = {}


class TopicGroupSummary(BaseModel):
    group_id: str
    title: str
    phase: str
    main_question: str
    followup_count: int
    revisions_count: int
    eligible_criteria: List[str]


class CoachingObservations(BaseModel):
    note: str
    facial_expressions: Optional[Dict[str, Any]] = None
    eye_contact_percent: Optional[float] = None
    face_present_percent: Optional[float] = None
    posture: Optional[Dict[str, Any]] = None


class RubricAssessmentResponse(BaseModel):
    rubric_version: str
    job_role: str
    difficulty: str
    assessment_status: str  # "complete" | "partial" | "unassessed"
    total_score_100: Optional[float] = None
    provisional_normalized_100: Optional[float] = None
    assessed_score: float
    assessed_score_raw: float
    assessed_maximum: float
    coverage_percent: float
    missing_criteria: List[str]
    criteria: Dict[str, CriterionResult]
    rating_source: str
    review_status: str
    topic_groups: List[TopicGroupSummary] = []
    coaching_observations: Optional[CoachingObservations] = None


class RubricAssessSessionRequest(BaseModel):
    session_id: Optional[str] = None
    job_role: str
    difficulty: str = "Medium"
    turns: List[Dict[str, Any]] = []
    spoken_delivery_rating: Optional[float] = None
    coaching_observations: Optional[Dict[str, Any]] = None


class ManualCriterionOverrideRequest(BaseModel):
    session_id: str
    criterion_id: str
    rating: float
    reason: str
    reviewer_notes: Optional[str] = None
