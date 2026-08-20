# liara/api/routers/memory_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(
    prefix="/memory",
    tags=["Liara Memory"]
)

class MemoryItem(BaseModel):
    id: int
    content: str
    category: Optional[str] = None

# Dummy-Daten (später durch SQLite/JSON/VectorStore ersetzt)
MEMORY_DB = []

@router.post("/add", response_model=MemoryItem)
def add_memory(item: MemoryItem):
    """
    Fügt einen Gedächtniseintrag hinzu.
    -----------------------------------
    Später:
        - persistente Speicherung (SQLite oder JSON)
        - Kategorien & Tags
        - Querying mit NLP-Interpretation
    """
    MEMORY_DB.append(item)
    return item

@router.get("/list", response_model=List[MemoryItem])
def list_memory():
    """
    Listet alle gespeicherten Erinnerungen.
    """
    return MEMORY_DB

@router.get("/search", response_model=List[MemoryItem])
def search_memory(query: str):
    """
    Volltextsuche nach einem Begriff.
    ---------------------------------
    Später:
        - fuzzy search
        - embedding-basierte Ähnlichkeit
    """
    return [m for m in MEMORY_DB if query.lower() in m.content.lower()]
