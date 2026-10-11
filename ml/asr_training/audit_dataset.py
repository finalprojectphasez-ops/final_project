# -*- coding: utf-8 -*-
"""
audit_dataset.py
Audits the pilot dataset splits for:
  - Sample counts per split
  - Client ID speaker leakage across splits
  - Missing/empty transcripts
  - Audio validity
  - Token decoding correctness
"""

import os
from datasets import load_from_disk
from transformers import WhisperProcessor
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "processed_data_pilot")
MODEL_ID   = "openai/whisper-base.en"

print("Loading processor for token verification...")
processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

print(f"\nLoading dataset from: {DATA_DIR}")
ds = load_from_disk(DATA_DIR)

splits = list(ds.keys())
print(f"\nSplits found: {splits}")

# ── 1. Sample counts ────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  SAMPLE COUNTS")
print("="*60)
total = 0
for split in splits:
    n = len(ds[split])
    total += n
    print(f"  {split:12s}: {n} samples")
print(f"  {'TOTAL':12s}: {total} samples")

# ── 2. Column names ─────────────────────────────────────────────────────────
print(f"\n  Columns: {ds[splits[0]].column_names}")

# ── 3. Client ID speaker leakage ────────────────────────────────────────────
print("\n" + "="*60)
print("  CLIENT ID / SPEAKER LEAKAGE ANALYSIS")
print("="*60)
cols = ds[splits[0]].column_names
has_client_id = "client_id" in cols

if has_client_id:
    speaker_sets = {}
    for split in splits:
        ids = set(ds[split]["client_id"])
        speaker_sets[split] = ids
        print(f"  {split:12s}: {len(ids)} unique speakers")

    # Check overlap between train and val/test
    for s1 in splits:
        for s2 in splits:
            if s1 >= s2:
                continue
            overlap = speaker_sets[s1] & speaker_sets[s2]
            if overlap:
                print(f"\n  [WARNING] LEAKAGE: {len(overlap)} speaker(s) appear in BOTH '{s1}' and '{s2}'")
                for cid in list(overlap)[:3]:
                    print(f"      client_id: {cid}")
            else:
                print(f"\n  [OK] No speaker overlap between '{s1}' and '{s2}'")
else:
    print("  ⚠️  'client_id' column NOT present in dataset — speaker-based splitting not possible.")
    print("      Current split is random (shuffle + select by index).")

# ── 4. Missing / empty transcripts ─────────────────────────────────────────
print("\n" + "="*60)
print("  TRANSCRIPT QUALITY")
print("="*60)
for split in splits:
    empty = [i for i, s in enumerate(ds[split]["sentence"]) if not s or not s.strip()]
    print(f"  {split:12s}: {len(empty)} missing/empty transcripts")
    if empty[:3]:
        print(f"    Example indices: {empty[:3]}")

# ── 5. Audio validity ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("  AUDIO VALIDITY")
print("="*60)
for split in splits:
    bad, sr_mismatches, zero_len = [], [], []
    for i, ex in enumerate(ds[split]):
        audio = ex["audio"]
        arr = audio.get("array")
        sr  = audio.get("sampling_rate")
        if arr is None or len(arr) == 0:
            bad.append(i)
        elif len(arr) < 100:
            zero_len.append(i)
        if sr != 16000:
            sr_mismatches.append((i, sr))
    print(f"  {split:12s}: {len(bad)} null/empty arrays, "
          f"{len(zero_len)} near-zero arrays, "
          f"{len(sr_mismatches)} SR != 16kHz")

# ── 6. Token decode verification ───────────────────────────────────────────
print("\n" + "="*60)
print("  TOKEN DECODE VERIFICATION (first 3 train examples)")
print("="*60)
for i in range(min(3, len(ds["train"]))):
    ref = ds["train"][i]["sentence"]
    token_ids = processor.tokenizer(ref).input_ids
    # Simulate label masking: strip BOS if present
    if token_ids and token_ids[0] == processor.tokenizer.bos_token_id:
        token_ids = token_ids[1:]
    decoded = processor.tokenizer.decode(token_ids, skip_special_tokens=True)
    match = "[OK]" if decoded.strip() == ref.strip() else "[MISMATCH]"
    print(f"  [{i}] {match}")
    print(f"    Reference : {ref}")
    print(f"    Re-decoded: {decoded}")

print("\nAudit complete.")
