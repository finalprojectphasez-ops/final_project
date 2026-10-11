import os, sys, json, torch
from datasets import load_dataset, Audio
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor,
    Seq2SeqTrainer, Seq2SeqTrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dataclasses import dataclass
from typing import Any, Dict, List
import evaluate as ev

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SPLIT_FILE = os.path.join(SCRIPT_DIR, "full_speaker_split.json")
OUT_DIR    = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_lora_20k")
MODEL_ID   = "openai/whisper-base.en"

# Safety memory checks
def print_memory_stats(step_name=""):
    if torch.cuda.is_available():
        allocated = torch.cuda.max_memory_allocated() / 1e9
        reserved = torch.cuda.max_memory_reserved() / 1e9
        print(f"[{step_name}] Peak CUDA Memory - Allocated: {allocated:.2f} GB | Reserved: {reserved:.2f} GB")

def main():
    print("="*65)
    print("Starting 20,000-sample Whisper LoRA Fine-Tuning")
    print("="*65)

    # 1. Load splits
    if not os.path.exists(SPLIT_FILE):
        print("Error: full_speaker_split.json not found!")
        sys.exit(1)

    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)

    train_spk = set(splits["train"])
    val_spk   = set(splits["validation"])

    # 2. Load dataset
    print("Loading dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    # 3. Filter safely
    print("Filtering by speaker splits...")
    train_ds = ds.filter(lambda x: x["client_id"] in train_spk, num_proc=4)
    val_ds   = ds.filter(lambda x: x["client_id"] in val_spk, num_proc=4)

    # 4. Subset strictly to 20,000 train, 200 val
    print("Selecting fixed subsets (seed=42)...")
    train_ds = train_ds.shuffle(seed=42).select(range(min(20000, len(train_ds))))
    val_ds   = val_ds.shuffle(seed=42).select(range(min(200, len(val_ds))))

    print(f"Final subsets -> Train: {len(train_ds)} | Val: {len(val_ds)}")

    # 5. Processor & Preprocessing
    processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")

    def prep(batch):
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    print("Extracting features (this will take ~30-40 min)...")
    train_ds = train_ds.map(prep, remove_columns=train_ds.column_names, num_proc=4)
    val_ds   = val_ds.map(prep, remove_columns=val_ds.column_names, num_proc=4)

    print("Filtering out sequences exceeding Whisper's 448 token limit...")
    # num_proc=1 to avoid RAM MemoryError: multi-proc loads full audio arrays per worker
    train_ds = train_ds.filter(lambda x: len(x["labels"]) <= 448, num_proc=1)
    val_ds   = val_ds.filter(lambda x: len(x["labels"]) <= 448, num_proc=1)
    print(f"After length filter -> Train: {len(train_ds)} | Val: {len(val_ds)}")

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

    # 6. Model Init
    print("Initializing model...")
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

    print_memory_stats("Post-Model Load")

    # 7. Training Args
    args = Seq2SeqTrainingArguments(
        output_dir=OUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        warmup_steps=50,
        max_steps=1250,
        gradient_checkpointing=True,
        fp16=True,
        eval_strategy="steps",
        eval_steps=400,
        save_strategy="steps",
        save_steps=400,
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
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    # 8. Resume logic
    resume_from_checkpoint = False
    if os.path.exists(OUT_DIR):
        chkpts = [d for d in os.listdir(OUT_DIR) if d.startswith("checkpoint")]
        if len(chkpts) > 0:
            resume_from_checkpoint = True
            print(f"Found checkpoints in {OUT_DIR}, resuming from latest...")

    # 9. Train Safely
    print("Starting training...")
    try:
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        print("Training finished successfully!")
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n[ERROR] OOM DETECTED: {e}")
            print("Training stopped safely due to OOM. Latest checkpoint preserved.")
        else:
            raise e

    # 10. Save Final Model
    trainer.save_model(OUT_DIR)
    print(f"Final model saved to: {OUT_DIR}")
    print_memory_stats("Post-Training")

if __name__ == "__main__":
    main()
