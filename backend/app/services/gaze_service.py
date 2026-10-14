import os
import io
import cv2
import numpy as np
import json
import logging
import requests
from PIL import Image

import sys
sys.modules['tensorflow'] = None

try:
    import mediapipe as mp
except ImportError:
    mp = None

logger = logging.getLogger(__name__)

GAZE_SERVICE_URL = "http://127.0.0.1:8001/predict"

class GazeService:
    def __init__(self):
        self.config = None
        self.load_error = None
        self.face_mesh = None
        
        # Load the configuration JSON from the ml directory where we calibrated it
        self.config_path = os.path.join(os.path.dirname(__file__), '../../../ml/eye_contact/eye_contact_thresholds.json')
        
        self._init_mediapipe()
        self._load_config()

    def _init_mediapipe(self):
        if mp is None:
            logger.warning("MediaPipe is not installed. Face presence will fail.")
            return
        
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True, 
            max_num_faces=10, 
            refine_landmarks=True
        )

    def _load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"Gaze config not found at {self.config_path}")
            return

        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info("Eye contact thresholds loaded successfully.")
        except Exception as e:
            self.load_error = str(e)
            logger.error(f"Failed to load gaze config: {e}")

    def analyze_gaze(self, image_bytes: bytes) -> dict:
        """
        Detects face, crops the right eye, calls the isolated Gaze inference service, 
        and calculates eye contact boolean using calibrated thresholds.
        """
        response = {
            "face_present": False,
            "face_count": 0,
            "looking_at_camera": None,
            "gaze_pitch": None,
            "gaze_yaw": None,
            "face_crop_bytes": None,
            "error": None
        }

        if self.config is None or self.face_mesh is None:
            if self.load_error:
                response["error"] = f"Gaze service configuration unavailable. Real error: {self.load_error}"
            else:
                response["error"] = "Gaze service unavailable (missing dependencies or config)."
            return response

        try:
            # 1. Load image and convert to OpenCV RGB format for MediaPipe
            try:
                img_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
                img_rgb = np.array(img_pil)
            except Exception as e:
                logger.error(f"Failed to decode image bytes: {e}")
                response["error"] = f"Failed to decode image bytes: {e}"
                return response
            
            # 2. Detect face
            results = self.face_mesh.process(img_rgb)
            if not results.multi_face_landmarks:
                logger.error("No face landmarks detected by MediaPipe")
                return response
                
            response["face_present"] = True
            response["face_count"] = len(results.multi_face_landmarks)
            
            if response["face_count"] > 1:
                logger.warning(f"Multiple faces detected: {response['face_count']}")
                return response
            
            landmarks = results.multi_face_landmarks[0].landmark
            h_img, w_img, _ = img_rgb.shape

            # Crop detected face with 15% margin for emotion recognition
            face_pts_x = [int(lm.x * w_img) for lm in landmarks]
            face_pts_y = [int(lm.y * h_img) for lm in landmarks]
            f_xmin, f_xmax = min(face_pts_x), max(face_pts_x)
            f_ymin, f_ymax = min(face_pts_y), max(face_pts_y)
            margin_fx = int((f_xmax - f_xmin) * 0.15)
            margin_fy = int((f_ymax - f_ymin) * 0.15)
            f_xmin = max(0, f_xmin - margin_fx)
            f_xmax = min(w_img, f_xmax + margin_fx)
            f_ymin = max(0, f_ymin - margin_fy)
            f_ymax = min(h_img, f_ymax + margin_fy)
            if f_xmax > f_xmin and f_ymax > f_ymin:
                face_crop = img_rgb[f_ymin:f_ymax, f_xmin:f_xmax]
                face_crop_bgr = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
                success_face, enc_face = cv2.imencode('.jpg', face_crop_bgr)
                if success_face:
                    response["face_crop_bytes"] = enc_face.tobytes()

            # 3. Locate the right eye region
            RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            
            pts = []
            for idx in RIGHT_EYE_INDICES:
                lm = landmarks[idx]
                x = int(lm.x * w_img)
                y = int(lm.y * h_img)
                pts.append([x, y])
                
            pts = np.array(pts)
            xmin, ymin = np.min(pts, axis=0)
            xmax, ymax = np.max(pts, axis=0)
            
            w = xmax - xmin
            h = ymax - ymin
            
            margin_w = int(w * 0.5)
            margin_h = int(h * 1.5)
            
            xmin = max(0, int(xmin - margin_w))
            xmax = min(w_img, int(xmax + margin_w))
            ymin = max(0, int(ymin - margin_h))
            ymax = min(h_img, int(ymax + margin_h))
            
            if xmin >= xmax or ymin >= ymax:
                logger.error("Invalid crop bounds")
                return response
                
            # Crop using grayscale image
            img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
            crop = img_gray[ymin:ymax, xmin:xmax]
            
            if crop.size == 0:
                logger.error("Empty crop")
                return response
                
            # Resize crop to model required dimensions (width=48, height=36)
            crop = cv2.resize(crop, (48, 36))
            
            # Encode crop to JPEG to send over HTTP
            success, encoded_image = cv2.imencode('.jpg', crop)
            if not success:
                response["error"] = "Failed to encode eye crop"
                return response
                
            # 5. Call isolated Gaze service
            try:
                files = {"file": ("eye_crop.jpg", encoded_image.tobytes(), "image/jpeg")}
                res = requests.post(GAZE_SERVICE_URL, files=files, timeout=2.0)
                res.raise_for_status()
                pred_data = res.json()
                
                if "error" in pred_data:
                    response["error"] = pred_data["error"]
                    return response
                    
                pitch = pred_data.get("pitch")
                yaw = pred_data.get("yaw")
                
                if pitch is None or yaw is None:
                    response["error"] = "Invalid response from Gaze inference service"
                    return response
            except requests.exceptions.RequestException as req_e:
                response["error"] = f"Gaze inference service unavailable: {req_e}"
                return response
            
            response["gaze_pitch"] = pitch
            response["gaze_yaw"] = yaw
            
            # 6. Eye Contact interpretation
            adj_pitch = pitch - self.config["center_pitch"]
            adj_yaw = yaw - self.config["center_yaw"]
            
            looking_at_camera = (abs(adj_pitch) <= self.config["pitch_threshold"]) and (abs(adj_yaw) <= self.config["yaw_threshold"])
            response["looking_at_camera"] = bool(looking_at_camera)
            
            return response
            
        except Exception as e:
            logger.error(f"Error during gaze analysis: {e}")
            response["error"] = str(e)
            return response

gaze_service = GazeService()
