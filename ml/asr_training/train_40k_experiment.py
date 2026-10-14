"""
train_40k_experiment.py

Controlled continuation experiment for PreMock AI Whisper ASR:
- Starts from the existing fine-tuned 20k LoRA adapter (whisper_indian_accent_lora_20k).
- Trains on 20,000 previously unused, verified recordings from the training split ONLY (indices 20000 to 40002).
- Zero overlap with previous 20k training data.
- Zero speaker leakage into validation or test sets.
- Conservative learning rate (3e-5) to prevent catastrophic forgetting.
- Outputs exclusively to a separate directory: asr_model/whisper_indian_accent_40k_experiment.
- Deployed 20k adapter remains 100% untouched.

DO NOT RUN AUTOMATICALLY — AWAIT EXPLICIT USER APPROVAL.
"""

import os
import sys
import json
import torch
from datasets import load_dataset, Audio
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor,
    Seq2SeqTrainer, Seq2SeqTrainingArguments, BitsAndBytesConfig
)
from peft import PeftModel, prepare_model_for_kbit_training
from dataclasses import dataclass
from typing import Any, Dict, List
import evaluate as ev

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_FILE = os.path.join(SCRIPT_DIR, "full_speaker_split.json")
PREV_LORA  = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200")
OUT_DIR    = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_40k_experiment")
MODEL_ID   = "openai/whisper-base.en"

def print_memory_stats(step_name=""):
    if torch.cuda.is_available():
        allocated = torch.cuda.max_memory_allocated() / 1e9
        reserved = torch.cuda.max_memory_reserved() / 1e9
        print(f"[{step_name}] Peak CUDA Memory - Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB")

def main():
    print("=" * 65)
    print("  PreMock AI — Additional 20k Whisper LoRA Continuation Experiment")
    print(f"  Starting Adapter : {PREV_LORA}")
    print(f"  Target Output    : {OUT_DIR}")
    print("=" * 65)

    # 1. Load verified speaker splits
    if not os.path.exists(SPLIT_FILE):
        print(f"Error: {SPLIT_FILE} not found!")
        sys.exit(1)

    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)

    train_spk = set(splits["train"])
    val_spk   = set(splits["validation"])

    # 2. Load dataset
    print("Loading dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    # 3. Filter safely by speaker splits
    print("Filtering dataset by verified speaker splits...")
    cids = ds["client_id"]
    train_indices = [i for i, cid in enumerate(cids) if cid in train_spk]
    val_indices   = [i for i, cid in enumerate(cids) if cid in val_spk]

    train_ds = ds.select(train_indices).shuffle(seed=42)
    val_ds   = ds.select(val_indices).shuffle(seed=42)

    # 4. Select the SECOND 20,000 batch (indices 20,000 to 40,002 to account for length filtering)
    print("Selecting strictly unused second 20k slice (indices 20000..40002)...")
    train_subset = train_ds.select(range(20000, min(40002, len(train_ds))))
    val_subset   = val_ds.select(range(min(200, len(val_ds))))

    print(f"Selected raw slices -> Train: {len(train_subset)} | Val: {len(val_subset)}")

    # 5. Processor & Preprocessing
    processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

    def prep(batch):
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    print("Extracting features (per-device memory safe)...")
    train_subset = train_subset.map(prep, remove_columns=train_subset.column_names, num_proc=1)
    val_subset   = val_subset.map(prep, remove_columns=val_subset.column_names, num_proc=1)

    # Filter out sequences exceeding 448 token limit
    train_subset = train_subset.filter(lambda x: len(x["labels"]) <= 448, num_proc=1)
    val_subset   = val_subset.filter(lambda x: len(x["labels"]) <= 448, num_proc=1)

    # Cap to exactly 20,000 clean training samples
    if len(train_subset) > 20000:
        train_subset = train_subset.select(range(20000))

    print(f"Final clean training dataset: {len(train_subset)} samples")
    print(f"Final validation dataset    : {len(val_subset)} samples")

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

    data_collator = DataCollator(processor=processor)

    metric = ev.load("wer")
    def compute_metrics(pred):
        pred_ids  = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        return {"wer": metric.compute(
            predictions=processor.batch_decode(pred_ids, skip_special_tokens=True),
            references=processor.batch_decode(label_ids, skip_special_tokens=True)
        )}

    # 6. Model initialization continuing from previous 20k LoRA adapter
    print(f"Loading base model {MODEL_ID} in 8-bit...")
    torch.cuda.reset_peak_memory_stats()
    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens    = []
    base_model = prepare_model_for_kbit_training(base_model)

    print(f"Loading existing 20k LoRA adapter from {PREV_LORA} for continued training...")
    model = PeftModel.from_pretrained(base_model, PREV_LORA, is_trainable=True)
    model.print_trainable_parameters()

    print_memory_stats("Post-Model Load")

    # 7. Safe training arguments for 4GB RTX 3050 Laptop GPU
    # 20,000 samples / (2 * 8) = 1,250 steps for 1 epoch
    args = Seq2SeqTrainingArguments(
        output_dir=OUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=3e-5,            # Conservative learning rate to preserve earlier 20k learning
        warmup_steps=50,
        max_steps=1250,                # 1 full epoch over the new 20,000 samples
        gradient_checkpointing=True,
        fp16=True,
        eval_strategy="steps",
        eval_steps=250,                # Periodic validation WER checks (5 times per epoch)
        save_strategy="steps",
        save_steps=250,
        logging_steps=50,
        remove_unused_columns=False,
        predict_with_generate=True,
        generation_max_length=225,
        report_to="none",
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        save_total_limit=3,
    )

    trainer = Seq2SeqTrainer(
        args=args, model=model,
        train_dataset=train_subset,
        eval_dataset=val_subset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    print(f"\nTraining configuration prepared.")
    print(f"Effective batch size: {args.per_device_train_batch_size * args.gradient_accumulation_steps}")
    print(f"Max steps: {args.max_steps} (~1 epoch)")
    print(f"Output directory: {OUT_DIR}")
    import time
    start_time = time.time()
    print("\nStarting training run...")

    try:
        train_result = trainer.train()
        print("\nTraining completed successfully!")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n[ERROR] CUDA OUT OF MEMORY DETECTED: {e}")
            sys.exit(1)
        else:
            raise e
    except Exception as e:
        print(f"\n[ERROR] TRAINING EXCEPTION: {e}")
        sys.exit(1)

    duration_sec = time.time() - start_time
    duration_min = duration_sec / 60.0

    # Save final best model in dedicated experiment folder
    os.makedirs(OUT_DIR, exist_ok=True)
    trainer.save_model(OUT_DIR)
    processor.save_pretrained(OUT_DIR)
    print(f"Final best model saved to: {OUT_DIR}")
    print_memory_stats("Post-Training")

    best_ckpt = trainer.state.best_model_checkpoint
    best_wer = trainer.state.best_metric

    peak_allocated_gb = torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0.0
    peak_reserved_gb = torch.cuda.max_memory_reserved() / 1e9 if torch.cuda.is_available() else 0.0

    summary = {
        "best_checkpoint": best_ckpt,
        "best_val_wer": best_wer,
        "training_duration_seconds": round(duration_sec, 2),
        "training_duration_minutes": round(duration_min, 2),
        "peak_gpu_allocated_gb": round(peak_allocated_gb, 3),
        "peak_gpu_reserved_gb": round(peak_reserved_gb, 3),
        "total_steps": trainer.state.global_step,
        "train_samples": len(train_subset),
        "val_samples": len(val_subset),
    }

    summary_path = os.path.join(OUT_DIR, "experiment_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 65)
    print("  EXPERIMENT SUMMARY REPORT")
    print(f"  Best Checkpoint        : {best_ckpt}")
    if best_wer is not None:
        print(f"  Best Validation WER    : {best_wer:.4f} ({best_wer*100:.2f}%)")
    else:
        print("  Best Validation WER    : N/A")
    print(f"  Training Duration      : {duration_min:.2f} minutes ({duration_sec:.1f} s)")
    print(f"  Peak GPU Allocated     : {peak_allocated_gb:.2f} GB")
    print(f"  Peak GPU Reserved      : {peak_reserved_gb:.2f} GB")
    print("=" * 65)

if __name__ == "__main__":
    main()
