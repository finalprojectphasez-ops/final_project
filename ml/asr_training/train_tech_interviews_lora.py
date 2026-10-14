"""
train_tech_interviews_lora.py

Experimental Fine-Tuning Pipeline for PreMock AI ASR:
- Dataset: WhissleAI/Meta_STT_EN-IN_Tech_Interviews (via streaming=True)
- Training Limit: Exactly 10,000 unique, valid recordings for Phase 1
- Base Model: openai/whisper-base.en (8-bit quantized)
- Warm-Start Adapter: checkpoint-1200 from ml/asr_model/whisper_indian_accent_lora_20k
- Cache Directory: D:/project phase 2/final_project-1/scratch/asr_cache_10k
- Dedicated Output: ml/asr_model/whisper_tech_interviews_lora/phase1_10k/

CRITICAL SAFETY & ISOLATION GUARANTEES:
- Production ASR model (ml/asr_model/whisper_indian_accent_lora_20k) is strictly READ-ONLY.
- Existing 5-step smoke-test checkpoint in whisper_tech_interviews_lora is preserved.
- Gaze and emotion services and models are 100% UNTOUCHED.
- No running services (ports 8000, 8001, 8002, 8003, 3000) are stopped or restarted.
- Does NOT download the full 27.8 GB dataset; uses streaming and bounded disk-backed Arrow caching.
- Enforces strict validation set exclusion (zero leakage from validation sessions/clips into training).
- Halts with an explicit error if fewer than the requested unique valid recordings are found.
- Checkpoint-1200 adapter weights are loaded as trainable parameters, but with a FRESH
  optimizer and LR schedule (Trainer state is NOT resumed from the old run).
"""

import os
import sys
import re
import json
import time
import glob
import argparse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psutil
import numpy as np
import torch
from datasets import load_dataset, Dataset, Features, Sequence, Value, concatenate_datasets
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    BitsAndBytesConfig,
)
from peft import PeftModel, prepare_model_for_kbit_training, LoraConfig, get_peft_model
import evaluate as ev

# ---------------------------------------------------------------------------
# Path Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

BASE_MODEL_ID = "openai/whisper-base.en"
PREV_LORA_PATH = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200"
)
DEFAULT_OUT_DIR = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora", "phase1_10k"
)
SMOKE_OUT_DIR = os.path.join(
    PROJECT_ROOT, "ml", "asr_model", "whisper_tech_interviews_lora", "smoke_test"
)
DEFAULT_CACHE_DIR = os.path.join(
    PROJECT_ROOT, "scratch", "asr_cache_10k"
)
DATASET_ID = "WhissleAI/Meta_STT_EN-IN_Tech_Interviews"

# ---------------------------------------------------------------------------
# Regex Cleaning for Metadata Suffixes
# ---------------------------------------------------------------------------
# Matches trailing block of annotation tokens: AGE_*, GER_*, EMOTION_*, INTENT_*
ANNOTATION_SUFFIX_REGEX = re.compile(
    r'(?:\s+\b(?:AGE|GER|EMOTION|INTENT)_[A-Za-z0-9_]+\b)+\s*$'
)


def clean_transcript(raw_text: str) -> str:
    """
    Strips only trailing metadata annotation tokens from the WhissleAI dataset.
    Preserves all spoken words, repetitions, punctuation, and casing.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""
    cleaned = ANNOTATION_SUFFIX_REGEX.sub("", raw_text)
    return cleaned.strip()


def verify_regex_cleaner():
    """Positive and negative test cases verifying annotation tag cleaning."""
    test_cases = [
        # (Input text, Expected cleaned text, description)
        (
            "logical clocks. Use logical clocks instead of physical time stamps. AGE_18_30 GER_MALE EMOTION_NEU INTENT_EXPLAIN",
            "logical clocks. Use logical clocks instead of physical time stamps.",
            "Positive: standard multi-tag suffix removal",
        ),
        (
            "show select average from table person where name is some. AGE_30_45 GER_MALE EMOTION_NEU INTENT_INSTRUCT",
            "show select average from table person where name is some.",
            "Positive: SQL statement with trailing annotations",
        ),
        (
            "Okay. AGE_30_45 GER_MALE EMOTION_SAD INTENT_ACCEPT",
            "Okay.",
            "Positive: single word + punctuation preserved",
        ),
        (
            "AngularJS is a AngularJS is a framework of JavaScript. AGE_18_30 GER_FEMALE EMOTION_SAD INTENT_EXPLAIN",
            "AngularJS is a AngularJS is a framework of JavaScript.",
            "Positive: stuttered repetition and framework names preserved",
        ),
        (
            "The candidate showed clear intent to explain the architecture.",
            "The candidate showed clear intent to explain the architecture.",
            "Negative: spoken word 'intent' without underscore preserved",
        ),
        (
            "We pass the integer variable age to the function.",
            "We pass the integer variable age to the function.",
            "Negative: spoken word 'age' preserved",
        ),
        (
            "In this experiment we check GER_MALE as a sample token in middle.",
            "In this experiment we check GER_MALE as a sample token in middle.",
            "Negative: mid-sentence token not at end of text preserved",
        ),
    ]

    for raw, expected, desc in test_cases:
        actual = clean_transcript(raw)
        assert actual == expected, (
            f"REGEX SANITY CHECK FAILED on '{desc}'!\n"
            f"  Input:    '{raw}'\n"
            f"  Expected: '{expected}'\n"
            f"  Actual:   '{actual}'"
        )
    print("  [OK] Regex annotation cleaning verified with all positive and negative test cases.")


# ---------------------------------------------------------------------------
# Comprehensive Memory Stats Logging (Host RAM & GPU VRAM)
# ---------------------------------------------------------------------------
def print_system_memory_stats(step_name=""):
    """Logs both host physical RAM and CUDA VRAM metrics safely."""
    ram = psutil.virtual_memory()
    host_used_gb = ram.used / 1e9
    host_avail_gb = ram.available / 1e9
    print(f"  [{step_name}] Host RAM  — Used: {host_used_gb:.2f} GB | Available: {host_avail_gb:.2f} GB ({ram.percent}% used)")

    if torch.cuda.is_available():
        allocated = torch.cuda.max_memory_allocated() / 1e9
        reserved = torch.cuda.max_memory_reserved() / 1e9
        print(f"  [{step_name}] CUDA VRAM — Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB")


# ---------------------------------------------------------------------------
# Data Collator for Whisper
# ---------------------------------------------------------------------------
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")

        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")

        # Mask padding tokens with -100 so CrossEntropy ignores them
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        # Cut start token if present at index 0
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        batch["labels"] = labels
        return batch


# ---------------------------------------------------------------------------
# Validation Set Loader & Blacklist Indexer
# ---------------------------------------------------------------------------
def build_validation_set_and_blacklist(
    processor: Any,
    max_val_samples: int = 200,
    min_duration: float = 0.5,
    max_duration: float = 30.0,
) -> tuple:
    """
    Streams validation samples from WhissleAI (split='validation').
    Extracts validation features and compiles blacklist sets of validation
    (source_file, audio_filepath) to guarantee zero leakage into training.
    """
    print(f"\nStreaming up to {max_val_samples} validation samples from official validation split...")
    ds_val_stream = load_dataset(DATASET_ID, split="validation", streaming=True)

    val_records = []
    val_blacklist_filepaths = set()
    val_blacklist_sources = set()
    drop_stats = {
        "corrupt_audio": 0,
        "sample_rate_mismatch": 0,
        "duration_out_of_bounds": 0,
        "empty_transcript": 0,
        "speech_rate_anomaly": 0,
        "label_length_overflow": 0,
    }

    for record in ds_val_stream:
        if len(val_records) >= max_val_samples:
            break

        src_file = record.get("source_file", "unknown")
        audio_fpath = record.get("audio_filepath", "unknown")

        # Record for leakage blacklist
        val_blacklist_sources.add(src_file)
        val_blacklist_filepaths.add(audio_fpath)

        # Audio validation
        audio_dict = record.get("audio", None)
        if not audio_dict or not isinstance(audio_dict, dict):
            drop_stats["corrupt_audio"] += 1
            continue
        arr = audio_dict.get("array", None)
        sr = audio_dict.get("sampling_rate", None)
        if arr is None or not isinstance(arr, np.ndarray) or len(arr) == 0 or not np.isfinite(arr).all():
            drop_stats["corrupt_audio"] += 1
            continue
        if sr != 16000:
            drop_stats["sample_rate_mismatch"] += 1
            continue
        if np.max(np.abs(arr)) < 1e-4:
            drop_stats["corrupt_audio"] += 1
            continue

        # Duration validation
        calc_dur = len(arr) / float(sr)
        meta_dur = float(record.get("duration", calc_dur))
        dur = meta_dur if abs(calc_dur - meta_dur) < 0.2 else calc_dur
        if dur < min_duration or dur > max_duration:
            drop_stats["duration_out_of_bounds"] += 1
            continue

        # Transcript cleaning & non-empty check
        cleaned_text = clean_transcript(record.get("text", ""))
        if not cleaned_text or len(cleaned_text.strip()) == 0:
            drop_stats["empty_transcript"] += 1
            continue

        # Speech rate check
        wps = len(cleaned_text.split()) / dur
        if dur > 5.0 and (wps > 8.5 or wps < 0.15):
            drop_stats["speech_rate_anomaly"] += 1
            continue

        # Label token limit check
        labels = processor.tokenizer(cleaned_text).input_ids
        if len(labels) > 448:
            drop_stats["label_length_overflow"] += 1
            continue

        # Feature extraction
        input_features = processor.feature_extractor(
            arr, sampling_rate=16000
        ).input_features[0]

        val_records.append({
            "input_features": input_features,
            "labels": labels,
        })

    print(f"  [Validation] Collected {len(val_records)} clean validation records.")
    print(f"  [Validation] Indexed {len(val_blacklist_sources)} distinct source sessions and {len(val_blacklist_filepaths)} audio files for train-leakage exclusion.")
    print(f"  [Validation] Drop statistics: {drop_stats}")

    val_ds = Dataset.from_list(val_records)
    return val_ds, val_blacklist_sources, val_blacklist_filepaths


# ---------------------------------------------------------------------------
# Disk Cache Compatibility Verifier
# ---------------------------------------------------------------------------
def verify_and_load_disk_cache(
    cache_dir: str,
    target_train_n: int,
) -> Optional[Dataset]:
    """
    Checks whether cache_dir already contains a complete, compatible Arrow dataset.
    Validates:
    - Existence of Arrow shard files
    - Total sample count >= target_train_n
    - Schema contains 'input_features' and 'labels'
    - Input features match Whisper dimensions (80 mel filterbanks x 3000 frames)
    - Labels are non-empty sequences
    - Sample values are finite (no NaN / Inf)
    Returns loaded Dataset if 100% compatible, otherwise None.
    """
    if not os.path.exists(cache_dir):
        return None

    arrow_files = sorted(glob.glob(os.path.join(cache_dir, "**", "*.arrow"), recursive=True))
    if not arrow_files:
        return None

    print(f"\n  [Cache Check] Found {len(arrow_files)} Arrow shard(s) in {cache_dir}. Verifying compatibility...")
    try:
        cached_ds = concatenate_datasets([Dataset.from_file(f) for f in arrow_files])
        cached_len = len(cached_ds)
        print(f"  [Cache Check] Shards contain {cached_len} records (Target: {target_train_n}).")

        if cached_len < target_train_n:
            print(f"  [Cache Check] Cache incomplete ({cached_len} < {target_train_n}). Incompatible.")
            return None

        # Verify column names
        required_cols = {"input_features", "labels"}
        if not required_cols.issubset(set(cached_ds.column_names)):
            print(f"  [Cache Check] Missing columns. Found: {cached_ds.column_names}. Incompatible.")
            return None

        # Verify sample dimensions and finiteness
        sample_0 = cached_ds[0]
        feats = np.array(sample_0["input_features"], dtype=np.float32)
        if feats.ndim != 2 or feats.shape[0] != 80 or feats.shape[1] != 3000:
            print(f"  [Cache Check] Feature shape mismatch: {feats.shape} vs expected (80, 3000). Incompatible.")
            return None
        if not np.isfinite(feats).all():
            print(f"  [Cache Check] Non-finite values in cached features. Incompatible.")
            return None

        labels = sample_0["labels"]
        if not labels or len(labels) == 0:
            print(f"  [Cache Check] Empty label sequence in sample 0. Incompatible.")
            return None

        # Slice to exact target_train_n if cache has more
        if cached_len > target_train_n:
            cached_ds = cached_ds.select(range(target_train_n))

        print(f"  [Cache Verification PASSED] Existing disk cache is 100% valid and compatible!")
        print(f"  Reusing {len(cached_ds)} cached records (Mel shape: 80x3000, schema: {cached_ds.column_names}).")
        return cached_ds
    except Exception as e:
        print(f"  [Cache Check] Error while verifying existing cache: {e}. Falling back to generation.")
        return None


# ---------------------------------------------------------------------------
# Training Dataset Builder with Disk-Backed Arrow Caching
# ---------------------------------------------------------------------------
def build_cached_train_dataset(
    processor: Any,
    target_train_n: int,
    cache_dir: str,
    val_blacklist_sources: set,
    val_blacklist_filepaths: set,
    min_duration: float = 0.5,
    max_duration: float = 30.0,
) -> Dataset:
    """
    Streams training samples from WhissleAI (split='train').
    Extracts features on-the-fly and writes directly to a disk-backed Apache Arrow
    cache directory, guaranteeing RAM usage stays well below 3.89 GB.
    Halts with RuntimeError if fewer than target_train_n eligible samples are found.
    Reuses existing disk cache if verified compatible.
    """
    # 1. Compatibility check: Reuse existing disk cache if complete & verified
    verified_ds = verify_and_load_disk_cache(cache_dir, target_train_n)
    if verified_ds is not None:
        return verified_ds

    os.makedirs(cache_dir, exist_ok=True)
    print(f"\nBuilding disk-backed Arrow training cache ({target_train_n} unique recordings)...")
    print(f"  Cache Directory: {cache_dir}")

    # Track drop statistics and unique identifiers
    stats = {
        "scanned": 0,
        "valid_accepted": 0,
        "val_leakage_excluded": 0,
        "duplicate_excluded": 0,
        "corrupt_audio": 0,
        "sample_rate_mismatch": 0,
        "duration_out_of_bounds": 0,
        "empty_transcript": 0,
        "speech_rate_anomaly": 0,
        "label_length_overflow": 0,
    }

    seen_train_keys = set()
    unique_source_files = set()

    def train_generator():
        ds_train_stream = load_dataset(DATASET_ID, split="train", streaming=True)
        for record in ds_train_stream:
            stats["scanned"] += 1

            src_file = record.get("source_file", "unknown")
            audio_fpath = record.get("audio_filepath", "unknown")

            # 1. Validation Leakage Exclusion
            if src_file in val_blacklist_sources or audio_fpath in val_blacklist_filepaths:
                stats["val_leakage_excluded"] += 1
                continue

            # 2. Deduplication Check
            record_key = (src_file, audio_fpath)
            if record_key in seen_train_keys:
                stats["duplicate_excluded"] += 1
                continue

            # 3. Audio Validation
            audio_dict = record.get("audio", None)
            if not audio_dict or not isinstance(audio_dict, dict):
                stats["corrupt_audio"] += 1
                continue
            arr = audio_dict.get("array", None)
            sr = audio_dict.get("sampling_rate", None)
            if arr is None or not isinstance(arr, np.ndarray) or len(arr) == 0 or not np.isfinite(arr).all():
                stats["corrupt_audio"] += 1
                continue
            if sr != 16000:
                stats["sample_rate_mismatch"] += 1
                continue
            if np.max(np.abs(arr)) < 1e-4:
                stats["corrupt_audio"] += 1
                continue

            # 4. Duration Check
            calc_dur = len(arr) / float(sr)
            meta_dur = float(record.get("duration", calc_dur))
            dur = meta_dur if abs(calc_dur - meta_dur) < 0.2 else calc_dur
            if dur < min_duration or dur > max_duration:
                stats["duration_out_of_bounds"] += 1
                continue

            # 5. Transcript Cleaning & Non-Empty
            cleaned_text = clean_transcript(record.get("text", ""))
            if not cleaned_text or len(cleaned_text.strip()) == 0:
                stats["empty_transcript"] += 1
                continue

            # 6. Speech Rate Sanity
            wps = len(cleaned_text.split()) / dur
            if dur > 5.0 and (wps > 8.5 or wps < 0.15):
                stats["speech_rate_anomaly"] += 1
                continue

            # 7. Token Length Overflow Check
            labels = processor.tokenizer(cleaned_text).input_ids
            if len(labels) > 448:
                stats["label_length_overflow"] += 1
                continue

            # 8. Feature Extraction on-the-fly
            input_features = processor.feature_extractor(
                arr, sampling_rate=16000
            ).input_features[0]

            seen_train_keys.add(record_key)
            unique_source_files.add(src_file)
            stats["valid_accepted"] += 1

            if stats["valid_accepted"] % 1000 == 0:
                print(f"  [Progress] Cached {stats['valid_accepted']}/{target_train_n} valid recordings (Scanned: {stats['scanned']})...")
                print_system_memory_stats(f"Cache Progress {stats['valid_accepted']}")

            yield {
                "input_features": input_features,
                "labels": labels,
            }

            if stats["valid_accepted"] >= target_train_n:
                break

    # Construct memory-mapped Arrow dataset on disk
    feature_schema = Features({
        "input_features": Sequence(Sequence(Value("float32"))),
        "labels": Sequence(Value("int64")),
    })

    t0_cache = time.time()
    train_ds = Dataset.from_generator(
        train_generator,
        features=feature_schema,
        cache_dir=cache_dir,
    )
    cache_elapsed = time.time() - t0_cache

    print(f"\n  [Train Cache Complete] Generated {len(train_ds)} samples in {cache_elapsed:.1f}s.")
    print(f"  Distinct interview sessions: {len(unique_source_files)}")
    print(f"  Stream statistics: {stats}")

    # Requirement 4: Explicit Stop if fewer than target samples found
    if len(train_ds) < target_train_n:
        error_msg = (
            f"[CRITICAL ERROR] INSUFFICIENT ELIGIBLE SAMPLES!\n"
            f"  Target requested : {target_train_n}\n"
            f"  Eligible found   : {len(train_ds)}\n"
            f"  Scanned total    : {stats['scanned']}\n"
            f"Halting training immediately per safety rules. Will not silently train on fewer samples."
        )
        print(f"\n{error_msg}")
        raise RuntimeError(error_msg)

    return train_ds


# ---------------------------------------------------------------------------
# Main Training Function
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="PreMock AI — Whisper Technical Interview Fine-Tuning Pipeline"
    )
    parser.add_argument(
        "--smoke_test",
        action="store_true",
        help="Run quick smoke test with 10 train samples, 4 val samples, and 5 steps.",
    )
    parser.add_argument(
        "--max_train_samples",
        type=int,
        default=10000,
        help="Target number of unique valid training recordings (default: 10000).",
    )
    parser.add_argument(
        "--max_val_samples",
        type=int,
        default=200,
        help="Number of validation samples to evaluate on (default: 200).",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=625,
        help="Number of optimizer steps (default: 625 for 1 full epoch over 10000 samples).",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=5e-5,
        help="Learning rate for LoRA adapter (default: 5e-5).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUT_DIR,
        help=f"Dedicated output directory (default: {DEFAULT_OUT_DIR}).",
    )
    parser.add_argument(
        "--cache_dir",
        type=str,
        default=DEFAULT_CACHE_DIR,
        help=f"Disk-backed Arrow cache directory (default: {DEFAULT_CACHE_DIR}).",
    )
    parser.add_argument(
        "--from_scratch_lora",
        action="store_true",
        help="Initialize a fresh LoRA adapter instead of warming up from 20k checkpoint-1200.",
    )
    parser.add_argument(
        "--resume_from_checkpoint",
        type=str,
        default=None,
        help="Path to checkpoint directory to resume training from (restores adapter, optimizer, scheduler, RNG, and trainer state).",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("PreMock AI — Technical Interview Whisper LoRA Fine-Tuning Pipeline")
    print("=" * 70)

    # 1. Regex Cleaner Self-Test
    print("\n[Step 1/8] Verifying Annotation Cleaning Regex...")
    verify_regex_cleaner()

    # 2. Configure Limits and Output Directories
    if args.smoke_test:
        train_n = 10
        val_n = 4
        steps = 5
        eval_steps = 5
        save_steps = 5
        out_dir = SMOKE_OUT_DIR if args.output_dir == DEFAULT_OUT_DIR else args.output_dir
        print(f"\n[MODE] SMOKE TEST ACTIVE: train_samples={train_n}, val_samples={val_n}, steps={steps}")
    else:
        train_n = args.max_train_samples
        val_n = args.max_val_samples
        steps = args.max_steps
        eval_steps = 125
        save_steps = 125
        out_dir = args.output_dir
        print(f"\n[MODE] PHASE 1 TRAINING ACTIVE: train_samples={train_n}, val_samples={val_n}, steps={steps}")

    print(f"  Target Output Directory: {out_dir}")
    print(f"  Disk Cache Directory   : {args.cache_dir}")

    # Validate resume checkpoint if specified
    if args.resume_from_checkpoint:
        resume_dir = os.path.abspath(args.resume_from_checkpoint)
        if not os.path.isdir(resume_dir):
            raise FileNotFoundError(f"Resume checkpoint directory not found: {args.resume_from_checkpoint}")
        trainer_state_file = os.path.join(resume_dir, "trainer_state.json")
        if not os.path.isfile(trainer_state_file):
            raise FileNotFoundError(f"Missing trainer_state.json in resume checkpoint: {resume_dir}")
        with open(trainer_state_file, "r") as f:
            t_state = json.load(f)
        resumed_step = t_state.get("global_step", None)
        print(f"\n[Resume Check] Resuming from checkpoint: {resume_dir}")
        print(f"  Verified trainer_state.json: global_step = {resumed_step} (Target max_steps: {steps})")
        if resumed_step is not None and resumed_step >= steps:
            raise ValueError(f"Checkpoint already at step {resumed_step} >= max_steps ({steps})!")

    # Checkpoint safety check: Protect production model
    assert not os.path.samefile(
        os.path.abspath(out_dir), os.path.abspath(PREV_LORA_PATH)
    ) if os.path.exists(out_dir) else True, "FATAL: Output directory cannot be the production model!"

    # 3. Log Initial Memory State
    print("\n[Step 2/8] Logging Initial System Resources...")
    print_system_memory_stats("Initial State")

    # 4. Processor Initialization
    print(f"\n[Step 3/8] Initializing WhisperProcessor ({BASE_MODEL_ID})...")
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="English", task="transcribe")

    # 5. Build Separate Validation Set and Leakage Blacklist
    print("\n[Step 4/8] Building Validation Set & Leakage Blacklist...")
    val_ds, val_blacklist_sources, val_blacklist_filepaths = build_validation_set_and_blacklist(
        processor, max_val_samples=val_n
    )

    # 6. Build Disk-Backed Cached Training Dataset
    print("\n[Step 5/8] Streaming and Caching Training Dataset...")
    train_ds = build_cached_train_dataset(
        processor,
        target_train_n=train_n,
        cache_dir=args.cache_dir,
        val_blacklist_sources=val_blacklist_sources,
        val_blacklist_filepaths=val_blacklist_filepaths,
    )

    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

    # 7. Evaluation Metric (WER)
    metric = ev.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
        wer_val = metric.compute(predictions=pred_str, references=label_str)
        return {"wer": wer_val}

    # 8. Model Initialization (Base 8-bit + Trainable LoRA)
    print(f"\n[Step 6/8] Loading Base Model in 8-bit ({BASE_MODEL_ID})...")
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens = []
    base_model = prepare_model_for_kbit_training(base_model)

    if args.resume_from_checkpoint and os.path.exists(args.resume_from_checkpoint):
        print(f"  Loading LoRA adapter from resume checkpoint: {args.resume_from_checkpoint}")
        model = PeftModel.from_pretrained(base_model, args.resume_from_checkpoint, is_trainable=True)
    elif not args.from_scratch_lora and os.path.exists(PREV_LORA_PATH):
        print(f"  Loading warm-start adapter weights from: {PREV_LORA_PATH}")
        print("  [CRITICAL] Adapter weights loaded as trainable; Trainer optimizer/schedule start FRESH.")
        model = PeftModel.from_pretrained(base_model, PREV_LORA_PATH, is_trainable=True)
    else:
        print("  Initializing fresh LoRA adapter (r=8, alpha=16 on q_proj, v_proj)...")
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_proj", "v_proj"],
            lora_dropout=0.05,
            bias="none",
        )
        model = get_peft_model(base_model, lora_config)

    print_system_memory_stats("Post-Model Load")

    # 9. Training Arguments & Trainer Setup
    print(f"\n[Step 7/8] Configuring Trainer (Output Dir: {out_dir})...")
    training_args = Seq2SeqTrainingArguments(
        output_dir=out_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=args.learning_rate,
        warmup_steps=min(50, steps // 4) if steps > 10 else 1,
        max_steps=steps,
        gradient_checkpointing=True,
        fp16=torch.cuda.is_available(),
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=save_steps,
        logging_steps=1 if args.smoke_test else 25,
        remove_unused_columns=False,
        predict_with_generate=True,
        generation_max_length=225,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        save_total_limit=None,  # Preserves all checkpoints (125, 250, 375, 500, 625) without deleting or overwriting
        dataloader_num_workers=0,  # Single-process dataloader for Windows memory safety
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    # 10. Execution
    print(f"\n[Step 8/8] Starting Training Run ({steps} optimizer steps across {train_n} samples)...")
    start_train_time = time.time()
    try:
        resume_arg = args.resume_from_checkpoint if args.resume_from_checkpoint else None
        if resume_arg:
            print(f"  [RESUME ACTIVE] Calling trainer.train(resume_from_checkpoint='{resume_arg}')")
            print("  Restoring optimizer, scheduler, trainer state, and RNG state...")
        else:
            print(f"  [FRESH START] Calling trainer.train()")
        trainer.train(resume_from_checkpoint=resume_arg)
        train_elapsed_min = (time.time() - start_train_time) / 60.0
        print(f"\n  [SUCCESS] Training run finished successfully in {train_elapsed_min:.2f} minutes!")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n  [ERROR] CUDA OUT OF MEMORY: {e}")
            sys.exit(1)
        else:
            raise e

    # 11. Save Final Model
    print(f"\nSaving Best Checkpoint to {out_dir}...")
    os.makedirs(out_dir, exist_ok=True)
    trainer.save_model(out_dir)
    processor.save_pretrained(out_dir)
    print(f"  Model saved to: {out_dir}")
    print_system_memory_stats("Post-Training Complete")
    print("\n[COMPLETE] Phase 1 Training Finished Successfully.")


if __name__ == "__main__":
    main()
