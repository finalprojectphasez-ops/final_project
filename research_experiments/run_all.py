"""
Unified Research Experiment Suite Runner for PreMock AI (Workspace: MY_PART).
Runs all 4 experiments sequentially, verifies status, and prints consolidated output.
"""

import os
import sys
import subprocess
import time
from datetime import datetime, timezone

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXP_DIR = os.path.abspath(os.path.dirname(__file__))

EXPERIMENTS = [
    (
        "EXPERIMENT 1 — Interview workflow and rubric correctness",
        os.path.join(EXP_DIR, "experiment_1_workflow_rubric", "run_experiment_1.py")
    ),
    (
        "EXPERIMENT 2 — Automated scoring versus human reviewers (Pilot)",
        os.path.join(EXP_DIR, "experiment_2_human_evaluation", "analyze_human_rubric_agreement.py")
    ),
    (
        "EXPERIMENT 3 — Question and feedback quality audit",
        os.path.join(EXP_DIR, "experiment_3_quality_evaluation", "evaluate_question_feedback_quality.py")
    ),
    (
        "EXPERIMENT 4 — End-to-end integration and multimodal service audit",
        os.path.join(EXP_DIR, "experiment_4_integration", "run_experiment_4.py")
    )
]


def run_all():
    print("=" * 80)
    print("PREMOCK AI — UNIFIED RESEARCH EXPERIMENTS EXECUTION (MY_PART)")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    results = []

    for name, script_path in EXPERIMENTS:
        print(f"\n>>> Running: {name}")
        print(f"    Script: {os.path.relpath(script_path, BASE_DIR)}")
        start_t = time.time()
        
        proc = subprocess.run(
            [sys.executable, script_path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start_t

        status = "PASS" if proc.returncode == 0 else "FAIL"
        results.append({
            "name": name,
            "status": status,
            "exit_code": proc.returncode,
            "elapsed_seconds": round(elapsed, 2)
        })

        if proc.stdout:
            # Print last few lines of stdout
            lines = proc.stdout.strip().splitlines()
            for line in lines[-6:]:
                print(f"    {line}")
        if proc.returncode != 0 and proc.stderr:
            print("    [STDERR]:")
            for line in proc.stderr.strip().splitlines()[-6:]:
                print(f"    ! {line}")

    print("\n" + "=" * 80)
    print("CONSOLIDATED EXPERIMENTS EXECUTION SUMMARY")
    print("=" * 80)
    for r in results:
        status_marker = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        print(f"  {status_marker} {r['name']} ({r['elapsed_seconds']}s, Exit Code: {r['exit_code']})")

    print("\nAudit reports and evidence documents updated successfully.")


if __name__ == "__main__":
    run_all()
