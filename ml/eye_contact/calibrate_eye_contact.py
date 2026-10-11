import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

def load_eye_contact_config():
    config_path = os.path.join(os.path.dirname(__file__), 'eye_contact_thresholds.json')
    if not os.path.exists(config_path):
        return None
    import json
    with open(config_path, 'r') as f:
        return json.load(f)

def gaze_to_eye_contact(pitch, yaw, cfg=None):
    """
    Evaluates whether a predicted (pitch, yaw) constitutes eye contact.
    """
    if cfg is None:
        cfg = load_eye_contact_config()
        if cfg is None:
            raise ValueError("Eye contact thresholds not found. Run calibrate_eye_contact.py first.")
            
    # Adjust predictions by the calibrated center offset
    adj_pitch = pitch - cfg["center_pitch"]
    adj_yaw = yaw - cfg["center_yaw"]
    
    # Check if within tolerance
    looking_at_camera = (abs(adj_pitch) <= cfg["pitch_threshold"]) and (abs(adj_yaw) <= cfg["yaw_threshold"])
    
    # Calculate continuous score 0-100 based on euclidean distance from center
    # Normalize by the tolerances to get a distance ratio
    dist = np.sqrt((adj_pitch / cfg["pitch_threshold"])**2 + (adj_yaw / cfg["yaw_threshold"])**2)
    
    # If dist is 0, score is 100. If dist >= 1.5, score is 0.
    score = max(0, min(100, (1.0 - (dist / 1.5)) * 100))
    
    return {
        "looking_at_camera": bool(looking_at_camera),
        "gaze_score": round(float(score), 1)
    }

def calibrate_thresholds(y_val, y_pred, mean_pitch_err, mean_yaw_err):
    # Find predictions where the actual gaze is near (0,0) (within 0.1 rad / 5 degrees)
    center_mask = (np.abs(y_val[:, 0]) < 0.1) & (np.abs(y_val[:, 1]) < 0.1)
    center_preds = y_pred[center_mask]
    
    if len(center_preds) == 0:
        print("No validation samples looking perfectly center. Using heuristics.")
        center_pitch = np.mean(y_pred[:, 0])
        center_yaw = 0.0
    else:
        center_pitch = np.mean(center_preds[:, 0])
        center_yaw = np.mean(center_preds[:, 1])
        
    print(f"\n--- Calibration ---")
    print(f"Number of 'looking center' samples in Val: {len(center_preds)}")
    print(f"Model predicts center as -> Pitch: {center_pitch:.4f}, Yaw: {center_yaw:.4f}")
    
    # Base threshold on the MAE to account for the model's inherent noise
    # We add a buffer of ~5 degrees (0.087 rad)
    pitch_threshold = mean_pitch_err + 0.087
    yaw_threshold = mean_yaw_err + 0.087
    
    return {
        "center_pitch": float(center_pitch),
        "center_yaw": float(center_yaw),
        "pitch_threshold": float(pitch_threshold),
        "yaw_threshold": float(yaw_threshold)
    }

if __name__ == "__main__":
    dataset_dir = os.path.join(os.path.dirname(__file__), 'dataset', 'processed')
    model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ml_models', 'gaze_model.keras')

    print("Loading validation data and model...")
    X_val = np.load(os.path.join(dataset_dir, 'X_val.npy'))
    y_val = np.load(os.path.join(dataset_dir, 'y_val.npy'))
    from tensorflow.keras.models import load_model
    model = load_model(model_path)

    print("Generating validation predictions...")
    y_pred = model.predict(X_val, verbose=0)

    # Calculate Errors
    pitch_err = np.abs(y_pred[:, 0] - y_val[:, 0])
    yaw_err = np.abs(y_pred[:, 1] - y_val[:, 1])

    print("\n--- Validation Error Stats (Radians) ---")
    print(f"Mean Absolute Pitch Error: {np.mean(pitch_err):.4f}")
    print(f"Mean Absolute Yaw Error: {np.mean(yaw_err):.4f}")
    
    config = calibrate_thresholds(y_val, y_pred, np.mean(pitch_err), np.mean(yaw_err))

    import json
    config_path = os.path.join(os.path.dirname(__file__), 'eye_contact_thresholds.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

    print(f"\nRecommended Eye Contact Configuration (saved to {config_path}):")
    print(f"Center Pitch Offset: {config['center_pitch']:.4f}")
    print(f"Center Yaw Offset: {config['center_yaw']:.4f}")
    print(f"Pitch Tolerance (+/-): {config['pitch_threshold']:.4f}")
    print(f"Yaw Tolerance (+/-): {config['yaw_threshold']:.4f}")
