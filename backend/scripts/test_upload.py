import httpx
import asyncio
import numpy as np
import soundfile as sf
import io

async def test():
    print("Generating audio...")
    # generate 3 seconds of 16kHz audio with a sine wave (definitely speech-like energy)
    t = np.linspace(0, 3, 3 * 16000)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    # save to wav buffer
    buf = io.BytesIO()
    sf.write(buf, audio, 16000, format='WAV', subtype='PCM_16')
    buf.seek(0)
    
    print("Sending to backend...")
    async with httpx.AsyncClient() as client:
        res = await client.post('http://127.0.0.1:8000/api/speech/transcribe-local', files={'audio': ('test.wav', buf, 'audio/wav')})
        print("Status code:", res.status_code)
        print("Response:", res.json())

asyncio.run(test())
