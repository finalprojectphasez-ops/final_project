import os
import time
import threading
import requests

WAV_PATH = r"D:\project phase 2\final_project-1\ml\asr_service\validation_speech.wav"
IMG_PATH = r"D:\project phase 2\final_project-1\backend\test.jpg"

print("=" * 60)
print("TEST 1: BACKEND PROXY SPEECH TRANSCRIBE (IDLE)")
print("=" * 60)
t0 = time.time()
with open(WAV_PATH, "rb") as f:
    r = requests.post(
        "http://127.0.0.1:8000/api/speech/transcribe-local",
        files={"audio": ("validation_speech.wav", f, "audio/wav")},
        timeout=30
    )
dur = time.time() - t0
print(f"Status: {r.status_code}")
print(f"Duration: {dur:.3f}s")
print(f"Response JSON: {r.json() if r.status_code == 200 else r.text}")

print("\n" + "=" * 60)
print("TEST 2: EMOTION / GAZE PREDICTION ENDPOINT")
print("=" * 60)
t0 = time.time()
with open(IMG_PATH, "rb") as f:
    r = requests.post(
        "http://127.0.0.1:8000/api/emotion/predict",
        files={"file": ("frame.jpg", f, "image/jpeg")},
        timeout=10
    )
dur = time.time() - t0
print(f"Status: {r.status_code}")
print(f"Duration: {dur:.3f}s")
if r.status_code == 200:
    data = r.json()
    print("Response fields:", list(data.keys()))
    print(f"face_present: {data.get('face_present')}, face_count: {data.get('face_count')}")
    print(f"looking_at_camera: {data.get('looking_at_camera')}")
    print(f"emotion: {data.get('emotion')}, confidence: {data.get('confidence')}")
    print(f"error: {data.get('error')}, gaze_error: {data.get('gaze_error')}")
else:
    print(f"Error: {r.text}")

print("\n" + "=" * 60)
print("TEST 3: SPEECH TRANSCRIBE DURING CONTINUOUS EMOTION STREAMING")
print("=" * 60)

stop_event = threading.Event()
emotion_results = []

def emotion_worker():
    while not stop_event.is_set():
        try:
            with open(IMG_PATH, "rb") as f:
                r = requests.post(
                    "http://127.0.0.1:8000/api/emotion/predict",
                    files={"file": ("frame.jpg", f, "image/jpeg")},
                    timeout=5
                )
                emotion_results.append((r.status_code, time.time()))
        except Exception as e:
            emotion_results.append((str(e), time.time()))
        time.sleep(0.1)

# Start 2 worker threads simulating continuous webcam frame uploads
threads = [threading.Thread(target=emotion_worker) for _ in range(2)]
for t in threads:
    t.daemon = True
    t.start()

# Let workers start hammering the backend
time.sleep(1.0)
print(f"Active background emotion requests running... Sent so far: {len(emotion_results)}")

# Now submit speech transcription while backend is actively receiving webcam frames
t0 = time.time()
with open(WAV_PATH, "rb") as f:
    r_speech = requests.post(
        "http://127.0.0.1:8000/api/speech/transcribe-local",
        files={"audio": ("validation_speech.wav", f, "audio/wav")},
        timeout=30
    )
speech_dur = time.time() - t0

stop_event.set()
for t in threads:
    t.join(timeout=2)

print(f"Concurrent Speech Status: {r_speech.status_code}")
print(f"Concurrent Speech Duration: {speech_dur:.3f}s")
if r_speech.status_code == 200:
    data = r_speech.json()
    print("Transcript chars:", len(data.get("text", "")))
    print("Sidecar reported duration:", data.get("transcription_time_s"))
    print("Text preview:", data.get("text", "")[:40])
else:
    print("Error:", r_speech.text)

print(f"Total background emotion frames processed during test: {len(emotion_results)}")
