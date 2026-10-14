"""
Deterministic 100-Mark Rubric Calculation Engine.
Strict mathematical calculation following rubric version: interview_practice_100_v1.
"""

import math
from typing import Dict, Any, Optional, List
from app.rubric.config import (
    RUBRIC_VERSION,
    RUBRIC_CRITERIA,
    TOTAL_MAX_MARKS,
    ORDERED_CRITERIA_KEYS,
)


class RubricValidationError(ValueError):
    """Raised when rating inputs violate deterministic rubric constraints."""
    pass


def validate_criterion_rating(criterion_id: str, rating: Any) -> Optional[float]:
    """
    Validates a criterion rating according to rubric rules:
      - Criterion ID must exist in rubric
      - None indicates unavailable evidence / not fairly assessed (valid)
      - Must NOT be a boolean (e.g. True/False)
      - Must be a finite numeric type (int or float)
      - Must not be NaN or Infinity
      - Must be between 0.0 and 4.0 inclusive
    """
    if criterion_id not in RUBRIC_CRITERIA:
        raise RubricValidationError(f"Unknown criterion ID: '{criterion_id}'")

    if rating is None:
        return None

    # In Python, bool is a subclass of int (isinstance(True, int) == True)
    if isinstance(rating, bool):
        raise RubricValidationError(
            f"Invalid rating for '{criterion_id}': booleans are rejected, got {rating}"
        )

    if not isinstance(rating, (int, float)):
        raise RubricValidationError(
            f"Invalid rating for '{criterion_id}': numeric value expected, got {type(rating).__name__}"
        )

    if math.isnan(rating) or math.isinf(rating):
        raise RubricValidationError(
            f"Invalid rating for '{criterion_id}': NaN and Infinity are rejected"
        )

    float_val = float(rating)
    if float_val < 0.0 or float_val > 4.0:
        raise RubricValidationError(
            f"Invalid rating for '{criterion_id}': rating must be between 0 and 4, got {float_val}"
        )

    return float_val


def calculate_criterion_marks(criterion_id: str, rating: Optional[float]) -> Optional[float]:
    """
    Calculates marks for a single criterion using full precision:
      criterion_marks = criterion_rating / 4.0 * maximum_marks
    Returns None if rating is None.
    """
    if rating is None:
        return None
    max_marks = RUBRIC_CRITERIA[criterion_id]["max_marks"]
    return (rating / 4.0) * max_marks


def compute_rubric_assessment(
    ratings: Dict[str, Any],
    job_role: str = "General",
    difficulty: str = "Medium",
    reasons: Optional[Dict[str, str]] = None,
    evidence: Optional[Dict[str, List[Any]]] = None,
    rating_source: str = "local_model",
    review_status: str = "verified"
) -> Dict[str, Any]:
    """
    Computes deterministic interview-level assessment across all rubric criteria.
    Full precision is preserved internally; display scores are rounded to 2 decimals.
    """
    if TOTAL_MAX_MARKS != 100.0:
        raise RubricValidationError(f"Rubric configuration error: total marks must be 100.0, got {TOTAL_MAX_MARKS}")

    reasons = reasons or {}
    evidence = evidence or {}

    # Reject unknown criterion IDs passed in dictionary
    for k in ratings.keys():
        if k not in RUBRIC_CRITERIA:
            raise RubricValidationError(f"Unknown criterion ID in ratings: '{k}'")

    validated_ratings: Dict[str, Optional[float]] = {}
    criteria_results: Dict[str, Dict[str, Any]] = {}

    assessed_score_raw = 0.0
    assessed_max_raw = 0.0
    missing_criteria: List[str] = []

    for criterion_id in ORDERED_CRITERIA_KEYS:
        raw_val = ratings.get(criterion_id)
        val = validate_criterion_rating(criterion_id, raw_val)
        validated_ratings[criterion_id] = val

        max_marks = RUBRIC_CRITERIA[criterion_id]["max_marks"]
        marks_raw = calculate_criterion_marks(criterion_id, val)

        is_assessed = val is not None
        if is_assessed:
            assessed_score_raw += marks_raw
            assessed_max_raw += max_marks
        else:
            missing_criteria.append(criterion_id)

        criteria_results[criterion_id] = {
            "criterion_id": criterion_id,
            "name": RUBRIC_CRITERIA[criterion_id]["name"],
            "rating": val,
            "maximum_marks": max_marks,
            "earned_marks": round(marks_raw, 2) if marks_raw is not None else None,
            "earned_marks_raw": marks_raw,
            "is_assessed": is_assessed,
            "reason": reasons.get(criterion_id, ""),
            "evidence": evidence.get(criterion_id, []),
            "anchors": RUBRIC_CRITERIA[criterion_id]["anchors"]
        }

    # Coverage and Assessment Status
    coverage_percent = round((assessed_max_raw / TOTAL_MAX_MARKS) * 100.0, 2)

    if assessed_max_raw == 0.0:
        assessment_status = "unassessed"
        total_score_100 = None
        provisional_normalized_100 = None
    elif len(missing_criteria) == 0 and assessed_max_raw == 100.0:
        assessment_status = "complete"
        total_score_100 = round(assessed_score_raw, 2)
        provisional_normalized_100 = total_score_100
    else:
        assessment_status = "partial"
        total_score_100 = None  # Do NOT present partial score out of 100!
        provisional_normalized_100 = round((assessed_score_raw / assessed_max_raw) * 100.0, 2)

    return {
        "rubric_version": RUBRIC_VERSION,
        "job_role": job_role,
        "difficulty": difficulty,
        "assessment_status": assessment_status,
        "total_score_100": total_score_100,
        "provisional_normalized_100": provisional_normalized_100,
        "assessed_score": round(assessed_score_raw, 2) if assessed_max_raw > 0 else 0.0,
        "assessed_score_raw": assessed_score_raw,
        "assessed_maximum": round(assessed_max_raw, 2),
        "coverage_percent": coverage_percent,
        "missing_criteria": missing_criteria,
        "criteria": criteria_results,
        "rating_source": rating_source,
        "review_status": review_status,
    }
