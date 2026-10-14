"""
Unittest test suite wrapper for Experiment 1: Workflow & Rubric Invariants.
Enables execution via `python -m unittest discover` or `pytest`.
"""

import unittest
import os
import sys

# Ensure backend and script directories are in path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
EXP1_DIR = os.path.abspath(os.path.dirname(__file__))
for p in (BACKEND_DIR, EXP1_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from run_experiment_1 import (
    run_existing_rubric_tests,
    execute_scripted_cases,
    verify_evidence_quote_matching,
    verify_topic_weights_aggregation_invariant,
    verify_missing_signals_handling
)


class TestExperiment1WorkflowRubric(unittest.TestCase):

    def test_existing_rubric_unit_tests_pass(self):
        res = run_existing_rubric_tests()
        self.assertTrue(res["was_successful"])
        self.assertEqual(res["failures"], 0)
        self.assertEqual(res["errors"], 0)

    def test_all_18_scripted_matrix_cases_pass_invariants(self):
        res = execute_scripted_cases()
        self.assertEqual(res["total_combinations"], 18)
        self.assertTrue(res["all_passed"])

    def test_evidence_quote_matching_and_hallucination_flagging(self):
        res = verify_evidence_quote_matching()
        self.assertTrue(res["pass"])

    def test_topic_group_aggregation_prevents_followup_inflation(self):
        res = verify_topic_weights_aggregation_invariant()
        self.assertTrue(res["pass"])
        self.assertEqual(res["topic_group_rating"], 3.0)
        self.assertNotEqual(res["topic_group_rating"], res["naive_turn_rating"])

    def test_missing_signals_partial_scoring_rules(self):
        res = verify_missing_signals_handling()
        self.assertTrue(res["pass"])


if __name__ == "__main__":
    unittest.main()
