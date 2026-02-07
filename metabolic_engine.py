import math
from typing import Optional, Literal, Union, Any
from pydantic import BaseModel

# Try to import scipy for 3-point CP model, fallback to 2-point if unavailable
try:
    from scipy.optimize import curve_fit
    import numpy as np
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def calculate_cp_wprime(
    mmp_data: dict[int, float],
    use_3point: bool = False
) -> tuple[float, float, dict]:
    """
    Calculates Critical Power (CP) and W' using 2-point or 3-point model.
    
    Args:
        mmp_data: Dictionary of {duration_seconds: power_watts}
                  e.g., {180: 350, 360: 320, 900: 280, 420: 310, 720: 295}
        use_3point: If True and scipy available, use 3-point non-linear regression
    
    Returns:
        (cp, w_prime, metadata)
        - cp: Critical Power in watts
        - w_prime: Anaerobic work capacity in joules
        - metadata: Dict with model info, confidence, etc.
    
    Models:
        2-point: Linear model using 2 durations (typically 6' and 15')
                 CP = (W₂ - W₁) / (t₂ - t₁)
                 W' = W₁ - CP × t₁
        
        3-point: Non-linear hyperbolic model P = CP + W'/t
                 Uses scipy.optimize.curve_fit for best fit
    """
    if len(mmp_data) < 2:
        raise ValueError("Need at least 2 MMP values to calculate CP")
    
    # Sort by duration
    sorted_durations = sorted(mmp_data.keys())
    
    # 2-Point Model (Linear - Default and Fallback)
    if not use_3point or not SCIPY_AVAILABLE or len(mmp_data) < 3:
        # Use longest two durations for 2-point model
        # Typically 6min (360s) and 15min (900s)
        if len(sorted_durations) >= 2:
            t1 = sorted_durations[-2]  # Second longest
            t2 = sorted_durations[-1]  # Longest
        else:
            t1, t2 = sorted_durations[0], sorted_durations[1]
        
        p1 = mmp_data[t1]
        p2 = mmp_data[t2]
        
        work1 = p1 * t1
        work2 = p2 * t2
        
        cp = (work2 - work1) / (t2 - t1)
        w_prime = work1 - cp * t1
        
        # Handle negative W' (can happen with poor data)
        if w_prime < 0:
            w_prime = 0
            cp = p2  # Use longest duration power as CP estimate
        
        metadata = {
            "model": "2-point-linear",
            "durations_used": [t1, t2],
            "powers_used": [p1, p2],
            "confidence": "medium",
            "note": "Standard 2-point linear model (Monod-Scherrer)"
        }
        
        return cp, w_prime, metadata
    
    # 3-Point Model (Non-linear Hyperbolic Regression)
    # Model: P(t) = CP + W'/t
    durations = np.array(sorted_durations, dtype=float)
    powers = np.array([mmp_data[d] for d in sorted_durations], dtype=float)
    
    # Define hyperbolic model
    def hyperbolic_model(t, cp, w_prime):
        return cp + w_prime / t
    
    # Initial guess: use 2-point model as starting point
    t1, t2 = sorted_durations[-2], sorted_durations[-1]
    p1, p2 = mmp_data[t1], mmp_data[t2]
    work1, work2 = p1 * t1, p2 * t2
    cp_guess = (work2 - work1) / (t2 - t1)
    w_prime_guess = work1 - cp_guess * t1
    
    # Ensure positive initial guesses
    cp_guess = max(cp_guess, powers.min() * 0.5)
    w_prime_guess = max(w_prime_guess, 10000)
    
    try:
        # Curve fitting with bounds
        # CP should be between 50% of min power and 95% of longest duration power
        # W' should be between 5kJ and 50kJ
        bounds = (
            [powers.min() * 0.5, 5000],      # Lower bounds [CP_min, W'_min]
            [powers[-1] * 0.95, 50000]       # Upper bounds [CP_max, W'_max]
        )
        
        params, covariance = curve_fit(
            hyperbolic_model,
            durations,
            powers,
            p0=[cp_guess, w_prime_guess],
            bounds=bounds,
            maxfev=5000
        )
        
        cp_fitted, w_prime_fitted = params
        
        # Calculate R² for goodness of fit
        predictions = hyperbolic_model(durations, cp_fitted, w_prime_fitted)
        residuals = powers - predictions
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((powers - np.mean(powers)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine confidence based on R²
        if r_squared > 0.95:
            confidence = "high"
        elif r_squared > 0.85:
            confidence = "medium"
        else:
            confidence = "low"
        
        metadata = {
            "model": "3-point-hyperbolic",
            "durations_used": sorted_durations,
            "powers_used": [mmp_data[d] for d in sorted_durations],
            "r_squared": round(r_squared, 4),
            "confidence": confidence,
            "note": f"Non-linear regression fit (R²={r_squared:.3f})"
        }
        
        return float(cp_fitted), float(w_prime_fitted), metadata
        
    except Exception as e:
        # Fallback to 2-point if curve fitting fails
        print(f"3-point model failed ({e}), falling back to 2-point")
        return calculate_cp_wprime(mmp_data, use_3point=False)

class CombustionData(BaseModel):
    watt: int
    fat_oxidation: float
    carb_oxidation: float

class PDCPoint(BaseModel):
    duration_seconds: int
    watt: float

class MetabolicZone(BaseModel):
    name: str
    min_watt: int
    max_watt: int
    description: str
    color: str

class MetabolicProfile(BaseModel):
    vlamax: float
    map: float
    vo2max: float
    mlss: int
    w_prime: int
    fat_max: int
    confidence_score: float
    bmr: int
    tdee: int
    carb_rate_at_ftp: float
    zones: list[MetabolicZone]
    combustion_curve: list[CombustionData]
    pdc_curve: list[PDCPoint] = []

class MetabolicEngine:
    @staticmethod
    def calculate_profile(
        weight: float,
        height: float = 175,
        age: int = 30,
        gender: str = 'MALE',
        body_fat_percentage: float = 15,
        somatotype: Literal['ECTOMORPH', 'MESOMORPH', 'ENDOMORPH'] = 'MESOMORPH',
        p_max: float = 800,
        mmp3: float = 350,
        mmp6: float = 300,
        mmp15: float = 250,
        use_3point_cp: bool = False,  # ← NUOVO parametro opzionale
        mmp_additional: Optional[dict[int, float]] = None  # ← Per dati extra (es. 7min, 12min)
    ) -> MetabolicProfile:
        # 1. BASE METABOLISM (BMR, TDEE)
        bmr = MetabolicEngine._calculate_bmr(weight, height, age, gender)
        tdee = bmr * 1.55

        # 2. PERFORMANCE MODEL (Masse e Potenze)
        ffm = weight * (1 - body_fat_percentage / 100)
        active_muscle_mass = ffm * 0.31

        # Critical Power (CP) Model
        # Build MMP data dictionary
        mmp_data = {
            180: mmp3,
            360: mmp6,
            900: mmp15
        }
        
        # Add additional MMP values if provided
        if mmp_additional:
            mmp_data.update(mmp_additional)
        
        # Calculate CP and W' using appropriate model
        cp, w_prime_work, cp_metadata = calculate_cp_wprime(mmp_data, use_3point_cp)

        # Thresholds
        cp_to_mlss_ratio = 0.88
        if somatotype == 'ECTOMORPH': cp_to_mlss_ratio = 0.92
        elif somatotype == 'ENDOMORPH': cp_to_mlss_ratio = 0.85
        
        mlss = cp * cp_to_mlss_ratio

        # 3. PERFORMANCE MODEL ESTIMATORS
        vla_max = MetabolicEngine._estimate_vla_max(p_max, active_muscle_mass, mlss, mmp3)
        vo2_max = MetabolicEngine._estimate_vo2_max(mmp3, w_prime_work, weight)
        fat_max = MetabolicEngine._estimate_fat_max(mlss, vla_max)

        # 4. SUBSTRATE CURVE GENERATOR
        clamp_vla_max = min(max(vla_max, 0.2), 1.2)
        map_aerobic = mmp3 - w_prime_work / 180.0
        zones = MetabolicEngine._calculate_zones(mlss, fat_max, map_aerobic)
        combustion_curve = MetabolicEngine._calculate_combustion_curve(map_aerobic, fat_max, clamp_vla_max)

        # 5. CONFIDENCE & VALIDATION
        confidence = MetabolicEngine._calculate_confidence(p_max, mmp3, mmp6, mmp15)

        return MetabolicProfile(
            vlamax=round(clamp_vla_max, 2),
            map=round(map_aerobic, 1),
            vo2max=round(vo2_max, 1),
            mlss=int(round(mlss)),
            w_prime=int(round(w_prime_work)),
            fat_max=int(round(fat_max)),
            confidence_score=round(confidence, 2),
            bmr=int(round(bmr)),
            tdee=int(round(tdee)),
            carb_rate_at_ftp=round(50 + clamp_vla_max * 45, 1),
            zones=zones,
            combustion_curve=combustion_curve,
            pdc_curve=MetabolicEngine._generate_pdc_curve(cp, w_prime_work, p_max)
        )

    @staticmethod
    def _calculate_bmr(w: float, h: float, age: int, gender: str) -> float:
        if gender.upper() == 'FEMALE':
            return 447.593 + (9.247 * w) + (3.098 * h) - (4.330 * age)
        return 88.362 + (13.397 * w) + (4.799 * h) - (5.677 * age)

    @staticmethod
    def _estimate_vla_max(p_max: float, muscle_mass: float, mlss: float, mmp3: float) -> float:
        vla_max = (p_max / muscle_mass) * 0.013
        aerobic_fraction = mlss / (mmp3 * 0.94)
        vla_max += 0.4 * (1.1 - aerobic_fraction)
        return vla_max

    @staticmethod
    def _estimate_vo2_max(mmp3: float, w_prime: float, weight: float) -> float:
        map_aerobic = mmp3 - w_prime / 180.0
        efficiency = 0.225
        return ((map_aerobic / efficiency) / 21.1) * 60 / weight

    @staticmethod
    def _estimate_fat_max(mlss: float, vla_max: float) -> float:
        return mlss * (0.8 - vla_max * 0.25)

    @staticmethod
    def _calculate_confidence(p_max: float, m3: float, m6: float, m15: float) -> float:
        score = 0.4
        if p_max > 0: score += 0.15
        if m3 > 0: score += 0.15
        if m15 > 0: score += 0.15
        if m3 > m6 > m15: score += 0.15
        return min(max(score, 0.1), 1.0)

    @staticmethod
    def _calculate_zones(ftp: float, fat_max_watt: float, map_val: float) -> list[MetabolicZone]:
        z1_limit = int(round(ftp * 0.55))
        z2_limit = int(round(fat_max_watt + 15))
        safe_z2 = max(z2_limit, z1_limit + 10)
        z3_limit = int(round(ftp * 0.88))
        z4_limit = int(round(ftp * 1.05))
        z5_limit = int(round(map_val))

        return [
            MetabolicZone(name='Z1 - Recovery', min_watt=0, max_watt=z1_limit, description='Recupero attivo', color='text-slate-400'),
            MetabolicZone(name='Z2 - Endurance', min_watt=z1_limit + 1, max_watt=safe_z2, description='Endurance base', color='text-emerald-500'),
            MetabolicZone(name='Z3 - Tempo', min_watt=safe_z2 + 1, max_watt=z3_limit, description='Lavoro tempo', color='text-blue-500'),
            MetabolicZone(name='Z4 - Threshold', min_watt=z3_limit + 1, max_watt=z4_limit, description='Soglia anaerobica', color='text-orange-500'),
            MetabolicZone(name='Z5 - VO2max', min_watt=z4_limit + 1, max_watt=z5_limit, description='Potenza aerobica massima', color='text-red-500')
        ]

    @staticmethod
    def _calculate_combustion_curve(map_val: float, fat_max_watt: float, vlamax: float) -> list[CombustionData]:
        data = []
        end_watt = int(map_val * 1.3)
        for w in range(50, end_watt + 1, 10):
            r = w / map_val
            fat_ox = 100 * math.exp(-((w - fat_max_watt) / (map_val * 0.4))**2) - (r * 12)
            fat_ox = max(0.0, fat_ox)
            carb_ox = 100 / (1 + math.exp(-12 * (r - (0.98 - vlamax * 0.4))))
            carb_ox = min(100.0, carb_ox)
            data.append(CombustionData(watt=w, fat_oxidation=round(fat_ox, 1), carb_oxidation=round(carb_ox, 1)))
        return data

    @staticmethod
    def _generate_pdc_curve(cp: float, w_prime: float, p_max: float) -> list[PDCPoint]:
        """Genera punti per la curva PD modellata (P = CP + W'/t)"""
        durations = [1, 5, 10, 30, 60, 120, 300, 600, 1200, 1800, 3600]
        curve = []
        for t in durations:
            # Modello Monod-Scherrer con limitatore a Pmax
            p = cp + (w_prime / t)
            p = min(p, p_max)
            curve.append(PDCPoint(duration_seconds=t, watt=round(p, 1)))
        return curve
