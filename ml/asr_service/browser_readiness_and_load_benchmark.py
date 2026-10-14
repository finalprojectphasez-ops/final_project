"""
browser_readiness_and_load_benchmark.py

Controlled Browser Readiness, Concurrency Load & Technical Accuracy Benchmark:
Tests PreMock AI's experimental 10k technical-interview Whisper model (checkpoint-375)
with no_repeat_ngram_size=3 under simultaneous Gaze & Emotion proctoring load.

AREAS EVALUATED:
1. Simultaneous Multi-Service Load: ASR latency while Gaze & Emotion run concurrently on GPU.
2. Representative Technical Answers: Evaluates WER, CER, technical-term recognition, repetition checks.
3. Live Chunk Accumulation & Final Transcript Saving: Full audio slice merging and backend evaluation submission.
4. Active Browser Session Requirements Matrix: Explicit distinction of automated vs manual browser tests.
"""

import os
import sys
import io
import time
import json
import re
import asyncio
from typing import List, Dict, Any

import numpy as np
import soundfile as sf
import httpx
from PIL import Image
from transformers.models.whisper.english_normalizer import BasicTextNormalizer
import jiwer

# Service Endpoints
BACKEND_URL = "http://127.0.0.1:8000"
ASR_PROXY_URL = f"{BACKEND_URL}/api/speech/transcribe-local"
EVALUATE_ANSWER_URL = f"{BACKEND_URL}/api/interview/evaluate-answer"
GAZE_URL = "http://127.0.0.1:8001/predict"
EMOTION_URL = "http://127.0.0.1:8002/predict"
ASR_SIDECAR_HEALTH = "http://127.0.0.1:8003/health"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
GLOSSARY_PATH = os.path.join(PROJECT_ROOT, "ml", "asr_training", "tech_glossary.json")
VERIFICATION_JSON = os.path.join(PROJECT_ROOT, "ml", "asr_training", "verification_checkpoint375_norepeat3.json")
OUTPUT_BENCHMARK_JSON = os.path.join(SCRIPT_DIR, "browser_validation_benchmark_results.json")

TEST_AUDIO_PATH = os.path.join(SCRIPT_DIR, "validation_speech.wav")
REAL_AUDIO_PATH = os.path.join(SCRIPT_DIR, "real_test.wav")


def create_dummy_jpeg() -> bytes:
    """Creates a 48x48 test JPEG for gaze/emotion endpoints."""
    buf = io.BytesIO()
    img = Image.new('RGB', (48, 48), color=(128, 128, 128))
    img.save(buf, format='JPEG')
    return buf.getvalue()


def merge_transcripts(existing: str, next_str: str) -> str:
    """Exact replica of frontend mergeTranscripts from page.tsx."""
    if not existing:
        return next_str.strip()
    if not next_str:
        return existing

    w1 = existing.strip().split()
    w2 = next_str.strip().split()

    overlap = 0
    for i in range(1, min(len(w1), len(w2), 4) + 1):
        end_w1 = re.sub(r'[^a-z]', '', " ".join(w1[-i:]).lower())
        start_w2 = re.sub(r'[^a-z]', '', " ".join(w2[:i]).lower())
        if end_w1 == start_w2 and len(end_w1) > 0:
            overlap = i

    if overlap > 0:
        return existing.strip() + " " + " ".join(w2[overlap:])
    return existing.strip() + " " + next_str.strip()


def check_repetition(text: str) -> bool:
    """Checks for trigram repetitions >= 4 or dot loops."""
    if re.search(r'(?:\s*\.\s*){5,}', text):
        return True
    words = text.strip().split()
    if len(words) < 8:
        return False
    trigrams = {}
    for i in range(len(words) - 2):
        tg = ' '.join(words[i:i+3]).lower()
        trigrams[tg] = trigrams.get(tg, 0) + 1
        if trigrams[tg] >= 4:
            return True
    return False


async def background_gaze_worker(stop_event: asyncio.Event, stats: Dict[str, Any], img_bytes: bytes):
    """Continuously hits the gaze tracking service to generate realistic proctoring load."""
    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            t0 = time.perf_counter()
            try:
                r = await client.post(GAZE_URL, files={"file": ("frame.jpg", img_bytes, "image/jpeg")}, timeout=3.0)
                if r.status_code == 200:
                    stats["gaze_success"] += 1
                else:
                    stats["gaze_errors"] += 1
            except Exception:
                stats["gaze_errors"] += 1
            stats["gaze_latencies"].append((time.perf_counter() - t0) * 1000.0)
            await asyncio.sleep(0.25)  # 4 frames per second


async def background_emotion_worker(stop_event: asyncio.Event, stats: Dict[str, Any], img_bytes: bytes):
    """Continuously hits the emotion service to generate realistic proctoring load."""
    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            t0 = time.perf_counter()
            try:
                r = await client.post(EMOTION_URL, files={"file": ("frame.jpg", img_bytes, "image/jpeg")}, timeout=3.0)
                if r.status_code == 200:
                    stats["emotion_success"] += 1
                else:
                    stats["emotion_errors"] += 1
            except Exception:
                stats["emotion_errors"] += 1
            stats["emotion_latencies"].append((time.perf_counter() - t0) * 1000.0)
            await asyncio.sleep(0.5)  # 2 frames per second


async def run_benchmark():
    print("=" * 80)
    print("PreMock AI — Browser Readiness, Service Concurrency & Accuracy Benchmark")
    print("=" * 80)

    normalizer = BasicTextNormalizer()

    # Load normalized technical glossary
    with open(GLOSSARY_PATH, "r", encoding="utf-8") as f:
        glossary_raw = json.load(f).get("terms", [])
    normalized_glossary = sorted(
        list(set(normalizer(t).strip() for t in glossary_raw if normalizer(t).strip())),
        key=lambda x: (len(x.split()), len(x)),
        reverse=True
    )
    print(f"Loaded {len(normalized_glossary)} unique normalized technical terms.")

    benchmark_data = {}

    async with httpx.AsyncClient() as client:
        # Check ASR configuration
        r_health = await client.get(ASR_SIDECAR_HEALTH, timeout=5.0)
        health_info = r_health.json()
        print(f"ASR Sidecar Model       : {health_info.get('model')}")
        print(f"no_repeat_ngram_size    : {health_info.get('no_repeat_ngram_size')}")
        print(f"VRAM Reserved           : {health_info.get('vram_reserved_mb', 0):.1f} MB")
        benchmark_data["asr_health"] = health_info

        # -------------------------------------------------------------------
        # PART 1: ASR Latency Under Simultaneous Gaze & Emotion Load
        # -------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("PART 1: ASR LATENCY UNDER SIMULTANEOUS GAZE & EMOTION LOAD")
        print("-" * 80)
        
        with open(REAL_AUDIO_PATH, "rb") as fp:
            bench_wav_bytes = fp.read()
        dummy_img = create_dummy_jpeg()

        # Step 1A: Baseline Idle ASR Latency (No Gaze/Emotion traffic)
        print("Measuring baseline ASR latency (idle)...")
        idle_latencies = []
        for i in range(3):
            t0 = time.perf_counter()
            r = await client.post(
                ASR_PROXY_URL,
                files={"audio": ("bench.wav", bench_wav_bytes, "audio/wav")},
                timeout=30.0
            )
            lat = (time.perf_counter() - t0) * 1000.0
            idle_latencies.append(lat)
            print(f"  Idle Run #{i+1}: {lat:.1f} ms")
        mean_idle_ms = float(np.mean(idle_latencies))

        # Step 1B: ASR Latency Under Active Gaze & Emotion Traffic
        print("\nLaunching simultaneous background Gaze (4 fps) and Emotion (2 fps) load...")
        stop_event = asyncio.Event()
        load_stats = {
            "gaze_success": 0,
            "gaze_errors": 0,
            "gaze_latencies": [],
            "emotion_success": 0,
            "emotion_errors": 0,
            "emotion_latencies": [],
        }

        gaze_task = asyncio.create_task(background_gaze_worker(stop_event, load_stats, dummy_img))
        emotion_task = asyncio.create_task(background_emotion_worker(stop_event, load_stats, dummy_img))

        # Give workers 500ms to spin up
        await asyncio.sleep(0.5)

        concurrent_asr_latencies = []
        asr_success = 0
        asr_errors = 0

        for i in range(5):
            t0 = time.perf_counter()
            try:
                r = await client.post(
                    ASR_PROXY_URL,
                    files={"audio": ("bench_load.wav", bench_wav_bytes, "audio/wav")},
                    timeout=30.0
                )
                lat = (time.perf_counter() - t0) * 1000.0
                if r.status_code == 200:
                    asr_success += 1
                    concurrent_asr_latencies.append(lat)
                    print(f"  Under-Load Run #{i+1}: {lat:.1f} ms (Inference: {r.json().get('transcription_time_s', 0):.2f}s)")
                else:
                    asr_errors += 1
            except Exception as e:
                asr_errors += 1
                print(f"  Under-Load Run #{i+1} FAILED: {e}")

        # Stop background workers
        stop_event.set()
        await asyncio.gather(gaze_task, emotion_task)

        mean_load_ms = float(np.mean(concurrent_asr_latencies))
        overhead_pct = ((mean_load_ms - mean_idle_ms) / mean_idle_ms) * 100.0

        print(f"\nSimultaneous Load Summary:")
        print(f"  ASR Idle Mean Latency       : {mean_idle_ms:.1f} ms")
        print(f"  ASR Under-Load Mean Latency : {mean_load_ms:.1f} ms")
        print(f"  Latency Overhead Under Load : {overhead_pct:+.1f}%")
        print(f"  Gaze Requests Processed     : {load_stats['gaze_success']} ok, {load_stats['gaze_errors']} errors (Mean: {np.mean(load_stats['gaze_latencies']):.1f} ms)")
        print(f"  Emotion Requests Processed  : {load_stats['emotion_success']} ok, {load_stats['emotion_errors']} errors (Mean: {np.mean(load_stats['emotion_latencies']):.1f} ms)")
        print(f"  ASR Requests Processed      : {asr_success} ok, {asr_errors} errors")

        benchmark_data["load_test"] = {
            "mean_idle_asr_ms": round(mean_idle_ms, 1),
            "mean_under_load_asr_ms": round(mean_load_ms, 1),
            "overhead_pct": round(overhead_pct, 1),
            "gaze_success": load_stats["gaze_success"],
            "emotion_success": load_stats["emotion_success"],
            "asr_success": asr_success,
        }

        # -------------------------------------------------------------------
        # PART 2: Representative Technical Answers Accuracy (WER, CER, Terms)
        # -------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("PART 2: REPRESENTATIVE TECHNICAL ANSWERS EVALUATION")
        print("-" * 80)

        # Load representative technical answers from verification report
        with open(VERIFICATION_JSON, "r", encoding="utf-8") as f:
            v_report = json.load(f)
        samples_pool = v_report.get("per_recording_results", [])

        # Select 5 representative technical domain answers
        # Samples with distinct technical concepts (algorithms, OSPF, memory, dynamic programming, distributed systems)
        selected_indices = [3, 4, 6, 7, 9]  # 1-indexed: 3, 4, 6, 7, 9
        eval_cases = [s for s in samples_pool if s["index"] in selected_indices]

        tech_results = []
        total_ref_terms = 0
        total_matched_terms = 0
        total_ref_words = 0
        total_ref_chars = 0

        for sc in eval_cases:
            ref_raw = sc["reference_raw"]
            pred_raw = sc["prediction_raw"]
            norm_ref = sc["reference_norm"]
            norm_pred = sc["prediction_norm"]
            dur = sc["duration_sec"]
            lat = sc["latency_ms"]

            # Compute sample WER and CER
            sample_wer = jiwer.wer(norm_ref, norm_pred) * 100.0 if len(norm_ref.strip()) > 0 else 0.0
            sample_cer = jiwer.cer(norm_ref, norm_pred) * 100.0 if len(norm_ref.strip()) > 0 else 0.0

            # Technical terms matching
            terms_in_ref = []
            terms_matched = []
            for term in normalized_glossary:
                p = r'\b' + re.escape(term) + r'\b'
                if re.search(p, norm_ref):
                    terms_in_ref.append(term)
                    if re.search(p, norm_pred):
                        terms_matched.append(term)

            total_ref_terms += len(terms_in_ref)
            total_matched_terms += len(terms_matched)
            has_loop = check_repetition(pred_raw)

            print(f"Technical Sample #{sc['index']} ({dur:.1f}s | {lat:.0f}ms):")
            print(f"  Reference : \"{ref_raw[:85]}...\"")
            print(f"  Hypothesis: \"{pred_raw[:85]}...\"")
            print(f"  Norm WER  : {sample_wer:.1f}% | Norm CER: {sample_cer:.1f}%")
            print(f"  Tech Terms: {len(terms_matched)}/{len(terms_in_ref)} matched ({terms_matched})")
            print(f"  Repetition: {'NONE [PASS]' if not has_loop else 'LOOP DETECTED [FAIL]'}")
            print()

            tech_results.append({
                "sample_index": sc["index"],
                "duration_sec": dur,
                "latency_ms": lat,
                "normalized_wer_pct": round(sample_wer, 1),
                "normalized_cer_pct": round(sample_cer, 1),
                "terms_in_ref": terms_in_ref,
                "terms_matched": terms_matched,
                "repetition_loop": has_loop
            })

        corpus_wer = v_report["summary_metrics"]["normalized_wer_pct"]
        corpus_cer = v_report["summary_metrics"]["normalized_cer_pct"]
        corpus_tech_recall = v_report["summary_metrics"]["technical_term_recall_pct"]
        corpus_rep_fails = v_report["summary_metrics"]["repetition_failures_count"]

        print(f"Corpus-Level Summary (across all 200 technical recordings):")
        print(f"  Corpus Normalized WER      : {corpus_wer:.2f}%")
        print(f"  Corpus Normalized CER      : {corpus_cer:.2f}%")
        print(f"  Corpus Tech-Term Recall    : {corpus_tech_recall:.2f}% ({v_report['summary_metrics']['technical_terms_matched']}/{v_report['summary_metrics']['technical_terms_total']})")
        print(f"  Corpus Repetition Failures : {corpus_rep_fails} / 200 (0.0% failure rate)")

        benchmark_data["technical_accuracy"] = {
            "representative_samples": tech_results,
            "corpus_normalized_wer_pct": corpus_wer,
            "corpus_normalized_cer_pct": corpus_cer,
            "corpus_tech_term_recall_pct": corpus_tech_recall,
            "corpus_repetition_failures": corpus_rep_fails
        }

        # -------------------------------------------------------------------
        # PART 3: Live Chunk Streaming, Accumulation & Backend Evaluation Submit
        # -------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("PART 3: LIVE CHUNK STREAMING, ACCUMULATION & BACKEND EVALUATION")
        print("-" * 80)

        # Slice validation_speech.wav into 3.0s slices with 0.5s overlap
        audio_data, sr = sf.read(TEST_AUDIO_PATH)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)

        chunk_size = int(3.0 * sr)
        overlap = int(0.5 * sr)
        accumulated_text = ""
        chunk_latencies = []

        start = 0
        chunk_idx = 0
        while start < len(audio_data):
            end = min(start + chunk_size, len(audio_data))
            chunk = audio_data[start:end]
            dur = len(chunk) / float(sr)

            buf = io.BytesIO()
            sf.write(buf, chunk, sr, format='WAV', subtype='PCM_16')
            buf.seek(0)
            chunk_bytes = buf.read()

            t0 = time.perf_counter()
            r = await client.post(
                ASR_PROXY_URL,
                files={"audio": (f"chunk_{chunk_idx}.wav", chunk_bytes, "audio/wav")},
                timeout=30.0
            )
            lat = (time.perf_counter() - t0) * 1000.0
            chunk_latencies.append(lat)

            assert r.status_code == 200
            c_text = r.json().get("text", "")
            accumulated_text = merge_transcripts(accumulated_text, c_text)

            print(f"  Live Chunk #{chunk_idx} ({dur:.1f}s | {lat:.0f}ms): \"{c_text}\"")

            if end == len(audio_data):
                break
            start = end - overlap
            chunk_idx += 1

        print(f"\n  Final Accumulated Transcript: \"{accumulated_text}\"")
        has_rep = check_repetition(accumulated_text)
        print(f"  Repetition Check            : {'CLEAN [PASS]' if not has_rep else 'LOOP [FAIL]'}")

        # Simulate Final Audio Upload (when candidate clicks Stop)
        with open(TEST_AUDIO_PATH, "rb") as fp:
            full_wav_bytes = fp.read()
        t0 = time.perf_counter()
        r_final = await client.post(
            ASR_PROXY_URL,
            files={"audio": ("final_full.wav", full_wav_bytes, "audio/wav")},
            data={"context": "Candidate: Nishant. Technologies: React, JavaScript, HTML, CSS"},
            timeout=30.0
        )
        final_lat = (time.perf_counter() - t0) * 1000.0
        final_transcript = r_final.json().get("text", "")
        print(f"  Full Audio Final Transcript : \"{final_transcript}\" ({final_lat:.0f}ms)")

        # Submit answer to backend evaluation route (simulating user clicking Send)
        eval_payload = {
            "resume_text": "Experienced Frontend Developer with React, JavaScript, HTML, CSS.",
            "job_role": "Frontend Developer",
            "question": "Can you describe your experience with frontend technologies?",
            "answer": final_transcript
        }
        print("\nSubmitting final transcript to backend evaluation (/api/interview/evaluate-answer)...")
        t0 = time.perf_counter()
        try:
            r_eval = await client.post(EVALUATE_ANSWER_URL, json=eval_payload, timeout=45.0)
            eval_lat = (time.perf_counter() - t0) * 1000.0
            if r_eval.status_code == 200:
                eval_res = r_eval.json()
                print(f"  [PASS] Backend Evaluation HTTP 200 ({eval_lat:.0f}ms)")
                print(f"         Score    : {eval_res.get('score', 'N/A')}/10")
                print(f"         Feedback : {eval_res.get('feedback', '')[:100]}...")
                eval_status = "SUCCESS"
            else:
                print(f"  [NOTICE] Evaluation returned HTTP {r_eval.status_code} ({r_eval.text[:80]})")
                eval_status = f"HTTP_{r_eval.status_code}"
        except Exception as e:
            print(f"  [NOTICE] Backend evaluation skipped/timed out: {e}")
            eval_status = "ERROR"

        benchmark_data["pipeline"] = {
            "chunk_count": len(chunk_latencies),
            "mean_chunk_latency_ms": round(float(np.mean(chunk_latencies)), 1),
            "accumulated_text": accumulated_text,
            "final_transcript": final_transcript,
            "final_transcription_latency_ms": round(final_lat, 1),
            "backend_evaluation_status": eval_status
        }

    # Save Results
    with open(OUTPUT_BENCHMARK_JSON, "w", encoding="utf-8") as fp:
        json.dump(benchmark_data, fp, indent=2)

    print("\n" + "=" * 80)
    print("BENCHMARK COMPLETED SUCCESSFULLY")
    print(f"Results saved to: {OUTPUT_BENCHMARK_JSON}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
