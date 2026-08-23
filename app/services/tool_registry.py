"""
🔧 Tool Registry für automatisches Tool-Calling
Zentrale Verwaltung verfügbarer Tools für Liara
"""
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum


class ToolCategory(str, Enum):
    """Tool-Kategorien"""
    INFORMATION = "information"  # Web-Suche, Wikipedia
    LOCATION = "location"        # Standort, Wetter
    SYSTEM = "system"            # Systemabfragen
    UTILITY = "utility"          # Hilfsfunktionen


@dataclass
class ToolParameter:
    """Tool-Parameter Definition"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    """Tool-Definition für Ollama"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter]
    function: Callable
    requires_consent: bool = False
    privacy_level: str = "low"  # low, medium, high


class ToolRegistry:
    """Zentrale Registry für verfügbare Tools"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Registriere Standard-Tools"""
        
        # 🌍 Web Search Tool
        self.register_tool(ToolDefinition(
            name="web_search",
            description="Durchsucht das Internet mit DuckDuckGo nach aktuellen Informationen, Fakten und Definitionen",
            category=ToolCategory.INFORMATION,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Die Suchanfrage",
                    required=True
                ),
                ToolParameter(
                    name="search_type",
                    type="string",
                    description="Art der Suche",
                    required=False,
                    default="instant",
                    enum=["instant", "wikipedia"]
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Sprache der Ergebnisse",
                    required=False,
                    default="de",
                    enum=["de", "en"]
                )
            ],
            function=self._web_search_stub,
            requires_consent=False,
            privacy_level="low"
        ))
        
        # 🌤️ Weather Tool
        self.register_tool(ToolDefinition(
            name="get_weather",
            description="Ruft aktuelle Wetterdaten für einen Ort ab",
            category=ToolCategory.LOCATION,
            parameters=[
                ToolParameter(
                    name="city",
                    type="string",
                    description="Stadt oder Ort",
                    required=True
                ),
                ToolParameter(
                    name="country",
                    type="string",
                    description="Land (optional)",
                    required=False
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Sprache der Wettervorhersage",
                    required=False,
                    default="de",
                    enum=["de", "en"]
                )
            ],
            function=self._weather_stub,
            # Only ever operates on a city name the model already pulled from
            # the user's own message - never the user's real location/IP.
            # Same public-lookup privacy profile as web_search/wikipedia_search
            # (both "low", no consent gate) - "medium" was a miscategorization,
            # not a deliberate protection (see live-tested "Fix tools" plan).
            requires_consent=False,
            privacy_level="low"
        ))
        
        # 📍 Location Detection Tool
        self.register_tool(ToolDefinition(
            name="detect_location",
            description="Ermittelt den aktuellen Standort des Benutzers (Stadt/Region) basierend auf IP",
            category=ToolCategory.LOCATION,
            parameters=[],
            function=self._location_stub,
            requires_consent=True,
            privacy_level="high"
        ))
        
        # 📚 Wikipedia Search
        self.register_tool(ToolDefinition(
            name="wikipedia_search",
            description="Sucht nach Informationen in Wikipedia",
            category=ToolCategory.INFORMATION,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Suchbegriff",
                    required=True
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Wikipedia-Sprache",
                    required=False,
                    default="de",
                    enum=["de", "en", "fr", "es"]
                )
            ],
            function=self._wikipedia_stub,
            requires_consent=False,
            privacy_level="low"
        ))
        
        # 🕐 Current Time/Date
        self.register_tool(ToolDefinition(
            name="get_current_time",
            description="Gibt aktuelles Datum und Uhrzeit zurück",
            category=ToolCategory.UTILITY,
            parameters=[
                ToolParameter(
                    name="timezone",
                    type="string",
                    description="Zeitzone (optional)",
                    required=False,
                    default="Europe/Berlin"
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Ausgabeformat",
                    required=False,
                    default="full",
                    enum=["full", "date", "time"]
                )
            ],
            function=self._time_stub,
            requires_consent=False,
            privacy_level="low"
        ))
    
    def register_tool(self, tool: ToolDefinition):
        """Registriere neues Tool"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Hole Tool-Definition"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """Liste alle Tools (optional gefiltert nach Kategorie)"""
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())
    
    def get_tool_descriptions_for_llm(self) -> str:
        """Generiere Tool-Beschreibungen für Ollama System-Prompt"""
        lines = ["Du hast Zugriff auf folgende Tools:\n"]
        
        for tool in self._tools.values():
            params_str = ", ".join([
                f"{p.name}: {p.type}" + ("" if p.required else " (optional)")
                for p in tool.parameters
            ])
            
            lines.append(f"• {tool.name}({params_str})")
            lines.append(f"  → {tool.description}")
            if tool.requires_consent:
                lines.append(f"  ⚠️ Erfordert User-Zustimmung")
            lines.append("")
        
        lines.append("Um ein Tool zu verwenden, antworte mit:")
        lines.append("<tool_call>")
        lines.append("{")
        lines.append('  "tool": "tool_name",')
        lines.append('  "parameters": { "param": "value" }')
        lines.append("}")
        lines.append("</tool_call>")
        
        return "\n".join(lines)
    
    def get_tools_for_ollama(self) -> List[Dict]:
        """
        Serializes tools into Ollama's native function-calling format
        (`{"type": "function", "function": {...}}`, JSON-Schema parameters) -
        for the real tool_calls loop in chat_streaming.py, as opposed to
        get_tool_descriptions_for_llm()'s prompt text that teaches chat.py's
        model a <tool_call> tag to emit and tool_parser.py to regex out.

        Restricted to privacy_level == "low": get_weather/detect_location
        require consent, and ToolExecutor._check_user_consent is currently a
        stub that unconditionally denies anything above "low" - exposing
        them as callable tools here would just mean the model "calls" them
        and always gets a consent-denied error back. Filtering by the same
        field ToolExecutor itself checks means this list widens on its own,
        with no change needed here, once real per-user consent exists.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            p.name: {
                                "type": p.type,
                                "description": p.description,
                                **({"enum": p.enum} if p.enum else {}),
                                **({"default": p.default} if p.default is not None else {})
                            }
                            for p in tool.parameters
                        },
                        "required": [p.name for p in tool.parameters if p.required]
                    }
                }
            }
            for tool in self._tools.values()
            if tool.privacy_level == "low"
        ]

    def get_tool_schema(self, name: str) -> Optional[Dict]:
        """Hole Tool-Schema als JSON (für API-Docs)"""
        tool = self.get_tool(name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description,
                        **({"enum": p.enum} if p.enum else {}),
                        **({"default": p.default} if p.default is not None else {})
                    }
                    for p in tool.parameters
                },
                "required": [p.name for p in tool.parameters if p.required]
            },
            "requires_consent": tool.requires_consent,
            "privacy_level": tool.privacy_level
        }
    
    # Stub-Funktionen (werden später durch echte Services ersetzt)
    async def _web_search_stub(self, **kwargs):
        """Placeholder für Web-Search"""
        return {"error": "Not implemented", "tool": "web_search"}
    
    async def _weather_stub(self, **kwargs):
        """Placeholder für Weather"""
        return {"error": "Not implemented", "tool": "get_weather"}
    
    async def _location_stub(self, **kwargs):
        """Placeholder für Location"""
        return {"error": "Not implemented", "tool": "detect_location"}
    
    async def _wikipedia_stub(self, **kwargs):
        """Placeholder für Wikipedia"""
        return {"error": "Not implemented", "tool": "wikipedia_search"}
    
    async def _time_stub(self, **kwargs):
        """Placeholder für Time"""
        from datetime import datetime
        import pytz
        
        tz = pytz.timezone(kwargs.get("timezone", "Europe/Berlin"))
        now = datetime.now(tz)
        
        format_type = kwargs.get("format", "full")
        
        if format_type == "date":
            return {"date": now.strftime("%d.%m.%Y")}
        elif format_type == "time":
            return {"time": now.strftime("%H:%M:%S")}
        else:
            return {
                "datetime": now.isoformat(),
                "formatted": now.strftime("%A, %d. %B %Y, %H:%M:%S Uhr"),
                "timezone": str(tz)
            }


# Singleton instance
_tool_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get or create ToolRegistry singleton"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
