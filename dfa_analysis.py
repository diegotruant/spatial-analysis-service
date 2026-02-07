"""
DFA (Detrended Fluctuation Analysis) Alpha 1 Engine
Identifies VT1 (Ventilatory Threshold 1) from RR interval data during exercise
"""
import numpy as np
from scipy.stats import linregress
from typing import Optional


def calculate_dfa_alpha1(
    rr_intervals: list[int],
    min_window: int = 4,
    max_window: int = 16
) -> dict:
    """
    Calculate DFA alpha 1 from RR intervals.
    
    DFA alpha 1 interpretation:
    - α1 > 0.75: Below VT1 (aerobic, well-correlated/organized HRV)
    - α1 = 0.5-0.75: Around VT1 (transition zone)
    - α1 < 0.5: Above VT1 (anaerobic, decorrelated/chaotic HRV)
    
    Args:
        rr_intervals: List of RR intervals in milliseconds
        min_window: Minimum box size for DFA (default 4 beats)
        max_window: Maximum box size for DFA (default 16 beats)
    
    Returns:
        dict with:
            - alpha1: DFA alpha 1 value
            - status: "BELOW_VT1", "AT_VT1", or "ABOVE_VT1"
            - confidence: "high", "medium", "low"
            - interpretation: Human-readable description
            - metadata: Additional calculation details
    """
    # Validate input
    if len(rr_intervals) < 60:
        return {
            "alpha1": None,
            "status": "INSUFFICIENT_DATA",
            "confidence": "none",
            "interpretation": "Need at least 60 RR intervals (approximately 1 minute of data)",
            "metadata": {"samples": len(rr_intervals)}
        }
    
    try:
        # Convert to numpy array
        rr = np.array(rr_intervals, dtype=float)
        
        # Remove mean (detrending step 1)
        rr_mean = np.mean(rr)
        rr_detrended = rr - rr_mean
        
        # Cumulative sum (integration)
        rr_cumsum = np.cumsum(rr_detrended)
        
        # Calculate fluctuations for different box sizes
        box_sizes = np.arange(min_window, min(max_window + 1, len(rr) // 4))
        fluctuations = []
        
        for box_size in box_sizes:
            n_boxes = len(rr_cumsum) // box_size
            if n_boxes < 2:
                continue
                
            # Truncate to fit complete boxes
            truncated = rr_cumsum[:n_boxes * box_size]
            boxes = truncated.reshape(n_boxes, box_size)
            
            # Detrend each box (fit linear trend)
            fluctuation = 0
            for box in boxes:
                t = np.arange(box_size)
                # Linear fit
                coeffs = np.polyfit(t, box, 1)
                trend = np.polyval(coeffs, t)
                # RMS deviation from trend
                fluctuation += np.sum((box - trend) ** 2)
            
            # Average fluctuation for this box size
            F = np.sqrt(fluctuation / (n_boxes * box_size))
            fluctuations.append(F)
        
        if len(fluctuations) < 3:
            return {
                "alpha1": None,
                "status": "INSUFFICIENT_DATA",
                "confidence": "none",
                "interpretation": "Not enough data points for reliable DFA calculation",
                "metadata": {"samples": len(rr_intervals), "valid_box_sizes": len(fluctuations)}
            }
        
        # Log-log linear regression to get slope (alpha1)
        log_boxes = np.log(box_sizes[:len(fluctuations)])
        log_fluctuations = np.log(fluctuations)
        
        slope, intercept, r_value, p_value, std_err = linregress(log_boxes, log_fluctuations)
        alpha1 = slope
        r_squared = r_value ** 2
        
        # Determine status and confidence
        if alpha1 > 0.75:
            status = "BELOW_VT1"
            interpretation = "Aerobic zone - well below ventilatory threshold. Good for base training."
        elif alpha1 >= 0.5:
            status = "AT_VT1"
            interpretation = "Transition zone - near or at ventilatory threshold. Maximum aerobic intensity."
        else:
            status = "ABOVE_VT1"
            interpretation = "Above ventilatory threshold - mixed aerobic/anaerobic metabolism."
        
        # Confidence based on R² and data quality
        if r_squared > 0.95:
            confidence = "high"
        elif r_squared > 0.85:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "alpha1": round(alpha1, 3),
            "status": status,
            "confidence": confidence,
            "interpretation": interpretation,
            "metadata": {
                "r_squared": round(r_squared, 4),
                "samples": len(rr_intervals),
                "box_sizes_used": box_sizes[:len(fluctuations)].tolist(),
                "std_error": round(std_err, 4)
            }
        }
        
    except Exception as e:
        return {
            "alpha1": None,
            "status": "ERROR",
            "confidence": "none",
            "interpretation": f"Calculation failed: {str(e)}",
            "metadata": {"error": str(e)}
        }


def analyze_rr_stream(
    rr_data: list[dict],
    window_seconds: int = 120
) -> list[dict]:
    """
    Analyze a stream of timestamped RR intervals with sliding window.
    
    Args:
        rr_data: List of {timestamp, elapsed, rr} dictionaries
        window_seconds: Size of sliding window in seconds (default 2 minutes)
    
    Returns:
        List of DFA results with timestamps
    """
    results = []
    
    # Flatten RR intervals with timestamps
    all_rr = []
    for sample in rr_data:
        elapsed = sample.get('elapsed', 0)
        rr_intervals = sample.get('rr', [])
        for rr in rr_intervals:
            all_rr.append({'elapsed': elapsed, 'rr': rr})
    
    if len(all_rr) < 60:
        return []
    
    # Sliding window analysis
    current_window = []
    last_calc_time = -window_seconds
    
    for i, item in enumerate(all_rr):
        elapsed = item['elapsed']
        current_window.append(item['rr'])
        
        # Calculate DFA every 30 seconds
        if elapsed - last_calc_time >= 30:
            # Get last window_seconds worth of data
            window_start_time = elapsed - window_seconds
            window_rr = [x['rr'] for x in all_rr if window_start_time <= x['elapsed'] <= elapsed]
            
            if len(window_rr) >= 60:
                dfa_result = calculate_dfa_alpha1(window_rr)
                if dfa_result['alpha1'] is not None:
                    results.append({
                        'timestamp': elapsed,
                        'window_size': len(window_rr),
                        **dfa_result
                    })
                    last_calc_time = elapsed
    
    return results


def detect_vt1_from_activity(
    rr_data: list[dict],
    power_data: Optional[list[float]] = None
) -> dict:
    """
    Detect VT1 from complete activity data.
    
    Args:
        rr_data: List of {timestamp, elapsed, rr} dictionaries
        power_data: Optional power data (1 value per second)
    
    Returns:
        dict with VT1 detection results
    """
    # Analyze RR stream
    dfa_results = analyze_rr_stream(rr_data, window_seconds=120)
    
    if not dfa_results:
        return {
            "vt1_detected": False,
            "message": "Insufficient RR data for VT1 detection"
        }
    
    # Find transition point where alpha1 crosses 0.75 threshold
    vt1_candidates = []
    for i in range(1, len(dfa_results)):
        prev = dfa_results[i-1]
        curr = dfa_results[i]
        
        # Look for crossing from above to below 0.75
        if prev['alpha1'] > 0.75 and curr['alpha1'] <= 0.75:
            vt1_candidates.append({
                'time': curr['timestamp'],
                'alpha1': curr['alpha1'],
                'confidence': curr['confidence']
            })
    
    if not vt1_candidates:
        # Check if always above or always below
        avg_alpha1 = np.mean([r['alpha1'] for r in dfa_results])
        if avg_alpha1 > 0.75:
            return {
                "vt1_detected": False,
                "message": "Activity appears to be entirely below VT1 (aerobic)",
                "avg_alpha1": round(avg_alpha1, 3),
                "dfa_timeline": dfa_results
            }
        else:
            return {
                "vt1_detected": False,
                "message": "Activity appears to be entirely above VT1 (high intensity)",
                "avg_alpha1": round(avg_alpha1, 3),
                "dfa_timeline": dfa_results
            }
    
    # Use first high-confidence VT1 crossing
    best_vt1 = max(vt1_candidates, key=lambda x: 1 if x['confidence'] == 'high' else 0.5 if x['confidence'] == 'medium' else 0.1)
    
    result = {
        "vt1_detected": True,
        "vt1_time_seconds": best_vt1['time'],
        "vt1_alpha1": best_vt1['alpha1'],
        "confidence": best_vt1['confidence'],
        "dfa_timeline": dfa_results
    }
    
    # Add power at VT1 if available
    if power_data and best_vt1['time'] < len(power_data):
        vt1_power = power_data[best_vt1['time']]
        result['vt1_power'] = round(vt1_power, 1)
    
    return result
