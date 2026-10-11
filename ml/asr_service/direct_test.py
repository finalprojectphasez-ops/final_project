import sys
import os
import io
import asyncio
import numpy as np
import soundfile as sf
import traceback

sys.path.append(os.path.dirname(__file__))

async def run_test():
    try:
        from asr_server import transcribe, engine
    except Exception as e:
        print("Failed to import transcribe:", e)
        return
        
    print("Successfully imported transcribe function.")
    
    # Mock engine model to bypass model check
    engine.model = True
    
    # Create fake FastAPI UploadFile
    from fastapi import UploadFile
    
    t = np.linspace(0, 3, 3 * 16000)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    buf = io.BytesIO()
    sf.write(buf, audio, 16000, format='WAV', subtype='PCM_16')
    buf.seek(0)
    content = buf.read()
    
    class MockUploadFile:
        def __init__(self, c):
            self.content_type = "audio/wav"
            self.c = c
        async def read(self):
            return self.c
            
    mock_file = MockUploadFile(content)
    
    try:
        print("Calling transcribe()...")
        response = await transcribe(mock_file)
        print("Transcribe returned:", response)
        if hasattr(response, 'body'):
            import json
            print("Response body:", response.body.decode('utf-8'))
        
        # Test a silent file to verify VAD
        print("\nTesting silent audio...")
        silent_audio = np.zeros(3 * 16000, dtype=np.float32)
        buf2 = io.BytesIO()
        sf.write(buf2, silent_audio, 16000, format='WAV', subtype='PCM_16')
        buf2.seek(0)
        silent_content = buf2.read()
        
        mock_silent = MockUploadFile(silent_content)
        silent_response = await transcribe(mock_silent)
        if hasattr(silent_response, 'body'):
            print("Silent response body:", silent_response.body.decode('utf-8'))
            
    except Exception as e:
        print("Transcribe raised exception:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
