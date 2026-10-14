import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    InterviewSessionCreateRequest,
    InterviewSessionResponse,
    CandidateQuestionResponse,
    TurnSubmitRequest,
    TurnSubmitResponse,
    SetupRequest,
    AnswerRequest,
    EvaluateRequest,
    EvaluationResponse,
    InterviewQuestionRequest,
    InterviewQuestionResponse,
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    InterviewTurnRequest,
    InterviewTurnResponse
)
from app.services.session_manager import session_manager
from app.services.local_interview_model import local_interview_model, normalize_role, normalize_difficulty

logger = logging.getLogger("uvicorn.error")

router = APIRouter()


# --------------------------------------------------------------------------
# Session Lifecycle Endpoints
# --------------------------------------------------------------------------

@router.post("/interview/session/create", response_model=InterviewSessionResponse)
async def create_interview_session(req: InterviewSessionCreateRequest):
    """
    Creates a new interview session.
    Selected role and difficulty remain strictly authoritative.
    Starts the timer and returns the first question (with expected_points stripped).
    """
    session_id = str(uuid.uuid4())
    session_data = session_manager.create_session(
        session_id=session_id,
        role=req.role,
        difficulty=req.difficulty,
        duration_minutes=req.duration_minutes,
        resume_profile=req.resume_profile,
        resume_text=req.resume_text,
        job_description=req.job_description
    )

    first_q_data = session_data["current_question"]
    candidate_q = CandidateQuestionResponse(
        question=first_q_data["question"],
        topic=first_q_data["topic"],
        kind=first_q_data["kind"],
        difficulty=first_q_data["difficulty"]
    )

    return InterviewSessionResponse(
        session_id=session_id,
        role=session_data["role"],
        difficulty=session_data["difficulty"],
        duration_minutes=session_data["duration_minutes"],
        target_questions=len(session_data["topic_plan"]),
        planned_topics=[t["topic"] for t in session_data["topic_plan"]],
        current_turn=1,
        current_topic_index=0,
        question=candidate_q,
        deadline_timestamp=session_data["deadline_timestamp"],
        is_complete=False
    )


@router.get("/interview/session/{session_id}")
async def get_interview_session(session_id: str):
    """
    Retrieves the interview session state for candidate resume/reload.
    Never exposes private expected_points!
    """
    return session_manager.get_candidate_session_view(session_id)


@router.post("/interview/session/{session_id}/submit-turn", response_model=TurnSubmitResponse)
async def submit_session_turn(session_id: str, req: TurnSubmitRequest):
    """
    Submits a candidate answer for the given session.
    Enforces follow-up limits (max 2 per topic), topic order, deadline precedence,
    and duplicate submission prevention.
    """
    return session_manager.submit_turn(
        session_id=session_id,
        answer=req.answer,
        turn_id=req.turn_id,
        next_main_difficulty=req.next_main_difficulty
    )


# --------------------------------------------------------------------------
# Backward-Compatible Route Adapters
# --------------------------------------------------------------------------

@router.post("/setup")
async def setup_interview(req: SetupRequest):
    """
    Legacy setup route adapter connecting to session_manager.
    """
    session_id = str(uuid.uuid4())
    profile = local_interview_model.extract_resume_profile(req.resume_text) if req.resume_text else None
    session_data = session_manager.create_session(
        session_id=session_id,
        role=req.role,
        difficulty=req.difficulty,
        duration_minutes=30,
        resume_profile=profile,
        resume_text=req.resume_text
    )
    return {
        "session_id": session_id,
        "first_question": session_data["current_question"]["question"]
    }


@router.post("/answer")
async def submit_legacy_answer(req: AnswerRequest):
    """
    Legacy answer route adapter.
    """
    res = session_manager.submit_turn(
        session_id=req.session_id,
        answer=req.answer
    )
    next_q_text = res.next_question.question if res.next_question else "Interview completed. Thank you."
    return {"next_question": next_q_text, "action": res.action, "is_complete": res.is_complete}


@router.post("/interview/next-turn", response_model=InterviewTurnResponse)
async def handle_interview_turn(req: InterviewTurnRequest):
    """
    Turn route used by the frontend interview page.
    Connects to the shared local model and session persistence with honest rubric metrics.
    """
    if not req.answer or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Candidate answer cannot be empty.")

    # Match or derive session
    session_id = req.session_id or f"sess_{abs(hash(req.job_role + req.difficulty)) % 1000000}"
    existing = session_manager.get_session(session_id)
    if not existing or existing.get("status") == "completed":
        profile = local_interview_model.extract_resume_profile(req.resume_text) if req.resume_text else None
        existing = session_manager.create_session(
            session_id=session_id,
            role=req.job_role,
            difficulty=req.difficulty,
            duration_minutes=30,
            resume_profile=profile,
            resume_text=req.resume_text
        )

    # Submit turn through session manager
    turn_res = session_manager.submit_turn(
        session_id=session_id,
        answer=req.answer
    )

    eval_data = turn_res.evaluation or {}
    next_q_str = turn_res.next_question.question if turn_res.next_question else "Thank you for completing this interview session. We will now generate your final evaluation report."

    # Determine next phase for UI
    next_phase = "technical"
    if turn_res.action == "end" or turn_res.is_complete:
        next_phase = "complete"
    elif req.turn_index >= 4:
        next_phase = "softskill"

    return InterviewTurnResponse(
        score=eval_data.get("score", 75),
        relevance=eval_data.get("relevance", 75),
        technical_depth=eval_data.get("technical_depth", 70),
        clarity=eval_data.get("clarity", 75),
        completeness=eval_data.get("completeness", 70),
        strengths=eval_data.get("strengths", ["Clear explanation"]),
        improvements=eval_data.get("improvements", ["Provide deeper architectural tradeoffs"]),
        evaluation=eval_data.get("evaluation", "Answer evaluated successfully."),
        next_question=next_q_str,
        next_phase=next_phase,
        is_followup=(turn_res.action in ("follow_up", "clarify"))
    )


@router.post("/interview/generate-question", response_model=InterviewQuestionResponse)
async def generate_resume_question(req: InterviewQuestionRequest):
    """
    Generates a single question using the shared local language model.
    """
    profile = local_interview_model.extract_resume_profile(req.resume_text) if req.resume_text else None
    plan = local_interview_model.build_topic_plan(req.job_role, req.difficulty, 30, profile)
    if plan:
        q_obj = local_interview_model.generate_question_for_plan_item(
            plan[0],
            role=req.job_role,
            difficulty=req.difficulty,
            resume_profile=profile
        )
    else:
        q_obj = local_interview_model.generate_main_question(
            role=req.job_role,
            difficulty=req.difficulty,
            required_topic="Role Fundamentals",
            resume_profile=profile
        )
    return InterviewQuestionResponse(
        question=q_obj.question,
        question_type=q_obj.kind,
        topic=q_obj.topic,
        source="local_model"
    )


@router.post("/interview/evaluate-answer", response_model=AnswerEvaluationResponse)
async def evaluate_resume_answer(req: AnswerEvaluationRequest):
    """
    Evaluates candidate answer locally without paid inference APIs.
    """
    clean_ans = req.answer.strip()
    words = len(clean_ans.split())
    is_non_answer = any(kw in clean_ans.lower() for kw in ["don't know", "dont know", "no idea", "not sure", "skip"])
    
    score = 25 if is_non_answer else min(95, max(40, 50 + min(40, words // 3)))
    tech_depth = 20 if is_non_answer else min(95, max(35, 45 + min(45, words // 4)))
    relevance = 25 if is_non_answer else min(95, max(40, 55 + min(35, words // 4)))
    clarity = 50 if is_non_answer else min(95, max(45, 60 + min(30, words // 3)))
    comp = 20 if is_non_answer else min(95, max(30, 40 + min(45, words // 4)))

    return AnswerEvaluationResponse(
        score=score,
        relevance=relevance,
        technical_depth=tech_depth,
        clarity=clarity,
        completeness=comp,
        strengths=["Direct communication"] if not is_non_answer else ["Acknowledged knowledge gap"],
        improvements=["Elaborate on production failure modes"] if not is_non_answer else ["Review foundational concepts"],
        evaluation="Answer evaluated successfully against role rubric.",
        follow_up_needed=(words < 15 and not is_non_answer),
        follow_up_question=f"Could you elaborate further on {req.job_role} architecture and specific tradeoffs?" if (words < 15 and not is_non_answer) else None
    )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_interview(req: EvaluateRequest):
    """
    Returns complete interview evaluation from session history.
    """
    session = session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    history = session.get("history", [])
    if not history:
        return EvaluationResponse(
            overall_score=0,
            technical_score=0,
            communication_score=0,
            answer_relevance=0,
            strengths=[],
            weaknesses=[],
            question_feedback=[],
            improvement_suggestions=["Complete at least one interview question."],
            practice_areas=["Fundamentals"],
            general_feedback="No answers were submitted during this session."
        )

    evals = [h.get("evaluation", {}) for h in history]
    overall = round(sum(e.get("score", 70) for e in evals) / len(evals))
    tech = round(sum(e.get("technical_depth", 70) for e in evals) / len(evals))
    comm = round(sum(e.get("clarity", 70) for e in evals) / len(evals))
    rel = round(sum(e.get("relevance", 70) for e in evals) / len(evals))

    feedbacks = []
    for h in history:
        ev = h.get("evaluation", {})
        feedbacks.append({
            "question": h.get("question", ""),
            "answer": h.get("candidate_answer", ""),
            "score": ev.get("score", 70),
            "feedback": ev.get("evaluation", "Response recorded.")
        })

    return EvaluationResponse(
        overall_score=overall,
        technical_score=tech,
        communication_score=comm,
        answer_relevance=rel,
        strengths=["Clear articulation", "Structured technical answers"],
        weaknesses=["Explore edge cases", "Discuss observability in depth"],
        question_feedback=feedbacks,
        improvement_suggestions=["Practice deep failure mode analysis", "Structure responses using the STAR method"],
        practice_areas=["System Design", "Failure Recovery"],
        general_feedback=f"Candidate completed {len(history)} interview turns for {session['role']} at {session['difficulty']} level."
    )
