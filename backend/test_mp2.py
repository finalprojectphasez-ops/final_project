import sys
sys.modules['tensorflow'] = None

try:
    import mediapipe as mp
    print('MediaPipe OK!')
except Exception as e:
    print('MediaPipe failed:', e)
