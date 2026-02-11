import numpy as np
from typing import List, Dict, Union

class WPrimeDCP:
    """
    Implementation of Skiba's 2015 Dynamic Control of Power (DCP) model for W' Balance.
    Reference: Skiba, P. F., et al. (2015). Modeling the expenditure and reconstitution 
    of work capacity above critical power. Medicine & Science in Sports & Exercise.
    
    Key concept:
    Recovery of W' is not linear or exponential with a fixed time constant (tau).
    Instead, tau varies dynamically based on how far below Critical Power (CP) 
    the athlete is recovering.
    
    Tau Formula:
    tau = 546 * exp(-0.01 * D_CP) + 316
    
    Where D_CP = CP - Power (for Power < CP)
    
    This shows that recovery is slower when closer to CP, and faster when further below CP,
    but with diminishing returns (curvilinear relationship).
    """
    
    @staticmethod
    def calculate_balance(
        power_data: Union[List[float], np.ndarray], 
        cp: float, 
        w_prime: float
    ) -> List[float]:
        """
        Calculates the W' balance for a given power series.
        
        Args:
            power_data: List or array of power values (1-second intervals).
            cp: Critical Power in Watts.
            w_prime: W' capacity in Joules.
            
        Returns:
            List of W' balance values in Joules for each second.
        """
        n = len(power_data)
        w_bal = np.zeros(n)
        current_w_bal = w_prime
        
        for i in range(n):
            p = power_data[i]
            
            if p > cp:
                # DEPLETION
                # When power > CP, W' is depleted linearly by the excess work.
                # W'_exp = (P - CP) * t
                # Since we are iterating second by second, t = 1
                depletion = (p - cp)
                current_w_bal -= depletion
            else:
                # RECOVERY
                # When power < CP, W' is reconstituted.
                # We calculate the dynamic time constant (tau) based on D_CP.
                d_cp = cp - p
                
                # Skiba 2015 formula for Tau
                # tau = 546 * exp(-0.01 * D_CP) + 316
                tau = 546 * np.exp(-0.01 * d_cp) + 316
                
                # Reconstitution formula for discrete time step (1s)
                # W'_bal(t) = W'_bal(t-1) + (W' - W'_bal(t-1)) * (1 - exp(-1/tau))
                reconstitution = (w_prime - current_w_bal) * (1 - np.exp(-1.0 / tau))
                current_w_bal += reconstitution
                
            # Clamp between 0 and W' max
            if current_w_bal > w_prime:
                current_w_bal = w_prime
            elif current_w_bal < 0:
                current_w_bal = 0
                
            w_bal[i] = current_w_bal
            
        return w_bal.tolist()

    @staticmethod
    def calculate_time_to_exhaustion(
        current_w_bal: float, 
        target_power: float, 
        cp: float
    ) -> float:
        """
        Estimates time to exhaustion (TTE) at a target power.
        If target_power <= CP, TTE is infinite (theoretically).
        """
        if target_power <= cp:
            return float('inf')
            
        # W' = (P - CP) * t
        # t = W' / (P - CP)
        return current_w_bal / (target_power - cp)

    @staticmethod
    def calculate_recovery_time(
        current_w_bal: float,
        target_w_bal: float,
        recovery_power: float,
        cp: float,
        w_prime_total: float
    ) -> float:
        """
        Estimates time required to recover to a target W' balance at a specific recovery power.
        """
        if recovery_power >= cp:
            return float('inf') # Cannot recover if power >= CP
            
        if current_w_bal >= target_w_bal:
            return 0.0
            
        d_cp = cp - recovery_power
        tau = 546 * np.exp(-0.01 * d_cp) + 316
        
        # Formula derived from exponential decay:
        # W_target = W_total - (W_total - W_current) * exp(-t/tau)
        # exp(-t/tau) = (W_total - W_target) / (W_total - W_current)
        # -t/tau = ln( (W_total - W_target) / (W_total - W_current) )
        # t = -tau * ln( (W_total - W_target) / (W_total - W_current) )
        
        numerator = w_prime_total - target_w_bal
        denominator = w_prime_total - current_w_bal
        
        if denominator == 0: return 0.0
        if numerator <= 0: return float('inf') # Should not happen if target < total
        
        ratio = numerator / denominator
        if ratio <= 0: return 0.0 # Safety check
        
        t = -tau * np.log(ratio)
        return t
