import os
import json
import random
from collections import defaultdict
from datasets import load_dataset

print("Loading dataset...")
ds = load_dataset("ishands/commonvoice-indian_accent", split="train", trust_remote_code=True)
print(f"Dataset loaded. Total rows: {len(ds)}")

unique_speakers = set()
speakers_samples = defaultdict(int)

print("Counting speakers...")
client_ids = ds["client_id"]
for cid in client_ids:
    unique_speakers.add(cid)
    speakers_samples[cid] += 1

speakers = sorted(unique_speakers)
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

print(f"Training   : {n_train} speakers, {train_samples} samples")
print(f"Validation : {n_val} speakers, {val_samples} samples")
print(f"Test       : {n_test} speakers, {test_samples} samples")

out_dir = os.path.dirname(os.path.abspath(__file__))
split_map = {
    "train": list(train_spk),
    "validation": list(val_spk),
    "test": list(test_spk),
}
with open(os.path.join(out_dir, "full_speaker_split.json"), "w") as f:
    json.dump(split_map, f, indent=2)

print("Saved full_speaker_split.json")
