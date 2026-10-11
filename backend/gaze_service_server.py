import os
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, UploadFile, File
import logging

# Ensure TF logging is minimal
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    from keras.models import load_model
except ImportError:
    load_model = None

app = FastAPI(title="Gaze Inference Service")
logger = logging.getLogger("uvicorn")

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'gaze_model.keras')
gaze_model = None

@app.on_event("startup")
async def startup_event():
    global gaze_model
    try:
        gaze_model = load_model(MODEL_PATH)
        logger.info("[Gaze Service] Model loaded successfully")
    except Exception as e:
        logger.error(f"[Gaze Service] Failed to load model: {e}")

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if gaze_model is None:
        return {"error": "Gaze model not loaded"}
        
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"error": "Invalid image format"}
            
        # Preprocess for model (grayscale, resize to 48x36, normalize)
        if len(img.shape) == 3:
            gray_eye = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray_eye = img
            
        resized_eye = cv2.resize(gray_eye, (48, 36))  # W=48, H=36
        normalized_eye = resized_eye.astype(np.float32) / 255.0
        input_data = np.expand_dims(normalized_eye, axis=(0, -1))
        
        # Predict
        preds = gaze_model.predict(input_data, verbose=0)
        pitch, yaw = float(preds[0][0]), float(preds[0][1])
        
        return {
            "pitch": pitch,
            "yaw": yaw
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("gaze_service_server:app", host="127.0.0.1", port=8001, reload=False)
