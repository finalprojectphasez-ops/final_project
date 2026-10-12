"""
Rubric Package for PreMock AI 100-Mark Assessment.
Version: interview_practice_100_v1
"""

from app.rubric.config import (
    RUBRIC_VERSION,
    RUBRIC_CRITERIA,
    TOTAL_MAX_MARKS,
    ORDERED_CRITERIA_KEYS,
    GROUP_ELIGIBILITY_RULES,
)
from app.rubric.calculator import (
    RubricValidationError,
    validate_criterion_rating,
    calculate_criterion_marks,
    compute_rubric_assessment,
)
from app.rubric.aggregator import (
    TopicGroup,
    build_topic_groups_from_history,
    aggregate_criterion_ratings_across_groups,
)
from app.rubric.evaluator import (
    LocalRubricEvaluator,
    rubric_evaluator,
)

__all__ = [
    "RUBRIC_VERSION",
    "RUBRIC_CRITERIA",
    "TOTAL_MAX_MARKS",
    "ORDERED_CRITERIA_KEYS",
    "GROUP_ELIGIBILITY_RULES",
    "RubricValidationError",
    "validate_criterion_rating",
    "calculate_criterion_marks",
    "compute_rubric_assessment",
    "TopicGroup",
    "build_topic_groups_from_history",
    "aggregate_criterion_ratings_across_groups",
    "LocalRubricEvaluator",
    "rubric_evaluator",
]
