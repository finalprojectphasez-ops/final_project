"""
verify_checkpoint375_norepeat3.py

Dedicated Verification Script for PreMock AI ASR:
Verifying the existing 10k technical-interview model (checkpoint-375)
with repetition-control decoding (no_repeat_ngram_size=3) on the 200
held-out technical-interview recordings.

STRICT CONSTRAINTS:
- Read-only inference.
- Do not train.
- Do not alter model checkpoints.
- Do not alter production ASR or other services.
- Never overwrite existing reports.
- Output saved strictly to a new file.
"""

import os
import sys
import re
import json
import time
import argparse
from typing import List, Dict, Any, Tuple

import numpy as np
import torch
from datasets import load_dataset
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    BitsAndBytesConfig,
)
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
from peft import PeftModel
import evaluate as ev
import jiwer
import scipy.stats as st

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

BASE_MODEL_ID = "openai/whisper-base.en"
CHECKPOINT_DIR = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora", "phase1_10k", "checkpoint-375"
)
GLOSSARY_PATH = os.path.join(SCRIPT_DIR, "tech_glossary.json")
BASELINE_V2_RESULTS = os.path.join(SCRIPT_DIR, "eval_results_v2_200samples.json")
OUTPUT_JSON_PATH = os.path.join(SCRIPT_DIR, "verification_checkpoint375_norepeat3.json")
DATASET_ID = "WhissleAI/Meta_STT_EN-IN_Tech_Interviews"

# Trailing demographic/annotation tag stripper
ANNOTATION_SUFFIX_REGEX = re.compile(
    r'(?:\s+\b(?:AGE|GER|EMOTION|INTENT)_[A-Za-z0-9_]+\b)+\s*$'
)


def clean_transcript(raw_text: str) -> str:
    """Strips trailing metadata annotation tags while preserving all spoken words."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    return ANNOTATION_SUFFIX_REGEX.sub("", raw_text).strip()


# ---------------------------------------------------------------------------
# Repetition Loop Failure Detector
# ---------------------------------------------------------------------------
def detect_repetition_failure(pred_raw: str) -> Tuple[bool, str]:
    """
    Detects whether a transcription output exhibits repetition degeneracy:
    1. Repetitive dot loop: >= 5 space-separated dots.
    2. Repeated trigram: any 3-word phrase repeated >= 4 times.
    3. Repeated bigram: any 2-word phrase repeated >= 5 times.
    """
    if not pred_raw or not isinstance(pred_raw, str):
        return False, "empty"

    # Check punctuation loop
    if re.search(r'(?:\s*\.\s*){5,}', pred_raw):
        return True, "dot_loop"

    words = pred_raw.strip().split()
    if len(words) < 8:
        return False, "none"

    # Trigram repetition check
    trigrams = {}
    for i in range(len(words) - 2):
        tg = ' '.join(words[i:i+3]).lower()
        trigrams[tg] = trigrams.get(tg, 0) + 1
        if trigrams[tg] >= 4:
            return True, f"trigram_repeat: '{tg}'"

    # Bigram repetition check
    bigrams = {}
    for i in range(len(words) - 1):
        bg = ' '.join(words[i:i+2]).lower()
        bigrams[bg] = bigrams.get(bg, 0) + 1
        if bigrams[bg] >= 5:
            return True, f"bigram_repeat: '{bg}'"

    return False, "none"


# ---------------------------------------------------------------------------
# Normalized Technical Glossary Loader
# ---------------------------------------------------------------------------
def load_normalized_glossary(path: str, normalizer: BasicTextNormalizer) -> List[str]:
    """Loads and normalizes domain terms from tech_glossary.json."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Glossary file missing: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_terms = data.get("terms", [])

    normalized_set = set()
    for term in raw_terms:
        norm_t = normalizer(term).strip()
        if norm_t:
            normalized_set.add(norm_t)

    return sorted(list(normalized_set), key=lambda x: (len(x.split()), len(x)), reverse=True)


def evaluate_technical_terms(
    references: List[str],
    predictions: List[str],
    normalizer: BasicTextNormalizer,
    glossary: List[str],
) -> Dict[str, Any]:
    """Computes technical-term recall against normalized glossary."""
    total_tech_in_ref = 0
    matched_tech = 0
    missed_terms = []

    for ref, pred in zip(references, predictions):
        norm_ref = normalizer(ref)
        norm_pred = normalizer(pred)

        ref_terms = []
        for term in glossary:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, norm_ref):
                ref_terms.append(term)

        for term in ref_terms:
            total_tech_in_ref += 1
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, norm_pred):
                matched_tech += 1
            else:
                missed_terms.append(term)

    recall = (matched_tech / total_tech_in_ref * 100.0) if total_tech_in_ref > 0 else 100.0

    return {
        "total_in_references": total_tech_in_ref,
        "correctly_transcribed": matched_tech,
        "tech_term_recall_pct": round(recall, 2),
        "frequent_misses": list(set(missed_terms))[:10],
    }


# ---------------------------------------------------------------------------
# Held-Out Data Loader
# ---------------------------------------------------------------------------
def load_heldout_dataset(max_samples: int = 200) -> List[Dict[str, Any]]:
    """Loads held-out validation samples from WhissleAI using streaming=True."""
    print(f"\n[1/5] Streaming {max_samples} held-out validation samples from {DATASET_ID}...")
    ds_val = load_dataset(DATASET_ID, split="validation", streaming=True)

    records = []
    for s in ds_val:
        if len(records) >= max_samples:
            break
        raw_text = s.get("text", "")
        clean_text = clean_transcript(raw_text)
        audio = s.get("audio", None)

        if not audio or not clean_text or len(clean_text.strip()) == 0:
            continue

        arr = audio.get("array", None)
        sr = audio.get("sampling_rate", 16000)
        dur = len(arr) / float(sr) if arr is not None else 0.0

        if dur < 0.5 or dur > 30.0:
            continue

        records.append({
            "audio": {"array": arr, "sampling_rate": sr},
            "reference": clean_text,
            "duration": dur,
            "source_file": s.get("source_file", ""),
        })

    print(f"  Successfully loaded {len(records)} clean held-out validation utterances.")
    return records


# ---------------------------------------------------------------------------
# Main Verification Routine
# ---------------------------------------------------------------------------
def main():
    print("=" * 80)
    print("PreMock AI — Checkpoint-375 & Repetition-Control Decoding Verification")
    print("=" * 80)
    print(f"Base Model              : {BASE_MODEL_ID} (8-bit quantized)")
    print(f"Target LoRA Adapter     : {CHECKPOINT_DIR}")
    print(f"Decoding Setting        : no_repeat_ngram_size=3, num_beams=1, max_length=225")
    print(f"Target Output Report    : {OUTPUT_JSON_PATH}")
    print("=" * 80)

    # 1. Verification of output file safety: Destination MUST NOT exist
    if os.path.exists(OUTPUT_JSON_PATH):
        print(f"\n[ERROR] Output destination already exists: {OUTPUT_JSON_PATH}")
        print("        To prevent overwriting existing reports, execution has been stopped.")
        sys.exit(1)

    # 2. Setup normalizer and glossary
    normalizer = BasicTextNormalizer()
    glossary = load_normalized_glossary(GLOSSARY_PATH, normalizer)
    print(f"[2/5] Loaded and normalized {len(glossary)} domain terms from technical glossary.")

    # 3. Load 200 Held-Out Samples
    eval_records = load_heldout_dataset(200)
    if len(eval_records) != 200:
        raise ValueError(f"Expected 200 samples, but got {len(eval_records)}")

    references = [r["reference"] for r in eval_records]
    norm_refs = [normalizer(r) for r in references]
    total_audio_sec = sum(r["duration"] for r in eval_records)

    # 4. Confirm alignment with baseline experiment (eval_results_v2_200samples.json)
    if os.path.exists(BASELINE_V2_RESULTS):
        with open(BASELINE_V2_RESULTS, "r", encoding="utf-8") as f:
            v2_baseline = json.load(f)
        v2_samples = v2_baseline.get("per_recording_results", [])
        print(f"  Verifying sample alignment with baseline v2 ({len(v2_samples)} records)...")
        mismatches = 0
        for i in range(len(eval_records)):
            if eval_records[i]["source_file"] != v2_samples[i]["source_file"]:
                mismatches += 1
            if norm_refs[i] != v2_samples[i]["reference_norm"]:
                mismatches += 1
        if mismatches == 0:
            print("  [CONFIRMED] 100% exact match of all 200 audio recordings and normalized references!")
        else:
            print(f"  [WARNING] Detected {mismatches} mismatches against baseline v2!")
    else:
        print("  [NOTICE] Baseline v2 results file not found for cross-comparison.")

    # 5. Load Model and Adapter
    print(f"\n[3/5] Loading base Whisper model and attaching checkpoint-375...")
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")

    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_map = "auto" if device == "cuda" else None

    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_cfg if device == "cuda" else None,
        device_map=device_map,
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []

    model = PeftModel.from_pretrained(base_model, CHECKPOINT_DIR)
    model.eval()

    target_dtype = model.get_base_model().model.encoder.conv1.weight.dtype
    print(f"  Model loaded successfully on {device} with encoder dtype {target_dtype}.")

    # 6. Run Inference with no_repeat_ngram_size=3
    print(f"\n[4/5] Running verification inference across 200 utterances (no_repeat_ngram_size=3)...")
    raw_predictions = []
    norm_predictions = []
    latencies_ms = []
    repetition_flags = []

    start_eval_time = time.time()

    with torch.no_grad():
        for s_idx, item in enumerate(eval_records):
            arr = item["audio"]["array"]
            sr = item["audio"]["sampling_rate"]

            input_features = processor.feature_extractor(
                arr, sampling_rate=sr, return_tensors="pt"
            ).input_features
            if device == "cuda":
                input_features = input_features.to(device=device, dtype=target_dtype)
            else:
                input_features = input_features.to(dtype=target_dtype)

            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t0 = time.perf_counter()

            # Generation with no_repeat_ngram_size=3
            pred_ids = model.generate(
                input_features,
                max_length=225,
                num_beams=1,
                do_sample=False,
                no_repeat_ngram_size=3,
            )
            transcription = processor.batch_decode(pred_ids, skip_special_tokens=True)[0]

            if torch.cuda.is_available():
                torch.cuda.synchronize()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            is_rep, rep_reason = detect_repetition_failure(transcription)

            raw_predictions.append(transcription)
            norm_predictions.append(normalizer(transcription))
            latencies_ms.append(round(elapsed_ms, 2))
            repetition_flags.append({
                "is_failure": is_rep,
                "reason": rep_reason
            })

            if (s_idx + 1) % 25 == 0 or (s_idx + 1) == len(eval_records):
                print(f"  Completed {s_idx + 1:3d} / {len(eval_records)} utterances ({time.time() - start_eval_time:.1f}s elapsed)...")

    # Clean up model from GPU
    del model
    del base_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 7. Compute Metrics
    print(f"\n[5/5] Computing evaluation metrics and comparative statistics...")
    wer_metric = ev.load("wer")
    cer_metric = ev.load("cer")

    raw_wer = wer_metric.compute(predictions=raw_predictions, references=references) * 100.0
    norm_wer = wer_metric.compute(predictions=norm_predictions, references=norm_refs) * 100.0
    norm_cer = cer_metric.compute(predictions=norm_predictions, references=norm_refs) * 100.0

    tech_results = evaluate_technical_terms(references, raw_predictions, normalizer, glossary)
    rep_fail_count = sum(1 for f in repetition_flags if f["is_failure"])

    total_infer_sec = sum(latencies_ms) / 1000.0
    rtf = total_infer_sec / total_audio_sec if total_audio_sec > 0 else 0.0
    mean_lat = float(np.mean(latencies_ms))
    median_lat = float(np.median(latencies_ms))

    # Per-utterance WER for statistical comparison against baseline Model A
    per_sample_records = []
    per_sample_wers = []
    for i in range(len(eval_records)):
        p_wer = jiwer.wer(norm_refs[i], norm_predictions[i]) * 100.0 if len(norm_refs[i].strip()) > 0 else 0.0
        per_sample_wers.append(p_wer)

        rec = eval_records[i]
        per_sample_records.append({
            "index": i + 1,
            "source_file": rec["source_file"],
            "duration_sec": round(rec["duration"], 3),
            "reference_raw": rec["reference"],
            "reference_norm": norm_refs[i],
            "prediction_raw": raw_predictions[i],
            "prediction_norm": norm_predictions[i],
            "normalized_wer_pct": round(p_wer, 2),
            "latency_ms": latencies_ms[i],
            "repetition_flag": repetition_flags[i],
        })

    # Comparative evaluation against Model A (deployed) from eval_results_v2_200samples.json
    comparison = {}
    if os.path.exists(BASELINE_V2_RESULTS):
        with open(BASELINE_V2_RESULTS, "r", encoding="utf-8") as f:
            v2_data = json.load(f)
        model_a_summary = v2_data.get("summary_metrics", {}).get("model_a", {})
        model_b_summary = v2_data.get("summary_metrics", {}).get("model_b", {})
        v2_per_sample = v2_data.get("per_recording_results", [])

        # Model A per-sample normalized WER
        model_a_sample_wers = [s.get("model_a", {}).get("norm_wer_pct", 0.0) for s in v2_per_sample]
        model_b_baseline_wers = [s.get("model_b", {}).get("norm_wer_pct", 0.0) for s in v2_per_sample]

        # Calculate wins, ties, losses vs Model A
        wins_vs_a = sum(1 for a, b in zip(model_a_sample_wers, per_sample_wers) if b < a)
        ties_vs_a = sum(1 for a, b in zip(model_a_sample_wers, per_sample_wers) if b == a)
        losses_vs_a = sum(1 for a, b in zip(model_a_sample_wers, per_sample_wers) if b > a)

        # Wilcoxon signed-rank test vs Model A
        deltas_vs_a = [a - b for a, b in zip(model_a_sample_wers, per_sample_wers)]
        non_zero_deltas = [d for d in deltas_vs_a if d != 0]
        if len(non_zero_deltas) > 0:
            w_stat_a, p_val_a = st.wilcoxon(deltas_vs_a)
        else:
            w_stat_a, p_val_a = 0.0, 1.0

        comparison = {
            "model_a_deployed_wer_pct": model_a_summary.get("norm_wer_pct"),
            "model_b_baseline_greedy_wer_pct": model_b_summary.get("norm_wer_pct"),
            "model_b_norepeat3_wer_pct": round(norm_wer, 2),
            "absolute_wer_improvement_vs_model_a": round(model_a_summary.get("norm_wer_pct", 0.0) - norm_wer, 2),
            "absolute_wer_improvement_vs_greedy": round(model_b_summary.get("norm_wer_pct", 0.0) - norm_wer, 2),
            "wins_vs_model_a": wins_vs_a,
            "ties_vs_model_a": ties_vs_a,
            "losses_vs_model_a": losses_vs_a,
            "wilcoxon_stat_vs_model_a": float(w_stat_a),
            "wilcoxon_p_value_vs_model_a": float(p_val_a),
        }

    # Summary dictionary
    summary = {
        "model_id": CHECKPOINT_DIR,
        "base_model": BASE_MODEL_ID,
        "quantization": "8-bit",
        "decoding": {
            "max_length": 225,
            "num_beams": 1,
            "do_sample": False,
            "no_repeat_ngram_size": 3,
        },
        "num_samples_evaluated": len(eval_records),
        "total_audio_duration_seconds": round(total_audio_sec, 2),
        "total_inference_seconds": round(total_infer_sec, 2),
        "normalized_wer_pct": round(norm_wer, 2),
        "raw_wer_pct": round(raw_wer, 2),
        "normalized_cer_pct": round(norm_cer, 2),
        "technical_term_recall_pct": tech_results["tech_term_recall_pct"],
        "technical_terms_matched": tech_results["correctly_transcribed"],
        "technical_terms_total": tech_results["total_in_references"],
        "repetition_failures_count": rep_fail_count,
        "repetition_failure_rate_pct": round(rep_fail_count / len(eval_records) * 100.0, 2),
        "mean_latency_ms": round(mean_lat, 2),
        "median_latency_ms": round(median_lat, 2),
        "real_time_factor": round(rtf, 4),
        "comparison_with_deployed_model_a": comparison,
    }

    # Print Summary Table
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"Normalized WER               : {summary['normalized_wer_pct']:.2f}%")
    print(f"Raw WER                      : {summary['raw_wer_pct']:.2f}%")
    print(f"Normalized CER               : {summary['normalized_cer_pct']:.2f}%")
    print(f"Technical-Term Recall        : {summary['technical_term_recall_pct']:.2f}% ({summary['technical_terms_matched']}/{summary['technical_terms_total']})")
    print(f"Repetition Failures          : {summary['repetition_failures_count']} / {len(eval_records)} ({summary['repetition_failure_rate_pct']:.1f}%)")
    print(f"Mean Latency                 : {summary['mean_latency_ms']:.1f} ms")
    print(f"Median Latency               : {summary['median_latency_ms']:.1f} ms")
    print(f"Real-Time Factor (RTF)       : {summary['real_time_factor']:.4f}")
    if comparison:
        print("-" * 80)
        print(f"Deployed Model A Norm WER    : {comparison['model_a_deployed_wer_pct']:.2f}%")
        print(f"Improvement vs Deployed      : +{comparison['absolute_wer_improvement_vs_model_a']:.2f} percentage points (p = {comparison['wilcoxon_p_value_vs_model_a']:.4e})")
        print(f"Win / Tie / Loss vs Model A  : {comparison['wins_vs_model_a']} Wins / {comparison['ties_vs_model_a']} Ties / {comparison['losses_vs_model_a']} Losses")
        print(f"Improvement vs Model B Greedy: +{comparison['absolute_wer_improvement_vs_greedy']:.2f} percentage points")
    print("=" * 80)

    # Inspect outlier / known repetition cases
    print("\nREPETITION SUPPRESSION SPOT CHECKS:")
    # Sample 49 (idx 48) and Sample 119 (idx 118)
    for sample_no in [49, 119]:
        idx = sample_no - 1
        rec = per_sample_records[idx]
        print(f"\nSample #{sample_no}:")
        print(f"  Reference : \"{rec['reference_raw']}\"")
        print(f"  Prediction: \"{rec['prediction_raw'][:140]}...\"")
        print(f"  Repetition: {rec['repetition_flag']['is_failure']} ({rec['repetition_flag']['reason']})")
        print(f"  Latency   : {rec['latency_ms']:.1f} ms")

    # Build and Save JSON Payload
    payload = {
        "metadata": {
            "verification_experiment": "checkpoint375_norepeat3_verification",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model_path": CHECKPOINT_DIR,
            "base_model": BASE_MODEL_ID,
            "quantization": "8-bit",
            "decoding_parameters": {
                "max_length": 225,
                "num_beams": 1,
                "do_sample": False,
                "no_repeat_ngram_size": 3,
            },
            "num_samples_evaluated": len(eval_records),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
        "summary_metrics": summary,
        "per_recording_results": per_sample_records,
    }

    # Refuse to overwrite if created during execution
    if os.path.exists(OUTPUT_JSON_PATH):
        print(f"\n[FATAL] Output file already exists: {OUTPUT_JSON_PATH}. Aborting write.")
        sys.exit(1)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\n[SUCCESS] New verification report written safely to:")
    print(f"  {OUTPUT_JSON_PATH}")
    print("\n[VERIFICATION COMPLETE] Production files and models remain 100% unchanged.")


if __name__ == "__main__":
    main()
