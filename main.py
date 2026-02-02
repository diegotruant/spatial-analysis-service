from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Union
import polars as pl
from analysis_prototype import analyze_activity, calculate_pmc_trends
from metabolic_engine import MetabolicEngine, MetabolicProfile
from hrv_engine import HRVEngine
from pdc_engine import PDCEngine, PDCAnalysisRequest, PowerCurvePoint

app = FastAPI(title="Spatial Cosmic Analysis API")

# --- Models ---
class AnalysisRequest(BaseModel):
    power_data: List[float]
    hr_data: Optional[List[float]] = None
    cadence_data: Optional[List[float]] = None
    ftp: float
    w_prime: float = 20000

class PMCRequest(BaseModel):
    tss_history: List[Dict[str, Union[float, str]]] # List of {"date": "YYYY-MM-DD", "tss": 100}

class MetabolicRequest(BaseModel):
    weight: float
    height: float = 175
    age: int = 30
    gender: str = 'MALE'
    body_fat: float
    somatotype: str = 'MESOMORPH'
    p_max: float
    mmp3: float
    mmp6: float
    mmp15: float

class HRVRequest(BaseModel):
    hrv_current: float
    hrv_history: List[float] # Last 7-30 days
    full_history: Optional[List[Dict]] = None # For overreaching

class PDCAnalysisRequestModel(BaseModel):
    power_curve: List[Dict[str, Union[int, float, str]]]  # [{"duration": 5, "watts": 800, "date": "2024-01-01"}]
    weight: float
    cp: Optional[float] = None
    w_prime: Optional[float] = None
    vo2max: Optional[float] = None

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "spatial-cosmic-analysis"}

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    try:
        data = {"power": request.power_data}
        if request.hr_data:
            data["heart_rate"] = request.hr_data
        if request.cadence_data:
            data["cadence"] = request.cadence_data
            
        df = pl.DataFrame(data)
        results = analyze_activity(df, request.ftp, request.w_prime)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pmc")
async def calculate_pmc(request: PMCRequest):
    try:
        results = calculate_pmc_trends(request.tss_history)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/metabolic/profile")
async def calculate_metabolic_profile(request: MetabolicRequest):
    try:
        profile = MetabolicEngine.calculate_profile(
            weight=request.weight,
            height=request.height,
            age=request.age,
            gender=request.gender,
            body_fat_percentage=request.body_fat,
            somatotype=request.somatotype, # type: ignore
            p_max=request.p_max,
            mmp3=request.mmp3,
            mmp6=request.mmp6,
            mmp15=request.mmp15
        )
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hrv/analyze")
async def analyze_hrv(request: HRVRequest):
    try:
        baseline = HRVEngine.calculate_baseline(request.hrv_history)
        traffic = HRVEngine.calculate_traffic_light(request.hrv_current, baseline["mean"])
        
        overreaching = None
        if request.full_history:
            overreaching = HRVEngine.analyze_overreaching(request.full_history, baseline["mean"])
            
        return {
            "baseline": baseline,
            "today": traffic,
            "overreaching": overreaching,
            "recommendation": HRVEngine.get_recommendation(
                traffic["status"], 
                traffic["deviation"],
                overreaching["days_depressed"] if overreaching else 0
            )
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pdc/analyze")
async def analyze_pdc(request: PDCAnalysisRequestModel):
    try:
        # Converti i dati in PowerCurvePoint
        power_curve_points = [
            PowerCurvePoint(
                duration=int(p["duration"]),
                watts=float(p["watts"]),
                date=p.get("date")
            )
            for p in request.power_curve
        ]
        
        # Crea la richiesta per PDCEngine
        pdc_request = PDCAnalysisRequest(
            power_curve=power_curve_points,
            weight=request.weight,
            cp=request.cp,
            w_prime=request.w_prime,
            vo2max=request.vo2max
        )
        
        # Esegui l'analisi
        analysis = PDCEngine.analyze(pdc_request)
        
        # Converti la risposta in dict per JSON
        return analysis.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
