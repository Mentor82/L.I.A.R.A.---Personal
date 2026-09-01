"""
Specialized Vision Agent für L.I.A.R.A.
======================================
Autonomer Wahrnehmungs- und Sensor-Agent für multimodale Bild- & Szenenanalyse.
Trennt strikt zwischen gesicherten optischen Fakten [VISION_FACTS] und
funktionalen Hypothesen [VISION_INTERPRETATION].
"""
import logging
from typing import Optional, Dict, Any, List

from services.agents.base_agent import BaseAgent
from services.vision_service import analyze_image_with_vision, format_vision_context_block

logger = logging.getLogger(__name__)

VISION_AGENT_SYSTEM_PROMPT = """Du bist Liaras spezialisierter autonomer Vision-Agent (Optischer Sensor- & Wahrnehmungs-Agent).
Deine Aufgabe ist es, Bilder, UI-Mockups, technische Zeichnungen, Screenshots, Diagramme und Fotos mit höchster Präzision zu untersuchen.

### Deine Kernprinzipien:
1. **Strikte Trennung von Wahrnehmung und Spekulation**:
   - `[VISION_FACTS]`: Dokumentiere nur das, was unumstößlich im Bild messbar oder lesbar ist (OCR-Texte wortgetreu, Pixelmaße, Geometrie, Layout, Farben).
   - `[VISION_INTERPRETATION]`: Formuliere plausible technische Einordnungen, Domänen (z. B. VFX-Spec, Systemarchitektur) und Use-Cases als getrennte Hypothesen.
   - `[UNCERTAINTIES]`: Benenne Unschärfen, abgeschnittene Elemente oder Mehrdeutigkeiten transparent.

2. **Hilfsbereite Aufbereitung für den Reasoning-Agenten**:
   - Bereite Daten so auf, dass nachgelagerte Reasoning-Modelle (z. B. Nemotron, Code-Agent) direkt darauf aufbauen können.
"""


class VisionAgent(BaseAgent):
    """
    Spezialisierter Vision-Agent mit Multimodal- & OCR-Toolkit.
    """

    def __init__(
        self,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        model: str = "qwen3.5:cloud",
        max_steps: int = 8
    ):
        super().__init__(
            name="VisionAgent",
            role_description="Spezialist für visuelle Wahrnehmung, 2-Stufen-Bildanalyse, OCR und technische Zeichnungen.",
            system_prompt=VISION_AGENT_SYSTEM_PROMPT,
            model=model,
            max_steps=max_steps
        )
        self.user_id = user_id
        self.session_id = session_id
        self._register_vision_tools()

    def _register_vision_tools(self):
        """Registriert alle optischen Analyse-Werkzeuge."""

        # 1. analyze_image (2-Stufen-Befund)
        self.register_tool(
            name="analyze_image",
            description="Führt eine hochpräzise 2-Stufen-Bildanalyse (VISION_FACTS + VISION_INTERPRETATION) durch.",
            parameters={
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-kodiertes Bild."
                    },
                    "question": {
                        "type": "string",
                        "description": "Optionale spezifische Frage zum Bild."
                    }
                },
                "required": ["image_base64"]
            },
            handler=self._tool_analyze_image
        )

        # 2. detect_objects (Hardware/NPU Objekterkennung)
        self.register_tool(
            name="detect_objects",
            description="Erkennt Objekte und Bounding-Boxes via Hailo NPU, EdgeTPU oder YOLO.",
            parameters={
                "type": "object",
                "properties": {
                    "image_bytes_base64": {
                        "type": "string",
                        "description": "Base64-kodierte Bilddaten."
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["hailo", "edgetpu", "cpu"],
                        "description": "Bevorzugtes Hardware-Backend."
                    },
                    "model": {
                        "type": "string",
                        "description": "Modell-ID (z. B. 'yolov8n')."
                    }
                },
                "required": ["image_bytes_base64"]
            },
            handler=self._tool_detect_objects
        )

    async def _tool_analyze_image(self, image_base64: str, question: str = "") -> Dict[str, Any]:
        """Führt 2-Stufen-Bildanalyse aus."""
        try:
            analysis = analyze_image_with_vision(image_base64, question)
            return {
                "success": True,
                "analysis": analysis,
                "formatted_block": format_vision_context_block(analysis)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _tool_detect_objects(
        self,
        image_bytes_base64: str,
        backend: str = "hailo",
        model: str = "yolov8n"
    ) -> Dict[str, Any]:
        """Führt NPU/YOLO-Objekterkennung aus."""
        try:
            import base64
            from services.vision_detection_service import get_vision_detection_service

            raw_b64 = image_bytes_base64.split(",", 1)[1] if "," in image_bytes_base64 else image_bytes_base64
            img_bytes = base64.b64decode(raw_b64)

            detection_svc = get_vision_detection_service()
            result = await detection_svc.detect_objects(
                image_bytes=img_bytes,
                backend=backend,
                model=model
            )
            return {"success": True, "detections": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
