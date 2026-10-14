from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.emotion_service import emotion_service
from app.services.gaze_service import gaze_service
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio

router = APIRouter()
_gaze_lock = asyncio.Lock()

class EmotionResponse(BaseModel):
    # Original emotion fields
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    
    # New vision fields
    face_present: bool = False
    face_count: Optional[int] = None
    looking_at_camera: Optional[bool] = None
    gaze_pitch: Optional[float] = None
    gaze_yaw: Optional[float] = None
    
    error: Optional[str] = None
    gaze_error: Optional[str] = None

@router.post("/predict", response_model=EmotionResponse)
async def predict_emotion(file: UploadFile = File(...)):
    """
    Predict facial emotion and gaze from an uploaded image file (frame from webcam).
    """
    # Validate content type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be an image.")

    try:
        contents = await file.read()
        
        # 1. Run Gaze & Face detection first
        async with _gaze_lock:
            gaze_result = await asyncio.to_thread(gaze_service.analyze_gaze, contents)

        # 2. Extract cropped face for Emotion prediction
        face_crop_bytes = gaze_result.pop("face_crop_bytes", None)
        if gaze_result.get("face_present") and face_crop_bytes:
            emotion_result = await asyncio.to_thread(emotion_service.predict_emotion, face_crop_bytes)
        else:
            emotion_result = {"emotion": None, "confidence": None}
        
        response = EmotionResponse()
        
        # Populate Emotion
        if "error" in emotion_result:
            response.error = emotion_result["error"]
        else:
            response.emotion = emotion_result.get("emotion")
            response.confidence = emotion_result.get("confidence")
            
        # Populate Gaze
        if gaze_result.get("error"):
            response.gaze_error = gaze_result["error"]
            
        response.face_present = gaze_result.get("face_present", False)
        response.face_count = gaze_result.get("face_count")
        response.looking_at_camera = gaze_result.get("looking_at_camera")
        response.gaze_pitch = gaze_result.get("gaze_pitch")
        response.gaze_yaw = gaze_result.get("gaze_yaw")
            
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
