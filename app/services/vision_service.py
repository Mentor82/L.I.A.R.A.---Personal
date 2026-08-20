"""
🖼️ Vision Service - LLaVA Integration
Multimodale Bildanalyse mit Ollama LLaVA
"""

import requests
import base64
from typing import Dict, List, Optional
import asyncio


class VisionService:
    """Service für Bildanalyse mit LLaVA"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.default_model = "llava:7b"
    
    async def is_available(self) -> bool:
        """Prüfe ob LLaVA verfügbar ist"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code != 200:
                return False
            
            models = response.json().get('models', [])
            return any('llava' in m['name'].lower() for m in models)
        except:
            return False
    
    async def list_available_models(self) -> List[str]:
        """Liste alle verfügbaren Vision-Modelle"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code != 200:
                return []
            
            models = response.json().get('models', [])
            vision_models = [
                m['name'] for m in models 
                if 'llava' in m['name'].lower() or 'vision' in m['name'].lower()
            ]
            return vision_models
        except:
            return []
    
    async def analyze_image(
        self,
        image_base64: str,
        prompt: str = "Beschreibe dieses Bild detailliert auf Deutsch.",
        model: str = None,
        user_id: int = None
    ) -> Dict:
        """
        Analysiere Bild mit LLaVA
        
        Args:
            image_base64: Base64-kodiertes Bild
            prompt: Analyseaufforderung
            model: Optional spezifisches Modell (default: llava:7b)
            user_id: Optional User ID für Logging
            
        Returns:
            {
                'description': str,
                'model_used': str,
                'success': bool
            }
        """
        model = model or self.default_model
        
        # Stelle sicher, dass LLaVA verfügbar ist
        if not await self.is_available():
            raise Exception(
                "LLaVA nicht verfügbar. Bitte installiere: ollama pull llava:7b"
            )
        
        # LLaVA API Call
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500  # Max. Tokens für Beschreibung
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60  # Vision kann länger dauern
            )
            response.raise_for_status()
            
            result = response.json()
            description = result.get('response', '').strip()
            
            if not description:
                raise Exception("LLaVA hat keine Beschreibung generiert")
            
            return {
                'description': description,
                'model_used': model,
                'success': True
            }
            
        except requests.exceptions.Timeout:
            raise Exception("Bildanalyse-Timeout (> 60s)")
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLaVA API Fehler: {str(e)}")
    
    async def analyze_image_with_context(
        self,
        image_base64: str,
        conversation_history: List[Dict],
        current_message: str,
        model: str = None
    ) -> str:
        """
        Analysiere Bild mit Konversations-Kontext
        
        Für Multi-Turn Chat mit Bildern
        """
        model = model or self.default_model
        
        # Baue Prompt mit Kontext
        context_prompt = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history[-3:]  # Letzte 3 Nachrichten
        ])
        
        full_prompt = f"{context_prompt}\n\nUser: {current_message}"
        
        result = await self.analyze_image(
            image_base64=image_base64,
            prompt=full_prompt,
            model=model
        )
        
        return result['description']


# Singleton Instance
_vision_service: Optional[VisionService] = None


def get_vision_service() -> VisionService:
    """Factory für VisionService (Singleton)"""
    global _vision_service
    
    if _vision_service is None:
        _vision_service = VisionService()
    
    return _vision_service
