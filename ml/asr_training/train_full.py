import os
import json
import torch
import evaluate
import numpy as np
from datasets import load_dataset, Audio, DatasetDict
from transformers import (
    WhisperForConditionalGeneration, WhisperProcessor,
    Seq2SeqTrainer, Seq2SeqTrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from dataclasses import dataclass
from typing import Any, Dict, List, Union

def train_full():
    print("="*65)
    print("  FULL-DATASET ASR TRAINING SCRIPT")
    print("="*65)
    
    base_dir = os.path.dirname(__file__)
    split_file = os.path.join(base_dir, "full_speaker_split.json")
    out_model_dir = os.path.join(base_dir, "..", "asr_model", "whisper_indian_accent_lora")
    
    if not os.path.exists(split_file):
        raise FileNotFoundError(f"Split file not found: {split_file}")
        
    with open(split_file, "r") as f:
        split_map = json.load(f)
        
    train_speakers = set(split_map["train"])
    val_speakers = set(split_map["validation"])
    test_speakers = set(split_map["test"])
    
    print("Loading full dataset from hub...")
    dataset = load_dataset("ishands/commonvoice-indian_accent", split="train", trust_remote_code=True)
    
    print("Filtering and resampling...")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    dataset = dataset.filter(lambda x: x["sentence"] is not None and len(x["sentence"].strip()) > 0)
    
    print("Applying speaker-safe split...")
    def get_split(cid):
        if cid in train_speakers: return "train"
        if cid in val_speakers: return "validation"
        return "test"
        
    def add_split_col(batch):
        batch["split_group"] = [get_split(cid) for cid in batch["client_id"]]
        return batch
        
    dataset = dataset.map(add_split_col, batched=True, batch_size=1000, num_proc=4)
    
    train_ds = dataset.filter(lambda x: x["split_group"] == "train", num_proc=4)
    val_ds = dataset.filter(lambda x: x["split_group"] == "validation", num_proc=4)
    test_ds = dataset.filter(lambda x: x["split_group"] == "test", num_proc=4)
    
    print(f"Splits prepared - Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")
    
    model_id = "openai/whisper-base.en"
    print(f"Loading processor for {model_id}...")
    processor = WhisperProcessor.from_pretrained(model_id, language="English", task="transcribe")
    
    def prepare_dataset_for_model(batch):
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch
    
    print("Extracting features and tokenizing (this will take time)...")
    cols_to_remove = train_ds.column_names
    train_ds = train_ds.map(prepare_dataset_for_model, remove_columns=cols_to_remove, num_proc=4)
    val_ds = val_ds.map(prepare_dataset_for_model, remove_columns=cols_to_remove, num_proc=4)
    test_ds = test_ds.map(prepare_dataset_for_model, remove_columns=cols_to_remove, num_proc=4)
    
    # We evaluate on a fixed subset of 500 validation samples
    val_subset_size = min(500, len(val_ds))
    val_subset = val_ds.shuffle(seed=42).select(range(val_subset_size))
    print(f"Evaluation will run on a fixed subset of {val_subset_size} samples.")

    print("Loading model in 8-bit with LoRA...")
    bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    model = WhisperForConditionalGeneration.from_pretrained(
        model_id, 
        quantization_config=bnb_config,
        device_map="auto"
    )
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []
    
    model = prepare_model_for_kbit_training(model)
    config = LoraConfig(
        r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"], 
        lora_dropout=0.05, bias="none"
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    @dataclass
    class DataCollatorSpeechSeq2SeqWithPadding:
        processor: Any
        def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
            input_features = [{"input_features": feature["input_features"]} for feature in features]
            batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
            label_features = [{"input_ids": feature["labels"]} for feature in features]
            labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
            labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
            if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
                labels = labels[:, 1:]
            batch["labels"] = labels
            return batch

    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)
    metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
        wer = metric.compute(predictions=pred_str, references=label_str)
        return {"wer": wer}

    # Configuration based on hardware limits
    # 1 epoch = (len(train_ds) / effective_batch_size) steps
    eff_batch_size = 2 * 4  # batch_size * grad_accum
    steps_per_epoch = len(train_ds) // eff_batch_size
    
    training_args = Seq2SeqTrainingArguments(
        output_dir=out_model_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        warmup_steps=500,
        max_steps=steps_per_epoch,  # ~1 epoch
        gradient_checkpointing=True,
        fp16=True,
        eval_strategy="steps",
        per_device_eval_batch_size=2,
        predict_with_generate=True,
        generation_max_length=225,
        save_steps=1000,
        eval_steps=2500,
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="wer",
        greater_is_better=False,
        remove_unused_columns=False,
        save_total_limit=3,
        dataloader_num_workers=4,
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train_ds,
        eval_dataset=val_subset,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    import glob
    checkpoints = glob.glob(os.path.join(out_model_dir, "checkpoint-*"))
    if checkpoints:
        print(f"Resuming from checkpoint in {out_model_dir}")
        trainer.train(resume_from_checkpoint=True)
    else:
        print("Starting full training from scratch...")
        trainer.train()

    print(f"Training complete. Saving final best model to {out_model_dir}")
    trainer.save_model()
    processor.save_pretrained(out_model_dir)

if __name__ == "__main__":
    train_full()
