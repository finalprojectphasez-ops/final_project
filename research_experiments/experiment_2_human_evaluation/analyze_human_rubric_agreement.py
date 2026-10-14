"""
Statistical Analysis of Human vs Automated Rubric Scoring Agreement.
Rubric: interview_practice_100_v1 (100.0 Marks)

Calculates:
1. Human vs Human agreement using Weighted Cohen's Kappa per criterion (Linear & Quadratic).
2. Automated vs Human Reviewer 1 agreement using Weighted Cohen's Kappa per criterion.
3. Automated vs Human Reviewer 2 agreement using Weighted Cohen's Kappa per criterion.
4. Total-score Mean Absolute Error (MAE) against the Human Mean Score.

Preserves original data. If human review templates are uncompleted, marks status PENDING HUMAN INPUT.
Includes a mathematical self-test fixture to verify statistical formulas independently.
"""

import os
import sys
import csv
import json
import math
from typing import List, Dict, Any, Tuple, Optional

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.rubric.config import ORDERED_CRITERIA_KEYS, RUBRIC_CRITERIA

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
REV1_CSV = os.path.join(SCRIPT_DIR, "review_scoring_template_reviewer1.csv")
REV2_CSV = os.path.join(SCRIPT_DIR, "review_scoring_template_reviewer2.csv")
AUTO_JSON = os.path.join(SCRIPT_DIR, "automated_scores_blinded_reference.json")
STATUS_JSON = os.path.join(SCRIPT_DIR, "experiment_2_pilot_status.json")


def compute_weighted_cohen_kappa(
    rater1: List[int],
    rater2: List[int],
    weight_type: str = "quadratic",
    categories: List[int] = [0, 1, 2, 3, 4]
) -> float:
    """
    Computes Cohen's Kappa with linear or quadratic weighting across ordinal categories 0-4.
    Formula:
      kappa = 1 - (sum(w_ij * O_ij) / sum(w_ij * E_ij))
    """
    if len(rater1) != len(rater2) or len(rater1) == 0:
        return 0.0

    n = len(rater1)
    k = len(categories)
    cat_to_idx = {c: i for i, c in enumerate(categories)}

    # Build observed confusion matrix O
    O = [[0 for _ in range(k)] for _ in range(k)]
    for r1, r2 in zip(rater1, rater2):
        if r1 in cat_to_idx and r2 in cat_to_idx:
            O[cat_to_idx[r1]][cat_to_idx[r2]] += 1

    # Marginal totals
    row_sums = [sum(O[i][j] for j in range(k)) for i in range(k)]
    col_sums = [sum(O[i][j] for i in range(k)) for j in range(k)]

    # Expected confusion matrix E
    E = [[(row_sums[i] * col_sums[j]) / n for j in range(k)] for i in range(k)]

    # Weight matrix W
    W = [[0.0 for _ in range(k)] for _ in range(k)]
    for i in range(k):
        for j in range(k):
            diff = abs(i - j)
            if weight_type == "quadratic":
                W[i][j] = (diff ** 2) / ((k - 1) ** 2)
            else:  # linear
                W[i][j] = diff / (k - 1)

    # Weighted observed and expected disagreement
    obs_disagreement = sum(W[i][j] * O[i][j] for i in range(k) for j in range(k))
    exp_disagreement = sum(W[i][j] * E[i][j] for i in range(k) for j in range(k))

    if exp_disagreement == 0.0:
        return 1.0 if obs_disagreement == 0.0 else 0.0

    kappa = 1.0 - (obs_disagreement / exp_disagreement)
    return round(kappa, 4)


def load_reviewer_csv(csv_path: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Loads reviewer CSV and checks whether all numeric ratings are populated.
    Returns (records, is_complete).
    """
    if not os.path.exists(csv_path):
        return [], False

    records = []
    is_complete = True
    active_criteria = [
        "technical_knowledge", "problem_solving", "practical_application",
        "relevance_completeness", "communication_clarity", "followup_reflection"
    ]

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed_row = {"item_id": row.get("item_id"), "role": row.get("role"), "difficulty": row.get("difficulty")}
            for crit in active_criteria:
                val = row.get(crit, "").strip()
                if val == "" or val is None:
                    is_complete = False
                    parsed_row[crit] = None
                else:
                    try:
                        parsed_row[crit] = int(float(val))
                    except ValueError:
                        is_complete = False
                        parsed_row[crit] = None
            records.append(parsed_row)

    return records, (is_complete and len(records) > 0)


def calculate_item_total_marks(ratings: Dict[str, Optional[int]]) -> float:
    """Calculates total marks out of 95.0 (for text-only items) using rubric weights."""
    total = 0.0
    for crit, anchor in ratings.items():
        if anchor is not None and crit in RUBRIC_CRITERIA:
            max_m = RUBRIC_CRITERIA[crit]["max_marks"]
            total += (anchor / 4.0) * max_m
    return round(total, 2)


def test_statistical_calibration_fixtures() -> Dict[str, Any]:
    """
    Self-test calibration fixture to verify mathematical accuracy of Kappa and MAE functions.
    Uses known analytical inputs.
    """
    # 1. Perfect agreement
    r_a = [0, 1, 2, 3, 4, 3, 2, 1]
    r_b = [0, 1, 2, 3, 4, 3, 2, 1]
    kappa_perfect = compute_weighted_cohen_kappa(r_a, r_b, "quadratic")

    # 2. Slight adjacent disagreement
    r_c = [0, 1, 2, 3, 4]
    r_d = [0, 1, 2, 3, 3]  # One adjacent off-by-one
    kappa_high = compute_weighted_cohen_kappa(r_c, r_d, "quadratic")

    # 3. Complete inverse disagreement
    r_e = [0, 4, 0, 4]
    r_f = [4, 0, 4, 0]
    kappa_inverse = compute_weighted_cohen_kappa(r_e, r_f, "quadratic")

    # 4. MAE calculation test
    auto_scores = [75.0, 80.0, 60.0]
    h1_scores = [70.0, 80.0, 65.0]
    h2_scores = [72.0, 82.0, 63.0]
    human_means = [(h1 + h2) / 2.0 for h1, h2 in zip(h1_scores, h2_scores)]  # [71.0, 81.0, 64.0]
    # diffs: |75 - 71| = 4, |80 - 81| = 1, |60 - 64| = 4 -> mean = 9/3 = 3.0
    mae_test = sum(abs(a - hm) for a, hm in zip(auto_scores, human_means)) / len(auto_scores)

    calibration_passed = (
        kappa_perfect == 1.0
        and kappa_high > 0.80
        and kappa_inverse == -1.0
        and abs(mae_test - 3.0) < 1e-4
    )

    return {
        "kappa_perfect_agreement": kappa_perfect,
        "kappa_adjacent_agreement": kappa_high,
        "kappa_inverse_disagreement": kappa_inverse,
        "mae_calibration": round(mae_test, 4),
        "calibration_passed": calibration_passed
    }


def main():
    print("=" * 70)
    print("EXPERIMENT 2: AUTOMATED SCORING VS HUMAN REVIEWERS (PILOT STUDY)")
    print("=" * 70)

    # 1. Run statistical formula self-test
    calib = test_statistical_calibration_fixtures()
    print(f"[Self-Test] Statistical formula calibration: {'PASS' if calib['calibration_passed'] else 'FAIL'}")
    print(f"  - Perfect Kappa: {calib['kappa_perfect_agreement']}")
    print(f"  - Adjacent Kappa: {calib['kappa_adjacent_agreement']}")
    print(f"  - Analytical MAE: {calib['mae_calibration']}")

    # 2. Load automated reference scores
    with open(AUTO_JSON, "r", encoding="utf-8") as f:
        auto_records = json.load(f)
    print(f"\n[Dataset] Loaded {len(auto_records)} pilot items from automated reference.")

    # 3. Check human reviewer templates
    rev1_records, rev1_complete = load_reviewer_csv(REV1_CSV)
    rev2_records, rev2_complete = load_reviewer_csv(REV2_CSV)

    print(f"[Reviewer 1] Path: {REV1_CSV} | Complete: {rev1_complete} | Items: {len(rev1_records)}")
    print(f"[Reviewer 2] Path: {REV2_CSV} | Complete: {rev2_complete} | Items: {len(rev2_records)}")

    active_criteria = [
        "technical_knowledge", "problem_solving", "practical_application",
        "relevance_completeness", "communication_clarity", "followup_reflection"
    ]

    # If both human sets are completed, perform full evaluation
    if rev1_complete and rev2_complete:
        print("\n[Analysis] Both human reviewer datasets are complete. Running statistical comparisons...")
        
        comparison_results = {}
        h_h_kappas = {}
        auto_h1_kappas = {}
        auto_h2_kappas = {}

        for crit in active_criteria:
            r1_vals = [r[crit] for r in rev1_records]
            r2_vals = [r[crit] for r in rev2_records]
            auto_vals = [int(round(a["ratings"].get(crit, 0))) for a in auto_records]

            h_h_kappas[crit] = compute_weighted_cohen_kappa(r1_vals, r2_vals, "quadratic")
            auto_h1_kappas[crit] = compute_weighted_cohen_kappa(auto_vals, r1_vals, "quadratic")
            auto_h2_kappas[crit] = compute_weighted_cohen_kappa(auto_vals, r2_vals, "quadratic")

        # Total-score MAE
        item_maes = []
        for i in range(len(auto_records)):
            h1_score = calculate_item_total_marks({c: rev1_records[i][c] for c in active_criteria})
            h2_score = calculate_item_total_marks({c: rev2_records[i][c] for c in active_criteria})
            human_mean = (h1_score + h2_score) / 2.0
            auto_score = auto_records[i]["assessed_score"]
            item_maes.append(abs(auto_score - human_mean))

        overall_mae = round(sum(item_maes) / len(item_maes), 2)

        output_status = {
            "experiment": "EXPERIMENT 2 — Automated scoring versus human reviewers",
            "status": "EXECUTED",
            "sample_size": len(auto_records),
            "human_human_weighted_kappa": h_h_kappas,
            "auto_human1_weighted_kappa": auto_h1_kappas,
            "auto_human2_weighted_kappa": auto_h2_kappas,
            "total_score_mae_against_human_mean": overall_mae,
            "formula_calibration": calib
        }
    else:
        print("\n[Status] Human review templates contain unpopulated entries.")
        print("  Notice: AI is strictly prohibited from inventing synthetic human annotations.")
        print("  Templates are prepared and validated for independent double-blind human review.")
        print("  STATUS: PENDING HUMAN INPUT")

        output_status = {
            "experiment": "EXPERIMENT 2 — Automated scoring versus human reviewers",
            "status": "PENDING HUMAN INPUT",
            "sample_size": len(auto_records),
            "protocol": "Double-blind independent evaluation of 35 pilot responses using interview_practice_100_v1",
            "reviewer_1_template": os.path.basename(REV1_CSV),
            "reviewer_2_template": os.path.basename(REV2_CSV),
            "reviewer_1_status": "Blank template prepared (Awaiting human ratings)",
            "reviewer_2_status": "Blank template prepared (Awaiting human ratings)",
            "blinded_packet": os.path.basename(AUTO_JSON),
            "eligible_criteria_evaluated": active_criteria,
            "statistical_methods_prepared": [
                "Quadratic weighted Cohen's Kappa per criterion (Human 1 vs Human 2)",
                "Quadratic weighted Cohen's Kappa per criterion (Automated vs Human 1)",
                "Quadratic weighted Cohen's Kappa per criterion (Automated vs Human 2)",
                "Total-score Mean Absolute Error (MAE) against Human Mean Score"
            ],
            "formula_calibration_validation": calib
        }

    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(output_status, f, indent=2)

    print(f"\n[Saved] Experiment 2 status written to: {STATUS_JSON}")


if __name__ == "__main__":
    main()
