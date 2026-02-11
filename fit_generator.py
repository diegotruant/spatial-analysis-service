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
    # if has_rr:
    #    fields.append("rr_interval") # Units: s (if conversion is done right in tool? usually s)
        
    # Build Definition Row
    # Local Num 1
    def_row = ["Definition", "1", "record"]
    for f in fields:
        def_row.extend([f, "1", ""]) # Field Name, Count, Units (empty in def)
    
    writer.writerow(def_row)
    
    # 3. HRV Definition (Message ID 78)
    # We define it if we have any RR data
    if has_rr:
        # Local Num 2
        # Field: time (array of seconds)
        writer.writerow(["Definition", "2", "hrv", "time", "1", "s"])
    
    # --- Developer Fields Setup ---
    # 1. Developer Data ID (Msg 207)
    # We use a fixed Application ID for VeloLab
    writer.writerow(["Definition", "5", "developer_data_id", "developer_data_index", "1", "", "application_id", "16", "", "application_version", "1", ""])
    # App ID: VeloLabAnalytics (hashed or random UUID)
    # 56 65 6C 6F 4C 61 62 41 6E 61 6C 79 74 69 63 73 (Hex for VeloLabAnalytics - 16 bytes)
    app_id = "56656C6F4C6162416E616C7974696373"
    writer.writerow(["Data", "5", "developer_data_id", "developer_data_index", "0", "", "application_id", app_id, "", "application_version", "100", ""])

    # 2. Field Description (Msg 206)
    # Define "Alpha1" (Field 0)
    # developer_data_index=0, field_definition_number=0, field_name="Alpha1", units="score", native_mesg_num=20 (Record), fit_base_type_id=136 (float32)
    writer.writerow(["Definition", "6", "field_description", 
                     "developer_data_index", "1", "", 
                     "field_definition_number", "1", "", 
                     "fit_base_type_id", "1", "", 
                     "field_name", "64", "", 
                     "units", "16", "", 
                     "native_mesg_num", "1", ""])
    
    writer.writerow(["Data", "6", "field_description", 
                     "developer_data_index", "0", "", 
                     "field_definition_number", "0", "", 
                     "fit_base_type_id", "136", "", 
                     "field_name", "Alpha1", "", 
                     "units", "score", "", 
                     "native_mesg_num", "20", ""])

    # 3. Data Rows with Alpha1 support
    # We assume 'alpha1' might be in the samples now
    for sample in data["samples"]:
        ts = _iso_to_garmin_time(sample["timestamp"])
        hr = sample.get("hr", "")
        pwr = sample.get("power", "")
        cad = sample.get("cadence", "")
        spd = sample.get("speed", "")
        alpha1 = sample.get("alpha1", "")
        
        # Base Row
        row = ["Data", "1", "record", "timestamp", ts, "", "heart_rate", hr, "bpm", "power", pwr, "watts", "cadence", cad, "rpm", "speed", spd, "m/s"]
        
        # Add Developer Field if Alpha1 is present
        if alpha1 != "":
            # We append the Developer Field data
            # Format: developer_data_index, 0, field_definition_number, 0, value, <val>
            # NOTE: Logic to append to the SAME row or use a different definition?
            # Integration with FitCSVTool usually requires the Definition to MATCH the Data row.
            # So if some rows have Alpha1 and others don't, we theoretically need 2 definitions.
            # BUT, standard practice is to use one definition and leave empty if missing? 
            # FitCSVTool handles empty strings as null/missing usually.
            pass 
        
        # RE-THINK: we need a definition that INCLUDES the developer field if we want to write it.
        # So we should update Definition 1 (Record) to include the dev field slots, or make a new Definition.
        # Let's verify if we can just append to the existing row without it being in definition? No.
        # So we must redefine Record.
    
    # Redefine Record (Def 1) to include Alpha1 potentially
    # Efficient strategy: Only use the definition with Alpha1? Or use two definitions?
    # Simpler: Just define it with Alpha1 and leave it empty if not present.
    
    # Re-writing Definition 1 (Record)
    # Local Num 1
    def_row = ["Definition", "1", "record"]
    for f in fields: # standard fields
        def_row.extend([f, "1", ""])
    
    # Add Developer Field columns to Definition
    # developer_data_index, field_definition_number, value
    def_row.extend(["developer_data_index", "1", "", "field_definition_number", "1", "", "value", "1", ""])
    
    writer.writerow(def_row)
    
    # Now write data
    for sample in data["samples"]:
        ts = _iso_to_garmin_time(sample["timestamp"])
        hr = sample.get("hr", "")
        pwr = sample.get("power", "")
        cad = sample.get("cadence", "")
        spd = sample.get("speed", "")
        alpha1 = sample.get("alpha1", "")
        
        row = ["Data", "1", "record", "timestamp", ts, "", "heart_rate", hr, "bpm", "power", pwr, "watts", "cadence", cad, "rpm", "speed", spd, "m/s"]
        
        # Always write the developer field columns, even if empty
        if alpha1 != "":
            # dev_index=0, field_def_num=0, value=alpha1
            row.extend(["0", "", "0", "", str(alpha1), "score"])
        else:
            # write empty
            row.extend(["", "", "", "", "", ""])
            
        writer.writerow(row)
        
        # Write HRV if present (Message 2 - as before)
        if has_rr:
            rr = sample.get("rr", [])
            if rr:
                rr_str = "|".join([str(x) for x in rr])
                writer.writerow(["Data", "2", "hrv", "time", rr_str, "s"])

    # --- Summary Calculation ---
    total_records = len(data["samples"])
    if total_records > 0:
        start_ts = _iso_to_garmin_time(data["samples"][0]["timestamp"])
        end_ts = _iso_to_garmin_time(data["samples"][-1]["timestamp"])
        total_elapsed_time = end_ts - start_ts
        total_timer_time = total_elapsed_time # Assuming no pauses for now
        
        # Aggregates
        pwrs = [float(s["power"]) for s in data["samples"] if "power" in s and s["power"] is not None]
        hrs = [float(s["hr"]) for s in data["samples"] if "hr" in s and s["hr"] is not None]
        cads = [float(s["cadence"]) for s in data["samples"] if "cadence" in s and s["cadence" ] is not None]
        speeds = [float(s["speed"]) for s in data["samples"] if "speed" in s and s["speed"] is not None]
        
        avg_power = sum(pwrs) / len(pwrs) if pwrs else 0
        max_power = max(pwrs) if pwrs else 0
        avg_hr = sum(hrs) / len(hrs) if hrs else 0
        max_hr = max(hrs) if hrs else 0
        avg_cad = sum(cads) / len(cads) if cads else 0
        max_cad = max(cads) if cads else 0
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        
        # Distance (approximate if not in samples, or take last if cumulative)
        # We wrote 'speed' throughout, let's assume valid speed
        # Simple Riemann sum for distance if not provided
        total_distance = sum(speeds) # 1 sec intervals = speed * 1
        
        # 5. Lap Message (Msg ID 19)
        # Definition
        # timestamp, start_time, total_elapsed_time, total_timer_time, total_distance, 
        # avg_speed, max_speed, avg_heart_rate, max_heart_rate, avg_cadence, max_cadence, avg_power, max_power
        writer.writerow(["Definition", "3", "lap", 
                         "timestamp", "1", "", 
                         "start_time", "1", "", 
                         "total_elapsed_time", "1", "s",
                         "total_timer_time", "1", "s",
                         "total_distance", "1", "m",
                         "avg_speed", "1", "m/s",
                         "max_speed", "1", "m/s",
                         "avg_heart_rate", "1", "bpm",
                         "max_heart_rate", "1", "bpm",
                         "avg_cadence", "1", "rpm",
                         "max_cadence", "1", "rpm",
                         "avg_power", "1", "watts",
                         "max_power", "1", "watts"])
        
        writer.writerow(["Data", "3", "lap", 
                         end_ts, "", 
                         start_ts, "",
                         total_elapsed_time, "s",
                         total_timer_time, "s",
                         f"{total_distance:.2f}", "m",
                         f"{avg_speed:.3f}", "m/s",
                         f"{max_speed:.3f}", "m/s",
                         int(avg_hr), "bpm",
                         int(max_hr), "bpm",
                         int(avg_cad), "rpm",
                         int(max_cad), "rpm",
                         int(avg_power), "watts",
                         int(max_power), "watts"])

        # 6. Session Message (Msg ID 18)
        # Definition - similar to Lap + sport
        writer.writerow(["Definition", "4", "session", 
                         "timestamp", "1", "", 
                         "start_time", "1", "", 
                         "total_elapsed_time", "1", "s",
                         "total_timer_time", "1", "s",
                         "total_distance", "1", "m",
                         "avg_speed", "1", "m/s",
                         "max_speed", "1", "m/s",
                         "avg_heart_rate", "1", "bpm",
                         "max_heart_rate", "1", "bpm",
                         "avg_cadence", "1", "rpm",
                         "max_cadence", "1", "rpm",
                         "avg_power", "1", "watts",
                         "max_power", "1", "watts",
                         "sport", "1", "",
                         "sub_sport", "1", ""]) # generic

        # Sport: Cycling = 2
        # SubSport: Generic = 0
        writer.writerow(["Data", "4", "session", 
                         end_ts, "", 
                         start_ts, "",
                         total_elapsed_time, "s",
                         total_timer_time, "s",
                         f"{total_distance:.2f}", "m",
                         f"{avg_speed:.3f}", "m/s",
                         f"{max_speed:.3f}", "m/s",
                         int(avg_hr), "bpm",
                         int(max_hr), "bpm",
                         int(avg_cad), "rpm",
                         int(max_cad), "rpm",
                         int(avg_power), "watts",
                         int(max_power), "watts",
                         "2", "", # Cycling
                         "0", ""])

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

