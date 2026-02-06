import polars as pl
from typing import Optional, Literal

TrafficLightStatus = Literal['GREEN', 'YELLOW', 'RED']
OverreachingStatus = Literal['NORMAL', 'FOR', 'NFOR', 'WARNING']

class HRVEngine:
    @staticmethod
    def calculate_baseline(values: list[float], window_days: int = 7) -> dict:
        """
        Calculate dynamic baseline from recent HRV measurements.
        Standard: 7-30 day rolling average.
        """
        if len(values) < 3:
            return {
                "mean": 0, "std_dev": 0, "min": 0, "max": 0,
                "normal_range": {"lower": 0, "upper": 0},
                "sample_size": 0
            }

        # Using Polars for statistical analysis
        s = pl.Series(values[-window_days:])
        mean = s.mean() or 0
        std_dev = s.std() or 0
        
        return {
            "mean": round(mean, 1),
            "std_dev": round(std_dev, 1),
            "min": float(s.min() or 0),
            "max": float(s.max() or 0),
            "normal_range": {
                "lower": round(mean * 0.90, 1),
                "upper": round(mean * 1.10, 1)
            },
            "sample_size": len(s)
        }

    @staticmethod
    def calculate_traffic_light(current: float, baseline: float) -> dict:
        if baseline <= 0:
            return {"status": "YELLOW", "deviation": 0.0}

        deviation = ((current - baseline) / baseline) * 100
        
        status: TrafficLightStatus = "RED"
        if deviation >= -5:
            status = "GREEN"
        elif deviation >= -15:
            status = "YELLOW"
            
        return {"status": status, "deviation": round(deviation, 1)}

    @staticmethod
    def get_recommendation(status: TrafficLightStatus, deviation: float, days_depressed: int = 0) -> str:
        if status == 'GREEN':
            return '🟢 Ottimo! HRV elevata - Finestra ottimale per allenamento intenso.' if deviation > 5 \
                else '🟢 Pronto per allenarsi - Sistema parasimpatico recuperato.'
        elif status == 'YELLOW':
            return f'🟠 Attenzione: HRV ridotta per {days_depressed} giorni. Riduci volume/intensità del 20-30%.' if days_depressed >= 2 \
                else '🟠 HRV leggermente depressa - Modula sessione: riduci volume 20% o intensità al 90%.'
        else: # RED
            return f'🔴 ALERT: Pattern depresso {days_depressed} giorni consecutivi. Settimana scarico.' if days_depressed >= 3 \
                else '🔴 Sistema parasimpatico soppresso - Annulla sessione intensa. Recupero attivo o riposo.'

    @staticmethod
    def analyze_overreaching(history: list[dict], baseline: float) -> dict:
        """
        Analyze overreaching status based on HRV pattern (last 21 days).
        """
        # Filter valid recent records
        valid = [h['hrv'] for h in history if h.get('hrv') and h['hrv'] > 0][-21:]
        
        if len(valid) < 5 or baseline <= 0:
            return {
                "status": "NORMAL", "days_depressed": 0, "avg_deviation": 0,
                "recommendation": "Dati insufficienti.", "severity": "low"
            }

        # Calculate consecutive days with deviation < -15%
        consecutive = 0
        max_consecutive = 0
        depressed_sum = 0
        depressed_count = 0
        
        # We look from newest to oldest to find current streak
        for val in reversed(valid):
            dev = ((val - baseline) / baseline) * 100
            if dev < -15:
                consecutive += 1
                depressed_sum += dev
                depressed_count += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                # If the most recent isn't depressed, current streak is 0
                if consecutive == 0: break 
                consecutive = 0

        avg_dev = round(depressed_sum / depressed_count, 1) if depressed_count > 0 else 0
        
        status: OverreachingStatus = "NORMAL"
        severity: Literal['low', 'medium', 'high'] = "low"
        
        if max_consecutive >= 11:
            status, severity = "NFOR", "high"
        elif max_consecutive >= 3:
            status, severity = "FOR", "medium"
        elif max_consecutive >= 1:
            status, severity = "WARNING", "medium"
            
        return {
            "status": status,
            "days_depressed": max_consecutive,
            "avg_deviation": avg_dev,
            "severity": severity
        }
