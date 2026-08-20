# liara/api/routers/gpx_router.py

from fastapi import APIRouter, UploadFile
from typing import Dict

router = APIRouter(
    prefix="/gpx",
    tags=["GPX Analysis"]
)

@router.post("/upload")
async def upload_gpx(file: UploadFile):
    """
    GPX Upload
    ----------
    Später:
        - Parsing via gpxpy
        - Höhenprofil
        - Kurvenklassifizierung
        - Lieblingskurven-Markierung
    """
    return {"filename": file.filename, "status": "uploaded"}

@router.get("/analysis/{tour_id}")
def analyze_tour(tour_id: int) -> Dict:
    """
    Führt eine vollständige Analyse einer Tour durch.
    """
    return {
        "tour_id": tour_id,
        "status": "analysis_pending",
        "details": "Analysis will be implemented in v0.3"
    }
