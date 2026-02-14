import sys
import os
import random
import datetime

# Add current directory to path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



def generate_sample_fit():
    print("Generating sample FIT file with HRV data...")
    
    # Simulate a 10-minute activity (600 seconds)
    duration_seconds = 600
    start_time = datetime.datetime.now()
    
    power_data = []
    hr_data = []
    rr_intervals = []
    timestamps = []
    
    # Base values
    current_power = 150
    current_hr = 120
    
    # RR simulation: 60000 / HR = ms per beat
    # We accumulate RR intervals
    last_beat_time = 0
    
    for i in range(duration_seconds):
        t = start_time + datetime.timedelta(seconds=i)
        timestamps.append(t.isoformat())
        
        # Power Ramp
        current_power += 0.2 # Slow ramp up
        power_data.append(int(current_power + random.uniform(-10, 10)))
        
        # HR Response (lagged)
        target_hr = 120 + (current_power - 150) * 0.5
        current_hr += (target_hr - current_hr) * 0.1
        hr_data.append(int(current_hr))
        
        # RR Intervals for this second
        # At 120 bpm, 2 beats per second = 500ms
        # We generate RR intervals that sum up to approx 1 second
        ms_per_beat = 60000 / current_hr
        
        # DFA Alpha-1 simulation: 
        # Add some 1/f noise or random noise (white noise = 0.5, pink = 1.0)
        # Here just random variation
        noise = random.uniform(-20, 20) 
        rr = ms_per_beat + noise
        rr_intervals.append(rr)
        # Add a second beat if HR > 60 approx
        if current_hr > 60:
             rr_intervals.append(rr + random.uniform(-5, 5))
             
    # Prepare data structure for FitGenerator
    activity_data = {
        "samples": []
    }
    
    for i in range(duration_seconds):
        sample = {
            "timestamp": timestamps[i],
            "power": power_data[i],
            "heart_rate": hr_data[i],
            "cadence": 85 + int(random.uniform(-5, 5)),
            "speed": 8.0 + (power_data[i] / 300) * 2,
            "rr": [rr_intervals[i]] # FitGenerator expects list of RR for this second
        }
        # Add extra RR if we generated multiple for this second (simplified above as 1-2 per sec)
        # In my logic above, I appended to flat list rr_intervals.
        # I need to restructure the loop to key RR to the sample.
        
    # Let's rewrite the data generation loop to be cleaner and match FitGenerator expectation
    activity_data = {
        "start_time": timestamps[0],
        "samples": []
    }
    
    rr_index = 0
    for i in range(duration_seconds):
        # Determine how many R-R intervals fall into this second?
        # Simplified: Just assign the RR interval generated for this step
        # Note: In real FIT, RR are cumulative. Here we just want data to exist.
        
        current_rr = rr_intervals[i]
        sample_rr = [current_rr]
        
        # If we had a second beat
        if i < len(rr_intervals) - 1 and len(rr_intervals) > duration_seconds:
             # This logic is messy because I generated a flat list of RR separately.
             # Let's just put 1 RR per second for simplicity, or 2 if HR > 60
             pass

        # Simulated Alpha1: 1.0 (low) to 0.5 (high)
        alpha1 = max(0.4, 1.0 - (hr_data[i] - 120) * 0.0125)
        
        sample = {
            "timestamp": timestamps[i],
            "power": power_data[i],
            "heart_rate": hr_data[i],
            "cadence": 85 + int(random.uniform(-5, 5)),
            "speed": 8.0 + (power_data[i] / 300) * 2,
            "rr": [current_rr / 1000.0],
            "alpha1": alpha1
        }
        activity_data["samples"].append(sample)

    output_filename = "sample_activity_with_hrv.fit"
    
    try:
        from fit_generator import generate_fit_from_json
        
        fit_path = generate_fit_from_json(activity_data)
        
        # Move to local directory
        import shutil
        local_path = os.path.abspath(output_filename)
        shutil.move(fit_path, local_path)
        
        print(f"✅ Created {local_path}")
        print(f"Size: {os.path.getsize(local_path)} bytes")
        
    except Exception as e:
        print(f"❌ Error generating FIT: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_sample_fit()
