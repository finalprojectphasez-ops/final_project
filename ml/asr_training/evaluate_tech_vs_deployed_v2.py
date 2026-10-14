"""
evaluate_tech_vs_deployed_v2.py

Independent, Corrected Comparative Evaluation for PreMock AI ASR:
- Model A (Deployed): ml/asr_model/whisper_indian_accent_lora_20k/checkpoint-1200
- Model B (Experimental): ml/asr_model/whisper_tech_interviews_lora/phase1_10k/checkpoint-375
- Evaluation Data:
    200 held-out validation samples from WhissleAI/Meta_STT_EN-IN_Tech_Interviews

KEY V2 IMPROVEMENTS & CORRECTIONS:
1. Technical Glossary Normalization:
   Normalizes all 222 glossary terms before matching, ensuring multi-word,
   hyphenated, and compound terms (e.g., 'b-tree', 'ci/cd', 'tcp/ip') match
   normalized reference transcripts.
2. Capitalized-Token Recall Metric:
   Explicitly labeled as 'Capitalized-Token Recall (%)' (not claimed as true NLP NER).
   Uses sentence-boundary awareness to filter sentence-initial capitalizations while
   preserving mid-sentence entities and acronyms (e.g., Python, Docker, AWS, SQL).
3. Explicit CUDA Synchronization:
   Wraps per-utterance inference with torch.cuda.synchronize() for microsecond-accurate
   latency and real-time factor (RTF) benchmarking.
4. Paired Statistical Significance & Uncertainty:
   - Wilcoxon signed-rank test on per-utterance normalized WER and CER deltas.
   - 1,000-iteration paired bootstrap 95% Confidence Intervals (CI) for corpus-level
     normalized WER delta and normalized CER delta.
   - Win / Tie / Loss counts and statistical limitations documentation.
5. Strictly Preserved Identical Conditions:
   - Same 200 held-out audio recordings and ground-truth references.
   - Same 8-bit quantized base model (openai/whisper-base.en).
   - Same greedy decoding settings (max_length=225, num_beams=1, do_sample=False).
6. Safe, Non-Overwriting Persistence:
   - Writes detailed per-utterance results and statistical summaries to a designated
     JSON file.
   - Validates that the destination file does not exist before execution; refuses
     to overwrite any existing file.
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
import jiwer
import scipy.stats as st

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
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora", "phase1_10k", "checkpoint-375"
)
GLOSSARY_PATH = os.path.join(SCRIPT_DIR, "tech_glossary.json")
DEFAULT_OUTPUT_JSON = os.path.join(SCRIPT_DIR, "eval_results_v2_200samples.json")
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
# Technical Term & Capitalized Token Scoring
# ---------------------------------------------------------------------------
def load_normalized_glossary(path: str, normalizer: BasicTextNormalizer) -> List[str]:
    """
    Loads domain terms from tech_glossary.json and normalizes every term using
    BasicTextNormalizer.

    This ensures hyphenated terms ('b-tree', 'ci/cd', 'tcp/ip') and multi-word
    phrases match the normalized reference and prediction strings.
    Terms are sorted descending by word count and length so longer compound phrases
    match before shorter constituent substrings.
    """
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

    # Sort descending by word count, then character length
    sorted_terms = sorted(
        list(normalized_set),
        key=lambda x: (len(x.split()), len(x)),
        reverse=True
    )
    return sorted_terms


def evaluate_technical_terms(
    references: List[str],
    predictions: List[str],
    normalizer: BasicTextNormalizer,
    glossary: List[str],
) -> Dict[str, Any]:
    """
    Evaluates technical-term recall:
    Identifies normalized domain terms from the glossary present in reference
    transcripts and checks whether each term is preserved in the model prediction.

    Recall (%) = (matched_terms / total_in_references) * 100.0
    """
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


def evaluate_capitalized_token_recall(
    references: List[str],
    predictions: List[str],
    normalizer: BasicTextNormalizer,
) -> Dict[str, Any]:
    """
    Evaluates Capitalized-Token Recall (%):
    Detects capitalized tokens that appear mid-sentence or multi-letter uppercase
    acronyms (e.g., Python, Docker, React, AWS, SQL, HTTP) across reference
    transcripts and checks for their preservation in model predictions.

    NOTE ON STATISTICAL LIMITATION:
    This is a rule-based capitalization and token-heuristic metric, NOT a trained
    NLP Named Entity Recognizer (NER). It measures the model's ability to retain
    specifically capitalized technical tokens, tools, and acronyms.
    """
    total_cap_tokens = 0
    matched_cap_tokens = 0

    COMMON_SENTENCE_STARTERS = {
        "the", "a", "an", "this", "that", "it", "so", "and", "or", "but", "in", "on", "at",
        "to", "for", "with", "is", "are", "was", "were", "we", "i", "you", "they", "he",
        "she", "there", "here", "when", "if", "as", "by", "from", "then", "now", "well"
    }

    for ref, pred in zip(references, predictions):
        norm_pred = normalizer(pred)
        # Split into sentences by punctuation
        sentences = re.split(r'[.!?]+', ref)

        for sent in sentences:
            words = sent.strip().split()
            for i, w in enumerate(words):
                clean_w = re.sub(r'[^A-Za-z0-9]', '', w)
                if not clean_w:
                    continue

                is_acronym = len(clean_w) >= 2 and clean_w.isupper()
                is_capitalized = clean_w[0].isupper()

                # Filter out sentence-initial words unless they are acronyms
                if i == 0 and not is_acronym:
                    if clean_w.lower() in COMMON_SENTENCE_STARTERS or not is_acronym:
                        continue

                if is_capitalized or is_acronym:
                    total_cap_tokens += 1
                    pattern = r'\b' + re.escape(clean_w.lower()) + r'\b'
                    if re.search(pattern, norm_pred):
                        matched_cap_tokens += 1

    accuracy = (matched_cap_tokens / total_cap_tokens * 100.0) if total_cap_tokens > 0 else 100.0
    return {
        "total_capitalized_tokens": total_cap_tokens,
        "matched_capitalized_tokens": matched_cap_tokens,
        "capitalized_token_recall_pct": round(accuracy, 2),
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
    """
    Runs inference across audio records and measures latency with explicit
    torch.cuda.synchronize() boundaries.
    """
    predictions = []
    latencies = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    target_dtype = get_model_input_dtype(model)

    with torch.no_grad():
        for item in audio_records:
            arr = item["audio"]["array"]
            sr = item["audio"]["sampling_rate"]

            if torch.cuda.is_available():
                torch.cuda.synchronize()
            start_t = time.perf_counter()

            input_features = processor.feature_extractor(
                arr, sampling_rate=sr, return_tensors="pt"
            ).input_features
            if device == "cuda":
                input_features = input_features.to(device=device, dtype=target_dtype)
            else:
                input_features = input_features.to(dtype=target_dtype)

            # Generate tokens
            pred_ids = model.generate(
                input_features,
                max_length=225,
                num_beams=1,
                do_sample=False,
            )
            transcription = processor.batch_decode(pred_ids, skip_special_tokens=True)[0]

            if torch.cuda.is_available():
                torch.cuda.synchronize()
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
# Paired Statistical Testing & Bootstrap Uncertainty
# ---------------------------------------------------------------------------
def compute_paired_statistics(
    norm_refs: List[str],
    norm_preds_a: List[str],
    norm_preds_b: List[str],
    num_bootstrap: int = 1000,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Calculates paired per-recording error deltas, Wilcoxon signed-rank test,
    win/tie/loss counts, and 1,000-sample paired bootstrap 95% Confidence Intervals
    for corpus-level Normalized WER and CER deltas.
    """
    np.random.seed(random_seed)
    n_samples = len(norm_refs)

    # 1. Per-sample stats via jiwer
    words_a = [jiwer.process_words(r, p) for r, p in zip(norm_refs, norm_preds_a)]
    words_b = [jiwer.process_words(r, p) for r, p in zip(norm_refs, norm_preds_b)]

    chars_a = [jiwer.process_characters(r, p) for r, p in zip(norm_refs, norm_preds_a)]
    chars_b = [jiwer.process_characters(r, p) for r, p in zip(norm_refs, norm_preds_b)]

    per_sample_wer_a = np.array([
        (w.substitutions + w.deletions + w.insertions) / max(1, w.hits + w.substitutions + w.deletions)
        for w in words_a
    ])
    per_sample_wer_b = np.array([
        (w.substitutions + w.deletions + w.insertions) / max(1, w.hits + w.substitutions + w.deletions)
        for w in words_b
    ])

    per_sample_cer_a = np.array([
        (c.substitutions + c.deletions + c.insertions) / max(1, c.hits + c.substitutions + c.deletions)
        for c in chars_a
    ])
    per_sample_cer_b = np.array([
        (c.substitutions + c.deletions + c.insertions) / max(1, c.hits + c.substitutions + c.deletions)
        for c in chars_b
    ])

    # Deltas: Model A - Model B (Positive delta means Model B has lower error -> Model B Win)
    delta_wer = per_sample_wer_a - per_sample_wer_b
    delta_cer = per_sample_cer_a - per_sample_cer_b

    wer_wins = int(np.sum(delta_wer > 1e-4))
    wer_ties = int(np.sum(np.abs(delta_wer) <= 1e-4))
    wer_losses = int(np.sum(delta_wer < -1e-4))

    cer_wins = int(np.sum(delta_cer > 1e-4))
    cer_ties = int(np.sum(np.abs(delta_cer) <= 1e-4))
    cer_losses = int(np.sum(delta_cer < -1e-4))

    # 2. Wilcoxon Signed-Rank Test on non-zero differences
    diff_wer_nonzero = delta_wer[np.abs(delta_wer) > 1e-4]
    if len(diff_wer_nonzero) > 0:
        res_wilcoxon_wer = st.wilcoxon(diff_wer_nonzero, alternative="two-sided")
        wilcoxon_stat_wer = float(res_wilcoxon_wer.statistic)
        wilcoxon_p_wer = float(res_wilcoxon_wer.pvalue)
    else:
        wilcoxon_stat_wer = 0.0
        wilcoxon_p_wer = 1.0

    diff_cer_nonzero = delta_cer[np.abs(delta_cer) > 1e-4]
    if len(diff_cer_nonzero) > 0:
        res_wilcoxon_cer = st.wilcoxon(diff_cer_nonzero, alternative="two-sided")
        wilcoxon_stat_cer = float(res_wilcoxon_cer.statistic)
        wilcoxon_p_cer = float(res_wilcoxon_cer.pvalue)
    else:
        wilcoxon_stat_cer = 0.0
        wilcoxon_p_cer = 1.0

    # 3. Paired Bootstrap 95% Confidence Intervals for Corpus-Level Metric Delta
    err_w_a = np.array([w.substitutions + w.deletions + w.insertions for w in words_a])
    ref_w_len = np.array([max(1, w.hits + w.substitutions + w.deletions) for w in words_a])
    err_w_b = np.array([w.substitutions + w.deletions + w.insertions for w in words_b])

    err_c_a = np.array([c.substitutions + c.deletions + c.insertions for c in chars_a])
    ref_c_len = np.array([max(1, c.hits + c.substitutions + c.deletions) for c in chars_a])
    err_c_b = np.array([c.substitutions + c.deletions + c.insertions for c in chars_b])

    boot_delta_wer = []
    boot_delta_cer = []

    for _ in range(num_bootstrap):
        idx = np.random.choice(n_samples, size=n_samples, replace=True)
        # Corpus-level WER = sum(errors) / sum(ref_tokens)
        corpus_wer_a = np.sum(err_w_a[idx]) / np.sum(ref_w_len[idx]) * 100.0
        corpus_wer_b = np.sum(err_w_b[idx]) / np.sum(ref_w_len[idx]) * 100.0
        boot_delta_wer.append(corpus_wer_a - corpus_wer_b)

        corpus_cer_a = np.sum(err_c_a[idx]) / np.sum(ref_c_len[idx]) * 100.0
        corpus_cer_b = np.sum(err_c_b[idx]) / np.sum(ref_c_len[idx]) * 100.0
        boot_delta_cer.append(corpus_cer_a - corpus_cer_b)

    ci_wer_low, ci_wer_high = np.percentile(boot_delta_wer, [2.5, 97.5])
    ci_cer_low, ci_cer_high = np.percentile(boot_delta_cer, [2.5, 97.5])

    return {
        "per_sample_wer_a": [round(float(v), 4) for v in per_sample_wer_a],
        "per_sample_wer_b": [round(float(v), 4) for v in per_sample_wer_b],
        "per_sample_cer_a": [round(float(v), 4) for v in per_sample_cer_a],
        "per_sample_cer_b": [round(float(v), 4) for v in per_sample_cer_b],
        "normalized_wer_comparison": {
            "model_b_wins": wer_wins,
            "ties": wer_ties,
            "model_b_losses": wer_losses,
            "wilcoxon_signed_rank_stat": round(wilcoxon_stat_wer, 2),
            "wilcoxon_p_value": float(f"{wilcoxon_p_wer:.6e}"),
            "statistically_significant_p05": bool(wilcoxon_p_wer < 0.05),
            "bootstrap_corpus_delta_mean_pct": round(float(np.mean(boot_delta_wer)), 2),
            "bootstrap_corpus_delta_95_ci_pct": [round(float(ci_wer_low), 2), round(float(ci_wer_high), 2)],
        },
        "normalized_cer_comparison": {
            "model_b_wins": cer_wins,
            "ties": cer_ties,
            "model_b_losses": cer_losses,
            "wilcoxon_signed_rank_stat": round(wilcoxon_stat_cer, 2),
            "wilcoxon_p_value": float(f"{wilcoxon_p_cer:.6e}"),
            "statistically_significant_p05": bool(wilcoxon_p_cer < 0.05),
            "bootstrap_corpus_delta_mean_pct": round(float(np.mean(boot_delta_cer)), 2),
            "bootstrap_corpus_delta_95_ci_pct": [round(float(ci_cer_low), 2), round(float(ci_cer_high), 2)],
        },
        "statistical_limitations": (
            "1. Sample size N=200 reflects a held-out sample of interview recordings; wider multi-speaker "
            "variance requires ongoing multi-domain testing. 2. Non-parametric paired tests (Wilcoxon) and "
            "bootstrap resamples assume identically distributed independent recordings. 3. Capitalized-token "
            "recall is a token-level heuristic and does not substitute for full statistical NLP Named Entity Recognition."
        ),
    }


# ---------------------------------------------------------------------------
# Main Evaluation Orchestrator
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PreMock AI — ASR Corrected Comparative Evaluation v2"
    )
    parser.add_argument(
        "--num_samples",
        type=int,
        default=200,
        help="Number of held-out validation samples to evaluate on (default: 200).",
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

    print("=" * 74)
    print("PreMock AI — ASR Corrected Independent Comparative Evaluation (v2)")
    print("=" * 74)
    print(f"Model A (Deployed)     : {args.model_a}")
    print(f"Model B (Experimental) : {args.model_b}")
    print(f"Held-out Sample Count  : {args.num_samples}")
    print(f"Output JSON Path       : {args.output_json}")
    print("=" * 74)

    # 1. Normalizer, Glossary & Metrics
    normalizer = BasicTextNormalizer()
    glossary = load_normalized_glossary(GLOSSARY_PATH, normalizer)
    print(f"Loaded and normalized {len(glossary)} unique domain terms from technical glossary.")

    wer_metric = ev.load("wer")
    cer_metric = ev.load("cer")

    # 2. Load Evaluation Data (In-Memory List)
    eval_records = load_heldout_dataset(args.num_samples)
    references = [r["reference"] for r in eval_records]
    norm_refs = [normalizer(r) for r in references]
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
        norm_preds = [normalizer(p) for p in preds]

        raw_wer = wer_metric.compute(predictions=preds, references=references) * 100.0
        norm_wer = wer_metric.compute(predictions=norm_preds, references=norm_refs) * 100.0
        norm_cer = cer_metric.compute(predictions=norm_preds, references=norm_refs) * 100.0

        tech_results = evaluate_technical_terms(references, preds, normalizer, glossary)
        cap_results = evaluate_capitalized_token_recall(references, preds, normalizer)

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
            "frequent_missed_tech": tech_results["frequent_misses"],
            "cap_token_recall_pct": cap_results["capitalized_token_recall_pct"],
            "cap_tokens_total": cap_results["total_capitalized_tokens"],
            "cap_tokens_matched": cap_results["matched_capitalized_tokens"],
            "mean_latency_ms": round(float(np.mean(latencies)), 2),
            "median_latency_ms": round(float(np.median(latencies)), 2),
            "total_inference_sec": round(total_infer_sec, 2),
            "rtf": round(rtf, 4),
            "raw_predictions": preds,
            "norm_predictions": norm_preds,
            "latencies_ms": [round(l, 2) for l in latencies],
        }

    # Evaluate Model A (Deployed)
    res_a = evaluate_model_pipeline("Model A (Deployed 20k)", args.model_a)

    # Evaluate Model B (Experimental)
    if not os.path.exists(args.model_b):
        print(f"\n[ERROR] Model B adapter not found at {args.model_b}.")
        sys.exit(1)
    res_b = evaluate_model_pipeline("Model B (Experimental Tech Interviews)", args.model_b)

    # 3. Compute Paired Statistical Significance & Bootstrap Uncertainty
    print("\n>>> Computing Paired Statistical Significance & 1,000 Bootstrap CIs...")
    stat_results = compute_paired_statistics(
        norm_refs=norm_refs,
        norm_preds_a=res_a["norm_predictions"],
        norm_preds_b=res_b["norm_predictions"],
        num_bootstrap=1000,
        random_seed=42,
    )

    # 4. Print Summary Table
    print("\n" + "=" * 76)
    print("COMPARATIVE EVALUATION RESULTS SUMMARY (v2)")
    print("=" * 76)
    print(f"{'Metric':<34} | {'Model A (Deployed)':<18} | {'Model B (Experimental)':<18}")
    print("-" * 76)
    print(f"{'Normalized WER (%)':<34} | {res_a['norm_wer_pct']:<18} | {res_b['norm_wer_pct']:<18}")
    print(f"{'Raw WER (%)':<34} | {res_a['raw_wer_pct']:<18} | {res_b['raw_wer_pct']:<18}")
    print(f"{'Normalized CER (%)':<34} | {res_a['norm_cer_pct']:<18} | {res_b['norm_cer_pct']:<18}")
    print(f"{'Tech-Term Recall (%) [Normalized]':<34} | {res_a['tech_recall_pct']:<18} | {res_b['tech_recall_pct']:<18}")
    print(f"{'Capitalized-Token Recall (%)':<34} | {res_a['cap_token_recall_pct']:<18} | {res_b['cap_token_recall_pct']:<18}")
    print(f"{'Mean Latency (ms)':<34} | {res_a['mean_latency_ms']:<18} | {res_b['mean_latency_ms']:<18}")
    print(f"{'Median Latency (ms)':<34} | {res_a['median_latency_ms']:<18} | {res_b['median_latency_ms']:<18}")
    print(f"{'Real-Time Factor (RTF)':<34} | {res_a['rtf']:<18} | {res_b['rtf']:<18}")
    print("=" * 76)

    print("\nPAIRED STATISTICAL SIGNIFICANCE (Model A vs Model B across 200 recordings):")
    wer_comp = stat_results["normalized_wer_comparison"]
    cer_comp = stat_results["normalized_cer_comparison"]
    print(f"  Normalized WER: Model B Wins: {wer_comp['model_b_wins']} | Ties: {wer_comp['ties']} | Losses: {wer_comp['model_b_losses']}")
    print(f"    Wilcoxon Signed-Rank Test : W = {wer_comp['wilcoxon_signed_rank_stat']}, p = {wer_comp['wilcoxon_p_value']}")
    print(f"    Statistically Significant : {wer_comp['statistically_significant_p05']} (alpha = 0.05)")
    print(f"    Bootstrap 95% CI (Delta)  : [{wer_comp['bootstrap_corpus_delta_95_ci_pct'][0]}%, {wer_comp['bootstrap_corpus_delta_95_ci_pct'][1]}%] (Mean: {wer_comp['bootstrap_corpus_delta_mean_pct']}%)")
    print(f"  Normalized CER: Model B Wins: {cer_comp['model_b_wins']} | Ties: {cer_comp['ties']} | Losses: {cer_comp['model_b_losses']}")
    print(f"    Wilcoxon Signed-Rank Test : W = {cer_comp['wilcoxon_signed_rank_stat']}, p = {cer_comp['wilcoxon_p_value']}")
    print(f"    Statistically Significant : {cer_comp['statistically_significant_p05']} (alpha = 0.05)")
    print(f"    Bootstrap 95% CI (Delta)  : [{cer_comp['bootstrap_corpus_delta_95_ci_pct'][0]}%, {cer_comp['bootstrap_corpus_delta_95_ci_pct'][1]}%] (Mean: {cer_comp['bootstrap_corpus_delta_mean_pct']}%)")

    # 5. Assemble and Save Results JSON
    per_recording_data = []
    for i in range(len(eval_records)):
        rec = eval_records[i]
        per_recording_data.append({
            "index": i + 1,
            "source_file": rec["source_file"],
            "duration_sec": round(rec["duration"], 3),
            "reference_raw": rec["reference"],
            "reference_norm": norm_refs[i],
            "model_a_pred_raw": res_a["raw_predictions"][i],
            "model_a_pred_norm": res_a["norm_predictions"][i],
            "model_b_pred_raw": res_b["raw_predictions"][i],
            "model_b_pred_norm": res_b["norm_predictions"][i],
            "sample_wer_norm_model_a": stat_results["per_sample_wer_a"][i],
            "sample_wer_norm_model_b": stat_results["per_sample_wer_b"][i],
            "sample_cer_norm_model_a": stat_results["per_sample_cer_a"][i],
            "sample_cer_norm_model_b": stat_results["per_sample_cer_b"][i],
            "latency_ms_model_a": res_a["latencies_ms"][i],
            "latency_ms_model_b": res_b["latencies_ms"][i],
        })

    final_payload = {
        "metadata": {
            "evaluation_version": "v2_independent",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "dataset": DATASET_ID,
            "split": "validation",
            "num_samples_evaluated": len(eval_records),
            "total_audio_duration_seconds": round(total_audio_sec, 2),
            "model_a_adapter": args.model_a,
            "model_b_adapter": args.model_b,
            "base_model": BASE_MODEL_ID,
            "quantization": "8-bit",
            "decoding": "greedy (num_beams=1, max_length=225)",
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        },
        "summary_metrics": {
            "model_a": {
                "name": res_a["model_name"],
                "norm_wer_pct": res_a["norm_wer_pct"],
                "raw_wer_pct": res_a["raw_wer_pct"],
                "norm_cer_pct": res_a["norm_cer_pct"],
                "tech_term_recall_pct": res_a["tech_recall_pct"],
                "tech_matched": res_a["tech_matched"],
                "tech_total": res_a["tech_total"],
                "capitalized_token_recall_pct": res_a["cap_token_recall_pct"],
                "capitalized_matched": res_a["cap_tokens_matched"],
                "capitalized_total": res_a["cap_tokens_total"],
                "mean_latency_ms": res_a["mean_latency_ms"],
                "median_latency_ms": res_a["median_latency_ms"],
                "total_inference_sec": res_a["total_inference_sec"],
                "rtf": res_a["rtf"],
            },
            "model_b": {
                "name": res_b["model_name"],
                "norm_wer_pct": res_b["norm_wer_pct"],
                "raw_wer_pct": res_b["raw_wer_pct"],
                "norm_cer_pct": res_b["norm_cer_pct"],
                "tech_term_recall_pct": res_b["tech_recall_pct"],
                "tech_matched": res_b["tech_matched"],
                "tech_total": res_b["tech_total"],
                "capitalized_token_recall_pct": res_b["cap_token_recall_pct"],
                "capitalized_matched": res_b["cap_tokens_matched"],
                "capitalized_total": res_b["cap_tokens_total"],
                "mean_latency_ms": res_b["mean_latency_ms"],
                "median_latency_ms": res_b["median_latency_ms"],
                "total_inference_sec": res_b["total_inference_sec"],
                "rtf": res_b["rtf"],
            },
        },
        "statistical_significance": {
            "normalized_wer_comparison": wer_comp,
            "normalized_cer_comparison": cer_comp,
            "statistical_limitations": stat_results["statistical_limitations"],
        },
        "per_recording_results": per_recording_data,
    }

    # Re-verify destination before writing
    if os.path.exists(args.output_json):
        print(f"\n[FATAL] Output file was created during execution: {args.output_json}. Aborting write.")
        sys.exit(1)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)

    print(f"\n[SUCCESS] Independent evaluation results saved safely to:")
    print(f"  {args.output_json}")
    print("\n[COMPLETE] Evaluation completed without altering any deployed services or models.")


if __name__ == "__main__":
    main()
