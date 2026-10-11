import os
import numpy as np

import tensorflow as tf
from tensorflow.keras.models import load_model

dataset_dir = os.path.join(os.path.dirname(__file__), 'dataset', 'processed')
model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ml_models', 'gaze_model.keras')

print("--- TEST-SET INSPECTION ---")
print("WARNING: This script is for exploratory analysis ONLY.")
print("The results of this script MUST NOT be used to choose calibration thresholds.")
print("Loading test data and model...")
X_test = np.load(os.path.join(dataset_dir, 'X_test.npy'))
y_test = np.load(os.path.join(dataset_dir, 'y_test.npy'))
model = load_model(model_path)

print("Generating predictions...")
y_pred = model.predict(X_test, verbose=0)

print("\n--- Pearson Correlation ---")
p_corr_pitch = np.corrcoef(y_test[:, 0], y_pred[:, 0])[0, 1]
p_corr_yaw = np.corrcoef(y_test[:, 1], y_pred[:, 1])[0, 1]

print(f"Pitch Correlation: {p_corr_pitch:.4f}")
print(f"Yaw Correlation: {p_corr_yaw:.4f}")

print("\n--- Bias / Extreme Value Analysis ---")
pitch_diff = np.mean(y_pred[:, 0] - y_test[:, 0])
yaw_diff = np.mean(y_pred[:, 1] - y_test[:, 1])
print(f"Mean Pitch Error (Bias): {pitch_diff:.4f}")
print(f"Mean Yaw Error (Bias): {yaw_diff:.4f}")

# Extreme values
extreme_pitch_mask = np.abs(y_test[:, 0]) > 0.3
extreme_yaw_mask = np.abs(y_test[:, 1]) > 0.3

print(f"Extreme Pitch (>0.3) MAE: {np.mean(np.abs(y_pred[extreme_pitch_mask, 0] - y_test[extreme_pitch_mask, 0])):.4f}")
print(f"Extreme Yaw (>0.3) MAE: {np.mean(np.abs(y_pred[extreme_yaw_mask, 1] - y_test[extreme_yaw_mask, 1])):.4f}")
