import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.schemas import SetupRequest, AnswerRequest, InterviewContext
from app.services.llm_engine import LLMEngine
from app.services.audio_parser import AudioStreamParser

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
        return {"error": "Session not found. It may have expired."}, 404
    next_q = await engine.get_next_question(user_answer=req.answer)
    return {"next_question": next_q}

@router.websocket("/stream/{session_id}")
async def interview_audio_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    audio_parser = AudioStreamParser(client_ws=websocket)
    await audio_parser.start_listening()
    try:
        while True:
            data = await websocket.receive_bytes()
            audio_parser.process_audio_chunk(data)
    except WebSocketDisconnect:
        audio_parser.close()
        print(f"Client disconnected from session {session_id}")
