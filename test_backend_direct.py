import requests
import os

def test_backend():
    url = "http://127.0.0.1:8000"
    print(f"Testing connectivity to {url}...")
    
    try:
        # 1. Health Check
        r = requests.get(url + "/")
        print(f"Root Status: {r.status_code}")
        print(f"Root Response: {r.text}")
        
        # 2. Chat Check (Auth)
        headers = {"X-API-Key": "Banestic4"}
        payload = {"message": "hi", "session_id": "debug-session"}
        
        print("\nTesting /api/chat...")
        r = requests.post(url + "/api/chat", json=payload, headers=headers, stream=True)
        print(f"Chat Status: {r.status_code}")
        
        if r.status_code == 200:
            print("Chat Response Stream:")
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    print(chunk.decode(), end="")
            print("\nSUCCESS: Backend is reachable and working.")
        else:
            print(f"FAILURE: Backend returned {r.status_code} - {r.text}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to backend. {e}")

if __name__ == "__main__":
    test_backend()
