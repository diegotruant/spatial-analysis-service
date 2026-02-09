from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Union, Any
import polars as pl
from analysis_prototype import analyze_activity, calculate_pmc_trends
from metabolic_engine import MetabolicEngine, MetabolicProfile
from hrv_engine import HRVEngine
from pdc_engine import PDCEngine, PDCAnalysisRequest, PowerCurvePoint

app = FastAPI(title="Velo Lab Analysis API")

# Include Routers
from routers import fit
app.include_router(fit.router)

# --- Models ---
class AnalysisRequest(BaseModel):
    power_data: list[float]
    hr_data: Optional[list[float]] = None
    cadence_data: Optional[list[float]] = None
    ftp: float
    w_prime: float = 20000
    altitude_data: Optional[list[float]] = None  # Altitude in meters for each second
    temperature: Optional[float] = None  # Average temperature in Celsius

class PMCRequest(BaseModel):
    tss_history: list[dict[str, Union[float, str]]] # List of {"date": "YYYY-MM-DD", "tss": 100}

class MetabolicRequest(BaseModel):
    weight: float
    height: float = 175
    age: int = 30
    gender: str = 'MALE'
    body_fat: float = 15 # Changed from body_fat: float
    somatotype: str = 'MESOMORPH'
    p_max: float
    mmp3: float
    mmp6: float
    mmp15: float
    use_3point_cp: bool = False  # Enable 3-point CP model
    mmp_additional: Optional[dict[int, float]] = None  # Extra MMP values {duration_sec: watts}

class DFARequest(BaseModel):
    rr_data: list[dict]  # List of {timestamp, elapsed, rr}
    power_data: Optional[list[float]] = None
    window_seconds: int = 120  # Extra MMP values {duration_sec: watts}

class HRVRequest(BaseModel):
    hrv_current: float
    hrv_history: list[float] # Last 7-30 days
    full_history: Optional[list[dict]] = None # For overreaching

class PDCAnalysisRequestModel(BaseModel):
    power_curve: list[dict[str, Union[int, float, str]]]  # [{"duration": 5, "watts": 800, "date": "2024-01-01"}]
    weight: float
    cp: Optional[float] = None
    w_prime: Optional[float] = None
    vo2max: Optional[float] = None

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "velo-lab-analysis"}

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    try:
        data = {"power": request.power_data}
        if request.hr_data:
            data["heart_rate"] = request.hr_data
        if request.cadence_data:
            data["cadence"] = request.cadence_data
            
        df = pl.DataFrame(data)
        results = analyze_activity(
            df, 
            request.ftp, 
            request.w_prime,
            request.altitude_data,
            request.temperature
        )
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

@app.post("/pdc/analyze")
async def analyze_pdc(request: PDCAnalysisRequest):
    try:
        result = PDCEngine.analyze_power_duration(request.power_curve)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DFA Analysis Endpoints ---
@app.post("/hrv/dfa")
async def analyze_dfa(request: DFARequest):
    """
    Calculate DFA alpha 1 from RR interval data.
    Returns time series of DFA values and VT1 detection if applicable.
    """
    try:
        from dfa_analysis import analyze_rr_stream, detect_vt1_from_activity
        
        # Analyze RR stream with sliding window
        dfa_timeline = analyze_rr_stream(
            rr_data=request.rr_data,
            window_seconds=request.window_seconds
        )
        
        # Detect VT1 if power data provided
        vt1_result = None
        if request.power_data:
            vt1_result = detect_vt1_from_activity(
                rr_data=request.rr_data,
                power_data=request.power_data
            )
        
        return {
            "dfa_timeline": dfa_timeline,
            "vt1_detection": vt1_result,
            "window_seconds": request.window_seconds,
            "total_samples": len(request.rr_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Velo Lab Analysis API - RR/DFA Enabled", "version": "1.4.0"}

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
            mmp15=request.mmp15,
            use_3point_cp=request.use_3point_cp,
            mmp_additional=request.mmp_additional
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
                overreaching["days_depressed"] if overreaching else 0,
                baseline.get("cv_status", "OPTIMAL")  # Include CV status in recommendation
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
