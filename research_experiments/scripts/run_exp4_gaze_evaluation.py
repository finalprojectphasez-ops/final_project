"""
run_exp4_gaze_evaluation.py
===========================
Experiment 4: MPIIGaze Eye Gaze Tracking Model Evaluation
Evaluates frozen gaze_model.keras separately on:
  - Validation set (p11, p12: 2,300 samples)
  - Independent test set (p13, p14: 1,502 samples)

Reports:
  1. Pitch MAE (radians and degrees)
  2. Yaw MAE (radians and degrees)
  3. Mean Pitch/Yaw MAE (radians and degrees)
  4. 3D Gaze Vector Angular Error (radians and degrees: mean, median, p95)
Keeps coordinate conventions and metric definitions distinct.
"""

import os
import json
import time
import numpy as np
import tensorflow as tf
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAZE_DATA_DIR = os.path.join(PROJECT_ROOT, "ml", "eye_contact", "dataset", "processed")
MODEL_PATH = os.path.join(PROJECT_ROOT, "backend", "ml_models", "gaze_model.keras")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "research_experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def angles_to_unit_vectors(pitch, yaw):
    """
    Convert spherical gaze angles (pitch, yaw) to 3D unit gaze vectors
    using MPIIGaze coordinate convention from preprocess.py:
      pitch = asin(-gy)  => gy = -sin(pitch)
      yaw = atan2(-gx, -gz) => gx = -cos(pitch)*sin(yaw), gz = -cos(pitch)*cos(yaw)
    """
    gx = -np.cos(pitch) * np.sin(yaw)
    gy = -np.sin(pitch)
    gz = -np.cos(pitch) * np.cos(yaw)
    vectors = np.stack([gx, gy, gz], axis=-1)
    # Re-normalize to guard against float precision artifacts
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / norms

def compute_angular_error(vec_true, vec_pred):
    """
    Computes angular error in radians between two batches of unit vectors.
    angular_error = arccos(clip(v_true . v_pred, -1.0, 1.0))
    """
    dot_prod = np.sum(vec_true * vec_pred, axis=-1)
    dot_prod = np.clip(dot_prod, -1.0, 1.0)
    angular_rad = np.arccos(dot_prod)
    return angular_rad

def evaluate_partition(model, X, y, partition_name, participants):
    print(f"\n--- Evaluating {partition_name.upper()} Partition ({', '.join(participants)}) ---")
    print(f"Sample count: {len(X)}")
    
    t0 = time.time()
    preds = model.predict(X, batch_size=64, verbose=1)
    elapsed = time.time() - t0
    
    true_pitch = y[:, 0]
    true_yaw = y[:, 1]
    pred_pitch = preds[:, 0]
    pred_yaw = preds[:, 1]
    
    pitch_err = np.abs(pred_pitch - true_pitch)
    yaw_err = np.abs(pred_yaw - true_yaw)
    
    pitch_mae_rad = float(np.mean(pitch_err))
    yaw_mae_rad = float(np.mean(yaw_err))
    mean_mae_rad = float((pitch_mae_rad + yaw_mae_rad) / 2.0)
    
    pitch_mae_deg = float(np.degrees(pitch_mae_rad))
    yaw_mae_deg = float(np.degrees(yaw_mae_rad))
    mean_mae_deg = float(np.degrees(mean_mae_rad))
    
    # 3D Gaze Vector Angular Error
    vec_true = angles_to_unit_vectors(true_pitch, true_yaw)
    vec_pred = angles_to_unit_vectors(pred_pitch, pred_yaw)
    angular_err_rad = compute_angular_error(vec_true, vec_pred)
    angular_err_deg = np.degrees(angular_err_rad)
    
    mean_ang_err_rad = float(np.mean(angular_err_rad))
    median_ang_err_rad = float(np.median(angular_err_rad))
    p95_ang_err_rad = float(np.percentile(angular_err_rad, 95))
    
    mean_ang_err_deg = float(np.mean(angular_err_deg))
    median_ang_err_deg = float(np.median(angular_err_deg))
    p95_ang_err_deg = float(np.percentile(angular_err_deg, 95))
    
    mse_total = float(np.mean((preds - y) ** 2))
    
    print(f"  Pitch MAE:               {pitch_mae_rad:.4f} rad ({pitch_mae_deg:.2f}°)")
    print(f"  Yaw MAE:                 {yaw_mae_rad:.4f} rad ({yaw_mae_deg:.2f}°)")
    print(f"  Mean (Pitch+Yaw)/2 MAE:  {mean_mae_rad:.4f} rad ({mean_mae_deg:.2f}°)")
    print(f"  3D Angular Error (Mean): {mean_ang_err_rad:.4f} rad ({mean_ang_err_deg:.2f}°)")
    print(f"  3D Angular Error (Med):  {median_ang_err_rad:.4f} rad ({median_ang_err_deg:.2f}°)")
    print(f"  3D Angular Error (p95):  {p95_ang_err_rad:.4f} rad ({p95_ang_err_deg:.2f}°)")
    print(f"  Total MSE Loss:          {mse_total:.6f}")
    print(f"  Inference Latency:       {elapsed:.2f}s ({elapsed / len(X) * 1000:.2f} ms/sample)")
    
    return {
        "partition": partition_name,
        "participants": participants,
        "sample_count": int(len(X)),
        "mse_loss": mse_total,
        "pitch_mae_rad": pitch_mae_rad,
        "pitch_mae_deg": pitch_mae_deg,
        "yaw_mae_rad": yaw_mae_rad,
        "yaw_mae_deg": yaw_mae_deg,
        "mean_pitch_yaw_mae_rad": mean_mae_rad,
        "mean_pitch_yaw_mae_deg": mean_mae_deg,
        "3d_vector_angular_error_rad": {
            "mean": mean_ang_err_rad,
            "median": median_ang_err_rad,
            "p95": p95_ang_err_rad
        },
        "3d_vector_angular_error_deg": {
            "mean": mean_ang_err_deg,
            "median": median_ang_err_deg,
            "p95": p95_ang_err_deg
        },
        "inference_latency_seconds": float(round(elapsed, 3)),
        "avg_latency_ms_per_sample": float(round(elapsed / len(X) * 1000, 3)),
        "predictions": preds,
        "angular_err_deg": angular_err_deg
    }

def main():
    print("=" * 70)
    print("EXPERIMENT 4: MPIIGaze Eye Gaze Tracking Evaluation")
    print("=" * 70)
    
    # Load metadata
    meta_path = os.path.join(GAZE_DATA_DIR, "metadata.json")
    with open(meta_path, "r") as f:
        meta = json.load(f)
    print("Loaded metadata.json:")
    print(f"  Val participants:  {meta['participants']['val']}")
    print(f"  Test participants: {meta['participants']['test']}")
    print(f"  Reported val count:  {meta['val_samples']}")
    print(f"  Reported test count: {meta['test_samples']}")
    
    # Load datasets
    X_val = np.load(os.path.join(GAZE_DATA_DIR, "X_val.npy"))
    y_val = np.load(os.path.join(GAZE_DATA_DIR, "y_val.npy"))
    X_test = np.load(os.path.join(GAZE_DATA_DIR, "X_test.npy"))
    y_test = np.load(os.path.join(GAZE_DATA_DIR, "y_test.npy"))
    
    assert len(X_val) == 2300, f"Expected 2300 val samples, got {len(X_val)}"
    assert len(X_test) == 1502, f"Expected 1502 test samples, got {len(X_test)}"
    
    print(f"\nLoading model from {MODEL_PATH}...")
    model = tf.keras.models.load_model(MODEL_PATH)
    
    val_res = evaluate_partition(model, X_val, y_val, "validation", meta['participants']['val'])
    test_res = evaluate_partition(model, X_test, y_test, "test", meta['participants']['test'])
    
    results = {
        "dataset": "MPIIGaze",
        "model_file": "gaze_model.keras",
        "coordinate_convention": "MPIIGaze spherical: pitch = asin(-gy), yaw = atan2(-gx, -gz)",
        "metric_definitions": {
            "pitch_mae": "mean(|pred_pitch - true_pitch|)",
            "yaw_mae": "mean(|pred_yaw - true_yaw|)",
            "mean_pitch_yaw_mae": "0.5 * (pitch_mae + yaw_mae)",
            "3d_angular_error": "arccos(clip(v_true . v_pred, -1.0, 1.0)) where v are normalized 3D gaze unit vectors"
        },
        "validation_partition": {k: v for k, v in val_res.items() if k not in ["predictions", "angular_err_deg"]},
        "test_partition": {k: v for k, v in test_res.items() if k not in ["predictions", "angular_err_deg"]},
        "discrepancy_analysis": {
            "reported_claim": "0.100 radians MAE",
            "validation_mae_actual": val_res["mean_pitch_yaw_mae_rad"],
            "test_mae_actual": test_res["mean_pitch_yaw_mae_rad"],
            "test_3d_angular_error_mean_deg": test_res["3d_vector_angular_error_deg"]["mean"],
            "findings": (
                "The previously claimed 0.100 rad error corresponds to the VALIDATION set MAE (0.0984 rad ~ 5.64°), "
                "which was evaluated on participants p11/p12. On the completely independent TEST participants (p13/p14), "
                f"the actual mean pitch/yaw MAE is {test_res['mean_pitch_yaw_mae_rad']:.4f} rad ({test_res['mean_pitch_yaw_mae_deg']:.2f}°), "
                f"and the true 3D gaze-vector angular error is {test_res['3d_vector_angular_error_deg']['mean']:.2f}°."
            )
        }
    }
    
    out_json_path = os.path.join(RESULTS_DIR, "exp4_gaze_evaluation.json")
    with open(out_json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved JSON results to: {out_json_path}")
    
    # Save per-sample predictions CSV for test partition
    df_test = pd.DataFrame({
        "sample_index": np.arange(len(y_test)),
        "true_pitch_rad": y_test[:, 0],
        "true_yaw_rad": y_test[:, 1],
        "pred_pitch_rad": test_res["predictions"][:, 0],
        "pred_yaw_rad": test_res["predictions"][:, 1],
        "pitch_abs_err_rad": np.abs(test_res["predictions"][:, 0] - y_test[:, 0]),
        "yaw_abs_err_rad": np.abs(test_res["predictions"][:, 1] - y_test[:, 1]),
        "angular_err_deg": test_res["angular_err_deg"]
    })
    out_csv_path = os.path.join(RESULTS_DIR, "exp4_predictions.csv")
    df_test.to_csv(out_csv_path, index=False)
    print(f"Saved test predictions to: {out_csv_path}")

if __name__ == "__main__":
    main()
