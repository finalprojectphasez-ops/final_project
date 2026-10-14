import os
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, UploadFile, File
import logging

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    from keras.models import load_model
except ImportError:
    load_model = None

app = FastAPI(title="Emotion Inference Service")
logger = logging.getLogger("uvicorn")

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml_models', 'emotion_model.keras')
emotion_model = None
CLASSES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

@app.on_event("startup")
async def startup_event():
    global emotion_model
    try:
        emotion_model = load_model(MODEL_PATH)
        logger.info("[Emotion Service] Model loaded successfully")
    except Exception as e:
        logger.error(f"[Emotion Service] Failed to load model: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "emotion", "model_loaded": emotion_model is not None}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if emotion_model is None:
        return {"error": "Emotion model not loaded"}
        
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"error": "Invalid image format"}
            
        # 1 & 2. Decode and convert to grayscale
        if len(img.shape) == 3:
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray_img = img
            
        # 3. Resize to 48x48
        resized_img = cv2.resize(gray_img, (48, 48))
        
        # 4. Normalize to [0,1]
        normalized_img = resized_img.astype(np.float32) / 255.0
        
        # 5. Add batch/channel dims -> (1, 48, 48, 1)
        # Adding channel dim
        img_expanded = np.expand_dims(normalized_img, axis=-1)
        # Adding batch dim
        input_data = np.expand_dims(img_expanded, axis=0)
        
        # 6. Predict
        preds = emotion_model.predict(input_data, verbose=0)[0]
        max_index = np.argmax(preds)
        emotion = CLASSES[max_index]
        confidence = float(preds[max_index])
        
        # 7. Return
        return {
            "emotion": emotion,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("emotion_service_server:app", host="127.0.0.1", port=8002, reload=False)
