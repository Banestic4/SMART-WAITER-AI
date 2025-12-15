import uvicorn
import threading
import requests
import time
from api.index import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

def test_api():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(3) # Wait for server startup
    
    url = "http://127.0.0.1:8000/api/chat"
    session_id = "test-api-session-secure"
    headers = {"X-API-Key": "Banestic4"}
    
    print("\n--- Testing API Security ---")
    
    # 0. Test Unauthorized
    print(f"\n[Test]: Missing Header")
    res = requests.post(url, json={"message": "hi"})
    print(f"[API Status]: {res.status_code} (Expected 403)")

    # 1. Menu Inquiry (Authorized)
    payload = {"message": "What do you have?", "session_id": session_id}
    print(f"\n[User]: {payload['message']}")
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        print(f"[API]: {res.json()}")
    else:
        print(f"[API Error]: {res.text}")
    
    # 2. Order (Authorized)
    payload = {"message": "I'll have a coke.", "session_id": session_id}
    print(f"\n[User]: {payload['message']}")
    res = requests.post(url, json=payload, headers=headers)
    print(f"[API]: {res.json()}")

if __name__ == "__main__":
    test_api()
