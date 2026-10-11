import requests
with open('test.jpg', 'rb') as f:
    res = requests.post('http://127.0.0.1:8002/predict', files={'file': ('test.jpg', f, 'image/jpeg')})
print(res.status_code, res.json())
