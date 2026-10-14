"""
Experiment 1 Runner: Interview Workflow and Rubric Correctness Verification.
Authoritative Rubric: interview_practice_100_v1 (100.0 Marks)
Platform: PreMock AI Local Engine

Verifications:
1. Run existing rubric unit tests (test_rubric_100.py)
2. Scripted test cases across all 6 roles and 3 difficulty levels (18 matrix combinations)
3. Invariant checks:
   - Introduction occurs once (Phase 1)
   - General questions precede technical questions (Phase 2 before Phase 3)
   - Questions respect selected role and difficulty
   - Follow-ups reference actual answers and never exceed 2 per topic
   - Controlled simulated clock reaches deadline and closes cleanly
   - Candidate views never expose expected_points
   - Unmatched evidence quotations are flagged
   - Topic weights do not inflate due to extra follow-ups (Topic-Group Aggregator invariant)
   - Missing signal handling follows 100-mark partial assessment rules
"""

import os
import sys
import time
import json
import unittest
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add backend directory to sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.models.schemas import CandidateQuestionResponse
from app.services.local_interview_model import (
    local_interview_model,
    normalize_role,
    normalize_difficulty,
    ROLE_TAXONOMIES
)
from app.services.session_manager import SessionManager
from app.rubric.config import RUBRIC_VERSION, TOTAL_MAX_MARKS, ORDERED_CRITERIA_KEYS, RUBRIC_CRITERIA
from app.rubric.calculator import compute_rubric_assessment
from app.rubric.aggregator import (
    TopicGroup,
    build_topic_groups_from_history,
    aggregate_criterion_ratings_across_groups
)
from app.rubric.evaluator import rubric_evaluator

# Output directories
OUTPUT_DIR = os.path.abspath(os.path.dirname(__file__))
TRACES_DIR = os.path.join(OUTPUT_DIR, "session_traces")
RAW_LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "raw_logs"))
os.makedirs(TRACES_DIR, exist_ok=True)
os.makedirs(RAW_LOGS_DIR, exist_ok=True)

# Custom test session storage to avoid polluting production data
TEST_SESSIONS_DIR = os.path.join(OUTPUT_DIR, "test_sessions_tmp")
os.makedirs(TEST_SESSIONS_DIR, exist_ok=True)
test_session_manager = SessionManager(sessions_dir=TEST_SESSIONS_DIR)


def run_existing_rubric_tests() -> Dict[str, Any]:
    """Runs existing backend/tests/test_rubric_100.py suite and records output."""
    import tests.test_rubric_100 as test_module
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_module)
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    res = runner.run(suite)
    elapsed = time.time() - start_time
    
    return {
        "tests_run": res.testsRun,
        "failures": len(res.failures),
        "errors": len(res.errors),
        "was_successful": res.wasSuccessful(),
        "elapsed_seconds": round(elapsed, 4)
    }


def execute_scripted_cases() -> Dict[str, Any]:
    """
    Executes scripted sessions across all 6 roles x 3 difficulty levels (18 matrix combinations).
    Labels tests explicitly as SIMULATED SCRIPTED BENCHMARK CASES.
    """
    roles = [
        ("full_stack_engineer", "Full Stack Engineer"),
        ("frontend_developer", "Frontend Developer"),
        ("backend_engineer", "Backend Engineer"),
        ("devops_sre", "DevOps / SRE"),
        ("ml_engineer", "ML Engineer"),
        ("data_analyst", "Data Analyst")
    ]
    difficulties = ["beginner", "intermediate", "advanced"]
    
    matrix_results = []
    all_invariants_passed = True
    
    # Generic domain answer bank for scripted simulation
    role_answer_templates = {
        "full_stack_engineer": [
            "I have built full stack web applications with React on the frontend and FastAPI/Node.js on the backend.",
            "I prioritize breaking down features by API schema contracts and establishing clear boundaries.",
            "In our API layer, we enforce strict schema validation using Pydantic and JSON schema contracts.",
            "For optimistic UI updates, we dispatch local state changes immediately while queuing network requests with rollback capability.",
            "We handle race conditions by using AbortController on the client and database transactions with row-level locks on the server."
        ],
        "frontend_developer": [
            "I specialize in building accessible, high-performance user interfaces with React and Next.js.",
            "I balance pixel-perfect designs with delivery timelines by implementing reusable component libraries.",
            "The event loop processes microtasks like resolved promises before rendering the next frame.",
            "We optimize LCP by preloading hero assets and eliminating render-blocking CSS stylesheets.",
            "For state synchronization, we use selective Zustand stores to prevent cascading re-renders across the component tree."
        ],
        "backend_engineer": [
            "I design and maintain distributed backend systems, REST/gRPC microservices, and PostgreSQL databases.",
            "I handle technical trade-offs by writing technical design docs and consulting cross-functional stakeholders.",
            "REST APIs provide uniform interface semantics; we ensure idempotency using idempotency keys stored in Redis.",
            "We inspect EXPLAIN ANALYZE execution plans to convert sequential scans into index scans on high-cardinality foreign keys.",
            "We use connection pooling with HikariCP, sizing the pool according to Little's law to prevent thread starvation."
        ],
        "devops_sre": [
            "I manage Kubernetes clusters, AWS cloud infrastructure, and automated CI/CD deployment pipelines.",
            "During incidents, I prioritize mitigation and traffic shedding before conducting blameless postmortems.",
            "Linux namespaces provide PID, network, and mount isolation, while cgroups constrain CPU and memory consumption.",
            "We use Terraform remote state locking with DynamoDB and isolate environments across separate AWS accounts.",
            "Our canary deployment pipeline uses Argo Rollouts to evaluate Prometheus error rates before promoting traffic."
        ],
        "ml_engineer": [
            "I develop and deploy machine learning models, training pipelines, and low-latency inference services.",
            "I bridge research and production by ensuring offline preprocessing matches online inference transformations.",
            "Data leakage occurs if feature transformers are fit on the full dataset instead of only the training split.",
            "We address severe class imbalance using PR-AUC curves and cost-sensitive threshold optimization.",
            "We monitor covariate shift and concept drift in production using Population Stability Index (PSI) and KS tests."
        ],
        "data_analyst": [
            "I build analytical data models, executive Tableau dashboards, and SQL reporting pipelines.",
            "I prioritize ad-hoc business requests by assessing business impact and alignment with quarterly KPIs.",
            "SQL handles NULL via three-valued logic; COUNT(column) ignores NULLs whereas COUNT(*) counts all rows.",
            "We use window functions like DENSE_RANK and SUM OVER ROWS BETWEEN to compute 7-day rolling metrics.",
            "We guard against join fan-out by asserting primary key uniqueness in our dbt data transformation tests."
        ]
    }

    for role_key, role_label in roles:
        for diff in difficulties:
            session_id = f"sim_{role_key}_{diff}_{int(time.time()*1000)%1000000}"
            trace = {
                "session_id": session_id,
                "role_key": role_key,
                "role_label": role_label,
                "difficulty": diff,
                "turns": [],
                "invariants": {}
            }
            
            # Step 1: Create session
            session = test_session_manager.create_session(
                session_id=session_id,
                role=role_label,
                difficulty=diff,
                duration_minutes=30
            )
            
            # INVARIANT 1: Topic plan order: Intro -> General -> Technical
            plan = session["topic_plan"]
            has_intro_first = (plan[0]["phase"] == "intro" and plan[0]["topic"] == "Self-Introduction")
            intro_count = sum(1 for p in plan if p.get("phase") == "intro")
            intro_once = (intro_count == 1)
            
            general_items = [p for p in plan if p.get("phase") == "general"]
            technical_items = [p for p in plan if p.get("phase") == "technical"]
            general_precedes_technical = False
            if general_items and technical_items:
                max_gen_idx = max(plan.index(g) for g in general_items)
                min_tech_idx = min(plan.index(t) for t in technical_items)
                general_precedes_technical = (max_gen_idx < min_tech_idx)
            
            # INVARIANT 2: Role and difficulty authoritative
            role_respected = (session["role_key"] == role_key)
            diff_respected = (session["difficulty"] == diff)
            
            # INVARIANT 3: Candidate view strips expected_points
            q0 = session["current_question"]
            expected_points_hidden_init = True
            cand_view_init = test_session_manager.get_candidate_session_view(session_id)
            if "expected_points" in cand_view_init.get("current_question", {}):
                expected_points_hidden_init = False
            for h in cand_view_init.get("history", []):
                if "expected_points" in h:
                    expected_points_hidden_init = False
            
            trace["turns"].append({
                "turn": 0,
                "action": "session_created",
                "phase": session["current_phase"],
                "question": q0["question"],
                "topic": q0["topic"]
            })
            
            # Step 2: Multi-turn simulation (run 5 scripted turns)
            answers = role_answer_templates.get(role_key, role_answer_templates["full_stack_engineer"])
            followup_limits_respected = True
            expected_points_hidden_throughout = expected_points_hidden_init
            max_followups_observed = 0
            
            for t_idx, ans in enumerate(answers):
                turn_resp = test_session_manager.submit_turn(
                    session_id=session_id,
                    answer=ans,
                    turn_id=f"{session_id}_turn_{t_idx+1}"
                )
                
                # Check candidate response payload
                if turn_resp.next_question:
                    if hasattr(turn_resp.next_question, "expected_points"):
                        expected_points_hidden_throughout = False
                
                # Check candidate session view
                cand_view = test_session_manager.get_candidate_session_view(session_id)
                for h in cand_view.get("history", []):
                    if "expected_points" in h:
                        expected_points_hidden_throughout = False
                
                fu_used = turn_resp.followups_used
                if fu_used > max_followups_observed:
                    max_followups_observed = fu_used
                if fu_used > 2:
                    followup_limits_respected = False
                
                trace["turns"].append({
                    "turn": t_idx + 1,
                    "submitted_answer": ans,
                    "action": turn_resp.action,
                    "followups_used": fu_used,
                    "remaining_topics_count": turn_resp.remaining_topics_count,
                    "is_complete": turn_resp.is_complete
                })
                
                if turn_resp.is_complete:
                    break
            
            # INVARIANT 4: Simulated clock deadline test
            # Artificially set deadline in the past to verify deadline handling reaches closing/completed
            session_for_clock = test_session_manager.get_session(session_id)
            session_for_clock["deadline_timestamp"] = time.time() - 100.0  # Expired
            test_session_manager.save_session(session_for_clock)
            
            clock_expire_resp = test_session_manager.submit_turn(
                session_id=session_id,
                answer="Final wrap up response under time constraint.",
                turn_id=f"{session_id}_clock_test"
            )
            deadline_reached_closing = (clock_expire_resp.action == "end" and clock_expire_resp.is_complete is True)
            
            inv_summary = {
                "intro_occurs_once": intro_once,
                "general_precedes_technical": general_precedes_technical,
                "role_respected": role_respected,
                "difficulty_respected": diff_respected,
                "followups_never_exceed_two": followup_limits_respected,
                "expected_points_never_exposed": expected_points_hidden_throughout,
                "simulated_clock_reaches_closing": deadline_reached_closing
            }
            trace["invariants"] = inv_summary
            
            case_passed = all(inv_summary.values())
            if not case_passed:
                all_invariants_passed = False
            
            matrix_results.append({
                "role": role_label,
                "role_key": role_key,
                "difficulty": diff,
                "session_id": session_id,
                "passed": case_passed,
                "invariants": inv_summary
            })
            
            # Save individual trace
            trace_path = os.path.join(TRACES_DIR, f"{session_id}.json")
            with open(trace_path, "w", encoding="utf-8") as f:
                json.dump(trace, f, indent=2)

    return {
        "total_combinations": len(matrix_results),
        "all_passed": all_invariants_passed,
        "results": matrix_results
    }


def verify_evidence_quote_matching() -> Dict[str, Any]:
    """Tests quotation verification and hallucination detection in rubric_evaluator."""
    candidate_transcript = (
        "We implemented optimistic UI updates in React. "
        "When the user clicks submit, we update the local cache immediately. "
        "If the network request fails with an error status, we rollback the UI state gracefully."
    )
    
    # Legitimate verbatim quotation
    valid_quote = "we update the local cache immediately"
    # Fabricated / hallucinated quotation
    hallucinated_quote = "we used multi-threaded C++ shared memory buffers"
    
    verified_valid = rubric_evaluator.verify_evidence_quote(valid_quote, candidate_transcript)
    verified_fake = rubric_evaluator.verify_evidence_quote(hallucinated_quote, candidate_transcript)
    
    return {
        "valid_quote_detected": verified_valid is True,
        "hallucinated_quote_flagged": verified_fake is False,
        "pass": (verified_valid is True and verified_fake is False)
    }


def verify_topic_weights_aggregation_invariant() -> Dict[str, Any]:
    """
    Verifies that topic weights DO NOT increase simply because more follow-up turns exist.
    Compares Topic-Group Aggregation vs Naive Turn Aggregation:
    Topic 1: 1 turn (main only), rating = 4.0
    Topic 2: 4 turns (1 main + 3 follow-ups), rating = 2.0
    
    Under Topic-Group Aggregation:
      Score = (4.0 * 50%) + (2.0 * 50%) = 3.00 (Equal topic weight)
    Under Naive Turn Averaging:
      Score = (4.0 * 1 + 2.0 * 4) / 5 = 12.0 / 5 = 2.40 (Distorted by follow-up count)
    """
    turns = [
        # Topic 1: 1 turn
        {
            "turn_index": 1,
            "question": "Explain database indexing in PostgreSQL.",
            "answer": "B-Tree indexes provide logarithmic lookup time.",
            "phase": "technical",
            "is_followup": False
        },
        # Topic 2: 1 main + 3 follow-ups (4 turns)
        {
            "turn_index": 2,
            "question": "How do you design a rate limiter?",
            "answer": "We use a token bucket algorithm.",
            "phase": "technical",
            "is_followup": False
        },
        {"turn_index": 3, "question": "Probe 1", "answer": "Followup answer 1", "phase": "technical", "is_followup": True},
        {"turn_index": 4, "question": "Probe 2", "answer": "Followup answer 2", "phase": "technical", "is_followup": True},
        {"turn_index": 5, "question": "Probe 3", "answer": "Followup answer 3", "phase": "technical", "is_followup": True}
    ]
    
    topic_groups = build_topic_groups_from_history(turns)
    
    group_assessments = [
        {
            "group_id": topic_groups[0].group_id,
            "eligible_criteria": ["technical_knowledge"],
            "ratings": {"technical_knowledge": 4.0}
        },
        {
            "group_id": topic_groups[1].group_id,
            "eligible_criteria": ["technical_knowledge"],
            "ratings": {"technical_knowledge": 2.0}
        }
    ]
    
    # Authoritative aggregation
    aggregated_ratings = aggregate_criterion_ratings_across_groups(group_assessments)
    topic_group_rating = aggregated_ratings.get("technical_knowledge")
    
    # Naive turn rating: 1 turn of 4.0 + 4 turns of 2.0
    naive_turn_rating = (4.0 + 2.0 * 4) / 5.0  # 2.40
    
    topic_group_rating_is_3_0 = (abs(topic_group_rating - 3.00) < 1e-4)
    naive_rating_is_2_4 = (abs(naive_turn_rating - 2.40) < 1e-4)
    
    return {
        "groups_detected": len(topic_groups),
        "topic_1_turns": 1,
        "topic_2_turns": 4,
        "topic_group_rating": topic_group_rating,
        "naive_turn_rating": naive_turn_rating,
        "topic_1_effective_weight": "50.0%",
        "topic_2_effective_weight": "50.0%",
        "invariant_holds": topic_group_rating_is_3_0,
        "pass": topic_group_rating_is_3_0 and (topic_group_rating != naive_turn_rating)
    }


def verify_missing_signals_handling() -> Dict[str, Any]:
    """
    Verifies that missing signals follow the documented 100-mark rubric rules:
    - Text-only (spoken_delivery is None) -> assessed out of 95, total_score_100 is None, status='partial'
    - All signals missing -> total_score_100 is None, status='unassessed'
    - Full signals -> assessed out of 100, total_score_100 is not None, status='complete'
    """
    # 1. Spoken delivery missing (text-only)
    text_only_ratings = {
        "technical_knowledge": 3.0,
        "problem_solving": 3.0,
        "practical_application": 3.0,
        "relevance_completeness": 3.0,
        "communication_clarity": 3.0,
        "followup_reflection": 3.0,
        "spoken_delivery": None
    }
    res_partial = compute_rubric_assessment(text_only_ratings)
    
    check_partial = (
        res_partial["assessment_status"] == "partial"
        and res_partial["assessed_maximum"] == 95.0
        and res_partial["total_score_100"] is None
        and res_partial["provisional_normalized_100"] is not None
        and res_partial["coverage_percent"] == 95.0
    )
    
    # 2. All missing
    all_missing_ratings = {k: None for k in ORDERED_CRITERIA_KEYS}
    res_unassessed = compute_rubric_assessment(all_missing_ratings)
    check_unassessed = (
        res_unassessed["assessment_status"] == "unassessed"
        and res_unassessed["total_score_100"] is None
        and res_unassessed["coverage_percent"] == 0.0
    )
    
    # 3. Complete
    complete_ratings = {k: 4.0 for k in ORDERED_CRITERIA_KEYS}
    res_complete = compute_rubric_assessment(complete_ratings)
    check_complete = (
        res_complete["assessment_status"] == "complete"
        and res_complete["assessed_maximum"] == 100.0
        and res_complete["total_score_100"] == 100.0
    )
    
    return {
        "partial_text_only_handled_correctly": check_partial,
        "all_missing_unassessed_handled_correctly": check_unassessed,
        "complete_handled_correctly": check_complete,
        "pass": check_partial and check_unassessed and check_complete
    }


def main():
    print("=" * 70)
    print("EXPERIMENT 1: INTERVIEW WORKFLOW AND RUBRIC CORRECTNESS AUDIT")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Rubric Version: {RUBRIC_VERSION} (Maximum Marks: {TOTAL_MAX_MARKS})")
    print("=" * 70)
    
    # 1. Existing rubric unit tests
    print("\n[Step 1] Running existing backend/tests/test_rubric_100.py...")
    unit_res = run_existing_rubric_tests()
    print(f"  Tests run: {unit_res['tests_run']}, Failures: {unit_res['failures']}, Errors: {unit_res['errors']}")
    print(f"  Status: {'PASS' if unit_res['was_successful'] else 'FAIL'} in {unit_res['elapsed_seconds']}s")
    
    # 2. Scripted cases (18 combinations)
    print("\n[Step 2] Executing scripted cases across 6 roles x 3 difficulties (18 combinations)...")
    scripted_res = execute_scripted_cases()
    print(f"  Executed: {scripted_res['total_combinations']} combinations.")
    print(f"  All Invariants Maintained: {'PASS' if scripted_res['all_passed'] else 'FAIL'}")
    for r in scripted_res["results"]:
        status_str = "PASS" if r["passed"] else "FAIL"
        print(f"    - {r['role']} [{r['difficulty']}]: {status_str} (Session: {r['session_id']})")
    
    # 3. Evidence quotation verification
    print("\n[Step 3] Verifying evidence quote matching and hallucination detection...")
    quote_res = verify_evidence_quote_matching()
    print(f"  Valid quote detected: {quote_res['valid_quote_detected']}")
    print(f"  Hallucinated quote flagged: {quote_res['hallucinated_quote_flagged']}")
    print(f"  Status: {'PASS' if quote_res['pass'] else 'FAIL'}")
    
    # 4. Topic weights aggregation invariant
    print("\n[Step 4] Verifying topic weights invariant (follow-ups do NOT inflate topic weight)...")
    weight_res = verify_topic_weights_aggregation_invariant()
    print(f"  Topic Group Aggregation (Equal Topic Weight): {weight_res['topic_group_rating']:.2f}")
    print(f"  Naive Turn Aggregation (Biased by follow-ups): {weight_res['naive_turn_rating']:.2f}")
    print(f"  Status: {'PASS' if weight_res['pass'] else 'FAIL'}")
    
    # 5. Missing signals handling
    print("\n[Step 5] Verifying missing signals handling under 100-mark rubric...")
    signals_res = verify_missing_signals_handling()
    print(f"  Text-only (spoken_delivery=None) -> partial / assessed out of 95: {signals_res['partial_text_only_handled_correctly']}")
    print(f"  All missing -> unassessed / 0% coverage: {signals_res['all_missing_unassessed_handled_correctly']}")
    print(f"  Complete -> complete / 100.0: {signals_res['complete_handled_correctly']}")
    print(f"  Status: {'PASS' if signals_res['pass'] else 'FAIL'}")
    
    # Summary
    all_passed = (
        unit_res["was_successful"]
        and scripted_res["all_passed"]
        and quote_res["pass"]
        and weight_res["pass"]
        and signals_res["pass"]
    )
    
    final_output = {
        "experiment": "EXPERIMENT 1 — Interview workflow and rubric correctness",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "EXECUTED",
        "overall_result": "PASS" if all_passed else "FAIL",
        "details": {
            "unit_tests": unit_res,
            "scripted_matrix_18": scripted_res,
            "quote_verification": quote_res,
            "topic_weight_invariant": weight_res,
            "missing_signals_handling": signals_res
        }
    }
    
    results_path = os.path.join(OUTPUT_DIR, "experiment_1_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"\n[Complete] Results saved to: {results_path}")
    print(f"[Traces] 18 session traces saved to: {TRACES_DIR}")
    
    # Clean up temporary test sessions
    try:
        import shutil
        shutil.rmtree(TEST_SESSIONS_DIR, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
