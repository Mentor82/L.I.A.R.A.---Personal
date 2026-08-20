from fastapi import APIRouter
import platform
import psutil
import time

router = APIRouter()

@router.get("/info")
def system_info():
    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "kernel": platform.release(),
        "cpu_count": psutil.cpu_count(),
        "uptime": time.time() - psutil.boot_time()
    }
