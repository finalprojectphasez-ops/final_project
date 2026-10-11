"""
inspect_full_dataset.py
Streams the full dataset to count rows, unique speakers,
and filtering statistics — without loading everything into RAM.
"""
import os
import sys
from datasets import load_dataset, Audio
from collections import defaultdict

print("Streaming full dataset to count rows...")
print("(This uses streaming mode - no large download required)\n")

try:
    # Stream the dataset without loading into memory
    ds_stream = load_dataset(
        "ishands/commonvoice-indian_accent",
        split="train",
        streaming=True
    )
except Exception as e:
    print(f"ERROR loading dataset: {e}")
    sys.exit(1)

total_rows         = 0
valid_rows         = 0
missing_sentence   = 0
empty_sentence     = 0
missing_audio      = 0
unique_speakers    = set()
speakers_samples   = defaultdict(int)
domain_counts      = defaultdict(int)
locale_counts      = defaultdict(int)

print("Counting... (this may take a minute)")
for ex in ds_stream:
    total_rows += 1

    # Check sentence
    sentence = ex.get("sentence", None)
    if sentence is None:
        missing_sentence += 1
        continue
    if not sentence.strip():
        empty_sentence += 1
        continue

    # Check audio bytes exist (don't decode — just check the path/bytes field)
    audio = ex.get("audio", None)
    if audio is None:
        missing_audio += 1
        continue

    valid_rows += 1
    cid = ex.get("client_id", "UNKNOWN")
    unique_speakers.add(cid)
    speakers_samples[cid] += 1

    domain = ex.get("sentence_domain", "unknown") or "unknown"
    domain_counts[domain] += 1

    locale = ex.get("locale", "unknown") or "unknown"
    locale_counts[locale] += 1

    if total_rows % 5000 == 0:
        print(f"  Scanned {total_rows} rows so far... ({valid_rows} valid, {len(unique_speakers)} speakers)")

print("\n" + "="*65)
print("  FULL DATASET STATISTICS")
print("="*65)
print(f"  Total rows in dataset        : {total_rows:,}")
print(f"  Valid rows (audio+transcript): {valid_rows:,}")
print(f"  Excluded — missing sentence  : {missing_sentence:,}")
print(f"  Excluded — empty sentence    : {empty_sentence:,}")
print(f"  Excluded — missing audio     : {missing_audio:,}")
print(f"  Total unique speakers        : {len(unique_speakers):,}")
print(f"  Avg samples per speaker      : {valid_rows/max(1,len(unique_speakers)):.1f}")
print()

# Speaker distribution
sample_counts = list(speakers_samples.values())
sample_counts.sort()
print(f"  Speaker sample distribution:")
print(f"    Min samples per speaker    : {min(sample_counts)}")
print(f"    Max samples per speaker    : {max(sample_counts)}")
print(f"    Median                     : {sample_counts[len(sample_counts)//2]}")

print(f"\n  Locale breakdown:")
for loc, cnt in sorted(locale_counts.items(), key=lambda x: -x[1])[:5]:
    print(f"    {loc:20s}: {cnt:,}")

print(f"\n  Domain breakdown (top 5):")
for dom, cnt in sorted(domain_counts.items(), key=lambda x: -x[1])[:5]:
    print(f"    {str(dom):20s}: {cnt:,}")

# Speaker-safe split proposal
print("\n" + "="*65)
print("  PROPOSED SPEAKER-SAFE SPLIT")
print("="*65)
speakers = sorted(unique_speakers)
import random
random.seed(42)
random.shuffle(speakers)

n_total    = len(speakers)
n_val      = max(10, int(n_total * 0.10))
n_test     = max(10, int(n_total * 0.10))
n_train    = n_total - n_val - n_test

train_spk = set(speakers[:n_train])
val_spk   = set(speakers[n_train:n_train+n_val])
test_spk  = set(speakers[n_train+n_val:])

train_samples = sum(speakers_samples[s] for s in train_spk)
val_samples   = sum(speakers_samples[s] for s in val_spk)
test_samples  = sum(speakers_samples[s] for s in test_spk)

print(f"  Training   : {n_train:,} speakers, {train_samples:,} samples")
print(f"  Validation : {n_val:,} speakers, {val_samples:,} samples")
print(f"  Test       : {n_test:,} speakers, {test_samples:,} samples")
print(f"  No speaker overlap: GUARANTEED")

# Save speaker assignments
out_dir = os.path.dirname(os.path.abspath(__file__))
import json
split_map = {
    "train": list(train_spk),
    "validation": list(val_spk),
    "test": list(test_spk),
}
with open(os.path.join(out_dir, "full_speaker_split.json"), "w") as f:
    json.dump(split_map, f, indent=2)
print(f"\n  Speaker split saved to: full_speaker_split.json")
print("="*65)
