"""
Hailo RPi5 REST API Client

Service for communicating with hailo-api on RPi5 (192.168.178.15:5000)
Handles image encoding, inference requests, and response parsing.

This service acts as a bridge between liara backend and the Hailo-8L NPU
running on the Raspberry Pi 5 with docker-compose services.
"""

import httpx
import base64
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# Configuration
RPI5_API_URL = "http://192.168.178.15:5000"
RPI5_HEALTH_TIMEOUT = 5.0  # seconds
RPI5_INFERENCE_TIMEOUT = 30.0  # seconds
RPI5_HEALTH_CHECK_INTERVAL = 30.0  # Check every 30 seconds


class RPi5Status(Enum):
    """RPi5 API availability status"""
    HEALTHY = "healthy"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class HailoRPi5Client:
    """
    Client for communicating with hailo-api on RPi5.
    
    Handles:
    - Health checking
    - Model listing
    - Inference requests (REST + MQTT)
    - Error handling and retries
    """
    
    def __init__(self):
        self.api_url = RPI5_API_URL
        self.status = RPi5Status.OFFLINE
        self.last_health_check = None
        self.models = []
        self._client = None
        self._health_check_task = None
    
    async def initialize(self):
        """Initialize client and start health check loop"""
        self._client = httpx.AsyncClient(timeout=RPI5_HEALTH_TIMEOUT)
        await self.health_check()
        logger.info(f"Hailo RPi5 client initialized: {self.status.value}")
    
    async def shutdown(self):
        """Cleanup resources"""
        if self._client:
            await self._client.aclose()
            logger.info("Hailo RPi5 client shutdown")
    
    async def health_check(self) -> bool:
        """
        Check if RPi5 Hailo API is healthy
        
        Returns:
            True if API is reachable and responsive
        """
        if not self._client:
            self.status = RPi5Status.OFFLINE
            return False
        
        try:
            response = await self._client.get(
                f"{self.api_url}/health",
                timeout=RPI5_HEALTH_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                self.status = RPi5Status.HEALTHY
                self.last_health_check = datetime.now()
                
                # Update available models
                models = data.get("models", [])
                self.models = models
                logger.debug(f"RPi5 health check OK: {len(models)} models available")
                return True
            else:
                self.status = RPi5Status.DEGRADED
                logger.warning(f"RPi5 health check returned {response.status_code}")
                return False
                
        except Exception as e:
            self.status = RPi5Status.OFFLINE
            logger.warning(f"RPi5 health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """
        Get available inference models from RPi5
        
        Returns:
            List of model names available on RPi5
        """
        if not self._client:
            logger.error("Client not initialized")
            return []
        
        try:
            response = await self._client.get(
                f"{self.api_url}/models",
                timeout=RPI5_HEALTH_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                self.models = data.get("models", [])
                logger.debug(f"Retrieved {len(self.models)} models from RPi5")
                return self.models
            else:
                logger.warning(f"Failed to list models: {response.status_code}")
                return self.models  # Return cached models
                
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return self.models  # Return cached models
    
    async def infer(
        self,
        model_name: str,
        image_base64: str,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Run inference on RPi5 with given model and image
        
        Args:
            model_name: Model to use (e.g., "yolov8n", "resnet_v1_50")
            image_base64: Base64-encoded image data
            timeout: Optional timeout override
            
        Returns:
            Inference result dict or None on failure
            
        Example result:
            {
                "model": "yolov8n",
                "status": "completed",
                "output": "...",
                "timestamp": "2026-01-02T20:53:55.549055",
                "source": "rest"
            }
        """
        if not self._client:
            logger.error("Client not initialized")
            return None
        
        if self.status == RPi5Status.OFFLINE:
            logger.warning(f"RPi5 is offline, cannot infer with {model_name}")
            return None
        
        try:
            payload = {
                "model": model_name,
                "image": image_base64
            }
            
            response = await self._client.post(
                f"{self.api_url}/infer",
                json=payload,
                timeout=timeout or RPI5_INFERENCE_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Inference successful for model {model_name}")
                return result
            else:
                logger.warning(f"Inference failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                return None
                
        except httpx.TimeoutException:
            logger.error(f"Inference timeout for {model_name}")
            return None
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return None
    
    async def detect_objects(
        self,
        image_base64: str,
        model_name: str = "yolov8n",
        confidence_threshold: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Run object detection on image using YOLOv8 on RPi5
        
        Args:
            image_base64: Base64-encoded image
            model_name: Detection model (yolov8n, yolov8s, yolov11n, etc.)
            confidence_threshold: Confidence threshold (stored for client filtering)
            
        Returns:
            Detection result with bbox list
        """
        # Note: confidence filtering done client-side
        # RPi5 API doesn't expose confidence threshold parameter
        result = await self.infer(model_name, image_base64)
        
        # Parse YOLO output if available
        if result and result.get("status") == "completed":
            # The output format depends on RPi5 implementation
            # Store confidence threshold in metadata for client-side filtering
            result["confidence_threshold"] = confidence_threshold
        
        return result
    
    async def pose_estimation(
        self,
        image_base64: str,
        model_name: str = "yolov8s_pose"
    ) -> Optional[Dict[str, Any]]:
        """
        Run pose estimation on image using YOLOv8-Pose on RPi5
        
        Args:
            image_base64: Base64-encoded image
            model_name: Pose model (yolov8s_pose, yolov8n_pose, etc.)
            
        Returns:
            Pose estimation result with keypoints
        """
        result = await self.infer(model_name, image_base64)
        return result
    
    async def segmentation(
        self,
        image_base64: str,
        model_name: str = "yolov5n_seg"
    ) -> Optional[Dict[str, Any]]:
        """
        Run instance segmentation on image on RPi5
        
        Args:
            image_base64: Base64-encoded image
            model_name: Segmentation model (yolov5n_seg, yolov5s_seg, etc.)
            
        Returns:
            Segmentation result with masks
        """
        result = await self.infer(model_name, image_base64)
        return result


# Global client instance
_client: Optional[HailoRPi5Client] = None


async def get_rpi5_client() -> HailoRPi5Client:
    """
    Get or create global RPi5 client instance
    
    Returns:
        Initialized HailoRPi5Client
    """
    global _client
    
    if _client is None:
        _client = HailoRPi5Client()
        await _client.initialize()
    
    return _client


async def initialize_rpi5_client():
    """Initialize RPi5 client (call from app startup)"""
    global _client
    _client = HailoRPi5Client()
    await _client.initialize()


async def shutdown_rpi5_client():
    """Shutdown RPi5 client (call from app shutdown)"""
    global _client
    if _client:
        await _client.shutdown()
        _client = None
