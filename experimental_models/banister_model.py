import numpy as np
from typing import List, Dict, Tuple, Optional

class BanisterModel:
    """
    Implementation of the Banister Impulse-Response Model (Fitness-Fatigue).
    
    Formula:
    Performance(t) = Fitness(t) - Fatigue(t) + Performance_0
    
    Fitness(t) = Fitness(t-1) * exp(-1/tau_1) + w(t)
    Fatigue(t) = Fatigue(t-1) * exp(-1/tau_2) + w(t) * k_2
    
    Where:
    - tau_1: Time constant for fitness decay (typically 42 days, range 30-50)
    - tau_2: Time constant for fatigue decay (typically 7 days, range 5-15)
    - k_1: Multiplier for fitness gain (often normalized to 1)
    - k_2: Multiplier for fatigue impact (typically 2-3x fitness)
    """
    
    @staticmethod
    def calculate_state(
        daily_tss: List[float],
        tau_fitness: int = 42,
        tau_fatigue: int = 7,
        k_fitness: float = 1.0,
        k_fatigue: float = 2.0,
        initial_fitness: float = 0.0,
        initial_fatigue: float = 0.0
    ) -> Dict[str, List[float]]:
        """
        Calculates daily Fitness (CTL), Fatigue (ATL), and Form (TSB/Performance) 
        using the exponential weighted moving average (EWMA) which is mathematically 
        equivalent to the discrete version of Banister's model.

        Args:
            daily_tss: List of daily training loads (TSS).
            tau_fitness: Time constant for fitness (days).
            tau_fatigue: Time constant for fatigue (days).
            k_fitness: Gain factor for fitness (standard PMC uses 1).
            k_fatigue: Gain factor for fatigue (standard PMC uses 1, Banister uses >1).
            initial_fitness: Starting fitness value.
            initial_fatigue: Starting fatigue value.

        Returns:
            Dictionary containing lists for 'fitness', 'fatigue', 'performance'.
        """
        n = len(daily_tss)
        fitness = np.zeros(n)
        fatigue = np.zeros(n)
        performance = np.zeros(n)
        
        # Decay factors
        # Note: In standard PMC (TrainingPeaks), the smoothing factor is 1/tau.
        # e.g. CTL_today = CTL_yesterday + (TSS - CTL_yesterday) * (1/tau)
        # This is an EWMA. Banister's original formulation uses exp(-1/tau).
        # For valid comparison with modern tools, we often use the EWMA approximation:
        # factor = 1 - exp(-1/tau)
        
        df_fitness = np.exp(-1.0 / tau_fitness)
        df_fatigue = np.exp(-1.0 / tau_fatigue)
        
        curr_fitness = initial_fitness
        curr_fatigue = initial_fatigue
        
        for i in range(n):
            load = daily_tss[i]
            
            # Banister Recursive Implementation
            curr_fitness = (curr_fitness * df_fitness) + (load * k_fitness * (1 - df_fitness))
            curr_fatigue = (curr_fatigue * df_fatigue) + (load * k_fatigue * (1 - df_fatigue))
            
            fitness[i] = curr_fitness
            fatigue[i] = curr_fatigue
            performance[i] = curr_fitness - curr_fatigue
            
        return {
            "fitness": fitness.tolist(),
            "fatigue": fatigue.tolist(),
            "performance": performance.tolist()
        }

    @staticmethod
    def optimize_parameters(daily_tss: List[float], performance_metric: List[float]) -> Dict[str, float]:
        """
        Placeholder for parameter optimization. 
        In a full implementation, this function would use scipy.optimize to find 
        the best tau1, tau2, k1, k2 that minimize the error between predicted 
        performance and actual measured performance (e.g. CP, FTP tests).
        """
        pass
