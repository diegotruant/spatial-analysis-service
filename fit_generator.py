import csv
import json
import os
import subprocess
import tempfile
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Config
# Expecting FitCSVTool.jar in a 'libs' directory relative to this file
FIT_SDK_JAR_PATH = os.path.join(os.path.dirname(__file__), "libs", "FitCSVTool.jar")

def generate_fit_from_json(json_data: dict) -> str:
    """
    Generates a FIT file from the provided JSON data.
    Returns the path to the generated FIT file.
    """
    # 1. Validate data
    if "samples" not in json_data or not json_data["samples"]:
        raise ValueError("No samples provided")

    start_time_str = json_data.get("start_time")
    if not start_time_str:
        raise ValueError("No start_time provided")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as csv_file:
        csv_path = csv_file.name
        _write_fit_csv(json_data, csv_file)
    
    fit_path = csv_path.replace(".csv", ".fit")
    
    # 2. Run FitCSVTool
    try:
        _run_fit_csv_tool(csv_path, fit_path)
    except Exception as e:
        # Cleanup CSV if failed, or keep it for debugging?
        # For now, keep it if it fails could be useful, but standard is cleanup
        if os.path.exists(csv_path):
            os.remove(csv_path)
        raise e
        
    # Cleanup CSV
    if os.path.exists(csv_path):
        os.remove(csv_path)
        
    return fit_path

def _write_fit_csv(data: dict, file_handle):
    """
    Writes the data to a CSV file in the format expected by FitCSVTool.
    """
    writer = csv.writer(file_handle)
    
    # Garmin Epoch
    creation_time = _iso_to_garmin_time(data["start_time"])
    
    # Header
    writer.writerow(["Type", "Local Number", "Message", "Field 1", "Value 1", "Units 1", "Field 2", "Value 2", "Units 2", "Field 3", "Value 3", "Units 3", "Field 4", "Value 4", "Units 4", "Field 5", "Value 5", "Units 5", "Field 6", "Value 6", "Units 6"])
    
    # 1. File ID
    # Definition
    writer.writerow(["Definition", "0", "file_id", "type", "1", "", "manufacturer", "1", "", "product", "1", "", "time_created", "1", "", "serial_number", "1", ""])
    # Data
    writer.writerow(["Data", "0", "file_id", "type", "4", "", "manufacturer", "1", "", "product", "0", "", "time_created", str(creation_time), "", "serial_number", "0", ""])
    
    # 2. Record Definition
    # We check if we need RR data
    has_rr = False
    for s in data["samples"]:
        if "rr" in s and s["rr"]:
            has_rr = True
            break
            
    # Base definition
    # timestamp, heart_rate, power, cadence, speed
    # Note: Fields must be in the order of the definition
    fields = ["timestamp", "heart_rate", "power", "cadence", "speed"]
    
    # Use standard field names. FitCSVTool uses names to look up IDs.
    # Check if 'rr_interval' is accepted. If strictly following SDK, it might be.
    # If not, we might need to use developer data, but let's try standard field.
    if has_rr:
        fields.append("rr_interval") # Units: s (if conversion is done right in tool? usually s)
        
    # Build Definition Row
    # Local Num 1
    def_row = ["Definition", "1", "record"]
    for f in fields:
        def_row.extend([f, "1", ""]) # Field Name, Count, Units (empty in def)
    
    writer.writerow(def_row)
    
    # 3. Data Rows
    for sample in data["samples"]:
        ts = _iso_to_garmin_time(sample["timestamp"])
        hr = sample.get("hr", "")
        pwr = sample.get("power", "")
        cad = sample.get("cadence", "")
        spd = sample.get("speed", "")
        
        row = ["Data", "1", "record", "timestamp", ts, "", "heart_rate", hr, "bpm", "power", pwr, "watts", "cadence", cad, "rpm", "speed", spd, "m/s"]
        
        if has_rr:
            # Add RR
            rr = sample.get("rr", [])
            if rr:
                # Value|Value|Value
                rr_str = "|".join([str(x) for x in rr])
                row.extend(["rr_interval", rr_str, "s"])
            else:
                row.extend(["rr_interval", "", "s"])
                
        writer.writerow(row)

def _run_fit_csv_tool(csv_path, fit_path):
    if not os.path.exists(FIT_SDK_JAR_PATH):
        raise FileNotFoundError(f"FitCSVTool.jar not found at {FIT_SDK_JAR_PATH}. Please install the Garmin FIT SDK.")


    # java -jar FitCSVTool.jar -c <csv> <fit>
    cmd = ["java", "-jar", FIT_SDK_JAR_PATH, "-c", csv_path, fit_path]
    
    # Capture output for debugging
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"FitCSVTool stdout: {result.stdout}")
        logger.error(f"FitCSVTool stderr: {result.stderr}")
        raise RuntimeError(f"FitCSVTool failed. Check logs for details. Stderr: {result.stderr}")

def _iso_to_garmin_time(iso_str):
    # Garmin epoch: 1989-12-31 00:00:00 UTC
    garmin_epoch = datetime(1989, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
    try:
        # Handle ISO with Z or offset
        if iso_str.endswith('Z'):
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # Fallback if isoformat is strict
        dt = datetime.now(timezone.utc) # Should probably error out, but safe fallback? No, raise.
        raise ValueError(f"Invalid date format: {iso_str}")
        
    delta = dt - garmin_epoch
    return int(delta.total_seconds())

