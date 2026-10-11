"""
evaluate_baseline_vs_finetuned.py
Compares WER of original whisper-base.en vs the fine-tuned LoRA pilot model
on the exact same validation recordings.
"""

import os
import torch
import numpy as np
from datasets import load_from_disk
from transformers import WhisperForConditionalGeneration, WhisperProcessor, WhisperFeatureExtractor, WhisperTokenizer
from peft import PeftModel
import evaluate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "processed_data_pilot")
PILOT_DIR  = os.path.join(SCRIPT_DIR, "..", "asr_model", "pilot_model")
MODEL_ID   = "openai/whisper-base.en"
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Device: {DEVICE}")

# ── 1. Load validation split ────────────────────────────────────────────────
print("\nLoading validation dataset...")
val_ds = load_from_disk(DATA_DIR)["validation"]
print(f"  Validation samples: {len(val_ds)}")

# ── 2. Load shared processor ────────────────────────────────────────────────
print("Loading processor (shared for both models)...")
processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

# ── 3. Inference helper ─────────────────────────────────────────────────────
def transcribe_batch(model, examples, use_fp16=False):
    predictions, references = [], []
    model.eval()
    with torch.no_grad():
        for ex in examples:
            audio = ex["audio"]
            inputs = processor.feature_extractor(
                audio["array"], sampling_rate=audio["sampling_rate"], return_tensors="pt"
            ).input_features.to(DEVICE)
            # 8-bit LoRA model weights are fp16 — cast inputs accordingly
            if use_fp16:
                inputs = inputs.half()
            forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
            generated = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
            pred = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
            ref  = ex["sentence"].strip()
            predictions.append(pred)
            references.append(ref)
    return predictions, references

# ── 4. BASELINE: original pretrained whisper-base.en ───────────────────────
print("\n[BASELINE] Loading original whisper-base.en (float32, no LoRA)...")
baseline_model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID).to(DEVICE)
print("  Running inference on all validation samples...")
base_preds, base_refs = transcribe_batch(baseline_model, val_ds)
del baseline_model
torch.cuda.empty_cache()

# ── 5. FINE-TUNED: LoRA pilot model ────────────────────────────────────────
print("\n[FINE-TUNED] Loading pilot LoRA model in 8-bit...")
from transformers import BitsAndBytesConfig
bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
base_for_peft = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
)
base_for_peft.config.forced_decoder_ids = None
base_for_peft.config.suppress_tokens = []
ft_model = PeftModel.from_pretrained(base_for_peft, PILOT_DIR)
print("  Running inference on all validation samples...")
ft_preds, ft_refs = transcribe_batch(ft_model, val_ds, use_fp16=True)
del ft_model, base_for_peft
torch.cuda.empty_cache()

# ── 6. WER calculation ──────────────────────────────────────────────────────
metric = evaluate.load("wer")
base_wer = metric.compute(predictions=base_preds, references=base_refs)
ft_wer   = metric.compute(predictions=ft_preds,   references=ft_refs)

print("\n" + "="*65)
print("  BASELINE vs FINE-TUNED COMPARISON  (Validation Set)")
print("="*65)
print(f"  Original whisper-base.en WER : {base_wer*100:.2f}%")
print(f"  Fine-tuned pilot WER         : {ft_wer*100:.2f}%")
delta = (ft_wer - base_wer) * 100
sign  = "improvement" if delta < 0 else "degradation"
print(f"  Absolute change              : {abs(delta):.2f}% {sign}")
print("="*65)

# ── 7. Sample predictions ───────────────────────────────────────────────────
N = min(5, len(base_refs))
print(f"\n  Sample Predictions (first {N} validation examples)")
print("-"*65)
for i in range(N):
    print(f"\n  Reference  : {base_refs[i]}")
    print(f"  Baseline   : {base_preds[i]}")
    print(f"  Fine-tuned : {ft_preds[i]}")
print("-"*65)
print(f"\n  GPU VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB total")
print(f"  Allocated now: {torch.cuda.memory_allocated(0)/1e6:.0f}MB")
print(f"  Reserved  now: {torch.cuda.memory_reserved(0)/1e6:.0f}MB")
print("\nEvaluation complete.")
