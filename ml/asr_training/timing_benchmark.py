"""
timing_benchmark.py
Runs a short timed benchmark (10 steps) to measure:
 - Seconds per training step (on current GPU, full batch)
 - Seconds per evaluation sample (generate mode)
 - Time to load and map a batch of 20 samples through feature extractor
Then computes a full training time estimate for the 110,088-row dataset.
"""
import time, os, torch
from datasets import load_from_disk
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor,
    Seq2SeqTrainer, Seq2SeqTrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dataclasses import dataclass
from typing import Any, Dict, List, Union
import evaluate as ev

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, "processed_data_pilot_fixed")
MODEL_ID   = "openai/whisper-base.en"
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
BENCH_STEPS = 10  # short benchmark run

print(f"Device: {DEVICE}")
print("="*65)

# ── Load dataset and processor ─────────────────────────────────────────────
processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")
dataset   = load_from_disk(DATA_DIR)

# ── Feature extraction timing ──────────────────────────────────────────────
print("\n[1] Measuring audio feature extraction speed...")
t0 = time.perf_counter()
def prep(batch):
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
    return batch

sample_20 = dataset["validation"]
t0 = time.perf_counter()
_ = sample_20.map(prep, remove_columns=sample_20.column_names, num_proc=1)
feat_time_20 = time.perf_counter() - t0
feat_per_sample = feat_time_20 / len(sample_20)
print(f"  Feature extraction: {feat_time_20:.2f}s for {len(sample_20)} samples")
print(f"  Per-sample rate   : {feat_per_sample:.3f} s/sample")
print(f"  For 110,088 full  : {110088 * feat_per_sample / 60:.1f} min")

# ── Prepare full dataset for training benchmark ────────────────────────────
cols_to_remove = dataset["train"].column_names
mapped_ds = dataset.map(prep, remove_columns=cols_to_remove, num_proc=1)

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

# ── Load model ─────────────────────────────────────────────────────────────
print("\n[2] Measuring training step speed (10 steps)...")
bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
model   = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
)
model.config.forced_decoder_ids = None
model.config.suppress_tokens    = []
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, LoraConfig(
    r=8, lora_alpha=16, target_modules=["q_proj","v_proj"],
    lora_dropout=0.05, bias="none"
))

bench_dir = os.path.join(SCRIPT_DIR, "..", "asr_model", "_bench_tmp")
args = Seq2SeqTrainingArguments(
    output_dir=bench_dir,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=1e-4,
    warmup_steps=2,
    max_steps=BENCH_STEPS,
    gradient_checkpointing=True,
    fp16=True,
    eval_strategy="no",
    save_strategy="no",
    logging_steps=BENCH_STEPS,
    remove_unused_columns=False,
    report_to="none",
)

trainer = Seq2SeqTrainer(
    args=args, model=model,
    train_dataset=mapped_ds["train"],
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    tokenizer=processor.feature_extractor,
)

t0 = time.perf_counter()
result = trainer.train()
train_elapsed = time.perf_counter() - t0
s_per_step  = train_elapsed / BENCH_STEPS
eff_batch   = 2 * 4  # per_device * grad_accum

print(f"  Benchmark steps   : {BENCH_STEPS}")
print(f"  Total time        : {train_elapsed:.2f}s")
print(f"  Seconds/step      : {s_per_step:.3f}")
print(f"  Effective batch   : {eff_batch} samples/step")

# ── Evaluation speed (inference / generate mode) ───────────────────────────
print("\n[3] Measuring eval (generate) speed on 20 val samples...")
val_raw = load_from_disk(DATA_DIR)["validation"]
model.eval()
t0 = time.perf_counter()
with torch.no_grad():
    for ex in val_raw:
        audio  = ex["audio"]
        inputs = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"], return_tensors="pt"
        ).input_features.to(DEVICE)
        forced = processor.get_decoder_prompt_ids(language="english", task="transcribe")
        model.generate(inputs, forced_decoder_ids=forced, max_new_tokens=225)
eval_elapsed  = time.perf_counter() - t0
s_per_eval    = eval_elapsed / len(val_raw)
print(f"  Eval samples      : {len(val_raw)}")
print(f"  Eval total time   : {eval_elapsed:.2f}s")
print(f"  Seconds/sample    : {s_per_eval:.3f}")

# ── FULL TRAINING ESTIMATE ─────────────────────────────────────────────────
print("\n" + "="*65)
print("  FULL TRAINING TIME ESTIMATE  (110,088 rows)")
print("="*65)

TOTAL_ROWS   = 110088
TRAIN_ROWS   = int(TOTAL_ROWS * 0.80)    # 88,070
VAL_ROWS     = int(TOTAL_ROWS * 0.10)    # 11,009
TEST_ROWS    = TOTAL_ROWS - TRAIN_ROWS - VAL_ROWS

# Phase 1: Download (estimated — cannot measure without actual download)
DOWNLOAD_GB  = 3.84
SPEED_MBS    = 8.0   # conservative home internet
dl_sec       = (DOWNLOAD_GB * 1024) / SPEED_MBS
print(f"\n  [A] Dataset download (~{DOWNLOAD_GB}GB @ {SPEED_MBS}MB/s)")
print(f"      Estimated: {dl_sec/60:.0f} min  ({dl_sec:.0f}s)")

# Phase 2: Preprocessing
prep_sec = feat_per_sample * TOTAL_ROWS
print(f"\n  [B] Audio preprocessing (feature extraction, {TOTAL_ROWS:,} rows)")
print(f"      Per-sample rate: {feat_per_sample:.3f}s")
print(f"      Estimated: {prep_sec/3600:.2f} h  ({prep_sec:.0f}s)")

# Phase 3: Training — 1 full epoch
steps_1ep    = TRAIN_ROWS // eff_batch    # integer steps in 1 epoch
train_1ep    = steps_1ep * s_per_step
print(f"\n  [C] Training — 1 epoch")
print(f"      Training samples: {TRAIN_ROWS:,}")
print(f"      Steps per epoch : {steps_1ep:,}  (batch={eff_batch})")
print(f"      Seconds/step    : {s_per_step:.3f}")
print(f"      Estimated: {train_1ep/3600:.2f} h  ({train_1ep:.0f}s)")

# Phase 4: Monitoring eval (small subset, every 500 steps)
EVAL_SUBSET  = 500    # recommended: not all 11K
EVAL_FREQ    = 500    # every 500 steps
n_eval_runs  = steps_1ep // EVAL_FREQ
eval_run_sec = EVAL_SUBSET * s_per_eval
total_eval_sec = n_eval_runs * eval_run_sec
print(f"\n  [D] Monitoring validation ({EVAL_SUBSET} samples every {EVAL_FREQ} steps)")
print(f"      Eval runs in 1 epoch: {n_eval_runs}")
print(f"      Per-run time: {eval_run_sec:.0f}s ({eval_run_sec/60:.1f}min)")
print(f"      Total eval time: {total_eval_sec/3600:.2f}h")

# Eval on ALL val samples if done after every eval:
all_val_eval = n_eval_runs * VAL_ROWS * s_per_eval
print(f"\n  [D-alt] If eval on ALL {VAL_ROWS:,} val samples every {EVAL_FREQ} steps:")
print(f"      Per-run time: {VAL_ROWS*s_per_eval/3600:.2f}h — IMPRACTICAL")

# Phase 5: Final full test eval (once)
final_eval = TEST_ROWS * s_per_eval
print(f"\n  [E] Final test-set evaluation ({TEST_ROWS:,} samples, once)")
print(f"      Estimated: {final_eval/3600:.2f}h")

# Checkpoint saving: ~45MB adapter per checkpoint, 1-2 min I/O each
chk_count  = steps_1ep // 500
chk_sec    = chk_count * 60   # 1 min per checkpoint
print(f"\n  [F] Checkpoint saving (~{chk_count} checkpoints, 1 min each)")
print(f"      Estimated: {chk_sec/60:.0f} min")

# TOTALS
total_1ep = prep_sec + train_1ep + total_eval_sec + chk_sec
total_2ep = prep_sec + 2*train_1ep + 2*total_eval_sec + chk_sec

print(f"\n{'='*65}")
print(f"  SUMMARY (excluding download)")
print(f"{'='*65}")
print(f"  1 epoch (recommended minimum): {total_1ep/3600:.1f} h")
print(f"  2 epochs                     : {total_2ep/3600:.1f} h")
print(f"\n  With download (~{dl_sec/60:.0f} min):")
print(f"  1 epoch total wall time      : {(total_1ep+dl_sec)/3600:.1f} h")

# Recommended step count
RECOMMENDED_STEPS = min(steps_1ep * 2, 20000)
recommended_time  = prep_sec + RECOMMENDED_STEPS * s_per_step + (RECOMMENDED_STEPS//EVAL_FREQ) * eval_run_sec
print(f"\n  Recommended training steps   : {RECOMMENDED_STEPS:,} (~2 epochs)")
print(f"  Recommended total time       : {recommended_time/3600:.1f} h (no download)")

print(f"\n  GPU VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB total")
print(f"  Allocated now: {torch.cuda.memory_allocated(0)/1e6:.0f}MB")
print(f"  Reserved  now: {torch.cuda.memory_reserved(0)/1e6:.0f}MB")
print("="*65)
