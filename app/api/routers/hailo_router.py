"""
Hailo Router - API endpoints for NPU inference and monitoring
Proxies requests to Hailo-8L on RPi5 (192.168.178.15:5000)
Provides REST endpoint for computer vision tasks
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import base64

from services.hailo_service import (
    HailoService,
    get_hailo_service,
    HailoDevice,
    HailoModelInfo,
    InferenceMetrics
)

from services.hailo_vision_service import (
    get_hailo_vision_service,
    HailoVisionService,
    VisionResult,
    Detection,
    Pose,
    Face,
    VisionTaskType
)

from services.hailo_rpi5_client import (
    HailoRPi5Client,
    get_rpi5_client,
    RPi5Status
)

from core.dependencies import require_active_user
from api.models.base_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hailo", tags=["hailo"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class DeviceInfo(BaseModel):
    """Hailo device information"""
    device_id: str
    architecture: str
    firmware_version: str
    driver_version: str
    temperature: float
    power_consumption_w: float
    available: bool


class ModelInfo(BaseModel):
    """HEF model information"""
    name: str
    architecture: str
    input_shape: List[int]
    output_shape: List[int]
    max_fps: float
    inference_time_ms: float
    power_w: float


class InferenceRequest(BaseModel):
    """Inference request payload"""
    model: str
    input: Dict[str, Any]
    stream: bool = False


class InferenceResponse(BaseModel):
    """Inference response"""
    model: str
    latency_ms: float
    output: Dict[str, Any]
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Inference metrics for a model"""
    model_name: str
    fps: float
    latency_ms: float
    throughput_mbps: float
    queue_length: int
    errors_total: int
    successful_inferences: int
    timestamp: datetime


class PowerProfile(BaseModel):
    """Power consumption profile"""
    current_w: float
    peak_w: float
    average_w: float
    temperature_c: float


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@router.get("/health", tags=["hailo"])
async def hailo_health(service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)):
    """Check Hailo service health"""
    is_healthy = await service.health_check()
    device = service.device
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "available": service.is_available(),
        "device": device.device_id if device else None,
        "architecture": device.architecture if device else None,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/device", response_model=DeviceInfo, tags=["hailo"])
async def get_device_info(service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)):
    """Get Hailo device information"""
    device = await service.get_device_info()
    
    if not device:
        raise HTTPException(
            status_code=503,
            detail="Hailo device not available"
        )
    
    return DeviceInfo(
        device_id=device.device_id,
        architecture=device.architecture,
        firmware_version=device.firmware_version,
        driver_version=device.driver_version,
        temperature=device.temperature,
        power_consumption_w=device.power_consumption_w,
        available=device.available
    )


# ============================================================================
# MODELS
# ============================================================================

@router.get("/models", response_model=List[ModelInfo], tags=["hailo"])
async def list_models(service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)):
    """List available HEF models"""
    models = await service.list_models()
    
    return [
        ModelInfo(
            name=m.name,
            architecture=m.architecture,
            input_shape=m.input_shape,
            output_shape=m.output_shape,
            max_fps=m.max_fps,
            inference_time_ms=m.inference_time_ms,
            power_w=m.power_w
        )
        for m in models
    ]


@router.get("/models/{model_name}", response_model=ModelInfo, tags=["hailo"])
async def get_model_info(
    model_name: str,
    service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)
):
    """Get detailed information about a specific HEF model"""
    models = await service.list_models()
    model = next((m for m in models if m.name == model_name), None)
    
    if not model:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found"
        )
    
    return ModelInfo(
        name=model.name,
        architecture=model.architecture,
        input_shape=model.input_shape,
        output_shape=model.output_shape,
        max_fps=model.max_fps,
        inference_time_ms=model.inference_time_ms,
        power_w=model.power_w
    )


# ============================================================================
# INFERENCE
# ============================================================================

@router.post("/infer", response_model=InferenceResponse, tags=["hailo"])
async def run_inference(
    request: InferenceRequest,
    service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)
):
    """Run inference on Hailo accelerator"""
    if not service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Hailo accelerator not available"
        )
    
    try:
        result = await service.run_inference(
            request.model,
            request.input,
            request.stream
        )
        
        return InferenceResponse(
            model=request.model,
            latency_ms=result.get("latency_ms", 0.0),
            output=result.get("output", {}),
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed: {str(e)}"
        )


# ============================================================================
# METRICS & MONITORING
# ============================================================================

@router.get("/metrics/model/{model_name}", response_model=MetricsResponse, tags=["hailo"])
async def get_model_metrics(
    model_name: str,
    service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)
):
    """Get inference metrics for a specific model"""
    metrics = await service.get_inference_metrics(model_name)
    
    if not metrics:
        raise HTTPException(
            status_code=503,
            detail=f"Metrics unavailable for model '{model_name}'"
        )
    
    return MetricsResponse(
        model_name=metrics.model_name,
        fps=metrics.fps,
        latency_ms=metrics.latency_ms,
        throughput_mbps=metrics.throughput_mbps,
        queue_length=metrics.queue_length,
        errors_total=metrics.errors_total,
        successful_inferences=metrics.successful_inferences,
        timestamp=metrics.timestamp
    )


@router.get("/power", response_model=PowerProfile, tags=["hailo"])
async def get_power_consumption(
    service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)
):
    """Get current power consumption profile"""
    profile = await service.get_power_profile()
    
    return PowerProfile(
        current_w=profile.get("current_w", 0.0),
        peak_w=profile.get("peak_w", 0.0),
        average_w=profile.get("average_w", 0.0),
        temperature_c=profile.get("temperature_c", 0.0)
    )


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

@router.get("/metrics", response_class=PlainTextResponse, tags=["hailo"])
async def prometheus_metrics(
    service: HailoService = Depends(get_hailo_service),
    current_user: User = Depends(require_active_user)
):
    """
    Prometheus metrics endpoint for Hailo accelerator
    
    Exposes:
    - hailo_device_temperature (gauge)
    - hailo_power_consumption_watts (gauge)
    - hailo_inference_fps (gauge, per model)
    - hailo_inference_latency_ms (gauge, per model)
    - hailo_inference_throughput_mbps (gauge, per model)
    - hailo_inference_queue_length (gauge, per model)
    - hailo_inference_errors_total (counter, per model)
    - hailo_inference_successful_total (counter, per model)
    """
    
    metrics_lines = [
        "# HELP hailo_up Hailo service availability",
        "# TYPE hailo_up gauge",
        f"hailo_up {1 if service.is_available() else 0}",
        ""
    ]
    
    # Device metrics
    if service.device:
        metrics_lines.extend([
            "# HELP hailo_device_temperature Device temperature in Celsius",
            "# TYPE hailo_device_temperature gauge",
            f'hailo_device_temperature{{device="{service.device.device_id}",arch="{service.device.architecture}"}} {service.device.temperature}',
            "",
            "# HELP hailo_power_consumption_watts Current power consumption in watts",
            "# TYPE hailo_power_consumption_watts gauge",
            f'hailo_power_consumption_watts{{device="{service.device.device_id}"}} {service.device.power_consumption_w}',
            ""
        ])
    
    # Model metrics
    try:
        models = await service.list_models()
        for model in models:
            safe_model_name = model.name.replace("-", "_").replace(".", "_")
            
            # Max FPS from model spec
            metrics_lines.extend([
                f"# HELP hailo_model_max_fps_{{model}} Maximum FPS for model",
                f"# TYPE hailo_model_max_fps_{{model}} gauge",
                f'hailo_model_max_fps{{model="{model.name}",arch="{model.architecture}"}} {model.max_fps}',
                "",
                f"# HELP hailo_model_inference_time_ms Inference latency in milliseconds",
                f"# TYPE hailo_model_inference_time_ms gauge",
                f'hailo_model_inference_time_ms{{model="{model.name}"}} {model.inference_time_ms}',
                "",
                f"# HELP hailo_model_power_w Power consumption for model",
                f"# TYPE hailo_model_power_w gauge",
                f'hailo_model_power_w{{model="{model.name}"}} {model.power_w}',
                ""
            ])
            
            # Get live metrics for this model
            metrics = await service.get_inference_metrics(model.name)
            if metrics:
                metrics_lines.extend([
                    f"# HELP hailo_inference_fps_{{model}} Current inference FPS",
                    f"# TYPE hailo_inference_fps_{{model}} gauge",
                    f'hailo_inference_fps{{model="{model.name}"}} {metrics.fps}',
                    "",
                    f"# HELP hailo_inference_latency_ms_{{model}} Current latency in milliseconds",
                    f"# TYPE hailo_inference_latency_ms_{{model}} gauge",
                    f'hailo_inference_latency_ms{{model="{model.name}"}} {metrics.latency_ms}',
                    "",
                    f"# HELP hailo_inference_throughput_mbps_{{model}} Network throughput",
                    f"# TYPE hailo_inference_throughput_mbps_{{model}} gauge",
                    f'hailo_inference_throughput_mbps{{model="{model.name}"}} {metrics.throughput_mbps}',
                    "",
                    f"# HELP hailo_inference_queue_length_{{model}} Queue length",
                    f"# TYPE hailo_inference_queue_length_{{model}} gauge",
                    f'hailo_inference_queue_length{{model="{model.name}"}} {metrics.queue_length}',
                    "",
                    f"# HELP hailo_inference_errors_total_{{model}} Total inference errors",
                    f"# TYPE hailo_inference_errors_total_{{model}} counter",
                    f'hailo_inference_errors_total{{model="{model.name}"}} {metrics.errors_total}',
                    "",
                    f"# HELP hailo_inference_successful_total_{{model}} Successful inferences",
                    f"# TYPE hailo_inference_successful_total_{{model}} counter",
                    f'hailo_inference_successful_total{{model="{model.name}"}} {metrics.successful_inferences}',
                    ""
                ])
    except Exception as e:
        logger.error(f"Error collecting model metrics: {e}")
    
    return "\n".join(metrics_lines)


# ============================================================================
# VISION MODELS - Object Detection, Pose Estimation, Face Recognition
# ============================================================================

class DetectionResponse(BaseModel):
    """Object detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Dict[str, float]


class KeypointResponse(BaseModel):
    """Pose keypoint"""
    name: str
    x: float
    y: float
    confidence: float


class PoseResponse(BaseModel):
    """Pose estimation result"""
    keypoints: List[KeypointResponse]
    confidence: float


class FaceResponse(BaseModel):
    """Face detection result"""
    bbox: Dict[str, float]
    confidence: float
    landmarks: Optional[List[Dict[str, Any]]] = None


class VisionResultResponse(BaseModel):
    """Vision inference result"""
    task: str
    model_name: str
    detections: Optional[List[DetectionResponse]] = None
    poses: Optional[List[PoseResponse]] = None
    faces: Optional[List[FaceResponse]] = None
    latency_ms: float
    fps: float
    timestamp: datetime


@router.get("/vision/models", tags=["vision"])
async def list_vision_models(
    client: HailoRPi5Client = Depends(get_rpi5_client),
    current_user: User = Depends(require_active_user)
):
    """List available vision models on Hailo-8L RPi5"""
    models = await client.list_models()
    return {
        "count": len(models),
        "models": models,
        "rpi5_status": client.status.value,
        "source": "hailo-rpi5"
    }



@router.post("/vision/detect", tags=["vision"])
async def detect_objects(
    file: UploadFile = File(...),
    model: str = Query("yolov8n", description="Object detection model"),
    confidence: float = Query(0.5, ge=0.0, le=1.0, description="Confidence threshold"),
    client: HailoRPi5Client = Depends(get_rpi5_client),
    current_user: User = Depends(require_active_user)
):
    """
    🎯 Detect objects in image using YOLOv8 on Hailo-8L NPU (RPi5)
    
    Supports: person, vehicle, animal, objects, and 77+ COCO classes
    Models: yolov8n, yolov8s, yolov11n, yolov10n (trained on COCO dataset)
    
    Args:
        file: Image file (JPG, PNG, WEBP, max 10MB)
        model: Object detection model name
        confidence: Detection confidence threshold (0-1)
        
    Returns:
        Detection results with bounding boxes and confidence scores
    """
    # Check RPi5 connectivity
    if client.status != RPi5Status.HEALTHY:
        raise HTTPException(
            status_code=503,
            detail=f"Hailo RPi5 API unavailable: {client.status.value}"
        )
    
    # Validate file
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only images allowed."
        )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=413,
            detail="Image too large (max 10MB)"
        )
    
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    try:
        result = await client.detect_objects(
            image_base64=image_base64,
            model_name=model,
            confidence_threshold=confidence
        )
    except Exception as e:
        logger.error(f"Object detection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Detection failed: {str(e)}"
        )

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Inference timeout or RPi5 error"
        )

    # Add metadata and return raw result from RPi5
    return {
        "model": model,
        "confidence_threshold": confidence,
        "status": result.get("status", "unknown"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "timestamp": result.get("timestamp"),
        "rpi5_status": client.status.value,
        "source": "hailo-rpi5"
    }


@router.post("/vision/pose", tags=["vision"])
async def estimate_pose(
    file: UploadFile = File(...),
    model: str = Query("yolov8s_pose", description="Pose estimation model"),
    client: HailoRPi5Client = Depends(get_rpi5_client),
    current_user: User = Depends(require_active_user)
):
    """
    🧍 Estimate human pose using YOLOv8-Pose on Hailo-8L NPU (RPi5)
    
    Returns 17 keypoints (COCO format):
    - Head: nose, eyes, ears
    - Upper body: shoulders, elbows, wrists
    - Lower body: hips, knees, ankles
    
    Args:
        file: Image file (JPG, PNG, WEBP, max 10MB)
        model: yolov8s_pose (trained for 17-keypoint estimation)
        
    Returns:
        Pose estimation results with keypoint coordinates
    """
    # Check RPi5 connectivity
    if client.status != RPi5Status.HEALTHY:
        raise HTTPException(
            status_code=503,
            detail=f"Hailo RPi5 API unavailable: {client.status.value}"
        )
    
    # Validate file
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only images allowed."
        )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image too large (max 10MB)"
        )
    
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    try:
        result = await client.pose_estimation(
            image_base64=image_base64,
            model_name=model
        )
    except Exception as e:
        logger.error(f"Pose estimation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pose estimation failed: {str(e)}"
        )

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Inference timeout or RPi5 error"
        )

    return {
        "model": model,
        "status": result.get("status", "unknown"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "timestamp": result.get("timestamp"),
        "rpi5_status": client.status.value,
        "source": "hailo-rpi5"
    }


@router.post("/vision/faces", tags=["vision"])
async def detect_faces(
    file: UploadFile = File(...),
    model: str = Query("yolov8s", description="Face detection model"),
    confidence: float = Query(0.6, ge=0.0, le=1.0, description="Confidence threshold"),
    client: HailoRPi5Client = Depends(get_rpi5_client),
    current_user: User = Depends(require_active_user)
):
    """
    👤 Detect faces in image using YOLOv8 on Hailo-8L NPU (RPi5)
    
    Returns bounding boxes for faces detected in images
    
    Args:
        file: Image file (JPG, PNG, WEBP, max 10MB)
        model: yolov8s (general detection can be adapted for faces)
        confidence: Face confidence threshold (0-1)
        
    Returns:
        List of detected faces with bounding boxes
    """
    # Check RPi5 connectivity
    if client.status != RPi5Status.HEALTHY:
        raise HTTPException(
            status_code=503,
            detail=f"Hailo RPi5 API unavailable: {client.status.value}"
        )
    
    # Validate file
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only images allowed."
        )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image too large (max 10MB)"
        )
    
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    try:
        result = await client.detect_objects(
            image_base64=image_base64,
            model_name=model,
            confidence_threshold=confidence
        )
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Face detection failed: {str(e)}"
        )

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Inference timeout or RPi5 error"
        )

    return {
        "model": model,
        "confidence_threshold": confidence,
        "status": result.get("status", "unknown"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "timestamp": result.get("timestamp"),
        "rpi5_status": client.status.value,
        "source": "hailo-rpi5"
    }


@router.post("/vision/segment", tags=["vision"])
async def segment_objects(
    file: UploadFile = File(...),
    model: str = Query("yolov5n_seg", description="Segmentation model"),
    client: HailoRPi5Client = Depends(get_rpi5_client),
    current_user: User = Depends(require_active_user)
):
    """
    🎨 Instance segmentation using YOLOv5-Seg on Hailo-8L NPU (RPi5)
    
    Provides pixel-level masks for each detected object
    
    Args:
        file: Image file (JPG, PNG, WEBP, max 10MB)
        model: yolov5n_seg, yolov5s_seg
        
    Returns:
        List of detected objects with instance segmentation masks
    """
    # Check RPi5 connectivity
    if client.status != RPi5Status.HEALTHY:
        raise HTTPException(
            status_code=503,
            detail=f"Hailo RPi5 API unavailable: {client.status.value}"
        )
    
    # Validate file
    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only images allowed."
        )
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image too large (max 10MB)"
        )
    
    image_base64 = base64.b64encode(content).decode('utf-8')
    
    try:
        result = await client.segmentation(
            image_base64=image_base64,
            model_name=model
        )
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Segmentation failed: {str(e)}"
        )

    if result is None:
        raise HTTPException(
            status_code=504,
            detail="Inference timeout or RPi5 error"
        )

    return {
        "model": model,
        "status": result.get("status", "unknown"),
        "output": result.get("output"),
        "latency_ms": result.get("latency_ms"),
        "timestamp": result.get("timestamp"),
        "rpi5_status": client.status.value,
        "source": "hailo-rpi5"
    }

