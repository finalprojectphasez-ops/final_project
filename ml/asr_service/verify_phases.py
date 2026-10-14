import requests
import time
import os

print("=== PHASE 1: ASR SIDECAR HEALTH CHECK ===")
try:
    r_health = requests.get("http://127.0.0.1:8003/health", timeout=5)
    print("Health HTTP Status:", r_health.status_code)
    print("Health JSON:", r_health.json())
except Exception as e:
    print("Health check failed:", e)

wav_path = r"D:\project phase 2\final_project-1\ml\asr_service\validation_speech.wav"
print("\nWAV path exists:", os.path.exists(wav_path), "size:", os.path.getsize(wav_path))

print("\n=== PHASE 2: DIRECT ASR SIDECAR TEST (PORT 8003) ===")
try:
    t0 = time.time()
    with open(wav_path, "rb") as f:
        r_direct = requests.post("http://127.0.0.1:8003/transcribe", files={"audio": ("validation_speech.wav", f, "audio/wav")}, timeout=30)
    dur_direct = time.time() - t0
    print("Direct HTTP Status:", r_direct.status_code)
    print(f"Direct Response Duration: {dur_direct:.3f}s")
    if r_direct.status_code == 200:
        data = r_direct.json()
        text = data.get("text", "")
        print("Text returned:", bool(text))
        print("Transcript character count:", len(text))
        print("Sidecar reported duration:", data.get("transcription_time_s"))
        print("Peak VRAM (MB):", data.get("peak_vram_mb"))
    else:
        print("Direct Error Response:", r_direct.text)
except Exception as e:
    print("Direct test exception:", e)

print("\n=== PHASE 3: BACKEND PROXY TEST (PORT 8000) ===")
try:
    t0 = time.time()
    with open(wav_path, "rb") as f:
        r_proxy = requests.post("http://127.0.0.1:8000/api/speech/transcribe-local", files={"audio": ("validation_speech.wav", f, "audio/wav")}, timeout=30)
    dur_proxy = time.time() - t0
    print("Proxy HTTP Status:", r_proxy.status_code)
    print(f"Proxy Response Duration: {dur_proxy:.3f}s")
    if r_proxy.status_code == 200:
        data = r_proxy.json()
        text = data.get("text", "")
        print("Response JSON keys:", list(data.keys()))
        print("Text returned:", bool(text))
        print("Transcript character count:", len(text))
        print("Sidecar reported duration:", data.get("transcription_time_s"))
    else:
        print("Proxy Error Response:", r_proxy.text)
except Exception as e:
    print("Proxy test exception:", e)
