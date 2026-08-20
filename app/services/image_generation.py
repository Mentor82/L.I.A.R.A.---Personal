"""
Image Generation Service - Lokale Stable Diffusion Integration

Unterstützt:
- AUTOMATIC1111 Stable Diffusion WebUI (lokal)
- Stable Diffusion 1.5 / SDXL
- Privacy-First: Alle Daten bleiben auf dem Server
"""
import os
import httpx
import asyncio
import base64
from typing import Optional, Dict, Literal
from datetime import datetime
from pathlib import Path


class ImageGenerationService:
    """
    Service für lokale AI-Bild-Generierung mit Stable Diffusion.
    
    Features:
    - AUTOMATIC1111 WebUI API (http://localhost:7860)
    - Privacy-First: Alle Daten lokal
    - Base64 + File Output
    - Prompt-Optimierung
    """
    
    def __init__(self):
        self.sd_webui_url = os.getenv("SD_WEBUI_URL", "http://localhost:7860")
        self.output_dir = Path(os.getenv("SD_OUTPUT_DIR", "/opt/liara/app/generated_images"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Prüft ob Stable Diffusion WebUI erreichbar ist."""
        try:
            import requests
            response = requests.get(f"{self.sd_webui_url}/sdapi/v1/sd-models", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def is_enabled(self) -> bool:
        """Prüft ob Image Generation verfügbar ist."""
        return self.enabled
    
    async def generate_image(
        self, 
        prompt: str,
        negative_prompt: str = "ugly, blurry, low quality, distorted, deformed",
        width: int = 512,
        height: int = 512,
        num_steps: int = 15,  # Reduziert für CPU-Performance
        guidance_scale: float = 7.5,
        sampler: str = "Euler a"
    ) -> Dict:
        """
        Generiert Bild mit lokalem Stable Diffusion.
        
        Args:
            prompt: Beschreibung des gewünschten Bildes
            negative_prompt: Was NICHT im Bild sein soll
            width: Bildbreite (Standard: 512, max 1024)
            height: Bildhöhe (Standard: 512, max 1024)
            num_steps: Anzahl Diffusion-Steps (20-50 empfohlen)
            guidance_scale: CFG Scale (7-12 empfohlen)
            sampler: Sampler-Name (Euler a, DPM++ 2M Karras, etc.)
            
        Returns:
            {
                "success": bool,
                "image_path": str,  # Lokaler Pfad
                "image_url": str,   # Web-URL
                "image_base64": str,  # Base64 für direktes Rendering
                "prompt": str,
                "model": str,
                "generation_time": float,
                "error": Optional[str]
            }
        """
        if not self.enabled:
            return {
                "status": "error",
                "error": "Image generation is disabled",
                "image_path": None,
                "image_base64": None,
                "prompt": prompt,
                "model": "none",
                "generation_time": 0.0
            }
        
        start_time = datetime.now()
        
        try:
            # Stable Diffusion WebUI API Request
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": num_steps,
                "cfg_scale": guidance_scale,
                "width": width,
                "height": height,
                "sampler_name": sampler,
                "batch_size": 1,
                "n_iter": 1,
                "save_images": True
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.sd_webui_url}/sdapi/v1/txt2img",
                    json=payload
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"SD WebUI Error: {response.status_code} - {response.text}"
                    }
                
                result = response.json()
                
                # Extrahiere erstes Bild (Base64)
                if not result.get("images"):
                    return {
                        "success": False,
                        "error": "No image generated"
                    }
                
                image_base64 = result["images"][0]
                
                # Speichere Bild lokal
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"liara_{timestamp}.png"
                filepath = self.output_dir / filename
                
                # Decode Base64 und speichere
                image_data = base64.b64decode(image_base64)
                filepath.write_bytes(image_data)
                
                generation_time = (datetime.now() - start_time).total_seconds()
                
                # Web-URL für Frontend
                image_url = f"/api/images/{filename}"
                
                return {
                    "success": True,
                    "image_path": str(filepath),
                    "image_url": image_url,
                    "image_base64": f"data:image/png;base64,{image_base64}",
                    "prompt": prompt,
                    "model": "Stable Diffusion (local)",
                    "generation_time": generation_time,
                    "width": width,
                    "height": height
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Image generation error: {str(e)}"
            }
    
    def optimize_prompt(self, user_prompt: str) -> str:
        """
        Optimiert User-Prompt für bessere Stable Diffusion Ergebnisse.
        
        Fügt hinzu:
        - Qualitäts-Keywords
        - Stil-Hints
        - Detail-Verbesserungen
        """
        # Basis-Qualität
        quality_tags = "highly detailed, professional, 8k uhd, sharp focus"
        
        # Prüfe auf bestimmte Keywords
        prompt_lower = user_prompt.lower()
        
        # Fotorealistisch?
        if any(word in prompt_lower for word in ["foto", "realistic", "real", "photograph"]):
            return f"{user_prompt}, {quality_tags}, photorealistic, studio lighting"
        
        # Künstlerisch/Fantasy?
        if any(word in prompt_lower for word in ["fantasy", "magie", "magic", "kunst", "art"]):
            return f"{user_prompt}, {quality_tags}, artstation, concept art, elegant"
        
        # Mechanisch/Tech?
        if any(word in prompt_lower for word in ["mechanisch", "robot", "machine", "tech"]):
            return f"{user_prompt}, {quality_tags}, industrial design, intricate mechanisms"
        
        # Default
        return f"{user_prompt}, {quality_tags}"


# Singleton Instance
_image_generation_service = None

def get_image_generation_service() -> ImageGenerationService:
    """Singleton Accessor für Image Generation Service."""
    global _image_generation_service
    if _image_generation_service is None:
        _image_generation_service = ImageGenerationService()
    return _image_generation_service
