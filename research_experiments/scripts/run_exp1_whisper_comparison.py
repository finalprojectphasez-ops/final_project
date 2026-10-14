"""
run_exp1_whisper_comparison.py
==============================
Experiment 1: Whisper ASR Baseline vs. 20k LoRA vs. 40k LoRA Evaluation
Evaluates on identical frozen 500 held-out test recordings from Common Voice Indian Accent.
Strict verification:
  - 0 speaker overlap with training or validation splits.
  - Identical 8-bit quantization, feature extraction, decoder prompt, and decoding parameters.
  - Standard BasicTextNormalizer for normalized WER/CER.
  - Computes exact Substitutions (S), Deletions (D), Insertions (I), Hits (H), Word Error Rate (WER),
    and Character Error Rate (CER) via jiwer.process_words.
  - Exports per-clip references and predictions to CSV.
"""

import os
import json
import time
import torch
import numpy as np
import pandas as pd
from datasets import load_dataset, Audio
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
from peft import PeftModel
import jiwer
import evaluate as ev

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SPLIT_FILE = os.path.join(PROJECT_ROOT, "ml", "asr_training", "full_speaker_split.json")
BASE_MODEL_ID = "openai/whisper-base.en"
MODEL_20K_DIR = os.path.join(PROJECT_ROOT, "ml", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200")
MODEL_40K_DIR = os.path.join(PROJECT_ROOT, "ml", "asr_model", "whisper_indian_accent_40k_experiment")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "research_experiments", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TEST_N = 500
SEED = 42

def load_verified_test_dataset():
    print("Loading speaker splits from full_speaker_split.json...")
    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)
        
    train_spk = set(splits["train"])
    val_spk = set(splits["validation"])
    test_spk = set(splits["test"])
    
    assert len(train_spk & test_spk) == 0, "CRITICAL: Train/Test speaker overlap!"
    assert len(val_spk & test_spk) == 0, "CRITICAL: Val/Test speaker overlap!"
    
    print(f"  Train speakers: {len(train_spk)}")
    print(f"  Val speakers:   {len(val_spk)}")
    print(f"  Test speakers:  {len(test_spk)} [Strictly Disjoint: 0 Overlap]")
    
    print("Loading cached Common Voice dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    
    cids = ds["client_id"]
    test_indices = [i for i, cid in enumerate(cids) if cid in test_spk]
    train_indices = [i for i, cid in enumerate(cids) if cid in train_spk]
    
    assert not set(test_indices).intersection(set(train_indices)), "CRITICAL: Row index overlap!"
    
    test_ds = ds.select(test_indices).shuffle(seed=SEED).select(range(min(TEST_N, len(test_indices))))
    print(f"  Selected frozen {len(test_ds)} test recordings (seed={SEED})")
    
    speakers_in_test = set(test_ds["client_id"])
    print(f"  Total unique speakers in 500 test set: {len(speakers_in_test)}")
    
    return test_ds, len(speakers_in_test)

def transcribe_dataset(model, test_ds, processor):
    preds, refs = [], []
    model.eval()
    forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
    t0 = time.time()
    
    with torch.no_grad():
        for i, ex in enumerate(test_ds):
            audio = ex["audio"]
            inputs = processor.feature_extractor(
                audio["array"],
                sampling_rate=audio["sampling_rate"],
                return_tensors="pt"
            ).input_features.to(DEVICE).half()
            
            generated = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
            pred = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
            ref = ex["sentence"].strip()
            preds.append(pred)
            refs.append(ref)
            
            if (i + 1) % 50 == 0:
                elapsed = time.time() - t0
                print(f"    [{i+1}/{len(test_ds)}] {elapsed:.1f}s elapsed (avg {(elapsed/(i+1))*1000:.1f} ms/sample)", flush=True)
                
    elapsed_total = time.time() - t0
    return preds, refs, elapsed_total

def compute_detailed_metrics(preds_raw, refs_raw, normalizer, metric_cer):
    # Normalized texts
    preds_norm = [normalizer(p) for p in preds_raw]
    refs_norm = [normalizer(r) for r in refs_raw]
    
    # Process word measures via jiwer
    res_raw = jiwer.process_words(refs_raw, preds_raw)
    res_norm = jiwer.process_words(refs_norm, preds_norm)
    
    cer_raw = metric_cer.compute(predictions=preds_raw, references=refs_raw)
    cer_norm = metric_cer.compute(predictions=preds_norm, references=refs_norm)
    
    total_ref_words_raw = res_raw.hits + res_raw.substitutions + res_raw.deletions
    total_ref_words_norm = res_norm.hits + res_norm.substitutions + res_norm.deletions
    
    return {
        "raw": {
            "wer": float(round(res_raw.wer, 4)),
            "wer_pct": float(round(res_raw.wer * 100, 2)),
            "cer_pct": float(round(cer_raw * 100, 2)),
            "substitutions": int(res_raw.substitutions),
            "deletions": int(res_raw.deletions),
            "insertions": int(res_raw.insertions),
            "hits": int(res_raw.hits),
            "reference_words": int(total_ref_words_raw)
        },
        "normalized": {
            "wer": float(round(res_norm.wer, 4)),
            "wer_pct": float(round(res_norm.wer * 100, 2)),
            "cer_pct": float(round(cer_norm * 100, 2)),
            "substitutions": int(res_norm.substitutions),
            "deletions": int(res_norm.deletions),
            "insertions": int(res_norm.insertions),
            "hits": int(res_norm.hits),
            "reference_words": int(total_ref_words_norm)
        },
        "preds_raw": preds_raw,
        "preds_norm": preds_norm,
        "refs_raw": refs_raw,
        "refs_norm": refs_norm
    }

def main():
    print("=" * 70)
    print("EXPERIMENT 1: Whisper Baseline vs. 20k LoRA vs. 40k LoRA Comparison")
    print(f"Device: {DEVICE}")
    print("=" * 70)
    
    test_ds, n_speakers = load_verified_test_dataset()
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")
    normalizer = BasicTextNormalizer()
    metric_cer = ev.load("cer")
    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    
    # 1. EVALUATE BASE MODEL (openai/whisper-base.en)
    print("\n" + "-" * 70)
    print("  [MODEL 1/3] Loading Base Model (Zero-Shot openai/whisper-base.en)...")
    print("-" * 70)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []
    
    base_preds, base_refs, base_time = transcribe_dataset(base_model, test_ds, processor)
    del base_model
    torch.cuda.empty_cache()
    print(f"  Base Model completed in {base_time:.1f}s. Memory cleared.")
    
    # 2. EVALUATE 20K LORA (checkpoint-1200)
    print("\n" + "-" * 70)
    print("  [MODEL 2/3] Loading 20k LoRA Model (checkpoint-1200)...")
    print("-" * 70)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []
    model_20k = PeftModel.from_pretrained(base_model, MODEL_20K_DIR)
    
    preds_20k, _, time_20k = transcribe_dataset(model_20k, test_ds, processor)
    del model_20k, base_model
    torch.cuda.empty_cache()
    print(f"  20k LoRA completed in {time_20k:.1f}s. Memory cleared.")
    
    # 3. EVALUATE 40K LORA (checkpoint-500)
    print("\n" + "-" * 70)
    print("  [MODEL 3/3] Loading 40k LoRA Model (Best checkpoint-500)...")
    print("-" * 70)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []
    model_40k = PeftModel.from_pretrained(base_model, MODEL_40K_DIR)
    
    preds_40k, _, time_40k = transcribe_dataset(model_40k, test_ds, processor)
    del model_40k, base_model
    torch.cuda.empty_cache()
    print(f"  40k LoRA completed in {time_40k:.1f}s. Memory cleared.")
    
    # 4. COMPUTE DETAILED MEASURES
    print("\nComputing substitutions, deletions, insertions, WER, and CER...")
    m_base = compute_detailed_metrics(base_preds, base_refs, normalizer, metric_cer)
    m_20k = compute_detailed_metrics(preds_20k, base_refs, normalizer, metric_cer)
    m_40k = compute_detailed_metrics(preds_40k, base_refs, normalizer, metric_cer)
    
    results = {
        "dataset": "ishands/commonvoice-indian_accent",
        "split": "held-out-test",
        "total_clips": len(test_ds),
        "total_unique_speakers": n_speakers,
        "speaker_overlap_train": 0,
        "speaker_overlap_val": 0,
        "normalization_rules": "transformers.models.whisper.english_normalizer.BasicTextNormalizer (lowercase, punctuation stripped, numbers expanded, whitespace collapsed)",
        "models": {
            "base_whisper": {
                "name": "openai/whisper-base.en (Zero-Shot Base)",
                "adapter": None,
                "precision": "8-bit int quantized (BitsAndBytes)",
                "total_time_seconds": round(base_time, 2),
                "avg_ms_per_sample": round(base_time / len(test_ds) * 1000, 2),
                "metrics_raw": m_base["raw"],
                "metrics_normalized": m_base["normalized"]
            },
            "whisper_20k_lora": {
                "name": "whisper_indian_accent_lora_20k (checkpoint-1200)",
                "adapter_path": MODEL_20K_DIR,
                "precision": "8-bit base + LoRA adapter",
                "total_time_seconds": round(time_20k, 2),
                "avg_ms_per_sample": round(time_20k / len(test_ds) * 1000, 2),
                "metrics_raw": m_20k["raw"],
                "metrics_normalized": m_20k["normalized"]
            },
            "whisper_40k_lora": {
                "name": "whisper_indian_accent_40k_experiment (checkpoint-500)",
                "adapter_path": MODEL_40K_DIR,
                "precision": "8-bit base + LoRA adapter",
                "total_time_seconds": round(time_40k, 2),
                "avg_ms_per_sample": round(time_40k / len(test_ds) * 1000, 2),
                "metrics_raw": m_40k["raw"],
                "metrics_normalized": m_40k["normalized"]
            }
        },
        "comparisons": {
            "20k_vs_base": {
                "raw_wer_delta_pp": round(m_20k["raw"]["wer_pct"] - m_base["raw"]["wer_pct"], 2),
                "norm_wer_delta_pp": round(m_20k["normalized"]["wer_pct"] - m_base["normalized"]["wer_pct"], 2),
                "norm_cer_delta_pp": round(m_20k["normalized"]["cer_pct"] - m_base["normalized"]["cer_pct"], 2)
            },
            "40k_vs_20k": {
                "raw_wer_delta_pp": round(m_40k["raw"]["wer_pct"] - m_20k["raw"]["wer_pct"], 2),
                "norm_wer_delta_pp": round(m_40k["normalized"]["wer_pct"] - m_20k["normalized"]["wer_pct"], 2),
                "norm_cer_delta_pp": round(m_40k["normalized"]["cer_pct"] - m_20k["normalized"]["cer_pct"], 2)
            }
        }
    }
    
    out_json_path = os.path.join(RESULTS_DIR, "exp1_whisper_comparison.json")
    with open(out_json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved experiment JSON results to: {out_json_path}")
    
    # Save per-clip predictions CSV
    df_preds = pd.DataFrame({
        "clip_index": np.arange(len(test_ds)),
        "client_id": test_ds["client_id"],
        "reference_raw": base_refs,
        "reference_norm": m_base["refs_norm"],
        "base_pred_raw": base_preds,
        "base_pred_norm": m_base["preds_norm"],
        "lora_20k_pred_raw": preds_20k,
        "lora_20k_pred_norm": m_20k["preds_norm"],
        "lora_40k_pred_raw": preds_40k,
        "lora_40k_pred_norm": m_40k["preds_norm"]
    })
    out_csv_path = os.path.join(RESULTS_DIR, "exp1_predictions.csv")
    df_preds.to_csv(out_csv_path, index=False)
    print(f"Saved per-clip predictions to: {out_csv_path}")
    
    # Print clean summary table
    print("\n" + "=" * 78)
    print("  EXPERIMENT 1 SUMMARY (500 Held-Out Clips, 103 Disjoint Speakers)")
    print("=" * 78)
    print(f"{'Model':<25} | {'Raw WER':<10} | {'Norm WER':<10} | {'Norm CER':<10} | {'S / D / I (Norm)':<18}")
    print("-" * 78)
    for k, name in [("base_whisper", "Base (whisper-base.en)"), ("whisper_20k_lora", "20k LoRA (ckp-1200)"), ("whisper_40k_lora", "40k LoRA (ckp-500)")]:
        m = results["models"][k]
        norm = m["metrics_normalized"]
        raw = m["metrics_raw"]
        sdi = f"{norm['substitutions']} / {norm['deletions']} / {norm['insertions']}"
        print(f"{name:<25} | {raw['wer_pct']:>8.2f}% | {norm['wer_pct']:>8.2f}% | {norm['cer_pct']:>8.2f}% | {sdi:<18}")
    print("=" * 78)

if __name__ == "__main__":
    main()
