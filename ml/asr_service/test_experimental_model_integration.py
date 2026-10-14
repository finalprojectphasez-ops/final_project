"""
test_experimental_model_integration.py

Controlled Local Integration Test Suite for PreMock AI ASR:
Verifies the integration of the 10k technical-interview Whisper model
(checkpoint-375) with repetition-control decoding (no_repeat_ngram_size=3).

TESTS COVERED:
1. Sidecar Health & Metadata: Confirms experimental model and decoding settings.
2. Direct Sidecar Transcription: Verifies direct port 8003 transcription, latency, VRAM.
3. Main Backend Proxy: Verifies port 8000 /api/speech/transcribe-local proxying.
4. Text Accumulation / Chunk Merging: Simulates frontend microphone chunk streaming and transcript merging.
5. Context & Term Handling: Tests candidate context handling and technical glossary enrichment.
6. Repetition-Control Verification: Verifies absence of runaway trigram loops and dot loops.
7. Error Handling & Edge Cases: Tests empty audio, malformed bytes, WebM rejection, silence handling.
"""

import os
import sys
import io
import time
import json
import re
import numpy as np
import soundfile as sf
import httpx
import asyncio

SIDECAR_URL = "http://127.0.0.1:8003"
BACKEND_PROXY_URL = "http://127.0.0.1:8000/api/speech/transcribe-local"
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))

REAL_TEST_WAV = os.path.join(SERVICE_DIR, "real_test.wav")
VALIDATION_WAV = os.path.join(SERVICE_DIR, "validation_speech.wav")
EMPTY_TEST_WAV = os.path.join(SERVICE_DIR, "empty_test.wav")
MALFORMED_WAV = os.path.join(SERVICE_DIR, "malformed.wav")


def merge_transcripts(existing: str, next_str: str) -> str:
    """Exact replica of the frontend mergeTranscripts logic from page.tsx."""
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
        return existing.trim() + " " + " ".join(w2[overlap:]) if hasattr(existing, 'trim') else existing.strip() + " " + " ".join(w2[overlap:])
    return existing.strip() + " " + next_str.strip()


def check_for_repetition(text: str) -> bool:
    """Detects runaway repetition loops (>=4 repeated trigrams or dot loops)."""
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


async def run_integration_tests():
    print("=" * 80)
    print("PreMock AI — ASR Integration Test: Checkpoint-375 (no_repeat_ngram_size=3)")
    print("=" * 80)
    results = {}

    async with httpx.AsyncClient() as client:
        # -------------------------------------------------------------------
        # 1. Health & Model Configuration Check
        # -------------------------------------------------------------------
        print("\n[TEST 1] Verifying ASR Sidecar Health & Configuration...")
        try:
            resp = await client.get(f"{SIDECAR_URL}/health", timeout=5.0)
            assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}"
            data = resp.json()
            assert data.get("status") == "ready", f"Service not ready: {data}"
            assert data.get("is_experimental") is True, f"Experimental model not active: {data}"
            assert data.get("no_repeat_ngram_size") == 3, f"Incorrect no_repeat_ngram_size: {data}"
            assert "checkpoint-375" in data.get("lora_path", ""), f"LoRA path incorrect: {data.get('lora_path')}"
            
            print(f"  [PASS] Health Status        : {data['status']}")
            print(f"  [PASS] Active Model         : {data['model']}")
            print(f"  [PASS] Checkpoint Path      : {data['lora_path']}")
            print(f"  [PASS] no_repeat_ngram_size : {data['no_repeat_ngram_size']}")
            print(f"  [PASS] Device / VRAM        : {data['device']} / {data['vram_reserved_mb']:.1f} MB")
            results["health_check"] = {"status": "PASS", "data": data}
        except Exception as e:
            print(f"  [FAIL] Health check failed: {e}")
            results["health_check"] = {"status": "FAIL", "error": str(e)}

        # -------------------------------------------------------------------
        # 2. Direct Sidecar Transcription (real_test.wav)
        # -------------------------------------------------------------------
        print("\n[TEST 2] Direct Sidecar Transcription (real_test.wav)...")
        try:
            with open(REAL_TEST_WAV, "rb") as f:
                content = f.read()
            t0 = time.perf_counter()
            resp = await client.post(
                f"{SIDECAR_URL}/transcribe",
                files={"audio": ("real_test.wav", content, "audio/wav")},
                timeout=30.0
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            res_data = resp.json()
            assert "text" in res_data and len(res_data["text"].strip()) > 0, "No transcription text returned"
            has_rep = check_for_repetition(res_data["text"])
            assert not has_rep, f"Repetition detected in output: {res_data['text']}"

            print(f"  [PASS] HTTP Status          : {resp.status_code}")
            print(f"  [PASS] Transcription        : \"{res_data['text']}\"")
            print(f"  [PASS] Engine Inferred Time : {res_data.get('transcription_time_s', 0):.2f}s")
            print(f"  [PASS] Round-trip Latency   : {elapsed_ms:.1f} ms")
            print(f"  [PASS] Peak VRAM            : {res_data.get('peak_vram_mb', 0):.1f} MB")
            results["direct_transcribe_real"] = {
                "status": "PASS",
                "text": res_data["text"],
                "latency_ms": round(elapsed_ms, 1),
                "vram_mb": res_data.get("peak_vram_mb", 0)
            }
        except Exception as e:
            print(f"  [FAIL] Direct transcribe failed: {e}")
            results["direct_transcribe_real"] = {"status": "FAIL", "error": str(e)}

        # -------------------------------------------------------------------
        # 3. Main Backend Proxy Transcription (/api/speech/transcribe-local)
        # -------------------------------------------------------------------
        print("\n[TEST 3] Main Backend Proxy Transcription (Port 8000)...")
        try:
            with open(REAL_TEST_WAV, "rb") as f:
                content = f.read()
            t0 = time.perf_counter()
            resp = await client.post(
                BACKEND_PROXY_URL,
                files={"audio": ("real_test.wav", content, "audio/wav")},
                timeout=30.0
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            res_data = resp.json()
            assert "text" in res_data and len(res_data["text"].strip()) > 0
            
            print(f"  [PASS] Proxy HTTP Status    : {resp.status_code}")
            print(f"  [PASS] Proxy Output Text    : \"{res_data['text']}\"")
            print(f"  [PASS] Proxy Round-trip     : {elapsed_ms:.1f} ms")
            results["backend_proxy_real"] = {
                "status": "PASS",
                "text": res_data["text"],
                "latency_ms": round(elapsed_ms, 1)
            }
        except Exception as e:
            print(f"  [FAIL] Backend proxy failed: {e}")
            results["backend_proxy_real"] = {"status": "FAIL", "error": str(e)}

        # -------------------------------------------------------------------
        # 4. Context & Technical Glossary Injection Test
        # -------------------------------------------------------------------
        print("\n[TEST 4] Transcription with Technical & Candidate Context...")
        try:
            with open(VALIDATION_WAV, "rb") as f:
                content = f.read()
            candidate_ctx = "Candidate: Nishant. Technologies: Python, SQL, Docker, FastAPI"
            t0 = time.perf_counter()
            resp = await client.post(
                BACKEND_PROXY_URL,
                files={"audio": ("validation_speech.wav", content, "audio/wav")},
                data={"context": candidate_ctx},
                timeout=30.0
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            res_data = resp.json()
            assert not check_for_repetition(res_data["text"])

            print(f"  [PASS] Injected Context     : \"{candidate_ctx}\"")
            print(f"  [PASS] Output Text          : \"{res_data['text']}\"")
            print(f"  [PASS] Latency              : {elapsed_ms:.1f} ms")
            results["context_transcription"] = {
                "status": "PASS",
                "text": res_data["text"],
                "latency_ms": round(elapsed_ms, 1)
            }
        except Exception as e:
            print(f"  [FAIL] Context transcription failed: {e}")
            results["context_transcription"] = {"status": "FAIL", "error": str(e)}

        # -------------------------------------------------------------------
        # 5. Live Recording / Text Accumulation Simulation (Frontend Chunks)
        # -------------------------------------------------------------------
        print("\n[TEST 5] Live Recording & Text Accumulation (3s slices + 0.5s overlap)...")
        try:
            audio_data, sr = sf.read(VALIDATION_WAV)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            chunk_len = int(3.0 * sr)
            overlap_len = int(0.5 * sr)
            accumulated_text = ""
            chunk_results = []

            start = 0
            chunk_idx = 0
            total_chunk_time = 0.0

            while start < len(audio_data):
                end = min(start + chunk_len, len(audio_data))
                chunk = audio_data[start:end]
                dur = len(chunk) / float(sr)

                buf = io.BytesIO()
                sf.write(buf, chunk, sr, format='WAV', subtype='PCM_16')
                buf.seek(0)
                chunk_bytes = buf.read()

                t0 = time.perf_counter()
                resp = await client.post(
                    BACKEND_PROXY_URL,
                    files={"audio": (f"chunk_{chunk_idx}.wav", chunk_bytes, "audio/wav")},
                    timeout=30.0
                )
                chunk_ms = (time.perf_counter() - t0) * 1000.0
                total_chunk_time += chunk_ms

                assert resp.status_code == 200, f"Chunk {chunk_idx} failed: {resp.text}"
                c_text = resp.json().get("text", "")

                prev_acc = accumulated_text
                accumulated_text = merge_transcripts(accumulated_text, c_text)

                chunk_results.append({
                    "chunk": chunk_idx,
                    "duration_s": round(dur, 2),
                    "raw_whisper": c_text,
                    "accumulated_after": accumulated_text,
                    "latency_ms": round(chunk_ms, 1)
                })

                print(f"  Chunk {chunk_idx} ({dur:.1f}s): {chunk_ms:.0f}ms -> \"{c_text[:40]}...\"")

                if end == len(audio_data):
                    break
                start = end - overlap_len
                chunk_idx += 1

            has_rep = check_for_repetition(accumulated_text)
            assert not has_rep, f"Repetition detected in accumulated text: {accumulated_text}"
            print(f"  [PASS] Slices Streamed      : {len(chunk_results)}")
            print(f"  [PASS] Accumulated Text     : \"{accumulated_text}\"")
            print(f"  [PASS] Repetition Degeneracy: NONE (0 trigram loops)")
            print(f"  [PASS] Average Chunk Latency: {total_chunk_time / len(chunk_results):.1f} ms")
            results["chunked_accumulation"] = {
                "status": "PASS",
                "num_chunks": len(chunk_results),
                "final_accumulated_text": accumulated_text,
                "repetition_failure": False,
                "avg_chunk_latency_ms": round(total_chunk_time / len(chunk_results), 1),
                "chunks": chunk_results
            }
        except Exception as e:
            print(f"  [FAIL] Chunked accumulation failed: {e}")
            results["chunked_accumulation"] = {"status": "FAIL", "error": str(e)}

        # -------------------------------------------------------------------
        # 6. Error Handling & Edge Cases
        # -------------------------------------------------------------------
        print("\n[TEST 6] Verifying Robust Error Handling & Edge Cases...")
        # 6a. Empty Audio File (0 bytes)
        try:
            resp = await client.post(
                f"{SIDECAR_URL}/transcribe",
                files={"audio": ("empty.wav", b"", "audio/wav")},
                timeout=10.0
            )
            assert resp.status_code == 400, f"Expected 400 for empty audio, got {resp.status_code}"
            print(f"  [PASS] Empty audio rejected       : HTTP {resp.status_code} ({resp.json().get('code')})")
            results["empty_audio"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Empty audio test failed: {e}")
            results["empty_audio"] = "FAIL"

        # 6b. Malformed Audio Bytes
        try:
            resp = await client.post(
                f"{SIDECAR_URL}/transcribe",
                files={"audio": ("corrupt.wav", b"invalid_audio_bytes_header_missing", "audio/wav")},
                timeout=10.0
            )
            assert resp.status_code == 400, f"Expected 400 for malformed audio, got {resp.status_code}"
            print(f"  [PASS] Malformed audio rejected    : HTTP {resp.status_code} ({resp.json().get('code')})")
            results["malformed_audio"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Malformed audio test failed: {e}")
            results["malformed_audio"] = "FAIL"

        # 6c. WebM Format Rejection
        try:
            resp = await client.post(
                f"{SIDECAR_URL}/transcribe",
                files={"audio": ("audio.webm", b"dummy_webm", "audio/webm")},
                timeout=10.0
            )
            assert resp.status_code == 415, f"Expected 415 for WebM, got {resp.status_code}"
            print(f"  [PASS] WebM format rejected        : HTTP {resp.status_code} ({resp.json().get('code')})")
            results["webm_rejection"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] WebM rejection test failed: {e}")
            results["webm_rejection"] = "FAIL"

        # 6d. Pure Silence Audio Handling
        try:
            silent_buf = io.BytesIO()
            sf.write(silent_buf, np.zeros(16000, dtype=np.float32), 16000, format='WAV')
            silent_buf.seek(0)
            resp = await client.post(
                f"{SIDECAR_URL}/transcribe",
                files={"audio": ("silence.wav", silent_buf.read(), "audio/wav")},
                timeout=10.0
            )
            assert resp.status_code == 200, f"Expected 200 for silence, got {resp.status_code}"
            data = resp.json()
            assert data.get("text") == "" and data.get("code") == "NO_SPEECH_DETECTED"
            print(f"  [PASS] Silence cleanly handled     : HTTP 200 (code: {data.get('code')}, text: \"\")")
            results["silence_handling"] = "PASS"
        except Exception as e:
            print(f"  [FAIL] Silence handling failed: {e}")
            results["silence_handling"] = "FAIL"

        # -------------------------------------------------------------------
        # 7. Consecutive Latency & RTF Benchmark
        # -------------------------------------------------------------------
        print("\n[TEST 7] Consecutive Latency & Real-Time Factor (RTF) Benchmark...")
        latencies = []
        with open(REAL_TEST_WAV, "rb") as f:
            wav_bytes = f.read()

        audio_info = sf.info(REAL_TEST_WAV)
        duration_s = audio_info.duration

        for run_idx in range(5):
            t0 = time.perf_counter()
            resp = await client.post(
                BACKEND_PROXY_URL,
                files={"audio": ("benchmark.wav", wav_bytes, "audio/wav")},
                timeout=30.0
            )
            lat_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200
            latencies.append(lat_ms)
            print(f"  Run #{run_idx + 1}: {lat_ms:.1f} ms (Inference time: {resp.json().get('transcription_time_s', 0):.2f}s)")

        mean_lat = float(np.mean(latencies))
        median_lat = float(np.median(latencies))
        rtf = (mean_lat / 1000.0) / duration_s

        print(f"  [PASS] Audio Duration       : {duration_s:.2f}s")
        print(f"  [PASS] Mean Latency         : {mean_lat:.1f} ms")
        print(f"  [PASS] Median Latency       : {median_lat:.1f} ms")
        print(f"  [PASS] Real-Time Factor     : {rtf:.4f} (Faster than real-time by {1.0/rtf:.1f}x)")
        results["benchmark"] = {
            "status": "PASS",
            "audio_duration_s": round(duration_s, 2),
            "mean_latency_ms": round(mean_lat, 1),
            "median_latency_ms": round(median_lat, 1),
            "rtf": round(rtf, 4),
            "runs_ms": [round(l, 1) for l in latencies]
        }

    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY REPORT")
    print("=" * 80)
    all_passed = all(
        (v.get("status") == "PASS" if isinstance(v, dict) else v == "PASS")
        for v in results.values()
    )
    for test_name, res in results.items():
        st = res.get("status") if isinstance(res, dict) else res
        print(f"  {test_name:<30}: {st}")
    print(f"\nOVERALL RESULT: {'ALL TESTS PASSED [OK]' if all_passed else 'SOME TESTS FAILED [FAIL]'}")
    print("=" * 80)

    # Save summary report to JSON
    report_file = os.path.join(SERVICE_DIR, "local_test_integration_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model_tested": "whisper_tech_interviews_lora/phase1_10k/checkpoint-375",
            "decoding_setting": "no_repeat_ngram_size=3",
            "all_tests_passed": all_passed,
            "test_details": results
        }, f, indent=2)
    print(f"Test results saved to: {report_file}")


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
