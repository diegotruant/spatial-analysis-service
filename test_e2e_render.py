import requests
import json
import time
import sys

# URL = "http://localhost:8000" # Local debug
URL = "https://spatial-analysis-service.onrender.com" # Production

def test_health():
    print(f"Checking {URL}/health...")
    try:
        res = requests.get(f"{URL}/health")
        if res.status_code == 200:
            print("✅ Health Check Passed:", res.json())
            return True
        else:
            print(f"❌ Health Check Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_w_prime_balance():
    print(f"\nTesting {URL}/experimental/w_prime_balance...")
    payload = {
        "power_data": [100.0, 100.0, 400.0, 400.0],
        "cp": 250,
        "w_prime": 20000
    }
    
    try:
        res = requests.post(f"{URL}/experimental/w_prime_balance", json=payload)
        if res.status_code == 200:
            data = res.json()
            if "w_prime_balance" in data and len(data["w_prime_balance"]) == 4:
                print("✅ W' Balance Endpoint Passed")
                return True
            else:
                print(f"❌ Invalid Response Format: {data}")
                return False
        else:
            print(f"❌ Request Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    print(f"Waiting for deployment to propagate (sleeping 10s)...")
    time.sleep(10) 
    
    if not test_health():
        sys.exit(1)
        
    if not test_w_prime_balance():
        print("⚠️ Experimental endpoint might not be deployed yet.")
        sys.exit(1)
        
    print("\n🚀 DEPLOYMENT VERIFIED SUCCESSFUL")
