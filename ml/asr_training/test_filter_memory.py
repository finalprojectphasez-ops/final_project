"""
Memory-safe filter smoke test.
Uses the same cached preprocessed dataset (train_ds after .map()) to
verify that num_proc=1 filtering works without a MemoryError.
Only loads a small slice (500 samples) to keep RAM usage low.
"""
import os, sys, json, torch
from datasets import load_dataset, Audio
from transformers import WhisperProcessor

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_FILE = os.path.join(SCRIPT_DIR, "full_speaker_split.json")
MODEL_ID   = "openai/whisper-base.en"

def main():
    print("Loading speaker splits...")
    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)
    train_spk = set(splits["train"])

    print("Loading dataset (will hit cache)...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    print("Filtering train speakers (num_proc=4, cached)...")
    train_ds = ds.filter(lambda x: x["client_id"] in train_spk, num_proc=4)
    train_ds = train_ds.shuffle(seed=42).select(range(500))   # small slice only
    print(f"Slice size: {len(train_ds)}")

    processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

    def prep(batch):
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    print("Mapping features (num_proc=4)...")
    train_ds = train_ds.map(prep, remove_columns=train_ds.column_names, num_proc=4)
    print(f"After map: {len(train_ds)} samples")

    print("Filtering labels <= 448 (num_proc=1, memory-safe)...")
    before = len(train_ds)
    train_ds = train_ds.filter(lambda x: len(x["labels"]) <= 448, num_proc=1)
    after = len(train_ds)
    removed = before - after
    print(f"After filter: {after} samples  (removed {removed} long-transcript examples)")
    print("MEMORY-SAFE FILTER TEST PASSED!")

if __name__ == "__main__":
    main()
