"""
Chat Extensions für Hailo-8L Integration
Erweitert chat.py um Vision-Anfragen, Auto-Fallback und Backend-Selection
"""

import logging
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
import asyncio

from services.hailo_service import get_hailo_service, HailoService
from services.backend_router import get_backend_router, BackendType, BackendRouter

logger = logging.getLogger(__name__)


class ChatRequestWithBackend(BaseModel):
    """Extended chat request with backend selection"""
    message: str
    model: Optional[str] = None
    use_accelerator: Optional[str] = None  # "hailo", "gpu", "auto", "cpu"
    attachments: Optional[List[Dict[str, Any]]] = None
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 2048


class BackendSelectionResult(BaseModel):
    """Result of backend selection"""
    selected_backend: str
    fallback_chain: List[str]
    rationale: str
    expected_latency_ms: float
    power_consumption_w: float


async def detect_vision_request(
    message: str,
    attachments: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Detect if request needs vision processing
    
    Args:
        message: User message
        attachments: Attached images/files
    
    Returns:
        True if vision processing needed
    """
    # Has image attachments
    if attachments:
        for att in attachments:
            if att.get("type") in ["image", "image/jpeg", "image/png"]:
                return True
    
    # Vision keywords in message
    vision_keywords = [
        "bild", "foto", "image", "picture", "describe", "analyse",
        "analyze", "sehe", "siehst", "zeig", "erkenne", "identify",
        "objekt", "object", "person", "scene", "what is", "what's",
        "visual", "looks", "appearance", "schau", "guck"
    ]
    message_lower = message.lower()
    
    return any(keyword in message_lower for keyword in vision_keywords)


async def select_backend_for_request(
    message: str,
    attachments: Optional[List[Dict[str, Any]]] = None,
    user_preferred_backend: Optional[str] = None,
    allow_fallback: bool = True
) -> tuple[BackendType, BackendSelectionResult]:
    """
    Intelligently select backend based on request characteristics
    
    Args:
        message: User message
        attachments: Attachments (images, files)
        user_preferred_backend: User's preference ("hailo", "gpu", "local", "cpu")
        allow_fallback: Allow fallback to other backends
    
    Returns:
        (selected_backend, selection_result)
    """
    router = get_backend_router()
    
    # Determine use case
    is_vision = await detect_vision_request(message, attachments)
    
    if is_vision:
        use_case = "vision"
        preferred = BackendType.HAILO
    else:
        use_case = "chat"
        preferred = BackendType.VLMM if user_preferred_backend != "cpu" else BackendType.LLAMA_CPP
    
    # Override with user preference
    backend_map = {
        "hailo": BackendType.HAILO,
        "gpu": BackendType.VLMM,
        "local": BackendType.OLLAMA,
        "cpu": BackendType.LLAMA_CPP,
        "auto": None,  # Auto-select
    }
    
    if user_preferred_backend and user_preferred_backend in backend_map:
        pref = backend_map[user_preferred_backend]
        if pref:
            preferred = pref
    
    # Select backend
    selected = await router.select_backend(
        use_case=use_case,
        preferred_backend=preferred,
        allow_fallback=allow_fallback
    )
    
    # Build fallback chain for logging
    chains = {
        "vision": ["hailo", "ollama", "llama_cpp"],
        "chat": ["vllm", "ollama", "llama_cpp"],
    }
    fallback_chain = chains.get(use_case, chains["chat"])
    
    # Get capability info
    capability = router.capabilities[selected]
    
    result = BackendSelectionResult(
        selected_backend=selected.value,
        fallback_chain=fallback_chain,
        rationale=f"Selected {selected.value} for {use_case} (vision={is_vision})",
        expected_latency_ms=capability.typical_latency_ms,
        power_consumption_w=capability.power_consumption_w
    )
    
    logger.info(f"Backend selection: {result.selected_backend} - {result.rationale}")
    
    return selected, result


async def run_vision_inference_on_hailo(
    image_data: bytes,
    image_type: str = "image/jpeg",
    model: str = "vision_model"
) -> Dict[str, Any]:
    """
    Run vision inference on Hailo-8L
    
    Args:
        image_data: Raw image bytes
        image_type: MIME type (image/jpeg, image/png)
        model: Vision model to use
    
    Returns:
        Inference result with classifications/detections
    """
    hailo: HailoService = get_hailo_service()
    
    if not hailo.is_available():
        logger.warning("Hailo not available, vision inference will fall back to Ollama")
        return {"error": "Hailo not available", "fallback": "ollama"}
    
    try:
        # Prepare input
        input_data = {
            "image": image_data,
            "image_type": image_type,
        }
        
        # Run inference
        result = await hailo.run_inference(model, input_data, stream=False)
        return result
    
    except Exception as e:
        logger.error(f"Hailo vision inference failed: {e}")
        return {"error": str(e), "fallback": "ollama"}


async def build_fallback_message(
    original_error: str,
    failed_backend: BackendType,
    fallback_backend: BackendType
) -> str:
    """
    Create user-friendly message about backend fallback
    """
    return (
        f"⚠️ {failed_backend.value} war leider nicht verfügbar ({original_error}). "
        f"Ich verwende stattdessen {fallback_backend.value}. Die Antwort könnte etwas langsamer sein."
    )


async def get_chat_backend_status() -> Dict[str, Any]:
    """
    Get status of all chat backends for dashboard
    """
    router = get_backend_router()
    hailo = get_hailo_service()
    
    status = await router.get_backend_status()
    
    return {
        "backends": status,
        "hailo_device": {
            "available": hailo.is_available(),
            "device_id": hailo.device.device_id if hailo.device else None,
            "temperature": hailo.device.temperature if hailo.device else 0,
            "power_w": hailo.device.power_consumption_w if hailo.device else 0,
        },
        "recommendation": await build_recommendation(status)
    }


async def build_recommendation(status: Dict[str, Dict]) -> str:
    """
    Build user recommendation based on backend availability
    """
    healthy_count = sum(1 for s in status.values() if s["healthy"])
    
    if healthy_count == 0:
        return "⚠️ Alle Backend sind offline. Bitte versuche es später erneut."
    
    # Recommend most efficient
    if status.get("hailo", {}).get("healthy"):
        return "✅ Hailo-8L ist verfügbar - sehr effizient und schnell!"
    elif status.get("vllm", {}).get("healthy"):
        return "✅ GPU Backend verfügbar - gute Balance aus Qualität und Geschwindigkeit"
    elif status.get("ollama", {}).get("healthy"):
        return "✅ Lokales Backend verfügbar - stabil und zuverlässig"
    else:
        return "✅ CPU Backend verfügbar - langsamer aber funktionsfähig"


class HailoChatIntegration:
    """
    Helper class for integrating Hailo into chat workflow
    """
    
    def __init__(self):
        self.hailo = get_hailo_service()
        self.router = get_backend_router()
    
    async def should_use_hailo(self, message: str, attachments: Optional[List[Dict]] = None) -> bool:
        """Determine if Hailo should be used for this request"""
        # Check if request is vision-related
        is_vision = await detect_vision_request(message, attachments)
        
        # Check if Hailo is healthy
        is_hailo_available = await self.hailo.health_check()
        
        return is_vision and is_hailo_available
    
    async def process_with_fallback(
        self,
        message: str,
        attachments: Optional[List[Dict]] = None,
        primary_backend: Optional[BackendType] = None,
        process_fn=None
    ) -> Dict[str, Any]:
        """
        Process message with fallback to alternative backends
        
        Args:
            message: User message
            attachments: Attachments
            primary_backend: Primary backend to try
            process_fn: Async function to process with selected backend
        
        Returns:
            Result or fallback result
        """
        # Select backend
        selected, selection_info = await select_backend_for_request(
            message, attachments, str(primary_backend) if primary_backend else None
        )
        
        try:
            # Try primary backend
            if process_fn:
                result = await process_fn(selected)
                return {
                    "result": result,
                    "backend": selected.value,
                    "selection": selection_info.dict(),
                    "fallback": False
                }
        except Exception as e:
            logger.warning(f"Primary backend {selected.value} failed: {e}")
            
            # Fallback to next available
            healthy = await self.router.get_healthy_backends()
            healthy = [b for b in healthy if b != selected]
            
            if healthy and process_fn:
                fallback = healthy[0]
                try:
                    result = await process_fn(fallback)
                    fallback_msg = await build_fallback_message(str(e), selected, fallback)
                    
                    return {
                        "result": result,
                        "backend": fallback.value,
                        "selection": selection_info.dict(),
                        "fallback": True,
                        "fallback_message": fallback_msg,
                        "fallback_reason": str(e)
                    }
                except Exception as e2:
                    logger.error(f"Fallback to {fallback.value} also failed: {e2}")
                    raise RuntimeError(f"All backends failed: {e2}")
            else:
                raise
