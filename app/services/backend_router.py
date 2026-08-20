"""
Backend Router Service - Intelligente Auswahl zwischen vLLM, Ollama, Hailo, llama.cpp
Implementiert auto-fallback bei Backend-Ausfällen
"""

import logging
from typing import Optional, Dict, List, Literal
from dataclasses import dataclass
from enum import Enum
import asyncio
import requests

logger = logging.getLogger(__name__)


class BackendType(str, Enum):
    """Verfügbare LLM/Inference Backends"""
    HAILO = "hailo"
    VLMM = "vllm"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"


@dataclass
class BackendHealth:
    """Health status of a backend"""
    backend: BackendType
    is_healthy: bool
    latency_ms: float
    error_message: Optional[str] = None


@dataclass
class BackendCapability:
    """What a backend can do"""
    backend: BackendType
    supports_vision: bool
    supports_streaming: bool
    supports_functions: bool
    max_concurrent_requests: int
    typical_latency_ms: float
    power_consumption_w: float


class BackendRouter:
    """
    Intelligente Auswahl von Inference-Backends mit Auto-Fallback.
    
    Fallback-Kette:
    1. Hailo-8L (Vision, super-efficient)
    2. vLLM (GPU, schnell für LLM)
    3. Ollama (lokal, flexibel)
    4. llama.cpp (CPU-only fallback)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Backend endpoints
        self.hailo_url = "http://localhost:8000"
        self.vllm_url = "http://localhost:8000"
        self.ollama_url = "http://localhost:11434"
        self.llama_cpp_url = "http://localhost:8080"
        
        # Health cache (update every 30s)
        self.health_cache: Dict[BackendType, BackendHealth] = {}
        self.last_health_check = 0
        
        # Capabilities
        self.capabilities = {
            BackendType.HAILO: BackendCapability(
                backend=BackendType.HAILO,
                supports_vision=True,
                supports_streaming=False,
                supports_functions=False,
                max_concurrent_requests=1,
                typical_latency_ms=5,
                power_consumption_w=6.0
            ),
            BackendType.VLMM: BackendCapability(
                backend=BackendType.VLMM,
                supports_vision=False,
                supports_streaming=True,
                supports_functions=True,
                max_concurrent_requests=10,
                typical_latency_ms=50,
                power_consumption_w=150.0
            ),
            BackendType.OLLAMA: BackendCapability(
                backend=BackendType.OLLAMA,
                supports_vision=False,
                supports_streaming=True,
                supports_functions=False,
                max_concurrent_requests=5,
                typical_latency_ms=100,
                power_consumption_w=20.0
            ),
            BackendType.LLAMA_CPP: BackendCapability(
                backend=BackendType.LLAMA_CPP,
                supports_vision=False,
                supports_streaming=True,
                supports_functions=False,
                max_concurrent_requests=2,
                typical_latency_ms=500,
                power_consumption_w=10.0
            ),
        }
    
    async def health_check(self, backend: BackendType) -> BackendHealth:
        """Check if backend is healthy"""
        try:
            if backend == BackendType.HAILO:
                response = await self._check_hailo()
            elif backend == BackendType.VLMM:
                response = await self._check_vllm()
            elif backend == BackendType.OLLAMA:
                response = await self._check_ollama()
            elif backend == BackendType.LLAMA_CPP:
                response = await self._check_llama_cpp()
            else:
                response = BackendHealth(backend, False, 0, "Unknown backend")
            
            return response
        except Exception as e:
            logger.error(f"Health check failed for {backend}: {e}")
            return BackendHealth(backend, False, 0, str(e))
    
    async def _check_hailo(self) -> BackendHealth:
        """Check Hailo health"""
        try:
            response = requests.get(
                f"{self.hailo_url}/hailo/health",
                timeout=2
            )
            is_healthy = response.status_code == 200
            return BackendHealth(
                BackendType.HAILO,
                is_healthy,
                response.elapsed.total_seconds() * 1000 if is_healthy else 0
            )
        except Exception as e:
            return BackendHealth(BackendType.HAILO, False, 0, str(e))
    
    async def _check_vllm(self) -> BackendHealth:
        """Check vLLM health"""
        try:
            response = requests.get(
                f"{self.vllm_url}/health",
                timeout=2
            )
            is_healthy = response.status_code == 200
            return BackendHealth(
                BackendType.VLMM,
                is_healthy,
                response.elapsed.total_seconds() * 1000 if is_healthy else 0
            )
        except Exception as e:
            return BackendHealth(BackendType.VLMM, False, 0, str(e))
    
    async def _check_ollama(self) -> BackendHealth:
        """Check Ollama health"""
        try:
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=2
            )
            is_healthy = response.status_code == 200
            return BackendHealth(
                BackendType.OLLAMA,
                is_healthy,
                response.elapsed.total_seconds() * 1000 if is_healthy else 0
            )
        except Exception as e:
            return BackendHealth(BackendType.OLLAMA, False, 0, str(e))
    
    async def _check_llama_cpp(self) -> BackendHealth:
        """Check llama.cpp health"""
        try:
            response = requests.get(
                f"{self.llama_cpp_url}/health",
                timeout=2
            )
            is_healthy = response.status_code == 200
            return BackendHealth(
                BackendType.LLAMA_CPP,
                is_healthy,
                response.elapsed.total_seconds() * 1000 if is_healthy else 0
            )
        except Exception as e:
            return BackendHealth(BackendType.LLAMA_CPP, False, 0, str(e))
    
    async def select_backend(
        self,
        use_case: Literal["chat", "vision", "code", "reasoning"] = "chat",
        preferred_backend: Optional[BackendType] = None,
        allow_fallback: bool = True
    ) -> BackendType:
        """
        Select best backend for given use case with auto-fallback
        
        Args:
            use_case: Type of inference needed
            preferred_backend: User's preference (will try first)
            allow_fallback: Fall back to other backends if preferred unavailable
        
        Returns:
            Selected backend
        """
        # Define fallback chains
        fallback_chains = {
            "vision": [BackendType.HAILO, BackendType.OLLAMA, BackendType.LLAMA_CPP],
            "chat": [BackendType.VLMM, BackendType.OLLAMA, BackendType.LLAMA_CPP],
            "code": [BackendType.VLMM, BackendType.OLLAMA, BackendType.LLAMA_CPP],
            "reasoning": [BackendType.VLMM, BackendType.OLLAMA, BackendType.LLAMA_CPP],
        }
        
        chain = fallback_chains.get(use_case, fallback_chains["chat"])
        
        # If preferred backend specified, try it first
        if preferred_backend:
            chain = [preferred_backend] + [b for b in chain if b != preferred_backend]
        
        # Test each backend in fallback chain
        for backend in chain:
            health = await self.health_check(backend)
            if health.is_healthy:
                logger.info(f"Selected backend: {backend.value}")
                return backend
        
        # If no backend healthy and fallback disabled, raise error
        if not allow_fallback:
            raise RuntimeError("No healthy backend available and fallback disabled")
        
        # Last resort: return first in chain (might fail, but let client handle)
        logger.warning(f"No healthy backend found, defaulting to {chain[0].value}")
        return chain[0]
    
    async def get_healthy_backends(self) -> List[BackendType]:
        """Get list of all healthy backends"""
        healthy = []
        for backend in BackendType:
            health = await self.health_check(backend)
            if health.is_healthy:
                healthy.append(backend)
        return healthy
    
    async def get_backend_status(self) -> Dict[str, Dict]:
        """Get status of all backends"""
        status = {}
        for backend in BackendType:
            health = await self.health_check(backend)
            capability = self.capabilities[backend]
            
            status[backend.value] = {
                "healthy": health.is_healthy,
                "latency_ms": health.latency_ms,
                "error": health.error_message,
                "capabilities": {
                    "vision": capability.supports_vision,
                    "streaming": capability.supports_streaming,
                    "functions": capability.supports_functions,
                    "max_concurrent": capability.max_concurrent_requests,
                    "power_w": capability.power_consumption_w,
                },
            }
        
        return status
    
    def get_capability(self, backend: BackendType, feature: str) -> bool:
        """Check if backend supports a feature"""
        cap = self.capabilities.get(backend)
        if not cap:
            return False
        
        return getattr(cap, f"supports_{feature}", False)
    
    def get_typical_latency(self, backend: BackendType) -> float:
        """Get typical latency for backend in milliseconds"""
        cap = self.capabilities.get(backend)
        return cap.typical_latency_ms if cap else 1000
    
    def get_power_consumption(self, backend: BackendType) -> float:
        """Get power consumption in watts"""
        cap = self.capabilities.get(backend)
        return cap.power_consumption_w if cap else 100.0


def get_backend_router() -> BackendRouter:
    """Dependency injection for BackendRouter (singleton)"""
    return BackendRouter()
