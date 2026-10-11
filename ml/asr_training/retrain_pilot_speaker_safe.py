"""
retrain_pilot_speaker_safe.py
Retrains a small pilot using ONLY the speaker-safe split (processed_data_pilot_fixed).
Then evaluates both baseline whisper-base.en and the corrected fine-tuned model
on the same corrected validation set, reporting actual WER for both.
"""
import os
import torch
import evaluate as ev
from dataclasses import dataclass
from typing import Any, Dict, List, Union
from datasets import load_from_disk, Audio
from transformers import (
    WhisperForConditionalGeneration,
    WhisperProcessor,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(SCRIPT_DIR, "processed_data_pilot_fixed")
OUT_DIR     = os.path.join(SCRIPT_DIR, "..", "asr_model", "pilot_model_corrected")
OUT_DIR     = os.path.normpath(OUT_DIR)
MODEL_ID    = "openai/whisper-base.en"
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Device : {DEVICE}")
print(f"Data   : {DATA_DIR}")
print(f"Output : {OUT_DIR}\n")

# ── 1. Load corrected dataset ───────────────────────────────────────────────
print("Loading speaker-safe dataset...")
dataset = load_from_disk(DATA_DIR)
print(f"  Train      : {len(dataset['train'])} samples")
print(f"  Validation : {len(dataset['validation'])} samples")
print(f"  Test       : {len(dataset['test'])} samples")

# Verify zero overlap
train_spk = set(dataset["train"]["client_id"])
val_spk   = set(dataset["validation"]["client_id"])
test_spk  = set(dataset["test"]["client_id"])
tv_overlap = train_spk & val_spk
tt_overlap = train_spk & test_spk
vt_overlap = val_spk  & test_spk
print(f"\n  Speaker overlap train/val  : {len(tv_overlap)} (MUST be 0)")
print(f"  Speaker overlap train/test : {len(tt_overlap)} (MUST be 0)")
print(f"  Speaker overlap val/test   : {len(vt_overlap)} (MUST be 0)")
assert len(tv_overlap) == 0, "Speaker leakage detected in train/val!"
assert len(tt_overlap) == 0, "Speaker leakage detected in train/test!"
print("  [OK] No speaker leakage confirmed.\n")

# ── 2. Load processor ───────────────────────────────────────────────────────
print("Loading processor...")
processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

# ── 3. Feature extraction ───────────────────────────────────────────────────
def prepare_example(batch):
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
    return batch

print("Extracting features for all splits...")
cols_to_remove = dataset["train"].column_names
dataset = dataset.map(prepare_example, remove_columns=cols_to_remove, num_proc=1)

# ── 4. Data collator ────────────────────────────────────────────────────────
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any
    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch

data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

# ── 5. WER metric ───────────────────────────────────────────────────────────
metric = ev.load("wer")
def compute_metrics(pred):
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
    pred_str  = processor.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
    return {"wer": metric.compute(predictions=pred_str, references=label_str)}

# ── 6. Load model with 8-bit LoRA ───────────────────────────────────────────
print("Loading whisper-base.en in 8-bit for LoRA training...")
bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
model = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
)
model.config.forced_decoder_ids = None
model.config.suppress_tokens = []
model = prepare_model_for_kbit_training(model)
lora_cfg = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"],
                      lora_dropout=0.05, bias="none")
model = get_peft_model(model, lora_cfg)
model.print_trainable_parameters()

# ── 7. Training ─────────────────────────────────────────────────────────────
train_args = Seq2SeqTrainingArguments(
    output_dir=OUT_DIR,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=1e-4,
    warmup_steps=5,
    max_steps=50,
    gradient_checkpointing=True,
    fp16=True,
    eval_strategy="steps",
    per_device_eval_batch_size=2,
    predict_with_generate=True,
    generation_max_length=225,
    save_steps=25,
    eval_steps=25,
    logging_steps=10,
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    remove_unused_columns=False,
)

trainer = Seq2SeqTrainer(
    args=train_args,
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    tokenizer=processor.feature_extractor,
)

print("\nStarting corrected pilot training (50 steps)...")
trainer.train()
trainer.save_model()
processor.save_pretrained(OUT_DIR)
print(f"\nCorrected pilot model saved to: {OUT_DIR}")

# ── 8. BASELINE vs FINE-TUNED comparison on corrected validation set ────────
print("\n" + "="*65)
print("  BASELINE vs CORRECTED FINE-TUNED COMPARISON")
print("="*65)

# Reload raw validation audio for inference
val_raw = load_from_disk(DATA_DIR)["validation"]
print(f"  Evaluating on {len(val_raw)} corrected validation samples...")

def transcribe_all(model, val_raw, use_fp16=False):
    preds, refs = [], []
    model.eval()
    with torch.no_grad():
        for ex in val_raw:
            audio = ex["audio"]
            inputs = processor.feature_extractor(
                audio["array"], sampling_rate=audio["sampling_rate"], return_tensors="pt"
            ).input_features.to(DEVICE)
            if use_fp16:
                inputs = inputs.half()
            forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
            gen = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
            preds.append(processor.batch_decode(gen, skip_special_tokens=True)[0].strip())
            refs.append(ex["sentence"].strip())
    return preds, refs

# Baseline
print("\n[BASELINE] Loading original whisper-base.en (no LoRA)...")
del model
torch.cuda.empty_cache()
baseline = WhisperForConditionalGeneration.from_pretrained(MODEL_ID).to(DEVICE)
base_preds, base_refs = transcribe_all(baseline, val_raw, use_fp16=False)
base_wer = metric.compute(predictions=base_preds, references=base_refs)
del baseline
torch.cuda.empty_cache()

# Fine-tuned
print("[FINE-TUNED] Loading corrected LoRA model...")
base2 = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID, quantization_config=BitsAndBytesConfig(load_in_8bit=True), device_map="auto"
)
base2.config.forced_decoder_ids = None
base2.config.suppress_tokens = []
ft_model = PeftModel.from_pretrained(base2, OUT_DIR)
ft_preds, ft_refs = transcribe_all(ft_model, val_raw, use_fp16=True)
ft_wer = metric.compute(predictions=ft_preds, references=ft_refs)

print("\n" + "="*65)
print(f"  Original whisper-base.en WER : {base_wer*100:.2f}%")
print(f"  Corrected fine-tuned WER     : {ft_wer*100:.2f}%")
delta = (ft_wer - base_wer) * 100
sign  = "improvement" if delta < 0 else "degradation"
print(f"  Absolute change              : {abs(delta):.2f}% {sign}")
print("="*65)

print(f"\n  Sample predictions (first 5):")
print("-"*65)
for i in range(min(5, len(base_refs))):
    print(f"\n  Reference  : {base_refs[i]}")
    print(f"  Baseline   : {base_preds[i]}")
    print(f"  Fine-tuned : {ft_preds[i]}")
print("-"*65)
print("\nCorrected evaluation complete.")
