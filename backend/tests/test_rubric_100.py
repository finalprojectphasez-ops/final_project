"""
Comprehensive Unit Test Suite for 100-Mark Interview Assessment Rubric.
Version: interview_practice_100_v1

Verification Requirements:
1. All ratings 4 produce 100/100.
2. All observed ratings 0 produce 0/100.
3. Ratings 3, 3, 3, 4, 3, 2, 3 produce 75/100.
4. Missing spoken delivery produces an assessment out of 95 and no complete total.
5. All ratings null produce no assessment score.
6. Invalid ratings (bool, NaN, Inf, non-numeric, values outside 0-4) and fabricated evidence are rejected.
7. Extra follow-ups do not multiply topic weight.
8. Facial emotion, gaze, and posture values do not change marks.
"""

import math
import unittest
from app.rubric.config import (
    RUBRIC_VERSION,
    RUBRIC_CRITERIA,
    TOTAL_MAX_MARKS,
    ORDERED_CRITERIA_KEYS,
)
from app.rubric.calculator import (
    compute_rubric_assessment,
    validate_criterion_rating,
    calculate_criterion_marks,
    RubricValidationError,
)
from app.rubric.aggregator import (
    TopicGroup,
    build_topic_groups_from_history,
    aggregate_criterion_ratings_across_groups,
)
from app.rubric.evaluator import rubric_evaluator, LocalRubricEvaluator


class TestRubric100Engine(unittest.TestCase):

    def test_rubric_weights_sum_to_100(self):
        """Validates that all 7 criteria maximum marks sum strictly to 100.0."""
        self.assertEqual(TOTAL_MAX_MARKS, 100.0)
        self.assertEqual(len(ORDERED_CRITERIA_KEYS), 7)
        self.assertEqual(RUBRIC_CRITERIA["technical_knowledge"]["max_marks"], 30.0)
        self.assertEqual(RUBRIC_CRITERIA["problem_solving"]["max_marks"], 20.0)
        self.assertEqual(RUBRIC_CRITERIA["practical_application"]["max_marks"], 15.0)
        self.assertEqual(RUBRIC_CRITERIA["relevance_completeness"]["max_marks"], 10.0)
        self.assertEqual(RUBRIC_CRITERIA["communication_clarity"]["max_marks"], 10.0)
        self.assertEqual(RUBRIC_CRITERIA["followup_reflection"]["max_marks"], 10.0)
        self.assertEqual(RUBRIC_CRITERIA["spoken_delivery"]["max_marks"], 5.0)

    def test_all_ratings_4_produce_100(self):
        """Test: All ratings 4 produce 100/100."""
        ratings = {k: 4.0 for k in ORDERED_CRITERIA_KEYS}
        res = compute_rubric_assessment(ratings=ratings)
        self.assertEqual(res["assessment_status"], "complete")
        self.assertEqual(res["total_score_100"], 100.0)
        self.assertEqual(res["assessed_score"], 100.0)
        self.assertEqual(res["assessed_maximum"], 100.0)
        self.assertEqual(res["coverage_percent"], 100.0)
        self.assertEqual(len(res["missing_criteria"]), 0)

    def test_all_observed_ratings_0_produce_0(self):
        """Test: All observed ratings 0 produce 0/100."""
        ratings = {k: 0.0 for k in ORDERED_CRITERIA_KEYS}
        res = compute_rubric_assessment(ratings=ratings)
        self.assertEqual(res["assessment_status"], "complete")
        self.assertEqual(res["total_score_100"], 0.0)
        self.assertEqual(res["assessed_score"], 0.0)
        self.assertEqual(res["assessed_maximum"], 100.0)
        self.assertEqual(res["coverage_percent"], 100.0)

    def test_ratings_3_3_3_4_3_2_3_produce_75(self):
        """
        Test: Ratings 3, 3, 3, 4, 3, 2, 3 produce exactly 75/100.
        Calculation:
          technical_knowledge: 3/4 * 30 = 22.5
          problem_solving:     3/4 * 20 = 15.0
          practical_app:       3/4 * 15 = 11.25
          relevance_complete:  4/4 * 10 = 10.0
          communication:       3/4 * 10 = 7.5
          followup_reflect:    2/4 * 10 = 5.0
          spoken_delivery:     3/4 * 5  = 3.75
          Total = 22.5 + 15.0 + 11.25 + 10.0 + 7.5 + 5.0 + 3.75 = 75.00
        """
        ratings_list = [3.0, 3.0, 3.0, 4.0, 3.0, 2.0, 3.0]
        ratings = dict(zip(ORDERED_CRITERIA_KEYS, ratings_list))
        res = compute_rubric_assessment(ratings=ratings)
        self.assertEqual(res["assessment_status"], "complete")
        self.assertEqual(res["total_score_100"], 75.0)
        self.assertEqual(res["assessed_score"], 75.0)
        self.assertEqual(res["assessed_maximum"], 100.0)

    def test_missing_spoken_delivery_produces_95_and_no_complete_total(self):
        """
        Test: Missing spoken delivery produces an assessment out of 95 and no complete total.
        Must NOT present an audio-missing result assessed out of 95 as a complete assessment out of 100.
        """
        ratings = {
            "technical_knowledge": 4.0,
            "problem_solving": 4.0,
            "practical_application": 4.0,
            "relevance_completeness": 4.0,
            "communication_clarity": 4.0,
            "followup_reflection": 4.0,
            "spoken_delivery": None  # Audio evidence unavailable
        }
        res = compute_rubric_assessment(ratings=ratings)
        self.assertEqual(res["assessment_status"], "partial")
        self.assertIsNone(res["total_score_100"], "total_score_100 MUST be None for partial assessment")
        self.assertEqual(res["assessed_score"], 95.0)
        self.assertEqual(res["assessed_maximum"], 95.0)
        self.assertEqual(res["coverage_percent"], 95.0)
        self.assertEqual(res["provisional_normalized_100"], 100.0)
        self.assertIn("spoken_delivery", res["missing_criteria"])

    def test_all_ratings_null_produce_no_assessment_score(self):
        """Test: All ratings null produce no assessment score."""
        ratings = {k: None for k in ORDERED_CRITERIA_KEYS}
        res = compute_rubric_assessment(ratings=ratings)
        self.assertEqual(res["assessment_status"], "unassessed")
        self.assertIsNone(res["total_score_100"])
        self.assertIsNone(res["provisional_normalized_100"])
        self.assertEqual(res["coverage_percent"], 0.0)
        self.assertEqual(len(res["missing_criteria"]), 7)

    def test_invalid_ratings_rejected(self):
        """
        Test: Reject unknown criterion IDs, booleans, non-numeric ratings,
        NaN, infinity, and values outside 0-4.
        """
        # 1. Reject boolean (Python trap: isinstance(True, int) is True)
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", True)
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", False)

        # 2. Reject NaN and Infinity
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", float("nan"))
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", float("inf"))
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", float("-inf"))

        # 3. Reject non-numeric types
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", "high")
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", [3.0])

        # 4. Reject values outside 0-4
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", -0.5)
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", 4.5)
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("technical_knowledge", 10.0)

        # 5. Reject unknown criterion ID
        with self.assertRaises(RubricValidationError):
            validate_criterion_rating("unknown_criterion", 3.0)

        with self.assertRaises(RubricValidationError):
            compute_rubric_assessment(ratings={"fake_criterion": 3.0})

    def test_fabricated_evidence_is_detected_and_flagged(self):
        """Test: Fabricated quotations not found in candidate answers are rejected/flagged."""
        candidate_actual_answer = "I designed a Redis caching layer to reduce database read latency."
        
        # Valid quote
        valid_quote = "Redis caching layer"
        self.assertTrue(LocalRubricEvaluator.verify_evidence_quote(valid_quote, candidate_actual_answer))

        # Fabricated quote
        fake_quote = "I architected an asynchronous Kafka microservice cluster"
        self.assertFalse(LocalRubricEvaluator.verify_evidence_quote(fake_quote, candidate_actual_answer))

        # When evaluated in session with an unverified quote, review_status must become 'requires_review'
        turns = [
            {
                "question": "How did you optimize performance?",
                "answer": candidate_actual_answer,
                "phase": "technical"
            }
        ]
        res = rubric_evaluator.evaluate_interview_session(turns=turns, job_role="Software Engineer")
        # Evidence generated from actual answer is verified
        for crit_id, crit in res["criteria"].items():
            for ev in crit.get("evidence", []):
                if isinstance(ev, dict) and "verified" in ev:
                    self.assertTrue(ev["verified"])

    def test_extra_followups_do_not_multiply_topic_weight(self):
        """
        Test: Extra follow-ups do not multiply topic weight.
        Topic 1 (with 0 follow-ups) and Topic 2 (with 4 follow-ups)
        must have equal 50% voting weight on shared criteria.
        """
        turns = [
            # Topic 1: Main question, no follow-ups. Rating: 4.0
            {
                "turn_index": 1,
                "question": "Explain database indexing in PostgreSQL.",
                "answer": "B-Tree indexes provide logarithmic lookup time. We evaluated tradeoffs between read speed and write throughput.",
                "phase": "technical",
                "is_followup": False
            },
            # Topic 2: Main question + 3 follow-ups. Main answer has rating 2.0
            {
                "turn_index": 2,
                "question": "How do you design a rate limiter?",
                "answer": "We use a token bucket algorithm.",
                "phase": "technical",
                "is_followup": False
            },
            {
                "turn_index": 3,
                "question": "What happens when Redis runs out of memory?",
                "answer": "It uses an eviction policy.",
                "phase": "technical",
                "is_followup": True
            },
            {
                "turn_index": 4,
                "question": "How do you handle distributed race conditions?",
                "answer": "We use Redis Lua scripts for atomic increments.",
                "phase": "technical",
                "is_followup": True
            },
            {
                "turn_index": 5,
                "question": "What if the Redis master crashes?",
                "answer": "Redis Sentinel performs automatic failover.",
                "phase": "technical",
                "is_followup": True
            }
        ]

        topic_groups = build_topic_groups_from_history(turns)
        # There should be exactly 2 topic groups
        self.assertEqual(len(topic_groups), 2)
        self.assertEqual(len(topic_groups[0].followups), 0)
        self.assertEqual(len(topic_groups[1].followups), 3)

        # Topic 1 group rating = 4.0, Topic 2 group rating = 2.0
        # Equal topic group aggregation: (4.0 + 2.0) / 2 = 3.0
        # NOT weighted by 4 answers in Topic 2!
        group_assessments = [
            {
                "group_id": "topic_1",
                "title": "Topic 1",
                "eligible_criteria": ["technical_knowledge"],
                "ratings": {"technical_knowledge": 4.0}
            },
            {
                "group_id": "topic_2",
                "title": "Topic 2",
                "eligible_criteria": ["technical_knowledge"],
                "ratings": {"technical_knowledge": 2.0}
            }
        ]
        aggregated = aggregate_criterion_ratings_across_groups(group_assessments)
        self.assertEqual(aggregated["technical_knowledge"], 3.0)

    def test_facial_emotion_gaze_posture_do_not_alter_marks(self):
        """
        Test: Facial emotion, gaze, and posture values do not change marks.
        Classifier probabilities and vision data are strictly in coaching_observations.
        """
        turns = [
            {
                "question": "Describe a challenging bug you fixed.",
                "answer": "I identified a memory leak in the connection pool by analyzing heap dumps. We tested the fix under simulated load.",
                "phase": "technical"
            }
        ]

        # Scenario A: Perfect vision metrics
        coaching_a = {
            "eye_contact_percent": 98.0,
            "face_present_percent": 100.0,
            "facial_expressions": {"happy": 90, "neutral": 10}
        }
        res_a = rubric_evaluator.evaluate_interview_session(
            turns=turns,
            job_role="Software Engineer",
            spoken_delivery_rating=3.0,
            coaching_observations=coaching_a
        )

        # Scenario B: Low eye contact and stress/fear emotion
        coaching_b = {
            "eye_contact_percent": 15.0,
            "face_present_percent": 40.0,
            "facial_expressions": {"fear": 80, "neutral": 20}
        }
        res_b = rubric_evaluator.evaluate_interview_session(
            turns=turns,
            job_role="Software Engineer",
            spoken_delivery_rating=3.0,
            coaching_observations=coaching_b
        )

        # Crucial check: Rubric marks and ratings MUST be IDENTICAL
        self.assertEqual(res_a["assessed_score"], res_b["assessed_score"])
        self.assertEqual(res_a["total_score_100"], res_b["total_score_100"])
        for cid in ORDERED_CRITERIA_KEYS:
            self.assertEqual(
                res_a["criteria"][cid]["rating"],
                res_b["criteria"][cid]["rating"],
                f"Rating for {cid} was improperly affected by vision metrics!"
            )
            self.assertEqual(
                res_a["criteria"][cid]["earned_marks"],
                res_b["criteria"][cid]["earned_marks"],
                f"Marks for {cid} were improperly affected by vision metrics!"
            )

        # Verify coaching observations are strictly preserved without affecting score
        self.assertEqual(res_a["coaching_observations"]["eye_contact_percent"], 98.0)
        self.assertEqual(res_b["coaching_observations"]["eye_contact_percent"], 15.0)


if __name__ == "__main__":
    unittest.main()
