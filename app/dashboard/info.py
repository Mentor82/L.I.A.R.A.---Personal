import psutil
import platform
import datetime

def get_dashboard_info():
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    cpu_load = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "hostname": platform.node(),
        "uptime": str(datetime.datetime.now() - boot_time),
        "cpu_load": cpu_load,
        "memory": {
            "used": memory.used,
            "total": memory.total,
            "percent": memory.percent
        },
        "disk": {
            "used": disk.used,
            "total": disk.total,
            "percent": disk.percent
        }
    }
