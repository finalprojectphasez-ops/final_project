import asyncio
import httpx
import uvicorn
import multiprocessing
import time
import numpy as np
import soundfile as sf
import io
import sys

def run_server():
    try:
        import uvicorn
        uvicorn.run("asr_server:app", host="127.0.0.1", port=8006, log_level="debug")
    except Exception as e:
        print("Server crashed:", e)

async def run_test():
    print("Starting sidecar on port 8006...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    # Wait for server to start up (takes a few seconds for Whisper to load)
    print("Waiting 15 seconds for Whisper model to load...")
    time.sleep(15)
    
    try:
        print("Generating audio...")
        t = np.linspace(0, 3, 3 * 16000)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        buf = io.BytesIO()
        sf.write(buf, audio, 16000, format='WAV', subtype='PCM_16')
        buf.seek(0)
        content = buf.read()
        print(f"Generated WAV size: {len(content)} bytes")
        
        print("Sending audio to port 8006...")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                'http://127.0.0.1:8006/transcribe', 
                files={'audio': ('test.wav', content, 'audio/wav')},
                timeout=30.0
            )
            print("Status code:", res.status_code)
            print("Response:", res.json())
    except Exception as e:
        print("Test failed with exception:")
        import traceback
        traceback.print_exc()
    finally:
        print("Shutting down server...")
        server_process.terminate()
        server_process.join()

if __name__ == "__main__":
    asyncio.run(run_test())
