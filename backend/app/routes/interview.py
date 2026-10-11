import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.models.schemas import (
    SetupRequest, AnswerRequest, InterviewContext, EvaluateRequest, EvaluationResponse,
    InterviewQuestionRequest, InterviewQuestionResponse,
    AnswerEvaluationRequest, AnswerEvaluationResponse
)
from app.services.llm_engine import LLMEngine
from app.services.interview_llm_service import OpenRouterLLMService

router = APIRouter()

# In-memory store for active sessions
active_sessions = {}

@router.post("/setup")
async def setup_interview(req: SetupRequest):
    engine = LLMEngine(InterviewContext(
        role=req.role,
        difficulty=req.difficulty,
        resume_text=req.resume_text
    ))
    first_q = await engine.get_next_question()
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = engine
    return {"session_id": session_id, "first_question": first_q}

@router.post("/answer")
async def submit_answer(req: AnswerRequest):
    engine = active_sessions.get(req.session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Session not found. It may have expired.")
    next_q = await engine.get_next_question(user_answer=req.answer)
    return {"next_question": next_q}

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_interview(req: EvaluateRequest):
    engine = active_sessions.get(req.session_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Session not found. It may have expired.")
    
    # Generate the evaluation based on the stored history
    # Pass empty full_transcript since the engine already has the history
    evaluation = await engine.generate_evaluation([])
    
    # Optionally, we can remove the session from active_sessions if we assume 
    # it won't be used again after evaluation, but leaving it for now is safer.
    
    return evaluation



# -------------------------------------------------------------------
# New Resume-Based AI Interview Engine Endpoints (OpenRouter API)
# -------------------------------------------------------------------

@router.post("/interview/generate-question", response_model=InterviewQuestionResponse)
async def generate_resume_question(req: InterviewQuestionRequest):
    service = OpenRouterLLMService()
    try:
        return await service.generate_question(
            resume_text=req.resume_text,
            job_role=req.job_role,
            difficulty=req.difficulty
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interview/evaluate-answer", response_model=AnswerEvaluationResponse)
async def evaluate_resume_answer(req: AnswerEvaluationRequest):
    if not req.answer or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Candidate answer cannot be empty.")
        
    service = OpenRouterLLMService()
    try:
        return await service.evaluate_answer(
            resume_text=req.resume_text,
            job_role=req.job_role,
            question=req.question,
            answer=req.answer
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
