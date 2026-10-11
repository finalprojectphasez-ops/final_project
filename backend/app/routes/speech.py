from fastapi import APIRouter, UploadFile, File, HTTPException
import httpx
import logging

router = APIRouter()
logger = logging.getLogger("uvicorn")

ASR_SIDECAR_URL = "http://127.0.0.1:8003/transcribe"

@router.post("/transcribe-local")
async def transcribe_local(audio: UploadFile = File(...)):
    """
    Proxies audio transcription requests to the local Whisper ASR sidecar.
    """
    try:
        content = await audio.read()
        logger.info(f"[Speech Route] Received audio upload: filename={audio.filename}, content_type={audio.content_type}, bytes={len(content)}")
    except Exception as e:
        logger.error(f"[Speech Route] Failed to read audio upload: {e}")
        raise HTTPException(status_code=400, detail="Failed to read uploaded file")
        
    try:
        async with httpx.AsyncClient() as client:
            files = {"audio": (audio.filename, content, audio.content_type)}
            # 60s timeout accommodates potential queueing + inference time
            response = await client.post(ASR_SIDECAR_URL, files=files, timeout=60.0)
            logger.info(f"[Speech Route] ASR Sidecar responded with HTTP {response.status_code}")
            
            if response.status_code != 200:
                # Safely relay the error without exposing stack traces
                err_data = response.json()
                detail = err_data.get("error", "ASR service returned an error")
                logger.warning(f"[Speech Route] ASR Sidecar error detail: {detail}")
                raise HTTPException(status_code=response.status_code, detail=detail)
                
            res_data = response.json()
            char_count = len(res_data.get("text", ""))
            duration_s = res_data.get("transcription_time_s", None)
            logger.info(f"[Speech Route] ASR result: HTTP {response.status_code}, chars={char_count}, transcription_time_s={duration_s}")
            return res_data
            
    except httpx.RequestError as e:
        logger.error(f"ASR Sidecar connection error: {e}")
        raise HTTPException(status_code=503, detail="Local ASR service is currently unavailable")
