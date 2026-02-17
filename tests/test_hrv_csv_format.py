import io
import csv
import sys
import os

# Add directory to path to import fit_generator
sys.path.append(os.path.dirname(__file__))

from fit_generator import _write_fit_csv

def test_hrv_format():
    print("Testing HRV CSV Generation...")
    
    # Mock Data with RR intervals
    data = {
        "start_time": "2024-01-01T12:00:00Z",
        "samples": [
            {
                "timestamp": "2024-01-01T12:00:01Z",
                "power": 100,
                "hr": 60,
                "rr": [1.0] # 1 second RR
            },
            {
                "timestamp": "2024-01-01T12:00:02Z",
                "power": 100,
                "hr": 60,
                "rr": [0.5, 0.5] # Two 0.5s intervals
            }
        ]
    }
    
    # Capture output
    output = io.StringIO()
    _write_fit_csv(data, output)
    
    content = output.getvalue()
    print("Generated CSV Content:")
    print("---------------------------------------------------")
    print(content)
    print("---------------------------------------------------")
    
    # Verify Content
    if "Definition,2,hrv" in content:
        print("✅ HRV Definition found")
    else:
        print("❌ HRV Definition NOT found")
        
    if "Data,2,hrv" in content:
         print("✅ HRV Data row found")
    else:
         print("❌ HRV Data row NOT found")

    if "1.0" in content and "0.5|0.5" in content:
        print("✅ RR values formatted correctly")
    else:
        print("❌ RR values missing or malformed")

if __name__ == "__main__":
    test_hrv_format()
