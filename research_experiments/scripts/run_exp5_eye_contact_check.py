"""
run_exp5_eye_contact_check.py
=============================
Experiment 5: Eye-Contact Ground-Truth Validation Readiness Audit
Checks repository for independently labeled camera-directed gaze data.
If absent:
  - Formally documents absence (avoiding circular threshold-as-ground-truth fallacy)
  - Formulates a standardized human data collection, calibration, and labeling protocol
  - Marks evaluation status as PENDING LABELED DATA
"""

import os
import json
import glob

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "research_experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

CANDIDATE_SEARCH_PATHS = [
    os.path.join(PROJECT_ROOT, "ml", "eye_contact", "dataset"),
    os.path.join(PROJECT_ROOT, "ml", "eye_contact"),
    os.path.join(PROJECT_ROOT, "backend", "ml_models"),
    os.path.join(PROJECT_ROOT, "backend", "data"),
]

def search_for_ground_truth_labels():
    found_files = []
    for base in CANDIDATE_SEARCH_PATHS:
        if os.path.exists(base):
            for pattern in ["*eye_contact*.csv", "*ground_truth*.json", "*camera_labels*.csv", "*fixation*.txt"]:
                matches = glob.glob(os.path.join(base, "**", pattern), recursive=True)
                found_files.extend(matches)
    return found_files

def main():
    print("=" * 70)
    print("EXPERIMENT 5: Eye-Contact Validation Readiness Audit")
    print("=" * 70)
    
    matches = search_for_ground_truth_labels()
    print(f"Searching for ground-truth eye-contact label files: found {len(matches)} files.")
    
    threshold_path = os.path.join(PROJECT_ROOT, "ml", "eye_contact", "eye_contact_thresholds.json")
    thresholds_exist = os.path.exists(threshold_path)
    thresholds = {}
    if thresholds_exist:
        with open(threshold_path, "r") as f:
            thresholds = json.load(f)
        print("Existing threshold configuration found:")
        print(json.dumps(thresholds, indent=2))
        
    status = "PENDING LABELED DATA"
    
    protocol = {
        "protocol_name": "PreMock AI Standardized Eye-Contact Validation Protocol",
        "version": "1.0-CONSENTED",
        "objective": "Establish an empirical, independent benchmark for binary camera-directed gaze classification (eye contact vs. non-eye contact).",
        "participant_requirements": {
            "target_cohort": "10-20 diverse participants with varied skin tones, eye shapes, and eyewear (glasses, contact lenses, none)",
            "subject_isolation": "Strict participant-level disjoint splits: 60% Calibration cohort (threshold tuning), 40% Evaluation cohort (zero-tuning held-out test)",
            "informed_consent": "Full IRB/Ethics-compliant participant consent for video recording and research publication."
        },
        "fixation_conditions": [
            {
                "condition_id": "COND_01_CAMERA_DIRECT",
                "label": 1,
                "description": "Fixation directly on laptop webcam lens (true eye-contact).",
                "duration_seconds": 10,
                "trials_per_subject": 3
            },
            {
                "condition_id": "COND_02_SCREEN_CENTER",
                "label": 0,
                "description": "Reading text in center of screen (subtle downward gaze, ~10-15° below camera).",
                "duration_seconds": 10,
                "trials_per_subject": 3
            },
            {
                "condition_id": "COND_03_SCREEN_PERIPHERY",
                "label": 0,
                "description": "Fixation on top-left, top-right, bottom-left, bottom-right corners of display.",
                "duration_seconds": 10,
                "trials_per_subject": 4
            },
            {
                "condition_id": "COND_04_OFF_SCREEN_AVOIDANCE",
                "label": 0,
                "description": "Looking away toward interviewer, room entrance, or downward note-taking.",
                "duration_seconds": 10,
                "trials_per_subject": 4
            }
        ],
        "recording_environment": {
            "distance_cm": "50 cm to 70 cm typical laptop working distance",
            "resolutions": "720p and 1080p at 30 fps",
            "lighting_variations": ["Natural daylight", "Overhead LED fluorescent", "Low-light evening (screen glare only)"]
        },
        "evaluation_metrics_when_data_available": [
            "Accuracy",
            "Precision (Camera Gaze)",
            "Recall / Sensitivity (Camera Gaze)",
            "Specificity (Screen/Aversion Gaze)",
            "F1-Score (Binary)",
            "Confusion Matrix (2x2)",
            "ROC-AUC across continuous threshold sweeps"
        ]
    }
    
    report = {
        "experiment_status": status,
        "ground_truth_dataset_found": False,
        "active_implementation": {
            "method": "Heuristic angular thresholding on predicted pitch/yaw",
            "source_file": "ml/eye_contact/calibrate_eye_contact.py",
            "threshold_file": "ml/eye_contact/eye_contact_thresholds.json",
            "configured_thresholds": thresholds,
            "scientific_limitation": (
                "The current platform evaluates 'eye contact' purely via geometric thresholding "
                "(|pitch - center_pitch| <= 0.06 rad and |yaw - center_yaw| <= 0.075 rad). "
                "Because no human-labeled ground truth exists in the repository, any self-evaluated "
                "F1 or accuracy based on model thresholds would be circular and scientifically invalid."
            )
        },
        "standardized_protocol": protocol
    }
    
    out_json_path = os.path.join(RESULTS_DIR, "exp5_eye_contact_status.json")
    with open(out_json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved Experiment 5 Status to: {out_json_path}")
    print(f"Status: {status}")

if __name__ == "__main__":
    main()
