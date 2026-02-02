import math
from typing import List, Dict, Optional, Literal, Union
from pydantic import BaseModel

class CombustionData(BaseModel):
    watt: int
    fat_oxidation: float
    carb_oxidation: float

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
    cp: float  # Critical Power - aggiunto per sincronizzazione con PDC
    w_prime: int
    fat_max: int
    confidence_score: float
    bmr: int
    tdee: int
    carb_rate_at_ftp: float
    zones: List[MetabolicZone]
    combustion_curve: List[CombustionData]

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
        mmp15: float = 250
    ) -> MetabolicProfile:
        # 1. BASE METABOLISM (BMR, TDEE)
        bmr = MetabolicEngine._calculate_bmr(weight, height, age, gender)
        tdee = bmr * 1.55

        # 2. PERFORMANCE MODEL (Masse e Potenze)
        ffm = weight * (1 - body_fat_percentage / 100)
        active_muscle_mass = ffm * 0.31

        # Critical Power (CP) Model
        t6 = 360.0
        t15 = 900.0
        work6 = mmp6 * t6
        work15 = mmp15 * t15
        cp = (work15 - work6) / (t15 - t6)
        w_prime_work = work6 - cp * t6

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
            cp=round(cp, 1),  # Aggiunto CP per sincronizzazione
            w_prime=int(round(w_prime_work)),
            fat_max=int(round(fat_max)),
            confidence_score=round(confidence, 2),
            bmr=int(round(bmr)),
            tdee=int(round(tdee)),
            carb_rate_at_ftp=round(50 + clamp_vla_max * 45, 1),
            zones=zones,
            combustion_curve=combustion_curve
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
    def _calculate_zones(ftp: float, fat_max_watt: float, map_val: float) -> List[MetabolicZone]:
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
    def _calculate_combustion_curve(map_val: float, fat_max_watt: float, vlamax: float) -> List[CombustionData]:
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
