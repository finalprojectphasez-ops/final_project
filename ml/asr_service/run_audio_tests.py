import asyncio
import httpx
import time
import soundfile as sf
import os
import io
import sys
from datasets import load_dataset

async def run_tests():
    print("Loading one sample from dataset...")
    try:
        ds = load_dataset("ishands/commonvoice-indian_accent", split="train", trust_remote_code=True, streaming=True)
        sample = next(iter(ds))
        audio_array = sample["audio"]["array"]
        sample_rate = sample["audio"]["sampling_rate"]
        text = sample["sentence"]
        print(f"Original Text: {text}")
        
        # Save to buffer
        buf = io.BytesIO()
        sf.write(buf, audio_array, sample_rate, format='WAV', subtype='PCM_16')
        buf.seek(0)
        wav_bytes = buf.read()
        print(f"Generated WAV size: {len(wav_bytes)} bytes, Sample rate: {sample_rate}Hz")
        
        # Test A: Direct through local Whisper sidecar (full audio)
        print("\n--- Test A: Direct Full Audio ---")
        async with httpx.AsyncClient() as client:
            t0 = time.time()
            res = await client.post(
                'http://127.0.0.1:8003/transcribe', 
                files={'audio': ('test.wav', wav_bytes, 'audio/wav')},
                timeout=60.0
            )
            print(f"Status code: {res.status_code}")
            if res.status_code == 200:
                print(f"Transcription: {res.json().get('text')}")
                print(f"Time: {res.json().get('transcription_time_s'):.2f}s")
            else:
                print(f"Error: {res.text}")
                
        # Test B: Chunked audio (simulating frontend)
        print("\n--- Test B: Chunked Audio ---")
        # Split into 3-second chunks with 0.5s overlap
        # 16000 hz -> 3s = 48000 samples. 0.5s = 8000 samples.
        chunk_size = 3 * sample_rate
        overlap = int(0.5 * sample_rate)
        
        start = 0
        chunks = []
        while start < len(audio_array):
            end = min(start + chunk_size, len(audio_array))
            chunks.append(audio_array[start:end])
            if end == len(audio_array):
                break
            start = end - overlap
            
        print(f"Split into {len(chunks)} chunks.")
        
        async with httpx.AsyncClient() as client:
            for i, chunk in enumerate(chunks):
                chunk_buf = io.BytesIO()
                sf.write(chunk_buf, chunk, sample_rate, format='WAV', subtype='PCM_16')
                chunk_buf.seek(0)
                
                res = await client.post(
                    'http://127.0.0.1:8003/transcribe', 
                    files={'audio': (f'chunk_{i}.wav', chunk_buf.read(), 'audio/wav')},
                    timeout=30.0
                )
                if res.status_code == 200:
                    print(f"Chunk {i} text: {res.json().get('text')}")
                else:
                    print(f"Chunk {i} error: {res.text}")
                    
    except Exception as e:
        print("Error during tests:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_tests())
