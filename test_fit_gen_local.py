import sys
import os
import json
import csv
from datetime import datetime

# Add current dir to path
sys.path.append(os.path.dirname(__file__))

from fit_generator import generate_fit_from_json, _iso_to_garmin_time

def test_full_generation():
    print("Testing Full FIT Generation (End-to-End)...")
    
    data = {
        "start_time": "2026-02-09T08:00:00Z",
        "sport": "bike",
        "samples": [
            {
                "timestamp": "2026-02-09T08:00:01Z",
                "hr": 140,
                "power": 200,
                "cadence": 90,
                "speed": 8.5,
                "rr": [0.8, 0.81]
            },
            {
                "timestamp": "2026-02-09T08:00:02Z",
                "hr": 142,
                "power": 210,
                "cadence": 92,
                "speed": 8.6,
                "rr": [0.79]
            }
        ]
    }
    
    try:
        fit_path = generate_fit_from_json(data)
        print(f"\n✅ FIT File generated at: {fit_path}")
        
        # Check if it's binary (real FIT) or text (Mock) if we reverted?
        # We expect real binary now.
        with open(fit_path, 'rb') as f:
            header = f.read(14) # FIT header is usually 12 or 14 bytes
            print(f"Header bytes: {header}")
            
            # Simple check for FIT magic string ".FIT" in header
            if b'.FIT' in header:
                 print("✅ Valid FIT Magic String found")
            else:
                 print("⚠️ Magic string not found (might be mock or invalid)")
                 
    except Exception as e:
        print(f"\n❌ Process Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_generation()
