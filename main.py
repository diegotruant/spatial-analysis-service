from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import polars as pl
from analysis_prototype import analyze_activity
from metabolic_engine import MetabolicEngine, MetabolicProfile
from hrv_engine import HRVEngine

app = FastAPI(title="Spatial Cosmic Analysis API")

# --- Models ---
class AnalysisRequest(BaseModel):
    power_data: List[float]
    hr_data: Optional[List[float]] = None
    ftp: float

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
            
        df = pl.DataFrame(data)
        results = analyze_activity(df, request.ftp)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
