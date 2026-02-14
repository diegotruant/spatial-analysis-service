from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import numpy as np

# Import models
from experimental_models.w_prime_dcp import WPrimeDCP
from experimental_models.banister_model import BanisterModel
from experimental_models.dfa_alpha1 import DFAAlpha1

router = APIRouter(
    prefix="/experimental",
    tags=["Experimental Models"],
    responses={404: {"description": "Not found"}},
)

# --- Pydantic Models for Validation ---

class WPrimeRequest(BaseModel):
    power_data: List[float] = Field(..., description="Power data in Watts (1s intervals)", min_items=1)
    cp: float = Field(..., gt=0, lt=600, description="Critical Power in Watts")
    w_prime: float = Field(..., gt=0, lt=50000, description="W' Capacity in Joules")

    # Validator to ensure power is within physiological range
    @property
    def validated_power(self):
        # We allow 0 (coasting) but cap at 2500W (world class sprint)
        return [max(0.0, min(x, 2500.0)) for x in self.power_data]

class BanisterRequest(BaseModel):
    daily_tss: List[float] = Field(..., description="Daily TSS values", min_items=1)
    tau_fitness: int = Field(42, ge=1, le=100, description="Fitness decay constant (days)")
    tau_fatigue: int = Field(7, ge=1, le=30, description="Fatigue decay constant (days)")
    k_fitness: float = Field(1.0, gt=0, le=5.0, description="Fitness gain factor")
    k_fatigue: float = Field(2.0, gt=0, le=10.0, description="Fatigue gain factor")
    initial_fitness: float = Field(0.0, ge=0, description="Starting CTL")
    initial_fatigue: float = Field(0.0, ge=0, description="Starting ATL")

    @property
    def validated_tss(self):
         # Cap TSS at 1000/day (physiologically impossible to sustain much more)
        return [max(0.0, min(x, 1000.0)) for x in self.daily_tss]

class DFARequest(BaseModel):
    rr_intervals: List[float] = Field(..., description="RR intervals in ms", min_items=50)
    window_seconds: int = Field(120, ge=30, le=600, description="Rolling window size in seconds")
    
    @property
    def validated_rr(self):
        # Human RR intervals: 300ms (200bpm) to 2000ms (30bpm)
        # Filter out obvious artifacts before passing to model
        return [x for x in self.rr_intervals if 300 <= x <= 2000]

# --- Endpoints ---

@router.post("/w_prime_balance")
async def calculate_w_prime_balance(request: WPrimeRequest):
    """
    Calculates W' Balance using Skiba's 2015 Dynamic Control of Power (DCP) model.
    Output is time-synced 1:1 with input power_data.
    """
    try:
        balance = WPrimeDCP.calculate_balance(
            power_data=request.validated_power,
            cp=request.cp,
            w_prime=request.w_prime
        )
        
        # Verify sync (length match)
        if len(balance) != len(request.power_data):
            raise HTTPException(status_code=500, detail="Output length mismatch. Sync error.")
            
        return {"w_prime_balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/banister")
async def calculate_banister_model(request: BanisterRequest):
    """
    Calculates Fitness (CTL), Fatigue (ATL), and Form (TSB) using Banister's Impulse-Response model.
    """
    try:
        result = BanisterModel.calculate_state(
            daily_tss=request.validated_tss,
            tau_fitness=request.tau_fitness,
            tau_fatigue=request.tau_fatigue,
            k_fitness=request.k_fitness,
            k_fatigue=request.k_fatigue,
            initial_fitness=request.initial_fitness,
            initial_fatigue=request.initial_fatigue
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dfa_alpha1")
async def calculate_dfa_alpha1(request: DFARequest):
    """
    Calculates DFA Alpha-1 for aerobic threshold estimation from RR intervals.
    Returns a time-series of Alpha-1 values.
    """
    try:
        rr_clean = request.validated_rr
        if len(rr_clean) < 50:
            raise HTTPException(status_code=400, detail="Insufficient valid RR intervals (need > 50)")

        alpha1_series = DFAAlpha1.calculate_rolling_alpha1(
            rr_intervals=rr_clean,
            window_size_seconds=request.window_seconds
        )
        return {"alpha1_series": alpha1_series}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
