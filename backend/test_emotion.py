import requests
with open('real_test.webp', 'rb') as f:
    res = requests.post('http://127.0.0.1:8000/api/emotion/predict', files={'file': ('real_test.webp', f, 'image/webp')})
print(res.status_code, res.json())
