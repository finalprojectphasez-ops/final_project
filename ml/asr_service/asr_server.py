import os
import time
import io
import asyncio
import torch
import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import soundfile as sf
import logging
import numpy as np
from whisper_engine import WhisperEngine

app = FastAPI(title="Whisper ASR Sidecar")
logger = logging.getLogger("uvicorn")

MODEL_ID = "openai/whisper-base.en"
LORA_PATH = os.path.join(os.path.dirname(__file__), '..', 'asr_model', 'whisper_indian_accent_lora_20k')

engine = WhisperEngine(MODEL_ID, LORA_PATH)
inference_lock = asyncio.Lock()

@app.on_event("startup")
async def startup_event():
    logger.info("[ASR Sidecar] Starting up and loading model...")
    try:
        engine.load_model()
    except Exception as e:
        logger.error(f"[ASR Sidecar] Failed to load model: {e}")

@app.get("/health")
async def health_check():
    vram = 0
    if torch.cuda.is_available():
        vram = torch.cuda.memory_reserved(0) / 1e6
        
    status = "ready" if engine.model is not None else "failed"
    return {
        "status": status,
        "model": f"{MODEL_ID} + LoRA 20k",
        "device": engine.device,
        "vram_reserved_mb": vram
    }

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    if not engine.model:
        return JSONResponse(status_code=503, content={"error": "Model not loaded", "code": "MODEL_OFFLINE"})
        
    if not audio.content_type.startswith("audio/"):
        return JSONResponse(status_code=400, content={"error": "Uploaded file is not audio", "code": "INVALID_FILE"})
        
    if audio.content_type == "audio/webm":
        return JSONResponse(
            status_code=415,
            content={"error": "Unsupported audio format. WebM requires FFmpeg. Please upload a WAV file.", "code": "UNSUPPORTED_FORMAT"}
        )
        
    # Read file
    try:
        content = await audio.read()
        if len(content) > 25 * 1024 * 1024:
            return JSONResponse(status_code=413, content={"error": "File too large (max 25MB)", "code": "PAYLOAD_TOO_LARGE"})
            
        if len(content) == 0:
            return JSONResponse(status_code=400, content={"error": "Empty audio file", "code": "EMPTY_FILE"})
            
        with io.BytesIO(content) as buffer:
            audio_data, sample_rate = sf.read(buffer)
            
        # soundfile returns 2D array if stereo, we need mono
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        duration = len(audio_data) / sample_rate
        rms = float(np.sqrt(np.mean(audio_data**2)))
        max_amp = float(np.max(np.abs(audio_data)))
        
        logger.info(f"[ASR Sidecar] Audio received: {len(content)} bytes, sample_rate={sample_rate}Hz, duration={duration:.2f}s, rms={rms:.4f}, max_amp={max_amp:.4f}")
        
        # Pure silence check (only reject true silence)
        if rms < 0.002 or max_amp < 0.008:
            logger.info(f"[ASR Sidecar] Pure silence detected (rms={rms:.5f}, max_amp={max_amp:.5f}) -> returning empty text")
            return JSONResponse(status_code=200, content={"error": "No speech detected", "code": "NO_SPEECH_DETECTED", "text": ""})
            
        if duration < 0.5 or duration > 120:
            return JSONResponse(status_code=400, content={"error": f"Audio duration {duration:.1f}s is out of bounds (0.5s - 120s)", "code": "INVALID_DURATION"})

    except Exception as e:
        import traceback
        with open("asr_server_error.log", "w") as f:
            f.write(traceback.format_exc())
        logger.exception(f"[ASR Sidecar] Audio decoding error:")
        return JSONResponse(status_code=400, content={"error": "Failed to decode audio. Ensure it is a valid WAV file.", "code": "DECODE_ERROR"})

    # Inference with concurrency protection (strictly 1 inference at a time on GPU)
    t0 = time.time()
    try:
        async def _do_inference():
            async with inference_lock:
                if torch.cuda.is_available():
                    torch.cuda.reset_peak_memory_stats(0)
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, engine.transcribe_audio_array, audio_data, sample_rate)

        text = await asyncio.wait_for(_do_inference(), timeout=50.0)
    except asyncio.TimeoutError:
        logger.error("[ASR Sidecar] Inference request timed out waiting for or executing in lock.")
        return JSONResponse(status_code=504, content={"error": "Inference timed out. ASR service is busy.", "code": "INFERENCE_TIMEOUT"})
    except Exception as e:
        logger.error(f"[ASR Sidecar] Inference error: {e}")
        return JSONResponse(status_code=500, content={"error": "Inference failed", "code": "INFERENCE_ERROR"})
        
    transcription_time_s = time.time() - t0
    logger.info(f"[ASR Sidecar] Transcribed in {transcription_time_s:.2f}s -> raw: '{text}'")
    
    peak_vram_mb = 0
    if torch.cuda.is_available():
        peak_vram_mb = torch.cuda.max_memory_allocated(0) / 1e6
        
    return {
        "text": text,
        "transcription_time_s": transcription_time_s,
        "peak_vram_mb": peak_vram_mb
    }

if __name__ == "__main__":
    uvicorn.run("asr_server:app", host="127.0.0.1", port=8003, reload=False)
