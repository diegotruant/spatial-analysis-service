import requests
import random
import json

BASE_URL = "http://localhost:8000"

def test_health():
    print("--- Testing Health Endpoint ---")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.json()}")
    print()

def test_analysis():
    print("--- Testing Activity Analysis (Advanced Metrics) ---")
    # Simulate 1 hour of data with Power and HR
    mock_power = [max(0, 250 + random.uniform(-60, 60)) for _ in range(3600)]
    mock_hr = [max(60, 140 + random.uniform(-5, 5)) for _ in range(3600)]
    
    payload = {
        "power_data": mock_power,
        "hr_data": mock_hr,
        "ftp": 280
    }
    
    response = requests.post(f"{BASE_URL}/analyze", json=payload)
    results = response.json()
    print(f"Response: {json.dumps(results, indent=2)}")
    print()

def test_metabolic():
    print("--- Testing Metabolic Engine ---")
    payload = {
        "weight": 72.5,
        "height": 180,
        "age": 32,
        "gender": "MALE",
        "body_fat": 12.5,
        "somatotype": "ECTOMORPH",
        "p_max": 950,
        "mmp3": 380,
        "mmp6": 320,
        "mmp15": 290
    }
    
    response = requests.post(f"{BASE_URL}/metabolic/profile", json=payload)
    results = response.json()
    print(f"Metabolic Profile Results:")
    print(f"  VLamax: {results['vlamax']}")
    print(f"  VO2max: {results['vo2max']}")
    print(f"  MLSS (FTP): {results['mlss']} W")
    print(f"  BMR: {results['bmr']} kcal")
    print(f"  Zones: {len(results['zones'])} zones generated")
    print()

def test_hrv():
    print("--- Testing HRV Analysis ---")
    payload = {
        "hrv_current": 55.0,
        "hrv_history": [62, 58, 60, 65, 63, 59, 61],
        "full_history": [
            {"date": "2024-01-25", "hrv": 62},
            {"date": "2024-01-26", "hrv": 45}, # Depressed
            {"date": "2024-01-27", "hrv": 42}, # Depressed
            {"date": "2024-01-28", "hrv": 40}, # Depressed
            {"date": "2024-01-29", "hrv": 44}, # Depressed
            {"date": "2024-01-30", "hrv": 55}
        ]
    }
    
    response = requests.post(f"{BASE_URL}/hrv/analyze", json=payload)
    results = response.json()
    print(f"HRV Analysis Results:")
    print(f"  Today: {results['today']['status']} ({results['today']['deviation']}%)")
    print(f"  Overreaching Status: {results['overreaching']['status']}")
    print(f"  Recommendation: {results['recommendation']}")
    print()

if __name__ == "__main__":
    try:
        test_health()
        test_analysis()
        test_metabolic()
        test_hrv()
    except Exception as e:
        print(f"Error: Server might not be running. Error details: {e}")
