"""
run_exp2_asr_latency.py
=======================
Experiment 2: Whisper ASR Latency & Real-Time Factor (RTF) Benchmark
Measures:
  - 50 held-out clips spanning audio durations from 1.5s to 10.5s.
  - 5 initial GPU warm-up runs.
  - 3 repetitions per clip (batch size = 1).
  - Explicit torch.cuda.synchronize() before and after every inference call.
  - Separate complete processing (feature extraction + generate + token decode)
    and pure inference (model.generate) timings.
  - Reports audio duration, latency (ms), and RTF for every run.
"""

import os
import json
import time
import torch
import numpy as np
import pandas as pd
from datasets import load_dataset, Audio
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from peft import PeftModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPLIT_FILE = os.path.join(PROJECT_ROOT, "ml", "asr_training", "full_speaker_split.json")
ADAPTER_PATH = os.path.join(PROJECT_ROOT, "ml", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200")
BASE_MODEL_ID = "openai/whisper-base.en"
RESULTS_DIR = os.path.join(PROJECT_ROOT, "research_experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WARMUP_RUNS = 5
REPETITIONS = 3
N_CLIPS = 50
SEED = 42

def load_held_out_clips():
    print("Loading test split and Common Voice dataset...")
    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)
    test_spk = set(splits["test"])
    train_spk = set(splits["train"])
    val_spk = set(splits["validation"])
    
    assert len(test_spk & train_spk) == 0, "Speaker overlap detected!"
    assert len(test_spk & val_spk) == 0, "Speaker overlap detected!"
    
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    
    test_indices = [i for i, cid in enumerate(ds["client_id"]) if cid in test_spk]
    test_ds = ds.select(test_indices).shuffle(seed=SEED).select(range(min(500, len(test_indices))))
    
    # Calculate durations and select 50 evenly spaced clips across duration spectrum
    durations = [len(x["audio"]["array"]) / 16000.0 for x in test_ds]
    sorted_order = np.argsort(durations)
    
    # Select 50 clips spaced across the 500 clips
    selected_indices = [sorted_order[int(i)] for i in np.linspace(0, len(sorted_order) - 1, N_CLIPS)]
    selected_subset = test_ds.select(selected_indices)
    
    return selected_subset

def main():
    print("=" * 70)
    print("EXPERIMENT 2: ASR Latency & Real-Time Factor (RTF) Evaluation")
    print(f"Device: {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"Precision: 8-bit quantized weights (BitsAndBytes) + FP16 input features")
    print("=" * 70)
    
    clips = load_held_out_clips()
    print(f"Selected {len(clips)} clips for latency benchmarking.")
    clip_durations = [len(x["audio"]["array"]) / 16000.0 for x in clips]
    print(f"  Duration range: {min(clip_durations):.2f}s to {max(clip_durations):.2f}s (Mean: {np.mean(clip_durations):.2f}s)")
    
    print("\nLoading processor and model...")
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")
    forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
    
    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []
    model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
    model.eval()
    
    # 1. Warm-up
    print(f"\nPerforming {WARMUP_RUNS} GPU warm-up runs...")
    dummy_audio = clips[0]["audio"]["array"]
    dummy_sr = clips[0]["audio"]["sampling_rate"]
    dummy_feat = processor.feature_extractor(dummy_audio, sampling_rate=dummy_sr, return_tensors="pt").input_features.to(DEVICE).half()
    
    with torch.no_grad():
        for w in range(WARMUP_RUNS):
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            _ = model.generate(dummy_feat, forced_decoder_ids=forced_ids, max_new_tokens=225)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            print(f"  Warm-up {w+1}/{WARMUP_RUNS} completed.")
            
    # 2. Benchmarking
    print(f"\nBenchmarking {len(clips)} clips x {REPETITIONS} repetitions...")
    records = []
    
    with torch.no_grad():
        for clip_idx, ex in enumerate(clips):
            audio_arr = ex["audio"]["array"]
            sr = ex["audio"]["sampling_rate"]
            duration_s = len(audio_arr) / float(sr)
            ref_text = ex["sentence"].strip()
            
            for rep in range(REPETITIONS):
                # Complete processing timer start
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_proc_start = time.perf_counter()
                
                # Feature extraction
                feat = processor.feature_extractor(audio_arr, sampling_rate=sr, return_tensors="pt").input_features.to(DEVICE).half()
                
                # Inference timer start
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_inf_start = time.perf_counter()
                
                generated = model.generate(feat, forced_decoder_ids=forced_ids, max_new_tokens=225)
                
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t_inf_end = time.perf_counter()
                
                # Decode text
                pred_text = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
                t_proc_end = time.perf_counter()
                
                inf_latency_ms = (t_inf_end - t_inf_start) * 1000.0
                complete_latency_ms = (t_proc_end - t_proc_start) * 1000.0
                
                rtf_inf = (inf_latency_ms / 1000.0) / duration_s
                rtf_complete = (complete_latency_ms / 1000.0) / duration_s
                
                records.append({
                    "clip_index": clip_idx,
                    "repetition": rep + 1,
                    "audio_duration_seconds": round(duration_s, 3),
                    "inference_latency_ms": round(inf_latency_ms, 2),
                    "complete_latency_ms": round(complete_latency_ms, 2),
                    "rtf_inference": round(rtf_inf, 4),
                    "rtf_complete": round(rtf_complete, 4),
                    "reference": ref_text,
                    "prediction": pred_text
                })
                
            if (clip_idx + 1) % 10 == 0:
                print(f"  Processed {clip_idx + 1}/{len(clips)} clips...")
                
    df_runs = pd.DataFrame(records)
    runs_csv_path = os.path.join(RESULTS_DIR, "exp2_latency_runs.csv")
    df_runs.to_csv(runs_csv_path, index=False)
    print(f"\nSaved raw run records to: {runs_csv_path}")
    
    # Statistical analysis
    inf_ms = df_runs["inference_latency_ms"].values
    comp_ms = df_runs["complete_latency_ms"].values
    durs = df_runs["audio_duration_seconds"].values
    rtf_inf = df_runs["rtf_inference"].values
    rtf_comp = df_runs["rtf_complete"].values
    
    stats_summary = {
        "hardware": {
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
            "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else None,
            "precision": "8-bit int quantized (BitsAndBytes) + FP16 input features",
            "batch_size": 1
        },
        "benchmark_design": {
            "total_clips": N_CLIPS,
            "warmup_runs": WARMUP_RUNS,
            "repetitions_per_clip": REPETITIONS,
            "total_measurements": len(records),
            "cuda_synchronized": True
        },
        "audio_durations": {
            "min_seconds": float(round(np.min(durs), 2)),
            "max_seconds": float(round(np.max(durs), 2)),
            "mean_seconds": float(round(np.mean(durs), 2)),
            "median_seconds": float(round(np.median(durs), 2))
        },
        "inference_only_latency_ms": {
            "mean": float(round(np.mean(inf_ms), 2)),
            "median": float(round(np.median(inf_ms), 2)),
            "p95": float(round(np.percentile(inf_ms, 95), 2)),
            "min": float(round(np.min(inf_ms), 2)),
            "max": float(round(np.max(inf_ms), 2)),
            "std": float(round(np.std(inf_ms), 2))
        },
        "complete_processing_latency_ms": {
            "mean": float(round(np.mean(comp_ms), 2)),
            "median": float(round(np.median(comp_ms), 2)),
            "p95": float(round(np.percentile(comp_ms, 95), 2)),
            "min": float(round(np.min(comp_ms), 2)),
            "max": float(round(np.max(comp_ms), 2)),
            "std": float(round(np.std(comp_ms), 2))
        },
        "real_time_factor_complete": {
            "mean": float(round(np.mean(rtf_comp), 4)),
            "median": float(round(np.median(rtf_comp), 4)),
            "p95": float(round(np.percentile(rtf_comp, 95), 4)),
            "is_faster_than_realtime": bool(np.mean(rtf_comp) < 1.0),
            "realtime_speedup_ratio": float(round(1.0 / np.mean(rtf_comp), 2))
        },
        "scientific_assessment_of_claimed_823ms": {
            "claimed_metric": "823.89 ms",
            "measured_mean_complete_ms": float(round(np.mean(comp_ms), 2)),
            "measured_mean_inf_ms": float(round(np.mean(inf_ms), 2)),
            "measured_mean_rtf": float(round(np.mean(rtf_comp), 4)),
            "assessment": (
                "The 823.89 ms metric is an average per-utterance latency on Common Voice clips "
                f"(which average ~5.46 seconds in duration). With a complete processing mean latency of "
                f"{np.mean(comp_ms):.1f} ms and an RTF of {np.mean(rtf_comp):.3f}, the model operates "
                f"at ~{1.0/np.mean(rtf_comp):.1f}x real-time speed. However, latency scales with audio length "
                f"and decoding length; describing 823.89 ms as a fixed universal latency without reporting "
                "underlying audio durations and Real-Time Factor is incomplete."
            )
        }
    }
    
    summary_json_path = os.path.join(RESULTS_DIR, "exp2_asr_latency.json")
    with open(summary_json_path, "w") as f:
        json.dump(stats_summary, f, indent=2)
    print(f"Saved statistical summary to: {summary_json_path}")
    print("\n--- Benchmark Summary ---")
    print(f"Mean Complete Latency: {np.mean(comp_ms):.2f} ms")
    print(f"Median Complete Latency: {np.median(comp_ms):.2f} ms")
    print(f"p95 Complete Latency: {np.percentile(comp_ms, 95):.2f} ms")
    print(f"Mean Real-Time Factor (RTF): {np.mean(rtf_comp):.4f} (Speedup: {1.0/np.mean(rtf_comp):.2f}x)")

if __name__ == "__main__":
    main()
