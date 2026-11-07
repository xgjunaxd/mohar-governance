import requests
res = requests.post("http://127.0.0.1:8000/api/submissions", json={
    "title": "Test", "text": "Test", "channel": "social", "audience": "general", "creator": "Creator"
})
print("THE DATABASE ERROR IS:")
print(res.text)
