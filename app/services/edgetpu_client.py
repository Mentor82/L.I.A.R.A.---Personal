"""
Edge TPU REST API Client

Service for communicating with the edge TPU inference server on edge01
(Coral USB Accelerator via Proxmox USB-Passthrough, 192.168.178.155:5001).
Mirrors the structure of hailo_rpi5_client.py so both accelerator backends
can be swapped through the same VisionDetectionService interface.
"""

import httpx
import base64
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
EDGETPU_API_URL = "http://192.168.178.155:5001"
EDGETPU_HEALTH_TIMEOUT = 5.0  # seconds
EDGETPU_INFERENCE_TIMEOUT = 15.0  # seconds


class EdgeTpuStatus(Enum):
    """Edge TPU API availability status"""
    HEALTHY = "healthy"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class EdgeTpuClient:
    """
    Client for communicating with the edge01 Edge TPU inference server.

    Handles:
    - Health checking
    - Model listing
    - Inference requests (object detection via SSD MobileDet)
    """

    def __init__(self):
        self.api_url = EDGETPU_API_URL
        self.status = EdgeTpuStatus.OFFLINE
        self.last_health_check = None
        self.models: List[str] = []
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Initialize client and run an initial health check"""
        self._client = httpx.AsyncClient(timeout=EDGETPU_HEALTH_TIMEOUT)
        await self.health_check()
        logger.info(f"Edge TPU client initialized: {self.status.value}")

    async def shutdown(self):
        """Cleanup resources"""
        if self._client:
            await self._client.aclose()
            logger.info("Edge TPU client shutdown")

    async def health_check(self) -> bool:
        """
        Check if the edge01 Edge TPU API is healthy

        Returns:
            True if API is reachable and responsive
        """
        if not self._client:
            self.status = EdgeTpuStatus.OFFLINE
            return False

        try:
            response = await self._client.get(
                f"{self.api_url}/health",
                timeout=EDGETPU_HEALTH_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                self.status = (
                    EdgeTpuStatus.HEALTHY
                    if data.get("status") == "healthy"
                    else EdgeTpuStatus.DEGRADED
                )
                self.last_health_check = datetime.now()
                self.models = data.get("models", [])
                logger.debug(f"edge01 health check OK: {len(self.models)} models available")
                return self.status == EdgeTpuStatus.HEALTHY
            else:
                self.status = EdgeTpuStatus.DEGRADED
                logger.warning(f"edge01 health check returned {response.status_code}")
                return False

        except Exception as e:
            self.status = EdgeTpuStatus.OFFLINE
            logger.warning(f"edge01 health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """Get available inference models from edge01"""
        if not self._client:
            logger.error("Client not initialized")
            return []

        try:
            response = await self._client.get(
                f"{self.api_url}/models",
                timeout=EDGETPU_HEALTH_TIMEOUT
            )
            if response.status_code == 200:
                self.models = response.json().get("models", [])
            return self.models
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return self.models  # Return cached models

    async def detect_objects(
        self,
        image_base64: str,
        model_name: str = "ssd_mobiledet",
        confidence_threshold: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Run object detection on edge01's Coral Edge TPU

        Args:
            image_base64: Base64-encoded image
            model_name: Detection model (currently only "ssd_mobiledet")
            confidence_threshold: Score threshold applied on-device

        Returns:
            {"status": "completed", "model": ..., "boxes": [...], "latency_ms": ...}
            or None on failure
        """
        if not self._client:
            logger.error("Client not initialized")
            return None

        if self.status == EdgeTpuStatus.OFFLINE:
            logger.warning(f"edge01 is offline, cannot infer with {model_name}")
            return None

        try:
            payload = {
                "model": model_name,
                "image": image_base64,
                "confidence_threshold": confidence_threshold,
            }

            response = await self._client.post(
                f"{self.api_url}/infer",
                json=payload,
                timeout=EDGETPU_INFERENCE_TIMEOUT,
            )

            if response.status_code == 200:
                return response.json()

            logger.warning(f"edge01 inference failed: {response.status_code}")
            logger.debug(f"Response: {response.text}")
            return None

        except httpx.TimeoutException:
            logger.error(f"edge01 inference timeout for {model_name}")
            return None
        except Exception as e:
            logger.error(f"edge01 inference error: {e}")
            return None


# Global client instance
_client: Optional[EdgeTpuClient] = None


async def get_edgetpu_client() -> EdgeTpuClient:
    """Get or create global Edge TPU client instance"""
    global _client

    if _client is None:
        _client = EdgeTpuClient()
        await _client.initialize()

    return _client


async def initialize_edgetpu_client():
    """Initialize Edge TPU client (call from app startup)"""
    global _client
    _client = EdgeTpuClient()
    await _client.initialize()


async def shutdown_edgetpu_client():
    """Shutdown Edge TPU client (call from app shutdown)"""
    global _client
    if _client:
        await _client.shutdown()
        _client = None
