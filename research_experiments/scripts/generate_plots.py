"""
generate_plots.py
=================
Generates empirical figures from saved experimental records for PreMock AI research report:
  1. Figure 1: Experiment 1 — Corpus Word and Character Error Rates (Base vs. 20k vs. 40k)
  2. Figure 2: Experiment 2 — Processing Latency vs. Audio Duration & RTF Distribution
  3. Figure 3: Experiment 3 — FER-2013 Confusion Matrices (Legacy v1 CNN vs. MobileNetV2 v2)
  4. Figure 4: Experiment 4 — MPIIGaze Pitch/Yaw MAE and 3D Angular Error Distribution
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
PLOTS_DIR = os.path.join(PROJECT_ROOT, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Set clean aesthetic styling
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

def plot_experiment_2():
    json_path = os.path.join(RESULTS_DIR, "exp2_asr_latency.json")
    csv_path = os.path.join(RESULTS_DIR, "exp2_latency_runs.csv")
    if not os.path.exists(csv_path):
        print("Exp 2 data not found, skipping.")
        return
        
    df = pd.read_csv(csv_path)
    with open(json_path, "r") as f:
        meta = json.load(f)
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    
    # Subplot 1: Latency vs. Audio Duration
    ax1.scatter(df["audio_duration_seconds"], df["complete_latency_ms"], color="#1f77b4", alpha=0.6, edgecolors="none", s=35, label="Measured Runs (3 reps/clip)")
    ax1.scatter(df["audio_duration_seconds"], df["inference_latency_ms"], color="#ff7f0e", alpha=0.6, edgecolors="none", s=25, label="Inference Only")
    
    # Linear fit for complete latency
    z = np.polyfit(df["audio_duration_seconds"], df["complete_latency_ms"], 1)
    p = np.poly1d(z)
    x_vals = np.linspace(df["audio_duration_seconds"].min(), df["audio_duration_seconds"].max(), 100)
    ax1.plot(x_vals, p(x_vals), color="#1f77b4", linestyle="--", linewidth=1.5, label=f"Trend: {z[0]:.1f}ms/s + {z[1]:.1f}ms")
    
    # Claimed 823.89 ms horizontal reference
    ax1.axhline(823.89, color="#d62728", linestyle=":", linewidth=1.5, label="Reported 823.89 ms Claim")
    
    ax1.set_title("Processing Latency vs. Audio Duration (Batch Size 1, RTX 3050)", fontsize=11, fontweight="bold", pad=10)
    ax1.set_xlabel("Audio Duration (seconds)", fontsize=10)
    ax1.set_ylabel("Latency (milliseconds)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    # Subplot 2: Real-Time Factor (RTF) Distribution
    ax2.hist(df["rtf_complete"], bins=20, color="#2ca02c", alpha=0.75, edgecolor="#1b611b")
    ax2.axvline(df["rtf_complete"].mean(), color="#d62728", linestyle="--", linewidth=1.5, label=f"Mean RTF: {df['rtf_complete'].mean():.4f} (~{1/df['rtf_complete'].mean():.1f}x real-time)")
    ax2.axvline(1.0, color="#333333", linestyle="-", linewidth=1.2, label="Real-Time Boundary (RTF = 1.0)")
    
    ax2.set_title("Real-Time Factor (RTF) Distribution across 150 Runs", fontsize=11, fontweight="bold", pad=10)
    ax2.set_xlabel("RTF (Latency / Duration)", fontsize=10)
    ax2.set_ylabel("Frequency", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "exp2_latency_vs_duration.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Experiment 2 plot to: {out_path}")

def plot_experiment_3():
    json_path = os.path.join(RESULTS_DIR, "exp3_emotion_comparison.json")
    if not os.path.exists(json_path):
        print("Exp 3 data not found, skipping.")
        return
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    emotions = data["class_labels"]
    cm_v1 = np.array(data["model_v1"]["confusion_matrix"])
    cm_v2 = np.array(data["model_v2"]["confusion_matrix"])
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=300)
    
    # Heatmap v1
    im1 = ax1.imshow(cm_v1, interpolation='nearest', cmap=plt.cm.Blues)
    ax1.set_title(f"Model v1: Legacy 6-Layer CNN\nTest Accuracy: {data['model_v1']['accuracy']*100:.2f}% | F1: {data['model_v1']['weighted_f1']*100:.2f}%", fontsize=11, fontweight="bold")
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    
    tick_marks = np.arange(len(emotions))
    ax1.set_xticks(tick_marks)
    ax1.set_xticklabels(emotions, rotation=45, ha="right")
    ax1.set_yticks(tick_marks)
    ax1.set_yticklabels(emotions)
    
    for i in range(cm_v1.shape[0]):
        for j in range(cm_v1.shape[1]):
            val = cm_v1[i, j]
            color = "white" if val > cm_v1.max() / 2 else "black"
            ax1.text(j, i, format(val, 'd'), ha="center", va="center", color=color, fontsize=8.5)
            
    ax1.set_ylabel("True Emotion Label", fontsize=10)
    ax1.set_xlabel("Predicted Emotion Label", fontsize=10)
    
    # Heatmap v2
    im2 = ax2.imshow(cm_v2, interpolation='nearest', cmap=plt.cm.Greens)
    ax2.set_title(f"Model v2: MobileNetV2 Fine-Tuned\nTest Accuracy: {data['model_v2']['accuracy']*100:.2f}% | F1: {data['model_v2']['weighted_f1']*100:.2f}%", fontsize=11, fontweight="bold")
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    
    ax2.set_xticks(tick_marks)
    ax2.set_xticklabels(emotions, rotation=45, ha="right")
    ax2.set_yticks(tick_marks)
    ax2.set_yticklabels(emotions)
    
    for i in range(cm_v2.shape[0]):
        for j in range(cm_v2.shape[1]):
            val = cm_v2[i, j]
            color = "white" if val > cm_v2.max() / 2 else "black"
            ax2.text(j, i, format(val, 'd'), ha="center", va="center", color=color, fontsize=8.5)
            
    ax2.set_ylabel("True Emotion Label", fontsize=10)
    ax2.set_xlabel("Predicted Emotion Label", fontsize=10)
    
    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "exp3_confusion_matrices.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Experiment 3 plot to: {out_path}")

def plot_experiment_4():
    json_path = os.path.join(RESULTS_DIR, "exp4_gaze_evaluation.json")
    csv_path = os.path.join(RESULTS_DIR, "exp4_predictions.csv")
    if not os.path.exists(json_path) or not os.path.exists(csv_path):
        print("Exp 4 data not found, skipping.")
        return
        
    with open(json_path, "r") as f:
        meta = json.load(f)
    df = pd.read_csv(csv_path)
    
    val_meta = meta["validation_partition"]
    test_meta = meta["test_partition"]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    
    # Subplot 1: Bar chart comparing Validation vs Test MAE and 3D Angular Error
    metrics = ["Pitch MAE", "Yaw MAE", "Mean MAE", "3D Angular Err"]
    val_vals = [val_meta["pitch_mae_deg"], val_meta["yaw_mae_deg"], val_meta["mean_pitch_yaw_mae_deg"], val_meta["3d_vector_angular_error_deg"]["mean"]]
    test_vals = [test_meta["pitch_mae_deg"], test_meta["yaw_mae_deg"], test_meta["mean_pitch_yaw_mae_deg"], test_meta["3d_vector_angular_error_deg"]["mean"]]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    rects1 = ax1.bar(x - width/2, val_vals, width, label="Validation (p11, p12: 2300 samples)", color="#3498db")
    rects2 = ax1.bar(x + width/2, test_vals, width, label="Test (p13, p14: 1502 samples)", color="#e74c3c")
    
    ax1.set_title("MPIIGaze Subject-Independent Evaluation: Val vs. Test Errors", fontsize=11, fontweight="bold", pad=10)
    ax1.set_ylabel("Error (Degrees)", fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.grid(True, linestyle="--", alpha=0.4, axis="y")
    ax1.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:.2f}°", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5)
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:.2f}°", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5)
        
    # Subplot 2: Histogram of 3D Angular Error on Test Set
    ax2.hist(df["angular_err_deg"], bins=30, color="#9b59b6", alpha=0.75, edgecolor="#6c3483")
    ax2.axvline(test_meta["3d_vector_angular_error_deg"]["mean"], color="#e74c3c", linestyle="--", linewidth=1.5, label=f"Mean: {test_meta['3d_vector_angular_error_deg']['mean']:.2f}°")
    ax2.axvline(test_meta["3d_vector_angular_error_deg"]["median"], color="#27ae60", linestyle="-.", linewidth=1.5, label=f"Median: {test_meta['3d_vector_angular_error_deg']['median']:.2f}°")
    ax2.axvline(test_meta["3d_vector_angular_error_deg"]["p95"], color="#f39c12", linestyle=":", linewidth=1.5, label=f"p95: {test_meta['3d_vector_angular_error_deg']['p95']:.2f}°")
    
    ax2.set_title("3D Gaze Vector Angular Error Distribution (Test Set, N=1,502)", fontsize=11, fontweight="bold", pad=10)
    ax2.set_xlabel("Angular Error (Degrees)", fontsize=10)
    ax2.set_ylabel("Sample Count", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "exp4_gaze_error_distributions.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Experiment 4 plot to: {out_path}")

def plot_experiment_1():
    json_path = os.path.join(RESULTS_DIR, "exp1_whisper_comparison.json")
    if not os.path.exists(json_path):
        print("Exp 1 data not found, skipping.")
        return
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    models = ["Base (whisper-base.en)", "20k LoRA (ckp-1200)", "40k LoRA (ckp-500)"]
    keys = ["base_whisper", "whisper_20k_lora", "whisper_40k_lora"]
    
    raw_wer = [data["models"][k]["metrics_raw"]["wer_pct"] for k in keys]
    norm_wer = [data["models"][k]["metrics_normalized"]["wer_pct"] for k in keys]
    norm_cer = [data["models"][k]["metrics_normalized"]["cer_pct"] for k in keys]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    
    x = np.arange(len(models))
    width = 0.28
    
    rects1 = ax1.bar(x - width, raw_wer, width, label="Raw Corpus WER (%)", color="#7f7f7f")
    rects2 = ax1.bar(x, norm_wer, width, label="Normalized WER (%)", color="#1f77b4")
    rects3 = ax1.bar(x + width, norm_cer, width, label="Normalized CER (%)", color="#2ca02c")
    
    ax1.set_title("Speech Recognition Error Rates on 500 Disjoint Held-Out Clips", fontsize=11, fontweight="bold", pad=10)
    ax1.set_ylabel("Error Rate (%)", fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.4, axis="y")
    ax1.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    for r in rects1:
        h = r.get_height()
        ax1.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    for r in rects2:
        h = r.get_height()
        ax1.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
    for r in rects3:
        h = r.get_height()
        ax1.annotate(f"{h:.1f}%", xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8)
        
    # Subplot 2: Breakdown of Substitutions, Deletions, Insertions
    subs = [data["models"][k]["metrics_normalized"]["substitutions"] for k in keys]
    dels = [data["models"][k]["metrics_normalized"]["deletions"] for k in keys]
    inss = [data["models"][k]["metrics_normalized"]["insertions"] for k in keys]
    
    ax2.bar(x, subs, width=0.5, label="Substitutions (S)", color="#e74c3c")
    ax2.bar(x, dels, width=0.5, bottom=subs, label="Deletions (D)", color="#f39c12")
    bottom_sd = [s + d for s, d in zip(subs, dels)]
    ax2.bar(x, inss, width=0.5, bottom=bottom_sd, label="Insertions (I)", color="#3498db")
    
    ax2.set_title("Word Error Decomposition (Normalized Text, 500 Clips)", fontsize=11, fontweight="bold", pad=10)
    ax2.set_ylabel("Count of Errors", fontsize=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.4, axis="y")
    ax2.legend(frameon=True, facecolor="#F8F9FA", edgecolor="#DDDDDD", fontsize=8.5)
    
    plt.tight_layout()
    out_path = os.path.join(PLOTS_DIR, "exp1_wer_cer_comparison.png")
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Experiment 1 plot to: {out_path}")

def main():
    print("Generating plots from empirical results...")
    plot_experiment_2()
    plot_experiment_3()
    plot_experiment_4()
    plot_experiment_1()
    print("All available plots rendered.")

if __name__ == "__main__":
    main()
