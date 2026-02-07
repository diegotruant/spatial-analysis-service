import polars as pl
import random
from typing import Optional, List, Any

def calculate_air_density(altitude: float, temperature: float = 15.0) -> float:
    """
    Calculates air density at given altitude and temperature.
    
    Args:
        altitude: Altitude in meters above sea level
        temperature: Temperature in Celsius (default: 15°C standard conditions)
    
    Returns:
        Air density relative to sea level (1.0 = sea level)
    
    Formula: ρ = ρ₀ × (1 - 0.0065 × alt / 288.15)^5.255
    Temperature correction: -0.5% per °C above 15°C
    """
    # Standard atmospheric pressure formula
    # Barometric formula for air density
    pressure_ratio = (1 - 0.0065 * altitude / 288.15) ** 5.255
    
    # Temperature correction relative to standard (15°C)
    # Air density decreases by ~0.5% per degree Celsius increase
    temp_correction = 1 - 0.005 * (temperature - 15.0)
    
    # Combined density ratio
    density_ratio = pressure_ratio * temp_correction
    
    return max(0.5, min(1.0, density_ratio))  # Clamp between 0.5 and 1.0


def normalize_power_for_altitude(power: float, altitude: float, temperature: float = 15.0) -> float:
    """
    Normalizes power output to sea level equivalent.
    
    At altitude, air resistance is lower, so the same power produces higher speed.
    This function converts altitude power to sea-level equivalent.
    
    Args:
        power: Measured power in watts
        altitude: Altitude in meters
        temperature: Temperature in Celsius
    
    Returns:
        Normalized power (sea level equivalent)
    
    Formula: P_normalized = P_measured × (ρ₀ / ρ_actual)^(1/3)
    The 1/3 exponent accounts for power being proportional to velocity³
    """
    if altitude <= 0 and abs(temperature - 15.0) < 1.0:
        return power  # No correction needed at sea level and standard temp
    
    density_ratio = calculate_air_density(altitude, temperature)
    
    # Power correction factor
    # Power ∝ v³, and v ∝ (P/ρ)^(1/3), so P_normalized = P × (1/ρ)^(1/3)
    correction_factor = (1.0 / density_ratio) ** (1.0 / 3.0)
    
    return power * correction_factor


def calculate_np(power_series: pl.Series) -> float:
    """
    Calculates Normalized Power (NP) using Polars.
    1. 30s rolling average
    2. Power to the 4th
    3. Average of results
    4. 4th root
    """
    if len(power_series) < 30:
        return power_series.mean() if len(power_series) > 0 else 0.0

    # Rolling 30s average
    rolling_avg = power_series.rolling_mean(window_size=30)
    
    # Drop nulls from the beginning of the rolling window
    valid_rolling = rolling_avg.drop_nulls()
    
    if len(valid_rolling) == 0:
        return 0.0

    # Raise to 4th power, take mean, then 4th root
    avg_pow4 = (valid_rolling ** 4).mean()
    np_val = avg_pow4 ** 0.25
    
    return float(np_val)

def calculate_tss(np_val: float, ftp: float, duration_seconds: int) -> float:
    """Calculates Training Stress Score (TSS)"""
    if ftp <= 0:
        return 0.0
    intensity_factor = np_val / ftp
    tss = (duration_seconds * np_val * intensity_factor) / (ftp * 3600) * 100
    return float(tss)

def calculate_peak_powers(power_series: pl.Series) -> dict[str, float]:
    """
    Calculates peak powers for various durations using Polars rolling_mean and max.
    """
    return {
        "5s": float(power_series.rolling_mean(window_size=5).max() or 0),
        "1m": float(power_series.rolling_mean(window_size=60).max() or 0),
        "5m": float(power_series.rolling_mean(window_size=300).max() or 0),
        "20m": float(power_series.rolling_mean(window_size=1200).max() or 0),
    }

def analyze_activity(
    df: pl.DataFrame, 
    ftp: float, 
    w_prime: Optional[float] = None,
    altitude_data: Optional[list[float]] = None,
    temperature: Optional[float] = None
) -> dict:
    """
    Performs full analysis on a DataFrame containing 'power' column.
    Now supports altitude/temperature correction for more accurate power metrics.
    
    Args:
        df: DataFrame with 'power' column (and optionally 'heart_rate', 'cadence')
        ftp: Functional Threshold Power
        w_prime: W' (anaerobic capacity) - kept for compatibility
        altitude_data: Optional list of altitude values (meters) for each second
        temperature: Optional average temperature (Celsius) for the activity
    """
    power_series = df["power"]
    duration = len(power_series)
    
    # Altitude correction if data provided
    altitude_corrected = False
    avg_altitude = 0.0
    air_density_ratio = 1.0
    
    if altitude_data and len(altitude_data) == len(power_series):
        # Calculate average altitude for the activity
        avg_altitude = sum(altitude_data) / len(altitude_data)
        temp = temperature if temperature is not None else 15.0
        
        # Only apply correction if significant altitude (>200m) or non-standard temp
        if avg_altitude > 200 or abs(temp - 15.0) > 5.0:
            air_density_ratio = calculate_air_density(avg_altitude, temp)
            
            # Normalize each power value
            normalized_power_values = [
                normalize_power_for_altitude(p, alt, temp)
                for p, alt in zip(power_series.to_list(), altitude_data)
            ]
            power_series = pl.Series(normalized_power_values)
            altitude_corrected = True
    
    np_val = calculate_np(power_series)
    
    # Variability Index (VI) = NP / AvgPower
    avg_power = power_series.mean()
    if avg_power is None or avg_power == 0:
        avg_power = 1.0 # Avoid division by zero if mean is 0 or None
    vi = np_val / avg_power
    
    # Training Stress Score
    tss = calculate_tss(np_val, ftp, duration)
    
    # Intensity Factor
    if_val = np_val / ftp if ftp > 0 else 0.0
    
    # Efficiency Factor (EF) and Aerobic Decoupling (if HR exists)
    ef = None
    decoupling = None
    if "heart_rate" in df.columns:
        hr_series = df["heart_rate"].drop_nulls()
        if len(hr_series) > 0:
            avg_hr = hr_series.mean()
            if avg_hr is not None and avg_hr > 0:
                ef = avg_power / avg_hr
            
            # Decoupling: EF first half vs EF second half
            half = len(df) // 2
            first_half_df = df.head(half)
            second_half_df = df.tail(half)

            # Ensure both halves have power and HR data
            if "power" in first_half_df.columns and "heart_rate" in first_half_df.columns and \
               "power" in second_half_df.columns and "heart_rate" in second_half_df.columns:
                
                first_half_avg_power = first_half_df["power"].mean()
                first_half_avg_hr = first_half_df["heart_rate"].mean()
                second_half_avg_power = second_half_df["power"].mean()
                second_half_avg_hr = second_half_df["heart_rate"].mean()

                if (first_half_avg_power is not None and first_half_avg_power > 0 and
                    first_half_avg_hr is not None and first_half_avg_hr > 0 and
                    second_half_avg_power is not None and second_half_avg_power > 0 and
                    second_half_avg_hr is not None and second_half_avg_hr > 0):
                    
                    ef1 = first_half_avg_power / first_half_avg_hr
                    ef2 = second_half_avg_power / second_half_avg_hr
                    decoupling = ((ef1 - ef2) / ef1) * 100 if ef1 > 0 else None

    # Calculate peak powers
    peak_powers = calculate_peak_powers(power_series)

    result = {
        "duration_seconds": duration,
        "normalized_power": round(np_val, 2),
        "tss": round(tss, 2),
        "intensity_factor": round(if_val, 3),
        "peak_powers": peak_powers,
        "variability_index": round(vi, 2),
        "efficiency_factor": round(ef, 2) if ef else None,
        "decoupling": round(decoupling, 2) if decoupling else None
    }
    
    # Add altitude correction metadata if applied
    if altitude_corrected:
        result["altitude_correction"] = {
            "applied": True,
            "avg_altitude_m": round(avg_altitude, 1),
            "temperature_c": temperature if temperature is not None else 15.0,
            "air_density_ratio": round(air_density_ratio, 3),
            "correction_info": f"Power normalized from {round(avg_altitude, 0)}m to sea level"
        }
    else:
        result["altitude_correction"] = {
            "applied": False,
            "reason": "No altitude data provided" if not altitude_data else "Altitude <200m, no correction needed"
        }
    
    return result

def calculate_pmc_trends(tss_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Calculates PMC trends (CTL, ATL, TSB) from TSS history.
    Now includes Freshness Alert detection for rapid TSB increases.
    tss_history: List of {"date": "YYYY-MM-DD", "tss": float}
    """
    if not tss_history:
        return []

    # Sort by date
    history = sorted(tss_history, key=lambda x: x["date"])
    
    ctl = 0.0
    atl = 0.0
    results = []

    # Time constants (standard Coggan values)
    ctl_tc = 42.0
    atl_tc = 7.0

    for i, entry in enumerate(history):
        tss = float(entry.get("tss", 0.0))
        
        # Exponentially Weighted Moving Average
        # New CTL = Old CTL + (TSS - Old CTL) / 42
        ctl = ctl + (tss - ctl) / ctl_tc
        atl = atl + (tss - atl) / atl_tc
        tsb = ctl - atl
        
        # TSB Freshness Alert Detection
        # Based on expert feedback: rapid TSB increase may indicate loss of chronic adaptations
        freshness_alert = None
        tsb_delta_7d = 0.0
        
        # Calculate TSB change over last 7 days
        if i >= 7:
            tsb_7days_ago = results[i - 7]["tsb"]
            tsb_delta_7d = tsb - tsb_7days_ago
            
            # Alert conditions:
            # 1. TSB is above +20 (high freshness)
            # 2. TSB increased >15 points in <7 days (rapid increase)
            if tsb > 20 and tsb_delta_7d > 15:
                freshness_alert = {
                    "status": "DETRAINING_RISK",
                    "message": "⚠️ TSB salito troppo rapidamente - Rischio perdita adattamenti cronici",
                    "tsb_delta_7d": round(tsb_delta_7d, 1),
                    "recommendation": "Reintrodurre carico gradualmente per mantenere fitness (CTL)"
                }
            elif tsb > 25:
                freshness_alert = {
                    "status": "VERY_FRESH",
                    "message": "🏁 Picco di forma - Finestra ottimale per competizione",
                    "tsb_delta_7d": round(tsb_delta_7d, 1),
                    "recommendation": "Mantieni questo livello per max 5-7 giorni prima della gara"
                }
            elif tsb > 20:
                freshness_alert = {
                    "status": "FRESH",
                    "message": "✨ Forma elevata - Ready to race",
                    "tsb_delta_7d": round(tsb_delta_7d, 1),
                    "recommendation": "Ottimo per competizioni o allenamenti di qualità"
                }
        
        results.append({
            "date": entry["date"],
            "tss": tss,
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
            "tsb_delta_7d": round(tsb_delta_7d, 1),
            "freshness_alert": freshness_alert
        })

    return results

# Example usage with mock data
if __name__ == "__main__":
    # Create 1 hour of mock data (3600 seconds)
    # Average 200W with some noise using standard random
    mock_power = [max(0, 200 + random.uniform(-50, 50)) for _ in range(3600)]
    df = pl.DataFrame({"power": mock_power})
    
    results = analyze_activity(df, ftp=250)
    
    print("--- Analysis Results (Polars) ---")
    print(f"Duration: {results['duration_seconds']}s")
    print(f"NP: {results['normalized_power']} W")
    print(f"TSS: {results['tss']}")
    print(f"IF: {results['intensity_factor']}")
    print(f"Peak Powers: {results['peak_powers']}")
