import os
import json
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Body

logger = logging.getLogger(__name__)

router = APIRouter()

REPORTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
)
os.makedirs(REPORTS_DIR, exist_ok=True)


def _ensure_rubric_assessment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures 100-mark rubric assessment exists on report payload."""
    if not payload.get("rubric_assessment") and payload.get("question_feedback"):
        try:
            from app.rubric.evaluator import rubric_evaluator
            turns = [
                {
                    "turn_index": idx + 1,
                    "question": qf.get("question", ""),
                    "answer": qf.get("answer", ""),
                    "phase": qf.get("phase", "technical"),
                    "is_followup": bool(qf.get("follow_up_needed")),
                    "audio_present": True
                }
                for idx, qf in enumerate(payload.get("question_feedback", []))
            ]
            coaching_obs = {
                "facial_expressions": {
                    "neutral": payload.get("neutral_expr"),
                    "happy": payload.get("happy_expr"),
                    "sad": payload.get("sad_expr"),
                    "angry": payload.get("angry_expr"),
                    "disgust": payload.get("disgust_expr"),
                    "fear": payload.get("fear_expr"),
                    "surprise": payload.get("surprise_expr"),
                },
                "eye_contact_percent": payload.get("eye_contact"),
                "face_present_percent": payload.get("face_present")
            }
            rubric_res = rubric_evaluator.evaluate_interview_session(
                turns=turns,
                job_role=payload.get("role", "Software Engineer"),
                difficulty=payload.get("difficulty", "Medium"),
                spoken_delivery_rating=None,
                coaching_observations=coaching_obs
            )
            payload["rubric_assessment"] = rubric_res
            payload["rubric_version"] = rubric_res["rubric_version"]
            payload["total_score_100"] = rubric_res["total_score_100"]
            payload["provisional_normalized_100"] = rubric_res["provisional_normalized_100"]
            payload["assessment_status"] = rubric_res["assessment_status"]
            payload["coverage_percent"] = rubric_res["coverage_percent"]
        except Exception as e:
            logger.warning(f"Could not compute rubric assessment for report: {e}")
    return payload


@router.post("/save")
async def save_report(payload: Dict[str, Any] = Body(...)):
    """
    Saves the completed interview report persistently as JSON on disk.
    Always succeeds regardless of database or authentication state.
    """
    try:
        session_id = payload.get("id") or payload.get("backend_session_id")
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
            payload["id"] = session_id

        # Normalize key ids
        if "backend_session_id" not in payload:
            payload["backend_session_id"] = session_id

        payload = _ensure_rubric_assessment(payload)

        file_path = os.path.join(REPORTS_DIR, f"{session_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"Report persistently saved to {file_path}")
        return {
            "status": "ok",
            "id": session_id,
            "message": "Report saved successfully"
        }
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
@router.get("/")
async def list_reports() -> List[Dict[str, Any]]:
    """
    Returns all persistently saved interview reports, sorted newest first.
    """
    reports = []
    if not os.path.exists(REPORTS_DIR):
        return []

    for fname in os.listdir(REPORTS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(REPORTS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                reports.append(data)
        except Exception as e:
            logger.warning(f"Failed to read report {fname}: {e}")

    # Sort descending by completed_at or created_at
    reports.sort(
        key=lambda r: r.get("completed_at") or r.get("created_at") or "",
        reverse=True
    )
    return reports


@router.get("/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """
    Fetches a single report by id or backend_session_id.
    """
    file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return _ensure_rubric_assessment(data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read report: {e}")

    # Fallback search across all files if report_id differs from filename
    if os.path.exists(REPORTS_DIR):
        for fname in os.listdir(REPORTS_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(REPORTS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("id") == report_id or data.get("backend_session_id") == report_id:
                        return _ensure_rubric_assessment(data)
            except Exception:
                continue

    raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
