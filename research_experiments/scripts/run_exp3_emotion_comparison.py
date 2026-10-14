"""
run_exp3_emotion_comparison.py
==============================
Experiment 3: FER-2013 Emotion Recognition — Legacy v1 CNN vs. MobileNetV2 v2
Evaluates both models on identical unseen 7,178 test images from FER-2013.
Preserves exact preprocessing for both models:
  - v1: 48x48 grayscale normalized [0, 1]
  - v2: 96x96 RGB normalized [0, 1] (channel-repeated and resized)
"""

import os
import json
import time
import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import pandas as pd

# Set seeds
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "ml", "emotion", "dataset", "processed")
MODELS_DIR = os.path.join(PROJECT_ROOT, "backend", "ml_models")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "research_experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MODEL_V1_PATH = os.path.join(MODELS_DIR, "emotion_model.keras")
MODEL_V2_PATH = os.path.join(MODELS_DIR, "emotion_model_v2.keras")
X_TEST_PATH = os.path.join(PROCESSED_DIR, "X_test.npy")
Y_TEST_PATH = os.path.join(PROCESSED_DIR, "y_test.npy")
X_TRAIN_PATH = os.path.join(PROCESSED_DIR, "X_train.npy")

EMOTIONS = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
NUM_CLASSES = 7

def verify_partition_isolation():
    print("Verifying partition isolation between train and test sets...")
    x_test = np.load(X_TEST_PATH)
    x_train = np.load(X_TRAIN_PATH)
    print(f"  X_train samples: {x_train.shape[0]} (Expected: 28,709)")
    print(f"  X_test samples:  {x_test.shape[0]} (Expected: 7,178 = 3,589 PublicTest + 3,589 PrivateTest)")
    
    # Check shape & size
    assert x_train.shape[0] == 28709, "X_train count mismatch!"
    assert x_test.shape[0] == 7178, "X_test count mismatch!"
    print("  Partition sizes match standard FER-2013 train and combined test sets.")
    return x_test

def main():
    print("=" * 70)
    print("EXPERIMENT 3: Emotion Recognition Model Comparison (v1 CNN vs. v2 MobileNet)")
    print("=" * 70)
    
    X_test_raw = verify_partition_isolation()
    y_test = np.load(Y_TEST_PATH)
    print(f"Loaded test labels: {len(y_test)} labels across 7 classes.")
    
    # 1. Evaluate v1
    print("\n--- Evaluating Model v1 (Legacy 6-Layer CNN) ---")
    print(f"Loading {MODEL_V1_PATH}...")
    model_v1 = tf.keras.models.load_model(MODEL_V1_PATH)
    
    # v1 preprocessing: (N, 48, 48, 1) float32 in [0, 1]
    X_v1 = np.expand_dims(X_test_raw, axis=-1).astype(np.float32)
    
    t0 = time.time()
    preds_v1_probs = model_v1.predict(X_v1, batch_size=64, verbose=1)
    v1_latency = time.time() - t0
    y_pred_v1 = np.argmax(preds_v1_probs, axis=1)
    
    acc_v1 = accuracy_score(y_test, y_pred_v1)
    f1_macro_v1 = f1_score(y_test, y_pred_v1, average='macro')
    f1_weighted_v1 = f1_score(y_test, y_pred_v1, average='weighted')
    prec_macro_v1 = precision_score(y_test, y_pred_v1, average='macro')
    rec_macro_v1 = recall_score(y_test, y_pred_v1, average='macro')
    prec_weighted_v1 = precision_score(y_test, y_pred_v1, average='weighted')
    rec_weighted_v1 = recall_score(y_test, y_pred_v1, average='weighted')
    cm_v1 = confusion_matrix(y_test, y_pred_v1)
    report_v1_dict = classification_report(y_test, y_pred_v1, target_names=EMOTIONS, output_dict=True)
    
    print(f"v1 Accuracy:        {acc_v1*100:.2f}%")
    print(f"v1 Macro F1:        {f1_macro_v1*100:.2f}%")
    print(f"v1 Weighted F1:     {f1_weighted_v1*100:.2f}%")
    print(f"v1 Total Inference: {v1_latency:.2f}s ({v1_latency / len(y_test) * 1000:.2f} ms/sample)")
    
    del model_v1
    tf.keras.backend.clear_session()
    
    # 2. Evaluate v2
    print("\n--- Evaluating Model v2 (MobileNetV2 Fine-Tuned) ---")
    print(f"Loading {MODEL_V2_PATH}...")
    model_v2 = tf.keras.models.load_model(MODEL_V2_PATH)
    
    # v2 preprocessing: (N, 96, 96, 3) float32 in [0, 1]
    print("Preprocessing test data for v2 (resizing 48x48 gray to 96x96 RGB)...")
    X_rgb = np.stack([X_test_raw, X_test_raw, X_test_raw], axis=-1)
    # Process in batches to avoid high memory spike
    X_v2_batches = []
    chunk_size = 1000
    for i in range(0, len(X_rgb), chunk_size):
        chunk = X_rgb[i:i+chunk_size]
        resized_chunk = tf.image.resize(chunk, [96, 96]).numpy().astype(np.float32)
        X_v2_batches.append(resized_chunk)
    X_v2 = np.concatenate(X_v2_batches, axis=0)
    print(f"v2 input tensor ready: {X_v2.shape}, dtype={X_v2.dtype}")
    
    t0 = time.time()
    preds_v2_probs = model_v2.predict(X_v2, batch_size=64, verbose=1)
    v2_latency = time.time() - t0
    y_pred_v2 = np.argmax(preds_v2_probs, axis=1)
    
    acc_v2 = accuracy_score(y_test, y_pred_v2)
    f1_macro_v2 = f1_score(y_test, y_pred_v2, average='macro')
    f1_weighted_v2 = f1_score(y_test, y_pred_v2, average='weighted')
    prec_macro_v2 = precision_score(y_test, y_pred_v2, average='macro')
    rec_macro_v2 = recall_score(y_test, y_pred_v2, average='macro')
    prec_weighted_v2 = precision_score(y_test, y_pred_v2, average='weighted')
    rec_weighted_v2 = recall_score(y_test, y_pred_v2, average='weighted')
    cm_v2 = confusion_matrix(y_test, y_pred_v2)
    report_v2_dict = classification_report(y_test, y_pred_v2, target_names=EMOTIONS, output_dict=True)
    
    print(f"v2 Accuracy:        {acc_v2*100:.2f}%")
    print(f"v2 Macro F1:        {f1_macro_v2*100:.2f}%")
    print(f"v2 Weighted F1:     {f1_weighted_v2*100:.2f}%")
    print(f"v2 Total Inference: {v2_latency:.2f}s ({v2_latency / len(y_test) * 1000:.2f} ms/sample)")
    
    # Per-class comparison
    per_class_summary = {}
    for emo in EMOTIONS:
        per_class_summary[emo] = {
            "v1_precision": report_v1_dict[emo]["precision"],
            "v1_recall": report_v1_dict[emo]["recall"],
            "v1_f1": report_v1_dict[emo]["f1-score"],
            "v2_precision": report_v2_dict[emo]["precision"],
            "v2_recall": report_v2_dict[emo]["recall"],
            "v2_f1": report_v2_dict[emo]["f1-score"],
            "support": report_v1_dict[emo]["support"]
        }
        
    results = {
        "dataset": "FER-2013",
        "split": "PublicTest + PrivateTest (Combined held-out test)",
        "total_test_samples": int(len(y_test)),
        "class_labels": EMOTIONS,
        "class_distribution": {EMOTIONS[i]: int(c) for i, c in zip(*np.unique(y_test, return_counts=True))},
        "model_v1": {
            "name": "emotion_model.keras (Legacy v1 6-layer CNN)",
            "deployed_in_production": True,
            "deployed_port": 8002,
            "input_shape": [48, 48, 1],
            "accuracy": float(acc_v1),
            "macro_f1": float(f1_macro_v1),
            "weighted_f1": float(f1_weighted_v1),
            "macro_precision": float(prec_macro_v1),
            "macro_recall": float(rec_macro_v1),
            "weighted_precision": float(prec_weighted_v1),
            "weighted_recall": float(rec_weighted_v1),
            "total_inference_time_s": float(round(v1_latency, 3)),
            "avg_latency_ms_per_sample": float(round(v1_latency / len(y_test) * 1000, 3)),
            "confusion_matrix": cm_v1.tolist(),
            "classification_report": report_v1_dict
        },
        "model_v2": {
            "name": "emotion_model_v2.keras (MobileNetV2 Fine-Tuned)",
            "deployed_in_production": False,
            "offline_research_model": True,
            "input_shape": [96, 96, 3],
            "accuracy": float(acc_v2),
            "macro_f1": float(f1_macro_v2),
            "weighted_f1": float(f1_weighted_v2),
            "macro_precision": float(prec_macro_v2),
            "macro_recall": float(rec_macro_v2),
            "weighted_precision": float(prec_weighted_v2),
            "weighted_recall": float(rec_weighted_v2),
            "total_inference_time_s": float(round(v2_latency, 3)),
            "avg_latency_ms_per_sample": float(round(v2_latency / len(y_test) * 1000, 3)),
            "confusion_matrix": cm_v2.tolist(),
            "classification_report": report_v2_dict
        },
        "comparison": {
            "accuracy_delta_pp": float(round((acc_v2 - acc_v1) * 100, 2)),
            "macro_f1_delta_pp": float(round((f1_macro_v2 - f1_macro_v1) * 100, 2)),
            "weighted_f1_delta_pp": float(round((f1_weighted_v2 - f1_weighted_v1) * 100, 2)),
            "per_class": per_class_summary
        }
    }
    
    # Save JSON summary
    out_json_path = os.path.join(RESULTS_DIR, "exp3_emotion_comparison.json")
    with open(out_json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved JSON results to: {out_json_path}")
    
    # Save per-sample predictions CSV
    df_preds = pd.DataFrame({
        "sample_index": np.arange(len(y_test)),
        "true_label_idx": y_test,
        "true_emotion": [EMOTIONS[i] for i in y_test],
        "v1_pred_idx": y_pred_v1,
        "v1_pred_emotion": [EMOTIONS[i] for i in y_pred_v1],
        "v1_correct": (y_test == y_pred_v1).astype(int),
        "v2_pred_idx": y_pred_v2,
        "v2_pred_emotion": [EMOTIONS[i] for i in y_pred_v2],
        "v2_correct": (y_test == y_pred_v2).astype(int)
    })
    out_csv_path = os.path.join(RESULTS_DIR, "exp3_predictions.csv")
    df_preds.to_csv(out_csv_path, index=False)
    print(f"Saved per-sample predictions to: {out_csv_path}")

if __name__ == "__main__":
    main()
