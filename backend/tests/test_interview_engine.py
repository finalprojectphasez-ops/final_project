"""
Test suite for PreMock AI Interview Engine:
1. Role, difficulty and duration selections reach backend correctly.
2. Resume information personalizes questions without overriding selected role.
3. Missing resume information produces a valid role-only interview.
4. Unsupported resume claims are not added.
5. Follow-ups respond to different answers to the same question.
6. Clarification, skip, topic change and ending work correctly.
7. Follow-up limits (max 2) and deadlines are enforced.
8. Duplicate submissions do not advance twice.
9. Invalid JSON and duplicate questions are handled.
10. Candidate responses never contain expected_points.
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.local_interview_model import (
    local_interview_model,
    normalize_role,
    normalize_difficulty
)
from app.services.session_manager import session_manager
from app.models.schemas import ProfessionalProfile, InterviewQuestionInternal

client = TestClient(app)


def test_1_setup_selections_reach_backend():
    """Verify all 6 roles, 3 difficulties, and 3 durations map correctly."""
    role_tests = [
        ("Full Stack Engineer", "full_stack_engineer"),
        ("Frontend Developer", "frontend_developer"),
        ("Backend Engineer", "backend_engineer"),
        ("DevOps / SRE", "devops_sre"),
        ("ML Engineer", "ml_engineer"),
        ("Data Analyst", "data_analyst"),
    ]
    diff_tests = [("Easy", "beginner"), ("Medium", "intermediate"), ("Hard", "advanced")]
    dur_tests = [(15, 4), (30, 6), (45, 8)]

    for role_label, expected_key in role_tests:
        for diff_label, expected_diff in diff_tests:
            for dur_min, expected_targets in dur_tests:
                res = client.post("/api/interview/session/create", json={
                    "role": role_label,
                    "difficulty": diff_label,
                    "duration_minutes": dur_min
                })
                assert res.status_code == 200, f"Failed for {role_label}, {diff_label}, {dur_min}"
                data = res.json()
                assert data["difficulty"] == expected_diff
                assert data["duration_minutes"] == dur_min
                assert data["target_questions"] == expected_targets
                assert len(data["planned_topics"]) == expected_targets
                assert "session_id" in data
                assert data["question"]["kind"] == "main"
                assert "expected_points" not in data["question"]


def test_2_resume_personalization_preserves_authoritative_role():
    """Verify resume technical skills personalize context, but selected role remains strictly authoritative."""
    # A candidate whose resume mentions frontend React, but applies for Backend Engineer at Hard level
    resume_text = """
    Jane Smith
    Experience with React, Next.js, and TypeScript.
    Built UI dashboards and frontend web components.
    """
    profile = local_interview_model.extract_resume_profile(resume_text)
    assert profile is not None
    assert "React" in profile.core_skills

    # User explicitly selects Backend Engineer at Hard difficulty
    res = client.post("/api/interview/session/create", json={
        "role": "Backend Engineer",
        "difficulty": "Hard",
        "duration_minutes": 30,
        "resume_profile": profile.model_dump(),
        "resume_text": resume_text
    })
    assert res.status_code == 200
    data = res.json()

    # The selected role and difficulty MUST remain strictly authoritative
    assert data["role"] == "Backend Engineer"
    assert data["difficulty"] == "advanced"
    # Planned topics must reflect Backend Engineer technical domain (not overridden by React frontend)
    assert any(any(term in t.lower() for term in ["api", "database", "protocol", "backend", "concurrency"]) for t in data["planned_topics"])


def test_3_missing_resume_produces_valid_role_only_interview():
    """Verify role-only interview works cleanly without inventing any candidate profile."""
    res = client.post("/api/interview/session/create", json={
        "role": "DevOps / SRE",
        "difficulty": "Medium",
        "duration_minutes": 15
    })
    assert res.status_code == 200
    data = res.json()
    session_id = data["session_id"]

    # Verify session on disk
    backend_session = session_manager.get_session(session_id)
    assert backend_session is not None
    assert backend_session["resume_profile"] is None
    assert backend_session["resume_text"] is None

    # First question is a valid role-only hypothetical question
    assert len(data["question"]["question"]) > 20
    assert data["question"]["kind"] == "main"


def test_4_unsupported_resume_claims_not_added():
    """Verify resume extraction only extracts supported information and does not invent unmentioned skills."""
    minimal_resume = "Alex Brown\nSoftware Developer\nAustin, TX\nWorked with Python and Git."
    profile = local_interview_model.extract_resume_profile(minimal_resume)
    assert profile is not None
    assert "Python" in profile.core_skills
    assert "Git" in profile.tools
    # Does not invent unmentioned technologies or titles
    assert "Kubernetes" not in profile.core_skills
    assert "TensorFlow" not in profile.core_skills
    assert profile.seniority != "principal"


def test_5_followup_answers_dynamic_response():
    """Verify follow-up generator responds dynamically to different answers to the same question."""
    res = client.post("/api/interview/session/create", json={
        "role": "Full Stack Engineer",
        "difficulty": "Medium",
        "duration_minutes": 30
    })
    session_id = res.json()["session_id"]
    current_q_data = res.json()["question"]
    q_internal = InterviewQuestionInternal(
        question=current_q_data["question"],
        topic=current_q_data["topic"],
        kind=current_q_data["kind"],
        difficulty=current_q_data["difficulty"],
        expected_points=["HTTP methods and status codes", "Payload validation", "Error contracts"]
    )

    # 1. Partial answer -> should probe missing reasoning
    act_partial, next_q_partial, _ = local_interview_model.generate_followup_turn(
        role="Full Stack Engineer",
        difficulty="intermediate",
        current_question=q_internal,
        latest_answer="We use JSON payloads over HTTP for sending data back and forth.",
        conversation_history=[],
        remaining_topics=[{"topic": "Database transactions"}],
        followups_used=0
    )
    assert act_partial == "follow_up"
    assert next_q_partial is not None
    assert next_q_partial.kind == "follow_up"

    # 2. Vague answer -> should ask to clarify
    act_vague, next_q_vague, _ = local_interview_model.generate_followup_turn(
        role="Full Stack Engineer",
        difficulty="intermediate",
        current_question=q_internal,
        latest_answer="It works fine.",
        conversation_history=[],
        remaining_topics=[{"topic": "Database transactions"}],
        followups_used=0
    )
    assert act_vague == "clarify"
    assert next_q_vague.kind == "clarify"

    # 3. Strong comprehensive answer -> extension or next topic
    act_strong, next_q_strong, _ = local_interview_model.generate_followup_turn(
        role="Full Stack Engineer",
        difficulty="intermediate",
        current_question=q_internal,
        latest_answer="We define strict OpenAPI specs with JSON Schema validation on payloads, use proper HTTP status codes like 400 for client errors and 500 for server errors, and standardize error contracts using RFC 7807 problem details.",
        conversation_history=[],
        remaining_topics=[{"topic": "Database transactions"}],
        followups_used=0
    )
    assert act_strong in ("follow_up", "next_topic")


def test_6_clarification_skip_topic_change_and_end():
    """Verify 'I don't know' clarification, explicit skip, topic advancement and graceful end."""
    res = client.post("/api/interview/session/create", json={
        "role": "Data Analyst",
        "difficulty": "Easy",
        "duration_minutes": 15
    })
    session_id = res.json()["session_id"]

    # 1. 'I don't know' -> Action: clarify
    turn1_res = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "I don't know much about this specific concept."
    })
    assert turn1_res.status_code == 200
    t1 = turn1_res.json()
    assert t1["action"] == "clarify"
    assert t1["next_question"]["kind"] == "clarify"
    assert t1["followups_used"] == 1

    # 2. Explicit skip -> Action: next_topic
    turn2_res = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "Please skip this, let's move on to the next topic."
    })
    assert turn2_res.status_code == 200
    t2 = turn2_res.json()
    assert t2["action"] == "next_topic"
    assert t2["next_question"]["kind"] == "main"
    # Invariant: Follow-up counter MUST reset to 0 upon entering a new main topic!
    assert t2["followups_used"] == 0
    assert t2["current_topic_index"] == 1


def test_7_followup_limits_and_deadlines():
    """Verify maximum of 2 follow-ups per topic, counter reset invariant, and deadline enforcement."""
    res = client.post("/api/interview/session/create", json={
        "role": "Backend Engineer",
        "difficulty": "Medium",
        "duration_minutes": 15
    })
    session_id = res.json()["session_id"]

    # Turn 1 answer: substantive self-introduction -> triggers follow-up 1
    t1 = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "I am a backend engineer with six years of experience building distributed systems, REST APIs, and database pipelines."
    }).json()
    assert t1["action"] == "follow_up"
    assert t1["followups_used"] == 1

    # Turn 2 answer: follow-up 2
    t2 = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "For idempotency and mutation safety, we attach a unique idempotency key header to every mutation endpoint and verify locks."
    }).json()
    assert t2["action"] in ("follow_up", "next_topic")
    
    # If action was follow_up (followups_used == 2), the NEXT turn MUST advance to next_topic
    if t2["action"] == "follow_up":
        assert t2["followups_used"] == 2
        t3 = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
            "answer": "We check the Redis cache and verify distributed consistency before executing the underlying database write operation."
        }).json()
        assert t3["action"] in ("next_topic", "end")
        assert t3["followups_used"] == 0  # Reset upon topic transition!

    # Test Deadline Enforcement
    backend_session = session_manager.get_session(session_id)
    # Manually expire deadline
    backend_session["deadline_timestamp"] = time.time() - 10
    session_manager.save_session(backend_session)

    expired_turn = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "Another answer after time is up."
    }).json()
    assert expired_turn["action"] == "end"
    assert expired_turn["is_complete"] is True
    assert expired_turn["next_question"] is None


def test_8_duplicate_submissions_do_not_advance_twice():
    """Verify duplicate answer submissions are blocked with HTTP 409 and do not advance the session twice."""
    res = client.post("/api/interview/session/create", json={
        "role": "Frontend Developer",
        "difficulty": "Easy",
        "duration_minutes": 30
    })
    session_id = res.json()["session_id"]

    payload = {"answer": "The DOM represents the page hierarchy in browser memory."}

    # First submission -> success
    sub1 = client.post(f"/api/interview/session/{session_id}/submit-turn", json=payload)
    assert sub1.status_code == 200
    turn_index_1 = sub1.json()["turn_index"]

    # Duplicate submission immediately after -> 409 Conflict
    sub2 = client.post(f"/api/interview/session/{session_id}/submit-turn", json=payload)
    assert sub2.status_code == 409
    assert "Duplicate submission" in sub2.json()["detail"]

    # Verify session in backend still has turn_index 2, not 3
    sess_view = client.get(f"/api/interview/session/{session_id}").json()
    assert sess_view["current_turn"] == turn_index_1


def test_9_invalid_json_and_duplicate_questions():
    """Verify invalid payloads and near-duplicate questions are rejected safely."""
    # Empty answer
    res_empty = client.post("/api/interview/session/some-id/submit-turn", json={"answer": "   "})
    assert res_empty.status_code in (400, 404, 422)

    # Near-duplicate question check
    q1 = "Explain how you handle database migrations with zero downtime while serving active client traffic."
    is_dup = local_interview_model._is_near_duplicate(
        candidate_q="Explain how you handle database migrations with zero downtime while serving active user traffic.",
        history=[q1]
    )
    assert is_dup is True

    # Completely different question is NOT duplicate
    q_diff = "What is the difference between CSS Flexbox and CSS Grid in responsive design?"
    assert local_interview_model._is_near_duplicate(q_diff, history=[q1]) is False


def test_10_candidate_responses_never_contain_expected_points():
    """Verify candidate-facing endpoints NEVER expose expected_points or rubrics."""
    # 1. Create session
    create_res = client.post("/api/interview/session/create", json={
        "role": "ML Engineer",
        "difficulty": "Hard",
        "duration_minutes": 30
    })
    assert create_res.status_code == 200
    data = create_res.json()
    session_id = data["session_id"]

    assert "expected_points" not in data["question"]

    # 2. Submit turn
    turn_res = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
        "answer": "We evaluate data drift using Population Stability Index on streaming features."
    })
    assert turn_res.status_code == 200
    turn_data = turn_res.json()
    if turn_data["next_question"]:
        assert "expected_points" not in turn_data["next_question"]

    # 3. Retrieve session view
    get_res = client.get(f"/api/interview/session/{session_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    if get_data["current_question"]:
        assert "expected_points" not in get_data["current_question"]
    for h in get_data.get("history", []):
        assert "expected_points" not in h


def test_11_zero_duplicate_questions_in_multi_turn_session():
    """
    Verify across multiple roles and difficulties that multi-turn sessions
    produce ZERO duplicate or near-duplicate questions across all turns,
    even under candidate evasion ('I don't know', brief answers, skips).
    """
    test_scenarios = [
        ("Data Analyst", "Easy", [
            "Hello, my name is Mugilan. I am a data analytics enthusiast with practical experience in Python and SQL.",
            "I don't know.",
            "database and structured query language",
            "sorry I don't know",
            "We use GROUP BY with aggregate functions to summarize rows.",
            "I don't know."
        ]),
        ("Backend Engineer", "Medium", [
            "I am a backend developer experienced with FastAPI, PostgreSQL, and Redis caching systems.",
            "We use gRPC with Protobuf for low-latency internal microservice communication.",
            "I'm not sure about distributed consensus algorithms.",
            "skip",
            "We run EXPLAIN ANALYZE to identify sequential table scans and create composite B-tree indexes.",
            "We use connection pooling with pgbouncer."
        ]),
        ("Full Stack Engineer", "Hard", [
            "I am a full stack engineer working with React on the frontend and Node.js on the backend.",
            "I don't know.",
            "We use optimistic UI updates and React Query caching.",
            "Next topic please.",
            "We enforce database transaction isolation levels using PostgreSQL serializable transactions.",
            "I haven't used that particular framework."
        ])
    ]

    for role, difficulty, candidate_answers in test_scenarios:
        create_res = client.post("/api/interview/session/create", json={
            "role": role,
            "difficulty": difficulty,
            "duration_minutes": 30
        })
        assert create_res.status_code == 200, f"Failed to create session for {role}"
        session_data = create_res.json()
        session_id = session_data["session_id"]

        asked_questions = [session_data["question"]["question"]]

        for turn_idx, ans in enumerate(candidate_answers, start=1):
            turn_res = client.post(f"/api/interview/session/{session_id}/submit-turn", json={
                "answer": ans,
                "turn_id": f"turn_test_{turn_idx}_{int(time.time()*1000)}"
            })
            assert turn_res.status_code == 200, f"Turn {turn_idx} failed for {role}: {turn_res.text}"
            turn_data = turn_res.json()

            if turn_data.get("next_question"):
                next_q = turn_data["next_question"]["question"]
                asked_questions.append(next_q)

            if turn_data.get("is_complete"):
                break

        # Check all questions asked in this session for ANY exact or near duplicates
        for i in range(len(asked_questions)):
            for j in range(i + 1, len(asked_questions)):
                q1 = asked_questions[i]
                q2 = asked_questions[j]
                # 1. Exact string duplicate assertion
                assert q1.strip().lower() != q2.strip().lower(), (
                    f"Duplicate question detected in {role} session!\n"
                    f"Turn {i+1}: {q1}\n"
                    f"Turn {j+1}: {q2}"
                )
                # 2. Near duplicate assertion using local Jaccard similarity
                is_near = local_interview_model._is_near_duplicate(q1, [q2], threshold=0.55)
                assert not is_near, (
                    f"Near-duplicate question detected in {role} session!\n"
                    f"Turn {i+1}: {q1}\n"
                    f"Turn {j+1}: {q2}"
                )


if __name__ == "__main__":
    tests = [
        test_1_setup_selections_reach_backend,
        test_2_resume_personalization_preserves_authoritative_role,
        test_3_missing_resume_produces_valid_role_only_interview,
        test_4_unsupported_resume_claims_not_added,
        test_5_followup_answers_dynamic_response,
        test_6_clarification_skip_topic_change_and_end,
        test_7_followup_limits_and_deadlines,
        test_8_duplicate_submissions_do_not_advance_twice,
        test_9_invalid_json_and_duplicate_questions,
        test_10_candidate_responses_never_contain_expected_points,
        test_11_zero_duplicate_questions_in_multi_turn_session
    ]
    passed = 0
    failed = 0
    print("=" * 60)
    print("RUNNING INTERVIEW ENGINE VERIFICATION TESTS")
    print("=" * 60)
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests.")
    print("=" * 60)
    if failed > 0:
        exit(1)
