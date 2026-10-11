"""
evaluate_20k_vs_baseline.py

Compares original whisper-base.en against the 20k LoRA fine-tuned model
on a fixed, speaker-independent, held-out test set (500 samples, seed=42).

This test set was NEVER used during:
  - Training (train speakers only)
  - Checkpoint selection (validation speakers only)
  - Validation-based early stopping (validation speakers only)

Speaker safety is enforced via full_speaker_split.json.
"""

import os, sys, json, time, torch
from datasets import load_dataset, Audio
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from peft import PeftModel
import evaluate as ev

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SPLIT_FILE  = os.path.join(SCRIPT_DIR, "full_speaker_split.json")
MODEL_DIR   = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_lora_20k")
MODEL_ID    = "openai/whisper-base.en"
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
TEST_N      = 500
SEED        = 42
SAMPLE_SHOW = 5   # number of example predictions to print


def build_test_set():
    """Load held-out test speakers, select 500 samples (seed=42)."""
    print("Loading speaker splits...")
    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)

    train_spk = set(splits["train"])
    val_spk   = set(splits["validation"])
    test_spk  = set(splits["test"])

    # Confirm disjointness
    assert not (train_spk & test_spk), "SAFETY VIOLATION: train/test speaker overlap!"
    assert not (val_spk   & test_spk), "SAFETY VIOLATION: val/test speaker overlap!"
    print(f"  Train speakers  : {len(train_spk)}")
    print(f"  Val speakers    : {len(val_spk)}")
    print(f"  Test speakers   : {len(test_spk)}  [disjoint from train and val - OK]")

    print("\nLoading dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    print("Filtering to test speakers (num_proc=4)...")
    test_ds = ds.filter(lambda x: x["client_id"] in test_spk, num_proc=4)
    print(f"  Available test samples: {len(test_ds)}")

    test_ds = test_ds.shuffle(seed=SEED).select(range(min(TEST_N, len(test_ds))))
    print(f"  Using fixed {len(test_ds)} samples (seed={SEED}) for evaluation")
    return test_ds


def transcribe(model, test_ds, processor, use_fp16=False):
    """Run inference sample-by-sample. Returns (predictions, references, seconds)."""
    preds, refs = [], []
    model.eval()
    t0 = time.time()
    with torch.no_grad():
        for i, ex in enumerate(test_ds):
            audio = ex["audio"]
            inputs = processor.feature_extractor(
                audio["array"],
                sampling_rate=audio["sampling_rate"],
                return_tensors="pt"
            ).input_features.to(DEVICE)
            if use_fp16:
                inputs = inputs.half()
            forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
            generated  = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
            pred = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
            ref  = ex["sentence"].strip()
            preds.append(pred)
            refs.append(ref)
            if (i + 1) % 50 == 0:
                elapsed = time.time() - t0
                print(f"    [{i+1}/{len(test_ds)}]  {elapsed:.0f}s elapsed")
    return preds, refs, time.time() - t0


def main():
    print("=" * 65)
    print("  20k LoRA Fine-Tune vs Baseline — HELD-OUT TEST SET EVALUATION")
    print("=" * 65)

    # ── 1. Build test set ──────────────────────────────────────────────
    test_ds = build_test_set()

    # ── 2. Shared processor ───────────────────────────────────────────
    processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

    # ── 3. BASELINE ───────────────────────────────────────────────────
    print(f"\n[BASELINE] Loading original {MODEL_ID} (float32)...")
    baseline = WhisperForConditionalGeneration.from_pretrained(MODEL_ID).to(DEVICE)
    print("  Transcribing test set...")
    base_preds, base_refs, base_time = transcribe(baseline, test_ds, processor, use_fp16=False)
    del baseline
    torch.cuda.empty_cache()
    print(f"  Baseline inference done in {base_time:.1f}s")

    # ── 4. FINE-TUNED ─────────────────────────────────────────────────
    print(f"\n[FINE-TUNED] Loading 20k LoRA model from {MODEL_DIR}...")
    if not os.path.isdir(MODEL_DIR):
        print(f"ERROR: Model directory not found: {MODEL_DIR}")
        sys.exit(1)
    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    base_for_peft = WhisperForConditionalGeneration.from_pretrained(
        MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_for_peft.config.forced_decoder_ids = None
    base_for_peft.config.suppress_tokens    = []
    ft_model = PeftModel.from_pretrained(base_for_peft, MODEL_DIR)
    print("  Transcribing test set...")
    ft_preds, ft_refs, ft_time = transcribe(ft_model, test_ds, processor, use_fp16=True)
    del ft_model, base_for_peft
    torch.cuda.empty_cache()
    print(f"  Fine-tuned inference done in {ft_time:.1f}s")

    # ── 5. WER & CER ──────────────────────────────────────────────────
    metric_wer   = ev.load("wer")
    metric_cer   = ev.load("cer")
    
    base_wer = metric_wer.compute(predictions=base_preds, references=base_refs)
    ft_wer   = metric_wer.compute(predictions=ft_preds,   references=ft_refs)
    delta_wer    = (ft_wer - base_wer) * 100
    direction_wer = "improvement" if delta_wer < 0 else "degradation"
    
    base_cer = metric_cer.compute(predictions=base_preds, references=base_refs)
    ft_cer   = metric_cer.compute(predictions=ft_preds,   references=ft_refs)
    delta_cer    = (ft_cer - base_cer) * 100
    direction_cer = "improvement" if delta_cer < 0 else "degradation"

    print("\n" + "=" * 65)
    print("  FINAL EVALUATION RESULTS  (Held-Out Test Set)")
    print("=" * 65)
    print(f"  Test samples evaluated     : {len(test_ds)}")
    print(f"  Baseline inference time    : {base_time:.1f}s")
    print(f"  Fine-tuned inference time  : {ft_time:.1f}s")
    print(f"  Original whisper-base.en WER : {base_wer*100:.2f}% (CER: {base_cer*100:.2f}%)")
    print(f"  Fine-tuned LoRA 20k WER      : {ft_wer*100:.2f}% (CER: {ft_cer*100:.2f}%)")
    print(f"  Absolute WER change          : {abs(delta_wer):.2f}% {direction_wer}")
    print(f"  Absolute CER change          : {abs(delta_cer):.2f}% {direction_cer}")
    print("=" * 65)

    # ── 6. Sample predictions ─────────────────────────────────────────
    n = min(SAMPLE_SHOW, len(base_refs))
    print(f"\n  Sample Predictions (first {n} test examples)")
    print("-" * 65)
    for i in range(n):
        print(f"\n  Reference  : {base_refs[i]}")
        print(f"  Baseline   : {base_preds[i]}")
        print(f"  Fine-tuned : {ft_preds[i]}")
    print("-" * 65)

    # ── 7. GPU memory ─────────────────────────────────────────────────
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        print(f"\n  GPU           : {props.name}")
        print(f"  Total VRAM    : {props.total_memory/1e9:.1f} GB")
        print(f"  Allocated now : {torch.cuda.memory_allocated(0)/1e6:.0f} MB")
        print(f"  Reserved now  : {torch.cuda.memory_reserved(0)/1e6:.0f} MB")

    print("\nEvaluation complete.")


if __name__ == "__main__":
    main()
