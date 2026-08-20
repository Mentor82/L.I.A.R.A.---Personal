"""
GPU Detection API Router
Provides GPU information and recommendations
"""

from fastapi import APIRouter
from core.gpu_detection import get_gpu_detector

router = APIRouter(prefix="/gpu", tags=["GPU"])


@router.get("/status")
async def get_gpu_status():
    """
    Get GPU detection status and information
    
    Returns:
        - available: bool - GPU availability
        - devices: list - GPU device information
        - total_vram_mb: int - Total VRAM in MB
        - recommended_models: list - Models that can run on GPU
    """
    detector = get_gpu_detector()
    return detector.get_status()


@router.get("/check/{model_size}")
async def check_model_compatibility(model_size: float):
    """
    Check if a model of given size (in GB) can run on GPU
    
    Args:
        model_size: Model size in GB (e.g., 7.0 for 7GB)
    
    Returns:
        - can_run: bool
        - gpu_available: bool
        - vram_available_mb: int
        - vram_required_mb: int
    """
    detector = get_gpu_detector()
    
    if not detector.is_available():
        return {
            'can_run': False,
            'gpu_available': False,
            'vram_available_mb': 0,
            'vram_required_mb': int(model_size * 1024 * 1.2),
            'message': 'No GPU available'
        }
    
    can_run = detector.can_run_model(model_size)
    vram = detector.get_total_vram() or 0
    
    return {
        'can_run': can_run,
        'gpu_available': True,
        'vram_available_mb': vram,
        'vram_required_mb': int(model_size * 1024 * 1.2),
        'message': 'Model can run on GPU' if can_run else 'Insufficient VRAM'
    }


@router.get("/recommendations")
async def get_model_recommendations():
    """
    Get model size recommendations based on available GPU
    
    Returns list of recommended model sizes (e.g., ['70b', '34b', '20b'])
    """
    detector = get_gpu_detector()
    
    if not detector.is_available():
        return {
            'gpu_available': False,
            'recommendations': [],
            'message': 'No GPU detected - CPU-only models recommended'
        }
    
    return {
        'gpu_available': True,
        'recommendations': detector.get_recommended_models(),
        'vram_mb': detector.get_total_vram(),
        'message': f'GPU with {detector.get_total_vram()} MB VRAM detected'
    }
