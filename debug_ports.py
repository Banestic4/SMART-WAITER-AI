import socket
import requests

def check_port(port, name):
    print(f"Checking {name} on port {port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    if result == 0:
        print(f"✅ {name} port {port} IS OPEN.")
        return True
    else:
        print(f"❌ {name} port {port} IS CLOSED. (Code: {result})")
        return False

def check_backend_health():
    try:
        r = requests.get("http://127.0.0.1:8000/")
        if r.status_code == 200:
            print(f"✅ Backend Health Check: PASS ({r.json()})")
        else:
            print(f"❌ Backend Health Check: FAIL (Status {r.status_code})")
    except Exception as e:
        print(f"❌ Backend Health Check: ERROR ({e})")

if __name__ == "__main__":
    be = check_port(8000, "Backend")
    fe = check_port(3000, "Frontend")
    
    if be:
        check_backend_health()
