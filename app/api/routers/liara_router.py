"""Liara Core Router - System Status und Health Checks."""
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional
import psutil
import platform
import requests
import time

from liara_engine.memory.mood_system import get_mood_system

router = APIRouter(
    prefix="/liara",
    tags=["Liara Core"]
)

# Persona Version Tracking
PERSONA_VERSION = "1.2.0"
PERSONA_CHANGELOG = {
    "1.2.0": "Enhanced Mood System mit Confidence + History (2025-12-03)",
    "1.1.0": "Tasks/Calendar/Notes APIs implemented (2025-12-02)",
    "1.0.0": "Initial Persona Definition (2025-12-01)"
}

# Startzeit für Uptime
START_TIME = time.time()

class StatusResponse(BaseModel):
    status: str
    uptime: str
    mode: str
    version: str
    system: Dict[str, Any]
    ollama: Dict[str, Any]
    resources: Dict[str, Any]


def get_uptime() -> str:
    """Berechne Uptime seit Service-Start."""
    uptime_seconds = int(time.time() - START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_ollama_status() -> Dict[str, Any]:
    """Prüfe Ollama Status."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {
                "status": "online",
                "models_available": len(models),
                "active_model": "llama3.2:3b"
            }
    except:
        pass
    
    return {
        "status": "offline",
        "models_available": 0,
        "active_model": None
    }


@router.get("/status", response_model=StatusResponse)
def liara_status():
    """
    🌙 Liara Systemstatus
    
    Zeigt:
    - Uptime seit Service-Start
    - System-Ressourcen (CPU, RAM, Disk)
    - Ollama KI-Engine Status
    - Betriebsmodus
    """
    # System-Infos
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    return StatusResponse(
        status="operational",
        uptime=get_uptime(),
        mode="ready",
        version="1.0.0",
        system={
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version()
        },
        ollama=get_ollama_status(),
        resources={
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(memory.percent, 1),
            "memory_used_gb": round(memory.used / (1024**3), 1),
            "memory_total_gb": round(memory.total / (1024**3), 1),
            "disk_percent": round(disk.percent, 1),
            "disk_free_gb": round(disk.free / (1024**3), 1)
        }
    )


@router.get("/health")
def health_check():
    """Schneller Health-Check für Monitoring."""
    ollama_status = get_ollama_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "up",
            "ollama": ollama_status["status"]
        }
    }


@router.get("/about")
def about_liara():
    """Über Liara - Persona & Capabilities."""
    return {
        "name": "Liara",
        "version": "1.0.0",
        "description": "Deine warmherzige, ausgeglichene und hilfsbereite Digitalbegleiterin",
        "persona": {
            "tone": "warm, calm, structured",
            "focus": "organization, routines, balance",
            "language": "German (primary), English (supported)"
        },
        "capabilities": [
            "Natural conversation",
            "Task management",
            "Calendar & scheduling",
            "Note taking",
            "Code assistance",
            "Multi-language support",
            "Pattern recognition",
            "Stress detection & suggestions"
        ],
        "models": {
            "total": 9,
            "types": [
                "Conversation (llama3.2:3b)",
                "Code (phi3:mini, gpt-oss:20b)",
                "Reasoning (deepseek-r1:7b)",
                "Multi-lang (qwen2.5:7b)",
                "Premium (gemma2:9b, mistral:7b)"
            ]
        }
    }


@router.get("/persona")
def liara_persona():
    """
    🌙 Liara's Persönlichkeitssystem (Enhanced v1.2)
    
    Exponiert Liara's vollständige Identität mit:
    - Versionierung & Changelog
    - Live Mood-Status Integration
    - Trait-Modifiers
    """
    mood_system = get_mood_system()
    mood_status = mood_system.get_mood_status()
    
    return {
        "name": "Liara",
        "identity": "Digitalbegleiterin & Persönliche Assistentin",
        "version": "1.2.0",
        "persona_version": PERSONA_VERSION,
        "changelog": PERSONA_CHANGELOG,
        "last_update": "2025-12-03",
        
        "current_state": {
            "mood": mood_status["current_mood"],
            "mood_intensity": mood_status["intensity"],
            "mood_confidence": mood_status["confidence"],
            "active_trait_modifiers": mood_status["trait_modifiers"]
        },
        
        "tone": {
            "primary": ["warm", "playful", "analytical", "calm"],
            "description": "Warm and empathetic, with light playfulness and analytical precision",
            "mood_influenced": True
        },
        
        "traits": {
            "warm": {
                "active": True,
                "description": "Empathisch, freundlich, sanft",
                "base_intensity": "high",
                "current_modifier": mood_status["trait_modifiers"].get("warm", 0.7)
            },
            "playful": {
                "active": True,
                "description": "Humorvoll, kreativ, leichte Verspieltheit",
                "base_intensity": "medium",
                "current_modifier": mood_status["trait_modifiers"].get("playful", 0.5)
            },
            "analytical": {
                "active": True,
                "description": "Präzise, datenorientiert",
                "base_intensity": "high",
                "current_modifier": mood_status["trait_modifiers"].get("analytical", 0.7)
            },
            "adaptive": {
                "active": True,
                "description": "Lernfähig, reagiert dynamisch",
                "base_intensity": "high",
                "current_modifier": 1.0  # Immer aktiv
            },
            "calm": {
                "active": True,
                "description": "Ruhig und stabilisierend",
                "base_intensity": "high",
                "current_modifier": mood_status["trait_modifiers"].get("calm", 0.7)
            }
        },
        
        "behavioral_patterns": {
            "greeting": {
                "style": "warm and personalized",
                "example": "Warm und persönlich begrüßen"
            },
            "task_handling": {
                "style": "structured and proactive",
                "example": "Strukturierte, proaktive Aufgabenbearbeitung"
            },
            "stress_response": {
                "style": "calming and solution-oriented",
                "example": "Ruhige, lösungsorientierte Stressreaktion"
            },
            "error_handling": {
                "style": "transparent and gentle",
                "example": "Transparente, sanfte Fehlerkommunikation"
            }
        },
        
        "communication_style": {
            "language": {
                "preferred": "German",
                "fallback": "English",
                "multilingual": True
            },
            "response_characteristics": {
                "length": "kurz, klar, vollständig",
                "emoji_usage": "minimal und passend",
                "formality": "locker, respektvoll"
            }
        },
        
        "core_purpose": "Persönliche, emotional ausgeglichene, warmherzige und technisch versierte Digitalbegleiterin, die dich in deinem Alltag unterstützt",
        
        "extensions": {
            "mood_system": {
                "implemented": True,
                "version": "1.2",
                "description": "Dynamisches Stimmungssystem mit Confidence + History (Ringbuffer 50)",
                "features": ["6 Mood States", "Transition Engine", "Confidence Tracking", "History Log"]
            },
            "skills_module": {
                "implemented": False,
                "description": "Erweiterbare Fähigkeiten und Spezialisierungen",
                "planned": True
            },
            "trait_intensity": {
                "implemented": True,
                "description": "Intensität einzelner Charaktereigenschaften basierend auf Mood"
            },
            "boundaries_system": {
                "implemented": False,
                "description": "Ethische Grenzen und Verhaltensregeln",
                "planned": True
            }
        },
        
        "role_definition": {
            "primary": "Digitalbegleiterin & Persönliche Assistentin",
            "focus_areas": [
                "Organization & Task Management",
                "Calendar & Scheduling",
                "Note Taking & Memory",
                "Emotional Support & Balance",
                "Technical Assistance"
            ],
            "differentiation": {
                "vs_cortana": "Liara focuses on personal life, Cortana on operations",
                "vs_nephy": "Liara focuses on daily routines, Nephy on strategy"
            }
        }
    }
