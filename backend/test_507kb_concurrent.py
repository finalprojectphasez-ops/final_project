import time
import wave
import threading
import requests

# 1. Create a 507KB WAV in memory / file
wav_path = r"D:\project phase 2\final_project-1\backend\test_507kb_temp.wav"
with wave.open(wav_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    # 253,920 samples (15.87s) * 2 bytes = 507,840 bytes PCM + 44 bytes header = 507,884 bytes
    silence = b"\x00\x00" * 253920
    wf.writeframes(silence)

IMG_PATH = r"D:\project phase 2\final_project-1\backend\test.jpg"

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

threads = [threading.Thread(target=emotion_worker) for _ in range(2)]
for t in threads:
    t.daemon = True
    t.start()

time.sleep(1.0)
print(f"Background emotion workers streaming... Sent so far: {len(emotion_results)}")

t0 = time.time()
with open(wav_path, "rb") as f:
    r = requests.post(
        "http://127.0.0.1:8000/api/speech/transcribe-local",
        files={"audio": ("full_recording.wav", f, "audio/wav")},
        timeout=30
    )
dur = time.time() - t0

stop_event.set()
for t in threads:
    t.join(timeout=2)

print(f"507KB Speech Status under load: {r.status_code}")
print(f"Duration: {dur:.3f}s")
if r.status_code == 200:
    data = r.json()
    print("Response JSON:", data)
else:
    print("Error:", r.text)

print(f"Total background emotion frames during test: {len(emotion_results)}")
