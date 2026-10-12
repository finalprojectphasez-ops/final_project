import urllib.request
import json

BASE = "http://localhost:8000"

def test_api():
    print("[1] Testing GET /api/rubric/config...")
    req = urllib.request.urlopen(f"{BASE}/api/rubric/config")
    cfg = json.loads(req.read().decode())
    assert cfg["rubric_version"] == "interview_practice_100_v1"
    assert cfg["total_max_marks"] == 100.0
    print("  [OK] Config OK:", cfg["rubric_version"], "total marks:", cfg["total_max_marks"])

    print("[2] Testing POST /api/rubric/assess (complete assessment)...")
    post_data = json.dumps({
        "job_role": "Software Engineer",
        "difficulty": "Medium",
        "turns": [
            {
                "question": "Tell me about yourself and your background.",
                "answer": "I have been building full stack web applications with React and Python for four years.",
                "phase": "intro"
            },
            {
                "question": "How do you handle database concurrency and race conditions?",
                "answer": "We use Redis distributed locks and PostgreSQL row-level locking with SELECT FOR UPDATE to prevent race conditions during checkout.",
                "phase": "technical"
            }
        ],
        "spoken_delivery_rating": 3.0,
        "coaching_observations": {
            "eye_contact_percent": 88.0,
            "face_present_percent": 95.0
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/rubric/assess",
        data=post_data,
        headers={"Content-Type": "application/json"}
    )
    res = urllib.request.urlopen(req)
    assessment = json.loads(res.read().decode())
    print("  [OK] Assessment Status:", assessment["assessment_status"])
    print("  [OK] Total Score 100:", assessment["total_score_100"])
    print("  [OK] Coverage %:", assessment["coverage_percent"])
    print("  [OK] Criteria Evaluated:", list(assessment["criteria"].keys()))

    print("[3] Testing POST /api/reports/save with rubric assessment...")
    session_id = "test-session-rubric-100"
    report_data = json.dumps({
        "id": session_id,
        "role": "Software Engineer",
        "difficulty": "Medium",
        "rubric_assessment": assessment,
        "overall_score": assessment["total_score_100"],
        "question_feedback": [
            {"question": "Q1", "answer": "Answer 1"}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/api/reports/save",
        data=report_data,
        headers={"Content-Type": "application/json"}
    )
    save_res = urllib.request.urlopen(req)
    assert save_res.status == 200
    print("  [OK] Report Saved persistently with ID:", session_id)

    print("[4] Testing GET /api/rubric/export/{id} (JSON format)...")
    req = urllib.request.urlopen(f"{BASE}/api/rubric/export/{session_id}?format=json")
    export_json = json.loads(req.read().decode())
    assert export_json["provenance"]["rubric_version"] == "interview_practice_100_v1"
    print("  [OK] JSON Provenance Export OK, Version:", export_json["provenance"]["rubric_version"])

    print("[5] Testing GET /api/rubric/export/{id} (CSV format)...")
    req = urllib.request.urlopen(f"{BASE}/api/rubric/export/{session_id}?format=csv")
    export_csv = json.loads(req.read().decode())
    assert export_csv["format"] == "csv"
    assert "technical_knowledge" in export_csv["csv_content"]
    print("  [OK] CSV Provenance Export OK:")
    print("    First line:", export_csv["csv_content"].splitlines()[0])

    print("[6] Testing POST /api/rubric/manual-review override...")
    review_post = json.dumps({
        "session_id": session_id,
        "criterion_id": "spoken_delivery",
        "rating": 4.0,
        "reason": "Expert review verified excellent clarity and cadence",
        "reviewer_notes": "Audio tested through Sennheiser monitoring"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/rubric/manual-review",
        data=review_post,
        headers={"Content-Type": "application/json"}
    )
    review_res = urllib.request.urlopen(req)
    review_data = json.loads(review_res.read().decode())
    assert review_data["status"] == "ok"
    updated_delivery = review_data["rubric_assessment"]["criteria"]["spoken_delivery"]
    assert updated_delivery["rating"] == 4.0
    assert updated_delivery["earned_marks"] == 5.0
    print("  [OK] Manual Override OK! Spoken delivery earned marks updated to:", updated_delivery["earned_marks"])

    print("\nALL API ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
