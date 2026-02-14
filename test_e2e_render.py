import requests
import json
import random
import time

# URL = "http://localhost:10000/analyze" # Local test
URL = "https://spatial-analysis-service.onrender.com/analyze" # Production

def test_analyze_experimental():
    print(f"Testing {URL}...")
    
    # Simulate 10 minutes of data (600 seconds)
    # Power: Ramp from 100 to 300
    power_data = [100 + (200 * i / 600) for i in range(600)]
    
    # RR Intervals: Simulate 60bpm (1000ms) with some noise
    # We need a list of RR intervals for the whole session.
    # 10 mins @ 60bpm = ~600 beats.
    rr_intervals = [1000 + random.uniform(-50, 50) for _ in range(600)]
    
    payload = {
        "power_data": power_data,
        "rr_intervals": rr_intervals,
        "ftp": 250,
        "w_prime": 20000
    }
    
    try:
        start_time = time.time()
        response = requests.post(URL, json=payload)
        duration = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            keys = data.keys()
            print("Response Keys:", list(keys))
            
            # Check for Experimental Fields
            if "alpha1_analysis" in data:
                print("✅ Alpha-1 Analysis present")
                a1 = data["alpha1_analysis"]
                print(f"   - {len(a1)} data points returned")
                if len(a1) > 0:
                    print(f"   - Sample: {a1[0]}")
            else:
                print("❌ Alpha-1 Analysis MISSING")
                
            if "w_balance_dynamic" in data:
                print("✅ Dynamic W' Balance present")
                wd = data["w_balance_dynamic"]
                print(f"   - {len(wd)} data points returned")
            else:
                print("❌ Dynamic W' Balance MISSING")
                
            if "w_balance" in data:
                print("✅ Standard W' Balance present")
        else:
            print("Error Response:", response.text)
            
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    test_analyze_experimental()
