import httpx
import asyncio
import os
import time

SIDECAR_URL = "http://127.0.0.1:8003"
PROXY_URL = "http://127.0.0.1:8000/api/speech/transcribe-local"
TEST_WAV = os.path.join(os.path.dirname(__file__), "test_audio.wav")
TEST_WEBM = os.path.join(os.path.dirname(__file__), "test_audio.webm")

def create_test_files():
    # 1. Create a 1s silent WAV file using soundfile
    import soundfile as sf
    import numpy as np
    silent_audio = np.zeros(16000, dtype=np.float32)
    sf.write(TEST_WAV, silent_audio, 16000)

    # 2. Create a dummy WebM file
    with open(TEST_WEBM, "wb") as f:
        f.write(b"dummy webm content")

async def test_health():
    print("Test 1-3: Health endpoint & Model loading...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{SIDECAR_URL}/health", timeout=5.0)
            data = resp.json()
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            assert data["status"] == "ready", "Model not ready"
            print(f"  [OK] Health OK. VRAM reserved: {data.get('vram_reserved_mb', 0):.0f} MB")
        except Exception as e:
            print(f"  [FAIL] Health check failed: {e}")
            raise

async def test_wav_direct():
    print("Test 4, 8, 9: WAV Transcription (Direct) + Latency + VRAM...")
    async with httpx.AsyncClient() as client:
        with open(TEST_WAV, "rb") as f:
            files = {"audio": ("test_audio.wav", f, "audio/wav")}
            t0 = time.time()
            resp = await client.post(f"{SIDECAR_URL}/transcribe", files=files, timeout=60.0)
            dt = time.time() - t0
            
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert "text" in data, "No text in response"
            # Since it's silence, Whisper usually predicts empty string or hallucinations like "Thank you." 
            # We just verify it returns a successful payload.
            print(f"  [OK] Transcribed successfully in {dt:.2f}s (Engine reported: {data['transcription_time_s']:.2f}s). Peak VRAM: {data['peak_vram_mb']:.0f} MB")
            print(f"       Text: '{data['text']}'")

async def test_webm_rejection():
    print("Test 5, 7: WebM Rejection & Invalid handling...")
    async with httpx.AsyncClient() as client:
        with open(TEST_WEBM, "rb") as f:
            files = {"audio": ("test_audio.webm", f, "audio/webm")}
            resp = await client.post(f"{SIDECAR_URL}/transcribe", files=files, timeout=60.0)
            assert resp.status_code == 415, f"Expected 415, got {resp.status_code}"
            print(f"  [OK] WebM gracefully rejected: {resp.json()}")

async def test_backend_proxy():
    print("Test 6: Main backend proxy...")
    async with httpx.AsyncClient() as client:
        try:
            with open(TEST_WAV, "rb") as f:
                files = {"audio": ("test_audio.wav", f, "audio/wav")}
                resp = await client.post(PROXY_URL, files=files, timeout=60.0)
                
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
                data = resp.json()
                assert "text" in data, "No text in proxy response"
                print(f"  [OK] Proxy successful. Text: '{data['text']}'")
        except httpx.ConnectError:
            print("  [SKIP] Main backend not running on port 8000, skipping proxy test.")

async def run_all():
    create_test_files()
    try:
        await test_health()
        await test_wav_direct()
        await test_webm_rejection()
        await test_backend_proxy()
        print("\nAll accessible tests passed!")
    finally:
        if os.path.exists(TEST_WAV): os.remove(TEST_WAV)
        if os.path.exists(TEST_WEBM): os.remove(TEST_WEBM)

if __name__ == "__main__":
    asyncio.run(run_all())
