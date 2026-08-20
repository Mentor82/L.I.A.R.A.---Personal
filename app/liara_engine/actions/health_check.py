"""
Health Check Action - Liara kann ihren eigenen Systemstatus prüfen

Erlaubt Liara, auf Anfrage:
- Gesamten Systemstatus abzurufen
- Einzelne Komponenten zu prüfen (DB, Services, AI, etc.)
- Load-Status zu checken
"""

import asyncio
import httpx
from typing import Dict, Optional


async def check_system_health(component: Optional[str] = None) -> Dict:
    """
    Prüft Systemstatus - kann von Liara im Chat aufgerufen werden.
    
    Args:
        component: Optional - spezifische Komponente (z.B. "database", "ollama", "load")
                  None = kompletter Systemcheck
    
    Returns:
        Dict mit Status-Informationen
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if component == "load":
                # System Load abfragen
                response = await client.get("http://localhost:8100/system/load")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "component": "System Load",
                        "data": {
                            "cpu": f"{data['cpu_percent']}%",
                            "memory": f"{data['memory_percent']}%",
                            "connections": data['active_connections'],
                            "mode": data['recommendation'],
                            "reasoning": data['reasoning']
                        },
                        "message": f"CPU: {data['cpu_percent']}%, RAM: {data['memory_percent']}%, Modus: {data['recommendation']}"
                    }
            
            elif component in ["database", "db", "postgres", "postgresql"]:
                # Nur Datenbank prüfen
                response = await client.get("http://localhost:8100/admin/health/full")
                if response.status_code == 200:
                    health = response.json()
                    db_status = health.get('databases', {}).get('postgresql', {})
                    return {
                        "status": "success",
                        "component": "PostgreSQL",
                        "data": db_status,
                        "message": f"PostgreSQL: {db_status.get('status', 'unknown')}"
                    }
            
            elif component in ["neo4j", "graph"]:
                # Neo4j Graph DB prüfen
                response = await client.get("http://localhost:8100/admin/health/full")
                if response.status_code == 200:
                    health = response.json()
                    neo4j_status = health.get('databases', {}).get('neo4j', {})
                    return {
                        "status": "success",
                        "component": "Neo4j",
                        "data": neo4j_status,
                        "message": f"Neo4j: {neo4j_status.get('status', 'unknown')}, Nodes: {neo4j_status.get('node_count', 0)}"
                    }
            
            elif component in ["ollama", "ai", "models"]:
                # Ollama AI Service prüfen
                response = await client.get("http://localhost:8100/admin/health/full")
                if response.status_code == 200:
                    health = response.json()
                    ollama_status = health.get('services', {}).get('ollama', {})
                    return {
                        "status": "success",
                        "component": "Ollama",
                        "data": ollama_status,
                        "message": f"Ollama: {ollama_status.get('status', 'unknown')}"
                    }
            
            else:
                # Kompletter Health Check
                response = await client.get("http://localhost:8100/admin/health/full")
                if response.status_code == 200:
                    health = response.json()
                    overall = health.get('overall', {})
                    
                    # Zusammenfassung erstellen
                    summary = {
                        "status": overall.get('status', 'unknown'),
                        "health_percentage": overall.get('health_percentage', 0),
                        "checks_passed": overall.get('checks_passed', 0),
                        "checks_total": overall.get('checks_total', 0),
                        "services": {},
                        "databases": {}
                    }
                    
                    # Services zusammenfassen
                    for service, status in health.get('services', {}).items():
                        summary['services'][service] = status.get('status', 'unknown')
                    
                    # Datenbanken zusammenfassen
                    for db, status in health.get('databases', {}).items():
                        summary['databases'][db] = status.get('status', 'unknown')
                    
                    return {
                        "status": "success",
                        "component": "System Health",
                        "data": summary,
                        "message": f"System: {overall.get('status', 'unknown')} ({overall.get('health_percentage', 0):.0f}%), {overall.get('checks_passed', 0)}/{overall.get('checks_total', 0)} Checks OK"
                    }
            
            return {
                "status": "error",
                "message": f"Unbekannte Komponente: {component}"
            }
            
    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": "Health Check Timeout - System antwortet nicht"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Fehler beim Health Check: {str(e)}"
        }


# Intent Detection Keywords für Health Checks
# NUR technische/explizite System-Anfragen, NICHT "Wie geht es dir?"
HEALTH_CHECK_KEYWORDS = [
    'systemstatus', 'system status', 'system check', 'health check',
    'server status', 'backend status', 'api status',
    'datenbank status', 'database status', 'postgres status',
    'neo4j status', 'graph status', 'ollama status', 
    'ai status', 'service status', 'komponenten status',
    'system load', 'system auslastung', 'server load',
    'cpu auslastung', 'ram auslastung', 'speicher auslastung',
    'prüf system', 'check system', 'diagnose system',
    'läuft datenbank', 'läuft neo4j', 'läuft ollama',
    'funktioniert datenbank', 'funktioniert neo4j'
]
