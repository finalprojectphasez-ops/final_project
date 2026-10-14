"""
evaluate_decoding_experiments.py

Controlled Decoding Experiment for PreMock AI ASR:
Evaluating inference-time repetition suppression configurations on the
experimental model (whisper_tech_interviews_lora/phase1_10k/checkpoint-375)
across the 200 held-out recordings.

CONFIGURATIONS EVALUATED:
- Config A: Current Baseline (Greedy search, repetition_penalty=1.0, no_repeat_ngram_size=0)
- Config B: N-Gram Anti-Repetition (no_repeat_ngram_size=3, repetition_penalty=1.0)
- Config C: Logit Repetition Penalty (repetition_penalty=1.1, no_repeat_ngram_size=0)
- Config D: Combined Guardrail (no_repeat_ngram_size=3, repetition_penalty=1.1)

SAFETY & ISOLATION GUARANTEES:
- Strictly read-only inference.
- No model checkpoints or weights modified.
- No training executed.
- Port 8003 (production ASR) and all other application services are untouched.
- Output written to a new, non-existing report file.
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

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

BASE_MODEL_ID = "openai/whisper-base.en"
DEFAULT_MODEL_DIR = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora", "phase1_10k", "checkpoint-375"
)
GLOSSARY_PATH = os.path.join(SCRIPT_DIR, "tech_glossary.json")
DEFAULT_OUTPUT_JSON = os.path.join(SCRIPT_DIR, "decoding_experiment_results.json")
DATASET_ID = "WhissleAI/Meta_STT_EN-IN_Tech_Interviews"

# Trailing demographic/annotation tag stripper
ANNOTATION_SUFFIX_REGEX = re.compile(
    r'(?:\s+\b(?:AGE|GER|EMOTION|INTENT)_[A-Za-z0-9_]+\b)+\s*$'
)


def clean_transcript(raw_text: str) -> str:
    """Strips trailing metadata annotation tags while preserving spoken words."""
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
    """Loads and normalizes all domain terms from tech_glossary.json."""
    if not os.path.exists(path):
        print(f"  [WARN] Glossary file not found at {path}, using default subset.")
        raw_terms = ["algorithm", "api", "database", "python", "javascript", "react", "sql"]
    else:
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
def load_heldout_dataset(max_samples: int) -> List[Dict[str, Any]]:
    """Loads held-out validation samples from WhissleAI using streaming=True."""
    print(f"\nStreaming {max_samples} held-out validation samples from {DATASET_ID}...")
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
# Main Orchestrator
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PreMock AI — ASR Repetition-Loop Decoding Experiment"
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default=DEFAULT_MODEL_DIR,
        help=f"Path to Experimental Model B adapter (default: {DEFAULT_MODEL_DIR}).",
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=200,
        help="Number of held-out validation samples to evaluate on (default: 200).",
    )
    parser.add_argument(
        "--output_json",
        type=str,
        default=DEFAULT_OUTPUT_JSON,
        help=f"Destination path for results JSON (default: {DEFAULT_OUTPUT_JSON}).",
    )
    args = parser.parse_args()

    # Safety check: Destination MUST NOT exist
    if os.path.exists(args.output_json):
        print(f"\n[ERROR] Output destination already exists: {args.output_json}")
        print("        To prevent accidental overwriting, execution has been stopped.")
        sys.exit(1)

    print("=" * 76)
    print("PreMock AI — ASR Repetition-Loop Decoding Experiment")
    print("=" * 76)
    print(f"Experimental Model     : {args.model_dir}")
    print(f"Held-out Sample Count  : {args.num_samples}")
    print(f"Output Report File     : {args.output_json}")
    print("=" * 76)

    # 1. Setup normalizer and glossary
    normalizer = BasicTextNormalizer()
    glossary = load_normalized_glossary(GLOSSARY_PATH, normalizer)
    print(f"Loaded and normalized {len(glossary)} unique domain terms from technical glossary.")

    wer_metric = ev.load("wer")
    cer_metric = ev.load("cer")

    # 2. Load Evaluation Data
    eval_records = load_heldout_dataset(args.num_samples)
    references = [r["reference"] for r in eval_records]
    norm_refs = [normalizer(r) for r in references]
    total_audio_sec = sum(r["duration"] for r in eval_records)

    # 3. Load Model Once
    print(f"\nLoading processor: {BASE_MODEL_ID}")
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")

    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_map = "auto" if device == "cuda" else None

    print(f"Loading base model: {BASE_MODEL_ID} (8-bit quantization)")
    model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_cfg if device == "cuda" else None,
        device_map=device_map,
    )
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []

    print(f"Attaching LoRA adapter from: {args.model_dir}")
    model = PeftModel.from_pretrained(model, args.model_dir)
    model.eval()

    # Determine input dtype
    target_dtype = model.get_base_model().model.encoder.conv1.weight.dtype

    # Define Configurations
    configs = [
        {
            "id": "config_a",
            "name": "Config A: Baseline (Greedy, rep_pen=1.0, no_repeat=0)",
            "gen_kwargs": {"max_length": 225, "num_beams": 1, "do_sample": False},
        },
        {
            "id": "config_b",
            "name": "Config B: N-Gram Guard (no_repeat_ngram_size=3)",
            "gen_kwargs": {"max_length": 225, "num_beams": 1, "do_sample": False, "no_repeat_ngram_size": 3},
        },
        {
            "id": "config_c",
            "name": "Config C: Repetition Penalty (repetition_penalty=1.1)",
            "gen_kwargs": {"max_length": 225, "num_beams": 1, "do_sample": False, "repetition_penalty": 1.1},
        },
        {
            "id": "config_d",
            "name": "Config D: Combined Guard (no_repeat_ngram_size=3 + rep_pen=1.1)",
            "gen_kwargs": {"max_length": 225, "num_beams": 1, "do_sample": False, "no_repeat_ngram_size": 3, "repetition_penalty": 1.1},
        },
    ]

    # Store results per config
    results_per_config = {
        cfg["id"]: {
            "name": cfg["name"],
            "gen_kwargs": cfg["gen_kwargs"],
            "raw_predictions": [],
            "norm_predictions": [],
            "latencies_ms": [],
            "repetition_flags": [],
        }
        for cfg in configs
    }

    print(f"\n>>> Running multi-configuration inference across {len(eval_records)} held-out utterances...")
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

            # Generate under each configuration
            for cfg in configs:
                c_id = cfg["id"]
                kwargs = cfg["gen_kwargs"]

                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                t0 = time.perf_counter()

                pred_ids = model.generate(input_features, **kwargs)
                transcription = processor.batch_decode(pred_ids, skip_special_tokens=True)[0]

                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                elapsed_ms = (time.perf_counter() - t0) * 1000.0

                is_rep, rep_reason = detect_repetition_failure(transcription)

                results_per_config[c_id]["raw_predictions"].append(transcription)
                results_per_config[c_id]["norm_predictions"].append(normalizer(transcription))
                results_per_config[c_id]["latencies_ms"].append(round(elapsed_ms, 2))
                results_per_config[c_id]["repetition_flags"].append({
                    "is_failure": is_rep,
                    "reason": rep_reason
                })

            if (s_idx + 1) % 25 == 0 or (s_idx + 1) == len(eval_records):
                print(f"  Evaluated {s_idx + 1} / {len(eval_records)} utterances ({((time.time() - start_eval_time)):.1f}s elapsed)...")

    # Free GPU
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 4. Compute Aggregate Metrics for each configuration
    summary_metrics = {}
    print("\n" + "=" * 76)
    print("COMPARATIVE DECODING EXPERIMENT RESULTS")
    print("=" * 76)
    print(f"{'Configuration':<32} | {'Norm WER':<10} | {'Raw WER':<10} | {'Norm CER':<10} | {'Tech Rec':<10} | {'Rep Fails':<10} | {'Mean ms':<10} | {'RTF':<8}")
    print("-" * 110)

    for cfg in configs:
        c_id = cfg["id"]
        data = results_per_config[c_id]

        preds_raw = data["raw_predictions"]
        preds_norm = data["norm_predictions"]
        lats = data["latencies_ms"]
        rep_flags = data["repetition_flags"]

        raw_wer = wer_metric.compute(predictions=preds_raw, references=references) * 100.0
        norm_wer = wer_metric.compute(predictions=preds_norm, references=norm_refs) * 100.0
        norm_cer = cer_metric.compute(predictions=preds_norm, references=norm_refs) * 100.0

        tech_res = evaluate_technical_terms(references, preds_raw, normalizer, glossary)
        rep_fail_count = sum(1 for f in rep_flags if f["is_failure"])

        total_infer_sec = sum(lats) / 1000.0
        rtf = total_infer_sec / total_audio_sec if total_audio_sec > 0 else 0.0

        summary_metrics[c_id] = {
            "name": data["name"],
            "gen_kwargs": data["gen_kwargs"],
            "norm_wer_pct": round(norm_wer, 2),
            "raw_wer_pct": round(raw_wer, 2),
            "norm_cer_pct": round(norm_cer, 2),
            "tech_recall_pct": tech_res["tech_term_recall_pct"],
            "tech_matched": tech_res["correctly_transcribed"],
            "tech_total": tech_res["total_in_references"],
            "repetition_failures_count": rep_fail_count,
            "repetition_failure_rate_pct": round(rep_fail_count / len(eval_records) * 100.0, 2),
            "mean_latency_ms": round(float(np.mean(lats)), 2),
            "median_latency_ms": round(float(np.median(lats)), 2),
            "total_inference_sec": round(total_infer_sec, 2),
            "rtf": round(rtf, 4),
        }

        print(f"{cfg['id'].upper():<32} | {norm_wer:6.2f}%    | {raw_wer:6.2f}%    | {norm_cer:6.2f}%    | {tech_res['tech_term_recall_pct']:6.2f}%    | {rep_fail_count:2d}/200     | {np.mean(lats):7.1f}ms  | {rtf:6.4f}")

    print("=" * 110)

    # 5. Detail Inspection on Known Outlier Cases (Sample 49 and Sample 119)
    # Note: 0-indexed: Sample 49 is idx 48; Sample 119 is idx 118
    sample_49_idx = 48
    sample_119_idx = 118

    case_studies = {
        "sample_49": {
            "index": 49,
            "reference": eval_records[sample_49_idx]["reference"],
            "outputs": {
                c_id: results_per_config[c_id]["raw_predictions"][sample_49_idx]
                for c_id in ["config_a", "config_b", "config_c", "config_d"]
            }
        },
        "sample_119": {
            "index": 119,
            "reference": eval_records[sample_119_idx]["reference"],
            "outputs": {
                c_id: results_per_config[c_id]["raw_predictions"][sample_119_idx]
                for c_id in ["config_a", "config_b", "config_c", "config_d"]
            }
        }
    }

    print("\nKNOWN REPETITION CASE STUDY (Sample 119):")
    print(f"  REFERENCE: \"{case_studies['sample_119']['reference']}\"")
    for c_id, out_txt in case_studies['sample_119']['outputs'].items():
        print(f"  {c_id.upper()}: \"{out_txt[:120]}...\"")

    # 6. Save Complete Payload to JSON
    per_sample_records = []
    for i in range(len(eval_records)):
        rec = eval_records[i]
        per_sample_records.append({
            "index": i + 1,
            "source_file": rec["source_file"],
            "duration_sec": round(rec["duration"], 3),
            "reference_raw": rec["reference"],
            "reference_norm": norm_refs[i],
            "predictions_raw": {
                c_id: results_per_config[c_id]["raw_predictions"][i] for c_id in results_per_config
            },
            "predictions_norm": {
                c_id: results_per_config[c_id]["norm_predictions"][i] for c_id in results_per_config
            },
            "latencies_ms": {
                c_id: results_per_config[c_id]["latencies_ms"][i] for c_id in results_per_config
            },
            "repetition_flags": {
                c_id: results_per_config[c_id]["repetition_flags"][i] for c_id in results_per_config
            },
        })

    payload = {
        "metadata": {
            "experiment": "decoding_repetition_penalty_comparison",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model_evaluated": args.model_dir,
            "num_samples_evaluated": len(eval_records),
            "total_audio_duration_seconds": round(total_audio_sec, 2),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
        "summary_metrics": summary_metrics,
        "case_studies": case_studies,
        "per_sample_results": per_sample_records,
    }

    # Final check before writing
    if os.path.exists(args.output_json):
        print(f"\n[FATAL] Output file was created during execution: {args.output_json}. Aborting write.")
        sys.exit(1)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\n[SUCCESS] Decoding experiment results saved safely to:")
    print(f"  {args.output_json}")
    print("\n[COMPLETE] Evaluation completed without altering any deployed services or models.")


if __name__ == "__main__":
    main()
