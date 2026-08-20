"""
⚙️ Tool Executor
Automatische Ausführung von Tool-Calls mit Privacy-Checks
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.tool_registry import get_tool_registry, ToolDefinition
from services.tool_parser import ToolCall
from services.web_search_service import get_web_search_service
from services.location_service import get_location_service

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Tool-Ausführungs-Fehler"""
    pass


class ToolExecutor:
    """Führt Tool-Calls automatisch aus"""
    
    def __init__(self):
        self.registry = get_tool_registry()
        self.web_search = get_web_search_service()
        self.location_service = get_location_service()
    
    async def execute(
        self,
        tool_call: ToolCall,
        user_id: int,
        check_consent: bool = True
    ) -> Dict[str, Any]:
        """
        Führt Tool-Call aus
        
        Args:
            tool_call: Der auszuführende Tool-Call
            user_id: User-ID für Privacy-Checks
            check_consent: Ob Consent geprüft werden soll
            
        Returns:
            Tool-Execution Result
            
        Raises:
            ToolExecutionError: Bei Ausführungsfehlern
        """
        # Tool aus Registry holen
        tool_def = self.registry.get_tool(tool_call.tool_name)
        
        if not tool_def:
            return self._error_result(
                tool_call.tool_name,
                f"Unknown tool: {tool_call.tool_name}"
            )
        
        # Privacy-Check
        if check_consent and tool_def.requires_consent:
            has_consent = await self._check_user_consent(user_id, tool_def)
            if not has_consent:
                return self._error_result(
                    tool_call.tool_name,
                    "User consent required but not granted",
                    consent_required=True
                )
        
        # Parameter-Validierung
        validation_error = self._validate_parameters(tool_call, tool_def)
        if validation_error:
            return self._error_result(
                tool_call.tool_name,
                validation_error
            )
        
        # Tool ausführen
        try:
            logger.info(f"Executing tool: {tool_call.tool_name} for user {user_id}")
            
            result = await self._execute_tool(tool_def, tool_call.parameters, user_id)
            
            return {
                "success": True,
                "tool": tool_call.tool_name,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "execution_time_ms": 0  # TODO: Measure actual time
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_call.tool_name}: {e}")
            return self._error_result(
                tool_call.tool_name,
                str(e)
            )
    
    async def _execute_tool(
        self,
        tool_def: ToolDefinition,
        parameters: Dict[str, Any],
        user_id: int
    ) -> Any:
        """
        Routing zu echten Tool-Implementierungen
        """
        # Web Search
        if tool_def.name == "web_search":
            return await self._execute_web_search(parameters)
        
        # Weather
        elif tool_def.name == "get_weather":
            return await self._execute_weather(parameters)
        
        # Location Detection
        elif tool_def.name == "detect_location":
            return await self._execute_location(user_id)
        
        # Wikipedia
        elif tool_def.name == "wikipedia_search":
            return await self._execute_wikipedia(parameters)
        
        # Current Time
        elif tool_def.name == "get_current_time":
            return await self._execute_current_time(parameters)
        
        # Fallback to stub function
        else:
            return await tool_def.function(**parameters)
    
    async def _execute_web_search(self, params: Dict[str, Any]) -> Dict:
        """Führt Web-Suche aus"""
        query = params.get("query")
        search_type = params.get("search_type", "instant")
        language = params.get("language", "de")
        
        if search_type == "wikipedia":
            result = self.web_search.search_wikipedia(query, language)
        else:
            result = await self.web_search.search_instant_answer(query)
        
        # Formatiere für LLM-Konsum
        return {
            "query": query,
            "type": search_type,
            "summary": self._format_search_result(result),
            "raw": result
        }
    
    async def _execute_weather(self, params: Dict[str, Any]) -> Dict:
        """Führt Wetter-Abfrage aus"""
        city = params.get("city")
        country = params.get("country")
        language = params.get("language", "de")
        
        # TODO: Implement weather service integration
        return {
            "city": city,
            "country": country,
            "temperature": 5,
            "condition": "Bewölkt",
            "humidity": 87,
            "wind_speed": 15,
            "note": "Mock data - real weather service not yet implemented"
        }
    
    async def _execute_location(self, user_id: int) -> Dict:
        """Führt Standort-Erkennung aus"""
        # TODO: Get user's IP from request context
        location = await self.location_service.detect_location_from_ip(None)
        
        return {
            "city": location.get("city", "Unknown"),
            "region": location.get("region", "Unknown"),
            "country": location.get("country", "Unknown"),
            "timezone": location.get("timezone", "UTC")
        }
    
    async def _execute_wikipedia(self, params: Dict[str, Any]) -> Dict:
        """Führt Wikipedia-Suche aus"""
        query = params.get("query")
        language = params.get("language", "de")
        
        result = self.web_search.search_wikipedia(query, language)
        
        return {
            "query": query,
            "summary": result.get("extract", "Kein Ergebnis gefunden"),
            "url": result.get("url", ""),
            "title": result.get("title", query)
        }
    
    async def _execute_current_time(self, params: Dict[str, Any]) -> Dict:
        """Gibt aktuelle Zeit zurück"""
        from datetime import datetime
        import pytz
        
        timezone = params.get("timezone", "Europe/Berlin")
        format_type = params.get("format", "full")
        
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            
            result = {
                "timestamp": now.isoformat(),
                "timezone": timezone
            }
            
            if format_type == "date":
                result["formatted"] = now.strftime("%d.%m.%Y")
            elif format_type == "time":
                result["formatted"] = now.strftime("%H:%M:%S")
            else:
                result["formatted"] = now.strftime("%A, %d. %B %Y, %H:%M:%S Uhr")
                result["date"] = now.strftime("%d.%m.%Y")
                result["time"] = now.strftime("%H:%M:%S")
                result["weekday"] = now.strftime("%A")
            
            return result
            
        except pytz.UnknownTimeZoneError:
            return {
                "error": f"Unknown timezone: {timezone}",
                "available_timezones": pytz.common_timezones[:10]
            }
    
    def _format_search_result(self, result: Dict) -> str:
        """Formatiert Suchergebnis für LLM"""
        parts = []
        
        if result.get("abstract"):
            parts.append(f"**Zusammenfassung**: {result['abstract']}")
        
        if result.get("answer"):
            parts.append(f"**Antwort**: {result['answer']}")
        
        if result.get("definition"):
            parts.append(f"**Definition**: {result['definition']}")
        
        if not parts:
            parts.append("Keine detaillierten Informationen gefunden.")
        
        return "\n\n".join(parts)
    
    def _validate_parameters(
        self,
        tool_call: ToolCall,
        tool_def: ToolDefinition
    ) -> Optional[str]:
        """
        Validiert Tool-Parameter
        
        Returns:
            Error message oder None
        """
        # Prüfe erforderliche Parameter
        for param in tool_def.parameters:
            if param.required and param.name not in tool_call.parameters:
                return f"Missing required parameter: {param.name}"
        
        # Prüfe Parameter-Typen
        for param_name, param_value in tool_call.parameters.items():
            # Finde Parameter-Definition
            param_def = next(
                (p for p in tool_def.parameters if p.name == param_name),
                None
            )
            
            if not param_def:
                # Unknown parameter - warning but allow
                logger.warning(f"Unknown parameter: {param_name} for tool {tool_def.name}")
                continue
            
            # Type check (basic)
            expected_type = param_def.type
            if expected_type == "string" and not isinstance(param_value, str):
                return f"Parameter {param_name} must be a string"
            elif expected_type == "number" and not isinstance(param_value, (int, float)):
                return f"Parameter {param_name} must be a number"
            elif expected_type == "boolean" and not isinstance(param_value, bool):
                return f"Parameter {param_name} must be a boolean"
            
            # Enum check
            if param_def.enum and param_value not in param_def.enum:
                return f"Parameter {param_name} must be one of: {param_def.enum}"
        
        return None
    
    async def _check_user_consent(self, user_id: int, tool_def: ToolDefinition) -> bool:
        """
        Prüft ob User Consent für Tool gegeben hat
        
        TODO: Implement actual database check
        """
        # Für jetzt: Erlaube alle Tools mit niedrigem Privacy-Level
        if tool_def.privacy_level == "low":
            return True
        
        # Mittlere und hohe Privacy-Levels erfordern expliziten Consent
        # TODO: Check database for user_tool_consents table
        logger.warning(f"Consent check not fully implemented - denying {tool_def.name}")
        return False
    
    def _error_result(
        self,
        tool_name: str,
        error_msg: str,
        consent_required: bool = False
    ) -> Dict[str, Any]:
        """Erstellt Fehler-Result"""
        return {
            "success": False,
            "tool": tool_name,
            "error": error_msg,
            "consent_required": consent_required,
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instance
_executor = None

def get_tool_executor() -> ToolExecutor:
    """Get or create ToolExecutor singleton"""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
