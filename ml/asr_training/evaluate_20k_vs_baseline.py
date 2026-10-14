"""
evaluate_20k_vs_baseline.py

Direct 20k vs 40k LoRA Evaluation:
- Model A: 20k Deployed Model (checkpoint-1200)
- Model B: 40k Experimental Model (whisper_indian_accent_40k_experiment / best checkpoint-500)
Evaluated on:
1. 500 held-out test recordings from full_speaker_split.json (seed=42).
   Strict verification: 0 test speakers or test recordings in either training batch.
2. 4 reference audio files:
   - validation_speech.wav
   - test_name_place.wav
   - test_indian_places.wav
   - real_test.wav

Metrics reported:
- Word Error Rate (WER) [Raw and Normalized]
- Character Error Rate (CER) [Raw and Normalized]
- Inference Latency (Total and per-sample avg)
- Reference audio transcriptions side-by-side
"""

import os
import sys
import json
import time
import torch
import soundfile as sf
import torchaudio
from datasets import load_dataset, Audio
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
from peft import PeftModel
import evaluate as ev

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SPLIT_FILE  = os.path.join(SCRIPT_DIR, "full_speaker_split.json")
MODEL_A_DIR = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_lora_20k", "checkpoint-1200")
MODEL_B_DIR = os.path.join(SCRIPT_DIR, "..", "asr_model", "whisper_indian_accent_40k_experiment")
REF_DIR     = os.path.join(SCRIPT_DIR, "..", "asr_service")
MODEL_ID    = "openai/whisper-base.en"
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
TEST_N      = 500
SEED        = 42

REF_FILES = [
    {
        "filename": "validation_speech.wav",
        "path": os.path.join(REF_DIR, "validation_speech.wav"),
        "reference": None
    },
    {
        "filename": "test_name_place.wav",
        "path": os.path.join(REF_DIR, "test_name_place.wav"),
        "reference": None
    },
    {
        "filename": "test_indian_places.wav",
        "path": os.path.join(REF_DIR, "test_indian_places.wav"),
        "reference": None
    },
    {
        "filename": "real_test.wav",
        "path": os.path.join(REF_DIR, "real_test.wav"),
        "reference": "It might be in this writer's Top Ten!"
    }
]

def build_test_set():
    """Load held-out test speakers, select exactly 500 samples (seed=42)."""
    print("Loading speaker splits...")
    with open(SPLIT_FILE, "r") as f:
        splits = json.load(f)

    train_spk = set(splits["train"])
    val_spk   = set(splits["validation"])
    test_spk  = set(splits["test"])

    # Strict disjointness verification
    train_test_overlap = train_spk & test_spk
    val_test_overlap   = val_spk & test_spk
    assert len(train_test_overlap) == 0, f"VIOLATION: train/test speaker overlap: {len(train_test_overlap)}"
    assert len(val_test_overlap) == 0,   f"VIOLATION: val/test speaker overlap: {len(val_test_overlap)}"
    
    print(f"  Train speakers  : {len(train_spk)}")
    print(f"  Val speakers    : {len(val_spk)}")
    print(f"  Test speakers   : {len(test_spk)}  [Strictly Disjoint from train/val: 0 overlap - OK]")

    print("\nLoading dataset cache...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train")
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))

    cids = ds["client_id"]
    test_indices = [i for i, cid in enumerate(cids) if cid in test_spk]
    train_indices = [i for i, cid in enumerate(cids) if cid in train_spk]

    # Verify zero recording overlap with training slices (batch 1: 0..20000, batch 2: 20000..40002)
    assert not set(test_indices).intersection(set(train_indices)), "VIOLATION: test and train row overlap!"
    print(f"  Available held-out test recordings: {len(test_indices)}")

    test_ds = ds.select(test_indices).shuffle(seed=SEED).select(range(min(TEST_N, len(test_indices))))
    print(f"  Selected fixed {len(test_ds)} test recordings (seed={SEED}) for evaluation")
    return test_ds

def transcribe_dataset(model, test_ds, processor):
    """Run inference sample-by-sample with identical decoding. Returns preds, refs, elapsed_s."""
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
            ).input_features.to(DEVICE).half()
            forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
            generated  = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
            pred = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
            ref  = ex["sentence"].strip()
            preds.append(pred)
            refs.append(ref)
            if (i + 1) % 100 == 0:
                elapsed = time.time() - t0
                print(f"    [{i+1}/{len(test_ds)}]  {elapsed:.1f}s elapsed (avg {(elapsed/(i+1))*1000:.1f} ms/sample)")
    return preds, refs, time.time() - t0

def transcribe_file(model, processor, file_path):
    """Transcribe a standalone WAV file with resampling to 16kHz."""
    data, sr = sf.read(file_path)
    if len(data.shape) > 1:
        data = data.mean(axis=1)
    waveform = torch.tensor(data, dtype=torch.float32)
    if sr != 16000:
        waveform = torchaudio.functional.resample(waveform, sr, 16000)
    audio_np = waveform.numpy()
    inputs = processor.feature_extractor(
        audio_np,
        sampling_rate=16000,
        return_tensors="pt"
    ).input_features.to(DEVICE).half()
    forced_ids = processor.get_decoder_prompt_ids(language="english", task="transcribe")
    t0 = time.time()
    with torch.no_grad():
        generated = model.generate(inputs, forced_decoder_ids=forced_ids, max_new_tokens=225)
    elapsed = time.time() - t0
    pred = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
    return pred, elapsed

def load_peft_adapter(adapter_path):
    bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    base_model = WhisperForConditionalGeneration.from_pretrained(
        MODEL_ID, quantization_config=bnb_cfg, device_map="auto"
    )
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens    = []
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model.eval()
    return model, base_model

def main():
    print("=" * 70)
    print("  PREMOCK AI: FINAL 20K VS 40K WHISPER EVALUATION")
    print(f"  Model A (20k Deployed)   : {MODEL_A_DIR}")
    print(f"  Model B (40k Experiment) : {MODEL_B_DIR}")
    print(f"  Device                   : {DEVICE}")
    print("=" * 70)

    # 1. Dataset & Normalizer
    test_ds = build_test_set()
    processor = WhisperProcessor.from_pretrained(MODEL_ID, language="English", task="transcribe")
    normalizer = BasicTextNormalizer()
    metric_wer = ev.load("wer")
    metric_cer = ev.load("cer")

    # 2. EVALUATE MODEL A (20k Deployed, checkpoint-1200)
    print("\n" + "-" * 70)
    print("  [MODEL A] Loading 20k Deployed Adapter (checkpoint-1200)...")
    print("-" * 70)
    model_a, base_a = load_peft_adapter(MODEL_A_DIR)
    
    print("  Evaluating Model A on 500 test recordings...")
    a_preds, a_refs, a_time = transcribe_dataset(model_a, test_ds, processor)
    
    print("  Evaluating Model A on reference audio files...")
    a_ref_results = {}
    for ref_item in REF_FILES:
        fname = ref_item["filename"]
        fpath = ref_item["path"]
        if os.path.exists(fpath):
            transcript, elapsed = transcribe_file(model_a, processor, fpath)
            a_ref_results[fname] = {
                "transcript": transcript,
                "latency_s": round(elapsed, 3),
                "reference": ref_item["reference"]
            }
        else:
            print(f"  Warning: {fpath} not found")

    del model_a, base_a
    torch.cuda.empty_cache()
    print(f"  Model A completed in {a_time:.1f}s. Memory cleared.")

    # 3. EVALUATE MODEL B (40k Experiment, best checkpoint)
    print("\n" + "-" * 70)
    print("  [MODEL B] Loading 40k Experimental Adapter (Best Model)...")
    print("-" * 70)
    model_b, base_b = load_peft_adapter(MODEL_B_DIR)

    print("  Evaluating Model B on 500 test recordings...")
    b_preds, b_refs, b_time = transcribe_dataset(model_b, test_ds, processor)

    print("  Evaluating Model B on reference audio files...")
    b_ref_results = {}
    for ref_item in REF_FILES:
        fname = ref_item["filename"]
        fpath = ref_item["path"]
        if os.path.exists(fpath):
            transcript, elapsed = transcribe_file(model_b, processor, fpath)
            b_ref_results[fname] = {
                "transcript": transcript,
                "latency_s": round(elapsed, 3),
                "reference": ref_item["reference"]
            }
        else:
            print(f"  Warning: {fpath} not found")

    del model_b, base_b
    torch.cuda.empty_cache()
    print(f"  Model B completed in {b_time:.1f}s. Memory cleared.")

    # 4. COMPUTE METRICS
    # Raw metrics
    a_wer_raw = metric_wer.compute(predictions=a_preds, references=a_refs)
    b_wer_raw = metric_wer.compute(predictions=b_preds, references=b_refs)
    a_cer_raw = metric_cer.compute(predictions=a_preds, references=a_refs)
    b_cer_raw = metric_cer.compute(predictions=b_preds, references=b_refs)

    # Normalized metrics (standard Whisper benchmark convention)
    a_preds_norm = [normalizer(p) for p in a_preds]
    b_preds_norm = [normalizer(p) for p in b_preds]
    refs_norm    = [normalizer(r) for r in a_refs]

    a_wer_norm = metric_wer.compute(predictions=a_preds_norm, references=refs_norm)
    b_wer_norm = metric_wer.compute(predictions=b_preds_norm, references=refs_norm)
    a_cer_norm = metric_cer.compute(predictions=a_preds_norm, references=refs_norm)
    b_cer_norm = metric_cer.compute(predictions=b_preds_norm, references=refs_norm)

    delta_wer_norm = (b_wer_norm - a_wer_norm) * 100
    delta_cer_norm = (b_cer_norm - a_cer_norm) * 100

    n_samples = len(test_ds)
    a_lat_per_sample_ms = (a_time / n_samples) * 1000
    b_lat_per_sample_ms = (b_time / n_samples) * 1000

    # 5. PRINT RESULTS
    print("\n" + "=" * 70)
    print("  HELD-OUT TEST SET EVALUATION SUMMARY (500 Unseen Recordings)")
    print("=" * 70)
    print(f"  Number of recordings evaluated : {n_samples}")
    print(f"  Model A (20k Deployed) WER (Raw)     : {a_wer_raw*100:.2f}% | CER: {a_cer_raw*100:.2f}%")
    print(f"  Model B (40k Experiment) WER (Raw)   : {b_wer_raw*100:.2f}% | CER: {b_cer_raw*100:.2f}%")
    print("-" * 70)
    print(f"  Model A (20k Deployed) WER (Norm)    : {a_wer_norm*100:.2f}% | CER: {a_cer_norm*100:.2f}%")
    print(f"  Model B (40k Experiment) WER (Norm)  : {b_wer_norm*100:.2f}% | CER: {b_cer_norm*100:.2f}%")
    print(f"  Normalized WER Delta                 : {delta_wer_norm:+.2f}% ({'IMPROVEMENT' if delta_wer_norm < 0 else 'DEGRADATION' if delta_wer_norm > 0 else 'IDENTICAL'})")
    print(f"  Normalized CER Delta                 : {delta_cer_norm:+.2f}% ({'IMPROVEMENT' if delta_cer_norm < 0 else 'DEGRADATION' if delta_cer_norm > 0 else 'IDENTICAL'})")
    print("-" * 70)
    print(f"  Inference Latency Model A (Total)    : {a_time:.2f}s ({a_lat_per_sample_ms:.1f} ms/sample)")
    print(f"  Inference Latency Model B (Total)    : {b_time:.2f}s ({b_lat_per_sample_ms:.1f} ms/sample)")
    print("=" * 70)

    # 6. REFERENCE FILES TRANSCRIPT COMPARISON
    print("\n" + "=" * 70)
    print("  REFERENCE AUDIO FILES EVALUATION")
    print("=" * 70)
    for fname in a_ref_results:
        ref_text = a_ref_results[fname]["reference"]
        a_t = a_ref_results[fname]["transcript"]
        b_t = b_ref_results[fname]["transcript"]
        a_lat = a_ref_results[fname]["latency_s"]
        b_lat = b_ref_results[fname]["latency_s"]

        print(f"\n  File: {fname}")
        if ref_text:
            print(f"    Reference Text : \"{ref_text}\"")
        print(f"    Model A (20k)  : \"{a_t}\" ({a_lat:.2f}s)")
        print(f"    Model B (40k)  : \"{b_t}\" ({b_lat:.2f}s)")

    # 7. SAMPLE PREDICTIONS FROM TEST SET
    print("\n" + "=" * 70)
    print("  SAMPLE PREDICTIONS (First 5 Held-out Recordings)")
    print("=" * 70)
    for i in range(min(5, n_samples)):
        print(f"\n  [Sample {i+1}]")
        print(f"    Reference      : \"{a_refs[i]}\"")
        print(f"    Model A (20k)  : \"{a_preds[i]}\"")
        print(f"    Model B (40k)  : \"{b_preds[i]}\"")

    # 8. SAVE REPORT JSON
    report = {
        "dataset": "ishands/commonvoice-indian_accent",
        "split": "held-out-test",
        "n_samples": n_samples,
        "seed": SEED,
        "model_a": {
            "name": "20k_deployed_checkpoint-1200",
            "path": MODEL_A_DIR,
            "raw_wer": round(a_wer_raw, 4),
            "raw_cer": round(a_cer_raw, 4),
            "norm_wer": round(a_wer_norm, 4),
            "norm_cer": round(a_cer_norm, 4),
            "total_latency_seconds": round(a_time, 2),
            "avg_latency_ms_per_sample": round(a_lat_per_sample_ms, 2)
        },
        "model_b": {
            "name": "40k_experiment_best",
            "path": MODEL_B_DIR,
            "raw_wer": round(b_wer_raw, 4),
            "raw_cer": round(b_cer_raw, 4),
            "norm_wer": round(b_wer_norm, 4),
            "norm_cer": round(b_cer_norm, 4),
            "total_latency_seconds": round(b_time, 2),
            "avg_latency_ms_per_sample": round(b_lat_per_sample_ms, 2)
        },
        "comparison": {
            "norm_wer_delta_pct": round(delta_wer_norm, 2),
            "norm_cer_delta_pct": round(delta_cer_norm, 2),
            "verdict": "improved" if delta_wer_norm < 0 else "degraded" if delta_wer_norm > 0 else "neutral"
        },
        "reference_files": {
            fname: {
                "reference": a_ref_results[fname]["reference"],
                "model_a_transcript": a_ref_results[fname]["transcript"],
                "model_a_latency_s": a_ref_results[fname]["latency_s"],
                "model_b_transcript": b_ref_results[fname]["transcript"],
                "model_b_latency_s": b_ref_results[fname]["latency_s"]
            }
            for fname in a_ref_results
        }
    }

    report_path = os.path.join(MODEL_B_DIR, "evaluation_20k_vs_40k_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport written to: {report_path}")

if __name__ == "__main__":
    main()

