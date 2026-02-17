import urllib.request
import urllib.error
import json
import os
import time
from datetime import datetime

# Production URL
BACKEND_URL = "https://spatial-analysis-service.onrender.com/generate_fit"

def test_production_fit_generation():
    print(f"🚀 Testing Production Backend: {BACKEND_URL}")
    
    # 1. Create Realistic Payload (from Mobile App)
    start_dt = datetime.now()
    payload = {
        "sport": "cycling",
        "start_time": start_dt.isoformat(), 
        "samples": []
    }
    
    # Generate 10 minutes of data (1Hz)
    start_ts = start_dt.timestamp()
    for i in range(600):
        t_ts = start_ts + i
        t_iso = datetime.fromtimestamp(t_ts).isoformat()
        
        # Simulate a ramp: 100W to 200W
        power = 100 + (i / 600) * 100
        hr = 120 + (i / 600) * 30
        
        sample = {
            "timestamp": t_iso,
            "power": int(power),
            "hr": int(hr), # Key is 'hr' in BikeSample
            "cadence": int(80 + (i % 10)),
            "speed": 8.0 + (i / 1000),
            "rr": [60.0 / hr] # Key is 'rr' in BikeSample, value in seconds [0.5]
        }
        
        payload["samples"].append(sample)
        
    print(f"📦 Payload prepared: {len(payload['samples'])} samples")
    
    # 2. Send Request
    try:
        print("⏳ Sending request... (this might take a few seconds if cold start)")
        start_req = datetime.now()
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(BACKEND_URL, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            duration = (datetime.now() - start_req).total_seconds()
            print(f"✅ Success! Response received in {duration:.2f}s")
            
            # 3. Save FIT File
            filename = f"test_production_{datetime.now().strftime('%Y%m%d_%H%M%S')}.fit"
            with open(filename, "wb") as f:
                f.write(response.read())
            
            print(f"💾 FIT file saved to: {os.path.abspath(filename)}")
            print(f"👉 You can upload this file to Strava manually to verify.")
            
            # Check file header
            with open(filename, "rb") as f:
                header = f.read(14)
                if b".FIT" in header:
                    print("✅ Valid FIT Header detected.")
                else:
                    print("⚠️ Warning: FIT Header not found in first 14 bytes.")
                    
    except urllib.error.HTTPError as e:
        print(f"❌ Failed: Status {e.code}")
        print(f"Reason: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_production_fit_generation()
