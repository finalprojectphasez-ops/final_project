import httpx
import asyncio
import os
import time
import soundfile as sf
import numpy as np
import io

try:
    from datasets import load_dataset, Audio
except ImportError:
    # Just in case datasets is not cleanly importable, fallback to a simpler text
    pass

PROXY_URL = "http://127.0.0.1:8000/api/speech/transcribe-local"
TEST_REAL_WAV = os.path.join(os.path.dirname(__file__), "real_test.wav")
TEST_EMPTY_WAV = os.path.join(os.path.dirname(__file__), "empty_test.wav")
TEST_MALFORMED = os.path.join(os.path.dirname(__file__), "malformed.wav")

def prepare_test_files():
    # 1. Real Audio from Dataset
    print("Fetching 1 real audio sample from dataset...")
    ds = load_dataset("ishands/commonvoice-indian_accent", split="train", streaming=True)
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    sample = next(iter(ds))
    
    reference_text = sample["sentence"]
    audio_array = sample["audio"]["array"]
    sf.write(TEST_REAL_WAV, audio_array, 16000)
    print(f"Created real_test.wav. Reference: '{reference_text}'")
    
    # 2. Empty WAV (0 seconds) - invalid duration
    empty_array = np.zeros(0, dtype=np.float32)
    sf.write(TEST_EMPTY_WAV, empty_array, 16000)
    
    # 3. Malformed audio (just random text bytes saved as .wav)
    with open(TEST_MALFORMED, "wb") as f:
        f.write(b"this is not a real audio file at all")

    return reference_text

async def run_test(filename, name):
    print(f"\n--- Testing {name} ---")
    async with httpx.AsyncClient() as client:
        with open(filename, "rb") as f:
            files = {"audio": (os.path.basename(filename), f, "audio/wav")}
            resp = await client.post(PROXY_URL, files=files, timeout=60.0)
            print(f"HTTP Status: {resp.status_code}")
            try:
                print(f"Response: {resp.json()}")
            except:
                print(f"Response (text): {resp.text}")

async def run_chunked_test(filename, name):
    print(f"\n--- Testing Chunked {name} ---")
    
    # Read the WAV
    audio_data, sr = sf.read(filename)
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
        
    # Simulate frontend chunks: 3 seconds (48000 samples at 16kHz) with 0.5s overlap (8000 samples)
    chunk_size = 3 * sr
    overlap = int(0.5 * sr)
    
    start = 0
    chunk_idx = 0
    
    async with httpx.AsyncClient() as client:
        while start < len(audio_data):
            end = min(start + chunk_size, len(audio_data))
            chunk = audio_data[start:end]
            
            import io
            buf = io.BytesIO()
            sf.write(buf, chunk, sr, format='WAV', subtype='PCM_16')
            buf.seek(0)
            wav_bytes = buf.read()
            
            # Diagnostics
            rms = np.sqrt(np.mean(chunk**2))
            max_amp = np.max(np.abs(chunk))
            duration = len(chunk) / sr
            
            print(f"Chunk {chunk_idx}: duration={duration:.2f}s, bytes={len(wav_bytes)}, rms={rms:.4f}, max_amp={max_amp:.4f}")
            
            files = {"audio": (f"chunk_{chunk_idx}.wav", wav_bytes, "audio/wav")}
            resp = await client.post(PROXY_URL, files=files, timeout=60.0)
            
            if resp.status_code == 200:
                print(f"   -> Raw Whisper Text: '{resp.json().get('text')}'")
            else:
                print(f"   -> Error: {resp.text}")
                
            if end == len(audio_data):
                break
            start = end - overlap
            chunk_idx += 1

async def main():
    if not os.path.exists(TEST_REAL_WAV):
        print(f"Error: {TEST_REAL_WAV} not found.")
        return
        
    await run_test(TEST_REAL_WAV, "Real Spoken Audio (Full)")
    
    await run_chunked_test(TEST_REAL_WAV, "Real Spoken Audio")
    
    # Let's also test a chunk of pure silence and noise to see if Solitaire is generated
    print("\n--- Testing 3s Silence & Noise Chunks ---")
    async with httpx.AsyncClient() as client:
        # Silence
        silence = np.zeros(3 * 16000, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, silence, 16000, format='WAV', subtype='PCM_16')
        buf.seek(0)
        files = {"audio": ("silence.wav", buf.read(), "audio/wav")}
        resp = await client.post(PROXY_URL, files=files, timeout=60.0)
        print(f"Silence Response: {resp.json()}")
        
        # Noise (simulating loud fan noise that bypasses VAD)
        # VAD threshold is rms=0.01. Let's make noise with rms=0.02
        noise = np.random.normal(0, 0.02, 3 * 16000).astype(np.float32)
        buf2 = io.BytesIO()
        sf.write(buf2, noise, 16000, format='WAV', subtype='PCM_16')
        buf2.seek(0)
        files2 = {"audio": ("noise.wav", buf2.read(), "audio/wav")}
        resp2 = await client.post(PROXY_URL, files=files2, timeout=60.0)
        print(f"Noise Response: {resp2.json()}")

if __name__ == "__main__":
    asyncio.run(main())
