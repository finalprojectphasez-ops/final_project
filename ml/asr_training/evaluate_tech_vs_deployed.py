"""
evaluate_tech_vs_deployed.py

Comparative Evaluation for PreMock AI ASR:
- Model A (Deployed): ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200
- Model B (Experimental): ml/asr_model/whisper_tech_interviews_lora
- Evaluation Data:
    1. Held-out validation stream from WhissleAI/Meta_STT_EN-IN_Tech_Interviews
    2. Reference test WAV files in ml/asr_service/

Reported Metrics:
- Word Error Rate (WER) [Raw and Normalized]
- Character Error Rate (CER) [Normalized]
- Technical-term Accuracy / Recall (evaluated against ml/asr_training/tech_glossary.json)
- Proper-noun Accuracy
- Inference Latency (Mean ms, Median ms, and Real-Time Factor)

SAFETY & ISOLATION GUARANTEES:
- Pure read-only inference.
- Does NOT touch, restart, or alter the running ASR service (port 8003).
- Does NOT automatically promote or deploy the experimental model.
- Completely isolated from gaze, emotion, frontend, and backend systems.
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
import soundfile as sf
from datasets import load_dataset
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    BitsAndBytesConfig,
)
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
from peft import PeftModel
import evaluate as ev

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

BASE_MODEL_ID = "openai/whisper-base.en"
DEFAULT_MODEL_A = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200"
)
DEFAULT_MODEL_B = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora"
)
GLOSSARY_PATH = os.path.join(SCRIPT_DIR, "tech_glossary.json")
REF_DIR = os.path.join(PROJECT_ROOT, "ml", "asr_service")
DATASET_ID = "WhissleAI/Meta_STT_EN-IN_Tech_Interviews"

# Annotation tag cleaner
ANNOTATION_SUFFIX_REGEX = re.compile(
    r'(?:\s+\b(?:AGE|GER|EMOTION|INTENT)_[A-Za-z0-9_]+\b)+\s*$'
)


def clean_transcript(raw_text: str) -> str:
    """Strips trailing metadata annotation tags while preserving all spoken words."""
    if not raw_text or not isinstance(raw_text, str):
        return ""
    return ANNOTATION_SUFFIX_REGEX.sub("", raw_text).strip()


# ---------------------------------------------------------------------------
# Technical Term & Proper Noun Scoring
# ---------------------------------------------------------------------------
def load_glossary(path: str) -> List[str]:
    """Loads domain terms from tech_glossary.json."""
    if not os.path.exists(path):
        print(f"  [WARN] Glossary file not found at {path}, using default subset.")
        return ["algorithm", "api", "database", "python", "javascript", "react", "sql"]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [term.lower().strip() for term in data.get("terms", [])]


def evaluate_technical_terms(
    references: List[str],
    predictions: List[str],
    normalizer: BasicTextNormalizer,
    glossary: List[str],
) -> Dict[str, Any]:
    """
    Evaluates technical-term recall:
    Identifies terms from the glossary present in reference transcripts and
    measures how many are preserved in model predictions.
    """
    total_tech_in_ref = 0
    total_tech_in_pred = 0
    matched_tech = 0
    missed_terms = []

    # Sort terms by length descending to match multi-word phrases first
    sorted_glossary = sorted(glossary, key=lambda x: len(x), reverse=True)

    for ref, pred in zip(references, predictions):
        norm_ref = normalizer(ref)
        norm_pred = normalizer(pred)

        ref_terms = []
        for term in sorted_glossary:
            # Word boundary check for term
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


def evaluate_proper_nouns(
    references: List[str],
    predictions: List[str],
    normalizer: BasicTextNormalizer,
) -> Dict[str, Any]:
    """
    Evaluates capitalized proper nouns / named entities present in the references
    (e.g., Python, Docker, React, AWS, MongoDB) to measure preservation.
    """
    total_pn = 0
    matched_pn = 0

    # Common English words that happen to start a sentence
    COMMON_SENTENCE_STARTERS = {
        "the", "a", "an", "this", "that", "it", "so", "and", "or", "but", "in", "on", "at",
        "to", "for", "with", "is", "are", "was", "were", "we", "i", "you", "they", "he", "she"
    }

    for ref, pred in zip(references, predictions):
        words = ref.split()
        norm_pred = normalizer(pred)

        for i, w in enumerate(words):
            clean_w = re.sub(r'[^A-Za-z0-9]', '', w)
            if not clean_w:
                continue

            # Check if capitalized (and not just first word sentence-starter)
            if clean_w[0].isupper():
                if i == 0 and clean_w.lower() in COMMON_SENTENCE_STARTERS:
                    continue
                total_pn += 1
                pattern = r'\b' + re.escape(clean_w.lower()) + r'\b'
                if re.search(pattern, norm_pred):
                    matched_pn += 1

    accuracy = (matched_pn / total_pn * 100.0) if total_pn > 0 else 100.0
    return {
        "total_proper_nouns": total_pn,
        "matched_proper_nouns": matched_pn,
        "proper_noun_accuracy_pct": round(accuracy, 2),
    }


# ---------------------------------------------------------------------------
# Model Loader & Inference Engine
# ---------------------------------------------------------------------------
def load_eval_model(adapter_path: str = None) -> Tuple[Any, Any]:
    """Loads base Whisper-base model in 8-bit, optionally attaching a LoRA adapter."""
    print(f"  Loading processor: {BASE_MODEL_ID}")
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")

    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    device_map = "auto" if device == "cuda" else None

    print(f"  Loading base model: {BASE_MODEL_ID} (8-bit quantization)")
    model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_cfg if device == "cuda" else None,
        device_map=device_map,
    )
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []

    if adapter_path and os.path.exists(adapter_path):
        print(f"  Attaching LoRA adapter from: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
    else:
        if adapter_path:
            print(f"  [WARN] Adapter path not found: {adapter_path}. Running base model.")

    model.eval()
    return model, processor


def get_model_input_dtype(model: Any) -> torch.dtype:
    """Retrieves the expected input dtype from the model's first convolution layer."""
    try:
        base = model.get_base_model() if hasattr(model, "get_base_model") else model
        if hasattr(base, "model") and hasattr(base.model, "encoder") and hasattr(base.model.encoder, "conv1"):
            return base.model.encoder.conv1.weight.dtype
        elif hasattr(base, "encoder") and hasattr(base.encoder, "conv1"):
            return base.encoder.conv1.weight.dtype
    except Exception:
        pass
    return getattr(model, "dtype", torch.float32)


def transcribe_audio_samples(
    model: Any,
    processor: Any,
    audio_records: List[Dict[str, Any]],
) -> Tuple[List[str], List[float]]:
    """Runs inference across audio records and measures latency."""
    predictions = []
    latencies = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    target_dtype = get_model_input_dtype(model)

    with torch.no_grad():
        for item in audio_records:
            arr = item["audio"]["array"]
            sr = item["audio"]["sampling_rate"]

            start_t = time.perf_counter()

            input_features = processor.feature_extractor(
                arr, sampling_rate=sr, return_tensors="pt"
            ).input_features
            if device == "cuda":
                input_features = input_features.to(device=device, dtype=target_dtype)
            else:
                input_features = input_features.to(dtype=target_dtype)

            pred_ids = model.generate(input_features, max_length=225)
            transcription = processor.batch_decode(pred_ids, skip_special_tokens=True)[0]

            elapsed = (time.perf_counter() - start_t) * 1000.0  # ms
            latencies.append(elapsed)
            predictions.append(transcription)

    return predictions, latencies


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
# Main Evaluation Orchestrator
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PreMock AI — ASR Comparative Evaluation (Deployed vs Experimental)"
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=50,
        help="Number of held-out validation samples to evaluate on (default: 50).",
    )
    parser.add_argument(
        "--model_a",
        type=str,
        default=DEFAULT_MODEL_A,
        help=f"Path to Deployed Model A adapter (default: {DEFAULT_MODEL_A}).",
    )
    parser.add_argument(
        "--model_b",
        type=str,
        default=DEFAULT_MODEL_B,
        help=f"Path to Experimental Model B adapter (default: {DEFAULT_MODEL_B}).",
    )
    parser.add_argument(
        "--skip_model_b",
        action="store_true",
        help="Skip Model B evaluation if experimental training has not run yet.",
    )
    parser.add_argument(
        "--smoke_test",
        action="store_true",
        help="Run quick evaluation on 5 samples only.",
    )
    args = parser.parse_args()

    n_samples = 5 if args.smoke_test else args.num_samples

    print("=" * 70)
    print("PreMock AI — ASR Comparative Evaluation")
    print("=" * 70)
    print(f"Model A (Deployed)     : {args.model_a}")
    print(f"Model B (Experimental) : {args.model_b}")
    print(f"Held-out Sample Count  : {n_samples}")
    print("=" * 70)

    # 1. Load Glossary & Metrics
    glossary = load_glossary(GLOSSARY_PATH)
    normalizer = BasicTextNormalizer()
    wer_metric = ev.load("wer")
    cer_metric = ev.load("cer")

    # 2. Load Evaluation Data
    eval_records = load_heldout_dataset(n_samples)
    references = [r["reference"] for r in eval_records]
    total_audio_sec = sum(r["duration"] for r in eval_records)

    def evaluate_model_pipeline(model_name: str, adapter_path: str):
        print(f"\n>>> Evaluating {model_name}...")
        model, processor = load_eval_model(adapter_path)

        preds, latencies = transcribe_audio_samples(model, processor, eval_records)

        # Free GPU memory before evaluating next model
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Compute Metrics
        norm_refs = [normalizer(r) for r in references]
        norm_preds = [normalizer(p) for p in preds]

        raw_wer = wer_metric.compute(predictions=preds, references=references) * 100.0
        norm_wer = wer_metric.compute(predictions=norm_preds, references=norm_refs) * 100.0
        norm_cer = cer_metric.compute(predictions=norm_preds, references=norm_refs) * 100.0

        tech_results = evaluate_technical_terms(references, preds, normalizer, glossary)
        pn_results = evaluate_proper_nouns(references, preds, normalizer)

        total_infer_sec = sum(latencies) / 1000.0
        rtf = total_infer_sec / total_audio_sec if total_audio_sec > 0 else 0.0

        return {
            "model_name": model_name,
            "raw_wer_pct": round(raw_wer, 2),
            "norm_wer_pct": round(norm_wer, 2),
            "norm_cer_pct": round(norm_cer, 2),
            "tech_recall_pct": tech_results["tech_term_recall_pct"],
            "tech_total": tech_results["total_in_references"],
            "tech_matched": tech_results["correctly_transcribed"],
            "pn_accuracy_pct": pn_results["proper_noun_accuracy_pct"],
            "mean_latency_ms": round(float(np.mean(latencies)), 2),
            "median_latency_ms": round(float(np.median(latencies)), 2),
            "rtf": round(rtf, 4),
            "predictions_sample": list(zip(references[:3], preds[:3])),
        }

    # Evaluate Model A (Deployed)
    res_a = evaluate_model_pipeline("Model A (Deployed 20k)", args.model_a)

    # Evaluate Model B (Experimental)
    res_b = None
    if not args.skip_model_b:
        if os.path.exists(args.model_b):
            res_b = evaluate_model_pipeline("Model B (Experimental Tech Interviews)", args.model_b)
        else:
            print(f"\n[INFO] Model B directory not found ({args.model_b}).")
            print("       To evaluate Model B, complete training with train_tech_interviews_lora.py first.")

    # 3. Print Comparative Summary Report
    print("\n" + "=" * 70)
    print("COMPARATIVE EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<32} | {'Model A (Deployed)':<18} | {'Model B (Experimental)':<18}")
    print("-" * 74)
    print(f"{'Normalized WER (%)':<32} | {res_a['norm_wer_pct']:<18} | {res_b['norm_wer_pct'] if res_b else 'Pending Train':<18}")
    print(f"{'Raw WER (%)':<32} | {res_a['raw_wer_pct']:<18} | {res_b['raw_wer_pct'] if res_b else 'Pending Train':<18}")
    print(f"{'Normalized CER (%)':<32} | {res_a['norm_cer_pct']:<18} | {res_b['norm_cer_pct'] if res_b else 'Pending Train':<18}")
    print(f"{'Tech-Term Recall (%)':<32} | {res_a['tech_recall_pct']:<18} | {res_b['tech_recall_pct'] if res_b else 'Pending Train':<18}")
    print(f"{'Proper-Noun Accuracy (%)':<32} | {res_a['pn_accuracy_pct']:<18} | {res_b['pn_accuracy_pct'] if res_b else 'Pending Train':<18}")
    print(f"{'Mean Latency (ms)':<32} | {res_a['mean_latency_ms']:<18} | {res_b['mean_latency_ms'] if res_b else 'Pending Train':<18}")
    print(f"{'Real-Time Factor (RTF)':<32} | {res_a['rtf']:<18} | {res_b['rtf'] if res_b else 'Pending Train':<18}")
    print("=" * 70)

    print("\nSample Transcriptions (Model A):")
    for i, (ref, pred) in enumerate(res_a["predictions_sample"]):
        print(f"  [{i+1}] REF : \"{ref}\"")
        print(f"      PRED: \"{pred}\"")

    print("\n[COMPLETE] Evaluation completed without altering any deployed services or models.")


if __name__ == "__main__":
    main()
