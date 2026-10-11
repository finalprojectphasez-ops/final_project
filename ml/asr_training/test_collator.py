import torch
from datasets import load_dataset, Audio
from transformers import WhisperProcessor
from typing import Any, Dict, List
from dataclasses import dataclass

processor = WhisperProcessor.from_pretrained("openai/whisper-base.en", language="English", task="transcribe")

@dataclass
class DataCollator:
    processor: Any
    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        inp = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(inp, return_tensors="pt")
        lab = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(lab, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch

def prep(batch):
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
    return batch

print("Loading dataset for test...")
ds = load_dataset("ishands/commonvoice-indian_accent", split="train").cast_column("audio", Audio(sampling_rate=16000)).select(range(5))
ds = ds.map(prep, remove_columns=ds.column_names)

# REGRESSION TEST
long_label = ds[0]["labels"] * 40
def inject_long(batch, idx):
    if idx == 0:
        batch["labels"] = long_label
    return batch
ds = ds.map(inject_long, with_indices=True)

print(f"Before filter: {len(ds)} samples")
ds = ds.filter(lambda x: len(x["labels"]) <= 448)
print(f"After filter: {len(ds)} samples")

if len(ds) == 4:
    print("Regression Test Passed! Long sequence safely filtered out.")
else:
    print("Regression Test Failed!")

collator = DataCollator(processor=processor)
batch = collator([ds[i] for i in range(len(ds))])

print("Collator Smoke Test Passed!")
print(f"Input features shape: {batch['input_features'].shape}")
print(f"Labels shape: {batch['labels'].shape}")
