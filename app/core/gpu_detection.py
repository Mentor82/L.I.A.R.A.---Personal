"""
GPU Detection Module
Detects NVIDIA GPUs and provides information for model optimization
"""

import subprocess
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class GPUDetector:
    """Detects and manages GPU information"""
    
    def __init__(self):
        self._gpu_available = None
        self._gpu_info = None
        self._check_gpu()
    
    def _check_gpu(self):
        """Check for NVIDIA GPU availability"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', 
                 '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                self._gpu_available = True
                self._gpu_info = []
                
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        self._gpu_info.append({
                            'name': parts[0],
                            'memory': parts[1],
                            'driver': parts[2]
                        })
                
                logger.info(f"GPU detected: {len(self._gpu_info)} device(s)")
            else:
                self._gpu_available = False
                logger.info("No NVIDIA GPU detected")
                
        except FileNotFoundError:
            self._gpu_available = False
            logger.info("nvidia-smi not found - no GPU support")
        except subprocess.TimeoutExpired:
            self._gpu_available = False
            logger.warning("nvidia-smi timeout - GPU detection failed")
        except Exception as e:
            self._gpu_available = False
            logger.error(f"GPU detection error: {e}")
    
    def is_available(self) -> bool:
        """Check if GPU is available"""
        return self._gpu_available or False
    
    def get_gpu_info(self) -> List[Dict[str, str]]:
        """Get detailed GPU information"""
        return self._gpu_info or []
    
    def get_total_vram(self) -> Optional[int]:
        """Get total VRAM in MB"""
        if not self._gpu_info:
            return None
        
        try:
            # Parse memory from first GPU (e.g., "24576 MiB")
            memory_str = self._gpu_info[0]['memory']
            memory_mb = int(memory_str.split()[0])
            return memory_mb
        except (IndexError, ValueError, KeyError):
            return None
    
    def get_recommended_models(self) -> List[str]:
        """Get list of models recommended for available GPU"""
        vram = self.get_total_vram()
        
        if not vram:
            return []
        
        # Recommendations based on VRAM
        if vram >= 24000:  # 24GB+
            return ['70b', '34b', '20b', '13b', '7b']
        elif vram >= 16000:  # 16GB
            return ['34b', '20b', '13b', '7b']
        elif vram >= 12000:  # 12GB
            return ['20b', '13b', '7b']
        elif vram >= 8000:   # 8GB
            return ['13b', '7b', '3b']
        elif vram >= 4000:   # 4GB
            return ['7b', '3b', '1b']
        else:
            return ['3b', '1b']
    
    def can_run_model(self, model_size_gb: float) -> bool:
        """Check if GPU can run a model of given size"""
        vram = self.get_total_vram()
        
        if not vram:
            return False
        
        # Convert to GB and add 20% overhead
        required_vram = model_size_gb * 1024 * 1.2
        return vram >= required_vram
    
    def get_status(self) -> Dict:
        """Get complete GPU status for API response"""
        if not self._gpu_available:
            return {
                'available': False,
                'message': 'No NVIDIA GPU detected',
                'devices': []
            }
        
        return {
            'available': True,
            'message': f'{len(self._gpu_info)} GPU(s) detected',
            'devices': self._gpu_info,
            'total_vram_mb': self.get_total_vram(),
            'recommended_models': self.get_recommended_models()
        }


# Singleton instance
_gpu_detector = None

def get_gpu_detector() -> GPUDetector:
    """Get or create GPU detector singleton"""
    global _gpu_detector
    if _gpu_detector is None:
        _gpu_detector = GPUDetector()
    return _gpu_detector
