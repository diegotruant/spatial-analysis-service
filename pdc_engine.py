"""
Power Duration Curve (PDC) Analysis Engine
Analizza la curva di potenza dell'atleta per identificare fenotipo, percentili e punti forza/debolezza
"""

import numpy as np
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel
from enum import Enum


class Phenotype(str, Enum):
    ALL_ROUNDER = "ALL_ROUNDER"
    SPRINTER = "SPRINTER"
    DIESEL = "DIESEL"
    TIME_TRIALIST = "TIME_TRIALIST"
    CLIMBER = "CLIMBER"


class StrengthLevel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class PowerCurvePoint(BaseModel):
    duration: int  # seconds
    watts: float
    date: Optional[str] = None


class PDCAnalysisRequest(BaseModel):
    power_curve: List[PowerCurvePoint]
    weight: float
    cp: Optional[float] = None
    w_prime: Optional[float] = None
    vo2max: Optional[float] = None


class PowerValues(BaseModel):
    sprint5s: float
    sprint10s: float
    anaerobic30s: float
    anaerobic1min: float
    vo2max3min: float
    vo2max5min: float
    threshold10min: float
    threshold20min: float
    threshold40min: float


class Percentiles(BaseModel):
    sprint: int
    anaerobic: int
    vo2max: int
    threshold: int


class Strengths(BaseModel):
    sprint: StrengthLevel
    anaerobic: StrengthLevel
    vo2max: StrengthLevel
    threshold: StrengthLevel


class AdvancedParams(BaseModel):
    ftp_estimated: float
    critical_power: float
    vo2max_estimated: float
    sprint_power: float  # W/kg
    anaerobic_capacity: float  # kJ
    p_max: float
    aerobic_power: float  # APR
    tte_vo2max: float  # minutes


class CurveAnalysis(BaseModel):
    flat_until: float
    collapse_after: float
    description: str


class PDCAnalysisResponse(BaseModel):
    phenotype: Phenotype
    phenotype_label: str
    phenotype_description: str
    power_values: PowerValues
    percentiles: Percentiles
    strengths: Strengths
    advanced_params: AdvancedParams
    coggan_category: str
    curve_analysis: CurveAnalysis


# Database di riferimento per percentili (valori medi per ciclisti amatori)
# Basato su dati pubblici e studi scientifici
PERCENTILE_REFERENCE = {
    'sprint': {
        5: 12.0, 10: 11.0, 25: 9.5, 50: 8.0, 75: 6.5, 90: 5.5, 95: 4.5
    },
    'anaerobic': {
        5: 9.0, 10: 8.0, 25: 7.0, 50: 6.0, 75: 5.0, 90: 4.0, 95: 3.5
    },
    'vo2max': {
        5: 6.5, 10: 6.0, 25: 5.5, 50: 4.8, 75: 4.2, 90: 3.5, 95: 3.0
    },
    'threshold': {
        5: 4.5, 10: 4.0, 25: 3.5, 50: 3.0, 75: 2.5, 90: 2.0, 95: 1.8
    }
}


class PDCEngine:
    @staticmethod
    def analyze(request: PDCAnalysisRequest) -> PDCAnalysisResponse:
        """
        Analizza la Power Duration Curve completa
        """
        if not request.power_curve or len(request.power_curve) == 0:
            raise ValueError("Power curve is empty")
        
        if request.weight <= 0:
            raise ValueError("Weight must be positive")
        
        # Estrai valori per durate chiave
        power_values = PDCEngine._extract_power_values(request.power_curve)
        
        # Calcola percentili
        percentiles = PDCEngine._calculate_percentiles(power_values, request.weight)
        
        # Identifica fenotipo
        phenotype = PDCEngine._identify_phenotype(
            power_values.sprint5s,
            power_values.anaerobic1min,
            power_values.vo2max5min,
            power_values.threshold20min,
            request.weight
        )
        
        # Determina punti forza/debolezza
        strengths = PDCEngine._determine_strengths(percentiles)
        
        # Analizza forma curva
        curve_analysis = PDCEngine._analyze_curve_shape(request.power_curve)
        
        # Calcola parametri avanzati
        advanced_params = PDCEngine._calculate_advanced_params(
            power_values,
            request.weight,
            request.cp,
            request.w_prime,
            request.vo2max
        )
        
        # Determina categoria Coggan
        coggan_category = PDCEngine._determine_coggan_category(
            power_values.threshold20min,
            request.weight
        )
        
        # Etichette fenotipo
        phenotype_info = PDCEngine._get_phenotype_info(phenotype)
        
        return PDCAnalysisResponse(
            phenotype=phenotype,
            phenotype_label=phenotype_info['label'],
            phenotype_description=phenotype_info['description'],
            power_values=power_values,
            percentiles=percentiles,
            strengths=strengths,
            advanced_params=advanced_params,
            coggan_category=coggan_category,
            curve_analysis=curve_analysis
        )
    
    @staticmethod
    def _extract_power_values(power_curve: List[PowerCurvePoint]) -> PowerValues:
        """Estrae valori di potenza per durate chiave con interpolazione logaritmica"""
        
        def get_power_at(duration: int) -> float:
            # Cerca valore esatto
            exact = next((p.watts for p in power_curve if p.duration == duration), None)
            if exact is not None:
                return exact
            
            # Ordina per durata
            sorted_curve = sorted(power_curve, key=lambda x: x.duration)
            
            # Trova punti precedente e successivo
            prev = None
            next_p = None
            
            for i, p in enumerate(sorted_curve):
                if p.duration < duration:
                    prev = p
                elif p.duration > duration:
                    next_p = p
                    break
            
            # Interpolazione logaritmica
            if prev and next_p:
                log_d = np.log(duration)
                log_prev = np.log(prev.duration)
                log_next = np.log(next_p.duration)
                ratio = (log_d - log_prev) / (log_next - log_prev)
                return prev.watts + (next_p.watts - prev.watts) * ratio
            
            if prev:
                return prev.watts
            
            if next_p:
                return next_p.watts
            
            return 0.0
        
        return PowerValues(
            sprint5s=get_power_at(5),
            sprint10s=get_power_at(10),
            anaerobic30s=get_power_at(30),
            anaerobic1min=get_power_at(60),
            vo2max3min=get_power_at(180),
            vo2max5min=get_power_at(300),
            threshold10min=get_power_at(600),
            threshold20min=get_power_at(1200),
            threshold40min=get_power_at(2400)
        )
    
    @staticmethod
    def _calculate_percentiles(power_values: PowerValues, weight: float) -> Percentiles:
        """Calcola percentili per ogni categoria"""
        
        def calc_percentile(watts_per_kg: float, category: str) -> int:
            ref = PERCENTILE_REFERENCE[category]
            
            if watts_per_kg >= ref[5]:
                return 5
            if watts_per_kg >= ref[10]:
                return 10
            if watts_per_kg >= ref[25]:
                return 25
            if watts_per_kg >= ref[50]:
                return 50
            if watts_per_kg >= ref[75]:
                return 75
            if watts_per_kg >= ref[90]:
                return 90
            if watts_per_kg >= ref[95]:
                return 95
            return 99
        
        sprint_wkg = (power_values.sprint5s + power_values.sprint10s) / 2 / weight
        anaerobic_wkg = (power_values.anaerobic30s + power_values.anaerobic1min) / 2 / weight
        vo2max_wkg = (power_values.vo2max3min + power_values.vo2max5min) / 2 / weight
        threshold_wkg = (power_values.threshold10min + power_values.threshold20min) / 2 / weight
        
        return Percentiles(
            sprint=calc_percentile(sprint_wkg, 'sprint'),
            anaerobic=calc_percentile(anaerobic_wkg, 'anaerobic'),
            vo2max=calc_percentile(vo2max_wkg, 'vo2max'),
            threshold=calc_percentile(threshold_wkg, 'threshold')
        )
    
    @staticmethod
    def _identify_phenotype(
        sprint5s: float,
        anaerobic1min: float,
        vo2max5min: float,
        threshold20min: float,
        weight: float
    ) -> Phenotype:
        """Identifica il fenotipo basandosi sulla distribuzione della potenza"""
        
        sprint_wkg = sprint5s / weight
        anaerobic_wkg = anaerobic1min / weight
        vo2max_wkg = vo2max5min / weight
        threshold_wkg = threshold20min / weight
        
        # Calcola deviazioni dalla mediana
        sprint_dev = sprint_wkg / PERCENTILE_REFERENCE['sprint'][50]
        anaerobic_dev = anaerobic_wkg / PERCENTILE_REFERENCE['anaerobic'][50]
        vo2max_dev = vo2max_wkg / PERCENTILE_REFERENCE['vo2max'][50]
        threshold_dev = threshold_wkg / PERCENTILE_REFERENCE['threshold'][50]
        
        # Logica di identificazione
        if sprint_dev > 1.3 and anaerobic_dev > 1.2 and vo2max_dev < 0.9 and threshold_dev < 0.9:
            return Phenotype.SPRINTER
        
        if sprint_dev < 0.7 and anaerobic_dev < 0.8 and vo2max_dev > 1.1 and threshold_dev > 1.2:
            return Phenotype.DIESEL
        
        if threshold_dev > 1.3 and vo2max_dev > 1.1 and sprint_dev < 0.8:
            return Phenotype.TIME_TRIALIST
        
        if vo2max_dev > 1.2 and threshold_dev > 1.1 and anaerobic_dev > 1.0:
            return Phenotype.CLIMBER
        
        return Phenotype.ALL_ROUNDER
    
    @staticmethod
    def _determine_strengths(percentiles: Percentiles) -> Strengths:
        """Determina punti forza/debolezza basati sui percentili"""
        
        def get_strength(percentile: int) -> StrengthLevel:
            if percentile <= 25:
                return StrengthLevel.STRONG
            if percentile <= 75:
                return StrengthLevel.MODERATE
            return StrengthLevel.WEAK
        
        return Strengths(
            sprint=get_strength(percentiles.sprint),
            anaerobic=get_strength(percentiles.anaerobic),
            vo2max=get_strength(percentiles.vo2max),
            threshold=get_strength(percentiles.threshold)
        )
    
    @staticmethod
    def _analyze_curve_shape(power_curve: List[PowerCurvePoint]) -> CurveAnalysis:
        """Analizza la forma della curva per identificare pattern"""
        
        if len(power_curve) < 3:
            return CurveAnalysis(
                flat_until=0,
                collapse_after=0,
                description="Dati insufficienti"
            )
        
        sorted_curve = sorted(power_curve, key=lambda x: x.duration)
        
        flat_until = sorted_curve[0].duration
        collapse_after = sorted_curve[-1].duration
        
        # Calcola il tasso di declino
        for i in range(1, len(sorted_curve)):
            prev = sorted_curve[i - 1]
            curr = sorted_curve[i]
            
            if prev.watts > 0:
                decline = (prev.watts - curr.watts) / prev.watts
                
                # Se il declino è > 10%, la curva sta crollando
                if decline > 0.10 and collapse_after == sorted_curve[-1].duration:
                    collapse_after = curr.duration
                
                # Se il declino è < 2%, la curva è ancora piatta
                if decline < 0.02:
                    flat_until = curr.duration
        
        # Genera descrizione
        flat_min = flat_until / 60
        collapse_min = collapse_after / 60
        
        if flat_until >= 180:
            description = f"La curva resta piatta fino a {flat_min:.1f} minuti, indicando buone prestazioni su sforzi brevi."
        else:
            description = f"La curva inizia a scendere dopo {flat_until:.0f} secondi."
        
        if collapse_after <= 300:
            description += f" Dopo {collapse_min:.1f} minuti la potenza crolla significativamente."
        else:
            description += f" La potenza rimane stabile fino a {collapse_min:.1f} minuti."
        
        return CurveAnalysis(
            flat_until=flat_until,
            collapse_after=collapse_after,
            description=description
        )
    
    @staticmethod
    def _calculate_advanced_params(
        power_values: PowerValues,
        weight: float,
        cp: Optional[float],
        w_prime: Optional[float],
        vo2max: Optional[float]
    ) -> AdvancedParams:
        """Calcola parametri avanzati"""
        
        ftp_estimated = power_values.threshold20min or cp or 0
        critical_power = cp or power_values.threshold20min or 0
        vo2max_estimated = vo2max or (power_values.vo2max5min / weight * 12)  # Stima semplificata
        sprint_power = power_values.sprint5s / weight
        anaerobic_capacity = (w_prime / 1000) if w_prime else 15.8  # kJ
        p_max = max(power_values.sprint5s, power_values.sprint10s) if power_values.sprint10s > 0 else power_values.sprint5s
        aerobic_power = p_max - critical_power  # APR
        tte_vo2max = PDCEngine._calculate_tte_vo2max(vo2max_estimated, power_values.vo2max5min, weight)
        
        return AdvancedParams(
            ftp_estimated=ftp_estimated,
            critical_power=critical_power,
            vo2max_estimated=vo2max_estimated,
            sprint_power=sprint_power,
            anaerobic_capacity=anaerobic_capacity,
            p_max=p_max,
            aerobic_power=aerobic_power,
            tte_vo2max=tte_vo2max
        )
    
    @staticmethod
    def _calculate_tte_vo2max(vo2max: float, vo2max_power: float, weight: float) -> float:
        """Calcola TTE @ VO2max (Time to Exhaustion)"""
        vo2max_wkg = vo2max_power / weight
        estimated_tte = 4 + (vo2max_wkg - 4.0) * 0.5  # Stima empirica
        return max(2, min(8, estimated_tte))  # Clamp tra 2 e 8 minuti
    
    @staticmethod
    def _determine_coggan_category(threshold20min: float, weight: float) -> str:
        """Determina categoria Coggan basata su W/kg"""
        avg_wkg = threshold20min / weight
        
        if avg_wkg >= 4.0:
            return "Elite"
        elif avg_wkg >= 3.5:
            return "Very Good"
        elif avg_wkg >= 3.0:
            return "Good"
        elif avg_wkg >= 2.5:
            return "Moderate"
        else:
            return "Fair"
    
    @staticmethod
    def _get_phenotype_info(phenotype: Phenotype) -> Dict[str, str]:
        """Restituisce informazioni sul fenotipo"""
        info = {
            Phenotype.ALL_ROUNDER: {
                'label': 'All-Rounder',
                'description': 'Profilo equilibrato tra potenza e resistenza. Né sprinter puro né diesel puro. Un po\' di tutto, ma niente di eccellente.'
            },
            Phenotype.SPRINTER: {
                'label': 'Sprinter',
                'description': 'Eccellente potenza esplosiva e capacità anaerobica. Forte negli sprint e negli attacchi brevi, ma limitato nelle durate lunghe.'
            },
            Phenotype.DIESEL: {
                'label': 'Diesel',
                'description': 'Motore aerobico molto efficiente. Eccellente resistenza e capacità di mantenere potenze elevate per lunghi periodi.'
            },
            Phenotype.TIME_TRIALIST: {
                'label': 'Time Trialist',
                'description': 'Specialista nelle prove a cronometro. Eccellente capacità di sostenere potenze elevate per 20-60 minuti.'
            },
            Phenotype.CLIMBER: {
                'label': 'Climber',
                'description': 'Eccellente rapporto potenza/peso. Forte nelle salite e negli sforzi prolungati ad alta intensità.'
            }
        }
        return info[phenotype]

