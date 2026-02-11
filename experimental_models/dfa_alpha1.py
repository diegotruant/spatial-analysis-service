import numpy as np
from typing import List, Tuple, Optional, Dict

class DFAAlpha1:
    """
    Implementation of Detrended Fluctuation Analysis (DFA) Alpha-1 for HRV analysis.
    Based on Rogers et al. (2021) and standard fractal analysis methods.
    
    Alpha-1 (short-range scaling exponent) is used to estimate the Aerobic Threshold (LT1/VT1).
    - Alpha-1 > 0.75: Below LT1 (Aerobic)
    - Alpha-1 approx 0.75: At LT1
    - Alpha-1 < 0.75: Above LT1 (Mixed/Anaerobic)
    - Alpha-1 approx 0.5: Uncorrelated (White noise) - often seen near max effort
    """
    
    @staticmethod
    def calculate_alpha1(rr_intervals: List[float], scale_min: int = 4, scale_max: int = 16) -> Tuple[float, float]:
        """
        Calculates Alpha-1 from a series of RR intervals.
        
        Args:
            rr_intervals: List of RR intervals in milliseconds (or seconds).
            scale_min: Minimum box size (default 4 beats).
            scale_max: Maximum box size (default 16 beats for short-term scaling).
            
        Returns:
            Tuple of (alpha1, r_squared)
            alpha1: The slope of log(F(n)) vs log(n).
            r_squared: Quality of the linear fit (should be > 0.9 for validity).
        """
        rr = np.array(rr_intervals)
        
        # 1. Preprocessing: Basic outlier removal (simple artifact correction)
        # In a real production system, clearer artifact correction is needed (e.g. Kubios style)
        rr = DFAAlpha1._remove_artifacts(rr)
        
        n_samples = len(rr)
        if n_samples < scale_max * 2:
            return 0.0, 0.0 # Not enough data
            
        # 2. Integration: Cumulative sum of (RR - meanRR)
        rr_mean = np.mean(rr)
        y = np.cumsum(rr - rr_mean)
        
        # 3. Define scales (box sizes)
        # We use logarithmic spacing for scales
        scales = np.unique(np.logspace(np.log10(scale_min), np.log10(scale_max), num=10).astype(int))
        scales = scales[scales <= n_samples // 4] # Ensure at least 4 windows
        
        if len(scales) < 3:
            return 0.0, 0.0
            
        fluctuations = []
        
        # 4. Detrending and Fluctuation Calculation
        for s in scales:
            f_n = DFAAlpha1._calculate_fluctuation(y, s)
            fluctuations.append(f_n)
            
        # 5. Calculate Slope (Alpha-1)
        # Fit line to log-log plot
        log_scales = np.log10(scales)
        log_fluctuations = np.log10(fluctuations)
        
        slope, intercept = np.polyfit(log_scales, log_fluctuations, 1)
        
        # Calculate R-squared
        y_pred = slope * log_scales + intercept
        ss_res = np.sum((log_fluctuations - y_pred) ** 2)
        ss_tot = np.sum((log_fluctuations - np.mean(log_fluctuations)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)
        
        return slope, r_squared

    @staticmethod
    def calculate_rolling_alpha1(
        rr_intervals: List[float], 
        window_size_seconds: int = 120, 
        step_seconds: int = 30
    ) -> List[Dict[str, float]]:
        """
        Calculates Alpha-1 in a rolling window to show trends over time.
        
        Args:
            rr_intervals: List of RR intervals in milliseconds.
            window_size_seconds: Size of the window in seconds (standard is 2 min).
            step_seconds: Step size for the sliding window.
            
        Returns:
            List of Dict with keys: 'time' (seconds from start), 'alpha1', 'r_squared'.
        """
        rr = np.array(rr_intervals)
        rr_clean = DFAAlpha1._remove_artifacts(rr)
        
        # Calculate cumulative time to map beats to seconds
        # RR is in ms, so divide by 1000
        beat_times = np.cumsum(rr_clean) / 1000.0
        total_duration = beat_times[-1]
        
        results = []
        
        current_time = window_size_seconds
        
        while current_time <= total_duration:
            start_time = current_time - window_size_seconds
            
            # Find indices corresponding to this time window
            # We want beats where: start_time <= beat_time <= current_time
            mask = (beat_times >= start_time) & (beat_times <= current_time)
            window_rr = rr_clean[mask]
            
            if len(window_rr) > 50: # Minimum beats for validity
                alpha1, r2 = DFAAlpha1.calculate_alpha1(window_rr, scale_min=4, scale_max=16)
                if r2 > 0.5: # Filter extremely poor fits
                    results.append({
                        "time": int(current_time), # Timestamp at end of window
                        "alpha1": round(alpha1, 2),
                        "r_squared": round(r2, 2)
                    })
            
            current_time += step_seconds
            
        return results

    @staticmethod
    def _calculate_fluctuation(y: np.ndarray, s: int) -> float:
        """
        Calculates F(s): RMS fluctuation for window size s.
        """
        n = len(y)
        n_windows = n // s
        
        residual_sum_sq = 0.0
        
        for i in range(n_windows):
            start = i * s
            end = start + s
            segment = y[start:end]
            x = np.arange(s)
            
            # Linear detrending (degree 1)
            coef = np.polyfit(x, segment, 1)
            trend = np.polyval(coef, x)
            
            residuals = segment - trend
            residual_sum_sq += np.sum(residuals ** 2)
            
        # RMS calculation
        # F(s) = sqrt( (1/samples) * sum(residuals^2) )
        # Here samples = n_windows * s (ignoring remainder)
        f_s = np.sqrt(residual_sum_sq / (n_windows * s))
        return f_s

    @staticmethod
    def _remove_artifacts(rr: np.ndarray, threshold_percent: float = 20.0) -> np.ndarray:
        """
        Simple artifact correction filter.
        Removes RR intervals that deviate > threshold% from the local median (window 5).
        Replaces them with the median.
        """
        rr_clean = rr.copy()
        n = len(rr)
        window = 5
        
        for i in range(2, n - 2):
            local_window = rr[i-2 : i+3]
            median = np.median(local_window)
            if median == 0: continue
            
            diff = abs(rr[i] - median)
            if (diff / median) * 100 > threshold_percent:
                rr_clean[i] = median
                
        return rr_clean
