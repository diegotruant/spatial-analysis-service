import polars as pl
import random
from typing import Optional, List, Any

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

def analyze_activity(df: pl.DataFrame, ftp: float, rhr: Optional[float] = None) -> dict:
    """
    Performs full analysis on a DataFrame containing 'power' column.
    """
    power_series = df["power"]
    duration = len(power_series)
    
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

    return {
        "duration_seconds": duration,
        "normalized_power": round(np_val, 2),
        "tss": round(tss, 2),
        "intensity_factor": round(if_val, 3),
        "peak_powers": peak_powers,
        "variability_index": round(vi, 2),
        "efficiency_factor": round(ef, 2) if ef else None,
        "decoupling": round(decoupling, 2) if decoupling else None
    }

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
