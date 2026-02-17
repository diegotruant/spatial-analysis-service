import logging
import os
import sys
import uuid
import json
import psycopg2
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Union, Any, Dict
import polars as pl
from analysis_prototype import analyze_activity, calculate_pmc_trends
from metabolic_engine import MetabolicEngine, MetabolicProfile
from hrv_engine import HRVEngine
from pdc_engine import PDCEngine, PDCAnalysisRequest, PowerCurvePoint

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("velo-lab-analysis")

app = FastAPI(title="Velo Lab Analysis API")

# --- Database & Config ---
# Database connection from .env or hardcoded fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.xdqvjqqwywuguuhsehxm:emvtzC2B2Duu6PLg@aws-1-eu-west-3.pooler.supabase.com:6543/postgres")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

class TaskRepository:
    @staticmethod
    def create_task(task_id: str) -> None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO analysis_tasks (task_id, status) VALUES (%s, %s)",
                (task_id, 'pending')
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to create task {task_id}: {e}")
            raise

    @staticmethod
    def update_task(task_id: str, status: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "UPDATE analysis_tasks SET status = %s, updated_at = NOW()"
            params = [status]
            
            if result:
                query += ", result = %s"
                params.append(json.dumps(result))
            if error:
                query += ", error = %s"
                params.append(error)
                
            query += " WHERE task_id = %s"
            params.append(task_id)
            
            cursor.execute(query, tuple(params))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")

    @staticmethod
    def get_task(task_id: str) -> Optional[dict]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT task_id, status, result, error, created_at, updated_at FROM analysis_tasks WHERE task_id = %s",
                (task_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                return {
                    "task_id": row[0],
                    "status": row[1],
                    "result": row[2],  # psychopg2 automatically converts jsonb
                    "error": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

# --- Core Analysis Logic (Refactored) ---
def _perform_analysis(request: "AnalysisRequest") -> dict:
    """Core analysis logic shared by sync and async endpoints"""
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
    
    # DFA Alpha-1 Analysis
    if request.rr_intervals and len(request.rr_intervals) > 0:
        from experimental_models.dfa_alpha1 import DFAAlpha1
        alpha1_series = DFAAlpha1.calculate_rolling_alpha1(request.rr_intervals)
        results["alpha1_analysis"] = alpha1_series
        
    # Dynamic W' Balance
    from experimental_models.w_prime_dcp import WPrimeDCP
    w_bal_dynamic = WPrimeDCP.calculate_balance(request.power_data, request.ftp, request.w_prime)
    results["w_balance_dynamic"] = w_bal_dynamic
    
    return results

def process_analysis_task(task_id: str, request: "AnalysisRequest"):
    """Background task worker"""
    try:
        logger.info(f"Starting background analysis for task {task_id}")
        TaskRepository.update_task(task_id, "processing")
        
        # Run synchronous heavy analysis
        results = _perform_analysis(request)
        
        TaskRepository.update_task(task_id, "completed", result=results)
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Task {task_id} failed: {error_msg}")
        TaskRepository.update_task(task_id, "failed", error=str(e)) # Store simple error message

# --- CORS Configuration ---
from fastapi.middleware.cors import CORSMiddleware

# Secure CORS: explicit list from env or safe default
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Error Handling ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    # Log the full stack trace securely on the server
    error_detail = f"Unhandled error in {request.url.path}: {str(exc)}\n{traceback.format_exc()}"
    logger.error(error_detail)
    
    # Return a generic error to the client to avoid information disclosure
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please contact support if the issue persists."},
    )

# Include Routers
from routers import fit, experimental
app.include_router(fit.router)
app.include_router(experimental.router)

# --- Models ---
class AnalysisRequest(BaseModel):
    power_data: list[float]
    hr_data: Optional[list[float]] = None
    cadence_data: Optional[list[float]] = None
    ftp: float
    w_prime: float = 20000
    altitude_data: Optional[list[float]] = None  # Altitude in meters for each second
    temperature: Optional[float] = None  # Average temperature in Celsius
    rr_intervals: Optional[list[float]] = None # List of RR intervals in ms for Alpha-1 analysis

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
    """Synchronous analysis endpoint (Blocking) - Legacy"""
    # Use the shared core logic
    return _perform_analysis(request)

@app.post("/analyze/async")
async def analyze_async(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Asynchronous analysis endpoint (Non-blocking)"""
    task_id = str(uuid.uuid4())
    
    # Initialize task in DB
    TaskRepository.create_task(task_id)
    
    # Add to background queue
    background_tasks.add_task(process_analysis_task, task_id, request)
    
    return {"task_id": task_id, "status": "pending", "message": "Analysis started in background"}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status and result of a background task"""
    task = TaskRepository.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task

@app.post("/pmc")
async def calculate_pmc(request: PMCRequest):
    results = calculate_pmc_trends(request.tss_history)
    return results


# --- DFA Analysis Endpoints ---
@app.post("/hrv/dfa")
async def analyze_dfa(request: DFARequest):
    """
    Calculate DFA alpha 1 from RR interval data.
    Returns time series of DFA values and VT1 detection if applicable.
    """
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

@app.get("/")
async def root():
    return {"message": "Velo Lab Analysis API - RR/DFA Enabled", "version": "1.4.1"}

@app.post("/metabolic/profile")
async def calculate_metabolic_profile(request: MetabolicRequest):
    # Removed try/except here to let Global Exception Handler manage it
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

@app.post("/hrv/analyze")
async def analyze_hrv(request: HRVRequest):
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

@app.post("/pdc/analyze")
async def analyze_pdc(request: PDCAnalysisRequestModel):
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
