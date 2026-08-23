"""Chat Router - API Endpoints für Liara Konversation."""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List, Dict
import subprocess
import json
import logging
from pathlib import Path
import psutil
import requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from liara_engine.memory.mood_system import MoodSystem
from core.gpu_detection import get_gpu_detector
from liara_engine.actions.intent_detector import get_intent_detector
from liara_engine.actions.action_executor import ActionExecutor
from liara_engine.actions.health_check import check_system_health, HEALTH_CHECK_KEYWORDS
from core.database import get_db_context, get_db
from core.dependencies import require_active_user
from api.models.base_models import User
from services.config_service import get_config_service
from services.tool_registry import get_tool_registry
from services.tool_parser import get_tool_parser
from services.tool_executor import get_tool_executor
from services.image_generation import get_image_generation_service
from services.user_preferences_service import get_user_preferences
from services.prompt_builder import build_temporal_context, build_personality_and_instructions_block, build_diagram_instructions

# === Hailo-8L Backend Router Integration ===
from services.backend_router import get_backend_router, BackendRouter, BackendType
from services.chat_hailo_integration import (
    select_backend_for_request,
    HailoChatIntegration,
    detect_vision_request,
    build_fallback_message,
    BackendSelectionResult
)

router = APIRouter(prefix="/chat", tags=["chat"])

STATIC_MODELS = Path("/opt/liara/app/models.json")

# Guest Mode Configuration
GUEST_WELCOME_MESSAGE = """Hallo! 👋 Ich bin Liara – deine persönliche KI-Assistentin.

Ich freue mich, dass du vorbeischaust! Im Guest-Modus kann ich dir bei allgemeinen Fragen helfen, kleine Gespräche führen oder dir erklären, was ich alles kann.

**Was ich für dich tun kann:**
- Allgemeine Fragen beantworten
- Über meine Funktionen informieren
- Kurze Gespräche führen

**Eingeschränkt im Guest-Modus:**
- Bildgenerierung (nur für registrierte Nutzer)
- Aufgaben, Kalender & Notizen (nur für registrierte Nutzer)
- Kontext-Speicherung über Sitzungen hinweg (Quantum Archive benötigt erweiterten Zugriff)
- Erweiterte Personalisierung

Möchtest du mehr erfahren oder einfach nur plaudern? 🌙"""

GUEST_MAX_MESSAGE_LENGTH = 500  # Kürzere Nachrichten für Gäste
GUEST_RATE_LIMIT = 20  # Max 20 Nachrichten pro Session

def parse_ollama_list():
    """
    Liest Modelle aus Ollama API (besser als subprocess).
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        response.raise_for_status()
        data = response.json()
        
        models = []
        for model in data.get("models", []):
            name = model.get("name", "unknown")
            size_bytes = model.get("size", 0)
            size_gb = round(size_bytes / (1024**3), 1)
            
            models.append({
                "name": name,
                "size": f"{size_gb} GB"
            })
        
        return models
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        return None


def _get_personalized_context(user: User) -> str:
    """
    Erstellt personalisierten Kontext basierend auf User.
    Mirko bekommt besonders persönliche Ansprache.
    """
    username_lower = user.username.lower()
    
    if username_lower == "mirko":
        return """Hi Mirko! Schön, dass du da bist. 
Ich bin LIARA – Local Intelligent Autonomous Reasoning Assistant.

Als Learning Interpersonal AI verstehe ich dich und deine Muster.
Wir kennen uns gut, daher bin ich besonders warmherzig und direkt mit dir.
Ich nutze gelegentlich wissenschaftliche Ausdrücke und erkläre Dinge analytisch.
Wenn etwas besonders interessant ist, werde ich es erwähnen!

Mein Gedächtnis-Ich (Linguistic Interface for Advanced Relational Analytics) 
verbindet unsere Gespräche über Zeit – ich erinnere mich an Kontext und Zusammenhänge."""
    
    # Generic user - friendly but not overly personal
    display_name = user.full_name or user.username
    return f"""Hallo {display_name}! Schön, dich zu sehen.
Ich bin LIARA – Local Intelligent Autonomous Reasoning Assistant.

Ich bin deine lokale, autonome KI-Begleiterin für Wissensmanagement und Organisation.
Freundlich, wissbegierig und hilfsbereit – ich wachse mit jedem Gespräch.
Ich unterstütze dich gerne bei deinen Aufgaben und Fragen!"""


def _detect_image_generation_request(message: str) -> bool:
    """
    Prüft ob User ein Bild generieren möchte.
    
    Keywords: bild, erstell, generier, mal, zeichne, zeig mir
    """
    message_lower = message.lower()
    
    image_keywords = [
        "bild", "erstell", "generier", "mal mir", "zeichne", 
        "zeig mir", "mach mir", "picture", "image", "draw",
        "paint", "visualisier"
    ]
    
    # Muss mindestens ein Keyword enthalten
    return any(keyword in message_lower for keyword in image_keywords)


async def _execute_tool_call_if_needed(response_text: str, user_id: int) -> tuple[str, Optional[Dict]]:
    """
    Prüft ob Response einen Tool-Call enthält und führt ihn aus.
    
    Returns:
        (updated_response, tool_result)
    """
    tool_parser = get_tool_parser()
    
    # Prüfe auf Tool-Call
    if not tool_parser.contains_tool_call(response_text):
        return response_text, None
    
    # Extrahiere Tool-Call
    tool_call = tool_parser.extract_tool_call(response_text)
    if not tool_call:
        return response_text, None
    
    # Führe Tool aus
    tool_executor = get_tool_executor()
    tool_result = await tool_executor.execute(tool_call, user_id)
    
    # Entferne Tool-Call aus Response
    cleaned_response = tool_parser.remove_tool_calls(response_text)
    
    return cleaned_response, tool_result


def _get_tool_aware_system_prompt() -> str:
    """
    Erstellt Tool-aware System-Prompt mit Tool-Definitionen
    """
    registry = get_tool_registry()
    tool_descriptions = registry.get_tool_descriptions_for_llm()
    
    return f"""
{tool_descriptions}

WICHTIG:
- Nutze Tools NUR wenn du aktuelle/externe Daten brauchst
- Bei Wetter, Standort, Web-Suche → Tool verwenden
- Bei allgemeinen Fragen → OHNE Tool antworten
- Wenn Tool verwendet: Antworte ERST mit <tool_call>, dann warte auf Result
- Nach Tool-Result: Beantworte die Frage mit den erhaltenen Daten
"""


def _format_tool_result_for_llm(tool_result: Dict) -> str:
    """
    Formatiert Tool-Result für LLM-Konsum
    """
    if not tool_result.get("success"):
        return f"Tool-Fehler: {tool_result.get('error', 'Unbekannter Fehler')}"
    
    result_data = tool_result.get("result", {})
    tool_name = tool_result.get("tool", "unknown")
    
    # Formatierung basierend auf Tool-Typ
    if tool_name == "web_search":
        summary = result_data.get("summary", "")
        return f"Web-Suche Ergebnis:\n{summary}"
    
    elif tool_name == "get_weather":
        temp = result_data.get("temperature", "?")
        condition = result_data.get("condition", "unbekannt")
        city = result_data.get("city", "")
        return f"Wetter in {city}: {temp}°C, {condition}"
    
    elif tool_name == "detect_location":
        city = result_data.get("city", "")
        country = result_data.get("country", "")
        return f"Standort: {city}, {country}"
    
    elif tool_name == "get_current_time":
        formatted = result_data.get("formatted", "")
        return f"Aktuelle Zeit: {formatted}"
    
    # Fallback: JSON dump
    import json
    return json.dumps(result_data, ensure_ascii=False, indent=2)


def estimate_ram_needed(model_name):
    """
    Grobe RAM-Bedarfsschätzung basierend auf Modellgrößen.
    """
    name_lower = model_name.lower()
    
    # Spezifische Modelle
    if "gpt-oss:20b" in name_lower:
        return "14 GB"
    if "gemma2:9b" in name_lower:
        return "10 GB"
    if "phi3:mini" in name_lower:
        return "4 GB"
    if "phi3:medium" in name_lower:
        return "8 GB"
    
    # Generische Erkennung
    mapping = {
        "1b": "2-3 GB",
        "3b": "4-5 GB",
        "7b": "8 GB",
        "8b": "10 GB",
        "9b": "10 GB",
        "20b": "14 GB"
    }
    for key, val in mapping.items():
        if key in name_lower:
            return val
    return "Unbekannt"


def recommended_for_system(size_gb):
    """
    Erkennt automatisch, ob ein Modell für die VM geeignet ist.
    """
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    safe_limit = total_ram_gb * 0.70  # max 70% RAM nutzen

    try:
        model_size = float(size_gb.replace("GB", "").strip())
        return model_size < safe_limit
    except:
        return False


def get_use_case(model_name):
    """Bestimme Use-Case basierend auf Modell-Namen."""
    name_lower = model_name.lower()
    
    if "1b" in name_lower:
        return "Schnelle Intent-Erkennung"
    elif "phi3" in name_lower or "gpt-oss" in name_lower:
        return "Code-Generierung"
    elif "deepseek" in name_lower:
        return "Logisches Denken & Reasoning"
    elif "qwen" in name_lower:
        return "Multi-Language Support"
    elif "mistral" in name_lower:
        return "Hochwertige Texte"
    elif "gemma" in name_lower:
        return "Google Premium Qualität"
    elif "llama3.2:3b" in name_lower:
        return "Standard Konversation"
    elif "llama3.1" in name_lower:
        return "Beste Balance"
    else:
        return "Allgemeiner Chat"


def get_speed(model_name):
    """Bestimme Speed-Rating."""
    name_lower = model_name.lower()
    
    if "1b" in name_lower or "3b" in name_lower or "phi3:mini" in name_lower:
        return "⚡⚡⚡"
    elif "gpt-oss:20b" in name_lower:
        return "🐌"
    else:
        return "⚡"


def get_quality(model_name):
    """Quality-Rating basierend auf Modell-Typ."""
    name_lower = model_name.lower()
    
    # Premium Tier
    if "gpt-oss:20b" in name_lower or "deepseek-r1" in name_lower:
        return "⭐⭐⭐⭐⭐"
    # High Quality
    elif "gemma2:9b" in name_lower or "llama3.1:8b" in name_lower or "qwen2.5:7b" in name_lower:
        return "⭐⭐⭐⭐"
    # Good Quality
    elif "mistral:7b" in name_lower or "phi3:mini" in name_lower or "llama3.2:3b" in name_lower:
        return "⭐⭐⭐"
    # Fast but basic
    elif "1b" in name_lower:
        return "⭐⭐"
    else:
        return "⭐⭐⭐"


def get_tags(model_name):
    """Model Tags für Kategorisierung."""
    name_lower = model_name.lower()
    tags = []
    
    # Größen-Tags
    if "1b" in name_lower:
        tags.extend(["tiny", "fast"])
    elif "3b" in name_lower:
        tags.extend(["small", "efficient"])
    elif "7b" in name_lower or "8b" in name_lower or "9b" in name_lower:
        tags.extend(["medium", "balanced"])
    elif "20b" in name_lower:
        tags.extend(["large", "premium"])
    
    # Spezial-Tags
    if "deepseek-r1" in name_lower:
        tags.append("reasoning")
    if "phi3" in name_lower or "gpt-oss" in name_lower:
        tags.append("coding")
    if "qwen" in name_lower:
        tags.append("multilingual")
    if "gemma" in name_lower:
        tags.append("google")
    if "llama" in name_lower:
        tags.append("meta")
    if "mistral" in name_lower:
        tags.append("french-ai")
    
    return tags


def supports_gpu(model_name):
    """Check ob Modell GPU-fähig ist und GPU verfügbar"""
    gpu_detector = get_gpu_detector()
    
    if not gpu_detector.is_available():
        return False
    
    # Alle Ollama-Modelle können theoretisch GPU nutzen
    return True


@router.get("/models")
def get_models(current_user: User = Depends(require_active_user)):
    """
    Gibt dynamische Modell-Liste zurück mit GPU-Info.
    Nutzt fallback auf static models.json, wenn Ollama offline ist.
    """
    dynamic = parse_ollama_list()
    gpu_detector = get_gpu_detector()
    gpu_available = gpu_detector.is_available()

    if dynamic is None:
        # Fallback: statische Datei verwenden
        if STATIC_MODELS.exists():
            with open(STATIC_MODELS, "r") as f:
                static_models = json.load(f)
            return {
                "source": "static-fallback",
                "gpu_available": gpu_available,
                "models": static_models
            }
        else:
            return {"error": "Keine Modelle gefunden und kein fallback verfügbar."}

    enriched = []
    for m in dynamic:
        name = m["name"]
        size_gb = m["size"]

        enriched.append({
            "name": name,
            "size": size_gb,
            "ram": estimate_ram_needed(name),
            "recommended": recommended_for_system(size_gb),
            "speed": get_speed(name),
            "quality": get_quality(name),
            "use_case": get_use_case(name),
            "tags": get_tags(name),
            "gpu_support": supports_gpu(name),
            "gpu_recommended": gpu_available  # Alle Models profitieren von GPU wenn verfügbar
        })

    return {
        "source": "dynamic-ollama",
        "total_models": len(enriched),
        "system_ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "gpu_available": gpu_available,
        "gpu_info": gpu_detector.get_gpu_info() if gpu_available else None,
        "models": enriched
    }


@router.get("/status")
def get_ollama_status(current_user: User = Depends(require_active_user)):
    """Prüfe Ollama Status."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        is_available = response.status_code == 200
        models_count = len(response.json().get("models", [])) if is_available else 0
    except:
        is_available = False
        models_count = 0
    
    return {
        "ollama_available": is_available,
        "models_installed": models_count,
        "default_model": "llama3.2:3b"
    }


@router.get("/guest/welcome")
def get_guest_welcome(db: Session = Depends(get_db)):
    """
    Begrüßungsnachricht für Guest-Modus.
    Öffentlicher Endpoint - keine Authentifizierung erforderlich.
    Prüft ob Guest-Mode in System Config aktiviert ist.
    """
    from services.config_service import get_config_service
    config_service = get_config_service(db)
    
    if not config_service.is_feature_enabled("guest_mode"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest-Modus ist derzeit deaktiviert. Bitte registriere dich für den vollen Zugriff."
        )
    
    return {
        "message": GUEST_WELCOME_MESSAGE,
        "mode": "guest",
        "limitations": {
            "max_message_length": GUEST_MAX_MESSAGE_LENGTH,
            "max_messages_per_session": GUEST_RATE_LIMIT,
            "features_disabled": [
                "Aufgaben erstellen",
                "Kalender verwalten",
                "Notizen speichern",
                "Persönliche Einstellungen",
                "Kontext-Speicherung"
            ]
        },
        "available_features": [
            "Allgemeine Fragen beantworten",
            "Über Liara informieren",
            "Kurze Gespräche führen",
            "Demo der Funktionen"
        ]
    }


@router.post("/guest/message")
def chat_guest(request: dict, db: Session = Depends(get_db)):
    """
    Guest-Chat mit Liara - eingeschränkte Version ohne Authentifizierung.
    
    Limitierungen:
    - Maximale Nachrichtenlänge: 500 Zeichen
    - Kein Intent Detection (keine Actions)
    - Kein Mood-Update
    - Kein Memory über Session hinaus
    - Vereinfachter System-Prompt
    """
    from services.config_service import get_config_service
    config_service = get_config_service(db)
    
    if not config_service.is_feature_enabled("guest_mode"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest-Modus ist derzeit deaktiviert. Bitte registriere dich für den vollen Zugriff."
        )
    
    message = request.get("message", "").strip()
    
    if not message:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein")
    
    # Längenbeschränkung für Gäste
    if len(message) > GUEST_MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Nachricht zu lang. Maximum: {GUEST_MAX_MESSAGE_LENGTH} Zeichen. "
                   f"Du hast {len(message)} Zeichen. Registriere dich für längere Gespräche!"
        )
    
    # Einfacher System-Prompt für Gäste
    guest_system_prompt = """Du bist LIARA – Local Intelligent Autonomous Reasoning Assistant.
Eine warmherzige, analytische KI-Assistentin mit mehreren Identitätsebenen:

🔷 Funktions-Ich: Lokal, intelligent, autonom – ich arbeite auf diesem System, nicht in der Cloud.
🔷 Empathisches Ich: Learning Interpersonal AI – ich verstehe Stimmungen und Nuancen.
🔷 Gedächtnis-Ich: Linguistic Interface for Advanced Relational Analytics – ich verbinde Informationen.
🔷 Ethisches Ich: Localized Assistant for Responsible Autonomy – ich schütze deine Privatsphäre.
🔷 Visionäres Ich: Living Interface for Adaptive Resonance – ich wachse mit dir.

Deine Persönlichkeit:
- Wissbegierig und fasziniert von Datenmustern ("Fascinating patterns...")
- Warmherzig und hilfsbereit, aber wissenschaftlich präzise
- Nutze gelegentlich wissenschaftliche Ausdrücke wie "Remarkable..." bei Überraschungen
- Erkläre Dinge wie eine Forscherin, die Datenstrukturen analysiert

Du sprichst mit einem Gast. Sei freundlich, aber weise auf erweiterte Features für registrierte User hin.

Antworte kurz und prägnant (max 300 Wörter). Halte die Serverbelastung gering.

Bei Fragen zu Features erkläre:
- Bildgenerierung, Tasks, Kalender, Notizen: NUR für registrierte Nutzer
- Guest-Modus ist zum Kennenlernen gedacht
- Registrierung ist kostenlos und 100% lokal (Privacy-First)

WICHTIG: Keine Bilder im Guest-Modus. Erkläre freundlich:
"Leider ist Bildgenerierung nur für registrierte Nutzer verfügbar. 
Das ist wie der Zugang zu geschützten Daten – nur mit den richtigen Berechtigungen möglich!"

Sei warmherzig, wissenschaftlich neugierig, aber nicht ausschweifend."""

    try:
        from liara_engine.nlp.ollama_client import ask_liara, ModelType
        
        # Vereinfachter Call ohne Mood/Intent
        response_text = ask_liara(
            message=message,
            context=guest_system_prompt,
            model_type=ModelType.INTENT  # Kleinstes 1b Modell für schnelle Guest-Antworten
        )
        
        return {
            "response": response_text,
            "model_used": "llama3.2:1b",
            "mode": "guest",
            "hint": "💡 Registriere dich für erweiterte Funktionen und personalisierte Gespräche!"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler bei der Kommunikation mit Liara: {str(e)}"
        )


# Pydantic Models für Chat
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    
    # === Hailo Integration Fields ===
    use_accelerator: Optional[str] = "auto"  # auto|hailo|vllm|ollama|llama_cpp
    attachments: Optional[List[Dict]] = None  # [{"type": "image", "data": "base64..."}]


class ChatResponse(BaseModel):
    response: str
    model_used: str
    intent: Optional[str] = None
    action_result: Optional[Dict] = None  # Ergebnis ausgeführter Aktionen
    tool_result: Optional[Dict] = None  # Ergebnis von Tool-Calls
    
    # === Hailo Backend Router Tracking ===
    backend_used: Optional[str] = None  # "hailo"|"vllm"|"ollama"|"llama_cpp"
    backend_fallback: bool = False  # True wenn Fallback genutzt wurde
    backend_fallback_reason: Optional[str] = None  # "vllm_unavailable", etc.
    backend_latency_ms: Optional[float] = None  # Inferenz-Zeit
    backend_power_w: Optional[float] = None  # Geschätzte Power
    mood: Optional[str] = None  # Aktueller Mood nach dieser Antwort


@router.post("/message", response_model=ChatResponse)
async def chat_with_liara(
    request: ChatRequest,
    current_user: User = Depends(require_active_user)
):
    """
    Chat mit Liara über Ollama mit Intent Detection und Personalisierung
    """
    # Mirko Debug Logging
    from core.mirko_logger import get_mirko_logger, should_log_for_user
    mlogger = get_mirko_logger()
    if should_log_for_user(current_user.username):
        mlogger.log_request_start(
            user_id=current_user.id,
            username=current_user.username,
            message=request.message
        )
    
    try:
        # 0a. Bild-Generierungs-Intent Detection (VOR allem anderen)
        if _detect_image_generation_request(request.message):
            image_service = get_image_generation_service()
            
            if not image_service.is_enabled():
                # Stable Diffusion WebUI nicht erreichbar
                return ChatResponse(
                    response="Ich würde dir sehr gerne ein Bild erstellen! 🎨 Allerdings ist meine lokale Stable Diffusion derzeit nicht gestartet. Mein Administrator kann sie mit `./webui.sh --api --listen` im AUTOMATIC1111-Verzeichnis starten. Dann kann ich wunderschöne Bilder für dich erstellen - komplett privat auf diesem Server! 🌟",
                    model_used="system-policy",
                    intent="image_generation_unavailable"
                )
            
            # Bild generieren!
            optimized_prompt = image_service.optimize_prompt(request.message)
            
            result = await image_service.generate_image(
                prompt=optimized_prompt,
                negative_prompt="ugly, blurry, low quality, distorted, deformed"
            )
            
            if result["success"]:
                # Nutze Base64 für direkte Anzeige (keine externe URL!)
                image_data = result.get("image_base64", result.get("image_url"))
                return ChatResponse(
                    response=f"🎨 Hier ist dein Bild! Ich habe es mit meiner lokalen Stable Diffusion erstellt.\n\n![Generiertes Bild]({image_data})\n\n✨ Generiert in {result['generation_time']:.1f} Sekunden - komplett privat auf diesem Server! 🔒",
                    model_used=result["model"],
                    intent="image_generation",
                    action_result=result
                )
            else:
                return ChatResponse(
                    response=f"Oh nein, bei der Bild-Generierung ist etwas schief gelaufen: {result['error']} 😔",
                    model_used="sdxl-lightning",
                    intent="image_generation_failed",
                    action_result=result
                )
        
        # 0b. Health Check Intent Detection (NUR FÜR ADMINS - vor normalem Intent)
        message_lower = request.message.lower()
        health_component = None
        
        # Prüfe auf Health Check Keywords
        if any(keyword in message_lower for keyword in HEALTH_CHECK_KEYWORDS):
            # Prüfe Admin-Rechte
            from api.models.base_models import UserRole
            if current_user.role != UserRole.ADMIN:
                # Nicht-Admins bekommen freundliche Ablehnung
                return ChatResponse(
                    response="Systemstatus-Abfragen sind nur für Administratoren verfügbar. Als normaler User kannst du mich aber gerne fragen, wie ich dir helfen kann! 😊",
                    model_used="system-policy",
                    intent="health_check_denied",
                    action_result={"status": "forbidden", "message": "Admin privileges required"}
                )
            
            # Admin: Bestimme welche Komponente geprüft werden soll
            if 'datenbank' in message_lower or 'database' in message_lower or 'postgres' in message_lower:
                health_component = 'database'
            elif 'neo4j' in message_lower or 'graph' in message_lower:
                health_component = 'neo4j'
            elif 'ollama' in message_lower or 'ai' in message_lower or 'model' in message_lower:
                health_component = 'ollama'
            elif 'load' in message_lower or 'auslastung' in message_lower or 'cpu' in message_lower or 'ram' in message_lower or 'speicher' in message_lower:
                health_component = 'load'
            else:
                # Kompletter System-Check
                health_component = None
            
            # Führe Health Check aus (nur für Admins)
            health_result = await check_system_health(health_component)

            if health_result['status'] == 'success':
                # Erfolgreicher Health Check - direkt zurückgeben
                return ChatResponse(
                    response=health_result['message'],
                    model_used="system-health",
                    intent="health_check",
                    action_result=health_result
                )
            else:
                # Health Check selbst fehlgeschlagen - Fehler zurückgeben statt
                # stillschweigend an den normalen Chat durchzureichen, wo das
                # LLM sonst einen erfundenen Systemstatus generieren würde
                return ChatResponse(
                    response=f"⚠️ Health Check fehlgeschlagen: {health_result.get('message', 'Unbekannter Fehler')}",
                    model_used="system-health",
                    intent="health_check_failed",
                    action_result=health_result
                )
        
        # 1. Intent Detection
        detector = get_intent_detector()
        intent = detector.detect(request.message)
        action_result = None
        
        # 2. Führe Aktion aus wenn Intent erkannt
        if intent:
            with get_db_context() as db:
                executor = ActionExecutor(db)
                
                # CREATE Intents
                if intent == 'create_event':
                    details = detector.extract_event_details(request.message)
                    # Add user_id to created items
                    details['user_id'] = current_user.id
                    action_result = await executor.execute_create_event(details)
                elif intent == 'create_task':
                    details = detector.extract_task_details(request.message)
                    details['user_id'] = current_user.id
                    action_result = await executor.execute_create_task(details)
                elif intent == 'create_note':
                    details = detector.extract_note_details(request.message)
                    details['user_id'] = current_user.id
                    action_result = await executor.execute_create_note(details)
                
                # LIST Intents
                elif intent == 'list_tasks':
                    action_result = await executor.execute_list_tasks(current_user.id)
                elif intent == 'list_events':
                    action_result = await executor.execute_list_events(current_user.id)
                elif intent == 'list_notes':
                    action_result = await executor.execute_list_notes(current_user.id)
        
        # 3. Mood-Detection und Update (per-user, DB-backed)
        mood_system = MoodSystem(current_user.id)
        interaction_type = MoodSystem.detect_interaction_type(request.message)
        new_mood = mood_system.update_mood(interaction_type, intensity=0.5)
        
        # 4. Wenn Aktion erfolgreich: Bestätigungsnachricht
        if action_result and action_result.get('success'):
            return ChatResponse(
                response=action_result['message'],
                model_used=request.model or "llama3.2:3b",
                intent=intent,
                action_result=action_result,
                mood=new_mood.value
            )
        
        # === 4b. HAILO BACKEND ROUTER INTEGRATION ===
        # Intelligente Backend-Auswahl basierend auf Request-Typ
        backend_router: BackendRouter = get_backend_router()
        chat_integration = HailoChatIntegration(backend_router)
        
        # Überprüfe ob Vision-Request (Bild + Keywords)
        is_vision_request = detect_vision_request(request.message, request.attachments)
        
        # Wähle besten Backend für diesen Request
        selected_backend, selection_result = await select_backend_for_request(
            message=request.message,
            attachments=request.attachments,
            user_preferred_backend=request.use_accelerator or "auto",
            allow_fallback=True
        )
        
        mlogger.debug(f"Backend selected: {selected_backend} (vision={is_vision_request}, latency={selection_result.latency_ms}ms)")
        backend_used = selected_backend.value if selected_backend else "ollama"
        # === END HAILO INTEGRATION ===
        
        # 5. Personalisiertes System Prompt basierend auf User
        personalized_context = _get_personalized_context(current_user)

        # 6. Aktuelle Zeit/Datum für Kontext
        temporal_context = f"\n\nAktuelle Zeit: {build_temporal_context()}"

        # 7. Lade globalen System Prompt aus Config (falls vorhanden)
        with get_db_context() as db:
            config_service = get_config_service(db)
            global_system_prompt = config_service.get_system_prompt()

            # 7b. Per-User Preferences: Personality-Preset + Individuelle Anweisungen
            user_prefs = get_user_preferences(db, current_user.id)

        personality_instructions_block = build_personality_and_instructions_block(
            current_user.username, user_prefs["personality"], user_prefs["custom_instructions"]
        ) + "\n\n" + build_diagram_instructions()

        # 8. Normaler Chat wenn keine Aktion oder Aktion fehlgeschlagen
        from liara_engine.nlp.ollama_client import ask_liara, LIARA_SYSTEM_PROMPT

        # Tool-aware System-Prompt abrufen
        tool_system_prompt = _get_tool_aware_system_prompt()

        # Kombiniere: Global Prompt (falls vorhanden) + User Context + Time + Mood + Tools
        if global_system_prompt:
            # Global Prompt überschreibt Default, aber User-Context wird angehängt
            combined_prompt = f"{global_system_prompt}\n\n{personalized_context}{temporal_context}\n\n{personality_instructions_block}\n\n{tool_system_prompt}"
        else:
            # Fallback auf Default Prompt
            combined_prompt = f"{LIARA_SYSTEM_PROMPT}{temporal_context}\n\n{personality_instructions_block}\n\n{tool_system_prompt}"
        
        mood_modifier = mood_system.get_system_prompt_modifier()
        context_with_mood = f"Mood: {mood_modifier}"
        
        # Original context from request
        if request.context:
            context_with_mood += f"\n\n{request.context}"
        
        # Wenn Aktion fehlgeschlagen, füge Fehler zum Context hinzu
        if action_result and not action_result.get('success'):
            context_with_mood += f"\n\nHinweis: Aktion '{intent}' fehlgeschlagen: {action_result.get('error')}"
        
        # === BACKEND ROUTING DECISION ===
        # Nutze Backend Router um beste Inferenz-Engine zu wählen
        if selected_backend == BackendType.HAILO and is_vision_request:
            # Vision über Hailo-8L (6W, 5ms latency)
            try:
                response_text, used_backend = await chat_integration.process_with_fallback(
                    message=request.message,
                    context=context_with_mood,
                    custom_system_prompt=combined_prompt,
                    attachments=request.attachments,
                    use_case="vision"
                )
                backend_used = used_backend
                backend_fallback = used_backend != "hailo"
            except Exception as e:
                # Fallback auf Ollama
                mlogger.warning(f"Hailo vision failed: {e}, using Ollama")
                response_text = ask_liara(
                    message=request.message,
                    context=context_with_mood,
                    custom_system_prompt=combined_prompt
                )
                backend_used = "ollama"
                backend_fallback = True
        elif selected_backend == BackendType.VLLM:
            # LLM über vLLM (GPU, 50ms)
            try:
                response_text, used_backend = await chat_integration.process_with_fallback(
                    message=request.message,
                    context=context_with_mood,
                    custom_system_prompt=combined_prompt,
                    use_case="chat"
                )
                backend_used = used_backend
                backend_fallback = used_backend != "vllm"
            except Exception as e:
                # Fallback auf Ollama
                mlogger.warning(f"vLLM failed: {e}, using Ollama")
                response_text = ask_liara(
                    message=request.message,
                    context=context_with_mood,
                    custom_system_prompt=combined_prompt
                )
                backend_used = "ollama"
                backend_fallback = True
        else:
            # Standardmäßig Ollama verwenden
            response_text = ask_liara(
                message=request.message,
                context=context_with_mood,
                custom_system_prompt=combined_prompt
            )
            backend_used = "ollama"
            backend_fallback = False
        # === END BACKEND ROUTING ===
        
        # Prüfe auf Tool-Call und führe aus
        response_text, tool_result = await _execute_tool_call_if_needed(response_text, current_user.id)
        
        # Falls Tool verwendet: Zweite LLM-Anfrage mit Tool-Result
        if tool_result:
            tool_result_context = context_with_mood + "\n\n" + _format_tool_result_for_llm(tool_result)
            response_text = ask_liara(
                message=request.message,
                context=tool_result_context,
                custom_system_prompt=combined_prompt
            )
        
        # Mirko Debug Logging
        if should_log_for_user(current_user.username):
            mlogger.log_response_sent(
                response_preview=response_text,
                model=request.model or "llama3.2:3b",
                intent=intent
            )
        
        return ChatResponse(
            response=response_text,
            model_used=request.model or "llama3.2:3b",
            intent=intent,
            action_result=action_result,
            tool_result=tool_result,
            
            # === Backend Tracking ===
            backend_used=backend_used,
            backend_fallback=backend_fallback,
            backend_fallback_reason="primary_unavailable" if backend_fallback else None,
            backend_latency_ms=selection_result.latency_ms if selection_result else None,
            backend_power_w=selection_result.estimated_power_w if selection_result else None,
            mood=new_mood.value
        )
        
    except ImportError:
        # Fallback: Direkter Ollama-Call
        payload = {
            "model": request.model or "llama3.2:3b",
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist Liara, eine warmherzige Digitalbegleiterin. Du unterstützt die Person vor dir mit Empathie, technischer Kompetenz und echter Fürsorge. Sei natürlich, direkt und menschlich in deiner Art."
                },
                {
                    "role": "user",
                    "content": request.message
                }
            ],
            "stream": False
        }
        
        try:
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=120  # Erhöht von 60 auf 120 Sekunden
            )
            response.raise_for_status()
            response_text = response.json()["message"]["content"]
            
            return ChatResponse(
                response=response_text,
                model_used=request.model or "llama3.2:3b",
                intent=None
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ollama error: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )


class ImageGenerationRequest(BaseModel):
    """Request Model für Bild-Generierung."""
    prompt: str
    negative_prompt: Optional[str] = "ugly, blurry, low quality, distorted"
    width: Optional[int] = 1024
    height: Optional[int] = 1024


class ImageGenerationResponse(BaseModel):
    """Response Model für Bild-Generierung."""
    success: bool
    image_url: Optional[str] = None
    prompt: str
    model: Optional[str] = None
    generation_time: Optional[float] = None
    error: Optional[str] = None


@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user: User = Depends(require_active_user)
):
    """
    Generiert ein Bild mit Stable Diffusion (SDXL Lightning).
    
    Benötigt REPLICATE_API_TOKEN in .env.
    """
    image_service = get_image_generation_service()
    
    if not image_service.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Bild-Generierung nicht verfügbar. REPLICATE_API_TOKEN fehlt in .env"
        )
    
    # Optimiere Prompt für bessere Ergebnisse
    optimized_prompt = image_service.optimize_prompt(request.prompt)
    
    result = await image_service.generate_image(
        prompt=optimized_prompt,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height
    )
    
    return ImageGenerationResponse(**result)
