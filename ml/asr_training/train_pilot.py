import os
import torch
from datasets import load_from_disk
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig
import evaluate
import numpy as np

def train_pilot():
    print("Loading metrics...")
    metric = evaluate.load("wer")

    # Paths
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "processed_data_pilot")
    model_id = "openai/whisper-base.en"
    out_model_dir = os.path.join(base_dir, "../asr_model/pilot_model")

    print(f"Loading processor for {model_id}...")
    processor = WhisperProcessor.from_pretrained(model_id, language="English", task="transcribe")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        # Replace -100 with pad_token_id
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        
        pred_str = processor.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.batch_decode(label_ids, skip_special_tokens=True)
        
        wer = metric.compute(predictions=pred_str, references=label_str)
        return {"wer": wer}

    print("Loading prepared dataset...")
    dataset = load_from_disk(data_dir)

    def prepare_dataset_for_model(batch):
        audio = batch["audio"]
        batch["input_features"] = processor.feature_extractor(audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
        batch["labels"] = processor.tokenizer(batch["sentence"]).input_ids
        return batch

    print("Extracting features and tokenizing...")
    dataset = dataset.map(prepare_dataset_for_model, remove_columns=dataset["train"].column_names, num_proc=1)

    # Load model in 8-bit
    print("Loading model in 8-bit with LoRA...")
    bnb_config = BitsAndBytesConfig(load_in_8bit=True)

    model = WhisperForConditionalGeneration.from_pretrained(
        model_id, 
        quantization_config=bnb_config,
        device_map="auto"
    )
    
    model.config.forced_decoder_ids = None
    model.config.suppress_tokens = []

    # Prepare for PEFT
    model = prepare_model_for_kbit_training(model)
    config = LoraConfig(
        r=8, 
        lora_alpha=16, 
        target_modules=["q_proj", "v_proj"], 
        lora_dropout=0.05, 
        bias="none"
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    # Data collator
    import torch
    from dataclasses import dataclass
    from typing import Any, Dict, List, Union

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

    # Calculate max steps based on memory constraints
    # With 100 samples, batch_size=2, grad_accum=4, that's 8 samples per step
    # 100/8 = 12.5 steps per epoch. We can train for 4 epochs (50 steps)
    
    training_args = Seq2SeqTrainingArguments(
        output_dir=out_model_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        warmup_steps=10,
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
        args=training_args,
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    print("Starting pilot training...")
    trainer.train()

    print(f"Training complete. Saving model to {out_model_dir}")
    trainer.save_model()
    processor.save_pretrained(out_model_dir)

if __name__ == "__main__":
    train_pilot()
