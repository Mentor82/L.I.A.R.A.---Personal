# liara/api/routers/automation_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/automation",
    tags=["Automation"]
)

class Automation(BaseModel):
    id: int
    name: str
    steps: List[str]

AUTOMATION_DB = []

@router.post("/create", response_model=Automation)
def create_automation(automation: Automation):
    """
    Erstellt eine neue Automation.
    Beispiel:
        - VM starten
        - Edge01 rebooten
        - Backup triggern
    """
    AUTOMATION_DB.append(automation)
    return automation

@router.post("/run/{automation_id}")
def run_automation(automation_id: int):
    """
    Führt die definierte Automation aus.
    Später:
        - echte Orchestrierung
        - Logs
        - Error-Handling
    """
    return {"status": "running", "automation_id": automation_id}
