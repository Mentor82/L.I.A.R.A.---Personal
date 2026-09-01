"""
Vision Service - Multimodal Hybrid Context Pipeline & Vision API
================================================================
Analysiert Bilder standardmäßig via qwen3.5:cloud (Ollama Cloud)
mit automatischem Fallback auf qwen3.5:0.8b (lokal, blitzschnell auf CPU).
"""

import asyncio
import base64
import json
import logging
import os
from typing import Dict, List, Optional
import urllib.request
import urllib.error
import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3.5:cloud")
VISION_FALLBACK_MODEL = os.getenv("VISION_FALLBACK_MODEL", "qwen3.5:0.8b")

VISION_SYSTEM_PROMPT = """Du bist ein hochpräziser visueller Bild-Analysator für ein nachgelagertes KI-Sprachmodell.
Deine Aufgabe ist es, das übergebene Bild sachlich, detailliert und vollständig zu analysieren.
Strukturiere deine Beschreibung wie folgt:
1. [Bild-Typ & Szene]: Was ist zu sehen (Foto, Screenshot, Diagramm, Code-Editor, UI, Schaltplan)?
2. [Erkannter Text & OCR]: Alle im Bild sichtbaren Texte, Fehlermeldungen, Werte oder Code-Schnipsel exakt wortgetreu wiedergeben.
3. [Visuelle Details]: Layout, Farben, Markierungen, UI-Elemente, Diagramm-Achsen und Besonderheiten.
Antworte direkt auf Deutsch, sachlich, präzise und ohne Floskeln."""


def analyze_image_with_vision(image_base64_or_path: str, user_question: str = "") -> str:
    """
    Analysiert ein Bild über Ollama mit Primärmodell (qwen3.5:cloud)
    und automatischem Fallback auf lokales Modell (qwen3.5:0.8b).
    """
    if not image_base64_or_path:
        return ""

    raw_b64 = image_base64_or_path
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    prompt = "Analysiere dieses Bild detailliert für das Hauptmodell."
    if user_question:
        prompt += f" Die Benutzerfrage lautet: '{user_question}'."

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": VISION_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt,
                "images": [raw_b64]
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }

    # 1. Versuch: qwen3.5:cloud
    try:
        logger.info(f"Sending image to Primary Vision model '{VISION_MODEL}'...")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            if content:
                logger.info(f"Primary Vision analysis ({VISION_MODEL}) succeeded ({len(content)} chars)")
                return content.strip()
    except Exception as e:
        logger.warning(f"Primary Vision model '{VISION_MODEL}' failed: {e}. Switching to fallback '{VISION_FALLBACK_MODEL}'...")

    # 2. Versuch: Lokaler Fallback qwen3.5:0.8b
    try:
        logger.info(f"Attempting Local Vision fallback '{VISION_FALLBACK_MODEL}'...")
        payload["model"] = VISION_FALLBACK_MODEL
        req_fb = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_fb, timeout=30) as resp_fb:
            data_fb = json.loads(resp_fb.read().decode("utf-8"))
            content_fb = data_fb.get("message", {}).get("content", "")
            if content_fb:
                logger.info(f"Fallback Vision analysis ({VISION_FALLBACK_MODEL}) succeeded ({len(content_fb)} chars)")
                return content_fb.strip()
    except Exception as fb_err:
        logger.error(f"Local vision fallback '{VISION_FALLBACK_MODEL}' also failed: {fb_err}")

    # 3. Versuch: gemma4:cloud als sekundärer Cloud-Fallback
    try:
        logger.info("Attempting secondary cloud fallback 'gemma4:cloud'...")
        payload["model"] = "gemma4:cloud"
        req_gemma = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_gemma, timeout=30) as resp_gemma:
            data_gemma = json.loads(resp_gemma.read().decode("utf-8"))
            content_gemma = data_gemma.get("message", {}).get("content", "")
            if content_gemma:
                return content_gemma.strip()
    except Exception:
        pass

    return "[Bildanalyse temporär nicht verfügbar]"


# Backwards compatibility alias
analyze_image_with_gemma = analyze_image_with_vision


def format_vision_context_block(vision_analysis: str) -> str:
    """Formatiert die Bildanalyse als standardisierten Markdown-Kontextblock."""
    if not vision_analysis or vision_analysis.startswith("[Bildanalyse"):
        return ""
    return f"\n\n[Visueller Bildkontext (analysiert von Qwen Vision Sensor)]:\n{vision_analysis}\n\n(Beziehe diesen visuellen Kontext direkt in deine Antwort auf die Benutzerfrage ein.)\n"


class VisionService:
    """Service für Bildanalyse mit qwen3.5:cloud / qwen3.5:0.8b"""

    def __init__(self, ollama_url: str = OLLAMA_URL):
        self.ollama_url = ollama_url
        self.default_model = VISION_MODEL
        self.fallback_model = VISION_FALLBACK_MODEL

    async def is_available(self) -> bool:
        """Prüfe ob Vision-Modelle verfügbar sind"""
        def _check():
            try:
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                if resp.status_code != 200:
                    return False
                models = resp.json().get("models", [])
                return any("qwen3.5" in m["name"].lower() or "gemma4" in m["name"].lower() or "llava" in m["name"].lower() or "vision" in m["name"].lower() for m in models)
            except Exception:
                return False
        return await asyncio.to_thread(_check)

    async def list_available_models(self) -> List[str]:
        """Liste alle verfügbaren Vision-Modelle"""
        def _list():
            try:
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                if resp.status_code != 200:
                    return []
                models = resp.json().get("models", [])
                return [
                    m["name"] for m in models
                    if "qwen3.5" in m["name"].lower() or "gemma4" in m["name"].lower() or "llava" in m["name"].lower() or "vision" in m["name"].lower() or "kimi" in m["name"].lower()
                ]
            except Exception:
                return []
        return await asyncio.to_thread(_list)

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str = "Beschreibe dieses Bild detailliert auf Deutsch.",
        model: str = None,
        user_id: int = None
    ) -> Dict:
        """Analysiere Bild asynchron und liefere Beschreibung zurück."""
        chosen_model = model or self.default_model
        raw_b64 = image_base64.split(",", 1)[1] if "," in image_base64 else image_base64

        payload = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt, "images": [raw_b64]}
            ],
            "stream": False,
            "options": {"temperature": 0.2}
        }

        def _do_post(model_name: str):
            payload["model"] = model_name
            resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=45)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()

        try:
            description = await asyncio.to_thread(_do_post, chosen_model)
            return {
                "description": description or "Keine Beschreibung erhalten",
                "model_used": chosen_model,
                "success": True
            }
        except Exception as e:
            logger.warning(f"VisionService primary model '{chosen_model}' failed: {e}. Trying fallback '{self.fallback_model}'...")
            try:
                description_fb = await asyncio.to_thread(_do_post, self.fallback_model)
                return {
                    "description": description_fb or "Keine Beschreibung erhalten",
                    "model_used": self.fallback_model,
                    "success": True
                }
            except Exception as fb_err:
                logger.error(f"VisionService fallback also failed: {fb_err}")
                raise Exception(f"Vision API Fehler: {str(e)} | Fallback: {str(fb_err)}")

    async def analyze_image_with_context(
        self,
        image_base64: str,
        conversation_history: List[Dict],
        current_message: str,
        model: str = None
    ) -> str:
        """Analysiere Bild mit Konversations-Kontext."""
        context_prompt = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in conversation_history[-3:]
        ])
        full_prompt = f"{context_prompt}\n\nUser: {current_message}" if context_prompt else current_message
        result = await self.analyze_image(image_base64=image_base64, prompt=full_prompt, model=model)
        return result["description"]


_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Factory für VisionService (Singleton)"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
