"""
Hailo NPU Service - Integration with Hailo-8L accelerator
Provides access to HEF model inference and telemetry
"""

import requests
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Hailo API Config
HAILO_API_BASE_URL = "http://localhost:8080"  # hailo-api default port
HAILO_API_TIMEOUT = 30
HAILO_HEALTH_CHECK_ENDPOINT = f"{HAILO_API_BASE_URL}/health"
HAILO_METRICS_ENDPOINT = f"{HAILO_API_BASE_URL}/metrics"


@dataclass
class HailoDevice:
    """Hailo device information"""
    device_id: str
    architecture: str  # HAILO8L, HAILO8, etc.
    firmware_version: str
    driver_version: str
    temperature: float = 0.0
    power_consumption_w: float = 0.0
    available: bool = True


@dataclass
class HailoModelInfo:
    """HEF Model metadata"""
    name: str
    architecture: str  # HAILO8L, HAILO8
    input_shape: List[int]
    output_shape: List[int]
    max_fps: float
    inference_time_ms: float
    power_w: float


@dataclass
class InferenceMetrics:
    """Inference performance metrics"""
    model_name: str
    fps: float
    latency_ms: float
    throughput_mbps: float
    queue_length: int
    errors_total: int
    successful_inferences: int
    timestamp: datetime


class HailoService:
    """Service for managing Hailo-8L NPU accelerator"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.api_url = HAILO_API_BASE_URL
        self.device: Optional[HailoDevice] = None
        self.models_cache: Dict[str, HailoModelInfo] = {}
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Hailo service and verify connectivity"""
        try:
            # Check if hailo-api is reachable
            response = requests.get(
                HAILO_HEALTH_CHECK_ENDPOINT,
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            health = response.json()
            
            # Fetch device information
            device_info = await self.get_device_info()
            self._initialized = device_info is not None
            
            logger.info(f"✅ Hailo service initialized: {device_info}")
            return self._initialized
        except requests.ConnectionError:
            logger.warning(f"❌ Hailo API not reachable at {self.api_url}")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"❌ Hailo initialization error: {e}")
            self._initialized = False
            return False
    
    async def get_device_info(self) -> Optional[HailoDevice]:
        """Get Hailo device information"""
        try:
            response = requests.get(
                f"{self.api_url}/device",
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            self.device = HailoDevice(
                device_id=data.get("device_id", "unknown"),
                architecture=data.get("architecture", "HAILO8L"),
                firmware_version=data.get("firmware_version", "unknown"),
                driver_version=data.get("driver_version", "unknown"),
                temperature=data.get("temperature", 0.0),
                power_consumption_w=data.get("power_consumption_w", 0.0),
                available=data.get("available", True)
            )
            return self.device
        except Exception as e:
            logger.error(f"Error fetching Hailo device info: {e}")
            return None
    
    async def list_models(self) -> List[HailoModelInfo]:
        """List available HEF models"""
        try:
            response = requests.get(
                f"{self.api_url}/models",
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            models_data = response.json()
            
            models = []
            for model_data in models_data.get("models", []):
                model = HailoModelInfo(
                    name=model_data.get("name"),
                    architecture=model_data.get("architecture"),
                    input_shape=model_data.get("input_shape", []),
                    output_shape=model_data.get("output_shape", []),
                    max_fps=model_data.get("max_fps", 0.0),
                    inference_time_ms=model_data.get("inference_time_ms", 0.0),
                    power_w=model_data.get("power_w", 0.0)
                )
                models.append(model)
                self.models_cache[model.name] = model
            
            return models
        except Exception as e:
            logger.error(f"Error listing Hailo models: {e}")
            return list(self.models_cache.values())
    
    async def run_inference(
        self,
        model_name: str,
        input_data: Dict[str, Any],
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Run inference on Hailo accelerator
        
        Args:
            model_name: Name of the HEF model
            input_data: Input tensor data
            stream: Enable streaming output
        
        Returns:
            Inference result with output tensors and metrics
        """
        try:
            payload = {
                "model": model_name,
                "input": input_data,
                "stream": stream
            }
            
            response = requests.post(
                f"{self.api_url}/infer",
                json=payload,
                timeout=HAILO_API_TIMEOUT,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                # Handle streaming response
                return {"stream": response.iter_content(chunk_size=1024)}
            else:
                return response.json()
        
        except requests.Timeout:
            logger.error(f"Hailo inference timeout for model {model_name}")
            raise
        except Exception as e:
            logger.error(f"Hailo inference error: {e}")
            raise
    
    async def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get Hailo metrics (Prometheus format or JSON)"""
        try:
            response = requests.get(
                HAILO_METRICS_ENDPOINT,
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            
            # Try to parse as JSON first, fall back to Prometheus text format
            try:
                return response.json()
            except:
                return {"raw_metrics": response.text}
        except Exception as e:
            logger.error(f"Error fetching Hailo metrics: {e}")
            return None
    
    async def get_inference_metrics(self, model_name: str) -> Optional[InferenceMetrics]:
        """Get detailed inference metrics for a specific model"""
        try:
            response = requests.get(
                f"{self.api_url}/metrics/{model_name}",
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            return InferenceMetrics(
                model_name=model_name,
                fps=data.get("fps", 0.0),
                latency_ms=data.get("latency_ms", 0.0),
                throughput_mbps=data.get("throughput_mbps", 0.0),
                queue_length=data.get("queue_length", 0),
                errors_total=data.get("errors_total", 0),
                successful_inferences=data.get("successful_inferences", 0),
                timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
            )
        except Exception as e:
            logger.error(f"Error fetching model metrics: {e}")
            return None
    
    async def get_power_profile(self) -> Dict[str, float]:
        """Get current power consumption profile"""
        try:
            response = requests.get(
                f"{self.api_url}/power",
                timeout=HAILO_API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching power profile: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Quick health check of Hailo service"""
        try:
            response = requests.get(
                HAILO_HEALTH_CHECK_ENDPOINT,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if Hailo service is available"""
        return self._initialized and self.device is not None


def get_hailo_service() -> HailoService:
    """Dependency injection for HailoService (singleton)"""
    return HailoService()
