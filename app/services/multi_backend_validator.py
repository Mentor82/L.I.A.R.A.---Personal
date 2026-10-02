"""
AI Validator Service - Multi-Backend with Fallback
Primär: LiNeP-Cluster (Trunk, "task:judge" - Personal#29 B5)
Fallback: liara (192.168.178.50:11434, lokales Ollama)

liara-core (192.168.178.60) existiert nicht mehr und wird nicht mehr angefragt.
Bewertungen laufen ueber task:judge, das per distinct_from nie ein Modell von
task:reason nimmt: wer erzeugt, bewertet sich nicht selbst. Die Syntax-Pruefung
(AI-Validator auf .150) ist davon unberuehrt.
"""

import httpx
import logging
from typing import Optional, Dict, List, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import asyncio

from core.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Primary Validator: LiNeP cluster trunk (host/port come from core.config)
JUDGE_TASK = "task:judge"
LOCAL_JUDGE_MODEL = "llama3.2:3b"  # Notfall-Modell auf liara (CPU: mistral:7b braucht dort ~85 s Kaltstart)

# Fallback Validator (liara)
FALLBACK_VALIDATOR_HOST = "192.168.178.50"
FALLBACK_VALIDATOR_PORT = 11434
FALLBACK_VALIDATOR_URL = f"http://{FALLBACK_VALIDATOR_HOST}:{FALLBACK_VALIDATOR_PORT}"

# Syntax Validation (AI-Validator REST API)
SYNTAX_VALIDATOR_HOST = "192.168.178.150"
SYNTAX_VALIDATOR_PORT = 5000
SYNTAX_VALIDATOR_URL = f"http://{SYNTAX_VALIDATOR_HOST}:{SYNTAX_VALIDATOR_PORT}"

# Timeout für Modell-Inference: 2 Minuten (120s) da Text-Generierung lange dauert
VALIDATOR_TIMEOUT = 120.0

# Supported Languages
SUPPORTED_LANGUAGES = [
    "python", "javascript", "typescript", "bash", "shell", "sh",
    "json", "yaml", "yml", "c", "cpp", "c++", "go", "golang",
    "rust", "rs", "php", "ruby", "rb", "sql", "html", "css", "java"
]

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ValidationError(BaseModel):
    """Validation error/warning"""
    tool: Optional[str] = None
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # error, warning, info

class ValidationResult(BaseModel):
    """Code validation result"""
    language: str
    status: str  # ok, warning, error
    timestamp: datetime
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    file: Optional[str] = None
    latency_ms: Optional[float] = None
    backend: Optional[str] = None  # Which backend was used

# ============================================================================
# MULTI-BACKEND VALIDATOR SERVICE
# ============================================================================

class MultiBackendValidatorService:
    """Service for remote code validation with automatic fallback"""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.primary_healthy = False
        self.fallback_healthy = False
        self._last_primary_check = None
        self._last_fallback_check = None
    
    async def initialize(self):
        """Initialize async HTTP client"""
        self.client = httpx.AsyncClient(timeout=VALIDATOR_TIMEOUT)
        await self._check_backends()
    
    async def shutdown(self):
        """Shutdown async HTTP client"""
        if self.client:
            await self.client.aclose()
    
    async def _check_backends(self):
        """Check health of both backends"""
        if not self.client:
            self.client = httpx.AsyncClient(timeout=VALIDATOR_TIMEOUT)
        
        # Check primary (LiNeP cluster)
        try:
            from services.cluster_info import get_cluster_info
            cluster = await asyncio.to_thread(get_cluster_info)
            self.primary_healthy = bool(cluster and cluster["available"] and JUDGE_TASK in cluster["tasks"])
            logger.info(f"🟢 Primary Backend (LiNeP cluster): {'✅ Healthy' if self.primary_healthy else '❌ Unhealthy/not configured'}")
        except Exception as e:
            self.primary_healthy = False
            logger.warning(f"🔴 Primary Backend (LiNeP cluster) error: {str(e)}")
        
        # Check fallback (liara)
        try:
            response = await self.client.get(f"{FALLBACK_VALIDATOR_URL}/api/tags", timeout=10)
            self.fallback_healthy = response.status_code == 200
            logger.info(f"🟡 Fallback Backend (liara): {'✅ Healthy' if self.fallback_healthy else '❌ Unhealthy'}")
        except Exception as e:
            self.fallback_healthy = False
            logger.warning(f"🟠 Fallback Backend (liara) error: {str(e)}")
    
    async def _get_active_backend(self) -> Tuple[str, str]:
        """Get active backend URL and name"""
        if self.primary_healthy:
            return "cluster", "LiNeP cluster (primary)"
        elif self.fallback_healthy:
            logger.warning("⚠️ Primary backend unavailable, using fallback (liara)")
            return FALLBACK_VALIDATOR_URL, "liara (fallback)"
        else:
            # Try to reach primary even if last check failed
            raise Exception("❌ No validation backend available!")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends"""
        if not self.client:
            await self.initialize()
        else:
            await self._check_backends()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "primary": {
                "name": "LiNeP cluster (task:judge)",
                "host": settings.linep_trunk_host or None,
                "port": settings.linep_trunk_port if settings.linep_trunk_host else None,
                "status": "healthy" if self.primary_healthy else "unhealthy"
            },
            "fallback": {
                "name": "liara",
                "host": FALLBACK_VALIDATOR_HOST,
                "port": FALLBACK_VALIDATOR_PORT,
                "status": "healthy" if self.fallback_healthy else "unhealthy"
            },
            "active": "primary" if self.primary_healthy else ("fallback" if self.fallback_healthy else "none")
        }
    
    async def validate_syntax(
        self,
        code: str,
        language: str
    ) -> Dict[str, Any]:
        """Validate code syntax via AI-Validator (REST API for syntax checking)"""
        try:
            if not self.client:
                await self.initialize()
            
            endpoint = f"{SYNTAX_VALIDATOR_URL}/validate/{language}"
            
            response = await self.client.post(
                endpoint,
                json={"code": code},
                timeout=VALIDATOR_TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            result["backend"] = "ai-validator (syntax)"
            
            logger.info(f"✅ Syntax validation for {language} via AI-Validator")
            return result
        except Exception as e:
            logger.error(f"Syntax validation failed: {str(e)}")
            return {
                "language": language,
                "status": "error",
                "message": str(e),
                "backend": "ai-validator (syntax)"
            }
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available models from active backend"""
        try:
            if not self.client:
                await self.initialize()
            
            backend_url, backend_name = await self._get_active_backend()
            if backend_url == "cluster":
                from services.cluster_info import get_cluster_info
                cluster = await asyncio.to_thread(get_cluster_info)
                models = [{"name": n} for n in (cluster["tasks"] + cluster["models"])] if cluster else []
                logger.info(f"📦 Retrieved {len(models)} models/tasks from {backend_name}")
                return models

            response = await self.client.get(
                f"{backend_url}/api/tags",
                timeout=VALIDATOR_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            logger.info(f"📦 Retrieved {len(models)} models from {backend_name}")
            return models
        except Exception as e:
            logger.error(f"Failed to get models: {str(e)}")
            return []
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate text using active backend. Without an explicit model the
        cluster grades via task:judge (never a task:reason model)."""
        try:
            if not self.client:
                await self.initialize()
            
            backend_url, backend_name = await self._get_active_backend()
            if backend_url == "cluster":
                target = model or JUDGE_TASK
                try:
                    from services.linep_provider import get_linep_provider
                    text = await asyncio.to_thread(
                        get_linep_provider().chat_sync, target,
                        [{"role": "user", "content": prompt}], 2000, 0.2,
                    )
                    logger.info(f"✅ Generated text using {target} on {backend_name}")
                    return {"model": target, "response": text, "done": True, "backend": backend_name}
                except Exception as e:
                    logger.warning(f"Cluster-Bewertung fehlgeschlagen ({e}) - Fallback auf liara")
                    if not self.fallback_healthy:
                        raise
                    backend_url, backend_name = FALLBACK_VALIDATOR_URL, "liara (fallback)"
            if model is None or model.startswith("task:"):
                model = LOCAL_JUDGE_MODEL
            print(f"[DEBUG] 🔍 Generating text with {model} on {backend_name} ({backend_url})")
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            print(f"[DEBUG] Making request to {backend_url}/api/generate")
            response = await self.client.post(
                f"{backend_url}/api/generate",
                json=payload,
                timeout=VALIDATOR_TIMEOUT
            )
            print(f"[DEBUG] Response status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            result["backend"] = backend_name
            
            logger.info(f"✅ Generated text using {model} on {backend_name}")
            print(f"[DEBUG] ✅ Text generation successful")
            return result
        except httpx.TimeoutException as e:
            error_str = f"Timeout after {VALIDATOR_TIMEOUT}s: {str(e)}"
            logger.error(f"Text generation timeout: {error_str}")
            print(f"[DEBUG] ❌ Timeout error: {error_str}")
            return {"status": "error", "message": error_str, "backend": "unknown"}
        except Exception as e:
            error_str = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Text generation failed: {error_str}")
            print(f"[DEBUG] ❌ Text generation error: {error_str}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": error_str, "backend": "unknown"}


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_validator_instance: Optional[MultiBackendValidatorService] = None

async def get_validator() -> MultiBackendValidatorService:
    """Get or create validator singleton"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = MultiBackendValidatorService()
        await _validator_instance.initialize()
    return _validator_instance
