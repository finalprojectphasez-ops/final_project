from datasets import load_dataset
from transformers import WhisperProcessor
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
processor = WhisperProcessor.from_pretrained("openai/whisper-base.en", language="English", task="transcribe")

def main():
    print("Loading split file...")
    with open(os.path.join(SCRIPT_DIR, "full_speaker_split.json"), "r") as f:
        splits = json.load(f)

    train_spk = set(splits["train"])
    print("Loading dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")

    print("Filtering for train split...")
    train_ds = ds.filter(lambda x: x["client_id"] in train_spk, num_proc=4)
    print("Selecting 20000...")
    train_ds = train_ds.shuffle(seed=42).select(range(min(20000, len(train_ds))))

    print("Scanning for long transcripts...")
    long_count = 0
    for i, ex in enumerate(train_ds):
        tokens = processor.tokenizer(ex["sentence"]).input_ids
        if len(tokens) > 448:
            long_count += 1
            if long_count == 1:
                print(f"Found first long transcript at index {i} with {len(tokens)} tokens!")
                print(f"Sentence excerpt: {ex['sentence'][:500]}")

    print(f"\nTotal transcripts > 448 tokens: {long_count}")

if __name__ == "__main__":
    main()
