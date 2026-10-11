"""
fix_speaker_split.py
Fixes speaker leakage in the pilot dataset by grouping samples by client_id
and ensuring no speaker appears in more than one split.
"""
import os
import random
from datasets import load_from_disk, DatasetDict
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Load the original raw 140 samples from the combined pilot pool
DATA_DIR   = os.path.join(SCRIPT_DIR, "processed_data_pilot")

print("Loading pilot dataset...")
ds = load_from_disk(DATA_DIR)

# Combine all splits back into one pool first
all_data = []
for split in ds.keys():
    for ex in ds[split]:
        all_data.append(ex)

print(f"Total samples in pool: {len(all_data)}")

# Group indices by client_id
speaker_to_indices = defaultdict(list)
for i, ex in enumerate(all_data):
    speaker_to_indices[ex["client_id"]].append(i)

speakers = list(speaker_to_indices.keys())
random.seed(42)
random.shuffle(speakers)

total_speakers = len(speakers)
val_n  = max(1, int(total_speakers * 0.15))
test_n = max(1, int(total_speakers * 0.15))
train_n = total_speakers - val_n - test_n

train_speakers = set(speakers[:train_n])
val_speakers   = set(speakers[train_n:train_n + val_n])
test_speakers  = set(speakers[train_n + val_n:])

print(f"Speaker allocation -- Train: {len(train_speakers)}, Val: {len(val_speakers)}, Test: {len(test_speakers)}")

train_idx, val_idx, test_idx = [], [], []
for i, ex in enumerate(all_data):
    cid = ex["client_id"]
    if cid in train_speakers:
        train_idx.append(i)
    elif cid in val_speakers:
        val_idx.append(i)
    else:
        test_idx.append(i)

print(f"Sample allocation  -- Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

# Rebuild as DatasetDict using the combined dataset
from datasets import concatenate_datasets
all_ds = concatenate_datasets([ds[s] for s in ds.keys()])

fixed = DatasetDict({
    "train":      all_ds.select(train_idx),
    "validation": all_ds.select(val_idx),
    "test":       all_ds.select(test_idx),
})

out = os.path.join(SCRIPT_DIR, "processed_data_pilot_fixed")
print(f"\nSaving fixed dataset to: {out}")
fixed.save_to_disk(out)
print("Done. No speakers overlap across splits.")
