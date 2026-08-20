"""System Load Router - Provides real-time system load information for adaptive SSE."""
from fastapi import APIRouter
import psutil
import time

router = APIRouter(prefix="/system", tags=["system"])

# Cache for load average (refresh every 2 seconds)
_load_cache = {"timestamp": 0, "data": None}
_CACHE_TTL = 2.0


@router.get("/load")
async def get_system_load():
    """
    Get current system load for SSE decision-making.
    
    Returns:
        - cpu_percent: Current CPU usage (0-100)
        - memory_percent: Current RAM usage (0-100)
        - active_connections: Estimated active connections
        - recommendation: "sse" or "sync" based on load
    """
    global _load_cache
    
    now = time.time()
    
    # Return cached data if fresh
    if _load_cache["data"] and (now - _load_cache["timestamp"]) < _CACHE_TTL:
        return _load_cache["data"]
    
    # Get fresh metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Estimate active connections (simplified)
    net_connections = len(psutil.net_connections(kind='inet'))
    
    # Decision Logic:
    # - SSE wenn CPU < 70% und Memory < 80%
    # - SYNC wenn System überlastet
    recommendation = "sse"
    
    if cpu_percent > 70 or memory.percent > 80:
        recommendation = "sync"
    
    data = {
        "cpu_percent": round(cpu_percent, 1),
        "memory_percent": round(memory.percent, 1),
        "active_connections": net_connections,
        "recommendation": recommendation,
        "reasoning": f"CPU: {cpu_percent:.1f}%, RAM: {memory.percent:.1f}%"
    }
    
    # Update cache
    _load_cache = {"timestamp": now, "data": data}
    
    return data
