"""
🖼️ Vision API - Bildanalyse mit LLaVA
Endpoints für Bild-Upload und multimodale Analyse
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import base64
import io
import os
import time
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from api.models.base_models import User
from core.dependencies import require_active_user
from core.database import get_db
from services.vision_service import VisionService, get_vision_service
from services.vision_detection_service import get_vision_detection_service
from services.chat_persistence import persist_chat_turn

router = APIRouter(
    prefix="/vision",
    tags=["Vision"]
)


class ImageAnalysisRequest(BaseModel):
    """Request für Bildanalyse"""
    prompt: str = "Beschreibe dieses Bild detailliert auf Deutsch."
    temperature: float = 0.7


class ImageAnalysisResponse(BaseModel):
    """Response der Bildanalyse"""
    description: str
    model_used: str
    processing_time_ms: int
    image_size: dict
    timestamp: str


class DetectionBox(BaseModel):
    """Bounding box für Objekterkennung"""
    x: float
    y: float
    width: float
    height: float
    score: float
    label: str


class VisionDetectResponse(BaseModel):
    """Antwort der Objekterkennung"""
    backend: str
    model: str
    boxes: List[DetectionBox]
    latency_ms: float
    image_size: dict


@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    prompt: str = "Beschreibe dieses Bild detailliert auf Deutsch.",
    current_user: User = Depends(require_active_user)
):
    """
    📸 Analysiere ein hochgeladenes Bild mit LLaVA
    
    Unterstützte Formate: JPG, PNG, WEBP
    Max. Größe: 10 MB
    
    Args:
        file: Bilddatei
        prompt: Analyseaufforderung (z.B. "Was ist auf dem Bild zu sehen?")
        
    Returns:
        Detaillierte Bildbeschreibung
    """
    # 1. Validierung
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Dateityp: {file.content_type}. Nur Bilder erlaubt."
        )
    
    # 2. Größencheck (10 MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Bild zu groß. Maximum: 10 MB"
        )
    
    # 3. Base64 Encoding
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    # 4. Vision Service
    vision_service = get_vision_service()
    
    try:
        start_time = datetime.now()
        
        result = await vision_service.analyze_image(
            image_base64=image_base64,
            prompt=prompt,
            user_id=current_user.id
        )
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return ImageAnalysisResponse(
            description=result['description'],
            model_used=result['model_used'],
            processing_time_ms=processing_time,
            image_size={
                'bytes': len(content),
                'mb': round(len(content) / (1024 * 1024), 2)
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bildanalyse fehlgeschlagen: {str(e)}"
        )


@router.post("/detect", response_model=VisionDetectResponse)
async def detect_image(
    file: UploadFile = File(...),
    backend: str = Form("hailo"),
    model: str = Form("yolov8n"),
    score_threshold: float = Form(0.25),
    current_user: User = Depends(require_active_user)
):
    """
    🎯 Objekterkennung mit wählbarem Backend (Hailo, EdgeTPU, CPU-Stub).

    - backend: "hailo" | "edgetpu" | "cpu"
    - model:   model-ID (z.B. "yolov8n")
    - score_threshold: gewünschter Schwellenwert (nur relevant, wenn das Backend ihn nutzt)
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilder erlaubt")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß (max 10 MB)")

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(content))
        width, height = img.size
    except Exception as e:  # pragma: no cover - fallback
        raise HTTPException(status_code=400, detail=f"Bild konnte nicht gelesen werden: {e}")

    detection_service = get_vision_detection_service()
    start = time.time()

    try:
        result = await detection_service.detect_objects(
            image_bytes=content,
            backend=backend,
            model=model,
            confidence_threshold=score_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - runtime errors
        raise HTTPException(status_code=500, detail=f"Erkennung fehlgeschlagen: {e}")

    latency_ms = result.get("latency_ms", (time.time() - start) * 1000)

    return VisionDetectResponse(
        backend=result.get("backend", backend),
        model=result.get("model", model),
        boxes=[DetectionBox(**box) for box in result.get("boxes", [])],
        latency_ms=latency_ms,
        image_size={
            "width": width,
            "height": height,
            "bytes": len(content),
            "mb": round(len(content) / (1024 * 1024), 2),
        },
    )


@router.post("/chat")
async def vision_chat(
    file: UploadFile = File(...),
    message: str = "Was siehst du auf diesem Bild?",
    session_id: Optional[int] = None,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db)
):
    """
    💬 Chat mit Bild-Kontext (für Chat-Integration)

    Kombiniert Bildanalyse mit Konversation.
    Kann mehrere Fragen zum selben Bild beantworten.
    """
    # Validierung
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Nur Bilder erlaubt")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß (max 10 MB)")

    image_base64 = base64.b64encode(content).decode('utf-8')

    vision_service = get_vision_service()

    try:
        result = await vision_service.analyze_image(
            image_base64=image_base64,
            prompt=message,
            user_id=current_user.id
        )

        # issue #13: persist this turn ourselves (server-side, before
        # responding) rather than have the client post the description
        # back afterward as a trusted "assistant" message.
        if session_id:
            persist_chat_turn(db, session_id, current_user.id, message, result['description'], model=result['model_used'])

        return {
            'response': result['description'],
            'model_used': result['model_used'],
            'has_image': True,
            'image_format': file.content_type
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_vision_models(current_user: User = Depends(require_active_user)):
    """
    📋 Liste verfügbare Vision-Modelle
    
    Zeigt alle installierten multimodalen Modelle (LLaVA, etc.)
    """
    vision_service = get_vision_service()
    models = await vision_service.list_available_models()
    
    return {
        'available_models': models,
        'default_model': 'gemma4:cloud',
        'recommended': {
            'fast': 'gemma4:cloud',
            'quality': 'kimi-k3:cloud',
            'local': 'llava:7b'
        }
    }


@router.get("/status")
async def get_vision_status():
    """
    🔍 Vision Service Status
    
    Prüft ob Vision verfügbar ist
    """
    vision_service = get_vision_service()
    is_available = await vision_service.is_available()
    
    return {
        'vision_available': is_available,
        'model': 'gemma4:cloud',
        'capabilities': [
            'Bildbeschreibung',
            'Objekt-Erkennung',
            'Szenen-Analyse',
            'Text-Extraktion (OCR)',
            'Fragen zu Bildern beantworten'
        ]
    }
