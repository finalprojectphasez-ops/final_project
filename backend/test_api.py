import cv2
import numpy as np
import requests
img = np.zeros((36, 48, 3), dtype=np.uint8)
cv2.imwrite('test.jpg', img)
with open('test.jpg', 'rb') as f:
    res = requests.post('http://127.0.0.1:8001/predict', files={'file': ('test.jpg', f, 'image/jpeg')})
print(res.status_code, res.json())
