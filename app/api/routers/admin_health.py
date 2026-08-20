"""
🏥 LIARA SYSTEM HEALTH DIAGNOSTICS
Comprehensive health check for all system components
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import psutil
import subprocess
import requests
from pathlib import Path
import json

router = APIRouter(prefix="/admin", tags=["Admin"])


def check_service_status(service_name: str) -> Dict:
    """Check systemd service status"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.stdout.strip() == 'active'
        
        # Get detailed info
        status_result = subprocess.run(
            ['systemctl', 'status', service_name, '--no-pager'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Extract PID
        pid = None
        for line in status_result.stdout.split('\n'):
            if 'Main PID:' in line:
                try:
                    pid = int(line.split('Main PID:')[1].strip().split()[0])
                except:
                    pass
        
        return {
            "status": "running" if is_active else "stopped",
            "healthy": is_active,
            "pid": pid,
            "details": status_result.stdout.split('\n')[2] if len(status_result.stdout.split('\n')) > 2 else None
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "healthy": False, "error": "Command timeout"}
    except Exception as e:
        return {"status": "error", "healthy": False, "error": str(e)}


def check_port(port: int, name: str) -> Dict:
    """Check if port is listening"""
    try:
        connections = psutil.net_connections(kind='inet')
        listening = any(
            conn.status == 'LISTEN' and conn.laddr.port == port
            for conn in connections
        )
        return {
            "port": port,
            "name": name,
            "listening": listening,
            "healthy": listening
        }
    except Exception as e:
        return {
            "port": port,
            "name": name,
            "listening": False,
            "healthy": False,
            "error": str(e)
        }


def check_endpoint(url: str, name: str, timeout: int = 5) -> Dict:
    """Check HTTP endpoint health"""
    try:
        start_time = datetime.now()
        response = requests.get(url, timeout=timeout)
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "name": name,
            "url": url,
            "status_code": response.status_code,
            "healthy": 200 <= response.status_code < 300,
            "response_time_ms": round(response_time, 2),
            "reachable": True
        }
    except requests.Timeout:
        return {
            "name": name,
            "url": url,
            "healthy": False,
            "reachable": False,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "healthy": False,
            "reachable": False,
            "error": str(e)
        }


def check_network_connectivity() -> Dict:
    """Check network connectivity (DNS, Internet)"""
    results = {
        "dns": {"healthy": False, "response_time_ms": 0},
        "internet": {"healthy": False, "response_time_ms": 0},
        "external_api": {"healthy": False, "response_time_ms": 0}
    }
    
    # DNS Test (resolve google.com)
    try:
        start = datetime.now()
        import socket
        socket.gethostbyname('google.com')
        dns_time = (datetime.now() - start).total_seconds() * 1000
        results["dns"] = {
            "healthy": True,
            "response_time_ms": round(dns_time, 2),
            "test": "DNS resolution (google.com)"
        }
    except Exception as e:
        results["dns"] = {
            "healthy": False,
            "error": str(e),
            "test": "DNS resolution"
        }
    
    # Internet Connectivity Test (ping 1.1.1.1)
    try:
        start = datetime.now()
        response = requests.get('http://1.1.1.1', timeout=3)
        ping_time = (datetime.now() - start).total_seconds() * 1000
        results["internet"] = {
            "healthy": True,
            "response_time_ms": round(ping_time, 2),
            "test": "HTTP to 1.1.1.1 (Cloudflare DNS)"
        }
    except Exception as e:
        results["internet"] = {
            "healthy": False,
            "error": str(e)[:100],
            "test": "Internet connectivity"
        }
    
    # External API Test (httpbin.org)
    try:
        start = datetime.now()
        response = requests.get('https://httpbin.org/get', timeout=5)
        api_time = (datetime.now() - start).total_seconds() * 1000
        results["external_api"] = {
            "healthy": response.status_code == 200,
            "response_time_ms": round(api_time, 2),
            "status_code": response.status_code,
            "test": "External API (httpbin.org)"
        }
    except Exception as e:
        results["external_api"] = {
            "healthy": False,
            "error": str(e)[:100],
            "test": "External API connectivity"
        }
    
    # Overall network health
    all_healthy = all(r.get('healthy', False) for r in results.values())
    
    return {
        "overall_healthy": all_healthy,
        "tests": results
    }


def check_docker_container(container_name: str) -> Dict:
    """Check Docker container status"""
    try:
        result = subprocess.run(
            ['docker', 'inspect', container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return {
                "name": container_name,
                "status": "not_found",
                "healthy": False
            }
        
        data = json.loads(result.stdout)[0]
        state = data['State']
        
        return {
            "name": container_name,
            "status": state['Status'],
            "running": state['Running'],
            "healthy": state['Running'] and state['Status'] == 'running',
            "started_at": state.get('StartedAt'),
            "restart_count": state.get('RestartCount', 0)
        }
    except Exception as e:
        return {
            "name": container_name,
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


def get_system_resources() -> Dict:
    """Get system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # CPU Status
        cpu_status = "healthy"
        if cpu_percent > 90:
            cpu_status = "critical"
        elif cpu_percent > 70:
            cpu_status = "warning"
        
        # Memory Status
        mem_status = "healthy"
        if memory.percent > 90:
            mem_status = "critical"
        elif memory.percent > 80:
            mem_status = "warning"
        
        # Disk Status
        disk_status = "healthy"
        if disk.percent > 90:
            disk_status = "critical"
        elif disk.percent > 80:
            disk_status = "warning"
        
        return {
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "cores": psutil.cpu_count(),
                "status": cpu_status,
                "healthy": cpu_status == "healthy"
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "usage_percent": round(memory.percent, 2),
                "status": mem_status,
                "healthy": mem_status == "healthy"
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": round(disk.percent, 2),
                "status": disk_status,
                "healthy": disk_status == "healthy"
            }
        }
    except Exception as e:
        return {"error": str(e), "healthy": False}


def check_database_connection() -> Dict:
    """Check PostgreSQL database connection"""
    try:
        from core.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        result = db.execute(text("SELECT version();"))
        version = result.scalar()
        
        # Check table count
        result = db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public';
        """))
        table_count = result.scalar()
        
        db.close()
        
        return {
            "name": "PostgreSQL",
            "connected": True,
            "healthy": True,
            "version": version.split()[1] if version else None,
            "tables": table_count
        }
    except Exception as e:
        return {
            "name": "PostgreSQL",
            "connected": False,
            "healthy": False,
            "error": str(e)
        }


def check_ollama() -> Dict:
    """Check Ollama availability"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            return {
                "name": "Ollama",
                "available": True,
                "healthy": True,
                "models_count": len(models),
                "models": [m['name'] for m in models[:5]]  # First 5
            }
        else:
            return {
                "name": "Ollama",
                "available": False,
                "healthy": False,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "name": "Ollama",
            "available": False,
            "healthy": False,
            "error": str(e)
        }


@router.get("/health/full")
async def full_health_check():
    """
    🏥 COMPREHENSIVE SYSTEM HEALTH CHECK
    
    Returns detailed status of all system components:
    - System Resources (CPU, RAM, Disk)
    - Services (Backend, Frontend, Nginx)
    - Docker Containers (Redis, Neo4j)
    - Databases (PostgreSQL, Neo4j, Redis)
    - AI Services (Ollama)
    - Network Endpoints
    """
    
    # System Resources
    resources = get_system_resources()
    
    # Services
    services = {
        "liara-backend": check_service_status("liara-backend"),
        "liara-sse": check_service_status("liara-sse"),
        "liara-frontend": check_service_status("liara-frontend"),
        "nginx": check_service_status("nginx"),
        "postgresql": check_service_status("postgresql"),
        "docker": check_service_status("docker")
    }
    
    # Ports
    ports = [
        check_port(8100, "FastAPI Backend"),
        check_port(8101, "SSE Streaming Server"),
        check_port(5173, "Vite Frontend"),
        check_port(80, "Nginx HTTP"),
        check_port(443, "Nginx HTTPS"),
        check_port(5432, "PostgreSQL"),
        check_port(6379, "Redis"),
        check_port(7474, "Neo4j HTTP"),
        check_port(7687, "Neo4j Bolt"),
        check_port(11434, "Ollama")
    ]
    
    # Docker Containers
    containers = {
        "redis": check_docker_container("liara_redis"),
        "neo4j": check_docker_container("liara_neo4j")
    }
    
    # Database Connections
    databases = {
        "postgresql": check_database_connection()
    }
    
    # Endpoints
    endpoints = [
        check_endpoint("http://localhost:8100/", "Backend API Root"),
        check_endpoint("http://localhost:8100/health/full", "Backend Health"),
        check_endpoint("http://localhost:8101/", "SSE Streaming Server"),
        check_endpoint("http://localhost:5173/", "Frontend Dev Server"),
        check_endpoint("http://localhost:7474/", "Neo4j Browser")
    ]
    
    # AI Services
    ai_services = {
        "ollama": check_ollama()
    }
    
    # Network Connectivity
    network = check_network_connectivity()
    
    # Calculate overall health
    all_checks = []
    
    # Add resource checks
    all_checks.extend([
        resources.get('cpu', {}).get('healthy', False),
        resources.get('memory', {}).get('healthy', False),
        resources.get('disk', {}).get('healthy', False)
    ])
    
    # Add service checks
    all_checks.extend([s.get('healthy', False) for s in services.values()])
    
    # Add critical ports (backend, SSE, frontend, db)
    critical_ports = [p for p in ports if p['port'] in [8100, 8101, 5173, 5432]]
    all_checks.extend([p.get('healthy', False) for p in critical_ports])
    
    # Add container checks
    all_checks.extend([c.get('healthy', False) for c in containers.values()])
    
    # Add database checks
    all_checks.extend([d.get('healthy', False) for d in databases.values()])
    
    # Add network checks (DNS at minimum)
    all_checks.append(network.get('overall_healthy', False))
    
    # Overall status
    healthy_count = sum(all_checks)
    total_count = len(all_checks)
    health_percentage = (healthy_count / total_count * 100) if total_count > 0 else 0
    
    overall_status = "healthy"
    if health_percentage < 50:
        overall_status = "critical"
    elif health_percentage < 80:
        overall_status = "degraded"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overall": {
            "status": overall_status,
            "healthy": overall_status == "healthy",
            "health_percentage": round(health_percentage, 2),
            "checks_passed": healthy_count,
            "checks_total": total_count
        },
        "system": {
            "resources": resources,
            "uptime_seconds": psutil.boot_time()
        },
        "services": services,
        "ports": ports,
        "containers": containers,
        "databases": databases,
        "endpoints": endpoints,
        "ai_services": ai_services,
        "network": network
    }


@router.get("/health/summary")
async def health_summary():
    """
    🩺 QUICK HEALTH SUMMARY
    
    Returns condensed health status for dashboard
    """
    full = await full_health_check()
    
    return {
        "timestamp": full["timestamp"],
        "status": full["overall"]["status"],
        "healthy": full["overall"]["healthy"],
        "health_percentage": full["overall"]["health_percentage"],
        "critical_issues": [
            {"component": name, "issue": svc.get("error", "Service down")}
            for name, svc in full["services"].items()
            if not svc.get("healthy", False)
        ],
        "resource_alerts": [
            {"type": "CPU", "usage": full["system"]["resources"]["cpu"]["usage_percent"]}
            if full["system"]["resources"]["cpu"]["status"] != "healthy" else None,
            {"type": "Memory", "usage": full["system"]["resources"]["memory"]["usage_percent"]}
            if full["system"]["resources"]["memory"]["status"] != "healthy" else None,
            {"type": "Disk", "usage": full["system"]["resources"]["disk"]["usage_percent"]}
            if full["system"]["resources"]["disk"]["status"] != "healthy" else None
        ]
    }
