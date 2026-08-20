"""
Vision Detection Service
- Provides a unified interface for object detection across backends
- Backends: hailo (Hailo-8L), edgetpu (Coral), cpu (stub/placeholder)
"""
from __future__ import annotations

import asyncio
import base64
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from services.hailo_vision_service import HailoVisionService, Detection as HailoDetection


class VisionDetectionService:
    """Unified detection service with pluggable backends."""

    def __init__(self) -> None:
        self.hailo_service = HailoVisionService()

    async def detect_objects(
        self,
        image_bytes: bytes,
        backend: str = "hailo",
        model: str = "yolov8n",
        confidence_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        backend = backend.lower().strip()

        if backend == "hailo":
            return await self._detect_hailo(image_bytes, model, confidence_threshold)
        if backend == "edgetpu":
            return await self._detect_edgetpu(image_bytes, model, confidence_threshold)
        return await self._detect_cpu_stub(image_bytes, model, confidence_threshold)

    async def _detect_hailo(
        self,
        image_bytes: bytes,
        model: str,
        confidence_threshold: Optional[float],
    ) -> Dict[str, Any]:
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        result = await self.hailo_service.detect_objects(
            image_base64=image_base64,
            model_name=model,
            confidence_threshold=confidence_threshold,
        )

        boxes = [self._map_hailo_detection(det) for det in result.detections or []]
        return {
            "backend": "hailo",
            "model": model,
            "boxes": boxes,
            "latency_ms": result.latency_ms,
        }

    async def _detect_edgetpu(
        self,
        image_bytes: bytes,
        model: str,
        confidence_threshold: Optional[float],
    ) -> Dict[str, Any]:
        # Placeholder Edge TPU path: replace with real TFLite + edgetpu runtime call
        start = time.time()
        await asyncio.sleep(0.05)
        return {
            "backend": "edgetpu",
            "model": model,
            "boxes": [
                {
                    "x": 60,
                    "y": 40,
                    "width": 180,
                    "height": 140,
                    "score": 0.81,
                    "label": "object",
                }
            ],
            "latency_ms": (time.time() - start) * 1000,
        }

    async def _detect_cpu_stub(
        self,
        image_bytes: bytes,
        model: str,
        confidence_threshold: Optional[float],
    ) -> Dict[str, Any]:
        # Lightweight CPU stub: replace with ONNX/PyTorch runtime if needed
        start = time.time()
        await asyncio.sleep(0.05)
        return {
            "backend": "cpu",
            "model": model,
            "boxes": [
                {
                    "x": 120,
                    "y": 80,
                    "width": 140,
                    "height": 120,
                    "score": 0.72,
                    "label": "object",
                }
            ],
            "latency_ms": (time.time() - start) * 1000,
        }

    def _map_hailo_detection(self, det: HailoDetection) -> Dict[str, Any]:
        return {
            "x": det.bbox.get("x", 0),
            "y": det.bbox.get("y", 0),
            "width": det.bbox.get("width", 0),
            "height": det.bbox.get("height", 0),
            "score": det.confidence,
            "label": det.class_name,
        }


@lru_cache(maxsize=1)
def get_vision_detection_service() -> VisionDetectionService:
    return VisionDetectionService()
