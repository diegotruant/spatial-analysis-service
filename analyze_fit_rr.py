"""
Script per analizzare il file FIT e verificare presenza dati RR
"""
import sys

try:
    from fitparse import FitFile
    print("✅ fitparse installed")
except ImportError:
    print("❌ fitparse NOT installed")
    print("Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fitparse"])
    from fitparse import FitFile
    print("✅ fitparse installed successfully")

# File FIT trovato
FIT_FILE = r"c:\Users\Diego Truant\Desktop\00DDTraining\spatial-cosmic\cycling-coach-platform\1770398355836.fit"

print("\n" + "=" * 70)
print("RR INTERVAL DATA CHECK - FIT FILE ANALYSIS")
print("=" * 70)
print(f"\nAnalyzing: {FIT_FILE}\n")

try:
    fitfile = FitFile(FIT_FILE)
    
    # Track what we find
    has_rr_data = False
    rr_count = 0
    hr_count = 0
    record_count = 0
    all_fieldnames = set()
    sample_records = []
    
    print("📊 Scanning all records...\n")
    
    for record in fitfile.get_messages('record'):
        record_count += 1
        record_data = {}
        
        for field in record:
            field_name = field.name
            all_fieldnames.add(field_name)
            record_data[field_name] = field.value
            
            # Look for HR data
            if 'heart_rate' in field_name.lower():
                hr_count += 1
            
            # Look for RR data (various possible names)
            if any(keyword in field_name.lower() for keyword in ['rr', 'r_r', 'heart_rate_interval', 'hrv']):
                has_rr_data = True
                rr_count += 1
                print(f"🎯 FOUND RR FIELD: {field_name} = {field.value}")
        
        # Save first few records for inspection
        if len(sample_records) < 3:
            sample_records.append(record_data)
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n📈 Total records: {record_count}")
    print(f"💓 Records with HR: {hr_count}")
    print(f"⏱️  Records with RR: {rr_count}")
    
    print(f"\n📋 All field names found ({len(all_fieldnames)}):")
    for field in sorted(all_fieldnames):
        print(f"  - {field}")
    
    print(f"\n🔍 Sample record (first):")
    if sample_records:
        for key, value in sample_records[0].items():
            if value is not None:
                print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    
    if has_rr_data:
        print("✅ RR DATA FOUND!")
        print(f"   {rr_count} records contain RR intervals")
        print("\n🎉 Your device supports RR transmission!")
        print("   ✅ DFA alpha 1 implementation is FEASIBLE")
    else:
        print("❌ NO RR DATA FOUND")
        print("\n⚠️ Possible reasons:")
        print("   1. Heart rate strap doesn't transmit RR")
        print("   2. Recording device didn't save RR data")
        print("   3. RR data is in a different message type")
        
        # Check HRV and other message types
        print("\n🔍 Checking other message types for RR/HRV data...")
        for msg_type in ['hrv', 'heart_rate_variability', 'hr_data']:
            try:
                for msg in fitfile.get_messages(msg_type):
                    print(f"\n   Found {msg_type} message:")
                    for field in msg:
                        print(f"      {field.name}: {field.value}")
                    has_rr_data = True
            except:
                pass
        
        if not has_rr_data:
            print("\n   ❌ No RR data found in any message type")
            print("\n💡 Recommendations:")
            print("   1. Use Polar H10, Garmin HRM-Pro, or Wahoo TICKR X")
            print("   2. Check if your app supports RR recording")
            print("   3. Try a different recording device (Garmin, Wahoo, etc.)")

except Exception as e:
    print(f"\n❌ Error analyzing file: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
