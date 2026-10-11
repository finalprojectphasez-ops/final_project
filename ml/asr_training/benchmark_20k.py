import time, os, torch
from datasets import load_dataset
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor,
    Seq2SeqTrainer, Seq2SeqTrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dataclasses import dataclass
from typing import Any, Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID   = "openai/whisper-base.en"
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
BENCH_STEPS = 10 

print(f"Device: {DEVICE}")
print("="*65)

processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")
print("Loading train split for benchmarking...")
from datasets import Audio
dataset = load_dataset("ishands/commonvoice-indian_accent", split="train")
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

def prep(batch):
    audio = batch["audio"]
    batch["input_features"] = processor.feature_extractor(
        audio["array"], sampling_rate=audio["sampling_rate"]
    ).input_features[0]
    batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
    return batch

print("Measuring feature extraction speed...")
sample_20 = dataset.select(range(20))
t0 = time.perf_counter()
sample_20 = sample_20.map(prep, remove_columns=sample_20.column_names, num_proc=1, desc="Prep 20")
feat_time_20 = time.perf_counter() - t0
feat_per_sample = feat_time_20 / 20.0

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

torch.cuda.reset_peak_memory_stats()
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

# We need 200 samples to feed batch=2, grad accum=8 for 10 steps (160 samples total used)
print("Mapping 200 samples for train benchmark...")
bench_ds = dataset.select(range(200)).map(prep, remove_columns=dataset.column_names, num_proc=1, desc="Prep 200")

args = Seq2SeqTrainingArguments(
    output_dir=os.path.join(SCRIPT_DIR, "tmp_bench_20k"),
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
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
    train_dataset=bench_ds,
    data_collator=data_collator,
    tokenizer=processor.feature_extractor,
)

print("Starting 10-step benchmark training run...")
t0 = time.perf_counter()
trainer.train()
train_elapsed = time.perf_counter() - t0
s_per_step  = train_elapsed / BENCH_STEPS

peak_mem = torch.cuda.max_memory_allocated() / 1e9

print("Measuring inference generation speed...")
val_raw = dataset.select(range(200, 220))
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
s_per_eval = (time.perf_counter() - t0) / 20.0

print(f"\n[BENCHMARK RESULTS]")
print(f"Peak VRAM        : {peak_mem:.2f} GB")
print(f"Time per step    : {s_per_step:.2f} s")
print(f"Time per eval    : {s_per_eval:.2f} s")
print(f"Time per prep    : {feat_per_sample:.3f} s")

print("\n[ESTIMATES FOR 20k SAMPLES]")
prep_sec = feat_per_sample * 20000
print(f"Prep (20k)        : {prep_sec/60:.1f} min")
train_sec = 1250 * s_per_step
print(f"Train (1250 steps): {train_sec/60:.1f} min")
# 3 evals * 200 samples (step 400, 800, 1200)
eval_sec = 3 * 200 * s_per_eval
print(f"Periodic Eval     : {eval_sec/60:.1f} min")
# Final comparison (500 samples * 2 models)
comp_sec = 2 * 500 * s_per_eval
print(f"Final Comparison  : {comp_sec/60:.1f} min")
total_sec = prep_sec + train_sec + eval_sec + comp_sec
print(f"TOTAL TIME        : {total_sec/60:.1f} min ({total_sec/3600:.2f} hrs)")
