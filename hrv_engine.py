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
        Now includes Coefficient of Variation (CV) for stability assessment.
        """
        if len(values) < 3:
            return {
                "mean": 0, "std_dev": 0, "min": 0, "max": 0,
                "normal_range": {"lower": 0, "upper": 0},
                "sample_size": 0,
                "cv": 0,
                "cv_status": "INSUFFICIENT_DATA",
                "stability": "unknown"
            }

        # Using Polars for statistical analysis
        s = pl.Series(values[-window_days:])
        mean = s.mean() or 0
        std_dev = s.std() or 0
        
        # Calculate Coefficient of Variation (CV)
        # CV = (std_dev / mean) × 100
        # High CV indicates nervous system instability even if mean HRV is good
        cv = (std_dev / mean * 100) if mean > 0 else 0
        
        # Determine CV status and stability
        # Based on expert feedback and HRV literature
        if cv < 10:
            cv_status = "OPTIMAL"
            stability = "Stabilità ottimale - Sistema nervoso in equilibrio"
        elif cv < 20:
            cv_status = "MODERATE"
            stability = "Variabilità moderata - Monitorare l'andamento"
        else:
            cv_status = "UNSTABLE"
            stability = "⚠️ Instabilità rilevata - Sistema nervoso in pre-allarme"
        
        return {
            "mean": round(mean, 1),
            "std_dev": round(std_dev, 1),
            "min": float(s.min() or 0),
            "max": float(s.max() or 0),
            "normal_range": {
                "lower": round(mean * 0.90, 1),
                "upper": round(mean * 1.10, 1)
            },
            "sample_size": len(s),
            "cv": round(cv, 1),
            "cv_status": cv_status,
            "stability": stability
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
    def get_recommendation(status: TrafficLightStatus, deviation: float, days_depressed: int = 0, cv_status: str = "OPTIMAL") -> str:
        """
        Generate training recommendation based on HRV status and CV stability.
        CV (Coefficient of Variation) adds an additional layer of analysis:
        - High CV (>20%) indicates nervous system instability even with good mean HRV
        """
        # Construct base recommendation based on traffic light
        if status == 'GREEN':
            base_rec = '🟢 Ottimo! HRV elevata - Finestra ottimale per allenamento intenso.' if deviation > 5 \
                else '🟢 Pronto per allenarsi - Sistema parasimpatico recuperato.'
        elif status == 'YELLOW':
            base_rec = f'🟠 Attenzione: HRV ridotta per {days_depressed} giorni. Riduci volume/intensità del 20-30%.' if days_depressed >= 2 \
                else '🟠 HRV leggermente depressa - Modula sessione: riduci volume 20% o intensità al 90%.'
        else: # RED
            base_rec = f'🔴 ALERT: Pattern depresso {days_depressed} giorni consecutivi. Settimana scarico.' if days_depressed >= 3 \
                else '🔴 Sistema parasimpatico soppresso - Annulla sessione intensa. Recupero attivo o riposo.'
        
        # Add CV-based warning if instability is detected
        if cv_status == "UNSTABLE":
            if status == 'GREEN':
                base_rec += ' ⚠️ Attenzione: HRV instabile (CV elevato). Considera allenamento moderato invece di intenso.'
            else:
                base_rec += ' ⚠️ HRV molto instabile - Priorità al recupero.'
        elif cv_status == "MODERATE" and status == 'GREEN':
            base_rec += ' Nota: HRV con variabilità moderata - Mantieni monitoraggio costante.'
        
        return base_rec

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
