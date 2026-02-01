import requests
import random
import time

def test_analysis_api():
    url = "http://localhost:8000/analyze"
    
    # Simulate 1 hour of power data
    mock_power = [max(0, 220 + random.uniform(-40, 40)) for _ in range(3600)]
    
    payload = {
        "power_data": mock_power,
        "ftp": 250
    }
    
    print(f"Sending request with {len(mock_power)} data points...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        results = response.json()
        
        print(f"\n--- API Response in {elapsed:.4f}s ---")
        print(f"NP: {results['normalized_power']} W")
        print(f"TSS: {results['tss']}")
        print(f"Peak 5m: {results['peak_powers']['5m']} W")
        
    except Exception as e:
        print(f"Error testing API: {e}")
        print("Make sure the FastAPI server is running (python main.py)")

if __name__ == "__main__":
    test_analysis_api()
