from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.emotion_service import emotion_service
from app.services.gaze_service import gaze_service
from pydantic import BaseModel
from typing import Dict, Optional

router = APIRouter()

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
        
        # 1. Emotion Prediction
        emotion_result = emotion_service.predict_emotion(contents)
        
        # 2. Gaze Prediction
        gaze_result = gaze_service.analyze_gaze(contents)
        
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
