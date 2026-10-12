"""
FastAPI Routes for 100-Mark Interview Assessment Rubric.
Version: interview_practice_100_v1
"""

import os
import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from app.rubric.config import (
    RUBRIC_VERSION,
    RUBRIC_CRITERIA,
    TOTAL_MAX_MARKS,
    ORDERED_CRITERIA_KEYS,
)
from app.rubric.evaluator import rubric_evaluator
from app.rubric.calculator import compute_rubric_assessment, validate_criterion_rating
from app.rubric.schemas import (
    RubricAssessmentResponse,
    RubricAssessSessionRequest,
    ManualCriterionOverrideRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

REPORTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
)


@router.get("/config")
async def get_rubric_config():
    """Returns the versioned rubric configuration, criteria, weights, and anchors."""
    return {
        "rubric_version": RUBRIC_VERSION,
        "total_max_marks": TOTAL_MAX_MARKS,
        "criteria": RUBRIC_CRITERIA,
        "ordered_keys": ORDERED_CRITERIA_KEYS
    }


@router.post("/assess", response_model=RubricAssessmentResponse)
async def assess_interview(req: RubricAssessSessionRequest):
    """
    Executes deterministic 100-mark interview rubric evaluation using local inference.
    No paid or external AI APIs.
    """
    try:
        result = rubric_evaluator.evaluate_interview_session(
            turns=req.turns,
            job_role=req.job_role,
            difficulty=req.difficulty,
            spoken_delivery_rating=req.spoken_delivery_rating,
            coaching_observations=req.coaching_observations
        )
        return result
    except Exception as e:
        logger.error(f"[RubricRoute] Assessment error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rubric assessment failed: {str(e)}")


@router.post("/manual-review")
async def manual_criterion_override(req: ManualCriterionOverrideRequest):
    """
    Supports manual human assessment for spoken delivery or review overrides.
    """
    try:
        validate_criterion_rating(req.criterion_id, req.rating)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))

    # Look up report file
    file_path = os.path.join(REPORTS_DIR, f"{req.session_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        rubric_data = report_data.get("rubric_assessment")
        if not rubric_data:
            raise HTTPException(status_code=400, detail="Session does not have a rubric assessment to review")

        # Update rating
        current_ratings = {k: v.get("rating") for k, v in rubric_data.get("criteria", {}).items()}
        current_ratings[req.criterion_id] = req.rating

        reasons = {k: v.get("reason", "") for k, v in rubric_data.get("criteria", {}).items()}
        reasons[req.criterion_id] = f"Manual Review ({req.reason})"

        evidence = {k: v.get("evidence", []) for k, v in rubric_data.get("criteria", {}).items()}
        if req.reviewer_notes:
            evidence.setdefault(req.criterion_id, []).append({
                "source": "manual_reviewer",
                "notes": req.reviewer_notes
            })

        # Re-compute deterministically
        updated_assessment = compute_rubric_assessment(
            ratings=current_ratings,
            job_role=report_data.get("role", "General"),
            difficulty=report_data.get("difficulty", "Medium"),
            reasons=reasons,
            evidence=evidence,
            rating_source="hybrid_reviewed",
            review_status="verified"
        )
        updated_assessment["topic_groups"] = rubric_data.get("topic_groups", [])
        updated_assessment["coaching_observations"] = rubric_data.get("coaching_observations", {})

        report_data["rubric_assessment"] = updated_assessment
        report_data["overall_score"] = updated_assessment.get("total_score_100") or updated_assessment.get("provisional_normalized_100")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return {
            "status": "ok",
            "message": f"Criterion '{req.criterion_id}' updated successfully.",
            "rubric_assessment": updated_assessment
        }
    except Exception as e:
        logger.error(f"[RubricRoute] Review update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{session_id}")
async def export_rubric_provenance(session_id: str, format: str = Query("json", pattern="^(json|csv)$")):
    """
    Exports full interview provenance, candidate answer transcripts, verifiable quotes,
    ratings, criterion marks, and review status for human audit.
    """
    file_path = os.path.join(REPORTS_DIR, f"{session_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    with open(file_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    rubric_data = report_data.get("rubric_assessment") or {}

    if format == "json":
        return {
            "provenance": {
                "session_id": session_id,
                "rubric_version": rubric_data.get("rubric_version", RUBRIC_VERSION),
                "job_role": report_data.get("role"),
                "difficulty": report_data.get("difficulty"),
                "assessment_status": rubric_data.get("assessment_status"),
                "total_score_100": rubric_data.get("total_score_100"),
                "provisional_normalized_100": rubric_data.get("provisional_normalized_100"),
                "coverage_percent": rubric_data.get("coverage_percent"),
                "rating_source": rubric_data.get("rating_source"),
                "review_status": rubric_data.get("review_status"),
                "created_at": report_data.get("created_at"),
                "completed_at": report_data.get("completed_at")
            },
            "criteria_breakdown": rubric_data.get("criteria", {}),
            "topic_groups": rubric_data.get("topic_groups", []),
            "question_feedback": report_data.get("question_feedback", []),
            "coaching_observations": rubric_data.get("coaching_observations", {})
        }

    # CSV format
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Criterion ID", "Name", "Rating (0-4)", "Max Marks", "Earned Marks", "Status", "Reason"])
    criteria = rubric_data.get("criteria", {})
    for cid in ORDERED_CRITERIA_KEYS:
        c_obj = criteria.get(cid, {})
        writer.writerow([
            cid,
            c_obj.get("name", cid),
            c_obj.get("rating"),
            c_obj.get("maximum_marks"),
            c_obj.get("earned_marks"),
            "Assessed" if c_obj.get("is_assessed") else "Missing",
            c_obj.get("reason", "")
        ])

    return {
        "format": "csv",
        "csv_content": output.getvalue()
    }
