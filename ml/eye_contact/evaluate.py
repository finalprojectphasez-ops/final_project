import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt

# Paths
dataset_dir = os.path.join(os.path.dirname(__file__), 'dataset', 'processed')
model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'ml_models')
model_path = os.path.join(model_dir, 'gaze_model.keras')

def evaluate_model():
    print("Loading test data...")
    X_test = np.load(os.path.join(dataset_dir, 'X_test.npy'))
    y_test = np.load(os.path.join(dataset_dir, 'y_test.npy'))
    
    print("Loading model...")
    model = load_model(model_path)
    
    print("Evaluating model...")
    results = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test Loss (MSE): {results[0]:.4f}")
    print(f"Test MAE: {results[1]:.4f}")
    
    print("\nGenerating predictions...")
    y_pred = model.predict(X_test)
    
    # Target-wise MAE
    mae_pitch = np.mean(np.abs(y_pred[:, 0] - y_test[:, 0]))
    mae_yaw = np.mean(np.abs(y_pred[:, 1] - y_test[:, 1]))
    
    print(f"Target-wise MAE -> Pitch: {mae_pitch:.4f}, Yaw: {mae_yaw:.4f}")
    print(f"Actual Target Range -> Pitch: [{y_test[:, 0].min():.4f}, {y_test[:, 0].max():.4f}], Yaw: [{y_test[:, 1].min():.4f}, {y_test[:, 1].max():.4f}]")
    print(f"Prediction Range    -> Pitch: [{y_pred[:, 0].min():.4f}, {y_pred[:, 0].max():.4f}], Yaw: [{y_pred[:, 1].min():.4f}, {y_pred[:, 1].max():.4f}]")

    # Save a scatter plot of predicted vs actual
    plt.figure(figsize=(10, 5))
    
    plt.subplot(1, 2, 1)
    plt.scatter(y_test[:, 0], y_pred[:, 0], alpha=0.3, s=2)
    plt.plot([y_test[:, 0].min(), y_test[:, 0].max()], [y_test[:, 0].min(), y_test[:, 0].max()], 'r--')
    plt.title("Pitch: Actual vs Predicted")
    plt.xlabel("Actual Pitch")
    plt.ylabel("Predicted Pitch")
    
    plt.subplot(1, 2, 2)
    plt.scatter(y_test[:, 1], y_pred[:, 1], alpha=0.3, s=2)
    plt.plot([y_test[:, 1].min(), y_test[:, 1].max()], [y_test[:, 1].min(), y_test[:, 1].max()], 'r--')
    plt.title("Yaw: Actual vs Predicted")
    plt.xlabel("Actual Yaw")
    plt.ylabel("Predicted Yaw")
    
    plt.tight_layout()
    plot_path = os.path.join(dataset_dir, 'evaluation_scatter.png')
    plt.savefig(plot_path)
    print(f"Saved evaluation plot to: {plot_path}")

if __name__ == "__main__":
    evaluate_model()
