import os
import io
import logging
import requests
from PIL import Image

logger = logging.getLogger(__name__)

EMOTION_SERVICE_URL = "http://127.0.0.1:8002/predict"

class EmotionService:
    def __init__(self):
        self.classes = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

    def predict_emotion(self, image_bytes: bytes) -> dict:
        """
        Sends raw image bytes to the isolated Emotion inference service.
        Returns a dict with emotion and confidence.
        """
        try:
            # We can send the raw image bytes as they are
            files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
            res = requests.post(EMOTION_SERVICE_URL, files=files, timeout=2.0)
            res.raise_for_status()
            pred_data = res.json()
            
            if "error" in pred_data:
                return {"error": pred_data["error"]}
                
            return {
                "emotion": pred_data.get("emotion"),
                "confidence": pred_data.get("confidence")
            }

        except requests.exceptions.RequestException as req_e:
            logger.error(f"Error during emotion prediction request: {req_e}")
            return {
                "error": f"Emotion service unavailable: {req_e}"
            }
        except Exception as e:
            logger.error(f"Error during emotion prediction: {e}")
            return {
                "error": str(e)
            }

emotion_service = EmotionService()
