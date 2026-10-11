import sys
import os
import io
import soundfile as sf
import traceback

sys.path.append(os.path.dirname(__file__))

def test_vad():
    try:
        from asr_server import app, logger
    except Exception as e:
        print("Failed to import asr_server:", e)
        traceback.print_exc()
        return
        
    print("Successfully imported asr_server. Testing VAD logic...")
    import numpy as np
    
    # generate 3 seconds of 16kHz audio with a sine wave
    t = np.linspace(0, 3, 3 * 16000)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    
    buf = io.BytesIO()
    sf.write(buf, audio, 16000, format='WAV', subtype='PCM_16')
    buf.seek(0)
    content = buf.read()
    
    try:
        with io.BytesIO(content) as buffer:
            audio_data, sample_rate = sf.read(buffer)
            
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        # This matches the code in asr_server.py exactly
        import asr_server
        
        # Test evaluating it inside the module's namespace
        rms = asr_server.np.sqrt(asr_server.np.mean(audio_data**2))
        max_amp = asr_server.np.max(asr_server.np.abs(audio_data))
        print("VAD RMS:", rms, "Max Amp:", max_amp)
        print("Test passed!")
    except Exception as e:
        print("Error during simulated VAD:")
        traceback.print_exc()

if __name__ == "__main__":
    test_vad()
