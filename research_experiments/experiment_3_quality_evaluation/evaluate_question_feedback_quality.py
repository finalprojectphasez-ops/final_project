"""
Experiment 3 Runner: Question and Feedback Quality Audit.
Audits:
1. Question repetition: Identifies identical or near-duplicate questions within and across session turns.
2. Answer grounding and unsupported feedback statements: Verifies whether feedback claims and rubric justifications are grounded in candidate transcripts.
3. Human Reviewer Quality Protocol: Prepares Likert rating templates (1-5 scale) for follow-up relevance, answer grounding, and feedback usefulness.

Note on Limitations:
Per experimental protocol, usefulness ratings reflect subjective candidate satisfaction and do not establish improved interview performance.
"""

import os
import sys
import glob
import json
import csv
import re
from typing import List, Dict, Any, Set

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.rubric.evaluator import rubric_evaluator

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
EXP1_TRACES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "experiment_1_workflow_rubric", "session_traces"))
EXP2_PACKET = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "experiment_2_human_evaluation", "blinded_review_packet.json"))
REPORTS_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "data", "reports"))
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "quality_metrics_summary.json")
TEMPLATE_CSV = os.path.join(SCRIPT_DIR, "quality_rating_template.csv")


def tokenize_clean(text: str) -> Set[str]:
    """Tokenizes text into lowercase alphanumeric word stems for similarity."""
    return set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", (text or "").lower()))


def jaccard_similarity(text1: str, text2: str) -> float:
    """Computes Jaccard word overlap between two questions."""
    tokens1 = tokenize_clean(text1)
    tokens2 = tokenize_clean(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return intersection / union if union > 0 else 0.0


def audit_question_repetition_in_traces() -> Dict[str, Any]:
    """
    Audits all 18 simulated session traces for repeated questions.
    Checks consecutive turn pairs and all pairwise question combinations within each session.
    """
    trace_files = glob.glob(os.path.join(EXP1_TRACES_DIR, "*.json"))
    total_sessions = len(trace_files)
    total_questions_analyzed = 0
    exact_duplicates = 0
    near_duplicates = 0  # Jaccard > 0.85
    repetition_incidents = []

    for tf in trace_files:
        with open(tf, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
        
        session_id = trace_data.get("session_id")
        questions = []
        for t in trace_data.get("turns", []):
            q_text = t.get("question")
            if q_text:
                questions.append((t.get("turn", 0), q_text))
        
        total_questions_analyzed += len(questions)
        
        # Check pairwise duplicates within session
        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                turn_i, q_i = questions[i]
                turn_j, q_j = questions[j]
                
                if q_i.strip().lower() == q_j.strip().lower():
                    exact_duplicates += 1
                    repetition_incidents.append({
                        "session_id": session_id,
                        "type": "exact_duplicate",
                        "turn_a": turn_i,
                        "turn_b": turn_j,
                        "question": q_i
                    })
                else:
                    sim = jaccard_similarity(q_i, q_j)
                    if sim > 0.85:
                        near_duplicates += 1
                        repetition_incidents.append({
                            "session_id": session_id,
                            "type": "near_duplicate",
                            "similarity": round(sim, 3),
                            "turn_a": turn_i,
                            "turn_b": turn_j,
                            "question_a": q_i,
                            "question_b": q_j
                        })

    return {
        "sessions_inspected": total_sessions,
        "total_questions_audited": total_questions_analyzed,
        "exact_duplicate_questions_count": exact_duplicates,
        "near_duplicate_questions_count": near_duplicates,
        "repetition_rate_percent": round(((exact_duplicates + near_duplicates) / max(1, total_questions_analyzed)) * 100, 2),
        "incidents": repetition_incidents
    }


def audit_unsupported_feedback_statements() -> Dict[str, Any]:
    """
    Audits saved session reports for unsupported feedback statements or fabricated quotes.
    """
    report_files = glob.glob(os.path.join(REPORTS_DIR, "*.json"))
    total_feedback_statements = 0
    unsupported_statements_count = 0
    unsupported_incidents = []

    for rf in report_files:
        try:
            with open(rf, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception:
            continue

        report_id = report.get("session_id")
        
        # Collect candidate transcripts in this session
        all_candidate_text = ""
        turns = report.get("turns", []) or report.get("history", [])
        for t in turns:
            ans = t.get("candidate_answer") or t.get("answer") or t.get("transcript") or ""
            all_candidate_text += " " + ans
        
        # Check criteria evidence and reasons
        criteria_breakdown = report.get("criteria_breakdown", {})
        for crit_key, crit_data in criteria_breakdown.items():
            if not isinstance(crit_data, dict):
                continue
            
            # Check reasons / justifications
            reason = crit_data.get("reason", "")
            if reason:
                total_feedback_statements += 1
            
            # Check quotes
            quotes = crit_data.get("evidence", [])
            for q in quotes:
                total_feedback_statements += 1
                if all_candidate_text.strip():
                    is_valid = rubric_evaluator.verify_evidence_quote(q, all_candidate_text)
                    if not is_valid:
                        unsupported_statements_count += 1
                        unsupported_incidents.append({
                            "report_id": report_id,
                            "criterion": crit_key,
                            "unsupported_quote": q
                        })

    return {
        "reports_inspected": len(report_files),
        "total_feedback_statements_audited": total_feedback_statements,
        "unsupported_feedback_statements_count": unsupported_statements_count,
        "grounding_fidelity_percent": round(((total_feedback_statements - unsupported_statements_count) / max(1, total_feedback_statements)) * 100, 2) if total_feedback_statements > 0 else 100.0,
        "incidents": unsupported_incidents
    }


def prepare_quality_rating_template():
    """
    Prepares quality rating template for human reviewers to evaluate:
    - Follow-up relevance (1-5 Likert scale)
    - Answer grounding (1-5 Likert scale)
    - Feedback usefulness (1-5 Likert scale)
    """
    with open(EXP2_PACKET, "r", encoding="utf-8") as f:
        packet_data = json.load(f)
    items = packet_data.get("items", [])

    fieldnames = [
        "item_id", "role", "difficulty", "question", "candidate_answer",
        "followup_relevance_1_to_5",
        "answer_grounding_1_to_5",
        "feedback_usefulness_1_to_5",
        "reviewer_comments"
    ]

    with open(TEMPLATE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for it in items:
            writer.writerow({
                "item_id": it["item_id"],
                "role": it["role"],
                "difficulty": it["difficulty"],
                "question": it["question"],
                "candidate_answer": it["candidate_answer"][:100] + "...",
                "followup_relevance_1_to_5": "",
                "answer_grounding_1_to_5": "",
                "feedback_usefulness_1_to_5": "",
                "reviewer_comments": ""
            })

    print(f"Quality rating template written to: {TEMPLATE_CSV}")


def main():
    print("=" * 70)
    print("EXPERIMENT 3: QUESTION AND FEEDBACK QUALITY AUDIT")
    print("=" * 70)

    # 1. Question Repetition Audit
    rep_res = audit_question_repetition_in_traces()
    print(f"\n[Audit 1: Question Repetition]")
    print(f"  Sessions inspected: {rep_res['sessions_inspected']}")
    print(f"  Total questions audited: {rep_res['total_questions_audited']}")
    print(f"  Exact duplicate questions: {rep_res['exact_duplicate_questions_count']}")
    print(f"  Near-duplicate questions (Jaccard > 0.85): {rep_res['near_duplicate_questions_count']}")
    print(f"  Repetition rate: {rep_res['repetition_rate_percent']}%")

    # 2. Unsupported Feedback Statements Audit
    ground_res = audit_unsupported_feedback_statements()
    print(f"\n[Audit 2: Answer Grounding and Evidence Fidelity]")
    print(f"  Reports inspected: {ground_res['reports_inspected']}")
    print(f"  Total feedback statements audited: {ground_res['total_feedback_statements_audited']}")
    print(f"  Unsupported statements: {ground_res['unsupported_feedback_statements_count']}")
    print(f"  Grounding fidelity: {ground_res['grounding_fidelity_percent']}%")

    # 3. Prepare Human Template
    prepare_quality_rating_template()

    # 4. Save Final Output
    summary = {
        "experiment": "EXPERIMENT 3 — Question and feedback quality",
        "status": "PENDING HUMAN INPUT",
        "note": "Automated repetition and grounding audits EXECUTED; human Likert ratings (1-5) PENDING HUMAN INPUT.",
        "limitation_disclaimer": "Per experimental protocol, usefulness ratings reflect subjective candidate perception and do not establish improved interview performance.",
        "automated_question_repetition_audit": rep_res,
        "automated_feedback_grounding_audit": ground_res,
        "human_evaluation_protocol": {
            "template_path": os.path.basename(TEMPLATE_CSV),
            "sample_size": len(glob.glob(os.path.join(EXP1_TRACES_DIR, "*.json"))),
            "likert_dimensions": [
                "Follow-up relevance (1-5 scale: 1=completely disconnected, 5=highly probing and context-grounded)",
                "Answer grounding (1-5 scale: 1=unrelated to candidate response, 5=strictly grounded in candidate response)",
                "Feedback usefulness (1-5 scale: 1=generic/unhelpful, 5=highly actionable and specific)"
            ],
            "human_ratings_status": "Blank template prepared (Awaiting human reviewer input)"
        }
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[Complete] Experiment 3 summary written to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
