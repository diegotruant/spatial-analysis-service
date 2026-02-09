from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import tempfile

from fit_generator import generate_fit_from_json

router = APIRouter()

class BikeSample(BaseModel):
    timestamp: str
    hr: Optional[int] = None
    power: Optional[int] = None
    cadence: Optional[int] = None
    speed: Optional[float] = None
    rr: Optional[List[float]] = [] # RR in seconds

class FitRequest(BaseModel):
    sport: str
    start_time: str
    samples: List[BikeSample]

@router.post("/generate_fit")
async def create_fit_file(request: FitRequest):
    try:
        # Convert Pydantic model to dict
        data = request.dict()
        
        # Generate FIT
        fit_path = generate_fit_from_json(data)
        
        if not os.path.exists(fit_path):
             raise HTTPException(status_code=500, detail="FIT file creation failed")
             
        # Return file
        # Note: We should probably return it as a stream or save it to a permanent location
        # For now, return as attachment. 
        # CAUTION: Cleanup might be needed if using temp file. 
        # FileResponse can handle background tasks for cleanup if needed, 
        # but standard FileResponse just reads it.
        
        return FileResponse(
            path=fit_path, 
            filename=f"activity_{request.start_time.replace(':', '-')}.fit", 
            media_type='application/octet-stream'
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
